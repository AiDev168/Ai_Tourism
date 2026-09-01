# AI Travel Advisor — Architecture Analysis & Proposed Target Architecture

## 1. Scope and status

This document is the architectural analysis derived from the supplied **AI Travel Advisor Reference Architecture** document, followed by additional architecture proposals made during review.

The source document is the baseline. The sections explicitly labeled **Proposed / Analysis** are architectural recommendations and are not presented as if they were already specified by the source.

---

## 2. Architecture maturity assessment

| Architecture level | Assessment |
|---|---|
| Business Architecture | Good |
| Product / Domain Architecture | Good |
| System / Conceptual Architecture | Good |
| Logical Architecture | Medium–Good |
| Detailed Architecture | Incomplete |
| Physical / Deployment Architecture | Conceptually good, implementation incomplete |
| Implementation Architecture | Not yet specified |

The source already defines the product vision, actors, C4 context/container/component/deployment views, major services, business flows, UML/BPMN concepts, event-driven communication, RAG/knowledge architecture, decision engine, recommendation engine, XAI, security, observability, deployment and migration direction. It is therefore a strong **architecture baseline**, but it is not yet an implementation-ready detailed system specification.

---

# 3. Proposed Data Architecture

The source recommends PostgreSQL as the main database, Redis for cache/temporary state, a vector database for RAG, and object storage for files. For the MVP, a PostgreSQL + pgvector approach with modular schemas is recommended.

## 3.1 PostgreSQL schema boundaries

```text
PostgreSQL
├── identity
├── user
├── conversation
├── travel
├── knowledge
├── recommendation
├── booking
├── notification
├── feedback
├── analytics
├── ai
├── audit
└── system
```

For the MVP these can live in one PostgreSQL instance while retaining domain ownership. They can later be separated if scale or organizational boundaries justify it.

## 3.2 Identity

### users

```text
id
external_id
email
phone
password_hash / auth_provider_id
status
language
created_at
updated_at
last_login_at
```

### roles

```text
id
name
description
```

### user_roles

```text
user_id
role_id
```

### consents

```text
id
user_id
consent_type
version
granted
granted_at
revoked_at
```

## 3.3 User profile and preferences

### user_profiles

```text
user_id
display_name
language
home_city_id
default_budget_level
preferred_accommodation
notification_preferences
privacy_preferences
profile_version
created_at
updated_at
```

### user_preferences

```text
id
user_id
preference_type
value
weight
source
confidence
valid_from
valid_until
is_long_term
created_at
updated_at
```

Long-term preferences should be separated logically from trip-specific preferences.

## 3.4 Conversation

### conversations

```text
id
user_id
channel
language
status
started_at
ended_at
last_message_at
```

### messages

```text
id
conversation_id
user_id
role
content
message_type
model_id
model_version
token_input
token_output
latency_ms
created_at
```

### conversation_context

```text
conversation_id
context_version
structured_context JSONB
updated_at
```

### conversation_summaries

```text
id
conversation_id
summary
model_version
created_at
```

### conversation_entities

```text
id
conversation_id
message_id
entity_type
entity_value
confidence
source
```

## 3.5 Travel domain

### trips

```text
id
user_id
conversation_id
origin
start_date
end_date
duration_days
budget_min
budget_max
currency
traveler_count
travel_type
status
created_at
updated_at
```

### trip_travelers

```text
id
trip_id
type
age_group
relationship
special_requirements
```

### trip_preferences

```text
id
trip_id
preference_type
value
weight
priority
```

### trip_constraints

```text
id
trip_id
constraint_type
operator
value
severity
is_hard_constraint
```

Hard constraints must be evaluated deterministically and must not be overridden by a high recommendation score.

## 3.6 Knowledge domain

### destinations

```text
id
name
slug
country_id
province_id
city_id
latitude
longitude
description
destination_type
family_friendly
difficulty
status
created_at
updated_at
```

