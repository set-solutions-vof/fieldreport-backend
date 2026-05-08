from typing import Annotated

from fastapi import APIRouter, Depends

from src.models.auth.authentication import CurrentUser
from src.security.authentication import get_current_user

router = APIRouter(
    prefix="/api/v1/reports",
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def get_reports(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[dict[str, str]]:
    return [
        {
            "id": "demo-report",
            "company_id": str(current_user.company_id),
            "status": "draft",
        }
    ]
