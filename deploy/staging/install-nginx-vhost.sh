#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
cd "$(dirname "$0")"
set -a; . <(sed 's/\r$//' /opt/rahgard-staging/.env); set +a
host="${RAHGARD_PUBLIC_HOST:-}"
[[ "$host" == rahgard.hinaa.ir ]] || { echo 'This release is pinned to the owner-selected rahgard.hinaa.ir host.' >&2; exit 2; }
file=/etc/nginx/conf.d/rahgard-staging.conf
[[ ! -e "$file" && ! -L "$file" ]] || { echo 'Dedicated Nginx filename already exists; preserving it.' >&2; exit 2; }
cert="/etc/letsencrypt/live/$host/fullchain.pem"
key="/etc/letsencrypt/live/$host/privkey.pem"
sudo -n test -r "$cert" && sudo -n test -r "$key" || {
  echo 'A readable trusted origin certificate and key are required; no Nginx change made.' >&2; exit 2;
}
sans=$(sudo -n openssl x509 -in "$cert" -noout -ext subjectAltName 2>/dev/null || true)
printf '%s' "$sans" | grep -Fq "DNS:$host" || {
  echo 'The origin certificate SAN does not cover the exact staging hostname.' >&2; exit 2;
}
sudo -n openssl x509 -in "$cert" -checkend 86400 -noout >/dev/null || {
  echo 'The origin certificate is expired or expires within 24 hours.' >&2; exit 2;
}
cert_pub=$(sudo -n openssl x509 -in "$cert" -pubkey -noout | openssl pkey -pubin -outform DER 2>/dev/null | sha256sum | awk '{print $1}')
key_pub=$(sudo -n openssl pkey -in "$key" -pubout -outform DER 2>/dev/null | sha256sum | awk '{print $1}')
[[ -n "$cert_pub" && "$cert_pub" == "$key_pub" ]] || {
  echo 'The origin certificate and key do not match.' >&2; exit 2;
}
if sudo -n ss -H -ltn 'sport = :63202' | grep -q .; then
  echo 'Port 63202 already has a listener; preserving it.' >&2; exit 2
fi
if sudo -n nginx -T 2>/dev/null | grep -Eiq "server_name[^;]*(^|[[:space:]])${host//./\.}([[:space:]]|;)"; then
  echo 'The requested host already appears in active Nginx configuration; no change made.' >&2; exit 2
fi
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
sed "s/__RAHGARD_PUBLIC_HOST__/$host/g" nginx-host.conf.template > "$tmp"
grep -Fq "listen 63202 ssl default_server;" "$tmp"
grep -Fq "server_name $host;" "$tmp"
sudo -n install -o root -g root -m 0644 "$tmp" "$file"
rollback_new_vhost() {
  sudo -n rm -f -- "$file"
  sudo -n nginx -t && sudo -n systemctl reload nginx || true
}
if ! sudo -n nginx -t; then
  rollback_new_vhost
  echo 'Nginx rejected the additive TLS vhost; it was removed without retaining the change.' >&2
  exit 2
fi
if ! sudo -n systemctl reload nginx; then
  rollback_new_vhost
  echo 'Nginx reload failed; the new vhost was removed and prior configuration reloaded.' >&2
  exit 2
fi
if ! curl --fail --silent --show-error --max-time 12 \
    --resolve "$host:63202:127.0.0.1" "https://$host:63202/" >/dev/null; then
  rollback_new_vhost
  echo 'The local HTTPS origin check failed; the new vhost was removed.' >&2
  exit 2
fi
printf 'PASS: dedicated TLS origin installed and locally verified for %s on port 63202. Configure Arvan/NAT to use HTTPS to this port before enabling traveler access.\n' "$host"
