#!/usr/bin/env python3
"""
POSITIONAL-VARIANT VERBOSE CIPHER: CLOSING THE ALPHABET GAP
========================================================================

forward_process_models found that the verbose positional cipher is the ONLY encoding
that reproduces VMS's extreme bigram predictability (H(c|prev) = 2.47).
But it has too few characters (13 vs VMS 32) and wrong IC/H(char).

HYPOTHESIS: if source characters map to DIFFERENT cipher characters
depending on their POSITION within the word (initial, early, medial,
late, final), the cipher alphabet multiplies while keeping within-
expansion bigram predictability intact.

This matches known VMS features:
  - q is almost exclusively word-initial (96.6%)
  - y,n dominate word-final positions (88.2% of endings)
  - Gallows cluster in early positions (mean 0.19–0.35)
  - Positional entropy: H(initial)=3.02, H(mid)=3.31, H(final)=2.47
  - 5 SVD character clusters with distinct positional profiles

TARGET (VMS):
  alpha_size  = 32      H(char)    = 3.86    H(char|prev) = 2.47
  H_ratio     = 0.64    IC         = 0.082   mean_wlen    = 4.94
  TTR         = 0.27    hapax_ratio= 0.66    V_frac       = 0.28
  VC_alt      = 0.73

ENCODING SCHEMES:
  A) 3-zone verbose: initial / medial / final (×3 alphabet)
  B) 5-zone verbose: initial / early / medial / late / final (×5 alphabet)
  C) 3-zone with shared frequent chars: some chars shared across zones
  D) 5-zone vowel-only variants: consonants stable, vowels vary by zone
  E) Graduated: initial+final get unique chars, medial is shared
  F) Optimized search: grid-search zone counts and sharing to minimize
     distance to VMS

Source text: Italian (Dante, Inferno — Gutenberg #1012).
"""

import re, sys, io, math, random, json, string
from pathlib import Path
from collections import Counter, defaultdict
import urllib.request
import numpy as np
from common import eva_to_glyphs_v2 as eva_to_glyphs, fetch_gutenberg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdout.reconfigure(line_buffering=True)

random.seed(60)
np.random.seed(60)

_print = print
def pr(s=''):
    _print(s)
    sys.stdout.flush()

# ═══════════════════════════════════════════════════════════════════════
# METRICS (from cross_script_fingerprint/59)
# ═══════════════════════════════════════════════════════════════════════

def compute_metrics(words, chars, name='', max_tokens=10000):
    nb_chars = [c for c in chars if c != ' ']
    if len(nb_chars) < 200:
        return None

    alphabet = set(nb_chars)
    alpha_size = len(alphabet)

    counts = Counter(nb_chars)
    total = sum(counts.values())
    H_char = -sum((n/total)*math.log2(n/total) for n in counts.values())

    bigram_counts = defaultdict(Counter)
    for i in range(1, len(nb_chars)):
        bigram_counts[nb_chars[i-1]][nb_chars[i]] += 1
    H_cond = 0.0
    for prev_char, nexts in bigram_counts.items():
        prev_total = sum(nexts.values())
        p_prev = prev_total / (total - 1)
        h_local = -sum((n/prev_total)*math.log2(n/prev_total)
                       for n in nexts.values())
        H_cond += p_prev * h_local

    H_ratio = H_cond / H_char if H_char > 0 else 0
    IC = sum(n*(n-1) for n in counts.values()) / (total*(total-1)) if total > 1 else 0
    mean_wlen = np.mean([len(w) for w in words]) if words else 0

    std_words = words[:max_tokens]
    std_n = len(std_words)
    ttr = len(set(std_words)) / std_n if std_n > 0 else 0

    std_counts = Counter(std_words)
    hapax = sum(1 for c in std_counts.values() if c == 1)
    hapax_ratio = hapax / len(std_counts) if std_counts else 0

    v_count, v_set = sukhotin(nb_chars, alphabet)
    v_frac = v_count / alpha_size if alpha_size > 0 else 0
    alt_rate = vc_alternation(nb_chars, v_set)

    return {
        'name': name,
        'alpha_size': alpha_size,
        'H_char': H_char,
        'H_cond': H_cond,
        'H_ratio': H_ratio,
        'IC': IC,
        'mean_wlen': mean_wlen,
        'TTR': ttr,
        'hapax_ratio': hapax_ratio,
        'V_frac': v_frac,
        'VC_alt': alt_rate,
        'n_chars': len(nb_chars),
        'n_words': len(words),
        'n_types': len(set(words)),
    }


def sukhotin(chars, alphabet):
    alpha_list = sorted(alphabet)
    n = len(alpha_list)
    idx = {c: i for i, c in enumerate(alpha_list)}
    adj = np.zeros((n, n), dtype=float)
    for i in range(1, len(chars)):
        a, b = chars[i-1], chars[i]
        if a in idx and b in idx and a != b:
            adj[idx[a]][idx[b]] += 1
            adj[idx[b]][idx[a]] += 1
    row_sums = adj.sum(axis=1)
    vowels = set()
    remaining = set(range(n))
    for _ in range(n):
        best = -1; best_val = 0
        for r in remaining:
            if row_sums[r] > best_val:
                best_val = row_sums[r]; best = r
        if best < 0 or best_val <= 0: break
        vowels.add(best)
        remaining.discard(best)
        for r in remaining:
            row_sums[r] -= 2 * adj[best][r]
    v_set = {alpha_list[i] for i in vowels}
    return len(v_set), v_set


