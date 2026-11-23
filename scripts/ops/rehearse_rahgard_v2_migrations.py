"""Verify and migrate a Rahgard encrypted backup in a new networkless PG17 container."""

import argparse
import hashlib
import hmac
import json
import secrets
import subprocess
import time
from pathlib import Path

from check_rahgard_v2_ledger import BASE_NUMBERS, check, migration_blobs

PG_IMAGE = "sha256:a30c041297b2306a8bb79cc6ed737f16bfca3078a3024324bb8115b302e83535"
DATABASE = "rahgard_pilot_vps_staging"
OWNER = "ai_tourism_owner"
COUNT_TABLES = (
    "identity.users", "identity.web_sessions", "conversation.conversations", "conversation.messages",
    "travel.trips", "travel.itineraries", "travel.itinerary_stops", "travel.provisional_itineraries",
    "partner.organizations", "partner.memberships", "partner.services", "partner.offers",
    "partner.prices", "partner.schedules", "partner.availability_snapshots",
    "knowledge.destinations", "knowledge.knowledge_sources", "knowledge.destination_sources",
    "knowledge.knowledge_documents", "knowledge.knowledge_chunks", "knowledge.production_destinations",
    "knowledge.destination_candidates", "knowledge.catalogue_publication_events",
)


def run(*args: str, data: bytes | None = None) -> bytes:
    completed = subprocess.run(args, input=data, capture_output=True, timeout=120, check=False)
    if completed.returncode:
        raise RuntimeError(f"{args[0:2]} exited {completed.returncode}")
    return completed.stdout


def decrypt(args: argparse.Namespace) -> tuple[bytes, str]:
    path = args.backup.resolve(strict=True)
    encrypted = path.read_bytes()
    digest = hashlib.sha256(encrypted).hexdigest()
    if path.with_name(path.name + ".sha256").read_text("ascii").split() != [digest, path.name]:
        raise ValueError("Encrypted archive checksum mismatch")
    key_root = args.key_dir.resolve(strict=True)
    key = (key_root / (path.name + ".hmac-key")).read_bytes()
    if len(key) != 32:
        raise ValueError("Invalid archive integrity key")
    sidecar = path.with_name(path.name + ".hmac").read_text("ascii").split()
    if len(sidecar) != 2 or sidecar[1] != path.name or not hmac.compare_digest(
        sidecar[0], hmac.digest(key, encrypted, "sha256").hex()
    ):
        raise ValueError("Encrypted archive authentication failed")
    password = key_root / (path.name + ".passphrase")
    plain = run(
        args.openssl, "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "600000",
        "-pass", f"file:{password}", data=encrypted,
    )
    if not plain.startswith(b"PGDMP"):
        raise ValueError("Expected a custom-format PostgreSQL archive")
    return plain, digest


def sql(container: str, statement: str, user: str = OWNER) -> str:
    return run(
        "docker", "exec", container, "psql", "-XqAt", "-F", "|", "-v", "ON_ERROR_STOP=1",
        "-h", "127.0.0.1", "-U", user, "-d", DATABASE, "-c", statement,
    ).decode().strip()


def counts(container: str) -> dict[str, int]:
    statement = " UNION ALL ".join(f"SELECT '{table}', count(*) FROM {table}" for table in COUNT_TABLES)
    output = sql(container, "BEGIN READ ONLY; " + statement + "; COMMIT;")
    return {table: int(count) for table, count in (row.split("|") for row in output.splitlines())}


def ledger(container: str) -> list[str]:
    return sql(
        container,
        "BEGIN READ ONLY; SELECT migration_id, rtrim(sha256) FROM system.schema_migrations "
        "ORDER BY migration_id; COMMIT;",
    ).splitlines()


