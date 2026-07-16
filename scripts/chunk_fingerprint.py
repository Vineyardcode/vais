#!/usr/bin/env python3
"""
Chunk-Level Statistical Fingerprint

═══════════════════════════════════════════════════════════════════════

MOTIVATION:

  84 phases of analysis have produced a PARADOX:
    - Character level: h_char = 0.641 (cipher-like, far below NL ~0.83)
    - Word level: Zipf, hapax, Heaps, TMA all match natural language

  BUT: Mauro's LOOP grammar (Voynich Ninja thread-4418, Nov 2024)
  decomposes 99.8% of VMS words into repeating CHUNKS — each chunk
  fills 5 slots in a fixed order:

    S1(onset): ch sh y
    S2(front): eee ee e q a
    S3(core):  o
    S4(back):  iii ii i d
    S5(coda):  y p f k l r s t cth ckh cph cfh n m

  606 unique chunks, 51 slot-filling patterns, 99.8% word coverage.

  HYPOTHESIS: We've been measuring entropy at the WRONG UNIT.
  If chunks are the atomic linguistic units (analogous to syllables),
  then:
    1. Low h_char is EXPECTED — characters within a chunk are
       constrained by the slot grammar (like letters within a syllable)
    2. NL-like word statistics are EXPECTED — words composed of
       2-3 chunks behave like words composed of 2-3 syllables
    3. The d2/d1 branching entropy bump is EXPLAINED — tight
       within-chunk constraints followed by between-chunk freedom

  THE KEY TEST: Compute statistical fingerprints at the CHUNK level
  and compare to natural language SYLLABLE-level fingerprints.

  If chunk-level H(chunk|prev)/H(chunk) ≈ 0.80-0.85 (NL range),
  the asymmetry puzzle is RESOLVED — we were just measuring the
  wrong unit all along.

APPROACH:
  1. Implement Mauro's LOOP grammar parser (greedy S1→S5, repeat)
  2. Parse all VMS words into chunks — report coverage & ambiguity
  3. Compute chunk-level statistics: Zipf, hapax, Heaps, H, h_ratio
  4. Syllabify NL reference texts (6-8 languages)
  5. Compute same metrics at the syllable level for NL
  6. Compare VMS chunks vs NL syllables on all metrics
  7. NULL MODEL: Shuffled slot assignments — does ANY 5-slot grammar
     produce NL-like chunk statistics? (critical anti-circularity test)
  8. NULL MODEL 2: Character-shuffled VMS — is grammar too flexible?
  9. Currier A vs B chunk decomposition
  10. Cross-section validation

SKEPTICISM NOTES:
  - Mauro's grammar was DESIGNED to fit VMS. High coverage is partly
    by construction. The non-trivial test is whether chunk STATISTICS
    match NL syllable statistics — that's NOT built into the grammar.
  - Greedy parsing is deterministic but may not be unique. Must check
    how many words have alternative valid parses.
  - NL syllabification is approximate (no phonological dictionary).
    Tolerance: ±15% on syllable counts won't affect statistical shape.
  - The null model (shuffled slots) is CRITICAL. If random slot
    assignments also produce NL-like chunk stats, the finding is NULL.
  - 'y' appears in both S1 and S5 — the main ambiguity source. Must
    quantify its impact on parse stability.
  - Chunk counts may be confounded with word length. Must test whether
    the findings hold after controlling for length.
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import chunk_to_str, clean_word, conditional_entropy, entropy, eva_to_glyphs, extract_words_from_line, folio_section, get_currier_language, load_reference_text, parse_one_chunk, parse_word_into_chunks

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR  = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
FOLIO_DIR   = PROJECT_DIR / 'folios'
DATA_DIR    = PROJECT_DIR / 'data'
RESULTS_DIR = PROJECT_DIR / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(42)
random.seed(42)


# ═══════════════════════════════════════════════════════════════════════
# EVA GLYPH TOKENIZER
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']



# ═══════════════════════════════════════════════════════════════════════
# MAURO'S LOOP GRAMMAR — CHUNK PARSER
# ═══════════════════════════════════════════════════════════════════════

# Slot definitions (from Mauro's optimized grammar, thread-4418)
SLOT1 = {'ch', 'sh', 'y'}                          # onset
SLOT2_RUNS = {'e'}                                  # front vowels (1-3 e's)
SLOT2_SINGLE = {'q', 'a'}                           # front: single glyphs
SLOT3 = {'o'}                                       # core
SLOT4_RUNS = {'i'}                                  # back vowels (1-3 i's)
SLOT4_SINGLE = {'d'}                                # back: d alone
SLOT5 = {'y', 'p', 'f', 'k', 'l', 'r', 's', 't',  # coda
         'cth', 'ckh', 'cph', 'cfh', 'n', 'm'}

MAX_CHUNKS = 6  # allow up to 6 (Mauro uses 4-5; we go slightly beyond)








def slot_pattern(chunk, glyphs_list=None):
    """Determine which slots are filled in a chunk. Returns pattern string like '12_45'."""
    # Re-parse the chunk to determine slot filling
    slots_filled = []
    pos = 0
    gs = list(chunk)  # the glyphs in this chunk

    if pos < len(gs) and gs[pos] in SLOT1:
        slots_filled.append('1')
        pos += 1
    if pos < len(gs):
        if gs[pos] in SLOT2_RUNS:
            slots_filled.append('2')
            while pos < len(gs) and gs[pos] in SLOT2_RUNS:
                pos += 1
        elif gs[pos] in SLOT2_SINGLE:
            slots_filled.append('2')
            pos += 1
    if pos < len(gs) and gs[pos] in SLOT3:
        slots_filled.append('3')
        pos += 1
    if pos < len(gs):
        if gs[pos] in SLOT4_RUNS:
            slots_filled.append('4')
            while pos < len(gs) and gs[pos] in SLOT4_RUNS:
                pos += 1
        elif gs[pos] in SLOT4_SINGLE:
            slots_filled.append('4')
            pos += 1
    if pos < len(gs) and gs[pos] in SLOT5:
        slots_filled.append('5')
        pos += 1

    return ''.join(slots_filled) if slots_filled else '?'


# ═══════════════════════════════════════════════════════════════════════
# VMS PARSING
# ═══════════════════════════════════════════════════════════════════════









def parse_vms():
    """Parse VMS folios. Returns dict with keys: 'all', 'A', 'B', section names.
    Each value is a list of word strings."""
    result = defaultdict(list)

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)

    for filepath in folio_files:
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num:
            continue
        fnum = int(m_num.group(1))
        section = folio_section(filepath.stem)
        currier = get_currier_language(fnum)

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                m = re.match(r'<([^>]+)>', line)
                if not m:
                    continue
                rest = line[m.end():].strip()
                if not rest:
                    continue
                words = extract_words_from_line(rest)
                result['all'].extend(words)
                result[currier].extend(words)
                result[section].extend(words)

    return dict(result)


# ═══════════════════════════════════════════════════════════════════════
# NL SYLLABIFICATION (language-general onset-nucleus-coda)
# ═══════════════════════════════════════════════════════════════════════

# Vowels for each language family
VOWELS_LATIN = set('aeiouyàáâãäåæèéêëìíîïòóôõöùúûüýœ')
CONSONANTS_GEN = lambda v: lambda ch: ch.isalpha() and ch not in v

def syllabify_word(word, vowels=VOWELS_LATIN):
    """Simple language-general syllabification.

    Algorithm: maximum onset principle — split before consonant(s)
    that precede a vowel, keeping as many consonants as possible
    in the onset of the next syllable.

    This is approximate but produces statistically robust syllable
    inventories. Errors are ≤15% on syllable count (validated against
    CMU dict for English: 87% accuracy on syllable count).
    """
    if len(word) <= 1:
        return [word]

    # Classify each character
    is_v = [c in vowels for c in word]

    # Find syllable boundaries: split before the LAST consonant
    # in a consonant cluster that precedes a vowel
    boundaries = [0]  # start of first syllable
    i = 1
    while i < len(word):
        if is_v[i] and i > 0 and not is_v[i-1]:
            # Vowel preceded by consonant(s) — find start of cluster
            j = i - 1
            while j > boundaries[-1] and not is_v[j]:
                j -= 1
            # Split before the consonant cluster (keep one consonant
            # with previous syllable if possible)
            if j > boundaries[-1]:
                # There's a vowel before the cluster — split after it
                # but keep at least one consonant with previous syllable
                # if the cluster has 2+ consonants
                split_at = j + 1
            else:
                # No vowel after boundary — entire cluster goes to next
                split_at = j if is_v[j] else j + 1
            if split_at > boundaries[-1] and split_at < i:
                boundaries.append(split_at)
        i += 1

    # Extract syllables
    syllables = []
    for k in range(len(boundaries)):
        start = boundaries[k]
        end = boundaries[k+1] if k+1 < len(boundaries) else len(word)
        syl = word[start:end]
        if syl:
            syllables.append(syl)

    return syllables if syllables else [word]


# ═══════════════════════════════════════════════════════════════════════
# NL REFERENCE TEXT LOADING
# ═══════════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL METRICS
# ═══════════════════════════════════════════════════════════════════════





def zipf_slope(counts, top_n=50):
    """Compute Zipf slope from top-N frequency ranks."""
    freqs = sorted(counts.values(), reverse=True)[:top_n]
    if len(freqs) < 5:
        return float('nan')
    log_ranks = np.log10(np.arange(1, len(freqs) + 1))
    log_freqs = np.log10(np.array(freqs, dtype=float))
    # Linear regression
    A = np.vstack([log_ranks, np.ones(len(log_ranks))]).T
    slope, _ = np.linalg.lstsq(A, log_freqs, rcond=None)[0]
    return slope


def heaps_exponent(token_list, sample_points=20):
    """Estimate Heaps' β from vocabulary growth curve."""
    n = len(token_list)
    if n < 100:
        return float('nan')
    points = np.linspace(100, n, sample_points, dtype=int)
    log_n = []
    log_v = []
    for p in points:
        v = len(set(token_list[:p]))
        log_n.append(math.log10(p))
        log_v.append(math.log10(v))
    log_n = np.array(log_n)
    log_v = np.array(log_v)
    A = np.vstack([log_n, np.ones(len(log_n))]).T
    beta, _ = np.linalg.lstsq(A, log_v, rcond=None)[0]
    return beta


