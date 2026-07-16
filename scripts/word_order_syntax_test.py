#!/usr/bin/env python3
"""
INTER-WORD STRUCTURE: IS THERE SYNTAX?
===================================================

Phases 32-38 established that INTRA-word morphological structure is real
(z=119.7 vs bigrams). Now: do ADJACENT words interact?

The critical skeptical challenge: morphological features correlate with
line position and section. Two adjacent words share position neighborhood
and section. Any apparent "syntax" could be just co-occurrence within
the same positional/sectional context.

Sub-analyses:
  39a) WORD-ORDER MI: Does word order matter?
       Observed MI(pfx_i, pfx_{i+1}) vs:
       - Null 1: shuffle word ORDER within each line (destroys syntax,
         preserves line composition)
       - Null 2: shuffle words across lines within same section
         (destroys line-level co-occurrence too)
       If obs >> null1 → word order matters (syntax)
       If obs ≈ null1 >> null2 → co-occurrence but not order

  39b) MORPHOLOGICAL AGREEMENT
       Do adjacent words share prefix or suffix more than expected?
       After controlling for position: compare obs agreement to a
       positionally-matched null (shuffle words within position bins).

  39c) DISTANCE DECAY
       Does the dependency between word_i and word_{i+k} decay with k?
       In real language: rapid decay (syntax is local).
       In positional confound: slow decay or no decay.

  39d) THE sh→qo PATTERN: REAL OR POSITIONAL?
       sh- is line-initial (mean=0.424), qo- follows.
       Within the same position bin, does sh→qo still hold?
       Test: restrict to mid-line pairs (position 0.3-0.7), compare.

  39e) VOYNICH vs WORD-SHUFFLED TEXT
       Complete comparison: Voynich bigram MI vs null where words
       are shuffled within position×section bins.
       If MI survives → genuine syntactic ordering.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_mi, get_collapsed, get_suffix, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(42)
np.random.seed(42)

# ══════════════════════════════════════════════════════════════════
# CONSTANTS & HELPERS
# ══════════════════════════════════════════════════════════════════

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']

SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']



def get_prefix(w):
    for p in ['qo','lch','lsh','sh','ch','so','do','q','o','d','y','l']:
        if w.startswith(p): return p
    return 'NONE'



def cramers_v(x_arr, y_arr):
    x_vals = sorted(set(x_arr))
    y_vals = sorted(set(y_arr))
    if len(x_vals) < 2 or len(y_vals) < 2: return 0.0
    x_map = {v: i for i, v in enumerate(x_vals)}
    y_map = {v: i for i, v in enumerate(y_vals)}
    table = np.zeros((len(x_vals), len(y_vals)))
    for xi, yi in zip(x_arr, y_arr):
        table[x_map[xi]][y_map[yi]] += 1
    N = table.sum()
    row_sums = table.sum(axis=1, keepdims=True)
    col_sums = table.sum(axis=0, keepdims=True)
    expected = row_sums * col_sums / N
    mask = expected > 0
    chi2 = np.sum((table[mask] - expected[mask])**2 / expected[mask])
    r, c = table.shape
    denom = N * (min(r, c) - 1)
    return math.sqrt(chi2 / denom) if denom > 0 else 0


# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════

FOLIO_DIR = Path("folios")



# ══════════════════════════════════════════════════════════════════
# EXTRACT FEATURES
# ══════════════════════════════════════════════════════════════════

def annotate_lines(lines):
    """Add collapsed form, prefix, suffix, position to each word."""
    for line in lines:
        n = len(line['words'])
        line['collapsed'] = [get_collapsed(w) for w in line['words']]
        line['pfx'] = [get_prefix(c) for c in line['collapsed']]
        line['sfx'] = [get_suffix(c) for c in line['collapsed']]
        line['pos'] = [i / max(n - 1, 1) for i in range(n)]
        line['pos_bin'] = []
        for p in line['pos']:
            if p < 0.2: line['pos_bin'].append('P0')
            elif p < 0.4: line['pos_bin'].append('P1')
            elif p < 0.6: line['pos_bin'].append('P2')
            elif p < 0.8: line['pos_bin'].append('P3')
            else: line['pos_bin'].append('P4')
    return lines


def extract_bigrams(lines, field, gap=1):
    """Extract (field_i, field_{i+gap}) pairs from all lines."""
    pairs = []
    for line in lines:
        arr = line[field]
        for i in range(len(arr) - gap):
            pairs.append((arr[i], arr[i + gap]))
    return pairs


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

print("Loading lines...")
lines = load_lines()
lines = annotate_lines(lines)
total_words = sum(len(l['words']) for l in lines)
print(f"  {len(lines)} lines, {total_words} word tokens")

# ══════════════════════════════════════════════════════════════════
# 39a: WORD-ORDER MI
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("39a: WORD-ORDER MI — Does word order matter?")
print("=" * 70)

# Observed bigram MI at prefix and suffix level
obs_pfx_bg = extract_bigrams(lines, 'pfx')
obs_sfx_bg = extract_bigrams(lines, 'sfx')
obs_pfx_mi = compute_mi([a for a, _ in obs_pfx_bg], [b for _, b in obs_pfx_bg])
obs_sfx_mi = compute_mi([a for a, _ in obs_sfx_bg], [b for _, b in obs_sfx_bg])
# Cross: prefix_i → suffix_{i+1}
obs_cross_bg = []
for line in lines:
    for i in range(len(line['pfx']) - 1):
        obs_cross_bg.append((line['pfx'][i], line['sfx'][i + 1]))
obs_cross_mi = compute_mi([a for a, _ in obs_cross_bg], [b for _, b in obs_cross_bg])

print(f"\n  Observed bigram MI:")
print(f"    MI(pfx_i, pfx_{{i+1}})   = {obs_pfx_mi:.4f} bits")
print(f"    MI(sfx_i, sfx_{{i+1}})   = {obs_sfx_mi:.4f} bits")
print(f"    MI(pfx_i, sfx_{{i+1}})   = {obs_cross_mi:.4f} bits")

# Null 1: shuffle word ORDER within each line
N_PERM = 500
null1_pfx = []
null1_sfx = []
null1_cross = []

print(f"\n  Running {N_PERM} within-line shuffles (Null 1: destroy order, keep composition)...")
for perm in range(N_PERM):
    shuffled = []
    for line in lines:
        n = len(line['words'])
        perm_idx = list(range(n))
        random.shuffle(perm_idx)
        shuffled.append({
            'pfx': [line['pfx'][j] for j in perm_idx],
            'sfx': [line['sfx'][j] for j in perm_idx],
        })
    # Extract bigrams from shuffled
    pfx_bg = []
    sfx_bg = []
    cross_bg = []
    for sl in shuffled:
        for i in range(len(sl['pfx']) - 1):
            pfx_bg.append((sl['pfx'][i], sl['pfx'][i + 1]))
            sfx_bg.append((sl['sfx'][i], sl['sfx'][i + 1]))
            cross_bg.append((sl['pfx'][i], sl['sfx'][i + 1]))
    null1_pfx.append(compute_mi([a for a, _ in pfx_bg], [b for _, b in pfx_bg]))
    null1_sfx.append(compute_mi([a for a, _ in sfx_bg], [b for _, b in sfx_bg]))
    null1_cross.append(compute_mi([a for a, _ in cross_bg], [b for _, b in cross_bg]))

n1_pfx_m, n1_pfx_s = np.mean(null1_pfx), np.std(null1_pfx)
n1_sfx_m, n1_sfx_s = np.mean(null1_sfx), np.std(null1_sfx)
n1_cross_m, n1_cross_s = np.mean(null1_cross), np.std(null1_cross)

z_pfx_1 = (obs_pfx_mi - n1_pfx_m) / max(n1_pfx_s, 1e-10)
z_sfx_1 = (obs_sfx_mi - n1_sfx_m) / max(n1_sfx_s, 1e-10)
z_cross_1 = (obs_cross_mi - n1_cross_m) / max(n1_cross_s, 1e-10)

print(f"\n  Null 1 (within-line shuffle — destroys ORDER, keeps composition):")
print(f"  {'Feature':<25} {'Observed':>10} {'Null 1':>15} {'z':>8}")
print(f"  {'-' * 58}")
print(f"  {'MI(pfx→pfx)':<25} {obs_pfx_mi:>10.4f} {n1_pfx_m:>8.4f}±{n1_pfx_s:.4f} {z_pfx_1:>8.1f}")
print(f"  {'MI(sfx→sfx)':<25} {obs_sfx_mi:>10.4f} {n1_sfx_m:>8.4f}±{n1_sfx_s:.4f} {z_sfx_1:>8.1f}")
print(f"  {'MI(pfx→sfx_next)':<25} {obs_cross_mi:>10.4f} {n1_cross_m:>8.4f}±{n1_cross_s:.4f} {z_cross_1:>8.1f}")

# Null 2: shuffle words across lines WITHIN section
print(f"\n  Running {N_PERM} across-line shuffles within section (Null 2)...")
# Group words by section
section_words = defaultdict(list)
for line in lines:
    for i in range(len(line['words'])):
        section_words[line['section']].append({
            'pfx': line['pfx'][i], 'sfx': line['sfx'][i]
        })

null2_pfx = []
null2_sfx = []
for perm in range(N_PERM):
    # Shuffle within section, then refill lines
    pools = {}
    for sec, wds in section_words.items():
        pool = list(wds)
        random.shuffle(pool)
        pools[sec] = iter(pool)

    pfx_bg = []
    sfx_bg = []
    for line in lines:
        n = len(line['words'])
        sec = line['section']
        try:
            drawn = [next(pools[sec]) for _ in range(n)]
        except StopIteration:
            continue
        for i in range(n - 1):
            pfx_bg.append((drawn[i]['pfx'], drawn[i + 1]['pfx']))
            sfx_bg.append((drawn[i]['sfx'], drawn[i + 1]['sfx']))

    null2_pfx.append(compute_mi([a for a, _ in pfx_bg], [b for _, b in pfx_bg]))
    null2_sfx.append(compute_mi([a for a, _ in sfx_bg], [b for _, b in sfx_bg]))

n2_pfx_m, n2_pfx_s = np.mean(null2_pfx), np.std(null2_pfx)
n2_sfx_m, n2_sfx_s = np.mean(null2_sfx), np.std(null2_sfx)
z_pfx_2 = (obs_pfx_mi - n2_pfx_m) / max(n2_pfx_s, 1e-10)
z_sfx_2 = (obs_sfx_mi - n2_sfx_m) / max(n2_sfx_s, 1e-10)

print(f"\n  Null 2 (across-line shuffle within section — destroys line composition):")
print(f"  {'Feature':<25} {'Observed':>10} {'Null 2':>15} {'z':>8}")
print(f"  {'-' * 58}")
print(f"  {'MI(pfx→pfx)':<25} {obs_pfx_mi:>10.4f} {n2_pfx_m:>8.4f}±{n2_pfx_s:.4f} {z_pfx_2:>8.1f}")
print(f"  {'MI(sfx→sfx)':<25} {obs_sfx_mi:>10.4f} {n2_sfx_m:>8.4f}±{n2_sfx_s:.4f} {z_sfx_2:>8.1f}")

print(f"\n  INTERPRETATION:")
if z_pfx_1 > 3 or z_sfx_1 > 3:
    print(f"  → z >> 3 against Null 1: WORD ORDER MATTERS — genuine syntax signal")
else:
    print(f"  → z ≤ 3 against Null 1: NO word-order effect — co-occurrence only")

if z_pfx_2 > 3 or z_sfx_2 > 3:
    print(f"  → z >> 3 against Null 2: LINE-LEVEL co-occurrence is real")
else:
    print(f"  → z ≤ 3 against Null 2: no structure beyond section-level")


# ══════════════════════════════════════════════════════════════════
# 39b: MORPHOLOGICAL AGREEMENT
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("39b: MORPHOLOGICAL AGREEMENT")
print("    Do adjacent words share prefix/suffix more than expected?")
print("=" * 70)

# Observed agreement rates
pfx_agree = sum(1 for a, b in obs_pfx_bg if a == b) / len(obs_pfx_bg)
sfx_agree = sum(1 for a, b in obs_sfx_bg if a == b) / len(obs_sfx_bg)

# Position-controlled null: shuffle words within position×section bins
print(f"\n  Observed same-prefix rate:  {100 * pfx_agree:.2f}%")
print(f"  Observed same-suffix rate:  {100 * sfx_agree:.2f}%")

# Build position×section bins
pos_sec_bins = defaultdict(list)
for line in lines:
    for i in range(len(line['words'])):
        key = (line['pos_bin'][i], line['section'])
        pos_sec_bins[key].append({
            'pfx': line['pfx'][i], 'sfx': line['sfx'][i],
            'line_id': id(line), 'word_idx': i
        })

null_pfx_agree = []
null_sfx_agree = []
print(f"  Running {N_PERM} position×section-controlled shuffles...")
for perm in range(N_PERM):
    # Shuffle within bins, then reconstitute lines
    shuffled_pool = {}
    for key, wds in pos_sec_bins.items():
        pool = list(wds)
        random.shuffle(pool)
        shuffled_pool[key] = iter(pool)

    pfx_matches = 0
    sfx_matches = 0
    total_pairs = 0
    for line in lines:
        n = len(line['words'])
        drawn = []
        for i in range(n):
            key = (line['pos_bin'][i], line['section'])
            try:
                drawn.append(next(shuffled_pool[key]))
            except StopIteration:
                drawn.append({'pfx': line['pfx'][i], 'sfx': line['sfx'][i]})
        for i in range(n - 1):
            if drawn[i]['pfx'] == drawn[i + 1]['pfx']:
                pfx_matches += 1
            if drawn[i]['sfx'] == drawn[i + 1]['sfx']:
                sfx_matches += 1
            total_pairs += 1

    if total_pairs > 0:
        null_pfx_agree.append(pfx_matches / total_pairs)
        null_sfx_agree.append(sfx_matches / total_pairs)

np_m, np_s = np.mean(null_pfx_agree), np.std(null_pfx_agree)
ns_m, ns_s = np.mean(null_sfx_agree), np.std(null_sfx_agree)
z_pa = (pfx_agree - np_m) / max(np_s, 1e-10)
z_sa = (sfx_agree - ns_m) / max(ns_s, 1e-10)

print(f"\n  Position×Section controlled null:")
print(f"  {'':>25} {'Observed':>10} {'Null':>15} {'z':>8}")
print(f"  {'-' * 58}")
print(f"  {'Same prefix rate':<25} {100*pfx_agree:>9.2f}% {100*np_m:>7.2f}%±{100*np_s:.2f}% {z_pa:>8.1f}")
print(f"  {'Same suffix rate':<25} {100*sfx_agree:>9.2f}% {100*ns_m:>7.2f}%±{100*ns_s:.2f}% {z_sa:>8.1f}")

if z_pa > 3:
    print(f"  → Prefix agreement is REAL — not explained by position/section")
else:
    print(f"  → Prefix agreement is explained by position/section confound")

if z_sa > 3:
    print(f"  → Suffix agreement is REAL — not explained by position/section")
else:
    print(f"  → Suffix agreement is explained by position/section confound")


# ══════════════════════════════════════════════════════════════════
# 39c: DISTANCE DECAY
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("39c: DISTANCE DECAY")
print("    Does MI decay with word distance? (syntax = fast decay)")
print("=" * 70)

print(f"\n  {'Gap':>4} {'MI(pfx,pfx)':>14} {'MI(sfx,sfx)':>14} {'N pairs':>10}")
print(f"  {'-' * 46}")

for gap in [1, 2, 3, 4, 5, 6]:
    pfx_bg = extract_bigrams(lines, 'pfx', gap=gap)
    sfx_bg = extract_bigrams(lines, 'sfx', gap=gap)
    if len(pfx_bg) < 100:
        continue
    mi_pfx = compute_mi([a for a, _ in pfx_bg], [b for _, b in pfx_bg])
    mi_sfx = compute_mi([a for a, _ in sfx_bg], [b for _, b in sfx_bg])
    print(f"  {gap:>4} {mi_pfx:>14.4f} {mi_sfx:>14.4f} {len(pfx_bg):>10}")

# Compare to null (within-line shuffle) at each gap
print(f"\n  With z-scores vs within-line shuffle (50 perms):")
print(f"  {'Gap':>4} {'z(pfx)':>10} {'z(sfx)':>10} | Verdict")
print(f"  {'-' * 46}")

for gap in [1, 2, 3, 4, 5, 6]:
    obs_pfx_g = extract_bigrams(lines, 'pfx', gap=gap)
    obs_sfx_g = extract_bigrams(lines, 'sfx', gap=gap)
    if len(obs_pfx_g) < 100:
        continue
    obs_mp = compute_mi([a for a, _ in obs_pfx_g], [b for _, b in obs_pfx_g])
    obs_ms = compute_mi([a for a, _ in obs_sfx_g], [b for _, b in obs_sfx_g])

    null_pfx_g = []
    null_sfx_g = []
    for _ in range(50):
        shuffled = []
        for line in lines:
            n = len(line['words'])
            perm_idx = list(range(n))
            random.shuffle(perm_idx)
            shuffled.append({
                'pfx': [line['pfx'][j] for j in perm_idx],
                'sfx': [line['sfx'][j] for j in perm_idx],
            })
        pfx_bg = []
        sfx_bg = []
        for sl in shuffled:
            for i in range(len(sl['pfx']) - gap):
                pfx_bg.append((sl['pfx'][i], sl['pfx'][i + gap]))
                sfx_bg.append((sl['sfx'][i], sl['sfx'][i + gap]))
        null_pfx_g.append(compute_mi([a for a, _ in pfx_bg], [b for _, b in pfx_bg]))
        null_sfx_g.append(compute_mi([a for a, _ in sfx_bg], [b for _, b in sfx_bg]))

    z_p = (obs_mp - np.mean(null_pfx_g)) / max(np.std(null_pfx_g), 1e-10)
    z_s = (obs_ms - np.mean(null_sfx_g)) / max(np.std(null_sfx_g), 1e-10)

    verdict = ""
    if z_p > 3 or z_s > 3:
        verdict = "ORDER MATTERS"
    else:
        verdict = "no order effect"
    print(f"  {gap:>4} {z_p:>10.1f} {z_s:>10.1f} | {verdict}")


# ══════════════════════════════════════════════════════════════════
# 39d: THE sh→qo PATTERN
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("39d: THE sh→qo PATTERN — REAL OR POSITIONAL?")
print("=" * 70)

# sh- is line-initial (mean=0.424). Does sh→qo persist mid-line?
# Restrict to pairs where BOTH words are in position 0.2-0.8
mid_pfx_bg = []
all_pfx_bg = []
for line in lines:
    for i in range(len(line['pfx']) - 1):
        pair = (line['pfx'][i], line['pfx'][i + 1])
        all_pfx_bg.append(pair)
        if 0.2 <= line['pos'][i] <= 0.8 and 0.2 <= line['pos'][i + 1] <= 0.8:
            mid_pfx_bg.append(pair)

# Transition rates: P(next=qo | current=sh)
def transition_rate(pairs, from_pfx, to_pfx):
    denom = sum(1 for a, _ in pairs if a == from_pfx)
    if denom == 0: return 0, 0
    numer = sum(1 for a, b in pairs if a == from_pfx and b == to_pfx)
    base_rate = sum(1 for _, b in pairs if b == to_pfx) / len(pairs)
    return numer / denom, base_rate

# Test several notable transitions
notable = [
    ('sh', 'qo', 'sh→qo'),
    ('qo', 'ch', 'qo→ch'),
    ('ch', 'd', 'ch→d'),
    ('d', 'o', 'd→o'),
    ('y', 'y', 'y→y'),
    ('NONE', 'NONE', '∅→∅'),
    ('l', 'l', 'l→l'),
]

print(f"\n  {'Pattern':<10} {'All pairs':>15} {'Mid-line only':>15} {'Base rate':>12}")
print(f"  {'-' * 55}")
for from_p, to_p, label in notable:
    r_all, br_all = transition_rate(all_pfx_bg, from_p, to_p)
    r_mid, br_mid = transition_rate(mid_pfx_bg, from_p, to_p)
    print(f"  {label:<10} {100*r_all:>7.1f}% ({100*r_all/max(100*br_all,0.01):.1f}x)"
          f" {100*r_mid:>7.1f}% ({100*r_mid/max(100*br_mid,0.01):.1f}x)"
          f" {100*br_all:>7.1f}%")

# Also: what typically FOLLOWS sh- words?
print(f"\n  What follows sh- words? (all positions)")
sh_next = Counter(b for a, b in all_pfx_bg if a == 'sh')
sh_total = sum(sh_next.values())
overall_pfx = Counter(b for _, b in all_pfx_bg)
overall_total = sum(overall_pfx.values())
print(f"  {'Next pfx':<8} {'Obs %':>8} {'Exp %':>8} {'Ratio':>8}")
print(f"  {'-' * 36}")
for pfx in sorted(sh_next, key=sh_next.get, reverse=True):
    obs = sh_next[pfx] / sh_total * 100
    exp = overall_pfx.get(pfx, 0) / overall_total * 100
    print(f"  {pfx:<8} {obs:>7.1f}% {exp:>7.1f}% {obs/max(exp,0.01):>7.2f}x")


# ══════════════════════════════════════════════════════════════════
# 39e: COMPREHENSIVE SYNTAX TEST
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("39e: COMPREHENSIVE SYNTAX TEST")
print("    Position×Section controlled word-order MI")
print("=" * 70)

# The strongest test: shuffle words within position×section bins,
# then measure loss of bigram MI. This controls for BOTH position
# and section effects simultaneously.

obs_word_bg = []
for line in lines:
    for i in range(len(line['collapsed']) - 1):
        obs_word_bg.append((line['collapsed'][i], line['collapsed'][i+1]))

# Use collapsed forms for raw word MI (but limit to top 200 forms to avoid
# MI inflation from rare-form noise)
top_forms = set(f for f, c in Counter(c for line in lines for c in line['collapsed']).most_common(200))

def word_to_class(w):
    """Map word to its class: top-200 form or prefix+suffix bucket."""
    if w in top_forms:
        return w
    return f"{get_prefix(w)}+{get_suffix(w)}"

obs_class_bg = []
for line in lines:
    classes = [word_to_class(c) for c in line['collapsed']]
    for i in range(len(classes) - 1):
        obs_class_bg.append((classes[i], classes[i + 1]))

obs_class_mi = compute_mi([a for a, _ in obs_class_bg], [b for _, b in obs_class_bg])

# Position×section null
N_PERM_E = 200
null_class_mi = []
print(f"\n  Running {N_PERM_E} position×section shuffles...")

# Pre-build word→class mapping
all_word_classes = {}
for line in lines:
    for c in line['collapsed']:
        if c not in all_word_classes:
            all_word_classes[c] = word_to_class(c)

for perm in range(N_PERM_E):
    # Shuffle within position×section bins
    pools = defaultdict(list)
    for line in lines:
        for i in range(len(line['words'])):
            key = (line['pos_bin'][i], line['section'])
            pools[key].append(line['collapsed'][i])

    for key in pools:
        random.shuffle(pools[key])

    pool_iters = {k: iter(v) for k, v in pools.items()}

    class_bg = []
    for line in lines:
        n = len(line['words'])
        drawn = []
        for i in range(n):
            key = (line['pos_bin'][i], line['section'])
            try:
                w = next(pool_iters[key])
            except StopIteration:
                w = line['collapsed'][i]
            drawn.append(all_word_classes.get(w, word_to_class(w)))
        for i in range(n - 1):
            class_bg.append((drawn[i], drawn[i + 1]))

    null_class_mi.append(compute_mi([a for a, _ in class_bg], [b for _, b in class_bg]))

    if (perm + 1) % 50 == 0:
        print(f"    ... {perm + 1}/{N_PERM_E} done")

nc_m, nc_s = np.mean(null_class_mi), np.std(null_class_mi)
z_class = (obs_class_mi - nc_m) / max(nc_s, 1e-10)

print(f"\n  RESULTS (word-class bigram MI, pos×sec controlled):")
print(f"    Observed MI:  {obs_class_mi:.4f} bits")
print(f"    Null MI:      {nc_m:.4f} ± {nc_s:.4f} bits")
print(f"    z = {z_class:.1f}")

if z_class > 10:
    verdict_e = "STRONG SYNTAX: word order carries information beyond position/section"
elif z_class > 3:
    verdict_e = "MODERATE SYNTAX: some word-order structure survives controls"
elif z_class > 0:
    verdict_e = "WEAK/NO SYNTAX: word order adds little beyond position/section"
else:
    verdict_e = "NO SYNTAX: order is random after controlling for position/section"

print(f"    → {verdict_e}")

# How much of the bigram MI is explained by position×section?
pct_explained = nc_m / obs_class_mi * 100 if obs_class_mi > 0 else 0
pct_residual = 100 - pct_explained
print(f"\n    Position×section explains: {pct_explained:.1f}% of bigram MI")
print(f"    Residual (genuine syntax): {pct_residual:.1f}%")


# ══════════════════════════════════════════════════════════════════
# SYNTHESIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("word_order_syntax_test SYNTHESIS")
print("=" * 70)

print(f"""
  WORD-ORDER TEST (39a):
    MI(pfx→pfx): obs={obs_pfx_mi:.4f}, null1={n1_pfx_m:.4f}, z={z_pfx_1:.1f}
    MI(sfx→sfx): obs={obs_sfx_mi:.4f}, null1={n1_sfx_m:.4f}, z={z_sfx_1:.1f}
    If z > 3: word ORDER within lines carries information

  AGREEMENT (39b):
    Prefix agreement: obs={100*pfx_agree:.2f}%, null={100*np_m:.2f}%, z={z_pa:.1f}
    Suffix agreement: obs={100*sfx_agree:.2f}%, null={100*ns_m:.2f}%, z={z_sa:.1f}

  DISTANCE DECAY (39c):
    See table above. Syntax → fast decay. Confound → slow decay.

  sh→qo (39d):
    All: {100*transition_rate(all_pfx_bg, 'sh', 'qo')[0]:.1f}%
    Mid-line: {100*transition_rate(mid_pfx_bg, 'sh', 'qo')[0]:.1f}%
    If mid-line rate drops → positional artifact

  COMPREHENSIVE (39e):
    Observed MI={obs_class_mi:.4f}, Pos×Sec null={nc_m:.4f}±{nc_s:.4f}
    z={z_class:.1f}
    {verdict_e}
""")

print("[word_order_syntax_test Complete]")
