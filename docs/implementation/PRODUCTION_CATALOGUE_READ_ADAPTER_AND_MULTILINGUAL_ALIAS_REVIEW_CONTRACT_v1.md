# Production Catalogue Read Adapter and Multilingual Alias Review Contract v1

**Status:** implemented read-only adapter; publication and locale-name coverage remain editorial gates.

## Read boundary and endpoint

`GET /api/v1/catalog/destinations` is a same-origin, public, read-only endpoint with no query, body, or traveler text. It reads only `knowledge.production_destinations` and verifies provenance through `knowledge.production_destination_sources`, using the existing `ai_tourism_app` role. It returns `{status: available, complete: true, count, items}` on success, including a successful zero-item response for an empty view. Database, malformed projection, manifest, timeout, and response-cap failures return the stable sanitized `503 {status: unavailable, error: {code: catalogue_unavailable}}` response. Internal database details are logged only as fixed event names.

The adapter retrieves at most 1,000 rows in deterministic destination-ID order, requesting 1,001 to detect overflow. It fails closed on overflow rather than silently omitting candidates; pagination is intentionally not offered because incomplete candidate sets could falsely produce unique resolutions. If the catalogue outgrows this cap, the contract needs reviewed pagination or server-side matching.

The projection contains the decimal-string destination ID, key, canonical name, reviewed locale display names and aliases, type, province, and city. Raw DB aliases are deliberately not selected: the existing `TEXT[]` is untagged and cannot safely support locale-aware matching. The adapter is geospatial-only because the production view requires valid location and coordinate role; foods, products, and other nonspatial knowledge need a separately approved publication/read contract.

The frontend sends no trip text, and uses only the same-origin path. Vite proxies `/api` to the local backend. The service worker bypasses API caching so an offline/stale response cannot masquerade as a current publication result. Empty and unavailable remain separate resolver states.

## Alias review manifest

The version-controlled review artifact is `engineering/database-prep/alias-review/manifest-v1.schema.json`; runtime projection is `backend/app/modules/catalog/destination_alias_manifest_v1.json`. Each record requires `destination_key`, `locale` (`fa-IR`, `en-US`, `ar`), `canonical_display_name`, `alias`, `alias_type`, `source_reference`, `editorial_status`, and `review_notes`. The checked-in runtime manifest is intentionally empty: no names or translations have been invented or approved. `engineering/database-prep/alias-review/visitiran-alias-proposals-v1.json` is a separate proposed-only curation package and is not read by the runtime.

Only explicitly `approved` records are projected. Every approved record needs a source reference and review notes. Canonical display-name entries must normalize to their alias. Same-identity, same-locale duplicate aliases after comparison normalization invalidate the manifest. Conflicts in canonical display names for the same identity and locale invalidate it. A spelling shared by different identities is retained so exact resolution reports ambiguity; it is never resolved by choosing the first/highest scoring candidate. Draft, in-review, rejected, and duplicate records are not emitted. Locale coverage is visible through nullable localized-name fields; missing locale coverage must be reported as a gap and is not filled by translation.

Comparison normalization is NFC, removes tatweel and zero-width join/word controls, normalizes Arabic yeh/alef maksura/kaf to the Persian yeh/kaf comparison forms, treats punctuation as separators, collapses whitespace, and lowercases Latin text. It does not rewrite stored names, remove Arabic diacritics, transliterate, translate, or fuzzy-match. Approved spelling variants and alternate-script names must be independently evidenced and reviewed before approval. The manifest is a curation artifact, not a database table; only approved values may later be compiled into the legacy aliases array. Locale-tagged persistence needs a separately reviewed schema decision if editorial operations outgrow this manifest.

## Test and release boundary

In-memory automated tests cover projection validation, exact resolver behavior, API success/empty/error contracts, and no request-text transfer. Database integration must additionally prove the publication view and application-role grants on isolated PostgreSQL instances. The shared development database is not a test target. The adapter does not make pending, synthetic, unverified, expired, revoked, or nonspatial records eligible, and does not change publication status.

There are no current production-ready destination identities until the approved view contains reviewed, spatial, provenance-backed records. Recommendation generation and RAG remain separate future work; stored knowledge documents/chunks or vector storage alone do not establish semantic retrieval readiness.
