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

---

## Phase 1 — The assumption stack

Every decipherment attempt of the last century, and every one of this
suite's 129 tests, stands on some subset of seven assumptions. None of them
is established. This section names them, states what would break if each
fails, and reports the first measured results of poking at the bottom one.

### The stack, bottom to top

**A1 — The transliteration IS the text.** The suite analyzes the ZL
(Zandbergen-Landini) EVA transliteration, IVTFF v3b, 201 folio files —
i.e., one team's reading, through one alphabet's ontology. EVA itself is a
*convention*: it decides that 'ch' is two letters, that 'iin' is three,
that a gallows glyph is one unit. Character-level statistics (h2 ≈ 2 bits,
positional rigidity, the 25-class chunk alphabet) are statements about
*EVA strings*, not about the manuscript, until proven invariant across
transliterations and alphabet re-codings (phase110's job).

**A2 — Spaces are word boundaries.** 2,879 of the manuscript's spaces are
marked *uncertain* (`,` in IVTFF) — ~7% of all boundaries. The suite treats
them identically to certain spaces. Every word-level statistic (Zipf,
Heaps, TTR, morphology, slot grammar) inherits this choice.

**A3 — Lines read linearly, left to right, and adjacent tokens are
syntactically related.** All bigram/MI/Markov statistics assume it. The
strong line-position effects (measured: line_init_jsd 0.164 vs ~0.001 for
prose) are themselves evidence that the line is a stronger unit than the
"sentence flowing across lines" model implies.

**A4 — Every glyph carries signal.** No test in the suite models nulls,
padding, or decoration. If ~20% of glyphs were nulls (period-attested
practice), every entropy and morphology number changes.

**A5 — It is language at all.** 49/89 data-touching scripts compare against
natural-language references; the comparison is only meaningful under A5.
The negative controls N3/N4 exist precisely because A5 might be false.

**A6 — One system throughout.** 70/89 scripts pool the whole corpus.
Currier A and B differ enough that pooling may average two different
systems into a statistical chimera (the phase101 result — 0.94 LOO
separability — makes pooling actively dangerous).

**A7 — Page and section structure is original and meaningful.** 59/89
scripts use section labels (herbal/bio/...) or folio identity. Codicology
says the current binding order is NOT original (quire signatures added
later); section labels come from illustrations, not text.

### Finding T1 — the bottom assumption failed concretely (ESTABLISHED)

The naive loaders (all four legacy families) mishandle IVTFF markup:

- Page-metadata comments (`<! $Q=S $P=C $F=b $L=A ...>`) leaked phantom
  tokens: 'la' ×119, 'ih' ×135, 'fb', 'fz', 'qt'... — **878 phantom types**.
- Alternate readings were fused: `chofa[r:n]y` → nonexistent 'chofarny'
  (827 groups).
- Words containing illegible glyphs were silently truncated into phantom
  forms; genuine single-glyph words (standalone 'y', 's', 'o') were
  dropped (2,389 tokens, 5.6%).
- Net: **~2,168 tokens (5.4%) of the analyzed "manuscript" was markup
  artifact, and the manuscript's type count was inflated 13.6%**
  (8,842 naive → 7,643 clean).

Fix: `common.core.load_folio_lines_ivtff()` + pure cleaner
`ivtff_clean_words()` (policy documented in-code; hand-verified in
`sanity_checks/checks_ivtff.py`). Legacy loaders left untouched — the 129
golden outputs remain valid as *records of what was computed*; all research
phases (108+) use the clean loader. Controls rebuilt clean; designed-behavior
checks re-run: 7/7 PASS.

**Sensitivity of headline features to the loader** (naive vs IVTFF-clean vs
comma-join; full table `results/phase108b_loader_sensitivity.json`):

| feature | naive | ivtff | comma-join | max shift |
|---|---|---|---|---|
| h2_ratio | 0.569 | 0.546 | 0.548 | 4.1% |
| pos_predict | 0.898 | 0.851 | 0.877 | 5.3% |
| ttr_5000 | 0.380 | 0.361 | 0.406 | 6.9% |
| zipf_alpha | 0.896 | 0.929 | 0.897 | 3.7% |
| line_init_jsd | 0.149 | 0.164 | 0.164 | 10.2% |
| line_final_jsd | 0.094 | 0.084 | 0.079 | 15.8% |

Verdict: the suite's *qualitative* anomalies survive cleaning (low h2,
line effects — which actually strengthen, adjacency texture). Its
*vocabulary-size* claims were inflated ~14% and any argument built on type
counts or hapax inventories must be re-based on the clean loader. The
uncertain-space knob moves word-level features by up to 7% — enough to
matter for close model comparisons, so phase109+ report both settings
where feasible.

