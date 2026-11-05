import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.health import router as health_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("ai_tourism")
app = FastAPI(title="AI Tourism API", version="0.1.0")
app.include_router(health_router)
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied = request.headers.get("X-Request-ID", "")
    request_id = supplied if _REQUEST_ID.fullmatch(supplied) else str(uuid.uuid4())
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.error("request.failed", extra={"request_id": request_id, "result": "error"})
        response = JSONResponse(status_code=500, content={"error": {"code": "internal_error"}})
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request.completed",
        extra={"request_id": request_id, "result": str(response.status_code),
               "latency_ms": round((time.perf_counter() - started) * 1000, 2)},
    )
    return response
