# Rahgard V2 Issue #23 local acceptance

**LOCAL GO for the demonstrated Persian planning and two-company sharing journey.** Chromium used the real FastAPI app, marked disposable PostgreSQL 17 and LM Studio. Remote TaHa1_VL remains blocked before a provider request because the authorized development token is absent from the runner process.

The Windows branch fast-forwarded to `d76da457fde481c3e615a4cf33526b2e2c8dece1`, including the owner’s required-field and calendar patches. The tested code is `0cf4c349a30eb42f4b00ed2e093b3298e9afcdf0` on `feat/rahgard-unified-travel-v2`. There are no application migrations in this change. All database operations in the browser test used a newly created disposable database.

## What changed and what passed

| Owner concern | Observed result |
| --- | --- |
| Planning says the populated trip is incomplete | Baseline Chromium reproduced `needs_confirmation` with `destination_resolution` as its sole blocker. The service grouped it under `requirements_incomplete`. It now reports `destination_identity_unresolved` and assesses the confirmed destination name and duration as known. Reviewed flat values can clear obsolete missing flags. Explicit ambiguity, stale consent and mandatory constraints still block. |
| Confirming edits loses known requirements | Confirmation uses the editable form values, including intentional clearing of optional values. Recommendations use the saved selection. On stale consent the UI sends the traveler back to review. The browser confirmed Mashhad, Shiraz, four days, three travelers, the edited 25 million TOMAN budget and a four-day date range. |
| Initial request and chat feel separate | Submitting the first description saves one user message and automatically starts a model turn. The initial form collapses once the conversation opens. The follow-up composer is the primary action and the requirements extraction action focuses the editable profile. |
| AI status reports configuration as connection | The authenticated readiness endpoint uses one shared, short-lived model discovery probe for the configured server route. Chromium verified the connected state before the first message. Model discovery spends no inference turn. The actual run then counted three successful model invocations. |
| Incomplete AI results look like fallback or overwrite edits | An accepted reply can leave fields open for review without classifying the turn as an outage. Typed current-turn evidence controls model fields. The deterministic safety detector remains in use for explicit restrictions. Reviewed context is bounded and sent with later calls. The outage run separately verified deterministic fallback and save/reopen. |
| Required and optional fields are unclear | Destination name and duration are required. Confirmation focuses the missing field and explains invalid duration. Origin, dates, group size and budget are optional; the catalogue identity and mandatory constraint messages are separate from missing traveler information. |
| Local login presentation | The owner option displays local-account instructions only when the API advertises it. Authentication capabilities are unchanged. Dedicated owner login coverage is from the backend regression suite; the browser journey used the guarded test login. |
| Today in the Persian calendar is unclear | Generic workspace button rules overrode the calendar’s colors. Calendar controls now keep their own styles. Chromium set and persisted ISO dates using the Persian calendar, then verified that today and the selected day have distinct colors after reopening. |

## Persian browser trace

The input was the runbook’s three-person, four-day Mashhad-to-Shiraz request with 20 million TOMAN and interests in gardens, historical places and local food. The LM Studio model `qwen3-8b-abliterated` supplied origin, destination, duration, traveler count, budget, interests and weather. It replied to the date and budget follow-up. Its follow-up did not yield an accepted structured date pair in this run, so the traveler selected December 5–8, 2026 in the Jalali picker. The run used manual fields to complete route difficulty and food where the model omitted them. The edited budget and all three preference fields were persisted, and the user reopened the plan after reauthentication.

The normal recommendation response contained zero eligible approved destinations for this route. The app generated and saved a distinct `provisional_unverified` four-day plan. A separate synthetic dependency override exercised positive catalogue recommendation and itinerary persistence in the same isolated stack, with the ordinary published-catalogue endpoint unchanged before and after.

The traveler selected two eligible companies and consented in the UI. Each company’s separate authenticated session opened the reviewed request and itinerary for the original and revised version of the same share in its inbox. The unverified company was excluded. The trace verifies cross-tenant denial, anonymous denial and revocation of the second recipient while the first retained both revisions. Delivery was via the authenticated in-app inbox.

Run `06-20-09-125Z-39400` captured 97 allowlisted API response events. The three model calls took 9.085, 11.981 and 19.153 seconds. The screenshots contain redacted field values and content. Horizontal overflow checks passed at both captured widths.

- [Sanitized trace](evidence/issue23/lm-studio-trace.json)
- [Persian mobile screenshot at 390 px](evidence/issue23/lm-studio-390.png)
- [Persian desktop screenshot at 1440 px](evidence/issue23/lm-studio-1440.png)
- [Jalali calendar screenshot](evidence/issue23/jalali-calendar.png)
- [Forced outage trace](evidence/issue23/forced-outage.json)
- [Evidence checksums](evidence/issue23/SHA256SUMS.txt)

## Executed checks

| Check | Result |
| --- | --- |
| Backend regression suite, including recommendation module | 501 passed, 18 skipped |
| Focused assistant, adapter, provider-admin and recommendation tests | 148 passed |
| Frontend suite | 192 passed |
| TypeScript, production build and PWA asset injection | Passed; existing Vite chunk-size advisory |
| Ruff, Node harness syntax and Git whitespace | Passed |
| LM Studio / Chromium / disposable PG17 | Passed, three real calls and two protected company browser views |
| Forced outage / Chromium / disposable PG17 | Passed, one failed provider attempt, no successful inference, parsed trip persisted and reopened |
| Remote vLLM | Blocked at the runner’s private token check, before network access |

Reproduce from the Windows repository root:

```powershell
.\engineering\pilot\Run-National-Catalogue-Browser-E2E.ps1 -ChatProvider lm_studio
.\engineering\pilot\Run-National-Catalogue-Browser-E2E.ps1 -ChatProvider forced_outage
```

When the authorized token is privately present in the process as `RAHGARD_REAL_CHAT_TOKEN` or `INTERNAL_CHAT_TOKEN`, the same runner supports `-ChatProvider remote_vllm`. The acceptance uses generated, disposable identities and the runner’s guarded login. It does not require real traveler credentials.

The browser gate covers the incomplete-catalogue path and sharing controls. Mandatory safety blocking was covered in the recommendation regression tests. Real catalogue quality, local-owner browser sign-in and remote inference were outside the demonstrated pass. The runbook’s synthetic positive recommendation used a dependency override, and the two protected views were displayed inside the company inbox. No VPS, DNS, persistent database, public catalogue or notification provider was changed.
