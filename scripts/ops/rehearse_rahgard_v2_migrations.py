"""Verify and migrate a Rahgard encrypted backup in a new networkless PG17 container."""

import argparse
import hashlib
import hmac
import json
import re
import secrets
import subprocess
import time
from pathlib import Path

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from check_rahgard_v2_ledger import (
    BASE_NUMBERS, CURRENT_BASE_NUMBERS, CURRENT_TARGET_NUMBERS,
    check, check_current_snapshot, current_migration_blobs, migration_blobs,
)

PG_IMAGE = "sha256:a30c041297b2306a8bb79cc6ed737f16bfca3078a3024324bb8115b302e83535"
DATABASE = "rahgard_pilot_vps_staging"
OWNER = "ai_tourism_owner"
REPO = Path(__file__).resolve().parents[2]
COUNT_TABLES = (
    "identity.users", "identity.web_sessions", "conversation.conversations", "conversation.messages",
    "travel.trips", "travel.itineraries", "travel.itinerary_stops", "travel.provisional_itineraries",
    "partner.organizations", "partner.memberships", "partner.services", "partner.offers",
    "partner.prices", "partner.schedules", "partner.availability_snapshots",
    "knowledge.destinations", "knowledge.knowledge_sources", "knowledge.destination_sources",
    "knowledge.knowledge_documents", "knowledge.knowledge_chunks", "knowledge.production_destinations",
    "knowledge.destination_candidates", "knowledge.catalogue_publication_events",
)


def run(*args: str, data: bytes | None = None, safe_metadata_error: bool = False) -> bytes:
    completed = subprocess.run(args, input=data, capture_output=True, timeout=120, check=False)
    if completed.returncode:
        error = completed.stderr.decode("utf-8", errors="replace").lower()
        categories = (
            ("permission", ("permission denied", "not permitted")),
            ("role_or_owner", ("role \"", "must be owner", "owner of")),
            ("missing_object", ("does not exist", "undefined table", "undefined object")),
            ("duplicate_object", ("already exists", "duplicate key")),
            ("migration_guard", ("division by zero", "current transaction is aborted")),
            ("constraint_or_rls", ("violates", "row-level security", "policy")),
            ("connection", ("could not connect", "connection refused", "no route")),
        )
        category = next((name for name, needles in categories if any(n in error for n in needles)), "tool_failure")
        sqlstate = None
        for line in error.splitlines():
            match = re.search(r"\b([0-9A-Z]{5})(?::|\b)", line)
            if match:
                sqlstate = match.group(1)
                break
        token_hint = ""
        if sqlstate == "42601":
            match = re.search(r"syntax error at or near ['\"]([^'\"]{1,48})['\"]", error)
            if match:
                token_hint = f", near={match.group(1)}"
            line_match = re.search(r"\bLINE ([0-9]+):", error)
            if line_match:
                token_hint += f", sql_line={line_match.group(1)}"
            if any("RAHGARD_PILOT_MIGRATION_" in arg for arg in args):
                diagnostic = next((line.strip() for line in completed.stderr.decode("utf-8", errors="replace").splitlines()
                                   if line.strip().startswith("LINE ")), "")
                diagnostic = re.sub(r"[0-9a-fA-F]{32,}", "[redacted]", diagnostic)[:180]
                if diagnostic:
                    token_hint += f", context={diagnostic}"
        # Never echo raw database/client stderr: COPY and constraint failures
        # can contain traveler or account values. Return only a safe category.
        if args[0:2] == ("docker", "exec"):
            operation = "pg_restore" if "pg_restore" in args else "migration SQL" if data and b"system.schema_migrations" in data else "isolated PostgreSQL query"
        else:
            operation = args[0]
        identifier_hint = ""
        if sqlstate == "42703":
            missing = re.search(r"column ([a-z_][a-z_0-9.]*) does not exist", error)
            if missing:
                identifier_hint = f", missing_column={missing.group(1)}"
        suffix = f", sqlstate={sqlstate}{token_hint}{identifier_hint}" if sqlstate else ""
        context = ""
        if safe_metadata_error:
            # These specific pg_catalog queries return no application rows and
            # only read schema metadata; include a bounded ERROR summary to
            # diagnose PostgreSQL-version differences without dumping stderr.
            first_error = next((line.strip() for line in completed.stderr.decode("utf-8", errors="replace").splitlines()
                                if line.lstrip().startswith(("ERROR:", "FATAL:"))), "")
            first_error = re.sub(r"'[^']*'|\"[^\"]*\"", "[identifier]", first_error)
            first_error = re.sub(r"[0-9a-fA-F]{16,}", "[redacted]", first_error)[:120]
            if first_error:
                context = f", context={first_error}"
        raise RuntimeError(f"{operation} exited {completed.returncode} ({category}{suffix}{context})")
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
    # The backup writer deliberately sends 32 random binary bytes to OpenSSL
    # through an inherited pipe. Its separately protected sidecar stores the
    # ASCII hex encoding. OpenSSL's `-pass file:` interface cannot represent
    # arbitrary binary passphrases on Windows, so derive the exact OpenSSL enc
    # key/IV here instead of converting the passphrase or weakening the format.
    encoded_password = (key_root / (path.name + ".passphrase")).read_bytes().strip()
    try:
        password_bytes = bytes.fromhex(encoded_password.decode("ascii"))
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("Invalid encrypted archive passphrase encoding") from error
    if len(password_bytes) != 32 or not encrypted.startswith(b"Salted__") or len(encrypted) < 32:
        raise ValueError("Invalid encrypted archive envelope")
    salt = encrypted[8:16]
    material = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=48, salt=salt, iterations=600_000
    ).derive(password_bytes)
    decryptor = Cipher(algorithms.AES(material[:32]), modes.CBC(material[32:])).decryptor()
    padded = decryptor.update(encrypted[16:]) + decryptor.finalize()
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    try:
        plain = unpadder.update(padded) + unpadder.finalize()
    except ValueError as error:
        raise ValueError("Encrypted archive decryption failed") from error
    if not plain.startswith(b"PGDMP"):
        raise ValueError("Expected a custom-format PostgreSQL archive")
    return plain, digest


