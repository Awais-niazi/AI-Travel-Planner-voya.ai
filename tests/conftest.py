import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/voya_test.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:////tmp/voya_test.db"
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-key"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["REDIS_URL"] = ""

@pytest_asyncio.fixture(autouse=True)
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
    from app.db.session import engine
    from app.services.ai_protection_service import ai_protection
    from app.services.rate_limit_service import rate_limiter
    from app.core.config import settings

    ai_protection.reset()
    rate_limiter.reset()
    settings.enable_ai_chat = True
    settings.enable_trip_generation = True

    async with engine.begin() as conn:
        table_names = set(await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
        for table in ("reviews", "budget_plans", "itineraries", "trips", "places", "users"):
            if table in table_names:
                await conn.execute(text(f"DELETE FROM {table}"))


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
