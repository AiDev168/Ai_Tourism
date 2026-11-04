# AI Tourism — MVP Implementation Blueprint & Codex Handoff

**Document status:** Pre-Codex implementation blueprint, database-preparation status updated after owner-run base validation  
**Version:** 0.3  
**Repository:** `AiDev168/Ai_Tourism`  
**Repository baseline reviewed:** `main` at `f242bbb649f04adc86944a3e95a2428f76367e46` (reported clean and aligned with `origin/main` in the project preflight)  
**Purpose:** Convert the existing architecture references into a bounded, testable MVP implementation plan. This document is not authorization to modify `main`, deploy infrastructure, incur API costs, download models, or change other projects.

---

## 1. Executive direction

**Pre-Codex gate added by owner:** Before starting application implementation with Codex, initialize the isolated development database, run the full schema/seed/RAG-storage test suite, reconcile all exact table and row counts, and inspect/fix any failure. Continue adding traceable real destination batches and synthetic QA fixtures only through versioned, idempotent seeds. Do not pass the project to Codex merely because the package was generated; local Docker/PostgreSQL tests must first pass on the owner's Windows machine.

Build a **mobile-first travel-advisor product** whose primary interaction is a Persian conversational experience on a phone. The first release must be genuinely useful: it should understand a travel request, ask for missing information, show a small set of justified destinations, and produce an editable short itinerary with useful external information links.

The MVP implementation should use a **modular monolith**, not a microservice fleet or a multi-agent swarm. The LLM is a remote service accessed only by the backend. LLM and embedding providers must be replaceable through adapters. The deterministic decision core owns hard constraints, scoring, eligibility and ranking; an LLM must never override those rules.

The first release is not a booking marketplace. It redirects users to external booking providers and may record outbound clicks. It does not take payment, confirm hotel/flight/tour reservations, issue tickets, or manage cancellations.

### 1.1 Confirmed owner constraints

The following constraints have been stated by the project owner:

1. Most end users are expected to use the product on a phone.
2. The preferred LLM connection is remote API, not local model inference on the development PC.
3. LLM and embedding models, and the underlying RAG algorithms, must remain replaceable. Do not hard-code a model choice into the business architecture.
4. The owner already develops RAG systems and algorithms in other repositories. Do not spend project effort duplicating temporary RAG benchmarking or independently redesigning those algorithms. Integrate through a stable interface when the owner supplies or approves the retrieval implementation.
5. Use synthetic data for development and automated tests. Synthetic data must never be mistaken for production truth. A real pilot requires a controlled, sourced and verified destination dataset.
6. Do not download models, change other repositories, or alter existing PostgreSQL services/containers as part of this project without explicit approval.
7. Preserve safe Git practices: do not work directly on `main`; do not commit, push, merge or deploy without explicit authorization.
8. The current local environment has Python 3.13.15, `uv`, Docker Desktop with a working Linux Engine, and an NVIDIA RTX 4070 Laptop GPU. Existing Docker workloads include `cheshm_bidar-app-1` on port 8000 and `ai-cosulation-worker-pg16-test` published on 55432. Treat them as unrelated and do not modify them.
9. The pre-Codex database package now defines exactly 30 project-owned tables and 419 expected rows after Migration 0006. The owner executed the base v0.2 package on Windows/Docker Desktop: PostgreSQL 17, PostGIS 3.6.4, pgvector 0.8.7, 30 tables and 329 rows passed all database checks. The additive second factual batch (Migration 0006) is now on this feature branch and still requires a fresh owner-side Initialize/Test run to confirm the 419-row baseline.
10. The factual dataset now includes 17 Iranian UNESCO World Heritage properties across two batches, 38 source/map/admin references, 17 Persian paraphrased documents and 34 chunks. All 17 destinations remain `needs_review` and must not be returned by production views until editorial approval. The existing 15 supplied destinations remain unverified; the 12 QA destinations are fabricated test fixtures.

### 1.2 Recommended decisions — pending owner confirmation where noted

| Area | Recommendation | Status |
|---|---|---|
| Client | Installable mobile-first PWA | Recommended; confirm before frontend implementation |
| Frontend | React + TypeScript, responsive RTL UI | Recommended; exact framework/build tooling to be pinned after compatibility review |
| Backend | Python + FastAPI modular monolith | Recommended; confirm before backend implementation |
| Primary database | PostgreSQL | Strong recommendation |
| Geographic queries | PostGIS extension in the same PostgreSQL instance | Recommended where proximity/area queries are required |
| Vector persistence | PostgreSQL + pgvector as the initial option, behind a retrieval boundary | Recommended; do not lock the RAG algorithm or embedding model to it |
| LLM | Remote API through backend-owned provider adapter | Owner preference confirmed; provider/model not selected |
| Embedding | Provider-neutral interface; local-on-server or remote API may be selected later | Model choice intentionally deferred |
| Cache/queue | No Redis or message broker in the first slice unless a demonstrated requirement justifies it | Recommended |
| Object storage | Defer until the product actually needs user uploads or managed media | Recommended |
| Architecture | Modular monolith with explicit domain boundaries | Recommended and consistent with the MVP-first architecture analysis |
| Advanced agents | Out of MVP | Defer to a later roadmap phase |

Do not present a recommendation in this table as an owner-approved vendor or technology decision until the owner confirms it.

---

## 2. MVP product boundary

### 2.1 User outcome

A user should be able to:

1. Open the product on Android or iPhone without installing a native application; optionally install the PWA to the home screen.
2. Describe a trip naturally in Persian.
3. Have the system extract the trip requirements into a visible, editable structured profile.
4. Answer only the necessary clarification questions when critical information is missing or ambiguous.
5. Receive up to three ranked destination recommendations backed by verified catalog data and relevant evidence.
6. Understand why each destination was recommended, which requirements it satisfies, and what limitations or unknowns remain.
7. View a simple one-to-three-day itinerary and edit its days/stops.
8. Open a map/directions link for a destination or attraction only when its coordinates and identity are verified.
9. View weather information with provider and freshness timestamp when available.
10. Follow an external link to a booking provider. The MVP does not complete the booking.
11. Create a basic account, manage a limited profile/history, send feedback, and request deletion of their data.

