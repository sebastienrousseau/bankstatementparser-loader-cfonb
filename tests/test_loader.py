# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Tests for French CFONB 120 / AFB120 Banking Statement Loader."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from hypothesis import given
from hypothesis import strategies as st

from bankstatementparser_loader_cfonb import (
    CfonbStatementParser,
    CfonbSummary,
    __version__,
    load_cfonb,
    load_cfonb_file,
    summarize_cfonb,
)
from bankstatementparser_loader_cfonb.loader import (
    _decode_cfonb_amount,
    _parse_cfonb_date,
    _parse_cfonb_stream,
)


def _sample_cfonb_120_text() -> str:
    """Return a standard CFONB 120 statement with opening balance, movements, details, and closing."""
    # 01 record (Header / Ancien Solde)
    # 1500000 cents = 15000.00 EUR
    l1 = (
        "01"
        "10057"
        "19000"
        "EUR"
        "2"
        "     "
        "00012345678"
        "  "
        "010126" + " " * 50 + "0000001500000"
        "C" + " " * 16
    )

    # 04 record (Operation 1: Credit Virement)
    # 250000 cents = 2500.00 EUR
    l2 = (
        "04"
        "10057"
        "19000"
        "EUR"
        "2"
        "     "
        "00012345678"
        "02"
        "050126"
        "  "
        "050126"
        "VIREMENT RECU CLIENT ACME      "
        "  "
        "REF1234"
        "  "
        "0000000250000"
        "+" + " " * 16
    )

    # 05 record (Complementary detail for Operation 1)
    l3 = (
        "05"
        "10057"
        "19000"
        "EUR"
        "2"
        "     "
        "00012345678"
        "02"
        "050126"
        "LIB1"
        "FACTURE INV-2026-999 PAYEE PAR VIREMENT SEPA EMETTEUR ACME CORP       "
        + " "
        * 6
    )

    # 04 record (Operation 2: Debit Prelevement with signed zoned decimal 'K' = -2)
    # 0000000045000 + K -> -450.02
    l4 = (
        "04"
        "10057"
        "19000"
        "EUR"
        "2"
        "     "
        "00012345678"
        "03"
        "100126"
        "  "
        "100126"
        "PRELEVEMENT EDF ELECTRICITE    "
        "  "
        "REF5678"
        "  "
        "0000000045000"
        "K" + " " * 16
    )

    # 07 record (Closing Balance / Nouveau Solde)
    # 1704998 cents = 17049.98 EUR
    l5 = (
        "07"
        "10057"
        "19000"
        "EUR"
        "2"
        "     "
        "00012345678"
        "  "
        "310126" + " " * 50 + "0000001704998"
        "C" + " " * 16
    )

    return "\n".join([l1, l2, l3, l4, l5])


def test_version() -> None:
    """Verifies that version is exposed and semantic."""
    assert __version__ == "0.0.19"


def test_decode_cfonb_amount_zoned_positive() -> None:
    """Tests zoned decimal decode for positive numbers."""
    assert _decode_cfonb_amount("000000015000", "{", 2) == Decimal("150.00")
    assert _decode_cfonb_amount("00000001500", "A", 2) == Decimal("15.01")
    assert _decode_cfonb_amount("00000001500", "B", 2) == Decimal("15.02")
    assert _decode_cfonb_amount("00000001500", "I", 2) == Decimal("15.09")
    assert _decode_cfonb_amount("00000001500", "+", 2) == Decimal("15.00")
    assert _decode_cfonb_amount("00000001500", "C", 2) == Decimal("15.00")
    assert _decode_cfonb_amount("150B", "", 2) == Decimal("15.02")


def test_decode_cfonb_amount_zoned_negative() -> None:
    """Tests zoned decimal decode for negative numbers."""
    assert _decode_cfonb_amount("000000015000", "}", 2) == Decimal("-150.00")
    assert _decode_cfonb_amount("00000001500", "J", 2) == Decimal("-15.01")
    assert _decode_cfonb_amount("00000001500", "K", 2) == Decimal("-15.02")
    assert _decode_cfonb_amount("00000001500", "R", 2) == Decimal("-15.09")
    assert _decode_cfonb_amount("00000001500", "-", 2) == Decimal("-15.00")
    assert _decode_cfonb_amount("00000001500", "D", 2) == Decimal("-15.00")
    assert _decode_cfonb_amount("150K", "", 2) == Decimal("-15.02")


def test_decode_cfonb_amount_edge_cases() -> None:
    """Tests amount decoder edge cases including zero decimals and blanks."""
    assert _decode_cfonb_amount("", "") == Decimal("0.00")
    assert _decode_cfonb_amount("   ", "") == Decimal("0.00")
    assert _decode_cfonb_amount("---", "") == Decimal("0.00")
    assert _decode_cfonb_amount("100", "", num_decimals=0) == Decimal("100")
    assert _decode_cfonb_amount("5", "", num_decimals=3) == Decimal("0.005")
    assert _decode_cfonb_amount("150A", "", num_decimals=2) == Decimal("15.01")
    assert _decode_cfonb_amount("150J", "", num_decimals=2) == Decimal(
        "-15.01"
    )
    assert _decode_cfonb_amount("12", "", num_decimals=4) == Decimal("0.0012")
    assert _decode_cfonb_amount("1234", "X", num_decimals=2) == Decimal(
        "12.34"
    )


