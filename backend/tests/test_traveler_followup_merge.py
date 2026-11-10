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
