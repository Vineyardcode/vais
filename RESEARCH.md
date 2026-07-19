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

---

### Phase 4c — Verbose cipher inversion, rung 3: max strength + folio-level holdout (2026-07-17)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-17; awaiting human review before promotion to any evidence tier.]

Budget (pre-registered in the script docstring): {'EM_OUTER': 32, 'EM_PROPOSALS': 48, 'EM_RESTARTS': 16, 'RESTARTS': 64, 'TOP_LMS_RUNG2': 3}. Runtime 1.76 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folios (controls), closing the rung-2 Currier-A memorization leak.

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

The corpse is logged with the same prominence as a positive would be, per charter rule 5.

---

### Phase 4d — Verbose cipher inversion, rung 3b: coverage-penalized objective (2026-07-17)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-17; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): {'EM_OUTER': 32, 'EM_PROPOSALS': 48, 'EM_RESTARTS': 16, 'RESTARTS': 64, 'TOP_LMS_RUNG2': 3}. Runtime 1.59 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

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

---

### Portfolio S7 — line-as-record structures, first instrumented run (2026-07-18)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-18; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): script defaults. Runtime 0.00 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

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

The corpse is logged with the same prominence as a positive would be, per charter rule 5.

---

### Portfolio S7, rung 2 — per-hand line-as-record adjudication (2026-07-18)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-18; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): script defaults. Runtime 0.03 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

**SUGGESTIVE — awaiting human review (quarantined; never merged automatically):**

**Pre-registered outcomes** (line_as_record_per_hand.py docstring, full post-hoc provenance disclosed there): a hand passes only if its 10-split median interior gain beats ALL 20 of its own null-shuffle medians (empirical p ~ 0.048) AND clears the 0.05 bits/token effect floor over the null median — strictly harder than the rung-1 observation that motivated this rung.

| corpus | median gain (bits/token) | null max | null median | margin | pass |
|---|---|---|---|---|---|
| PREC_records | +0.7471 | — | — | — | gate |
| P1_latin_plain | -0.0039 | — | — | — | gate |
| VMS_currier_A | +0.0113 | -0.0132 | -0.0187 | +0.0301 | fail |
| VMS_currier_B | +0.0513 | -0.0043 | -0.0067 | +0.0580 | **PASS** |

Instrument gate: P-REC +0.7471, P1 -0.0039 → PASS.

**VERDICT: B ONLY — consistent with line-level field structure in Currier B (SUGGESTIVE, quarantined; the first registered test of the rung-1 observation). NOT a decode; no field is named or read.**

---

## Phase 7 — External-findings intake (2026-07-18, human-directed)

Four sources supplied for review plus a self-directed voynich.ninja
sweep, assessed for incorporation BEFORE the next test is built. Each
item states what it changes in this program.

### 7.1 Parisel 2026a — "A Quantitative Confirmation of the Currier
Language Distinction" (arXiv:2604.25979)

Beta-binomial mixture over character-pair substitution across 185
folios recovers A/B unsupervised (89% label agreement; 195/197 folios
classified); a two-state switch (vowel selection after specific
digraphs; "template identity" = 92% of switching variance) is claimed
to underlie the contrast — i.e., A/B as one system with a discrete
switch, not two languages.

**Bearing on us:** directly engages A6/S10 and converges with our S7
rung-2 observation that the positional-field signal is GRADED across
hands (B passes, A stably above its nulls but sub-floor) — both
consistent with "one mechanism at different intensities" rather than
two systems. **Charter caveat:** no negative-control battery is
reported; mixture models find clusters eagerly (F3). **Incorporations:**
(a) S7 rung 3 should emit PER-FOLIO interior gains so positional
strength can be correlated against per-folio switch intensity — if the
two findings track each other, they describe one regime; (b) implement
the beta-binomial substitution instrument in VAIS and run it on the
control battery (does it "discover two languages" in N4 self-citation?)
— an adjudication the field lacks, cheap, high value either way.

### 7.2 Parisel 2026b — "Layered Positional and Directional
Constraints" (arXiv:2604.19762)

Claims a directional dissociation (RTL-optimized word-internal
sequences vs LTR-optimized word-boundary transitions; 80.6%
end-class→start-class rate) absent in 4 comparison languages; reports
that a parametric slot generator AND a Cardan grille each fail at least
one of 4 registered signatures across full parameter ranges.