### 2.2 MVP in scope

- Persian-first conversational UX, RTL and mobile-first layout.
- Natural-language extraction of origin, dates/season, trip duration, budget range, currency, party size/composition, interests, travel style, transport preference and hard constraints.
- Editable, structured trip requirements with provenance/confidence where useful.
- Clarification flow for missing or conflicting requirements.
- Destination/attraction catalog with source provenance and verification status.
- Retrieval integration through an adapter. The retrieval algorithm itself is owner-controlled and is not to be reimplemented or replaced without approval.
- Deterministic eligibility filters, constraint enforcement, scoring and ranking.
- Up to three recommendations with traceable explanation and warnings.
- Simple editable itinerary for one to three days; approximate planning only.
- Map/deep links based on verified location data.
- Weather adapter and short-lived cache, with freshness metadata and graceful degradation.
- External booking/partner redirects and outbound-click tracking.
- Basic registration/authentication, profile, bounded conversation history and feedback.
- Privacy controls to view and delete the user's own profile/history in accordance with the agreed retention policy.
- Request IDs, structured logs, basic usage/cost tracking for remote AI calls, rate limits and health checks.

### 2.3 Explicitly out of scope for MVP

Do not implement these just because they appear in the broad reference architecture:

- In-app hotel/flight/train/tour booking, reservation confirmation, ticket issuance, payment, refunds, cancellation or change workflows.
- Storing payment-card data or processing payments.
- Full travel-agency back office, multi-tenant organization administration or partner settlement.
- Advanced multi-agent orchestration, agent swarms, autonomous tool loops or unrestricted agent-to-agent communication.
- Voice assistant, ASR/TTS interaction, AR/VR, social travel or group booking.
- Price prediction, loyalty programs, sophisticated personalization/behavioral profiling or advanced analytics warehouse.
- Full offline travel planning. A PWA shell/offline fallback may be considered, but must not be advertised as full offline operation.
- Microservices, Kubernetes, Kafka/RabbitMQ, a separate vector database or Redis unless evidence demonstrates a real MVP need.
- A large admin CMS unless content operations cannot be handled safely through a controlled import/review workflow.

**Important scope resolution:** the reference architecture contains broader booking, payment, notification and agentic designs. Those describe future/product-wide capabilities, not permission to implement all of them in the MVP. The MVP boundary above takes precedence for the first implementation.

---

## 3. System shape

```text
Phone / Browser
  └── Mobile-first PWA (Persian RTL)
        │ HTTPS
        ▼
Backend API — Modular Monolith
  ├── Identity & Profile
  ├── Conversation & Trip Requirements
  ├── Destination / Knowledge Catalog
  ├── Retrieval Port (owner-approved implementation)
  ├── Deterministic Decision & Ranking
  ├── Recommendation & Explanation
  ├── Itinerary
  ├── External Integrations
  ├── Feedback & Privacy
  └── AI Gateway / Usage / Audit
        │
        ├── PostgreSQL
        │    ├── relational product data
        │    ├── PostGIS (if geospatial operations are used)
        │    └── pgvector (initial candidate, behind an abstraction)
        │
        ├── Remote LLM Provider API
        ├── Embedding Provider (replaceable; local service or API)
        ├── Weather Provider API
        ├── Maps / Directions links or API
        └── External Booking Provider links
```

### 3.1 Trust and network boundaries

- The phone communicates only with the product backend over HTTPS. It never connects directly to PostgreSQL, a vector store, or a privileged AI provider key.
- All provider credentials remain server-side in environment/secret management. Never put a provider key in JavaScript, a PWA bundle, local storage, or a mobile-visible response.
- The backend calls the remote LLM API. It decides which minimum context is sent and must not forward unnecessary personal data.
- Retrieved documents and third-party responses are untrusted input. They cannot change system instructions, authorize actions, or bypass deterministic rules.
- The database must not be exposed publicly. Only the backend service/network should have database access in staging/production.

### 3.2 Request flow

```text
User message
  → authenticate / apply rate limits
  → load conversation state
  → extract or update structured trip requirements
  → validate fields and detect missing/conflicting constraints
  → ask a clarification question OR continue
  → retrieve candidate evidence through Retrieval Port
  → deterministic hard filters
  → deterministic scoring/ranking
  → generate source-grounded explanation (LLM may phrase; it may not invent facts)
  → optionally draft a 1–3 day itinerary
  → persist result and usage metadata
  → stream/return response to the PWA
```

The synchronous path should remain small and debuggable. Audit, analytics and non-critical notifications can be asynchronous later. Do not introduce a broker merely to imitate the future architecture.

---

## 4. Modular monolith boundaries

Keep modules separated by ownership and public interfaces. Do not create a folder-per-future-microservice or implement every domain table from the broad analysis.

| Module | Owns | Must not own |
|---|---|---|
| `identity` | users, authentication integration, account status, authorization | trip logic or provider API keys in client code |
| `profile` | basic user preferences, consent and privacy operations | inferred sensitive profile enrichment |
| `conversation` | conversations, messages, conversation lifecycle, context references | destination ranking rules |
| `trip` | trip request, structured requirements, constraints, trip lifecycle | LLM prompt internals |
| `catalog` / `knowledge` | destinations, attractions, source provenance, verification, controlled imports | invented or unverified facts presented as verified |
| `retrieval` | stable port and result/evidence contracts; adapter to approved RAG implementation | selecting/changing the owner's RAG algorithm without approval |
| `decision` | hard constraints, eligibility, scoring, penalties/rewards, ranking | LLM-only decisions |
| `recommendation` | recommendation run, ranked items, explanation facts and alternatives | changing scores during natural-language generation |
| `itinerary` | 1–3 day plan, day/stop ordering, user edits | precise live route/availability claims without a source |
| `integrations` | LLM, embeddings, weather, maps and outbound booking adapters | secrets exposed to client |
| `feedback` | user feedback and recommendation response | silent training on personal data without a policy/consent |
| `privacy` | user data export/delete workflows and retention coordination | unbounded retention |
| `observability` | request correlation, structured logs, metrics and AI usage | logging raw secrets or unnecessary personal content |

