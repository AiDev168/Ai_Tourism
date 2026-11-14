#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root="${RAHGARD_ROOT:-/opt/rahgard-staging}"
user="${RAHGARD_OPERATOR_USER:-$(id -un)}"
if [[ "$root" != /opt/rahgard-staging ]]; then
  echo 'This tested staging package is rooted only at /opt/rahgard-staging; review source before changing it.' >&2
  exit 2
fi
sudo install -d -o "$user" -g "$user" -m 0700 "$root" "$root/secrets" "$root/state" \
  "$root/backups" "$root/releases"
install -d -m 0700 "$root/secrets" "$root/state" "$root/backups" "$root/releases"
if [[ -e "$root/.env" && ( ! -f "$root/.env" || -L "$root/.env" ) ]]; then
  echo 'Deployment config is not a regular non-symlink file; preserving it.' >&2; exit 2
fi
export RAHGARD_SECRET_DIR="$root/secrets"
"$(dirname "$0")/prepare-secrets.sh"
if [[ ! -e "$root/.env" ]]; then
  cp "$(dirname "$0")/config.env.example" "$root/.env"
  chmod 0600 "$root/.env"
fi
if ! grep -q '^RAHGARD_STATE_DIR=' "$root/.env"; then
  printf 'RAHGARD_STATE_DIR=%s/state\n' "$root" >> "$root/.env"
fi
chmod 0600 "$root/.env"
printf 'Prepared owner-only deployment directories at %s. DNS, Nginx, containers and database were not modified.\n' "$root"
