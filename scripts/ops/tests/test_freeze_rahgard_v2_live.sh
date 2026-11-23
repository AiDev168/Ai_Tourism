#!/usr/bin/env bash
set -Eeuo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
script="$repo/scripts/ops/freeze_rahgard_v2_live.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_contains() { grep -Fq "$2" <<<"$1" || fail "expected output: $2"; }

make_fixture() {
  local root="$tmp/$1"
  mkdir -p "$root/nginx/conf.d" "$root/state" "$root/bin" "$root/releases/36625ecf269c2a3d5590528257d32af2b6f47dd0"
  printf '%s\n' 36625ecf269c2a3d5590528257d32af2b6f47dd0 >"$root/releases/36625ecf269c2a3d5590528257d32af2b6f47dd0/RELEASE_COMMIT"
  touch "$root/.rahgard-ops-test" "$root/api.running" "$root/web.running"
  cat >"$root/.env.v2" <<'ENV'
RAHGARD_PUBLIC_HOST=hinaa.ir
RAHGARD_RELEASE_SHA=36625ecf269c2a3d5590528257d32af2b6f47dd0
RAHGARD_WEB_BIND_PORT=18081
RAHGARD_COMPOSE_PROJECT=rahgard-staging
RAHGARD_PG_VOLUME=rahgard_staging_pgdata
RAHGARD_STAGING_EMAIL_SIGNUP_ENABLED=true
RAHGARD_BUILD_IMAGES=false
ENV
  chmod 600 "$root/.env.v2"
  cat >"$root/nginx/conf.d/rahgard-v2-apex.conf" <<'NGINX'
server {
    listen 63202 ssl;
    server_name hinaa.ir;
    if ($ssl_server_name != hinaa.ir) { return 421; }
    if ($host != hinaa.ir) { return 421; }
    location / {
        proxy_pass http://127.0.0.1:18081;
    }
}
NGINX
  cat >"$root/bin/nginx" <<'SH'
#!/usr/bin/env bash
if [[ "$1" == -T ]]; then cat "$OPS_TEST_ROOT/nginx/conf.d/rahgard-v2-apex.conf"; exit 0; fi
if [[ "$1" == -t ]]; then exit 0; fi
if [[ "$1" == -s && "$2" == reload ]]; then echo reload >>"$OPS_TEST_ROOT/reloads"; exit 0; fi
exit 64
SH
  cat >"$root/bin/docker" <<'SH'
#!/usr/bin/env bash
set -eu
op="$1"; shift
if [[ "$op" == inspect ]]; then
  [[ "$1" == -f ]] || exit 64; fmt="$2"; name="$3"
  case "$fmt" in
    *State.Health.Status*) echo healthy ;;
    *Config.Image*)
      case "$name" in
        rahgard-staging-db-1) echo rahgard-postgres:17-postgis36-vector087 ;;
        rahgard-staging-api-1) echo 'rahgard-api:36625ecf269c2a3d5590528257d32af2b6f47dd0' ;;
        rahgard-staging-web-1) echo 'rahgard-web:36625ecf269c2a3d5590528257d32af2b6f47dd0' ;;
      esac ;;
    *Image*)
      case "$name" in
        rahgard-staging-db-1) echo sha256:a30c041297b2306a8bb79cc6ed737f16bfca3078a3024324bb8115b302e83535 ;;
        rahgard-staging-api-1) [[ "${TEST_BAD_IMAGE:-false}" == true ]] && echo sha256:$(printf '0%.0s' {1..64}) || echo sha256:2c814062db391b3b484b8c45b622329e9f8519a1bf0cc1627828744b23ab497e ;;
        rahgard-staging-web-1) echo sha256:44fb963eea6b5fa0dbd2a876036906c15581eec8677e34f3111781229eabd375 ;;
      esac ;;
    *Mounts*)
      if [[ -n "${TEST_VOLUME:-}" ]]; then vol="${TEST_VOLUME#*|}"; else vol=rahgard_staging_pgdata; fi
      echo "[{\"Type\":\"volume\",\"Name\":\"$vol\",\"Destination\":\"/var/lib/postgresql/data\"}]" ;;
    *State.Running*)
      case "$name" in rahgard-staging-api-1) state=api;; rahgard-staging-web-1) state=web;; *) state=db;; esac
      if [[ -e "$OPS_TEST_ROOT/$state.running" ]]; then echo true; else echo false; fi ;;
    *) exit 64 ;;
  esac
elif [[ "$op" == ps ]]; then
  if [[ "${TEST_EXTRA_API:-false}" == true ]]; then echo 'rahgard-staging-api-1|rahgard-api:36625ecf269c2a3d5590528257d32af2b6f47dd0'; echo 'rogue-api|rahgard-api:legacy'; else echo 'rahgard-staging-api-1|rahgard-api:36625ecf269c2a3d5590528257d32af2b6f47dd0'; fi
  echo 'rahgard-staging-web-1|rahgard-web:36625ecf269c2a3d5590528257d32af2b6f47dd0'
elif [[ "$op" == stop ]]; then
  shift 2
  case "$1" in rahgard-staging-api-1) state=api;; rahgard-staging-web-1) state=web;; *) exit 64;; esac
  rm -f "$OPS_TEST_ROOT/$state.running"
