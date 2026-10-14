from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from bisibility import AsyncBisibilityClient, BisibilityClient, BisibilityResponseError

FIXTURE = json.loads((Path(__file__).parent / "fixtures/rank-check-runs.json").read_text())
PROJECT = FIXTURE["detail"]["project_id"]
RUN = FIXTURE["detail"]["id"]


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("listed", [False, True])
def test_run_reads_roundtrip_and_only_get(asynchronous: bool, listed: bool) -> None:
    calls: list[httpx.Request] = []
    expected = FIXTURE["list" if listed else "detail"]

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=expected)

    kwargs = dict(
        api_key="bsb_pat_live_example",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    )
    options = {
        "segment": "planned", "status": "planned,blocked", "limit": 200, "cursor": FIXTURE["cursor"]
    }
    if asynchronous:

        async def scenario():
            async with AsyncBisibilityClient(**kwargs) as client:
                if listed:
                    return await client.list_rank_check_runs(PROJECT, options)
                return await client.get_rank_check_run(PROJECT, RUN)

        result = asyncio.run(scenario())
    else:
        with BisibilityClient(**kwargs) as client:
            result = (
                client.list_rank_check_runs(PROJECT, options)
                if listed
                else client.get_rank_check_run(PROJECT, RUN)
            )
    assert result.model_dump(mode="json") == expected
    assert len(calls) == 1
    request = calls[0]
    assert request.method == "GET"
    assert request.url.path == (
        f"/api/v1/projects/{PROJECT}/rank-check-runs" + ("" if listed else f"/{RUN}")
    )
    assert request.headers["Authorization"] == "Bearer bsb_pat_live_example"
    assert dict(request.url.params) == (
        {
            "segment": "planned", "status": "planned,blocked",
            "limit": "200", "cursor": FIXTURE["cursor"],
        } if listed else {}
    )


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "mutation", ["required_null", "foreign_id", "boolean_count", "negative_count", "terminal"]
)
def test_invalid_response_is_rejected(asynchronous: bool, mutation: str) -> None:
    raw = copy.deepcopy(FIXTURE["detail"])
    if mutation == "required_null":
        del raw["outcome"]
    elif mutation == "foreign_id":
        raw["id"] = PROJECT
    elif mutation == "boolean_count":
        raw["counts"]["cancelled"] = True
    elif mutation == "negative_count":
        raw["counts"]["cancelled"] = -1
    else:
        raw["terminal"] = "true"
    kwargs = dict(
        api_key="bsb_pat_live_example",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=raw)),
    )
    with pytest.raises(BisibilityResponseError):
        if asynchronous:

            async def scenario():
                async with AsyncBisibilityClient(**kwargs) as client:
                    await client.get_rank_check_run(PROJECT, RUN)

            asyncio.run(scenario())
        else:
            with BisibilityClient(**kwargs) as client:
                client.get_rank_check_run(PROJECT, RUN)


@pytest.mark.parametrize("listed", [False, True])
@pytest.mark.parametrize("invalid", ["raw-id", "kw_abcdefghijklmnopqrstuvwx"])
def test_invalid_identifiers_fail_before_http(listed: bool, invalid: str) -> None:
    calls: list[httpx.Request] = []
    with BisibilityClient(
        api_key="bsb_pat_live_example",
        transport=httpx.MockTransport(lambda request: calls.append(request)),
    ) as client:
        with pytest.raises(ValueError):
            if listed:
                client.list_rank_check_runs(invalid)
            else:
                client.get_rank_check_run(PROJECT, invalid)
    assert calls == []


@pytest.mark.parametrize(
    "options", [{"limit": 0}, {"limit": 201}, {"limit": True}, {"segment": "future"}]
)
def test_invalid_selection_fails_before_http(options: dict[str, object]) -> None:
    calls: list[httpx.Request] = []
    with BisibilityClient(
        api_key="bsb_pat_live_example",
        transport=httpx.MockTransport(lambda request: calls.append(request)),
    ) as client:
        with pytest.raises(ValidationError):
            client.list_rank_check_runs(PROJECT, options)
    assert calls == []


@pytest.mark.parametrize(
    "status,outcome,terminal,polling", [
        ("cancelled", None, True, "terminal"),
        ("completed", "deferred", True, "terminal"),
        ("blocked", None, False, "blocked"),
        ("future_status", "future_outcome", False, "future_polling"),
    ]
)
def test_no_check_required_and_future_metadata_preserved(
    status: str, outcome: str | None, terminal: bool, polling: str
) -> None:
    raw = copy.deepcopy(FIXTURE["detail"])
    raw.update(status=status, outcome=outcome, terminal=terminal, polling_state=polling)
    raw["future_field"] = {"value": 1}
    with BisibilityClient(
        api_key="bsb_pat_live_example",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=raw)),
    ) as client:
        assert client.get_rank_check_run(PROJECT, RUN).model_dump(mode="json") == raw


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "listed,field", [(False, "id"), (False, "project_id"), (True, "project_id")]
)
def test_run_response_is_bound_to_requested_scope(
    asynchronous: bool, listed: bool, field: str
) -> None:
    raw = copy.deepcopy(FIXTURE["list" if listed else "detail"])
    run = raw["data"][0] if listed else raw
    run[field] = ("prj_" if field == "project_id" else "rcr_") + "bbbbbbbbbbbbbbbbbbbbbbbb"
    kwargs = dict(
        api_key="bsb_pat_live_example",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=raw)),
    )
    with pytest.raises(BisibilityResponseError):
        if asynchronous:

            async def scenario():
                async with AsyncBisibilityClient(**kwargs) as client:
                    if listed:
                        await client.list_rank_check_runs(PROJECT)
                    else:
                        await client.get_rank_check_run(PROJECT, RUN)

            asyncio.run(scenario())
        else:
            with BisibilityClient(**kwargs) as client:
                if listed:
                    client.list_rank_check_runs(PROJECT)
                else:
                    client.get_rank_check_run(PROJECT, RUN)
