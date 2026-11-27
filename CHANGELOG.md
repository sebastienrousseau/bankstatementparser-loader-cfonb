# Changelog

All notable changes to `bankstatementparser-loader-cfonb` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- CI: four pinned actions move to their latest releases:
  codeql-action 4.39.5, markdownlint-cli2-action 25.1.0,
  cosign-installer 4.1.4 and sbom-action 0.24.4.

## [0.0.36] - 2026-11-27

### Fixed

- **Breaking for files in the old layout:** the loader now reads the
  columns of the published CFONB 120 standard. It took the branch
  (guichet) from columns 8-12 instead of 12-16, the currency from 13-15
  instead of 17-19 and the number of decimals from 16 instead of 20, and
  read the amount as 13 digits plus a separate sign at 104. The amount
  is 14 characters at 91-104 whose last character is both the units
  digit and the sign (`{`, `A`-`I` positive; `}`, `J`-`R` negative), so
  a bank's `0000000001904}` (-190.40) loaded as -19.04; a final `C`
  (+3) was taken as a bare credit sign. The `05` detail is read from
  49-118 (it was 45-114).
  `tests/test_cfonb120_layout.py` builds records from the standard.
- A non-ASCII digit (a superscript such as `²`) in the number of
  decimals no longer aborts the load with `ValueError`; numeric zones
  and dates count ASCII `0`-`9` only.
- The examples' sample statement used the old layout; they now build
  records at the standard's columns.

### Added

- An Atheris fuzz target, `fuzz/fuzz_load_cfonb.py`, for `load_cfonb`
  and `summarize_cfonb`, with a seed corpus; it fails on any exception,
  a malformed `Transaction` or a summary that disagrees with the load.
  CI runs it for 120 s on every change; `make fuzz` locally.
- `benches/bench_load_cfonb.py`, a real benchmark of `load_cfonb` and
  `summarize_cfonb` on statements of 10 to 50,000 operations, replacing
  a file that timed an empty loop. CI runs `--quick`;
  `docs/BENCHMARKS.md` records a full run with its environment.
- `tests/fixtures/statement.cfonb`, a whole statement, with a golden
  test.
- A `Makefile` wrapping the local gates (`make check`).
- A MkDocs Material user manual (`mkdocs.yml`, `docs/`) with an
  mkdocstrings API reference, built with `--strict` on every pull
  request and deployed to GitHub Pages from `main`
  (`.github/workflows/docs.yml`, `make docs`). It replaces a Sphinx
  configuration that nothing built.
- `ARCHITECTURE.md`, `CODE_OF_CONDUCT.md`, `docs/POLICIES.md`,
  `docs/BENCHMARKS.md`, `docs/COMPARISON.md`, `docs/format.md` and
  `docs/suite.md`.
- Signed releases: keyless cosign `.sig` and `.pem` per distribution,
  SLSA provenance
  (`bankstatementparser-loader-cfonb-vX.Y.Z.intoto.jsonl`,
  slsa-github-generator 2.1.0), CycloneDX and SPDX SBOMs and a licence
  manifest on every GitHub release, and PEP 740 attestations on PyPI.
- The OpenSSF Scorecard workflow, the suite's Docs Lint workflow
  (`scripts/readme-check.sh` and markdownlint), a Security workflow
  (Bandit and `pip-audit` on every locked set), the portfolio pull
  request and issue templates, and `.github/demo.gif` rendered by
  `make demo` from `.github/demo.tape`.
- Hash-pinned requirement sets exported from the lock
  (`requirements/{runtime,ci,fuzz,docs}.txt`, by the suite's
  `scripts/export_locked_requirements.py`) and compiled release tooling
  (`requirements/{build,sbom}.txt`).

### Changed

- Require `bankstatementparser >= 0.0.35`, the newest core release, and
  align the version with the suite's 0.0.36 release; `poetry.lock`
  moves core to 0.0.35.
- Dev tools: ruff 0.17.6, mypy 2.4.1, pytest 9.2.0, hypothesis 6.168.5,
  tomli 2.5.0 and pytest-benchmark 5.3.1 (Dependabot #4 to #9).
- CI pins every action by commit SHA, installs only the hashed lock
  exports, and tests CPython 3.10 to 3.14 on Ubuntu, macOS and Windows.
  Write permissions sit on the jobs that need them.
- `README.md` follows the portfolio template; its Quick Start and
  record layout are checked by the tests. The suite table moves to
  `docs/suite.md`. `CONTRIBUTING.md` describes the steps that work in
  this repository.

## [0.0.35] - 2026-11-26

The first release on PyPI. Versions 0.0.20 to 0.0.34 were never
released: the package joins the bankstatementparser suite, which ships
one version across every package, at 0.0.35.

### Added

- `.github/workflows/release.yml`: a `v*` tag builds the sdist and
  wheel, publishes them to PyPI by trusted publishing, attaches them to
  a GitHub release and writes its notes with `scripts/release_notes.py`
  from the highlights in `.github/releases/<tag>.md`.
- `.github/workflows/pr.yml` (PR Gate) and
  `.github/workflows/suite-consistency.yml`, a daily check that every
  suite package on PyPI agrees on one version
  (`scripts/check_suite_consistency.py`).
- `scripts/verify_versions.py` and the suite's shared
  `tests/test_suite_conformance.py` and `tests/test_release_notes.py`.
- `.github/dependabot.yml`: weekly pip and GitHub Actions updates.
- `scripts/check_complexity.py`, the suite's complexity gate, with
  `scripts/complexity_baseline.json`: per-function ceilings
  (cyclomatic 10, cognitive 15, Halstead 30, 60 lines; 500 lines per
  file), run in CI's lint job. Functions already over a ceiling are
  baselined and may not get worse.
- `.github/workflows/codeql.yml`: CodeQL as an advanced setup for
  Python and GitHub Actions, on pushes and pull requests to `main`
  and weekly.

### Changed

- **Breaking:** `get_summary()` returns `opening_balance` and `closing_balance` as
  `Decimal` (or `None`), as the core `SummaryRecord` declares, instead of `float`.
  The values are exact, decoded from the record text. Code comparing them with a
  float literal must compare with a `Decimal` instead: `Decimal("17049.98") == 17049.98`
  is `False`. `total_credit` and `total_debit` stay `float`.
- Requires `bankstatementparser >= 0.0.34` (was `>= 0.0.18`).
- The coverage gate measures branches (`--cov-branch`). Four branches
  in `loader.py` that no test took are now covered; coverage is 100%
  with branches counted.
- Dev dependency floor `pytest >= 9.0.3`, the release that fixes
  PYSEC-2026-1845; `tomli` (Python < 3.11) and `packaging` declared for
  the conformance test.
- GitHub Actions: `actions/checkout` v7, `actions/setup-python` v7.

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
