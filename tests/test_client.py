from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from bisibility import (
    AddCompetitorInput,
    AlertRuleInput,
    ApiKeyCreateInput,
    BisibilityApiError,
    BisibilityClient,
    BisibilityConfigurationError,
    BisibilityError,
    BisibilityNetworkError,
    BisibilityResponseError,
    CloudImportPackage,
    CloudImportSessionCreate,
    ConnectProviderInput,
    CostEstimateOptions,
    CreateKeywordInput,
    CreateKeywordsBatch,
    CreateSavedViewInput,
    CreateSignalInput,
    CreateTeamInviteInput,
    KeywordBulkInput,
    KeywordMetricsInput,
    KeywordResearchOptions,
    KeywordSchedule,
    KeywordScheduleInput,
    ListKeywordsOptions,
    ListRankedKeywordSuggestionsOptions,
    ListSearchPerformanceQueryStatsOptions,
    ListSignalsOptions,
    ListTrafficSnapshotsOptions,
    MintMigrationTokenInput,
    NotificationPreferencesPatch,
    Project,
    ProjectDefaults,
    ProjectDefaultsPatch,
    ProviderCredentialsInput,
    RankHistoryExportOptions,
    RequestOptions,
    RunRankCheckInput,
    SavedViewConfig,
    SavedViewFilters,
    SearchLocationsOptions,
    SitemapMonitorPatch,
    UpdateKeywordInput,
    UpdateProjectInput,
    WebhookUpdateInput,
    create_bisibility_client,
)
from bisibility import (
    TestProviderConnectionInput as ProviderConnectionTestInput,
)

API_KEY = "bsk_live_1234567890abcdef"


def json_response(
    body: Any,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(status_code, json=body, headers=headers)


def text_response(
    body: str,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    merged = {"Content-Type": "text/plain; charset=utf-8", **(headers or {})}
    return httpx.Response(status_code, text=body, headers=merged)


def list_response(data: list[dict[str, Any]], next_cursor: str | None = None) -> dict[str, Any]:
    return {"data": data, "meta": {"next_cursor": next_cursor}}


def project(**overrides: Any) -> dict[str, Any]:
    return {
        "created_at": "2026-01-01T00:00:00.000Z",
        "domain": "example.com",
        "id": "prj_1",
        "name": "Example",
        "updated_at": "2026-01-02T00:00:00.000Z",
        "write_mode": "active",
        **overrides,
    }


def api_key_resource(**overrides: Any) -> dict[str, Any]:
    return {
        "created_at": "2026-01-01T00:00:00.000Z",
        "id": "key_1",
        "last_used_at": None,
        "name": "Production",
        "prefix": "bsk_live_12345678",
        "revoked_at": None,
        **overrides,
    }


def personal_token_resource(**overrides: Any) -> dict[str, Any]:
    return {
        "created_at": "2026-07-12T00:00:00.000Z",
        "expires_at": None,
        "id": "pat_1",
        "last_used_at": None,
        "name": "CLI",
        "prefix": "bsp_live_example",
        "revoked_at": None,
        "scope": "admin",
        **overrides,
    }


def webhook_resource(**overrides: Any) -> dict[str, Any]:
    return {
        "created_at": "2026-07-12T00:00:00.000Z",
        "description": "CI",
        "enabled": True,
        "id": "wh_1",
        "last_delivery_at": None,
        "updated_at": "2026-07-12T00:00:00.000Z",
        "url": "https://example.com/hook",
        **overrides,
    }


def project_defaults(**overrides: Any) -> dict[str, Any]:
    return {
        "city": None,
        "country": "United States",
        "cron_expression": None,
        "device": "desktop",
        "frequency": "daily",
        "jitter_minutes": 60,
        "last_checked_at": None,
        "location_key": "US",
        "next_check_at": "2026-01-05T00:00:00.000Z",
        "project_id": "prj_1",
        "serp_depth": 100,
        "serp_stop_on_match": True,
        "source": "explicit",
        "timezone": "UTC",
        "updated_at": "2026-01-04T00:00:00.000Z",
        **overrides,
    }


def keyword(**overrides: Any) -> dict[str, Any]:
    return {
        "country": "United States",
        "created_at": "2026-01-03T00:00:00.000Z",
        "device": "desktop",
        "id": "kw_1",
        "intent": None,
        "latest_position": 4,
        "location": "United States",
        "previous_position": 8,
        "project_id": "prj_1",
        "ranking_url": "https://example.com/page",
        "schedule": None,
        "tags": ["Product"],
        "target_url": "https://example.com/page",
        "text": "rank tracker",
        "topic": None,
        "updated_at": "2026-01-04T00:00:00.000Z",
        **overrides,
    }


def rank_check(**overrides: Any) -> dict[str, Any]:
    return {
        "attempts": None,
        "checked_at": "2026-01-06T00:00:00.000Z",
        "cost_cents": 0.06,
        "error": None,
        "id": "check_1",
        "keyword_id": "kw_1",
        "position": 4,
        "previous_position": 8,
        "provider": "dataforseo",
        "ranking_url": "https://example.com/page",
        "status": "completed",
        **overrides,
    }


def rank_history_export_row(**overrides: Any) -> dict[str, Any]:
    return {
        "checked_at": "2026-07-20T10:00:00.000Z",
        "id": "check_1",
        "keyword": "rank tracker",
        "keyword_id": "kw_1",
        "position": 4,
        "previous_position": 7,
        "ranking_url": "https://example.com/rank",
        **overrides,
    }


def alert_rule(**overrides: Any) -> dict[str, Any]:
    return {
        "channels": ["email"],
        "condition_type": "threshold",
        "enabled": True,
        "id": "rule_1",
        "name": "Ranking drop",
        "target_ids": [],
        "target_type": "all",
        "threshold_position": 10,
        **overrides,
    }


def triggered_alert(**overrides: Any) -> dict[str, Any]:
    return {
        "action": "Review the latest rank check.",
        "ctas": ["Open keyword"],
        "current": "#12",
        "headline": "Ranking drop",
        "id": "ta_1",
        "keyword": "rank tracker",
        "previous": "#4",
        "rule": "Ranking drop",
        "severity": "urgent",
        "unread": True,
        "when": "just now",
        **overrides,
    }


def sitemap_monitor(**overrides: Any) -> dict[str, Any]:
    return {
        "enabled": True,
        "id": "prj_1",
        "latest_snapshot": {
            "fetched_at": "2026-07-21T04:45:00.000Z",
            "id": "snapshot_1",
            "sitemap_url": "https://example.com/sitemap.xml",
            "url_count": 42,
        },
        "project_id": "prj_1",
        "sitemap_url": "https://example.com/sitemap.xml",
        "status": "active",
        **overrides,
    }


def team_member(**overrides: Any) -> dict[str, Any]:
    return {
        "color": "accent",
        "email": "owner@example.com",
        "id": "mem_1",
        "initials": "OE",
        "name": "Owner Example",
        "role": "Owner",
        "role_value": "owner",
        **overrides,
    }


def team_invite(**overrides: Any) -> dict[str, Any]:
    return {
        "email": "new@example.com",
        "expires_label": "expires in 6d",
        "id": "inv_1",
        "invited_label": "invited just now",
        "role": "Viewer",
        "role_value": "viewer",
        **overrides,
    }


def provider(**overrides: Any) -> dict[str, Any]:
    return {
        "description": "SerpAPI rank-data provider.",
        "drawer": {
            "activities": [{"label": "Last used", "value": "Never"}],
            "cost_help": "Provider billing remains direct.",
            "credential_fields": [
                {
                    "label": "API key",
                    "name": "secret",
                    "placeholder": "Stored in instance",
                    "type": "password",
                }
            ],
            "defaults": {
                "cost_per_check": 0.0,
                "enabled": True,
                "login": "",
                "primary": False,
                "priority": 100,
                "secret": "",
            },
            "env_hint": "Credentials can also be configured through environment variables.",
            "primary_toggle_label": "Set as primary serp provider",
        },
        "enabled": True,
        "icon": "globe",
        "id": "serpapi",
        "logo_domain": "serpapi.com",
        "meta": [{"label": "State", "value": "Enabled"}],
        "name": "SerpAPI",
        "primary": True,
        "priority": 0,
        "secondary_action": "Test",
        "status": "connected",
        "tint": "var(--accent)",
        **overrides,
    }


def provider_connection(**overrides: Any) -> dict[str, Any]:
    return {
        "cost_per_check_cents": 0.01,
        "created_at": "2026-01-01T00:00:00.000Z",
        "enabled": True,
        "id": "pc_1",
        "is_primary": False,
        "kind": "serp",
        "last_used_at": None,
        "priority": 100,
        "project_id": "prj_1",
        "provider": "serpapi",
        "status": "connected",
        "updated_at": "2026-01-02T00:00:00.000Z",
        **overrides,
    }


def saved_view(**overrides: Any) -> dict[str, Any]:
    return {
        "config": {
            "filters": {
                "change": "any",
                "contains": "",
                "country": "all",
                "device": "desktop",
                "position": ["top10"],
                "serp": [],
                "tags": ["Product"],
                "vol_max": 50,
                "vol_min": 0,
                "wrong_url": False,
            },
            "search": "rank",
        },
        "created_at": "2026-01-01T00:00:00.000Z",
        "created_by_id": "usr_1",
        "id": "view_1",
        "name": "Product desktop",
        **overrides,
    }


def competitor(**overrides: Any) -> dict[str, Any]:
    return {
        "domain": "rankzly.io",
        "id": "comp_1",
        "initials": "RI",
        "label": "Rankzly",
        **overrides,
    }


def competitor_market() -> dict[str, Any]:
    return {
        "checked_keyword_count": 1,
        "columns": [
            {"domain": "example.com", "kind": "You", "label": "example.com"},
            {"domain": "rankzly.io", "id": "comp_1", "kind": "Managed", "label": "Rankzly"},
        ],
        "competitor_count": 1,
        "country": "United States",
        "device": "Desktop",
        "engine": "Google",
        "has_rank_data": True,
        "key": "United States::Desktop::Google",
        "rows": [
            {
                "gap": -2,
                "keyword": "rank tracker",
                "ranks": {"example.com": 4, "rankzly.io": 2},
            }
        ],
        "shares": [
            {
                "color": "var(--accent)",
                "domain": "example.com",
                "initials": "EC",
                "kind": "You",
                "label": "example.com",
                "share_of_voice": 40,
                "shared_keywords": 1,
            }
        ],
        "shared_keyword_count": 1,
        "tracked_keyword_count": 1,
    }


def notification_preferences(**overrides: Any) -> dict[str, Any]:
    return {
        "alert_email": True,
        "alert_in_app": True,
        "alert_slack": False,
        "alert_webhook": False,
        "check_email": False,
        "check_in_app": True,
        "email": "owner@example.com",
        "email_verification": "verified",
        "import_email": True,
        "import_in_app": True,
        "invite_email": True,
        "invite_in_app": True,
        "project_id": "prj_1",
        "slack_available": False,
        "webhook_available": False,
        **overrides,
    }


def cloud_import_job(**overrides: Any) -> dict[str, Any]:
    return {
        "counts": None,
        "created_at": None,
        "error": None,
        "finished_at": None,
        "id": None,
        "progress": 0,
        "started_at": None,
        "state": "idle",
        **overrides,
    }


def migration_token(**overrides: Any) -> dict[str, Any]:
    return {
        "created_at": "2026-01-01T00:00:00.000Z",
        "created_by": {"email": "owner@example.com", "name": "Owner Example"},
        "expires_at": "2026-01-01T01:00:00.000Z",
        "id": "tok_1",
        "scope": "full",
        "single_use": True,
        **overrides,
    }


def signal(**overrides: Any) -> dict[str, Any]:
    return {
        "created_at": "2026-07-04T19:31:00.000Z",
        "happened_at": "2026-07-04T19:30:00.000Z",
        "id": "sig_1",
        "keyword_id": "kw_1",
        "payload": {"version": "1.2.3"},
        "project_id": "prj_1",
        "public_id": "sig_1",
        "severity": "warning",
        "source": "deploy",
        "type": "deploy.completed",
        "url": "https://example.com/releases/1",
        **overrides,
    }


def flat_provider_rate(**overrides: Any) -> dict[str, Any]:
    return {
        "checked_at": "2026-06-01",
        "label": "DataForSEO",
        "notes": "Pay as you go.",
        "options": [
            {
                "key": "standard",
                "label": "Standard queue",
                "short_label": "Standard",
                "turnaround": "~5 min",
                "unit_cost_cents": 0.06,
                "unit_cost_usd": 0.0006,
            }
        ],
        "pricing_model": "flat",
        "provider_id": "dataforseo",
        "source_url": "https://dataforseo.com/pricing",
        **overrides,
    }


def plan_provider_rate(**overrides: Any) -> dict[str, Any]:
    return {
        "checked_at": "2026-06-01",
        "label": "SerpAPI",
        "plans": [
            {
                "included_checks": 5000,
                "label": "Developer",
                "monthly_price_cents": 7500,
                "monthly_price_usd": 75,
                "plan_key": "developer",
            }
        ],
        "pricing_model": "plan",
        "provider_id": "serpapi",
        "source_url": "https://serpapi.com/pricing",
        **overrides,
    }


def cost_estimate(**overrides: Any) -> dict[str, Any]:
    return {
        "checks_per_run": 248,
        "effective_cost_per_check_cents": 0.06,
        "exceeds_largest_plan": False,
        "exceeds_selected_plan": False,
        "monthly_checks": 7440,
        "monthly_cost_cents": 446.4,
        "monthly_cost_usd": 4.464,
        "pricing_model": "flat",
        "provider_id": "dataforseo",
        "rate_checked_at": "2026-06-01",
        "rate_source_url": "https://dataforseo.com/pricing",
        "selected_option": {
            "key": "standard",
            "label": "Standard queue",
            "short_label": "Standard",
            "turnaround": "~5 min",
            "unit_cost_cents": 0.06,
            "unit_cost_usd": 0.0006,
        },
        **overrides,
    }


TransportItem = httpx.Response | BaseException | Callable[[httpx.Request], httpx.Response]


@dataclass
class QueueTransport:
    items: list[TransportItem]
    requests: list[httpx.Request] = field(default_factory=list)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self.items:
            raise AssertionError(f"Unexpected request: {request.method} {request.url}")
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        response = item(request) if callable(item) else item
        response.request = request
        return response


def make_client(queue: QueueTransport, **options: Any) -> BisibilityClient:
    return BisibilityClient(
        api_key=API_KEY,
        base_url="https://api.test/api/v1/",
        transport=queue.transport(),
        **options,
    )


def request_json(request: httpx.Request) -> Any:
    return httpx.Response(200, request=request, content=request.content).json()


def test_discovery_methods_do_not_require_auth() -> None:
    capability = {
        "description": "Add one or more keywords",
        "input_schema": {"type": "object"},
        "name": "addKeywords",
        "operationId": "addKeywords",
    }
    queue = QueueTransport(
        [
            json_response(
                {
                    "checked_at": "2026-01-01T00:00:00.000Z",
                    "providers": {"serp": ["dataforseo"]},
                    "services": {"app": "ok", "database": "ok"},
                    "status": "ok",
                }
            ),
            json_response({"info": {"title": "Bisibility"}, "openapi": "3.1.0", "paths": {}}),
            json_response({"data": [capability]}),
            text_response("# Bisibility API v1"),
        ]
    )
    client = BisibilityClient(base_url="https://api.test/api/v1/", transport=queue.transport())

    assert client.get_health().status == "ok"
    assert client.get_open_api().openapi == "3.1.0"
    assert client.get_capabilities().data[0].name == "addKeywords"
    assert client.get_llms_text() == "# Bisibility API v1"

    assert [str(request.url) for request in queue.requests] == [
        "https://api.test/api/v1/health",
        "https://api.test/api/v1/openapi.json",
        "https://api.test/api/v1/capabilities",
        "https://api.test/api/v1/llms.txt",
    ]
    assert all("Authorization" not in request.headers for request in queue.requests)


def test_public_cost_methods_do_not_require_auth() -> None:
    queue = QueueTransport(
        [
            json_response({"data": [flat_provider_rate(), plan_provider_rate()]}),
            json_response({"data": cost_estimate()}),
        ]
    )
    client = BisibilityClient(base_url="https://api.test/api/v1/", transport=queue.transport())

    rates = client.get_provider_rates()
    assert rates.data[0].provider_id == "dataforseo"
    assert rates.data[0].pricing_model == "flat"
    assert rates.data[0].options is not None
    assert rates.data[0].options[0].key == "standard"
    assert rates.data[0].options[0].unit_cost_usd == 0.0006
    assert rates.data[1].pricing_model == "plan"
    assert rates.data[1].plans is not None
    assert rates.data[1].plans[0].plan_key == "developer"
    assert rates.data[1].plans[0].included_checks == 5000
    assert rates.data[1].notes is None

    estimate = client.get_cost_estimate(
        CostEstimateOptions(
            devices=1,
            frequency="daily",
            keywords=248,
            locations=1,
            option="standard",
            provider="dataforseo",
        )
    )
    assert estimate.data.checks_per_run == 248
    assert estimate.data.monthly_checks == 7440
    assert estimate.data.monthly_cost_usd == 4.464
    assert estimate.data.selected_option is not None
    assert estimate.data.selected_option.short_label == "Standard"
    assert estimate.data.selected_plan is None

    assert str(queue.requests[0].url) == "https://api.test/api/v1/provider-rates"
    assert str(queue.requests[1].url) == (
        "https://api.test/api/v1/cost-estimate?"
        "devices=1&frequency=daily&keywords=248&locations=1&option=standard&provider=dataforseo"
    )
    assert all("Authorization" not in request.headers for request in queue.requests)


def test_estimates_plan_provider_cost_from_mapping_options() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "data": cost_estimate(
                        checks_per_run=50,
                        exceeds_selected_plan=True,
                        monthly_checks=1500,
                        monthly_cost_cents=2500,
                        monthly_cost_usd=25,
                        pricing_model="plan",
                        provider_id="serpapi",
                        rate_source_url="https://serpapi.com/pricing",
                        selected_option=None,
                        selected_plan={
                            "included_checks": 1000,
                            "label": "Starter",
                            "monthly_price_cents": 2500,
                            "monthly_price_usd": 25,
                            "plan_key": "starter",
                        },
                    )
                }
            )
        ]
    )
    client = make_client(queue)

    estimate = client.get_cost_estimate({"keywords": 50, "plan": "starter", "provider": "serpapi"})

    assert estimate.data.exceeds_selected_plan is True
    assert estimate.data.selected_plan is not None
    assert estimate.data.selected_plan.plan_key == "starter"
    assert estimate.data.selected_option is None
    assert str(queue.requests[-1].url) == (
        "https://api.test/api/v1/cost-estimate?keywords=50&plan=starter&provider=serpapi"
    )


