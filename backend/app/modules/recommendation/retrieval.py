"""Exact structured candidate retrieval over the approved catalogue projection.

This is a bounded deterministic catalogue search seam, not semantic RAG. It
never opens a database connection; production callers supply projections from
the approved production views.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.modules.catalog.alias_manifest import normalize_alias
from app.modules.catalog.schemas import ProductionDestinationItem

_AREA_TYPES = {"city", "town", "region", "province"}
_MAX_CANDIDATES = 1_000


@dataclass(frozen=True, slots=True)
class StructuredDestinationMetadata:
    """Optional tag projection from approved production metadata views.

    The source view does not carry tag locale metadata. Terms are compared only
    as exact normalized strings and never translated or transliterated.
    """

    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateRetrievalQuery:
    selected_destination_ids: tuple[str, ...]
    interests: tuple[str, ...]
    locale: str
    limit: int = _MAX_CANDIDATES


@dataclass(frozen=True, slots=True)
class RetrievedDestination:
    destination: ProductionDestinationItem
    selected_destination_id: str
    request_order: int
    scope_match: str
    matched_interest_terms: tuple[str, ...]


class StructuredDestinationCandidateRetrievalPort(Protocol):
    """Injectable candidate-retrieval seam for the deterministic decision core."""

    def retrieve(
        self,
        *,
        query: CandidateRetrievalQuery,
        catalogue: Sequence[ProductionDestinationItem],
        metadata_by_destination: Mapping[str, StructuredDestinationMetadata],
    ) -> list[RetrievedDestination]: ...


class ApprovedCatalogueCandidateRetriever:
    """Retrieve exact selected identities and, for an explicit area, its places."""

    def retrieve(
        self,
        *,
        query: CandidateRetrievalQuery,
        catalogue: Sequence[ProductionDestinationItem],
        metadata_by_destination: Mapping[str, StructuredDestinationMetadata],
    ) -> list[RetrievedDestination]:
        if query.limit < 1 or query.limit > _MAX_CANDIDATES:
            raise ValueError("candidate retrieval limit is outside the supported bound")

        by_id: dict[str, ProductionDestinationItem] = {}
        for item in catalogue:
            prior = by_id.get(item.destination_id)
            if prior is not None and prior != item:
                raise ValueError("conflicting production catalogue identities")
            by_id[item.destination_id] = item

        hits: list[RetrievedDestination] = []
        seen: set[str] = set()
        normalized_interests = tuple(
            (raw, normalize_alias(raw)) for raw in query.interests if raw.strip()
        )

        for request_order, selected_id in enumerate(query.selected_destination_ids):
            selected = by_id.get(selected_id)
            if selected is None:
                continue
            selected_type = selected.destination_type.strip().casefold()
            selected_names = _selected_display_names(selected, query.locale)
            city_scope = selected_type in {"city", "town"}
            province_scope = selected_type in {"region", "province"}
            broad_area = city_scope or province_scope
            normalized_names = {normalize_alias(name) for name in selected_names}

            for item in catalogue:
                if item.destination_id in seen:
                    continue
                direct = item.destination_id == selected_id
                # A selected city/region is the hard geographic scope, not a
                # POI recommendation or itinerary stop itself.
                if direct and broad_area:
                    continue
                area_value = item.city_name if city_scope else item.province_name
                area_match = bool(
                    broad_area
                    and area_value
                    and normalize_alias(area_value) in normalized_names
                )
                if not direct and not area_match:
                    continue

                item_metadata = metadata_by_destination.get(
                    item.destination_id, StructuredDestinationMetadata()
                )
                normalized_tags = {normalize_alias(tag) for tag in item_metadata.tags if tag.strip()}
                matched = tuple(
                    raw for raw, normalized in normalized_interests if normalized and normalized in normalized_tags
                )
                scope = "explicit_identity" if direct else "explicit_area"
                # A city/region match is allowed only when the selected entity
                # itself explicitly represents that broad area.
                hits.append(RetrievedDestination(item, selected_id, request_order, scope, matched))
                seen.add(item.destination_id)
                if len(hits) >= query.limit:
                    return hits
        return hits


def _selected_display_names(item: ProductionDestinationItem, locale: str) -> tuple[str, ...]:
    names = [item.canonical_name]
    localized = item.localized_names.get(locale)
    if localized:
        names.append(localized)
    names.extend(alias.value for alias in item.aliases)
    return tuple(names)

