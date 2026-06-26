import asyncio
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings
from src.storage.blob import close_service_client, ensure_containers, upload_file

DEMO_PASSWORD = "Password123!"
CURRENT_TEMPLATE_ID = "e4378133-da5e-4caf-b7d2-2605c6e88a72"
DEMO_DIR = Path(__file__).parent
REPO_ROOT = DEMO_DIR.parent
TEMPLATE_DOCX_PATH = REPO_ROOT / "templates" / "thermofly_paneel_tagged.docx"
TEMPLATE_DOCX_KEY = f"thermofly/paneel/{CURRENT_TEMPLATE_ID}.docx"

TRUNCATE_SQL = """
TRUNCATE TABLE
  password_reset_tokens,
  invites,
  template_analysis_job_files,
  template_analysis_jobs,
  report_section_evidence,
  report_sections,
  reports,
  transcription_segments,
  image_analyses,
  transcriptions,
  inspection_photo_files,
  inspection_audio_files,
  inspections,
  templates,
  users,
  company
CASCADE
"""

SEED_SQL_PATH = DEMO_DIR / "seed.sql"


async def seed_database() -> None:
    seed_statements = [
        statement.strip() for statement in SEED_SQL_PATH.read_text().split(";") if statement.strip()
    ]
    engine = create_async_engine(settings.database_url)

    async with engine.begin() as connection:
        await connection.execute(sa.text(TRUNCATE_SQL))

        for statement in seed_statements:
            await connection.execute(sa.text(statement))

    await engine.dispose()


async def seed_template_blobs() -> None:
    await ensure_containers()
    await upload_file(
        "templates",
        TEMPLATE_DOCX_KEY,
        TEMPLATE_DOCX_PATH.read_bytes(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    await close_service_client()


async def seed_demo() -> None:
    await seed_database()
    await seed_template_blobs()


def main() -> None:
    asyncio.run(seed_demo())
    print("Demo data loaded.")
    print(f"  bas@thermofly.nl / {DEMO_PASSWORD}")
    print(f"  twan@thermofly.nl / {DEMO_PASSWORD}")
    print("  onboarding_completed: true (ThermoFly Demo with templates)")


if __name__ == "__main__":
    main()
