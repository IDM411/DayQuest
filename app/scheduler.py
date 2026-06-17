from datetime import datetime, time, timedelta

from .models import FixedCommitment, Obligation, ScheduledBlock, db

DAY_START_HOUR = 8
DAY_END_HOUR = 22
HORIZON_DAYS = 14
MIN_BLOCK_MINUTES = 15
DEFAULT_PUSH_MINUTES = 30


def _fixed_occurrences(start, end):
    """Expand FixedCommitment rows into concrete (commitment_id, start, end) intervals in [start, end)."""
    occurrences = []
    for fc in FixedCommitment.query.all():
        if fc.recurring:
            day = start.date()
            while day <= end.date():
                if day.weekday() == fc.day_of_week:
                    occ_start = datetime.combine(day, fc.start_time)
                    occ_end = datetime.combine(day, fc.end_time)
                    if occ_end > start and occ_start < end:
                        occurrences.append((fc.id, occ_start, occ_end))
                day += timedelta(days=1)
        elif fc.specific_date and start.date() <= fc.specific_date <= end.date():
            occ_start = datetime.combine(fc.specific_date, fc.start_time)
            occ_end = datetime.combine(fc.specific_date, fc.end_time)
            if occ_end > start and occ_start < end:
                occurrences.append((fc.id, occ_start, occ_end))
    return sorted(occurrences, key=lambda o: o[1])


def _locked_blocks(start, end):
    """Obligation blocks active, done, or explicitly pushed by the user - never moved by a re-run."""
    blocks = ScheduledBlock.query.filter(
        ScheduledBlock.status.in_(["active", "done", "pushed"]),
        ScheduledBlock.end_time > start,
        ScheduledBlock.start_time < end,
    ).all()
    return [(b.start_time, b.end_time) for b in blocks]


def _reserved_minutes(start, end):
    """Minutes of obligation effort already claimed by active/pushed blocks in [start, end) - not yet logged via mark_done, so it must be subtracted from remaining effort to avoid double-scheduling."""
    blocks = ScheduledBlock.query.filter(
        ScheduledBlock.ref_type == "obligation",
        ScheduledBlock.status.in_(["active", "pushed"]),
        ScheduledBlock.end_time > start,
        ScheduledBlock.start_time < end,
    ).all()
    reserved = {}
    for b in blocks:
        reserved[b.ref_id] = reserved.get(b.ref_id, 0) + (b.end_time - b.start_time).total_seconds() / 60
    return reserved


def _free_gaps(start, end, busy_intervals):
    """Waking-hours gaps in [start, end) not covered by busy_intervals, per calendar day."""
    busy = sorted(busy_intervals)
    gaps = []
    day = start.date()
    while day <= end.date():
        day_start = max(datetime.combine(day, time(hour=DAY_START_HOUR)), start)
        day_end = min(datetime.combine(day, time(hour=DAY_END_HOUR)), end)
        if day_start < day_end:
            cursor = day_start
            for b_start, b_end in busy:
                if b_end <= cursor or b_start >= day_end:
                    continue
                if b_start > cursor:
                    gaps.append((cursor, min(b_start, day_end)))
                cursor = max(cursor, b_end)
            if cursor < day_end:
                gaps.append((cursor, day_end))
        day += timedelta(days=1)
    return gaps


def compute_urgency(obligation, now, remaining_minutes):
    minutes_until_deadline = max((obligation.deadline - now).total_seconds() / 60, 1)
    return remaining_minutes / minutes_until_deadline


def _fill_gaps(gaps, reserved):
    """Greedily fill gaps chronologically with the highest-urgency pending obligation (PRD Section 9, steps 2-4)."""
    obligations = {o.id: o for o in Obligation.query.filter_by(status="pending").all()}
    remaining = {
        oid: max(o.estimated_effort_minutes - o.time_logged_minutes - reserved.get(oid, 0), 0)
        for oid, o in obligations.items()
    }

    new_blocks = []
    for gap_start, gap_end in gaps:
        cursor = gap_start
        while cursor < gap_end:
            candidates = [oid for oid, mins in remaining.items() if mins > 0 and obligations[oid].deadline > cursor]
            if not candidates:
                break
            candidates.sort(key=lambda oid: (
                -compute_urgency(obligations[oid], cursor, remaining[oid]),
                obligations[oid].deadline,
                -remaining[oid],
            ))
            chosen_id = candidates[0]
            chosen = obligations[chosen_id]

            slot_minutes = min(remaining[chosen_id], (gap_end - cursor).total_seconds() / 60)
            # A sliver too small to be useful is skipped unless it's enough to finish the obligation outright.
            if slot_minutes < MIN_BLOCK_MINUTES and slot_minutes < remaining[chosen_id]:
                break

            block_end = min(cursor + timedelta(minutes=slot_minutes), chosen.deadline)
            new_blocks.append(ScheduledBlock(
                ref_type="obligation",
                ref_id=chosen_id,
                start_time=cursor,
                end_time=block_end,
                status="planned",
            ))
            remaining[chosen_id] -= (block_end - cursor).total_seconds() / 60
            cursor = block_end

    return new_blocks


