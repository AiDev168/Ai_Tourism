#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
dir="${RAHGARD_SECRET_DIR:-/opt/rahgard-staging/secrets}"
install -d -m 0700 "$dir"
create_secret() {
  local name="$1" tmp
  local target="$dir/$name"
  if [[ -e "$target" ]]; then
    [[ -f "$target" && ! -L "$target" && -s "$target" ]] || { echo "Existing secret file is invalid: $name" >&2; exit 2; }
  else
    tmp=$(mktemp "$dir/.${name}.XXXXXXXX")
    openssl rand -hex 32 > "$tmp"
    chmod 0600 "$tmp"
    mv -- "$tmp" "$target"
  fi
  # The API/PostgreSQL images use numeric GID 999. Their individual Compose
  # secret mounts need group-read, while the owner-only parent directory keeps
  # these files inaccessible to other host users.
  sudo -n chown "${RAHGARD_SECRET_OWNER_USER:-$(id -un)}:999" "$target"
  chmod 0640 "$target"
}
for key in pg_owner_password app_db_password auth_otp_hmac_secret auth_csrf_secret \
           auth_rate_limit_secret internal_chat_token geo_authorizer_password geo_publisher_password \
           backup_encryption_passphrase; do
  create_secret "$key"
done
printf 'Private staging runtime secrets are present under %s; no values displayed.\n' "$dir"
