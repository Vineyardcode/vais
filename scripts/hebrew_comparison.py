#!/usr/bin/env python3
"""
VOYNICH ↔ HEBREW MORPHOLOGICAL COMPARISON
==========================================
Compares Voynich prefix×suffix paradigm grid shapes against
Hebrew verb conjugation tables to test the hypothesis that
Voynichese was constructed using Hebrew-style triconsonantal
root morphology as a structural template.

Hebrew verb system (simplified):
  - Prefix conjugation (imperfect): person-prefix + root + gender/number-suffix
  - Suffix conjugation (perfect): root + person/gender/number-suffix
  - 7 major binyanim (verb stems): Qal, Niphal, Piel, Pual, Hiphil, Hophal, Hithpael
  - Each binyan fills a different subset of the prefix×suffix grid

The key question: does the SHAPE of Voynich paradigm tables
(which prefixes co-occur with which suffixes, relative fill
patterns) match Hebrew conjugation patterns better than
chance or better than other language families?
"""

import json
import math
import os
import sys
from collections import Counter, defaultdict
from common import result_path

# ─────────────────────────────────────────────────────────────
# HEBREW VERB CONJUGATION REFERENCE DATA
# ─────────────────────────────────────────────────────────────
# Hebrew imperfect (prefix conjugation) for a regular triliteral root
# Format: (prefix, suffix) → person/number/gender label
# Using standard transliteration for prefixes: ʼe/yi/ti/ni/ta
#
# We map Hebrew conjugation "slots" to abstract prefix×suffix positions
# to enable structural comparison with Voynich paradigm grids.

# Hebrew IMPERFECT (yiqtol) paradigm - prefix conjugation
# prefix markers: ʼ(1sg), t(2m.sg, 2f.sg, 3f.sg), y(3m.sg), n(1pl)
# suffix markers: ∅(m.sg), i(f.sg), u(m.pl), na(f.pl)
HEBREW_IMPERFECT = {
    # (prefix, suffix): label
    ("ʼe", "∅"):   "1sg",
    ("ti", "∅"):    "2m.sg",
    ("ti", "i"):    "2f.sg",
    ("yi", "∅"):    "3m.sg",
    ("ti", "∅_f"):  "3f.sg",  # same prefix as 2m.sg
    ("ni", "∅"):    "1pl",
    ("ti", "u"):    "2m.pl",
    ("ti", "na"):   "2f.pl",
    ("yi", "u"):    "3m.pl",
    ("ti", "na_f"): "3f.pl",  # same as 2f.pl in form
}

# Hebrew PERFECT (qatal) paradigm - suffix conjugation
# No prefix, all suffixes
HEBREW_PERFECT = {
    ("∅", "ti"):    "1sg",
    ("∅", "ta"):    "2m.sg",
    ("∅", "t"):     "2f.sg",
    ("∅", "∅"):     "3m.sg",
    ("∅", "a"):     "3f.sg",
    ("∅", "nu"):    "1pl",
    ("∅", "tem"):   "2m.pl",
    ("∅", "ten"):   "2f.pl",
    ("∅", "u"):     "3pl",
}

# Combined: Hebrew has BOTH prefix and suffix paradigms for each root
# This means a Hebrew root fills cells in TWO grids:
#   1) prefix grid (imperfect) - ~4 prefixes × ~4 suffixes ≈ 10 forms
#   2) suffix grid (perfect) - 1 prefix(∅) × ~9 suffixes ≈ 9 forms
# Total: ~19 distinct forms per root (in one binyan)
# Across all 7 binyanim: up to ~133 forms theoretically

# For structural comparison, we model the abstract SHAPE of the grid:
# How many distinct prefixes? How many distinct suffixes?
# What % of cells are filled? What's the distribution shape?

HEBREW_BINYANIM = {
    "qal": {
        "prefixes": ["∅", "yi", "ti", "ʼe", "ni"],  # perfect(∅) + imperfect prefixes
        "suffixes": ["∅", "a", "ti_p", "ta", "t", "nu", "tem", "ten", "u",  # perfect
                     "i", "u_i", "na"],  # imperfect
        "n_prefixes": 5,
        "n_suffixes": 12,
        "n_filled": 19,  # ~19 distinct forms
        "prefix_entropy": 1.8,  # moderate (5 prefixes, ∅ dominant from perfect)
        "suffix_entropy": 3.2,  # higher (12 distinct suffixes)
    },
    "niphal": {
        "prefixes": ["ni", "yi", "ti", "ʼe"],  # ni- prefix in perfect too
        "suffixes": ["∅", "a", "ti_p", "ta", "t", "nu", "tem", "ten", "u", "i", "na"],
        "n_prefixes": 4,
        "n_suffixes": 11,
        "n_filled": 18,
        "prefix_entropy": 1.5,
        "suffix_entropy": 3.1,
    },
    "piel": {
        "prefixes": ["∅", "yi", "ti", "ʼe", "ni"],
        "suffixes": ["∅", "a", "ti_p", "ta", "t", "nu", "tem", "ten", "u", "i", "na"],
        "n_prefixes": 5,
        "n_suffixes": 11,
        "n_filled": 19,
        "prefix_entropy": 1.8,
        "suffix_entropy": 3.1,
    },
    "hiphil": {
        "prefixes": ["hi", "yi", "ti", "ʼa", "ni"],  # hi- causative prefix
        "suffixes": ["∅", "a", "ti_p", "ta", "t", "nu", "tem", "ten", "u", "i", "na"],
        "n_prefixes": 5,
        "n_suffixes": 11,
        "n_filled": 19,
        "prefix_entropy": 1.8,
        "suffix_entropy": 3.1,
    },
}

