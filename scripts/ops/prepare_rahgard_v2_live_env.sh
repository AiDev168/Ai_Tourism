#!/usr/bin/env bash
# Idempotently prepare/verify the separate apex V2 runtime env. Never prints or
# modifies secret values. Existing files are verified, never overwritten.
set -Eeuo pipefail
umask 077

sha=36625ecf269c2a3d5590528257d32af2b6f47dd0
legacy_sha=5e2664fb51e18f52549aa37a8b5793e12ace09b2
test_mode=false
if [[ -n "${RAHGARD_ENV_TEST_ROOT:-}" ]]; then
  root="$(cd "$RAHGARD_ENV_TEST_ROOT" && pwd -P)"
  [[ -f "$root/.rahgard-env-test" ]] || { echo 'test fixture marker missing' >&2; exit 65; }
  test_mode=true
else
  root=/opt/rahgard-staging
fi
source_env="$root/.env"
target_env="$root/.env.v2"
current_marker="$root/current/RELEASE_COMMIT"
release_marker="$root/releases/$sha/RELEASE_COMMIT"

if ! $test_mode; then [[ "$(id -u)" == 0 ]] || { echo 'must run as root through the approved operator path' >&2; exit 77; }; fi
[[ -f "$source_env" && ! -L "$source_env" ]] || { echo 'legacy environment file missing or symlinked' >&2; exit 1; }
[[ -f "$release_marker" && "$(cat "$release_marker")" == "$sha" ]] || { echo 'immutable V2 release marker mismatch' >&2; exit 1; }
[[ -f "$current_marker" ]] || { echo 'legacy current release marker missing' >&2; exit 1; }

if [[ -e "$target_env" || -L "$target_env" ]]; then
  [[ -f "$target_env" && ! -L "$target_env" ]] || { echo 'existing V2 env is not a regular file' >&2; exit 1; }
  python3 - "$target_env" "$sha" <<'PY'
import pathlib
import stat
import sys
p = pathlib.Path(sys.argv[1])
values = {}
for line in p.read_text(encoding="utf-8").splitlines():
    if not line or line.lstrip().startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values.setdefault(key, []).append(value)
expected = {
    "RAHGARD_PUBLIC_HOST": "hinaa.ir",
    "RAHGARD_RELEASE_SHA": sys.argv[2],
    "RAHGARD_WEB_BIND_PORT": "18081",
    "RAHGARD_COMPOSE_PROJECT": "rahgard-staging",
    "RAHGARD_PG_VOLUME": "rahgard_staging_pgdata",
    "RAHGARD_STAGING_EMAIL_SIGNUP_ENABLED": "true",
    "RAHGARD_BUILD_IMAGES": "false",
}
for key, value in expected.items():
    if values.get(key) != [value]:
        raise SystemExit("existing V2 runtime config mismatch at " + key)
if stat.S_IMODE(p.stat().st_mode) != 0o600:
    raise SystemExit("existing V2 runtime config permissions must be exactly 0600")
print("EXISTING_V2_ENV_VERIFIED; no file changed")
PY
else
  [[ "$(cat "$current_marker")" == "$legacy_sha" ]] || { echo 'first-time env creation requires the recorded legacy release' >&2; exit 1; }
  python3 - "$source_env" "$target_env" "$sha" "$legacy_sha" <<'PY'
import os
import pathlib
import sys

source, target = map(pathlib.Path, sys.argv[1:3])
sha, old_sha = sys.argv[3:5]
lines = source.read_text(encoding="utf-8").splitlines()
values = {}
for line in lines:
    if line and not line.lstrip().startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        values.setdefault(key, []).append(value)
required = {
    "RAHGARD_PUBLIC_HOST": ("rahgard.hinaa.ir", "hinaa.ir"),
    "RAHGARD_RELEASE_SHA": (old_sha, sha),
    "RAHGARD_WEB_BIND_PORT": ("18080", "18081"),
}
for key, (old, _) in required.items():
    if values.get(key) != [old]:
        raise SystemExit("protected source configuration mismatch at " + key)
for key, value in {
    "RAHGARD_COMPOSE_PROJECT": "rahgard-staging",
    "RAHGARD_PG_VOLUME": "rahgard_staging_pgdata",
    "RAHGARD_STAGING_EMAIL_SIGNUP_ENABLED": "true",
    "RAHGARD_BUILD_IMAGES": "false",
}.items():
    if values.get(key) != [value]:
        raise SystemExit("protected source configuration mismatch at " + key)
updated = []
for line in lines:
    key, sep, _ = line.partition("=")
    if sep and key in required:
        line = key + "=" + required[key][1]
    updated.append(line)
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as stream:
    stream.write("\n".join(updated) + "\n")
print("V2_ENV_PREPARED; changed_keys=" + ",".join(sorted(required)))
PY
fi

docker compose --env-file "$target_env" -f "$root/releases/$sha/deploy/staging/compose.yaml" config --quiet
echo 'V2_COMPOSE_CONFIG_PASS; secrets redacted'