def test_searches_canonical_locations() -> None:
    queue = QueueTransport(
        [
            json_response(
                list_response(
                    [
                        {
                            "city_name": "Austin",
                            "country_code": "US",
                            "display_name": "Austin, Texas, United States",
                            "hl": "en",
                            "id": "loc_1",
                            "kind": "city",
                            "language_label": "English",
                            "location_key": "US/Texas/Austin",
                            "region_code": "TX",
                            "region_name": "Texas",
                        }
                    ]
                )
            )
        ]
    )
    client = make_client(queue)

    result = client.search_locations(SearchLocationsOptions(country="US", limit=10, q="Austin"))

    assert result.data[0].location_key == "US/Texas/Austin"
    assert result.data[0].kind == "city"
    assert str(queue.requests[-1].url) == (
        "https://api.test/api/v1/locations/search?country=US&limit=10&q=Austin"
    )


def test_mirrored_openapi_enums_accept_current_values_and_reject_provider_drift() -> None:
    assert Project.model_validate(project(write_mode="migrated")).write_mode == "migrated"
    assert (
        ProjectDefaults.model_validate(project_defaults(frequency="monthly")).frequency == "monthly"
    )
    assert CostEstimateOptions(keywords=10, provider="serpapi").provider == "serpapi"

    with pytest.raises(ValidationError):
        CostEstimateOptions(keywords=10, provider="ga4")


def test_project_defaults_and_keyword_schedule_models_match_openapi_field_sets() -> None:
    assert set(ProjectDefaults.model_fields) == {
        "city",
        "country",
        "cron_expression",
        "device",
        "frequency",
        "jitter_minutes",
        "last_checked_at",
        "location_key",
        "next_check_at",
        "project_id",
        "serp_depth",
        "serp_stop_on_match",
        "source",
        "timezone",
        "updated_at",
    }
    assert set(ProjectDefaultsPatch.model_fields) == {
        "city",
        "country",
        "cron_expression",
        "device",
        "frequency",
        "jitter_minutes",
        "location_key",
        "serp_stop_on_match",
        "timezone",
    }
    assert set(KeywordSchedule.model_fields) == {
        "cron_expression",
        "frequency",
        "jitter_minutes",
        "last_checked_at",
        "next_check_at",
        "timezone",
    }
    assert set(KeywordScheduleInput.model_fields) == {
        "cron_expression",
        "frequency",
        "jitter_minutes",
        "timezone",
    }


def test_project_defaults_rejects_unknown_source() -> None:
    with pytest.raises(ValidationError):
        ProjectDefaults.model_validate(project_defaults(source="guessed"))


def test_sends_bearer_auth_and_default_headers_on_protected_requests() -> None:
    queue = QueueTransport([json_response(list_response([project()]))])
    client = make_client(queue, headers={"X-Client": "sdk-test"})

    result = client.list_projects(RequestOptions(headers={"X-Request": "request"}))

    request = queue.requests[-1]
    assert result.data[0].id == "prj_1"
    assert request.method == "GET"
    assert str(request.url) == "https://api.test/api/v1/projects"
    assert request.headers["Authorization"] == f"Bearer {API_KEY}"
    assert request.headers["X-Client"] == "sdk-test"
    assert request.headers["X-Request"] == "request"
    assert request.headers["User-Agent"] == "bisibility-sdk-python/0.2.1"
    assert request.headers["X-Bisibility-Client"] == "bisibility-sdk-python/0.2.1"
    assert request.extensions["timeout"] == {
        "connect": 30.0,
        "read": 30.0,
        "write": 30.0,
        "pool": 30.0,
    }


def test_preserves_user_agent_and_allows_disabling_timeout() -> None:
    queue = QueueTransport([json_response(list_response([project()]))])
    client = make_client(queue, headers={"User-Agent": "my-app/1.0"})

    client.list_projects(RequestOptions(timeout=None))

    request = queue.requests[-1]
    assert request.headers["User-Agent"] == "my-app/1.0"
    assert request.headers["X-Bisibility-Client"] == "bisibility-sdk-python/0.2.1"
    assert request.extensions["timeout"] == {
        "connect": None,
        "read": None,
        "write": None,
        "pool": None,
    }


@pytest.mark.parametrize(
    ("method_name", "args", "resource_factory", "options", "expected_ids"),
    [
        (
            "iter_api_keys",
            (),
            lambda page: api_key_resource(id=f"key_{page}"),
            {"limit": 1},
            ["key_1", "key_2"],
        ),
        (
            "iter_project_api_keys",
            ("prj_1",),
            lambda page: api_key_resource(id=f"key_{page}"),
            {"limit": 1},
            ["key_1", "key_2"],
        ),
        (
            "iter_webhooks",
            ("prj_1",),
            lambda page: webhook_resource(id=f"wh_{page}"),
            {"limit": 1},
            ["wh_1", "wh_2"],
        ),
        (
            "iter_keywords",
            ("prj_1",),
            lambda page: keyword(id=f"kw_{page}"),
            {"limit": 1, "search": "rank tracker"},
            ["kw_1", "kw_2"],
        ),
        (
            "iter_rank_checks",
            ("kw_1",),
            lambda page: rank_check(id=f"check_{page}"),
            {"limit": 1},
            ["check_1", "check_2"],
        ),
        (
            "iter_project_signals",
            ("prj_1",),
            lambda page: signal(id=f"sig_{page}", public_id=f"sig_{page}"),
            {"limit": 1, "source": "deploy"},
            ["sig_1", "sig_2"],
        ),
        (
            "iter_alert_rules",
            ("prj_1",),
            lambda page: alert_rule(id=f"rule_{page}"),
            {"limit": 1},
            ["rule_1", "rule_2"],
        ),
        (
            "iter_triggered_alerts",
            ("prj_1",),
            lambda page: triggered_alert(id=f"ta_{page}"),
            {"limit": 1},
            ["ta_1", "ta_2"],
        ),
        (
            "iter_team_members",
            ("prj_1",),
            lambda page: team_member(id=f"mem_{page}"),
            {"limit": 1},
            ["mem_1", "mem_2"],
        ),
        (
            "iter_team_invites",
            ("prj_1",),
            lambda page: team_invite(id=f"inv_{page}"),
            {"limit": 1},
            ["inv_1", "inv_2"],
        ),
        (
            "iter_providers",
            ("prj_1",),
            lambda page: provider(id="serpapi" if page == 1 else "dataforseo"),
            {"limit": 1},
            ["serpapi", "dataforseo"],
        ),
        (
            "iter_saved_views",
            ("prj_1",),
            lambda page: saved_view(id=f"view_{page}"),
            {"limit": 1},
            ["view_1", "view_2"],
        ),
        (
            "iter_competitors",
            ("prj_1",),
            lambda page: competitor(id=f"comp_{page}"),
            {"limit": 1},
            ["comp_1", "comp_2"],
        ),
        (
            "iter_migration_tokens",
            ("prj_1",),
            lambda page: migration_token(id=f"tok_{page}"),
            {"limit": 1},
            ["tok_1", "tok_2"],
        ),
    ],
)
def test_cursor_iterators_fetch_all_pages_and_preserve_options(
    method_name: str,
    args: tuple[str, ...],
    resource_factory: Callable[[int], dict[str, Any]],
    options: dict[str, Any],
    expected_ids: list[str],
) -> None:
    queue = QueueTransport(
        [
            json_response(list_response([resource_factory(1)], "next_1")),
            json_response(list_response([resource_factory(2)])),
        ]
    )
    client = make_client(queue)

    resources = list(getattr(client, method_name)(*args, options))

    assert [resource.id for resource in resources] == expected_ids
    assert queue.requests[0].url.params.get("limit") == "1"
    assert queue.requests[0].url.params.get("cursor") is None
    assert queue.requests[1].url.params.get("limit") == "1"
    assert queue.requests[1].url.params.get("cursor") == "next_1"
    if "search" in options:
        assert all(request.url.params.get("search") == "rank tracker" for request in queue.requests)
    if "source" in options:
        assert all(request.url.params.get("source") == "deploy" for request in queue.requests)


