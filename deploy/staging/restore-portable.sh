#!/usr/bin/env bash
# Restore a cryptographically re-authenticated archive into a disposable target only.
set -Eeuo pipefail
umask 077
bundle="${1:-}"
passphrase_file="${2:-}"
hmac_key_file="${3:-}"
bundle_dir="${4:-}"
target_container="${5:-}"
target_db="${6:-}"
db_owner="${7:-}"
confirmation="${8:-}"
usage='Usage: restore-portable.sh <bundle.tar.enc> <passphrase-file> <independent-hmac-key-file> <verified-extraction-dir> <isolated-pg-container> <rahgard_restore_dbname> <existing-db-owner-role> <exact-dbname-confirmation>'
[[ -f "$bundle" && ! -L "$bundle" && -f "$bundle.hmac" && ! -L "$bundle.hmac" \
   && -f "$bundle.sha256" && ! -L "$bundle.sha256" \
   && -f "$passphrase_file" && ! -L "$passphrase_file" && -s "$passphrase_file" \
   && -f "$hmac_key_file" && ! -L "$hmac_key_file" && -s "$hmac_key_file" \
   && -d "$bundle_dir" && ! -L "$bundle_dir" && -n "$target_container" ]] || {
  echo "$usage" >&2; exit 2;
}
[[ "$target_container" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ ]] || { echo 'Invalid target container name/ID.' >&2; exit 2; }
[[ "$target_db" =~ ^rahgard_restore_[A-Za-z0-9_]{1,45}$ ]] || { echo 'Target DB must be a new isolated rahgard_restore_* database.' >&2; exit 2; }
[[ "$confirmation" == "$target_db" ]] || { echo 'Exact target DB confirmation does not match.' >&2; exit 2; }
[[ "$db_owner" =~ ^[A-Za-z_][A-Za-z0-9_]{0,62}$ ]] || { echo 'Invalid database owner role.' >&2; exit 2; }
[[ "$db_owner" == ai_tourism_owner ]] || { echo 'Restore target must use the deployment bootstrap owner role ai_tourism_owner.' >&2; exit 2; }
bundle=$(realpath -e -- "$bundle")
passphrase_file=$(realpath -e -- "$passphrase_file")
hmac_key_file=$(realpath -e -- "$hmac_key_file")
bundle_dir=$(realpath -e -- "$bundle_dir")

work=$(mktemp -d "${TMPDIR:-/tmp}/rahgard-portable-restore.XXXXXX")
chmod 0700 "$work"
cleanup() { rm -rf -- "$work"; }
trap cleanup EXIT
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# Re-run authenticated inspection from the encrypted input. Then compare the
# operator-provided extraction byte-for-byte with this fresh result; a loose
# SHA manifest alone is not accepted as proof of extraction provenance.
bash "$script_dir/inspect-portable.sh" "$bundle" "$passphrase_file" "$hmac_key_file" "$work/reverified"
diff -qr --no-dereference "$work/reverified" "$bundle_dir" >/dev/null || {
  echo 'Provided extraction differs from the freshly HMAC-authenticated extraction.' >&2; exit 2;
}
(
  cd -- "$work/reverified"
  sha256sum --check MANIFEST.sha256 >/dev/null
)
python3 - "$work/reverified/database.migration-ledger.tsv" <<'PY'
import re, sys
seen = set()
with open(sys.argv[1], encoding="ascii") as f:
    for line in f:
        m = re.fullmatch(r"([A-Za-z0-9_-]+)\|([0-9a-f]{64})\n?", line)
        if not m or m.group(1) in seen:
            raise SystemExit("Invalid or duplicate source migration-ledger row.")
        seen.add(m.group(1))
if not seen:
    raise SystemExit("Source migration ledger is empty.")
PY

# Require a genuinely disposable target rather than trusting the caller's name.
docker inspect "$target_container" | python3 -c '
import json,sys
x=json.load(sys.stdin)
if len(x)!=1: raise SystemExit("Expected exactly one target container.")
c=x[0]; labels=c.get("Config",{}).get("Labels") or {}
if labels.get("rahgard.restore.target")!="isolated" or labels.get("rahgard.environment") not in {"restore-test","qa","test"}:
    raise SystemExit("Target lacks required isolated restore labels.")
if c.get("State",{}).get("Running") is not True: raise SystemExit("Target container is not running.")
image=c.get("Config",{}).get("Image","")
if not (image.startswith("postgres:17") or "rahgard-postgres:17" in image):
    raise SystemExit("Target image is not PostgreSQL 17.")
mounts=c.get("Mounts") or []
host=c.get("HostConfig") or {}
tmpfs=host.get("Tmpfs") or {}
if "/var/lib/postgresql/data" not in tmpfs:
    raise SystemExit("PostgreSQL data directory is not mounted on tmpfs.")
if host.get("Binds") or host.get("Mounts"): raise SystemExit("Unexpected persistent/bind mount configuration on target container.")
if any(m.get("Type")!="tmpfs" or m.get("Destination") not in tmpfs for m in mounts): raise SystemExit("Unexpected persistent/bind mount on target container.")
ports=c.get("NetworkSettings",{}).get("Ports") or {}
if any(v for v in ports.values() if v): raise SystemExit("Target has a published host port.")
env=c.get("Config",{}).get("Env") or []
if any(e.startswith("APP_ENV=production") for e in env): raise SystemExit("Production environment is forbidden.")
'
docker exec -i "$target_container" pg_restore --list < "$work/reverified/database.dump" >/dev/null
pg_version=$(docker exec "$target_container" sh -c 'cat "${PGDATA:-/var/lib/postgresql/data}/PG_VERSION"')
[[ "$pg_version" == 17 ]] || { echo 'Target server is not PostgreSQL 17.' >&2; exit 2; }
owner_is_superuser=$(docker exec "$target_container" psql -X -q -A -t -U "$db_owner" -d postgres \
  -c "SELECT rolsuper FROM pg_roles WHERE rolname='$db_owner'")
