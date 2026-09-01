# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Documentation accuracy verification tests for bankstatementparser-loader-cfonb."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from bankstatementparser_loader_cfonb import (
    CfonbStatementParser,
    summarize_cfonb,
)
from tests.test_loader import _sample_cfonb_120_text


def test_readme_code_examples(tmp_path: Path) -> None:
    """Assert that all code snippets in README execute accurately."""
    sample = _sample_cfonb_120_text()
    stmt_file = tmp_path / "statement.cfonb"
    stmt_file.write_text(sample, encoding="utf-8")

    parser = CfonbStatementParser(stmt_file)
    txns = parser.to_transactions()
    assert len(txns) == 2
    assert txns[0].amount == Decimal("2500.00")

    summary = summarize_cfonb(sample)
    assert summary.account_id == "00012345678"
    assert summary.opening_balance == Decimal("15000.00")
    assert summary.closing_balance == Decimal("17049.98")
