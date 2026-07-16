#!/usr/bin/env python3
"""
CURRIER A/B INDEPENDENT FINGERPRINT ANALYSIS

═══════════════════════════════════════════════════════════════════════

CRITICAL METHODOLOGICAL QUESTION:
  We have been treating the VMS as a monolithic corpus with target:
    h_char=0.641, Heaps=0.753, hapax=0.656, wlen=4.94, Zipf=0.942, TTR=0.342

  But Currier identified TWO distinct "languages" (A and B) in the VMS.
  spectral_vowel_consonant confirmed their gallows rates differ (z=3.70) and 'o' rates
  differ (z=9.52).

  IF A and B are genuinely different encoding systems, then our whole-corpus
  fingerprint is an AVERAGE of two different things. Every experiment that
  tried to match this average was chasing a chimera.

WHAT THIS TESTS:
  1. Full 6D fingerprint for Currier A (folios 1-57) independently
  2. Full 6D fingerprint for Currier B (folios 75-116) independently
  3. Are A and B significantly different on each dimension?
  4. Is EITHER section closer to natural language than the mixture?
  5. Does the h_char anomaly persist within each section, or is it
     a MIXING artifact?
  6. Bootstrap confidence intervals (A is ~10K words, B is ~26K, size matters)

MIXING THEORY:
  If you mix two streams with different bigram distributions:
    - H(c|prev) increases (less predictability from mixed stats)
    - So h_char = H(c|prev)/H(c) could go UP
  This means: if split sections have HIGHER h_char → mixing HURT the ratio
              if split sections have LOWER h_char → the anomaly is intrinsic

CONTROLS:
  - Random 50/50 split of whole corpus → if this matches A/B split in effect
    size, the A/B distinction is just a sample-size artifact
  - Subsample B down to A's size → controls for corpus-size effects on metrics

═══════════════════════════════════════════════════════════════════════
"""

import re, sys, io, math, json, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import char_bigram_predictability, clean_word, eva_to_glyphs, extract_words_from_line, hapax_ratio_at_midpoint, index_of_coincidence, mean_word_length, ttr_at_n

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
# EVA PARSING (from spectral_vowel_consonant)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']





# ═══════════════════════════════════════════════════════════════════════
# PARSE VMS WITH FOLIO-LEVEL RESOLUTION
# ═══════════════════════════════════════════════════════════════════════

# Currier sections — traditional assignment
# A: Herbal-A pages (roughly folios 1-57)
# B: Herbal-B, Biological, Cosmological, Pharmaceutical, Stars (roughly 58+)
# We use the standard Currier assignment via folio number ranges.
# Folios 58-74 are sometimes considered transitional — we test them separately.

SECTION_A = set(range(1, 58))
SECTION_B = set(range(75, 117))
SECTION_MID = set(range(58, 75))  # transitional folios

def parse_vms_by_section():
    """Parse VMS returning words per section with folio tracking."""
    section_words = {'A': [], 'B': [], 'MID': [], 'ALL': []}
    folio_section_map = {}

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)

    for filepath in folio_files:
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num: continue
        folio_num = int(m_num.group(1))

        if folio_num in SECTION_A:
            sec = 'A'
        elif folio_num in SECTION_B:
            sec = 'B'
        elif folio_num in SECTION_MID:
            sec = 'MID'
        else:
            sec = 'B'  # high-numbered folios default to B

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line: continue
                m = re.match(r'<([^>]+)>', line)
                if not m: continue
                rest = line[m.end():].strip()
                if not rest: continue
                words = extract_words_from_line(rest)
                section_words[sec].extend(words)
                section_words['ALL'].extend(words)

        folio_section_map[folio_num] = sec

    return section_words, folio_section_map


# ═══════════════════════════════════════════════════════════════════════
# FINGERPRINT BATTERY (from spectral_vowel_consonant/81)
# ═══════════════════════════════════════════════════════════════════════

