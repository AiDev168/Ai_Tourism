# AI Tourism — Repository Instructions for Coding Agents

## Project intent

Build a Persian-first, mobile-first AI Travel Advisor. The current target is a genuinely usable MVP, not a demo-only interface. Read `README.md`, `docs/reference/AI_Travel_Advisor_Reference_Architecture.md`, `docs/reference/ARCHITECTURE_ANALYSIS.md`, and the latest approved implementation/handoff documents before proposing changes.

## Non-negotiable scope boundaries

- MVP architecture is a **modular monolith** with explicit module boundaries. Do not introduce microservices, an event broker, Kubernetes, a multi-agent swarm, or Redis without a measured requirement and explicit approval.
- Client is mobile-first and PWA-oriented. The backend is the trust boundary; the client never connects directly to PostgreSQL or receives provider secrets.
- Remote LLM calls are performed by backend adapters. Provider/model configuration must be replaceable and secrets must remain server-side.
- Embedding and RAG implementations are replaceable. Do not hard-code a specific embedding model, vector dimension, provider, reranker, or retrieval algorithm into domain logic or database migrations. Do not rewrite the owner's separate RAG work without explicit approval.
- Deterministic code enforces hard trip constraints, eligibility, scoring rules and final ranking. LLM output is not authoritative for hard constraints or factual provenance.
- MVP may redirect to external booking providers and record clicks. Do not implement payment capture, booking transactions, ticket issuance, cancellation, refunds or inventory synchronization in MVP.
- The MVP itinerary is a simple editable 1–3 day plan. Do not build a full live route optimizer unless separately approved.

## Data integrity and provenance

- A destination or knowledge document must preserve source provenance, retrieval time, content/version hash and review/publication status.
- Never promote user-supplied or unverified data to verified/active by inference.
- Synthetic records must be clearly marked (`is_synthetic`, `record_origin='synthetic_fixture'`, and test-only status) and must never be returned by production recommendation/retrieval queries.
- Do not fabricate coordinates, opening hours, prices, route durations, availability, safety facts, weather, accessibility or source citations. Unknown values remain unknown/NULL.
- Do not copy synthetic test fixtures into production seeds or real-data imports.
- Database changes must be migration-based, reversible where practical, and backed by tests for table counts, constraints, foreign keys, seed idempotency, provenance and key retrieval paths.

## Repository and Git safety

- Inspect `git status`, current branch, HEAD and remote tracking state before making changes.
- Never work directly on `main`; use a clearly named feature branch after the user authorizes implementation.
- Do not reset, clean, force-push, rebase shared history, delete branches, remove Docker volumes, drop databases, or overwrite user data.
- Do not commit, push, merge, open PRs, or modify GitHub remotely unless the user explicitly authorizes that exact action.
- Preserve user changes. Stop if the working tree is dirty and a safe boundary cannot be established.
- Before any database reset or destructive data migration, require a backup and explicit approval. Prefer additive migrations and isolated development databases.

## Development and dependencies

- Windows development is supported. Use the repository's documented Python version and `uv` environment once selected; do not install global packages.
- Keep development, test, staging and production databases separate.
- Do not download large models, invoke paid model APIs, or make network/provider calls during tests unless explicitly authorized.
- External APIs must be behind typed adapters with timeouts, bounded retries, cost/rate limits, error mapping and mockable test interfaces.
- No secrets in source files, SQL seeds, logs, test fixtures or client bundles. Use a separate least-privilege application DB role; the database owner/superuser is for migrations and administration only.

## Testing and delivery

- Prioritize reproducible local validation and meaningful unit/integration tests; do not over-engineer CI before core functionality exists.
- Database tests must verify exact expected table/fixture counts and fail on unexpected or duplicate rows.
- RAG storage tests and semantic retrieval-quality tests are separate concerns. Do not claim semantic quality from a vector-storage smoke test.
- For every task, state: inspected state, files changed, migrations/data changed, commands/tests actually run, pass/fail results, known gaps and next safe action.
- Never claim a test passed unless it was actually executed and its output was inspected.
- Keep each phase small and reviewable. Ask before expanding beyond its acceptance criteria.
