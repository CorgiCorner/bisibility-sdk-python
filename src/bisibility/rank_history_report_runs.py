from typing import Literal

from .model_base import BisibilityModel
from .public_ids import KeywordId, RankCheckRunId


class RankHistoryRunRecordBase(BisibilityModel):
    recorded_at: str
    started_at: str | None
    finished_at: str | None
    status: str
    blocked_reason: str | None
    run_id: RankCheckRunId
    rank_check_state: str


class RankHistoryReportRunItem(RankHistoryRunRecordBase):
    kind: Literal["rank_check_run_item"]
    id: str
    keyword_id: KeywordId
    keyword: str
    not_before: str | None
    run_status: str
    run_outcome: str | None
    scope_membership: str


class RankHistoryReportRunCounts(BisibilityModel):
    requested: int
    total: int
    completed: int
    failed: int
    deferred: int
    skipped: int
    cancelled: int


class RankHistoryReportRun(RankHistoryRunRecordBase):
    kind: Literal["rank_check_run"]
    id: RankCheckRunId
    planned_for: str | None
    launched_at: str | None
    outcome: str | None
    trigger: str
    selection_kind: str
    scope_membership: str
    counts: RankHistoryReportRunCounts