def heaps_exponent(words):
    n = len(words)
    if n < 100: return float('nan')
    sample_points = np.linspace(100, n, 20, dtype=int)
    vocab_at = {}
    running = set()
    idx = 0
    for pt in sorted(sample_points):
        while idx < pt:
            running.add(words[idx]); idx += 1
        vocab_at[pt] = len(running)
    log_n = np.array([math.log(pt) for pt in sample_points])
    log_v = np.array([math.log(vocab_at[pt]) for pt in sample_points])
    A = np.vstack([log_n, np.ones(len(log_n))]).T
    result = np.linalg.lstsq(A, log_v, rcond=None)
    return float(result[0][0])





def zipf_alpha(words):
    freq = Counter(words)
    ranked = sorted(freq.values(), reverse=True)
    n = min(len(ranked), 500)
    if n < 10: return float('nan')
    log_rank = np.log(np.arange(1, n+1))
    log_freq = np.log(np.array(ranked[:n], dtype=float))
    A = np.vstack([log_rank, np.ones(n)]).T
    result = np.linalg.lstsq(A, log_freq, rcond=None)
    return float(-result[0][0])


def compute_fingerprint(words, label):
    """Compute full fingerprint from word list."""
    char_list = []
    for w in words:
        char_list.extend(eva_to_glyphs(w))
    return {
        'label': label,
        'n_tokens': len(words),
        'n_types': len(set(words)),
        'alphabet_size': len(set(char_list)),
        'heaps_beta': heaps_exponent(words),
        'hapax_ratio_mid': hapax_ratio_at_midpoint(words),
        'h_char_ratio': char_bigram_predictability(char_list),
        'mean_word_len': mean_word_length(words),
        'ttr_5000': ttr_at_n(words, 5000),
        'zipf_alpha': zipf_alpha(words),
        'ic': index_of_coincidence(char_list),
    }

VMS_TARGET = {
    'h_char_ratio': 0.641,
    'heaps_beta': 0.753,
    'hapax_ratio_mid': 0.656,
    'mean_word_len': 4.94,
    'zipf_alpha': 0.942,
    'ttr_5000': 0.342,
}

DIMS = ['h_char_ratio', 'heaps_beta', 'hapax_ratio_mid',
        'mean_word_len', 'zipf_alpha', 'ttr_5000']

def fingerprint_distance(fp, target=VMS_TARGET):
    dims = []
    for key, vms_val in target.items():
        if key in fp and vms_val != 0 and not math.isnan(fp.get(key, float('nan'))):
            dims.append(((fp[key] - vms_val) / vms_val) ** 2)
    return math.sqrt(sum(dims)) if dims else float('inf')


# ═══════════════════════════════════════════════════════════════════════
# BOOTSTRAP CONFIDENCE INTERVALS
# ═══════════════════════════════════════════════════════════════════════

def bootstrap_fingerprint(words, n_bootstrap=200, sample_size=None):
    """Bootstrap CI for each fingerprint dimension.
    If sample_size is given, subsample to that size each iteration."""
    if sample_size is None:
        sample_size = len(words)

    boot_results = {dim: [] for dim in DIMS}

    for _ in range(n_bootstrap):
        # Sample with replacement
        indices = np.random.randint(0, len(words), size=sample_size)
        sample = [words[i] for i in indices]
        fp = compute_fingerprint(sample, 'boot')
        for dim in DIMS:
            val = fp[dim]
            if not math.isnan(val):
                boot_results[dim].append(val)

    ci = {}
    for dim in DIMS:
        vals = sorted(boot_results[dim])
        if len(vals) >= 10:
            lo = vals[int(0.025 * len(vals))]
            hi = vals[int(0.975 * len(vals))]
            mean = np.mean(vals)
            ci[dim] = {'mean': mean, 'lo_95': lo, 'hi_95': hi, 'std': np.std(vals)}
        else:
            ci[dim] = {'mean': float('nan'), 'lo_95': float('nan'),
                       'hi_95': float('nan'), 'std': float('nan')}
    return ci


