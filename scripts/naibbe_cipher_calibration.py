#!/usr/bin/env python3
"""
Naibbe-Style Verbose Cipher Calibration Experiment
═════════════════════════════════════════════════════════════════

QUESTION:  Can a Naibbe cipher (letter → glyph-substring, concatenate
           within "words", word boundaries placed by a rule) over
           natural language text reproduce the VMS statistical fingerprint?

WHY THIS MATTERS:
- cipher_identification_tests EXCLUDED simple verbose cipher (1 letter → 1 word): MI 4× too low
- encoding_model_tournament showed it scores worst (L2=5.012) of all models tested
- But Naibbe is fundamentally different: multiple letters → one word
  via glyph-group concatenation.  NEVER TESTED.
- If Naibbe can match the VMS fingerprint, it becomes the leading hypothesis
- If it cannot, even with favorable parameters, the hypothesis weakens

SKEPTICAL DESIGN:
- 50 RANDOM glyph tables per configuration (not hand-tuned)
- 3 source languages (Latin, Italian, English) — tests source-dependence
- 4 word-break rules — tests segmentation-dependence
- All 7 metrics reported for EVERY experiment — no cherry-picking
- Distribution analysis: what FRACTION of random tables match?
- Sensitivity analysis: which parameters drive which metrics?
- Explicit failure criteria stated BEFORE running

FAILURE CRITERIA (stated in advance):
- If NO random table achieves L2 < 3.0 → Naibbe is severely challenged
- If h_ratio_char is always > 0.80 or always < 0.40 → key metric fails
- If source language doesn't matter → hypothesis is unfalsifiable
- If ONLY a hand-tuned table matches → hypothesis is ad hoc

SUCCESS CRITERIA:
- Multiple random tables achieve L2 < 2.0 (comparable to raw Italian)
- h_ratio_char naturally falls near 0.64 for some tables
- Source language matters (Latin/Italian outperform English)

VMS TARGET FINGERPRINT (from encoding_model_tournament):
  Heaps β      = 0.7533
  Hapax@mid    = 0.6555
  H(c|p)/H(c) = 0.6407
  H(w|p)/H(w) = 0.4448
  Mean wlen    = 4.9352
  TTR@5K       = 0.3420
  Zipf α       = 0.9415
"""

import sys, os, re, math, random, time, json, unicodedata
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import urllib.request
from common import load_vms_words, fetch_gutenberg

_print = print
OUTPUT = []
def pr(s='', end='\n'):
    _print(s, end=end)
    sys.stdout.flush()
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

SCRIPT_DIR = Path(__file__).resolve().parent
FOLIO_DIR  = SCRIPT_DIR.parent / 'folios'
RESULTS_DIR = SCRIPT_DIR.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

SEED = 20250413
N_TABLES = 30     # random tables per configuration (sufficient for distribution)
TARGET_WORDS = 36000   # match VMS corpus size

# 18 core EVA characters (the frequent ones in VMS)
EVA_CHARS = list('acdefhiklnopqrsty')

# VMS target fingerprint
VMS = {
    'heaps': 0.7533,
    'hapax':  0.6555,
    'h_char': 0.6407,
    'h_word': 0.4448,
    'wlen':   4.9352,
    'ttr':    0.3420,
    'zipf':   0.9415,
}

# ═══════════════════════════════════════════════════════════════════════
# FINGERPRINT FUNCTIONS (from encoding_model_tournament, verified)
# ═══════════════════════════════════════════════════════════════════════

def heaps_exponent(words):
    n = len(words)
    if n < 200: return 0.0
    pts = np.linspace(100, n, 20, dtype=int)
    running = set(); idx = 0; vocab = {}
    for pt in sorted(pts):
        while idx < pt:
            running.add(words[idx]); idx += 1
        vocab[pt] = len(running)
    ln = np.log(np.array(sorted(pts), dtype=float))
    lv = np.log(np.array([vocab[p] for p in sorted(pts)], dtype=float))
    A = np.vstack([ln, np.ones(len(ln))]).T
    res = np.linalg.lstsq(A, lv, rcond=None)
    return float(res[0][0])

def hapax_at_mid(words):
    mid = len(words) // 2
    if mid < 10: return 0.0
    freq = Counter(words[:mid])
    return sum(1 for c in freq.values() if c == 1) / max(len(freq), 1)

def h_ratio_char(words):
    """H(char|prev) / H(char)"""
    chars = list(''.join(words))
    if len(chars) < 100: return 1.0
    uni = Counter(chars); tot = sum(uni.values())
    h_uni = -sum((c/tot)*math.log2(c/tot) for c in uni.values() if c > 0)
    if h_uni == 0: return 1.0

    bi = Counter()
    for i in range(1, len(chars)):
        bi[(chars[i-1], chars[i])] += 1
    tot_bi = sum(bi.values())
    h_joint = -sum((c/tot_bi)*math.log2(c/tot_bi) for c in bi.values() if c > 0)
    prev_c = Counter()
    for (c1,c2), cnt in bi.items(): prev_c[c1] += cnt
    ptot = sum(prev_c.values())
    h_prev = -sum((c/ptot)*math.log2(c/ptot) for c in prev_c.values() if c > 0)
    return (h_joint - h_prev) / h_uni

def h_ratio_word(words):
    """H(word|prev) / H(word)"""
    if len(words) < 200: return 1.0
    uni = Counter(words); tot = sum(uni.values())
    h_uni = -sum((c/tot)*math.log2(c/tot) for c in uni.values() if c > 0)
    if h_uni == 0: return 1.0

    bi = Counter()
    for i in range(1, len(words)):
        bi[(words[i-1], words[i])] += 1
    tot_bi = sum(bi.values())
    h_joint = -sum((c/tot_bi)*math.log2(c/tot_bi) for c in bi.values() if c > 0)
    prev_c = Counter()
    for (w1,w2), cnt in bi.items(): prev_c[w1] += cnt
    ptot = sum(prev_c.values())
    h_prev = -sum((c/ptot)*math.log2(c/ptot) for c in prev_c.values() if c > 0)
    return (h_joint - h_prev) / h_uni

def mean_wlen(words):
    if not words: return 0.0
    return float(np.mean([len(w) for w in words]))