### destination_categories

```text
id
name
```

### destination_category_map

```text
destination_id
category_id
```

### attractions

```text
id
destination_id
name
description
type
latitude
longitude
duration_minutes
estimated_cost
difficulty
family_friendly
accessibility
safety_notes
status
```

### accommodations

```text
id
destination_id
name
type
rating
price_level
family_friendly
amenities
latitude
longitude
provider_id
```

### activities

```text
id
destination_id
name
type
description
duration
cost
difficulty
family_friendly
season
```

### transport_options

```text
id
origin
destination_id
transport_type
duration
estimated_cost
availability
```

## 3.7 Source and provenance

### sources

```text
id
name
source_type
url
authority_level
reliability_score
provider
created_at
updated_at
```

### knowledge_documents

```text
id
source_id
title
content
content_type
language
country
province
city
category
valid_from
valid_until
last_updated
reliability_score
status
version
```

### knowledge_chunks

```text
id
document_id
chunk_index
content
token_count
metadata JSONB
created_at
```

The knowledge model should explicitly preserve provenance, validity windows, source reliability and versioning.

## 3.8 Vector store

For the MVP:

```text
PostgreSQL + pgvector
```

Logical embedding record:

```text
chunk_id
embedding
embedding_model
embedding_version
metadata
created_at
```

A dedicated vector database can be introduced later if scale or retrieval workload requires it.

## 3.9 Dynamic data

### weather_snapshots

```text
id
destination_id
provider_id
forecast_date
temperature_min
temperature_max
precipitation_probability
humidity
wind_speed
condition
warning
raw_response
fetched_at
expires_at
```

Weather, live prices, hotel capacity and other volatile data should not be treated as permanent knowledge truth; they should be obtained through live integrations and cached with explicit freshness/expiry semantics.

## 3.10 Recommendation domain

### recommendation_requests

```text
id
user_id
trip_id
conversation_id
request_context JSONB
algorithm_version
created_at
```

### recommendations

```text
id
request_id
destination_id
rank
final_score
confidence
status
created_at
```

### recommendation_scores

```text
id
recommendation_id
criterion
raw_score
normalized_score
weight
weighted_score
```

### recommendation_penalties

```text
id
recommendation_id
type
value
reason
```

### recommendation_rewards

```text
id
recommendation_id
type
value
reason
```

### recommendation_explanations

```text
id
recommendation_id
primary_reason
secondary_reasons JSONB
warnings JSONB
alternatives JSONB
sources JSONB
explanation_level
model_version
created_at
```

## 3.11 Booking

### booking_providers

```text
id
name
provider_type
api_base_url
status
reliability_score
```

### booking_requests

```text
id
user_id
trip_id
recommendation_id
service_type
provider_id
status
idempotency_key
created_at
```

### bookings

```text
id
booking_request_id
provider_booking_id
service_type
status
amount
currency
confirmed_at
cancelled_at
```

### booking_items

```text
id
booking_id
service_id
service_type
start_at
end_at
quantity
price
metadata JSONB
```

## 3.12 Payment

### payment_transactions

```text
id
booking_id
user_id
amount
currency
provider
provider_transaction_id
status
initiated_at
completed_at
failed_at
```

Card data should not be stored by the application.

## 3.13 Feedback

### feedback

```text
id
user_id
conversation_id
recommendation_id
trip_id
feedback_type
rating
comment
created_at
```

### recommendation_feedback

```text
id
recommendation_id
accepted
rejected
rejection_reason
edited
created_at
```

## 3.14 Notifications

### notifications

```text
id
user_id
booking_id
type
channel
template
status
scheduled_at
sent_at
delivered_at
failed_at
```

### notification_attempts

```text
id
notification_id
provider
attempt_number
status
error
created_at
```

## 3.15 Event store

### domain_events

```text
event_id
event_type
event_version
producer
aggregate_type
aggregate_id
correlation_id
causation_id
user_id
payload JSONB
metadata JSONB
created_at
processed_at
```

