import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON, TypeDecorator

from app.db.session import Base, _is_sqlite


def utcnow():
    return datetime.now(timezone.utc)


# ── Portable array type ───────────────────────────────────────────────
# Uses JSON on SQLite (tests), native ARRAY on Postgres (production)
class ArrayOfString(TypeDecorator):
    """Stores a list of strings as JSON on SQLite, ARRAY on Postgres."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value or []

    def process_result_value(self, value, dialect):
        return value or []


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)

    trips: Mapped[list["Trip"]] = relationship("Trip", back_populates="user", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="user")


class Trip(TimestampMixin, Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_country: Mapped[str] = mapped_column(String(100), nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    num_days: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    budget_level: Mapped[str] = mapped_column(String(20), nullable=False, default="mid")
    budget_amount: Mapped[float] = mapped_column(Float, nullable=True)
    travel_style: Mapped[str] = mapped_column(String(50), nullable=False, default="couple")
    interests: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    tagline: Mapped[str] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="trips")
    itineraries: Mapped[list["Itinerary"]] = relationship("Itinerary", back_populates="trip", cascade="all, delete-orphan")
    budget_plan: Mapped["BudgetPlan"] = relationship("BudgetPlan", back_populates="trip", uselist=False)


class Itinerary(TimestampMixin, Base):
    __tablename__ = "itineraries"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id"), nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    theme: Mapped[str] = mapped_column(String(255), nullable=True)
    activities: Mapped[dict] = mapped_column(JSON, default=list)

    trip: Mapped["Trip"] = relationship("Trip", back_populates="itineraries")


class Place(TimestampMixin, Base):
    __tablename__ = "places"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    destination: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    price_level: Mapped[int] = mapped_column(Integer, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    external_id: Mapped[str] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict] = mapped_column(JSON, default=dict, name="metadata")

    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="place")


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    place_id: Mapped[str] = mapped_column(String(36), ForeignKey("places.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="reviews")
    place: Mapped["Place"] = relationship("Place", back_populates="reviews")


class BudgetPlan(TimestampMixin, Base):
    __tablename__ = "budget_plans"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id"), nullable=False, unique=True)
    total_budget: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    accommodation: Mapped[float] = mapped_column(Float, default=0)
    food: Mapped[float] = mapped_column(Float, default=0)
    transport: Mapped[float] = mapped_column(Float, default=0)
    activities: Mapped[float] = mapped_column(Float, default=0)
    miscellaneous: Mapped[float] = mapped_column(Float, default=0)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)

    trip: Mapped["Trip"] = relationship("Trip", back_populates="budget_plan")