# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""CFONB 120 numeric zones are ASCII digits; nothing else counts.

``str.isdigit`` is also true for superscripts and for the digits of
other scripts, which ``int`` refuses. A stray ``"²"`` in the number of
decimals (header column 20) used to escape ``load_cfonb`` and
``summarize_cfonb`` as ``ValueError``.
"""

from __future__ import annotations

from decimal import Decimal

from bankstatementparser_loader_cfonb import load_cfonb, summarize_cfonb
from bankstatementparser_loader_cfonb.loader import (
    _decode_cfonb_amount,
    _parse_cfonb_date,
)
from tests.test_cfonb120_layout import record


def test_superscript_scale_keeps_the_default() -> None:
    """A non-ASCII digit in column 20 leaves the scale at 2."""
    text = "\n".join(
        [
            record("01", scale="²", amount="0000000150000{"),
            record("04", scale="²", amount="0000000001904}"),
        ]
    )
    (txn,) = load_cfonb(text)
    assert txn.amount == Decimal("-190.40")
    assert summarize_cfonb(text).opening_balance == Decimal("15000.00")


def test_superscript_in_amount_is_not_a_digit() -> None:
    """Only the ASCII digits of an amount are read."""
    assert _decode_cfonb_amount("000000002²5{", 2) == Decimal("2.50")


def test_other_script_digits_in_amount_are_not_read() -> None:
    """Arabic-Indic digits are not centimes."""
    assert _decode_cfonb_amount("١٢", 2) == Decimal("0.00")


def test_non_ascii_date_is_not_a_date() -> None:
    """A date with a non-ASCII digit does not parse."""
    assert _parse_cfonb_date("1²0126") is None
    assert _parse_cfonb_date("١٥٠١٢٦") is None
