# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Golden test for ``tests/fixtures/statement.cfonb``.

The fixture is a whole CFONB 120 statement at the standard's columns
(an opening balance, a credit transfer with a ``05`` detail, a direct
debit, a closing balance) that the README demo and the fuzz seeds use;
this pins what the loader reads from it.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from bankstatementparser_loader_cfonb import (
    CfonbStatementParser,
    load_cfonb_file,
    summarize_cfonb,
)

FIXTURE = Path(__file__).parent / "fixtures" / "statement.cfonb"


def test_transactions() -> None:
    """Every 04 record becomes one signed transaction."""
    rows = [
        (t.booking_date, t.amount, t.category, t.reference)
        for t in load_cfonb_file(FIXTURE)
    ]
    assert rows == [
        (date(2026, 1, 5), Decimal("2500.00"), "cfonb:02", "REF1234"),
        (date(2026, 1, 10), Decimal("-450.02"), "cfonb:03", "REF5678"),
    ]


def test_summary() -> None:
    """The summary carries the balances, dates and totals."""
    summary = summarize_cfonb(FIXTURE.read_text(encoding="utf-8"))
    assert (summary.bank_code, summary.branch_code) == ("10057", "19000")
    assert summary.account_id == "00012345678"
    assert summary.opening_balance == Decimal("15000.00")
    assert summary.closing_balance == Decimal("17049.98")
    assert summary.opening_date == date(2026, 1, 1)
    assert summary.closing_date == date(2026, 1, 31)
    assert summary.total_credit - summary.total_debit == Decimal("2049.98")


def test_parser_plugin() -> None:
    """The core's plugin interface reads the same file."""
    parser = CfonbStatementParser(str(FIXTURE))
    assert list(parser.parse()["amount"]) == [2500.0, -450.02]
    assert parser.get_summary()["transaction_count"] == 2
