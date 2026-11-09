"""Versioned validation for the separate Shiraz/Fars content addendum.

This contract intentionally does not alter the fixed v2 candidate pack. The
validated records are review proposals only and are never canonical catalogue
rows or traveler-facing content.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Locale = Literal["fa-IR", "en-US", "ar"]
DATASET_KEY = "shiraz_fars_candidate_content_addendum_v1"
DATASET_VERSION = "1.0.0"
EXPECTED_PROPOSALS = 4
EXPECTED_LOCALES = {"fa-IR", "en-US", "ar"}
EXPECTED_KEYS = {
    "shiraz-delgosha-garden-v1",
    "shiraz-afifabad-garden-v1",
    "shiraz-shah-cheragh-v1",
    "shiraz-naqsh-e-rostam-v1",
}


class AddendumModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AddendumClaim(AddendumModel):
    claim_id: str = Field(min_length=1, max_length=200)
    claim_by_locale: dict[Locale, str]
    source_ids: list[str] = Field(min_length=1, max_length=20)

    @field_validator("claim_by_locale")
    @classmethod
    def localized_claim(cls, value: dict[str, str]) -> dict[str, str]:
        _locale_map(value, "claim")
        return value


class AddendumProposal(AddendumModel):
    record_key: str = Field(min_length=1, max_length=240)
    target_record_action: Literal["stage_existing_record_enrichment_review"]
    canonical_name: str = Field(min_length=1, max_length=240)
    names_by_locale: dict[Locale, str]
    destination_type: str = Field(min_length=1, max_length=64)
    province_name: str = Field(min_length=1, max_length=240)
    city_name: str = Field(min_length=1, max_length=240)
    geographic_scope: Literal["within_shiraz", "regional_day_trip"]
    description_by_locale_draft: dict[Locale, str]
    factual_claims: list[AddendumClaim] = Field(min_length=1, max_length=32)
    coordinate_policy: str = Field(min_length=1, max_length=1_000)
    unknown_fields: list[str] = Field(min_length=1, max_length=32)
    editorial_notes: list[str] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_proposal_locales(self) -> "AddendumProposal":
        _locale_map(self.names_by_locale, "names")
        _locale_map(self.description_by_locale_draft, "draft descriptions")
        if self.record_key == "shiraz-naqsh-e-rostam-v1" and (
            self.city_name != "Marvdasht" or self.geographic_scope != "regional_day_trip"
        ):
            raise ValueError("regional identity must remain scoped to Marvdasht")
        return self


class AddendumSource(AddendumModel):
    source_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2048)
    publisher: str = Field(min_length=1, max_length=500)
    source_type: str = Field(min_length=1, max_length=100)
    language: str = Field(min_length=2, max_length=16)
    retrieved_at: date
    supports: list[str] = Field(min_length=1, max_length=64)
    limitations: str = Field(min_length=1, max_length=2_000)

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


class AddendumPack(AddendumModel):
    dataset_key: Literal["shiraz_fars_candidate_content_addendum_v1"]
    version: Literal["1.0.0"]
    created_at: date
    purpose: str = Field(min_length=1, max_length=1_000)
    locale_contract: dict[str, object]
    publication_contract: dict[str, object]
    import_contract: dict[str, object]
    spatial_entities: list[AddendumProposal]
    source_register: list[AddendumSource]
    global_limitations: list[str] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_review_only_contract(self) -> "AddendumPack":
        if self.locale_contract != {
            "locales": ["fa-IR", "en-US", "ar"],
            "translation_status": "draft_human_review_required",
        }:
            raise ValueError("locales must remain draft for human review")
        expected_publication = {
            "record_origin": "verified_external",
            "verification_status": "pending",
            "is_synthetic": False,
            "status": "needs_review",
            "data_confidence": 0.0,
            "publishable": False,
        }
        if self.publication_contract != expected_publication:
            raise ValueError("addendum must remain unverified and non-publishable")
        if self.import_contract != {
            "record_action": "stage_existing_record_enrichment_review",
            "must_resolve_exactly_one_existing_record": True,
            "must_not_insert_new_destination": True,
            "must_not_mutate_canonical_record": True,
            "if_target_missing_or_conflicting": "stop_and_report_identity_conflict",
        }:
            raise ValueError("addendum import boundary is not the reviewed exact-match contract")
        keys = [item.record_key for item in self.spatial_entities]
        if len(keys) != EXPECTED_PROPOSALS or set(keys) != EXPECTED_KEYS:
            raise ValueError("addendum must contain exactly the four reviewed target keys")
        source_ids = [item.source_id for item in self.source_register]
        source_urls = [item.url for item in self.source_register]
        if len(set(source_ids)) != len(source_ids) or len(set(source_urls)) != len(source_urls):
            raise ValueError("source IDs and URLs must be unique")
        known = set(source_ids)
        for proposal in self.spatial_entities:
            if proposal.target_record_action != "stage_existing_record_enrichment_review":
                raise ValueError("only existing-record enrichment proposals are permitted")
            for claim in proposal.factual_claims:
                if not claim.source_ids or not set(claim.source_ids) <= known:
                    raise ValueError("every factual claim must retain known source references")
        return self


class ContentAddendumUnavailable(ValueError):
    """Addendum files are malformed, inconsistent, or not the expected version."""


def _locale_map(value: dict[str, str], label: str) -> None:
    if set(value) != EXPECTED_LOCALES or any(not text.strip() for text in value.values()):
        raise ValueError(f"{label} must contain nonblank fa-IR, en-US, and ar values")


def _parse_supports(value: str) -> list[str]:
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        raise ContentAddendumUnavailable("source register supports field is invalid") from None
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        raise ContentAddendumUnavailable("source register supports field is invalid")
    return parsed


def _validate_source_csv(pack: AddendumPack, rows: list[dict[str, str]]) -> None:
    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        source_id = row.get("source_id", "")
        if not source_id or source_id in by_id:
            raise ContentAddendumUnavailable("source CSV has blank or duplicate identifiers")
        by_id[source_id] = row
    if set(by_id) != {item.source_id for item in pack.source_register}:
        raise ContentAddendumUnavailable("source CSV keys differ from JSON source register")
    for source in pack.source_register:
        row = by_id[source.source_id]
        if any(
            row.get(key) != expected
            for key, expected in (
                ("title", source.title),
                ("url", source.url),
                ("publisher", source.publisher),
                ("source_type", source.source_type),
                ("language", source.language),
                ("retrieved_at", source.retrieved_at.isoformat()),
                ("limitations", source.limitations),
            )
        ) or _parse_supports(row.get("supports", "")) != source.supports:
            raise ContentAddendumUnavailable("source CSV metadata differs from JSON source register")


def load_content_addendum(package_dir: Path | str | None = None) -> AddendumPack:
    """Load the v1 addendum, requiring its JSON and source CSV to agree."""
    root = Path(package_dir) if package_dir is not None else (
        Path(__file__).resolve().parents[4]
        / "engineering" / "data-research" / "shiraz_fars_candidate_content_addendum_v1"
    )
    try:
        payload = json.loads((root / "spatial_enrichment_addendum_v1.json").read_text(encoding="utf-8"))
        pack = AddendumPack.model_validate(payload)
        with (root / "SOURCE_REGISTER.csv").open("r", encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, csv.Error, json.JSONDecodeError, ValidationError, TypeError, ValueError):
        raise ContentAddendumUnavailable("content addendum is unavailable or invalid") from None
    _validate_source_csv(pack, rows)
    return pack


def addendum_payload_hash(proposal_payload: dict[str, object]) -> str:
    """Hash canonical UTF-8 JSON; includes source snapshots added by importer."""
    try:
        encoded = json.dumps(
            proposal_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ContentAddendumUnavailable("addendum proposal payload is invalid") from None
    return hashlib.sha256(encoded).hexdigest()
