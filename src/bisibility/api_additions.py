"""Domain proof, retained crawl, account device, and search totals contracts."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import ConfigDict, Field

from .model_base import BisibilityModel
from .models import SiteAuditPage
from .public_ids import DevicePushTokenId

DomainVerificationMethod: TypeAlias = Literal["dns_txt", "search_console"]
DevicePushEnvironment: TypeAlias = Literal["production", "sandbox"]


class DomainVerificationInput(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    method: DomainVerificationMethod


class DomainVerification(BisibilityModel):
    domain: str
    method: str
    dns_host: str
    dns_value: str
    verified_at: str | None
    last_checked_at: str | None
    last_check_result: str | None
    failures: int
    revoked_at: str | None


class DomainVerificationResponse(BisibilityModel):
    data: DomainVerification | None


class SiteAuditRunProgress(BisibilityModel):
    state: str
    stop_reason: str | None
    pages_crawled: int
    budget_pages: int
    requests: int
    started_at: str | None
    completed_at: str | None


class SiteAuditPageList(BisibilityModel):
    pages: list[SiteAuditPage]
    offset: int
    next_offset: int | None


class ListSiteAuditPagesOptions(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    offset: int | None = Field(default=None, strict=True, ge=0, le=100000)
    limit: int | None = Field(default=None, strict=True, ge=1, le=100)


class DeleteMeInput(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    confirm_email: str = Field(min_length=3, max_length=320)


class MeDeleted(BisibilityModel):
    deleted: Literal[True]


class RegisterDevicePushTokenInput(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(pattern=r"^[0-9A-Fa-f]{32,200}$")
    environment: DevicePushEnvironment
    bundle_id: str = Field(
        min_length=1, max_length=155, pattern=r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$"
    )


class DevicePushToken(BisibilityModel):
    id: DevicePushTokenId
    bundle_id: str
    environment: str
    created_at: str
    last_seen_at: str
    token_suffix: str


class SearchPerformanceTotalsOptions(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    start_date: Annotated[str, Field(pattern=r"^[1-9]\d{3}-\d{2}-\d{2}$")]
    end_date: Annotated[str, Field(pattern=r"^[1-9]\d{3}-\d{2}-\d{2}$")]
    compare_previous: Literal["true", "false"] | None = None


class SearchPerformanceFreshness(BisibilityModel):
    data_state: str
    fetched_at: str
    finalized_through: str | None
    first_incomplete_date: str | None


class SearchPerformancePeriod(BisibilityModel):
    start_date: str
    end_date: str
    data_start_date: str | None
    data_end_date: str | None
    clicks: int
    impressions: int
    ctr: float
    position: float
    freshness: SearchPerformanceFreshness


class SearchPerformanceTotalsResponse(BisibilityModel):
    current: SearchPerformancePeriod
    previous: SearchPerformancePeriod | None
    property: str
    search_type: str
    source: str
