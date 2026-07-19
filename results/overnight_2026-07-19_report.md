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

## Run 2026-07-19 03:40:17 — N5
**S7-R: independent re-implementation of the intra-line ordinal measurement (rank statistic, PHASE8 §8.7-1)**
- script: `scripts/line_ordinal_rank_test.py`
- profile: `{}`
- log: `overnight_2026-07-19.log`; results JSON: `line_ordinal_rank_test.json`; branch: `overnight/2026-07-19`
- runtime: 66s (0.02 h), exit code 0

**Pre-registered ladder** (script docstring; answers PHASE8_DRAFT §8.7-1 at IMPLEMENTATION level — same-author caveat disclosed): rank statistic T = weighted between-class variance of mean interior rank, first-EVA-glyph classes, no bins / smoothing / holdout; inference by 1000 within-line permutations.

| corpus | T | perms ≥ T | p | lines |
|---|---|---|---|---|
| PREC_records | 0.029613 | 0 | 0.0010 | 4600 |
| P1_latin | 0.000106 | 132 | 0.1329 | 4755 |
| N1_shuffle | 0.000042 | 643 | 0.6434 | 3956 |
| VMS_currier_B | 0.000599 | 0 | 0.0010 | 2522 |
| VMS_currier_A | 0.001013 | 0 | 0.0010 | 1310 |

**VERDICT: REPLICATED — the intra-line class-ordering signal survives a methodologically disjoint instrument (B p < 0.005; and observationally, hand A also rejects under this more sensitive statistic). The shared-implementation-DNA objection is answered; author-level independence remains open and travels with the finding.**

B class mean interior ranks (early → late): sh 0.457, q 0.474, k 0.481, l 0.497, ch 0.498, y 0.500, o 0.518, d 0.522, t 0.530, s 0.531, a 0.536, r 0.561 — coherent with the rung-4 characterization (q-early), and the EVA-parsed sh class emerges as the earliest carrier.

## Run 2026-07-19 13:37:02 — N1c
**Verbose cipher inversion, rung 3c: Occitan LM extension (max-strength budget, coverage-penalized objective)**
- script: `scripts/verbose_cipher_inversion.py`
- profile: `{'EM_OUTER': 32, 'EM_PROPOSALS': 48, 'EM_RESTARTS': 16, 'RESTARTS': 64, 'TOP_LMS_RUNG2': 3}`
- log: `overnight_2026-07-19.log`; results JSON: `verbose_cipher_inversion.json`; branch: `overnight/2026-07-19`
- runtime: 5650s (1.57 h), exit code 0

**Pre-registered criteria** (verbose_cipher_inversion.py docstring; RESEARCH.md Phase 4b): instrument passes only if BOTH hold — P4 planted-inventory recovery >= 50% AND P4 best holdout gap beats the same-rung noise floor by >= 0.1 bits/sym. VMS rows are interpreted only if the instrument passes, and only as "consistent with", never "decoded".

| pre-registered check | threshold | actual | verdict |
|---|---|---|---|
| P4 inventory recovery (rung 2, latin/plain LM) | >= 50% | 65% (mapping accuracy 57%) | PASS |
| P4 gap − noise floor (rung 2) | >= +0.100 bits/sym | +0.350 (gap -0.512 via latin/plain, floor -0.862) | PASS |

Rung-2 holdout gaps (folio-level holdout, this budget):

| corpus | best LM | gap (bits/sym) | gap − floor | holdout words excluded |
|---|---|---|---|---|
| P4_latin_verbose | latin/plain | -0.512 | +0.350 | 12.9% |
| P1_latin_plain | latin/abbrev4 | -1.129 | -0.266 | 74.4% |
| N2_char_shuffle | latin/abjad | -0.994 | -0.131 | 87.8% |
| N3_grille | latin/abjad | -0.862 | +0.000 | 70.3% |
| N4_self_citation | latin/abjad | -0.922 | -0.060 | 78.3% |
| VMS_full | latin/abbrev4 | -0.880 | -0.018 | 43.8% |
| VMS_currier_A | latin/plain | -0.842 | +0.020 | 48.3% |
| VMS_currier_B | latin/abbrev4 | -0.895 | -0.033 | 49.4% |

Rung 1 for the record: P4 segmenter inventory recovery 13%, best gap -0.773 vs rung-1 noise floor -0.660.

**VERDICT: INSTRUMENT PASSED** — the known cipher was inverted above the noise floor at this rung. VMS rows, read under the pre-registered vocabulary:

- VMS_full: best gap -0.880 (latin/abbrev4) — within the noise floor: nothing beyond free-mapping noise at this rung (a clean negative for the strict 1:1 verbose-cipher family under these 6 LMs).
- VMS_currier_A: best gap -0.842 (latin/plain) — within the noise floor: nothing beyond free-mapping noise at this rung (a clean negative for the strict 1:1 verbose-cipher family under these 6 LMs).
- VMS_currier_B: best gap -0.895 (latin/abbrev4) — within the noise floor: nothing beyond free-mapping noise at this rung (a clean negative for the strict 1:1 verbose-cipher family under these 6 LMs).

## Run 2026-07-19 17:32:02 — N6
**S3 rung 2: line-discipline tournament — is B's line texture reducible to lexicon + table + one knob?**
- script: `scripts/line_discipline_tournament.py`
- profile: `{}`
- log: `overnight_2026-07-19.log`; results JSON: `line_discipline_tournament.json`; branch: `overnight/2026-07-19`
- runtime: 204s (0.06 h), exit code 0

**Pre-registered outcomes** (script docstring; a DIAGNOSTIC REDUCTION TEST, not a blind generator — the class-position table is measured from B, plus ONE strength knob fitted on one feature, frozen at LAMBDA=1.25). Bars are the phase-109 contiguous-halves convention.

| entrant | D_line (bar 7.489) | D_unfitted (bar 4.092) |
|---|---|---|
| G0_ablation | 21.56 | 1.854 |
| G1_discipline | 6.645 | 1.98 |
| G2_verbose_ref | 8.714 | 31.411 |

| feature | B | G0 | G1 |
|---|---|---|---|
| line_init_jsd | 0.2128 | 0.0017 | 0.2008 |
| line_final_jsd | 0.1063 | 0.0015 | 0.0017 |
| interior_gain | 0.0513 | -0.006 | 0.0425 |
| r_pos | 0.0406 | -0.0007 | 0.0387 |
| r_bi | 0.0496 | 0.0016 | 0.0323 |
| h2_ratio | 0.5141 | 0.5141 | 0.5141 |
| adj_dup | 0.009 | 0.0092 | 0.0096 |
| adj_near | 0.0341 | 0.0309 | 0.032 |

**VERDICT: LINE TEXTURE REDUCIBLE — Currier B's full line texture (edge effects AND interior ordinal residue) is statistically forgeable from its lexicon plus one measured class-position table and one strength knob, without breaking the unfitted order-sensitive features. SUGGESTIVE, quarantined. Scope: a mechanism-family claim about statistics — the phase-109 moat is reduced, not decoded; blind generation of the table is the registered future rung.**

## Run 2026-07-19 17:50:39 — N6b
**S3 rung 2b: table-compression test — is the discipline one latent axis?**
- script: `scripts/line_discipline_compression.py`
- profile: `{}`
- log: `overnight_2026-07-19.log`; results JSON: `line_discipline_compression.json`; branch: `overnight/2026-07-19`
- runtime: 56s (0.02 h), exit code 0

**Pre-registered outcomes** (script docstring): rank-1 SVD compression of the N6 discipline table (deterministic, no search), same bars and machinery as N6 (all cross-checked at runtime), one re-fitted knob (LAMBDA=2.0). Rank-1 variance share: 85.7%.

| entrant | D_line (bar 7.489) | D_unfitted (bar 4.092) |
|---|---|---|
| G1 full table (N6) | 6.645 | 1.98 |
| G1b rank-1 table | 9.529 | 2.0 |

Class axis A (low → high): a -0.994, ch -0.783, sh -0.416, l -0.385, o -0.339, k -0.332, # -0.247, q -0.141, d +0.387, y +0.533, t +0.672, s +0.760, p +1.285.
Position profile V: p1 +2.114, p2 -0.627, m1 -0.360, m2 -0.332, m3 -0.144, pL-1 -0.275, pL -0.376.
Observational axis correlations (declared predictors): log_class_freq -0.648, mean_word_len +0.165, gallows_initial +0.593.

**VERDICT: NOT COMPRESSIBLE — one latent axis does not reproduce the line texture (the dominant axis is the EDGE/paragraph axis; the interior ordering is a second, independent dimension). The discipline is at least rank-2; corpse logged with coordinates.**

## Run 2026-07-19 18:18:17 — N6c
**S3 rung 2c: rank-2 test — do two axes complete the discipline?**
- script: `scripts/line_discipline_rank2.py`
- profile: `{}`
- log: `overnight_2026-07-19.log`; results JSON: `line_discipline_rank2.json`; branch: `overnight/2026-07-19`
- runtime: 59s (0.02 h), exit code 0

**Pre-registered outcomes** (script docstring): rank-2 SVD reconstruction (deterministic; declared sign convention), N6 machinery/bars cross-checked, one re-fitted knob (LAMBDA=1.75). Rank-2 variance share: 97.0%.

