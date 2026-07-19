# VAIS — Voynich Analysis Interactive Suite

A self-contained, reproducible laboratory for statistical analysis of the
**Voynich manuscript** (Beinecke MS 408): 144 runnable tests covering
morphology, entropy, cipher hypotheses, hoax models, and codicology, plus a
local web UI that lets you run any test with your own parameters — no code
changes required.

The suite is built for **people who want to test their own theories**
against the manuscript with real statistical instruments, calibrated
controls, and honest reporting — instead of eyeballing a transcription.

---

## What it does

- **144 tests**, each an independent script in `scripts/` with a clear name
  and a docstring stating exactly what it tests. The full catalog is in
  [INVENTORY.md](INVENTORY.md). Highlights:
  - *Morphology & grammar*: slot grammar, prefix/suffix paradigms, word
    classes, parser-free validations of all of the above.
  - *Information theory*: character/word entropy stacks, mutual
    information, positional predictability, Zipf/Heaps profiles.
  - *Hypothesis tests*: natural language vs cipher (`language_vs_cipher`),
    verbose ciphers (`naibbe_cipher_calibration`, `positional_verbose_cipher`),
    abjad (`abjad_hypothesis`), syllabary (`syllabary_hypothesis`),
    reading direction (`rtl_direction_test`), published claims
    (`bax_decipherment_test`, `cappelli_abbreviation_retest`).
  - *Hoax models*: Rugg-style grille tables and Timm-style self-citation,
    implemented as calibrated generators and scored against the manuscript
    (`forgery_tournament`).
  - *Research instruments*: a 17-feature statistical fingerprint, a
    deterministic control-corpus foundry (`controls_foundry`), an
    alphabet-space search (`alphabet_space_search`), and a
    segmentation test (`space_free_segmentation`). Their findings and
    methodology are documented in [RESEARCH.md](RESEARCH.md).
- **A web UI** to browse, run, and customize all of it (see below).
- **Reproducibility infrastructure**: pinned hash seeds, committed golden
  reference outputs for every test, hand-verified sanity checks for the
  shared math (`sanity_checks/`), and a control battery of 9 synthetic
  corpora (genuine Latin/Italian, period-plausible ciphers, shuffles,
  hoax generators) in `data/controls/`.

### What it deliberately does NOT do

Nothing here "decodes" the manuscript, and the suite is engineered to make
false decodes hard: methods run on positive and negative control corpora
before the real text, kill criteria are pre-registered in docstrings, and
classifiers always have a "none of the above" arm. If you can get a theory
past these instruments, it is interesting. The methodology (and a catalog
of the failure modes of a century of prior attempts) is in
[RESEARCH.md](RESEARCH.md).

---

## Quick start

Requirements: Python 3.11+ with `numpy` and `flask`
(`pip install numpy flask`). Everything else is standard library. The
manuscript transliteration (ZL, IVTFF v3b, courtesy of René Zandbergen /
voynich.nu) ships in `folios/`; reference texts ship in `data/` with a
disk cache for the Gutenberg fetches, so everything runs offline.

### Web UI (recommended)

```bash
python webui/server.py          # set PORT=xxxx first if 5000 is taken
```

Open `http://localhost:5000`. From there you can:

- **Browse and filter** all 144 tests, each with its description.
- **Run any test** and read its full output in the browser.
- **Customize parameters**: 134 of the tests expose their tunable
  constants (876 parameters suite-wide — thresholds, seeds, suffix lists,
  beam widths...) as form fields with the code's real defaults. Overrides
  are spliced into a temporary copy; the scripts themselves are never
  modified.
- **Save presets** of parameter combinations and re-run them later.
- **Run all** tests with live progress and per-test error reporting.
- **Golden diff**: default-parameter runs are automatically compared
  against the committed reference outputs in `golden/`, so you can see at
  a glance whether a code change altered any result.

Details: [README_WEBUI.md](README_WEBUI.md).

### Command line

```bash
python scripts/syllabary_hypothesis.py      # any test in scripts/
python sanity_checks/run_all.py             # verify the shared math
python tools/run_baseline.py --outdir golden --hashseed 0   # refresh goldens
```

Output goes to stdout and to `results/`. For byte-comparable outputs
across runs, set `PYTHONHASHSEED=0` (the web UI and baseline tool do this
automatically). Two tests are slow by design: `chunk_alphabet_decipherment`
(~40 min) and `alphabet_space_search` (~25 min).

### Adding your own test

Drop a `my_test.py` into `scripts/`: load the manuscript through
`common.core.load_folio_lines_ivtff()` (the markup-clean loader), write
results via `common.result_path()`, and give it a docstring — the UI
discovers it automatically and exposes any module-level `UPPERCASE`
constants as parameters. Run it on the control corpora in `data/controls/`
before trusting what it says about the manuscript.

---

## Project layout

| path | contents |
|---|---|
| `scripts/` | the 144 tests + `common/` (shared loaders, statistics, fingerprint) |
| `webui/` | Flask server, test registry, runner |
| `folios/` | EVA transliteration, one file per folio (ZL, IVTFF v3b) |
| `data/` | reference corpora, control battery, Gutenberg cache |
| `results/` | test outputs (JSON + text) |
| `golden/` | committed reference outputs (hash seed 0) |
| `sanity_checks/` | hand-verified checks of the shared math |
| `tools/` | baseline/golden capture, refactor tooling |
| `attic/` | superseded code and outputs (nothing is hard-deleted) |

## Documentation map

- [INVENTORY.md](INVENTORY.md) — catalog of every test.
- [RESEARCH.md](RESEARCH.md) — the research program: assumptions audit,
  failure-mode catalog, control methodology, findings ranked
  established/suggestive/speculative.
- [README_WEBUI.md](README_WEBUI.md) — web UI reference.
- [RENAME_MAP.md](RENAME_MAP.md) — old `phaseNN` name → current name
  (historical docs and git history use the old names).
- [AUDIT.md](AUDIT.md), [CHANGES.md](CHANGES.md) — full accountability log
  of the refactor and adversarial audit that produced this codebase.

## Data credits

Manuscript transliteration: **ZL (Zandbergen–Landini) EVA transliteration,
IVTFF v3b**, from [voynich.nu](https://www.voynich.nu) — © René Zandbergen,
used here for research. Reference texts from Project Gutenberg and other
public-domain sources (see `data/`).
