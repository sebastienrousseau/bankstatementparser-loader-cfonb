<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# bankstatementparser-loader-cfonb Architecture

A map of the codebase for new contributors and maintainers: how a
CFONB 120 statement becomes `Transaction` objects, and where to change
what.

## The pipeline

```text
CFONB 120 payload (str, iterable of lines, or file)
        |  _parse_cfonb_stream: one pass over the lines
        |    01 -> _handle_header_01   (bank, branch, currency, decimals, account, opening balance)
        |    04 -> _handle_operation_04 (one dict per operation)
        |    05 -> _handle_detail_05   (text appended to the open operation)
        |    07 -> _handle_closing_07  (closing balance)
        |    anything else -> skipped
        v
_CfonbState (header fields, balances, list of operation dicts)
        |
        +--> load_cfonb       -> list[Transaction] (source="cfonb")
        +--> summarize_cfonb  -> CfonbSummary (balances, dates, totals, no Transaction)
```

`load_cfonb_file` reads a path as UTF-8 (undecodable bytes replaced)
and calls `load_cfonb`. `CfonbStatementParser`, the plugin the core
finds through the `cfonb` and `afb120` entry points, wraps the same
functions for the core's `parse()` (a pandas DataFrame),
`to_transactions()` and `get_summary()` (cached after the first read).

## Modules

| Area | Module | Responsibility |
| :--- | :--- | :--- |
| **Loader** | `bankstatementparser_loader_cfonb/loader.py` | Record dispatch, the amount and date decoders, `load_cfonb` / `load_cfonb_file` / `summarize_cfonb`, `CfonbSummary`, `CfonbStatementParser` |
| **Package entry** | `bankstatementparser_loader_cfonb/__init__.py` | Re-exports the public API and defines `__version__` (single source of truth) |
| **Tests** | `tests/` | 100% line + branch coverage: unit and Hypothesis tests (`test_loader.py`), records built at the standard's columns (`test_cfonb120_layout.py`), the golden fixture, non-ASCII digits, the documented layout and Quick Start (`test_docs_accuracy.py`), examples, release notes and the shared suite conformance gate |
| **Fuzzing** | `fuzz/fuzz_load_cfonb.py`, `fuzz/corpus/` | Atheris target for `load_cfonb` and `summarize_cfonb`, run by the CI `Fuzz` job |
| **Benchmarks** | `benches/bench_load_cfonb.py` | Load and summary cost as a statement grows; `--quick` runs in CI |
| **Examples** | `examples/` | Two runnable scripts: loading and summarising, and the parser plugin with a balance reconciliation |
| **Manual** | `mkdocs.yml`, `docs/` | The MkDocs Material user manual and API reference, deployed to GitHub Pages |
| **Scripts** | `scripts/` | `verify_versions.py`, `release_notes.py`, `export_locked_requirements.py`, `check_complexity.py`, `check_suite_consistency.py`, `readme-check.sh` |

## How an operation becomes a transaction

1. An `04` record opens an operation: the bank, branch, currency and
   account fall back to the `01` header's when blank; the interbank
   code (33-34), operation date (35-40), value date (43-48, else the
   operation date), label (49-79), entry number (82-88) and amount
   (91-104) are sliced from their columns.
2. `_decode_cfonb_amount` replaces the amount's final character by its
   units digit and sign, keeps the ASCII digits and scales them by the
   header's number of decimals (column 20, default 2).
3. Each following `05` record appends its text (49-118) to the label.
4. The next `04` or an `07` closes the operation; `load_cfonb` turns
   each into a `Transaction`, numbering them with `source_index`.

## Key design decisions

- **Decimal everywhere.** Amounts are integers scaled with
  `Decimal.scaleb`; `float` appears only in the DataFrame and the
  credit and debit totals of the summary dict the core's interface
  asks for.
- **Lenient input.** CRLF, blank, short and unknown lines and
  unparsable dates or amounts never raise; numeric zones count ASCII
  digits only, so a stray character cannot become a number.
- **One pass.** Both entry points share `_parse_cfonb_stream`; the
  summary never builds `Transaction` objects.
- **Coverage enforced at 100%** line + branch and docstring, and every
  function within the suite's complexity ceilings.

## Extension points

- **A new record code:** add it to the dispatch in `_parse_cfonb_stream`.
- **`05` qualifiers:** `_handle_detail_05` keeps the text only; parsing
  a qualifier (46-48) into its own field would start there.
- **A summary field:** extend `CfonbSummary`, `summarize_cfonb` and
  `CfonbSummaryRecord`.
