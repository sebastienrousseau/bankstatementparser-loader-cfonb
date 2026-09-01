# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Basic usage example for bankstatementparser-loader-cfonb."""

from bankstatementparser_loader_cfonb import load_cfonb, summarize_cfonb

SAMPLE = """011005719000EUR2     00012345678  010126                                                  0000001500000C
041005719000EUR2     0001234567802050126  050126VIREMENT RECU CLIENT ACME        REF1234  0000000250000+
051005719000EUR2     0001234567802050126FACTURE INV-2026-999
041005719000EUR2     0001234567803150126  150126PRELEVEMENT FOURNISSEUR          REF5678  0000000045002-
071005719000EUR2     00012345678  310126                                                  0000001704998C                """


def main() -> None:
    print("Loading statement...")
    txns = load_cfonb(SAMPLE)
    for tx in txns:
        print(
            f"  Transaction: {tx.booking_date} | {tx.amount} {tx.currency} | {tx.description}"
        )

    summary = summarize_cfonb(SAMPLE)
    print(f"Summary generated successfully: {summary}")


if __name__ == "__main__":
    main()