**Bearing on us:** their generator-vs-signatures test is a narrower
sibling of our S3 forgery tournament and reaches the same verdict
(nobody forges it). **Incorporations:** (a) add the directional-
dissociation statistics to the fingerprint as versioned new features
(F5: score models on features they were not designed for); (b) the
Zattera-style slot generator becomes a calibrated S3 tournament entrant
— see 7.4.

### 7.3 LAAFU prior art (voynich.ninja threads 4869, 5021) — REQUIRED
READING for S7; two competing mundane models now bound rung 3

Community-established points: (a) Stolfi's justification model —
scribes fitting words to line width produce longer line-initial and
shorter line-final words as pure formatting fallout; empirically
confirmed there (line-final words ~1 character shorter); (b) natural-
language control texts can show false LAAFU (Vogt: Tom Sawyer); (c)
paragraph-initial lines obey different rules than ordinary lines
(Zandbergen).

**Bearing on us:** these are the two live ALTERNATIVE explanations for
the S7 rung-2 Currier-B signal, and they are ORDINAL — a within-line
shuffle null does NOT dismiss space management, because space
management is itself an ordering mechanism. **Binding consequences for
the rung-3 registration:** (a) composition-preserving nulls
(within-folio AND within-line shuffles) to kill the section/lexicon
confound; (b) PER-FEATURE breakdown — if B's interior signal lives in
the length feature alone, justification is the parsimonious reading;
field-vocabulary structure requires glyph-identity features to carry
signal independently; (c) a P-JUST control: natural-language text
line-broken by a width-fitting algorithm, measuring how much interior
gain pure justification produces in this instrument; (d) future rungs
should separate paragraph-initial lines.

### 7.4 Zattera slot-machine update (thread 5715) and Layfield & Davis
singulions + Timm's critique (threads 5911, 5896)

Thread 5715: switchable-template slot grammar, F1 0.214→0.242, token
coverage 0.549→0.662; community debate mirrors our S5 MDL position
(coverage/precision/complexity must be traded explicitly — Stolfi).
**Incorporation:** a calibrated slot-machine generator (with switchable
templates) as an S3 tournament entrant, scored on the FULL fingerprint
— the line-effects moat is precisely what word-grammar generators
cannot see, and neither the F1 debate nor 7.2 tests it.

Threads 5911/5896: Layfield & Davis's singulion/binding work supports
A7's demotion of current page order (helpful codicological cover for
our folio-level holdout, which depends only on the folio as a physical
unit, not on binding order). Their LSA-based RESEQUENCING claim is an
uncontrolled S11: Timm's critique (no permutation nulls; production
proximity vs textual continuity) is our charter's F3/F6 stated
independently. **Incorporation:** S11, when prototyped, adjudicates
their resequencing claim under our controls — it now has an external
claim to test, raising its priority within the portfolio.

### Intake verdict — revised next-step ranking

1. S7 rung 3 REDESIGNED before registration (was: composition nulls
   only): within-folio + within-line nulls, P-JUST justification
   control, per-feature and per-folio read-outs (7.1a + 7.3).
