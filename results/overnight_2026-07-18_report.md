# Overnight report — 2026-07-18

<!-- OVERNIGHT-SUGGESTIVE -->
> **SUGGESTIVE FINDING — AWAITING HUMAN REVIEW — DO NOT MERGE.**
> A run below produced a decode-like/positive signal. It is
> quarantined: committed only to its overnight/ branch, claims
> nothing beyond "consistent with", and is not a decode. See the
> flagged run section for the numbers and the pre-registered
> criteria they were judged against.

## Run 2026-07-18 00:44:33 — N3
**Line-as-record structures (portfolio S7): interior positional-field information**
- script: `scripts/line_as_record_structures.py`
- profile: `{}`
- log: `overnight_2026-07-18.log`; results JSON: `line_as_record_structures.json`; branch: `overnight/2026-07-18`
- runtime: 2s (0.00 h), exit code 0

**Pre-registered gates** (line_as_record_structures.py docstring): instrument gate P-REC >= 0.3 and P1 <= 0.05 interior bits/token; kill if VMS_full − N1 < 0.05; positive only if all three VMS rows clear the margin (F8 concordance). Headline is INTERIOR gain — the line edges are the already-established anomaly.

| corpus | interior gain (bits/token) | edge gain | margin over N1 |
|---|---|---|---|
| PREC_records | +0.7189 | +1.6007 | — |
| P1_latin_plain | -0.0033 | -0.0063 | — |
| N1_word_shuffle | -0.0083 | -0.0060 | — |
| N3_grille | -0.0042 | -0.0050 | — |
| VMS_full | +0.0246 | +0.3598 | +0.0329 |
| VMS_currier_A | -0.0138 | +0.2869 | -0.0055 |
| VMS_currier_B | +0.0685 | +0.4379 | +0.0768 |

Instrument gate: P-REC +0.7189, P1 -0.0033 → PASS.

**VERDICT: KILLED (pre-registered): VMS_full interior margin +0.0329 < 0.05 — interior positional structure is not distinguishable from a line-length artifact at this instrument. The moat stays at the line EDGES.**

Observation for the record (NO claim, not adjudicated here): Currier B alone clears the margin (+0.0768) while A shows none (-0.0055) — consistent with the "B is the more systematized register" thread. A per-hand adjudication would need its own pre-registration in a future rung.

## Run 2026-07-18 01:50:40 — N3b
**Line-as-record rung 2 (portfolio S7): per-hand adjudication with per-hand null batteries**
- script: `scripts/line_as_record_per_hand.py`
- profile: `{}`
- log: `overnight_2026-07-18.log`; results JSON: `line_as_record_per_hand.json`; branch: `overnight/2026-07-18`
- runtime: 94s (0.03 h), exit code 0

**Pre-registered outcomes** (line_as_record_per_hand.py docstring, full post-hoc provenance disclosed there): a hand passes only if its 10-split median interior gain beats ALL 20 of its own null-shuffle medians (empirical p ~ 0.048) AND clears the 0.05 bits/token effect floor over the null median — strictly harder than the rung-1 observation that motivated this rung.

| corpus | median gain (bits/token) | null max | null median | margin | pass |
|---|---|---|---|---|---|
| PREC_records | +0.7471 | — | — | — | gate |
| P1_latin_plain | -0.0039 | — | — | — | gate |
| VMS_currier_A | +0.0113 | -0.0132 | -0.0187 | +0.0301 | fail |
| VMS_currier_B | +0.0513 | -0.0043 | -0.0067 | +0.0580 | **PASS** |

Instrument gate: P-REC +0.7471, P1 -0.0039 → PASS.

**VERDICT: B ONLY — consistent with line-level field structure in Currier B (SUGGESTIVE, quarantined; the first registered test of the rung-1 observation). NOT a decode; no field is named or read.**

## Run 2026-07-18 17:23:49 — N3c
**Line-as-record rung 3 (portfolio S7): composition vs ordinal structure in Currier B**
- script: `scripts/line_as_record_ordinal.py`
- profile: `{}`
- log: `overnight_2026-07-18.log`; results JSON: `line_as_record_ordinal.json`; branch: `overnight/2026-07-18`
- runtime: 97s (0.03 h), exit code 0

**Pre-registered ladder** (line_as_record_ordinal.py docstring; Currier B adjudicated, A observational): T1 composition (folio-nulls), T2 ordinal (line-nulls), T3 glyph-only (line-nulls); each = beat ALL 20 nulls AND clear the floor (0.05 total / 0.025 glyph). P-JUST (width-broken Latin) is the justification reference, not a gate.

