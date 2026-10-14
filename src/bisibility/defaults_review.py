"""Typed issuer-bound review data. Preview never writes project defaults."""

from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field, StrictBool, StrictInt, field_validator

from .model_base import BisibilityModel
from .public_ids import ProjectId


class ProjectDefaultsReview(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    expected_source_hash: str = Field(pattern=r"^[a-f0-9]{64}$", strict=True)
    expected_revision: str = Field(pattern=r"^(0|[1-9][0-9]*)$", strict=True)
    preview_token: str = Field(min_length=1, max_length=8192, strict=True)
    idempotency_key: str = Field(min_length=8, max_length=128, strict=True)
    confirmed: Literal[True]

    @field_validator("confirmed", mode="before")
    @classmethod
    def explicit_consent(cls, value: Any) -> Any:
        if value is not True:
            raise ValueError("Defaults review requires explicit confirmation")
        return value


class ProjectDefaultsPreviewRequest(BisibilityModel):
    kind: Literal["patch"]
    values: dict[str, Any]


class ProjectDefaultsPreviewDraft(BisibilityModel):
    project_id: ProjectId
    city: str | None
    country: str
    device: str
    location_key: str
    frequency: str
    cron_expression: str | None
    jitter_minutes: StrictInt
    serp_depth: StrictInt
    serp_stop_on_match: StrictBool
    timezone: str


class ProjectDefaultsPreviewResolved(BisibilityModel):
    location_key: str
    label: str
    language_code: str
    device: str


class ProjectDefaultsPreviewImpact(BisibilityModel):
    existing_target_retargets: StrictInt
    new_targets: StrictInt
    inherited_depth_targets: StrictInt
    recurring_estimate: str
    scope_changed: StrictBool
    cadence_changed: StrictBool


class ProjectDefaultsPreview(BisibilityModel):
    request: ProjectDefaultsPreviewRequest
    draft: ProjectDefaultsPreviewDraft
    expected_source_hash: str = Field(pattern=r"^[a-f0-9]{64}$", strict=True)
    expected_revision: str = Field(pattern=r"^(0|[1-9][0-9]*)$", strict=True)
    preview_token: str = Field(min_length=1, max_length=8192, strict=True)
    expires_at: str

    @field_validator("expires_at")
    @classmethod
    def valid_expiry(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    resolved: ProjectDefaultsPreviewResolved
    impact: ProjectDefaultsPreviewImpact
    policy_ready: StrictBool


def assert_defaults_support(capabilities: Any) -> None:
    features = getattr(capabilities, "features", None)
    if not isinstance(features, dict) or features.get("reviewed_project_defaults") != "v1":
        from .errors import BisibilityConfigurationError

        raise BisibilityConfigurationError(
            "This server does not advertise reviewed project defaults v1; no PATCH was sent."
        )


def validate_preview_scope(
    preview: ProjectDefaultsPreview, project_id: str
) -> ProjectDefaultsPreview:
    if (
        preview.request.values.get("project_id") != project_id
        or preview.draft.project_id != project_id
    ):
        raise ValueError("Defaults preview does not match the requested project")
    return preview