def vc_alternation(chars, vowels):
    if len(chars) < 2: return 0
    transitions = sum(1 for i in range(1, len(chars))
                      if (chars[i-1] in vowels) != (chars[i] in vowels))
    return transitions / (len(chars) - 1)


# ═══════════════════════════════════════════════════════════════════════
# POSITIONAL METRICS (new in positional_verbose_cipher)
# ═══════════════════════════════════════════════════════════════════════

def positional_entropy(words):
    """
    Compute per-position entropy and character distributions.
    Returns dict with position → {H, top_chars, n_types}.
    """
    pos_counts = defaultdict(Counter)
    for w in words:
        chars = list(w)
        n = len(chars)
        for i, c in enumerate(chars):
            # Normalize position to 5 zones: initial, early, medial, late, final
            if i == 0:
                zone = 'initial'
            elif i == n - 1:
                zone = 'final'
            elif i <= n * 0.33:
                zone = 'early'
            elif i >= n * 0.67:
                zone = 'late'
            else:
                zone = 'medial'
            pos_counts[zone][c] += 1

    result = {}
    for zone in ['initial', 'early', 'medial', 'late', 'final']:
        if zone not in pos_counts:
            continue
        cnts = pos_counts[zone]
        total = sum(cnts.values())
        H = -sum((n/total)*math.log2(n/total) for n in cnts.values())
        top3 = cnts.most_common(3)
        top_str = ', '.join(f"{c}({n/total:.0%})" for c, n in top3)
        result[zone] = {
            'H': H,
            'n_types': len(cnts),
            'top_chars': top_str,
            'total': total,
        }
    return result


def initial_final_concentration(words):
    """
    Fraction of words starting with top-3 initial chars, ending with
    top-3 final chars. VMS: initial (o,c,q)=55%, final (y,n,r)=88%.
    """
    init_counts = Counter()
    final_counts = Counter()
    for w in words:
        if len(w) >= 1:
            init_counts[w[0]] += 1
            final_counts[w[-1]] += 1

    n = len(words)
    if n == 0:
        return 0, 0

    init_top3 = sum(c for _, c in init_counts.most_common(3)) / n
    final_top3 = sum(c for _, c in final_counts.most_common(3)) / n
    return init_top3, final_top3


# ═══════════════════════════════════════════════════════════════════════
# VMS LOADING
# ═══════════════════════════════════════════════════════════════════════

FOLIO_DIR = Path("folios")



def load_vms():
    words_all = []
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'): continue
            m = re.match(r'<([^>]+)>', line)
            rest = line[m.end():].strip() if m else line
            if not rest: continue
            ws = [w.strip() for w in re.split(r'[.\s,;]+', rest)
                  if w.strip() and re.match(r'^[a-z]+$', w.strip())]
            words_all.extend(ws)
    return words_all


def vms_char_sequence(words):
    seq = []
    for w in words:
        seq.extend(eva_to_glyphs(w))
        seq.append(' ')
    return seq


def vms_words_as_glyph_strings(words):
    """Convert VMS words to glyph-level strings for positional analysis."""
    result = []
    for w in words:
        glyphs = eva_to_glyphs(w)
        result.append(''.join(glyphs))
    return result


# ═══════════════════════════════════════════════════════════════════════
# SOURCE TEXT
# ═══════════════════════════════════════════════════════════════════════



ITALIAN_VOWELS = set('aeiouàáâãäåèéêëìíîïòóôõöùúûüý')

def load_italian():
    raw = fetch_gutenberg(1012)
    text = raw.lower()
    text = re.sub(r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþß]+', ' ', text)
    words = [w for w in text.split() if len(w) >= 1]
    return words[:50000]


# ═══════════════════════════════════════════════════════════════════════
# POSITIONAL-VARIANT VERBOSE CIPHER ENCODINGS
# ═══════════════════════════════════════════════════════════════════════

SRC_VOWELS = set('aeiouàèéìòù')
SRC_CONSONANTS = set('bcdfghlmnpqrstvz')

def _get_word_zones_3(word):
    """Return list of zone labels for each character: 3-zone system."""
    n = len(word)
    if n <= 2:
        return ['initial'] + ['final'] * (n - 1) if n > 1 else ['initial']
    zones = []
    for i in range(n):
        if i == 0:
            zones.append('initial')
        elif i == n - 1:
            zones.append('final')
        else:
            zones.append('medial')
    return zones


def _get_word_zones_5(word):
    """Return list of zone labels for each character: 5-zone system."""
    n = len(word)
    if n <= 2:
        return ['initial'] + ['final'] * (n - 1) if n > 1 else ['initial']
    if n <= 4:
        zones = ['initial']
        for _ in range(n - 2):
            zones.append('medial')
        zones.append('final')
        return zones
    zones = []
    for i in range(n):
        if i == 0:
            zones.append('initial')
        elif i == n - 1:
            zones.append('final')
        elif i <= n * 0.25:
            zones.append('early')
        elif i >= n * 0.75:
            zones.append('late')
        else:
            zones.append('medial')
    return zones


