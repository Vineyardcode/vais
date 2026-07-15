# CHANGES.md — refactor & web UI accountability log

Branch: `refactor/test-webui`. Every entry lists what changed, why, and where
results shift relative to `baseline/` (the golden pre-refactor run captured by
`tools/run_baseline.py`).

## Phase 0 — Safety net
- Created branch `refactor/test-webui`; committed the dirty working tree
  (phases 98–107 scripts/results, CLAUDE.md, doc edits) as the baseline commit
  so every later step is diffable/rollback-able.
- Nothing is hard-deleted anywhere in this refactor; superseded material goes
  to `attic/` or lives in git history.

## Phase 1 — Inventory & baseline
- `tools/extract_inventory.py` — static scan of all 131 scripts (docstrings,
  module constants, functions, file I/O, seeds) → `tools/inventory_raw.json`.
- `tools/run_baseline.py` — ran every script once from the project root with
  stdout/stderr captured to `baseline/`, runtimes and touched result files in
  `baseline/_meta.json`. Downloaders (`download_folios.py`, `download_latin.py`)
  skipped by design (network, ~1 GB).
- `tools/dedup_map.py` — AST-hash map of duplicated functions/constants across
  scripts (the dedup blueprint; e.g. `strip_gallows` in 50 files across 5
  variants, `eva_to_glyphs` 48/4, `classify_folio` 23/8).
- `tools/inventory_notes.md` — per-script reading notes (what each test
  measures, inputs, knobs, outputs, issues); `INVENTORY.md` is generated from
  these plus baseline timings by `tools/gen_inventory.py`.
- Baseline dependency failures (expected, not bugs): `astro_crossref`,
  `crosssign_network`, `medieval_degrees`, `innermost_ring_dive` consume result
  JSONs produced by scripts that sort later alphabetically; re-run after the
  sweep so `baseline/` holds valid golden outputs for them.

### Findings recorded during Phase 1 (fixed in Phase 2 below)
1. **BUG — `grammar_extraction.py:83`**: in `parse_word`, an
   `if not matched: break` sits *inside* the `for rb in ROOT_BODIES:` loop, so
   only the first candidate root-body (`"eee"`) is ever tried; every other body
   (`ee`, `e`, `da`, …) is unreachable. Parse quality silently degraded, and
   the script's output `grammar_results.json` feeds `innermost_ring_dive.py`
   and `herbal_crossref.py`. The identical loop is *correct* in the 6 sibling
   copies (ring_text_analysis.py etc.) — this is a copy corruption.
2. **BUG — `medieval_degrees.py:71`**: same corrupted loop as (1).
3. **BUG — `phase86_chunk_equivalence.py:1138-1139`**: Step 10 (NL syllable
   cross-check) points at `data/latin_texts/caesar_gallic_wars.txt` and
   `data/vernacular_texts/libro_della_cucina.txt`; the real files are
   `caesar.txt` and `italian_cucina.txt`, so the cross-check silently skips.
   `phase86R_revalidation.py`'s docstring itself lists "NL cross-check failed
   (wrong file paths)" as a known flaw.
4. **BUG — `currier_ab.py` / `deep_dive.py`**: `analyze()` builds a `results`
   dict that is never populated, so `currier_ab_results.json` /
   `deep_dive_results.json` are always `{}`.
5. **Portability — `phase96_cluster_hchar.py`, `phase97_slot_grammar_hchar.py`**:
   hardcoded absolute paths (`c:\projects\voynich_slop\...`).
6. Dead code (no behavior impact): no-op suffix loops in the `parse_word`
   copies (`attack_plan.py:121-127`, `freq_rank_mapping.py:98-99`,
   `deep_dive_phase1.py:97-98`), unused `entry` in `currier_ab.py`, dead
   per-ring loop `ring_text_analysis.py:404-410`, dead loop
   `medieval_degrees.py:379-382`, unused `a_total` + dead
   `import random`/seed in `pharma_comparison.py`.
7. **Result-file convention split**: pre-phase-19 scripts read/write result
   JSONs in the *project root* (the committed copies under `results/` are
   stale manual snapshots nothing reads); phase 19+ write to `results/`.
   Documented per test in INVENTORY.md; root-writing behavior left as-is in
   Phase 2 to keep baselines byte-comparable (changing it would break the
   inter-script dependency chain silently). `[REVIEW]`
8. **Section taxonomy inconsistency**: two independent folio→section
   classifiers exist (header-comment-based with `astro`/`other`, and
   folio-number-based with `zodiac`/`cosmo`/`herbal-A/B`), with 8 hash-variants
   overall and different herbal-A/B boundaries in `herbal_labels.py`. This is
   *intentional drift across research eras*; harmonizing would change results
   corpus-wide. Both canonical variants are preserved in `common/` under
   explicit names; scripts keep whichever they used. `[REVIEW]`
