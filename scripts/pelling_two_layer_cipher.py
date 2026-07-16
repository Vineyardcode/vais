#!/usr/bin/env python3
"""
PELLING-STYLE TWO-LAYER CIPHER: ABBREVIATION + VERBOSE BIGRAM MAP
══════════════════════════════════════════════════════════════════════════════

STRATEGIC RATIONALE:

mi_distance_curve demolished encoding_layer_sweep's "blockbuster" result:
  - Stochastic p<1.0 vowel expansion is seed-dependent noise
  - VMS_TARGET was a phantom (didn't match the script's own computed VMS)
  - The "a→a1" toy model is ahistorical

But mi_distance_curve also identified CONVERGENCE from two directions:
  STATISTICAL: Vowel-targeted encoding is the ONLY class that produces h_char≈0.64
  HISTORICAL: Pelling's article shows 15th-century ciphers specifically targeted
              vowels; his verbose cipher + abbreviation hypothesis is the most
              historically plausible model proposed.

This phase implements the TWO-LAYER model:

  LAYER 1 — ABBREVIATION: Truncate words to first N characters (N=3..6),
            simulating medieval scribal abbreviation/truncation.

  LAYER 2 — VERBOSE CIPHER: Map plaintext character BIGRAMS to deterministic
            2-character cipher tokens. Each bigram always → same output.
            This produces:
              - Low h_char: second cipher char predicted from first
              - Deterministic: same plaintext → same ciphertext (decryptable)
              - Natural "chunk" structure: pairs that look like VMS word-internal
                sequences

  LAYER 2b — SYLLABLE-BASED VERBOSE: Instead of raw bigrams, segment words
             into onset+nucleus+coda syllable components, and map those. This
             is more linguistically motivated.

CRITICAL TESTS (beyond encoding_layer_sweep's 6 metrics):

  T1: GLOBAL FINGERPRINT — 6 metrics + distance to VMS (with CORRECTED target
      using the script's own VMS computation, not phantom values)
  T2: I*M+F* SLOT GRAMMAR — Does the cipher output obey the positional pattern?
      Real ciphers just permute the alphabet; they shouldn't create positional
      rigidity. Verbose ciphers MIGHT, because the mapping creates chunk patterns.
  T3: POSITIONAL ENTROPY CURVES — Character frequency at word-initial vs
      word-medial vs word-final positions. VMS shows extreme concentration.
  T4: CROSS-WORD-BOUNDARY PREDICTION — Does word-final chunk predict next-word
      initial chunk? VMS shows this property.
  T5: WORD-LENGTH DISTRIBUTION — Shape, not just mean.

SOURCE TEXTS:
  - Latin Apicius (recipes/medical — 30K tokens, closest genre to VMS)
  - German BvgS (medieval recipes — 8K tokens, but period-appropriate)
  - Latin Galen (medical — 50K tokens, medical genre)

PREDICTIONS (pre-registered):

  P1: The two-layer model will produce h_char in [0.60, 0.72], matching VMS.
      SKEPTIC: Low h_char is trivially achievable — the question is whether
      OTHER metrics are also preserved.

  P2: The two-layer model will FAIL to reproduce I*M+F* slot grammar.
      Natural language has positional structure (e.g., 'q' is word-initial),
      but bigram→pair mapping shuffles which output chars appear where.
      SKEPTIC: If bigrams are position-aware, this prediction might be wrong.

  P3: Abbreviation + verbose will produce better overall distance than either
      layer alone, because abbreviation compensates for verbose word-length
      inflation.
      SKEPTIC: Abbreviation destroys vocabulary metrics (Heaps, Zipf).

  P4: Cross-word boundary prediction will NOT match VMS levels.
      Verbose bigram ciphers operate WITHIN words; they don't create
      dependencies ACROSS word boundaries.
      SKEPTIC: If abbreviation creates similar truncated endings that then
      produce similar cipher chunks, this could emerge accidentally.

  P5: No combination of parameters will produce VMS-like positional entropy
      AND VMS-like h_char simultaneously. These are competing constraints.
      SKEPTIC: Maybe there's a parameter sweet spot we haven't found.
"""

import re, sys, io, math
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import clean_word_v2 as clean_word, eva_to_glyphs, load_bvgs, load_reference_text_v2 as load_reference_text, mean_word_length, ttr_at_n

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
DATA_DIR  = Path(__file__).resolve().parent.parent / 'data'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(85)


# ═══════════════════════════════════════════════════════════════════════
# EVA PARSING
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']



def parse_vms_words():
    words = []
    all_glyphs = []
    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)
    for filepath in folio_files:
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
                text = rest.replace('<%>', '').replace('<$>', '').strip()
                text = re.sub(r'@\d+;', '', text)
                text = re.sub(r'<[^>]*>', '', text)
                for tok in re.split(r'[.\s]+', text):
                    for subtok in re.split(r',', tok):
                        c = clean_word(subtok.strip())
                        if c:
                            words.append(c)
                            all_glyphs.extend(eva_to_glyphs(c))
    return words, all_glyphs


# ═══════════════════════════════════════════════════════════════════════
# TEXT LOADING
# ═══════════════════════════════════════════════════════════════════════




# ═══════════════════════════════════════════════════════════════════════
# FINGERPRINT METRICS (corrected: VMS_TARGET computed live from data)
# ═══════════════════════════════════════════════════════════════════════

