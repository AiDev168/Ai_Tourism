"""Offline regression for applying correction turns without losing safety requirements."""

from app.modules.trip.repository import _merge_extraction


def field(value, status="extracted"):
    return {"value": value, "status": status, "evidence": None}


def test_follow_up_replaces_explicit_duration_and_keeps_other_fields():
    previous = {"requestText": "Plan a 3-day trip to Shiraz",
                "durationDays": field(3),
                "destinations": field(["Shiraz"]),
                "constraints": field(["no stairs"])}
    followup = {"requestText": previous["requestText"],
                "durationDays": field(5),
                "destinations": field(None, "unknown"),
                "constraints": field(None, "unknown")}
    merged = _merge_extraction(previous, followup)
    assert merged["durationDays"]["value"] == 5
    assert merged["destinations"]["value"] == ["Shiraz"]
    assert merged["constraints"]["value"] == ["no stairs"]
    assert merged["requestText"] == previous["requestText"]


def test_ambiguous_correction_must_not_restore_prior_duration():
    previous = {"durationDays": field(3), "destinations": field(["Shiraz"])}
    followup = {"durationDays": field(None, "ambiguous"),
                "destinations": field(None, "unknown")}
    merged = _merge_extraction(previous, followup)
    assert merged["durationDays"] == followup["durationDays"]
    assert merged["destinations"] == previous["destinations"]
    assert previous["durationDays"]["value"] == 3


def test_follow_up_does_not_restore_initial_typed_snapshot_over_a_corrected_profile():
    previous = {
        "requestText": "سفر ۱۵ روزه به شیراز با بودجهٔ ۲۰ میلیون تومان",
        "budget": field({"amount": 20, "currency": "TOMAN", "unit": "million", "raw": "۲۰ میلیون تومان"}),
        "requirements_v1": {"contract_version": "trip-requirements-v1", "fields": {"budget": field("20")}},
    }
    correction = {
        "requestText": previous["requestText"],
        "budget": field({"amount": 45, "currency": "TOMAN", "unit": "million", "raw": "۴۵ میلیون تومان"}),
    }
    corrected = _merge_extraction(previous, correction)
    assert corrected["budget"]["value"]["amount"] == 45
    assert "requirements_v1" not in corrected
    later = _merge_extraction(corrected, {"requestText": previous["requestText"], "durationDays": field(15)})
    assert later["budget"]["value"]["amount"] == 45
