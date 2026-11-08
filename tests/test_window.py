from datetime import UTC, datetime

import pytest

from tv7_epg.window import build_window


def test_default_window_is_yesterday_to_end_of_today_plus_three():
    # 00:30 UTC on 8 Nov = 01:30 in Zurich (CET), so "today" is 8 Nov.
    window = build_window(1, 3, now=datetime(2026, 11, 8, 0, 30, tzinfo=UTC))
    assert window.start.isoformat() == "2026-11-07T00:00:00+01:00"
    assert window.end.isoformat() == "2026-11-12T00:00:00+01:00"


def test_today_is_determined_in_local_time():
    # 23:30 UTC on 7 Nov is already 8 Nov in Zurich.
    window = build_window(0, 0, now=datetime(2026, 11, 7, 23, 30, tzinfo=UTC))
    assert window.start.date().isoformat() == "2026-11-08"


def test_daylight_saving_change_inside_window():
    # Summer time ends on 25 Oct 2026; the bounds keep their local offsets.
    window = build_window(1, 3, now=datetime(2026, 10, 24, 12, 0, tzinfo=UTC))
    assert window.start.isoformat() == "2026-10-23T00:00:00+02:00"
    assert window.end.isoformat() == "2026-10-28T00:00:00+01:00"
    # Python subtracts same-zone datetimes on wall time, so compare in UTC.
    elapsed = window.end.astimezone(UTC) - window.start.astimezone(UTC)
    assert elapsed.total_seconds() == (5 * 24 + 1) * 3600


def test_overlap_keeps_programmes_crossing_the_edges():
    window = build_window(0, 0, now=datetime(2026, 11, 8, 12, 0, tzinfo=UTC))
    before = datetime(2026, 11, 7, 22, 0, tzinfo=UTC)  # 23:00 local
    edge = datetime(2026, 11, 7, 23, 0, tzinfo=UTC)  # 00:00 local
    after = datetime(2026, 11, 7, 23, 30, tzinfo=UTC)
    assert window.overlaps(before, after)
    assert not window.overlaps(before, edge)


def test_negative_days_are_rejected():
    with pytest.raises(ValueError):
        build_window(-1, 3)
