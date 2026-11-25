import datetime as dt
from types import SimpleNamespace as NS

from app.trends.selection import pick_default_trend

T0 = dt.datetime(2026, 11, 25, 12, 0)


def t(source, score, minutes=0, kw=""):
    return NS(source=source, score=score, fetched_at=T0 + dt.timedelta(minutes=minutes), keyword=kw or f"{source}-{score}")


def test_empty():
    assert pick_default_trend([]) is None


def test_not_biased_toward_source_with_bigger_numbers():
    # YouTube views dwarf Google rank scores; the top Google trend should still compete fairly.
    items = [t("youtube", 5_000_000, kw="yt-top"), t("youtube", 1_000_000), t("google_trends", 10, kw="g-top"), t("google_trends", 3)]
    # Both tops are 100% of their source; tie broken by raw score -> youtube. Lower ones must never win.
    assert pick_default_trend(items).keyword in {"yt-top", "g-top"}


def test_ignores_old_batches():
    old = t("google_trends", 999, minutes=-120, kw="old")
    new = t("google_trends", 5, minutes=0, kw="new")
    assert pick_default_trend([old, new]).keyword == "new"


def test_weakest_trend_is_not_picked_just_because_it_was_inserted_last():
    items = [t("youtube", 9_000_000, kw="best"), t("youtube", 10_000, kw="weak-inserted-last")]
    assert pick_default_trend(items).keyword == "best"
