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
from bankstatementparser.record_types import SummaryRecord
from bankstatementparser.transaction_models import Transaction

SOURCE = "cfonb"

# The last character of a CFONB 120 amount carries its units digit and
# its sign (a signed "overpunch"): "{" and "A"-"I" are +0 to +9, "}" and
# "J"-"R" are -0 to -9.
_OVERPUNCH: dict[str, tuple[str, bool]] = {
    **{ch: (str(i), False) for i, ch in enumerate("{ABCDEFGHI")},
    **{ch: (str(i), True) for i, ch in enumerate("}JKLMNOPQR")},
}


def _decode_cfonb_amount(raw_amount: str, num_decimals: int = 2) -> Decimal:
    """Decode a CFONB 120 amount zone (columns 91-104).

    The zone is 13 digits and a final character that is the units digit
    and the sign (see ``_OVERPUNCH``); a plain final digit is read as a
    positive units digit. Characters other than ASCII digits are skipped.

    Args:
        raw_amount: The amount zone, e.g. ``'0000000001904}'``.
        num_decimals: The number of decimals (header column 20).

    Returns:
        The signed amount, ``num_decimals`` places after the point.
    """
    zone = raw_amount.strip()
    negative = False
    if zone and zone[-1] in _OVERPUNCH:
        unit, negative = _OVERPUNCH[zone[-1]]
        zone = zone[:-1] + unit
    digits = "".join(ch for ch in zone if ch in "0123456789")
    amount = Decimal(int(digits or "0")).scaleb(-num_decimals)
    return -amount if negative and amount else amount


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


class CfonbSummaryRecord(SummaryRecord, total=False):
    """``get_summary()`` result: the core summary keys plus CFONB header fields.

    A ``SummaryRecord`` subtype, so the override matches the base parser's
    contract. The balances are ``Decimal``, as ``SummaryRecord`` declares,
    decoded from the record text; the credit and debit totals stay ``float``.
    """

    bank_code: str
    branch_code: str
    opening_date: str | None
    closing_date: str | None
    total_credit: float
    total_debit: float


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
    state.branch_code = raw[11:16].strip()
    curr = raw[16:19].strip()
    if curr:
        state.currency = curr
    dec_str = raw[19:20].strip()
    if dec_str.isdigit():
        state.decimals = int(dec_str)
    state.account_id = raw[21:32].strip()
    state.opening_date = _parse_cfonb_date(raw[34:40])
    state.opening_balance = _decode_cfonb_amount(raw[90:104], state.decimals)


def _handle_operation_04(raw: str, state: _CfonbState) -> dict[str, Any]:
    """Parse 04 movement line and extract operation fields."""
    bank = raw[2:7].strip() or state.bank_code
    branch = raw[11:16].strip() or state.branch_code
    curr = raw[16:19].strip() or state.currency
    acct = raw[21:32].strip() or state.account_id
    if not state.account_id:
        state.account_id = acct

    interbank_code = raw[32:34].strip()
    op_date = _parse_cfonb_date(raw[34:40])
    val_date = _parse_cfonb_date(raw[42:48]) or op_date
    label = raw[48:79].strip()
    ref = raw[81:88].strip()
    amount = _decode_cfonb_amount(raw[90:104], state.decimals)
    info = raw[104:120].strip()

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
    detail = raw[48:118].strip()
    if current_tx is not None and detail:
        current_tx["complementary_details"].append(detail)
        current_tx["description"] = (
            f"{current_tx['description']} {detail}".strip()
        )


def _handle_closing_07(raw: str, state: _CfonbState) -> None:
    """Parse 07 closing balance line and extract final balance metrics."""
    state.closing_date = _parse_cfonb_date(raw[34:40])
    state.closing_balance = _decode_cfonb_amount(raw[90:104], state.decimals)


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

    def get_summary(self) -> CfonbSummaryRecord:
        """Get summary metadata and balance metrics for the CFONB file.

        Returns:
            Statement statistics. ``opening_balance`` and ``closing_balance``
            are ``Decimal`` (or ``None`` when the file has no balance record),
            as ``SummaryRecord`` declares.
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
            "opening_balance": s.opening_balance,
            "closing_balance": s.closing_balance,
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
