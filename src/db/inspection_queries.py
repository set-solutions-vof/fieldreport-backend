from datetime import date
from uuid import uuid4

import asyncpg

from src.db.connection import get_connection_url


async def insert_inspection(
    id: str,
    company_id: str,
    inspector_id: str,
    template_id: str,
    client_name: str,
    address: str,
    investigation_type: str,
    client_type: str,
    extra_context: str,
    inspection_date: date,
) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        await connection.execute(
            """
            INSERT INTO inspections (
                id,
                company_id,
                inspector_id,
                template_id,
                client_name,
                address,
                investigation_type,
                client_type,
                extra_context,
                inspection_date,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::uuid,
                $4::uuid,
                $5::text,
                $6::text,
                $7::text,
                $8::text,
                $9::text,
                $10::date,
                NOW()
            )
            """,
            id,
            company_id,
            inspector_id,
            template_id,
            client_name,
            address,
            investigation_type,
            client_type,
            extra_context,
            inspection_date,
        )
    finally:
        await connection.close()


async def insert_inspection_audio_file(
    inspection_id: str,
    storage_key: str,
    original_filename: str,
) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        await connection.execute(
            """
            INSERT INTO inspection_audio_files (
                id,
                inspection_id,
                storage_key,
                original_filename,
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
            original_filename,
        )
    finally:
        await connection.close()


async def insert_inspection_photo_file(
    inspection_id: str,
    storage_key: str,
    original_filename: str,
) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        await connection.execute(
            """
            INSERT INTO inspection_photo_files (
                id,
                inspection_id,
                storage_key,
                original_filename,
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
            original_filename,
        )
    finally:
        await connection.close()


async def fetch_inspection_audio_files(inspection_id: str) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(get_connection_url())

    try:
        return await connection.fetch(
            """
            SELECT id, inspection_id, storage_key, original_filename, created_at
            FROM inspection_audio_files
            WHERE inspection_id = $1::uuid
            ORDER BY created_at ASC
            """,
            inspection_id,
        )
    finally:
        await connection.close()


async def fetch_inspection_photo_files(inspection_id: str) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(get_connection_url())

    try:
        return await connection.fetch(
            """
            SELECT id, inspection_id, storage_key, original_filename, created_at
            FROM inspection_photo_files
            WHERE inspection_id = $1::uuid
            ORDER BY created_at ASC
            """,
            inspection_id,
        )
    finally:
        await connection.close()


async def insert_report(
    id: str,
    inspection_id: str,
    company_id: str,
    template_id: str,
) -> None:
    connection = await asyncpg.connect(get_connection_url())

    try:
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
    finally:
        await connection.close()
