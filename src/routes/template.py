from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.http.v1.request.template import (
    TemplateConfigurationRequest,
    UpdateTemplateStructureRequest,
)
from src.http.v1.response.template import template_configuration_response
from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import (
    TemplateConfiguration,
    TemplateConfigurationActive,
)
from src.security.authentication import require_admin
from src.services import templates, templates_state

router = APIRouter(prefix="/api/v1/template")


@router.get("")
async def get_template_configuration(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateConfiguration:
    state = await templates.load_template_company_state(str(current_user.company_id))

    return template_configuration_response(state)


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
) -> TemplateConfiguration:
    try:
        job = await templates.get_template_analysis_job(current_user, job_id)

        return template_configuration_response(templates_state.resolve_template_job_state(job))
    except LookupError:
        raise HTTPException(status_code=404, detail="Template analysis not found")


@router.patch("/analysis/{job_id}", status_code=204)
async def update_template_analysis_structure(
    job_id: str,
    request_body: UpdateTemplateStructureRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> None:
    await templates.update_pending_template_structure(
        current_user,
        job_id,
        request_body.sections,
    )


@router.post("")
async def confirm_template(
    request_body: TemplateConfigurationRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateConfigurationActive:
    return await templates.confirm_template(current_user, request_body.sections)
