import logging
import re
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.health import router as health_router
from app.api.catalogue import router as catalogue_router
from app.api.auth import router as auth_router
from app.modules.identity.auth_service import AuthenticationUnavailable
from app.modules.identity.sms import DisabledSmsAdapter, FakeSmsAdapter

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("ai_tourism")
app = FastAPI(title="AI Tourism API", version="0.1.0")
app.include_router(health_router)
app.include_router(catalogue_router)
app.include_router(auth_router)
app.state.sms_adapter = FakeSmsAdapter() if settings.auth_sms_adapter == "fake" else DisabledSmsAdapter()
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@app.exception_handler(AuthenticationUnavailable)
async def authentication_unavailable(_request: Request, _error: AuthenticationUnavailable):
    return JSONResponse(status_code=503, content={"error": {"code": "authentication_unavailable"}})


@app.exception_handler(HTTPException)
async def safe_http_exception(_request: Request, error: HTTPException):
    if error.status_code == 401:
        return JSONResponse(status_code=401, content={"error": {"code": "unauthenticated"}})
    return JSONResponse(status_code=error.status_code, content={"error": {"code": "request_rejected"}})


@app.exception_handler(RequestValidationError)
async def safe_validation_exception(_request: Request, _error: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "invalid_request"}})


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
