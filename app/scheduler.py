from datetime import datetime, time, timedelta

from .models import FixedCommitment, Goal, Obligation, ScheduledBlock, db
from .timeutils import local_now

DAY_START_HOUR = 8
DAY_END_HOUR = 22
HORIZON_DAYS = 14
MIN_BLOCK_MINUTES = 15
DEFAULT_PUSH_MINUTES = 30

# Schedulable work (obligations + goals) shares one urgency formula and one
# gap-filling loop. "ref_type" is the discriminator the rest of the system
# already uses on ScheduledBlock.
SCHEDULABLE_REF_TYPES = ("obligation", "goal")

# A goal session targets roughly this length; cadence breaks the weekly effort
# into sessions of about this size (PRD Section 10.1).
SESSION_TARGET_MINUTES = 45


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
    """Minutes of effort already claimed by active/pushed blocks in [start, end) - not yet logged via mark_done, so it must be subtracted from remaining effort to avoid double-scheduling. Keyed by (ref_type, ref_id) to cover obligations and goals alike."""
    blocks = ScheduledBlock.query.filter(
        ScheduledBlock.ref_type.in_(SCHEDULABLE_REF_TYPES),
        ScheduledBlock.status.in_(["active", "pushed"]),
        ScheduledBlock.end_time > start,
        ScheduledBlock.start_time < end,
    ).all()
    reserved = {}
    for b in blocks:
        key = (b.ref_type, b.ref_id)
        reserved[key] = reserved.get(key, 0) + (b.end_time - b.start_time).total_seconds() / 60
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


def _target_datetime(item):
    """The point urgency races toward: an obligation's hard deadline or a goal's soft target date."""
    return getattr(item, "deadline", None) or getattr(item, "soft_target_date", None)


def _schedulable_items():
    """Currently-schedulable work, keyed by (ref_type, ref_id).

    Obligations and goals are pooled here so they compete in one urgency-ranked
    queue. Keying by (ref_type, ref_id) keeps an obligation #1 distinct from a
    goal #1.
    """
    items = {}
    for o in Obligation.query.filter_by(status="pending").all():
        items[("obligation", o.id)] = o
    for g in Goal.query.filter_by(status="active").all():
        items[("goal", g.id)] = g
    return items


def compute_urgency(item, now, remaining_minutes):
    """urgency = remaining_effort / minutes_until_target (PRD Section 9, step 2).

    Works for any schedulable item: obligations race toward their deadline,
    goals toward their soft target date. minutes_until clamps to 1 so an
    already-past target yields a finite urgency equal to remaining effort
    rather than blowing up or going negative.
    """
    minutes_until = max((_target_datetime(item) - now).total_seconds() / 60, 1)
    return remaining_minutes / minutes_until


def compute_cadence(goal, now=None):
    """Back-calculate a session cadence for a goal (PRD Section 10.1).

    The whole thing is derived from *current* state, which is what makes it
    self-correcting: as `now` advances and `time_logged_minutes` grows, the
    same formula re-run later automatically tightens or loosens.

        remaining        = total_effort - time_logged              (clamped >= 0)
        weeks_until      = days_until_target / 7                   (>= ~1 day)
        minutes_per_week = remaining / weeks_until
        sessions_per_week = round(minutes_per_week / SESSION_TARGET_MINUTES)  (>= 1)
        session_length    = minutes_per_week / sessions_per_week

    Worked example - 6h total, 2 weeks out, nothing logged yet:
        remaining = 360, weeks_until = 2  -> minutes_per_week = 180
        sessions_per_week = round(180/45) = 4, session_length = 45
        => four ~45-minute sessions a week. (Fewer/longer sessions only if the
        weekly load is smaller; the load itself is fixed by effort and time.)
    """
    now = now or local_now()
    remaining = max(goal.total_effort_minutes - goal.time_logged_minutes, 0)
    days_until = max((goal.soft_target_date - now).total_seconds() / 86400, 1.0)
    weeks_until = days_until / 7
    minutes_per_week = remaining / weeks_until
    sessions_per_week = max(1, round(minutes_per_week / SESSION_TARGET_MINUTES))
    session_length = round(minutes_per_week / sessions_per_week) if sessions_per_week else 0
    return {
        "remaining_minutes": round(remaining),
        "days_until_target": round(days_until, 2),
        "minutes_per_week": round(minutes_per_week),
        "sessions_per_week": sessions_per_week,
        "session_length_minutes": session_length,
    }


def pace_status(goal, now=None, tolerance=0.05):
    """Whether a goal is ahead of / behind / on its original linear plan.

    Compares time actually logged against the time a steady run from creation
    to soft target would have logged by `now`:

        fraction_elapsed = (now - created_at) / (target - created_at)   (0..1)
        expected_logged  = total_effort * fraction_elapsed
        behind  if logged < expected - tolerance*total_effort
        ahead   if logged > expected + tolerance*total_effort

    "behind" means compute_cadence will have tightened relative to the original;
    "ahead" means it will have loosened. The cadence is the actionable number;
    this is the human-readable label that goes with it.
    """
    now = now or local_now()
    total_window = (goal.soft_target_date - goal.created_at).total_seconds()
    if total_window <= 0:
        return "on_pace"
    fraction = min(max((now - goal.created_at).total_seconds() / total_window, 0.0), 1.0)
    expected_logged = goal.total_effort_minutes * fraction
    margin = goal.total_effort_minutes * tolerance
    if goal.time_logged_minutes < expected_logged - margin:
        return "behind"
    if goal.time_logged_minutes > expected_logged + margin:
        return "ahead"
    return "on_pace"


