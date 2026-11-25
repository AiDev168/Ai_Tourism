#!/usr/bin/env bash
# Authenticated, cutover-consistent portability snapshot. Never modifies DB.
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
freeze_marker="$root/state/WRITE_FREEZE"

if [[ "${1:-}" != "--cutover-frozen" || $# -ne 1 ]]; then
  echo 'Usage: export-portable.sh --cutover-frozen' >&2
  echo 'Stop writes, create state/WRITE_FREEZE, and stop this Compose project api/web first.' >&2
  exit 2
fi
env_file="$root/.env.v2"
test -s "$env_file"
[[ -f "$root/secrets/backup_encryption_passphrase" && ! -L "$root/secrets/backup_encryption_passphrase" && -s "$root/secrets/backup_encryption_passphrase" && "$(stat -c '%a' "$root/secrets/backup_encryption_passphrase")" == 600 ]] || {
  echo 'Encryption passphrase must be a regular non-symlink file.' >&2; exit 2;
}
[[ -f "$root/secrets/portable_bundle_hmac_key" && ! -L "$root/secrets/portable_bundle_hmac_key" && -s "$root/secrets/portable_bundle_hmac_key" && "$(stat -c '%a' "$root/secrets/portable_bundle_hmac_key")" == 600 ]] || {
  echo 'Independent HMAC key must be a regular non-symlink file.' >&2; exit 2;
}
test -f "$freeze_marker" && test ! -L "$freeze_marker" || {
  echo 'A write-freeze marker is required; refusing a potentially inconsistent export.' >&2; exit 2;
}
test -d "$root/state"
test -d "$root/backups"
readarray -t runtime_identity < <(python3 - "$env_file" <<'PY'
import pathlib, re, sys
values = {}
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line and not line.lstrip().startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        values.setdefault(key, []).append(value)
sha = values.get("RAHGARD_RELEASE_SHA", [])
if len(sha) != 1 or not re.fullmatch(r"[0-9a-f]{40}", sha[0]):
    raise SystemExit("V2 runtime release SHA missing or duplicated")
if values.get("RAHGARD_PUBLIC_HOST") != ["hinaa.ir"]:
    raise SystemExit("expected canonical V2 host hinaa.ir")
if values.get("RAHGARD_BUILD_IMAGES") != ["false"]:
    raise SystemExit("portable snapshot requires immutable prebuilt images")
print(sha[0])
for key in ("RAHGARD_COMPOSE_PROJECT", "RAHGARD_PG_VOLUME", "RAHGARD_SECRET_DIR"):
    if len(values.get(key, [])) != 1 or not values[key][0]:
        raise SystemExit("missing or duplicated runtime identity setting: " + key)
    print(values[key][0])
PY
)
sha=${runtime_identity[0]:-}
compose_project=${runtime_identity[1]:-}
expected_volume=${runtime_identity[2]:-}
secret_dir=${runtime_identity[3]:-}
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid V2 release SHA.' >&2; exit 2; }
[[ "$compose_project" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$ && "$expected_volume" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$ ]] || { echo 'Invalid V2 Compose project/volume identity.' >&2; exit 2; }
[[ -d "$secret_dir" && ! -L "$secret_dir" && "$(stat -c '%a' "$secret_dir")" == 700 ]] || { echo 'Runtime secret directory must be a real mode-0700 directory.' >&2; exit 2; }
[[ "$(stat -c '%a' "$env_file")" == 600 ]] || { echo 'V2 runtime configuration must be a protected mode-0600 file.' >&2; exit 2; }
release_dir="$root/releases/$sha"
[[ -d "$release_dir" && -f "$release_dir/RELEASE_COMMIT" && "$(cat "$release_dir/RELEASE_COMMIT")" == "$sha" ]] || {
  echo 'V2 runtime env and immutable release directory differ; refusing stale current/RELEASE_COMMIT fallback.' >&2; exit 2;
}
compose=(docker compose --project-name "$compose_project" --env-file "$env_file" -f "$release_dir/deploy/staging/compose.yaml")
db_owner=ai_tourism_owner
db_name=rahgard_pilot_vps_staging
running=$("${compose[@]}" ps --status running --services)
if grep -Eq '^(api|web)$' <<<"$running"; then
  echo 'Rahgard api/web are still running; stop them before the frozen export.' >&2
  exit 2
fi
db_container=$("${compose[@]}" ps -a -q db)
[[ "$db_container" =~ ^[0-9a-f]{64}$ ]] || { echo 'Cannot identify exactly one V2 PostgreSQL container.' >&2; exit 2; }
db_identity=$(docker inspect --format '{{.Config.Image}}|{{.Image}}|{{.State.Health.Status}}|{{.State.Running}}' "$db_container")
IFS='|' read -r db_config_image db_image_id db_health db_running <<<"$db_identity"
[[ "$db_config_image" == 'rahgard-postgres:17-postgis36-vector087' && "$db_image_id" =~ ^sha256:[0-9a-f]{64}$ && "$db_health" == healthy && "$db_running" == true ]] || {
  echo 'PostgreSQL runtime image/health/running identity mismatch.' >&2; exit 2;
}
mounts=$(docker inspect --format '{{json .Mounts}}' "$db_container")
if ! RAHGARD_PORTABLE_MOUNTS_JSON="$mounts" python3 - "$expected_volume" <<'PY'
import json, os, sys
mounts = json.loads(os.environ["RAHGARD_PORTABLE_MOUNTS_JSON"])
matches = [m for m in mounts if m.get("Destination") == "/var/lib/postgresql/data"]
raise SystemExit(0 if len(matches) == 1 and matches[0].get("Type") == "volume" and matches[0].get("Name") == sys.argv[1] else 1)
PY
then echo 'Persistent PostgreSQL volume identity mismatch.' >&2; exit 2; fi
writers=$("${compose[@]}" exec -T db psql -X -q -A -t -U "$db_owner" -d "$db_name" \
  -c "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()")
[[ "$writers" == 0 ]] || {
  echo "Database still has $writers other sessions; ensure all writers/readers are drained before export." >&2; exit 2;
}
db_marker=$("${compose[@]}" exec -T db psql -X -q -A -t -U "$db_owner" -d "$db_name" \
  -c "SELECT marker_value FROM public.rahgard_private_pilot_marker LIMIT 1")
host_marker=$(cat "$root/state/database-marker")
[[ "$db_marker" =~ ^[a-fA-F0-9]{48}$ && "$db_marker" == "$host_marker" ]] || {
  echo 'Protected database marker differs from host state.' >&2; exit 2;
}
db_bytes=$("${compose[@]}" exec -T db psql -X -q -A -t -U "$db_owner" -d "$db_name" \
  -c 'SELECT pg_database_size(current_database())')
image_bytes=0
for image in "rahgard-api:$sha" "rahgard-web:$sha" rahgard-postgres:17-postgis36-vector087; do
  size=$(docker image inspect --format '{{.Size}}' "$image")
  [[ "$size" =~ ^[0-9]+$ ]] || { echo "Could not measure pinned image size: $image" >&2; exit 2; }
  image_bytes=$((image_bytes + size))
done
payload_bytes=$(du -sb -- "$root/state" "$root/releases/$sha" | awk '{total += $1} END {print total+0}')
[[ "$db_bytes" =~ ^[0-9]+$ && "$payload_bytes" =~ ^[0-9]+$ ]] || { echo 'Could not measure backup payload size.' >&2; exit 2; }
# The encrypted output and source work files coexist until verification. Reserve
# two full payload estimates plus 1 GiB for compression/temporary overhead.
required_bytes=$(((db_bytes + image_bytes + payload_bytes) * 2 + 1073741824))
available_kb=$(df -Pk "$root/backups" | awk 'NR==2 {print $4}')
[[ "$available_kb" =~ ^[0-9]+$ ]] && (( available_kb * 1024 >= required_bytes )) || {
  echo 'Insufficient free space for temporary plus encrypted portable bundle; no backup started.' >&2; exit 2;
}

stamp=$(date -u +%Y%m%dT%H%M%SZ)
tmp=$(mktemp -d "$root/backups/.portable-$stamp.XXXXXX")
nonce=${tmp##*.}
out="$root/backups/rahgard-portable-$stamp-$sha-$nonce.tar.enc"
success=false
cleanup() {
  rm -rf -- "$tmp"
  if [[ "$success" != true ]]; then rm -f -- "$out" "$out.hmac" "$out.sha256"; fi
}
trap cleanup EXIT
mkdir -m 0700 "$tmp/private" "$tmp/private/secrets"
cp -- "$env_file" "$tmp/private/host.env"
cp -a -- "$root/state" "$tmp/private/state"
cp -a -- "$release_dir" "$tmp/release"
cp -- "$freeze_marker" "$tmp/private/state/WRITE_FREEZE"

# Verify the exact V2 image tags after stopping the API/Web containers. The
# source revision labels, image IDs, OS and architecture must match the
# immutable release SHA; a stale legacy marker is never used to name images.
api_image="rahgard-api:$sha"
web_image="rahgard-web:$sha"
db_image='rahgard-postgres:17-postgis36-vector087'
identity_file="$tmp/runtime-image-identities.tsv"
for image in "$api_image" "$web_image" "$db_image"; do
  row=$(docker image inspect --format '{{.Id}}|{{.Os}}|{{.Architecture}}|{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image")
  IFS='|' read -r image_id image_os image_arch image_revision <<<"$row"
  expected_revision="$sha"
  if [[ "$image" == "$db_image" ]]; then expected_revision=external-db-image; image_revision=$expected_revision; fi
  [[ "$image_id" =~ ^sha256:[0-9a-f]{64}$ && "$image_os" == linux && "$image_arch" == amd64 && "$image_revision" == "$expected_revision" ]] || {
    echo "Pinned image identity mismatch for $image; refusing portability export." >&2; exit 2;
  }
  printf '%s|%s|%s|%s|%s\n' "$image" "$image_id" "$image_os" "$image_arch" "$image_revision" >> "$identity_file"
done
docker save --output "$tmp/runtime-images.tar" "$api_image" "$web_image" "$db_image"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
python3 "$script_dir/verify-portable-images.py" "$tmp/runtime-images.tar" "$identity_file" "$sha"
mv "$identity_file" "$tmp/runtime-image-identities.tsv"

# Only operational secrets required by the current Compose contract are copied.
# Backup and portable-integrity keys are deliberately excluded.
required_secrets=(pg_owner_password app_db_password geo_authorizer_password geo_publisher_password auth_otp_hmac_secret auth_csrf_secret auth_rate_limit_secret internal_chat_token sms_ir_production_api_key)
api_container=$("${compose[@]}" ps -a -q api)
web_container=$("${compose[@]}" ps -a -q web)
[[ "$api_container" =~ ^[0-9a-f]{64}$ && "$web_container" =~ ^[0-9a-f]{64}$ ]] || { echo 'Stopped V2 API/Web container identity missing.' >&2; exit 2; }
api_container_identity=$(docker inspect --format '{{.Config.Image}}|{{.Image}}' "$api_container")
web_container_identity=$(docker inspect --format '{{.Config.Image}}|{{.Image}}' "$web_container")
api_image_id=$(docker image inspect --format '{{.Id}}' "$api_image")
web_image_id=$(docker image inspect --format '{{.Id}}' "$web_image")
[[ "$api_container_identity" == "$api_image|$api_image_id" && "$web_container_identity" == "$web_image|$web_image_id" ]] || {
  echo 'Stopped V2 containers do not match the pinned API/Web images.' >&2; exit 2;
}
if ! docker inspect "$api_container" | python3 -c '
import json,sys
containers=json.load(sys.stdin)
if len(containers)!=1: raise SystemExit(1)
values={}
entries=containers[0]["Config"].get("Env",[])
for entry in entries:
    if "=" in entry:
        key,value=entry.split("=",1); values.setdefault(key,[]).append(value)
expected={"APP_ENV":"staging","STAGING_PUBLIC_HOST":"hinaa.ir","AUTH_ALLOWED_ORIGINS":"https://hinaa.ir","AUTH_COOKIE_SECURE":"true","AUTH_LOCAL_OWNER_ENABLED":"false","AUTH_SMS_ADAPTER":"disabled","AI_PROVIDER_ADMIN_ENABLED":"false","TOURISM_RAG_ENABLED":"false"}
if any(values.get(k)!=[v] for k,v in expected.items()): raise SystemExit(1)
flags=tuple(sum(entry.startswith(k+"=") for entry in entries) for k in ("PLATFORM_ADMIN_MFA_ENCRYPTION_KEY_FILE","PLATFORM_ADMIN_RECOVERY_PEPPER_FILE"))
if flags not in {(0,0),(1,1)}: raise SystemExit(1)
if flags==(1,1) and (values.get("PLATFORM_ADMIN_MFA_ENCRYPTION_KEY_FILE") != ["/run/secrets/platform_admin_mfa_encryption_key_hex"] or values.get("PLATFORM_ADMIN_RECOVERY_PEPPER_FILE") != ["/run/secrets/platform_admin_recovery_pepper"]): raise SystemExit(1)
print("mfa_enabled" if flags==(1,1) else "mfa_disabled")
' > "$tmp/platform-mfa-status.txt"; then
  echo 'Active V2 API host/auth/security settings do not match the canonical hardened contract.' >&2; exit 2
fi
if [[ "$(cat "$tmp/platform-mfa-status.txt")" == mfa_enabled ]]; then
  required_secrets+=(platform_admin_mfa_encryption_key_hex platform_admin_recovery_pepper)
fi
cp -- "$tmp/platform-mfa-status.txt" "$tmp/private/state/platform-mfa-status"
if docker ps --format '{{.Image}}' | grep -q '^rahgard-api:'; then
  echo 'A Rahgard API writer remains running during portability export.' >&2; exit 2
fi
for name in "${required_secrets[@]}"; do
  file="$secret_dir/$name"
  if [[ "$name" == sms_ir_production_api_key ]]; then
    [[ -f "$file" && ! -L "$file" && "$(stat -c '%a' "$file")" == 600 ]] || {
      echo "Compose runtime placeholder/secret is missing or unsafe: $name" >&2; exit 2;
    }
  else
    [[ -f "$file" && ! -L "$file" && -s "$file" && "$(stat -c '%a' "$file")" == 600 ]] || {
      echo "Required runtime secret is missing or unsafe: $name" >&2; exit 2;
    }
  fi
done
for path in "$root/state" "$release_dir"; do
  if find "$path" -type l -print -quit | grep -q .; then
    echo "Symlink found in portability payload; refusing ambiguous traversal: $path" >&2; exit 2
  fi
done

for name in "${required_secrets[@]}"; do
  install -m 0600 -- "$secret_dir/$name" "$tmp/private/secrets/$name"
done

"${compose[@]}" exec -T db pg_dump -U "$db_owner" -d "$db_name" -Fc > "$tmp/database.dump"
test -s "$tmp/database.dump"
"${compose[@]}" exec -T db pg_restore --list < "$tmp/database.dump" >/dev/null
"${compose[@]}" exec -T db psql -X -q -A -t -U "$db_owner" -d "$db_name" \
  -c "SELECT migration_id||'|'||rtrim(sha256) FROM system.schema_migrations ORDER BY migration_id" \
  > "$tmp/database.migration-ledger.tsv"
test -s "$tmp/database.migration-ledger.tsv"
counts_sql=$(cat <<'SQL'
SELECT 'identity.users', count(*) FROM identity.users UNION ALL
SELECT 'conversation.conversations', count(*) FROM conversation.conversations UNION ALL
SELECT 'conversation.messages', count(*) FROM conversation.messages UNION ALL
SELECT 'travel.trips', count(*) FROM travel.trips UNION ALL
SELECT 'travel.itineraries', count(*) FROM travel.itineraries UNION ALL
SELECT 'travel.itinerary_stops', count(*) FROM travel.itinerary_stops UNION ALL
SELECT 'knowledge.production_destinations', count(*) FROM knowledge.production_destinations
ORDER BY 1
SQL
)
"${compose[@]}" exec -T db psql -X -q -A -t -F '|' -U "$db_owner" -d "$db_name" \
  -c "$counts_sql" > "$tmp/database.critical-counts.tsv"
(
  cd "$tmp"
  find private release -type f -print0 | sort -z | xargs -0 sha256sum
  sha256sum database.dump database.migration-ledger.tsv database.critical-counts.tsv runtime-images.tar runtime-image-identities.tsv
) > "$tmp/MANIFEST.sha256"
(
  cd "$tmp"
  tar -cf - MANIFEST.sha256 database.dump database.migration-ledger.tsv database.critical-counts.tsv runtime-images.tar runtime-image-identities.tsv private release
) | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 600000 \
  -pass file:"$root/secrets/backup_encryption_passphrase" -out "$out"
test -s "$out"

# Encrypt-then-MAC: HMAC is checked before decryption. The integrity key is
# independent of the encryption key and is never included in this bundle.
python3 - "$root/secrets/portable_bundle_hmac_key" "$out" "$out.hmac" <<'PY'
import hashlib, hmac, os, sys
key_path, bundle_path, mac_path = sys.argv[1:]
with open(key_path, "rb") as f:
    key = f.read()
if len(key) < 32:
    raise SystemExit("Portable HMAC key must contain at least 32 random bytes.")
mac = hmac.new(key, digestmod=hashlib.sha256)
with open(bundle_path, "rb") as f:
    for block in iter(lambda: f.read(1024 * 1024), b""):
        mac.update(block)
with open(mac_path, "x", encoding="ascii") as f:
    f.write(mac.hexdigest() + "  " + os.path.basename(bundle_path) + "\n")
PY
(
  cd "$root/backups"
  sha256sum "${out##*/}" > "${out##*/}.sha256"
)
chmod 0600 "$out" "$out.hmac" "$out.sha256"

# Verify the completed encrypted bundle before reporting success. Decryption
# and the authenticated manifest stay inside the protected temporary folder.
(
  cd -- "$root/backups"
  sha256sum --check -- "${out##*/}.sha256" >/dev/null
)
python3 - "$root/secrets/portable_bundle_hmac_key" "$out" "$out.hmac" <<'PY'
import hashlib, hmac, os, re, sys
key_path, bundle_path, mac_path = sys.argv[1:]
with open(key_path, "rb") as f:
    key = f.read()
with open(mac_path, "r", encoding="ascii") as f:
    line = f.read(257)
m = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)\n", line)
if not m or m.group(2) != os.path.basename(bundle_path):
    raise SystemExit("Generated HMAC sidecar failed structural validation.")
mac = hmac.new(key, digestmod=hashlib.sha256)
with open(bundle_path, "rb") as f:
    for block in iter(lambda: f.read(1024 * 1024), b""):
        mac.update(block)
if not hmac.compare_digest(mac.hexdigest(), m.group(1)):
    raise SystemExit("Generated portable bundle failed HMAC verification.")
PY
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -pass file:"$root/secrets/backup_encryption_passphrase" -in "$out" -out "$tmp/verify.tar"
tar -tf "$tmp/verify.tar" >/dev/null
tar -xf "$tmp/verify.tar" -C "$tmp/private"
(
  cd "$tmp/private"
  sha256sum --check MANIFEST.sha256 >/dev/null
  pg_restore --list database.dump >/dev/null
)
success=true
printf 'Authenticated portability bundle: %s\n' "$out"
printf 'Transfer .tar.enc, .hmac, and .sha256 off-host. Independently transfer the encryption passphrase and HMAC key; neither is in the bundle.\n'
printf 'Snapshot is marked write-frozen. External DNS/TLS, vLLM, and RAG are NOT included.\n'
