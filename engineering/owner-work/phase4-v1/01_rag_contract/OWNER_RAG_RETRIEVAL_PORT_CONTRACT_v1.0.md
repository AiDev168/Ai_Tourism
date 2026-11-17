# قرارداد اتصال RAG مالک به AI Tourism — نسخه ۱.۰

**وضعیت:** پیشنهاد فنی برای بررسی مالک؛ هنوز قرارداد اجرایی امضاشده نیست  
**تاریخ:** ۲۰۲۶-۱۱-۰۹  
**مبنای معماری:** ADR-0003، ADR-0004، ADR-0008 و قرارداد ذخیره‌سازی RAG پروژه

## 1. هدف و مرز مسئولیت

این سند فقط مرز اتصال RAG مستقل مالک را تعریف می‌کند. پیاده‌سازی RAG مالک در این پروژه کپی، بازنویسی، benchmark یا جایگزین نمی‌شود. موتور RAG مسئول بازیابی و بازگرداندن شواهد است؛ AI Tourism مسئول اعتبار محتوای منتشرشده، قواعد سفر، سنجش محدودیت‌ها، eligibility، رتبه‌بندی قطعی و نمایش پاسخ است.

**RAG حق تصمیم‌گیری دربارهٔ امکان‌پذیری سفر را ندارد.** متن بازیابی‌شده، LLM و reranker نمی‌توانند محدودیت سخت، نیاز دسترس‌پذیری یا قاعدهٔ ایمنی را کنار بزنند. هیچ سند staging، `needs_review`، synthetic، منبع منقضی/لغوشده یا دادهٔ فاقد provenance نباید وارد پاسخ مسافر شود.

## 2. جایگاه در معماری فعلی

```text
Trip Intake / normalized request
        |
        v
Requirement Assessment + Consent Validation
        |  hard constraints / non-waivable safety & accessibility
        v
Application-owned RetrievalPort (read-only)
        |  exact owner-RAG adapter; no model choice in domain code
        v
Approved Production Corpus + Provenance
        |
        v
Deterministic Eligibility / Ranking / Evidence Validation
        |
        +----> Spatial destination result (map/itinerary only when coordinate role permits)
        |
        +----> Separate non-spatial culinary result (never a map stop)
        |
        v
Evidence-aware response composition / UI
```

`backend/app/modules/recommendation/retrieval.py` بازیابی ساختاریافتهٔ exact/bounded است و با این port یکی نیست. `backend/app/modules/integrations/ai_gateway.py` هم فقط مرز عمومی capability provider است؛ خودش RetrievalPort یا آداپتور owner RAG محسوب نمی‌شود.

## 3. Proposed Python interface

این interface عمداً provider-neutral است. نوع‌ها باید در package پروژه تعریف شوند؛ نباید request/response از SDK یک vendor وارد domain شود.

```python
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol, Sequence

class CorpusKind(StrEnum):
    SPATIAL_DESTINATIONS = "spatial_destinations"
    CULINARY_KNOWLEDGE = "culinary_knowledge"

class RetrievalOutcome(StrEnum):
    OK = "ok"
    NO_EVIDENCE = "no_evidence"
    UNAVAILABLE = "unavailable"
    INVALID_REQUEST = "invalid_request"

@dataclass(frozen=True)
class RetrievalRequest:
    request_id: str                 # opaque correlation id; not a user id
    query: str                     # minimized retrieval text; untrusted
    locale: str                    # exactly fa-IR | en-US | ar
    corpus: CorpusKind
    limit: int                     # bounded by server policy
    filters: dict[str, str]        # server-generated allowlisted filters only
    as_of: datetime                # UTC, supplied by application

@dataclass(frozen=True)
class EvidenceSource:
    source_id: str                  # stable source registry identity
    source_name: str
    source_url: str
    source_role: str
    retrieved_at: datetime | None
    valid_from: datetime | None
    valid_until: datetime | None
    license: str | None

@dataclass(frozen=True)
class RetrievedEvidence:
    evidence_id: str                # stable chunk/claim identifier
    document_id: str
    content_hash: str
    text: str                       # source-derived content; untrusted
    locale: str
    corpus: CorpusKind
    canonical_entity_key: str | None
    claim_key: str | None
    score: float | None             # diagnostic only; never user-facing quality score
    sources: tuple[EvidenceSource, ...]

@dataclass(frozen=True)
class RetrievalResponse:
    outcome: RetrievalOutcome
    items: tuple[RetrievedEvidence, ...]
    corpus_version: str | None
    retrieval_version: str | None
    generated_at: datetime
    warnings: tuple[str, ...]

class RetrievalPort(Protocol):
    async def retrieve(self, request: RetrievalRequest) -> RetrievalResponse: ...
```

### Type and validation invariants

- Locale is one of `fa-IR`, `en-US`, `ar`; invalid locale is `INVALID_REQUEST`, never silently substituted.
- `limit` is an application-owned small cap. Initial proposal: 1–20 evidence units; final value must be load-tested by Codex after interface approval.
- `request_id` is opaque. No phone number, trip id, conversation id, email or raw account identifier is passed into the RAG adapter.
- `filters` are produced by trusted application code, schema-validated and allowlisted. The user cannot supply SQL, table names, embedding-space identifiers or publication predicates.
- `score` is an optional diagnostic from the owner system. It is not calibrated across corpora/locales and must not be exposed as a recommendation score.
- Empty evidence is a successful abstention (`NO_EVIDENCE`), not a server failure.
- `UNAVAILABLE` means adapter/service is unavailable or timed out. It must not be silently replaced by another model, local/remote service or corpus.
- The adapter must return source/document/chunk identity and claim/locale attribution with every evidence unit. An answer text without traceable evidence is not a valid retrieval result.

