from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

import bisibility
from bisibility import (
    AnalyzeDomainOverviewOptions,
    AsyncBisibilityClient,
    BisibilityClient,
    BisibilityResponseError,
    DomainOverviewEstimate,
    DomainOverviewReport,
    LoadDomainOverviewHistoryOptions,
    LoadDomainOverviewKeywordsOptions,
    LoadDomainOverviewPagesOptions,
)

API_KEY = "bsb_key_live_1234567890abcdef"
PROJECT_ID = "prj_a00000000000000000000000"


class QueueTransport:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json=self.responses.pop(0), request=request)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


def make_client(queue: QueueTransport) -> BisibilityClient:
    return BisibilityClient(
        api_key=API_KEY,
        base_url="https://api.test/api/v1",
        transport=queue.transport(),
    )


def request_json(request: httpx.Request) -> dict[str, Any]:
    value = httpx.Response(200, request=request, content=request.content).json()
    assert isinstance(value, dict)
    return value


def metrics(**overrides: Any) -> dict[str, Any]:
    return {
        "count": 142,
        "estimated_traffic_cost_cents": 9812.37,
        "etv": 1413.3,
        "is_down": 12,
        "is_lost": 4,
        "is_new": 8,
        "is_up": 15,
        "pos1": 3,
        "pos2_3": 7,
        "pos4_10": 13,
        "pos11_20": 21,
        "pos21_30": 18,
        "pos31_40": 16,
        "pos41_50": 14,
        "pos51_60": 12,
        "pos61_70": 11,
        "pos71_80": 10,
        "pos81_90": 9,
        "pos91_100": 8,
        **overrides,
    }


def keyword_page() -> dict[str, Any]:
    return {
        "cost_cents": 2,
        "rows": [
            {
                "cpc_cents": 175.5,
                "difficulty": 42,
                "estimated_traffic": 84.2,
                "intent": "commercial",
                "keyword": "rank tracker",
                "position": 3,
                "rank_absolute": 5,
                "rank_absolute_delta": 2,
                "ranking_url": "https://example.com/rank-tracker",
                "search_volume": 1900,
                "serp_features": ["people_also_ask"],
            }
        ],
        "total_count": 938,
    }


def pages() -> dict[str, Any]:
    return {
        "cost_cents": 2,
        "rows": [
            {
                "etv": 142.065,
                "etv_delta_pct": None,
                "keyword_count": 22,
                "path": "/rank-tracker",
                "top_keyword": None,
                "top_keyword_position": None,
            }
        ],
        "total_count": 225,
    }


def estimate() -> dict[str, Any]:
    return {
        "cached": False,
        "estimate": True,
        "estimated_cost_cents": 6,
        "fresh_estimated_cost_cents": 8,
        "history_estimated_cost_cents": 12,
        "history_mode": "lazy",
        "keyword_page_estimated_cost_cents": 2,
        "language_code": "en",
        "location_code": 2840,
        "page_page_estimated_cost_cents": 2,
        "provider": "dataforseo",
        "scope": "root",
        "target": "example.com",
    }


def report() -> dict[str, Any]:
    return {
        "cached": False,
        "cached_until": "2026-08-13T18:00:00Z",
        "cost_cents": 6,
        "fetched_at": "2026-08-13T06:00:00Z",
        "history_mode": "lazy",
        "keywords": {
            "cached": False,
            "cost_cents": 2,
            "data": keyword_page(),
            "fetched_at": "2026-08-13T06:00:00Z",
            "ok": True,
        },
        "language_code": "en",
        "location_code": 2840,
        "overview": metrics(),
        "pages": {
            "cost_cents": 1.5,
            "ok": False,
            "reason": "rate_limited",
            "reset_at": 1_775_000_000_000,
        },
        "previous_fetched_at": "2026-08-06T06:00:00Z",
        "previous_overview": metrics(count=130),
        "previous_source_snapshot_at": "2026-08-05T00:00:00Z",
        "provider": "dataforseo",
        "scope": "root",
        "source_snapshot_at": "2026-08-12T00:00:00Z",
        "state": "partial",
        "target": "example.com",
    }


