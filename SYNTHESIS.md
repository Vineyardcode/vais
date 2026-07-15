# The Voynich Manuscript: A Statistical Portrait

## What 68 Phases of Computational Analysis Establish

This document synthesizes 62 phases of progressively skeptical statistical
analysis of the Voynich manuscript's EVA transcription. Every claim below
survived cross-validation, permutation testing, and deliberate attack.
Multiple findings were retracted during the analysis; what remains has
been stress-tested, including a dedicated Phase 51 that attacked the
synthesis itself, Phase 56 that retracted Phase 55's premature
claim about excluding alphabetic encoding, Phase 57 that tested
the first external decipherment proposal (Bax/Vogt), Phase 58
that fingerprinted VMS against known writing systems, Phase 59
that forward-modeled encoding processes to reproduce the VMS fingerprint,
and Phase 62 that dissected word-final characters via MI decomposition
to determine whether they are terminators, grammar, or content.

---

## 1. The Core Finding

**Voynichese has genuine non-random structure at the character level,
but the "morphological grammar" we identified is 95.6% explained by
single-character transitions. Words are bursty (B=0.246, natural
language range) and show clear phonotactic positional structure,
excluding mechanical generation. Sukhotin's V/C separation produces a
degenerate split (91% "vowels"), but Phase 56 showed this is EXPECTED
from the VMS bigram model — the degenerate split is an artifact of
character frequency distribution, not evidence for or against any
particular script type.**

This is the single paragraph that summarizes 56 phases. Everything below
elaborates on it.

---

## 2. The Statistical Fingerprint

| Property | Value | Comparable To |
|----------|-------|---------------|
| Tokens | 35,747 | Short novel |
| Types | 3,319 | |
| Alphabet size | ~20-26 chars | Alphabetic script |
| H(character) | 3.62 bits | Lower than English (4.07) |
| H(char\|prev char) | 1.92 bits | Much lower than English (3.30) |
| H(word) | 8.48 bits | Lower than English (~11) |
| Mean word length | 4.01 chars | Shorter than English (4.7) |
| Zipf exponent | ~1.0 | Normal natural language |
| Hapax ratio | 57.8% | High but natural-language range |
| Type-token ratio | 0.093 | Normal |
| Words per line | 7.93 | Sentence-length |

**Key anomaly:** Character bigram conditional entropy (1.92 bits EVA,
2.32 bits at glyph level) is lower than European languages (3.0-3.3).
**CORRECTION (Phase 51):** The anomaly is smaller than initially claimed
after correcting for EVA compound glyphs, and the bits-per-word
comparison (9.3-10.3 VMS vs ~15.5 English) shows VMS words carry LESS
information, not anomalously more. The low entropy could indicate:
- A syllabary-like script (fewer valid combinations)
- Partially formulaic word construction
- A closed lexicon with constrained character patterns

---

## 3. What We Know (High Confidence)

### 3.1 Character-Level Syntax (99% confidence)

The PRIMARY structural phenomenon in Voynichese: the last character(s)
of word $i$ predict the first character(s) of word $i+1$.

- z = 80.3 (parser-free, Phase 48)
- Cross-validates at 85.5% retention (Phase 49)
- Direction is left-to-right: all 20 jackknife samples confirm
- Dominant pattern: words ending in 'y' → words starting with 'q'

This can be DESCRIBED in morphological terms (suffix -dy predicts
prefix qo-), because suffixes are determined by last characters and
prefixes are determined by first characters. But Phase 51 showed that
**95.6% of the so-called "morphological MI" is explained by single
character transitions**. The morphological labels are useful shorthand
but not independent phenomena.

| Level | MI | After char control | Explained by chars |
|-------|----|--------------------|---------------------|
| Suffix→prefix | 0.0833 bits | 0.0036 bits | 95.6% |
| Residual z-score | — | z=9.2 | Modest but real |

### 3.2 Morphological Categories (50-85% confidence)

We identified 10 suffix patterns and 7 prefix patterns. These are
useful DESCRIPTIVE LABELS for character-level regularities:
- Suffix is almost entirely determined by last 1-2 characters
  (last='n' → -aiin/-ain/-iin; last='y' → -y/-dy; last='l' → -ol/-al)
- Prefix is almost entirely determined by first 1-2 characters
  (first='q' → qo-; first='d' → d-; first='o' → o-)

However, the 4.4% residual MI (z=9.2) after character control suggests
some genuine multi-character morphological signal exists beyond single
character pairs. This warrants caution: the suffixes and prefixes are
not purely epiphenomenal, but they are mostly so.

### 3.3 Lines Are Syntactic Units (97% confidence)

The morphological grammar operates **entirely within lines** and resets
at line boundaries:
- Within-line MI(sfx→gpfx) = 0.0833 bits
- Cross-line MI(sfx→gpfx) = 0.0106 bits (z = −0.5, **chance**)
- d-prefix words are 2.5× enriched at line starts
- qo-prefix words are line-internal grammar targets
- The dominant dy→qo transition drops from 33.5% to 15.0% across line
  boundaries

Lines function as independent syntactic units — analogous to sentences
or clauses in natural language.

### 3.4 Character-Level Syntax (99% confidence)

Even without any morphological parsing, the last character of word $i$
significantly predicts the first character of word $i+1$:
- z = 80.3 (Phase 48, parser-free)
- Cross-validates at 85.5% retention (Phase 49)
- This is the **parser-free proof** that inter-word syntax is real

### 3.5 Strictly Local (90% confidence)

All syntax operates at **gap 1 only** (adjacent words):
- Gap 1: z ≈ 35
- Gap 2: z ≈ 2-5
- Gap 3+: noise

There is no long-range dependency. Grammar is purely local.

---

## 4. What We Know (Moderate Confidence)

### 4.1 Three Suffix Classes (88%)

Suffixes cluster into three groups based on syntactic behavior:
- **Class A** = {-dy, -y} — the "grammar-triggering" suffixes
- **Class M** = {X (no suffix), -ar, -in} — intermediate
- **Class B** = {-aiin, -ain, -iin, -al, -ol, -or} — the "complement" suffixes

But this class system explains only 9.6% of morphological information. The
remaining 90.4% is suffix-specific, not class-level.

### 4.2 Suffixes Are Inflectional (88%)

Suffixes change the grammatical role of a word but not its lexical meaning:
- Mean pairwise suffix cosine = 0.953 (very similar distributions)
- z = 5.45 for inflectional vs derivational test
- -or is the most distributionally distinct (pharma/herbal enrichment)

### 4.3 No Discrete Word Classes (90%)

Unlike European languages with clear noun/verb/adjective categories:
- k=3 clustering explains only 12.4% of distributional variance
- NMI between distributional clusters and morphological classes = 0.007
- Words exist on a continuous gradient, not in discrete bins

### 4.4 Sparse Word-Level Syntax (85%)

Word-specific transitions are real (z=43.6 within morphological strata)
but too sparse for a discrete model:
- 51% of test bigrams are unseen in training
- Cross-validated bigram model is 4.4× WORSE than unigram
- Only 3,319 types in a 35K corpus = average 10.8 tokens per type

**CORRECTION (Phase 51):** VMS's 51% unseen rate is actually LOWER
than both a unigram baseline (65%) and a constructed language model
(78%). This means VMS word co-occurrence is MORE regular than random,
not less. The sparsity is a corpus-size effect and does NOT distinguish
natural from constructed language.

### 4.5 Vocabulary Compositionality (~50%)

The compositionality question depends on what level you test:

**Morphological level (Phase 51d):** Paradigm fill = 8.4% vs 36.2%
random (z=−25.4). ANTI-compositional. But this test assumed the
morphological decomposition was real, which Phase 51a showed is 95.6%
character-level. So the "stems" and "suffixes" tested aren't genuine
morphemes.

**Character level (Phase 52e):** First-2 × last-2 fill rate = 10.04%,
z=+2.2 (slightly above random). First-1 × last-1 fill: z ≈ 0 across
all word lengths. CONSISTENT WITH RANDOM.

**Conclusion:** The anti-compositionality from Phase 51d was an artifact
of the morphological decomposition. At the character level — which
Phase 51a showed is where the real structure lives — the vocabulary is
neither closed nor open; it's consistent with character-level generation.

### 4.6 Word Burstiness (95% NEW, Phase 52b)

VMS words cluster in usage — if a word appears once, it tends to appear
again nearby. Burstiness B = (σ−μ)/(σ+μ) for inter-occurrence gaps:

- **Mean B = 0.246** (natural language typical: 0.2−0.5)
- 93% of words have B > 0.1 (clearly bursty)
- 0% have B < −0.1 (none mechanical/regular)
- Poisson null: B = −0.005

This is the strongest evidence for genuine topical content. Burstiness
is a property of natural language (content words cluster around topics)
and is INCOMPATIBLE with mechanical generation (which produces uniform
distributions). However, any cipher of natural language would preserve
burstiness.

### 4.7 Phonotactic Positional Structure (93% NEW, Phase 52d)

Character entropy varies strongly by position within words:
- Position 1: H=3.02 (o=24%, c=16%, q=15%) — constrained
- Position 2: H=3.01 (h=26%, o=22%, a=15%) — constrained
- Position 3-4: H=3.21-3.31 — most varied ("middle" of word)
- Position 5+: H declining (y=28%, n=18% dominate) — suffix-like

Skip-gram MI within words: 0.894 bits at gap 2, 0.499 at gap 3.
Position explains 17.3% of character choice.

This pattern (constrained beginnings, varied middles, constrained
endings) is characteristic of natural phonotactic systems, not
cipher artifacts.

### 4.8 Gallows Dominance at Paragraph Starts (99% NEW, Phase 71)

The four EVA gallows characters (p, t, k, f) account for **81.9% of all
paragraph-initial characters** despite comprising only ~10.5% of general
character frequency. This is the most extreme positional bias found in
the manuscript:

- **p**: 44.9% of paragraph starts vs 1.0% baseline (**45.6× enrichment**)
- **t**: 22.2% vs 3.6% (**6.2×**)
- **k**: 10.3% vs 5.5% (1.9×)
- **f**: 4.0% vs 0.4% (**10.3×**)
- **o** (most common char): 4.0% vs 13.0% (**0.31× — actively suppressed**)

χ² = 16,905 (df=18, p ≈ 0). NOT a line-initial artifact: paragraph starts
differ categorically from non-paragraph line starts (χ² = 15,884). The
effect is consistent across ALL manuscript sections (66–88% gallows at
paragraph starts).

79% of paragraph-initial words (451/573 unique forms) appear ONLY at
paragraph starts — never in body text. These are a distinct vocabulary
class, not ordinary words that happen to occur first.

Interpretation: gallows likely serve as paragraph-type markers encoding
information about what follows (e.g., Latin recipe openings like
"Recipe", "Accipe", "Pone", "Fiat"), or as a cipher-mode/key indicator.
This constrains any decipherment: the first word of each paragraph
carries different information than body words.

---

## 5. What This Rules Out

### 5.1 Random or Meaningless Text — EXCLUDED

The manuscript is not gibberish. Morphological structure at z=119.7
and syntactic structure at z=80+ are incompatible with random generation.
A random process would not produce consistent suffix→prefix transitions
that generalize to held-out data at 94.7% retention.

### 5.2 Simple Substitution Cipher on European Language — UNLIKELY

A monoalphabetic cipher on English/Latin/Italian would preserve the
source language's word-length distribution, character entropy, and
bigram patterns. Voynichese has:
- Much lower H(char|prev) than any European language (1.92 vs 3.1-3.3)
- Shorter mean word length (4.01 vs 4.3-5.5)
- Agglutinative morphology (suffix + prefix on stems) unlike European
  inflection patterns

If it is a cipher, it is not a simple one, and the source language
is probably not European.

### 5.3 Logographic Script — EXCLUDED

The alphabet of ~20-26 characters is far too small for a logographic
system (Chinese uses 3,000+). This is an alphabetic or syllabic script.

### 5.4 Purely Constructed Language (à la Esperanto) — CANNOT EXCLUDE

**CORRECTION (Phase 51):** Our earlier claim that sparse bigrams
exclude constructed language was wrong. VMS bigrams are actually LESS
sparse than random (51% vs 65% unseen). The no-discrete-classes and
high hapax ratio arguments also don't distinguish natural from
constructed: a sufficiently complex constructed system could produce
both.

Moreover, the anti-compositional vocabulary (z=−25.4) is INCONSISTENT
with a productively-generated agglutinative language — which applies
both to natural agglutinative languages AND to constructed ones that
rely on free morpheme combination. The vocabulary behaves more like
a closed list with shared character patterns at edges.

### 5.5 Meaningless but Structured ("Glossolalia Hypothesis") — NOT EXCLUDED

One hypothesis that our analysis **cannot** exclude: the text could be
structured but semantically empty — generated by someone who internalized
the statistical patterns (like speaking in tongues with consistent
"grammar"). We can show the structure is real but cannot prove it
carries referential meaning.

---

## 6. What This Is Consistent With

After Phase 52's discrimination tests, the picture has sharpened:

1. **A natural language** with strong phonotactic constraints or a
   syllabic script, where word-final sounds predict word-initial sounds
   of the following word (sandhi-like processes). Supported by:
   burstiness (B=0.246), phonotactic positional structure, U-shaped
   surprisal curve within lines.

