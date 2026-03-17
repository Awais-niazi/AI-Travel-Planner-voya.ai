import pytest
from httpx import ASGITransport, AsyncClient


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