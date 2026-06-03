from uuid import uuid4

import asyncpg

from src.db.report_mapper import map_stored_image_analysis, map_stored_transcription_segment
from src.models.reports.generation import GeneratedReportSection
from src.models.reports.pipeline import StoredImageAnalysis, StoredTranscriptionSegment
from src.models.reports.transcription import TranscriptionSegment
from src.models.templates.domain import TemplateSection


class ReportPipelineRepository:
    def __init__(self, connection: asyncpg.Connection) -> None:
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

        await self.connection.execute(
            """
            INSERT INTO transcriptions (
                id,
                inspection_id,
                company_id,
                storage_key,
                raw_text,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::uuid,
                $4::text,
                $5::text,
                NOW()
            )
            """,
            transcription_id,
            inspection_id,
            company_id,
            storage_key,
            raw_text,
        )

        return transcription_id

    async def insert_transcription_segments(
        self,
        transcription_id: str,
        inspection_id: str,
        segments: list[TranscriptionSegment],
    ) -> list[str]:
        segment_ids = [str(uuid4()) for _ in segments]

        for segment_id, segment in zip(segment_ids, segments, strict=True):
            await self.connection.execute(
                """
                INSERT INTO transcription_segments (
                    id,
                    transcription_id,
                    inspection_id,
                    segment_index,
                    start_seconds,
                    end_seconds,
                    text,
                    created_at
                )
                VALUES (
                    $1::uuid,
                    $2::uuid,
                    $3::uuid,
                    $4::integer,
                    $5::double precision,
                    $6::double precision,
                    $7::text,
                    NOW()
                )
                """,
                segment_id,
                transcription_id,
                inspection_id,
                segment.segment_index,
                segment.start_seconds,
                segment.end_seconds,
                segment.text,
            )

        return segment_ids

    async def insert_image_analysis(
        self,
        inspection_id: str,
        company_id: str,
        storage_key: str,
        analysis_text: str,
    ) -> str:
        image_analysis_id = str(uuid4())

        await self.connection.execute(
            """
            INSERT INTO image_analyses (
                id,
                inspection_id,
                company_id,
                storage_key,
                analysis_text,
                geotag_lat,
                geotag_lng,
                captured_at,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::uuid,
                $4::text,
                $5::text,
                NULL,
                NULL,
                NULL,
                NOW()
            )
            """,
            image_analysis_id,
            inspection_id,
            company_id,
            storage_key,
            analysis_text,
        )

        return image_analysis_id

    async def fetch_transcription_segments_for_inspection(
        self,
        inspection_id: str,
    ) -> list[StoredTranscriptionSegment]:
        rows = await self.connection.fetch(
            """
            SELECT
                id,
                transcription_id,
                inspection_id,
                segment_index,
                start_seconds,
                end_seconds,
                text,
                created_at
            FROM transcription_segments
            WHERE inspection_id = $1::uuid
            ORDER BY transcription_id ASC, segment_index ASC
            """,
            inspection_id,
        )

        return [map_stored_transcription_segment(row) for row in rows]

    async def fetch_image_analyses_for_inspection(
        self,
        inspection_id: str,
    ) -> list[StoredImageAnalysis]:
        rows = await self.connection.fetch(
            """
            SELECT
                id,
                inspection_id,
                company_id,
                storage_key,
                analysis_text,
                captured_at,
                created_at
            FROM image_analyses
            WHERE inspection_id = $1::uuid
            ORDER BY created_at ASC
            """,
            inspection_id,
        )

        return [map_stored_image_analysis(row) for row in rows]

    async def insert_report_section(
        self,
        report_id: str,
        company_id: str,
        section: GeneratedReportSection,
        template_section: TemplateSection,
    ) -> str:
        report_section_id = str(uuid4())

        await self.connection.execute(
            """
            INSERT INTO report_sections (
                id,
                report_id,
                company_id,
                section_id,
                section_order,
                render_type,
                generated_content,
                reviewed_content,
                edit_distance,
                approved,
                confidence_level,
                confidence_score,
                updated_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                $3::uuid,
                $4::text,
                $5::integer,
                $6::render_type_enum,
                to_jsonb(ARRAY[$7::text]),
                NULL,
                NULL,
                false,
                $8::confidence_level_enum,
                $9::numeric,
                NOW()
            )
            """,
            report_section_id,
            report_id,
            company_id,
            section.id,
            template_section.order,
            template_section.render_type,
            section.generated_content,
            section.confidence_level,
            section.confidence_score,
        )

        return report_section_id

    async def insert_report_section_source_transcription(
        self,
        report_section_id: str,
        transcription_segment_id: str,
    ) -> None:
        await self.connection.execute(
            """
            INSERT INTO report_section_evidence (
                id,
                report_section_id,
                evidence_type,
                transcription_segment_id,
                image_analysis_id,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                'transcription_segment'::report_evidence_type,
                $3::uuid,
                NULL,
                NOW()
            )
            """,
            str(uuid4()),
            report_section_id,
            transcription_segment_id,
        )

    async def insert_report_section_source_image(
        self,
        report_section_id: str,
        image_analysis_id: str,
    ) -> None:
        await self.connection.execute(
            """
            INSERT INTO report_section_evidence (
                id,
                report_section_id,
                evidence_type,
                transcription_segment_id,
                image_analysis_id,
                created_at
            )
            VALUES (
                $1::uuid,
                $2::uuid,
                'image_analysis'::report_evidence_type,
                NULL,
                $3::uuid,
                NOW()
            )
            """,
            str(uuid4()),
            report_section_id,
            image_analysis_id,
        )