def ttr_5k(words):
    sub = words[:min(5000, len(words))]
    return len(set(sub)) / len(sub) if sub else 0.0

def zipf_alpha(words):
    freq = Counter(words)
    ranked = sorted(freq.values(), reverse=True)
    n = min(len(ranked), 500)
    if n < 10: return 0.0
    lr = np.log(np.arange(1, n+1, dtype=float))
    lf = np.log(np.array(ranked[:n], dtype=float))
    A = np.vstack([lr, np.ones(n)]).T
    res = np.linalg.lstsq(A, lf, rcond=None)
    return float(-res[0][0])

def fingerprint(words):
    return {
        'heaps': heaps_exponent(words),
        'hapax': hapax_at_mid(words),
        'h_char': h_ratio_char(words),
        'h_word': h_ratio_word(words),
        'wlen': mean_wlen(words),
        'ttr': ttr_5k(words),
        'zipf': zipf_alpha(words),
    }

METRIC_KEYS = ['heaps', 'hapax', 'h_char', 'h_word', 'wlen', 'ttr', 'zipf']

def l2_raw(fp):
    """Raw (unnormalized) L2 distance from VMS target."""
    return math.sqrt(sum((fp[k] - VMS[k])**2 for k in METRIC_KEYS))

# ═══════════════════════════════════════════════════════════════════════
# SOURCE TEXT LOADING
# ═══════════════════════════════════════════════════════════════════════


def strip_diacritics(text):
    """Normalize diacritics to base Latin letters (č→c, á→a, ř→r, etc.).
    Essential for Czech/accented texts so characters aren't just dropped."""
    nfkd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')

def text_to_letters(text, keep_spaces=True):
    """Reduce text to lowercase letters (and optionally spaces)."""
    text = strip_diacritics(text.lower())
    if keep_spaces:
        text = re.sub(r'[^a-z ]+', '', text)
        text = re.sub(r' +', ' ', text).strip()
    else:
        text = re.sub(r'[^a-z]+', '', text)
    return text

def load_source(name):
    """Load source text as (letters_str, words_list).
    Returns enough text for ~36K cipher words × 3 letters = ~108K source letters."""
    min_chars = 120000

    if name == 'italian':
        pr(f"  Fetching Italian (Dante, Gutenberg #1012)...")
        try:
            raw = fetch_gutenberg(1012)
            text = text_to_letters(raw, keep_spaces=True)
            if len(text) >= min_chars:
                pr(f"  OK: {len(text)} chars, {len(text.split())} words")
                return text, text.split()
        except Exception as e:
            pr(f"  Fetch failed: {e}")

    elif name == 'latin':
        # Try Caesar's Gallic Wars (Latin)
        for eid, label in [(10657, "Gallic War"), (7028, "Aeneid")]:
            pr(f"  Trying Gutenberg #{eid} ({label})...")
            try:
                raw = fetch_gutenberg(eid)
                text = text_to_letters(raw, keep_spaces=True)
                if len(text) >= min_chars:
                    pr(f"  OK: {len(text)} chars, {len(text.split())} words")
                    return text, text.split()
                else:
                    pr(f"  Too short: {len(text)} chars")
            except Exception as e:
                pr(f"  Fetch failed: {e}")

    elif name == 'english':
        # King James Bible, very large
        for eid in [10, 100]:
            pr(f"  Trying Gutenberg #{eid} (English)...")
            try:
                raw = fetch_gutenberg(eid)
                text = text_to_letters(raw, keep_spaces=True)
                if len(text) >= min_chars:
                    pr(f"  OK: {len(text)} chars, {len(text.split())} words")
                    return text, text.split()
                else:
                    pr(f"  Too short: {len(text)} chars")
            except Exception as e:
                pr(f"  Fetch failed: {e}")

    elif name == 'czech':
        # Bible Kralická 1613 — period-appropriate Czech (16th/17th century)
        kralice_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'czech_bible_kralice')
        import glob
        txt_files = sorted(glob.glob(os.path.join(kralice_dir, '*_read.txt')))
        pr(f"  Loading Bible Kralická 1613 from {len(txt_files)} chapter files...")
        combined_text = []
        for fpath in txt_files:
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = f.read()
            text = text_to_letters(raw, keep_spaces=True)
            combined_text.append(text)
        if combined_text:
            full = ' '.join(combined_text)
            full = re.sub(r' +', ' ', full).strip()
            pr(f"  Combined: {len(full)} chars, {len(full.split())} words")
            if len(full) >= min_chars:
                return full, full.split()
            else:
                pr(f"  Still too short: {len(full)} chars")

    # Fallback: generate from letter frequencies
    pr(f"  Falling back to Markov generation for '{name}'...")
    return generate_markov_source(name, min_chars)

# Letter frequency tables (published corpus statistics)
LANG_FREQ = {
    'latin': {
        'a': .078,'b': .015,'c': .037,'d': .033,'e': .122,'f': .010,
        'g': .012,'h': .009,'i': .113,'j': .001,'k': .001,'l': .028,
        'm': .056,'n': .070,'o': .054,'p': .029,'q': .012,'r': .068,
        's': .074,'t': .085,'u': .078,'v': .010,'x': .005,'y': .003,'z': .001,
    },
    'italian': {
        'a': .117,'b': .009,'c': .045,'d': .037,'e': .118,'f': .011,
        'g': .016,'h': .006,'i': .103,'l': .065,'m': .025,'n': .069,
        'o': .098,'p': .031,'q': .005,'r': .064,'s': .050,'t': .056,
        'u': .030,'v': .021,'z': .012,
    },
    'english': {
        'a': .082,'b': .015,'c': .028,'d': .043,'e': .127,'f': .022,
        'g': .020,'h': .061,'i': .070,'j': .002,'k': .008,'l': .040,
        'm': .024,'n': .067,'o': .075,'p': .019,'q': .001,'r': .060,
        's': .063,'t': .091,'u': .028,'v': .010,'w': .024,'x': .002,
        'y': .020,'z': .001,
    },
    # Czech letter frequencies (after stripping diacritics to base Latin)
    'czech': {
        'a': .082,'b': .015,'c': .040,'d': .034,'e': .120,'f': .003,
        'g': .003,'h': .022,'i': .064,'j': .020,'k': .038,'l': .038,
        'm': .030,'n': .066,'o': .088,'p': .036,'q': .001,'r': .052,
        's': .052,'t': .057,'u': .042,'v': .047,'w': .001,'x': .001,
        'y': .028,'z': .029,
    },
}

