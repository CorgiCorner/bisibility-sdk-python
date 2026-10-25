from __future__ import annotations

import asyncio
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from bisibility import (
    AsyncBisibilityClient,
    BisibilityApiError,
    BisibilityClient,
    BisibilityResponseError,
)

FIXTURE = json.loads((Path(__file__).parent / "fixtures/page-indexing.json").read_text())
PROJECT = "prj_a00000000000000000000000"
METHODS = {
    "getPageIndexingReport": ("get_page_indexing_report", (PROJECT,)),
    "listPageIndexingUrls": ("list_page_indexing_urls", (PROJECT,)),
    "getPageIndexingSettings": ("get_page_indexing_settings", (PROJECT,)),
    "updatePageIndexingSettings": (
        "update_page_indexing_settings",
        (PROJECT, {"budget_mode": "fixed"}),
    ),
}


def invoke(asynchronous, transport, method, args, request_options=None):
    kwargs = {
        "api_key": "bsb_pat_live_example",
        "transport": transport,
        "max_retries": 2,
        "base_url": "https://api.example.com/api/v1",
    }
    if asynchronous:

        async def scenario():
            async with AsyncBisibilityClient(**kwargs) as client:
                return await getattr(client, method)(*args, request_options=request_options)

        return asyncio.run(scenario())
    with BisibilityClient(**kwargs) as client:
        return getattr(client, method)(*args, request_options=request_options)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("capture", FIXTURE)
def test_captured_contracts(asynchronous, capture):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(capture["status"], json=capture["body"])

    if capture["status"] == 200:
        result = invoke(
            asynchronous, httpx.MockTransport(handler), *METHODS[capture["operationId"]]
        )
        assert result.model_dump(mode="json", exclude_unset=True) == capture["body"]
    else:
        with pytest.raises(BisibilityApiError) as caught:
            invoke(asynchronous, httpx.MockTransport(handler), *METHODS[capture["operationId"]])
        assert caught.value.status == capture["status"]
        assert caught.value.problem.model_dump(exclude_unset=True) == capture["body"]
    assert len(calls) == 1
    request = calls[0]
    assert request.method == capture["method"]
    assert request.url.path == "/api/v1" + capture["path"].replace("{project_id}", PROJECT)
    assert not request.url.params
    assert request.headers["X-Bisibility-Source"] == "sdk"
    if request.method == "PATCH":
        assert json.loads(request.content) == {"budget_mode": "fixed"}
        assert "Idempotency-Key" not in request.headers


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("typed", [False, True])
def test_all_filters_and_opaque_next_cursor(asynchronous, typed):
    from bisibility import ListPageIndexingUrlsOptions

    options = {
        "group": "not_indexed",
        "coverage_state": "Unspecified",
        "sitemap": "https://example.com/sitemap.xml?part=1&lang=en",
        "source": "manual",
        "search": "/pricing?currency=EUR",
        "changed_since": "2026-10-24T12:00:00Z",
        "cursor": "https://example.com/blog/a?x=1&y=2",
        "limit": 100,
        "history": "true",
    }
    pages = [
        copy.deepcopy(c["body"])
        for c in FIXTURE
        if c["operationId"] == "listPageIndexingUrls" and c["status"] == 200
    ]
    expected = pages[-1]

    def handler(request):
        assert dict(request.url.params) == {k: str(v) for k, v in options.items()}
        assert list(request.url.params) == list(options)
        return httpx.Response(200, json=expected)

    result = invoke(
        asynchronous,
        httpx.MockTransport(handler),
        "list_page_indexing_urls",
        (PROJECT, ListPageIndexingUrlsOptions(**options) if typed else options),
    )
    assert result.meta.next_cursor == expected["meta"]["next_cursor"]
    assert result.data[0].history.complete is True
    assert result.data[0].history.changes[0].previous.verdict == "FAIL"
    options["cursor"] = result.meta.next_cursor
    invoke(
        asynchronous,
        httpx.MockTransport(handler),
        "list_page_indexing_urls",
        (PROJECT, ListPageIndexingUrlsOptions(**options) if typed else options),
    )


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("typed", [False, True])
@pytest.mark.parametrize(
    "value,expected",
    [
        (datetime(2026, 10, 24, 12, tzinfo=timezone.utc), "2026-10-24T12:00:00Z"),
        (
            datetime(2026, 10, 24, 14, 30, 1, 123456, timezone(timedelta(hours=2))),
            "2026-10-24T12:30:01.123456Z",
        ),
        ("2026-10-24T12:00:00Z", "2026-10-24T12:00:00Z"),
        ("2026-10-24T14:30:01.123456+02:00", "2026-10-24T12:30:01.123456Z"),
        ("2026-10-24T07:00:00-05:00", "2026-10-24T12:00:00Z"),
        (None, None),
    ],
)
def test_changed_since_wire_value(asynchronous, typed, value, expected):
    from bisibility import ListPageIndexingUrlsOptions

    options = {"changed_since": value}

    def handler(request):
        assert dict(request.url.params) == ({} if expected is None else {"changed_since": expected})
        return httpx.Response(200, json={"data": [], "meta": {"next_cursor": None}})

    invoke(
        asynchronous,
        httpx.MockTransport(handler),
        "list_page_indexing_urls",
        (PROJECT, ListPageIndexingUrlsOptions(**options) if typed else options),
    )


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "value",
    [
        "not-a-date",
        "",
        "2026-02-30T12:00:00Z",
        "2026-10-24",
        "2026-10-24T12:00:00",
        datetime(2026, 10, 24, 12),
        True,
        1792843200,
        1792843200.0,
        b"2026-10-24T12:00:00Z",
        [],
        {},
    ],
)
def test_invalid_changed_since_fails_before_http(asynchronous, value):
    with pytest.raises(ValidationError):
        invoke(
            asynchronous,
            httpx.MockTransport(lambda request: pytest.fail("HTTP")),
            "list_page_indexing_urls",
            (PROJECT, {"changed_since": value}),
        )


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("oldest_result_at", [None, "2026-10-24T12:00:00.000Z"])
def test_reason_oldest_result_at_is_required_and_nullable(asynchronous, oldest_result_at):
    raw = copy.deepcopy(next(c["body"] for c in reversed(FIXTURE) if "groups" in c["body"]))
    reason = raw["groups"][0]["reasons"][0]
    reason["oldest_result_at"] = oldest_result_at
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=raw))
    result = invoke(asynchronous, transport, *METHODS["getPageIndexingReport"])
    parsed = result.groups[0].reasons[0]
    assert parsed.oldest_result_at == oldest_result_at
    assert "oldest_result_at" not in (parsed.model_extra or {})
    del reason["oldest_result_at"]
    with pytest.raises(BisibilityResponseError):
        invoke(asynchronous, transport, *METHODS["getPageIndexingReport"])


