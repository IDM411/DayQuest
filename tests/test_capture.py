"""Tests for free-text capture (Phase 3).

The live LLM call is non-deterministic and needs network/credentials, so these
tests inject `parse` with the structured JSON Claude Haiku would return for each
example input, then assert the deterministic half — classification routing,
defaulting, record creation, and the confirmation summary. `normalize_capture`
is also tested directly for the default rules.
"""

from datetime import datetime, time, timedelta

from app import capture as cap
from app.models import FixedCommitment, Goal, Obligation

# 2026-06-17 09:00 — a Wednesday (weekday() == 2).
WEDNESDAY = datetime(2026, 6, 17, 9, 0, 0)


def _parse(payload):
    """A fake LLM parser that returns a fixed structured payload."""
    return lambda text: dict(payload)


# ---------------------------------------------------------------------------
# normalize_capture — defaulting rules (pure, no DB)
# ---------------------------------------------------------------------------

def test_normalize_obligation_defaults_effort_and_first_step(app):
    plan = cap.normalize_capture(
        {"classification": "obligation", "title": "Report", "deadline": "2026-06-18"},
        WEDNESDAY,
    )
    assert plan["kind"] == "obligation"
    assert plan["effort_minutes"] == cap.DEFAULT_EFFORT_MINUTES  # missing -> 60
    assert plan["first_step"].startswith("Make a start")          # missing -> generated
    assert plan["deadline"].date() == datetime(2026, 6, 18).date()


def test_normalize_goal_defaults_target_to_14_days(app):
    plan = cap.normalize_capture(
        {"classification": "goal", "title": "Learn X", "effort_minutes": 300},
        WEDNESDAY,
    )
    assert plan["kind"] == "goal"
    assert plan["effort_minutes"] == 300
    # No soft target stated -> 14 days out.
    assert plan["soft_target_date"].date() == (WEDNESDAY + timedelta(days=14)).date()


def test_normalize_missing_classification_infers_from_deadline(app):
    with_deadline = cap.normalize_capture({"title": "X", "deadline": "2026-07-01"}, WEDNESDAY)
    without_deadline = cap.normalize_capture({"title": "Y"}, WEDNESDAY)
    assert with_deadline["kind"] == "obligation"
    assert without_deadline["kind"] == "goal"


# ---------------------------------------------------------------------------
# capture() — the three example inputs the user would actually type
# ---------------------------------------------------------------------------

def test_capture_report_due_thursday_makes_obligation(app):
    parsed = {
        "classification": "obligation",
        "title": "Report",
        "deadline": "2026-06-18",          # the upcoming Thursday
        "first_step": "Open the doc and write the title",
        "effort_minutes": None,            # not mentioned
    }
    result = cap.capture("report due thursday", now=WEDNESDAY, parse=_parse(parsed))

    assert result["classification"] == "obligation"
    obligations = Obligation.query.all()
    assert len(obligations) == 1
    o = obligations[0]
    assert o.title == "Report"
    assert o.estimated_effort_minutes == 60  # defaulted
    assert o.deadline.date() == datetime(2026, 6, 18).date()
    assert "obligation" in result["summary"].lower()


def test_capture_gym_mon_wed_fri_makes_three_fixed_commitments(app):
    parsed = {
        "classification": "fixed_commitment",
        "title": "Gym",
        "days_of_week": [0, 2, 4],
        "start_time": "17:00",             # "5 to 6" -> 17:00-18:00
        "end_time": "18:00",
    }
    result = cap.capture("gym mon wed fri 5 to 6", now=WEDNESDAY, parse=_parse(parsed))

    assert result["classification"] == "fixed_commitment"
    commitments = FixedCommitment.query.order_by(FixedCommitment.day_of_week).all()
    assert [c.day_of_week for c in commitments] == [0, 2, 4]
    assert all(c.recurring for c in commitments)
    assert commitments[0].start_time == time(17, 0)
    assert commitments[0].end_time == time(18, 0)


def test_capture_learn_kubernetes_makes_goal(app):
    parsed = {
        "classification": "goal",
        "title": "Learn Kubernetes",
        "effort_minutes": 300,             # "maybe 5 hours"
        "soft_target_date": "2026-06-30",  # "sometime this month"
    }
    result = cap.capture(
        "learn kubernetes sometime this month, maybe 5 hours",
        now=WEDNESDAY,
        parse=_parse(parsed),
    )

    assert result["classification"] == "goal"
    goals = Goal.query.all()
    assert len(goals) == 1
    g = goals[0]
    assert g.title == "Learn Kubernetes"
    assert g.estimated_total_effort_minutes == 300
    assert g.soft_target_date.date() == datetime(2026, 6, 30).date()
    assert g.status == "active"


def test_capture_goal_with_no_effort_or_date_uses_defaults(app):
    parsed = {"classification": "goal", "title": "Read more books"}
    cap.capture("read more books", now=WEDNESDAY, parse=_parse(parsed))

    g = Goal.query.one()
    assert g.estimated_total_effort_minutes == 60                       # default effort
    assert g.soft_target_date.date() == (WEDNESDAY + timedelta(days=14)).date()


# ---------------------------------------------------------------------------
# /api/capture route — uses the live parser path, monkeypatched
# ---------------------------------------------------------------------------

def test_capture_route_creates_record_and_returns_summary(app, monkeypatch):
    monkeypatch.setattr(
        cap,
        "parse_with_llm",
        lambda text: {
            "classification": "goal",
            "title": "Practice piano",
            "effort_minutes": 120,
            "soft_target_date": "2026-07-15",
        },
    )
    client = app.test_client()
    res = client.post("/api/capture", json={"text": "practice piano this summer, ~2h"})

    assert res.status_code == 201
    body = res.get_json()
    assert body["classification"] == "goal"
    assert "summary" in body and body["summary"]
    assert Goal.query.count() == 1


def test_capture_route_rejects_empty_text(app):
    client = app.test_client()
    res = client.post("/api/capture", json={"text": "   "})
    assert res.status_code == 400
