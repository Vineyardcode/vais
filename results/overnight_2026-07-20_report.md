# Overnight report — 2026-07-20

## Run 2026-07-20 01:46:02 — N7
**Part-D hapax re-adjudication: does language_vs_cipher's hapax clustering survive a paragraph-only corpus?**
- script: `scripts/hapax_locus_readjudication.py`
- profile: `{}`
- log: `overnight_2026-07-20.log`; results JSON: `hapax_locus_readjudication.json`; branch: `overnight/2026-07-20`
- runtime: 1s (0.00 h), exit code 0

**Pre-registered outcomes** (script docstring): Part D of language_vs_cipher replicated faithfully (gate = golden reproduction) and re-adjudicated by its OWN original thresholds (chi2 > 15.0; B classes) on a paragraph-only corpus. Same rules, cleaned data.

| policy | lines | tokens | hapaxes | chi2 (class) | B (class) |
|---|---|---|---|---|---|
| all | 4508 | 35747 | 1918 | 216.1 (CONCENTRATED) | +0.591 (CLUSTERED) |
| P_only | 4281 | 33309 | 1752 | 131.4 (CONCENTRATED) | +0.581 (CLUSTERED) |
| nonP_only | 227 | 2438 | 444 | 43.0 (CONCENTRATED) | +0.324 (CLUSTERED) |

**VERDICT: VERDICT SURVIVES — the hapax-clustering evidence is a property of the running text: decontamination removes ~39% of the chi2 statistic (the measured layout-artifact share) but every original classification holds. The contamination asterisk on Part D is removed by test.**

## Run 2026-07-20 12:22:19 — N6f
**S3 rung 3b: axis-3 characterization in hand A — absent, inverted, or shared?**
- script: `scripts/line_discipline_axis3_handA.py`
- profile: `{}`
- log: `overnight_2026-07-20.log`; results JSON: `line_discipline_axis3_handA.json`; branch: `overnight/2026-07-20`
- runtime: 6s (0.00 h), exit code 0

**Pre-registered outcomes** (script docstring): hand A's centered log-table projected onto B's FIXED N6d axes (no SVD on A — avoiding the component-mixing hazard behind N6e's −0.46), permutation null (200 within-line shuffles), model-free bin-level sign cross-check.

| axis | beta(A) | null max |beta| | significant |
|---|---|---|---|
| 1 | +0.753 | 0.106 | yes |
| 2 | +0.756 | 0.191 | yes |
| 3 | +0.324 | 0.785 | no |

Bin-level pre-final skew, A vs B: Spearman +0.559 (observational).

**VERDICT: AXIS 3 ABSENT IN A — no measurable pre-final-zone rule at A's sample size (the axis-3 direction is intrinsically noisy: wide null band). The point observations lean weakly SAME-direction, so N6e's −0.46 is resolved as component-mixing artifact, not inversion. Axis 3 remains B's own as far as A's data can resolve; ledger entry 15's "anti-transfers" reading is refined to "undetectable in A".**
