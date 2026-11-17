"""Offline contract: stored assistant hints are reviewable but raw metadata stays private."""
from datetime import UTC, datetime
from uuid import uuid4

from app.modules.trip.repository import _public_conversation_message
from app.modules.trip.requirements_interpretation import interpret_trip_requirements
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


def test_public_history_rejects_literal_backslash_and_control_character_in_cities():
    for invalid in ("bad\ncity", "bad\\ncity"):
        row = _public_conversation_message(message(
            "assistant", {"requirements_candidate": {
                "destination": invalid, "origin": invalid,
            }},
        ))
        assert MessageResponse.model_validate(row).candidate_requirements == {}


def test_owner_history_can_reopen_only_validated_budget_dates_and_interest():
    row = _public_conversation_message(message(
        "assistant",
        {"requirements_candidate": {
            "budget_text": "200000 تومان", "travel_start": "2027-03-01",
            "travel_end": "2027-03-04", "interest": "باغ‌های تاریخی",
            "hard_constraint": "do not forward", "secret": "never-public",
        }},
    ))
    parsed = MessageResponse.model_validate(row)
    assert parsed.candidate_requirements == {
        "budget_text": "200000 تومان", "travel_start": "2027-03-01",
        "travel_end": "2027-03-04", "interest": "باغ‌های تاریخی",
    }
    assert "never-public" not in str(parsed.model_dump())
    assert "hard_constraint" not in str(parsed.model_dump())


def test_history_rejects_unsupported_dates_and_budget_without_denomination():
    row = _public_conversation_message(message(
        "assistant", {"requirements_candidate": {
            "travel_start": "2027-02-30", "travel_end": "2027-03-02",
            "budget_text": "cheap", "interest": "bad\\ntext",
        }},
    ))
    assert MessageResponse.model_validate(row).candidate_requirements == {}


def test_typed_five_key_candidate_survives_owner_history_response_validation():
    profile = interpret_trip_requirements("Plan a trip to Shiraz", "en-US")
    row = _public_conversation_message(message(
        "assistant", {"requirements_candidate": profile.model_dump(mode="json")},
    ))
    parsed = MessageResponse.model_validate(row)
    assert parsed.candidate_requirements["contract_version"] == "trip-requirements-v1"
    assert len(parsed.candidate_requirements) == 5
    assert "metadata" not in row
