from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://aigita:aigita_dev_password@postgres:5432/aigita"

    # Redis
    redis_url: str = "redis://redis:6379"

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333

    # LiveKit
    livekit_url: str = "ws://livekit:7880"
    livekit_api_key: str = "aigita_dev_key"
    livekit_api_secret: str = "aigita_dev_secret_change_me"

    # OpenAI
    openai_api_key: str = ""

    # JWT
    jwt_secret: str = "dev_jwt_secret_please_change_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # App
    environment: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
