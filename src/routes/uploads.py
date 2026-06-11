from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from src.models.auth.authentication import CurrentUser
from src.security.authentication import require_admin
from src.storage import blob
from src.utils.images import normalize_to_jpeg

router = APIRouter(tags=["Uploads"])


@router.post("/api/v1/uploads/logo")
async def upload_logo(
    file: UploadFile,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> dict[str, str]:
    content_type = file.content_type or ""

    if content_type not in {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
        "image/heic-sequence",
    }:
        raise HTTPException(status_code=422, detail="Unsupported logo content type")

    data = await file.read()

    if len(data) > 5_000_000:
        raise HTTPException(status_code=413, detail="Logo file too large")

    data, content_type = normalize_to_jpeg(data, content_type)
    key = f"{current_user.company_id}/{uuid4()}"
    url = await blob.upload_file("logos", key, data, content_type)
    return {"url": url}