elif [[ "$op" == exec && "${1:-}" == rahgard-staging-db-1 && "${2:-}" == rahgard-test-active-work ]]; then echo 0
else exit 64
fi
SH
  cat >"$root/bin/curl" <<'SH'
#!/usr/bin/env bash
if [[ "${TEST_UPSTREAM_CODE:-200}" == 200 ]]; then
  [[ " $* " == *"--write-out"* ]] && { printf 200; exit 0; }
  exit 0
fi
[[ " $* " == *"--write-out"* ]] && { printf '%s' "$TEST_UPSTREAM_CODE"; exit 0; }
exit 22
SH
  chmod +x "$root/bin/"*
  printf '%s' "$root"
}

run_script() {
  local root="$1" mode="$2"
  OPS_TEST_ROOT="$root" RAHGARD_OPS_TEST_ROOT="$root" PATH="$root/bin:$PATH" bash "$script" "$mode"
}

root="$(make_fixture healthy)"
out="$(run_script "$root" --freeze)" || fail 'isolated apex freeze failed'
assert_contains "$out" 'FROZEN new_writes=blocked inflight=drained http_mode=apex_503 api_writer=stopped web=stopped active_db_work=0'
[[ -f "$root/state/rahgard-v2-apex.conf.pre-freeze" ]] || fail 'exact previous config snapshot missing'
[[ ! -e "$root/api.running" && ! -e "$root/web.running" ]] || fail 'writer/web still running after freeze'
out="$(run_script "$root" --status)" || fail 'status inspection failed after freeze'
assert_contains "$out" 'writer_freeze=verified'
out="$(run_script "$root" --freeze)" || fail 'repeated freeze was not idempotent'
assert_contains "$out" 'ALREADY_FROZEN'
touch "$root/api.running" "$root/web.running"
out="$(run_script "$root" --restore)" || fail 'isolated restoration failed'
assert_contains "$out" 'RESTORED exact prior apex vhost'
! grep -Fq RAHGARD_APEX_MAINTENANCE "$root/nginx/conf.d/rahgard-v2-apex.conf" || fail 'maintenance marker remains after restore'
[[ ! -e "$root/state/rahgard-v2-apex.conf.pre-freeze" ]] || fail 'snapshot not cleaned after successful restore'

root="$(make_fixture legacy_only)"
sed -i 's/server_name hinaa\.ir;/server_name rahgard.hinaa.ir;/' "$root/nginx/conf.d/rahgard-v2-apex.conf"
if run_script "$root" --plan >/dev/null 2>&1; then fail 'legacy-only vhost incorrectly passed'; fi
[[ -e "$root/api.running" ]] || fail 'legacy-only rejection modified services'

root="$(make_fixture extra_writer)"
if TEST_EXTRA_API=true OPS_TEST_ROOT="$root" RAHGARD_OPS_TEST_ROOT="$root" PATH="$root/bin:$PATH" bash "$script" --plan >/dev/null 2>&1; then fail 'unexpected active writer incorrectly passed'; fi

root="$(make_fixture bad_sha)"
if RAHGARD_EXPECTED_RELEASE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa OPS_TEST_ROOT="$root" RAHGARD_OPS_TEST_ROOT="$root" PATH="$root/bin:$PATH" bash "$script" --plan >/dev/null 2>&1; then fail 'SHA mismatch incorrectly passed'; fi

root="$(make_fixture bad_volume)"
if TEST_VOLUME='volume|unexpected' OPS_TEST_ROOT="$root" RAHGARD_OPS_TEST_ROOT="$root" PATH="$root/bin:$PATH" bash "$script" --plan >/dev/null 2>&1; then fail 'volume mismatch incorrectly passed'; fi

root="$(make_fixture bad_image)"
if TEST_BAD_IMAGE=true OPS_TEST_ROOT="$root" RAHGARD_OPS_TEST_ROOT="$root" PATH="$root/bin:$PATH" bash "$script" --plan >/dev/null 2>&1; then fail 'immutable image ID mismatch incorrectly passed'; fi

root="$(make_fixture interrupted)"
sed -i '/proxy_pass/i\        # RAHGARD_APEX_MAINTENANCE\n        return 503;' "$root/nginx/conf.d/rahgard-v2-apex.conf"
if run_script "$root" --freeze >/dev/null 2>&1; then fail 'interrupted state without snapshot incorrectly passed'; fi
[[ -e "$root/api.running" ]] || fail 'interrupted-state refusal modified API'

root="$(make_fixture restore_health_fail)"
OPS_TEST_ROOT="$root" RAHGARD_OPS_TEST_ROOT="$root" PATH="$root/bin:$PATH" bash "$script" --freeze >/dev/null || fail 'setup freeze failed'
touch "$root/api.running" "$root/web.running"
if TEST_UPSTREAM_CODE=503 OPS_TEST_ROOT="$root" RAHGARD_OPS_TEST_ROOT="$root" PATH="$root/bin:$PATH" bash "$script" --restore >/dev/null 2>&1; then fail 'restore without healthy upstream incorrectly passed'; fi
grep -Fq RAHGARD_APEX_MAINTENANCE "$root/nginx/conf.d/rahgard-v2-apex.conf" || fail 'failed restore did not reinstate maintenance'

echo 'PASS isolated process rehearsal: apex freeze, exact restore, idempotency, legacy-only fail-closed, unexpected writer, SHA/volume mismatch, interrupted state, failed-health rollback'
