from functools import lru_cache
from urllib.parse import urlsplit

from pathlib import Path

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
    internal_chat_enabled: bool = False
    internal_chat_endpoint: str = ""
    internal_chat_model: str = ""
    internal_chat_token: SecretStr | None = None
    # Explicitly opt into one development/test loopback HTTP listener only.
    # Staging, local_pilot and production never use this exception.
    internal_chat_loopback_http_port: int | None = Field(default=None, ge=1024, le=65535)
    internal_chat_daily_user_limit: int = Field(default=8, ge=1, le=1000)
    internal_chat_daily_global_limit: int = Field(default=100, ge=1, le=100000)
    ai_provider_admin_enabled: bool = False
    ai_provider_vault_dir: Path | None = None
    ai_provider_admin_recovery_pepper: SecretStr | None = None
    # Separate server-side key material for platform-reviewer MFA. This is
    # independent of local-only provider administration and is never returned
    # to the client.
    platform_admin_mfa_encryption_key_hex: SecretStr | None = None
    platform_admin_recovery_pepper: SecretStr | None = None
    tourism_rag_enabled: bool = False
    tourism_rag_api_url: str = "http://127.0.0.1:8765"
    tourism_rag_api_token: SecretStr | None = None
    auth_enabled: bool = False
    auth_sms_adapter: str = "disabled"
    auth_local_owner_enabled: bool = False
    staging_auth_enabled: bool = False
    staging_email_signup_enabled: bool = False
    staging_email_signup_ip_limit: int = Field(default=5, ge=1, le=20)
    staging_email_signup_global_limit: int = Field(default=30, ge=1, le=200)
    staging_email_signup_account_limit: int = Field(default=25, ge=1, le=200)
    staging_public_host: str = ""
    sms_ir_sandbox_api_key: SecretStr | None = None
    sms_ir_production_api_key_file: Path | None = None
    sms_ir_production_template_id: int = Field(default=0, ge=0, le=2_147_483_647)
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
        environment = self.app_env.lower()
        if environment not in {"development", "test", "local_pilot", "staging", "production"}:
            raise ValueError("APP_ENV is not supported")
        if self.staging_auth_enabled:
            host = self.staging_public_host.lower().strip()
            origin = urlsplit(self.auth_allowed_origins.strip())
            if (
                environment != "staging" or not self.auth_enabled
                or self.auth_local_owner_enabled
                or self.auth_sms_adapter not in {"disabled", "sms_ir_live_staging"}
                or not self.auth_cookie_secure or not host or "/" in host or ":" in host
                or "," in self.auth_allowed_origins
                or origin.scheme != "https" or origin.hostname != host
                or origin.port is not None or origin.username or origin.password
                or origin.path or origin.query or origin.fragment
            ):
                raise ValueError("Staging invitation authentication requires one exact HTTPS public origin")
        if self.staging_email_signup_enabled and (
            environment != "staging" or not self.auth_enabled or not self.staging_auth_enabled
        ):
            raise ValueError("Staging email registration is restricted to authenticated staging")
        if self.ai_provider_admin_enabled:
            if self.app_env.lower() != "local_pilot" or not self.auth_enabled or not self.auth_cookie_secure:
                raise ValueError("AI provider administration is restricted to authenticated local pilot")
            if self.ai_provider_vault_dir is None or self.ai_provider_admin_recovery_pepper is None:
                raise ValueError("Provider vault and recovery pepper are required when admin is enabled")
            if len(self.ai_provider_admin_recovery_pepper.get_secret_value().encode("utf-8")) < 32:
                raise ValueError("Provider recovery pepper must contain at least 32 bytes")
        if self.platform_admin_mfa_encryption_key_hex is not None or self.platform_admin_recovery_pepper is not None:
            key = (self.platform_admin_mfa_encryption_key_hex.get_secret_value()
                   if self.platform_admin_mfa_encryption_key_hex else "")
            pepper = (self.platform_admin_recovery_pepper.get_secret_value()
                      if self.platform_admin_recovery_pepper else "")
            if (environment not in {"staging", "production"} or not self.auth_enabled
                    or not self.auth_cookie_secure or self.auth_rate_limit_secret is None
                    or len(key) != 64 or any(char not in "0123456789abcdefABCDEF" for char in key)
                    or len(pepper.encode("utf-8")) < 32):
                raise ValueError("Platform reviewer MFA requires secure authenticated staging/production and two valid server keys")
        if self.auth_local_owner_enabled:
            origin = urlsplit(self.auth_allowed_origins.strip())
            if (
                self.app_env.lower() != "local_pilot" or not self.auth_enabled
                or self.auth_sms_adapter != "disabled" or not self.auth_cookie_secure
                or self.app_host not in {"127.0.0.1", "::1", "localhost"}
                or "," in self.auth_allowed_origins
                or origin.scheme != "https" or origin.hostname not in {"localhost", "127.0.0.1", "::1"}
                or origin.username or origin.password or origin.path or origin.query or origin.fragment
            ):
                raise ValueError("Local owner authentication is restricted to a secure localhost pilot")
        if self.internal_chat_enabled:
            chat_url = urlsplit(self.internal_chat_endpoint)
            if (
                environment not in {"development", "test", "local_pilot", "staging"}
                or not chat_url.hostname
                or chat_url.username or chat_url.password or chat_url.query or chat_url.fragment
                or not self.internal_chat_model.strip() or len(self.internal_chat_model) > 160
                or self.internal_chat_token is None
            ):
                raise ValueError("Internal Chat configuration is invalid")
            if environment == "staging":
                if (not self.staging_auth_enabled or chat_url.scheme != "http"
                        or chat_url.hostname != "host.docker.internal" or chat_url.port != 8000):
                    raise ValueError("Staging Chat may use only the private host vLLM endpoint")
            elif chat_url.scheme != "https":
                loopback_http = (
                    environment in {"development", "test"}
                    and chat_url.scheme == "http"
                    and chat_url.hostname in {"127.0.0.1", "localhost"}
                    and chat_url.port is not None
                    and chat_url.port == self.internal_chat_loopback_http_port
                )
                if not loopback_http:
                    raise ValueError("Internal Chat configuration is invalid")
            if self.app_env.lower() == "local_pilot":
                allowed = urlsplit(self.auth_allowed_origins.strip())
                if (
                    not self.auth_enabled or not self.auth_cookie_secure
                    or self.app_host not in {"127.0.0.1", "::1", "localhost"}
                    or "," in self.auth_allowed_origins
                    or allowed.scheme != "https"
                    or allowed.hostname not in {"localhost", "127.0.0.1", "::1"}
                    or allowed.username or allowed.password or allowed.path
                    or allowed.query or allowed.fragment
                ):
                    raise ValueError("Local-pilot Chat requires authenticated HTTPS loopback access")
            token = self.internal_chat_token.get_secret_value()
            if not token or token != token.strip() or "\r" in token or "\n" in token:
                raise ValueError("Internal Chat configuration is invalid")
        if self.tourism_rag_enabled:
            parsed_rag_url = urlsplit(self.tourism_rag_api_url)
            if (
                environment not in {"development", "test"}
                or parsed_rag_url.scheme != "http"
                or parsed_rag_url.hostname != "127.0.0.1"
                or parsed_rag_url.port != 8765
                or parsed_rag_url.path not in {"", "/"}
                or parsed_rag_url.query
                or parsed_rag_url.fragment
                or parsed_rag_url.username
                or parsed_rag_url.password
            ):
                raise ValueError(
                    "TOURISM_RAG_API_URL must target the local development service on 127.0.0.1:8765"
                )
            if self.tourism_rag_api_token is None:
                raise ValueError("TOURISM_RAG_API_TOKEN is required when TOURISM_RAG_ENABLED is true")
            rag_token = self.tourism_rag_api_token.get_secret_value()
            if not rag_token or rag_token != rag_token.strip() or "\r" in rag_token or "\n" in rag_token:
                raise ValueError("TOURISM_RAG_API_TOKEN is invalid")
        if self.auth_sms_adapter not in {"disabled", "fake", "sms_ir_sandbox", "sms_ir_live_staging"}:
            raise ValueError("AUTH_SMS_ADAPTER is not supported")
        if environment == "production":
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
        if self.auth_sms_adapter == "sms_ir_live_staging":
            if environment != "staging" or not self.auth_enabled or not self.staging_auth_enabled:
                raise ValueError("Live SMS.ir is restricted to authenticated staging")
            secret_path = self.sms_ir_production_api_key_file
            if secret_path != Path("/run/secrets/sms_ir_production_api_key"):
                raise ValueError("Live staging SMS must use its dedicated mounted secret file")
            if self.sms_ir_production_template_id <= 0 or self.sms_ir_production_template_id == 123456:
                raise ValueError("A non-sandbox SMS_IR_PRODUCTION_TEMPLATE_ID is required for live staging SMS")
        if self.auth_enabled:
            for name in ("auth_otp_hmac_secret", "auth_csrf_secret", "auth_rate_limit_secret"):
                secret = getattr(self, name)
                if secret is None or len(secret.get_secret_value().encode("utf-8")) < 32:
                    raise ValueError(f"{name.upper()} must contain at least 32 bytes when authentication is enabled")
            if self.auth_session_idle_seconds is None or self.auth_session_absolute_seconds is None:
                raise ValueError("Both authentication session lifetimes must be configured")
            if self.auth_session_idle_seconds > self.auth_session_absolute_seconds:
                raise ValueError("Session idle lifetime cannot exceed absolute lifetime")
            if (self.auth_sms_adapter == "disabled" and not self.auth_local_owner_enabled
                    and not self.staging_auth_enabled):
                raise ValueError("Authentication is enabled without an available SMS delivery adapter")
            if not self.auth_allowed_origins.strip():
                raise ValueError("AUTH_ALLOWED_ORIGINS must contain at least one exact origin")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
