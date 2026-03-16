from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer()

DBSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DBSession,
) -> User:
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id: str = payload.get("sub", "")
    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(user_id))

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return user


async def get_current_premium_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
        )
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
PremiumUser = Annotated[User, Depends(get_current_premium_user)]


class Pagination:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size