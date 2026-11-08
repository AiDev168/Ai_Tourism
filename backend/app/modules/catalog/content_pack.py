"""Read-only validation and deterministic planning for reviewed content packs.

This module deliberately contains no database connection or mutation path. A
controlled importer may consume its validated output after the schema and
least-privilege contracts are approved.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.modules.catalog.alias_manifest import normalize_alias

Locale = Literal["fa-IR", "en-US", "ar"]
RecordOrigin = Literal["verified_external"]
ReviewStatus = Literal["needs_review"]

DATASET_KEY = "shiraz_fars_candidate_content_v2"
DATASET_VERSION = "2.0.0"
EXPECTED_SPATIAL_PROPOSALS = 11
EXPECTED_CULINARY_PROPOSALS = 5
EXPECTED_SOURCES = 23
EXPECTED_LOCALES = frozenset({"fa-IR", "en-US", "ar"})


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClaimDraft(StrictModel):
    claim_id: str = Field(min_length=1, max_length=200)
    claim_by_locale: dict[Locale, str] | None = None
    text_by_locale: dict[Locale, str] | None = None
    source_ids: list[str] = Field(min_length=1, max_length=23)
    editorial_check: str | None = None

    @model_validator(mode="after")
    def one_localized_text_field(self) -> "ClaimDraft":
        if (self.claim_by_locale is None) == (self.text_by_locale is None):
            raise ValueError("claim must have exactly one localized text field")
        return self


class CoordinateDraft(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    coordinate_role: Literal["representative_point", "property_reference"]
    coordinate_status: str = Field(min_length=1, max_length=100)
    source_id: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1, max_length=2048)
    coordinate_cross_check_source_ids: list[str] = Field(default_factory=list, max_length=23)


class AccessProfile(StrictModel):
    access_modes: list[str] | None
    difficulty: str | None
    mobility_accessibility: str | None
    safety_restrictions: list[str] | None
    evidence_status: Literal["unknown_not_researched"]


class OperationalFacts(StrictModel):
    opening_hours: Any | None
    ticket_price: Any | None
    visit_duration_minutes: Any | None
    visitor_entrance: Any | None
    parking: Any | None
    public_transport: Any | None
    evidence_status: Literal["not_verified"]


class ProposalProvenance(StrictModel):
    source_ids: list[str] = Field(default_factory=list, max_length=23)
    record_origin: RecordOrigin
    verification_status: Literal["pending"]
    is_synthetic: Literal[False]
    status: ReviewStatus
    data_confidence: Literal[0.0]
    publishable: Literal[False]


class SpatialProposal(StrictModel):
    entity_kind: Literal["existing_destination_enrichment_proposal"]
    canonical_name: str = Field(min_length=1, max_length=240)
    names_by_locale: dict[Locale, str]
    destination_type: str = Field(min_length=2, max_length=64)
    province_name: str = Field(min_length=1, max_length=240)
    city_name: str | None = Field(max_length=240)
    geographic_scope: Literal["city_scope", "within_shiraz", "regional_day_trip"]
    description_by_locale_draft: dict[Locale, str]
    factual_claims: list[ClaimDraft] = Field(min_length=1, max_length=32)
    coordinates: CoordinateDraft
    access_profile: AccessProfile
    operational_facts: OperationalFacts
    provenance: ProposalProvenance
    editorial_notes: list[str] = Field(min_length=1, max_length=32)
    target_record_key: str = Field(min_length=1, max_length=240)
    record_action: Literal["stage_existing_record_enrichment_review"]
    target_resolution: dict[str, Any]
    record_key: str | None = None
    coordinate_apply_policy: Literal[
        "reference_only_never_overwrite_existing_coordinate",
        "UNESCO_property_reference_only_never_overwrite_existing_coordinate",
    ]


class DuplicateCheck(StrictModel):
    match_by: list[Literal["normalized_locale_names", "culinary_category"]]
    must_resolve_no_existing_duplicate_before_insert: Literal[True]
    if_match_found: Literal["stage_as_existing_record_enrichment_instead"]


class CulinaryProposal(StrictModel):
    entity_kind: Literal["non_spatial_culinary_knowledge"]
    record_key: str = Field(min_length=1, max_length=240)
    record_action: Literal[
        "stage_existing_record_enrichment_review", "stage_new_non_spatial_candidate_review"
    ]
    category: str = Field(min_length=2, max_length=64)
    name_by_locale: dict[Locale, str]
    description_by_locale_draft: dict[Locale, str]
    claims: list[ClaimDraft] = Field(min_length=1, max_length=32)
    dietary_and_allergen_data: Any | None
    venue_ids: list[str] = Field(max_length=64)
    provenance: ProposalProvenance
    editorial_notes: list[str] = Field(min_length=1, max_length=32)
    duplicate_check: DuplicateCheck | None = None


class SourceRecord(StrictModel):
    source_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2048)
    publisher: str = Field(min_length=1, max_length=500)
    source_type: str = Field(min_length=1, max_length=100)
    supports: list[str] = Field(min_length=1, max_length=64)
    retrieved_at: date
    license: str | None = None
    notes: str

    @field_validator("url")
    @classmethod
    def absolute_http_url(cls, value: str) -> str:
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("source URL must be absolute HTTP(S)")
        if parsed.username or parsed.password:
            raise ValueError("source URL cannot contain credentials")
        return value


class RegionalClaim(StrictModel):
    claim_id: str = Field(min_length=1, max_length=200)
    claim_by_locale: dict[Locale, str]
    source_ids: list[str] = Field(min_length=1, max_length=23)
    editorial_note: str = Field(min_length=1, max_length=2000)


class CandidateContentPack(StrictModel):
    dataset_key: Literal["shiraz_fars_candidate_content_v2"]
    version: Literal["2.0.0"]
    created_at: date
    scope: dict[str, Any]
    purpose: str = Field(min_length=1, max_length=1000)
    locale_contract: dict[str, Any]
    publication_contract: dict[str, Any]
    spatial_entities: list[Any]
    existing_destination_enrichment_proposals: list[SpatialProposal]
    non_spatial_knowledge: list[CulinaryProposal]
    regional_context_claims: list[RegionalClaim]
    source_register: list[SourceRecord]
    global_limitations: list[str] = Field(min_length=1, max_length=64)


class ContentPackUnavailable(ValueError):
    """Malformed, incomplete, or inconsistent owner-reviewed content package."""


class CandidateIdentityError(ValueError):
    """Exact identity or import idempotency precondition failed."""


def _require_locale_map(value: dict[str, str], label: str) -> None:
    if set(value) != EXPECTED_LOCALES or any(not text.strip() for text in value.values()):
        raise ContentPackUnavailable(f"{label} must contain nonblank fa-IR, en-US, and ar values")


def _csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, csv.Error):
        raise ContentPackUnavailable("review index could not be read") from None
    if not rows:
        raise ContentPackUnavailable("review index is empty")
    return rows


def _validate_package_consistency(
    pack: CandidateContentPack,
    entity_index: list[dict[str, str]],
    source_csv: list[dict[str, str]],
) -> None:
    if pack.spatial_entities:
        raise ContentPackUnavailable("unexpected new spatial entities are not permitted")
    if len(pack.existing_destination_enrichment_proposals) != EXPECTED_SPATIAL_PROPOSALS:
        raise ContentPackUnavailable("spatial proposal count does not match this reviewed package")
    if len(pack.non_spatial_knowledge) != EXPECTED_CULINARY_PROPOSALS:
        raise ContentPackUnavailable("culinary proposal count does not match this reviewed package")
    if len(pack.source_register) != EXPECTED_SOURCES:
        raise ContentPackUnavailable("source count does not match this reviewed package")
    if pack.locale_contract.get("locales") != ["fa-IR", "en-US", "ar"]:
        raise ContentPackUnavailable("package locale contract is not the approved three-locale set")
    if pack.locale_contract.get("translation_status") != "draft_human_review_required":
        raise ContentPackUnavailable("package translations must remain draft pending human review")
    expected_publication = {
        "record_origin": "verified_external",
        "verification_status": "pending",
        "is_synthetic": False,
        "status": "needs_review",
        "data_confidence": 0.0,
        "publishable": False,
    }
    if pack.publication_contract != expected_publication:
        raise ContentPackUnavailable("package publication contract must remain review-only")

    source_ids = [source.source_id for source in pack.source_register]
    source_urls = [source.url for source in pack.source_register]
    if len(set(source_ids)) != len(source_ids) or len(set(source_urls)) != len(source_urls):
        raise ContentPackUnavailable("source IDs and URLs must be unique within the package")
    known_sources = set(source_ids)
    proposal_ids: set[str] = set()
    for proposal in pack.existing_destination_enrichment_proposals:
        if proposal.target_record_key in proposal_ids:
            raise ContentPackUnavailable("spatial target keys must be unique")
        proposal_ids.add(proposal.target_record_key)
        _require_locale_map(proposal.names_by_locale, "spatial names")
        _require_locale_map(proposal.description_by_locale_draft, "spatial descriptions")
        if (
            proposal.target_resolution.get("expected_existing_record_key")
            != proposal.target_record_key
        ):
            raise ContentPackUnavailable("spatial target-resolution key mismatch")
        if proposal.target_resolution.get("must_resolve_exactly_one_existing_record") is not True:
            raise ContentPackUnavailable("spatial target must resolve exactly once")
        if proposal.target_resolution.get("must_not_insert_new_destination") is not True:
            raise ContentPackUnavailable("spatial import cannot create canonical destinations")
        if (
            proposal.target_resolution.get("must_not_mutate_published_or_canonical_record")
            is not True
        ):
            raise ContentPackUnavailable("spatial import cannot mutate canonical records")
        if (
            proposal.target_resolution.get("if_missing_or_conflicting")
            != "stop_and_report_identity_conflict"
        ):
            raise ContentPackUnavailable("spatial identity conflict must fail closed")
        if proposal.coordinates.source_id not in known_sources:
            raise ContentPackUnavailable("coordinate source is absent from source register")
        _require_known_sources(proposal.provenance.source_ids, known_sources)
        for claim in proposal.factual_claims:
            _require_locale_map(
                claim.claim_by_locale or claim.text_by_locale or {}, "spatial claim"
            )
            _require_known_sources(claim.source_ids, known_sources)

    culinary_keys: set[str] = set()
    for item in pack.non_spatial_knowledge:
        if item.record_key in culinary_keys:
            raise ContentPackUnavailable("culinary record keys must be unique")
        culinary_keys.add(item.record_key)
        _require_locale_map(item.name_by_locale, "culinary names")
        _require_locale_map(item.description_by_locale_draft, "culinary descriptions")
        if item.venue_ids or item.dietary_and_allergen_data is not None:
            raise ContentPackUnavailable("pack must not imply venue or dietary/allergen facts")
        for claim in item.claims:
            _require_locale_map(
                claim.claim_by_locale or claim.text_by_locale or {}, "culinary claim"
            )
            _require_known_sources(claim.source_ids, known_sources)
        if (
            item.record_action == "stage_new_non_spatial_candidate_review"
            and item.duplicate_check is None
        ):
            raise ContentPackUnavailable(
                "new culinary candidate requires its reviewed duplicate-check rule"
            )

    for claim in pack.regional_context_claims:
        _require_locale_map(claim.claim_by_locale, "regional claim")
        _require_known_sources(claim.source_ids, known_sources)

    indexed: dict[str, dict[str, str]] = {}
    for row in entity_index:
        key = row.get("record_key", "")
        if not key or key in indexed:
            raise ContentPackUnavailable("entity review index has blank or duplicate record keys")
        indexed[key] = row
    pack_keys = proposal_ids | culinary_keys
    if set(indexed) != pack_keys:
        raise ContentPackUnavailable(
            "entity review index keys differ from JSON candidate identities"
        )
    if (
        len(source_csv) != EXPECTED_SOURCES
        or {row.get("source_id") for row in source_csv} != known_sources
    ):
        raise ContentPackUnavailable("source CSV rows differ from JSON source register")

    # CSV remains a human-facing companion index. Check its review-only
    # classifications without treating localized labels as identity keys.
    for row in entity_index:
        if (
            row.get("verification_status") != "pending"
            or row.get("status") != "needs_review"
            or row.get("publishable", "").lower() != "false"
        ):
            raise ContentPackUnavailable(
                "entity review index contains a publishable or non-pending row"
            )


def _require_known_sources(source_ids: list[str], known: set[str]) -> None:
    if not source_ids or not set(source_ids) <= known:
        raise ContentPackUnavailable("content claim references an unknown source ID")


def load_candidate_content_pack(
    package_dir: Path | str | None = None,
) -> CandidateContentPack:
    """Load and validate the checked-in JSON and CSV companion files."""
    root = (
        Path(package_dir)
        if package_dir is not None
        else (
            Path(__file__).resolve().parents[4]
            / "engineering"
            / "data-research"
            / "shiraz_fars_candidate_content_v2"
        )
    )
    try:
        data = json.loads(
            (root / "shiraz_fars_candidate_content_v2.json").read_text(encoding="utf-8")
        )
        pack = CandidateContentPack.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError, ValueError):
        raise ContentPackUnavailable("candidate content JSON is unavailable or invalid") from None
    _validate_package_consistency(
        pack,
        _csv_rows(root / "entity_review_index.csv"),
        _csv_rows(root / "SOURCE_REGISTER.csv"),
    )
    return pack


def proposal_stable_key(dataset_key: str, version: str, record_key: str) -> str:
    """Version-scoped key for retry-safe imports without touching canonical data."""
    values = (dataset_key, version, record_key)
    if any(not value or any(char in value for char in "\r\n") for value in values):
        raise ContentPackUnavailable("invalid stable proposal identity")
    return ":".join(values)


def payload_sha256(payload: Any) -> str:
    """Hash an input JSON value deterministically, preserving all supplied claims."""
    try:
        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ContentPackUnavailable("proposal payload must be finite JSON data") from None
    return hashlib.sha256(encoded).hexdigest()


def resolve_exact_destination_id(
    target_record_key: str,
    existing_destinations: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> int:
    """Resolve a proposal only by its exact stable destination key.

    No canonical row is created or changed. Any missing/ambiguous key fails
    closed; display names and coordinates are never used as fallback identity.
    """
    matches = [
        row for row in existing_destinations if row.get("destination_key") == target_record_key
    ]
    if len(matches) != 1:
        raise CandidateIdentityError(
            "destination identity must resolve to exactly one existing key"
        )
    try:
        destination_id = int(matches[0]["destination_id"])
    except (KeyError, TypeError, ValueError):
        raise CandidateIdentityError("destination identity has an invalid database ID") from None
    if destination_id < 1 or str(matches[0]["destination_id"]) != str(destination_id):
        raise CandidateIdentityError("destination identity has an invalid database ID")
    return destination_id


def resolve_source_ids_exactly(
    pack: CandidateContentPack,
    existing_sources: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> dict[str, int]:
    """Map package source IDs by exact URL, requiring one pre-registered source.

    This function never creates source rows. The offline import is blocked when
    any source URL is missing or duplicated in the source registry.
    """
    result: dict[str, int] = {}
    for source in pack.source_register:
        matches = [row for row in existing_sources if row.get("url") == source.url]
        if len(matches) != 1:
            raise CandidateIdentityError(
                "each source URL must resolve to exactly one existing source"
            )
        try:
            source_id = int(matches[0]["source_id"])
        except (KeyError, TypeError, ValueError):
            raise CandidateIdentityError("source URL resolved to an invalid source ID") from None
        if source_id < 1 or str(matches[0]["source_id"]) != str(source_id):
            raise CandidateIdentityError("source URL resolved to an invalid source ID")
        result[source.source_id] = source_id
    return result


def resolve_optional_source_ids_exactly(
    pack: CandidateContentPack,
    existing_sources: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> dict[str, int | None]:
    """Resolve exact pre-registered sources; preserve unmatched refs as null.

    A duplicate URL is an identity conflict. A missing source remains a
    provenance snapshot with no FK; this helper never registers a source.
    """
    result: dict[str, int | None] = {}
    for source in pack.source_register:
        matches = [row for row in existing_sources if row.get("url") == source.url]
        if len(matches) > 1:
            raise CandidateIdentityError("source URL resolves to multiple existing sources")
        if not matches:
            result[source.source_id] = None
            continue
        try:
            source_id = int(matches[0]["source_id"])
        except (KeyError, TypeError, ValueError):
            raise CandidateIdentityError("source URL resolved to an invalid source ID") from None
        if source_id < 1 or str(matches[0]["source_id"]) != str(source_id):
            raise CandidateIdentityError("source URL resolved to an invalid source ID")
        result[source.source_id] = source_id
    return result


def resolve_new_culinary_duplicate(
    proposal: CulinaryProposal,
    existing_culinary_records: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> str | None:
    """Return the sole exact locale-name/category duplicate, or fail ambiguous.

    Name matching is locale-preserving and uses the repository's conservative
    Unicode normalization. There is no transliteration, translation, or fuzzy
    matching. A duplicate must be reviewed as enrichment, never inserted as a
    second culinary item automatically.
    """
    if proposal.record_action != "stage_new_non_spatial_candidate_review":
        return None
    candidate_names = {
        (locale, normalize_alias(name)) for locale, name in proposal.name_by_locale.items()
    }
    matches: set[str] = set()
    for row in existing_culinary_records:
        if row.get("category") != proposal.category:
            continue
        existing_names = row.get("name_by_locale")
        record_key = row.get("record_key")
        if (
            not isinstance(existing_names, dict)
            or not isinstance(record_key, str)
            or not record_key
        ):
            raise CandidateIdentityError("existing culinary identity projection is incomplete")
        keys = {
            (locale, normalize_alias(name))
            for locale, name in existing_names.items()
            if locale in EXPECTED_LOCALES and isinstance(name, str) and name.strip()
        }
        if candidate_names & keys:
            matches.add(record_key)
    if len(matches) > 1:
        raise CandidateIdentityError("culinary name/category duplicate is ambiguous")
    return next(iter(matches), None)


def import_disposition(
    stable_key: str,
    payload_hash: str,
    existing: dict[str, Any] | None,
) -> Literal["insert", "noop"]:
    """Classify one review-only retry; never update an existing row."""
    if existing is None:
        return "insert"
    if existing.get("payload_sha256") != payload_hash:
        raise CandidateIdentityError("stable proposal key already exists with different content")
    if (
        existing.get("review_status") not in {"needs_review", "pending_review"}
        or existing.get("publication_status") != "unpublished"
    ):
        raise CandidateIdentityError("reviewed or published proposal cannot be replaced or retried")
    if existing.get("proposal_key") != stable_key:
        raise CandidateIdentityError("stored proposal identity does not match the stable key")
    return "noop"
