"""Frozen model generation previews and trusted prompt provenance."""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from .models import BisibilityModel

ConnectionId = Annotated[str, Field(pattern=r"^conn_[a-z][a-z0-9]{23}$")]
GenerationId = Annotated[str, Field(pattern=r"^asg_[a-z][a-z0-9]{23}$")]
DraftId = Annotated[
    str,
    Field(pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"),
]


class PromptResearchGenerationReference(BisibilityModel):
    generation_id: GenerationId
    draft_id: DraftId


class PromptResearchProviderDatasetReference(BisibilityModel):
    report_id: Annotated[str, Field(pattern=r"^agr_[a-z][a-z0-9]{23}$")]
    row_index: int = Field(ge=0)


class PromptResearchSuggestionConfiguration(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["dataforseo"]
    engine: Literal["chat_gpt"]
    model: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,119}$")
    language_code: str = Field(min_length=2, max_length=20)
    country_iso_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    max_output_tokens: int = Field(ge=16, le=4096)
    advisory_cost_limit_cents: float = Field(gt=0, le=1000000, allow_inf_nan=False)


class PromptResearchReviewedContext(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    business: str
    audience: str
    products: str
    goals: str
    agent_rules: str


class PromptResearchReviewedCompetitor(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    id: Annotated[str, Field(pattern=r"^cmp_[a-z][a-z0-9]{23}$")]
    label: str | None
    domain: str = Field(min_length=1, max_length=253)


class PromptResearchSuggestionReviewSnapshot(BisibilityModel):
    context: PromptResearchReviewedContext
    competitors: list[PromptResearchReviewedCompetitor]


class PromptResearchSuggestionSnapshot(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    context: PromptResearchReviewedContext
    competitors: list[PromptResearchReviewedCompetitor] = Field(max_length=20)

    @model_validator(mode="after")
    def validate_reviewed_snapshot(self) -> PromptResearchSuggestionSnapshot:
        snapshot = self.model_dump(mode="json")
        snapshot["context"]["agentRules"] = snapshot["context"].pop("agent_rules")
        length = len(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
        if length > 5000:
            raise ValueError("Reviewed input snapshot exceeds 5000 serialized characters.")
        if len({row.id for row in self.competitors}) != len(self.competitors):
            raise ValueError("Reviewed competitors must have unique public IDs.")
        return self


class PromptResearchSuggestionsPreviewInput(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    configuration: PromptResearchSuggestionConfiguration
    input_snapshot: PromptResearchSuggestionSnapshot
    credential_connection_id: ConnectionId | None = None


class PromptResearchSuggestionsPreview(PromptResearchSuggestionsPreviewInput):
    version: Literal[1]
    snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    estimated_cost_cents: float = Field(gt=0, allow_inf_nan=False)
    estimate_kind: Literal["forecast"]
    is_guaranteed_maximum: Literal[False]
    credential_connection_id: ConnectionId
    credential_version: str = Field(min_length=1)
    budget_revision: str = Field(min_length=1)
    consent_revision: str = Field(min_length=1)
    expires_at: str
    limitations: list[str] = Field(max_length=20)


class PromptResearchSuggestionsGenerateInput(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    preview: PromptResearchSuggestionsPreview
    consent: Literal[True]


class PromptResearchModelSuggestion(BisibilityModel):
    draft_id: DraftId
    text: str
    category: Literal["neutral", "comparative", "branded"]
    provenance: Literal["model_generated_hypothesis"]
    evidence_ids: list[str] = Field(max_length=0)
    popularity: None
    accepted: Literal[False]


class PromptResearchSuggestionsGeneration(BisibilityModel):
    generation_id: GenerationId
    drafts: list[PromptResearchModelSuggestion]
    cost_usd: str | None
    cost_state: Literal["unknown", "confirmed"]
    method: Literal["model_generated_hypothesis"]
    limitations: list[str]


class PromptResearchAcceptedDraft(BisibilityModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=3, max_length=4000)
    category: Literal["neutral", "comparative", "branded"]
    generation_reference: PromptResearchGenerationReference | None = None
    provider_dataset_reference: PromptResearchProviderDatasetReference | None = None
    provenance: (
        Literal["generated_hypothesis", "provider_dataset", "model_generated_hypothesis"] | None
    ) = None
    evidence_ids: list[str] | None = Field(default=None, max_length=30)
    popularity: None = None
    accepted: Literal[False] | None = None

    @model_validator(mode="after")
    def require_trusted_provenance(self) -> PromptResearchAcceptedDraft:
        if self.generation_reference and self.provider_dataset_reference:
            raise ValueError("Choose one trusted provenance reference.")
        if self.provenance == "model_generated_hypothesis" and not self.generation_reference:
            raise ValueError("Model drafts require a trusted generation reference.")
        if self.provenance == "provider_dataset" and not self.provider_dataset_reference:
            raise ValueError("Provider datasets require a trusted report reference.")
        if (
            self.evidence_ids
            and not self.generation_reference
            and not self.provider_dataset_reference
        ):
            raise ValueError("Evidence claims require a trusted provenance reference.")
        return self
