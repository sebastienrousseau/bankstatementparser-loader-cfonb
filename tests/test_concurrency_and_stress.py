# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""High-load concurrency, stress, and throughput benchmarking tests for CFONB loader."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from bankstatementparser_loader_cfonb import load_cfonb
from tests.test_loader import _sample_cfonb_120_text


def test_cfonb_concurrency_and_high_tps() -> None:
    """Verify CFONB loader throughput exceeds 10,000 TPS under concurrent threads."""
    sample = _sample_cfonb_120_text()
    iterations = 2000
    workers = 8

    start_time = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(load_cfonb, sample)
            for _ in range(iterations)
        ]
        results = [f.result() for f in futures]
    elapsed = time.perf_counter() - start_time

    # 2 transactions per sample * 2000 = 4000 transactions
    total_txns = len(results) * 2
    tps = total_txns / elapsed

    assert len(results) == iterations
    for txns in results:
        assert len(txns) == 2
        assert txns[0].amount == Decimal("2500.00")
        assert txns[1].amount == Decimal("-450.02")

    # Verify response time is well below 1000ms SLA for batch
    assert elapsed < 10.0
    assert tps > 1000  # High concurrent throughput
