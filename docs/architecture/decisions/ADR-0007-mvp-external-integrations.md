# ADR-0007: External Integrations in the MVP

- **Status:** Accepted for MVP scope; provider choices remain open
- **Decision date:** 2026-11-05
- **Sources:** root `AGENTS.md`; `docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.3.md` sections 2, 8 and 17.

## Decision

1. **Booking:** the MVP may display allowlisted external provider links and record a click. It does not search/hold/confirm live inventory, create reservations, issue tickets, collect payment, cancel or refund.
2. **Redirect security:** the client submits a known link identifier, not an arbitrary destination URL. The backend resolves the active, allowlisted target. Do not implement an open redirect.
3. **Maps:** verified coordinates may be exposed through safe map/deep links. Distance, ETA, route conditions or access instructions require a selected provider and source-backed result; they must not be inferred from a property-reference point.
4. **Weather:** weather is volatile and must be accompanied by provider, location, forecast time and freshness metadata. Do not let an LLM fill missing or stale weather facts.
5. Provider names, commercial plans, API keys, data-region compatibility, rate/cost policies and production cache policy remain open decisions.
6. The initial local/dev implementation uses fake adapters in normal automated tests. No paid API calls occur by default.

## Consequences

- No booking/payment state machine or payment-related schema is added to the MVP.
- Provider integrations remain replaceable server-side adapters.
- External-provider failure must degrade the relevant feature without corrupting conversation or trip state.

## Revisit when

The owner approves a specific partner/provider or the product scope expands to transactional booking/payment in a separately reviewed phase.