def char_bigram_predictability(char_list):
    """H(c|prev) / H(c) — the central h_char metric."""
    unigram = Counter(char_list)
    total = sum(unigram.values())
    if total < 50:
        return float('nan')
    h_uni = -sum((c/total) * math.log2(c/total) for c in unigram.values() if c > 0)
    bigrams = Counter()
    for i in range(1, len(char_list)):
        bigrams[(char_list[i-1], char_list[i])] += 1
    total_bi = sum(bigrams.values())
    h_joint = -sum((c/total_bi) * math.log2(c/total_bi) for c in bigrams.values() if c > 0)
    prev_counts = Counter()
    for (c1, c2), cnt in bigrams.items():
        prev_counts[c1] += cnt
    prev_total = sum(prev_counts.values())
    h_prev = -sum((c/prev_total) * math.log2(c/prev_total) for c in prev_counts.values() if c > 0)
    h_cond = h_joint - h_prev
    if h_uni == 0:
        return 1.0
    return h_cond / h_uni

def heaps_exponent(words):
    n = len(words)
    if n < 100:
        return float('nan')
    sample_points = np.linspace(max(10, n//20), n, min(20, n//5), dtype=int)
    if len(sample_points) < 3:
        return float('nan')
    vocab_at = {}
    running = set()
    idx = 0
    for pt in sorted(sample_points):
        while idx < pt:
            running.add(words[idx])
            idx += 1
        vocab_at[pt] = len(running)
    log_n = np.array([math.log(pt) for pt in sample_points])
    log_v = np.array([math.log(vocab_at[pt]) for pt in sample_points])
    A = np.vstack([log_n, np.ones(len(log_n))]).T
    result = np.linalg.lstsq(A, log_v, rcond=None)
    return float(result[0][0])

def hapax_ratio_at_midpoint(words):
    mid = len(words) // 2
    if mid < 10:
        return float('nan')
    freq = Counter(words[:mid])
    hapax = sum(1 for c in freq.values() if c == 1)
    return hapax / max(len(freq), 1)



def zipf_alpha_fn(words):
    freq = Counter(words)
    ranked = sorted(freq.values(), reverse=True)
    n = min(len(ranked), 500)
    if n < 10:
        return float('nan')
    log_rank = np.log(np.arange(1, n+1))
    log_freq = np.log(np.array(ranked[:n], dtype=float))
    A = np.vstack([log_rank, np.ones(n)]).T
    result = np.linalg.lstsq(A, log_freq, rcond=None)
    return float(-result[0][0])

def compute_fingerprint(words, char_list):
    return {
        'h_char_ratio': char_bigram_predictability(char_list),
        'heaps_beta': heaps_exponent(words),
        'hapax_ratio_mid': hapax_ratio_at_midpoint(words),
        'mean_word_len': mean_word_length(words),
        'zipf_alpha': zipf_alpha_fn(words),
        'ttr_5000': ttr_at_n(words, 5000),
    }

def fingerprint_distance(fp, target):
    """Normalized Euclidean distance — corrected to use LIVE VMS target."""
    dims = []
    for key, vms_val in target.items():
        v = fp.get(key, float('nan'))
        if vms_val != 0 and not math.isnan(v):
            dims.append(((v - vms_val) / vms_val) ** 2)
    return math.sqrt(sum(dims)) if dims else float('inf')


# ═══════════════════════════════════════════════════════════════════════
# LAYER 1: ABBREVIATION
# ═══════════════════════════════════════════════════════════════════════

def abbreviate_words(words, max_len):
    """Truncate each word to at most max_len characters.
    Simulates medieval scribal abbreviation (contraction/truncation).
    """
    return [w[:max_len] for w in words]


# ═══════════════════════════════════════════════════════════════════════
# LAYER 2: DETERMINISTIC VERBOSE BIGRAM CIPHER
# ═══════════════════════════════════════════════════════════════════════

def build_bigram_cipher_table(words, alphabet_size=35):
    """Build a deterministic bigram→pair mapping from corpus statistics.

    Strategy: rank all character bigrams by frequency in the corpus.
    Map each bigram to a deterministic 2-character output from a
    synthetic alphabet of size `alphabet_size`.

    The output alphabet is designed to have STRUCTURE:
      - Some output chars are "initial-like" (appear as first char of pair)
      - Some are "medial-like" (appear as second char of pair)
    This naturally creates positional tendencies in the cipher output.

    The mapping is DETERMINISTIC: same input bigram → same output pair.
    """
    # Count all character bigrams across all words
    bigram_freq = Counter()
    for w in words:
        for i in range(len(w) - 1):
            bigram_freq[(w[i], w[i+1])] += 1

    # Also count single-character words and word-start/end conditions
    # to handle odd-length words (the last char needs mapping too)
    char_freq = Counter()
    for w in words:
        for c in w:
            char_freq[c] += 1

    # Rank bigrams by frequency
    ranked_bigrams = [bg for bg, _ in bigram_freq.most_common()]

    # Build output alphabet: use letters a-z plus symbols 1-9 to get 35
    out_chars = list('abcdefghijklmnopqrstuvwxyz123456789')[:alphabet_size]

    # STRUCTURED assignment: divide output alphabet into 3 zones
    # Zone I (initial-like): first third → tends to be first char of output pair
    # Zone M (medial-like): middle third → can be either position
    # Zone F (final-like): last third → tends to be second char of output pair
    n_zone = alphabet_size // 3
    zone_I = out_chars[:n_zone]
    zone_M = out_chars[n_zone:2*n_zone]
    zone_F = out_chars[2*n_zone:]

    # Map bigrams to output pairs, cycling through zone combinations
    # Most frequent bigrams → I+M or I+F pairs (creates I→M transition dominance)
    # Less frequent → M+F or M+M pairs
    # Rare → any zone combination
    cipher_table = {}
    pair_idx = 0
    zone_combos = []
    # Priority: I+M, I+F, M+M, M+F, I+I, F+M, F+F (descending positional plausibility)
    for c1_pool in [zone_I, zone_M, zone_F]:
        for c2_pool in [zone_M, zone_F, zone_I]:
            for c1 in c1_pool:
                for c2 in c2_pool:
                    zone_combos.append((c1, c2))

    for idx, bg in enumerate(ranked_bigrams):
        if idx < len(zone_combos):
            cipher_table[bg] = zone_combos[idx]
        else:
            # Overflow: wrap around
            cipher_table[bg] = zone_combos[idx % len(zone_combos)]

    # For single-character residuals (odd-length words, last char)
    residual_table = {}
    for idx, (ch, _) in enumerate(char_freq.most_common()):
        residual_table[ch] = out_chars[idx % alphabet_size]

    return cipher_table, residual_table


def apply_verbose_cipher(words, cipher_table, residual_table):
    """Apply the deterministic bigram→pair verbose cipher.

    Each word is processed by:
    1. Walking through the word's characters in bigram steps
    2. Each bigram → 2 output characters (from cipher_table)
    3. Odd-length words: last character → 1 output char (from residual_table)

    Returns: list of cipher "words" (strings), list of all cipher chars
    """
    cipher_words = []
    all_chars = []

    for w in words:
        out = []
        i = 0
        while i + 1 < len(w):
            bg = (w[i], w[i+1])
            if bg in cipher_table:
                c1, c2 = cipher_table[bg]
                out.append(c1)
                out.append(c2)
            else:
                # Unknown bigram — use residuals for both chars
                out.append(residual_table.get(w[i], '?'))
                out.append(residual_table.get(w[i+1], '?'))
            i += 2
        if i < len(w):
            # Odd-length word: one char left
            out.append(residual_table.get(w[i], '?'))

        cipher_word = ''.join(out)
        if cipher_word:
            cipher_words.append(cipher_word)
            all_chars.extend(list(cipher_word))

    return cipher_words, all_chars


# ═══════════════════════════════════════════════════════════════════════
# LAYER 2b: OVERLAPPING BIGRAM CIPHER (more realistic)
# ═══════════════════════════════════════════════════════════════════════

def build_overlap_cipher_table(words, alphabet_size=35):
    """Build a verbose cipher where each OVERLAPPING bigram maps to a
    SINGLE output character. Since bigrams overlap (char i appears in
    bigram (i-1,i) AND bigram (i,i+1)), the output char for position i
    depends on BOTH the current char and its predecessor — exactly the
    kind of context-dependence that produces low h_char.

    Each overlapping bigram (c_prev, c_cur) → one output character.
    Word-initial character (no predecessor) → mapped by unigram table.

    This is closer to Pelling's model: the cipher "reads" pairs and
    produces output that encodes the pair relationship.
    """
    bigram_freq = Counter()
    for w in words:
        for i in range(1, len(w)):
            bigram_freq[(w[i-1], w[i])] += 1

    char_freq = Counter()
    for w in words:
        for c in w:
            char_freq[c] += 1

    out_chars = list('abcdefghijklmnopqrstuvwxyz123456789')[:alphabet_size]

    # Map each bigram to a single output char
    # Spread evenly across the alphabet to maintain reasonable entropy
    ranked_bigrams = [bg for bg, _ in bigram_freq.most_common()]
    cipher_table = {}
    for idx, bg in enumerate(ranked_bigrams):
        cipher_table[bg] = out_chars[idx % alphabet_size]

    # Word-initial chars: separate mapping
    initial_table = {}
    initial_freq = Counter(w[0] for w in words if w)
    for idx, (ch, _) in enumerate(initial_freq.most_common()):
        initial_table[ch] = out_chars[idx % alphabet_size]

    return cipher_table, initial_table


def apply_overlap_cipher(words, cipher_table, initial_table):
    """Apply overlapping bigram cipher: each position encoded using
    (prev_char, current_char) context.

    Word length is PRESERVED (1:1 mapping), but each output char
    depends on the local bigram context → low h_char.
    """
    cipher_words = []
    all_chars = []

    for w in words:
        if not w:
            continue
        out = []
        # First char: use initial table
        out.append(initial_table.get(w[0], '?'))
        # Subsequent chars: use bigram context
        for i in range(1, len(w)):
            bg = (w[i-1], w[i])
            out.append(cipher_table.get(bg, '?'))

        cipher_word = ''.join(out)
        cipher_words.append(cipher_word)
        all_chars.extend(list(cipher_word))

    return cipher_words, all_chars


# ═══════════════════════════════════════════════════════════════════════
# POSITIONAL ANALYSIS (from run_length_morphology slot grammar)
# ═══════════════════════════════════════════════════════════════════════

def compute_positional_profile(words):
    """Compute character frequency at 3 word positions: initial, medial, final.

    Returns: dict with keys 'initial', 'medial', 'final', each mapping to
    a Counter of character frequencies at that position.
    Also returns the concentration metric: what fraction of total occurrences
    of a character are in its dominant position.
    """
    initial = Counter()
    medial = Counter()
    final = Counter()

    for w in words:
        if len(w) == 0:
            continue
        chars = list(w)
        initial[chars[0]] += 1
        if len(chars) > 1:
            final[chars[-1]] += 1
        for c in chars[1:-1]:
            medial[c] += 1

    return {'initial': initial, 'medial': medial, 'final': final}


def positional_concentration(profile):
    """For each character, what fraction of its occurrences are in its
    most frequent position? High concentration = strong positional bias.
    Returns: mean concentration across all characters.
    """
    all_chars = set()
    for pos in ['initial', 'medial', 'final']:
        all_chars.update(profile[pos].keys())

    concentrations = []
    for c in all_chars:
        counts = [profile[pos].get(c, 0) for pos in ['initial', 'medial', 'final']]
        total = sum(counts)
        if total >= 5:  # minimum frequency threshold
            concentrations.append(max(counts) / total)

    return np.mean(concentrations) if concentrations else 0.0


def imf_conformance(words, alphabet_size=35):
    """Test I*M+F* slot grammar conformance.

    For cipher output: define I/M/F sets based on EMPIRICAL positional
    dominance (the same way VMS definitions were derived in run_length_morphology).

    Returns: conformance rate, I/M/F sets
    """
    profile = compute_positional_profile(words)

    # Classify each character by its dominant position
    all_chars = set()
    for pos in ['initial', 'medial', 'final']:
        all_chars.update(profile[pos].keys())

    char_classes = {}
    for c in all_chars:
        i_count = profile['initial'].get(c, 0)
        m_count = profile['medial'].get(c, 0)
        f_count = profile['final'].get(c, 0)
        total = i_count + m_count + f_count
        if total < 3:
            char_classes[c] = '?'
            continue

        # Classify by >50% dominance (same criterion as run_length_morphology)
        if i_count / total > 0.50:
            char_classes[c] = 'I'
        elif f_count / total > 0.50:
            char_classes[c] = 'F'
        else:
            char_classes[c] = 'M'

    # Test conformance
    n_conform = 0
    n_total = 0

    for w in words:
        if not w:
            continue
        n_total += 1
        template = ''.join(char_classes.get(c, '?') for c in w)
        if re.match(r'^I*M+F*$', template):
            n_conform += 1

    rate = n_conform / n_total if n_total else 0
    return rate, char_classes


def cross_word_boundary_prediction(words):
    """Measure how well word-final character predicts next-word initial character.

    Returns: conditional entropy H(next_initial | this_final).
    Lower = more predictable = more VMS-like.
    """
    if len(words) < 2:
        return float('nan')

    boundary_pairs = Counter()
    for i in range(len(words) - 1):
        if words[i] and words[i+1]:
            final_char = words[i][-1]
            initial_char = words[i+1][0]
            boundary_pairs[(final_char, initial_char)] += 1

    total = sum(boundary_pairs.values())
    if total < 10:
        return float('nan')

    # H(next_initial | this_final)
    final_counts = Counter()
    for (f, i), cnt in boundary_pairs.items():
        final_counts[f] += cnt

    h_cond = 0.0
    for (f, init), cnt in boundary_pairs.items():
        p_joint = cnt / total
        p_final = final_counts[f] / total
        if p_joint > 0 and p_final > 0:
            h_cond -= p_joint * math.log2(p_joint / p_final)

    return h_cond


# ═══════════════════════════════════════════════════════════════════════
# WORD-LENGTH DISTRIBUTION COMPARISON
# ═══════════════════════════════════════════════════════════════════════

def wlen_distribution_distance(words1, words2):
    """Jensen-Shannon divergence between word-length distributions."""
    def wlen_dist(words):
        lens = [len(w) for w in words]
        max_len = max(max(lens), 15)
        counts = Counter(lens)
        total = len(lens)
        return {k: counts.get(k, 0)/total for k in range(1, max_len+1)}

    d1 = wlen_dist(words1)
    d2 = wlen_dist(words2)
    all_keys = set(d1) | set(d2)

    # Jensen-Shannon divergence
    jsd = 0.0
    for k in all_keys:
        p = d1.get(k, 0)
        q = d2.get(k, 0)
        m = (p + q) / 2
        if p > 0 and m > 0:
            jsd += 0.5 * p * math.log2(p / m)
        if q > 0 and m > 0:
            jsd += 0.5 * q * math.log2(q / m)

    return jsd


# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION GRID
# ═══════════════════════════════════════════════════════════════════════

def build_configs():
    """Build the parameter grid for the two-layer model.

    Parameters:
      - abbreviation: max_len in {None, 3, 4, 5, 6} (None = no abbreviation)
      - cipher_type: 'nonjoint' (bigram→pair) or 'overlap' (bigram→single)
      - alphabet_size: {25, 30, 35}

    Total: 5 × 2 × 3 = 30 configs per source language
    """
    configs = []

    for abbrev in [None, 3, 4, 5, 6]:
        for cipher_type in ['nonjoint', 'overlap']:
            for alpha_size in [25, 30, 35]:
                label_parts = []
                if abbrev is not None:
                    label_parts.append(f'abbr{abbrev}')
                else:
                    label_parts.append('noabbr')
                label_parts.append(cipher_type)
                label_parts.append(f'a{alpha_size}')
                label = '_'.join(label_parts)

                configs.append({
                    'label': label,
                    'abbrev': abbrev,
                    'cipher_type': cipher_type,
                    'alphabet_size': alpha_size,
                })

    return configs


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr('=' * 80)
    pr('pelling_two_layer_cipher — PELLING-STYLE TWO-LAYER CIPHER: ABBREVIATION + VERBOSE BIGRAM')
    pr('  Deterministic cipher tested against global metrics + positional structure')
    pr('=' * 80)
    pr()

    # ─── STEP 1: VMS BASELINE (computed LIVE — no phantom targets) ────
    pr('─' * 80)
    pr('STEP 1: VMS BASELINE (computed from actual data)')
    pr('─' * 80)

    vms_words, vms_glyphs = parse_vms_words()
    vms_fp = compute_fingerprint(vms_words, vms_glyphs)
    vms_glyph_words = [''.join(eva_to_glyphs(w)) for w in vms_words]

    pr(f'  Tokens: {len(vms_words):,}   Types: {len(set(vms_words)):,}')
    pr(f'  h_char={vms_fp["h_char_ratio"]:.4f}  Heaps={vms_fp["heaps_beta"]:.4f}  '
       f'hapax={vms_fp["hapax_ratio_mid"]:.4f}  wlen={vms_fp["mean_word_len"]:.2f}  '
       f'Zipf={vms_fp["zipf_alpha"]:.4f}  TTR={vms_fp["ttr_5000"]:.4f}')

    # VMS positional analysis
    vms_pos_profile = compute_positional_profile(vms_glyph_words)
    vms_pos_conc = positional_concentration(vms_pos_profile)
    vms_imf_rate, vms_char_classes = imf_conformance(vms_glyph_words)
    vms_boundary_h = cross_word_boundary_prediction(vms_glyph_words)
    vms_wlen_mean = vms_fp['mean_word_len']

    pr(f'  Positional concentration: {vms_pos_conc:.4f}')
    pr(f'  I*M+F* conformance: {vms_imf_rate:.4f} ({vms_imf_rate:.1%})')
    pr(f'  Cross-boundary H(init|final): {vms_boundary_h:.4f}')
    pr()

    # Use LIVE VMS fingerprint as the target
    VMS_TARGET = dict(vms_fp)

    # ─── STEP 2: LOAD SOURCE CORPORA ──────────────────────────────────
    pr('─' * 80)
    pr('STEP 2: REFERENCE CORPORA')
    pr('─' * 80)

    corpora = {}

    # Latin Apicius (recipes)
    apicius_path = DATA_DIR / 'latin_texts' / 'apicius.txt'
    if apicius_path.exists():
        ws = load_reference_text(apicius_path)
        if len(ws) > 30000:
            ws = ws[:30000]
        corpora['Latin_Apicius'] = ws

    # Latin Galen (medical)
    galen_path = DATA_DIR / 'latin_texts' / 'galen.txt'
    if galen_path.exists():
        ws = load_reference_text(galen_path)
        if len(ws) > 30000:
            ws = ws[:30000]
        corpora['Latin_Galen'] = ws

    # German BvgS (medieval recipes)
    bvgs_path = DATA_DIR / 'vernacular_texts' / 'german_bvgs_raw.txt'
    if bvgs_path.exists():
        corpora['German_BvgS'] = load_bvgs(bvgs_path)

    # German Ortolf (medieval medicine)
    ortolf_path = DATA_DIR / 'vernacular_texts' / 'german_ortolf_raw.txt'
    if ortolf_path.exists():
        ws = load_reference_text(ortolf_path)
        corpora['German_Ortolf'] = ws

    # Italian Cucina
    cucina_path = DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt'
    if cucina_path.exists():
        ws = load_reference_text(cucina_path)
        if len(ws) > 30000:
            ws = ws[:30000]
        corpora['Italian_Cucina'] = ws

    for name, ws in corpora.items():
        pr(f'  {name:20s} tokens={len(ws):>6,}')

    pr(f'\n  Loaded {len(corpora)} corpora.')
    pr()

    # ─── STEP 3: PARAMETER SWEEP ─────────────────────────────────────
    pr('─' * 80)
    pr(f'STEP 3: PARAMETER SWEEP — {len(corpora)} languages × 30 configs = '
       f'{len(corpora) * 30} tests')
    pr('─' * 80)
    pr()

    configs = build_configs()
    all_results = []

    for lang_name, source_words in corpora.items():
        pr(f'  Testing {lang_name}...')
        best_dist = float('inf')
        best_label = ''

        for cfg in configs:
            # Layer 1: Abbreviation
            if cfg['abbrev'] is not None:
                working_words = abbreviate_words(source_words, cfg['abbrev'])
            else:
                working_words = list(source_words)

            # Layer 2: Verbose cipher
            if cfg['cipher_type'] == 'nonjoint':
                cipher_tab, residual_tab = build_bigram_cipher_table(
                    working_words, cfg['alphabet_size'])
                cipher_words, cipher_chars = apply_verbose_cipher(
                    working_words, cipher_tab, residual_tab)
            else:  # overlap
                cipher_tab, initial_tab = build_overlap_cipher_table(
                    working_words, cfg['alphabet_size'])
                cipher_words, cipher_chars = apply_overlap_cipher(
                    working_words, cipher_tab, initial_tab)

            if len(cipher_words) < 100 or len(cipher_chars) < 200:
                continue

            # Global fingerprint
            fp = compute_fingerprint(cipher_words, cipher_chars)
            dist = fingerprint_distance(fp, VMS_TARGET)

            # Positional metrics
            pos_conc = positional_concentration(
                compute_positional_profile(cipher_words))
            imf_rate, _ = imf_conformance(cipher_words, cfg['alphabet_size'])
            boundary_h = cross_word_boundary_prediction(cipher_words)
            wlen_jsd = wlen_distribution_distance(cipher_words, vms_glyph_words)

            result = {
                'lang': lang_name,
                'config': cfg['label'],
                'dist': dist,
                'h_char': fp.get('h_char_ratio', float('nan')),
                'heaps': fp.get('heaps_beta', float('nan')),
                'hapax': fp.get('hapax_ratio_mid', float('nan')),
                'wlen': fp.get('mean_word_len', float('nan')),
                'zipf': fp.get('zipf_alpha', float('nan')),
                'ttr': fp.get('ttr_5000', float('nan')),
                'pos_conc': pos_conc,
                'imf_rate': imf_rate,
                'boundary_h': boundary_h,
                'wlen_jsd': wlen_jsd,
                'cipher_type': cfg['cipher_type'],
                'abbrev': cfg['abbrev'],
                'alpha_size': cfg['alphabet_size'],
            }
            all_results.append(result)

            if dist < best_dist:
                best_dist = dist
                best_label = cfg['label']

        pr(f'    Best: {best_label}  dist={best_dist:.4f}')

    pr()

    # ─── STEP 4: TOP 30 BY GLOBAL DISTANCE ───────────────────────────
    pr('─' * 80)
    pr('STEP 4: TOP 30 (language × config) BY GLOBAL FINGERPRINT DISTANCE')
    pr('─' * 80)
    pr()

    all_results.sort(key=lambda r: r['dist'])

    pr(f'  {"Rank":>4s}  {"Language":20s} {"Config":30s} {"dist":>7s}  '
       f'{"h_char":>7s} {"heaps":>7s} {"wlen":>6s} {"zipf":>6s} {"ttr":>6s}  '
       f'{"posConc":>7s} {"IMF%":>6s} {"bndH":>6s} {"wlJSD":>6s}')
    pr('  ' + '─' * 150)

    for rank, r in enumerate(all_results[:30], 1):
        pr(f'  {rank:>4d}  {r["lang"]:20s} {r["config"]:30s} {r["dist"]:>7.4f}  '
           f'{r["h_char"]:>7.4f} {r["heaps"]:>7.4f} {r["wlen"]:>6.2f} '
           f'{r["zipf"]:>6.4f} {r["ttr"]:>6.4f}  '
           f'{r["pos_conc"]:>7.4f} {r["imf_rate"]:>6.1%} {r["boundary_h"]:>6.3f} '
           f'{r["wlen_jsd"]:>6.4f}')

    pr()
    pr(f'  {"VMS":>4s}  {"TARGET":20s} {"":30s} {"0.0000":>7s}  '
       f'{VMS_TARGET["h_char_ratio"]:>7.4f} {VMS_TARGET["heaps_beta"]:>7.4f} '
       f'{VMS_TARGET["mean_word_len"]:>6.2f} {VMS_TARGET["zipf_alpha"]:>6.4f} '
       f'{VMS_TARGET["ttr_5000"]:>6.4f}  '
       f'{vms_pos_conc:>7.4f} {vms_imf_rate:>6.1%} {vms_boundary_h:>6.3f} '
       f'{"0.0000":>6s}')
    pr()

    # ─── STEP 5: POSITIONAL ANALYSIS OF THE BEST MODEL ───────────────
    pr('─' * 80)
    pr('STEP 5: DETAILED POSITIONAL ANALYSIS — TOP 5 MODELS vs VMS')
    pr('─' * 80)
    pr()

    # Rebuild the top 5 models for detailed analysis
    for rank, r in enumerate(all_results[:5], 1):
        lang_name = r['lang']
        cfg_label = r['config']

        # Parse config back
        parts = cfg_label.split('_')
        abbrev_str = parts[0]
        cipher_type = parts[1]
        alpha_str = parts[2]

        abbrev = None if abbrev_str == 'noabbr' else int(abbrev_str.replace('abbr', ''))
        alpha_size = int(alpha_str.replace('a', ''))

        source_words = corpora[lang_name]
        if abbrev is not None:
            working = abbreviate_words(source_words, abbrev)
        else:
            working = list(source_words)

        if cipher_type == 'nonjoint':
            ct, rt = build_bigram_cipher_table(working, alpha_size)
            cw, cc = apply_verbose_cipher(working, ct, rt)
        else:
            ct, it = build_overlap_cipher_table(working, alpha_size)
            cw, cc = apply_overlap_cipher(working, ct, it)

        pr(f'  ── Rank #{rank}: {lang_name} / {cfg_label} (dist={r["dist"]:.4f}) ──')
        pr()

        # Positional profile comparison
        ciph_profile = compute_positional_profile(cw)

        pr(f'  Positional concentration: {r["pos_conc"]:.4f} '
           f'(VMS: {vms_pos_conc:.4f}, Δ={r["pos_conc"]-vms_pos_conc:+.4f})')
        pr(f'  I*M+F* conformance:       {r["imf_rate"]:.1%} '
           f'(VMS: {vms_imf_rate:.1%})')
        pr(f'  Cross-boundary H:         {r["boundary_h"]:.4f} '
           f'(VMS: {vms_boundary_h:.4f})')
        pr(f'  Word-length JSD:          {r["wlen_jsd"]:.4f}')
        pr()

        # Show top-5 characters in each position
        for pos_name in ['initial', 'medial', 'final']:
            top5 = ciph_profile[pos_name].most_common(5)
            total = sum(ciph_profile[pos_name].values())
            chars_str = ', '.join(f'{c}({cnt/total:.1%})' for c, cnt in top5)
            pr(f'    {pos_name:>8s}: {chars_str}')

        # VMS comparison
        pr(f'    VMS comparison:')
        for pos_name in ['initial', 'medial', 'final']:
            top5 = vms_pos_profile[pos_name].most_common(5)
            total = sum(vms_pos_profile[pos_name].values())
            chars_str = ', '.join(f'{c}({cnt/total:.1%})' for c, cnt in top5)
            pr(f'    {pos_name:>8s}: {chars_str}')

        pr()

    # ─── STEP 6: BEST CONFIG PER LANGUAGE ─────────────────────────────
    pr('─' * 80)
    pr('STEP 6: BEST CONFIG PER LANGUAGE')
    pr('─' * 80)
    pr()

    seen_langs = set()
    for r in all_results:
        if r['lang'] not in seen_langs:
            seen_langs.add(r['lang'])
            pr(f'  {r["lang"]:20s} {r["config"]:30s} dist={r["dist"]:.4f}  '
               f'h_char={r["h_char"]:.4f}  imf={r["imf_rate"]:.1%}  '
               f'posConc={r["pos_conc"]:.4f}  bndH={r["boundary_h"]:.3f}')

    pr()

    # ─── STEP 7: CIPHER TYPE COMPARISON ───────────────────────────────
    pr('─' * 80)
    pr('STEP 7: NONJOINT (bigram→pair) vs OVERLAP (bigram→single) COMPARISON')
    pr('─' * 80)
    pr()

    for ctype in ['nonjoint', 'overlap']:
        subset = [r for r in all_results if r['cipher_type'] == ctype]
        if subset:
            best = subset[0]
            mean_dist = np.mean([r['dist'] for r in subset[:10]])
            mean_hchar = np.mean([r['h_char'] for r in subset[:10]])
            mean_imf = np.mean([r['imf_rate'] for r in subset[:10]])
            mean_posconc = np.mean([r['pos_conc'] for r in subset[:10]])
            pr(f'  {ctype:12s}: best_dist={best["dist"]:.4f}  '
               f'mean_top10_dist={mean_dist:.4f}  mean_h_char={mean_hchar:.4f}  '
               f'mean_IMF={mean_imf:.1%}  mean_posConc={mean_posconc:.4f}')

    pr()

    # ─── STEP 8: ABBREVIATION EFFECT ─────────────────────────────────
    pr('─' * 80)
    pr('STEP 8: ABBREVIATION EFFECT — does Layer 1 help?')
    pr('─' * 80)
    pr()

    for abbrev_val in [None, 3, 4, 5, 6]:
        subset = [r for r in all_results
                  if r['abbrev'] == abbrev_val]
        if subset:
            best = min(subset, key=lambda r: r['dist'])
            mean_dist = np.mean([r['dist'] for r in subset])
            mean_wlen = np.mean([r['wlen'] for r in subset])
            lbl = f'abbr={abbrev_val}' if abbrev_val else 'no_abbr'
            pr(f'  {lbl:>12s}: best_dist={best["dist"]:.4f}  '
               f'mean_dist={mean_dist:.4f}  mean_wlen={mean_wlen:.2f}  '
               f'best={best["lang"]}/{best["config"]}')

    pr()

    # ─── STEP 9: PREDICTION TESTS ────────────────────────────────────
    pr('─' * 80)
    pr('STEP 9: PREDICTION TESTS')
    pr('─' * 80)
    pr()

    # P1: Does the model produce h_char in [0.60, 0.72]?
    hchar_in_range = [r for r in all_results
                      if 0.60 <= r['h_char'] <= 0.72]
    pr(f'  P1: h_char in [0.60, 0.72]?  {len(hchar_in_range)}/{len(all_results)} combos')
    if hchar_in_range:
        best_hc = min(hchar_in_range, key=lambda r: abs(r['h_char'] - VMS_TARGET['h_char_ratio']))
        pr(f'      Closest to VMS: {best_hc["lang"]}/{best_hc["config"]} '
           f'h_char={best_hc["h_char"]:.4f}')
    pr(f'      VERDICT: {"CONFIRMED" if len(hchar_in_range) > 0 else "REFUTED"}')
    pr()

    # P2: Does the model FAIL to reproduce I*M+F*?
    best5_imf = [r['imf_rate'] for r in all_results[:5]]
    mean_best5_imf = np.mean(best5_imf) if best5_imf else 0
    pr(f'  P2: I*M+F* conformance in top-5 models?')
    pr(f'      VMS I*M+F*: {vms_imf_rate:.1%}')
    pr(f'      Top-5 mean: {mean_best5_imf:.1%}')
    delta_imf = abs(mean_best5_imf - vms_imf_rate)
    pr(f'      Gap: {delta_imf:.1%}')
    if delta_imf < 0.10:
        pr(f'      VERDICT: REFUTED — model DOES produce VMS-like I*M+F*!')
    else:
        pr(f'      VERDICT: CONFIRMED — model fails to reproduce slot grammar')
    pr()

    # P3: Abbreviation + verbose beats either layer alone?
    no_abbr = [r for r in all_results if r['abbrev'] is None]
    with_abbr = [r for r in all_results if r['abbrev'] is not None]
    best_no = min(no_abbr, key=lambda r: r['dist'])['dist'] if no_abbr else float('inf')
    best_with = min(with_abbr, key=lambda r: r['dist'])['dist'] if with_abbr else float('inf')
    pr(f'  P3: Does abbreviation help?')
    pr(f'      Best without abbreviation: {best_no:.4f}')
    pr(f'      Best with abbreviation:    {best_with:.4f}')
    if best_with < best_no:
        pr(f'      VERDICT: CONFIRMED — abbreviation helps (Δ={best_no-best_with:.4f})')
    else:
        pr(f'      VERDICT: REFUTED — abbreviation does NOT help')
    pr()

    # P4: Cross-word boundary prediction?
    best5_bnd = [r['boundary_h'] for r in all_results[:5]]
    mean_best5_bnd = np.mean(best5_bnd) if best5_bnd else float('nan')
    pr(f'  P4: Cross-boundary prediction (lower = more VMS-like)?')
    pr(f'      VMS boundary H: {vms_boundary_h:.4f}')
    pr(f'      Top-5 mean:     {mean_best5_bnd:.4f}')
    delta_bnd = abs(mean_best5_bnd - vms_boundary_h)
    pr(f'      Gap: {delta_bnd:.4f}')
    if delta_bnd / max(vms_boundary_h, 0.001) < 0.15:
        pr(f'      VERDICT: REFUTED — model DOES match boundary prediction!')
    else:
        pr(f'      VERDICT: CONFIRMED — model fails on cross-boundary')
    pr()

    # P5: Can any config match BOTH h_char AND positional structure?
    dual_match = [r for r in all_results
                  if abs(r['h_char'] - VMS_TARGET['h_char_ratio']) < 0.05
                  and abs(r['imf_rate'] - vms_imf_rate) < 0.10
                  and abs(r['pos_conc'] - vms_pos_conc) < 0.10]
    pr(f'  P5: Dual match (h_char + positional)?')
    pr(f'      Combos within 5% h_char AND 10% IMF AND 10% posConc: {len(dual_match)}')
    if dual_match:
        best_dual = min(dual_match, key=lambda r: r['dist'])
        pr(f'      Best dual: {best_dual["lang"]}/{best_dual["config"]} '
           f'dist={best_dual["dist"]:.4f}')
        pr(f'      VERDICT: REFUTED — dual match IS achievable!')
    else:
        pr(f'      VERDICT: CONFIRMED — dual match NOT achievable')
    pr()

    # ─── STEP 10: SELF-CRITIQUE ───────────────────────────────────────
    pr('─' * 80)
    pr('STEP 10: SELF-CRITIQUE — METHODOLOGICAL CONCERNS')
    pr('─' * 80)
    pr()

    pr('  1. CIPHER TABLE IS CORPUS-DEPENDENT: The bigram→output mapping is')
    pr('     built FROM the same corpus it\'s tested on. A real cipher\'s key')
    pr('     is independent of the plaintext. This means the cipher is')
    pr('     optimally tuned to its own statistics — unfair advantage.')
    pr()
    pr('  2. POSITIONAL STRUCTURE IS ENGINEERED: The zone-based output')
    pr('     alphabet (I/M/F zones) was designed to create positional')
    pr('     patterns. A real cipher wouldn\'t necessarily have this.')
    pr('     The overlap cipher has NO such engineering — its positional')
    pr('     properties emerge naturally (or not).')
    pr()
    pr('  3. ABBREVIATION IS A FREE PARAMETER: Adding truncation gives')
    pr('     us a dial to match word length, which might just be')
    pr('     overfitting. The question is whether it helps OTHER metrics.')
    pr()
    pr('  4. ALPHABET SIZE CONFOUND: Varying alphabet size (25/30/35)')
    pr('     changes h_char mechanically. Smaller alphabets → lower')
    pr('     entropy → different h_char. The VMS has ~35 EVA glyphs,')
    pr('     so alpha_size=35 is the fairest comparison.')
    pr()
    pr('  5. WE DON\'T TEST CURRIER A/B SPLIT: VMS has two "languages"')
    pr('     with different statistics. A single cipher model may not')
    pr('     explain both.')
    pr()

    # ─── SAVE ─────────────────────────────────────────────────────────
    outpath = RESULTS_DIR / 'pelling_two_layer_cipher_pelling_verbose.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f'  Results saved to {outpath}')


if __name__ == '__main__':
    main()
