"""Offline contract: stored assistant hints are reviewable but raw metadata stays private."""
from datetime import UTC, datetime
from uuid import uuid4

from app.modules.trip.repository import _public_conversation_message
from app.modules.trip.schemas import MessageResponse


def message(role: str, metadata: object) -> dict:
    return {
        "message_id": uuid4(),
        "conversation_id": uuid4(),
        "trip_id": uuid4(),
        "role": role,
        "content": "پیشنهاد بررسی‌نشده",
        "created_at": datetime.now(UTC),
        "metadata": metadata,
    }


def test_only_bounded_candidate_fields_are_exposed():
    row = _public_conversation_message(message(
        "assistant",
        {"source": "internal_chat", "secret": "never-public",
         "requirements_candidate": {
             "destination": "  کاشان  ", "duration_days": 3,
             "budget": 900_000, "internal": "never-public"}},
    ))
    parsed = MessageResponse.model_validate(row)
    assert parsed.candidate_requirements == {"destination": "کاشان", "duration_days": 3}
    assert "metadata" not in row
    assert "secret" not in str(parsed.model_dump())


def test_user_metadata_and_invalid_ai_hints_are_not_public():
    for role, candidate in [
        ("user", {"destination": "تهران", "duration_days": 2}),
        ("assistant", {"destination": "bad\nname", "duration_days": 999}),
        ("assistant", {"destination": "", "duration_days": True}),
    ]:
        row = _public_conversation_message(message(
            role, {"requirements_candidate": candidate, "internal": "private"}))
        assert MessageResponse.model_validate(row).candidate_requirements == {}
        assert "metadata" not in row


def test_public_owner_history_exposes_bounded_origin_and_traveler_count_only():
    row = _public_conversation_message(message(
        "assistant",
        {"requirements_candidate": {
            "destination": "کاشان", "duration_days": 3,
            "origin": "  تهران ", "traveler_count": 4,
            "budget": "private", "secret": "never-public",
        }},
    ))
    parsed = MessageResponse.model_validate(row)
    assert parsed.candidate_requirements == {
        "destination": "کاشان", "duration_days": 3,
        "origin": "تهران", "traveler_count": 4,
    }
    assert "never-public" not in str(parsed.model_dump())
    assert "metadata" not in row
