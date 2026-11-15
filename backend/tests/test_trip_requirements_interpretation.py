from datetime import date

import pytest

from app.modules.trip.requirements_interpretation import (
    TripInterpretationRequest,
    TripRequirementsV1,
    interpret_trip_requirements,
)


EXAMPLE = "از دو روز دیگه با 4 نفر میخوام برم از مناطق تاریخی شیراز دیدن کنم و فقط 10 میلیون هزینه میخوام بکنم"


def test_persian_relative_departure_is_not_trip_duration_and_budget_currency_stays_unknown():
    result = interpret_trip_requirements(EXAMPLE, "fa-IR")
    fields = result.fields

    assert result.original_text == EXAMPLE
    assert fields.destination.value == "شیراز"
    assert fields.travelers.value == 4
    assert fields.relative_start_date.value.offset_days == 2
    assert fields.relative_start_date.value.anchor_date is None
    assert fields.duration_days.status == "missing"
    assert fields.duration_days.value is None
    assert fields.budget.value.amount == "10"
    assert fields.budget.value.scale == "million"
    assert fields.budget.value.currency is None
    assert fields.budget.value.currency_status == "unknown"
    assert fields.budget.value.raw == "10 میلیون"
    assert fields.interests.value == ["historical_attractions"]
    assert result.clarification.missing_fields == ["duration_days"]
    assert "budget.currency" in result.clarification.question_fields
    assert "relative_start_date.anchor" not in result.clarification.question_fields

    for field in (fields.destination, fields.travelers, fields.relative_start_date,
                  fields.budget, fields.interests):
        span = field.evidence_span
        assert span is not None
        assert EXAMPLE[span.start:span.end] == span.text


def test_relative_departure_is_anchored_only_to_explicit_reference_context():
    result = interpret_trip_requirements(
        EXAMPLE, "fa-IR", traveler_timezone="Asia/Tehran", traveler_reference_date=date(2026, 11, 11),
    )
    relative = result.fields.relative_start_date.value
    assert relative.anchor_date == date(2026, 11, 13)
    assert relative.timezone == "Asia/Tehran"
    assert "relative_start_date.anchor" not in result.clarification.question_fields


@pytest.mark.parametrize(
    ("phrase", "expected_days"),
    [("سفر سه‌روزه به شیراز", 3), ("سفر سه روزه به شیراز", 3),
     ("از سه روز دیگر به شیراز می‌روم", None), ("سه روز دیگر به شیراز", None)],
)
def test_duration_parser_separates_trip_length_from_relative_departure(phrase, expected_days):
    result = interpret_trip_requirements(phrase, "fa-IR")
    if expected_days is None:
        assert result.fields.duration_days.status == "missing"
        assert result.fields.relative_start_date.value.offset_days == 3
    else:
        assert result.fields.duration_days.value == expected_days
        assert result.fields.relative_start_date.status == "missing"


def test_budget_parser_does_not_take_the_traveler_count_as_amount():
    result = interpret_trip_requirements(EXAMPLE, "fa-IR")
    assert result.fields.travelers.value == 4
    assert result.fields.budget.value.amount == "10"


def test_english_toman_denomination_is_preserved_without_conversion():
    text = "Please plan a trip with a budget of 20 million toman."
    result = interpret_trip_requirements(text, "en-US")
    budget = result.fields.budget.value
    assert budget.amount == "20"
    assert budget.scale == "million"
    assert budget.currency == "TOMAN"
    assert budget.currency_status == "known"
    assert budget.raw == "20 million toman"
    span = result.fields.budget.evidence_span
    assert span is not None
    assert text[span.start:span.end] == budget.raw


def test_persian_soft_preference_accessibility_and_hard_constraint_are_distinct():
    text = (
        "سفر ۱۵ روزه به شیراز با بودجهٔ ۲۰ میلیون تومان؛ به طبیعت و جاهای تاریخی علاقه دارم؛ "
        "ترجیح می‌دهم مسیرها سنگ‌فرش باشند؛ دسترسی ویلچر ضروری است؛ "
        "باید از مسیرهای ناهموار پرهیز شود."
    )
    fields = interpret_trip_requirements(text, "fa-IR").fields
    assert fields.destination.value == "شیراز"
    assert fields.duration_days.value == 15
    assert fields.budget.value.currency == "TOMAN"
    assert fields.interests.value == ["historical_attractions"]
    assert fields.soft_preferences.status == "known"
    assert "سنگ‌فرش" in fields.soft_preferences.value[0]
    assert fields.accessibility.value == ["wheelchair_access"]
    assert fields.hard_constraints.status == "known"
    assert "ناهموار" in fields.hard_constraints.value[0]



def test_arabic_hard_constraint_uses_arabic_yeh_without_waiving_accessibility():
    text = (
        "\u0631\u062d\u0644\u0629 \u0644\u0645\u062f\u0629 10 \u0623\u064a\u0627\u0645 \u0625\u0644\u0649 Shiraz; "
        "\u0627\u062d\u062a\u064a\u0627\u062c\u0627\u062a \u062d\u0631\u0643\u064a\u0629 \u0636\u0631\u0648\u0631\u064a\u0629; "
        "\u064a\u062c\u0628 \u062a\u062c\u0646\u0628 \u0627\u0644\u0637\u0631\u0642 \u0627\u0644\u0648\u0639\u0631\u0629."
    )
    fields = interpret_trip_requirements(text, "ar").fields
    assert fields.duration_days.value == 10
    assert fields.accessibility.value == ["wheelchair_access"]
    assert fields.hard_constraints.status == "known"
    assert "\u064a\u062c\u0628" in fields.hard_constraints.value[0]


