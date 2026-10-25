"""Google's known indexed state, which may be partial or delayed, not a live test."""

from typing import Annotated

from pydantic import ConfigDict, Field, StrictBool, field_validator

from .model_base import BisibilityModel

_Count = Annotated[int, Field(strict=True, ge=0)]
_UrlInput = Annotated[str, Field(strict=True, min_length=1, max_length=2048)]


class SearchIndexSitemapContent(BisibilityModel):
    type: str
    submitted: _Count


class SearchIndexSitemap(BisibilityModel):
    path: str
    type: str | None
    is_sitemaps_index: StrictBool
    is_pending: StrictBool
    errors: _Count
    warnings: _Count
    last_submitted: str | None
    last_downloaded: str | None
    contents: list[SearchIndexSitemapContent]


class SearchIndexSitemaps(BisibilityModel):
    property: str
    sitemaps: list[SearchIndexSitemap]


class SearchIndexSitemapResponse(BisibilityModel):
    property: str
    sitemap: SearchIndexSitemap


class SearchIndexIssueCount(BisibilityModel):
    severity: str | None
    count: _Count


class SearchIndexDetectedItem(BisibilityModel):
    rich_result_type: str | None
    item_count: _Count
    issue_count: _Count
    issues: list[SearchIndexIssueCount]


class SearchIndexRichResults(BisibilityModel):
    verdict: str | None
    detected_items: list[SearchIndexDetectedItem]


class SearchIndexInspection(BisibilityModel):
    verdict: str | None
    coverage_state: str | None
    robots_txt_state: str | None
    indexing_state: str | None
    last_crawl_time: str | None
    last_crawl_at: str | None
    page_fetch_state: str | None
    google_canonical: str | None
    user_canonical: str | None
    crawled_as: str | None
    referring_urls: list[str]
    sitemap: list[str]
    inspection_result_link: str | None
    rich_results_result: SearchIndexRichResults | None


class SearchIndexInspectionError(BisibilityModel):
    code: str
    message: str
    reset_at: str | None = None
    scope: str | None = None

    @field_validator("reset_at", "scope")
    @classmethod
    def present_metadata_is_not_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Rate-limit metadata must be a string when present.")
        return value


class SearchIndexInspectionRow(BisibilityModel):
    url: str
    inspection: SearchIndexInspection | None
    error: SearchIndexInspectionError | None


class SearchIndexInspections(BisibilityModel):
    property: str
    results: list[SearchIndexInspectionRow]


class SearchIndexInspectionInput(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    urls: Annotated[list[_UrlInput], Field(min_length=1, max_length=10)]
