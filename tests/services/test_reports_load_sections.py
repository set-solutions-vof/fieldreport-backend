from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.models.reports.report import ReportDetailSection, ReportTimelineItem
from src.services import reports as reports_service


async def test_load_report_detail_sections_fetches_and_maps() -> None:
    report_id = str(uuid4())
    rows = [{"id": uuid4()}]
    expected_sections = [ReportDetailSection.model_construct()]
    expected_timeline = [ReportTimelineItem.model_construct()]

    with (
        patch.object(
            reports_service.report_queries,
            "fetch_report_section_rows",
            AsyncMock(return_value=rows),
        ) as fetch_rows,
        patch.object(
            reports_service,
            "map_report_detail_sections",
            return_value=(expected_sections, expected_timeline),
        ) as map_sections,
    ):
        sections, timeline_items = await reports_service.load_report_detail_sections(report_id)

    assert sections is expected_sections
    assert timeline_items is expected_timeline
    fetch_rows.assert_awaited_once_with(report_id)
    map_sections.assert_called_once_with(rows)
