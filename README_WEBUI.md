# VAIS — Voynich Analysis Interactive Suite — Web UI

A small local web app for browsing, running, and customizing the 129 analysis
scripts in `scripts/`.

## Setup

Requirements: Python 3.10+ with `flask` and `numpy` (the analysis scripts
themselves need only numpy + stdlib).

```
pip install flask numpy
python webui/server.py          # serves http://127.0.0.1:5000
PORT=8080 python webui/server.py  # any other port
```

Run from the project root (`c:\projects\vais`). The server only
binds 127.0.0.1 — it is a local tool, not a deployment.

## What it does

- **Test list** (left sidebar): every analysis script with its one-line
  description from the inventory. Filter box narrows by name/description.
  Colored dots show the last run status (green ok / red error / yellow
  timeout / blue running).
- **Test detail**: description, file/lines, baseline runtime, dependency
  badges (`needs X` = run X first, it produces a result JSON this test
  reads), and a `network` badge for tests that fetch reference corpora from
  Project Gutenberg.
- **Parameters**: every module-level constant of the script (ints, floats,
  strings, bools, lists/sets) rendered as a form control, pre-filled with the
  code's real default. Changed fields highlight blue. *Reset to defaults*
  restores them. Values are validated server-side against the default's type.
- **Run**: executes the actual script (subprocess, project root as CWD).
  Parameter overrides are spliced into a temporary copy of the script as new
  literal values for the matching constants — the analysis logic that runs is
  always the script's own code. Stdout streams into the output pane when the
  run finishes; stderr and tracebacks are shown, never swallowed. The header
  shows runtime and which `results/` files the run (re)wrote.
- **Run all (filtered)**: runs every listed test sequentially with per-test
  status dots; filter first to run a subset.
- **Presets**: save the current parameter set under a name, load it, delete
  it. Stored in `webui/presets.json` (survives restarts). Every test always
  has the built-in read-only `defaults` preset.
- **Timeout**: per-run override in seconds; default is `3 × baseline runtime
  + 60s` (clamped to 120–3600).

## Notes and caveats

- Long tests: baseline runtimes are listed per test (see `INVENTORY.md`);
  the slowest (`phase100_decipherment`, `phase101_currier_ab_dichotomy`,
  `phase62_word_anatomy`, `phase72_naibbe_calibration`) run for minutes.
- Dependency-ordered tests: a test with a `needs X` badge reads a JSON that
  script X writes. Run X first (or use its committed output if present).
- `download_folios.py` / `download_latin.py` are data downloaders, not
  analyses, and are intentionally absent from the UI.
- Runs are sequential within a job; starting several jobs concurrently is
  possible but not recommended — many scripts write to the shared `results/`
  directory.

## Layout

```
webui/
  server.py     Flask app + job store + preset endpoints
  registry.py   static test catalog (descriptions, params, dependencies)
  runner.py     subprocess runner + AST parameter-override splicing
  static/index.html  single-page frontend (vanilla JS, no build step)
  presets.json  saved presets (created on first save)
```

## Golden-diff integration

Every default-parameter run is automatically compared against the committed
golden reference (`golden/<test>.stdout.txt`, captured with
`PYTHONHASHSEED=0`; UI runs are executed under the same hash seed so the
comparison is meaningful). The output header shows a badge:

- **`= golden`** — stdout byte-identical to the reference,
- **`≠ golden (N lines)`** — click the badge to view the unified diff,
- runs with custom parameters (or errors/timeouts) are marked not comparable.

Refresh the reference after intentional changes with
`python tools/run_baseline.py --outdir golden --hashseed 0 [--only names]`.

## Offline reference corpora

`data/gutenberg_cache/` (~16 MB, committed) holds every Project Gutenberg
text the network tests use; `common.fetch_gutenberg` reads the cache first,
so phases 58-65 and 72-73 run fully offline. Re-populate with
`python tools/prefetch_gutenberg.py`.

## Result-file convention

All inter-script result JSONs live in `results/` via `common.result_path()`;
producers and consumers can no longer drift apart (the pre-refactor root-level
snapshots are preserved in `attic/root_result_snapshots/`).

Known benign case: `phase72_naibbe_calibration` and `phase73_abbreviation_model`
print wall-clock "Elapsed:" lines, so their golden badge will report a few
differing lines on every run — the click-through diff shows only the timings.
