from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Voya.ai"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "changeme"
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://voya:password@localhost:5432/voyadb"
    database_url_sync: str = "postgresql://voya:password@localhost:5432/voyadb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # JWT
    jwt_secret_key: str = "changeme-jwt"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Go services
    recommendation_service_url: str = "http://localhost:8001"
    itinerary_service_url: str = "http://localhost:8002"
    routing_service_url: str = "http://localhost:8003"

    # External APIs
    google_maps_api_key: str = ""
    weather_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()