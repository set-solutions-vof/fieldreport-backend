from datetime import UTC, datetime
from uuid import uuid4

from src.db.onboarding_mapper import map_company, map_created_invite, map_invite
from src.models.onboarding import CompanyOnboarding, InviteCreated, InviteRecord


def test_map_company_returns_company_response() -> None:
    company_id = uuid4()

    company = map_company(
        {
            "id": company_id,
            "name": "LEKK BV",
            "logo_url": None,
            "primary_color": "#3B5BDB",
            "onboarding_completed": True,
        }
    )

    assert company == CompanyOnboarding(
        id=company_id,
        name="LEKK BV",
        logo_url=None,
        primary_color="#3B5BDB",
        onboarding_completed=True,
    )


def test_map_created_invite_returns_created_invite_response() -> None:
    invite_id = uuid4()
    created_at = datetime.now(UTC)

    invite = map_created_invite(
        {
            "id": invite_id,
            "email": "new.user@lekk.nl",
            "role": "admin",
            "created_at": created_at,
        },
    )

    assert invite == InviteCreated(
        id=invite_id,
        email="new.user@lekk.nl",
        role="admin",
        created_at=created_at,
    )


def test_map_invite_returns_invite_response() -> None:
    invite_id = uuid4()
    created_at = datetime.now(UTC)
    expires_at = datetime.now(UTC)

    invite = map_invite(
        {
            "id": invite_id,
            "email": "new.user@lekk.nl",
            "role": "inspector",
            "is_accepted": False,
            "created_at": created_at,
            "expires_at": expires_at,
        }
    )

    assert invite == InviteRecord(
        id=invite_id,
        email="new.user@lekk.nl",
        role="inspector",
        is_accepted=False,
        created_at=created_at,
        expires_at=expires_at,
    )
