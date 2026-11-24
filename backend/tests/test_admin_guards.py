import pytest
from fastapi import HTTPException

from app.api.admin_guards import privileged_admin_writes_available, require_privileged_admin_step_up


@pytest.mark.parametrize("environment", ["staging", "production", "prod", "preview"])
def test_public_environments_fail_closed_without_privileged_step_up(environment):
    assert privileged_admin_writes_available(environment) is False
    with pytest.raises(HTTPException) as error:
        require_privileged_admin_step_up(environment)
    assert error.value.status_code == 403
    assert error.value.detail == "privileged_admin_step_up_unavailable"


@pytest.mark.parametrize("environment", ["development", "test", "local_pilot"])
def test_isolated_and_local_environments_keep_existing_audited_review_workflows(environment):
    assert privileged_admin_writes_available(environment) is True
    require_privileged_admin_step_up(environment)


def test_environment_matching_is_case_and_whitespace_insensitive():
    assert privileged_admin_writes_available(" Production ") is False
