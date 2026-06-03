from datetime import date
from uuid import uuid4

from src.db.connection import get_pool
from src.db.inspection_mapper import map_inspection_media_file
from src.models.reports.metadata import ReportMetadata
from src.models.reports.pipeline import InspectionMediaFile


async def insert_inspection(
    id: str,
    company_id: str,
    inspector_id: str,
    template_id: str,
    metadata: ReportMetadata,
    extra_context: str,
    inspection_date: date,
) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            INSERT INTO inspections (
                id,
                company_id,
                inspector_id,
                template_id,
                metadata,
                extra_context,
                inspection_date,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::uuid,
                $4::uuid,
                $5::jsonb,
                $6::text,
                $7::date,
                NOW()
            )
            """,
            id,
            company_id,
            inspector_id,
            template_id,
            metadata.model_dump_json(),
            extra_context,
            inspection_date,
        )


async def insert_inspection_audio_file(
    inspection_id: str,
    storage_key: str,
    original_file_name: str,
) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            INSERT INTO inspection_audio_files (
                id,
                inspection_id,
                storage_key,
                original_file_name,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::text,
                $4::text,
                NOW()
            )
            """,
            str(uuid4()),
            inspection_id,
            storage_key,
            original_file_name,
        )


async def insert_inspection_photo_file(
    inspection_id: str,
    storage_key: str,
    original_file_name: str,
) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            INSERT INTO inspection_photo_files (
                id,
                inspection_id,
                storage_key,
                original_file_name,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::text,
                $4::text,
                NOW()
            )
            """,
            str(uuid4()),
            inspection_id,
            storage_key,
            original_file_name,
        )


async def fetch_inspection_audio_files(inspection_id: str) -> list[InspectionMediaFile]:
    async with get_pool().acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, inspection_id, storage_key, original_file_name, created_at
            FROM inspection_audio_files
            WHERE inspection_id = $1::uuid
            ORDER BY created_at ASC
            """,
            inspection_id,
        )

    return [map_inspection_media_file(row) for row in rows]


async def fetch_inspection_photo_files(inspection_id: str) -> list[InspectionMediaFile]:
    async with get_pool().acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, inspection_id, storage_key, original_file_name, created_at
            FROM inspection_photo_files
            WHERE inspection_id = $1::uuid
            ORDER BY created_at ASC
            """,
            inspection_id,
        )

    return [map_inspection_media_file(row) for row in rows]


async def insert_report(
    id: str,
    inspection_id: str,
    company_id: str,
    template_id: str,
) -> None:
    async with get_pool().acquire() as connection:
        await connection.execute(
            """
            INSERT INTO reports (
                id,
                inspection_id,
                company_id,
                template_id,
                status,
                created_at,
                updated_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::uuid,
                $4::uuid,
                'generating'::report_status,
                NOW(),
                NOW()
            )
            """,
            id,
            inspection_id,
            company_id,
            template_id,
        )