Suggested source layout is illustrative and should be finalized by Codex only after inspecting the current repository and proposing a concrete plan:

```text
apps/
  api/
  web/
docs/
  architecture/
  decisions/
  api/
packages/ or src/
  domain modules...
database/
tests/
```

Do not add a monorepo/tooling framework solely for fashion. Keep local development simple.

---

## 5. Core domain model — MVP only

The detailed ERD and migration scripts are implementation deliverables for the design phase. The following entities define the minimum conceptual boundary; they are not a demand to create every possible table exactly as named.

### 5.1 Identity and conversation

- `User`
- `UserProfile`
- `ConsentRecord` (only for consent categories actually used)
- `Conversation`
- `Message`
- `ConversationState` or versioned structured context

Conversation context must be versioned and validated. Do not rely exclusively on a large untyped JSON blob as the only source of truth for budget, dates, participants or hard constraints.

### 5.2 Trip request and requirements

A trip request should preserve at least:

- origin (place identifier and/or user-entered text; coordinates only when known)
- date range or season/flexible date expression
- duration
- budget range and currency
- party size and relevant broad participant categories
- interests / travel types
- preferred transport
- accommodation preference when relevant
- mobility/accessibility or other constraints only when the user explicitly supplies them and storage is justified
- hard vs soft constraints
- field source, confidence or confirmation state where needed

Unknown values remain unknown. Never silently convert a missing budget, date, origin or participant detail into a fabricated value.

### 5.3 Tourism knowledge

The prepared MVP schema uses one hierarchical geospatial place catalogue rather than separate `destinations` and `attractions` tables:

- `knowledge.destinations` represents a city, region, destination, attraction/POI, route or city experience.
- `destination_type` distinguishes the entity kind; `parent_destination_id` models containment/parent relationships (for example, an attraction inside a city or a component within a heritage property).
- `aliases`, `destination_categories`, `destination_category_map` and `destination_tags` support Persian/English lookup and controlled classification.
- `location`/`coordinate_role` distinguish visitor entrances from representative or property-reference points.
- `knowledge_sources` and `destination_sources` preserve provenance.
- `knowledge_documents` and `knowledge_chunks` preserve source-backed RAG content; `embedding_spaces` and `chunk_embeddings` persist vectors without fixing one model/dimension in the domain schema.

This unified catalogue is the MVP decision for now. Do not create a separate `attractions` table unless implementation evidence demonstrates that attractions need independent lifecycle, ownership or attributes that cannot be safely represented in this catalogue. Record that as an ADR first.

Every user-facing factual item must have traceable provenance appropriate to its volatility. Suggested metadata include source/provider, source URL or identifier, retrieved/verified timestamp, verification status, valid-from/until, and freshness policy.

Use explicit statuses such as `pending`, `verified`, `rejected` and `stale`. The default public recommendation query must exclude unverified/rejected/stale records unless an explicit policy allows a clearly labeled result.

### 5.4 Recommendation and itinerary

- `RecommendationRun` (request context, algorithm/rule version, timestamp)
- `RecommendationItem` (destination, rank, eligibility, final score)
- `RecommendationFactor` (criterion, raw/normalized score, weight and contribution)
- `RecommendationExplanation` (reasons, warnings, evidence references)
- `Itinerary`
- `ItineraryDay`
- `ItineraryStop`

Persist enough information to explain and reproduce a recommendation. Do not persist opaque LLM prose as the only record of why an item ranked first.

### 5.5 External services and feedback

- `ProviderConfiguration` metadata (never plaintext secrets)
- `WeatherSnapshot` or equivalent cache record with `fetched_at` and `expires_at`
- `ExternalLink` / allowlisted provider target
- `OutboundClick`
- `Feedback`
- `AIUsageRecord` with provider/model alias, prompt/version reference if applicable, task, latency, token usage, estimated cost and status
- audit/security events with privacy-aware payloads

MVP does not need booking, payment, ticket, refund or settlement entities.

---

## 6. Destination data quality and provenance gate

The current `database/tourism_points.sql` is a **provisional research seed**, not a production-ready destination catalog. It has 15 rows, source status `pending`, destination status `needs_review` and `data_confidence = 0`; the pre-Codex database package preserves that state. It adds two separate batches totalling 17 source-verified UNESCO properties, 17 Persian source-backed documents and 34 chunks, all still in `needs_review` pending editorial approval.

### 6.1 Database preparation status

The original `database/tourism_points.sql` still contains 15 user-supplied rows with pending sources, `needs_review`, zero confidence and no coordinates. Do not alter or reinterpret those records. The pre-Codex bundle adds a separate migration-based schema around this baseline:

- source-name and canonical-place uniqueness are made explicit/null-safe;
- PostGIS `geography(Point, 4326)` and a GiST location index replace the old latitude/longitude B-tree as the spatial query path;
- coordinates have an explicit semantic role (`unknown`, `property_reference`, `representative_point`, `visitor_entrance`, or `test_fixture`);
- destination categories use a controlled taxonomy; arbitrary destination types remain key-shaped strings to allow new entity types without changing the schema;
- provenance, document/chunk hashes, synthetic markers, and production publication views are included;
- expected exact table/row counts and SQL integration checks are in the package.

The package is prepared but not yet runtime-verified on the owner's machine. It must not be considered applied until `Initialize-Database.ps1` and `Test-Database.ps1` both complete successfully and the actual-vs-expected row-count report is all PASS.

### 6.2 Synthetic vs production data

