#!/usr/bin/env python3
"""Turn a LibreLane run into a job summary a first-year can read.

This is the course's answer to "no grades, but the student must know whether they
succeeded". It runs on success AND on failure, because a student whose flow died
needs more help than one whose flow passed.

Written to $GITHUB_STEP_SUMMARY, so it renders on the Actions page with nothing to
download.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def latest_run(design_dir: Path) -> Path | None:
    runs = sorted(design_dir.glob("runs/*"))
    return runs[-1] if runs else None


def tool_versions() -> dict[str, str]:
    """The versions that actually produced this chip.

    Surfaced deliberately: LibreLane pins itself but NOT the tools it drives, so a
    CI chip and a workbench chip differ. Showing both makes that visible instead of
    mysterious.
    """
    probes = {
        "LibreLane": ["librelane", "--version"],
        "Yosys": ["yosys", "-V"],
        "OpenROAD": ["openroad", "-version"],
        "Magic": ["magic", "--version"],
    }
    out = {}
    for name, cmd in probes.items():
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            line = (r.stdout or r.stderr).strip().splitlines()
            out[name] = line[0].strip() if line else "?"
        except Exception:
            out[name] = "not found"
    return out


def fmt(v, unit="", nd=2):
    try:
        return f"{float(v):,.{nd}f}{unit}"
    except (TypeError, ValueError):
        return str(v)


def main() -> int:
    design_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    run = latest_run(design_dir)

    print("## Your chip\n")

    if run is None:
        print("The flow did not get far enough to produce a run directory.\n")
        print("That usually means the config was rejected before any tool started. "
              "Check the **Harden** step's log above — the first error is the real one; "
              "everything after it is fallout.\n")
        return 0

    metrics_path = run / "final" / "metrics.json"
    if not metrics_path.is_file():
        print(f"The flow started (`{run.name}`) but did not finish, so there is no "
              "final chip to report.\n")
        print("Open the **Harden** log and search for the first line beginning "
              "`ERROR`. Two failures are common early on:\n")
        print("- `PDN-0185: Insufficient width` — your design is small and the die came "
              "out too tight for power straps. Add `\"FP_CORE_UTIL\": 30` to `config.json`.")
        print("- `Unable to find a valid ...` — a path in `VERILOG_FILES` does not match "
              "any file.\n")
        _print_versions()
        return 0

    m = json.loads(metrics_path.read_text())

    cells = m.get("design__instance__count")
    die = m.get("design__die__area")
    core = m.get("design__core__area")
    ws = m.get("timing__setup__ws")
    seq = m.get("design__instance__area__class:sequential_cell")
    inst_area = m.get("design__instance__area")

    print("| | |")
    print("|---|---|")
    print(f"| **Standard cells placed** | {fmt(cells, nd=0)} |")
    print(f"| **Die area** | {fmt(die, ' µm²')} |")
    print(f"| **Core area** | {fmt(core, ' µm²')} |")
    if seq and inst_area:
        try:
            pct = 100.0 * float(seq) / float(inst_area)
            print(f"| **Flip-flops, as a share of cell area** | {pct:.1f} % |")
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    if ws is not None:
        verdict = "met" if float(ws) >= 0 else "**VIOLATED**"
        print(f"| **Worst setup slack** | {fmt(ws, ' ns', 3)} — timing {verdict} |")
    print()

    # --- the checks that decide whether this is a real chip -----------------
    checks = [
        ("DRC (does it obey the manufacturing rules?)", "magic__drc_error__count"),
        ("LVS (does the layout match the netlist?)", "design__lvs_error__count"),
        ("Antenna (will it survive being manufactured?)", "route__antenna_violation__count"),
    ]
    print("### Sign-off\n")
    print("| Check | Violations | |")
    print("|---|---|---|")
    all_clean = True
    for label, key in checks:
        v = m.get(key)
        if v is None:
            print(f"| {label} | — | not run |")
            continue
        clean = float(v) == 0
        all_clean &= clean
        print(f"| {label} | {fmt(v, nd=0)} | {'clean' if clean else 'needs work'} |")
    print()

    if all_clean:
        print("Every sign-off check passed. **This is a manufacturable chip.**\n")
    else:
        print("At least one sign-off check found violations. The GDS exists, but it is "
              "not something a foundry would accept yet.\n")

    gds = list((run / "final" / "gds").glob("*.gds"))
    render = list((run / "final" / "render").glob("*.png"))
    if gds or render:
        print("### Download it\n")
        print("The **chip-…** artifact at the top of this page contains:\n")
        if gds:
            size = gds[0].stat().st_size / 1024
            print(f"- `{gds[0].name}` — your layout, {size:,.0f} KB. This is the file a "
                  "foundry would be sent.")
        if render:
            print(f"- `{render[0].name}` — a picture of it. **Open this one.**")
        print()

    _print_versions()
    return 0


def _print_versions() -> None:
    v = tool_versions()
    print("<details><summary>Which tools built this</summary>\n")
    print("| Tool | Version |")
    print("|---|---|")
    for k, val in v.items():
        print(f"| {k} | `{val}` |")
    print()
    print("LibreLane pins *itself*, but not the tools it drives. The workbench image ships "
          "different builds of Yosys, OpenROAD and Magic than this runner does, so your "
          "numbers here will be close to — but not identical to — the ones you get locally. "
          "Expect a percent or two. That is why a real tapeout pins every tool by hash.\n")
    print("</details>")


if __name__ == "__main__":
    raise SystemExit(main())
