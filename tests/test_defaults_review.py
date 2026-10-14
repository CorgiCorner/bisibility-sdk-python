import asyncio
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from bisibility import AsyncBisibilityClient, BisibilityClient, ProjectDefaultsReview
from bisibility.errors import BisibilityConfigurationError

F = json.loads((Path(__file__).parent / "fixtures/defaults-review.json").read_text())
REVIEW = {
    "expected_source_hash": F["preview"]["expected_source_hash"],
    "expected_revision": F["preview"]["expected_revision"],
    "preview_token": F["preview"]["preview_token"],
    "idempotency_key": "synthetic-reviewed-key-123",
    "confirmed": True,
}


@pytest.mark.parametrize("asynchronous", [False, True])
def test_signed_defaults_preview_and_confirmed_retry_identity(asynchronous):
    requests = []

    def handler(request):
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(
                200,
                json={
                    "data": [],
                    "apiVersions": ["v1"],
                    "features": {"reviewed_project_defaults": "v1"},
                },
            )
        requests.append(request)
        assert request.method == "PATCH"
        body = json.loads(request.content)
        if request.url.params.get("preview_only") == "true":
            assert "review" not in body
            assert "Idempotency-Key" not in request.headers
            return httpx.Response(200, json=F["preview"])
        assert body["review"] == REVIEW
        assert request.headers["Idempotency-Key"] == REVIEW["idempotency_key"]
        return httpx.Response(200, json=F["saved"])

    async def async_case():
        async with AsyncBisibilityClient(
            api_key="bsb_key_test_fixture",
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(handler),
        ) as client:
            preview = await client.preview_project_defaults(F["project"], F["patch"])
            assert preview.model_dump(mode="json") == F["preview"]
            assert preview.expected_revision == "9007199254740993123"
            saved = await client.update_project_defaults(
                F["project"], {**F["patch"], "review": REVIEW}
            )
            assert saved.project_id == F["project"]

    if asynchronous:
        asyncio.run(async_case())
    else:
        with BisibilityClient(
            api_key="bsb_key_test_fixture",
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(handler),
        ) as client:
            preview = client.preview_project_defaults(F["project"], F["patch"])
            assert preview.model_dump(mode="json") == F["preview"]
            saved = client.update_project_defaults(F["project"], {**F["patch"], "review": REVIEW})
            assert saved.project_id == F["project"]
    assert len(requests) == 2


@pytest.mark.parametrize("asynchronous", [False, True])
def test_legacy_server_cannot_mistake_preview_for_write(asynchronous):
    methods = []

    def handler(request):
        methods.append(request.method)
        return httpx.Response(200, json={"data": [], "apiVersions": ["v1"]})

    async def async_case():
        async with AsyncBisibilityClient(
            api_key="bsb_key_test_fixture", transport=httpx.MockTransport(handler)
        ) as client:
            with pytest.raises(BisibilityConfigurationError):
                await client.preview_project_defaults(F["project"], F["patch"])

    if asynchronous:
        asyncio.run(async_case())
    else:
        with BisibilityClient(
            api_key="bsb_key_test_fixture", transport=httpx.MockTransport(handler)
        ) as client:
            with pytest.raises(BisibilityConfigurationError):
                client.preview_project_defaults(F["project"], F["patch"])
    assert methods == ["GET"]


@pytest.mark.parametrize("confirmed", [False, 1, "true", None])
def test_review_requires_literal_user_consent(confirmed):
    with pytest.raises(ValidationError):
        ProjectDefaultsReview.model_validate({**REVIEW, "confirmed": confirmed})


@pytest.mark.parametrize("key", [" abcdefgh ", "abcdefgh\t", "abcdefgh\x7f"])
def test_review_key_cannot_change_between_body_and_header(key):
    with BisibilityClient(
        api_key="bsb_key_test_fixture",
        transport=httpx.MockTransport(lambda _: pytest.fail("invalid command reached HTTP")),
    ) as client:
        with pytest.raises(BisibilityConfigurationError):
            client.update_project_defaults(
                F["project"], {**F["patch"], "review": {**REVIEW, "idempotency_key": key}}
            )


@pytest.mark.parametrize("field,value", [("policy_ready", "false"), ("expires_at", "invalid-date")])
def test_preview_rejects_invalid_response_types(field, value):
    from bisibility import ProjectDefaultsPreview

    with pytest.raises(ValidationError):
        ProjectDefaultsPreview.model_validate({**F["preview"], field: value})
