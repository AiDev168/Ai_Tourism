from functools import lru_cache

from pydantic import Field, SecretStr, field_validator, model_validator
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
    auth_enabled: bool = False
    auth_sms_adapter: str = "disabled"
    sms_ir_sandbox_api_key: SecretStr | None = None
    auth_otp_hmac_secret: SecretStr | None = None
    auth_csrf_secret: SecretStr | None = None
    auth_rate_limit_secret: SecretStr | None = None
    auth_session_idle_seconds: int | None = Field(default=None, ge=60)
    auth_session_absolute_seconds: int | None = Field(default=None, ge=60)
    auth_otp_length: int = Field(default=6, ge=6, le=8)
    auth_otp_ttl_seconds: int = Field(default=300, ge=60, le=900)
    auth_otp_max_attempts: int = Field(default=5, ge=1, le=10)
    auth_otp_resend_cooldown_seconds: int = Field(default=60, ge=10, le=600)
    auth_cookie_secure: bool = True
    auth_allowed_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    auth_rate_window_seconds: int = Field(default=600, ge=60, le=3600)
    auth_phone_issue_limit: int = Field(default=3, ge=1, le=20)
    auth_ip_issue_limit: int = Field(default=20, ge=1, le=200)
    auth_global_issue_limit: int = Field(default=500, ge=1, le=10000)
    auth_phone_verify_limit: int = Field(default=20, ge=1, le=500)
    auth_ip_verify_limit: int = Field(default=60, ge=1, le=1000)

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

    @model_validator(mode="after")
    def validate_auth_configuration(self):
        if self.auth_sms_adapter not in {"disabled", "fake", "sms_ir_sandbox"}:
            raise ValueError("AUTH_SMS_ADAPTER must be disabled, fake, or sms_ir_sandbox")
        if self.app_env.lower() == "production":
            if self.auth_enabled:
                raise ValueError("Authentication is disabled in production pending separate SMS authorization")
            if not self.auth_cookie_secure:
                raise ValueError("AUTH_COOKIE_SECURE must be true in production")
        if self.auth_sms_adapter == "fake" and self.app_env.lower() not in {"development", "test"}:
            raise ValueError("The fake SMS adapter is restricted to development and tests")
        if self.auth_sms_adapter == "sms_ir_sandbox":
            if self.app_env.lower() not in {"development", "test"}:
                raise ValueError("SMS.ir Sandbox is restricted to development and tests")
            if self.sms_ir_sandbox_api_key is None:
                raise ValueError("SMS_IR_SANDBOX_API_KEY is required for the SMS.ir Sandbox adapter")
            key = self.sms_ir_sandbox_api_key.get_secret_value()
            if not key or key != key.strip() or "\r" in key or "\n" in key:
                raise ValueError("SMS_IR_SANDBOX_API_KEY is invalid for the SMS.ir Sandbox adapter")
        if self.auth_enabled:
            for name in ("auth_otp_hmac_secret", "auth_csrf_secret", "auth_rate_limit_secret"):
                secret = getattr(self, name)
                if secret is None or len(secret.get_secret_value().encode("utf-8")) < 32:
                    raise ValueError(f"{name.upper()} must contain at least 32 bytes when authentication is enabled")
            if self.auth_session_idle_seconds is None or self.auth_session_absolute_seconds is None:
                raise ValueError("Both authentication session lifetimes must be configured")
            if self.auth_session_idle_seconds > self.auth_session_absolute_seconds:
                raise ValueError("Session idle lifetime cannot exceed absolute lifetime")
            if self.auth_sms_adapter == "disabled":
                raise ValueError("Authentication is enabled without an available SMS delivery adapter")
            if not self.auth_allowed_origins.strip():
                raise ValueError("AUTH_ALLOWED_ORIGINS must contain at least one exact origin")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
