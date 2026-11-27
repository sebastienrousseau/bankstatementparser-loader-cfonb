# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Concurrent loads of one statement return the same, correct result.

The loader keeps no shared state between calls, so 2,000 loads on eight
threads must each return the two operations of the sample. Speed is not
asserted here: wall-clock is not comparable between machines, and
benches/bench_load_cfonb.py measures it without a threshold.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from bankstatementparser_loader_cfonb import load_cfonb
from tests.test_loader import _sample_cfonb_120_text


def test_cfonb_concurrent_loads_agree() -> None:
    """Every one of 2,000 concurrent loads reads the same two operations."""
    sample = _sample_cfonb_120_text()
    iterations = 2000

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(load_cfonb, sample) for _ in range(iterations)
        ]
        results = [f.result() for f in futures]

    assert len(results) == iterations
    for txns in results:
        assert [t.amount for t in txns] == [
            Decimal("2500.00"),
            Decimal("-450.02"),
        ]
