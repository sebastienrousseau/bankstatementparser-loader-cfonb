# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Documentation accuracy verification tests for bankstatementparser-loader-cfonb."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from bankstatementparser_loader_cfonb import (
    CfonbStatementParser,
    load_cfonb,
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


ROOT = Path(__file__).resolve().parent.parent
_ROW = re.compile(
    r"^\|\s*`(\d+)(?:-(\d+))?`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.M
)
_BASE = _sample_cfonb_120_text().split("\n")
_INDEX = {"01": 0, "04": 1, "05": 2, "07": 4}


def _statement(code: str, start: int, end: int, marker: str) -> str:
    """The sample with ``marker`` at ``start``-``end`` of record ``code``."""
    lines = list(_BASE)
    line = lines[_INDEX[code]].ljust(120)
    lines[_INDEX[code]] = line[: start - 1] + marker + line[end:]
    return "\n".join(lines)


def _first(text: str) -> Any:
    """The first transaction of ``text``."""
    return load_cfonb(text)[0]


# field: (record carrying it, marker, check(text, marker))
_CHECKS: dict[str, tuple[str, str, Callable[[str, str], bool]]] = {
    "bank code": (
        "01",
        "98765",
        lambda t, m: summarize_cfonb(t).bank_code == m,
    ),
    "branch code": (
        "01",
        "54321",
        lambda t, m: summarize_cfonb(t).branch_code == m,
    ),
    "currency": ("04", "JPY", lambda t, m: _first(t).currency == m),
    "number of decimals": (
        "01",
        "3",
        lambda t, m: _first(t).amount == Decimal("250.000"),
    ),
    "account number": (
        "04",
        "99988877766",
        lambda t, m: _first(t).account_id == m,
    ),
    "interbank operation code": (
        "04",
        "B1",
        lambda t, m: _first(t).category == f"cfonb:{m}",
    ),
    "date": (
        "04",
        "311227",
        lambda t, m: _first(t).booking_date == date(2027, 12, 31),
    ),
    "value date": (
        "04",
        "301127",
        lambda t, m: _first(t).value_date == date(2027, 11, 30),
    ),
    "label": (
        "04",
        "QWERTYUIOPASDFGHJKLZXCVBNMQWERT",
        lambda t, m: (_first(t).description or "").startswith(m),
    ),
    "entry number": ("04", "QWERTYU", lambda t, m: _first(t).reference == m),
    "amount": (
        "04",
        "0000000001904}",
        lambda t, m: _first(t).amount == Decimal("-190.40"),
    ),
    "complementary information": (
        "05",
        "Q" * 70,
        lambda t, m: (_first(t).description or "").endswith(m),
    ),
}
_SKIPPED = {"internal operation code": "04"}


def test_readme_layout_table_matches_the_loader() -> None:
    """Each documented column range carries the field it is named for."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = _ROW.findall(text)
    assert rows, "README.md has no record layout table"
    for a, b, name, _records in rows:
        start, end, field = int(a), int(b or a), name.strip().lower()
        if field in _SKIPPED:
            marker = "Z" * (end - start + 1)
            changed = _statement(_SKIPPED[field], start, end, marker)
            assert load_cfonb(changed) == load_cfonb("\n".join(_BASE))
            continue
        assert field in _CHECKS, f"no check for {field!r}"
        code, marker, check = _CHECKS[field]
        assert len(marker) == end - start + 1, field
        assert check(_statement(code, start, end, marker), marker), (
            f"{field!r} is not at columns {start}-{end}"
        )


def test_readme_quick_start_prints_what_it_says(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The in-memory Quick Start runs and prints its ``# `` comments."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", readme, re.S)
    (block,) = [b for b in blocks if "payload" in b]
    expected = [
        line[2:] for line in block.splitlines() if line.startswith("# ")
    ]
    exec(compile(block, "README.md", "exec"), {})
    assert capsys.readouterr().out.splitlines() == expected
