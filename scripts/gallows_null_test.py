#!/usr/bin/env python3
"""
GALLOWS-AS-NULLS TEST

═══════════════════════════════════════════════════════════════════════

HYPOTHESIS: Gallows characters (t, k, p, f, cth, ckh, cph, cfh) are
null insertions — meaningless padding added to disguise the real text.
Additional sub-hypothesis: "o" is also a null character.

IF GALLOWS = NULLS, WE PREDICT:
  1. Stripping gallows should IMPROVE h_char (move toward NL range 0.82-0.90)
     because nulls disrupt character predictability.
  2. Vocabulary should COLLAPSE disproportionately (many word-types merge,
     because gallows were the only thing differentiating them).
  3. Word-length distribution should become MORE natural-language-like.
  4. Zipf slope should remain stable (null insertion doesn't change
     rank-frequency shape much).
  5. Heaps exponent should DROP (fewer new types as vocabulary consolidates).

IF GALLOWS ≠ NULLS (they carry meaning), WE PREDICT:
  1. h_char should get WORSE (removing real characters destroys bigram
     structure), OR stay roughly the same if they're somewhat redundant.
  2. Vocabulary merge should be PROPORTIONAL to frequency — random removal
     doesn't cause disproportionate merging.
  3. Some words become empty (impossible if they carry real content).

DIAGNOSTICS BEYOND FINGERPRINT:
  A. Merge analysis: How many word-types collapse? Is it disproportionate?
  B. Empty words: Do any words reduce to nothing?
  C. Positional bias: Where do gallows appear in word structure?
     (Nulls should be uniform; real chars should have positional function.)
  D. Section variation: Do gallows rates vary between Currier A and B?
     (Nulls should be constant; functional chars track content changes.)
  E. Line-position effects: Are gallows paragraph-initial as Pelling claims?

SKEPTICISM PROTOCOL:
  Even if stripping improves the fingerprint, this does NOT prove gallows
  are nulls. Removing ANY frequent glyph class would mechanically alter
  the fingerprint. We must compare against CONTROL strippings — remove
  other glyph classes of similar frequency and see if the improvement
  is SPECIFIC to gallows or generic to any removal.

═══════════════════════════════════════════════════════════════════════
"""

import re, sys, io, math, json, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import char_bigram_predictability, clean_word, eva_to_glyphs, extract_words_from_line, hapax_ratio_at_midpoint, index_of_coincidence, mean_word_length, ttr_at_n, zipf_alpha

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
# EVA PARSING
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']

# Gallows characters: tall (t,k,p,f) + bench (cth,ckh,cph,cfh)
GALLOWS_SET = {'t', 'k', 'p', 'f', 'cth', 'ckh', 'cph', 'cfh'}






# ═══════════════════════════════════════════════════════════════════════
# PARSE VMS — with folio-level tracking for section analysis
# ═══════════════════════════════════════════════════════════════════════

# Currier A/B assignment (approximate, based on consensus)
# A: herbals (f1-f57), B: biological/cosmo/pharma (f75-f116)
CURRIER_A_RANGE = range(1, 58)
CURRIER_B_RANGE = range(75, 117)

def parse_vms_by_folio():
    """Parse VMS returning words per folio and overall."""
    folio_words = defaultdict(list)
    all_words = []
    all_lines = []  # (folio_id, line_text, words) for line-level analysis

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)
    for filepath in folio_files:
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num: continue
        folio_num = int(m_num.group(1))

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line: continue
                m = re.match(r'<([^>]+)>', line)
                if not m: continue
                rest = line[m.end():].strip()
                if not rest: continue
                words = extract_words_from_line(rest)
                folio_words[folio_num].extend(words)
                all_words.extend(words)
                all_lines.append((folio_num, rest, words))

    return all_words, folio_words, all_lines


