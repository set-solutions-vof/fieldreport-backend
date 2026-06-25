import json
from collections.abc import Mapping

from pydantic import TypeAdapter

from src.models.reports.metadata import ReportMetadata
from src.models.reports.pipeline import (
    ReportPipelineContext,
    StoredImageAnalysis,
    StoredTranscriptionSegment,
)
from src.models.reports.report import (
    ImageEvidenceItem,
    ReportDetail,
    ReportDetailSection,
    ReportEvidenceSource,
    ReportSection,
    ReportSummary,
    TranscriptionEvidenceItem,
)
from src.models.templates.domain import TemplateSectionGroup

_groups_adapter: TypeAdapter[list[TemplateSectionGroup]] = TypeAdapter(list[TemplateSectionGroup])


def numeric_to_float(value: object) -> float:
    return float(str(value))


def row_data(row: Mapping[str, object]) -> dict[str, object]:
    data = dict(row)
    metadata = data["metadata"]
    parsed_metadata = json.loads(metadata) if isinstance(metadata, str) else metadata
    data["metadata"] = ReportMetadata.model_validate(parsed_metadata)

    return data


def map_report_summary(row: Mapping[str, object]) -> ReportSummary:
    return ReportSummary.model_validate(row_data(row))


def map_report_detail(row: Mapping[str, object]) -> ReportDetail:
    return ReportDetail.model_validate({**row_data(row), "sections": []})


def map_report_section_source(row: Mapping[str, object]) -> ReportEvidenceSource:
    if row["evidence_type"] == "transcription_segment":
        return ReportEvidenceSource.model_validate(
            {
                "type": "audio",
                "start_seconds": row["start_seconds"],
                "end_seconds": row["end_seconds"],
                "captured_at": None,
                "content_summary": row["transcription_text"],
            }
        )

    return ReportEvidenceSource.model_validate(
        {
            "type": "image",
            "start_seconds": None,
            "end_seconds": None,
            "captured_at": row["captured_at"],
            "content_summary": row["image_analysis_text"],
        }
    )


def map_report_evidence_item(
    row: Mapping[str, object],
) -> TranscriptionEvidenceItem | ImageEvidenceItem:
    if row["evidence_type"] == "transcription_segment":
        return TranscriptionEvidenceItem.model_validate(
            {
                "id": row["transcription_segment_id"],
                "timeline_seconds": numeric_to_float(row["timeline_seconds"]),
                "start_seconds": row["start_seconds"],
                "end_seconds": row["end_seconds"],
                "content_summary": row["transcription_text"],
                "transcription_id": row["transcription_id"],
            }
        )

    return ImageEvidenceItem.model_validate(
        {
            "id": row["image_analysis_id"],
            "timeline_seconds": None,
            "captured_at": row["captured_at"],
            "content_summary": row["image_analysis_text"],
            "storage_key": row["image_storage_key"],
        }
    )


def map_template_section_groups(row: Mapping[str, object]) -> list[TemplateSectionGroup] | None:
    groups_raw = row["groups"]

    return _groups_adapter.validate_python(groups_raw) if groups_raw else None


def map_report_sections(rows: list[Mapping[str, object]]) -> list[ReportSection]:
    sections_by_id: dict[object, ReportSection] = {}
    sections: list[ReportSection] = []

    for row in rows:
        section_id = row["id"]

        if section_id not in sections_by_id:
            section = ReportSection.model_validate(
                {
                    "id": section_id,
                    "section_id": row["section_id"],
                    "label": row["label"],
                    "generated_content": row["generated_content"],
                    "reviewed_content": row["reviewed_content"],
                    "approved": row["approved"],
                    "confidence_level": row["confidence_level"],
                    "confidence_score": numeric_to_float(row["confidence_score"]),
                    "render_type": row["render_type"],
                    "fields": row["fields"],
                    "groups": map_template_section_groups(row),
                    "evidence_sources": [],
                }
            )
            sections_by_id[section_id] = section
            sections.append(section)

        if row["evidence_type"] is not None:
            sections_by_id[section_id].evidence_sources.append(map_report_section_source(row))

    return sections


def map_report_detail_sections(
    rows: list[Mapping[str, object]],
) -> tuple[list[ReportDetailSection], list[TranscriptionEvidenceItem | ImageEvidenceItem]]:
    sections_by_id: dict[object, ReportDetailSection] = {}
    evidence_items_by_id: dict[object, TranscriptionEvidenceItem | ImageEvidenceItem] = {}
    sections: list[ReportDetailSection] = []

    for row in rows:
        section_id = row["id"]

        if section_id not in sections_by_id:
            section = ReportDetailSection.model_validate(
                {
                    "id": section_id,
                    "section_id": row["section_id"],
                    "label": row["label"],
                    "generated_content": row["generated_content"],
                    "reviewed_content": row["reviewed_content"],
                    "approved": row["approved"],
                    "confidence_level": row["confidence_level"],
                    "confidence_score": numeric_to_float(row["confidence_score"]),
                    "render_type": row["render_type"],
                    "fields": row["fields"],
                    "groups": map_template_section_groups(row),
                    "evidence_item_ids": [],
                }
            )
            sections_by_id[section_id] = section
            sections.append(section)

        if row["evidence_type"] is not None:
            evidence_item = map_report_evidence_item(row)
            sections_by_id[section_id].evidence_item_ids.append(evidence_item.id)
            evidence_items_by_id[evidence_item.id] = evidence_item

    evidence_items = sorted(
        evidence_items_by_id.values(),
        key=lambda item: (
            item.timeline_seconds is None,
            item.timeline_seconds or 0.0,
            item.evidence_type,
            str(item.id),
        ),
    )

    return sections, evidence_items


def map_report_pipeline_context(row: Mapping[str, object]) -> ReportPipelineContext:
    return ReportPipelineContext.model_validate(row_data(row))


def map_stored_transcription_segment(row: Mapping[str, object]) -> StoredTranscriptionSegment:
    return StoredTranscriptionSegment.model_validate(dict(row))


def map_stored_image_analysis(row: Mapping[str, object]) -> StoredImageAnalysis:
    return StoredImageAnalysis.model_validate(dict(row))
