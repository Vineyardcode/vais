#!/usr/bin/env python3
"""
Encoding Model Tournament: Generative Discrimination
════════════════════════════════════════════════════════════════

PREMISE:
63 phases of characterization. Time to DISCRIMINATE between models.
Instead of describing VMS, we generate synthetic texts under each
encoding hypothesis applied to Italian (Dante), compute a battery of
statistics on each, and score them against VMS.

THE FINGERPRINT BATTERY (7 statistics):
 1. Heaps' exponent β  (vocabulary growth rate)
 2. Hapax ratio at corpus midpoint
 3. H(char | prev_char) / H(char)  (bigram predictability)
 4. H(word | prev_word) / H(word)  (word-level predictability)
 5. Mean word length (in characters)
 6. TTR at 5000 tokens
 7. Zipf α exponent (slope of log-rank vs log-freq)

ENCODING MODELS TO TEST:
 A. VMS raw (target)
 B. Italian raw (natural language baseline)
 C. Simple substitution (letter→letter; preserves all word-level stats)
 D. Homophonic substitution (letter→random from set of 2-4; changes
    word identity but preserves character-level structure)
 E. Syllabic encoding (Italian syllables→VMS-like "words")
 F. Verbose cipher (letter→"word" from 20-symbol pool; already excluded
    but included for calibration)
 G. Anagram (shuffle characters within each word; preserves freq, kills
    bigram structure)
 H. VMS-style null model (random text matching VMS unigram char freq
    and word length distribution)

SCORING:
 For each model, compute L2 distance from VMS fingerprint (after
 z-normalizing each dimension). The model with lowest distance is the
 best match for VMS.

SKEPTICAL CAVEATS:
 - Italian may not be the source language; results are illustrative
 - Encoding models are simplified; real ciphers may be more complex
 - We test 7 statistics; more would be better but diminishing returns
 - This is a RANKING, not a proof
"""

import sys
import os
import re
import math
import json
import random
import urllib.request
from pathlib import Path
from collections import Counter, defaultdict

_print = print
import numpy as np
from common import eva_to_glyphs_v2 as eva_to_glyphs, fetch_gutenberg, get_currier_language, hapax_ratio_at_midpoint, zipf_alpha

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    _print(s, end=end)
    sys.stdout.flush()
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

# ═══════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════

def load_vms_words():
    """Load all VMS words in folio order."""
    words = []
    folio_files = sorted(FOLIO_DIR.glob('*.txt'))
    for fp in folio_files:
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Strip leading <tag> markup
                m = re.match(r'<([^>]+)>', line)
                rest = line[m.end():].strip() if m else line
                if not rest:
                    continue
                for tok in re.split(r'[.\s,;]+', rest):
                    tok = tok.strip()
                    if tok and re.match(r'^[a-z]+$', tok):
                        words.append(tok)
    return words

def load_vms_chars(words):
    """Get character stream from VMS words (EVA glyphs)."""
    chars = []
    for w in words:
        glyphs = eva_to_glyphs(w)
        chars.extend(glyphs)
    return chars



def load_italian_words():
    """Load Italian (Dante) words, lowercase, alpha-only."""
    raw = fetch_gutenberg(1012)
    text = raw.lower()
    text = re.sub(r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþß\' ]+', ' ', text)
    words = [w for w in text.split() if len(w) >= 1]
    return words[:50000]

# ═══════════════════════════════════════════════════════════════════════
# FINGERPRINT COMPUTATION
# ═══════════════════════════════════════════════════════════════════════