[[ "$owner_is_superuser" == t ]] || { echo 'Target owner is not the isolated cluster bootstrap role.' >&2; exit 2; }
existing=$(docker exec "$target_container" psql -X -q -A -t -U "$db_owner" -d postgres \
  -c "SELECT COALESCE(string_agg(datname,',' ORDER BY datname),'') FROM pg_database WHERE NOT datistemplate AND datname <> 'postgres'")
[[ -z "$existing" ]] || { echo 'Target cluster contains an existing application database; refusing restore.' >&2; exit 2; }
exists=$(docker exec "$target_container" psql -X -q -A -t -U "$db_owner" -d postgres \
  -v target_db="$target_db" -c "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=:'target_db')")
[[ "$exists" == f ]] || { echo 'Target database already exists; refusing to overwrite it.' >&2; exit 2; }

# pg_dump does not contain cluster-global roles. Recreate only the minimum
# application roles from the authenticated secret payload before preserving
# the database ACLs from the dump. The existing target owner is not changed.
app_password_file="$bundle_dir/private/secrets/app_db_password"
[[ -f "$app_password_file" && ! -L "$app_password_file" && -s "$app_password_file" ]] || {
  echo 'Authenticated bundle has no app DB password; refusing a runtime-incomplete restore.' >&2; exit 2;
}
docker cp "$app_password_file" "$target_container:/tmp/rahgard-restore-app-db-password"
docker exec "$target_container" sh -ceu '
  cleanup_secret() { unset RAHGARD_RESTORE_APP_DB_PASSWORD; rm -f -- /tmp/rahgard-restore-app-db-password; }
  trap cleanup_secret EXIT HUP INT TERM
  chmod 0600 /tmp/rahgard-restore-app-db-password
  export RAHGARD_RESTORE_APP_DB_PASSWORD="$(cat /tmp/rahgard-restore-app-db-password)"
  psql -X -v ON_ERROR_STOP=1 -U "$1" -d postgres <<'"'"'SQL'"'"'
\getenv app_password RAHGARD_RESTORE_APP_DB_PASSWORD
SELECT format('CREATE ROLE ai_tourism_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ai_tourism_app')
\gexec
SELECT 'CREATE ROLE rahgard_pilot_geo_executor NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rahgard_pilot_geo_executor')
\gexec
SELECT 'CREATE ROLE rahgard_pilot_geo_migrator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rahgard_pilot_geo_migrator')
\gexec
GRANT rahgard_pilot_geo_executor TO rahgard_pilot_geo_migrator;
SQL
' _ "$db_owner"

echo "Creating new isolated database $target_db in container $target_container."
docker exec "$target_container" createdb -U "$db_owner" -O "$db_owner" "$target_db"
docker exec -i "$target_container" pg_restore -U "$db_owner" -d "$target_db" \
  --no-owner --exit-on-error --single-transaction < "$work/reverified/database.dump"
restored_ledger=$(docker exec "$target_container" psql -X -q -A -t -U "$db_owner" -d "$target_db" \
  -c "SELECT migration_id||'|'||rtrim(sha256) FROM system.schema_migrations ORDER BY migration_id")
source_ledger=$(cat "$work/reverified/database.migration-ledger.tsv")
[[ "$restored_ledger" == "$source_ledger" ]] || {
  echo 'Restored migration ledger differs from the frozen source; preserve the isolated target for review.' >&2; exit 3;
}
count=$(docker exec "$target_container" psql -X -q -A -t -U "$db_owner" -d "$target_db" \
  -c 'SELECT count(*) FROM system.schema_migrations')
[[ "$count" =~ ^[0-9]+$ && "$count" -eq $(wc -l < "$work/reverified/database.migration-ledger.tsv") ]] || {
  echo 'Restored migration count differs from the frozen source ledger.' >&2; exit 3;
}
check=$(docker exec "$target_container" psql -X -q -A -t -U "$db_owner" -d "$target_db" -c 'SELECT current_database()')
[[ "$check" == "$target_db" ]] || { echo 'Restored database identity check failed.' >&2; exit 3; }
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
restored_counts=$(docker exec "$target_container" psql -X -q -A -t -F '|' -U "$db_owner" -d "$target_db" -c "$counts_sql")
source_counts=$(cat "$work/reverified/database.critical-counts.tsv")
[[ "$restored_counts" == "$source_counts" ]] || {
  echo 'Restored critical row counts differ from the frozen source manifest; preserve the isolated target for review.' >&2; exit 3;
}
printf 'PASS: isolated PostgreSQL 17 restore complete; database=%s migrations=%s release=%s\n' \
  "$target_db" "$count" "$(cat "$work/reverified/release/RELEASE_COMMIT")"
printf 'PASS: privacy-safe critical table/view row counts match the frozen export.\n'
printf 'Application startup/health was not tested; this script did not start an app or touch the live stack.\n'
