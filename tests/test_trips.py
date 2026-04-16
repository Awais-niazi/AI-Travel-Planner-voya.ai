import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import AsyncSessionLocal
from app.core.config import settings
from app.repositories.trip import TripRepository
from app.services.ai_protection_service import AIServiceUnavailable
from app.services.trip_generation_service import process_generation_job


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


async def register_and_login(client, email, password="Secure123", name="User"):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": name},
    )
    assert reg.status_code == 201, f"Register failed: {reg.text}"
    return reg.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_trip(client: AsyncClient):
    token = await register_and_login(client, "tripper@voya.ai")
    response = await client.post(
        "/api/v1/trips",
        json={
            "destination": "Tokyo, Japan",
            "num_days": 5,
            "budget_level": "mid",
            "travel_style": "couple",
            "interests": ["culture", "food"],
        },
        headers=auth(token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["destination"] == "Tokyo, Japan"
    assert data["num_days"] == 5
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_list_trips(client: AsyncClient):
    token = await register_and_login(client, "lister@voya.ai")
    for dest in ["Paris, France", "Bali, Indonesia"]:
        await client.post(
            "/api/v1/trips",
            json={"destination": dest, "num_days": 3, "budget_level": "mid"},
            headers=auth(token),
        )
    response = await client.get("/api/v1/trips", headers=auth(token))
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert "items" in data


@pytest.mark.asyncio
async def test_get_trip(client: AsyncClient):
    token = await register_and_login(client, "getter@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Rome, Italy", "num_days": 4, "budget_level": "luxury"},
        headers=auth(token),
    )
    assert create.status_code == 201, f"Create failed: {create.text}"
    trip_id = create.json()["id"]
    response = await client.get(f"/api/v1/trips/{trip_id}", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["id"] == trip_id


@pytest.mark.asyncio
async def test_get_trip_not_found(client: AsyncClient):
    token = await register_and_login(client, "notfound@voya.ai")
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/trips/{fake_id}", headers=auth(token))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_trip(client: AsyncClient):
    token = await register_and_login(client, "deleter@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Madrid, Spain", "num_days": 3, "budget_level": "budget"},
        headers=auth(token),
    )
    assert create.status_code == 201, f"Create failed: {create.text}"
    trip_id = create.json()["id"]
    delete = await client.delete(f"/api/v1/trips/{trip_id}", headers=auth(token))
    assert delete.status_code == 204
    get = await client.get(f"/api/v1/trips/{trip_id}", headers=auth(token))
    assert get.status_code == 404


@pytest.mark.asyncio
async def test_trip_forbidden_for_other_user(client: AsyncClient):
    token_a = await register_and_login(client, "user_a@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Seoul, Korea", "num_days": 5, "budget_level": "mid"},
        headers=auth(token_a),
    )
    assert create.status_code == 201, f"Create failed: {create.text}"
    trip_id = create.json()["id"]

    token_b = await register_and_login(client, "user_b@voya.ai")
    response = await client.get(f"/api/v1/trips/{trip_id}", headers=auth(token_b))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_invalid_budget_level(client: AsyncClient):
    token = await register_and_login(client, "invalid@voya.ai")
    response = await client.post(
        "/api/v1/trips",
        json={"destination": "Lisbon", "num_days": 3, "budget_level": "billionaire"},
        headers=auth(token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_generation_job(client: AsyncClient):
    token = await register_and_login(client, "jobber@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Kyoto, Japan", "num_days": 4, "budget_level": "mid"},
        headers=auth(token),
    )
    trip_id = create.json()["id"]

    response = await client.post(
        f"/api/v1/trips/{trip_id}/generation-jobs",
        headers=auth(token),
    )
    assert response.status_code == 202
    data = response.json()
    assert data["trip_id"] == trip_id
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_generation_job(client: AsyncClient):
    token = await register_and_login(client, "jobstatus@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Osaka, Japan", "num_days": 3, "budget_level": "mid"},
        headers=auth(token),
    )
    trip_id = create.json()["id"]

    job_create = await client.post(
        f"/api/v1/trips/{trip_id}/generation-jobs",
        headers=auth(token),
    )
    job_id = job_create.json()["id"]

    response = await client.get(
        f"/api/v1/trips/generation-jobs/{job_id}",
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["id"] == job_id


@pytest.mark.asyncio
async def test_create_generation_job_reuses_active_job(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.trips.process_generation_job",
        lambda job_id: None,
    )

    token = await register_and_login(client, "jobreuse@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Busan, Korea", "num_days": 3, "budget_level": "mid"},
        headers=auth(token),
    )
    trip_id = create.json()["id"]

    first = await client.post(
        f"/api/v1/trips/{trip_id}/generation-jobs",
        headers=auth(token),
    )
    second = await client.post(
        f"/api/v1/trips/{trip_id}/generation-jobs",
        headers=auth(token),
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.asyncio
async def test_process_generation_job_completes(client: AsyncClient, monkeypatch):
    async def fake_generate_itinerary(**kwargs):
        return {
            "destination": "Kyoto, Japan",
            "tagline": "Temples and tea houses.",
            "estimatedBudget": 900,
            "currency": "USD",
            "accommodation": 300,
            "food": 220,
            "transport": 120,
            "activities": 200,
            "miscellaneous": 60,
            "days": [
                {
                    "dayNumber": 1,
                    "theme": "Arrival",
                    "activities": [
                        {
                            "time": "9:00 AM",
                            "name": "Gion Walk",
                            "description": "Explore Kyoto's historic district.",
                            "estimatedCost": 0,
                            "duration": "2 hours",
                            "tags": ["Free"],
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr(
        "app.api.v1.endpoints.trips.process_generation_job",
        lambda job_id: None,
    )
    monkeypatch.setattr(
        "app.services.trip_generation_service.ai_service.generate_itinerary",
        fake_generate_itinerary,
    )

    token = await register_and_login(client, "jobcomplete@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Kyoto, Japan", "num_days": 3, "budget_level": "mid"},
        headers=auth(token),
    )
    trip_id = create.json()["id"]

    job_create = await client.post(
        f"/api/v1/trips/{trip_id}/generation-jobs",
        headers=auth(token),
    )
    job_id = job_create.json()["id"]

    await process_generation_job(job_id)

    async with AsyncSessionLocal() as db:
        repo = TripRepository(db)
        job = await repo.get_generation_job(job_id)
        trip = await repo.get_with_details(trip_id)

        assert job is not None
        assert job.status == "completed"
        assert trip is not None
        assert trip.status == "generated"
        assert len(trip.itineraries) == 1


@pytest.mark.asyncio
async def test_generate_async_endpoint_creates_job(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.trips.process_generation_job",
        lambda job_id: None,
    )

    token = await register_and_login(client, "asyncgen@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Hanoi, Vietnam", "num_days": 4, "budget_level": "mid"},
        headers=auth(token),
    )
    trip_id = create.json()["id"]

    response = await client.post(
        "/api/v1/trips/generate-async",
        json={"trip_id": trip_id},
        headers=auth(token),
    )
    assert response.status_code == 202
    assert response.json()["trip_id"] == trip_id


@pytest.mark.asyncio
async def test_existing_pending_generation_job_is_requeued(client: AsyncClient, monkeypatch):
    queued_job_ids = []

    async def capture_job(job_id: str):
        queued_job_ids.append(job_id)

    monkeypatch.setattr(
        "app.api.v1.endpoints.trips.process_generation_job",
        capture_job,
    )

    token = await register_and_login(client, "requeuejob@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Paris, France", "num_days": 4, "budget_level": "mid"},
        headers=auth(token),
    )
    trip_id = create.json()["id"]

    first = await client.post(
        f"/api/v1/trips/{trip_id}/generation-jobs",
        headers=auth(token),
    )
    second = await client.post(
        f"/api/v1/trips/{trip_id}/generation-jobs",
        headers=auth(token),
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["id"] == first.json()["id"]
    assert queued_job_ids == [first.json()["id"], first.json()["id"]]


@pytest.mark.asyncio
async def test_get_latest_generation_job(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.trips.process_generation_job",
        lambda job_id: None,
    )

    token = await register_and_login(client, "latestjob@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Taipei, Taiwan", "num_days": 4, "budget_level": "mid"},
        headers=auth(token),
    )
    trip_id = create.json()["id"]

    job_create = await client.post(
        f"/api/v1/trips/{trip_id}/generation-jobs",
        headers=auth(token),
    )
    job_id = job_create.json()["id"]

    response = await client.get(
        f"/api/v1/trips/{trip_id}/generation-jobs/latest",
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["id"] == job_id


@pytest.mark.asyncio
async def test_generation_job_rate_limited(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.trips.process_generation_job",
        lambda job_id: None,
    )

    token = await register_and_login(client, "genlimit@voya.ai")
    trip_ids = []
    for index in range(6):
        create = await client.post(
            "/api/v1/trips",
            json={"destination": f"City {index}", "num_days": 2, "budget_level": "mid"},
            headers=auth(token),
        )
        trip_ids.append(create.json()["id"])

    last_response = None
    for trip_id in trip_ids:
        last_response = await client.post(
            f"/api/v1/trips/{trip_id}/generation-jobs",
            headers=auth(token),
        )

    assert last_response is not None
    assert last_response.status_code == 429
    assert last_response.headers["Retry-After"]


@pytest.mark.asyncio
async def test_generate_trip_returns_503_when_ai_unavailable(client: AsyncClient, monkeypatch):
    async def fail_generate_trip(*args, **kwargs):
        raise AIServiceUnavailable("AI itinerary generation is unavailable")

    monkeypatch.setattr(
        "app.api.v1.endpoints.trips.generate_trip_for_trip",
        fail_generate_trip,
    )

    token = await register_and_login(client, "trip503@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Prague, Czech Republic", "num_days": 4, "budget_level": "mid"},
        headers=auth(token),
    )
    trip_id = create.json()["id"]

    response = await client.post(
        "/api/v1/trips/generate",
        json={"trip_id": trip_id},
        headers=auth(token),
    )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_trip_returns_503_when_generation_disabled(client: AsyncClient):
    settings.enable_trip_generation = False

    token = await register_and_login(client, "tripdisabled@voya.ai")
    create = await client.post(
        "/api/v1/trips",
        json={"destination": "Vienna, Austria", "num_days": 4, "budget_level": "mid"},
        headers=auth(token),
    )
    trip_id = create.json()["id"]

    response = await client.post(
        "/api/v1/trips/generate",
        json={"trip_id": trip_id},
        headers=auth(token),
    )

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"].lower()
