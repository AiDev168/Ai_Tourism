"""Run the real FastAPI app with secrets loaded only inside this process."""
from __future__ import annotations

import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
secret = root / "secrets"
runtime = {
    "APP_ENV": "staging", "APP_HOST": "127.0.0.1", "APP_PORT": "8801",
    "LOG_LEVEL": "INFO", "DATABASE_HOST": "127.0.0.1", "DATABASE_PORT": "18543",
    "DATABASE_NAME": "rahgard_pilot_vps_staging", "DATABASE_USER": "ai_tourism_app",
    "AUTH_ENABLED": "true", "AUTH_COOKIE_SECURE": "true",
    "STAGING_AUTH_ENABLED": "true", "STAGING_EMAIL_SIGNUP_ENABLED": "true",
    "STAGING_PUBLIC_HOST": "localhost", "AUTH_ALLOWED_ORIGINS": "https://localhost",
    "AUTH_SESSION_IDLE_SECONDS": "1800", "AUTH_SESSION_ABSOLUTE_SECONDS": "43200",
    "AUTH_OTP_LENGTH": "6", "AUTH_OTP_TTL_SECONDS": "300",
    "AUTH_LOCAL_OWNER_ENABLED": "false", "AUTH_SMS_ADAPTER": "disabled",
    "AUTH_TRUSTED_PROXY_CIDRS": "127.0.0.1/32", "INTERNAL_CHAT_ENABLED": "false",
    "AI_PROVIDER_ADMIN_ENABLED": "false", "TOURISM_RAG_ENABLED": "false",
    "PLATFORM_ADMIN_MFA_ENCRYPTION_KEY_FILE": str(secret / "platform_admin_mfa_encryption_key_hex"),
    "PLATFORM_ADMIN_RECOVERY_PEPPER_FILE": str(secret / "platform_admin_recovery_pepper"),
    "AUTH_OTP_HMAC_SECRET": (secret / "auth_otp_hmac_secret").read_text().strip(),
    "AUTH_CSRF_SECRET": (secret / "auth_csrf_secret").read_text().strip(),
    "AUTH_RATE_LIMIT_SECRET": (secret / "auth_rate_limit_secret").read_text().strip(),
    "DATABASE_PASSWORD": (secret / "app_db_password").read_text().strip(),
}
os.environ.update(runtime)
backend = Path(__file__).resolve().parents[3] / "backend"
repo = backend.parent
os.chdir(backend)
sys.path.insert(0, str(backend))
sys.path.insert(0, str(repo))
venv_site = repo / ".venv" / "Lib" / "site-packages"
if venv_site.is_dir():
    sys.path.insert(0, str(venv_site))
import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=8801, log_level="info", access_log=False)
