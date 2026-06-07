from uuid import uuid4

from src.db.connection import get_pool
from src.db.template_mapper import (
    map_active_company_template,
    map_optional_active_company_template,
    map_template_analysis_file,
    map_template_analysis_job,
)
from src.models.templates.domain import TemplateStructure
from src.models.templates.pipeline import TemplateAnalysisFile
from src.models.templates.records import (
    ActiveCompanyTemplateRecord,
    TemplateAnalysisJobRecord,
)


async def fetch_template_configuration_context(
    company_id: str,
) -> tuple[ActiveCompanyTemplateRecord | None, TemplateAnalysisJobRecord | None]:
    async with get_pool().acquire() as connection:
        active_template_row = await _fetch_optional_active_company_template_row(
            connection, company_id
        )
        job_row = await _fetch_latest_template_analysis_job_row(connection, company_id)

    active_template = map_optional_active_company_template(active_template_row)
    job = map_template_analysis_job(job_row) if job_row is not None else None

    return active_template, job


async def fetch_active_company_template(company_id: str) -> ActiveCompanyTemplateRecord:
    async with get_pool().acquire() as connection:
        company_row = await _fetch_active_company_template_row(connection, company_id)

    return map_active_company_template(company_row)


async def fetch_optional_active_company_template(
    company_id: str,
) -> ActiveCompanyTemplateRecord | None:
    async with get_pool().acquire() as connection:
        company_row = await _fetch_optional_active_company_template_row(connection, company_id)

    return map_optional_active_company_template(company_row)


async def fetch_optional_latest_template_analysis_job(
    company_id: str,
) -> TemplateAnalysisJobRecord | None:
    async with get_pool().acquire() as connection:
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
    async with get_pool().acquire() as connection:
        job_row = await connection.fetchrow(
            """
            SELECT
                id,
                company_id,
                status,
                source_reports_count,
                structure,
                failure_message,
                created_at
            FROM template_analysis_jobs
            WHERE id = $1::uuid
            AND company_id = $2::uuid
            """,
            job_id,
            company_id,
        )

    if job_row is None:
        return None

    return map_template_analysis_job(job_row)


async def replace_template_analysis_job(
    job_id: str,
    company_id: str,
    files: list[TemplateAnalysisFile],
) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            DELETE FROM template_analysis_jobs
            WHERE company_id = $1::uuid
            """,
            company_id,
        )
        await connection.execute(
            """
            INSERT INTO template_analysis_jobs (
                id,
                company_id,
                status,
                source_reports_count,
                structure,
                failure_message,
                started_at,
                finished_at,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                'queued'::template_analysis_status_enum,
                $3::integer,
                NULL,
                NULL,
                NULL,
                NULL,
                NOW()
            )
            """,
            job_id,
            company_id,
            len(files),
        )

        for file in files:
            await connection.execute(
                """
                INSERT INTO template_analysis_job_files (
                    id,
                    job_id,
                    original_file_name,
                    stored_file_path,
                    created_at
                )
                VALUES (
                    $4::uuid,
                    $1::uuid,
                    $2::text,
                    $3::text,
                    NOW()
                )
                """,
                job_id,
                file.original_file_name,
                file.stored_file_path,
                str(uuid4()),
            )


async def update_template_analysis_job(
    job_id: str,
    status: str,
    structure: TemplateStructure | None,
    failure_message: str | None = None,
) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            UPDATE template_analysis_jobs
            SET status = $2::template_analysis_status_enum,
                structure = $3::jsonb,
                failure_message = $4::text,
                finished_at = CASE
                    WHEN $2::template_analysis_status_enum IN (
                        'pending_review'::template_analysis_status_enum,
                        'active'::template_analysis_status_enum,
                        'failed'::template_analysis_status_enum
                    )
                    THEN NOW()
                    ELSE finished_at
                END
            WHERE id = $1::uuid
            """,
            job_id,
            status,
            structure.model_dump_json() if structure is not None else None,
            failure_message,
        )


async def delete_template_analysis_job(job_id: str, company_id: str) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            DELETE FROM template_analysis_jobs
            WHERE id = $1::uuid
            AND company_id = $2::uuid
            """,
            job_id,
            company_id,
        )


async def claim_next_template_analysis_job() -> TemplateAnalysisJobRecord | None:
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
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

    if row is None:
        return None

    return map_template_analysis_job(row)


async def get_template_analysis_job_files(job_id: str) -> list[TemplateAnalysisFile]:
    async with get_pool().acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT
                original_file_name AS original_file_name,
                stored_file_path AS stored_file_path
            FROM template_analysis_job_files
            WHERE job_id = $1::uuid
            ORDER BY created_at ASC
            """,
            job_id,
        )

    return [map_template_analysis_file(row) for row in rows]


async def fetch_template_structure(template_id: str, company_id: str) -> TemplateStructure:
    async with get_pool().acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT structure
            FROM templates
            WHERE id = $1::uuid
            AND company_id = $2::uuid
            """,
            template_id,
            company_id,
        )

    return TemplateStructure.model_validate_json(row["structure"])


async def update_template_structure(
    template_id: str,
    company_id: str,
    structure: TemplateStructure,
) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            UPDATE templates
            SET structure = $3::jsonb
            WHERE id = $1::uuid
            AND company_id = $2::uuid
            """,
            template_id,
            company_id,
            structure.model_dump_json(),
        )


async def create_template(
    company_id: str,
    template_id: str,
    structure: TemplateStructure,
) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            INSERT INTO templates (
                id,
                company_id,
                structure,
                logo_url,
                primary_color,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::jsonb,
                '',
                '',
                NOW()
            )
            """,
            template_id,
            company_id,
            structure.model_dump_json(),
        )


async def set_active_template(company_id: str, template_id: str) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            UPDATE company
            SET current_template_id = $2::uuid
            WHERE id = $1::uuid
            """,
            company_id,
            template_id,
        )


async def _fetch_optional_active_company_template_row(connection, company_id: str):
    return await connection.fetchrow(
        """
        SELECT
            company.current_template_id AS current_template_id,
            templates.structure AS structure
        FROM company
        LEFT JOIN templates ON templates.id = company.current_template_id
        WHERE company.id = $1::uuid
        """,
        company_id,
    )


async def _fetch_active_company_template_row(connection, company_id: str):
    return await connection.fetchrow(
        """
        SELECT
            company.current_template_id AS current_template_id,
            templates.structure AS structure
        FROM company
        JOIN templates ON templates.id = company.current_template_id
        WHERE company.id = $1::uuid
        """,
        company_id,
    )


async def _fetch_latest_template_analysis_job_row(connection, company_id: str):
    return await connection.fetchrow(
        """
        SELECT
            id,
            company_id,
            status,
            source_reports_count,
            structure,
            failure_message,
            created_at
        FROM template_analysis_jobs
        WHERE company_id = $1::uuid
        ORDER BY created_at DESC
        LIMIT 1
        """,
        company_id,
    )
