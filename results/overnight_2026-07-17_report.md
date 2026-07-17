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