def test_uses_default_base_url_and_accepts_url_objects() -> None:
    queue = QueueTransport(
        [
            json_response(list_response([project()])),
            json_response(list_response([project()])),
        ]
    )
    default_client = BisibilityClient(api_key=API_KEY, transport=queue.transport())
    url_client = BisibilityClient(
        api_key=API_KEY,
        base_url=httpx.URL("https://api.test/api/v1/"),
        transport=queue.transport(),
    )

    default_client.list_projects()
    url_client.list_projects()

    assert str(queue.requests[0].url) == "https://bisibility.com/api/v1/projects"
    assert str(queue.requests[1].url) == "https://api.test/api/v1/projects"


def test_lists_and_gets_projects() -> None:
    queue = QueueTransport(
        [
            json_response(list_response([project()])),
            json_response(project(id="prj spaced")),
        ]
    )
    client = make_client(queue)

    assert client.list_projects().data[0].domain == "example.com"
    assert client.get_project("prj spaced").id == "prj spaced"

    assert str(queue.requests[0].url) == "https://api.test/api/v1/projects"
    assert str(queue.requests[1].url) == "https://api.test/api/v1/projects/prj%20spaced"


def test_personal_project_header_and_request_override() -> None:
    queue = QueueTransport([json_response(keyword()), json_response(keyword())])
    client = make_client(queue, project_id="prj_default")

    client.get_keyword("kw_1")
    client.get_keyword("kw_1", RequestOptions(headers={"X-Bisibility-Project": "prj_override"}))

    assert queue.requests[0].headers["X-Bisibility-Project"] == "prj_default"
    assert queue.requests[1].headers["X-Bisibility-Project"] == "prj_override"


def test_profile_personal_tokens_and_project_creation() -> None:
    me = {
        "email": "owner@example.com",
        "id": "user_1",
        "name": "Owner",
        "projects": [{"domain": "example.com", "id": "prj_1", "name": "Example", "role": "owner"}],
    }
    issued = {
        **personal_token_resource(),
        "masked_value": "bsp_live_example******abcd",
        "token": "bsp_live_raw",
    }
    queue = QueueTransport(
        [
            json_response(me),
            json_response({**me, "name": "Renamed"}),
            json_response(list_response([personal_token_resource()])),
            json_response(issued, 201),
            json_response(personal_token_resource(revoked_at="2026-07-12T01:00:00.000Z")),
            json_response(project(), 201),
        ]
    )
    client = make_client(queue)

    assert client.get_me().email == "owner@example.com"
    assert client.update_me({"name": "Renamed"}).name == "Renamed"
    assert client.list_my_tokens().data[0].id == "pat_1"
    assert (
        client.create_my_token({"name": "CLI", "scope": "admin", "expires_in_days": 90}).token
        == "bsp_live_raw"
    )
    assert client.revoke_my_token("current").revoked_at is not None
    assert client.create_project({"domain": "example.com", "name": "Example"}).id == "prj_1"

    assert [str(request.url) for request in queue.requests] == [
        "https://api.test/api/v1/me",
        "https://api.test/api/v1/me",
        "https://api.test/api/v1/me/tokens",
        "https://api.test/api/v1/me/tokens",
        "https://api.test/api/v1/me/tokens/current",
        "https://api.test/api/v1/projects",
    ]
    assert request_json(queue.requests[3]) == {
        "expires_in_days": 90,
        "name": "CLI",
        "scope": "admin",
    }


def test_project_api_keys_and_webhook_crud() -> None:
    issued_key = {
        **api_key_resource(id="key_ci", name="CI"),
        "masked_value": "bsk_live_12345678******cdef",
        "token": API_KEY,
    }
    queue = QueueTransport(
        [
            json_response(list_response([api_key_resource()])),
            json_response(issued_key, 201),
            json_response(list_response([webhook_resource()])),
            json_response(webhook_resource(), 201),
            json_response(webhook_resource(enabled=False)),
            json_response(webhook_resource(enabled=False)),
        ]
    )
    client = make_client(queue)

    assert client.list_project_api_keys("prj_1").data[0].id == "key_1"
    assert client.create_project_api_key("prj_1", {"name": "CI"}).id == "key_ci"
    assert client.list_webhooks("prj_1").data[0].id == "wh_1"
    assert (
        client.create_webhook(
            "prj_1",
            {"hmac_secret": "1234567890123456", "url": "https://example.com/hook"},
        ).id
        == "wh_1"
    )
    assert client.update_webhook("prj_1", "wh_1", {"enabled": False}).enabled is False
    assert client.delete_webhook("prj_1", "wh_1").enabled is False

    assert [str(request.url) for request in queue.requests] == [
        "https://api.test/api/v1/projects/prj_1/api-keys",
        "https://api.test/api/v1/projects/prj_1/api-keys",
        "https://api.test/api/v1/projects/prj_1/webhooks",
        "https://api.test/api/v1/projects/prj_1/webhooks",
        "https://api.test/api/v1/projects/prj_1/webhooks/wh_1",
        "https://api.test/api/v1/projects/prj_1/webhooks/wh_1",
    ]


@pytest.mark.parametrize("hmac_secret", [None, "", "   "])
def test_webhook_update_rejects_null_or_blank_hmac_secret(
    hmac_secret: str | None,
) -> None:
    with pytest.raises(
        ValidationError,
        match="hmac_secret must be a non-empty string when provided",
    ):
        WebhookUpdateInput(hmac_secret=hmac_secret)


def test_webhook_update_accepts_non_empty_hmac_secret() -> None:
    update = WebhookUpdateInput(hmac_secret="rotated-secret")

    assert update.model_dump(exclude_unset=True) == {"hmac_secret": "rotated-secret"}


def test_webhook_update_omits_unset_hmac_secret_from_request_body() -> None:
    queue = QueueTransport([json_response(webhook_resource(enabled=False))])
    client = make_client(queue)

    update = WebhookUpdateInput(enabled=False)
    assert client.update_webhook("prj_1", "wh_1", update).enabled is False

    assert request_json(queue.requests[0]) == {"enabled": False}


def test_project_exposes_write_mode() -> None:
    queue = QueueTransport(
        [
            json_response(project()),
            json_response(project(write_mode="migration_hold")),
        ]
    )
    client = make_client(queue)

    assert client.get_project("prj_1").write_mode == "active"
    assert client.get_project("prj_1").write_mode == "migration_hold"


def test_updates_and_deletes_project() -> None:
    queue = QueueTransport(
        [
            json_response(project(name="Renamed")),
            json_response(project(domain="renamed.example.com")),
            json_response(project()),
        ]
    )
    client = make_client(queue)

    assert client.update_project("prj_1", UpdateProjectInput(name="Renamed")).name == "Renamed"
    assert (
        client.update_project("prj_1", {"domain": "renamed.example.com"}).domain
        == "renamed.example.com"
    )
    assert client.delete_project("prj_1").id == "prj_1"

    assert str(queue.requests[0].url) == "https://api.test/api/v1/projects/prj_1"
    assert queue.requests[0].method == "PATCH"
    assert request_json(queue.requests[0]) == {"name": "Renamed"}
    assert request_json(queue.requests[1]) == {"domain": "renamed.example.com"}
    assert queue.requests[2].method == "DELETE"
    assert str(queue.requests[2].url) == "https://api.test/api/v1/projects/prj_1"


def test_updates_project_defaults() -> None:
    queue = QueueTransport(
        [
            json_response(project_defaults(frequency="weekly")),
            json_response(project_defaults(city="Austin", location_key="US/Texas/Austin")),
        ]
    )
    client = make_client(queue)

    updated = client.update_project_defaults(
        "prj_1",
        ProjectDefaultsPatch(frequency="weekly", jitter_minutes=30, timezone="UTC"),
    )
    assert updated.frequency == "weekly"
    assert updated.project_id == "prj_1"
    moved = client.update_project_defaults("prj_1", {"location_key": "US/Texas/Austin"})
    assert moved.city == "Austin"
    assert moved.location_key == "US/Texas/Austin"

    assert str(queue.requests[0].url) == "https://api.test/api/v1/projects/prj_1/defaults"
    assert queue.requests[0].method == "PATCH"
    assert request_json(queue.requests[0]) == {
        "frequency": "weekly",
        "jitter_minutes": 30,
        "timezone": "UTC",
    }
    assert request_json(queue.requests[1]) == {"location_key": "US/Texas/Austin"}


def test_gets_project_defaults() -> None:
    response = project_defaults(
        city="Austin",
        last_checked_at="2026-01-03T00:00:00.000Z",
        location_key="US/Texas/Austin",
        serp_depth=50,
        serp_stop_on_match=False,
        source="explicit",
    )
    queue = QueueTransport([json_response(response)])
    client = make_client(queue)

    defaults = client.get_project_defaults("prj spaced/1")

    assert defaults.model_dump() == response
    assert defaults.source == "explicit"
    assert queue.requests[0].method == "GET"
    assert (
        str(queue.requests[0].url)
        == "https://api.test/api/v1/projects/prj%20spaced%2F1/defaults"
    )


def test_get_project_defaults_maps_forbidden() -> None:
    problem = {
        "detail": "API key scope does not allow this operation.",
        "status": 403,
        "title": "Forbidden",
        "type": "https://bisibility.dev/problems/forbidden",
    }
    queue = QueueTransport(
        [json_response(problem, 403, {"Content-Type": "application/problem+json"})]
    )
    client = make_client(queue)

    with pytest.raises(BisibilityApiError) as exc_info:
        client.get_project_defaults("prj_1")

    assert exc_info.value.status == 403
    assert exc_info.value.problem is not None
    assert exc_info.value.problem.title == "Forbidden"
    assert (
        exc_info.value.url == "https://api.test/api/v1/projects/prj_1/defaults"
    )


def test_lists_creates_and_revokes_api_keys() -> None:
    created = {
        **api_key_resource(id="key_new", name="CI"),
        "masked_value": "bsk_live_12345678******cdef",
        "token": API_KEY,
    }
    queue = QueueTransport(
        [
            json_response(list_response([api_key_resource()], "cursor_1")),
            json_response(created, 201),
            json_response(api_key_resource(revoked_at="2026-01-03T00:00:00.000Z")),
        ]
    )
    client = make_client(queue)

    assert client.list_api_keys({"cursor": "cursor 1", "limit": 10}).meta.next_cursor == "cursor_1"
    assert (
        client.create_api_key(
            {"name": "CI"},
            request_options=RequestOptions(idempotency_key="idem_1"),
        ).token
        == API_KEY
    )
    assert client.revoke_api_key("key_1").revoked_at == "2026-01-03T00:00:00.000Z"

    assert str(queue.requests[0].url) == "https://api.test/api/v1/api-keys?cursor=cursor+1&limit=10"
    assert queue.requests[1].method == "POST"
    assert queue.requests[1].headers["Idempotency-Key"] == "idem_1"
    assert request_json(queue.requests[1]) == {"name": "CI"}
    assert queue.requests[2].method == "DELETE"
    assert str(queue.requests[2].url) == "https://api.test/api/v1/api-keys/key_1"


