from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile

from src.models.auth.authentication import CurrentUser
from src.security.authentication import require_admin
from src.storage import blob

router = APIRouter(tags=["Uploads"])


@router.post("/api/v1/uploads/logo")
async def upload_logo(
    file: UploadFile,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> dict[str, str]:
    key = str(uuid4())
    url = await blob.upload_form_file("logos", key, file)
    return {"url": url}