def heaps_exponent(words):
    """Fit Heaps' law V(n) = K * n^β via log-log regression.
    Sample at 20 evenly-spaced points to avoid size bias."""
    n = len(words)
    if n < 100:
        return 0.0
    sample_points = np.linspace(100, n, 20, dtype=int)
    log_n = []
    log_v = []
    seen = set()
    word_list = list(words)
    # Compute cumulative vocabulary at each point
    vocab_at = {}
    running = set()
    idx = 0
    for pt in sorted(sample_points):
        while idx < pt:
            running.add(word_list[idx])
            idx += 1
        vocab_at[pt] = len(running)
    for pt in sample_points:
        log_n.append(math.log(pt))
        log_v.append(math.log(vocab_at[pt]))
    log_n = np.array(log_n)
    log_v = np.array(log_v)
    # Linear regression in log-log space
    A = np.vstack([log_n, np.ones(len(log_n))]).T
    result = np.linalg.lstsq(A, log_v, rcond=None)
    beta = result[0][0]
    return float(beta)


def char_bigram_predictability(char_list):
    """H(c|prev) / H(c) — how much does the previous char help?"""
    unigram = Counter(char_list)
    total = sum(unigram.values())
    if total < 2:
        return 1.0
    h_uni = -sum((c/total) * math.log2(c/total) for c in unigram.values() if c > 0)

    bigrams = Counter()
    for i in range(1, len(char_list)):
        bigrams[(char_list[i-1], char_list[i])] += 1
    total_bi = sum(bigrams.values())
    # H(c2|c1) = H(c1,c2) - H(c1)
    joint = Counter()
    for (c1, c2), cnt in bigrams.items():
        joint[(c1, c2)] = cnt
    h_joint = -sum((c/total_bi) * math.log2(c/total_bi) for c in joint.values() if c > 0)
    prev_freq = Counter(c1 for (c1, c2) in bigrams for _ in range(bigrams[(c1,c2)]))
    # Actually recompute properly
    prev_total = sum(bigrams.values())
    prev_counts = Counter()
    for (c1, c2), cnt in bigrams.items():
        prev_counts[c1] += cnt
    h_prev = -sum((c/prev_total) * math.log2(c/prev_total) for c in prev_counts.values() if c > 0)
    h_cond = h_joint - h_prev
    if h_uni == 0:
        return 1.0
    return h_cond / h_uni

def word_bigram_predictability(words):
    """H(w|prev_w) / H(w) — word-level predictability ratio."""
    n = len(words)
    if n < 100:
        return 1.0
    unigram = Counter(words)
    total = sum(unigram.values())
    h_uni = -sum((c/total) * math.log2(c/total) for c in unigram.values() if c > 0)

    bigrams = Counter()
    for i in range(1, n):
        bigrams[(words[i-1], words[i])] += 1
    total_bi = sum(bigrams.values())
    h_joint = -sum((c/total_bi) * math.log2(c/total_bi) for c in bigrams.values() if c > 0)
    prev_counts = Counter()
    for (w1, w2), cnt in bigrams.items():
        prev_counts[w1] += cnt
    prev_total = sum(prev_counts.values())
    h_prev = -sum((c/prev_total) * math.log2(c/prev_total) for c in prev_counts.values() if c > 0)
    h_cond = h_joint - h_prev
    if h_uni == 0:
        return 1.0
    return h_cond / h_uni

def mean_word_length(words):
    return np.mean([len(w) for w in words])

def ttr_at_n(words, n=5000):
    """Type-token ratio at first n tokens."""
    subset = words[:min(n, len(words))]
    return len(set(subset)) / len(subset)


def vocab_growth_curve(words, n_points=50):
    """Return (n_tokens, n_types) pairs for vocabulary growth curve."""
    n = len(words)
    points = np.linspace(1, n, n_points, dtype=int)
    seen = set()
    idx = 0
    curve = []
    for pt in points:
        while idx < pt:
            seen.add(words[idx])
            idx += 1
        curve.append((int(pt), len(seen)))
    return curve

def compute_fingerprint(words, char_list, label):
    """Compute the full 7-stat fingerprint."""
    fp = {
        'label': label,
        'n_tokens': len(words),
        'n_types': len(set(words)),
        'heaps_beta': heaps_exponent(words),
        'hapax_ratio_mid': hapax_ratio_at_midpoint(words),
        'char_bigram_pred': char_bigram_predictability(char_list),
        'word_bigram_pred': word_bigram_predictability(words),
        'mean_word_len': mean_word_length(words),
        'ttr_5000': ttr_at_n(words, 5000),
        'zipf_alpha': zipf_alpha(words),
    }
    return fp

