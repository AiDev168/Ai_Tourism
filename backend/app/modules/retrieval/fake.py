"""Deterministic test adapter for the application RetrievalPort."""

from __future__ import annotations

from collections.abc import Mapping

from app.modules.retrieval.contracts import RetrievalRequest, RetrievalResponse


class DeterministicRetrievalFake:
    """Return configured immutable results; default to an honest no-evidence result."""

    def __init__(
        self,
        responses: Mapping[tuple[str, str, str], RetrievalResponse] | None = None,
    ) -> None:
        self._responses = dict(responses or {})
        self.requests: list[RetrievalRequest] = []

    async def retrieve(self, request: RetrievalRequest, /) -> RetrievalResponse:
        self.requests.append(request)
        key = (request.corpus, request.locale, request.query)
        configured = self._responses.get(key)
        if configured is not None:
            return configured.model_copy(deep=True)
        return RetrievalResponse(
            request_id=request.request_id,
            corpus=request.corpus,
            locale=request.locale,
            status="no_evidence",
            retrieval_version="deterministic-fake-v1",
            evidence=[],
        )
