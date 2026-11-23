#!/usr/bin/env bash
# Guarded V2 apex maintenance lifecycle. Default is read-only plan mode.
# A 503 alone is never reported as a writer freeze: freeze also drains/stops
# the uniquely identified API/Web pair and verifies zero active DB work.
set -Eeuo pipefail
umask 077

mode="${1:---plan}"
case "$mode" in --plan|--status|--freeze|--restore) ;; *) echo 'usage: freeze_rahgard_v2_live.sh [--plan|--status|--freeze|--restore]' >&2; exit 64 ;; esac

expected_sha="${RAHGARD_EXPECTED_RELEASE_SHA:-36625ecf269c2a3d5590528257d32af2b6f47dd0}"
expected_api_image_id="sha256:2c814062db391b3b484b8c45b622329e9f8519a1bf0cc1627828744b23ab497e"
expected_web_image_id="sha256:44fb963eea6b5fa0dbd2a876036906c15581eec8677e34f3111781229eabd375"
expected_db_image="rahgard-postgres:17-postgis36-vector087"
expected_db_image_id="sha256:a30c041297b2306a8bb79cc6ed737f16bfca3078a3024324bb8115b302e83535"
expected_volume="rahgard_staging_pgdata"
db="rahgard-staging-db-1"
api="rahgard-staging-api-1"
web="rahgard-staging-web-1"
test_mode=false
if [[ -n "${RAHGARD_OPS_TEST_ROOT:-}" ]]; then
  test_mode=true
  root="$(cd "$RAHGARD_OPS_TEST_ROOT" && pwd -P)"
  [[ -f "$root/.rahgard-ops-test" ]] || { echo 'test root marker missing' >&2; exit 65; }
  conf="$root/nginx/conf.d/rahgard-v2-apex.conf"
  saved="$root/state/rahgard-v2-apex.conf.pre-freeze"
  root_path="$root"
else
  root=/opt/rahgard-staging
  conf=/etc/nginx/conf.d/rahgard-v2-apex.conf
  saved="$root/state/rahgard-v2-apex.conf.pre-freeze"
  root_path="$root"
  [[ "$(id -u)" == 0 ]] || { echo 'run as root through the approved operator path' >&2; exit 77; }
fi

