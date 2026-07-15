# AUDIT.md — VAIS full adversarial audit + rebrand log

Branch: `audit/full-review` (from `refactor/test-webui` @ f219bf7).
Conventions: every fix logged with file, what was wrong, what changed, and a
before/after where results shift; lower-confidence judgment calls tagged
`[REVIEW]`. Clean areas are recorded too — an audit that only lists problems
is unverifiable.

## Phase 0.5 — Rebrand sweep (voynich_slop → VAIS)

Case-insensitive sweep for `voynich_slop` / "voynich slop" over all tracked
source/doc/config files (excluding data corpora `folios/`, `data/voynichese/`,
and output dirs `baseline/`, `golden/`, `results/`, `attic/`, scratch dirs).
Hits and disposition:

| location | occurrences | disposition |
|---|---|---|
| `scripts/phase96_cluster_hchar.py` 448-450, 468, 531 | 5 hardcoded absolute paths | **AUDIT FINDING A1 — fixed in code (see below), not a rebrand edit** |
| `webui/static/index.html` (title, h1) | brand string "Voynich Analysis Suite" | rebrand → "VAIS — Voynich Analysis Interactive Suite" |
| `README_WEBUI.md` (header, root-path line) | brand + old path | rebrand; path updated to the post-Phase-5 location |
| `.claude/launch.json` | server name `voynich-webui` | rebrand → `vais-webui` |
| `webui/server.py` docstring | "Voynich analysis suite" | rebrand |
| `tools/gen_inventory.py` → `INVENTORY.md` header | generated doc | generator updated + doc regenerated |
| `CHANGES.md` 51, 120 | historical quotes of the old hardcoded paths | **kept verbatim** — they quote past defects; rewriting them would falsify the accountability record. Header note added. |
| `tools/inventory_notes.md` | historical Phase-1 reading notes | kept verbatim (same reason) |
| `tools/inventory_raw.json` | generated static-scan artifact | regenerated after A1 fix (strings disappear with the code fix) |
| remote `origin` | github.com/Vineyardcode/voynich_slop | `gh repo rename` attempted — outcome logged below |

## Findings

### A1 — CRITICAL(portability) / previous-pass error: phase96 hardcoded paths survived
- **File**: `scripts/phase96_cluster_hchar.py` lines 448-450, 468, 531.
- **Wrong**: the previous pass replaced the module-level `FOLIO_DIR`
  constant and CHANGES.md claims phase96's "hardcoded absolute paths [were]
  replaced with `__file__`-relative equivalents" — but five more absolute
  paths (`latin_dir`, `vern_dir`, `czech_dir`, and a temp-file path used
  twice) sit mid-file in lowercase locals, which both the constant-grep and
  the module-level static scan missed. The folder rename (Phase 5) would
  have broken this script; CHANGES.md's claim was false as stated.
- **Fix**: all five derive from a `_PROJECT_DIR = dirname(dirname(__file__))`
  base, same idiom as the previous partial fix.
- **Shift**: none on this machine (paths resolve identically);
  verified byte-identical vs `golden/`.

### Remote rename — manual steps required (no `gh` CLI installed)
`git remote -v` → `origin = https://github.com/Vineyardcode/voynich_slop.git`.
Push auth works (`git ls-remote` OK) but repository *rename* requires the
GitHub API or web UI, and no authenticated CLI is available. Exact steps:
1. Web: https://github.com/Vineyardcode/voynich_slop → Settings → General →
   Repository name → `vais` → Rename. Then in "Description", set:
   "Voynich Analysis Interactive Suite".
2. Locally afterwards:
   `git remote set-url origin https://github.com/Vineyardcode/vais.git`
   (GitHub redirects the old URL indefinitely, so this is safe to do anytime.)
3. No badges/clone URLs exist in the docs; nothing else to update.

### Rebrand verification protocol
"Byte-identical vs baseline" is interpreted against **`golden/`** (the
committed PYTHONHASHSEED=0 reference): `baseline/` proper was captured under
randomized hashing, and ~50 tests legitimately reorder tie-rows against it
(established and documented in CHANGES.md Phase 2). Full-suite rerun result
recorded below when complete. Expected deltas: phase72/73 wall-clock
"Elapsed:" lines only (documented benign).

