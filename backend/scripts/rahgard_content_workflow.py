"""Review-gated Issue #5 staging/publication/export commands.

All database commands require the repository's guarded disposable PG17 marker
and operator credentials. This script never reads dotenv files or writes to
the owner RAG repository. The default review-plan and dry-run commands are
offline and side-effect free.
"""

# The standalone operator script bootstraps the backend package root below.
# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.catalog.content_importer import stage_review_content_pack
from app.modules.catalog.content_pack import (
    CandidateContentPack,
    load_candidate_content_pack,
    payload_sha256,
)
from app.modules.catalog.owner_content_approval import (
    PILOT_RECORD_KEYS,
    ApprovalBlocked,
    OwnerDecisionPacket,
    approved_owner_record,
    build_review_queue,
    canonical_json_bytes,
    sign_decision_packet,
    validate_decisions,
)

MAX_PACKET_BYTES = 1_000_000
_DB_NAME = re.compile(r"^ai_tourism_auth_test_mvp_[a-f0-9]{12}$")
_MIGRATION = "0012_task5_published_claim_evidence"


def _read_packet(path: Path) -> OwnerDecisionPacket:
    if not path.is_file() or path.stat().st_size > MAX_PACKET_BYTES:
        raise ApprovalBlocked("decision packet is missing or exceeds the size limit")
    try:
        return OwnerDecisionPacket.model_validate_json(path.read_bytes())
    except Exception:
        raise ApprovalBlocked("decision packet is malformed") from None


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(data) + b"\n")


def _approval_key() -> bytes:
    raw = os.environ.get("RAHGARD_CONTENT_APPROVAL_HMAC_KEY", "")
    if len(raw.encode("utf-8")) < 32:
        raise ApprovalBlocked("owner approval HMAC key is not configured")
    return raw.encode("utf-8")


def _guarded_operator_connection():
    if os.environ.get("AUTH_INTEGRATION_TESTS") != "1":
        raise ApprovalBlocked("guarded disposable database mode is required")
    host = os.environ.get("AUTH_TEST_DATABASE_HOST", "")
    port_text = os.environ.get("AUTH_TEST_DATABASE_PORT", "")
    name = os.environ.get("AUTH_TEST_DATABASE_NAME", "")
    user = os.environ.get("AUTH_TEST_DATABASE_OWNER_USER", "ai_tourism_owner")
    password = os.environ.get("AUTH_TEST_DATABASE_OWNER_PASSWORD", "")
    marker = os.environ.get("AUTH_TEST_DATABASE_MARKER", "")
    try:
        port = int(port_text)
    except ValueError:
        raise ApprovalBlocked("disposable database endpoint is invalid") from None
    if (
        host not in {"127.0.0.1", "localhost"}
        or port == 55433
        or not 1024 <= port <= 65535
        or not _DB_NAME.fullmatch(name)
        or user != "ai_tourism_owner"
        or not password
        or len(marker) < 32
    ):
        raise ApprovalBlocked("disposable database guard is incomplete")
    try:
        connection = psycopg.connect(
            host=host, port=port, dbname=name, user=user, password=password,
            connect_timeout=3, application_name="rahgard-content-review-workflow",
            row_factory=dict_row,
        )
        facts = connection.execute(
            """SELECT current_database() AS database_name, current_user AS database_user,
                      current_setting('server_version_num')::INTEGER AS server_version,
                      (SELECT marker_value FROM public.ai_tourism_auth_test_marker LIMIT 1) AS marker,
                      (SELECT sha256 FROM system.schema_migrations WHERE migration_id=%s) AS migration_hash""",
            (_MIGRATION,),
        ).fetchone()
        expected_hash = hashlib.sha256(
            (Path(__file__).resolve().parents[2]
             / "engineering" / "database-prep" / "sql"
             / "012_task5_published_claim_evidence.sql").read_bytes()
        ).hexdigest()
        if (
            facts["database_name"] != name
            or facts["database_user"] != user
            or not 170000 <= facts["server_version"] < 180000
            or not hmac.compare_digest(str(facts["marker"]), marker)
            or facts["migration_hash"] != expected_hash
        ):
            connection.close()
            raise ApprovalBlocked("database marker, engine, or migration checksum did not match")
        # End the read-only preflight transaction before any command starts a
        # separate staging/publication transaction. Without this commit, the
        # command-level transaction contexts become savepoints and connection
        # close would roll back the reported inserts/publication.
        connection.commit()
        return connection
    except ApprovalBlocked:
        raise
    except Exception:
        raise ApprovalBlocked("guarded disposable database is unavailable") from None


