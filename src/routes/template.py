from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status

from src.exceptions import ActiveTemplateNotFound, TemplateAnalysisJobNotFound
from src.http.v1.request.template import StartTemplateAnalysisRequest
from src.models.auth.authentication import CurrentUser
from src.models.templates import status_resolver
from src.models.templates.configuration import (
    TemplateStatus,
    TemplateStatusActive,
)
from src.models.templates.domain import TemplateStructure
from src.security.authentication import get_current_user, require_admin
from src.services import templates

router = APIRouter(tags=["Template"])


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
    "/api/v1/template/analysis",
    response_model=TemplateStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start template analysis",
    description="Uploads example PDFs and queues template structure analysis.",
)
async def start_template_analysis(
    request_body: Annotated[StartTemplateAnalysisRequest, Form()],
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateStatus:
    return await templates.start_template_analysis(current_user, request_body.files)


@router.get(
    "/api/v1/template/analysis/{job_id}",
    response_model=TemplateStatus,
    summary="Get template analysis",
    description="Returns the status and result of a template analysis job.",
)
async def get_template_analysis(
    job_id: str,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateStatus:
    try:
        job = await templates.get_template_analysis_job(current_user, job_id)

        return status_resolver.resolve_template_job_state(job)
    except TemplateAnalysisJobNotFound:
        raise HTTPException(status_code=404, detail="Template analysis not found")


@router.post(
    "/api/v1/template",
    response_model=TemplateStatusActive,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm template",
    description="Activates the reviewed template structure for the company.",
)
async def confirm_template(
    request_body: TemplateStructure,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TemplateStatusActive:
    try:
        return await templates.confirm_template(current_user, request_body)
    except ActiveTemplateNotFound:
        raise HTTPException(status_code=400, detail="Template not configured")
