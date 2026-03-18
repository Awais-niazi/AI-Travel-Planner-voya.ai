import json
import re

from groq import AsyncGroq

from app.core.config import settings


class AIService:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.anthropic_api_key)
        self.model = "llama-3.3-70b-versatile"

    async def generate_itinerary(
        self,
        destination: str,
        num_days: int,
        budget_level: str,
        travel_style: str,
        interests: list[str],
    ) -> dict:
        budget_map = {
            "budget": "under $50/day per person",
            "mid": "$50–150/day per person",
            "luxury": "$150+ per day per person",
        }
        interests_str = ", ".join(interests) if interests else "general sightseeing"

        prompt = f"""You are a world-class travel planner with deep local knowledge.

Create a detailed {num_days}-day travel itinerary for {destination}.

Trip details:
- Duration: {num_days} days
- Budget: {budget_map.get(budget_level, 'mid-range')}
- Travel style: {travel_style}
- Interests: {interests_str}

Return ONLY a valid JSON object with NO markdown fences, NO preamble. Use this exact structure:
{{
  "destination": "City, Country",
  "tagline": "One evocative sentence capturing the destination essence",
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
          "description": "2-3 sentences with authentic local tips.",
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
- 4-6 activities per day across morning, afternoon, and evening
- Always include at least one meal per day
- Make it locally authentic
- Include latitude/longitude for every activity
- Tags from: Free, Must-see, Hidden gem, Budget-friendly, Splurge, Local favourite, Foodie pick, Nature, Cultural, Nightlife
- estimatedCost in USD for each activity
- Return ONLY the JSON object, nothing else"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7,
        )

        raw = response.choices[0].message.content
        clean = re.sub(r"```json|```", "", raw).strip()
        return json.loads(clean)

    async def chat(
        self,
        messages: list[dict],
        trip_context: str | None = None,
    ) -> str:
        system = (
            "You are Voya, a friendly and expert AI travel guide with knowledge of every "
            "destination worldwide. You help travellers with destination advice, local customs, "
            "visa requirements, food recommendations, transport tips, packing lists, safety, "
            "and anything else travel-related. Be conversational, warm, specific, and concise."
        )

        if trip_context:
            system += f"\n\nThe user currently has a trip planned: {trip_context}"

        groq_messages = [{"role": "system", "content": system}] + messages

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=groq_messages,
            max_tokens=1000,
            temperature=0.7,
        )

        return response.choices[0].message.content


ai_service = AIService()