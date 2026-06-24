from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.exceptions import TemplateConfirmationNotAllowed
from src.models.auth.authentication import CurrentUser
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.records import ActiveCompanyTemplateRecord
from src.services import templates as templates_service

FIXED_TEMPLATE_CREATED_AT = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)


def build_active_template_record(
    *,
    template_id=None,
    structure: TemplateStructure | None = None,
    version: int = 1,
    source_reports_count: int = 0,
) -> ActiveCompanyTemplateRecord:
    return ActiveCompanyTemplateRecord(
        current_template_id=template_id if template_id is not None else uuid4(),
        structure=structure if structure is not None else TemplateStructure(sections=[]),
        created_at=FIXED_TEMPLATE_CREATED_AT,
        version=version,
        source_reports_count=source_reports_count,
    )


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="demo@fieldreport.local",
        first_name="Demo",
        last_name="User",
        role="admin",
    )


async def test_confirm_template_creates_and_activates_template() -> None:
    current_user = build_current_user()
    template_id = uuid4()
    sections = [
        TemplateSection(id="summary", label="Executive Summary", render_type="text_block"),
        TemplateSection(
            id="findings",
            label="Findings",
            render_type="key_value_table",
            fields=["Issue", "Action"],
        ),
    ]
    active_template = build_active_template_record(source_reports_count=3)

    with (
        patch.object(templates_service, "uuid4", side_effect=[template_id]),
        patch.object(
            templates_service.queries,
            "fetch_optional_active_company_template",
            AsyncMock(return_value=active_template),
        ),
        patch.object(
            templates_service.queries,
            "create_template",
            AsyncMock(),
        ) as create_template,
        patch.object(
            templates_service.queries,
            "set_active_template",
            AsyncMock(),
        ) as set_active_template,
        patch.object(
            templates_service.queries,
            "fetch_active_company_template",
            AsyncMock(
                return_value=build_active_template_record(
                    template_id=template_id,
                    structure=TemplateStructure(sections=sections),
                    version=3,
                    source_reports_count=3,
                )
            ),
        ),
    ):
        result = await templates_service.confirm_template(
            current_user, TemplateStructure(sections=sections)
        )

    assert result.model_dump(mode="json", exclude_none=True) == {
        "status": "active",
        "source_reports_count": 3,
        "metadata_fields": [],
        "template_id": str(template_id),
        "version": 3,
        "updated_at": FIXED_TEMPLATE_CREATED_AT.isoformat().replace("+00:00", "Z"),
        "sections": [
            {
                "id": "summary",
                "label": "Executive Summary",
                "order": 0,
                "render_type": "text_block",
                "found_in": 0,
            },
            {
                "id": "findings",
                "label": "Findings",
                "order": 0,
                "render_type": "key_value_table",
                "fields": ["Issue", "Action"],
                "found_in": 0,
            },
        ],
    }
    create_template.assert_awaited_once_with(
        str(current_user.company_id),
        str(template_id),
        TemplateStructure(sections=sections),
        3,
    )
    set_active_template.assert_awaited_once_with(str(current_user.company_id), str(template_id))


async def test_confirm_template_carries_forward_source_reports_count() -> None:
    current_user = build_current_user()
    template_id = uuid4()
    sections = [
        TemplateSection(id="summary", label="Updated Summary", render_type="text_block"),
    ]
    active_template = build_active_template_record(
        template_id=template_id,
        structure=TemplateStructure(sections=sections),
        version=2,
        source_reports_count=5,
    )

    with (
        patch.object(templates_service, "uuid4", side_effect=[template_id]),
        patch.object(
            templates_service.queries,
            "fetch_optional_active_company_template",
            AsyncMock(return_value=active_template),
        ),
        patch.object(
            templates_service.queries,
            "create_template",
            AsyncMock(),
        ) as create_template,
        patch.object(
            templates_service.queries,
            "set_active_template",
            AsyncMock(),
        ) as set_active_template,
        patch.object(
            templates_service.queries,
            "fetch_active_company_template",
            AsyncMock(
                return_value=build_active_template_record(
                    template_id=template_id,
                    structure=TemplateStructure(sections=sections),
                    version=2,
                    source_reports_count=5,
                )
            ),
        ),
    ):
        result = await templates_service.confirm_template(
            current_user, TemplateStructure(sections=sections)
        )

    assert result.status == "active"
    assert result.source_reports_count == 5
    assert result.version == 2
    assert result.sections == sections
    create_template.assert_awaited_once_with(
        str(current_user.company_id),
        str(template_id),
        TemplateStructure(sections=sections),
        5,
    )
    set_active_template.assert_awaited_once_with(str(current_user.company_id), str(template_id))


async def test_confirm_template_raises_when_no_active_template() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.queries,
        "fetch_optional_active_company_template",
        AsyncMock(return_value=None),
    ):
        with pytest.raises(TemplateConfirmationNotAllowed):
            await templates_service.confirm_template(current_user, TemplateStructure(sections=[]))


async def test_confirm_template_fetches_active_template_after_save() -> None:
    current_user = build_current_user()
    template_id = uuid4()
    active_template = build_active_template_record(template_id=template_id, source_reports_count=2)

    with (
        patch.object(templates_service, "uuid4", side_effect=[template_id]),
        patch.object(
            templates_service.queries,
            "fetch_optional_active_company_template",
            AsyncMock(return_value=active_template),
        ),
        patch.object(
            templates_service.queries,
            "fetch_active_company_template",
            AsyncMock(return_value=active_template),
        ) as fetch_active_template,
        patch.object(
            templates_service.queries,
            "create_template",
            AsyncMock(),
        ),
        patch.object(
            templates_service.queries,
            "set_active_template",
            AsyncMock(),
        ),
    ):
        await templates_service.confirm_template(current_user, TemplateStructure(sections=[]))

    fetch_active_template.assert_awaited_once_with(str(current_user.company_id))
