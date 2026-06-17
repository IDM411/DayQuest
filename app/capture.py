"""Free-text capture (PRD Phase 3): natural language -> one structured record.

A single line of text is sent to Claude Haiku, which returns structured fields
via a forced tool call. We then apply defaults (never blocking on missing info,
per the PRD's "never make the user choose" rule) and create the matching record
through the same services the manual forms use.

The LLM call (`parse_with_llm`) is deliberately separated from the deterministic
normalization (`normalize_capture`) and creation, so the defaulting/creation
pipeline is unit-testable without a live model.
"""

from datetime import date as date_cls
from datetime import datetime, time, timedelta

import anthropic
from flask import current_app, has_app_context

from . import scheduler, services
from .timeutils import local_now

DEFAULT_MODEL = "claude-haiku-4-5"

# Defaults applied when the text omits a field - reasonable assumptions so
# capture never has to ask the user anything.
DEFAULT_EFFORT_MINUTES = 60
GOAL_DEFAULT_WINDOW_DAYS = 14
OBLIGATION_DEFAULT_WINDOW_DAYS = 7
DEFAULT_COMMITMENT_START = time(9, 0)
DEFAULT_COMMITMENT_END = time(10, 0)

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class CaptureError(Exception):
    """Raised when the LLM call or parsing fails (surfaced as a 502 to the client)."""


# --- LLM contract --------------------------------------------------------

CAPTURE_TOOL = {
    "name": "record_capture",
    "description": "Record the structured interpretation of the user's input.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "A short title for the task, goal, or commitment.",
            },
            "classification": {
                "type": "string",
                "enum": ["fixed_commitment", "obligation", "goal"],
                "description": (
                    "fixed_commitment = recurring day/time block; "
                    "obligation = has a hard deadline; "
                    "goal = open-ended / soft or no timeframe."
                ),
            },
            "first_step": {
                "type": ["string", "null"],
                "description": "For an obligation, a tiny literal first action. Else null.",
            },
            "deadline": {
                "type": ["string", "null"],
                "description": "Hard deadline as ISO 8601 date or datetime, if one is stated. Else null.",
            },
            "effort_minutes": {
                "type": ["integer", "null"],
                "description": "Estimated effort in minutes if stated (convert hours). Else null.",
            },
            "days_of_week": {
                "type": ["array", "null"],
                "items": {"type": "integer"},
                "description": "For a fixed_commitment: weekdays as 0=Mon..6=Sun. Else null.",
            },
            "start_time": {
                "type": ["string", "null"],
                "description": "For a fixed_commitment: 24h start time 'HH:MM'. Else null.",
            },
            "end_time": {
                "type": ["string", "null"],
                "description": "For a fixed_commitment: 24h end time 'HH:MM'. Else null.",
            },
            "soft_target_date": {
                "type": ["string", "null"],
                "description": "For a goal: loosely targeted ISO date, if any. Else null.",
            },
        },
        "required": ["title", "classification"],
    },
}

SYSTEM_PROMPT_TEMPLATE = """You convert a single line of natural language into one structured item for a personal planner. Today is {today} ({weekday}); resolve relative dates ("thursday", "next week", "this month") against it.

Classify the input as exactly one of:
- "fixed_commitment": a recurring or fixed day/time block (e.g. "gym mon wed fri 5 to 6", "class tuesdays 10am"). Set days_of_week (0=Mon..6=Sun) and start_time/end_time as 24h "HH:MM".
- "obligation": something with a hard deadline (e.g. "report due thursday", "submit by the 15th"). Set deadline (ISO date or datetime) and a tiny literal first_step.
- "goal": an open-ended ambition with a soft or absent timeframe (e.g. "learn kubernetes sometime this month, maybe 5 hours"). Set soft_target_date (ISO date) if one is implied.

Always set a short title. Set effort_minutes when any duration/effort is mentioned (convert hours to minutes). Use null for anything not stated - do not invent values. Respond by calling the record_capture tool."""


def parse_with_llm(text):
    """Send raw text to Claude Haiku and return the structured fields as a dict."""
    now = local_now()
    system = SYSTEM_PROMPT_TEMPLATE.format(
        today=now.strftime("%Y-%m-%d"), weekday=now.strftime("%A")
    )
    model = DEFAULT_MODEL
    if has_app_context():
        model = current_app.config.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=512,
            system=system,
            tools=[CAPTURE_TOOL],
            tool_choice={"type": "tool", "name": "record_capture"},
            messages=[{"role": "user", "content": text}],
        )
    except anthropic.AnthropicError as exc:
        raise CaptureError(f"LLM request failed: {exc}") from exc

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_capture":
            return dict(block.input)
    raise CaptureError("LLM did not return a structured capture")


# --- Deterministic normalization (pure, unit-tested) ---------------------

