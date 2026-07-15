#!/usr/bin/env python3
"""
Phase 73 — Medieval Abbreviation/Shorthand Model vs VMS Fingerprint
═════════════════════════════════════════════════════════════════════

QUESTION:  Could the VMS be a natural language (Latin, Italian, Czech)
           written in an abbreviated notation system — like medieval
           pharmaceutical/recipe shorthand — in an invented script?

MOTIVATION (from Phase 70C and 72):
- Davis's codicological evidence (5 scribes, heavy use, bifolium
  organization) rules out complex ciphers; the system must be
  learnable and practical for a community of readers.
- Phase 72 showed Naibbe verbose cipher partially matches VMS but
  systematically fails 4/7 metrics (hapax, h_word, TTR, Zipf) and
  completely fails the word-boundary test.
- An abbreviation/shorthand system is the remaining candidate that
  is (a) community-learnable, (b) historically plausible, and (c)
  untested against the VMS fingerprint.

WHAT WE ARE MODELING:
Medieval Latin manuscripts used extensive abbreviation systems. The
rules are well-documented in Cappelli's "Lexicon Abbreviaturarum" (1899,
still the standard reference) and standard paleography textbooks.

We model three categories of abbreviation:
  1. SUSPENSION: Truncate word endings. -us, -um, -tur etc. become
     a single abbreviation mark. (e.g., "dominus" → "domin" + mark)
  2. CONTRACTION: Omit interior letters, keep start/end.
     (e.g., "noster" → "nr" + mark, "dominus" → "dns" + mark)
  3. SPECIAL SYMBOLS: Common words/prefixes become single symbols.
     (e.g., "et" → single char, "con-" → mark + rest, "per-" → mark)

IMPORTANT CAVEATS:
  a) We are MODELING abbreviation rules, not using data from actual
     abbreviated manuscripts. Our model approximates but does not
     replicate real scribal practice.
  b) Abbreviation density varied widely between scribes and document
     types. We test a range of densities.
  c) After abbreviation, we map to a ~20-char "VMS-like" alphabet.
     The mapping is arbitrary — this tests the STATISTICAL EFFECT
     of abbreviation, not any specific script hypothesis.
  d) We also test a SYLLABIC model where common Latin syllables are
     mapped to single characters, as an alternative shorthand theory.

FAILURE CRITERIA:
- If all abbreviation models produce L2 > 3.0 → abbreviation doesn't help
- If h_char stays near 0.84 (natural language level) → abbreviation
  doesn't reduce character predictability enough
- If word-boundary test ΔH is always strongly negative → abbreviation
  doesn't fix the boundary problem either
- If results match equally well with random character mappings → the
  abbreviation structure is irrelevant

SUCCESS CRITERIA:
- Some abbreviation levels produce L2 < 1.0
- h_char drops toward 0.64 (the VMS anomaly)
- Word boundary information is reduced (ΔH closer to 0 or positive)
- The model explains WHY VMS has specific metric values

VMS TARGET FINGERPRINT (from Phase 64):
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
from common import load_vms_words

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
TARGET_WORDS = 36000

# VMS-like alphabet (~20 chars)
ALPHA = list('acdefhiklnopqrsty')  # 18 EVA chars

VMS = {
    'heaps': 0.7533,
    'hapax':  0.6555,
    'h_char': 0.6407,
    'h_word': 0.4448,
    'wlen':   4.9352,
    'ttr':    0.3420,
    'zipf':   0.9415,
}
METRIC_KEYS = ['heaps', 'hapax', 'h_char', 'h_word', 'wlen', 'ttr', 'zipf']

# ═══════════════════════════════════════════════════════════════════════
# FINGERPRINT FUNCTIONS (shared with Phase 72)
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

def fp(words):
    return {
        'heaps': heaps_exponent(words),
        'hapax': hapax_at_mid(words),
        'h_char': h_ratio_char(words),
        'h_word': h_ratio_word(words),
        'wlen': mean_wlen(words),
        'ttr': ttr_5k(words),
        'zipf': zipf_alpha(words),
    }

def l2(f):
    return math.sqrt(sum((f[k] - VMS[k])**2 for k in METRIC_KEYS))

def word_boundary_info(words):
    """Word boundary information test. Returns (stream_h, boundary_h, delta)."""
    chars = list(''.join(words))
    if len(chars) < 200:
        return (0, 0, 0)
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

    BOUND = '|'
    bchars = []
    for w in words:
        bchars.append(BOUND)
        bchars.extend(list(w))
    bi_b = Counter()
    for i in range(1, len(bchars)):
        bi_b[(bchars[i-1], bchars[i])] += 1
    tot_b = sum(bi_b.values())
    h_joint_b = -sum((c/tot_b)*math.log2(c/tot_b) for c in bi_b.values() if c > 0)
    prev_b = Counter()
    for (c1,c2), cnt in bi_b.items(): prev_b[c1] += cnt
    ptot_b = sum(prev_b.values())
    h_prev_b = -sum((c/ptot_b)*math.log2(c/ptot_b) for c in prev_b.values() if c > 0)
    h_bound = h_joint_b - h_prev_b

    return (h_stream, h_bound, h_bound - h_stream)

# ═══════════════════════════════════════════════════════════════════════
# SOURCE TEXT LOADING
# ═══════════════════════════════════════════════════════════════════════

def fetch_gutenberg(ebook_id):
    url = f'https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (VMS-Research)'})
    resp = urllib.request.urlopen(req, timeout=30)
    data = resp.read().decode('utf-8', errors='replace')
    start = data.find('*** START OF')
    end   = data.find('*** END OF')
    if start > 0 and end > 0:
        return data[data.index('\n', start)+1:end]
    return data

def strip_diacritics(text):
    nfkd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')

def load_latin():
    """Load Latin text preserving case for abbreviation (needed for suffix matching)."""
    pr(f"  Fetching Latin (Caesar, Gutenberg #10657)...")
    try:
        raw = fetch_gutenberg(10657)
        # Keep case initially for proper abbreviation matching
        text = raw.lower()
        text = re.sub(r'[^a-z ]+', '', text)
        text = re.sub(r' +', ' ', text).strip()
        words = text.split()
        pr(f"  OK: {len(text)} chars, {len(words)} words")
        return words
    except Exception as e:
        pr(f"  FAILED: {e}")
        return []

def load_italian():
    pr(f"  Fetching Italian (Dante, Gutenberg #1012)...")
    try:
        raw = fetch_gutenberg(1012)
        text = raw.lower()
        text = re.sub(r'[^a-z ]+', '', text)
        text = re.sub(r' +', ' ', text).strip()
        words = text.split()
        pr(f"  OK: {len(text)} chars, {len(words)} words")
        return words
    except Exception as e:
        pr(f"  FAILED: {e}")
        return []

def load_czech():
    """Load Bible Kralická 1613 from local files."""
    import glob
    bible_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'czech_bible_kralice')
    if not os.path.isdir(bible_dir):
        pr(f"  Bible Kralická directory not found at {bible_dir}")
        return []
    txt_files = sorted(glob.glob(os.path.join(bible_dir, '*_read.txt')))
    pr(f"  Loading Bible Kralická 1613 from {len(txt_files)} chapter files...")
    combined = []
    for tf in txt_files:
        with open(tf, 'r', encoding='utf-8') as fh:
            raw = fh.read()
        text = strip_diacritics(raw.lower())
        text = re.sub(r'[^a-z ]+', '', text)
        text = re.sub(r' +', ' ', text).strip()
        if text:
            combined.extend(text.split())
    pr(f"  OK: {len(combined)} words")
    return combined


# ═══════════════════════════════════════════════════════════════════════
# MODEL A: MEDIEVAL LATIN ABBREVIATION
# ═══════════════════════════════════════════════════════════════════════
#
# We implement documented medieval Latin abbreviation conventions.
# Sources: Cappelli (1899), Bischoff (1990), Parkes (1992).
#
# The rules are simplified — real scribal practice was more variable
# and context-dependent. We model the STATISTICAL EFFECT, not every
# individual scribal decision.

# Common Latin word abbreviations (word → abbreviated form)
# We use special chars 1-9 and A-Z uppercase as "abbreviation marks"
# to represent scribal symbols (tildes, hooks, special characters)
# that have no direct ASCII equivalent.
#
# NOTE: These mappings approximate DOCUMENTED medieval practice but are
# necessarily simplified. Real scribes had hundreds of abbreviations.
WORD_ABBREVIATIONS = {
    # Function words (very high frequency, often abbreviated)
    'et': '7',           # Tironian et (single symbol, universal)
    'est': 'e3',         # e + stroke
    'sunt': 's3',        # s + mark
    'non': 'n4',         # n + bar
    'sed': 's9',         # s + mark
    'enim': 'en',        # contraction
    'autem': 'at',       # contraction (a + t, very common)
    'tamen': 'tn',       # contraction
    'igitur': 'ig',      # contraction
    'quod': 'qd',        # contraction (universal)
    'quam': 'q8',        # q + mark
    'quia': 'qa',        # contraction
    'quasi': 'qs',       # contraction
    'cum': '9',          # single symbol (common)
    'aut': 'a3',         # a + mark
    'vel': 'vl',         # contraction
    'sicut': 'sic3',     # contraction
    'ergo': 'eg',        # contraction
    'ideo': 'io',        # contraction
    'item': 'it',        # contraction
    'etiam': 'et8',      # common contraction
    'vero': 'vo',        # contraction
    'ante': 'a5',        # contraction
    'post': 'p3',        # contraction
    'inter': 'i5',       # contraction
    'unde': 'u5',        # contraction
    'inde': 'i5e',       # contraction
    'eius': 'ei9',       # contraction
    'esse': 'ee',        # contraction
    'deus': 'ds',        # nomina sacra
    'dominus': 'dns',    # nomina sacra
    'christus': 'xps',   # nomina sacra (Christogram)
    'jesus': 'ihs',      # nomina sacra
    'spiritus': 'sps',   # nomina sacra
    'sanctus': 'scs',    # nomina sacra
    'ecclesia': 'eccla',  # nomina sacra
    'noster': 'nr',      # very common contraction
    'vester': 'vr',      # analogous
}

# Suffix abbreviations: word endings replaced by marks
# Format: (suffix, min_remaining_length, mark)
# A word like "dominus" → "domin" + mark for -us
# We only abbreviate if at least min_remaining chars would remain
SUFFIX_RULES = [
    ('ibus', 2, '1'),    # dative/ablative plural
    ('orum', 2, '2'),    # genitive plural
    ('orum', 2, '2'),
    ('ione', 2, '3'),    # -tion- forms
    ('tur',  2, '4'),    # passive verb endings
    ('bus',  2, '1'),    # -bus endings
    ('rum',  2, '2'),    # -rum endings
    ('tis',  2, '5'),    # 2nd person plural
    ('mus',  2, '6'),    # 1st person plural
    ('unt',  2, '3'),    # 3rd person plural
    ('us',   2, '1'),    # extremely common
    ('um',   2, '2'),    # extremely common
    ('ur',   2, '4'),    # passive
    ('er',   2, '5'),    # agent nouns, comparatives
    ('em',   2, '2'),    # accusative singular
    ('is',   2, '5'),    # genitive/dative
    ('it',   2, '3'),    # 3rd person singular
    ('am',   2, '6'),    # 1st declension accusative
    ('os',   2, '1'),    # 2nd declension acc. plural
    ('as',   2, '6'),    # 1st declension acc. plural
]

# Prefix abbreviations: common prefixes get compressed
# Format: (prefix, replacement)
PREFIX_RULES = [
    ('contra', 'c4a'),
    ('contr', 'c4'),
    ('cons',  'c4s'),
    ('con',   'c4'),
    ('com',   'c4'),
    ('per',   'p8'),
    ('par',   'p8'),
    ('prae',  'p6'),
    ('pre',   'p6'),
    ('pro',   'p5'),
    ('trans', 't5'),
    ('super', 's6'),
    ('inter', 'i5'),
]

# Nasal bar: m or n before a consonant → tilde mark (compresses 1 char)
VOWELS = set('aeiou')


def abbreviate_word(word, density, rng):
    """Apply medieval abbreviation rules to a single word.
    
    density: float 0.0–1.0, probability of applying each rule.
             Medieval pharmaceutical MSS could be very heavily abbreviated
             (density ~0.6-0.8); literary texts less so (~0.2-0.4).
    """
    # 1. Check whole-word abbreviations first
    if word in WORD_ABBREVIATIONS and rng.random() < density:
        return WORD_ABBREVIATIONS[word]
    
    result = word
    
    # 2. Try prefix abbreviation
    for prefix, repl in PREFIX_RULES:
        if result.startswith(prefix) and len(result) > len(prefix) + 1:
            if rng.random() < density * 0.7:  # slightly less frequent than suffix
                result = repl + result[len(prefix):]
            break
    
    # 3. Try suffix abbreviation
    for suffix, min_rem, mark in SUFFIX_RULES:
        if result.endswith(suffix) and len(result) - len(suffix) >= min_rem:
            if rng.random() < density * 0.9:  # very commonly abbreviated
                result = result[:-len(suffix)] + mark
            break
    
    # 4. Nasal bar: replace m/n before consonant with mark
    if len(result) >= 3 and rng.random() < density * 0.5:
        new = []
        i = 0
        while i < len(result):
            if i < len(result) - 1 and result[i] in 'mn' and result[i+1] not in VOWELS and result[i+1].isalpha():
                new.append('8')  # nasal bar mark
                # skip the m/n
            else:
                new.append(result[i])
            i += 1
        result = ''.join(new)
    
    return result


def abbreviate_text(words, density, rng):
    """Apply abbreviation to a list of words. Returns new word list."""
    return [abbreviate_word(w, density, rng) for w in words]


# ═══════════════════════════════════════════════════════════════════════
# MODEL B: SYLLABIC SHORTHAND
# ═══════════════════════════════════════════════════════════════════════
#
# Alternative model: common syllables are written as single characters.
# This is inspired by shorthand systems and syllabaries, though we note
# that no specific medieval Latin syllabary is documented for this period.
# We test this as a HYPOTHETICAL model.
#
# Approach:
# 1. Extract all syllables from the source text (using a simple rule)
# 2. Rank by frequency
# 3. Map top-N syllables to single characters
# 4. Map remaining syllables to digraphs
# 5. Words are sequences of (mapped) syllables

CONSONANTS = set('bcdfghjklmnpqrstvwxyz')

def syllabify_latin(word):
    """Simple Latin syllabification (approximate).
    Rules: split before consonant+vowel sequences.
    This is an approximation — real Latin syllabification has more rules."""
    if len(word) <= 2:
        return [word]
    
    syllables = []
    current = word[0]
    for i in range(1, len(word)):
        ch = word[i]
        prev = word[i-1]
        # Split before a consonant that precedes a vowel
        if (ch in CONSONANTS and i + 1 < len(word) and word[i+1] in VOWELS
            and len(current) >= 1 and current[-1] in VOWELS):
            syllables.append(current)
            current = ch
        else:
            current += ch
    if current:
        syllables.append(current)
    return syllables


def build_syllable_table(words, n_single=40, rng=None):
    """Build a mapping from syllables to output characters.
    Top n_single syllables → single output chars (a-z, then 0-9, etc.)
    Remaining → two-char combinations from a small alphabet.
    """
    # Count syllable frequencies
    syl_freq = Counter()
    for word in words[:50000]:  # sample for efficiency
        syls = syllabify_latin(word)
        for s in syls:
            syl_freq[s] += 1
    
    # Single-char outputs for top syllables
    output_chars = list('acdefhiklnopqrsty')  # 18 EVA chars
    
    # Build mapping
    ranked = [s for s, _ in syl_freq.most_common()]
    mapping = {}
    
    # Top syllables get single chars
    for i, syl in enumerate(ranked[:min(n_single, len(output_chars))]):
        mapping[syl] = output_chars[i % len(output_chars)]
    
    # Remaining get digraphs
    digraph_idx = 0
    for syl in ranked[min(n_single, len(output_chars)):]:
        c1 = output_chars[digraph_idx % len(output_chars)]
        c2 = output_chars[(digraph_idx // len(output_chars)) % len(output_chars)]
        mapping[syl] = c1 + c2
        digraph_idx += 1
    
    return mapping, syl_freq


def syllabic_encode(words, syl_map):
    """Encode words using syllabic mapping. Preserves word boundaries."""
    output = []
    for word in words:
        syls = syllabify_latin(word)
        encoded = ''.join(syl_map.get(s, s) for s in syls)
        if encoded:
            output.append(encoded)
    return output


# ═══════════════════════════════════════════════════════════════════════
# MODEL C: ABBREVIATION + ALPHABET MAPPING
# ═══════════════════════════════════════════════════════════════════════
#
# After abbreviation, map the resulting character set (a-z + marks 1-9)
# to a ~20-character "VMS-like" alphabet. This simulates writing
# abbreviated text in an invented script.

def map_to_alphabet(words, rng):
    """Map abbreviated text characters to a ~20-char alphabet.
    Characters in the abbreviated text include a-z and marks 1-9.
    We randomly assign each to one of ~18 output characters."""
    # Collect all unique chars in the abbreviated text
    all_chars = set()
    for w in words:
        all_chars.update(w)
    all_chars = sorted(all_chars)
    
    # Create a random mapping to EVA chars
    mapping = {}
    for ch in all_chars:
        mapping[ch] = rng.choice(ALPHA)
    
    # Apply mapping
    output = []
    for w in words:
        mapped = ''.join(mapping[c] for c in w)
        if mapped:
            output.append(mapped)
    return output, mapping


# ═══════════════════════════════════════════════════════════════════════
# MAIN EXPERIMENT
# ═══════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    pr("=" * 75)
    pr("PHASE 73: MEDIEVAL ABBREVIATION/SHORTHAND MODEL vs VMS FINGERPRINT")
    pr("Can abbreviation systems reproduce the VMS statistical signature?")
    pr("=" * 75)
    
    # ── 1. Load VMS reference ──
    pr()
    pr("1. LOADING VMS REFERENCE")
    pr("─" * 75)
    vms_words = load_vms_words()
    pr(f"  VMS: {len(vms_words)} words, {len(set(vms_words))} types")
    vms_fp = fp(vms_words)
    pr("  Fingerprint:")
    for k in METRIC_KEYS:
        pr(f"    {k:12s} = {vms_fp[k]:.4f}  (target: {VMS[k]:.4f})")
    
    vms_sh, vms_bh, vms_delta = word_boundary_info(vms_words)
    pr(f"  Word boundary test: stream_H={vms_sh:.4f}, bound_H={vms_bh:.4f}, ΔH={vms_delta:.4f}")

    # ── 2. Load source texts ──
    pr()
    pr("2. LOADING SOURCE TEXTS")
    pr("─" * 75)
    sources = {}
    
    pr()
    pr("  [LATIN]")
    sources['latin'] = load_latin()
    
    pr()
    pr("  [ITALIAN]")
    sources['italian'] = load_italian()
    
    pr()
    pr("  [CZECH]")
    sources['czech'] = load_czech()
    
    # Filter empty
    sources = {k: v for k, v in sources.items() if v}
    
    if not sources:
        pr("  ERROR: No source texts loaded!")
        return
    
    # Print raw fingerprints
    pr()
    pr("  Source language raw fingerprints (first 36000 words):")
    for name, words in sorted(sources.items()):
        sub = words[:TARGET_WORDS]
        sfp = fp(sub)
        pr(f"    [{name.upper()}]")
        for k in METRIC_KEYS:
            delta = sfp[k] - VMS[k]
            pr(f"      {k:12s} = {sfp[k]:.4f}  (VMS: {VMS[k]:.4f}, Δ={delta:+.4f})")

    # ── 3. Experiment design ──
    pr()
    pr("3. EXPERIMENT DESIGN")
    pr("─" * 75)
    
    # Abbreviation densities to test
    # 0.0 = no abbreviation (baseline), up to 0.9 = very heavy abbreviation
    densities = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    n_tables = 20  # random alphabet mappings per config
    
    models = ['abbrev_raw', 'abbrev_mapped', 'syllabic']
    
    n_abbrev = len(sources) * len(densities) * n_tables  # abbrev mapped
    n_abbrev_raw = len(sources) * len(densities)          # abbrev raw (no random mapping)
    n_syllabic = len(sources) * 3 * n_tables              # 3 syllable configs
    total = n_abbrev + n_abbrev_raw + n_syllabic
    
    pr(f"  Model A (abbreviation, raw chars): {n_abbrev_raw} experiments")
    pr(f"  Model B (abbreviation + alphabet map): {n_abbrev} experiments")
    pr(f"  Model C (syllabic encoding): {n_syllabic} experiments")
    pr(f"  TOTAL: ~{total} experiments")
    
    # ── 4. Run experiments ──
    pr()
    pr("4. RUNNING EXPERIMENTS")
    pr("═" * 75)
    
    all_results = []
    rng = random.Random(SEED)
    exp_count = 0
    
    # ── 4A: Abbreviation model (raw chars — before alphabet mapping) ──
    pr()
    pr("4A. ABBREVIATION MODEL — RAW CHARACTER STATISTICS")
    pr("─" * 75)
    pr("  (Abbreviated text in original Latin chars + marks, no alphabet mapping)")
    pr("  This shows the DIRECT effect of abbreviation on entropy/statistics.")
    pr()
    
    for name, src_words in sorted(sources.items()):
        pr(f"  [{name.upper()}]")
        for density in densities:
            # Use deterministic seed per config
            local_rng = random.Random(SEED + hash((name, density)))
            abbrev_words = abbreviate_text(src_words[:TARGET_WORDS * 2], density, local_rng)
            # Trim to target
            abbrev_words = abbrev_words[:TARGET_WORDS]
            if len(abbrev_words) < 1000:
                continue
            
            f_val = fp(abbrev_words)
            dist = l2(f_val)
            sh, bh, delta = word_boundary_info(abbrev_words)
            
            # Count unique chars to see alphabet size
            all_chars = set()
            for w in abbrev_words:
                all_chars.update(w)
            
            result = {
                'model': 'abbrev_raw',
                'source': name,
                'density': density,
                'table_id': 0,
                'l2': dist,
                'n_chars': len(all_chars),
                'wbi_delta': delta,
                **f_val,
            }
            all_results.append(result)
            exp_count += 1
            
            if density in [0.0, 0.3, 0.6, 0.9]:
                pr(f"    density={density:.1f}: L2={dist:.4f}, |Σ|={len(all_chars):2d}, "
                   f"h_char={f_val['h_char']:.4f}, wlen={f_val['wlen']:.4f}, "
                   f"zipf={f_val['zipf']:.4f}, ΔH_bound={delta:.4f}")
        pr()
    
    # ── 4B: Abbreviation + random alphabet mapping ──
    pr()
    pr("4B. ABBREVIATION + RANDOM ALPHABET MAPPING")
    pr("─" * 75)
    pr("  (Abbreviated text mapped to ~18-char EVA-like alphabet)")
    pr()
    
    for name, src_words in sorted(sources.items()):
        pr(f"  [{name.upper()}]", end='')
        for density in densities:
            local_rng = random.Random(SEED + hash((name, density)))
            abbrev_words = abbreviate_text(src_words[:TARGET_WORDS * 2], density, local_rng)
            abbrev_words = abbrev_words[:TARGET_WORDS]
            if len(abbrev_words) < 1000:
                continue
            
            for table_id in range(n_tables):
                map_rng = random.Random(SEED + hash((name, density, table_id)))
                mapped_words, _ = map_to_alphabet(abbrev_words, map_rng)
                mapped_words = mapped_words[:TARGET_WORDS]
                
                f_val = fp(mapped_words)
                dist = l2(f_val)
                sh, bh, delta = word_boundary_info(mapped_words)
                
                result = {
                    'model': 'abbrev_mapped',
                    'source': name,
                    'density': density,
                    'table_id': table_id,
                    'l2': dist,
                    'n_chars': len(set(''.join(mapped_words))),
                    'wbi_delta': delta,
                    **f_val,
                }
                all_results.append(result)
                exp_count += 1
        
        pr(f" done ({exp_count} total)")
    
    # ── 4C: Syllabic encoding ──
    pr()
    pr("4C. SYLLABIC ENCODING MODEL")
    pr("─" * 75)
    pr("  (Words broken into syllables, common syllables → single chars)")
    pr()
    
    syllable_configs = [
        ('syl_10', 10),    # Only top 10 syllables get single chars
        ('syl_20', 20),    # Top 20
        ('syl_40', 40),    # Top 40 (most aggressive compression)
    ]
    
    for name, src_words in sorted(sources.items()):
        pr(f"  [{name.upper()}]", end='')
        
        for config_name, n_single in syllable_configs:
            local_rng = random.Random(SEED + hash((name, config_name)))
            syl_map, syl_freq = build_syllable_table(src_words, n_single, local_rng)
            encoded = syllabic_encode(src_words[:TARGET_WORDS * 2], syl_map)
            encoded = encoded[:TARGET_WORDS]
            
            if len(encoded) < 1000:
                continue
            
            # Base fingerprint (syllabic encoding preserves words)
            f_base = fp(encoded)
            dist_base = l2(f_base)
            sh, bh, delta = word_boundary_info(encoded)
            
            result = {
                'model': f'syllabic_{config_name}',
                'source': name,
                'density': n_single,
                'table_id': 0,
                'l2': dist_base,
                'n_chars': len(set(''.join(encoded))),
                'wbi_delta': delta,
                **f_base,
            }
            all_results.append(result)
            exp_count += 1
            
            # Also test with random alphabet mapping
            for table_id in range(n_tables):
                map_rng = random.Random(SEED + hash((name, config_name, table_id)))
                mapped_words, _ = map_to_alphabet(encoded, map_rng)
                mapped_words = mapped_words[:TARGET_WORDS]
                
                f_val = fp(mapped_words)
                dist = l2(f_val)
                sh2, bh2, delta2 = word_boundary_info(mapped_words)
                
                result = {
                    'model': f'syllabic_{config_name}_mapped',
                    'source': name,
                    'density': n_single,
                    'table_id': table_id,
                    'l2': dist,
                    'n_chars': len(set(''.join(mapped_words))),
                    'wbi_delta': delta2,
                    **f_val,
                }
                all_results.append(result)
                exp_count += 1
        
        pr(f" done ({exp_count} total)")
    
    pr()
    pr(f"  Total experiments: {exp_count}")
    pr(f"  Elapsed: {time.time()-t0:.1f}s")
    
    # ═══════════════════════════════════════════════════════════════════
    # 5. RESULTS ANALYSIS
    # ═══════════════════════════════════════════════════════════════════
    pr()
    pr("5. RESULTS ANALYSIS")
    pr("═" * 75)
    
    # ── 5a: Overall L2 distribution ──
    pr()
    pr("5a. L2 DISTANCE DISTRIBUTION (all experiments)")
    pr("─" * 75)
    l2s = [r['l2'] for r in all_results]
    pr(f"  Min L2:    {min(l2s):.4f}")
    pr(f"  Max L2:    {max(l2s):.4f}")
    pr(f"  Mean L2:   {np.mean(l2s):.4f}")
    pr(f"  Median L2: {np.median(l2s):.4f}")
    pr(f"  L2 < 0.5: {sum(1 for x in l2s if x < 0.5)}/{len(l2s)} ({sum(1 for x in l2s if x < 0.5)/len(l2s)*100:.1f}%)")
    pr(f"  L2 < 1.0: {sum(1 for x in l2s if x < 1.0)}/{len(l2s)} ({sum(1 for x in l2s if x < 1.0)/len(l2s)*100:.1f}%)")
    pr(f"  L2 < 2.0: {sum(1 for x in l2s if x < 2.0)}/{len(l2s)} ({sum(1 for x in l2s if x < 2.0)/len(l2s)*100:.1f}%)")
    
    pr()
    pr("  Phase 64/72 reference distances:")
    pr("    Italian (Phase 64 best raw):   1.777")
    pr("    Naibbe best (Phase 72):        0.3412")
    pr("    Naibbe variable mean:          1.0387")
    
    # ── 5b: By model type ──
    pr()
    pr("5b. L2 DISTRIBUTION BY MODEL TYPE")
    pr("─" * 75)
    for model_prefix in ['abbrev_raw', 'abbrev_mapped', 'syllabic']:
        subset = [r for r in all_results if r['model'].startswith(model_prefix)]
        if not subset:
            continue
        l2s_sub = [r['l2'] for r in subset]
        pr(f"  {model_prefix:25s}: n={len(subset):4d}, min={min(l2s_sub):.4f}, "
           f"mean={np.mean(l2s_sub):.4f}, median={np.median(l2s_sub):.4f}, "
           f"<1.0: {sum(1 for x in l2s_sub if x < 1.0)}/{len(subset)}")
    
    # ── 5c: By source language ──
    pr()
    pr("5c. L2 DISTRIBUTION BY SOURCE LANGUAGE")
    pr("─" * 75)
    for lang in sorted(set(r['source'] for r in all_results)):
        subset = [r for r in all_results if r['source'] == lang]
        l2s_sub = [r['l2'] for r in subset]
        pr(f"  {lang.upper():12s}: n={len(subset):4d}, min={min(l2s_sub):.4f}, "
           f"mean={np.mean(l2s_sub):.4f}, <1.0: {sum(1 for x in l2s_sub if x < 1.0)}/{len(subset)}")
    
    # ── 5d: Abbreviation density effect ──
    pr()
    pr("5d. ABBREVIATION DENSITY EFFECT (abbreviation models only)")
    pr("─" * 75)
    pr(f"  {'Density':>8s} {'Min L2':>8s} {'Mean L2':>8s} {'h_char':>8s} {'wlen':>8s} {'zipf':>8s} {'ΔH_bnd':>8s}")
    pr(f"  {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    
    for density in densities:
        subset = [r for r in all_results 
                  if r['model'] in ('abbrev_raw', 'abbrev_mapped') 
                  and r['density'] == density]
        if not subset:
            continue
        l2s_sub = [r['l2'] for r in subset]
        hc = np.mean([r['h_char'] for r in subset])
        wl = np.mean([r['wlen'] for r in subset])
        zp = np.mean([r['zipf'] for r in subset])
        bd = np.mean([r['wbi_delta'] for r in subset])
        pr(f"  {density:8.1f} {min(l2s_sub):8.4f} {np.mean(l2s_sub):8.4f} "
           f"{hc:8.4f} {wl:8.4f} {zp:8.4f} {bd:8.4f}")
    
    pr(f"\n  VMS reference: h_char={VMS['h_char']:.4f}, wlen={VMS['wlen']:.4f}, "
       f"zipf={VMS['zipf']:.4f}, ΔH_bnd={vms_delta:.4f}")
    
    # ── 5e: Top 20 best matches ──
    pr()
    pr("5e. TOP 20 BEST-MATCHING EXPERIMENTS")
    pr("─" * 75)
    sorted_results = sorted(all_results, key=lambda r: r['l2'])
    
    pr(f"  {'Rank':>4s} {'L2':>8s} {'Model':>25s} {'Source':>8s} {'Dens':>6s} "
       f"{'heaps':>7s} {'hapax':>7s} {'h_chr':>7s} {'h_wrd':>7s} "
       f"{'wlen':>7s} {'ttr':>7s} {'zipf':>7s} {'ΔH_b':>7s}")
    pr(f"  {'─'*4} {'─'*8} {'─'*25} {'─'*8} {'─'*6} "
       f"{'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7}")
    pr(f"  {'VMS':>4s} {'0.000':>8s} {'':>25s} {'':>8s} {'':>6s} "
       f"{VMS['heaps']:7.4f} {VMS['hapax']:7.4f} {VMS['h_char']:7.4f} {VMS['h_word']:7.4f} "
       f"{VMS['wlen']:7.4f} {VMS['ttr']:7.4f} {VMS['zipf']:7.4f} {vms_delta:7.4f}")
    
    for i, r in enumerate(sorted_results[:20]):
        dens_str = f"{r['density']:.1f}" if isinstance(r['density'], float) else str(r['density'])
        pr(f"  {i+1:4d} {r['l2']:8.4f} {r['model']:>25s} {r['source']:>8s} {dens_str:>6s} "
           f"{r['heaps']:7.4f} {r['hapax']:7.4f} {r['h_char']:7.4f} {r['h_word']:7.4f} "
           f"{r['wlen']:7.4f} {r['ttr']:7.4f} {r['zipf']:7.4f} {r['wbi_delta']:7.4f}")
    
    # ── 5f: h_char analysis (the key VMS anomaly) ──
    pr()
    pr("5f. CRITICAL METRIC: H(c|p)/H(c) — THE KEY VMS ANOMALY")
    pr("─" * 75)
    pr(f"  VMS target: {VMS['h_char']:.4f}")
    pr()
    
    for model_prefix in ['abbrev_raw', 'abbrev_mapped', 'syllabic']:
        subset = [r for r in all_results if r['model'].startswith(model_prefix)]
        if not subset:
            continue
        hcs = [r['h_char'] for r in subset]
        in_range = sum(1 for x in hcs if 0.55 <= x <= 0.75)
        pr(f"  {model_prefix:25s}: mean={np.mean(hcs):.4f}, min={min(hcs):.4f}, "
           f"max={max(hcs):.4f}, in [0.55,0.75]: {in_range}/{len(subset)}")
    
    # ── 5g: Word boundary test ──
    pr()
    pr("5g. WORD BOUNDARY INFORMATION TEST")
    pr("─" * 75)
    pr(f"  VMS: ΔH = {vms_delta:+.4f} (positive = non-informative boundaries)")
    pr()
    
    for model_prefix in ['abbrev_raw', 'abbrev_mapped', 'syllabic']:
        subset = [r for r in all_results if r['model'].startswith(model_prefix)]
        if not subset:
            continue
        deltas = [r['wbi_delta'] for r in subset]
        n_positive = sum(1 for x in deltas if x > 0)
        pr(f"  {model_prefix:25s}: mean ΔH={np.mean(deltas):+.4f}, "
           f"min={min(deltas):+.4f}, max={max(deltas):+.4f}, "
           f"positive (like VMS): {n_positive}/{len(subset)}")
    
    pr()
    pr("  CRITICAL: VMS boundaries are non-informative (ΔH > 0).")
    pr("  Natural language text has informative boundaries (ΔH < 0).")
    pr("  If abbreviation preserves word boundaries, it should also preserve ΔH < 0.")
    
    # ── 5h: Per-metric analysis for best experiments ──
    pr()
    pr("5h. PER-METRIC ANALYSIS (best 30 experiments)")
    pr("─" * 75)
    top30 = sorted_results[:30]
    pr(f"  {'Metric':>10s} {'VMS':>8s} {'Mean':>8s} {'Std':>8s} {'Min':>8s} {'Max':>8s} {'|Δ|/VMS':>8s}")
    for k in METRIC_KEYS:
        vals = [r[k] for r in top30]
        mean_val = np.mean(vals)
        delta_rel = abs(mean_val - VMS[k]) / max(abs(VMS[k]), 0.001)
        pr(f"  {k:>10s} {VMS[k]:8.4f} {mean_val:8.4f} {np.std(vals):8.4f} "
           f"{min(vals):8.4f} {max(vals):8.4f} {delta_rel:8.3f}")
    
    # ── 6. Detailed best match analysis ──
    pr()
    pr("6. DETAILED BEST-MATCH ANALYSIS")
    pr("═" * 75)
    best = sorted_results[0]
    pr(f"  Configuration: {best['model']}, source={best['source']}, density={best['density']}")
    pr(f"  L2 distance: {best['l2']:.4f}")
    pr()
    pr(f"  {'Metric':>12s} {'VMS':>8s} {'Model':>8s} {'Δ':>8s} {'|Δ|/VMS':>8s} {'Match?':>8s}")
    pr(f"  {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    for k in METRIC_KEYS:
        d = best[k] - VMS[k]
        rel = abs(d) / max(abs(VMS[k]), 0.001)
        match_str = '✓' if rel < 0.10 else '~' if rel < 0.25 else '✗'
        pr(f"  {k:>12s} {VMS[k]:8.4f} {best[k]:8.4f} {d:+8.4f} {rel:8.3f} {match_str:>8s}")
    
    pr(f"\n  Word boundary: ΔH = {best['wbi_delta']:+.4f} (VMS: {vms_delta:+.4f})")
    
    # ── 7. Comparison table ──
    pr()
    pr("7. COMPARISON: ALL MODELS vs VMS")
    pr("═" * 75)
    
    # Get best from each model category
    categories = {}
    for r in all_results:
        cat = r['model'].split('_mapped')[0] if '_mapped' in r['model'] else r['model']
        if cat.startswith('syllabic_syl'):
            cat = 'syllabic'
        if cat not in categories or r['l2'] < categories[cat]['l2']:
            categories[cat] = r
    
    pr(f"  {'Model':>30s} {'L2':>7s} {'heaps':>7s} {'hapax':>7s} {'h_chr':>7s} "
       f"{'h_wrd':>7s} {'wlen':>7s} {'ttr':>7s} {'zipf':>7s} {'ΔH_b':>7s}")
    pr(f"  {'─'*30} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7}")
    pr(f"  {'VMS (target)':>30s} {'0.000':>7s} {VMS['heaps']:7.4f} {VMS['hapax']:7.4f} "
       f"{VMS['h_char']:7.4f} {VMS['h_word']:7.4f} {VMS['wlen']:7.4f} {VMS['ttr']:7.4f} "
       f"{VMS['zipf']:7.4f} {vms_delta:7.4f}")
    
    for cat_name, r in sorted(categories.items(), key=lambda x: x[1]['l2']):
        pr(f"  {cat_name:>30s} {r['l2']:7.4f} {r['heaps']:7.4f} {r['hapax']:7.4f} "
           f"{r['h_char']:7.4f} {r['h_word']:7.4f} {r['wlen']:7.4f} {r['ttr']:7.4f} "
           f"{r['zipf']:7.4f} {r['wbi_delta']:7.4f}")
    
    # Add Phase 72 references
    pr(f"  {'Naibbe best (Phase 72)':>30s} {'0.341':>7s} {'0.7029':>7s} {'0.4952':>7s} "
       f"{'0.6187':>7s} {'0.3646':>7s} {'4.8456':>7s} {'0.3676':>7s} {'0.6720':>7s} {'-0.308':>7s}")
    pr(f"  {'Italian raw (Phase 64)':>30s} {'1.777':>7s} {'0.7515':>7s} {'0.6390':>7s} "
       f"{'0.8393':>7s} {'0.4639':>7s} {'3.9302':>7s} {'0.3374':>7s} {'1.0207':>7s} {'':>7s}")
    
    # ── 8. Skeptical assessment ──
    pr()
    pr("8. SKEPTICAL SELF-ASSESSMENT")
    pr("═" * 75)
    pr()
    
    # Check failure criteria
    best_l2 = min(r['l2'] for r in all_results)
    best_hchar_delta = min(abs(r['h_char'] - VMS['h_char']) for r in all_results)
    all_deltas = [r['wbi_delta'] for r in all_results]
    any_positive_delta = any(d > 0 for d in all_deltas)
    
    pr("  FAILURE CRITERIA CHECK:")
    pr(f"    All L2 > 3.0?                    Best L2 = {best_l2:.4f} → {'FAIL' if best_l2 > 3.0 else 'PASS'}")
    pr(f"    h_char stuck near 0.84?           Closest to VMS = {best_hchar_delta:.4f} → {'FAIL' if best_hchar_delta > 0.15 else 'PASS'}")
    pr(f"    ΔH always strongly negative?      Any positive: {any_positive_delta} → {'PASS (some +)' if any_positive_delta else 'FAIL (all negative)'}")
    
    pr()
    pr("  KEY OBSERVATIONS:")
    pr("  ─────────────────")
    
    # Does abbreviation reduce h_char?
    abbrev_raw_results = [r for r in all_results if r['model'] == 'abbrev_raw']
    if abbrev_raw_results:
        d0 = [r for r in abbrev_raw_results if r['density'] == 0.0]
        d9 = [r for r in abbrev_raw_results if r['density'] == 0.9]
        if d0 and d9:
            hc_0 = np.mean([r['h_char'] for r in d0])
            hc_9 = np.mean([r['h_char'] for r in d9])
            pr(f"  a) h_char at density=0.0: {hc_0:.4f}, at density=0.9: {hc_9:.4f}")
            pr(f"     Change: {hc_9-hc_0:+.4f} ({'drops toward VMS' if hc_9 < hc_0 else 'RISES away from VMS'})")
            pr(f"     VMS target: {VMS['h_char']:.4f}")
    
    # Does abbreviation help Zipf?
    if abbrev_raw_results:
        d0 = [r for r in abbrev_raw_results if r['density'] == 0.0]
        d9 = [r for r in abbrev_raw_results if r['density'] == 0.9]
        if d0 and d9:
            z_0 = np.mean([r['zipf'] for r in d0])
            z_9 = np.mean([r['zipf'] for r in d9])
            pr(f"  b) Zipf α at density=0.0: {z_0:.4f}, at density=0.9: {z_9:.4f}")
            pr(f"     VMS target: {VMS['zipf']:.4f}")
    
    # Word boundary comparison
    pr(f"  c) Word boundary ΔH range: [{min(all_deltas):+.4f}, {max(all_deltas):+.4f}]")
    pr(f"     VMS ΔH: {vms_delta:+.4f}")
    pr(f"     ALL abbreviation models PRESERVE original word boundaries,")
    pr(f"     so ΔH should remain similar to source language (negative).")
    
    pr()
    pr("  POTENTIAL CONFOUNDS:")
    pr("  ─────────────────────")
    pr("  a) Our abbreviation rules are MODELED, not taken from real manuscripts.")
    pr("     Actual scribal abbreviation was more varied and context-dependent.")
    pr("  b) We don't have digitized medieval abbreviated text to compare directly.")
    pr("  c) The alphabet mapping step (random mapping to 18 chars) adds noise.")
    pr("  d) Syllabification is approximate. Real Latin syllable rules are complex.")
    pr("  e) We only test Latin, Italian, Czech. Other languages may differ.")
    pr("  f) The abbreviation model preserves word boundaries — but VMS word")
    pr("     boundaries are non-informative, which abbreviation cannot explain.")
    
    elapsed = time.time() - t0
    pr()
    pr(f"Total runtime: {elapsed:.1f}s")
    
    # ── Save results ──
    out_txt = RESULTS_DIR / 'phase73_abbreviation_model.txt'
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    
    out_json = RESULTS_DIR / 'phase73_abbreviation_raw.json'
    with open(out_json, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    pr(f"\nResults saved to {out_txt} and {out_json}")


if __name__ == '__main__':
    main()