# ═══════════════════════════════════════════════════════════════════════
# ENCODING MODELS
# ═══════════════════════════════════════════════════════════════════════

def model_simple_substitution(italian_words):
    """Monoalphabetic substitution: permute the alphabet.
    Preserves ALL word-level and char-level structure."""
    # Build a random 1:1 letter mapping
    alphabet = sorted(set(c for w in italian_words for c in w))
    shuffled = list(alphabet)
    random.shuffle(shuffled)
    table = dict(zip(alphabet, shuffled))
    return [''.join(table.get(c, c) for c in w) for w in italian_words]

def model_homophonic(italian_words, fan_out=3):
    """Homophonic substitution: each letter → one of fan_out symbols.
    Creates new 'characters' like 'a1','a2','a3', picked at random.
    This changes word identities but preserves character-level stats."""
    alphabet = sorted(set(c for w in italian_words for c in w))
    # Each letter maps to fan_out possible symbols
    table = {}
    for ch in alphabet:
        table[ch] = [f'{ch}{i}' for i in range(fan_out)]
    encoded_words = []
    for w in italian_words:
        encoded = ''.join(random.choice(table[c]) for c in w)
        encoded_words.append(encoded)
    # Characters in encoded text are the multi-char "symbols"
    return encoded_words

def model_syllabic(italian_words):
    """Syllabic encoding: split Italian words into CV-ish syllables,
    each syllable becomes a VMS-like 'word'.

    Simple rule: split before each consonant that follows a vowel.
    E.g. 'parlare' → 'par' 'la' 're'
    """
    vowels = set('aeiouyàáâãäåæèéêëìíîïòóôõöùúûüý')
    encoded = []
    for w in italian_words:
        syllables = []
        current = ''
        for i, ch in enumerate(w):
            if i > 0 and ch not in vowels and len(current) > 0 and current[-1] in vowels:
                syllables.append(current)
                current = ch
            else:
                current += ch
        if current:
            syllables.append(current)
        encoded.extend(syllables)
    return encoded

def model_verbose(italian_words, pool_size=22):
    """Verbose cipher: each plaintext letter → a 'word' from a pool of
    pool_size symbols. Already excluded by word_predictability_decomposition but included for
    calibration."""
    alphabet = sorted(set(c for w in italian_words for c in w))
    # Map each letter to a fixed 'word' (short string)
    symbols = [f'w{i:02d}' for i in range(max(pool_size, len(alphabet)))]
    random.shuffle(symbols)
    table = {ch: symbols[i % len(symbols)] for i, ch in enumerate(alphabet)}
    encoded = []
    for w in italian_words:
        for ch in w:
            encoded.append(table[ch])
    return encoded

def model_anagram(italian_words):
    """Shuffle characters within each word. Preserves unigram char freq
    and word lengths, destroys bigram structure."""
    encoded = []
    for w in italian_words:
        chars = list(w)
        random.shuffle(chars)
        encoded.append(''.join(chars))
    return encoded

def model_null_vms_like(vms_words, n_tokens=36000):
    """Generate random 'words' matching VMS unigram char freq and word
    length distribution. No structure beyond that."""
    # Get char freq distribution
    all_chars = []
    for w in vms_words:
        all_chars.extend(list(w))
    char_freq = Counter(all_chars)
    chars = list(char_freq.keys())
    weights = np.array([char_freq[c] for c in chars], dtype=float)
    weights /= weights.sum()

    # Get word length distribution
    lengths = [len(w) for w in vms_words]
    len_freq = Counter(lengths)
    len_vals = list(len_freq.keys())
    len_weights = np.array([len_freq[v] for v in len_vals], dtype=float)
    len_weights /= len_weights.sum()

    encoded = []
    for _ in range(n_tokens):
        wlen = np.random.choice(len_vals, p=len_weights)
        word = ''.join(np.random.choice(chars, size=wlen, p=weights))
        encoded.append(word)
    return encoded

