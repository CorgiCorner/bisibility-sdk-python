from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from bisibility import AsyncBisibilityClient, BisibilityClient, RequestOptions, SavedView

PROJECT = "prj_a00000000000000000000000"
REPORT = "agr_a00000000000000000000000"
DEVICE = "dpt_a00000000000000000000000"
FIXTURES = json.loads((Path(__file__).parent / "fixtures/challenge-api.json").read_text())
CASES = [
    (
        "get_domain_verification",
        "getDomainVerification",
        "GET",
        f"/projects/{PROJECT}/domain-verification",
        [PROJECT],
        None,
        {},
    ),
    (
        "issue_domain_verification",
        "issueDomainVerification",
        "POST",
        f"/projects/{PROJECT}/domain-verification",
        [PROJECT, {"method": "dns_txt"}],
        {"method": "dns_txt"},
        {},
    ),
    (
        "check_domain_verification",
        "checkDomainVerification",
        "POST",
        f"/projects/{PROJECT}/domain-verification/check",
        [PROJECT],
        None,
        {},
    ),
    (
        "get_site_audit_run",
        "getSiteAuditRun",
        "GET",
        f"/projects/{PROJECT}/site-audits/{REPORT}/run",
        [PROJECT, REPORT],
        None,
        {},
    ),
    (
        "cancel_site_audit_run",
        "cancelSiteAuditRun",
        "POST",
        f"/projects/{PROJECT}/site-audits/{REPORT}/cancel",
        [PROJECT, REPORT],
        None,
        {},
    ),
    (
        "resume_site_audit_run",
        "resumeSiteAuditRun",
        "POST",
        f"/projects/{PROJECT}/site-audits/{REPORT}/resume",
        [PROJECT, REPORT],
        None,
        {},
    ),
    (
        "list_site_audit_pages",
        "listSiteAuditPages",
        "GET",
        f"/projects/{PROJECT}/site-audits/{REPORT}/pages",
        [PROJECT, REPORT, {"offset": 15, "limit": 100}],
        None,
        {"offset": "15", "limit": "100"},
    ),
    (
        "delete_me",
        "deleteMe",
        "DELETE",
        "/me",
        [{"confirm_email": "owner@example.com"}],
        {"confirm_email": "owner@example.com"},
        {},
    ),
    ("list_device_push_tokens", "listDevicePushTokens", "GET", "/me/push-tokens", [], None, {}),
    (
        "register_device_push_token",
        "registerDevicePushToken",
        "POST",
        "/me/push-tokens",
        [{"token": "0" * 32, "environment": "sandbox", "bundle_id": "com.example.app"}],
        {"token": "0" * 32, "environment": "sandbox", "bundle_id": "com.example.app"},
        {},
    ),
    (
        "delete_device_push_token",
        "deleteDevicePushToken",
        "DELETE",
        f"/me/push-tokens/{DEVICE}",
        [DEVICE],
        None,
        {},
    ),
    (
        "get_search_performance_totals",
        "getSearchPerformanceTotals",
        "GET",
        f"/projects/{PROJECT}/analytics/totals",
        [
            PROJECT,
            {"start_date": "2026-11-01", "end_date": "2026-11-10", "compare_previous": "true"},
        ],
        None,
        {"start_date": "2026-11-01", "end_date": "2026-11-10", "compare_previous": "true"},
    ),
]


def invoke(async_mode, transport, name, args, **kwargs):
    if async_mode:

        async def run():
            async with AsyncBisibilityClient(
                api_key="bsb_pat_live_example",
                base_url="https://api.example.com/api/v1",
                transport=transport,
            ) as client:
                return await getattr(client, name)(*args, **kwargs)

        return asyncio.run(run())
    with BisibilityClient(
        api_key="bsb_pat_live_example",
        base_url="https://api.example.com/api/v1",
        transport=transport,
    ) as client:
        return getattr(client, name)(*args, **kwargs)


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name,fixture,method,path,args,body,query", CASES)
def test_operation_contracts(async_mode, name, fixture, method, path, args, body, query):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == method
        assert request.url.path == "/api/v1" + path
        assert dict(request.url.params) == query
        assert request.headers["Authorization"] == "Bearer bsb_pat_live_example"
        assert request.headers["Idempotency-Key"] == "challenge-test"
        assert (json.loads(request.content) if request.content else None) == body
        return httpx.Response(200, json=FIXTURES[fixture])

    result = invoke(
        async_mode,
        httpx.MockTransport(handler),
        name,
        args,
        request_options=RequestOptions(idempotency_key="challenge-test"),
    )
    assert result.model_dump(mode="json", exclude_unset=True) == FIXTURES[fixture]
    assert len(calls) == 1