def bootstrap_overlap_test(words_a, words_b, n_bootstrap=200):
    """Test whether A and B differ significantly on each dimension
    by checking bootstrap CI overlap."""
    ci_a = bootstrap_fingerprint(words_a, n_bootstrap)
    ci_b = bootstrap_fingerprint(words_b, n_bootstrap)

    results = {}
    for dim in DIMS:
        a = ci_a[dim]
        b = ci_b[dim]
        overlap = min(a['hi_95'], b['hi_95']) - max(a['lo_95'], b['lo_95'])
        span_a = a['hi_95'] - a['lo_95']
        span_b = b['hi_95'] - b['lo_95']
        # Cohen's d (approximate)
        pooled_std = math.sqrt((a['std']**2 + b['std']**2) / 2) if a['std'] > 0 and b['std'] > 0 else 0.001
        cohens_d = abs(a['mean'] - b['mean']) / pooled_std
        results[dim] = {
            'a_mean': a['mean'], 'a_lo': a['lo_95'], 'a_hi': a['hi_95'],
            'b_mean': b['mean'], 'b_lo': b['lo_95'], 'b_hi': b['hi_95'],
            'overlap': overlap > 0,
            'cohens_d': cohens_d,
            'significant': overlap <= 0,  # Non-overlapping CIs → p < ~0.01
        }
    return results


# ═══════════════════════════════════════════════════════════════════════
# TOP VOCABULARY COMPARISON
# ═══════════════════════════════════════════════════════════════════════

def vocab_comparison(words_a, words_b):
    """Compare vocabulary overlap and distinctive words."""
    types_a = set(words_a)
    types_b = set(words_b)
    shared = types_a & types_b
    only_a = types_a - types_b
    only_b = types_b - types_a

    freq_a = Counter(words_a)
    freq_b = Counter(words_b)

    pr(f"\n  VOCABULARY COMPARISON:")
    pr(f"    Types in A: {len(types_a):,}")
    pr(f"    Types in B: {len(types_b):,}")
    pr(f"    Shared:     {len(shared):,} ({100*len(shared)/len(types_a|types_b):.1f}% of union)")
    pr(f"    Only in A:  {len(only_a):,}")
    pr(f"    Only in B:  {len(only_b):,}")

    # Jaccard similarity
    jaccard = len(shared) / max(len(types_a | types_b), 1)
    pr(f"    Jaccard similarity: {jaccard:.4f}")

    # Most distinctive words (high frequency in one, absent/rare in other)
    pr(f"\n    Top 15 words distinctive to A (freq_A >> freq_B):")
    a_ratio = []
    for w in types_a:
        fa = freq_a[w] / len(words_a)
        fb = freq_b.get(w, 0) / len(words_b)
        if fa > 0.001:  # at least somewhat common in A
            ratio = fa / max(fb, 1e-7)
            a_ratio.append((w, freq_a[w], freq_b.get(w, 0), ratio))
    a_ratio.sort(key=lambda x: -x[3])
    for w, fa, fb, ratio in a_ratio[:15]:
        pr(f"      {w:<16} A:{fa:>5} B:{fb:>5} ratio:{ratio:>.1f}x")

    pr(f"\n    Top 15 words distinctive to B (freq_B >> freq_A):")
    b_ratio = []
    for w in types_b:
        fb = freq_b[w] / len(words_b)
        fa = freq_a.get(w, 0) / len(words_a)
        if fb > 0.001:
            ratio = fb / max(fa, 1e-7)
            b_ratio.append((w, freq_a.get(w, 0), freq_b[w], ratio))
    b_ratio.sort(key=lambda x: -x[3])
    for w, fa, fb, ratio in b_ratio[:15]:
        pr(f"      {w:<16} A:{fa:>5} B:{fb:>5} ratio:{ratio:>.1f}x")

    return jaccard


# ═══════════════════════════════════════════════════════════════════════
# CHARACTER-LEVEL DISTRIBUTION COMPARISON
# ═══════════════════════════════════════════════════════════════════════

