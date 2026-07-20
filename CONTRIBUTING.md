# Contributing to VAIS

Contributions are welcome — and **negative results are first-class
citizens** here. A good share of the adjudicated ledger is carefully
killed hypotheses, logged with the same prominence as positives. If you
have a method that went nowhere, that is exactly the kind of thing this
suite preserves: a reproducible corpse with your name on it beats a
forum post from years ago.

**The bar is reproducibility, not positivity — and rough is fine.**
You do not need to match the house style to contribute. Open a PR with
whatever you have (a script, a notebook, even a plain-language
description of the method and what killed it, in an issue), and the
maintainers will port it into the test format with credit in the
docstring and in [CREDITS.md](CREDITS.md).

## What a VAIS test looks like

Every test in `scripts/` is one standalone Python file (stdlib + numpy;
Flask only in the web UI). If you want to write it in house form
yourself, the rules that matter — each one exists because of a logged
past failure:

1. **Load the manuscript only via the clean loaders** —
   `common.core.load_folio_lines_ivtff()` / `ivtff_clean_words()`
   (optionally with `locus_types={'P'}` for continuous text only).
   The legacy loaders leak markup tokens: ~5% of the "manuscript" they
   return is IVTFF artifact (finding T1 in [RESEARCH.md](RESEARCH.md)).
2. **Controls before manuscript, always.** Run your method on the
   control battery in `data/controls/` (real Latin/Italian, a planted
   verbose cipher, a Rugg-style grille, Timm-style self-citation,
   shuffles) before any Voynich row. A method that "finds meaning" in a
   negative control is dead, and that death is a publishable result.
3. **Pre-register your kill criteria in the docstring** — the numeric
   thresholds that would falsify the hypothesis, written before the
   first run. Results are adjudicated against those, never against
   criteria invented after seeing the numbers.
4. **Determinism**: seed everything (`random.Random(SEED)`), no wall
   clock in output. All committed outputs reproduce at
   `PYTHONHASHSEED=0`.
5. **Expose knobs as module-level UPPERCASE constants** (ints, floats,
   strings, lists). The web UI, the static site, and the in-browser
   runner discover them automatically and let anyone re-run your test
   with different parameters.
6. **Write results to `results/<test_name>.json`** via
   `common.result_path()`, and print a human-readable adjudication.

Good examples to crib from: `line_as_record_ordinal.py` (a positive
that survived), `line_discipline_compression.py` (an instructive kill),
`hapax_locus_readjudication.py` (a re-audit of an older test).

## Process

1. **PR or issue** with your method — polished or rough.
2. **Review**: maintainers read everything before running it, check
   charter compliance ([RESEARCH.md](RESEARCH.md) Phase 0 — the
   anti-crackpot charter is binding), and discuss the registration
   with you (for dead ends: what would have counted as success, and
   what killed it?).
3. **Port + adjudicate**: the test runs its controls, gets a verdict,
   and enters the ledger.
4. **Golden + site**: `python tools/run_baseline.py --outdir golden
   --hashseed 0 --only <your_test>` captures the reference output;
   `python tools/build_site.py` adds your test page (with the
   run-in-browser button) to the public mirror.
5. Before any commit: `python sanity_checks/run_all.py` must print
   `ALL SANITY CHECKS PASS`, and never modify other tests' golden
   files.

## Vocabulary discipline (binding)

Nothing in this repository claims a decode, and contributions may not
either. The strongest claim any result can make is "consistent with",
after surviving controls and held-out validation. Positive findings are
quarantined as SUGGESTIVE pending scrutiny; kills are logged with equal
prominence. See the charter in [RESEARCH.md](RESEARCH.md).

## Licensing and data

Code contributions are accepted under the repository's
[MIT license](LICENSE) — free for anyone to use. Do not add third-party
data without provenance: manuscript transliterations, images, and
reference texts carry their sources' terms, documented in
[CREDITS.md](CREDITS.md); new data needs the same treatment (source,
terms, attribution) before it can be committed.

## Anything else

Statistical critiques of existing tests are contributions too — several
ledger entries exist because someone asked a sharp question about
corpus scope or a threshold. Open an issue; if it has teeth, it becomes
a registered re-adjudication.