def _selected_pack(pack: CandidateContentPack) -> CandidateContentPack:
    selected = [
        proposal for proposal in pack.existing_destination_enrichment_proposals
        if proposal.target_record_key in PILOT_RECORD_KEYS
    ]
    if {proposal.target_record_key for proposal in selected} != set(PILOT_RECORD_KEYS):
        raise ApprovalBlocked("fixed owner-review candidates are not present in the source pack")
    return CandidateContentPack.model_validate({
        **pack.model_dump(mode="json"),
        "existing_destination_enrichment_proposals": selected,
        "non_spatial_knowledge": [],
    })


def _create_batch(connection, pack: CandidateContentPack) -> str:
    payload = [
        proposal.model_dump(mode="json")
        for proposal in pack.existing_destination_enrichment_proposals
    ]
    digest = payload_sha256(payload)
    key = f"rahgard-issue5-review:{pack.dataset_key}:{pack.version}:{digest[:16]}"
    with connection.transaction():
        connection.execute(
            """INSERT INTO operations.dataset_import_batches
               (batch_key, data_class, record_counts, source_checksum, notes)
               VALUES (%s, 'verified_external', %s::JSONB, %s,
                       'Issue #5 selected three-record proposal staging; review only')
               ON CONFLICT (batch_key) DO NOTHING""",
            (key, json.dumps({"spatial_proposals": 3, "culinary_proposals": 0}), digest),
        )
        row = connection.execute(
            """SELECT dataset_import_batch_id, data_class, source_checksum
               FROM operations.dataset_import_batches WHERE batch_key=%s""", (key,)
        ).fetchone()
        if row is None or row["data_class"] != "verified_external" or row["source_checksum"].strip() != digest:
            raise ApprovalBlocked("existing import batch does not match this review payload")
        return str(row["dataset_import_batch_id"])


def _stage_review(connection, pack: CandidateContentPack) -> dict[str, int]:
    selected = _selected_pack(pack)
    with connection.transaction():
        before = connection.execute(
            """SELECT
                 (SELECT count(*) FROM knowledge.destinations) AS destinations,
                 (SELECT count(*) FROM knowledge.knowledge_sources) AS sources,
                 (SELECT count(*) FROM knowledge.knowledge_documents) AS documents,
                 (SELECT count(*) FROM knowledge.production_destinations) AS production"""
        ).fetchone()
        batch_id = _create_batch(connection, selected)
        counts = stage_review_content_pack(connection, batch_id, selected)
        after = connection.execute(
            """SELECT
                 (SELECT count(*) FROM knowledge.destinations) AS destinations,
                 (SELECT count(*) FROM knowledge.knowledge_sources) AS sources,
                 (SELECT count(*) FROM knowledge.knowledge_documents) AS documents,
                 (SELECT count(*) FROM knowledge.production_destinations) AS production"""
        ).fetchone()
        if before != after:
            raise ApprovalBlocked("review staging changed canonical or production row counts")
        pending = connection.execute(
            """SELECT count(*) AS n FROM knowledge.destination_enrichment_proposals
               WHERE dataset_import_batch_id=%s AND review_status='needs_review'
                 AND verification_status='pending' AND approval_confidence=0 AND publishable=FALSE""",
            (batch_id,),
        ).fetchone()["n"]
        if pending != 3:
            raise ApprovalBlocked("staged proposal set is not exactly three pending review rows")
    return counts


