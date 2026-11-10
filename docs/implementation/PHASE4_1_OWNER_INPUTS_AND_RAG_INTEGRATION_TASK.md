# AI Tourism — Phase 4.1 owner inputs and integration task

**Date:** 2026-11-09  
**Status:** Ready for Codex implementation with owner data package; live RAG adapter remains gated  
**Branch:** `feat/mvp-traveler-e2e-v1`  
**Baseline:** `c912000bccaee982a98d58f6810ad74431945ed0`

## Outcome first

Deliver one cohesive, useful traveler flow: authenticated natural-language trip request → reviewed/clarified requirements → deterministic eligible recommendations with evidence or truthful empty state → editable persisted itinerary → history/reopen/delete, in fa-IR/en-US/ar.

Preserve the existing tests, modules, security gates and production publication views. No GitHub CI initiative, marketplace, heavy agent orchestration, database reset, production content activation or unrelated rearchitecture.

## Phase 4 owner package (required input to Codex)

The owner-supplied `AI_TOURISM_OWNER_WORK_PHASE4_V1.zip` contains 13 content files + `MANIFEST.json`. On local checkout, Codex should place unchanged files, preserving relative paths and verified checksums, under:

`engineering/owner-work/phase4-v1/`

Use the supplied repository-root overlay `AI_TOURISM_PHASE4_1_OWNER_INPUTS_REPO_OVERLAY.zip` when it is available alongside the task. This archive has already been path-checked for this prefix and contains the complete unchanged source files. Do not invent, regenerate, overwrite or merge these with existing `shiraz_fars_candidate_content_v2` records.

Package components:
- `01_rag_contract`: proposed typed RetrievalPort, provenance/publication and error semantics.
- `02_rag_evaluation`: **draft** 78 cases (26 scenarios in 3 locales); no RAG run or score established.
- `03_content_research`: 16 regional research rows (15 new candidates + 1 existing reference), 8 culinary discovery rows, 9 source addenda; research-only, not production import.
- `04_coverage`: status matrix/report; proposal counts are not published catalogue counts.
- `05_ux_architecture`: evidence-first recommendation, honest no-evidence/unavailable, nonspatial culinary separation and itinerary behavior.
- `README_FA.md` and `MANIFEST.json`: package interpretation and exact source checksums.

**Do not mutate the shared DB, add unapproved publication migrations, set review status to approved, or enable candidate rows in production views.** The owner supplies real approved data incrementally; population is not a blocker to software implementation.

## Mandatory RAG ownership boundary (ADR-0003 is authoritative)

**Owner's independent ScaleRAG/RAG system owns** embedding-model selection and all installed embeddings, embedding spaces and dimensions, document chunking/indexing, semantic/hybrid retrieval, BM25/FAISS, reranking, graph/min-cut/flow algorithms, benchmarks, tuning and service execution.

**Codex owns in AI Tourism only** a typed read-only application `RetrievalPort`, a deterministic fake, adapter/contract tests, and—**only after actual callable/transport and wire contract are supplied and approved**—a thin integration adapter. The uploaded proposal does not specify the real RAG callable/API, deployment topology, source/chunk ID mapping, or live data-processing permission. Do not fabricate them or treat the proposed Python interface as a verified existing service API.

Keep existing `backend/app/modules/recommendation/retrieval.py` exact structured retrieval distinct from semantic RAG. Keep `backend/app/modules/integrations/ai_gateway.py` (Chat/Vision/Embedding/Reranking capability seam) distinct from RetrievalPort. Do not select, install, download, run or tune embedding models or build a second RAG in this repository.

Contract draft expects `spatial_destinations` and `culinary_knowledge` separate; statuses `OK`, `NO_EVIDENCE`, `UNAVAILABLE`, `INVALID_REQUEST`; opaque request ID, bounded query/limit, locale and approved server-generated filters; traceable canonical/document/chunk/claim IDs, hashes and source/validity metadata. The application, never the RAG or LLM, validates publication/consent/hard constraints and ranks eligible destinations. Any live RAG call is separately gated; use fake for default tests.

## Codex implementation boundaries