# ═══════════════════════════════════════════════════════════════════════
# STRIPPING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def strip_glyphs(words, remove_set):
    """Remove specified glyphs from word list. Returns new word list
    (empty words are dropped) and statistics."""
    new_words = []
    empty_count = 0
    total_removed = 0
    total_glyphs = 0

    for w in words:
        glyphs = eva_to_glyphs(w)
        total_glyphs += len(glyphs)
        remaining = [g for g in glyphs if g not in remove_set]
        removed = len(glyphs) - len(remaining)
        total_removed += removed

        if not remaining:
            empty_count += 1
            continue
        new_word = ''.join(remaining)
        new_words.append(new_word)

    return new_words, {
        'total_glyphs_before': total_glyphs,
        'total_removed': total_removed,
        'pct_removed': 100 * total_removed / max(total_glyphs, 1),
        'empty_words': empty_count,
        'words_before': len(words),
        'words_after': len(new_words),
        'words_lost_pct': 100 * empty_count / max(len(words), 1),
    }


# ═══════════════════════════════════════════════════════════════════════
# FINGERPRINT BATTERY
# ═══════════════════════════════════════════════════════════════════════

def heaps_exponent(words):
    n = len(words)
    if n < 100: return 0.0
    sample_points = np.linspace(100, n, 20, dtype=int)
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

def fingerprint_distance(fp, target=VMS_TARGET):
    dims = []
    for key, vms_val in target.items():
        if key in fp and vms_val != 0:
            dims.append(((fp[key] - vms_val) / vms_val) ** 2)
    return math.sqrt(sum(dims)) if dims else float('inf')


# ═══════════════════════════════════════════════════════════════════════
# CONTROL STRIPPING — CRITICAL METHODOLOGICAL STEP
# ═══════════════════════════════════════════════════════════════════════

# To test whether gallows-removal effects are SPECIFIC or just an artifact
# of removing any frequent glyph class, we also strip CONTROL sets of
# similar aggregate frequency.

# Common VMS glyphs by frequency (approximate):
# e, o, a, i, ch, d, y, l, sh, n, k, t, r, s, q, p, f, m, g
# Gallows (t,k,p,f + bench variants) are ~12-15% of all glyphs.
# "o" alone is ~10-12%.

CONTROL_SETS = {
    'ctrl_vowel_like':  {'e', 'a', 'i'},     # ~25% of glyphs — vowel-like
    'ctrl_medial':      {'d', 'l', 'r'},      # ~10-12% of glyphs — medial/final
}


