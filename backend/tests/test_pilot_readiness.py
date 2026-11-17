from app.core.pilot_readiness import (
    LiveChatSmokeInputs,
    PilotReadinessInputs,
    evaluate_pilot_readiness,
    evaluate_single_chat_smoke,
)


def test_pilot_readiness_fails_closed_by_default() -> None:
    result = evaluate_pilot_readiness(PilotReadinessInputs())

    assert not result.ready
    assert "approved_published_content_missing" in result.blockers
    assert "production_sms_not_authorized" in result.blockers
    assert "remote_chat_not_authorized" in result.blockers
    assert "physical_device_acceptance_incomplete" in result.blockers


def test_pilot_readiness_rejects_shared_development_database() -> None:
    result = evaluate_pilot_readiness(
        PilotReadinessInputs(
            database_host="127.0.0.1",
            database_port=55433,
            database_name="ai_tourism_dev",
        )
    )

    assert "shared_development_database_target_forbidden" in result.blockers


def test_https_rejects_loopback_and_embedded_credentials() -> None:
    loopback = evaluate_pilot_readiness(
        PilotReadinessInputs(
            public_origin="https://127.0.0.1",
            owner_rag_origin="http://127.0.0.1:8765",
            remote_chat_endpoint="https://user:secret@example.invalid",
        )
    )

    assert "public_https_origin_not_configured" in loopback.blockers
    assert "production_owner_rag_https_origin_not_configured" in loopback.blockers
    assert "remote_chat_https_endpoint_not_configured" in loopback.blockers


def test_live_chat_smoke_requires_each_explicit_gate_and_single_call() -> None:
    result = evaluate_single_chat_smoke(LiveChatSmokeInputs())

    assert not result.ready
    assert "owner_live_call_authorization_missing" in result.blockers
    assert "traveler_remote_processing_consent_missing" in result.blockers
    assert "chat_smoke_must_be_limited_to_one_call" in result.blockers


def test_single_chat_smoke_reports_ready_only_with_all_staging_gates() -> None:
    result = evaluate_single_chat_smoke(
        LiveChatSmokeInputs(
            app_environment="test",
            gateway_enabled=True,
            endpoint="https://chat.example.invalid",
            credential_available=True,
            owner_authorized=True,
            traveler_processing_consent=True,
            budget_approved=True,
            max_calls=1,
            max_output_tokens=400,
        )
    )

    assert result.ready
    assert result.blockers == ()


def test_single_chat_smoke_cannot_run_in_production_or_exceed_one_call() -> None:
    result = evaluate_single_chat_smoke(
        LiveChatSmokeInputs(
            app_environment="production",
            gateway_enabled=True,
            endpoint="https://chat.example.invalid",
            credential_available=True,
            owner_authorized=True,
            traveler_processing_consent=True,
            budget_approved=True,
            max_calls=2,
            max_output_tokens=100,
        )
    )

    assert "live_smoke_must_run_in_isolated_staging" in result.blockers
    assert "chat_smoke_must_be_limited_to_one_call" in result.blockers
