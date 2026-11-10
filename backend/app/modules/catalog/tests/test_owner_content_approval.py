from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
import hashlib

from app.modules.catalog.content_pack import load_candidate_content_pack
from app.modules.catalog.owner_content_approval import (
    ApprovalBlocked,
    build_review_queue,
    bind_exact_content_mappings,
    approved_owner_record,
    sign_decision_packet,
    validate_decisions,
)
from scripts.rahgard_content_workflow import (
    REPOSITORY_ROOT,
    _approved_source_row,
    _export_rows,
    _validate_private_export_path,
    _write_json,
)
import scripts.rahgard_content_workflow as content_workflow

KEY = b"test-only-approval-key-material-32-bytes"
FIXTURE_TEXT = "TEST ONLY: source-backed content serialization fixture."
FIXTURE_CHUNK_HASH = hashlib.sha256(FIXTURE_TEXT.encode("utf-8")).hexdigest()


def _fully_approved_packet():
    pack = load_candidate_content_pack()
    packet = build_review_queue(pack)
    records = []
    for record in packet.records:
        records.append(record.model_copy(update={
            "decision": "approve",
            "pilot_scope_decision": "approve",
            "coordinate_use_decision": "approve",
            "locale_reviews": {locale: "approve" for locale in ("fa-IR", "en-US", "ar")},
            "sources": [source.model_copy(update={
                "rights_decision": "approve",
                "source_role": "primary" if source.source_id.startswith("UNESCO_") else "secondary",
                "approved_license": "Test-only documented permission",
                "attribution_text": "TEST ONLY",
            }) for source in record.sources],
            "claims": [claim.model_copy(update={
                "decision": "approve",
                "evidence_locations": [item.model_copy(update={
                    "document_key": f"{record.record_key}-doc-{item.locale}",
                    "document_sha256": "a" * 64,
                    "chunk_id": f"chunk-{record.record_key}-{item.locale}",
                    "chunk_sha256": FIXTURE_CHUNK_HASH,
                    "claim_key": claim.claim_id,
                }) for item in claim.evidence_locations],
            }) for claim in record.claims],
        }))
    packet = bind_exact_content_mappings(packet.model_copy(update={"records": records}))
    return pack, sign_decision_packet(
        packet,
        approver_name="QA Test Approver",
        approver_role="test-only",
        approval_reference="TEST-ONLY-DO-NOT-PUBLISH",
        decided_at=datetime.now(UTC),
        signing_key=KEY,
    )


def test_review_queue_defaults_every_choice_to_defer_and_never_approves():
    pack = load_candidate_content_pack()
    packet = build_review_queue(pack)
    assert [row.record_key for row in packet.records] == ["unesco-persepolis-v1"]
    assert all(row.decision == "defer" for row in packet.records)
    assert all(row.pilot_scope_decision == "defer" for row in packet.records)
    assert all(row.coordinate_use_decision == "defer" for row in packet.records)
    assert all(set(row.locale_reviews.values()) == {"defer"} for row in packet.records)
    assert set(packet.records[0].reviewed_name_by_locale) == {"fa-IR", "en-US", "ar"}
    assert len(packet.records[0].claims) == 2
    assert all(
        {location.locale for location in claim.evidence_locations} == {"fa-IR", "en-US", "ar"}
        and all(location.document_key is None and location.chunk_id is None
                for location in claim.evidence_locations)
        for claim in packet.records[0].claims
    )
    assert validate_decisions(pack, packet) == ()


def test_signed_complete_decisions_can_be_validated_without_publishing():
    pack, packet = _fully_approved_packet()
    approved = validate_decisions(pack, packet, signing_key=KEY)
    assert len(approved) == 1
    assert all(row.decision == "approve" for row in approved)


def test_unsigned_or_tampered_owner_decision_is_rejected():
    pack, packet = _fully_approved_packet()
    with pytest.raises(ApprovalBlocked, match="signature"):
        validate_decisions(pack, packet, signing_key=b"x" * 32)
    changed = packet.model_copy(update={
        "owner_approval": packet.owner_approval.model_copy(update={
            "approval_reference": "TAMPERED-REFERENCE"
        }),
    })
    with pytest.raises(ApprovalBlocked, match="signature"):
        validate_decisions(pack, changed, signing_key=KEY)


