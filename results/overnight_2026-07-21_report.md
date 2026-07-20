# Overnight report — 2026-07-21

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