### event_processing

```text
event_id
consumer
status
attempt_count
last_error
processed_at
```

This supports idempotency, tracing, replay and asynchronous processing.

## 3.16 AI observability

### ai_model_calls

```text
id
request_id
conversation_id
agent_id
model_provider
model_name
model_version
task_type
input_tokens
output_tokens
latency_ms
estimated_cost
status
created_at
```

### prompt_versions

```text
id
name
version
template
status
created_at
```

### agent_runs

```text
id
conversation_id
agent_type
agent_version
task
input
output
status
latency
cost
created_at
```

## 3.17 Audit

### audit_logs

```text
id
actor_id
actor_type
action
resource_type
resource_id
before_state
after_state
correlation_id
created_at
```

## 3.18 Analytics

At higher scale, analytics should be separated from OLTP:

```text
PostgreSQL
      │
      ▼
Event Bus
      │
      ▼
Data Warehouse
      ├── user_events
      ├── conversation_facts
      ├── recommendation_facts
      ├── booking_facts
      ├── ai_usage_facts
      └── feedback_facts
```

---

# 4. Redis and object storage

## Redis

Use Redis for:

- session state
- short-term conversation context
- cache
- rate limiting
- distributed locks
- idempotency keys
- temporary booking state
- job state

Redis should not become the system-of-record database.

## Object storage

Use object storage for:

```text
/images
/documents
/pdfs
/tickets
/vouchers
/raw-data
/backups
/ai-artifacts
/reports
```

PostgreSQL stores metadata and object references, not large binary files.

---

# 5. Architecture alternatives

## A — Modular Monolith

```text
Web / Mobile
     │
     ▼
API Backend
     │
 ┌───┼───────────────┐
 │   │               │
Conversation     Decision      Knowledge
 │   │               │             │
 └───┴───────────────┴─────────────┘
              │
         PostgreSQL
              │
           pgvector
```

**Advantages:** low operational complexity, fast MVP delivery, simple transactions, easy debugging.

**Disadvantages:** independent scaling is limited and boundaries can erode if not enforced.

**Recommendation:** best MVP architecture.

## B — Microservices

```text
API Gateway
   │
   ├── Conversation
   ├── Decision
   ├── Knowledge
   ├── Recommendation
   ├── Booking
   ├── User
   ├── Notification
   └── Analytics
            │
        Event Bus
```

**Advantages:** independent deployment and scaling, team autonomy, failure isolation.

**Disadvantages:** distributed systems complexity, network failures, observability and transaction complexity.

**Recommendation:** evolution target, not day-one architecture.

## C — Event-Driven Platform

```text
UserMessageReceived
        │
        ▼
    Event Bus
     ├── Intent
     ├── Preference
     ├── Recommendation
     ├── Analytics
     └── Memory
```

This is highly useful for analytics, notifications, audit, learning and decoupling, but the core decision path should remain synchronous where an immediate answer is required.

## D — AI-Centric Agentic Architecture

```text
Conversation Agent
        │
        ▼
Agent Orchestrator
 ├── Destination Agent
 ├── Weather Agent
 ├── Budget Agent
 ├── Transport Agent
 ├── Safety Agent
 └── Planning Agent
        │
        ▼
Decision Engine
        │
        ▼
Recommendation
        │
        ▼
XAI
```

This is appropriate for later phases, not as the default MVP architecture.

## E — Hybrid Architecture (recommended target)

```text
Client
  │
API Gateway
  │
Conversation
  │
Agent Orchestrator
  │
 ├── AI Agents
 ├── Knowledge Agents
 └── Planning Agents
  │
  ▼
Deterministic Decision Core
 ├── Rules
 ├── Constraints
 ├── Safety
 ├── Scoring
 └── Ranking
  │
  ▼
Recommendation
  │
  ▼
XAI
  │
  ▼
User
```

