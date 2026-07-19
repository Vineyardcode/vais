# Overnight report — 2026-07-19

<!-- OVERNIGHT-SUGGESTIVE -->
> **SUGGESTIVE FINDING — AWAITING HUMAN REVIEW — DO NOT MERGE.**
> A run below produced a decode-like/positive signal. It is
> quarantined: committed only to its overnight/ branch, claims
> nothing beyond "consistent with", and is not a decode. See the
> flagged run section for the numbers and the pre-registered
> criteria they were judged against.

## Run 2026-07-19 00:17:09 — N3d
**Line-as-record rung 4 (portfolio S7): paragraph control + characterization of the Currier-B ordinal signal**
- script: `scripts/line_as_record_characterization.py`
- profile: `{}`
- log: `overnight_2026-07-19.log`; results JSON: `line_as_record_characterization.json`; branch: `overnight/2026-07-19`
- runtime: 225s (0.06 h), exit code 0

**Pre-registered structure** (script docstring): gate = rung-3 headline reproduced (verified); T-PARA = paragraph-initial lines excluded, significance-only battery (200 nulls, p < 0.0050); decomposition is descriptive only and adjudicates nothing.

T-PARA: 131 paragraph-initial lines excluded → 2391 kept; real +0.0519 vs null max -0.0017 (nulls ≥ real: 0, p = 0.0050) → **PASS**.

| interior bin | gain (bits/token) |
|---|---|
| m1 | +0.0816 |
| m2 | +0.0381 |
| m3 | +0.0299 |

| feature | gain |
|---|---|
| len | +0.0018 |
| first | +0.0296 |
| last | +0.0174 |
| gallows | +0.0024 |

| first glyph | support | contribution | skew m1/m2/m3 |
|---|---|---|---|
| q | 2908 | +0.0352 | 1.109/0.972/0.877 |
| c | 2413 | +0.0281 | 1.009/1.019/0.963 |
| o | 3529 | +0.0200 | 0.937/1.004/1.086 |
| d | 764 | -0.0151 | 0.918/1.001/1.117 |
| y | 516 | -0.0101 | 1.021/1.001/0.969 |
| t | 258 | -0.0095 | 0.873/0.972/1.216 |
| s | 1545 | -0.0075 | 1.096/1.056/0.793 |
| a | 877 | -0.0067 | 0.849/0.975/1.248 |

| last glyph | support | contribution | skew m1/m2/m3 |
|---|---|---|---|
| y | 6615 | +0.0191 | 1.039/1.005/0.936 |
| r | 2195 | +0.0086 | 0.885/0.968/1.205 |
| l | 2100 | +0.0082 | 0.986/1.025/0.99 |
| n | 2469 | -0.0039 | 1.008/0.998/0.992 |
| o | 294 | -0.0032 | 0.93/0.976/1.129 |
| s | 354 | -0.0005 | 1.016/0.879/1.123 |
| d | 226 | -0.0000 | 0.941/1.203/0.839 |

**VERDICT: CHARACTERIZED — the signal survives the paragraph control (the last registered structural threat); the tables above are the program's description of the Currier-B ordinal signal. SUGGESTIVE supporting detail for the quarantined finding; NOT a decode; no value is a translation.**

## Run 2026-07-19 01:53:52 — N3e
**Line-as-record rung 5 (portfolio S7): within-section replication (bio / recipes / other_B)**
- script: `scripts/line_as_record_section_split.py`
- profile: `{}`
- log: `overnight_2026-07-19.log`; results JSON: `line_as_record_section_split.json`; branch: `overnight/2026-07-19`
- runtime: 227s (0.06 h), exit code 0

**Pre-registered outcomes** (script docstring; human-directed section-confound test): per usable section PASS iff the real median beats ALL 200 within-line-shuffle nulls (p < 0.0050); taxonomy: folio-number: bio f75-84, recipes f103-116, other_B rest. Pooled rung-3 headline reproduced (gate).

| section | lines / folios | real gain | null max | nulls ≥ real | p | verdict |
|---|---|---|---|---|---|---|
| bio | 739 / 20 | +0.0106 | -0.0052 | 0 | 0.0050 | **PASS** |
| recipes | 1039 / 23 | +0.0584 | -0.0036 | 0 | 0.0050 | **PASS** |
| other_B | 744 / 34 | +0.0478 | -0.0077 | 0 | 0.0050 | **PASS** |

**VERDICT: SECTION-GENERAL — the ordinal signal replicates within every usable B section independently; the section-confound objection is dismissed. SUGGESTIVE supporting detail for the quarantined finding; not a decode.**

## Run 2026-07-19 02:40:29 — N4
**S5/S6 line-class family test: which calibrated process orders Currier B's lines?**
- script: `scripts/line_class_family_test.py`
- profile: `{}`
- log: `overnight_2026-07-19.log`; results JSON: `line_class_family_test.json`; branch: `overnight/2026-07-19`
- runtime: 4s (0.00 h), exit code 0

**Pre-registered rule** (script docstring): nearest family centroid with margin (d1 < 0.5 x d2) and an explicit none-of-the-above arm (F4); gate = centroids separate (> 2.0 x max split RMS). Profiles = normalized position-driven vs neighbor-driven class-sequence information, folio holdout, 10-split medians.

| corpus | r_pos | r_bi | split RMS | lines |
|---|---|---|---|---|
| P1_language | -0.0005 | +0.0013 | 0.0005 | 4755 |
| PREC_records | +0.3388 | +0.3217 | 0.0030 | 4600 |
| PNUM_positional | +0.3168 | +0.4636 | 0.0057 | 4600 |
| N4_hoax | +0.0427 | +0.2180 | 0.0050 | 2572 |
| N1_shuffle_ref | -0.0005 | -0.0010 | 0.0005 | 3956 |
| VMS_currier_B | +0.0354 | +0.0407 | 0.0048 | 2522 |
| VMS_currier_A | +0.0253 | +0.0256 | 0.0044 | 1310 |

Gate: min centroid separation 0.1436 vs required 0.0114 → PASS. B distances: family_language 0.0533, family_hoax 0.1775, family_records 0.4135, family_positional 0.5080.

**VERDICT: FAMILY_LANGUAGE** — B's line-class ordering profile is nearest the language reference with clear margin. A family-level reading only: nothing is decoded, and the S7 positional finding stands as the residual that separates B from the pure family centroid (real prose shows r_pos ~ 0; B does not).