def _fill_gaps(gaps, reserved):
    """Greedily fill gaps chronologically with the highest-urgency pending item (PRD Section 9, steps 2-4).

    Obligations and goals share this loop: both are pooled by _schedulable_items
    and ranked by the same urgency formula, with no per-type branching.
    """
    items = _schedulable_items()  # {(ref_type, ref_id): orm_obj}
    remaining = {
        key: max(obj.total_effort_minutes - obj.time_logged_minutes - reserved.get(key, 0), 0)
        for key, obj in items.items()
    }

    new_blocks = []
    for gap_start, gap_end in gaps:
        cursor = gap_start
        while cursor < gap_end:
            candidates = [
                key for key, mins in remaining.items()
                if mins > 0 and _target_datetime(items[key]) > cursor
            ]
            if not candidates:
                break
            candidates.sort(key=lambda key: (
                -compute_urgency(items[key], cursor, remaining[key]),
                _target_datetime(items[key]),
                -remaining[key],
            ))
            chosen_key = candidates[0]
            chosen = items[chosen_key]
            ref_type, ref_id = chosen_key

            slot_minutes = min(remaining[chosen_key], (gap_end - cursor).total_seconds() / 60)
            # A sliver too small to be useful is skipped unless it's enough to finish the item outright.
            if slot_minutes < MIN_BLOCK_MINUTES and slot_minutes < remaining[chosen_key]:
                break

            block_end = min(cursor + timedelta(minutes=slot_minutes), _target_datetime(chosen))
            new_blocks.append(ScheduledBlock(
                ref_type=ref_type,
                ref_id=ref_id,
                start_time=cursor,
                end_time=block_end,
                status="planned",
            ))
            remaining[chosen_key] -= (block_end - cursor).total_seconds() / 60
            cursor = block_end

    return new_blocks


def run_scheduler(now=None):
    """Full re-run: locks fixed commitments, then fills every open gap by urgency (Section 9, steps 1-4)."""
    now = now or local_now()
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
    """Push: move the block to the next free slot at least push_minutes later, then refill the remainder of the day around it (Section 9, step 5)."""
    now = now or local_now()
    block = ScheduledBlock.query.get(block_id)
    if block is None:
        raise ValueError(f"no scheduled block with id {block_id}")
    if block.ref_type not in SCHEDULABLE_REF_TYPES:
        raise ValueError("only obligation or goal blocks can be pushed")

    duration = block.end_time - block.start_time
    earliest_start = block.start_time + timedelta(minutes=push_minutes)
    day_end = datetime.combine(block.start_time.date(), time(hour=DAY_END_HOUR))

    # The new slot must clear every other locked interval (fixed commitments,
    # other already-pushed/active blocks) - a flat "+= delta" offset can land
    # straight on top of a block that was pushed independently elsewhere.
    target_fixed = _fixed_occurrences(earliest_start, day_end)
    target_busy = [(s, e) for _, s, e in target_fixed] + _locked_blocks(earliest_start, day_end)
    target_gaps = _free_gaps(earliest_start, day_end, target_busy)
    new_start = next((g_start for g_start, g_end in target_gaps if g_end - g_start >= duration), None)
    if new_start is None:
        # No slot big enough remains today - best effort; the next full re-run reconciles it.
        new_start = max(day_end - duration, earliest_start)

    block.start_time = new_start
    block.end_time = new_start + duration
    block.status = "pushed"
    db.session.flush()

    ScheduledBlock.query.filter(
        ScheduledBlock.ref_type.in_(SCHEDULABLE_REF_TYPES),
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
    now = now or local_now()
    block = ScheduledBlock.query.get(block_id)
    if block is None:
        raise ValueError(f"no scheduled block with id {block_id}")

    block.status = "done"
    # Obligations and goals both log actual time against their effort tally; a
    # goal's logged time is what makes its cadence self-correct on the next
    # re-run (compute_cadence reads the updated remaining effort). Fixed
    # commitments carry no effort, so nothing to log.
    ref = None
    if block.ref_type == "obligation":
        ref = Obligation.query.get(block.ref_id)
    elif block.ref_type == "goal":
        ref = Goal.query.get(block.ref_id)
    if ref is not None:
        logged = actual_minutes if actual_minutes is not None else (block.end_time - block.start_time).total_seconds() / 60
        ref.time_logged_minutes += logged
        if ref.time_logged_minutes >= ref.total_effort_minutes:
            ref.status = "done"
    db.session.commit()

    return run_scheduler(now=now)


def get_right_now(now=None):
    """The entire home view: the single highest-urgency work block currently due.

    Considers obligations and goals alike - whichever the urgency-ranked
    gap-fill placed in the earliest current slot wins the screen.
    """
    now = now or local_now()
    return (
        ScheduledBlock.query.filter(
            ScheduledBlock.ref_type.in_(SCHEDULABLE_REF_TYPES),
            ScheduledBlock.status.in_(["planned", "active"]),
            ScheduledBlock.end_time > now,
        )
        .order_by(ScheduledBlock.start_time)
        .first()
    )
