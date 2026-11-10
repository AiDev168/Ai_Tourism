"""Durable, owner-scoped Chat reservation and completion.

The database is the concurrency boundary: a conversation row lock serializes
turns, unique idempotency keys prevent duplicate provider calls, and daily
counters are shared by all application workers. A crashed in-flight turn is
*not* retried automatically: its charge status is unknown.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.modules.trip.repository import (
    MAX_CONVERSATION_MESSAGES,
    TravelerConflict,
    TravelerInvalidState,
    TravelerNotFound,
    TravelerRepository,
)


class ChatBudgetExceeded(Exception):
    pass


@dataclass(frozen=True)
class TurnReservation:
    turn_id: UUID
    status: str
    locale: str
    user_message_id: UUID
    assistant_message_id: UUID | None = None
    created: bool = False


class AssistantTurnRepository:
    def __init__(self, traveler: TravelerRepository) -> None:
        self.traveler = traveler

    def reserve(
        self, *, user_id: UUID, conversation_id: UUID, trip_id: UUID,
        idempotency_key: str, expected_version: int, content: str,
        extracted_requirements: dict[str, Any] | None,
        per_user_limit: int, global_limit: int,
    ) -> TurnReservation:
        fingerprint = json.dumps({'content': content, 'extracted': extracted_requirements},
                                 ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(fingerprint.encode('utf-8')).digest()
        with self.traveler.connection() as conn, conn.transaction():
            row = conn.execute(
                """SELECT conversation_id,version,language_code
                   FROM conversation.conversations
                   WHERE conversation_id=%s AND user_id=%s AND conversation_status='active'
                   FOR UPDATE""", (conversation_id, user_id),
            ).fetchone()
            if row is None:
                raise TravelerNotFound
            existing = conn.execute(
                """SELECT turn_id,trip_id,content_sha256,status,user_message_id,assistant_message_id
                   FROM conversation.assistant_turns
                   WHERE conversation_id=%s AND user_id=%s AND idempotency_key=%s""",
                (conversation_id, user_id, idempotency_key),
            ).fetchone()
            if existing:
                if existing['trip_id'] != trip_id or bytes(existing['content_sha256']) != digest:
                    raise TravelerConflict
                return TurnReservation(
                    existing['turn_id'], existing['status'], row['language_code'],
                    existing['user_message_id'], existing['assistant_message_id'], False,
                )
            if row['version'] != expected_version:
                raise TravelerConflict
            trip = conn.execute(
                """SELECT trip_id FROM travel.trips
                   WHERE trip_id=%s AND conversation_id=%s AND user_id=%s FOR UPDATE""",
                (trip_id, conversation_id, user_id),
            ).fetchone()
            if trip is None:
                raise TravelerNotFound
            count = conn.execute(
                'SELECT COUNT(*) AS n FROM conversation.messages WHERE conversation_id=%s',
                (conversation_id,),
            ).fetchone()['n']
            if count + 2 > MAX_CONVERSATION_MESSAGES:
                raise TravelerInvalidState
            # Budget increments and the reservation commit together. If the
            # second limit fails, the first increment is rolled back too.
            per_user = conn.execute(
                """INSERT INTO integration.chat_daily_user_budget (user_id,budget_day,hit_count)
                   VALUES (%s,(NOW() AT TIME ZONE 'UTC')::date,1)
                   ON CONFLICT (user_id,budget_day) DO UPDATE
                   SET hit_count=integration.chat_daily_user_budget.hit_count+1
                   WHERE integration.chat_daily_user_budget.hit_count < %s
                   RETURNING hit_count""", (user_id, per_user_limit),
            ).fetchone()
            if per_user is None:
                raise ChatBudgetExceeded
            global_row = conn.execute(
                """INSERT INTO integration.chat_daily_global_budget (budget_day,hit_count)
                   VALUES ((NOW() AT TIME ZONE 'UTC')::date,1)
                   ON CONFLICT (budget_day) DO UPDATE
                   SET hit_count=integration.chat_daily_global_budget.hit_count+1
                   WHERE integration.chat_daily_global_budget.hit_count < %s
                   RETURNING hit_count""", (global_limit,),
            ).fetchone()
            if global_row is None:
                raise ChatBudgetExceeded
            message_id, turn_id = uuid4(), uuid4()
            conn.execute(
                """INSERT INTO conversation.messages
                   (message_id,conversation_id,trip_id,role,content,message_type,metadata,is_synthetic)
                   VALUES (%s,%s,%s,'user',%s,'text',%s,FALSE)""",
                (message_id, conversation_id, trip_id, content,
                 Jsonb({'source': 'internal_chat', 'consent': 'explicit'})),
            )
            conn.execute(
                """INSERT INTO conversation.assistant_turns
                   (turn_id,user_id,conversation_id,trip_id,idempotency_key,
                    content_sha256,status,user_message_id)
                   VALUES (%s,%s,%s,%s,%s,%s,'reserved',%s)""",
                (turn_id, user_id, conversation_id, trip_id, idempotency_key, digest, message_id),
            )
            # A chat turn is not a traveler-approved profile edit. Keep the
            # trip version, confirmed requirements, extracted profile and
            # version-bound recommendations/itineraries intact. The AI's
            # candidate suggestions live only on the assistant message.
            conn.execute(
                """UPDATE conversation.conversations SET version=version+1,
                   last_message_at=NOW(),updated_at=NOW() WHERE conversation_id=%s""",
                (conversation_id,),
            )
            return TurnReservation(turn_id, 'reserved', row['language_code'], message_id, None, True)

    def history(self, *, user_id: UUID, conversation_id: UUID, trip_id: UUID,
                exclude_message_id: UUID) -> list[dict[str, str]]:
        """Keep the traveler's original request in the bounded chat context.

        A long conversation must not silently forget the initial destination,
        duration, or mandatory constraints. The newest 11 turns are included
        as well, so a later explicit correction supersedes the older request.
        All queries remain owner- and trip-scoped; the currently reserved user
        message is included by ChatRequest.text and must not be duplicated.
        """
        scope = (user_id, conversation_id, trip_id, exclude_message_id)
        with self.traveler.connection() as conn:
            first = conn.execute(
                """SELECT m.message_id,m.role,m.content FROM conversation.messages m
                   JOIN conversation.conversations c USING (conversation_id)
                   WHERE c.user_id=%s AND m.conversation_id=%s AND m.trip_id=%s
                     AND m.message_id<>%s AND m.role='user'
                   ORDER BY m.created_at ASC,m.message_id ASC LIMIT 1""",
                scope,
            ).fetchone()
            if first is None:
                # No prior user statement exists. Do not invent context.
                return []
            rows = conn.execute(
                """SELECT m.message_id,m.role,m.content FROM conversation.messages m
                   JOIN conversation.conversations c USING (conversation_id)
                   WHERE c.user_id=%s AND m.conversation_id=%s AND m.trip_id=%s
                     AND m.message_id<>%s AND m.message_id<>%s
                     AND m.role IN ('user','assistant')
                   ORDER BY m.created_at DESC,m.message_id DESC LIMIT 11""",
                (*scope, first['message_id']),
            ).fetchall()
            ordered = [first, *reversed(rows)]
            return [{'role': row['role'], 'content': row['content'][:1200]}
                    for row in ordered]

    def complete(self, *, user_id: UUID, turn_id: UUID, reply: str,
                 requirements: dict[str, Any], clarification: str | None) -> None:
        with self.traveler.connection() as conn, conn.transaction():
            turn = conn.execute(
                """SELECT turn_id,conversation_id,trip_id,status FROM conversation.assistant_turns
                   WHERE turn_id=%s AND user_id=%s FOR UPDATE""", (turn_id, user_id),
            ).fetchone()
            if turn is None or turn['status'] != 'reserved':
                raise TravelerConflict
            message_id = uuid4()
            conn.execute(
                """INSERT INTO conversation.messages
                   (message_id,conversation_id,trip_id,role,content,message_type,metadata,is_synthetic)
                   VALUES (%s,%s,%s,'assistant',%s,'text',%s,FALSE)""",
                (message_id, turn['conversation_id'], turn['trip_id'], reply,
                 Jsonb({'requirements_candidate': requirements, 'clarification': clarification})),
            )
            conn.execute(
                """UPDATE conversation.assistant_turns
                   SET status='completed',assistant_message_id=%s,updated_at=NOW()
                   WHERE turn_id=%s""", (message_id, turn_id),
            )
            conn.execute(
                """UPDATE conversation.conversations SET version=version+1,
                   last_message_at=NOW(),updated_at=NOW() WHERE conversation_id=%s""",
                (turn['conversation_id'],),
            )

    def fail(self, *, user_id: UUID, turn_id: UUID) -> None:
        with self.traveler.connection() as conn, conn.transaction():
            conn.execute(
                """UPDATE conversation.assistant_turns
                   SET status='failed',updated_at=NOW()
                   WHERE turn_id=%s AND user_id=%s AND status='reserved'""",
                (turn_id, user_id),
            )

    def result(self, *, user_id: UUID, conversation_id: UUID, trip_id: UUID,
               turn_id: UUID) -> dict[str, Any] | None:
        with self.traveler.connection() as conn:
            row = conn.execute(
                """SELECT m.message_id,m.conversation_id,m.trip_id,m.role,m.content,m.created_at,
                          m.metadata FROM conversation.assistant_turns t
                   JOIN conversation.messages m ON m.message_id=t.assistant_message_id
                   WHERE t.turn_id=%s AND t.user_id=%s AND t.conversation_id=%s
                     AND t.trip_id=%s AND t.status='completed'""",
                (turn_id, user_id, conversation_id, trip_id),
            ).fetchone()
            return dict(row) if row else None
