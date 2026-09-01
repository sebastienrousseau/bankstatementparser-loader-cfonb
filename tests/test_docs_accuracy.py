# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Documentation accuracy verification tests for bankstatementparser-loader-cfonb."""

from decimal import Decimal
from pathlib import Path

from bankstatementparser_loader_cfonb import (
    CfonbStatementParser,
    summarize_cfonb,
)


def test_readme_code_examples(tmp_path: Path) -> None:
    """Assert that all code snippets in README execute accurately."""
    sample = """01300020000100001234567EUR2020260101                    0000000010000{
04300020000100001234567EUR2020260115000000000002500A                    REF-1001   Virement Client
05300020000100001234567EUR2020260115FACT-2026-9999 Facture Janvier 2026
07300020000100001234567EUR2020260131                    0000000012500{"""
    stmt_file = tmp_path / "statement.cfonb"
    stmt_file.write_text(sample, encoding="utf-8")

    parser = CfonbStatementParser(stmt_file)
    txns = parser.to_transactions()
    assert len(txns) == 1
    assert txns[0].amount == Decimal("250.00")

    summary = summarize_cfonb(sample)
    assert summary.account_id == "300020000100001234567"
    assert summary.opening_balance == Decimal("1000.00")
    assert summary.closing_balance == Decimal("1250.00")
