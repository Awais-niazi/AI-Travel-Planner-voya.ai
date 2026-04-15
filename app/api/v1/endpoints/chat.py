from fastapi import APIRouter, HTTPException, Request, status

from app.core.dependencies import CurrentUser, DBSession, enforce_rate_limit
from app.repositories.trip import TripRepository
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.ai_service import ai_service
from app.services.ai_protection_service import AIServiceUnavailable
from app.services.feature_gate_service import ensure_ai_chat_enabled

router = APIRouter(prefix="/chat", tags=["AI Chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request, current_user: CurrentUser, db: DBSession):
    """
    Multi-turn AI travel guide chat.
    Optionally provide trip_id to give the AI context about the user's current trip.
    """
    enforce_rate_limit(
        request,
        scope="chat",
        max_requests=20,
        window_seconds=60,
        user_id=str(current_user.id),
    )
    ensure_ai_chat_enabled()
    trip_context = None

    if body.trip_id:
        repo = TripRepository(db)
        trip = await repo.get_by_id(body.trip_id)
        if trip and trip.user_id == current_user.id:
            trip_context = (
                f"{trip.num_days}-day trip to {trip.destination}, "
                f"budget: {trip.budget_level}, "
                f"style: {trip.travel_style}, "
                f"interests: {', '.join(trip.interests or [])}"
            )

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    try:
        reply = await ai_service.chat(messages=messages, trip_context=trip_context)
    except AIServiceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return ChatResponse(reply=reply, trip_context=trip_context)
