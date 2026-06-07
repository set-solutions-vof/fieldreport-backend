from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.exceptions import InviteAlreadyExists, InviteEmailDeliveryFailed
from src.http.v1.request.onboarding import CreateInviteRequest, UpdateCompanyOnboardingRequest
from src.http.v1.response.onboarding import (
    CompanyOnboardingResponse,
    InviteCreatedResponse,
    InviteResponse,
)
from src.models.auth.authentication import CurrentUser
from src.models.onboarding.company import CompanyOnboardingUpdate
from src.security.authentication import require_admin
from src.services import onboarding

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
    company = await onboarding.get_company(str(current_user.company_id))

    return CompanyOnboardingResponse.model_validate(company.model_dump())


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
    company = await onboarding.update_company(
        str(current_user.company_id),
        CompanyOnboardingUpdate(
            logo_url=request_body.logo_url,
            primary_color=request_body.primary_color,
            onboarding_completed=request_body.onboarding_completed,
            update_logo_url="logo_url" in fields,
            update_primary_color="primary_color" in fields,
            update_onboarding_completed="onboarding_completed" in fields,
        ),
    )

    return CompanyOnboardingResponse.model_validate(company.model_dump())


@router.post(
    "/api/v1/onboarding/invites",
    response_model=InviteCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create onboarding invite",
    description="Creates an invite for the current company.",
)
async def create_invite(
    request_body: CreateInviteRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> InviteCreatedResponse:
    try:
        invite = await onboarding.create_invite(
            str(current_user.company_id),
            request_body.email,
            request_body.role,
        )
    except InviteAlreadyExists:
        raise HTTPException(status_code=409, detail="Invite already exists")
    except InviteEmailDeliveryFailed:
        raise HTTPException(status_code=502, detail="Invite email could not be sent")

    return InviteCreatedResponse.model_validate(invite.model_dump())


@router.get(
    "/api/v1/onboarding/invites",
    response_model=list[InviteResponse],
    summary="List onboarding invites",
    description="Returns invites for the current company.",
)
async def list_invites(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> list[InviteResponse]:
    invites = await onboarding.list_invites(str(current_user.company_id))

    return [InviteResponse.model_validate(invite.model_dump()) for invite in invites]


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
    was_deleted = await onboarding.delete_pending_invite(
        str(current_user.company_id),
        invite_id,
    )

    if not was_deleted:
        raise HTTPException(status_code=404, detail="Invite not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
