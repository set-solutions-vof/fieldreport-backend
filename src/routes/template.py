from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Response

from src.db.connection import get_database
from src.db.schema.tables import company
from src.db.schema.tables import templates as templates_table
from src.exceptions import TemplateConfirmationNotAllowed
from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import (
    TemplateStatus,
    TemplateStatusActive,
)
from src.models.templates.domain import TemplateStructure
from src.security.authentication import get_current_user, get_pdf_preview_user, require_admin
from src.services import templates
from src.storage.blob import download_file

router = APIRouter(tags=["Template"])


@router.get(
    "/api/v1/template/preview-pdf",
    summary="Get template preview PDF",
    description="Returns the company's imported template as a preview PDF.",
)
async def get_template_preview_pdf(
    current_user: Annotated[CurrentUser, Depends(get_pdf_preview_user)],
) -> Response:
    stmt = (
        sa.select(templates_table.c.preview_pdf_storage_key)
        .select_from(
            company.join(templates_table, templates_table.c.id == company.c.current_template_id)
        )
        .where(company.c.id == str(current_user.company_id))
    )
    async with get_database().acquire() as conn:
        row = (await conn.execute(stmt)).mappings().first()

    if row is None or not row["preview_pdf_storage_key"]:
        raise HTTPException(status_code=404, detail="Template preview not found")

    pdf_bytes, _ = await download_file("templates", row["preview_pdf_storage_key"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="Rapportage Paneel - Preview.pdf"'},
    )


@router.get(
    "/api/v1/template",
    response_model=TemplateStatus,
    summary="Get template configuration",
    description="Returns the company's template configuration status.",
)
async def get_template_configuration(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> TemplateStatus:
    return await templates.load_template_configuration(str(current_user.company_id))


@router.post(
    "/api/v1/template",
    response_model=TemplateStatusActive,
    status_code=201,
    summary="Confirm template",
    description="Activates the reviewed template structure for the company.",
)
async def confirm_template(
    request_body: TemplateStructure,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateStatusActive:
    try:
        return await templates.confirm_template(current_user, request_body)
    except TemplateConfirmationNotAllowed:
        raise HTTPException(status_code=422, detail="Template cannot be confirmed")
