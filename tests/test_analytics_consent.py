import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from bisibility import (
    AsyncBisibilityClient,
    BisibilityApiError,
    BisibilityClient,
    BisibilityResponseError,
)

PENDING = {"analytics": False, "decided_at": None, "source": None, "version": 2}


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("analytics", [False, True])
def test_reads_pending_and_writes_only_explicit_account_analytics(asynchronous, analytics):
    requests = []

    def handler(request):
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"apiVersions": ["v1"], "data": []})
        requests.append(request)
        assert request.url.path == "/api/v1/me/analytics-consent"
        assert request.headers["Authorization"] == "Bearer bsb_pat_live_fixture"
        if request.method == "GET":
            return httpx.Response(200, json=PENDING)
        assert request.method == "PUT"
        assert json.loads(request.content) == {"analytics": analytics}
        return httpx.Response(
            200,
            json={
                **PENDING,
                "analytics": analytics,
                "source": "api",
                "decided_at": "2026-10-18T12:00:00Z",
            },
        )

    kwargs = {
        "api_key": "bsb_pat_live_fixture",
        "base_url": "https://api.test/api/v1",
        "transport": httpx.MockTransport(handler),
    }

    async def run():
        async with AsyncBisibilityClient(**kwargs) as client:
            pending = await client.get_analytics_consent()
            assert pending.model_dump(mode="json") == PENDING
            saved = await client.update_analytics_consent({"analytics": analytics})
            assert saved.analytics is analytics

    if asynchronous:
        asyncio.run(run())
    else:
        with BisibilityClient(**kwargs) as client:
            assert client.get_analytics_consent().model_dump(mode="json") == PENDING
            assert client.update_analytics_consent({"analytics": analytics}).analytics is analytics
    assert len(requests) == 2


@pytest.mark.parametrize(
    "body",
    [
        {**PENDING, "analytics": "false"},
        {**PENDING, "source": "other"},
        {"analytics": False, "source": None, "version": 2},
    ],
)
def test_rejects_malformed_permission_response(body):
    def handler(request):
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"apiVersions": ["v1"], "data": []})
        return httpx.Response(200, json=body)

    with BisibilityClient(
        api_key="bsb_pat_live_fixture", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(BisibilityResponseError):
            client.get_analytics_consent()


def test_preserves_authorization_error():
    def handler(request):
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"apiVersions": ["v1"], "data": []})
        return httpx.Response(
            403, json={"type": "about:blank", "title": "Forbidden", "status": 403}
        )

    with BisibilityClient(
        api_key="bsb_pat_live_fixture", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(BisibilityApiError):
            client.update_analytics_consent({"analytics": False})


@pytest.mark.parametrize("body", [{}, {"analytics": "false"}, {"analytics": True, "replay": True}])
def test_rejects_missing_coerced_or_browser_replay_input_before_http(body):
    requests = []

    def handler(request):
        requests.append(request)
        raise AssertionError("Invalid account consent input must not reach HTTP")

    with BisibilityClient(
        api_key="bsb_pat_live_fixture", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ValidationError):
            client.update_analytics_consent(body)
    assert requests == []
