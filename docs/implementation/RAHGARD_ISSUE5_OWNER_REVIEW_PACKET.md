# Issue #5 — Shiraz/Fars owner-review decision packet

**Decision status: pending owner/editor review.** This packet is a review aid, not a content import, publication, license grant, or approval of Fars as pilot geography. It was assembled from the repository's existing `shiraz_fars_candidate_content_v2` research package, owner-work source register, and existing seed/document SQL. No source rows, canonical records, or production views were changed.

## Proposed small review set

The three entities below already have stable canonical keys. The two UNESCO properties are nearby Fars records, not Shiraz-city points. Their coordinates are property references, never visitor entrances. Names and descriptions in the source package are draft translations, not native editorial sign-off.

| Canonical key | Draft names (fa / en / ar) | Source-backed draft claims and exact sources | Current persisted content identity | Important unknowns / decisions |
|---|---|---|---|---|
| `unesco-persepolis-v1` | تخت جمشید؛ پارسه / Persepolis / تخت جمشيد؛ برسبوليس | `persepolis_518_bce`: UNESCO WHC 114, `https://whc.unesco.org/en/list/114/`; `persepolis_marvdasht_fars`: Visit Iran Persepolis profile plus UNESCO WHC 114, exact URLs in the v2 `SOURCE_REGISTER.csv`. | Document key `unesco-persepolis-v1-doc`; document SHA-256 `65e96c69e5e15917fa48825d88c2f740c073895b2eff48af2e37d996fb455454`. Existing chunk hashes: overview `1b48030acb3d67dc1b97d8c4a33aeadf7963de628a9e929c62d05dc76f15991f`; coordinate/limits `6d07684ae1f734ddaea47105ff6f5d083ec4a13881b9ed6a566392bbec52405c`. Source registry resolves exact URL to UNESCO descriptive/map rows; source page lists CC-BY-SA IGO 3.0, attribution and current terms require review. | Fars/Marvdasht locality; `property_reference` coordinate only. Entrance, hours, price, route, current access, safety and accessibility unknown. Confirm identity-to-document/claim mapping, reuse license/attribution, Persian wording, and English/Arabic review. |
| `unesco-pasargadae-v1` | پاسارگاد / Pasargadae / پاسارغاد | `pasargadae_first_capital`: UNESCO WHC 1106, `https://whc.unesco.org/en/list/1106/`; `pasargadae_landmarks`: same UNESCO property page. Map reference: `https://whc.unesco.org/en/list/1106/maps/`. | Document key `unesco-pasargadae-v1-doc`; document SHA-256 `b88aa1cb7a2755f0dec8b5951c96e09af0780a574ca28b7d04bdda84f477852a`. Existing chunk hashes: overview `d4aeec732938245fc1231eeef428bdf2362f489db43b589b1198cdc836ecff02`; ensemble/limits `58c497928e6dac6d0f03cb8a8d4b89857e102a8fb1489b6ff1863619d462da3b`. Source page displays CC-BY-SA IGO 3.0; attribution and current terms require review. | Fars; broad archaeological landscape. `property_reference` is not an entrance or route endpoint. Current access, internal transport, hours, price, accessibility, safety and seasonal restrictions unknown. Confirm scope/claim mapping, license/attribution and locale review. |
| `shiraz-eram-garden-v1` | باغ ارم / Eram Garden / حديقة إرم | `eram_location_and_history`: Visit Iran English and Persian garden pages (`https://visitiran.ir/attraction/eram-garden`, `https://visitiran.ir/fa/attraction/%D8%A8%D8%A7%D8%BA-%D8%A7%D8%B1%D9%85`); `eram_unesco_component`: Persian Visit Iran page. Coordinate source is separate Wikipedia secondary reference and is not evidence for access. | Existing key and document key `shiraz-eram-garden-v1-doc`; source record uses `https://en.wikipedia.org/wiki/Eram_Garden` for the existing compact profile; canonical coordinate role is `representative_point`. Candidate content does not establish a publication-approved document/claim/hash mapping. | In-city Shiraz. Representative point is not an entrance. Confirm identity, UNESCO component wording, source-use/license terms (not specified in Visit Iran register), exact claim/document mapping, native review, and whether the secondary coordinate should remain only for orientation. Access, hours, price, entrance, route, safety and accessibility unknown. |

The claim IDs shown are the candidate package's claim identifiers, not proof that an equivalent `claim_key` currently exists in the production projection. The existing knowledge schema contains document and chunk identities/hashes, but an owner/editor must approve the exact claim-to-chunk association before a RAG citation can be shown. A display-name match, URL match, or the `needs_review` canonical row is not sufficient.

## Required owner decisions

For each row, the owner/editor should record **approve / reject / revise / defer** for:

1. Pilot geography and whether each entity is in scope (including explicit acceptance of Persepolis/Pasargadae as nearby Fars day-trip candidates rather than Shiraz-city destinations).
2. Canonical key and identity; names and claim summaries in fa-IR, en-US and ar, with named native reviewers and review date.
3. Each factual claim and its exact evidence document/chunk/hash. Do not approve coordinates as entrances; decide whether the representative/property reference is useful for a map orientation view.
4. Source reuse terms, attribution text, and any commercial display permission. UNESCO pages identify CC-BY-SA IGO 3.0; confirm the applicable current terms. Visit Iran entries in the source register have no license field, so written permission/terms review is required before republication.
5. Publication scope: only explicitly approved claims/content may enter the ordinary traveler projection. Access, pricing, hours, route, safety, mobility and accessibility remain unknown until independently sourced and approved.

No approval is inferred from filling this table. Until signed decisions are recorded and applied through the existing controlled publication process, all three remain `needs_review` / pending and are not eligible for production recommendation output.

## Source and freshness ledger

- The v2 research register records Visit Iran and UNESCO sources retrieved `2026-11-08`; claims are paraphrases, not copied page text. The owner-work addendum records its source discovery on `2026-11-09`.
- Source pages must be re-opened before approval to confirm current content, URL identity and terms. Those recorded retrieval dates do not establish current opening/access status.
- UNESCO Persepolis and Pasargadae source entries are in `engineering/data-research/shiraz_fars_candidate_content_v2/SOURCE_REGISTER.csv` as `UNESCO_PERSEPOLIS`, `UNESCO_PERSEPOLIS_MAP`, `UNESCO_PASARGADAE`, and `UNESCO_PASARGADAE_MAP`. The v2 pack's corresponding references include `UNESCO_PERSEPOLIS`, `VISITIRAN_PERSEPOLIS`, `UNESCO_PASARGADAE`, and `UNESCO_PASARGADAE_MAP`.
- Eram's source identifiers are `VISITIRAN_ERAM_EN`, `VISITIRAN_ERAM_FA`, and `WIKI_COORD_SECONDARY` in the v2 source register.

## Review boundary

This packet does not stage data in PostgreSQL, alter the v2 research package, add source-registry records, create an approval, or enable RAG citation display. Existing seed SQL shows UNESCO descriptions as short Persian paraphrases and marks destination rows `needs_review`; the current production views should remain governed by their existing status/source-validity filters. Recheck those views only in a fresh disposable database as part of integration tests.

## Executable review gate

The machine-readable counterpart is produced by `backend/scripts/rahgard_content_workflow.py`. It is locked to the three canonical keys above, captures exact source-pack payload hashes and claim/source/locale decisions, and defaults every choice to `defer`.

From `backend/`, inspect the safe current state and write a template to a protected operator-selected path:

```powershell
uv run python scripts/rahgard_content_workflow.py dry-run
uv run python scripts/rahgard_content_workflow.py template --output C:\secure-review\rahgard-issue5-decisions.json
```

The dry run must report `candidate_records=3`, `deferred_records=3`, `approved_records=0`, `owner_index_jsonl_records=0`, `published=false`, and `indexed=false`. The template contains no approval and is not publishable. Keep completed decisions and HMAC key outside Git; provide `RAHGARD_CONTENT_APPROVAL_HMAC_KEY` through the owner’s approved secret-handling channel. `sign-decisions` will refuse incomplete approved records and will never create an approval itself.

`stage-review` uses only the `AUTH_TEST_DATABASE_*` guard and operator password from a fresh disposable PG17 runner. It reuses `stage_review_content_pack`, stages exactly three pending proposals, and verifies that destination/source/document/production row counts did not change. It never publishes.

`publish-approved --decisions <signed.json> --apply-owner-approval` requires the HMAC, exact unchanged pack hashes, independent publication visibility for each target destination/document/source, exact per-locale document/chunk hashes, and the explicit switch. It inserts only claim-evidence mappings in the guarded disposable staging DB. It cannot activate canonical destinations, sources, documents or chunks. Any missing production identity aborts the whole transaction.

`export-owner-index --decisions <signed.json> --output <approved.jsonl>` re-reads only the current approved claim/document/chunk/source projection and emits only the exact identities in that signed packet, using the signed review timestamp and persisted `claim_evidence_id`. If there are no approved rows it fails without writing output.

TourismRagApiV1 exposes no index-write HTTP endpoint. Its read-only, owner-operated ingestion command is:

```powershell
python -m owner_rag_api.cli build-index --source <approved.jsonl> --index-root <private-index-root>
python -m owner_rag_api.cli index-info --index-root <private-index-root>
```

The first command builds from the exact ApprovedRecord JSONL format and loads the already-cached local embedding model; it must only be run by the owner after approval and with the chosen private index path. The service is then restarted using its existing `serve --index-root ...` command. No HTTP writer, model load, index build, or service restart is executed by this task. The review queue remains entirely deferred until the owner returns a signed decision file.
