from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.modules.catalog.repository import CatalogueUnavailableError, list_production_destinations
from app.modules.catalog.schemas import (
    AvailableDestinationCatalogue,
    CatalogueUnavailable,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["catalogue"])


@router.get(
    "/destinations",
    response_model=AvailableDestinationCatalogue,
    responses={503: {"model": CatalogueUnavailable}},
    summary="Read published spatial destinations",
    description=(
        "Returns the complete bounded set from the approved production publication views. "
        "No trip text is accepted or stored."
    ),
)
def destinations(response: Response, settings: Settings = Depends(get_settings)):
    response.headers["Cache-Control"] = "no-store"
    try:
        items = list_production_destinations(settings)
    except CatalogueUnavailableError:
        return JSONResponse(
            status_code=503,
            content=CatalogueUnavailable().model_dump(mode="json"),
        )
    return AvailableDestinationCatalogue(count=len(items), items=items)