9. **Intentional parser variants**: phases 32–36 deliberately re-parse with
   short/long suffix lists and with/without the `s` gram-prefix to test for
   parsing artifacts. These are experiment variables, not accidental drift —
   the refactor must not (and does not) unify them.

### Judgment call: no test merges `[REVIEW]`
The instruction allowed merging effectively-identical tests. After reading the
suite, none are effectively identical: the repo is a sequential research log
where later phases re-test earlier claims under different assumptions.
Closest pairs — `deep_dive.py` vs `deep_dive_phase1.py` (overlapping q-prefix
test but different root-classification sources), `phase40_syntax_attack.py`
vs `phase40_supplement.py` (the supplement *corrects* two methods of the
main script and is kept as the documented correction), and the `phase85/86/87`
scripts vs their `*R_revalidation` audits (audits complement, not duplicate).
Merging any would rewrite the research record and shift baselines with no
maintenance win, so all were kept and the relationships are documented in
INVENTORY.md.

## Phase 2 — Deduplication (details appended as applied)
- `scripts/common/` package generated by `tools/build_common.py` +
  `tools/verify_common.py`: 50 canonical helpers extracted **verbatim** from
  the dominant AST-variant of each duplicated function (alpha-rename hashing),
  with dependency closure verified per carrier script. Same-name divergent
  families are exported under suffixed names (`strip_gallows` returns
  `(residue, found)`, `strip_gallows_v2` returns the residue string, etc.).
- `tools/rewrite_scripts.py` — replaces a script's local def with a
  `from common import …` (aliased when needed) **only when** the local def's
  alpha-hash matches the extracted canonical variant *and* every dependency
  the canonical body references resolves identically in that script. Scripts
  keep minority variants locally (documented, zero behavior risk).

### Phase 2 — applied fixes (commit-by-commit detail in git log)

**Behavior-changing fixes** (baseline diffs expected and explained):
- `grammar_extraction.py` — removed the misplaced `if not matched: break`
  inside the ROOT_BODIES loop (Bug 1). Root bodies beyond `eee` now match, so
  parse quality improves; stdout and `grammar_results.json` shift, and the
  downstream `innermost_ring_dive` / `herbal_crossref` outputs shift with it.
- `medieval_degrees.py` — same fix (Bug 2); per-degree root/suffix columns
  shift.
- `phase86_chunk_equivalence.py` — Step 10 reference filenames corrected to
  `caesar.txt` / `italian_cucina.txt` (Bug 3). Step 10 now actually runs; its
  output section appears (was "file not found, skipping" in baseline).
- `currier_ab.py`, `deep_dive.py` — `analyze()` now populates the previously
  always-empty results dict, so `currier_ab_results.json` /
  `deep_dive_results.json` contain the summary metrics the scripts already
  computed and printed. `[REVIEW]` — the selection of which metrics to persist
  is my judgment; stdout unchanged.
- `phase96_cluster_hchar.py`, `phase97_slot_grammar_hchar.py` — hardcoded
  `c:\projects\voynich_slop\...` paths replaced with `__file__`-relative
  equivalents. Same resolved paths on this machine; portable elsewhere.
  stdout unchanged.

**Behavior-neutral cleanups** (stdout must remain byte-identical; verified in
the rerun diff):
- Dead `elif ...: pass` suffix branches removed from the `parse_word` copies
  in `attack_plan.py`, `freq_rank_mapping.py`, `deep_dive.py`,
  `deep_dive_phase1.py`.
- `currier_ab.py`: unused `entry` tuple removed.
- `ring_text_analysis.py`: dead per-ring loop (computed, never printed)
  removed from `phase3_register`.
- `medieval_degrees.py`: dead first-attempt boundary loop removed.
- `pharma_comparison.py`: unused `a_total`, dead `import random`/`seed(42)`
  removed (the "sampling" is a deterministic window; comment now says so).

### Phase 2 — verification against baseline (rerun + baseline-prime)

Method: full rerun of all 129 tests with the refactored code under
`PYTHONHASHSEED=0` (`rerun/`), diffed against `baseline/`. Because the
baseline ran with randomized hashing, any stdout that differed was
adjudicated by also running the **pre-refactor original** of that script
under the same fixed hash seed ("baseline-prime") and comparing
rewritten-vs-original under identical conditions.

Ledger (129 tests):
- **73** byte-identical to the baseline outright.
- **49** differed from baseline but are **byte-identical to their
  pre-refactor originals** under equal hash seed — the baseline diffs were
  pure set/dict iteration-order noise (tie re-ordering in ranked tables).