def char_distribution_comparison(words_a, words_b):
    """Compare glyph frequency distributions between A and B."""
    glyphs_a = []
    for w in words_a:
        glyphs_a.extend(eva_to_glyphs(w))
    glyphs_b = []
    for w in words_b:
        glyphs_b.extend(eva_to_glyphs(w))

    freq_a = Counter(glyphs_a)
    freq_b = Counter(glyphs_b)
    all_glyphs = sorted(set(freq_a) | set(freq_b),
                        key=lambda g: -(freq_a[g] + freq_b[g]))

    total_a = len(glyphs_a)
    total_b = len(glyphs_b)

    pr(f"\n  GLYPH FREQUENCY COMPARISON (top 20):")
    pr(f"    {'Glyph':<6} {'A_pct':>7} {'B_pct':>7} {'Delta':>7} {'Note'}")
    pr(f"    {'─'*6} {'─'*7} {'─'*7} {'─'*7} {'─'*20}")

    significant_diffs = []
    for g in all_glyphs[:20]:
        pa = freq_a[g] / total_a if total_a > 0 else 0
        pb = freq_b[g] / total_b if total_b > 0 else 0
        delta = pb - pa

        # z-test for proportion difference
        p_pool = (freq_a[g] + freq_b[g]) / (total_a + total_b)
        se = math.sqrt(p_pool * (1-p_pool) * (1/total_a + 1/total_b)) if p_pool > 0 and p_pool < 1 else 0.001
        z = (pa - pb) / se if se > 0 else 0

        note = ''
        if abs(z) > 3.0:
            note = f'z={z:+.1f} ***'
            significant_diffs.append((g, pa, pb, z))
        elif abs(z) > 2.0:
            note = f'z={z:+.1f} **'

        pr(f"    {g:<6} {100*pa:>6.2f}% {100*pb:>6.2f}% {100*delta:>+6.2f}% {note}")

    return significant_diffs


