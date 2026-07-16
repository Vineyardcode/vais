#!/usr/bin/env python3
"""
CROSS-VALIDATION AND STRUCTURAL TESTS
==================================================

word_transition_network revealed a two-level grammar: feature-level (suffix→prefix,
asymmetric, 20% of info) and word-level (symmetric, word-specific, 80%).
This phase stress-tests these findings.

Sub-analyses:
  48a) SUFFIX→PREFIX TRANSITION MATRIX — Full 11×8 matrix. How
       concentrated is the morphological syntax?

  48b) CROSS-VALIDATION — Train on even lines, test on odd. Does the
       word MI generalize or is it overfitting?

  48c) FIRST-CHAR / LAST-CHAR MI — Raw character-level test at word
       boundaries. No parsing needed.

  48d) REMOVING THE -dy→qo PIPELINE — How much syntax remains if we
       exclude -dy→qo transitions?

  48e) WORD MI WITHIN SUFFIX STRATA — Among word pairs sharing the
       same suffix transition, is there still word-specific MI?
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_H, get_collapsed, get_gram_prefix, get_suffix, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(48)
np.random.seed(48)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']
GRAM_PREFIXES = ['qo','so','do','q','o','d','y']




def get_class(sfx):
    if sfx in ('dy', 'y'): return 'A'
    if sfx in ('X', 'ar', 'in'): return 'M'
    return 'B'

FOLIO_DIR = Path("folios")



def compute_MI_from_bigrams(bigram_counts, unigram_counts, N_tokens, N_bigrams):
    """Compute MI(W1;W2) from bigram and unigram counts"""
    H_uni = compute_H(unigram_counts, N_tokens)
    # H(W2|W1) = H(W1,W2) - H(W1)
    H_joint = 0.0
    for c in bigram_counts.values():
        if c > 0:
            p = c / N_bigrams
            H_joint -= p * math.log2(p)
    w1_counts = Counter()
    for (w1, w2), c in bigram_counts.items():
        w1_counts[w1] += c
    H_w1 = compute_H(w1_counts, N_bigrams)
    H_cond = H_joint - H_w1
    MI = H_uni - H_cond
    return H_uni, H_cond, MI

print("Loading lines...")
lines = load_lines()

line_collapsed = []
all_collapsed = []
for line in lines:
    coll = [get_collapsed(w) for w in line['words']]
    line_collapsed.append(coll)
    all_collapsed.extend(coll)

word_counts = Counter(all_collapsed)
N = len(all_collapsed)
print(f"  {len(lines)} lines, {N} tokens, {len(word_counts)} types")


# ══════════════════════════════════════════════════════════════════
# 48a: SUFFIX→PREFIX TRANSITION MATRIX
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("48a: SUFFIX→GRAM PREFIX TRANSITION MATRIX")
print("    Full morphological syntax map")
print("=" * 70)

sfx_gpfx_matrix = Counter()
sfx_count = Counter()
gpfx_count = Counter()
total_trans = 0

for seq in line_collapsed:
    for i in range(len(seq) - 1):
        sfx = get_suffix(seq[i])
        gpfx = get_gram_prefix(seq[i+1])
        sfx_gpfx_matrix[(sfx, gpfx)] += 1
        sfx_count[sfx] += 1
        gpfx_count[gpfx] += 1
        total_trans += 1

sfx_list = ['X'] + SUFFIXES
gpfx_list = ['X'] + GRAM_PREFIXES

# Print transition probabilities P(gpfx | sfx)
print(f"\n  P(next_gpfx | prev_sfx) — rows=suffix, cols=gram_prefix")
header = f"  {'sfx':>6}" + "".join(f"{gp:>7}" for gp in gpfx_list) + f"{'N':>8}"
print(header)
print("  " + "-" * (len(header) - 2))

sfx_mi_contribution = {}
for sfx in sfx_list:
    n = sfx_count.get(sfx, 0)
    if n == 0:
        continue
    row = []
    for gp in gpfx_list:
        c = sfx_gpfx_matrix.get((sfx, gp), 0)
        row.append(c / n * 100)
    row_str = "".join(f"{v:>6.1f}%" for v in row)
    print(f"  {sfx:>6}{row_str}{n:>8}")
    
    # MI contribution of this suffix
    mi_contrib = 0.0
    for gp in gpfx_list:
        c = sfx_gpfx_matrix.get((sfx, gp), 0)
        if c > 0:
            p_joint = c / total_trans
            p_sfx = sfx_count[sfx] / total_trans
            p_gpfx = gpfx_count[gp] / total_trans
            mi_contrib += p_joint * math.log2(p_joint / (p_sfx * p_gpfx))
    sfx_mi_contribution[sfx] = mi_contrib

# Print marginal gpfx distribution
n_total = sum(gpfx_count[gp] for gp in gpfx_list)
marg_str = "".join(f"{gpfx_count[gp]/n_total*100:>6.1f}%" for gp in gpfx_list)
print(f"  {'MARG':>6}{marg_str}")

# MI contribution by suffix
total_mi = sum(sfx_mi_contribution.values())
print(f"\n  MI(sfx_i → gpfx_{'{'}i+1{'}'}) = {total_mi:.4f} bits")
print(f"\n  MI contributions by suffix:")
for sfx in sorted(sfx_mi_contribution, key=sfx_mi_contribution.get, reverse=True):
    mi = sfx_mi_contribution[sfx]
    print(f"  {sfx:>6}: {mi:.4f} bits ({mi/total_mi*100:.1f}%)")

# Which suffix→prefix transitions are most over-represented?
print(f"\n  Top 15 over-represented transitions (O/E ratio):")
oe_pairs = []
for sfx in sfx_list:
    for gp in gpfx_list:
        c = sfx_gpfx_matrix.get((sfx, gp), 0)
        if c < 5:
            continue
        expected = sfx_count[sfx] * gpfx_count[gp] / total_trans
        if expected > 0:
            oe = c / expected
            oe_pairs.append((sfx, gp, c, expected, oe))

oe_pairs.sort(key=lambda x: x[4], reverse=True)
print(f"  {'Suffix':>8} {'→Gpfx':>8} {'Count':>8} {'O/E':>8}")
for sfx, gp, c, exp, oe in oe_pairs[:15]:
    print(f"  {sfx:>8} {gp:>8} {c:>8} {oe:>7.2f}x")


# ══════════════════════════════════════════════════════════════════
# 48b: CROSS-VALIDATION
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("48b: CROSS-VALIDATION OF WORD BIGRAM MI")
print("    Train on even lines, test on odd. Does MI generalize?")
print("=" * 70)

even_lines = [line_collapsed[i] for i in range(0, len(line_collapsed), 2)]
odd_lines = [line_collapsed[i] for i in range(1, len(line_collapsed), 2)]

def get_stats(line_set):
    words = []
    for seq in line_set:
        words.extend(seq)
    wc = Counter(words)
    n = len(words)
    bg = Counter()
    for seq in line_set:
        for i in range(len(seq) - 1):
            bg[(seq[i], seq[i+1])] += 1
    total_bg = sum(bg.values())
    return words, wc, n, bg, total_bg

even_words, even_wc, even_N, even_bg, even_total_bg = get_stats(even_lines)
odd_words, odd_wc, odd_N, odd_bg, odd_total_bg = get_stats(odd_lines)

# Within-half MI
for name, wc, n, bg, total_bg in [('Even', even_wc, even_N, even_bg, even_total_bg),
                                     ('Odd', odd_wc, odd_N, odd_bg, odd_total_bg)]:
    H_uni, H_cond, MI = compute_MI_from_bigrams(bg, wc, n, total_bg)
    print(f"  {name}: N={n}, types={len(wc)}, H={H_uni:.3f}, H(w2|w1)={H_cond:.3f}, MI={MI:.3f}, MI/H={MI/H_uni:.3f}")

# Cross-validation: compute perplexity of odd data under even-trained bigram model
# PP = 2^{H_cross} where H_cross = -1/N * sum log2 P_train(w2|w1)
# Use add-1 smoothing to handle unseen bigrams

def cross_perplexity(train_bg, train_w1_counts, train_vocab_size, test_lines):
    """Compute perplexity of test data under smoothed train bigram model"""
    log_prob_sum = 0.0
    n_tokens = 0
    unseen_bg = 0
    for seq in test_lines:
        for i in range(len(seq) - 1):
            w1, w2 = seq[i], seq[i+1]
            # Add-1 smoothing
            count = train_bg.get((w1, w2), 0)
            w1_count = train_w1_counts.get(w1, 0)
            prob = (count + 1) / (w1_count + train_vocab_size)
            log_prob_sum += math.log2(prob)
            n_tokens += 1
            if count == 0:
                unseen_bg += 1
    H_cross = -log_prob_sum / n_tokens
    return 2 ** H_cross, unseen_bg / n_tokens * 100

# Train counts
even_w1 = Counter()
for (w1, w2), c in even_bg.items():
    even_w1[w1] += c
odd_w1 = Counter()
for (w1, w2), c in odd_bg.items():
    odd_w1[w1] += c

# Merge vocabularies for smoothing
all_vocab = len(set(list(even_wc.keys()) + list(odd_wc.keys())))

pp_even_on_odd, unseen_eo = cross_perplexity(even_bg, even_w1, all_vocab, odd_lines)
pp_odd_on_even, unseen_oe = cross_perplexity(odd_bg, odd_w1, all_vocab, even_lines)

# Also compute unigram perplexity as baseline
def unigram_perplexity(train_wc, train_N, train_vocab, test_lines):
    log_prob_sum = 0.0
    n_tokens = 0
    for seq in test_lines:
        for w in seq:
            count = train_wc.get(w, 0)
            prob = (count + 1) / (train_N + train_vocab)
            log_prob_sum += math.log2(prob)
            n_tokens += 1
    H_cross = -log_prob_sum / n_tokens
    return 2 ** H_cross

pp_uni_even_on_odd = unigram_perplexity(even_wc, even_N, all_vocab, odd_lines)
pp_uni_odd_on_even = unigram_perplexity(odd_wc, odd_N, all_vocab, even_lines)

print(f"\n  Cross-validation perplexity:")
print(f"  {'Model':>20} {'Train→Test':>15} {'PP':>10} {'Unseen%':>10}")
print(f"  {'Unigram':>20} {'Even→Odd':>15} {pp_uni_even_on_odd:>10.1f}")
print(f"  {'Unigram':>20} {'Odd→Even':>15} {pp_uni_odd_on_even:>10.1f}")
print(f"  {'Bigram':>20} {'Even→Odd':>15} {pp_even_on_odd:>10.1f} {unseen_eo:>9.1f}%")
print(f"  {'Bigram':>20} {'Odd→Even':>15} {pp_odd_on_even:>10.1f} {unseen_oe:>9.1f}%")

pp_reduction_eo = (1 - pp_even_on_odd / pp_uni_even_on_odd) * 100
pp_reduction_oe = (1 - pp_odd_on_even / pp_uni_odd_on_even) * 100
print(f"\n  Bigram PP reduction (cross-validated):")
print(f"    Even→Odd: {pp_reduction_eo:.1f}%")
print(f"    Odd→Even: {pp_reduction_oe:.1f}%")
print(f"    Mean:     {(pp_reduction_eo + pp_reduction_oe)/2:.1f}%")

# Compare to within-sample PP reduction (parser_free_word_classes found 40.6%)
all_words_all, all_wc_all, all_N_all, all_bg_all, all_total_bg_all = get_stats(line_collapsed)
all_w1 = Counter()
for (w1, w2), c in all_bg_all.items():
    all_w1[w1] += c
pp_bigram_within = cross_perplexity(all_bg_all, all_w1, len(word_counts), line_collapsed)[0]
pp_uni_within = unigram_perplexity(all_wc_all, all_N_all, len(word_counts), line_collapsed)
pp_within = (1 - pp_bigram_within / pp_uni_within) * 100
print(f"    Within-sample: {pp_within:.1f}%")
print(f"    Overfitting: {pp_within - (pp_reduction_eo + pp_reduction_oe)/2:.1f}pp")


# ══════════════════════════════════════════════════════════════════
# 48c: FIRST-CHAR / LAST-CHAR MI
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("48c: FIRST-CHAR / LAST-CHAR MI")
print("    Raw character-level syntax at word boundaries")
print("=" * 70)

# For each adjacent word pair, record (last char of w1, first char of w2)
# Use ORIGINAL (uncollapsed) words for this test
char_bigrams = Counter()
last_char_counts = Counter()
first_char_counts = Counter()
total_char_bg = 0

for line in lines:
    words = line['words']
    for i in range(len(words) - 1):
        w1 = words[i]
        w2 = words[i+1]
        if w1 and w2:
            lc = w1[-1]
            fc = w2[0]
            char_bigrams[(lc, fc)] += 1
            last_char_counts[lc] += 1
            first_char_counts[fc] += 1
            total_char_bg += 1

# MI(last_char, first_char)
H_lc = compute_H(last_char_counts, total_char_bg)
H_fc = compute_H(first_char_counts, total_char_bg)

H_joint_char = 0.0
for c in char_bigrams.values():
    if c > 0:
        p = c / total_char_bg
        H_joint_char -= p * math.log2(p)

MI_char = H_lc + H_fc - H_joint_char
print(f"\n  H(last_char) = {H_lc:.3f}")
print(f"  H(first_char) = {H_fc:.3f}")
print(f"  MI(last_char, first_char) = {MI_char:.4f} bits")
print(f"  MI/H ratio = {MI_char/H_lc:.4f}")

# Shuffled null
n_shuf = 200
shuf_mi = []
for trial in range(n_shuf):
    shuf_bg = Counter()
    for line in lines:
        words = list(line['words'])
        random.shuffle(words)
        for i in range(len(words) - 1):
            if words[i] and words[i+1]:
                shuf_bg[(words[i][-1], words[i+1][0])] += 1
    H_s = 0.0
    for c in shuf_bg.values():
        if c > 0:
            p = c / total_char_bg
            H_s -= p * math.log2(p)
    mi_s = H_lc + H_fc - H_s
    shuf_mi.append(mi_s)

excess_char = MI_char - np.mean(shuf_mi)
z_char = excess_char / np.std(shuf_mi)
print(f"  Shuffled MI: {np.mean(shuf_mi):.4f} ± {np.std(shuf_mi):.4f}")
print(f"  Excess: {excess_char:.4f}")
print(f"  z-score: {z_char:.1f}")

# Transition matrix: last char → first char
print(f"\n  Top 15 over-represented last→first char transitions:")
char_oe = []
for (lc, fc), c in char_bigrams.items():
    if c < 10:
        continue
    exp = last_char_counts[lc] * first_char_counts[fc] / total_char_bg
    if exp > 0:
        oe = c / exp
        char_oe.append((lc, fc, c, exp, oe))
char_oe.sort(key=lambda x: x[4], reverse=True)
print(f"  {'Last':>6} {'First':>6} {'Count':>8} {'O/E':>8}")
for lc, fc, c, exp, oe in char_oe[:15]:
    print(f"  {lc:>6} {fc:>6} {c:>8} {oe:>7.2f}x")

# Under-represented
print(f"\n  Top 10 AVOIDED transitions (lowest O/E, count≥10):")
char_oe.sort(key=lambda x: x[4])
print(f"  {'Last':>6} {'First':>6} {'Count':>8} {'O/E':>8}")
for lc, fc, c, exp, oe in char_oe[:10]:
    print(f"  {lc:>6} {fc:>6} {c:>8} {oe:>7.2f}x")


# ══════════════════════════════════════════════════════════════════
# 48d: REMOVING THE -dy→qo PIPELINE
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("48d: REMOVING THE -dy→qo PIPELINE")
print("    How much syntax remains without the dominant pattern?")
print("=" * 70)

# Count what fraction of all bigrams are -dy→qo
dy_qo_count = 0
dy_any_count = 0
any_qo_count = 0
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        sfx1 = get_suffix(seq[i])
        gpfx2 = get_gram_prefix(seq[i+1])
        if sfx1 == 'dy':
            dy_any_count += 1
            if gpfx2 == 'qo':
                dy_qo_count += 1
        if gpfx2 == 'qo':
            any_qo_count += 1

total_all_bg = sum(1 for seq in line_collapsed for i in range(len(seq)-1))
print(f"\n  -dy→qo: {dy_qo_count} / {total_all_bg} = {dy_qo_count/total_all_bg*100:.1f}% of all bigrams")
print(f"  -dy→anything: {dy_any_count} ({dy_any_count/total_all_bg*100:.1f}%)")
print(f"  anything→qo: {any_qo_count} ({any_qo_count/total_all_bg*100:.1f}%)")

# P(qo | -dy) vs P(qo | not -dy)
p_qo_given_dy = dy_qo_count / dy_any_count if dy_any_count > 0 else 0
not_dy_count = total_all_bg - dy_any_count
not_dy_qo = any_qo_count - dy_qo_count
p_qo_given_not_dy = not_dy_qo / not_dy_count if not_dy_count > 0 else 0
print(f"  P(qo | -dy) = {p_qo_given_dy:.3f}")
print(f"  P(qo | not -dy) = {p_qo_given_not_dy:.3f}")
print(f"  Ratio: {p_qo_given_dy / p_qo_given_not_dy:.2f}x")

# Recompute suffix→prefix MI excluding -dy and qo
# Strategy: remove all -dy words as w1 and all qo- words as w2
excl_sfx_gpfx = Counter()
excl_sfx = Counter()
excl_gpfx = Counter()
excl_total = 0

for seq in line_collapsed:
    for i in range(len(seq) - 1):
        sfx = get_suffix(seq[i])
        gpfx = get_gram_prefix(seq[i+1])
        if sfx == 'dy' or gpfx == 'qo':
            continue
        excl_sfx_gpfx[(sfx, gpfx)] += 1
        excl_sfx[sfx] += 1
        excl_gpfx[gpfx] += 1
        excl_total += 1

# MI excluding -dy and qo
if excl_total > 0:
    excl_mi = 0.0
    for (sfx, gpfx), c in excl_sfx_gpfx.items():
        p_joint = c / excl_total
        p_sfx = excl_sfx[sfx] / excl_total
        p_gpfx = excl_gpfx[gpfx] / excl_total
        if p_sfx > 0 and p_gpfx > 0:
            excl_mi += p_joint * math.log2(p_joint / (p_sfx * p_gpfx))
    
    print(f"\n  MI(sfx→gpfx) full: {sum(sfx_mi_contribution.values()):.4f} bits")
    print(f"  MI(sfx→gpfx) excluding -dy and qo-: {excl_mi:.4f} bits")
    print(f"  Retained: {excl_mi/sum(sfx_mi_contribution.values())*100:.1f}%")

# Shuffled null for the exclusion set
n_shuf = 200
shuf_excl_mi = []
for trial in range(n_shuf):
    shuf_bg = Counter()
    shuf_sfx = Counter()
    shuf_gpfx = Counter()
    shuf_total = 0
    for seq in line_collapsed:
        shuf = list(seq)
        random.shuffle(shuf)
        for i in range(len(shuf) - 1):
            sfx = get_suffix(shuf[i])
            gpfx = get_gram_prefix(shuf[i+1])
            if sfx == 'dy' or gpfx == 'qo':
                continue
            shuf_bg[(sfx, gpfx)] += 1
            shuf_sfx[sfx] += 1
            shuf_gpfx[gpfx] += 1
            shuf_total += 1
    
    mi_s = 0.0
    for (sfx, gpfx), c in shuf_bg.items():
        p_j = c / shuf_total
        p_s = shuf_sfx[sfx] / shuf_total
        p_g = shuf_gpfx[gpfx] / shuf_total
        if p_s > 0 and p_g > 0:
            mi_s += p_j * math.log2(p_j / (p_s * p_g))
    shuf_excl_mi.append(mi_s)

excl_z = (excl_mi - np.mean(shuf_excl_mi)) / np.std(shuf_excl_mi)
print(f"  Shuffled MI (excl): {np.mean(shuf_excl_mi):.4f} ± {np.std(shuf_excl_mi):.4f}")
print(f"  z-score (excl): {excl_z:.1f}")

# Also try removing only -dy (keep qo) and only qo (keep -dy)
for label, exclude_sfx, exclude_gpfx in [('-dy only', 'dy', None), ('qo only', None, 'qo')]:
    test_bg = Counter()
    test_sfx = Counter()
    test_gpfx = Counter()
    test_total = 0
    for seq in line_collapsed:
        for i in range(len(seq) - 1):
            sfx = get_suffix(seq[i])
            gpfx = get_gram_prefix(seq[i+1])
            if exclude_sfx and sfx == exclude_sfx:
                continue
            if exclude_gpfx and gpfx == exclude_gpfx:
                continue
            test_bg[(sfx, gpfx)] += 1
            test_sfx[sfx] += 1
            test_gpfx[gpfx] += 1
            test_total += 1
    
    mi_test = 0.0
    for (sfx, gpfx), c in test_bg.items():
        p_j = c / test_total
        p_s = test_sfx[sfx] / test_total
        p_g = test_gpfx[gpfx] / test_total
        if p_s > 0 and p_g > 0:
            mi_test += p_j * math.log2(p_j / (p_s * p_g))
    print(f"  MI(sfx→gpfx) excluding {label}: {mi_test:.4f} ({mi_test/sum(sfx_mi_contribution.values())*100:.1f}%)")


# ══════════════════════════════════════════════════════════════════
# 48e: WORD MI WITHIN SUFFIX STRATA
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("48e: WORD MI WITHIN SUFFIX STRATA")
print("    Within same suffix transition, is there word-specific MI?")
print("=" * 70)

# For each (sfx_i, sfx_{i+1}) stratum, compute MI(w1, w2)
strata = defaultdict(lambda: {'bigrams': Counter(), 'w1': Counter(), 'w2': Counter(), 'n': 0})

for seq in line_collapsed:
    for i in range(len(seq) - 1):
        w1, w2 = seq[i], seq[i+1]
        sfx1 = get_suffix(w1)
        sfx2 = get_suffix(w2)
        key = (sfx1, sfx2)
        strata[key]['bigrams'][(w1, w2)] += 1
        strata[key]['w1'][w1] += 1
        strata[key]['w2'][w2] += 1
        strata[key]['n'] += 1

# For strata with enough data, compute within-stratum MI
print(f"\n  {'Sfx1→Sfx2':>15} {'N':>6} {'Types(bg)':>10} {'H(w1)':>7} {'H(w2|w1)':>9} {'MI':>7} {'MI/H':>7}")

strata_results = []
for key in sorted(strata, key=lambda k: strata[k]['n'], reverse=True):
    s = strata[key]
    if s['n'] < 50:
        continue
    
    n = s['n']
    bg_types = len(s['bigrams'])
    h_w1 = compute_H(s['w1'], n)
    
    # H(w2|w1) within stratum
    h_joint = 0.0
    for c in s['bigrams'].values():
        if c > 0:
            p = c / n
            h_joint -= p * math.log2(p)
    h_w1_bg = compute_H(s['w1'], n)  # same as h_w1
    h_w2_given_w1 = h_joint - h_w1_bg
    
    h_w2 = compute_H(s['w2'], n)
    mi = h_w2 - h_w2_given_w1
    mi_h = mi / h_w2 if h_w2 > 0 else 0
    
    label = f"{key[0]}→{key[1]}"
    print(f"  {label:>15} {n:>6} {bg_types:>10} {h_w2:>7.3f} {h_w2_given_w1:>9.3f} {mi:>7.3f} {mi_h:>7.3f}")
    strata_results.append((key, n, mi, mi_h))

# How does within-stratum MI compare to overall?
# Weight by N
weighted_mi = sum(n * mi for _, n, mi, _ in strata_results)
total_n = sum(n for _, n, _, _ in strata_results)
weighted_mi_h = sum(n * mi_h for _, n, _, mi_h in strata_results)
print(f"\n  Weighted average within-stratum MI: {weighted_mi/total_n:.4f}")
print(f"  Weighted average within-stratum MI/H: {weighted_mi_h/total_n:.4f}")
print(f"  Overall MI(w1,w2): {MI_char:.4f}" if False else "")

# Permutation test: shuffle w1 and w2 within each stratum
print(f"\n  Permutation test (shuffle within strata, 100 trials):")
n_perm = 100
perm_mi_weighted = []
for trial in range(n_perm):
    trial_mi_sum = 0.0
    trial_n_sum = 0
    for key in strata:
        s = strata[key]
        if s['n'] < 50:
            continue
        n = s['n']
        # Get all w1 and w2 in this stratum
        w1_list = []
        w2_list = []
        for (w1, w2), c in s['bigrams'].items():
            w1_list.extend([w1] * c)
            w2_list.extend([w2] * c)
        # Shuffle w2
        random.shuffle(w2_list)
        shuf_bg = Counter(zip(w1_list, w2_list))
        
        h_joint_s = 0.0
        for c in shuf_bg.values():
            if c > 0:
                p = c / n
                h_joint_s -= p * math.log2(p)
        h_w1_s = compute_H(Counter(w1_list), n)
        h_w2_given_w1_s = h_joint_s - h_w1_s
        h_w2_s = compute_H(Counter(w2_list), n)
        mi_s = h_w2_s - h_w2_given_w1_s
        
        trial_mi_sum += n * mi_s
        trial_n_sum += n
    perm_mi_weighted.append(trial_mi_sum / trial_n_sum)

actual_weighted = weighted_mi / total_n
perm_mean = np.mean(perm_mi_weighted)
perm_std = np.std(perm_mi_weighted)
z_strata = (actual_weighted - perm_mean) / perm_std if perm_std > 0 else 0
print(f"  Actual within-stratum MI:  {actual_weighted:.4f}")
print(f"  Shuffled within-stratum:   {perm_mean:.4f} ± {perm_std:.4f}")
print(f"  z-score:                   {z_strata:.1f}")

print("\n" + "=" * 70)
print("structure_cross_validation COMPLETE")
print("=" * 70)
