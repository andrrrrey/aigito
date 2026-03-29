from pydantic_settings import BaseSettings
from functools import lru_cache


class AgentSettings(BaseSettings):
    livekit_url: str = "ws://livekit:7880"
    livekit_api_key: str = "aigita_dev_key"
    livekit_api_secret: str = "aigita_dev_secret_change_me"

    openai_api_key: str = ""
    elevenlabs_api_key: str = ""
    lemonslice_api_key: str = ""

    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333

    database_url: str = "postgresql+asyncpg://aigita:aigita_dev_password@postgres:5432/aigita"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> AgentSettings:
    return AgentSettings()


settings = get_settings()
