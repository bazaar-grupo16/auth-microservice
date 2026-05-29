"""Repository helpers for refresh token persistence."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models.refresh_token import RefreshToken


def create_refresh_token(
    db: Session,
    token_id: str,
    user_id: str,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    """Persist a refresh token row."""
    row = RefreshToken(
        id=token_id,
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_refresh_token_by_id(db: Session, token_id: str) -> RefreshToken | None:
    """Fetch a refresh token row by primary key."""
    return db.get(RefreshToken, token_id)


def revoke_refresh_token(db: Session, refresh_token: RefreshToken) -> None:
    """Mark a refresh token row as revoked."""
    refresh_token.revoked_at = datetime.now(timezone.utc)
    db.add(refresh_token)
    db.commit()


def revoke_all_refresh_tokens_for_user(db: Session, user_id: str) -> None:
    """Mark all active refresh tokens for a user as revoked."""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": datetime.now(timezone.utc)})
    db.commit()
