from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest
from pydantic import ValidationError

from bisibility import (
    AsyncBisibilityClient,
    BisibilityApiError,
    BisibilityClient,
    BisibilityConfigurationError,
    BisibilityNetworkError,
    BisibilityResponseError,
    RequestOptions,
    SearchIndexInspectionError,
    SearchIndexInspectionInput,
)

FIXTURE = json.loads((Path(__file__).parent / "fixtures/search-index.json").read_text())
PROJECT = "prj_a00000000000000000000000"
SITEMAP = "https://example.com/blog/sitemap.xml?part=1&lang=en"
METHODS = {
    "listSearchIndexSitemaps": ("list_search_index_sitemaps", (PROJECT,)),
    "getSearchIndexSitemap": ("get_search_index_sitemap", (PROJECT, SITEMAP)),
    "inspectSearchIndexUrls": (
        "inspect_search_index_urls",
        (PROJECT, {"urls": ["https://example.com/blog/a"]}),
    ),
}


def invoke(asynchronous, transport, method, args, request_options=None):
    kwargs = {
        "api_key": "bsb_pat_live_example",
        "base_url": "https://api.example.com/api/v1",
        "transport": transport,
        "max_retries": 2,
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

    method, args = METHODS[capture["operationId"]]
    if capture["status"] == 200:
        result = invoke(asynchronous, httpx.MockTransport(handler), method, args)
        assert result.model_dump(mode="json", exclude_unset=True) == capture["body"]
    else:
        with pytest.raises(BisibilityApiError) as caught:
            invoke(asynchronous, httpx.MockTransport(handler), method, args)
        assert caught.value.status == capture["status"]
        assert caught.value.problem.model_dump(exclude_unset=True) == capture["body"]
    assert len(calls) == 1
    request = calls[0]
    assert request.method == capture["method"]
    expected_path = (
        capture["path"].replace("{project_id}", PROJECT).replace("{path}", quote(SITEMAP, safe=""))
    )
    assert request.url.raw_path.decode() == "/api/v1" + expected_path
    assert request.headers["X-Bisibility-Source"] == "sdk"
    assert request.headers["Authorization"] == "Bearer bsb_pat_live_example"
    if request.method == "POST":
        assert json.loads(request.content) == args[1]


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("key", [None, "inspection-example-001"])
def test_inspection_network_loss_never_blindly_retries(asynchronous, key):
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadError("Response lost", request=request)

    with pytest.raises(BisibilityNetworkError):
        invoke(
            asynchronous,
            httpx.MockTransport(handler),
            *METHODS["inspectSearchIndexUrls"],
            request_options=RequestOptions(idempotency_key=key),
        )
    assert len(calls) == 1
    assert calls[0].headers.get("Idempotency-Key") == key


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("key,expected_calls", [(None, 1), ("inspection-example-002", 3)])
def test_inspection_status_retry_requires_key(asynchronous, key, expected_calls, monkeypatch):
    monkeypatch.setattr("bisibility.client._sleep", lambda delay: None)

    async def no_sleep(delay):
        pass

    monkeypatch.setattr("bisibility.async_client.asyncio.sleep", no_sleep)
    calls = []
    body = {
        "type": "https://api.example.com/problems/provider_rate_limited",
        "title": "Provider rate limited",
        "status": 429,
        "code": "provider_rate_limited",
        "details": {"scope": "minute", "reset_at": "2026-10-25T00:00:00Z"},
    }

    def handler(request):
        calls.append(request)
        return httpx.Response(429, json=body)

    with pytest.raises(BisibilityApiError) as caught:
        invoke(
            asynchronous,
            httpx.MockTransport(handler),
            *METHODS["inspectSearchIndexUrls"],
            request_options={"idempotency_key": key},
        )
    assert len(calls) == expected_calls
    assert caught.value.problem.code == "provider_rate_limited"
    assert caught.value.problem.details == body["details"]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"urls": []},
        {"urls": ["a"] * 11},
        {"urls": [""]},
        {"urls": ["a" * 2049]},
        {"urls": [True]},
        {"urls": ["a"], "property": "other"},
    ],
)
def test_invalid_inspection_input_fails_before_http(body):
    def handler(request):
        pytest.fail("Invalid input reached HTTP")

    with pytest.raises(ValidationError):
        invoke(False, httpx.MockTransport(handler), "inspect_search_index_urls", (PROJECT, body))


