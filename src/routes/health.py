from fastapi import APIRouter

from src.http.v1.response.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the current health status of the service.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")