def test_creates_api_key_with_typed_input() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    **api_key_resource(id="key_new", name="CI"),
                    "masked_value": "bsk_live_12345678******cdef",
                    "token": API_KEY,
                },
                201,
            )
        ]
    )
    client = make_client(queue)

    assert client.create_api_key(ApiKeyCreateInput(name="CI")).id == "key_new"
    assert request_json(queue.requests[-1]) == {"name": "CI"}


def test_preserves_explicit_content_type_and_request_timeout() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    **api_key_resource(id="key_new", name="CI"),
                    "masked_value": "bsk_live_12345678******cdef",
                    "token": API_KEY,
                },
                201,
            )
        ]
    )
    client = make_client(queue)

    client.create_api_key(
        {"name": "CI"},
        request_options={
            "headers": {"Content-Type": "application/vnd.bisibility+json"},
            "timeout": 3.0,
        },
    )

    assert queue.requests[-1].headers["Content-Type"] == "application/vnd.bisibility+json"


def test_lists_keywords_with_all_supported_filters() -> None:
    queue = QueueTransport([json_response(list_response([keyword()], "next_1"))])
    client = make_client(queue)

    result = client.list_keywords(
        "prj_1",
        ListKeywordsOptions(
            country="United States",
            cursor="cursor_1",
            device="desktop",
            intent="transactional",
            limit=25,
            position_gt=3,
            position_lt=10,
            search="rank tracker",
            sort="-updated_at",
            tag="Product",
            topic="Pricing",
        ),
    )

    assert result.data[0].text == "rank tracker"
    assert str(queue.requests[-1].url) == (
        "https://api.test/api/v1/projects/prj_1/keywords?"
        "cursor=cursor_1&filter%5Bcountry%5D=United+States&filter%5Bdevice%5D=desktop&"
        "filter%5Bintent%5D=transactional&"
        "filter%5Bposition_gt%5D=3&filter%5Bposition_lt%5D=10&filter%5Btag%5D=Product&"
        "filter%5Btopic%5D=Pricing&"
        "limit=25&search=rank+tracker&sort=-updated_at"
    )


def test_lists_ranked_keyword_suggestions_with_paid_cache_metadata() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "cached": False,
                    "connections": [
                        {"id": "connection_1", "label": "DataForSEO", "provider": "dataforseo"}
                    ],
                    "cost_cents": 2,
                    "fetched_at": "2026-07-22T10:00:00.000Z",
                    "offset": 100,
                    "rows": [
                        {
                            "already_tracked": True,
                            "estimated_traffic": 61.2,
                            "keyword": "rank tracker api",
                            "position": 4,
                            "search_volume": 720,
                        }
                    ],
                    "total_count": 184,
                }
            )
        ]
    )
    client = make_client(queue)

    result = client.list_ranked_keyword_suggestions(
        "prj_1",
        ListRankedKeywordSuggestionsOptions(
            connection_id="connection_1",
            fresh=True,
            limit=100,
            offset=100,
        ),
    )

    assert result.cached is False
    assert result.cost_cents == 2
    assert result.rows[0].already_tracked is True
    assert result.rows[0].estimated_traffic == 61.2
    assert str(queue.requests[-1].url) == (
        "https://api.test/api/v1/projects/prj_1/ranked-keyword-suggestions?"
        "connection_id=connection_1&fresh=true&limit=100&offset=100"
    )


def test_researches_keywords_with_partial_source_diagnostics_and_cost_options() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "cached": False,
                    "connections": [
                        {"id": "connection_1", "label": "DataForSEO", "provider": "dataforseo"}
                    ],
                    "cost_cents": 1.6,
                    "fetched_at": "2026-07-22T10:00:00.000Z",
                    "provider": "DataForSEO",
                    "rows": [
                        {
                            "already_tracked": True,
                            "competition": None,
                            "cpc_cents": None,
                            "difficulty": None,
                            "intent": None,
                            "keyword": "rank tracker api",
                            "monthly_trend": [{"month": 6, "search_volume": None, "year": 2026}],
                            "search_volume": None,
                            "source": "related",
                        }
                    ],
                    "sources": [
                        {
                            "cached": False,
                            "cost_cents": 1.6,
                            "returned": 1,
                            "source": "related",
                            "status": "ok",
                        },
                        {
                            "cached": False,
                            "cost_cents": 0,
                            "reason": "budget_exhausted",
                            "returned": 0,
                            "source": "suggestion",
                            "status": "failed",
                        },
                        {
                            "cached": False,
                            "cost_cents": 0,
                            "reason": "previous_source_failed",
                            "returned": 0,
                            "source": "idea",
                            "status": "skipped",
                        },
                    ],
                    "total_count": 1,
                }
            )
        ]
    )
    client = make_client(queue)

    result = client.research_keywords(
        "prj spaced",
        KeywordResearchOptions(
            connection_id="connection_1",
            estimate_only=False,
            fresh=True,
            include_clickstream=True,
            max_cost_cents=7,
            mode="auto",
            result_limit=300,
            seed="rank tracker",
        ),
    )

    assert result.cached is False
    assert result.provider == "DataForSEO"
    assert result.rows[0].source == "related"
    assert result.rows[0].already_tracked is True
    assert result.rows[0].difficulty is None
    assert result.rows[0].monthly_trend[0].search_volume is None
    assert result.sources[0].status == "ok"
    assert result.sources[1].status == "failed"
    assert result.sources[1].reason == "budget_exhausted"
    assert result.sources[2].status == "skipped"
    assert result.sources[2].reason == "previous_source_failed"
    assert str(queue.requests[-1].url) == (
        "https://api.test/api/v1/projects/prj%20spaced/keyword-research?"
        "connection_id=connection_1&estimate_only=false&fresh=true&include_clickstream=true&"
        "max_cost_cents=7&mode=auto&result_limit=300&seed=rank+tracker"
    )


def test_maps_keyword_research_estimate_response() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "cached": False,
                    "connections": [
                        {"id": "connection_1", "label": "DataForSEO", "provider": "dataforseo"}
                    ],
                    "cost_cents": 0,
                    "estimate": True,
                    "fetched_at": "2026-07-22T10:00:00.000Z",
                    "provider": "DataForSEO",
                    "rows": [],
                    "sources": [
                        {
                            "cached": True,
                            "cost_cents": 0,
                            "returned": 0,
                            "source": "related",
                            "status": "ok",
                        },
                        {
                            "cached": False,
                            "cost_cents": 1.01,
                            "returned": 0,
                            "source": "suggestion",
                            "status": "ok",
                        },
                    ],
                    "total_count": 0,
                }
            )
        ]
    )
    client = make_client(queue)

    result = client.research_keywords(
        "prj_1", KeywordResearchOptions(estimate_only=True, seed="rank tracker")
    )

    assert result.estimate is True
    assert result.rows == []
    assert result.sources[0].cached is True
    assert result.sources[1].cost_cents == 1.01
    assert str(queue.requests[-1].url).endswith(
        "/projects/prj_1/keyword-research?estimate_only=true&seed=rank+tracker"
    )


def test_gets_keyword_metrics_with_body_options_and_cached_counts() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "cached_count": 1,
                    "connections": [
                        {"id": "connection_1", "label": "DataForSEO", "provider": "dataforseo"}
                    ],
                    "cost_cents": 1,
                    "fetched_at": "2026-07-22T10:00:00.000Z",
                    "fetched_count": 1,
                    "provider": "DataForSEO",
                    "rows": [
                        {
                            "competition": 0.42,
                            "cpc_cents": 135,
                            "difficulty": 38,
                            "intent": "commercial",
                            "keyword": "rank tracker",
                            "monthly_trend": [{"month": 6, "search_volume": 1200, "year": 2026}],
                            "search_volume": 1200,
                        },
                        {
                            "competition": None,
                            "cpc_cents": 95,
                            "difficulty": None,
                            "intent": None,
                            "keyword": "seo api",
                            "monthly_trend": [],
                            "search_volume": 90,
                        },
                    ],
                    "total_count": 2,
                }
            )
        ]
    )
    client = make_client(queue)

    result = client.get_keyword_metrics(
        "prj_1",
        KeywordMetricsInput(
            connection_id="connection_1",
            estimate_only=False,
            fresh=True,
            include_clickstream=True,
            keywords=["rank tracker", "seo api"],
            max_cost_cents=7,
        ),
    )

    assert result.cached_count == 1
    assert result.fetched_count == 1
    assert result.rows[0].intent == "commercial"
    assert result.rows[1].difficulty is None
    assert result.rows[1].intent is None
    request = queue.requests[-1]
    assert request.method == "POST"
    assert str(request.url) == "https://api.test/api/v1/projects/prj_1/keyword-metrics"
    assert request_json(request) == {
        "connection_id": "connection_1",
        "estimate_only": False,
        "fresh": True,
        "include_clickstream": True,
        "keywords": ["rank tracker", "seo api"],
        "max_cost_cents": 7,
    }


def test_maps_keyword_metrics_estimate_response() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "cached_count": 1,
                    "connections": [
                        {"id": "connection_1", "label": "DataForSEO", "provider": "dataforseo"}
                    ],
                    "cost_cents": 0,
                    "estimate": True,
                    "estimated_cost_cents": 1.01,
                    "fetched_at": "2026-07-22T10:00:00.000Z",
                    "fetched_count": 0,
                    "fetched_count_estimate": 1,
                    "provider": "DataForSEO",
                    "rows": [],
                    "total_count": 0,
                }
            )
        ]
    )
    client = make_client(queue)

    result = client.get_keyword_metrics(
        "prj_1",
        KeywordMetricsInput(estimate_only=True, keywords=["rank tracker", "seo api"]),
    )

    assert result.estimate is True
    assert result.cached_count == 1
    assert result.fetched_count_estimate == 1
    assert result.estimated_cost_cents == 1.01
    assert result.rows == []
    assert request_json(queue.requests[-1]) == {
        "estimate_only": True,
        "keywords": ["rank tracker", "seo api"],
    }


def test_keyword_metrics_enforces_provider_batch_limit() -> None:
    with pytest.raises(ValidationError):
        KeywordMetricsInput(keywords=["keyword"] * 701)


def test_creates_keywords_through_create_keywords_and_add_keywords() -> None:
    response = {
        "created": 1,
        "results": [{"keyword": keyword(id="kw_new"), "status": "created"}],
        "skipped": 0,
    }
    body = CreateKeywordsBatch(
        keywords=[
            CreateKeywordInput(
                keyword="rank tracker",
                schedule=KeywordScheduleInput(cron_expression=None, frequency="daily"),
                tags=["Product"],
                target_url="https://example.com/page",
            )
        ]
    )
    queue = QueueTransport([json_response(response, 201), json_response(response, 201)])
    client = make_client(queue)

    assert (
        client.create_keywords(
            "prj_1",
            body,
            request_options={"idempotencyKey": "idem_keywords"},
        ).created
        == 1
    )
    assert client.add_keywords("prj_1", ["rank tracker"]).results[0].keyword.id == "kw_new"

    assert str(queue.requests[0].url) == "https://api.test/api/v1/projects/prj_1/keywords"
    assert queue.requests[0].headers["Content-Type"] == "application/json"
    assert queue.requests[0].headers["Idempotency-Key"] == "idem_keywords"
    assert request_json(queue.requests[0]) == {
        "keywords": [
            {
                "keyword": "rank tracker",
                "schedule": {"cronExpression": None, "frequency": "daily"},
                "tags": ["Product"],
                "target_url": "https://example.com/page",
            }
        ]
    }
    assert request_json(queue.requests[1]) == ["rank tracker"]


def test_create_keywords_sends_market_and_classification_fields() -> None:
    response = {
        "created": 1,
        "results": [
            {
                "keyword": keyword(id="kw_new", intent="commercial", topic="rank tracking"),
                "status": "created",
                "warning": "City not found; tracking at country level.",
            }
        ],
        "skipped": 0,
        "warnings": ["City not found; tracking at country level."],
    }
    queue = QueueTransport([json_response(response, 201)])
    client = make_client(queue)

    result = client.create_keywords(
        "prj_1",
        CreateKeywordsBatch(
            keywords=[
                CreateKeywordInput(
                    city="Austin",
                    intent="commercial",
                    keyword="rank tracker",
                    location_key="US/Texas/Austin",
                    topic="rank tracking",
                )
            ]
        ),
    )

    assert result.results[0].keyword.intent == "commercial"
    assert result.results[0].keyword.topic == "rank tracking"
    assert result.results[0].warning == "City not found; tracking at country level."
    assert result.warnings == ["City not found; tracking at country level."]
    assert request_json(queue.requests[-1]) == {
        "keywords": [
            {
                "city": "Austin",
                "intent": "commercial",
                "keyword": "rank tracker",
                "location_key": "US/Texas/Austin",
                "topic": "rank tracking",
            }
        ]
    }


