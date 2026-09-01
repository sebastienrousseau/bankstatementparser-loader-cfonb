<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

<p align="center">
  <img
    src="https://cloudcdn.pro/bankstatementparser/v1/logos/bankstatementparser.svg"
    alt="bankstatementparser-loader-cfonb logo"
    width="120"
    height="120"
  />
</p>

<h1 align="center">bankstatementparser-loader-cfonb</h1>

<p align="center">
  <b>French CFONB 120 / AFB120 fixed-width banking statement loader plugin for bankstatementparser.</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/bankstatementparser-loader-cfonb/"><img src="https://img.shields.io/pypi/v/bankstatementparser-loader-cfonb?style=for-the-badge" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/bankstatementparser-loader-cfonb/"><img src="https://img.shields.io/pypi/pyversions/bankstatementparser-loader-cfonb.svg?style=for-the-badge" alt="Python versions" /></a>
  <a href="https://pypi.org/project/bankstatementparser-loader-cfonb/"><img src="https://img.shields.io/pypi/dm/bankstatementparser-loader-cfonb.svg?style=for-the-badge" alt="PyPI downloads" /></a>
  <a href="https://github.com/sebastienrousseau/bankstatementparser-loader-cfonb/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/sebastienrousseau/bankstatementparser-loader-cfonb/ci.yml?branch=main&label=Tests&style=for-the-badge" alt="Tests" /></a>
  <a href="#license"><img src="https://img.shields.io/pypi/l/bankstatementparser-loader-cfonb?style=for-the-badge" alt="License" /></a>
</p>

---

## Contents

