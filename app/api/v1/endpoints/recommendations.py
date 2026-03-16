from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser
from app.services.go_clients import recommendation_client

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("")
async def get_recommendations(
    destination: str = Query(min_length=2),
    interests: list[str] = Query(default=[]),
    budget_level: str = Query(default="mid"),
    travel_style: str = Query(default="couple"),
    current_user: CurrentUser = None,
):
    """
    Get AI-powered place recommendations for a destination.
    Proxies to the Go recommendation microservice.
    """
    return await recommendation_client.get_recommendations(
        destination=destination,
        interests=interests,
        budget_level=budget_level,
        travel_style=travel_style,
        user_id=current_user.id if current_user else None,
    )


@router.get("/places/{place_id}/similar")
async def get_similar_places(
    place_id: str,
    limit: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = None,
):
    """Get places similar to a given place — proxies to Go service."""
    return await recommendation_client.get_similar_places(place_id=place_id, limit=limit)


@router.post("/interactions")
async def record_interaction(
    place_id: str,
    interaction_type: str = Query(pattern="^(view|save|complete)$"),
    current_user: CurrentUser = None,
):
    """Record a user interaction to improve future recommendations."""
    if current_user:
        await recommendation_client.record_interaction(
            user_id=current_user.id,
            place_id=place_id,
            interaction_type=interaction_type,
        )
    return {"status": "recorded"}