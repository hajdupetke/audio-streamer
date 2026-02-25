from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.addons.seeder import seed_addons_for_user
from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


# ── Cookie helpers ────────────────────────────────────────────────────────────

def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.environment != "development"
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        user = await auth_service.create_user(db, data.email, data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Install all currently registered bundled addons for the new user
    await seed_addons_for_user(db, user.id)

    access_token, refresh_token = await auth_service.create_auth_tokens(db, user.id)
    _set_auth_cookies(response, access_token, refresh_token)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=UserResponse)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        user = await auth_service.authenticate_user(db, data.email, data.password)
    except ValueError:
        # Keep the message vague regardless of whether email exists
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token, refresh_token = await auth_service.create_auth_tokens(db, user.id)
    _set_auth_cookies(response, access_token, refresh_token)
    return UserResponse.model_validate(user)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw_token = request.cookies.get("refresh_token")
    if raw_token:
        await auth_service.revoke_refresh_token(db, raw_token)
    _clear_auth_cookies(response)
    return {"ok": True}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        new_access, new_refresh = await auth_service.rotate_refresh_token(db, raw_token)
    except ValueError as e:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail=str(e))

    _set_auth_cookies(response, new_access, new_refresh)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get("/token")
async def get_token(request: Request) -> dict:
    """Return the current access token value so the frontend can build ?token= stream URLs."""
    token = request.cookies.get("access_token")
    if not token:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"access_token": token}