def account_fingerprints(container: str) -> str:
    # Return these only to the rehearsal process for comparison. The report
    # carries a boolean and never includes a credential/verifier or row hash.
    return sql(container, """
        BEGIN READ ONLY;
        SELECT md5(coalesce(jsonb_agg(to_jsonb(u) ORDER BY user_id)::text, '')) FROM identity.users u
        UNION ALL
        SELECT md5(coalesce(jsonb_agg(to_jsonb(c) ORDER BY user_id)::text, ''))
        FROM identity.staging_password_credentials c;
        COMMIT;
    """)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def check_api(db_container: str, image: str, label: str, expected_count: int) -> dict:
    image_state = json.loads(run("docker", "image", "inspect", image))[0]
    require(image_state["Os"] == "linux" and image_state["Architecture"] == "amd64", "Wrong API platform")
    name = f"rahgard-v2-restore-api-{label}"
    environment = {
        "APP_ENV": "test", "DATABASE_HOST": "127.0.0.1", "DATABASE_PORT": "5432",
        "DATABASE_NAME": DATABASE, "DATABASE_USER": "ai_tourism_app", "DATABASE_PASSWORD": label,
        "AUTH_ENABLED": "false", "AUTH_LOCAL_OWNER_ENABLED": "false", "STAGING_AUTH_ENABLED": "false",
        "AUTH_SMS_ADAPTER": "disabled", "INTERNAL_CHAT_ENABLED": "false", "TOURISM_RAG_ENABLED": "false",
        "AI_PROVIDER_ADMIN_ENABLED": "false",
    }
    flags = [arg for key, value in environment.items() for arg in ("-e", f"{key}={value}")]
    api = run(
        "docker", "run", "-d", "--name", name, "--network", f"container:{db_container}",
        "--label", f"rahgard.v2.restore={label}", "--read-only", "--tmpfs", "/tmp",
        "--security-opt", "no-new-privileges", "--cap-drop", "ALL",
        *flags, "--entrypoint", "python", image_state["Id"], "-m", "uvicorn",
        "app.main:app", "--host", "127.0.0.1", "--port", "8000",
    ).decode().strip()
    try:
        probe = (
            "import json,urllib.request; base='http://127.0.0.1:8000';"
            "urllib.request.urlopen(base+'/health/ready',timeout=2).close();"
            "body=json.load(urllib.request.urlopen(base+'/api/v1/catalog/destinations',timeout=2));"
            "print(body['count'])"
        )
        for _ in range(30):
            try:
                count = int(run("docker", "exec", api, "python", "-c", probe).decode().strip())
            except RuntimeError:
                time.sleep(1)
            else:
                require(count == expected_count, "API catalogue count differs from the restored database")
                return {"image_id": image_state["Id"], "health": "ready", "catalogue_count": count}
        raise RuntimeError("API readiness and catalogue checks did not succeed on the migrated clone")
    finally:
        state = json.loads(run("docker", "inspect", api))[0]
        require(state["Config"]["Labels"].get("rahgard.v2.restore") == label, "API cleanup identity mismatch")
        run("docker", "rm", "-f", api)


