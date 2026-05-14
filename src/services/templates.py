import re
from typing import Literal, NotRequired, TypedDict, cast
from uuid import uuid4

from fastapi import UploadFile

from src.integrations import template_repository
from src.models.auth.authentication import CurrentUser
from src.models.templates.template import (
    TemplateConfigurationActive,
    TemplateConfigurationExtracting,
    TemplateConfigurationNotConfigured,
    TemplateConfigurationPendingReview,
    TemplateSection,
)

StoredRenderType = Literal[
    "text_block",
    "key_value_table",
    "measurement_table",
    "photo_grid",
]
ApiTemplateType = Literal["text", "kv", "measure", "photo"]

RENDER_TYPE_BY_API_TYPE: dict[ApiTemplateType, StoredRenderType] = {
    "text": "text_block",
    "kv": "key_value_table",
    "measure": "measurement_table",
    "photo": "photo_grid",
}
API_TYPE_BY_RENDER_TYPE: dict[StoredRenderType, ApiTemplateType] = {
    value: key for key, value in RENDER_TYPE_BY_API_TYPE.items()
}


class TemplateAnalysisNotFoundError(Exception):
    pass


class StoredTemplateSection(TypedDict):
    id: str
    key: str
    label: str
    order: int
    render_type: StoredRenderType
    fields: NotRequired[list[str] | None]


class StoredTemplateStructure(TypedDict):
    sections: list[StoredTemplateSection]


def build_default_sections() -> list[TemplateSection]:
    return [
        TemplateSection(id="summary", label="Summary", type="text"),
        TemplateSection(
            id="findings",
            label="Findings",
            type="kv",
            fields=["Location", "Issue", "Recommendation"],
        ),
        TemplateSection(
            id="measurements",
            label="Measurements",
            type="measure",
            fields=["Metric", "Value", "Unit"],
        ),
        TemplateSection(id="photos", label="Photos", type="photo"),
    ]


def build_structure(sections: list[TemplateSection]) -> StoredTemplateStructure:
    stored_sections: list[StoredTemplateSection] = []

    for index, section in enumerate(sections):
        stored_sections.append(
            {
                "id": section.id,
                "key": slugify(section.label),
                "label": section.label,
                "order": index,
                "render_type": RENDER_TYPE_BY_API_TYPE[section.type],
                "fields": section.fields,
            }
        )

    return {"sections": stored_sections}


def slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def map_sections(structure: StoredTemplateStructure | None) -> list[TemplateSection]:
    if structure is None:
        return []

    sections = structure["sections"]

    return [
        TemplateSection(
            id=section["id"],
            label=section["label"],
            type=API_TYPE_BY_RENDER_TYPE[cast(StoredRenderType, section["render_type"])],
            fields=section.get("fields"),
        )
        for section in sorted(sections, key=lambda section: section["order"])
    ]


async def get_template_configuration(
    user: CurrentUser,
) -> (
    TemplateConfigurationNotConfigured
    | TemplateConfigurationExtracting
    | TemplateConfigurationPendingReview
    | TemplateConfigurationActive
):
    company_row, job_row = await template_repository.get_company_template_context(
        str(user.company_id)
    )

    if job_row is not None:
        if job_row["status"] == "extracting":
            return TemplateConfigurationExtracting(
                status="extracting",
                jobId=str(job_row["id"]),
                reports_count=job_row["reports_count"],
            )

        if job_row["status"] == "pending_review":
            return TemplateConfigurationPendingReview(
                status="pending_review",
                reports_count=job_row["reports_count"],
                sections=map_sections(job_row["structure"]),
            )

        if job_row["status"] == "active":
            return TemplateConfigurationActive(
                status="active",
                reports_count=job_row["reports_count"],
                sections=map_sections(job_row["structure"]),
            )

    if company_row["active_template_id"] is not None:
        return TemplateConfigurationActive(
            status="active",
            reports_count=0,
            sections=map_sections(company_row["active_structure"]),
        )

    return TemplateConfigurationNotConfigured(status="not_configured")


async def start_template_analysis(
    user: CurrentUser,
    files: list[UploadFile],
) -> TemplateConfigurationExtracting:
    job_id = str(uuid4())

    await template_repository.replace_template_analysis_job(
        job_id, str(user.company_id), len(files)
    )

    return TemplateConfigurationExtracting(
        status="extracting",
        jobId=job_id,
        reports_count=len(files),
    )


async def get_template_analysis(
    user: CurrentUser,
    job_id: str,
) -> (
    TemplateConfigurationExtracting
    | TemplateConfigurationPendingReview
    | TemplateConfigurationActive
):
    job_row = await template_repository.get_template_analysis_job(job_id, str(user.company_id))

    if job_row is None:
        raise TemplateAnalysisNotFoundError

    if job_row["status"] == "extracting":
        sections = build_default_sections()
        structure = build_structure(sections)

        await template_repository.update_template_analysis_job(job_id, "pending_review", structure)

        return TemplateConfigurationPendingReview(
            status="pending_review",
            reports_count=job_row["reports_count"],
            sections=sections,
        )

    if job_row["status"] == "pending_review":
        return TemplateConfigurationPendingReview(
            status="pending_review",
            reports_count=job_row["reports_count"],
            sections=map_sections(job_row["structure"]),
        )

    return TemplateConfigurationActive(
        status="active",
        reports_count=job_row["reports_count"],
        sections=map_sections(job_row["structure"]),
    )


async def confirm_template(
    user: CurrentUser,
    sections: list[TemplateSection],
) -> TemplateConfigurationActive:
    company_row, job_row = await template_repository.get_company_template_context(
        str(user.company_id)
    )
    structure = build_structure(sections)
    template_id = str(uuid4())

    await template_repository.create_template(str(user.company_id), template_id, structure)
    await template_repository.set_active_template(str(user.company_id), template_id)

    if job_row is not None:
        await template_repository.update_template_analysis_job(
            str(job_row["id"]),
            "active",
            structure,
            template_id,
        )

    reports_count = job_row["reports_count"] if job_row is not None else 0

    if reports_count == 0 and company_row["active_template_id"] is not None:
        reports_count = 0

    return TemplateConfigurationActive(
        status="active",
        reports_count=reports_count,
        sections=sections,
    )
