"""Pydantic schemas for JWT token endpoints."""

from uuid import UUID

from pydantic import BaseModel


class TokenCreateRequest(BaseModel):
    """Payload used to mint an access token for a user."""

    user_id: UUID
    is_admin: bool


class TokenCreateResponse(BaseModel):
    """Response returned after issuing an access/refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class TokenRefreshRequest(BaseModel):
    """Payload used to refresh an access token."""

    refresh_token: str
