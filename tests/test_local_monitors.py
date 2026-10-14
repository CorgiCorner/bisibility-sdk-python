import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from bisibility import (
    AsyncBisibilityClient,
    BisibilityApiError,
    BisibilityClient,
    LocalMonitorPointListingsResponse,
    LocalMonitorPointReport,
    LocalMonitorRunResultResponse,
)

FIXTURE = json.loads((Path(__file__).parent / "fixtures/local-monitor-transport.json").read_text())
PROJECT = "prj_abcdefghijklmnopqrstuvwx"
MONITOR = "lmn_abcdefghijklmnopqrstuvwx"
RUN = "lmr_abcdefghijklmnopqrstuvwx"
POINT = FIXTURE["result"]["data"]["points"][0]["id"]
AT = "2026-10-12T12:00:00.000Z"
CASES = [
    ("list_local_monitor_runs", [PROJECT, MONITOR], "history", "/runs"),
    (
        "get_local_monitor_run_result",
        [PROJECT, MONITOR, RUN],
        "result",
        "/runs/" + RUN + "/results",
    ),
    (
        "list_local_monitor_point_listings",
        [PROJECT, MONITOR, RUN, POINT],
        "listings",
        "/runs/" + RUN + "/points/" + POINT + "/listings",
    ),
    (
        "list_local_monitor_point_history",
        [PROJECT, MONITOR, RUN, POINT],
        "point_history",
        "/runs/" + RUN + "/points/" + POINT + "/history",
    ),
    (
        "export_local_monitor_run",
        [PROJECT, MONITOR, RUN],
        "export_json",
        "/runs/" + RUN + "/export",
    ),
]


@pytest.mark.parametrize("method,args,key,suffix", CASES)
@pytest.mark.parametrize("asynchronous", [False, True])
def test_actual_server_local_get_roundtrip(method, args, key, suffix, asynchronous):
    calls = []

    def handler(request):
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"data": [], "apiVersions": ["v1"]})
        calls.append(request)
        return httpx.Response(200, json=FIXTURE[key])

    options = {"as_of": AT}
    if key in ["history", "point_history"]:
        options.update({"from": "2026-10-12T00:00:00.000Z", "to": AT, "cursor": "opaque+cursor/="})
    kwargs = dict(
        api_key="bsb_key_test_fixture",
        base_url="https://api.example.com/api/v1",
        transport=httpx.MockTransport(handler),
    )
    if asynchronous:

        async def scenario():
            async with AsyncBisibilityClient(**kwargs) as client:
                return await getattr(client, method)(*args, options=options)

        result = asyncio.run(scenario())
    else:
        with BisibilityClient(**kwargs) as client:
            result = getattr(client, method)(*args, options=options)
    assert result.model_dump(mode="json", by_alias=True) == FIXTURE[key]
    assert len(calls) == 1
    assert calls[0].method == "GET"
    assert (
        calls[0].url.path == "/api/v1/projects/" + PROJECT + "/local-monitors/" + MONITOR + suffix
    )
    assert calls[0].url.params["as_of"] == AT
    assert calls[0].headers["Authorization"] == "Bearer bsb_key_test_fixture"
    if "cursor" in options:
        assert calls[0].url.params["cursor"] == options["cursor"]


@pytest.mark.parametrize("key", ["result_unknown", "result_stale"])
def test_unknown_and_stale_are_retained(key):
    model = LocalMonitorRunResultResponse.model_validate(FIXTURE[key])
    assert model.model_dump(mode="json", by_alias=True) == FIXTURE[key]
    assert model.data.freshness_policy.policy_epoch == "8"


@pytest.mark.parametrize(
    "options",
    [
        {"cursor": ""},
        {"cursor": "x" * 8001},
        {"cursor": "😀" * 4001},
        {"cursor": 42},
        {"as_of": "2026-10-12T12:00:00Z"},
        {"as_of": "2026-02-30T12:00:00.000Z"},
        {"from": AT, "to": "2026-10-12T00:00:00.000Z"},
        {"provider": "dataforseo"},
    ],
)
def test_invalid_selection_stops_before_http(options):
    calls = []
    with BisibilityClient(
        api_key="bsb_key_test_fixture", transport=httpx.MockTransport(lambda r: calls.append(r))
    ) as client:
        with pytest.raises((ValidationError, ValueError)):
            client.list_local_monitor_runs(PROJECT, MONITOR, options)
    assert calls == []


@pytest.mark.parametrize("index", range(4))
def test_foreign_or_internal_identifiers_stop_before_http(index):
    args = [PROJECT, MONITOR, RUN, POINT]
    args[index] = "kw_abcdefghijklmnopqrstuvwx"
    calls = []
    with BisibilityClient(
        api_key="bsb_key_test_fixture", transport=httpx.MockTransport(lambda r: calls.append(r))
    ) as client:
        with pytest.raises(ValueError):
            client.list_local_monitor_point_listings(*args)
    assert calls == []


