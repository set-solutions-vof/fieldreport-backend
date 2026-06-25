from datetime import date
from uuid import uuid4

import sqlalchemy as sa

from src.db.connection import DatabaseConnection, get_database
from src.db.inspection.mapper import map_inspection_media_file
from src.db.schema.tables import (
    image_analyses,
    inspection_audio_files,
    inspection_photo_files,
    inspections,
    reports,
)
from src.models.reports.metadata import ReportMetadata
from src.models.reports.pipeline import InspectionMediaFile


async def insert_inspection(
    connection: DatabaseConnection,
    id: str,
    company_id: str,
    inspector_id: str,
    template_id: str,
    metadata: ReportMetadata,
    extra_context: str,
    inspection_date: date,
) -> None:
    statement = inspections.insert().values(
        id=id,
        company_id=company_id,
        inspector_id=inspector_id,
        template_id=template_id,
        metadata=metadata.model_dump(mode="json"),
        extra_context=extra_context,
        inspection_date=inspection_date,
        created_at=sa.func.now(),
    )

    await connection.execute(statement)


async def insert_inspection_audio_file(
    connection: DatabaseConnection,
    inspection_id: str,
    storage_key: str,
    original_file_name: str,
) -> None:
    statement = inspection_audio_files.insert().values(
        id=str(uuid4()),
        inspection_id=inspection_id,
        storage_key=storage_key,
        original_file_name=original_file_name,
        created_at=sa.func.now(),
    )

    await connection.execute(statement)


async def insert_inspection_photo_file(
    connection: DatabaseConnection,
    inspection_id: str,
    storage_key: str,
    original_file_name: str,
) -> None:
    statement = inspection_photo_files.insert().values(
        id=str(uuid4()),
        inspection_id=inspection_id,
        storage_key=storage_key,
        original_file_name=original_file_name,
        created_at=sa.func.now(),
    )

    await connection.execute(statement)


async def fetch_inspection_audio_files(inspection_id: str) -> list[InspectionMediaFile]:
    statement = (
        sa.select(
            inspection_audio_files.c.id,
            inspection_audio_files.c.inspection_id,
            inspection_audio_files.c.storage_key,
            inspection_audio_files.c.original_file_name,
            inspection_audio_files.c.created_at,
        )
        .where(inspection_audio_files.c.inspection_id == inspection_id)
        .order_by(inspection_audio_files.c.created_at.asc())
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        rows = result.mappings().all()

    return [map_inspection_media_file(row) for row in rows]


async def inspection_photo_belongs_to_company(company_id: str, storage_key: str) -> bool:
    # Check original uploads
    stmt_uploaded = (
        sa.select(sa.literal(1))
        .select_from(
            inspection_photo_files.join(
                inspections,
                inspections.c.id == inspection_photo_files.c.inspection_id,
            )
        )
        .where(
            inspections.c.company_id == company_id,
            inspection_photo_files.c.storage_key == storage_key,
        )
        .limit(1)
    )
    # Also allow pipeline-generated images (e.g. panel location annotations)
    stmt_generated = (
        sa.select(sa.literal(1))
        .select_from(
            image_analyses.join(
                inspections,
                inspections.c.id == image_analyses.c.inspection_id,
            )
        )
        .where(
            inspections.c.company_id == company_id,
            image_analyses.c.storage_key == storage_key,
        )
        .limit(1)
    )

    async with get_database().acquire() as connection:
        row = (await connection.execute(stmt_uploaded)).first()
        if row is not None:
            return True
        row = (await connection.execute(stmt_generated)).first()
        return row is not None


async def fetch_inspection_photo_files(inspection_id: str) -> list[InspectionMediaFile]:
    statement = (
        sa.select(
            inspection_photo_files.c.id,
            inspection_photo_files.c.inspection_id,
            inspection_photo_files.c.storage_key,
            inspection_photo_files.c.original_file_name,
            inspection_photo_files.c.created_at,
        )
        .where(inspection_photo_files.c.inspection_id == inspection_id)
        .order_by(inspection_photo_files.c.created_at.asc())
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        rows = result.mappings().all()

    return [map_inspection_media_file(row) for row in rows]


async def insert_report(
    connection: DatabaseConnection,
    id: str,
    inspection_id: str,
    company_id: str,
    template_id: str,
) -> None:
    statement = reports.insert().values(
        id=id,
        inspection_id=inspection_id,
        company_id=company_id,
        template_id=template_id,
        status="generating",
        created_at=sa.func.now(),
        updated_at=sa.func.now(),
    )

    await connection.execute(statement)
