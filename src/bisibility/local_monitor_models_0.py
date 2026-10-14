from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BeforeValidator, Field

from .model_base import BisibilityModel
from .public_ids import (
    KeywordId,
    LocalMeasurementTargetId,
    LocalMonitorId,
    LocalMonitorRunId,
    ProjectId,
)


def _exact_local_version(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value != 1:
        raise ValueError("Unsupported Local response version")
    return value


LocalMonitorVersion = Annotated[Literal[1], BeforeValidator(_exact_local_version)]


class LocalMonitorRunResultResponseDataProtocol(BisibilityModel):
    geometry: str
    matcher: str
    normalizer_versions: list[str] = Field(max_length=100)
    metric_definition: str


class LocalMonitorRunResultResponseDataFreshnessPolicy(BisibilityModel):
    basis: str | None
    fresh_for_ms: float | None = Field(strict=True, allow_inf_nan=False)
    freshness_reason: str | None
    policy_epoch: str | None
    configuration_revision: str | None
    semantics: str


class LocalMonitorRunResultResponseDataPointsItemReceipt(BisibilityModel):
    target_id: LocalMeasurementTargetId
    status: str
    version: int = Field(strict=True, ge=0)
    acceptance: str | None
    known_accepted_task_count: int | None = Field(strict=True, ge=0)
    collected: bool = Field(strict=True)
    cancellation_requested: bool = Field(strict=True)
    financial_state: str | None
    owner_retained: bool = Field(strict=True)
    resolution: str
    accounting_pending: bool | None = Field(strict=True)
    reconciliation_reason: str | None


class LocalMonitorRunResultResponseDataPointsItem(BisibilityModel):
    id: LocalMeasurementTargetId
    keyword_id: KeywordId
    keyword: str
    ordinal: int = Field(strict=True, ge=0)
    row: int = Field(strict=True, ge=0)
    column: int = Field(strict=True, ge=0)
    latitude: str = Field(pattern="^-?[0-9]{1,3}\\.[0-9]{7}$")
    longitude: str = Field(pattern="^-?[0-9]{1,3}\\.[0-9]{7}$")
    surface: str
    cutoff: int = Field(strict=True, ge=0)
    zoom: float | None = Field(strict=True, ge=0, allow_inf_nan=False)
    language: str
    device: str
    operating_system: str | None
    observed_at: str | None
    recorded_at: str | None
    position: float | None = Field(strict=True, allow_inf_nan=False)
    observed_position: float | None = Field(strict=True, allow_inf_nan=False)
    evidence: str
    reason: str | None
    freshness: str
    freshness_reason: str | None
    identity_match: str
    scope_class: str
    receipt: LocalMonitorRunResultResponseDataPointsItemReceipt


class LocalMonitorRunResultResponseDataGridsItemCounts(BisibilityModel):
    expected: int = Field(strict=True, ge=0)
    measured: int = Field(strict=True, ge=0)
    metric_eligible: int = Field(strict=True, ge=0)
    ranked: int = Field(strict=True, ge=0)
    known_absent: int = Field(strict=True, ge=0)
    unknown: int = Field(strict=True, ge=0)
    never_checked: int = Field(strict=True, ge=0)
    failed: int = Field(strict=True, ge=0)
    stale: int = Field(strict=True, ge=0)
    unsupported: int = Field(strict=True, ge=0)
    fresh_determinate: int | None = Field(strict=True, ge=0)
    unknown_freshness: int = Field(strict=True, ge=0)
    comparable: int = Field(strict=True, ge=0)


class LocalMonitorRunResultResponseDataGridsItem(BisibilityModel):
    keyword_id: KeywordId
    keyword: str
    grid_revision_key: str
    identity_revision_id: str
    top_n: int = Field(strict=True, ge=0)
    size: int = Field(strict=True)
    point_ids: list[LocalMeasurementTargetId] = Field(max_length=49)
    expected: int = Field(strict=True, ge=0)
    observed_rate: float | None = Field(strict=True, allow_inf_nan=False)
    observed_coverage: float | None = Field(strict=True, allow_inf_nan=False)
    data_coverage: float | None = Field(strict=True, allow_inf_nan=False)
    sample_bounds: tuple[float, float] | None = Field(min_length=2, max_length=2)
    counts: LocalMonitorRunResultResponseDataGridsItemCounts
    freshness: str
    comparison: str
    scope: str


class LocalMonitorRunResultResponseDataReceiptCounts(BisibilityModel):
    items: int = Field(strict=True, ge=0)
    complete: int = Field(strict=True, ge=0)
    acceptance_unresolved: int = Field(strict=True, ge=0)
    accounting_pending: int = Field(strict=True, ge=0)
    unavailable: int = Field(strict=True, ge=0)
    retained_owners: int = Field(strict=True, ge=0)


class LocalMonitorRunResultResponseDataReceipt(BisibilityModel):
    id: LocalMonitorRunId
    version: int = Field(strict=True, ge=0)
    cancellation_requested: bool = Field(strict=True)
    expected_count: int = Field(strict=True, ge=0)
    items: list[LocalMonitorRunResultResponseDataPointsItemReceipt] = Field(max_length=100)
    counts: LocalMonitorRunResultResponseDataReceiptCounts


class LocalMonitorRunResultResponseData(BisibilityModel):
    version: LocalMonitorVersion
    project_id: ProjectId
    monitor_id: LocalMonitorId
    run_id: LocalMonitorRunId
    as_of: str
    definition_revision_id: str
    identity_revision_id: str
    subject: str
    protocol: LocalMonitorRunResultResponseDataProtocol
    financial_basis: str
    freshness_policy: LocalMonitorRunResultResponseDataFreshnessPolicy | None
    points: list[LocalMonitorRunResultResponseDataPointsItem] = Field(max_length=100)
    grids: list[LocalMonitorRunResultResponseDataGridsItem] = Field(max_length=100)
    created_at: str
    definition_revision: int = Field(strict=True, ge=0)
    receipt: LocalMonitorRunResultResponseDataReceipt


class LocalMonitorRunResultResponse(BisibilityModel):
    data: LocalMonitorRunResultResponseData


class LocalMonitorRunHistoryResponseDataWindow(BisibilityModel):
    from_: str | None = Field(alias="from")
    to: str
    time_basis: str


class LocalMonitorRunHistoryResponseDataItemsItem(BisibilityModel):
    run_id: LocalMonitorRunId
    created_at: str
    definition_revision: int = Field(strict=True, ge=0)
    mode: str


class LocalMonitorRunHistoryResponseData(BisibilityModel):
    version: LocalMonitorVersion
    project_id: ProjectId
    monitor_id: LocalMonitorId
    as_of: str
    window: LocalMonitorRunHistoryResponseDataWindow | None
    eligible_total: int | None = Field(strict=True, ge=0)
    next_cursor: str | None = Field(min_length=1, max_length=8000)
    items: list[LocalMonitorRunHistoryResponseDataItemsItem] = Field(max_length=20)


class LocalMonitorRunHistoryResponse(BisibilityModel):
    data: LocalMonitorRunHistoryResponseData


class LocalMonitorPointHistoryResponseDataItemsItem(BisibilityModel):
    id: str
    run_id: LocalMonitorRunId
    created_at: str
    observed_at: str | None
    position: float | None = Field(strict=True, allow_inf_nan=False)
    evidence: str
    reason: str | None
    freshness: str | None
    freshness_reason: str | None


class LocalMonitorPointHistoryResponseData(BisibilityModel):
    version: LocalMonitorVersion
    as_of: str
    target_id: LocalMeasurementTargetId
    scope: str
    limit: int = Field(strict=True)
    has_more: bool = Field(strict=True)
    window: LocalMonitorRunHistoryResponseDataWindow | None
    eligible_total: int | None = Field(strict=True, ge=0)
    next_cursor: str | None = Field(min_length=1, max_length=8000)
    policy_epoch: str | None
    freshness_configuration_revision: str | None
    items: list[LocalMonitorPointHistoryResponseDataItemsItem] = Field(max_length=20)


class LocalMonitorPointHistoryResponse(BisibilityModel):
    data: LocalMonitorPointHistoryResponseData