def test_future_output_metadata_and_extra_fields_preserved():
    raw = copy.deepcopy(FIXTURE["result"])
    raw["data"]["freshness_policy"]["basis"] = "future_policy"
    raw["data"]["points"][0]["evidence"] = "future_evidence"
    raw["data"]["points"][0]["rank_scale"] = "finder_group"
    raw["data"]["future_field"] = {"value": 1}
    raw["data"]["grids"][0]["size"] = 9
    assert (
        LocalMonitorRunResultResponse.model_validate(raw).model_dump(mode="json", by_alias=True)
        == raw
    )


@pytest.mark.parametrize(
    "mutation",
    ["missing", "version", "foreign_id", "numeric_cid", "boolean_version", "boolean_ordinal"],
)
def test_invalid_output_is_rejected(mutation):
    raw = copy.deepcopy(FIXTURE["listings"] if mutation == "numeric_cid" else FIXTURE["result"])
    model = (
        LocalMonitorPointListingsResponse
        if mutation == "numeric_cid"
        else LocalMonitorRunResultResponse
    )
    if mutation == "numeric_cid":
        raw["data"][0]["cid"] = 1234567890123456789
    elif mutation == "missing":
        del raw["data"]["points"]
    elif mutation == "version":
        raw["data"]["version"] = 2
    elif mutation == "boolean_version":
        raw["data"]["version"] = True
    elif mutation == "boolean_ordinal":
        raw["data"]["points"][0]["ordinal"] = True
    else:
        raw["data"]["project_id"] = RUN
    with pytest.raises(ValidationError):
        model.model_validate(raw)


def test_csv_exact_and_input_version_strict():
    calls = []

    def handler(request):
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"data": [], "apiVersions": ["v1"]})
        calls.append(request)
        return httpx.Response(200, text=FIXTURE["export_csv"])

    with BisibilityClient(
        api_key="bsb_key_test_fixture", transport=httpx.MockTransport(handler)
    ) as client:
        assert (
            client.export_local_monitor_run(
                PROJECT, MONITOR, RUN, {"format": "csv", "version": "1"}
            )
            == FIXTURE["export_csv"]
        )
        with pytest.raises(ValidationError):
            client.export_local_monitor_run(PROJECT, MONITOR, RUN, {"version": "2"})
    assert len(calls) == 1 and calls[0].url.params["format"] == "csv"


@pytest.mark.parametrize("status", [401, 403])
def test_local_auth_refusal_never_retries_or_mutates(status):
    calls = []

    def handler(request):
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(200, json={"data": [], "apiVersions": ["v1"]})
        calls.append(request)
        return httpx.Response(status, json={"error": {"code": "forbidden", "message": "Denied"}})

    with BisibilityClient(
        api_key="bsb_key_test_fixture", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(BisibilityApiError) as error:
            client.get_local_monitor_run_result(PROJECT, MONITOR, RUN)
        assert error.value.status == status
    assert len(calls) == 1 and calls[0].method == "GET"


def test_exact_cursor_capacity_accepted():
    from bisibility import LocalMonitorHistoryOptions

    assert LocalMonitorHistoryOptions(cursor="😀" * 4000).cursor == "😀" * 4000


def test_subclass_options_cannot_smuggle_history_into_result():
    from bisibility import LocalMonitorHistoryOptions

    calls = []
    with BisibilityClient(
        api_key="bsb_key_test_fixture", transport=httpx.MockTransport(lambda r: calls.append(r))
    ) as client:
        with pytest.raises(ValidationError):
            client.get_local_monitor_run_result(
                PROJECT, MONITOR, RUN, LocalMonitorHistoryOptions(cursor="retained-token")
            )
    assert calls == []


@pytest.mark.parametrize("key", ["result", "export_json"])
def test_retained_fractional_zoom_read_contract(key):
    from bisibility import LocalMonitorPointReport

    raw = copy.deepcopy(FIXTURE[key])
    points = raw["data"]["points"] if key == "result" else raw["points"]
    points[0]["zoom"] = 5.5
    model = LocalMonitorRunResultResponse if key == "result" else LocalMonitorPointReport
    parsed = model.model_validate(raw)
    assert parsed.model_dump(mode="json", by_alias=True) == raw


@pytest.mark.parametrize("version", [True, 1.0, "1"])
def test_local_export_requires_exact_integer_response_version(version):
    raw = copy.deepcopy(FIXTURE["export_json"])
    raw["version"] = version
    with pytest.raises(ValidationError):
        LocalMonitorPointReport.model_validate(raw)

def test_local_listing_retains_finder_group_rank_scale():
    from bisibility.local_monitor_models_1 import LocalMonitorPointListingsResponse

    raw = copy.deepcopy(FIXTURE["listings"])
    raw["data"][0]["rank_scale"] = "finder_group"
    assert LocalMonitorPointListingsResponse.model_validate(raw).model_dump(mode="json") == raw
