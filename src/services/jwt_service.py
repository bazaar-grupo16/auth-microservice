"""Service helpers for issuing and validating JWT access tokens."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from src.core.config import get_settings


class TokenValidationError(ValueError):
    """Raised when a JWT cannot be validated."""


def generate_access_token(user_id: UUID) -> tuple[str, int]:
    """Generate a signed JWT including the user UUID in the ``sub`` claim."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, int(expires_delta.total_seconds())


def validate_access_token(token: str) -> UUID:
    """Validate a signed JWT and return the UUID from the ``sub`` claim."""
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

    user_id_claim = payload.get("sub")
    if not user_id_claim:
        raise TokenValidationError("Token is missing subject claim")

    try:
        return UUID(str(user_id_claim))
    except ValueError as exc:
        raise TokenValidationError("Token subject is not a valid UUID") from exc
