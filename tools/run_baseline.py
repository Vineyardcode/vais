#!/usr/bin/env python3
"""Baseline runner: executes every analysis script once and captures output.

Golden reference for the refactor. For each scripts/*.py:
  baseline/<stem>.stdout.txt   captured stdout
  baseline/<stem>.stderr.txt   captured stderr (only if non-empty)
  baseline/_meta.json          exit codes, durations, results/ files touched

Runs with CWD = project root (required by the CWD-relative scripts).
Skips pure downloader scripts. Progressive meta writes so a crash loses nothing.

Usage: python tools/run_baseline.py [--only name1,name2] [--timeout SECS]
                                    [--outdir DIR] [--hashseed N] [--scriptdir DIR]
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
BASELINE = ROOT / "baseline"
RESULTS = ROOT / "results"

SKIP = {
    "download_folios.py": "pure downloader (network, ~1GB)",
    "download_latin.py": "pure downloader (network)",
}

DEFAULT_TIMEOUT = 900  # generous; slow tests get recorded as timeouts


def results_snapshot():
    if not RESULTS.exists():
        return {}
    return {p.name: p.stat().st_mtime_ns for p in RESULTS.iterdir() if p.is_file()}


def main():
    global BASELINE, SCRIPTS
    only = None
    timeout = DEFAULT_TIMEOUT
    hashseed = None
    args = sys.argv[1:]
    while args:
        a = args.pop(0)
        if a == "--only":
            only = set(args.pop(0).split(","))
        elif a == "--timeout":
            timeout = int(args.pop(0))
        elif a == "--outdir":
            BASELINE = Path(args.pop(0))
        elif a == "--hashseed":
            hashseed = args.pop(0)
        elif a == "--scriptdir":
            SCRIPTS = Path(args.pop(0))

    BASELINE.mkdir(exist_ok=True)
    meta_path = BASELINE / "_meta.json"
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    scripts = sorted(SCRIPTS.glob("*.py"))
    for i, sp in enumerate(scripts, 1):
        name = sp.name
        stem = sp.stem
        if only and stem not in only and name not in only:
            continue
        if name in SKIP:
            meta[stem] = {"status": "skipped", "reason": SKIP[name]}
            print(f"[{i}/{len(scripts)}] SKIP {name}: {SKIP[name]}", flush=True)
            continue
        if not only and stem in meta and meta[stem].get("status") not in (None, "error"):
            print(f"[{i}/{len(scripts)}] already done {name}", flush=True)
            continue

        print(f"[{i}/{len(scripts)}] running {name} ...", flush=True)
        before = results_snapshot()
        t0 = time.time()
        try:
            env = dict(os.environ)
            if hashseed is not None:
                env["PYTHONHASHSEED"] = hashseed
            proc = subprocess.run(
                [sys.executable, str(sp)],
                cwd=str(ROOT),
                capture_output=True,
                timeout=timeout,
                env=env,
            )
            dur = time.time() - t0
            stdout = proc.stdout.decode("utf-8", errors="replace")
            stderr = proc.stderr.decode("utf-8", errors="replace")
            status = "ok" if proc.returncode == 0 else "error"
            rc = proc.returncode
        except subprocess.TimeoutExpired as e:
            dur = time.time() - t0
            stdout = (e.stdout or b"").decode("utf-8", errors="replace")
            stderr = (e.stderr or b"").decode("utf-8", errors="replace")
            status = "timeout"
            rc = None
        after = results_snapshot()
        touched = sorted(
            k for k in after
            if k not in before or after[k] != before[k]
        )

        # newline='' prevents \r\n in the captured stream from being
        # re-translated to \r\r\n on disk (Windows)
        with open(BASELINE / f"{stem}.stdout.txt", "w", encoding="utf-8",
                  newline="") as fh:
            fh.write(stdout)
        errfile = BASELINE / f"{stem}.stderr.txt"
        if stderr.strip():
            with open(errfile, "w", encoding="utf-8", newline="") as fh:
                fh.write(stderr)
        elif errfile.exists():
            errfile.unlink()

        meta[stem] = {
            "status": status,
            "returncode": rc,
            "duration_s": round(dur, 2),
            "stdout_bytes": len(stdout),
            "results_files_touched": touched,
        }
        tmp_meta = meta_path.with_suffix(".json.tmp")
        tmp_meta.write_text(json.dumps(meta, indent=1), encoding="utf-8")
        tmp_meta.replace(meta_path)
        print(f"    -> {status} rc={rc} {dur:.1f}s, wrote {len(touched)} results files",
              flush=True)

    # Summary
    counts = {}
    for v in meta.values():
        counts[v["status"]] = counts.get(v["status"], 0) + 1
    print("\nSummary:", counts, flush=True)


if __name__ == "__main__":
    main()
