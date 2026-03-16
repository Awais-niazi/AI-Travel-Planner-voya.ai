from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import BudgetPlan, Itinerary, Trip


class TripRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, trip_id: UUID) -> Trip | None:
        result = await self.db.execute(select(Trip).where(Trip.id == trip_id))
        return result.scalar_one_or_none()

    async def get_with_details(self, trip_id: UUID) -> Trip | None:
        result = await self.db.execute(
            select(Trip)
            .options(
                selectinload(Trip.itineraries),
                selectinload(Trip.budget_plan),
            )
            .where(Trip.id == trip_id)
        )
        return result.scalar_one_or_none()

    async def get_user_trips(self, user_id: UUID, offset: int = 0, limit: int = 20) -> list[Trip]:
        result = await self.db.execute(
            select(Trip)
            .where(Trip.user_id == user_id)
            .order_by(Trip.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_user_trips(self, user_id: UUID) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(Trip).where(Trip.user_id == user_id)
        )
        return result.scalar_one()

    async def create(self, user_id: UUID, **kwargs) -> Trip:
        trip = Trip(user_id=user_id, **kwargs)
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

    async def save_itineraries(self, trip_id: UUID, days: list[dict]) -> list[Itinerary]:
        # Delete existing itineraries for this trip first
        from sqlalchemy import delete
        await self.db.execute(delete(Itinerary).where(Itinerary.trip_id == trip_id))

        itineraries = []
        for day in days:
            itin = Itinerary(
                trip_id=trip_id,
                day_number=day["dayNumber"],
                theme=day.get("theme"),
                activities=day.get("activities", []),
            )
            self.db.add(itin)
            itineraries.append(itin)

        await self.db.flush()
        return itineraries

    async def save_budget_plan(self, trip_id: UUID, data: dict) -> BudgetPlan:
        from sqlalchemy import delete
        await self.db.execute(delete(BudgetPlan).where(BudgetPlan.trip_id == trip_id))

        plan = BudgetPlan(
            trip_id=trip_id,
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