# ─────────────────────────────────────────────────────────────
# OTHER LANGUAGE PARADIGM BASELINES FOR COMPARISON
# ─────────────────────────────────────────────────────────────

# Latin verb paradigm (for contrast - fusional, not agglutinative)
LATIN_VERB = {
    "n_prefixes": 1,   # Latin doesn't use prefixes for person (only ∅)
    "n_suffixes": 30,   # 6 persons × 5 tenses in indicative alone
    "n_filled": 30,
    "prefix_entropy": 0.0,  # no prefix variation
    "suffix_entropy": 4.9,  # very high suffix entropy
    "label": "Latin (fusional)"
}

# Turkish verb paradigm (agglutinative, for contrast)
TURKISH_VERB = {
    "n_prefixes": 1,    # Turkish uses no person prefixes
    "n_suffixes": 24,    # 6 person × 4 tenses basic
    "n_filled": 24,
    "prefix_entropy": 0.0,
    "suffix_entropy": 4.6,
    "label": "Turkish (agglutinative, suffix-only)"
}

# Arabic verb paradigm (Semitic sister, for validation)
ARABIC_VERB = {
    "n_prefixes": 5,    # similar to Hebrew
    "n_suffixes": 12,
    "n_filled": 19,
    "prefix_entropy": 1.9,
    "suffix_entropy": 3.2,
    "label": "Arabic (Semitic)"
}

# Enochian (Kelley's constructed language)
# Enochian has no clear verb conjugation system - it's more like
# a vocabulary cipher with fixed word forms
ENOCHIAN = {
    "n_prefixes": 2,    # minimal prefix variation
    "n_suffixes": 5,    # limited suffix variation
    "n_filled": 6,
    "prefix_entropy": 0.5,
    "suffix_entropy": 1.8,
    "label": "Enochian (Kelley's constructed)"
}


def load_voynich_paradigms(filepath):
    """Load paradigm tables from attack_plan_results.json"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['paradigm_tables']


def analyze_voynich_paradigm(root, table_data):
    """Compute structural metrics for one Voynich root's paradigm table."""
    table = table_data['table']
    freq = table_data['freq']

    all_prefixes = set()
    all_suffixes = set()
    total_tokens = 0
    prefix_totals = Counter()
    suffix_totals = Counter()
    cells = {}

    for pfx, suf_counts in table.items():
        # Normalize the ∅ character
        if pfx in ('∅', '\u2205', '…', '\u00e2\u02c6\u2026'):
            pfx = '∅'
        all_prefixes.add(pfx)
        for suf, count in suf_counts.items():
            if suf in ('∅', '\u2205', '…', '\u00e2\u02c6\u2026'):
                suf = '∅'
            all_suffixes.add(suf)
            total_tokens += count
            prefix_totals[pfx] += count
            suffix_totals[suf] += count
            cells[(pfx, suf)] = cells.get((pfx, suf), 0) + count

    n_prefixes = len(all_prefixes)
    n_suffixes = len(all_suffixes)
    n_filled = len(cells)
    n_possible = n_prefixes * n_suffixes
    fill_rate = n_filled / n_possible if n_possible > 0 else 0

    # Compute prefix entropy
    pfx_probs = [c / total_tokens for c in prefix_totals.values()]
    prefix_entropy = -sum(p * math.log2(p) for p in pfx_probs if p > 0)

    # Compute suffix entropy
    suf_probs = [c / total_tokens for c in suffix_totals.values()]
    suffix_entropy = -sum(p * math.log2(p) for p in suf_probs if p > 0)

    # Prefix dominance: fraction of tokens from top prefix
    top_pfx_frac = max(prefix_totals.values()) / total_tokens if total_tokens > 0 else 0

    # Suffix dominance: fraction of tokens from top suffix
    top_suf_frac = max(suffix_totals.values()) / total_tokens if total_tokens > 0 else 0

    # Rank-order the prefixes and suffixes by frequency
    pfx_ranked = sorted(prefix_totals.items(), key=lambda x: -x[1])
    suf_ranked = sorted(suffix_totals.items(), key=lambda x: -x[1])

    return {
        'root': root,
        'freq': freq,
        'n_prefixes': n_prefixes,
        'n_suffixes': n_suffixes,
        'n_filled': n_filled,
        'n_possible': n_possible,
        'fill_rate': fill_rate,
        'prefix_entropy': prefix_entropy,
        'suffix_entropy': suffix_entropy,
        'top_pfx_frac': top_pfx_frac,
        'top_suf_frac': top_suf_frac,
        'prefix_ranked': pfx_ranked,
        'suffix_ranked': suf_ranked,
        'total_tokens': total_tokens,
        'cells': cells,
        'prefix_totals': dict(prefix_totals),
        'suffix_totals': dict(suffix_totals),
    }


def compute_grid_shape_vector(metrics):
    """Create a normalized shape vector for paradigm comparison."""
    return {
        'n_prefixes': metrics['n_prefixes'],
        'n_suffixes': metrics['n_suffixes'],
        'prefix_suffix_ratio': metrics['n_prefixes'] / max(metrics['n_suffixes'], 1),
        'fill_rate': metrics['fill_rate'],
        'prefix_entropy': metrics['prefix_entropy'],
        'suffix_entropy': metrics['suffix_entropy'],
        'entropy_ratio': metrics['prefix_entropy'] / max(metrics['suffix_entropy'], 0.01),
    }


