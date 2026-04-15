from functools import lru_cache
import json
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Voya.ai"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "changeme"
    allowed_origins_str: str = Field(
        default="http://localhost:3000",
        validation_alias="ALLOWED_ORIGINS",
    )

    # Database
    database_url: str = "postgresql+asyncpg://voya:password@localhost:5432/voyadb"
    database_url_sync: str = "postgresql://voya:password@localhost:5432/voyadb"

    # Redis
    redis_url: str = ""

    # AI — now using Groq
    anthropic_api_key: str = ""
    anthropic_model: str = "llama-3.3-70b-versatile"
    ai_timeout_seconds: int = 20
    ai_circuit_failure_threshold: int = 3
    ai_circuit_cooldown_seconds: int = 60
    enable_ai_chat: bool = True
    enable_trip_generation: bool = True

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

    @property
    def allowed_origins(self) -> list[str]:
        val = self.allowed_origins_str.strip()
        if val.startswith("["):
            try:
                return json.loads(val)
            except Exception:
                pass
        return [v.strip() for v in val.split(",") if v.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
