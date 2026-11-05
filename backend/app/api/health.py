from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import check_database

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live():
    return {"status": "live"}


@router.get("/ready")
def ready():
    if not check_database(get_settings()):
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