Alongside the synchronous path:

```text
Event Bus
 ├── Analytics
 ├── Notification
 └── Audit
```

**Recommendation:** this is the preferred long-term architecture.

---

# 6. Proposed Agentic Swarm Architecture

A fully decentralized peer-to-peer swarm is not recommended. The preferred pattern is:

> **Hierarchical Agentic Swarm + Central Orchestrator + Deterministic Decision Core**

## 6.1 High-level structure

```text
                         USER
                           │
                           ▼
                  Conversation Agent
                           │
                           ▼
                 Travel Orchestrator
                           │
          ┌────────────────┼─────────────────┐
          │                │                 │
          ▼                ▼                 ▼
   Requirement Agent  Knowledge Agent   Planning Agent
          │                │                 │
          │        ┌───────┼────────┐        │
          │        ▼       ▼        ▼        │
          │     Weather  Maps   Travel Data  │
          │        Agent   Agent    Agents   │
          │                                  │
          └────────────────┬─────────────────┘
                           ▼
                    Deterministic Core
                    ├── Safety Rules
                    ├── Constraints
                    ├── Budget
                    ├── Scoring
                    └── Ranking
                           │
                           ▼
                    Recommendation
                           │
                           ▼
                      Explanation
                           │
                           ▼
                         USER
```

## 6.2 Agent categories

### Cognitive agents

- Conversation Agent
- Intent Agent
- Preference Agent
- Planning Agent
- Explanation Agent

### Knowledge agents

- Destination Knowledge Agent
- RAG Agent
- Weather Agent
- Maps Agent
- Local Information Agent
- Regulation Agent

### Decision-facing agents

- Constraint Agent
- Safety Agent
- Budget Agent
- Alternative Agent

However, Safety, scoring and hard-constraint enforcement should preferably be deterministic services behind stable APIs rather than LLM-only agents.

### Operational agents

- Booking Agent
- Payment Agent
- Notification Agent
- Support Agent

These become more relevant in later commercial phases.

---

# 7. Orchestrator design

The orchestrator should:

```text
Understand Task
      ↓
Create Plan
      ↓
Select Agents
      ↓
Dispatch Tasks
      ↓
Parallel Execution
      ↓
Validate Results
      ↓
Resolve Conflicts
      ↓
Decision Engine
      ↓
Final Response
```

It should not independently invent destination scores or bypass deterministic business rules.

## 7.1 Dynamic routing

Do not activate the whole swarm for every request.

Simple request:

```text
"What is the weather in Shiraz tomorrow?"
       ↓
Weather Agent only
```

Complex request:

```text
Family + budget + duration + multiple destinations + weather + accommodation
       ↓
Orchestrator
       ├── Requirement
       ├── Knowledge
       ├── Weather
       ├── Maps
       ├── Accommodation
       ├── Budget
       ├── Safety
       └── Planning
```

This reduces latency and LLM cost.

## 7.2 DAG-based orchestration

Prefer a controlled task DAG over unrestricted agent-to-agent calls:

```text
Requirement
    │
    ├──── Knowledge ────┐
    ├──── Weather ──────┤
    ├──── Maps ─────────┤
    └──── Budget ───────┤
                         ▼
                    Candidate Set
                         │
                    Constraints
                         │
                    Recommendation
                         │
                    Explanation
```

Independent tasks should execute in parallel.

---

# 8. Agent contracts

Define explicit contracts rather than relying on free-form messages.

## AgentTask

```text
task_id
parent_task_id
agent_type
objective
input_context
constraints
deadline
priority
correlation_id
```

## AgentResult

```text
task_id
agent_type
status
confidence
result
sources
warnings
execution_time
cost
```

Additional stable concepts:

```text
AgentRequest
AgentResponse
AgentError
AgentCapability
AgentTask
AgentResult
```

These contracts enable audit, evaluation, tracing, retries and deterministic orchestration.

---

