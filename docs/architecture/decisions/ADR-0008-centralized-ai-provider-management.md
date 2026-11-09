# ADR-0008: Centralized AI Provider Gateway and Administrator Control Plane

- **Status:** Accepted owner requirement; implementation gated on approved administrator authentication/authorization
- **Decision date:** 2026-11-05
- **Scope:** MVP provider management and every AI capability
- **Source:** Explicit owner architecture requirement, 2026-11-05

## Context

AI infrastructure is an administrative concern. The travel product must remain provider-agnostic, with no provider setup or infrastructure detail exposed to ordinary PWA users. The MVP needs a replaceable server-side boundary for different providers, models, and capabilities without tying provider selection to domain logic or requiring redeployment for routine configuration changes.

## Decisions

1. All Chat, Vision, Embedding, and optional Reranking requests pass through a server-side **AI Provider Gateway** inside the backend modular monolith. The PWA never calls LM Studio, Ollama, or remote model providers directly.
2. The application owns routing. Domain code requests a capability through typed gateway interfaces; it cannot select a vendor, model, endpoint, profile, credential, or fallback from user input.
3. Only an authenticated and authorized primary system administrator can manage provider profiles through a protected administrative interface after deployment. There is no provider configuration or model selector for ordinary users, no anonymous admin access, and no placeholder admin authentication.
4. The control plane supports multiple profiles; independent capability/model configuration where supported; protected credential entry and rotation; connection testing; activate/deactivate; and controlled rollback to a prior validated revision.
5. Configuration is versioned and validated before activation. Activation publishes an atomic runtime configuration snapshot without a full redeployment or process restart. In-flight requests use one consistent snapshot. Rollback reactivates a previously validated revision and is audited.
6. Provider credentials remain server-side and are protected at rest by an approved secret-storage/encryption mechanism. Runtime configuration and audit events may contain secret references and non-secret metadata only; they never contain credential values. Secrets are excluded from public responses, client bundles, browser storage, logs and error details.
7. Failover is disabled unless an administrator explicitly configures an eligible fallback and order. In particular, local-to-remote fallback must never happen silently by default. Routing decisions and configuration changes are audited without recording secrets or raw user content.
8. Provider names, model identifiers, endpoints, profile/routing details, credentials and provider/infrastructure health are not exposed through ordinary-user interfaces or public product API responses. Operational and admin status belongs to protected operations surfaces. Provider-specific failures map to stable, provider-neutral user messages.
9. Provider selection, profile state, activation and fallback policy are never persisted as end-user preferences.
10. No gateway, provider integration, or admin interface is part of Phase 1. Real provider use is gated on the approved admin authentication/authorization design and the relevant privacy, residency, and provider decisions.

## Consequences

- Provider-specific SDKs, URLs, identifiers and credentials stay in gateway adapters and protected control-plane modules, outside the PWA and domain decision core.
- Runtime reconfiguration needs validated revisions, safe concurrent publication, bounded connection tests, credential rotation behavior and recovery/rollback tests.
- Admin authentication, authorization, bootstrap recovery, secret-storage technology and provider-specific capability support remain separate decisions; this ADR does not select them.
- Public health/readiness routes and deployment routing must not expose operational/provider status to ordinary or anonymous product traffic.

## Required verification before live AI release

- Authorization tests prove ordinary and anonymous principals cannot call admin operations or obtain provider metadata.
- Tests prove the browser/API bundle and logs/responses contain no secret values or internal endpoints.
- Tests prove config activation is atomic and takes effect without restart, rollback is controlled and audited, and fallback is absent unless explicitly configured.
- Provider failures return provider-neutral, localized safe messages; deterministic validation and decision rules remain authoritative.

## Revisit when

The owner approves the administrator authentication design, secret-storage approach, deployment/hosting boundary, and any capability-specific provider contract. Vendor and model choices remain replaceable profile data, not an architecture decision.
