from uuid import uuid4

import sqlalchemy as sa
from pydantic import TypeAdapter

from src.db.connection import DatabaseConnection
from src.db.report.mapper import map_stored_image_analysis, map_stored_transcription_segment
from src.db.schema.tables import (
    image_analyses,
    report_section_evidence,
    report_sections,
    transcription_segments,
    transcriptions,
)
from src.models.reports.generation import GeneratedReportSection
from src.models.reports.pipeline import StoredImageAnalysis, StoredTranscriptionSegment
from src.models.reports.transcription import TranscriptionSegment
from src.models.templates.domain import TemplateSection, TemplateSectionGroup

_fields_adapter: TypeAdapter[list[str]] = TypeAdapter(list[str])
_groups_adapter: TypeAdapter[list[TemplateSectionGroup]] = TypeAdapter(list[TemplateSectionGroup])


class ReportPipelineRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    async def insert_transcription(
        self,
        inspection_id: str,
        company_id: str,
        storage_key: str,
        raw_text: str,
        duration_seconds: float,
    ) -> str:
        transcription_id = str(uuid4())
        statement = transcriptions.insert().values(
            id=transcription_id,
            inspection_id=inspection_id,
            company_id=company_id,
            storage_key=storage_key,
            raw_text=raw_text,
            duration_seconds=duration_seconds,
            created_at=sa.func.now(),
        )

        await self.connection.execute(statement)

        return transcription_id

    async def insert_transcription_segments(
        self,
        transcription_id: str,
        inspection_id: str,
        segments: list[TranscriptionSegment],
    ) -> list[str]:
        segment_ids = [str(uuid4()) for _ in segments]

        if not segments:
            return segment_ids

        statement = transcription_segments.insert().values(
            [
                {
                    "id": segment_id,
                    "transcription_id": transcription_id,
                    "inspection_id": inspection_id,
                    "segment_index": segment.segment_index,
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "text": segment.text,
                    "created_at": sa.func.now(),
                }
                for segment_id, segment in zip(segment_ids, segments, strict=True)
            ]
        )
        await self.connection.execute(statement)

        return segment_ids

    async def insert_image_analysis(
        self,
        inspection_id: str,
        company_id: str,
        storage_key: str,
        analysis_text: str,
    ) -> str:
        image_analysis_id = str(uuid4())
        statement = image_analyses.insert().values(
            id=image_analysis_id,
            inspection_id=inspection_id,
            company_id=company_id,
            storage_key=storage_key,
            analysis_text=analysis_text,
            geotag_lat=None,
            geotag_lng=None,
            captured_at=None,
            created_at=sa.func.now(),
        )

        await self.connection.execute(statement)

        return image_analysis_id

    async def fetch_transcription_segments_for_inspection(
        self,
        inspection_id: str,
    ) -> list[StoredTranscriptionSegment]:
        statement = (
            sa.select(
                transcription_segments.c.id,
                transcription_segments.c.transcription_id,
                transcription_segments.c.inspection_id,
                transcription_segments.c.segment_index,
                transcription_segments.c.start_seconds,
                transcription_segments.c.end_seconds,
                transcription_segments.c.text,
                transcription_segments.c.created_at,
            )
            .where(transcription_segments.c.inspection_id == inspection_id)
            .order_by(
                transcription_segments.c.transcription_id.asc(),
                transcription_segments.c.segment_index.asc(),
            )
        )

        result = await self.connection.execute(statement)
        rows = result.mappings().all()

        return [map_stored_transcription_segment(row) for row in rows]

    async def fetch_image_analyses_for_inspection(
        self,
        inspection_id: str,
    ) -> list[StoredImageAnalysis]:
        statement = (
            sa.select(
                image_analyses.c.id,
                image_analyses.c.inspection_id,
                image_analyses.c.company_id,
                image_analyses.c.storage_key,
                image_analyses.c.analysis_text,
                image_analyses.c.captured_at,
                image_analyses.c.created_at,
            )
            .where(image_analyses.c.inspection_id == inspection_id)
            .order_by(image_analyses.c.created_at.asc())
        )

        result = await self.connection.execute(statement)
        rows = result.mappings().all()

        return [map_stored_image_analysis(row) for row in rows]

    async def insert_report_section(
        self,
        report_id: str,
        company_id: str,
        section: GeneratedReportSection,
        template_section: TemplateSection,
    ) -> str:
        report_section_id = str(uuid4())
        statement = report_sections.insert().values(
            id=report_section_id,
            report_id=report_id,
            company_id=company_id,
            section_id=section.id,
            section_order=template_section.order,
            render_type=template_section.render_type,
            generated_content=[section.generated_content],
            reviewed_content=None,
            edit_distance=None,
            approved=False,
            confidence_level=section.confidence_level,
            confidence_score=section.confidence_score,
            label=template_section.label,
            fields=_fields_adapter.dump_python(template_section.fields, mode="json")
            if template_section.fields is not None
            else None,
            groups=_groups_adapter.dump_python(template_section.groups, mode="json")
            if template_section.groups is not None
            else None,
            updated_at=sa.func.now(),
        )

        await self.connection.execute(statement)

        return report_section_id

    async def insert_report_sections(
        self,
        report_id: str,
        company_id: str,
        section_pairs: list[tuple[GeneratedReportSection, TemplateSection]],
    ) -> list[str]:
        report_section_ids = [str(uuid4()) for _ in section_pairs]

        if not section_pairs:
            return report_section_ids

        statement = report_sections.insert().values(
            [
                {
                    "id": report_section_id,
                    "report_id": report_id,
                    "company_id": company_id,
                    "section_id": section.id,
                    "section_order": template_section.order,
                    "render_type": template_section.render_type,
                    "generated_content": [section.generated_content],
                    "reviewed_content": None,
                    "edit_distance": None,
                    "approved": False,
                    "confidence_level": section.confidence_level,
                    "confidence_score": section.confidence_score,
                    "label": template_section.label,
                    "fields": _fields_adapter.dump_python(template_section.fields, mode="json")
                    if template_section.fields is not None
                    else None,
                    "groups": _groups_adapter.dump_python(template_section.groups, mode="json")
                    if template_section.groups is not None
                    else None,
                    "updated_at": sa.func.now(),
                }
                for report_section_id, (section, template_section) in zip(
                    report_section_ids, section_pairs, strict=True
                )
            ]
        )

        await self.connection.execute(statement)

        return report_section_ids

    async def insert_report_section_source_transcription(
        self,
        report_section_id: str,
        transcription_segment_id: str,
    ) -> None:
        statement = report_section_evidence.insert().values(
            id=str(uuid4()),
            report_section_id=report_section_id,
            evidence_type="transcription_segment",
            transcription_segment_id=transcription_segment_id,
            image_analysis_id=None,
            created_at=sa.func.now(),
        )
        await self.connection.execute(statement)

    async def insert_report_section_source_image(
        self,
        report_section_id: str,
        image_analysis_id: str,
    ) -> None:
        statement = report_section_evidence.insert().values(
            id=str(uuid4()),
            report_section_id=report_section_id,
            evidence_type="image_analysis",
            transcription_segment_id=None,
            image_analysis_id=image_analysis_id,
            created_at=sa.func.now(),
        )
        await self.connection.execute(statement)
