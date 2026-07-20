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
