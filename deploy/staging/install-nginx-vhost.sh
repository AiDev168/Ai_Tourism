#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
cd "$(dirname "$0")"
set -a; . /opt/rahgard-staging/.env; set +a
host="${RAHGARD_PUBLIC_HOST:-}"
[[ "$host" =~ ^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$ ]] || { echo 'RAHGARD_PUBLIC_HOST is invalid.' >&2; exit 2; }
file=/etc/nginx/conf.d/rahgard-staging.conf
[[ ! -e "$file" ]] || { echo 'Dedicated Nginx filename already exists; preserving it.' >&2; exit 2; }
if sudo -n nginx -T 2>/dev/null | grep -Eiq "server_name[^;]*(^|[[:space:]])${host//./\.}([[:space:]]|;)"; then
  echo 'The requested host already appears in active Nginx configuration; no change made.' >&2; exit 2
fi
resolved=$(getent ahostsv4 "$host" | awk '{print $1}' | sort -u | tr '\n' ' ')
[[ -n "$resolved" ]] || { echo 'The staging hostname has no IPv4 DNS answer yet.' >&2; exit 2; }
if ! timeout 8 openssl s_client -verify_return_error -CApath /etc/ssl/certs \
    -connect "$host:443" -servername "$host" </dev/null >/dev/null 2>&1; then
  echo 'The staging hostname does not yet present a trusted HTTPS certificate.' >&2; exit 2
fi
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
sed "s/__RAHGARD_PUBLIC_HOST__/$host/g" nginx-host.conf.template > "$tmp"
grep -Fq "server_name $host;" "$tmp" || { echo 'Generated vhost validation failed.' >&2; exit 2; }
sudo -n install -o root -g root -m 0644 "$tmp" "$file"
if ! sudo -n nginx -t; then
  sudo -n rm -f -- "$file"
  sudo -n nginx -t >/dev/null 2>&1 || true
  echo 'Nginx rejected the additive staging config; it was removed without reloading.' >&2
  exit 2
fi
if ! sudo -n systemctl reload nginx; then
  sudo -n rm -f -- "$file"
  sudo -n nginx -t && sudo -n systemctl reload nginx || true
  echo 'Nginx reload failed; only the newly created staging file was removed.' >&2
  exit 2
fi
printf 'Installed dedicated HTTPS-origin vhost for %s; existing vhost files were not changed.\n' "$host"
