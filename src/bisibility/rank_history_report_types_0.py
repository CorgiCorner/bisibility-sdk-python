from __future__ import annotations

from typing import Literal

from pydantic import Field

from .model_base import BisibilityModel
from .public_ids import CheckId, KeywordId
from .rank_history_report_items import RankHistoryReportNormalizedItem


class RankHistoryReportObservationConfiguredScope(BisibilityModel):
    device: str
    engine: str
    identity_revision: str | None
    language: str
    location: str
    policy_revision: str | None
    rank_scale: str
    result_kind: str
    surface: str
    target_revision: str | None


class RankHistoryReportObservation(BisibilityModel):
    checked_at: str
    check_recorded_at: str
    observed_at: str | None
    recorded_at: str
    requested_at: str | None
    comparison_digest: str | None
    complete_through: int | None
    completeness: str
    configured_scope: RankHistoryReportObservationConfiguredScope | None
    effective_scope: RankHistoryReportObservationConfiguredScope | None
    evidence: str
    expected_url_at_check: str | None
    freshness: str
    freshness_as_of: str
    freshness_reason: str | None
    id: CheckId
    keyword_id: KeywordId
    keyword: str
    normalization_version: str | None
    position: float | None
    provider: str | None
    ranking_url: str | None
    reason: str | None
    reported_position: float | None
    requested_depth: int | None
    normalized_items: list[RankHistoryReportNormalizedItem]
    normalized_item_count: int


class RankHistoryReportAttempt(BisibilityModel):
    checked_at: str
    check_recorded_at: str
    observed_at: str | None
    recorded_at: str
    requested_at: str | None
    deferred_reason: str | None
    error_code: str | None
    finished_at: str | None
    id: CheckId
    keyword_id: KeywordId
    keyword: str
    kind: Literal["logical_rank_check"]
    provider: str | None
    reported_provider_attempt_count: int
    started_at: str | None
    status: str


class RankHistoryReportMetadataWindow(BisibilityModel):
    basis: str
    from_: str = Field(alias="from")
    to: str


class RankHistoryReportMetadataSummaryMetricCounts(BisibilityModel):
    expected: int
    measured: int
    metric_eligible: int
    ranked: int
    known_absent: int
    unknown: int
    never_checked: int
    failed: int
    stale: int
    unsupported: int
    fresh_determinate: int | None
    unknown_freshness: int
    comparable: int


class RankHistoryReportMetadataSummaryMetricContributionsItem(BisibilityModel):
    target_id: KeywordId
    weight: float
    value: float | None
    delta: float | None


class RankHistoryReportMetadataSummaryMetricExclusionsItem(BisibilityModel):
    target_id: KeywordId
    reason: str


class RankHistoryReportMetadataSummaryMetricWeightProvenance(BisibilityModel):
    source: str | None
    period: str | None
    market: str | None


class RankHistoryReportMetadataSummaryMetric(BisibilityModel):
    metric_id: str
    definition_version: str
    as_of: str
    value: float | None
    delta: float | None
    counts: RankHistoryReportMetadataSummaryMetricCounts
    data_coverage: float | None
    observed_coverage: float | None
    freshness: str
    freshness_reason: str | None
    imputed_weight_share: float | None
    contributions: list[RankHistoryReportMetadataSummaryMetricContributionsItem]
    exclusions: list[RankHistoryReportMetadataSummaryMetricExclusionsItem]
    added: list[KeywordId] | None
    removed: list[KeywordId] | None
    composition_reason: str | None
    weight_provenance: RankHistoryReportMetadataSummaryMetricWeightProvenance
    included_count: int
    eligible_total: int
    is_truncated: bool


class RankHistoryReportMetadataSummaryMovementCounts(BisibilityModel):
    improved: int
    declined: int
    entered: int
    exited: int
    first: int
    moved: int
    re_entered: int
    steady: int
    unknown: int


class RankHistoryReportMetadataSummaryRetainedHistory(BisibilityModel):
    checks: int
    completeness: str
    targets: int


class RankHistoryReportMetadataSummaryTimeBasisBaseline(BisibilityModel):
    before: str
    not_before: str | None


class RankHistoryReportMetadataSummaryTimeBasis(BisibilityModel):
    as_of: str
    baseline: RankHistoryReportMetadataSummaryTimeBasisBaseline | None
    current_not_before: str | None


class RankHistoryReportMetadataSummary(BisibilityModel):
    comparison: str
    metric: RankHistoryReportMetadataSummaryMetric
    movement_counts: RankHistoryReportMetadataSummaryMovementCounts | None
    retained_history: RankHistoryReportMetadataSummaryRetainedHistory
    selection_digest: str
    time_basis: RankHistoryReportMetadataSummaryTimeBasis


class RankHistoryReportMetadataResolutionsItemBaseline(BisibilityModel):
    comparison_digest: str | None
    evidence: str
    freshness: str
    freshness_reason: str | None
    id: CheckId
    normalization_version: str | None
    observed_at: str | None
    position: float | None
    provider: str | None
    ranking_url: str | None
    reason: str | None
    recorded_at: str
    reported_position: float | None
    requested_depth: int | None


class RankHistoryReportMetadataResolutionsItemComparisonBoundary(BisibilityModel):
    point: RankHistoryReportMetadataResolutionsItemBaseline | None
    reason: str


class RankHistoryReportMetadataResolutionsItemLatestAttempt(BisibilityModel):
    id: CheckId
    measurement_recorded_at: str
    observed_at: str | None
    recorded_at: str | None
    status: str


class RankHistoryReportMetadataResolutionsItemLastKnown(BisibilityModel):
    baseline: RankHistoryReportMetadataResolutionsItemBaseline | None
    comparison: str
    comparison_boundary: RankHistoryReportMetadataResolutionsItemComparisonBoundary | None
    comparison_window: RankHistoryReportMetadataSummaryTimeBasisBaseline | None
    comparison_unavailable_reason: str | None
    current: RankHistoryReportMetadataResolutionsItemBaseline | None
    event: str | None
    keyword_id: KeywordId
    last_success: RankHistoryReportMetadataResolutionsItemBaseline | None
    latest_attempt: RankHistoryReportMetadataResolutionsItemLatestAttempt | None
    movement: float | None


class RankHistoryReportMetadataResolutionsItem(BisibilityModel):
    baseline: RankHistoryReportMetadataResolutionsItemBaseline | None
    comparison: str
    comparison_boundary: RankHistoryReportMetadataResolutionsItemComparisonBoundary | None
    comparison_window: RankHistoryReportMetadataSummaryTimeBasisBaseline | None
    comparison_unavailable_reason: str | None
    current: RankHistoryReportMetadataResolutionsItemBaseline | None
    event: str | None
    keyword_id: KeywordId
    last_success: RankHistoryReportMetadataResolutionsItemBaseline | None
    latest_attempt: RankHistoryReportMetadataResolutionsItemLatestAttempt | None
    movement: float | None
    current_scope_state: str
    last_known: RankHistoryReportMetadataResolutionsItemLastKnown