- [What is bankstatementparser-loader-cfonb?](#what-is-bankstatementparser-loader-cfonb) — the problem it solves
- [Install](#install) — PyPI, virtualenv
- [Quick start](#quick-start) — parse a file in three lines
- [Public API](#public-api) — `load_cfonb`, `load_cfonb_file`, `summarize_cfonb`
- [Supported CFONB subset](#supported-cfonb-subset) — record codes and signed zoned decimals
- [Amount and sign convention](#amount-and-sign-convention) — French zoned decimal decoding
- [Development](#development) — quality gates, tests
- [Ecosystem](#ecosystem) — modular package suite
- [Contributing](#contributing)
- [License](#license)

---

## What is bankstatementparser-loader-cfonb?

**CFONB 120** (Comité Français d'Organisation et de Normalisation Bancaires) and **AFB120** is the standard 120-character fixed-width bank statement format widely used across French and Francophone corporate banking environments.

**bankstatementparser-loader-cfonb** is an enterprise-grade loader plugin that parses CFONB 120 statement files into standard `bankstatementparser` `Transaction` objects and `pandas.DataFrame` tables.

| Concern | How this loader handles it |
| :--- | :--- |
| **Record Types** | Parses Record `01` (Opening Balance), `04` (Operation Movement), `05` (Complementary Details), `07` (Closing Balance) |
| **Zoned Decimal** | Fully decodes French signed overpunch characters (`{`, `}`, `A`-`I`, `J`-`R`, `+`, `-`, `C`, `D`) |
| **Amounts** | Converts minor units (centimes) to exact `Decimal` objects (never `float`) |
| **Dates** | Translates French DDMMYY dates into standard Python `datetime.date` |
| **Multi-account** | Seamlessly groups operations and balances per RIB/IBAN account |

---

## Install

| Channel | Command | Notes |
| :--- | :--- | :--- |
| PyPI | `pip install bankstatementparser-loader-cfonb` | Pulls in `bankstatementparser >= 0.0.19` |
| Source | `git clone https://github.com/sebastienrousseau/bankstatementparser-loader-cfonb && cd bankstatementparser-loader-cfonb && poetry install` | For local development |

Requires Python 3.10 or later. Compatible with macOS, Linux, and Windows.

<details>
<summary>Using an isolated virtual environment (recommended)</summary>

```sh
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
python -m pip install -U bankstatementparser-loader-cfonb
```

</details>

---


## Quick start

```python
from bankstatementparser_loader_cfonb import load_cfonb_file, summarize_cfonb

# Parse statement into standard Transaction models
transactions = load_cfonb_file("statement.cfonb")
for tx in transactions:
    print(f"{tx.booking_date} | {tx.description} | {tx.amount} {tx.currency}")

# Extract statement summary
summary = summarize_cfonb(open("statement.cfonb").read())
print(f"Account: {summary.account_id}")
print(f"Opening Balance: {summary.opening_balance} | Closing Balance: {summary.closing_balance}")
```

---

## Public API

- `load_cfonb(data: str | bytes) -> list[Transaction]`: Ingests CFONB string/bytes and returns unified `Transaction` objects.
- `load_cfonb_file(file_path: str | Path) -> list[Transaction]`: Reads a local CFONB file.
- `summarize_cfonb(data: str | bytes) -> CfonbSummary`: Extracts balances, date bounds, operation counts, and metadata.
- `CfonbStatementParser`: Parser class with `parse()` (returning DataFrame) and `to_transactions()`.

---

## Supported CFONB Subset

| Code | Record Name | Description |
| :--- | :--- | :--- |
| `01` | Ancien solde | Opening statement balance |
| `04` | Mouvement d'opération | Main transaction record with amount, date, and basic label |
| `05` | Détail complémentaire | Extended multi-line transaction narrative and references |
| `07` | Nouveau solde | Closing statement balance |

---

## Amount and sign convention

CFONB 120 encodes amounts in the final columns of records `01`, `04`, and `07` with the last digit replaced by a signed EBCDIC/ASCII overpunch character:
- Positive / Credit (`+`, `{`, `A`–`I`, `C`): `A`=1, `B`=2, ..., `I`=9, `{`=0
- Negative / Debit (`-`, `}`, `J`–`R`, `D`): `J`=1, `K`=2, ..., `R`=9, `}`=0

The loader automatically resolves these characters and returns exact signed `Decimal` amounts.

---

## Development

The project enforces strict code-quality gates: 100% test and branch coverage, strict type annotations (`mypy`), style linting (`ruff`), docstring coverage (`interrogate`), and security scanning (`bandit`).

```bash
# Run test suite with branch coverage enforcement
poetry run pytest

# Type checking and linting
poetry run mypy .
poetry run ruff check .
poetry run ruff format --check .

# Documentation and security gates
poetry run interrogate -v
poetry run bandit -r . -c pyproject.toml
```

---


## Ecosystem

`bankstatementparser` is part of a modular financial ecosystem. Optional companion packages provide specialized loaders, writers, AI agents, language servers, and transport protocol adapters:

| Package | GitHub Repository | PyPI | Role | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`bankstatementparser`** | [`sebastienrousseau/bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser.svg)](https://pypi.org/project/bankstatementparser/) | Core Engine | Unified parser for CAMT (052/053), PAIN.001, CSV, OFX, QFX, MT940, and PDF statements |
| **`bankstatementparser-mcp`** | [`sebastienrousseau/bankstatementparser-mcp`](https://github.com/sebastienrousseau/bankstatementparser-mcp) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-mcp.svg)](https://pypi.org/project/bankstatementparser-mcp/) | AI Protocol | Model Context Protocol (MCP) server exposing statement tools to LLMs & AI agents |
| **`bankstatementparser-lsp`** | [`sebastienrousseau/bankstatementparser-lsp`](https://github.com/sebastienrousseau/bankstatementparser-lsp) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-lsp.svg)](https://pypi.org/project/bankstatementparser-lsp/) | Developer Tooling | Language Server Protocol (LSP) with live SWIFT MT940 statement validation & diagnostics |
| **`bankstatementparser-transport-ebics`** | [`sebastienrousseau/bankstatementparser-transport-ebics`](https://github.com/sebastienrousseau/bankstatementparser-transport-ebics) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-transport-ebics.svg)](https://pypi.org/project/bankstatementparser-transport-ebics/) | Transport | Automated bank statement retrieval over EBICS 3.0 (`H005`) and 2.5 (`H004`) protocols |
| **`bankstatementparser-writer-xlsx`** | [`sebastienrousseau/bankstatementparser-writer-xlsx`](https://github.com/sebastienrousseau/bankstatementparser-writer-xlsx) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-writer-xlsx.svg)](https://pypi.org/project/bankstatementparser-writer-xlsx/) | Output Writer | Formats and exports parsed banking transactions into styled Microsoft Excel (`.xlsx`) workbooks |
| **`bankstatementparser-writer-qif`** | [`sebastienrousseau/bankstatementparser-writer-qif`](https://github.com/sebastienrousseau/bankstatementparser-writer-qif) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-writer-qif.svg)](https://pypi.org/project/bankstatementparser-writer-qif/) | Output Writer | Serializes transactions into standard Quicken Interchange Format (`.qif`) exchange files |
| **`bankstatementparser-writer-ofx`** | [`sebastienrousseau/bankstatementparser-writer-ofx`](https://github.com/sebastienrousseau/bankstatementparser-writer-ofx) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-writer-ofx.svg)](https://pypi.org/project/bankstatementparser-writer-ofx/) | Output Writer | Serializes transactions into standard Open Financial Exchange (`.ofx`) XML/SGML files |
| **`bankstatementparser-writer-swift`** | [`sebastienrousseau/bankstatementparser-writer-swift`](https://github.com/sebastienrousseau/bankstatementparser-writer-swift) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-writer-swift.svg)](https://pypi.org/project/bankstatementparser-writer-swift/) | Output Writer | Exports transactions to SWIFT MT940 customer statements and MT942 interim reports |
| **`bankstatementparser-loader-bai2`** | [`sebastienrousseau/bankstatementparser-loader-bai2`](https://github.com/sebastienrousseau/bankstatementparser-loader-bai2) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-loader-bai2.svg)](https://pypi.org/project/bankstatementparser-loader-bai2/) | Input Loader | Parses BAI2 cash-management and account balance statements |
| **`bankstatementparser-loader-mt942`** | [`sebastienrousseau/bankstatementparser-loader-mt942`](https://github.com/sebastienrousseau/bankstatementparser-loader-mt942) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-loader-mt942.svg)](https://pypi.org/project/bankstatementparser-loader-mt942/) | Input Loader | Parses SWIFT MT942 interim transaction reports with credit/debit summary reconciliation |
| **`bankstatementparser-loader-cfonb`** | [`sebastienrousseau/bankstatementparser-loader-cfonb`](https://github.com/sebastienrousseau/bankstatementparser-loader-cfonb) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-loader-cfonb.svg)](https://pypi.org/project/bankstatementparser-loader-cfonb/) | Input Loader | Parses French CFONB 120 / AFB120 120-byte fixed-width banking statement files |
| **`bankstatementparser-loader-camt054`** | [`sebastienrousseau/bankstatementparser-loader-camt054`](https://github.com/sebastienrousseau/bankstatementparser-loader-camt054) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-loader-camt054.svg)](https://pypi.org/project/bankstatementparser-loader-camt054/) | Input Loader | Ingests ISO 20022 CAMT.054 real-time debit/credit notification stream XML |
| **`bankstatementparser-loader-sepa`** | [`sebastienrousseau/bankstatementparser-loader-sepa`](https://github.com/sebastienrousseau/bankstatementparser-loader-sepa) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-loader-sepa.svg)](https://pypi.org/project/bankstatementparser-loader-sepa/) | Input Loader | Ingests ISO 20022 SEPA PAIN.002 payment status reports and PAIN.008 direct debit mandates |
| **`bankstatementparser-loader-bacs`** | [`sebastienrousseau/bankstatementparser-loader-bacs`](https://github.com/sebastienrousseau/bankstatementparser-loader-bacs) | [![PyPI](https://img.shields.io/pypi/v/bankstatementparser-loader-bacs.svg)](https://pypi.org/project/bankstatementparser-loader-bacs/) | Input Loader | Parses UK BACS Standard 18 / Faster Payments 106-byte fixed-width transmission files |

---

## Contributing

Contributions are welcome! Please submit an issue or pull request on GitHub. Ensure that all quality gates pass and test coverage remains at 100%.

---

## License

This project is dual-licensed under the **Apache License 2.0** and the **MIT License**. See [LICENSE-APACHE](LICENSE-APACHE) and [LICENSE-MIT](LICENSE-MIT) for full details.

