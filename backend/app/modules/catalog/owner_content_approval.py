"""Signed, fail-closed editorial decisions for the small Issue #5 pilot set.

This module creates review inputs only. It cannot connect to a database, mutate
catalogue state, publish content, or invoke the owner RAG index builder.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import UTC, date, datetime
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID, NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.catalog.content_pack import CandidateContentPack, payload_sha256

PILOT_RECORD_KEYS = (
    "unesco-persepolis-v1",
)
LOCALES = ("fa-IR", "en-US", "ar")
DECISIONS = Literal["approve", "reject", "revise", "defer"]
APPROVAL_SCHEMA = "rahgard-owner-content-approval-v1"
_HEX_SHA256 = re.compile(r"^[a-f0-9]{64}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SourceDecision(StrictModel):
    source_id: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1, max_length=2048)
    source_title: str = Field(min_length=1, max_length=500)
    publisher: str = Field(min_length=1, max_length=500)
    source_type: str = Field(min_length=1, max_length=100)
    retrieved_at: date
    review_notes: str = Field(min_length=1, max_length=2000)
    rights_decision: DECISIONS = "defer"
    source_role: Literal["primary", "secondary", "verification", "discovery"] | None = None
    approved_license: str | None = Field(default=None, max_length=200)
    attribution_text: str | None = Field(default=None, max_length=1000)


class EvidenceLocation(StrictModel):
    locale: Literal["fa-IR", "en-US", "ar"]
    document_key: str | None = Field(default=None, max_length=240)
    document_sha256: str | None = Field(default=None, max_length=64)
    chunk_id: str | None = Field(default=None, max_length=240)
    chunk_sha256: str | None = Field(default=None, max_length=64)
    claim_key: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def require_complete_identity_or_empty(self) -> "EvidenceLocation":
        values = (
            self.document_key,
            self.document_sha256,
            self.chunk_id,
            self.chunk_sha256,
            self.claim_key,
        )
        if any(value is not None for value in values) and any(value is None for value in values):
            raise ValueError("evidence mapping identity must be fully specified")
        if self.document_sha256 and not _HEX_SHA256.fullmatch(self.document_sha256):
            raise ValueError("invalid document hash")
        if self.chunk_sha256 and not _HEX_SHA256.fullmatch(self.chunk_sha256):
            raise ValueError("invalid chunk hash")
        return self


class ClaimDecision(StrictModel):
    claim_id: str = Field(min_length=1, max_length=200)
    decision: DECISIONS = "defer"
    source_ids: list[str] = Field(min_length=1, max_length=23)
    reviewed_text_by_locale: dict[str, str]
    evidence_locations: list[EvidenceLocation] = Field(default_factory=list, max_length=3)


class CoordinateReview(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    coordinate_role: Literal["property_reference", "representative_point"]
    coordinate_source_id: str = Field(min_length=1, max_length=100)
    coordinate_source_url: str = Field(min_length=1, max_length=2048)
    caution: str = Field(min_length=1, max_length=1000)


class ExistingIdentitySnapshot(StrictModel):
    """Canonical Persepolis identity captured from the immutable approved seed."""

    canonical_name: str = Field(min_length=1, max_length=240)
    destination_type: str = Field(min_length=2, max_length=64)
    province_name: str = Field(min_length=1, max_length=240)
    city_name: str | None = Field(max_length=240)


class RecordDecision(StrictModel):
    record_key: str = Field(min_length=1, max_length=240)
    proposal_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_existing_identity: ExistingIdentitySnapshot
    reviewed_name_by_locale: dict[str, str]
    reviewed_description_by_locale: dict[str, str]
    coordinate_review: CoordinateReview
    decision: DECISIONS = "defer"
    pilot_scope_decision: DECISIONS = "defer"
    coordinate_use_decision: DECISIONS = "defer"
    locale_reviews: dict[str, DECISIONS]
    sources: list[SourceDecision] = Field(min_length=1, max_length=23)
    claims: list[ClaimDecision] = Field(min_length=1, max_length=32)


class OwnerApproval(StrictModel):
    approver_name: str = Field(min_length=1, max_length=200)
    approver_role: str = Field(min_length=1, max_length=120)
    decided_at: datetime
    approval_reference: str = Field(min_length=1, max_length=240)
    hmac_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def utc_timestamp(self) -> "OwnerApproval":
        if self.decided_at.tzinfo is None or self.decided_at.utcoffset() != UTC.utcoffset(self.decided_at):
            raise ValueError("approval timestamp must be UTC")
        return self


class OwnerDecisionPacket(StrictModel):
    schema_version: Literal["rahgard-owner-content-approval-v1"]
    dataset_key: str = Field(min_length=1, max_length=120)
    dataset_version: str = Field(min_length=1, max_length=40)
    owner_approval: OwnerApproval | None = None
    records: list[RecordDecision] = Field(min_length=1, max_length=1)

    @model_validator(mode="after")
    def one_persepolis_record_only(self) -> "OwnerDecisionPacket":
        if tuple(item.record_key for item in self.records) != PILOT_RECORD_KEYS:
            raise ValueError("this approval packet is limited to the Persepolis candidate")
        return self


class ApprovalBlocked(ValueError):
    """Decision packet is incomplete, stale, unsigned, or unsafe to apply."""


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def owner_document_key(record_key: str, locale: str) -> str:
    return f"rahgard-owner-{record_key}-{locale}"


def owner_document_id(record_key: str, locale: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"ai-tourism:owner-document:{record_key}:{locale}")


def owner_chunk_id(record_key: str, claim_key: str, locale: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"ai-tourism:owner-chunk:{record_key}:{claim_key}:{locale}")


def bind_exact_content_mappings(packet: OwnerDecisionPacket) -> OwnerDecisionPacket:
    """Bind every reviewed locale string to deterministic document/chunk IDs and hashes."""
    records = []
    for record in packet.records:
        if set(record.reviewed_description_by_locale) != set(LOCALES):
            raise ApprovalBlocked("reviewed descriptions must cover all three locales")
        claims = []
        for claim in record.claims:
            if set(claim.reviewed_text_by_locale) != set(LOCALES):
                raise ApprovalBlocked("reviewed claim text must cover all three locales")
            locations = [
                EvidenceLocation(
                    locale=locale,
                    document_key=owner_document_key(record.record_key, locale),
                    document_sha256=hashlib.sha256(
                        record.reviewed_description_by_locale[locale].encode("utf-8")
                    ).hexdigest(),
                    chunk_id=str(owner_chunk_id(record.record_key, claim.claim_id, locale)),
                    chunk_sha256=hashlib.sha256(
                        claim.reviewed_text_by_locale[locale].encode("utf-8")
                    ).hexdigest(),
                    claim_key=claim.claim_id,
                )
                for locale in LOCALES
            ]
            claims.append(claim.model_copy(update={"evidence_locations": locations}))
        records.append(record.model_copy(update={"claims": claims}))
    return packet.model_copy(update={"records": records})


def build_review_queue(pack: CandidateContentPack) -> OwnerDecisionPacket:
    """Return the single Persepolis owner-review row with all choices deferred."""
    proposals = {
        proposal.target_record_key: proposal
        for proposal in pack.existing_destination_enrichment_proposals
    }
    missing = set(PILOT_RECORD_KEYS) - set(proposals)
    if missing:
        raise ApprovalBlocked("fixed pilot queue does not match the loaded source pack")
    sources = {source.source_id: source for source in pack.source_register}
    records: list[RecordDecision] = []
    for key in PILOT_RECORD_KEYS:
        proposal = proposals[key]
        claim_rows = [
            ClaimDecision(
                claim_id=claim.claim_id,
                source_ids=list(claim.source_ids),
                reviewed_text_by_locale=claim.claim_by_locale or claim.text_by_locale or {},
                evidence_locations=[EvidenceLocation(locale=locale) for locale in LOCALES],
            )
            for claim in proposal.factual_claims
        ]
        coordinate_source_id = proposal.coordinates.source_id
        records.append(
            RecordDecision(
                record_key=key,
                proposal_sha256=payload_sha256(proposal.model_dump(mode="json")),
                expected_existing_identity=ExistingIdentitySnapshot(
                    canonical_name="تخت جمشید",
                    destination_type="archaeological_site",
                    province_name="فارس",
                    city_name=None,
                ),
                reviewed_name_by_locale=proposal.names_by_locale,
                reviewed_description_by_locale=proposal.description_by_locale_draft,
                coordinate_review=CoordinateReview(
                    latitude=proposal.coordinates.latitude,
                    longitude=proposal.coordinates.longitude,
                    coordinate_role=proposal.coordinates.coordinate_role,
                    coordinate_source_id=proposal.coordinates.source_id,
                    coordinate_source_url=proposal.coordinates.source_url,
                    caution=(
                        "UNESCO property-reference point only; not an entrance, route, "
                        "parking location, or access assertion."
                    ),
                ),
                locale_reviews={locale: "defer" for locale in LOCALES},
                sources=[
                    SourceDecision(
                        source_id=source_id,
                        source_url=sources[source_id].url,
                        source_title=sources[source_id].title,
                        publisher=sources[source_id].publisher,
                        source_type=sources[source_id].source_type,
                        retrieved_at=sources[source_id].retrieved_at,
                        review_notes=sources[source_id].notes,
                        source_role=None,
                    )
                    for source_id in sorted(
                        {source_id for claim in proposal.factual_claims for source_id in claim.source_ids}
                        | {coordinate_source_id}
                    )
                ],
                claims=claim_rows,
            )
        )
    return OwnerDecisionPacket(
        schema_version=APPROVAL_SCHEMA,
        dataset_key=pack.dataset_key,
        dataset_version=pack.version,
        records=records,
    )


def _canonical_for_signature(packet: OwnerDecisionPacket) -> bytes:
    data = packet.model_dump(mode="json", exclude={"owner_approval": {"hmac_sha256"}})
    return canonical_json_bytes(data)


def validate_decisions(
    pack: CandidateContentPack,
    packet: OwnerDecisionPacket,
    *,
    require_signature: bool = True,
    signing_key: bytes | None = None,
) -> tuple[RecordDecision, ...]:
    """Validate exact source-pack identity and return only fully approved records.

    A record is publishable only if the owner separately approves geography,
    coordinate use, all three locale reviews, every factual claim, and all
    source-rights decisions. Any changed payload or key fails closed.
    """
    if packet.dataset_key != pack.dataset_key or packet.dataset_version != pack.version:
        raise ApprovalBlocked("approval is for a different dataset version")
    if tuple(item.record_key for item in packet.records) != PILOT_RECORD_KEYS:
        raise ApprovalBlocked("approval records must exactly match the fixed pilot queue")
    expected = {
        item.target_record_key: item for item in pack.existing_destination_enrichment_proposals
    }
    known_sources = {source.source_id: source.url for source in pack.source_register}
    approved: list[RecordDecision] = []
    for decision in packet.records:
        proposal = expected[decision.record_key]
        digest = payload_sha256(proposal.model_dump(mode="json"))
        if not hmac.compare_digest(decision.proposal_sha256, digest):
            raise ApprovalBlocked("approval payload hash is stale")
        expected_claims = {claim.claim_id: claim for claim in proposal.factual_claims}
        if {claim.claim_id for claim in decision.claims} != set(expected_claims):
            raise ApprovalBlocked("claim decision set differs from source pack")
        if set(decision.reviewed_name_by_locale) != set(LOCALES) or any(
            not value.strip() for value in decision.reviewed_name_by_locale.values()
        ):
            raise ApprovalBlocked("reviewed display names must cover all locales")
        if set(decision.reviewed_description_by_locale) != set(LOCALES) or any(
            not value.strip() for value in decision.reviewed_description_by_locale.values()
        ):
            raise ApprovalBlocked("reviewed descriptions must cover all locales")
        expected_proposal = expected[decision.record_key]
        if decision.expected_existing_identity != ExistingIdentitySnapshot(
            canonical_name="تخت جمشید",
            destination_type="archaeological_site",
            province_name="فارس",
            city_name=None,
        ):
            raise ApprovalBlocked("reviewed canonical identity snapshot differs from the existing pilot record")
        expected_coordinate = expected_proposal.coordinates
        if (
            decision.coordinate_review.latitude != expected_coordinate.latitude
            or decision.coordinate_review.longitude != expected_coordinate.longitude
            or decision.coordinate_review.coordinate_role != expected_coordinate.coordinate_role
            or decision.coordinate_review.coordinate_source_id != expected_coordinate.source_id
            or decision.coordinate_review.coordinate_source_url != expected_coordinate.source_url
        ):
            raise ApprovalBlocked("coordinate review differs from the immutable candidate coordinate")
        expected_source_ids = {
            source_id
            for claim in proposal.factual_claims
            for source_id in claim.source_ids
        } | {proposal.coordinates.source_id}
        sources = {source.source_id: source for source in decision.sources}
        if set(sources) != expected_source_ids or any(
            sources[source_id].source_url != known_sources[source_id]
            or sources[source_id].source_title != next(
                item.title for item in pack.source_register if item.source_id == source_id
            )
            or sources[source_id].publisher != next(
                item.publisher for item in pack.source_register if item.source_id == source_id
            )
            or sources[source_id].source_type != next(
                item.source_type for item in pack.source_register if item.source_id == source_id
            )
            or sources[source_id].retrieved_at != next(
                item.retrieved_at for item in pack.source_register if item.source_id == source_id
            )
            for source_id in expected_source_ids
        ):
            raise ApprovalBlocked("source decision identities differ from source pack")
        for claim_decision in decision.claims:
            source_claim = expected_claims[claim_decision.claim_id]
            if set(claim_decision.reviewed_text_by_locale) != set(LOCALES) or any(
                not value.strip() for value in claim_decision.reviewed_text_by_locale.values()
            ):
                raise ApprovalBlocked("reviewed claim text must cover all locales")
            if set(claim_decision.source_ids) != set(source_claim.source_ids):
                raise ApprovalBlocked("claim source references differ from source pack")
            if len({item.locale for item in claim_decision.evidence_locations}) != len(
                claim_decision.evidence_locations
            ):
                raise ApprovalBlocked("duplicate locale evidence mapping")
        if decision.decision != "approve":
            continue
        if (
            decision.pilot_scope_decision != "approve"
            or decision.coordinate_use_decision != "approve"
            or set(decision.locale_reviews) != set(LOCALES)
            or any(decision.locale_reviews[locale] != "approve" for locale in LOCALES)
            or any(claim.decision != "approve" for claim in decision.claims)
            or any(source.rights_decision != "approve" for source in decision.sources)
        ):
            raise ApprovalBlocked("approved record has incomplete scope, claim, locale, or source review")
        for claim in decision.claims:
            mappings = {item.locale: item for item in claim.evidence_locations}
            if set(mappings) != set(LOCALES) or any(
                not all((item.document_key, item.document_sha256, item.chunk_id,
                         item.chunk_sha256, item.claim_key))
                for item in mappings.values()
            ):
                raise ApprovalBlocked("approved claim lacks exact evidence mapping for every locale")
            expected_content = bind_exact_content_mappings(
                OwnerDecisionPacket.model_validate(packet.model_dump(mode="python"))
            )
            expected_record = next(item for item in expected_content.records if item.record_key == decision.record_key)
            expected_claim = next(item for item in expected_record.claims if item.claim_id == claim.claim_id)
            if mappings != {item.locale: item for item in expected_claim.evidence_locations}:
                raise ApprovalBlocked("approved document/chunk identity or hash differs from reviewed text")
        for source in decision.sources:
            if not source.approved_license or not source.attribution_text:
                raise ApprovalBlocked("approved source lacks reviewed license and attribution")
            if source.source_role is None:
                raise ApprovalBlocked("approved source lacks an explicit destination-source role")
            parsed = urlsplit(source.source_url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ApprovalBlocked("approved source URL must be credential-free HTTPS")
        approved.append(decision)

    if not approved:
        # A signed decision may explicitly defer/reject/revise all records, but
        # such a packet authorizes no stage/publish/index side effect.
        return ()
    if require_signature:
        approval = packet.owner_approval
        if approval is None or approval.hmac_sha256 is None or signing_key is None:
            raise ApprovalBlocked("complete owner signature is required")
        if len(signing_key) < 32:
            raise ApprovalBlocked("approval verification key is too short")
        expected_signature = hmac.new(
            signing_key, _canonical_for_signature(packet), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(approval.hmac_sha256, expected_signature):
            raise ApprovalBlocked("owner decision signature is invalid")
        if approval.decided_at > datetime.now(UTC):
            raise ApprovalBlocked("owner decision timestamp is in the future")
    return tuple(approved)


def sign_decision_packet(
    packet: OwnerDecisionPacket,
    *,
    approver_name: str,
    approver_role: str,
    approval_reference: str,
    decided_at: datetime,
    signing_key: bytes,
) -> OwnerDecisionPacket:
    """Sign an explicit decision after exact pack validation by the caller."""
    if len(signing_key) < 32:
        raise ApprovalBlocked("approval signing key must contain at least 32 bytes")
    unsigned = packet.model_copy(update={
        "owner_approval": OwnerApproval(
            approver_name=approver_name,
            approver_role=approver_role,
            approval_reference=approval_reference,
            decided_at=decided_at,
        ),
    })
    signature = hmac.new(signing_key, _canonical_for_signature(unsigned), hashlib.sha256).hexdigest()
    return unsigned.model_copy(update={
        "owner_approval": unsigned.owner_approval.model_copy(update={"hmac_sha256": signature}),
    })


def approved_owner_record(
    *,
    evidence_id: str,
    document_id: str,
    content_hash: str,
    text: str,
    locale: str,
    canonical_entity_key: str,
    claim_key: str,
    source_rows: list[dict[str, object]],
    reviewed_at: datetime,
) -> dict[str, object]:
    """Serialize one database-approved claim into TourismRagApiV1 JSONL shape.

    Callers must supply rows read from the app's current production evidence
    view joined to its current production chunk/source views. This function
    validates invariants and performs no approval or publication itself.
    """
    if not source_rows or len(source_rows) > 20 or not text.strip() or len(text) > 12_000:
        raise ApprovalBlocked("approved evidence has an invalid source count")
    if not _HEX_SHA256.fullmatch(content_hash) or hashlib.sha256(text.encode("utf-8")).hexdigest() != content_hash:
        raise ApprovalBlocked("content hash does not match approved UTF-8 text")
    if locale not in LOCALES or reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise ApprovalBlocked("owner index record locale or review timestamp is invalid")
    if reviewed_at.utcoffset().total_seconds() != 0 or reviewed_at > datetime.now(UTC):
        raise ApprovalBlocked("owner review timestamp must be a nonfuture UTC instant")
    safe_id = re.compile(r"^[\w.:-]{1,160}$")
    if not all(safe_id.fullmatch(value) for value in (evidence_id, document_id, canonical_entity_key, claim_key)):
        raise ApprovalBlocked("owner index identity contains unsupported characters")
    source_payloads = []
    for source in source_rows:
        source_id = str(source["source_id"])
        source_name = source["source_name"]
        source_url = source["source_url"]
        source_role = source["source_role"]
        license_text = source["license"]
        parsed = urlsplit(source_url)
        if (
            not safe_id.fullmatch(source_id)
            or not isinstance(source_name, str) or not source_name.strip() or len(source_name) > 250
            or parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password
            or not isinstance(source_role, str) or not source_role.strip() or len(source_role) > 100
            or (license_text is not None and (not isinstance(license_text, str) or len(license_text) > 200))
        ):
            raise ApprovalBlocked("owner index source identity or license is invalid")
        for field_name in ("retrieved_at", "valid_from", "valid_until"):
            stamp = source[field_name]
            if stamp is not None and (
                stamp.tzinfo is None or stamp.utcoffset() is None
                or stamp.utcoffset().total_seconds() != 0
            ):
                raise ApprovalBlocked("owner index source timestamp is not UTC-aware")
        if source["retrieved_at"] is not None and source["retrieved_at"] > reviewed_at:
            raise ApprovalBlocked("source retrieval occurred after signed review")
        if (
            source["valid_from"] is not None and source["valid_until"] is not None
            and source["valid_from"] > source["valid_until"]
        ):
            raise ApprovalBlocked("source validity window is inverted")
        source_payloads.append({
            "source_id": source_id,
            "source_name": source_name,
            "source_url": source_url,
            "source_role": source_role,
            "retrieved_at": source["retrieved_at"].isoformat() if source["retrieved_at"] else None,
            "valid_from": source["valid_from"].isoformat() if source["valid_from"] else None,
            "valid_until": source["valid_until"].isoformat() if source["valid_until"] else None,
            "license": source["license"],
        })
    record = {
        "publication_status": "published",
        "verification_status": "verified",
        "source_registry_status": "active",
        "is_synthetic": False,
        "reviewed_at": reviewed_at.astimezone(UTC).isoformat(),
        "evidence": {
            "evidence_id": evidence_id,
            "document_id": document_id,
            "content_hash": content_hash,
            "text": text,
            "locale": locale,
            "corpus": "spatial_destinations",
            "canonical_entity_key": canonical_entity_key,
            "claim_key": claim_key,
            "score": None,
            "sources": source_payloads,
        },
    }
    return record
