from datetime import datetime, time, timedelta

import pytest

from app import scheduler
from app.models import ScheduledBlock

from .helpers import assert_no_overlaps, total_minutes

# 2026-06-17 08:00, confirmed weekday() == 2 (Wednesday) - used everywhere so
# day_of_week-based fixed commitments line up deterministically.
WEDNESDAY = datetime(2026, 6, 17, 8, 0, 0)


def obligation_blocks(ref_id):
    return ScheduledBlock.query.filter_by(ref_type="obligation", ref_id=ref_id).all()


def all_blocks():
    return ScheduledBlock.query.all()


# ---------------------------------------------------------------------------
# 1. Stale obligation
# ---------------------------------------------------------------------------

def test_stale_overdue_obligation_does_not_block_or_blow_up(app, make_obligation):
    now = WEDNESDAY
    stale = make_obligation("Forgotten reading", deadline=now - timedelta(days=3), effort_minutes=60)
    fresh = make_obligation("Current essay", deadline=now + timedelta(days=2), effort_minutes=60)

    # urgency must stay finite and sane once the deadline is in the past -
    # minutes_until_deadline clamps to 1, so urgency == remaining, never
    # negative/undefined/infinite.
    urgency = scheduler.compute_urgency(stale, now, remaining_minutes=60)
    assert urgency == 60

    scheduler.run_scheduler(now=now)

    # the overdue item can never win a slot (its deadline is already behind
    # the scheduling cursor) so it never claims one ...
    assert obligation_blocks(stale.id) == []
    # ... and, crucially, it doesn't sit there blocking the gap either - the
    # still-actionable obligation gets its full effort scheduled.
    assert total_minutes(obligation_blocks(fresh.id)) == 60
    assert stale.status == "pending"


# ---------------------------------------------------------------------------
# 2. Push-cascade correctness (regression test for the pushed-block bug)
# ---------------------------------------------------------------------------

def test_push_then_full_rerun_does_not_double_count_pushed_obligation(app, make_obligation):
    now = WEDNESDAY
    essay = make_obligation("Essay draft", deadline=now + timedelta(days=1), effort_minutes=120)
    reading = make_obligation("Reading response", deadline=now + timedelta(days=7), effort_minutes=60)

    scheduler.run_scheduler(now=now)
    essay_block = obligation_blocks(essay.id)[0]
    assert essay_block.start_time == now  # essay's urgency wins the first slot

    scheduler.push_block(essay_block.id, push_minutes=30, now=now)

    essay_after_push = obligation_blocks(essay.id)
    assert len(essay_after_push) == 1
    assert essay_after_push[0].status == "pushed"
    assert essay_after_push[0].start_time == now + timedelta(minutes=30)
    assert total_minutes(essay_after_push) == 120

    # This is exactly the call that exposed the original bug: a full re-run
    # (as would be triggered by adding a new obligation/commitment elsewhere)
    # must not touch or duplicate the already-pushed block.
    scheduler.run_scheduler(now=now)

    essay_after_rerun = obligation_blocks(essay.id)
    assert len(essay_after_rerun) == 1
    assert essay_after_rerun[0].id == essay_after_push[0].id
    assert essay_after_rerun[0].status == "pushed"
    assert total_minutes(essay_after_rerun) == 120  # not 240 - no duplication

    assert total_minutes(obligation_blocks(reading.id)) == 60
    assert_no_overlaps(all_blocks())


# ---------------------------------------------------------------------------
# 3. Overload
# ---------------------------------------------------------------------------

def test_overload_lowest_urgency_falls_through_to_next_day(app, make_obligation):
    now = WEDNESDAY  # 08:00 - full 14h (840 min) day available
    high = make_obligation("Due tomorrow", deadline=now + timedelta(days=1), effort_minutes=500)
    low = make_obligation("Due in 10 days", deadline=now + timedelta(days=10), effort_minutes=500)

    scheduler.run_scheduler(now=now)  # 1000 min of effort, 840 min/day capacity

    high_blocks = obligation_blocks(high.id)
    low_blocks = obligation_blocks(low.id)

    # nothing vanished - every minute of effort lands somewhere
    assert total_minutes(high_blocks) == 500
    assert total_minutes(low_blocks) == 500

    # the lower-urgency item can't fully fit in day one and has to spill into
    # day two rather than being dropped
    today = now.date()
    assert any(b.start_time.date() > today for b in low_blocks)

    assert_no_overlaps(all_blocks())


# ---------------------------------------------------------------------------
# 4. Tie-breaking determinism
# ---------------------------------------------------------------------------

