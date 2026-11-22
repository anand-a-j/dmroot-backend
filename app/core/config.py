from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import SecretStr, ValidationInfo, field_validator
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

    # Auth / JWT (access tokens are signed with secret_key)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minties: int = 15
    refresh_token_expire_days: int = 30


    # PostgreSQL connection pool
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10

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


    @property
    def database_dsn(self) -> str:
        user = quote(self.db_user, safe="")
        password = quote(self.db_password.get_secret_value(), safe="")
        return (
            f"postgresql://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_setings() -> Settings:
    return Settings()


settings = get_setings()