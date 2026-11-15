#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

dir="${RAHGARD_SECRET_DIR:-/opt/rahgard-staging/secrets}"
target="$dir/sms_ir_production_api_key"
install -d -m 0700 "$dir"
[[ ! -L "$target" ]] || { echo 'SMS secret target must not be a symlink.' >&2; exit 2; }
if [[ -e "$target" && -s "$target" ]]; then
  echo 'An SMS secret already exists; preserving it.' >&2
  exit 2
fi

tmp=$(mktemp "$dir/.sms_ir_production_api_key.XXXXXXXX")
cleanup() {
  unset api_key extra
  rm -f -- "$tmp"
}
trap cleanup EXIT

api_key=''
if ! IFS= read -r api_key && [[ -z "$api_key" ]]; then
  echo 'SMS secret input is empty.' >&2
  exit 2
fi
extra=''
if IFS= read -r extra || [[ -n "$extra" ]]; then
  echo 'SMS secret input must contain exactly one line.' >&2
  exit 2
fi
[[ -n "$api_key" && "$api_key" != *[[:space:]]* ]] || {
  echo 'SMS secret input is invalid.' >&2
  exit 2
}
printf '%s' "$api_key" > "$tmp"
unset api_key
size=$(wc -c < "$tmp")
(( size >= 16 && size <= 4096 )) || { echo 'SMS secret input is invalid.' >&2; exit 2; }
sudo -n chown "${RAHGARD_SECRET_OWNER_USER:-$(id -un)}:999" "$tmp"
chmod 0640 "$tmp"
mv -f -- "$tmp" "$target"
trap - EXIT
unset extra
printf 'SMS.ir staging credential installed with restricted permissions; value not displayed.\n'
