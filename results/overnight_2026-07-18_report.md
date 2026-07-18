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
