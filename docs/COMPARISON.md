# Comparison

Where bankstatementparser-loader-cfonb fits next to the other CFONB 120
reader a Python user would reach for. Every cell comes from the
projects' own source code, read on 2026-11-27; nothing here is a
measured ranking.

| Project | Output | Malformed input | `05` records | Writes CFONB | Licence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **bankstatementparser-loader-cfonb** | `bankstatementparser` `Transaction` objects, a `CfonbSummary`, or a DataFrame through the core's plugin interface | Skipped or read leniently; never raises | Text appended to the operation's label | No | Apache-2.0 OR MIT |
| [`python-cfonb`](https://github.com/dhatim/python-cfonb) 2.13 (fork of akretion's) | `Statement` objects (header row, operation rows, footer row), one per account | Raises `ParsingError` on a line that is not `01`/`04`/`05`/`07` or does not match its record pattern (length, digits, amount) | Parsed by qualifier into extra fields and a comment | Yes (statements and transfers) | LGPL |
| [`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser) 0.0.35 | `Transaction` objects | Not applicable | Not applicable | No | Apache-2.0 OR MIT |

Both CFONB readers use the same columns: bank 3-7, branch 12-16,
currency 17-19, number of decimals 20, account 22-32, amount 91-104
with an overpunched final character. Evidence:
`cfonb/parser/common.py` and `cfonb/parser/statement.py` in
python-cfonb 2.13, `bankstatementparser/parsers/` in the core (no
CFONB parser), and `bankstatementparser_loader_cfonb/loader.py` here.

## When each fits

- **bankstatementparser-loader-cfonb**: you want CFONB 120 operations as
  signed `Transaction` objects next to statements from other formats,
  and a file with a stray line should still load.
- **python-cfonb**: you also write CFONB files, want the `05`
  qualifiers parsed into fields, or want a malformed file refused, and
  its LGPL licence suits you.

The wider family is listed in [The suite](suite.md).
