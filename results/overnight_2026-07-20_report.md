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

## Run 2026-07-20 15:46:29 — N8
**S2 rung 0: raw-scan glyph feasibility probe (numpy+Pillow, no CV stack)**
- script: `scripts/scan_glyph_feasibility.py`
- profile: `{}`
- log: `overnight_2026-07-20.log`; results JSON: `scan_glyph_feasibility.json`; branch: `overnight/2026-07-20`
- runtime: 37s (0.01 h), exit code 0

**Pre-registered verdicts** (script docstring): a rung-0 imaging probe of S2 with in-repo scans and numpy+Pillow only — the question is whether transliteration-free analysis can get off the ground, not anything about the manuscript's content.

G1 binarization: median ink 0.1904, CV 0.288 → PASS. G2 segmentation: Spearman(components, ZL chars) +0.842 over 30 folios (strong ≥ 0.8). G3: k* [10, 15] (FAIL ±30%), centroid ratio 0.395 (PASS < 0.5). 21214 glyph-scale components.

**VERDICT: PARTIALLY FEASIBLE — the pipeline reliably SEES the writing (count correlation +0.84 with the transliteration through drawings and all), but glyph-shape cluster counts are unstable across folio halves (the F10 concern, at rung 0). S2 proceeds restricted: better shape descriptors / a real CV stack / text-only pages.**

## Run 2026-07-20 23:21:32 — N9
**Hapax-clustering discriminator calibration: does "clustered → language" separate the control classes?**
- script: `scripts/hapax_clustering_calibration.py`
- profile: `{}`
- log: `overnight_2026-07-20.log`; results JSON: `hapax_clustering_calibration.json`; branch: `overnight/2026-07-20`
- runtime: 1s (0.00 h), exit code 0

**Pre-registered outcomes** (script docstring): Part D reads hapax burstiness B > 0.1 as "language". This calibration runs that exact statistic on the control battery. Hapax = strict count==1 on the collapsed vocabulary (Part D's definition, NOT relaxed to "rare words").

| corpus | class | burstiness B | hapax rate | TTR |
|---|---|---|---|---|
| P1_latin | language+ | +0.068 | 0.129 | 0.226 |
| P2_italian | language+ | +0.007 | 0.103 | 0.17 |
| P4_verbose_cipher | cipher | +0.062 | 0.136 | 0.233 |
| N3_grille | nonlang- | n/a (<10 hapax) | — | — |
| N4_self_citation | nonlang- | +0.272 | 0.09 | 0.184 |
| VMS_wordshuffle | reference | +0.051 | 0.058 | 0.097 |

**VERDICT: INCONCLUSIVE by the pre-registered criteria — which required the language positives to cluster, and they do NOT (Latin +0.068, Italian +0.007, both below 0.1). The controls are single-work corpora with no manuscript-like sections, so they cannot exhibit *topical* hapax clustering; the battery as built cannot fully test the topical version of the claim. But two observations (reported, not re-adjudicated) independently undermine Part D's inference as stated: (a) high hapax burstiness is NOT an intrinsic property of language text — real Latin/Italian sit near zero; (b) a NON-language hoax control (N4 self-citation, B +0.272) clusters more strongly than anything else, so burstiness alone is not diagnostic of language. Net: Part D's "clustered → language" inference is uncalibrated and unsupported by these controls; a properly powered re-test needs multi-topic language and cipher corpora (a registered future rung). Ledger entry 14 — which claims only that the VMS clustering is real and locus-robust, never that it proves language — is unaffected and now carries a pointer to this result.**

## Run 2026-07-20 23:45:27 — N10
**Egyptian determinative test: are the gallows semantic determinatives, or dialectal vocabulary?**
- script: `scripts/egyptian_determinative_test.py`
- profile: `{}`
- log: `overnight_2026-07-20.log`; results JSON: `egyptian_determinative_test.json`; branch: `overnight/2026-07-20`
- runtime: 6s (0.00 h), exit code 0

**Pre-registered outcomes** (script docstring): the Egyptian core claim (gallows = semantic determinatives) tested by its discriminating signature — a determinative predicts SECTION more than the phonetic root does; dialect predicts the reverse. U*(X) = section-predictiveness above a cardinality-shuffle null.

| corpus | U*(gallows) | U*(root) | reading |
|---|---|---|---|
| P-DET control | +0.99980 | +0.00004 | gallows-carried |
| P-DIA control | +0.00001 | +0.93755 | root-carried |
| VMS pooled | +0.00576 | +0.13030 | root-carried |
| VMS Currier A | +0.01162 | +0.12253 | root-carried |
| VMS Currier B | +0.00694 | +0.10015 | root-carried |

Gate (controls separate the mechanisms): PASS.
**VERDICT: DIALECT, NOT DETERMINATIVE — the section information lives in the ROOT vocabulary (pooled U* 0.130), not the gallows (0.006); a ~23× gap matching the dialect control. The gallows-section association the pre-charter test read as "determinatives" is dialectal vocabulary variation. The Egyptian determinative claim is KILLED on its core prediction — now with controls, where the old test had none.**
