from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
from types import ModuleType

from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2] / "alembic" / "versions" / "001_initial_schema.py"
)


def load_migration_module() -> ModuleType:
    spec = spec_from_file_location("initial_schema_migration", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def render_upgrade_sql() -> str:
    module = load_migration_module()
    buffer = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql",
        opts={"as_sql": True, "output_buffer": buffer},
    )
    operations = Operations(context)
    original_op = getattr(module, "op")
    setattr(module, "op", operations)

    try:
        upgrade = getattr(module, "upgrade")
        assert callable(upgrade)
        upgrade()
    finally:
        setattr(module, "op", original_op)

    return buffer.getvalue()


def test_upgrade_creates_all_tables() -> None:
    sql = render_upgrade_sql()

    for table_name in [
        "company",
        "users",
        "templates",
        "inspections",
        "transcriptions",
        "image_analyses",
        "transcription_segments",
        "reports",
        "report_sections",
        "report_section_evidence",
    ]:
        assert f"CREATE TABLE {table_name}" in sql


def test_upgrade_enforces_exactly_one_report_section_source() -> None:
    sql = render_upgrade_sql()

    assert "ck_report_section_evidence_exactly_one_source" in sql
    assert "(transcription_segment_id IS NOT NULL) <> (image_analysis_id IS NOT NULL)" in sql
