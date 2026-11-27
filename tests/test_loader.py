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
    _CfonbState,
    _decode_cfonb_amount,
    _parse_cfonb_date,
    _parse_cfonb_stream,
)
from tests.test_cfonb120_layout import detail, record


def _sample_cfonb_120_text() -> str:
    """A CFONB 120 statement: balance, two operations, a detail, balance."""
    return "\n".join(
        [
            # 01 Ancien solde: 15000.00 EUR
            record(
                "01", bank="10057", branch="19000", amount="0000000150000{"
            ),
            # 04 Mouvement: credit transfer, 2500.00
            record(
                "04",
                bank="10057",
                branch="19000",
                interbank="02",
                date="050126",
                value="050126",
                label="VIREMENT RECU CLIENT ACME",
                entry="REF1234",
                amount="0000000025000{",
            ),
            # 05 Complement for the credit transfer
            detail("FACTURE INV-2026-999 PAYEE PAR VIREMENT SEPA ACME CORP"),
            # 04 Mouvement: direct debit, "K" is -2: -450.02
            record(
                "04",
                bank="10057",
                branch="19000",
                interbank="03",
                date="100126",
                value="100126",
                label="PRELEVEMENT EDF ELECTRICITE",
                entry="REF5678",
                amount="0000000004500K",
            ),
            # 07 Nouveau solde: 17049.98 ("H" is +8)
            record(
                "07",
                bank="10057",
                branch="19000",
                date="310126",
                amount="0000000170499H",
            ),
        ]
    )


def test_version() -> None:
    """Verifies that version is exposed and semantic."""
    assert __version__ == "0.0.35"


def test_decode_cfonb_amount_zoned_positive() -> None:
    """``{`` and ``A``-``I`` are the positive units digits 0 to 9."""
    assert _decode_cfonb_amount("0000000015000{", 2) == Decimal("1500.00")
    assert _decode_cfonb_amount("0000000000150A", 2) == Decimal("15.01")
    assert _decode_cfonb_amount("0000000000150B", 2) == Decimal("15.02")
    assert _decode_cfonb_amount("0000000000150I", 2) == Decimal("15.09")
    assert _decode_cfonb_amount("150B", 2) == Decimal("15.02")


def test_decode_cfonb_amount_zoned_negative() -> None:
    """``}`` and ``J``-``R`` are the negative units digits 0 to 9."""
    assert _decode_cfonb_amount("0000000015000}", 2) == Decimal("-1500.00")
    assert _decode_cfonb_amount("0000000000150J", 2) == Decimal("-15.01")
    assert _decode_cfonb_amount("0000000000150K", 2) == Decimal("-15.02")
    assert _decode_cfonb_amount("0000000000150R", 2) == Decimal("-15.09")
    assert _decode_cfonb_amount("150K", 2) == Decimal("-15.02")


def test_decode_cfonb_amount_edge_cases() -> None:
    """Blanks, zero scales, plain digits and a negative zero."""
    assert _decode_cfonb_amount("") == Decimal("0.00")
    assert _decode_cfonb_amount("   ") == Decimal("0.00")
    assert _decode_cfonb_amount("---") == Decimal("0.00")
    assert _decode_cfonb_amount("100", num_decimals=0) == Decimal("100")
    assert _decode_cfonb_amount("5", num_decimals=3) == Decimal("0.005")
    assert _decode_cfonb_amount("12", num_decimals=4) == Decimal("0.0012")
    assert _decode_cfonb_amount("1234", 2) == Decimal("12.34")
    zero = _decode_cfonb_amount("0000000000000}", 2)
    assert zero == 0 and not zero.is_signed()


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
    assert summary["opening_balance"] == Decimal("15000.00")
    assert summary["closing_balance"] == Decimal("17049.98")
    assert type(summary["opening_balance"]) is Decimal
    assert type(summary["closing_balance"]) is Decimal
    assert summary["opening_date"] == "2026-01-01"
    assert summary["closing_date"] == "2026-01-31"
    assert summary["transaction_count"] == 2
    assert summary["total_credit"] == 2500.00
    assert summary["total_debit"] == 450.02


def test_get_summary_balances_are_decimal_not_float(tmp_path: Path) -> None:
    """The summary balances keep their exact decimal value, as SummaryRecord declares.

    A float would round-trip 17049.98 inexactly and break the core contract.
    """
    sample_file = tmp_path / "statement.cfonb"
    sample_file.write_text(_sample_cfonb_120_text(), encoding="utf-8")

    summary = CfonbStatementParser(sample_file).get_summary()

    for key in ("opening_balance", "closing_balance"):
        value = summary[key]
        assert isinstance(value, Decimal), f"{key} is {type(value).__name__}"
        assert not isinstance(value, float)
    assert str(summary["closing_balance"]) == "17049.98"


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
    line = record(
        "04",
        interbank="02",
        date="050126",
        label="SAMPLE WITHOUT VALUE DATE",
        entry="REF9999",
        amount="0000000010000{",
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
    amount_int=st.integers(min_value=0, max_value=10**13 - 1),
    unit=st.sampled_from(list("{ABCDEFGHI}JKLMNOPQR0123456789")),
)
def test_fuzz_amount_decoder(amount_int: int, unit: str) -> None:
    """Property: the zone decodes to its 13 digits, units digit and sign."""
    val = _decode_cfonb_amount(f"{amount_int:013d}{unit}", num_decimals=2)
    index = "{ABCDEFGHI}JKLMNOPQR".find(unit)
    digit = int(unit) if index < 0 else index % 10
    magnitude = Decimal(amount_int * 10 + digit) / 100
    assert val == (-magnitude if index >= 10 else magnitude)


def test_state_keeps_records_it_is_given() -> None:
    """A records list passed in is kept, not replaced by an empty one."""
    seed = [{"amount": Decimal("1.00")}]
    state = _CfonbState(records=seed)
    assert state.records is seed


def test_detail_without_an_operation_is_dropped() -> None:
    """A 05 line before any 04 operation has nothing to attach to."""
    state = _parse_cfonb_stream([detail("ORPHAN DETAIL")])
    assert state.records == []


def test_closing_without_a_pending_operation() -> None:
    """A 07 closing line with no open operation records nothing."""
    state = _parse_cfonb_stream(["07"])
    assert state.records == []


def test_summary_is_read_once_and_cached(tmp_path: Path) -> None:
    """A second get_summary() call reuses the first result."""
    sample_file = tmp_path / "statement.cfonb"
    sample_file.write_text(_sample_cfonb_120_text(), encoding="utf-8")
    parser = CfonbStatementParser(sample_file)

    first = parser.get_summary()
    sample_file.unlink()
    assert parser.get_summary() == first
