"""Public AI tracking contracts. Cost amounts retain decimal USD strings and unknowns."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, SerializerFunctionWrapHandler, model_serializer

from .ai_tracking_suggestions import (
    AITrackingAcceptedDraft,
    AITrackingGenerationReference,
    AITrackingProviderDatasetReference,
    AITrackingSuggestionReviewSnapshot,
)
from .models import BisibilityModel

TopicId = Annotated[str, Field(pattern=r"^ait_[a-z][a-z0-9]{23}$")]
PromptId = Annotated[str, Field(pattern=r"^aip_[a-z][a-z0-9]{23}$")]
ScheduleId = Annotated[str, Field(pattern=r"^ais_[a-z][a-z0-9]{23}$")]
RunId = Annotated[str, Field(pattern=r"^air_[a-z][a-z0-9]{23}$")]
SampleId = Annotated[str, Field(pattern=r"^asm_[a-z][a-z0-9]{23}$")]
ConnectionId = Annotated[str, Field(pattern=r"^conn_[a-z][a-z0-9]{23}$")]
RunState = Literal[
    "planned", "running", "completed", "partial", "blocked", "failed", "cancelled", "skipped"
]


class AITrackingSourceConfiguration(BisibilityModel):
    provider: Literal["dataforseo"]
    endpoint: str = Field(min_length=1, max_length=256)
    engine: Literal["chat_gpt", "gemini", "claude", "perplexity", "google"]
    source: Literal["consumer_scrape", "model_api", "google_aio"]
    model: str | None
    parameters: dict[str, Any]

    @model_serializer(mode="wrap")
    def _serialize_keep_nullable_model(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, Any]:
        """Preserve ``model: null`` so a null provider model survives serialization.

        The API's source configuration schema lists ``model`` as a required
        nullable field. The SDK's shared body dumper runs with
        ``exclude_none=True``; without this hook, ``model=None`` would be
        stripped and the request would fail backend validation. The field is
        required at validation time, so it is always known here and we re-emit
        it when the generic serializer drops it.
        """
        data: dict[str, Any] = handler(self)
        if "model" not in data:
            data["model"] = self.model
        return data


class AITrackingTopicInput(BisibilityModel):
    paused: bool | None = None
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)


class AITrackingTopicPatch(BisibilityModel):
    paused: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)


class AITrackingTopic(AITrackingTopicInput):
    paused_at: str | None
    id: TopicId
    archived_at: str | None
    created_at: str
    updated_at: str


class AITrackingPromptInput(BisibilityModel):
    generation_reference: AITrackingGenerationReference | None = None
    provider_dataset_reference: AITrackingProviderDatasetReference | None = None
    text: str = Field(min_length=1, max_length=64000)
    topic_id: TopicId | None = None
    label: str | None = Field(default=None, max_length=200)
    category: Literal["neutral", "comparative", "branded"] | None = None
    paused: bool | None = None


class AITrackingPromptPatch(BisibilityModel):
    generation_reference: AITrackingGenerationReference | None = None
    provider_dataset_reference: AITrackingProviderDatasetReference | None = None
    text: str | None = Field(default=None, min_length=1, max_length=64000)
    topic_id: TopicId | None = None
    label: str | None = Field(default=None, max_length=200)
    category: Literal["neutral", "comparative", "branded"] | None = None
    paused: bool | None = None


class AITrackingPromptRevision(BisibilityModel):
    generation_reference: AITrackingGenerationReference | None = None
    provider_dataset_reference: AITrackingProviderDatasetReference | None = None
    id: Annotated[str, Field(pattern=r"^apr_[a-z][a-z0-9]{23}$")]
    ordinal: int
    category: Literal["neutral", "comparative", "branded"]
    text: str
    text_hash: str
    created_at: str


class AITrackingPrompt(BisibilityModel):
    revisions: list[AITrackingPromptRevision]
    paused_at: str | None
    id: PromptId
    topic_id: TopicId | None
    label: str | None
    archived_at: str | None
    created_at: str
    updated_at: str


class AITrackingPreviewInput(BisibilityModel):
    prompt_ids: list[PromptId] = Field(min_length=1, max_length=100)
    configurations: list[AITrackingSourceConfiguration] = Field(min_length=1, max_length=20)
    credential_connection_id: ConnectionId | None = None


class AITrackingPreview(BisibilityModel):
    configurations: list[AITrackingSourceConfiguration]
    credential_connection_id: ConnectionId
    credential_version: str
    budget_revision: str
    consent_revision: str
    estimated_cost_cents: float


class AITrackingRunInput(AITrackingPreviewInput):
    credential_connection_id: ConnectionId
    credential_version: str
    budget_revision: str
    consent_revision: str
    deadline: str
    origin: Literal["manual", "scheduled"] | None = None
    entry_source: Literal["app", "api", "mcp", "worker"] | None = None
    consent: Literal[True]
    schedule_id: ScheduleId | None = None
    planned_at: str | None = None


class AITrackingScheduleInput(BisibilityModel):
    name: str = Field(min_length=1, max_length=200)
    cron: str = Field(min_length=1, max_length=200)
    timezone: str = Field(min_length=1, max_length=100)
    enabled: bool = False
    configuration: AITrackingRunInput
    next_run_at: str | None = None
    # The API reads consent from the top level of the schedule payload when a
    # reviewed configuration must be re-approved on create or update, so expose
    # it here instead of only inside ``configuration``.
    consent: Literal[True] | None = None


class AITrackingSchedulePatch(BisibilityModel):
    """Partial update for an AI tracking schedule.

    Mirrors the API's ``scheduleInputSchema.partial()`` so none of the create
    fields are required. ``consent`` lives at the top level because the API
    reads it from the raw payload (not from ``configuration``) whenever a new
    reviewed configuration must be approved while updating the schedule.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    cron: str | None = Field(default=None, min_length=1, max_length=200)
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None
    configuration: AITrackingRunInput | None = None
    next_run_at: str | None = None
    consent: Literal[True] | None = None