### Dependency matrix (mechanically derived)

Per-script grep-based inheritance over the 89 VMS-data-touching scripts
(heuristic tags; full per-script table
`results/phase108c_assumption_matrix.json`):

| assumption | inherited by |
|---|---|
| A1 transliteration-is-text | 89/89 (100%) |
| A2 spaces-are-boundaries | 45/89 (51%) |
| A3 linear adjacency stats | 68/89 (76%) |
| A5 language comparisons | 49/89 (55%) |
| A6 pools A+B as one system | 70/89 (79%) |
| A7 uses section/folio structure | 59/89 (66%) |

(A4 — nulls — is not grep-detectable: it is inherited by **all 89** by
omission; no script models null glyphs.)

Reading: 100% of the suite's evidence is conditional on A1; T1 showed A1
was concretely false at the 5% level and the suite survived — but the
deeper A1 question (EVA's unit ontology) is untested until phase110.

---

## Phase 2 — Graveyard autopsy

Not a history lesson: each corpse yields a *named failure mode* that
becomes a hard constraint on Phase 3 strategies. Deaths are grouped by
mechanism, not chronology.

### The corpses

**Newbold (1921, "Latin micrography + anagrams").** Claimed each glyph
dissolved into microscopic shorthand strokes, read via anagramming Latin.
Died when Manly (1931) showed the "micrographic strokes" were ink cracks,
and the anagramming step could produce essentially any target text.
*Failure modes: signal-from-noise (reading artifacts as data) + unbounded
DOF (anagramming).*

**Friedman's teams (1944-1959).** The best cryptanalysts of the century,
two study groups, years of machine tabulation. Produced no decipherment —
but importantly produced *negative knowledge*: not a simple substitution,
not a transposition, not a known polyalphabetic. Friedman's own conclusion
(early synthetic language) was itself unfalsifiable-as-stated. *Failure
mode: hypothesis exhaustion inside one paradigm — every tested system was a
cipher a human clerk would design.*

**Brumbaugh (1978), Levitov (1987), Feely, Strong.** Each produced
"readings" via flexible many-to-one mappings into a chosen language
(Latin, polyglot creole, medical shorthand...). Each translation read as
word salad requiring further "interpretation". *Failure mode: DOF
laundering — the mapping's freedom hides in the interpretive step, so the
pipeline as a whole can absorb any input.*

**Rugg (2004, Cardan grille hoax).** Demonstrated a *generation* mechanism
(tables + sliding grille) that produces Voynich-like words fast enough for
a 15th-c. forger. Died as an explanation, not as a demonstration: measured
against the corpus it undershoots vocabulary richness catastrophically (our
N3: 903 types vs 7,643; hapax structure absent; no line effects; too-rigid
positional grammar). *Failure mode: resemblance-by-eyeball — matching a few
salient features and declaring victory without a full fingerprint.*

**Timm & Schinner (2020, self-citation).** The strongest hoax model:
copy-and-modify explains adjacency similarity, Currier drift, and hapax
richness qualitatively. But it has never been scored on a *full* feature
vector against calibrated rivals — and our N4 already exposes a bind:
mutation rates rich enough for the lexicon overshoot adjacency texture 8×
(0.209 vs 0.027). *Failure mode: single-statistic advocacy — a generative
model validated only on the statistics it was designed to explain.*

**Bax (2014, "provisional decoding of 10 words").** Bootstrapped from
assumed plant identifications to sound values. Plant IDs are themselves
speculative; ten words with flexible vowels in an unknown language are
within coincidence range for ANY glyph-to-sound assignment. *Failure mode:
anchor decay — chaining inferences off an uncertain anchor while treating
it as fixed.*

**Gibbs (2017, "abbreviated Latin recipes").** Announced in TLS; two
"translated" lines, which Latinists immediately rejected as not
grammatical Latin; ignored existing scholarship (the "index" he posited is
known to be quire numbers). *Failure mode: no-controls publication — zero
held-out validation, zero skeptical review before claiming.*

**Cheshire (2019, "proto-Romance").** Peer-reviewed (briefly), then
demolished: the posited language ("proto-Romance survived unwritten for
centuries") is historically incoherent; every word was translated by
scanning modern Romance dictionaries until something fit. *Failure modes:
DOF laundering + nonexistent-prior (the hypothesis class itself has prior
probability ~0).*

**Hauer & Kondrak (2018, AI: Hebrew + anagrams).** Serious NLP work with a
fatal design: their classifier was *forced* to pick one of 380 candidate
languages for ANY input — it picks Hebrew for shuffled gibberish too; then
anagram decoding + Google-Translate smoothing manufactured fluency. Never
run on negative controls. *Failure modes: forced-choice classification
(no "none of the above" arm) + unbounded DOF (anagramming) + no negative
controls.*

**Every published "AI solves Voynich" since.** Common template: embed VMS
tokens, find nearest neighbors in some language's embedding space, decode
cherry-picked lines. None survives an N1 word-shuffle control (embeddings
of shuffled Voynich "decode" equally well). *Failure mode: control-free
pipelines.*

### The catalog — binding constraints for Phase 3

| id | failure mode | constraint on every VAIS strategy |
|---|---|---|
| F1 | Unbounded DOF (anagrams, flexible lookup) | DOF budget declared numerically; any step that can absorb arbitrary input kills the strategy |
| F2 | DOF laundering (freedom hidden in "interpretation") | end-to-end scoring only: the pipeline's output is scored mechanically, never "read" by a human for plausibility |
| F3 | Control-free pipeline | the 9-corpus battery runs first; a method fooled by N1-N4 is dead (charter rule 1) |
| F4 | Forced-choice classification | every classifier gets an explicit "none of the above" arm |
| F5 | Single-statistic advocacy | models are scored on the full 17-feature fingerprint, including features they were not designed to explain |
| F6 | Resemblance-by-eyeball | distances are computed, never asserted; z-scores against reference distributions |
| F7 | Anchor decay | no inference chains off unverified anchors (plant IDs, month names, marginalia) — anchors enter only as *hypotheses to test*, weighted by their own uncertainty |
| F8 | Corpus pooling (A6) | every result reported for Currier A and B separately as well as pooled; disagreement is data |
| F9 | Paradigm tunnel vision | the portfolio must span mutually exclusive hypothesis families (language, cipher, hoax, notation) — no strategy assumes its own family is true |
| F10 | Signal-from-noise (Newbold) | any feature extracted below the transliteration level (strokes, pixels) needs inter-source agreement (ZL vs other transliterations, or multiple scans) before use |

---

## Phase 3 — The machine-scale attack portfolio

Twelve strategies. Each is feasible only (or overwhelmingly better) at
machine scale, states which assumption it relaxes, and carries a
pre-registered kill criterion. Family coverage per F9: cipher (S1, S4, S5,
S8), language (S4, S6), hoax/generated (S3), notation-not-language (S6),
and family-agnostic instruments (S9-S12).

| # | strategy | relaxes | compute | kill criterion (pre-registered) |
|---|---|---|---|---|
| S1 | Alphabet-space search: beam-search over glyph merge/split/unify re-codings of EVA, scoring each candidate alphabet by how far it moves the corpus toward its best-matching positive control | A1 | hours | if the objective "normalizes" N3/N4 toward language as easily as it recovers P4's planted grouping, the objective is non-discriminative — kill |
| S2 | Raw-scan glyph clustering: unsupervised stroke/shape clustering from folio scans; rebuild the token stream with NO human alphabet; re-run the fingerprint | A1 (fully) | days, GPU helpful | if cluster count is unstable (±30%) across folios/scan qualities, transliteration-free analysis is unreliable at this scan quality — kill (F10 gate) |
| S3 | Generative forgery tournament: every proposed mechanism (grille, self-citation, verbose cipher, language+cipher stack) implemented as a calibrated generator, scored on the full 17-feature fingerprint z-distance to VMS | A5 (tests it) | minutes | any generator whose z-distance to VMS beats VMS-half-A-to-half-B's own internal distance = manuscript is *statistically forgeable* by that family; if NO generator family closes within 3× the internal distance, all current mechanisms insufficient — both outcomes informative; kill only applies to single generators |
| S4 | Segmentation-agnostic modeling: BPE/unigram-LM learned on the space-stripped stream; compare learned units to EVA words; MDL scoring | A2 | hours | if learned segmentation matches spaces no better on VMS than on N2 (where spaces are meaningless by construction), spaces carry no segmental signal — downgrade every word-level result |
| S5 | Nomenclator/codebook MDL: model tokens as codebook indices (arbitrary word→word table); compare description length vs language/cipher/hoax models | A5 | hours | if codebook MDL beats language MDL on P1 (plain Latin), the MDL comparison is broken — kill the instrument, not the hypothesis |
| S6 | Numeral/positional-notation test: score the corpus as number system (minim runs = digits, gallows = place markers) against Roman/abacus/cistercian numeral corpora | A5 | minutes | if the same scorer rates P1 (Latin prose) as "numbers" comparably to real numeral corpora — kill |
| S7 | Line-as-unit encodings: model each LINE as one record (fixed-field, key-value, table row); test field-position predictability across lines | A3 | minutes-hours | if field structure found in VMS is matched by N1 (shuffled words, real line lengths) — artifact of line-length distribution, kill |
| S8 | Null/filler search: for every candidate null set (greedy over glyph subsets), measure entropy/structure gain after deletion; compare against same search on controls | A4 | hours (combinatorial, bounded beam) | the search WILL find "nulls" everywhere (DOF!); signal = VMS gain exceeding the 95th percentile of gain on P1-P5; below that — kill |
| S9 | Cross-transliteration invariance audit: recompute the headline fingerprint on Currier, v101, GC transliterations; report which suite results are transliteration-robust | A1 | minutes + data acquisition | results that flip across transliterations are demoted to artifacts; instrument cannot be killed, only starved of data |
| S10 | Scribe/hand-conditional systems: fit every generative model per-Currier-hand (and per Lisa Fagin Davis scribe if data acquirable); test whether hands differ in PARAMETERS or in SYSTEM | A6 | hours | if pooled model beats per-hand models on held-out folios after MDL penalty — hands are one system, kill the multi-system hypothesis |
| S11 | Page-order optimization: find the folio permutation maximizing cross-page statistical continuity; compare optimal order to current binding and to codicological reconstructions | A7 | hours (TSP-like, heuristic) | if optimizer improves continuity on N1 (where true order is destroyed) as much as on VMS — continuity signal is noise, kill |
| S12 | DOF calculator: meta-instrument that takes any decipherment pipeline (as config) and computes its effective degrees of freedom by measuring how well it "decodes" the negative battery | (audits F1/F2) | minutes per pipeline | cannot be killed; it IS the kill apparatus |

### Ranking for Phase 4 prototyping

Scored on (discriminative power × feasibility with in-repo data ÷ DOF
risk):

1. **S3 forgery tournament** — the fingerprint + controls already exist;
   directly adjudicates the biggest live question (hoax vs cipher vs
   language) under F5 full-vector scoring. PROTOTYPE = phase109.
2. **S1 alphabet-space search** — attacks the load-bearing assumption
   (A1/EVA ontology) that 100% of results inherit; has a built-in positive
   control (must recover P4's planted verbose grouping). PROTOTYPE =
   phase110.
3. **S4 segmentation-agnostic** — cheap, kills or validates A2 for the
   whole suite. PROTOTYPE = phase111 if budget allows; else next cycle.

S2 (raw scans) is the most assumption-free attack but needs scan
acquisition + GPU; specced as future work. S9 needs external
transliteration files; queued behind data acquisition.

---

## Phase 4 — Prototype results

All three prototypes are permanent VAIS modules (auto-discovered by the
web UI with their parameters exposed; golden references captured at
PYTHONHASHSEED=0). Controls ran first in every case, per charter.

### phase109 — Forgery tournament (S3): nobody can forge it

Zero fitted parameters (generators frozen in phase108 before the
tournament existed). Yardsticks: interleaved-halves internal distance
0.049 (tight), contiguous-halves 0.175 (loose = forgeability bar).

Ranking vs VMS_full (mean per-feature |z| over 15 features):

| entrant | z-dist | note |
|---|---|---|
| vms_word_shuffle | 0.341 | *diagnostic, not generator — shares the actual tokens* |
| italian_plain | 0.887 | closest true generator is... plain language |
| latin_plain / subst | 0.953 | |
| latin_verbose | 0.996 | |
| latin_abjad | 1.004 | |
| self_citation | 1.080 | |
| grille_table | 1.399 | |
| vms_char_shuffle | 1.580 | |

Adjudicated against the pre-registered criteria: **no entrant closes
under the forgeability bar; all mechanisms as calibrated are partially
adequate at best** (best true generator ~5× the bar). Three sharp facts:

1. **The line effects are the moat.** Even the word-shuffle — which starts
   from the manuscript's own vocabulary — fails, entirely on
   line_init_jsd (2.29z) and line_final_jsd (1.95z). No proposed
   mechanism, hoax or cipher, reproduces what happens at line boundaries.
2. **Hoax generators lose to plain language** on the full feature vector.
   The grille undershoots vocabulary catastrophically; self-citation pays
   for its lexicon with 8× the manuscript's adjacent-word similarity
   (the "Timm bind": in our parameter sweep the theory cannot buy hapax
   richness and adjacency texture at the same time).
3. Currier B is uniformly harder to match than A (every entrant's
   distance is higher vs B) — consistent with B being the more
   "worn-in" (more systematized) register.

Scope: kills apply to the calibrated generators, not theory families
(docstring caveat); the per-feature breakdown is the actionable output.

### phase111 — Segmentation-agnostic BPE (S4): A2 survives, spectacularly

Strip every space; learn 200 BPE merges from character statistics alone;
ask whether learned unit boundaries rediscover the original spaces.
Excess F1 = boundary F1 minus density-matched random baseline:

| corpus | F1 | random-F1 | excess |
|---|---|---|---|
| P1 latin | 0.390 | 0.222 | 0.168 |
| P2 italian | 0.464 | 0.312 | 0.152 |
| P4 verbose cipher | 0.373 | 0.094 | 0.279 |
| N2 char-shuffle | 0.278 | 0.276 | **0.002** |
| N3 grille | 0.132 | 0.243 | −0.111 |
| **VMS** | **0.685** | 0.231 | **0.454** |

Instrument validated (P1 strongly positive, N2 ≈ 0 as designed). Verdict:
**Voynich spaces are recoverable from character statistics at 2.7× the
strength of genuine Latin.** A2 survives — word-level statistics rest on
real segmental signal — but over-survives into a new anomaly: word
boundaries this predictable from context mean word forms are far more
constrained than natural orthography (consistent with the rigid
slot-grammar findings, and notably with P4-style verbose units, whose
excess (0.279) also exceeds plain language). N3's *negative* excess is a
new discriminator against table generation.

### phase110 — Alphabet-space search (S1): EVA is not hiding a normal text

Beam search (breadth 6, depth 10; ~1,000-1,350 configurations explored
per target; runtime ~25 min) over merge/unify/drop re-codings, objective
= distance of char-structural features from the P1+P2 language band.
Controls first, per protocol:

| target | band-dist start → final | gap closed | final alphabet |
|---|---|---|---|
| P4 verbose (positive) | 1.804 → 0.754 | **58%** | 21 |
| N3 grille (negative) | 1.102 → 0.539 | 51% | 21 |
| VMS full | 0.937 → 0.460 | 51% | 23 |
| VMS Currier A | 0.890 → 0.432 | 51% | 30 |
| VMS Currier B | 1.102 → 0.505 | 54% | 24 |

Formal adjudication: the pre-registered kill (N3 normalized as easily as
P4) did NOT fire — 51% < 58% — and the positive control passed (the
search's chosen ops on P4 visibly re-merge planted verbose groups: qo,
ol, dy, ai...). But the margin is 7 points, so the instrument's
discriminative power is **weak as configured**, and the honest headline
is the comparison: **VMS gains (51%) track the cosmetic-normalization
baseline (N3: 51%), not the genuine-recovery profile (P4: 58%).**

Reading (SUGGESTIVE tier): within this op space — bigram merges,
paleographic unifications, rare-glyph drops, alphabet size 15-60 — there
is no re-coding of EVA under which the manuscript becomes statistically
ordinary, beyond what the same machinery does to table gibberish. The
character-level anomalies are deep properties of the token stream, not
artifacts of EVA's unit choices. (Ops chosen for the VMS are nonetheless
sensible and stable across A/B: merge dy/ai/ar/ey, unify f=p, drop the
rare non-core glyphs — a useful canonical-recoding candidate for future
instruments.) Caveats: one objective, 4 features, one beam config; a
richer op space (context-dependent splits, many-to-one glyph maps) is
future work and the parameters are UI-exposed for exactly that.

---

## Phase 5 — Report: what is established, suggestive, speculative

### ESTABLISHED (survived controls + pre-registered criteria)

1. **T1 — the analyzed corpus contained 5.4% markup artifacts** (phantom
   tokens from IVTFF metadata, fused alternate readings), and the type
   inventory was inflated 13.6%. Fixed (`load_folio_lines_ivtff`); the
   suite's qualitative anomalies survive the correction, so prior
   results are dented, not overturned. Every corpus-level claim made
   from this repo before 2026-07-15 should cite the clean numbers.
2. **No proposed generative mechanism, as calibrated, forges the
   manuscript** (phase109, zero fitted parameters, bar pre-registered):
   best true generator is 5× above the forgeability yardstick. The
   line-boundary effects are the universally unreproduced feature — the
   moat. Any future hoax theory must clear them or is dead on arrival.
3. **Spaces carry real segmental signal** (phase111): boundary
   recovery from character statistics alone, validated against positive
   and negative controls, is 2.7× stronger for the VMS than for Latin.
   Word-level statistics are not artifacts of a layout convention (A2
   survives).
4. **The self-citation bind** (phase108/109): within our parameter
   sweep, copy-modify generation cannot simultaneously match the
   manuscript's vocabulary richness and its adjacency texture (mutation
   rates rich enough for TTR overshoot adjacent-similarity ~8×).
   Scope: our implementation family; a published-parameter replication
   is the obvious next test.

### SUGGESTIVE (real signal, one instrument, or thin margins)

5. **The verbose-cipher profile keeps matching.** P4 is the only
   positive control reproducing the manuscript's h2_ratio (0.533 vs
   0.546 clean), its BPE boundary-excess also exceeds plain language,
   and phase106's abbreviation results point the same way. Nothing here
   *decodes* anything — but as a hypothesis family, "verbose/multi-glyph
   units over a natural-language plaintext" is the only one that keeps
   scoring on features it was not designed for.
