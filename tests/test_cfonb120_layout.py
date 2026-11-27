# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Records laid out as the published CFONB 120 standard lays them out.

The CFONB "Relevé de compte sur support informatique" layout puts the
bank code at columns 3-7, an internal operation code at 8-11, the
branch (guichet) at 12-16, the currency at 17-19, the number of
decimals at 20, the account at 22-32 and the amount at 91-104: 13
digits and a final character that carries both the units digit and the
sign (``{`` and ``A``-``I`` positive, ``}`` and ``J``-``R`` negative).
On a ``04`` record the label is 49-79 and the entry number 82-88; on a
``05`` record the qualifier is 46-48 and the complementary information
49-118.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from bankstatementparser_loader_cfonb import load_cfonb, summarize_cfonb
from bankstatementparser_loader_cfonb.loader import _decode_cfonb_amount


def record(code: str, **f: str) -> str:
    """One 120-character record from its CFONB 120 fields."""
    line = (
        code
        + f.get("bank", "30004")
        + f.get("op", "0123")
        + f.get("branch", "00456")
        + f.get("ccy", "EUR")
        + f.get("scale", "2")
        + " "
        + f.get("account", "00012345678")
        + f.get("interbank", "  ")
        + f.get("date", "010126")
        + f.get("reject", "  ")
        + f.get("value", "      ")
        + f.get("label", "").ljust(31)
        + "  "
        + f.get("entry", "").ljust(7)
        + "  "
        + f.get("amount", "").rjust(14)
        + f.get("ref", "").ljust(16)
    )
    assert len(line) == 120, len(line)
    return line


def detail(info: str, qualifier: str = "LIB") -> str:
    """A ``05`` complementary record carrying ``info`` at 49-118."""
    head = record("05")[:40] + "     " + qualifier
    return head + info.ljust(70) + "  "


@pytest.mark.parametrize(
    ("field", "scale", "expected"),
    [
        ("0000000001904}", 2, "-190.40"),
        ("0000000150000{", 2, "15000.00"),
        ("0000000025000E", 2, "2500.05"),
        ("0000000025000R", 2, "-2500.09"),
        ("0000000001904}", 0, "-19040"),
        ("0000000001904}", 3, "-19.040"),
        ("00000000250000", 2, "2500.00"),
    ],
)
def test_amount_is_thirteen_digits_and_a_signed_unit(
    field: str, scale: int, expected: str
) -> None:
    """The final character is the units digit and the sign."""
    assert _decode_cfonb_amount(field, scale) == Decimal(expected)


STATEMENT = "\n".join(
    [
        record("01", date="010126", amount="0000000150000{"),
        record(
            "04",
            interbank="02",
            date="050126",
            value="060126",
            label="VIREMENT RECU ACME CORPORATION",
            entry="E000042",
            amount="0000000001904}",
            ref="REF-0001",
        ),
        detail("FACTURE 2026-999"),
        record("07", date="310126", amount="0000000148096{"),
    ]
)


def test_an_operation_at_the_published_columns() -> None:
    """The 04 and 05 records read at their columns."""
    (txn,) = load_cfonb(STATEMENT)
    assert (txn.amount, txn.currency) == (Decimal("-190.40"), "EUR")
    assert txn.account_id == "00012345678"
    assert (txn.booking_date, txn.value_date) == (
        date(2026, 1, 5),
        date(2026, 1, 6),
    )
    assert txn.description == (
        "VIREMENT RECU ACME CORPORATION FACTURE 2026-999"
    )
    assert (txn.reference, txn.category) == ("E000042", "cfonb:02")


def test_balances_at_the_published_columns() -> None:
    """The 01 and 07 records read at their columns."""
    summary = summarize_cfonb(STATEMENT)
    assert (summary.bank_code, summary.branch_code) == ("30004", "00456")
    assert summary.currency == "EUR"
    assert summary.opening_balance == Decimal("15000.00")
    assert summary.closing_balance == Decimal("14809.60")
    assert summary.total_debit == Decimal("190.40")


def test_scale_is_read_from_column_20() -> None:
    """The number of decimals on the header applies to the amounts."""
    text = "\n".join(
        [
            record("01", ccy="JPY", scale="0", amount="0000000001500{"),
            record("04", ccy="JPY", scale="0", amount="0000000000150{"),
        ]
    )
    (txn,) = load_cfonb(text)
    assert txn.amount == Decimal("1500")
    assert txn.currency == "JPY"
    assert summarize_cfonb(text).opening_balance == Decimal("15000")
