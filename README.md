# French CFONB 120 / AFB120 Statement Loader for Bank Statement Parser

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0_OR_MIT-blue.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/sebastienrousseau/bankstatementparser-loader-cfonb)

A high-performance, enterprise-grade French CFONB 120 (Comité Français d'Organisation et de Normalisation Bancaires) and AFB120 fixed-width banking statement loader plugin for [`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser).

---

## Features

- **Standard Fixed-Width Record Parsing**: Complete support for CFONB 120 record codes:
  - `01`: Opening Balance (`Ancien solde`)
  - `04`: Movement / Operation (`Mouvements d'opérations`)
  - `05`: Complementary Details (`Détails complémentaires / libellés étendus`)
  - `07`: Closing Balance (`Nouveau solde`)
- **Signed Zoned Decimal Support**: Full support for French signed overpunch / zoned decimal characters (`{`, `}`, `A`-`I`, `J`-`R`, `+`, `-`, `C`, `D`).
- **Seamless Plugin Integration**: Dynamically registers under `bankstatementparser.loaders` entry points (`cfonb`, `afb120`).
- **Comprehensive Output**: Produces standardized `Transaction` models and `pandas.DataFrame` tables.

---

## Installation

```bash
pip install bankstatementparser-loader-cfonb
```

---

## Quickstart

```python
from bankstatementparser_loader_cfonb import load_cfonb_file, summarize_cfonb

# 1. Parse statement into standard Transaction models
transactions = load_cfonb_file("statement.cfonb")
for tx in transactions:
    print(f"{tx.date} | {tx.description} | {tx.amount} {tx.currency}")

# 2. Get statement summary
summary = summarize_cfonb(open("statement.cfonb").read())
print(f"Account: {summary.account_id}")
print(
    f"Opening: {summary.opening_balance} | Closing: {summary.closing_balance}"
)
```

---

## License

Dual-licensed under Apache 2.0 and MIT.
