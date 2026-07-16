#!/usr/bin/env python3
"""
WORD-SHAPE VALIDATION: IS THE 10-FEATURE MATCH REAL OR SUPERFICIAL?
================================================================================

Phases 58-60 matched VMS on 9/10 global summary statistics using a
position-variant verbose cipher. But summary statistics can match by
coincidence while the actual micro-structure is completely different.

THIS PHASE TESTS WHETHER THE CIPHER PRODUCES VMS-LIKE WORD SHAPES.

If the cipher matches VMS at the word-shape level, the model gains
significant credibility. If not, the 10-feature match is superficial.

VALIDATION TESTS:
  1. Word-length distribution (full shape, not just mean)
  2. Character bigram rank correlation (top bigrams shared?)
  3. Position-specific character frequency correlation
  4. Word-shape repetition rate (how stereotyped are the words?)
  5. Initial/final character concentration (q-initial, y-final pattern)
  6. Cross-word-boundary bigram analysis
  7. Rank-frequency (Zipf) curve comparison

Comparisons: VMS vs best cipher vs Italian source vs simple substitution
(the substitution acts as a control — it preserves Italian word shapes
perfectly, so any deviation in the cipher is meaningful).

Uses positional_verbose_cipher's best grid-search parameters.
"""

import re, sys, io, math, random, json, string
from pathlib import Path
from collections import Counter, defaultdict
import urllib.request
import numpy as np
from common import eva_to_glyphs_v2 as eva_to_glyphs, fetch_gutenberg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdout.reconfigure(line_buffering=True)

random.seed(61)
np.random.seed(61)

_print = print
def pr(s='', end='\n'):
    _print(s, end=end)
    sys.stdout.flush()


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

def vms_glyph_words(words):
    """Convert raw EVA words into glyph-segmented word lists."""
    return [eva_to_glyphs(w) for w in words]


# ═══════════════════════════════════════════════════════════════════════
# SOURCE TEXT + CIPHER
# ═══════════════════════════════════════════════════════════════════════


ITALIAN_VOWELS = set('aeiouàáâãäåèéêëìíîïòóôõöùúûüý')
SRC_VOWELS = set('aeiouàèéìòù')
SRC_CONSONANTS = set('bcdfghlmnpqrstvz')

def load_italian():
    raw = fetch_gutenberg(1012)
    text = raw.lower()
    text = re.sub(r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþß]+', ' ', text)
    words = [w for w in text.split() if len(w) >= 1]
    return words[:50000]


def _get_word_zones_3(word):
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


def _build_cipher_alphabet(n_chars):
    alpha = []
    for c in string.ascii_lowercase:
        alpha.append(c)
        if len(alpha) >= n_chars: return alpha
    for c in string.ascii_uppercase:
        alpha.append(c)
        if len(alpha) >= n_chars: return alpha
    for i in range(200):
        alpha.append(f'#{i}')
        if len(alpha) >= n_chars: return alpha
    return alpha


def encode_verbose_optimized(words, n_c_shared, n_c_unique, n_v_shared,
                              n_v_unique, n_zones=3, expand_prob=1.0):
    """positional_verbose_cipher's best encoding function."""
    zone_func = _get_word_zones_3  # best was 3-zone
    zone_names = ['initial', 'medial', 'final']

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

    always_expand = set()
    for v in src_vow:
        if hash(v) % 100 < expand_prob * 100:
            always_expand.add(v)

    enc_words = []
    enc_word_chars = []  # list of lists (per-word char lists)
    for w in words:
        zones = zone_func(w)
        w_chars = []
        for j, c in enumerate(w):
            z = zones[j] if j < len(zones) else zones[-1]
            if c in always_expand:
                w_chars.extend(list(z_vowel_map[z][c]))
            elif c in SRC_VOWELS:
                zv = zone_v[z]
                w_chars.append(zv[src_vow.index(c) % len(zv)])
            elif c in SRC_CONSONANTS:
                w_chars.append(z_cons_map[z][c])
        if w_chars:
            enc_words.append(''.join(w_chars))
            enc_word_chars.append(w_chars)

    return enc_words, enc_word_chars


