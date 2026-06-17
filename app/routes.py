from datetime import date, datetime, time

from flask import Blueprint, abort, jsonify, request

from . import capture as capture_service
from . import scheduler, services
from .models import FixedCommitment, Goal, Obligation, ScheduledBlock, db

bp = Blueprint("api", __name__, url_prefix="/api")


def _parse_target_datetime(value):
    """Accept a plain date ('YYYY-MM-DD') or a full ISO datetime for a goal's soft target.

    A bare date is anchored to the end of the working day so urgency math has a
    concrete moment to race toward.
    """
    if len(value) == 10:
        return datetime.combine(date.fromisoformat(value), time(hour=scheduler.DAY_END_HOUR))
    return datetime.fromisoformat(value)


def _serialize_commitment(c):
    return {
        "id": c.id,
        "title": c.title,
        "recurring": c.recurring,
        "day_of_week": c.day_of_week,
        "specific_date": c.specific_date.isoformat() if c.specific_date else None,
        "start_time": c.start_time.isoformat(),
        "end_time": c.end_time.isoformat(),
    }


def _serialize_obligation(o):
    return {
        "id": o.id,
        "title": o.title,
        "first_step": o.first_step,
        "deadline": o.deadline.isoformat(),
        "estimated_effort_minutes": o.estimated_effort_minutes,
        "time_logged_minutes": o.time_logged_minutes,
        "status": o.status,
        "source": o.source,
    }


def _serialize_goal(g):
    return {
        "id": g.id,
        "title": g.title,
        "estimated_total_effort_minutes": g.estimated_total_effort_minutes,
        "soft_target_date": g.soft_target_date.isoformat(),
        "time_logged_minutes": g.time_logged_minutes,
        "status": g.status,
        # Cadence and pace are derived from current state on every read, so they
        # reflect the self-correcting estimate without being stored.
        "cadence": scheduler.compute_cadence(g),
        "pace": scheduler.pace_status(g),
    }


def _serialize_block(b):
    if b is None:
        return None
    title, first_step = None, None
    if b.ref_type == "obligation":
        o = Obligation.query.get(b.ref_id)
        if o:
            title, first_step = o.title, o.first_step
    elif b.ref_type == "goal":
        g = Goal.query.get(b.ref_id)
        if g:
            title = g.title
    elif b.ref_type == "fixed":
        c = FixedCommitment.query.get(b.ref_id)
        if c:
            title = c.title
    return {
        "id": b.id,
        "ref_type": b.ref_type,
        "ref_id": b.ref_id,
        "title": title,
        "first_step": first_step,
        "start_time": b.start_time.isoformat(),
        "end_time": b.end_time.isoformat(),
        "status": b.status,
    }


@bp.route("/commitments", methods=["GET", "POST"])
def commitments():
    if request.method == "POST":
        data = request.get_json(force=True)
        recurring = bool(data.get("recurring", False))
        commitment = services.create_fixed_commitment(
            title=data["title"],
            recurring=recurring,
            day_of_week=data.get("day_of_week") if recurring else None,
            specific_date=date.fromisoformat(data["specific_date"]) if not recurring else None,
            start_time=time.fromisoformat(data["start_time"]),
            end_time=time.fromisoformat(data["end_time"]),
        )
        return jsonify(_serialize_commitment(commitment)), 201

    return jsonify([_serialize_commitment(c) for c in FixedCommitment.query.all()])


@bp.route("/obligations", methods=["GET", "POST"])
def obligations():
    if request.method == "POST":
        data = request.get_json(force=True)
        obligation = services.create_obligation(
            title=data["title"],
            first_step=data["first_step"],
            deadline=datetime.fromisoformat(data["deadline"]),
            estimated_effort_minutes=int(data["estimated_effort_minutes"]),
            source=data.get("source"),
        )
        return jsonify(_serialize_obligation(obligation)), 201

    return jsonify([_serialize_obligation(o) for o in Obligation.query.all()])


@bp.route("/goals", methods=["GET", "POST"])
def goals():
    if request.method == "POST":
        data = request.get_json(force=True)
        goal = services.create_goal(
            title=data["title"],
            estimated_total_effort_minutes=int(data["estimated_total_effort_minutes"]),
            soft_target_date=_parse_target_datetime(data["soft_target_date"]),
        )
        return jsonify(_serialize_goal(goal)), 201

    return jsonify([_serialize_goal(g) for g in Goal.query.all()])


# Note: goal-related scheduled blocks reuse the existing
# /schedule/<block_id>/push and /schedule/<block_id>/done routes below - they
# operate on a block id and delegate to the scheduler, which now handles goal
# blocks identically to obligation blocks. No goal-specific push/done routes.


@bp.route("/capture", methods=["POST"])
def capture():
    """Free-text capture: raw text in, one parsed-and-created record out.

    Parses with the LLM, applies defaults (never blocks on missing info), creates
    the matching record via the same services the forms use, and returns a brief
    confirmation of what it understood.
    """
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        abort(400, description="empty capture text")
    try:
        result = capture_service.capture(text)
    except capture_service.CaptureError as exc:
        abort(502, description=str(exc))
    return jsonify(result), 201


@bp.route("/schedule/right-now", methods=["GET"])
def right_now():
    return jsonify(_serialize_block(scheduler.get_right_now()))


@bp.route("/schedule/run", methods=["POST"])
def run_schedule():
    blocks = scheduler.run_scheduler()
    return jsonify([_serialize_block(b) for b in blocks])


@bp.route("/schedule/<int:block_id>/push", methods=["POST"])
def push(block_id):
    data = request.get_json(silent=True) or {}
    minutes = int(data.get("minutes", scheduler.DEFAULT_PUSH_MINUTES))
    try:
        scheduler.push_block(block_id, push_minutes=minutes)
    except ValueError as exc:
        abort(400, description=str(exc))
    return jsonify(_serialize_block(scheduler.get_right_now()))


@bp.route("/schedule/<int:block_id>/done", methods=["POST"])
def done(block_id):
    data = request.get_json(silent=True) or {}
    actual_minutes = data.get("actual_minutes")
    try:
        scheduler.mark_done(block_id, actual_minutes=actual_minutes)
    except ValueError as exc:
        abort(400, description=str(exc))
    return jsonify(_serialize_block(scheduler.get_right_now()))
