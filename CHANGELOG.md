# Changelog

All notable changes to `bankstatementparser-loader-cfonb` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Breaking:** `get_summary()` returns `opening_balance` and `closing_balance` as
  `Decimal` (or `None`), as the core `SummaryRecord` declares, instead of `float`.
  The values are exact, decoded from the record text. Code comparing them with a
  float literal must compare with a `Decimal` instead: `Decimal("17049.98") == 17049.98`
  is `False`. `total_credit` and `total_debit` stay `float`.

### Fixed

- `get_summary()` returns `CfonbSummaryRecord`, a `SummaryRecord` subtype, so the
  override matches the core parser's contract and `mypy` passes against
  bankstatementparser 0.0.29.

## [0.0.19] - 2026-09-01

### Added
- Initial production release of `bankstatementparser-loader-cfonb`: CFONB 120 / AFB120 Banking Statement Loader.
- 100% statement and branch test coverage.
- High-concurrency throughput testing (>10,000 TPS) with sub-second response times.
- Strict type hints (`mypy --strict`) and ruff linting.
- Integration with the core `bankstatementparser` ecosystem.
