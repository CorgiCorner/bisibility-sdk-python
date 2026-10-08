# Changelog

## 0.12.0 - 2026-10-07

- Add typed project context, agent reports, AI visibility, prompt comparison, and site-audit
  methods, including strict report IDs and cursor iteration.
- Keep queued rank-check polling active until the matching check is completed or failed; the
  asynchronous helper now polls without blocking and supports cancellation.
- Support cloud-import package and session versions 6 and 7, including current ranking-history
  metadata, canonical location keys, and alert severity. Preserve required null history values,
  accept server-advertised integer compatibility versions, and reject ambiguous legacy history.
- Correct product, public-ID, project-creation, migration, and documentation-link guidance.

## 0.11.1 - 2026-09-27

- Replaced the stale README version label with a link to the current package registry release.

## 0.11.0 - 2026-09-27

- Added saved research report reads and separate own-key and credit provider budget methods.

- **Breaking for typed consumers:** `analyze_backlinks` now returns `data` as
  `BacklinksEstimate | BacklinksSnapshot`. With `estimate_only=True` the API answers with a
  cost-only `BacklinksEstimate` that carries no `summary`, `history`, `rows`, `fetched_at`,
  `fetched_row_count`, or `total_rows_available`, and `BacklinksSnapshot` no longer carries
  `estimate` or `estimated_cost_cents`. Use `isinstance(response.data, BacklinksEstimate)` to tell
  them apart. `load_more_backlink_rows` still returns a snapshot.
- **Breaking for typed consumers:** `KeywordResearchResponse` is now the union
  `KeywordResearchEstimate | KeywordResearchResult` instead of one model. With
  `estimate_only=True` the API answers with a cost-only `KeywordResearchEstimate` whose
  `sources` carry `{source, cost_cents, cached}` only, and `KeywordResearchResult` no longer
  carries `estimate`. Use `isinstance(response, KeywordResearchEstimate)` to tell them apart.
- Add `serp_depth` (`10`, `20`, `50`, or `100`) to `ProjectDefaultsPatch`. Omitting it keeps the
  stored depth, like `serp_stop_on_match`; the schedule fields are still replaced as a whole.
- `connect_provider` now sends `priority` with the connect request instead of following the
  connect with a settings PATCH, so connecting at a chosen priority is a single request. A
  rejected priority now fails the connect with `BisibilityApiError`;
  `BisibilityProviderPrioritySyncError` stays exported but is deprecated and no longer raised.
- Document that a provider connection test answers `"Connected."`, or `"Connected · <detail>."`
  for analytics providers, and that Plausible's `credentials.login` is the Plausible site domain
  (its `site_id`) that defaults to the project domain when omitted, with `credentials.api_key`
  holding the Stats API token.
- Export `BacklinksEstimate`, `BacklinksOutcome`, `BacklinksTargetScope`,
  `KeywordResearchEstimate`, `KeywordResearchEstimateSource`, `KeywordResearchResult`, and
  `SerpDepth`.

## 0.10.0 - 2026-09-20

- Add `max_cost_cents` to `RunRankCheckInput`; the server refuses the check with
  `cost_limit_exceeded` when its preflight estimate is higher.
- Send `X-Bisibility-Source: sdk` on every request so the API can report SDK usage separately;
  a caller-provided `X-Bisibility-Source` default header wins.

## 0.9.0 - 2026-09-05

- Model the queued rank-check contract: `run_rank_check` returns either the completed check or the
  queued run answered with 202, and rank checks carry `run_id`.
- Add `run_rank_check_and_wait`, which follows a queued run to its check and raises
  `BisibilityTimeoutError` at the deadline.
- Register the `rcr` rank-check-run public identifier prefix.

## 0.8.0 - 2026-08-14

- Add language-qualified market fields to typed keyword and location models.

## 0.7.0 - 2026-08-13

- Add typed sync and async Domain Overview analyze, history, ranked-keyword, and relevant-page
  operations with explicit provider-cost caps.

## 0.6.0 - 2026-08-10

- `connect_provider` now applies requested priority with a follow-up settings update. Deprecated
  `primary=True` still selects priority `0`; `primary=False` remains a no-op. If the follow-up
  update fails, `BisibilityProviderPrioritySyncError` exposes the connected provider for recovery.

## 0.5.1 - 2026-08-04

- No client API or runtime behavior changes. This maintenance release updates public package
  validation and preserves the 0.5.0 client surface.

## 0.5.0 - 2026-08-02

- **Breaking for typed consumers:** `get_health`, `get_liveness`, and `get_readiness` now return
  status-only responses; degraded health and readiness HTTP 503 responses return normally without
  retries, while other endpoints retain 503 retries.
- Added `AsyncBisibilityClient`, `create_async_bisibility_client`, async context manager support,
  and async iterator parity with the synchronous client.
- Added `list_saved_keywords`, `iter_saved_keywords`, `create_saved_keywords`, and
  `delete_saved_keyword` with `svkw` public IDs.

## 0.4.1 - 2026-07-30

- Improved package metadata to describe the SDK's SEO rank-tracking, keyword, and ranking-history
  capabilities.

## 0.4.0 - 2026-07-29

- Adopt the strict public ID v3 registry and reject legacy or malformed opaque cursors.
- Accept `bsb_key_live_`, `bsb_key_test_`, and `bsb_pat_live_` credentials while rejecting the
  retired `bsk_` and `bsp_` formats.
- Update cloud transfer models to package version 5.

## 0.3.1 - 2026-07-28

- Use nullable `ranking_url` to identify which result URL a stored keyword position belongs to
  after the last completed check.

## 0.3.0 - 2026-07-27

- Add typed project keyword matching that distinguishes normalized request `matched_text` from
  stored keyword `text` and reports partial matching-market rows through `meta.truncated_texts`.
- Add typed project overview reads with dashboard filters.
- Add typed Backlinks analyze and load-more operations.

## 0.2.1 - 2026-07-26

- No library changes. The package contents are identical to `0.2.0`; this release carries the
  PyPI publication workflow into the release snapshot so the project can be published.

## 0.2.0 - 2026-07-26

- Added `get_project_defaults` to read the effective default market and schedule settings for a project.
- Matched project defaults to the current API contract by adding SERP settings and typed source provenance.
- Removed the retired auto-schedule field from schedule models.
- Rejected null, empty, and whitespace-only `hmac_secret` on webhook update; omit the field to leave the secret unchanged.

## 0.1.0 - 2026-07-24

- Initial release.
- Changed the default request timeout from 10 seconds to 30 seconds.