def test_create_keywords_response_omits_warnings_by_default() -> None:
    response = {
        "created": 1,
        "results": [{"keyword": keyword(id="kw_new"), "status": "created"}],
        "skipped": 0,
    }
    queue = QueueTransport([json_response(response, 201)])
    client = make_client(queue)

    result = client.create_keywords("prj_1", ["rank tracker"])

    assert result.warnings is None
    assert result.results[0].warning is None


def test_update_keyword_sends_market_and_classification_fields() -> None:
    queue = QueueTransport([json_response(keyword(intent="informational", topic="docs"))])
    client = make_client(queue)

    updated = client.update_keyword(
        "kw_1",
        UpdateKeywordInput(
            city="Austin",
            intent="informational",
            location_key="US/Texas/Austin",
            topic="docs",
        ),
    )

    assert updated.intent == "informational"
    assert updated.topic == "docs"
    assert request_json(queue.requests[-1]) == {
        "city": "Austin",
        "intent": "informational",
        "location_key": "US/Texas/Austin",
        "topic": "docs",
    }


def test_gets_updates_sets_target_url_and_deletes_keyword() -> None:
    queue = QueueTransport(
        [
            json_response(keyword()),
            json_response(keyword(text="new text")),
            json_response(keyword(target_url=None)),
            json_response(keyword()),
        ]
    )
    client = make_client(queue)

    assert client.get_keyword("kw_1").id == "kw_1"
    updated = client.update_keyword("kw_1", UpdateKeywordInput(keyword="new text", tags=["API"]))
    assert updated.text == "new text"
    assert client.set_keyword_target_url("kw_1", None).target_url is None
    assert client.delete_keyword("kw_1").id == "kw_1"

    assert str(queue.requests[0].url) == "https://api.test/api/v1/keywords/kw_1"
    assert queue.requests[1].method == "PATCH"
    assert request_json(queue.requests[1]) == {"keyword": "new text", "tags": ["API"]}
    assert request_json(queue.requests[2]) == {"target_url": None}
    assert queue.requests[3].method == "DELETE"


def test_bulk_updates_keywords() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "operation": "add_tags",
                    "results": [{"keyword_id": "kw_1", "status": "updated"}],
                }
            )
        ]
    )
    client = make_client(queue)

    result = client.bulk_update_keywords(
        KeywordBulkInput(keyword_ids=["kw_1"], operation="add_tags", tags=["Product"])
    )

    assert result.operation == "add_tags"
    assert str(queue.requests[-1].url) == "https://api.test/api/v1/keywords/bulk"
    assert queue.requests[-1].method == "POST"
    assert request_json(queue.requests[-1]) == {
        "keyword_ids": ["kw_1"],
        "operation": "add_tags",
        "tags": ["Product"],
    }


def test_lists_runs_and_gets_rank_checks() -> None:
    since = datetime(2026, 1, 1, tzinfo=timezone.utc)
    queue = QueueTransport(
        [
            json_response(list_response([rank_check()], "cursor_2")),
            json_response(rank_check(), 201),
            json_response(rank_check(id="check_2")),
        ]
    )
    client = make_client(queue)

    assert (
        client.list_rank_checks(
            "kw_1",
            {
                "cursor": "cursor_1",
                "limit": 5,
                "since": since,
                "status": "failed",
                "until": "2026-01-31T00:00:00.000Z",
            },
        ).meta.next_cursor
        == "cursor_2"
    )
    run_result = client.run_rank_check("kw_1", RunRankCheckInput(provider_id="dataforseo"))
    assert run_result.id == "check_1"
    assert client.get_rank_check_result("check_2").id == "check_2"

    assert str(queue.requests[0].url) == (
        "https://api.test/api/v1/keywords/kw_1/rank-checks?"
        "cursor=cursor_1&limit=5&since=2026-01-01T00%3A00%3A00Z&status=failed&"
        "until=2026-01-31T00%3A00%3A00.000Z"
    )
    assert str(queue.requests[1].url) == "https://api.test/api/v1/keywords/kw_1/checks"
    assert queue.requests[1].method == "POST"
    assert request_json(queue.requests[1]) == {"provider_id": "dataforseo"}
    assert str(queue.requests[2].url) == "https://api.test/api/v1/rank-checks/check_2"


def test_omits_body_for_rank_check_without_provider_input() -> None:
    queue = QueueTransport([json_response(rank_check(), 201)])
    client = make_client(queue)

    client.run_rank_check("kw_1")

    assert queue.requests[-1].content == b""
    assert "Content-Type" not in queue.requests[-1].headers


def test_rank_check_exposes_provider_fallback_attempts() -> None:
    attempts = [
        {"message": "Quota exhausted.", "provider": "serpapi"},
        {"message": "Provider timed out.", "provider": "dataforseo"},
    ]
    queue = QueueTransport(
        [json_response(rank_check(attempts=attempts, error="Rank check failed.", status="failed"))]
    )
    client = make_client(queue)

    check = client.get_rank_check_result("check_1")

    assert check.status == "failed"
    assert check.attempts is not None
    assert check.attempts[0].provider == "serpapi"
    assert check.attempts[1].message == "Provider timed out."


def test_runs_rank_check_in_async_mode() -> None:
    queue = QueueTransport(
        [
            json_response(rank_check(position=None, status="running"), 202),
            json_response(rank_check(position=None, status="running"), 202),
        ]
    )
    client = make_client(queue)

    accepted = client.run_rank_check("kw_1", async_mode=True)
    assert accepted.status == "running"
    assert (
        client.run_rank_check(
            "kw_1",
            RunRankCheckInput(provider_id="dataforseo"),
            async_mode=True,
        ).status
        == "running"
    )

    assert str(queue.requests[0].url) == "https://api.test/api/v1/keywords/kw_1/checks?async=true"
    assert queue.requests[0].content == b""
    assert str(queue.requests[1].url) == "https://api.test/api/v1/keywords/kw_1/checks?async=true"
    assert request_json(queue.requests[1]) == {"provider_id": "dataforseo"}


def test_lists_rank_checks_filtered_by_running_status() -> None:
    queue = QueueTransport(
        [json_response(list_response([rank_check(position=None, status="running")]))]
    )
    client = make_client(queue)

    result = client.list_rank_checks("kw_1", {"status": "running"})

    assert result.data[0].status == "running"
    assert str(queue.requests[-1].url) == (
        "https://api.test/api/v1/keywords/kw_1/rank-checks?status=running"
    )


def test_creates_signal_with_typed_input() -> None:
    queue = QueueTransport([json_response(signal(), 201)])
    client = make_client(queue)

    created = client.create_signal(
        CreateSignalInput(
            happened_at=datetime(2026, 7, 4, 19, 30, tzinfo=timezone.utc),
            keyword_id="kw_1",
            payload={"version": "1.2.3"},
            severity="warning",
            source="deploy",
            type="deploy.completed",
            url="https://example.com/releases/1",
        ),
        request_options=RequestOptions(idempotency_key="idem_signal"),
    )

    assert created.id == "sig_1"
    assert created.public_id == "sig_1"
    assert created.project_id == "prj_1"
    assert created.keyword_id == "kw_1"
    assert created.severity == "warning"
    assert created.payload == {"version": "1.2.3"}
    request = queue.requests[-1]
    assert request.method == "POST"
    assert str(request.url) == "https://api.test/api/v1/signals"
    assert request.headers["Idempotency-Key"] == "idem_signal"
    assert request_json(request) == {
        "happened_at": "2026-07-04T19:30:00Z",
        "keyword_id": "kw_1",
        "payload": {"version": "1.2.3"},
        "severity": "warning",
        "source": "deploy",
        "type": "deploy.completed",
        "url": "https://example.com/releases/1",
    }


def test_creates_signal_from_mapping_with_required_fields_only() -> None:
    queue = QueueTransport(
        [json_response(signal(keyword_id=None, payload=None, severity="info", url=None), 201)]
    )
    client = make_client(queue)

    created = client.create_signal({"source": "api", "type": "api.changed"})

    assert created.severity == "info"
    assert created.keyword_id is None
    assert created.url is None
    assert request_json(queue.requests[-1]) == {"source": "api", "type": "api.changed"}


def test_creates_signal_from_mapping_with_datetime_happened_at() -> None:
    queue = QueueTransport([json_response(signal(), 201)])
    client = make_client(queue)

    client.create_signal(
        {
            "happened_at": datetime(2026, 7, 4, 19, 30, tzinfo=timezone.utc),
            "source": "deploy",
            "type": "deploy.completed",
        }
    )

    assert request_json(queue.requests[-1]) == {
        "happened_at": "2026-07-04T19:30:00Z",
        "source": "deploy",
        "type": "deploy.completed",
    }


def test_lists_project_signals_with_filters_and_cursor() -> None:
    queue = QueueTransport(
        [
            json_response(
                list_response(
                    [signal(id="sig_2", public_id="sig_2"), signal()],
                    "cursor_next",
                )
            )
        ]
    )
    client = make_client(queue)

    result = client.list_project_signals(
        "prj_1",
        ListSignalsOptions(
            cursor="cursor_1",
            from_="2026-07-01T00:00:00.000Z",
            limit=50,
            source="deploy",
            to=datetime(2026, 7, 5, tzinfo=timezone.utc),
            type="deploy.completed",
        ),
    )

    assert [item.public_id for item in result.data] == ["sig_2", "sig_1"]
    assert result.data[0].source == "deploy"
    assert result.meta.next_cursor == "cursor_next"
    assert str(queue.requests[-1].url) == (
        "https://api.test/api/v1/projects/prj_1/signals?"
        "cursor=cursor_1&from=2026-07-01T00%3A00%3A00.000Z&limit=50&source=deploy&"
        "to=2026-07-05T00%3A00%3A00Z&type=deploy.completed"
    )


def test_lists_project_signals_accepts_from_alias_in_mapping() -> None:
    queue = QueueTransport([json_response(list_response([signal()]))])
    client = make_client(queue)

    result = client.list_project_signals("prj_1", {"from": "2026-07-01T00:00:00.000Z"})

    assert result.meta.next_cursor is None
    assert str(queue.requests[-1].url) == (
        "https://api.test/api/v1/projects/prj_1/signals?from=2026-07-01T00%3A00%3A00.000Z"
    )


def test_analytics_snapshot_query_and_sync_methods() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "offset": 5,
                    "rows": [
                        {
                            "bounce_rate": 0.3,
                            "created_at": "2026-07-02T00:00:00.000Z",
                            "date": "2026-07-01",
                            "engagement_rate": 0.7,
                            "id": "traffic_1",
                            "key_events": 3.0,
                            "path": "/pricing",
                            "project_id": "prj_1",
                            "provider": "ga4",
                            "scroll_depth": None,
                            "sessions": 42,
                            "updated_at": "2026-07-02T00:00:00.000Z",
                            "visit_duration_seconds": 91.5,
                            "visitors": 35,
                            "window_days": 1,
                        }
                    ],
                    "total_count": 1,
                }
            ),
            json_response(
                {
                    "connection": {"id": "gsc_1", "label": "Search Console", "provider": "gsc"},
                    "rows": [
                        {
                            "clicks": 14,
                            "ctr": 0.2,
                            "impressions": 70,
                            "page": "/pricing",
                            "position": 4.5,
                            "query": "rank tracker",
                        }
                    ],
                }
            ),
            json_response(
                {
                    "connections": 1,
                    "keyword_snapshots": 2,
                    "page_snapshots": 3,
                    "project_id": "prj_1",
                    "runs": [
                        {
                            "connection_id": "ga4_1",
                            "provider": "ga4",
                            "rows_fetched": 4,
                            "rows_matched": 3,
                            "rows_upserted": 3,
                            "status": "succeeded_with_data",
                            "truncated": False,
                        }
                    ],
                    "skipped": [{"provider": "plausible", "reason": "no_capability"}],
                }
            ),
        ]
    )
    client = make_client(queue)

    snapshots = client.list_traffic_snapshots(
        "prj_1",
        ListTrafficSnapshotsOptions(
            end_date="2026-07-31",
            limit=25,
            offset=5,
            path=["/pricing", "/docs"],
            start_date="2026-07-01",
        ),
    )
    stats = client.list_search_performance_query_stats(
        "prj_1",
        ListSearchPerformanceQueryStatsOptions(
            connection_id="gsc_1",
            end_date="2026-07-31",
            limit=100,
            query="rank tracker",
            start_date="2026-07-01",
        ),
    )
    sync = client.sync_project_traffic(
        "prj_1", RequestOptions(idempotency_key="analytics-sync-001")
    )

    assert snapshots.rows[0].sessions == 42
    assert snapshots.total_count == 1
    assert stats.connection.provider == "gsc"
    assert stats.rows[0].position == 4.5
    assert sync.runs[0].status == "succeeded_with_data"
    assert sync.skipped[0].reason == "no_capability"
    assert str(queue.requests[0].url) == (
        "https://api.test/api/v1/projects/prj_1/analytics/traffic-snapshots?"
        "end_date=2026-07-31&limit=25&offset=5&path=%2Fpricing&path=%2Fdocs&"
        "start_date=2026-07-01"
    )
    assert str(queue.requests[1].url) == (
        "https://api.test/api/v1/projects/prj_1/analytics/query-stats?"
        "connection_id=gsc_1&end_date=2026-07-31&limit=100&query=rank+tracker&"
        "start_date=2026-07-01"
    )
    assert queue.requests[2].method == "POST"
    assert queue.requests[2].headers["Idempotency-Key"] == "analytics-sync-001"