@pytest.mark.parametrize("method,args", METHODS.values())
def test_invalid_project_fails_before_http(method, args):
    with pytest.raises(ValueError):
        invoke(
            False,
            httpx.MockTransport(lambda request: pytest.fail("HTTP")),
            method,
            ("raw-id", *args[1:]),
        )


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "path",
    [
        "",
        ".",
        "..",
        pytest.param("a" * 2049, id="overlong-string"),
        pytest.param("https://example.com/" + "a" * 2048, id="overlong-https-url"),
        "/sitemap.xml",
        "sitemap.xml",
        "ftp://example.com/sitemap.xml",
        "javascript:alert(1)",
        "https://",
        "http:///sitemap.xml",
        "https://[invalid/sitemap.xml",
        "https://user@/sitemap.xml",
        None,
        123,
    ],
)
def test_invalid_sitemap_url_fails_before_http(asynchronous, path):
    with pytest.raises(BisibilityConfigurationError) as caught:
        invoke(
            asynchronous,
            httpx.MockTransport(lambda request: pytest.fail("HTTP")),
            "get_search_index_sitemap",
            (PROJECT, path),
        )
    assert str(caught.value) == (
        "Expected an absolute HTTP or HTTPS sitemap URL of 1-2048 characters."
    )


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "path",
    [
        pytest.param(
            "https://example.com/" + "a" * (2048 - len("https://example.com/")),
            id="https-url-at-length-limit",
        ),
        "HTTP://example.com/sitemap.xml",
    ],
)
def test_valid_sitemap_url_boundaries_are_encoded(asynchronous, path):
    calls = []
    body = next(
        c["body"]
        for c in FIXTURE
        if c["operationId"] == "getSearchIndexSitemap" and c["status"] == 200
    )

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=body)

    invoke(
        asynchronous,
        httpx.MockTransport(handler),
        "get_search_index_sitemap",
        (PROJECT, path),
    )
    assert len(calls) == 1
    assert calls[0].method == "GET"
    assert calls[0].url.raw_path.decode() == (
        f"/api/v1/projects/{PROJECT}/search-index/sitemaps/{quote(path, safe='')}"
    )


@pytest.mark.parametrize("asynchronous", [False, True])
def test_required_null_and_open_response_values(asynchronous):
    raw = copy.deepcopy(
        next(
            c["body"]
            for c in FIXTURE
            if c["operationId"] == "inspectSearchIndexUrls"
            and c["status"] == 200
            and c["body"]["results"][0]["inspection"] is not None
        )
    )
    row = raw["results"][0]
    row["inspection"]["verdict"] = "FUTURE_VERDICT"
    row["inspection"]["future_field"] = {"value": 1}
    row["error"] = {"code": "future_error", "message": "Example", "scope": "future_scope"}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=raw))
    result = invoke(asynchronous, transport, *METHODS["inspectSearchIndexUrls"])
    assert result.model_dump(mode="json", exclude_unset=True) == raw
    del row["inspection"]["last_crawl_at"]
    with pytest.raises(BisibilityResponseError):
        invoke(asynchronous, transport, *METHODS["inspectSearchIndexUrls"])


@pytest.mark.parametrize("field", ["reset_at", "scope"])
def test_optional_rate_limit_metadata_cannot_be_explicitly_null(field):
    with pytest.raises(ValidationError):
        SearchIndexInspectionError.model_validate(
            {"code": "provider_rate_limited", "message": "Example", field: None}
        )


def test_typed_inspection_input_at_batch_boundary():
    body = SearchIndexInspectionInput(urls=[f"https://example.com/{i}" for i in range(10)])
    expected = {"property": "sc-domain:example.com", "results": []}

    def handler(request):
        assert json.loads(request.content) == body.model_dump()
        return httpx.Response(200, json=expected)

    result = invoke(
        False, httpx.MockTransport(handler), "inspect_search_index_urls", (PROJECT, body)
    )
    assert result.model_dump() == expected
