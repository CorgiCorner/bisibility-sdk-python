from __future__ import annotations

import asyncio
import inspect
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from bisibility import (
    AsyncBisibilityClient,
    BisibilityApiError,
    BisibilityClient,
    BisibilityNetworkError,
    BisibilityResponseError,
    create_async_bisibility_client,
)

API_KEY = "bsb_key_live_1234567890abcdef"


def project(project_id: str = "prj_a00000000000000000000000") -> dict[str, Any]:
    return {
        "created_at": "2026-01-01T00:00:00.000Z",
        "domain": "example.com",
        "id": project_id,
        "name": "Example",
        "updated_at": "2026-01-02T00:00:00.000Z",
        "write_mode": "active",
    }


def keyword(keyword_id: str) -> dict[str, Any]:
    return {
        "country": "United States",
        "created_at": "2026-01-01T00:00:00.000Z",
        "device": "desktop",
        "id": keyword_id,
        "intent": None,
        "latest_position": 4,
        "location": "United States",
        "previous_position": None,
        "project_id": "prj_a00000000000000000000000",
        "ranking_url": "https://example.com/page",
        "schedule": None,
        "tags": ["Product"],
        "target_url": "https://example.com/page",
        "text": "rank tracker api",
        "topic": None,
        "updated_at": "2026-01-02T00:00:00.000Z",
    }


def public_methods(client_type: type[object]) -> set[str]:
    return {
        name
        for name, value in inspect.getmembers(client_type, inspect.isfunction)
        if not name.startswith("_")
    }


def test_async_client_has_full_sync_surface_and_matching_parameters() -> None:
    sync_methods = public_methods(BisibilityClient)
    async_methods = public_methods(AsyncBisibilityClient)

    assert async_methods == sync_methods | {"aclose"}
    for name in sync_methods - {"close"}:
        async_method = getattr(AsyncBisibilityClient, name)
        sync_method = getattr(BisibilityClient, name)
        assert inspect.iscoroutinefunction(async_method) or inspect.isasyncgenfunction(async_method)
        assert list(inspect.signature(async_method).parameters.values()) == list(
            inspect.signature(sync_method).parameters.values()
        )


def test_async_factory_request_headers_timeout_and_owned_lifecycle() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": [project()], "meta": {"next_cursor": None}})

    async def scenario() -> None:
        client = create_async_bisibility_client(
            api_key=API_KEY,
            project_id="prj_a00000000000000000000000",
            base_url="https://api.example.com/api/v1",
            timeout=30.0,
            transport=httpx.MockTransport(handler),
        )
        async with client as entered:
            response = await entered.list_projects()
            assert response.data[0].name == "Example"
        assert client._client.is_closed

    asyncio.run(scenario())
    request = requests[0]
    assert request.headers["Authorization"] == f"Bearer {API_KEY}"
    assert request.headers["X-Bisibility-Project"] == "prj_a00000000000000000000000"
    assert request.headers["X-Bisibility-Client"].startswith("bisibility-sdk-python/")
    assert request.extensions["timeout"] == {
        "connect": 30.0,
        "pool": 30.0,
        "read": 30.0,
        "write": 30.0,
    }


def test_async_iterator_preserves_filters_across_cursor_pages() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        cursor = request.url.params.get("cursor")
        suffix = "b" if cursor else "a"
        return httpx.Response(
            200,
            json={
                "data": [keyword(f"kw_{suffix}{'0' * 23}")],
                "meta": {"next_cursor": "eyJ2IjozLCJvIjoxfQ" if cursor is None else None},
            },
        )

    async def scenario() -> list[str]:
        async with AsyncBisibilityClient(
            api_key=API_KEY,
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(handler),
        ) as client:
            return [
                item.id
                async for item in client.iter_keywords(
                    "prj_a00000000000000000000000",
                    {"limit": 7, "tag": "Product"},
                )
            ]

    assert asyncio.run(scenario()) == [
        "kw_a00000000000000000000000",
        "kw_b00000000000000000000000",
    ]
    assert [request.url.params.get("filter[tag]") for request in requests] == [
        "Product",
        "Product",
    ]
    assert [request.url.params.get("limit") for request in requests] == ["7", "7"]
    assert [request.url.params.get("cursor") for request in requests] == [
        None,
        "eyJ2IjozLCJvIjoxfQ",
    ]


def test_async_retries_use_non_blocking_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"detail": "retry"})
        return httpx.Response(200, json={"data": [project()], "meta": {"next_cursor": None}})

    sleep = AsyncMock()
    monkeypatch.setattr("bisibility.async_client.asyncio.sleep", sleep)

    async def scenario() -> None:
        async with AsyncBisibilityClient(
            api_key=API_KEY,
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(handler),
        ) as client:
            await client.list_projects()

    asyncio.run(scenario())
    assert attempts == 2
    sleep.assert_awaited_once_with(0.5)


def test_async_readiness_returns_degraded_503_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, json={"status": "degraded"})

    sleep = AsyncMock()
    monkeypatch.setattr("bisibility.async_client.asyncio.sleep", sleep)

    async def scenario() -> None:
        async with AsyncBisibilityClient(
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(handler),
        ) as client:
            response = await client.get_readiness()
            assert response.status == "degraded"

    asyncio.run(scenario())
    assert attempts == 1
    sleep.assert_not_awaited()


def test_async_request_cancellation_is_not_retried() -> None:
    attempts = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    async def scenario() -> None:
        async with AsyncBisibilityClient(
            api_key=API_KEY,
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(handler),
        ) as client:
            task = asyncio.create_task(client.list_projects())
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    asyncio.run(scenario())
    assert attempts == 1


def test_async_client_preserves_error_contracts() -> None:
    async def api_error() -> None:
        async with AsyncBisibilityClient(
            api_key=API_KEY,
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    400,
                    headers={"Content-Type": "application/problem+json"},
                    json={
                        "detail": "Project selection is ambiguous.",
                        "status": 400,
                        "title": "Bad Request",
                        "type": "https://example.com/problems/project-selection",
                    },
                )
            ),
        ) as client:
            with pytest.raises(BisibilityApiError) as raised:
                await client.list_projects()
            assert raised.value.status == 400
            assert raised.value.problem is not None
            assert raised.value.problem.detail == "Project selection is ambiguous."

    async def invalid_json() -> None:
        async with AsyncBisibilityClient(
            api_key=API_KEY,
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200,
                    headers={"Content-Type": "application/json"},
                    text="not json",
                )
            ),
        ) as client:
            with pytest.raises(BisibilityResponseError):
                await client.list_projects()

    async def network_error() -> None:
        def fail(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline", request=request)

        async with AsyncBisibilityClient(
            api_key=API_KEY,
            base_url="https://api.example.com/api/v1",
            max_retries=0,
            transport=httpx.MockTransport(fail),
        ) as client:
            with pytest.raises(BisibilityNetworkError):
                await client.list_projects()

    asyncio.run(api_error())
    asyncio.run(invalid_json())
    asyncio.run(network_error())


def test_async_client_does_not_close_injected_http_client() -> None:
    async def scenario() -> None:
        http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200, json={"data": [project()], "meta": {"next_cursor": None}}
                )
            )
        )
        client = AsyncBisibilityClient(api_key=API_KEY, http_client=http_client)
        await client.list_projects()
        await client.aclose()
        assert not http_client.is_closed
        await http_client.aclose()

    asyncio.run(scenario())
