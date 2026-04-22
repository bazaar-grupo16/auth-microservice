"""Pydantic schemas for JWT token endpoints."""

from uuid import UUID

from pydantic import BaseModel


class TokenCreateRequest(BaseModel):
    """Payload used to mint an access token for a user."""

    user_id: UUID


class TokenCreateResponse(BaseModel):
    """Response returned after creating an access token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