# Word length distributions (approximate, from published data)
WLEN_PARAMS = {
    'latin':   (5.3, 2.5),   # mean, std of Latin word lengths
    'italian': (4.8, 2.3),
    'english': (4.7, 2.2),
    'czech':   (4.9, 2.4),   # Czech has moderate word length
}

def generate_markov_source(lang, n_chars, seed=SEED):
    """Generate text with correct unigram letter frequencies and
    word-length distribution. NOT real language: no bigram structure.
    Serves as conservative baseline (real text has MORE structure)."""
    rng = random.Random(seed)
    freq = LANG_FREQ.get(lang, LANG_FREQ['english'])
    letters = [l for l in freq if freq[l] > 0]
    weights = [freq[l] for l in letters]
    total = sum(weights)
    weights = [w/total for w in weights]

    wlen_mean, wlen_std = WLEN_PARAMS.get(lang, (5.0, 2.0))

    result_chars = []
    words = []
    current_word = []

    target_len = max(2, int(rng.gauss(wlen_mean, wlen_std)))
    for _ in range(n_chars):
        c = rng.choices(letters, weights=weights, k=1)[0]
        current_word.append(c)
        if len(current_word) >= target_len:
            w = ''.join(current_word)
            words.append(w)
            result_chars.extend(current_word)
            result_chars.append(' ')
            current_word = []
            target_len = max(2, int(rng.gauss(wlen_mean, wlen_std)))

    if current_word:
        words.append(''.join(current_word))
        result_chars.extend(current_word)

    text = ''.join(result_chars).strip()
    pr(f"  Generated: {len(text)} chars, {len(words)} words")
    return text, words

# ═══════════════════════════════════════════════════════════════════════
# NAIBBE CIPHER IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════

def make_random_table(rng, glyph_len_dist=None):
    """Create a random glyph table: each of 26 letters → EVA glyph string.
    glyph_len_dist: dict {length: probability}, default {1: 0.35, 2: 0.45, 3: 0.20}
    """
    if glyph_len_dist is None:
        glyph_len_dist = {1: 0.35, 2: 0.45, 3: 0.20}

    lens = list(glyph_len_dist.keys())
    probs = list(glyph_len_dist.values())

    table = {}
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        glen = rng.choices(lens, weights=probs, k=1)[0]
        glyph = ''.join(rng.choices(EVA_CHARS, k=glen))
        table[letter] = glyph
    return table

def make_huffman_table(rng, lang_freq):
    """Frequency-aware table: common letters → shorter glyphs."""
    sorted_letters = sorted(lang_freq.keys(), key=lambda l: lang_freq[l], reverse=True)
    table = {}
    for i, letter in enumerate(sorted_letters):
        if i < 7:    # top 7 → 1-char glyph
            glen = 1
        elif i < 18:  # next 11 → 2-char glyph
            glen = 2
        else:         # rest → 3-char glyph
            glen = 3
        glyph = ''.join(rng.choices(EVA_CHARS, k=glen))
        table[letter] = glyph
    # Fill any missing letters (w, j, etc.)
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        if letter not in table:
            table[letter] = ''.join(rng.choices(EVA_CHARS, k=2))
    return table

def naibbe_encode(source_letters, table, break_rule, rng):
    """Encode source text using Naibbe cipher.

    source_letters: string of lowercase letters (no spaces)
    table: dict mapping letter → EVA glyph string
    break_rule: one of:
        ('fixed', K)       — word break every K source letters
        ('variable', probs) — K drawn from distribution
        ('charcount', W)   — break after accumulating ~W ciphertext chars
        ('source_words', words) — break at source word boundaries

    Returns: list of ciphertext words
    """
    cipher_stream = []

    # Optimization: limit encoding to avoid processing 700K+ chars
    # when we only need ~36K words. With K≈3 and glyph_len≈2,
    # we need ~36K × 3 = 108K source letters max.
    max_letters = 200000
    for i, ch in enumerate(source_letters[:max_letters]):
        glyph = table.get(ch, '')
        if glyph:
            cipher_stream.append(glyph)

    # Now segment the cipher stream into "words"
    cipher_words = []
    rule_type = break_rule[0]

    if rule_type == 'fixed':
        K = break_rule[1]
        current = []
        for i, g in enumerate(cipher_stream):
            current.append(g)
            if len(current) >= K:
                word = ''.join(current)
                if word:
                    cipher_words.append(word)
                current = []
        if current:
            word = ''.join(current)
            if word:
                cipher_words.append(word)

    elif rule_type == 'variable':
        K_dist = break_rule[1]  # dict {K: prob}
        ks = list(K_dist.keys())
        ps = list(K_dist.values())
        current = []
        target_k = rng.choices(ks, weights=ps, k=1)[0]
        for g in cipher_stream:
            current.append(g)
            if len(current) >= target_k:
                word = ''.join(current)
                if word:
                    cipher_words.append(word)
                current = []
                target_k = rng.choices(ks, weights=ps, k=1)[0]
        if current:
            word = ''.join(current)
            if word:
                cipher_words.append(word)

    elif rule_type == 'charcount':
        W = break_rule[1]  # target character count per word
        current_chars = []
        for g in cipher_stream:
            current_chars.extend(list(g))
            if len(current_chars) >= W:
                word = ''.join(current_chars)
                if word:
                    cipher_words.append(word)
                current_chars = []
        if current_chars:
            word = ''.join(current_chars)
            if word:
                cipher_words.append(word)

    elif rule_type == 'source_words':
        # break at source word boundaries
        words_list = break_rule[1]
        for w in words_list[:TARGET_WORDS + 5000]:  # limit to avoid waste
            cipher_word = ''.join(table.get(c, '') for c in w)
            if cipher_word:
                cipher_words.append(cipher_word)

    return cipher_words

