from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = ["*"]
    max_workers: int = 4


settings = Settings()
