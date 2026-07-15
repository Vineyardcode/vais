# RESEARCH.md — VAIS assumption audit & machine-scale attack program

Branch: `research/machine-attacks`. Network: available (verified). This
document is the complete log: charter, assumption dependency matrix,
failure-mode catalog, strategy portfolio, prototype results, and the
established/suggestive/speculative ledger. Nothing below claims "decoded";
see the vocabulary discipline in the charter.

---

## Phase 0 — The anti-crackpot charter (binding)

1. **Controls before manuscript, always.** Every method runs on the control
   battery (below) before touching Voynich data. A method that "finds
   meaning" in a negative control is dead on the spot; the corpse is logged
   in this file with the score that killed it.
2. **Degrees of freedom are counted, not waved at.** Any pipeline with free
   choice of target language, anagramming, unconstrained abbreviation
   expansion, or post-hoc dictionary lookup carries enough DOF to "decode"
   arbitrary noise. Each strategy states its DOF budget explicitly.
3. **Held-out validation.** Development on one partition (section, scribal
   hand, Currier language), blind evaluation on another. Partitions are
   declared before any fitting.
4. **Kill criteria are pre-registered.** Every strategy states, in advance,
   the observation that would falsify it. Results reported against those
   criteria, not against criteria invented after seeing the numbers.
5. **Vocabulary discipline.** "Decoded" requires surviving controls +
   held-out validation + a skeptical reader of this file agreeing.
   Everything below that bar is "consistent with". Clean negative results
   that kill a hypothesis family are successes and are reported with the
   same prominence as positives.
6. **Prior AI "solutions" are case studies of failure** (Hauer & Kondrak
   2018 Hebrew-anagram; Cheshire 2019 "proto-Romance"), not prior art. The
   failure-mode catalog (Phase 2) explains precisely where each died; every
   strategy here states which failure modes it is *structurally* immune to.

### The control battery (deterministic, seeded; built by `phase108_controls_foundry`)

**Positive controls** (a good method should find these language-like /
correctly identify their generative class):
- P1 `latin_plain` — genuine classical/medieval Latin prose (Caesar, local
  corpus; medieval register cross-checked with Apicius' recipe Latin).
- P2 `italian_plain` — Dante (period vernacular).
- P3 `latin_subst` — P1 under a monoalphabetic substitution (period-plausible).
- P4 `latin_verbose` — P1 under a verbose cipher (letter → glyph-group,
  Naibbe-style tables reusing the phase72 machinery).
- P5 `latin_abjad` — P1 with vowels stripped (abjad-like consonantal text).
**Negative controls** (a good method must NOT find these language-like /
must identify their generative class):
- N1 `vms_word_shuffle` — Voynich tokens, word order shuffled corpus-wide.
- N2 `vms_char_shuffle` — Voynich characters shuffled within lines
  (destroys word structure, preserves char inventory).
- N3 `grille_table` — Rugg-style Cardan-grille pseudo-text generated from
  prefix/mid/suffix tables fitted to VMS morphology.
- N4 `self_citation` — Timm & Schinner-style copy-and-modify generation
  seeded with a few genuine VMS lines.

All controls are size-matched (~36-40k tokens) to the manuscript where the
statistic demands it.

### Immediate consequences adopted from the charter
- The existing suite's headline numbers (h2 ≈ 2 bits, Zipf α, slot grammar,
  25-class chunk alphabet) are hereby downgraded to **conditional
  results** — conditional on the assumption stack of Phase 1 — until the
  invariance tests of Phase 4 report.

### Phase 0 — COMPLETED. Foundry built, controls verified.

Infrastructure (all deterministic, sanity-checked):
- `scripts/common/fingerprint.py` — 17-feature statistical fingerprint
  (entropy stack, lexicon shape, positional rigidity, line effects,
  adjacency repetition, z-distance scorer). Hand-verified in
  `sanity_checks/checks_fingerprint.py` (levenshtein, entropy stack on
  deterministic streams, adjacency arithmetic, JSD edge cases) — ALL PASS.
