"""Typed contracts for deterministic, publication-gated recommendations."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Locale = Literal["fa-IR", "en-US", "ar"]


class EvidenceSource(BaseModel):
    """A source row projected by the approved production provenance view."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    destination_id: int = Field(gt=0)
    source_id: int = Field(gt=0)
    source_name: str = Field(min_length=1, max_length=240)
    source_url: str = Field(min_length=1, max_length=1_000)
    source_role: str = Field(min_length=1, max_length=64)
    evidence_note: str | None = Field(default=None, max_length=2_000)
    reliability_score: float | None = Field(default=None, ge=0, le=1)
    retrieved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    @field_validator("source_url")
    @classmethod
    def require_http_source_url(cls, value: str) -> str:
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise ValueError("source_url must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password:
            raise ValueError("source_url must not contain credentials")
        return value


class RecommendedDestination(BaseModel):
    """One eligible catalogue identity and the provenance supporting it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    destination_id: str = Field(pattern=r"^[0-9]+$")
    rank: int = Field(ge=1, le=1_000)
    # This represents an exact requested-identity match, not quality or truth confidence.
    final_score: float = Field(ge=0, le=1)
    matched_requirements: list[str] = Field(max_length=16)
    unknown_fields: list[str] = Field(max_length=16)
    warnings: list[str] = Field(max_length=16)
    explanation_key: Literal["explicit_destination_match", "published_area_candidate"]
    score_components: list["RankingComponent"] = Field(max_length=4)
    evidence: list[EvidenceSource] = Field(min_length=1, max_length=32)


class RankingComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    component_key: Literal["destination_scope", "exact_interest_tag_match"]
    raw_score: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)
    weighted_score: float = Field(ge=0, le=1)
    matched_terms: list[str] = Field(max_length=32)


class RecommendationOutcome(BaseModel):
    """Stable service result; empty and clarification outcomes are not failures."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["available", "empty", "needs_confirmation"]
    algorithm_version: Literal["structured-catalogue-ranking-v2"] = "structured-catalogue-ranking-v2"
    retrieval_version: Literal["approved-structured-catalogue-v2"] = "approved-structured-catalogue-v2"
    reason_code: str | None = Field(default=None, max_length=64)
    unresolved_fields: list[str] = Field(default_factory=list, max_length=32)
    duration_days: int | None = Field(default=None, ge=1, le=365)
    items: list[RecommendedDestination] = Field(max_length=1_000)

