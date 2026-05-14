import json
from collections.abc import Mapping

import asyncpg

from src.config import settings


def get_database_connection_url() -> str:
    return settings.database_url.replace("+asyncpg", "")


async def get_company_template_context(
    company_id: str,
) -> tuple[asyncpg.Record, asyncpg.Record | None]:
    connection = await asyncpg.connect(get_database_connection_url())

    try:
        company_row = await connection.fetchrow(
            """
            SELECT
                company.active_template_id,
                templates.structure AS active_structure
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

    return company_row, job_row


async def get_template_analysis_job(job_id: str, company_id: str) -> asyncpg.Record | None:
    connection = await asyncpg.connect(get_database_connection_url())

    try:
        return await connection.fetchrow(
            """
            SELECT
                id,
                company_id,
                template_id,
                status,
                reports_count,
                structure,
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


async def replace_template_analysis_job(job_id: str, company_id: str, reports_count: int) -> None:
    connection = await asyncpg.connect(get_database_connection_url())

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
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                NULL,
                'extracting'::template_analysis_status_enum,
                $3::integer,
                NULL,
                NOW()
            )
            """,
            job_id,
            company_id,
            reports_count,
        )
    finally:
        await connection.close()


async def update_template_analysis_job(
    job_id: str,
    status: str,
    structure: Mapping[str, object] | None,
    template_id: str | None = None,
) -> None:
    connection = await asyncpg.connect(get_database_connection_url())

    try:
        await connection.execute(
            """
            UPDATE template_analysis_jobs
            SET status = $2::template_analysis_status_enum,
                structure = $3::jsonb,
                template_id = $4::uuid
            WHERE id = $1::uuid
            """,
            job_id,
            status,
            json.dumps(structure) if structure is not None else None,
            template_id,
        )
    finally:
        await connection.close()


async def create_template(
    company_id: str,
    template_id: str,
    structure: Mapping[str, object],
) -> None:
    connection = await asyncpg.connect(get_database_connection_url())

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
            json.dumps(structure),
        )
    finally:
        await connection.close()


async def set_active_template(company_id: str, template_id: str) -> None:
    connection = await asyncpg.connect(get_database_connection_url())

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
