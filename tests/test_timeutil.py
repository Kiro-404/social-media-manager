import datetime as dt

from app.timeutil import to_utc_naive, utc_naive_to_iso


def test_naive_local_time_is_converted_to_utc():
    # Cairo is UTC+2 in winter (no DST in late November).
    local = dt.datetime(2026, 11, 26, 18, 0)
    assert to_utc_naive(local, "Africa/Cairo") == dt.datetime(2026, 11, 26, 16, 0)


def test_aware_time_is_converted_exactly_regardless_of_tz_name():
    aware = dt.datetime(2026, 11, 26, 18, 0, tzinfo=dt.timezone.utc)
    assert to_utc_naive(aware, "Africa/Cairo") == dt.datetime(2026, 11, 26, 18, 0)


def test_result_is_naive():
    assert to_utc_naive(dt.datetime(2026, 1, 1, 0, 0), "UTC").tzinfo is None


def test_iso_serialisation_has_explicit_z():
    assert utc_naive_to_iso(dt.datetime(2026, 11, 26, 16, 0, 5, 123)) == "2026-11-26T16:00:05Z"
