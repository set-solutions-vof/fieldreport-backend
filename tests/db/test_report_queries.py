from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import sqlalchemy as sa

from src.db.report import queries
from src.db.report.mapper import map_report_detail_sections
from src.db.schema.tables import report_sections
from src.exceptions import ReportNotFound
from src.models.reports.metadata import ReportMetadata
from tests.db.sqlalchemy_fakes import FakeResult, build_connection


async def test_list_report_summaries_by_company_id_returns_mapped_reports() -> None:
    company_id = uuid4()
    inspection_date = datetime(2026, 5, 8, 12, 30, tzinfo=UTC)
    rows = [
        {
            "id": uuid4(),
            "company_id": company_id,
            "status": "draft",
            "metadata": {"naam_opdrachtgever": "ACME", "adres_schadeadres": "Main Street 1"},
            "inspection_date": inspection_date,
            "inspector_name": "Inspector User",
        },
        {
            "id": uuid4(),
            "company_id": company_id,
            "status": "approved",
            "metadata": {"naam_opdrachtgever": "Globex", "adres_schadeadres": "Second Street 2"},
            "inspection_date": inspection_date,
            "inspector_name": "Admin User",
        },
    ]
    connection = build_connection(rows=rows)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        reports = await queries.list_report_summaries_by_company_id(str(company_id))

    assert [report.id for report in reports] == [rows[0]["id"], rows[1]["id"]]
    assert all(report.company_id == company_id for report in reports)
    assert [report.status for report in reports] == ["draft", "approved"]
    assert [report.metadata.model_dump()["naam_opdrachtgever"] for report in reports] == [
        "ACME",
        "Globex",
    ]
    assert reports[0].metadata.model_dump()["adres_schadeadres"] == "Main Street 1"
    assert reports[0].inspection_date == inspection_date
    assert reports[0].inspector_name == "Inspector User"
    connection.execute.assert_awaited_once()


async def test_get_report_by_id_returns_mapped_report_for_company() -> None:
    report_id = uuid4()
    company_id = uuid4()
    inspection_date = datetime(2026, 5, 8, 12, 30, tzinfo=UTC)
    updated_at = datetime(2026, 5, 9, 8, 15, tzinfo=UTC)
    row = {
        "id": report_id,
        "status": "draft",
        "metadata": {"naam_opdrachtgever": "ACME", "adres_schadeadres": "Main Street 1"},
        "inspection_date": inspection_date,
        "inspector_name": "Inspector User",
        "updated_at": updated_at,
    }
    connection = build_connection(row=row)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        report = await queries.get_report_by_id(str(report_id), str(company_id))

    assert report is not None
    assert report.id == report_id
    assert report.status == "draft"
    assert report.metadata == ReportMetadata.model_validate(
        {
            "naam_opdrachtgever": "ACME",
            "adres_schadeadres": "Main Street 1",
        }
    )
    assert report.inspection_date == inspection_date
    assert report.inspector_name == "Inspector User"
    assert report.updated_at == updated_at
    assert report.sections == []
    connection.execute.assert_awaited_once()


async def test_get_report_by_id_raises_when_missing() -> None:
    connection = build_connection(row=None)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        try:
            await queries.get_report_by_id(str(uuid4()), str(uuid4()))
        except ReportNotFound as error:
            assert str(error) != ""
        else:
            raise AssertionError("Expected ReportNotFound")