- Synthetic records must carry explicit provenance such as `is_synthetic`, `data_origin` and a batch/test identifier, or be isolated in a test-only database/fixture layer.
- Production queries must not return synthetic rows.
- Synthetic descriptions/coordinates must not masquerade as real places. Prefer synthetic test entities or fixture factories; do not invent plausible coordinates for real locations.
- The current preparation bundle contains a first factual batch of 10 Iranian UNESCO World Heritage sites. Each has official description/map references and a Persian paraphrased document. UNESCO's registry currently lists 30 Iranian properties; this first batch is not complete coverage. Expand by further source-backed batches after the database tests pass. (Official country registry: https://whc.unesco.org/en/statesparties/ir/.)
- Before pilot, the owner must approve a defined geographic coverage and a real dataset whose names, classifications, coordinates and important facts have been verified against traceable sources.
- Missing facts must remain null/unknown and be reflected in the UI, not generated by the LLM.

---

## 6.3 Pre-Codex database and RAG-storage test gate

The database preparation image is PostgreSQL 17 + PostGIS 3.6.x (currently 3.6.4 from `postgis/postgis:17-3.6`) + pgvector 0.8.7. This is a fresh isolated volume; it is not an in-place upgrade path for any existing PostgreSQL/PostGIS data directory. The PostGIS image maintainers document that the 3.5-to-3.6 line changed the Debian base and warn against switching an existing data volume across that boundary.

The current preparation bundle expects 30 project-owned tables and 419 rows after Migration 0006. The previously executed 329-row base is preserved; Migration 0006 is additive and must be applied without resetting the existing database or Volume. The full per-table count is in `engineering/database-prep/docs/EXPECTED_ROW_COUNTS.md` and is enforced again by SQL tests. Important intentional zero rows include `embedding_spaces`, `chunk_embeddings`, `outbound_clicks`, `ai_model_calls` and `audit_events`.

The package includes:

- exact table inventory and seed-count assertions;
- idempotent seed re-execution and migration checksum checks;
- SHA-256 and character-count validation before and after database insertion;
- foreign-key/provenance/recommendation-score/itinerary relationship checks;
- PostGIS distance, `ST_DWithin`, GiST and alias GIN index checks;
- vector storage and nearest-neighbor contract tests in separate synthetic 3D and 4D spaces, including rejection of mismatched dimensions;
- application-role least-privilege and actual runtime-role checks;
- positive/negative production publication-view tests;
- external UNESCO source/document/coordinate assertions.

**Important boundary:** these tests prove data import, schema integrity, spatial storage and pgvector persistence/nearest-neighbor mechanics. They do not prove semantic Persian retrieval quality or the correctness of the owner's RAG algorithm. The actual embedding spaces and vectors remain empty until the owner-approved pipeline is integrated. Do not invent a semantic RAG score or claim the RAG system is production-ready from these storage tests.

## 7. AI and RAG integration contracts

### 7.1 LLM gateway

The backend should depend on an application-owned interface, not a vendor SDK scattered through domain code. Conceptual operations:

```text
LLMProvider
  generate(request, response_schema, timeout, metadata) -> structured result
  stream(request, response_schema, timeout, metadata) -> stream of response events
```

The concrete interface and event schema should be documented in code and tested. Provider/model selection is configuration-driven. Record model/provider alias, version where exposed, prompt/template version, latency, token usage, estimated cost and status.

Requirements:

- server-side credentials only;
- structured output validated against application schemas;
- timeout and bounded retry policy;
- per-user and global usage/cost limits;
- circuit breaking or controlled fallback for provider outages;
- no raw provider exception or secret returned to the client;
- no unnecessary PII in model prompts;
- safe handling of prompt injection in user text and retrieved content;
- deterministic validation after every model-produced field that affects business rules.

Streaming should not compromise persistence or consistency: define how partial output, disconnects, cancellation, duplicate submissions and final persisted messages work. SSE is the initial recommendation; WebSocket is not required unless a demonstrated bidirectional use case emerges.

### 7.2 Embedding and retrieval boundary

Do not choose or freeze an embedding model in this blueprint. Expose replaceable contracts, for example:

```text
EmbeddingProvider
  embed_queries(texts, model_alias) -> vectors + model metadata
  embed_documents(texts, model_alias) -> vectors + model metadata

RetrievalPort
  retrieve(query, filters, top_k, context) -> RetrievalResult

RetrievalResult
  candidates[]:
    document/chunk reference
    text or safe excerpt
    source/provenance
    freshness/validity metadata
    retrieval score and optional method metadata
```

The owner's evolving RAG algorithm plugs behind `RetrievalPort`. Codex must not independently invent, tune, benchmark or replace the RAG pipeline. If the current retrieval code is not ready to integrate, use a small deterministic fake adapter for tests and keep the port stable.

Persist enough embedding metadata to support later model changes: provider/model alias, exact model/version, dimensions, preprocessing/normalization version and creation timestamp. Keep vector spaces isolated; do not compare or mix vectors produced by different models as though they belonged to one space. Re-embedding/re-indexing is an explicit migration/job, not an invisible side effect of switching a config value.

### 7.3 Decision core and explanation

The deterministic decision core owns:

1. eligibility and hard filters;
2. validation of required facts;
3. scoring of soft preferences;
4. ranking, penalties and tie-breaking;
5. explanation facts and warning codes.

Examples of hard constraints include a user-declared maximum budget, trip dates, required accessibility, prohibited transport, or a strict distance limit. Soft preferences may affect ranking but cannot make an ineligible destination eligible.

LLM responsibilities are limited to interpreting natural language, extracting structured fields, asking clarifying questions and phrasing source-grounded explanations/itinerary drafts. It must not invent scores, coordinates, prices, weather, opening hours, travel times, safety facts or source references.

Each ranking run should be reproducible from the stored request, candidate set, rule/algorithm version and score factors.

---

## 8. External integrations

### Weather

- Weather facts are volatile. The initial 30-table database does not create a persistent weather-snapshot table or require Redis.
- For the first slice, the weather adapter returns provider, location, forecast time, `fetched_at`, `expires_at` and relevant warnings with the response. Add persistence/cache only if measured latency, cost or rate limits justify it; record the decision as an ADR.
- Show freshness/updated time in the client.
- If data is unavailable or stale, say so; do not let the LLM fabricate a forecast.
- Provider choice is an open decision and should be isolated behind an adapter.

### Maps and routing

