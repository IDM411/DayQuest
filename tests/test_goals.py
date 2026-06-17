from datetime import datetime, timedelta

from app import scheduler
from app.models import ScheduledBlock

from .helpers import assert_no_overlaps, total_minutes

# Same anchor the obligation suite uses: 2026-06-17 08:00, a Wednesday, start of
# a full 14h scheduling day.
WEDNESDAY = datetime(2026, 6, 17, 8, 0, 0)


def goal_blocks(ref_id):
    return ScheduledBlock.query.filter_by(ref_type="goal", ref_id=ref_id).all()


def schedulable_blocks():
    return (
        ScheduledBlock.query.filter(ScheduledBlock.ref_type.in_(("obligation", "goal")))
        .order_by(ScheduledBlock.start_time)
        .all()
    )


def all_blocks():
    return ScheduledBlock.query.all()


# ---------------------------------------------------------------------------
# 1. Goal vs obligation competing for the same slot - urgency decides
# ---------------------------------------------------------------------------

def test_goal_outranks_far_obligation_for_the_first_slot(app, make_goal, make_obligation):
    now = WEDNESDAY

    # Goal: near soft target -> high urgency. 120/1440 ~= 0.0833.
    goal = make_goal("Learn Spanish", soft_target_date=now + timedelta(days=1), total_effort_minutes=120)
    # Obligation: distant deadline -> low urgency. 120/14400 ~= 0.0083.
    obligation = make_obligation("Distant essay", deadline=now + timedelta(days=10), effort_minutes=120)

    # The shared urgency formula ranks the goal above the obligation...
    assert scheduler.compute_urgency(goal, now, 120) > scheduler.compute_urgency(obligation, now, 120)

    scheduler.run_scheduler(now=now)

    # ...so the goal claims the first slot, the obligation follows, and nothing
    # is lost.
    first = schedulable_blocks()[0]
    assert (first.ref_type, first.ref_id) == ("goal", goal.id)
    assert first.start_time == now
    assert total_minutes(goal_blocks(goal.id)) == 120
    assert assert_no_overlaps(all_blocks()) is None


def test_obligation_outranks_far_goal_for_the_first_slot(app, make_goal, make_obligation):
    now = WEDNESDAY

    # Mirror image: the obligation is the urgent one this time.
    obligation = make_obligation("Due tomorrow", deadline=now + timedelta(days=1), effort_minutes=120)
    goal = make_goal("Someday reading", soft_target_date=now + timedelta(days=10), total_effort_minutes=120)

    assert scheduler.compute_urgency(obligation, now, 120) > scheduler.compute_urgency(goal, now, 120)

    scheduler.run_scheduler(now=now)

    first = schedulable_blocks()[0]
    assert (first.ref_type, first.ref_id) == ("obligation", obligation.id)


# ---------------------------------------------------------------------------
# 2. Self-correcting cadence: falling behind tightens it
# ---------------------------------------------------------------------------

def test_falling_behind_pace_tightens_cadence(app, make_goal):
    created = WEDNESDAY
    target = WEDNESDAY + timedelta(days=14)
    # 840 min over 2 weeks -> original plan is 420 min/week.
    goal = make_goal("Thesis chapter", soft_target_date=target, total_effort_minutes=840, created_at=created)

    original = scheduler.compute_cadence(goal, now=created)
    assert original["minutes_per_week"] == 420

    # 10 days in, only 100 min logged (a steady pace would be ~600 by now).
    later = created + timedelta(days=10)
    goal.time_logged_minutes = 100

    assert scheduler.pace_status(goal, now=later) == "behind"

    tightened = scheduler.compute_cadence(goal, now=later)
    # Remaining effort is still large but far less time remains, so the required
    # weekly load (and session count) goes UP.
    assert tightened["minutes_per_week"] > original["minutes_per_week"]
    assert tightened["sessions_per_week"] > original["sessions_per_week"]


# ---------------------------------------------------------------------------
# 3. Self-correcting cadence: running ahead loosens it
# ---------------------------------------------------------------------------

def test_running_ahead_of_pace_loosens_cadence(app, make_goal):
    created = WEDNESDAY
    target = WEDNESDAY + timedelta(days=14)
    goal = make_goal("Thesis chapter", soft_target_date=target, total_effort_minutes=840, created_at=created)

    original = scheduler.compute_cadence(goal, now=created)
    assert original["minutes_per_week"] == 420

    # 4 days in, already 500 min logged (a steady pace would be ~240 by now).
    later = created + timedelta(days=4)
    goal.time_logged_minutes = 500

    assert scheduler.pace_status(goal, now=later) == "ahead"

    loosened = scheduler.compute_cadence(goal, now=later)
    # Less effort remains with plenty of time left, so the required weekly load
    # (and session count) drops.
    assert loosened["minutes_per_week"] < original["minutes_per_week"]
    assert loosened["sessions_per_week"] < original["sessions_per_week"]


# ---------------------------------------------------------------------------
# 4. Goal-type blocks go through push and done exactly like obligations
# ---------------------------------------------------------------------------

def test_goal_block_push_then_rerun_does_not_double_count(app, make_goal):
    now = WEDNESDAY
    goal = make_goal("Learn Spanish", soft_target_date=now + timedelta(days=1), total_effort_minutes=120)

    scheduler.run_scheduler(now=now)
    block = goal_blocks(goal.id)[0]
    assert block.start_time == now

    scheduler.push_block(block.id, push_minutes=30, now=now)

    after_push = goal_blocks(goal.id)
    assert len(after_push) == 1
    assert after_push[0].status == "pushed"
    assert after_push[0].start_time == now + timedelta(minutes=30)
    assert total_minutes(after_push) == 120

    # A later full re-run (as triggered by adding anything elsewhere) must leave
    # the pushed goal block untouched - same identity, no duplication.
    scheduler.run_scheduler(now=now)

    after_rerun = goal_blocks(goal.id)
    assert len(after_rerun) == 1
    assert after_rerun[0].id == after_push[0].id
    assert after_rerun[0].status == "pushed"
    assert total_minutes(after_rerun) == 120  # not 240
    assert_no_overlaps(all_blocks())


def test_goal_block_done_logs_time_and_completes_goal(app, make_goal):
    now = WEDNESDAY
    goal = make_goal("Learn Spanish", soft_target_date=now + timedelta(days=2), total_effort_minutes=180)

    scheduler.run_scheduler(now=now)
    block = goal_blocks(goal.id)[0]
    assert total_minutes([block]) == 180  # fits contiguously before the soft target

    scheduler.mark_done(block.id, now=now)

    # Time logged against the goal, and since it met the estimate the goal is done.
    assert goal.time_logged_minutes == 180
    assert goal.status == "done"
    # Completed goal no longer competes, so nothing remains for "Right Now".
    assert scheduler.get_right_now(now=now) is None


def test_goal_done_with_explicit_actual_minutes_keeps_goal_active(app, make_goal):
    now = WEDNESDAY
    goal = make_goal("Learn Spanish", soft_target_date=now + timedelta(days=5), total_effort_minutes=600)

    scheduler.run_scheduler(now=now)
    block = goal_blocks(goal.id)[0]

    # A short session logs less than the full block duration (the zero-tap done
    # path can also pass explicit minutes); the goal stays active with the
    # logged time recorded.
    scheduler.mark_done(block.id, actual_minutes=20, now=now)

    assert goal.time_logged_minutes == 20
    assert goal.status == "active"
