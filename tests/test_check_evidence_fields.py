"""Check-summary and retained-evidence response compatibility contracts."""

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest
from pydantic import TypeAdapter, ValidationError

from bisibility import (
    AsyncBisibilityClient,
    BisibilityClient,
    NotificationPreferencesPatch,
    RankCheck,
)
from bisibility.models import CloudImportNotificationPreference, RankHistoryExportRow
from bisibility.rank_check_runs import RankCheckRunRead
from bisibility.rank_history_report import RankHistoryReportRecord

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = json.loads((FIXTURES / "check-evidence-fields.json").read_text())
PROJECT = FIXTURE["preferences"]["project_id"]
NEW_FIELDS = {
    "check_notification_setting": "important",
    "check_notification_top_n": 10,
    "check_notification_position_move": 5,
    "provider_incident_in_app": False,
}


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("field,value", NEW_FIELDS.items())
@pytest.mark.parametrize("mapping", [False, True])
def test_preference_writes_and_typed_warnings(asynchronous, field, value, mapping):
    calls = []
    response = {**FIXTURE["preferences"], "warnings": [FIXTURE["warning"]]}

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=response)

    options = dict(
        api_key="bsb_key_test_fixture",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    )
    payload = {field: value}
    body = payload if mapping else NotificationPreferencesPatch.model_validate(payload)
    if asynchronous:

        async def scenario():
            async with AsyncBisibilityClient(**options) as client:
                return await client.update_notification_preferences(PROJECT, body)

        result = asyncio.run(scenario())
    else:
        with BisibilityClient(**options) as client:
            result = client.update_notification_preferences(PROJECT, body)
    assert json.loads(calls[0].content) == payload
    assert calls[0].method == "PATCH"
    assert result.warnings[0].field == "check_in_app"
    assert result.warnings[0].code == FIXTURE["warning"]["code"]
    assert result.warnings[0].message == FIXTURE["warning"]["message"]
    for name, expected in NEW_FIELDS.items():
        assert getattr(result, name) == expected
        assert name not in (result.model_extra or {})


@pytest.mark.parametrize("model", [NotificationPreferencesPatch, CloudImportNotificationPreference])
@pytest.mark.parametrize("value", ["all", "important", "none"])
def test_preference_setting_input_enum(model, value):
    assert model(check_notification_setting=value).check_notification_setting == value


@pytest.mark.parametrize("model", [NotificationPreferencesPatch, CloudImportNotificationPreference])
@pytest.mark.parametrize("field", NEW_FIELDS)
@pytest.mark.parametrize("value", [None, "invalid", 0, 101, True, 1.5])
def test_preference_input_rejects_invalid_values(model, field, value):
    if field == "provider_incident_in_app" and value is True:
        return
    with pytest.raises(ValidationError):
        model.model_validate({field: value})


@pytest.mark.parametrize("field", ["check_notification_top_n", "check_notification_position_move"])
@pytest.mark.parametrize("value", [1, 100])
@pytest.mark.parametrize("model", [NotificationPreferencesPatch, CloudImportNotificationPreference])
def test_preference_threshold_boundaries(model, field, value):
    assert getattr(model.model_validate({field: value}), field) == value


