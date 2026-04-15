from fastapi import HTTPException, status

from app.core.config import settings


def ensure_ai_chat_enabled() -> None:
    if not settings.enable_ai_chat:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI chat is temporarily unavailable",
        )


def ensure_trip_generation_enabled() -> None:
    if not settings.enable_trip_generation:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trip generation is temporarily unavailable",
        )