def test_changed_source_pack_hash_and_unknown_claim_fail_closed():
    pack, packet = _fully_approved_packet()
    changed_pack = pack.model_copy(deep=True)
    selected = next(
        item for item in changed_pack.existing_destination_enrichment_proposals
        if item.target_record_key == packet.records[0].record_key
    )
    selected.canonical_name += " edited"
    with pytest.raises(ApprovalBlocked, match="payload hash"):
        validate_decisions(changed_pack, packet, signing_key=KEY)
    changed_claim = packet.records[0].claims[0].model_copy(update={"claim_id": "unknown-claim"})
    changed = packet.model_copy(update={
        "records": [packet.records[0].model_copy(update={
            "claims": [changed_claim, *packet.records[0].claims[1:]]
        }), *packet.records[1:]]
    })
    with pytest.raises(ApprovalBlocked, match="claim decision set"):
        validate_decisions(pack, changed, signing_key=KEY)


def test_approval_requires_per_claim_locale_source_and_current_evidence_mapping():
    pack, packet = _fully_approved_packet()
    first = packet.records[0]
    missing_locale = first.claims[0].model_copy(update={
        "evidence_locations": first.claims[0].evidence_locations[:2]
    })
    changed = packet.model_copy(update={
        "records": [first.model_copy(update={
            "claims": [missing_locale, *first.claims[1:]]
        }), *packet.records[1:]]
    })
    # Decision content is signed; signing a malformed decision doesn't make it valid.
    resigned = sign_decision_packet(
        changed.model_copy(update={"owner_approval": None}),
        approver_name="QA Test Approver", approver_role="test-only",
        approval_reference="TEST-ONLY-DO-NOT-PUBLISH", decided_at=datetime.now(UTC),
        signing_key=KEY,
    )
    with pytest.raises(ApprovalBlocked, match="every locale"):
        validate_decisions(pack, resigned, signing_key=KEY)


def test_signed_claim_text_must_match_bound_chunk_identity():
    pack, packet = _fully_approved_packet()
    record = packet.records[0]
    first_claim = record.claims[0].model_copy(update={
        "reviewed_text_by_locale": {
            **record.claims[0].reviewed_text_by_locale,
            "en-US": "Altered after the evidence hash was bound.",
        }
    })
    changed = packet.model_copy(update={
        "owner_approval": None,
        "records": [record.model_copy(update={
            "claims": [first_claim, *record.claims[1:]],
        })],
    })
    resigned = sign_decision_packet(
        changed,
        approver_name="QA Test Approver", approver_role="test-only",
        approval_reference="TEST-ONLY-DO-NOT-PUBLISH", decided_at=datetime.now(UTC),
        signing_key=KEY,
    )
    with pytest.raises(ApprovalBlocked, match="identity or hash differs"):
        validate_decisions(pack, resigned, signing_key=KEY)


def test_owner_packet_is_bound_to_the_pre_review_canonical_identity():
    pack, packet = _fully_approved_packet()
    record = packet.records[0]
    changed_record = record.model_copy(update={
        "expected_existing_identity": record.expected_existing_identity.model_copy(update={
            "city_name": "Shiraz",
        }),
    })
    changed = packet.model_copy(update={"records": [changed_record]})
    with pytest.raises(ApprovalBlocked, match="identity snapshot differs"):
        validate_decisions(pack, changed, signing_key=KEY)


def test_owner_index_serializer_preserves_signed_review_time_and_hashes_text():
    reviewed = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    text = "TEST ONLY: evidence serializer contract fixture."
    import hashlib

    digest = hashlib.sha256(text.encode()).hexdigest()
    record = approved_owner_record(
        evidence_id="00000000-0000-0000-0000-000000000001",
        document_id="test-document",
        content_hash=digest,
        text=text,
        locale="fa-IR",
        canonical_entity_key="test-only-destination",
        claim_key="test.claim",
        source_rows=[{
            "source_id": 991,
            "source_name": "QA fixture",
            "source_url": "https://example.invalid/qa-fixture",
            "source_role": "test_only",
            "retrieved_at": datetime(2026, 11, 9, tzinfo=UTC),
            "valid_from": None,
            "valid_until": None,
            "license": "TEST ONLY",
        }],
        reviewed_at=reviewed,
    )
    assert record["publication_status"] == "published"
    assert record["reviewed_at"] == reviewed.isoformat()
    assert record["evidence"]["text"] == text
    assert record["evidence"]["content_hash"] == digest
    assert record["evidence"]["score"] is None
    assert record["evidence"]["sources"][0]["source_id"] == "991"


