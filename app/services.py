"""Creation logic for the three record types.

Both the manual form routes and the free-text capture endpoint go through these
functions, so there is one place that builds a record, persists it, and triggers
a reschedule. `reschedule=False` lets a caller create several records (e.g. a
recurring commitment across multiple days) and run the scheduler once at the end.
"""

from . import scheduler
from .models import FixedCommitment, Goal, Obligation, db


def create_fixed_commitment(*, title, recurring, day_of_week, specific_date,
                            start_time, end_time, reschedule=True):
    commitment = FixedCommitment(
        title=title,
        recurring=recurring,
        day_of_week=day_of_week,
        specific_date=specific_date,
        start_time=start_time,
        end_time=end_time,
    )
    db.session.add(commitment)
    db.session.commit()
    if reschedule:
        scheduler.run_scheduler()
    return commitment


def create_obligation(*, title, first_step, deadline, estimated_effort_minutes,
                      source=None, reschedule=True):
    obligation = Obligation(
        title=title,
        first_step=first_step,
        deadline=deadline,
        estimated_effort_minutes=estimated_effort_minutes,
        source=source,
    )
    db.session.add(obligation)
    db.session.commit()
    if reschedule:
        scheduler.run_scheduler()
    return obligation


def create_goal(*, title, estimated_total_effort_minutes, soft_target_date,
                reschedule=True):
    goal = Goal(
        title=title,
        estimated_total_effort_minutes=estimated_total_effort_minutes,
        soft_target_date=soft_target_date,
    )
    db.session.add(goal)
    db.session.commit()
    if reschedule:
        scheduler.run_scheduler()
    return goal