def encode_simple_subst(words):
    """Simple substitution as control."""
    all_chars = sorted(set(c for w in words for c in w))
    shuffled = all_chars[:]
    random.shuffle(shuffled)
    mapping = dict(zip(all_chars, shuffled))
    enc_words = [''.join(mapping.get(c, c) for c in w) for w in words]
    enc_word_chars = [list(w) for w in enc_words]
    return enc_words, enc_word_chars


# ═══════════════════════════════════════════════════════════════════════
# WORD-SHAPE ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def word_length_distribution(words, max_len=15):
    """Return normalized length distribution."""
    lengths = [len(w) for w in words]
    counts = Counter(lengths)
    total = len(lengths)
    dist = {}
    for l in range(1, max_len + 1):
        dist[l] = counts.get(l, 0) / total
    return dist


def length_dist_l1(d1, d2, max_len=15):
    """L1 distance between two length distributions."""
    return sum(abs(d1.get(l, 0) - d2.get(l, 0)) for l in range(1, max_len + 1))


def length_dist_kl(d1, d2, max_len=15, eps=1e-10):
    """KL divergence D(d1 || d2)."""
    kl = 0
    for l in range(1, max_len + 1):
        p = d1.get(l, 0)
        q = d2.get(l, 0)
        if p > eps:
            kl += p * math.log2(p / max(q, eps))
    return kl


def char_bigrams_within_words(word_chars_list):
    """Count character bigrams within words."""
    counts = Counter()
    for wc in word_chars_list:
        for i in range(len(wc) - 1):
            counts[(wc[i], wc[i+1])] += 1
    return counts


def rank_correlation(counts1, counts2, top_n=50):
    """Spearman rank correlation of top-N items from counts1 vs counts2."""
    top1 = [item for item, _ in counts1.most_common(top_n)]
    top2 = [item for item, _ in counts2.most_common(top_n)]

    # Union of both top-N lists
    all_items = list(set(top1) | set(top2))
    if len(all_items) < 3:
        return 0.0

    # Rank each item in each distribution (absent = rank at bottom)
    def get_ranks(counts, items):
        sorted_items = [it for it, _ in counts.most_common()]
        rank_map = {it: i+1 for i, it in enumerate(sorted_items)}
        max_rank = len(sorted_items) + 1
        return [rank_map.get(it, max_rank) for it in items]

    r1 = get_ranks(counts1, all_items)
    r2 = get_ranks(counts2, all_items)

    # Spearman: 1 - 6*sum(d^2) / (n*(n^2-1))
    n = len(all_items)
    d_sq = sum((a - b) ** 2 for a, b in zip(r1, r2))
    if n <= 1:
        return 0.0
    rho = 1 - (6 * d_sq) / (n * (n * n - 1))
    return rho


def jaccard_top_n(counts1, counts2, top_n):
    """Jaccard overlap of top-N items."""
    s1 = set(item for item, _ in counts1.most_common(top_n))
    s2 = set(item for item, _ in counts2.most_common(top_n))
    if not s1 and not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def position_char_freq(word_chars_list, max_pos=8):
    """Character frequency distribution at each absolute position."""
    pos_counts = defaultdict(Counter)
    for wc in word_chars_list:
        for i, c in enumerate(wc):
            if i < max_pos:
                pos_counts[i][c] += 1
    # Normalize each position
    pos_dist = {}
    for pos in range(max_pos):
        total = sum(pos_counts[pos].values())
        if total > 0:
            pos_dist[pos] = {c: n/total for c, n in pos_counts[pos].items()}
        else:
            pos_dist[pos] = {}
    return pos_dist


def position_entropy(word_chars_list, max_pos=8):
    """Entropy at each absolute position."""
    pos_counts = defaultdict(Counter)
    for wc in word_chars_list:
        for i, c in enumerate(wc):
            if i < max_pos:
                pos_counts[i][c] += 1
    result = {}
    for pos in range(max_pos):
        total = sum(pos_counts[pos].values())
        if total > 0:
            H = -sum((n/total)*math.log2(n/total)
                     for n in pos_counts[pos].values())
            result[pos] = (H, len(pos_counts[pos]), total)
        else:
            result[pos] = (0, 0, 0)
    return result


