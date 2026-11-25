import pytest

from app.models import Platform
from app.publishing.instagram_publisher import InstagramPublisher
from app.publishing.publisher_factory import get_publisher
from app.publishing.tiktok_publisher import TikTokPublisher
from app.publishing.twitter_publisher import TwitterPublisher
from app.publishing.youtube_publisher import YouTubePublisher


@pytest.mark.parametrize(
    "platform,expected_cls",
    [
        (Platform.YOUTUBE, YouTubePublisher),
        (Platform.INSTAGRAM, InstagramPublisher),
        (Platform.TIKTOK, TikTokPublisher),
        (Platform.TWITTER, TwitterPublisher),
    ],
)
def test_get_publisher_returns_correct_type(platform, expected_cls):
    publisher = get_publisher(platform)
    assert isinstance(publisher, expected_cls)


def test_publish_without_credentials_fails_gracefully(db_session):
    """Every publisher must return a PublishResult, never raise, on missing config."""
    from app.models import ContentIdea, ContentPiece, Niche, PlatformAccount

    niche = Niche(name="Test niche")
    db_session.add(niche)
    db_session.commit()
    db_session.refresh(niche)

    idea = ContentIdea(niche_id=niche.id, title="t", caption="c", hashtags="#h")
    db_session.add(idea)
    db_session.commit()
    db_session.refresh(idea)

    piece = ContentPiece(idea_id=idea.id, video_path="")
    account = PlatformAccount(platform=Platform.TIKTOK)

    publisher = TikTokPublisher()
    result = publisher.publish(piece, account, caption="hello", hashtags="#x")

    assert result.success is False
    assert result.error_message  # some explanatory message, not a raised exception
