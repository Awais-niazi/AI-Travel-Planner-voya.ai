import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-key"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    import app.models.user  # noqa: F401
    from app.db.session import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield
    from sqlalchemy import text
    from app.db.session import engine

    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM reviews"))
        await conn.execute(text("DELETE FROM budget_plans"))
        await conn.execute(text("DELETE FROM itineraries"))
        await conn.execute(text("DELETE FROM trips"))
        await conn.execute(text("DELETE FROM places"))
        await conn.execute(text("DELETE FROM users"))


@pytest_asyncio.fixture
async def client():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client():
    """Returns a helper that creates an authenticated client for a given token."""
    from app.main import app

    async def _make(token: str) -> AsyncClient:
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        )

    return _make