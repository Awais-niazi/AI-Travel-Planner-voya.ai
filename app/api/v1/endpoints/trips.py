import math

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.core.dependencies import CurrentUser, DBSession, Pagination, enforce_rate_limit
from app.repositories.trip import TripRepository
from app.schemas.schemas import (
    GenerateItineraryRequest,
    ItineraryUpdate,
    PaginatedResponse,
    TripGenerationJobOut,
    TripCreate,
    TripOut,
    TripWithItinerary,
)
from app.services.cache_service import cache
from app.services.ai_protection_service import AIServiceUnavailable
from app.services.feature_gate_service import ensure_trip_generation_enabled
from app.services.trip_generation_service import generate_trip_for_trip, process_generation_job

router = APIRouter(prefix="/trips", tags=["Trips"])


async def _queue_generation_job_for_trip(
    trip_id: str,
    current_user: CurrentUser,
    db: DBSession,
    background_tasks: BackgroundTasks,
):
    repo = TripRepository(db)
    trip = await repo.get_by_id(trip_id)

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if str(trip.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trip")

    existing_job = await repo.get_active_generation_job(trip_id)
    if existing_job:
        if existing_job.status == "pending":
            background_tasks.add_task(process_generation_job, str(existing_job.id))
        return existing_job

    await repo.update(trip, status="generating")
    job = await repo.create_generation_job(trip_id=trip_id, user_id=str(current_user.id))
    background_tasks.add_task(process_generation_job, str(job.id))
    return job


@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
async def create_trip(body: TripCreate, current_user: CurrentUser, db: DBSession):
    repo = TripRepository(db)
    trip = await repo.create(
        user_id=str(current_user.id),
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
        user_id=str(current_user.id),
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    total = await repo.count_user_trips(str(current_user.id))

    return PaginatedResponse(
        items=[TripOut.model_validate(t) for t in trips],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=math.ceil(total / pagination.page_size),
    )


@router.get("/{trip_id}", response_model=TripWithItinerary)
async def get_trip(trip_id: str, current_user: CurrentUser, db: DBSession):
    repo = TripRepository(db)
    trip = await repo.get_with_details(trip_id)

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if str(trip.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trip")

    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(trip_id: str, current_user: CurrentUser, db: DBSession):
    repo = TripRepository(db)
    trip = await repo.get_by_id(trip_id)

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if str(trip.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trip")

    await repo.delete(trip)
    await cache.invalidate_trip(str(trip_id))


@router.post("/generate-async", response_model=TripGenerationJobOut, status_code=status.HTTP_202_ACCEPTED)
async def generate_itinerary_async(
    body: GenerateItineraryRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DBSession,
):
    enforce_rate_limit(
        request,
        scope="trip_generate_async",
        max_requests=5,
        window_seconds=300,
        user_id=str(current_user.id),
    )
    ensure_trip_generation_enabled()
    return await _queue_generation_job_for_trip(
        trip_id=str(body.trip_id),
        current_user=current_user,
        db=db,
        background_tasks=background_tasks,
    )


@router.post("/{trip_id}/generation-jobs", response_model=TripGenerationJobOut, status_code=status.HTTP_202_ACCEPTED)
async def create_generation_job(
    trip_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DBSession,
):
    enforce_rate_limit(
        request,
        scope="trip_generation_jobs",
        max_requests=5,
        window_seconds=300,
        user_id=str(current_user.id),
    )
    ensure_trip_generation_enabled()
    return await _queue_generation_job_for_trip(
        trip_id=trip_id,
        current_user=current_user,
        db=db,
        background_tasks=background_tasks,
    )


@router.get("/generation-jobs/{job_id}", response_model=TripGenerationJobOut)
async def get_generation_job(job_id: str, current_user: CurrentUser, db: DBSession):
    repo = TripRepository(db)
    job = await repo.get_generation_job(job_id)

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")
    if str(job.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your generation job")

    return job


@router.get("/{trip_id}/generation-jobs/latest", response_model=TripGenerationJobOut)
async def get_latest_generation_job(trip_id: str, current_user: CurrentUser, db: DBSession):
    repo = TripRepository(db)
    trip = await repo.get_by_id(trip_id)

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if str(trip.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trip")

    job = await repo.get_latest_generation_job(trip_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")

    return job


@router.post("/generate", response_model=TripWithItinerary)
async def generate_itinerary(
    body: GenerateItineraryRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
):
    enforce_rate_limit(
        request,
        scope="trip_generate_sync",
        max_requests=5,
        window_seconds=300,
        user_id=str(current_user.id),
    )
    ensure_trip_generation_enabled()
    repo = TripRepository(db)
    trip = await repo.get_by_id(str(body.trip_id))

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if str(trip.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trip")

    cached = await cache.get_itinerary(str(trip.id))
    if cached:
        trip = await repo.get_with_details(str(trip.id))
        return trip

    try:
        await generate_trip_for_trip(repo, trip)
    except AIServiceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    full_trip = await repo.get_with_details(str(trip.id))
    return full_trip


@router.patch("/{trip_id}/itinerary/{day_number}", response_model=dict)
async def update_itinerary_day(
    trip_id: str,
    day_number: int,
    body: ItineraryUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    from sqlalchemy import select
    from app.models.user import Itinerary

    repo = TripRepository(db)
    trip = await repo.get_by_id(trip_id)

    if not trip or str(trip.user_id) != str(current_user.id):
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
    await cache.invalidate_trip(trip_id)

    return {"day_number": day_number, "status": "updated"}
