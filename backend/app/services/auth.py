from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def register(self, payload: RegisterRequest) -> tuple[User, str]:
        existing = await self.users.get_by_email(payload.email)
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

        role = UserRole(payload.role)
        if role == UserRole.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot register as admin")

        user = User(
            full_name=payload.full_name.strip(),
            email=payload.email,
            phone=payload.phone.strip(),
            hashed_password=hash_password(payload.password),
            role=role,
            is_active=True,
        )
        user = await self.users.create(user)
        token = create_access_token(str(user.id), extra={"role": user.role.value})
        return user, token

    async def login(self, payload: LoginRequest) -> tuple[User, str]:
        user = await self.users.get_by_email(payload.email)
        if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        token = create_access_token(str(user.id), extra={"role": user.role.value})
        return user, token
