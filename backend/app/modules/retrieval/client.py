"""Safe invocation and error mapping for an injected RetrievalPort."""

from __future__ import annotations

from app.modules.retrieval.contracts import (
    RetrievalPort,
    RetrievalPortError,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalUnavailable,
    validate_response_for_request,
)


async def retrieve_validated(
    port: RetrievalPort,
    request: RetrievalRequest,
) -> RetrievalResponse:
    """Call once, validate the response, and map all adapter errors safely."""

    try:
        response = await port.retrieve(request)
    except RetrievalPortError:
        raise
    except Exception:
        raise RetrievalUnavailable() from None
    return validate_response_for_request(request, response)