- For MVP, verified coordinates and a safe external maps/deep link may be sufficient.
- Never fabricate coordinates, distance, route duration or road conditions.
- Actual route-time/distance claims require a selected maps/routing provider and provider-grounded results.
- Provider links must be allowlisted and safely constructed.

### Booking links

- Support outbound links only. Track destination/provider/campaign/click timestamp without capturing unnecessary personal data.
- Do not expose arbitrary redirect URLs that create an open-redirect vulnerability; resolve a server-side allowlisted provider/link identifier.
- No reservation or payment state machine in MVP.

---

## 9. Mobile client requirements

The PWA should be designed for narrow screens first, not merely shrink a desktop dashboard.

- Persian RTL throughout: navigation, form controls, mixed Persian/Latin content, dates, numbers and error states.
- Responsive Android Chrome and iOS Safari behavior; installation is optional and must be tested on real devices before pilot.
- Chat input remains usable with mobile keyboards; preserve drafts across transient navigation/network changes where safe.
- Long answers are broken into readable sections/cards; recommendation cards show the reason, source/freshness and action links.
- Trip requirements are visible and editable; the user can correct an extracted date, budget or preference.
- Loading, streaming, offline/connection-loss, retry, empty and provider-failure states are designed explicitly.
- Ask for geolocation permission only when a user action needs it; allow manual origin entry. Do not require location permission merely to use the app.
- Do not store auth tokens or secrets in insecure browser storage. Select an appropriate secure session/token strategy during the security design.

---

## 10. API contract baseline

Codex must produce an OpenAPI contract before implementing the complete vertical flow. Endpoint names below are starting candidates, not a final contract:

```text
POST   /api/v1/auth/...                         # auth method still open
GET    /api/v1/me
PATCH  /api/v1/me/profile
DELETE /api/v1/me                               # user data deletion request/workflow

POST   /api/v1/conversations
GET    /api/v1/conversations/{conversation_id}
POST   /api/v1/conversations/{conversation_id}/messages  # SSE-capable

GET    /api/v1/destinations                     # only approved/public records
GET    /api/v1/destinations/{destination_id}
GET    /api/v1/recommendations/{recommendation_id}

GET    /api/v1/itineraries/{itinerary_id}
PATCH  /api/v1/itineraries/{itinerary_id}

GET    /api/v1/weather                          # provider-backed, freshness-aware
POST   /api/v1/feedback
POST   /api/v1/outbound-clicks                   # allowlisted provider/link key only
```

Define common response/error envelopes, field validation, pagination, request IDs, authentication/authorization requirements and idempotency behavior where applicable. Do not create MVP endpoints for payment or booking confirmation.

---

## 11. Security, privacy and abuse controls

Minimum requirements before any external pilot:

- HTTPS for all public traffic; secure cookies/session strategy or carefully scoped short-lived access tokens.
- Server-side secret management; `.env` excluded from Git; commit only a placeholder `.env.example`.
- Authentication and object-level authorization: one user cannot read another user's profile, messages, trips or feedback.
- Rate limiting and quotas for chat/recommendation/LLM-heavy operations; protect against automated cost abuse.
- Bounded request sizes, strict input validation and safe output rendering.
- Prompt-injection defense: retrieved/user content is data, not instructions; no arbitrary tool execution or unrestricted URL fetching.
- Minimize personal data sent to remote AI providers. Do not send phone/email/account IDs when not needed for the task.
- Define retention and deletion behavior for user profile, conversation messages, derived trip context, logs and backups. Deletion must not silently leave ordinary application data indefinitely.
- Redact secrets and unnecessary PII from logs and error traces.
- No passport, payment-card or sensitive identity document collection in MVP.
- Admin/content import privileges are separated from ordinary user privileges and audited.
- Provider errors are translated into safe user-facing messages; stack traces and credentials are never returned.

The exact legal/privacy notices and hosting jurisdiction remain owner decisions and must be resolved before public release.

---

## 12. Reliability, performance and cost controls

Do not invent SLO numbers before measuring a working baseline. Instrument first, then set targets with the owner.

Required instrumentation:

- one request/correlation ID across API, conversation, retrieval, decision, integrations and LLM calls;
- structured logs with user identifiers pseudonymized or omitted where possible;
- API latency/error rate and database health;
- LLM provider/model alias, latency, tokens, estimated cost and failure class;
- retrieval/decision trace sufficient to explain the result without logging excessive raw user content;
- rate-limit and quota events;
- external provider freshness and error status.

Failure behavior:

- Remote LLM failure must not create fabricated travel facts. Return a recoverable error or a clearly limited result.
- Weather/map provider failure should not block unrelated catalog/recommendation functions.
- Use bounded timeouts and bounded retries. Do not retry non-idempotent operations blindly.
- Persist completed messages/results consistently; handle client disconnects and duplicate message submissions.
- Add caching only with explicit freshness/invalidation semantics.

---

## 13. Development and deployment environments

### 13.1 Local development

Known local environment:

- Project path: `C:\Projects\Ai_Tourism`
- Windows 11; Python 3.13.15 available through `py`.
- `uv` is installed.
- Docker Desktop Linux Engine is confirmed working.
- Existing PostgreSQL 17 Windows service and other projects' Docker containers are out of scope and must remain untouched.

Recommended local approach:

- Backend/frontend run natively on Windows during early development unless there is a concrete reason to containerize them.
- Run only the project's database in an isolated Compose service.
- Suggested service name: `ai-tourism-postgres`.
- Suggested host binding: `127.0.0.1:55433` (verify availability immediately before use).
- Use a project-specific persistent Docker volume such as `ai_tourism_pgdata`.
- Use a pinned, compatible PostgreSQL image that includes the required PostGIS and pgvector extensions. Select and verify the exact tag before writing Compose; do not use an unpinned `latest` tag.
- Do not map the database to `0.0.0.0` in local development.
- Do not start, stop, delete, rename or recreate other project containers or volumes.
- Do not change the Windows PostgreSQL 17 service.

The earlier port scan did not show a listener between 5432 and 5500, but availability must be rechecked at the time the Compose file is introduced.