@pytest.mark.parametrize(
    ("phrase", "locale"),
    [
        ("I won't travel by boat", "en-US"),
        ("I can't use a boat", "en-US"),
        ("\u0628\u0627 \u0642\u0627\u06cc\u0642 \u0646\u0645\u06cc\u200c\u0631\u0648\u06cc\u0645", "fa-IR"),
    ],
)
def test_explicit_transport_prohibitions_remain_hard_constraints(phrase, locale):
    fields = interpret_trip_requirements(phrase, locale).fields
    assert fields.hard_constraints.status == "known"
    assert fields.soft_preferences.status == "missing"


def test_soft_transport_preference_and_hard_prohibition_stay_separate():
    fields = interpret_trip_requirements("I prefer trains but won't travel by boat", "en-US").fields
    assert fields.soft_preferences.value == ["trains"]
    assert fields.hard_constraints.value == ["won't travel by boat"]


@pytest.mark.parametrize(
    ("phrase", "offset"),
    [
        ("\u0628\u0639\u062f \u062b\u0644\u0627\u062b\u0629 \u0623\u064a\u0627\u0645", 3),
        ("\u0628\u0639\u062f 3 \u0623\u064a\u0627\u0645", 3),
    ],
)
def test_arabic_relative_day_offsets(phrase, offset):
    relative = interpret_trip_requirements(
        phrase, "ar", traveler_timezone="Asia/Tehran", traveler_reference_date=date(2026, 11, 15)
    ).fields.relative_start_date
    assert relative.value.offset_days == offset
    assert relative.value.anchor_date == date(2026, 11, 15 + offset)

def test_unselected_server_date_and_timezone_are_never_inferred():
    request = TripInterpretationRequest(request_text=EXAMPLE, locale="fa-IR")
    result = interpret_trip_requirements(
        request.request_text, request.locale,
        traveler_timezone=request.traveler_timezone,
        traveler_reference_date=request.traveler_reference_date,
    )
    assert result.fields.relative_start_date.value.anchor_date is None
    assert result.fields.relative_start_date.value.timezone is None


@pytest.mark.parametrize(
    ("phrase", "offset"), [
        ("از فردا سفر می‌کنم", 1),
        ("از پس فردا سفر می‌کنم", 2),
        ("پس‌فردا می‌رویم", 2),
        ("Travel tomorrow", 1),
        ("Travel the day after tomorrow", 2),
        ("السفر غداً", 1),
        ("السفر بعد غد", 2),
    ],
)
def test_relative_tomorrow_across_locales(phrase, offset):
    locale = "en-US" if "Travel" in phrase else "ar" if "السفر" in phrase else "fa-IR"
    result = interpret_trip_requirements(
        phrase, locale,
        traveler_timezone="Asia/Tehran", traveler_reference_date=date(2026, 11, 15),
    )
    relative = result.fields.relative_start_date.value
    assert relative.offset_days == offset
    assert relative.anchor_date == date(2026, 11, 15 + offset)


@pytest.mark.parametrize(
    ("phrase", "offset", "reference", "expected"),
    [
        ("از امروز سفر می‌کنم", 0, date(2026, 12, 31), date(2026, 12, 31)),
        ("Travel today", 0, date(2026, 12, 31), date(2026, 12, 31)),
        ("Travel tomorrow", 1, date(2026, 12, 31), date(2027, 1, 1)),
        ("Travel the day after tomorrow", 2, date(2026, 12, 31), date(2027, 1, 2)),
        ("السفر غداً", 1, date(2026, 2, 28), date(2026, 3, 1)),
        ("السفر اليوم", 0, date(2026, 2, 28), date(2026, 2, 28)),
    ],
)
def test_relative_day_dates_use_explicit_local_reference_and_roll_over(
    phrase, offset, reference, expected,
):
    result = interpret_trip_requirements(
        phrase, "en-US" if phrase.startswith("Travel") else "ar",
        traveler_timezone="Asia/Tehran", traveler_reference_date=reference,
    )
    relative = result.fields.relative_start_date.value
    assert relative.offset_days == offset
    assert relative.anchor_date == expected
    assert result.fields.duration_days.status == "missing"


def test_relative_days_remain_unanchored_without_traveler_reference_context():
    result = interpret_trip_requirements("Travel tomorrow", "en-US")
    assert result.fields.relative_start_date.value.offset_days == 1
    assert result.fields.relative_start_date.value.anchor_date is None
    assert result.fields.duration_days.status == "missing"


def test_legacy_typed_requirements_default_soft_preferences_to_missing():
    payload = interpret_trip_requirements("Plan a trip to Shiraz", "en-US").model_dump(mode="python")
    payload["fields"].pop("soft_preferences")
    restored = TripRequirementsV1.model_validate(payload)
    assert restored.fields.soft_preferences.status == "missing"
    assert restored.fields.soft_preferences.value is None
    assert restored.fields.soft_preferences.source == "fallback"
