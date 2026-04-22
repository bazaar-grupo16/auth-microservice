"""Authentication endpoints for JWT generation and validation."""

from fastapi import APIRouter, Header, HTTPException, status

from src.schemas.auth import (
    TokenCreateRequest,
    TokenCreateResponse,
)
from src.services.jwt_service import (
    TokenValidationError,
    generate_access_token,
    validate_access_token,
)


router = APIRouter(tags=["Auth"])


@router.post(
    "/token",
    response_model=TokenCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an access token",
)
async def create_token(payload: TokenCreateRequest) -> TokenCreateResponse:
    """Issue a JWT signed with the service secret key."""
    access_token, expires_in = generate_access_token(payload.user_id)
    return TokenCreateResponse(access_token=access_token, expires_in=expires_in)


@router.get(
    "/validate",
    status_code=status.HTTP_200_OK,
    summary="Validate an access token",
)
async def validate_token(authorization: str | None = Header(default=None)) -> dict[str, str]:
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
        user_id = validate_access_token(token)
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return {"status": "valid", "user_id": str(user_id)}