def _build_cipher_alphabet(n_chars):
    """Build a cipher alphabet of size n_chars using ASCII then extended."""
    alpha = []
    # Use lowercase first, then uppercase, then numbered symbols
    for c in string.ascii_lowercase:
        alpha.append(c)
        if len(alpha) >= n_chars:
            return alpha
    for c in string.ascii_uppercase:
        alpha.append(c)
        if len(alpha) >= n_chars:
            return alpha
    for i in range(200):
        alpha.append(f'#{i}')
        if len(alpha) >= n_chars:
            return alpha
    return alpha


def encode_verbose_positional_zones(words, n_zones=3, share_fraction=0.0):
    """
    Verbose positional cipher with zone-dependent character variants.

    Each source character maps to a cipher sequence that depends on
    its position-zone within the word:
      - Vowels → 2 cipher chars (C_zone + V_zone)
      - Consonants → 1 cipher char (C_zone)

    The cipher characters are DIFFERENT per zone, so the same source
    letter produces different cipher output at word-initial vs word-
    final positions. This multiplies the effective alphabet.

    share_fraction: fraction of cipher chars shared across all zones
    (0.0 = fully distinct per zone, 1.0 = same as forward_process_models baseline).
    """
    zone_func = _get_word_zones_5 if n_zones >= 5 else _get_word_zones_3
    zone_names = (['initial', 'medial', 'final'] if n_zones == 3
                  else ['initial', 'early', 'medial', 'late', 'final'])

    # Build per-zone cipher alphabets
    # Base consonant chars and vowel chars
    n_base_c = 8
    n_base_v = 5
    n_shared_c = int(n_base_c * share_fraction)
    n_shared_v = int(n_base_v * share_fraction)
    n_unique_c = n_base_c - n_shared_c
    n_unique_v = n_base_v - n_shared_v

    # Total alphabet size will be:
    #   shared_c + n_zones * unique_c + shared_v + n_zones * unique_v
    total_alpha = (n_shared_c + len(zone_names) * n_unique_c +
                   n_shared_v + len(zone_names) * n_unique_v)
    all_chars = _build_cipher_alphabet(total_alpha + 10)

    idx = 0
    shared_c_chars = all_chars[idx:idx+n_shared_c]; idx += n_shared_c
    shared_v_chars = all_chars[idx:idx+n_shared_v]; idx += n_shared_v

    zone_c_chars = {}
    zone_v_chars = {}
    for z in zone_names:
        unique_c = all_chars[idx:idx+n_unique_c]; idx += n_unique_c
        unique_v = all_chars[idx:idx+n_unique_v]; idx += n_unique_v
        zone_c_chars[z] = shared_c_chars + unique_c
        zone_v_chars[z] = shared_v_chars + unique_v

    # Map source consonants → per-zone cipher chars
    src_cons = sorted(SRC_CONSONANTS)
    src_vow = sorted(SRC_VOWELS)

    # Per-zone consonant mappings
    zone_cons_map = {}
    for z in zone_names:
        zc = zone_c_chars[z]
        zone_cons_map[z] = {c: zc[i % len(zc)] for i, c in enumerate(src_cons)}

    # Per-zone vowel expansion mappings (vowel → C_char + V_char)
    zone_vowel_map = {}
    for z in zone_names:
        zc = zone_c_chars[z]
        zv = zone_v_chars[z]
        vm = {}
        for i, v in enumerate(src_vow):
            vm[v] = zc[i % len(zc)] + zv[i % len(zv)]
        zone_vowel_map[z] = vm

    # Encode words
    enc_words = []
    enc_chars = []
    for w in words:
        zones = zone_func(w)
        w_chars = []
        for j, c in enumerate(w):
            if j >= len(zones):
                z = zones[-1]
            else:
                z = zones[j]
            if c in SRC_VOWELS:
                w_chars.extend(list(zone_vowel_map[z][c]))
            elif c in SRC_CONSONANTS:
                w_chars.append(zone_cons_map[z][c])
        if w_chars:
            enc_words.append(''.join(w_chars))
            enc_chars.extend(w_chars)
            enc_chars.append(' ')

    return enc_words, enc_chars


