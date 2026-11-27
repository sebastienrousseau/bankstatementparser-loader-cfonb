# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Load a CFONB 120 statement and summarise it.

The sample has the shape of ``tests/fixtures/statement.cfonb``: an
``01`` opening balance, a credit transfer with a ``05`` detail, a
direct debit and an ``07`` closing balance. Each amount's last
character carries its units digit and sign: ``{`` is +0, ``K`` is -2
and ``H`` is +8.
"""

from bankstatementparser_loader_cfonb import load_cfonb, summarize_cfonb

# Columns 1-34: code, bank, internal code, branch, currency, decimals,
# a blank, account, interbank operation code.
HEAD = "{code}10057    19000EUR2 00012345678{interbank}"


def balance(code: str, day: str, amount: str) -> str:
    """An 01 or 07 balance record."""
    return f"{HEAD.format(code=code, interbank='  ')}{day}{'':50}{amount:>14}{'':16}"


def operation(code: str, day: str, label: str, ref: str, amount: str) -> str:
    """An 04 operation record."""
    head = HEAD.format(code="04", interbank=code)
    return f"{head}{day}  {day}{label:<32} {ref:<7}  {amount:>14}{'':16}"


def complement(text: str) -> str:
    """A 05 complementary record."""
    head = HEAD.format(code="05", interbank="  ")
    return f"{head}050126     LIB{text:<70}  "


SAMPLE = "\n".join(
    [
        balance("01", "010126", "0000000150000{"),
        operation(
            "02",
            "050126",
            "VIREMENT RECU CLIENT ACME",
            "REF1234",
            "0000000025000{",
        ),
        complement("FACTURE INV-2026-999"),
        operation(
            "03",
            "100126",
            "PRELEVEMENT EDF ELECTRICITE",
            "REF5678",
            "0000000004500K",
        ),
        balance("07", "310126", "0000000170499H"),
    ]
)


def main() -> None:
    """Print each transaction, then the statement's summary."""
    for tx in load_cfonb(SAMPLE):
        print(
            f"{tx.booking_date}  {tx.amount:>9} {tx.currency}  "
            f"{tx.category}  {tx.reference}  {tx.description}"
        )

    s = summarize_cfonb(SAMPLE)
    print(
        f"\nAccount {s.account_id} (bank {s.bank_code}, branch "
        f"{s.branch_code}): {s.opening_balance} on {s.opening_date} "
        f"to {s.closing_balance} on {s.closing_date}, "
        f"{s.transaction_count} operations"
    )


if __name__ == "__main__":
    main()
