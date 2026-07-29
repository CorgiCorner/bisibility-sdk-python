# bisibility

> Part of [bisibility](https://github.com/CorgiCorner/bisibility) - open-source keyword
> rank tracking you can self-host and automate. This repository contains the Python SDK
> for the Bisibility REST API.
>
> [Docs](https://bisibility.com/docs) ·
> [API reference](https://bisibility.com/docs/api/overview) ·
> [Roadmap](https://bisibility.com/roadmap)
>
> **Status:** Published on PyPI as v0.4.0.

Python SDK for the Bisibility REST API.

## Install

```sh
pip install bisibility
```

For local development:

```sh
pip install -e .[dev]
```

## Quickstart

```python
import os

from bisibility import BisibilityClient

bisibility = BisibilityClient(api_key=os.environ["BISIBILITY_API_KEY"])

projects = bisibility.list_projects()
project_id = projects.data[0].id if projects.data else None

if project_id:
    created = bisibility.create_keywords(
        project_id,
        {
            "keywords": [
                {
                    "keyword": "rank tracker api",
                    "target_url": "https://example.com/rank-tracker",
                    "tags": ["api"],
                }
            ]
        },
    )

    keyword_id = created.results[0].keyword.id if created.results else None
    if keyword_id:
        check = bisibility.run_rank_check(keyword_id)
        print(check.position, check.ranking_url)
```

## Configuration

```python
import os

from bisibility import BisibilityClient

bisibility = BisibilityClient(
    api_key=os.environ["BISIBILITY_API_KEY"],
    base_url="https://bisibility.com/api/v1",
    project_id=os.environ.get("BISIBILITY_PROJECT_ID"),
    timeout=30.0,
)
```

`base_url` should point at the API v1 root. Protected methods send
`Authorization: Bearer <api_key>`. Write methods accept `RequestOptions` with an
`idempotency_key`, which maps to the server `Idempotency-Key` header.

The client accepts project API keys (`bsb_key_live_...` or `bsb_key_test_...`) and
personal access tokens (`bsb_pat_live_...`). For a PAT with multiple project memberships,
set `project_id` to a project ID returned by `list_projects`; the client sends it
as `X-Bisibility-Project` on project-implicit routes. PAT methods include
`get_me`, `create_project`, personal-token self-management, project API-key
minting, and webhook CRUD.

Legacy `bsk_...` and `bsp_...` credentials are not accepted by the v3 contract.

### Public IDs and cursors v3

Every resource identifier at the HTTP boundary is a strict lowercase public ID:
`<prefix>_[a-z][a-z0-9]{23}`. The SDK rejects raw database IDs, legacy IDs,
wrong prefixes, uppercase characters, and malformed suffixes before sending a
request. The same validation is applied to typed request bodies, project header,
and ID-bearing API responses. A malformed success response raises
`BisibilityResponseError`.

The registry is fixed to: `al`, `alr`, `audit`, `check`, `cmp`, `conn`, `dwh`,
`ferry`, `imp`, `inv`, `key`, `kw`, `mbr`, `ntf`, `pat`, `prj`, `sid`, `sig`,
`svkw`, `tag`, `usr`, `viw`, and `we`. Import
`PUBLIC_ID_PREFIXES` or `public_id_pattern()` when another component needs the
same contract.

List operations accept and return opaque v3 cursors. Pass `meta.next_cursor`
back unchanged; the SDK rejects legacy, unversioned, and malformed cursors
before a request is sent or a success response is returned.

Cloud transfer uses package version 5 only. Its project, cloud-import, and
transfer-token identifiers follow the same public-ID rules.

The examples below reuse `project_id` and `keyword_id` values returned by the
API, as shown in the quickstart, instead of embedding synthetic resource IDs.

The default timeout is 30 seconds per attempt. Pass `timeout=None` to the client
to opt out globally, or `RequestOptions(timeout=None)` for one request. The SDK
sends `User-Agent: bisibility-sdk-python/<version>` unless you supplied a user
agent, and always sends the matching `X-Bisibility-Client` header.

### Retries

Failed requests are retried automatically up to `max_retries` times (default 2)
when the failure is an `httpx` transport error or a `429`/`503` response. Only
requests that are safe to replay are retried: idempotent
`GET`/`HEAD`/`PUT`/`DELETE` requests are always eligible, while non-idempotent
`POST`/`PATCH` requests are retried only when an `Idempotency-Key` header is present (set via
`RequestOptions(idempotency_key=...)`). When
the server sends a `Retry-After` header in seconds or HTTP-date form, the client
waits that long (capped at 60 seconds); otherwise it uses capped exponential
backoff (0.5s, 1s, 2s, ... up to 8s). Set `max_retries=0` to disable retries.

```python
bisibility = BisibilityClient(api_key="bsb_key_live_...", max_retries=3)
```

```python
from bisibility import RequestOptions

bisibility.create_api_key(
    {"name": "CI"},
    request_options=RequestOptions(idempotency_key="request-123"),
)
```

## Methods

- Discovery: `get_health`, `get_open_api`, `get_capabilities`, `get_llms_text`
- Public cost (no auth): `get_provider_rates`, `get_cost_estimate`
- Projects: `list_projects`, `get_project`, `update_project`, `delete_project`,
  `update_project_defaults`
- API keys: `list_api_keys`, `create_api_key`, `revoke_api_key`
- Keywords: `list_keywords`, `create_keywords`, `add_keywords`, `get_keyword`,
  `update_keyword`, `set_keyword_target_url`, `delete_keyword`, `bulk_update_keywords`
- Keyword research: `research_keywords` for one seed and `get_keyword_metrics` for
  batches of up to 700 keywords. Both require API write scope because a cache miss can
  spend provider budget. Pass `estimate_only=True` for a free cache-aware dry run and
  `max_cost_cents` for a best-effort request guard. Research source diagnostics report
  `ok`, `failed`, or `skipped`, including a machine-readable reason when applicable.
  Both methods expose nullable provider metrics, cache metadata, and paid BYO-key cost.
- Rank checks: `list_rank_checks`, `run_rank_check`, `get_rank_check_result`
- Signals: `create_signal`, `list_project_signals`
- Alert rules: `list_alert_rules`, `create_alert_rule`, `update_alert_rule`,
  `delete_alert_rule`, `list_triggered_alerts`, `mute_triggered_alert`,
  `mark_project_alerts_read`
- Rank-history export: `export_rank_history` for typed cursor-paginated JSON or raw CSV text
- Sitemap monitors: `list_sitemap_monitors`, `update_sitemap_monitor`
- Team: `list_team_members`, `list_team_invites`, `create_team_invite`,
  `revoke_project_team_invite`, `revoke_team_invite`
- Providers: `list_providers`, `connect_provider`, `test_provider_connection`,
  `update_provider_settings`, `set_provider_enabled`, `set_provider_priority`,
  `set_primary_provider`, `disconnect_provider`
- Saved views: `list_saved_views`, `create_saved_view`, `delete_project_saved_view`,
  `delete_saved_view`
- Competitors: `list_competitors`, `add_competitor`, `remove_project_competitor`,
  `remove_competitor`
- Notification preferences: `get_notification_preferences`, `update_notification_preferences`
- Migration tokens: `list_migration_tokens`, `mint_migration_token`,
  `revoke_project_migration_token`, `revoke_migration_token`
- Cloud import: `get_cloud_import_compatibility`, `import_cloud_export`,
  `create_cloud_import_session`, `upload_cloud_import_chunk`,
  `finalize_cloud_import_session`

### Cloud import v5

Cloud import accepts only version 5 packages. Every package must use strict
snake_case top-level keys and include all five section arrays, even when they
are empty. Package, session, chunk, and response identifiers are validated as
typed public IDs before a request is sent.

```python
from bisibility import CloudImportPackage, CloudImportSessionCreate

package = CloudImportPackage(
    version=5,
    project_id=project_id,
    keywords=[],
    alert_rules=[],
    competitors=[],
    notification_preferences=[],
    saved_views=[],
)

session = CloudImportSessionCreate(
    version=5,
    chunk_count=1,
    source_project_id=project_id,
)
```

The nested `CloudImportKeyword`, `CloudImportCompetitor`, `CloudImportAlertRule`,
`CloudImportNotificationPreference`, and `CloudImportSavedView` models mirror
the API schema. Alert targets are a discriminated union with `type="keyword"`
or `type="tag"`; arbitrary fields and legacy aliases are rejected.

List methods return `ListResponse[T]` with `data` and `meta.next_cursor`. Resource
methods return pydantic models matching the Bisibility API response shape.

Keyword research uses a single seed and a result limit of 100, 300, or 500. Metrics
requests accept at most 700 keywords per call, matching the REST contract. Split larger
batches explicitly so each response retains its own cache counts and provider cost.

Cursor-paginated resources also expose lazy `iter_*` generators. They preserve
the supplied filters, request pages only as needed, and stop when
`meta.next_cursor` is `None`:

```python
from bisibility import ListKeywordsOptions

for keyword in bisibility.iter_keywords(
    project_id,
    ListKeywordsOptions(tag="Product", limit=100),
):
    print(keyword.text)
```

Iterators are available for keywords, rank checks, signals, API keys (including
project API keys), webhooks, alert rules, triggered alerts, team members, team
invites, providers, saved views, competitors, and migration tokens.

### Webhook secret rotation

To rotate a webhook secret, set `hmac_secret` on `WebhookUpdateInput` to a
non-empty string. Sending a null, empty, or whitespace-only secret is rejected.
Omit `hmac_secret` entirely to leave the existing secret unchanged; omitted
fields are not included in the PATCH request.

All SDK-defined exceptions derive from `BisibilityError`. `BisibilityApiError`
also exposes `is_rate_limit`, `is_not_found`, and `retry_after_seconds` helpers.
Problem responses follow RFC 9457 and preserve extension members; sensitive
response headers are removed before an API error is exposed.

There is intentionally no `create_project` method: the API returns
`403 Forbidden` for `POST /projects` because project-scoped API keys cannot
create projects. Create projects from the Bisibility app instead.

`list_keywords` supports `country`, `device`, `tag`, `topic`, `intent`,
`position_gt`/`position_lt`, `search` and `sort` filters via
`ListKeywordsOptions` (or a plain dict); `topic` and `intent` match the keyword
classification fields, case-insensitively.

### Signals

Ingest deploy/CMS/API events as signals and read them back per project.
`create_signal` requires `source` (`"deploy"`, `"cms"`, or `"api"`) and `type`
(shaped like `category.event`, e.g. `"deploy.completed"`); `payload` must
serialize to 8KB or less. `list_project_signals` returns signals newest first
and accepts `source`, `type` and a `from`/`to` time range (use the `from_`
field name, or the `"from"` key in a dict).

```python
from bisibility import CreateSignalInput, ListSignalsOptions

emitted = bisibility.create_signal(
    CreateSignalInput(
        source="deploy",
        type="deploy.completed",
        payload={"version": "1.2.3"},
        url="https://example.com/releases/1",
    )
)

signals = bisibility.list_project_signals(
    project_id,
    ListSignalsOptions(source="deploy", from_="2026-07-01T00:00:00Z"),
)
```

### Public cost estimates

`get_provider_rates` and `get_cost_estimate` are public discovery endpoints and
work without an API key. `get_cost_estimate` requires `keywords` and accepts
`locations`, `devices` (1-2), `frequency` (`"daily"`, `"weekly"`,
`"monthly"`), `provider`, and a flat-rate `option` or plan `plan` selector.
Both return a `DataResponse` whose `data` is typed (`list[ProviderRate]` and
`CostEstimate`).

```python
from bisibility import BisibilityClient, CostEstimateOptions

anonymous = BisibilityClient()  # no api_key needed for these calls

rates = anonymous.get_provider_rates()
estimate = anonymous.get_cost_estimate(
    CostEstimateOptions(keywords=248, frequency="daily", provider="dataforseo")
)
print(estimate.data.monthly_cost_usd)
```

### Async rank checks

`run_rank_check` blocks until the check completes by default. Pass
`async_mode=True` to queue the check instead: the server responds with
`202 Accepted` and a rank check in status `"running"`; poll
`get_rank_check_result` until the status becomes `"completed"` or `"failed"`.

```python
queued = bisibility.run_rank_check(keyword_id, async_mode=True)
assert queued.status == "running"

result = bisibility.get_rank_check_result(queued.id)
```

## Typed Inputs

Plain dictionaries are supported for request bodies, and pydantic input models are
available when you want validation and editor completion.

```python
from bisibility import CreateKeywordInput, CreateKeywordsBatch, KeywordScheduleInput

created = bisibility.create_keywords(
    project_id,
    CreateKeywordsBatch(
        keywords=[
            CreateKeywordInput(
                keyword="rank tracker",
                target_url="https://example.com/rank-tracker",
                tags=["api"],
                schedule=KeywordScheduleInput(
                    frequency="daily",
                    cron_expression=None,
                ),
            )
        ]
    ),
)
```

New app-surface endpoints also have typed request models. Plain dictionaries remain supported.

```python
from bisibility import (
    AlertRuleInput,
    ApiKeyCreateInput,
    ConnectProviderInput,
    ProjectDefaultsPatch,
    ProviderCredentialsInput,
    UpdateProjectInput,
)

project = bisibility.update_project(
    project_id, UpdateProjectInput(name="Marketing site")
)

defaults = bisibility.update_project_defaults(
    project_id,
    ProjectDefaultsPatch(frequency="daily", location_key="US/Texas/Austin"),
)

api_key = bisibility.create_api_key(ApiKeyCreateInput(name="CI"))

rule = bisibility.create_alert_rule(
    project_id,
    AlertRuleInput(
        channels=["email"],
        condition_type="threshold",
        name="Ranking drop",
        target_type="all",
        threshold_position=10,
    ),
)

provider = bisibility.connect_provider(
    project_id,
    "serpapi",
    ConnectProviderInput(
        credentials=ProviderCredentialsInput(api_key="serpapi-secret"),
        primary=True,
    ),
)

# Self-hosted analytics providers (e.g. "plausible") accept an optional
# endpoint credential pointing at the instance API.
analytics = bisibility.connect_provider(
    project_id,
    "plausible",
    ConnectProviderInput(
        credentials=ProviderCredentialsInput(
            api_key="plausible-secret",
            endpoint="https://plausible.example.com/api",
        ),
    ),
)
```

## Errors

Non-2xx API responses raise `BisibilityApiError`. The RFC problem details body is
available on `error.problem` when the server returns one.

```python
from bisibility import BisibilityApiError

try:
    bisibility.get_keyword("kw_z9y8x7w6v5u4t3s2r1q0p9n8")
except BisibilityApiError as error:
    print(error.status, error.problem.detail if error.problem else error.body)
```

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
