"""Account analytics permission, independent of browser replay."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StrictBool, StrictInt

from .model_base import BisibilityModel


class AccountAnalyticsConsent(BisibilityModel):
    analytics: StrictBool
    decided_at: datetime | None
    source: Literal["web", "ios", "api"] | None
    version: Annotated[StrictInt, Field(ge=1)]


class UpdateAnalyticsConsentInput(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    analytics: StrictBool