# ═══════════════════════════════════════════════════════════════════════
# DIAGNOSTIC: VOCABULARY MERGE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def merge_analysis(original_words, stripped_words, label):
    """Analyze how stripping causes word types to merge."""
    orig_types = set(original_words)
    # Build mapping: original word → stripped word
    mapping = {}
    for ow, sw in zip(original_words, stripped_words):
        if ow not in mapping:
            mapping[ow] = sw

    # Count how many orig types map to the same stripped type
    stripped_to_orig = defaultdict(set)
    for ow, sw in mapping.items():
        stripped_to_orig[sw].add(ow)

    merges = {sw: origs for sw, origs in stripped_to_orig.items() if len(origs) > 1}
    merge_count = sum(len(origs) - 1 for origs in merges.values())
    total_merged_types = sum(len(origs) for origs in merges.values())

    pr(f"\n  {label} MERGE ANALYSIS:")
    pr(f"    Original types: {len(orig_types)}")
    pr(f"    Stripped types:  {len(stripped_to_orig)}")
    pr(f"    Types that merged: {total_merged_types} → {len(merges)} groups")
    pr(f"    Net type reduction: {len(orig_types) - len(stripped_to_orig)} "
       f"({100*(len(orig_types)-len(stripped_to_orig))/len(orig_types):.1f}%)")

    # Show top merges
    biggest = sorted(merges.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    if biggest:
        pr(f"    Top merge groups:")
        for stripped, origs in biggest:
            examples = sorted(origs, key=lambda w: -original_words.count(w))[:5]
            pr(f"      '{stripped}' ← {list(examples)}")

    # CRITICAL: Is merge rate proportional to expectation?
    # If gallows were random noise, the merge rate should be predictable
    # from the frequency of gallows tokens
    return {
        'orig_types': len(orig_types),
        'stripped_types': len(stripped_to_orig),
        'type_reduction_pct': 100 * (len(orig_types) - len(stripped_to_orig)) / max(len(orig_types), 1),
        'merge_groups': len(merges),
        'types_involved_in_merges': total_merged_types,
    }


# ═══════════════════════════════════════════════════════════════════════
# DIAGNOSTIC: POSITIONAL DISTRIBUTION OF GALLOWS
# ═══════════════════════════════════════════════════════════════════════

def positional_analysis(words):
    """Where do gallows appear within words? If nulls: should be uniform."""
    positions = defaultdict(lambda: Counter())  # position_cat → glyph → count
    total_per_pos = Counter()

    for w in words:
        glyphs = eva_to_glyphs(w)
        n = len(glyphs)
        if n == 0: continue
        for i, g in enumerate(glyphs):
            if n == 1:
                pos_cat = 'sole'
            elif i == 0:
                pos_cat = 'initial'
            elif i == n - 1:
                pos_cat = 'final'
            else:
                pos_cat = 'medial'
            total_per_pos[pos_cat] += 1
            if g in GALLOWS_SET:
                positions[pos_cat][g] += 1

    pr("\n  POSITIONAL DISTRIBUTION OF GALLOWS:")
    pr(f"    {'Position':<10} {'Total glyphs':>14} {'Gallows':>10} {'Pct':>8}")
    pr(f"    {'─'*10} {'─'*14} {'─'*10} {'─'*8}")

    for pos in ['initial', 'medial', 'final', 'sole']:
        gal_total = sum(positions[pos].values())
        tot = total_per_pos[pos]
        if tot > 0:
            pr(f"    {pos:<10} {tot:>14,} {gal_total:>10,} {100*gal_total/tot:>7.1f}%")

    # Breakdown by individual gallows
    pr(f"\n    Individual gallows by position:")
    pr(f"    {'Glyph':<6}", end='')
    for pos in ['initial', 'medial', 'final']:
        pr(f" {pos:>10}", end='')
    pr(f" {'TOTAL':>10}")

    for g in sorted(GALLOWS_SET):
        pr(f"    {g:<6}", end='')
        total_g = 0
        for pos in ['initial', 'medial', 'final']:
            c = positions[pos][g]
            total_g += c
            pr(f" {c:>10,}", end='')
        pr(f" {total_g:>10,}")

    # Chi-square test: is gallows distribution across positions
    # consistent with overall glyph distribution?
    observed_gallows = []
    expected_gallows = []
    total_all = sum(total_per_pos.values())
    total_gallows_all = sum(sum(v.values()) for v in positions.values())

    if total_all > 0 and total_gallows_all > 0:
        overall_gallows_rate = total_gallows_all / total_all
        for pos in ['initial', 'medial', 'final']:
            obs = sum(positions[pos].values())
            exp = total_per_pos[pos] * overall_gallows_rate
            observed_gallows.append(obs)
            expected_gallows.append(exp)

        chi2 = sum((o - e)**2 / e for o, e in zip(observed_gallows, expected_gallows) if e > 0)
        pr(f"\n    Chi-square (uniform distribution test): χ²={chi2:.1f}, df=2")
        pr(f"    If χ² > 5.99 → gallows are NOT uniformly distributed (p<0.05)")
        pr(f"    Verdict: {'POSITIONALLY BIASED (nulls unlikely)' if chi2 > 5.99 else 'Consistent with uniform (nulls possible)'}")


# ═══════════════════════════════════════════════════════════════════════
# DIAGNOSTIC: CURRIER A vs B GALLOWS RATES
# ═══════════════════════════════════════════════════════════════════════

def section_analysis(folio_words):
    """Compare gallows rates in Currier A vs Currier B sections."""
    stats = {}
    for label, frange in [('Currier_A', CURRIER_A_RANGE), ('Currier_B', CURRIER_B_RANGE)]:
        words = []
        for fnum in frange:
            words.extend(folio_words.get(fnum, []))

        if not words:
            continue

        all_glyphs = []
        gallows_count = 0
        o_count = 0
        for w in words:
            gs = eva_to_glyphs(w)
            all_glyphs.extend(gs)
            for g in gs:
                if g in GALLOWS_SET:
                    gallows_count += 1
                if g == 'o':
                    o_count += 1

        total = len(all_glyphs)
        stats[label] = {
            'words': len(words),
            'glyphs': total,
            'gallows': gallows_count,
            'gallows_pct': 100 * gallows_count / max(total, 1),
            'o_count': o_count,
            'o_pct': 100 * o_count / max(total, 1),
        }

    pr("\n  CURRIER A vs B — GALLOWS & 'o' RATES:")
    pr(f"    {'Section':<12} {'Words':>8} {'Glyphs':>8} {'Gallows':>8} {'Gal%':>6} {'o':>8} {'o%':>6}")
    pr(f"    {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*6} {'─'*8} {'─'*6}")
    for label in ['Currier_A', 'Currier_B']:
        if label not in stats: continue
        s = stats[label]
        pr(f"    {label:<12} {s['words']:>8,} {s['glyphs']:>8,} {s['gallows']:>8,} "
           f"{s['gallows_pct']:>5.1f}% {s['o_count']:>8,} {s['o_pct']:>5.1f}%")

    if 'Currier_A' in stats and 'Currier_B' in stats:
        a = stats['Currier_A']
        b = stats['Currier_B']
        # z-test for difference in proportions
        p_a = a['gallows'] / max(a['glyphs'], 1)
        p_b = b['gallows'] / max(b['glyphs'], 1)
        p_pool = (a['gallows'] + b['gallows']) / max(a['glyphs'] + b['glyphs'], 1)
        se = math.sqrt(p_pool * (1 - p_pool) * (1/max(a['glyphs'],1) + 1/max(b['glyphs'],1)))
        if se > 0:
            z = (p_a - p_b) / se
            pr(f"\n    Gallows rate difference: z = {z:.2f}")
            pr(f"    If |z| > 1.96 → sections differ significantly (p<0.05)")
            pr(f"    Verdict: {'RATES DIFFER (nulls should be constant)' if abs(z) > 1.96 else 'Rates similar (consistent with nulls)'}")

        # Same for 'o'
        p_a_o = a['o_count'] / max(a['glyphs'], 1)
        p_b_o = b['o_count'] / max(b['glyphs'], 1)
        p_pool_o = (a['o_count'] + b['o_count']) / max(a['glyphs'] + b['glyphs'], 1)
        se_o = math.sqrt(p_pool_o * (1 - p_pool_o) * (1/max(a['glyphs'],1) + 1/max(b['glyphs'],1)))
        if se_o > 0:
            z_o = (p_a_o - p_b_o) / se_o
            pr(f"    'o' rate difference: z = {z_o:.2f}")
            pr(f"    Verdict: {'RATES DIFFER' if abs(z_o) > 1.96 else 'Rates similar'}")


# ═══════════════════════════════════════════════════════════════════════
# DIAGNOSTIC: LINE-INITIAL / LINE-FINAL EFFECTS (Pelling)
# ═══════════════════════════════════════════════════════════════════════

def line_position_effects(all_lines):
    """Test Pelling's claim: gallows favor paragraph-initial positions."""
    first_word_glyphs = Counter()
    other_word_glyphs = Counter()
    first_word_gallows = 0
    other_word_gallows = 0
    first_word_total = 0
    other_word_total = 0

    for folio_num, line_text, words in all_lines:
        if not words: continue
        # First word of each line
        fw_glyphs = eva_to_glyphs(words[0])
        first_word_total += len(fw_glyphs)
        for g in fw_glyphs:
            first_word_glyphs[g] += 1
            if g in GALLOWS_SET:
                first_word_gallows += 1

        # Other words
        for w in words[1:]:
            gs = eva_to_glyphs(w)
            other_word_total += len(gs)
            for g in gs:
                other_word_glyphs[g] += 1
                if g in GALLOWS_SET:
                    other_word_gallows += 1

    pr("\n  LINE-INITIAL vs OTHER POSITIONS — GALLOWS:")
    pr(f"    First-word glyphs: {first_word_total:,} total, "
       f"{first_word_gallows:,} gallows ({100*first_word_gallows/max(first_word_total,1):.1f}%)")
    pr(f"    Other-word glyphs: {other_word_total:,} total, "
       f"{other_word_gallows:,} gallows ({100*other_word_gallows/max(other_word_total,1):.1f}%)")

    rate_first = first_word_gallows / max(first_word_total, 1)
    rate_other = other_word_gallows / max(other_word_total, 1)
    p_pool = (first_word_gallows + other_word_gallows) / max(first_word_total + other_word_total, 1)
    se = math.sqrt(p_pool * (1-p_pool) * (1/max(first_word_total,1) + 1/max(other_word_total,1)))
    if se > 0:
        z = (rate_first - rate_other) / se
        pr(f"    Rate difference z = {z:.2f}")
        pr(f"    Verdict: {'GALLOWS FAVOR LINE-INITIAL (functional, not null)' if z > 1.96 else 'No significant line-initial bias'}")


# ═══════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 72)
    pr("  gallows_null_test — GALLOWS-AS-NULLS HYPOTHESIS TEST")
    pr("=" * 72)

    # ── 1. Parse VMS ──────────────────────────────────────────────────
    pr("\n▸ Parsing VMS corpus...")
    all_words, folio_words, all_lines = parse_vms_by_folio()
    pr(f"  Total tokens: {len(all_words):,}")
    pr(f"  Total types:  {len(set(all_words)):,}")

    # Glyph frequency overview
    all_glyphs = []
    for w in all_words:
        all_glyphs.extend(eva_to_glyphs(w))
    glyph_freq = Counter(all_glyphs)
    total_glyphs = len(all_glyphs)
    pr(f"  Total glyphs: {total_glyphs:,}")

    gallows_total = sum(glyph_freq[g] for g in GALLOWS_SET)
    o_total = glyph_freq['o']
    pr(f"  Gallows frequency: {gallows_total:,} ({100*gallows_total/total_glyphs:.1f}%)")
    pr(f"  'o' frequency:     {o_total:,} ({100*o_total/total_glyphs:.1f}%)")
    pr(f"  Combined:          {gallows_total+o_total:,} ({100*(gallows_total+o_total)/total_glyphs:.1f}%)")

    pr(f"\n  Individual gallows frequencies:")
    for g in sorted(GALLOWS_SET, key=lambda g: -glyph_freq[g]):
        pr(f"    {g:<5}: {glyph_freq[g]:>6,} ({100*glyph_freq[g]/total_glyphs:.2f}%)")

    # ── 2. Baseline fingerprint ───────────────────────────────────────
    pr("\n" + "─" * 72)
    pr("▸ BASELINE VMS FINGERPRINT (live recompute)")
    fp_baseline = compute_fingerprint(all_words, 'VMS_baseline')
    dist_baseline = fingerprint_distance(fp_baseline)
    pr(f"  h_char={fp_baseline['h_char_ratio']:.4f}  Heaps={fp_baseline['heaps_beta']:.4f}  "
       f"hapax={fp_baseline['hapax_ratio_mid']:.4f}  wlen={fp_baseline['mean_word_len']:.2f}  "
       f"Zipf={fp_baseline['zipf_alpha']:.4f}  TTR={fp_baseline['ttr_5000']:.4f}")
    pr(f"  Types={fp_baseline['n_types']:,}  Alphabet={fp_baseline['alphabet_size']}  "
       f"IC={fp_baseline['ic']:.4f}")
    pr(f"  Distance to VMS_TARGET: {dist_baseline:.4f}")

    # ── 3. Stripping experiments ──────────────────────────────────────
    pr("\n" + "=" * 72)
    pr("  STRIPPING EXPERIMENTS")
    pr("=" * 72)

    experiments = [
        ('GALLOWS_STRIPPED', GALLOWS_SET),
        ('O_STRIPPED', {'o'}),
        ('GALLOWS+O_STRIPPED', GALLOWS_SET | {'o'}),
    ]

    # Add control experiments
    for ctrl_name, ctrl_set in CONTROL_SETS.items():
        experiments.append((ctrl_name.upper(), ctrl_set))

    results = {}
    all_stripped_pairs = {}  # label → (stripped_words, stats)

    for label, remove_set in experiments:
        pr(f"\n{'─'*72}")
        pr(f"▸ {label}: removing {sorted(remove_set)}")

        stripped_words, stats = strip_glyphs(all_words, remove_set)
        all_stripped_pairs[label] = (stripped_words, stats)

        pr(f"  Glyphs removed: {stats['total_removed']:,} / {stats['total_glyphs_before']:,} "
           f"({stats['pct_removed']:.1f}%)")
        pr(f"  Empty words (entirely removed): {stats['empty_words']} "
           f"({stats['words_lost_pct']:.2f}%)")
        pr(f"  Words: {stats['words_before']:,} → {stats['words_after']:,}")

        if not stripped_words:
            pr(f"  ERROR: No words remain after stripping!")
            continue

        fp = compute_fingerprint(stripped_words, label)
        dist = fingerprint_distance(fp)
        results[label] = {'fp': fp, 'dist': dist, 'stats': stats}

        pr(f"\n  FINGERPRINT:")
        pr(f"  h_char={fp['h_char_ratio']:.4f}  Heaps={fp['heaps_beta']:.4f}  "
           f"hapax={fp['hapax_ratio_mid']:.4f}  wlen={fp['mean_word_len']:.2f}  "
           f"Zipf={fp['zipf_alpha']:.4f}  TTR={fp['ttr_5000']:.4f}")
        pr(f"  Types={fp['n_types']:,}  Alphabet={fp['alphabet_size']}  IC={fp['ic']:.4f}")
        pr(f"  Distance to VMS_TARGET: {dist:.4f}")

        # Delta from baseline
        pr(f"\n  DELTAS from baseline:")
        for key in ['h_char_ratio', 'heaps_beta', 'hapax_ratio_mid', 'mean_word_len',
                     'zipf_alpha', 'ttr_5000']:
            delta = fp[key] - fp_baseline[key]
            pct = 100 * delta / max(abs(fp_baseline[key]), 0.001)
            direction = '↑' if delta > 0 else '↓' if delta < 0 else '='
            # For h_char, moving UP toward NL range (0.82-0.90) would support null hypothesis
            support = ''
            if key == 'h_char_ratio':
                if delta > 0:
                    support = ' ← TOWARD NL range (supports null hyp)'
                else:
                    support = ' ← AWAY from NL range (opposes null hyp)'
            pr(f"    {key:<18}: {delta:>+.4f} ({pct:>+.1f}%) {direction}{support}")

        pr(f"  Distance delta: {dist - dist_baseline:>+.4f} "
           f"({'CLOSER to VMS target' if dist < dist_baseline else 'FARTHER from VMS target'})")

    # ── 4. Merge analysis (only for gallows and gallows+o) ─────────────
    pr("\n" + "=" * 72)
    pr("  VOCABULARY MERGE ANALYSIS")
    pr("=" * 72)

    merge_sets = {
        'GALLOWS_STRIPPED': GALLOWS_SET,
        'O_STRIPPED': {'o'},
        'GALLOWS+O_STRIPPED': GALLOWS_SET | {'o'},
    }
    for label, remove_set in merge_sets.items():
        if label in all_stripped_pairs:
            # Build aligned pairs: filter out empties for merge analysis
            orig_stripped_pairs = []
            for w in all_words:
                glyphs = eva_to_glyphs(w)
                remaining = [g for g in glyphs if g not in remove_set]
                if remaining:
                    orig_stripped_pairs.append((w, ''.join(remaining)))

            orig_for_merge = [p[0] for p in orig_stripped_pairs]
            strip_for_merge = [p[1] for p in orig_stripped_pairs]
            merge_analysis(orig_for_merge, strip_for_merge, label)

    # ── 5. Positional analysis ────────────────────────────────────────
    pr("\n" + "=" * 72)
    pr("  POSITIONAL ANALYSIS")
    pr("=" * 72)
    positional_analysis(all_words)

    # ── 6. Currier A vs B ─────────────────────────────────────────────
    pr("\n" + "=" * 72)
    pr("  SECTION VARIATION ANALYSIS")
    pr("=" * 72)
    section_analysis(folio_words)

    # ── 7. Line-position effects ──────────────────────────────────────
    pr("\n" + "=" * 72)
    pr("  LINE-POSITION EFFECTS")
    pr("=" * 72)
    line_position_effects(all_lines)

    # ═══════════════════════════════════════════════════════════════════════
    # COMPARATIVE TABLE + VERDICT
    # ═══════════════════════════════════════════════════════════════════════

    pr("\n" + "=" * 72)
    pr("  COMPARATIVE FINGERPRINT TABLE")
    pr("=" * 72)

    dims = ['h_char_ratio', 'heaps_beta', 'hapax_ratio_mid', 'mean_word_len',
            'zipf_alpha', 'ttr_5000']
    header_labels = ['h_char', 'Heaps', 'hapax', 'wlen', 'Zipf', 'TTR', 'Dist']

    pr(f"\n  {'Variant':<24}", end='')
    for h in header_labels:
        pr(f" {h:>8}", end='')
    pr(f" {'Types':>8}")

    pr(f"  {'─'*24}", end='')
    for _ in header_labels:
        pr(f" {'─'*8}", end='')
    pr(f" {'─'*8}")

    # VMS Target
    pr(f"  {'VMS_TARGET':<24}", end='')
    for d in dims:
        pr(f" {VMS_TARGET[d]:>8.4f}", end='')
    pr(f" {'─':>8}     {'─':>8}")

    # NL reference range
    pr(f"  {'NL_range (approx)':<24}", end='')
    nl_ranges = {'h_char_ratio': '0.82-0.90', 'heaps_beta': '0.60-0.80',
                 'hapax_ratio_mid': '0.50-0.70', 'mean_word_len': '4.0-6.0',
                 'zipf_alpha': '0.90-1.10', 'ttr_5000': '0.30-0.50'}
    for d in dims:
        pr(f" {nl_ranges[d]:>8}", end='')
    pr()

    # Baseline
    pr(f"  {'VMS_baseline':<24}", end='')
    for d in dims:
        pr(f" {fp_baseline[d]:>8.4f}", end='')
    pr(f" {dist_baseline:>8.4f} {fp_baseline['n_types']:>8,}")

    # All experiments
    for label, remove_set in experiments:
        if label not in results: continue
        r = results[label]
        pr(f"  {label:<24}", end='')
        for d in dims:
            val = r['fp'][d]
            # Mark if moved toward NL range
            pr(f" {val:>8.4f}", end='')
        pr(f" {r['dist']:>8.4f} {r['fp']['n_types']:>8,}")

    # ═══════════════════════════════════════════════════════════════════
    # CRITICAL VERDICT
    # ═══════════════════════════════════════════════════════════════════

    pr("\n" + "=" * 72)
    pr("  CRITICAL VERDICT")
    pr("=" * 72)

    # Score the evidence
    evidence_for = []
    evidence_against = []

    # Test 1: Does h_char move toward NL?
    gal = results.get('GALLOWS_STRIPPED', {})
    if gal:
        h_delta = gal['fp']['h_char_ratio'] - fp_baseline['h_char_ratio']
        if h_delta > 0.01:
            evidence_for.append(f"h_char increases by {h_delta:.4f} "
                               f"({gal['fp']['h_char_ratio']:.4f}), moving toward NL range")
        elif h_delta < -0.01:
            evidence_against.append(f"h_char DECREASES by {abs(h_delta):.4f} — removing "
                                   f"gallows destroys predictability (they were functional)")
        else:
            evidence_against.append(f"h_char barely changes ({h_delta:+.4f}) — "
                                   f"gallows were not disrupting character predictability")

    # Test 2: Compare to controls
    gal_dist = results.get('GALLOWS_STRIPPED', {}).get('dist', float('inf'))
    for ctrl_name in CONTROL_SETS:
        ctrl = results.get(ctrl_name.upper(), {})
        if ctrl:
            ctrl_dist = ctrl.get('dist', float('inf'))
            if gal_dist < ctrl_dist - 0.05:
                evidence_for.append(f"Gallows removal reduces distance MORE than "
                                   f"control ({ctrl_name}): {gal_dist:.4f} vs {ctrl_dist:.4f}")
            elif abs(gal_dist - ctrl_dist) < 0.05:
                evidence_against.append(f"Gallows removal effect similar to control "
                                       f"({ctrl_name}): {gal_dist:.4f} vs {ctrl_dist:.4f} — "
                                       f"not specific to gallows")
            else:
                evidence_against.append(f"Gallows removal is WORSE than control "
                                       f"({ctrl_name}): {gal_dist:.4f} vs {ctrl_dist:.4f}")

    # Test 3: Empty words
    if gal:
        empties = gal['stats']['empty_words']
        if empties > 10:
            evidence_against.append(f"{empties} words are ENTIRELY gallows — these can't "
                                   f"be null padding if the word has no other content")
        elif empties > 0:
            evidence_against.append(f"{empties} words are entirely gallows (suspicious)")
        else:
            evidence_for.append("No words are entirely gallows (consistent with decoration)")

    # Test 4: Type reduction proportionality
    if gal:
        glyph_pct = gal['stats']['pct_removed']
        type_pct = 100 * (fp_baseline['n_types'] - gal['fp']['n_types']) / max(fp_baseline['n_types'], 1)
        ratio = type_pct / max(glyph_pct, 0.01)
        if ratio > 1.5:
            evidence_for.append(f"Type reduction ({type_pct:.1f}%) is disproportionate to "
                               f"glyph removal ({glyph_pct:.1f}%) — ratio {ratio:.1f}x — "
                               f"gallows inflated vocabulary artificially")
        elif ratio < 0.5:
            evidence_against.append(f"Type reduction ({type_pct:.1f}%) is LESS than glyph "
                                   f"removal ({glyph_pct:.1f}%) — gallows carry real "
                                   f"vocabulary information")
        else:
            # Neutral
            pass

    pr("\n  EVIDENCE SUPPORTING 'gallows = nulls':")
    if evidence_for:
        for e in evidence_for:
            pr(f"    ✓ {e}")
    else:
        pr("    (none)")

    pr("\n  EVIDENCE AGAINST 'gallows = nulls':")
    if evidence_against:
        for e in evidence_against:
            pr(f"    ✗ {e}")
    else:
        pr("    (none)")

    # Overall
    score = len(evidence_for) - len(evidence_against)
    pr(f"\n  SCORE: {len(evidence_for)} for, {len(evidence_against)} against")

    if score >= 2:
        verdict = "SUPPORTED — gallows show properties consistent with null characters"
    elif score <= -2:
        verdict = "REJECTED — gallows show properties of functional characters"
    else:
        verdict = "INCONCLUSIVE — mixed evidence, cannot confirm or deny"

    pr(f"  VERDICT: {verdict}")

    pr(f"\n  CAVEAT: Even a SUPPORTED verdict only means 'consistent with', not ")
    pr(f"  'proven'. Gallows could be: (a) true nulls, (b) positional markers ")
    pr(f"  that serve a formatting role, (c) weak ciphertext symbols that are ")
    pr(f"  partially redundant, or (d) something else entirely.")

    # ═══════════════════════════════════════════════════════════════════
    # Save results
    # ═══════════════════════════════════════════════════════════════════

    outpath = RESULTS_DIR / 'gallows_null_test.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"\n  Results saved to {outpath}")


if __name__ == '__main__':
    main()