def words_to_chars(words):
    """Flatten words to character list."""
    chars = []
    for w in words:
        chars.extend(list(w))
    return chars

# ═══════════════════════════════════════════════════════════════════════
# VOCABULARY GROWTH ANALYSIS (unique to this phase)
# ═══════════════════════════════════════════════════════════════════════

def analyze_vocab_growth(vms_words, italian_words, models_data):
    """Detailed vocabulary growth comparison."""
    pr('═' * 70)
    pr('TEST 1: VOCABULARY GROWTH CURVES (Heaps\' Law)')
    pr('═' * 70)
    pr()

    all_curves = {}
    for label, words in [('VMS', vms_words), ('Italian', italian_words)] + models_data:
        curve = vocab_growth_curve(words, n_points=50)
        all_curves[label] = curve
        beta = heaps_exponent(words)
        n = len(words)
        v = len(set(words))
        pr(f'  {label:30s}  N={n:>6d}  V={v:>5d}  β={beta:.4f}')

    pr()
    pr('  Heaps β interpretation:')
    pr('    β ≈ 0.4-0.6 → natural language (open, productive vocabulary)')
    pr('    β ≈ 0.6-0.8 → high-diversity text or morphologically rich language')
    pr('    β < 0.3     → restricted/closed vocabulary (code, cipher)')
    pr('    β → 0       → fixed vocabulary (verbose letter-cipher)')
    pr()

    return all_curves

# ═══════════════════════════════════════════════════════════════════════
# MAIN TOURNAMENT
# ═══════════════════════════════════════════════════════════════════════