| corpus | total (bits/token) | glyph | len |
|---|---|---|---|
| PREC_records | +0.7288 | +0.7215 | +0.0068 |
| P1_latin_plain | -0.0045 | -0.0043 | +0.0004 |
| PJUST_justified | +0.0133 | +0.0039 | +0.0099 |
| VMS_currier_A | +0.0100 | +0.0085 | -0.0016 |
| VMS_currier_B | +0.0513 | +0.0524 | +0.0018 |

| B test | margin | null max | verdict |
|---|---|---|---|
| T1 composition | +0.0571 | -0.0041 | **PASS** |
| T2 ordinal | +0.0577 | -0.0032 | **PASS** |
| T3 glyph-only | +0.0571 | -0.0019 | **PASS** |

**VERDICT: ORDINAL GLYPH STRUCTURE — Currier B's intra-line word order carries glyph-identity signal beyond composition and beyond length-based space management: consistent with field-like vocabulary ordering. SUGGESTIVE, quarantined, NOT a decode; no field is named or read.**

Observation (A, not adjudicated): total +0.0100 (glyph +0.0085) — same glyph-dominated shape at ~1/5 the strength, above all its nulls but under the floors: the hand gradient persists at rung 3.

## Run 2026-07-18 17:36:57 — N2
**Cross-transliteration invariance audit (portfolio S9): A1 fingerprint spread + S7-B ordinal invariance**
- script: `scripts/cross_transliteration_invariance.py`
- profile: `{}`
- log: `overnight_2026-07-18.log`; results JSON: `cross_transliteration_invariance.json`; branch: `overnight/2026-07-18`
- runtime: 73s (0.02 h), exit code 0

**Pre-registered outcomes** (script docstring): gate = ZL passes the S7-B ordinal battery with alphabet-agnostic features; then robust / partial / artifact_suspect over usable alternatives (usable = >= 500 B-lines). Part 1 flags fingerprint features deviating > 20% from ZL.

| transliteration | B-lines | median gain | null max | margin | battery |
|---|---|---|---|---|---|
| ZL | 2522 | +0.0442 | -0.0031 | +0.0501 | **PASS** |
| CD | 991 | +0.0094 | -0.0115 | +0.0326 | fail |
| GC | 2365 | +0.0372 | -0.0088 | +0.0487 | fail |
| FG | 2259 | +0.0475 | -0.0027 | +0.0534 | **PASS** |
| IT | 2329 | +0.0475 | -0.0032 | +0.0529 | **PASS** |

Part 1: flagged transliteration-sensitive features: {'mean_wlen': ['GC'], 'line_init_jsd': ['GC'], 'line_final_jsd': ['CD']}.

**VERDICT: PARTIAL — the signal passes in some readings and misses in others; sensitive to reading choices. Investigation required before any promotion of the rung-3 finding.**

Observation for the investigation (no claim): every usable transliteration beats ALL its nulls (empirical p bar 5/5); the misses are effect-floor misses only — whether a fixed bits/token floor mechanically penalizes finer-grained alphabets (GC: 162 symbols, miss by 0.0013) is the registered question for the follow-up.

## Run 2026-07-18 20:26:05 — N2b
**S9 follow-up: sensitivity-normalized effect floors (floor-scaling hypothesis test)**
- script: `scripts/transliteration_floor_calibration.py`
- profile: `{}`
- log: `overnight_2026-07-18.log`; results JSON: `transliteration_floor_calibration.json`; branch: `overnight/2026-07-18`
- runtime: 139s (0.04 h), exit code 0

**Pre-registered outcomes** (script docstring; written with full disclosure AFTER N2's PARTIAL): floors scale by MEASURED sensitivity rho (planted sort implant, ZL anchor, symmetric — floors may rise), battery values inherited from N2's exact seed streams and cross-checked.

| reading | margin | implant response | rho | normalized floor | verdict (was, fixed 0.05) |
|---|---|---|---|---|---|
| ZL | +0.0501 | +0.5806 | 1.0000 | 0.0500 | PASS (PASS) |
| CD | +0.0326 | +0.6490 | 1.1178 | 0.0559 | fail (fail) |
| GC | +0.0487 | +0.6488 | 1.1175 | 0.0559 | fail (fail) |
| FG | +0.0534 | +0.6812 | 1.1733 | 0.0587 | fail (PASS) |
| IT | +0.0529 | +0.5632 | 0.9700 | 0.0485 | PASS (PASS) |

**VERDICT: REFERENCE FLIP — symmetric normalization flipped a previously-passing reading by RAISING its floor: the normalized-floor instrument is not consistent enough to re-adjudicate at these margins. No claim; N2 PARTIAL unchanged. The registered question IS answered: measured sensitivities refute the "finer alphabets are mechanically penalized" hypothesis (GC rho > 1).**
