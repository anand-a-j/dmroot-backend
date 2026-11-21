from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "DMRoot"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Security
    secret_key: SecretStr

    # PostgreSQL
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "dmroot"
    db_user: str = "postgres"
    db_password: SecretStr

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Meta / Instagram application
    meta_app_id: str = ""
    meta_app_secret: SecretStr | None = None
    meta_webhook_verify_token: SecretStr | None = None
    meta_api_version: str = "vXX.X"


@lru_cache
def get_setings() -> Settings:
    return Settings()


settings = get_setings()