@pytest.mark.parametrize(
    "options",
    [
        {"limit": 0},
        {"limit": 101},
        {"limit": True},
        {"limit": "10"},
        {"history": True},
        {"history": "yes"},
        {"group": "future"},
        {"source": "future"},
        {"coverage_state": "a" * 501},
        {"search": "a" * 501},
        {"sitemap": "a" * 2049},
        {"cursor": "a" * 2049},
        {"other": "value"},
    ],
)
def test_invalid_options_fail_before_http(options):
    with pytest.raises(ValidationError):
        invoke(
            False,
            httpx.MockTransport(lambda request: pytest.fail("HTTP")),
            "list_page_indexing_urls",
            (PROJECT, options),
        )


@pytest.mark.parametrize(
    "patch",
    [
        {},
        {"budget_mode": "future"},
        {"budget_mode": None},
        {"inspection_daily_limit": None},
        {"inspection_daily_limit": -1},
        {"inspection_daily_limit": 2001},
        {"inspection_daily_limit": True},
        {"inspection_daily_limit": "1"},
        {"inspection_daily_limit": 1.5},
        {"other": "value"},
    ],
)
def test_invalid_patch_fails_before_http(patch):
    with pytest.raises(ValidationError):
        invoke(
            False,
            httpx.MockTransport(lambda request: pytest.fail("HTTP")),
            "update_page_indexing_settings",
            (PROJECT, patch),
        )


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "patch",
    [
        {"budget_mode": "off"},
        {"budget_mode": "available_quota"},
        {"inspection_daily_limit": 0},
        {"budget_mode": "fixed", "inspection_daily_limit": 2000},
    ],
)
def test_patch_omissions_typed_input_and_idempotency(asynchronous, patch):
    from bisibility import PageIndexingSettingsPatch, RequestOptions

    expected = next(c["body"] for c in FIXTURE if c["operationId"] == "getPageIndexingSettings")

    def handler(request):
        assert json.loads(request.content) == patch
        assert request.headers["Idempotency-Key"] == "settings-example-001"
        return httpx.Response(200, json=expected)

    result = invoke(
        asynchronous,
        httpx.MockTransport(handler),
        "update_page_indexing_settings",
        (PROJECT, PageIndexingSettingsPatch(**patch)),
        request_options=RequestOptions(idempotency_key="settings-example-001"),
    )
    assert result.inspection_daily_limit == expected["inspection_daily_limit"]


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "operation,field",
    [
        ("getPageIndexingReport", "oldest_result_at"),
        ("getPageIndexingSettings", "last429_at"),
        ("listPageIndexingUrls", "inspection_failed_at"),
    ],
)
def test_required_null_fields(asynchronous, operation, field):
    raw = copy.deepcopy(
        next(
            c["body"]
            for c in reversed(FIXTURE)
            if c["operationId"] == operation and c["status"] == 200
        )
    )
    row = raw["data"][0] if operation == "listPageIndexingUrls" else raw
    del row[field]
    with pytest.raises(BisibilityResponseError):
        invoke(
            asynchronous,
            httpx.MockTransport(lambda request: httpx.Response(200, json=raw)),
            *METHODS[operation],
        )


