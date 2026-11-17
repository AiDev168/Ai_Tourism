"""Stage the verified owner archive into a disposable, marked PostgreSQL database.

This command is intentionally unusable against a live/staging database. It
checks the database name, loopback endpoint, PostgreSQL major, marker and
reviewer grant before invoking the normal archive staging path twice.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from uuid import UUID

import psycopg
from pydantic import SecretStr
from psycopg.rows import dict_row

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings  # noqa: E402
from app.modules.catalog.archive_ingest import stage_archive  # noqa: E402
from app.modules.identity.auth_service import AuthenticatedUser  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", help="read-only path to owner ZIP; never copied")
    args = parser.parse_args()
    host = os.environ.get("DATABASE_HOST", "")
    database = os.environ.get("DATABASE_NAME", "")
    user = os.environ.get("DATABASE_USER", "")
    password = os.environ.get("DATABASE_PASSWORD", "")
    port_text = os.environ.get("DATABASE_PORT", "")
    marker = os.environ.get("RAHGARD_PILOT_DATABASE_MARKER", "")
    actor_text = os.environ.get("RAHGARD_ARCHIVE_REVIEWER_ID", "")
    if (
        host not in {"127.0.0.1", "localhost"}
        or database != "rahgard_pilot_vps_staging"
        or user != "ai_tourism_app"
        or not password
        or not re.fullmatch(r"[a-fA-F0-9]{32,128}", marker)
    ):
        raise SystemExit("isolated archive staging refused: target configuration failed closed")
    try:
        port = int(port_text)
        actor_id = UUID(actor_text)
    except ValueError:
        raise SystemExit("isolated archive staging refused: target configuration failed closed") from None
    if not 1 <= port <= 65535:
        raise SystemExit("isolated archive staging refused: target configuration failed closed")
    archive = Path(args.archive)
    if not archive.is_file():
        raise SystemExit("owner archive is not a readable file")

    connect_args = {
        "host": host,
        "port": port,
        "dbname": database,
        "user": user,
        "password": password,
        "connect_timeout": 3,
        "row_factory": dict_row,
    }
    try:
        with psycopg.connect(**connect_args) as conn:
            identity = conn.execute(
                """SELECT current_database() AS db, current_user AS role,
                current_setting('server_version_num')::int AS version,
                (SELECT count(*) FROM public.rahgard_private_pilot_marker) AS marker_count,
                (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) AS marker"""
            ).fetchone()
            grant = conn.execute(
                "SELECT identity.has_catalogue_review_capability(%s,'candidate_review') AS allowed",
                (actor_id,),
            ).fetchone()
    except Exception:
        raise SystemExit("isolated archive staging refused: database marker or grant could not be checked") from None
    if (
        identity["db"] != database
        or identity["role"] != user
        or not 170000 <= identity["version"] < 180000
        or identity["marker_count"] != 1
        or identity["marker"] != marker
        or not grant["allowed"]
    ):
        raise SystemExit("isolated archive staging refused: disposable target validation failed")

    settings = Settings(
        _env_file=None,
        app_env="test",
        database_host=host,
        database_port=port,
        database_name=database,
        database_user=user,
        database_password=SecretStr(password),
    )
    reviewer = AuthenticatedUser(actor_id, None, UUID(int=1), "isolated_archive_review")
    payload = archive.read_bytes()
    first = stage_archive(payload, reviewer, settings)
    second = stage_archive(payload, reviewer, settings)
    with psycopg.connect(**connect_args) as conn:
        conn.execute("SELECT set_config('app.actor_id',%s,false)", (str(actor_id),))
        source_candidate = conn.execute(
            """SELECT source_candidate_id,proposed_source_name,proposed_source_type,proposed_url
            FROM knowledge.source_candidates
            WHERE candidate_status='needs_review' AND proposed_source_name IS NOT NULL
              AND proposed_url LIKE 'https://%%' ORDER BY source_candidate_id LIMIT 1 FOR UPDATE"""
        ).fetchone()
        if source_candidate is None:
            raise SystemExit("archive has no source-register row usable for the pending-registration smoke")
        source_name = str(source_candidate["proposed_source_name"]).strip()
        source_type = str(source_candidate["proposed_source_type"] or "research_pending")[:80]
        source_url = str(source_candidate["proposed_url"]).strip()
        pending_source = conn.execute(
            """INSERT INTO knowledge.knowledge_sources
            (source_name,source_type,verification_status,url,notes,is_synthetic)
            VALUES (%s,%s,'pending',%s,'Isolated archive review test; not approved for publication.',FALSE)
            RETURNING source_id,verification_status,is_synthetic""",
            (source_name, source_type, source_url),
        ).fetchone()
        conn.execute(
            """INSERT INTO knowledge.source_candidate_reviews
            (source_candidate_id,decision,source_id,reason,evidence_refs,reviewer_user_id,policy_version)
            VALUES (%s,'register_pending',%s,'isolated test of pending-only source registration',%s::jsonb,%s,'isolated-test-v1')""",
            (source_candidate["source_candidate_id"], pending_source["source_id"],
             json.dumps(["isolated-archive-row"]), str(actor_id)),
        )
        conn.execute(
            """UPDATE knowledge.source_candidates SET candidate_status='registered_pending',
            registered_source_id=%s,updated_at=now() WHERE source_candidate_id=%s""",
            (pending_source["source_id"], source_candidate["source_candidate_id"]),
        )
        counts = conn.execute(
            """SELECT candidate_kind,count(*)::int AS n,
            count(*) FILTER (WHERE candidate_status <> 'needs_review')::int AS resolved,
            count(*) FILTER (WHERE canonical_destination_id IS NOT NULL)::int AS linked
            FROM knowledge.destination_candidates WHERE source_file_sha256 <> repeat('a',64)
            GROUP BY candidate_kind ORDER BY candidate_kind"""
        ).fetchall()
        file_count = conn.execute(
            """SELECT count(*)::int AS n FROM operations.dataset_import_files f
            JOIN operations.dataset_import_batches b USING(dataset_import_batch_id)
            WHERE b.batch_key=%s AND f.import_status='review_ready'""",
            (f"upload:{first['archive_sha256']}",),
        ).fetchone()["n"]
        source_state = conn.execute(
            """SELECT count(*)::int AS n,
            count(*) FILTER (WHERE candidate_status <> 'needs_review')::int AS reviewed,
            count(*) FILTER (WHERE registered_source_id IS NOT NULL)::int AS registered,
            (SELECT count(*)::int FROM knowledge.source_candidate_reviews) AS decisions,
            (SELECT count(*)::int FROM knowledge.knowledge_sources WHERE verification_status='pending' AND NOT is_synthetic) AS pending_sources
            FROM knowledge.source_candidates"""
        ).fetchone()
    count_by_kind = {row["candidate_kind"]: row["n"] for row in counts}
    expected = {"destination_identity": 167, "discovery_lead": 533}
    if count_by_kind != expected:
        raise SystemExit(
            "archive staging count mismatch; "
            + json.dumps(
                {
                    "database_counts": count_by_kind,
                    "first_import_counts": first["candidate_rows_by_kind"],
                    "first_import_staged": first["rows_staged"],
                    "first_import_candidate_files": first["candidate_files"],
                },
                sort_keys=True,
            )
        )
    if first["rows_staged"] != 700 or second["rows_staged"] != 0:
        raise SystemExit("archive staging idempotency assertion failed")
    if second["source_rows_staged"] != 0 or source_state["n"] != first["source_rows_staged"]:
        raise SystemExit("source-register staging idempotency assertion failed")
    if any(row["resolved"] or row["linked"] for row in counts):
        raise SystemExit("archive staging unexpectedly resolved or linked candidates")
    if (source_state["reviewed"], source_state["registered"], source_state["decisions"], source_state["pending_sources"]) != (1, 1, 1, 1):
        raise SystemExit("source review did not create exactly one non-published pending source")
    safe_result = {
        "archive_sha256": first["archive_sha256"],
        "member_count": first["members"],
        "csv_file_count": first["csv_files"],
        "candidate_files": first["candidate_files"],
        "ignored_non_place_csv_files": first["ignored_non_place_csv_files"],
        "source_register_files": first["source_register_files"],
        "source_register_rows_seen": first["source_rows_in_supported_registers"],
        "source_candidate_rows_staged": first["source_rows_staged"],
        "source_candidate_repeat_import_staged": second["source_rows_staged"],
        "source_candidates_reviewed": source_state["reviewed"],
        "source_review_decisions": source_state["decisions"],
        "registered_sources_pending_unpublished": source_state["pending_sources"],
        "csv_rows_by_supported_kind": first["candidate_rows_by_kind"],
        "distinct_keys_by_kind": first["distinct_record_keys_by_kind"],
        "staged_first_import": first["rows_staged"],
        "staged_repeat_import": second["rows_staged"],
        "review_ready_file_rows": file_count,
        "candidate_rows": count_by_kind,
        "all_candidates_unresolved_unpublished": True,
        "publication_approved": False,
        "source_registration_is_pending_only": True,
    }
    print(json.dumps(safe_result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
