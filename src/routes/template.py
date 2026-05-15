from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.http.v1.request.template import TemplateConfigurationRequest
from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import (
    TemplateAnalysisConfiguration,
    TemplateConfiguration,
    TemplateConfigurationActive,
)
from src.security.authentication import require_admin
from src.services import templates

router = APIRouter(prefix="/api/v1/template")


@router.get("")
async def get_template_configuration(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateConfiguration:
    return await templates.get_template_configuration(current_user)


@router.post("/analysis")
async def start_template_analysis(
    files: Annotated[list[UploadFile], File()],
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateConfiguration:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    return await templates.start_template_analysis(current_user, files)


@router.get("/analysis/{job_id}")
async def get_template_analysis(
    job_id: str,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateAnalysisConfiguration:
    try:
        return await templates.get_template_analysis(current_user, job_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Template analysis not found")


@router.post("")
async def confirm_template(
    request_body: TemplateConfigurationRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateConfigurationActive:
    return await templates.confirm_template(current_user, request_body.sections)
