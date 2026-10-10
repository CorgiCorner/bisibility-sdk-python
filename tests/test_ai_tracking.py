from __future__ import annotations

import asyncio
import base64
import inspect
import json
from typing import Any

import httpx
import pytest

from bisibility import AsyncBisibilityClient, BisibilityClient
from bisibility.errors import BisibilityConfigurationError

PROJECT = "prj_a00000000000000000000000"
PROMPT = "aip_a00000000000000000000000"
RUN = "air_a00000000000000000000000"
CURSOR = (
    base64.urlsafe_b64encode(
        json.dumps(
            {"v": 3, "public_id": "asm_a00000000000000000000000", "t": "2026-10-08T00:00:00Z"}
        ).encode()
    )
    .decode()
    .rstrip("=")
)
CONFIG = {
    "provider": "dataforseo",
    "endpoint": "consumer_scrape",
    "engine": "chat_gpt",
    "source": "consumer_scrape",
    "model": None,
    "parameters": {},
}
PREVIEW = {"prompt_ids": [PROMPT], "configurations": [CONFIG]}
PLAN = {
    **PREVIEW,
    "credential_connection_id": "conn_a00000000000000000000000",
    "credential_version": "v1",
    "budget_revision": "b1",
    "consent_revision": "c1",
    "deadline": "2026-10-09T00:00:00Z",
    "consent": True,
}


@pytest.mark.parametrize("async_mode", [False, True])
def test_tracking_transport_preserves_identity_and_unknown_evidence(async_mode: bool) -> None:
    requests: list[httpx.Request] = []
    sample = {
        "id": "asm_a00000000000000000000000",
        "prompt_revision_id": "apr_a00000000000000000000000",
        "measurement": "unknown",
        "source": "consumer_scrape",
        "engine": "chat_gpt",
        "prompt": "Example?",
        "evidence": None,
        "citations": [],
        "cost_usd": None,
        "cost_state": "unknown",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/preview"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "configurations": [CONFIG],
                        "credential_connection_id": PLAN["credential_connection_id"],
                        "credential_version": "v1",
                        "budget_revision": "b1",
                        "consent_revision": "c1",
                        "estimated_cost_cents": 0.6,
                    }
                },
            )
        if request.url.path.endswith("/samples"):
            return httpx.Response(200, json={"data": [sample], "meta": {"next_cursor": CURSOR}})
        return httpx.Response(
            201,
            json={
                "data": {
                    "id": RUN,
                    "state": "planned",
                    "created_at": "2026-10-08T00:00:00Z",
                    "updated_at": "2026-10-08T00:00:00Z",
                    "finished_at": None,
                    "planned_at": None,
                    "sample_count": 1,
                }
            },
        )

    async def run() -> None:
        client: Any = (AsyncBisibilityClient if async_mode else BisibilityClient)(
            api_key="bsb_key_test_x",
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(handler),
        )

        async def call(value: Any) -> Any:
            return await value if inspect.isawaitable(value) else value

        try:
            await call(client.preview_ai_tracking_run(PROJECT, PREVIEW))
            await call(client.create_ai_tracking_run(PROJECT, PLAN, {"idempotency_key": "stable"}))
            result = await call(client.list_ai_tracking_samples(PROJECT, RUN, {"cursor": CURSOR}))
            assert result.data[0].model_dump() == sample
            assert result.meta.next_cursor == CURSOR
            with pytest.raises(BisibilityConfigurationError):
                await call(client.get_ai_tracking_run(PROJECT, PROMPT))
            with pytest.raises(BisibilityConfigurationError, match="Idempotency-Key"):
                await call(client.create_ai_tracking_run(PROJECT, PLAN))
        finally:
            await call(client.close())

    asyncio.run(run())
    assert len(requests) == 3
    assert requests[1].headers["Idempotency-Key"] == "stable"
    assert "idempotency_key" not in json.loads(requests[1].content)
    assert requests[2].url.params["cursor"] == CURSOR
