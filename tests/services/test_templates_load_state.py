from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.models.templates import status_resolver
from src.models.templates.configuration import TemplateStatusNotConfigured
from src.services import templates as templates_service


async def test_load_template_configuration_fetches_and_resolves() -> None:
    company_id = str(uuid4())
    expected = TemplateStatusNotConfigured(status="not_configured")

    with (
        patch.object(
            templates_service.template_queries,
            "fetch_template_configuration_context",
            AsyncMock(return_value=(None, None)),
        ) as fetch_context,
        patch.object(
            status_resolver,
            "resolve_template_company_state",
            return_value=expected,
        ) as resolve_state,
    ):
        result = await templates_service.load_template_configuration(company_id)

    assert result is expected
    fetch_context.assert_awaited_once_with(company_id)
    resolve_state.assert_called_once_with(None, None)
