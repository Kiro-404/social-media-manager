"""API-level tests: scheduling timezone handling, retry/cancel, idea review endpoints."""
from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ContentIdea, ContentPiece, Niche, Platform, PlatformAccount, PostResult, PostStatus, ScheduledPost


@pytest.fixture()
def client_and_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # No `with` block -> lifespan (DB init + background scheduler) is not started.
    client = TestClient(app)
    session = Session()
    try:
        yield client, session
    finally:
        session.close()
        app.dependency_overrides.clear()
        engine.dispose()


def _seed(session):
    niche = Niche(name="Fitness", language="ar")
    session.add(niche)
    session.flush()
    idea = ContentIdea(niche_id=niche.id, title="Idea", script="s", caption="c", hashtags="#x")
    session.add(idea)
    session.flush()
    piece = ContentPiece(idea_id=idea.id)
    account = PlatformAccount(platform=Platform.YOUTUBE, display_name="Chan")
    session.add_all([piece, account])
    session.commit()
    return idea, piece, account


def test_naive_schedule_time_is_stored_as_utc(client_and_session):
    client, session = client_and_session
    _, piece, account = _seed(session)

    # Local Cairo wall-clock time a day from now (naive, as the dashboard sends it).
    local = (dt.datetime.utcnow() + dt.timedelta(days=1)).replace(microsecond=0, second=0)
    resp = client.post("/schedule", json={"content_piece_id": piece.id, "account_id": account.id, "scheduled_for": local.isoformat()})
    assert resp.status_code == 200

    stored = session.query(ScheduledPost).one().scheduled_for
    # Settings default TIMEZONE is Africa/Cairo (UTC+2 in winter, UTC+3 in summer) -> stored is earlier than the naive input.
    assert stored < local
    assert resp.json()["scheduled_for"].endswith("Z")


def test_scheduling_in_the_past_is_rejected(client_and_session):
    client, session = client_and_session
    _, piece, account = _seed(session)
    resp = client.post(
        "/schedule",
        json={"content_piece_id": piece.id, "account_id": account.id, "scheduled_for": "2000-01-01T00:00:00Z"},
    )
    assert resp.status_code == 400


def test_retry_only_works_on_failed_and_clears_old_result(client_and_session):
    client, session = client_and_session
    _, piece, account = _seed(session)
    post = ScheduledPost(content_piece_id=piece.id, account_id=account.id, scheduled_for=dt.datetime.utcnow(), status=PostStatus.FAILED)
    session.add(post)
    session.flush()
    session.add(PostResult(scheduled_post_id=post.id, success=False, error_message="boom"))
    session.commit()

    resp = client.post(f"/schedule/{post.id}/retry")
    assert resp.status_code == 200
    session.expire_all()
    assert session.query(PostResult).count() == 0  # UNIQUE(scheduled_post_id) would otherwise block the next attempt
    assert session.get(ScheduledPost, post.id).status == PostStatus.QUEUED

    # Now QUEUED -> a second retry is refused.
    assert client.post(f"/schedule/{post.id}/retry").status_code == 409


def test_list_schedule_includes_display_fields(client_and_session):
    client, session = client_and_session
    _, piece, account = _seed(session)
    session.add(ScheduledPost(content_piece_id=piece.id, account_id=account.id, scheduled_for=dt.datetime.utcnow() + dt.timedelta(hours=1)))
    session.commit()

    rows = client.get("/schedule").json()
    assert rows[0]["platform"] == "youtube"
    assert rows[0]["idea_title"] == "Idea"
    assert rows[0]["status"] == "queued"


def test_edit_and_delete_idea(client_and_session):
    client, session = client_and_session
    idea, piece, _ = _seed(session)

    resp = client.patch(f"/content/ideas/{idea.id}", json={"title": "Edited"})
    assert resp.status_code == 200 and resp.json()["title"] == "Edited"
    assert resp.json()["caption"] == "c"  # untouched fields stay as they were

    # Has a generated piece -> cannot delete.
    assert client.delete(f"/content/ideas/{idea.id}").status_code == 409

    session.delete(session.get(ContentPiece, piece.id))
    session.commit()
    assert client.delete(f"/content/ideas/{idea.id}").status_code == 200


def test_stats(client_and_session):
    client, session = client_and_session
    _seed(session)
    stats = client.get("/stats").json()
    assert stats["niches"] == 1 and stats["accounts"] == 1 and stats["ideas"] == 1 and stats["pieces"] == 1
