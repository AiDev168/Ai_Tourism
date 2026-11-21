from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.partners import CompanyTripResponseInput, TravelerCompanyShareInput, TravelerCompanyDecisionInput


def test_company_sharing_requires_explicit_consent_and_unique_selected_recipients():
    first, second = uuid4(), uuid4()
    request = TravelerCompanyShareInput(
        organization_ids=[first, second], consent_confirmed=True,
        include_original_request=False,
    )
    assert request.organization_ids == [first, second]
    assert request.include_original_request is False

    with pytest.raises(ValidationError):
        TravelerCompanyShareInput(organization_ids=[first], consent_confirmed=False)
    with pytest.raises(ValidationError):
        TravelerCompanyShareInput(organization_ids=[first, first], consent_confirmed=True)


def test_company_sharing_rejects_empty_or_oversized_recipient_lists():
    with pytest.raises(ValidationError):
        TravelerCompanyShareInput(organization_ids=[], consent_confirmed=True)
    with pytest.raises(ValidationError):
        TravelerCompanyShareInput(
            organization_ids=[uuid4() for _ in range(11)], consent_confirmed=True,
        )


def test_broadcast_requires_separate_explicit_consent_and_no_raw_original_text():
    verified = TravelerCompanyShareInput(
        recipient_mode="all_eligible", organization_ids=[], consent_confirmed=True,
        broad_sharing_consent_confirmed=True, include_original_request=False,
    )
    assert verified.recipient_mode == "all_eligible"
    with pytest.raises(ValidationError):
        TravelerCompanyShareInput(recipient_mode="all_eligible", consent_confirmed=True)
    with pytest.raises(ValidationError):
        TravelerCompanyShareInput(recipient_mode="all_eligible", organization_ids=[uuid4()],
                                  consent_confirmed=True, broad_sharing_consent_confirmed=True)
    with pytest.raises(ValidationError):
        TravelerCompanyShareInput(recipient_mode="all_eligible", consent_confirmed=True,
                                  broad_sharing_consent_confirmed=True,
                                  include_original_request=True)


def test_company_acceptance_cannot_silently_modify_original_terms():
    base = dict(client_request_id=uuid4(), revision_id=uuid4(),
                response_kind="accepted_as_requested", message="Accepted with no changes.")
    assert CompanyTripResponseInput(**base).proposed_price_toman is None
    with pytest.raises(ValidationError):
        CompanyTripResponseInput(**base, proposed_price_toman=Decimal("25000000"))
    with pytest.raises(ValidationError):
        CompanyTripResponseInput(**base, proposed_start_date=date(2026, 12, 5),
                                  proposed_end_date=date(2026, 12, 8))


def test_company_counter_offer_requires_real_change_and_valid_dates():
    base = dict(client_request_id=uuid4(), revision_id=uuid4(),
                response_kind="counter_offer", message="We propose a new schedule.")
    with pytest.raises(ValidationError):
        CompanyTripResponseInput(**base)
    with pytest.raises(ValidationError):
        CompanyTripResponseInput(**base, proposed_start_date=date(2026, 12, 8))
    with pytest.raises(ValidationError):
        CompanyTripResponseInput(**base, proposed_start_date=date(2026, 12, 8),
                                  proposed_end_date=date(2026, 12, 5))
    proposal = CompanyTripResponseInput(**base, proposed_price_toman=Decimal("27000000.00"),
                                        proposed_start_date=date(2026, 12, 5),
                                        proposed_end_date=date(2026, 12, 8))
    assert proposal.proposed_price_toman == Decimal("27000000.00")
    assert TravelerCompanyDecisionInput(decision="accepted").decision == "accepted"
    with pytest.raises(ValidationError):
        TravelerCompanyDecisionInput(decision="pending")
