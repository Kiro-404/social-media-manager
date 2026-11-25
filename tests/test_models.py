from app.models import Niche, Platform, PlatformAccount


def test_create_niche(db_session):
    niche = Niche(name="Fitness tips", description="Home workouts", language="ar")
    db_session.add(niche)
    db_session.commit()
    db_session.refresh(niche)

    assert niche.id is not None
    assert niche.name == "Fitness tips"
    assert niche.language == "ar"


def test_create_platform_account(db_session):
    account = PlatformAccount(platform=Platform.YOUTUBE, display_name="My channel")
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    assert account.id is not None
    assert account.platform == Platform.YOUTUBE
    assert account.is_active is True
