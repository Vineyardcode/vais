# Overnight report — 2026-07-18

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