async def test_fetch_report_section_rows_maps_detail_sections_and_timeline() -> None:
    first_section_id = uuid4()
    second_section_id = uuid4()
    third_section_id = uuid4()
    shared_transcription_segment_id = uuid4()
    first_unique_segment_id = uuid4()
    shared_image_analysis_id = uuid4()
    third_section_segment_id = uuid4()
    capture_time = datetime(2026, 5, 8, 12, 30, 20, tzinfo=UTC)
    first_transcription_id = uuid4()
    second_transcription_id = uuid4()
    rows = [
        {
            "id": first_section_id,
            "section_id": "bevindingen",
            "label": "Bevindingen",
            "fields": ["Issue", "Action"],
            "groups": [
                {"id": "damage", "label": "Damage", "fields": ["Issue"]},
            ],
            "section_order": 1,
            "generated_content": "Draft text",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "evidence_type": "image_analysis",
            "transcription_segment_id": None,
            "transcription_id": None,
            "start_seconds": None,
            "end_seconds": None,
            "transcription_text": None,
            "image_analysis_id": shared_image_analysis_id,
            "captured_at": capture_time,
            "image_analysis_text": "Thermal image",
            "timeline_seconds": 20.0,
        },
        {
            "id": first_section_id,
            "section_id": "bevindingen",
            "label": "Bevindingen",
            "fields": ["Issue", "Action"],
            "groups": [
                {"id": "damage", "label": "Damage", "fields": ["Issue"]},
            ],
            "section_order": 1,
            "generated_content": "Draft text",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "evidence_type": "transcription_segment",
            "transcription_segment_id": shared_transcription_segment_id,
            "transcription_id": first_transcription_id,
            "start_seconds": 12.0,
            "end_seconds": 15.0,
            "transcription_text": "Moisture mentioned",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_seconds": 12.0,
        },
        {
            "id": second_section_id,
            "section_id": "advies",
            "label": "Advies",
            "fields": None,
            "groups": None,
            "section_order": 2,
            "generated_content": "Advice",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "medium",
            "confidence_score": 0.71,
            "evidence_type": "transcription_segment",
            "transcription_segment_id": shared_transcription_segment_id,
            "transcription_id": first_transcription_id,
            "start_seconds": 12.0,
            "end_seconds": 15.0,
            "transcription_text": "Moisture mentioned",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_seconds": 12.0,
        },
        {
            "id": second_section_id,
            "section_id": "advies",
            "label": "Advies",
            "fields": None,
            "groups": None,
            "section_order": 2,
            "generated_content": "Advice",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "medium",
            "confidence_score": 0.71,
            "evidence_type": "transcription_segment",
            "transcription_segment_id": first_unique_segment_id,
            "transcription_id": second_transcription_id,
            "start_seconds": 5.0,
            "end_seconds": 8.0,
            "transcription_text": "Opening note",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_seconds": 5.0,
        },
        {
            "id": second_section_id,
            "section_id": "advies",
            "label": "Advies",
            "fields": None,
            "groups": None,
            "section_order": 2,
            "generated_content": "Advice",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "medium",
            "confidence_score": 0.71,
            "evidence_type": "image_analysis",
            "transcription_segment_id": None,
            "transcription_id": None,
            "start_seconds": None,
            "end_seconds": None,
            "transcription_text": None,
            "image_analysis_id": shared_image_analysis_id,
            "captured_at": capture_time,
            "image_analysis_text": "Thermal image",
            "timeline_seconds": 20.0,
        },
        {
            "id": third_section_id,
            "section_id": "samenvatting",
            "label": "Samenvatting",
            "fields": None,
            "groups": None,
            "section_order": 3,
            "generated_content": "Summary",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "low",
            "confidence_score": 0.42,
            "evidence_type": "transcription_segment",
            "transcription_segment_id": third_section_segment_id,
            "transcription_id": first_transcription_id,
            "start_seconds": 30.0,
            "end_seconds": 35.0,
            "transcription_text": "Summary audio",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_seconds": 30.0,
        },
    ]
    photo_key = "company-id/inspection-id/photos/photo.jpg"
    for row in rows:
        row["render_type"] = "text_block"
        row["image_storage_key"] = photo_key if row["evidence_type"] == "image_analysis" else None
    rows[0]["render_type"] = "measurement_table"
    connection = build_connection(rows=rows)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        rows = await queries.fetch_report_section_rows(str(uuid4()), str(uuid4()))
        sections, evidence_items = map_report_detail_sections(rows)

    assert [section.id for section in sections] == [
        first_section_id,
        second_section_id,
        third_section_id,
    ]
    assert sections[0].render_type == "measurement_table"
    assert sections[0].label == "Bevindingen"
    assert sections[0].fields == ["Issue", "Action"]
    assert sections[0].groups is not None
    assert sections[0].groups[0].label == "Damage"
    assert sections[0].evidence_item_ids == [
        shared_image_analysis_id,
        shared_transcription_segment_id,
    ]
    assert sections[1].evidence_item_ids == [
        shared_transcription_segment_id,
        first_unique_segment_id,
        shared_image_analysis_id,
    ]
    assert sections[2].evidence_item_ids == [third_section_segment_id]
    assert [evidence_item.id for evidence_item in evidence_items] == [
        first_unique_segment_id,
        shared_transcription_segment_id,
        third_section_segment_id,
        shared_image_analysis_id,
    ]
    assert [evidence_item.evidence_type for evidence_item in evidence_items] == [
        "transcription_segment",
        "transcription_segment",
        "transcription_segment",
        "image_analysis",
    ]
    assert [evidence_item.timeline_seconds for evidence_item in evidence_items] == [
        5.0,
        12.0,
        30.0,
        None,
    ]
    transcription_evidence = [
        evidence_item
        for evidence_item in evidence_items
        if evidence_item.evidence_type == "transcription_segment"
    ]
    assert transcription_evidence[0].transcription_id == second_transcription_id
    assert transcription_evidence[1].transcription_id == first_transcription_id
    connection.execute.assert_awaited_once()


