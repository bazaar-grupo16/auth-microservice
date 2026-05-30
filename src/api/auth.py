"""Authentication endpoints for JWT generation and validation."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse

from src.core.dependencies import DbSession
from src.schemas.auth import (
    TokenCreateRequest,
    TokenCreateResponse,
    TokenRefreshRequest,
)
from src.services.jwt_service import (
    TokenValidationError,
    issue_token_pair,
    revoke_user_tokens,
    rotate_refresh_token,
    validate_access_token,
)


router = APIRouter(tags=["Auth"])


@router.post(
    "/token",
    response_model=TokenCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an access token",
)
async def create_token(payload: TokenCreateRequest, db: DbSession) -> TokenCreateResponse:
    """Issue a JWT signed with the service secret key."""
    tokens = issue_token_pair(payload.user_id, payload.is_admin, db)
    return TokenCreateResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        refresh_expires_in=tokens.refresh_expires_in,
    )


@router.post(
    "/token/refresh",
    response_model=TokenCreateResponse,
    summary="Refresh an access token",
)
async def refresh_token(payload: TokenRefreshRequest, db: DbSession) -> TokenCreateResponse:
    """Rotate refresh token and issue a new access/refresh token pair."""
    try:
        tokens = rotate_refresh_token(payload.refresh_token, db)
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return TokenCreateResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        refresh_expires_in=tokens.refresh_expires_in,
    )


@router.delete(
    "/token/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke all tokens for a user",
)
async def revoke_tokens(user_id: UUID, db: DbSession) -> None:
    """Revoke all active refresh tokens for a user. Called internally on logout or ban."""
    revoke_user_tokens(user_id, db)


@router.get(
    "/validate",
    status_code=status.HTTP_200_OK,
    summary="Validate an access token",
)
async def validate_token(authorization: str | None = Header(default=None)) -> JSONResponse:
    """Validate JWT from Authorization header for reverse-proxy auth checks."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    try:
        claims = validate_access_token(token)
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "valid", "user_id": str(claims.user_id)},
        headers={
            "X-User-ID": str(claims.user_id),
            "X-Is-Admin": str(claims.is_admin).lower(),
        },
    )