def test_analyze_domain_overview_posts_complete_snake_case_body_and_validates_report() -> None:
    queue = QueueTransport([{"data": report()}])
    client = make_client(queue)

    result = client.analyze_domain_overview(
        PROJECT_ID,
        AnalyzeDomainOverviewOptions(
            target="example.com",
            location_code=2840,
            language_code="en",
            scope_override="root",
            fresh=True,
            max_cost_cents=8,
            estimate_only=False,
            keyword_limit=100,
            page_limit=500,
        ),
    )

    assert isinstance(result.data, DomainOverviewReport)
    assert result.data.overview is not None
    assert result.data.overview.pos2_3 == 7
    assert result.data.overview.estimated_traffic_cost_cents == 9812.37
    assert result.data.keywords.ok is True
    assert result.data.keywords.data.rows[0].serp_features == ["people_also_ask"]
    assert result.data.pages.ok is False
    assert result.data.pages.reason == "rate_limited"
    request = queue.requests[0]
    assert request.method == "POST"
    assert request.url.path.endswith(f"/projects/{PROJECT_ID}/domain-overview/analyze")
    assert request_json(request) == {
        "estimate_only": False,
        "fresh": True,
        "keyword_limit": 100,
        "language_code": "en",
        "location_code": 2840,
        "max_cost_cents": 8,
        "page_limit": 500,
        "scope_override": "root",
        "target": "example.com",
    }


def test_analyze_domain_overview_minimal_request_omits_unset_fields_and_decodes_estimate() -> None:
    queue = QueueTransport([{"data": estimate()}])
    client = make_client(queue)

    result = client.analyze_domain_overview(
        PROJECT_ID,
        {
            "target": "example.com",
            "location_code": 2840,
            "language_code": "en",
            "estimate_only": True,
        },
    )

    assert isinstance(result.data, DomainOverviewEstimate)
    assert result.data.fresh_estimated_cost_cents == 8
    assert request_json(queue.requests[0]) == {
        "estimate_only": True,
        "language_code": "en",
        "location_code": 2840,
        "target": "example.com",
    }


def test_domain_overview_option_models_are_strict_and_allow_explicit_zero_cap() -> None:
    options = LoadDomainOverviewHistoryOptions(
        target="example.com",
        location_code=2840,
        language_code="en",
        max_cost_cents=0,
    )
    assert options.max_cost_cents == 0
    with pytest.raises(ValidationError):
        AnalyzeDomainOverviewOptions.model_validate(
            {
                "target": "example.com",
                "location_code": 2840,
                "language_code": "en",
                "unexpected": True,
            }
        )
    with pytest.raises(ValidationError, match="max_cost_cents is required"):
        AnalyzeDomainOverviewOptions(
            target="example.com",
            location_code=2840,
            language_code="en",
        )


def test_domain_overview_minimal_history_request_omits_optional_fields() -> None:
    queue = QueueTransport(
        [
            {
                "data": {
                    "cached": True,
                    "cost_cents": 0,
                    "data": [],
                    "fetched_at": "2026-08-13T06:00:00Z",
                }
            }
        ]
    )
    make_client(queue).load_domain_overview_history(
        PROJECT_ID,
        LoadDomainOverviewHistoryOptions(
            target="example.com",
            location_code=2840,
            language_code="en",
            max_cost_cents=0,
        ),
    )
    assert request_json(queue.requests[0]) == {
        "language_code": "en",
        "location_code": 2840,
        "max_cost_cents": 0,
        "target": "example.com",
    }


@pytest.mark.parametrize(
    ("call", "suffix", "body", "response", "assertion"),
    [
        (
            lambda client, value: client.load_domain_overview_history(PROJECT_ID, value),
            "history",
            LoadDomainOverviewHistoryOptions(
                target="example.com",
                location_code=2840,
                language_code="en",
                scope_override="root",
                fresh=True,
                max_cost_cents=12,
            ),
            {
                "cached": False,
                "cost_cents": 12,
                "data": [{"year": 2026, "month": 7, "metrics": metrics()}],
                "fetched_at": "2026-08-13T06:00:00Z",
            },
            lambda data: data.data[0].metrics.pos1 == 3,
        ),
        (
            lambda client, value: client.load_domain_overview_keywords(PROJECT_ID, value),
            "keywords",
            LoadDomainOverviewKeywordsOptions(
                target="example.com",
                location_code=2840,
                language_code="en",
                scope_override="subdomain",
                fresh=True,
                max_cost_cents=2,
                limit=100,
                offset=200,
            ),
            {
                "cached": False,
                "cost_cents": 2,
                "data": keyword_page(),
                "fetched_at": "2026-08-13T06:00:00Z",
            },
            lambda data: data.data.rows[0].rank_absolute_delta == 2,
        ),
        (
            lambda client, value: client.load_domain_overview_pages(PROJECT_ID, value),
            "pages",
            LoadDomainOverviewPagesOptions(
                target="example.com",
                location_code=2840,
                language_code="en",
                scope_override="root",
                fresh=False,
                max_cost_cents=0,
                limit=500,
                offset=1000,
            ),
            {
                "cached": True,
                "cost_cents": 0,
                "data": pages(),
                "fetched_at": "2026-08-13T06:00:00Z",
            },
            lambda data: data.data.rows[0].path == "/rank-tracker",
        ),
    ],
)
def test_domain_overview_module_operations_post_validated_bodies(
    call: Callable[[BisibilityClient, Any], Any],
    suffix: str,
    body: Any,
    response: dict[str, Any],
    assertion: Callable[[Any], bool],
) -> None:
    queue = QueueTransport([{"data": response}])
    result = call(make_client(queue), body)

    assert assertion(result.data)
    request = queue.requests[0]
    assert request.method == "POST"
    assert request.url.path.endswith(f"/domain-overview/{suffix}")
    assert request_json(request) == body.model_dump(exclude_none=True, exclude_unset=True)


