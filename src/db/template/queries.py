import sqlalchemy as sa

from src.db.connection import get_database
from src.db.schema.tables import company, templates
from src.db.template.mapper import (
    map_active_company_template,
    map_optional_active_company_template,
    parse_template_structure,
)
from src.models.templates.domain import TemplateStructure
from src.models.templates.records import ActiveCompanyTemplateRecord


async def fetch_active_company_template(company_id: str) -> ActiveCompanyTemplateRecord:
    async with get_database().acquire() as connection:
        company_row = await _fetch_active_company_template_row(connection, company_id)

    if company_row is None:
        raise RuntimeError(f"No active template found for company {company_id}")

    return map_active_company_template(company_row)


async def fetch_optional_active_company_template(
    company_id: str,
) -> ActiveCompanyTemplateRecord | None:
    async with get_database().acquire() as connection:
        company_row = await _fetch_optional_active_company_template_row(connection, company_id)

    return map_optional_active_company_template(company_row)


async def fetch_template_structure(template_id: str, company_id: str) -> TemplateStructure:
    statement = sa.select(templates.c.structure).where(
        templates.c.id == template_id,
        templates.c.company_id == company_id,
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().one()

    return parse_template_structure(row["structure"])


async def create_template(
    company_id: str,
    template_id: str,
    structure: TemplateStructure,
    source_reports_count: int,
) -> None:
    statement = templates.insert().values(
        id=template_id,
        company_id=company_id,
        structure=structure.model_dump(mode="json"),
        source_reports_count=source_reports_count,
        logo_url="",
        primary_color="",
        created_at=sa.func.now(),
    )

    async with get_database().acquire() as connection:
        await connection.execute(statement)


async def set_active_template(company_id: str, template_id: str) -> None:
    statement = (
        company.update().where(company.c.id == company_id).values(current_template_id=template_id)
    )

    async with get_database().acquire() as connection:
        await connection.execute(statement)


async def _fetch_optional_active_company_template_row(connection, company_id: str):
    version_count = (
        sa.select(sa.func.count())
        .select_from(templates)
        .where(templates.c.company_id == company_id)
        .scalar_subquery()
    )
    statement = (
        sa.select(
            company.c.current_template_id,
            templates.c.structure,
            templates.c.created_at,
            templates.c.source_reports_count,
            version_count.label("version"),
        )
        .select_from(company.outerjoin(templates, templates.c.id == company.c.current_template_id))
        .where(company.c.id == company_id)
    )
    result = await connection.execute(statement)
    return result.mappings().first()


async def _fetch_active_company_template_row(connection, company_id: str):
    version_count = (
        sa.select(sa.func.count())
        .select_from(templates)
        .where(templates.c.company_id == company_id)
        .scalar_subquery()
    )
    statement = (
        sa.select(
            company.c.current_template_id,
            templates.c.structure,
            templates.c.created_at,
            templates.c.source_reports_count,
            version_count.label("version"),
        )
        .select_from(company.join(templates, templates.c.id == company.c.current_template_id))
        .where(company.c.id == company_id)
    )
    result = await connection.execute(statement)
    return result.mappings().first()
