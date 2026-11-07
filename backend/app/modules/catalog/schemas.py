from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApprovedDestinationAlias(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locale: Literal["fa-IR", "en-US", "ar"]
    value: str = Field(min_length=1, max_length=200)
    alias_type: Literal["canonical_display_name", "spelling_variant", "alternate_script_name", "exonym"]


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
