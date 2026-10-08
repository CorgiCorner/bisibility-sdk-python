from __future__ import annotations

import asyncio
import base64
import inspect
import json
from typing import Any

import httpx
import pytest

from bisibility import (
    AsyncBisibilityClient,
    BisibilityApiError,
    BisibilityClient,
    BisibilityResponseError,
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


RESEARCH_FIXTURES = {
    "report": {
        "id": "agr_a00000000000000000000000",
        "kind": "external_review",
        "title": "Review",
        "created_at": "2026-10-07T00:00:00Z",
        "body": {"CamelCase": {"keyword_id": "producer-defined"}},
        "provenance": {"SourceUrl": "https://example.org/source"},
    },
    "summary": {
        "id": "agr_a00000000000000000000000",
        "kind": "external_review",
        "title": "Review",
        "created_at": "2026-10-07T00:00:00Z",
    },
    "context": {
        "business": "Example",
        "audience": "Developers",
        "products": "API",
        "goals": "Quality",
        "agent_rules": "Use sources",
        "updated_at": None,
    },
    "site": {
        "id": "agr_a00000000000000000000000",
        "created_at": "2026-10-07T00:00:00Z",
        "cached": False,
        "result": {
            "version": 1,
            "target": "https://example.com",
            "started_at": "2026-10-07T00:00:00Z",
            "completed_at": "2026-10-07T00:00:00Z",
            "state": "complete",
            "stop_reason": "finished",
            "limits": {
                "max_pages": 10,
                "max_requests": 20,
                "max_duration_ms": 1000,
                "max_page_bytes": 1048576,
            },
            "requests": 1,
            "pages": [
                {
                    "url": "https://example.com",
                    "final_url": "https://example.com",
                    "status": 200,
                    "response_time_ms": 1,
                    "title": "Example",
                    "description": None,
                    "canonical": None,
                    "headings": [{"level": 1, "text": "Example"}],
                    "h1_count": 1,
                    "indexable": True,
                    "robots": None,
                    "internal_link_count": 0,
                    "external_link_count": 0,
                    "internal_links": [],
                    "image_count": 0,
                    "missing_alt_count": 0,
                    "issues": [
                        {
                            "code": "description_missing",
                            "message": "Missing description",
                            "severity": "warning",
                        }
                    ],
                }
            ],
            "summary": {"pages": 1, "errors": 0, "warnings": 1, "indexable": 1},
            "limitations": ["Bounded crawl"],
        },
    },
    "estimate": {
        "ok": True,
        "estimate": True,
        "estimated_cost_cents": 1.25,
        "evidence": "observed_dataset",
    },
    "ai": {
        "ok": True,
        "estimate": False,
        "cached": False,
        "report_id": "agr_a00000000000000000000000",
        "cost_cents": 1.25,
        "result": {
            "evidence": "synthetic_prompt_test",
            "rows": [
                {
                    "prompt": "Example",
                    "model": "gpt-4.1-mini",
                    "answer": "Example API",
                    "observed_at": None,
                    "brand_mentioned": True,
                    "domain_cited": True,
                    "citations": [
                        {"title": "Example", "url": "https://example.com", "target_domain": True}
                    ],
                    "content_truncated": False,
                }
            ],
            "total_available": None,
            "truncated": False,
            "fetched_at": "2026-10-07T00:00:00Z",
            "cost_cents": 1.25,
            "cost_status": "confirmed",
            "failure": None,
        },
    },
}


@pytest.mark.parametrize(
    "name,method,suffix,body,fixture",
    [
        ("get_project_context", "GET", "context", None, "context"),
        (
            "update_project_context",
            "PATCH",
            "context",
            {k: v for k, v in RESEARCH_FIXTURES["context"].items() if k != "updated_at"},
            "context",
        ),
        ("list_agent_reports", "GET", "agent-reports", None, "summary"),
        (
            "create_agent_report",
            "POST",
            "agent-reports",
            {k: v for k, v in RESEARCH_FIXTURES["report"].items() if k not in ("id", "created_at")},
            "report",
        ),
        ("get_agent_report", "GET", "agent-reports/agr_a00000000000000000000000", None, "report"),
        ("list_site_audits", "GET", "site-audits", None, "summary"),
        ("run_site_audit", "POST", "site-audits", {"max_pages": 2}, "site"),
        ("get_site_audit", "GET", "site-audits/agr_a00000000000000000000000", None, "site"),
        (
            "analyze_ai_visibility",
            "POST",
            "ai-visibility",
            {
                "brand": "Example",
                "domain": "example.com",
                "max_cost_cents": 0,
                "estimate_only": True,
            },
            "estimate",
        ),
        (
            "compare_ai_prompts",
            "POST",
            "prompt-explorer",
            {
                "brand": "Example",
                "domain": "example.com",
                "max_cost_cents": 2,
                "prompt": "Example",
                "models": ["gpt-4.1-mini"],
            },
            "ai",
        ),
    ],
)
def test_research_workspace_operations(name, method, suffix, body, fixture):
    requests = []
    payload = RESEARCH_FIXTURES[fixture]
    response = {"data": [payload] if name.startswith("list_") else payload}
    if name == "list_agent_reports":
        response["meta"] = {"next_cursor": None}

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=response)

    with BisibilityClient(
        api_key="bsb_key_test_example",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    ) as client:
        args = ["prj_a00000000000000000000000"]
        if name.startswith("get_") and fixture in ("report", "site"):
            args.append("agr_a00000000000000000000000")
        if body is not None:
            args.append(body)
        result = getattr(client, name)(*args)
        item = result.data[0] if name.startswith("list_") else result.data
        assert item.model_dump(exclude_unset=True) == payload
    assert len(requests) == 1
    assert requests[0].method == method
    assert requests[0].url.path == "/api/v1/projects/prj_a00000000000000000000000/" + suffix
    if body is not None:
        assert json.loads(requests[0].content) == body