1. Confirm local branch/HEAD/worktree; preserve all changes and do not work on `main`.
2. Import the owner package at the specified research-only paths; verify exact `MANIFEST.json` hashes, dataset schema and source IDs, no publication.
3. Implement typed RetrievalPort + deterministic fake/validation + error mapping, with no real RAG engine and no invented endpoint.
4. Complete the traveler vertical slice using the existing app foundation and **server-side remote Chat adapter** only behind approved AI Provider Gateway settings; default automated tests must use fakes and make no paid requests. No live provider activation without explicit processing approval. Never expose provider configuration or secrets to traveler.
5. Demonstrate authenticated travel request and clarification, hard/soft consent preservation, valid evidence-cited fixture recommendations or honest empty result, persistent itinerary edit/reopen/delete and safe provider/RAG error cases.
6. Run local focused tests, frontend build, Ruff and isolated PostgreSQL/browser journey; report exact outcomes, branch/HEAD, changed files, remaining product blockers. No mandatory GitHub CI, automatic merge or new phase.

## Blockers that must be reported rather than invented

Real owner RAG callable/transport and wire schema; approval of remote data processing; pilot hosting/real SMS/device setup; owner-reviewed production content. **These do not prevent fake-boundary and main traveler journey delivery.**

This document supersedes older C1/C2 wording insofar as it might imply Codex may implement or optimize the owner's separate RAG. The companion `AI_TOURISM_PHASE4_1_CODEX_TASK.md` may be used for additional detail. In any conflict, follow this repository task's current-state reconciliation and accepted ADRs; avoid re-implementing finished functionality.

## Reconciliation of historical owner notes (2026-11-09)

**Language:** All Codex instructions, technical task reports, code comments and task acceptance statements must be in **English**. The owner-facing management summary may be in Persian.

**Source handling:** The owner's 2026-11-09 attached historical notes describe the long-term three-sided tourism platform (travelers, partners, platform administration), early MVP gaps, and a *proposed* v1 RAG adapter. Treat dated observations as snapshots; the later 2026-11-08/09 Phase 3 closure and Phase 4 readiness report plus current executable code are authoritative for implementation status. Do not create another planning/audit task for work already accepted.

### Current foundation — reuse, do not rebuild

- PostgreSQL-backed traveler OTP/session, CSRF, principal and owner-scoped conversation/trip/history/reopen/delete are already implemented and tested with fake OTP. Production authentication and account recovery remain separately gated.
- Deterministic requirement assessment, profile-version-bound advisory consent and recommendation code exist. Explicit soft preferences must not waive ambiguous/hard constraints, safety or accessibility. The 2026-11-08 Phase 4 report recorded 138 passed/4 skipped backend tests, four separately passed guarded PostgreSQL tests, 83 frontend tests, SQL 14/14 and an actual three-locale browser journey. These are prior reported results, **not** a substitute for the new task's own tests.
- The typed published spatial catalogue and separate approved-view `GET /api/v1/catalog/culinary` are implemented. Culinary concepts are non-spatial: never promote them to destination/itinerary/map stops. Do not create a redundant culinary catalogue domain.
- The itinerary service already permits **1–365 days** and labels insufficiently evidenced days `partial/unplanned`; preserve this existing approved capability. Older 1–3-day wording in historic blueprint and owner UX drafts is superseded for current behavior. Cover a 10-day partial-itinerary regression as part of the end-to-end test, without fabricating additional stops.
- OTP lifecycle cleanup, provenance barriers, user deletion and hard/soft constraints received changes after earlier Task 3.0 critiques; inspect the **latest code/tests first** and fix only still-reproducible defects.

### Integrate useful product/UX decisions, not duplicate modules

Maintain one coherent traveler journey: language-aware natural-language intake; review/clarification of required/ambiguous fields; immutable hard requirements and explicit soft-preference consent; independently validated publication and claim evidence; deterministic eligibility and ranking; a persuasive, **source-linked** answer including uncertainty; an editable persistent itinerary. Show `available`, `needs_confirmation`, `no_evidence/empty`, `unavailable`, and `partial` as distinct honest states. Inspiration-card fixtures must never masquerade as retrieved destinations or evidence. Do not show invented suitability percentages, star ratings, access level, difficulty, weather, ticket prices, hours or ETA.

