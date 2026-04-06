from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI-Analyst Platform API"
    api_v1_prefix: str = "/api/v1"

    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "ai_analyst_db"
    postgres_host: str = "db"
    postgres_port: int = 5432
    database_url: str | None = None

    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"
    file_service_url: str = "http://file_service:8000"

    jwt_secret_key: str = "change-me-in-production"
    jwt_refresh_secret_key: str = "change-me-refresh-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 14

    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://web_frontend:3000",
            "http://localhost:8501",
        ]
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