run_nginx() {
  if $test_mode; then nginx "$@"; else nginx "$@"; fi
}
docker_cmd() { docker "$@"; }
assert_sha() { [[ "$expected_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'invalid expected release SHA' >&2; exit 65; }; }
assert_release_marker() {
  local marker="$root_path/releases/$expected_sha/RELEASE_COMMIT"
  [[ -f "$marker" && "$(cat "$marker")" == "$expected_sha" ]] || { echo 'immutable V2 release source marker mismatch' >&2; return 1; }
}
assert_v2_environment() {
  local env_file="$root_path/.env.v2"
  [[ -f "$env_file" && ! -L "$env_file" ]] || { echo 'separate V2 runtime env missing or symlinked' >&2; return 1; }
  if ! python3 - "$env_file" "$expected_sha" "$expected_volume" <<'PY'
import pathlib
import stat
import sys
p = pathlib.Path(sys.argv[1])
values = {}
for line in p.read_text(encoding="utf-8").splitlines():
    if line and not line.lstrip().startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        values.setdefault(key, []).append(value)
expected = {
    "RAHGARD_PUBLIC_HOST": "hinaa.ir",
    "RAHGARD_RELEASE_SHA": sys.argv[2],
    "RAHGARD_WEB_BIND_PORT": "18081",
    "RAHGARD_COMPOSE_PROJECT": "rahgard-staging",
    "RAHGARD_PG_VOLUME": sys.argv[3],
    "RAHGARD_STAGING_EMAIL_SIGNUP_ENABLED": "true",
    "RAHGARD_BUILD_IMAGES": "false",
}
if any(values.get(k) != [v] for k, v in expected.items()) or stat.S_IMODE(p.stat().st_mode) != 0o600:
    raise SystemExit(1)
PY
  then
    echo 'V2 runtime host/release/volume/config permission mismatch' >&2
    return 1
  fi
}
assert_apex_vhost() {
  [[ -f "$conf" ]] || { echo 'expected apex vhost missing' >&2; return 1; }
  local text
  text="$(cat "$conf")"
  [[ "$(grep -Ec '^[[:space:]]*server_name[[:space:]]+hinaa\.ir;' <<<"$text")" == 1 ]] || { echo 'apex server_name differs' >&2; return 1; }
  grep -Eq '^[[:space:]]*listen[[:space:]]+63202[[:space:]]+ssl;' <<<"$text" || { echo 'apex HTTPS listener differs' >&2; return 1; }
  grep -Fq 'if ($ssl_server_name != hinaa.ir)' "$conf" && grep -Fq 'if ($host != hinaa.ir)' "$conf" || { echo 'exact apex SNI/Host guards missing' >&2; return 1; }
  if grep -Fq 'RAHGARD_APEX_MAINTENANCE' "$conf"; then
    grep -Fq 'return 503;' "$conf" || { echo 'maintenance marker without maintenance response' >&2; return 1; }
  else
    [[ "$(grep -Fc 'proxy_pass http://127.0.0.1:18081;' "$conf")" == 1 ]] || { echo 'apex upstream differs from expected V2 web listener' >&2; return 1; }
  fi
  local all
  all="$(nginx -T 2>&1)" || { echo 'nginx -T failed' >&2; return 1; }
  [[ "$(grep -Ec '^[[:space:]]*server_name[[:space:]]+hinaa\.ir[[:space:]]*;' <<<"$all")" == 1 ]] || { echo 'Nginx has duplicate or unexpected exact-apex vhost' >&2; return 1; }
}
assert_database_identity() {
  [[ "$(docker_cmd inspect -f '{{.State.Health.Status}}' "$db")" == healthy ]] || { echo 'database health mismatch' >&2; return 1; }
  [[ "$(docker_cmd inspect -f '{{.Config.Image}}' "$db")" == "$expected_db_image" ]] || { echo 'database image mismatch' >&2; return 1; }
  [[ "$(docker_cmd inspect -f '{{.Image}}' "$db")" == "$expected_db_image_id" ]] || { echo 'database image digest mismatch' >&2; return 1; }
  local mounts
  mounts="$(docker_cmd inspect -f '{{json .Mounts}}' "$db")"
  if ! RAHGARD_MOUNTS_JSON="$mounts" python3 - "$expected_volume" <<'PY'
import json
import os
import sys
try:
    mounts = json.loads(os.environ["RAHGARD_MOUNTS_JSON"])
except Exception:
    raise SystemExit(1)
matches = [m for m in mounts if m.get("Destination") == "/var/lib/postgresql/data"]
raise SystemExit(0 if len(matches) == 1 and matches[0].get("Type") == "volume" and matches[0].get("Name") == sys.argv[1] else 1)
PY
  then
    echo 'persistent database volume mismatch' >&2
    return 1
  fi
}
assert_unique_v2_writer() {
  local rows api_rows
  rows="$(docker_cmd ps --format '{{.Names}}|{{.Image}}')"
  api_rows="$(grep -E '(^|\|)rahgard-api:' <<<"$rows" || true)"
  if [[ "$(wc -l <<<"$api_rows" | tr -d ' ')" != 1 || "$api_rows" != "$api|rahgard-api:$expected_sha" ]]; then
    echo 'expected exactly one running V2 API writer; legacy/duplicate API detected' >&2
    return 1
  fi
  grep -Fxq "$web|rahgard-web:$expected_sha" <<<"$rows" || { echo 'expected V2 web container/image missing' >&2; return 1; }
  [[ "$(docker_cmd inspect -f '{{.State.Health.Status}}' "$api")" == healthy ]] || { echo 'V2 API is not healthy' >&2; return 1; }
  [[ "$(docker_cmd inspect -f '{{.State.Health.Status}}' "$web")" == healthy ]] || { echo 'V2 web is not healthy' >&2; return 1; }
  [[ "$(docker_cmd inspect -f '{{.Image}}' "$api")" == "$expected_api_image_id" ]] || { echo 'V2 API immutable image ID mismatch' >&2; return 1; }
  [[ "$(docker_cmd inspect -f '{{.Image}}' "$web")" == "$expected_web_image_id" ]] || { echo 'V2 web immutable image ID mismatch' >&2; return 1; }
}
db_active_work() {
  if $test_mode; then docker_cmd exec "$db" rahgard-test-active-work; return; fi
  docker_cmd exec -i "$db" sh -lc 'export PGPASSWORD="$(cat /run/secrets/pg_owner_password)"; exec psql -XqAt -v ON_ERROR_STOP=1 -h 127.0.0.1 -U ai_tourism_owner -d rahgard_pilot_vps_staging' <<'SQL'
BEGIN READ ONLY;
SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND state IS DISTINCT FROM 'idle';
COMMIT;
SQL
}
assert_maintenance_response() {
  if $test_mode; then curl --silent --fail-with-body http://127.0.0.1:18081/; return; fi
  local code
  code="$(curl --silent --show-error --insecure --resolve hinaa.ir:63202:127.0.0.1 --output /dev/null --write-out '%{http_code}' https://hinaa.ir:63202/)"
  [[ "$code" == 503 ]] || { echo 'canonical apex SNI/Host maintenance probe did not return 503' >&2; return 1; }
}
assert_upstream_healthy() {
  local code
  if $test_mode; then code="$(curl --silent --output /dev/null --write-out '%{http_code}' http://127.0.0.1:18081/)"; else code="$(curl --silent --output /dev/null --write-out '%{http_code}' http://127.0.0.1:18081/)"; fi
  [[ "$code" =~ ^(200|301|302)$ ]] || { echo 'V2 web upstream is not healthy' >&2; return 1; }
}

assert_sha
assert_release_marker
assert_v2_environment
assert_apex_vhost
assert_database_identity

case "$mode" in
  --plan)
    if grep -Fq 'RAHGARD_APEX_MAINTENANCE' "$conf"; then
      echo 'APEX_MAINTENANCE_ALREADY_ACTIVE; this is not by itself a writer freeze'
    else
      assert_unique_v2_writer
      echo "PLAN_ONLY apex=hinaa.ir sni=hinaa.ir listener=63202 upstream=127.0.0.1:18081 release=$expected_sha volume=$expected_volume writes=no"
    fi
    ;;
  --status)
    if grep -Fq 'RAHGARD_APEX_MAINTENANCE' "$conf"; then
      echo 'maintenance=active http_mode=apex_503'
    else
      echo 'maintenance=inactive'
    fi
    if docker_cmd inspect -f '{{.State.Running}}' "$api" 2>/dev/null | grep -qx true; then echo 'api=running'; else echo 'api=stopped'; fi
    if docker_cmd inspect -f '{{.State.Running}}' "$web" 2>/dev/null | grep -qx true; then echo 'web=running'; else echo 'web=stopped'; fi
    work="$(db_active_work)"
    [[ "$work" =~ ^[0-9]+$ ]] || { echo 'database activity status unavailable' >&2; exit 1; }
    echo "active_db_work=$work"
    if grep -Fq 'RAHGARD_APEX_MAINTENANCE' "$conf" \
       && ! docker_cmd inspect -f '{{.State.Running}}' "$api" 2>/dev/null | grep -qx true \
       && ! docker_cmd inspect -f '{{.State.Running}}' "$web" 2>/dev/null | grep -qx true \
       && [[ "$work" == 0 ]]; then
      echo 'writer_freeze=verified'
    else
      echo 'writer_freeze=not_verified'
    fi
    ;;
  --freeze)
    if grep -Fq 'RAHGARD_APEX_MAINTENANCE' "$conf"; then
      [[ -e "$saved" ]] || { echo 'maintenance active but prior-config snapshot missing' >&2; exit 1; }
      if docker_cmd inspect -f '{{.State.Running}}' "$api" 2>/dev/null | grep -qx false && docker_cmd inspect -f '{{.State.Running}}' "$web" 2>/dev/null | grep -qx false; then
        echo 'ALREADY_FROZEN new_writes=blocked inflight=drained http_mode=apex_503 api=stopped web=stopped'
        exit 0
      fi
      echo 'partial or interrupted freeze state; inspect manually, refusing repeated mutation' >&2
      exit 1
    fi
    assert_unique_v2_writer
    [[ ! -e "$saved" ]] || { echo 'stale prior-config snapshot exists; refusing to overwrite' >&2; exit 1; }
    cp -p "$conf" "$saved"
    temp="$conf.rahgard-new"
    cp -p "$conf" "$temp"
    python3 - "$temp" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