def test_owner_index_serializer_rejects_hash_mismatch_or_missing_sources():
    with pytest.raises(ApprovalBlocked, match="content hash"):
        approved_owner_record(
            evidence_id="id", document_id="doc", content_hash="a" * 64,
            text="unhashed", locale="fa-IR", canonical_entity_key="key",
            claim_key="claim", source_rows=[{}], reviewed_at=datetime.now(UTC),
        )


def test_index_export_groups_all_exact_source_rows_under_persisted_claim_identity():
    pack, packet = _fully_approved_packet()
    approved = validate_decisions(pack, packet, signing_key=KEY)
    chosen_record = next(
        item for item in packet.records
        if any(len(claim.source_ids) > 1 for claim in item.claims)
    )
    claim_decision = next(item for item in chosen_record.claims if len(item.source_ids) > 1)
    source_decisions = {item.source_id: item for item in chosen_record.sources}
    location = claim_decision.evidence_locations[0]
    expected_rows = []
    for number, source_id in enumerate(claim_decision.source_ids[:2], start=1):
        source = source_decisions[source_id]
        expected_rows.append({
            "canonical_entity_key": chosen_record.record_key,
            "claim_evidence_id": UUID(int=number),
            "document_id": location.document_key,
            "document_key": location.document_key,
            "document_sha256": location.document_sha256,
            "chunk_id": location.chunk_id,
            "chunk_sha256": location.chunk_sha256,
            "content_hash": location.chunk_sha256,
            "locale": location.locale,
            "corpus": "spatial_destinations",
            "claim_key": location.claim_key,
            "content": claim_decision.reviewed_text_by_locale[location.locale],
            "source_id": source_id,
            "source_name": f"Test source {number}",
            "source_url": source.source_url,
            "source_role": "test_only",
            "license": source.approved_license,
            "retrieved_at": datetime(2026, 11, 9, tzinfo=UTC),
            "valid_from": None,
            "valid_until": None,
        })

    class Result:
        def fetchall(self):
            return expected_rows

    class Connection:
        def execute(self, _sql, _params):
            return Result()

    output = _export_rows(Connection(), approved, packet.owner_approval.decided_at)
    assert len(output) == 1
    evidence = output[0]["evidence"]
    assert evidence["evidence_id"] == str(UUID(int=1))
    assert len(evidence["sources"]) == 2
    assert {row["source_url"] for row in evidence["sources"]} == {
        source_decisions[source_id].source_url for source_id in claim_decision.source_ids[:2]
    }


def test_private_owner_export_must_be_outside_checkout_and_must_not_overwrite(monkeypatch):
    with pytest.raises(ApprovalBlocked, match="outside the repository"):
        _validate_private_export_path(REPOSITORY_ROOT / "owner-index.jsonl")

    # Model a separate private export root without creating anything outside
    # the checkout or relying on the machine's restricted pytest temp folder.
    monkeypatch.setattr(content_workflow, "REPOSITORY_ROOT", REPOSITORY_ROOT / "backend" / "app")
    private_root = REPOSITORY_ROOT / "backend"
    monkeypatch.setenv("RAHGARD_OWNER_INDEX_DIR", str(private_root))
    existing = private_root / "scripts" / "rahgard_content_workflow.py"
    with pytest.raises(ApprovalBlocked, match="refusing to overwrite"):
        _validate_private_export_path(existing)
    with pytest.raises(FileExistsError):
        _write_json(existing, {"status": "test-only"})

    with pytest.raises(ApprovalBlocked, match="inside the configured private directory"):
        _validate_private_export_path(REPOSITORY_ROOT / "outside-owner-index.jsonl")

    target = private_root / ".pytest_cache" / "not-created-owner-index.jsonl"
    assert _validate_private_export_path(target) == target.resolve()


def test_existing_source_match_must_match_reviewed_identity():
    class Result:
        def fetchall(self):
            return [{
                "source_id": 42,
                "source_name": "Different source title",
                "source_type": "world_heritage_primary_record",
                "verification_status": "verified",
                "url": "https://whc.unesco.org/en/list/114",
                "is_synthetic": False,
            }]

    class Connection:
        def execute(self, _sql, _params):
            return Result()

    source = build_review_queue(load_candidate_content_pack()).records[0].sources[0]
    with pytest.raises(ApprovalBlocked, match="identity differs"):
        _approved_source_row(Connection(), source, "TEST-ONLY")