def test_alert_rule_methods_cover_rules_and_triggered_alerts() -> None:
    queue = QueueTransport(
        [
            json_response(list_response([alert_rule()], "cursor_2")),
            json_response(list_response([triggered_alert()])),
            json_response(alert_rule(id="rule_new"), 201),
            json_response(alert_rule(threshold_position=9)),
            json_response({"deleted": True}),
        ]
    )
    client = make_client(queue)
    rule_input = AlertRuleInput(
        channels=["email", "webhook"],
        condition_type="threshold",
        enabled=True,
        name="Ranking drop",
        target_type="all",
        threshold_position=10,
    )

    assert client.list_alert_rules("prj_1", {"cursor": "cursor_1", "limit": 1}).data[0].id == (
        "rule_1"
    )
    assert client.list_triggered_alerts("prj_1").data[0].headline == "Ranking drop"
    assert client.create_alert_rule("prj_1", rule_input).id == "rule_new"
    assert client.update_alert_rule("rule_1", {**rule_input.model_dump(), "threshold_position": 9})
    assert client.delete_alert_rule("rule_1").deleted is True

    assert str(queue.requests[0].url) == (
        "https://api.test/api/v1/projects/prj_1/alert-rules?cursor=cursor_1&limit=1"
    )
    assert str(queue.requests[1].url) == "https://api.test/api/v1/projects/prj_1/triggered-alerts"
    assert str(queue.requests[2].url) == "https://api.test/api/v1/projects/prj_1/alert-rules"
    assert queue.requests[2].method == "POST"
    assert request_json(queue.requests[2]) == {
        "channels": ["email", "webhook"],
        "condition_type": "threshold",
        "enabled": True,
        "name": "Ranking drop",
        "target_type": "all",
        "threshold_position": 10,
    }
    assert str(queue.requests[3].url) == "https://api.test/api/v1/alert-rules/rule_1"
    assert queue.requests[3].method == "PATCH"
    assert request_json(queue.requests[3])["threshold_position"] == 9
    assert str(queue.requests[4].url) == "https://api.test/api/v1/alert-rules/rule_1"
    assert queue.requests[4].method == "DELETE"


def test_triggered_alert_mutations_map_results_and_paths() -> None:
    queue = QueueTransport(
        [
            json_response({"muted": True, "snoozed_until": "2026-07-23T10:00:00.000Z"}),
            json_response({"updated": 3}),
        ]
    )
    client = make_client(queue)

    muted = client.mute_triggered_alert(
        "prj spaced",
        "alert/1",
        RequestOptions(idempotency_key="mute-1"),
    )
    marked = client.mark_project_alerts_read(
        "prj spaced",
        RequestOptions(idempotency_key="mark-1"),
    )

    assert muted.muted is True
    assert muted.snoozed_until == "2026-07-23T10:00:00.000Z"
    assert marked.updated == 3
    assert str(queue.requests[0].url) == (
        "https://api.test/api/v1/projects/prj%20spaced/triggered-alerts/alert%2F1/mute"
    )
    assert str(queue.requests[1].url) == (
        "https://api.test/api/v1/projects/prj%20spaced/triggered-alerts/mark-read"
    )
    assert queue.requests[0].headers["Idempotency-Key"] == "mute-1"
    assert queue.requests[1].headers["Idempotency-Key"] == "mark-1"


def test_exports_rank_history_as_typed_json_or_raw_csv() -> None:
    csv = "keyword_id,keyword,checked_at,position,previous_position,ranking_url\n"
    queue = QueueTransport(
        [
            json_response(list_response([rank_history_export_row()], "cursor_2")),
            text_response(csv, headers={"Content-Type": "text/csv; charset=utf-8"}),
        ]
    )
    client = make_client(queue)

    result = client.export_rank_history(
        "prj_1",
        RankHistoryExportOptions(
            cursor="cursor 1",
            format="json",
            granularity="weekly",
            keyword_ids=["kw 1", "kw/2"],
            limit=2,
            range="90",
        ),
    )
    raw = client.export_rank_history(
        "prj_1",
        {"format": "csv", "keyword_ids": ["kw_1"]},
    )

    assert not isinstance(result, str)
    assert result.data[0].checked_at == "2026-07-20T10:00:00.000Z"
    assert result.data[0].position == 4
    assert result.meta.next_cursor == "cursor_2"
    assert raw == csv
    assert str(queue.requests[0].url) == (
        "https://api.test/api/v1/projects/prj_1/exports/rank-history?"
        "cursor=cursor+1&format=json&granularity=weekly&keyword_id=kw+1&"
        "keyword_id=kw%2F2&limit=2&range=90"
    )
    assert str(queue.requests[1].url) == (
        "https://api.test/api/v1/projects/prj_1/exports/rank-history?format=csv&keyword_id=kw_1"
    )


def test_lists_and_updates_sitemap_monitors() -> None:
    queue = QueueTransport(
        [
            json_response(list_response([sitemap_monitor()])),
            json_response(sitemap_monitor(enabled=False, status="disabled")),
        ]
    )
    client = make_client(queue)

    listed = client.list_sitemap_monitors("prj spaced")
    updated = client.update_sitemap_monitor(
        "prj spaced",
        "monitor/1",
        SitemapMonitorPatch(enabled=False),
        RequestOptions(idempotency_key="monitor-1"),
    )

    assert listed.data[0].latest_snapshot is not None
    assert listed.data[0].latest_snapshot.url_count == 42
    assert updated.enabled is False
    assert updated.status == "disabled"
    assert str(queue.requests[0].url) == (
        "https://api.test/api/v1/projects/prj%20spaced/sitemap-monitors"
    )
    assert str(queue.requests[1].url) == (
        "https://api.test/api/v1/projects/prj%20spaced/sitemap-monitors/monitor%2F1"
    )
    assert queue.requests[1].method == "PATCH"
    assert queue.requests[1].headers["Idempotency-Key"] == "monitor-1"
    assert request_json(queue.requests[1]) == {"enabled": False}


def test_team_member_and_invite_methods() -> None:
    queue = QueueTransport(
        [
            json_response(list_response([team_member()])),
            json_response(list_response([team_invite()], "next_invites")),
            json_response(
                {
                    "expires_at": "2026-01-08T00:00:00.000Z",
                    "id": "inv_2",
                    "invite_link": "https://app.test/invite/raw",
                },
                201,
            ),
            json_response({"id": "inv_1"}),
            json_response({"id": "inv_2"}),
        ]
    )
    client = make_client(queue)

    assert client.list_team_members("prj_1").data[0].role_value == "owner"
    assert client.list_team_invites("prj_1", {"limit": 25}).meta.next_cursor == "next_invites"
    created = client.create_team_invite(
        "prj_1",
        CreateTeamInviteInput(email="new@example.com", role="viewer"),
    )
    assert created.invite_link.endswith("/invite/raw")
    assert client.revoke_project_team_invite("prj_1", "inv_1").id == "inv_1"
    assert client.revoke_team_invite("inv_2").id == "inv_2"

    assert str(queue.requests[0].url) == "https://api.test/api/v1/projects/prj_1/team/members"
    assert str(queue.requests[1].url) == (
        "https://api.test/api/v1/projects/prj_1/team/invites?limit=25"
    )
    assert str(queue.requests[2].url) == "https://api.test/api/v1/projects/prj_1/team/invites"
    assert request_json(queue.requests[2]) == {"email": "new@example.com", "role": "viewer"}
    assert str(queue.requests[3].url) == (
        "https://api.test/api/v1/projects/prj_1/team/invites/inv_1"
    )
    assert str(queue.requests[4].url) == "https://api.test/api/v1/team/invites/inv_2"


def test_team_member_mutation_and_invite_resend_methods() -> None:
    queue = QueueTransport(
        [
            json_response({"id": "member_1", "role": "admin"}),
            json_response({"id": "member_2"}),
            json_response(
                {
                    "expires_at": "2026-07-29T10:00:00.000Z",
                    "id": "invite_1",
                    "invite_link": "https://app.test/invite/new-token",
                }
            ),
        ]
    )
    client = make_client(queue)

    updated = client.update_team_member_role("prj_1", "member_1", {"role": "admin"})
    removed = client.remove_team_member("prj_1", "member_2")
    resent = client.resend_team_invite("prj_1", "invite_1")

    assert updated.role == "admin"
    assert removed.id == "member_2"
    assert resent.invite_link.endswith("/new-token")
    assert queue.requests[0].method == "PATCH"
    assert request_json(queue.requests[0]) == {"role": "admin"}
    assert str(queue.requests[0].url) == (
        "https://api.test/api/v1/projects/prj_1/team/members/member_1"
    )
    assert queue.requests[1].method == "DELETE"
    assert str(queue.requests[1].url) == (
        "https://api.test/api/v1/projects/prj_1/team/members/member_2"
    )
    assert queue.requests[2].method == "POST"
    assert str(queue.requests[2].url) == (
        "https://api.test/api/v1/projects/prj_1/team/invites/invite_1/resend"
    )


def test_provider_methods_and_settings_helpers() -> None:
    queue = QueueTransport(
        [
            json_response(list_response([provider()])),
            json_response(provider_connection(id="pc_connect"), 201),
            json_response({"balance": 42, "message": "Provider ready", "ok": True}),
            json_response(provider_connection(enabled=False, priority=20)),
            json_response(provider_connection(enabled=True)),
            json_response(provider_connection(priority=5)),
            json_response(provider_connection(is_primary=True, priority=0)),
            json_response({"ok": True}),
        ]
    )
    client = make_client(queue)

    assert client.list_providers("prj_1").data[0].drawer is not None
    assert (
        client.connect_provider(
            "prj_1",
            "serpapi",
            ConnectProviderInput(
                cost_per_check=0.01,
                credentials=ProviderCredentialsInput(api_key="secret"),
                primary=True,
            ),
        ).id
        == "pc_connect"
    )
    assert (
        client.test_provider_connection(
            "prj_1",
            "serpapi",
            ProviderConnectionTestInput(credentials=ProviderCredentialsInput(api_key="secret")),
        ).ok
        is True
    )
    assert client.update_provider_settings("prj_1", "serpapi", {"enabled": False, "priority": 20})
    assert client.set_provider_enabled("prj_1", "serpapi", True).enabled is True
    assert client.set_provider_priority("prj_1", "serpapi", 5).priority == 5
    assert client.set_primary_provider("prj_1", "serpapi").is_primary is True
    assert client.disconnect_provider("prj_1", "serpapi").ok is True

    assert str(queue.requests[0].url) == "https://api.test/api/v1/projects/prj_1/providers"
    assert str(queue.requests[1].url) == (
        "https://api.test/api/v1/projects/prj_1/providers/serpapi/connect"
    )
    assert request_json(queue.requests[1]) == {
        "cost_per_check": 0.01,
        "credentials": {"api_key": "secret"},
        "primary": True,
    }
    assert str(queue.requests[2].url) == (
        "https://api.test/api/v1/projects/prj_1/providers/serpapi/test"
    )
    assert request_json(queue.requests[2]) == {"credentials": {"api_key": "secret"}}
    assert request_json(queue.requests[3]) == {"enabled": False, "priority": 20}
    assert request_json(queue.requests[4]) == {"enabled": True}
    assert request_json(queue.requests[5]) == {"priority": 5}
    assert request_json(queue.requests[6]) == {"primary": True}
    assert queue.requests[7].method == "DELETE"


def test_connects_plausible_provider_with_endpoint_credential() -> None:
    queue = QueueTransport(
        [
            json_response(
                provider_connection(id="pc_plausible", kind="analytics", provider="plausible"),
                201,
            )
        ]
    )
    client = make_client(queue)

    connection = client.connect_provider(
        "prj_1",
        "plausible",
        ConnectProviderInput(
            credentials=ProviderCredentialsInput(
                api_key="plausible-secret",
                endpoint="https://plausible.example.com/api",
            ),
        ),
    )

    assert connection.provider == "plausible"
    assert connection.kind == "analytics"
    assert str(queue.requests[-1].url) == (
        "https://api.test/api/v1/projects/prj_1/providers/plausible/connect"
    )
    assert request_json(queue.requests[-1]) == {
        "credentials": {
            "api_key": "plausible-secret",
            "endpoint": "https://plausible.example.com/api",
        }
    }


