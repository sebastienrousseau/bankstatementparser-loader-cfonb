# Examples for bankstatementparser-loader-cfonb

Runnable scripts with an inline CFONB 120 sample, so no data files are
needed. CI runs every one (`tests/test_regression_examples.py` and the
`Examples` job).

- `01_basic_usage.py`: `load_cfonb` and `summarize_cfonb` on a statement
  with an opening balance, a credit transfer and its `05` detail, a
  direct debit and a closing balance, built at the standard's columns.
- `02_advanced_workflow.py`: the core's `CfonbStatementParser` plugin
  reading the same statement from disk as a DataFrame and a summary,
  and checking that the opening balance plus the operations equals the
  closing balance.

```sh
python examples/01_basic_usage.py
```