def pos_entropy_correlation(pe1, pe2, max_pos=8):
    """Correlation of positional entropy curves."""
    h1 = [pe1.get(i, (0,0,0))[0] for i in range(max_pos)]
    h2 = [pe2.get(i, (0,0,0))[0] for i in range(max_pos)]
    # Only use positions where both have data
    valid = [(a, b) for a, b in zip(h1, h2) if a > 0 and b > 0]
    if len(valid) < 3:
        return 0.0
    a_arr = np.array([x[0] for x in valid])
    b_arr = np.array([x[1] for x in valid])
    if np.std(a_arr) < 1e-10 or np.std(b_arr) < 1e-10:
        return 0.0
    return float(np.corrcoef(a_arr, b_arr)[0, 1])


def word_shape_repetition(word_chars_list):
    """Fraction of word tokens that share their shape with ≥1 other token.
    Shape = sequence of character identities. Also count unique shapes."""
    shapes = Counter()
    for wc in word_chars_list:
        shapes[tuple(wc)] += 1
    n_tokens = sum(shapes.values())
    n_repeated = sum(c for c in shapes.values() if c > 1)
    n_shapes = len(shapes)
    return n_repeated / n_tokens if n_tokens > 0 else 0, n_shapes


def top_initial_chars(word_chars_list, top_n=5):
    """Top N word-initial characters and their frequencies."""
    counts = Counter()
    for wc in word_chars_list:
        if wc:
            counts[wc[0]] += 1
    total = sum(counts.values())
    return [(c, n/total) for c, n in counts.most_common(top_n)]


def top_final_chars(word_chars_list, top_n=5):
    """Top N word-final characters and their frequencies."""
    counts = Counter()
    for wc in word_chars_list:
        if wc:
            counts[wc[-1]] += 1
    total = sum(counts.values())
    return [(c, n/total) for c, n in counts.most_common(top_n)]


def initial_final_hhi(word_chars_list):
    """Herfindahl-Hirschman Index of initial and final character distributions.
    Higher = more concentrated (fewer characters dominate)."""
    init_counts = Counter()
    final_counts = Counter()
    for wc in word_chars_list:
        if wc:
            init_counts[wc[0]] += 1
            final_counts[wc[-1]] += 1
    def hhi(counts):
        total = sum(counts.values())
        if total == 0: return 0
        return sum((n/total)**2 for n in counts.values())
    return hhi(init_counts), hhi(final_counts)


def cross_word_bigrams(word_chars_list):
    """Bigrams that span word boundaries (last char of word N, first char of N+1)."""
    counts = Counter()
    for i in range(len(word_chars_list) - 1):
        w1 = word_chars_list[i]
        w2 = word_chars_list[i+1]
        if w1 and w2:
            counts[(w1[-1], w2[0])] += 1
    return counts


def cross_vs_within_entropy(word_chars_list):
    """Compare entropy of cross-word bigrams vs within-word bigrams."""
    within = char_bigrams_within_words(word_chars_list)
    cross = cross_word_bigrams(word_chars_list)

    def bigram_entropy(counts):
        total = sum(counts.values())
        if total == 0: return 0
        return -sum((n/total)*math.log2(n/total) for n in counts.values())

    return bigram_entropy(within), bigram_entropy(cross)


def zipf_curve(word_list, max_rank=100):
    """Return (rank, frequency) pairs for the top-N words."""
    counts = Counter(word_list)
    ranked = counts.most_common(max_rank)
    total = len(word_list)
    return [(i+1, n/total) for i, (_, n) in enumerate(ranked)]


