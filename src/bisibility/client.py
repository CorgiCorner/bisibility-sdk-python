"""Synchronous client for the Bisibility REST API v1.

The client accepts both project API keys (``bsk_live_*``, scoped to a single
project) and personal access tokens (``bsp_live_*``, scoped to all of the
user's projects). PAT routes without a project in the path target a project
via the ``X-Bisibility-Project`` header; pass ``project_id`` to the client to
send it on every request.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from importlib.metadata import PackageNotFoundError, version
from json import JSONDecodeError
from typing import Any, Literal, TypeAlias, TypeVar, cast
from urllib.parse import quote, urlencode, urlsplit

import httpx
from pydantic import BaseModel, ValidationError

from .errors import (
    BisibilityApiError,
    BisibilityConfigurationError,
    BisibilityNetworkError,
    BisibilityResponseError,
)
from .models import (
    AddCompetitorInput,
    AlertRule,
    AlertRuleDeleteResult,
    AlertRuleInput,
    ApiKey,
    ApiKeyCreateInput,
    Capability,
    CloudImportChunkResponse,
    CloudImportCompatibility,
    CloudImportFinalizeResponse,
    CloudImportPackage,
    CloudImportSessionCreate,
    CloudImportSessionCreateResponse,
    Competitor,
    CompetitorRemoveResult,
    ConnectProviderInput,
    CostEstimate,
    CostEstimateOptions,
    CreatedApiKey,
    CreatedPersonalAccessToken,
    CreatedTeamInvite,
    CreateKeywordsInput,
    CreateKeywordsResponse,
    CreateProjectInput,
    CreateSavedViewInput,
    CreateSignalInput,
    CreateTeamInviteInput,
    DataResponse,
    HealthResponse,
    IssuedMigrationToken,
    Keyword,
    KeywordBulkInput,
    KeywordBulkResponse,
    KeywordMetricsInput,
    KeywordMetricsResponse,
    KeywordResearchOptions,
    KeywordResearchResponse,
    ListCompetitorsResponse,
    ListKeywordsOptions,
    ListMigrationTokensResponse,
    ListRankChecksOptions,
    ListRankedKeywordSuggestionsOptions,
    ListResponse,
    ListSearchPerformanceQueryStatsOptions,
    ListSignalsOptions,
    ListTrafficSnapshotsOptions,
    LocationSuggestion,
    Me,
    MigrationToken,
    MigrationTokenRevokeResult,
    MintMigrationTokenInput,
    NotificationPreferences,
    NotificationPreferencesPatch,
    OpenApiDocument,
    PageTrafficSnapshotsResponse,
    PaginationOptions,
    PersonalAccessToken,
    PersonalAccessTokenCreateInput,
    ProblemDetails,
    Project,
    ProjectDefaults,
    ProjectDefaultsPatch,
    Provider,
    ProviderConnection,
    ProviderDisconnectResult,
    ProviderRate,
    ProviderSettingsInput,
    ProviderTestResult,
    RankCheck,
    RankedKeywordSuggestionsResponse,
    RankHistoryExportOptions,
    RankHistoryExportResponse,
    RankHistoryExportRow,
    RevokedTeamInvite,
    RunRankCheckInput,
    SavedView,
    SavedViewDeleteResult,
    SearchLocationsOptions,
    SearchPerformanceQueryStatsResponse,
    Signal,
    SitemapMonitor,
    SitemapMonitorListResponse,
    SitemapMonitorPatch,
    TeamInvite,
    TeamInviteResendResult,
    TeamMember,
    TeamMemberMutationResult,
    TeamMemberRolePatch,
    TeamMemberRoleResult,
    TestProviderConnectionInput,
    TrafficSyncSummary,
    TriggeredAlert,
    TriggeredAlertMuteResult,
    TriggeredAlertsReadResult,
    UpdateKeywordInput,
    UpdateMeInput,
    UpdateProjectInput,
    Webhook,
    WebhookCreateInput,
    WebhookUpdateInput,
)

DEFAULT_BASE_URL = "https://bisibility.com/api/v1"
RELATIVE_BASE_ORIGIN = "https://bisibility.local"
DEFAULT_MAX_RETRIES = 2
RETRYABLE_STATUS_CODES = frozenset({429, 503})
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "PUT", "DELETE"})
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
PROJECT_HEADER = "X-Bisibility-Project"
RETRY_BACKOFF_INITIAL_SECONDS = 0.5
RETRY_BACKOFF_CAP_SECONDS = 8.0
RETRY_AFTER_CAP_SECONDS = 60.0
_MISSING = object()

try:
    SDK_VERSION = version("bisibility")
except PackageNotFoundError:  # pragma: no cover - source tree without installed metadata
    SDK_VERSION = "0.2.1"
CLIENT_ID = f"bisibility-sdk-python/{SDK_VERSION}"


class _UnsetTimeout:
    pass


_UNSET_TIMEOUT = _UnsetTimeout()

QueryValue = date | datetime | int | float | str | bool | list[str] | None
QueryParams = Mapping[str, QueryValue]
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RequestOptions:
    headers: Mapping[str, str] | None = None
    idempotency_key: str | None = None
    timeout: float | httpx.Timeout | _UnsetTimeout | None = _UNSET_TIMEOUT


RequestOptionsLike: TypeAlias = RequestOptions | Mapping[str, Any] | None


def _is_absolute_url(value: str) -> bool:
    return bool(urlsplit(value).scheme)


def _normalize_base_url(base_url: str | httpx.URL | None) -> str:
    raw = str(base_url or DEFAULT_BASE_URL).strip()
    if not raw:
        raise BisibilityConfigurationError("base_url cannot be empty.")
    return raw.rstrip("/")


def _encoded_path_segment(value: str) -> str:
    return quote(value, safe="")


def _query_value(value: QueryValue) -> str | list[str] | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        normalized = value.astimezone(timezone.utc) if value.tzinfo else value
        return normalized.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return value
    return str(value)


def _dump_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True, exclude_unset=True)
    if isinstance(value, Mapping):
        return {str(key): _dump_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_dump_jsonable(item) for item in value]
    return value


def _dump_options(
    value: BaseModel | Mapping[str, Any] | None,
    model: type[BaseModel],
) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, model):
        parsed = value
    else:
        parsed = model.model_validate(value)
    return parsed.model_dump(mode="python", by_alias=False, exclude_none=True, exclude_unset=True)


def _coerce_request_options(value: RequestOptionsLike = None) -> RequestOptions:
    if value is None:
        return RequestOptions()
    if isinstance(value, RequestOptions):
        return value

    idempotency_key = value.get("idempotency_key", value.get("idempotencyKey"))
    timeout = value["timeout"] if "timeout" in value else _UNSET_TIMEOUT
    if not isinstance(timeout, (_UnsetTimeout, int, float, httpx.Timeout, type(None))):
        raise TypeError("timeout must be a number, httpx.Timeout, or None.")
    headers = value.get("headers")
    if headers is not None and not isinstance(headers, Mapping):
        raise TypeError("headers must be a mapping.")

    return RequestOptions(
        headers=cast(Mapping[str, str] | None, headers),
        idempotency_key=cast(str | None, idempotency_key),
        timeout=cast(float | httpx.Timeout | _UnsetTimeout | None, timeout),
    )


def _problem_from_json(value: Any) -> ProblemDetails | None:
    if not isinstance(value, Mapping):
        return None
    problem_type = value.get("type")
    title = value.get("title")
    status = value.get("status")
    if not isinstance(problem_type, str) and not (
        isinstance(title, str) and isinstance(status, int) and not isinstance(status, bool)
    ):
        return None
    normalized = dict(value)
    for name in ("type", "title", "detail", "instance", "docs_url"):
        if name in normalized and not isinstance(normalized[name], str):
            normalized.pop(name)
    if "status" in normalized and (
        not isinstance(normalized["status"], int) or isinstance(normalized["status"], bool)
    ):
        normalized.pop("status")
    try:
        return ProblemDetails.model_validate(normalized)
    except ValidationError:
        return None


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _retry_after_seconds(headers: httpx.Headers) -> float | None:
    raw: str | None = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        seconds = max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())
    if seconds < 0:
        return None
    return min(seconds, RETRY_AFTER_CAP_SECONDS)


def _backoff_seconds(attempt: int) -> float:
    return min(RETRY_BACKOFF_INITIAL_SECONDS * (2.0**attempt), RETRY_BACKOFF_CAP_SECONDS)


class BisibilityClient:
    """Synchronous Bisibility API client.

    ``api_key`` accepts a project API key (``bsk_live_*``) or a personal
    access token (``bsp_live_*``). PATs cover all of the user's projects; on
    routes without a project in the path the target project is chosen via the
    ``X-Bisibility-Project`` header (project ``id`` or public id). Pass
    ``project_id`` to send that header on every request; without it the API
    implies the project only when the user has exactly one, and answers
    ``400`` otherwise.

    Failed requests are retried up to ``max_retries`` times when the failure is
    an ``httpx`` transport error or a ``429``/``503`` response. Only requests
    that are safe to replay are retried: idempotent
    ``GET``/``HEAD``/``PUT``/``DELETE`` requests are always eligible, while
    non-idempotent ``POST``/``PATCH`` requests are retried only when an
    ``Idempotency-Key`` header is present
    (set via ``RequestOptions.idempotency_key``). The ``Retry-After``
    response header is honored when present (capped at 60 seconds); otherwise a
    capped exponential backoff is used. Set ``max_retries=0`` to disable retries.
    """

    base_url: str

    def __init__(
        self,
        *,
        api_key: str | None = None,
        project_id: str | None = None,
        base_url: str | httpx.URL | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout | None = 30.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if max_retries < 0:
            raise BisibilityConfigurationError("max_retries cannot be negative.")
        self.api_key = api_key
        self.project_id = project_id
        self.base_url = _normalize_base_url(base_url)
        self.max_retries = max_retries
        self._default_headers = dict(headers or {})
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> BisibilityClient:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def get_health(self, request_options: RequestOptionsLike = None) -> HealthResponse:
        return self._request(
            "GET",
            "/health",
            response_model=HealthResponse,
            auth=False,
            request_options=request_options,
        )

    def get_open_api(self, request_options: RequestOptionsLike = None) -> OpenApiDocument:
        return self._request(
            "GET",
            "/openapi.json",
            response_model=OpenApiDocument,
            auth=False,
            request_options=request_options,
        )

    def get_capabilities(
        self,
        request_options: RequestOptionsLike = None,
    ) -> DataResponse[list[Capability]]:
        return self._request(
            "GET",
            "/capabilities",
            response_model=DataResponse[list[Capability]],
            auth=False,
            request_options=request_options,
        )

    def get_llms_text(self, request_options: RequestOptionsLike = None) -> str:
        return self._request(
            "GET",
            "/llms.txt",
            auth=False,
            parse_as="text",
            request_options=request_options,
        )

    def get_provider_rates(
        self,
        request_options: RequestOptionsLike = None,
    ) -> DataResponse[list[ProviderRate]]:
        """List public provider rate cards via GET /provider-rates (no auth)."""
        return self._request(
            "GET",
            "/provider-rates",
            response_model=DataResponse[list[ProviderRate]],
            auth=False,
            request_options=request_options,
        )

    def get_cost_estimate(
        self,
        options: CostEstimateOptions | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> DataResponse[CostEstimate]:
        """Estimate monthly rank-check cost via GET /cost-estimate (no auth).

        ``keywords`` is required; ``locations``, ``devices``, ``frequency``,
        ``provider``, ``option`` and ``plan`` are optional and fall back to the
        server defaults (1 location, 1 device, daily checks on ``dataforseo``).
        """
        params = _dump_options(options, CostEstimateOptions)
        return self._request(
            "GET",
            "/cost-estimate",
            query={
                "devices": params.get("devices"),
                "frequency": params.get("frequency"),
                "keywords": params.get("keywords"),
                "locations": params.get("locations"),
                "option": params.get("option"),
                "plan": params.get("plan"),
                "provider": params.get("provider"),
            },
            response_model=DataResponse[CostEstimate],
            auth=False,
            request_options=request_options,
        )

    def search_locations(
        self,
        options: SearchLocationsOptions | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[LocationSuggestion]:
        filters = _dump_options(options, SearchLocationsOptions)
        return self._request(
            "GET",
            "/locations/search",
            query={
                "country": filters.get("country"),
                "limit": filters.get("limit"),
                "q": filters.get("q"),
            },
            response_model=ListResponse[LocationSuggestion],
            request_options=request_options,
        )

    def list_projects(self, request_options: RequestOptionsLike = None) -> ListResponse[Project]:
        return self._request(
            "GET",
            "/projects",
            response_model=ListResponse[Project],
            request_options=request_options,
        )

    def get_me(self, request_options: RequestOptionsLike = None) -> Me:
        return self._request(
            "GET",
            "/me",
            response_model=Me,
            request_options=request_options,
        )

    def update_me(
        self,
        input: UpdateMeInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> Me:
        return self._request(
            "PATCH",
            "/me",
            body=input,
            response_model=Me,
            request_options=request_options,
        )

    def list_my_tokens(
        self,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[PersonalAccessToken]:
        return self._request(
            "GET",
            "/me/tokens",
            response_model=ListResponse[PersonalAccessToken],
            request_options=request_options,
        )

    def create_my_token(
        self,
        input: PersonalAccessTokenCreateInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> CreatedPersonalAccessToken:
        return self._request(
            "POST",
            "/me/tokens",
            body=input,
            response_model=CreatedPersonalAccessToken,
            request_options=request_options,
        )

    def revoke_my_token(
        self,
        token_id: str,
        request_options: RequestOptionsLike = None,
    ) -> PersonalAccessToken:
        return self._request(
            "DELETE",
            f"/me/tokens/{_encoded_path_segment(token_id)}",
            response_model=PersonalAccessToken,
            request_options=request_options,
        )

    def create_project(
        self,
        input: CreateProjectInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> Project:
        return self._request(
            "POST",
            "/projects",
            body=input,
            response_model=Project,
            request_options=request_options,
        )

    def get_project(
        self,
        project_id: str,
        request_options: RequestOptionsLike = None,
    ) -> Project:
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}",
            response_model=Project,
            request_options=request_options,
        )

    def update_project(
        self,
        project_id: str,
        input: UpdateProjectInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> Project:
        """Update a project's ``name`` and/or ``domain`` via PATCH /projects/{id}.

        At least one of ``name`` or ``domain`` must be provided; the server
        rejects an empty patch.
        """
        return self._request(
            "PATCH",
            f"/projects/{_encoded_path_segment(project_id)}",
            body=input,
            response_model=Project,
            request_options=request_options,
        )

    def delete_project(
        self,
        project_id: str,
        request_options: RequestOptionsLike = None,
    ) -> Project:
        """Delete a project via DELETE /projects/{id}.

        Returns the project resource as it existed before deletion.
        """
        return self._request(
            "DELETE",
            f"/projects/{_encoded_path_segment(project_id)}",
            response_model=Project,
            request_options=request_options,
        )

    def get_project_defaults(
        self,
        project_id: str,
        request_options: RequestOptionsLike = None,
    ) -> ProjectDefaults:
        """Get project-level keyword defaults via GET /projects/{id}/defaults."""
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/defaults",
            response_model=ProjectDefaults,
            request_options=request_options,
        )

    def update_project_defaults(
        self,
        project_id: str,
        input: ProjectDefaultsPatch | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> ProjectDefaults:
        """Update project-level keyword defaults via PATCH /projects/{id}/defaults.

        Accepts schedule fields (``frequency``, ``cron_expression``, ``timezone``,
        ``jitter_minutes``), ``serp_stop_on_match``, and default-market selectors.
        When ``location_key`` is omitted, ``country`` and ``device`` must be provided
        together.
        """
        return self._request(
            "PATCH",
            f"/projects/{_encoded_path_segment(project_id)}/defaults",
            body=input,
            response_model=ProjectDefaults,
            request_options=request_options,
        )

    def list_api_keys(
        self,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[ApiKey]:
        pagination = _dump_options(options, PaginationOptions)
        return self._request(
            "GET",
            "/api-keys",
            query={"cursor": pagination.get("cursor"), "limit": pagination.get("limit")},
            response_model=ListResponse[ApiKey],
            request_options=request_options,
        )

    def create_api_key(
        self,
        input: ApiKeyCreateInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> CreatedApiKey:
        return self._request(
            "POST",
            "/api-keys",
            body=input,
            response_model=CreatedApiKey,
            request_options=request_options,
        )

    def revoke_api_key(
        self,
        key_id: str,
        request_options: RequestOptionsLike = None,
    ) -> ApiKey:
        return self._request(
            "DELETE",
            f"/api-keys/{_encoded_path_segment(key_id)}",
            response_model=ApiKey,
            request_options=request_options,
        )

    def list_project_api_keys(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[ApiKey]:
        pagination = _dump_options(options, PaginationOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/api-keys",
            query={"cursor": pagination.get("cursor"), "limit": pagination.get("limit")},
            response_model=ListResponse[ApiKey],
            request_options=request_options,
        )

    def create_project_api_key(
        self,
        project_id: str,
        input: ApiKeyCreateInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> CreatedApiKey:
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/api-keys",
            body=input,
            response_model=CreatedApiKey,
            request_options=request_options,
        )

    def list_webhooks(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[Webhook]:
        pagination = _dump_options(options, PaginationOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/webhooks",
            query={"cursor": pagination.get("cursor"), "limit": pagination.get("limit")},
            response_model=ListResponse[Webhook],
            request_options=request_options,
        )

    def create_webhook(
        self,
        project_id: str,
        input: WebhookCreateInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> Webhook:
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/webhooks",
            body=input,
            response_model=Webhook,
            request_options=request_options,
        )

    def update_webhook(
        self,
        project_id: str,
        webhook_id: str,
        input: WebhookUpdateInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> Webhook:
        return self._request(
            "PATCH",
            (
                f"/projects/{_encoded_path_segment(project_id)}/webhooks/"
                f"{_encoded_path_segment(webhook_id)}"
            ),
            body=input,
            response_model=Webhook,
            request_options=request_options,
        )

    def delete_webhook(
        self,
        project_id: str,
        webhook_id: str,
        request_options: RequestOptionsLike = None,
    ) -> Webhook:
        return self._request(
            "DELETE",
            (
                f"/projects/{_encoded_path_segment(project_id)}/webhooks/"
                f"{_encoded_path_segment(webhook_id)}"
            ),
            response_model=Webhook,
            request_options=request_options,
        )

    def list_keywords(
        self,
        project_id: str,
        options: ListKeywordsOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[Keyword]:
        filters = _dump_options(options, ListKeywordsOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/keywords",
            query={
                "cursor": filters.get("cursor"),
                "filter[country]": filters.get("country"),
                "filter[device]": filters.get("device"),
                "filter[intent]": filters.get("intent"),
                "filter[position_gt]": filters.get("position_gt"),
                "filter[position_lt]": filters.get("position_lt"),
                "filter[tag]": filters.get("tag"),
                "filter[topic]": filters.get("topic"),
                "limit": filters.get("limit"),
                "search": filters.get("search"),
                "sort": filters.get("sort"),
            },
            response_model=ListResponse[Keyword],
            request_options=request_options,
        )

    def list_ranked_keyword_suggestions(
        self,
        project_id: str,
        options: ListRankedKeywordSuggestionsOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> RankedKeywordSuggestionsResponse:
        filters = _dump_options(options, ListRankedKeywordSuggestionsOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/ranked-keyword-suggestions",
            query={
                "connection_id": filters.get("connection_id"),
                "fresh": filters.get("fresh"),
                "limit": filters.get("limit"),
                "offset": filters.get("offset"),
            },
            response_model=RankedKeywordSuggestionsResponse,
            request_options=request_options,
        )

    def research_keywords(
        self,
        project_id: str,
        options: KeywordResearchOptions | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> KeywordResearchResponse:
        """Research keywords from one seed.

        This operation requires API write scope because a cache miss can spend the
        project's provider budget. Set ``estimate_only`` for a free dry run.
        """
        filters = _dump_options(options, KeywordResearchOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/keyword-research",
            query={
                "connection_id": filters.get("connection_id"),
                "estimate_only": filters.get("estimate_only"),
                "fresh": filters.get("fresh"),
                "include_clickstream": filters.get("include_clickstream"),
                "max_cost_cents": filters.get("max_cost_cents"),
                "mode": filters.get("mode"),
                "result_limit": filters.get("result_limit"),
                "seed": filters.get("seed"),
            },
            response_model=KeywordResearchResponse,
            request_options=request_options,
        )

    def get_keyword_metrics(
        self,
        project_id: str,
        input: KeywordMetricsInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> KeywordMetricsResponse:
        """Hydrate keyword metrics for up to 700 keywords.

        This operation requires API write scope because cache misses can spend the
        project's provider budget. Set ``estimate_only`` for a free dry run.
        """
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/keyword-metrics",
            body=input,
            response_model=KeywordMetricsResponse,
            request_options=request_options,
        )

    def add_keywords(
        self,
        project_id: str,
        input: CreateKeywordsInput,
        request_options: RequestOptionsLike = None,
    ) -> CreateKeywordsResponse:
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/keywords",
            body=input,
            response_model=CreateKeywordsResponse,
            request_options=request_options,
        )

    def create_keywords(
        self,
        project_id: str,
        input: CreateKeywordsInput,
        request_options: RequestOptionsLike = None,
    ) -> CreateKeywordsResponse:
        return self.add_keywords(project_id, input, request_options=request_options)

    def get_keyword(self, keyword_id: str, request_options: RequestOptionsLike = None) -> Keyword:
        return self._request(
            "GET",
            f"/keywords/{_encoded_path_segment(keyword_id)}",
            response_model=Keyword,
            request_options=request_options,
        )

    def update_keyword(
        self,
        keyword_id: str,
        input: UpdateKeywordInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> Keyword:
        return self._request(
            "PATCH",
            f"/keywords/{_encoded_path_segment(keyword_id)}",
            body=input,
            response_model=Keyword,
            request_options=request_options,
        )

    def set_keyword_target_url(
        self,
        keyword_id: str,
        target_url: str | None,
        request_options: RequestOptionsLike = None,
    ) -> Keyword:
        return self.update_keyword(
            keyword_id,
            {"target_url": target_url},
            request_options=request_options,
        )

    def delete_keyword(
        self,
        keyword_id: str,
        request_options: RequestOptionsLike = None,
    ) -> Keyword | None:
        return self._request(
            "DELETE",
            f"/keywords/{_encoded_path_segment(keyword_id)}",
            response_model=Keyword,
            request_options=request_options,
        )

    def bulk_update_keywords(
        self,
        input: KeywordBulkInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> KeywordBulkResponse:
        return self._request(
            "POST",
            "/keywords/bulk",
            body=input,
            response_model=KeywordBulkResponse,
            request_options=request_options,
        )

    def list_rank_checks(
        self,
        keyword_id: str,
        options: ListRankChecksOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[RankCheck]:
        filters = _dump_options(options, ListRankChecksOptions)
        return self._request(
            "GET",
            f"/keywords/{_encoded_path_segment(keyword_id)}/rank-checks",
            query={
                "cursor": filters.get("cursor"),
                "limit": filters.get("limit"),
                "since": filters.get("since"),
                "status": filters.get("status"),
                "until": filters.get("until"),
            },
            response_model=ListResponse[RankCheck],
            request_options=request_options,
        )

    def run_rank_check(
        self,
        keyword_id: str,
        input: RunRankCheckInput | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
        *,
        async_mode: bool = False,
    ) -> RankCheck:
        """Run a rank check for a keyword via POST /keywords/{id}/checks.

        When ``async_mode`` is True the request is sent with ``?async=true`` and
        the server answers ``202 Accepted`` with a rank check in status
        ``"running"``; poll ``get_rank_check_result`` until it completes or
        fails. Otherwise the call blocks until the check finishes and returns
        the completed rank check with ``201 Created``.
        """
        body: object = _MISSING
        if input is not None:
            dumped = _dump_jsonable(input)
            if dumped:
                body = dumped
        return self._request(
            "POST",
            f"/keywords/{_encoded_path_segment(keyword_id)}/checks",
            body=body,
            query={"async": True} if async_mode else None,
            response_model=RankCheck,
            request_options=request_options,
        )

    def get_rank_check_result(
        self,
        check_id: str,
        request_options: RequestOptionsLike = None,
    ) -> RankCheck:
        return self._request(
            "GET",
            f"/rank-checks/{_encoded_path_segment(check_id)}",
            response_model=RankCheck,
            request_options=request_options,
        )

    def create_signal(
        self,
        signal_input: CreateSignalInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> Signal:
        """Ingest a signal via POST /signals.

        ``source`` (one of ``"deploy"``, ``"cms"``, ``"api"``) and ``type``
        (matching ``category.event``, e.g. ``"deploy.completed"``) are required.
        ``payload`` must serialize to 8KB or less and ``url`` must be http(s).
        The signal is attached to the project the API key is scoped to.
        """
        if not isinstance(signal_input, CreateSignalInput):
            signal_input = CreateSignalInput.model_validate(signal_input)
        return self._request(
            "POST",
            "/signals",
            body=signal_input,
            response_model=Signal,
            request_options=request_options,
        )

    def list_project_signals(
        self,
        project_id: str,
        options: ListSignalsOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[Signal]:
        """List a project's signals via GET /projects/{id}/signals.

        Signals are returned newest first. Supports ``source``, ``type``,
        ``from``/``to`` (pass ``from_`` or ``"from"``) time-range filters and
        cursor pagination.
        """
        filters = _dump_options(options, ListSignalsOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/signals",
            query={
                "cursor": filters.get("cursor"),
                "from": filters.get("from_"),
                "limit": filters.get("limit"),
                "source": filters.get("source"),
                "to": filters.get("to"),
                "type": filters.get("type"),
            },
            response_model=ListResponse[Signal],
            request_options=request_options,
        )

    def list_traffic_snapshots(
        self,
        project_id: str,
        options: ListTrafficSnapshotsOptions | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> PageTrafficSnapshotsResponse:
        filters = _dump_options(options, ListTrafficSnapshotsOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/analytics/traffic-snapshots",
            query={
                "end_date": filters.get("end_date"),
                "limit": filters.get("limit"),
                "offset": filters.get("offset"),
                "path": filters.get("path"),
                "start_date": filters.get("start_date"),
            },
            response_model=PageTrafficSnapshotsResponse,
            request_options=request_options,
        )

    def list_search_performance_query_stats(
        self,
        project_id: str,
        options: ListSearchPerformanceQueryStatsOptions | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> SearchPerformanceQueryStatsResponse:
        filters = _dump_options(options, ListSearchPerformanceQueryStatsOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/analytics/query-stats",
            query={
                "connection_id": filters.get("connection_id"),
                "end_date": filters.get("end_date"),
                "limit": filters.get("limit"),
                "query": filters.get("query"),
                "start_date": filters.get("start_date"),
            },
            response_model=SearchPerformanceQueryStatsResponse,
            request_options=request_options,
        )

    def sync_project_traffic(
        self,
        project_id: str,
        request_options: RequestOptionsLike = None,
    ) -> TrafficSyncSummary:
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/analytics/sync",
            response_model=TrafficSyncSummary,
            request_options=request_options,
        )

    def list_alert_rules(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[AlertRule]:
        pagination = _dump_options(options, PaginationOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/alert-rules",
            query={"cursor": pagination.get("cursor"), "limit": pagination.get("limit")},
            response_model=ListResponse[AlertRule],
            request_options=request_options,
        )

    def create_alert_rule(
        self,
        project_id: str,
        input: AlertRuleInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> AlertRule:
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/alert-rules",
            body=input,
            response_model=AlertRule,
            request_options=request_options,
        )

    def update_alert_rule(
        self,
        rule_id: str,
        input: AlertRuleInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> AlertRule:
        return self._request(
            "PATCH",
            f"/alert-rules/{_encoded_path_segment(rule_id)}",
            body=input,
            response_model=AlertRule,
            request_options=request_options,
        )

    def delete_alert_rule(
        self,
        rule_id: str,
        request_options: RequestOptionsLike = None,
    ) -> AlertRuleDeleteResult:
        return self._request(
            "DELETE",
            f"/alert-rules/{_encoded_path_segment(rule_id)}",
            response_model=AlertRuleDeleteResult,
            request_options=request_options,
        )

    def list_triggered_alerts(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[TriggeredAlert]:
        pagination = _dump_options(options, PaginationOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/triggered-alerts",
            query={"cursor": pagination.get("cursor"), "limit": pagination.get("limit")},
            response_model=ListResponse[TriggeredAlert],
            request_options=request_options,
        )

    def mute_triggered_alert(
        self,
        project_id: str,
        alert_id: str,
        request_options: RequestOptionsLike = None,
    ) -> TriggeredAlertMuteResult:
        return self._request(
            "POST",
            (
                f"/projects/{_encoded_path_segment(project_id)}/triggered-alerts/"
                f"{_encoded_path_segment(alert_id)}/mute"
            ),
            response_model=TriggeredAlertMuteResult,
            request_options=request_options,
        )

    def mark_project_alerts_read(
        self,
        project_id: str,
        request_options: RequestOptionsLike = None,
    ) -> TriggeredAlertsReadResult:
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/triggered-alerts/mark-read",
            response_model=TriggeredAlertsReadResult,
            request_options=request_options,
        )

    def export_rank_history(
        self,
        project_id: str,
        options: RankHistoryExportOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> RankHistoryExportResponse | str:
        filters = _dump_options(options, RankHistoryExportOptions)
        path = f"/projects/{_encoded_path_segment(project_id)}/exports/rank-history"
        query = {
            "cursor": filters.get("cursor"),
            "format": filters.get("format"),
            "granularity": filters.get("granularity"),
            "keyword_id": filters.get("keyword_ids"),
            "limit": filters.get("limit"),
            "range": filters.get("range"),
        }
        if filters.get("format") == "csv":
            return self._request(
                "GET",
                path,
                parse_as="text",
                query=query,
                request_options=request_options,
            )
        return self._request(
            "GET",
            path,
            query=query,
            response_model=ListResponse[RankHistoryExportRow],
            request_options=request_options,
        )

    def list_sitemap_monitors(
        self,
        project_id: str,
        request_options: RequestOptionsLike = None,
    ) -> SitemapMonitorListResponse:
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/sitemap-monitors",
            response_model=ListResponse[SitemapMonitor],
            request_options=request_options,
        )

    def update_sitemap_monitor(
        self,
        project_id: str,
        monitor_id: str,
        input: SitemapMonitorPatch | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> SitemapMonitor:
        return self._request(
            "PATCH",
            (
                f"/projects/{_encoded_path_segment(project_id)}/sitemap-monitors/"
                f"{_encoded_path_segment(monitor_id)}"
            ),
            body=input,
            response_model=SitemapMonitor,
            request_options=request_options,
        )

    def list_team_members(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[TeamMember]:
        pagination = _dump_options(options, PaginationOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/team/members",
            query={"cursor": pagination.get("cursor"), "limit": pagination.get("limit")},
            response_model=ListResponse[TeamMember],
            request_options=request_options,
        )

    def list_team_invites(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[TeamInvite]:
        pagination = _dump_options(options, PaginationOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/team/invites",
            query={"cursor": pagination.get("cursor"), "limit": pagination.get("limit")},
            response_model=ListResponse[TeamInvite],
            request_options=request_options,
        )

    def create_team_invite(
        self,
        project_id: str,
        input: CreateTeamInviteInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> CreatedTeamInvite:
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/team/invites",
            body=input,
            response_model=CreatedTeamInvite,
            request_options=request_options,
        )

    def resend_team_invite(
        self,
        project_id: str,
        invite_id: str,
        request_options: RequestOptionsLike = None,
    ) -> TeamInviteResendResult:
        return self._request(
            "POST",
            (
                f"/projects/{_encoded_path_segment(project_id)}/team/invites/"
                f"{_encoded_path_segment(invite_id)}/resend"
            ),
            response_model=TeamInviteResendResult,
            request_options=request_options,
        )

    def update_team_member_role(
        self,
        project_id: str,
        member_id: str,
        input: TeamMemberRolePatch | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> TeamMemberRoleResult:
        return self._request(
            "PATCH",
            (
                f"/projects/{_encoded_path_segment(project_id)}/team/members/"
                f"{_encoded_path_segment(member_id)}"
            ),
            body=input,
            response_model=TeamMemberRoleResult,
            request_options=request_options,
        )

    def remove_team_member(
        self,
        project_id: str,
        member_id: str,
        request_options: RequestOptionsLike = None,
    ) -> TeamMemberMutationResult:
        return self._request(
            "DELETE",
            (
                f"/projects/{_encoded_path_segment(project_id)}/team/members/"
                f"{_encoded_path_segment(member_id)}"
            ),
            response_model=TeamMemberMutationResult,
            request_options=request_options,
        )

    def revoke_project_team_invite(
        self,
        project_id: str,
        invite_id: str,
        request_options: RequestOptionsLike = None,
    ) -> RevokedTeamInvite:
        return self._request(
            "DELETE",
            (
                f"/projects/{_encoded_path_segment(project_id)}/team/invites/"
                f"{_encoded_path_segment(invite_id)}"
            ),
            response_model=RevokedTeamInvite,
            request_options=request_options,
        )

    def revoke_team_invite(
        self,
        invite_id: str,
        request_options: RequestOptionsLike = None,
    ) -> RevokedTeamInvite:
        return self._request(
            "DELETE",
            f"/team/invites/{_encoded_path_segment(invite_id)}",
            response_model=RevokedTeamInvite,
            request_options=request_options,
        )

    def list_providers(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[Provider]:
        pagination = _dump_options(options, PaginationOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/providers",
            query={"cursor": pagination.get("cursor"), "limit": pagination.get("limit")},
            response_model=ListResponse[Provider],
            request_options=request_options,
        )

    def connect_provider(
        self,
        project_id: str,
        provider_id: str,
        input: ConnectProviderInput | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ProviderConnection:
        return self._request(
            "POST",
            (
                f"/projects/{_encoded_path_segment(project_id)}/providers/"
                f"{_encoded_path_segment(provider_id)}/connect"
            ),
            body=input if input is not None else _MISSING,
            response_model=ProviderConnection,
            request_options=request_options,
        )

    def test_provider_connection(
        self,
        project_id: str,
        provider_id: str,
        input: TestProviderConnectionInput | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ProviderTestResult:
        return self._request(
            "POST",
            (
                f"/projects/{_encoded_path_segment(project_id)}/providers/"
                f"{_encoded_path_segment(provider_id)}/test"
            ),
            body=input if input is not None else _MISSING,
            response_model=ProviderTestResult,
            request_options=request_options,
        )

    def update_provider_settings(
        self,
        project_id: str,
        provider_id: str,
        input: ProviderSettingsInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> ProviderConnection:
        return self._request(
            "PATCH",
            (
                f"/projects/{_encoded_path_segment(project_id)}/providers/"
                f"{_encoded_path_segment(provider_id)}"
            ),
            body=input,
            response_model=ProviderConnection,
            request_options=request_options,
        )

    def set_provider_enabled(
        self,
        project_id: str,
        provider_id: str,
        enabled: bool,
        request_options: RequestOptionsLike = None,
    ) -> ProviderConnection:
        return self.update_provider_settings(
            project_id,
            provider_id,
            {"enabled": enabled},
            request_options=request_options,
        )

    def set_provider_priority(
        self,
        project_id: str,
        provider_id: str,
        priority: int,
        request_options: RequestOptionsLike = None,
    ) -> ProviderConnection:
        return self.update_provider_settings(
            project_id,
            provider_id,
            {"priority": priority},
            request_options=request_options,
        )

    def set_primary_provider(
        self,
        project_id: str,
        provider_id: str,
        primary: bool = True,
        request_options: RequestOptionsLike = None,
    ) -> ProviderConnection:
        return self.update_provider_settings(
            project_id,
            provider_id,
            {"primary": primary},
            request_options=request_options,
        )

    def disconnect_provider(
        self,
        project_id: str,
        provider_id: str,
        request_options: RequestOptionsLike = None,
    ) -> ProviderDisconnectResult:
        return self._request(
            "DELETE",
            (
                f"/projects/{_encoded_path_segment(project_id)}/providers/"
                f"{_encoded_path_segment(provider_id)}"
            ),
            response_model=ProviderDisconnectResult,
            request_options=request_options,
        )

    def list_saved_views(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListResponse[SavedView]:
        pagination = _dump_options(options, PaginationOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/saved-views",
            query={"cursor": pagination.get("cursor"), "limit": pagination.get("limit")},
            response_model=ListResponse[SavedView],
            request_options=request_options,
        )

    def create_saved_view(
        self,
        project_id: str,
        input: CreateSavedViewInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> SavedView:
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/saved-views",
            body=input,
            response_model=SavedView,
            request_options=request_options,
        )

    def delete_project_saved_view(
        self,
        project_id: str,
        view_id: str,
        request_options: RequestOptionsLike = None,
    ) -> SavedViewDeleteResult:
        return self._request(
            "DELETE",
            (
                f"/projects/{_encoded_path_segment(project_id)}/saved-views/"
                f"{_encoded_path_segment(view_id)}"
            ),
            response_model=SavedViewDeleteResult,
            request_options=request_options,
        )

    def delete_saved_view(
        self,
        view_id: str,
        request_options: RequestOptionsLike = None,
    ) -> SavedViewDeleteResult:
        return self._request(
            "DELETE",
            f"/saved-views/{_encoded_path_segment(view_id)}",
            response_model=SavedViewDeleteResult,
            request_options=request_options,
        )

    def list_competitors(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> ListCompetitorsResponse:
        pagination = _dump_options(options, PaginationOptions)
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/competitors",
            query={"cursor": pagination.get("cursor"), "limit": pagination.get("limit")},
            response_model=ListCompetitorsResponse,
            request_options=request_options,
        )

    def add_competitor(
        self,
        project_id: str,
        input: AddCompetitorInput | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> Competitor:
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/competitors",
            body=input,
            response_model=Competitor,
            request_options=request_options,
        )

    def remove_project_competitor(
        self,
        project_id: str,
        competitor_id: str,
        request_options: RequestOptionsLike = None,
    ) -> CompetitorRemoveResult:
        return self._request(
            "DELETE",
            (
                f"/projects/{_encoded_path_segment(project_id)}/competitors/"
                f"{_encoded_path_segment(competitor_id)}"
            ),
            response_model=CompetitorRemoveResult,
            request_options=request_options,
        )

    def remove_competitor(
        self,
        competitor_id: str,
        request_options: RequestOptionsLike = None,
    ) -> CompetitorRemoveResult:
        return self._request(
            "DELETE",
            f"/competitors/{_encoded_path_segment(competitor_id)}",
            response_model=CompetitorRemoveResult,
            request_options=request_options,
        )

    def get_notification_preferences(
        self,
        project_id: str,
        request_options: RequestOptionsLike = None,
    ) -> NotificationPreferences:
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/notification-preferences",
            response_model=NotificationPreferences,
            request_options=request_options,
        )

    def update_notification_preferences(
        self,
        project_id: str,
        input: NotificationPreferencesPatch | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> NotificationPreferences:
        return self._request(
            "PATCH",
            f"/projects/{_encoded_path_segment(project_id)}/notification-preferences",
            body=input,
            response_model=NotificationPreferences,
            request_options=request_options,
        )

    def list_migration_tokens(
        self,
        project_id: str,
        request_options: RequestOptionsLike = None,
    ) -> ListMigrationTokensResponse:
        return self._request(
            "GET",
            f"/projects/{_encoded_path_segment(project_id)}/migration-tokens",
            response_model=ListMigrationTokensResponse,
            request_options=request_options,
        )

    def mint_migration_token(
        self,
        project_id: str,
        input: MintMigrationTokenInput | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> IssuedMigrationToken:
        return self._request(
            "POST",
            f"/projects/{_encoded_path_segment(project_id)}/migration-tokens",
            body=input if input is not None else _MISSING,
            response_model=IssuedMigrationToken,
            request_options=request_options,
        )

    def revoke_project_migration_token(
        self,
        project_id: str,
        token_id: str,
        request_options: RequestOptionsLike = None,
    ) -> MigrationTokenRevokeResult:
        return self._request(
            "DELETE",
            (
                f"/projects/{_encoded_path_segment(project_id)}/migration-tokens/"
                f"{_encoded_path_segment(token_id)}"
            ),
            response_model=MigrationTokenRevokeResult,
            request_options=request_options,
        )

    def revoke_migration_token(
        self,
        token_id: str,
        request_options: RequestOptionsLike = None,
    ) -> MigrationTokenRevokeResult:
        return self._request(
            "DELETE",
            f"/migration-tokens/{_encoded_path_segment(token_id)}",
            response_model=MigrationTokenRevokeResult,
            request_options=request_options,
        )

    def get_cloud_import_compatibility(
        self,
        request_options: RequestOptionsLike = None,
    ) -> CloudImportCompatibility:
        """Preflight cloud import compatibility via GET /cloud/import/compatibility.

        Returns the app version, the latest applied migration and the list of
        export schema versions the server accepts. No authentication required.
        """
        return self._request(
            "GET",
            "/cloud/import/compatibility",
            response_model=CloudImportCompatibility,
            auth=False,
            request_options=request_options,
        )

    def import_cloud_export(
        self,
        package: CloudImportPackage | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> CloudImportFinalizeResponse:
        """Import an export package in one request via POST /cloud/import.

        Authenticate with a migration token (``Authorization: Bearer mig_...``)
        by passing it as the client ``api_key``. The full ``package`` is sent as
        the JSON body and the server answers ``201`` with the finalized import
        counts once the import completes.
        """
        return self._request(
            "POST",
            "/cloud/import",
            body=package,
            response_model=CloudImportFinalizeResponse,
            request_options=request_options,
        )

    def create_cloud_import_session(
        self,
        session: CloudImportSessionCreate | Mapping[str, Any],
        request_options: RequestOptionsLike = None,
    ) -> CloudImportSessionCreateResponse:
        """Open a chunked cloud import session via POST /cloud/import/sessions.

        ``session`` declares the export ``version`` and ``chunk_count`` (and
        optional ``totals``). The response carries the ``session_id`` used to
        upload chunks and the per-chunk size limits enforced by the server.
        Authenticate with a migration token passed as the client ``api_key``.
        """
        return self._request(
            "POST",
            "/cloud/import/sessions",
            body=session,
            response_model=CloudImportSessionCreateResponse,
            request_options=request_options,
        )

    def upload_cloud_import_chunk(
        self,
        session_id: str,
        index: int,
        chunk: Mapping[str, Any],
        request_options: RequestOptionsLike = None,
        *,
        gzip: bool = False,
    ) -> CloudImportChunkResponse:
        """Upload one chunk via PUT /cloud/import/sessions/{sessionId}/chunks/{index}.

        ``chunk`` is a JSON body carrying a ``checksum`` (``sha256:<hex>``), a
        ``kind`` (``"keywords"`` or ``"sections"``) and the matching payload.
        Set ``gzip=True`` when ``chunk`` is a gzip-compressed JSON body to send
        the ``Content-Encoding: gzip`` header. Authenticate with a migration
        token passed as the client ``api_key``.
        """
        options = _coerce_request_options(request_options)
        if gzip:
            headers = dict(options.headers or {})
            headers["Content-Encoding"] = "gzip"
            options = RequestOptions(
                headers=headers,
                idempotency_key=options.idempotency_key,
                timeout=options.timeout,
            )
        return self._request(
            "PUT",
            (f"/cloud/import/sessions/{_encoded_path_segment(session_id)}/chunks/{index}"),
            body=chunk,
            response_model=CloudImportChunkResponse,
            request_options=options,
        )

    def finalize_cloud_import_session(
        self,
        session_id: str,
        request_options: RequestOptionsLike = None,
    ) -> CloudImportFinalizeResponse:
        """Finalize a chunked session via POST /cloud/import/sessions/{sessionId}/finalize.

        Called after every chunk has been uploaded; the server assembles the
        chunks, runs the import and answers ``200`` with the final counts.
        Authenticate with a migration token passed as the client ``api_key``.
        """
        return self._request(
            "POST",
            (f"/cloud/import/sessions/{_encoded_path_segment(session_id)}/finalize"),
            response_model=CloudImportFinalizeResponse,
            request_options=request_options,
        )

    def _iterate_cursor(
        self,
        fetch_page: Callable[[dict[str, Any]], Any],
        initial_options: dict[str, Any],
    ) -> Iterator[Any]:
        cursor = initial_options.get("cursor")
        while True:
            page_options = dict(initial_options)
            if cursor is None:
                page_options.pop("cursor", None)
            else:
                page_options["cursor"] = cursor
            page = fetch_page(page_options)
            yield from page.data
            cursor = page.meta.next_cursor
            if cursor is None:
                return

    def iter_api_keys(
        self,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[ApiKey]:
        initial = _dump_options(options, PaginationOptions)
        return cast(
            Iterator[ApiKey],
            self._iterate_cursor(lambda page: self.list_api_keys(page, request_options), initial),
        )

    def iter_project_api_keys(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[ApiKey]:
        initial = _dump_options(options, PaginationOptions)
        return cast(
            Iterator[ApiKey],
            self._iterate_cursor(
                lambda page: self.list_project_api_keys(project_id, page, request_options), initial
            ),
        )

    def iter_webhooks(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[Webhook]:
        initial = _dump_options(options, PaginationOptions)
        return cast(
            Iterator[Webhook],
            self._iterate_cursor(
                lambda page: self.list_webhooks(project_id, page, request_options), initial
            ),
        )

    def iter_keywords(
        self,
        project_id: str,
        options: ListKeywordsOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[Keyword]:
        initial = _dump_options(options, ListKeywordsOptions)
        return cast(
            Iterator[Keyword],
            self._iterate_cursor(
                lambda page: self.list_keywords(project_id, page, request_options), initial
            ),
        )

    def iter_rank_checks(
        self,
        keyword_id: str,
        options: ListRankChecksOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[RankCheck]:
        initial = _dump_options(options, ListRankChecksOptions)
        return cast(
            Iterator[RankCheck],
            self._iterate_cursor(
                lambda page: self.list_rank_checks(keyword_id, page, request_options), initial
            ),
        )

    def iter_project_signals(
        self,
        project_id: str,
        options: ListSignalsOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[Signal]:
        initial = _dump_options(options, ListSignalsOptions)
        return cast(
            Iterator[Signal],
            self._iterate_cursor(
                lambda page: self.list_project_signals(project_id, page, request_options), initial
            ),
        )

    def _iter_project_list(
        self,
        project_id: str,
        list_method: Callable[[str, Mapping[str, Any], RequestOptionsLike], Any],
        options: PaginationOptions | Mapping[str, Any] | None,
        request_options: RequestOptionsLike,
    ) -> Iterator[Any]:
        initial = _dump_options(options, PaginationOptions)
        return self._iterate_cursor(
            lambda page: list_method(project_id, page, request_options), initial
        )

    def iter_alert_rules(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[AlertRule]:
        return cast(
            Iterator[AlertRule],
            self._iter_project_list(project_id, self.list_alert_rules, options, request_options),
        )

    def iter_triggered_alerts(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[TriggeredAlert]:
        return cast(
            Iterator[TriggeredAlert],
            self._iter_project_list(
                project_id, self.list_triggered_alerts, options, request_options
            ),
        )

    def iter_team_members(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[TeamMember]:
        return cast(
            Iterator[TeamMember],
            self._iter_project_list(project_id, self.list_team_members, options, request_options),
        )

    def iter_team_invites(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[TeamInvite]:
        return cast(
            Iterator[TeamInvite],
            self._iter_project_list(project_id, self.list_team_invites, options, request_options),
        )

    def iter_providers(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[Provider]:
        return cast(
            Iterator[Provider],
            self._iter_project_list(project_id, self.list_providers, options, request_options),
        )

    def iter_saved_views(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[SavedView]:
        return cast(
            Iterator[SavedView],
            self._iter_project_list(project_id, self.list_saved_views, options, request_options),
        )

    def iter_competitors(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[Competitor]:
        return cast(
            Iterator[Competitor],
            self._iter_project_list(project_id, self.list_competitors, options, request_options),
        )

    def iter_migration_tokens(
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> Iterator[MigrationToken]:
        initial = _dump_options(options, PaginationOptions)
        path = f"/projects/{_encoded_path_segment(project_id)}/migration-tokens"
        return cast(
            Iterator[MigrationToken],
            self._iterate_cursor(
                lambda page: self._request(
                    "GET",
                    path,
                    query={"cursor": page.get("cursor"), "limit": page.get("limit")},
                    response_model=ListMigrationTokensResponse,
                    request_options=request_options,
                ),
                initial,
            ),
        )

    def _build_url(self, path: str, query: QueryParams | None = None) -> str:
        base_url = (
            self.base_url
            if _is_absolute_url(self.base_url)
            else f"{RELATIVE_BASE_ORIGIN}{self.base_url}"
        )
        url = f"{base_url}{'' if path.startswith('/') else '/'}{path}"
        if not query:
            return url

        query_items = {
            key: rendered
            for key, value in query.items()
            if (rendered := _query_value(value)) is not None
        }
        if not query_items:
            return url

        return f"{url}?{urlencode(query_items, doseq=True)}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        body: object = _MISSING,
        parse_as: Literal["text"] | None = None,
        query: QueryParams | None = None,
        request_options: RequestOptionsLike = None,
        response_model: type[T] | None = None,
    ) -> T:
        options = _coerce_request_options(request_options)
        url = self._build_url(path, query)
        if auth and not self.api_key:
            raise BisibilityConfigurationError(
                "api_key is required for this Bisibility API method."
            )

        headers = httpx.Headers(self._default_headers)
        if self.project_id:
            headers[PROJECT_HEADER] = self.project_id
        if options.headers:
            headers.update(options.headers)
        if auth:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers.pop("Authorization", None)
        if options.idempotency_key:
            headers["Idempotency-Key"] = options.idempotency_key
        if "User-Agent" not in headers:
            headers["User-Agent"] = CLIENT_ID
        headers["X-Bisibility-Client"] = CLIENT_ID

        request_kwargs: dict[str, Any] = {"headers": headers}
        if not isinstance(options.timeout, _UnsetTimeout):
            request_kwargs["timeout"] = options.timeout
        if body is not _MISSING:
            request_kwargs["json"] = _dump_jsonable(body)

        response = self._send_with_retries(method, url, request_kwargs)

        if response.status_code < 200 or response.status_code >= 300:
            raise self._error_from_response(response, method, url)

        if parse_as == "text":
            return cast(T, response.text)

        return self._json_from_response(response, method, url, response_model)

    def _send_with_retries(
        self,
        method: str,
        url: str,
        request_kwargs: dict[str, Any],
    ) -> httpx.Response:
        headers: Mapping[str, str] = request_kwargs.get("headers") or {}
        retryable = method.upper() in IDEMPOTENT_METHODS or any(
            name.lower() == IDEMPOTENCY_KEY_HEADER.lower() for name in headers
        )
        for attempt in range(self.max_retries + 1):
            retries_left = retryable and attempt < self.max_retries
            try:
                response = self._client.request(method, url, **request_kwargs)
            except httpx.RequestError as exc:
                if retries_left:
                    _sleep(_backoff_seconds(attempt))
                    continue
                raise BisibilityNetworkError(
                    "Network error while calling the Bisibility API.",
                    cause=exc,
                    method=method,
                    url=url,
                ) from exc

            if response.status_code in RETRYABLE_STATUS_CODES and retries_left:
                retry_after = _retry_after_seconds(response.headers)
                response.close()
                _sleep(retry_after if retry_after is not None else _backoff_seconds(attempt))
                continue

            return response

        raise AssertionError("unreachable")  # pragma: no cover

    def _json_from_response(
        self,
        response: httpx.Response,
        method: str,
        url: str,
        response_model: type[T] | None,
    ) -> T:
        body = response.text
        if not body:
            return cast(T, None)

        try:
            parsed = response.json()
        except JSONDecodeError as exc:
            raise BisibilityResponseError(
                "Bisibility API returned invalid JSON.",
                body=body,
                cause=exc,
                method=method,
                status=response.status_code,
                url=url,
            ) from exc

        if response_model is None:
            return cast(T, parsed)

        validator = getattr(response_model, "model_validate", None)
        if callable(validator):
            return cast(T, validator(parsed))
        return cast(T, parsed)

    def _error_from_response(
        self,
        response: httpx.Response,
        method: str,
        url: str,
    ) -> BisibilityApiError:
        body = response.text
        content_type = response.headers.get("Content-Type", "")
        parsed: Any | None = None
        if body and "json" in content_type:
            try:
                parsed = response.json()
            except JSONDecodeError:
                parsed = None

        problem = _problem_from_json(parsed)
        message = (
            problem.detail
            if problem is not None and problem.detail
            else body or f"Bisibility API request failed with status {response.status_code}."
        )
        return BisibilityApiError(
            message,
            body=body,
            headers=response.headers,
            method=method,
            problem=problem,
            status=response.status_code,
            url=url,
        )


def create_bisibility_client(
    *,
    api_key: str | None = None,
    project_id: str | None = None,
    base_url: str | httpx.URL | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float | httpx.Timeout | None = 30.0,
    max_retries: int = DEFAULT_MAX_RETRIES,
    http_client: httpx.Client | None = None,
    transport: httpx.BaseTransport | None = None,
) -> BisibilityClient:
    return BisibilityClient(
        api_key=api_key,
        project_id=project_id,
        base_url=base_url,
        headers=headers,
        timeout=timeout,
        max_retries=max_retries,
        http_client=http_client,
        transport=transport,
    )
