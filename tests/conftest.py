import os
import tempfile

import pytest

from app import create_app
from app.models import FixedCommitment, Goal, Obligation, db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    class TestConfig:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SECRET_KEY = "test"
        TESTING = True

    flask_app = create_app(TestConfig)

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def make_obligation(app):
    def _make(title, deadline, effort_minutes, time_logged=0, status="pending", first_step="do the first tiny step"):
        obligation = Obligation(
            title=title,
            first_step=first_step,
            deadline=deadline,
            estimated_effort_minutes=effort_minutes,
            time_logged_minutes=time_logged,
            status=status,
        )
        db.session.add(obligation)
        db.session.commit()
        return obligation

    return _make


@pytest.fixture
def make_goal(app):
    def _make(title, soft_target_date, total_effort_minutes, time_logged=0, status="active", created_at=None):
        goal = Goal(
            title=title,
            estimated_total_effort_minutes=total_effort_minutes,
            soft_target_date=soft_target_date,
            time_logged_minutes=time_logged,
            status=status,
        )
        if created_at is not None:
            goal.created_at = created_at
        db.session.add(goal)
        db.session.commit()
        return goal

    return _make


@pytest.fixture
def make_fixed_commitment(app):
    def _make(title, start_time, end_time, day_of_week=None, specific_date=None, recurring=False):
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
        return commitment

    return _make
