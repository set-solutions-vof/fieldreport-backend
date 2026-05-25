from uuid import uuid4

import asyncpg

from src.db.connection import get_connection_url
from src.db.template_mapper import (
    map_claimed_template_analysis_job,
    map_company_template,
    map_template_analysis_file,
    map_template_analysis_job,
    parse_stored_template_structure,
)
from src.models.templates.configuration import StoredTemplateStructure
from src.models.templates.pipeline import TemplateAnalysisFile, TemplateAnalysisJob
from src.models.templates.records import CompanyTemplateRecord, TemplateAnalysisJobRecord


async def fetch_company_template_context(
    company_id: str,
) -> tuple[CompanyTemplateRecord, TemplateAnalysisJobRecord | None]:
    connection = await asyncpg.connect(get_connection_url())

    try:
        company_row = await connection.fetchrow(
            """
            SELECT
                company.active_template_id AS template_id,
                templates.structure AS structure
            FROM company
            LEFT JOIN templates ON templates.id = company.active_template_id
            WHERE company.id = $1::uuid
            """,
            company_id,
        )
        job_row = await connection.fetchrow(
            """
            SELECT
                id,
                company_id,
                template_id,
                status,
                reports_count,
                structure,
                error_message,
                created_at
            FROM template_analysis_jobs
            WHERE company_id = $1::uuid
            ORDER BY created_at DESC
            LIMIT 1
            """,
            company_id,
        )
    finally:
        await connection.close()

    company = map_company_template(company_row)
    job = map_template_analysis_job(job_row) if job_row is not None else None

    return company, job


async def get_template_analysis_job(
    job_id: str, company_id: str
) -> TemplateAnalysisJobRecord | None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        job_row = await connection.fetchrow(
            """
            SELECT
                id,
                company_id,
                template_id,
                status,
                reports_count,
                structure,
                error_message,
                created_at
            FROM template_analysis_jobs
            WHERE id = $1::uuid
            AND company_id = $2::uuid
            """,
            job_id,
            company_id,
        )
    finally:
        await connection.close()

    if job_row is None:
        return None

    return map_template_analysis_job(job_row)


async def replace_template_analysis_job(
    job_id: str,
    company_id: str,
    files: list[TemplateAnalysisFile],
) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
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
                template_id,
                status,
                reports_count,
                structure,
                error_message,
                started_at,
                finished_at,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                NULL,
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
                    file_name,
                    storage_path,
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
                file.file_name,
                file.storage_path,
                str(uuid4()),
            )
    finally:
        await connection.close()


async def update_template_analysis_job(
    job_id: str,
    status: str,
    structure: StoredTemplateStructure | None,
    template_id: str | None = None,
    error_message: str | None = None,
) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        await connection.execute(
            """
            UPDATE template_analysis_jobs
            SET status = $2::template_analysis_status_enum,
                structure = $3::jsonb,
                template_id = $4::uuid,
                error_message = $5::text,
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
            template_id,
            error_message,
        )
    finally:
        await connection.close()


async def update_pending_template_structure(
    job_id: str,
    company_id: str,
    structure: StoredTemplateStructure,
) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        await connection.execute(
            """
            UPDATE template_analysis_jobs
            SET structure = $3::jsonb
            WHERE id = $1::uuid
            AND company_id = $2::uuid
            AND status = 'pending_review'::template_analysis_status_enum
            """,
            job_id,
            company_id,
            structure.model_dump_json(),
        )
    finally:
        await connection.close()


async def claim_next_template_analysis_job() -> TemplateAnalysisJob | None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        row = await connection.fetchrow(
            """
            WITH next_job AS (
                SELECT id
                FROM template_analysis_jobs
                WHERE status IN (
                    'queued'::template_analysis_status_enum,
                    'extracting'::template_analysis_status_enum
                )
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE template_analysis_jobs
            SET status = 'processing'::template_analysis_status_enum,
                started_at = NOW(),
                error_message = NULL,
                finished_at = NULL
            WHERE id IN (SELECT id FROM next_job)
            RETURNING id, company_id, template_id, status, reports_count, structure, error_message
            """
        )
    finally:
        await connection.close()

    if row is None:
        return None

    return map_claimed_template_analysis_job(row)


async def get_template_analysis_job_files(job_id: str) -> list[TemplateAnalysisFile]:
    connection = await asyncpg.connect(get_connection_url())

    try:
        rows = await connection.fetch(
            """
            SELECT file_name, storage_path
            FROM template_analysis_job_files
            WHERE job_id = $1::uuid
            ORDER BY created_at ASC
            """,
            job_id,
        )
    finally:
        await connection.close()

    return [map_template_analysis_file(row) for row in rows]


async def fetch_template_structure(template_id: str) -> StoredTemplateStructure:
    connection = await asyncpg.connect(get_connection_url())

    try:
        row = await connection.fetchrow(
            """
            SELECT structure
            FROM templates
            WHERE id = $1::uuid
            """,
            template_id,
        )
    finally:
        await connection.close()

    return parse_stored_template_structure(row["structure"])


async def create_template(
    company_id: str,
    template_id: str,
    structure: StoredTemplateStructure,
) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
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
    finally:
        await connection.close()


async def set_active_template(company_id: str, template_id: str) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        await connection.execute(
            """
            UPDATE company
            SET active_template_id = $2::uuid
            WHERE id = $1::uuid
            """,
            company_id,
            template_id,
        )
    finally:
        await connection.close()
