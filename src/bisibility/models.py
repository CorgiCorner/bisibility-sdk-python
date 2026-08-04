from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Annotated, Any, Generic, Literal, TypeAlias, TypeVar

from pydantic import (
    AfterValidator,
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .public_ids import (
    PUBLIC_ID_PREFIXES,
    PUBLIC_ID_SUFFIX_PATTERN,
    AlertRuleId,
    CheckId,
    CloudImportId,
    CompetitorId,
    ConnectionId,
    InviteId,
    KeyId,
    KeywordId,
    MemberId,
    PersonalAccessTokenId,
    ProjectId,
    SavedKeywordId,
    SignalId,
    TagId,
    TransferTokenId,
    TriggeredAlertId,
    UserId,
    ViewId,
    WebhookEndpointId,
    require_public_id,
)

JsonObject: TypeAlias = dict[str, Any]
Device: TypeAlias = Literal["desktop", "mobile"]
RankCheckFrequency: TypeAlias = Literal[
    "paused", "manual", "daily", "weekly", "monthly", "custom_cron"
]
AlertConditionType: TypeAlias = Literal[
    "threshold",
    "change_pct",
    "enters_top_n",
    "exits_top_n",
    "competitor_overtake",
    "serp_feature",
]
AlertChannel: TypeAlias = Literal["email", "slack", "webhook"]
AlertTargetType: TypeAlias = Literal["all", "keyword", "tag"]
KeywordBulkOperation: TypeAlias = Literal[
    "add_tags",
    "delete",
    "remove_tags",
    "set_frequency",
    "set_target_url",
]
KeywordBulkStatus: TypeAlias = Literal["deleted", "not_found", "updated"]
RankCheckStatus: TypeAlias = Literal["completed", "failed", "running"]
RankHistoryExportFormat: TypeAlias = Literal["csv", "json"]
RankHistoryGranularity: TypeAlias = Literal["daily", "weekly"]
RankHistoryRange: TypeAlias = Literal["30", "90", "all"]
ProjectWriteMode: TypeAlias = Literal["active", "migration_hold", "migrated"]
ProjectOverviewDevice: TypeAlias = Literal["all", "desktop", "mobile"]
ProjectOverviewRange: TypeAlias = Literal["7d", "28d", "90d"]
TrackingScope: TypeAlias = Literal["city", "country"]
PersonalAccessTokenScope: TypeAlias = Literal["admin", "read", "write"]
TeamInviteRole: TypeAlias = Literal["admin", "member", "viewer"]
TeamRoleValue: TypeAlias = Literal["admin", "auditor", "member", "owner", "viewer"]
ProviderId: TypeAlias = Literal[
    "dataforseo",
    "serpapi",
    "gsc",
    "ga4",
    "plausible",
    "ahrefs",
    "semrush",
]
ProviderKind: TypeAlias = Literal["serp", "analytics", "enrichment"]
MigrationScope: TypeAlias = Literal["full", "keywords"]
CloudImportState: TypeAlias = Literal["idle", "receiving", "importing", "done", "failed"]
KeywordSort: TypeAlias = Literal[
    "created_at",
    "-created_at",
    "keyword",
    "-keyword",
    "text",
    "-text",
    "updated_at",
    "-updated_at",
]
SignalSource: TypeAlias = Literal[
    "rank_tracker",
    "search_analytics",
    "url_inspection",
    "sitemap",
    "deploy",
    "cms",
    "search_engine_status",
    "manual",
    "api",
]
SignalCreateSource: TypeAlias = Literal["deploy", "cms", "api"]
SignalSeverity: TypeAlias = Literal["info", "warning", "critical"]
CostEstimateFrequency: TypeAlias = Literal["daily", "weekly", "monthly"]
CostEstimateProvider: TypeAlias = Literal["dataforseo", "serpapi"]
ProviderPricingModel: TypeAlias = Literal["flat", "plan"]
LocationKind: TypeAlias = Literal["country", "region", "city"]
RankedKeywordProvider: TypeAlias = Literal["dataforseo"]
KeywordResearchMode: TypeAlias = Literal["auto", "related", "suggestions", "ideas"]
KeywordResearchSource: TypeAlias = Literal["related", "suggestion", "idea"]
KeywordResearchSourceReason: TypeAlias = Literal[
    "budget_exhausted",
    "cost_limit",
    "in_progress",
    "needs_reauth",
    "no_source",
    "previous_source_failed",
    "provider_error",
    "rate_limited",
    "result_limit",
    "unsupported_location",
]
KeywordResearchSourceStatus: TypeAlias = Literal["ok", "failed", "skipped"]
KeywordIntent: TypeAlias = Literal[
    "informational", "commercial", "transactional", "navigational", "unknown"
]
TrafficSyncSkipReason: TypeAlias = Literal["no_capability", "rate_limited"]
TrafficSyncStatus: TypeAlias = Literal[
    "succeeded_with_data",
    "succeeded_empty",
    "deferred_rate_limit",
    "failed",
    "not_applicable",
]
SitemapMonitorStatus: TypeAlias = Literal["active", "disabled", "pending"]

T = TypeVar("T")

_CURSOR_V3_ERROR_MESSAGE = "cursor must be an opaque v3 cursor"


def _validate_offset_cursor_v3(payload: JsonObject) -> None:
    offset = payload["o"]
    if type(offset) is not int or offset < 0:
        raise ValueError(_CURSOR_V3_ERROR_MESSAGE)


def _validate_keyset_cursor_v3(payload: JsonObject) -> None:
    public_id = payload["public_id"]
    timestamp = payload["t"]
    if not isinstance(public_id, str) or not isinstance(timestamp, str):
        raise ValueError(_CURSOR_V3_ERROR_MESSAGE)
    prefix, separator, suffix = public_id.partition("_")
    if (
        separator != "_"
        or prefix not in PUBLIC_ID_PREFIXES
        or re.fullmatch(PUBLIC_ID_SUFFIX_PATTERN, suffix) is None
        or "T" not in timestamp
        or not timestamp.endswith("Z")
    ):
        raise ValueError(_CURSOR_V3_ERROR_MESSAGE)
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(_CURSOR_V3_ERROR_MESSAGE) from error


def _validate_cursor_payload_v3(payload: JsonObject) -> None:
    if set(payload) == {"v", "o"}:
        _validate_offset_cursor_v3(payload)
        return
    if set(payload) == {"v", "public_id", "t"}:
        _validate_keyset_cursor_v3(payload)
        return
    raise ValueError(_CURSOR_V3_ERROR_MESSAGE)


def _validate_cursor_v3(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError(_CURSOR_V3_ERROR_MESSAGE)
    try:
        padding = "=" * (-len(value) % 4)
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
        payload = json.loads(decoded)
    except ValueError as error:
        raise ValueError(_CURSOR_V3_ERROR_MESSAGE) from error

    if not isinstance(payload, dict) or type(payload.get("v")) is not int or payload["v"] != 3:
        raise ValueError(_CURSOR_V3_ERROR_MESSAGE)

    _validate_cursor_payload_v3(payload)
    return value


CursorV3: TypeAlias = Annotated[str, AfterValidator(_validate_cursor_v3)]


class BisibilityModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ProblemDetails(BisibilityModel):
    detail: str | None = None
    docs_url: str | None = None
    instance: str | None = None
    status: int | None = None
    title: str | None = None
    type: str | None = None
    errors: Any | None = None


class ListMeta(BisibilityModel):
    next_cursor: CursorV3 | None = None


class ListResponse(BisibilityModel, Generic[T]):
    data: list[T]
    meta: ListMeta


class DataResponse(BisibilityModel, Generic[T]):
    data: T
    meta: JsonObject | None = None


class Project(BisibilityModel):
    created_at: str
    domain: str
    id: ProjectId
    name: str
    updated_at: str
    write_mode: ProjectWriteMode


class UpdateProjectInput(BisibilityModel):
    domain: str | None = None
    name: str | None = None


class LocationSuggestion(BisibilityModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    city_name: str | None
    country_code: str
    display_name: str
    hl: str
    kind: LocationKind
    language_label: str
    location_key: str
    region_code: str | None
    region_name: str | None


class ProjectDefaults(BisibilityModel):
    city: str | None
    country: str
    cron_expression: str | None
    device: Device
    frequency: RankCheckFrequency
    jitter_minutes: int
    last_checked_at: str | None
    location_key: str
    next_check_at: str | None
    project_id: ProjectId
    serp_depth: Literal[10, 20, 50, 100]
    serp_stop_on_match: bool
    source: Literal["derived", "explicit", "fallback"]
    timezone: str
    updated_at: str | None = None


class ProjectDefaultsPatch(BisibilityModel):
    city: str | None = None
    country: str | None = None
    cron_expression: str | None = None
    device: Device | None = None
    frequency: RankCheckFrequency | None = None
    jitter_minutes: int | None = None
    location_key: str | None = None
    serp_stop_on_match: bool | None = None
    timezone: str | None = None


class PositionDistributionBucket(BisibilityModel):
    count: int | None = Field(ge=0)
    max: int = Field(ge=1)
    min: int = Field(ge=1)


class ProjectOverview(BisibilityModel):
    average_position: float | None
    average_position_delta: float | None
    keywords_added_this_month: int = Field(ge=0)
    last_check_at: str | None
    next_check_at: str | None
    position_distribution: list[PositionDistributionBucket]
    project_id: ProjectId
    top_10_count: int | None = Field(ge=0)
    top_10_delta: int | None
    top_100_count: int | None = Field(ge=0)
    top_3_count: int | None = Field(ge=0)
    tracked_keyword_count: int = Field(ge=0)
    visibility: float | None = Field(ge=0, le=100)
    visibility_delta: float | None


class ProjectOverviewOptions(BisibilityModel):
    device: ProjectOverviewDevice | None = None
    range: ProjectOverviewRange | None = None
    tag: str | None = Field(default=None, max_length=48)


class CreateProjectInput(BisibilityModel):
    defaults: ProjectDefaultsPatch | None = None
    domain: str
    name: str
    tracking_scope: TrackingScope | None = None


class MeProject(BisibilityModel):
    domain: str
    id: ProjectId
    name: str
    role: TeamRoleValue


class Me(BisibilityModel):
    email: str
    id: UserId
    name: str | None = None
    projects: list[MeProject]


class UpdateMeInput(BisibilityModel):
    name: str


class PersonalAccessTokenCreateInput(BisibilityModel):
    expires_in_days: Literal[30, 90, 365] | None = None
    name: str
    scope: PersonalAccessTokenScope | None = None


class PersonalAccessToken(BisibilityModel):
    created_at: str
    expires_at: str | None
    id: PersonalAccessTokenId
    last_used_at: str | None
    name: str
    prefix: str
    revoked_at: str | None
    scope: PersonalAccessTokenScope


class CreatedPersonalAccessToken(PersonalAccessToken):
    masked_value: str
    token: str


class ApiKeyCreateInput(BisibilityModel):
    name: str


class ApiKey(BisibilityModel):
    created_at: str
    id: KeyId
    last_used_at: str | None
    name: str
    prefix: str
    revoked_at: str | None


class CreatedApiKey(ApiKey):
    masked_value: str
    token: str


class KeywordSchedule(BisibilityModel):
    cron_expression: str | None
    frequency: RankCheckFrequency
    jitter_minutes: int
    last_checked_at: str | None
    next_check_at: str | None
    timezone: str


class Keyword(BisibilityModel):
    country: str
    created_at: str
    device: Device
    id: KeywordId
    intent: str | None = None
    latest_position: int | None
    location: str
    previous_position: int | None
    project_id: ProjectId
    ranking_url: str | None
    schedule: KeywordSchedule | None
    tags: list[str]
    target_url: str | None
    text: str
    topic: str | None = None
    updated_at: str


class KeywordMatchRequest(BisibilityModel):
    texts: list[Annotated[str, Field(min_length=1, max_length=180)]] = Field(
        min_length=1, max_length=50
    )


class KeywordMatchMarket(BisibilityModel):
    country_code: str
    device: Device
    location: str
    location_key: str


class KeywordMatch(BisibilityModel):
    keyword_id: KeywordId
    latest_position: int | None
    previous_position: int | None
    ranking_url: str | None = Field(
        description=(
            "URL that ranked at `latest_position` in the last completed check, or null when the "
            "keyword has no completed check."
        )
    )
    market: KeywordMatchMarket
    matched_text: str = Field(
        description="Trimmed, lowercase request text used to match this keyword."
    )
    text: str = Field(
        description=(
            "Stored keyword text, which can differ from matched_text in case and whitespace."
        )
    )


class KeywordMatchMeta(BisibilityModel):
    truncated_texts: list[str] = Field(
        description=(
            "Normalized texts with more than 100 matching markets. Their returned rows are partial."
        )
    )


class KeywordMatchResponse(BisibilityModel):
    data: list[KeywordMatch]
    meta: KeywordMatchMeta


class RankedKeywordConnection(BisibilityModel):
    id: ConnectionId
    label: str
    provider: RankedKeywordProvider


class RankedKeywordSuggestion(BisibilityModel):
    already_tracked: bool
    estimated_traffic: float | None
    keyword: str
    position: int | None
    search_volume: float | None


class RankedKeywordSuggestionsResponse(BisibilityModel):
    cached: bool
    connections: list[RankedKeywordConnection]
    cost_cents: float
    fetched_at: str
    offset: int
    rows: list[RankedKeywordSuggestion]
    total_count: int | None


class MonthlyKeywordVolume(BisibilityModel):
    month: int = Field(ge=1, le=12)
    search_volume: float | None
    year: int


class KeywordMetricsRow(BisibilityModel):
    competition: float | None = Field(ge=0, le=1)
    cpc_cents: int | None = Field(ge=0)
    difficulty: float | None = Field(ge=0, le=100)
    intent: KeywordIntent | None
    keyword: str
    monthly_trend: list[MonthlyKeywordVolume] = Field(max_length=12)
    search_volume: float | None = Field(ge=0)


class KeywordResearchRow(KeywordMetricsRow):
    already_tracked: bool
    source: KeywordResearchSource


class KeywordResearchSourceResult(BisibilityModel):
    cached: bool
    cost_cents: float = Field(ge=0)
    reason: KeywordResearchSourceReason | None = None
    returned: int = Field(ge=0)
    source: KeywordResearchSource
    status: KeywordResearchSourceStatus


class KeywordResearchResponse(BisibilityModel):
    cached: bool
    connections: list[RankedKeywordConnection]
    cost_cents: float = Field(ge=0)
    estimate: bool | None = None
    fetched_at: str
    provider: str
    rows: list[KeywordResearchRow]
    sources: list[KeywordResearchSourceResult]
    total_count: int = Field(ge=0)


class BacklinksSummary(BisibilityModel):
    backlinks_total: int = Field(ge=0)
    broken_backlinks: int = Field(ge=0)
    broken_pages: int = Field(ge=0)
    dofollow_pct: float = Field(ge=0, le=100)
    domain_rank: int = Field(ge=0, le=100)
    lost_backlinks: int = Field(ge=0)
    lost_referring_domains: int = Field(ge=0)
    new_backlinks: int = Field(ge=0)
    new_referring_domains: int = Field(ge=0)
    referring_domains_total: int = Field(ge=0)
    referring_pages: int = Field(ge=0)
    spam_score: float = Field(ge=0)


class BacklinksHistoryMonth(BisibilityModel):
    lost_links: int = Field(ge=0)
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    new_links: int = Field(ge=0)


class BacklinkRow(BisibilityModel):
    anchor: str
    domain_authority: int = Field(ge=0, le=100)
    first_seen: date
    flags: list[str]
    links_count: int = Field(ge=0)
    lost_at: date | None
    source_domain: str
    source_url: str
    spam_score: float = Field(ge=0)
    status: Literal["active", "new", "lost"]
    target_url: str


class BacklinksSnapshot(BisibilityModel):
    cached: bool
    cached_until: str
    cost_cents: float = Field(ge=0)
    estimate: bool | None = None
    estimated_cost_cents: float | None = Field(default=None, ge=0)
    fetched_at: str
    fetched_row_count: int = Field(ge=0)
    history: list[BacklinksHistoryMonth] = Field(min_length=12, max_length=12)
    include_subdomains: bool
    provider: str
    rows: list[BacklinkRow]
    summary: BacklinksSummary
    target: str
    target_scope: Literal["site", "page"]
    total_rows_available: int = Field(ge=0)


class KeywordMetricsResponse(BisibilityModel):
    cached_count: int = Field(ge=0)
    connections: list[RankedKeywordConnection]
    cost_cents: float = Field(ge=0)
    estimate: bool | None = None
    estimated_cost_cents: float | None = Field(default=None, ge=0)
    fetched_at: str
    fetched_count: int = Field(ge=0)
    fetched_count_estimate: int | None = Field(default=None, ge=0)
    provider: str
    rows: list[KeywordMetricsRow]
    total_count: int = Field(ge=0)


class KeywordScheduleInput(BisibilityModel):
    cron_expression: str | None = Field(
        validation_alias=AliasChoices("cron_expression", "cronExpression"),
        serialization_alias="cronExpression",
    )
    frequency: RankCheckFrequency
    jitter_minutes: int | None = Field(
        default=None,
        validation_alias=AliasChoices("jitter_minutes", "jitterMinutes"),
        serialization_alias="jitterMinutes",
    )
    timezone: str | None = None


class CreateKeywordInput(BisibilityModel):
    city: str | None = None
    country: str | None = None
    device: Device | None = None
    intent: str | None = None
    keyword: str
    location: str | None = None
    location_key: str | None = None
    schedule: KeywordScheduleInput | None = None
    tags: list[str] | None = None
    target_url: str | None = None
    topic: str | None = None


CreateKeywordItem: TypeAlias = str | CreateKeywordInput | Mapping[str, Any]


class CreateKeywordsBatch(BisibilityModel):
    keywords: list[CreateKeywordItem]


CreateKeywordsInput: TypeAlias = (
    CreateKeywordInput
    | CreateKeywordsBatch
    | Sequence[CreateKeywordInput | Mapping[str, Any] | str]
    | Mapping[str, Any]
)


class CreateKeywordResult(BisibilityModel):
    keyword: Keyword
    status: str
    warning: str | None = None


class CreateKeywordsResponse(BisibilityModel):
    created: int
    results: list[CreateKeywordResult]
    skipped: int
    warnings: list[str] | None = None


class UpdateKeywordInput(BisibilityModel):
    city: str | None = None
    country: str | None = None
    device: Device | None = None
    frequency: RankCheckFrequency | None = None
    intent: str | None = None
    keyword: str | None = None
    location: str | None = None
    location_key: str | None = None
    schedule: KeywordScheduleInput | None = None
    tags: list[str] | None = None
    target_url: str | None = None
    topic: str | None = None


class KeywordBulkInput(BisibilityModel):
    keyword_ids: list[KeywordId]
    operation: KeywordBulkOperation
    frequency: RankCheckFrequency | None = None
    schedule: KeywordScheduleInput | None = None
    tags: list[str] | None = None
    target_url: str | None = None


class KeywordBulkItemResult(BisibilityModel):
    keyword_id: KeywordId
    status: str


class KeywordBulkResponse(BisibilityModel):
    operation: KeywordBulkOperation
    results: list[KeywordBulkItemResult]


class RankCheckAttempt(BisibilityModel):
    message: str
    provider: str


class RankCheck(BisibilityModel):
    attempts: list[RankCheckAttempt] | None = None
    checked_at: str
    cost_cents: float | None
    error: str | None
    id: CheckId
    keyword_id: KeywordId
    position: int | None
    previous_position: int | None
    provider: str
    ranking_url: str | None
    status: str


class RankHistoryExportRow(BisibilityModel):
    checked_at: str
    id: CheckId
    keyword: str
    keyword_id: KeywordId
    position: int | None
    previous_position: int | None
    ranking_url: str | None


RankHistoryExportResponse: TypeAlias = ListResponse[RankHistoryExportRow]


class RunRankCheckInput(BisibilityModel):
    provider_id: str | None = None


class Signal(BisibilityModel):
    created_at: str
    happened_at: str
    id: SignalId
    keyword_id: KeywordId | None
    payload: JsonObject | None
    project_id: ProjectId
    public_id: SignalId
    severity: SignalSeverity
    source: SignalSource
    type: str
    url: str | None


class AnalyticsConnection(BisibilityModel):
    id: ConnectionId
    label: str
    provider: str


class PageTrafficSnapshot(BisibilityModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    bounce_rate: float | None
    created_at: str
    date: str
    engagement_rate: float | None
    key_events: float | None
    path: str
    provider: str
    scroll_depth: float | None
    sessions: int
    updated_at: str
    visit_duration_seconds: float | None
    visitors: int | None
    window_days: int


class PageTrafficSnapshotsResponse(BisibilityModel):
    offset: int
    rows: list[PageTrafficSnapshot]
    total_count: int


class SearchPerformanceQueryStat(BisibilityModel):
    clicks: int
    ctr: float
    impressions: int
    page: str | None = None
    position: float
    query: str


class SearchPerformanceQueryStatsResponse(BisibilityModel):
    connection: AnalyticsConnection
    rows: list[SearchPerformanceQueryStat]


class TrafficSyncRun(BisibilityModel):
    connection_id: ConnectionId
    error: str | None = None
    error_class: str | None = None
    provider: str
    rows_fetched: int
    rows_matched: int
    rows_upserted: int
    status: TrafficSyncStatus
    truncated: bool


class TrafficSyncSkipped(BisibilityModel):
    provider: str
    reason: TrafficSyncSkipReason


class TrafficSyncSummary(BisibilityModel):
    connections: int
    keyword_snapshots: int
    page_snapshots: int
    project_id: ProjectId
    runs: list[TrafficSyncRun]
    skipped: list[TrafficSyncSkipped]


class CreateSignalInput(BisibilityModel):
    happened_at: str | datetime | None = None
    keyword_id: KeywordId | None = None
    payload: JsonObject | None = None
    severity: SignalSeverity | None = None
    source: SignalCreateSource
    type: str
    url: str | None = None


def _validate_alert_targets(
    target_type: AlertTargetType | None,
    target_ids: list[str] | None,
) -> None:
    if target_type is None:
        if target_ids:
            raise ValueError("target_type is required when target_ids are provided.")
        return
    if target_type == "all":
        if target_ids:
            raise ValueError("target_ids must be empty when target_type is 'all'.")
        return
    for index, target_id in enumerate(target_ids or []):
        if target_type == "keyword":
            require_public_id(target_id, "kw", field=f"target_ids[{index}]")
        else:
            require_public_id(target_id, "tag", field=f"target_ids[{index}]")


class AlertRule(BisibilityModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: AlertRuleId
    change_pct: float | None = None
    channel: str | None = None
    channels: list[AlertChannel] | None = None
    condition: str | None = None
    condition_type: AlertConditionType | None = None
    competitor_domain: str | None = None
    enabled: bool | None = None
    fires: str | None = None
    name: str | None = None
    period: str | None = None
    recipient_ids: list[UserId]
    scope: str | None = None
    serp_feature: str | None = None
    severity: str | None = None
    status: str | None = None
    target_ids: list[KeywordId | TagId]
    target_type: AlertTargetType
    threshold_position: int | None = None
    top_n: int | None = None

    @model_validator(mode="after")
    def validate_targets(self) -> AlertRule:
        _validate_alert_targets(self.target_type, self.target_ids)
        return self


class AlertRuleInput(BisibilityModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    channels: list[AlertChannel] | None = None
    change_pct: float | None = None
    competitor_domain: str | None = None
    condition_type: AlertConditionType
    enabled: bool | None = None
    name: str
    serp_feature: str | None = None
    recipient_ids: list[UserId] | None = None
    target_ids: list[KeywordId | TagId] | None = None
    target_type: AlertTargetType | None = None
    threshold_position: int | None = None
    top_n: int | None = None

    @model_validator(mode="after")
    def validate_targets(self) -> AlertRuleInput:
        _validate_alert_targets(self.target_type, self.target_ids)
        return self


class AlertRuleDeleteResult(BisibilityModel):
    deleted: bool


class TriggeredAlert(BisibilityModel):
    action: str | None = None
    ctas: list[str] | None = None
    current: str | None = None
    headline: str | None = None
    id: TriggeredAlertId
    keyword: str | None = None
    previous: str | None = None
    rule: str | None = None
    severity: str | None = None
    unread: bool | None = None
    when: str | None = None


class TriggeredAlertMuteResult(BisibilityModel):
    muted: Literal[True]
    snoozed_until: str | None


class TriggeredAlertsReadResult(BisibilityModel):
    updated: int = Field(ge=0)


class TeamMember(BisibilityModel):
    color: str | None = None
    email: str
    id: MemberId
    initials: str | None = None
    name: str | None = None
    role: str | None = None
    role_value: TeamRoleValue | None = None


class TeamInvite(BisibilityModel):
    email: str
    expires_label: str | None = None
    id: InviteId
    invited_label: str | None = None
    role: str | None = None
    role_value: TeamInviteRole | None = None


class CreateTeamInviteInput(BisibilityModel):
    email: str
    role: TeamInviteRole


class CreatedTeamInvite(BisibilityModel):
    expires_at: str
    id: InviteId
    invite_link: str


class RevokedTeamInvite(BisibilityModel):
    id: InviteId


class TeamInviteResendResult(BisibilityModel):
    expires_at: str
    id: InviteId
    invite_link: str


class TeamMemberMutationResult(BisibilityModel):
    id: MemberId


class TeamMemberRolePatch(BisibilityModel):
    role: TeamInviteRole


class TeamMemberRoleResult(BisibilityModel):
    id: MemberId
    role: TeamInviteRole


class SitemapSnapshotSummary(BisibilityModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    fetched_at: str
    sitemap_url: str
    url_count: int = Field(ge=0)


class SitemapMonitor(BisibilityModel):
    enabled: bool
    id: ProjectId
    latest_snapshot: SitemapSnapshotSummary | None
    project_id: ProjectId
    sitemap_url: str | None
    status: SitemapMonitorStatus


SitemapMonitorListResponse: TypeAlias = ListResponse[SitemapMonitor]


class SitemapMonitorPatch(BisibilityModel):
    enabled: bool


class ProviderCredentialsInput(BisibilityModel):
    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("api_key", "apiKey"),
    )
    endpoint: str | None = None
    login: str | None = None
    secret: str | None = None


class ConnectProviderInput(BisibilityModel):
    cost_per_check: float | None = None
    credentials: ProviderCredentialsInput | None = None
    enabled: bool | None = None
    login: str | None = None
    primary: bool | None = None
    priority: int | None = None
    secret: str | None = None


class TestProviderConnectionInput(BisibilityModel):
    credentials: ProviderCredentialsInput | None = None
    login: str | None = None
    secret: str | None = None


class ProviderSettingsInput(BisibilityModel):
    enabled: bool | None = None
    primary: bool | None = None
    priority: int | None = None


class ProviderMetaRow(BisibilityModel):
    label: str
    value: str


class ProviderCredentialField(BisibilityModel):
    label: str
    name: str
    placeholder: str
    type: str | None = None


class ProviderDrawerDefaults(BisibilityModel):
    cost_per_check: float | None = None
    depth: str | None = None
    device: str | None = None
    enabled: bool | None = None
    language: str | None = None
    location: str | None = None
    login: str | None = None
    primary: bool | None = None
    priority: int | None = None
    secret: str | None = None


class ProviderDrawer(BisibilityModel):
    activities: list[ProviderMetaRow]
    cost_help: str
    credential_fields: list[ProviderCredentialField]
    defaults: ProviderDrawerDefaults
    env_hint: str
    primary_toggle_label: str


class Provider(BisibilityModel):
    description: str | None = None
    drawer: ProviderDrawer | None = None
    enabled: bool | None = None
    icon: str | None = None
    id: str
    connection_id: ConnectionId | None = None
    logo_domain: str | None = None
    meta: list[ProviderMetaRow] | None = None
    name: str | None = None
    primary: bool | None = None
    priority: int | None = None
    secondary_action: str | None = None
    status: str | None = None
    tint: str | None = None


class ProviderConnection(BisibilityModel):
    id: ConnectionId
    cost_per_check_cents: float | None = None
    created_at: str | None = None
    credentials_hash: str | None = None
    enabled: bool | None = None
    is_primary: bool | None = None
    kind: ProviderKind | str | None = None
    last_used_at: str | None = None
    priority: int | None = None
    project_id: ProjectId | None = None
    provider: ProviderId | str | None = None
    status: str | None = None
    updated_at: str | None = None


class ProviderTestResult(BisibilityModel):
    ok: bool
    message: str | None = None
    balance: float | None = None


class ProviderDisconnectResult(BisibilityModel):
    ok: bool


class SavedViewFilters(BisibilityModel):
    change: Literal["any", "up", "down", "new", "lost"] | None = None
    contains: str | None = None
    country: Literal["all", "us", "gb", "de", "pl"] | None = None
    device: Literal["all", "desktop", "mobile"] | None = None
    position: list[Literal["top3", "top10", "11-50", "51-100"]] | None = None
    serp: list[Literal["featured", "paa", "sitelinks", "image", "video", "ai"]] | None = None
    tags: list[str] | None = None
    vol_max: int | None = Field(default=None, validation_alias=AliasChoices("vol_max", "volMax"))
    vol_min: int | None = Field(default=None, validation_alias=AliasChoices("vol_min", "volMin"))
    wrong_url: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("wrong_url", "wrongUrl"),
    )


class SavedViewConfig(BisibilityModel):
    filters: SavedViewFilters | None = None
    search: str | None = None


class CreateSavedViewInput(BisibilityModel):
    config: SavedViewConfig
    name: str


class SavedView(BisibilityModel):
    config: SavedViewConfig
    created_at: str
    created_by_id: UserId | None
    id: ViewId
    name: str


class SavedViewDeleteResult(BisibilityModel):
    deleted: bool


class SavedKeywordTrendPoint(BisibilityModel):
    month: int
    search_volume: int | None = None
    year: int


class SavedKeyword(BisibilityModel):
    cpc: float | None = None
    difficulty: int | None = None
    id: SavedKeywordId
    intent: str | None = None
    location: str
    saved_at: str
    source_seed: str | None = None
    text: str
    trend: list[SavedKeywordTrendPoint]
    variant_count: int
    volume: int | None = None


class SavedKeywordInput(BisibilityModel):
    cpc_cents: int | None = None
    difficulty: int | None = None
    intent: str | None = None
    keyword: str
    location: str | None = None
    search_volume: int | None = None
    source_seed: str | None = None
    variant_count: int | None = None


SavedKeywordItem: TypeAlias = str | SavedKeywordInput | Mapping[str, Any]


class CreateSavedKeywordsInput(BisibilityModel):
    keywords: list[SavedKeywordItem]


class CreateSavedKeywordResult(BisibilityModel):
    keyword: str
    status: Literal["created", "skipped"]


class CreateSavedKeywordsResponse(BisibilityModel):
    duplicate_count: int
    results: list[CreateSavedKeywordResult]
    saved_count: int


class SavedKeywordDeleteResult(BisibilityModel):
    removed_count: int


class AddCompetitorInput(BisibilityModel):
    domain: str
    label: str | None = None


class Competitor(BisibilityModel):
    domain: str
    id: CompetitorId
    initials: str | None = None
    label: str | None = None


class CompetitorColumn(BisibilityModel):
    domain: str
    id: CompetitorId | None = None
    kind: str
    label: str


class CompetitorShare(BisibilityModel):
    color: str
    domain: str
    id: CompetitorId | None = None
    initials: str
    kind: str
    label: str
    share_of_voice: int
    shared_keywords: int


class HeadToHeadRow(BisibilityModel):
    gap: int | None
    keyword: str
    ranks: dict[str, int | None]


class CompetitorMarket(BisibilityModel):
    checked_keyword_count: int
    columns: list[CompetitorColumn]
    competitor_count: int
    country: str
    device: str
    engine: str
    has_rank_data: bool
    key: str
    rows: list[HeadToHeadRow]
    shares: list[CompetitorShare]
    shared_keyword_count: int
    tracked_keyword_count: int


class SuggestedCompetitor(BisibilityModel):
    domain: str
    initials: str
    overlap: int


class CompetitorListMeta(ListMeta):
    markets: list[CompetitorMarket] | None = None
    suggestions: list[SuggestedCompetitor] | None = None


class ListCompetitorsResponse(ListResponse[Competitor]):
    meta: CompetitorListMeta


class CompetitorRemoveResult(BisibilityModel):
    removed: bool


class NotificationPreferences(BisibilityModel):
    alert_email: bool
    alert_in_app: bool
    alert_slack: bool
    alert_webhook: bool
    check_email: bool
    check_in_app: bool
    email: str | None = None
    email_verification: Literal["unverified", "verified"] | None = None
    import_email: bool
    import_in_app: bool
    invite_email: bool
    invite_in_app: bool
    project_id: ProjectId
    slack_available: bool | None = None
    webhook_available: bool | None = None


class NotificationPreferencesPatch(BisibilityModel):
    alert_email: bool | None = None
    alert_in_app: bool | None = None
    alert_slack: bool | None = None
    alert_webhook: bool | None = None
    check_email: bool | None = None
    check_in_app: bool | None = None
    import_email: bool | None = None
    import_in_app: bool | None = None
    invite_email: bool | None = None
    invite_in_app: bool | None = None


class Webhook(BisibilityModel):
    created_at: str
    description: str | None
    enabled: bool
    id: WebhookEndpointId
    last_delivery_at: str | None
    updated_at: str
    url: str


class WebhookCreateInput(BisibilityModel):
    description: str | None = None
    enabled: bool | None = None
    hmac_secret: str
    url: str


class WebhookUpdateInput(BisibilityModel):
    description: str | None = None
    enabled: bool | None = None
    hmac_secret: str | None = None
    url: str | None = None

    @field_validator("hmac_secret")
    @classmethod
    def validate_hmac_secret(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            raise ValueError(
                "hmac_secret must be a non-empty string when provided; "
                "omit it to leave the secret unchanged"
            )
        return value


class CloudImportJob(BisibilityModel):
    counts: JsonObject | None = None
    created_at: str | None = None
    error: str | None = None
    finished_at: str | None = None
    id: CloudImportId | None = None
    progress: int
    started_at: str | None = None
    state: CloudImportState


class CloudImportCompatibility(BisibilityModel):
    app_version: str
    latest_migration: str | None
    schema_versions_supported: list[Literal[5]]


CloudImportMarket: TypeAlias = Literal[
    "United States",
    "United Kingdom",
    "Canada",
    "Australia",
    "Germany",
    "France",
    "Spain",
    "Italy",
    "Netherlands",
    "Sweden",
    "Poland",
    "Ireland",
    "Portugal",
    "Belgium",
    "Switzerland",
    "Austria",
    "Denmark",
    "Norway",
    "Finland",
    "Brazil",
    "Mexico",
    "India",
    "Japan",
    "Singapore",
    "New Zealand",
    "South Africa",
    "United Arab Emirates",
]
CloudImportAlertConditionType: TypeAlias = Literal[
    "change_pct",
    "competitor_overtake",
    "ctr_drop",
    "downtrend",
    "enters_top_n",
    "exits_top_n",
    "position_drop",
    "serp_feature",
    "threshold",
    "url_mismatch",
]
CloudImportAlertTargetType: TypeAlias = Literal["all", "keyword", "tag"]
CloudImportSavedViewSurface: TypeAlias = Literal["keywords", "competitors"]
CloudImportPosition: TypeAlias = Annotated[int | None, Field(ge=1)]
CloudImportTargetUrl: TypeAlias = Annotated[str | None, Field(max_length=500)]


class CloudImportModel(BisibilityModel):
    """Strict model base for the versioned cloud-import contract."""

    model_config = ConfigDict(extra="forbid", populate_by_name=False)


class CloudImportV5Model(CloudImportModel):
    version: Literal[5]

    @field_validator("version", mode="before")
    @classmethod
    def validate_version_type(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("version must be the integer 5")
        return value


class CloudImportRankingHistory(CloudImportModel):
    checkedAt: str
    position: CloudImportPosition = None
    previousPosition: CloudImportPosition = None
    rankingUrl: CloudImportTargetUrl = None


class CloudImportKeyword(CloudImportModel):
    device: Device
    id: KeywordId
    keyword: Annotated[str, Field(min_length=1, max_length=180)]
    location: CloudImportMarket
    rankingHistory: Annotated[list[CloudImportRankingHistory], Field(max_length=5000)] | None = None
    tags: (
        Annotated[list[Annotated[str, Field(min_length=1, max_length=48)]], Field(max_length=12)]
        | None
    ) = None
    target_url: CloudImportTargetUrl = None


class CloudImportCompetitor(CloudImportModel):
    domain: Annotated[str, Field(min_length=1, max_length=253)]
    id: CompetitorId
    label: Annotated[str, Field(max_length=80)] | None = None


class CloudImportKeywordAlertTarget(CloudImportModel):
    keyword_id: KeywordId
    type: Literal["keyword"]
    device: Device | None = None
    keyword: Annotated[str, Field(min_length=1, max_length=180)] | None = None
    location: CloudImportMarket | None = None


class CloudImportTagAlertTarget(CloudImportModel):
    tag: Annotated[str, Field(min_length=1, max_length=80)]
    type: Literal["tag"]


CloudImportAlertRuleTarget: TypeAlias = Annotated[
    CloudImportKeywordAlertTarget | CloudImportTagAlertTarget,
    Field(discriminator="type"),
]


class CloudImportAlertRule(CloudImportModel):
    id: AlertRuleId
    name: Annotated[str, Field(min_length=1, max_length=120)]
    change_pct: float | None = None
    channels: list[AlertChannel] | None = None
    competitor_domain: str | None = None
    condition_type: CloudImportAlertConditionType | None = None
    drop_positions: CloudImportPosition = None
    enabled: bool | None = None
    serp_feature: str | None = None
    target_type: CloudImportAlertTargetType | None = None
    targets: Annotated[list[CloudImportAlertRuleTarget], Field(max_length=1000)] | None = None
    threshold_position: CloudImportPosition = None
    top_n: CloudImportPosition = None


class CloudImportNotificationPreference(CloudImportModel):
    alert_email: bool | None = None
    alert_in_app: bool | None = None
    check_email: bool | None = None
    check_in_app: bool | None = None
    import_email: bool | None = None
    import_in_app: bool | None = None
    invite_email: bool | None = None
    invite_in_app: bool | None = None
    report_email: bool | None = None


class CloudImportSavedView(CloudImportModel):
    id: ViewId
    name: Annotated[str, Field(min_length=1, max_length=120)]
    config: Any | None = None
    surface: CloudImportSavedViewSurface | None = None


class CloudImportPackage(CloudImportV5Model):
    """Exact version-5 export package accepted by ``POST /cloud/import``."""

    project_id: ProjectId
    keywords: Annotated[list[CloudImportKeyword], Field(max_length=500)]
    alert_rules: Annotated[list[CloudImportAlertRule], Field(max_length=500)]
    competitors: Annotated[list[CloudImportCompetitor], Field(max_length=500)]
    notification_preferences: Annotated[
        list[CloudImportNotificationPreference], Field(max_length=50)
    ]
    saved_views: Annotated[list[CloudImportSavedView], Field(max_length=500)]
    exported_at: str | None = None
    scope: Literal["current", "history"] | None = None


CloudImportCounts: TypeAlias = dict[str, int]


class CloudImportFinalizeResponse(BisibilityModel):
    counts: CloudImportCounts
    job_id: CloudImportId
    state: Literal["done"]


class CloudImportSessionTotals(CloudImportModel):
    keywords: int | None = Field(default=None, ge=0)
    rank_checks: int | None = Field(default=None, ge=0)


class CloudImportSessionCreate(CloudImportV5Model):
    chunk_count: int = Field(ge=1, le=500)
    source_project_id: ProjectId
    totals: CloudImportSessionTotals | None = None


class CloudImportChunkLimits(BisibilityModel):
    max_body_bytes: int = Field(ge=1)
    max_history_rows: int = Field(ge=1)
    max_keywords: int = Field(ge=1)


class CloudImportSessionCreateResponse(BisibilityModel):
    chunk_limits: CloudImportChunkLimits
    session_id: CloudImportId
    state: Literal["receiving"]


class CloudImportChunkResponse(BisibilityModel):
    chunk_count: int = Field(ge=1)
    chunks_received: int = Field(ge=0)
    state: Literal["receiving"]


class CloudImportSourceKeyword(CloudImportModel):
    device: Device
    location: CloudImportMarket
    text: str


class CloudImportSessionSections(CloudImportModel):
    alert_rules: Annotated[list[CloudImportAlertRule], Field(max_length=500)] | None = None
    competitors: Annotated[list[CloudImportCompetitor], Field(max_length=500)] | None = None
    notification_preferences: (
        Annotated[list[CloudImportNotificationPreference], Field(max_length=50)] | None
    ) = None
    saved_views: Annotated[list[CloudImportSavedView], Field(max_length=500)] | None = None
    source_keyword_ids: dict[str, CloudImportSourceKeyword] | None = None


class CloudImportKeywordUploadChunk(CloudImportModel):
    checksum: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    kind: Literal["keywords"]
    keywords: Annotated[list[CloudImportKeyword], Field(max_length=500)]


class CloudImportSectionsUploadChunk(CloudImportModel):
    checksum: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    kind: Literal["sections"]
    sections: CloudImportSessionSections


CloudImportUploadChunk: TypeAlias = Annotated[
    CloudImportKeywordUploadChunk | CloudImportSectionsUploadChunk,
    Field(discriminator="kind"),
]


class MigrationTokenCreator(BisibilityModel):
    email: str
    name: str


class MigrationToken(BisibilityModel):
    created_at: str
    created_by: MigrationTokenCreator | None = None
    expires_at: str
    id: TransferTokenId
    scope: MigrationScope
    single_use: bool


class IssuedMigrationToken(MigrationToken):
    import_job: CloudImportJob
    token: str


class MintMigrationTokenInput(BisibilityModel):
    scope: MigrationScope | None = None


class MigrationTokenListMeta(ListMeta):
    import_job: CloudImportJob | None = None


class ListMigrationTokensResponse(ListResponse[MigrationToken]):
    meta: MigrationTokenListMeta


class MigrationTokenRevokeResult(BisibilityModel):
    id: TransferTokenId
    revoked_at: str


class HealthServices(BisibilityModel):
    app: str
    database: str


class HealthProviders(BisibilityModel):
    serp: list[str]


class HealthResponse(BisibilityModel):
    status: Literal["degraded", "ok"]


class LivenessServices(BisibilityModel):
    app: Literal["ok"]
    appRelease: str
    appRevision: str


class LivenessResponse(BisibilityModel):
    status: Literal["ok"]


class ReadinessServices(LivenessServices):
    database: Literal["degraded", "ok"]
    migrations: Literal["incomplete", "ready", "unknown"]


class ReadinessResponse(BisibilityModel):
    status: Literal["degraded", "ok"]


class ProviderRateOption(BisibilityModel):
    key: str
    label: str
    short_label: str
    turnaround: str
    unit_cost_cents: float
    unit_cost_usd: float


class ProviderRatePlan(BisibilityModel):
    included_checks: int
    label: str
    monthly_price_cents: float
    monthly_price_usd: float
    plan_key: str


class ProviderRate(BisibilityModel):
    checked_at: str
    label: str
    notes: str | None = None
    options: list[ProviderRateOption] | None = None
    plans: list[ProviderRatePlan] | None = None
    pricing_model: ProviderPricingModel
    provider_id: str
    source_url: str


class CostEstimate(BisibilityModel):
    checks_per_run: int
    effective_cost_per_check_cents: float
    exceeds_largest_plan: bool
    exceeds_selected_plan: bool
    monthly_checks: int
    monthly_cost_cents: float
    monthly_cost_usd: float
    pricing_model: ProviderPricingModel
    provider_id: str
    rate_checked_at: str
    rate_source_url: str
    selected_option: ProviderRateOption | None = None
    selected_plan: ProviderRatePlan | None = None


class CostEstimateOptions(BisibilityModel):
    keywords: int
    devices: int | None = None
    frequency: CostEstimateFrequency | None = None
    locations: int | None = None
    option: str | None = None
    plan: str | None = None
    provider: CostEstimateProvider | None = None


class Capability(BisibilityModel):
    description: str
    input_schema: JsonObject
    name: str
    operationId: str


class OpenApiDocument(BisibilityModel):
    info: JsonObject
    openapi: str
    paths: JsonObject


class PaginationOptions(BisibilityModel):
    cursor: CursorV3 | None = None
    limit: int | None = None


class SearchLocationsOptions(BisibilityModel):
    q: str = Field(min_length=2, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    limit: int | None = Field(default=None, ge=1, le=100)


class ListRankedKeywordSuggestionsOptions(BisibilityModel):
    connection_id: ConnectionId | None = None
    fresh: bool | None = None
    limit: int | None = Field(default=None, ge=1, le=100)
    offset: int | None = Field(default=None, ge=0, le=900, multiple_of=100)


class KeywordResearchOptions(BisibilityModel):
    seed: str = Field(min_length=1, max_length=80)
    connection_id: ConnectionId | None = None
    estimate_only: bool | None = None
    fresh: bool | None = None
    include_clickstream: bool | None = None
    max_cost_cents: int | None = Field(default=None, ge=1)
    mode: KeywordResearchMode | None = None
    result_limit: Literal[100, 300, 500] | None = None


class AnalyzeBacklinksOptions(BisibilityModel):
    target: str
    target_scope: Literal["site", "page"] | None = None
    include_subdomains: bool | None = None
    result_limit: Literal[100, 300, 500, 1000] | None = None
    mode: Literal["as_is", "one_per_domain"] | None = None
    estimate_only: bool | None = None
    fresh: bool | None = None
    max_cost_cents: int | None = Field(default=None, ge=1)


class LoadMoreBacklinkRowsOptions(BisibilityModel):
    target: str
    target_scope: Literal["site", "page"]
    include_subdomains: bool
    limit: int = Field(ge=100, le=1000, multiple_of=100)


class KeywordMetricsInput(BisibilityModel):
    keywords: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        min_length=1, max_length=700
    )
    connection_id: ConnectionId | None = None
    estimate_only: bool | None = None
    fresh: bool | None = None
    include_clickstream: bool | None = None
    max_cost_cents: int | None = Field(default=None, ge=1)


class ListTrafficSnapshotsOptions(BisibilityModel):
    start_date: str | date
    end_date: str | date
    limit: int | None = Field(default=None, ge=1, le=200)
    offset: int | None = Field(default=None, ge=0)
    path: list[str] | None = Field(default=None, max_length=50)


class ListSearchPerformanceQueryStatsOptions(BisibilityModel):
    start_date: str | date
    end_date: str | date
    connection_id: ConnectionId | None = None
    limit: int | None = Field(default=None, ge=1, le=1000)
    query: str | None = Field(default=None, max_length=1000)


class ListKeywordsOptions(PaginationOptions):
    country: str | None = None
    device: Device | None = None
    intent: str | None = None
    position_gt: int | None = Field(
        default=None,
        validation_alias=AliasChoices("position_gt", "positionGt"),
    )
    position_lt: int | None = Field(
        default=None,
        validation_alias=AliasChoices("position_lt", "positionLt"),
    )
    search: str | None = None
    sort: KeywordSort | None = None
    tag: str | None = None
    topic: str | None = None


class ListRankChecksOptions(PaginationOptions):
    since: str | date | datetime | None = None
    status: RankCheckStatus | None = None
    until: str | date | datetime | None = None


class RankHistoryExportOptions(PaginationOptions):
    format: RankHistoryExportFormat | None = None
    granularity: RankHistoryGranularity | None = None
    keyword_ids: list[KeywordId] | None = Field(default=None, max_length=500)
    range: RankHistoryRange | None = None


class ListSignalsOptions(PaginationOptions):
    from_: str | date | datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("from_", "from"),
        serialization_alias="from",
    )
    source: SignalSource | None = None
    to: str | date | datetime | None = None
    type: str | None = None
