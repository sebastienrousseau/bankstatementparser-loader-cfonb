# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Core CFONB 120 / AFB120 Fixed-Width Banking Statement Loader."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
from bankstatementparser.base_parser import BankStatementParser
from bankstatementparser.transaction_models import Transaction

SOURCE = "cfonb"

# Zoned decimal sign maps for French banking
_POSITIVE_ZONED: dict[str, str] = {
    "{": "0",
    "A": "1",
    "B": "2",
    "C": "3",
    "D": "4",
    "E": "5",
    "F": "6",
    "G": "7",
    "H": "8",
    "I": "9",
    "+": "0",
    " ": "0",
}

_NEGATIVE_ZONED: dict[str, str] = {
    "}": "0",
    "J": "1",
    "K": "2",
    "L": "3",
    "M": "4",
    "N": "5",
    "O": "6",
    "P": "7",
    "Q": "8",
    "R": "9",
    "-": "0",
}


def _resolve_sign_and_digits(raw: str, sign: str) -> tuple[bool, str]:
    """Determine sign and substituted digits for zoned decimal decoding.

    Args:
        raw: Raw amount string.
        sign: Sign character or zoned overpunch indicator.

    Returns:
        Tuple of (is_negative flag, substituted digits string).
    """
    if (
        raw
        and raw[-1] in _NEGATIVE_ZONED
        and not raw[-1].isdigit()
        and raw[-1] != "-"
    ):
        return True, raw[:-1] + _NEGATIVE_ZONED[raw[-1]]
    if (
        raw
        and raw[-1] in _POSITIVE_ZONED
        and not raw[-1].isdigit()
        and raw[-1] not in ("+", " ")
    ):
        return False, raw[:-1] + _POSITIVE_ZONED[raw[-1]]
    if sign in ("-", "D", "d", "}") or sign in _NEGATIVE_ZONED:
        sub = _NEGATIVE_ZONED.get(sign, "")
        digits = (
            (raw[:-1] + sub)
            if sub and sign not in ("-", "D", "d", "}")
            else raw
        )
        return True, digits
    if sign in _POSITIVE_ZONED:
        sub = _POSITIVE_ZONED.get(sign, "")
        digits = (
            (raw[:-1] + sub)
            if sub and sign not in ("+", "C", "c", "{", "", " ")
            else raw
        )
        return False, digits
    return False, raw


def _decode_cfonb_amount(
    raw_amount: str, sign_char: str = "", num_decimals: int = 2
) -> Decimal:
    """Decode a CFONB 120 amount field with optional signed zoned decimal or trailing sign.

    Args:
        raw_amount: The numeric string (e.g. 13 characters '0000000150000').
        sign_char: Trailing sign indicator or zoned decimal character.
        num_decimals: Number of decimal places (default 2).

    Returns:
        Signed Decimal amount.
    """
    raw_clean = raw_amount.strip()
    sign_clean = sign_char.strip()

    if not raw_clean and not sign_clean:
        return Decimal("0.00")

    is_negative, digits = _resolve_sign_and_digits(raw_clean, sign_clean)
    digits_only = "".join(ch for ch in digits if ch.isdigit())
    if not digits_only:
        return Decimal("0.00")

    if num_decimals == 0:
        val_str = digits_only
    elif len(digits_only) > num_decimals:
        integer_part = digits_only[:-num_decimals] or "0"
        fractional_part = digits_only[-num_decimals:]
        val_str = f"{integer_part}.{fractional_part}"
    else:
        integer_part = "0"
        fractional_part = digits_only.zfill(num_decimals)
        val_str = f"{integer_part}.{fractional_part}"

    amount = Decimal(val_str)
    return -amount if is_negative else amount


def _parse_cfonb_date(raw_date: str) -> date | None:
    """Parse a CFONB date string formatted as JJMMAA (DDMMYY).

    Args:
        raw_date: 6-character date string (e.g. '150126').

    Returns:
        A date object, or None if invalid or blank.
    """
    clean = raw_date.strip()
    if len(clean) != 6 or not clean.isdigit():
        return None
    try:
        dt = datetime.strptime(clean, "%d%m%y").replace(tzinfo=timezone.utc)
        return dt.date()
    except ValueError:
        return None


@dataclass(frozen=True)
class CfonbSummary:
    """Financial and header summary for a parsed CFONB 120 statement."""

    account_id: str
    bank_code: str
    branch_code: str
    currency: str
    opening_balance: Decimal | None
    closing_balance: Decimal | None
    opening_date: date | None
    closing_date: date | None
    transaction_count: int
    total_credit: Decimal
    total_debit: Decimal