# 9. Memory architecture

Use three distinct memory classes:

## Working memory

Redis:

```text
current conversation
current task
current plan
temporary context
```

## Long-term user memory

PostgreSQL:

```text
preferences
travel history
accepted/rejected destinations
```

## Semantic memory

Vector store:

```text
knowledge
relevant past conversations
semantic memories
```

Memory and RAG should remain separate concepts even though both may use vector retrieval.

---

# 10. Deterministic decision core

A key architectural rule is:

> LLMs interpret and plan; deterministic services enforce hard rules and calculate business decisions that must be reproducible.

LLMs are appropriate for:

- natural-language understanding
- intent detection
- preference extraction
- summarization
- planning
- explanation
- conversational interaction

Deterministic code/rules are appropriate for:

- budget constraints
- safety rules
- hard constraints
- date calculations
- capacity
- scoring calculations
- authorization
- payment
- idempotency
- compliance rules

Example:

```text
LLM
  ↓
"I am traveling with a small child"
  ↓
Structured constraint
  ↓
Rule Engine
  ↓
Reject activity if difficulty == HARD
```

The LLM should not be the final authority for such a rule.

---

# 11. XAI architecture

The explanation layer should not invent reasons after the fact.

It should receive:

```text
Score Breakdown
Applied Rules
Penalties
Rewards
Sources
Warnings
```

and render them into a human-readable explanation.

Logical flow:

```text
Recommendation
     │
     ├── Scores
     ├── Rules
     ├── Penalties
     ├── Rewards
     └── Sources
             │
             ▼
       Explanation Agent
             │
             ▼
       User-facing reason
```

---

# 12. Recommended evolution path

The source's MVP-first direction can be formalized as:

```text
                    Target Architecture
                           │
          ┌────────────────┴────────────────┐
          │                                 │
   Modular Monolith                   Agentic Platform
          │                                 │
          ▼                                 ▼
       MVP / V1                         Later phase
          │
          ▼
  Modular boundaries
          │
          ▼
Selective extraction
          │
          ▼
Event-driven integration
          │
          ▼
Cloud-native scale
```

The architectural objective is not to deploy every future component immediately. The objective is to establish clean domain boundaries and contracts so future extraction is possible without rewriting the business model.

---

# 13. What is still required for implementation-ready detailed architecture?

The current baseline still needs formal definitions for:

```text
Domain model
Entity relationships
Aggregate boundaries
Database schemas and indexes
Transaction boundaries
API contracts / OpenAPI
Event contracts / schemas
Agent capability registry
Agent state machines
Booking state machine
Payment state machine
Conversation state machine
Error taxonomy
Retry / timeout policies
Concurrency model
Consistency model
Security trust boundaries
Secrets / credential boundaries
Data retention and deletion lifecycle
Observability schema
SLOs / SLIs
Deployment topology
Environment configuration
CI/CD architecture
Disaster recovery
Capacity assumptions
```

These are the next artifacts required to move from architecture baseline to **Detailed System Architecture** and then to implementation architecture.

---

# 14. Final architectural recommendation

The recommended target is:

> **Hybrid Architecture + Hierarchical Agentic Swarm + Central Orchestrator + Deterministic Decision Core + Event-Driven Side Plane**

with:

```text
MVP
  → Modular Monolith
  → PostgreSQL + pgvector
  → Redis
  → Object Storage
  → synchronous core decision path
  → asynchronous analytics/notification/audit

Scale-up
  → selective service extraction
  → event bus
  → dedicated vector infrastructure if required
  → independent AI/agent workers
  → data warehouse

Advanced Agentic phase
  → hierarchical dynamic swarm
  → DAG orchestration
  → explicit agent contracts
  → tool/API mediated access
  → deterministic safety/constraint/scoring core
  → traceable XAI
```

This approach preserves the source document's MVP-first intent while providing a technically credible path toward a production-grade agentic travel platform.