class AITrackingScheduleConfiguration(BisibilityModel):
    prompt_ids: list[PromptId]
    configurations: list[AITrackingSourceConfiguration]


class AITrackingSchedule(BisibilityModel):
    name: str
    cron: str
    timezone: str
    enabled: bool
    next_run_at: str | None
    configuration: AITrackingScheduleConfiguration
    id: ScheduleId
    archived_at: str | None
    created_at: str
    updated_at: str


class AITrackingRun(BisibilityModel):
    id: RunId
    state: RunState
    created_at: str
    updated_at: str
    finished_at: str | None
    planned_at: str | None
    sample_count: int | None


class AITrackingEvidence(BisibilityModel):
    answer_text: str | None
    raw: Any
    answer_truncated: bool
    raw_truncated: bool
    search_results: list[dict[str, Any]]
    requested_locale: str | None
    effective_locale: str | None
    locale_mechanism: str | None
    requested_model: str | None
    actual_model: str | None
    provider_status: str | None
    observed_at: str | None
    fetched_at: str
    recorded_source: Literal["fresh", "cache"]


class AITrackingSample(BisibilityModel):
    id: SampleId
    measurement: Literal[
        "answer_present", "aio_not_present", "partial", "unavailable", "failed", "unknown"
    ]
    source: Literal["consumer_scrape", "model_api", "google_aio"]
    engine: Literal["chat_gpt", "gemini", "claude", "perplexity", "google"]
    prompt: str
    prompt_revision_id: Annotated[str, Field(pattern=r"^apr_[a-z][a-z0-9]{23}$")]
    evidence: AITrackingEvidence | None
    citations: list[dict[str, Any]]
    cost_usd: str | None
    cost_state: Literal["unknown", "pending", "confirmed", "refund_pending", "derived"]


class AITrackingExportScope(BisibilityModel):
    complete: bool
    max_pages: int
    loaded: int
    resumed: bool


class AITrackingExport(BisibilityModel):
    items: list[AITrackingSample]
    run_id: RunId
    next_cursor: str | None
    scope: AITrackingExportScope | None = None


class AITrackingEvidenceOptions(BisibilityModel):
    format: Literal["json", "csv"] | None = None
    run_id: RunId
    limit: int | None = Field(default=None, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=512)


class AITrackingTrendOptions(AITrackingEvidenceOptions):
    previous_run_id: RunId | None = None


class AITrackingDenominator(BisibilityModel):
    expected: int
    observed: int
    eligible: int
    mentioned: int
    absent_aio: int
    partial: int
    failed: int
    unknown: int
    missing: int
    coverage: float
    mention_rate: float | None


class AITrackingTrendStratum(BisibilityModel):
    """One per-category trend bucket inside :class:`AITrackingTrends`.

    The API ships this closed shape with every category it tracks so clients
    can read branded, comparative, neutral, and unknown trends side by side.
    """

    category: Literal["neutral", "comparative", "branded", "unknown"]
    current: AITrackingDenominator
    previous: AITrackingDenominator
    comparable: bool
    reason: str | None
    delta: float | None


class AITrackingTrends(BisibilityModel):
    comparable: bool
    reason: str | None
    current_run_id: RunId
    previous_run_id: RunId | None = None
    previous: AITrackingDenominator | None = None
    current: AITrackingDenominator
    delta: float | None
    next_cursor: str | None
    previous_next_cursor: str | None = None
    # ``baseline`` is always ``"neutral"`` today but ships on every trends
    # response so clients know which category anchors the shared cohort.
    baseline: Literal["neutral"] = "neutral"
    # ``category`` and ``strata`` only arrive on comparative responses that
    # include a previous run; keep them optional so single-run neutral
    # baselines remain parseable without inventing fields.
    category: Literal["neutral"] | None = None
    strata: list[AITrackingTrendStratum] | None = None


class AITrackingSuggestion(BisibilityModel):
    generation_reference: AITrackingGenerationReference | None = None
    provider_dataset_reference: AITrackingProviderDatasetReference | None = None
    text: str = Field(min_length=3, max_length=4000)
    category: Literal["neutral", "comparative", "branded"]
    provenance: Literal["generated_hypothesis", "provider_dataset", "model_generated_hypothesis"]
    evidence_ids: list[str] = Field(max_length=30)
    popularity: float | None
    accepted: Literal[False]


class AITrackingSuggestions(BisibilityModel):
    input_snapshot: AITrackingSuggestionReviewSnapshot | None = None
    drafts: list[AITrackingSuggestion]
    method: Literal["context_template_heuristic", "manual_fallback"]
    context_updated_at: str | None
    requires_acceptance: bool
    cost_usd: str
    limitations: list[str]


class AITrackingAcceptanceInput(BisibilityModel):
    drafts: list[AITrackingAcceptedDraft] = Field(min_length=1, max_length=20)


class AITrackingAcceptance(BisibilityModel):
    prompts: list[AITrackingPrompt]
