from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.repositories.trip import TripRepository
from app.services.ai_service import ai_service
from app.services.cache_service import cache


async def generate_trip_for_trip(repo: TripRepository, trip) -> None:
    itinerary_data = await ai_service.generate_itinerary(
        destination=trip.destination,
        num_days=trip.num_days,
        budget_level=trip.budget_level,
        travel_style=trip.travel_style,
        interests=trip.interests or [],
    )

    await repo.save_itineraries(str(trip.id), itinerary_data.get("days", []))
    await repo.save_budget_plan(str(trip.id), itinerary_data)
    await repo.update(
        trip,
        status="generated",
        tagline=itinerary_data.get("tagline"),
        destination_country=itinerary_data.get("destination", "").split(",")[-1].strip(),
        budget_amount=itinerary_data.get("estimatedBudget"),
    )
    await cache.set_itinerary(str(trip.id), itinerary_data)


async def process_generation_job(job_id: str) -> None:
    async with AsyncSessionLocal() as db:
        repo = TripRepository(db)
        job = await repo.get_generation_job(job_id)
        if not job or job.status not in {"pending", "running"}:
            return

        trip = await repo.get_by_id(str(job.trip_id))
        if not trip:
            await repo.update_generation_job(
                job,
                status="failed",
                error_message="Trip not found",
            )
            await db.commit()
            return

        try:
            await repo.update_generation_job(job, status="running", error_message=None)
            await generate_trip_for_trip(repo, trip)
            await repo.update_generation_job(job, status="completed", error_message=None)
            await db.commit()
        except Exception as exc:
            await repo.update(trip, status="draft")
            await repo.update_generation_job(job, status="failed", error_message=str(exc))
            await db.commit()