def encode_verbose_vowel_variant_only(words, n_zones=3):
    """
    Only VOWEL expansions vary by position; consonants stay the same
    across all positions. This tests whether vowel specialization alone
    can produce the right alphabet size.
    """
    zone_func = _get_word_zones_5 if n_zones >= 5 else _get_word_zones_3
    zone_names = (['initial', 'medial', 'final'] if n_zones == 3
                  else ['initial', 'early', 'medial', 'late', 'final'])

    # Consonant chars: same across all zones (8 chars)
    C_CHARS = list('bcdfghkl')
    # Vowel chars: distinct per zone
    all_v_chars = _build_cipher_alphabet(5 * len(zone_names) + 26)
    # Skip the consonant chars to avoid overlap
    v_pool = [c for c in all_v_chars if c not in C_CHARS]

    zone_v_chars = {}
    idx = 0
    for z in zone_names:
        zone_v_chars[z] = v_pool[idx:idx+5]
        idx += 5

    src_cons = sorted(SRC_CONSONANTS)
    src_vow = sorted(SRC_VOWELS)
    cons_map = {c: C_CHARS[i % len(C_CHARS)] for i, c in enumerate(src_cons)}

    # Per-zone vowel maps: vowel → C_char + V_zone_char
    zone_vowel_map = {}
    for z in zone_names:
        zv = zone_v_chars[z]
        vm = {}
        for i, v in enumerate(src_vow):
            vm[v] = C_CHARS[i % len(C_CHARS)] + zv[i % len(zv)]
        zone_vowel_map[z] = vm

    enc_words = []
    enc_chars = []
    for w in words:
        zones = zone_func(w)
        w_chars = []
        for j, c in enumerate(w):
            z = zones[j] if j < len(zones) else zones[-1]
            if c in SRC_VOWELS:
                w_chars.extend(list(zone_vowel_map[z][c]))
            elif c in SRC_CONSONANTS:
                w_chars.append(cons_map[c])
        if w_chars:
            enc_words.append(''.join(w_chars))
            enc_chars.extend(w_chars)
            enc_chars.append(' ')

    return enc_words, enc_chars


def encode_verbose_graduated(words):
    """
    Graduated variant: initial and final positions get UNIQUE cipher
    characters; medial positions share a common set. This mirrors VMS's
    q-initial and y-final pattern.
    """
    # Initial-only chars (4), final-only chars (4), shared chars (8+5)
    INIT_C = list('ABCD')       # 4 initial-exclusive consonant chars
    FINAL_C = list('WXYZ')      # 4 final-exclusive consonant chars
    MED_C = list('bcdfghkl')    # 8 medial/shared consonant chars
    INIT_V = list('12345')      # 5 initial-exclusive vowel markers
    FINAL_V = list('67890')     # 5 final-exclusive vowel markers
    MED_V = list('aeiou')       # 5 medial/shared vowel markers

    src_cons = sorted(SRC_CONSONANTS)
    src_vow = sorted(SRC_VOWELS)

    cons_maps = {
        'initial': {c: INIT_C[i % len(INIT_C)] for i, c in enumerate(src_cons)},
        'medial': {c: MED_C[i % len(MED_C)] for i, c in enumerate(src_cons)},
        'final': {c: FINAL_C[i % len(FINAL_C)] for i, c in enumerate(src_cons)},
    }
    vowel_maps = {
        'initial': {v: INIT_C[i % len(INIT_C)] + INIT_V[i % len(INIT_V)]
                    for i, v in enumerate(src_vow)},
        'medial': {v: MED_C[i % len(MED_C)] + MED_V[i % len(MED_V)]
                   for i, v in enumerate(src_vow)},
        'final': {v: FINAL_C[i % len(FINAL_C)] + FINAL_V[i % len(FINAL_V)]
                  for i, v in enumerate(src_vow)},
    }

    enc_words = []
    enc_chars = []
    for w in words:
        zones = _get_word_zones_3(w)
        w_chars = []
        for j, c in enumerate(w):
            z = zones[j] if j < len(zones) else zones[-1]
            if c in SRC_VOWELS:
                w_chars.extend(list(vowel_maps[z][c]))
            elif c in SRC_CONSONANTS:
                w_chars.append(cons_maps[z][c])
        if w_chars:
            enc_words.append(''.join(w_chars))
            enc_chars.extend(w_chars)
            enc_chars.append(' ')

    return enc_words, enc_chars


def encode_verbose_optimized(words, n_c_shared, n_c_unique, n_v_shared,
                              n_v_unique, n_zones=3, expand_prob=1.0):
    """
    Parameterized verbose cipher for grid search:
      n_c_shared:  number of shared consonant chars across zones
      n_c_unique:  number of unique consonant chars per zone
      n_v_shared:  number of shared vowel-marker chars across zones
      n_v_unique:  number of unique vowel-marker chars per zone
      n_zones:     number of zones
      expand_prob: probability that a vowel expands to 2 chars (rest → 1 char)

    Total alphabet = n_c_shared + n_zones * n_c_unique
                   + n_v_shared + n_zones * n_v_unique
    """
    zone_func = _get_word_zones_5 if n_zones >= 5 else _get_word_zones_3
    zone_names = (['initial', 'medial', 'final'] if n_zones == 3
                  else ['initial', 'early', 'medial', 'late', 'final'])

    total_alpha = (n_c_shared + len(zone_names) * n_c_unique +
                   n_v_shared + len(zone_names) * n_v_unique)
    all_chars = _build_cipher_alphabet(total_alpha + 10)

    idx = 0
    sc = all_chars[idx:idx+n_c_shared]; idx += n_c_shared
    sv = all_chars[idx:idx+n_v_shared]; idx += n_v_shared

    zone_c = {}; zone_v = {}
    for z in zone_names:
        uc = all_chars[idx:idx+n_c_unique]; idx += n_c_unique
        uv = all_chars[idx:idx+n_v_unique]; idx += n_v_unique
        zone_c[z] = sc + uc
        zone_v[z] = sv + uv

    src_cons = sorted(SRC_CONSONANTS)
    src_vow = sorted(SRC_VOWELS)

    z_cons_map = {}
    for z in zone_names:
        zc = zone_c[z]
        z_cons_map[z] = {c: zc[i % len(zc)] for i, c in enumerate(src_cons)}

    z_vowel_map = {}
    for z in zone_names:
        zc = zone_c[z]; zv = zone_v[z]
        vm = {}
        for i, v in enumerate(src_vow):
            vm[v] = zc[i % len(zc)] + zv[i % len(zv)]
        z_vowel_map[z] = vm

    # Use deterministic expansion decision based on source char identity
    # (not random per occurrence — that would break the deterministic property)
    always_expand = set()
    for v in src_vow:
        if hash(v) % 100 < expand_prob * 100:
            always_expand.add(v)

    enc_words = []
    enc_chars = []
    for w in words:
        zones = zone_func(w)
        w_chars = []
        for j, c in enumerate(w):
            z = zones[j] if j < len(zones) else zones[-1]
            if c in always_expand:
                w_chars.extend(list(z_vowel_map[z][c]))
            elif c in SRC_VOWELS:
                # Non-expanding vowel → single vowel-marker char
                zv = zone_v[z]
                w_chars.append(zv[src_vow.index(c) % len(zv)])
            elif c in SRC_CONSONANTS:
                w_chars.append(z_cons_map[z][c])
        if w_chars:
            enc_words.append(''.join(w_chars))
            enc_chars.extend(w_chars)
            enc_chars.append(' ')

    return enc_words, enc_chars


