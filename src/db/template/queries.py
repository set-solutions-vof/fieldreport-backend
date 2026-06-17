from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import text

from src.db.connection import get_database
from src.db.schema.tables import (
    company,
    template_analysis_job_files,
    template_analysis_jobs,
    templates,
)
from src.db.template.mapper import (
    map_active_company_template,
    map_optional_active_company_template,
    map_template_analysis_file,
    map_template_analysis_job,
    parse_template_structure,
)
from src.models.templates.domain import TemplateStructure
from src.models.templates.pipeline import TemplateAnalysisFile
from src.models.templates.records import (
    ActiveCompanyTemplateRecord,
    TemplateAnalysisJobRecord,
)


def _template_analysis_job_columns():
    return (
        template_analysis_jobs.c.id,
        template_analysis_jobs.c.company_id,
        template_analysis_jobs.c.status,
        template_analysis_jobs.c.source_reports_count,
        template_analysis_jobs.c.structure,
        template_analysis_jobs.c.failure_message,
        template_analysis_jobs.c.created_at,
    )


async def fetch_template_configuration_context(
    company_id: str,
) -> tuple[ActiveCompanyTemplateRecord | None, TemplateAnalysisJobRecord | None]:
    async with get_database().acquire() as connection:
        active_template_row = await _fetch_optional_active_company_template_row(
            connection, company_id
        )
        job_row = await _fetch_latest_template_analysis_job_row(connection, company_id)

    active_template = map_optional_active_company_template(active_template_row)
    job = map_template_analysis_job(job_row) if job_row is not None else None

    return active_template, job


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


async def fetch_optional_latest_template_analysis_job(
    company_id: str,
) -> TemplateAnalysisJobRecord | None:
    async with get_database().acquire() as connection:
        job_row = await _fetch_latest_template_analysis_job_row(connection, company_id)

    if job_row is None:
        return None

    return map_template_analysis_job(job_row)


async def fetch_latest_template_analysis_job(
    company_id: str,
) -> TemplateAnalysisJobRecord:
    job = await fetch_optional_latest_template_analysis_job(company_id)

    if job is None:
        raise IndexError(f"No template analysis job found for company {company_id}")

    return job


async def get_template_analysis_job(
    job_id: str, company_id: str
) -> TemplateAnalysisJobRecord | None:
    statement = sa.select(*_template_analysis_job_columns()).where(
        template_analysis_jobs.c.id == job_id,
        template_analysis_jobs.c.company_id == company_id,
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        job_row = result.mappings().first()

    if job_row is None:
        return None

    return map_template_analysis_job(job_row)


async def replace_template_analysis_job(
    job_id: str,
    company_id: str,
    files: list[TemplateAnalysisFile],
) -> None:
    async with get_database().acquire() as connection:
        await connection.execute(
            template_analysis_jobs.delete().where(template_analysis_jobs.c.company_id == company_id)
        )
        await connection.execute(
            template_analysis_jobs.insert().values(
                id=job_id,
                company_id=company_id,
                status="queued",
                source_reports_count=len(files),
                structure=None,
                failure_message=None,
                started_at=None,
                finished_at=None,
                created_at=sa.func.now(),
            )
        )

        for file in files:
            await connection.execute(
                template_analysis_job_files.insert().values(
                    id=str(uuid4()),
                    job_id=job_id,
                    original_file_name=file.original_file_name,
                    stored_file_path=file.stored_file_path,
                    created_at=sa.func.now(),
                )
            )


async def update_template_analysis_job(
    job_id: str,
    status: str,
    structure: TemplateStructure | None,
    failure_message: str | None = None,
) -> None:
    finished_statuses = ("pending_review", "active", "failed")
    statement = (
        template_analysis_jobs.update()
        .where(template_analysis_jobs.c.id == job_id)
        .values(
            status=status,
            structure=structure.model_dump(mode="json") if structure is not None else None,
            failure_message=failure_message,
            finished_at=sa.case(
                (sa.literal(status).in_(finished_statuses), sa.func.now()),
                else_=template_analysis_jobs.c.finished_at,
            ),
        )
    )

    async with get_database().acquire() as connection:
        await connection.execute(statement)


async def delete_template_analysis_job(job_id: str, company_id: str) -> None:
    statement = template_analysis_jobs.delete().where(
        template_analysis_jobs.c.id == job_id,
        template_analysis_jobs.c.company_id == company_id,
    )

    async with get_database().acquire() as connection:
        await connection.execute(statement)


async def claim_next_template_analysis_job() -> TemplateAnalysisJobRecord | None:
    statement = text(
        """
        WITH next_job AS (
            SELECT id
            FROM template_analysis_jobs
            WHERE status = 'queued'::template_analysis_status_enum
            ORDER BY created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        UPDATE template_analysis_jobs
        SET status = 'processing'::template_analysis_status_enum,
            started_at = NOW(),
            failure_message = NULL,
            finished_at = NULL
        WHERE id IN (SELECT id FROM next_job)
        RETURNING
            id,
            company_id,
            status,
            source_reports_count,
            structure,
            failure_message,
            created_at
        """
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    if row is None:
        return None

    return map_template_analysis_job(row)


async def get_template_analysis_job_files(job_id: str) -> list[TemplateAnalysisFile]:
    statement = (
        sa.select(
            template_analysis_job_files.c.original_file_name,
            template_analysis_job_files.c.stored_file_path,
        )
        .where(template_analysis_job_files.c.job_id == job_id)
        .order_by(template_analysis_job_files.c.created_at.asc())
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        rows = result.mappings().all()

    return [map_template_analysis_file(row) for row in rows]


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
) -> None:
    statement = templates.insert().values(
        id=template_id,
        company_id=company_id,
        structure=structure.model_dump(mode="json"),
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
    statement = (
        sa.select(
            company.c.current_template_id,
            templates.c.structure,
        )
        .select_from(company.outerjoin(templates, templates.c.id == company.c.current_template_id))
        .where(company.c.id == company_id)
    )
    result = await connection.execute(statement)
    return result.mappings().first()


async def _fetch_active_company_template_row(connection, company_id: str):
    statement = (
        sa.select(
            company.c.current_template_id,
            templates.c.structure,
        )
        .select_from(company.join(templates, templates.c.id == company.c.current_template_id))
        .where(company.c.id == company_id)
    )
    result = await connection.execute(statement)
    return result.mappings().first()


async def _fetch_latest_template_analysis_job_row(connection, company_id: str):
    statement = (
        sa.select(*_template_analysis_job_columns())
        .where(template_analysis_jobs.c.company_id == company_id)
        .order_by(template_analysis_jobs.c.created_at.desc())
        .limit(1)
    )
    result = await connection.execute(statement)
    return result.mappings().first()
