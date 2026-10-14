"""Read-only rank-check run contracts, including outcomes without a check."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field, StrictBool, TypeAdapter

from .model_base import BisibilityModel
from .models import CursorV3, ListResponse
from .public_ids import ProjectId, RankCheckRunId

RunCount = Annotated[int, Field(strict=True, ge=0)]
RunNumber = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]


class RankCheckRunCounts(BisibilityModel):
    requested: RunCount
    total: RunCount
    completed: RunCount
    failed: RunCount
    deferred: RunCount
    skipped: RunCount
    cancelled: RunCount


class RankCheckRunUsage(BisibilityModel):
    actual: RunCount | None
    estimated: RunCount | None
    unit: str


class RankCheckRunNativeEstimate(BisibilityModel):
    provider_id: str | None
    unit: str | None
    quantity: RunNumber | None
    unknown_targets: RunCount


class RankCheckRunRead(BisibilityModel):
    id: RankCheckRunId
    project_id: ProjectId
    status: str
    outcome: str | None
    terminal: StrictBool
    polling_state: str
    trigger: str
    counts_basis: str
    counts: RankCheckRunCounts
    keyword_count: RunCount
    target_count: RunCount
    planned_for: str | None
    launched_at: str | None
    started_at: str | None
    finished_at: str | None
    blocked_reason: str | None
    parent_run_id: RankCheckRunId | None
    cost_cents: RunNumber | None
    usage: RankCheckRunUsage | None
    native_estimate: RankCheckRunNativeEstimate | None


class ListRankCheckRunsOptions(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    segment: Literal["history", "planned"] | None = None
    status: str | None = None
    cursor: CursorV3 | None = None
    limit: int | None = Field(default=None, strict=True, ge=1, le=200)


def _run_response_adapter(project_id: str, run_id: str) -> TypeAdapter[RankCheckRunRead]:
    def match_scope(run: RankCheckRunRead) -> RankCheckRunRead:
        if run.project_id != project_id or run.id != run_id:
            raise ValueError("Rank-check run response does not match the requested scope.")
        return run

    return TypeAdapter(Annotated[RankCheckRunRead, AfterValidator(match_scope)])


def _run_list_response_adapter(project_id: str) -> TypeAdapter[ListResponse[RankCheckRunRead]]:
    def match_scope(page: ListResponse[RankCheckRunRead]) -> ListResponse[RankCheckRunRead]:
        if any(run.project_id != project_id for run in page.data):
            raise ValueError("Rank-check run list does not match the requested project.")
        return page

    return TypeAdapter(Annotated[ListResponse[RankCheckRunRead], AfterValidator(match_scope)])
