#!/usr/bin/env python3
"""
GENERALIZATION AND LINE BOUNDARY TESTS
===================================================

structure_cross_validation showed word-level bigrams don't generalize. Does the
morphological grammar generalize? Are lines syntactic units?

Sub-analyses:
  A) CROSS-VALIDATED MORPHOLOGICAL MI — Does suffix→prefix MI
       survive on held-out data?

  B) CROSS-VALIDATED CHARACTER MI — Does last_char→first_char MI
       generalize?

  C) LINE BOUNDARY TEST — Within-line vs cross-line transitions.

  D) JACKKNIFE STABILITY — Do key z-scores survive leave-k-out?

  E) THE qo-WORD NETWORK — Among -dy→qo transitions, is the
       specific qo-word predicted by the predecessor?
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_H, get_collapsed, get_gram_prefix, get_suffix, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(49)
np.random.seed(49)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']
GRAM_PREFIXES = ['qo','so','do','q','o','d','y']




FOLIO_DIR = Path("folios")



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
# 49a: CROSS-VALIDATED MORPHOLOGICAL MI
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("A: CROSS-VALIDATED MORPHOLOGICAL MI")
print("    Does suffix→prefix MI survive on held-out data?")
print("=" * 70)

sfx_list = ['X'] + SUFFIXES
gpfx_list = ['X'] + GRAM_PREFIXES

def get_sfx_gpfx_model(line_set):
    """Build suffix→prefix transition model from lines"""
    sfx_gpfx = Counter()
    sfx_counts = Counter()
    gpfx_counts = Counter()
    total = 0
    for seq in line_set:
        coll = [get_collapsed(w) for w in seq] if isinstance(seq[0], str) and not seq[0].replace('a','').replace('i','').replace('e','').replace('o','').replace('y','').replace('n','').replace('d','').replace('l','').replace('r','').replace('s','').replace('ch','') == '' else seq
        for i in range(len(coll) - 1):
            sfx = get_suffix(coll[i])
            gpfx = get_gram_prefix(coll[i+1])
            sfx_gpfx[(sfx, gpfx)] += 1
            sfx_counts[sfx] += 1
            gpfx_counts[gpfx] += 1
            total += 1
    return sfx_gpfx, sfx_counts, gpfx_counts, total

def compute_morph_mi(sfx_gpfx, sfx_counts, gpfx_counts, total):
    mi = 0.0
    for (sfx, gpfx), c in sfx_gpfx.items():
        p_joint = c / total
        p_sfx = sfx_counts[sfx] / total
        p_gpfx = gpfx_counts[gpfx] / total
        if p_sfx > 0 and p_gpfx > 0:
            mi += p_joint * math.log2(p_joint / (p_sfx * p_gpfx))
    return mi

def sfx_gpfx_cross_entropy(train_model, test_lines):
    """Cross-entropy of test data under trained sfx→gpfx model"""
    train_sfx_gpfx, train_sfx_counts, train_gpfx_counts, train_total = train_model
    n_sfx = len(sfx_list)
    n_gpfx = len(gpfx_list)
    
    log_prob_sum = 0.0
    n_tokens = 0
    for seq in test_lines:
        for i in range(len(seq) - 1):
            sfx = get_suffix(seq[i])
            gpfx = get_gram_prefix(seq[i+1])
            # Add-1 smoothing with n_gpfx possible outcomes
            count = train_sfx_gpfx.get((sfx, gpfx), 0)
            sfx_total = train_sfx_counts.get(sfx, 0)
            prob = (count + 1) / (sfx_total + n_gpfx)
            log_prob_sum += math.log2(prob)
            n_tokens += 1
    return -log_prob_sum / n_tokens if n_tokens > 0 else 0, n_tokens

# Split into even/odd
even_lines = [line_collapsed[i] for i in range(0, len(line_collapsed), 2)]
odd_lines = [line_collapsed[i] for i in range(1, len(line_collapsed), 2)]

# Train on each half
even_model = get_sfx_gpfx_model(even_lines)
odd_model = get_sfx_gpfx_model(odd_lines)
full_model = get_sfx_gpfx_model(line_collapsed)

# Within-sample MI
full_mi = compute_morph_mi(*full_model)
even_mi = compute_morph_mi(*even_model)
odd_mi = compute_morph_mi(*odd_model)

print(f"\n  Within-sample MI(sfx→gpfx):")
print(f"  Full:  {full_mi:.4f} bits")
print(f"  Even:  {even_mi:.4f} bits")
print(f"  Odd:   {odd_mi:.4f} bits")

# Cross-entropy test
# Baseline: marginal gpfx entropy (no conditioning on sfx)
all_gpfx_counts = Counter()
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        all_gpfx_counts[get_gram_prefix(seq[i+1])] += 1
H_gpfx_marginal = compute_H(all_gpfx_counts, sum(all_gpfx_counts.values()))
print(f"\n  Marginal H(gpfx) = {H_gpfx_marginal:.4f} bits")

# Cross-entropy
h_even_on_odd, n_eo = sfx_gpfx_cross_entropy(even_model, odd_lines)
h_odd_on_even, n_oe = sfx_gpfx_cross_entropy(odd_model, even_lines)
h_full_on_full, n_ff = sfx_gpfx_cross_entropy(full_model, line_collapsed)

print(f"\n  Cross-entropy H_cross(gpfx | sfx):")
print(f"  Full on Full: {h_full_on_full:.4f} bits")
print(f"  Even on Odd:  {h_even_on_odd:.4f} bits")
print(f"  Odd on Even:  {h_odd_on_even:.4f} bits")

mi_xval_eo = H_gpfx_marginal - h_even_on_odd
mi_xval_oe = H_gpfx_marginal - h_odd_on_even
print(f"\n  Cross-validated MI:")
print(f"  Even→Odd: {mi_xval_eo:.4f} bits")
print(f"  Odd→Even: {mi_xval_oe:.4f} bits")
print(f"  Mean:     {(mi_xval_eo + mi_xval_oe)/2:.4f} bits")
print(f"  Within:   {full_mi:.4f} bits")
print(f"  Retention: {(mi_xval_eo + mi_xval_oe)/2 / full_mi * 100:.1f}%")

# Shuffled null for cross-validated MI
n_shuf = 200
shuf_xval_mi = []
for trial in range(n_shuf):
    # Shuffle within each line
    shuf_even = [list(seq) for seq in even_lines]
    shuf_odd = [list(seq) for seq in odd_lines]
    for seq in shuf_even:
        random.shuffle(seq)
    for seq in shuf_odd:
        random.shuffle(seq)
    
    shuf_even_model = get_sfx_gpfx_model(shuf_even)
    h_se_on_odd, _ = sfx_gpfx_cross_entropy(shuf_even_model, odd_lines)
    shuf_xval_mi.append(H_gpfx_marginal - h_se_on_odd)

z_morph = ((mi_xval_eo + mi_xval_oe)/2 - np.mean(shuf_xval_mi)) / np.std(shuf_xval_mi)
print(f"\n  Shuffled cross-val MI: {np.mean(shuf_xval_mi):.4f} ± {np.std(shuf_xval_mi):.4f}")
print(f"  z-score: {z_morph:.1f}")


# ══════════════════════════════════════════════════════════════════
# 49b: CROSS-VALIDATED CHARACTER MI
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("B: CROSS-VALIDATED CHARACTER MI")
print("    Does last_char→first_char MI generalize?")
print("=" * 70)

def get_char_model(line_set):
    """Build last_char→first_char model from lines"""
    bg = Counter()
    lc_counts = Counter()
    fc_counts = Counter()
    total = 0
    for seq in line_set:
        for i in range(len(seq) - 1):
            if seq[i] and seq[i+1]:
                lc = seq[i][-1]
                fc = seq[i+1][0]
                bg[(lc, fc)] += 1
                lc_counts[lc] += 1
                fc_counts[fc] += 1
                total += 1
    return bg, lc_counts, fc_counts, total

# Use original words for character-level test
even_orig = [[w for w in lines[i]['words']] for i in range(0, len(lines), 2)]
odd_orig = [[w for w in lines[i]['words']] for i in range(1, len(lines), 2)]
all_orig = [[w for w in line['words']] for line in lines]

even_char = get_char_model(even_orig)
odd_char = get_char_model(odd_orig)
full_char = get_char_model(all_orig)

# MI within-sample
def char_mi(bg, lc_counts, fc_counts, total):
    mi = 0.0
    for (lc, fc), c in bg.items():
        p_j = c / total
        p_lc = lc_counts[lc] / total
        p_fc = fc_counts[fc] / total
        if p_lc > 0 and p_fc > 0:
            mi += p_j * math.log2(p_j / (p_lc * p_fc))
    return mi

full_char_mi = char_mi(*full_char)
even_char_mi = char_mi(*even_char)
odd_char_mi = char_mi(*odd_char)
print(f"\n  Within-sample MI(last_char, first_char):")
print(f"  Full: {full_char_mi:.4f}")
print(f"  Even: {even_char_mi:.4f}")
print(f"  Odd:  {odd_char_mi:.4f}")

# Cross-entropy
all_fc_counts = Counter()
for seq in all_orig:
    for i in range(len(seq) - 1):
        if seq[i+1]:
            all_fc_counts[seq[i+1][0]] += 1
H_fc_marg = compute_H(all_fc_counts, sum(all_fc_counts.values()))

def char_cross_entropy(train_bg, train_lc, train_total, test_lines):
    n_chars = len(set(list(train_lc.keys()) + list(all_fc_counts.keys())))
    log_sum = 0.0
    n = 0
    for seq in test_lines:
        for i in range(len(seq) - 1):
            if seq[i] and seq[i+1]:
                lc = seq[i][-1]
                fc = seq[i+1][0]
                count = train_bg.get((lc, fc), 0)
                lc_total = train_lc.get(lc, 0)
                prob = (count + 1) / (lc_total + n_chars)
                log_sum += math.log2(prob)
                n += 1
    return -log_sum / n if n > 0 else 0

h_eo = char_cross_entropy(even_char[0], even_char[1], even_char[3], odd_orig)
h_oe = char_cross_entropy(odd_char[0], odd_char[1], odd_char[3], even_orig)

mi_char_xval = H_fc_marg - (h_eo + h_oe) / 2
print(f"\n  Cross-validated character MI: {mi_char_xval:.4f}")
print(f"  Within-sample:                {full_char_mi:.4f}")
print(f"  Retention:                    {mi_char_xval/full_char_mi*100:.1f}%")


# ══════════════════════════════════════════════════════════════════
# 49c: LINE BOUNDARY TEST
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("C: LINE BOUNDARY TEST")
print("    Within-line vs cross-line transitions")
print("=" * 70)

# Within-line transitions: adjacent words in same line (already have these)
within_sfx_gpfx = Counter()
within_total = 0
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        sfx = get_suffix(seq[i])
        gpfx = get_gram_prefix(seq[i+1])
        within_sfx_gpfx[(sfx, gpfx)] += 1
        within_total += 1

# Cross-line transitions: last word of line_i → first word of line_{i+1}
cross_sfx_gpfx = Counter()
cross_total = 0
for i in range(len(line_collapsed) - 1):
    seq1 = line_collapsed[i]
    seq2 = line_collapsed[i+1]
    if seq1 and seq2:
        sfx = get_suffix(seq1[-1])
        gpfx = get_gram_prefix(seq2[0])
        cross_sfx_gpfx[(sfx, gpfx)] += 1
        cross_total += 1

# Compute MI for each
within_sfx = Counter()
within_gpfx = Counter()
for (sfx, gpfx), c in within_sfx_gpfx.items():
    within_sfx[sfx] += c
    within_gpfx[gpfx] += c

cross_sfx = Counter()
cross_gpfx = Counter()
for (sfx, gpfx), c in cross_sfx_gpfx.items():
    cross_sfx[sfx] += c
    cross_gpfx[gpfx] += c

within_mi = compute_morph_mi(within_sfx_gpfx, within_sfx, within_gpfx, within_total)
cross_mi = compute_morph_mi(cross_sfx_gpfx, cross_sfx, cross_gpfx, cross_total)

print(f"\n  Within-line MI(sfx→gpfx):  {within_mi:.4f} bits (N={within_total})")
print(f"  Cross-line MI(sfx→gpfx):   {cross_mi:.4f} bits (N={cross_total})")
print(f"  Cross/within ratio:        {cross_mi/within_mi:.3f}")

# Shuffled null for cross-line
n_shuf = 200
shuf_cross_mi = []
for trial in range(n_shuf):
    indices = list(range(len(line_collapsed)))
    random.shuffle(indices)
    shuf_bg = Counter()
    shuf_sfx = Counter()
    shuf_gpfx = Counter()
    shuf_total = 0
    for i in range(len(indices) - 1):
        seq1 = line_collapsed[indices[i]]
        seq2 = line_collapsed[indices[i+1]]
        if seq1 and seq2:
            sfx = get_suffix(seq1[-1])
            gpfx = get_gram_prefix(seq2[0])
            shuf_bg[(sfx, gpfx)] += 1
            shuf_sfx[sfx] += 1
            shuf_gpfx[gpfx] += 1
            shuf_total += 1
    mi_s = compute_morph_mi(shuf_bg, shuf_sfx, shuf_gpfx, shuf_total)
    shuf_cross_mi.append(mi_s)

z_cross = (cross_mi - np.mean(shuf_cross_mi)) / np.std(shuf_cross_mi)
print(f"\n  Shuffled cross-line MI: {np.mean(shuf_cross_mi):.4f} ± {np.std(shuf_cross_mi):.4f}")
print(f"  Cross-line z-score:    {z_cross:.1f}")

# Within vs cross for specific transitions
print(f"\n  Key transitions, within vs cross:")
print(f"  {'Sfx→Gpfx':>15} {'Within%':>10} {'Cross%':>10} {'Ratio':>10}")
for sfx in ['dy', 'y', 'X', 'aiin', 'ol']:
    for gpfx in ['qo', 'X', 'o', 'd']:
        w = within_sfx_gpfx.get((sfx, gpfx), 0) / max(within_sfx.get(sfx, 1), 1) * 100
        c = cross_sfx_gpfx.get((sfx, gpfx), 0) / max(cross_sfx.get(sfx, 1), 1) * 100
        if w > 2 or c > 2:
            ratio = c / w if w > 0 else 0
            print(f"  {sfx+'→'+gpfx:>15} {w:>9.1f}% {c:>9.1f}% {ratio:>9.2f}x")

# Character-level cross-line test
within_char = Counter()
cross_char = Counter()
for seq in all_orig:
    for i in range(len(seq) - 1):
        if seq[i] and seq[i+1]:
            within_char[(seq[i][-1], seq[i+1][0])] += 1

for i in range(len(lines) - 1):
    w1 = lines[i]['words']
    w2 = lines[i+1]['words']
    if w1 and w2:
        cross_char[(w1[-1][-1], w2[0][0])] += 1

# MI for each
wc_lc = Counter()
wc_fc = Counter()
for (lc, fc), c in within_char.items():
    wc_lc[lc] += c
    wc_fc[fc] += c
wc_total = sum(within_char.values())

cc_lc = Counter()
cc_fc = Counter()
for (lc, fc), c in cross_char.items():
    cc_lc[lc] += c
    cc_fc[fc] += c
cc_total = sum(cross_char.values())

within_char_mi = char_mi(within_char, wc_lc, wc_fc, wc_total)
cross_char_mi = char_mi(cross_char, cc_lc, cc_fc, cc_total)
print(f"\n  Character-level:")
print(f"  Within-line MI(last,first): {within_char_mi:.4f} (N={wc_total})")
print(f"  Cross-line MI(last,first):  {cross_char_mi:.4f} (N={cc_total})")
print(f"  Cross/within ratio:         {cross_char_mi/within_char_mi:.3f}")


# ══════════════════════════════════════════════════════════════════
# 49d: JACKKNIFE STABILITY
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("D: JACKKNIFE STABILITY")
print("    Do key findings survive leave-10%-out?")
print("=" * 70)

n_jackknife = 20
jack_fraction = 0.1

# For each jackknife sample: compute morph MI, char MI, and L→R asymmetry
jack_morph_mi = []
jack_char_mi = []
jack_lr_asym = []

for trial in range(n_jackknife):
    # Leave out 10% of lines
    n_leave = int(len(line_collapsed) * jack_fraction)
    leave_out = set(random.sample(range(len(line_collapsed)), n_leave))
    jack_lines = [line_collapsed[i] for i in range(len(line_collapsed)) if i not in leave_out]
    jack_orig = [[w for w in lines[i]['words']] for i in range(len(lines)) if i not in leave_out]
    
    # Morph MI
    jack_model = get_sfx_gpfx_model(jack_lines)
    jack_morph_mi.append(compute_morph_mi(*jack_model))
    
    # Char MI
    jack_char_model = get_char_model(jack_orig)
    jack_char_mi.append(char_mi(*jack_char_model))
    
    # L→R asymmetry: H(gpfx|sfx) vs H(sfx|gpfx)
    jbg = jack_model[0]
    j_sfx = jack_model[1]
    j_gpfx = jack_model[2]
    j_total = jack_model[3]
    
    # H(gpfx|sfx) = H(sfx,gpfx) - H(sfx)
    h_joint = 0.0
    for c in jbg.values():
        if c > 0:
            p = c / j_total
            h_joint -= p * math.log2(p)
    h_sfx = compute_H(j_sfx, j_total)
    h_gpfx = compute_H(j_gpfx, j_total)
    h_gpfx_given_sfx = h_joint - h_sfx
    h_sfx_given_gpfx = h_joint - h_gpfx
    # L→R means sfx predicts gpfx: MI from sfx side
    # Asymmetry = H(sfx|gpfx) - H(gpfx|sfx) > 0 means L→R
    jack_lr_asym.append(h_sfx_given_gpfx - h_gpfx_given_sfx)

print(f"\n  Jackknife results (leave {jack_fraction*100:.0f}% out, {n_jackknife} trials):")
print(f"\n  Morph MI(sfx→gpfx):")
print(f"    Full: {full_mi:.4f}")
print(f"    Jack: {np.mean(jack_morph_mi):.4f} ± {np.std(jack_morph_mi):.4f}")
print(f"    Min:  {np.min(jack_morph_mi):.4f}")

print(f"\n  Char MI(last,first):")
print(f"    Full: {full_char_mi:.4f}")
print(f"    Jack: {np.mean(jack_char_mi):.4f} ± {np.std(jack_char_mi):.4f}")
print(f"    Min:  {np.min(jack_char_mi):.4f}")

print(f"\n  L→R asymmetry (H(sfx|gpfx) - H(gpfx|sfx)):")
print(f"    Jack: {np.mean(jack_lr_asym):.4f} ± {np.std(jack_lr_asym):.4f}")
print(f"    All > 0? {all(a > 0 for a in jack_lr_asym)} (L→R in all samples)")


# ══════════════════════════════════════════════════════════════════
# 49e: THE qo-WORD NETWORK
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("E: THE qo-WORD NETWORK")
print("    Among -dy→qo transitions, is qo-word predicted by predecessor?")
print("=" * 70)

# Collect all -dy → qo-word transitions
dy_to_qo = Counter()  # (dy_word, qo_word) -> count
dy_word_counts = Counter()  # dy_word -> count (as w1 in dy→qo)
qo_word_counts = Counter()  # qo_word -> count (as w2 in dy→qo)
dy_qo_total = 0

for seq in line_collapsed:
    for i in range(len(seq) - 1):
        w1, w2 = seq[i], seq[i+1]
        if get_suffix(w1) == 'dy' and get_gram_prefix(w2) == 'qo':
            dy_to_qo[(w1, w2)] += 1
            dy_word_counts[w1] += 1
            qo_word_counts[w2] += 1
            dy_qo_total += 1

print(f"\n  -dy → qo- transitions: {dy_qo_total}")
print(f"  Unique -dy words: {len(dy_word_counts)}")
print(f"  Unique qo- words: {len(qo_word_counts)}")

# MI(dy_word, qo_word) within this subset
mi_dy_qo = 0.0
for (w1, w2), c in dy_to_qo.items():
    p_j = c / dy_qo_total
    p_w1 = dy_word_counts[w1] / dy_qo_total
    p_w2 = qo_word_counts[w2] / dy_qo_total
    if p_w1 > 0 and p_w2 > 0:
        mi_dy_qo += p_j * math.log2(p_j / (p_w1 * p_w2))

h_qo_word = compute_H(qo_word_counts, dy_qo_total)
h_dy_word = compute_H(dy_word_counts, dy_qo_total)
print(f"\n  H(-dy word) = {h_dy_word:.3f}")
print(f"  H(qo- word) = {h_qo_word:.3f}")
print(f"  MI(dy_word, qo_word) = {mi_dy_qo:.4f}")
print(f"  MI/H(qo) = {mi_dy_qo/h_qo_word:.4f}")

# Shuffled null
n_shuf = 200
shuf_mi_dyqo = []
for trial in range(n_shuf):
    w1_list = []
    w2_list = []
    for (w1, w2), c in dy_to_qo.items():
        w1_list.extend([w1] * c)
        w2_list.extend([w2] * c)
    random.shuffle(w2_list)
    shuf_bg = Counter(zip(w1_list, w2_list))
    mi_s = 0.0
    for (w1, w2), c in shuf_bg.items():
        p_j = c / dy_qo_total
        p_w1 = dy_word_counts[w1] / dy_qo_total
        p_w2 = qo_word_counts[w2] / dy_qo_total
        if p_w1 > 0 and p_w2 > 0:
            mi_s += p_j * math.log2(p_j / (p_w1 * p_w2))
    shuf_mi_dyqo.append(mi_s)

excess_dyqo = mi_dy_qo - np.mean(shuf_mi_dyqo)
z_dyqo = excess_dyqo / np.std(shuf_mi_dyqo)
print(f"\n  Shuffled MI: {np.mean(shuf_mi_dyqo):.4f} ± {np.std(shuf_mi_dyqo):.4f}")
print(f"  Excess: {excess_dyqo:.4f}")
print(f"  z-score: {z_dyqo:.1f}")

# Top specific -dy→qo transitions
print(f"\n  Top -dy → qo- word pairs:")
top_dyqo = dy_to_qo.most_common(15)
print(f"  {'DY word':>15} {'QO word':>15} {'Count':>8} {'O/E':>8}")
for (w1, w2), c in top_dyqo:
    expected = dy_word_counts[w1] * qo_word_counts[w2] / dy_qo_total
    oe = c / expected if expected > 0 else 0
    print(f"  {w1:>15} {w2:>15} {c:>8} {oe:>7.2f}x")

# Is it just self-repetition? (same suffix pair, same stem)
# Or does the specific -dy word predict which qo- word follows?
# Test: for each common -dy word, what's H(qo_word | this_dy_word)?
print(f"\n  H(qo_word | dy_word) for common -dy words:")
for w, n in dy_word_counts.most_common(10):
    succ = Counter()
    for (w1, w2), c in dy_to_qo.items():
        if w1 == w:
            succ[w2] += c
    h = compute_H(succ, n)
    top = succ.most_common(3)
    top_str = ", ".join(f"{w2}({c})" for w2, c in top)
    print(f"  {w:>15} N={n:>4}, H={h:.3f}, top: {top_str}")

print("\n" + "=" * 70)
print("line_boundary_generalization COMPLETE")
print("=" * 70)
