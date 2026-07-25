# Changelog

## Unreleased

## 0.2.0 - 2026-07-26

- Added `get_project_defaults` to read the effective default market and schedule settings for a project.
- Matched project defaults to the current API contract by adding SERP settings and typed source provenance.
- Removed the retired auto-schedule field from schedule models.
- Rejected null, empty, and whitespace-only `hmac_secret` on webhook update; omit the field to leave the secret unchanged.

## 0.1.0 - 2026-07-24

- Initial release.
