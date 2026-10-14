from __future__ import annotations

from typing import Literal

from .model_base import BisibilityModel
from .rank_history_report_items import RankHistoryReportNormalizedItems
from .rank_history_report_types_0 import (
    RankHistoryReportMetadataResolutionsItem,
    RankHistoryReportMetadataSummary,
    RankHistoryReportMetadataWindow,
)


class RankHistoryReportMetadata(BisibilityModel):
    version: Literal[2]
    aggregation: str
    as_of: str
    window: RankHistoryReportMetadataWindow
    summary_basis: str
    definition_version: str
    metric_id: str
    selection_digest: str
    total_count: int
    excluded_unknown_time: int
    unresolved_membership_count: int
    normalized_items: RankHistoryReportNormalizedItems
    membership: str
    summary: RankHistoryReportMetadataSummary
    resolutions: list[RankHistoryReportMetadataResolutionsItem]
