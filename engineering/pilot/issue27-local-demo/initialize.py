"""Initialize only a brand-new Issue 27 Owner Demo PostgreSQL volume.

This intentionally supports the production-shaped runtime ledger (0000-0013,
0016-0026; migrations 0014/0015 are excluded). It never reconnects/retries a
partially initialized database. Every migration checksum is recorded from the
checked-in SQL bytes.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DATABASE = "rahgard_pilot_vps_staging"
CONTAINER = os.environ.get("RAHGARD_DEMO_DB_CONTAINER", "")
MARKER = os.environ.get("RAHGARD_PILOT_DATABASE_MARKER", "")
if not __import__("re").fullmatch(r"rahgard-issue27-[0-9a-f]{12}-db-1", CONTAINER) or len(MARKER) != 48:
    raise SystemExit("BLOCKED: local demo target identity is invalid")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def docker(args: list[str], *, data: bytes | None = None, env: dict[str, str] | None = None) -> bytes:
    result = subprocess.run(["docker", *args], input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env={**os.environ, **(env or {})})
    if result.returncode:
        raise SystemExit(f"BLOCKED: isolated database command failed ({args[0]})")
    return result.stdout


def psql(sql: bytes | str, *, tcp: bool = False, role: str = "ai_tourism_owner",
         extra_env: dict[str, str] | None = None) -> None:
    command = ["exec", "-i"]
    command.extend(["-e", f"RAHGARD_PILOT_DATABASE_MARKER={MARKER}"])
    for key, value in (extra_env or {}).items():
        command.extend(["-e", f"{key}={value}"])
    command.append(CONTAINER)
    if tcp:
        script = 'export PGPASSWORD="$(cat /run/secrets/pg_owner_password)"; exec psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
        command.extend(["sh", "-lc", script])
    else:
        command.extend(["psql", "-X", "-v", "ON_ERROR_STOP=1", "-U", role, "-d", DATABASE])
    content = sql.encode() if isinstance(sql, str) else sql
    docker(command, data=b"\\getenv marker RAHGARD_PILOT_DATABASE_MARKER\n" + content)


def scalar(sql: str) -> str:
    result = docker(["exec", CONTAINER, "psql", "-X", "-q", "-A", "-t", "-U", "ai_tourism_owner", "-d", DATABASE,
                     "-c", sql]).decode().strip()
    return result


def apply(migration_id: str, relative: str, *, prior: dict[str, str] | None = None,
          tcp: bool = False, role: str = "ai_tourism_owner", prefix: bytes = b"") -> str:
    path = ROOT / relative
    digest = sha(path)
    env = {f"RAHGARD_PILOT_MIGRATION_{key}_SHA256": value for key, value in (prior or {}).items()}
    env[f"RAHGARD_PILOT_MIGRATION_{migration_id[:4]}_SHA256"] = digest
    # SQL migration uses \getenv for the unprefixed current migration hash.
    env[f"RAHGARD_PILOT_MIGRATION_{migration_id[:4]}_SHA256"] = digest
    psql(prefix + path.read_bytes(), tcp=tcp, role=role, extra_env=env)
    stored = scalar(f"SELECT sha256 FROM system.schema_migrations WHERE migration_id='{migration_id}';")
    if stored != digest:
        raise SystemExit(f"BLOCKED: migration checksum was not recorded ({migration_id})")
    return digest


def main() -> None:
    if scalar("SELECT current_database()") != DATABASE:
        raise SystemExit("BLOCKED: database identity mismatch")
    if scalar("SELECT current_setting('server_version_num')::int BETWEEN 170000 AND 179999") != "t":
        raise SystemExit("BLOCKED: PostgreSQL is not version 17")
    if scalar("SELECT to_regclass('system.schema_migrations') IS NULL") != "t":
        raise SystemExit("BLOCKED: nonempty/unexpected schema; preserve for review")

    sql_dir = ROOT / "engineering/database-prep/sql"
    legacy = ROOT / "database/tourism_points.sql"
    bootstrap = sql_dir / "000_bootstrap.sql"
    bootstrap_prefix = b"\\getenv app_password RAHGARD_APP_DB_PASSWORD\n\\set app_user ai_tourism_app\n"
    # The secret is read inside the isolated container; it is never a Docker CLI
    # argument or host process output.
    docker(["exec", "-i", CONTAINER, "sh", "-lc",
            'export RAHGARD_APP_DB_PASSWORD="$(cat /run/secrets/app_db_password)"; exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
           data=bootstrap_prefix + bootstrap.read_bytes())
    psql(legacy.read_bytes())
    legacy_hash = sha(legacy)
    psql(f"INSERT INTO system.schema_migrations(migration_id,sha256) VALUES ('0000_legacy_tourism_points_baseline','{legacy_hash}');")

    base = [
        ("0001_core_schema", "001_core_schema.sql"),
        ("0002_synthetic_knowledge_seed", "002_synthetic_knowledge_seed.sql"),
        ("0003_synthetic_e2e_seed", "003_synthetic_e2e_seed.sql"),
        ("0004_app_role_grants", "004_app_role_grants.sql"),
        ("0005_verified_unesco_destination_seed", "005_verified_unesco_destination_seed.sql"),
        ("0006_verified_unesco_destination_seed_batch2", "006_verified_unesco_destination_seed_batch2.sql"),
        ("0007_shiraz_dalahoo_wikipedia_dataset_v1", "007_shiraz_dalahoo_wikipedia_dataset_v1.sql"),
        ("0008_authentication_foundation", "008_authentication_foundation.sql"),
        ("0009_traveler_core", "009_traveler_core.sql"),
        ("0010_task31_content_privacy_full_itinerary", "010_task31_content_privacy_full_itinerary.sql"),
        ("0011_internal_chat_turns", "011_internal_chat_turns.sql"),
        ("0012_task5_published_claim_evidence", "012_task5_published_claim_evidence.sql"),
    ]
    hashes: dict[str, str] = {}
    for mid, filename in base:
        path = sql_dir / filename
        content = path.read_bytes()
        if mid == "0004_app_role_grants":
            old = b'GRANT CONNECT ON DATABASE ai_tourism_dev TO :"app_user";'
            if content.count(old) != 1:
                raise SystemExit("BLOCKED: immutable 0004 adaptation token differs")
            content = content.replace(old, b'GRANT CONNECT ON DATABASE rahgard_pilot_vps_staging TO :"app_user";')
            content = b"\\set app_user ai_tourism_app\n" + content
        digest = sha(path)
        psql(b"\\set migration_hash " + digest.encode() + b"\n" + content)
        if scalar(f"SELECT sha256 FROM system.schema_migrations WHERE migration_id='{mid}';") != digest:
            raise SystemExit(f"BLOCKED: base migration checksum failed ({mid})")
        hashes[mid] = digest

    psql("""