def rehearse(args: argparse.Namespace) -> dict:
    manifest = json.loads(args.baseline.read_text(encoding="utf-8"))
    expected = check(manifest, args.source_sha)
    migration_rows = manifest["vps"]["database"]["migration_ledger"]
    base = [f'{row["migration_id"]}|{row["sha256"]}' for row in migration_rows]
    blobs = migration_blobs(args.source_sha)
    archive, digest = decrypt(args)
    run("docker", "image", "inspect", PG_IMAGE)
    label = secrets.token_hex(10)
    container = run(
        "docker", "run", "--detach", "--name", f"rahgard-v2-restore-{label}", "--network", "none",
        "--label", f"rahgard.v2.restore={label}", "--tmpfs", "/var/lib/postgresql/data:rw,size=1g",
        "--add-host", "api:127.0.0.1",
        "-e", f"POSTGRES_USER={OWNER}", "-e", f"POSTGRES_DB={DATABASE}",
        "-e", "POSTGRES_HOST_AUTH_METHOD=trust", PG_IMAGE,
    ).decode().strip()
    try:
        state = json.loads(run("docker", "inspect", container))[0]
        host = state["HostConfig"]
        require(
            host["NetworkMode"] == "none" and not host["PortBindings"]
            and not host["Binds"] and not host.get("Mounts")
            and "/var/lib/postgresql/data" in host["Tmpfs"]
            and all(mount["Type"] == "tmpfs" for mount in state["Mounts"]),
            "Restore container is not isolated",
        )
        for _ in range(60):
            try:
                if sql(container, "SELECT current_setting('server_version_num')::int / 10000 = 17") == "t":
                    break
            except RuntimeError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Disposable PostgreSQL 17 did not become ready")
        run("docker", "exec", "-i", container, "pg_restore", "--list", data=archive)
        sql(
            container,
            "CREATE ROLE ai_tourism_app LOGIN NOSUPERUSER NOBYPASSRLS;"
            "CREATE ROLE rahgard_pilot_geo_executor NOLOGIN NOSUPERUSER NOBYPASSRLS;"
            "CREATE ROLE rahgard_pilot_geo_migrator NOLOGIN NOSUPERUSER NOBYPASSRLS;"
            "GRANT rahgard_pilot_geo_executor TO rahgard_pilot_geo_migrator;",
        )
        run(
            "docker", "exec", "-i", container, "pg_restore", "-U", OWNER, "-d", DATABASE,
            "--single-transaction", "--exit-on-error", data=archive,
        )
        require(len(base) == len(BASE_NUMBERS) and ledger(container) == base, "Restore ledger differs from observed VPS")
        before = counts(container)
        accounts_before = account_fingerprints(container)
        live = manifest["vps"]["database"]["aggregate_counts"]
        for table, field in (
            ("identity.users", "users"), ("identity.web_sessions", "sessions"), ("travel.trips", "trips"),
            ("conversation.conversations", "conversations"), ("travel.itineraries", "itineraries"),
            ("partner.organizations", "organizations"), ("knowledge.production_destinations", "published_destinations"),
        ):
            require(before[table] == live[field], f"Restored count differs from observed VPS for {table}")
        started = time.monotonic()
        prior_hash = migration_rows[-1]["sha256"]
        elapsed = {}
        for position, number in enumerate((22, 23)):
            identity, source = blobs[number]
            item = expected["pending"][position]
            require(identity == item["id"], "Migration identity mismatch")
            current_hash = item["sha256"]
            cmd = """
marker=$(psql -XqAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'SELECT marker_value FROM public.rahgard_private_pilot_marker')
export RAHGARD_PILOT_DATABASE_MARKER="$marker"
exec psql -Xq -v ON_ERROR_STOP=1 -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"
"""
            phase_start = time.monotonic()
            run(
                "docker", "exec", "-i",
                "-e", f"RAHGARD_PILOT_MIGRATION_{number - 1:04d}_SHA256={prior_hash}",
                "-e", f"RAHGARD_PILOT_MIGRATION_{number:04d}_SHA256={current_hash}",
                container, "sh", "-ec", cmd, data=source,
            )
            elapsed[identity] = round(time.monotonic() - phase_start, 3)
            base.append(f"{identity}|{current_hash}")
            require(ledger(container) == base, f"Ledger differs after {identity}")
            prior_hash = current_hash
        after = counts(container)
        require(after == before, "Existing row counts changed during migration")
        require(account_fingerprints(container) == accounts_before, "Existing account or credential data drift")
        require(sql(container, """
            SELECT
              (SELECT NOT rolsuper AND NOT rolbypassrls FROM pg_roles WHERE rolname='ai_tourism_app')
              AND (SELECT count(*)=4 AND bool_and(relrowsecurity) FROM pg_class WHERE oid IN (
                'partner.traveler_request_shares'::regclass, 'partner.traveler_request_revisions'::regclass,
                'partner.traveler_request_inbox'::regclass, 'partner.trip_company_responses'::regclass))
              AND NOT has_table_privilege('ai_tourism_app', 'partner.traveler_request_revisions', 'INSERT')
              AND NOT has_table_privilege('ai_tourism_app', 'partner.traveler_request_inbox', 'INSERT')
              AND NOT has_column_privilege('ai_tourism_app', 'partner.organizations', 'is_test', 'INSERT')
              AND NOT has_column_privilege('ai_tourism_app', 'partner.organizations', 'is_test', 'UPDATE');
        """) == "t", "Unexpected app grants or missing RLS")
        require(sql(container, """
            SELECT (SELECT count(*) FROM partner.traveler_request_shares)
              + (SELECT count(*) FROM partner.traveler_request_revisions)
              + (SELECT count(*) FROM partner.traveler_request_inbox)
              + (SELECT count(*) FROM partner.trip_company_responses)
        """) == "0", "Migration created unexpected shares or responses")
        api_checks = {}
        for image in args.runtime_image:
            api_checks[image] = check_api(container, image, label, before["knowledge.production_destinations"])
            require(counts(container) == after, "API compatibility check changed restored row counts")
        apex_auth = None
        if args.apex_auth_images:
            from test_rahgard_apex_auth import test_apex_auth

            apex_auth = test_apex_auth(container, *args.apex_auth_images, args.openssl)
        return {
            "backup": args.backup.name, "backup_sha256": digest, "checksum_hmac_and_archive": "passed",
            "tested_source_sha": args.source_sha, "postgresql_image_id": PG_IMAGE,
            "before_migration_count": len(BASE_NUMBERS), "after_migration_count": len(base),
            "after_ledger": base, "migration_seconds": elapsed,
            "counts_before": before, "counts_after": after, "new_share_response_rows": 0,
            "existing_account_and_credential_contents_preserved": True,
            "rls_and_app_grants": "passed", "isolation": "network none, no published ports, tmpfs data",
            "runtime_image_checks": api_checks,
            "isolated_apex_auth": apex_auth,
            "migration_and_checks_seconds": round(time.monotonic() - started, 3),
        }
    finally:
        actual = json.loads(run("docker", "inspect", container))[0]
        require(actual["Config"]["Labels"].get("rahgard.v2.restore") == label, "Refusing cleanup outside owned test container")
        run("docker", "rm", "-f", container)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("source_sha")
    parser.add_argument("backup", type=Path)
    parser.add_argument("key_dir", type=Path)
    parser.add_argument("--openssl", default="openssl")
    parser.add_argument("--runtime-image", action="append", default=[], help="Local API image for isolated smoke")
    parser.add_argument("--apex-auth-images", nargs=3, metavar=("LEGACY_API", "V2_API", "V2_WEB"))
    args = parser.parse_args()
    try:
        print(json.dumps(rehearse(args), indent=2))
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        parser.exit(2, f"BLOCKED: {error}\n")


if __name__ == "__main__":
    main()