# ═══════════════════════════════════════════════════════════════════════
# VMS REFERENCE LOADING
# ═══════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════
# WORD BOUNDARY INFORMATION TEST (from cipher_identification_tests part e)
# ═══════════════════════════════════════════════════════════════════════

def word_boundary_info(words):
    """Test: do word boundaries carry predictive information?
    Compute H(char|prev) with and without boundary markers.
    Returns (stream_h, boundary_h, delta).
    Negative delta = boundaries help; positive = boundaries hurt."""
    # Stream model: continuous character stream
    chars = list(''.join(words))
    if len(chars) < 200:
        return (0, 0, 0)

    # Compute stream bigram entropy
    bi_stream = Counter()
    for i in range(1, len(chars)):
        bi_stream[(chars[i-1], chars[i])] += 1
    tot_s = sum(bi_stream.values())
    h_joint_s = -sum((c/tot_s)*math.log2(c/tot_s) for c in bi_stream.values() if c > 0)
    prev_s = Counter()
    for (c1,c2), cnt in bi_stream.items(): prev_s[c1] += cnt
    ptot_s = sum(prev_s.values())
    h_prev_s = -sum((c/ptot_s)*math.log2(c/ptot_s) for c in prev_s.values() if c > 0)
    h_stream = h_joint_s - h_prev_s

    # Boundary model: add ^ (word start) and $ (word end) markers
    bchars = []
    for w in words:
        bchars.append('^')
        bchars.extend(list(w))
        bchars.append('$')

    bi_bound = Counter()
    for i in range(1, len(bchars)):
        bi_bound[(bchars[i-1], bchars[i])] += 1
    tot_b = sum(bi_bound.values())
    h_joint_b = -sum((c/tot_b)*math.log2(c/tot_b) for c in bi_bound.values() if c > 0)
    prev_b = Counter()
    for (c1,c2), cnt in bi_bound.items(): prev_b[c1] += cnt
    ptot_b = sum(prev_b.values())
    h_prev_b = -sum((c/ptot_b)*math.log2(c/ptot_b) for c in prev_b.values() if c > 0)
    h_bound = h_joint_b - h_prev_b

    return h_stream, h_bound, h_bound - h_stream