def test_saved_view_methods() -> None:
    queue = QueueTransport(
        [
            json_response(list_response([saved_view()], "views_next")),
            json_response(saved_view(id="view_2", name="Top 10"), 201),
            json_response({"deleted": True}),
            json_response({"deleted": False}),
        ]
    )
    client = make_client(queue)
    input_model = CreateSavedViewInput(
        name="Top 10",
        config=SavedViewConfig(
            filters=SavedViewFilters(
                change="any",
                contains="rank",
                country="all",
                device="desktop",
                position=["top10"],
                serp=[],
                tags=["Product"],
                vol_max=50,
                vol_min=0,
                wrong_url=False,
            ),
            search="rank",
        ),
    )

    assert client.list_saved_views("prj_1", {"cursor": "cursor_1"}).meta.next_cursor == (
        "views_next"
    )
    assert client.create_saved_view("prj_1", input_model).id == "view_2"
    assert client.delete_project_saved_view("prj_1", "view_1").deleted is True
    assert client.delete_saved_view("view_2").deleted is False

    assert str(queue.requests[0].url) == (
        "https://api.test/api/v1/projects/prj_1/saved-views?cursor=cursor_1"
    )
    assert request_json(queue.requests[1]) == {
        "config": {
            "filters": {
                "change": "any",
                "contains": "rank",
                "country": "all",
                "device": "desktop",
                "position": ["top10"],
                "serp": [],
                "tags": ["Product"],
                "vol_max": 50,
                "vol_min": 0,
                "wrong_url": False,
            },
            "search": "rank",
        },
        "name": "Top 10",
    }
    assert str(queue.requests[2].url) == (
        "https://api.test/api/v1/projects/prj_1/saved-views/view_1"
    )
    assert str(queue.requests[3].url) == "https://api.test/api/v1/saved-views/view_2"


def test_competitor_methods_include_list_meta() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "data": [competitor()],
                    "meta": {
                        "markets": [competitor_market()],
                        "next_cursor": None,
                        "suggestions": [{"domain": "newrank.io", "initials": "NI", "overlap": 3}],
                    },
                }
            ),
            json_response(competitor(id="comp_2", initials=None, label=None), 201),
            json_response({"removed": True}),
            json_response({"removed": True}),
        ]
    )
    client = make_client(queue)

    competitors = client.list_competitors("prj_1", {"limit": 10})
    assert competitors.data[0].domain == "rankzly.io"
    assert competitors.meta.markets is not None
    assert competitors.meta.markets[0].shares[0].share_of_voice == 40
    assert competitors.meta.suggestions is not None
    assert competitors.meta.suggestions[0].domain == "newrank.io"
    assert client.add_competitor("prj_1", AddCompetitorInput(domain="rankzly.io")).id == "comp_2"
    assert client.remove_project_competitor("prj_1", "comp_1").removed is True
    assert client.remove_competitor("comp_2").removed is True

    assert str(queue.requests[0].url) == (
        "https://api.test/api/v1/projects/prj_1/competitors?limit=10"
    )
    assert request_json(queue.requests[1]) == {"domain": "rankzly.io"}
    assert str(queue.requests[2].url) == (
        "https://api.test/api/v1/projects/prj_1/competitors/comp_1"
    )
    assert str(queue.requests[3].url) == "https://api.test/api/v1/competitors/comp_2"


def test_notification_preferences_methods() -> None:
    queue = QueueTransport(
        [
            json_response(notification_preferences()),
            json_response(
                notification_preferences(
                    alert_slack=True,
                    email=None,
                    email_verification=None,
                    slack_available=None,
                    webhook_available=None,
                )
            ),
        ]
    )
    client = make_client(queue)

    assert client.get_notification_preferences("prj_1").email == "owner@example.com"
    updated = client.update_notification_preferences(
        "prj_1",
        NotificationPreferencesPatch(alert_slack=True, check_email=True),
    )
    assert updated.alert_slack is True

    assert str(queue.requests[0].url) == (
        "https://api.test/api/v1/projects/prj_1/notification-preferences"
    )
    assert queue.requests[1].method == "PATCH"
    assert request_json(queue.requests[1]) == {"alert_slack": True, "check_email": True}


def test_migration_token_methods() -> None:
    issued = {
        **migration_token(created_by=None),
        "import_job": cloud_import_job(id="job_1"),
        "token": "mig_secret_value_1234567890",
    }
    queue = QueueTransport(
        [
            json_response(
                {
                    "data": [migration_token()],
                    "meta": {"import_job": cloud_import_job(), "next_cursor": None},
                }
            ),
            json_response(issued, 201),
            json_response({"id": "tok_1", "revoked_at": "2026-01-01T00:10:00.000Z"}),
            json_response({"id": "tok_2", "revoked_at": "2026-01-01T00:20:00.000Z"}),
        ]
    )
    client = make_client(queue)

    tokens = client.list_migration_tokens("prj_1")
    assert tokens.data[0].scope == "full"
    assert tokens.meta.import_job is not None
    assert tokens.meta.import_job.state == "idle"
    minted = client.mint_migration_token("prj_1", MintMigrationTokenInput(scope="keywords"))
    assert minted.token.startswith("mig_")
    assert client.revoke_project_migration_token("prj_1", "tok_1").id == "tok_1"
    assert client.revoke_migration_token("tok_2").revoked_at.endswith("00.000Z")

    assert str(queue.requests[0].url) == "https://api.test/api/v1/projects/prj_1/migration-tokens"
    assert request_json(queue.requests[1]) == {"scope": "keywords"}
    assert str(queue.requests[2].url) == (
        "https://api.test/api/v1/projects/prj_1/migration-tokens/tok_1"
    )
    assert str(queue.requests[3].url) == "https://api.test/api/v1/migration-tokens/tok_2"


@pytest.mark.parametrize(
    ("operation", "expected_url"),
    [
        (
            lambda client: client.list_alert_rules("prj_1"),
            "https://api.test/api/v1/projects/prj_1/alert-rules",
        ),
        (
            lambda client: client.list_team_members("prj_1"),
            "https://api.test/api/v1/projects/prj_1/team/members",
        ),
        (
            lambda client: client.list_providers("prj_1"),
            "https://api.test/api/v1/projects/prj_1/providers",
        ),
        (
            lambda client: client.list_saved_views("prj_1"),
            "https://api.test/api/v1/projects/prj_1/saved-views",
        ),
        (
            lambda client: client.list_competitors("prj_1"),
            "https://api.test/api/v1/projects/prj_1/competitors",
        ),
        (
            lambda client: client.get_notification_preferences("prj_1"),
            "https://api.test/api/v1/projects/prj_1/notification-preferences",
        ),
        (
            lambda client: client.list_migration_tokens("prj_1"),
            "https://api.test/api/v1/projects/prj_1/migration-tokens",
        ),
    ],
)
def test_new_endpoint_groups_raise_problem_detail_errors(
    operation: Callable[[BisibilityClient], object],
    expected_url: str,
) -> None:
    problem = {
        "detail": "API key scope does not allow this operation.",
        "docs_url": "https://bisibility.com/docs/api/errors#forbidden",
        "instance": "urn:bisibility:api:v1:/api/v1/projects/prj_1",
        "status": 403,
        "title": "Forbidden",
        "type": "https://bisibility.dev/problems/forbidden",
    }
    queue = QueueTransport(
        [json_response(problem, 403, {"Content-Type": "application/problem+json"})]
    )
    client = make_client(queue)

    with pytest.raises(BisibilityApiError) as exc_info:
        operation(client)

    assert str(exc_info.value) == "API key scope does not allow this operation."
    assert exc_info.value.problem is not None
    assert exc_info.value.problem.title == "Forbidden"
    assert exc_info.value.url == expected_url


def test_returns_none_for_empty_success_response() -> None:
    queue = QueueTransport([httpx.Response(204)])
    client = make_client(queue)

    assert client.delete_keyword("kw_1") is None


def test_raises_configuration_error_when_protected_method_has_no_api_key() -> None:
    queue = QueueTransport([])
    client = BisibilityClient(base_url="https://api.test/api/v1", transport=queue.transport())

    with pytest.raises(BisibilityConfigurationError):
        client.list_projects()
    assert queue.requests == []


def test_raises_configuration_error_for_empty_base_url() -> None:
    with pytest.raises(BisibilityConfigurationError):
        BisibilityClient(api_key=API_KEY, base_url="   ")


def test_raises_api_error_with_problem_details() -> None:
    problem = {
        "detail": "Keyword not found.",
        "docs_url": "https://bisibility.com/docs/api/errors#not_found",
        "instance": "urn:bisibility:api:v1:/api/v1/keywords/kw_missing",
        "status": 404,
        "title": "Not found",
        "type": "https://bisibility.dev/problems/not_found",
    }
    queue = QueueTransport(
        [
            json_response(
                problem,
                404,
                {
                    "Authorization": "secret",
                    "Content-Type": "application/problem+json",
                    "Retry-After": "10",
                    "Set-Cookie": "session=secret",
                    "X-Api-Key": "secret",
                    "X-Trace-Id": "trace_1",
                },
            )
        ]
    )
    client = make_client(queue)

    with pytest.raises(BisibilityApiError) as exc_info:
        client.get_keyword("kw_missing")

    error = exc_info.value
    assert str(error) == "Keyword not found."
    assert error.status == 404
    assert error.problem is not None
    assert error.problem.detail == "Keyword not found."
    assert error.headers["Retry-After"] == "10"
    assert error.headers["X-Trace-Id"] == "trace_1"
    assert "Authorization" not in error.headers
    assert "Set-Cookie" not in error.headers
    assert "X-Api-Key" not in error.headers
    assert isinstance(error, BisibilityError)
    assert error.is_not_found is True
    assert error.is_rate_limit is False
    assert error.retry_after_seconds == 10.0


@pytest.mark.parametrize(
    "problem",
    [
        {"type": "https://bisibility.dev/problems/example", "extension": "kept"},
        {"title": "Invalid request", "status": 400, "extension": "kept"},
    ],
)
def test_accepts_minimal_rfc_9457_problem_details(problem: dict[str, Any]) -> None:
    queue = QueueTransport(
        [json_response(problem, 400, {"Content-Type": "application/problem+json"})]
    )
    client = make_client(queue)

    with pytest.raises(BisibilityApiError) as exc_info:
        client.list_projects()

    assert exc_info.value.problem is not None
    assert exc_info.value.problem.model_extra == {"extension": "kept"}


def test_all_sdk_errors_share_the_common_base() -> None:
    assert issubclass(BisibilityApiError, BisibilityError)
    assert issubclass(BisibilityConfigurationError, BisibilityError)
    assert issubclass(BisibilityNetworkError, BisibilityError)
    assert issubclass(BisibilityResponseError, BisibilityError)


def test_api_error_uses_body_when_problem_details_are_absent() -> None:
    queue = QueueTransport([text_response("upstream unavailable", 502)])
    client = make_client(queue)

    with pytest.raises(BisibilityApiError) as exc_info:
        client.list_projects()

    assert str(exc_info.value) == "upstream unavailable"
    assert exc_info.value.body == "upstream unavailable"
    assert exc_info.value.status == 502


def test_api_error_uses_json_body_text_when_not_problem_details() -> None:
    queue = QueueTransport([json_response({"error": "not a problem"}, 400)])
    client = make_client(queue)

    with pytest.raises(BisibilityApiError) as exc_info:
        client.list_projects()

    assert exc_info.value.body == '{"error":"not a problem"}'
    assert str(exc_info.value) == '{"error":"not a problem"}'
    assert exc_info.value.problem is None


def test_api_error_falls_back_to_status_for_empty_body() -> None:
    queue = QueueTransport([httpx.Response(500)])
    client = make_client(queue)

    with pytest.raises(BisibilityApiError) as exc_info:
        client.list_projects()

    assert str(exc_info.value) == "Bisibility API request failed with status 500."
    assert exc_info.value.body == ""
    assert exc_info.value.status == 500


def test_malformed_json_error_body_stays_plain_api_error() -> None:
    queue = QueueTransport(
        [httpx.Response(500, content=b"{", headers={"Content-Type": "application/problem+json"})]
    )
    client = make_client(queue)

    with pytest.raises(BisibilityApiError) as exc_info:
        client.list_projects()

    assert exc_info.value.body == "{"
    assert str(exc_info.value) == "{"
    assert exc_info.value.problem is None


