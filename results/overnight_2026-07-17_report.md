# Overnight report — 2026-07-17

## Run 2026-07-17 11:45:30 — N1
**Max-strength verbose cipher inversion (rung 3: folio-level holdout, pre-registered budget)**
- script: `scripts/verbose_cipher_inversion.py`
- profile: `{'EM_OUTER': 32, 'EM_PROPOSALS': 48, 'EM_RESTARTS': 16, 'RESTARTS': 64, 'TOP_LMS_RUNG2': 3}`
- log: `overnight_2026-07-17.log`; results JSON: `verbose_cipher_inversion.json`; branch: `overnight/2026-07-17`
- runtime: 1410s (0.39 h), exit code 1

**RUN FAILED — partial report.** Traceback:

```
Traceback (most recent call last):
  File "C:\projects\vais\tools\overnight.py", line 566, in main
    raise RunFailed(f'experiment {"timed out" if timed_out else f"exited rc={rc}"}'
                    ' — see the child output above in the log')
RunFailed: experiment exited rc=1 — see the child output above in the log
```

## Run 2026-07-17 13:50:49 — N1
**Max-strength verbose cipher inversion (rung 3: folio-level holdout, pre-registered budget)**
- script: `scripts/verbose_cipher_inversion.py`
- profile: `{'EM_OUTER': 32, 'EM_PROPOSALS': 48, 'EM_RESTARTS': 16, 'RESTARTS': 64, 'TOP_LMS_RUNG2': 3}`
- log: `overnight_2026-07-17.log`; results JSON: `verbose_cipher_inversion.json`; branch: `overnight/2026-07-17`
- runtime: 970s (0.27 h), exit code 1

**RUN FAILED — partial report.** Traceback:

```
Traceback (most recent call last):
  File "C:\projects\vais\tools\overnight.py", line 572, in main
    raise RunFailed(f'experiment {"timed out" if timed_out else f"exited rc={rc}"}'
                    ' — see the child output above in the log')
RunFailed: experiment exited rc=1 — see the child output above in the log
```

## Run 2026-07-17 14:10:18 — N1
**Max-strength verbose cipher inversion (rung 3: folio-level holdout, pre-registered budget)**
- script: `scripts/verbose_cipher_inversion.py`
- profile: `{'EM_OUTER': 32, 'EM_PROPOSALS': 48, 'EM_RESTARTS': 16, 'RESTARTS': 64, 'TOP_LMS_RUNG2': 3}`
- log: `overnight_2026-07-17.log`; results JSON: `verbose_cipher_inversion.json`; branch: `overnight/2026-07-17`
- runtime: 6323s (1.76 h), exit code 0

**Pre-registered criteria** (verbose_cipher_inversion.py docstring; RESEARCH.md Phase 4b): instrument passes only if BOTH hold — P4 planted-inventory recovery >= 50% AND P4 best holdout gap beats the same-rung noise floor by >= 0.1 bits/sym. VMS rows are interpreted only if the instrument passes, and only as "consistent with", never "decoded".

| pre-registered check | threshold | actual | verdict |
|---|---|---|---|
| P4 inventory recovery (rung 2, latin/plain LM) | >= 50% | 39% (mapping accuracy 26%) | **FAIL** |
| P4 gap − noise floor (rung 2) | >= +0.100 bits/sym | -0.150 (gap +0.856 via latin/abbrev4, floor +1.007) | **FAIL** |

Rung-2 holdout gaps (folio-level holdout, this budget):

| corpus | best LM | gap (bits/sym) | gap − floor | holdout words excluded |
|---|---|---|---|---|
| P4_latin_verbose | latin/abbrev4 | +0.856 | -0.150 | 99.2% |
| P1_latin_plain | latin/abbrev4 | +0.012 | -0.995 | 80.6% |
| N2_char_shuffle | italian/abjad | +0.384 | -0.622 | 99.0% |
| N3_grille | latin/abjad | +1.007 | +0.000 | 99.6% |
| N4_self_citation | latin/abjad | +0.301 | -0.705 | 88.4% |
| VMS_full | latin/abbrev4 | -0.201 | -1.208 | 65.5% |
| VMS_currier_A | latin/abbrev4 | +0.369 | -0.638 | 70.8% |
| VMS_currier_B | latin/abbrev4 | +0.166 | -0.841 | 68.8% |

Rung 1 for the record: P4 segmenter inventory recovery 13%, best gap -0.773 vs rung-1 noise floor -0.660.

**VERDICT: INSTRUMENT KILLED (pre-registered).** At this budget, with the folio-holdout memorization leak closed, the strict 1:1 inverter still cannot invert a KNOWN verbose cipher clearly above what a free mapping extracts from meaningless text. Per the pre-registered protocol the VMS rows below are NOT interpretable (shown for the record only):

- VMS_full: best gap -0.201 (latin/abbrev4) — not interpretable, instrument killed
- VMS_currier_A: best gap +0.369 (latin/abbrev4) — not interpretable, instrument killed
- VMS_currier_B: best gap +0.166 (latin/abbrev4) — not interpretable, instrument killed

The compute rungs of the ladder are now exhausted. The next rung would relax model strictness (homophones / positional variants), which per the pre-registration requires a human-logged justification in the script docstring BEFORE any run — not an overnight decision.
