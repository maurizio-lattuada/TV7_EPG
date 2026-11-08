"""Computation of the time range the guide should cover."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Europe/Zurich"


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """Half-open interval ``[start, end)`` with timezone-aware bounds."""

    start: datetime
    end: datetime

    def overlaps(self, start: datetime, stop: datetime) -> bool:
        """True if a programme running ``[start, stop)`` is at least partly inside."""
        return start < self.end and stop > self.start


def build_window(
    days_back: int,
    days_ahead: int,
    tz_name: str = DEFAULT_TIMEZONE,
    now: datetime | None = None,
) -> TimeWindow:
    """Return the window from local midnight ``days_back`` days ago up to the end
    of the local day ``days_ahead`` days from today.

    Calendar arithmetic is done on local dates, so days that are 23 or 25 hours
    long because of daylight saving changes are handled correctly.
    """
    if days_back < 0 or days_ahead < 0:
        raise ValueError("days_back and days_ahead must not be negative")

    tz = ZoneInfo(tz_name)
    today = (now or datetime.now(UTC)).astimezone(tz).date()
    first_day = today - timedelta(days=days_back)
    day_after_last = today + timedelta(days=days_ahead + 1)
    return TimeWindow(
        start=datetime.combine(first_day, time.min, tzinfo=tz),
        end=datetime.combine(day_after_last, time.min, tzinfo=tz),
    )