CREATE TABLE public.rahgard_private_pilot_marker(marker_value text PRIMARY KEY CHECK(marker_value ~ '^[a-fA-F0-9]{48}$'));
REVOKE ALL ON public.rahgard_private_pilot_marker FROM PUBLIC;
INSERT INTO public.rahgard_private_pilot_marker(marker_value) VALUES (:'marker');
GRANT USAGE ON SCHEMA public TO ai_tourism_app;
GRANT SELECT ON public.rahgard_private_pilot_marker TO ai_tourism_app;
GRANT USAGE ON SCHEMA system TO ai_tourism_app;
GRANT SELECT ON system.schema_migrations TO ai_tourism_app;
CREATE ROLE rahgard_pilot_geo_executor NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_ddl_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT rahgard_pilot_geo_executor TO rahgard_pilot_ddl_owner;
GRANT USAGE ON SCHEMA identity,knowledge,operations,system,public TO rahgard_pilot_ddl_owner;
GRANT CREATE ON SCHEMA identity,operations TO rahgard_pilot_ddl_owner;
GRANT REFERENCES ON identity.users,identity.web_sessions TO rahgard_pilot_ddl_owner;
GRANT CREATE ON DATABASE rahgard_pilot_vps_staging TO rahgard_pilot_ddl_owner;
GRANT USAGE ON SCHEMA knowledge,operations,public TO rahgard_pilot_geo_executor;
GRANT CREATE ON SCHEMA operations TO rahgard_pilot_geo_executor;
GRANT SELECT ON knowledge.destinations,knowledge.destination_sources,knowledge.knowledge_sources,system.schema_migrations,public.rahgard_private_pilot_marker TO rahgard_pilot_ddl_owner,rahgard_pilot_geo_executor;
GRANT SELECT ON knowledge.production_destinations TO rahgard_pilot_ddl_owner;
GRANT INSERT ON system.schema_migrations TO rahgard_pilot_ddl_owner;
GRANT UPDATE(status,updated_at),REFERENCES(destination_key) ON knowledge.destinations TO rahgard_pilot_ddl_owner;
GRANT UPDATE(status,updated_at) ON knowledge.destinations TO rahgard_pilot_geo_executor;
""")

    pilot = ROOT / "engineering/pilot/sql"
    geo = pilot / "013_private_pilot_geo_audit.sql"
    h12 = hashes["0012_task5_published_claim_evidence"]
    h13 = sha(geo)
    psql(b"SET ROLE rahgard_pilot_ddl_owner;\n\\set migration_hash " + h13.encode() + b"\n" + geo.read_bytes() + b"\nRESET ROLE;",
         tcp=True, role="ai_tourism_owner", extra_env={"RAHGARD_PILOT_MIGRATION_0012_SHA256": h12})
    hashes["0013_private_pilot_geo_audit"] = h13
    # Remove temporary migration authority, preserving the dedicated roles.
    psql("REVOKE CREATE ON SCHEMA operations FROM rahgard_pilot_ddl_owner,rahgard_pilot_geo_executor; REVOKE rahgard_pilot_geo_executor FROM rahgard_pilot_ddl_owner; REVOKE INSERT ON system.schema_migrations FROM rahgard_pilot_ddl_owner; REVOKE UPDATE(status,updated_at),REFERENCES(destination_key) ON knowledge.destinations FROM rahgard_pilot_ddl_owner; REVOKE SELECT ON knowledge.destinations,knowledge.destination_sources,knowledge.knowledge_sources,system.schema_migrations,public.rahgard_private_pilot_marker FROM rahgard_pilot_ddl_owner; REVOKE USAGE ON SCHEMA knowledge,operations,system,public FROM rahgard_pilot_ddl_owner;")

    chain = [
        ("0016_staging_invitation_auth", "016_staging_invitation_auth.sql", {"0013": h13}),
        ("0017_provisional_itineraries", "017_provisional_itineraries.sql", {"0016": None}),
        ("0018_national_catalogue_ingestion", "018_national_catalogue_ingestion.sql", {"0017": None}),
        ("0019_partner_workspace", "019_partner_workspace.sql", {"0018": None}),
        ("0020_archive_candidate_publication", "020_archive_candidate_publication.sql", {"0019": None}),
        ("0021_postgis_security_definer_publication", "021_postgis_security_definer_publication.sql", {"0020": None}),
        ("0022_traveler_company_requests", "022_traveler_company_requests.sql", {"0021": None}),
        ("0023_partner_trip_responses", "023_partner_trip_responses.sql", {"0022": None}),
        ("0024_partner_review_audit_actions", "024_partner_review_audit_actions.sql", {"0023": None}),
        ("0025_owner_control_center", "025_owner_control_center.sql", {"0024": None}),
        ("0026_platform_reviewer_mfa", "026_platform_reviewer_mfa.sql", {"0024": None, "0025": None}),
    ]
    for mid, filename, deps in chain:
        path = pilot / filename
        current = mid[:4]
        prior = {key: (hashes[next(k for k in hashes if k.startswith(key))] if val is None else val)
                 for key, val in deps.items()}
        h = sha(path)
        env = {f"RAHGARD_PILOT_MIGRATION_{key}_SHA256": val for key, val in prior.items()}
        env[f"RAHGARD_PILOT_MIGRATION_{current}_SHA256"] = h
        psql(b"\\set migration_hash " + h.encode() + b"\n" + path.read_bytes(), tcp=True, extra_env=env)
        if scalar(f"SELECT sha256 FROM system.schema_migrations WHERE migration_id='{mid}';") != h:
            raise SystemExit(f"BLOCKED: migration checksum failed ({mid})")
        hashes[mid] = h

    count = scalar("SELECT count(*) FROM system.schema_migrations")
    latest = scalar("SELECT max(migration_id) FROM system.schema_migrations")
    if count != "25" or latest != "0026_platform_reviewer_mfa":
        raise SystemExit("BLOCKED: runtime migration ledger differs from expected 25-row chain")
    if scalar("SELECT count(*) FROM knowledge.production_destinations") != "0":
        raise SystemExit("BLOCKED: unexpected published destination in clean owner demo")
    print("PASS: isolated demo schema initialized; migrations=25; latest=0026; published destinations=0")


if __name__ == "__main__":
    main()
