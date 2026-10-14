from __future__ import annotations

from typing import Literal

from pydantic import Field

from .local_monitor_models_0 import LocalMonitorVersion
from .model_base import BisibilityModel
from .public_ids import (
    KeywordId,
    LocalMeasurementTargetId,
    LocalMonitorId,
    LocalMonitorRunId,
    ProjectId,
)


class LocalMonitorPointListingsResponseDataItem(BisibilityModel):
    id: str
    name: str | None
    rank_group: int | None = Field(strict=True, ge=0)
    rank_absolute: int | None = Field(strict=True, ge=0)
    promotion: str
    observed_at: str | None
    matched: str
    cid: str | None = Field(strict=True)
    place_id: str | None
    source_page: int | None = Field(strict=True, ge=0)
    source_block_id: str | None
    source_ordinal: int | None = Field(strict=True, ge=0)
    rank_scale: str | None


class LocalMonitorPointListingsResponse(BisibilityModel):
    data: list[LocalMonitorPointListingsResponseDataItem] = Field(max_length=700)


class LocalMonitorPointReportProtocol(BisibilityModel):
    geometry: str
    matcher: str
    normalizer_versions: list[str] = Field(alias="normalizerVersions", max_length=100)
    metric_definition: str = Field(alias="metricDefinition")


class LocalMonitorPointReportFreshnessPolicy(BisibilityModel):
    basis: str | None
    fresh_for_ms: float | None = Field(strict=True, alias="freshForMs", allow_inf_nan=False)
    freshness_reason: str | None = Field(alias="freshnessReason")
    policy_epoch: str | None = Field(alias="policyEpoch")
    configuration_revision: str | None = Field(alias="configurationRevision")
    semantics: str


class LocalMonitorPointReportPointsItemReceipt(BisibilityModel):
    target_id: LocalMeasurementTargetId = Field(alias="targetId")
    status: str
    version: int = Field(strict=True, ge=0)
    acceptance: str | None
    known_accepted_task_count: int | None = Field(strict=True, alias="knownAcceptedTaskCount", ge=0)
    collected: bool = Field(strict=True)
    cancellation_requested: bool = Field(strict=True, alias="cancellationRequested")
    financial_state: str | None = Field(alias="financialState")
    owner_retained: bool = Field(strict=True, alias="ownerRetained")
    resolution: str
    accounting_pending: bool | None = Field(strict=True, alias="accountingPending")
    reconciliation_reason: str | None = Field(alias="reconciliationReason")


class LocalMonitorPointReportPointsItem(BisibilityModel):
    id: LocalMeasurementTargetId
    keyword_id: KeywordId = Field(alias="keywordId")
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
    operating_system: str | None = Field(alias="operatingSystem")
    observed_at: str | None = Field(alias="observedAt")
    recorded_at: str | None = Field(alias="recordedAt")
    position: float | None = Field(strict=True, allow_inf_nan=False)
    observed_position: float | None = Field(
        strict=True, alias="observedPosition", allow_inf_nan=False
    )
    evidence: str
    reason: str | None
    freshness: str
    freshness_reason: str | None = Field(alias="freshnessReason")
    identity_match: str = Field(alias="identityMatch")
    scope_class: str = Field(alias="scopeClass")
    receipt: LocalMonitorPointReportPointsItemReceipt


class LocalMonitorPointReportGridsItemCounts(BisibilityModel):
    expected: int = Field(strict=True, ge=0)
    measured: int = Field(strict=True, ge=0)
    metric_eligible: int = Field(strict=True, alias="metricEligible", ge=0)
    ranked: int = Field(strict=True, ge=0)
    known_absent: int = Field(strict=True, alias="knownAbsent", ge=0)
    unknown: int = Field(strict=True, ge=0)
    never_checked: int = Field(strict=True, alias="neverChecked", ge=0)
    failed: int = Field(strict=True, ge=0)
    stale: int = Field(strict=True, ge=0)
    unsupported: int = Field(strict=True, ge=0)
    fresh_determinate: int | None = Field(strict=True, alias="freshDeterminate", ge=0)
    unknown_freshness: int = Field(strict=True, alias="unknownFreshness", ge=0)
    comparable: int = Field(strict=True, ge=0)


class LocalMonitorPointReportGridsItem(BisibilityModel):
    keyword_id: KeywordId = Field(alias="keywordId")
    keyword: str
    grid_revision_key: str = Field(alias="gridRevisionKey")
    identity_revision_id: str = Field(alias="identityRevisionId")
    top_n: int = Field(strict=True, alias="topN", ge=0)
    size: int = Field(strict=True)
    point_ids: list[LocalMeasurementTargetId] = Field(alias="pointIds", max_length=49)
    expected: int = Field(strict=True, ge=0)
    observed_rate: float | None = Field(strict=True, alias="observedRate", allow_inf_nan=False)
    observed_coverage: float | None = Field(
        strict=True, alias="observedCoverage", allow_inf_nan=False
    )
    data_coverage: float | None = Field(strict=True, alias="dataCoverage", allow_inf_nan=False)
    sample_bounds: tuple[float, float] | None = Field(
        alias="sampleBounds", min_length=2, max_length=2
    )
    counts: LocalMonitorPointReportGridsItemCounts
    freshness: str
    comparison: str
    scope: str


class LocalMonitorPointReport(BisibilityModel):
    version: LocalMonitorVersion
    project_id: ProjectId = Field(alias="projectId")
    monitor_id: LocalMonitorId = Field(alias="monitorId")
    run_id: LocalMonitorRunId = Field(alias="runId")
    as_of: str = Field(alias="asOf")
    definition_revision_id: str = Field(alias="definitionRevisionId")
    identity_revision_id: str = Field(alias="identityRevisionId")
    subject: str
    protocol: LocalMonitorPointReportProtocol
    financial_basis: str = Field(alias="financialBasis")
    freshness_policy: LocalMonitorPointReportFreshnessPolicy | None = Field(alias="freshnessPolicy")
    points: list[LocalMonitorPointReportPointsItem] = Field(max_length=100)
    grids: list[LocalMonitorPointReportGridsItem] = Field(max_length=100)
    report: Literal["local-point-report-v1"]
    scope: str
    coordinate_proof: str = Field(alias="coordinateProof")
    comparison: str
