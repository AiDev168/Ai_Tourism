"""Real assistant-turn persistence checks, guarded to a disposable PostgreSQL 17 DB.

Never enable these tests against the owner's shared database. Both integration
opt-ins and the existing disposable DB identity/marker guard are required.
No provider or SMS requests are made.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.trip.assistant_turns import AssistantTurnRepository, ChatBudgetExceeded
from app.modules.trip.repository import TravelerConflict, TravelerNotFound, TravelerRepository
from test_auth_postgres import connect, make_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("AUTH_INTEGRATION_TESTS") != "1"
    or os.environ.get("ASSISTANT_INTEGRATION_TESTS") != "1",
    reason="requires both explicit opt-ins and the guarded disposable PG17 target",
)


@pytest.fixture
def assistant_db():
    # make_settings verifies loopback, non-shared port/name, PG17, least-privilege
    # role and a private marker. It refuses unknown targets before any write.
    settings = make_settings()
    with connect(settings) as conn:
        migrated = conn.execute(
            """SELECT EXISTS (SELECT 1 FROM system.schema_migrations
               WHERE migration_id='0011_internal_chat_turns') AS applied,
               to_regclass('conversation.assistant_turns') IS NOT NULL AS table_exists"""
        ).fetchone()
        assert migrated["applied"] and migrated["table_exists"], (
            "Apply 0011 only to the disposable PG17 database before this test"
        )
        today = datetime.now(UTC).date()
        global_before = conn.execute(
            "SELECT hit_count FROM integration.chat_daily_global_budget WHERE budget_day=%s",
            (today,),
        ).fetchone()

    user_id = uuid4()
    traveler = TravelerRepository(settings)
    with connect(settings) as conn, conn.transaction():
        conn.execute(
            """INSERT INTO identity.users (user_id,auth_subject,is_synthetic)
               VALUES (%s,%s,FALSE)""",
            (user_id, f"assistant-disposable-test-{user_id}"),
        )
    try:
        conversation_id, trip_id, _, created = traveler.create_conversation(
            user_id=user_id,
            locale="fa-IR",
            request_text="سفر سه روزه به اصفهان",
            extracted_requirements={"durationDays": {"value": 3}},
            confirmed_requirements={},
            destination_ids=[],
            idempotency_key=f"assistant-fixture-{uuid4().hex}",
        )
        assert created
        yield traveler, AssistantTurnRepository(traveler), user_id, conversation_id, trip_id
    finally:
        with connect(settings) as conn, conn.transaction():
            # Delete only this fixture's user. All owner-linked rows cascade.
            conn.execute("DELETE FROM identity.users WHERE user_id=%s", (user_id,))
            # The global counter has no owner FK. Restore the original count
            # only in this explicitly disposable, single-run test database.
            if global_before is None:
                conn.execute(
                    "DELETE FROM integration.chat_daily_global_budget WHERE budget_day=%s",
                    (today,),
                )
            else:
                conn.execute(
                    """UPDATE integration.chat_daily_global_budget SET hit_count=%s
                       WHERE budget_day=%s""",
                    (global_before["hit_count"], today),
                )


def _reserve(assistant, user_id, conversation_id, trip_id, *, key, version=1,
             content="لطفاً درباره سفر سؤال بپرس", per_user_limit=8,
             global_limit=100000):
    return assistant.reserve(
        user_id=user_id, conversation_id=conversation_id, trip_id=trip_id,
        idempotency_key=key, expected_version=version, content=content,
        extracted_requirements=None, per_user_limit=per_user_limit,
        global_limit=global_limit,
    )


def test_real_reservation_completion_replay_and_version(assistant_db):
    traveler, assistant, owner, conversation, trip = assistant_db
    key = f"assistant-replay-{uuid4().hex}"
    first = _reserve(assistant, owner, conversation, trip, key=key)
    assert first.created and first.status == "reserved"
    pending = _reserve(assistant, owner, conversation, trip, key=key)
    assert not pending.created and pending.turn_id == first.turn_id
    assert pending.status == "reserved"

    assistant.complete(
        user_id=owner, turn_id=first.turn_id,
        reply="چند نفر سفر می‌کنید؟", requirements={"traveler_count": None},
        clarification="تعداد مسافران؟",
    )
    completed = _reserve(assistant, owner, conversation, trip, key=key)
    assert not completed.created and completed.status == "completed"
    assert completed.turn_id == first.turn_id
    message = assistant.result(
        user_id=owner, conversation_id=conversation, trip_id=trip,
        turn_id=first.turn_id,
    )
    assert message is not None and message["content"] == "چند نفر سفر می‌کنید؟"
    assert message["metadata"]["requirements_candidate"] == {"traveler_count": None}
    assert traveler.conversation(owner, conversation)["version"] == 3
    assert traveler.trip(owner, trip)["confirmed_requirements"] == {}
    with traveler.connection() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM conversation.messages WHERE conversation_id=%s",
            (conversation,),
        ).fetchone()["n"]
    assert n == 3


def test_existing_initial_request_is_attached_without_duplicate_user_message(assistant_db):
    traveler, assistant, owner, conversation, trip = assistant_db
    with traveler.connection() as conn:
        row = conn.execute(
            """SELECT message_id,content FROM conversation.messages
               WHERE conversation_id=%s AND trip_id=%s AND role='user'""",
            (conversation, trip),
        ).fetchone()
        before = conn.execute(
            """SELECT COUNT(*) AS n FROM conversation.messages
               WHERE conversation_id=%s AND trip_id=%s AND role='user'""",
            (conversation, trip),
        ).fetchone()["n"]
    assert before == 1
    reserved = assistant.reserve(
        user_id=owner, conversation_id=conversation, trip_id=trip,
        idempotency_key=f"assistant-initial-{uuid4().hex}", expected_version=1,
        content=row["content"], extracted_requirements=None,
        per_user_limit=8, global_limit=100000,
        existing_user_message_id=row["message_id"],
    )
    assert reserved.created and reserved.user_message_id == row["message_id"]
    with traveler.connection() as conn:
        after = conn.execute(
            """SELECT COUNT(*) AS n FROM conversation.messages
               WHERE conversation_id=%s AND trip_id=%s AND role='user'""",
            (conversation, trip),
        ).fetchone()["n"]
    assert after == before
    assert traveler.conversation(owner, conversation)["version"] == 2
    assert traveler.trip(owner, trip)["confirmed_requirements"] == {}
    with traveler.connection() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM conversation.messages WHERE conversation_id=%s",
            (conversation,),
        ).fetchone()["n"]
    assert n == 1


def test_long_chat_context_retains_initial_request_and_latest_corrections(assistant_db):
    traveler, assistant, owner, conversation, trip = assistant_db
    # The initial trip request is recorded as a real user message by the
    # disposable fixture. More than 12 subsequent messages must not evict it.
    with traveler.connection() as conn, conn.transaction():
        for index in range(14):
            conn.execute(
                """INSERT INTO conversation.messages
                   (message_id,conversation_id,trip_id,role,content,message_type,
                    metadata,is_synthetic,created_at)
                   VALUES (%s,%s,%s,'user',%s,'text','{}'::jsonb,FALSE,
                           NOW()+(%s * INTERVAL '1 second'))""",
                (uuid4(), conversation, trip, f"later-{index}", index + 1),
            )
    context = assistant.history(
        user_id=owner, conversation_id=conversation, trip_id=trip,
        exclude_message_id=uuid4(),
    )
    assert len(context) == 12
    assert context[0] == {"role": "user", "content": "سفر سه روزه به اصفهان"}
    assert [entry["content"] for entry in context[1:]] == [
        f"later-{index}" for index in range(3, 14)
    ]
    assert assistant.history(
        user_id=uuid4(), conversation_id=conversation, trip_id=trip,
        exclude_message_id=uuid4(),
    ) == []


def test_real_owner_scope_and_conflicting_replay(assistant_db):
    _, assistant, owner, conversation, trip = assistant_db
    key = f"assistant-owner-{uuid4().hex}"
    with pytest.raises(TravelerNotFound):
        _reserve(assistant, uuid4(), conversation, trip, key=key)
    first = _reserve(assistant, owner, conversation, trip, key=key)
    with pytest.raises(TravelerConflict):
        _reserve(assistant, owner, conversation, trip, key=key, content="متن متفاوت")
    assert first.created


def test_real_budget_rollback_and_failed_turn_not_retried(assistant_db):
    traveler, assistant, owner, conversation, trip = assistant_db
    key = f"assistant-budget-{uuid4().hex}"
    first = _reserve(
        assistant, owner, conversation, trip,
        key=key, per_user_limit=1,
    )
    assert first.created
    with pytest.raises(ChatBudgetExceeded):
        _reserve(
            assistant, owner, conversation, trip,
            key=f"assistant-overlimit-{uuid4().hex}", version=2,
            per_user_limit=1,
        )
    assistant.fail(user_id=owner, turn_id=first.turn_id)
    replay = _reserve(
        assistant, owner, conversation, trip,
        key=key, version=1,
    )
    assert replay.status == "failed" and not replay.created
    with traveler.connection() as conn:
        hits = conn.execute(
            """SELECT hit_count FROM integration.chat_daily_user_budget
               WHERE user_id=%s AND budget_day=(NOW() AT TIME ZONE 'UTC')::date""",
            (owner,),
        ).fetchone()
    assert hits["hit_count"] == 1


def test_real_concurrent_same_key_reserves_once(assistant_db):
    traveler, assistant, owner, conversation, trip = assistant_db
    key = f"assistant-concurrent-{uuid4().hex}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_reserve, assistant, owner, conversation, trip, key=key)
                   for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert sorted(result.created for result in results) == [False, True]
    assert results[0].turn_id == results[1].turn_id
    with traveler.connection() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM conversation.assistant_turns WHERE conversation_id=%s",
            (conversation,),
        ).fetchone()["n"]
    assert n == 1


def test_real_assistant_message_deletion_cascades_turn(assistant_db):
    traveler, assistant, owner, conversation, trip = assistant_db
    first = _reserve(
        assistant, owner, conversation, trip,
        key=f"assistant-delete-{uuid4().hex}",
    )
    assistant.complete(
        user_id=owner, turn_id=first.turn_id,
        reply="سلام", requirements={}, clarification=None,
    )
    message = assistant.result(
        user_id=owner, conversation_id=conversation, trip_id=trip,
        turn_id=first.turn_id,
    )
    with traveler.connection() as conn, conn.transaction():
        conn.execute(
            "DELETE FROM conversation.messages WHERE message_id=%s",
            (message["message_id"],),
        )
        turn = conn.execute(
            "SELECT turn_id FROM conversation.assistant_turns WHERE turn_id=%s",
            (first.turn_id,),
        ).fetchone()
        assert turn is None


@pytest.mark.parametrize("proposed", [None, {"durationDays": {"value": 12}}])
def test_real_assistant_chat_preserves_confirmed_trip_and_version(assistant_db, proposed):
    traveler, assistant, owner, conversation, trip = assistant_db
    # Use the real confirmation path so the consent remains bound to the
    # approved trip version, as it would in the traveler journey.
    original = traveler.trip(owner, trip)
    traveler.confirm_trip_profile(
        user_id=owner, trip_id=trip, expected_version=original["version"],
        confirmed_requirements={
            "duration_days": 15,
            "constraints": ["wheelchair access is mandatory"],
            "confirmation_source": "traveler_reviewed",
        },
        destination_ids=[],
        requirement_consent={
            "contract_version": "recommendation-consent-v1",
            "field_decisions": {},
            "advisory_acknowledged_fields": [],
        },
    )
    before = traveler.trip(owner, trip)
    assert before["duration_days"] == 15
    assert before["confirmed_requirements"]["requirement_consent"]["profile_version"] == before["version"]
    conversation_version = traveler.conversation(owner, conversation)["version"]

    reserved = assistant.reserve(
        user_id=owner, conversation_id=conversation, trip_id=trip,
        idempotency_key=f"assistant-preserve-{uuid4().hex}",
        expected_version=conversation_version,
        content="برای این سفر چه پیشنهادهایی دارید؟",
        extracted_requirements=proposed,
        per_user_limit=8, global_limit=100000,
    )
    assert reserved.created
    assistant.complete(
        user_id=owner, turn_id=reserved.turn_id,
        reply="می‌توانم چند پیشنهاد بررسی‌نشده ارائه کنم.",
        requirements={"duration_days": 12}, clarification=None,
    )
    after = traveler.trip(owner, trip)
    assert after["version"] == before["version"]
    assert after["confirmed_requirements"] == before["confirmed_requirements"]
    assert after["extracted_requirements"] == before["extracted_requirements"]
    assert after["duration_days"] == before["duration_days"] == 15
    assert traveler.conversation(owner, conversation)["version"] == conversation_version + 2


def test_real_saved_assistant_candidate_is_reopenable_by_owner(assistant_db):
    traveler, assistant, owner, conversation, trip = assistant_db
    reserved = _reserve(
        assistant, owner, conversation, trip,
        key=f"assistant-reopen-{uuid4().hex}",
    )
    assistant.complete(
        user_id=owner, turn_id=reserved.turn_id,
        reply="کاشان می‌تواند گزینه‌ای برای بررسی باشد.",
        requirements={"destination": "کاشان", "duration_days": 2,
                      "budget": "unverified"},
        clarification=None,
    )
    restored = traveler.conversation(owner, conversation)
    matching = [msg for msg in restored["messages"] if msg["role"] == "assistant"]
    assert len(matching) == 1
    assert matching[0]["candidate_requirements"] == {
        "destination": "کاشان", "duration_days": 2,
    }
    assert "metadata" not in matching[0]
    assert traveler.conversation(uuid4(), conversation) is None