def run_scheduler(now=None):
    """Full re-run: locks fixed commitments, then fills every open gap by urgency (Section 9, steps 1-4)."""
    now = now or datetime.utcnow()
    horizon_end = now + timedelta(days=HORIZON_DAYS)

    ScheduledBlock.query.filter(
        ScheduledBlock.status == "planned",
        ScheduledBlock.start_time >= now,
    ).delete(synchronize_session=False)

    fixed_occurrences = _fixed_occurrences(now, horizon_end)
    busy = [(s, e) for _, s, e in fixed_occurrences] + _locked_blocks(now, horizon_end)
    gaps = _free_gaps(now, horizon_end, busy)
    reserved = _reserved_minutes(now, horizon_end)

    new_blocks = [
        ScheduledBlock(ref_type="fixed", ref_id=fc_id, start_time=s, end_time=e, status="planned")
        for fc_id, s, e in fixed_occurrences
    ]
    new_blocks += _fill_gaps(gaps, reserved)

    db.session.add_all(new_blocks)
    db.session.commit()
    return new_blocks


def push_block(block_id, push_minutes=DEFAULT_PUSH_MINUTES, now=None):
    """Push: shift the block later, cascade same-day obligation blocks, refill the remainder of the day (Section 9, step 5)."""
    now = now or datetime.utcnow()
    block = ScheduledBlock.query.get(block_id)
    if block is None:
        raise ValueError(f"no scheduled block with id {block_id}")
    if block.ref_type != "obligation":
        raise ValueError("only obligation blocks can be pushed")

    delta = timedelta(minutes=push_minutes)
    day_end = datetime.combine(block.start_time.date(), time(hour=DAY_END_HOUR))

    rest_of_day = ScheduledBlock.query.filter(
        ScheduledBlock.ref_type == "obligation",
        ScheduledBlock.status == "planned",
        ScheduledBlock.start_time >= block.start_time,
        ScheduledBlock.start_time < day_end,
    ).all()
    for b in rest_of_day:
        b.start_time += delta
        b.end_time += delta

    block.status = "pushed"
    db.session.flush()

    ScheduledBlock.query.filter(
        ScheduledBlock.ref_type == "obligation",
        ScheduledBlock.status == "planned",
        ScheduledBlock.start_time >= now,
        ScheduledBlock.start_time < day_end,
    ).delete(synchronize_session=False)

    fixed_occurrences = _fixed_occurrences(now, day_end)
    busy = [(s, e) for _, s, e in fixed_occurrences] + _locked_blocks(now, day_end)
    gaps = _free_gaps(now, day_end, busy)
    reserved = _reserved_minutes(now, day_end)
    new_blocks = _fill_gaps(gaps, reserved)

    db.session.add_all(new_blocks)
    db.session.commit()
    return new_blocks


def mark_done(block_id, actual_minutes=None, now=None):
    """Mark done: log actual time against the obligation, then fully re-run the scheduler."""
    now = now or datetime.utcnow()
    block = ScheduledBlock.query.get(block_id)
    if block is None:
        raise ValueError(f"no scheduled block with id {block_id}")

    block.status = "done"
    if block.ref_type == "obligation":
        obligation = Obligation.query.get(block.ref_id)
        logged = actual_minutes if actual_minutes is not None else (block.end_time - block.start_time).total_seconds() / 60
        obligation.time_logged_minutes += logged
        if obligation.time_logged_minutes >= obligation.estimated_effort_minutes:
            obligation.status = "done"
    db.session.commit()

    return run_scheduler(now=now)


def get_right_now(now=None):
    """The entire home view: the single highest-urgency obligation block currently due."""
    now = now or datetime.utcnow()
    return (
        ScheduledBlock.query.filter(
            ScheduledBlock.ref_type == "obligation",
            ScheduledBlock.status.in_(["planned", "active"]),
            ScheduledBlock.end_time > now,
        )
        .order_by(ScheduledBlock.start_time)
        .first()
    )
