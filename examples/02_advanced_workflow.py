# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Read a statement through the core's parser plugin and reconcile it.

Installing the package registers ``CfonbStatementParser`` in the
``bankstatementparser.loaders`` entry-point group. This writes the
sample statement from ``01_basic_usage.py`` to a file, reads it with the
plugin as a pandas DataFrame and a summary, and checks that the opening
balance plus the operations equals the closing balance.
"""

import importlib.util
import tempfile
from decimal import Decimal
from pathlib import Path

from bankstatementparser_loader_cfonb import CfonbStatementParser

_spec = importlib.util.spec_from_file_location(
    "basic", Path(__file__).with_name("01_basic_usage.py")
)
assert _spec and _spec.loader
basic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(basic)


def main() -> None:
    """Parse with the plugin and reconcile the balances."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "statement.cfonb"
        path.write_text(basic.SAMPLE + "\n", encoding="utf-8")

        parser = CfonbStatementParser(str(path))
        print(parser.parse().to_string(index=False))

        summary = parser.get_summary()
        net = sum((tx.amount for tx in parser.to_transactions()), Decimal(0))
        opening = summary["opening_balance"] or Decimal(0)
        closing = summary["closing_balance"] or Decimal(0)
        print(f"\n{opening} + {net} = {opening + net}; closing {closing}")
        if opening + net != closing:
            raise SystemExit("the statement does not reconcile")
        print("the statement reconciles")


if __name__ == "__main__":
    main()