## Phase 1 — fresh-eyes findings (shared modules & web layer)

### A2 — MAJOR(metadata): registry DEPENDS table wrong in both directions
- **File**: `webui/registry.py`.
- **Wrong** (verified against actual result-file reads in code):
  (a) `f66r_analysis` reads `attack_plan_results.json` (3 sites) and
  `freq_rank_results.json` but had NO dependency entry — the UI showed no
  "needs X" badge, so a user could run it against stale/absent inputs;
  (b) `hebrew_deep_analysis -> attack_plan` was claimed but FALSE — the
  script only mentions attack_plan in a comment ("PARSER (reused from
  attack_plan.py)") and reads nothing;
  (c) `phase86R_revalidation` reads `phase86_chunk_equivalence.json` but had
  no entry.
- **Fix**: table corrected + provenance comment. No analysis behavior change.
- Cross-check clean: phase98/100/101/102 edges verified real via
  `load_phase86_clusters`; astro/ring/grammar/hebrew_comparison/phase59/60
  edges verified real.

### Clean (verified, no action)
- `webui/runner.py` `_coerce`: string→int/float/bool coercions correct
  (incl. bool-from-string table and bool-rejected-as-int); json params
  literal-eval'd and container round-trip (list→set/tuple) correct.
- `apply_overrides`: AnnAssign/augmented assignments correctly NOT matched
  (unknown params error out); multi-line literal replacement splices by
  ast end_lineno; missing-param detection works.
- `compare_to_golden` newline normalization handles \r\r\n legacy + \r\n.
- `registry.extract_params`: non-JSON-serializable and >800-char literals
  excluded; sets served sorted (documented; overridden runs are excluded
  from golden comparison so set-iteration order cannot poison it).
- `scripts/common/core.py` read end-to-end: entropy/MI/IC/Zipf/H(Y|X)
  formula review at reading level OK (hand-verification in Phase 2);
  `eva_to_glyphs` boundary conditions verified correct (`i+2 < len` ⟺
  trigraph fits); `parse_one_chunk` run caps (≤3) match the phase85 family
  definition; taxonomy variants match their carriers.

### A3 — MINOR(hygiene): duplicates and dead code in the web/common layer
- `common.extract_words` and `common.extract_words_from_line` are
  byte-identical twins (two names for one body, from two script families).
  Left as two names (both are imported by scripts); marked here so nobody
  "fixes" one and not the other. `[REVIEW]` — could alias one to the other;
  not done to avoid touching 15+ import sites for zero behavior gain.
- `webui/runner.py` `run_test(..., progress_cb=None)` — dead parameter,
  never used. Removed.
