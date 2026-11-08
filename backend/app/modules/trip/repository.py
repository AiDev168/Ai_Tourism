"""PostgreSQL persistence for authenticated traveler conversations and trips."""

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.modules.trip.budget import InvalidBudgetAmount, convert_budget_to_irr

MAX_CONVERSATION_MESSAGES = 500


class TravelerNotFound(Exception):
    pass


class TravelerConflict(Exception):
    pass


class TravelerInvalidState(Exception):
    pass


def _field_value(requirements: Mapping[str, Any], key: str) -> Any:
    field = requirements.get(key)
    return field.get("value") if isinstance(field, Mapping) else None


def _profile_columns(requirements: Mapping[str, Any]) -> dict[str, Any]:
    origin = _field_value(requirements, "origin")
    duration = _field_value(requirements, "durationDays")
    travelers = _field_value(requirements, "travelerCount")
    dates = _field_value(requirements, "travelDates")
    start_date = dates.get("start") if isinstance(dates, Mapping) else None
    end_date = dates.get("end") if isinstance(dates, Mapping) else None
    budget = _field_value(requirements, "budget")
    amount: Decimal | None = None
    currency: str | None = None
    unit: str | None = None
    raw: str | None = None
    if isinstance(budget, Mapping):
        try:
            amount = Decimal(str(budget.get("amount")))
        except (InvalidOperation, TypeError):
            amount = None
        raw_currency = budget.get("currency")
        raw_unit = str(budget.get("unit") or "").casefold()
        if raw_currency == "IRR" and amount is not None and amount.is_finite() and amount >= 0:
            if "toman" in raw_unit or "تومان" in raw_unit:
                currency, unit = "IRR", "toman"
            elif "rial" in raw_unit or "ریال" in raw_unit or raw_unit.strip() == "irr":
                currency, unit = "IRR", "rial"
            try:
                if currency and unit:
                    convert_budget_to_irr(amount, unit)
                else:
                    raise InvalidBudgetAmount
            except InvalidBudgetAmount:
                currency = unit = None
            if currency:
                raw = str(budget.get("raw") or "")[:240]
            else:
                amount = None
    return {
        "origin": origin if isinstance(origin, str) and origin.strip() else None,
        "duration": duration if isinstance(duration, int) and 1 <= duration <= 365 else None,
        "travelers": travelers if isinstance(travelers, int) and 1 <= travelers <= 50 else None,
        "start_date": start_date,
        "end_date": end_date,
        "budget_amount": amount,
        "budget_currency": currency,
        "budget_unit": unit,
        "budget_raw": raw,
    }


def _destination_ids(requirements: Mapping[str, Any]) -> list[str]:
    values = requirements.get("destination_ids", [])
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and value.isdigit()][:50]


def _merge_extraction(previous: Any, latest: dict[str, Any]) -> dict[str, Any]:
    """Keep previously captured known values when a clarification parse omits them."""
    if not isinstance(previous, Mapping):
        return latest
    merged = dict(previous)
    for key, new_value in latest.items():
        old_value = merged.get(key)
        if isinstance(old_value, Mapping) and isinstance(new_value, Mapping) and "value" in new_value:
            if new_value.get("value") is None and old_value.get("value") is not None:
                merged[key] = dict(old_value)
            else:
                merged[key] = dict(new_value)
        else:
            merged[key] = new_value
    return merged


