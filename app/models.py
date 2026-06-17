from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class FixedCommitment(db.Model):
    __tablename__ = "fixed_commitments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    recurring = db.Column(db.Boolean, nullable=False, default=False)
    day_of_week = db.Column(db.Integer, nullable=True)  # 0=Monday..6=Sunday, set when recurring
    specific_date = db.Column(db.Date, nullable=True)  # set when not recurring
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Obligation(db.Model):
    __tablename__ = "obligations"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    first_step = db.Column(db.String(300), nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    estimated_effort_minutes = db.Column(db.Integer, nullable=False)
    time_logged_minutes = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending|done
    source = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def total_effort_minutes(self):
        """Uniform accessor so the scheduler can treat obligations and goals alike."""
        return self.estimated_effort_minutes


class Goal(db.Model):
    __tablename__ = "goals"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    estimated_total_effort_minutes = db.Column(db.Integer, nullable=False)
    soft_target_date = db.Column(db.DateTime, nullable=False)
    time_logged_minutes = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="active")  # active|done|abandoned
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def total_effort_minutes(self):
        """Uniform accessor so the scheduler can treat obligations and goals alike."""
        return self.estimated_total_effort_minutes


class ScheduledBlock(db.Model):
    __tablename__ = "scheduled_blocks"

    id = db.Column(db.Integer, primary_key=True)
    ref_type = db.Column(db.String(20), nullable=False)  # fixed|obligation
    ref_id = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="planned")  # planned|active|done|pushed
