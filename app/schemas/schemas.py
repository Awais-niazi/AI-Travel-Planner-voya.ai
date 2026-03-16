from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Base ──────────────────────────────────────────────────────────────
class BaseSchema(BaseModel):
    model_config = {"from_attributes": True}


# ── Auth ──────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ── User ──────────────────────────────────────────────────────────────
class UserOut(BaseSchema):
    id: UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    is_premium: bool
    preferences: dict
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
    preferences: dict | None = None


# ── Trip ──────────────────────────────────────────────────────────────
class TripCreate(BaseModel):
    destination: str = Field(min_length=2, max_length=255)
    num_days: int = Field(ge=1, le=30, default=5)
    budget_level: str = Field(pattern="^(budget|mid|luxury)$", default="mid")
    budget_amount: float | None = Field(None, ge=0)
    travel_style: str = Field(default="couple")
    interests: list[str] = Field(default_factory=list)
    start_date: datetime | None = None


class TripOut(BaseSchema):
    id: UUID
    destination: str
    destination_country: str | None
    num_days: int
    budget_level: str
    budget_amount: float | None
    travel_style: str
    interests: list[str]
    status: str
    tagline: str | None
    created_at: datetime
    updated_at: datetime


class TripWithItinerary(TripOut):
    itineraries: list["ItineraryOut"] = []
    budget_plan: "BudgetPlanOut | None" = None


# ── Itinerary ──────────────────────────────────────────────────────────
class ActivitySchema(BaseModel):
    time: str
    name: str
    description: str
    type: str = "sightseeing"
    estimated_cost: float = 0
    duration: str | None = None
    tags: list[str] = []
    place_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class ItineraryOut(BaseSchema):
    id: UUID
    trip_id: UUID
    day_number: int
    theme: str | None
    activities: list[Any]


class ItineraryUpdate(BaseModel):
    theme: str | None = None
    activities: list[ActivitySchema] | None = None


# ── Budget ──────────────────────────────────────────────────────────────
class BudgetPlanOut(BaseSchema):
    id: UUID
    trip_id: UUID
    total_budget: float
    currency: str
    accommodation: float
    food: float
    transport: float
    activities: float
    miscellaneous: float
    breakdown: dict


# ── Place ──────────────────────────────────────────────────────────────
class PlaceOut(BaseSchema):
    id: UUID
    name: str
    description: str | None
    destination: str
    category: str | None
    latitude: float | None
    longitude: float | None
    address: str | None
    rating: float | None
    price_level: int | None
    tags: list[str]


# ── Review ──────────────────────────────────────────────────────────────
class ReviewCreate(BaseModel):
    place_id: UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewOut(BaseSchema):
    id: UUID
    user_id: UUID
    place_id: UUID
    rating: int
    comment: str | None
    created_at: datetime


# ── AI Chat ──────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    trip_id: UUID | None = None  # optional context


class ChatResponse(BaseModel):
    reply: str
    trip_context: str | None = None


# ── Generate Itinerary ──────────────────────────────────────────────────
class GenerateItineraryRequest(BaseModel):
    trip_id: UUID


class GenerateItineraryResponse(BaseModel):
    trip_id: UUID
    status: str
    message: str


# ── Pagination ──────────────────────────────────────────────────────────
class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int