2. **A cipher or encoding of natural language** that preserves word
   boundaries. Not a simple substitution cipher (character patterns
   don't match European languages), but possibly a more complex
   system. Burstiness would be preserved by any word-level cipher.
   Phonotactic structure could reflect encoding rules rather than
   natural phonology.

3. ~~**A mechanical generation system**~~ — **NOW LARGELY EXCLUDED.**
   Phase 52b showed ALL 100 tested words are bursty (B>0). Random or
   mechanical generation produces B≈0 (Poisson). The simple grille
   also fails on MI (36× too little). Some very sophisticated generation
   mechanisms that deliberately produce burstiness might still work,
   but this requires increasingly complex assumptions.

4. **Structured glossolalia** — someone producing text with internalized
   statistical patterns. This remains possible but must account for
   burstiness (topical clustering) and phonotactic structure, which
   argues for a sophisticated mental model.

What we can say with confidence:
- **Line-as-sentence** structure (syntax resets at line boundaries)
- **Local character dependencies** (gap 1 only, left-to-right)
- **Bursty word distribution** (topical structure, natural language range)
- **Phonotactic positional structure** (constrained word edges)
- **Not random, not a simple cipher, not logographic, probably not mechanical**
- **Verbose cipher excluded** (MI 4× too low for word=letter, Phase 53)
- **IC too high for European cipher** (0.09 vs max 0.077, Phase 53)
- **Word length carries grammatical information** (6.5% of H, Phase 54)
- **Hapaxes are topic-clustered** (χ²=216, Phase 54)
- **Word-finals are grammatical, not terminators** (z=313, Phase 62)
- **Gallows dominate paragraph starts** (81.9% vs 10.5% baseline, Phase 71)
- **Paragraph-initial words are a distinct vocabulary** (79% unique to that position, Phase 71)
- **Overall: natural language modestly favored over cipher** (70%, Phase 62)

---

## 7. The Generative Model

The simplest model that captures the established structure:

**To generate a Voynich line:**

1. **Choose line length** (mean 7.93, sd 4.33 words)
2. **Generate word 1:**
   - Pick suffix from marginal distribution (H = 2.99 bits)
   - Pick gram prefix — d-prefix enriched 2.5× for line-initial position
   - Pick stem given suffix (H = 4.33 bits)
   - Assemble: prefix + stem + suffix
3. **For each subsequent word:**
   - Pick gram prefix **conditioned on previous suffix** (the grammar)
   - Pick suffix from marginal distribution
   - Pick stem given suffix
   - Assemble
4. **Line break resets** — no dependency across lines

This model captures the morphological grammar (MI = 0.083 bits saved
per transition) but NOT the word-specific tendencies that exist in
the real data. It produces text with roughly correct type-token ratio
and hapax ratio, but the Zipf distribution is slightly different and
self-repetition rate is too low (0.5% vs 2.0% real).

The gap between this model and reality represents the word-specific
information we cannot capture: about 80% of word-level predictability
that exists in the data but doesn't generalize.

---

## 8. What No Amount of Further Statistical Testing Will Resolve

After 54 phases of analysis, we have reached the point where statistical
analysis of this corpus alone cannot make further decisive progress.
The remaining questions require external information:

1. **Phonetic values.** Statistics can measure patterns but not assign
   sounds to symbols.
2. **Language identity.** Without knowing the sound values, we cannot
   match the phonotactic patterns to a specific language.
3. **Content meaning.** We can determine that structure exists but
   not what it encodes.
4. **Cipher vs. plaintext.** Statistical structure is compatible with
   both a natural language and a sophisticated cipher. Our tests
   modestly favor natural language (65%) but cannot be decisive.
5. **The semantic content of stems.** Stems are the opaque core and
   carry whatever lexical meaning exists.

The most productive next steps would be:
- Comparing VMS statistics to specific candidate languages (requires corpora)
- Testing specific decipherment hypotheses (requires phonetic mappings)
- Cross-referencing with codicological/historical evidence

### Phases 55–56: V/C Separation and Its Self-Correction

Phase 55 ran Sukhotin's algorithm and found a degenerate V/C split:
13/22 characters classified as "vowels" (91.4% of tokens), V/C
ratio 10.6, and V/C alternation BELOW random (z = −3.3).

Phase 56 ATTACKED this result and found:
- **The degenerate split is an ARTIFACT.** Random text generated from
  the VMS bigram model produces the same degenerate Sukhotin result
  (12.7±0.5 vowels vs VMS's 13, z = 0.7 — not different).
- **SVD rank is normal.** VMS transition matrix rank(90%) = 8 out of
  15, identical to the bigram null model (z = 0.0). No evidence of 
  the low-rank CV-grid structure that a true syllabary produces.
- **Character clustering shows NaN JSD** due to distribution sparsity,
  preventing distributional grouping analysis.

However, the alternation rate IS genuinely lower than the bigram null
(0.116 vs 0.100, z = 15.9), meaning VMS characters cluster together
MORE than even the bigram model predicts. This is a real signal, but
it's a QUANTITATIVE deviance in character clustering, not a QUALITATIVE
exclusion of any script type.

**What Phase 55's degenerate split ACTUALLY tells us:**
- VMS character frequencies are extremely skewed (top 11 chars = 95%)
- Characters freely combine with each other (no V/C partition)
- This is inconsistent with European alphabetic text (moderate claim)
- But it does NOT exclude alphabetic encoding in general

**REVISED CONFIDENCES (Phase 56):**
- Syllabary hypothesis: 70% (DOWNGRADED from 85%)
- Alphabetic exclusion: 75% (DOWNGRADED from 90%)
- Cipher still consistent

**SVD-based character groups** (the genuinely new finding):
- {q} is its own group (word-initial marker)
- {c, s} cluster together (medial position)
- {a, i} cluster together
- {h, l, o, y} cluster together
- {d, e, n, r} cluster together

These groups explain 85% more transition entropy than random groupings
(z = −8.2 at k=3). The grouping is REAL, even though the syllabary
interpretation is not confirmed.

---

## 9. Methodological Notes

### What Went Right
- **Systematic self-attack:** Every claim was tested by trying to break
  it. Multiple initial findings were retracted (Phases 27, 32-33, 35,
  41, 43, 46, 48, 51). What survives is robust.
- **Cross-validation:** The decisive tool. Feature-level grammar passes
  (94.7% retention); word-level doesn't.
- **Finite-sample bias awareness:** Most "anomalous" signals were
  inflated by sparse data. Proper null models (unigram baselines,
  permutation tests) separated real from artifactual.

### What Went Wrong
- **Phases 44-49 were partly circular:** Claims about word-level
  predictability (Phase 44-45) were retracted (Phase 46-48) then
  the wreckage was confirmed (Phase 49). The net discovery from 6
  phases could have been achieved in 2-3 with better null models upfront.
- **Early root-meaning speculation (Phases 24-26) was mostly wrong:**
  Phase 27 audited and found only 30% of predictions passed. The
  morphological STRUCTURE is real; the specific TRANSLATIONS were not.
- **Parser artifacts persisted for 8 phases** before being caught
  (Phase 32). The binary suffix split, -edy/-ey suffixes, and same-stem
  co-occurrence were all artifacts of greedy longest-match parsing.

### The Central Lesson
The Voynich manuscript's structure is real but operates at a level
(morphemes, character sequences) that statistical analysis can detect
but not decode. The word-level information that would matter for
translation is too sparse to extract computationally from a 35K-token
corpus. Decipherment, if possible, will require a key — external
information about the script or language that statistical analysis
alone cannot provide.

### Phase 57: External Decipherment Testing

Phase 57 pivoted from internal statistical profiling to testing an
external decipherment proposal: the Bax/Vogt phonetic system (2014-2016).
Stephen Bax proposed ~14 character-sound correspondences anchored by
plant and star name identifications; Derek Vogt extended this to a
near-complete phonetic system covering all major EVA characters.

**Key results:**
- The Vogt mapping applied to f2r (the "centaurea" folio) produces NO
  clear phonetic match with any centaurea cognate. Best edit distance:
  EVA "kydainy" → "kntwn" vs "kentaurion" (normalized dist = 0.600).
  The labels "ytoail" → "ngaws" and "iosanon" → "aSwa" are distant
  from all centaurea forms (dist ≥ 0.75).
- 9.9% of random mappings produce equally good or better centaurea
  matches (p = 0.099, not significant at 0.05 level).
- Vogt's V/C assignments {o,a,e}=vowels span TWO SVD character groups,
  while his consonants span THREE — the mapping does NOT respect the
  manuscript's own internal character classes.
- The mapping produces 40.4% vowels in running text (within natural
  language range of 40-55%) and raises conditional entropy from 1.92
  to 2.20 bits (toward but not reaching natural language levels).
- V/C alternation under Vogt's system (0.74 raw, 0.71 mapped) falls
  within natural language range (0.55-0.75).

**Critical insight:** With ~17 EVA characters mappable to ~17 phoneme
values, the combinatorial space contains ~8×10²⁰ possible mappings.
Finding plant-name "matches" by adjusting character-sound pairs is
almost guaranteed in this space — the multiple comparisons problem
renders individual cognate matches unpersuasive without strong
independent constraints.

**What Phase 57 does NOT do:** This analysis cannot prove Bax/Vogt
wrong. The mapping was developed using many folios, not just f2r.
What it shows is that the f2r centaurea evidence alone — often cited
as the flagship example — does not statistically distinguish the
Bax/Vogt mapping from random alternatives.

### Phase 58: Cross-Script Statistical Fingerprinting

Phase 58 computed the same battery of metrics on VMS and on reference
texts in 7 European languages (English, Latin, Italian, German, Spanish,
French, Finnish), 4 non-Latin scripts (Japanese hiragana, Korean hangul,
Arabic, Hawaiian), and 2 cipher variants (substitution and bigram cipher
of English). Ten features: alphabet size, character entropy, conditional
entropy, bigram predictability ratio, IC, mean word length, type-token
ratio, hapax ratio, Sukhotin vowel fraction, and V/C alternation.

**Key result — VMS clusters with European alphabets:**
- Nearest neighbors: Spanish (d=2.30), Latin (d=2.52), Italian (d=2.82)
- All top-5 neighbors are alphabetic European languages
- Syllabaries (Japanese, Korean) are distant; bigram cipher is farthest

**BUT VMS has extreme character-level anomalies** (z-scores vs 7 NL alphabets):
- H(char|prev) = 2.47 bits vs NL mean 3.48 → **z = −19.9** (EXTREME)
- H-ratio = 0.64 vs NL mean 0.84 → **z = −12.6** (EXTREME)
- IC = 0.082 vs NL mean 0.069 → **z = +5.9** (EXTREME)
- H(char) = 3.86 vs NL mean 4.13 → **z = −3.5** (EXTREME)

**VMS is NORMAL on all word-level metrics:**
- Alphabet size (32, z=0.3), mean word length (4.94, z=0.4)
- TTR (0.27, z=−0.1), hapax ratio (0.66, z=0.3)
- Sukhotin V-fraction (0.28, z=−1.1), V/C alternation (0.73, z=0.7)

**Interpretation:** VMS looks like a normal European alphabet at the
vocabulary level but has dramatically too-predictable character sequences.
This pattern is NOT produced by simple substitution cipher (which
preserves all source statistics perfectly). It IS consistent with:
1. A script or encoding that introduces artificial character-level
   regularity (e.g., verbose cipher, abbreviated notation, or syllabic
   encoding with a small symbol subset)
2. A natural language with exceptionally constrained phonotactics
   (but no known NL approaches z=−20 on conditional entropy)
3. A mixed system where common words are stereotyped character patterns

The conditional entropy anomaly (z=−19.9) is the single most
discriminating feature. No reference text — natural language, cipher,
or syllabary — matches VMS on this metric. VMS character sequences are
far more predictable than any comparison system at the bigram level,
while maintaining perfectly normal word-level statistical properties.

**REVISED CONFIDENCES (Phase 58):**
- Syllabary hypothesis: **60% (DOWNGRADED from 70%)** — VMS IC and
  alphabet size are wrong for a syllabary; clustering is alphabetic
- Not European alphabetic text: **80% (UPGRADED from 75%)** — VMS
  clusters NEAR European alphabets but the H(c|prev) z=−19.9 anomaly
  means it cannot be straightforward alphabetic text in any tested
  European language

### Phase 59: Forward Modeling — What Process Reproduces the VMS Fingerprint?

Phase 59 inverted the question: instead of asking what VMS resembles,
it asked what PROCESS applied to Italian (Dante’s Inferno) can
REPRODUCE the VMS 10-feature fingerprint. Nine encoding schemes tested:
syllabic encoding (3 variants), onset-rime decomposition, verbose
positional cipher (2 variants), abbreviation shorthand, and simple
substitution (benchmark).

**Key result: the verbose positional cipher nails H(c|prev):**
- Scheme 3a (vowels → 2 cipher chars, consonants → 1 cipher char)
  produces H(c|prev) = 2.453 — almost exactly VMS’s 2.471 (Δz = 0.36)
- It also matches TTR (Δz=0.02), hapax ratio (Δz=0.02), word length
  (Δz=0.94), and V/C alternation (Δz=0.94)
- BUT its alphabet has only 13 characters (VMS has 32), IC is too high,
  and H(char) is too low

**Syllabic encoding completely fails:** All three syllabic schemes
produce H(c|prev) = 3.9–4.3 — HIGHER than natural language, not lower.
Mapping syllables → random character codes introduces randomness at
code boundaries, increasing conditional entropy. This is the opposite
of the VMS pattern.

**The diagnostic insight:** The VMS H(c|prev) anomaly is specifically
reproduced by a process where SOME source characters expand to
deterministic multi-character sequences (like vowel ‘a’ always becoming
‘ba’). This creates within-expansion predictability that crushes bigram
entropy. But VMS has more characters (32) than a simple verbose cipher
produces (13), suggesting:
1. Multiple encoding rules operate simultaneously (some characters
   expand, some don’t, with position-dependent variants), OR
2. The large “alphabet” includes positionally-specialized characters
   that never compete — like VMS’s gallows (word-medial only), q
   (word-initial only), y (word-final) — producing high total alphabet
   count but low EFFECTIVE alphabet at any given position

This second possibility aligns perfectly with Phase 52d (positional
entropy: H drops from 3.3 in mid-word to 3.0 at edges) and Phase 56’s
SVD groups (5 character clusters with distinct positional profiles).

**No encoding scheme beat the nearest natural language (Spanish, d=2.30)**
in overall distance. The verbose cipher was closest at d=8.31. The
alphabet-size gap (13 vs 32) is the primary residual.

**REVISED CONFIDENCES (Phase 59):**
- Syllabic encoding of NL: **35% (DOWNGRADED from 60%)** — syllabic
  encoding goes in the WRONG direction on conditional entropy
- Verbose/expansion encoding: **75% NEW** — only process that
  reproduces the critical H(c|prev) ≈ 2.47 anomaly
- Positional character specialization: **85%** — large alphabet +
  low H(c|prev) requires position-specific character roles

### Phase 60: Positional-Variant Verbose Cipher — Closing the Alphabet Gap

Phase 60 directly addressed Phase 59's primary residual: the verbose
cipher matched H(c|prev) but had only 13 characters (VMS has 32). The
hypothesis: if cipher characters vary by POSITION within the word
(initial, medial, final zones), the same source letter produces
different cipher output at different positions, multiplying the
effective alphabet while preserving within-expansion predictability.

Six fixed encoding schemes tested (3-zone and 5-zone variants with
different sharing fractions), plus a 324-parameter grid search over
zone count, shared/unique character counts, and expansion probability.

**Key result: 9 of 10 features now match VMS within 2σ.**

Best model (3-zone, 4 shared + 3 unique consonant chars, 2 shared +
5 unique vowel chars, 80% vowel expansion):
- Alphabet size: 30 (VMS: 32) — gap nearly closed
- H(char): 3.945 (VMS: 3.857) — now within 1.1σ
- H(c|prev): 2.601 (VMS: 2.471) — Δz=+2.56, the ONLY remaining miss
- IC: 0.084 (VMS: 0.082) — excellent match
- TTR, hapax, V-frac, VC-alt: all within 2σ

**Distance from VMS dropped 53%:** 8.31 (Phase 59) → 3.94 (Phase 60).
Still doesn't beat Spanish (d=2.30), but the position-variant verbose
cipher is now the closest ARTIFICIAL model to VMS ever tested in this
project.

**Positional entropy comparison:**
| Zone | Cipher H | VMS H | Cipher types | VMS types |
|----------|----------|-------|-------------|----------|
| initial | 2.72 | 3.16 | 8 | 24 |
| early | 3.60 | 3.22 | 18 | 22 |
| medial | 3.54 | 3.22 | 19 | 23 |
| late | 3.03 | 2.65 | 16 | 17 |
| final | 2.90 | 2.45 | 17 | 22 |

The cipher reproduces the SHAPE (constrained edges, varied middle) but
undershoots initial diversity (8 vs 24 types) and overshoots final
entropy (2.90 vs 2.45). VMS has more characters competing at each
position than a simple 3-zone model predicts.

**What this means:**
1. A verbose cipher with positional character variants is the best
   statistical match for VMS found in 60 phases of analysis
2. The mechanism — vowels expand to deterministic 2-char sequences,
   with expansion characters varying by word position — simultaneously
   explains the extreme bigram predictability AND the large alphabet
3. The remaining gap (H(c|prev) Δz=2.56, still farther than Spanish)
   suggests either finer positional granularity, source language effects
   (Italian ≠ actual source), or EVA transcription artifacts

**REVISED CONFIDENCES (Phase 60):**
- Verbose/expansion encoding: **80% (UPGRADED from 75%)** — only
  encoding class that approaches VMS on all 10 features simultaneously
- Positional character specialization: **90% (UPGRADED from 85%)** —
  position-variant model matches 9/10 features, closes alphabet gap
- Syllabic encoding of NL: **30% (DOWNGRADED from 35%)** — verbose
  cipher outperforms all syllabic variants by a factor of 5–10×

### Phase 61: Word-Shape Validation — Is the 10-Feature Match Real or Superficial?

Phase 61 tested whether the position-variant verbose cipher (Phase 60)
produces VMS-like word SHAPES, not just matching summary statistics.
Nine micro-level word-shape metrics compared against VMS, with simple
substitution of Italian as a control.

**Result: PARTIAL validation — cipher wins 4/9 word-shape metrics.**

What the cipher REPRODUCES:
- Bigram rank correlation (ρ: cipher best of all 3 comparisons)
- Initial character concentration (HHI Δ=0.042 vs VMS)
- Final character concentration (HHI Δ=0.089 vs VMS)
- Word repetition rate (89.3% vs VMS 89.1% — almost exact)

What it FAILS to reproduce:
- Word-length distribution (L1=0.69, cipher words too long/spread)
- Positional entropy curve (r=−0.45: ANTI-correlated with VMS;
  VMS drops from mid to final, cipher rises)
- Bigram Jaccard overlap (near zero — cipher and VMS share almost
  no specific top bigrams, despite correlated ranks)
- Cross-word boundary delta (cipher suppresses too much: Δ=−0.30
  vs VMS −0.04)
- Zipf slope (cipher −0.87 vs VMS −0.66)

**Critical insight: The cipher's positional entropy curve is
ANTI-CORRELATED with VMS.** VMS entropy drops steadily from
position 3 (H=3.63) to position 7 (H=2.79). The cipher's entropy
RISES from position 1 (H=2.68) to position 7 (H=3.76). This means
the cipher's position-variant mechanism produces the WRONG shape of
positional predictability — the 3-zone model makes initial positions
too constrained and final positions not constrained enough, opposite
to VMS's pattern.

**What this means:**
1. The 10-feature match (Phase 60) captures REAL macro-level
   properties (repetition rate, initial/final concentration,
   bigram rank structure) — it's not completely superficial
2. But the micro-level word shape is wrong: wrong length
   distribution, wrong positional entropy curve, wrong specific
   bigrams
3. The position-variant verbose cipher is in the right FAMILY
   of explanations but the specific positional mapping (3-zone
   with uniform zone boundaries) doesn't reproduce VMS's actual
   character distribution within words

**REVISED CONFIDENCES (Phase 61):**
- Verbose/expansion encoding: **75% (DOWNGRADED from 80%)** — macro
  match confirmed but micro-level word shapes diverge significantly
- Positional character specialization: **90% (UNCHANGED)** — the
  cipher's initial/final HHI match confirms position matters; the
  problem is the SPECIFIC positional mapping, not the principle

### Phase 62: Functional Anatomy of the VMS Word — What Are Finals?

Phase 61 revealed that VMS positional entropy DROPS toward word-final
positions (3.63→2.79) while the verbose cipher's entropy RISES. This
anti-correlation was the key unexploited clue. Phase 62 asked: if VMS
finals are so constrained (only 8 characters, dominated by y=40.7%,
n=16.9%, l=15.8%, r=15.6%), what ROLE do they play?

Three hypotheses tested:
- **(A) Terminators** — content-free end markers (like punctuation)
- **(B) Grammar** — inflectional morphemes (like English -ed, -ing)
- **(C) Content** — constrained but information-bearing characters

**Method:** Decomposed 36,259 VMS words into (first, middle, last)
zones. Measured mutual information of each zone with five context
variables: section (topic), line position (syntax), next word's
initial (forward grammar), previous word's final (backward grammar),
and stem (zone↔core coupling). All MI values tested against 500
permutation shuffles to compute z-scores and NMI. Italian (Dante,
50K words) used as comparison with pseudo-sections.

**Key results:**

| Measurement | VMS last | VMS first | Italian last |
|---|---|---|---|
| NMI with section (topic) | 0.018 (z=128) | 0.042 (z=294) | 0.001 (z=5) |
| NMI with next_init (fwd grammar) | **0.080 (z=313)** | 0.026 (z=114) | 0.044 (z=232) |
| NMI with prev_final (bwd grammar) | 0.011 (z=35) | 0.085 (z=308) | 0.031 (z=151) |
| NMI with stem (core coupling) | **0.680 (z=401)** | 0.576 (z=441) | 0.720 (z=525) |
| NMI with line position | 0.021 (z=158) | 0.034 (z=249) | 0.001 (z≈0) |

**The dominant signal is forward grammar:** VMS last→next_init has
the STRONGEST z-score of any zone×context pair (z=313.2, NMI=0.080).
This is 1.8× stronger than Italian's equivalent (NMI=0.044). The
reverse — first←prev_final — is symmetrically strong (z=308), forming
a bidirectional inter-word grammar chain.

**Finals are NOT pure terminators.** Position-resolved MI curves show
MI(char; section) RISES at later positions (0.108→0.156 bits), despite
character entropy dropping. If finals were content-free end markers,
MI with topic would approach zero. Instead it increases — the handful
of finals carry MORE topical information per bit than early characters.

**Finals carry genuine content too.** NMI(last; stem) = 0.680, actually
HIGHER than NMI(first; stem) = 0.576. Finals are more tightly coupled
to the word core than initials. This is unusual — in Italian, the
pattern is reversed (first: 0.796 > last: 0.720).

**Chi-squared cross-tab:** Final char × section gives χ²=1690.8
(df=30, χ²/df=56.4), showing major section dependence. Example:
'y' ranges from 32.3% (pharma) to 53.7% (bio); 'r' from 9.4% (bio)
to 22.7% (cosmo2). Italian's equivalent: χ²/df=2.6 (pseudo-sections).

**Verdict: GRAMMAR with content hybrid (score: Grammar 6, Content 4,
Terminator 0).** VMS word-finals function primarily as grammatical
morphemes — they strongly predict the next word's initial and are
sensitive to line position — but they also carry genuine topical
information (z=128) and are tightly coupled to stems (NMI=0.68).
This is consistent with inflectional suffixes in a natural language,
where endings mark grammatical case/number while also being partly
determined by the word's meaning.

**What this means for the cipher model:** The verbose cipher's
anti-correlated positional entropy is now explained. VMS finals are
constrained because they are a small inflectional set (like -ed, -ing,
-s in English), not because they are redundant cipher padding. Any
encoding model must preserve this grammatical function at word
boundaries — simple positional variant mapping cannot reproduce it.

**Skeptical caveats:** (1) Section labels are approximate (MI is a
lower bound). (2) Italian pseudo-sections are a weak baseline. (3)
The zone decomposition is arbitrary at 1-character boundaries (but
Phase 51 showed 95.6% of morphological MI is single-character). (4)
"Grammar" vs "content" is a simplified dichotomy — real morphemes
serve both roles simultaneously.

**REVISED CONFIDENCES (Phase 62):**
- Word-final characters are grammatical: **85% NEW** — z=313 forward
  grammar signal, strongest inter-word MI of any zone
- Word-final characters carry content: **80% NEW** — NMI(last;stem)=
  0.680, MI(last;section) z=128, position MI rises toward finals
- Pure terminators: **<5% EXCLUDED** — every MI test shows genuine
  information in finals
- Verbose/expansion encoding: **70% (DOWNGRADED from 75%)** — the
  grammar-at-boundaries finding further constrains viable models;
  simple expansion cannot produce grammatical finals
- Natural language slightly favored over cipher: **70% (UPGRADED from
  65%)** — the grammatical final pattern is characteristic of natural
  language; reproducing it via cipher requires additional mechanism

---

## Appendix: Cumulative Retractions

| Finding | Claimed | Retracted | Reason |
|---------|---------|-----------|--------|
| h-verbal prefix | Phase 28 | Phase 35 | Only 2 genuine h-tokens |
| 's' as gram prefix | Phase 34 | Phase 35 | Always part of 'sh' |
| Binary suffix split | Phase 31 | Phase 32 | Greedy parser artifact |
| -ody suffix | Phase 32 | Phase 33 | Parser artifact |
| Vowel-initial suffixes (-edy, -ey, -eedy) | Phase 31 | Phase 32 | Parser steals stem vowels |
| Same-stem co-occurrence = inflection | Phase 31 | Phase 33 | Anti-correlated (z=−33) |
| "Alphabetic encoding excluded" (90%) | Phase 55 | Phase 56 | Bigram null produces same Sukhotin result |
| "Syllabary hypothesis" (85%) | Phase 55 | Phase 56 | No SVD low-rank structure, downgraded to 70% |
| 74.4% class interaction (raw) | Phase 41 | Phase 41 | 62% was finite-sample bias |
| Section-specific grammar rules | Phase 42 | Phase 43 | Marginal frequency differences only |
| Anomalous MI/H = 0.377 | Phase 45 | Phase 46 | 88% finite-sample bias |
| Position 1 most constrained | Phase 45 | Phase 46 | Fewer types, not special |
| 40.6% word-level PP reduction | Phase 44 | Phase 48 | Doesn't generalize (4.4× worse) |

---

### Phase 63: Codicological Coherence — Testing the Misbinding Hypothesis

External evidence (Lisa Fagin Davis, *Manuscript Studies* 2020; blog
"Voynich Codicology" Jan 2025) establishes that 5 scribes wrote the VMS,
bifolia are misbound within quires, and a catastrophic water spill led
to disbinding/rebinding in the wrong order. Phase 63 tests whether we
can detect these codicological facts from text statistics alone, and
evaluates how misbinding affects our earlier findings.

**Six tests, key results:**

| Test | Result | Significance |
|------|--------|-------------|
| Vocabulary Jaccard: same vs cross-language adjacent folios | Same-lang J=0.136, cross-lang J=0.062 | z=2.7, cross-lang breaks visible |
| Cross-folio bigram MI | Inflated by small-sample bias (N=199 vs 36059) | INCONCLUSIVE |
| K-means clustering vs Currier A/B | 80% agreement in botanical | Scribe detection VIABLE from statistics |
| MI(final_char, language_type) | NMI=0.006, z=41.0 | Word-finals STRONGLY distinguish A from B |
| Section-MI sensitivity (20–30% perturbation) | Retains 91–94% of baseline MI | Phase 62 findings ROBUST to misbinding |
| Within-quire same vs cross-language cosine | Same=0.904, Cross=0.853, z=10.2 | Scribal difference CONFIRMED statistically |

**Critical finding — interleaving detection:** K-means clustering of
character frequencies independently detects interleaved scribe patterns
within quires 4 (6 switches) and 6 (7 switches), exactly as Davis found
through paleographic analysis. Quires 1–3 show zero switches (pure
Scribe 1), also matching.

**Language A vs B profile:** Vocabulary Jaccard between A and B is only
0.233 — remarkably low for "the same language in different hands."
Key final-character differences: `y` is 4.4% more common in B, `n` is
2.8% more common in A. Key initials: `o` 4.3% more in B, `ch` 3.2%
more in A. Top-50 word overlap is 37/50.

**Implications for our analysis:**
1. Section assignments (herbal/astro/bio) are UNAFFECTED by misbinding —
   they are defined by illustration content, not folio sequence
2. Misbinding could cause our cross-folio analyses to UNDERESTIMATE true
   inter-page coherence
3. Two distinct writing styles organized by bifolium is STRONG EVIDENCE
   against hoax — a forger would produce one style, not two
4. Multi-scribe verbose cipher is harder to maintain consistently across
   5 scribes, weakening that hypothesis

**REVISED CONFIDENCES (Phase 63):**
- Natural language favored: **75% (up from 70%)** — multi-scribe + two
  language types + consistent grammar organized by bifolium
- Verbose encoding possible: **65% (down from 70%)** — harder to
  maintain across 5 scribes
- Random/hoax: **<5% (down from ~10%)** — bifolium-organized two-style
  production makes hoax extremely unlikely

---

### Phase 64: Encoding Model Tournament — Generative Discrimination

Instead of characterizing VMS, Phase 64 **generates synthetic text under
each encoding hypothesis** applied to Italian (Dante), computes a battery
of 7 statistics on each, and scores them against VMS by L2 distance in
z-normalized space.

**Models tested:** Italian raw, simple substitution, homophonic (fan=3),
syllabic encoding, verbose (letter→word), anagram (in-word shuffle),
null model (VMS char-freq + word-length matched random).

**The 7-statistic fingerprint:**

| Statistic | VMS | Italian | Syllabic | Null |
|-----------|-----|---------|----------|------|
| Heaps' β | 0.753 | 0.752 | 0.429 | 0.970 |
| Hapax @mid | 0.656 | 0.639 | 0.253 | 0.952 |
| H(c\|p)/H(c) | 0.641 | 0.839 | 0.839 | 0.999 |
| H(w\|p)/H(w) | 0.445 | 0.464 | 0.704 | 0.043 |
| Mean wlen | 4.94 | 3.93 | 2.15 | 4.94 |
| TTR @5K | 0.342 | 0.337 | 0.097 | 0.919 |
| Zipf α | 0.942 | 1.021 | 1.303 | 0.783 |

**Tournament ranking (L2 from VMS):**

| Rank | Model | L2 distance |
|------|-------|-------------|
| 1 | **Italian raw / Simple subst.** | **1.78** |
| 2 | Homophonic (fan=3) | 2.70 |
| 3 | Anagram | 3.17 |
| 4 | Syllabic encoding | 3.35 |
| 5 | Null (VMS-matched) | 4.19 |
| 6 | Verbose (letter→word) | 5.01 |

**Critical results:**

1. VMS matches natural language / simple substitution (L2=1.78) and is
   **2.4× closer** to NL than to the null model (4.19). Structure is
   NOT just unigram char-freq + word lengths.

2. **Heaps' β = 0.753** — virtually identical to Italian (0.752). VMS
   has an open, productive vocabulary that grows exactly like natural
   language. This eliminates syllabic encoding (β=0.43) and verbose
   cipher (β=0.08) at the vocabulary-dynamics level.

3. **The ONE anomaly:** H(c|prev)/H(c) = 0.641 for VMS vs 0.839 for
   Italian. Character bigram predictability in VMS is far higher than
   any natural language model produces. This +1.7σ deviation is the
   residual fingerprint of whatever encoding/script system is in play.

4. **A vs B have identical vocabulary dynamics:** β_A=0.756, β_B=0.732,
   |Δβ|=0.024. Combined vocab grows 29.4% over the larger — squarely
   in the "overlapping vocabulary" zone, NOT "different languages."
   Phase 63's Jaccard=0.233 is explained by A having 2× more text and
   more hapax legomena, not genuinely disjoint vocabularies.

5. Sections have 29-53% unique vocabulary each, with herbal (50.6%)
   and text (53.1%) most distinct. Cross-section Jaccard matrix shows
   moderate overlap (0.12–0.19), consistent with topically organized
   natural language.

**REVISED CONFIDENCES (Phase 64):**
- Natural language (possibly with monoalphabetic substitution):
  **80% (up from 75%)** — Heaps, Zipf, TTR, hapax, word-bigram all
  match NL fingerprint; only char-bigram deviates
- Syllabic encoding: **20% (was 30%)** — β=0.43 is 1.2σ too low;
  vocabulary dynamics don't match
- Verbose cipher: **excluded** — β=0.08, L2=5.01, rank last
- Hoax/random: **<3%** — null model L2=4.19, rank 5 of 7

---

### Phase 65: Reverse-Engineering the Script via BPE Merging

Phase 64's ONE anomaly — H(c|prev)/H(c) = 0.641 vs Italian 0.839 —
is the fingerprint of the writing system. Phase 65 asks: can we
reproduce this by merging common Italian character bigrams into single
symbols (BPE), simulating a partially syllabic script?

**Result: BPE FAILS to explain the anomaly.**

Even after 150 merges (creating a 184-symbol alphabet — implausibly
large), H(c|prev)/H(c) only drops from 0.839 to 0.790. The VMS target
is 0.641. BPE closes only 25% of the gap. More critically:

| Property | Italian raw | BPE-150 | VMS |
|----------|-------------|---------|-----|
| H(c\|p)/H(c) | 0.839 | 0.790 | 0.641 |
| Mean word length | 3.93 | 3.93 | 4.94 |
| Top-10 bigram conc. | 14.6% | 1.7% | **34.2%** |
| Mean successor H | 2.89 bits | 4.93 bits | **2.38 bits** |
| Positional entropy | 0.904 | 0.945 | **0.762** |
| Transition density | 0.478 | 0.393 | 0.464 |

**Three properties BPE cannot reproduce:**

1. **Top-10 bigram concentration = 34.2% in VMS vs 1.7% in BPE-150.**
   VMS transitions are dominated by a handful of pairs (q→o at 98%,
   i→n at 52%, d→y at 57%). BPE disperses concentration across many
   new symbols. VMS has the OPPOSITE structure: a small alphabet where
   a few transitions account for a third of all bigrams.

2. **Mean successor entropy = 2.38 bits in VMS vs 4.93 in BPE-150.**
   Each VMS glyph has very few plausible followers (q→o is nearly
   deterministic). BPE creates many symbols with many possible
   successors. VMS is MORE constrained, not less.

3. **Positional specialization = 0.762 in VMS vs 0.945 in BPE-150.**
   VMS glyphs concentrate in specific word positions: `q` is 99.5%
   word-initial, `i` is 99.9% word-medial, `y` is 88% word-final.
   BPE does NOT produce this pattern — it actually DECREASES
   positional specialization. This is a native property of the
   VMS writing system, not a byproduct of character merging.

**What the EVA compound glyphs explain:**
Merging ch/sh/th/kh/ph/fh into single glyphs explains only 18.2%
of the bigram anomaly (moves ratio from 0.597 to 0.641). The
remaining 82% comes from the STRUCTURE of the script itself.

**The VMS glyph q is the most constrained character in any known
writing system tested:** H(successor|q) = 0.184 bits. After `q`,
the next character is `o` 98.1% of the time. This is not explained
by any encoding model — it is a property of the SCRIPT.

**Critical implication:** The VMS character-bigram anomaly is NOT
explained by a syllabary-like script where symbols represent common
bigrams. It requires a script with:
- Mandatory character sequences (q→o, near-deterministic)
- Strong positional constraints (word-initial, medial, final sets)
- A handful of high-frequency transitions dominating the matrix

This pattern matches a **constructed or artificial writing system**
with explicit phonotactic rules — like an abugida or a conscript
with built-in syllable structure — NOT a cipher applied to any
tested natural language.

**REVISED CONFIDENCES (Phase 65):**
- Natural language in an unknown script: **80% (unchanged)** — all
  word-level stats match NL; the anomaly is in the SCRIPT, not in
  the LANGUAGE
- Simple substitution cipher: **WEAKENED to <10%** — cannot produce
  H(c|prev)/H(c) = 0.641; would preserve source ratio
- Syllabary hypothesis: **needs refinement** — BPE (digraph-merging)
  fails, but a script with POSITIONAL character variants could work
- Hoax/random: **<3%** — unchanged

---

### Phase 66: Data-Driven Glyph Resegmentation — Is EVA Over-Segmented?

Phase 65 concluded EVA may over-segment some glyphs (70% confidence).
Phase 66 tests this DIRECTLY on the VMS text by computing pointwise
mutual information for all within-word glyph pairs, checking for
complementary distribution (allographic variants), and merging
obligatory pairs to recompute the full fingerprint battery.

**Test A — MI Surgery:** Only ONE pair exceeds the 50% obligatoriness
threshold: **i+n** at min(P(n|i), P(i|n)) = 51.6%. The famous q→o
pair has 98.1% forward probability but only 35.1% reverse (o appears
frequently without q). Most EVA glyph pairs are NOT obligatory
co-occurrences — the script has fewer mandated bigrams than expected.

**Test B — Positional Specialization Confirmed:**
8/23 frequent glyphs have >85% positional concentration:
- **Initial-only:** q (99.5%), sh (73.9%)
- **Medial-only:** i (99.9%), e (98.9%), k (86.9%), a (84.0%), t (83.5%)
- **Final-only:** n (98.8%), m (96.8%), y (88.1%), r (80.2%)

Lowest Jensen-Shannon divergence pair: sh↔e at JSD = 0.163 (most
similar context distributions across positions) — but too distant
to claim allography.

**Test C — Merging Barely Closes the Gap:**

| Segmentation | Glyph types | H(c\|p)/H(c) | Gap from 0.839 | % closed |
|-------------|-------------|--------------|----------------|----------|
| EVA standard | 32 | 0.641 | 0.198 | baseline |
| qo merged | 33 | 0.649 | 0.190 | 4% |
| i+n merged | 33 | 0.660 | 0.179 | 10% |
| **Italian** | 35 | 0.839 | — | — |

Word-level stats (Heaps β, Zipf α, TTR) remain UNCHANGED by merging
— confirming the merges don't damage linguistic structure. But they
close only 4-10% of the gap. **90% of the anomaly survives.**

**Test D — Script Type:** H(c|p)/H(c) = 0.641 falls in the
**syllabary range** (0.55-0.70), but mean word length 4.43 glyphs
is too long for a typical syllabary (~3.2 for Japanese kana).
After i+n merging, H = 0.660 reaches the bottom of the abugida
range (0.65-0.78).

**Test E — ALTERNATION TEST FAILS (key surprise):** K-means clustering
of glyphs into 2 classes by successor distribution yields:
- Cross-class transitions: 41.9% vs 49.9% expected by chance
- **z = −54.7** — VMS has SIGNIFICANTLY LESS alternation than random
- `i` self-repeats 40.5% of the time; `e` self-repeats 26.1%
- No known alphabet, abugida, or syllabary has 40% character
  self-repetition

This **kills the simple abugida hypothesis**. A real C-V alternating
system would show z >> 0; VMS shows z << 0. The two glyph classes
CLUSTER rather than alternate.

**Critical synthesis:** The VMS writing system doesn't match any known
script type cleanly:
- Positional letter forms (like Arabic) but no allographic evidence
- Anti-alternation (unlike any natural writing system)
- Extreme self-repetition of medial glyphs (i, e)
- The H-ratio anomaly is INTRINSIC to the writing system — not an
  artifact of EVA over-segmentation

The 40% self-repetition of `i` (appearing in sequences like `aiin`,
`okaiin`) has no parallel in any known phonographic writing system.
It is more consistent with:
1. A quantitative/run-length notation (ii encodes magnitude)
2. A vowel length/quality system (repeats mark prosodic features)
3. An artificial script designed with positional constraints

**REVISED CONFIDENCES (Phase 66):**
- Natural language in unknown script: **80% (unchanged)** — word-level
  stats still match NL, but anti-alternation is a yellow flag
- Simple substitution cipher: **<5% (down from <10%)** — positional
  specialization cannot arise from a cipher
- EVA over-segmentation explains the anomaly: **WEAKENED to 30%
  (down from 70%)** — merging closes only 4-10% of gap
- Script has built-in phonotactic rules: **95% (up from 90%)** —
  positional sets + obligatory sequences confirmed by MI
- Script type: **anomalous** — H ratio says syllabary, word length
  says alphabet, alternation test says neither
- Self-repetition anomaly (i=40%, e=26%): **NEW finding, unexplained**
- Hoax/random: **<3%** (unchanged)

---

### Phase 67: Run-Length Morphology — What Are ii/iii/ee/eee Doing?

Phase 66 flagged `i`'s 40.5% self-repetition as unprecedented. Phase 67
dissects the functional role of these runs through six tests.

**Test A — Formal Slot Grammar:** 66.0% of VMS words conform to a strict
I*M+F* template (Initial-Medial-Final positional classes). The transition
matrix shows I→M = 90.5%, M→M = 58.8%, M→F = 36.8%. The I*M+F* grammar
is moderately regular — consistent with natural morphology, NOT so rigid
as to suggest an artificial template. The 34% violations mostly involve
`l`, `r`, `s` appearing in medial positions (they have split distributions).

**Test B — Run-Length Distribution (KEY FINDING):** The i-run distribution
is **peaked at length 2**, not length 1:

| Length | Count | % | Geometric expected | Ratio |
|--------|-------|-----|-------------------|-------|
| 1 | 2,338 | 34.6% | 59.5% | **0.58×** |
| 2 | 4,237 | 62.8% | 24.1% | **2.60×** |
| 3 | 176 | 2.6% | 9.8% | 0.27× |

`ii` is the DEFAULT form: 62.8% of all i-runs are length-2. Single `i` is
35% LESS common than geometric chance predicts; `ii` is 2.6× MORE common.
This is NOT what random repetition produces. For `e`, the peak is at
length 1 (67.6%) but length 2 is still 1.54× over-represented.

This peaked-at-2 distribution is most consistent with `ii` being a
**fundamental unit** that EVA over-segments, or a morphologically
mandated doublet (like Arabic shadda marking gemination).

**Test C — Context Independence:** Mean JSD = 0.828 for i-run variants,
0.877 for e-run variants. `dain` and `daiin` appear in DIFFERENT word
contexts. Each run length creates a **linguistically distinct word**.
This STRONGLY supports H1 (morphemic) and REJECTS H2 (numeric/tally).

Notably, the highest-frequency skeleton families (`a_n`, `qoka_n`) show
lower JSD (0.50-0.56) — partial interchangeability in the most common
word frames. Rarer frames show near-complete context divergence.

**Test D — Skeleton Recompute (SURPRISE):** Collapsing i+e runs makes
the H-ratio **WORSE**, not better:
- Collapse both: H = 0.6331 (Δ = −0.008, moves AWAY from Italian)
- Run-tokenize both: H = 0.6410 (Δ = +0.000, negligible)

The runs are NOT the mechanism behind the H-ratio anomaly. The anomaly
persists — and slightly worsens — when runs are removed. It arises from
the broader positional grammar (I→M→F constraint structure), not from
self-repetition specifically.

**Test E — Run-Length × Frequency:** Words with i×2 runs have HIGHER
mean frequency (7.5) than i×1 words (4.4). Correlation r = +0.16:
longer runs are slightly MORE common, not rarer. This contradicts the
tally-mark hypothesis (where longer = rarer) and is consistent with
`ii` being a high-frequency morpheme or base glyph.

**Test F — Anti-Alternation Decomposition:** i→i and e→e account for
89.4% of all self-transitions, but collapsing them closes only −3.9%
of the H-ratio gap (negative — makes it worse). The anti-alternation
from Phase 66 (z = −54.7) is partially explained by runs, but the
H-ratio anomaly is structurally independent of them.

**Critical synthesis:**

The H-ratio anomaly (0.641 vs 0.839) is NOT caused by:
- EVA over-segmentation (Phase 66: 4-10% closure)
- i/e self-repetition (Phase 67: −3.9% closure)
- BPE-style digraph merging (Phase 65: fails entirely)

It IS caused by the **positional slot grammar** itself: the constraint
that certain glyphs can only appear in initial/medial/final positions
creates a transition matrix where a handful of I→M and M→F pathways
dominate all character bigrams. This is the fingerprint of a writing
system with built-in positional rules — an intrinsic script property.

Meanwhile, `ii` behaves as a **morphemic unit**: it appears in distinct
word contexts, is peaked at length 2 (not geometric), and words
containing it are MORE frequent than those with single `i`. Whether
`ii` is one pen stroke split by EVA or a genuine doubled character
functioning as its own morpheme, it participates in word-formation
as a distinct element.

**REVISED CONFIDENCES (Phase 67):**
- Natural language in unknown script: **80% (unchanged)**
- Script has positional slot grammar (I-M-F): **95% CONFIRMED** —
  66% strict conformance + clean transition matrix
- i/e runs are morphemic, not numeric: **85% NEW** — high JSD (0.83),
  ll peaked at 2, positive freq correlation
- The H-ratio anomaly is caused by the slot grammar: **90% NEW** —
  Neither runs nor merges explain it; only positional constraints remain
- EVA may over-segment `ii` as a single glyph: **60%** — peaked-at-2
  distribution + morphemic behavior consistent with either hypothesis
- Simple substitution cipher: **<5%** (unchanged)
- Hoax/random: **<3%** (unchanged)

---

### Phase 68 — Run-Length-Conditioned Transitions: Currier A vs B

Phase 68 independently recomputes run-length-conditioned transition
probabilities across the entire VMS corpus, split by Currier language
(A vs B), and compares them to an external reference table.

**Test A: Run-Conditioned Successor Probabilities (verified against
external Currier A table)**

Our independently computed values closely match the external reference:
- `ii→n` = **94.6%** (external: 94.8%) — near-perfect replication
- `iii→n` = **92.9%** (external: 90.9%)
- `i→n` = **67.5%** (external: 56.1%) — our value is higher, likely
  different transcription or corpus coverage
- `ee→y` = **41.1%** (external: 51.8%) — moderate divergence
- `q→o` = **98.3%** (external: 97.1%) — excellent match

Critical finding: run length dramatically changes successor selection.
Single `i` has diverse successors (n=67.5%, r=25.6%), but doubled `ii`
is near-deterministic (`ii→n` = 94.6%). This is a qualitative shift, not
a gradual trend — consistent with `ii` being a distinct symbol.

**Test B: Currier A vs B Transition Divergence**

Mean glyph-level JSD between A and B: **0.041** — very low. Of 21
testable glyphs, **18/21 have the same top successor** in both languages.
The three exceptions are marginal:
- `cph`: o(29%) in A vs e(56%) in B — rare glyph (n=185 total)
- `t`: a(29%) in A vs e(37%) in B — near-tied in both
- `e`: self-repeat dominates both; subtly different #2

Run-conditioned mean JSD: **0.048** — similar to glyph-level.

**Conclusion: Currier A and B share nearly identical transition
rules.** This supports "same language, different scribes/sections"
over "two different languages."

**Test C: Word-Boundary Prediction from Slot Grammar**

Using the I-M-F positional classification from Phase 67, we predicted
word boundaries from transition pairs. The prediction rule: any pair
where the first glyph is classed FINAL predicts a word boundary.

Accuracy: **189/207 = 91.3%** of transition pairs correctly predicted.
Every high-boundary-probability pair (100% break rate) had a FINAL-class
first glyph. Every low-boundary pair (0% break rate) had an
INITIAL or MEDIAL first glyph. The slot grammar captures word structure
with high fidelity.

**Test D: Functional Glyph Taxonomy**

Glyphs cluster into six functional classes by position and transition:
- INITIAL: `ch`, `q`, `sh`, `s`, `cth`, `cph` — start words, feed medials
- MEDIAL→M: `o`, `k`, `t` — chain to other medials (vowel-like?)
- MEDIAL→F: `a`, `d`, `ckh` — feed directly to finals
- MEDIAL: `p`, `f`, `cfh` — mixed transition behavior
- REPEAT: `e`, `i` — unique self-repeating glyphs (26.2% and 40.5%)
- FINAL: `y`, `l`, `r`, `n`, `m`, `g` — terminate words

The REPEAT class (`e`, `i`) is unique. No other glyphs self-repeat at
meaningful rates. These two glyphs form a functional pair: medial-position
elements whose run lengths carry morphemic information.

**Test E: Information Content of Run-Length Choice**

For `i`: H(next|i) = 0.760, H(next|i,runlen) = 0.667. Run length
provides **0.093 bits** additional information about the successor.
For `e`: **0.058 bits**. For all other glyphs: <0.01 bits.

Why so small despite the dramatic probability shifts? Because `ii` is
already the dominant form (62.8% of i-runs), so the run-length signal
is partially absorbed by the marginal glyph frequency. The low ΔH
means the H-ratio anomaly cannot be explained by run-length conditioning
— the entropy reduction from knowing run length is an order of magnitude
smaller than the H-ratio gap (0.093 bits vs the ~0.8 bits gap).

**REVISED CONFIDENCES (Phase 68):**
- Natural language in unknown script: **80% (unchanged)**
- Script has positional slot grammar (I-M-F): **95%** — further
  confirmed by 91.3% boundary prediction accuracy
- Currier A and B share transition structure: **90% NEW** — mean
  JSD = 0.041, 18/21 same top successor
- i-run length is informationally loaded: **75% NEW** — dramatic
  probability shifts, but only 0.093 bits of information gain
- i/e runs are morphemic: **85% (unchanged)** — confirmed by
  near-deterministic ii→n (94.6%)
- H-ratio anomaly NOT caused by run lengths: **95% CONFIRMED** —
  ΔH = 0.093 ≪ the 0.8-bit gap
- Simple substitution cipher: **<5%** (unchanged)
- Hoax/random: **<3%** (unchanged)

**REVISED CONFIDENCES (Phase 72):**
- Natural language in unknown script: **80% (unchanged)**
- Script has positional slot grammar (I-M-F): **95%**
- Naibbe-style verbose cipher as VMS encoding: **15% DOWN from 25%** —
  reproduces h_char anomaly and word length but systematically fails
  Zipf α (33% off), hapax ratio (17% off), word entropy (26% off), TTR
  (29% off), and the word boundary information test (ΔH wrong sign).
  Source language is irrelevant (0.1–3% of variance), so Czech provenance
  provides no statistical traction.
- VMS word boundaries are non-informative: **95% CONFIRMED** — all 2040
  Naibbe experiments produce informative boundaries (ΔH = -0.31 to -0.81),
  opposite to VMS's +0.145. This is a structural property that Naibbe
  cannot reproduce.
- Simple substitution cipher: **<5%** (unchanged)
- Hoax/random: **<3%** (unchanged)

---

### Phase 73 — Medieval Abbreviation/Shorthand Model vs VMS Fingerprint

Phase 73 tests whether medieval abbreviation conventions (Cappelli-style
suffix marks, contractions, nasal bars, etc.) — potentially written in a
constructed alphabet — can reproduce the VMS statistical fingerprint.

**819 experiments** across 3 models:
- Model A: abbreviation with raw Latin characters (30 experiments)
- Model B: abbreviation + random many-to-18 alphabet mapping (600)
- Model C: syllabic encoding (189)

**DECISIVE FAILURE on h_char (the key VMS anomaly):**

Zero out of 819 experiments produce h_char in the VMS range [0.55, 0.75]:
- abbrev_raw: min h_char = 0.843 (VMS: 0.641, gap = 0.202)
- abbrev_mapped: min h_char = 0.872 (WORSE — mapping increases h_char)
- syllabic: min h_char = 0.994 (catastrophic)

Abbreviation moves h_char by only -0.003 across the full density range.
The VMS needs -0.21. Abbreviation delivers 1.6% of what's needed. This
is a fundamental limitation: abbreviation preserves natural language's
character-level bigram structure. h_char ≈ 0.85 is the natural language
floor, and no amount of abbreviation breaks through it.

**The asymmetry puzzle (abbreviation vs Naibbe):**

| Property | Naibbe | Abbreviation | VMS |
|---|---|---|---|
| h_char | 0.619 ✓ | 0.846 ✗ | 0.641 |
| h_word | 0.365 ✗ | 0.445 ✓ | 0.445 |
| heaps | 0.703 ~ | 0.755 ✓ | 0.753 |
| hapax | 0.495 ✗ | 0.726 ~ | 0.656 |
| zipf | 0.672 ✗ | 1.072 ✗ | 0.942 |

Naibbe gets the character-level anomaly right but destroys word-level
statistics. Abbreviation preserves word-level statistics but cannot touch
the character-level anomaly. Neither model produces both simultaneously.

**Methodological note:** L2 distance is MISLEADING for abbreviation.
Best abbreviation L2 (0.262) looks better than Naibbe (0.341), but
abbreviation fails catastrophically on h_char (32% error) — the single
most distinctive VMS metric — while Naibbe nearly nails it (3% error).

**REVISED CONFIDENCES (Phase 73):**
- Natural language in unknown script: **80% (unchanged)**
- Script has positional slot grammar (I-M-F): **95%**
- Medieval abbreviation/shorthand as VMS encoding: **5% DOWN from 20%** —
  cannot produce h_char anywhere near VMS level. The natural language
  h_char floor (~0.85) is preserved by abbreviation. Zero out of 819
  experiments in the VMS h_char range.
- Naibbe-style verbose cipher: **15% (unchanged)**
- Alphabet mapping (many-to-fewer chars) lowers h_char: **REFUTED** —
  it INCREASES h_char (0.84→0.93) by flattening conditional distributions
- Syllabic encoding: **<2% EFFECTIVELY RULED OUT** — catastrophic failure
  on all metrics (h_char≈1.0, wlen≈2.8, L2>2.15)
- **THE ASYMMETRY PUZZLE (NEW):** The VMS simultaneously has low h_char
  (character-level: cipher-like) AND natural word-level statistics
  (hapax, Zipf, h_word: language-like). No tested model achieves both.
  Either a combination mechanism exists, or the VMS represents something
  outside our current model space.
- Simple substitution cipher: **<5%** (unchanged)
- Hoax/random: **<3%** (unchanged)

---

### Phase 105 — Cappelli Abbreviation Re-Test + Paleographic Corroboration

Phase 105 re-tested Cappelli-style abbreviation using Phase 104's ending-
specific metrics (paradigm fill, NMI, H(ending), agreement ratio, bigram MI)
instead of Phase 73's fingerprint-only approach.

**Results — direction analysis (density=1.0, VMS target in parentheses):**

| Metric | Latin | Abbreviated | VMS | Gap Closed |
|---|---|---|---|---|
| Paradigm fill | 7.5% | 19.1% | 22.4% | **78%** |
| NMI(stem↔end) | 0.93 | 0.76 | 0.62 | **45%** |
| H(ending) | 2.84 | 3.93 | 3.05 | **−106%** (wrong way) |
| h_char | 0.87 | 0.87 | 0.64 | **2%** |
| Agreement ratio | 0.23 | 0.14 | 0.27 | **−181%** (wrong way) |
| Bigram MI | 0.051 | 0.029 | 0.044 | **−283%** (wrong way) |

Abbreviation closes **78% of the paradigm fill gap** (the most structurally
distinctive VMS anomaly) and **45% of the NMI gap**. These are genuine structural
predictions of many-to-one suffix collapse. But it **fails** on h_char (2%),
H(ending) (wrong direction), agreement ratio, and bigram MI.

**External corroboration — Voynich Ninja thread 2394 (JKP paleographic analysis):**
JKP's 10+ years of VMS glyph paleography independently confirms the abbreviation
mechanism from the visual/positional side:
- ~80% of VMS glyph shapes derive from Latin scribal abbreviation conventions
- Not just shape similarity — **positional matching**: glyphs appear in the same
  word positions as their Latin manuscript analogues
- Specific identifications: EVA-y = 9-sign (-us/-um); EVA-m = -ris/-tis/-cis
  (3 confirmed variants); EVA-k = Item (I + -is); EVA-s = -er/-eus/-ce
- Gallows are **constructed** from modular scribal building blocks (loops +
  ascenders + -is marks), not single characters
- Best single-source MSS: Cod. Sang. 839 (Swiss, 1459)
- The **composite glyph hypothesis** (some EVA characters = 2-4 scribal
  components) could explain the h_char anomaly: if character boundaries are
  wrong, effective h_char would be lower than EVA-measured h_char

**The convergence:** Phase 105's statistical finding (paradigm fill 78% gap
closed) and JKP's paleographic finding (positional glyph matches) arrive at
the same conclusion from independent directions: VMS endings behave like
abbreviation category marks. This is the strongest evidence to date for an
abbreviation component in the VMS encoding.

**What abbreviation cannot explain (hard constraints that still stand):**
1. h_char ≈ 0.64 (abbreviation floor ≈ 0.85, 0/819 experiments in range)
2. H(ending) goes wrong direction under abbreviation
3. Agreement ratio and bigram MI go wrong direction

**REVISED CONFIDENCES (Phase 105):**
- Medieval abbreviation as VMS encoding (alone): **15% UP from 5%** — paradigm
  fill and NMI compelling, but h_char failure is a hard ceiling
- Abbreviation as ONE component of multi-layer encoding: **30% (new)** —
  abbreviation handles suffix collapse, another mechanism handles h_char
- VMS endings purely mechanical (no abbreviation): **45% DOWN from 60%**
- Abbreviation + composite glyph hypothesis: **~20%** — if EVA miscounts
  character boundaries (as JKP argues), both the h_char and H(ending)
  failures might be measurement artifacts rather than real constraints

---

### Phase 106 — Abbreviation Decode Attempt + Multi-Language Frequency Matching

Phase 106 attempted actual decipherment using abbreviation identifications.

**Phase 106a/b (Latin decode):** Applied JKP mappings directly (EVA-y→-us, etc.)
to f1r. Three decode variants + 25 bench combinations tested. **Complete failure.**
Methodological flaw: treated Latin glyph SHAPES as Latin MEANINGS.

**Phase 106c (positional frequency matching):** Corrected approach — match VMS
glyph positional profiles (initial/final/medial frequencies) against 9 corpora
across 6 languages (Latin, Italian, German, Czech, French, English).

| Language | Word Hits (f1r) | Trigram Hits |
|---|---|---|
| German (Ortolf) | 11 | 96 |
| German (Faust) | 8 | 126 |
| Latin (Galen) | 7 | 146 |
| Czech (Kralice) | 5 | 176 |
| Italian (Cucina) | **0** | 58 |

**No language produced readable text.** All decoded outputs are gibberish.
Italian scored worst (0 word hits). EVA-y at 40% word-final has no single-
character analogue in any tested language.

**Conclusion:** Simple 1-to-1 glyph-to-character substitution is ruled out for
all tested languages. The encoding must be verbose, compressed, multi-layered,
or involve incorrectly parsed EVA digraphs.

**REVISED CONFIDENCES (Phase 106):**
- Simple substitution of ANY tested language: **<1%** — definitively ruled out
- Multi-layer encoding with abbreviation component: **35% UP from 30%** —
  abbreviation properties are real, but an additional cipher/encoding layer exists
- VMS as verbose/compressed encoding: **25% (new)** — consistent with all evidence

---

### Phase 107 — Intra-Chunk Slot Mutual Information Decomposition

Phase 107 localizes the unexplained h_char residual (+0.26, z=25.9 vs NL
from Phase 97) by computing pairwise MI between all LOOP grammar slots.

**Key findings (78,667 chunks from 40,214 words):**

1. ALL 10 slot pairs carry significant excess MI (z-scores 1,290 to 9,190).
   The anomaly is **distributed** across the entire chunk structure.

2. Highest excess: S4↔S5 (back↔coda) = 0.65 bits, S2↔S5 (front↔coda)
   = 0.65 bits. The coda is equally entangled with front and back vowels.

3. **Body-Coda NMI = 0.4273** — bodies predict 42.7% of coda entropy.
   NL onset↔coda NMI ranges 0.10-0.26. VMS is DOUBLE the NL maximum.
   → Inconsistent with pure abbreviation (suffix should be stem-independent)
   → Consistent with cipher/constructed system (body+coda jointly encode info)

4. Body isolation does NOT restore NL entropy: h_ratio rises only from
   0.539 to 0.600 (NL range: 0.82-0.88). Two-layer model is INSUFFICIENT.

5. Cross-chunk MI (0.11) << within-chunk MI (0.65): chunks are relatively
   independent encoding units, confirming Phase 85's chunk-as-basic-unit.

**REVISED CONFIDENCES (Phase 107):**
- Pure abbreviation system: **10% DOWN from 15%** — body-coda coupling too high
- Abbreviation shapes repurposed as cipher framework: **40% UP from 35%**
- Constructed/artificial language: **30% UP from 25%** — distributed entanglement
  across all slots matches constructed system better than cipher of NL

---

### Phase 74 — Paragraph Framing Analysis: Do Start/End Markers Define "Code Blocks"?

Phase 74 tests whether paragraphs are "code blocks" framed by specific
start AND end markers that define different reading modes.

**784 paragraphs** across the entire manuscript analyzed for initial glyph,
final glyph, internal statistics, and cross-tabulation.

**THE "CODE BLOCK" HYPOTHESIS IS REFUTED:**

| Prediction | Result |
|---|---|
| Initial concentrated | ✓ 83% gallows (confirmed Phase 71) |
| Final also concentrated | ✗ Matches word-final baseline (85% vs 83%) |
| Init-final correlated | ✗ **Completely independent** (χ²=41.7, p=0.95) |
| Different internal stats per frame | ✗ Δh_char < 0.02, uniform |
| Cross-section consistency | ~ Partial |

The initial glyph tells you NOTHING about the final glyph (p=0.95).
Paragraph interiors are statistically identical regardless of which
gallows starts the paragraph. Different "frames" don't create different
"code blocks."

**What the paragraph-initial gallows signal DOES mean:**

The gallows enrichment at paragraph starts is massive (83%, 23x enrichment
vs word-initial baseline). But rather than a cipher mechanism, this is
most likely:
- **Structural markers / heading words** — 451 words appear only paragraph-
  initially (Phase 71). These are probably labels, headings, or topic
  indicators from a restricted vocabulary.
- **Scribal convention** — gallows are visually large and complex, consistent
  with a "capital letter" function marking paragraph starts. This aligns
  with I-M-F slot grammar: gallows are INITIAL-class glyphs.

**Minor signal: `m` enrichment at paragraph endings** (3.6x vs word-final
baseline), but this is actually weaker than the line-ending `m` rate
(14.3%), suggesting it's a line-ending property, not paragraph-specific.

**REVISED CONFIDENCES (Phase 74):**
- Natural language in unknown script: **80% (unchanged)**
- Script has positional slot grammar (I-M-F): **95%**
- Paragraph-initial gallows function as structural markers: **85% NEW** —
  massive enrichment (83%), but paragraph-final shows no matching pattern,
  internal stats are uniform across frame types, and init-final are fully
  independent
- Paragraphs as "code blocks" with different reading rules: **<5% REFUTED**
  — fails 3 of 5 predictions. No evidence for start/end framing or
  different internal statistics per frame type
- Gallows as "capital letters" / decorative convention: **70% NEW** —
  consistent with I-M-F slot grammar (INITIAL class), visual prominence,
  and absence of final-marker pairing
- Simple substitution cipher: **<5%** (unchanged)
- Hoax/random: **<3%** (unchanged)

---

### Phase 75 Update: Latin Paragraph-Initial Mapping — REFUTED

**What was tested:** All C(26,4)×4! ≈ 358,800 possible mappings of VMS
gallows to Latin letters, evaluated against 6 actual Latin texts (Apicius,
Galen, Erasmus, Caesar, Vulgate, Pliny) and 4 medieval vocabulary models
(herbal, recipe, medical, mixed). ~1.2M total comparisons.

**Fatal finding — THE COVERAGE GAP:** VMS gallows account for 81.4% of
paragraph-initial positions. No Latin text concentrates more than 64% of
paragraph starts in any 4 letters. Average across 10 sources: 52%. This
29-percentage-point gap is robust across all genres tested.

**No consensus mapping exists.** Each text produces a different optimal
4-letter set. Cross-text voting shows no letter combination favored by
even 2 independent sources. The proportional fit within the chosen 4
letters can be excellent (Δ < 1% for individual letters), but this is
misleading overfitting when the absolute coverage is 30+ points off.

**Section-specific distributions compound the problem.** VMS herbal
(p:t:k:f ≈ 7:5:3:1) is somewhat balanced, while recipe is p-dominated
(54%), and astro uses essentially only t (31%). The same 4 Latin letters
cannot explain such varied distributions across sections.

**Information content:** Gallows carry 1.575 bits (78.7% of 2.0 max),
equivalent to ~3 equiprobable options — one dominant marker + secondary
types, not 4 equally-used letter substitutions.

**What this eliminates:** Gallows as monoalphabetic letter-for-letter
cipher substitutions representing 4 Latin letters. This is robust because
the gap exists regardless of text genre, time period, or vocabulary domain.

**What remains viable for gallows:**
- Structural/functional paragraph markers (paragraph type labels)
- Abbreviated words (not single letters)
- Polyalphabetic or more complex cipher elements
- Decorative variants with structural meaning beyond phonetics
- Scribal "capital letter" convention (I-M-F INITIAL class, Phase 74)

**REVISED CONFIDENCES (Phase 75):**
- Natural language in unknown script: **80% (unchanged)**
- Script has positional slot grammar (I-M-F): **95% (unchanged)**
- Paragraph-initial gallows as structural markers: **90% (↑ from 85%)** —
  the impossibility of simple letter mapping strengthens the structural
  marker hypothesis
- Gallows as monoalphabetic letter substitutions: **<2% REFUTED** —
  fatal coverage gap across all Latin sources tested
- Gallows as "capital letters" / decorative convention: **75% (↑ from 70%)** —
  the functional non-letter nature of gallows is reinforced
- Simple substitution cipher: **<3%** (unchanged, further weakened)
- Hoax/random: **<3%** (unchanged)

---

### Phase 76 Update: Vernacular Paragraph-Initial Mapping — PARTIAL MATCH

**What was tested:** Three medieval vernacular recipe collections from the
VMS era (Italian 14th c., French c. 1380–1420, Middle English c. 1390) —
testing whether imperative-verb-dominated recipe texts can reproduce VMS
gallows concentration (81–87%) at paragraph starts.

**Coverage results — dramatically closer than Latin:**
- Italian: 86.1% top-4 coverage (D, T, A, P) — exceeds VMS 81.4%
- French: 78.7% (P, C, B, S) — 2.7% below VMS
- English: 74.2% (T, F, C, N) — 7.2% below VMS
- Compare: Latin average was ~52%, max ~64% (Phase 75)

Vernacular recipe texts reach 74–86% vs Latin's 52–64%. The recipe genre
IS sufficiently formulaic to approach VMS gallows levels.

**The English proportional match is extraordinary:** The Forme of Cury
(c. 1390) achieves L2=0.004 to VMS gallows ratios (the lowest of ANY
text in Phases 75–76). Within the top-4 letters, English T:F:C:N maps
to VMS p:t:k:f with deltas of just 0.007, 0.023, 0.024, and 0.041.
The hierarchy p>t>k>f mirrors Take>For>C-words>Nym precisely.

**But no language matches both dimensions simultaneously:**
Italian matches coverage (86%) but not proportions (L2=0.036).
English matches proportions (L2=0.004) but not coverage (74%).
French is intermediate on both axes.

**Italian body-only analysis:** When section headers (=Dei=/\_Sub-recipe\_)
are stripped, recipe-body paragraphs show T=62%, with top-4 coverage of
82.1% — matching VMS. But T alone dominates too much (VMS p=44.9%).

**What this changes:**
- Gallows concentration is NOT anomalous in the recipe genre — vernacular
  recipe texts from the same era produce comparable concentration
- The COVERAGE dimension is now explained by genre conventions
- But the PROPORTIONAL structure of p:t:k:f still resists easy mapping —
  it simultaneously requires moderate concentration (no letter above 45%)
  and high total coverage (81%+), a combination no single language achieves
- The English proportional match hints at an English-like distribution of
  recipe conventions, but the coverage shortfall means the VMS has additional
  structural regularity beyond what natural recipe text produces

**REVISED CONFIDENCES (Phase 76):**
- Natural language in unknown script: **80% (unchanged)**
- Script has positional slot grammar (I-M-F): **95% (unchanged)**
- Paragraph-initial gallows as structural markers: **85% (↓ from 90%)** —
  vernacular recipe conventions can reproduce similar concentration, so
  gallows COULD be first-letter substitutions in a recipe context (but
  proportional mismatch keeps this from being certain)
- Gallows as monoalphabetic letter substitutions: **<5% (↑ from <2%)** —
  no longer categorically refuted; vernacular recipe texts CAN reach
  VMS coverage levels, but the simultaneous coverage+proportion match
  remains elusive
- Gallows as "capital letters" / decorative convention: **75% (unchanged)**
- Gallows correlation with recipe-style imperative verbs: **65% NEW** —
  the Italian and English data strongly suggest gallows correlate with
  formulaic recipe openings (Take/Togli/Pour), consistent with a recipe
  herbal in an unknown script
- Simple substitution cipher: **<5%** (slightly weakened — vernacular
  recipe text could produce the observed gallows patterns without needing
  a cipher mechanism)
- Hoax/random: **<3%** (unchanged)

---

### Phase 77 Update: Gallows Positional Ecology — FUNCTIONALLY DISTINCT ★★★

**What was tested:** Six converging tests comparing gallows behavior at
paragraph starts vs in body text — successor distributions, word-form
overlap, character-position profiles, compound vs plain gallows, ratio
comparison, and word diversity.

**DECISIVE FINDING 1 — Compound gallows exclusion (15σ):**
Compound/bench gallows (cph, cfh, ckh, cth) are 25.6% of all gallows at
word-initial positions in body text, predicting ~167 at paragraph starts.
OBSERVED: 4. This is a 15-sigma deviation. The paragraph-initial role is
specific to PLAIN gallows visual forms only.

**DECISIVE FINDING 2 — Ratio inversion (χ²=683):**
The p:t:k:f proportions are INVERTED between paragraph starts and body:
- Para-initial: p=54.5%, t=28.2%, k=12.5%, f=4.9%
- Body word-initial: p=9.1%, t=36.6%, k=50.7%, f=3.6%
'p' dominates paragraph starts but is rare in body; 'k' dominates body
but is minor at paragraph starts. This inversion is universal across ALL
five manuscript sections. If gallows were simple letter substitutions,
their proportions would be constant — they aren't.

**DECISIVE FINDING 3 — Word diversity (TTR 3× recipe texts):**
VMS paragraph-initial TTR = 0.737 (578 unique forms for 784 tokens).
Medieval recipe texts: TTR ~0.26 with dominant verb at 29-45%.
VMS most common paragraph word "tchedy" = 1.4%. This definitively rules
out "gallows = first letter of imperative verb."

**Additional findings:**
- Word-form overlap: only 33.6% of para-initial words appear in body text
- Positional duality: gallows are 75-87% word-MEDIAL in body text but
  always word-initial at paragraph starts
- Gallows-as-prefix evidence: stripping initial gallows from para-initial
  words yields 71.1% match to body vocabulary (vs 38.6% with gallows,
  50.3% null baseline). Same underlying words get different gallows
  prefixes: "ol" → p+ol=10, t+ol=7, k+ol=2

**What this changes:**
Phase 77 resolves the ambiguity from Phase 76. Vernacular recipe texts CAN
match VMS gallows coverage, but the internal ecology proves gallows are NOT
behaving as simple letters:
1. Different gallows get prefixed to the SAME base words
2. Compound forms are excluded despite being common in body text
3. The p:k ratio inverts between paragraph-initial and body positions
4. Word diversity is 3× too high for first-letter-of-verb model

The most parsimonious model: **gallows at paragraph starts are structural
markers prefixed to ordinary VMS vocabulary, encoding paragraph type or
section category.** Within body text, gallows serve a different linguistic
function as regular characters.

**REVISED CONFIDENCES (Phase 77):**
- Natural language in unknown script: **82% (↑ from 80%)** — the prefix
  stripping revealing ordinary vocabulary is strong NL evidence
- Script has positional slot grammar (I-M-F): **95% (unchanged)**
- Paragraph-initial gallows as structural markers: **95% (↑ from 85%)** —
  compound exclusion (15σ), ratio inversion (χ²=683), and prefix behavior
  all converge on structural markers, not letter substitution
- Gallows as monoalphabetic letter substitutions: **<1% REFUTED** — ratio
  inversion alone rules this out; confirmed by compound exclusion and
  word diversity
- Gallows as "capital letters" / decorative convention: **85% (↑ from 75%)**
  — compound exclusion specifically supports the visual-form hypothesis
- Gallows as paragraph-type markers (NEW): **90%** — the section-specific
  p:t:k:f hierarchy and prefix behavior strongly support this
- Gallows-as-prefix model (NEW): **75%** — stripping gallows reveals body
  vocabulary, different gallows attach to same base words, but high VMS
  morphological overlap (50.3% null baseline) prevents certainty
- Simple substitution cipher: **<3% (↓ from <5%)**
- Hoax/random: **<3%** (unchanged)

---

### Phase 77b Update: Line-Position Gallows — The {p,f} vs {t,k} Split ★★★

**Origin:** User observation that 'p' appears almost exclusively on the
first line of paragraphs.

**THE DISCOVERY:** The four gallows characters split into two functional
classes based on their line-position within paragraphs:

- **CLASS 1 — FIRST-LINE: {p, f}** — concentrated 12-15× on paragraph
  line 1 vs line 2+ (z=34.0 and z=22.7; p ⋘ 0.001). Drop from L1 to L2
  is cliff-like (p: 3.1% → 0.2%; f: 1.3% → 0.1%).
- **CLASS 2 — BODY-TEXT: {t, k}** — distributed uniformly (t: 0.9× ratio,
  k: 0.5× — k actually INCREASES on later lines).

**Critical proof of independence:** The p/f first-line concentration holds
REGARDLESS of which gallows starts the paragraph. Even in t-initial or
k-initial paragraphs, p shows 17-34× concentration on line 1. This is a
LINE-LEVEL property, not an artifact of paragraph-initial words.

**Compound gallows mirror the split perfectly:** cph/cfh are first-line
(8-10×), cth/ckh are body-text (0.4-0.5×). This proves the split is
about the UNDERLYING CHARACTER VALUE, not the plain/compound visual
distinction. NOTE: this REVISES the Phase 77 finding that compound
gallows are functionally different from plain gallows at paragraph starts.
The distinction is actually {p,f,cph,cfh} vs {t,k,cth,ckh} — a character-
family split that crosses the plain/compound boundary.

**The first-line vocabulary is nearly unique:** 87% of p-words and 93% of
f-words appearing on line 1 never appear on any other line. First lines
have not just different character frequencies but entirely different word
forms (opchedy, qopchedy, qopy, etc.).

**Universal across sections:** Holds in herbal (18×), recipe (8×), balneo
(38×), cosmo (4-11×), and weakly in astro (4×, small sample).

**What this changes:**
Phase 77b fundamentally restructures our understanding of the gallows.
The traditional grouping {p,t,k,f} as a single class of "tall characters"
is misleading. The actual functional structure is:

  **FIRST-LINE FAMILY: {p, f, cph, cfh}** — marks/decorates the opening
  line of paragraphs. These are structural/visual elements, not regular text.

  **BODY-TEXT FAMILY: {t, k, cth, ckh}** — regular linguistic characters
  appearing uniformly throughout text.

This split aligns with Phase 67's functional taxonomy (p,f → MEDIAL class;
t,k → MEDIAL→M class) and explains why p dominates paragraph-initial
positions: p is a first-line marker, not merely the most common word-
initial letter.

