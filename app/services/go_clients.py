"""
HTTP clients for calling Go microservices.
Each client maps to one Go service:
  - RecommendationClient  → go-services/recommendation  (:8001)
  - ItineraryClient       → go-services/itinerary        (:8002)
  - RoutingClient         → go-services/routing          (:8003)
"""
from uuid import UUID

import httpx

from app.core.config import settings


class RecommendationClient:
    """
    Calls the Go recommendation service.
    Handles content-based filtering, collaborative filtering,
    popularity ranking, and location-based ranking.
    """

    def __init__(self):
        self.base_url = settings.recommendation_service_url
        self.timeout = 10.0

    async def get_recommendations(
        self,
        destination: str,
        interests: list[str],
        budget_level: str,
        travel_style: str,
        user_id: UUID | None = None,
    ) -> dict:
        """
        Returns ranked list of places/attractions for a destination.
        Go service applies ML-based collaborative + content filtering.
        """
        payload = {
            "destination": destination,
            "interests": interests,
            "budget_level": budget_level,
            "travel_style": travel_style,
            "user_id": str(user_id) if user_id else None,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/v1/recommendations", json=payload)
            response.raise_for_status()
            return response.json()

    async def get_similar_places(self, place_id: str, limit: int = 10) -> list[dict]:
        """Content-based similarity for 'you might also like' features."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/v1/places/{place_id}/similar",
                params={"limit": limit},
            )
            response.raise_for_status()
            return response.json()

    async def record_interaction(
        self,
        user_id: UUID,
        place_id: str,
        interaction_type: str,  # view, save, complete
    ) -> None:
        """Feed user interactions back to the recommendation model."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            await client.post(
                f"{self.base_url}/v1/interactions",
                json={
                    "user_id": str(user_id),
                    "place_id": place_id,
                    "type": interaction_type,
                },
            )


class ItineraryClient:
    """
    Calls the Go itinerary planning service.
    Handles clustering by location, time-slot assignment,
    and combining recommendations into a daily schedule.
    """

    def __init__(self):
        self.base_url = settings.itinerary_service_url
        self.timeout = 15.0

    async def plan_itinerary(
        self,
        destination: str,
        num_days: int,
        places: list[dict],
        budget_level: str,
        travel_style: str,
    ) -> list[dict]:
        """
        Takes a list of recommended places and returns
        a day-by-day structured itinerary with time slots.
        Go service handles k-means clustering + time assignment.
        """
        payload = {
            "destination": destination,
            "num_days": num_days,
            "places": places,
            "budget_level": budget_level,
            "travel_style": travel_style,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/v1/plan", json=payload)
            response.raise_for_status()
            return response.json()

    async def replan_day(
        self,
        trip_id: UUID,
        day_number: int,
        constraints: dict,
    ) -> dict:
        """Replans a single day given new constraints (budget change, etc.)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/replan",
                json={
                    "trip_id": str(trip_id),
                    "day_number": day_number,
                    "constraints": constraints,
                },
            )
            response.raise_for_status()
            return response.json()


class RoutingClient:
    """
    Calls the Go route optimization service.
    Uses TSP (Travelling Salesman Problem) heuristics to
    compute the most efficient order to visit attractions.
    """

    def __init__(self):
        self.base_url = settings.routing_service_url
        self.timeout = 10.0

    async def optimize_route(
        self,
        waypoints: list[dict],  # list of {name, lat, lng}
        start_point: dict | None = None,
        transport_mode: str = "walking",
    ) -> dict:
        """
        Returns waypoints in optimal visit order
        with estimated travel times between each.
        """
        payload = {
            "waypoints": waypoints,
            "start_point": start_point,
            "transport_mode": transport_mode,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/v1/optimize", json=payload)
            response.raise_for_status()
            return response.json()

    async def get_directions(
        self,
        origin: dict,
        destination: dict,
        transport_mode: str = "walking",
    ) -> dict:
        """Point-to-point directions with duration and distance."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/directions",
                json={
                    "origin": origin,
                    "destination": destination,
                    "mode": transport_mode,
                },
            )
            response.raise_for_status()
            return response.json()


# Singleton instances — import these throughout the app
recommendation_client = RecommendationClient()
itinerary_client = ItineraryClient()
routing_client = RoutingClient()