def test_preference_responses_and_legacy_write():
    from bisibility import NotificationPreferences, NotificationPreferencesUpdated

    legacy = {k: v for k, v in FIXTURE["preferences"].items() if k not in NEW_FIELDS}
    assert NotificationPreferences.model_validate(legacy).check_notification_setting is None
    result = NotificationPreferencesUpdated.model_validate(legacy)
    assert result.warnings is None
    assert result.model_dump(exclude_unset=True) == legacy
    assert (
        NotificationPreferences.model_validate(
            {**FIXTURE["preferences"], "check_notification_setting": "future_setting"}
        ).check_notification_setting
        == "future_setting"
    )
    assert NotificationPreferences.model_fields["check_in_app"].deprecated
    assert NotificationPreferencesPatch.model_fields["check_in_app"].deprecated
    assert CloudImportNotificationPreference.model_fields["check_in_app"].deprecated
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, json={**FIXTURE["preferences"], "warnings": [FIXTURE["warning"]]}
        )

    with BisibilityClient(
        api_key="bsb_key_test_fixture",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.update_notification_preferences(PROJECT, {"check_in_app": False})
    assert json.loads(calls[0].content) == {"check_in_app": False}
    assert result.warnings[0].field == "check_in_app"


def test_invalid_mapping_is_rejected_before_transport():
    def handler(request):
        pytest.fail("invalid input reached transport")

    with BisibilityClient(
        api_key="bsb_key_test_fixture",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(ValidationError):
            client.update_notification_preferences(PROJECT, {"check_notification_top_n": 101})


@pytest.mark.parametrize("completeness", ["complete", "partial", "unresolved", "future_value"])
def test_rank_check_evidence_is_typed_and_open(completeness):
    check = RankCheck.model_validate(
        {
            **FIXTURE["check"],
            "comparison_allowed": False,
            "result_completeness": completeness,
            "returned_depth": 0,
            "evidence_projection": FIXTURE["projection"],
        }
    )
    assert check.comparison_allowed is False
    assert check.result_completeness == completeness
    assert check.returned_depth == 0
    assert check.evidence_projection.recovery.reason == "retained evidence"
    assert check.evidence_projection.returned_depth is None
    for name in (
        "comparison_allowed",
        "result_completeness",
        "returned_depth",
        "evidence_projection",
    ):
        assert name not in (check.model_extra or {})


def test_evidence_absent_null_and_nested_required_nulls():
    source = {k: v for k, v in FIXTURE["check"].items() if k != "evidence_projection"}
    legacy = RankCheck.model_validate(source)
    assert legacy.evidence_projection is None
    assert legacy.returned_depth is None
    assert (
        RankCheck.model_validate(
            {**source, "evidence_projection": None, "returned_depth": None}
        ).evidence_projection
        is None
    )
    from bisibility import ProviderEvidenceProjection

    nulls = dict.fromkeys(FIXTURE["projection"])
    assert ProviderEvidenceProjection.model_validate(nulls).model_dump() == nulls
    for field in nulls:
        missing = {k: v for k, v in nulls.items() if k != field}
        with pytest.raises(ValidationError):
            ProviderEvidenceProjection.model_validate(missing)


@pytest.mark.parametrize(
    "field,value",
    [
        ("comparison_allowed", True),
        ("comparison_allowed", 0),
        ("comparison_allowed", "false"),
        ("comparison_allowed", None),
        ("result_completeness", None),
        ("returned_depth", -1),
        ("returned_depth", True),
        ("returned_depth", 1.5),
    ],
)
def test_rank_check_evidence_rejects_invalid_values(field, value):
    with pytest.raises(ValidationError):
        RankCheck.model_validate({**FIXTURE["check"], field: value})


def test_evidence_on_runs_exports_and_report_records():
    projection = FIXTURE["projection"]
    run_source = json.loads((FIXTURES / "rank-check-runs.json").read_text())["detail"]
    for value in (None, [], [{**projection, "check_id": FIXTURE["check"]["id"]}]):
        run = RankCheckRunRead.model_validate({**run_source, "evidence_projections": value})
        assert "evidence_projections" not in (run.model_extra or {})
        if value:
            assert run.evidence_projections[0].check_id == FIXTURE["check"]["id"]
            assert run.evidence_projections[0].recovery.reason == "retained evidence"
    assert RankCheckRunRead.model_validate(run_source).evidence_projections is None
    row = {**FIXTURE["check"], "keyword": "example keyword"}
    for value in (None, projection):
        parsed = RankHistoryExportRow.model_validate({**row, "evidence_projection": value})
        assert "evidence_projection" not in (parsed.model_extra or {})
        if value:
            assert parsed.evidence_projection.recovery.reason == "retained evidence"
    assert (
        RankHistoryExportRow.model_validate(
            {k: v for k, v in row.items() if k != "evidence_projection"}
        ).evidence_projection
        is None
    )
    report = json.loads((FIXTURES / "rank-history-report.json").read_text())
    for stream in ("observations", "full_attempts"):
        record = copy.deepcopy(
            next(
                row
                for row in report[stream]["data"]
                if row.get("kind") in (None, "logical_rank_check")
            )
        )
        for value in (None, projection):
            parsed = TypeAdapter(RankHistoryReportRecord).validate_python(
                {**record, "evidence_projection": value}
            )
            assert "evidence_projection" not in (parsed.model_extra or {})
            if value:
                assert parsed.evidence_projection.recovery.reason == "retained evidence"


@pytest.mark.parametrize("asynchronous", [False, True])
def test_new_get_responses_preserve_evidence_and_preferences(asynchronous):
    check = {
        **FIXTURE["check"],
        "evidence_projection": FIXTURE["projection"],
        "comparison_allowed": False,
        "result_completeness": "partial",
        "returned_depth": None,
    }

    def handler(request):
        return httpx.Response(
            200,
            json=(
                FIXTURE["preferences"]
                if request.url.path.endswith("notification-preferences")
                else check
            ),
        )

    options = dict(
        api_key="bsb_key_test_fixture",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    )
    if asynchronous:

        async def scenario():
            async with AsyncBisibilityClient(**options) as client:
                return (
                    await client.get_notification_preferences(PROJECT),
                    await client.get_rank_check_result(check["id"]),
                )

        prefs, result = asyncio.run(scenario())
    else:
        with BisibilityClient(**options) as client:
            prefs = client.get_notification_preferences(PROJECT)
            result = client.get_rank_check_result(check["id"])
    assert prefs.check_notification_top_n == 10
    assert result.evidence_projection.recovery.reason == "retained evidence"
    assert result.result_completeness == "partial"


def test_warning_null_and_incomplete_warning_are_rejected():
    from bisibility import NotificationPreferencesUpdated

    for warnings in (None, [{"field": "check_in_app"}]):
        with pytest.raises(ValidationError):
            NotificationPreferencesUpdated.model_validate(
                {**FIXTURE["preferences"], "warnings": warnings}
            )
    assert (
        NotificationPreferencesUpdated.model_validate(
            {**FIXTURE["preferences"], "warnings": []}
        ).warnings
        == []
    )


@pytest.mark.parametrize("value", [0, 100, None])
def test_projection_depth_and_recovery_nulls(value):
    from bisibility import ProviderEvidenceProjection

    source = {
        **FIXTURE["projection"],
        "returned_depth": value,
        "recovery": dict.fromkeys(FIXTURE["projection"]["recovery"]),
    }
    result = ProviderEvidenceProjection.model_validate(source)
    assert result.returned_depth == value
    assert result.recovery.model_dump() == source["recovery"]
    assert result.model_dump() == source
    for field in source["recovery"]:
        broken = {**source, "recovery": {k: v for k, v in source["recovery"].items() if k != field}}
        with pytest.raises(ValidationError):
            ProviderEvidenceProjection.model_validate(broken)


@pytest.mark.parametrize("check_id", [None, "invalid", "kw_a00000000000000000000000"])
def test_run_projection_rejects_invalid_check_id(check_id):
    from bisibility import RankCheckRunEvidenceProjection

    with pytest.raises(ValidationError):
        RankCheckRunEvidenceProjection.model_validate(
            {**FIXTURE["projection"], "check_id": check_id}
        )