6. **EVA granularity is not the explanation** (phase110): no re-coding
   in a declared op space normalizes the corpus beyond cosmetic
   baseline. Weak instrument margin (7pp); needs a stronger objective
   before promotion.
7. **Currier B is harder to forge than A** (every phase109 entrant is
   further from B), consistent with B as the more systematized register.

### SPECULATIVE (hypotheses worth compute, no claims)

8. Line-as-record structures (S7): the moat feature suggests the LINE,
   not the word, may be the encoding unit.
9. Numeral/positional readings (S6) remain untested against the moat.
10. Raw-scan glyph clustering (S2) is the only strategy that fully
    escapes A1; queued on data acquisition.

### Phase 4b — Verbose cipher inversion, rungs 1-2 (2026-07-16)

The three converging verbose-cipher signals earned an actual inversion
attempt (`verbose_cipher_inversion`): strict 1:1 group→letter model,
6 language models (Latin/Italian × plain/abjad/abbrev4), holdout
scoring, planted-table replay verified byte-identical before grading.

**Rung 1 (blind segmentation): KILLED by its positive control.**
Frequency-only BPE recovered 13% of the planted P4 inventory; the KNOWN
cipher decoded worse than grille gibberish (−0.78 vs −0.63 bits/sym).
Diagnosis: cross-boundary glyph pairs are as frequent as within-group
pairs — verbose-group boundaries are invisible to frequency statistics.
(The scoring side validated perfectly: plain Latin came back at +0.001
bits/sym, indistinguishable from native.)