def _approved_db_rows(connection, approved, pack: CandidateContentPack):
    sources_by_id = {source.source_id: source for source in pack.source_register}
    proposal_by_key = {
        item.target_record_key: item for item in pack.existing_destination_enrichment_proposals
    }
    resolved: list[dict[str, Any]] = []
    for decision in approved:
        proposal = proposal_by_key[decision.record_key]
        destination = connection.execute(
            """SELECT destination_id FROM knowledge.production_destinations
               WHERE destination_key=%s""", (decision.record_key,)
        ).fetchone()
        if destination is None:
            raise ApprovalBlocked("destination is not independently approved in production view")
        for claim in decision.claims:
            source_claim = next(item for item in proposal.factual_claims if item.claim_id == claim.claim_id)
            for location in claim.evidence_locations:
                source_doc = connection.execute(
                    """SELECT document_id FROM knowledge.production_retrieval_documents
                       WHERE destination_id=%s AND document_key=%s AND content_sha256=%s
                         AND language_code IN (%s, %s)""",
                    (
                        destination["destination_id"], location.document_key,
                        location.document_sha256,
                        {"fa-IR": "fa", "en-US": "en", "ar": "ar"}[location.locale],
                        location.locale,
                    ),
                ).fetchone()
                if source_doc is None:
                    raise ApprovalBlocked("approved document does not match the current production projection")
                chunk = connection.execute(
                    """SELECT chunk_id, content, content_sha256 FROM knowledge.production_retrieval_chunks
                       WHERE destination_id=%s AND document_id=%s AND chunk_id=%s AND content_sha256=%s""",
                    (destination["destination_id"], source_doc["document_id"], location.chunk_id,
                     location.chunk_sha256),
                ).fetchone()
                if chunk is None or hashlib.sha256(chunk["content"].encode("utf-8")).hexdigest() != location.chunk_sha256:
                    raise ApprovalBlocked("approved chunk hash does not match current source text")
                for source_id in claim.source_ids:
                    source_decision = next(item for item in decision.sources if item.source_id == source_id)
                    if source_id not in source_claim.source_ids:
                        raise ApprovalBlocked("approval references source outside the selected claim")
                    source = connection.execute(
                        """SELECT source_id, source_name, source_url, source_role, retrieved_at,
                                  valid_from, valid_until
                           FROM knowledge.production_destination_sources
                           WHERE destination_id=%s AND source_url=%s""",
                        (destination["destination_id"], sources_by_id[source_id].url),
                    ).fetchone()
                    if source is None:
                        raise ApprovalBlocked("source is not currently approved for this destination")
                    resolved.append({
                        "destination_id": destination["destination_id"],
                        "destination_key": decision.record_key,
                        "document_id": source_doc["document_id"],
                        "chunk_id": chunk["chunk_id"],
                        "claim_key": location.claim_key,
                        "locale": location.locale,
                        "content_hash": chunk["content_sha256"].strip(),
                        "source": source,
                        "license": source_decision.approved_license,
                    })
    return resolved


