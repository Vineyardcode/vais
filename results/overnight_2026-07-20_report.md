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
