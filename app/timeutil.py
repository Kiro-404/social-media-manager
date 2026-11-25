"""
Time helpers. The database stores every datetime as *naive UTC*, and the
scheduler compares against ``datetime.utcnow()``. API clients, however, send
local wall-clock times (e.g. ``2026-11-26T18:00:00`` meaning 18:00 in Cairo).
Without conversion, that post would fire 2 hours late.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo


def to_utc_naive(value: dt.datetime, tz_name: str) -> dt.datetime:
    """
    Convert ``value`` to naive UTC.

    - tz-aware input (e.g. ``...Z`` or ``...+02:00``) is converted exactly.
    - naive input is interpreted as wall-clock time in ``tz_name``.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(tz_name))
    return value.astimezone(dt.timezone.utc).replace(tzinfo=None)


def utc_naive_to_iso(value: dt.datetime) -> str:
    """Serialise a naive-UTC datetime with an explicit ``Z`` so browsers parse it correctly."""
    return value.replace(microsecond=0).isoformat() + "Z"
