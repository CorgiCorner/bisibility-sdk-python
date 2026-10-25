"""Stored Page indexing reports, URL history and inspection budget settings."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StrictBool, field_validator, model_validator

from .model_base import BisibilityModel
from .search_index import SearchIndexRichResults

_Count = Annotated[int, Field(strict=True, ge=0)]
PageIndexingRichResults = SearchIndexRichResults


class _PageIndexingProgress(BisibilityModel):
    checked: _Count
    total: _Count
    complete: StrictBool
    remaining: _Count
    oldest_result_at: str | None
    newest_result_at: str | None
    budget_mode: str
    today_count: _Count
    last429_kind: str | None
    next_reset_at: str


class PageIndexingReason(BisibilityModel):
    coverage_state: str | None
    total: _Count
    oldest_result_at: str | None


class PageIndexingGroup(_PageIndexingProgress):
    group: str
    reasons: list[PageIndexingReason]


class PageIndexingReport(_PageIndexingProgress):
    property: str
    discovery_complete: StrictBool
    discovered_at: str | None
    estimated_days_remaining: _Count | None
    groups: list[PageIndexingGroup]


class PageIndexingTrackedState(BisibilityModel):
    verdict: str | None
    coverage_state: str | None
    google_canonical: str | None
    indexing_state: str | None
    robots_txt_state: str | None
    page_fetch_state: str | None


class PageIndexingChange(BisibilityModel):
    at: str
    previous: PageIndexingTrackedState
    next: PageIndexingTrackedState


class PageIndexingHistory(BisibilityModel):
    complete: StrictBool
    changes: list[PageIndexingChange]


class PageIndexingUrl(BisibilityModel):
    url: str
    verdict: str | None
    coverage_state: str | None
    last_crawl_at: str | None
    canonical_ok: StrictBool | None
    checked_at: str | None
    created_at: str
    updated_at: str
    source: str
    sitemap_url: str | None
    google_canonical: str | None
    user_canonical: str | None
    indexing_state: str | None
    robots_txt_state: str | None
    page_fetch_state: str | None
    crawled_as: str | None
    referring_urls: list[str]
    sitemaps: list[str]
    rich_results_summary: PageIndexingRichResults | None
    inspection_result_link: str | None
    inspection_error: str | None
    inspection_failed_at: str | None
    group: str
    history: PageIndexingHistory | None = None

    @field_validator("history")
    @classmethod
    def present_history_is_not_null(cls, value: PageIndexingHistory | None) -> PageIndexingHistory:
        if value is None:
            raise ValueError("History must be an object when present.")
        return value


class PageIndexingUrlsMeta(BisibilityModel):
    next_cursor: str | None


class PageIndexingUrls(BisibilityModel):
    data: list[PageIndexingUrl]
    meta: PageIndexingUrlsMeta


class ListPageIndexingUrlsOptions(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    group: Literal["indexed", "not_indexed", "inspection_failed", "not_checked"] | None = None
    coverage_state: str | None = Field(default=None, strict=True, max_length=500)
    sitemap: str | None = Field(default=None, strict=True, max_length=2048)
    source: Literal["keyword_target", "sitemap", "manual"] | None = None
    search: str | None = Field(default=None, strict=True, max_length=500)
    changed_since: str | datetime | None = None
    cursor: str | None = Field(default=None, strict=True, max_length=2048)
    limit: int | None = Field(default=None, strict=True, ge=1, le=100)
    history: Literal["true", "false"] | None = None

    @field_validator("changed_since", mode="before")
    @classmethod
    def valid_changed_since(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime):
            raise ValueError("changed_since must be a datetime or ISO 8601 string.")
        if value.utcoffset() is None:
            raise ValueError("changed_since must include a timezone offset.")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class PageIndexingSettings(BisibilityModel):
    property: str
    budget_mode: str
    today_count: _Count
    last429_kind: str | None
    next_reset_at: str
    inspection_daily_limit: Annotated[int, Field(strict=True, ge=0, le=2000)]
    available_modes: list[str]
    last429_at: str | None


class PageIndexingSettingsPatch(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    budget_mode: Literal["off", "fixed", "available_quota"] | None = None
    inspection_daily_limit: int | None = Field(default=None, strict=True, ge=0, le=2000)

    @model_validator(mode="after")
    def nonempty_settings(self) -> PageIndexingSettingsPatch:
        if not self.model_fields_set:
            raise ValueError("Supply at least one setting.")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Settings cannot be null.")
        return self