2. Beta-binomial A/B-switch instrument under the control battery
   (7.1b) — cheap, adjudicates an external claim, informs whether
   "hand" or "switch intensity" is the right conditioning variable for
   every per-hand analysis we run (F8's definition is at stake).
3. Fingerprint vNext with directional features + slot-machine
   tournament entrant (7.2, 7.4) — extends S3 without new DOF.
4. S11 with controls, adjudicating the resequencing claim (7.4).

---

### Portfolio S7, rung 3 — composition vs ordinal structure (Currier B) (2026-07-18)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-18; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): script defaults. Runtime 0.03 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

**SUGGESTIVE — awaiting human review (quarantined; never merged automatically):**

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

---

### Portfolio S9 — cross-transliteration invariance audit (A1) (2026-07-18)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-18; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): script defaults. Runtime 0.02 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

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

---

### Portfolio S9, follow-up — sensitivity-normalized effect floors (2026-07-18)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-18; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): script defaults. Runtime 0.04 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

**Pre-registered outcomes** (script docstring; written with full disclosure AFTER N2's PARTIAL): floors scale by MEASURED sensitivity rho (planted sort implant, ZL anchor, symmetric — floors may rise), battery values inherited from N2's exact seed streams and cross-checked.

| reading | margin | implant response | rho | normalized floor | verdict (was, fixed 0.05) |
|---|---|---|---|---|---|
| ZL | +0.0501 | +0.5806 | 1.0000 | 0.0500 | PASS (PASS) |
| CD | +0.0326 | +0.6490 | 1.1178 | 0.0559 | fail (fail) |
| GC | +0.0487 | +0.6488 | 1.1175 | 0.0559 | fail (fail) |
| FG | +0.0534 | +0.6812 | 1.1733 | 0.0587 | fail (PASS) |
| IT | +0.0529 | +0.5632 | 0.9700 | 0.0485 | PASS (PASS) |

**VERDICT: REFERENCE FLIP — symmetric normalization flipped a previously-passing reading by RAISING its floor: the normalized-floor instrument is not consistent enough to re-adjudicate at these margins. No claim; N2 PARTIAL unchanged. The registered question IS answered: measured sensitivities refute the "finer alphabets are mechanically penalized" hypothesis (GC rho > 1).**

---

### Portfolio S9, follow-up 2 — significance-only cross-reading battery (2026-07-18)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-18; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): script defaults. Runtime 0.81 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

**SUGGESTIVE — awaiting human review (quarantined; never merged automatically):**

**Pre-registered criterion** (script docstring; significance-only criteria change human-approved 2026-07-18): per reading, PASS iff the real 10-split median interior gain beats ALL 200 within-line-shuffle null medians — empirical p = 0.0050. No effect floor; margins are observational. Null stream is a strict superset of N2's (first 20 identical, cross-checked), splits identical to N2 (cross-checked).

| reading | B-lines | real gain | null max (of 200) | nulls ≥ real | p | verdict |
|---|---|---|---|---|---|---|
| ZL | 2522 | +0.0442 | -0.0020 | 0 | 0.0050 | **PASS** |
| CD | 991 | +0.0094 | -0.0084 | 0 | 0.0050 | **PASS** |
| GC | 2365 | +0.0372 | -0.0068 | 0 | 0.0050 | **PASS** |
| FG | 2259 | +0.0475 | -0.0020 | 0 | 0.0050 | **PASS** |
| IT | 2329 | +0.0475 | -0.0012 | 0 | 0.0050 | **PASS** |

**VERDICT: ROBUST AT SIGNIFICANCE — the S7-B ordinal signal is significant at p < 0.005 in every usable independent reading. The cross-reading objection to the quarantined rung-3 finding is resolved in favor of robustness. The finding remains SUGGESTIVE, quarantined, and is not a decode.**

---

### Portfolio S7, rung 4 — paragraph control and characterization (Currier B) (2026-07-19)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-19; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): script defaults. Runtime 0.06 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

**SUGGESTIVE — awaiting human review (quarantined; never merged automatically):**

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

---

### Portfolio S7, rung 5 — within-section replication (Currier B) (2026-07-19)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-19; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): script defaults. Runtime 0.06 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

**SUGGESTIVE — awaiting human review (quarantined; never merged automatically):**

**Pre-registered outcomes** (script docstring; human-directed section-confound test): per usable section PASS iff the real median beats ALL 200 within-line-shuffle nulls (p < 0.0050); taxonomy: folio-number: bio f75-84, recipes f103-116, other_B rest. Pooled rung-3 headline reproduced (gate).

| section | lines / folios | real gain | null max | nulls ≥ real | p | verdict |
|---|---|---|---|---|---|---|
| bio | 739 / 20 | +0.0106 | -0.0052 | 0 | 0.0050 | **PASS** |
| recipes | 1039 / 23 | +0.0584 | -0.0036 | 0 | 0.0050 | **PASS** |
| other_B | 744 / 34 | +0.0478 | -0.0077 | 0 | 0.0050 | **PASS** |

**VERDICT: SECTION-GENERAL — the ordinal signal replicates within every usable B section independently; the section-confound objection is dismissed. SUGGESTIVE supporting detail for the quarantined finding; not a decode.**

---

### Portfolio S5/S6 — line-class sequence family classification (Currier B) (2026-07-19)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-19; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): script defaults. Runtime 0.00 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

**SUGGESTIVE — awaiting human review (quarantined; never merged automatically):**

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

---

### Portfolio S7-R — independent re-implementation (rank-based) (2026-07-19)

[AUTOMATED — written by tools/overnight.py; run committed to branch overnight/2026-07-19; awaiting human review before promotion to any evidence tier.]

Configuration (pre-registered in the script docstring): script defaults. Runtime 0.02 h at PYTHONHASHSEED=0. Holdout: whole folios (VMS) / 24-line pseudo-folio blocks (controls).

**SUGGESTIVE — awaiting human review (quarantined; never merged automatically):**

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
