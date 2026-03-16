import json
import re

import anthropic

from app.core.config import settings


class AIService:
    """
    Wraps the Anthropic Claude API.
    Handles itinerary generation and the travel guide chat.
    """

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

    async def generate_itinerary(
        self,
        destination: str,
        num_days: int,
        budget_level: str,
        travel_style: str,
        interests: list[str],
    ) -> dict:
        """
        Calls Claude to generate a structured itinerary JSON.
        Returns the parsed dict ready to be saved to DB.
        """
        budget_map = {
            "budget": "under $50/day per person",
            "mid": "$50–150/day per person",
            "luxury": "$150+ per day per person",
        }
        interests_str = ", ".join(interests) if interests else "general sightseeing"

        prompt = f"""You are a world-class travel planner with deep local knowledge of destinations worldwide.

Create a detailed {num_days}-day travel itinerary for {destination}.

Trip details:
- Duration: {num_days} days
- Budget: {budget_map.get(budget_level, 'mid-range')}
- Travel style: {travel_style}
- Interests: {interests_str}

Return ONLY a valid JSON object with NO markdown fences, NO preamble. Use this exact structure:
{{
  "destination": "City, Country",
  "tagline": "One evocative sentence capturing the destination's essence",
  "estimatedBudget": 850,
  "currency": "USD",
  "accommodation": 300,
  "food": 200,
  "transport": 100,
  "activities": 200,
  "miscellaneous": 50,
  "days": [
    {{
      "dayNumber": 1,
      "theme": "Arrival & First Impressions",
      "date": "Day 1",
      "activities": [
        {{
          "time": "9:00 AM",
          "name": "Activity name",
          "description": "2-3 sentences with authentic local tips and what makes it special.",
          "type": "sightseeing",
          "estimatedCost": 0,
          "duration": "2 hours",
          "tags": ["Free", "Must-see"],
          "latitude": 35.6762,
          "longitude": 139.6503
        }}
      ]
    }}
  ]
}}

Rules:
- 4-6 activities per day, spread across morning, afternoon, and evening
- Always include at least one meal per day (breakfast, lunch, or dinner)
- Make it locally authentic — avoid generic tourist traps
- Include latitude/longitude for every activity
- Tags from: Free, Must-see, Hidden gem, Budget-friendly, Splurge, Local favourite, Foodie pick, Nature, Cultural, Nightlife
- estimatedCost in USD for each activity (0 for free items)
- total estimatedBudget = sum of accommodation + food + transport + activities + miscellaneous for the whole trip"""

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = "".join(block.text for block in message.content if hasattr(block, "text"))
        # Strip any accidental markdown fences
        clean = re.sub(r"```json|```", "", raw).strip()
        return json.loads(clean)

    async def chat(
        self,
        messages: list[dict],
        trip_context: str | None = None,
    ) -> str:
        """
        Multi-turn travel guide chat.
        Maintains history via the messages list passed in.
        """
        system = (
            "You are Voya, a friendly and expert AI travel guide with knowledge of every "
            "destination worldwide. You help travellers with destination advice, local customs, "
            "visa requirements, food recommendations, transport tips, packing lists, safety, "
            "and anything else travel-related. Be conversational, warm, specific, and concise. "
            "Avoid generic advice — give the kind of tips a well-travelled local friend would share."
        )

        if trip_context:
            system += f"\n\nThe user currently has a trip planned: {trip_context}"

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=system,
            messages=messages,
        )

        return "".join(block.text for block in response.content if hasattr(block, "text"))


ai_service = AIService()