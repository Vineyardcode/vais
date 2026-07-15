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