- `common.mean_word_length` would crash if numpy were absent (np=None
  guard exists but function doesn't check). All scripts require numpy;
  noted, not changed.

### A4 — CRITICAL(wrong results): phase74 star annotations silently discarded
- **File**: `scripts/phase74_paragraph_framing.py` (`parse_folio_extended`).
- **Wrong** (original-author bug, pre-dating the refactor — survived because
  the refactor only verified behavior *preservation*): three defects in the
  paragraph state machine —
  (1) closing a previous paragraph on a new `@P`/`<%>` start passed
  `current_star` (the NEW paragraph's annotation) to the OLD paragraph and
  then nulled it, so both paragraphs lost/mixed their stars;
  (2) the normal multi-line close path read
  `getattr(parse_folio_extended, '_last_star', None)` — a function attribute
  never assigned anywhere — so every multi-line paragraph's star was None;
  (3) the EOF close hardcoded None.
- **Symptom**: Test 7a (star type vs frame type) degenerated to a single
  "NONE stars (n=285)" bucket; section 11's Star column was all "none".
  Detected by cross-consistency: phase71 independently reports 14 DARK-star
  paragraphs from the same transcription.
- **Fix**: all three close sites pass the star captured at the paragraph's
  start (`para_star`, initialized None, cleared on close).
- **Before/after**: 7a BEFORE = `NONE (n=285)` only; AFTER = `DARK (n=14)`,
  `DOTTED (n=129)`, remaining groups populated — DARK n=14 now agrees
  exactly with phase71's independent count (cross-consistency restored).
  `baseline/` + `golden/` refreshed for this test with this justification.

### A5 — CRITICAL(wrong results): phase56 JSD NaN-poisoned distance matrix
- **File**: `scripts/phase56_syllabary_test.py` (`jsd`, section 56c).
- **Wrong** (original-author bug): numpy JSD masked only on `m > 0`, so any
  context cell present in one distribution but absent in the other produced
  `0 * log2(0/m) = 0 * -inf = NaN`; the NaN propagated through `np.sum`, and
  every character-pair distance in 56c printed as `JSD = nan` (visible in
  golden/baseline output) — the "most similar character pairs" ranking was
  meaningless.
- **Fix**: mask each KL term on its own distribution as well
  (`(p>0)&(m>0)` / `(q>0)&(m>0)`), the standard 0·log0=0 convention.
- **Before/after**: 56c BEFORE = all pairs `nan`; AFTER = real ranking
  (m-r 0.1969, l-r 0.2194, c-s 0.2399, …). 65 diff lines, all within 56c.
  `baseline/` + `golden/` refreshed for this test.

### JSD family disposition (10 variants audited)
- Correct standard JSD: phase43, phase53 (deliberate Laplace smoothing),
  phase77, phase78, phase82, phase86 (eps-clip approximation), phase100,
  phase101/102. All verified against the ½KL(P||M)+½KL(Q||M) definition.
- `currier_ab.jsd` and `shorthand_analysis._jsd_from_counters` return the
  Jensen-Shannon **distance** (sqrt of divergence) while their docstrings
  say "divergence" — mathematically legitimate metric, each used only for
  internal comparisons, so values were NOT changed (that would shift
  results for a labeling nit). Docstrings noted here as the record.
  `[REVIEW]`
- phase56: FIXED (A5 above).

## Phase 1 — data-flow map (raw transcription → tests)

`folios/*.txt` (201 IVTFF EVA transcriptions; `folios/` also holds 201 .png
scans, unused by code) → one of **six loader families**, each with its own
tokenization rules (differences are documented intent, verified by
corpus-size cross-tabulation over golden outputs — scripts within a family
agree exactly):

| family (representative loader) | corpus size | used by |
|---|---|---|
| `load_all_tokens` (strip non-a-z inside tokens, len≥2) | 40,300 | phase27-34, 104, 105 |
| chunk family (`extract_words_from_line`+`clean_word`) | 40,351 | phase79, 85-94, 98-102 |
| phase19-26 zodiac-era extractor | 39,564 | phase19-26 |
| gallows-strip family (`extract_all_words`) | 39,531 | coptic/egyptian/four_tasks/gallows_semantics/leo/root_lexicon |
| reject-non-a-z + drop-'?' family | 39,433 | gallows_test, rtl_direction_test |
| slot/attack family (len≥2, drop '?' and "'") | 38,732-38,900 | slot_analysis, attack_plan era, hebrew_* |
| paragraph extractors (phase71: 42,336 / phase74: 42,252) | — | intentionally different filters; Δ84 words explained by variant-marker & comma handling |

Preprocessing stages per family: tag/annotation removal → tokenization →
(family-specific) morphology/glyph/chunk parsing → per-test statistics →
stdout + `results/` JSON via `common.result_path`. Duplicated conceptual
steps that remain (by design, each variant carried by its era): 6 loader
families above; 3 parser families (multipath slot parser, gallows-strip
morphology, Mauro chunk grammar); 2 section taxonomies + 1 labels variant.

## Phase 2 — hunt ledger (what was checked, what was found)

**Math & logic**
- entropy/MI/conditional-entropy/IC/Zipf/Heaps/Cramér's V/JSD verified
  against standard definitions; hand-verified in `sanity_checks/` (uniform
  entropy = log2 n, MI hand-computed 2×2 = 0.311278…, JSD conventions,
  Cramér's V = 1.0/0.0 for perfect/none association, Heaps slope
  base-invariance).
- FOUND: A5 (phase56 JSD NaN); phase101 null-protocol asymmetry (below);
  A4 (phase74, found via cross-consistency).
- `heaps_exponent` 8 variants: same regression, era-specific guards —
  clean. `compute_fingerprint` 10 variants: genuinely different feature
  sets per phase — intentional. `cramers_v`: single variant, correct.

**Cross-consistency**
- Corpus sizes cross-tabulated across all 129 golden outputs → loader
  families internally consistent (table above).
- phase71 vs phase74 star counts: DISAGREED (14 DARK vs none) → A4 found
  and fixed; now agree exactly.

**Data handling**
- No stale tmp files; folios/ complete (201/201); no non-`f*` strays;
  `.tmp` scratch can't leak into `*.txt` globs; gutenberg cache complete
  (10/10 texts).
- attic/root_result_snapshots fully covered by regenerated `results/`
  equivalents (nothing unique lost; the one divergent file was the
  documented UI-poison artifact).

**Self-audit of previous pass**
- grammar_extraction/medieval_degrees loop fix: functionally verified
  (multi-glyph bodies parse: 'chodaiin' → root 'choda').
- phase86 Step 10: runs against both reference texts in golden.
- currier_ab/deep_dive results JSONs: populated, sensible keys.
- No merges were performed last pass; nothing to re-verify there.
- FOUND: A1 (phase96 paths — the previous pass's fix was incomplete and
  CHANGES.md overclaimed it).
- Import-shadowing scan: no script defines a name it also imports from
  common. No duplicate top-level defs anywhere.

**Web UI parity**
- Spot-verified registry defaults == code literals (int/list/declared-
  variant SUFFIXES/ZONE_PREFIX cases). Coercions, override splicing, and
  golden-diff normalization covered by `sanity_checks/checks_webui.py`.
- FOUND: A2 (DEPENDS table wrong in both directions).

**Robustness & rot**
- Bare `except:` census: 10 sites in 7 scripts, all wrapping file reads /
  cleanup / regex fallbacks with graceful degradation. `[REVIEW]` noted:
  f66r_analysis's dependency-read fallbacks would silently use freq=0 if
  its input JSONs were corrupt (not changed — fallback semantics are
  plausible intent and changing them shifts results on missing inputs).
- Dead `progress_cb` removed (A3).

### A6 — MAJOR(methodology): phase101 classifier null used a different protocol than the real metric
- **File**: `scripts/phase101_currier_ab_dichotomy.py` (Step 6).
- **Wrong** (original-author): the real accuracy is leave-one-out, but the
  500-shuffle null used resubstitution (sample included in its own
  centroid), inflating null accuracy — an apples-to-oranges comparison
  whose bias was CONSERVATIVE (understated z, overstated p).
- **Also**: docstring + code comment claimed "logistic regression"; the
  implementation is (and always printed) nearest-centroid. Labels fixed.
- **Fix**: null now uses the identical LOO protocol via O(1) class-sum
  exclusion. Before: z=+11.71, p=0.0000, null 0.574±0.027. After: recorded
  below when the rerun completes. Conclusion direction unchanged
  (significant separation); the test is now internally consistent.

**numpy log-domain audit** (all 26 np.log sites reviewed): phase84 MI uses
a correct double mask; phase103/54/86R JSD helpers eps-smooth + renormalize
before logs — safe; the "nan" strings in phase86's output are the
documented by-design sentinel for undersized collapsed corpora (heaps/hapax
< threshold), not corruption. Only defect: phase56 (A5, fixed).

**Predicted Phase-5 casualty (logged in advance)**: 51 golden/ and 45
baseline/ captures contain the old absolute project path inside output
text (scripts that print "saved to <abs path>"). After the folder rename,
these lines will read `...\vais\...`; the reference files will be
mechanically rewritten (voynich_slop → vais inside the captured text) in
the Phase-5 commit so the golden badge stays meaningful. Content otherwise
unchanged.
