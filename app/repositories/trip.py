from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import BudgetPlan, Itinerary, Trip, TripGenerationJob


class TripRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, trip_id: str) -> Trip | None:
        result = await self.db.execute(
            select(Trip).where(Trip.id == str(trip_id))
        )
        return result.scalar_one_or_none()

    async def get_with_details(self, trip_id: str) -> Trip | None:
        result = await self.db.execute(
            select(Trip)
            .options(
                selectinload(Trip.itineraries),
                selectinload(Trip.budget_plan),
            )
            .where(Trip.id == str(trip_id))
        )
        return result.scalar_one_or_none()

    async def get_user_trips(self, user_id: str, offset: int = 0, limit: int = 20) -> list[Trip]:
        result = await self.db.execute(
            select(Trip)
            .where(Trip.user_id == str(user_id))
            .order_by(Trip.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_user_trips(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Trip).where(Trip.user_id == str(user_id))
        )
        return result.scalar_one()

    async def create(self, user_id: str, **kwargs) -> Trip:
        trip = Trip(user_id=str(user_id), **kwargs)
        self.db.add(trip)
        await self.db.flush()
        await self.db.refresh(trip)
        return trip

    async def update(self, trip: Trip, **kwargs) -> Trip:
        for key, value in kwargs.items():
            setattr(trip, key, value)
        await self.db.flush()
        await self.db.refresh(trip)
        return trip

    async def delete(self, trip: Trip) -> None:
        await self.db.delete(trip)
        await self.db.flush()

    async def save_itineraries(self, trip_id: str, days: list[dict]) -> list[Itinerary]:
        await self.db.execute(
            delete(Itinerary).where(Itinerary.trip_id == str(trip_id))
        )
        itineraries = []
        for day in days:
            itin = Itinerary(
                trip_id=str(trip_id),
                day_number=day["dayNumber"],
                theme=day.get("theme"),
                activities=day.get("activities", []),
            )
            self.db.add(itin)
            itineraries.append(itin)
        await self.db.flush()
        return itineraries

    async def save_budget_plan(self, trip_id: str, data: dict) -> BudgetPlan:
        await self.db.execute(
            delete(BudgetPlan).where(BudgetPlan.trip_id == str(trip_id))
        )
        plan = BudgetPlan(
            trip_id=str(trip_id),
            total_budget=data.get("estimatedBudget", 0),
            currency=data.get("currency", "USD"),
            accommodation=data.get("accommodation", 0),
            food=data.get("food", 0),
            transport=data.get("transport", 0),
            activities=data.get("activities", 0),
            miscellaneous=data.get("miscellaneous", 0),
            breakdown=data,
        )
        self.db.add(plan)
        await self.db.flush()
        await self.db.refresh(plan)
        return plan

    async def get_active_generation_job(self, trip_id: str) -> TripGenerationJob | None:
        result = await self.db.execute(
            select(TripGenerationJob)
            .where(
                TripGenerationJob.trip_id == str(trip_id),
                TripGenerationJob.status.in_(("pending", "running")),
            )
            .order_by(TripGenerationJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_generation_job(self, trip_id: str, user_id: str) -> TripGenerationJob:
        job = TripGenerationJob(
            trip_id=str(trip_id),
            user_id=str(user_id),
            status="pending",
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_generation_job(self, job_id: str) -> TripGenerationJob | None:
        result = await self.db.execute(
            select(TripGenerationJob).where(TripGenerationJob.id == str(job_id))
        )
        return result.scalar_one_or_none()

    async def update_generation_job(self, job: TripGenerationJob, **kwargs) -> TripGenerationJob:
        for key, value in kwargs.items():
            setattr(job, key, value)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_latest_generation_job(self, trip_id: str) -> TripGenerationJob | None:
        result = await self.db.execute(
            select(TripGenerationJob)
            .where(TripGenerationJob.trip_id == str(trip_id))
            .order_by(TripGenerationJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
