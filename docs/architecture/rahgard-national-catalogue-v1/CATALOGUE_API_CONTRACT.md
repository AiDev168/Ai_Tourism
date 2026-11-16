# Scalable Catalogue API Contract

**Status:** additive API proposal. Preserve the existing endpoint and production-source safeguards. No endpoint or schema was changed in Stage 2A.

## 1. Existing endpoint and compatibility

Current route: `GET /api/v1/catalog/destinations` (`backend/app/api/catalogue.py`). It returns `AvailableDestinationCatalogue {status, count, items}` using `knowledge.production_destinations`, ordered by `destination_id`, and fails closed when the existing 1,000-item bound is exceeded. The current item includes destination ID/key/name/type, free-text province/city, coordinates and coordinate role; a reviewed alias manifest provides locale names/aliases. `Cache-Control: no-store` is set. Existing repository query requires verified provenance and limits `MAX_CATALOGUE_ITEMS=1000`.

Compatibility requirements:

1. Keep the route and existing item fields stable for one migration window; do not change ID types or remove `count`, `items`, `status`.
2. Add pagination fields (`page`, `next_cursor`, `has_more`) without removing the old envelope. `count` means returned page count after pagination, not global total; document this semantic change and add `total_count` only when deliberately computed cheaply. Prefer no exact total for large filtered queries.
3. Requests with no query parameters return the first default page. Existing clients that relied on a full catalogue must be migrated to follow cursors. Current production view is empty in the audit snapshot, and the known pilot has few rows; still ship frontend updates before raising the catalogue size limit.
4. Retain source/provenance validation, synthetic exclusion, publication status filters, role checks, read-only application DB role, bounded SQL timeout and fail-closed 503 behavior. Pagination must never query raw/unpublished candidate tables.
5. Return no-store for personalized/operational data. Public cache policy can be reconsidered only after an explicit content cache/version contract.

## 2. Request contract

`GET /api/v1/catalog/destinations`

| Query | Type / rule |
|---|---|
| `locale` | Optional enum `fa-IR`, `en-US`, `ar`; default `fa-IR` for existing Persian-first clients. Localization comes only from approved rows; if none, use current compatibility item fields and explicit null localized values. |
| `limit` | Integer 1–100; default 50. Reject, do not clamp. |
| `cursor` | Opaque server-signed cursor, max 2 KiB. Bound to filter fingerprint, sort version and expiry. Invalid, expired or mismatched cursor returns 400 `invalid_cursor`. |
| `q` | Optional trimmed Unicode search, 2–120 code points. Search approved canonical and approved alias/localized names only; parameterized query. |
| `province_code` | Optional exact official code resolved through approved `geo.admin_areas` release; mutually exclusive with `admin_area_id`. |
| `admin_area_id` | Optional positive integer. Query a reviewed area and descendants only where requested; `include_descendants` defaults true for province/county selectors. |
| `area_type` | Optional enum `province`, `county`, `district`, `city`, `locality`; validates that the requested ID matches. |
| `category` | Optional stable category key from existing approved category projection; one value per request in v1. |
| `bbox` | Optional WGS84 `west,south,east,north`; finite/range validated, south < north, west != east. Antimeridian crossing uses west > east explicitly. Uses GiST and tests exact inclusion semantics. |
| `around` + `radius_m` | Optional point `lat,lon` and radius 1–100,000 m; require both. Distance is search distance only, not road distance or visit feasibility. |
| `sort` | Enum `name`, `distance`; distance requires `around`; default name. `name` sort uses stable normalized display key and destination ID tie-break. |
| `include_descendants` | Boolean default true for administrative selector. |

Reject contradictory filters with 422 `invalid_filter`. Do not accept arbitrary SQL predicates, geometry WKT, raw destination IDs from untrusted RAG filters, or private attributes. Search normalization for Persian/Arabic is versioned; raw names are retained. Use B-tree indexes initially; add trigram/FTS indexes only after the extension and query plan are measured and approved. Geometry queries use GiST.

## 3. Response schema

```json
{
  "status": "available",
  "count": 1,
  "items": [
    {
      "destination_id": "123",
      "destination_key": "stable-canonical-key",
      "canonical_name": "نام اصلی",
      "localized_name": "Display name",
      "locale": "en-US",
      "destination_type": "tourism_point",
      "province_name": "existing compatibility value",
      "city_name": null,
      "admin_area": {"id": 10, "type": "county", "name": "...", "code": "..."},
      "latitude": 0.0,
      "longitude": 0.0,
      "coordinate_role": "property_reference",
      "access_points": [],
      "categories": [],
      "has_verified_provenance": true
    }
  ],
  "next_cursor": "opaque-or-null",
  "has_more": false,
  "sort_version": "catalog-name-v1"
}
```

`access_points` contains only individually approved points and their explicit role. Do not label a `property_reference` as an entrance. Omit unpublished source details from catalogue list responses unless a separate citation endpoint authorizes the public projection. Never include raw records, internal review notes, operational freshness internals, private partner rows or source tokens.

Unavailable response remains a typed 503 with a request ID and safe code. Empty `items` with `status=available` is a valid empty catalogue, distinct from unavailable. Cursor malformed, unsupported locale and invalid filters return typed 4xx; DB/view failures return safe 503, not empty success.

## 4. Cursor and ordering semantics

Cursor payload contains `cursor_version`, sort version, last sort key (and destination ID), filter hash, locale, and expiry; sign with a server-side rotating key. Do not encode PII or return raw SQL. The query uses keyset pagination; no OFFSET for deep pages. For name order, `(normalized_search_name, destination_id)` is stable. For distance, `(distance_m, destination_id)` is stable and distance semantics are spherical/geodesic; return distance only if product needs it and label it straight-line. A cursor cannot be reused with changed filters/locale/sort. Deleted/withdrawn rows are naturally omitted from the published view; duplicates do not cross pages.

## 5. Admin-area query semantics

Use `admin_area_id` for the selected canonical node in the latest approved hierarchy. Descendant expansion joins one exact release tree. If no reviewed mapping exists on a destination, it is not assigned to a guessed county; it may still appear in unfiltered results if otherwise publishable and retains legacy free-text location. Use source release code, not a human spelling, as API filter identity. Aliases are search/display support only, not proof of administrative mapping.

## 6. Itinerary-engine access

The itinerary/recommendation service should call a bounded internal repository operation with approved filters and explicit IDs/limit. It should not call the public endpoint over HTTP from inside the monolith or load the whole national table. Eligibility remains deterministic and evaluates hard constraints against known, current, published attributes. A national directory page does not itself qualify a destination for a recommendation. The existing recommendation APIs retain their contracts until versioned separately; cursor pagination applies to browsing/discovery, while itinerary candidate selection uses a capped filtered query and stable order.

## 7. Rollout and compatibility tests

1. Add migration views/indexes and contract tests first; preserve the old unfiltered route shape.
2. Add pagination fields, default limit and cursor; test old client parsing.
3. Upgrade client to request cursor pages and stop when `has_more=false`.
4. Remove the 1,000-all-items assumption only after telemetry shows no old client dependency. Keep a hard max limit.
5. Test pages on tied names, Persian/Arabic normalization, same sort values, withdrawn records between page reads, changed filters, malformed/expired cursor, antimeridian BBOX, admin-area descendants, missing admin mapping, source revoked between requests, synthetic rows and DB outage.
