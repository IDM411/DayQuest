"""Local wall-clock time for the scheduler.

The whole scheduler reasons in one timezone's wall-clock time: stored deadlines
and soft target dates are the user's local times, the 8-22 working window is
local, and so "now" must be local too. Computing "now" in UTC (the old bug) made
the window misalign with the user's real day, so "Right Now" could go empty
during normal waking hours.

Everything downstream uses naive datetimes, so we return naive local time -
the wall-clock reading in the configured zone, tzinfo stripped - which composes
directly with the stored naive datetimes.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context

DEFAULT_TIMEZONE = "America/New_York"


def local_timezone():
    """The configured local timezone (falls back to Eastern outside app context)."""
    tz_name = DEFAULT_TIMEZONE
    if has_app_context():
        tz_name = current_app.config.get("LOCAL_TIMEZONE", DEFAULT_TIMEZONE)
    return ZoneInfo(tz_name)


def _utc_now():
    """The real current instant as timezone-aware UTC.

    Isolated so tests can pin the clock to a specific moment.
    """
    return datetime.now(timezone.utc)


def local_now():
    """Current wall-clock time in the configured local timezone, as naive datetime."""
    return _utc_now().astimezone(local_timezone()).replace(tzinfo=None)