**Rung 2 (EM with LM feedback, still strict 1:1): ALSO KILLED — but
instructively.** At prototype budget (4 EM iterations, 6 proposals):

| corpus | best LM | holdout gap (bits/sym) |
|---|---|---|
| P4 planted cipher | latin/abjad | +0.115 — recovery **48%** (kill: <50%), mapping 48% |
| N4 self-citation | latin/abjad | +0.082 (noise floor) |
| N3 grille | latin/abjad | −0.127 |
| VMS full / A / B | — | not interpretable (kill fired) |

Three lessons, all logged as constraints:
1. **LM feedback works directionally**: inventory recovery jumped 13% →
   48% and mapping accuracy 0% → 48% with only 4 EM iterations. The
   kill missed by 2 points; the pre-registered threshold stands and the
   next escalation is **compute** (more EM iterations, restarts,
   proposals — the approved overnight sweep), NOT model freedom.
2. **The noise floor rises with model power.** Rung 2's extra freedom
   lifted the best negative from −0.63 to +0.08 bits/sym — meaningless
   text "decodes" better as the machinery gets stronger. Any future
   rung must beat the noise floor measured at ITS OWN rung.
3. **Overfitting red flag observed in the wild**: Currier A (the small
   corpus) scored +0.21 — "better than native Latin" — which is
   impossible as a decode and is the free-mapping memorization artifact
   the holdout was designed to expose. It survived because same-corpus
   holdout lines share vocabulary; the overnight run should hold out
   whole FOLIOS, not lines.

Vocabulary discipline: nothing here says the manuscript is or is not a
verbose cipher. It says the strict inverter cannot yet crack even a
KNOWN verbose cipher at this budget — so it has nothing to say about
the manuscript. The instrument, its ladder, and both corpses are
permanent (`verbose_cipher_inversion`, UI-parameterized).

### The scoreboard the field inherits

A century of theories now has a quantitative bar: **reproduce
line_init_jsd ≈ 0.16 / line_final_jsd ≈ 0.08 without copying whole
lines, while holding TTR ≈ 0.36, adjacency ≈ 0.027, and h2_ratio ≈
0.546.** Every mechanism we calibrated fails at least one. The
instruments (phase108-111), controls, and kill criteria are permanent
VAIS modules with UI-exposed parameters; the tournament is open.
