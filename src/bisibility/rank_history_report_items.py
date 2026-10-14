from .model_base import BisibilityModel
from .public_ids import CheckId, KeywordId


class RankHistoryReportNormalizedItem(BisibilityModel):
    id: str
    check_id: CheckId
    keyword_id: KeywordId
    checked_at: str
    check_recorded_at: str
    observed_at: str | None
    recorded_at: str
    requested_at: str | None
    source_observed_at: str | None
    block_position: int | None
    business_name: str | None
    cid: str | None
    domain: str | None
    maps_url: str | None
    ordinal: int
    place_id: str | None
    position_in_block: int | None
    rank_absolute: int | None
    rank_group: int | None
    rank_scale: str | None
    promotion: str | None
    source_page: int | None
    source_block_id: str | None
    source_ordinal: int | None
    result_kind: str
    title: str | None
    url: str | None


class RankHistoryReportNormalizedItems(BisibilityModel):
    total_count: int
    completeness: str
    is_truncated: bool
    capacity: int
    paging: str
