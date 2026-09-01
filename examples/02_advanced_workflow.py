# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Advanced batch processing example for bankstatementparser-loader-cfonb."""

from decimal import Decimal

from bankstatementparser_loader_cfonb import load_cfonb

SAMPLE = """011005719000EUR2     00012345678  010126                                                  0000001500000C
041005719000EUR2     0001234567802050126  050126VIREMENT RECU CLIENT ACME        REF1234  0000000250000+
051005719000EUR2     0001234567802050126FACTURE INV-2026-999
041005719000EUR2     0001234567803150126  150126PRELEVEMENT FOURNISSEUR          REF5678  0000000045002-
071005719000EUR2     00012345678  310126                                                  0000001704998C                """


def main() -> None:
    print("Batch processing 100 iterations...")
    total_volume = Decimal("0")
    for _ in range(100):
        txns = load_cfonb(SAMPLE)
        for t in txns:
            total_volume += abs(t.amount)
    print(
        f"Processed 100 batch statements. Total absolute volume: {total_volume}"
    )


if __name__ == "__main__":
    main()