def test_report_section_timeline_query_offsets_second_transcription() -> None:
    columns = queries._report_section_detail_columns(include_timeline=True)
    statement = sa.select(*columns).select_from(queries._report_sections_join())
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))

    assert "duration_seconds" in compiled
    assert "prior_transcription" in compiled
    assert "NULL" in compiled
    assert "epoch" not in compiled
    assert report_sections.c.id.key in compiled or "report_sections" in compiled


async def test_fetch_report_section_rows_offsets_timeline_by_prior_transcription_duration() -> None:
    section_id = uuid4()
    first_transcription_id = uuid4()
    second_transcription_id = uuid4()
    first_segment_id = uuid4()
    second_segment_id = uuid4()
    first_transcription_duration_seconds = 40.0
    second_segment_start_seconds = 5.0
    rows = [
        {
            "id": section_id,
            "section_id": "bevindingen",
            "label": "Bevindingen",
            "fields": None,
            "groups": None,
            "section_order": 1,
            "render_type": "text_block",
            "generated_content": "Draft text",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "evidence_type": "transcription_segment",
            "transcription_segment_id": first_segment_id,
            "transcription_id": first_transcription_id,
            "start_seconds": 10.0,
            "end_seconds": 15.0,
            "transcription_text": "First audio",
            "image_analysis_id": None,
            "image_storage_key": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_seconds": 10.0,
        },
        {
            "id": section_id,
            "section_id": "bevindingen",
            "label": "Bevindingen",
            "fields": None,
            "groups": None,
            "section_order": 1,
            "render_type": "text_block",
            "generated_content": "Draft text",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "evidence_type": "transcription_segment",
            "transcription_segment_id": second_segment_id,
            "transcription_id": second_transcription_id,
            "start_seconds": second_segment_start_seconds,
            "end_seconds": 8.0,
            "transcription_text": "Second audio",
            "image_analysis_id": None,
            "image_storage_key": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_seconds": second_segment_start_seconds + first_transcription_duration_seconds,
        },
    ]
    connection = build_connection(rows=rows)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        result_rows = await queries.fetch_report_section_rows(str(uuid4()), str(uuid4()))
        _, evidence_items = map_report_detail_sections(result_rows)

    assert len(evidence_items) == 2
    assert evidence_items[0].timeline_seconds == 10.0
    assert evidence_items[0].transcription_id == first_transcription_id
    assert evidence_items[1].timeline_seconds == 45.0
    assert evidence_items[1].transcription_id == second_transcription_id
    connection.execute.assert_awaited_once()


async def test_claim_next_report_for_generation_returns_claimed_report() -> None:
    row = {
        "id": uuid4(),
        "inspection_id": uuid4(),
        "company_id": uuid4(),
        "template_id": uuid4(),
    }
    connection = build_connection(row=row)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        result = await queries.claim_next_report_for_generation()

    assert result == row
    connection.execute.assert_awaited_once()


async def test_get_report_for_pipeline_returns_report_context() -> None:
    from src.models.reports.pipeline import ReportPipelineContext

    metadata = {"type_onderzoek": "Lekdetectie", "type_klant": "Zakelijk"}
    row = {
        "id": uuid4(),
        "inspection_id": uuid4(),
        "company_id": uuid4(),
        "template_id": uuid4(),
        "status": "generating",
        "extra_context": "",
        "metadata": metadata,
    }
    connection = build_connection(row=row)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        result = await queries.get_report_for_pipeline(str(row["id"]))

    assert result == ReportPipelineContext(**row)
    connection.execute.assert_awaited_once()


async def test_get_report_for_pipeline_raises_when_missing() -> None:
    connection = build_connection(row=None)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        with pytest.raises(ReportNotFound):
            await queries.get_report_for_pipeline(str(uuid4()))


async def test_set_report_status_executes_update() -> None:
    connection = build_connection()

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        await queries.set_report_status("report-id", "draft")

    connection.execute.assert_awaited_once()
    statement = connection.execute.await_args.args[0]
    assert statement.table.name == "reports"