# ═══════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 72)
    pr("  currier_split_fingerprint — CURRIER A/B INDEPENDENT FINGERPRINT ANALYSIS")
    pr("=" * 72)
    pr("  Question: Is VMS_TARGET a valid monolithic baseline, or are")
    pr("  we averaging two different systems?")
    pr("=" * 72)

    # ── 1. Parse VMS by section ───────────────────────────────────────
    pr("\n▸ Parsing VMS corpus by Currier section...")
    section_words, folio_map = parse_vms_by_section()

    for sec in ['A', 'B', 'MID', 'ALL']:
        n = len(section_words[sec])
        t = len(set(section_words[sec]))
        if n > 0:
            pr(f"  {sec:>4}: {n:>8,} tokens, {t:>6,} types")

    # ── 2. Full fingerprints ──────────────────────────────────────────
    pr("\n" + "=" * 72)
    pr("  FULL FINGERPRINT COMPARISON")
    pr("=" * 72)

    fps = {}
    for sec in ['ALL', 'A', 'B', 'MID']:
        if len(section_words[sec]) < 500:
            pr(f"\n  {sec}: too few words ({len(section_words[sec])}), skipping")
            continue
        fp = compute_fingerprint(section_words[sec], f'VMS_{sec}')
        fps[sec] = fp

    # Print comparison table
    pr(f"\n  {'Section':<14}", end='')
    headers = ['h_char', 'Heaps', 'hapax', 'wlen', 'Zipf', 'TTR', 'Types', 'Tokens']
    for h in headers:
        pr(f" {h:>8}", end='')
    pr()
    pr(f"  {'─'*14}", end='')
    for _ in headers:
        pr(f" {'─'*8}", end='')
    pr()

    # VMS Target row
    pr(f"  {'VMS_TARGET':<14}", end='')
    for d in DIMS:
        pr(f" {VMS_TARGET[d]:>8.4f}", end='')
    pr(f" {'─':>8} {'─':>8}")

    # NL range row
    pr(f"  {'NL_range':<14}", end='')
    nl = {'h_char_ratio': '.82-.90', 'heaps_beta': '.60-.80',
          'hapax_ratio_mid': '.50-.70', 'mean_word_len': ' 4.0-6.0',
          'zipf_alpha': '.90-1.10', 'ttr_5000': '.30-.50'}
    for d in DIMS:
        pr(f" {nl[d]:>8}", end='')
    pr()

    for sec in ['ALL', 'A', 'B', 'MID']:
        if sec not in fps: continue
        fp = fps[sec]
        dist = fingerprint_distance(fp)
        pr(f"  {'VMS_'+sec:<14}", end='')
        for d in DIMS:
            val = fp[d]
            pr(f" {val:>8.4f}", end='')
        pr(f" {fp['n_types']:>8,} {fp['n_tokens']:>8,}")
        pr(f"  {'':14} Distance to VMS_TARGET: {dist:.4f}")

    # ── 3. Key question: Does h_char split? ───────────────────────────
    pr("\n" + "=" * 72)
    pr("  KEY QUESTION: h_char ANOMALY — MIXING ARTIFACT OR INTRINSIC?")
    pr("=" * 72)

    if 'A' in fps and 'B' in fps:
        h_all = fps['ALL']['h_char_ratio']
        h_a = fps['A']['h_char_ratio']
        h_b = fps['B']['h_char_ratio']

        pr(f"\n  h_char(ALL)      = {h_all:.4f}")
        pr(f"  h_char(A)        = {h_a:.4f}")
        pr(f"  h_char(B)        = {h_b:.4f}")
        pr(f"  h_char(NL range) = 0.82 — 0.90")
        pr(f"\n  Gap ALL→NL:  {0.82 - h_all:.4f}")
        pr(f"  Gap A→NL:    {0.82 - h_a:.4f}")
        pr(f"  Gap B→NL:    {0.82 - h_b:.4f}")

        if h_a > h_all + 0.01 and h_b > h_all + 0.01:
            pr(f"\n  ⚠ BOTH sections have HIGHER h_char than the mixture!")
            pr(f"    → Mixing IS depressing h_char. The anomaly is PARTIALLY artificial.")
        elif abs(h_a - h_all) < 0.01 and abs(h_b - h_all) < 0.01:
            pr(f"\n  Both sections have h_char ≈ mixture.")
            pr(f"    → The anomaly is INTRINSIC to the encoding system, not a mixing artifact.")
        else:
            pr(f"\n  Mixed result: one section differs from mixture.")

        # How much of the gap does splitting close?
        avg_split_h = (h_a * len(section_words['A']) + h_b * len(section_words['B'])) / \
                      (len(section_words['A']) + len(section_words['B']))
        gap_closed = (avg_split_h - h_all) / (0.86 - h_all) * 100  # 0.86 = NL midpoint
        pr(f"\n  Weighted average of split h_chars: {avg_split_h:.4f}")
        pr(f"  Gap closed by splitting: {gap_closed:.1f}% of distance to NL midpoint")

    # ── 4. Bootstrap significance test ────────────────────────────────
    pr("\n" + "=" * 72)
    pr("  BOOTSTRAP SIGNIFICANCE: A vs B DIFFERENCES")
    pr("=" * 72)

    if 'A' in fps and 'B' in fps:
        pr("\n  Running 200-iteration bootstrap (this may take a moment)...")
        overlap_results = bootstrap_overlap_test(
            section_words['A'], section_words['B'], n_bootstrap=200
        )

        pr(f"\n  {'Dimension':<18} {'A_mean':>8} {'A_95CI':>16} {'B_mean':>8} "
           f"{'B_95CI':>16} {'Cohen_d':>8} {'Sig?':>6}")
        pr(f"  {'─'*18} {'─'*8} {'─'*16} {'─'*8} {'─'*16} {'─'*8} {'─'*6}")

        sig_count = 0
        for dim in DIMS:
            r = overlap_results[dim]
            a_ci = f"[{r['a_lo']:.4f},{r['a_hi']:.4f}]"
            b_ci = f"[{r['b_lo']:.4f},{r['b_hi']:.4f}]"
            sig = '***' if r['significant'] else ('*' if r['cohens_d'] > 0.5 else '')
            if r['significant']:
                sig_count += 1
            pr(f"  {dim:<18} {r['a_mean']:>8.4f} {a_ci:>16} {r['b_mean']:>8.4f} "
               f"{b_ci:>16} {r['cohens_d']:>8.2f} {sig:>6}")

        pr(f"\n  Significant differences (non-overlapping 95% CI): {sig_count}/{len(DIMS)}")
        if sig_count >= 4:
            pr(f"  → A and B are COMPREHENSIVELY different — treating VMS as monolith is WRONG")
        elif sig_count >= 2:
            pr(f"  → A and B differ on some dimensions — partial chimera effect")
        else:
            pr(f"  → A and B are similar — monolithic treatment is justified")

    # ── 5. Control: Random split ──────────────────────────────────────
    pr("\n" + "=" * 72)
    pr("  CONTROL: RANDOM 50/50 SPLIT (same corpus, no structural divide)")
    pr("=" * 72)

    all_w = section_words['ALL'][:]
    random.shuffle(all_w)
    half = len(all_w) // 2
    rand_a = all_w[:half]
    rand_b = all_w[half:]

    fp_ra = compute_fingerprint(rand_a, 'Random_A')
    fp_rb = compute_fingerprint(rand_b, 'Random_B')

    pr(f"\n  {'Split':<14}", end='')
    for h in ['h_char', 'Heaps', 'hapax', 'wlen', 'Zipf', 'TTR']:
        pr(f" {h:>8}", end='')
    pr()
    pr(f"  {'─'*14}", end='')
    for _ in range(6):
        pr(f" {'─'*8}", end='')
    pr()

    for label, fp in [('Random_A', fp_ra), ('Random_B', fp_rb)]:
        pr(f"  {label:<14}", end='')
        for d in DIMS:
            pr(f" {fp[d]:>8.4f}", end='')
        pr()

    # Max difference in random split
    max_rand_diff = max(abs(fp_ra[d] - fp_rb[d]) for d in DIMS)
    max_ab_diff = max(abs(fps['A'][d] - fps['B'][d]) for d in DIMS) if 'A' in fps and 'B' in fps else 0

    pr(f"\n  Max dimension difference — Random split: {max_rand_diff:.4f}")
    pr(f"  Max dimension difference — Currier A/B:  {max_ab_diff:.4f}")
    pr(f"  Ratio: Currier is {max_ab_diff/max(max_rand_diff, 0.0001):.1f}x larger than random")

    if max_ab_diff > 3 * max_rand_diff:
        pr(f"  → Currier A/B difference is FAR beyond sampling noise")
    elif max_ab_diff > 1.5 * max_rand_diff:
        pr(f"  → Currier A/B difference is moderately beyond sampling noise")
    else:
        pr(f"  → Currier A/B difference is comparable to sampling noise!")

    # ── 6. Control: Subsample B to A's size ───────────────────────────
    pr("\n" + "=" * 72)
    pr("  CONTROL: SUBSAMPLE B TO A's SIZE (corpus-size effect check)")
    pr("=" * 72)

    n_a = len(section_words['A'])
    if len(section_words['B']) > n_a:
        # Multiple subsamples
        pr(f"  Subsampling B ({len(section_words['B']):,} words) to A's size ({n_a:,})...")
        sub_fps = []
        for trial in range(10):
            indices = np.random.randint(0, len(section_words['B']), size=n_a)
            subsample = [section_words['B'][i] for i in indices]
            sub_fp = compute_fingerprint(subsample, f'B_sub_{trial}')
            sub_fps.append(sub_fp)

        pr(f"\n  B subsampled to {n_a:,} words (10 trials):")
        pr(f"  {'Dimension':<18} {'A':>8} {'B_full':>8} {'B_sub_mean':>10} {'B_sub_std':>10}")
        pr(f"  {'─'*18} {'─'*8} {'─'*8} {'─'*10} {'─'*10}")

        for d in DIMS:
            a_val = fps['A'][d]
            b_val = fps['B'][d]
            sub_vals = [fp[d] for fp in sub_fps]
            sub_mean = np.mean(sub_vals)
            sub_std = np.std(sub_vals)
            pr(f"  {d:<18} {a_val:>8.4f} {b_val:>8.4f} {sub_mean:>10.4f} {sub_std:>10.4f}")

        pr(f"\n  If B_sub ≈ B_full → size doesn't explain differences")
        pr(f"  If B_sub ≈ A → the 'difference' was a sample-size artifact")

    # ── 7. Vocabulary overlap ─────────────────────────────────────────
    pr("\n" + "=" * 72)
    pr("  VOCABULARY ANALYSIS")
    pr("=" * 72)

    if section_words['A'] and section_words['B']:
        jaccard = vocab_comparison(section_words['A'], section_words['B'])

    # ── 8. Glyph distribution ─────────────────────────────────────────
    pr("\n" + "=" * 72)
    pr("  GLYPH DISTRIBUTION COMPARISON")
    pr("=" * 72)

    if section_words['A'] and section_words['B']:
        sig_diffs = char_distribution_comparison(section_words['A'], section_words['B'])

    # ═══════════════════════════════════════════════════════════════════
    # CRITICAL VERDICT
    # ═══════════════════════════════════════════════════════════════════

    pr("\n" + "=" * 72)
    pr("  CRITICAL VERDICT")
    pr("=" * 72)

    if 'A' in fps and 'B' in fps:
        h_a = fps['A']['h_char_ratio']
        h_b = fps['B']['h_char_ratio']
        h_all = fps['ALL']['h_char_ratio']

        pr(f"\n  1. h_char ANOMALY:")
        pr(f"     Full corpus:  {h_all:.4f} (gap to NL min: {0.82 - h_all:.4f})")
        pr(f"     Currier A:    {h_a:.4f} (gap to NL min: {0.82 - h_a:.4f})")
        pr(f"     Currier B:    {h_b:.4f} (gap to NL min: {0.82 - h_b:.4f})")

        if abs(h_a - h_b) < 0.02:
            pr(f"     → h_char is STABLE across sections. Anomaly is INTRINSIC.")
            h_verdict = "INTRINSIC"
        elif h_a > h_b + 0.02:
            pr(f"     → A is more NL-like than B. Anomaly is STRONGER in B.")
            h_verdict = "SECTION_DEPENDENT"
        else:
            pr(f"     → B is more NL-like than A. Anomaly is STRONGER in A.")
            h_verdict = "SECTION_DEPENDENT"

        pr(f"\n  2. DISTANCE TO VMS_TARGET:")
        for sec in ['ALL', 'A', 'B']:
            d = fingerprint_distance(fps[sec])
            pr(f"     VMS_{sec}: {d:.4f}")

        dist_a = fingerprint_distance(fps['A'])
        dist_b = fingerprint_distance(fps['B'])
        dist_all = fingerprint_distance(fps['ALL'])
        pr(f"\n     Closer section: {'A' if dist_a < dist_b else 'B'} "
           f"(by {abs(dist_a - dist_b):.4f})")

        pr(f"\n  3. MONOLITH VALIDITY:")
        if h_verdict == "INTRINSIC" and abs(dist_a - dist_b) < 0.1:
            pr(f"     VMS_TARGET as monolithic baseline is JUSTIFIED.")
            pr(f"     A and B are dialects of the same system.")
        else:
            pr(f"     VMS_TARGET as monolithic baseline is QUESTIONABLE.")
            pr(f"     Future experiments should test against A and B targets separately.")

        pr(f"\n  4. IMPLICATIONS FOR PRIOR RESULTS:")
        pr(f"     encoding_layer_sweep best match (distance 0.1277) was against whole-corpus target.")
        if abs(dist_a - dist_b) > 0.1:
            pr(f"     → Should recompute against section-specific targets.")
        else:
            pr(f"     → Whole-corpus target is reasonable; result stands.")

    # Save
    outpath = RESULTS_DIR / 'currier_split_fingerprint.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"\n  Results saved to {outpath}")


if __name__ == '__main__':
    main()