- `scripts/phase108_controls_foundry.py` — builds all 9 controls into
  `data/controls/` (seed=108). **Byte-identical across reruns (verified).**
  Manifest: `results/phase108_controls_manifest.json`; fingerprints:
  `results/phase108_control_fingerprints.json`.

Calibration note (logged per charter rule on strawman rivals): the N4
self-citation generator needed its mutation repertoire widened
(substitution + glyph insert/delete + word duplicate/delete, 9 mods/copy)
before its vocabulary was rich enough to rival the manuscript (TTR 0.051 →
0.265 vs VMS 0.214). An under-mutated N4 would have lost any tournament for
being an artifact of this implementation, not for Timm & Schinner being wrong.

Designed-behavior verification (7/7 PASS):

| check | result |
|---|---|
| P3 substitution invisible to all structural features (== P1 to 1e-9) | PASS |
| N2 char-shuffle destroys conditional structure (h2 2.22 → 3.85) | PASS |
| N1 word-shuffle kills line effects (init JSD 0.149 → 0.001) | PASS |
| N1 word-shuffle kills adjacency texture (near 0.026 → 0.011) | PASS |
| N4 self-citation is repetition-rich (adj_near 0.212 vs Latin 0.0003) | PASS |
| P4 verbose cipher lowers h2_ratio vs plain (0.533 vs 0.823) | PASS |
| N3 grille is positionally rigid (pos_predict 0.780 vs 0.919) | PASS |

Control fingerprints (headline features; full table in results JSON):

| corpus | h2_ratio | pos_pred | ttr@5k | zipf α | line_init | adj_near |
|---|---|---|---|---|---|---|
| VMS (all) | **0.569** | 0.898 | 0.380 | 0.896 | **0.149** | 0.026 |
| P1 latin_plain | 0.823 | 0.919 | 0.421 | 0.807 | 0.001 | 0.000 |
| P2 italian_plain | 0.786 | 0.885 | 0.337 | 1.024 | 0.001 | 0.000 |
| P3 latin_subst | 0.823 | 0.919 | 0.421 | 0.807 | 0.001 | 0.000 |
| P4 latin_verbose | **0.533** | 0.949 | 0.421 | 0.807 | 0.000 | 0.001 |
| P5 latin_abjad | 0.877 | 0.849 | 0.322 | 0.866 | 0.000 | 0.001 |
| N1 word_shuffle | 0.569 | 0.898 | 0.378 | 0.896 | 0.001 | 0.011 |
| N2 char_shuffle | 0.986 | 0.992 | 0.954 | 0.637 | 0.002 | 0.000 |
| N3 grille | 0.675 | 0.780 | 0.181 | 0.532 | 0.000 | 0.002 |
| N4 self_citation | 0.813 | 0.877 | 0.350 | 0.638 | 0.107 | 0.212 |

**First observations (SUGGESTIVE tier — single seed, single cipher table,
recorded before any fitting):**
1. The verbose cipher P4 is the *only* positive control that reproduces the
   manuscript's anomalously low h2_ratio (0.533 vs VMS 0.569; every plain
   or substituted language sits ≥ 0.786). Low conditional entropy is the
   single most-cited "Voynich is weird" statistic; a period-plausible
   verbose cipher produces it for free.
2. My N4 exposes a tension inside the self-citation theory's parameter
   space: mutation rates high enough to match the manuscript's vocabulary
   richness produce ~8× too much adjacent-word similarity (0.212 vs 0.026).
   Whether Timm & Schinner's exact algorithm escapes this bind is precisely
   what phase109's tournament will quantify — but naive copy-modify cannot
   have both the lexicon and the texture.
3. No control reproduces the line-initial effect (VMS 0.149) except N4
   partially (0.107, inherited from copying whole genuine lines) — line
   effects are a hard discriminator and must be a scored feature in every
   tournament.
