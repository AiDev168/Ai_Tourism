# Destination Resolution and Clarification Contract v1

**Status:** deterministic client contract, read-only production catalogue adapter, and isolated resolver.

## Purpose and boundary

Trip intake extracts the traveler's destination phrase and preserves the complete original request. Resolution is a separate step that can return a canonical identity only when exactly one eligible production catalogue entry matches. A parsed phrase is never a verified identity by itself.

The current database model uses `knowledge.destinations.canonical_name`, `aliases TEXT[]`, `destination_key`, `destination_id`, `province_name`, `city_name`, `status`, `verification_status`, `record_origin`, `is_synthetic`, and source relationships. `aliases` is not locale-tagged and the catalogue has no structured canonical name columns for Persian, English, and Arabic. Each approved spelling therefore has to be present as a canonical name or alias. The resolver does not transliterate or call a translation service.

The only permitted production source is `knowledge.production_destinations` and its related `knowledge.production_destination_sources` provenance view. `GET /api/v1/catalog/destinations` now supplies a complete bounded projection to `ProductionDestinationCatalogPort` using the least-privilege app role; it does not query raw tables or staging/import tables. See `PRODUCTION_CATALOGUE_READ_ADAPTER_AND_MULTILINGUAL_ALIAS_REVIEW_CONTRACT_v1.md` for the API and alias curation contract.

The database was not accessed for this task. The local retrieval audit records zero rows in the production destination and provenance views as of its prior read-only verification; this is historical evidence, not a fresh count.

## Matching

Matching is exact after comparison-only normalization:

1. Apply Unicode NFC.
2. Remove Arabic tatweel and zero-width join/word controls.
3. Normalize Arabic/Persian `ي` and `ى` to Persian `ی`, and Arabic `ك` to Persian `ک`.
4. Treat punctuation and Unicode whitespace as separators, collapse repeated whitespace, trim, and lowercase Latin text.
5. Preserve Arabic diacritics. Do not apply NFKC, transliteration, translation, token containment, edit distance, semantic similarity, or best-score selection.

Normalization never changes the submitted text or returned canonical identity. If it causes two eligible identities to match the same phrase, the outcome is ambiguous. Approved aliases are evaluated alongside canonical names. Input in a different script matches only when that spelling is explicitly present in the catalogue's canonical name or aliases.

For a route, process every extracted phrase independently and in input order. Preserve repeated phrases and the exact original phrase for every item. Do not reorder or deduplicate route entries. The extractor may itself request clarification before resolution; no identity is returned for an ambiguous extracted phrase.

## Catalogue eligibility

A resolver candidate must come from the approved production boundary and satisfy all of:

- `status = active`;
- `verification_status = verified`;
- `record_origin = verified_external`;
- `is_synthetic = false`;
- verified, currently valid provenance exists.

The SQL production view already enforces these publication/provenance gates. The resolver repeats the relevant checks defensively. It rejects synthetic, `needs_review`, pending, unverified, wrong-boundary, or provenance-free candidates. It never changes a record's status.

## Result contract

`resolveDestinationNames(phrases, locale, catalogue)` returns the selected locale, an exact copy of the phrase list, an ordered result for each phrase, and an overall state:

| Item result | Meaning | User action |
|---|---|---|
| `resolved` | Exactly one eligible identity matched an exact normalized canonical name or alias | Show the canonical name and identity; never imply that unrelated facts were verified by this match |
| `ambiguous` | Two or more eligible identities matched | Ask a localized question quoting the original phrase; list only the eligible candidates, using catalogue canonical name/city/province fields and no invented descriptions; accept a transient choice or let the user revise the phrase |
| `confirmed` | The traveler explicitly selected one candidate from an ambiguous result | Keep the original phrase and record the selected canonical identity in transient request state; do not infer additional facts |
| `not-found` | An available, non-empty eligible catalogue had no exact match | Preserve the phrase and ask the traveler to correct or clarify it; no fuzzy fallback |
| `catalogue-empty` | The approved catalogue returned no eligible entries | State that no approved destination is currently available; preserve input and allow editing/retry |
| `catalogue-unavailable` | The catalogue adapter is absent, unreachable, or the supplied boundary is not the approved view | State that the name cannot currently be checked; preserve input and allow editing/retry |

The localized question and controls use `fa-IR`, `en-US`, or `ar` from the selected interface locale. Candidate names remain exactly as stored and use automatic text direction. The resolver never auto-selects the first candidate. A traveler radio choice becomes `confirmed` only if its ID is one of the eligible candidates returned in that ambiguous result. If no candidate is appropriate, the traveler edits the original natural-language request; no candidate is forced. Choices and requests remain transient and are cleared when the request changes.

## Current behavior and release dependencies

The UI invokes the contract with `catalogue-unavailable` because a production catalogue adapter is not present. It displays localized copy that the entered name remains unconfirmed. The pure resolver's match, collision, not-found, empty, eligibility, route-order, and normalization behavior is covered by isolated unit tests using in-memory fixtures only.

Before production resolution can be enabled:

1. Implement a read-only same-origin catalogue adapter over the approved production views, with timeouts and safe provider-neutral errors.
2. Decide how aliases will be reviewed and associated with Persian, English, and Arabic; current schema stores untagged aliases and does not guarantee all three languages.
3. Populate and editorially publish destinations with reviewed provenance; the last recorded production view count is zero.
4. Add adapter contract tests against isolated database states proving raw, synthetic, `needs_review`, and unverified rows cannot be returned.
5. Validate locale-specific disambiguation and accessibility in real browser states when production candidates exist.

No database migration, persistent trip API, semantic search, RAG, model call, or shared-database access is part of this contract implementation.
