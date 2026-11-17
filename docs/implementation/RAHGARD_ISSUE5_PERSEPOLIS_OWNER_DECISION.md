# Persepolis — owner publication decision

**Status: pending explicit factual/editorial/rights approval.** GitHub Issue #5 approved the Shiraz/Fars scope and selected Persepolis as the first candidate for review only. It did not approve factual claims, fa-IR/en-US/ar copy, source reuse, licenses, attribution, coordinate use, publication, or indexing.

This single-record decision packet supersedes the older three-record review set for the current execution. The executable queue is fixed to `unesco-persepolis-v1`; Pasargadae and Eram are excluded.

## Existing canonical identity

- Exact key: `unesco-persepolis-v1`.
- Current canonical Persian name: `تخت جمشید`; current city: `NULL`; province: `فارس`.
- Existing WGS84 coordinate: `(29.93444, 52.89028)`, role `property_reference`. The proposed workflow will never alter it or call it an entrance.
- Current destination status: `needs_review`; no production exposure until a valid signed owner decision and all production-view checks pass.
- The signed packet binds the pre-review canonical identity snapshot (`تخت جمشید`, `archaeological_site`, province `فارس`, city `NULL`) and the coordinate above. Activation aborts if the staged proposal points to a different row or if this canonical snapshot has drifted. An idempotent retry must find the already-active record exactly equal to the signed output.
- Existing Persian document key: `unesco-persepolis-v1-doc`. It does not provide the requested three-locale claim mapping.

## Exact candidate copy for review

All text below is copied from the existing versioned research pack. It is draft content, not an approved publication.

| Locale | Name | Description draft |
|---|---|---|
| fa-IR | تخت جمشید؛ پارسه | تخت جمشید محوطهٔ باستانی هخامنشی در محدودهٔ مرودشت استان فارس است. یونسکو آغاز ساخت مجموعه را به فرمان داریوش یکم در سال ۵۱۸ پیش از میلاد و آن را مجموعه‌ای از بناهای کاخی بر سکویی بزرگ توصیف می‌کند. |
| en-US | Persepolis | Persepolis is an Achaemenid archaeological complex near Marvdasht in Fars Province. UNESCO records that construction began under Darius I in 518 BCE and describes a major palatial ensemble on a vast terrace. |
| ar | تخت جمشيد؛ برسبوليس | برسبوليس مجمّع أثري أخميني قرب مرودشت في محافظة فارس. وتسجل اليونسكو بدء البناء في عهد داريوس الأول سنة 518 قبل الميلاد، وتصف مجموعة قصور على مصطبة واسعة. |

### Claim decisions

| Claim key | fa-IR draft | en-US draft | ar draft | Exact source(s) |
|---|---|---|---|---|
| `persepolis_518_bce` | ساخت تخت جمشید به فرمان داریوش یکم در سال ۵۱۸ پیش از میلاد آغاز شد. | Construction of Persepolis began under Darius I in 518 BCE. | بدأ بناء برسبوليس في عهد داريوس الأول سنة 518 قبل الميلاد. | `UNESCO_PERSEPOLIS`: [UNESCO World Heritage Centre, Persepolis](https://whc.unesco.org/en/list/114), retrieved 2026-11-08, source type `world_heritage_primary_record`, listed license `CC-BY-SA IGO 3.0`. |
| `persepolis_marvdasht_fars` | تخت جمشید در محدودهٔ مرودشت استان فارس قرار دارد. | Persepolis is in the Marvdasht area of Fars Province. | تقع برسبوليس في منطقة مرودشت بمحافظة فارس. | `VISITIRAN_PERSEPOLIS`: [Visit Iran, Persepolis](https://visitiran.ir/attraction/persepolis), retrieved 2026-11-08, source type `tourism_attraction_profile`, license not specified; and `UNESCO_PERSEPOLIS` above. |

### Source and coordinate review

| Source ID | Title / publisher | URL | Retrieval / rights decision needed |
|---|---|---|---|
| `UNESCO_PERSEPOLIS` | Persepolis — UNESCO World Heritage Centre / UNESCO World Heritage Centre | https://whc.unesco.org/en/list/114 | Retrieved 2026-11-08. Candidate register lists CC-BY-SA IGO 3.0; confirm current terms and exact attribution. |
| `VISITIRAN_PERSEPOLIS` | Persepolis — Visit Iran / Visit Iran portal | https://visitiran.ir/attraction/persepolis | Retrieved 2026-11-08. No license is supplied in the register. Explicitly determine reuse permission/terms; do not infer it. |
| `UNESCO_PERSEPOLIS_MAP` | Persepolis mapped property point / UNESCO World Heritage Centre | https://whc.unesco.org/en/list/114/maps | The point is a property reference, not an entrance, trailhead, parking location, or route point. Explicitly approve or defer its map use. |

Current evidence does not verify access modes, visitor entrance, opening hours, fees, travel time, route, safety, mobility/accessibility, seasonal restrictions, or current operating status. These remain unknown and must not be inferred from the proposed text.

## Explicit owner decisions required

1. Approve or defer the exact `unesco-persepolis-v1` Fars/Marvdasht regional-day-trip scope.
2. Approve, reject, or revise each locale’s name and description; record locale reviewers.
3. Approve, reject, revise, or defer each claim separately in each locale and its exact source set.
4. Decide source-use rights, attribution and destination-source role for each source. Visit Iran’s permission is unresolved.
5. Approve or defer the coordinate strictly as a `property_reference`; it is never a visitor entrance.
6. Provide authorized approver name/role/reference and sign the reviewed packet using the separately managed `RAHGARD_CONTENT_APPROVAL_HMAC_KEY`.

The current CLI template contains exactly one record and defaults all decisions to `defer`. Signing binds the reviewed locale text to deterministic document/chunk IDs and SHA-256 hashes. No template or Issue scope choice creates approval.

## Controlled isolated activation

After a valid signature only, the operator command can execute against a guarded disposable PostgreSQL 17 database. In one transaction it resolves exact existing Persepolis identity, creates or verifies explicitly approved source rows/links, creates reviewed locale documents and claim chunks, updates only the exact destination’s reviewed name/locality/description and `needs_review → active/verified` state without changing coordinates, writes claim-to-chunk/source evidence, and checks the production views. Any source, identity, hash, relationship, or view mismatch aborts and rolls back the entire transaction. It cannot publish any other destination or connect to a production/shared database.

The private approved JSONL export reads back only current production views and includes persisted claim-evidence IDs. The owner’s separate `TourismRagApiV1` CLI can build a private index only after approval. No real content publication, index build, or traveler recommendation is authorized or performed by this packet.
