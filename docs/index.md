# bankstatementparser-loader-cfonb

**CFONB 120** (also called AFB120) is the French banks' fixed-width
account statement format: 120-character records, an `01` opening
balance, one `04` record per operation with optional `05` complementary
records, and an `07` closing balance.

**bankstatementparser-loader-cfonb** turns a CFONB 120 statement into a
flat list of
[`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser)
`Transaction` objects (`source="cfonb"`) that the rest of a
deterministic pipeline can consume unchanged.

| Concern | How this loader handles it |
| :--- | :--- |
| Records | `01`, `04`, `05` and `07`; any other line is skipped |
| Columns | The published layout: bank 3-7, branch 12-16, currency 17-19, number of decimals 20, account 22-32, amount 91-104 |
| Amounts | 13 digits and a final character carrying the units digit and the sign (`{`, `A`-`I` positive; `}`, `J`-`R` negative), scaled by the number of decimals, as `Decimal` (never `float`) |
| Details | Each `05` record's text (49-118) is appended to the preceding operation's label |
| Dates | `JJMMAA` (day, month, two-digit year); the value date falls back to the operation date |
| Errors | None raised for malformed text: a line that is not a record is skipped, a zone that does not parse falls back |

## In this manual

- [CFONB 120 support](format.md): the public API, the record layout,
  the field mapping and the sign convention.
- [The suite](suite.md): the `bankstatementparser` packages.
- [Comparison](COMPARISON.md) and [Benchmarks](BENCHMARKS.md).
- [Supported Python policy](POLICIES.md).
- [API reference](api.md): generated from the docstrings.
- [Changelog](changelog.md) and [Security policy](security.md).

The source, issues and releases live on
[GitHub](https://github.com/sebastienrousseau/bankstatementparser-loader-cfonb);
the package is on
[PyPI](https://pypi.org/project/bankstatementparser-loader-cfonb/).