def test_wraps_network_failures() -> None:
    request = httpx.Request("GET", "https://api.test/api/v1/projects")
    cause = httpx.ConnectError("socket closed", request=request)
    queue = QueueTransport([cause])
    client = make_client(queue, max_retries=0)

    with pytest.raises(BisibilityNetworkError) as exc_info:
        client.list_projects()

    assert exc_info.value.cause is cause
    assert exc_info.value.url == "https://api.test/api/v1/projects"


def test_throws_response_error_for_invalid_success_json() -> None:
    queue = QueueTransport([text_response("not json", 200)])
    client = make_client(queue)

    with pytest.raises(BisibilityResponseError) as exc_info:
        client.list_projects()

    assert exc_info.value.body == "not json"
    assert exc_info.value.status == 200


@pytest.fixture
def recorded_sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleeps: list[float] = []
    monkeypatch.setattr("bisibility.client._sleep", sleeps.append)
    return sleeps


def test_retries_transport_errors_until_success(recorded_sleeps: list[float]) -> None:
    request = httpx.Request("GET", "https://api.test/api/v1/projects")
    queue = QueueTransport(
        [
            httpx.ConnectError("socket closed", request=request),
            httpx.ReadTimeout("timed out", request=request),
            json_response(list_response([project()])),
        ]
    )
    client = make_client(queue)

    assert client.list_projects().data[0].id == "prj_1"
    assert len(queue.requests) == 3
    assert recorded_sleeps == [0.5, 1.0]


def test_retries_429_honoring_retry_after_header(recorded_sleeps: list[float]) -> None:
    problem = {
        "detail": "Rate limit exceeded.",
        "docs_url": "https://bisibility.com/docs/api/errors#rate_limited",
        "instance": "urn:bisibility:api:v1:/api/v1/projects",
        "status": 429,
        "title": "Too many requests",
        "type": "https://bisibility.dev/problems/rate_limited",
    }
    queue = QueueTransport(
        [
            json_response(problem, 429, {"Retry-After": "3"}),
            json_response(list_response([project()])),
        ]
    )
    client = make_client(queue)

    assert client.list_projects().data[0].id == "prj_1"
    assert recorded_sleeps == [3.0]


def test_retries_429_honoring_http_date_retry_after(recorded_sleeps: list[float]) -> None:
    queue = QueueTransport(
        [
            httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"}),
            json_response(list_response([project()])),
        ]
    )
    client = make_client(queue)

    assert client.list_projects().data[0].id == "prj_1"
    assert recorded_sleeps == [60.0]


def test_retries_503_with_exponential_backoff_when_retry_after_missing(
    recorded_sleeps: list[float],
) -> None:
    queue = QueueTransport(
        [
            httpx.Response(503),
            httpx.Response(503, headers={"Retry-After": "not-a-number"}),
            json_response(list_response([project()])),
        ]
    )
    client = make_client(queue, max_retries=3)

    assert client.list_projects().data[0].id == "prj_1"
    assert recorded_sleeps == [0.5, 1.0]


def test_caps_retry_after_and_backoff_delays(recorded_sleeps: list[float]) -> None:
    queue = QueueTransport(
        [
            httpx.Response(429, headers={"Retry-After": "300"}),
            httpx.Response(503, headers={"Retry-After": "-5"}),
            *[httpx.Response(503) for _ in range(5)],
            json_response(list_response([project()])),
        ]
    )
    client = make_client(queue, max_retries=7)

    assert client.list_projects().data[0].id == "prj_1"
    assert recorded_sleeps == [60.0, 1.0, 2.0, 4.0, 8.0, 8.0, 8.0]


def test_raises_after_retries_are_exhausted(recorded_sleeps: list[float]) -> None:
    queue = QueueTransport([httpx.Response(429), httpx.Response(429), httpx.Response(429)])
    client = make_client(queue)

    with pytest.raises(BisibilityApiError) as exc_info:
        client.list_projects()

    assert exc_info.value.status == 429
    assert len(queue.requests) == 3
    assert recorded_sleeps == [0.5, 1.0]


def test_raises_network_error_after_transport_retries_are_exhausted(
    recorded_sleeps: list[float],
) -> None:
    request = httpx.Request("GET", "https://api.test/api/v1/projects")
    queue = QueueTransport([httpx.ConnectError("socket closed", request=request) for _ in range(3)])
    client = make_client(queue)

    with pytest.raises(BisibilityNetworkError):
        client.list_projects()

    assert len(queue.requests) == 3
    assert recorded_sleeps == [0.5, 1.0]


def test_does_not_retry_non_retryable_statuses(recorded_sleeps: list[float]) -> None:
    queue = QueueTransport([httpx.Response(400)])
    client = make_client(queue)

    with pytest.raises(BisibilityApiError):
        client.list_projects()

    assert len(queue.requests) == 1
    assert recorded_sleeps == []


def test_max_retries_zero_disables_retries(recorded_sleeps: list[float]) -> None:
    queue = QueueTransport([httpx.Response(503)])
    client = make_client(queue, max_retries=0)

    with pytest.raises(BisibilityApiError) as exc_info:
        client.list_projects()

    assert exc_info.value.status == 503
    assert len(queue.requests) == 1
    assert recorded_sleeps == []


def test_does_not_retry_post_without_idempotency_key(recorded_sleeps: list[float]) -> None:
    queue = QueueTransport([httpx.Response(503)])
    client = make_client(queue)

    with pytest.raises(BisibilityApiError) as exc_info:
        client.create_api_key({"name": "CI"})

    assert exc_info.value.status == 503
    assert len(queue.requests) == 1
    assert recorded_sleeps == []


def test_does_not_retry_post_transport_error_without_idempotency_key(
    recorded_sleeps: list[float],
) -> None:
    request = httpx.Request("POST", "https://api.test/api/v1/api-keys")
    queue = QueueTransport([httpx.ConnectError("socket closed", request=request)])
    client = make_client(queue)

    with pytest.raises(BisibilityNetworkError):
        client.create_api_key({"name": "CI"})

    assert len(queue.requests) == 1
    assert recorded_sleeps == []


def test_retries_post_with_idempotency_key(recorded_sleeps: list[float]) -> None:
    created = {
        **api_key_resource(id="key_new", name="CI"),
        "masked_value": "bsk_live_12345678******cdef",
        "token": API_KEY,
    }
    queue = QueueTransport([httpx.Response(503), json_response(created, 201)])
    client = make_client(queue)

    result = client.create_api_key(
        {"name": "CI"},
        request_options=RequestOptions(idempotency_key="idem_1"),
    )

    assert result.id == "key_new"
    assert len(queue.requests) == 2
    assert all(request.headers["Idempotency-Key"] == "idem_1" for request in queue.requests)
    assert recorded_sleeps == [0.5]


def test_retries_get_requests_on_503(recorded_sleeps: list[float]) -> None:
    queue = QueueTransport([httpx.Response(503), json_response(list_response([project()]))])
    client = make_client(queue)

    assert client.list_projects().data[0].id == "prj_1"
    assert len(queue.requests) == 2
    assert queue.requests[0].method == "GET"
    assert recorded_sleeps == [0.5]


def test_retries_delete_requests_without_idempotency_key(
    recorded_sleeps: list[float],
) -> None:
    queue = QueueTransport([httpx.Response(503), json_response(project())])
    client = make_client(queue)

    assert client.delete_project("prj_1").id == "prj_1"
    assert [request.method for request in queue.requests] == ["DELETE", "DELETE"]
    assert recorded_sleeps == [0.5]


def test_closes_discarded_retryable_responses(recorded_sleeps: list[float]) -> None:
    close_calls: list[int] = []

    def retryable_response(request: httpx.Request) -> httpx.Response:
        response = httpx.Response(503)
        original_close = response.close

        def tracked_close() -> None:
            close_calls.append(1)
            original_close()

        response.close = tracked_close  # type: ignore[method-assign]
        return response

    queue = QueueTransport(
        [retryable_response, retryable_response, json_response(list_response([project()]))]
    )
    client = make_client(queue, max_retries=2)

    assert client.list_projects().data[0].id == "prj_1"
    assert close_calls == [1, 1]
    assert recorded_sleeps == [0.5, 1.0]


def test_rejects_negative_max_retries() -> None:
    with pytest.raises(BisibilityConfigurationError):
        BisibilityClient(api_key=API_KEY, max_retries=-1)


def test_exposes_factory_helper_and_context_manager() -> None:
    queue = QueueTransport([json_response(list_response([project()]))])

    with create_bisibility_client(
        api_key=API_KEY,
        base_url="https://api.test/api/v1",
        transport=queue.transport(),
    ) as client:
        assert isinstance(client, BisibilityClient)
        assert client.list_projects().data[0].id == "prj_1"


CHUNK_CHECKSUM = "sha256:" + "a" * 64


def test_get_cloud_import_compatibility_requires_no_auth() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "app_version": "1.4.2",
                    "latest_migration": "0042_cloud_import",
                    "schema_versions_supported": [1, 2, 3],
                }
            )
        ]
    )
    client = BisibilityClient(base_url="https://api.test/api/v1/", transport=queue.transport())

    compatibility = client.get_cloud_import_compatibility()

    assert compatibility.schema_versions_supported == [1, 2, 3]
    assert compatibility.latest_migration == "0042_cloud_import"
    assert compatibility.app_version == "1.4.2"
    request = queue.requests[0]
    assert request.method == "GET"
    assert str(request.url) == "https://api.test/api/v1/cloud/import/compatibility"
    assert "Authorization" not in request.headers


def test_import_cloud_export_posts_package_with_migration_token() -> None:
    queue = QueueTransport(
        [
            json_response(
                {"counts": {"keywords": 3}, "job_id": "job_1", "state": "done"},
                201,
            )
        ]
    )
    client = BisibilityClient(
        api_key="mig_secret_value_1234567890",
        base_url="https://api.test/api/v1/",
        transport=queue.transport(),
    )

    result = client.import_cloud_export(
        CloudImportPackage(version=3, scope="current", project_id="prj_1")
    )

    assert result.state == "done"
    assert result.job_id == "job_1"
    assert result.counts == {"keywords": 3}
    request = queue.requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.test/api/v1/cloud/import"
    assert request.headers["Authorization"] == "Bearer mig_secret_value_1234567890"
    assert request_json(request) == {"version": 3, "scope": "current", "project_id": "prj_1"}


def test_cloud_import_session_flow() -> None:
    queue = QueueTransport(
        [
            json_response(
                {
                    "chunk_limits": {
                        "max_body_bytes": 1048576,
                        "max_history_rows": 5000,
                        "max_keywords": 500,
                    },
                    "session_id": "sess_1",
                    "state": "receiving",
                },
                201,
            ),
            json_response({"chunk_count": 2, "chunks_received": 1, "state": "receiving"}),
            json_response({"chunk_count": 2, "chunks_received": 2, "state": "receiving"}),
            json_response({"counts": {"keywords": 4}, "job_id": "job_2", "state": "done"}),
        ]
    )
    client = BisibilityClient(
        api_key="mig_secret_value_1234567890",
        base_url="https://api.test/api/v1/",
        transport=queue.transport(),
    )

    created = client.create_cloud_import_session(CloudImportSessionCreate(version=3, chunk_count=2))
    assert created.session_id == "sess_1"
    assert created.chunk_limits.max_keywords == 500

    first = client.upload_cloud_import_chunk(
        "sess_1",
        0,
        {"checksum": CHUNK_CHECKSUM, "kind": "keywords", "keywords": [{"keyword": "seo"}]},
    )
    assert first.chunks_received == 1

    second = client.upload_cloud_import_chunk(
        "sess_1",
        1,
        {"checksum": CHUNK_CHECKSUM, "kind": "sections", "sections": {"competitors": []}},
        gzip=True,
    )
    assert second.chunks_received == 2

    finalized = client.finalize_cloud_import_session("sess_1")
    assert finalized.state == "done"
    assert finalized.counts == {"keywords": 4}

    assert queue.requests[0].method == "POST"
    assert str(queue.requests[0].url) == "https://api.test/api/v1/cloud/import/sessions"
    assert request_json(queue.requests[0]) == {"version": 3, "chunk_count": 2}

    assert queue.requests[1].method == "PUT"
    assert str(queue.requests[1].url) == (
        "https://api.test/api/v1/cloud/import/sessions/sess_1/chunks/0"
    )
    assert "Content-Encoding" not in queue.requests[1].headers

    assert str(queue.requests[2].url) == (
        "https://api.test/api/v1/cloud/import/sessions/sess_1/chunks/1"
    )
    assert queue.requests[2].headers["Content-Encoding"] == "gzip"

    assert queue.requests[3].method == "POST"
    assert str(queue.requests[3].url) == (
        "https://api.test/api/v1/cloud/import/sessions/sess_1/finalize"
    )
    assert queue.requests[3].content in (b"", b"null")