def _publish(connection, resolved: list[dict[str, Any]]) -> dict[str, int]:
    inserted = unchanged = 0
    with connection.transaction():
        for row in resolved:
            source = row["source"]
            result = connection.execute(
                """INSERT INTO knowledge.destination_claim_evidence
                   (destination_id, document_id, chunk_id, claim_key, locale, content_hash,
                    source_id, source_name, source_url, source_role, source_license, retrieved_at,
                    valid_from, valid_until, review_status, verification_status, is_synthetic, published_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                           'approved','verified',FALSE,NOW())
                   ON CONFLICT (chunk_id, claim_key, locale, source_id) DO NOTHING
                   RETURNING claim_evidence_id""",
                (row["destination_id"], row["document_id"], row["chunk_id"], row["claim_key"],
                 row["locale"], row["content_hash"], source["source_id"], source["source_name"],
                 source["source_url"], source["source_role"], row["license"], source["retrieved_at"],
                 source["valid_from"], source["valid_until"]),
            ).fetchone()
            if result:
                inserted += 1
                continue
            existing = connection.execute(
                """SELECT destination_id, document_id, content_hash, source_name, source_url,
                          source_role, source_license, retrieved_at, valid_from, valid_until,
                          review_status, verification_status, is_synthetic
                   FROM knowledge.destination_claim_evidence
                   WHERE chunk_id=%s AND claim_key=%s AND locale=%s AND source_id=%s""",
                (row["chunk_id"], row["claim_key"], row["locale"], source["source_id"]),
            ).fetchone()
            expected = (
                row["destination_id"], row["document_id"], row["content_hash"],
                source["source_name"], source["source_url"], source["source_role"],
                row["license"], source["retrieved_at"], source["valid_from"], source["valid_until"],
                "approved", "verified", False,
            )
            actual = tuple(existing.values()) if existing else ()
            if actual != expected:
                raise ApprovalBlocked("existing publication mapping conflicts with signed owner decision")
            unchanged += 1
    return {"inserted": inserted, "unchanged": unchanged}


def _export_rows(connection, approved, reviewed_at):
    keys = [item.record_key for item in approved]
    if not keys:
        return []
    rows = connection.execute(
        """SELECT v.canonical_entity_key, v.claim_evidence_id,
                  v.document_id, rd.document_key, rd.content_sha256 AS document_sha256,
                  c.chunk_id, c.content_sha256 AS chunk_sha256,
                  v.content_hash, v.locale, v.corpus, v.claim_key,
                  c.content, v.source_id, v.source_name, v.source_url, v.source_role,
                  v.license, v.retrieved_at, v.source_valid_from AS valid_from,
                  v.source_valid_until AS valid_until
           FROM (
             SELECT p.*, ce.claim_evidence_id
             FROM knowledge.production_destination_claim_evidence p
             JOIN knowledge.destination_claim_evidence ce
               ON ce.destination_id=p.destination_id AND ce.document_id::TEXT=p.document_id
              AND ce.chunk_id::TEXT=p.chunk_id AND ce.claim_key=p.claim_key
              AND ce.locale=p.locale AND ce.source_id::TEXT=p.source_id
           ) v
           JOIN knowledge.production_retrieval_chunks c ON c.chunk_id::TEXT=v.chunk_id
           JOIN knowledge.production_retrieval_documents rd ON rd.document_id::TEXT=v.document_id
           WHERE v.canonical_entity_key = ANY(%s::TEXT[])
           ORDER BY v.canonical_entity_key, v.document_id, v.claim_key, v.locale, v.source_id""",
        (keys,),
    ).fetchall()
    pack = load_candidate_content_pack()
    proposal_by_key = {item.target_record_key: item for item in pack.existing_destination_enrichment_proposals}
    allowed: dict[tuple[str, str, str, str, str, str, str], set[str]] = {}
    for decision in approved:
        proposal = proposal_by_key[decision.record_key]
        claims = {item.claim_id: item for item in proposal.factual_claims}
        source_decisions = {item.source_id: item for item in decision.sources}
        for claim in decision.claims:
            if claim.claim_id not in claims:
                raise ApprovalBlocked("signed claim is absent from the source pack")
            for location in claim.evidence_locations:
                identity = (
                    decision.record_key, location.document_key or "",
                    location.document_sha256 or "", location.chunk_id or "",
                    location.chunk_sha256 or "", location.claim_key or "", location.locale,
                )
                allowed[identity] = {
                    source_decisions[source_id].source_url for source_id in claim.source_ids
                }
    by_claim: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        identity = (
            row["canonical_entity_key"], row["document_key"],
            str(row["document_sha256"]).strip(), str(row["chunk_id"]),
            str(row["chunk_sha256"]).strip(), row["claim_key"], row["locale"],
        )
        if row["source_url"] not in allowed.get(identity, set()):
            continue
        claim_identity = (
            row["canonical_entity_key"], str(row["document_id"]), str(row["chunk_id"]),
            row["claim_key"], row["locale"], str(row["content_hash"]).strip(),
        )
        grouped = by_claim.setdefault(claim_identity, {"row": row, "evidence_ids": [], "sources": []})
        grouped["evidence_ids"].append(str(row["claim_evidence_id"]))
        grouped["sources"].append({
            "source_id": row["source_id"], "source_name": row["source_name"],
            "source_url": row["source_url"], "source_role": row["source_role"],
            "retrieved_at": row["retrieved_at"], "valid_from": row["valid_from"],
            "valid_until": row["valid_until"], "license": row["license"],
        })
    return [
        approved_owner_record(
            # The source-level table has one persisted claim_evidence_id per
            # source relation. Use the lexically first persisted UUID as the
            # stable evidence identity for the grouped claim; all approved
            # source rows for this exact claim are emitted together so the
            # traveler mapper can require an exact source-set match.
            evidence_id=min(grouped["evidence_ids"]),
            document_id=str(row["document_id"]),
            content_hash=str(row["content_hash"]).strip(), text=row["content"],
            locale=row["locale"], canonical_entity_key=row["canonical_entity_key"],
            claim_key=row["claim_key"], source_rows=grouped["sources"], reviewed_at=reviewed_at,
        )
        for _, grouped in sorted(by_claim.items())
        for row in (grouped["row"],)
    ]


