from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.http.v1.request.template import TemplateStructureRequest
from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import (
    TemplateStatus,
    TemplateStatusActive,
)
from src.security.authentication import require_admin
from src.services import templates, templates_state

router = APIRouter(prefix="/api/v1/template")


@router.get("")
async def get_template_configuration(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateStatus:
    return await templates.load_template_configuration(str(current_user.company_id))


@router.post("/analysis")
async def start_template_analysis(
    files: Annotated[list[UploadFile], File()],
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateStatus:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    return await templates.start_template_analysis(current_user, files)


@router.get("/analysis/{job_id}")
async def get_template_analysis(
    job_id: str,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateStatus:
    try:
        job = await templates.get_template_analysis_job(current_user, job_id)

        return templates_state.resolve_template_job_state(job)
    except LookupError:
        raise HTTPException(status_code=404, detail="Template analysis not found")


@router.post("")
async def confirm_template(
    request_body: TemplateStructureRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateStatusActive:
    return await templates.confirm_template(current_user, request_body.sections)