@dataclass
class _CfonbState:
    """Internal mutable parser accumulator state."""

    bank_code: str = ""
    branch_code: str = ""
    currency: str = "EUR"
    account_id: str = ""
    decimals: int = 2
    opening_balance: Decimal | None = None
    opening_date: date | None = None
    closing_balance: Decimal | None = None
    closing_date: date | None = None
    records: list[dict[str, Any]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        """Initialize list of parsed transaction dictionaries."""
        if self.records is None:
            self.records = []


def _handle_header_01(raw: str, state: _CfonbState) -> None:
    """Parse 01 header line and extract opening balance."""
    state.bank_code = raw[2:7].strip()
    state.branch_code = raw[7:12].strip()
    curr = raw[12:15].strip()
    if curr:
        state.currency = curr
    dec_str = raw[15:16].strip()
    if dec_str.isdigit():
        state.decimals = int(dec_str)
    state.account_id = raw[21:32].strip()
    state.opening_date = _parse_cfonb_date(raw[34:40])
    raw_amt = raw[90:103] if len(raw) >= 103 else ""
    sign_char = raw[103:104] if len(raw) >= 104 else ""
    state.opening_balance = _decode_cfonb_amount(
        raw_amt, sign_char, state.decimals
    )


def _handle_operation_04(raw: str, state: _CfonbState) -> dict[str, Any]:
    """Parse 04 movement line and extract operation fields."""
    bank = raw[2:7].strip() or state.bank_code
    branch = raw[7:12].strip() or state.branch_code
    curr = raw[12:15].strip() or state.currency
    acct = raw[21:32].strip() or state.account_id
    if not state.account_id:
        state.account_id = acct

    interbank_code = raw[32:34].strip()
    op_date = _parse_cfonb_date(raw[34:40])
    val_date = _parse_cfonb_date(raw[42:48]) or op_date
    label = raw[48:79].strip() if len(raw) >= 49 else ""
    ref = raw[81:88].strip() if len(raw) >= 82 else ""
    raw_amt = raw[90:103] if len(raw) >= 103 else ""
    sign_char = raw[103:104] if len(raw) >= 104 else ""
    amount = _decode_cfonb_amount(raw_amt, sign_char, state.decimals)
    info = raw[104:120].strip() if len(raw) >= 105 else ""

    return {
        "bank_code": bank,
        "branch_code": branch,
        "account_id": acct,
        "currency": curr,
        "interbank_code": interbank_code,
        "booking_date": op_date,
        "value_date": val_date,
        "description": label,
        "reference": ref,
        "amount": amount,
        "extra_info": info,
        "complementary_details": [],
    }


def _handle_detail_05(raw: str, current_tx: dict[str, Any] | None) -> None:
    """Parse 05 complementary detail line and append to active transaction."""
    detail = raw[44:114].strip() if len(raw) >= 45 else ""
    if current_tx is not None and detail:
        current_tx["complementary_details"].append(detail)
        current_tx["description"] = (
            f"{current_tx['description']} {detail}".strip()
        )


def _handle_closing_07(raw: str, state: _CfonbState) -> None:
    """Parse 07 closing balance line and extract final balance metrics."""
    state.closing_date = _parse_cfonb_date(raw[34:40])
    raw_amt = raw[90:103] if len(raw) >= 103 else ""
    sign_char = raw[103:104] if len(raw) >= 104 else ""
    state.closing_balance = _decode_cfonb_amount(
        raw_amt, sign_char, state.decimals
    )


def _parse_cfonb_stream(lines: Iterable[str]) -> _CfonbState:
    """Parse a stream of CFONB 120 lines into an accumulated state object.

    Args:
        lines: Stream of text lines.

    Returns:
        Accumulated _CfonbState instance.
    """
    state = _CfonbState()
    current_tx: dict[str, Any] | None = None

    for line in lines:
        raw = line.rstrip("\r\n")
        if len(raw) < 2:
            continue

        rec_code = raw[:2]
        if rec_code == "01":
            _handle_header_01(raw, state)
        elif rec_code == "04":
            if current_tx is not None:
                state.records.append(current_tx)
            current_tx = _handle_operation_04(raw, state)
        elif rec_code == "05":
            _handle_detail_05(raw, current_tx)
        elif rec_code == "07":
            if current_tx is not None:
                state.records.append(current_tx)
                current_tx = None
            _handle_closing_07(raw, state)

    if current_tx is not None:
        state.records.append(current_tx)

    return state


def load_cfonb(text_or_lines: str | Iterable[str]) -> list[Transaction]:
    """Parse CFONB 120 formatted text into a list of Transaction models.

    Args:
        text_or_lines: Raw CFONB string or iterable of lines.

    Returns:
        List of parsed Transaction domain models.
    """
    lines = (
        text_or_lines.splitlines()
        if isinstance(text_or_lines, str)
        else text_or_lines
    )
    state = _parse_cfonb_stream(lines)
    transactions: list[Transaction] = []

    for idx, rec in enumerate(state.records):
        tx = Transaction(
            account_id=str(rec["account_id"]),
            currency=str(rec["currency"]),
            amount=rec["amount"],
            booking_date=rec["booking_date"],
            value_date=rec["value_date"],
            description=str(rec["description"]),
            reference=str(rec["reference"]) if rec.get("reference") else None,
            category=(
                f"cfonb:{rec['interbank_code']}"
                if rec.get("interbank_code")
                else None
            ),
            source=SOURCE,
            source_index=idx,
        )
        transactions.append(tx)

    return transactions


def load_cfonb_file(path: str | os.PathLike[str]) -> list[Transaction]:
    """Read and parse a CFONB 120 statement file from disk.

    Args:
        path: Path to the CFONB file.

    Returns:
        List of parsed Transaction domain models.
    """
    content = Path(path).read_text(encoding="utf-8", errors="replace")
    return load_cfonb(content)


def summarize_cfonb(text_or_lines: str | Iterable[str]) -> CfonbSummary:
    """Generate a structured financial summary for a CFONB statement.

    Args:
        text_or_lines: Raw CFONB string or iterable of lines.

    Returns:
        A CfonbSummary dataclass containing balances, dates, and aggregates.
    """
    lines = (
        text_or_lines.splitlines()
        if isinstance(text_or_lines, str)
        else text_or_lines
    )
    state = _parse_cfonb_stream(lines)

    total_credit = Decimal("0.00")
    total_debit = Decimal("0.00")

    for rec in state.records:
        amt = rec["amount"]
        if amt > 0:
            total_credit += amt
        else:
            total_debit += abs(amt)

    return CfonbSummary(
        account_id=state.account_id,
        bank_code=state.bank_code,
        branch_code=state.branch_code,
        currency=state.currency,
        opening_balance=state.opening_balance,
        closing_balance=state.closing_balance,
        opening_date=state.opening_date,
        closing_date=state.closing_date,
        transaction_count=len(state.records),
        total_credit=total_credit,
        total_debit=total_debit,
    )


class CfonbStatementParser(BankStatementParser):
    """BankStatementParser plugin implementation for French CFONB 120 statements."""

    def __init__(self, file_name: str | Path, **kwargs: Any) -> None:
        """Initialize the CFONB statement parser.

        Args:
            file_name: Path to the CFONB 120 statement file.
            **kwargs: Extra options passed to the base parser.
        """
        super().__init__(file_name, **kwargs)
        self._summary_cache: CfonbSummary | None = None

    def parse(self) -> pd.DataFrame:
        """Parse the CFONB file into a pandas DataFrame.

        Returns:
            A pandas DataFrame containing standardized statement transactions.
        """
        txs = self.to_transactions()
        if not txs:
            return pd.DataFrame(
                columns=[
                    "date",
                    "description",
                    "amount",
                    "currency",
                    "account_id",
                    "reference",
                    "source",
                ]
            )

        records = [
            {
                "date": tx.booking_date.isoformat() if tx.booking_date else "",
                "description": tx.description,
                "amount": float(tx.amount),
                "currency": tx.currency,
                "account_id": tx.account_id,
                "reference": tx.reference,
                "source": tx.source,
            }
            for tx in txs
        ]
        return pd.DataFrame(records)

    def to_transactions(self) -> list[Transaction]:
        """Parse the CFONB file into a list of Transaction models.

        Returns:
            List of parsed Transaction instances.
        """
        return load_cfonb_file(self.file_name)

    def get_summary(self) -> dict[str, Any]:
        """Get summary metadata and balance metrics for the CFONB file.

        Returns:
            Dictionary with statement statistics.
        """
        if self._summary_cache is None:
            content = Path(self.file_name).read_text(
                encoding="utf-8", errors="replace"
            )
            self._summary_cache = summarize_cfonb(content)

        s = self._summary_cache
        return {
            "account_id": s.account_id,
            "bank_code": s.bank_code,
            "branch_code": s.branch_code,
            "currency": s.currency,
            "opening_balance": (
                float(s.opening_balance)
                if s.opening_balance is not None
                else None
            ),
            "closing_balance": (
                float(s.closing_balance)
                if s.closing_balance is not None
                else None
            ),
            "opening_date": (
                s.opening_date.isoformat() if s.opening_date else None
            ),
            "closing_date": (
                s.closing_date.isoformat() if s.closing_date else None
            ),
            "transaction_count": s.transaction_count,
            "total_credit": float(s.total_credit),
            "total_debit": float(s.total_debit),
        }