def test_tie_break_closer_deadline_wins_on_equal_urgency(app, make_obligation):
    now = WEDNESDAY
    # Equal urgency by construction: 30/1440 == 60/2880 == 1/48.
    # (Note: the third-level tiebreak - larger remaining effort - only fires
    # when both urgency AND deadline are equal; since urgency = remaining /
    # minutes_until_deadline, an equal deadline forces equal remaining too,
    # so that branch is mathematically unreachable as an independent case
    # and isn't tested separately here.)
    closer = make_obligation("Closer deadline", deadline=now + timedelta(days=1), effort_minutes=30)
    farther = make_obligation("Farther deadline", deadline=now + timedelta(days=2), effort_minutes=60)

    urgency_closer = scheduler.compute_urgency(closer, now, 30)
    urgency_farther = scheduler.compute_urgency(farther, now, 60)
    assert urgency_closer == pytest.approx(urgency_farther)

    blocks = scheduler.run_scheduler(now=now)
    obligation_only = sorted(
        (b for b in blocks if b.ref_type == "obligation"), key=lambda b: b.start_time
    )
    assert obligation_only[0].ref_id == closer.id


def test_tie_break_is_deterministic_across_repeated_runs(app, make_obligation):
    now = WEDNESDAY
    closer = make_obligation("Closer deadline", deadline=now + timedelta(days=1), effort_minutes=30)
    farther = make_obligation("Farther deadline", deadline=now + timedelta(days=2), effort_minutes=60)

    orderings = set()
    for _ in range(5):
        blocks = scheduler.run_scheduler(now=now)
        order = tuple(
            (b.ref_id, b.start_time, b.end_time)
            for b in sorted((b for b in blocks if b.ref_type == "obligation"), key=lambda b: b.start_time)
        )
        orderings.add(order)

    assert len(orderings) == 1  # identical result every time, never random


# ---------------------------------------------------------------------------
# 5. Fixed commitment collision
# ---------------------------------------------------------------------------

def test_does_not_schedule_into_locked_fixed_commitment(app, make_obligation, make_fixed_commitment):
    now = WEDNESDAY  # 2026-06-17, weekday() == 2
    make_fixed_commitment("Gym", start_time=time(17, 0), end_time=time(18, 0), day_of_week=2, recurring=True)

    # the deadline sits *inside* the locked gym window - the obligation must
    # still be fully scheduled before the lock, never inside or across it
    obligation = make_obligation("Quick task", deadline=now.replace(hour=17, minute=30), effort_minutes=60)

    scheduler.run_scheduler(now=now)

    gym_start = now.replace(hour=17, minute=0)
    gym_end = now.replace(hour=18, minute=0)

    task_blocks = obligation_blocks(obligation.id)
    assert total_minutes(task_blocks) == 60  # comfortably fits in the 9h gap before gym
    for b in task_blocks:
        assert b.end_time <= gym_start or b.start_time >= gym_end

    assert_no_overlaps(all_blocks())


# ---------------------------------------------------------------------------
# 6. Concurrent multi-push
# ---------------------------------------------------------------------------

def test_concurrent_pushes_without_intervening_rerun_stay_consistent(app, make_obligation):
    now = WEDNESDAY
    c1 = make_obligation("C1", deadline=now + timedelta(days=1), effort_minutes=60)
    c2 = make_obligation("C2", deadline=now + timedelta(days=2), effort_minutes=60)
    c3 = make_obligation("C3", deadline=now + timedelta(days=3), effort_minutes=60)

    scheduler.run_scheduler(now=now)
    block_a = obligation_blocks(c1.id)[0]  # earliest / highest-urgency block

    scheduler.push_block(block_a.id, push_minutes=30, now=now)

    # Push a second block before ever calling run_scheduler() again - i.e.
    # before A's cascade/refill has been "settled" by a fresh full re-run.
    remaining_planned = (
        ScheduledBlock.query.filter_by(status="planned").order_by(ScheduledBlock.start_time).all()
    )
    block_b = remaining_planned[0]

    scheduler.push_block(block_b.id, push_minutes=30, now=now)

    final_blocks = all_blocks()
    assert_no_overlaps(final_blocks)

    # every minute of every obligation is accounted for exactly once - no
    # duplication, no loss, regardless of the exact slots each landed in
    assert total_minutes(obligation_blocks(c1.id)) == 60
    assert total_minutes(obligation_blocks(c2.id)) == 60
    assert total_minutes(obligation_blocks(c3.id)) == 60

    pushed_ids = {b.id for b in final_blocks if b.status == "pushed"}
    assert pushed_ids == {block_a.id, block_b.id}
