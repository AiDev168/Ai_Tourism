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

This document supersedes older C1/C2 wording insofar as it might imply Codex may implement or optimize the owner's separate RAG. The fuller working task packet is the companion `AI_TOURISM_PHASE4_1_CODEX_TASK.md`, supplied to Codex with the overlay archive.