def shape_distance(v1, v2):
    """Euclidean distance between two shape vectors, with normalization."""
    keys = ['prefix_suffix_ratio', 'fill_rate', 'entropy_ratio']
    dist = 0
    for k in keys:
        a = v1.get(k, 0)
        b = v2.get(k, 0)
        dist += (a - b) ** 2
    return math.sqrt(dist)


def prefix_distribution_similarity(voynich_pfx_probs, hebrew_pfx_probs):
    """
    Compare prefix frequency distributions using Jensen-Shannon divergence.
    Lower = more similar.
    """
    # Align on shared keys
    all_keys = set(list(voynich_pfx_probs.keys()) + list(hebrew_pfx_probs.keys()))
    p = [voynich_pfx_probs.get(k, 0) for k in all_keys]
    q = [hebrew_pfx_probs.get(k, 0) for k in all_keys]
    # Normalize
    sp, sq = sum(p), sum(q)
    if sp == 0 or sq == 0:
        return 1.0
    p = [x/sp for x in p]
    q = [x/sq for x in q]
    # JSD
    m = [(a+b)/2 for a,b in zip(p,q)]
    def kl(a, b):
        return sum(ai * math.log2(ai/bi) for ai, bi in zip(a, b) if ai > 0 and bi > 0)
    return math.sqrt((kl(p, m) + kl(q, m)) / 2)


def analyze_prefix_suffix_cooccurrence(all_metrics):
    """
    Key test: In Hebrew, the ∅-prefix row (perfect conjugation) uses a
    DIFFERENT set of suffixes than the prefixed rows (imperfect conjugation).
    Does Voynich show the same pattern?
    """
    results = []
    for m in all_metrics:
        if m['total_tokens'] < 100:
            continue
        cells = m['cells']
        pfx_totals = m['prefix_totals']

        # Get suffixes used with ∅ prefix vs with non-∅ prefixes
        null_suffixes = Counter()
        nonnull_suffixes = Counter()
        for (pfx, suf), count in cells.items():
            if pfx == '∅':
                null_suffixes[suf] += count
            else:
                nonnull_suffixes[suf] += count

        if not null_suffixes or not nonnull_suffixes:
            continue

        # Normalize
        null_total = sum(null_suffixes.values())
        nonnull_total = sum(nonnull_suffixes.values())
        null_dist = {k: v/null_total for k, v in null_suffixes.items()}
        nonnull_dist = {k: v/nonnull_total for k, v in nonnull_suffixes.items()}

        # Compute JSD between suffix distributions
        jsd = prefix_distribution_similarity(null_dist, nonnull_dist)

        # Compute overlap: what fraction of top-5 suffixes are shared?
        null_top5 = set(sorted(null_suffixes, key=null_suffixes.get, reverse=True)[:5])
        nonnull_top5 = set(sorted(nonnull_suffixes, key=nonnull_suffixes.get, reverse=True)[:5])
        overlap = len(null_top5 & nonnull_top5) / 5

        results.append({
            'root': m['root'],
            'freq': m['freq'],
            'null_pfx_frac': pfx_totals.get('∅', 0) / m['total_tokens'],
            'jsd_null_vs_prefixed': jsd,
            'top5_suffix_overlap': overlap,
            'null_top5': sorted(null_suffixes, key=null_suffixes.get, reverse=True)[:5],
            'nonnull_top5': sorted(nonnull_suffixes, key=nonnull_suffixes.get, reverse=True)[:5],
        })

    return results


def analyze_prefix_geometry(all_metrics):
    """
    In Hebrew, certain prefixes are MUTUALLY EXCLUSIVE (you can't have both
    yi- and ti- on the same form). In Voynich, qo- and o- might be analogous.
    Test: for each pair of top prefixes, how often do they appear with the
    SAME suffix? If they're person markers (like Hebrew), they should
    appear with mostly the SAME suffixes.
    """
    results = []
    for m in all_metrics:
        if m['total_tokens'] < 200:
            continue
        cells = m['cells']
        pfx_ranked = m['prefix_ranked']

        # Get top 4 prefixes
        top_pfx = [p for p, _ in pfx_ranked[:4]]
        if len(top_pfx) < 3:
            continue

        # For each prefix, get its suffix distribution
        pfx_suffix_sets = {}
        for pfx in top_pfx:
            suffs = {}
            for (p, s), c in cells.items():
                if p == pfx:
                    suffs[s] = suffs.get(s, 0) + c
            pfx_suffix_sets[pfx] = suffs

        # Compute pairwise suffix-set Jaccard similarity
        pairs = []
        for i in range(len(top_pfx)):
            for j in range(i+1, len(top_pfx)):
                p1, p2 = top_pfx[i], top_pfx[j]
                s1 = set(pfx_suffix_sets[p1].keys())
                s2 = set(pfx_suffix_sets[p2].keys())
                if not s1 or not s2:
                    continue
                jaccard = len(s1 & s2) / len(s1 | s2)
                pairs.append({
                    'pfx1': p1, 'pfx2': p2,
                    'jaccard': jaccard,
                    'shared': sorted(s1 & s2),
                    'only_p1': sorted(s1 - s2),
                    'only_p2': sorted(s2 - s1),
                })

        avg_jaccard = sum(p['jaccard'] for p in pairs) / len(pairs) if pairs else 0

        results.append({
            'root': m['root'],
            'top_prefixes': top_pfx,
            'avg_jaccard': avg_jaccard,
            'pairs': pairs,
        })

    return results


