# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Coverage-guided Atheris fuzz target for the CFONB 120 loader.

``load_cfonb`` and ``summarize_cfonb`` are the package's two entry
points for untrusted text. Neither documents an exception: a line that
is not a ``01``, ``04``, ``05`` or ``07`` record is skipped, and a zone
that does not parse falls back (an amount to its ASCII digits, a date
to none, the number of decimals to 2). Any exception escapes the target
and libFuzzer records it as a crash.

Every transaction that loads must also be well formed: a finite amount,
``source == "cfonb"`` and, when it has a category (a blank interbank
code leaves none), a ``cfonb:<code>`` one; and the summary of the same
text must count the same transactions and net to the same total.

Run (Linux x86_64, Python 3.12+, ``poetry install --with fuzz``)::

    python fuzz/fuzz_load_cfonb.py fuzz/corpus -max_total_time=60
"""

from __future__ import annotations

import sys
from decimal import Decimal

import atheris

with atheris.instrument_imports():
    from bankstatementparser_loader_cfonb import load_cfonb, summarize_cfonb


def test_one_input(data: bytes) -> None:
    """Load and summarise one fuzz input as CFONB 120 text."""
    text = atheris.FuzzedDataProvider(data).ConsumeUnicodeNoSurrogates(
        len(data)
    )
    transactions = load_cfonb(text)
    net = Decimal(0)
    for txn in transactions:
        if not txn.amount.is_finite():
            raise AssertionError(f"non-finite amount {txn.amount!r}")
        category = txn.category or "cfonb:"
        if txn.source != "cfonb" or not category.startswith("cfonb:"):
            raise AssertionError(f"mislabelled transaction {txn!r}")
        net += txn.amount
    summary = summarize_cfonb(text)
    if summary.transaction_count != len(transactions):
        raise AssertionError("summary and load disagree on the count")
    if summary.total_credit - summary.total_debit != net:
        raise AssertionError("summary and load disagree on the total")


def main() -> None:
    """Hand the target to libFuzzer with the command-line options."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
