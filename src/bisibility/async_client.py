"""Asynchronous client for the Bisibility REST API v1."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from functools import wraps
from typing import Any, Literal, ParamSpec, TypeVar, cast

import httpx

from .client import (
    _MISSING,
    AUTH_TOKEN_PREFIXES,
    CLIENT_ID,
    DEFAULT_MAX_RETRIES,
    IDEMPOTENCY_KEY_HEADER,
    IDEMPOTENT_METHODS,
    PROJECT_HEADER,
    RETRYABLE_STATUS_CODES,
    BisibilityClient,
    QueryParams,
    RequestOptionsLike,
    _backoff_seconds,
    _coerce_request_options,
    _dump_jsonable,
    _dump_options,
    _encoded_path_segment,
    _normalize_base_url,
    _retry_after_seconds,
    _UnsetTimeout,
)
from .errors import BisibilityConfigurationError, BisibilityNetworkError
from .models import (
    AlertRule,
    ApiKey,
    Competitor,
    Keyword,
    ListKeywordsOptions,
    ListMigrationTokensResponse,
    ListRankChecksOptions,
    ListSignalsOptions,
    MigrationToken,
    PaginationOptions,
    Provider,
    RankCheck,
    SavedKeyword,
    SavedView,
    Signal,
    TeamInvite,
    TeamMember,
    TriggeredAlert,
    Webhook,
)
from .public_ids import require_public_id

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")


def _asyncify(method: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    """Reuse one operation builder while preserving its public signature."""

    @wraps(method)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        pending = method(*args, **kwargs)
        return await cast(Awaitable[R], pending)

    return wrapped


class AsyncBisibilityClient(BisibilityClient):
    """Asynchronous Bisibility API client with full sync-client operation parity.

    Requests, retry delays, response cleanup, and cursor pagination are all
    non-blocking. Use ``async with`` or call ``await client.aclose()`` when the
    client owns its underlying ``httpx.AsyncClient``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        project_id: str | None = None,
        base_url: str | httpx.URL | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout | None = 30.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.AsyncClient | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if max_retries < 0:
            raise BisibilityConfigurationError("max_retries cannot be negative.")
        if api_key is not None and not api_key.startswith(AUTH_TOKEN_PREFIXES):
            raise BisibilityConfigurationError(
                "api_key must use a current bsb_key_live_, bsb_key_test_, "
                "bsb_pat_live_, or mig_ prefix."
            )
        self.api_key = api_key
        self.project_id = (
            require_public_id(project_id, "prj", field="project_id")
            if project_id is not None
            else None
        )
        self.base_url = _normalize_base_url(base_url)
        self.max_retries = max_retries
        self._default_headers = dict(headers or {})
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(  # type: ignore[assignment]
            timeout=timeout,
            transport=transport,
        )

    async def close(self) -> None:  # type: ignore[override]
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await cast(httpx.AsyncClient, self._client).aclose()

    async def __aenter__(self) -> AsyncBisibilityClient:
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self.aclose()

    def __enter__(self) -> AsyncBisibilityClient:
        raise TypeError("AsyncBisibilityClient must be used with 'async with'.")

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    get_health = _asyncify(BisibilityClient.get_health)  # type: ignore[assignment]
    get_liveness = _asyncify(BisibilityClient.get_liveness)  # type: ignore[assignment]
    get_readiness = _asyncify(BisibilityClient.get_readiness)  # type: ignore[assignment]
    get_open_api = _asyncify(BisibilityClient.get_open_api)  # type: ignore[assignment]
    get_capabilities = _asyncify(BisibilityClient.get_capabilities)  # type: ignore[assignment]
    get_llms_text = _asyncify(BisibilityClient.get_llms_text)  # type: ignore[assignment]
    get_provider_rates = _asyncify(BisibilityClient.get_provider_rates)  # type: ignore[assignment]
    get_cost_estimate = _asyncify(BisibilityClient.get_cost_estimate)  # type: ignore[assignment]
    search_locations = _asyncify(BisibilityClient.search_locations)  # type: ignore[assignment]
    list_projects = _asyncify(BisibilityClient.list_projects)  # type: ignore[assignment]
    get_me = _asyncify(BisibilityClient.get_me)  # type: ignore[assignment]
    update_me = _asyncify(BisibilityClient.update_me)  # type: ignore[assignment]
    list_my_tokens = _asyncify(BisibilityClient.list_my_tokens)  # type: ignore[assignment]
    create_my_token = _asyncify(BisibilityClient.create_my_token)  # type: ignore[assignment]
    revoke_my_token = _asyncify(BisibilityClient.revoke_my_token)  # type: ignore[assignment]
    create_project = _asyncify(BisibilityClient.create_project)  # type: ignore[assignment]
    get_project = _asyncify(BisibilityClient.get_project)  # type: ignore[assignment]
    update_project = _asyncify(BisibilityClient.update_project)  # type: ignore[assignment]
    delete_project = _asyncify(BisibilityClient.delete_project)  # type: ignore[assignment]
    get_project_defaults = _asyncify(BisibilityClient.get_project_defaults)  # type: ignore[assignment]
    get_project_overview = _asyncify(BisibilityClient.get_project_overview)  # type: ignore[assignment]
    match_project_keywords = _asyncify(BisibilityClient.match_project_keywords)  # type: ignore[assignment]
    update_project_defaults = _asyncify(BisibilityClient.update_project_defaults)  # type: ignore[assignment]
    list_api_keys = _asyncify(BisibilityClient.list_api_keys)  # type: ignore[assignment]
    create_api_key = _asyncify(BisibilityClient.create_api_key)  # type: ignore[assignment]
    revoke_api_key = _asyncify(BisibilityClient.revoke_api_key)  # type: ignore[assignment]
    list_project_api_keys = _asyncify(BisibilityClient.list_project_api_keys)  # type: ignore[assignment]
    create_project_api_key = _asyncify(BisibilityClient.create_project_api_key)  # type: ignore[assignment]
    list_webhooks = _asyncify(BisibilityClient.list_webhooks)  # type: ignore[assignment]
    create_webhook = _asyncify(BisibilityClient.create_webhook)  # type: ignore[assignment]
    update_webhook = _asyncify(BisibilityClient.update_webhook)  # type: ignore[assignment]
    delete_webhook = _asyncify(BisibilityClient.delete_webhook)  # type: ignore[assignment]
    list_keywords = _asyncify(BisibilityClient.list_keywords)  # type: ignore[assignment]
    list_ranked_keyword_suggestions = _asyncify(  # type: ignore[assignment]
        BisibilityClient.list_ranked_keyword_suggestions
    )
    research_keywords = _asyncify(BisibilityClient.research_keywords)  # type: ignore[assignment]
    analyze_backlinks = _asyncify(BisibilityClient.analyze_backlinks)  # type: ignore[assignment]
    load_more_backlink_rows = _asyncify(  # type: ignore[assignment]
        BisibilityClient.load_more_backlink_rows
    )
    get_keyword_metrics = _asyncify(BisibilityClient.get_keyword_metrics)  # type: ignore[assignment]
    add_keywords = _asyncify(BisibilityClient.add_keywords)  # type: ignore[assignment]
    create_keywords = _asyncify(BisibilityClient.create_keywords)  # type: ignore[assignment]
    get_keyword = _asyncify(BisibilityClient.get_keyword)  # type: ignore[assignment]
    update_keyword = _asyncify(BisibilityClient.update_keyword)  # type: ignore[assignment]
    set_keyword_target_url = _asyncify(  # type: ignore[assignment]
        BisibilityClient.set_keyword_target_url
    )
    delete_keyword = _asyncify(BisibilityClient.delete_keyword)  # type: ignore[assignment]
    bulk_update_keywords = _asyncify(BisibilityClient.bulk_update_keywords)  # type: ignore[assignment]
    list_rank_checks = _asyncify(BisibilityClient.list_rank_checks)  # type: ignore[assignment]
    run_rank_check = _asyncify(BisibilityClient.run_rank_check)  # type: ignore[assignment]
    get_rank_check_result = _asyncify(BisibilityClient.get_rank_check_result)  # type: ignore[assignment]
    create_signal = _asyncify(BisibilityClient.create_signal)  # type: ignore[assignment]
    list_project_signals = _asyncify(BisibilityClient.list_project_signals)  # type: ignore[assignment]
    list_traffic_snapshots = _asyncify(BisibilityClient.list_traffic_snapshots)  # type: ignore[assignment]
    list_search_performance_query_stats = _asyncify(  # type: ignore[assignment]
        BisibilityClient.list_search_performance_query_stats
    )
    sync_project_traffic = _asyncify(BisibilityClient.sync_project_traffic)  # type: ignore[assignment]
    list_alert_rules = _asyncify(BisibilityClient.list_alert_rules)  # type: ignore[assignment]
    create_alert_rule = _asyncify(BisibilityClient.create_alert_rule)  # type: ignore[assignment]
    update_alert_rule = _asyncify(BisibilityClient.update_alert_rule)  # type: ignore[assignment]
    delete_alert_rule = _asyncify(BisibilityClient.delete_alert_rule)  # type: ignore[assignment]
    list_triggered_alerts = _asyncify(BisibilityClient.list_triggered_alerts)  # type: ignore[assignment]
    mute_triggered_alert = _asyncify(BisibilityClient.mute_triggered_alert)  # type: ignore[assignment]
    mark_project_alerts_read = _asyncify(  # type: ignore[assignment]
        BisibilityClient.mark_project_alerts_read
    )
    export_rank_history = _asyncify(BisibilityClient.export_rank_history)  # type: ignore[assignment]
    list_sitemap_monitors = _asyncify(BisibilityClient.list_sitemap_monitors)  # type: ignore[assignment]
    update_sitemap_monitor = _asyncify(BisibilityClient.update_sitemap_monitor)  # type: ignore[assignment]
    list_team_members = _asyncify(BisibilityClient.list_team_members)  # type: ignore[assignment]
    list_team_invites = _asyncify(BisibilityClient.list_team_invites)  # type: ignore[assignment]
    create_team_invite = _asyncify(BisibilityClient.create_team_invite)  # type: ignore[assignment]
    resend_team_invite = _asyncify(BisibilityClient.resend_team_invite)  # type: ignore[assignment]
    update_team_member_role = _asyncify(BisibilityClient.update_team_member_role)  # type: ignore[assignment]
    remove_team_member = _asyncify(BisibilityClient.remove_team_member)  # type: ignore[assignment]
    revoke_project_team_invite = _asyncify(  # type: ignore[assignment]
        BisibilityClient.revoke_project_team_invite
    )
    revoke_team_invite = _asyncify(BisibilityClient.revoke_team_invite)  # type: ignore[assignment]
    list_providers = _asyncify(BisibilityClient.list_providers)  # type: ignore[assignment]
    connect_provider = _asyncify(BisibilityClient.connect_provider)  # type: ignore[assignment]
    test_provider_connection = _asyncify(  # type: ignore[assignment]
        BisibilityClient.test_provider_connection
    )
    update_provider_settings = _asyncify(  # type: ignore[assignment]
        BisibilityClient.update_provider_settings
    )
    set_provider_enabled = _asyncify(BisibilityClient.set_provider_enabled)  # type: ignore[assignment]
    set_provider_priority = _asyncify(BisibilityClient.set_provider_priority)  # type: ignore[assignment]
    set_primary_provider = _asyncify(BisibilityClient.set_primary_provider)  # type: ignore[assignment]
    disconnect_provider = _asyncify(BisibilityClient.disconnect_provider)  # type: ignore[assignment]
    list_saved_views = _asyncify(BisibilityClient.list_saved_views)  # type: ignore[assignment]
    create_saved_view = _asyncify(BisibilityClient.create_saved_view)  # type: ignore[assignment]
    delete_project_saved_view = _asyncify(  # type: ignore[assignment]
        BisibilityClient.delete_project_saved_view
    )
    delete_saved_view = _asyncify(BisibilityClient.delete_saved_view)  # type: ignore[assignment]
    list_saved_keywords = _asyncify(BisibilityClient.list_saved_keywords)  # type: ignore[assignment]
    create_saved_keywords = _asyncify(  # type: ignore[assignment]
        BisibilityClient.create_saved_keywords
    )
    delete_saved_keyword = _asyncify(BisibilityClient.delete_saved_keyword)  # type: ignore[assignment]
    list_competitors = _asyncify(BisibilityClient.list_competitors)  # type: ignore[assignment]
    add_competitor = _asyncify(BisibilityClient.add_competitor)  # type: ignore[assignment]
    remove_project_competitor = _asyncify(  # type: ignore[assignment]
        BisibilityClient.remove_project_competitor
    )
    remove_competitor = _asyncify(BisibilityClient.remove_competitor)  # type: ignore[assignment]
    get_notification_preferences = _asyncify(  # type: ignore[assignment]
        BisibilityClient.get_notification_preferences
    )
    update_notification_preferences = _asyncify(  # type: ignore[assignment]
        BisibilityClient.update_notification_preferences
    )
    list_migration_tokens = _asyncify(BisibilityClient.list_migration_tokens)  # type: ignore[assignment]
    mint_migration_token = _asyncify(BisibilityClient.mint_migration_token)  # type: ignore[assignment]
    revoke_project_migration_token = _asyncify(  # type: ignore[assignment]
        BisibilityClient.revoke_project_migration_token
    )
    revoke_migration_token = _asyncify(BisibilityClient.revoke_migration_token)  # type: ignore[assignment]
    get_cloud_import_compatibility = _asyncify(  # type: ignore[assignment]
        BisibilityClient.get_cloud_import_compatibility
    )
    import_cloud_export = _asyncify(BisibilityClient.import_cloud_export)  # type: ignore[assignment]
    create_cloud_import_session = _asyncify(  # type: ignore[assignment]
        BisibilityClient.create_cloud_import_session
    )
    upload_cloud_import_chunk = _asyncify(  # type: ignore[assignment]
        BisibilityClient.upload_cloud_import_chunk
    )
    finalize_cloud_import_session = _asyncify(  # type: ignore[assignment]
        BisibilityClient.finalize_cloud_import_session
    )

    async def _aiterate_cursor(
        self,
        fetch_page: Callable[[dict[str, Any]], Awaitable[Any]],
        initial_options: dict[str, Any],
    ) -> AsyncIterator[Any]:
        cursor = initial_options.get("cursor")
        while True:
            page_options = dict(initial_options)
            if cursor is None:
                page_options.pop("cursor", None)
            else:
                page_options["cursor"] = cursor
            page = await fetch_page(page_options)
            for item in page.data:
                yield item
            cursor = page.meta.next_cursor
            if cursor is None:
                return

    async def iter_api_keys(  # type: ignore[override]
        self,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[ApiKey]:
        initial = _dump_options(options, PaginationOptions)
        async for item in self._aiterate_cursor(
            lambda page: self.list_api_keys(page, request_options), initial
        ):
            yield cast(ApiKey, item)

    async def iter_project_api_keys(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[ApiKey]:
        initial = _dump_options(options, PaginationOptions)
        async for item in self._aiterate_cursor(
            lambda page: self.list_project_api_keys(project_id, page, request_options), initial
        ):
            yield cast(ApiKey, item)

    async def iter_webhooks(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[Webhook]:
        initial = _dump_options(options, PaginationOptions)
        async for item in self._aiterate_cursor(
            lambda page: self.list_webhooks(project_id, page, request_options), initial
        ):
            yield cast(Webhook, item)

    async def iter_keywords(  # type: ignore[override]
        self,
        project_id: str,
        options: ListKeywordsOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[Keyword]:
        initial = _dump_options(options, ListKeywordsOptions)
        async for item in self._aiterate_cursor(
            lambda page: self.list_keywords(project_id, page, request_options), initial
        ):
            yield cast(Keyword, item)

    async def iter_rank_checks(  # type: ignore[override]
        self,
        keyword_id: str,
        options: ListRankChecksOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[RankCheck]:
        initial = _dump_options(options, ListRankChecksOptions)
        async for item in self._aiterate_cursor(
            lambda page: self.list_rank_checks(keyword_id, page, request_options), initial
        ):
            yield cast(RankCheck, item)

    async def iter_project_signals(  # type: ignore[override]
        self,
        project_id: str,
        options: ListSignalsOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[Signal]:
        initial = _dump_options(options, ListSignalsOptions)
        async for item in self._aiterate_cursor(
            lambda page: self.list_project_signals(project_id, page, request_options), initial
        ):
            yield cast(Signal, item)

    async def _aiter_project_list(
        self,
        project_id: str,
        list_method: Callable[[str, Mapping[str, Any], RequestOptionsLike], Awaitable[Any]],
        options: PaginationOptions | Mapping[str, Any] | None,
        request_options: RequestOptionsLike,
    ) -> AsyncIterator[Any]:
        initial = _dump_options(options, PaginationOptions)
        async for item in self._aiterate_cursor(
            lambda page: list_method(project_id, page, request_options), initial
        ):
            yield item

    async def iter_alert_rules(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[AlertRule]:
        async for item in self._aiter_project_list(
            project_id, self.list_alert_rules, options, request_options
        ):
            yield cast(AlertRule, item)

    async def iter_triggered_alerts(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[TriggeredAlert]:
        async for item in self._aiter_project_list(
            project_id, self.list_triggered_alerts, options, request_options
        ):
            yield cast(TriggeredAlert, item)

    async def iter_team_members(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[TeamMember]:
        async for item in self._aiter_project_list(
            project_id, self.list_team_members, options, request_options
        ):
            yield cast(TeamMember, item)

    async def iter_team_invites(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[TeamInvite]:
        async for item in self._aiter_project_list(
            project_id, self.list_team_invites, options, request_options
        ):
            yield cast(TeamInvite, item)

    async def iter_providers(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[Provider]:
        async for item in self._aiter_project_list(
            project_id, self.list_providers, options, request_options
        ):
            yield cast(Provider, item)

    async def iter_saved_views(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[SavedView]:
        async for item in self._aiter_project_list(
            project_id, self.list_saved_views, options, request_options
        ):
            yield cast(SavedView, item)

    async def iter_saved_keywords(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[SavedKeyword]:
        async for item in self._aiter_project_list(
            project_id, self.list_saved_keywords, options, request_options
        ):
            yield cast(SavedKeyword, item)

    async def iter_competitors(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[Competitor]:
        async for item in self._aiter_project_list(
            project_id, self.list_competitors, options, request_options
        ):
            yield cast(Competitor, item)

    async def iter_migration_tokens(  # type: ignore[override]
        self,
        project_id: str,
        options: PaginationOptions | Mapping[str, Any] | None = None,
        request_options: RequestOptionsLike = None,
    ) -> AsyncIterator[MigrationToken]:
        initial = _dump_options(options, PaginationOptions)
        path = f"/projects/{_encoded_path_segment(project_id, 'prj')}/migration-tokens"
        async for item in self._aiterate_cursor(
            lambda page: self._request(
                "GET",
                path,
                query={"cursor": page.get("cursor"), "limit": page.get("limit")},
                response_model=ListMigrationTokensResponse,
                request_options=request_options,
            ),
            initial,
        ):
            yield cast(MigrationToken, item)

    async def _request(  # type: ignore[override]
        self,
        method: str,
        path: str,
        *,
        accepted_status_codes: frozenset[int] = frozenset(),
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
        if PROJECT_HEADER in headers:
            headers[PROJECT_HEADER] = require_public_id(
                headers[PROJECT_HEADER], "prj", field=PROJECT_HEADER
            )
        if auth:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers.pop("Authorization", None)
        if options.idempotency_key:
            headers[IDEMPOTENCY_KEY_HEADER] = options.idempotency_key
        if "User-Agent" not in headers:
            headers["User-Agent"] = CLIENT_ID
        headers["X-Bisibility-Client"] = CLIENT_ID

        request_kwargs: dict[str, Any] = {"headers": headers}
        if not isinstance(options.timeout, _UnsetTimeout):
            request_kwargs["timeout"] = options.timeout
        if body is not _MISSING:
            request_kwargs["json"] = _dump_jsonable(body)

        response = await self._send_with_retries(
            method,
            url,
            request_kwargs,
            accepted_status_codes=accepted_status_codes,
        )
        if (
            response.status_code < 200 or response.status_code >= 300
        ) and response.status_code not in accepted_status_codes:
            raise self._error_from_response(response, method, url)
        if parse_as == "text":
            return cast(T, response.text)
        return self._json_from_response(response, method, url, response_model)

    async def _send_with_retries(  # type: ignore[override]
        self,
        method: str,
        url: str,
        request_kwargs: dict[str, Any],
        *,
        accepted_status_codes: frozenset[int] = frozenset(),
    ) -> httpx.Response:
        headers: Mapping[str, str] = request_kwargs.get("headers") or {}
        retryable = method.upper() in IDEMPOTENT_METHODS or any(
            name.lower() == IDEMPOTENCY_KEY_HEADER.lower() for name in headers
        )
        client = cast(httpx.AsyncClient, self._client)
        for attempt in range(self.max_retries + 1):
            retries_left = retryable and attempt < self.max_retries
            try:
                response = await client.request(method, url, **request_kwargs)
            except httpx.RequestError as exc:
                if retries_left:
                    await asyncio.sleep(_backoff_seconds(attempt))
                    continue
                raise BisibilityNetworkError(
                    "Network error while calling the Bisibility API.",
                    cause=exc,
                    method=method,
                    url=url,
                ) from exc

            if (
                response.status_code in RETRYABLE_STATUS_CODES
                and response.status_code not in accepted_status_codes
                and retries_left
            ):
                retry_after = _retry_after_seconds(response.headers)
                await response.aclose()
                await asyncio.sleep(
                    retry_after if retry_after is not None else _backoff_seconds(attempt)
                )
                continue
            return response

        raise AssertionError("unreachable")  # pragma: no cover


def create_async_bisibility_client(
    *,
    api_key: str | None = None,
    project_id: str | None = None,
    base_url: str | httpx.URL | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float | httpx.Timeout | None = 30.0,
    max_retries: int = DEFAULT_MAX_RETRIES,
    http_client: httpx.AsyncClient | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> AsyncBisibilityClient:
    return AsyncBisibilityClient(
        api_key=api_key,
        project_id=project_id,
        base_url=base_url,
        headers=headers,
        timeout=timeout,
        max_retries=max_retries,
        http_client=http_client,
        transport=transport,
    )