def test_domain_overview_nested_response_validation_rejects_invalid_history_month() -> None:
    queue = QueueTransport(
        [
            {
                "data": {
                    "cached": False,
                    "cost_cents": 12,
                    "data": [{"year": 2026, "month": 13, "metrics": metrics()}],
                    "fetched_at": "2026-08-13T06:00:00Z",
                }
            }
        ]
    )

    with pytest.raises(BisibilityResponseError):
        make_client(queue).load_domain_overview_history(
            PROJECT_ID,
            LoadDomainOverviewHistoryOptions(
                target="example.com",
                location_code=2840,
                language_code="en",
                max_cost_cents=12,
            ),
        )


def test_domain_overview_sync_and_async_methods_are_exported_and_awaitable() -> None:
    method_names = {
        "analyze_domain_overview",
        "load_domain_overview_history",
        "load_domain_overview_keywords",
        "load_domain_overview_pages",
    }
    for name in method_names:
        assert callable(getattr(BisibilityClient, name))
        assert inspect.iscoroutinefunction(getattr(AsyncBisibilityClient, name))

    assert {
        "AnalyzeDomainOverviewOptions",
        "DomainOverviewEstimate",
        "DomainOverviewHistoricalRow",
        "DomainOverviewModuleFailure",
        "DomainOverviewModuleResult",
        "DomainOverviewModuleSuccess",
        "DomainOverviewRankedKeyword",
        "DomainOverviewRankedKeywordsPage",
        "DomainOverviewRelevantPage",
        "DomainOverviewRelevantPages",
        "DomainOverviewReport",
        "DomainRankMetrics",
        "LoadDomainOverviewHistoryOptions",
        "LoadDomainOverviewKeywordsOptions",
        "LoadDomainOverviewPagesOptions",
    } <= set(bisibility.__all__)

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": estimate()}, request=request)

    async def scenario() -> None:
        async with AsyncBisibilityClient(
            api_key=API_KEY,
            base_url="https://api.test/api/v1",
            transport=httpx.MockTransport(handler),
        ) as client:
            result = await client.analyze_domain_overview(
                PROJECT_ID,
                AnalyzeDomainOverviewOptions(
                    target="example.com",
                    location_code=2840,
                    language_code="en",
                    estimate_only=True,
                ),
            )
            assert isinstance(result.data, DomainOverviewEstimate)

    asyncio.run(scenario())
    assert requests[0].method == "POST"


def test_domain_overview_estimated_traffic_cost_cents_fraction_survives_async_decoding() -> None:
    async def scenario() -> None:
        async with AsyncBisibilityClient(
            api_key=API_KEY,
            base_url="https://api.test/api/v1",
            transport=httpx.MockTransport(handler),
        ) as client:
            result = await client.analyze_domain_overview(
                PROJECT_ID,
                AnalyzeDomainOverviewOptions(
                    target="example.com",
                    location_code=2840,
                    language_code="en",
                    scope_override="root",
                    fresh=True,
                    max_cost_cents=8,
                    estimate_only=False,
                    keyword_limit=100,
                    page_limit=500,
                ),
            )
            assert isinstance(result.data, DomainOverviewReport)
            assert result.data.overview is not None
            assert result.data.overview.estimated_traffic_cost_cents == 9812.37

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": report()}, request=request)

    asyncio.run(scenario())