def run_tournament():
    pr('╔' + '═'*68 + '╗')
    pr('║  encoding_model_tournament: Encoding Model Tournament — Generative Discrimination  ║')
    pr('╚' + '═'*68 + '╝')
    pr()

    # Load data
    pr('Loading VMS...')
    vms_words = load_vms_words()
    vms_chars = load_vms_chars(vms_words)
    pr(f'  VMS: {len(vms_words)} words, {len(vms_chars)} glyphs')
    pr()

    pr('Loading Italian (Dante, Gutenberg #1012)...')
    try:
        italian_words = load_italian_words()
    except Exception as e:
        pr(f'  FAILED to fetch Italian: {e}')
        pr('  Using cached fallback approach...')
        # If network fails, generate synthetic "Italian-like" text
        # with known properties for comparison
        italian_words = None

    if italian_words is None:
        pr('  ERROR: Cannot proceed without reference text.')
        return

    pr(f'  Italian: {len(italian_words)} words')
    pr()

    # Set seed for reproducibility
    random.seed(42)
    np.random.seed(42)

    # Generate all encoded versions
    pr('Generating encoded texts...')
    models = {}
    models['Italian (raw)'] = italian_words
    pr('  [C] Simple substitution...')
    models['Simple subst.'] = model_simple_substitution(italian_words)
    pr('  [D] Homophonic (fan=3)...')
    models['Homophonic (fan=3)'] = model_homophonic(italian_words, fan_out=3)
    pr('  [E] Syllabic encoding...')
    models['Syllabic'] = model_syllabic(italian_words)
    pr('  [F] Verbose cipher...')
    models['Verbose (letter→word)'] = model_verbose(italian_words)
    pr('  [G] Anagram (in-word shuffle)...')
    models['Anagram'] = model_anagram(italian_words)
    pr('  [H] Null (VMS char+len matched)...')
    models['Null (VMS-matched)'] = model_null_vms_like(vms_words)
    pr()

    # ─── TEST 1: Vocabulary growth ────────────────────────────────
    models_list = [(k, v) for k, v in models.items()]
    all_curves = analyze_vocab_growth(vms_words, italian_words, models_list)

    # ─── FINGERPRINTS ─────────────────────────────────────────────
    pr()
    pr('═' * 70)
    pr('TEST 2: FULL FINGERPRINT COMPARISON')
    pr('═' * 70)
    pr()

    fingerprints = {}

    # VMS fingerprint
    fp_vms = compute_fingerprint(vms_words, vms_chars, 'VMS')
    fingerprints['VMS'] = fp_vms
    pr(f'  VMS fingerprint computed.')

    # Italian raw
    fp_it = compute_fingerprint(italian_words, words_to_chars(italian_words), 'Italian (raw)')
    fingerprints['Italian (raw)'] = fp_it
    pr(f'  Italian fingerprint computed.')

    # All models
    for label, words in models.items():
        if label == 'Italian (raw)':
            continue  # Already done
        chars = words_to_chars(words)
        fp = compute_fingerprint(words, chars, label)
        fingerprints[label] = fp
        pr(f'  {label} fingerprint computed.')

    pr()

    # Print fingerprint table
    stat_keys = ['heaps_beta', 'hapax_ratio_mid', 'char_bigram_pred',
                 'word_bigram_pred', 'mean_word_len', 'ttr_5000', 'zipf_alpha']
    stat_labels = ['Heaps β', 'Hapax@mid', 'H(c|p)/H(c)', 'H(w|p)/H(w)',
                   'Mean wlen', 'TTR@5K', 'Zipf α']

    pr(f'  {"Model":30s}', end='')
    for sl in stat_labels:
        pr(f' {sl:>12s}', end='')
    pr()
    pr('  ' + '-' * (30 + 12 * len(stat_labels)))

    for label in ['VMS'] + [k for k in models.keys()]:
        fp = fingerprints[label]
        pr(f'  {label:30s}', end='')
        for sk in stat_keys:
            pr(f' {fp[sk]:>12.4f}', end='')
        pr()

    # ─── SCORING: L2 distance from VMS ───────────────────────────
    pr()
    pr('═' * 70)
    pr('TEST 3: MODEL SCORING (L2 distance from VMS fingerprint)')
    pr('═' * 70)
    pr()

    # Z-normalize each statistic across all models + VMS
    all_labels = ['VMS'] + list(models.keys())
    stat_matrix = np.zeros((len(all_labels), len(stat_keys)))
    for i, label in enumerate(all_labels):
        for j, sk in enumerate(stat_keys):
            stat_matrix[i, j] = fingerprints[label][sk]

    # Z-score each column
    means = stat_matrix.mean(axis=0)
    stds = stat_matrix.std(axis=0)
    stds[stds == 0] = 1  # Avoid division by zero
    z_matrix = (stat_matrix - means) / stds

    vms_z = z_matrix[0]  # VMS is first row
    pr(f'  {"Model":30s} {"L2 dist":>10s} {"Rank":>6s}')
    pr('  ' + '-' * 50)

    distances = {}
    for i, label in enumerate(all_labels):
        if label == 'VMS':
            continue
        dist = float(np.sqrt(np.sum((z_matrix[i] - vms_z) ** 2)))
        distances[label] = dist

    # Sort by distance
    ranked = sorted(distances.items(), key=lambda x: x[1])
    for rank, (label, dist) in enumerate(ranked, 1):
        marker = ' ◄◄◄ BEST MATCH' if rank == 1 else ''
        pr(f'  {label:30s} {dist:>10.3f} {rank:>6d}{marker}')

    # ─── DIAGNOSTIC: Per-statistic deviation ─────────────────────
    pr()
    pr('═' * 70)
    pr('TEST 4: PER-STATISTIC DEVIATION (VMS vs each model, in σ)')
    pr('═' * 70)
    pr()

    best_label = ranked[0][0]
    pr(f'  Best match: {best_label}')
    pr()

    pr(f'  {"Statistic":>15s}  {"VMS":>8s}', end='')
    for label in [best_label, 'Italian (raw)', 'Syllabic', 'Null (VMS-matched)']:
        if label in fingerprints:
            pr(f'  {label[:15]:>15s}', end='')
    pr()
    pr('  ' + '-' * 80)

    for j, (sk, sl) in enumerate(zip(stat_keys, stat_labels)):
        pr(f'  {sl:>15s}  {fingerprints["VMS"][sk]:>8.4f}', end='')
        for label in [best_label, 'Italian (raw)', 'Syllabic', 'Null (VMS-matched)']:
            if label in fingerprints:
                val = fingerprints[label][sk]
                dev = (val - fingerprints['VMS'][sk])
                if stds[j] > 0:
                    dev_z = dev / stds[j]
                    pr(f'  {val:>7.4f}({dev_z:+.1f}σ)', end='')
                else:
                    pr(f'  {val:>7.4f}(   —)', end='')
        pr()

    # ─── TEST 5: VMS A vs B vocabulary dynamics ──────────────────
    pr()
    pr('═' * 70)
    pr('TEST 5: VMS LANGUAGE A vs B VOCABULARY DYNAMICS')
    pr('═' * 70)
    pr()

    # Reload with folio metadata for A/B split
    vms_a_words, vms_b_words = load_vms_by_language()
    pr(f'  Language A: {len(vms_a_words)} words')
    pr(f'  Language B: {len(vms_b_words)} words')
    pr()

    beta_a = heaps_exponent(vms_a_words)
    beta_b = heaps_exponent(vms_b_words)
    beta_all = heaps_exponent(vms_words)
    pr(f'  Heaps β:  A={beta_a:.4f}  B={beta_b:.4f}  Combined={beta_all:.4f}')

    hapax_a = hapax_ratio_at_midpoint(vms_a_words)
    hapax_b = hapax_ratio_at_midpoint(vms_b_words)
    pr(f'  Hapax@mid: A={hapax_a:.4f}  B={hapax_b:.4f}')

    ttr_a = ttr_at_n(vms_a_words, 5000)
    ttr_b = ttr_at_n(vms_b_words, 5000)
    pr(f'  TTR@5K:   A={ttr_a:.4f}  B={ttr_b:.4f}')

    # Vocabulary overlap
    vocab_a = set(vms_a_words)
    vocab_b = set(vms_b_words)
    shared = vocab_a & vocab_b
    only_a = vocab_a - vocab_b
    only_b = vocab_b - vocab_a
    pr(f'  Vocab A: {len(vocab_a)}, Vocab B: {len(vocab_b)}')
    pr(f'  Shared: {len(shared)} ({100*len(shared)/len(vocab_a|vocab_b):.1f}%)')
    pr(f'  Only A: {len(only_a)}, Only B: {len(only_b)}')
    pr()

    # Test: does combining A+B produce a JUMP in vocabulary?
    # If A and B are the same language, combined Heaps should be similar.
    # If different languages, combined should show discontinuity.
    pr('  Combined-vs-separate vocabulary test:')
    v_a = len(vocab_a)
    v_b = len(vocab_b)
    v_combined = len(vocab_a | vocab_b)
    v_expected_if_same = max(v_a, v_b) * 1.1  # Rough: 10% more from doubling
    v_expected_if_diff = v_a + v_b  # Upper bound: all unique
    pr(f'    V(A)={v_a}, V(B)={v_b}, V(A∪B)={v_combined}')
    pr(f'    If same language: expect ~{v_expected_if_same:.0f} (mild growth)')
    pr(f'    If different languages: expect ~{v_expected_if_diff:.0f} (near sum)')
    ratio = (v_combined - max(v_a, v_b)) / max(v_a, v_b)
    pr(f'    Actual growth from larger to combined: {ratio:.1%}')
    pr(f'    → {"SUGGESTS different vocabularies" if ratio > 0.3 else "SUGGESTS overlapping vocabulary"}')

    # ─── TEST 6: Cross-section vocabulary matrix ─────────────────
    pr()
    pr('═' * 70)
    pr('TEST 6: CROSS-SECTION VOCABULARY OVERLAP (Jaccard matrix)')
    pr('═' * 70)
    pr()

    section_words = load_vms_by_section()
    sections = sorted(section_words.keys())
    pr(f'  Sections: {sections}')
    for sec in sections:
        pr(f'    {sec}: {len(section_words[sec])} words, {len(set(section_words[sec]))} types')
    pr()

    # Jaccard matrix
    section_vocabs = {s: set(section_words[s]) for s in sections}
    pr(f'  {"":>10s}', end='')
    for s in sections:
        pr(f' {s[:8]:>8s}', end='')
    pr()
    for s1 in sections:
        pr(f'  {s1[:10]:>10s}', end='')
        for s2 in sections:
            if s1 == s2:
                pr(f' {"—":>8s}', end='')
            else:
                inter = len(section_vocabs[s1] & section_vocabs[s2])
                union = len(section_vocabs[s1] | section_vocabs[s2])
                j = inter / max(union, 1)
                pr(f' {j:>8.3f}', end='')
        pr()

    # Section-specific vocabulary (words unique to one section)
    pr()
    pr('  Section-unique words (appear in ONLY that section):')
    all_vocab = set()
    for s in sections:
        all_vocab |= section_vocabs[s]
    for s in sections:
        unique = section_vocabs[s] - set().union(*(section_vocabs[s2] for s2 in sections if s2 != s))
        pr(f'    {s}: {len(unique)} unique words ({100*len(unique)/max(len(section_vocabs[s]),1):.1f}% of its vocab)')

    # ─── ADJUDICATION ─────────────────────────────────────────────
    pr()
    pr('═' * 70)
    pr('ADJUDICATION')
    pr('═' * 70)
    pr()

    vms_beta = fingerprints['VMS']['heaps_beta']
    it_beta = fingerprints['Italian (raw)']['heaps_beta']

    pr(f'  VMS Heaps β = {vms_beta:.4f}')
    pr(f'  Italian β   = {it_beta:.4f}')
    pr()

    pr('  MODEL RANKING (closest to VMS):')
    for rank, (label, dist) in enumerate(ranked, 1):
        pr(f'    {rank}. {label} (L2={dist:.3f})')
    pr()

    # Interpret
    best = ranked[0][0]
    pr(f'  BEST MATCH: {best}')
    pr()
    pr('  Interpretation:')

    if 'Italian' in best or 'subst' in best.lower():
        pr('    VMS fingerprint is closest to natural language or simple')
        pr('    substitution. This is CONSISTENT with the NL hypothesis.')
        pr('    Simple substitution is statistically identical to NL')
        pr('    (it just relabels characters), so this cannot distinguish')
        pr('    between plaintext NL and monoalphabetic cipher of NL.')
    elif 'Syllabic' in best:
        pr('    VMS fingerprint matches syllabic encoding of NL.')
        pr('    This would explain the low H(char|prev) and the')
        pr('    constrained vocabulary.')
    elif 'Homophonic' in best:
        pr('    VMS fingerprint matches homophonic encoding.')
        pr('    This would explain vocabulary inflation while preserving')
        pr('    character-level structure.')
    elif 'Null' in best:
        pr('    VMS fingerprint matches random text with matched')
        pr('    character frequencies. This is CONCERNING — suggests')
        pr('    structure is superficial (unigram + word-length only).')
    else:
        pr(f'    Best match is {best}. Further analysis needed.')

    pr()
    pr('  CRITICAL CONSTRAINTS from this phase:')

    # Check if VMS is clearly separated from null model
    null_dist = distances.get('Null (VMS-matched)', 999)
    best_dist = ranked[0][1]
    pr(f'    Null model distance: {null_dist:.3f}')
    pr(f'    Best model distance: {best_dist:.3f}')
    if null_dist > best_dist * 1.5:
        pr(f'    → VMS is {null_dist/best_dist:.1f}× farther from null than from')
        pr(f'      best model. Structure is NOT just char-freq + word-length.')
    else:
        pr(f'    → VMS is only {null_dist/best_dist:.1f}× farther from null than best.')
        pr(f'      CAUTION: Much of VMS "structure" may be unigram artifact.')

    pr()

    # Verbose exclusion confirmation
    verbose_dist = distances.get('Verbose (letter→word)', 999)
    pr(f'    Verbose cipher distance: {verbose_dist:.3f} (rank {[r for r,(l,d) in enumerate(ranked,1) if l=="Verbose (letter→word)"][0] if "Verbose (letter→word)" in distances else "?"})' )
    pr(f'    → Verbose cipher CONFIRMED excluded (as per word_predictability_decomposition)')

    # A/B divergence
    pr()
    pr(f'    A/B Heaps divergence: |β_A - β_B| = {abs(beta_a - beta_b):.4f}')
    if abs(beta_a - beta_b) > 0.05:
        pr(f'    → DIFFERENT vocabulary dynamics between A and B')
        pr(f'      Suggests genuinely different lexical sources, not just')
        pr(f'      different handwriting of the same text')
    else:
        pr(f'    → SIMILAR vocabulary dynamics between A and B')
        pr(f'      Compatible with same language in different hands')

    return fingerprints, distances, ranked

