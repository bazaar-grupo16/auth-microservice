"""Repository helpers for refresh token persistence."""

from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.refresh_token import RefreshToken


async def create_refresh_token(
    db: AsyncSession,
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
    await db.commit()
    await db.refresh(row)
    return row


async def get_refresh_token_by_id(db: AsyncSession, token_id: str) -> RefreshToken | None:
    """Fetch a refresh token row by primary key."""
    return await db.get(RefreshToken, token_id)


async def revoke_refresh_token(db: AsyncSession, refresh_token: RefreshToken) -> None:
    """Mark a refresh token row as revoked."""
    refresh_token.revoked_at = datetime.now(timezone.utc)
    db.add(refresh_token)
    await db.commit()


async def revoke_all_refresh_tokens_for_user(db: AsyncSession, user_id: str) -> None:
    """Mark all active refresh tokens for a user as revoked."""
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