@pytest.mark.parametrize(
    "operation", ["getPageIndexingReport", "getPageIndexingSettings", "listPageIndexingUrls"]
)
def test_future_values_and_optional_history(operation):
    raw = copy.deepcopy(
        next(
            c["body"]
            for c in reversed(FIXTURE)
            if c["operationId"] == operation and c["status"] == 200
        )
    )
    raw["future_field"] = {"value": 1}
    if operation == "getPageIndexingReport":
        raw["budget_mode"] = "future_mode"
        raw["groups"][0]["group"] = "future_group"
    elif operation == "getPageIndexingSettings":
        raw["budget_mode"] = "future_mode"
        raw["available_modes"].append("future_mode")
    else:
        raw["data"][0].update(group="future_group", source="future_source", verdict="FUTURE")
        del raw["data"][0]["history"]
    result = invoke(
        False,
        httpx.MockTransport(lambda request: httpx.Response(200, json=raw)),
        *METHODS[operation],
    )
    assert result.model_dump(mode="json", exclude_unset=True) == raw


@pytest.mark.parametrize("method,args", METHODS.values())
def test_invalid_project_fails_before_http(method, args):
    with pytest.raises(ValueError):
        invoke(
            False,
            httpx.MockTransport(lambda request: pytest.fail("HTTP")),
            method,
            ("kw_a00000000000000000000000", *args[1:]),
        )


@pytest.mark.parametrize("asynchronous", [False, True])
def test_history_is_optional_but_cannot_be_null(asynchronous):
    raw = copy.deepcopy(
        next(
            c["body"]
            for c in reversed(FIXTURE)
            if c["operationId"] == "listPageIndexingUrls" and c["status"] == 200
        )
    )
    raw["data"][0]["history"] = None
    with pytest.raises(BisibilityResponseError):
        invoke(
            asynchronous,
            httpx.MockTransport(lambda request: httpx.Response(200, json=raw)),
            *METHODS["listPageIndexingUrls"],
        )


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("key,expected_calls", [(None, 1), ("settings-example-002", 3)])
def test_patch_status_retries_follow_existing_idempotency_rule(
    asynchronous, key, expected_calls, monkeypatch
):
    monkeypatch.setattr("bisibility.client._sleep", lambda delay: None)

    async def no_sleep(delay):
        pass

    monkeypatch.setattr("bisibility.async_client.asyncio.sleep", no_sleep)
    calls = []
    body = {
        "type": "https://api.example.com/problems/provider_unavailable",
        "title": "Provider unavailable",
        "status": 503,
        "details": {"reason": "example"},
    }

    def handler(request):
        calls.append(request)
        return httpx.Response(503, json=body)

    with pytest.raises(BisibilityApiError) as caught:
        invoke(
            asynchronous,
            httpx.MockTransport(handler),
            *METHODS["updatePageIndexingSettings"],
            request_options={"idempotency_key": key},
        )
    assert len(calls) == expected_calls
    assert caught.value.problem.details == body["details"]
    assert all(request.headers.get("Idempotency-Key") == key for request in calls)
