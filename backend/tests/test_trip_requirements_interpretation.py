from datetime import date

import pytest

from app.modules.trip.requirements_interpretation import (
    TripInterpretationRequest,
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


def test_unselected_server_date_and_timezone_are_never_inferred():
    request = TripInterpretationRequest(request_text=EXAMPLE, locale="fa-IR")
    result = interpret_trip_requirements(
        request.request_text, request.locale,
        traveler_timezone=request.traveler_timezone,
        traveler_reference_date=request.traveler_reference_date,
    )
    assert result.fields.relative_start_date.value.anchor_date is None
    assert result.fields.relative_start_date.value.timezone is None