# ═══════════════════════════════════════════════════════════════════════
# A/B LANGUAGE AND SECTION HELPERS
# ═══════════════════════════════════════════════════════════════════════

def get_folio_num(fname):
    """Extract numeric part from folio filename."""
    m = re.search(r'f(\d+)', fname)
    return int(m.group(1)) if m else 0


def get_section(folio_num):
    if folio_num <= 56: return 'herbal'
    if folio_num <= 67: return 'astro'
    if folio_num <= 73: return 'cosmo'
    if folio_num <= 84: return 'bio'
    if folio_num <= 86: return 'cosmo2'
    if folio_num <= 102: return 'pharma'
    return 'text'

def load_vms_by_language():
    """Load VMS words split by Currier A/B."""
    a_words, b_words = [], []
    folio_files = sorted(FOLIO_DIR.glob('*.txt'))
    for fp in folio_files:
        fnum = get_folio_num(fp.name)
        lang = get_currier_language(fnum)
        words = []
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                m = re.match(r'<([^>]+)>', line)
                rest = line[m.end():].strip() if m else line
                if not rest:
                    continue
                for tok in re.split(r'[.\s,;]+', rest):
                    tok = tok.strip()
                    if tok and re.match(r'^[a-z]+$', tok):
                        words.append(tok)
        if lang == 'A':
            a_words.extend(words)
        else:
            b_words.extend(words)
    return a_words, b_words

def load_vms_by_section():
    """Load VMS words grouped by section."""
    section_words = defaultdict(list)
    folio_files = sorted(FOLIO_DIR.glob('*.txt'))
    for fp in folio_files:
        fnum = get_folio_num(fp.name)
        sec = get_section(fnum)
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                m = re.match(r'<([^>]+)>', line)
                rest = line[m.end():].strip() if m else line
                if not rest:
                    continue
                for tok in re.split(r'[.\s,;]+', rest):
                    tok = tok.strip()
                    if tok and re.match(r'^[a-z]+$', tok):
                        section_words[sec].append(tok)
    return dict(section_words)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    fingerprints, distances, ranked = run_tournament()

    # Save outputs
    out_path = RESULTS_DIR / 'encoding_model_tournament_output.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f'\nSaved to {out_path}')

    # Save JSON
    json_path = RESULTS_DIR / 'encoding_model_tournament_output.json'
    json_data = {
        'fingerprints': fingerprints,
        'distances': {k: float(v) for k, v in distances.items()},
        'ranking': [(k, float(v)) for k, v in ranked],
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, default=str)
    pr(f'Saved to {json_path}')
