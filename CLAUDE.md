# CLAUDE.md — VAIS (Voynich Analysis Interactive Suite)

Agent instructions for this repository. (Historical note: an earlier
CLAUDE.md here belonged to an unrelated project and is preserved in
attic/CLAUDE_czechlens_stale.md; it does not apply.)

## Binding research rules

- The anti-crackpot charter (RESEARCH.md, Phase 0) is binding law:
  controls before manuscript, counted degrees of freedom, held-out
  validation, pre-registered kill criteria, and vocabulary discipline —
  nothing is ever called "decoded"; the ceiling is "consistent with".
- New instruments register their criteria in the script docstring
  BEFORE first execution. Results are adjudicated against those
  criteria only. A kill is a valid result: log the corpse with the same
  prominence as a positive.
- Positive/decode-like findings are quarantined as SUGGESTIVE —
  flagged, never promoted without operator review.

## Operational rules (each learned the hard way)

- `python sanity_checks/run_all.py` must print ALL SANITY CHECKS PASS
  before any commit.
- Load the manuscript ONLY via `common.core.load_folio_lines_ivtff` /
  `ivtff_clean_words` (finding T1: legacy loaders leak markup tokens).
  Use `locus_types={'P'}` when continuous text is required.
- Determinism: outputs must reproduce at PYTHONHASHSEED=0. New or
  output-changed tests get golden refs:
  `python tools/run_baseline.py --outdir golden --hashseed 0 --only <stem>`
  Never modify other tests' goldens.
- Expose tunables as module-level UPPERCASE constants (the web UI, the
  static site, and the in-browser runner discover them automatically).
- Never hard-delete anything — superseded files go to attic/.
- Long research runs go through `tools/overnight.py` (queued items,
  pre-registered adjudication, results committed to overnight/<date>
  branches — never to main by the runner).
- After result-changing commits, regenerate the public mirror:
  `python tools/build_site.py`, commit docs/.
- Do not push to the remote without the operator's approval.

## Orientation

- RESEARCH.md — charter, assumption stack, strategy portfolio, the
  adjudicated ledger, and the accepted Phase 8 synthesis.
- CONTRIBUTING.md — the test format and contribution process.
- CREDITS.md / LICENSE — data provenance and licensing scope.
- INVENTORY.md — the test catalog (regenerate via tools/gen_inventory.py).
- results/overnight_state.json — queue state and verdicts.
