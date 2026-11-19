from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.partners import TravelerCompanyShareInput


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
