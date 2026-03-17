import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


async def register(client, email="test@voya.ai", password="Secure123", name="Test User"):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": name},
    )


async def login(client, email, password="Secure123"):
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await register(client)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await register(client, email="dup@voya.ai")
    response = await register(client, email="dup@voya.ai")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@voya.ai", "password": "nodigits", "full_name": "Test"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await register(client, email="login@voya.ai")
    response = await login(client, "login@voya.ai")
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await register(client, email="wrong@voya.ai")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@voya.ai", "password": "BadPassword1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    reg = await register(client, email="me@voya.ai")
    token = reg.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@voya.ai"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)