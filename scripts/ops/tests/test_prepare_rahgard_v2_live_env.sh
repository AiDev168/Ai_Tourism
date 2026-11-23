#!/usr/bin/env bash
set -Eeuo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
script="$repo/scripts/ops/prepare_rahgard_v2_live_env.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
root="$tmp/pilot"
mkdir -p "$root/current" "$root/releases/36625ecf269c2a3d5590528257d32af2b6f47dd0/deploy/staging" "$root/bin"
touch "$root/.rahgard-env-test"
printf '%s\n' 5e2664fb51e18f52549aa37a8b5793e12ace09b2 >"$root/current/RELEASE_COMMIT"
printf '%s\n' 36625ecf269c2a3d5590528257d32af2b6f47dd0 >"$root/releases/36625ecf269c2a3d5590528257d32af2b6f47dd0/RELEASE_COMMIT"
cat >"$root/releases/36625ecf269c2a3d5590528257d32af2b6f47dd0/deploy/staging/compose.yaml" <<'YAML'
services: {}
YAML
cat >"$root/.env" <<'ENV'
RAHGARD_PUBLIC_HOST=rahgard.hinaa.ir
RAHGARD_RELEASE_SHA=5e2664fb51e18f52549aa37a8b5793e12ace09b2
RAHGARD_WEB_BIND_PORT=18080
RAHGARD_COMPOSE_PROJECT=rahgard-staging
RAHGARD_PG_VOLUME=rahgard_staging_pgdata
RAHGARD_STAGING_EMAIL_SIGNUP_ENABLED=true
RAHGARD_BUILD_IMAGES=false
PRIVATE_TEST_SECRET=do-not-print
ENV
cat >"$root/bin/docker" <<'SH'
#!/usr/bin/env bash
[[ "$1" == compose && " $* " == *" config --quiet "* ]] || exit 64
[[ -f "$RAHGARD_TEST_ENV" ]] || exit 65
if grep -q '^RAHGARD_PUBLIC_HOST=hinaa.ir$' "$RAHGARD_TEST_ENV"; then exit 0; fi
exit 66
SH
chmod +x "$root/bin/docker"

export RAHGARD_ENV_TEST_ROOT="$root"
export RAHGARD_TEST_ENV="$root/.env.v2"
export PATH="$root/bin:$PATH"
out="$(bash "$script")"
grep -Fq 'V2_ENV_PREPARED; changed_keys=' <<<"$out"
[[ "$(stat -c '%a' "$root/.env.v2")" == 600 ]]
! grep -q 'do-not-print' <<<"$out"
before="$(sha256sum "$root/.env.v2" | cut -d' ' -f1)"
out="$(bash "$script")"
grep -Fq 'EXISTING_V2_ENV_VERIFIED; no file changed' <<<"$out"
after="$(sha256sum "$root/.env.v2" | cut -d' ' -f1)"
[[ "$before" == "$after" ]]
sed -i 's/RAHGARD_PUBLIC_HOST=hinaa.ir/RAHGARD_PUBLIC_HOST=wrong.example/' "$root/.env.v2"
if bash "$script" >/dev/null 2>&1; then echo 'unexpected existing config was overwritten/accepted' >&2; exit 1; fi
grep -q '^RAHGARD_PUBLIC_HOST=wrong.example$' "$root/.env.v2" || { echo 'mismatch was modified' >&2; exit 1; }
echo 'PASS isolated env preparation: 0600 creation, secret redaction, repeat verifies without rewrite, mismatch fails closed'
