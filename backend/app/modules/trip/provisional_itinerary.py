"""Persistence for clearly unverified, traveler-editable AI itinerary drafts."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings


class ProvisionalItineraryNotFound(Exception):
    pass


class ProvisionalItineraryConflict(Exception):
    pass


class ProvisionalItineraryInvalid(Exception):
    pass


class ProvisionalItineraryProfileNotConfirmed(Exception):
    pass


class ProvisionalItineraryRepository:
    """Stores drafts separately from approved-catalogue recommendation itineraries."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(
            host=self.settings.database_host,
            port=self.settings.database_port,
            dbname=self.settings.database_name,
            user=self.settings.database_user,
            password=self.settings.database_password.get_secret_value(),
            connect_timeout=self.settings.database_connect_timeout_seconds,
            application_name="ai-tourism-provisional-itinerary-api",
            row_factory=dict_row,
        ) as connection:
            yield connection

    @staticmethod
    def _public(row: dict[str, Any]) -> dict[str, Any]:
        days = row["days"]
        if isinstance(days, str):
            import json

            days = json.loads(days)
        normalized_days = []
        unplanned_days = []
        for day in sorted(days, key=lambda value: value["day_number"]):
            stops = [
                {
                    **stop,
                    "verification_status": "unverified",
                    "notes_by_locale": stop.get("notes_by_locale") or {},
                }
                for stop in day["stops"]
            ]
            if not stops:
                unplanned_days.append(day["day_number"])
            normalized_days.append({"day_number": day["day_number"], "stops": stops})
        return {
            "provisional_itinerary_id": row["provisional_itinerary_id"],
            "trip_id": row["trip_id"],
            "revision": row["revision"],
            "day_count": row["day_count"],
            "locale": row["locale"],
            "title_by_locale": row["title_by_locale"] or {},
            "status": "provisional_unverified",
            "days": normalized_days,
            "unplanned_days": unplanned_days,
            "updated_at": row["updated_at"],
        }

    def get_latest(self, *, user_id: UUID, trip_id: UUID) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                """SELECT p.* FROM travel.provisional_itineraries p
                   JOIN travel.trips t ON t.trip_id=p.trip_id AND t.user_id=p.user_id
                   WHERE p.user_id=%s AND p.trip_id=%s""",
                (user_id, trip_id),
            ).fetchone()
            return self._public(row) if row else None

    def create(
        self,
        *,
        user_id: UUID,
        trip_id: UUID,
        expected_trip_version: int,
        day_count: int,
        locale: str,
        title_by_locale: dict[str, str],
        days: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], bool]:
        with self.connection() as conn, conn.transaction():
            trip = conn.execute(
                """SELECT version, duration_days, confirmed_requirements FROM travel.trips
                   WHERE trip_id=%s AND user_id=%s FOR UPDATE""",
                (trip_id, user_id),
            ).fetchone()
            if not trip:
                raise ProvisionalItineraryNotFound
            if trip["version"] != expected_trip_version:
                raise ProvisionalItineraryConflict
            if not trip["confirmed_requirements"]:
                raise ProvisionalItineraryProfileNotConfirmed
            if trip["duration_days"] is not None and day_count > trip["duration_days"]:
                raise ProvisionalItineraryInvalid
            row = conn.execute(
                """INSERT INTO travel.provisional_itineraries
                   (trip_id,user_id,day_count,locale,title_by_locale,days)
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (trip_id) DO NOTHING
                   RETURNING *""",
                (trip_id, user_id, day_count, locale, Jsonb(title_by_locale), Jsonb(days)),
            ).fetchone()
            created = row is not None
            if row is None:
                row = conn.execute(
                    """SELECT * FROM travel.provisional_itineraries
                       WHERE trip_id=%s AND user_id=%s FOR UPDATE""",
                    (trip_id, user_id),
                ).fetchone()
                if not row:
                    raise ProvisionalItineraryConflict
                existing_days = row["days"]
                if isinstance(existing_days, str):
                    import json

                    existing_days = json.loads(existing_days)
                if (
                    row["day_count"] != day_count
                    or row["locale"] != locale
                    or (row["title_by_locale"] or {}) != title_by_locale
                    or existing_days != days
                ):
                    raise ProvisionalItineraryConflict
            return self._public(row), created

    def update(
        self,
        *,
        user_id: UUID,
        itinerary_id: UUID,
        expected_revision: int,
        day_count: int,
        title_by_locale: dict[str, str],
        days: list[dict[str, Any]],
    ) -> dict[str, Any]:
        with self.connection() as conn, conn.transaction():
            row = conn.execute(
                """SELECT p.revision,t.duration_days FROM travel.provisional_itineraries p
                   JOIN travel.trips t ON t.trip_id=p.trip_id AND t.user_id=p.user_id
                   WHERE p.provisional_itinerary_id=%s AND p.user_id=%s FOR UPDATE OF p,t""",
                (itinerary_id, user_id),
            ).fetchone()
            if not row:
                raise ProvisionalItineraryNotFound
            if row["revision"] != expected_revision:
                raise ProvisionalItineraryConflict
            if row["duration_days"] is not None and day_count > row["duration_days"]:
                raise ProvisionalItineraryInvalid
            updated = conn.execute(
                """UPDATE travel.provisional_itineraries
                   SET revision=revision+1,day_count=%s,title_by_locale=%s,days=%s,updated_at=now()
                   WHERE provisional_itinerary_id=%s AND user_id=%s
                   RETURNING *""",
                (day_count, Jsonb(title_by_locale), Jsonb(days), itinerary_id, user_id),
            ).fetchone()
            return self._public(updated)