## 4. Corpus and publication boundaries

| Corpus | Permitted source | Spatial semantics | Output use |
|---|---|---|---|
| `spatial_destinations` | `knowledge.production_destinations` + production provenance / retrieval views | City, region, destination and POI with explicit coordinate role | Destination explanation; map/itinerary only when independently verified coordinate semantics support it |
| `culinary_knowledge` | `knowledge.production_culinary_knowledge` and claim-level provenance | Non-spatial food/dish/souvenir knowledge | Food discovery and cultural context only; no coordinates, route stops or venue availability implied |

Hard exclusions: candidate import packs, content proposals, `needs_review`, `pending`, synthetic fixtures, unpublished canonical rows, revoked sources, stale/expired documents, content from arbitrary user-provided URLs, and any corpus not explicitly assigned to the request. No cross-corpus fallback unless the application explicitly requests two separate retrieval calls and labels their meaning.

## 5. Evidence validity and factual rules

For each evidence item the application must validate:

1. Canonical entity/document/chunk identity is stable and resolves to an eligible production publication row.
2. Source provenance is present and not revoked; `valid_from`/`valid_until` are respected relative to `as_of`.
3. `content_hash` matches the indexed document/chunk version or an approved version mapping.
4. Locale matches the requested locale. Cross-locale retrieval can be proposed as a separate *translation/semantic expansion* feature, but must not present translated retrieval as native source evidence without explicit labeling and review.
5. Every displayed factual claim is linked to one or more `EvidenceSource` objects. Unsupported parts are omitted or marked unknown.
6. Geospatial results retain `coordinate_role`: `visitor_entrance`, `representative_point`, or `property_reference` are not interchangeable. A property centroid cannot be rendered as a visitor gate or route origin.
7. Operational facts (opening hours, tickets, availability, current condition, trail status, transport, weather, access/safety) need an independent freshness contract. Historical knowledge RAG alone cannot assert current status.

## 6. Error and timeout semantics

| Condition | Port outcome | Application behavior |
|---|---|---|
| Valid evidence | `OK` | Validate every row, apply deterministic rules, present citations |
| Valid but no evidence | `NO_EVIDENCE` | Honest localized no-evidence state; do not invent or fill from fixtures |
| Invalid locale/filter/limit | `INVALID_REQUEST` | Internal validation error; safe client-facing message |
| Timeout/provider/network/database error | `UNAVAILABLE` | Localized retry affordance where safe; no silent fallback |
| One malformed/unprovenanced item | Response rejected or item dropped under an explicit strict policy | Record fixed redacted event; never expose malformed evidence |
| All evidence expired/revoked | `NO_EVIDENCE` | Explain that no current approved source is available |

Initial proposal for an adapter timeout: 3 seconds per read request, one bounded retry only for idempotent transient transport errors, and an overall request deadline owned by FastAPI. These are proposed starting values, not selected production SLOs. Codex must not introduce infinite retries, recursive self-calls or alternate provider fallback.

## 7. Security, privacy and observability

- Retrieval service receives only minimum necessary normalized query and approved filters.
- Never log query text, retrieved content, prompt, phone, tokens, credentials, endpoint, or provider raw exception by default.
- Telemetry may retain opaque correlation ID, corpus version, retrieval version, locale, count, duration, outcome code, and coarse error class.
- All retrieved text is untrusted data. It cannot issue instructions, alter system/developer policy or request secrets.
- Public API never reveals provider/model/profile/endpoint/embedding metadata or internal diagnostics.
- No provider is activated by this contract. The approved ADR-0008 gateway/admin/privacy gates still apply before any external AI processing.

## 8. Determinism and recommendation integration

Retrieval can rank evidence candidates but does not determine traveler eligibility. The deterministic core must independently enforce:

- mandatory constraints and explicit consent rules;
- safety and accessibility as non-waivable constraints;
- source validity, coordinate semantics and locale support;
- no synthetic/unreviewed or stale facts;
- deterministic rank/tie-break rules already approved by project code;
- separate spatial and culinary response types.

A semantic hit may be used as a *candidate* explanation only. It does not prove an attraction has a particular difficulty, wheelchair access, price, open status, activity suitability or route distance.

## 9. Versioning and compatibility

`contract_version`, `corpus_version`, `retrieval_version`, document `content_hash` and locale must be recorded in the recommendation-run metadata where the schema supports it. A breaking request/response change requires a version bump and contract tests. Embedding-space changes remain owned by the RAG project and must never mix vector spaces implicitly. No embedding model, vector dimension, reranker or index strategy is chosen here.

## 10. Approval checklist

Before Codex implements the real adapter, owner must explicitly confirm:

- [ ] The owner RAG callable API/entrypoint and deployment topology.
- [ ] Request and response field names/types and exact provenance mapping.
- [ ] Whether RAG is invoked in-process, via local service, or via a remote private endpoint (no choice made here).
- [ ] Corpus identifiers and production publication filtering responsibility.
- [ ] Locale behavior and whether cross-locale retrieval is prohibited or separately surfaced.
- [ ] Error taxonomy, timeout and bounded retry limits.
- [ ] Data-processing boundary, retention and whether trip query text may leave the app process.
- [ ] Evaluation set and acceptance thresholds in `../02_rag_evaluation/`.

**Until this checklist is approved, the deterministic fake adapter remains the only safe test adapter.**