Preserve verified coordinate semantics: `representative_point` and `property_reference` cannot become a visitor entrance, parking location or directions origin. Permit route/deep-link claims only under independently verified entrance/provider constraints. Keep food and other non-spatial knowledge separate from spatial destinations. Keep the existing Persian/English/Arabic design system, RTL/LTR, mixed-script handling, safe-area/keyboard accessibility and responsive PWA; do not redesign the UI from scratch.

### RAG contract precedence — strictly no parallel engine

The **newer draft** in the Phase 4 owner pack `01_rag_contract/OWNER_RAG_RETRIEVAL_PORT_CONTRACT_v1.0.md` supplies the application-side semantics:
- Corpus: `spatial_destinations` OR `culinary_knowledge` per call.
- Outcomes: `ok`, `no_evidence`, `unavailable`, `invalid_request`.
- Request: opaque correlation ID, minimized bounded query, `fa-IR/en-US/ar`, corpus, bounded limit, allowlisted trusted filters and `as_of`.
- Evidence: stable canonical/document/claim identifiers, content hash, locale, text, provenance, source validity, version metadata and *retrieval-only* score.

The older historical owner note used `destination/attraction/culinary/local_knowledge` with `ok/no_results` and different DTO fields. **Do not mix the two proposed contracts.** Likewise, the separately authored `OWNER_RAG_HTTP_API_CONTRACT_v1.yaml` is a draft example, **not** evidence that any service exists at `127.0.0.1:8765` or that this exact transport is owner-approved. No hardcoded endpoint, embedding model, dimension, local model runtime or automatic fallback.

The owner's independent ScaleRAG owns embedding/model and index selection, multilingual search, vector/BM25/FAISS, chunking, optional reranking, Min-Cut and evaluation. In AI Tourism implement ONLY the typed read-only port, deterministic fake, defensive identity/provenance validation and a thin future adapter **after the actual existing RAG callable/wire schema is supplied**. Preserve structured catalogue retrieval independently. Do not undertake a new RAG benchmark, model install, indexing job or another engine. A draft multilingual gold set is not proof of retrieval quality.

### Long-term product vision preserved; not a Phase 4.1 blocker

The target product has THREE distinct actors: traveler, tourism partner organization, platform administrator. Partner onboarding/verification, per-organization roles, service/offer catalogs, schedule/price/availability freshness, deterministic partner matching, outbound click and **consent-based** referrals are legitimate planned product capabilities. The repository already has the proposed partner architecture, domain contract, roadmap and ADR-0009–ADR-0013: **do not recreate them or turn proposals into accepted decisions**.

For rapid traveler MVP delivery, **do not implement partner organization schema, partner/admin UIs, referral leads, booking, payments or settlement in Phase 4.1.** Preserve the extension boundary: place/knowledge catalog remains canonical; partner services, offers, schedules, price and live inventory are separate structured commercial data, not RAG factual knowledge. Future referral leads require explicit consent/recipient/data-purpose rules and owner-approved ADR changes; the accepted ADR-0007 currently permits allowlisted external redirects/click tracking only, not in-app transactions or implicit referral-data sharing. Keep separate privileged AI Provider administration from marketplace governance.

### Practical Codex execution and finish criteria

At task start, inspect local branch, upstream, exact HEAD and dirty state, then `git fetch origin`. Check out or track `feat/mvp-traveler-e2e-v1` and use `git pull --ff-only origin feat/mvp-traveler-e2e-v1` **only if safe and no user-owned change would be overwritten**. Never reset/clean/rebase/force, migrate shared databases, or auto-merge. The owner research ZIP is imported unchanged under `engineering/owner-work/phase4-v1/` as **draft/research-only** with manifest verification; it is not a content-publication task.

Deliver **one coherent product epic**, not a queue of tiny refactors: complete only the missing real traveler/Chat integration and provenance-backed behavior around the preserved working foundation; run local isolated/fake-provider and browser tests for the eligible, no-evidence, unavailable and 10-day-partial paths. Do not activate paid/live AI processing without owner approval. Report concrete working behavior, exact executed tests, remaining RAG real-adapter dependency and next product-critical blockers. No GitHub CI initiative, unnecessary database filling or Marketplace implementation.
