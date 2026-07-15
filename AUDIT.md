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
