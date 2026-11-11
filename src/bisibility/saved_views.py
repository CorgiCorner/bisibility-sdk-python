"""Normalized saved-view definitions, with additive response compatibility."""

from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import Field, StrictBool

from .model_base import BisibilityModel


class KeywordSavedViewFilters(BisibilityModel):
    ai_overview_shown: StrictBool = False
    change: Literal["any", "up", "down", "new", "lost"]
    contains: str
    intents: list[str]
    last_check: Literal["any", "completed", "failed", "not_checked", "running"]
    position: list[Literal["top3", "top10", "11-50", "51-100"]]
    serp: list[Literal["featured", "paa", "sitelinks", "image", "video", "ai"]]
    tags: list[str]
    topics: list[str]
    url_changed: StrictBool
    vol_max: float
    vol_min: float
    wrong_url: StrictBool


class SavedViewLens(BisibilityModel):
    device: Literal["all", "desktop", "mobile"]
    location_id: str | None


class SavedViewSort(BisibilityModel):
    direction: Literal["asc", "desc"]
    field: str


class SavedViewPresentation(BisibilityModel):
    column_order: list[str]
    registry_version: int
    sizing: dict[str, float]
    version: Literal[1]
    visibility: dict[str, bool]


class SavedViewSubjectScope(BisibilityModel):
    id: str
    kind: Literal["keyword", "market"]


class SavedViewReportSubject(BisibilityModel):
    assignment_revision: int
    identity_revision_id: str
    location_id: str
    scope: SavedViewSubjectScope


SavedViewReportView: TypeAlias = Literal["general", "local", "ai_overviews"]


class SavedViewReportScope(BisibilityModel):
    as_of: str | None
    comparison_days: Literal[7, 28, 90]
    subject: SavedViewReportSubject | None
    view: SavedViewReportView


class KeywordSavedViewDefinitionV1(BisibilityModel):
    filters: KeywordSavedViewFilters
    lens: SavedViewLens
    search: str
    surface: Literal["keywords"]
    version: Literal[1]


class KeywordSavedViewDefinitionV2(BisibilityModel):
    filters: KeywordSavedViewFilters
    lens: SavedViewLens
    search: str
    surface: Literal["keywords"]
    version: Literal[2]
    grouped: StrictBool
    page_size: Literal[25, 50, 100]
    presentation: SavedViewPresentation
    report_scope: SavedViewReportScope
    sort: SavedViewSort


class CompetitorSavedViewFilters(BisibilityModel):
    excluded_keyword_ids: list[str] = Field(default_factory=list)
    position: Literal["all", "top3", "top10"]
    tag: str | None


class CompetitorSavedViewScope(BisibilityModel):
    device: Literal["desktop", "mobile"]
    engine: Literal["google"]
    location_id: str


class CompetitorSavedViewDefinitionV1(BisibilityModel):
    filters: CompetitorSavedViewFilters
    scope: CompetitorSavedViewScope
    surface: Literal["competitors"]
    version: Literal[1]


class CompetitorSavedViewDefinitionV2(BisibilityModel):
    filters: CompetitorSavedViewFilters
    scope: CompetitorSavedViewScope
    surface: Literal["competitors"]
    version: Literal[2]
    grouped: StrictBool
    page_size: Literal[25, 50, 100]
    presentation: SavedViewPresentation
    sort: SavedViewSort


SavedViewDefinition: TypeAlias = (
    KeywordSavedViewDefinitionV1
    | KeywordSavedViewDefinitionV2
    | CompetitorSavedViewDefinitionV1
    | CompetitorSavedViewDefinitionV2
)
