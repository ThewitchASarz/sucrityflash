import pytest
from pydantic import ValidationError

from apps.api.schemas.run import RunStart
from apps.api.models.project import Project


def test_run_start_requires_required_fields():
    with pytest.raises(ValidationError):
        RunStart()

    payload = RunStart(
        reviewer_approval="rev-ok",
        engineer_approval="eng-ok",
        started_by="operator@example.com",
        monitored_rate_limit_rpm=60,
        monitored_max_concurrency=10,
    )
    assert payload.started_by == "operator@example.com"
    assert payload.monitored_rate_limit_rpm == 60


def test_project_has_target_url_column():
    column_names = [c.name for c in Project.__table__.columns]
    assert "target_url" in column_names