def test_parse_cfonb_date() -> None:
    """Tests JJMMAA date parser."""
    assert _parse_cfonb_date("150126") == date(2026, 1, 15)
    assert _parse_cfonb_date("") is None
    assert _parse_cfonb_date("123") is None
    assert _parse_cfonb_date("999999") is None
    assert _parse_cfonb_date("abcdef") is None


def test_load_cfonb_full_stream() -> None:
    """Tests full stream parsing with transactions and complementary details."""
    text = _sample_cfonb_120_text()
    txs = load_cfonb(text)

    assert len(txs) == 2
    t1 = txs[0]
    assert t1.booking_date == date(2026, 1, 5)
    assert t1.value_date == date(2026, 1, 5)
    assert t1.amount == Decimal("2500.00")
    assert t1.currency == "EUR"
    assert t1.account_id == "00012345678"
    assert t1.reference == "REF1234"
    assert "ACME CORP" in (t1.description or "")
    assert t1.category == "cfonb:02"
    assert t1.source == "cfonb"
    assert t1.source_index == 0

    t2 = txs[1]
    assert t2.booking_date == date(2026, 1, 10)
    assert t2.amount == Decimal("-450.02")
    assert t2.currency == "EUR"
    assert t2.account_id == "00012345678"
    assert t2.reference == "REF5678"
    assert t2.category == "cfonb:03"
    assert t2.source_index == 1


def test_summarize_cfonb() -> None:
    """Tests summary generation with balances and totals."""
    text = _sample_cfonb_120_text()
    summary = summarize_cfonb(text)

    assert isinstance(summary, CfonbSummary)
    assert summary.account_id == "00012345678"
    assert summary.bank_code == "10057"
    assert summary.branch_code == "19000"
    assert summary.currency == "EUR"
    assert summary.opening_balance == Decimal("15000.00")
    assert summary.closing_balance == Decimal("17049.98")
    assert summary.opening_date == date(2026, 1, 1)
    assert summary.closing_date == date(2026, 1, 31)
    assert summary.transaction_count == 2
    assert summary.total_credit == Decimal("2500.00")
    assert summary.total_debit == Decimal("450.02")


def test_cfonb_statement_parser_class(tmp_path: Path) -> None:
    """Tests CfonbStatementParser BankStatementParser protocol implementation."""
    sample_file = tmp_path / "statement.cfonb"
    sample_file.write_text(_sample_cfonb_120_text(), encoding="utf-8")

    parser = CfonbStatementParser(sample_file)
    df = parser.parse()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "amount" in df.columns
    assert "date" in df.columns
    assert "account_id" in df.columns

    summary = parser.get_summary()
    assert summary["account_id"] == "00012345678"
    assert summary["bank_code"] == "10057"
    assert summary["opening_balance"] == 15000.00
    assert summary["closing_balance"] == 17049.98
    assert summary["opening_date"] == "2026-01-01"
    assert summary["closing_date"] == "2026-01-31"
    assert summary["transaction_count"] == 2
    assert summary["total_credit"] == 2500.00
    assert summary["total_debit"] == 450.02


def test_cfonb_statement_parser_empty_file(tmp_path: Path) -> None:
    """Tests CfonbStatementParser on empty file."""
    empty_file = tmp_path / "empty.cfonb"
    empty_file.write_text("", encoding="utf-8")

    parser = CfonbStatementParser(empty_file)
    df = parser.parse()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    assert "amount" in df.columns

    summary = parser.get_summary()
    assert summary["transaction_count"] == 0
    assert summary["opening_balance"] is None
    assert summary["closing_balance"] is None
    assert summary["opening_date"] is None
    assert summary["closing_date"] is None


def test_parse_cfonb_stream_fallback_value_date() -> None:
    """Tests that missing value date falls back to booking date."""
    # 04 line without value date in pos 43-48
    line = (
        "04"
        "10057"
        "19000"
        "EUR"
        "2"
        "     "
        "00012345678"
        "02"
        "050126"
        "  "
        "      "  # blank value date
        "SAMPLE WITHOUT VALUE DATE      "
        "  "
        "REF9999"
        "  "
        "0000000100000"
        "+" + " " * 16
    )
    txs = load_cfonb(line)
    assert len(txs) == 1
    assert txs[0].booking_date == date(2026, 1, 5)
    assert txs[0].value_date == date(2026, 1, 5)


def test_parse_cfonb_stream_ignoring_short_or_unknown_lines() -> None:
    """Tests that lines shorter than 2 chars or unknown record codes are safely ignored."""
    lines = ["", "X", "99unknown record", "01", "04", "07"]
    state = _parse_cfonb_stream(lines)
    assert len(state.records) == 1  # 04 created one record


def test_load_cfonb_file(tmp_path: Path) -> None:
    """Tests load_cfonb_file helper."""
    f = tmp_path / "test.cfonb"
    f.write_text(_sample_cfonb_120_text(), encoding="utf-8")
    txs = load_cfonb_file(f)
    assert len(txs) == 2


@given(
    amount_int=st.integers(min_value=0, max_value=999999999),
    sign_char=st.sampled_from(
        ["{", "}", "A", "B", "J", "K", "+", "-", "C", "D", ""]
    ),
)
def test_fuzz_amount_decoder(amount_int: int, sign_char: str) -> None:
    """Property-based fuzzing of the CFONB amount decoder."""
    raw_str = f"{amount_int:012d}"
    val = _decode_cfonb_amount(raw_str, sign_char, num_decimals=2)
    assert isinstance(val, Decimal)
