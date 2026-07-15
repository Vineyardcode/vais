"""VAIS statistical fingerprint: one feature vector per corpus.

The full profile the research program scores generative hypotheses against:
  - entropy stack: h0/h1/h2 at character level, word-level entropy
  - lexicon shape: Zipf alpha, Heaps beta, TTR@5k, hapax@midpoint,
    mean word length, type/token counts
  - word-grammar rigidity: positional character predictability inside words
  - line effects: divergence of line-initial and line-final word starts /
    endings from line-interior words (the documented VMS line-as-unit
    phenomenon)
  - repetition texture: adjacent-token similarity (Timm's statistic) —
    exact repeats and near-repeats (normalized edit distance <= 0.25)

Input is a list of LINES, each a list of word strings. All features are
deterministic. Character units are whatever the caller's tokenization
produced (this module never re-tokenizes — alphabet choice is exactly the
assumption under test upstream).
"""
import math
from collections import Counter

from .core import entropy, ttr_at_n, hapax_ratio_at_midpoint, zipf_alpha

try:
    import numpy as np
except ImportError:
    np = None


def levenshtein(a, b):
    """Plain dynamic-programming edit distance (words are short)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def heaps_beta(tokens, sample_points=20):
    """Heaps' law exponent (same regression as the suite's family)."""
    n = len(tokens)
    if n < 200 or np is None:
        return float('nan')
    points = np.linspace(100, n, sample_points, dtype=int)
    running = set()
    idx = 0
    log_n, log_v = [], []
    for p in sorted(points):
        while idx < p:
            running.add(tokens[idx])
            idx += 1
        log_n.append(math.log(p))
        log_v.append(math.log(len(running)))
    A = np.vstack([np.array(log_n), np.ones(len(log_n))]).T
    slope, _ = np.linalg.lstsq(A, np.array(log_v), rcond=None)[0]
    return float(slope)


def char_entropy_stack(tokens):
    """(h0, h1, h2) over the character stream with word-boundary marker.

    h0 = log2(alphabet size); h1 = unigram entropy; h2 = conditional
    entropy H(c|prev) = H(bigram) - H(prev-marginal).
    """
    stream = []
    for w in tokens:
        stream.extend(w)
        stream.append(' ')
    if len(stream) < 3:
        return float('nan'), float('nan'), float('nan')
    uni = Counter(stream)
    h0 = math.log2(len(uni))
    h1 = entropy(uni)
    bi = Counter(zip(stream, stream[1:]))
    prev = Counter(dict(Counter(c1 for (c1, _) in bi.elements())))
    # prev marginal derived from the same bigram population
    prevm = Counter()
    for (c1, _), n in bi.items():
        prevm[c1] += n
    h2 = entropy(bi) - entropy(prevm)
    return h0, h1, h2


def positional_predictability(tokens, max_len=12):
    """Word-grammar rigidity: mean per-position character entropy,
    normalized by unigram char entropy. Low = rigid slot structure."""
    by_pos = [Counter() for _ in range(max_len)]
    allc = Counter()
    for w in tokens:
        for i, c in enumerate(w[:max_len]):
            by_pos[i][c] += 1
            allc[c] += 1
    h_all = entropy(allc)
    if h_all == 0:
        return float('nan')
    hs = [entropy(c) for c in by_pos if sum(c.values()) >= 100]
    if not hs:
        return float('nan')
    return (sum(hs) / len(hs)) / h_all


def line_effect_scores(lines):
    """JSD-style divergence of line-initial first-characters and line-final
    last-characters vs line-interior words. Near 0 for prose broken at
    arbitrary points; markedly positive for the VMS."""
    def jsd(c1, c2):
        keys = set(c1) | set(c2)
        t1, t2 = sum(c1.values()) or 1, sum(c2.values()) or 1
        d = 0.0
        for k in keys:
            p, q = c1.get(k, 0) / t1, c2.get(k, 0) / t2
            m = (p + q) / 2
            if p > 0 and m > 0:
                d += 0.5 * p * math.log2(p / m)
            if q > 0 and m > 0:
                d += 0.5 * q * math.log2(q / m)
        return d

    init_first, inter_first = Counter(), Counter()
    final_last, inter_last = Counter(), Counter()
    for words in lines:
        if len(words) < 3:
            continue
        init_first[words[0][0]] += 1
        final_last[words[-1][-1]] += 1
        for w in words[1:-1]:
            inter_first[w[0]] += 1
            inter_last[w[-1]] += 1
    return (jsd(init_first, inter_first), jsd(final_last, inter_last))


def adjacency_repetition(lines, near_threshold=0.25):
    """Timm's texture: fraction of adjacent token pairs that are exact
    repeats, and fraction that are near-repeats (normalized edit distance
    <= threshold, excluding exact)."""
    pairs = 0
    exact = 0
    near = 0
    for words in lines:
        for a, b in zip(words, words[1:]):
            pairs += 1
            if a == b:
                exact += 1
                continue
            d = levenshtein(a, b) / max(len(a), len(b))
            if d <= near_threshold:
                near += 1
    if pairs == 0:
        return float('nan'), float('nan')
    return exact / pairs, near / pairs


FEATURE_ORDER = [
    'n_tokens', 'n_types', 'mean_wlen', 'ttr_5000', 'hapax_mid',
    'heaps_beta', 'zipf_alpha', 'h0_char', 'h1_char', 'h2_char',
    'h2_ratio', 'h_word', 'pos_predict', 'line_init_jsd',
    'line_final_jsd', 'adj_exact', 'adj_near',
]


def fingerprint(lines, label=""):
    """Compute the full feature dict for a corpus given as lines of words."""
    tokens = [w for line in lines for w in line]
    types = Counter(tokens)
    h0, h1, h2 = char_entropy_stack(tokens)
    li, lf = line_effect_scores(lines)
    ax, an = adjacency_repetition(lines)
    return {
        'label': label,
        'n_tokens': len(tokens),
        'n_types': len(types),
        'mean_wlen': sum(len(w) for w in tokens) / max(len(tokens), 1),
        'ttr_5000': ttr_at_n(tokens, 5000),
        'hapax_mid': hapax_ratio_at_midpoint(tokens),
        'heaps_beta': heaps_beta(tokens),
        'zipf_alpha': zipf_alpha(tokens),
        'h0_char': h0, 'h1_char': h1, 'h2_char': h2,
        'h2_ratio': (h2 / h1) if (h1 and not math.isnan(h1) and h1 > 0) else float('nan'),
        'h_word': entropy(types),
        'pos_predict': positional_predictability(tokens),
        'line_init_jsd': li, 'line_final_jsd': lf,
        'adj_exact': ax, 'adj_near': an,
    }


def z_distance(fp, refs, features=None):
    """Mean |z| of fp against the reference set (per-feature mean/std over
    refs). NaN features are skipped. refs: list of fingerprint dicts."""
    if np is None:
        raise RuntimeError("numpy required")
    features = features or [f for f in FEATURE_ORDER
                            if f not in ('n_tokens', 'n_types')]
    zs = []
    for f in features:
        vals = [r[f] for r in refs
                if isinstance(r.get(f), float) and not math.isnan(r[f])]
        v = fp.get(f)
        if len(vals) < 2 or not isinstance(v, float) or math.isnan(v):
            continue
        mu, sd = float(np.mean(vals)), float(np.std(vals))
        if sd < 1e-12:
            continue
        zs.append(abs((v - mu) / sd))
    return sum(zs) / len(zs) if zs else float('nan'), len(zs)