def _template_command(args) -> None:
    pack = load_candidate_content_pack()
    packet = build_review_queue(pack)
    _write_json(args.output, packet.model_dump(mode="json"))
    print(json.dumps({"status": "review_only", "records": len(packet.records),
                      "all_deferred": True, "output": str(args.output)}, sort_keys=True))


def _dry_run_command(_args) -> None:
    pack = load_candidate_content_pack()
    packet = build_review_queue(pack)
    approved = validate_decisions(pack, packet, require_signature=False)
    # There is no owner-approved publication projection or signed export input
    # in the repository; therefore no owner-index JSONL can be emitted.
    print(json.dumps({
        "status": "held_for_owner_review",
        "candidate_records": len(packet.records),
        "deferred_records": sum(item.decision == "defer" for item in packet.records),
        "approved_records": len(approved),
        "owner_index_jsonl_records": 0,
        "published": False,
        "indexed": False,
    }, sort_keys=True))


def _sign_command(args) -> None:
    pack = load_candidate_content_pack()
    packet = _read_packet(args.decisions)
    validate_decisions(pack, packet, require_signature=False)
    signed = sign_decision_packet(
        packet,
        approver_name=args.approver_name,
        approver_role=args.approver_role,
        approval_reference=args.approval_reference,
        decided_at=args.decided_at,
        signing_key=_approval_key(),
    )
    _write_json(args.output, signed.model_dump(mode="json"))
    print(json.dumps({"status": "signed_decision_packet_written", "output": str(args.output)}, sort_keys=True))


def _verify_approval(path: Path, pack: CandidateContentPack):
    packet = _read_packet(path)
    approved = validate_decisions(pack, packet, require_signature=False)
    if approved:
        approved = validate_decisions(pack, packet, signing_key=_approval_key())
    return packet, approved


def _stage_command(args) -> None:
    pack = load_candidate_content_pack()
    connection = _guarded_operator_connection()
    try:
        counts = _stage_review(connection, pack)
        connection.commit()
    finally:
        connection.close()
    print(json.dumps({"status": "review_only", "proposal_counts": counts, "published": False}, sort_keys=True))


