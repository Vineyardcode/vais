# Phase 8 (DRAFT) — The Currier-B systematization layer: consolidated evidence review

> **DRAFT — NOT PROMOTED, NOT COMMITTED TO MAIN.** This document
> assembles quarantined SUGGESTIVE material from eleven adjudicated
> runs (2026-07-17 … 2026-07-19) into a single reviewable artifact for
> the skeptical-reader gate (charter rule 5). Nothing in it upgrades
> any finding. Every number below is reproducible from the committed
> instruments at PYTHONHASHSEED=0; the artifact index is in §8.9.
> Drafted by the session agent 2026-07-19; the dispositions in §8.8
> are proposals for the human operator to accept, amend, or reject.

---

## 8.1 The claim under review

Stated in the program's registered vocabulary, at maximum precision and
minimum romance:

> In Currier B, the words within a line are ordered: word-initial
> glyph class predicts interior line position (front-loaded — strongest
> in the early interior), at small absolute magnitude (~0.05 bits/token)
> but with high statistical robustness. The ordering is not explained by
> folio/section composition, line content, scribal space management,
> paragraph-initial behavior, or the choice of transliteration. It is
> not a record template or positional notation at calibrated strength;
> its overall class-ordering profile is language-like, PLUS a positional
> component that genuine prose measurably lacks. It intensifies from
> hand A to hand B and from bio to recipes.

Nothing here is a decode. No field, meaning, or plaintext is named.

## 8.2 The evidence chain (all runs adjudicated by pre-registered criteria)

| item | instrument | verdict | key numbers |
|---|---|---|---|
| N1 | verbose inversion, rung 3 (max compute) | KILLED | P4 recovery 39% (<50%); margin −0.150; autopsy: 65–99.6% holdout exclusion — objective exploitable |
| N1b | rung 3b (coverage-penalized objective) | INSTRUMENT PASSED; VMS negative | P4 recovery 65%, margin +0.350; VMS full/A/B −0.880/−0.842/−0.895 vs floor −0.862 → within noise |
| N3 | S7 v1 (pooled line-as-record) | KILLED (pooled) | gate P-REC +0.719/P1 −0.003; VMS_full margin +0.033 (<0.05); B +0.077 / A −0.006 noted post hoc |
| N3b | S7 rung 2 (per-hand, harder test) | B_ONLY | B +0.0513 > all 20 per-hand nulls, margin +0.058; A +0.011 above nulls, below floor |
| N3c | S7 rung 3 (composition vs ordinal) | ORDINAL_GLYPH_STRUCTURE | folio-nulls +0.0571, line-nulls +0.0577, glyph-only +0.0571; B glyph +0.0524 / len +0.0018; P-JUST reference +0.0133 (len-dominated: +0.0099/+0.0039) |
| N2 | S9 (5 transliterations, fixed floor) | PARTIAL | pass ZL +0.0501 / FG +0.0534 / IT +0.0529; fail GC +0.0487 (−0.0013), CD +0.0326; all 5 beat all 20 nulls |
| N2b | S9 floor calibration (implant ρ) | REFERENCE_FLIP | ρ: ZL 1.00, CD 1.12, GC 1.12, FG 1.17, IT 0.97 — floor-scaling hypothesis REFUTED; FG raised-floor flip → no re-adjudication |
| N2c | S9 significance-only (200 nulls) | ROBUST_SIGNIFICANCE | 5/5 readings beat all 200 nulls (p<0.005 each); all 1,000 null medians negative |
| N3d | S7 rung 4 (paragraph control + characterization) | CHARACTERIZED | para-initial excluded → +0.0519, beats 200 nulls; bins m1 +0.0816 > m2 +0.0381 > m3 +0.0299; carriers: first-glyph q +0.0352, c +0.0281, o +0.0200; finals -y +0.0191, -r, -l; indifferent: d/y/t/s/a-initial |
| N3e | S7 rung 5 (within-section) | SECTION_GENERAL | recipes +0.0584, other_B +0.0478, bio +0.0106 — each beats all 200 of its own nulls |
| N4 | S5/S6 family classifier | FAMILY_LANGUAGE | B (r_pos +0.0354, r_bi +0.0407): nearest language d 0.053 ≪ hoax 0.178, records 0.414, positional 0.508; gate sep 0.144 vs required 0.023 |
| N5 | S7-R independent re-implementation (rank statistic, no bins/smoothing/holdout, EVA-glyph classes) | REPLICATED | B p=0.0010 (0/1000 perms); gate clean (P-REC 0.001, P1 0.133, N1 0.643); observationally A also rejects (p=0.0010); class mean-ranks corroborate rung 4 (sh 0.457, q 0.474 earliest; r 0.561 latest) |

