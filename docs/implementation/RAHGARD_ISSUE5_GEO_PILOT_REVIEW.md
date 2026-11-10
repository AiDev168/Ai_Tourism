# Rahgard Issue #5 — geo-aware pilot review (owner decision required)

**Purpose:** propose a small, reviewable Fars pilot set and state exactly what the supplied candidate package says about geography. This is not publication approval, a route plan, or evidence that a traveler can enter a site.

## Proposed first review batch

The candidate values below are copied from `engineering/data-research/shiraz_fars_candidate_content_v2/shiraz_fars_candidate_content_v2.json`. The pack labels all records `needs_review`, `verification_status=pending`, `publishable=false`, and `data_confidence=0.0`. Coordinates retain the pack's stated role and source. They have **not** been promoted into the approved production catalogue by this review.

| Exact target key | Candidate identity / locality in pack | Candidate WGS84 point | Stated role and coordinate source | Pilot handling proposed |
|---|---|---:|---|---|
| `shiraz-hafezieh-v1` | حافظیه؛ آرامگاه حافظ / Hafezieh — Tomb of Hafez; Shiraz, Fars | 29.6254028, 52.5583194 | `representative_point`; secondary Wikipedia page: [Tomb of Hafez](https://en.wikipedia.org/wiki/Tomb_of_Hafez) | Suitable for an owner-reviewed Shiraz city grouping if identity and point are confirmed. Never label this coordinate as an entrance or route start. |
| `shiraz-eram-garden-v1` | باغ ارم / Eram Garden; Shiraz, Fars | 29.63583, 52.52528 | `representative_point`; secondary Wikipedia page: [Eram Garden](https://en.wikipedia.org/wiki/Eram_Garden) | Candidate for a Shiraz city grouping. Visit Iran has separate identity pages in the pack: [English](https://visitiran.ir/attraction/eram-garden), [Persian](https://visitiran.ir/fa/attraction/%D8%A8%D8%A7%D8%BA-%D8%A7%D8%B1%D9%85). These do not turn the point into an entrance. |
| `shiraz-vakil-bazaar-v1` | بازار وکیل / Vakil Bazaar; Shiraz, Fars | 29.6149806, 52.5467972 | `representative_point`; secondary Wikipedia page: [Vakil Bazaar](https://en.wikipedia.org/wiki/Vakil_Bazaar) | Candidate city asset; do not infer opening hours, current access, or that the representative point is an entrance. Candidate identity source: [Visit Iran](https://visitiran.ir/en/attraction/vakil-bazaar-0). |
| `unesco-persepolis-v1` | تخت جمشید؛ پارسه / Persepolis; Marvdasht, Fars (regional day trip, not Shiraz city) | 29.93444, 52.89028 | `property_reference`; UNESCO property page: [Persepolis](https://whc.unesco.org/en/list/114) | Keep in a separate regional day-trip group. A property-reference coordinate is not a visitor entrance, parking point, or route endpoint. |

These four records make a modest candidate review batch, not a promise that four stops form a feasible itinerary. The pack gives no verified access mode, opening schedule, ticket price, visit duration, public transport, route, entrance, mobility information, or safety profile for them. Do not generate driving or walking directions to their representative/property reference points. A router may only produce ETAs for an actual verified entrance or other reviewed access point.

### Excluded from this first batch pending locality resolution

`unesco-pasargadae-v1` has a pack-supplied `property_reference` coordinate (30.193830000000002, 53.167289999999994) from [UNESCO](https://whc.unesco.org/en/list/1106), but its `city_name` is null and the pack does not supply a county in the proposal row. It should remain a regional candidate until the pilot owner accepts its locality label and the exact canonical identity/location. Its coordinate must not be treated as an entrance.

## Evidence and boundary notes

- The research pack contains eleven spatial proposals and explicitly describes them as review-only enrichments against existing destination identities. Coordinate policy says reference-only; do not overwrite canonical coordinates.
- Nine Shiraz candidate points use the pack's `WIKI_COORD_SECONDARY` source and are explicitly marked `secondary_coordinate_requires_validation`. This review does not treat those points as independently verified.
- Persepolis and Pasargadae use UNESCO property-reference coordinates. Those coordinates describe the heritage property reference, not a visitor gate.
- The pack's Visit Iran and UNESCO pages support candidate identity/context claims as cited in the proposals. No live page fetch or independent geospatial cross-check was performed for this implementation note.
- The application catalogue now carries optional `latitude`, `longitude`, and `coordinate_role` from the approved spatial production view. It preserves nulls and does not relabel `property_reference` or `representative_point` as an entrance. Candidate/review records remain outside that view and cannot appear through this read path.
- Any review outcome should be one owner decision for this batch: approve/reject each candidate identity, city/county placement, coordinate and coordinate role, and visibility as a traveler-facing map point. Approval of a representative/property reference point does not approve directions or site access.

## Owner decision requested

For each row in the proposed batch, confirm whether its exact identity, Fars/Shiraz or Marvdasht locality, coordinate value, and coordinate role may be exposed to travelers as a **reference map point**. Separately identify an entrance/access point only if an attributable source supports one. Until that review is recorded through the existing owner-controlled publication workflow, all four remain unpublished and traveler recommendations must continue to use only currently approved production rows.

## Implementation and isolated acceptance evidence

- The approved-catalogue projection now carries nullable latitude, longitude, and the original coordinate role. It rejects partial coordinate pairs, out-of-range values, and coordinates without a known role. No candidate rows were published or copied into this projection.
- Itinerary drafts now use a deterministic geographic grouping heuristic when approved destination points are available. Origin is not used because the traveler profile has no trusted origin-to-point mapping. The ordering is an editable display suggestion only; it does not assert road feasibility, entrance access, travel time, opening hours, or route safety.
- Missing coordinates, reference/representative points, heuristic grouping, and unplanned days are returned as explicit warning codes and localized in fa-IR, en-US, and ar.
- The profile/recommendation contract was corrected to accept the PWA's empty `accessibility: []` representation as “no explicit access requirement.” Nonempty values still enter normal fail-closed assessment; malformed list items remain invalid.
- Focused backend validation: 54 tests passed; Ruff passed. Frontend validation: 110 tests passed; production build passed. The browser run below passed. One earlier combined backend invocation without the isolated test-only `DATABASE_PASSWORD` failed during test collection; rerunning with the approved test value passed. No shared database was used.
- Chromium 156.0.8078.47 ran against a fresh PostgreSQL 17 disposable database (`ai_tourism_auth_test_mvp_05e97a5501b3`, loopback port 50097, marker validated). All three locales passed. The production catalogue remained empty and the traveler-visible production path correctly returned `needs_confirmation`; the positive itinerary used four private test-only identities through the real browser UI, FastAPI, and database. It persisted 15 days, four initial stops, then three edited stops and 12 unplanned days after reload/reopen.
- Sanitized screenshots and the machine report are under `artifacts/visual-qa-task15d/run-2026-11-10T11-53-24-658Z-37128/`. The itinerary fixture has no coordinate evidence, so the browser correctly reported `stop_location_unknown`; geographic grouping itself is covered by focused service tests, not represented as real traveler geography in this run.

The owner decision above remains required before any Fars candidate can be exposed. Real entrance/access evidence and a trusted origin mapping are also absent, so this work does not establish a navigable or optimized itinerary.