The ~20% of characters on first lines being p/f means that any plaintext
decipherment must account for ~20% structural overhead on first lines.
This could explain part of the h_char anomaly (Phase 67): structural
markers on first lines lower the character entropy.

**REVISED CONFIDENCES (Phase 77b):**
- Natural language in unknown script: **83% (↑ from 82%)**
- Script has positional slot grammar (I-M-F): **95% (unchanged)**
- Gallows as line-position structural markers: **97% (↑ from 95%)** —
  the independence proof, compound confirmation, and vocabulary separation
  make this near-definitive
- **{p,f} vs {t,k} functional split: 98% NEW** — the statistical evidence
  is overwhelming (z=34, z=23) and confirmed by every control test
- **First lines contain structural/decorative encoding: 95% NEW**
- Gallows as monoalphabetic letter substitutions: **<1% REFUTED**
- **p/f as first-line variants of t/k: 40% NEW** — speculative but
  consistent with visual similarity (descenders vs ascenders) and the
  functional split; would mean only 2 underlying gallows characters exist
- Simple substitution cipher: **<3%**
- Hoax/random: **<2% (↓ from <3%)** — the {p,f}/{t,k} split is too
  complex and consistent for a random or meaningless text

---

### Phase 77c — Critical Revalidation (Post-Skeptical Audit)

The Phase 77b findings were subjected to a rigorous 6-test revalidation.
ALL findings survived. Key results:

**Glyph-level analysis** (proper EVA segmentation, not raw characters):
p=14.0×, f=17.4×, cph=8.3×, cfh=10.3× enrichment on L1. No other glyph
exceeds 1.54× (sh). Effect is SPECIFIC to {p,f,cph,cfh}.

**Per-word normalization** (fraction of words containing each glyph —
most conservative metric): p=4.54×, f=7.96×, cph=6.99×, cfh=8.19×.
Line-structural differences (L1 words ~6% longer, ~7% fewer per line)
cannot explain 5–17× enrichment.

**Permutation null model** (10,000 shuffles of line assignments):
Real p-ratio 4.54× vs permuted max 1.51×. z-scores ≈ 24.5. p < 0.0001.

**Multi-parsing robustness**: Holds at 300 paras (strict) and 789 paras
(inclusive), and in herbal-only subset (p=15.7×).

**Compound gallows reconciled**: cph/cfh excluded from W1 (paragraph-
initial word) but enriched on L1 at word positions 2+. Two compatible
phenomena, not a contradiction.

**REVISED CONFIDENCES (Phase 77c post-revalidation):**
- Natural language in unknown script: **83% (unchanged)**
- Script has positional slot grammar (I-M-F): **95% (unchanged)**
- Gallows as line-position structural markers: **98% (↑ from 97%)** —
  survived all skeptical tests including permutation null model
- {p,f} vs {t,k} functional split: **99% (↑ from 98%)** — glyph-level
  analysis, per-word normalization, and permutation test all confirm
- First lines contain structural/decorative encoding: **96% (↑ from 95%)**
- Gallows as monoalphabetic letter substitutions: **<1% REFUTED**
- p/f as first-line variants of t/k: **40% (unchanged)** — still
  speculative; revalidation confirmed the SPLIT but cannot determine
  whether p/f are variants of t/k or entirely independent symbols
- Simple substitution cipher: **<3%**
- Hoax/random: **<2% (unchanged)**

---

### Phase 78 — The Allograph Hypothesis: Refuted

Phase 78 tested whether p≡t and f≡k (allographs — same letter, different
line-position form). Six tests give a decisive NO.

**Key evidence against allography:**
- p→k substitution matches at 63.0% vs p→t at 61.6% — no specific p↔t
  pairing; any body-text gallows works equally well
- p's successor distribution (ch=54%, a=15%) is fundamentally different
  from t's (a=28%, e=31%, ch=17%) — this is intrinsic, not positional
  (p→ch is 56% on L2+ too)
- 52.6% of L1 p-words also exist in L2+ vocabulary — they're not
  transformed versions of t-words
- Nearest-neighbor matching: 0/30 closest L2+ words are p→t substitutions

**Key evidence against prefix/marker model:**
- p appears at word-MIDDLE 85% of the time, not as a prefix
- Stripping p gives ~50% L2+ match (similar to stripping t/k: ~69%)

**MAJOR NEW FINDING: Parametric Slot-Fillers**

All four gallows are the SAME structural class:
- Predecessor JSD ≈ 0.033 (near same-glyph baseline of ~0.02)
- 78 word templates accept ALL 4 gallows (e.g., o[G]aiin: k=221, t=165,
  p=18, f=5)
- Any gallows→gallows substitution yields valid words ~62% of the time

But the CHOICE encodes information along two correlated axes:

| | ch-successor (50%) | a/e-successor (60%) |
|---|---|---|
| **L1-enriched** | **p, f** | (rare) |
| **Body-text** | (rare) | **t, k** |

The successor preference and line preference correlate perfectly:
- CLASS A {p, f, cph, cfh}: ch-following, L1-enriched
- CLASS B {t, k, cth, ckh}: a/e-following, body-text

This resolves Phase 13's semantic domains: on L2+ alone (removing
positional confound), p shows recipe/cosmo enrichment (0.50 herbal,
1.61 recipe, 1.70 cosmo) while t is relatively flat. The semantic
signal partially survives but differs from the original L1-contaminated
assignments.

**REVISED CONFIDENCES (Phase 78):**
- Natural language in unknown script: **83% (unchanged)**
- Script has positional slot grammar (I-M-F): **95% (unchanged)**
- Gallows as line-position structural markers: **95% (↓ from 98%)** —
  p/f are not purely structural markers; they carry distributional
  information (ch-following) and 53% of p-words exist on L2+ too
- {p,f} vs {t,k} functional split: **99% (unchanged)** — confirmed by
  successor distributions, shared templates, line-position data
- **Gallows as parametric slot-fillers: 97% NEW** — 78 shared templates,
  predecessor convergence, and interchangeability all confirm same slot
- **Successor-class encoding (ch vs a/e): 98% NEW** — fundamental
  distributional property, independent of line position
- p/f as first-line allographs of t/k: **<5% REFUTED (↓ from 40%)**
- Gallows as monoalphabetic letter substitutions: **<1% REFUTED**
- Simple substitution cipher: **<3%**
- Hoax/random: **<2% (unchanged)**

---

### Phase 79 — Gallows Collapse: Information Theory Reveals Two-Layer Encoding

Phase 79 applied mutual information analysis and vocabulary collapse to
determine whether gallows are informationally redundant with their context.

**THE HEADLINE: Gallows retain 79.8% independent entropy.**

H(gallows) = 1.4192 bits. After conditioning on predecessor, successor,
line position, and section: H(gallows|all context) = 1.1328 bits. Only
20.2% of gallows information is explained by measurable context.

**But the system has two layers:**

- **Layer 1 (CLASS: {p,f} vs {t,k}):** H=0.48 bits, 78% predictable
  from successor glyph, 89.6% classification accuracy. The ch/a/e
  successor split largely determines the class.

- **Layer 2 (MEMBER within class: p vs f, t vs k):** H≈0.94 bits,
  nearly UNPREDICTABLE from any context. This is where 79.8% of the
  residual lives.

**Vocabulary collapse:**
- Two-class collapse: 8,212→7,378 types (−10.2%) — JUSTIFIED by 78%
  class predictability from successor
- Full collapse: 8,212→6,939 types (−15.5%) — NOT JUSTIFIED; destroys
  genuine within-class information

**The bigram entropy paradox:** Word bigram entropy INCREASES from
4.327→4.692 after full collapse. Gallows carry word-to-word transition
information — they help predict what word comes next. This is
incompatible with "decorative variation" and argues for genuine
linguistic content in the gallows choice.

**Best estimate of true vocabulary: ~7,400 types** (two-class collapse).
The original 8,212 overcounts by ~834 due to the redundant A/B class
distinction; full collapse undercounts by ~440 by merging genuinely
distinct forms.

**REVISED CONFIDENCES (Phase 79):**
- Natural language in unknown script: **83% (unchanged)**
- Script has positional slot grammar (I-M-F): **95% (unchanged)**
- Gallows as line-position structural markers: **95% (unchanged)**
- {p,f} vs {t,k} functional split: **99% (unchanged)**
- Gallows as parametric slot-fillers: **97% (unchanged)**
- Successor-class encoding (ch vs a/e): **98% (unchanged)**
- **Gallows carry independent information: 90% NEW** — 1.13 bits
  (79.8%) unexplained by all measured context; bigram entropy increase
  confirms this is genuine word-transition information
- **Two-class collapse justified: 85% NEW** — class distinction is
  78% predictable from successor; true vocabulary ≈ 7,400 types
- **Full collapse justified: <30% NEW** — destroys bigram predictability
  and merges genuinely distinct word forms
- **Gallows as pure decorative variation: <10% NEW** — refuted by
  residual entropy and bigram entropy increase
- p/f as first-line allographs of t/k: **<5% REFUTED**
- Gallows as monoalphabetic letter substitutions: **<1% REFUTED**
- Simple substitution cipher: **<3%**
- Hoax/random: **<2% (unchanged)**

---

## Phase 80 — Abjad Hypothesis Refuted + External Research Integration

### The Abjad Test

Three independent analyses converge on 13 functional VMS letters:
Hebrew consonant reduction, Voynich Talk positional variant collapse,
and Phase 59 verbose cipher. The abjad hypothesis proposes this
matches consonant-only writing systems.

**Test:** Strip vowels from 6 reference texts, compare fingerprints
to VMS.

**Result: UNANIMOUS REFUTATION.** Every language moved FARTHER from
VMS after stripping. Not a single metric improved consistently:
- h_char: 0/6 toward VMS (stripping pushes from ~0.85 to ~0.92,
  VMS is 0.641 — WRONG direction)
- Word length: 0/6 (words collapse from ~4.5 to ~2.8; VMS is 4.94)
- Heaps β: 0/6
- Hapax ratio: 0/6
- Overall distance roughly doubled for every language

**Why it fails:** Vowels create predictable VC alternation. Remove
them and you get consonant clusters with LESS sequential structure,
pushing h_char UP (less predictable) when VMS needs it DOWN. Word
lengths collapse catastrophically. Alphabet shrinks to 21-24, not 13.

**The 13-convergence remains intriguing but unexplained by simple
abjad writing.** If 13 base units exist, they expand to ~30 surface
glyphs through a MORE complex mechanism (Phase 59 positional verbose).

### External Research: Four Video/Lecture Analyses

**1. Lisa Fagin Davis — Materiality of the VMS:**
- Five scribes identified; singlion structure (unbound bifolia stack)
- LSA confirms misbinding; conjoint scores > facing scores
- No punctuation, no majuscule/minuscule
- Bowern & Lindemann: "extremely low word-level entropy" (= our h_word)
- Possibly pedagogical (communal use, like West African Quran bifolia)
- Material testing: authentic early 15th century, no forgery signatures

**2. Voynich Talk — Alphabet smaller than you think:**
- Positional variant collapse → ~13 functional letters
- Concludes simple substitution impossible
- Never considers abjad (where 13 IS adequate) — this was our test

