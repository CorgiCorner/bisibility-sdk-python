from typing import Annotated, Any

from pydantic import Discriminator, Field, Tag

from .model_base import BisibilityModel
from .rank_history_report_runs import RankHistoryReportRun, RankHistoryReportRunItem
from .rank_history_report_types_0 import RankHistoryReportAttempt, RankHistoryReportObservation
from .rank_history_report_types_1 import RankHistoryReportMetadata


def _record_kind(value: Any) -> str:
    if isinstance(value, dict):
        if "kind" not in value:
            return "observation"
        kind = value["kind"]
        if kind in ("logical_rank_check", "rank_check_run", "rank_check_run_item"):
            return str(kind)
        return "__invalid__"
    return str(getattr(value, "kind", "observation"))


RankHistoryReportRecord = Annotated[
    Annotated[RankHistoryReportObservation, Tag("observation")]
    | Annotated[RankHistoryReportAttempt, Tag("logical_rank_check")]
    | Annotated[RankHistoryReportRun, Tag("rank_check_run")]
    | Annotated[RankHistoryReportRunItem, Tag("rank_check_run_item")],
    Discriminator(_record_kind),
]


class RankHistoryReportMeta(BisibilityModel):
    next_cursor: str | None = Field(min_length=1, max_length=8192)
    report: RankHistoryReportMetadata


class RankHistoryReportResponse(BisibilityModel):
    data: list[RankHistoryReportRecord]
    meta: RankHistoryReportMeta