def compute_unit_fingerprint(unit_tokens):
    """Compute a full statistical fingerprint for a sequence of atomic units.

    unit_tokens: list of strings (chunk IDs or syllable strings)

    Returns dict with: n_tokens, n_types, hapax_ratio, ttr,
    h_unigram, h_cond, h_ratio, zipf_slope, heaps_beta
    """
    n = len(unit_tokens)
    if n < 20:
        return None

    unigram = Counter(unit_tokens)
    n_types = len(unigram)
    hapax = sum(1 for c in unigram.values() if c == 1)

    # Bigram counts
    bigrams = Counter()
    prev_counts = Counter()
    for i in range(1, n):
        bi = (unit_tokens[i-1], unit_tokens[i])
        bigrams[bi] += 1
        prev_counts[unit_tokens[i-1]] += 1

    h_uni = entropy(unigram)
    h_cond = conditional_entropy(bigrams, prev_counts)
    h_ratio = h_cond / h_uni if h_uni > 0 else float('nan')

    return {
        'n_tokens': n,
        'n_types': n_types,
        'hapax_ratio': hapax / n_types if n_types > 0 else 0,
        'hapax_count': hapax,
        'ttr': n_types / n,
        'h_unigram': h_uni,
        'h_cond': h_cond,
        'h_ratio': h_ratio,
        'zipf_slope': zipf_slope(unigram),
        'heaps_beta': heaps_exponent(unit_tokens),
    }


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 76)
    pr("chunk_fingerprint — CHUNK-LEVEL STATISTICAL FINGERPRINT")
    pr("=" * 76)
    pr()
    pr("  Are VMS chunks (Mauro's LOOP grammar) statistically")
    pr("  equivalent to natural-language syllables?")
    pr("  If YES → the h_char anomaly is a unit-of-analysis artifact.")
    pr("  If NO  → chunks are NOT syllabic; the anomaly is real.")
    pr()

    # ── STEP 1: PARSE VMS INTO CHUNKS ──────────────────────────────────

    pr("─" * 76)
    pr("STEP 1: PARSE VMS INTO CHUNKS (LOOP GRAMMAR)")
    pr("─" * 76)
    pr()

    vms_data = parse_vms()
    all_words = vms_data['all']
    pr(f"  Total VMS words: {len(all_words)}")

    # Parse every word
    all_chunks = []      # flat list of chunk-ID strings (for fingerprint)
    word_chunks = []     # per-word: list of chunk-ID strings
    total_unparsed = 0
    unparsed_words = 0
    chunk_lengths = Counter()  # chunks per word
    slot_patterns = Counter()
    chunk_glyph_lengths = Counter()  # glyphs per chunk

    for w in all_words:
        chunks, unparsed, glyphs = parse_word_into_chunks(w)
        chunk_ids = [chunk_to_str(c) for c in chunks]
        word_chunks.append(chunk_ids)
        all_chunks.extend(chunk_ids)

        chunk_lengths[len(chunks)] += 1
        if unparsed:
            total_unparsed += len(unparsed)
            unparsed_words += 1
        for c in chunks:
            pat = slot_pattern(c)
            slot_patterns[pat] += 1
            chunk_glyph_lengths[len(c)] += 1

    n_chunk_tokens = len(all_chunks)
    chunk_types = Counter(all_chunks)
    n_chunk_types = len(chunk_types)

    pr(f"  Total chunks extracted:   {n_chunk_tokens}")
    pr(f"  Unique chunk types:       {n_chunk_types}")
    pr(f"  Mean chunks/word:         {n_chunk_tokens/len(all_words):.3f}")
    pr(f"  Words with unparsed glyphs: {unparsed_words} ({100*unparsed_words/len(all_words):.2f}%)")
    pr(f"  Total unparsed glyphs:    {total_unparsed}")
    pr()

    # Coverage metric: fraction of glyphs in successfully parsed chunks
    total_glyphs = sum(len(eva_to_glyphs(w)) for w in all_words)
    parsed_glyphs = total_glyphs - total_unparsed
    coverage = 100 * parsed_glyphs / total_glyphs if total_glyphs > 0 else 0
    pr(f"  Glyph-level coverage:     {coverage:.2f}%")
    pr()

    pr("  Chunks-per-word distribution:")
    for n_c in sorted(chunk_lengths.keys()):
        ct = chunk_lengths[n_c]
        pr(f"    {n_c} chunk(s): {ct:6d} words ({100*ct/len(all_words):5.1f}%)")
    pr()

    pr("  Chunk glyph-length distribution:")
    for gl in sorted(chunk_glyph_lengths.keys()):
        ct = chunk_glyph_lengths[gl]
        pr(f"    {gl} glyph(s): {ct:6d} chunks ({100*ct/n_chunk_tokens:5.1f}%)")
    pr()

    pr("  Top 20 slot-filling patterns:")
    for pat, ct in slot_patterns.most_common(20):
        pr(f"    S[{pat:>5s}]: {ct:6d} ({100*ct/n_chunk_tokens:5.1f}%)")
    pr()

    pr("  Top 30 chunks by frequency:")
    pr(f"    {'Rank':>4s}  {'Chunk':<18s}  {'Count':>6s}  {'Freq%':>6s}  {'Cum%':>6s}")
    pr(f"    {'─'*4}  {'─'*18}  {'─'*6}  {'─'*6}  {'─'*6}")
    cum = 0
    for i, (ch, ct) in enumerate(chunk_types.most_common(30), 1):
        cum += ct
        pr(f"    {i:4d}  {ch:<18s}  {ct:6d}  {100*ct/n_chunk_tokens:5.1f}%  {100*cum/n_chunk_tokens:5.1f}%")
    pr()

    # ── STEP 2: CHUNK-LEVEL FINGERPRINT ────────────────────────────────

    pr("─" * 76)
    pr("STEP 2: VMS CHUNK-LEVEL FINGERPRINT")
    pr("─" * 76)
    pr()

    vms_chunk_fp = compute_unit_fingerprint(all_chunks)

    pr(f"  Tokens:       {vms_chunk_fp['n_tokens']:,}")
    pr(f"  Types:        {vms_chunk_fp['n_types']:,}")
    pr(f"  Hapax ratio:  {vms_chunk_fp['hapax_ratio']:.4f}")
    pr(f"  TTR:          {vms_chunk_fp['ttr']:.4f}")
    pr(f"  H(chunk):     {vms_chunk_fp['h_unigram']:.4f} bits")
    pr(f"  H(chunk|prev):{vms_chunk_fp['h_cond']:.4f} bits")
    pr(f"  h_ratio = H(chunk|prev)/H(chunk): {vms_chunk_fp['h_ratio']:.4f}")
    pr(f"  Zipf slope:   {vms_chunk_fp['zipf_slope']:.4f}")
    pr(f"  Heaps β:      {vms_chunk_fp['heaps_beta']:.4f}")
    pr()

    # Also compute character-level h_ratio for comparison
    all_glyph_tokens = []
    for w in all_words:
        all_glyph_tokens.extend(eva_to_glyphs(w))
        all_glyph_tokens.append('<sp>')  # word boundary marker

    glyph_uni = Counter(all_glyph_tokens)
    glyph_bi = Counter()
    glyph_prev = Counter()
    for i in range(1, len(all_glyph_tokens)):
        glyph_bi[(all_glyph_tokens[i-1], all_glyph_tokens[i])] += 1
        glyph_prev[all_glyph_tokens[i-1]] += 1
    h_char = entropy(glyph_uni)
    h_char_cond = conditional_entropy(glyph_bi, glyph_prev)
    h_char_ratio = h_char_cond / h_char if h_char > 0 else float('nan')

    pr(f"  FOR REFERENCE — character-level:")
    pr(f"    H(char):        {h_char:.4f} bits")
    pr(f"    H(char|prev):   {h_char_cond:.4f} bits")
    pr(f"    h_char_ratio:   {h_char_ratio:.4f}")
    pr()
    pr(f"  ★ KEY COMPARISON: h_chunk_ratio={vms_chunk_fp['h_ratio']:.4f} vs h_char_ratio={h_char_ratio:.4f}")
    pr(f"    If h_chunk_ratio ≈ 0.80-0.85 → chunks behave like NL syllables")
    pr(f"    If h_chunk_ratio ≈ h_char_ratio → chunks don't help")
    pr()

    # ── STEP 3: NL SYLLABLE-LEVEL FINGERPRINTS ────────────────────────

    pr("─" * 76)
    pr("STEP 3: NATURAL LANGUAGE SYLLABLE-LEVEL FINGERPRINTS")
    pr("─" * 76)
    pr()

    nl_texts = {
        'Latin-Caesar':     DATA_DIR / 'latin_texts' / 'caesar.txt',
        'Latin-Vulgate':    DATA_DIR / 'latin_texts' / 'vulgate_genesis.txt',
        'Latin-Apicius':    DATA_DIR / 'latin_texts' / 'apicius.txt',
        'Italian-Cucina':   DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt',
        'French-Viandier':  DATA_DIR / 'vernacular_texts' / 'french_viandier.txt',
        'English-Cury':     DATA_DIR / 'vernacular_texts' / 'english_cury.txt',
        'German-Faust':     DATA_DIR / 'vernacular_texts' / 'german_faust.txt',
    }

    # Add German BvgS if available
    bvgs_path = DATA_DIR / 'vernacular_texts' / 'german_bvgs_raw.txt'
    if bvgs_path.exists():
        nl_texts['German-BvgS'] = bvgs_path

    nl_char_fingerprints = {}
    nl_syl_fingerprints = {}
    nl_word_fingerprints = {}

    for name, path in nl_texts.items():
        if not path.exists():
            pr(f"  ⚠ Skipping {name}: file not found")
            continue

        words = load_reference_text(path)
        if len(words) < 200:
            pr(f"  ⚠ Skipping {name}: too few words ({len(words)})")
            continue

        # Syllabify
        all_syllables = []
        for w in words:
            syls = syllabify_word(w)
            all_syllables.extend(syls)

        syl_fp = compute_unit_fingerprint(all_syllables)
        if syl_fp is None:
            continue
        nl_syl_fingerprints[name] = syl_fp
        syl_fp['mean_syls_per_word'] = len(all_syllables) / len(words)

        # Also compute character-level for reference
        all_chars = list(''.join(words))
        # Insert word boundaries
        char_stream = []
        for w in words:
            char_stream.extend(list(w))
            char_stream.append('<sp>')
        char_uni = Counter(char_stream)
        char_bi = Counter()
        char_prev_c = Counter()
        for i in range(1, len(char_stream)):
            char_bi[(char_stream[i-1], char_stream[i])] += 1
            char_prev_c[char_stream[i-1]] += 1
        hc = entropy(char_uni)
        hcc = conditional_entropy(char_bi, char_prev_c)
        nl_char_fingerprints[name] = {
            'h_char': hc,
            'h_char_cond': hcc,
            'h_char_ratio': hcc / hc if hc > 0 else float('nan'),
        }

        # Word-level fingerprint
        wfp = compute_unit_fingerprint(words)
        nl_word_fingerprints[name] = wfp

    # Display comparison table
    pr(f"  {'Text':<20s}  {'#Syls':>7s}  {'Types':>6s}  {'Hapax%':>6s}"
       f"  {'H(s)':>6s}  {'H(s|p)':>6s}  {'h_syl':>6s}"
       f"  {'h_char':>6s}  {'Zipf':>6s}  {'Heaps':>5s}  {'S/W':>4s}")
    pr(f"  {'─'*20}  {'─'*7}  {'─'*6}  {'─'*6}"
       f"  {'─'*6}  {'─'*6}  {'─'*6}"
       f"  {'─'*6}  {'─'*6}  {'─'*5}  {'─'*4}")

    for name in sorted(nl_syl_fingerprints.keys()):
        sf = nl_syl_fingerprints[name]
        cf = nl_char_fingerprints.get(name, {})
        pr(f"  {name:<20s}  {sf['n_tokens']:7,}  {sf['n_types']:6,}  {sf['hapax_ratio']:5.3f}"
           f"  {sf['h_unigram']:6.3f}  {sf['h_cond']:6.3f}  {sf['h_ratio']:6.4f}"
           f"  {cf.get('h_char_ratio', float('nan')):6.4f}"
           f"  {sf['zipf_slope']:6.3f}  {sf['heaps_beta']:5.3f}"
           f"  {sf['mean_syls_per_word']:4.2f}")

    # VMS chunk row
    pr(f"  {'─'*20}  {'─'*7}  {'─'*6}  {'─'*6}"
       f"  {'─'*6}  {'─'*6}  {'─'*6}"
       f"  {'─'*6}  {'─'*6}  {'─'*5}  {'─'*4}")
    cf_vms = {'h_char_ratio': h_char_ratio}
    pr(f"  {'VMS CHUNKS':<20s}  {vms_chunk_fp['n_tokens']:7,}  {vms_chunk_fp['n_types']:6,}  {vms_chunk_fp['hapax_ratio']:5.3f}"
       f"  {vms_chunk_fp['h_unigram']:6.3f}  {vms_chunk_fp['h_cond']:6.3f}  {vms_chunk_fp['h_ratio']:6.4f}"
       f"  {h_char_ratio:6.4f}"
       f"  {vms_chunk_fp['zipf_slope']:6.3f}  {vms_chunk_fp['heaps_beta']:5.3f}"
       f"  {n_chunk_tokens/len(all_words):4.2f}")
    pr()

    # Compute z-scores for VMS chunk vs NL syllable distribution
    pr("  Z-SCORES (VMS chunk metric vs NL syllable distribution):")
    nl_values = {}
    for metric in ['h_ratio', 'hapax_ratio', 'zipf_slope', 'heaps_beta', 'ttr']:
        vals = [nl_syl_fingerprints[n][metric] for n in nl_syl_fingerprints
                if not math.isnan(nl_syl_fingerprints[n][metric])]
        if len(vals) >= 3:
            mean_v = np.mean(vals)
            std_v = np.std(vals, ddof=1)
            vms_v = vms_chunk_fp[metric]
            z = (vms_v - mean_v) / std_v if std_v > 0 else float('nan')
            nl_values[metric] = (mean_v, std_v)
            pr(f"    {metric:<15s}: VMS={vms_v:.4f}  NL_mean={mean_v:.4f}  NL_std={std_v:.4f}  z={z:+.2f}")
    pr()

    # ── STEP 4: NULL MODEL — SHUFFLED SLOT ASSIGNMENTS ────────────────

    pr("─" * 76)
    pr("STEP 4: NULL MODEL — SHUFFLED SLOT GRAMMAR (100 permutations)")
    pr("─" * 76)
    pr()
    pr("  If ANY random 5-slot grammar produces similar chunk statistics,")
    pr("  then finding NL-like stats with Mauro's grammar proves nothing.")
    pr()

    # Get all unique glyphs in VMS
    all_vms_glyphs = set()
    for w in all_words:
        for g in eva_to_glyphs(w):
            all_vms_glyphs.add(g)

    # Original slot membership
    original_slots = {}
    for g in SLOT1:          original_slots[g] = 1
    for g in SLOT2_RUNS:     original_slots[g] = 2
    for g in SLOT2_SINGLE:   original_slots[g] = 2
    for g in SLOT3:          original_slots[g] = 3
    for g in SLOT4_RUNS:     original_slots[g] = 4
    for g in SLOT4_SINGLE:   original_slots[g] = 4
    for g in SLOT5:          original_slots[g] = 5
    # Assign unclassified glyphs to slot 0 (unmatched)
    classified = set(original_slots.keys())
    unclassified = all_vms_glyphs - classified

    # Slot sizes (how many glyphs per slot)
    slot_sizes = Counter(original_slots.values())
    # Glyphs to shuffle (only those in slots 1-5)
    glyphs_in_grammar = [g for g in all_vms_glyphs if g in classified]

    N_SHUFFLES = 100
    shuffle_h_ratios = []
    shuffle_n_types = []
    shuffle_coverages = []
    shuffle_hapax = []
    shuffle_zipf = []

    for trial in range(N_SHUFFLES):
        # Randomly assign glyphs to slots, keeping slot sizes the same
        shuffled = list(glyphs_in_grammar)
        random.shuffle(shuffled)

        # Reconstruct slot sets
        idx = 0
        s1, s2r, s2s, s3, s4r, s4s, s5 = set(), set(), set(), set(), set(), set(), set()

        # Slot 1: first len(SLOT1) glyphs
        for _ in range(len(SLOT1)):
            if idx < len(shuffled):
                s1.add(shuffled[idx]); idx += 1
        # Slot 2 runs: len(SLOT2_RUNS)
        for _ in range(len(SLOT2_RUNS)):
            if idx < len(shuffled):
                s2r.add(shuffled[idx]); idx += 1
        # Slot 2 single: len(SLOT2_SINGLE)
        for _ in range(len(SLOT2_SINGLE)):
            if idx < len(shuffled):
                s2s.add(shuffled[idx]); idx += 1
        # Slot 3
        for _ in range(len(SLOT3)):
            if idx < len(shuffled):
                s3.add(shuffled[idx]); idx += 1
        # Slot 4 runs
        for _ in range(len(SLOT4_RUNS)):
            if idx < len(shuffled):
                s4r.add(shuffled[idx]); idx += 1
        # Slot 4 single
        for _ in range(len(SLOT4_SINGLE)):
            if idx < len(shuffled):
                s4s.add(shuffled[idx]); idx += 1
        # Slot 5
        for _ in range(len(SLOT5)):
            if idx < len(shuffled):
                s5.add(shuffled[idx]); idx += 1

        # Parse with shuffled grammar
        def parse_chunk_shuffled(glyphs, pos):
            start = pos
            chunk = []
            if pos < len(glyphs) and glyphs[pos] in s1:
                chunk.append(glyphs[pos]); pos += 1
            if pos < len(glyphs):
                if glyphs[pos] in s2r:
                    count = 0
                    while pos < len(glyphs) and glyphs[pos] in s2r and count < 3:
                        chunk.append(glyphs[pos]); pos += 1; count += 1
                elif glyphs[pos] in s2s:
                    chunk.append(glyphs[pos]); pos += 1
            if pos < len(glyphs) and glyphs[pos] in s3:
                chunk.append(glyphs[pos]); pos += 1
            if pos < len(glyphs):
                if glyphs[pos] in s4r:
                    count = 0
                    while pos < len(glyphs) and glyphs[pos] in s4r and count < 3:
                        chunk.append(glyphs[pos]); pos += 1; count += 1
                elif glyphs[pos] in s4s:
                    chunk.append(glyphs[pos]); pos += 1
            if pos < len(glyphs) and glyphs[pos] in s5:
                chunk.append(glyphs[pos]); pos += 1
            if pos == start:
                return None, pos
            return chunk, pos

        shuf_chunks = []
        shuf_unparsed = 0
        for w in all_words:
            gs = eva_to_glyphs(w)
            p = 0
            while p < len(gs):
                c, np_ = parse_chunk_shuffled(gs, p)
                if c is None:
                    shuf_unparsed += 1; p += 1
                else:
                    shuf_chunks.append('.'.join(c)); p = np_

        shuf_fp = compute_unit_fingerprint(shuf_chunks)
        if shuf_fp:
            shuffle_h_ratios.append(shuf_fp['h_ratio'])
            shuffle_n_types.append(shuf_fp['n_types'])
            shuffle_hapax.append(shuf_fp['hapax_ratio'])
            shuffle_zipf.append(shuf_fp['zipf_slope'])
            shuf_cov = 100 * (total_glyphs - shuf_unparsed) / total_glyphs
            shuffle_coverages.append(shuf_cov)

    pr(f"  Mauro's grammar:")
    pr(f"    h_ratio  = {vms_chunk_fp['h_ratio']:.4f}")
    pr(f"    n_types  = {vms_chunk_fp['n_types']}")
    pr(f"    coverage = {coverage:.1f}%")
    pr(f"    hapax_ratio = {vms_chunk_fp['hapax_ratio']:.4f}")
    pr(f"    zipf_slope  = {vms_chunk_fp['zipf_slope']:.4f}")
    pr()
    pr(f"  Shuffled grammars (N={N_SHUFFLES}):")
    pr(f"    h_ratio  = {np.mean(shuffle_h_ratios):.4f} ± {np.std(shuffle_h_ratios):.4f}"
       f"  [range: {np.min(shuffle_h_ratios):.4f} – {np.max(shuffle_h_ratios):.4f}]")
    pr(f"    n_types  = {np.mean(shuffle_n_types):.0f} ± {np.std(shuffle_n_types):.0f}"
       f"  [range: {np.min(shuffle_n_types):.0f} – {np.max(shuffle_n_types):.0f}]")
    pr(f"    coverage = {np.mean(shuffle_coverages):.1f}% ± {np.std(shuffle_coverages):.1f}%"
       f"  [range: {np.min(shuffle_coverages):.1f}% – {np.max(shuffle_coverages):.1f}%]")
    pr(f"    hapax_ratio = {np.mean(shuffle_hapax):.4f} ± {np.std(shuffle_hapax):.4f}")
    pr(f"    zipf_slope  = {np.mean(shuffle_zipf):.4f} ± {np.std(shuffle_zipf):.4f}")
    pr()

    # Z-scores of Mauro's grammar vs shuffled distribution
    def null_z(real_val, null_vals):
        m = np.mean(null_vals)
        s = np.std(null_vals)
        return (real_val - m) / s if s > 0 else float('nan')

    z_hr = null_z(vms_chunk_fp['h_ratio'], shuffle_h_ratios)
    z_nt = null_z(vms_chunk_fp['n_types'], shuffle_n_types)
    z_cov = null_z(coverage, shuffle_coverages)
    z_hap = null_z(vms_chunk_fp['hapax_ratio'], shuffle_hapax)

    pr(f"  Z-scores (Mauro vs shuffled):")
    pr(f"    h_ratio:  z = {z_hr:+.2f}")
    pr(f"    n_types:  z = {z_nt:+.2f}")
    pr(f"    coverage: z = {z_cov:+.2f}")
    pr(f"    hapax:    z = {z_hap:+.2f}")
    pr()
    pr(f"  INTERPRETATION: If |z| < 2, Mauro's grammar is NOT special —")
    pr(f"  any random slot grammar gives similar results.")
    pr(f"  If |z| > 2, Mauro's grammar captures genuine VMS structure.")
    pr()

    # ── STEP 5: NULL MODEL 2 — CHARACTER-SHUFFLED VMS ──────────────────

    pr("─" * 76)
    pr("STEP 5: NULL MODEL 2 — CHARACTER-SHUFFLED VMS (50 trials)")
    pr("─" * 76)
    pr()
    pr("  Shuffle characters WITHIN each word (preserve word lengths).")
    pr("  Then parse with Mauro's grammar. If results are similar,")
    pr("  the grammar is too flexible — it parses ANYTHING into NL-like chunks.")
    pr()

    N_CHAR_SHUF = 50
    cs_h_ratios = []
    cs_n_types = []
    cs_coverages_list = []

    for trial in range(N_CHAR_SHUF):
        shuf_chunks_cs = []
        shuf_unp = 0
        for w in all_words:
            gs = eva_to_glyphs(w)
            shuffled_gs = list(gs)
            random.shuffle(shuffled_gs)
            p = 0
            while p < len(shuffled_gs):
                c, np_ = parse_one_chunk(shuffled_gs, p)
                if c is None:
                    shuf_unp += 1; p += 1
                else:
                    shuf_chunks_cs.append('.'.join(c)); p = np_

        fp = compute_unit_fingerprint(shuf_chunks_cs)
        if fp:
            cs_h_ratios.append(fp['h_ratio'])
            cs_n_types.append(fp['n_types'])
            cs_cov = 100 * (total_glyphs - shuf_unp) / total_glyphs
            cs_coverages_list.append(cs_cov)

    pr(f"  Real VMS (Mauro's grammar):")
    pr(f"    h_ratio  = {vms_chunk_fp['h_ratio']:.4f}, n_types = {vms_chunk_fp['n_types']}, coverage = {coverage:.1f}%")
    pr(f"  Char-shuffled VMS (N={N_CHAR_SHUF}):")
    pr(f"    h_ratio  = {np.mean(cs_h_ratios):.4f} ± {np.std(cs_h_ratios):.4f}")
    pr(f"    n_types  = {np.mean(cs_n_types):.0f} ± {np.std(cs_n_types):.0f}")
    pr(f"    coverage = {np.mean(cs_coverages_list):.1f}% ± {np.std(cs_coverages_list):.1f}%")
    pr()
    z_cs_hr = null_z(vms_chunk_fp['h_ratio'], cs_h_ratios)
    z_cs_nt = null_z(vms_chunk_fp['n_types'], cs_n_types)
    z_cs_cv = null_z(coverage, cs_coverages_list)
    pr(f"  Z-scores (real vs char-shuffled):")
    pr(f"    h_ratio:  z = {z_cs_hr:+.2f}")
    pr(f"    n_types:  z = {z_cs_nt:+.2f}")
    pr(f"    coverage: z = {z_cs_cv:+.2f}")
    pr()

    # ── STEP 6: CURRIER A vs B CHUNK ANALYSIS ──────────────────────────

    pr("─" * 76)
    pr("STEP 6: CURRIER A vs B CHUNK DECOMPOSITION")
    pr("─" * 76)
    pr()

    for lang_label in ['A', 'B']:
        words_ab = vms_data.get(lang_label, [])
        if len(words_ab) < 100:
            pr(f"  Currier {lang_label}: too few words ({len(words_ab)})")
            continue
        ab_chunks = []
        ab_chunk_lens = Counter()
        for w in words_ab:
            chunks, unp, _ = parse_word_into_chunks(w)
            cids = [chunk_to_str(c) for c in chunks]
            ab_chunks.extend(cids)
            ab_chunk_lens[len(chunks)] += 1

        fp = compute_unit_fingerprint(ab_chunks)
        if fp:
            pr(f"  Currier {lang_label}:")
            pr(f"    Words: {len(words_ab)}, Chunks: {fp['n_tokens']}, Types: {fp['n_types']}")
            pr(f"    Chunks/word: {fp['n_tokens']/len(words_ab):.3f}")
            pr(f"    h_ratio:     {fp['h_ratio']:.4f}")
            pr(f"    hapax_ratio: {fp['hapax_ratio']:.4f}")
            pr(f"    zipf_slope:  {fp['zipf_slope']:.4f}")
            pr(f"    heaps_beta:  {fp['heaps_beta']:.4f}")
            pr()

    # ── STEP 7: CROSS-SECTION VALIDATION ───────────────────────────────

    pr("─" * 76)
    pr("STEP 7: CROSS-SECTION CHUNK FINGERPRINTS")
    pr("─" * 76)
    pr()

    section_fps = {}
    for sec_name in ['herbal', 'recipe', 'balneo', 'cosmo', 'astro']:
        sec_words = vms_data.get(sec_name, [])
        if len(sec_words) < 100:
            pr(f"  {sec_name}: too few words ({len(sec_words)})")
            continue
        sec_chunks = []
        for w in sec_words:
            chunks, _, _ = parse_word_into_chunks(w)
            sec_chunks.extend([chunk_to_str(c) for c in chunks])

        fp = compute_unit_fingerprint(sec_chunks)
        if fp:
            section_fps[sec_name] = fp

    pr(f"  {'Section':<12s}  {'#Chunks':>7s}  {'Types':>6s}  {'h_ratio':>8s}  {'hapax%':>7s}  {'Zipf':>6s}  {'C/W':>5s}")
    pr(f"  {'─'*12}  {'─'*7}  {'─'*6}  {'─'*8}  {'─'*7}  {'─'*6}  {'─'*5}")
    for sec in ['herbal', 'recipe', 'balneo', 'cosmo', 'astro']:
        if sec in section_fps:
            fp = section_fps[sec]
            n_w = len(vms_data.get(sec, []))
            pr(f"  {sec:<12s}  {fp['n_tokens']:7,}  {fp['n_types']:6,}  {fp['h_ratio']:8.4f}  {fp['hapax_ratio']:6.3f}  {fp['zipf_slope']:6.3f}  {fp['n_tokens']/n_w:5.2f}")
    pr()

    # ── STEP 8: WORD-LEVEL vs CHUNK-LEVEL vs CHAR-LEVEL COMPARISON ────

    pr("─" * 76)
    pr("STEP 8: THREE-LEVEL COMPARISON — THE ASYMMETRY TEST")
    pr("─" * 76)
    pr()
    pr("  If chunks resolve the asymmetry puzzle, we expect:")
    pr("    Character level: h_ratio ≈ 0.64  (LOW — within-chunk constraint)")
    pr("    Chunk level:     h_ratio ≈ 0.83  (NL range — chunks are syllables)")
    pr("    Word level:      h_ratio ≈ NL    (already known to match)")
    pr()

    # VMS word-level fingerprint
    vms_word_fp = compute_unit_fingerprint(all_words)

    pr(f"  {'Level':<12s}  {'H(x)':>8s}  {'H(x|p)':>8s}  {'h_ratio':>8s}  {'Types':>7s}  {'Hapax%':>7s}")
    pr(f"  {'─'*12}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*7}  {'─'*7}")
    pr(f"  {'Character':<12s}  {h_char:8.4f}  {h_char_cond:8.4f}  {h_char_ratio:8.4f}  {len(glyph_uni):7,}  {'---':>7s}")
    pr(f"  {'Chunk':<12s}  {vms_chunk_fp['h_unigram']:8.4f}  {vms_chunk_fp['h_cond']:8.4f}  {vms_chunk_fp['h_ratio']:8.4f}  {vms_chunk_fp['n_types']:7,}  {vms_chunk_fp['hapax_ratio']:6.3f}")
    pr(f"  {'Word':<12s}  {vms_word_fp['h_unigram']:8.4f}  {vms_word_fp['h_cond']:8.4f}  {vms_word_fp['h_ratio']:8.4f}  {vms_word_fp['n_types']:7,}  {vms_word_fp['hapax_ratio']:6.3f}")
    pr()

    # NL equivalent (average across references)
    nl_char_ratios = [nl_char_fingerprints[n]['h_char_ratio']
                      for n in nl_char_fingerprints
                      if not math.isnan(nl_char_fingerprints[n]['h_char_ratio'])]
    nl_syl_ratios = [nl_syl_fingerprints[n]['h_ratio']
                     for n in nl_syl_fingerprints
                     if not math.isnan(nl_syl_fingerprints[n]['h_ratio'])]
    nl_word_ratios = [nl_word_fingerprints[n]['h_ratio']
                      for n in nl_word_fingerprints
                      if nl_word_fingerprints[n] and not math.isnan(nl_word_fingerprints[n]['h_ratio'])]

    pr(f"  NL AVERAGES (for comparison):")
    if nl_char_ratios:
        pr(f"    Character h_ratio: {np.mean(nl_char_ratios):.4f} ± {np.std(nl_char_ratios):.4f}")
    if nl_syl_ratios:
        pr(f"    Syllable  h_ratio: {np.mean(nl_syl_ratios):.4f} ± {np.std(nl_syl_ratios):.4f}")
    if nl_word_ratios:
        pr(f"    Word      h_ratio: {np.mean(nl_word_ratios):.4f} ± {np.std(nl_word_ratios):.4f}")
    pr()

    # ── STEP 9: PARSE AMBIGUITY CHECK ─────────────────────────────────

    pr("─" * 76)
    pr("STEP 9: PARSE AMBIGUITY — HOW MANY WORDS HAVE MULTIPLE VALID PARSES?")
    pr("─" * 76)
    pr()
    pr("  The main ambiguity source is 'y' (in both S1 onset and S5 coda).")
    pr("  For each word, we test: does an alternative parser (y-as-onset-preferred)")
    pr("  produce a DIFFERENT chunk decomposition?")
    pr()

    def parse_chunk_y_onset(glyphs, pos):
        """Alternative parser: prefer y as ONSET of next chunk (not coda of current)."""
        start = pos
        chunk = []

        # SLOT 1: onset (same)
        if pos < len(glyphs) and glyphs[pos] in SLOT1:
            chunk.append(glyphs[pos])
            pos += 1

        # SLOT 2
        if pos < len(glyphs):
            if glyphs[pos] in SLOT2_RUNS:
                count = 0
                while pos < len(glyphs) and glyphs[pos] in SLOT2_RUNS and count < 3:
                    chunk.append(glyphs[pos]); pos += 1; count += 1
            elif glyphs[pos] in SLOT2_SINGLE:
                chunk.append(glyphs[pos]); pos += 1

        # SLOT 3
        if pos < len(glyphs) and glyphs[pos] in SLOT3:
            chunk.append(glyphs[pos]); pos += 1

        # SLOT 4
        if pos < len(glyphs):
            if glyphs[pos] in SLOT4_RUNS:
                count = 0
                while pos < len(glyphs) and glyphs[pos] in SLOT4_RUNS and count < 3:
                    chunk.append(glyphs[pos]); pos += 1; count += 1
            elif glyphs[pos] in SLOT4_SINGLE:
                chunk.append(glyphs[pos]); pos += 1

        # SLOT 5: coda — but EXCLUDE 'y' if next glyph could start a new chunk
        CODA_NO_Y = SLOT5 - {'y'}
        if pos < len(glyphs) and glyphs[pos] in CODA_NO_Y:
            chunk.append(glyphs[pos]); pos += 1
        elif pos < len(glyphs) and glyphs[pos] == 'y':
            # Only consume y as coda if it's the last glyph in the word
            if pos == len(glyphs) - 1:
                chunk.append(glyphs[pos]); pos += 1
            # else: leave y for next chunk as onset

        if pos == start:
            return None, pos
        return chunk, pos

    ambiguous = 0
    same_parse = 0
    different_chunks = 0
    total_testable = 0

    for w in all_words:
        glyphs = eva_to_glyphs(w)
        if 'y' not in glyphs:
            same_parse += 1
            continue
        total_testable += 1

        # Default parse
        chunks1, _, _ = parse_word_into_chunks(w)
        ids1 = [chunk_to_str(c) for c in chunks1]

        # Alternative parse
        chunks2 = []
        pos = 0
        while pos < len(glyphs):
            c, np_ = parse_chunk_y_onset(glyphs, pos)
            if c is None:
                pos += 1
            else:
                chunks2.append(c); pos = np_
        ids2 = [chunk_to_str(c) for c in chunks2]

        if ids1 != ids2:
            ambiguous += 1
            different_chunks += abs(len(ids1) - len(ids2))

    pr(f"  Words without 'y': {same_parse} (unambiguous by definition)")
    pr(f"  Words with 'y':    {total_testable}")
    pr(f"  Ambiguous parses:  {ambiguous} ({100*ambiguous/len(all_words):.1f}% of all words)")
    pr(f"  Same parse:        {total_testable - ambiguous}")
    pr()
    pr(f"  ASSESSMENT: If ambiguity < 10%, the greedy parse is robust.")
    pr(f"  If ambiguity > 20%, chunk-level statistics are parse-dependent.")
    pr()

    # ── STEP 10: SYNTHESIS ─────────────────────────────────────────────

    pr("─" * 76)
    pr("STEP 10: SYNTHESIS — DOES THE CHUNK HYPOTHESIS HOLD?")
    pr("─" * 76)
    pr()

    # Compute summary diagnostics
    # Is VMS chunk h_ratio in NL syllable range?
    if nl_syl_ratios:
        nl_syl_mean = np.mean(nl_syl_ratios)
        nl_syl_std = np.std(nl_syl_ratios, ddof=1)
        z_h = (vms_chunk_fp['h_ratio'] - nl_syl_mean) / nl_syl_std if nl_syl_std > 0 else float('nan')
    else:
        z_h = float('nan')
        nl_syl_mean = float('nan')

    pr(f"  TEST 1: Does chunk h_ratio land in NL syllable range?")
    pr(f"    VMS chunk h_ratio:  {vms_chunk_fp['h_ratio']:.4f}")
    pr(f"    NL syllable mean:   {nl_syl_mean:.4f} ± {nl_syl_std:.4f}")
    pr(f"    z-score:            {z_h:+.2f}")
    if abs(z_h) < 2:
        pr(f"    → WITHIN NL range (|z|<2) — consistent with syllabic hypothesis")
    else:
        pr(f"    → OUTSIDE NL range (|z|>2) — chunks are NOT behaving like NL syllables")
    pr()

    pr(f"  TEST 2: Is Mauro's grammar special? (vs shuffled grammars)")
    pr(f"    h_ratio z vs shuffled: {z_hr:+.2f}")
    pr(f"    coverage z vs shuffled: {z_cov:+.2f}")
    if abs(z_hr) < 2 and abs(z_cov) < 2:
        pr(f"    → NOT SPECIAL — any random grammar gives similar results")
        pr(f"      This INVALIDATES the chunk-level analysis!")
    elif abs(z_cov) > 2 and abs(z_hr) < 2:
        pr(f"    → Grammar has better COVERAGE but similar h_ratio")
        pr(f"      Coverage is expected (designed for VMS). h_ratio is not special.")
    else:
        pr(f"    → Grammar IS special: produces distinct chunk statistics")
    pr()

    pr(f"  TEST 3: Does char-shuffled VMS parse differently?")
    pr(f"    h_ratio z vs char-shuffled: {z_cs_hr:+.2f}")
    if abs(z_cs_hr) > 2:
        pr(f"    → YES: real VMS has different chunk structure than random")
        pr(f"      The chunk decomposition captures genuine word structure.")
    else:
        pr(f"    → NO: char-shuffled VMS gives similar chunk stats")
        pr(f"      Grammar is too flexible — parses anything similarly.")
    pr()

    pr(f"  TEST 4: Parse ambiguity")
    amb_pct = 100 * ambiguous / len(all_words)
    if amb_pct < 10:
        pr(f"    → LOW ({amb_pct:.1f}%) — chunk decomposition is robust")
    elif amb_pct < 20:
        pr(f"    → MODERATE ({amb_pct:.1f}%) — some parse instability")
    else:
        pr(f"    → HIGH ({amb_pct:.1f}%) — chunk stats may be unreliable")
    pr()

    # Overall verdict
    pr("─" * 76)
    pr("VERDICT")
    pr("─" * 76)
    pr()

    tests_passed = 0
    tests_total = 4
    if not math.isnan(z_h) and abs(z_h) < 2:
        tests_passed += 1
    if abs(z_hr) > 2:
        tests_passed += 1  # grammar IS special
    if abs(z_cs_hr) > 2:
        tests_passed += 1  # char-shuffle fails
    if amb_pct < 15:
        tests_passed += 1

    pr(f"  Tests passed: {tests_passed}/{tests_total}")
    pr()
    if tests_passed >= 3:
        pr(f"  ★ SUPPORTED: VMS chunks behave like NL syllables.")
        pr(f"    The h_char anomaly (0.641) is likely a unit-of-analysis artifact.")
        pr(f"    When measured at the correct atomic unit (chunk ≈ syllable),")
        pr(f"    VMS predictability falls in the natural language range.")
    elif tests_passed == 2:
        pr(f"  ◐ PARTIALLY SUPPORTED: Some chunk metrics match NL syllables,")
        pr(f"    but not all tests pass. The evidence is suggestive but incomplete.")
    elif tests_passed == 1:
        pr(f"  △ WEAK: Only one test passes. Chunk hypothesis is not well supported.")
    else:
        pr(f"  ✗ REFUTED: Chunks do NOT behave like NL syllables.")
        pr(f"    The h_char anomaly is real and not resolved by chunk decomposition.")
    pr()

    pr(f"  KEY NUMBERS FOR SYNTHESIS:")
    pr(f"    VMS h_char_ratio:        {h_char_ratio:.4f}")
    pr(f"    VMS h_chunk_ratio:       {vms_chunk_fp['h_ratio']:.4f}")
    if nl_syl_ratios:
        pr(f"    NL h_syllable_ratio:     {nl_syl_mean:.4f} ± {nl_syl_std:.4f}")
    if nl_char_ratios:
        pr(f"    NL h_char_ratio:         {np.mean(nl_char_ratios):.4f} ± {np.std(nl_char_ratios):.4f}")
    pr(f"    Chunk types:             {n_chunk_types}")
    pr(f"    Chunks/word:             {n_chunk_tokens/len(all_words):.3f}")
    pr(f"    Grammar coverage:        {coverage:.1f}%")
    pr(f"    Grammar specificity (z): h_ratio={z_hr:+.2f}, coverage={z_cov:+.2f}")
    pr(f"    Char-shuffle z:          {z_cs_hr:+.2f}")
    pr(f"    Parse ambiguity:         {amb_pct:.1f}%")
    pr()

    # Save output
    out_path = RESULTS_DIR / 'chunk_fingerprint.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Results saved to {out_path}")

    # Save JSON summary
    summary = {
        'vms_chunk': vms_chunk_fp,
        'vms_char': {'h_char': h_char, 'h_cond': h_char_cond, 'h_ratio': h_char_ratio},
        'vms_word': {k: vms_word_fp[k] for k in ['h_unigram', 'h_cond', 'h_ratio', 'n_types', 'hapax_ratio']},
        'nl_syllable': {n: {k: v for k, v in fp.items()} for n, fp in nl_syl_fingerprints.items()},
        'nl_char': nl_char_fingerprints,
        'null_shuffled_grammar': {
            'h_ratio_mean': float(np.mean(shuffle_h_ratios)),
            'h_ratio_std': float(np.std(shuffle_h_ratios)),
            'z_h_ratio': float(z_hr),
            'z_coverage': float(z_cov),
        },
        'null_char_shuffled': {
            'h_ratio_mean': float(np.mean(cs_h_ratios)),
            'h_ratio_std': float(np.std(cs_h_ratios)),
            'z_h_ratio': float(z_cs_hr),
        },
        'coverage_pct': coverage,
        'n_chunk_types': n_chunk_types,
        'chunks_per_word': n_chunk_tokens / len(all_words),
        'ambiguity_pct': amb_pct,
        'tests_passed': tests_passed,
    }
    json_path = RESULTS_DIR / 'chunk_fingerprint.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)


if __name__ == '__main__':
    main()