Registration hygiene of note: rung 2's test was made strictly harder
than the observation that motivated it; the N2b normalization was
symmetric and measured (and self-invalidated as registered); N2c's
criteria change was explicitly human-approved before registration; N4
carried an explicit none-of-the-above arm (F4).

## 8.3 What was killed along the way (equal prominence, per charter)

1. **The strict 1:1 verbose-cipher reading of the manuscript** —
   tested for the first time by a validated instrument (N1b) and
   negative: all three VMS rows sit within the free-mapping noise
   floor while the planted control clears it by 3.5× the margin.
2. **The rung-3 inverter objective** — exploitable by coverage
   shrinkage; produced a false "grille beats known cipher" ordering
   before the fix. Two crashes and one near-catastrophic scoring
   artifact are logged in the instrument docstring.
3. **The pooled line-as-record reading** — line-length artifact at
   pooled level (S7 v1).
4. **The space-management explanation of B's ordering** — P-JUST
   reproduces the LAAFU-predicted signature (small, length-dominated);
   B's signature is its mirror image (glyph-dominated, no length).
5. **The floor-scaling excuse for GC/CD** — refuted by measurement
   (ρ > 1: those readings are *more* sensitive to planted order).
6. **The record-template and positional-notation readings of B's
   ordering** — dead at family level: calibrated versions produce
   ~10× B's ordering strength with clearly different profiles.

## 8.4 Objections raised and their dispositions

| objection | test | outcome |
|---|---|---|
| holdout memorization | folio-level holdout, all instruments | controlled by design (rung-2 lesson) |
| post-hoc selection | rung 2: per-hand nulls, multi-split, harder than the motivating observation | survived |
| section/folio composition | within-folio shuffles ×20 | dismissed (+0.0571) |
| line content selection | within-line shuffles ×20…×200 | dismissed (+0.0577; later p<0.005 at 200) |
| scribal justification | P-JUST control + feature decomposition | opposite signature |
| transliteration artifact (A1) | 5 readings, 200 nulls each | robust (p<0.005 ×5) |
| paragraph-initial regime | exclusion of all 131 marked lines | dismissed (signal rises) |
| section confound / pooling | per-section batteries | replicates in all three strata |
| "it's records/numbers" (over-reading) | S5/S6 family classifier | rejected at calibrated strength |

## 8.5 The residue, quantitatively

What survives every test is small, specific, and consistent:

- **Magnitude**: ~0.05 bits/token of interior positional information in
  B (recipes +0.058 > other_B +0.048 > bio +0.011; hand A ~+0.010).
- **Shape**: front-loaded (early interior m1 carries 2.7× the late
  interior); carried by word-initial glyph identity (first +0.0296,
  last +0.0174, length +0.0018, gallows +0.0024).
- **Carriers**: q-, c-, o-initial word classes (positive contributors),
  -y/-r/-l finals; d-/y-/t-/s-/a-initial classes positionally
  indifferent.
- **Family profile**: language-like ordering magnitudes (r_pos +0.035,
  r_bi +0.041) — but genuine prose has r_pos ≈ 0.000, so the positional
  component itself is the anomaly, not the overall profile.
- **Gradients**: A ≈ ⅕ of B; bio ≪ recipes. Both echo the phase-101
  A/B separability result and Parisel 2026a's "switch intensity"
  picture (Phase 7.1).

## 8.6 Convergence with prior and external results

- **Phase 109 (forgery tournament)**: line-boundary effects are the
  universally unreproduced feature ("the moat"). The B residue is the
  first registered structure found *inside* lines beyond the moat.
- **N1b**: the manuscript is not a strict verbose cipher, yet the
  verbose-cipher *profile* (h2_ratio, boundary excess) still matches on
  independent features — consistent with "language-like substrate +
  added systematization" rather than plain language or pure cipher.
- **Parisel 2026a (arXiv:2604.25979)**: A/B as a graded switch of one
  system, 92% template variance — externally derived, matching both
  gradients here. (Caveat: no negative-control battery reported there;
  our replication of that instrument under our battery remains open —
  Phase 7.1b.)
- **LAAFU prior art**: the community's justification model was
  confirmed as a real mechanism (P-JUST) — and shown to be the wrong
  explanation for this particular signal.

## 8.7 Weaknesses a skeptical reader should attack first

Listed in the order I would attack them:

