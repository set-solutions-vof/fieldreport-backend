import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.db import onboarding_queries
from src.http.v1.request.onboarding import CreateInviteRequest, UpdateCompanyOnboardingRequest
from src.http.v1.response.onboarding import (
    CompanyOnboardingResponse,
    InviteCreatedResponse,
    InviteResponse,
)
from src.models.auth.authentication import CurrentUser
from src.security.authentication import require_admin

router = APIRouter(tags=["Onboarding"])


@router.get(
    "/api/v1/onboarding/company",
    response_model=CompanyOnboardingResponse,
    summary="Get onboarding company state",
    description="Returns the current company's branding and onboarding state.",
)
async def get_company(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> CompanyOnboardingResponse:
    return await onboarding_queries.get_company(str(current_user.company_id))


@router.patch(
    "/api/v1/onboarding/company",
    response_model=CompanyOnboardingResponse,
    summary="Update onboarding company state",
    description="Updates the current company's branding and onboarding state.",
)
async def update_company(
    request_body: UpdateCompanyOnboardingRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> CompanyOnboardingResponse:
    fields = request_body.model_dump(exclude_unset=True)

    return await onboarding_queries.update_company(
        str(current_user.company_id),
        request_body.logo_url,
        request_body.primary_color,
        request_body.onboarding_completed,
        "logo_url" in fields,
        "primary_color" in fields,
        "onboarding_completed" in fields,
    )


@router.post(
    "/api/v1/onboarding/invites",
    response_model=InviteCreatedResponse,
    summary="Create onboarding invite",
    description="Creates an invite for the current company.",
)
async def create_invite(
    request_body: CreateInviteRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> InviteCreatedResponse:
    has_pending_invite = await onboarding_queries.has_pending_invite(
        str(current_user.company_id),
        request_body.email,
    )

    if has_pending_invite:
        raise HTTPException(status_code=409, detail="Invite already exists")

    token = secrets.token_hex(32)
    expires_at = datetime.now(UTC) + timedelta(days=7)

    return await onboarding_queries.create_invite(
        str(current_user.company_id),
        request_body.email,
        request_body.role,
        token,
        expires_at,
    )


@router.get(
    "/api/v1/onboarding/invites",
    response_model=list[InviteResponse],
    summary="List onboarding invites",
    description="Returns invites for the current company.",
)
async def list_invites(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> list[InviteResponse]:
    return await onboarding_queries.list_invites(str(current_user.company_id))


@router.delete(
    "/api/v1/onboarding/invites/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete onboarding invite",
    description="Deletes a pending invite for the current company.",
)
async def delete_invite(
    invite_id: str,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> Response:
    was_deleted = await onboarding_queries.delete_pending_invite(
        str(current_user.company_id),
        invite_id,
    )

    if not was_deleted:
        raise HTTPException(status_code=404, detail="Invite not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