@pytest.mark.parametrize(
    "name,args",
    [
        ("get_agent_report", ["prj_a00000000000000000000000", "kw_a00000000000000000000000"]),
        ("get_site_audit", ["prj_a00000000000000000000000", "raw"]),
        ("run_site_audit", ["prj_a00000000000000000000000", {"max_pages": 16}]),
        (
            "create_agent_report",
            ["prj_a00000000000000000000000", {"kind": "site_audit", "title": "Title", "body": {}}],
        ),
        (
            "analyze_ai_visibility",
            [
                "prj_a00000000000000000000000",
                {"brand": "Example", "domain": "example.com", "max_cost_cents": -1},
            ],
        ),
    ],
)
def test_research_workspace_rejects_invalid_input_before_transport(name, args):
    def handler(request):
        raise AssertionError("invalid input reached transport")

    with BisibilityClient(
        api_key="bsb_key_test_example",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(ValueError):
            getattr(client, name)(*args)


def test_research_workspace_rejects_incomplete_ai_report():
    def handler(request):
        return httpx.Response(200, json={"data": {"ok": True, "estimate": False, "cached": False}})

    with BisibilityClient(
        api_key="bsb_key_test_example",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(BisibilityResponseError):
            client.analyze_ai_visibility(
                "prj_a00000000000000000000000",
                {"brand": "Example", "domain": "example.com", "max_cost_cents": 0},
            )


@pytest.mark.parametrize("async_mode", [False, True])
def test_agent_report_cursor_iterator_preserves_filters(async_mode: bool) -> None:
    cursor = (
        base64.urlsafe_b64encode(
            json.dumps(
                {
                    "v": 3,
                    "public_id": "agr_a00000000000000000000000",
                    "t": "2026-10-07T00:00:00Z",
                }
            ).encode()
        )
        .decode()
        .rstrip("=")
    )
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": [RESEARCH_FIXTURES["summary"]],
                "meta": {"next_cursor": cursor if len(requests) == 1 else None},
            },
        )

    async def scenario():
        client = (AsyncBisibilityClient if async_mode else BisibilityClient)(
            api_key="bsb_key_test_example",
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(handler),
        )
        try:
            iterator = client.iter_agent_reports(PROJECT, {"kind": "external_review", "limit": 1})
            reports = [report async for report in iterator] if async_mode else list(iterator)
            assert len(reports) == 2
        finally:
            result = client.close()
            if inspect.isawaitable(result):
                await result

    asyncio.run(scenario())
    assert [r.url.params["kind"] for r in requests] == ["external_review"] * 2
    assert [r.url.params["limit"] for r in requests] == ["1"] * 2
    assert "cursor" not in requests[0].url.params
    assert requests[1].url.params["cursor"] == cursor
