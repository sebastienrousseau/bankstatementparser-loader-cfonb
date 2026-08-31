# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""CFONB 120 / AFB120 French Banking Statement Loader.

Parses CFONB 120 fixed-width French bank statement files into
``bankstatementparser.transaction_models.Transaction`` objects.
"""

from __future__ import annotations

from .loader import (
    CfonbStatementParser,
    CfonbSummary,
    load_cfonb,
    load_cfonb_file,
    summarize_cfonb,
)

__version__ = "0.0.1"
__all__ = [
    "CfonbStatementParser",
    "CfonbSummary",
    "__version__",
    "load_cfonb",
    "load_cfonb_file",
    "summarize_cfonb",
]
