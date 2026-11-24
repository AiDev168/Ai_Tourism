"""Fail-closed guards for privileged platform writes.

The public staging runtime does not yet have an approved general reviewer MFA
step-up contract. Read-only review queues remain available to explicitly
granted identities, while consequential review/publication transitions are
blocked until that contract exists. Local development and isolated acceptance
can still exercise the existing audited workflow.
"""

from fastapi import HTTPException

PUBLIC_RUNTIME_ENVS = frozenset({"staging", "production", "prod", "preview"})


def privileged_admin_writes_available(app_env: str) -> bool:
    return app_env.strip().lower() not in PUBLIC_RUNTIME_ENVS


def require_privileged_admin_step_up(app_env: str) -> None:
    if not privileged_admin_writes_available(app_env):
        raise HTTPException(status_code=403, detail="privileged_admin_step_up_unavailable")
