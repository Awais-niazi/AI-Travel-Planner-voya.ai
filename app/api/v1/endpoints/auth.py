from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DBSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.repositories.user import UserRepository
from app.schemas.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DBSession):
    repo = UserRepository(db)

    existing = await repo.get_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = await repo.create(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DBSession):
    repo = UserRepository(db)
    user = await repo.get_by_email(body.email)

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: DBSession):
    from uuid import UUID

    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: CurrentUser):
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_me(body: UserUpdate, current_user: CurrentUser, db: DBSession):
    repo = UserRepository(db)
    updated = await repo.update(
        current_user,
        full_name=body.full_name,
        avatar_url=body.avatar_url,
        preferences=body.preferences,
    )
    return updated