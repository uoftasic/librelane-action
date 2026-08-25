#!/usr/bin/env python3
"""Refuse to run a config that does not pin its PDK.

Without an explicit "PDK", LibreLane inherits whatever the environment says — in the
workbench that is `ihp-sg13g2`. The flow then succeeds, and hands back a chip in the
wrong technology with no error anywhere. That failure is invisible, so we make it
loud here instead.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED_PDK = "sky130A"
EXPECTED_SCL = "sky130_fd_sc_hd"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_config.py <path to config.json>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"::error::No config at {path}")
        return 1

    try:
        cfg = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"::error file={path}::config.json is not valid JSON — {e}")
        return 1

    problems = []
    if cfg.get("PDK") != EXPECTED_PDK:
        problems.append(
            f'"PDK" is {cfg.get("PDK")!r}, expected "{EXPECTED_PDK}". '
            "Without this the flow silently targets whatever PDK the environment "
            "defaults to, and you get a chip in the wrong technology with no error."
        )
    if cfg.get("STD_CELL_LIBRARY") != EXPECTED_SCL:
        problems.append(
            f'"STD_CELL_LIBRARY" is {cfg.get("STD_CELL_LIBRARY")!r}, '
            f'expected "{EXPECTED_SCL}".'
        )
    if not cfg.get("DESIGN_NAME"):
        problems.append('"DESIGN_NAME" is missing.')
    if not cfg.get("VERILOG_FILES"):
        problems.append('"VERILOG_FILES" is missing.')

    if problems:
        for p in problems:
            print(f"::error file={path}::{p}")
        return 1

    print(f"config OK — {cfg['DESIGN_NAME']} on {EXPECTED_PDK}/{EXPECTED_SCL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