def zipf_slope(curve):
    """Fit log-log slope to Zipf curve."""
    if len(curve) < 5:
        return 0
    log_r = np.log([r for r, _ in curve])
    log_f = np.log([f for _, f in curve])
    # Linear regression
    A = np.vstack([log_r, np.ones(len(log_r))]).T
    slope, _ = np.linalg.lstsq(A, log_f, rcond=None)[0]
    return slope


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 72)
    pr("word_shape_validation: WORD-SHAPE VALIDATION")
    pr("Is the 10-feature match real or superficial?")
    pr("=" * 72)
    pr()

    # ── Load VMS ──
    pr("Loading VMS corpus...")
    vms_raw = load_vms()
    vms_wc = vms_glyph_words(vms_raw)  # list of glyph lists
    vms_str = [''.join(g) for g in vms_wc]  # string forms
    pr(f"  VMS: {len(vms_wc)} words, {len(set(vms_str))} types")
    pr()

    # ── Load Italian + encode ──
    pr("Fetching Italian source text...")
    ita_words = load_italian()
    ita_wc = [list(w) for w in ita_words]
    pr(f"  Italian: {len(ita_words)} words")
    pr()

    # Best cipher from positional_verbose_cipher grid search
    BEST_PARAMS = {
        'n_c_shared': 4, 'n_c_unique': 3,
        'n_v_shared': 2, 'n_v_unique': 5,
        'n_zones': 3, 'expand_prob': 0.8
    }

    pr("Encoding with positional_verbose_cipher best cipher...")
    cipher_str, cipher_wc = encode_verbose_optimized(ita_words, **BEST_PARAMS)
    pr(f"  Cipher: {len(cipher_str)} words, {len(set(cipher_str))} types")
    pr()

    pr("Encoding simple substitution (control)...")
    subst_str, subst_wc = encode_simple_subst(ita_words)
    pr(f"  Subst: {len(subst_str)} words, {len(set(subst_str))} types")
    pr()

    # Trim all to same token count for fair comparison
    N = min(len(vms_wc), len(cipher_wc), len(subst_wc))
    vms_wc = vms_wc[:N]; vms_str = vms_str[:N]
    cipher_wc = cipher_wc[:N]; cipher_str = cipher_str[:N]
    subst_wc = subst_wc[:N]; subst_str = subst_str[:N]
    ita_wc = ita_wc[:N]; ita_words = ita_words[:N]

    corpora = {
        'VMS': (vms_str, vms_wc),
        'Cipher': (cipher_str, cipher_wc),
        'Subst': (subst_str, subst_wc),
        'Italian': (ita_words, ita_wc),
    }

    # ═══════════════════════════════════════════════════════════════════
    # 61a) WORD-LENGTH DISTRIBUTION
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("61a) WORD-LENGTH DISTRIBUTION")
    pr("=" * 72)
    pr()

    len_dists = {}
    for name, (ws, wc) in corpora.items():
        len_dists[name] = word_length_distribution(ws)

    pr(f"  {'Len':>3s}", end='')
    for name in corpora:
        pr(f"  {name:>8s}", end='')
    pr()
    pr(f"  {'---':>3s}", end='')
    for _ in corpora:
        pr(f"  {'--------':>8s}", end='')
    pr()
    for l in range(1, 13):
        pr(f"  {l:>3d}", end='')
        for name in corpora:
            pr(f"  {len_dists[name].get(l,0):>8.3f}", end='')
        pr()
    pr()

    # L1 distances and KL divergence
    pr("  L1 distance from VMS:")
    for name in ['Cipher', 'Subst', 'Italian']:
        l1 = length_dist_l1(len_dists['VMS'], len_dists[name])
        kl = length_dist_kl(len_dists['VMS'], len_dists[name])
        pr(f"    {name:10s}: L1={l1:.4f}, KL={kl:.4f} bits")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 61b) CHARACTER BIGRAM ANALYSIS
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("61b) CHARACTER BIGRAM ANALYSIS")
    pr("=" * 72)
    pr()

    bigram_counts = {}
    for name, (ws, wc) in corpora.items():
        bigram_counts[name] = char_bigrams_within_words(wc)

    # Rank correlation and Jaccard overlap
    pr("  Bigram rank correlation with VMS (Spearman ρ):")
    for name in ['Cipher', 'Subst', 'Italian']:
        for top_n in [20, 50, 100]:
            rho = rank_correlation(bigram_counts['VMS'],
                                   bigram_counts[name], top_n)
            pr(f"    {name:10s} top-{top_n:3d}: ρ = {rho:+.3f}")
    pr()

    pr("  Jaccard overlap of top-N bigrams with VMS:")
    for name in ['Cipher', 'Subst', 'Italian']:
        for top_n in [10, 20, 50]:
            j = jaccard_top_n(bigram_counts['VMS'],
                              bigram_counts[name], top_n)
            pr(f"    {name:10s} top-{top_n:3d}: J = {j:.3f}")
    pr()

    # Show top 10 bigrams for each
    pr("  Top 10 within-word bigrams:")
    for name in corpora:
        top10 = bigram_counts[name].most_common(10)
        items = ', '.join(f"{''.join(bg)}({n})" for bg, n in top10)
        pr(f"    {name:10s}: {items}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 61c) POSITION-SPECIFIC ENTROPY CURVE
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("61c) POSITIONAL ENTROPY CURVE")
    pr("=" * 72)
    pr()

    pos_entropies = {}
    for name, (ws, wc) in corpora.items():
        pos_entropies[name] = position_entropy(wc)

    pr(f"  {'Pos':>3s}", end='')
    for name in corpora:
        pr(f"  {name+' H':>8s}  {name+' #':>5s}", end='')
    pr()
    pr("  " + "-" * (3 + len(corpora) * 16))
    for pos in range(8):
        pr(f"  {pos+1:>3d}", end='')
        for name in corpora:
            H, ntypes, total = pos_entropies[name].get(pos, (0,0,0))
            if total > 0:
                pr(f"  {H:>8.3f}  {ntypes:>5d}", end='')
            else:
                pr(f"  {'--':>8s}  {'--':>5s}", end='')
        pr()
    pr()

    # Correlation of entropy curves
    pr("  Positional entropy correlation with VMS:")
    for name in ['Cipher', 'Subst', 'Italian']:
        r = pos_entropy_correlation(pos_entropies['VMS'],
                                     pos_entropies[name])
        pr(f"    {name:10s}: r = {r:+.3f}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 61d) WORD-SHAPE REPETITION & STEREOTYPY
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("61d) WORD-SHAPE REPETITION & STEREOTYPY")
    pr("=" * 72)
    pr()

    pr(f"  {'Corpus':10s} {'Rep%':>8s} {'Shapes':>8s} {'TTR':>8s} "
       f"{'Top1%':>8s} {'Top5%':>8s}")
    pr("  " + "-" * 52)
    for name, (ws, wc) in corpora.items():
        rep_rate, n_shapes = word_shape_repetition(wc)
        wfreq = Counter(ws)
        top1_pct = wfreq.most_common(1)[0][1] / len(ws) if ws else 0
        top5_pct = sum(c for _, c in wfreq.most_common(5)) / len(ws) if ws else 0
        ttr = len(set(ws)) / len(ws)
        pr(f"  {name:10s} {rep_rate:>8.1%} {n_shapes:>8d} {ttr:>8.4f} "
           f"{top1_pct:>8.2%} {top5_pct:>8.2%}")
    pr()

    # Top 10 most frequent words
    pr("  Top 10 most frequent words:")
    for name, (ws, wc) in corpora.items():
        wfreq = Counter(ws)
        top10 = wfreq.most_common(10)
        items = ', '.join(f"{w}({n})" for w, n in top10)
        pr(f"    {name:10s}: {items}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 61e) INITIAL/FINAL CHARACTER CONCENTRATION
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("61e) INITIAL / FINAL CHARACTER CONCENTRATION")
    pr("=" * 72)
    pr()

    for name, (ws, wc) in corpora.items():
        init_hhi, final_hhi = initial_final_hhi(wc)
        init_top = top_initial_chars(wc, 5)
        final_top = top_final_chars(wc, 5)
        pr(f"  {name}:")
        pr(f"    Initial HHI={init_hhi:.4f}  "
           f"top-5: {', '.join(f'{c}({p:.0%})' for c,p in init_top)}")
        pr(f"    Final   HHI={final_hhi:.4f}  "
           f"top-5: {', '.join(f'{c}({p:.0%})' for c,p in final_top)}")
        pr()

    # ═══════════════════════════════════════════════════════════════════
    # 61f) CROSS-WORD-BOUNDARY ANALYSIS
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("61f) CROSS-WORD-BOUNDARY BIGRAMS")
    pr("=" * 72)
    pr()

    for name, (ws, wc) in corpora.items():
        h_within, h_cross = cross_vs_within_entropy(wc)
        cross_cnt = cross_word_bigrams(wc)
        n_cross_types = len(cross_cnt)
        pr(f"  {name:10s}: H(within)={h_within:.3f}  H(cross)={h_cross:.3f}  "
           f"Δ={h_cross - h_within:+.3f}  cross types={n_cross_types}")
    pr()

    pr("  Interpretation: VMS is known to have suppressed cross-word")
    pr("  bigram diversity. If cipher shows similar Δ, the model")
    pr("  reproduces this structural feature.")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 61g) ZIPF CURVE
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("61g) ZIPF RANK-FREQUENCY CURVE")
    pr("=" * 72)
    pr()

    for name, (ws, wc) in corpora.items():
        curve = zipf_curve(ws, 100)
        slope = zipf_slope(curve)
        top5 = curve[:5]
        top5_str = ', '.join(f"r{r}={f:.3f}" for r, f in top5)
        pr(f"  {name:10s}: slope={slope:.3f}  {top5_str}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 61h) COMPOSITE SCORECARD
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("61h) COMPOSITE WORD-SHAPE SCORECARD")
    pr("=" * 72)
    pr()

    # Compute all comparison metrics for Cipher, Subst, Italian
    scores = {}
    for name in ['Cipher', 'Subst', 'Italian']:
        ws, wc = corpora[name]
        s = {}

        # 1. Word length L1
        s['wlen_L1'] = length_dist_l1(len_dists['VMS'], len_dists[name])

        # 2. Bigram rank correlation (top-50)
        s['bigram_rho'] = rank_correlation(bigram_counts['VMS'],
                                            bigram_counts[name], 50)

        # 3. Bigram Jaccard (top-20)
        s['bigram_J20'] = jaccard_top_n(bigram_counts['VMS'],
                                         bigram_counts[name], 20)

        # 4. Positional entropy correlation
        s['pos_H_corr'] = pos_entropy_correlation(pos_entropies['VMS'],
                                                    pos_entropies[name])

        # 5. Initial HHI difference
        ci_hhi, cf_hhi = initial_final_hhi(wc)
        vi_hhi, vf_hhi = initial_final_hhi(corpora['VMS'][1])
        s['init_HHI_delta'] = abs(ci_hhi - vi_hhi)
        s['final_HHI_delta'] = abs(cf_hhi - vf_hhi)

        # 6. Cross-boundary entropy delta difference
        h_w, h_c = cross_vs_within_entropy(wc)
        h_vw, h_vc = cross_vs_within_entropy(corpora['VMS'][1])
        s['cross_delta_diff'] = abs((h_c - h_w) - (h_vc - h_vw))

        # 7. Zipf slope difference
        c_slope = zipf_slope(zipf_curve(ws, 100))
        v_slope = zipf_slope(zipf_curve(corpora['VMS'][0], 100))
        s['zipf_slope_delta'] = abs(c_slope - v_slope)

        # 8. Repetition rate difference
        c_rep, _ = word_shape_repetition(wc)
        v_rep, _ = word_shape_repetition(corpora['VMS'][1])
        s['rep_rate_delta'] = abs(c_rep - v_rep)

        scores[name] = s

    # Print scorecard
    metrics_display = [
        ('wlen_L1', 'Word-length L1', 'lower=better', True),
        ('bigram_rho', 'Bigram rank ρ', 'higher=better', False),
        ('bigram_J20', 'Bigram Jaccard-20', 'higher=better', False),
        ('pos_H_corr', 'Pos entropy corr', 'higher=better', False),
        ('init_HHI_delta', 'Initial HHI Δ', 'lower=better', True),
        ('final_HHI_delta', 'Final HHI Δ', 'lower=better', True),
        ('cross_delta_diff', 'Cross-boundary Δ', 'lower=better', True),
        ('zipf_slope_delta', 'Zipf slope Δ', 'lower=better', True),
        ('rep_rate_delta', 'Repetition rate Δ', 'lower=better', True),
    ]

    pr(f"  {'Metric':22s} {'Cipher':>10s} {'Subst':>10s} "
       f"{'Italian':>10s} {'Best?':>8s}")
    pr("  " + "-" * 62)

    cipher_wins = 0
    total_metrics = len(metrics_display)

    for key, label, direction, lower_is_better in metrics_display:
        vals = {n: scores[n][key] for n in ['Cipher', 'Subst', 'Italian']}
        if lower_is_better:
            best = min(vals, key=vals.get)
        else:
            best = max(vals, key=vals.get)
        flag = "← CIPHER" if best == 'Cipher' else ""
        if best == 'Cipher':
            cipher_wins += 1
        pr(f"  {label:22s} {vals['Cipher']:>10.4f} {vals['Subst']:>10.4f} "
           f"{vals['Italian']:>10.4f} {flag:>8s}")
    pr()
    pr(f"  Cipher beats both controls on {cipher_wins}/{total_metrics} "
       f"word-shape metrics")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # 61i) CRITICAL ASSESSMENT
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("61i) CRITICAL ASSESSMENT")
    pr("=" * 72)
    pr()

    pr("  The 10-feature fingerprint matching (positional_verbose_cipher) is validated if")
    pr("  the cipher also produces VMS-like word shapes at the micro-level.")
    pr()

    if cipher_wins >= 6:
        pr(f"  RESULT: VALIDATED — Cipher wins {cipher_wins}/{total_metrics} "
           f"word-shape metrics.")
        pr(f"  The position-variant verbose cipher reproduces VMS structure")
        pr(f"  at both summary AND micro levels. The 10-feature match is")
        pr(f"  NOT superficial.")
    elif cipher_wins >= 4:
        pr(f"  RESULT: PARTIAL — Cipher wins {cipher_wins}/{total_metrics} "
           f"metrics.")
        pr(f"  The model captures SOME but not all word-shape features.")
        pr(f"  The 10-feature match is real but incomplete.")
    else:
        pr(f"  RESULT: SUPERFICIAL — Cipher only wins "
           f"{cipher_wins}/{total_metrics} metrics.")
        pr(f"  The 10-feature match does NOT generalize to micro-level")
        pr(f"  word structure. The model gets the right summary statistics")
        pr(f"  for the wrong reasons.")
    pr()

    # Which specific word-shape features match and which don't?
    pr("  Feature-level diagnosis:")
    for key, label, direction, lower_is_better in metrics_display:
        cv = scores['Cipher'][key]
        sv = scores['Subst'][key]
        iv = scores['Italian'][key]
        if lower_is_better:
            cipher_better = cv < min(sv, iv)
        else:
            cipher_better = cv > max(sv, iv)

        if cipher_better:
            pr(f"    ✓ {label}: cipher is closest to VMS")
        else:
            # Who's closest?
            vals = {'Cipher': cv, 'Subst': sv, 'Italian': iv}
            if lower_is_better:
                closest = min(vals, key=vals.get)
            else:
                closest = max(vals, key=vals.get)
            pr(f"    ✗ {label}: {closest} is closer to VMS")
    pr()

    # ── Save results ──
    out_path = Path("results/word_shape_validation_output.json")
    out_path.parent.mkdir(exist_ok=True)
    json_data = {
        'scores': {name: {k: float(v) for k, v in s.items()}
                   for name, s in scores.items()},
        'cipher_wins': cipher_wins,
        'total_metrics': total_metrics,
        'word_length_dists': {name: {str(k): float(v)
                                      for k, v in d.items()}
                               for name, d in len_dists.items()},
    }
    with open(out_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    pr(f"\nResults saved to {out_path}")


if __name__ == '__main__':
    main()
