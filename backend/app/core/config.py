from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"
    database_host: str = "127.0.0.1"
    database_port: int = Field(default=55433, ge=1, le=65535)
    database_name: str = "ai_tourism_dev"
    database_user: str = "ai_tourism_app"
    database_password: SecretStr
    database_connect_timeout_seconds: int = Field(default=2, ge=1, le=10)

    @field_validator("log_level")
    @classmethod
    def supported_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING or ERROR")
        return normalized

    @field_validator("database_user")
    @classmethod
    def least_privilege_role(cls, value: str) -> str:
        if value != "ai_tourism_app":
            raise ValueError("DATABASE_USER must be the least-privilege ai_tourism_app role")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