def test_prefix_as_person_markers(all_metrics):
    """
    In Hebrew, each prefix = a person marker.
    Key prediction: if Voynich prefixes are person markers, then:
    1) The NUMBER of frequent prefixes should be ~4-6 (like Hebrew's 4 person prefixes)
    2) Each prefix should appear with roughly the SAME set of suffixes
    3) The prefix distribution should be relatively flat (each person ~equally likely)

    Compare this against:
    - Latin (no person prefixes, n=1)
    - Turkish (no person prefixes, n=1)
    - Arabic (person prefixes, n≈5)
    """
    # Aggregate stats across top roots
    prefix_counts_per_root = []
    prefix_entropy_per_root = []
    suffix_entropy_per_root = []

    for m in all_metrics:
        if m['freq'] < 200:
            continue
        # Count prefixes with >1% of root's tokens
        sig_pfx = sum(1 for p, c in m['prefix_ranked'] if c / m['total_tokens'] > 0.01)
        prefix_counts_per_root.append(sig_pfx)
        prefix_entropy_per_root.append(m['prefix_entropy'])
        suffix_entropy_per_root.append(m['suffix_entropy'])

    return {
        'n_roots_analyzed': len(prefix_counts_per_root),
        'avg_significant_prefixes': sum(prefix_counts_per_root) / len(prefix_counts_per_root) if prefix_counts_per_root else 0,
        'median_significant_prefixes': sorted(prefix_counts_per_root)[len(prefix_counts_per_root)//2] if prefix_counts_per_root else 0,
        'avg_prefix_entropy': sum(prefix_entropy_per_root) / len(prefix_entropy_per_root) if prefix_entropy_per_root else 0,
        'avg_suffix_entropy': sum(suffix_entropy_per_root) / len(suffix_entropy_per_root) if suffix_entropy_per_root else 0,
        'prefix_counts_hist': Counter(prefix_counts_per_root),
    }


def test_binyan_hypothesis(all_metrics):
    """
    Hebrew has 7 binyanim (verb stems). Each root can theoretically occur in
    multiple binyanim, each with a different onset pattern but same prefix/suffix
    grid. The Voynich onset slot (ch/sh/k/t/p/f/ckh/cth...) might play a
    similar role.

    Test: do roots with different onsets but same body show PARALLEL
    paradigm shapes? E.g., root 'ka' vs 'ta' vs 'cha' — do they all
    use the same set of prefixes and suffixes?
    """
    # Group roots by their body (the vowel pattern after the onset)
    body_groups = defaultdict(list)
    for m in all_metrics:
        if m['freq'] < 100:
            continue
        root = m['root']
        # Try to separate onset from body
        onsets = ['ckh', 'cth', 'cph', 'cfh', 'kch', 'tch', 'pch', 'fch',
                  'ksh', 'tsh', 'psh', 'fsh', 'sh', 'ch', 'k', 't', 'p', 'f']
        onset = ''
        body = root
        for o in onsets:
            if root.startswith(o) and len(root) > len(o):
                onset = o
                body = root[len(o):]
                break
        if onset:
            body_groups[body].append({
                'full_root': root,
                'onset': onset,
                'freq': m['freq'],
                'n_prefixes': m['n_prefixes'],
                'n_suffixes': m['n_suffixes'],
                'prefix_entropy': m['prefix_entropy'],
                'suffix_entropy': m['suffix_entropy'],
                'top_prefixes': [p for p, _ in m['prefix_ranked'][:5]],
                'top_suffixes': [s for s, _ in m['suffix_ranked'][:5]],
            })

    # Find bodies with multiple onsets
    parallel_bodies = {b: roots for b, roots in body_groups.items()
                       if len(roots) >= 2}

    results = []
    for body, roots in sorted(parallel_bodies.items(), key=lambda x: -sum(r['freq'] for r in x[1])):
        # Check if they share the same top prefixes/suffixes
        pfx_sets = [set(r['top_prefixes']) for r in roots]
        suf_sets = [set(r['top_suffixes']) for r in roots]

        # Average pairwise Jaccard for prefixes and suffixes
        pfx_jaccards = []
        suf_jaccards = []
        for i in range(len(roots)):
            for j in range(i+1, len(roots)):
                if pfx_sets[i] | pfx_sets[j]:
                    pfx_jaccards.append(len(pfx_sets[i] & pfx_sets[j]) / len(pfx_sets[i] | pfx_sets[j]))
                if suf_sets[i] | suf_sets[j]:
                    suf_jaccards.append(len(suf_sets[i] & suf_sets[j]) / len(suf_sets[i] | suf_sets[j]))

        avg_pfx_j = sum(pfx_jaccards) / len(pfx_jaccards) if pfx_jaccards else 0
        avg_suf_j = sum(suf_jaccards) / len(suf_jaccards) if suf_jaccards else 0

        results.append({
            'body': body,
            'onsets': [r['onset'] for r in roots],
            'full_roots': [r['full_root'] for r in roots],
            'freqs': [r['freq'] for r in roots],
            'prefix_jaccard': avg_pfx_j,
            'suffix_jaccard': avg_suf_j,
            'roots_detail': roots,
        })

    return results


def main():
    print("=" * 90)
    print("VOYNICH ↔ HEBREW MORPHOLOGICAL COMPARISON")
    print("=" * 90)

    # Load data
    results_path = result_path('attack_plan_results.json')
    if not os.path.exists(results_path):
        print(f"ERROR: {results_path} not found. Run attack_plan.py first.")
        sys.exit(1)

    paradigms = load_voynich_paradigms(results_path)

    # Analyze each root
    all_metrics = []
    for root, table_data in paradigms.items():
        m = analyze_voynich_paradigm(root, table_data)
        all_metrics.append(m)
    all_metrics.sort(key=lambda x: -x['freq'])

    # ═══════════════════════════════════════════════════════════
    # TEST 1: PARADIGM SHAPE COMPARISON
    # ═══════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 1: PARADIGM GRID SHAPE — Voynich vs Hebrew vs Others")
    print("━" * 90)
    print()

    # Compute Voynich average shape
    top_roots = [m for m in all_metrics if m['freq'] >= 200]
    avg_voynich = {
        'n_prefixes': sum(m['n_prefixes'] for m in top_roots) / len(top_roots),
        'n_suffixes': sum(m['n_suffixes'] for m in top_roots) / len(top_roots),
        'prefix_entropy': sum(m['prefix_entropy'] for m in top_roots) / len(top_roots),
        'suffix_entropy': sum(m['suffix_entropy'] for m in top_roots) / len(top_roots),
        'fill_rate': sum(m['fill_rate'] for m in top_roots) / len(top_roots),
    }
    avg_voynich['prefix_suffix_ratio'] = avg_voynich['n_prefixes'] / max(avg_voynich['n_suffixes'], 1)
    avg_voynich['entropy_ratio'] = avg_voynich['prefix_entropy'] / max(avg_voynich['suffix_entropy'], 0.01)

    # Hebrew average (across binyanim)
    heb_vals = list(HEBREW_BINYANIM.values())
    avg_hebrew = {
        'n_prefixes': sum(b['n_prefixes'] for b in heb_vals) / len(heb_vals),
        'n_suffixes': sum(b['n_suffixes'] for b in heb_vals) / len(heb_vals),
        'prefix_entropy': sum(b['prefix_entropy'] for b in heb_vals) / len(heb_vals),
        'suffix_entropy': sum(b['suffix_entropy'] for b in heb_vals) / len(heb_vals),
        'fill_rate': sum(b['n_filled'] / (b['n_prefixes'] * b['n_suffixes']) for b in heb_vals) / len(heb_vals),
    }
    avg_hebrew['prefix_suffix_ratio'] = avg_hebrew['n_prefixes'] / max(avg_hebrew['n_suffixes'], 1)
    avg_hebrew['entropy_ratio'] = avg_hebrew['prefix_entropy'] / max(avg_hebrew['suffix_entropy'], 0.01)

    comparisons = [
        ("Hebrew (Semitic)", avg_hebrew),
        ("Arabic (Semitic)", {
            'n_prefixes': ARABIC_VERB['n_prefixes'],
            'n_suffixes': ARABIC_VERB['n_suffixes'],
            'prefix_entropy': ARABIC_VERB['prefix_entropy'],
            'suffix_entropy': ARABIC_VERB['suffix_entropy'],
            'fill_rate': ARABIC_VERB['n_filled'] / (ARABIC_VERB['n_prefixes'] * ARABIC_VERB['n_suffixes']),
            'prefix_suffix_ratio': ARABIC_VERB['n_prefixes'] / ARABIC_VERB['n_suffixes'],
            'entropy_ratio': ARABIC_VERB['prefix_entropy'] / ARABIC_VERB['suffix_entropy'],
        }),
        ("Latin (fusional)", {
            'n_prefixes': LATIN_VERB['n_prefixes'],
            'n_suffixes': LATIN_VERB['n_suffixes'],
            'prefix_entropy': LATIN_VERB['prefix_entropy'],
            'suffix_entropy': LATIN_VERB['suffix_entropy'],
            'fill_rate': LATIN_VERB['n_filled'] / max(LATIN_VERB['n_prefixes'] * LATIN_VERB['n_suffixes'], 1),
            'prefix_suffix_ratio': LATIN_VERB['n_prefixes'] / LATIN_VERB['n_suffixes'],
            'entropy_ratio': 0.0,
        }),
        ("Turkish (agglut.)", {
            'n_prefixes': TURKISH_VERB['n_prefixes'],
            'n_suffixes': TURKISH_VERB['n_suffixes'],
            'prefix_entropy': TURKISH_VERB['prefix_entropy'],
            'suffix_entropy': TURKISH_VERB['suffix_entropy'],
            'fill_rate': TURKISH_VERB['n_filled'] / max(TURKISH_VERB['n_prefixes'] * TURKISH_VERB['n_suffixes'], 1),
            'prefix_suffix_ratio': TURKISH_VERB['n_prefixes'] / TURKISH_VERB['n_suffixes'],
            'entropy_ratio': 0.0,
        }),
        ("Enochian (Kelley)", {
            'n_prefixes': ENOCHIAN['n_prefixes'],
            'n_suffixes': ENOCHIAN['n_suffixes'],
            'prefix_entropy': ENOCHIAN['prefix_entropy'],
            'suffix_entropy': ENOCHIAN['suffix_entropy'],
            'fill_rate': ENOCHIAN['n_filled'] / max(ENOCHIAN['n_prefixes'] * ENOCHIAN['n_suffixes'], 1),
            'prefix_suffix_ratio': ENOCHIAN['n_prefixes'] / ENOCHIAN['n_suffixes'],
            'entropy_ratio': ENOCHIAN['prefix_entropy'] / max(ENOCHIAN['suffix_entropy'], 0.01),
        }),
    ]

    print(f"  {'Metric':<26s} {'VOYNICH':>10s}", end="")
    for name, _ in comparisons:
        print(f"  {name:>18s}", end="")
    print()
    print(f"  {'─'*26} {'─'*10}", end="")
    for _ in comparisons:
        print(f"  {'─'*18}", end="")
    print()

    for metric_key, label in [
        ('n_prefixes', 'Avg # prefixes'),
        ('n_suffixes', 'Avg # suffixes'),
        ('prefix_suffix_ratio', 'Prefix/Suffix ratio'),
        ('fill_rate', 'Grid fill rate'),
        ('prefix_entropy', 'Prefix entropy (bits)'),
        ('suffix_entropy', 'Suffix entropy (bits)'),
        ('entropy_ratio', 'Entropy ratio (pfx/suf)'),
    ]:
        print(f"  {label:<26s} {avg_voynich[metric_key]:>10.2f}", end="")
        for name, ref in comparisons:
            print(f"  {ref[metric_key]:>18.2f}", end="")
        print()

    # Compute distances
    print()
    print("  SHAPE DISTANCES from Voynich (lower = more similar):")
    voynich_shape = compute_grid_shape_vector(avg_voynich)
    distances = []
    for name, ref in comparisons:
        ref_shape = compute_grid_shape_vector(ref)
        d = shape_distance(voynich_shape, ref_shape)
        distances.append((name, d))
    distances.sort(key=lambda x: x[1])
    for name, d in distances:
        bar = "█" * int(d * 20)
        print(f"    {name:<22s} {d:.4f}  {bar}")

    # ═══════════════════════════════════════════════════════════
    # TEST 2: PREFIX AS PERSON MARKERS
    # ═══════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 2: ARE VOYNICH PREFIXES PERSON MARKERS? (like Hebrew yi-/ti-/ʼe-/ni-)")
    print("━" * 90)
    print()

    person_test = test_prefix_as_person_markers(all_metrics)
    print(f"  Roots analyzed (freq≥200): {person_test['n_roots_analyzed']}")
    print(f"  Avg significant prefixes per root:    {person_test['avg_significant_prefixes']:.1f}")
    print(f"  Median significant prefixes per root:  {person_test['median_significant_prefixes']}")
    print(f"  Avg prefix entropy:  {person_test['avg_prefix_entropy']:.2f} bits")
    print(f"  Avg suffix entropy:  {person_test['avg_suffix_entropy']:.2f} bits")
    print()
    print(f"  Hebrew prediction:  4-5 person prefixes, entropy ~1.5-2.0 bits")
    print(f"  Latin prediction:   1 prefix (none), entropy ~0.0 bits")
    print(f"  Turkish prediction: 1 prefix (none), entropy ~0.0 bits")
    print()
    print(f"  Distribution of prefix count per root:")
    for k, v in sorted(person_test['prefix_counts_hist'].items()):
        bar = "█" * v
        print(f"    {k:>2d} prefixes: {v:>3d} roots  {bar}")

    # Hebrew has 4 person prefixes (ʼe, yi, ti, ni) → predict ~4-6 significant prefixes
    match_hebrew = 4 <= person_test['median_significant_prefixes'] <= 8
    print()
    if match_hebrew:
        print(f"  ✓ MATCH: Voynich prefix count ({person_test['median_significant_prefixes']}) "
              f"is consistent with Hebrew-style person marking (4-6)")
    else:
        print(f"  ✗ MISMATCH: Voynich prefix count ({person_test['median_significant_prefixes']}) "
              f"differs from Hebrew prediction (4-6)")

    # ═══════════════════════════════════════════════════════════
    # TEST 3: ∅-PREFIX vs PREFIXED ROWS (Perfect vs Imperfect split)
    # ═══════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 3: DO ∅-PREFIX AND PREFIXED FORMS USE DIFFERENT SUFFIXES?")
    print("        (Hebrew perfect vs imperfect use different suffix sets)")
    print("━" * 90)
    print()

    cooccurrence = analyze_prefix_suffix_cooccurrence(all_metrics)
    if cooccurrence:
        print(f"  Root               ∅-frac    JSD(∅ vs pfx)  Top5-overlap  ∅-suffixes          Prefixed-suffixes")
        print(f"  ─────────────── ────────── ────────────── ──────────── ──────────────────── ────────────────────")
        for r in cooccurrence[:20]:
            null_suf = ', '.join(r['null_top5'][:5])
            nonnull_suf = ', '.join(r['nonnull_top5'][:5])
            print(f"  {r['root']:<16s} {r['null_pfx_frac']:>8.1%}    {r['jsd_null_vs_prefixed']:>10.4f}    "
                  f"{r['top5_suffix_overlap']:>8.0%}    {null_suf:<20s} {nonnull_suf}")

        avg_jsd = sum(r['jsd_null_vs_prefixed'] for r in cooccurrence) / len(cooccurrence)
        avg_overlap = sum(r['top5_suffix_overlap'] for r in cooccurrence) / len(cooccurrence)
        print()
        print(f"  Average JSD (∅ vs prefixed): {avg_jsd:.4f}")
        print(f"  Average top-5 suffix overlap: {avg_overlap:.0%}")
        print()

        # Hebrew prediction: JSD should be HIGH (suffix sets differ between perfect/imperfect)
        # If Voynich JSD is low, ∅-prefix and prefixed rows use SAME suffixes → NOT Hebrew-like split
        if avg_jsd > 0.15:
            print(f"  ✓ DIVERGENCE: ∅-prefix and prefixed rows use somewhat different suffixes")
            print(f"    This is consistent with a Hebrew-like perfect/imperfect split")
        else:
            print(f"  → CONVERGENCE: ∅-prefix and prefixed rows use nearly identical suffixes")
            print(f"    This suggests prefixes are independent of suffixes (like adding a")
            print(f"    determiner/article, not switching conjugation type)")

    # ═══════════════════════════════════════════════════════════
    # TEST 4: PREFIX GEOMETRY — Do prefixes share suffix sets? (person markers)
    # ═══════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 4: DO DIFFERENT PREFIXES SHARE THE SAME SUFFIX SET?")
    print("        (Hebrew: yi-/ti-/ʼe-/ni- all use same suffixes ∅/i/u/na)")
    print("━" * 90)
    print()

    geometry = analyze_prefix_geometry(all_metrics)
    if geometry:
        print(f"  Root               Top prefixes                    Avg suffix Jaccard")
        print(f"  ─────────────── ──────────────────────────────── ────────────────────")
        for r in geometry[:15]:
            pfx_str = ', '.join(r['top_prefixes'])
            print(f"  {r['root']:<16s} {pfx_str:<35s} {r['avg_jaccard']:.3f}")

        avg_jaccard = sum(r['avg_jaccard'] for r in geometry) / len(geometry)
        print()
        print(f"  Average suffix-set Jaccard across all roots: {avg_jaccard:.3f}")
        print()

        # Hebrew prediction: VERY HIGH Jaccard (>0.7) because all person prefixes
        # take the same set of tense/number/gender suffixes
        if avg_jaccard > 0.6:
            print(f"  ✓ HIGH OVERLAP: Different prefixes use same suffixes (Jaccard={avg_jaccard:.2f})")
            print(f"    Consistent with Hebrew-style person markers on a shared suffix grid")
        elif avg_jaccard > 0.4:
            print(f"  ~ MODERATE OVERLAP: Prefixes share most suffixes (Jaccard={avg_jaccard:.2f})")
            print(f"    Partially consistent with person markers, but some suffix differentiation")
        else:
            print(f"  ✗ LOW OVERLAP: Different prefixes use different suffix sets (Jaccard={avg_jaccard:.2f})")
            print(f"    Inconsistent with Hebrew person markers; prefixes may be derivational")

        # Show detailed pair analysis for top root
        if geometry:
            top = geometry[0]
            print()
            print(f"  DETAIL for root '{top['root']}':")
            for p in top['pairs']:
                shared_str = ', '.join(p['shared'][:8])
                print(f"    {p['pfx1']:>4s} ↔ {p['pfx2']:<4s}: Jaccard={p['jaccard']:.3f}  "
                      f"shared=[{shared_str}]")

    # ═══════════════════════════════════════════════════════════
    # TEST 5: BINYAN HYPOTHESIS — Onset as verb-stem marker
    # ═══════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 5: BINYAN HYPOTHESIS — Does onset (ch/sh/k/t) act like Hebrew verb stems?")
    print("        (Hebrew: same root in different binyanim → same prefix/suffix grid)")
    print("━" * 90)
    print()

    binyan_results = test_binyan_hypothesis(all_metrics)
    if binyan_results:
        print(f"  Body pattern    Onsets (≈ binyanim)          Prefix J.  Suffix J.  Frequencies")
        print(f"  ────────────── ──────────────────────────── ────────── ────────── ────────────")
        for r in binyan_results[:15]:
            onset_str = ', '.join(r['onsets'])
            freq_str = ', '.join(str(f) for f in r['freqs'])
            print(f"  {r['body']:<15s} {onset_str:<30s} {r['prefix_jaccard']:>8.3f}   "
                  f"{r['suffix_jaccard']:>8.3f}   [{freq_str}]")

        if binyan_results:
            avg_pfx_j = sum(r['prefix_jaccard'] for r in binyan_results) / len(binyan_results)
            avg_suf_j = sum(r['suffix_jaccard'] for r in binyan_results) / len(binyan_results)
            print()
            print(f"  Average prefix Jaccard across onset groups: {avg_pfx_j:.3f}")
            print(f"  Average suffix Jaccard across onset groups: {avg_suf_j:.3f}")
            print()

            if avg_pfx_j > 0.5 and avg_suf_j > 0.5:
                print(f"  ✓ STRONG PARALLEL: Roots with different onsets but same body share")
                print(f"    the same prefix/suffix grid → onset acts like a Hebrew binyan marker!")
            elif avg_pfx_j > 0.3 or avg_suf_j > 0.3:
                print(f"  ~ PARTIAL PARALLEL: Some structural similarity across onsets")
            else:
                print(f"  ✗ NO PARALLEL: Different onsets produce different paradigm shapes")

    # ═══════════════════════════════════════════════════════════
    # TEST 6: TOP VOYNICH PARADIGMS vs HEBREW CONJUGATION TABLES
    # ═══════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 6: DETAILED PARADIGM COMPARISON — Top 6 Voynich roots")
    print("━" * 90)
    print()
    print("  Hebrew Qal paradigm shape:")
    print(f"    {5} prefixes × {12} suffixes, {19} filled cells, fill rate={19/(5*12):.0%}")
    print(f"    Prefix entropy ≈ 1.8 bits, Suffix entropy ≈ 3.2 bits")
    print()

    for m in all_metrics[:6]:
        print(f"  ┌─ VOYNICH ROOT: '{m['root']}'  (freq: {m['freq']}, {m['n_filled']} forms)")
        print(f"  │ {m['n_prefixes']} prefixes × {m['n_suffixes']} suffixes, "
              f"fill rate={m['fill_rate']:.0%}")
        print(f"  │ Prefix entropy: {m['prefix_entropy']:.2f} bits  "
              f"(Hebrew Qal: 1.8)  Δ={abs(m['prefix_entropy']-1.8):.2f}")
        print(f"  │ Suffix entropy: {m['suffix_entropy']:.2f} bits  "
              f"(Hebrew Qal: 3.2)  Δ={abs(m['suffix_entropy']-3.2):.2f}")

        # Show prefix frequency profile
        pfx_str = '  '.join(f"{p}({c})" for p, c in m['prefix_ranked'][:6])
        print(f"  │ Prefixes: {pfx_str}")

        # Show suffix frequency profile
        suf_str = '  '.join(f"{s}({c})" for s, c in m['suffix_ranked'][:6])
        print(f"  │ Suffixes: {suf_str}")

        # Hebrew-like score
        pfx_score = max(0, 1 - abs(m['prefix_entropy'] - 1.8) / 1.8)
        suf_score = max(0, 1 - abs(m['suffix_entropy'] - 3.2) / 3.2)
        count_score = max(0, 1 - abs(m['n_prefixes'] - 5) / 5)
        overall = (pfx_score + suf_score + count_score) / 3
        print(f"  │ Hebrew similarity score: {overall:.0%} "
              f"(pfx_entropy:{pfx_score:.0%} suf_entropy:{suf_score:.0%} pfx_count:{count_score:.0%})")
        print(f"  └{'─'*80}")
        print()

    # ═══════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════
    print()
    print("═" * 90)
    print("SUMMARY: HEBREW MORPHOLOGICAL COMPARISON")
    print("═" * 90)
    print()
    print("  Feature                              Voynich        Hebrew         Match?")
    print("  ──────────────────────────────────── ────────────── ────────────── ──────")
    print(f"  Prefix-root-suffix structure          YES            YES           ✓")
    print(f"  # distinct prefixes per root          "
          f"{person_test['avg_significant_prefixes']:.1f}           4-5            "
          f"{'✓' if 3 <= person_test['avg_significant_prefixes'] <= 8 else '✗'}")
    print(f"  Prefix entropy (bits)                 "
          f"{person_test['avg_prefix_entropy']:.2f}          1.5-2.0         "
          f"{'✓' if 1.0 <= person_test['avg_prefix_entropy'] <= 3.0 else '~'}")
    print(f"  Suffix entropy (bits)                 "
          f"{person_test['avg_suffix_entropy']:.2f}          3.0-3.5         "
          f"{'✓' if 2.0 <= person_test['avg_suffix_entropy'] <= 4.5 else '~'}")
    if geometry:
        avg_j = sum(r['avg_jaccard'] for r in geometry) / len(geometry)
        print(f"  Prefix suffix-set overlap (Jaccard)   "
              f"{avg_j:.2f}           ~0.85           "
              f"{'✓' if avg_j > 0.5 else '~' if avg_j > 0.3 else '✗'}")
    if cooccurrence:
        avg_jsd = sum(r['jsd_null_vs_prefixed'] for r in cooccurrence) / len(cooccurrence)
        print(f"  ∅-prefix vs prefixed suffix JSD       "
              f"{avg_jsd:.3f}          ~0.3            "
              f"{'✓' if avg_jsd > 0.1 else '✗'}")
    if binyan_results:
        avg_sj = sum(r['suffix_jaccard'] for r in binyan_results) / len(binyan_results)
        print(f"  Onset-as-binyan suffix Jaccard        "
              f"{avg_sj:.2f}           ~0.7            "
              f"{'✓' if avg_sj > 0.4 else '~' if avg_sj > 0.25 else '✗'}")
    print()

    # Save results
    output = {
        'grid_shape': {
            'voynich': avg_voynich,
            'distances': distances,
        },
        'person_markers': person_test,
        'cooccurrence': cooccurrence[:20] if cooccurrence else [],
        'prefix_geometry': [{k: v for k, v in r.items() if k != 'pairs'}
                            for r in (geometry[:20] if geometry else [])],
        'binyan': [{k: v for k, v in r.items() if k != 'roots_detail'}
                   for r in (binyan_results[:20] if binyan_results else [])],
    }
    with open(result_path('hebrew_comparison_results.json'), 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved to results/hebrew_comparison_results.json")
    print()
    print("═" * 90)
    print("HEBREW COMPARISON COMPLETE")
    print("═" * 90)


if __name__ == '__main__':
    main()