def sql(container: str, statement: str, user: str = OWNER, *, safe_metadata_error: bool = False) -> str:
    return run(
        "docker", "exec", container, "psql", "-XqAt", "-F", "|", "-v", "ON_ERROR_STOP=1",
        "-h", "127.0.0.1", "-U", user, "-d", DATABASE, "-c", statement,
        safe_metadata_error=safe_metadata_error,
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


def catalog_security_snapshot(container: str) -> dict[str, list[str]]:
    def rows(name: str, query: str) -> list[str]:
        try:
            return sql(container, "BEGIN READ ONLY; " + query + "; COMMIT;", safe_metadata_error=True).splitlines()
        except RuntimeError as error:
            # Identify the metadata category without leaking raw PostgreSQL
            # stderr or any row content into operator output.
            raise RuntimeError(f"catalog security snapshot query failed: {name} ({error})") from None

    return {
        "indexes": rows("indexes", """SELECT n.nspname||'.'||t.relname||'|'||i.relname
          FROM pg_index x JOIN pg_class t ON t.oid=x.indrelid
          JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_namespace n ON n.oid=t.relnamespace
          WHERE n.nspname NOT IN ('pg_catalog','information_schema') ORDER BY 1"""),
        "constraints": rows("constraints", """SELECT n.nspname||'.'||t.relname||'|'||c.conname||'|'||c.contype::text||'|'||md5(pg_get_constraintdef(c.oid))
          FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
          JOIN pg_namespace n ON n.oid=t.relnamespace
          WHERE n.nspname NOT IN ('pg_catalog','information_schema') ORDER BY 1"""),
        "foreign_keys": rows("foreign_keys", """SELECT n.nspname||'.'||t.relname||'|'||c.conname||'|'||md5(pg_get_constraintdef(c.oid))
          FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
          JOIN pg_namespace n ON n.oid=t.relnamespace WHERE c.contype='f' ORDER BY 1"""),
        "policies": rows("policies", """SELECT n.nspname||'.'||t.relname||'|'||p.polname||'|'||md5(concat_ws('|',p.polcmd,p.polpermissive::text,p.polroles::text,p.polqual::text,p.polwithcheck::text))
          FROM pg_policy p JOIN pg_class t ON t.oid=p.polrelid
          JOIN pg_namespace n ON n.oid=t.relnamespace ORDER BY 1"""),
        "extensions": rows("extensions", """SELECT e.extname||'|'||e.extversion||'|'||n.nspname
          FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace ORDER BY 1"""),
        "roles": rows("roles", """SELECT rolname||'|'||rolcanlogin||'|'||rolsuper||'|'||rolcreaterole||'|'||rolcreatedb||'|'||rolreplication||'|'||rolbypassrls
          FROM pg_roles WHERE rolname IN ('ai_tourism_owner','ai_tourism_app','rahgard_pilot_geo_executor','rahgard_pilot_geo_migrator') ORDER BY 1"""),
        "application_grants": rows("application_grants", """SELECT table_schema||'.'||table_name||'|'||privilege_type||'|'||is_grantable
          FROM information_schema.role_table_grants WHERE grantee='ai_tourism_app'
          UNION ALL SELECT table_schema||'.'||table_name||'.'||column_name||'|'||privilege_type||'|'||is_grantable
          FROM information_schema.column_privileges WHERE grantee='ai_tourism_app' ORDER BY 1"""),
        "rls_relations": rows("rls_relations", """SELECT n.nspname||'.'||c.relname||'|'||c.relrowsecurity||'|'||c.relforcerowsecurity
          FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE c.relkind IN ('r','p') AND c.relrowsecurity ORDER BY 1"""),
    }


def assert_catalog_preserved(before: dict[str, list[str]], after: dict[str, list[str]]) -> dict[str, int]:
    require(set(before["foreign_keys"]).issubset(after["foreign_keys"]), "A pre-existing foreign-key definition changed during additive migrations")
    require(set(before["indexes"]).issubset(after["indexes"]), "A pre-existing index disappeared during additive migrations")
    allowed_constraints = {
        "partner.review_events|review_events_decision_check|c",
        "partner.platform_grants|platform_grants_capability_check|c",
    }
    before_constraints = {"|".join(row.split("|")[:3]): row for row in before["constraints"]}
    after_constraints = {"|".join(row.split("|")[:3]): row for row in after["constraints"]}
    require(set(before_constraints).issubset(after_constraints), "A pre-existing constraint disappeared")
    changed = {key for key, value in before_constraints.items() if after_constraints[key] != value}
    require(changed.issubset(allowed_constraints), "An unapproved existing constraint definition changed")
    allowed_policies = {"partner.review_events|review_events_platform_insert"}
    before_policies = {"|".join(row.split("|")[:2]): row for row in before["policies"]}
    after_policies = {"|".join(row.split("|")[:2]): row for row in after["policies"]}
    require(set(before_policies).issubset(after_policies), "A pre-existing RLS policy disappeared")
    changed_policies = {key for key, value in before_policies.items() if after_policies[key] != value}
    require(changed_policies.issubset(allowed_policies), "An unapproved existing RLS policy changed")
    require(before["extensions"] == after["extensions"], "PostgreSQL extension versions or schemas changed")
    require(before["roles"] == after["roles"], "Role attributes changed during additive migrations")
    return {
        "indexes_before": len(before["indexes"]), "indexes_after": len(after["indexes"]),
        "constraints_before": len(before["constraints"]), "constraints_after": len(after["constraints"]),
        "foreign_keys": len(after["foreign_keys"]), "policies_before": len(before["policies"]),
        "policies_after": len(after["policies"]), "extensions": len(after["extensions"]),
        "application_grants_before": len(before["application_grants"]),
        "application_grants_after": len(after["application_grants"]),
        "rls_relations_before": len(before["rls_relations"]), "rls_relations_after": len(after["rls_relations"]),
    }


def current_migration_0025_guard_failures(
    container: str, pilot_marker: str, migration_0024_hash: str, migration_0025_hash: str
) -> list[str]:
    checks = {
        "database": "current_database()='rahgard_pilot_vps_staging'",
        "postgresql_17": "current_setting('server_version_num')::int BETWEEN 170000 AND 179999",
        "non_shared_port": "COALESCE(inet_server_port(),0) <> 55433",
        "marker": f"(SELECT count(*)=1 AND bool_and(marker_value='{pilot_marker}' AND marker_value ~ '^[a-fA-F0-9]{{32,128}}$') FROM public.rahgard_private_pilot_marker)",
        "prior_0024_hash": f"EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0024_partner_review_audit_actions' AND sha256='{migration_0024_hash}')",
        "migration_hash_formats": f"'{migration_0024_hash}' ~ '^[a-f0-9]{{64}}$' AND '{migration_0025_hash}' ~ '^[a-f0-9]{{64}}$'",
        "ledger_size": "(SELECT count(*) IN (23,25) FROM system.schema_migrations)",
        "ledger_head": "(SELECT max(migration_id)='0024_partner_review_audit_actions' FROM system.schema_migrations)",
        "no_unknown_migrations": "NOT EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id NOT IN ('0000_legacy_tourism_points_baseline','0001_core_schema','0002_synthetic_knowledge_seed','0003_synthetic_e2e_seed','0004_app_role_grants','0005_verified_unesco_destination_seed','0006_verified_unesco_destination_seed_batch2','0007_shiraz_dalahoo_wikipedia_dataset_v1','0008_authentication_foundation','0009_traveler_core','0010_task31_content_privacy_full_itinerary','0011_internal_chat_turns','0012_task5_published_claim_evidence','0013_private_pilot_geo_audit','0014_local_owner_login','0015_ai_provider_admin','0016_staging_invitation_auth','0017_provisional_itineraries','0018_national_catalogue_ingestion','0019_partner_workspace','0020_archive_candidate_publication','0021_postgis_security_definer_publication','0022_traveler_company_requests','0023_partner_trip_responses','0024_partner_review_audit_actions'))",
        "production_optional_migrations": "(SELECT count(*)=23 FROM system.schema_migrations) OR (EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0014_local_owner_login') AND EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0015_ai_provider_admin'))",
        "not_already_applied": "NOT EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0025_owner_control_center')",
        "capability_constraint": "EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid='partner.platform_grants'::regclass AND conname='platform_grants_capability_check' AND contype='c')",
    }
    select = ", ".join(f"({expression}) AS {name}" for name, expression in checks.items())
    result = sql(container, f"SELECT {select}", user=OWNER)
    values = result.split("|")
    require(len(values) == len(checks), "Migration 0025 diagnostic returned an unexpected shape")
    return [name for (name, _), value in zip(checks.items(), values, strict=True) if value != "t"]


def migration_guard_probe(source: bytes) -> bytes:
    text = source.decode("utf-8")
    start = text.index("SELECT 1 / CASE WHEN") + len("SELECT 1 / CASE WHEN")
    end = text.index("THEN 1 ELSE 0 END;", start)
    expression = text[start:end]
    clauses = re.split(r"\n    AND ", expression.strip())
    if len(clauses) < 5:
        raise ValueError("Could not safely parse guarded migration predicates")
    sql = "SELECT " + ", ".join(f"({clause.strip()}) AS guard_{i}" for i, clause in enumerate(clauses)) + ";\n"
    return sql.encode()


def render_guard_inputs(source: bytes, values: dict[str, str]) -> bytes:
    """Resolve only the checked psql guard inputs without changing SQL DDL."""
    pairs = re.findall(rb"^\\getenv ([a-z0-9_]+) ([A-Z0-9_]+)\s*$", source, re.MULTILINE)
    if not pairs:
        raise ValueError("Migration has no declared psql guard inputs")
    rendered = re.sub(rb"(?m)^\\getenv [a-z0-9_]+ [A-Z0-9_]+\r?\n", b"", source)
    for psql_name, env_name in pairs:
        name = env_name.decode("ascii")
        if name not in values:
            raise ValueError(f"Missing guarded migration input {name}")
        value = values[name]
        pattern = r"[a-fA-F0-9]{32,128}" if name == "RAHGARD_PILOT_DATABASE_MARKER" else r"[a-f0-9]{64}"
        if not re.fullmatch(pattern, value):
            raise ValueError(f"Invalid guarded migration input {name}")
        placeholder = b":'" + psql_name + b"'"
        rendered = rendered.replace(placeholder, b"'" + value.encode("ascii") + b"'")
    if b"\\getenv " in rendered or b":'" in rendered:
        raise ValueError("Unresolved migration guard input remained")
    return rendered


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
    migration_rows = manifest["vps"]["database"]["migration_ledger"]
    base = [f'{row["migration_id"]}|{row["sha256"]}' for row in migration_rows]
    current_0023 = migration_rows[-1]["migration_id"] == "0023_partner_trip_responses"
    if current_0023:
        expected = check_current_snapshot(manifest, args.source_sha)
        base_numbers = CURRENT_BASE_NUMBERS
        target_numbers = CURRENT_TARGET_NUMBERS
        blobs = current_migration_blobs(args.source_sha)
    else:
        expected = check(manifest, args.source_sha)
        base_numbers = BASE_NUMBERS
        target_numbers = (22, 23)
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
        require(len(base) == len(base_numbers) and ledger(container) == base, "Restore ledger differs from observed VPS")
        before = counts(container)
        accounts_before = account_fingerprints(container)
        catalog_before = catalog_security_snapshot(container)
        live = manifest["vps"]["database"]["aggregate_counts"]
        for table, field in (
            ("identity.users", "users"), ("identity.web_sessions", "sessions"), ("travel.trips", "trips"),
            ("conversation.conversations", "conversations"), ("travel.itineraries", "itineraries"),
            ("partner.organizations", "organizations"), ("knowledge.production_destinations", "published_destinations"),
        ):
            require(before[table] == live[field], f"Restored count differs from observed VPS for {table}")
        started = time.monotonic()
        prior_hash = migration_rows[-1]["sha256"]
        pilot_marker = sql(container, "SELECT marker_value FROM public.rahgard_private_pilot_marker")
        recorded_hashes = {row["migration_id"]: row["sha256"] for row in migration_rows}
        recorded_hashes.update({item["id"]: item["sha256"] for item in expected["pending"]})
        guard_values = {
            "RAHGARD_PILOT_DATABASE_MARKER": pilot_marker,
            "RAHGARD_PILOT_MIGRATION_0023_SHA256": recorded_hashes["0023_partner_trip_responses"],
            "RAHGARD_PILOT_MIGRATION_0024_SHA256": recorded_hashes["0024_partner_review_audit_actions"],
            "RAHGARD_PILOT_MIGRATION_0025_SHA256": recorded_hashes["0025_owner_control_center"],
            "RAHGARD_PILOT_MIGRATION_0026_SHA256": recorded_hashes["0026_platform_reviewer_mfa"],
        }
        elapsed = {}
        for position, number in enumerate(target_numbers):
            identity, source = blobs[number]
            item = expected["pending"][position]
            require(identity == item["id"], "Migration identity mismatch")
            current_hash = item["sha256"]
            source_for_psql = render_guard_inputs(source, guard_values)
            cmd = "exec psql -Xq -v ON_ERROR_STOP=1 -v VERBOSITY=verbose -h 127.0.0.1 -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\""
            phase_start = time.monotonic()
            if number == 24:
                interrupted = source_for_psql.replace(b"COMMIT;", b"SELECT 1/0;\nCOMMIT;")
                require(interrupted != source_for_psql, "0024 transaction boundary not found for interruption test")
                try:
                    run("docker", "exec", "-i", container, "sh", "-ec", cmd, data=interrupted)
                except RuntimeError as error:
                    require("sqlstate=22012" in str(error), "Interrupted migration failed for an unexpected reason")
                else:
                    raise RuntimeError("Interrupted 0024 migration unexpectedly committed")
                require(ledger(container) == base, "Interrupted migration changed the baseline ledger")
                require(counts(container) == before, "Interrupted migration changed existing data counts")
                require(sql(container, "SELECT count(*)=1 FROM pg_catalog.pg_constraint WHERE conrelid='partner.review_events'::regclass AND conname='review_events_decision_check'") == "t",
                        "Interrupted migration left a partially changed review constraint")
            if number == 25:
                failures = current_migration_0025_guard_failures(container, pilot_marker, prior_hash, current_hash)
                require(not failures, "0025 preflight guard failed: " + ", ".join(failures))
                probe_cmd = "exec psql -XqAt -F '|' -v ON_ERROR_STOP=1 -h 127.0.0.1 -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\""
                probe = run("docker", "exec", "-i", container, "sh", "-ec", probe_cmd,
                             data=migration_guard_probe(source_for_psql)).decode().strip().split("|")
                require(all(value == "t" for value in probe),
                        "0025 source guard predicate failed: " + ", ".join(
                            f"guard_{i}" for i, value in enumerate(probe) if value != "t"))
            run(
                "docker", "exec", "-i",
                container, "sh", "-ec", cmd, data=source_for_psql,
            )
            elapsed[identity] = round(time.monotonic() - phase_start, 3)
            base.append(f"{identity}|{current_hash}")
            require(ledger(container) == base, f"Ledger differs after {identity}")
            prior_hash = current_hash
        after = counts(container)
        catalog_after = catalog_security_snapshot(container)
        catalog_changes = assert_catalog_preserved(catalog_before, catalog_after)
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
        if current_0023:
            require(sql(container, """
                SELECT
                  (SELECT count(*)=25 FROM system.schema_migrations)
                  AND (SELECT max(migration_id)='0026_platform_reviewer_mfa' FROM system.schema_migrations)
                  AND (SELECT bool_and(relrowsecurity) FROM pg_class WHERE oid IN (
                    'identity.platform_admin_mfa'::regclass,
                    'identity.platform_admin_step_up'::regclass,
                    'identity.platform_admin_mfa_events'::regclass))
                  AND (SELECT count(*)=3 FROM pg_policy WHERE polrelid IN (
                    'identity.platform_admin_mfa'::regclass,
                    'identity.platform_admin_step_up'::regclass,
                    'identity.platform_admin_mfa_events'::regclass))
                  AND NOT has_table_privilege('ai_tourism_app','identity.platform_admin_mfa_events','SELECT')
                  AND NOT has_table_privilege('ai_tourism_app','partner.platform_grants','UPDATE')
                  AND NOT has_table_privilege('ai_tourism_app','partner.platform_grant_events','INSERT')
                  AND has_function_privilege('ai_tourism_app','identity.record_platform_admin_mfa_event(text,uuid)','EXECUTE')
                  AND has_function_privilege('ai_tourism_app','identity.has_platform_admin_capability(uuid)','EXECUTE')
                  AND (SELECT pg_get_constraintdef(oid) LIKE '%admin_overview_read%'
                       FROM pg_constraint WHERE conrelid='partner.platform_grants'::regclass
                         AND conname='platform_grants_capability_check')
                  AND (SELECT count(*)=0 FROM identity.platform_admin_mfa)
                  AND (SELECT count(*)=0 FROM identity.platform_admin_step_up)
                  AND (SELECT count(*)=0 FROM identity.platform_admin_mfa_events)
            """) == "t", "0024-0026 ledger, reviewer privileges, audit or MFA RLS assertions failed")
        api_checks = {}
        for image in args.runtime_image:
            api_checks[image] = check_api(container, image, label, before["knowledge.production_destinations"])
            require(counts(container) == after, "API compatibility check changed restored row counts")
        apex_auth = None
        if args.apex_auth_images:
            from test_rahgard_apex_auth import test_apex_auth

            apex_auth = test_apex_auth(container, *args.apex_auth_images, args.openssl, browser=args.apex_browser)
        return {
            "backup": args.backup.name, "backup_sha256": digest, "checksum_hmac_and_archive": "passed",
            "migration_sql_source_sha": args.source_sha, "postgresql_image_id": PG_IMAGE,
            "before_migration_count": len(base_numbers), "after_migration_count": len(base),
            "after_ledger": base, "migration_seconds": elapsed,
            "counts_before": before, "counts_after": after, "new_share_response_rows": 0,
            "interrupted_0024_transaction": "rolled back; baseline ledger, data counts and review constraint unchanged",
            "existing_account_and_credential_contents_preserved": True,
            "catalog_security_comparison": catalog_changes,
            "rls_and_app_grants": "passed", "isolation": "network none, no published ports, tmpfs data",
            "rehearsal_scope": "actual-0023-ledger" if current_0023 else "historical-0021-ledger",
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
    parser.add_argument("--evidence-output", type=Path, help="Write sanitized result JSON inside the repository")
    parser.add_argument("--runtime-image", action="append", default=[], help="Local API image for isolated smoke")
    parser.add_argument("--apex-auth-images", nargs=3, metavar=("LEGACY_API", "V2_API", "V2_WEB"))
    parser.add_argument("--apex-browser", action="store_true", help="Run Chromium via an apex-only local fixture tunnel")
    args = parser.parse_args()
    try:
        result = rehearse(args)
        rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.evidence_output:
            output = args.evidence_output.resolve()
            try:
                output.relative_to(REPO / "docs/operations/evidence/issue27")
            except ValueError as error:
                raise ValueError("Evidence output must remain in the Issue 27 evidence directory") from error
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_suffix(output.suffix + ".tmp")
            temporary.write_text(rendered, encoding="utf-8")
            temporary.replace(output)
        print(rendered, end="")
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        parser.exit(2, f"BLOCKED: {error}\n")


if __name__ == "__main__":
    main()
