# Overnight report — 2026-07-21

<!-- OVERNIGHT-SUGGESTIVE -->
> **SUGGESTIVE FINDING — AWAITING HUMAN REVIEW — DO NOT MERGE.**
> A run below produced a decode-like/positive signal. It is
> quarantined: committed only to its overnight/ branch, claims
> nothing beyond "consistent with", and is not a decode. See the
> flagged run section for the numbers and the pre-registered
> criteria they were judged against.

## Run 2026-07-21 00:37:21 — N6g
**S3 rung 4: principled derivation — do the two shared axes reduce to class properties?**
- script: `scripts/line_discipline_derivation.py`
- profile: `{}`
- log: `overnight_2026-07-21.log`; results JSON: `line_discipline_derivation.json`; branch: `overnight/2026-07-21`
- runtime: 40s (0.01 h), exit code 0

**Pre-registered outcomes** (script docstring): "derive" means REDUCE the shared axes to position-independent class properties (log-frequency + gallows-membership + word-length) — not external layout physics, which stays open. An axis is reduced if its OLS R^2 beats a shuffle null by >= 0.25 AND the derived table still closes the moat.

| axis | R² | null R² | excess | freq β | gallows β | wlen β |
|---|---|---|---|---|---|---|
| 1 (edge, shared) | 0.5273 | 0.2379 | +0.289 | +0.47 | +0.21 | -0.29 |
| 2 (interior, shared) | 0.4981 | 0.2517 | +0.246 | -0.12 | -0.22 | -0.21 |
| 3 (pre-final, B-only) | 0.4154 | 0.2592 | +0.156 | +0.09 | +0.44 | +0.00 |

Derived-axes table (Âx₁, Âx₂ + measured axis 3): D_line 9.039 vs bar 7.489 (measured rank-3 achieved 6.882).

**VERDICT: NOT DERIVED (partial reduction, corpse logged) — the three principles explain a SUBSTANTIAL, above-chance share of each shared axis (edge R² 0.5273, interior 0.4981, both ~2× the shuffle null) with interpretable coefficients (frequent, gallows-initial, short words → line edges — Grove/LAAFU made quantitative), but substituting the ~50%-fidelity predictions reopens the moat (D_line 9.039 > bar 7.489). The strong claim ("the shared axes ARE these properties") is killed; the weak claim (they are ~half these properties, plus real residual structure the interior gradient carries on its own) is documented. Richer principle sets are the informed next candidate.**

## Run 2026-07-21 00:59:44 — N6h
**S3 rung 5: morphology derivation — does within-word position reduce the interior gradient?**
- script: `scripts/line_discipline_morphology.py`
- profile: `{}`
- log: `overnight_2026-07-21.log`; results JSON: `line_discipline_morphology.json`; branch: `overnight/2026-07-21`
- runtime: 41s (0.01 h), exit code 0

**Pre-registered outcomes** (script docstring): the HYPOTHESIS — the line orders words by the typical WITHIN-WORD position of their first glyph (word-initial-type early, word-final-type late) — tested by adding within-word morphology (wwpos + finality) to the N6g principle set. Reduced iff interior R^2 >= 0.7 AND gain over the 3-principle baseline >= 0.1.

| axis | R² (3-principle → +morphology) | gain | wwpos β | finality β |
|---|---|---|---|---|
| 1 (edge) | 0.5273 → 0.5806 | +0.053 | +0.00 | -0.18 |
| 2 (interior) | 0.4981 → 0.6294 | +0.131 | +0.31 | -0.25 |
| 3 (pre-final) | 0.4154 → 0.6226 | +0.207 | +0.06 | -0.16 |

Within-word position by class (0=word-initial, 1=word-final): q 0.00, sh 0.13, ch 0.20, p 0.20, o 0.25, t 0.28, k 0.34, a 0.45, s 0.48, # 0.50, d 0.58, l 0.62, y 0.90.
Enriched derived table: D_line 9.628 vs bar 7.489 (does not close; the residual persists).

