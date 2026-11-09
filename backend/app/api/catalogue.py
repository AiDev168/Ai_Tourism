from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.modules.catalog.repository import (
    CatalogueUnavailableError,
    list_production_culinary,
    list_production_destinations,
)
from app.modules.catalog.schemas import (
    AvailableDestinationCatalogue,
    AvailableCulinaryCatalogue,
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


@router.get(
    "/culinary",
    response_model=AvailableCulinaryCatalogue,
    responses={503: {"model": CatalogueUnavailable}},
    summary="Read published non-spatial culinary knowledge",
    description=(
        "Returns only approved, published and source-backed non-spatial culinary knowledge "
        "from the approved production publication view. No destination identity or spatial data is returned."
    ),
)
def culinary(
    response: Response,
    locale: Literal["fa-IR", "en-US", "ar"],
    category: str | None = Query(
        default=None, min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]{1,63}$"
    ),
    settings: Settings = Depends(get_settings),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        return list_production_culinary(settings, locale=locale, category=category)
    except CatalogueUnavailableError:
        return JSONResponse(
            status_code=503,
            content=CatalogueUnavailable().model_dump(mode="json"),
        )
