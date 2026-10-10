from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from bisibility import AsyncBisibilityClient, BisibilityClient
from bisibility.ai_tracking import AITrackingAcceptanceInput, AITrackingEvidence, AITrackingExport
from bisibility.ai_tracking_suggestions import AITrackingSuggestionsPreviewInput
from bisibility.errors import BisibilityConfigurationError

PROJECT = "prj_a00000000000000000000000"
KEY = "11111111-1111-4111-8111-111111111111"
INPUT = {
    "configuration": {
        "provider": "dataforseo",
        "engine": "chat_gpt",
        "model": "gpt-5-mini",
        "language_code": "en",
        "max_output_tokens": 1024,
        "advisory_cost_limit_cents": 50,
    },
    "input_snapshot": {
        "context": {
            "business": "Example",
            "audience": "Teams",
            "products": "Analytics",
            "goals": "Visibility",
            "agent_rules": "Review claims",
        },
        "competitors": [
            {
                "id": "cmp_a00000000000000000000000",
                "label": None,
                "domain": "competitor.example.com",
            }
        ],
    },
}
PREVIEW = {
    **INPUT,
    "version": 1,
    "snapshot_hash": "a" * 64,
    "estimated_cost_cents": 0.5,
    "estimate_kind": "forecast",
    "is_guaranteed_maximum": False,
    "credential_connection_id": "conn_a00000000000000000000000",
    "credential_version": "v1",
    "budget_revision": "b1",
    "consent_revision": "c1",
    "expires_at": "2026-10-08T23:00:00Z",
    "limitations": ["Forecast has no guaranteed maximum"],
}


def test_export_scope_is_optional_and_preserves_download_completeness() -> None:
    body = {"items": [], "run_id": "air_a00000000000000000000000", "next_cursor": "resume"}
    assert AITrackingExport.model_validate(body).scope is None
    scope = {"complete": False, "max_pages": 20, "loaded": 1000, "resumed": True}
    result = AITrackingExport.model_validate({**body, "scope": scope})
    assert result.scope is not None
    assert result.scope.model_dump() == scope
    evidence = AITrackingEvidence.model_validate(
        {
            "answer_text": None,
            "raw": None,
            "answer_truncated": False,
            "raw_truncated": False,
            "search_results": [],
            "requested_locale": None,
            "effective_locale": None,
            "locale_mechanism": None,
            "requested_model": None,
            "actual_model": None,
            "provider_status": None,
            "observed_at": None,
            "fetched_at": "2026-10-08T12:00:00Z",
            "recorded_source": "fresh",
        }
    )
    assert evidence.observed_at is None


@pytest.mark.parametrize("async_mode", [False, True])
def test_generation_transport_freezes_review_and_preserves_unknown_cost(async_mode: bool) -> None:
    requests: list[httpx.Request] = []
    result = {
        "generation_id": "asg_a00000000000000000000000",
        "drafts": [],
        "cost_usd": None,
        "cost_state": "unknown",
        "method": "model_generated_hypothesis",
        "limitations": [],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, json={"data": PREVIEW if request.url.path.endswith("preview") else result}
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
            preview = await call(client.ai_tracking_suggestions_preview(PROJECT, INPUT))
            response = await call(
                client.ai_tracking_suggestions_generate(
                    PROJECT,
                    {"preview": preview.data.model_dump(), "consent": True},
                    {"idempotency_key": KEY},
                )
            )
            assert response.data.cost_usd is None
            assert response.data.method == "model_generated_hypothesis"
            with pytest.raises(BisibilityConfigurationError, match="UUID"):
                await call(
                    client.ai_tracking_suggestions_generate(
                        PROJECT, {"preview": PREVIEW, "consent": True}
                    )
                )
        finally:
            await call(client.close())

    asyncio.run(run())
    assert requests[1].headers["Idempotency-Key"] == KEY
    body = json.loads(requests[1].content)
    assert "idempotency_key" not in body
    assert body["preview"]["input_snapshot"]["competitors"][0]["label"] is None
    assert len(requests) == 2


def test_snapshot_bounds_and_trusted_acceptance_are_explicit() -> None:
    oversized = {
        **INPUT,
        "input_snapshot": {
            **INPUT["input_snapshot"],
            "context": {**INPUT["input_snapshot"]["context"], "business": "x" * 5000},
        },
    }
    with pytest.raises(ValidationError, match="5000"):
        AITrackingSuggestionsPreviewInput.model_validate(oversized)
    draft = {
        "text": "Edited hypothesis?",
        "category": "neutral",
        "generation_reference": {"generation_id": "asg_a00000000000000000000000", "draft_id": KEY},
    }
    assert (
        AITrackingAcceptanceInput.model_validate({"drafts": [draft]}).drafts[0].generation_reference
        is not None
    )
    with pytest.raises(ValidationError, match="generation reference"):
        AITrackingAcceptanceInput.model_validate(
            {
                "drafts": [
                    {
                        "text": "Example?",
                        "category": "neutral",
                        "provenance": "model_generated_hypothesis",
                    }
                ]
            }
        )