### 13.2 Environments

Maintain separate configuration/data for:

1. **Development:** synthetic fixtures, local database, fake external providers by default.
2. **Test:** disposable isolated database, deterministic fake LLM/embedding/weather/maps adapters, no billable API calls in normal automated tests.
3. **Staging:** production-like topology, isolated credentials and dataset; real provider smoke tests only when explicitly enabled.
4. **Production:** verified real destination data, managed secrets, backups, monitoring, HTTPS and approved provider/hosting choices.

Do not use a developer's local model cache or local GPU as a hidden production dependency.

### 13.3 Production topology (logical, provider-neutral)

```text
PWA static hosting / CDN
          │ HTTPS
          ▼
Backend application service
          │ private network
          ├── PostgreSQL (private; backups + restore procedure)
          └── outbound HTTPS to approved AI/weather/maps providers
```

The exact cloud/region/provider is open. Before selection, compare service availability from the expected user locations, remote LLM API reachability, latency, data residency/privacy, cost, support and backup/restore capabilities. Do not provision infrastructure or select a paid plan without owner approval.

---

## 14. Testing strategy and acceptance gates

Automated tests must be deterministic and must not depend on real external API availability or spend money by default.

### 14.1 Test layers

- Unit: trip parsing/validation boundaries, hard constraints, eligibility, scoring, ranking, itinerary rules, URL allowlist, freshness policy and privacy logic.
- Contract: LLM/embedding/retrieval/weather/maps adapter schemas and error handling using fakes/stubs.
- Database integration: migrations, constraints, provenance filtering, geospatial queries (when implemented), transaction and deletion behavior against an isolated PostgreSQL instance.
- API integration: auth/object-level authorization, request validation, rate limits, SSE lifecycle, idempotency and safe error envelopes.
- Frontend: RTL/mobile rendering, editable trip fields, loading/disconnect/error states and recommendation/source rendering.
- E2E: complete synthetic trip journey from prompt to recommendations and editable itinerary.
- Security/regression: prompt-injection cases, cross-user access denial, synthetic-data exclusion from production queries, no secrets in bundles/logs.

### 14.2 MVP acceptance criteria

The MVP is not complete until all applicable criteria below are demonstrated:

1. A user can complete the primary journey on a narrow Android Chrome and iOS Safari viewport.
2. A Persian natural-language request becomes a validated, visible, editable trip profile.
3. Missing critical inputs trigger clarification instead of silent invention.
4. The system returns up to three eligible destinations. If fewer than three verified eligible destinations exist, it returns fewer and explains why; it must not pad the list with fabricated data.
5. Hard constraints cannot be overridden by LLM output or soft-preference scores.
6. Every recommendation reason is traceable to stored criteria, verified facts or cited evidence. Unknown facts are identified as unknown.
7. The user can create and edit a one-to-three-day itinerary. The system does not imply exact live scheduling when only approximate data exists.
8. Map links are generated only from validated destination/attraction identities and verified coordinates. No route duration or distance is invented.
9. Weather output carries provider and update/freshness time; stale/unavailable data is clearly labeled.
10. Booking actions are external allowlisted redirects only. The app does not claim to have booked or paid.
11. Users can access only their own private profile, conversations, trips and feedback.
12. A user deletion request has a documented, tested application-data lifecycle.
13. A remote LLM timeout/outage does not fabricate answers or corrupt conversation state.
14. Normal automated tests use synthetic fixtures and do not call billable third-party services.
15. AI usage, latency and errors are traceable by request ID without logging secrets.
16. Production/pilot mode rejects or hides synthetic and unverified tourism records by default.

### 14.3 Data gate for pilot

A technically green application is not ready for a real-user pilot until the owner-approved pilot geography has enough verified destination and attraction coverage to support the promised experience. Define the actual coverage and minimum dataset after selecting the initial launch region; do not make up a numeric threshold in code before that decision.

---

## 15. Recommended implementation phases for Codex

Codex should receive one bounded phase at a time. Each phase must start with a repository/state inspection and a written implementation plan. Do not ask Codex to "build the whole app" in one large task.

### Phase 0 — Detailed design and repository preparation

Deliverables (partly prepared in `AI_TOURISM_DB_PRECODEX_v0.2` and this handoff):

- repository-level `AGENTS.md` with engineering and safety rules;
- draft ADRs for confirmed boundaries and open decisions;
- 30-table MVP data model, ERD, exact expected row-count manifest and migration plan;
- provenance/verification/publication policy;
- isolated local PostgreSQL/PostGIS/pgvector Compose setup;
- deterministic database, spatial, provenance, security and RAG-storage tests;
- remaining OpenAPI for the first user journey, provider contracts, deployment and privacy/threat review.

**Additional owner gate:** before Codex begins Phase 1, the owner must run the database bootstrap and tests locally, share the full output, and resolve all failures. No application feature coding begins until the local DB test suite and exact row counts are green.

### Phase 1 — Technical skeleton

Deliverables:

- clean backend and frontend application skeleton;
- configuration/settings validation;
- isolated PostgreSQL Compose service and persistent volume;
- first migrations and database health check;
- API health/readiness endpoints;
- PWA shell with Persian RTL/mobile layout baseline;
- structured logging/request ID;
- local developer commands and `.env.example`;
- minimal tests proving a clean bootstrap.

Exit gate: another developer can clone the repo, configure local values, start the isolated DB and run the app/tests using documented commands. Existing projects remain untouched.

### Phase 2 — Identity, conversation and trip state

Deliverables:

- selected authentication strategy behind an interface;
- conversation/message persistence;
- versioned trip requirement model;
- extraction/validation service boundary;
- clarification state flow;
- editable trip summary UI;
- user isolation and authorization tests.

Use deterministic fixtures/fake LLM in tests. Remote provider is only exercised in explicitly enabled smoke tests.

### Phase 3 — Destination catalog and provenance

Deliverables:

