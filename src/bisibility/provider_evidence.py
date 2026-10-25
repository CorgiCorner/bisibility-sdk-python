"""Retained provider evidence, without inferring historical comparisons."""

from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from .model_base import BisibilityModel
from .public_ids import CheckId

ResultCompleteness: TypeAlias = Literal["complete", "partial", "unresolved"] | str
ReturnedDepth = Annotated[int, Field(strict=True, ge=0)]


class ProviderEvidenceRecovery(BisibilityModel):
    state: str | None
    last_attempt_at: str | None
    next_attempt_at: str | None
    reason: str | None


class ProviderEvidenceProjection(BisibilityModel):
    acceptance: str | None
    fulfillment: str | None
    returned_depth: ReturnedDepth | None
    accounting: str | None
    result: str | None
    cost: str | None
    original_checked_at: str | None
    recovery: ProviderEvidenceRecovery | None


class RankCheckRunEvidenceProjection(ProviderEvidenceProjection):
    check_id: CheckId