**3. Voynich Talk — The part we CAN read (f116v):**
- f116v has TWO linguistic registers on one page:
  - German recipe language: "boxleber" (buck's liver), "so nim gasmich"
    (then take goat's milk)
  - Latin-like charm: "ankhiton...cere portas N...maria"
- Two Voynichese words integrated in text — writer could produce VMS
- German dialect with Latin influence; recipe/medical instruction genre
- Confirms genre: instructional/recipe text

**4. Voynich Talk — Where and when (handwriting analysis):**
- 382 samples scored on 33 paleographic properties
- **Best matches: Fulda/Mainz in central Germany** (7/10 top hits)
- One excellent match from Zurich area
- Script definitively early 15th century; contemporaneous with manuscript
- Romance-language areas, Italy, England all score poorly
- Writer trained in West Central German dialect territory

### Synthesis: What This Changes

The external research converges powerfully with our statistical work:

1. **German, not Latin or Italian, should be our primary reference.**
   Phase 64 found VMS best matches Italian/Dutch. The paleographic
   evidence puts the scribe in central Germany. Medieval German
   (particularly West Central dialects) must be tested as a reference
   corpus in future phases.

2. **Recipe/medical instruction genre confirmed.** f116v contains
   cooking instructions. Davis sees the herbal section as plant
   identification + harvesting + preparation instructions. This is
   a domain-specific corpus, not general prose.

3. **Singlion structure explains some statistical anomalies.** If
   each bifolium is independent, cross-bifolium word-level statistics
   may be artificially noisy. The low h_word and unusual Heaps
   exponent could partly reflect genre fragmentation.

4. **The abjad path is closed.** Simple consonantal writing does NOT
   reproduce VMS fingerprints. Whatever produces the h_char anomaly,
   it is NOT vowel removal. The Phase 59 positional verbose model
   remains the only candidate.

5. **Bilingual context opens a new angle.** German + Latin on f116v.
   Could VMS encode a bilingual or code-switching text? This could
   explain the Language A/B distinction (not different dialects but
   different languages switching between sections).

**REVISED CONFIDENCES (Phase 81 — CORRECTED after revalidation):**
- Natural language in unknown script: **85% (unchanged)**
- Script has positional slot grammar (I-M-F): **95% (unchanged)**
- Gallows as line-position structural markers: **95% (unchanged)**
- {p,f} vs {t,k} functional split: **99% (unchanged)**
- Gallows carry independent information: **90% (unchanged)**
- Two-class collapse justified (true vocab ~7,400): **85% (unchanged)**
- German-language origin of scribe: **70% (unchanged)** — only Faust
  (#1 at 0.310) supports German; BvgS ranks #7 (0.452) after
  correcting foreword contamination. A single verse text is weak
  evidence. Original claim of "both German texts in top 2" was
  an artifact of ~10% modern German contamination in BvgS.
- Recipe/instructional genre: **40% (↓ from 75%)** — the genre
  hypothesis is substantially weakened. Recipe texts rank WORSE than
  non-recipe texts on average (0.459 vs 0.369). BvgS TTR=0.241 is
  far too low — recipe text is too formulaic for VMS (needs 0.342).
- **Consonantal/abjad system: <5% REFUTED** — vowel stripping makes
  ALL metrics worse; h_char moves wrong direction
- Positional verbose cipher with ~13 base chars: **25% (unchanged)**
- Simple substitution cipher: **<3%**
- Hoax/random: **<2% (unchanged)**

**Phase 81 Key Insight (CORRECTED):** The initial run produced a
false signal — BvgS appeared at #2 (0.346), suggesting "both German
texts in top 2." Revalidation revealed this was an artifact of ~10%
modern German foreword contamination. After cleaning, BvgS dropped to
#7 (0.452) — near the bottom. Only Faust (#1, 0.310) supports a
German signal, and it is a verse text with inflated vocabulary
richness. The genre hypothesis failed completely: recipe texts are
among the worst matches. All 4 predictions refuted (0/4). The h_char
anomaly (0.641 vs universal ~0.83-0.87) remains unexplained by any
natural language — VMS is not raw plaintext in any language.

**Methodological lesson:** The contamination episode demonstrates
that fingerprint distances are fragile. A 10% admixture of wrong-era
text shifted a corpus from #7 to #2 — enough to produce a false
positive for an entire hypothesis. Corpus curation is essential.

**REVISED CONFIDENCES (Phase 82 — Line-1 / Body Separation):**
- Natural language in unknown script: **85% (unchanged)**
- Script has positional slot grammar (I-M-F): **97% (↑ from 95%)** —
  Phase 82 confirms the slot grammar persists in body text (L2+) after
  removing L1. It is intrinsic to the encoding, not an artifact.
- {p,f} vs {t,k} functional split: **99% (unchanged)** — further
  confirmed: p is 5.4× enriched and f is 7.6× enriched on L1.
- h_char anomaly is intrinsic to encoding: **99% (NEW)** — body-only
  h_char (0.6393) is actually LOWER than full VMS (0.6442). Removing
  L1 closes no gap toward natural language (~0.83). The anomaly is
  a fundamental property of whatever encoding system was used.
- Two encoding subsystems (L1 vs body): **60% (NEW)** — L1 and body
  are statistically different (h_char z=8.21, JSD z=131.7, vocab
  z=−17.7), but they share the same positional grammar. This looks
  more like "same system + L1 prefix glyphs" than truly separate
  encodings. The difference could reflect topic (labels/headers)
  rather than encoding.
- Functional alphabet ~13-18 letters: **70% (↑ from 25% for verbose
  cipher)** — body text uses 18 functional glyphs but strong positional
  restriction reduces per-position repertoire to ~8-14. Consistent with
  Phase 59's ~13-base-character verbose cipher model and Koen's ~13
  functional letters argument.
- All other confidences unchanged from Phase 81.

**Phase 82 Key Insight:** The h_char anomaly (0.641) is NOT caused
by mixing two subsystems. L1 and body are measurably different (L1
h_char=0.6834, body=0.6393, z=8.21), but body alone is actually
FURTHER from natural language than the mixture. The anomaly is
intrinsic. Whatever encoding produced VMS, it operates on body text
just as strongly as on L1. The positional slot grammar (I-M-F)
persists fully in body text — it is a fundamental structural property,
not driven by L1's {p,f,cph} enrichment.

**Parser bug lesson:** The initial run captured only 42% of words
due to orphan continuation lines after `<$>` markers in star/label
sections. Quantitative values shifted after fix (vocab overlap 38.9%
→ 51.3%, h_char 0.6591 → 0.6442), though qualitative conclusions
held. Always validate corpus word counts against known totals.

---

**REVISED CONFIDENCES (Phase 83 — Sub-word Branching Entropy / Depth-2 Bump):**
- Natural language in unknown script: **85% (unchanged)**
- Script has positional slot grammar (I-M-F): **97% (unchanged)**
- {p,f} vs {t,k} functional split: **99% (unchanged)**
- h_char anomaly is intrinsic to encoding: **99% (unchanged)**
- Two encoding subsystems (L1 vs body): **60% (unchanged)**
- Functional alphabet ~13-18 letters: **70% (unchanged)**
- Positional verbose cipher with ~13 base chars: **35% (↑ from 25%)** —
  The Phase 60 verbose cipher is the ONLY tested system that reproduces
  the VMS depth-2 branching entropy bump (d2/d1 = 1.171 vs VMS 1.100).
  Zero of 8 natural languages show d2/d1 > 1 (mean 0.780, std 0.077).
  Simple substitution (0.958), random text (0.954), and isolated
  positional variation (0.831) all fail to produce the bump. VMS
  z-score = 4.2 vs NL. Bootstrap CI entirely above 1.0 (500/500).
  However, the bump is consistent with multiple non-NL mechanisms
  (constructed writing, syllabary, verbose cipher), so it supports
  the verbose cipher as one of several candidate explanations rather
  than uniquely identifying it.
- VMS is NOT plain natural language: **99% (↑ from 98%)** — the d2/d1
  bump adds a new structural dimension in which VMS differs from all
  tested natural languages. Combined with h_char anomaly, Zipf
  exponent, and now branching entropy profile, VMS fails to match
  natural language on multiple independent statistical axes.
- Simple substitution cipher: **<2% (↓ from <3%)** — simple
  substitution preserves NL branching structure (d2/d1 = 0.958).
  VMS's d2/d1 = 1.100 rules this out more firmly.
- Hoax/random: **<2% (unchanged)**
- All other confidences unchanged from Phase 82.

**Phase 83 Key Insight:** VMS words have a unique within-word
branching entropy profile: the depth-2 entropy EXCEEDS depth-1
(d2/d1 = 1.100), creating a "bump" that appears in ZERO of 8
natural languages but DOES appear in the verbose cipher model
(d2/d1 = 1.171). The mechanism is "bench bigrams" — extremely
tight initial glyph pairs (q→o 97.7%, d→a 81.1%, ch→e 53.3%)
followed by variable continuations. This is the first entropy-space
feature that structurally separates VMS from natural language at
the within-word level. Group segmentation via boundary detection
FAILED completely (cannot extract cipher alphabets), but the
branching PROFILE is a powerful discriminator.

**Methodological lesson:** The original Phase 83 synthesis concluded
"NOT SUPPORTED" based solely on group segmentation results (4,183
group types, poor cipher validation). Revalidation with NL baseline
comparison revealed the d2/d1 bump — a signal INVISIBLE to the
original analysis framework. The lesson: always test your metrics
against a null model (natural language baseline). Without the NL
comparison, the most important finding would have been missed.

---

### Phase 84 Update — MI(d) Text-Meaning-Area Analysis

**New metric: Text-Meaning-Area (TMA)** = integral of (raw MI(d) −
word-shuffled MI(d)) for d ∈ [20, 80]. Measures whether word ORDER
carries information beyond what character frequencies alone provide.

**Key results (TMA[20-80]):**
- VMS Full: **0.123** (1.9× NL average)
- VMS Currier A: 0.135, Currier B: 0.128 (both high, A ≈ B)
- NL average: 0.065 (range: 0.003 Latin-Caesar to 0.144 French-Viandier)
- Verbose cipher average: 0.029 (42-97% preservation of source TMA)
- Char-shuffled control: ≈ 0 (validates computation)

**Impact on confidence levels:**
- Verbose cipher as encoding mechanism: **35% → 30% (↓)** — the cipher
  partially preserves word-order structure (positive), but VMS TMA is
  4× higher than cipher TMA. The model underpredicts VMS word-order MI,
  suggesting VMS has richer word-order structure than the cipher produces.
  An enhanced cipher model (with contextual or syntactic dependencies)
  might close this gap.
- VMS is NOT plain natural language: **99% (unchanged)** — VMS TMA is
  in the NL range (actually ABOVE average), confirming word-order
  structure. But h_char, Zipf, and d2/d1 bump still rule out raw NL.
  VMS is NL-like in word order but non-NL in character statistics.
- Hoax/random generation: **<2% → <1% (↓)** — Known generation methods
  (copy-modify, grille systems) produce TMA ≈ 0. VMS TMA = 0.123
  requires genuine word-order structure, strongly arguing against
  meaningless generation.
- Simple substitution: **<2% (unchanged)**

**Phase 84 Key Insight:** VMS has ANOMALOUSLY HIGH word-order mutual
information — higher than most natural language texts. This is the
first statistical dimension where VMS looks MORE structured than NL,
not less. The text carries significant word-order information that
survives comparison to shuffled controls, ruling out purely generated
text and strengthening the case for meaningful content. The verbose
cipher model partially preserves this information (42-97%) but
underpredicts VMS by 4×, identifying a gap that future cipher models
must address. Currier A and B show nearly identical TMA, contradicting
quimqu's finding of A-generative / B-meaningful, and suggesting both
sublanguages encode word-order structure equally.

**Paradox identified:** VMS is simultaneously MORE structured than NL
in word-order MI (TMA = 1.9× NL average) and LESS structured than NL
in character entropy (h_char = 0.64 vs NL 0.83). This combination —
high inter-word structure with low intra-word diversity — is precisely
what a verbose positional cipher produces, but our cipher model doesn't
generate enough inter-word MI. The resolution likely requires a cipher
with CONTEXTUAL dependencies (where cipher output depends not just on
the current plaintext letter and its position, but also on adjacent
plaintext context).

---

### Phase 85 — Chunk-Level Statistical Fingerprint ★★★

**Origin:** Mauro's LOOP grammar (Voynich Ninja thread-4418, Nov 2024)
decomposes 99.8% of VMS words into repeating chunks — each chunk fills
5 ordered slots: S1(ch/sh/y) S2(e-run/q/a) S3(o) S4(i-run/d) S5(coda).
606 unique chunks from Mauro; our implementation yields 523 chunk types.

**HYPOTHESIS TESTED:** The h_char anomaly (0.641) is a unit-of-analysis
artifact. If chunks are the true atomic units (≈ syllables), measuring
entropy at the chunk level should yield NL-like h_ratio ≈ 0.80-0.85,
explaining why character-level measurement appears anomalously low.

**Implementation:** Greedy left-to-right LOOP parser, S1→S2→S3→S4→S5
in order within each chunk, up to 6 chunks per word. Parse ambiguity
tested via alternative y-onset-preferred parser.

**Core results:**

| Level | H(x) | H(x\|prev) | h_ratio | Types | NL equivalent |
|---|---|---|---|---|---|
| Character | 3.864 | 2.523 | 0.653 | 31 | NL char: 0.849 |
| **Chunk** | **6.287** | **5.141** | **0.818** | **523** | NL syl: 0.501 |
| Word | 10.430 | 4.326 | 0.415 | 8,212 | NL word: 0.441 |

**KEY FINDING: VMS h_chunk = 0.818 does NOT match NL syllable h_ratio
(0.501 ± 0.056, z = +5.64). Chunks are NOT syllable-equivalent.**

Instead, VMS chunk h_ratio most closely matches **NL character h_ratio**
(0.849 ± 0.018, z = −1.70). Chunks behave like NL *characters* in their
sequential predictability — they are nearly independent of their
predecessor, just as characters in natural text are.

**Null model validation:**

1. **Shuffled slot grammar** (100 permutations): Random glyph→slot
   assignments yield h_ratio = 0.678 ± 0.020, n_types = 208 ± 42.
   Mauro's grammar: h_ratio = 0.818, types = 523. z = +7.02 on h_ratio.
   **The grammar is specific to VMS** — random grammars produce
   fundamentally different chunk statistics.

2. **Character-shuffled VMS**: Shuffling glyphs within words then parsing
   yields h_ratio = 0.872 ± 0.001, types = 882 ± 10. Real VMS: z = −105.
   **The slot grammar captures genuine word-internal structure**, not
   parsing flexibility.

**Additional findings:**

- **Parse coverage:** 99.81% of glyphs successfully parsed into chunks.
  Only 292/40,351 words (0.72%) had unparsed glyphs.
- **Parse ambiguity:** Only 1.4% of words (585/40,351) parse differently
  under the alternative y-onset-preferred parser. Decomposition is robust.
- **Chunks per word:** mean = 1.946. Distribution: 1 chunk = 26.9%,
  2 chunks = 55.8%, 3 chunks = 13.8%, 4+ = 3.4%.
- **Top 10 chunks cover 42.2%** of all tokens; top 30 cover 70.8%;
  top 100 cover 91.8%. NL syllable top-10 coverage: ~15-28%. VMS chunk
  frequency is much more concentrated than NL syllable frequency.
- **523 chunk types** — far below NL syllable range (1,378–5,078) but
  far above NL alphabet size (~31). An intermediate zone.
- **Within-chunk glyph entropy** = 3.30 (weighted across positions).
  NL within-syllable glyph entropy = 3.58–3.99. VMS chunks have
  slightly MORE constrained internal structure than NL syllables.
- **Currier A vs B:** A h_ratio = 0.808, B h_ratio = 0.772. Both are
  in the NL-character range. B is slightly more predictable.
- **Cross-section:** herbal 0.794, recipe 0.759, balneo 0.749,
  cosmo 0.669, astro 0.709. All sections maintain consistent pattern.

**The three-level hierarchy (CORRECTED after revalidation):**

VMS has three distinct structural levels, each matching a DIFFERENT
level of natural language:

| VMS level | h_ratio | Matches NL... | z-score |
|---|---|---|---|
| Glyph (EVA char) | 0.653 | — | −10.7 vs NL char |
| **Chunk** | **0.818** | **NL character** | **−1.7 vs NL char** |
| Word | 0.415 | NL word | −0.4 vs NL word |

This mapping implies:
- VMS **glyphs** = sub-character features (like stroke components)
- VMS **chunks** = functional characters (like alphabet letters)
- VMS **words** = words

The h_char anomaly arises because we've been measuring entropy at the
sub-character level. But this does NOT fully resolve the puzzle, because
h_chunk (0.818) is still BELOW the NL character mean (0.849) — chunks
are slightly MORE predictable from their predecessor than NL characters.
The residual gap (z = −1.7, marginal) could reflect genuine structural
difference or measurement noise.

**CRITICAL SELF-ASSESSMENT:**

The syllabic hypothesis was REFUTED (z = +5.64 against NL syllables).
The character-equivalence hypothesis is SUPPORTED (z = −1.7, within
the 2σ boundary). However:

1. If chunks = characters, then 523 chunk types is too many for a
   simple alphabet (need ~20-30). This suggests chunks are positional
   VARIANTS of a smaller set of base characters — consistent with the
   verbose positional cipher model (Phase 59/60).

2. The top-30 coverage (70.8%) means ~30 core chunks dominate, with
   a long tail of 493 rare variants. This matches a system where ~30
   base units have position-dependent or context-dependent spelling
   variants.

3. The concentration (top 100 = 91.8%) is MUCH higher than NL
   syllables (top 100 ≈ 52-74%) but consistent with a LETTER
   frequency distribution with spelling variants.

**What this changes:**

Phase 85 establishes that Mauro's LOOP grammar creates a genuine
intermediate structural level in VMS text. At this level, the
sequential predictability matches NL character-to-character behavior,
not syllable-to-syllable behavior. This is strong evidence that chunks
are the functional equivalent of LETTERS in the VMS script system,
with 30-50 core forms and hundreds of positional variants.

The asymmetry puzzle is REFRAMED but not resolved: the low h_char
(0.653) arises from sub-character (intra-chunk) constraints, and the
chunk level shows NL-character-like independence. But the WORD-level
statistics (Zipf, hapax, MI) match NL words, which is expected if
words composed of 2 independent chunks behave like words composed
of 2-3 letters — which they do.

**REVISED CONFIDENCES (Phase 85):**
- Natural language in unknown script: **85% (unchanged)**
- Script has positional slot grammar (I-M-F): **97% (unchanged)**
- **LOOP grammar captures genuine VMS structure: 99% NEW** — coverage
  99.8%, z = +7.0 vs shuffled grammars, z = −105 vs char-shuffled,
  parse ambiguity only 1.4%
- **Chunks = functional characters (not syllables): 75% NEW** — h_ratio
  z = −1.7 vs NL characters (within 2σ); z = +5.6 vs NL syllables
  (outside). 523 types consistent with ~30 base + variants.
- **Chunks = syllables: <10% REFUTED** — z = +5.6, type count 6×
  too low, frequency distribution too concentrated
- **h_char anomaly is sub-character artifact: 60% NEW** — chunk-level
  h_ratio matches NL characters. But the residual gap (z = −1.7) and
  the type count discrepancy (523 vs ~30) prevent full confidence.
- Positional verbose cipher with ~13 base chars: **40% (↑ from 35%)**
  — 523 chunk types = ~30 core + variants is consistent with verbose
  cipher where ~13-30 plaintext letters each produce 1 chunk, with
  position-dependent variant selection generating the long tail
- VMS is NOT plain natural language: **99% (unchanged)**
- Simple substitution cipher: **<2% (unchanged)**
- Hoax/random: **<1% (unchanged)**

**Phase 85 Key Insight:** VMS has three structural levels — glyph,
chunk, word — that map onto sub-character, character, and word levels
of natural language. The 84-phase "h_char anomaly" may be an artifact
of measuring at the wrong level: VMS EVA glyphs are sub-character
features, not characters. The real characters are chunks, and their
sequential statistics match NL character behavior (z = −1.7). However,
this is NOT the same as saying chunks are syllables — syllable-level
metrics diverge strongly (z = +5.6). The most parsimonious model: VMS
uses a positional verbose script where each functional character (≈ chunk)
has internal slot structure, producing ~30 core forms with ~493 spelling
variants. This is unique among known writing systems but consistent with
a deliberately designed cipher script.

---

---

## Phase 82 — Medieval German Charm/Incantation Fingerprint Test

### Motivation

Phase 81 revealed that Goethe's Faust (modern German verse) is
statistically closer to VMS than medieval German recipes (BvgS).
This is anomalous: if VMS contains any German, MEDIEVAL German
should match better than MODERN. The result hinted that **verse
structure** (rhythm + lexical variety) rather than **language era**
drives the fingerprint match.

Phase 82 tests an alternative German plaintext model: medieval
Segen (blessings) and Zaubersprüche (magic spells). These texts:
- Are the correct era (OHG 9th-10th c., MHG 11th-12th c.)
- Combine rhythmic repetition with varied vocabulary
- Mix German and Latin (matching f116v marginalia)
- Use short formulaic words

### Corpus

All 15 surviving OHG/MHG charms compiled from Wikisource/Wikipedia:
Merseburg Charms 1-2, Lorsch Bee Blessing, Vienna Dog Blessing,
Pro Nessia, Contra Vermes, Strasbourg Blood Blessing (3 parts),
Ad catarrum dic, De hoc quod spurihalz dicunt, Ad equum errehet,
Gegen Fallsucht (2 MS versions), Incantacio contra equorum.

**Total: 587 tokens, 377 types.** This is ~80× smaller than VMS
(40,368 tokens) — a FATAL limitation for full fingerprint comparison.

### Key Results

| Metric | VMS | OHG/MHG Charms | BvgS | Faust |
|--------|-----|----------------|------|-------|
| mean\_word\_len | 5.10 | 4.67 | 4.19 | 4.78 |
| h\_char\_ratio | 0.657 | 0.842 | 0.827 | 0.825 |
| WLD L1 dist | — | **0.424** | 0.705 | 0.558 |
| hapax@mid | 0.734 | 0.730† | 0.628 | 0.658 |
| full distance | — | 1.083‡ | 0.458 | 0.324 |

† Trivially expected at N=587 (most words are hapax in a tiny corpus).
‡ UNRELIABLE: TTR@587 and Zipf@587 are not comparable to TTR@5000.

**WLD ranking** (L1 distance to VMS word-length distribution):
1. French Viandier (0.416)   2. **OHG/MHG Charms (0.424) ★**
3. Latin Vulgate (0.479)   ...   9. German BvgS (0.705)

### Prediction Tests

| # | Prediction | Result |
|---|-----------|--------|
| P1 | Charms have closer word length to VMS than BvgS | **CONFIRMED** (Δ=0.43 vs 0.92) |
| P2 | High hapax ratio from lexical variety | **UNFALSIFIABLE** (trivial at N=587) |
| P3 | Charm h\_char does NOT match VMS 0.641 | **CONFIRMED** (charm=0.842, normal NL) |
| P4 | 500-word samples show high noise (CI width > 0.15) | **CONFIRMED** (CI width ≈ 0.37) |
| P5 | Charm WLD closer to VMS than BvgS AND Faust | **CONFIRMED** (0.424 < 0.558 < 0.705) |

### Small-Sample Calibration

500-word bootstrap windows from larger corpora (200 resamples):
- **Faust@587**: mean dist=0.809, 95% CI=[0.639, 1.005], width=0.366
- **BvgS@587**: mean dist=0.465, 95% CI=[0.283, 0.617], width=0.335
- **Caesar@587**: mean dist=1.279, 95% CI=[1.072, 1.472], width=0.400

CI width ≈ 0.37 exceeds the full-corpus distance range (0.31-0.62),
confirming that **fingerprint comparison is UNRELIABLE at N≈587**.

### Critical Synthesis

1. **CORPUS SIZE PROBLEM (fatal):** 587 words is statistically
   meaningless for Heaps β, Zipf α, TTR, and word-bigram entropy.
   Only word-length distribution and h\_char are usable.

2. **WORD LENGTH DISTRIBUTION — the one reliable finding:** Charms
   rank #2 (WLD L1 = 0.424), beaten only by French Viandier (0.416),
   and far ahead of BvgS (0.705). This is the **most robust result**
   of Phase 82.

3. **h\_char ANOMALY PERSISTS:** Charm h\_char = 0.842, squarely in
   normal NL range. No natural language plaintext — including
   medieval German charms — matches VMS's 0.641. This anomaly
   requires an encoding layer explanation, not plaintext genre.

4. **THE REAL LESSON FROM PHASES 81+82:** The "Faust anomaly" is
   driven by **vocabulary richness** (high TTR, moderate Zipf), not
   verse/charm structure per se. VMS requires a plaintext model
   with rich vocabulary, not necessarily a specific genre.

5. **BILINGUAL MIXING:** Charms contain 4.4% Latin/Christian words,
   consistent with f116v's German/Latin marginalia. This is
   suggestive but not diagnostic.

### Verdict

**INCONCLUSIVE due to corpus size.** The OHG/MHG charm hypothesis
is interesting and shows one genuine signal (WLD rank #2), but the
surviving corpus is too small for reliable fingerprinting. The
h\_char anomaly remains unexplained by any plaintext model tested.

**REVISED CONFIDENCES (Phase 82):**
- Natural language: **93% (unchanged)**
- German charm plaintext: **10% (NEW)** — WLD signal is suggestive
  but corpus too small; h\_char anomaly unresolved
- h\_char requires encoding layer: **78% → 80% (UP)** — another NL
  genre fails to match, strengthening the encoding hypothesis
- Vocabulary richness as key discriminant: **NEW 65%** — Phases 81+82
  converge: the closest VMS matches are vocabulary-rich texts
- Hoax/random: **<1% (unchanged)**


---

## Phase 83 — Encoding Layer Parameter Sweep

### Motivation

94 phases converge on ONE central unsolved anomaly: h\_char\_ratio
(H(c|prev)/H(c)) = 0.641 for VMS vs 0.82-0.90 for ALL tested natural
languages. Phases 59-61 tested encoding transformations on Italian only.
Phase 64's tournament covered 7 models on Italian only.

**What had never been done:** Apply a parametric FAMILY of encodings to
MULTIPLE source languages simultaneously and find which (language,
encoding) combination minimizes distance to VMS across ALL 6 fingerprint
metrics. This is constraint-satisfaction, not hypothesis-testing.

### Method

5 encoding families × 8 source languages = **192 (language × encoding)
combinations**, each scored against VMS on 6 metrics:

**Encoding families:**
- E1: Null (identity baseline)
- E2: Vowel expansion (vowels → deterministic 2-char sequences,
  p=0.3 to 1.0)
- E3: Positional substitution (chars vary by word position, 2-5 zones)
- E4: Combined (E2+E3)
- E5: Bigram collapse (merge frequent pairs into single symbols, 5-30)

**Source languages:** German Faust, German BvgS, Latin Caesar, Latin
Vulgate, Latin Apicius, Italian Cucina, French Viandier, English Cury.

### Key Results

**OVERALL WINNER: German BvgS + 70% vowel expansion (dist=0.1277)**

| Rank | Language + Encoding | dist | h\_char | Heaps | wlen |
|------|---------------------|------|---------|-------|------|
| 1 | **German BvgS + E2 p=70%** | **0.128** | 0.663 | 0.758 | 5.35 |
| 2 | German BvgS + E2 p=85% | 0.161 | 0.618 | 0.754 | 5.59 |
| 3 | German BvgS + E2 p=50% | 0.173 | 0.715 | 0.764 | 5.02 |
| 4 | German BvgS + E2 p=30% | 0.221 | 0.764 | 0.764 | 4.68 |
| 5 | French Viandier + E2 p=30% | 0.235 | 0.755 | 0.688 | 5.40 |
| 6 | English Cury + E2 p=85% | 0.250 | 0.631 | 0.707 | 5.57 |
| — | VMS target | 0.000 | 0.641 | 0.753 | 4.94 |

**This is the closest match to VMS ever produced in this project.**
Distance 0.128 is 60% closer than the previous best (Faust null, 0.322).

### Best Encoding Per Language

| Language | Best Encoding | dist | Δh\_char |
|----------|--------------|------|----------|
| German BvgS | E2 vowexp p=70% | 0.128 | +0.022 |
| French Viandier | E2 vowexp p=30% | 0.235 | +0.114 |
| English Cury | E2 vowexp p=85% | 0.250 | -0.010 |
| German Faust | E1 null | 0.322 | +0.183 |
| Latin Vulgate | E5 collapse m=10 | 0.408 | +0.211 |
| Latin Caesar | E5 collapse m=30 | 0.410 | +0.185 |
| Latin Apicius | E5 collapse m=10 | 0.438 | +0.209 |
| Italian Cucina | E1 null | 0.448 | +0.213 |

### The h\_char Achievability

53 of 192 combinations achieve h\_char < 0.70. All use E2 (vowel
expansion). E3 (positional sub) alone pushes h\_char down only to ~0.70.
E5 (bigram collapse) barely affects h\_char. E4 (combined) destroys
word length (wlen > 10), making it useless.

Closest to VMS h\_char (0.641):
1. French Viandier + E2 p=70%: h\_char=0.645 (Δ=+0.004!)
2. English Cury + E2 p=85%: h\_char=0.631 (Δ=-0.010)
3. German Faust + E2 p=85%: h\_char=0.628 (Δ=-0.013)
4. German BvgS + E2 p=70%: h\_char=0.663 (Δ=+0.022)

**The h\_char anomaly is REPRODUCIBLE by vowel expansion at p≈70-85%.**
This is the first time in the project that the central anomaly has been
explained by a specific, parameterized encoding mechanism.

### Prediction Tests

| # | Prediction | Result |
|---|-----------|--------|
| P1 | Combined E4 wins | **REFUTED** — E2 alone wins; E4 destroys wlen |
| P2 | No encoding pushes h\_char < 0.60 | **REFUTED** — 9 combos do (all E2 p=100%) |
| P3 | Strong encoding destroys Heaps/Zipf | **REFUTED** — both preserved within 20% |
| P4 | Language matters more than encoding | **REFUTED** — encoding spread (0.92) >> language spread (0.32) |
| P5 | Italian outperforms German | **REFUTED** — BvgS ranks #1, Italian ranks last |

### Constraint Analysis

The binding constraint (worst metric) for the top results:
- Rank 1 (BvgS+E2p70): **mean\_word\_len** (Δ=8.2%) — too long by 0.41
- Rank 2 (BvgS+E2p85): **mean\_word\_len** (Δ=13.2%) — too long by 0.65
- Rank 6 (Cury+E2p85): **ttr\_5000** (Δ=19.4%) — too many types

The remaining residual is dominated by WORD LENGTH. Vowel expansion
increases word length (adding chars to vowels). At p=70%, BvgS words
grow from 4.19 to 5.35 chars — slightly overshooting VMS's 5.10.
The SWEET SPOT would be p≈60%, which we can interpolate would give
wlen ≈ 5.15 and h\_char ≈ 0.69.

### Critical Synthesis

**FINDING 1 — GERMAN BvgS IS THE BEST SOURCE LANGUAGE (SHOCKING):**
The medieval German recipe text that ranked #7 in Phase 81's
null-encoding comparison now ranks #1 when vowel expansion is applied.
This is because BvgS has EXACTLY the properties that vowel expansion
preserves: moderate vocabulary (Heaps β=0.764, near VMS 0.753),
moderate word length (4.19, which expansion pushes to VMS range),
and moderate Zipf (0.932, near VMS 0.942).

Phase 81's Faust anomaly is now EXPLAINED: Faust matched VMS under
null encoding because its VOCABULARY metrics (TTR, Zipf) happen to
land near VMS. But BvgS matches BETTER under encoding because its
BASE word length is closer to pre-expansion VMS.

**FINDING 2 — VOWEL EXPANSION IS THE ENCODING MECHANISM:**
Only E2 (vowel expansion) matches h\_char. E3 (positional sub),
E4 (combined), and E5 (bigram collapse) either fail to reduce h\_char
sufficiently or destroy other metrics. The mechanism is specific:
vowels expand to deterministic 2-char sequences, creating the
within-expansion predictability that suppresses H(c|prev)/H(c).

This matches Phase 59's finding that verbose cipher nailed h\_char,
but with a CRITICAL improvement: Phase 59 tested on Italian and got
dist=8.31. Phase 83 tests on BvgS and gets dist=0.128 — a 65×
improvement, because the SOURCE LANGUAGE matters enormously.

**FINDING 3 — ITALIAN IS THE WORST SOURCE LANGUAGE:**
Italian Cucina ranks LAST (dist=0.448, unimproved by any encoding).
This directly contradicts Phase 64's finding that VMS best matches
Italian/Dutch. The discrepancy: Phase 64 used null encoding only.
Italian's short words (mean 4.57) don't expand to VMS range as well
as BvgS's slightly longer words (4.19 → 5.35 at p=70%).

**FINDING 4 — P4 REFUTED, BUT THIS IS IMPORTANT:**
Encoding variation (spread 0.92) exceeds language variation (0.32).
This means the ENCODING CHOICE dominates over language choice.
The implication: identifying the correct encoding is MORE important
than identifying the correct source language.

### Skepticism Checklist

✗ **BvgS is small** (8,368 tokens vs 30K for Faust). Small corpora
  have noisier fingerprints. Must bootstrap to verify.

✗ **Vowel expansion is a toy model.** Real historical ciphers don't
  expand deterministic vowel pairs. Need to test whether MORE
  realistic encodings (e.g., Trithemius-style) also work.

✗ **The h\_char match may be coincidental.** E2 can achieve h\_char
  = 0.641 for ANY language at the right expansion probability. The
  question is whether other metrics ALSO match — and they do for BvgS.

✗ **Phase 61 showed positional entropy is anti-correlated.** The
  verbose cipher (Phase 60) produced WRONG word shapes. Phase 83's
  vowel expansion likely has the same problem. Must verify.

✗ **Selection bias.** We tested 8 languages and the one with the
  best PRE-ENCODING Heaps/Zipf match naturally benefits most from
  any encoding that fixes h\_char without damaging vocabulary metrics.

✗ **Medieval German recipe as VMS plaintext is IMPLAUSIBLE** on its
  face. The herbal section illustrations don't match cookbook content.
  But the STATISTICAL match doesn't claim semantic identity — it
  claims structural similarity in vocabulary dynamics.

### Verdict

**BREAKTHROUGH RESULT — German BvgS + vowel expansion at p=70%
produces distance 0.128, the closest VMS fingerprint match in the
entire project.** The h\_char anomaly is RESOLVED for the first time
by a specific, parameterized encoding mechanism (vowel expansion at
70% probability) applied to medieval German text.

**REVISED CONFIDENCES (Phase 83):**
- Natural language: **93% → 95% (UP)** — encoding + NL achieves
  dist=0.128; no previous model came this close
- h\_char explained by vowel expansion: **80% → 88% (UP)** —
  the ONLY encoding class that reproduces h\_char across all languages
- German source language: **10% → 35% (UP)** — BvgS ranks #1 under
  encoding; but "German" here means structural properties, not
  necessarily the literal language
- Positional verbose cipher: **30% → 20% (DOWN)** — E3/E4 fail;
  simple vowel expansion outperforms positional variants
- Italian source language: **~40% → 15% (DOWN)** — ranks last
  under encoding sweep
- Vocabulary richness as key: **65% → 50% (DOWN)** — Phase 83
  shows the ENCODING matters more than vocabulary richness
- Hoax/random: **<1% (unchanged)**

---

## Phase 84 — Revalidation of Phase 83 + Fifteenth-Century Cryptography Context

### Motivation

Phase 83 produced what appeared to be a blockbuster result: German BvgS + E2
vowel expansion at p=70% achieved distance 0.1277 from the VMS fingerprint —
60% closer than any previous model. Before building on this, we must attack
the result systematically. Additionally, Nick Pelling's article "Fifteenth
Century Cryptography" (ciphermysteries.com, 2016-07-06) provides historical
cipher context against which to evaluate both the result and the encoding model.

### Part A: Methodological Critique of Phase 83

**Issue 1 — VMS_TARGET vs. Computed Baseline Mismatch**

The script uses a hardcoded VMS_TARGET dict:
```
h_char_ratio: 0.641, heaps_beta: 0.753, hapax_ratio_mid: 0.656,
mean_word_len: 4.94, zipf_alpha: 0.942, ttr_5000: 0.342
```
But the script's own VMS baseline computation (Step 1 in output) yields:
```
h_char=0.6566, Heaps=0.7134, hapax=0.7337, wlen=5.10, Zipf=0.9268, TTR=0.3908
```
These differ substantially (h_char: 0.641 vs 0.657, Heaps: 0.753 vs 0.713,
hapax: 0.656 vs 0.734, wlen: 4.94 vs 5.10, TTR: 0.342 vs 0.391). The
hardcoded target appears to originate from earlier Phase 64/81 estimates using
slightly different metric implementations or text processing.

**Impact**: Distance=0 is unreachable — the code's own implementation of
these metrics on VMS data doesn't produce the target values. The "distance"
is measured to a phantom. This doesn't invalidate RANKING (all combos are
measured against the same phantom), but it means the absolute distance value
of 0.1277 is meaningless. BvgS+E2p70 is still #1, but it may not be as
close to the REAL VMS as the number suggests.

**Severity**: MODERATE. Rankings preserved, but confidence intervals around
the winning distance are wider than reported.

**Issue 2 — E2 Vowel Expansion: Stochastic Word-Type Inflation**

At p=1.0, the vowel expansion is deterministic: every instance of 'a' →
'a1', etc. This is a bijection on word types — same input word always
produces same output. Word-level metrics (Heaps, Zipf, TTR, hapax) are
EXACTLY preserved. Only h_char and mean_word_len change.

At p<1.0 (including the winning p=0.70), the expansion is STOCHASTIC: each
vowel instance has independent probability p of expanding. The same word
"und" might become "u5nd" in one occurrence and "und" in another. This
creates ARTIFICIAL word-type inflation — the ciphertext has MORE unique word
forms than the plaintext, not because of linguistic structure but because of
random coin flips (seeded by np.random.RandomState(83)).

This means the p=0.70 winner's Heaps/Zipf/TTR/hapax values are ARTIFACTS
of a specific random seed, not properties of the language+encoding system.
The "match" to VMS on vocabulary metrics is partly luck.

At p=1.0, BvgS drops to rank #19 (dist=0.3910) because h_char overshoots
(0.556, too low) and vocabulary metrics revert to raw BvgS values (which
happen to be poor: TTR=0.2412 — way below VMS 0.342).

**Severity**: HIGH. The stochastic p<1.0 regime is conceptually incoherent
as a cipher model (a real cipher must be deterministic for decryption), and
the "winning" vocabulary metrics depend on seed choice.

**Issue 3 — BvgS Corpus Size**

BvgS has only 8,368 tokens vs. 30,000 for Faust, 30,000 for Caesar, etc.
Smaller corpora produce noisier estimates of Heaps β, Zipf α, and TTR.
The winning BvgS distance of 0.1277 might partly reflect fortunate sampling
noise. A confidence interval via bootstrap would be needed to confirm.

**Severity**: MODERATE. The top 4 are ALL BvgS, suggesting a real signal,
but the margin over French (0.2353) could shrink with bootstrap.

**Issue 4 — The "a→a1" Model Is Not a Real Cipher**

The vowel expansion model (a→a1, e→e2, ...) is a toy computational model,
not a historically plausible 15th-century encoding technique. No known
cipher from any era works by appending digit-like characters to vowels.
The model demonstrates that vowel-targeted expansion CAN produce VMS-like
h_char, but this is a proof of concept, not an identification of the actual
mechanism.

**Severity**: LOW for the theoretical insight, HIGH for literal claims.

**Issue 5 — Phase 61 Word-Shape Problem Not Addressed**

Phase 61 showed that positional entropy patterns (word beginnings vs
endings) in VMS are ANTI-CORRELATED with Italian, and that simple encoding
models fail to reproduce VMS word-internal structure. Phase 83 measures
only 6 aggregate metrics and does not check whether BvgS+E2 produces
VMS-like positional glyph distributions. It almost certainly does not,
since E2 doesn't constrain which characters appear at word boundaries.

**Severity**: HIGH. The 6-metric distance hides the word-shape failure.

### Part B: What the Cipher Mysteries Article Teaches Us

Nick Pelling's article surveys the actual cryptographic toolkit available in
Northern Italy c. 1400–1460. Key points for our research:

**1. The Historical Cipher Toolkit (14th–15th century):**

| Feature | Date | Example |
|---|---|---|
| Monoalphabetic substitution + nulls | 1379 | Lavinde Vatican ledger |
| Nomenclator (whole-word codes) | 1379+ | ~12 common words coded |
| Homophonic vowels (3 shapes/vowel) | 1401 | Mantua cipher |
| Doubled-letter symbols | 1450 | Mantuan cipher |
| Syllable-group encoding (ab,ac,ad...) | 1450 | Mantuan cipher |
| Homophones for ALL letters | ~1460 | Orsini cipher |
| Space removal (anti-word-boundary) | ~1500 | Venice |

**2. The Vowel Obfuscation Insight:**

Pelling's central argument: homophonic vowel substitution was NOT primarily
a defense against frequency analysis (which was not widely known until
Alberti c. 1466). Instead, it was a practical defense against a simpler
attack: **Italian words end in vowels**, making vowels trivially
identifiable at word endings. Multiple shapes per vowel were introduced to
obscure this obvious pattern.

This is directly relevant to Phase 83's E2 model. VMS achieves
h_char ≈ 0.64, and the only encoding class that approaches this is E2
(vowel-targeted expansion). The article confirms that historical cipher
design ALSO specifically targeted vowels. The theory converges from two
independent directions: our statistical analysis says "the encoding acts
on vowels," and the historical record says "15th-century ciphers
targeted vowels."

**3. Pelling's Verbose Cipher + Abbreviation Hypothesis:**

Pelling proposes a TWO-LAYER model for VMS:
1. Plaintext is first ABBREVIATED (scribal contraction/truncation)
2. Abbreviated text is then enciphered with a VERBOSE cipher (common
   letter pairs → multi-character cipher sequences)

This would explain:
- Why Voynichese words are roughly the same length as NL words
  (abbreviation shrinks, verbose cipher expands, effects cancel)
- Why VMS has rigid positional structure in character placement
  (the verbose cipher pairs enforce position-dependent patterns)
- Why h_char is low (verbose pairs create highly predictable character
  sequences — the second char of a pair is determined by the first)

This is MORE historically plausible than our "a→a1" toy model.

**4. Pelling's Paradox:**

"The Voynich Manuscript stands outside the cipher-making traditions...
too few cipher shapes to be using homophonic cipher tricks... And yet...
its author devised or adapted an alternative way of concealing the
plaintext's vowels."

The VMS has ~35 distinct EVA characters — far fewer than the 60-200 shapes
in diplomatic cipher alphabets. So it can't be a standard homophonic
cipher. Yet it successfully hides its vowels. Something else is going on.

**5. Rene Zandbergen's Three Tests (from comments):**

When Tranchedino-style diplomatic ciphers are applied to Italian/Latin:
1. Alphabet size increases from ~25 to 60+
2. Single-character frequency distribution flattens
3. Zipf curve flattens

"None of the three are seen in the VMS text. There is no commonality."

This is important: standard 15th-century ciphers (even with homophones,
nomenclators, nulls) produce statistical signatures that are ABSENT from
VMS. Whatever encoded VMS text is qualitatively different from the known
diplomatic cipher tradition.

**6. J.K. Petersen's Positional Rigidity Observation (from comments):**

"The glyphs in the VMS are positional. Certain characters at the beginning,
certain characters in the middle, certain characters at the end. I have
never seen a natural language substitution code... that has this specific
underlying structure."

This is the constraint our models keep failing on (Phase 61, and now
Phase 83's E2 which doesn't even test for it).

### Part C: Integration — What Survives Revalidation?

**What holds up:**

1. VOWEL-TARGETED ENCODING is the only encoding class that reproduces
   VMS-like h_char. This is confirmed by both the Phase 83 sweep AND
   by the historical record (Pelling's vowel obfuscation thesis).
   **STRONG finding.**

2. ENCODING MATTERS MORE THAN LANGUAGE (P4 result). This survives
   revalidation because it's measured across all combos, not dependent
   on BvgS specifically. **MODERATE finding.**

3. ITALIAN RANKS LAST. Even correcting for BvgS noise, Italian Cucina
   performs worst under ALL encoding families. **MODERATE finding.**

4. E3 (positional substitution) and E4 (combined) FAIL catastrophically
   by inflating word length beyond any plausible range. **STRONG finding
   (negative result).**

**What does NOT hold up:**

1. ~~"BvgS+E2p70 achieves distance 0.1277"~~ — The distance is measured
   to a phantom target that differs from the script's own VMS computation.
   The absolute number is misleading.

2. ~~"60% closer than any previous model"~~ — Comparative claim fails
   because the target baseline changed between phases.

3. ~~"German ranks #1"~~ — BvgS's "winning" vocabulary metrics at p=0.70
   are seed-dependent stochastic artifacts, not stable language
   properties. At p=1.0 (deterministic), BvgS drops to #19.
   German Faust at null encoding (0.3219) is still noteworthy but
   unremarkable.

4. ~~"53/192 combos achieve h_char < 0.70"~~ — This holds, but it's
   trivially true: E2 can push h_char arbitrarily low by increasing p.
   The question was never whether h_char CAN be lowered, but whether
   lowering h_char preserves OTHER metrics. At p=1.0, it doesn't
   (vocabulary metrics unchanged, wlen overshoots).

### Part D: Revised Research Priorities

Based on revalidation + historical cipher context:

**Priority 1 — Verbose Cipher Model (Pelling's hypothesis)**

Instead of the toy "a→a1" expansion, implement a historically plausible
verbose cipher where common plaintext PAIRS (bigrams or character pairs)
map to multi-character cipher tokens. This is Pelling's model: the cipher
operates on PAIRS not individual characters, producing deterministic
2-character outputs for each pair. This would:
- Be deterministic (real cipher, not stochastic)
- Naturally produce low h_char (second char predicted from first)
- Not inflate vocabulary metrics artificially
- Be historically plausible

**Priority 2 — Abbreviation + Verbose: The Two-Layer Model**

Test Pelling's full hypothesis: first abbreviate text (truncate words to
3-4 chars), then apply verbose cipher. Measure whether this combination:
- Preserves mean word length near VMS range
- Produces low h_char
- Maintains VMS-like Heaps/Zipf

**Priority 3 — Positional Constraint Testing**

Any future model MUST be tested for VMS-like positional glyph placement
(certain chars only at word start, others only at word end). This is the
hardest constraint and the one every model has failed on so far.

**Priority 4 — Fix the VMS_TARGET**

Use the script's OWN computed VMS fingerprint as the target, not hardcoded
values from earlier phases. Rerun the sweep with corrected target.

### Part E: Revised Confidence Assessments

(Corrections to Phase 83's over-optimistic updates)

- Natural language plaintext: **95% → 90% (DOWN)** — vowel-targeted
  encoding is promising but the "proof" was methodologically flawed
- h_char explained by vowel-targeted encoding: **88% → 75% (DOWN)** —
  confirmed as the right CATEGORY of explanation, but the specific
  mechanism (a→a1) is a toy model; the REAL mechanism is unknown
- German source language: **35% → 15% (DOWN)** — BvgS "win" was a
  stochastic artifact + small corpus noise
- Verbose cipher (Pelling-style): **20% → 45% (UP)** — article provides
  strong historical motivation; this is the most plausible mechanism for
  producing both low h_char AND positional structure
- Abbreviation + encoding hybrid: **NEW: 40%** — Pelling's two-layer
  model elegantly explains the word-length invariance puzzle
- Italian source language: **15% (unchanged)** — still ranks last, but
  the article's total focus on Northern Italian diplomatic ciphers means
  we shouldn't dismiss it entirely
- Positional structure as key unsolved constraint: **NEW: 95%** — every
  review of the evidence, including Petersen's and Pelling's comments,
  converges on this as THE distinguishing feature no model has reproduced
- Hoax/random: **<1% (unchanged)**

---

## Phase 85 — Pelling-Style Two-Layer Cipher: Build and Test

### Objective

Implement and test the historically-motivated two-layer cipher model
proposed by Nick Pelling: (1) abbreviation/truncation of plaintext,
then (2) deterministic verbose cipher where plaintext bigrams map to
fixed multi-character output chunks. This is the first model we've
tested that has genuine 15th-century historical backing.

### Method

Two cipher architectures tested:

- **Nonjoint**: Plaintext character bigrams → 2-character output pairs.
  Output alphabet divided into I/M/F zones to potentially reproduce
  positional slot structure. Non-overlapping bigram walks (stride-2).
- **Overlap**: Each character encoded using (prev_char, current_char)
  context → single output character. Word length preserved (1:1).
  No engineered positional zones — structure must emerge naturally.

Layer 1 (abbreviation): truncate words to max_len ∈ {3, 4, 5, 6, None}.

Parameter grid: 5 abbreviation × 2 cipher types × 3 alphabet sizes
(25/30/35) = **30 configs × 5 source languages = 150 tests**.

Source corpora: Latin Apicius (30K tokens), Latin Galen (30K), German
BvgS (8K), German Ortolf (9K), Italian Cucina (25K).

Metrics: 6 global fingerprint metrics + positional concentration +
I*M+F* slot grammar conformance + cross-boundary conditional entropy +
word-length distribution JSD.

**Critical correction from Phase 84**: VMS target fingerprint computed
LIVE from actual folio data, not from phantom hardcoded values.

### VMS Baseline (live-computed)

| Metric | Value |
|--------|------:|
| h_char | 0.6566 |
| Heaps β | 0.7134 |
| hapax ratio | 0.7337 |
| mean word length | 5.10 |
| Zipf α | 0.9268 |
| TTR@5000 | 0.3908 |
| Positional concentration | 0.7870 |
| I*M+F* conformance | 62.1% |
| Cross-boundary H(init\|final) | 3.0303 |

### Results

**Top 5 by global fingerprint distance:**

| Rank | Source | Config | dist | h_char | Heaps | wlen | IMF% | posConc |
|---:|--------|--------|-----:|-------:|------:|-----:|-----:|--------:|
| 1 | Italian Cucina | overlap/a35 | 0.3763 | 0.8476 | 0.5975 | 4.57 | 96.1% | 0.6606 |
| 2 | Italian Cucina | nonjoint/a35 | 0.3768 | 0.8485 | 0.5983 | 4.57 | 68.3% | 0.7091 |
| 3 | Italian Cucina | nonjoint/a30 | 0.3886 | 0.8584 | 0.5983 | 4.57 | 69.0% | 0.7116 |
| 4 | Latin Apicius | nonjoint/a35 | 0.3949 | 0.8417 | 0.6019 | 5.03 | 94.9% | 0.7158 |
| 5 | Latin Apicius | overlap/a35 | 0.4101 | 0.8544 | 0.6005 | 5.03 | 100% | 0.7043 |

### Prediction Outcomes

**P1 — h_char in [0.60, 0.72]: REFUTED**
Zero out of 150 configurations produced h_char in the VMS range.
Every single combination yielded h_char ≥ 0.80. The Pelling verbose
cipher produces output that is NOT predictable enough at the character
level. This is the **critical failure** of the model.

Why? Within cipher "chunks" (bigram→pair), the second character is
perfectly predicted from the first. But at chunk BOUNDARIES (end of
one pair → start of the next), consecutive characters are essentially
independent. These boundary transitions wash out the within-chunk
predictability, pulling h_char UP to ~0.85. VMS's h_char of 0.66
requires that EVERY consecutive character pair be predictable, not
just pairs within cipher chunks.

**P2 — I*M+F* slot grammar fails: CONFIRMED**
Top-5 models average 85.7% conformance vs VMS's 62.1% — a 23.5% gap.
The zone-based output alphabet creates TOO MUCH positional rigidity.
The nonjoint cipher at alpha_size=35 with Italian Cucina got 68.3%
(close to VMS), but the h_char at 0.85 is fatally far from VMS 0.66.

**P3 — Abbreviation helps: REFUTED**
Best without abbreviation: 0.3763. Best with: 0.4556. Abbreviation
destroys vocabulary metrics (Heaps, hapax) without compensating gains.

**P4 — Cross-boundary prediction fails: REFUTED (partially)**
Some models match boundary entropy within ~13% (nonjoint Italian Cucina:
3.039 vs VMS 3.030). But this appears to be a weak test — most natural
language + cipher combinations produce similar boundary entropy.

**P5 — No dual match (h_char + positional): CONFIRMED**
Zero configurations simultaneously match h_char (within 5%), IMF rate
(within 10%), and positional concentration (within 10%).

### Cipher Type Comparison

| Type | Best dist | Mean top-10 dist | Mean h_char | Mean IMF% | Mean posConc |
|------|----------:|-----------------:|------------:|----------:|-------------:|
| Nonjoint | 0.377 | 0.423 | 0.866 | 87.8% | 0.697 |
| Overlap | 0.376 | 0.437 | 0.879 | 99.6% | 0.641 |

Both types fail identically on h_char. The overlap cipher (no engineered
zones) produces even MORE rigid positional structure (99.6% IMF) because
the deterministic mapping creates strict one-to-one positional relationships.

### Critical Analysis

**1. The h_char failure is fundamental, not parametric.**
This is not a tuning failure — it's a structural impossibility. Any
cipher that maps N plaintext characters to M output characters through
a deterministic table will have chunk boundaries where consecutive
output characters come from DIFFERENT mapping operations. At these
boundaries, there is no character-level predictability. The only way
to achieve h_char ≈ 0.65 across ALL consecutive pairs is if:
  - (a) The cipher has NO chunk boundaries (every output character
    depends on its immediate predecessor), OR
  - (b) The output alphabet is so small that collisions create
    artificial predictability, OR
  - (c) The low h_char comes from something other than the cipher
    mechanism — e.g., natural language word-boundary structure,
    or a constrained syllabary.

**2. The positional structure mismatch is informative.**
VMS has 62% I*M+F* conformance — low enough that ~38% of words VIOLATE
the slot grammar. The Pelling cipher produces 85-100% conformance
because the zone-based output is too rigid. This suggests VMS's
positional structure is SOFTER than what a zone-based cipher creates —
more like natural language positional tendencies than mechanical cipher
zone assignments.

**3. VMS's extreme final-position concentration remains unexplained.**
VMS's word-final position is dominated by 'y' (40.6%), with 'n', 'r',
'l' as distant seconds. The cipher models produce much more uniform
final distributions. No verbose cipher naturally creates this kind of
a single-glyph-dominant final position.

**4. Italian Cucina consistently outperforms other corpora.**
Across all configs, Italian Cucina produces the shortest global
distances (0.376-0.389). This is primarily because Italian word lengths
(mean ~4.5 chars) are closest to VMS when doubled by the nonjoint cipher
(~9 → too long) or preserved by the overlap cipher (~4.5 → close to
VMS 5.1). German and Latin words are longer, creating worse wlen matches.

**5. The Pelling model is historically motivated but statistically dead.**
The two-layer model (abbreviation + verbose bigram cipher) cannot
reproduce the VMS's most distinctive statistical property (h_char)
by a margin of +29% relative error. This isn't a close miss — it's a
fundamental architectural incompatibility.

### What This Means for the "Verbose Cipher" Hypothesis

The Pelling verbose cipher hypothesis is NOT refuted as a concept —
only the specific "bigram→pair" implementation tested here. The result
tells us something deeper: **whatever produced VMS must have continuous
character-to-character predictability without chunk boundaries**.

Possible models that COULD produce this:
1. **Syllabary**: Each output "word" IS a syllable, and characters
   within syllables have fixed relationships (like Japanese kana).
   This would produce h_char ≈ 0.65 because every char is part of
   a syllable template.
2. **Sliding-window cipher**: Each output character depends on the
   PREVIOUS output character (not just the previous input), creating
   chain dependencies that propagate predictability.
3. **Nomenclator with fixed spellings**: Entire words/concepts map to
   fixed multi-character tokens, and the "characters" are actually
   just sub-token segments of these fixed patterns.
4. **Natural language with constrained orthography**: If VMS IS a
   natural language, but written in a script with strong positional
   constraints (like Tibetan stacking), the low h_char could emerge
   from orthographic rules rather than cipher mechanics.

### Updated Confidence Levels

- Verbose cipher (Pelling bigram-style): **45% → 15% (DOWN)** — tested
  and failed on the most critical metric; the specific mechanism
  doesn't work, though the concept of "context-dependent encoding"
  remains viable
- Natural language plaintext: **90% → 85% (slight DOWN)** — the
  failure of verbose cipher slightly reopens the "structured" vs
  "natural" question
- h_char explained by cipher chunk structure: **75% → 40% (DOWN)** —
  chunk-based ciphers CAN'T produce the right h_char; something else
  is responsible
- Syllabary or nomenclator model: **NEW: 35%** — continuous
  character-to-character predictability without chunk boundaries
  points toward syllable-unit or whole-word-unit encoding
- Positional structure as key unsolved constraint: **95% (unchanged)**
  — now reinforced: even an engineered zone-based cipher produces
  the wrong kind of positional rigidity
- Italian source language: **15% → 25% (UP)** — Italian Cucina
  consistently outperforms; word-length profile is closest to VMS

---

## Phase 86 — Chunk Equivalence Class Discovery (+ 86R Revalidation)

**Question:** Can the 523 chunk types be clustered into a smaller set
of distributional equivalence classes? If so, what is the "true alphabet
size" of VMS?

### Method

1. Parsed all VMS words into chunks (LOOP grammar, 523 types, 78,526 tokens)
2. Extracted distributional features for 206 frequent chunks (≥20 tokens,
   covering 98.2% of chunk tokens):
   - Left/right context distributions (207-dim JSD vectors each)
   - Word-position profile (initial/medial/final, 3 dims)
   - Slot skeleton (which of 5 grammar slots filled, 5 dims)
3. Computed pairwise JSD-weighted distance matrix (206 × 206)
4. Agglomerative clustering (average-linkage)
5. Swept k = 10 to 200: silhouette score + collapsed-text fingerprint
6. Null models: random merging, frequency-rank merging, skeleton merging
7. NL cross-check: collapsed Latin/Italian/English/French syllables
8. Feature ablation: context-only, skeleton-only, position-only, all

### Headline Results

| k | Silhouette | h_ratio | Hapax | Types |
|---|-----------|---------|-------|-------|
| 15 | 0.296 | 0.856 | 0.000 | 16 |
| **25** | **0.250** | **0.849** | **0.000** | **26** |
| 30 | 0.243 | 0.848 | 0.000 | 31 |
| 50 | 0.245 | 0.847 | 0.000 | 51 |

At k = 25: h_ratio = 0.8486, gap = 0.0004 from NL character mean (0.849).
Zero hapax legomena — a closed alphabet. 26 functional types.

### Closest Chunk Pairs (distributional similarity)

| Distance | Chunk 1 | Chunk 2 | Slots |
|----------|---------|---------|-------|
| 0.046 | o.k | o.t | both 00101 |
| 0.071 | q.o.k | q.o.t | both 01101 |
| 0.084 | a.i.i.n | a.i.n | both 01011 |
| 0.088 | e.d.y | e.e.d.y | both 01011 |
| 0.094 | sh.e.o.r | sh.e.o.s | both 11101 |
| 0.094 | sh.e.y | ch.e.e.y | both 11001 |
| 0.105 | cth | ckh | both 00001 |

The closest pairs share slot skeletons AND differ only in one slot
value — strongly suggesting allographic variation within functional
equivalence classes.

### Null Model Comparison (k = 25)

| Method | h_ratio | Gap to NL (0.849) |
|--------|---------|-------------------|
| **Distributional** | **0.8486** | **0.0004** |
| Freq-rank merge | 0.9566 | 0.1076 |
| Random merge | 0.9693 | 0.1203 |
| Skeleton merge | 0.9286 | 0.0796 |

Distributional clustering is 270× closer to NL characters than random
merging, and 269× closer than frequency-rank. This is NOT a mathematical
artifact — it's genuine distributional structure.

### NL Syllable Cross-Check (CRITICAL)

When NL syllables are randomly collapsed to k = 25:

| Language | Base h_ratio | Random→k=25 | Freq-rank→k=25 |
|----------|-------------|-------------|-----------------|
| Latin-Caesar | 0.543 | 0.948 | 0.945 |
| Italian-Cucina | 0.596 | 0.972 | 0.971 |
| English-Cury | 0.479 | 0.968 | 0.965 |
| French-Viandier | 0.437 | 0.946 | 0.942 |

NL syllables collapse to h_ratio ≈ 0.94–0.97, NOT 0.85. The VMS result
(0.849) is SPECIFIC to VMS chunks under distributional clustering. This
confirms the finding is not a mathematical artifact of entropy collapse.

### Feature Ablation (at k = 25)

| Feature Set | h_ratio | Silhouette |
|-------------|---------|-----------|
| All features | 0.849 | 0.250 |
| Context only | 0.839 | 0.241 |
| Position only | 0.864 | 0.451 |
| **Skeleton only** | **0.947** | **0.848** |

Skeleton alone gives sharp clusters (sil=0.848) but WRONG h_ratio (0.947).
Context-based features are what drive the NL-char match. The information
is in distributional behavior, not structural similarity.

### Cluster Quality (Within/Between JSD)

- Within-cluster successor JSD: 0.161 ± 0.140 (1433 pairs)
- Between-cluster successor JSD: 0.560 ± 0.302 (436 pairs)
- **Ratio: 0.288** — cluster members are 3.5× more similar to each
  other than to members of other clusters.

This confirms the clusters represent genuine distributional equivalence
classes, not arbitrary groupings.

### Linkage Sensitivity (Caveat)

Single-linkage clustering gives h_ratio ≈ 0.98–0.99 — the NL-char match
depends on average-linkage. This doesn't invalidate the result (average-
linkage is theoretically better for this task) but means the finding
requires a specific, defensible analytical choice.

### Cluster Composition at k = 25

The largest 5 clusters (of 25 total):

| Cluster | Size | Top Members | Interpretation |
|---------|------|-------------|----------------|
| C0 | 57 | y, ch.e.d.y, ch.y, ch.e.y, d.y | Coda-heavy chunks (onset+coda families) |
| C1 | 44 | q.o.k, o.k, o.t, q.o.t, y.k | "Initial" chunks (high word-initial%) |
| C2 | 19 | e.e.y, e.d.y, e.e.d.y, e.y, e.o.l | Front-vowel + coda |
| C3 | 17 | a.i.i.n, a.r, a.l, a.i.n, a.m | Bench-mark: a+back-vowel+coda |
| C4 | 13 | d, o.d, ch.e.d, ch.d, ch.o.d | d-final / d-only chunks |

Cluster coherence: average intra-cluster skeleton entropy = 2.22 (high),
meaning clusters MIX different slot patterns. This is actually expected
and positive — it means the clustering is finding FUNCTIONAL equivalence
(same distributional role) rather than STRUCTURAL identity (same slot
pattern). Chunks with different internal structures that behave the same
way in context are grouped together.

### CRITICAL SELF-ASSESSMENT

**What Phase 86 establishes:**
1. VMS chunks cluster into ~25 distributional equivalence classes
2. These classes are genuine (within/between JSD = 0.288)
3. The collapsed h_ratio (0.849) matches NL characters precisely
4. This match is NOT a mathematical artifact (NL syllables give 0.95)
5. Distributional clustering is 270× closer to NL than random merging

**What Phase 86 does NOT establish:**
1. That k = 25 is uniquely correct — h_ratio varies little (0.833–0.856)
   across k = 10–200, so the "optimal" k is soft
2. That the clusters correspond to specific plaintext letters
3. That average-linkage is the "right" method (single-linkage fails)
4. Whether this is a cipher alphabet or a natural writing system

**What this changes:**

Phase 86 strengthens the "chunks = functional characters" hypothesis
from Phase 85 (75% → 85%). The ~25 equivalence classes with their
NL-character statistics confirm that the 523 surface chunk types
reduce to an alphabet-sized inventory of ~25 functional units.

The asymmetry puzzle is now SUBSTANTIALLY explained:
- EVA glyphs are sub-character features → low h_char (0.653)
- Chunks are functional characters (~25 classes) → NL-char h_ratio (0.849)
- Words are composed of ~2 chunks → NL word statistics (Zipf, hapax)

**REVISED CONFIDENCES (Phase 86):**
- Natural language in unknown script: **87% (↑ from 85%)**
- **Chunks = functional characters: 85% (↑ from 75%)** — distributional
  clustering to k≈25 gives h_ratio=0.849 (z<0.1 from NL char); 
  within/between JSD ratio 0.288 confirms genuine equivalence classes
- **True alphabet size ≈ 25: 70% NEW** — best combined silhouette +
  h_ratio match; consistent with European alphabet range (26–36) but
  soft optimum (k=15–35 all give similar results)
- **h_char anomaly resolved: 75% (↑ from 60%)** — three-level hierarchy
  (sub-char → char → word) with NL-match at chunk level, confirmed by
  distributional clustering reproducing NL char statistics exactly
- Positional verbose cipher: **45% (↑ from 40%)** — ~25 functional units
  with ~493 allographic variants matches verbose cipher prediction
- Hoax/random: **<1% (unchanged)**

---

## Phase 87 — Vowel-Consonant Spectral Separation

**Test:** Does the VMS chunk-to-chunk bigram transition matrix reveal a
vowel/consonant split? In every known alphabetic writing system, the 2nd
eigenvector of the row-normalized character bigram matrix separates vowels
from consonants due to universal V/C alternation patterns (CV, CVC, CVCC...).

**Method:** Build within-word chunk bigram matrix (top-50 chunks), 
eigendecompose the row-normalized transition matrix, examine 2nd eigenvector
for binary split. Compare against NL character baselines (Latin, Italian,
English, French), NL syllable control, two null models, Currier A/B 
cross-validation, and word-position confound check.

### Key results

| Metric | VMS chunks | NL chars (mean) | z-score |
|--------|-----------|-----------------|---------|
| Spectral gap | 0.4700 | 0.5534 ± 0.074 | -1.13 |
| Small-group ratio | 0.42 | 0.42 ± 0.04 | -0.08 |
| Alternation rate | 74.8% | 58.7% ± 13.9% | +1.16 |
| Stability (top-N) | 96–100% | — | — |
| Currier A/B Jaccard | 0.615 | — | — |

**The spectral split EXISTS and is highly stable** (96–100% retained
across top-30 to top-100; Jaccard 0.615 between Currier A and B). Against
the within-word shuffled null, z = 68.

### The split is POSITIONAL, not V/C

The critical finding: the 2nd eigenvector separates word-INITIAL chunks
from word-FINAL chunks, not vowels from consonants:

- "V-candidates" (negative v2): 66.7% word-initial (q.o.k 98.6%, o.k 94.7%, d 86.2%)
- "C-candidates" (positive v2): 60.1% word-final (a.i.i.n 85.9%, e.e.y, a.r, o.l)

This is exactly the positional structure Phase 86 identified. The internal
slot analysis confirms: no V-slot vs C-slot differentiation between groups.

### Method limitations exposed

1. **Purity metric was recall-only** (BUG, found in Phase 87R): The
   reported "83% purity" for Latin was RECALL — 5/6 vowels captured.
   But PRECISION was only 42% (12 symbols in "V-group", 7 were consonants).
   Corrected F1 scores: Latin 0.56, Italian 0.62, English 0.33, French 0.40.
   **Mean F1 = 0.48 — the method is near-random for V/C separation.**
2. **59% of chunk bigrams come from 2-chunk words** (each contributing
   exactly one I→F bigram). NL 2-letter words contribute only 4–7%.
   This makes VMS chunk bigrams structurally position-dominated.
3. **Syllable control failed**: NL syllable gaps (mean 0.50) are similar to
   NL character gaps (0.55), meaning the method detects ANY binary distributional
   asymmetry, not specifically V/C structure.
4. **Null model 1 (row-permuted) was INVALID** (found in Phase 87R): Row
   permutation preserves row sparsity, and random stochastic matrices with
   similar density have comparable gaps (0.735 ± 0.018). This null tested
   sparsity, not linguistic structure. **RETRACTED.**
5. **NL λ2 sign is not universally negative**: English has λ2 = +0.453.
   The "negative λ2 = V/C alternation" pattern holds for 3/4 NL languages.

### What Phase 87 establishes

1. VMS chunk bigrams have GENUINE ordering structure (z = 68 vs shuffle null)
2. The dominant structural axis is POSITIONAL (word-initial vs word-final),
   consistent with Phase 86's finding that clusters are positional bins
3. The spectral V/C test is INCONCLUSIVE — the positional confound
   overwhelms any possible V/C signal
4. The spectral method itself is unreliable for V/C detection (67–100%
   purity on known languages; syllable control fails)

### What Phase 87 does NOT establish

1. That VMS lacks V/C alternation — the method is too weak to detect it
2. That the positional structure is non-linguistic — NL systems also have
   strong positional patterns (capital letters, punctuation, word endings)
3. That chunks are NOT alphabetic characters

**Verdict: INCONCLUSIVE** — The spectral V/C method is insufficiently
sensitive to distinguish V/C from positional structure. A more targeted
approach (e.g., medial-position-only analysis to remove the I/F confound,
or analyzing chunk-internal structure for V/C patterns) would be needed.

### Phase 87R — Revalidation findings

**Bugs found and corrected:**
1. Purity metric was recall-only → corrected to F1 (mean drops from ~78% to 0.48)
2. Null model 1 (row-permuted) tested sparsity → RETRACTED
3. Stability sign-flip bug → fixed (actual stability 96–100%)

**New analysis: Eigenvalue structure comparison**

| System | N | λ2 | gap | vs NL z |
|--------|---|-----|-----|---------|
| NL chars (mean±std) | 25-29 | varies | 0.553 ± 0.074 | — |
| VMS chunks | 50 | -0.530 | 0.470 | -1.13 |
| VMS glyphs | 23 | +0.025 | 0.975 | +5.73 |

VMS chunk gap is in the NL range (z = -1.13); VMS glyph gap is FAR outside
(z = +5.7). The near-rank-1 glyph matrix (gap 0.975) confirms glyphs are
sub-character features dominated by rigid LOOP slot grammar — each glyph's
successor is nearly deterministic from the slot sequence, not from linguistic
content. This independently validates Phase 85's finding.

**New analysis: Position-corrected decomposition**

When 2-chunk words (59% of bigrams) are excluded:
- λ2 weakens from -0.530 to -0.152
- Positional confound drops (25% initial vs 52% initial)

The strong negative λ2 that appeared to match NL character structure was
**driven by I→F positional alternation in 2-chunk words**, not genuine V/C.

**New analysis: Glyph-level eigenvector**

The glyph 2nd eigenvector groups e(-0.62), i(-0.17), o(-0.09) — three LOOP
vowel glyphs — with no positional confound (negative group is 66% medial).
But λ2 = +0.025 is trivially small and 'a' (the 4th vowel) is misclassified.
The separation tracks the LOOP core sequence (e→o→i), not phonetic V/C.

**REVISED CONFIDENCES (Phase 87 + 87R):**
- Natural language: **87% (unchanged)** — Phase 87 neither confirms nor
  disconfirms; the positional structure is consistent with NL
- Chunks = functional characters: **85% (unchanged)** — eigenvalue structure
  supports chunks as character-level (gap in NL range, glyphs anomalous)
- True alphabet size ≈ 25: **70% (unchanged)**
- h_char anomaly resolved: **75% (unchanged)**
- Positional verbose cipher: **45% (unchanged)**
- Hoax/random: **<1% (unchanged)**

---


## Phase 87 — Gallows-as-Nulls Test

### Objective

Test the hypothesis that gallows characters (t, k, p, f, cth, ckh, cph,
cfh — 11.5% of all glyphs) are null insertions, and optionally that 'o'
(14.7%) is also null. If true, stripping them should improve h_char
toward the natural language range (0.82–0.90).

### Method

1. Strip gallows from all VMS words, recompute full 6D fingerprint
2. Strip 'o' only, recompute
3. Strip both gallows + 'o', recompute
4. **Control strippings**: remove {a, e, i} (~27%) and {d, l, r} (~18%)
   to test whether effects are gallows-specific or generic
5. Merge analysis: how many word-types collapse?
6. Positional distribution: where do gallows sit within words?
7. Currier A vs B: do gallows rates vary with section?
8. Line-position: do gallows favor line-initial words (Pelling claim)?

### Key Results

| Variant | h_char | Heaps | hapax | wlen | Zipf | TTR | Dist→TARGET | Types |
|---------|--------|-------|-------|------|------|-----|-------------|-------|
| VMS baseline | 0.653 | 0.751 | 0.719 | 5.05 | 0.924 | 0.377 | **0.145** | 8,212 |
| Gallows stripped | 0.683 | 0.712 | 0.683 | 4.43 | 1.077 | 0.265 | 0.301 | 5,427 |
| 'o' stripped | 0.691 | 0.724 | 0.698 | 4.41 | 0.993 | 0.314 | 0.181 | 6,466 |
| Both stripped | 0.714 | 0.679 | 0.658 | 3.79 | 1.234 | 0.199 | 0.591 | 3,793 |
| CTRL {a,e,i} | 0.805 | 0.688 | 0.675 | 3.82 | 1.057 | 0.289 | 0.406 | 5,231 |
| CTRL {d,l,r} | 0.709 | 0.689 | 0.683 | 4.28 | 1.065 | 0.279 | 0.298 | 5,178 |

### Critical Analysis

**1. Stripping gallows makes the overall fingerprint WORSE, not better.**
Distance doubles from 0.145 to 0.301. h_char gains +0.030 (still far from
0.82 NL minimum) but every other dimension degrades.

**2. The gallows effect is NOT specific to gallows.** Removing {d,l,r}
(18% of glyphs) gives distance 0.298 — essentially identical to gallows
removal (0.301). The h_char gain from {d,l,r} removal (+0.056) is actually
LARGER than from gallows removal (+0.030). Any structural glyph removal
produces comparable effects.

**3. Gallows are massively positionally biased (χ² = 6,161, df=2).**
Gallows are 16.2% of medial-position glyphs but only 0.5% of word-final
glyphs. Null characters should distribute uniformly; this is the pattern
of functional consonant-like characters occupying a specific structural slot.

**4. Section rates differ significantly.** Gallows: z = 3.70 (A: 11.9%,
B: 11.3%); 'o': z = 9.52 (A: 15.9%, B: 14.0%). Null characters should
have constant insertion rates independent of content.

**5. 51 words consist entirely of gallows.** These cannot be "null padding"
if the word has no other content.

**6. Line-initial gallows bias NOT confirmed (z = -0.35).** Pelling's claim
about gallows favoring paragraph/line-initial positions does not hold at the
line level in our data.

**7. Vocabulary merge is disproportionate but double-edged.** 33.9% type
reduction from 11.5% glyph removal (2.9x ratio). This means gallows
frequently differentiate otherwise-identical words — consistent with either
(a) nulls inflating vocabulary or (b) consonant-like differentiators.
The positional data strongly favors interpretation (b).

### Verdict

**GALLOWS = PURE NULLS: REJECTED** (confidence ~80%)

The positional structure, section variation, 51 all-gallows words, and
non-specific control comparison all point to gallows being functional
characters. A weaker claim survives: gallows may be partially redundant,
carrying some information with positional slot-grammar behavior.

### Updated Confidence Levels

- Gallows as pure nulls: **REJECTED** — positional χ²=6161, functional
  characters with medial preference
- Gallows as positional markers / slot grammar elements: **HIGH** —
  consistent with all observed data
- 'o' as null: **REJECTED** — 202 all-'o' words, section z=9.52

---

## Phase 88 — Position × Identity Decomposition

**Question:** Do VMS chunks form ONE alphabet used at all word positions
(NL character-like), or SEPARATE position-specific alphabets (positional
cipher-like)?

**Method:** For each chunk token in ≥2-chunk words, label by word-position
(I=initial, M=medial, F=final). Compute four metrics: Position Concentration
Index (PCI = max positional proportion per type), Jaccard overlap of
position-specific type inventories, Mutual Information I(type; position),
and percentage of type entropy explained by position. Same metrics computed
for NL characters (8 reference texts) and NL syllables. Null model:
within-word chunk shuffle (50 trials). Phase 60 reconciliation.

**Results — VMS vs NL characters (≥2-unit words):**

| Metric | VMS chunks | NL char μ±σ | z-score | Direction |
|--------|-----------|-------------|---------|-----------|
| Mean PCI | 0.804 | 0.671±0.039 | +3.40 | CIPHER |
| Weighted PCI | 0.825 | 0.636±0.029 | +6.55 | CIPHER |
| Restricted% (PCI>0.8) | 60.9% | 23.3%±10.2% | +3.68 | CIPHER |
| J(I,F) | 0.241 | 0.803±0.128 | -4.38 | CIPHER |
| J mean | 0.344 | 0.848±0.090 | -5.58 | CIPHER |
| NMI | 0.558 | 0.181±0.039 | +9.63 | CIPHER |
| MI/H(type)% | 13.0% | 6.2%±1.4% | +4.97 | CIPHER |

Score: **7/7 metrics favor CIPHER** vs NL characters.

**Results — VMS vs NL syllables (≥2-unit words):**

| Metric | VMS chunks | NL syl μ±σ | z-score | Direction |
|--------|-----------|------------|---------|-----------|
| Mean PCI | 0.804 | 0.891±0.050 | -1.75 | — |
| Weighted PCI | 0.825 | 0.842±0.056 | -0.31 | — |
| Restricted% | 60.9% | 75.3%±13.3% | -1.19 | — |
| J(I,F) | 0.241 | 0.066±0.039 | +4.52 | NL-direction |
| J mean | 0.344 | 0.134±0.064 | +3.28 | NL-direction |
| NMI | 0.558 | 0.700±0.104 | -1.37 | — |
| MI/H(type)% | 13.0% | 12.6%±1.5% | +0.23 | — |

Score: **0/7 cipher, 0/7 NL, 7/7 ambiguous** — VMS chunks are
INDISTINGUISHABLE from NL syllables on concentration/MI metrics. But
VMS has 3-4× MORE I/F overlap than NL syllables (J = 0.24 vs 0.07).

**Critical interpretation — the dual nature:**

Phase 85 established chunks ≈ characters in predictability (h_ratio 0.818
matches NL char 0.794, z = +5.64 ABOVE NL syllables 0.501). So the PRIMARY
comparison is chunks vs characters. The character comparison shows VMS chunks
are anomalously position-partitioned — behaving like characters that carry
character-level information but are deployed at position-specific locations.

This is precisely what a **positional verbose cipher** predicts: each chunk
encodes one plaintext character, but the encoding uses different glyph
combinations at different word positions. The result:
- h_ratio matches characters (each chunk IS one functional character)
- Positional concentration exceeds NL characters (encoding is position-dependent)
- Positional concentration is weaker than NL syllables (NOT sub-word morphemes)

**Type partitioning (≥2-chunk words, threshold=10 tokens):**
- Types at I only: **50** (40% of I inventory)
- Types at F only: **46** (39% of F inventory)
- Types at all 3 positions: **36** (just 18% of total qualifying types)
- Phase 60 predicted ~20% shared → observed **18%** (match within 2%)

**Phase 60 reconciliation:**
- Predicted J(I,F) from glyph-level cipher model: **0.273**
- Observed J(I,F) from chunk-level data: **0.241**
- NL character J(I,F): 0.803
- Match: VMS is **106% toward cipher**, -6% toward NL on the interpolation
- This prediction was computed months earlier at the glyph level, using an
  independent parameter search. The chunk-level match is independent
  confirmation.

**Null model validation:**
- Shuffled chunk order: PCI z=+306, NMI z=+839 from observed
- Positional coupling is overwhelmingly genuine, not compositional artifact.

**Length-controlled sub-analysis (≥3-chunk words only):**
- PCI z drops to +1.3 to +1.6 (ambiguous — concentration weakens)
- But J(I,F) remains at z = -4.14 and NMI at z = +5.79
- Even with M positions available, I and F inventories remain largely disjoint.

**Top-30 robustness (matching NL alphabet size):**
- Top-30 chunks: J(I,F) rises to 0.467 (vs all-chunks 0.241)
- Part of the low overlap is driven by rare position-locked types
- But 0.467 is still far below NL character mean (0.803)
- Even common chunks show genuine position partitioning.

**Method limitations:**
1. Word-length confound partially but not fully controlled (VMS 1.95 chunks/word
   vs NL 4.5 chars/word → VMS has far fewer M positions)
2. Alphabet-size confound (523 types vs 26-36 NL chars → more rare types
   trivially position-locked). Top-30 check mitigates but doesn't eliminate.
3. NL syllable comparison shows sub-word units naturally show similar or
   stronger positional concentration — the signal is not unique to ciphers.
4. No inner-position context consistency test (successor analysis would
   require more M-position data than available from 3+-chunk words).

**REVISED CONFIDENCES (Phase 88):**
- Natural language: **87% (unchanged)** — positional structure is
  compatible with NL at sub-word level (syllable comparison)
- Chunks = functional characters: **85% (unchanged)**
- True alphabet size ≈ 25: **70% (unchanged)**
- h_char anomaly resolved: **75% (unchanged)**
- Positional verbose cipher: **45% → 55%** — 7/7 metrics vs NL characters
  favor positional encoding; Phase 60 prediction independently confirmed
  (J=0.27 predicted vs 0.24 observed). Tempered by the NL syllable parallel
  (VMS is not MORE positional than syllables) and alphabet-size confound.
- Hoax/random: **<1% (unchanged)**

---

## Phase 89 — Cross-Position Context Divergence

**Question:** For the ~36 VMS chunks appearing at all word-positions (I, M, F),
do they function as the **same** linguistic unit at each position, or as
**different** units (homographs in a positional cipher)?

**Motivation:** Phase 88 found strong positional partitioning (J(I,F)=0.241),
but 36 chunk types DO appear at all 3 positions. If these shared chunks carry
the same context profile regardless of position, VMS has one alphabet with
positional preferences (NL-like). If they carry different context profiles,
they are homographs supporting a positional cipher.

### Method

For shared chunks appearing at both I and M positions in ≥3-chunk words:
- **Successor JSD**: Compare within-word successor distributions at I vs M
- **Predecessor JSD**: Compare predecessor distributions at M vs F
- **Conditional MI**: I(successor; position | chunk type) — does position
  add information about context beyond chunk identity?
- **Top-K concordance**: Do shared chunks have the same top-1/3 successors?
- **NL baselines**: Same tests for NL characters and syllables (8 texts)
- **Permutation null**: Within each type, shuffle position labels (100 trials)
- **Bonferroni correction** at α=0.05 → significance threshold |z| > 2.73

**Critical confound**: Successor of I-chunk is at M position; successor of
M-chunk is at later-M or F. Different inventories → JSD > 0 is **expected**
even for identical units. NL baselines are the primary control.

### Data availability

| Corpus | ≥3-unit words | Shared types (suc) | Shared types (pre) |
|--------|--------------|-------------------|-------------------|
| VMS chunks | 6,972 (17.3%) | 64 | 69 |
| NL chars (mean) | ~80% | ~25 | ~25 |
| NL syls (mean) | ~17% | ~47 | ~47 |

**Sparsity warning**: 40/64 VMS shared types have <20 tokens at one position.
This inflates mean JSD. Permutation null controls for sampling noise.

### Results — Summary table

| Metric | VMS | NL-char μ | z(char) | NL-syl μ | z(syl) |
|--------|-----|-----------|---------|----------|--------|
| Suc JSD mean (I vs M) | **0.653** | 0.325 | **+6.16** | 0.947 | **-10.65** |
| Suc JSD weighted | **0.513** | 0.326 | **+3.51** | 0.935 | **-12.81** |
| Pre JSD mean (M vs F) | **0.612** | 0.343 | **+3.79** | 0.917 | **-7.39** |
| Pre JSD weighted | **0.496** | 0.271 | **+5.91** | 0.902 | **-9.21** |
| CMI (successor) | **0.347** bits | 0.176 | **+4.74** | 0.647 | **-12.92** |
| Top-1 concordance | **4.7%** | 24.1% | -2.31 | 1.6% | +1.18 |

**Directional evidence (Bonferroni |z| > 2.73):**
- vs NL characters: **5 CIPHER**, 0 NL, 1 ambiguous
- vs NL syllables: **0 CIPHER**, 5 NL, 1 ambiguous

### Key finding: VMS falls BETWEEN characters and syllables

VMS successor JSD = 0.653 lies between NL characters (0.325) and NL syllables
(0.947). The interpolation position: **53% from characters toward syllables**.

This is expected from the inventory-overlap confound:
- NL chars: J(I,F) = 0.80 (high overlap → small confound → low JSD 0.33)
- VMS chunks: J(I,F) = 0.24 (low overlap → moderate confound → JSD 0.65)
- NL syls: J(I,F) = 0.07 (very low overlap → massive confound → JSD 0.95)

VMS's context divergence is **proportional to its inventory overlap**, not
anomalously high. A simple linear model predicts JSD ≈ 0.81 from VMS's J=0.24;
the observed 0.65 is actually BELOW this prediction.

### Permutation null model

| Test | Observed | Null μ ± σ | z |
|------|----------|-----------|---|
| Successor JSD | 0.653 | 0.421 ± 0.010 | **+23.97** |
| Predecessor JSD | 0.612 | 0.407 ± 0.011 | **+18.80** |

Context divergence is overwhelmingly above sampling noise. But this does NOT
distinguish genuine homography from the inventory confound. Only the NL
baseline comparison does that.

### Robustness check (≥2-chunk words)

With ≥2-chunk words (99 shared types, more data):
- Successor JSD mean = **0.433** (drops from 0.653)
- Predecessor JSD mean = **0.460** (drops from 0.612)

The drop confirms the ≥3-chunk sparsity inflates means. With better data,
VMS JSD approaches NL character range even more closely.

### Skepticism and limitations

1. **Sparsity**: 40/64 types have <20 tokens at one position. Well-sampled
   types (k, d, o.l, a.l, etc.) have JSD 0.22–0.53, closer to NL chars.
2. **Inventory confound**: The dominant effect. Successors at I draw from
   M-inventory; at M from M/F-inventory. Different inventories → JSD > 0
   mechanically. This explains most or all of VMS's excess over NL chars.
3. **Word-length asymmetry**: VMS ≥3-chunk words are 80% 3-chunk (one M
   each). NL ≥3-char words are typically 4-8 chars with many M positions.
4. **LOOP grammar**: Slot structure constrains which chunks start which
   positions, creating implicit context patterns.
5. **NL syllabification**: ~87% accuracy. Errors add noise → NL syl JSD
   is conservative (errors are position-random).
6. **Multiple testing**: 8 hypothesis tests; Bonferroni at |z| > 2.73.

### Critical audit: Bug caught and fixed

**The original verdict code had a critical bug** that would have classified
VMS as "CIPHER_SUPPORTED" (reporting shared chunks show more divergence
than both NL chars AND syllables). In fact, VMS shows MORE than chars but
LESS than syllables — placing it between the two, not above both. The bug
was caught during the skeptical audit phase and fixed before reporting.

### Verdict

**CONTEXT_DIVERGENCE_BETWEEN_CHAR_AND_SYL**: VMS shared chunks show
context divergence consistent with NL sub-word units having moderate positional
constraints. The excess over NL characters is explained by the inventory
confound (VMS J(I,F)=0.24 vs NL char J(I,F)=0.80). No evidence for
homography beyond what natural positional phonotactics predict.

**Phase 88 recontextualized**: The positional encoding from Phase 88 is
real (permutation null z=+24), but shared chunks that do appear at multiple
positions behave as the **same** unit, not as positional homographs. The
positional structure is one of **inventory partitioning** (different positions
use different chunk sets) rather than **identity splitting** (same-looking
chunks meaning different things).

**REVISED CONFIDENCES (Phase 89):**
- Natural language: **87% (unchanged)** — result is NL-consistent
- Chunks = functional characters: **85% (unchanged)**
- True alphabet ≈ 25: **70% (unchanged)**
- h_char anomaly resolved: **75% (unchanged)**
- Positional verbose cipher: **55% → 50% (DOWN)** — context divergence of
  shared chunks is within NL sub-word range, not anomalous. Shared chunks
  are NOT homographs.
- Hoax/random: **<1% (unchanged)**


---

## Phase 90 — Cross-Word Chunk Dependencies (MI at Word Boundaries)

**Date**: 2025-07-18
**Script**: `scripts/phase90_crossword_chunk_mi.py`
**Results**: `results/phase90_crossword_chunk_mi.json`

### Question

Does the glyph-level cross-word MI anomaly (Phase 62: NMI(last→next\_init)
= 0.080, z=313, 1.82× Italian) persist, strengthen, or vanish at the
chunk level?

### Motivation

Phase 62 found that VMS glyphs show anomalously strong inter-word
dependency: the last glyph of word N predicts the first glyph of word N+1
much more strongly than in any NL reference text. The TMA paradox (Phase
84: VMS TMA=0.123, 1.9× NL mean) reinforced this: VMS has more inter-word
structure than NL.

But Phases 85-89 showed that individual VMS glyphs are NOT the functional
unit — LOOP grammar chunks are. The glyph-level anomaly may therefore be a
**grain-size artifact**: sub-unit glyphs carry intra-chunk correlations that
inflate inter-word MI spuriously.

### Approach

1. Parse VMS preserving **line order** (cross-line pairs excluded)
2. For each consecutive same-line word pair: F-chunk of word N → I-chunk
   of word N+1 (cross-word pairs) and consecutive chunks within each word
   (within-word pairs)
3. Compute MI, NMI, H(Y|X), and boundary attenuation ratio (cross/within)
4. Same metrics for NL **characters** and NL **syllables** (8 reference texts)
5. Permutation null: shuffle word order within each line (100 trials)
6. Section-level breakdown and robustness checks

### Critical confounds addressed

1. **Inventory confound**: F-chunks and I-chunks draw from different type
   sets (Phase 88: J(I,F)=0.241). Even randomly paired words produce MI > 0
   from marginal frequency correlation. **Controlled by**: word-order shuffle
   null model — marginals are preserved, only order is destroyed.
2. **Grain-size effect**: Chunks are coarser than glyphs → raw MI scales
   differently. **Controlled by**: NMI normalization and by comparing to NL
   syllables (same grain level).
3. **Pseudo-line confound**: NL texts lack line boundaries; fixed-length
   pseudo-lines used (7 words, matching VMS mean of 7.1 words/line).
   Sensitivity tested at lengths 5, 8, 15, 50 — stable (max Δ = 0.07 bits).
4. **1-chunk word ambiguity**: 10,030 VMS words (24.9%) are single-chunk,
   making their F-chunk = I-chunk = the whole word. These are excluded from
   the primary cross-word analysis and analyzed separately.

### VMS corpus statistics

| Metric | Value |
|--------|-------|
| Lines parsed | 5,691 |
| Words | 40,272 |
| Chunk tokens | 80,046 |
| 1-chunk words | 10,030 (24.9%) |
| 2-chunk words | 22,790 (56.6%) |
| Cross-word pairs (≥2-chunk words) | 25,508 |
| Within-word consecutive pairs | 39,774 |

### Core results

| Pair type | MI (bits) | NMI | H(Y) bits | H(Y\|X) bits | H(Y) reduction |
|-----------|----------|------|-----------|-------------|---------------|
| **Cross-word** (≥2-chunk, F→I) | 0.782 | 0.147 | 6.08 | 5.30 | 12.9% |
| **Within-word** (consecutive) | 1.166 | 0.203 | 5.81 | 4.65 | 20.1% |
| **Boundary attenuation ratio** | **0.671** | **0.727** | — | — | — |
| Cross-word (1-chunk only) | 1.737 | 0.287 | — | — | — |

**Boundary attenuation**: Word boundaries reduce chunk MI by ~33% (ratio
0.67). This is a "moderate boundary" effect — word boundaries attenuate
but do not abolish inter-chunk dependency.

**1-chunk words** show substantially higher cross-word MI (1.74 vs 0.78),
consistent with single-chunk words being function words that strongly
predict what follows.

### Permutation null model (100 trials, word-order shuffle)

| Metric | Observed | Null mean ± σ | z-score |
|--------|----------|---------------|---------|
| Cross MI | 0.782 | 0.566 ± 0.005 | **+44.66** |
| Cross NMI | 0.147 | 0.106 ± 0.001 | **+45.81** |

**Genuine cross-word dependency confirmed**: z = +44.66 far exceeds any
significance threshold. Word order matters — the MI is not just from
marginal frequency correlation.

However, 72% of observed MI (0.566 / 0.782) is explained by marginal
frequency correlation alone. Only 28% (0.216 bits) is genuine word-order
dependency. This proportion matches NL exactly: Latin-Caesar syllables show
29% genuine excess (0.590 / 2.050).

### NL baselines — character level

| System | Cross MI | Cross NMI | Within MI | Ratio | H(Y) red. |
|--------|---------|-----------|----------|-------|-----------|
| **VMS chunks** | **0.782** | **0.147** | **1.166** | **0.671** | **12.9%** |
| English-Cury | 0.147 | 0.039 | 0.865 | 0.169 | 3.4% |
| French-Viandier | 0.144 | 0.047 | 0.916 | 0.157 | 3.7% |
| German-BvgS | 0.182 | 0.053 | 0.985 | 0.185 | 4.4% |
| Italian-Cucina | 0.113 | 0.040 | 0.813 | 0.139 | 2.8% |
| Latin-Caesar | 0.070 | 0.019 | 0.869 | 0.081 | 1.8% |
| Latin-Vulgate | 0.057 | 0.016 | 0.861 | 0.066 | 1.4% |
| **NL char mean** | **0.110** | **0.033** | **0.887** | **0.124** | **2.7%** |

VMS is 5–7× above every NL character baseline. All z-scores vs chars are
highly significant (z = +3.9 to +16.1). **VMS chunks are definitively not
characters** — the cross-word structure is far too rich.

### NL baselines — syllable level

| System | Cross MI | Cross NMI | Within MI | Ratio | H(Y) red. |
|--------|---------|-----------|----------|-------|-----------|
| **VMS chunks** | **0.782** | **0.147** | **1.166** | **0.671** | **12.9%** |
| English-Cury | 3.597 | 0.485 | 5.260 | 0.684 | 48.5% |
| French-Viandier | 2.992 | 0.454 | 5.354 | 0.559 | 45.4% |
| German-BvgS | 4.073 | 0.594 | 5.413 | 0.753 | 59.4% |
| Italian-Cucina | 2.034 | 0.300 | 3.867 | 0.526 | 30.0% |
| Latin-Caesar | 2.050 | 0.290 | 4.960 | 0.413 | 29.0% |
| Latin-Vulgate | 2.461 | 0.342 | 4.880 | 0.504 | 34.2% |
| **NL syl mean** | **3.044** | **0.427** | **5.038** | **0.598** | **42.7%** |

VMS raw Cross MI & NMI are below NL syllable baselines (z ≈ -2.8). But the
**boundary attenuation ratio** (0.671 vs NL mean 0.598) is NOT significantly
different (z = +0.64). The proportion of within-word MI that crosses word
boundaries is **normal** for sub-word units.

### Z-score summary (Bonferroni threshold |z| > 2.81 for 10 tests)

| Metric | VMS | z vs char | z vs syl |
|--------|-----|-----------|----------|
| Cross MI | 0.782 | **+16.09** | -2.85 |
| Cross NMI | 0.147 | **+8.84** | -2.69 |
| Within MI | 1.166 | **+3.90** | -7.77 |
| Ratio (cross/within) | 0.671 | **+12.51** | +0.64 |
| H(Y) reduction | 12.9% | **+10.14** | -2.87 |

- vs NL chars: 5/5 metrics significantly ABOVE → chunks ≠ characters
- vs NL syls: 3/5 below (Cross MI, Cross NMI, H(Y) red.), 1 N/S (ratio),
  1 below (within MI, but this measures within-word, not cross-word)

### Phase 62 anomaly inversion — KEY FINDING

| Level | VMS NMI | Italian NMI | VMS/Italian ratio |
|-------|---------|-------------|-------------------|
| **Glyph** (Phase 62) | 0.080 | 0.044 | **1.82×** (anomalous) |
| **Chunk** (Phase 90) | 0.147 | 0.300 | **0.49×** (normal/low) |

The glyph-level anomaly (VMS = 1.82× Italian) **inverts** at chunk level
(VMS = 0.49× Italian syllables). This is strong evidence that the Phase 62
finding was a **unit-of-analysis artifact**: VMS glyphs are sub-chunk units,
and intra-chunk glyph correlations inflated the apparent cross-word MI.

At the correct functional grain, VMS cross-word dependency is LOWER than NL,
not higher. The TMA paradox (Phase 84) may need similar re-evaluation at
chunk level.

### Section-level breakdown

| Section | N pairs | MI | NMI | H(Y) red. |
|---------|---------|-----|------|-----------|
| text | 12,994 | 0.894 | 0.172 | 14.9% |
| herbal-A | 6,408 | 1.186 | 0.223 | 19.5% |
| bio | 3,855 | 0.924 | 0.204 | 17.6% |
| pharma | 921 | 2.000 | 0.407 | 35.0% |
| cosmo | 575 | 2.532 | 0.504 | 46.4% |

**Caution**: Small sections (pharma, cosmo) show very high MI, but with
< 1,000 pairs and hundreds of chunk types, MI estimation has substantial
upward bias from sparse data. These values should NOT be interpreted at
face value.

### MI concentration

Top-20 cross-word bigrams account for only **10.0%** of total MI. The
cross-word dependency is **broadly distributed** across hundreds of
bigram pairs — not driven by a handful of formulaic collocations. This is
consistent with genuine language-like dependency rather than a few repeated
patterns.

### Skeptical audit notes

1. **Verdict sensitivity**: The automated verdict "BELOW\_NL" was triggered
   by mean z = -3.11 across all 5 metrics vs syllables. However, this mean
   includes "Within MI" (z = -7.77), which measures a different phenomenon
   (within-word chunk dependency is lower because VMS chunks have lower
   absolute entropy than NL syllables — H(Y) 6.08 vs 6.8–7.4 bits). If
   restricted to the 4 cross-word-specific metrics, the mean z = -1.94,
   which would yield "NL\_SYLLABLE\_CONSISTENT" instead of "BELOW\_NL".
   **Honest interpretation**: VMS is borderline between "consistent" and
   "slightly below" NL syllables; the ratio (cleanest metric) is firmly
   normal.

2. **Genuine excess proportion**: VMS shows 28% genuine excess (word-order
   MI above marginal-frequency baseline). This matches NL exactly (Caesar
   syllables: 29%). This is perhaps the single most informative comparison:
   the fraction of cross-word structure that is "real" (from syntax/ordering)
   vs "mechanical" (from inventory overlap) is indistinguishable from NL.

3. **H(Y) entropy gap**: VMS I-chunks H(Y) = 6.08 bits vs NL syllable
   H(Y) ≈ 6.8–7.4 bits. This 1-bit gap partly explains why raw MI is
   lower. NMI partially corrects for this but is not perfect.

4. **Pseudo-line stability**: NL syllable MI is nearly invariant to
   pseudo-line length (5→50 words: 2.08→2.01 bits, Δ = 3.4%). Results are
   not artifacts of the pseudo-line segmentation.

### Verdict

**CROSS\_WORD\_MI\_BELOW\_NL** (with important nuance): VMS cross-word
chunk MI is genuine (z=+44.66 vs shuffle) but falls slightly below NL
syllable baselines in absolute terms. The boundary attenuation ratio is
normal (z=+0.64), and the genuine excess proportion (28%) matches NL
exactly (29%). The Phase 62 glyph-level anomaly is a unit-of-analysis
artifact that inverts at chunk level.

**KEY IMPLICATIONS**:
- The glyph-level cross-word anomaly (Phase 62) is **resolved**: it was
  caused by measuring at the wrong grain (sub-chunk glyphs carry intra-chunk
  correlations that leak across word boundaries)
- VMS word boundaries behave like **real word boundaries**: they attenuate
  sub-word dependency by the same fraction as in NL
- Cross-word structure is broadly distributed, not formulaic
- The lower H(Y) of VMS chunks (vs NL syllables) suggests either a smaller
  effective vocabulary or information compression in the encoding

**REVISED CONFIDENCES (Phase 90):**
- Natural language: **87% → 89% (UP)** — word-boundary behavior is NL-normal;
  glyph-level anomaly resolved as grain artifact
- Chunks = functional characters: **85% (unchanged)**
- True alphabet ≈ 25: **70% (unchanged)**
- h\_char anomaly resolved: **75% → 78% (UP)** — Phase 62 anomaly now also
  explained as grain artifact
- Positional verbose cipher: **50% → 45% (DOWN)** — no cross-boundary
  anomaly to support sub-word cipher mechanism
- Hoax/random: **<1% (unchanged)**

---

## Phase 91 — Zodiac Galenic Axis Test

**Question**: Do EVA 'a' and 'e' frequencies in zodiac nymph labels show
an inverse seasonal pattern across the 12 zodiac signs, as claimed by a
Voynich Ninja poster (thread 4536)?

**Provenance**: A post from April 2026 proposes that nymph labels encode
Galenic medical treatment schedules — 'e' tracks thermal (Cold) demand
(peaks summer), 'a' tracks moisture (Dry) demand (peaks winter), forming
an inverse pair under "Contraria contrariis curantur."

### Data

- **299 nymph labels** across 12 sign-halves (10 merged signs), totalling
  1,946 glyphs
- Labels parsed from ZL transcription `@Lz`/`&Lz` markers
- Signs ordered by tropical zodiac: Aries(1)→Sagittarius(9), then
  Pisces(12) — Capricorn and Aquarius are missing from VMS

### Per-sign glyph frequencies

| Sign | Ord | Labels | Glyphs | a% | e% | a/e ratio |
|---|---|---|---|---|---|---|
| Aries | 1 | 30 | 254 | 17.3% | 7.1% | 2.44 |
| Taurus | 2 | 30 | 243 | 20.2% | 1.2% | 16.33 |
| Gemini | 3 | 29 | 172 | 20.9% | 3.5% | 6.00 |
| Cancer | 4 | 30 | 247 | 17.0% | 7.7% | 2.21 |
| Leo | 5 | 30 | 183 | 10.4% | 13.7% | 0.76 |
| Virgo | 6 | 30 | 196 | 7.7% | 16.8% | 0.45 |
| Libra | 7 | 30 | 157 | 4.5% | 19.7% | 0.23 |
| Scorpio | 8 | 30 | 164 | 6.1% | 18.9% | 0.32 |
| Sagittarius | 9 | 30 | 158 | 5.1% | 20.9% | 0.24 |
| Pisces | 12 | 30 | 172 | 19.8% | 2.3% | 8.50 |

The a/e ratio swings from 16.3 (Taurus) to 0.23 (Libra) — a 70× range.

### Correlation results

| Test | Value |
|---|---|
| Pearson r(a%, e%) | **-0.9904** |
| Permutation p (10,000 shuffles, two-tailed) | **< 0.001** (0 of 10,000 matched) |
| r(ordinal, a%) | -0.4113 |
| r(ordinal, e%) | +0.3737 |

The inverse correlation is near-perfect. In 10,000 random shuffles of sign
labels, zero produced a correlation as extreme as the observed -0.99.

### SLOT2 competition artifact check

In LOOP grammar, both 'a' and 'e' fill SLOT2 (front vowel position). They
are structural alternatives — more 'a' in a label mechanically means fewer
'e'. To check whether the extreme r = -0.99 is a compositional tautology:

- Computed ALL 190 pairwise glyph correlations across 10 signs
- **a/e is #1 most negative** — the single most extreme anti-correlation
- Only 2 of 190 pairs have r < -0.9 (a/e at -0.990, a/y at -0.903)
- If compositional pressure were the cause, many pairs would show
  similar extremes. They do not.

**Conclusion**: a/e is uniquely extreme. Not a generic compositional artifact.

### Ring text control

Ring text (circular running text on the same zodiac folios) also shows
a/e anti-correlation, but much weaker:

| Text type | r(a%, e%) |
|---|---|
| Nymph labels | **-0.9904** |
| Ring text (same folios) | **-0.7271** |
| Non-zodiac VMS | (not decomposed by section) |

Labels AMPLIFY the a/e opposition relative to ring text. Per-sign comparison
shows labels are enriched in 'a' by +8–11pp for spring signs and depleted
by -3 to -9pp for autumn signs, with mirror-image shifts in 'e'.

### Label vs non-zodiac vocabulary

| Glyph | Zodiac labels | Non-zodiac VMS | Δ |
|---|---|---|---|
| a | 13.6% | 7.7% | +5.9pp |
| e | 10.4% | 10.4% | 0.0pp |
| i | 4.5% | 6.4% | -1.8pp |
| o | 17.6% | 13.1% | +4.5pp |

Zodiac labels are substantially richer in 'a' and 'o', and poorer in 'i',
than the VMS corpus average.

### Seasonal direction mismatch

The Galenic claim predicts: a% peaks in **winter** (dry treatment for wet
season), e% peaks in **summer** (cold treatment for hot season).

The data shows: a% peaks in **spring** (Pisces–Gemini), e% peaks in
**autumn** (Leo–Sagittarius). The phase is shifted by ~1 season.

However, linear correlation with ordinal is a poor model for cyclic data
(Pisces at ordinal 12 wraps to before Aries at ordinal 1). The actual
structure is a "spring hemisphere" (a-dominant) vs "autumn hemisphere"
(e-dominant) with Cancer/Leo as the transition point.

### I-run analysis (dain/daiin/daiiin hypothesis)

The claim that i-run length encodes degrees of treatment is not supported.
i-runs are sparse per sign (0–16 total runs across 30 labels), and mean
run lengths show no systematic seasonal pattern (range: 1.00–2.00, but
counts are too small for meaningful inference).

### Skeptical audit

1. **POST-HOC**: The hypothesis was generated from the same data we're
   testing. True confirmation requires prediction on unseen data.

2. **SAMPLE SIZE**: 299 labels, 10 zodiac signs (8 df). The extreme r is
   real but based on only 10 data points.

3. **VOCABULARY STRATIFICATION**: The most parsimonious explanation is
   that spring signs use 'ot-a' type words (e.g., "otalar", "otaral",
   "otalchytaramdy") while autumn signs use 'oe-e' type words (e.g.,
   "oeedey", "oeeodaiin", "oeeoty"). This is label vocabulary selection,
   not necessarily Galenic encoding.

4. **RING TEXT ALSO ANTI-CORRELATES**: r = -0.73 in ring text means the
   phenomenon is not exclusively label-specific. It is AMPLIFIED in labels
   but present throughout the zodiac folios.

5. **SEASONAL PHASE SHIFT**: The claim's season-to-axis mapping does not
   match the data. This is the strongest evidence against the specific
   Galenic interpretation.

### Verdict

**INVERSE\_REAL\_GALENIC\_UNCONFIRMED**: The a/e inverse correlation across
zodiac signs is real (r = -0.99, p < 0.001), statistically significant
beyond any reasonable doubt, uniquely extreme among all glyph pairs (#1 of
190), and amplified in labels relative to ring text. However:

- The seasonal direction is **shifted** from the Galenic prediction
- The link to Galenic medicine specifically cannot be established from
  frequency data alone
- Vocabulary stratification is an equally valid (and more parsimonious)
  explanation
- The pattern in ring text (r = -0.73) means it is not exclusively a
  label phenomenon

The a/e axis is the strongest section-level glyph pattern found in 91
phases of analysis. It demands explanation but does not confirm the specific
Galenic interpretation.

**REVISED CONFIDENCES (Phase 91):**
- Natural language: **89% (unchanged)** — pattern may be linguistic
  (vocabulary selection per topic/sign)
- Chunks = functional characters: **85% (unchanged)**
- True alphabet ≈ 25: **70% (unchanged)**
- h\_char anomaly resolved: **78% (unchanged)**
- Positional verbose cipher: **45% (unchanged)**
- Systematic a/e axis in zodiac labels: **NEW — 80%** (pattern is real)
- Galenic medical encoding: **NEW — 10%** (unconfirmed interpretation)
- Hoax/random: **<1% (unchanged)**

---

## Phase 92 — a↔e Minimal Pair & Substitution Analysis

**Question**: Is the extreme zodiac a/e inverse (Phase 91: r = -0.990)
caused by PARAMETRIC SUBSTITUTION (same word frames, a↔e swapped) or
VOCABULARY STRATIFICATION (entirely different word types per sign)?

**Why this matters**: The answer determines whether the a/e pattern is
evidence for a cipher parameter or a natural-language property.

### Key findings

**1. ZERO cross-hemisphere a↔e minimal pairs**

Of 101 a↔e minimal pairs in the full VMS corpus, not a single pair has
one variant in spring zodiac labels and the other in autumn. The
"parametric substitution" hypothesis — same word frame with a↔e flipped
— is dead.

**2. Massive vocabulary stratification**

| Metric | Value |
|---|---|
| Spring label word types | 162 |
| Autumn label word types | 136 |
| Overlap (shared types) | 17 |
| Jaccard similarity | 0.060 |
| Shared word frames (SLOT2 → \_) | 19 / 268 (7.1%) |
| Stratification quotient | 0.825 |

Spring and autumn signs use 83% different vocabulary. Jaccard overlap
is only 6%.

**3. SLOT2 fully explains the Phase 91 pattern**

| Sign | S2 total | S2 'a' ct | S2 'e' ct | a-fraction |
|---|---|---|---|---|
| Aries | 60 | 44 | 16 | 73.3% |
| Taurus | 51 | 49 | 2 | 96.1% |
| Gemini | 40 | 36 | 4 | 90.0% |
| Cancer | 52 | 42 | 10 | 80.8% |
| Leo | 35 | 19 | 16 | 54.3% |
| Virgo | 41 | 15 | 26 | 36.6% |
| Libra | 26 | 7 | 19 | 26.9% |
| Scorpio | 30 | 10 | 20 | 33.3% |
| Sagittarius | 30 | 8 | 21 | 26.7% |
| Pisces | 37 | 34 | 3 | 91.9% |

r(SLOT2-a-frac, SLOT2-e-frac) = **-0.9994**. The Phase 91 glyph-level
pattern is entirely a SLOT2 phenomenon.

**4. SLOT2 filler distribution by hemisphere**

| Filler | Spring ct | Spring % | Autumn ct | Autumn % |
|---|---|---|---|---|
| a | 205 | 85.4% | 59 | 36.4% |
| e | 23 | 9.6% | 56 | 34.6% |
| ee | 9 | 3.8% | 41 | 25.3% |
| eee | 3 | 1.2% | 5 | 3.1% |

Spring labels fill SLOT2 with 'a' 85% of the time. Autumn labels split
60/37 between 'e'/'ee' and 'a'.

**5. NL baseline — vowel minimal pairs**

| Corpus | Types | a/e pairs | a/e per 1K types |
|---|---|---|---|
| VMS (EVA glyphs) | 8,188 | 101 | 12.3 |
| Italian (cucina) | 5,185 | 237 | 45.7 |
| Latin (Caesar) | 9,657 | 74 | 7.7 |
| Latin (Galen) | 9,745 | 175 | 18.0 |

VMS a/e minimal pair rate (12.3 per 1K types) falls within the NL range
(7.7–45.7). Nothing anomalous.

### Interpretation

The combined Phase 91 + 92 picture:
- Phase 91: a% and e% are almost perfectly anti-correlated across zodiac
  signs (r = -0.99)
- Phase 92: This arises from **different word types** per sign, NOT from
  the same words with a↔e swapped
- The different word types differ specifically at **SLOT2** (front vowel)
- Spring signs use an a-SLOT2 vocabulary: "otalar", "otaral", "okaram"
- Autumn signs use an e-SLOT2 vocabulary: "oeedey", "oeeoty", "oteoly"

This is vocabulary stratification: different zodiac signs draw from
different word pools, and those pools happen to be distinguished by their
SLOT2 front-vowel content. In natural language, this would correspond to
topic-specific vocabulary (botanical terms for spring plants vs autumn
plants, different ailment terminology, etc.).

### What this rules out

1. **Parametric substitution cipher**: No evidence. Zero a↔e minimal
   pairs cross hemispheres.
2. **Galenic encoding via a↔e switching**: No evidence. The glyphs don't
   switch — the whole words are different.
3. **SLOT2 as a tunable cipher parameter**: Not supported. SLOT2 varies
   because the words are different, not because a parameter is being set.

### What remains possible

1. **NL vocabulary stratification** — The simplest explanation. Different
   signs discuss different subjects using different words.
2. **Constructed vocabulary** — The word pools could be intentionally
   designed with SLOT2 as a distinguishing feature, but this requires
   a more complex hypothesis with no additional evidence.
3. **Morphological variation** — Spring-sign words may share a morphological
   pattern (e.g., 'a'-containing stems) distinct from autumn-sign words.

### Verdict

**VOCABULARY\_STRATIFICATION**: The zodiac a/e inverse is real and entirely
localized to SLOT2, but it arises from different word types per sign —
not parametric substitution. This is consistent with natural language where
different topics use different vocabulary.

**REVISED CONFIDENCES (Phase 92):**
- Natural language: **89% → 91% (UP)** — vocabulary stratification is
  normal in topical NL text
- Chunks = functional characters: **85% (unchanged)**
- True alphabet ≈ 25: **70% (unchanged)**
- h\_char anomaly resolved: **78% (unchanged)**
- Positional verbose cipher: **45% → 40% (DOWN)** — no parametric
  substitution evidence
- Systematic a/e axis in zodiac: **80% (unchanged)** — pattern is real
  but linguistic
- Galenic medical encoding: **10% → 5% (DOWN)** — no substitution mechanism
- Hoax/random: **<1% (unchanged)**

---

## Phase 93 — Currier A/B as SLOT2 Regime

### Question

Phase 92 found that zodiac labels split into spring/autumn hemispheres
via SLOT2 content alone (r = -0.9994). The Currier A/B distinction
(1976) is the most replicated structural finding in VMS studies.
**Does SLOT2 a-fraction explain the manuscript-wide Currier A/B split?**
If yes, "two languages" reduce to one grammar parameter.

### Method

1. Parsed Currier A/B labels from folio file headers (not hardcoded).
2. Loaded all 201 folios; filtered to 185 with ≥30 words and A/B label
   (107 A, 78 B; 16 unassigned including zodiac and cosmological).
3. Parsed every word → LOOP chunks; computed per-folio features:
   - SLOT2: a-frac, e-frac, q-frac, **empty-frac**
   - SLOT1: ch-frac, sh-frac, y-frac, empty-frac
   - SLOT5: y/l/r/s/n/k-frac, gallows-frac, empty-frac
   - Word-level: mean glyph length, mean chunks/word, gallows/word
4. For each of 19 features: Cohen's d, optimal threshold accuracy,
   10,000-permutation significance test.
5. Residual test: after removing all SLOT2 features, how well do
   remaining features classify A vs B?
6. Within-herbal control (same section, both A and B folios).
7. Bimodality test: gap/SD separation ratio.
8. Cross-correlation matrix of top 6 features.

### Results

**Feature ranking by A/B classification accuracy:**

| Feature | Mean A | Mean B | Cohen's d | Accuracy | perm-p |
|---|---|---|---|---|---|
| s2\_empty\_frac | 0.685 | 0.482 | +2.39 | **90.8%** | <0.0001 |
| s5\_empty\_frac | 0.239 | 0.158 | +1.79 | **84.9%** | <0.0001 |
| s2\_e\_frac | 0.109 | 0.228 | -1.57 | 80.0% | <0.0001 |
| s5\_gallows\_frac | 0.050 | 0.022 | +1.27 | 77.8% | <0.0001 |
| gallows\_per\_word | 0.098 | 0.042 | +1.25 | 77.8% | <0.0001 |
| s5\_y\_frac | 0.127 | 0.200 | -1.42 | 77.3% | — |
| s5\_k\_frac | 0.101 | 0.154 | -1.43 | 76.2% | — |
| s2\_a\_frac | 0.155 | 0.206 | -0.94 | 71.9% | — |

**Key finding 1: The hypothesis was WRONG — s2\_a\_frac is a weak predictor.**
`s2_a_frac` classifies A/B at only 71.9% (d = -0.94). Currier A folios
actually have LOWER a-fraction (15.5%) than B (20.6%). This is the
OPPOSITE direction from what the zodiac analogy predicted.

**Key finding 2: SLOT2 EMPTINESS, not a-frac, is the top feature.**
`s2_empty_frac` achieves 90.8% accuracy (d = +2.39, p < 0.0001).
Currier A chunks leave SLOT2 unfilled 68.5% of the time; B only 48.2%.
B words systematically have MORE front-vowel material.

**Key finding 3: Multiple features separate A/B — MULTI\_FEATURE pattern.**
After removing ALL SLOT2 features, `s5_empty_frac` alone achieves 84.9%.
The accuracy drop from removing SLOT2 is only 5.9 percentage points.
Currier A/B is a multi-slot structural difference, not a single-parameter
switch.

**Key finding 4: The structural signature is SLOT FILLING DENSITY.**
Currier B words are FULLER — more LOOP slots filled per chunk:
- SLOT2 filled: B 51.8% vs A 31.5% (more front vowels)
- SLOT5 filled: B 84.2% vs A 76.1% (more codas)
- B prefers 'e' in SLOT2, 'y'/'k' in SLOT5
- A has 2.3× more gallows per word than B

**Key finding 5: Zodiac pattern does NOT generalize.**
Zodiac labels: a-frac gap = ~50pp (spring 85%, autumn 35%).
Manuscript-wide A vs B: a-frac gap = only 5.2pp (15.5% vs 20.6%).
The zodiac SLOT2 pattern is a local phenomenon, not the Currier mechanism.

**Key finding 6: Section doesn't explain it fully.**
Within herbal section only (88 A, 28 B folios):
- Cohen's d = -0.887, threshold accuracy = 78.4%.
- A herbal: mean s2a = 15.6%, B herbal: mean s2a = 20.8%.
- The A/B difference persists after controlling for section.

**Bimodality: Distribution is overlapping, not bimodal.**
- Separation ratio (gap/pooled SD) = 0.94 — below 1.0.
- No clean split; A and B distributions overlap heavily.
- This argues against a clean "switch" model and favors a gradient.

**Cross-correlation of top features:**

| | s2\_empty | s5\_empty | s2\_e | s5\_gallows |
|---|---|---|---|---|
| s2\_empty | 1.000 | +0.648 | -0.849 | +0.397 |
| s5\_empty | +0.648 | 1.000 | -0.495 | +0.306 |
| s2\_e | -0.849 | -0.495 | 1.000 | -0.260 |
| s5\_gallows | +0.397 | +0.306 | -0.260 | 1.000 |

s2\_empty and s5\_empty are correlated (r = 0.648) but not redundant —
at least TWO independent structural dimensions distinguish A from B:
front-vowel filling and coda material.

### Interpretation

The Currier A/B distinction is NOT a single SLOT2 parameter switch.
It's a **multi-slot density difference**: B text fills more LOOP
grammar slots per chunk than A text. This is consistent with:

1. **Different NL registers** — elaborate B (pharmaceutical recipes with
   more qualifying vocabulary) vs terse A (herbal labels/descriptions).
2. **Different scribal spelling conventions** — one hand uses more
   vowel markers, the other more abbreviated forms.
3. **The distinction may reduce to "verbose vs sparse" encoding** —
   if the VMS uses a positional cipher, B might use more null/filler
   glyphs per encoded character.

The zodiac SLOT2 pattern (Phase 91/92) is a SEPARATE phenomenon from
Currier A/B. The zodiac pattern is about WHICH filler ('a' vs 'e')
appears at SLOT2; the Currier pattern is about WHETHER SLOT2 gets
filled at all.

### Skepticism

- **Optimal threshold accuracy is best-case.** Real out-of-sample
  performance would be lower (likely ~80-85% for s2\_empty).
- **Currier labels are 1970s assignments, not ground truth.** Some folios
  are disputed. If labels have noise, true separation is even stronger.
- **SLOT2 emptiness is partly circular.** The LOOP grammar defines
  SLOT2 to be optional. Saying "A has more empty SLOT2" is equivalent
  to saying "A words start with fewer front vowels" — just restating
  the known A/B vocabulary difference in grammar terminology.
- **The 2.3× gallows difference suggests scribal hand variation.** Gallows
  (bench-type characters) are the most visually distinctive glyphs;
  different hands may use different gallows frequency.
- **Multiple correlated features don't mean multiple independent causes.**
  One underlying factor (verbose vs sparse) could produce all observed
  feature differences simultaneously.

### Verdict

**SLOT2\_CONTRIBUTES (verdict: MULTI\_FEATURE):** The Currier A/B
distinction is a genuine multi-slot structural difference in LOOP
grammar. SLOT2 emptiness is the strongest single predictor (90.8%)
but is NOT the sole mechanism — other slot features independently
achieve 84.9%. The "two languages" are more accurately described as
two SLOT DENSITY REGIMES: sparse-chunk (A) vs dense-chunk (B).

The zodiac a/e axis (Phase 91/92) is a different, localized phenomenon
that does not explain the manuscript-wide Currier A/B distinction.

**REVISED CONFIDENCES (Phase 93):**
- Natural language: **91% → 92% (UP)** — multi-feature A/B difference
  with gradient overlap is typical of NL register/topic variation
- Chunks = functional characters: **85% → 87% (UP)** — LOOP slots
  differentially fill across A/B, behaving like NL syllable structure
- True alphabet ≈ 25: **70% (unchanged)**
- h\_char anomaly resolved: **78% (unchanged)**
- Positional verbose cipher: **40% → 35% (DOWN)** — "dense vs sparse"
  could support verbose cipher, but multi-feature nature argues against
  single encoding parameter
- Systematic a/e zodiac axis: **80% → 75% (DOWN)** — does not generalize
  to manuscript-wide A/B
- Currier A/B = multi-slot density: **NEW 80%** — well-supported by data
- Galenic medical encoding: **5% (unchanged)**
- Hoax/random: **<1% (unchanged)**

---

## Phase 94 — SLOT2 e-Extension: Productive Morphology or Slot Independence?

### Question

Petrasti (Voynich Ninja thread-5216, Aug 2026) observed that many VMS
words come in base/extended pairs where 'e' is inserted before 'o':
`chor→cheor`, `daiin→deaiin`, `kor→keor`, `chol→cheol`.

In LOOP grammar terms, this is **SLOT2 filling**: `chor` = ch|∅|o|r,
`cheor` = ch|e|o|r. Phase 93 showed Currier A leaves SLOT2 empty 2×
more than B. Is this alternation **productive morphology** (NL) or
**independent slot filling** (cipher)?

### Method

1. Loaded 40,351 tokens (8,212 types) with per-word positional metadata
   (folio, Currier label, line position, paragraph start).
2. Identified 4,151 "base" word types (50.5% of all types) that have
   ≥1 chunk with empty SLOT2 + 'o' present.
3. For each base, generated the e-extended variant (insert 'e' at SLOT2)
   and checked if it exists in the corpus.
4. Anti-circularity test: compared SLOT2 insertion hit rate vs random
   glyph-position insertion hit rate.
5. Measured: frequency asymmetry, selectional restrictions by frequency
   bin, Currier A/B distribution, line position, folio co-occurrence.
6. Verified Petrasti's specific examples. NL Latin baseline comparison.

### Results

**Core finding: 9.1% pairing rate with strong selectional restrictions.**

Only 377/4,151 base words (9.1%) have an e-extended partner in the corpus.
For comparison, a-extension pairing rate is 0.1% (6 pairs). The e-extension
is overwhelmingly specific — not a general slot-filling pattern.

**Anti-circularity: 2.64× above random position insertion.**
Inserting 'e' at SLOT2 produces 380 hits vs 144 average for random glyph
positions. The effect is real but moderate — positions 2-3 in glyph sequence
are inherently high-hit positions.

**Frequency asymmetry: base > extended at 2.58:1.**
Out of 377 pairs: 201 have base more frequent, 78 have extended more
frequent, 98 are equal. Median log2(base/ext) = 0.42.

| Base | Freq | Extended | Freq | Ratio |
|---|---|---|---|---|
| chol | 400 | cheol | 178 | 2.2× |
| chor | 212 | cheor | 97 | 2.2× |
| shol | 180 | sheol | 119 | 1.5× |
| cho | 80 | cheo | 82 | 1.0× |
| sho | 118 | sheo | 50 | 2.4× |
| okol | 82 | okeol | 65 | 1.3× |
| chodaiin | 44 | cheodaiin | 13 | 3.4× |

**Selectional restrictions are frequency-dependent (NL-like):**

| Frequency bin | Base words | With e-partner | Rate |
|---|---|---|---|
| 1 | 2870 | 92 | 3.2% |
| 2–5 | 929 | 151 | 16.3% |
| 6–20 | 245 | 95 | 38.8% |
| 21–100 | 83 | 30 | 36.1% |
| 101+ | 24 | 9 | 37.5% |

This pattern matches NL expectations: rare words (hapax) don't appear
in enough variant forms to catch the partner. The plateau at ~37-39%
for freq ≥6 suggests a natural ceiling.

**Currier distribution: base forms massively enriched in A.**
- Base forms: A=56.6%, B=43.4% (vs corpus baseline A=31.5%, B=68.5%)
- Extended forms: A=47.4%, B=52.6%
- Base-form A enrichment: 1.80× above corpus rate
- The direction is correct (base→A, extended→B) but extended forms
  don't cross the corpus B-baseline because common words appear everywhere.

**Folio co-occurrence: 1.70× expected.**
91/377 pairs co-occur in at least one folio (24.1%). Under independence,
only 53.6 would be expected. The 70% excess supports a genuine
word-formation relationship.

**Petrasti verification: 7/8 specific examples confirmed.**
Only `dor→deor` fails ('deor' not in corpus). All 12/12 prefix forms
of 'daiin' exist: daiin(853), odaiin(70), qodaiin(52), chodaiin(44),
chedaiin(41), ydaiin(17), cheodaiin(13), oldaiin(11), todaiin(9),
sodaiin(5), tedaiin(3), deaiin(1).

**NL Latin baseline: VMS e-extension is 45× higher than Latin.**
Latin vowel-insertion pairing rate: 0.2-0.4%. VMS: 9.1%.
This EXCEEDS what normal European NL morphology produces. It suggests
either (a) an agglutinative/templatic language like Semitic root+pattern,
(b) a systematic encoding mechanism, or (c) a partly constructed language.

### Interpretation

Five of six morphological diagnostics point toward genuine NL-like
word formation:

| Diagnostic | NL prediction | Cipher prediction | Observed |
|---|---|---|---|
| Selectional restriction | Yes, <50% | No, >80% | **9.1% ✓ NL** |
| Frequency asymmetry | base > ext | no pattern | **2.58:1 ✓ NL** |
| Frequency-dependent rate | low freq → low rate | uniform | **3.2%→38.8% ✓ NL** |
| Currier distribution | base→A, ext→B | no pattern | **base 1.8× A ✓ NL** |
| Folio co-occurrence | >1.0× | ~1.0× | **1.70× ✓ NL** |
| Rate vs Latin | comparable | n/a | **45× Latin ✗ NL** |

The outlier is the rate: 9.1% is far above any European NL tested.
This doesn't falsify NL, but it constrains the LANGUAGE TYPE — if NL,
it's templatic/agglutinative, not inflectional-European.

The e-extension appears to be **the morphological mechanism behind
Phase 93's Currier density difference**: Currier B text uses more
e-extended forms (filled SLOT2), producing the "dense-chunk" pattern.
Currier A uses more bare base forms (empty SLOT2) = "sparse-chunk."

### Skepticism

- **LOOP grammar makes SLOT2 optional by design.** The 2.64× anti-
  circularity ratio is moderate, not overwhelming. Some pairing is
  baked into the grammar's structure.
- **Frequency asymmetry conflated with word length.** Shorter words
  (empty SLOT2) tend to be more frequent by Zipf regardless of
  morphological relationship. Must control for length.
- **The 45× Latin excess is a red flag.** European NL don't behave
  like this. Either we're not comparing like-for-like, or the VMS
  uses a non-European morphological system, or the e-extension is
  an encoding/cipher mechanism that mimics morphology.
- **Petrasti's prefix list overlaps with LOOP SLOT1 + multi-chunk
  prefixes.** The prefix system may be a separate structural level
  from e-extension, or they may be confounded.
- **Folio co-occurrence excess (1.70×) is modest.** Common words
  co-occur everywhere; controlling for frequency might eliminate
  the excess.

### Verdict

**PRODUCTIVE\_MORPHOLOGY (score 5/6):** The e-extension passes five
of six NL morphology diagnostics. It is selective (9.1%), frequency-
asymmetric (2.58:1 base>ext), frequency-dependent (3→39% by frequency
bin), Currier-distributed (base enriched 1.8× in A), and co-localized
(1.70× expected). The 45× Latin excess constrains the language type
to something more templatic than European inflectional languages.

This finding LINKS Phase 93 (Currier density) to a specific morphological
mechanism: e-extension at SLOT2 = the productive operation that creates
"dense" B-text from "sparse" A-text base forms.

**REVISED CONFIDENCES (Phase 94):**
- Natural language: **92% → 93% (UP)** — five NL diagnostics pass;
  the one failure constrains language type, not NL status
- Chunks = functional characters: **87% → 88% (UP)** — e-extension
  operates exactly at the LOOP SLOT2 boundary
- True alphabet ≈ 25: **70% (unchanged)**
- h\_char anomaly resolved: **78% (unchanged)**
- Positional verbose cipher: **35% → 30% (DOWN)** — productive
  morphology with selectional restrictions is hard to achieve
  with a cipher
- Templatic/agglutinative language: **NEW 40%** — 45× Latin excess
  suggests non-European morphology
- Currier A/B = SLOT2 density: **80% → 85% (UP)** — e-extension
  provides the morphological mechanism
- Galenic medical encoding: **5% (unchanged)**
- Hoax/random: **<1% (unchanged)**



## Phase 95 — Currier A/B Independent Fingerprint Analysis

### Objective

Test whether the monolithic VMS_TARGET fingerprint is valid, or whether
we've been averaging two fundamentally different encoding systems. Full
6D fingerprint for Currier A and B independently, with bootstrap
significance testing and size-matched controls.

### Method

1. Parse VMS by Currier section (A: folios 1-57, B: folios 75-116,
   MID: folios 58-74)
2. Compute full 6D fingerprint for each section independently
3. Bootstrap 200 iterations for 95% CI on each dimension
4. Control: random 50/50 split (same corpus, no structural divide)
5. Control: subsample B down to A's size (10 trials) for size effects
6. Vocabulary overlap and distinctive-word analysis
7. Glyph frequency comparison with z-tests

### Key Results

| Section | Tokens | Types | h_char | Heaps | hapax | wlen | Zipf | TTR | Dist→TARGET |
|---------|--------|-------|--------|-------|-------|------|------|-----|-------------|
| VMS_ALL | 40,351 | 8,212 | 0.653 | 0.751 | 0.719 | 5.05 | 0.924 | 0.377 | **0.145** |
| Currier A | 9,853 | 3,162 | **0.676** | 0.768 | 0.736 | 4.90 | 0.919 | 0.377 | 0.172 |
| Currier B | 26,171 | 5,212 | **0.621** | 0.770 | 0.495 | 5.11 | 0.966 | 0.252 | 0.364 |
| MID | 4,327 | 1,977 | **0.690** | 0.829 | 0.770 | 5.03 | 0.778 | 0.457 | 0.436 |

### Critical Analysis

**1. The h_char anomaly is INTRINSIC, not a mixing artifact.**
h_char(A) = 0.676, h_char(B) = 0.621, weighted average = 0.636, which is
LOWER than the mixture at 0.653. Splitting makes the gap to NL worse
by -8.3%, not better. The mixing actually helps h_char because combining
two different bigram distributions increases conditional entropy. The
anomaly lives independently within each section.

**2. A and B are comprehensively different — 4/6 dimensions have
non-overlapping 95% bootstrap CIs.** Cohen's d values: h_char = 33.2,
mean_word_len = 12.0, zipf_alpha = 9.2, hapax = 6.0. These are enormous
effect sizes.

**3. The difference is 9.1× beyond random sampling noise.** Max dimension
difference in random 50/50 split: 0.026. In Currier A/B: 0.241. The
sections are genuinely structurally different.

**4. Vocabulary overlap is shockingly low: Jaccard = 16.6%.** Two
dialects of the same natural language would show >50%. A-specific words
are gallows-heavy (cthy, cthor, kchy). B-specific words use 'lk' patterns
(lkaiin, olkeey, olkain) and 'qo' prefixes (qotain, qokain) that are
essentially absent from A.

**5. Glyph 'e' is the sharpest discriminator:** 7.2% in A → 13.0% in B
(z = -32.2). 'ch' goes the opposite way: 8.7% in A → 5.6% in B (z = +22.4).
'q' nearly doubles: 2.2% → 3.8% (z = -16.2).

**6. Some B divergence is size-inflated, but h_char is not.** Subsampling
B to A's size shows hapax jumps from 0.495 → 0.638 (size artifact) and
TTR from 0.252 → 0.329. But h_char only moves from 0.621 → 0.638 — the
gap to A (0.676) remains significant.

**7. The MID section (folios 58-74) has the HIGHEST h_char (0.690)** —
closest to NL of all three sections. This transitional zone deserves
separate investigation.

### Impact on Prior Results

**VMS_TARGET is a chimera.** The monolithic baseline represents neither
section and only exists as a weighted average. Distance to target: A at
0.172, B at 0.364 — a 2× gap. Every prior experiment that matched against
the monolithic target was matching against a statistical midpoint.

**Phase 83's best match (distance 0.1277) should be retested** against
section-specific targets, but the result likely becomes stronger for
section A and weaker for section B.

**Discovery 84.4 revised:** Phase 84 found Currier A ≈ B in TMA.
Phase 95 shows they are comprehensively different on OTHER dimensions
(h_char, word length, hapax, Zipf). The TMA similarity means both
sections encode word-order structure similarly despite having different
glyph inventories — suggesting they share the same underlying
encoding mechanism but with different parameter settings or
different source materials.

### Verdict

**Currier was right: A and B are genuinely different systems.**
Future experiments MUST test against section-specific targets.
The h_char anomaly is intrinsic to both sections (not a mixing
artifact), but its severity differs: B is more anomalous (0.621)
than A (0.676). Any encoding theory must explain both values.

### Updated Confidence Levels (cumulative through Phase 95)

- Verbose cipher (Pelling bigram-style): **15% (unchanged)** — failed
  on h_char in Phase 85
- Natural language plaintext: **92% (unchanged from Phase 94)** — both sections
  independently show NL-like properties alongside the anomaly; trail:
  85% (Ph85) → 87% (Ph86) → 89% (Ph90) → 91% (Ph92) → 92% (Ph94)
- h_char explained by cipher chunk structure: **40% → 30% (DOWN)** —
  confirmed intrinsic to both sections; no chunk/mixing explanation
- Syllabary or nomenclator model: **35% (unchanged)**
- Positional structure as key constraint: **95% (unchanged)**
- Italian source language: **25% (unchanged)**
- Monolithic VMS_TARGET validity: **NEW: 40%** — valid as rough
  approximation but A and B should be tracked separately
- Currier A/B as genuinely different systems: **NEW: 95%** — 4/6
  dimensions significant, 9× beyond noise, Jaccard = 16.6%
- Gallows as pure nulls: **NEW: INCONCLUSIVE, leaning against** (~60% confidence
  against pure nulls) — results file verdict was "INCONCLUSIVE — mixed evidence,
  cannot confirm or deny" (3 for, 2 against). Positional bias and control-stripping
  equivalence argue against pure nulls, but the evidence does not reach rejection.

---

## Skeptical Revalidation Audit (post-Phase 95)

Cross-checked all confidence claims against actual results files. Issues found
and corrected:

### Corrections Applied

1. **[HIGH] NL confidence was 85% in Phase 95 section but should be 92%.**
   The confidence trail: 85% (Ph85) → 87% (Ph86) → 89% (Ph90) → 91% (Ph92)
   → 92% (Ph94). The Phase 95 section was written using the stale Phase 85
   baseline. FIXED: now reads 92%.

2. **[HIGH] Gallows verdict was "REJECTED (~80%)" but results file says
   "INCONCLUSIVE — mixed evidence, cannot confirm or deny" (3 for, 2 against).**
   The SYNTHESIS/DISCOVERIES entry overstated the evidence. FIXED: now reads
   INCONCLUSIVE, leaning against (~60%).

### Claims Validated (no correction needed)

3. **Chunks = functional characters: 85%** — supported by h_ratio z=-1.7 vs
   NL char, distributional clustering k=25, JSD ratio 0.288, eigenvalue
   structure match (Phase 87R). Multiple independent lines of evidence.

4. **True alphabet ≈ 25: 70%** — correctly caveated as soft optimum. Silhouette
   best at k=15, h_ratio works for k=15-35. Phase 86R: partly mathematical
   artifact but distributional clustering IS better than random. 70% is fair.

5. **Currier A/B different: 95%** — 4/6 bootstrap CIs non-overlapping, Cohen's
   d up to 33.2, 9.1× beyond random, Jaccard=16.6%. If anything conservative.

6. **a/e inverse r=-0.9904** — correctly reported, p<0.001. Interpretation
   correctly updated from "substitution" (Ph91) to "vocabulary stratification"
   (Ph92). Phase 92 showed ZERO cross-hemisphere a↔e minimal pairs.

7. **Phase 60 cipher prediction match** — J(I,F)=0.241 vs prediction 0.273.
   Correctly reported in Phase 88.

### Caveats Noted (not errors, but worth flagging)

8. **h_char anomaly**: "75% resolved" (Ph86) vs "30% explained by chunk
   structure" (Ph95).** Both are correct but measure different things. Ph86:
   chunk-level analysis gives NL-like entropy ratio (TRUE). Ph95: glyph-level
   anomaly persists in both Currier sections independently (ALSO TRUE). The
   anomaly is REFRAMED by the chunk analysis, not RESOLVED. Fair assessment:
   the glyph-level h_char remains unexplained; the chunk-level analysis shows
   that VMS characters compose like NL characters, which is informative but
   doesn't make the anomaly go away.

9. **Positional cipher confidence bounces 30-55%.** Phase 88 raised it to 55%
   (7/7 metrics favor cipher). Phase 94 dropped it to 30% (e-extension =
   productive morphology, hard for a cipher to produce). The latest data-supported
   value is ~30% (Phase 94). The Phase 95 cumulative section omits this metric.

10. **e-Extension "2.64× above random"** is correct methodology (compares
    SLOT2 vs per-position average) but could mislead: total random-insertion
    hits (1009) exceed SLOT2 hits (380). The per-position comparison is valid;
    the total is a different question.

11. **Monolithic VMS_TARGET validity: 40%** — given A dist=0.172 vs B dist=0.364
    and Jaccard=16.6%, this may be generous. The target represents neither
    section accurately. Future work should use section-specific targets.

## Phase 96 — Cluster-Level h_char Test + Source Language Matching

**Script:** [phase96_cluster_hchar.py](scripts/phase96_cluster_hchar.py)
**Results:** [phase96_cluster_hchar.txt](results/phase96_cluster_hchar.txt)

### Summary

Tested whether collapsing VMS chunks to Phase 86's 25 distributional
clusters would normalize the h_char anomaly (implying homophones explain
the low entropy ratio). **The result was a methodological failure with
one important negative finding.**

Cluster-level h_char = 0.942 — above NL range (0.82-0.90). But random
clustering gives 0.971 ± 0.004 (z = -7.15 for distributional vs random).
The uplift is a mathematical artifact of alphabet reduction: any collapse
from 500+ types to 25 bins pushes h_char toward 1.0.

43% of chunk tokens were unmapped (Phase 86 covered only 206 frequent
types). Cluster-level word length dropped to 1.67 (vs NL 4-6), making
fingerprint dimensions incomparable. All NL distances >1.1 at cluster
level vs 0.37-0.54 at glyph level. The transformation destroys useful
information.

### Key Findings

1. **Homophones do NOT explain h_char.** Random collapse produces same
   or higher h_char. The anomaly cannot be normalized by merging
   variant chunks.

2. **Phase 86 clusters validated.** z = -7.15 means distributional
   clusters retain significantly more sequential structure than random
   bins — confirming they capture real patterns.

3. **h_char anomaly is encoding-structural.** All content-level
   explanations now eliminated: not homophones (Phase 96), not
   Currier mixing (Phase 95), not Pelling cipher (Phase 85). The
   anomaly arises from positional constraints within the chunk
   slot grammar — a property of the encoding system itself.

4. **Cluster-level fingerprinting is not viable** with current
   coverage (57%) and dimensional collapse.

### What We Learned (methodological)

Should have run the random-clustering null model FIRST (10 lines of
code) before building the full 300-line analysis. The null immediately
shows that any k=25 mapping inflates h_char to 0.95+, killing the
premise. Lesson: always test the null before the full analysis.

### Updated Confidence Levels (cumulative through Phase 96)

- Verbose cipher (Pelling bigram-style): **15% (unchanged)**
- Natural language plaintext: **92% (unchanged)**
- h_char explained by homophones/cluster collapse: **30% → 10% (DOWN)** —
  random clustering null shows uplift is artifact
- h_char anomaly is encoding-structural: **NEW: 85%** — all content-level
  explanations eliminated
- Syllabary or nomenclator model: **35% (unchanged)**
- Positional structure as key constraint: **95% (unchanged)**
- Italian source language: **25% (unchanged)**
- Monolithic VMS_TARGET validity: **40% (unchanged)**
- Currier A/B as genuinely different systems: **95% (unchanged)**
- Phase 86 clusters capture real patterns: **70% → 80% (UP)** — z=-7.15
  validates sequential structure retention

---

## Phase 97 — Slot Grammar as h_char Generative Model

**Script:** [phase97_slot_grammar_hchar.py](scripts/phase97_slot_grammar_hchar.py)
**Results:** [phase97_slot_grammar_hchar.txt](results/phase97_slot_grammar_hchar.txt)

### Central Question

Does the LOOP slot grammar QUANTITATIVELY predict h_char ≈ 0.65?
If the grammar's restricted inventories (S1: 3 types, S2: 3 types,
S3: 1 type, S4: 2 types, S5: 14 types) mechanically force low bigram
entropy, then h_char is not anomalous — it's an expected consequence
of having a slot grammar, and was never evidence against natural language.

### Method

1. Parsed all VMS into glyph stream with per-glyph slot annotations
   (183,198 glyphs, 183,197 transitions)
2. Decomposed H2 by transition type: within-slot, slot-to-slot,
   cross-chunk, cross-word
3. Built three null models:
   - **Slot-Resample**: keep slot patterns, resample each slot's glyph
     independently from P(glyph|slot) — preserves grammar, destroys
     within-chunk correlations
   - **Slot-Shuffle**: permute glyph assignments within each slot across
     corpus — preserves exact marginals AND slot structure
   - **Flat-Shuffle**: random permutation of entire glyph stream
4. Applied equivalent CVC-slot model to 6 Latin NL baselines
5. Tested Currier A and B separately

### Key Results

| Model                | h_char  | Notes |
|----------------------|---------|-------|
| VMS observed         | 0.6560  | The anomaly |
| Slot-Resample (50×)  | 0.9162  | [0.9156, 0.9166] |
| Slot-Shuffle (50×)   | 0.9162  | [0.9158, 0.9167] — identical to resample |
| Flat-Shuffle (20×)   | 0.9991  | [0.9990, 0.9991] — near maximum |
| NL range             | 0.82—0.90 | |

**The slot grammar explains only 24.2% of the h_char depression.**
Residual: slot_resample − observed = **+0.2602**.

NL CVC residuals: mean +0.0736 ± 0.0072. VMS z-score vs NL = **+25.9**.
The VMS has **3.5× more** within-structure correlation than any NL language.

### h_char Decomposition (ALL VMS)

| Transition type | Fraction | H2_local | H2_contrib | % of H2 |
|-----------------|----------|----------|------------|---------|
| Within-slot (e→e) | 5.8% | 0.000 | 0.000 | 0.0% |
| Slot-to-slot | 51.3% | 1.929 | 0.989 | 45.7% |
| Cross-chunk | 20.9% | 2.209 | 0.462 | 21.3% |
| Cross-word | 22.0% | 3.245 | 0.715 | 33.0% |

The action is in **slot-to-slot transitions** (45.7% of H2): knowing
which glyph occupies SLOT1 strongly predicts which glyph follows in
SLOT2. This is NOT what an independently-filled slot model would produce.

### Currier A vs B

| Section | h_obs | h_slot_resample | Residual |
|---------|-------|-----------------|----------|
| A | 0.6809 | 0.9220 | +0.2410 |
| B | 0.6229 | 0.9058 | +0.2829 |

Section B has MORE within-chunk correlation than A (+0.28 vs +0.24),
consistent with B being more constrained/anomalous (Phase 95 finding).

### Per-Slot Inventory

| Slot | Tokens | Types | H (bits) | H_max | Top glyphs |
|------|--------|-------|----------|-------|------------|
| S1 onset | 22,028 | 3 | 1.470 | 1.585 | ch(11577), y(5645), sh(4806) |
| S2 front | 42,744 | 3 | 1.422 | 1.585 | e(21302), a(15665), q(5777) |
| S3 core | 26,814 | 1 | 0.000 | 0.000 | o(26814) |
| S4 back | 26,679 | 2 | 0.999 | 1.000 | d(13902), i(12777) |
| S5 coda | 64,164 | 14 | 3.085 | 3.807 | y(13196), l(11115), k(10576) |

S3 has ZERO entropy (only 'o'). S4 is near-maximum (d≈i). S5 has the
most diversity but still far below maximum. The extremely constrained
inventories explain why the slot-resample moves h_char to 0.916 — but
that's still far above the observed 0.656.

### Interpretation

**The slot grammar creates a 24% h_char depression, but the observed
depression is 34%. The remaining 76% comes from holistic chunk selection.**

When the VMS writer chose `ch` for SLOT1, they didn't independently
roll dice for SLOT2, SLOT3, etc. They selected a whole CHUNK TYPE
(e.g., `ch.e.d.y` or `ch.o.l`), which determines all slot fills
simultaneously. This produces massive within-chunk predictability
that independent slot sampling can't replicate.

This is **exactly what Phase 85-86 argued**: chunks are the functional
units, not individual glyphs. Phase 97 now quantifies the effect:
chunk-type holism accounts for 76% of the h_char depression, slot
grammar accounts for 24%.

### NL Comparison

| Language | h_obs | h_CVC_resample | Residual | %_explained |
|----------|-------|----------------|----------|-------------|
| Apicius | 0.812 | 0.899 | +0.088 | ~53% |
| Caesar | 0.865 | 0.941 | +0.076 | ~44% |
| Erasmus | 0.867 | 0.939 | +0.072 | ~46% |
| Galen | 0.876 | 0.948 | +0.072 | ~42% |
| Pliny | 0.883 | 0.946 | +0.064 | ~46% |
| Vulgate | 0.869 | 0.940 | +0.070 | ~46% |

In NL, CVC structure explains 42-54% of the h_char depression from 1.0.
In VMS, slot structure explains only 24%. The VMS's within-structure
correlations are 3.5× larger — its "syllables" are much more internally
rigid than any NL syllable.

### Skeptical Notes

1. **CVC baseline is crude.** NL syllables have more complex structure
   (onset clusters, codas) than the V/C + run-position model captures.
   However, this BIASES AGAINST the finding: the VMS grammar should
   explain MORE per slot (specific inventories) than CVC (binary V/C),
   yet explains LESS. The finding is conservative.

2. **Slot-Resample = Slot-Shuffle.** Both give 0.916 — confirming that
   the exact glyph frequencies per slot don't matter; it's the slot
   structure that produces the 0.916 baseline. Any deviation below
   this IS within-chunk correlation.

3. **Phase 85's 523 chunk types with steep Zipf distribution** means
   top ~50 chunks cover most tokens. This concentrates within-chunk
   predictability — knowing "I'm in a ch-initial chunk" narrows to
   about 10-15 common continuation patterns. In NL, knowing the onset
   consonant leaves many more possible syllable continuations.

4. **The 3.5× excess is the critical number.** Any encoding theory
   must explain why VMS chunks are 3.5× more internally rigid than NL
   syllables. Candidate explanations:
   - **Syllabary/abugida**: chunk types are holistic symbols (like kana),
     so internal predictability is definitional
   - **Nomenclator**: chunk types are look-up table entries
   - **Very small effective vocabulary**: only ~100-150 distinct "words"
     mapped onto the chunk inventory
   - **NOT**: independent slot-filling, where each slot encodes a
     separate piece of information (that would give h_char ≈ 0.916)

5. **What this does NOT explain:** Why the slot grammar exists at all.
   If chunks are holistic symbols, why do they decompose into 5 ordered
   slots? Possible answers: (a) the writing system was designed with
   internal regularity (like Korean Hangul); (b) the "slots" are an
   artifact of our grammar matching a small set of templates; (c) there
   IS some slot-level logic, but it's heavily constrained by co-selection.

### Updated Confidence Levels (cumulative through Phase 97)

- Verbose cipher (Pelling bigram-style): **15% (unchanged)**
- Natural language plaintext: **92% (unchanged)** — Phase 97 doesn't
  directly address NL vs non-NL; it characterizes the encoding structure
- h_char explained by slot grammar alone: **NEW: REFUTED** — only 24%,
  z = +25.9 vs NL. The slot grammar plus holistic chunk selection
  together would explain it, but that's "chunks = characters" (Phase 85)
- h_char anomaly is encoding-structural: **85% → 90% (UP)** — now
  quantified: 76% from chunk holism, 24% from slot constraints
- Chunks = functional characters (holistic units): **85% → 90% (UP)** —
  Phase 97 provides the strongest quantitative evidence yet:
  within-chunk correlations far exceed what independent slots would produce
- Syllabary or nomenclator model: **35% → 45% (UP)** — if chunks are
  holistic units with internal regularity, a syllabary-like writing system
  is the most natural explanation
- Positional verbose cipher: **30% → 15% (DOWN)** — independent slot-filling
  predicts h_char ≈ 0.916, observed 0.656. Fatal mismatch.
- Positional structure as key constraint: **95% (unchanged)**
- Italian source language: **25% (unchanged)**
- Monolithic VMS_TARGET validity: **40% (unchanged)**
- Currier A/B as genuinely different systems: **95% (unchanged)**
- Phase 86 clusters capture real patterns: **80% (unchanged)**

---

## Skeptical Revalidation Audit (post-Phase 97)

### Cross-check against results files

1. **[OK] h_char observed values.** Phase 97 reports 0.6560 (ALL),
   0.6809 (A), 0.6229 (B). Phase 95 reported 0.6530 (ALL), 0.6758 (A),
   0.6208 (B). Small differences (0.003) due to Phase 96 using a
   different tokenizer (8-slot regex, Phase 97 uses canonical 5-slot).
   Both are valid; the discrepancy is methodological, not an error.

2. **[OK] NL h_char range.** Phase 97 gets 0.812-0.883 for Latin texts.
   Phase 95 fingerprints show 0.840-0.894. Slight range difference
   from different text sets; no contradiction.

3. **[FLAGGED] Phase 94 "5/6 NL diagnostics pass" not in results file.**
   The results file lists 5 metrics but no formal pass/fail tally.
   SYNTHESIS used this framing for readability but it's editorialized.
   The Phase 94 SYNTHESIS section should state "5 of 6 tested metrics
   favor productive morphology" rather than implying a formal test.

4. **[FLAGGED] Positional cipher confidence omitted from Phase 95/96
   cumulative lists.** Phase 88 raised it to 55%, Phase 94 dropped to
   30%. It disappeared from Phase 95/96 lists. NOW restored at 15%
   (Phase 97 provides quantitative refutation: independent slot-filling
   predicts 0.916, not 0.656).

5. **[OK] Chunks = functional characters at 85% → 90%.** Phase 85R
   showed chunks match NL characters (z = -1.70) better than syllables
   (z = +5.64). Phase 97 now shows chunks are holistic units (3.5×
   NL syllable rigidity). The 90% confidence reflects both lines of
   evidence reinforcing each other.

6. **[OK] h_char encoding-structural at 85% → 90%.** Phase 96 eliminated
   homophones, Phase 95 eliminated A/B mixing, Phase 85 eliminated
   Pelling cipher. Phase 97 now shows it's specifically 76% chunk holism
   + 24% slot grammar. The mechanism is identified and quantified.

7. **[NOTED] Gallows-as-nulls still absent from cumulative list.**
   Phase 87 gallows null test was INCONCLUSIVE (~60% against pure nulls).
   This was correctly flagged in Phase 95 revalidation but never
   re-added to the cumulative list. Status: UNRESOLVED, not tracked.

---

## Phase 98 — Generative Chunk Model

### Objective

Train bigram and trigram Markov models on the 523 LOOP-grammar chunk
types. Generate synthetic VMS text. Quantify how much of the VMS's
statistical fingerprint — especially the anomalous glyph h_char (0.653) —
is captured by chunk-level sequential dependencies alone. Validate the
25-class alphabet reduction from Phase 86.

### Method

Bigram (order-1) and trigram (order-2) Markov models trained on the full
78,526-chunk stream (with word-boundary tokens). 10 synthetic texts per
model. Null models: (a) shuffled chunks, (b) uniform random. Z-scores
computed as (VMS − synthetic_mean) / synthetic_std. Collapsed all 523
chunk types to 25 Phase 86 equivalence classes (100% coverage via
distributional nearest-neighbour extension). 5-fold cross-validated
perplexity.

### Key Results

| Metric          | VMS    | Bigram  | Bi z   | Trigram | Tri z  |
|-----------------|--------|---------|--------|---------|--------|
| glyph h_char    | 0.6530 | 0.6695  | −17.6  | **0.6524** | **+0.66** |
| chunk h_ratio   | 0.8176 | 0.8401  | −42.0  | 0.8002  | +26.9  |
| Zipf slope      | −0.876 | −0.877  | +0.5   | −0.874  | −0.4   |
| cross-word MI   | 0.716  | 0.405   | +68.7  | 0.848   | −14.6  |
| positional Gini | 0.442  | 0.442   | +0.2   | 0.446   | −1.3   |
| word TTR        | 0.201  | 0.205   | −4.7   | 0.161   | +47.3  |

**Headline finding:** The trigram model reproduces glyph h_char almost
exactly (0.6524 vs 0.6530, z = +0.66, p > 0.50). Chunk-level bigram
dependencies fully account for the glyph-level entropy anomaly.

**25-class collapse:** Collapsed trigram is indistinguishable from VMS
on all metrics (h_ratio z = +1.50, Zipf z = −0.12). The 25-class
alphabet with 100% chunk coverage preserves essential structure.

**What Markov misses:** Cross-word MI (neither order captures the
intermediate VMS level), word TTR (trigram over-memorizes), hapax ratio
(both under-generate). The VMS has structure beyond Markov chains.

**Perplexity anomaly:** Trigram CV perplexity (54.2) exceeds bigram
(23.4) due to extreme context sparsity — the VMS has a very concentrated
transition structure.

**Currier A/B symmetric:** Both sections show the same Markov gap
(z ≈ −17.7 for bigram h_ratio), consistent with shared generative
mechanism.

### Critical Assessment

The glyph h_char match (z = +0.66) resolves a 98-phase-old puzzle:
the anomalous glyph entropy is fully emergent from chunk-level
sequential dependencies. This does NOT mean the VMS is a Markov process —
NL character bigrams are also well-approximated by Markov models. The
finding is consistent with both NL and systematic cipher interpretations.

The cross-word MI mismatch and hapax under-generation indicate VMS has
structure beyond local n-gram statistics — likely syntactic or semantic
constraints. The trigram's success at glyph h_char despite poor
perplexity is a cautionary note: fingerprint matching does not guarantee
model adequacy.

### Updated Confidence Levels (cumulative through Phase 98)

- Verbose cipher (Pelling bigram-style): **15% (unchanged)**
- Natural language plaintext: **92% (unchanged)** — Markov success
  consistent with NL; hapax/TTR mismatches support genuine vocabulary
- h_char anomaly is encoding-structural: **90% → 95% (UP)** — now
  quantitatively reproduced: chunk-level trigram dependencies generate
  glyph h_char = 0.652, z = +0.66 vs VMS 0.653
- Chunks = functional characters (holistic units): **90% → 92% (UP)** —
  25-class collapse with 100% coverage produces NL-like h_ratio (0.849)
  and trigram indistinguishable from VMS
- Phase 86 clusters capture real patterns: **80% → 85% (UP)** —
  extended to full coverage; collapsed metrics match VMS
- Syllabary or nomenclator model: **45% (unchanged)**
- Positional verbose cipher: **15% (unchanged)**
- Positional structure as key constraint: **95% (unchanged)**
- Italian source language: **25% (unchanged)**
- Monolithic VMS_TARGET validity: **40% (unchanged)**
- Currier A/B as genuinely different systems: **95% (unchanged)** —
  same Markov gap confirms shared mechanism
- VMS contains structure beyond Markov chains: **NEW: 85%** —
  cross-word MI (z = ±15–69), word TTR (z = +47), hapax ratio all
  deviate significantly from any Markov order tested

---

## Skeptical Revalidation Audit (post-Phase 98)

### Cross-check against Phase 97 results

1. **[OK] Glyph h_char baseline.** Phase 98 reports 0.6530 (ALL),
   consistent with Phase 97's 0.6560 (difference due to different
   tokenizer handling of non-alpha characters). Phase 95 reported
   0.6530. Values stable across phases.

2. **[OK] Chunk h_ratio baseline.** Phase 98 reports 0.8176 (ALL),
   matching Phase 85's 0.818 (rounded). Consistent.

3. **[FLAGGED] Trigram perplexity worse than bigram.** This is
   unusual and indicates the trigram model is not a good predictive
   model despite its excellent fingerprint match. The glyph h_char
   reproduction could be partially coincidental — the trigram
   over-memorizes specific patterns that happen to yield the right
   glyph entropy. Should be verified on held-out folio subsets.

4. **[OK] Null models clearly rejected.** Shuffled h_ratio = 0.941
   (z = −387), uniform glyph h_char = 0.787 (z = −402). Both
   extremes are massively far from VMS. Sequential structure is real.

5. **[FLAGGED] Cross-word MI mismatch needs investigation.** Bigram
   under-predicts by 43%, trigram over-predicts by 18%. This could
   indicate that word boundaries carry syntactic information not
   captured by local chunk transitions. Phase 99+ should investigate.

6. **[OK] 25-class full-coverage extension.** The nearest-neighbour
   mapping assigned all 317 unmapped chunk types to clusters.
   Coverage is now 100%, addressing the Phase 96 criticism (43% gap).
   The collapsed fingerprint is stable (h_ratio = 0.849 vs Phase 86's
   0.849 at k=25). No artifact detected.

---

### Phase 100 — Targeted Decipherment with the 25-Class Alphabet

**Result: SIMPLE SUBSTITUTION FAILS. VMS is NL-like but not decipherable
as a monoalphabetic substitution cipher on the 25-class alphabet.**

Key findings (script: `scripts/phase100_decipherment.py`,
results: `results/phase100_decipherment.json`):

1. **[CRITICAL] Five of six languages produce above-chance dictionary
   hits (z > 2).** Latin z=+7.91, Italian z=+7.72, Czech z=+5.68,
   German z=+4.56, English z=+4.03. French alone falls below chance
   (z=+1.39). This demonstrates generic NL-like structure, NOT
   specific language identification.

2. **[CRITICAL] Z-score rankings are unstable across runs.** The
   z-score leader changed every run: English (+8.38) → Italian
   (+7.72) → Latin (+7.91). CV generalization is stable: Latin
   consistently leads at ~16.7%.

3. **[CRITICAL] No coherent text produced.** The best Latin mapping
   yields: "esta us s vs t tt uam t er tt art us r t es us..." —
   complete gibberish. No grammatical structure, no recognizable
   phrases, no topic-relevant vocabulary. This is the definitive
   failure criterion.

4. **[OK] Word-length mismatch quantified.** VMS averages 1.83
   classes/word (55.8% are 2-class). NL words average 4–6 letters.
   The comparison is fundamentally between VMS syllable-sequences
   and NL letter-sequences — a category mismatch.

5. **[OK] VMS entropy is anomalously low.** Unigram H = 3.172 bits
   (25 classes) vs NL H = 4.03–4.72 bits. The entropy ratio (67–79%)
   confirms the VMS class alphabet is more concentrated / less
   uniform than any NL letter distribution tested.

6. **[FLAGGED] Latin shows best and most stable CV generalization**
   (16.7%), the only language consistently exceeding 10% across runs.
   Other languages vary wildly (English: 3.7–8.0%, Italian: 2.3–
   16.7%, German: 6.0–14.1%). This is consistent with Latin-text
   provenance but the ceiling (83.3% non-matching) is far too low
   for genuine decipherment.

7. **[OK] Short-word hits are trivially expected.** English len-1
   hit rate = 100%, Latin len-2 = 69.6%. With a 25-symbol alphabet,
   any single symbol maps to a valid 1-letter word, and most 2-symbol
   combinations match 2-letter function words (et, in, de, to, etc.).
   Only len ≥ 3 hits carry diagnostic information.

**Implications for the encoding hypothesis:**

- Simple substitution on distributional chunk classes: **REJECTED**
- The 25 classes likely represent syllable-types, not phonemes
- If a NL underlies the VMS, the encoding is polyalphabetic,
  homophonic, transposition-based, syllabic, or a nomenclator/code
- Italian/Latin remain the best-fitting substrate languages by
  structural similarity, consistent with provenance (N. Italy, 15th C)
- Latin is the most stable match by CV generalization (16.8%)
- NL hypothesis probability: **UNCHANGED at 92%**

---

## Phase 99 — Script Typology Comparison

### Headline Result
VMS chunks are typologically closest to **abugidas** (Thai d=5.174, Tibetan d=5.282) and **Korean Hangul** (d=5.376) in an 8-dimensional feature space, but the match is **NOT statistically significant** (permutation p=1.0). VMS occupies a novel region of typological space with uniquely high within-unit MI (1.540) and low onset dominance (0.636).

### Key Findings

1. **Script type ranking**: abugida (mean d=5.54) > Hangul (d=5.38) > NL syllable (mean d=5.63) > syllabary (mean d=7.87) > alphabet (mean d=8.55) > abjad (mean d=8.50)

2. **VMS is an outlier, not a cluster member.** Permutation test (2000 iterations): p=1.0. Random feature combinations are at least as close to any reference as VMS is to Thai. The ranking is informative but distances are uniformly large.

3. **Within-unit MI = 1.540 is anomalously high.** Next highest: French syllables 0.805, Korean Hangul 0.600. VMS glyphs within chunks predict each other far more strongly than sub-units in any known writing system. This is the single most discriminating feature.

4. **Low onset dominance (0.636) is unique.** All abugidas have onset/base dominance ≥ 1.0. VMS S1 fills only 27.9% vs S5 at 82.0%. The "coda" slot dominates, not the "onset" — opposite to every known abugida.

5. **h_ratio (0.818) matches abugidas closely.** Thai 0.810, Devanagari 0.820. This is the one dimension where VMS genuinely resembles abugidas. But 1/8 matching dimensions is insufficient for typological classification.

6. **Feature sensitivity: 5/8 stable.** Dropping n_slots, mean_fill_rate, or pos_entropy_ratio shifts nearest neighbour from Thai to Korean Hangul. The Thai-vs-Hangul distinction is fragile; both are approximately equidistant.

### Typological Feature Vector (VMS)

| Feature | Value | Closest match |
|---|---|---|
| log2(inventory) = 9.03 | 523 types | Between abugida and NL syllable |
| within_unit_mi = 1.540 | Anomalously high | Nothing close |
| n_slots = 5 | Complex structure | VMS is unique |
| mean_fill_rate = 0.438 | Sparse | Below all references |
| onset_dominance = 0.636 | Coda-dominant | Unique (all refs ≥ 1.0) |
| pos_entropy_ratio = 0.906 | Low positional effect | Near Ethiopic (0.900) |
| h_ratio = 0.818 | NL-like | Thai (0.810), Devanagari (0.820) |
| units_per_word = 1.948 | ~2 chunks/word | Near NL syllable count |

### Updated Confidence Levels (post-Phase 99)

- VMS chunks are functional sub-word units: **98%** (unchanged)
- VMS encodes natural language: **92%** (unchanged — abugida proximity is consistent but not diagnostic)
- VMS chunk structure is closer to abugida than alphabet: **85%** (NEW) — but only on h_ratio dimension; other features diverge
- VMS chunk structure is closer to abugida than syllabary: **90%** (NEW) — syllabaries lack internal structure entirely
- VMS is a known writing system type: **15%** (NEW) — p=1.0 outlier status; likely a novel/constructed system
- Korean Hangul is the best structural analogy for VMS chunks: **70%** (NEW) — featural blocks with positional sub-units, 4/8 dimensions match
- VMS has stronger internal correlations than any known script: **95%** (NEW) — within-MI = 1.540 is 2× the next highest

### Skeptical Revalidation Audit (post-Phase 99)

1. **[FLAGGED] Reference points are estimates.** Abugida/syllabary parameters come from typological descriptions, not measured corpus statistics. The Thai/Tibetan proximity could shift ±1 rank with properly measured reference data. This is a fundamental limitation.

2. **[FLAGGED] Feature space is hand-designed.** 8 dimensions were chosen a priori. Adding different features (e.g., Zipf slope, cross-word MI, hapax ratio) could change the typological landscape. The sensitivity test partially addresses this: 5/8 features are non-pivotal.

3. **[OK] NL syllable baselines are computed empirically.** 12 corpora × syllable decomposition provides a data-grounded alphabetic baseline. VMS is approximately equidistant from these as from published abugida references.

4. **[FLAGGED] Onset dominance < 1.0 is unprecedented.** No known writing system has its "onset" slot as the least-filled. This either means (a) the LOOP grammar's slot labeling doesn't correspond to phonological onset/nucleus, or (b) VMS genuinely inverts the typical consonant-onset structure, or (c) VMS is not an abugida at all. This deserves dedicated investigation.

5. **[OK] High within-MI validated.** Phase 97 independently found 45.7% of h_char from within-slot transitions. Phase 99's MI = 1.540 is consistent: strong within-chunk glyph-to-glyph predictability is real and not an artifact.

---

## Phase 101 — Resolve the Currier A/B Dichotomy

### What Was Done

Phase 101 discovered that the `get_currier_language()` function hardcoded in 8+ phase scripts had a 39% error rate (79/201 folios misassigned vs authoritative `$L=` tags in IVTFF headers). After correcting the split (A: 11,728 words / 107 folios; B: 25,504 words / 78 folios), the A/B dichotomy was re-analysed at every level: 25-class distributions, vocabulary overlap, Markov cross-perplexity, 1000-permutation significance test, folio-level nearest-centroid classifier (LOO-CV), differential feature ranking, NL fit comparison, section-effect controls, and glyph-level distributions.

### What Was Found

| Test | Result | Significance |
|---|---|---|
| Prior A/B assignments | 39% error rate — net shift of 10,604 words from A→B | All prior A/B results contaminated |
| Class unigram JSD(A,B) | 0.0184 | z = +32.3, p < 0.001 |
| Class bigram JSD(A,B) | 0.0988 | z = +45.1, p < 0.001 |
| Cross-perplexity A→B / A→A | 1.010 | Grammar nearly identical |
| Cross-perplexity B→A / B→B | 1.191 | Moderate divergence (asymmetric) |
| Word Jaccard | 0.148 | Vocabularies 85% disjoint |
| Chunk Jaccard | 0.643 | Building blocks shared |
| Class bigram Jaccard | 0.706 | Grammar patterns shared |
| Classifier accuracy (LOO-CV) | 88.6% (majority 57.8%) | z = +11.71, p < 0.001 |
| NL fit ranking A vs B | Identical ordering, max diff 0.009 | Same NL profile |
| Within-section herbal A/B JSD | 0.032 | ≈ between-section herbal-A vs pharma-A (0.034) |

### Key Patterns

| Pattern | Evidence | Confidence |
|---|---|---|
| A/B distinction is statistically real | z > 30 at both unigram and bigram levels, 1000 permutations | **99%** |
| A and B share the same chunk grammar | A→B cross-perplexity ratio = 1.010 | **95%** |
| A and B differ primarily in vocabulary | Word Jaccard 0.148 vs class bigram Jaccard 0.706 | **95%** |
| A/B is confounded with manuscript section | Bio/stars = 100% B; herbal/pharma ≈ 80% A; within-section JSD ≈ between-section JSD | **90%** |
| Prior A/B analyses are invalid | 79 folio misassignments, 39% error rate | **100%** |
| Pharma section is transitional | 10/21 classifier misclassifications are pharma folios | **70%** |
| Both A and B match the same NL languages | Italian < Latin < French ≈ German < English < Czech for both | **95%** |

### Critical Corrections to Prior Phases

- **Phase 3** (root JSD = 0.5038): Computed on corrupted A/B split; must be disregarded
- **Phase 63** (NMI = 0.006, z = 41.0): Scribe-Currier correlation was measured on wrong labels
- **Phase 68** (mean JSD = 0.041, 18/21 same top successor): Transition comparison contaminated
- **Phase 98** (A h_ratio=0.808, B h_ratio=0.772): Baselines computed on wrong split

### Distinctive A vs B Signatures

**A is enriched in:**
- Gallows glyphs: `cth` (3.9× in A), `cph` (3.1×), `ckh` (1.4×), `cfh` (2.7×)
- `o` glyph (+5.5% in A), `ch` (+2.3%), `s` (+1.0%)
- Class C4 (log-OR = +0.76), C5 (+0.47), C0 (+0.35)
- Gallows-rich words: `ctho`, `cthody`, `chom`, `qotchol`

**B is enriched in:**
- `e` glyph (+5.0% in B), `q` (+1.4%), `d` (+1.6%), `k` (+1.2%)
- Class C3 (log-OR = −0.42), C2 (−0.66), C7 (−0.84), C10 (−0.54)
- C10→C9 bigram (24× enrichment in B), C5→C9 (11×), C9→C3 (8×)
- -edy/-eedy words: `qokeedy(307)`, `otedy(166)`, `okedy(112)`

### Updated Confidence Levels (post-Phase 101)

- Currier A/B is a genuine statistical distinction: **99%** (NEW — z > 30, p < 0.001)
- A/B is register variation within one encoding system: **80%** (NEW — shared grammar, different vocabulary)
- A/B is partly a section effect, not purely linguistic: **85%** (NEW — within-section JSD ≈ between-section JSD)
- Prior A/B results (Phases 3, 63, 68, 98) are invalid: **100%** (NEW — 39% assignment error rate)
- VMS encodes natural language: **92%** (unchanged)

### Skeptical Revalidation Audit (post-Phase 101)

1. **[CRITICAL] Prior A/B analyses are invalid.** The hardcoded `get_currier_language()` function had a 39% error rate. Phases 3, 63, 68, and 98 all used this function. Their A/B-specific conclusions (root JSD, transition comparison, scribe detection baselines) must be disregarded until recomputed with correct assignments.

2. **[FLAGGED] Cross-perplexity asymmetry may be a corpus-size artifact.** B has 2.2× more words than A. The near-1.0 A→B ratio may mean A's patterns are a subset observable within B's larger corpus, not that grammars are truly identical. A controlled test with matched corpus sizes would be more rigorous.

3. **[FLAGGED] Section confound undermines causal claims.** The classifier's 88.6% accuracy may largely reflect *section identity* (herbal vs bio vs stars) rather than an intrinsic A/B property. A classifier trained only on within-section data (herbal A vs herbal B) would test this.

4. **[FLAGGED] $L= tags may themselves contain errors.** Currier's 1976 assignments were encoded into the IVTFF transcription. The 10 pharma folios classified as B but tagged A suggest Currier may have been uncertain about the pharma section. These tags are authoritative but not infallible.

5. **[OK] Permutation tests are valid.** 1,000 folio-level shuffles test the correct null hypothesis (random partition of folios). The z > 30 is robust and cannot be explained by multiple testing, corpus-size imbalance, or section effects.

6. **[OK] Low word Jaccard is genuine.** Even accounting for A's smaller corpus, 14.8% overlap is dramatically low. For comparison, random 30%/70% splits of a single corpus would yield Jaccard > 0.5 at these sample sizes.

---

## Phase 102 Update: Historical Validation — Capstone Synthesis

**What was tested:** Whether 101 phases of statistical findings are jointly compatible with the manuscript's historical constraints (C14 dating, Italian provenance, Widemann→Rudolf chain, pharmaceutical content, multi-scribe hypothesis). Eight validation steps: temporal corpus fit, genre fingerprinting, provenance language test, marginalia analysis, codicological cross-tabulation, Bayesian compatibility matrix, contradiction scan, cumulative evidence summary.

### Key findings

**1. Scribal hand predicts Currier language almost perfectly (Cramér's V = 0.968)**

This is the most impactful finding of Phase 102. Hand 1 → Currier A (105/106 folios); Hands 2, 3, 5 → Currier B (76/77 folios). χ² = 172.3, p < 0.001. This reinterprets Phase 101's "register variation" conclusion: A/B is a **scribal effect**, not a content-driven register switch. Different scribes used the same LOOP grammar but had different spelling/abbreviation habits.

**2. Temporal dating cannot be validated statistically**

Period-correct texts (1300–1500) are NOT closer to VMS than out-of-period texts (ratio = 1.089, wrong direction). The encoding transforms the signal so thoroughly that epoch-of-origin effects are washed out. Italian Cucina (1350) ranks #2 overall but ancient Latin texts (Vulgate 400 AD, Galen 180 AD) rank #1 and #3.

**3. Genre fingerprinting fails through the encoding layer**

Closest genre match is "literary" (distance 0.084), not "recipe" (0.237) or "medical" (0.151). This replicates the Phase 76 anomaly. Surface statistics cannot penetrate the encoding to identify content type. The pharmaceutical hypothesis rests on **illustrations**, not text statistics.

**4. Provenance-language alignment: directionally correct, not significant**

Italian/German/Latin are 18.6% closer to VMS than Czech/French/English, but permutation test gives p = 0.306 (z = −0.90). Italian has the best rank JSD (0.0099) of any language, consistent with provenance, but indistinguishable from chance with only 6 groups.

**5. No fatal contradictions across 102 phases**

All 5 logical consistency checks pass. Pre-1400 creation, simple substitution, and hoax/meaningless hypotheses are formally ruled out. Italian provenance is consistent with best-fit language. Pharmaceutical genre is consistent with illustrations.

### Most parsimonious scenario

The VMS is a **pharmaceutical/herbal compendium** written in **Northern Italy ~1440–1480**, encoding **Italian or Latin** through a **constructed notation system** operating at the chunk/syllable level (LOOP grammar). **Multiple scribes** wrote different sections, producing the Currier A/B distinction as a scribal artifact rather than a content register. The manuscript later entered German-speaking collections (Widemann → Rudolf II → Horčický → Baresch → Marci → Kircher) where marginal annotations were added in German on f116v.

### Bayesian compatibility summary

| Dimension | Winner | Score | Runner-up | Score |
|-----------|--------|-------|-----------|-------|
| Substrate language | Italian | +5 | Latin | +3 |
| Encoding type | Constructed script | +5 | Verbose cipher | +3 |
| Genre | Pharmaceutical | +7 | Alchemical | +5 |
| Creation era | 1440–1480 | +3 | 1400–1440 | +2 |

Ruled out: Pre-1400 (−6), simple substitution (−6), meaningless (−5), Czech (−2).

### Established facts (≥95% confidence after 107 phases)

1. VMS has NL-like statistical structure (h_ratio=0.818, Zipf, Heaps)
2. Chunks are functional sub-word units (LOOP grammar parses 99.8%)
3. Simple substitution is ruled out (Phase 75 gallows + Phase 100 failure)
4. Hoax/meaningless is ruled out (NL statistics + LOOP + cross-word MI)
5. Currier A/B is real (z > 30, 88.6% classifier)
6. A and B share the same grammar (perplexity ratio 1.01)
7. VMS is a typological outlier (p = 1.0 on 8 dimensions)
8. VMS endings have abbreviation-like properties (paradigm fill 78% gap closed,
   Phase 105; positional glyph matches to Latin scribal conventions, JKP)
9. Simple substitution cipher is ruled out for Latin, Italian, German, Czech,
   French, and English (Phase 106c positional frequency matching — 0 readable
   text across 9 corpora; confirms Phase 75 gallows result with broader scope)
10. Within-chunk slot interactions are ALL anomalously correlated (Phase 107:
    10/10 pairs significant, z > 1000; body-coda NMI = 0.43 vs NL max 0.26)

### Skeptical audit

1. **[CRITICAL] No readable text in 107 phases.** All findings are distributional. Phase 106 explicitly attempted decipherment via positional frequency matching across 6 languages and failed completely. Phase 107 characterized the anomaly's internal structure but did not produce readable text. Without decipherment, language identification is circumstantial and genre identification rests on illustrations.

2. **[CRITICAL] Corpus limitations.** Only 2 of 13 corpora are period-correct (Italian Cucina 1350, German Ortolf 1450). No 15th-century Italian pharmaceutical manuscripts available for comparison.

3. **[FLAGGED] Cramér's V depends on $H= tag accuracy.** If palaeographic hand assignments contain errors (as $L= tags did in 39% of folios), the hand-language association could be weaker. However, hand assignments are based on more objective criteria than language classification.

4. **[FLAGGED] Bayesian matrix is qualitative.** Scores reflect subjective evidence weighting. Different weights could reorder the rankings. The +7 pharmaceutical score aggregates 6 weak-to-moderate evidence items.

5. **[OK] Joint compatibility holds.** No internal contradictions detected across 107 phases. The Italian/pharmaceutical/constructed-script hypothesis is consistent with all established statistical findings and all known historical constraints.

6. **[FLAGGED] Italian scores worst in Phase 106c.** Despite being the leading candidate language, Italian (Cucina corpus) scored 0 word hits and lowest trigram hits in positional frequency matching. This doesn't rule out Italian (the test rules out simple substitution, not the language), but it is noteworthy that Italian's character frequency profile is the LEAST compatible with VMS glyph profiles among all tested languages.

7. **[FLAGGED] Body-coda coupling challenges abbreviation hypothesis.** Phase 107 found body-coda NMI = 0.4273, nearly double the highest NL value (0.26). This means VMS chunk bodies strongly predict their codas — inconsistent with the abbreviation model where suffixes should be relatively stem-independent. The abbreviation hypothesis may need to be reframed: shapes derive from abbreviation tradition, but the encoding mechanism is cipher-like or constructed.
