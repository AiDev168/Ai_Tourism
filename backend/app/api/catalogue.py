from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.modules.catalog.repository import (
    CatalogueUnavailableError,
    list_production_culinary,
    list_production_destinations,
    list_production_destination_page,
    sign_catalogue_cursor,
    verify_catalogue_cursor,
)
from app.modules.catalog.schemas import (
    AvailableDestinationCatalogue,
    AvailableCulinaryCatalogue,
    CatalogueUnavailable,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["catalogue"])
v2_router = APIRouter(prefix="/api/v2/catalog", tags=["catalogue-v2"])


@v2_router.get("/destinations")
def destination_page(
    response: Response,
    settings: Settings = Depends(get_settings),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2048),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    province: str | None = Query(default=None, min_length=1, max_length=120),
    destination_type: str | None = Query(default=None, min_length=1, max_length=64),
    west: float | None = Query(default=None, ge=-180, le=180),
    south: float | None = Query(default=None, ge=-90, le=90),
    east: float | None = Query(default=None, ge=-180, le=180),
    north: float | None = Query(default=None, ge=-90, le=90),
):
    response.headers["Cache-Control"] = "no-store"
    if any(x is not None for x in (west, south, east, north)) and not all(
        x is not None for x in (west, south, east, north)
    ):
        return JSONResponse(status_code=422, content={"error": {"code": "incomplete_bbox"}})
    if west is not None and (west > east or south > north):
        return JSONResponse(status_code=422, content={"error": {"code": "invalid_bbox"}})
    filters = {
        "q": q,
        "province": province,
        "destination_type": destination_type,
        "bbox": [west, south, east, north] if west is not None else None,
    }
    try:
        after = verify_catalogue_cursor(settings, cursor, filters) if cursor else 0
        items, next_id = list_production_destination_page(
            settings,
            limit=limit,
            after_id=after,
            query=q,
            province=province,
            destination_type=destination_type,
            bbox=(west, south, east, north) if west is not None else None,
        )
    except ValueError:
        return JSONResponse(status_code=400, content={"error": {"code": "invalid_cursor"}})
    except CatalogueUnavailableError:
        return JSONResponse(status_code=503, content=CatalogueUnavailable().model_dump(mode="json"))
    return {
        "status": "available",
        "items": [x.model_dump(mode="json") for x in items],
        "next_cursor": sign_catalogue_cursor(settings, last_id=next_id, filters=filters)
        if next_id
        else None,
    }


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