def _parse_dt(value):
    """Parse an ISO date or datetime string; a bare date anchors to end of day. None on failure."""
    if not value:
        return None
    try:
        if len(value) == 10:
            return datetime.combine(date_cls.fromisoformat(value), time(23, 59))
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_time(value):
    if not value:
        return None
    try:
        return time.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def normalize_capture(parsed, now):
    """Turn raw LLM fields into a fully-defaulted plan dict ready to create.

    Applies the PRD defaults: missing effort -> 60 min; a goal with no target ->
    14 days out; an obligation with no deadline -> 7 days out; a commitment with
    no day/time -> today, 09:00-10:00.
    """
    title = (parsed.get("title") or "Untitled").strip()
    classification = (parsed.get("classification") or "").strip()
    if classification not in ("fixed_commitment", "obligation", "goal"):
        # Infer per the PRD rule: a hard deadline means obligation, else goal.
        classification = "obligation" if parsed.get("deadline") else "goal"

    raw_effort = parsed.get("effort_minutes")
    effort = int(raw_effort) if raw_effort else DEFAULT_EFFORT_MINUTES

    if classification == "goal":
        soft_target = _parse_dt(parsed.get("soft_target_date")) or (
            now + timedelta(days=GOAL_DEFAULT_WINDOW_DAYS)
        )
        return {
            "kind": "goal",
            "title": title,
            "effort_minutes": effort,
            "soft_target_date": soft_target,
        }

    if classification == "fixed_commitment":
        days = parsed.get("days_of_week") or [now.weekday()]
        days = [int(d) for d in days]
        return {
            "kind": "fixed_commitment",
            "title": title,
            "days_of_week": days,
            "start_time": _parse_time(parsed.get("start_time")) or DEFAULT_COMMITMENT_START,
            "end_time": _parse_time(parsed.get("end_time")) or DEFAULT_COMMITMENT_END,
        }

    deadline = _parse_dt(parsed.get("deadline")) or (
        now + timedelta(days=OBLIGATION_DEFAULT_WINDOW_DAYS)
    )
    first_step = (parsed.get("first_step") or f"Make a start on: {title}").strip()
    return {
        "kind": "obligation",
        "title": title,
        "effort_minutes": effort,
        "deadline": deadline,
        "first_step": first_step,
    }


# --- Creation + confirmation ---------------------------------------------

def _create_from_plan(plan):
    kind = plan["kind"]
    if kind == "obligation":
        services.create_obligation(
            title=plan["title"],
            first_step=plan["first_step"],
            deadline=plan["deadline"],
            estimated_effort_minutes=plan["effort_minutes"],
            source="capture",
        )
    elif kind == "goal":
        services.create_goal(
            title=plan["title"],
            estimated_total_effort_minutes=plan["effort_minutes"],
            soft_target_date=plan["soft_target_date"],
        )
    elif kind == "fixed_commitment":
        # A recurring commitment across several days is several rows; create them
        # all, then reschedule once.
        for day in plan["days_of_week"]:
            services.create_fixed_commitment(
                title=plan["title"],
                recurring=True,
                day_of_week=day,
                specific_date=None,
                start_time=plan["start_time"],
                end_time=plan["end_time"],
                reschedule=False,
            )
        scheduler.run_scheduler()


def _fmt_day(dt):
    return f"{dt.strftime('%b')} {dt.day}"  # cross-platform (avoids %-d)


def _fmt_effort(minutes):
    if minutes >= 60:
        return f"~{minutes / 60:g} hrs"
    return f"~{minutes} min"


def _summary(plan):
    title = plan["title"]
    if plan["kind"] == "goal":
        return (
            f"Got it — added as a goal: \"{title}\", {_fmt_effort(plan['effort_minutes'])}, "
            f"target {_fmt_day(plan['soft_target_date'])}."
        )
    if plan["kind"] == "obligation":
        return (
            f"Got it — added as an obligation: \"{title}\", due {_fmt_day(plan['deadline'])}, "
            f"{_fmt_effort(plan['effort_minutes'])}. First step: {plan['first_step']}"
        )
    days = ", ".join(_DAY_NAMES[d] for d in plan["days_of_week"])
    return (
        f"Got it — added a fixed commitment: \"{title}\", {days} "
        f"{plan['start_time'].strftime('%H:%M')}–{plan['end_time'].strftime('%H:%M')}."
    )


def capture(text, now=None, parse=None):
    """Orchestrate the full capture: parse -> default -> create -> confirm.

    `now` and `parse` are injectable for testing; in production `parse` defaults
    to the live LLM call and `now` to local wall-clock time.
    """
    now = now or local_now()
    parse = parse or parse_with_llm
    parsed = parse(text)
    plan = normalize_capture(parsed, now)
    _create_from_plan(plan)
    return {
        "summary": _summary(plan),
        "classification": plan["kind"],
        "title": plan["title"],
    }
