import asyncio
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from bisibility import (
    AsyncBisibilityClient,
    BisibilityClient,
    BisibilityResponseError,
    RankHistoryExportOptions,
    RankHistoryReportResponse,
)
from bisibility.models import ListMeta, PaginationOptions

FIXTURE = json.loads((Path(__file__).parent / "fixtures/rank-history-report.json").read_text())
PROJECT = "prj_abcdefghijklmnopqrstuvwx"
KEYWORD = "kw_abcdefghijklmnopqrstuvwx"


@pytest.mark.parametrize("stream", ["observations", "attempts", "full_attempts"])
def test_async_actual_report_roundtrip(stream: str) -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"data": [], "apiVersions": ["v1"]})
        requests.append(request)
        return httpx.Response(200, json=FIXTURE[stream])

    async def scenario() -> None:
        async with AsyncBisibilityClient(
            api_key="bsb_key_test_transport_fixture",
            base_url="https://api.example.com/api/v1",
            transport=httpx.MockTransport(handler),
        ) as client:
            result = await client.export_rank_history(
                PROJECT,
                RankHistoryExportOptions(
                    version="2",
                    stream="attempts" if "attempts" in stream else "observations",
                    basis="observed_at" if stream == "observations" else "recorded_at",
                    range="all",
                    keyword_ids=None if stream == "full_attempts" else [KEYWORD],
                ),
            )
        assert isinstance(result, RankHistoryReportResponse)
        assert result.model_dump(mode="json", by_alias=True) == FIXTURE[stream]

    asyncio.run(scenario())
    assert len(requests) == 1
    assert requests[0].url.params["version"] == "2"


@pytest.mark.parametrize("stream", ["observations", "recorded", "attempts", "full_attempts"])
def test_actual_report_fields_and_endpoint_owned_cursor(stream: str) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"data": [], "apiVersions": ["v1"]})
        requests.append(request)
        return httpx.Response(200, json=FIXTURE[stream])

    with BisibilityClient(
        api_key="bsb_key_test_transport_fixture",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    ) as client:
        options = RankHistoryExportOptions(
            version="2",
            stream="attempts" if "attempts" in stream else "observations",
            basis="observed_at" if stream == "observations" else "recorded_at",
            range="all",
            from_="1970-01-01T00:00:00Z",
            to="2026-10-12T12:00:00Z",
            aggregation="none",
            keyword_ids=None if stream == "full_attempts" else [KEYWORD],
            limit=1 if stream == "attempts" else 200,
        )
        result = client.export_rank_history(PROJECT, options)
    assert isinstance(result, RankHistoryReportResponse)
    assert result.model_dump(mode="json", by_alias=True) == FIXTURE[stream]
    assert len(requests) == 1
    assert requests[0].url.params["version"] == "2"
    assert requests[0].url.params["from"] == options.from_
    assert requests[0].url.params["to"] == options.to
    assert "cursor" not in requests[0].url.params
    assert requests[0].url.params.get("keyword_id") == (
        None if stream == "full_attempts" else KEYWORD
    )


def test_export_cursor_change_does_not_relax_other_v3_contracts() -> None:
    cursor = "opaque+/." * 512
    assert RankHistoryExportOptions(version="2", cursor=cursor).cursor == cursor
    for model in [PaginationOptions, RankHistoryExportOptions]:
        with pytest.raises(ValidationError):
            model.model_validate({"cursor": cursor})
    with pytest.raises(ValidationError):
        ListMeta.model_validate({"next_cursor": cursor})
    with pytest.raises(ValidationError):
        RankHistoryExportOptions(version="2", cursor="x" * 8193)