def _publish_command(args) -> None:
    pack = load_candidate_content_pack()
    packet, approved = _verify_approval(args.decisions, pack)
    if not approved:
        print(json.dumps({"status": "held_for_owner_review", "published_rows": 0}, sort_keys=True))
        return
    if not args.apply_owner_approval:
        raise ApprovalBlocked("explicit --apply-owner-approval is required for isolated publication")
    connection = _guarded_operator_connection()
    try:
        # The identity/provenance reads, writes, and postcondition share one
        # transaction. A failed production-view check must roll back every row.
        with connection.transaction():
            resolved = _approved_db_rows(connection, approved, pack)
            result = _publish(connection, resolved)
            visible_keys = {
                row["canonical_entity_key"]
                for row in connection.execute(
                    """SELECT DISTINCT canonical_entity_key
                       FROM knowledge.production_destination_claim_evidence
                       WHERE canonical_entity_key = ANY(%s::TEXT[])""",
                    ([item.record_key for item in approved],),
                ).fetchall()
            }
            expected_keys = {item.record_key for item in approved}
            if visible_keys != expected_keys:
                raise ApprovalBlocked("signed claim mapping did not appear for every approved record")
            visible = len(visible_keys)
    finally:
        connection.close()
    print(json.dumps({"status": "published_to_disposable_staging", **result,
                      "visible_claim_rows": visible, "records": len(approved)}, sort_keys=True))


def _export_command(args) -> None:
    pack = load_candidate_content_pack()
    packet, approved = _verify_approval(args.decisions, pack)
    if not approved:
        raise ApprovalBlocked("no approved records exist for owner index export")
    connection = _guarded_operator_connection()
    try:
        records = _export_rows(connection, approved, packet.owner_approval.decided_at)
    finally:
        connection.close()
    if not records:
        raise ApprovalBlocked("approved production view returned no owner-index evidence")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(canonical_json_bytes(record) + b"\n" for record in records)
    args.output.write_bytes(payload)
    print(json.dumps({
        "status": "approved_jsonl_exported",
        "record_count": len(records),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "output": str(args.output),
        "index_command": "python -m owner_rag_api.cli build-index --source <approved.jsonl> --index-root <owner-private-index-root>",
    }, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("dry-run", help="offline: prove all queue decisions defer and no JSONL exists")
    template = sub.add_parser("template", help="write the fixed three-record review-only decision packet")
    template.add_argument("--output", type=Path, required=True)
    sign = sub.add_parser("sign-decisions", help="HMAC-sign a complete owner-reviewed decision file")
    sign.add_argument("--decisions", type=Path, required=True)
    sign.add_argument("--output", type=Path, required=True)
    sign.add_argument("--approver-name", required=True)
    sign.add_argument("--approver-role", required=True)
    sign.add_argument("--approval-reference", required=True)
    sign.add_argument("--decided-at", required=True, type=lambda value: __import__("datetime").datetime.fromisoformat(value.replace("Z", "+00:00")))
    sub.add_parser("stage-review", help="idempotently stage three pending proposals in guarded disposable PG17")
    publish = sub.add_parser("publish-approved", help="apply signed exact evidence mappings in guarded disposable PG17")
    publish.add_argument("--decisions", type=Path, required=True)
    publish.add_argument("--apply-owner-approval", action="store_true")
    export = sub.add_parser("export-owner-index", help="export current approved evidence to owner's exact JSONL contract")
    export.add_argument("--decisions", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        {
            "dry-run": _dry_run_command,
            "template": _template_command,
            "sign-decisions": _sign_command,
            "stage-review": _stage_command,
            "publish-approved": _publish_command,
            "export-owner-index": _export_command,
        }[args.command](args)
        return 0
    except (ApprovalBlocked, ValueError, OSError, psycopg.Error):
        print("BLOCKED: review workflow precondition failed; no approval was inferred.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
