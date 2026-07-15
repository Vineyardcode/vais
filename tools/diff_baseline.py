#!/usr/bin/env python3
"""Compare a rerun output directory against baseline/.

Usage: python tools/diff_baseline.py [rerun_dir] [baseline_dir]

Classifies each script's stdout as IDENTICAL / DIFFERS / status-mismatch and
prints a compact diff summary for the differing ones.
"""
import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    rerun = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "rerun"
    base = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "baseline"
    bmeta = json.loads((base / "_meta.json").read_text(encoding="utf-8"))
    rmeta = json.loads((rerun / "_meta.json").read_text(encoding="utf-8"))

    identical, differs, status_mismatch, missing = [], [], [], []
    for stem, bm in sorted(bmeta.items()):
        if bm.get("status") == "skipped":
            continue
        rm = rmeta.get(stem)
        if rm is None:
            missing.append(stem)
            continue
        if rm.get("status") != bm.get("status"):
            status_mismatch.append((stem, bm.get("status"), rm.get("status")))
            continue
        bf = base / f"{stem}.stdout.txt"
        rf = rerun / f"{stem}.stdout.txt"
        btxt = bf.read_text(encoding="utf-8", errors="replace") if bf.exists() else ""
        rtxt = rf.read_text(encoding="utf-8", errors="replace") if rf.exists() else ""
        if btxt == rtxt:
            identical.append(stem)
        else:
            bl, rl = btxt.splitlines(), rtxt.splitlines()
            changed = sum(1 for d in difflib.unified_diff(bl, rl, n=0, lineterm="")
                          if d.startswith(("+", "-")) and not d.startswith(("+++", "---")))
            differs.append((stem, len(bl), len(rl), changed))

    print(f"IDENTICAL: {len(identical)}")
    print(f"DIFFERS:   {len(differs)}")
    for stem, nb, nr, ch in differs:
        print(f"  {stem}: {nb} -> {nr} lines, ~{ch} changed lines")
    print(f"STATUS MISMATCH: {len(status_mismatch)}")
    for stem, b, r in status_mismatch:
        print(f"  {stem}: {b} -> {r}")
    if missing:
        print(f"MISSING FROM RERUN: {missing}")


if __name__ == "__main__":
    main()