async def test_reset_report_for_retry_executes_update() -> None:
    connection = build_connection()

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        await queries.reset_report_for_retry("report-id", "company-id")

    connection.execute.assert_awaited_once()
    statement = connection.execute.await_args.args[0]
    assert statement.table.name == "reports"


async def test_update_report_section_returns_updated_section_for_company() -> None:
    report_id = uuid4()
    section_id = uuid4()
    company_id = uuid4()
    capture_time = datetime(2026, 5, 8, 12, 45, tzinfo=UTC)
    rows = [
        {
            "id": section_id,
            "section_id": "advies",
            "label": "Advies",
            "fields": None,
            "groups": None,
            "section_order": 2,
            "render_type": "key_value_table",
            "generated_content": "Advice",
            "reviewed_content": "Updated advice",
            "approved": True,
            "confidence_level": "low",
            "confidence_score": 0.32,
            "evidence_type": "image_analysis",
            "start_seconds": None,
            "end_seconds": None,
            "transcription_text": None,
            "captured_at": capture_time,
            "image_analysis_text": "Image summary",
        }
    ]
    connection = build_connection(
        results=[
            FakeResult(row={"id": section_id}),
            FakeResult(rows=rows),
        ]
    )

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        section = await queries.update_report_section(
            str(report_id),
            str(section_id),
            str(company_id),
            "Updated advice",
            True,
        )

    assert section is not None
    assert section.id == section_id
    assert section.section_id == "advies"
    assert section.render_type == "key_value_table"
    assert section.reviewed_content == "Updated advice"
    assert section.approved is True
    assert section.confidence_level == "low"
    assert section.confidence_score == 0.32
    assert section.evidence_sources[0].type == "image"
    assert section.evidence_sources[0].captured_at == capture_time
    assert section.evidence_sources[0].content_summary == "Image summary"
    assert connection.execute.await_count == 2


async def test_update_report_section_returns_section_when_no_fields_are_changed() -> None:
    report_id = uuid4()
    section_id = uuid4()
    company_id = uuid4()
    rows = [
        {
            "id": section_id,
            "section_id": "advies",
            "section_order": 2,
            "label": "Advies",
            "render_type": "text_block",
            "fields": None,
            "groups": None,
            "generated_content": "Advice",
            "reviewed_content": "Expert advice",
            "approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "evidence_type": "transcription_segment",
            "start_seconds": 2.0,
            "end_seconds": 4.0,
            "transcription_text": "Advice audio",
            "captured_at": None,
            "image_analysis_text": None,
        }
    ]
    connection = build_connection(
        results=[
            FakeResult(row={"id": section_id}),
            FakeResult(rows=rows),
        ]
    )

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        section = await queries.update_report_section(
            str(report_id),
            str(section_id),
            str(company_id),
            None,
            None,
        )

    assert section is not None
    assert section.id == section_id
    assert section.reviewed_content == "Expert advice"
    assert section.approved is False
    assert section.evidence_sources[0].type == "audio"
    assert connection.execute.await_count == 2


async def test_update_report_section_raises_when_section_is_missing() -> None:
    connection = build_connection(row=None)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        try:
            await queries.update_report_section(
                str(uuid4()),
                str(uuid4()),
                str(uuid4()),
                None,
                None,
            )
        except ReportNotFound as error:
            assert str(error) != ""
        else:
            raise AssertionError("Expected ReportNotFound")


async def test_check_all_sections_approved_returns_true_when_no_unapproved() -> None:
    connection = build_connection(row={"unapproved_count": 0})

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        result = await queries.check_all_sections_approved("report-id", "company-id")

    assert result is True
    connection.execute.assert_awaited_once()


async def test_check_all_sections_approved_returns_false_when_unapproved_exist() -> None:
    connection = build_connection(row={"unapproved_count": 3})

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        result = await queries.check_all_sections_approved("report-id", "company-id")

    assert result is False


async def test_check_all_sections_approved_excludes_empty_sections() -> None:
    connection = build_connection(row={"unapproved_count": 0})

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.db.report.queries.get_database", return_value=pool):
        await queries.check_all_sections_approved("report-id", "company-id")

    stmt = connection.execute.call_args[0][0]
    compiled = str(stmt.compile(dialect=sa.dialects.postgresql.dialect()))
    assert "generated_content" in compiled
    assert "reviewed_content" in compiled
