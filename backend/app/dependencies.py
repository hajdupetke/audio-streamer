"""FastAPI dependency functions used across multiple routers."""
import uuid

from fastapi import Depends, HTTPException, Query, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth import decode_access_token


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Reads the access_token httpOnly cookie and returns the authenticated User.
    Raises HTTP 401 on any auth failure.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_id_str = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Malformed token")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None instead of raising 401. Useful for optional auth."""
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


async def get_current_user_for_stream(
    request: Request,
    token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Auth for the stream endpoint.
    Tries the access_token cookie first; falls back to ?token= query param
    so that HTML <audio src="...?token=..."> works without cookie access.
    """
    raw_token = request.cookies.get("access_token") or token
    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_id_str = decode_access_token(raw_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Malformed token")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
