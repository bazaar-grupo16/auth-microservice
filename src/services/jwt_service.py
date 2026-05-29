"""Service helpers for issuing and validating JWT access/refresh tokens."""

from dataclasses import dataclass
from hashlib import sha256
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from uuid import UUID

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.repositories.refresh_token_repository import (
    create_refresh_token,
    get_refresh_token_by_id,
    revoke_all_refresh_tokens_for_user,
    revoke_refresh_token,
)


class TokenValidationError(ValueError):
    """Raised when a JWT cannot be validated."""


@dataclass(frozen=True)
class TokenPair:
    """Represents an issued access/refresh token pair with expiration metadata."""

    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int


def _encode_token(payload: dict[str, object]) -> str:
    """Sign and encode a JWT payload using configured algorithm and secret."""
    settings = get_settings()
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _decode_token(token: str) -> dict[str, object]:
    """Decode a JWT and raise normalized validation errors."""
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except ExpiredSignatureError as exc:
        raise TokenValidationError("Token has expired") from exc
    except InvalidTokenError as exc:
        raise TokenValidationError("Token is invalid") from exc

    if not isinstance(payload, dict):
        raise TokenValidationError("Token payload is invalid")

    return payload


def _token_hash(token: str) -> str:
    """Return a deterministic SHA-256 hash for secure token storage."""
    return sha256(token.encode("utf-8")).hexdigest()


def issue_token_pair(user_id: UUID, db: Session) -> TokenPair:
    """Issue access and refresh tokens and persist hashed refresh token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    access_expires_delta = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_payload: dict[str, object] = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + access_expires_delta,
    }
    access_token = _encode_token(access_payload)

    refresh_expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token_id = str(uuid4())
    refresh_payload: dict[str, object] = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": refresh_token_id,
        "iat": now,
        "exp": now + refresh_expires_delta,
    }
    refresh_token = _encode_token(refresh_payload)
    create_refresh_token(
        db=db,
        token_id=refresh_token_id,
        user_id=str(user_id),
        token_hash=_token_hash(refresh_token),
        expires_at=now + refresh_expires_delta,
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_expires_delta.total_seconds()),
        refresh_expires_in=int(refresh_expires_delta.total_seconds()),
    )


def rotate_refresh_token(refresh_token: str, db: Session) -> TokenPair:
    """Validate and rotate a refresh token, returning a fresh token pair."""
    payload = _decode_token(refresh_token)

    token_type = payload.get("type")
    if token_type != "refresh":
        raise TokenValidationError("Token type is invalid for refresh")

    token_id = payload.get("jti")
    if not token_id or not isinstance(token_id, str):
        raise TokenValidationError("Token is missing token id")

    user_id_claim = payload.get("sub")
    if not user_id_claim:
        raise TokenValidationError("Token is missing subject claim")

    try:
        user_id = UUID(str(user_id_claim))
    except ValueError as exc:
        raise TokenValidationError("Token subject is not a valid UUID") from exc

    row = get_refresh_token_by_id(db, token_id)
    if row is None:
        raise TokenValidationError("Refresh token is not recognized")
    if row.revoked_at is not None:
        raise TokenValidationError("Refresh token has been revoked")
    if row.expires_at < datetime.now(timezone.utc):
        raise TokenValidationError("Refresh token has expired")
    if row.token_hash != _token_hash(refresh_token):
        raise TokenValidationError("Refresh token is invalid")

    revoke_refresh_token(db, row)
    return issue_token_pair(user_id, db)


def revoke_user_tokens(user_id: UUID, db: Session) -> None:
    """Revoke all active refresh tokens for a user."""
    revoke_all_refresh_tokens_for_user(db, str(user_id))


def validate_access_token(token: str) -> UUID:
    """Validate a signed JWT and return the UUID from the ``sub`` claim."""
    payload = _decode_token(token)

    token_type = payload.get("type")
    if token_type != "access":
        raise TokenValidationError("Token type is invalid for this endpoint")

    user_id_claim = payload.get("sub")
    if not user_id_claim:
        raise TokenValidationError("Token is missing subject claim")

    try:
        return UUID(str(user_id_claim))
    except ValueError as exc:
        raise TokenValidationError("Token subject is not a valid UUID") from exc
