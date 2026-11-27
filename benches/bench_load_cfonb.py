#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.
"""What a CFONB 120 statement costs to load, as the statement grows.

A CFONB 120 statement is an ``01`` opening balance, one ``04`` record
per operation (each optionally followed by ``05`` complementary
records) and a ``07`` closing balance, 120 characters a line. Its size
is set by how many operations the account saw that day, not by the
caller, so the axis that moves in practice is the number of ``04``
records. Every other operation here carries a ``05`` detail, which the
loader appends to the operation's label.

Read ``us/txn``. Flat means linear, and a busy account's statement is
fine. Climbing means something rescans records it has already read.

``summarize_cfonb`` is measured beside ``load_cfonb``: it parses the
same records but builds no ``Transaction`` objects, so a caller that
only wants balances and totals should pay less.

Run::

    python benches/bench_load_cfonb.py
    python benches/bench_load_cfonb.py --json
    python benches/bench_load_cfonb.py --quick     # what CI runs

Nothing here asserts a threshold: wall-clock is not comparable between
machines, and a flaky performance gate teaches people to ignore red. CI
runs ``--quick`` so a benchmark that has stopped running against the
current API fails the build instead of rotting into a file that reads
as verified and is not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bankstatementparser_loader_cfonb import (  # noqa: E402
    load_cfonb,
    summarize_cfonb,
)

# Columns 1-34 of every record: code, bank, internal code, branch,
# currency, number of decimals, a blank, account, interbank code.
PREFIX = "{code}30004012300456EUR2 00012345678{interbank}"
# Positive ("{" .. "I") and negative ("}" .. "R") final characters.
UNITS = "{ABCDEFGHI}JKLMNOPQR"


def _amount(i: int) -> str:
    """A 14-character amount zone, alternating credit and debit."""
    return f"{(i % 90000) + 100:013d}{UNITS[(i % 2) * 10 + i % 10]}"


def operation(i: int) -> str:
    """One 120-character ``04`` record."""
    head = PREFIX.format(code="04", interbank="02" if i % 2 else "03")
    label = f"OPERATION {i}"
    return (
        f"{head}050126  060126{label:<32} {f'E{i:06d}':<7}  "
        f"{_amount(i)}{f'REF{i:08d}':<16}"
    )


def complement(i: int) -> str:
    """One 120-character ``05`` record."""
    head = PREFIX.format(code="05", interbank="02")
    return f"{head}050126     LIB{f'DETAIL FOR OPERATION {i}':<70}  "


def balance(code: str) -> str:
    """An ``01`` or ``07`` balance record."""
    head = PREFIX.format(code=code, interbank="  ")
    return f"{head}010126{' ' * 50}0000001500000{{{' ' * 16}"


def build(operations: int) -> str:
    """A statement of ``operations`` operations, half with a detail."""
    lines = [balance("01")]
    for i in range(operations):
        lines.append(operation(i))
        if i % 2 == 0:
            lines.append(complement(i))
    lines.append(balance("07"))
    return "\n".join(lines)


def _best(call: Callable[[], object], repeats: int) -> float:
    """Best-of timing after one untimed warm-up.

    The minimum is the least noisy estimator available; the mean follows
    whatever else the machine happens to be doing.
    """
    call()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        samples.append(time.perf_counter() - start)
    return min(samples)


def measure(operations: int, repeats: int) -> dict[str, Any]:
    """Time ``load_cfonb`` and ``summarize_cfonb`` on one statement size."""
    text = build(operations)
    load = _best(lambda: load_cfonb(text), repeats)
    summary = _best(lambda: summarize_cfonb(text), repeats)
    transactions = len(load_cfonb(text))
    if transactions != operations or (
        summarize_cfonb(text).transaction_count != operations
    ):
        raise SystemExit(f"expected {operations} records, read {transactions}")
    return {
        "transactions": transactions,
        "bytes": len(text),
        "load_ms": load * 1e3,
        "summary_ms": summary * 1e3,
        "us_per_txn": load * 1e6 / transactions,
        "summary_over_load": summary / load,
    }


def run(quick: bool) -> list[dict[str, Any]]:
    """Measure every statement size; ``quick`` keeps to the small ones."""
    if quick:
        sizes, repeats = [10, 100], 3
    else:
        sizes, repeats = [10, 100, 1_000, 10_000, 50_000], 7
    return [measure(n, repeats) for n in sizes]


def render(rows: list[dict[str, Any]]) -> None:
    """Print the table and what it means."""
    print(
        f"{'operations':>11}{'KiB':>9}{'load ms':>10}"
        f"{'summary ms':>12}{'us/txn':>9}"
    )
    for row in rows:
        print(
            f"{row['transactions']:>11}{row['bytes'] / 1024:>9.1f}"
            f"{row['load_ms']:>10.2f}{row['summary_ms']:>12.2f}"
            f"{row['us_per_txn']:>9.2f}"
        )
    drift = rows[-1]["us_per_txn"] / rows[0]["us_per_txn"]
    print(
        f"\n  us/txn at {rows[-1]['transactions']:,} operations is "
        f"{drift:.2f}x the cost at {rows[0]['transactions']:,}. Flat is "
        f"linear; climbing means something rescans records it has "
        f"already read."
    )
    worst = max(r["summary_over_load"] for r in rows)
    print(
        f"\n  summarize_cfonb costs up to {worst:.2f}x load_cfonb. A ratio "
        f"near 1.00 would mean the summary pays for Transaction objects "
        f"it never returns."
    )


def main() -> int:
    """Parse the options, run, and print a table or JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--quick", action="store_true", help="small sizes, as CI runs"
    )
    args = parser.parse_args()

    rows = run(quick=args.quick)
    if args.json:
        json.dump(rows, sys.stdout, indent=1)
        print()
    else:
        render(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
