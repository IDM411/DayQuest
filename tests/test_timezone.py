"""Regression tests for the local-timezone scheduling fix.

The bug: the scheduler computed "now" with datetime.utcnow() but applied an
8:00-22:00 *window* to it. For a user in US Eastern, an evening that is still
well inside their waking day can fall outside the 8-22 UTC window (evening
Eastern is past midnight UTC), so nothing gets scheduled for their actual
present moment and "Right Now" goes empty.

These tests pin the real clock (via the timeutils._utc_now seam) to an instant
that is evening in Eastern but past-midnight in UTC, then exercise the default
"now" path the app actually uses in production (now=None).
"""

from datetime import datetime, timedelta, timezone

from app import scheduler, timeutils

# 2026-06-18 00:00 UTC == 2026-06-17 20:00 EDT (Eastern is UTC-4 in June).
# Evening Eastern, comfortably inside an 8-22 local window; outside 8-22 UTC.
EVENING_EASTERN_AS_UTC = datetime(2026, 6, 18, 0, 0, tzinfo=timezone.utc)


def _pin_clock(monkeypatch, utc_instant):
    monkeypatch.setattr(timeutils, "_utc_now", lambda: utc_instant)


def test_local_now_converts_utc_to_configured_eastern(app, monkeypatch):
    app.config["LOCAL_TIMEZONE"] = "America/New_York"
    _pin_clock(monkeypatch, EVENING_EASTERN_AS_UTC)

    # The naive wall-clock "now" must be 8 PM Eastern, not midnight UTC.
    assert timeutils.local_now() == datetime(2026, 6, 17, 20, 0)


def test_local_timezone_is_configurable_not_hardcoded(app, monkeypatch):
    _pin_clock(monkeypatch, EVENING_EASTERN_AS_UTC)

    # Same instant, a different configured zone -> a different wall clock.
    app.config["LOCAL_TIMEZONE"] = "America/Los_Angeles"  # UTC-7 in June
    assert timeutils.local_now() == datetime(2026, 6, 17, 17, 0)

    app.config["LOCAL_TIMEZONE"] = "UTC"
    assert timeutils.local_now() == datetime(2026, 6, 18, 0, 0)


def test_right_now_not_empty_in_local_evening_default_path(app, monkeypatch, make_obligation):
    """The core regression: evening-Eastern via the production default-now path.

    Under the old UTC logic, "now" would be 2026-06-18 00:00 UTC, which makes an
    obligation due at 22:00 *local that same evening* look already-past (its
    naive deadline 2026-06-17 22:00 < 2026-06-18 00:00), so it is dropped and
    get_right_now() returns None -> the empty screen. With local time, "now" is
    2026-06-17 20:00 and the task schedules into the present evening.
    """
    app.config["LOCAL_TIMEZONE"] = "America/New_York"
    _pin_clock(monkeypatch, EVENING_EASTERN_AS_UTC)

    now_local = timeutils.local_now()
    assert now_local.hour == 20  # sanity: evening, inside the 8-22 local window

    # Due two hours from now, this evening. Scheduled via the DEFAULT now path.
    make_obligation("Evening study", deadline=now_local + timedelta(hours=2), effort_minutes=60)
    scheduler.run_scheduler()  # now=None -> local_now()

    block = scheduler.get_right_now()  # now=None -> local_now()
    assert block is not None, "Right Now is empty in the local evening (the bug)"
    assert block.start_time == now_local  # starts now, in the local evening
    assert block.start_time.hour == 20


def test_window_opens_at_local_morning_not_utc_morning(app, monkeypatch, make_obligation):
    """Work scheduled the next day should open at 08:00 *local*, not 08:00 UTC.

    Pinned to late local evening (23:30 Eastern) with a deadline two days out,
    so the fresh day's first slot lands at the next local morning.
    """
    app.config["LOCAL_TIMEZONE"] = "America/New_York"
    # 2026-06-18 03:30 UTC == 2026-06-17 23:30 EDT (after the 22:00 cutoff).
    _pin_clock(monkeypatch, datetime(2026, 6, 18, 3, 30, tzinfo=timezone.utc))

    now_local = timeutils.local_now()
    assert (now_local.hour, now_local.minute) == (23, 30)

    make_obligation("Tomorrow task", deadline=now_local + timedelta(days=2), effort_minutes=60)
    scheduler.run_scheduler()

    block = scheduler.get_right_now()
    assert block is not None
    # First available slot is the next local morning at 08:00.
    assert block.start_time == datetime(2026, 6, 18, 8, 0)