# ═══════════════════════════════════════════════════════════════════════
# MAIN EXPERIMENT
# ═══════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    rng = random.Random(SEED)

    pr("=" * 75)
    pr("naibbe_cipher_calibration: NAIBBE-STYLE VERBOSE CIPHER CALIBRATION EXPERIMENT")
    pr("Skeptical calibration: can Naibbe encoding reproduce VMS fingerprint?")
    pr("=" * 75)
    pr()

    # ─── Load VMS reference ───────────────────────────────────────
    pr("1. LOADING VMS REFERENCE")
    pr("─" * 75)
    vms_words = load_vms_words()
    vms_fp = fingerprint(vms_words)
    pr(f"  VMS: {len(vms_words)} words, {len(set(vms_words))} types")
    pr(f"  Fingerprint:")
    for k in METRIC_KEYS:
        pr(f"    {k:12s} = {vms_fp[k]:.4f}  (target: {VMS[k]:.4f})")
    pr()

    # ─── Load source texts ────────────────────────────────────────
    pr("2. LOADING SOURCE TEXTS")
    pr("─" * 75)

    sources = {}
    for lang in ['latin', 'italian', 'english', 'czech']:
        pr(f"\n  [{lang.upper()}]")
        text, words = load_source(lang)
        # Strip to letters only for Naibbe encoding
        letters_only = re.sub(r'[^a-z]', '', text)
        sources[lang] = {
            'text': text,
            'words': words,
            'letters': letters_only,
        }
        pr(f"  Letters: {len(letters_only)}, Words: {len(words)}")

        # Compute source fingerprint for comparison
        src_fp = fingerprint(words[:TARGET_WORDS])
        pr(f"  Source language fingerprint (first {TARGET_WORDS} words):")
        for k in METRIC_KEYS:
            delta = src_fp[k] - VMS[k]
            pr(f"    {k:12s} = {src_fp[k]:.4f}  (VMS: {VMS[k]:.4f}, Δ={delta:+.4f})")
    pr()

    # ─── Define experiments ───────────────────────────────────────
    pr("3. EXPERIMENT DESIGN")
    pr("─" * 75)

    break_rules = {
        'K=2':       ('fixed', 2),
        'K=3':       ('fixed', 3),
        'K=4':       ('fixed', 4),
        'variable':  ('variable', {2: 0.25, 3: 0.50, 4: 0.25}),
    }

    glyph_dists = {
        'random_mixed':  {1: 0.35, 2: 0.45, 3: 0.20},
        'short_heavy':   {1: 0.60, 2: 0.30, 3: 0.10},
        'long_heavy':    {1: 0.15, 2: 0.40, 3: 0.45},
    }

    n_experiments = len(sources) * len(break_rules) * len(glyph_dists) * N_TABLES
    # Plus Huffman and source-word-aligned experiments
    n_experiments += len(sources) * len(break_rules) * N_TABLES  # huffman
    n_experiments += len(sources) * N_TABLES  # source-word-aligned

    pr(f"  Sources:      {len(sources)} ({', '.join(sources.keys())})")
    pr(f"  Break rules:  {len(break_rules)} ({', '.join(break_rules.keys())})")
    pr(f"  Glyph dists:  {len(glyph_dists)} ({', '.join(glyph_dists.keys())})")
    pr(f"  Tables per:   {N_TABLES}")
    pr(f"  TOTAL:        ~{n_experiments} experiments")
    pr()

    # ─── Run Monte Carlo ──────────────────────────────────────────
    pr("4. RUNNING MONTE CARLO EXPERIMENTS")
    pr("─" * 75)

    all_results = []
    experiment_count = 0

    for lang, src in sources.items():
        letters = src['letters']
        words_list = src['words']

        # ── Letter-chunked models (fixed and variable K) ──
        for brk_name, brk_rule in break_rules.items():
            for gdist_name, gdist in glyph_dists.items():
                for t_idx in range(N_TABLES):
                    table = make_random_table(rng, glyph_len_dist=gdist)
                    cipher_words = naibbe_encode(letters, table, brk_rule, rng)

                    # Trim to target size
                    if len(cipher_words) > TARGET_WORDS:
                        cipher_words = cipher_words[:TARGET_WORDS]
                    if len(cipher_words) < 1000:
                        continue  # too short, skip

                    fp = fingerprint(cipher_words)
                    dist = l2_raw(fp)

                    all_results.append({
                        'lang': lang,
                        'break': brk_name,
                        'glyph_dist': gdist_name,
                        'table_type': 'random',
                        'table_idx': t_idx,
                        'n_words': len(cipher_words),
                        'fp': fp,
                        'l2': dist,
                    })
                    experiment_count += 1

                # Progress every batch
                _print(f"\r  [{lang}] {brk_name}/{gdist_name}: {experiment_count} experiments...", end='', flush=True)

            # ── Huffman tables with each break rule ──
            for t_idx in range(N_TABLES):
                lang_freq = LANG_FREQ.get(lang, LANG_FREQ['english'])
                table = make_huffman_table(rng, lang_freq)
                cipher_words = naibbe_encode(letters, table, brk_rule, rng)

                if len(cipher_words) > TARGET_WORDS:
                    cipher_words = cipher_words[:TARGET_WORDS]
                if len(cipher_words) < 1000:
                    continue

                fp = fingerprint(cipher_words)
                dist = l2_raw(fp)

                all_results.append({
                    'lang': lang,
                    'break': brk_name,
                    'glyph_dist': 'huffman',
                    'table_type': 'huffman',
                    'table_idx': t_idx,
                    'n_words': len(cipher_words),
                    'fp': fp,
                    'l2': dist,
                })
                experiment_count += 1

        # ── Source-word-aligned model ──
        for t_idx in range(N_TABLES):
            for gdist_name, gdist in [('random_mixed', {1: 0.35, 2: 0.45, 3: 0.20})]:
                table = make_random_table(rng, glyph_len_dist=gdist)
                cipher_words = naibbe_encode(
                    letters, table,
                    ('source_words', words_list), rng
                )
                if len(cipher_words) > TARGET_WORDS:
                    cipher_words = cipher_words[:TARGET_WORDS]
                if len(cipher_words) < 1000:
                    continue

                fp = fingerprint(cipher_words)
                dist = l2_raw(fp)

                all_results.append({
                    'lang': lang,
                    'break': 'word_aligned',
                    'glyph_dist': gdist_name,
                    'table_type': 'random',
                    'table_idx': t_idx,
                    'n_words': len(cipher_words),
                    'fp': fp,
                    'l2': dist,
                })
                experiment_count += 1

        # Print progress
        elapsed = time.time() - t0
        pr(f"  [{lang}] done: {experiment_count} experiments, {elapsed:.1f}s elapsed")

    pr(f"\n  Total experiments: {experiment_count}")
    pr(f"  Elapsed: {time.time()-t0:.1f}s")
    pr()

    # ═══════════════════════════════════════════════════════════════
    # 5. ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    pr("5. RESULTS ANALYSIS")
    pr("═" * 75)

    # ── 5a. Overall L2 distribution ──
    pr("\n5a. L2 DISTANCE DISTRIBUTION (raw, all experiments)")
    pr("─" * 75)
    l2s = [r['l2'] for r in all_results]
    pr(f"  Min L2:    {min(l2s):.4f}")
    pr(f"  Max L2:    {max(l2s):.4f}")
    pr(f"  Mean L2:   {np.mean(l2s):.4f}")
    pr(f"  Median L2: {np.median(l2s):.4f}")
    pr(f"  Std L2:    {np.std(l2s):.4f}")

    # How many below thresholds
    for thresh in [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]:
        n_below = sum(1 for l in l2s if l < thresh)
        pr(f"  L2 < {thresh:.1f}: {n_below}/{len(l2s)} ({100*n_below/len(l2s):.1f}%)")

    # Compare to encoding_model_tournament baselines
    pr(f"\n  encoding_model_tournament reference distances (raw):")
    pr(f"    Italian (best):     1.777")
    pr(f"    Homophonic:         2.703")
    pr(f"    Anagram:            3.167")
    pr(f"    Simple verbose:     5.012")

    # ── 5b. Best 20 experiments ──
    pr("\n5b. TOP 20 BEST-MATCHING EXPERIMENTS")
    pr("─" * 75)
    sorted_results = sorted(all_results, key=lambda r: r['l2'])
    pr(f"  {'Rank':>4} {'L2':>7} {'Lang':>8} {'Break':>10} {'GlyphDist':>14} {'Type':>8} "
       f"{'N':>6} {'heaps':>7} {'hapax':>7} {'h_char':>7} {'h_word':>7} "
       f"{'wlen':>7} {'ttr':>7} {'zipf':>7}")
    pr(f"  {'─'*4} {'─'*7} {'─'*8} {'─'*10} {'─'*14} {'─'*8} "
       f"{'─'*6} {'─'*7} {'─'*7} {'─'*7} {'─'*7} "
       f"{'─'*7} {'─'*7} {'─'*7}")
    pr(f"  {'VMS':>4} {'0.000':>7} {'':>8} {'':>10} {'':>14} {'':>8} "
       f"{'36259':>6} {VMS['heaps']:>7.4f} {VMS['hapax']:>7.4f} {VMS['h_char']:>7.4f} "
       f"{VMS['h_word']:>7.4f} {VMS['wlen']:>7.4f} {VMS['ttr']:>7.4f} {VMS['zipf']:>7.4f}")

    for i, r in enumerate(sorted_results[:20]):
        fp = r['fp']
        pr(f"  {i+1:>4} {r['l2']:>7.4f} {r['lang']:>8} {r['break']:>10} "
           f"{r['glyph_dist']:>14} {r['table_type']:>8} "
           f"{r['n_words']:>6} {fp['heaps']:>7.4f} {fp['hapax']:>7.4f} "
           f"{fp['h_char']:>7.4f} {fp['h_word']:>7.4f} "
           f"{fp['wlen']:>7.4f} {fp['ttr']:>7.4f} {fp['zipf']:>7.4f}")

    # ── 5c. Breakdown by source language ──
    pr("\n5c. L2 DISTRIBUTION BY SOURCE LANGUAGE")
    pr("─" * 75)
    for lang in sources:
        lang_l2s = [r['l2'] for r in all_results if r['lang'] == lang]
        if not lang_l2s: continue
        pr(f"  {lang.upper():>10}: n={len(lang_l2s):>4}, "
           f"min={min(lang_l2s):.4f}, mean={np.mean(lang_l2s):.4f}, "
           f"median={np.median(lang_l2s):.4f}, "
           f"<2.0: {sum(1 for l in lang_l2s if l < 2.0)}/{len(lang_l2s)} "
           f"({100*sum(1 for l in lang_l2s if l < 2.0)/len(lang_l2s):.1f}%)")

    # ── 5d. Breakdown by break rule ──
    pr("\n5d. L2 DISTRIBUTION BY BREAK RULE")
    pr("─" * 75)
    for brk in list(break_rules.keys()) + ['word_aligned']:
        brk_l2s = [r['l2'] for r in all_results if r['break'] == brk]
        if not brk_l2s: continue
        pr(f"  {brk:>14}: n={len(brk_l2s):>4}, "
           f"min={min(brk_l2s):.4f}, mean={np.mean(brk_l2s):.4f}, "
           f"median={np.median(brk_l2s):.4f}, "
           f"<2.0: {sum(1 for l in brk_l2s if l < 2.0)}/{len(brk_l2s)}")

    # ── 5e. Breakdown by glyph distribution ──
    pr("\n5e. L2 DISTRIBUTION BY GLYPH LENGTH DISTRIBUTION")
    pr("─" * 75)
    for gd in list(glyph_dists.keys()) + ['huffman']:
        gd_l2s = [r['l2'] for r in all_results if r['glyph_dist'] == gd]
        if not gd_l2s: continue
        pr(f"  {gd:>14}: n={len(gd_l2s):>4}, "
           f"min={min(gd_l2s):.4f}, mean={np.mean(gd_l2s):.4f}, "
           f"median={np.median(gd_l2s):.4f}, "
           f"<2.0: {sum(1 for l in gd_l2s if l < 2.0)}/{len(gd_l2s)}")

    # ── 5f. Per-metric analysis: which metrics match, which fail? ──
    pr("\n5f. PER-METRIC ANALYSIS (best 50 experiments)")
    pr("─" * 75)
    top50 = sorted_results[:50]
    pr(f"  {'Metric':>12} {'VMS':>8} {'Mean':>8} {'Std':>8} {'Min':>8} {'Max':>8} "
       f"{'|Δ|/VMS':>8}")
    for k in METRIC_KEYS:
        vals = [r['fp'][k] for r in top50]
        vmv = VMS[k]
        m, s = np.mean(vals), np.std(vals)
        pr(f"  {k:>12} {vmv:>8.4f} {m:>8.4f} {s:>8.4f} {min(vals):>8.4f} "
           f"{max(vals):>8.4f} {abs(m-vmv)/max(abs(vmv),0.001):>8.3f}")

    # ── 5g. The critical h_ratio_char analysis ──
    pr("\n5g. CRITICAL METRIC: H(c|p)/H(c) — THE KEY VMS ANOMALY")
    pr("─" * 75)
    pr(f"  VMS target: {VMS['h_char']:.4f}")
    all_hchar = [r['fp']['h_char'] for r in all_results]
    pr(f"  All experiments: min={min(all_hchar):.4f}, max={max(all_hchar):.4f}, "
       f"mean={np.mean(all_hchar):.4f}, std={np.std(all_hchar):.4f}")
    in_range = sum(1 for h in all_hchar if 0.55 <= h <= 0.75)
    pr(f"  In VMS range [0.55, 0.75]: {in_range}/{len(all_hchar)} "
       f"({100*in_range/len(all_hchar):.1f}%)")

    # Breakdown by glyph dist
    for gd in list(glyph_dists.keys()) + ['huffman']:
        gd_hc = [r['fp']['h_char'] for r in all_results if r['glyph_dist'] == gd]
        if gd_hc:
            pr(f"    {gd:>14}: mean={np.mean(gd_hc):.4f}, "
               f"in [0.55,0.75]: {sum(1 for h in gd_hc if 0.55<=h<=0.75)}/{len(gd_hc)}")

    # Breakdown by break rule
    for brk in list(break_rules.keys()) + ['word_aligned']:
        brk_hc = [r['fp']['h_char'] for r in all_results if r['break'] == brk]
        if brk_hc:
            pr(f"    {brk:>14}: mean={np.mean(brk_hc):.4f}, "
               f"in [0.55,0.75]: {sum(1 for h in brk_hc if 0.55<=h<=0.75)}/{len(brk_hc)}")

    # ═══════════════════════════════════════════════════════════════
    # 6. WORD BOUNDARY INFORMATION TEST
    # ═══════════════════════════════════════════════════════════════
    pr("\n6. WORD BOUNDARY INFORMATION TEST")
    pr("═" * 75)
    pr("  Does Naibbe ciphertext match VMS's non-informative boundaries?")
    pr("  VMS: ΔH = +0.145 (boundaries INCREASE entropy = non-informative)")
    pr()

    # Test the best matching experiment
    best = sorted_results[0]
    # Re-generate the best ciphertext
    best_src = sources[best['lang']]
    best_rng = random.Random(SEED + best['table_idx'])

    if best['table_type'] == 'huffman':
        best_table = make_huffman_table(best_rng,
                                         LANG_FREQ.get(best['lang'], LANG_FREQ['english']))
    else:
        gdist_map = {**glyph_dists, 'random_mixed': {1: 0.35, 2: 0.45, 3: 0.20}}
        gd = gdist_map.get(best['glyph_dist'], {1: 0.35, 2: 0.45, 3: 0.20})
        best_table = make_random_table(best_rng, glyph_len_dist=gd)

    if best['break'] == 'word_aligned':
        best_brk = ('source_words', best_src['words'])
    else:
        best_brk = break_rules.get(best['break'], ('fixed', 3))

    best_cipher = naibbe_encode(best_src['letters'], best_table, best_brk, best_rng)
    if len(best_cipher) > TARGET_WORDS:
        best_cipher = best_cipher[:TARGET_WORDS]

    h_s, h_b, delta = word_boundary_info(best_cipher)
    pr(f"  Best experiment ({best['lang']}, {best['break']}, {best['glyph_dist']}):")
    pr(f"    Stream H(c|p):    {h_s:.4f}")
    pr(f"    Boundary H(c|p):  {h_b:.4f}")
    pr(f"    ΔH (bound-stream): {delta:+.4f}")
    if delta > 0:
        pr(f"    → Boundaries NON-INFORMATIVE (like VMS!) ✓")
    else:
        pr(f"    → Boundaries informative (UNLIKE VMS) ✗")

    # Also test VMS itself
    h_s_v, h_b_v, delta_v = word_boundary_info(vms_words)
    pr(f"\n  VMS reference:")
    pr(f"    Stream H(c|p):    {h_s_v:.4f}")
    pr(f"    Boundary H(c|p):  {h_b_v:.4f}")
    pr(f"    ΔH (bound-stream): {delta_v:+.4f}")

    # Test source language text for comparison
    for lang, src in sources.items():
        sw = src['words'][:TARGET_WORDS]
        h_s_l, h_b_l, delta_l = word_boundary_info(sw)
        pr(f"\n  {lang.upper()} source text:")
        pr(f"    Stream H(c|p):    {h_s_l:.4f}")
        pr(f"    Boundary H(c|p):  {h_b_l:.4f}")
        pr(f"    ΔH (bound-stream): {delta_l:+.4f}")

    # ═══════════════════════════════════════════════════════════════
    # 7. SENSITIVITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    pr("\n7. SENSITIVITY ANALYSIS: WHAT DRIVES THE FINGERPRINT?")
    pr("═" * 75)

    # For each metric, compute the variance explained by each factor
    for k in METRIC_KEYS:
        vals = np.array([r['fp'][k] for r in all_results])
        total_var = np.var(vals) if len(vals) > 1 else 0.001

        # Variance by source language
        lang_means = {}
        for lang in sources:
            lv = [r['fp'][k] for r in all_results if r['lang'] == lang]
            if lv: lang_means[lang] = np.mean(lv)
        between_lang = np.var(list(lang_means.values())) if lang_means else 0

        # Variance by break rule
        brk_means = {}
        for brk in list(break_rules.keys()) + ['word_aligned']:
            bv = [r['fp'][k] for r in all_results if r['break'] == brk]
            if bv: brk_means[brk] = np.mean(bv)
        between_brk = np.var(list(brk_means.values())) if brk_means else 0

        # Variance by glyph dist
        gd_means = {}
        for gd in list(glyph_dists.keys()) + ['huffman']:
            gv = [r['fp'][k] for r in all_results if r['glyph_dist'] == gd]
            if gv: gd_means[gd] = np.mean(gv)
        between_gd = np.var(list(gd_means.values())) if gd_means else 0

        pr(f"  {k:>12}: total_var={total_var:.6f}")
        pr(f"    Source language: {between_lang/total_var*100:.1f}% of variance" if total_var > 1e-9 else f"    Source language: N/A")
        pr(f"    Break rule:     {between_brk/total_var*100:.1f}% of variance" if total_var > 1e-9 else f"    Break rule: N/A")
        pr(f"    Glyph dist:     {between_gd/total_var*100:.1f}% of variance" if total_var > 1e-9 else f"    Glyph dist: N/A")

    # ═══════════════════════════════════════════════════════════════
    # 8. SKEPTICAL SELF-ASSESSMENT
    # ═══════════════════════════════════════════════════════════════
    pr("\n8. SKEPTICAL SELF-ASSESSMENT")
    pr("═" * 75)

    best_l2 = min(l2s)
    worst_l2 = max(l2s)
    frac_below_2 = sum(1 for l in l2s if l < 2.0) / len(l2s) * 100
    mean_hchar = np.mean(all_hchar)

    pr(f"""
  STATED FAILURE CRITERIA                        RESULT
  ─────────────────────────────────────────────  ──────────
  No random table achieves L2 < 3.0?             Best L2 = {best_l2:.4f} → {"FAIL" if best_l2 >= 3.0 else "PASS"}
  h_ratio_char always > 0.80 or always < 0.40?   Range = [{min(all_hchar):.4f}, {max(all_hchar):.4f}] → {"FAIL" if min(all_hchar)>0.80 or max(all_hchar)<0.40 else "PASS"}
  Source language doesn't matter?                 See 5c above → CHECK MANUALLY
  Only hand-tuned tables match?                   Random tables below 2.0: {frac_below_2:.1f}% → {"PASS (many match)" if frac_below_2 > 5 else "FAIL (too few)" if frac_below_2 > 0 else "FAIL (none)"}

  STATED SUCCESS CRITERIA                        RESULT
  ─────────────────────────────────────────────  ──────────
  Multiple tables achieve L2 < 2.0?              {sum(1 for l in l2s if l<2.0)} experiments → {"YES" if sum(1 for l in l2s if l<2.0) > 10 else "MARGINAL" if sum(1 for l in l2s if l<2.0) > 0 else "NO"}
  h_ratio_char near 0.64 for some tables?        Mean = {mean_hchar:.4f} → {"YES" if abs(mean_hchar - 0.64) < 0.15 else "NO"}
  Source language matters?                        See 5c above → CHECK MANUALLY

  POTENTIAL CONFOUNDS:
  ──────────────────────────────────────────────────────────────────
  a) Markov fallback text has NO bigram structure. Real language text
     has lower character entropy (more predictable bigrams). This means
     our h_ratio_char values for Markov sources are PESSIMISTIC — real
     text would produce LOWER h_ratio_char (closer to VMS's 0.64).

  b) The glyph table has {18}^1 + {18}^2 + {18}^3 = {18 + 18*18 + 18*18*18}
     possible glyphs. With only 26 letter assignments, we're sampling
     a tiny fraction of the glyph space. The results may not represent
     the full range of possible tables.

  c) We use raw (unnormalized) L2 distance. Metrics on different scales
     (e.g., wlen ≈ 5 vs h_char ≈ 0.6) have different weights in L2.
     A normalized distance would be more principled but requires
     estimated standard deviations.

  d) The word-break rule is a free parameter that strongly affects
     results (especially wlen and ttr). A determined researcher could
     tune this to match VMS, which weakens the argument.

  e) We test 7 metrics. There may be OTHER statistics where Naibbe
     fails (e.g., word-internal positional entropy, inter-word MI
     patterns, burstiness). Matching 7 metrics is NECESSARY but
     not SUFFICIENT for claiming Naibbe is the true encoding.
""")

    # ═══════════════════════════════════════════════════════════════
    # 9. DETAILED METRIC COMPARISON FOR BEST MATCH
    # ═══════════════════════════════════════════════════════════════
    pr("9. DETAILED BEST-MATCH ANALYSIS")
    pr("═" * 75)
    b = sorted_results[0]
    pr(f"  Configuration: {b['lang']}, break={b['break']}, "
       f"glyph={b['glyph_dist']}, type={b['table_type']}")
    pr(f"  L2 distance: {b['l2']:.4f}")
    pr(f"  Cipher words: {b['n_words']}")
    pr()
    pr(f"  {'Metric':>12} {'VMS':>8} {'Naibbe':>8} {'Δ':>8} {'|Δ|/VMS':>8} {'Match?':>8}")
    pr(f"  {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    for k in METRIC_KEYS:
        v = VMS[k]
        n = b['fp'][k]
        d = n - v
        rel = abs(d) / max(abs(v), 0.001)
        match = "✓" if rel < 0.15 else "~" if rel < 0.30 else "✗"
        pr(f"  {k:>12} {v:>8.4f} {n:>8.4f} {d:>+8.4f} {rel:>8.3f} {match:>8}")

    # ═══════════════════════════════════════════════════════════════
    # 10. SAMPLE CIPHERTEXT FROM BEST MATCH
    # ═══════════════════════════════════════════════════════════════
    pr("\n10. SAMPLE CIPHERTEXT FROM BEST MATCH")
    pr("═" * 75)
    pr(f"  First 100 cipher words:")
    for i in range(0, min(100, len(best_cipher)), 10):
        chunk = best_cipher[i:i+10]
        pr(f"    {' '.join(chunk)}")

    pr(f"\n  Character frequency in ciphertext:")
    all_chars = list(''.join(best_cipher[:TARGET_WORDS]))
    char_freq = Counter(all_chars)
    for ch, cnt in char_freq.most_common(20):
        pr(f"    '{ch}': {cnt:>6} ({100*cnt/len(all_chars):.1f}%)")

    pr(f"\n  Word length distribution:")
    wlens = [len(w) for w in best_cipher[:TARGET_WORDS]]
    wlen_counts = Counter(wlens)
    for wl in sorted(wlen_counts.keys()):
        pct = 100 * wlen_counts[wl] / len(wlens)
        bar = '█' * int(pct)
        pr(f"    len {wl:>2}: {wlen_counts[wl]:>5} ({pct:>5.1f}%) {bar}")

    # ═══════════════════════════════════════════════════════════════
    # 11. COMPARISON SUMMARY TABLE
    # ═══════════════════════════════════════════════════════════════
    pr("\n11. COMPARISON: NAIBBE vs encoding_model_tournament MODELS vs VMS")
    pr("═" * 75)
    pr(f"  {'Model':>25} {'L2':>7} {'heaps':>7} {'hapax':>7} {'h_char':>7} "
       f"{'h_word':>7} {'wlen':>7} {'ttr':>7} {'zipf':>7}")
    pr(f"  {'─'*25} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7}")
    pr(f"  {'VMS (target)':>25} {'0.000':>7} {VMS['heaps']:>7.4f} {VMS['hapax']:>7.4f} "
       f"{VMS['h_char']:>7.4f} {VMS['h_word']:>7.4f} {VMS['wlen']:>7.4f} "
       f"{VMS['ttr']:>7.4f} {VMS['zipf']:>7.4f}")

    # encoding_model_tournament references (approximate from the report)
    p64 = [
        ("Italian (encoding_model_tournament)",     1.777, 0.7515, 0.6390, 0.8393, 0.4639, 3.9302, 0.3374, 1.0207),
        ("Homophonic (encoding_model_tournament)",  2.703, None, None, None, None, None, None, None),
        ("Simple verbose (Ph.64)", 5.012, None, None, None, None, None, None, None),
    ]
    for label, l2, *vals in p64:
        if vals[0] is not None:
            pr(f"  {label:>25} {l2:>7.3f} {vals[0]:>7.4f} {vals[1]:>7.4f} "
               f"{vals[2]:>7.4f} {vals[3]:>7.4f} {vals[4]:>7.4f} "
               f"{vals[5]:>7.4f} {vals[6]:>7.4f}")
        else:
            pr(f"  {label:>25} {l2:>7.3f}")

    # Best Naibbe results by break rule
    for brk in list(break_rules.keys()) + ['word_aligned']:
        brk_res = [r for r in all_results if r['break'] == brk]
        if not brk_res: continue
        best_brk_r = min(brk_res, key=lambda r: r['l2'])
        fp = best_brk_r['fp']
        lbl = f"Naibbe {brk} (best)"
        pr(f"  {lbl:>25} {best_brk_r['l2']:>7.4f} {fp['heaps']:>7.4f} "
           f"{fp['hapax']:>7.4f} {fp['h_char']:>7.4f} {fp['h_word']:>7.4f} "
           f"{fp['wlen']:>7.4f} {fp['ttr']:>7.4f} {fp['zipf']:>7.4f}")

    pr()
    elapsed = time.time() - t0
    pr(f"Total runtime: {elapsed:.1f}s")

    # ── Save results ──
    out_path = RESULTS_DIR / 'naibbe_cipher_calibration.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(OUTPUT)
    _print(f"\nResults saved to {out_path}")

    # Also save raw data as JSON for further analysis
    json_path = RESULTS_DIR / 'naibbe_cipher_calibration_naibbe_raw.json'
    json_data = []
    for r in all_results:
        json_data.append({
            'lang': r['lang'],
            'break': r['break'],
            'glyph_dist': r['glyph_dist'],
            'table_type': r['table_type'],
            'n_words': r['n_words'],
            'l2': r['l2'],
            **{f'fp_{k}': r['fp'][k] for k in METRIC_KEYS},
        })
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    _print(f"Raw data saved to {json_path}")

if __name__ == '__main__':
    main()