@pytest.mark.parametrize("fixture", ["savedV1", "savedV2"])
@pytest.mark.parametrize("shown", [False, True])
def test_saved_view_definition(fixture, shown):
    payload = copy.deepcopy(FIXTURES[fixture])
    payload["definition"]["filters"]["ai_overview_shown"] = shown
    result = SavedView.model_validate(payload)
    assert result.definition.filters.ai_overview_shown is shown
    if fixture == "savedV2":
        assert result.definition.report_scope.view == "ai_overviews"
    assert result.model_dump(mode="json", exclude_unset=True) == payload
    del payload["definition"]["filters"]["ai_overview_shown"]
    legacy = SavedView.model_validate(payload)
    assert legacy.definition.filters.ai_overview_shown is False
    payload.pop("definition")
    assert SavedView.model_validate(payload).definition is None


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("fixture", ["savedV1", "savedV2"])
@pytest.mark.parametrize("method", ["list_saved_views", "create_saved_view"])
def test_saved_view_endpoints(async_mode, fixture, method):
    def handler(request):
        assert request.url.path == f"/api/v1/projects/{PROJECT}/saved-views"
        if method == "create_saved_view":
            assert request.method == "POST"
            assert json.loads(request.content)["config"]["filters"]["ai_overview_shown"] is False
            return httpx.Response(201, json=FIXTURES[fixture])
        assert request.method == "GET"
        return httpx.Response(
            200, json={"data": [FIXTURES[fixture]], "meta": {"next_cursor": None}}
        )

    args = [PROJECT]
    if method == "create_saved_view":
        args.append({"name": "Example", "config": {"filters": {"ai_overview_shown": False}}})
    result = invoke(async_mode, httpx.MockTransport(handler), method, args)
    view = result if method == "create_saved_view" else result.data[0]
    assert view.definition.filters.ai_overview_shown is False
    if fixture == "savedV2":
        assert view.definition.report_scope.view == "ai_overviews"


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "name,method,suffix,input",
    [
        ("connect_provider", "POST", "/connect", {}),
        ("test_provider_connection", "POST", "/test", {}),
        ("update_provider_settings", "PATCH", "", {}),
        ("disconnect_provider", "DELETE", "", None),
        ("update_provider_budgets", "PATCH", "/budgets", {}),
    ],
)
def test_pagespeed_all_operations(async_mode, name, method, suffix, input):
    def handler(request):
        assert request.method == method
        assert request.url.path == f"/api/v1/projects/{PROJECT}/providers/pagespeed{suffix}"
        if suffix == "/test":
            payload = {"ok": True, "message": "Connected."}
        elif method == "DELETE":
            payload = {"ok": True}
        elif suffix == "/budgets":
            payload = {
                "provider": "pagespeed",
                "connection_id": "conn_a00000000000000000000000",
                "credential_source": "own",
                "source": "connection",
                "own": {"app": None, "programmatic": None},
                "credits": {"app": None, "programmatic": None},
            }
        else:
            payload = {
                "id": "conn_a00000000000000000000000",
                "project_id": PROJECT,
                "provider": "pagespeed",
                "kind": "enrichment",
                "status": "connected",
                "enabled": False,
                "is_primary": False,
                "priority": 0,
            }
        return httpx.Response(200, json=payload)

    args = [PROJECT, "pagespeed"]
    if input is not None:
        args.append(input)
    invoke(async_mode, httpx.MockTransport(handler), name, args)


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "name,args",
    [
        ("get_domain_verification", ["raw"]),
        ("issue_domain_verification", [PROJECT, {"method": "invalid"}]),
        ("get_site_audit_run", [PROJECT, "raw"]),
        ("cancel_site_audit_run", [PROJECT, "raw"]),
        ("resume_site_audit_run", [PROJECT, "raw"]),
        ("list_site_audit_pages", [PROJECT, REPORT, {"offset": -1}]),
        ("list_site_audit_pages", [PROJECT, REPORT, {"limit": 101}]),
        ("delete_device_push_token", ["usr_a00000000000000000000000"]),
    ],
)
def test_invalid_input_never_reaches_transport(async_mode, name, args):
    def handler(request):
        pytest.fail("invalid input reached transport")

    with pytest.raises((ValueError, ValidationError)):
        invoke(async_mode, httpx.MockTransport(handler), name, args)


def test_pagespeed_is_in_public_provider_type():
    from pydantic import TypeAdapter

    from bisibility import ProviderId

    assert TypeAdapter(ProviderId).validate_python("pagespeed") == "pagespeed"


@pytest.mark.parametrize("fixture", ["savedV1", "savedV2"])
def test_saved_view_filter_rejects_non_boolean(fixture):
    for value in (None, "false", 0, 1):
        payload = copy.deepcopy(FIXTURES[fixture])
        payload["definition"]["filters"]["ai_overview_shown"] = value
        with pytest.raises(ValidationError):
            SavedView.model_validate(payload)


@pytest.mark.parametrize("async_mode", [False, True])
def test_missing_domain_proof(async_mode):
    result = invoke(
        async_mode,
        httpx.MockTransport(lambda request: httpx.Response(200, json={"data": None})),
        "get_domain_verification",
        [PROJECT],
    )
    assert result.data is None


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "name,args",
    [
        (
            "register_device_push_token",
            [{"token": "invalid", "environment": "sandbox", "bundle_id": "com.example.app"}],
        ),
        (
            "register_device_push_token",
            [{"token": "0" * 32, "environment": "invalid", "bundle_id": "com.example.app"}],
        ),
        ("delete_me", [{"confirm_email": ""}]),
        (
            "get_search_performance_totals",
            [PROJECT, {"start_date": "invalid", "end_date": "2026-11-11"}],
        ),
    ],
)
def test_additional_input_constraints(async_mode, name, args):
    def handler(request):
        pytest.fail("invalid input reached transport")

    with pytest.raises(ValueError):
        invoke(async_mode, httpx.MockTransport(handler), name, args)