# ═══════════════════════════════════════════════════════════════════════
# DISTANCE CALCULATION
# ═══════════════════════════════════════════════════════════════════════

FEATURE_KEYS = ['alpha_size', 'H_char', 'H_cond', 'H_ratio', 'IC',
                'mean_wlen', 'TTR', 'hapax_ratio', 'V_frac', 'VC_alt']

def feature_vec(m):
    return np.array([m[k] for k in FEATURE_KEYS])

def z_score_distance(vms_vec, test_vec, nl_mu, nl_sigma):
    z_vms = (vms_vec - nl_mu) / nl_sigma
    z_test = (test_vec - nl_mu) / nl_sigma
    return np.sqrt(np.sum((z_vms - z_test)**2))

def per_feature_z_delta(vms_vec, test_vec, nl_mu, nl_sigma):
    z_vms = (vms_vec - nl_mu) / nl_sigma
    z_test = (test_vec - nl_mu) / nl_sigma
    return z_test - z_vms  # positive = test is higher than VMS


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 72)
    pr("positional_verbose_cipher: POSITIONAL-VARIANT VERBOSE CIPHER")
    pr("Can position-dependent character mapping close the alphabet gap?")
    pr("=" * 72)
    pr()

    # ── Load VMS ──
    pr("Loading VMS corpus...")
    vms_words = load_vms()
    vms_chars = vms_char_sequence(vms_words)
    vms_m = compute_metrics(vms_words, vms_chars, name='VMS (target)')
    vms_glyph_words = vms_words_as_glyph_strings(vms_words)
    pr(f"  VMS: {vms_m['n_words']} words, {vms_m['n_chars']} chars, "
       f"α={vms_m['alpha_size']}")
    pr(f"  H(c)={vms_m['H_char']:.3f}, H(c|p)={vms_m['H_cond']:.3f}, "
       f"H-ratio={vms_m['H_ratio']:.3f}, IC={vms_m['IC']:.4f}")
    pr()

    # ── VMS positional profile ──
    pr("── VMS Positional Profile ──")
    vms_pos = positional_entropy(vms_glyph_words)
    for zone in ['initial', 'early', 'medial', 'late', 'final']:
        if zone in vms_pos:
            p = vms_pos[zone]
            pr(f"  {zone:8s}: H={p['H']:.3f}, types={p['n_types']:3d}, "
               f"top={p['top_chars']}")
    vms_init3, vms_fin3 = initial_final_concentration(vms_glyph_words)
    pr(f"  Initial top-3 concentration: {vms_init3:.1%}")
    pr(f"  Final top-3 concentration:   {vms_fin3:.1%}")
    pr()

    # ── Load NL reference from cross_script_fingerprint ──
    pr("Loading cross_script_fingerprint reference data...")
    try:
        with open('results/cross_script_fingerprint_output.json') as f:
            p58 = json.load(f)
        nl_names = ['English', 'Latin', 'Italian', 'German',
                    'Spanish', 'French', 'Finnish']
        nl_vecs = []
        for lang in nl_names:
            if lang in p58:
                nl_vecs.append(np.array([p58[lang][k]
                                         for k in FEATURE_KEYS]))
        nl_matrix = np.array(nl_vecs)
        nl_mu = nl_matrix.mean(axis=0)
        nl_sigma = nl_matrix.std(axis=0)
        nl_sigma[nl_sigma == 0] = 1
        pr(f"  {len(nl_vecs)} NL references loaded")
    except Exception as e:
        pr(f"  WARNING: {e}")
        nl_mu = np.zeros(len(FEATURE_KEYS))
        nl_sigma = np.ones(len(FEATURE_KEYS))
    pr()

    # ── Load Italian ──
    pr("Fetching Italian source text...")
    ita_words = load_italian()
    pr(f"  Italian: {len(ita_words)} words")
    pr()

    vms_vec = feature_vec(vms_m)

    # ═══════════════════════════════════════════════════════════════════
    # 60a) FIXED ENCODING SCHEMES
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("60a) POSITIONAL-VARIANT ENCODING SCHEMES")
    pr("=" * 72)
    pr()

    schemes = [
        ("A: 3-zone verbose (full variant)",
         lambda: encode_verbose_positional_zones(ita_words, n_zones=3,
                                                  share_fraction=0.0)),
        ("B: 5-zone verbose (full variant)",
         lambda: encode_verbose_positional_zones(ita_words, n_zones=5,
                                                  share_fraction=0.0)),
        ("C: 3-zone, 30% shared chars",
         lambda: encode_verbose_positional_zones(ita_words, n_zones=3,
                                                  share_fraction=0.3)),
        ("D: 5-zone, vowel-only variants",
         lambda: encode_verbose_vowel_variant_only(ita_words, n_zones=5)),
        ("E: Graduated (init/final unique)",
         lambda: encode_verbose_graduated(ita_words)),
        ("F: 3-zone, 50% shared chars",
         lambda: encode_verbose_positional_zones(ita_words, n_zones=3,
                                                  share_fraction=0.5)),
    ]

    results = {'VMS': vms_m}
    all_ranks = []

    for name, encoder in schemes:
        pr(f"  Encoding: {name}")
        try:
            enc_w, enc_c = encoder()
            m = compute_metrics(enc_w, enc_c, name=name)
            if m is None:
                pr(f"    FAILED: too few characters")
                continue
            results[name] = m
            dist_z = z_score_distance(vms_vec, feature_vec(m),
                                      nl_mu, nl_sigma)
            all_ranks.append((dist_z, name, m))
            pr(f"    α={m['alpha_size']:>3d}  H(c)={m['H_char']:.3f}  "
               f"H(c|p)={m['H_cond']:.3f}  H-rat={m['H_ratio']:.3f}  "
               f"IC={m['IC']:.4f}  MWL={m['mean_wlen']:.2f}")
            pr(f"    TTR={m['TTR']:.4f}  Hapax={m['hapax_ratio']:.3f}  "
               f"V-fr={m['V_frac']:.3f}  V/C-alt={m['VC_alt']:.3f}")
            pr(f"    Distance from VMS: z-normalized={dist_z:.3f}")

            # Positional profile
            enc_pos = positional_entropy(enc_w)
            for zone in ['initial', 'medial', 'final']:
                if zone in enc_pos:
                    p = enc_pos[zone]
                    pr(f"    pos/{zone:8s}: H={p['H']:.3f}, "
                       f"types={p['n_types']:3d}")
            i3, f3 = initial_final_concentration(enc_w)
            pr(f"    init-top3={i3:.1%}, final-top3={f3:.1%}")
        except Exception as e:
            pr(f"    ERROR: {e}")
            import traceback; traceback.print_exc()
        pr()

    # ═══════════════════════════════════════════════════════════════════
    # 60b) PARAMETER GRID SEARCH
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("60b) GRID SEARCH: OPTIMIZING FOR VMS FINGERPRINT")
    pr("=" * 72)
    pr()

    best_dist = float('inf')
    best_params = None
    best_metrics = None

    # Grid: vary n_zones, shared/unique char counts, and expand_prob
    grid_results = []
    param_combos = []
    for n_zones in [3, 5]:
        for n_c_shared in [0, 2, 4]:
            for n_c_unique in [3, 5, 8]:
                for n_v_shared in [0, 2]:
                    for n_v_unique in [2, 3, 5]:
                        for expand_prob in [0.6, 0.8, 1.0]:
                            param_combos.append({
                                'n_zones': n_zones,
                                'n_c_shared': n_c_shared,
                                'n_c_unique': n_c_unique,
                                'n_v_shared': n_v_shared,
                                'n_v_unique': n_v_unique,
                                'expand_prob': expand_prob,
                            })

    pr(f"  Testing {len(param_combos)} parameter combinations...")
    pr()

    for params in param_combos:
        try:
            enc_w, enc_c = encode_verbose_optimized(
                ita_words, **params)
            m = compute_metrics(enc_w, enc_c, name='grid')
            if m is None:
                continue
            dist_z = z_score_distance(vms_vec, feature_vec(m),
                                      nl_mu, nl_sigma)
            grid_results.append((dist_z, params, m))
            if dist_z < best_dist:
                best_dist = dist_z
                best_params = params
                best_metrics = m
        except:
            pass

    grid_results.sort()

    # Show top 10
    pr("  Top 10 parameter sets (z-distance from VMS):")
    pr()
    hdr = (f"  {'Rank':<5s} {'Dist':>7s} {'α':>4s} {'H(c|p)':>7s} "
           f"{'IC':>7s} {'MWL':>6s} {'Zones':>5s} "
           f"{'Csh':>3s} {'Cuq':>3s} {'Vsh':>3s} {'Vuq':>3s} {'Exp':>4s}")
    pr(hdr)
    pr("  " + "-" * (len(hdr) - 2))
    for i, (dist, params, m) in enumerate(grid_results[:10]):
        pr(f"  {i+1:<5d} {dist:>7.3f} {m['alpha_size']:>4d} "
           f"{m['H_cond']:>7.3f} {m['IC']:>7.4f} "
           f"{m['mean_wlen']:>6.2f} "
           f"{params['n_zones']:>5d} "
           f"{params['n_c_shared']:>3d} "
           f"{params['n_c_unique']:>3d} "
           f"{params['n_v_shared']:>3d} "
           f"{params['n_v_unique']:>3d} "
           f"{params['expand_prob']:>4.1f}")
    pr()
    pr(f"  VMS target: α=32, H(c|p)=2.471, IC=0.0817, MWL=4.94")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 60c) BEST MODEL — DETAILED ANALYSIS
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("60c) BEST MODEL — DETAILED FINGERPRINT COMPARISON")
    pr("=" * 72)
    pr()

    if best_metrics:
        best_name = (f"Optimized ({best_params['n_zones']}zone, "
                     f"Csh={best_params['n_c_shared']}, "
                     f"Cuq={best_params['n_c_unique']}, "
                     f"Vsh={best_params['n_v_shared']}, "
                     f"Vuq={best_params['n_v_unique']}, "
                     f"exp={best_params['expand_prob']})")
        best_metrics['name'] = best_name
        results['Grid_best'] = best_metrics

        pr(f"  Best: {best_name}")
        pr(f"  Distance from VMS: {best_dist:.3f}")
        pr()

        total_alpha = (best_params['n_c_shared'] +
                       best_params['n_zones'] * best_params['n_c_unique'] +
                       best_params['n_v_shared'] +
                       best_params['n_zones'] * best_params['n_v_unique'])
        pr(f"  Theoretical max alphabet: {total_alpha}")
        pr(f"  Observed alphabet:        {best_metrics['alpha_size']}")
        pr()

        # Feature-by-feature
        best_vec = feature_vec(best_metrics)
        z_deltas = per_feature_z_delta(vms_vec, best_vec, nl_mu, nl_sigma)

        pr(f"  {'Feature':<14s} {'VMS':>8s} {'Best':>8s} {'Δ':>8s} "
           f"{'NL μ':>8s} {'VMS z':>8s} {'Best z':>8s} {'Δz':>8s}")
        pr("  " + "-" * 72)
        for j, fk in enumerate(FEATURE_KEYS):
            v = vms_m[fk]
            b = best_metrics[fk]
            z_v = (v - nl_mu[j]) / nl_sigma[j]
            z_b = (b - nl_mu[j]) / nl_sigma[j]
            flag = " ✓" if abs(z_deltas[j]) < 2.0 else " ✗"
            pr(f"  {fk:<14s} {v:>8.3f} {b:>8.3f} {b-v:>+8.3f} "
               f"{nl_mu[j]:>8.3f} {z_v:>+8.2f} {z_b:>+8.2f} "
               f"{z_deltas[j]:>+8.2f}{flag}")
        pr()

        matched = sum(1 for d in z_deltas if abs(d) < 2.0)
        pr(f"  Features matched (|Δz| < 2): {matched}/10")
        pr()

        # Positional profile of best model
        pr("  Positional profile:")
        enc_w_best, _ = encode_verbose_optimized(ita_words, **best_params)
        enc_pos_best = positional_entropy(enc_w_best)
        for zone in ['initial', 'early', 'medial', 'late', 'final']:
            if zone in enc_pos_best:
                p = enc_pos_best[zone]
                vp = vms_pos.get(zone, {})
                v_h = vp.get('H', float('nan'))
                pr(f"    {zone:8s}: H={p['H']:.3f} (VMS: {v_h:.3f}), "
                   f"types={p['n_types']:3d} (VMS: {vp.get('n_types','?')})")

        i3, f3 = initial_final_concentration(enc_w_best)
        pr(f"    init-top3:  {i3:.1%}  (VMS: {vms_init3:.1%})")
        pr(f"    final-top3: {f3:.1%}  (VMS: {vms_fin3:.1%})")
        pr()

    # ──  How do the forward_process_models baselines compare? ──
    pr("  forward_process_models baselines for reference:")
    pr(f"    Verbose (no zones):  α=13, H(c|p)=2.453, d=8.31")
    pr(f"    Spanish (nearest NL): d=2.30")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 60d) RANKING ALL SCHEMES
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("60d) COMPLETE RANKING")
    pr("=" * 72)
    pr()

    if best_metrics:
        all_ranks.append((best_dist, 'Grid best', best_metrics))
    all_ranks.sort()

    hdr = (f"{'Rank':<5s} {'Scheme':<40s} {'Dist':>7s} "
           f"{'α':>4s} {'H(c|p)':>7s} {'IC':>7s} {'MWL':>6s}")
    pr(hdr)
    pr("-" * len(hdr))
    for i, (dist, name, m) in enumerate(all_ranks):
        pr(f"{i+1:<5d} {m['name'][:40]:<40s} {dist:>7.3f} "
           f"{m['alpha_size']:>4d} {m['H_cond']:>7.3f} "
           f"{m['IC']:>7.4f} {m['mean_wlen']:>6.2f}")
    pr()
    pr(f"{'':5s} {'VMS (TARGET)':40s} {'0.000':>7s} "
       f"{vms_m['alpha_size']:>4d} {vms_m['H_cond']:>7.3f} "
       f"{vms_m['IC']:>7.4f} {vms_m['mean_wlen']:>6.2f}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 60e) DOES POSITION-VARIANT BEAT NATURAL LANGUAGE?
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("60e) DOES POSITION-VARIANT CIPHER BEAT NEAREST NL?")
    pr("=" * 72)
    pr()

    spanish_dist = 2.30  # cross_script_fingerprint result
    beaten = [(d, n, m) for d, n, m in all_ranks if d < spanish_dist]
    if beaten:
        pr(f"  YES — {len(beaten)} scheme(s) are closer to VMS than "
           f"Spanish (d={spanish_dist:.2f}):")
        for d, n, m in beaten:
            pr(f"    {m['name'][:50]:50s} d={d:.3f}")
        pr()
        pr("  This means the position-variant verbose cipher is a BETTER")
        pr("  statistical match for VMS than any known natural language.")
    else:
        pr(f"  NO — no scheme beats Spanish (d={spanish_dist:.2f})")
        pr()
        # What's the closest?
        if all_ranks:
            d, n, m = all_ranks[0]
            pr(f"  Closest: {m['name'][:50]}  d={d:.3f}")
            improvement = 8.31 - d  # forward_process_models verbose baseline
            pr(f"  Improvement over forward_process_models baseline (d=8.31): "
               f"{improvement:.2f} ({improvement/8.31:.0%})")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 60f) CRITICAL SYNTHESIS
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("60f) CRITICAL SYNTHESIS")
    pr("=" * 72)
    pr()

    if best_metrics:
        best_vec = feature_vec(best_metrics)
        z_deltas = per_feature_z_delta(vms_vec, best_vec, nl_mu, nl_sigma)

        # What improved from forward_process_models?
        pr("What position-variant encoding FIXES vs forward_process_models baseline:")
        pr(f"  ● Alphabet size: 13 → {best_metrics['alpha_size']} "
           f"(VMS: 32)")
        pr(f"  ● H(char): forward_process_models was too low → now "
           f"{best_metrics['H_char']:.3f} (VMS: {vms_m['H_char']:.3f})")
        pr()

        pr("What it PRESERVES:")
        pr(f"  ● H(c|prev): {best_metrics['H_cond']:.3f} "
           f"(VMS: {vms_m['H_cond']:.3f})")
        pr()

        # What still doesn't match?
        mismatches = [(fk, z_deltas[j]) for j, fk in enumerate(FEATURE_KEYS)
                      if abs(z_deltas[j]) >= 2.0]
        if mismatches:
            pr("What STILL doesn't match (|Δz| ≥ 2):")
            for fk, dz in sorted(mismatches, key=lambda x: -abs(x[1])):
                direction = "too high" if dz > 0 else "too low"
                pr(f"  ✗ {fk}: Δz = {dz:+.2f} ({direction})")
        else:
            pr("ALL 10 features match within 2σ!")
        pr()

        # Overall assessment
        pr("INTERPRETATION:")
        pr()
        if best_dist < spanish_dist:
            pr(f"  The position-variant verbose cipher (d={best_dist:.3f})")
            pr(f"  is now CLOSER to VMS than any tested natural language.")
            pr(f"  A process where:")
            pr(f"    1. vowels expand to 2-char sequences (creating low H(c|prev))")
            pr(f"    2. expansion chars vary by word position (creating large α)")
            pr(f"  simultaneously reproduces the VMS fingerprint better than")
            pr(f"  any other tested hypothesis.")
        elif best_dist < 4.0:
            pr(f"  Significant improvement (d={best_dist:.3f} vs forward_process_models's 8.31)")
            pr(f"  but still farther from VMS than Spanish (d=2.30).")
            pr(f"  The position-variant mechanism HELPS but doesn't fully close")
            pr(f"  the gap. The remaining mismatch may indicate:")
            pr(f"    - Additional encoding complexity beyond position-zones")
            pr(f"    - Source language effects (Italian ≠ actual source)")
            pr(f"    - EVA transcription artifacts in the VMS fingerprint")
        else:
            pr(f"  Moderate improvement (d={best_dist:.3f} vs forward_process_models's 8.31)")
            pr(f"  but the cipher model remains far from VMS. Positional")
            pr(f"  variants alone don't explain the full VMS fingerprint.")
        pr()

    # ── Save results ──
    out_path = Path("results/positional_verbose_cipher_output.json")
    out_path.parent.mkdir(exist_ok=True)
    json_data = {}
    for key, m in results.items():
        if m is None: continue
        json_data[key] = {k: float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v
                          for k, v in m.items()}
    # Add grid search info
    if best_params:
        json_data['_grid_best_params'] = best_params
        json_data['_grid_best_distance'] = float(best_dist)
        json_data['_grid_top10'] = [
            {'distance': float(d), 'params': p,
             'alpha_size': m['alpha_size'],
             'H_cond': float(m['H_cond']),
             'IC': float(m['IC'])}
            for d, p, m in grid_results[:10]
        ]
    with open(out_path, 'w') as f:
        json.dump(json_data, f, indent=2, default=str)
    pr(f"Results saved to {out_path}")


if __name__ == '__main__':
    main()
