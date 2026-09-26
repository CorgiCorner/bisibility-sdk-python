from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

import httpx
import pytest

from bisibility import (
    AsyncBisibilityClient,
    BisibilityApiError,
    BisibilityClient,
    ProviderBudgetsUpdate,
)

PROJECT = "prj_a00000000000000000000000"
BUDGET = {
    "connection_id": "conn_a00000000000000000000000",
    "provider": "dataforseo",
    "credential_source": "own",
    "source": "connection",
    "own": {"app": None, "programmatic": None},
    "credits": {"app": None, "programmatic": None},
}


@pytest.mark.parametrize("async_mode", [False, True])
def test_reports_and_budget_requests_preserve_selection_and_null(async_mode: bool) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "PATCH":
            return httpx.Response(200, json=BUDGET)
        if request.url.path.endswith("/provider-budgets"):
            return httpx.Response(200, json={"data": [BUDGET], "meta": {"next_cursor": None}})
        return httpx.Response(200, json={"data": [], "meta": {"freshness_days": 30}})

    async def run() -> None:
        client: Any = (AsyncBisibilityClient if async_mode else BisibilityClient)(
            api_key="bsb_key_test_x",
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(handler),
        )

        async def call(value: Any) -> Any:
            return await value if inspect.isawaitable(value) else value

        try:
            result = await call(client.list_stored_research_reports(PROJECT))
            assert result.meta.freshness_days == 30
            result = await call(client.list_provider_budgets(PROJECT))
            assert result.data[0].credential_source == "own"
            await call(
                client.update_provider_budgets(
                    PROJECT,
                    "dataforseo",
                    ProviderBudgetsUpdate.model_validate(
                        {
                            "own": {"app": None},
                            "credits": {"programmatic": {"unit": "cents", "amount_per_month": 123}},
                        }
                    ),
                )
            )
        finally:
            await call(client.close())

    asyncio.run(run())
    assert [r.method for r in requests] == ["GET", "GET", "PATCH"]
    assert json.loads(requests[-1].content) == {
        "own": {"app": None},
        "credits": {"programmatic": {"unit": "cents", "amount_per_month": 123}},
    }


@pytest.mark.parametrize("async_mode", [False, True])
def test_missing_report_never_falls_back_to_provider(async_mode: bool) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(404, json={"status": 404, "title": "Not found"})

    async def run() -> None:
        client: Any = (AsyncBisibilityClient if async_mode else BisibilityClient)(
            api_key="bsb_key_test_x",
            base_url="https://api.example.com/api/v1",
            max_retries=0,
            transport=httpx.MockTransport(handler),
        )
        try:
            with pytest.raises(BisibilityApiError):
                result = client.get_stored_research_report(
                    PROJECT,
                    "backlinks",
                    {"target": "example.com", "include_subdomains": False, "location_code": 0},
                )
                if inspect.isawaitable(result):
                    await result
        finally:
            result = client.close()
            if inspect.isawaitable(result):
                await result

    asyncio.run(run())
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].url.params["include_subdomains"] == "false"
    assert requests[0].url.params["location_code"] == "0"


@pytest.mark.parametrize("kind", ["backlinks", "domain_overview", "keyword_research"])
def test_reads_typed_stored_report(kind: str) -> None:
    from pathlib import Path

    from bisibility import StoredResearchReportResponse

    fixtures = json.loads((Path(__file__).parent / "fixtures/stored_reports.json").read_text())
    response = StoredResearchReportResponse.model_validate({"data": fixtures[kind]})
    assert response.data.state == "fresh"
    assert response.data.fresh_until
    if kind == "domain_overview":
        assert response.data.data_state == "no_data"
