"""Auth service — all auth business logic lives here, no FastAPI concerns."""
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.refresh_token import RefreshToken
from app.models.user import User

settings = get_settings()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_access_token(token: str) -> str:
    """Decode a JWT access token and return the user_id string. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    sub = payload.get("sub")
    if sub is None:
        raise JWTError("Missing subject claim")
    return sub


# ── User queries ──────────────────────────────────────────────────────────────

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


# ── Auth operations ───────────────────────────────────────────────────────────

async def create_user(db: AsyncSession, email: str, password: str) -> User:
    """Register a new user. Raises ValueError if email already in use."""
    existing = await get_user_by_email(db, email)
    if existing:
        raise ValueError("Email already registered")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(email=email, hashed_password=hashed)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Verify credentials. Raises ValueError on failure (intentionally vague message)."""
    user = await get_user_by_email(db, email)
    if not user or not bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
        raise ValueError("Invalid email or password")
    return user


async def create_auth_tokens(db: AsyncSession, user_id: uuid.UUID) -> tuple[str, str]:
    """Issue a new access token + opaque refresh token. Returns (access_token, raw_refresh_token)."""
    access_token = _create_access_token(user_id)

    raw_refresh = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=_hash_refresh_token(raw_refresh),
        expires_at=expires_at,
    )
    db.add(db_token)
    await db.commit()

    return access_token, raw_refresh


async def rotate_refresh_token(db: AsyncSession, raw_token: str) -> tuple[str, str]:
    """
    Validate and rotate a refresh token.
    - If revoked: reuse detected → revoke ALL tokens for user, raise ValueError
    - If expired: raise ValueError
    - On success: revoke old token, issue new pair
    Returns (new_access_token, new_raw_refresh_token).
    """
    token_hash = _hash_refresh_token(raw_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise ValueError("Invalid refresh token")

    if db_token.revoked:
        # Reuse detected: a revoked token was presented — assume compromise.
        # Revoke every active token for this user to force full re-auth.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == db_token.user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await db.commit()
        raise ValueError("Session invalidated due to token reuse. Please log in again.")

    # Normalize to UTC-aware for comparison
    expires_at = db_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise ValueError("Refresh token expired")

    # Issue new tokens — Python-side uuid.uuid4() default fires on construction,
    # so new_db_token.id is available immediately without a flush.
    new_access = _create_access_token(db_token.user_id)
    raw_new_refresh = secrets.token_urlsafe(32)
    new_db_token = RefreshToken(
        user_id=db_token.user_id,
        token_hash=_hash_refresh_token(raw_new_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_db_token)

    # Revoke old token and record the rotation chain
    db_token.revoked = True
    db_token.replaced_by = new_db_token.id

    await db.commit()

    return new_access, raw_new_refresh


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    """Revoke a single refresh token (used on logout). Silent no-op if not found."""
    token_hash = _hash_refresh_token(raw_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    db_token = result.scalar_one_or_none()
    if db_token and not db_token.revoked:
        db_token.revoked = True
        await db.commit()
