from fastapi import APIRouter, HTTPException, status

from src.exceptions import InviteInvalid
from src.http.v1.request.invite import AcceptInviteRequest
from src.http.v1.response.auth import TokenResponse
from src.http.v1.response.invite import InvitePreviewResponse
from src.services import invites

router = APIRouter(tags=["Invites"])


@router.get(
    "/api/v1/invites/{token}",
    response_model=InvitePreviewResponse,
    summary="Get invite preview",
    description="Returns invite details for a public invite acceptance page.",
)
async def get_invite_preview(token: str) -> InvitePreviewResponse:
    try:
        invite_preview = await invites.get_invite_preview(token)
    except InviteInvalid:
        raise HTTPException(status_code=404, detail="Invite not found")

    return InvitePreviewResponse.model_validate(invite_preview.model_dump())


@router.post(
    "/api/v1/invites/{token}/accept",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Accept invite",
    description="Accepts an invite and creates the invited user account.",
)
async def accept_invite(token: str, request_body: AcceptInviteRequest) -> TokenResponse:
    try:
        token_pair = await invites.accept_invite(
            token,
            request_body.name,
            request_body.password,
        )
    except InviteInvalid:
        raise HTTPException(status_code=400, detail="Invite is invalid")

    return TokenResponse.model_validate(token_pair)
