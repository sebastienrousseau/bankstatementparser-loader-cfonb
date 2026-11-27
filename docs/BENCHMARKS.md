# Benchmarks

`benches/bench_load_cfonb.py` measures what a CFONB 120 statement costs
to load as it grows in the one direction a statement grows in practice:
the number of `04` operations between the `01` and `07` balances.
Every other operation carries a `05` detail, which the loader appends to
the label. It times `load_cfonb` and, beside it, `summarize_cfonb`,
which parses the same records but builds no `Transaction` objects.

Each figure is the best of 7 runs after one untimed warm-up. Nothing
asserts a threshold: wall-clock is not comparable between machines. CI
runs `python benches/bench_load_cfonb.py --quick` on every push so the
benchmark keeps running against the current API.

## Results

Run with `poetry run python benches/bench_load_cfonb.py` on 2026-11-27:
Apple M1 Pro, macOS 27.2.1, CPython 3.12.16,
bankstatementparser-loader-cfonb 0.0.36, bankstatementparser 0.0.35.

| Operations | KiB | `load_cfonb` ms | `summarize_cfonb` ms | us per operation |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 2.0 | 0.12 | 0.10 | 11.62 |
| 100 | 18.0 | 0.99 | 0.86 | 9.95 |
| 1000 | 177.5 | 10.50 | 8.60 | 10.50 |
| 10000 | 1772.7 | 110.76 | 92.41 | 11.08 |
| 50000 | 8862.5 | 633.81 | 492.49 | 12.68 |

The cost per operation at 50,000 operations is 1.09x the cost at 10, so
loading grows close to linearly with the statement: no step rescans the
records already read. `summarize_cfonb` costs at most 0.87x
`load_cfonb`: the summary still parses every record and joins every
`05` detail onto its operation, and saves only the `Transaction`
objects.

Reproduce with `python benches/bench_load_cfonb.py` (add `--json` for
machine-readable output).