def test_all_actual_signed_pages_and_legacy_envelope() -> None:
    pages = iter(FIXTURE["attempt_pages"])
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"data": []})
        calls.append(request)
        return httpx.Response(200, json=next(pages))

    with BisibilityClient(
        api_key="bsb_key_test_transport_fixture",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    ) as client:
        cursor = None
        records = []
        while True:
            page = client.export_rank_history(
                PROJECT,
                RankHistoryExportOptions(
                    version="2",
                    stream="attempts",
                    range="all",
                    basis="recorded_at",
                    aggregation="none",
                    from_="1970-01-01T00:00:00Z",
                    to="2026-10-12T12:00:00Z",
                    keyword_ids=[KEYWORD],
                    limit=1,
                    cursor=cursor,
                ),
            )
            assert isinstance(page, RankHistoryReportResponse)
            records.extend(row.model_dump(mode="json", by_alias=True) for row in page.data)
            cursor = page.meta.next_cursor
            if cursor is None:
                break
    assert records == [row for page in FIXTURE["attempt_pages"] for row in page["data"]]
    assert len(calls) == len(FIXTURE["attempt_pages"])
    assert [call.url.params.get("cursor") for call in calls[1:]] == [
        page["meta"]["next_cursor"] for page in FIXTURE["attempt_pages"][:-1]
    ]


@pytest.mark.parametrize("name", ["csv_observations", "csv_attempts"])
def test_complete_actual_csv_manifest(name: str) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"data": []})
        requests.append(request)
        return httpx.Response(200, text=FIXTURE[name], headers={"content-type": "text/csv"})

    with BisibilityClient(
        api_key="bsb_key_test_transport_fixture",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.export_rank_history(
            PROJECT,
            RankHistoryExportOptions(
                version="2",
                format="csv",
                stream="attempts" if name == "csv_attempts" else "observations",
                basis="observed_at" if name == "csv_observations" else "recorded_at",
                range="all",
                from_="1970-01-01T00:00:00Z",
                to="2026-10-12T12:00:00Z",
                aggregation="none",
                keyword_ids=[KEYWORD] if name == "csv_observations" else None,
            ),
        )
    assert result == FIXTURE[name]
    assert requests[0].url.params["format"] == "csv"
    assert "cursor" not in requests[0].url.params


def test_numeric_cid_and_missing_run_authority_are_rejected() -> None:
    original = json.dumps(FIXTURE["observations"])
    assert '"cid": "18446744073709551615"' in original
    invalid = json.loads(
        original.replace('"cid": "18446744073709551615"', '"cid": 18446744073709551615')
    )
    with pytest.raises(ValidationError):
        RankHistoryReportResponse.model_validate(invalid)
    run = json.loads(json.dumps(FIXTURE["attempts"]))
    del run["data"][0]["run_id"]
    with pytest.raises(ValidationError):
        RankHistoryReportResponse.model_validate(run)
    with BisibilityClient(
        api_key="bsb_key_test_transport_fixture",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=invalid)),
    ) as client:
        with pytest.raises(BisibilityResponseError):
            client.export_rank_history(PROJECT, RankHistoryExportOptions(version="2"))


def test_future_output_metadata_preserves_shapes_and_versions() -> None:
    future = json.loads(json.dumps(FIXTURE["attempts"]))
    report = future["meta"]["report"]
    report["window"]["basis"] = "future_time_basis"
    report["summary_basis"] = "future_summary_basis"
    report["normalized_items"]["completeness"] = "future_retention"
    report["normalized_items"]["is_truncated"] = True
    parsed = RankHistoryReportResponse.model_validate(future)
    assert parsed.model_dump(mode="json", by_alias=True) == future
    report["version"] = 3
    with pytest.raises(ValidationError):
        RankHistoryReportResponse.model_validate(future)

@pytest.mark.parametrize("kind", [None, "future_record_kind", "observation", ""])
def test_report_kind_is_not_silently_reclassified(kind: str | None) -> None:
    payload = json.loads(json.dumps(FIXTURE["observations"]))
    payload["data"][0]["kind"] = kind
    with pytest.raises(ValidationError):
        RankHistoryReportResponse.model_validate(payload)
