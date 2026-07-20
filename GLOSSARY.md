# Glossary — the terms VAIS uses

Definitions for reading the tests, the reports, and
[RESEARCH.md](RESEARCH.md) without opening the code. Added 2026-07-20
after community feedback that the test pages assume too much context.

## The manuscript and its text

- **Beinecke MS 408 / the VMS** — the Voynich manuscript: ~240 pages of
  unread text in an unknown script, radiocarbon-dated to the early
  15th century, held at Yale's Beinecke Library.
- **EVA** — the European Voynich Alphabet: a *convention* for writing
  Voynich glyphs in Latin letters (e.g. `qokedy`). It is one team's
  ontology of what counts as a letter, not ground truth — which is why
  the suite audits transliteration-dependence (assumption A1).
- **Transliteration** — a team's reading of the manuscript into
  machine-readable text. The suite's canonical corpus is **ZL**
  (Zandbergen–Landini); cross-checks use **C-D** (Currier/D'Imperio),
  **FSG** (Friedman's First Study Group), **v101** (Glen Claston) and
  **IT** (Takahashi).
- **IVTFF / locus / locus types** — the transliteration file format.
  Each transcribed unit (a *locus*) is typed: **P** = running
  paragraph text, **L** = label, **C** = circular (ring) text, **R** =
  radial. "Continuous text" analyses restrict to P (see the
  `LOCUS_TYPES` loader parameter).
- **Folio** — a manuscript leaf (page), e.g. `f75r`. The suite's
  held-out validation splits by folio, never by line.
- **Currier A / B** — the two statistical "dialects" (registers) of the
  text, identified by Prescott Currier in the 1970s. B dominates the
  biological and recipes sections. The suite treats the A/B label as a
  per-folio property from the transliteration metadata.
- **Hapax (legomenon)** — a word form occurring exactly once in a
  corpus. In these tests "hapax" refers to the *form*: the interesting
  question is whether unique forms behave like rare content words
  (language) or like encoding accidents (cipher).
- **Gallows** — the tall Voynich glyphs (EVA `t k p f` and compounds);
  prominent at paragraph and line starts (see *Grove words*).
- **Grove words / LAAFU** — community terms: gallows-initial words at
  paragraph starts (Grove), and Currier's "line as a functional unit"
  (LAAFU) — the long-observed fact that line starts/ends behave
  anomalously.

## Statistics used across the tests

- **Entropy (H)** — average unpredictability in bits. **h2 /
  conditional entropy** — unpredictability of the next character given
  the previous one; the manuscript's famously low h2 is its most-cited
  anomaly. **h2_ratio** — h2 divided by single-character entropy.
- **Bigram** — an adjacent pair (of characters or words).
- **JSD (Jensen–Shannon divergence)** — a 0-to-1 measure of how
  different two frequency distributions are. `line_init_jsd` compares
  line-initial words' first characters against everyone else's.
- **Zipf alpha** — the slope of the word frequency-vs-rank law;
  natural texts sit near 1.
- **TTR (type-token ratio)** — vocabulary richness: distinct words
  divided by total words (at a fixed sample size, e.g. `ttr_5000`).
- **Burstiness (B)** — whether events (e.g. hapaxes) arrive clumped
  (B → 1), regularly (B → −1), or randomly (B ≈ 0), from the spread of
  gaps between them.
- **Spearman correlation (ρ)** — rank correlation: do two quantities
  order things the same way (+1), oppositely (−1), or unrelatedly (0)?
- **Levenshtein distance** — minimum single-character edits between
  two words; used for adjacent-word similarity.
- **bits/token, bits/symbol** — information measured per word or per
  character; the units of most gains and gaps in these tests.

## The methodology (the anti-crackpot machinery)

- **Control battery** — corpora with known ground truth, built before
  any manuscript run: positives P1 (Latin), P2 (Italian), P3
  (substitution cipher), P4 (verbose cipher), P5 (abjad); negatives N1
  (word-shuffled VMS), N2 (character-shuffled), N3 (Rugg-style grille
  gibberish), N4 (Timm-style self-citation). A method fooled by a
  negative control is dead.
- **Pre-registration / kill criteria** — every instrument writes its
  falsification thresholds into its docstring *before first
  execution*; results are judged only against those.
- **DOF budget** — an explicit count of a method's freedom to fit
  anything (mappings, parameters, choices). Unbounded freedom
  "decodes" noise; the graveyard (RESEARCH.md Phase 2) is full of it.
- **Holdout (folio-level)** — models are fitted on one set of folios
  and scored on unseen folios, so memorization can't masquerade as
  signal.
- **Permutation null / null battery** — the same statistic recomputed
  on shuffled versions of the data (e.g. each line's words reshuffled
  in place). A real effect must beat *all* of them (empirical
  p ≈ 1/(N+1)).
- **Noise floor** — how well a method scores on *meaningless* input
  given the same freedom; a manuscript result must beat it by a
  registered margin.
- **Golden reference** — the committed byte-exact output of every test
  at `PYTHONHASHSEED=0`; any re-run (including in your browser) is
  diffed against it.
- **Adjudication / verdict / the ledger** — every registered run ends
  in a mechanical pass-or-kill verdict; the ledger (RESEARCH.md
  Phase 5) files results as **ESTABLISHED** (survived controls and
  criteria), **SUGGESTIVE** (real signal, quarantined pending
  scrutiny), or **SPECULATIVE** (worth compute, no claims).
- **Quarantine / "consistent with"** — positive findings are flagged,
  never promoted without human review, and the strongest permitted
  claim is "consistent with X" — never "decoded".

## Hypothesis families the suite tests

- **Verbose cipher (strict 1:1)** — each plaintext letter becomes one
  fixed multi-glyph group (e.g. Naibbe-style). Tested and negative for
  Latin/Italian/Occitan (ledger entry 11).
- **Syllable cipher** — words assembled from sub-word units mapped
  from plaintext units via a table, so word-internal structure
  reflects the table, not a phonology.
- **Codebook / nomenclator** — words as arbitrary dictionary indices
  (records/labels reading).
- **Positional notation** — lines as place-value number strings.
- **Self-citation** — Timm & Schinner's copy-and-modify generation
  (a hoax family).
- **Grille** — Rugg's table-and-window word generator (a hoax family).

## The line-discipline findings (ledger entries 13 and 15)

- **Intra-line ordinal structure** — within a line, *which* word goes
  *where* is partly predictable: word-initial glyph class carries
  positional information (bits/token) beyond every tested confound.
- **Class (first EVA glyph)** — words grouped by their first glyph
  (`q`-words, `sh`-words, …); the carrier of the placement signal.
- **Position bins** — line positions grouped as p1, p2 (first two),
  m1–m3 (interior thirds), pL-1, pL (last two).
- **Interior gain** — the headline statistic: how much better position
  predicts word features in the line's interior than a
  position-blind model, on held-out folios.
- **Placement discipline / the table / λ (lambda)** — the mechanical
  model: a measured table P(position-bin | class) plus one strength
  knob λ; placing each line's own words by this rule reproduces the
  manuscript's line statistics (the "moat") in Currier B.
- **The three axes** — the table's full content compresses to three
  interpretable rules: (1) the **edge/paragraph axis** (gallows-linked
  line-start preferences — Grove/LAAFU, quantified), (2) the
  **interior gradient** (sh/q-early → r-late drift), (3) the
  **pre-final-zone axis** (a distinct preference just *before* the
  line end — detectable only in B).
- **The moat** — shorthand from the forgery tournament: the
  line-boundary statistics that no calibrated generator reproduced —
  until the placement-discipline reduction.

## Infrastructure

- **Overnight runner** (`tools/overnight.py`) — the unattended
  executor: runs a queued instrument, adjudicates it against its
  registration, writes the report, and commits records to dated
  branches.
- **In-browser runner** — every test page's ▶ button: the actual
  Python instrument compiled to WebAssembly, running on your machine
  with your parameter overrides, diffed against the golden.
- **Data pack** — the zip of scripts, corpora and caches the browser
  runner mounts; nothing is uploaded anywhere.
