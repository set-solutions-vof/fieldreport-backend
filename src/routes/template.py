from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.http.v1.request.template import TemplateConfigurationRequest
from src.models.auth.authentication import CurrentUser
from src.security.authentication import get_current_user
from src.services import templates

router = APIRouter(prefix="/api/v1/template")


@router.get("")
async def get_template_configuration(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    configuration = await templates.get_template_configuration(current_user)

    return configuration.model_dump(exclude_none=True)


@router.post("/analysis")
async def start_template_analysis(
    files: Annotated[list[UploadFile], File()],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    configuration = await templates.start_template_analysis(current_user, files)

    return configuration.model_dump(exclude_none=True)


@router.get("/analysis/{job_id}")
async def get_template_analysis(
    job_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    try:
        configuration = await templates.get_template_analysis(current_user, job_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Template analysis not found")

    return configuration.model_dump(exclude_none=True)


@router.post("")
async def confirm_template(
    request_body: TemplateConfigurationRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    configuration = await templates.confirm_template(current_user, request_body.sections)

    return configuration.model_dump(exclude_none=True)
