from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from src.exceptions import TemplateConfirmationNotAllowed
from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import (
    TemplateStatus,
    TemplateStatusActive,
)
from src.models.templates.domain import TemplateStructure
from src.security.authentication import get_current_user, get_pdf_preview_user, require_admin
from src.services import report_pdf, templates

router = APIRouter(tags=["Template"])


@router.get(
    "/api/v1/template/preview-pdf",
    summary="Get template preview PDF",
    description="Returns the company's imported template as a preview PDF.",
)
async def get_template_preview_pdf(
    current_user: Annotated[CurrentUser, Depends(get_pdf_preview_user)],
) -> Response:
    try:
        pdf_bytes = await report_pdf.render_template_preview_to_pdf(str(current_user.company_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="Template preview not found")

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