- migrations to the approved 30-table MVP catalogue;
- one hierarchical place catalogue for destinations/POIs/attractions using `destination_type` and `parent_destination_id` (a separate attraction table requires a reviewed ADR);
- source/provenance and verification lifecycle;
- controlled import/seed mechanism;
- PostGIS/indexes if required by query use cases;
- strict exclusion of synthetic/unverified data from production recommendation queries;
- catalog tests and data-quality report.

Do not treat the current 15-row SQL seed as production-ready.

### Phase 4 — Retrieval integration and deterministic recommendations

Deliverables:

- stable `RetrievalPort` and test fake;
- integration with the owner-approved RAG implementation only after its contract is supplied/approved;
- deterministic hard-filter/score/rank service;
- recommendation run/factor/explanation persistence;
- traceable recommendation response;
- tests proving hard rules cannot be bypassed by LLM/RAG output.

Do not conduct another standalone embedding model benchmark or rewrite the RAG algorithm as part of this phase unless the owner explicitly requests it.

### Phase 5 — Remote LLM conversation and itinerary drafting

Deliverables:

- provider adapter configured server-side;
- structured extraction/clarification and source-grounded explanation;
- streaming response contract (SSE recommended);
- token/cost/latency instrumentation and per-user limits;
- bounded one-to-three-day itinerary draft;
- user editing and persistence;
- fake-provider integration tests and explicit opt-in smoke test.

### Phase 6 — Weather, maps and outbound links

Deliverables:

- provider adapters selected by owner;
- timestamped weather cache and stale-state UX;
- verified-coordinate map links;
- allowlisted external booking redirects and click records;
- graceful behavior when a provider is unavailable.

### Phase 7 — Profile, feedback, privacy and pilot hardening

Deliverables:

- basic profile and limited history;
- feedback flow;
- user data access/deletion behavior;
- security and abuse controls;
- mobile device E2E checks;
- backup/restore runbook and deployment checklist;
- pilot dataset verification gate and operational runbook.

A phase is done only when its acceptance tests pass, docs are updated, no unrelated project is changed and the owner receives a concise report of files changed, tests run, risks and remaining decisions.

---

## 16. Codex operating instructions

The following rules should be copied into repository-level `AGENTS.md` after owner review:

1. Inspect `git status`, current branch, HEAD and remote alignment before any work. Stop if the working tree is dirty or state is unexpected; report it instead of overwriting.
2. Never implement directly on `main`. Use an owner-approved feature branch based on the current `origin/main`.
3. Do not commit, push, merge, rebase shared branches or deploy unless explicitly requested.
4. Do not modify other repositories, global Python environments, Windows services, existing Docker containers or volumes.
5. Do not download AI models or datasets. Do not run billable API calls unless explicitly enabled by the owner.
6. Do not hard-code an LLM, embedding model, RAG algorithm or provider into domain logic. Use the approved adapters and configuration contracts.
7. Do not redesign or replace the owner's RAG implementation. Ask for its approved interface if integration details are missing; use a fake adapter meanwhile.
8. Do not implement future booking/payment/multi-agent features in the MVP.
9. Keep synthetic data separate and visibly labeled; never use it as production truth.
10. Never invent coordinates, sources, prices, availability, weather, route durations or destination facts.
11. Keep secrets out of source control, browser bundles, test output and logs.
12. Add/update tests for every behavior change. Prefer deterministic local tests and fake external providers.
13. Before broad edits, report a small plan and list files/components expected to change. Keep changes scoped to the assigned phase.
14. After implementation, report the exact branch/HEAD, changed files, commands/tests and outcomes, unverified behavior, risks and recommended next phase.
15. If an architectural decision not covered by an ADR blocks implementation, record the question and stop at a clean seam instead of silently making a costly irreversible choice.

### Definition of Done for every Codex task

- Acceptance criteria are met and demonstrated.
- Relevant tests pass locally; failures are explained, not hidden.
- Migrations are reversible or have a documented safe forward strategy.
- API/docs/config examples are updated.
- No secrets or synthetic/production data boundary violations.
- No unrelated file/project changes.
- Owner receives a clear diff summary and any open decisions.

---

## 17. Decisions still required from the owner

These are the genuine product/operational decisions that cannot be safely guessed. Some can remain open during the technical skeleton, but they must be settled before the relevant feature or pilot.

| Decision | Why it matters | Needed by |
|---|---|---|
| Confirm PWA vs native/cross-platform app | Sets client architecture and mobile capabilities | Before Phase 1 frontend |
| Confirm React/TypeScript and FastAPI | Pins main engineering stack | Before Phase 1 |
| Initial target market/geographic coverage | Defines data model defaults, currency/calendar, source coverage and pilot data | Before catalog/pilot |
| Authentication method (phone OTP, email, federated login) and SMS/email provider | Affects account UX, cost and security | Before Phase 2 |
| Remote LLM provider/model and deployment-region compatibility | Affects latency, cost, availability and data handling | Before live AI integration/staging |
| Whether embeddings run on the backend host or through a remote API | Affects deployment resources and network/cost | Before production retrieval deployment; not needed for interface design |
| Maps provider (deep links only vs routing API) | Determines accuracy and cost of distance/ETA claims | Before maps/routing integration |
| Weather provider | Determines coverage, freshness and forecast policy | Before weather integration |
| External booking destinations/partner links | Defines redirect behavior and tracking | Before outbound booking-link release |
| Initial hosting provider/region | Affects latency, data residency, API connectivity and operating cost | Before staging/production |
| Verified content owner/editor workflow | Defines how real destination records are reviewed and updated | Before real-data pilot |
| Privacy notice, retention and deletion policy | Required before collecting real user data | Before public pilot |

### Safe defaults until decisions are made

- Keep provider interfaces and configuration placeholders; do not choose paid vendors.
- Use fake adapters and synthetic data for development/tests.
- Use manual origin input; geolocation is optional and permission-based.
- Store dates/timestamps in an unambiguous API/database format and render the chosen local calendar in the client after the target market is confirmed.
- Keep currency explicit on every budget/price; do not assume toman vs rial or silently convert.
- Do not state distances, ETAs, weather or booking availability without an appropriate provider/source.

