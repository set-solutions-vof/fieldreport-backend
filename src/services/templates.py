from uuid import uuid4

from src.db.template import queries
from src.exceptions import TemplateConfirmationNotAllowed
from src.models.auth.authentication import CurrentUser
from src.models.templates import status_resolver
from src.models.templates.configuration import (
    TemplateStatus,
    TemplateStatusActive,
)
from src.models.templates.domain import TemplateStructure


async def load_template_configuration(company_id: str) -> TemplateStatus:
    active_template = await queries.fetch_optional_active_company_template(company_id)

    return status_resolver.resolve_template_company_state(active_template)


async def confirm_template(
    user: CurrentUser,
    structure: TemplateStructure,
) -> TemplateStatusActive:
    company_id = str(user.company_id)
    active_template = await queries.fetch_optional_active_company_template(company_id)

    if active_template is None:
        raise TemplateConfirmationNotAllowed()

    template_id = str(uuid4())
    await queries.create_template(company_id, template_id, structure, active_template.source_reports_count)
    await queries.set_active_template(company_id, template_id)

    active_template = await queries.fetch_active_company_template(company_id)

    return status_resolver.build_template_status_active(active_template)
