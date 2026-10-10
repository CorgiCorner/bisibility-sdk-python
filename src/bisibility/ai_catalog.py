"""Free AI research capability catalog."""

from typing import Literal

from .models import BisibilityModel


class AINamedChoice(BisibilityModel):
    code: str
    name: str


class AIModelCapability(BisibilityModel):
    id: str
    provider: Literal["chat_gpt"]
    label: str
    reasoning: bool
    web_search: bool
    min_output_tokens: int
    max_output_tokens: int
    price_available: bool
    admission_enabled: bool
    actual_cost_enabled: bool


class AIVisibilityMarket(BisibilityModel):
    platform: Literal["chat_gpt", "google"]
    location_code: int
    country_name: str
    languages: list[AINamedChoice]


class AICatalogLimits(BisibilityModel):
    max_models: Literal[2]
    max_output_tokens: Literal[4096]


class AIResearchCatalog(BisibilityModel):
    models: list[AIModelCapability]
    visibility_markets: list[AIVisibilityMarket]
    response_countries: list[AINamedChoice]
    response_languages: list[AINamedChoice]
    limits: AICatalogLimits
    fetched_at: str
    actual_cost_available: bool | None = None
