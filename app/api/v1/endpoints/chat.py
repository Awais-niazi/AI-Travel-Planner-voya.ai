from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DBSession
from app.repositories.trip import TripRepository
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/chat", tags=["AI Chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, current_user: CurrentUser, db: DBSession):
    """
    Multi-turn AI travel guide chat.
    Optionally provide trip_id to give the AI context about the user's current trip.
    """
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

    reply = await ai_service.chat(messages=messages, trip_context=trip_context)

    return ChatResponse(reply=reply, trip_context=trip_context)