1. **Shared instrument DNA.** Every S7-family rung uses the same
   feature set, position bins, Laplace smoothing, and holdout scheme.
   The null batteries randomize the *data*, never the *instrument
   design*. A design artifact that correlates with real line structure
   would replicate across all rungs and all readings. Mitigation
   evidence: the P-REC/P-JUST/P-NUM controls behave as designed and
   P1/N1 sit at zero — but an independent re-implementation (different
   bins, different estimator, ideally different author) is the real
   test.
   **[UPDATED 2026-07-19, N5]: the implementation half of this
   objection is now answered — a methodologically disjoint instrument
   (rank statistic, no bins/smoothing/holdout, EVA-glyph classes,
   fresh seeds) replicates B at p = 0.001 with a clean gate, and its
   class mean-ranks independently corroborate the rung-4
   characterization. The AUTHOR half remains open: both
   implementations were written by the same agent, and this caveat
   travels with the finding until a third party re-derives it.
   New observational fact from N5: hand A also rejects (p = 0.001)
   under the more sensitive statistic — the gradient reading of §8.5
   should say "both hands, B stronger", not "B-only".]**
2. **Reading non-independence.** The five transliterations are not
   fully independent: later transcribers consulted earlier ones, and
   all share reading conventions (line order, uncertain-space policy).
   Cross-reading robustness excludes idiosyncratic error, not shared
   convention. Fully escaping this requires S2 (raw-scan clustering).
3. **Sequential testing on fixed data.** There is no fresh manuscript.
   The ladder grew sequentially on the same corpus; each registration
   was harder than the last, but a principled global multiplicity
   correction across the whole ladder is not computable. The honest
   statement is "p < 0.005 per registered test", never a joint p.
4. **Small absolute effects.** 0.05 bits/token against feature
   entropies of ~9 bits/token is a ~0.5% effect. Robust ≠ large;
   large ≠ meaningful; the program has only established robust.
5. **The N2c criteria change.** Dropping the effect floor was disclosed
   and human-approved, but it followed two unfavorable-floor results.
   A reviewer should re-derive N2/N2b/N2c from the JSONs and decide
   whether the sequence reads as calibration or as bar-lowering. (The
   margins and ρ table are all committed; the re-derivation is
   mechanical.)
6. **Paragraph marking is interpretive.** T-PARA trusts ZL's locus
   markers; paragraph identification is itself a transcriber judgment.
7. **Section taxonomy is coarse.** The folio-number taxonomy assigns
   combined-folio files imperfectly; the within-section replication is
   robust to this only insofar as misassignment is noise, not bias.

## 8.8 Proposed dispositions (for human decision — nothing applied)

1. **Promote to the SUGGESTIVE tier of the Phase 5 ledger** (from
   raw quarantine): the residue statement of §8.1, with §8.7 attached
   verbatim. It has survived more registered attack than anything else
   in that tier.
2. **Keep at instrument level** (no ledger entry): the family
   assignment (N4) and the characterization tables (N3d) — they
   describe the finding; they are not independent findings.
3. **Record as ESTABLISHED** (they are clean negatives with validated
   instruments): (a) the strict 1:1 verbose-cipher negative (N1b);
   (b) the S7 pooled kill as a line-length artifact result (N3).
4. **Registered next steps, in value order**: (i) independent
   re-implementation of the S7 measurement (attacks §8.7-1); (ii) the
   Parisel-instrument control-battery replication (Phase 7.1b, attacks
   the switch-covariate story); (iii) a generative model of the
   residue entered into the phase-109 tournament — the only path the
   charter allows toward anything stronger than "consistent with";
   (iv) S2 raw-scan feasibility (attacks §8.7-2, the last A1 escape).
5. **Merge decision** for branches overnight/2026-07-{17,18,19} and
   the RESEARCH.md appends: recommend merging the *records* (logs,
   reports, JSONs) after review; the ledger promotions above are a
   separate, explicit edit.

## 8.9 Artifact index

- Reports: `results/overnight_2026-07-17_report.md` (N1, N1b),
  `results/overnight_2026-07-18_report.md` (N3, N3b, N3c, N2, N2b,
  N2c), `results/overnight_2026-07-19_report.md` (N3d, N3e, N4).
- Branches / verdict commits: `overnight/2026-07-17` → b1451f7 (N1),
  818dce0 (N1b); `overnight/2026-07-18` → 2633751 (N3), 17783ad (N3b),
  6fa9747 (N3c), 7b0d66d (N2), 3211e0d (N2b), 5930e79 (N2c);
  `overnight/2026-07-19` → b4c3726 (N3d), f441011 (N3e), 6402ce8 (N4).
- Instruments (main, PYTHONHASHSEED=0 goldens committed):
  `verbose_cipher_inversion.py`, `line_as_record_structures.py`,
  `line_as_record_per_hand.py`, `line_as_record_ordinal.py`,
  `line_as_record_characterization.py`, `line_as_record_section_split.py`,
  `cross_transliteration_invariance.py`,
  `transliteration_floor_calibration.py`,
  `transliteration_significance.py`, `line_class_family_test.py`;
  runner `tools/overnight.py`; state `results/overnight_state.json`.
- External data: `data/translit/{CD,GC,FG,IT}2a-n.txt` (voynich.nu,
  fetched 2026-07-18, committed for offline reproducibility).