- **2** (`phase72_naibbe_calibration`, `phase73_abbreviation_model`) differ
  only in printed wall-clock "elapsed" text inside progress lines.
- **4** differ because of the documented intentional fixes:
  `grammar_extraction` (parser-loop fix; parse rate and morphology tables
  improve), `medieval_degrees` (same fix), `phase86_chunk_equivalence`
  (Step 10 NL cross-check now actually executes), `innermost_ring_dive`
  (consumes `grammar_results.json`, downstream of the grammar fix).
- **1** (`phase100_decipherment`) baseline-prime adjudication in progress
  (39-minute runtime); its diff pattern (shifted class-score values) is
  consistent with iteration-order sensitivity inside its greedy mapping
  search — to be confirmed and recorded below.

### Rewriter regressions found & fixed during verification
1. **Import placement**: in 4 scripts with mid-file top-level imports
   (`phase44/47/50/51`), the `from common import …` line landed after the
   first use. Fixed the rewriter to insert before the first removed def;
   repaired the 4 scripts; re-verified ok.
2. **Dependency-guard hole**: `full_decompose` was extracted from the
   phase23–31 family even though their local `parse_morphology` binds a
   *variant* `SUFFIXES` list (no `'sy'`, different order — first-match
   semantics make order significant). The extracted copy silently bound to
   `common`'s list, shifting decomposition counts (~0.1%). Fixed by
   restoring a **local** `full_decompose` in those 9 scripts (with a comment
   explaining why) and hardening the rewriter guard to a fixpoint rule: a
   function is only extracted if every locally-defined dependency is itself
   extracted or hash-identical. All 9 re-verified byte-identical to their
   originals. This incident is exactly why the verification loop exists.

## Phase 3 — Web UI (webui/)
- `webui/server.py` (Flask, 127.0.0.1, `PORT` env), `webui/registry.py`
  (static catalog: description from docstring, params = module-level
  UPPERCASE literal constants with the code's real defaults, dependency
  edges from the Phase-1 inventory, network flags, baseline timings),
  `webui/runner.py` (subprocess execution with AST-spliced parameter
  overrides into a temp copy — the analysis code that runs is always the
  script's own), `webui/static/index.html` (vanilla-JS single page).
- Design decision `[REVIEW]`: tests run as subprocesses of the real scripts
  rather than as imported functions. The scripts are top-level procedural
  programs; converting 131 of them into parameterized functions would have
  been a rewrite (against the "refactor incrementally, don't rewrite"
  instruction). The Flask server imports and calls the refactored
  `runner`/`registry` modules directly, and no analysis logic exists in the
  web layer, which is the constraint's intent. Subprocesses also give
  timeouts and crash isolation.
- Downloaders (`download_folios`, `download_latin`) excluded from the UI.

## Phase 4 — verification of the UI (all performed against the live server)
- Ran with **defaults**: `slot_analysis` (UI button), `hebrew_comparison`
  (API), `diacritic_audit` + `hebrew_comparison` + `phase106b_bench_variants`
  (run-all batch with per-test status) — all ok, and `hebrew_comparison`'s
  UI-run stdout is **byte-identical** to the CLI run's output.
- Ran with **custom parameters**: `phase106b_bench_variants` with
  `CH_OPTIONS=["cr","ct"]` via API *and* via the UI form (output confirms
  the override took effect: "ch variants: ['cr', 'ct']", 10 combinations
  instead of 25).
- **Presets**: saved "aggressive-cr-ct" through the UI (prompt stubbed for
  automation), persisted to `webui/presets.json`, **survived a server
  restart**, load restores the saved values, reset restores code defaults,
  delete works ("junk" preset created and removed); built-in `defaults`
  preset is undeletable.
- **Error surfacing**: unknown parameter → HTTP 400 with the name; poisoned
  parameter value → run status `error` with the full Python traceback shown
  in the output pane; forced 2-second timeout → status `timeout`.

### Final verification ledger entry
- `phase100_decipherment`: adjudicated **byte-identical** to the pre-refactor
  original under `PYTHONHASHSEED=0` (the first adjudication attempt was
  invalid — the original's run timed out at 2700s while competing with
  concurrent sweeps; the uncontended re-run completed in ~39 min and matches
  exactly). Its baseline diff was hash-seed iteration-order noise like the
  other 49.

**Verification complete: 129/129 tests accounted for.**
73 identical to baseline outright · 50 proven identical to pre-refactor
originals under fixed hash seed · 2 differ only in printed wall-clock text ·
4 differ exactly as the documented bug fixes intend.
Scratch evidence dirs (`rerun/`, `baseline_prime/`, `.bp_scripts/`) are
gitignored but left on disk for audit; `baseline/` (golden) is committed.
