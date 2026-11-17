from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApprovedDestinationAlias(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locale: Literal["fa-IR", "en-US", "ar"]
    value: str = Field(min_length=1, max_length=200)
    alias_type: Literal[
        "canonical_display_name", "spelling_variant", "alternate_script_name", "exonym"
    ]


class ProductionDestinationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_id: str = Field(pattern=r"^[0-9]+$")
    destination_key: str = Field(min_length=1, max_length=240)
    canonical_name: str = Field(min_length=1, max_length=240)
    localized_names: dict[Literal["fa-IR", "en-US", "ar"], str | None]
    aliases: list[ApprovedDestinationAlias] = Field(max_length=32)
    destination_type: str = Field(min_length=1, max_length=64)
    province_name: str = Field(min_length=1, max_length=240)
    city_name: str | None = Field(default=None, max_length=240)
    # This point is the coordinate role recorded for the approved spatial row.
    # It is deliberately not renamed to "entrance" or interpreted as a route.
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    coordinate_role: Literal[
        "unknown", "property_reference", "representative_point", "visitor_entrance"
    ] | None = None

    @model_validator(mode="after")
    def validate_coordinate_contract(self) -> "ProductionDestinationItem":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must both be present or both be null")
        if self.latitude is not None and self.coordinate_role in {None, "unknown"}:
            raise ValueError("a coordinate must preserve its known coordinate role")
        return self


class ProductionDestinationSource(BaseModel):
    """A provenance projection from the approved production source view."""

    model_config = ConfigDict(extra="forbid")

    destination_id: int = Field(ge=1)
    source_id: int = Field(ge=1)
    source_name: str = Field(min_length=1, max_length=500)
    source_url: str = Field(min_length=1, max_length=2048)
    source_role: str = Field(min_length=1, max_length=64)
    evidence_note: str | None = Field(default=None, max_length=2_000)
    retrieved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    reliability_score: float | None = Field(default=None, ge=0, le=1)


class ProductionDestinationTag(BaseModel):
    """A tag projected only for an eligible published spatial destination."""

    model_config = ConfigDict(extra="forbid")

    destination_id: int = Field(ge=1)
    tag: str = Field(min_length=1, max_length=200)


class AvailableDestinationCatalogue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available"] = "available"
    complete: Literal[True] = True
    count: int = Field(ge=0)
    items: list[ProductionDestinationItem]


class CatalogueError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["catalogue_unavailable"] = "catalogue_unavailable"


class CatalogueUnavailable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["unavailable"] = "unavailable"
    error: CatalogueError = Field(default_factory=CatalogueError)


class CulinaryClaimSource(BaseModel):
    """Source metadata included by the approved culinary publication view."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1, max_length=500)
    source_url: str = Field(min_length=1, max_length=2048)
    license: str | None = Field(default=None, max_length=500)
    source_role: str = Field(min_length=1, max_length=64)
    evidence_note: str | None = Field(default=None, max_length=2_000)
    retrieved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class CulinaryClaim(BaseModel):
    """One localized, source-backed non-spatial claim."""

    model_config = ConfigDict(extra="forbid")

    claim_key: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1, max_length=4_000)
    sources: list[CulinaryClaimSource] = Field(min_length=1, max_length=32)


class ProductionCulinaryItem(BaseModel):
    """Localized non-spatial item from the approved publication view."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=36, max_length=36)
    item_key: str = Field(min_length=1, max_length=240)
    category: str = Field(min_length=1, max_length=64)
    record_key: str = Field(min_length=1, max_length=240)
    locale: Literal["fa-IR", "en-US", "ar"]
    name: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=8_000)
    claims: list[CulinaryClaim] = Field(max_length=32)
    updated_at: datetime


class AvailableCulinaryCatalogue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available"] = "available"
    count: int = Field(ge=0)
    locale: Literal["fa-IR", "en-US", "ar"]
    items: list[ProductionCulinaryItem]
