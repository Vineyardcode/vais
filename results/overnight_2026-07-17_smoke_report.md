# Overnight report — 2026-07-17

## Run 2026-07-17 11:39:27 — N1 (SMOKE REHEARSAL — tiny budget, not science)
**Max-strength verbose cipher inversion (rung 3: folio-level holdout, pre-registered budget)**
- script: `scripts/verbose_cipher_inversion.py`
- profile: `{'EM_OUTER': 1, 'EM_PROPOSALS': 1, 'EM_RESTARTS': 1, 'RESTARTS': 2, 'TOP_LMS_RUNG2': 1}`
- log: `overnight_2026-07-17_smoke.log`; results JSON: `verbose_cipher_inversion.json`; branch: `overnight/2026-07-17-smoke`
- runtime: 15s (0.00 h), exit code 0

**Pre-registered criteria** (verbose_cipher_inversion.py docstring; RESEARCH.md Phase 4b): instrument passes only if BOTH hold — P4 planted-inventory recovery >= 50% AND P4 best holdout gap beats the same-rung noise floor by >= 0.1 bits/sym. VMS rows are interpreted only if the instrument passes, and only as "consistent with", never "decoded".

| pre-registered check | threshold | actual | verdict |
|---|---|---|---|
| P4 inventory recovery (rung 2, latin/plain LM) | >= 50% | 48% (mapping accuracy 26%) | **FAIL** |
| P4 gap − noise floor (rung 2) | >= +0.100 bits/sym | -0.136 (gap -0.057 via latin/abjad, floor +0.079) | **FAIL** |

Rung-2 holdout gaps (folio-level holdout, this budget):

| corpus | best LM | gap (bits/sym) | gap − floor |
|---|---|---|---|
| P4_latin_verbose | latin/abjad | -0.057 | -0.136 |
| P1_latin_plain | latin/plain | -0.486 | -0.565 |
| N2_char_shuffle | latin/abjad | -0.316 | -0.395 |
| N3_grille | latin/abjad | -0.382 | -0.461 |
| N4_self_citation | latin/abjad | +0.079 | +0.000 |
| VMS_full | latin/plain | -0.331 | -0.410 |
| VMS_currier_A | latin/abbrev4 | +0.264 | +0.185 |
| VMS_currier_B | latin/plain | -0.415 | -0.494 |

Rung 1 for the record: P4 segmenter inventory recovery 13%, best gap -0.773 vs rung-1 noise floor -0.660.

**VERDICT: INSTRUMENT KILLED (pre-registered).** At this budget, with the folio-holdout memorization leak closed, the strict 1:1 inverter still cannot invert a KNOWN verbose cipher clearly above what a free mapping extracts from meaningless text. Per the pre-registered protocol the VMS rows below are NOT interpretable (shown for the record only):

- VMS_full: best gap -0.331 (latin/plain) — not interpretable, instrument killed
- VMS_currier_A: best gap +0.264 (latin/abbrev4) — not interpretable, instrument killed
- VMS_currier_B: best gap -0.415 (latin/plain) — not interpretable, instrument killed

The compute rungs of the ladder are now exhausted. The next rung would relax model strictness (homophones / positional variants), which per the pre-registration requires a human-logged justification in the script docstring BEFORE any run — not an overnight decision.

---
*Smoke mode: the following RESEARCH.md section was generated but NOT appended:*

### Phase 4c — Verbose cipher inversion, rung 3: max strength + folio-level holdout (2026-07-17)

[AUTOMATED — written by tools/overnight.py, smoke rehearsal; run committed to branch overnight/2026-07-17-smoke; awaiting human review before promotion to any evidence tier.]

Budget (pre-registered in the script docstring): {'EM_OUTER': 1, 'EM_PROPOSALS': 1, 'EM_RESTARTS': 1, 'RESTARTS': 2, 'TOP_LMS_RUNG2': 1}. Runtime 0.00 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folios (controls), closing the rung-2 Currier-A memorization leak.

**Pre-registered criteria** (verbose_cipher_inversion.py docstring; RESEARCH.md Phase 4b): instrument passes only if BOTH hold — P4 planted-inventory recovery >= 50% AND P4 best holdout gap beats the same-rung noise floor by >= 0.1 bits/sym. VMS rows are interpreted only if the instrument passes, and only as "consistent with", never "decoded".

| pre-registered check | threshold | actual | verdict |
|---|---|---|---|
| P4 inventory recovery (rung 2, latin/plain LM) | >= 50% | 48% (mapping accuracy 26%) | **FAIL** |
| P4 gap − noise floor (rung 2) | >= +0.100 bits/sym | -0.136 (gap -0.057 via latin/abjad, floor +0.079) | **FAIL** |

Rung-2 holdout gaps (folio-level holdout, this budget):

| corpus | best LM | gap (bits/sym) | gap − floor |
|---|---|---|---|
| P4_latin_verbose | latin/abjad | -0.057 | -0.136 |
| P1_latin_plain | latin/plain | -0.486 | -0.565 |
| N2_char_shuffle | latin/abjad | -0.316 | -0.395 |
| N3_grille | latin/abjad | -0.382 | -0.461 |
| N4_self_citation | latin/abjad | +0.079 | +0.000 |
| VMS_full | latin/plain | -0.331 | -0.410 |
| VMS_currier_A | latin/abbrev4 | +0.264 | +0.185 |
| VMS_currier_B | latin/plain | -0.415 | -0.494 |

Rung 1 for the record: P4 segmenter inventory recovery 13%, best gap -0.773 vs rung-1 noise floor -0.660.

**VERDICT: INSTRUMENT KILLED (pre-registered).** At this budget, with the folio-holdout memorization leak closed, the strict 1:1 inverter still cannot invert a KNOWN verbose cipher clearly above what a free mapping extracts from meaningless text. Per the pre-registered protocol the VMS rows below are NOT interpretable (shown for the record only):

- VMS_full: best gap -0.331 (latin/plain) — not interpretable, instrument killed
- VMS_currier_A: best gap +0.264 (latin/abbrev4) — not interpretable, instrument killed
- VMS_currier_B: best gap -0.415 (latin/plain) — not interpretable, instrument killed

The compute rungs of the ladder are now exhausted. The next rung would relax model strictness (homophones / positional variants), which per the pre-registration requires a human-logged justification in the script docstring BEFORE any run — not an overnight decision.

The corpse is logged with the same prominence as a positive, per charter rule 5. Compute escalation is now exhausted for the strict 1:1 model; relaxing strictness (homophones / positional variants) is the only rung left and requires a human-logged justification before any run.
