# Changelog

## Unreleased

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