**VERDICT: MODEST IMPROVEMENT (hypothesis directionally confirmed, not dominant) — within-word position is the LARGEST predictor of the interior gradient (wwpos β +0.31, positive as hypothesized: word-initial-type glyphs early, word-final-type late) and raises interior R^2 by +0.131 (0.50 → 0.6294), clearing the gain bar but not the 0.7 strong-reduction target. So the interior gradient is PARTLY a morphological echo — the line reflects word structure — but a residual survives even frequency + gallows + length + within-word position. The line-discipline mystery is now this smaller, sharper residual.**

## Run 2026-07-21 01:25:15 — N11
**Labelese subsystem test: are the marginal labels a distinct, section-specific naming register?**
- script: `scripts/labelese_subsystem.py`
- profile: `{}`
- log: `overnight_2026-07-21.log`; results JSON: `labelese_subsystem.json`; branch: `overnight/2026-07-21`
- runtime: 1s (0.00 h), exit code 0

**Pre-registered outcomes** (script docstring; prompted by f66r's label-dense margin): are the IVTFF label loci a distinct register, and a SECTION-SPECIFIC naming system beyond dialect? Controls (synthetic naming vs generic) validate the measure; the label result is compared to a SIZE-MATCHED running-text baseline. F7-bound: no label is read.

Corpus: 628 label tokens (450 types) over sections bio 123, herbalA 87, pharma 279, text 2, zodiac 137. Controls gate: P-NAME +0.159 vs P-GEN +0.014 → PASS.

| test | value | baseline | reading |
|---|---|---|---|
| (D) first-glyph JSD | 0.1507 | subsample null 0.0161 | distinct register |
| (S) section U* | labels +0.0797 | matched running +0.0366 | naming margin +0.0432 |

Label first-glyph profile: o 56%, d 14%, s 8%, ch 7%, y 7%, a 4%, sh 2%, k 2% — the o-/d- dominance, distinct from the gallows/q of line-starts.

**VERDICT: LABELESE NAMING SYSTEM — labels are a distinct register (first-glyph JSD 0.1507 ≫ null) AND their vocabulary is more section-specific than a size-matched running-text sample (U* +0.080 vs +0.037, margin +0.043, beating its own shuffle null): a section-bound naming-like register, beyond the dialect variation running text already carries. SUGGESTIVE, quarantined. POWER/CONFOUND CAVEATS travel with it: only 628 label tokens, unevenly spread (pharma 279 vs text 2), and label/running section marginals differ — the effect could be inflated by the pharma-label concentration. NOT a decode and F7-bound: "naming-like" is a distributional statement, not a claim that any label has been read. A section-marginal-matched re-test is the registered follow-up.**

## Run 2026-07-21 01:38:33 — N11b
**Labelese naming, refined: word-shaped labels + section-marginal-matched baseline**
- script: `scripts/labelese_naming_refined.py`
- profile: `{}`
- log: `overnight_2026-07-21.log`; results JSON: `labelese_naming_refined.json`; branch: `overnight/2026-07-21`
- runtime: 1s (0.00 h), exit code 0

**Pre-registered outcomes** (script docstring): N11's naming claim re-tested with its two flagged defects removed — (1) WORD-SHAPED labels only (>= 3 glyphs; fragment/marker tokens split off), (2) a SECTION-MARGINAL-MATCHED running baseline (identical per-section counts), so the pharma-label concentration cannot inflate the margin.

Word-shaped labels: 535 tokens (424 types); fragments split off: 93. Per section: bio 105, herbalA 34, pharma 273, text 2, zodiac 121.

| quantity | value |
|---|---|
| U*(word-shaped labels) | +0.0496 (beats null: True) |
| U*(marginal-matched running) | +0.0797 |
| naming margin | -0.0300 (threshold 0.03) |
| U*(fragment labels, observational) | +0.1152 |

**VERDICT: NAMING WAS CONCENTRATION (finding withdrawn) — with fragments removed and section marginals matched, word-shaped labels are LESS section-specific (+0.050) than running text drawn from the SAME sections (+0.080); margin -0.030 <= 0. N11's "naming system" reading was the pharma-label concentration, exactly the confound N11's own entry flagged — now confirmed and the naming claim WITHDRAWN. What stands from N11: labels are a distinct register (the first-glyph distinctness result, untouched); what falls: that they are a section-specific NAMING system. A textbook case of a quarantined SUGGESTIVE finding killed by its own registered follow-up.**

## Run 2026-07-21 11:13:35 — N6i
**S3 rung 6: phonotactic attack on the interior-gradient residual (DOF-honest)**
- script: `scripts/line_discipline_phonotactic.py`
- profile: `{}`
- log: `overnight_2026-07-21.log`; results JSON: `line_discipline_phonotactic.json`; branch: `overnight/2026-07-21`
- runtime: 1s (0.00 h), exit code 0

**Pre-registered outcomes** (script docstring; DOF-honest RESIDUAL test — the interior axis lives over only ~13 classes, so a small declared phonotactic feature set is fit to the N6h residual and required to beat an OVERFITTING shuffle null that measures chance fit of 4 features to 13 points).

| quantity | value |
|---|---|
| N6h 5-principle interior R² | 0.6294 |
| phonotactic R² on residual | 0.7599 |
| overfitting null (mean / max) | 0.3274 / 0.8997 |
| excess over null mean | +0.432 (bar 0.15) |
| empirical p (null ≥ real) | 0.0205 |

Per-feature Spearman with the residual: succ_entropy +0.38, pred_entropy -0.05, e_follow -0.18, bench -0.26.

**VERDICT: RESIDUAL PHONOTACTIC (pre-registered criterion met, but a SOFT and DOF-fragile finding — read the caveat) — the phonotactic set explains 76% of the interior-gradient residual, +0.43 above the null MEAN, led by successor-entropy (Spearman 0.379): tightly-constrained-onset words (q→o) sit earlier, loosely-constrained later. So across the full ladder the interior gradient reduces to frequency + gallows + length + within-word morphology + glyph-neighbour phonotactics. CAVEATS, prominent: the empirical p is 0.0205 — ABOVE the program's usual p<0.005 bar — because the overfitting null is fat-tailed (max 0.8997): 4 features on 13 class-points is near the DOF limit. This is the WEAKEST SUGGESTIVE finding in the ledger; it is a class-level reductive result (same reductive/same-author caveats as the derivation arc), and a higher-resolution (glyph-pair) re-test at p<0.005 is the registered follow-up. SUGGESTIVE, quarantined.**

## Run 2026-07-21 11:56:31 — N6j
**S3 rung 6b: glyph-pair phonotactic re-test (class-controlled) — firm or dissolve N6i?**
- script: `scripts/line_discipline_phonotactic_token.py`
- profile: `{}`
- log: `overnight_2026-07-21.log`; results JSON: `line_discipline_phonotactic_token.json`; branch: `overnight/2026-07-21`
- runtime: 174s (0.05 h), exit code 0

**Pre-registered outcomes** (script docstring): the registered follow-up to N6i (its own entry flagged it as the weakest SUGGESTIVE finding needing a p<0.005 re-test). Onset successor-entropy is a deterministic function of the first glyph, so it cannot separate a phonotactic law from the S7 class-position effect; the correct test controls for onset class and asks whether glyph-PAIR constraint predicts position WITHIN classes.

| quantity | value |
|---|---|
| raw onset-se vs position (collinear w/ class) | +0.0574 |
| class-controlled glyph-pair partial r (THE TEST) | +0.0031 |
| two-sided within-line null p | 0.7046 (null max |r| 0.03312) |
| interior tokens (with glyph pair) | 14096 |

**VERDICT: PHONOTACTIC IS CLASS CONFOUND (N6i downgraded) — with onset class controlled, glyph-pair phonotactic constraint does NOT predict interior position (partial r +0.0031, p 0.7046 ≫ 0.05, on 14096 tokens — un-inflated). N6i's soft p=0.02 phonotactic signal was the onset-CLASS effect that successor-entropy trivially re-expresses (raw onset-se +0.0574 just mirrors the S7 class-position effect), NOT a phonotactic law. The interior-gradient residual is not demonstrably phonotactic once class is controlled — it remains genuinely unexplained. Ledger entry 21 corrected. A quarantined SUGGESTIVE finding (N6i, flagged as the weakest) downgraded by its own registered follow-up — the process working exactly as the flag intended.**