| entrant | D_line (bar 7.489) | D_unfitted (bar 4.092) |
|---|---|---|
| G1 full table (N6) | 6.645 | 1.98 |
| G1b rank-1 (N6b) | 9.529 | 2.0 |
| G1c rank-2 | 8.12 | 2.421 |

Axis 2 (interior, low → high): sh -0.868, q -0.372, k -0.214, ch -0.205, p -0.183, t -0.145, y -0.132, o +0.097, l +0.293, s +0.299, a +0.366, d +0.478, # +0.585.
Observational correlations: axis2_vs_n5_mean_ranks +0.800, axis1_vs_log_class_freq +0.648, axis2_vs_log_class_freq -0.220, axis1_vs_gallows_initial -0.593, axis2_vs_gallows_initial -0.577.

**VERDICT: STILL NOT COMPRESSIBLE — two axes (96.9% of the table) do not close the line group at the tournament bar; the discipline carries tournament-relevant structure beyond rank 2. Note the convergence ladder (rank-1 → rank-2 → full) and that axis 2 independently reproduces the N5 interior ordering (ρ = +0.80).**

## Run 2026-07-19 20:54:39 — N6d
**S3 rung 2d: rank-3 test — do three axes complete the discipline?**
- script: `scripts/line_discipline_rank3.py`
- profile: `{}`
- log: `overnight_2026-07-19.log`; results JSON: `line_discipline_rank3.json`; branch: `overnight/2026-07-19`
- runtime: 101s (0.03 h), exit code 0

**Pre-registered outcomes** (script docstring): rank-3 SVD reconstruction, N6 machinery/bars cross-checked, one re-fitted knob (LAMBDA=1.5). Rank-3 variance share: 98.4%.

| entrant | D_line (bar 7.489) | D_unfitted (bar 4.092) |
|---|---|---|
| G1 full table (N6) | 6.645 | 1.98 |
| G1b rank-1 (N6b) | 9.529 | 2.0 |
| G1c rank-2 (N6c) | 8.12 | 2.421 |
| G1d rank-3 | 6.882 | 2.115 |

Axis 3 (pre-final zone, low → high): y -0.340, s -0.306, sh -0.285, l -0.217, d -0.169, # +0.061, q +0.068, k +0.073, o +0.079, ch +0.158, t +0.215, a +0.230, p +0.436.
Profile 3: p1 -0.092, p2 -0.248, m1 -0.169, m2 -0.147, m3 +0.618, pL-1 +0.334, pL -0.295.
Observational correlations: axis2_vs_n5_mean_ranks +0.800, axis3_vs_n5_mean_ranks +0.309, axis1_vs_log_class_freq +0.648, axis2_vs_log_class_freq -0.220, axis3_vs_log_class_freq -0.088, axis1_vs_gallows_initial -0.593, axis2_vs_gallows_initial -0.577, axis3_vs_gallows_initial +0.033.

**VERDICT: THREE AXES SUFFICIENT — Currier B's line discipline compresses to three interpretable axes plus one knob (~55 numbers vs the 91-cell table): the edge/paragraph axis, the interior early-late gradient (= the N5 residue, ρ +0.80), and a previously unnamed PRE-FINAL-ZONE axis (peaks m3/pL-1, not pL; uncorrelated with the declared predictors). SUGGESTIVE, quarantined; a compression of statistics, not a decode. Deriving each axis from independent principles is the registered blind-generation rung.**

## Run 2026-07-19 21:16:48 — N6e
**S3 rung 3: cross-hand blind test — does an A-measured table place B's lines?**
- script: `scripts/line_discipline_transfer.py`
- profile: `{}`
- log: `overnight_2026-07-19.log`; results JSON: `line_discipline_transfer.json`; branch: `overnight/2026-07-19`
- runtime: 103s (0.03 h), exit code 0

**Pre-registered outcomes** (script docstring; blind WITH RESPECT TO B — the table is measured on Currier A only (1310 lines), B contributes its lexicon and the single knob, fitted LAMBDA=1.75 vs B's own 1.25).

| entrant | D_line (bar 7.489) | D_unfitted (bar 4.092) |
|---|---|---|
| G1 B-table (N6) | 6.645 | 1.98 |
| G1e A-table | 8.282 | 1.194 |

Per-axis transfer (Spearman, A-table vs B-table rank-3 axes): axis1 +0.923, axis2 +0.830, axis3 -0.462.

**VERDICT: NOT TRANSFERABLE — the A-measured table does not close B's line group at any knob setting. The per-axis profile localizes the failure: the edge axis (+0.92) and interior gradient (+0.83) ARE manuscript-wide (shared shape, strength-scaled — the switch picture holds for them); the pre-final-zone axis ANTI-transfers (−0.46) and is B-specific. The hand difference is intensity on two shared rules PLUS one qualitatively B-own rule. Corpse logged.**