---

## 18. Source documents and current repository findings

The implementation baseline is derived from the repository's existing documents, with recommendations explicitly separated from source requirements:

- `README.md` — says the repository is an architecture/documentation baseline and that domain models, database schemas, API/event/agent contracts, state machines, security boundaries, deployment topology and implementation architecture remain to be designed.
- `docs/reference/AI_Travel_Advisor_Reference_Architecture.md` — product vision, MVP/RAG, mobile/product features, API and broader future platform capabilities.
- `docs/reference/ARCHITECTURE_ANALYSIS.md` — maturity assessment, modular-monolith MVP recommendation, target hybrid/agentic evolution and missing implementation artifacts.
- `database/tourism_points.sql` — provisional source-separated seed whose records remain pending/unverified with missing coordinates.

The broad reference documents contain material beyond the MVP. Codex must follow the bounded MVP scope in this handoff and the owner-approved ADRs, not implement every future capability merely because it is described in a reference document.

---

## 19. Immediate next engineering action

Do not start feature coding yet. The next high-value task is **Phase 0: convert this blueprint into repository-native, reviewed implementation artifacts**:

1. reconcile this blueprint with the full source architecture document;
2. confirm the few Phase 1 technology choices (PWA/native, frontend stack, backend stack, database extensions);
3. prepare ADRs, ERD/domain model, initial OpenAPI contract and threat/privacy boundary;
4. prepare `AGENTS.md` and a phase-specific Codex task packet;
5. only then authorize Codex to create the technical skeleton on a feature branch.

This handoff is intentionally provider- and embedding-model-neutral. Model selection is not a gate for the MVP architecture, and changes to a model must not require rewriting the application domain.


---

## 18. Current handoff status — 2026-11-04

| Work item | Status | Evidence / next action |
|---|---|---|
| Repository architecture baseline review | Complete | Repository main was read at `f242bbb649f04adc86944a3e95a2428f76367e46`; no application runtime existed in the baseline snapshot. |
| Mobile-first / modular-monolith / Remote LLM / replaceable RAG decisions | Drafted for owner review | This document and ADRs. Provider/model and initial hosting decisions remain open. |
| Root `AGENTS.md` | Prepared in DB prep ZIP | Install at repository root only after inspecting the target remains free/unchanged. |
| 30-table database schema / 419-row target after Migration 0006 | Base v0.2 applied and passed at 329 rows; additive batch 2 pending retest | `engineering/database-prep`; exact per-table counts in `docs/EXPECTED_ROW_COUNTS.md`. Pull feature branch and rerun Initialize/Test; do not reset Volume. |
| Offline seed content validator | Passed in preparation runtime | 12 synthetic documents/24 chunks plus 38 external source definitions, 17 factual documents and 34 factual chunks; SHA-256 and chunk character counts validated by updated offline validator (owner must rerun after pull). |
| Docker/PostgreSQL/PostGIS/pgvector bootstrap on owner's PC | Pending | Owner runs `Initialize-Database.ps1`. |
| Full database SQL integration suite | Pending | Owner runs `Test-Database.ps1`, shares complete output; all nine SQL test files (000 through 008) and exact 419-row count report must pass. |
| Semantic Persian RAG evaluation | Not part of this gate | Owner-controlled RAG implementation is integrated/tested later through the adapter; no temporary embedding benchmark is requested. |
| Codex application implementation | Not started | Do not hand off Phase 1 until the database tests above pass and remaining Phase 0 API/security decisions are reviewed. |

### Known scope of the initial data package

- 15 legacy supplied destinations remain pending/unverified and coordinate-free.
- 12 synthetic QA destinations, 12 synthetic documents and 24 synthetic chunks support deterministic tests only.
- 17 UNESCO-sourced Iranian heritage destinations, 38 source/provenance records, 17 original Persian knowledge documents and 34 non-synthetic chunks are seeded by two additive migrations. All remain `needs_review` and are not in production read views until editorial approval.
- 12 taxonomy categories are active; mapping/category counts are in the count manifest.
- The initial package intentionally leaves persistent embeddings, outbound clicks, AI usage calls and audit events empty.

The factual UNESCO records use official property descriptions and map coordinates. Coordinates are property/reference points, never presumed to be visitor gates or routable entrances. UNESCO descriptive pages display CC-BY-SA IGO 3.0; review attribution and share-alike obligations before commercial republication. The stored Persian text is a concise original paraphrase.


---

## 19. Database preparation update — Pre-Codex v0.3

The user ran the base database preparation on Windows PowerShell 5.1 and Docker Desktop. The owner-provided output established:

- PostgreSQL 17, PostGIS 3.6.4 and pgvector 0.8.7;
- exactly 30 project-owned tables and 329 rows for the base package;
- successful checksum, synthetic isolation, PostGIS, pgvector storage/retrieval, FK, publication-view and least-privilege checks;
- idempotent re-run of the first factual and synthetic seed batches.

This branch adds Migration `0006_verified_unesco_destination_seed_batch2` and its matching test. It adds seven source-backed Iranian UNESCO properties, sixteen sources/provenance records and links, seven category mappings, twenty-one tags, seven Persian documents and fourteen chunks. It also updates the offline validator, exact invariants, final count report and manifest.

**Expected state after Migration 0006: exactly 30 project-owned tables and 419 rows.** The existing 329-row database is upgraded additively; no database reset, container removal or Volume deletion is part of this operation.

Before application implementation is handed to Codex, the owner must pull this branch and freshly run:

```powershell
git pull --ff-only origin fix/initialize-database-powershell-inspect-v1
.\engineering\database-prep\scripts\Initialize-Database.ps1
.\engineering\database-prep\scripts\Test-Database.ps1
```

The final report must show 30 tables and exactly 419 expected rows, with every per-table count passing. The second factual batch must remain `needs_review`; production destination/retrieval views should remain empty. The RAG test in this phase validates storage mechanics only, not semantic Persian retrieval quality. Semantic evaluation is deferred until the owner-approved RAG implementation is integrated through its replaceable adapter.
