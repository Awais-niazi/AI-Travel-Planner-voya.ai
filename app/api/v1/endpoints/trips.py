import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import CurrentUser, DBSession, Pagination
from app.repositories.trip import TripRepository
from app.schemas.schemas import (
    GenerateItineraryRequest,
    GenerateItineraryResponse,
    ItineraryUpdate,
    PaginatedResponse,
    TripCreate,
    TripOut,
    TripWithItinerary,
)
from app.services.ai_service import ai_service
from app.services.cache_service import cache

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
async def create_trip(body: TripCreate, current_user: CurrentUser, db: DBSession):
    repo = TripRepository(db)
    trip = await repo.create(
        user_id=current_user.id,
        destination=body.destination,
        num_days=body.num_days,
        budget_level=body.budget_level,
        budget_amount=body.budget_amount,
        travel_style=body.travel_style,
        interests=body.interests,
        start_date=body.start_date,
    )
    return trip


@router.get("", response_model=PaginatedResponse)
async def list_trips(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination = Depends(),
):
    repo = TripRepository(db)
    trips = await repo.get_user_trips(
        user_id=current_user.id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    total = await repo.count_user_trips(current_user.id)

    return PaginatedResponse(
        items=[TripOut.model_validate(t) for t in trips],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=math.ceil(total / pagination.page_size),
    )


@router.get("/{trip_id}", response_model=TripWithItinerary)
async def get_trip(trip_id: UUID, current_user: CurrentUser, db: DBSession):
    repo = TripRepository(db)
    trip = await repo.get_with_details(trip_id)

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trip")

    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(trip_id: UUID, current_user: CurrentUser, db: DBSession):
    repo = TripRepository(db)
    trip = await repo.get_by_id(trip_id)

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trip")

    await repo.delete(trip)
    await cache.invalidate_trip(str(trip_id))


@router.post("/generate", response_model=TripWithItinerary)
async def generate_itinerary(body: GenerateItineraryRequest, current_user: CurrentUser, db: DBSession):
    """
    Core endpoint: triggers AI itinerary generation for a trip.
    Calls Claude API, persists results, returns full trip with itinerary.

    Flow:
    1. Load trip from DB
    2. Check cache
    3. Call AI service (Claude)
    4. Persist itinerary days + budget plan to DB
    5. Cache result
    6. Return full trip
    """
    repo = TripRepository(db)
    trip = await repo.get_by_id(body.trip_id)

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trip")

    # Check cache first
    cached = await cache.get_itinerary(str(trip.id))
    if cached:
        trip = await repo.get_with_details(trip.id)
        return trip

    # Call Claude
    itinerary_data = await ai_service.generate_itinerary(
        destination=trip.destination,
        num_days=trip.num_days,
        budget_level=trip.budget_level,
        travel_style=trip.travel_style,
        interests=trip.interests or [],
    )

    # Persist
    await repo.save_itineraries(trip.id, itinerary_data.get("days", []))
    await repo.save_budget_plan(trip.id, itinerary_data)
    await repo.update(
        trip,
        status="generated",
        tagline=itinerary_data.get("tagline"),
        destination_country=itinerary_data.get("destination", "").split(",")[-1].strip(),
        budget_amount=itinerary_data.get("estimatedBudget"),
    )

    # Cache
    await cache.set_itinerary(str(trip.id), itinerary_data)

    full_trip = await repo.get_with_details(trip.id)
    return full_trip


@router.patch("/{trip_id}/itinerary/{day_number}", response_model=dict)
async def update_itinerary_day(
    trip_id: UUID,
    day_number: int,
    body: ItineraryUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Edit a single day's activities in an itinerary."""
    from sqlalchemy import select, update
    from app.models.user import Itinerary

    repo = TripRepository(db)
    trip = await repo.get_by_id(trip_id)

    if not trip or trip.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    result = await db.execute(
        select(Itinerary).where(
            Itinerary.trip_id == trip_id,
            Itinerary.day_number == day_number,
        )
    )
    itin = result.scalar_one_or_none()
    if not itin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Day not found")

    if body.theme is not None:
        itin.theme = body.theme
    if body.activities is not None:
        itin.activities = [a.model_dump() for a in body.activities]

    await db.flush()
    await cache.invalidate_trip(str(trip_id))

    return {"day_number": day_number, "status": "updated"}