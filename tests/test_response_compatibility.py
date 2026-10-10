from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bisibility import (
    AnalyzeBacklinksOptions,
    BacklinksSnapshot,
    BisibilityApiError,
    Keyword,
    RankCheck,
)
from test_client import QueueTransport, json_response, make_client

FIXTURE = json.loads((Path(__file__).parent / "fixtures/response-compatibility.json").read_text())


def test_partial_backlinks_from_application_is_a_typed_success() -> None:
    queue = QueueTransport([json_response(FIXTURE["partial_backlinks"]["body"])])
    with make_client(queue) as client:
        response = client.analyze_backlinks(
            "prj_a00000000000000000000000", AnalyzeBacklinksOptions(target="example.com")
        )
    snapshot = response.data
    assert isinstance(snapshot, BacklinksSnapshot)
    assert snapshot.history_unavailable is True
    assert snapshot.history == []
    assert snapshot.summary.backlinks_total == 12
    assert snapshot.cost_cents == 0.3
    assert snapshot.model_dump()["history_unavailable"] is True


def test_normal_history_remains_exactly_twelve_months() -> None:
    normal = FIXTURE["full_backlinks"]["body"]["data"]
    assert len(BacklinksSnapshot.model_validate(normal).history) == 12
    assert BacklinksSnapshot.model_validate(normal).history_unavailable is False
    for history in ([], normal["history"][1:], [*normal["history"], normal["history"][0]]):
        with pytest.raises(ValidationError):
            BacklinksSnapshot.model_validate({**normal, "history": history})
    with pytest.raises(ValidationError):
        BacklinksSnapshot.model_validate({**normal, "history": [], "history_unavailable": False})
    with pytest.raises(ValidationError):
        BacklinksSnapshot.model_validate({**normal, "history_unavailable": True})


def test_page_scope_does_not_request_history() -> None:
    snapshot = BacklinksSnapshot.model_validate(FIXTURE["page_backlinks"]["body"]["data"])
    assert snapshot.history == []
    assert snapshot.history_unavailable is False


def test_coverage_and_latest_checks_are_typed_without_inferring_absence() -> None:
    for observation in FIXTURE["ranks"]:
        source = observation["check"]
        queue = QueueTransport([json_response(source), json_response(observation["keyword"])])
        with make_client(queue) as client:
            check = client.get_rank_check_result(source["id"])
            keyword = client.get_keyword(observation["keyword"]["id"])
        assert check.observation_completeness == source["observation_completeness"]
        assert check.position == source["position"]
        assert keyword.latest_check is not None
        assert keyword.latest_successful_check is not None
        assert keyword.latest_check.observation_completeness == check.observation_completeness
        assert keyword.latest_successful_check.position == check.position
        assert "observation_completeness" not in (check.model_extra or {})
        assert "latest_check" not in (keyword.model_extra or {})
    failed = Keyword.model_validate(FIXTURE["failed_keyword"])
    assert failed.latest_position is None
    assert failed.latest_check is not None and failed.latest_check.status == "failed"
    assert failed.latest_successful_check is not None
    assert failed.latest_successful_check.position == 6
    assert failed.latest_successful_check.observation_completeness == "truncated_by_stop_on_match"
    legacy = {**FIXTURE["ranks"][0]["check"]}
    legacy.pop("observation_completeness")
    assert RankCheck.model_validate(legacy).observation_completeness is None
    unobserved = Keyword.model_validate(FIXTURE["unobserved_keyword"])
    assert unobserved.latest_check is None
    assert unobserved.latest_successful_check is None
    assert unobserved.latest_position is None


def test_failed_summary_stays_an_error_with_unknown_total() -> None:
    source = FIXTURE["failed_summary"]
    queue = QueueTransport([json_response(source["body"], source["status"])])
    with make_client(queue) as client, pytest.raises(BisibilityApiError) as raised:
        client.analyze_backlinks(
            "prj_a00000000000000000000000", AnalyzeBacklinksOptions(target="example.com")
        )
    error = raised.value
    assert error.status == 500
    assert error.problem is not None
    assert error.problem.model_dump()["details"] == source["body"]["details"]
    assert source["body"]["details"]["cost_cents"] is None
    assert source["body"]["details"]["known_summary_cost_cents"] == 0.2