class TravelerRepository:
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
            application_name="ai-tourism-traveler-api",
            row_factory=dict_row,
        ) as connection:
            yield connection

    def create_conversation(
        self,
        *,
        user_id: UUID,
        locale: str,
        request_text: str,
        extracted_requirements: dict[str, Any],
        confirmed_requirements: dict[str, Any],
        destination_ids: list[str],
        idempotency_key: str,
    ) -> tuple[UUID, UUID, UUID, bool]:
        # Parser/resolver results are not traveler-confirmed until the explicit
        # profile-confirmation operation. Ignore client-supplied initial values.
        initial_confirmed: dict[str, Any] = {}
        profile = _profile_columns(extracted_requirements)
        with self.connection() as conn, conn.transaction():
            prior = conn.execute(
                """SELECT conversation_id,language_code FROM conversation.conversations
                   WHERE user_id=%s AND create_idempotency_key=%s""",
                (user_id, idempotency_key),
            ).fetchone()
            if prior:
                trip = conn.execute(
                    """SELECT trip_id FROM travel.trips
                       WHERE conversation_id=%s AND user_id=%s ORDER BY created_at, trip_id LIMIT 1""",
                    (prior["conversation_id"], user_id),
                ).fetchone()
                if not trip:
                    raise TravelerConflict
                msg = conn.execute(
                    """SELECT message_id,content,metadata FROM conversation.messages
                       WHERE conversation_id=%s AND trip_id=%s AND role='user'
                       ORDER BY created_at, message_id LIMIT 1""",
                    (prior["conversation_id"], trip["trip_id"]),
                ).fetchone()
                if not msg:
                    raise TravelerConflict
                stored_payload = msg["metadata"] or {}
                if (
                    prior["language_code"] != locale
                    or msg["content"] != request_text
                    or stored_payload.get("extracted_requirements") != extracted_requirements
                    or stored_payload.get("confirmed_requirements") != initial_confirmed
                ):
                    raise TravelerConflict
                return prior["conversation_id"], trip["trip_id"], msg["message_id"], False

            conversation_id, trip_id, message_id = uuid4(), uuid4(), uuid4()
            conn.execute(
                """INSERT INTO conversation.conversations
                   (conversation_id,user_id,channel,language_code,conversation_status,
                    structured_context,is_synthetic,create_idempotency_key)
                   VALUES (%s,%s,'pwa',%s,'active',%s,FALSE,%s)""",
                (conversation_id, user_id, locale, Jsonb({}), idempotency_key),
            )
            conn.execute(
                """INSERT INTO travel.trips
                   (trip_id,user_id,conversation_id,create_idempotency_key,origin_text,start_date,end_date,duration_days,
                    budget_amount_original,budget_currency_iso,budget_unit,budget_raw_text,
                    traveler_count,extracted_requirements,confirmed_requirements,is_synthetic)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE)""",
                (
                    trip_id, user_id, conversation_id, idempotency_key, profile["origin"], profile["start_date"],
                    profile["end_date"], profile["duration"], profile["budget_amount"],
                    profile["budget_currency"], profile["budget_unit"], profile["budget_raw"],
                    profile["travelers"], Jsonb(extracted_requirements), Jsonb(initial_confirmed),
                ),
            )
            conn.execute(
                """INSERT INTO conversation.messages
                   (message_id,conversation_id,trip_id,role,content,message_type,metadata,is_synthetic)
                   VALUES (%s,%s,%s,'user',%s,'text',%s,FALSE)""",
                (
                    message_id, conversation_id, trip_id, request_text,
                    Jsonb({
                        "locale": locale,
                        "extracted_requirements": extracted_requirements,
                        "confirmed_requirements": initial_confirmed,
                    }),
                ),
            )
            conn.execute(
                """UPDATE conversation.conversations SET last_message_at=NOW(), updated_at=NOW()
                   WHERE conversation_id=%s""",
                (conversation_id,),
            )
            return conversation_id, trip_id, message_id, True

    def create_trip_in_conversation(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        locale: str,
        request_text: str,
        extracted_requirements: dict[str, Any],
        confirmed_requirements: dict[str, Any],
        destination_ids: list[str],
        idempotency_key: str,
    ) -> tuple[UUID, UUID, UUID, bool]:
        # A new draft remains unconfirmed even if a client submits parsed IDs
        # or fields here. Confirmation is recorded only by confirm_trip_profile.
        initial_confirmed: dict[str, Any] = {}
        profile = _profile_columns(extracted_requirements)
        with self.connection() as conn, conn.transaction():
            conversation = conn.execute(
                """SELECT conversation_id,language_code FROM conversation.conversations
                   WHERE conversation_id=%s AND user_id=%s AND conversation_status='active' FOR UPDATE""",
                (conversation_id, user_id),
            ).fetchone()
            if not conversation:
                raise TravelerNotFound
            existing = conn.execute(
                """SELECT trip_id FROM travel.trips
                   WHERE user_id=%s AND create_idempotency_key=%s""",
                (user_id, idempotency_key),
            ).fetchone()
            if existing:
                message = conn.execute(
                    """SELECT m.message_id,m.content,m.metadata,t.conversation_id
                       FROM conversation.messages m JOIN travel.trips t USING(trip_id)
                       WHERE m.trip_id=%s AND m.role='user' ORDER BY m.created_at,m.message_id LIMIT 1""",
                    (existing["trip_id"],),
                ).fetchone()
                metadata = (message["metadata"] or {}) if message else {}
                if (
                    message is None
                    or message["conversation_id"] != conversation_id
                    or conversation["language_code"] != locale
                    or message["content"] != request_text
                    or metadata.get("extracted_requirements") != extracted_requirements
                    or metadata.get("confirmed_requirements") != initial_confirmed
                ):
                    raise TravelerConflict
                return conversation_id, existing["trip_id"], message["message_id"], False
            trip_id, message_id = uuid4(), uuid4()
            conn.execute(
                """INSERT INTO travel.trips
                   (trip_id,user_id,conversation_id,create_idempotency_key,origin_text,start_date,
                    end_date,duration_days,budget_amount_original,budget_currency_iso,budget_unit,
                    budget_raw_text,traveler_count,extracted_requirements,confirmed_requirements,is_synthetic)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE)""",
                (
                    trip_id, user_id, conversation_id, idempotency_key, profile["origin"],
                    profile["start_date"], profile["end_date"], profile["duration"],
                    profile["budget_amount"], profile["budget_currency"], profile["budget_unit"],
                    profile["budget_raw"], profile["travelers"], Jsonb(extracted_requirements),
                    Jsonb(initial_confirmed),
                ),
            )
            conn.execute(
                """INSERT INTO conversation.messages
                   (message_id,conversation_id,trip_id,role,content,message_type,metadata,is_synthetic)
                   VALUES (%s,%s,%s,'user',%s,'text',%s,FALSE)""",
                (
                    message_id, conversation_id, trip_id, request_text,
                    Jsonb({"locale": locale, "extracted_requirements": extracted_requirements,
                           "confirmed_requirements": initial_confirmed}),
                ),
            )
            conn.execute(
                "UPDATE conversation.conversations SET version=version+1,updated_at=NOW(),last_message_at=NOW() WHERE conversation_id=%s",
                (conversation_id,),
            )
            return conversation_id, trip_id, message_id, True

    def append_message(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        trip_id: UUID,
        content: str,
        extracted_requirements: dict[str, Any] | None,
        idempotency_key: str,
        expected_version: int,
        replace_previous_request: bool,
    ) -> tuple[UUID, bool]:
        with self.connection() as conn, conn.transaction():
            conversation = conn.execute(
                """SELECT conversation_id,version FROM conversation.conversations
                   WHERE conversation_id=%s AND user_id=%s FOR UPDATE""",
                (conversation_id, user_id),
            ).fetchone()
            if not conversation:
                raise TravelerNotFound
            existing = conn.execute(
                """SELECT message_id,trip_id,content,metadata FROM conversation.messages
                   WHERE conversation_id=%s AND idempotency_key=%s""",
                (conversation_id, idempotency_key),
            ).fetchone()
            if existing:
                stored_payload = existing["metadata"] or {}
                if (
                    existing["trip_id"] != trip_id
                    or existing["content"] != content
                    or stored_payload.get("extracted_requirements") != extracted_requirements
                    or stored_payload.get("replace_previous_request", False) != replace_previous_request
                ):
                    raise TravelerConflict
                return existing["message_id"], False
            if conversation["version"] != expected_version:
                raise TravelerConflict
            trip = conn.execute(
                """SELECT trip_id FROM travel.trips WHERE trip_id=%s AND conversation_id=%s
                   AND user_id=%s FOR UPDATE""",
                (trip_id, conversation_id, user_id),
            ).fetchone()
            if not trip:
                raise TravelerNotFound
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM conversation.messages WHERE conversation_id=%s",
                (conversation_id,),
            ).fetchone()["n"]
            if count >= MAX_CONVERSATION_MESSAGES:
                raise TravelerInvalidState
            message_id = uuid4()
            conn.execute(
                """INSERT INTO conversation.messages
                   (message_id,conversation_id,trip_id,role,content,message_type,metadata,
                    idempotency_key,is_synthetic)
                   VALUES (%s,%s,%s,'user',%s,'text',%s,%s,FALSE)""",
                (
                    message_id, conversation_id, trip_id, content,
                    Jsonb({"extracted_requirements": extracted_requirements,
                           "replace_previous_request": replace_previous_request}), idempotency_key,
                ),
            )
            profile = None
            if extracted_requirements is not None:
                previous_requirements = conn.execute(
                    "SELECT extracted_requirements FROM travel.trips WHERE trip_id=%s",
                    (trip_id,),
                ).fetchone()["extracted_requirements"] or {}
                merged = (
                    extracted_requirements
                    if replace_previous_request
                    else _merge_extraction(previous_requirements, extracted_requirements)
                )
                conn.execute(
                    """UPDATE travel.trips SET extracted_requirements=%s,
                       confirmed_requirements='{}'::jsonb
                       WHERE trip_id=%s AND user_id=%s""",
                    (Jsonb(merged), trip_id, user_id),
                )
                profile = _profile_columns(merged)
            # Any new turn invalidates the reviewed profile and prior version-bound runs.
            if profile is not None:
                conn.execute(
                    """UPDATE travel.trips SET confirmed_requirements='{}'::jsonb,
                       origin_text=%s,start_date=%s,end_date=%s,duration_days=%s,
                       traveler_count=%s,budget_amount_original=%s,budget_currency_iso=%s,
                       budget_unit=%s,budget_raw_text=%s,version=version+1,updated_at=NOW()
                       WHERE trip_id=%s AND user_id=%s""",
                    (
                        profile["origin"], profile["start_date"], profile["end_date"],
                        profile["duration"], profile["travelers"], profile["budget_amount"],
                        profile["budget_currency"], profile["budget_unit"], profile["budget_raw"],
                        trip_id, user_id,
                    ),
                )
            else:
                conn.execute(
                    """UPDATE travel.trips SET confirmed_requirements='{}'::jsonb,
                       version=version+1,updated_at=NOW() WHERE trip_id=%s AND user_id=%s""",
                    (trip_id, user_id),
                )
            conn.execute(
                """UPDATE conversation.conversations SET last_message_at=NOW(),
                   updated_at=NOW(),version=version+1 WHERE conversation_id=%s""",
                (conversation_id,),
            )
            return message_id, True

    def confirm_trip_profile(
        self,
        *,
        user_id: UUID,
        trip_id: UUID,
        expected_version: int,
        confirmed_requirements: dict[str, Any],
        destination_ids: list[str],
    ) -> None:
        requirements = dict(confirmed_requirements)
        requirements["destination_ids"] = destination_ids
        profile = _profile_columns(requirements)
        with self.connection() as conn, conn.transaction():
            row = conn.execute(
                "SELECT version FROM travel.trips WHERE trip_id=%s AND user_id=%s FOR UPDATE",
                (trip_id, user_id),
            ).fetchone()
            if not row:
                raise TravelerNotFound
            if row["version"] != expected_version:
                raise TravelerConflict
            conn.execute(
                """UPDATE travel.trips SET confirmed_requirements=%s,
                   origin_text=%s,start_date=%s,end_date=%s,duration_days=%s,
                   traveler_count=%s,budget_amount_original=%s,budget_currency_iso=%s,
                   budget_unit=%s,budget_raw_text=%s,version=version+1,updated_at=NOW()
                   WHERE trip_id=%s AND user_id=%s""",
                (
                    Jsonb(requirements), profile["origin"], profile["start_date"],
                    profile["end_date"], profile["duration"], profile["travelers"],
                    profile["budget_amount"], profile["budget_currency"], profile["budget_unit"],
                    profile["budget_raw"], trip_id, user_id,
                ),
            )

    def conversation(self, user_id: UUID, conversation_id: UUID) -> dict[str, Any] | None:
        with self.connection() as conn:
            return self._conversation(conn, user_id, conversation_id)

    def _conversation(
        self, conn: psycopg.Connection[Any], user_id: UUID, conversation_id: UUID
    ) -> dict[str, Any] | None:
        row = conn.execute(
            """SELECT conversation_id,language_code,version,started_at,updated_at,last_message_at
               FROM conversation.conversations WHERE conversation_id=%s AND user_id=%s""",
            (conversation_id, user_id),
        ).fetchone()
        if not row:
            return None
        trips = conn.execute(
            """SELECT t.*, c.language_code FROM travel.trips t
               JOIN conversation.conversations c USING (conversation_id)
               WHERE t.conversation_id=%s AND t.user_id=%s ORDER BY t.created_at,t.trip_id""",
            (conversation_id, user_id),
        ).fetchall()
        trip_values = [self._trip_response(conn, trip) for trip in trips]
        messages = conn.execute(
            """SELECT message_id,conversation_id,trip_id,role,content,created_at
               FROM conversation.messages WHERE conversation_id=%s
               ORDER BY created_at,message_id LIMIT %s""",
            (conversation_id, MAX_CONVERSATION_MESSAGES),
        ).fetchall()
        return {
            "conversation_id": row["conversation_id"],
            "locale": self._locale(row["language_code"]),
            "version": row["version"],
            "started_at": row["started_at"],
            "updated_at": row["updated_at"],
            "last_message_at": row["last_message_at"],
            "trips": trip_values,
            "messages": messages,
        }

    def list_conversations(
        self, user_id: UUID, limit: int, cursor: UUID | None
    ) -> tuple[list[dict[str, Any]], UUID | None]:
        with self.connection() as conn:
            if cursor:
                cursor_row = conn.execute(
                    """SELECT started_at FROM conversation.conversations
                       WHERE conversation_id=%s AND user_id=%s""",
                    (cursor, user_id),
                ).fetchone()
                if not cursor_row:
                    raise TravelerNotFound
                rows = conn.execute(
                    """SELECT conversation_id,language_code,version,started_at,updated_at,last_message_at
                       FROM conversation.conversations WHERE user_id=%s
                         AND (started_at,conversation_id)<(%s,%s)
                       ORDER BY started_at DESC,conversation_id DESC LIMIT %s""",
                    (user_id, cursor_row["started_at"], cursor, limit + 1),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT conversation_id,language_code,version,started_at,updated_at,last_message_at
                       FROM conversation.conversations WHERE user_id=%s
                       ORDER BY started_at DESC,conversation_id DESC LIMIT %s""",
                    (user_id, limit + 1),
                ).fetchall()
            has_more = len(rows) > limit
            rows = rows[:limit]
            items = []
            for row in rows:
                trips = conn.execute(
                    """SELECT t.*,c.language_code FROM travel.trips t
                       JOIN conversation.conversations c USING(conversation_id)
                       WHERE t.conversation_id=%s AND t.user_id=%s
                       ORDER BY t.created_at,t.trip_id""",
                    (row["conversation_id"], user_id),
                ).fetchall()
                items.append({
                    "conversation_id": row["conversation_id"],
                    "locale": self._locale(row["language_code"]),
                    "version": row["version"],
                    "started_at": row["started_at"],
                    "updated_at": row["updated_at"],
                    "last_message_at": row["last_message_at"],
                    "trips": [self._trip_response(conn, trip) for trip in trips],
                })
            next_cursor = rows[-1]["conversation_id"] if has_more and rows else None
            return items, next_cursor

    def trip(self, user_id: UUID, trip_id: UUID) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                """SELECT t.*,c.language_code FROM travel.trips t
                   LEFT JOIN conversation.conversations c USING(conversation_id)
                   WHERE t.trip_id=%s AND t.user_id=%s""",
                (trip_id, user_id),
            ).fetchone()
            return self._trip_response(conn, row) if row else None

    def _trip_response(self, conn: psycopg.Connection[Any], row: Mapping[str, Any]) -> dict[str, Any]:
        original = conn.execute(
            """SELECT content FROM conversation.messages WHERE trip_id=%s AND role='user'
               ORDER BY created_at,message_id LIMIT 1""",
            (row["trip_id"],),
        ).fetchone()
        extracted = row.get("extracted_requirements") or {}
        confirmed = row.get("confirmed_requirements") or {}
        latest_request = conn.execute(
            """SELECT recommendation_request_id,input_snapshot FROM recommendation.recommendation_requests
               WHERE trip_id=%s AND request_status='completed'
               ORDER BY created_at DESC,recommendation_request_id DESC LIMIT 1""",
            (row["trip_id"],),
        ).fetchone()
        latest_request_id = None
        if latest_request and (latest_request["input_snapshot"] or {}).get("trip_version") == row["version"]:
            latest_request_id = latest_request["recommendation_request_id"]
        latest_itinerary = None
        if latest_request_id:
            latest_itinerary_row = conn.execute(
                """SELECT itinerary_id FROM travel.itineraries WHERE trip_id=%s
                   AND recommendation_request_id=%s ORDER BY created_at DESC,version DESC LIMIT 1""",
                (row["trip_id"], latest_request_id),
            ).fetchone()
            latest_itinerary = latest_itinerary_row["itinerary_id"] if latest_itinerary_row else None
        return {
            "trip_id": row["trip_id"],
            "conversation_id": row["conversation_id"],
            "version": row["version"],
            "locale": self._locale(row.get("language_code")),
            "original_request": original["content"] if original else "",
            "extracted_requirements": extracted,
            "confirmed_requirements": confirmed,
            "destination_ids": _destination_ids(confirmed),
            "duration_days": row["duration_days"],
            "traveler_count": row["traveler_count"],
            "budget_amount_original": str(row["budget_amount_original"]) if row["budget_amount_original"] is not None else None,
            "budget_currency_iso": row["budget_currency_iso"].strip() if row["budget_currency_iso"] else None,
            "budget_unit": row["budget_unit"],
            "latest_recommendation_request_id": latest_request_id,
            "latest_itinerary_id": latest_itinerary,
            "trip_status": row["trip_status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _locale(value: Any) -> str:
        return value if value in {"fa-IR", "en-US", "ar"} else "fa-IR"

    def delete_trip(self, user_id: UUID, trip_id: UUID) -> UUID | None:
        with self.connection() as conn, conn.transaction():
            row = conn.execute(
                "DELETE FROM travel.trips WHERE trip_id=%s AND user_id=%s RETURNING conversation_id",
                (trip_id, user_id),
            ).fetchone()
            if not row:
                return None
            conversation_id = row["conversation_id"]
            if conversation_id:
                remaining = conn.execute(
                    "SELECT 1 FROM travel.trips WHERE conversation_id=%s AND user_id=%s LIMIT 1",
                    (conversation_id, user_id),
                ).fetchone()
                if not remaining:
                    conn.execute(
                        "DELETE FROM conversation.conversations WHERE conversation_id=%s AND user_id=%s",
                        (conversation_id, user_id),
                    )
            return conversation_id

    def delete_conversation(self, user_id: UUID, conversation_id: UUID) -> bool:
        with self.connection() as conn, conn.transaction():
            row = conn.execute(
                "DELETE FROM conversation.conversations WHERE conversation_id=%s AND user_id=%s RETURNING conversation_id",
                (conversation_id, user_id),
            ).fetchone()
            return row is not None

    def delete_account_data(self, user_id: UUID) -> bool:
        """Delete text-bearing feedback then cascade all owner-linked product data."""
        with self.connection() as conn, conn.transaction():
            exists = conn.execute(
                "SELECT 1 FROM identity.users WHERE user_id=%s AND account_status='active' AND is_synthetic=FALSE FOR UPDATE",
                (user_id,),
            ).fetchone()
            if not exists:
                return False
            conn.execute(
                """DELETE FROM operations.feedback WHERE user_id=%s
                   OR conversation_id IN (SELECT conversation_id FROM conversation.conversations WHERE user_id=%s)
                   OR trip_id IN (SELECT trip_id FROM travel.trips WHERE user_id=%s)""",
                (user_id, user_id, user_id),
            )
            conn.execute("DELETE FROM identity.users WHERE user_id=%s", (user_id,))
            return True

    def create_recommendation_run(
        self,
        *,
        user_id: UUID,
        trip_id: UUID,
        expected_trip_version: int,
        outcome: Any,
        selected_destination_ids: list[str],
    ) -> tuple[UUID, int]:
        with self.connection() as conn, conn.transaction():
            trip = conn.execute(
                """SELECT trip_id,conversation_id,version,confirmed_requirements FROM travel.trips
                   WHERE trip_id=%s AND user_id=%s FOR UPDATE""",
                (trip_id, user_id),
            ).fetchone()
            if not trip:
                raise TravelerNotFound
            if trip["version"] != expected_trip_version:
                raise TravelerConflict
            snapshot = {
                "trip_version": trip["version"],
                "confirmed_requirements": trip["confirmed_requirements"] or {},
                "selected_destination_ids": selected_destination_ids,
                "outcome_status": outcome.status,
                "reason_code": outcome.reason_code,
                "algorithm_version": outcome.algorithm_version,
                "retrieval_version": outcome.retrieval_version,
            }
            request_id = uuid4()
            conn.execute(
                """INSERT INTO recommendation.recommendation_requests
                   (recommendation_request_id,trip_id,conversation_id,algorithm_version,
                    retrieval_version,input_snapshot,request_status,is_synthetic,completed_at)
                   VALUES (%s,%s,%s,%s,%s,%s,'completed',FALSE,NOW())""",
                (
                    request_id,
                    trip_id,
                    trip["conversation_id"],
                    outcome.algorithm_version,
                    outcome.retrieval_version,
                    Jsonb(snapshot),
                ),
            )
            for item in outcome.items:
                rec_id = uuid4()
                evidence = [source.model_dump(mode="json") for source in item.evidence]
                explanation = _EXPLANATIONS.get(item.explanation_key, _EXPLANATIONS["explicit_destination_match"])
                conn.execute(
                    """INSERT INTO recommendation.recommendations
                       (recommendation_id,recommendation_request_id,destination_id,rank,final_score,
                        confidence,explanation_fa,warnings,is_synthetic,evidence,explanation_by_locale)
                       VALUES (%s,%s,%s,%s,%s,NULL,%s,%s,FALSE,%s,%s)""",
                    (
                        rec_id, request_id, int(item.destination_id), item.rank, item.final_score,
                        explanation["fa-IR"], Jsonb(item.warnings), Jsonb(evidence), Jsonb(explanation),
                    ),
                )
                for component in item.score_components:
                    conn.execute(
                        """INSERT INTO recommendation.recommendation_score_components
                           (recommendation_id,component_key,raw_score,normalized_score,weight,
                            weighted_score,component_reason,is_synthetic)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,FALSE)""",
                        (
                            rec_id,
                            component.component_key,
                            component.raw_score,
                            component.raw_score,
                            component.weight,
                            component.weighted_score,
                            json.dumps(component.matched_terms, ensure_ascii=False, separators=(",", ":")),
                        ),
                    )
            return request_id, trip["version"]

    def recommendation_context(
        self, user_id: UUID, trip_id: UUID, request_id: UUID
    ) -> dict[str, Any] | None:
        with self.connection() as conn:
            request = conn.execute(
                """SELECT r.recommendation_request_id,r.trip_id,r.algorithm_version,r.input_snapshot,
                          r.request_status,t.conversation_id,t.version AS current_trip_version,
                          t.confirmed_requirements,t.user_id
                   FROM recommendation.recommendation_requests r
                   JOIN travel.trips t USING(trip_id)
                   WHERE r.recommendation_request_id=%s AND r.trip_id=%s AND t.user_id=%s""",
                (request_id, trip_id, user_id),
            ).fetchone()
            if not request or request["request_status"] != "completed":
                return None
            if (request["input_snapshot"] or {}).get("trip_version") != request["current_trip_version"]:
                return None
            rows = conn.execute(
                """SELECT recommendation_id,destination_id,rank,final_score,explanation_fa,
                          explanation_by_locale,warnings,evidence FROM recommendation.recommendations
                   WHERE recommendation_request_id=%s ORDER BY rank""",
                (request_id,),
            ).fetchall()
            score_rows = conn.execute(
                """SELECT c.recommendation_id,c.component_key,c.raw_score,c.weight,c.weighted_score,
                          c.component_reason
                   FROM recommendation.recommendation_score_components c
                   JOIN recommendation.recommendations r USING(recommendation_id)
                   WHERE r.recommendation_request_id=%s AND c.is_synthetic=FALSE
                   ORDER BY r.rank,c.component_key""",
                (request_id,),
            ).fetchall()
            scores_by_recommendation: dict[UUID, list[dict[str, Any]]] = {}
            for score in score_rows:
                try:
                    matched_terms = json.loads(score["component_reason"] or "[]")
                except (TypeError, ValueError):
                    matched_terms = []
                if not isinstance(matched_terms, list) or any(not isinstance(term, str) for term in matched_terms):
                    matched_terms = []
                scores_by_recommendation.setdefault(score["recommendation_id"], []).append({
                    "component_key": score["component_key"],
                    "raw_score": float(score["raw_score"] or 0),
                    "weight": float(score["weight"] or 0),
                    "weighted_score": float(score["weighted_score"] or 0),
                    "matched_terms": matched_terms,
                })
            rows = [
                {**row, "score_components": scores_by_recommendation.get(row["recommendation_id"], [])}
                for row in rows
            ]
            return {**request, "items": rows}

    def create_itinerary(
        self,
        *,
        user_id: UUID,
        trip_id: UUID,
        recommendation_request_id: UUID,
        day_count: int,
        title_by_locale: dict[str, str],
        stops: list[dict[str, Any]],
    ) -> UUID:
        with self.connection() as conn, conn.transaction():
            trip = conn.execute(
                "SELECT trip_id,version FROM travel.trips WHERE trip_id=%s AND user_id=%s FOR UPDATE",
                (trip_id, user_id),
            ).fetchone()
            request = conn.execute(
                """SELECT recommendation_request_id,input_snapshot FROM recommendation.recommendation_requests
                   WHERE recommendation_request_id=%s AND trip_id=%s AND request_status='completed'""",
                (recommendation_request_id, trip_id),
            ).fetchone()
            if not trip or not request:
                raise TravelerNotFound
            if (request["input_snapshot"] or {}).get("trip_version") != trip["version"]:
                raise TravelerConflict
            if not stops:
                raise TravelerInvalidState
            recommendation_ids = [stop["recommendation_id"] for stop in stops]
            valid_ids = conn.execute(
                """SELECT recommendation_id FROM recommendation.recommendations
                   WHERE recommendation_request_id=%s AND recommendation_id=ANY(%s)""",
                (recommendation_request_id, recommendation_ids),
            ).fetchall()
            if len(valid_ids) != len(recommendation_ids):
                raise TravelerInvalidState
            itinerary_id = uuid4()
            version = conn.execute(
                "SELECT COALESCE(MAX(version),0)+1 AS v FROM travel.itineraries WHERE trip_id=%s",
                (trip_id,),
            ).fetchone()["v"]
            conn.execute(
                """INSERT INTO travel.itineraries
                   (itinerary_id,trip_id,recommendation_request_id,version,revision,title,day_count,
                    title_by_locale,itinerary_status,is_synthetic)
                   VALUES (%s,%s,%s,%s,1,%s,%s,%s,'draft',FALSE)""",
                (
                    itinerary_id, trip_id, recommendation_request_id, version,
                    next(iter(title_by_locale.values()), "Trip plan"), day_count, Jsonb(title_by_locale),
                ),
            )
            self._insert_stops(conn, itinerary_id, stops)
            return itinerary_id

    @staticmethod
    def _insert_stops(
        conn: psycopg.Connection[Any], itinerary_id: UUID, stops: list[dict[str, Any]]
    ) -> None:
        for stop in stops:
            conn.execute(
                """INSERT INTO travel.itinerary_stops
                   (itinerary_stop_id,itinerary_id,destination_id,recommendation_id,day_number,
                    stop_order,planned_start_time,duration_minutes,travel_to_next_estimate_minutes,
                    notes_fa,notes_by_locale,is_synthetic)
                   VALUES (%s,%s,%s,%s,%s,%s,NULL,NULL,NULL,NULL,%s,FALSE)""",
                (
                    uuid4(), itinerary_id, int(stop["destination_id"]), stop["recommendation_id"],
                    stop["day_number"], stop["stop_order"], Jsonb(stop.get("notes_by_locale", {})),
                ),
            )

    def itinerary(self, user_id: UUID, itinerary_id: UUID) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                """SELECT i.itinerary_id,i.trip_id,i.recommendation_request_id,i.version,i.revision,
                          i.day_count,i.title_by_locale,i.updated_at,t.user_id
                   FROM travel.itineraries i JOIN travel.trips t USING(trip_id)
                   WHERE i.itinerary_id=%s AND t.user_id=%s""",
                (itinerary_id, user_id),
            ).fetchone()
            if not row:
                return None
            stops = conn.execute(
                """SELECT s.itinerary_stop_id,s.recommendation_id,s.destination_id,s.day_number,
                          s.stop_order,s.notes_by_locale
                   FROM travel.itinerary_stops s WHERE s.itinerary_id=%s
                   ORDER BY s.day_number,s.stop_order""",
                (itinerary_id,),
            ).fetchall()
            return {**row, "stops": stops}

    def update_itinerary(
        self,
        *,
        user_id: UUID,
        itinerary_id: UUID,
        expected_revision: int,
        title_by_locale: dict[str, str],
        stops: list[dict[str, Any]],
    ) -> None:
        with self.connection() as conn, conn.transaction():
            row = conn.execute(
                """SELECT i.trip_id,i.revision,i.day_count,t.user_id
                   FROM travel.itineraries i JOIN travel.trips t USING(trip_id)
                   WHERE i.itinerary_id=%s AND t.user_id=%s FOR UPDATE OF i,t""",
                (itinerary_id, user_id),
            ).fetchone()
            if not row:
                raise TravelerNotFound
            if row["revision"] != expected_revision:
                raise TravelerConflict
            if any(stop["day_number"] > row["day_count"] for stop in stops):
                raise TravelerInvalidState
            ids = [stop["recommendation_id"] for stop in stops]
            if len(set(ids)) != len(ids):
                raise TravelerInvalidState
            valid = conn.execute(
                """SELECT r.recommendation_id,r.destination_id FROM recommendation.recommendations r
                   JOIN recommendation.recommendation_requests q USING(recommendation_request_id)
                   WHERE q.trip_id=%s AND r.recommendation_id=ANY(%s)""",
                (row["trip_id"], ids),
            ).fetchall() if ids else []
            by_id = {str(item["recommendation_id"]): item for item in valid}
            if len(by_id) != len(ids):
                raise TravelerInvalidState
            for stop in stops:
                stop["destination_id"] = str(by_id[str(stop["recommendation_id"])]["destination_id"])
            conn.execute(
                """UPDATE travel.itineraries SET title_by_locale=%s,title=%s,revision=revision+1,
                   itinerary_status='edited',updated_at=NOW() WHERE itinerary_id=%s AND revision=%s""",
                (Jsonb(title_by_locale), next(iter(title_by_locale.values()), "Trip plan"), itinerary_id, expected_revision),
            )
            conn.execute("DELETE FROM travel.itinerary_stops WHERE itinerary_id=%s", (itinerary_id,))
            self._insert_stops(conn, itinerary_id, stops)


_EXPLANATIONS: dict[str, dict[str, str]] = {
    "explicit_destination_match": {
        "fa-IR": "مقصدی که انتخاب کرده‌اید با نام و منبع تأییدشده در فهرست منتشرشده تطبیق دارد؛ این مورد رتبه‌بندی کیفی یا تأیید ساعات، قیمت، دسترسی و شرایط بازدید نیست.",
        "en-US": "The destination you selected matches a published name with approved source evidence. This is an identity match, not a quality ranking or confirmation of hours, price, access, or visit conditions.",
        "ar": "يطابق الوجهة التي اخترتها اسماً منشوراً وله مصدر معتمد. هذا تطابق للهوية وليس ترتيباً للجودة أو تأكيداً للمواعيد أو الأسعار أو الوصول أو ظروف الزيارة.",
    },
    "published_area_candidate": {
        "fa-IR": "این مکانِ منتشرشده در همان شهرِ مقصد انتخاب‌شده قرار دارد و منبع تأییدشده دارد. این تطبیق ساختاری است و تأیید کیفیت، ساعت بازدید، قیمت، دسترسی یا شرایط بازدید نیست.",
        "en-US": "This published place is in the same city as your selected destination and has approved source evidence. This is a structured match, not confirmation of quality, hours, price, access, or visit conditions.",
        "ar": "يقع هذا المكان المنشور في المدينة نفسها للوجهة التي اخترتها، وله مصدر معتمد. هذا تطابق مبني على بيانات منظمة، وليس تأكيداً للجودة أو ساعات الزيارة أو الأسعار أو سهولة الوصول أو ظروف الزيارة.",
    },
}


def localized_recommendation_explanation(explanation_key: str) -> dict[str, str]:
    """Return the reviewed localized explanation for a stable domain key."""
    return dict(_EXPLANATIONS.get(explanation_key, _EXPLANATIONS["explicit_destination_match"]))
