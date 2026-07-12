from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ok
from app.database.session import get_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    RegisterRequest,
    UserPublic,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new driver or owner",
    responses={409: {"description": "Email already registered"}},
)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)) -> dict:
    user, token = await AuthService(session).register(payload)
    body = AuthTokenResponse(access_token=token, user=UserPublic.model_validate(user))
    return ok(body.model_dump(mode="json"), message="Account created")


@router.post(
    "/login",
    summary="Sign in with email and password",
    responses={401: {"description": "Invalid credentials"}},
)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> dict:
    user, token = await AuthService(session).login(payload)
    body = AuthTokenResponse(access_token=token, user=UserPublic.model_validate(user))
    return ok(body.model_dump(mode="json"), message="Signed in")


@router.get(
    "/me",
    summary="Get current authenticated user",
    responses={401: {"description": "Not authenticated"}},
)
async def me(user: User = Depends(get_current_user)) -> dict:
    return ok(UserPublic.model_validate(user).model_dump(mode="json"))
