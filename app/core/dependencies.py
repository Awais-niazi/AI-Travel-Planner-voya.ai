from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.rate_limit_service import rate_limiter

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

    # Use the subject string directly — do NOT convert through UUID()
    # UUID() strips dashes and produces a different string than what was stored
    user_id: str = payload.get("sub", "")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

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


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(
    request: Request,
    scope: str,
    max_requests: int,
    window_seconds: int,
    user_id: str | None = None,
) -> None:
    client_ip = _client_ip(request)
    keys = [f"{scope}:ip:{client_ip}"]
    if user_id:
        keys.append(f"{scope}:user:{user_id}")

    retry_after = 0
    for key in keys:
        allowed, retry_after = rate_limiter.check(key, max_requests=max_requests, window_seconds=window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again soon.",
                headers={"Retry-After": str(retry_after)},
            )
