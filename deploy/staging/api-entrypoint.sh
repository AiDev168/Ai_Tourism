#!/bin/sh
set -eu

read_secret() {
  file="$1"
  name="$2"
  test -r "$file" || { echo "required runtime secret unavailable" >&2; exit 1; }
  value=$(cat "$file")
  test -n "$value" || { echo "required runtime secret unavailable" >&2; exit 1; }
  export "$name=$value"
  unset value
}

read_secret /run/secrets/app_db_password DATABASE_PASSWORD
read_secret /run/secrets/auth_otp_hmac_secret AUTH_OTP_HMAC_SECRET
read_secret /run/secrets/auth_csrf_secret AUTH_CSRF_SECRET
read_secret /run/secrets/auth_rate_limit_secret AUTH_RATE_LIMIT_SECRET
if [ "${INTERNAL_CHAT_ENABLED:-false}" = "true" ]; then
  read_secret /run/secrets/internal_chat_token INTERNAL_CHAT_TOKEN
fi
exec "$@"
