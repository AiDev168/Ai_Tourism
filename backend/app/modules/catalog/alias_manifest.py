"""Validation and runtime projection of the reviewed, locale-tagged alias manifest."""

import unicodedata
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

ManifestLocale = Literal["fa-IR", "en-US", "ar"]
AliasType = Literal["canonical_display_name", "spelling_variant", "alternate_script_name", "exonym"]
EditorialStatus = Literal["proposed", "draft", "in_review", "approved", "rejected", "duplicate"]


class AliasManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_key: str = Field(min_length=1, max_length=240)
    locale: ManifestLocale
    canonical_display_name: str = Field(min_length=1, max_length=240)
    alias: str = Field(min_length=1, max_length=200)
    alias_type: AliasType
    source_reference: str = Field(min_length=1, max_length=1000)
    editorial_status: EditorialStatus
    review_notes: str = Field(max_length=2000)

    @field_validator("destination_key", "canonical_display_name", "alias", "source_reference")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class AliasManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_version: Literal[1]
    entries: list[AliasManifestEntry]


class ReviewedAliasSet(BaseModel):
    localized_names: dict[ManifestLocale, str | None]
    aliases: list[dict[str, str]]


class AliasManifestUnavailable(ValueError):
    """Malformed review data; details must not be exposed by the API."""


def normalize_alias(value: str) -> str:
    text = unicodedata.normalize("NFC", value)
    text = text.replace("\u0640", "")
    text = text.replace("\u200c", "").replace("\u200d", "").replace("\u2060", "")
    text = text.translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"}))
    text = "".join(" " if unicodedata.category(char).startswith("P") else char for char in text)
    return " ".join(text.split()).lower()


def _build_projection(manifest: AliasManifest) -> dict[str, ReviewedAliasSet]:
    approved = [entry for entry in manifest.entries if entry.editorial_status == "approved"]
    names: dict[str, dict[ManifestLocale, str]] = defaultdict(dict)
    aliases: dict[str, list[dict[str, str]]] = defaultdict(list)
    same_identity_aliases: set[tuple[str, ManifestLocale, str]] = set()

    for entry in approved:
        if not entry.source_reference.strip() or not entry.review_notes.strip():
            raise AliasManifestUnavailable("approved alias lacks review evidence")
        if entry.alias_type == "canonical_display_name" and normalize_alias(entry.alias) != normalize_alias(entry.canonical_display_name):
            raise AliasManifestUnavailable("canonical alias differs from its display name")
        key = (entry.destination_key, entry.locale, normalize_alias(entry.alias))
        if key in same_identity_aliases:
            raise AliasManifestUnavailable("duplicate normalized alias for one identity")
        same_identity_aliases.add(key)

        prior_name = names[entry.destination_key].get(entry.locale)
        if prior_name is not None and normalize_alias(prior_name) != normalize_alias(entry.canonical_display_name):
            raise AliasManifestUnavailable("conflicting canonical display names for one locale")
        names[entry.destination_key][entry.locale] = entry.canonical_display_name
        aliases[entry.destination_key].append({
            "locale": entry.locale,
            "value": entry.alias,
            "alias_type": entry.alias_type,
        })

    locales: tuple[ManifestLocale, ...] = ("fa-IR", "en-US", "ar")
    projection: dict[str, ReviewedAliasSet] = {}
    for destination_key, by_locale in names.items():
        reviewed_names = {locale: by_locale.get(locale) for locale in locales}
        reviewed_aliases = list(aliases[destination_key])
        alias_keys = {
            (entry["locale"], normalize_alias(entry["value"])) for entry in reviewed_aliases
        }
        for locale, display_name in by_locale.items():
            key = (locale, normalize_alias(display_name))
            if key not in alias_keys:
                reviewed_aliases.append({
                    "locale": locale,
                    "value": display_name,
                    "alias_type": "canonical_display_name",
                })
        projection[destination_key] = ReviewedAliasSet(
            localized_names=reviewed_names,
            aliases=reviewed_aliases,
        )
    return projection


@lru_cache(maxsize=1)
def load_reviewed_aliases() -> dict[str, ReviewedAliasSet]:
    manifest_path = Path(__file__).with_name("destination_alias_manifest_v1.json")
    try:
        manifest = AliasManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        return _build_projection(manifest)
    except (OSError, ValidationError, ValueError) as exc:
        raise AliasManifestUnavailable from exc