needle = "    location / {\n        proxy_pass http://127.0.0.1:18081;"
if s.count(needle) != 1 or "RAHGARD_APEX_MAINTENANCE" in s:
    raise SystemExit("apex location changed; refusing to patch")
s = s.replace(needle, "    location / {\n        # RAHGARD_APEX_MAINTENANCE\n        add_header Retry-After 120 always;\n        return 503;", 1)
p.write_text(s, encoding="utf-8")
PY
    mv "$temp" "$conf"
    if ! run_nginx -t; then cp -p "$saved" "$conf"; rm -f "$saved"; exit 1; fi
    run_nginx -s reload
    assert_maintenance_response
    docker_cmd stop --time 30 "$api"
    docker_cmd stop --time 30 "$web"
    for _ in {1..30}; do
      [[ "$(db_active_work)" == 0 ]] && break
      sleep 1
    done
    [[ "$(docker_cmd inspect -f '{{.State.Running}}' "$api")" == false ]] || { echo 'API writer did not stop' >&2; exit 1; }
    [[ "$(docker_cmd inspect -f '{{.State.Running}}' "$web")" == false ]] || { echo 'web did not stop' >&2; exit 1; }
    [[ "$(db_active_work)" == 0 ]] || { echo 'database still reports active work; freeze incomplete' >&2; exit 1; }
    echo 'FROZEN new_writes=blocked inflight=drained http_mode=apex_503 api_writer=stopped web=stopped active_db_work=0; exact previous vhost saved'
    ;;
  --restore)
    [[ -f "$saved" ]] || { echo 'previous apex vhost snapshot missing' >&2; exit 1; }
    assert_unique_v2_writer
    assert_upstream_healthy
    temp="$conf.rahgard-maintenance"
    cp -p "$conf" "$temp"
    cp -p "$saved" "$conf"
    if ! run_nginx -t; then cp -p "$temp" "$conf"; rm -f "$temp"; exit 1; fi
    run_nginx -s reload
    code="$(curl --silent --output /dev/null --write-out '%{http_code}' http://127.0.0.1:18081/)"
    if [[ ! "$code" =~ ^(200|301|302)$ ]]; then
      cp -p "$temp" "$conf"; run_nginx -t; run_nginx -s reload
      echo 'health probe failed; restored maintenance config' >&2
      exit 1
    fi
    rm -f "$temp" "$saved"
    echo 'RESTORED exact prior apex vhost after V2 health checks'
    ;;
esac
