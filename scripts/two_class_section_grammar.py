#!/usr/bin/env python3
"""
THE TWO-CLASS SYSTEM AND SECTION GRAMMAR
=====================================================

syntactic_grammar_map found sfx→pfx is the dominant syntax channel (z=116.7).
The transition matrix reveals a clear binary pattern in suffixes:

  CLASS A (-dy, -y, -X): attract following qo- words (2.2×, 1.5×)
  CLASS B (-aiin, -ol, -al, -ain, -ar, -or, -iin, -in): attract sh/ch/d

This looks like a genuine word-class system. But we MUST test:
1. Does this binary split capture most of the sfx→pfx MI, or is it crude?
2. Is the bio section's 2× higher sfx→pfx MI a real grammatical difference
   or just different vocabulary frequencies?
3. Does the famous "chol daiin" bigram have genuine synergy, or is it
   just (ch→d) × (ol→aiin)?
4. Is there information structure WITHIN lines — do certain positions
   carry more syntactic weight?

Sub-analyses:
  A) TWO-CLASS MODEL — Binarize suffixes into A/B. How much MI is
       captured? Compare to the full 11-value suffix model.

  B) SECTION-SPECIFIC GRAMMAR — Train transition matrices on each
       section separately. Test whether a section's own matrix predicts
       its data better than the global matrix (log-likelihood ratio).
       If NOT → universal grammar. If YES → section-specific rules.

  C) "chol daiin" SYNERGY — Test whether (ch,ol)→(d,aiin) exceeds
       (ch→d)×(ol→aiin). More generally: for top class bigrams, how
       much is the combined-class ratio above the product of independent
       prefix and suffix ratios?

  D) POSITIONAL INFORMATION PROFILE — Entropy of prefix and suffix
       at each position within the line. Do certain positions (first,
       last, penultimate) carry more or less variety?

  E) PREDICTIVE ASYMMETRY — Does left context predict right context
       better than right predicts left? In natural language, word order
       is directional. If MI(word_i→word_{i+1}) ≈ MI(word_{i+1}→word_i)
       then ordering is symmetric (not clearly directional).
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_mi, get_collapsed, get_prefix, get_suffix, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(42)
np.random.seed(42)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']





def entropy(x_arr):
    N = len(x_arr)
    if N == 0: return 0.0
    counts = Counter(x_arr)
    h = 0.0
    for c in counts.values():
        p = c / N
        if p > 0:
            h -= p * math.log2(p)
    return h


# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════

FOLIO_DIR = Path("folios")



def annotate_lines(lines):
    for line in lines:
        n = len(line['words'])
        line['collapsed'] = [get_collapsed(w) for w in line['words']]
        line['pfx'] = [get_prefix(c) for c in line['collapsed']]
        line['sfx'] = [get_suffix(c) for c in line['collapsed']]
        line['pos'] = [i / max(n - 1, 1) for i in range(n)]
    return lines


print("Loading lines...")
lines = load_lines()
lines = annotate_lines(lines)
total_words = sum(len(l['words']) for l in lines)
print(f"  {len(lines)} lines, {total_words} word tokens")


# ══════════════════════════════════════════════════════════════════
# 42a: TWO-CLASS MODEL
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("A: TWO-CLASS SUFFIX MODEL")
print("    CLASS A (attract qo): dy, y, X")
print("    CLASS B (attract sh/ch): aiin, ain, iin, in, ar, or, al, ol")
print("    How much of the sfx→pfx MI does this binary capture?")
print("=" * 70)

CLASS_A = {'dy', 'y', 'X'}
CLASS_B = {'aiin', 'ain', 'iin', 'in', 'ar', 'or', 'al', 'ol'}

def sfx_class(s):
    return 'A' if s in CLASS_A else 'B'

# Build pair arrays
sfx_i_arr, pfx_j_arr = [], []
cls_i_arr, pfx_j_binary = [], []

for line in lines:
    for i in range(len(line['pfx']) - 1):
        sfx_i_arr.append(line['sfx'][i])
        pfx_j_arr.append(line['pfx'][i + 1])
        cls_i_arr.append(sfx_class(line['sfx'][i]))

mi_full = compute_mi(sfx_i_arr, pfx_j_arr)
mi_binary = compute_mi(cls_i_arr, pfx_j_arr)

# Also test: binarize the PREFIX side
# PFX_GROUP_1 (attracted by A): qo, so, do, q, lch, lsh
# PFX_GROUP_2 (attracted by B): sh, ch, d, o?
# Let data decide: which prefixes have ratio > 1 after Class A?
print(f"\n  MI(sfx→pfx) full 11 classes: {mi_full:.4f}")
print(f"  MI(sfx_class→pfx) binary A/B: {mi_binary:.4f}")
print(f"  Binary captures {mi_binary/mi_full*100:.1f}% of full MI")

# Let's also try a 3-class model: separate X from dy/y
def sfx_class3(s):
    if s in ('dy', 'y'): return 'A'
    if s == 'X': return 'M'  # Middle/mixed
    return 'B'

cls3_arr = [sfx_class3(sfx_i_arr[i]) for i in range(len(sfx_i_arr))]
mi_3class = compute_mi(cls3_arr, pfx_j_arr)
print(f"  MI(sfx_3class→pfx) A/M/B: {mi_3class:.4f} ({mi_3class/mi_full*100:.1f}%)")

# Permutation test for binary model
null_binary = []
for _ in range(500):
    shuf = []
    for line in lines:
        n = len(line['pfx'])
        perm = list(range(n))
        random.shuffle(perm)
        for i in range(n - 1):
            shuf.append((sfx_class(line['sfx'][perm[i]]), line['pfx'][perm[i+1]]))
    si = [s for s, _ in shuf]
    pj = [p for _, p in shuf]
    null_binary.append(compute_mi(si, pj))

z_bin = (mi_binary - np.mean(null_binary)) / max(np.std(null_binary), 1e-10)
print(f"\n  Binary model z-score: {z_bin:.1f} (null={np.mean(null_binary):.4f}±{np.std(null_binary):.4f})")

# Show what each class predicts
print(f"\n  Class A suffix → following prefix distribution:")
a_pfxs = [pfx_j_arr[i] for i in range(len(cls_i_arr)) if cls_i_arr[i] == 'A']
b_pfxs = [pfx_j_arr[i] for i in range(len(cls_i_arr)) if cls_i_arr[i] == 'B']
all_pfxs = pfx_j_arr

a_cts = Counter(a_pfxs); b_cts = Counter(b_pfxs); all_cts = Counter(all_pfxs)
n_a = len(a_pfxs); n_b = len(b_pfxs); n_all = len(all_pfxs)

print(f"  {'Prefix':<8} {'After A':>8} {'After B':>8} {'Overall':>8} {'A ratio':>8} {'B ratio':>8}")
for p in ['qo','sh','ch','o','d','X','y','l']:
    ra = a_cts[p]/n_a if n_a > 0 else 0
    rb = b_cts[p]/n_b if n_b > 0 else 0
    rall = all_cts[p]/n_all if n_all > 0 else 0
    ratio_a = ra/rall if rall > 0 else 0
    ratio_b = rb/rall if rall > 0 else 0
    print(f"  {p:<8} {ra:>8.3f} {rb:>8.3f} {rall:>8.3f} {ratio_a:>8.2f} {ratio_b:>8.2f}")


# ══════════════════════════════════════════════════════════════════
# 42b: SECTION-SPECIFIC GRAMMAR
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("B: SECTION-SPECIFIC GRAMMAR")
print("    Does each section have its own transition probabilities,")
print("    or is one global matrix sufficient?")
print("=" * 70)

# Test: for each section, compute log-likelihood under:
#  H0: global transition matrix (trained on all data)
#  H1: section-specific matrix (trained on that section)
# Compare via LR test.

# Global model: P(pfx_j | sfx_i) = count(sfx_i, pfx_j) / count(sfx_i)
global_joint = Counter(zip(sfx_i_arr, pfx_j_arr))
global_sfx_cts = Counter(sfx_i_arr)
N_total = len(sfx_i_arr)

# Smoothed probability
def get_prob(joint_cts, marg_cts, key_pair, n_categories=13, alpha=0.5):
    """Laplace-smoothed conditional probability."""
    s, p = key_pair
    num = joint_cts.get((s, p), 0) + alpha
    denom = marg_cts.get(s, 0) + alpha * n_categories
    return num / denom

sections_to_test = ['text', 'herbal-A', 'bio', 'pharma']
print(f"\n  {'Section':<12} {'N pairs':>8} {'LL global':>12} {'LL local':>12} {'LR':>10} {'LR/N':>8}")
print(f"  {'-' * 62}")

for sec in sections_to_test:
    sec_lines = [l for l in lines if l['section'] == sec]
    sec_si, sec_pj = [], []
    for line in sec_lines:
        for i in range(len(line['pfx']) - 1):
            sec_si.append(line['sfx'][i])
            sec_pj.append(line['pfx'][i + 1])

    n_sec = len(sec_si)
    sec_joint = Counter(zip(sec_si, sec_pj))
    sec_sfx_cts = Counter(sec_si)

    # Log-likelihood under global model
    ll_global = 0
    for i in range(n_sec):
        p = get_prob(global_joint, global_sfx_cts, (sec_si[i], sec_pj[i]))
        ll_global += math.log2(p)

    # Log-likelihood under section-specific model
    ll_local = 0
    for i in range(n_sec):
        p = get_prob(sec_joint, sec_sfx_cts, (sec_si[i], sec_pj[i]))
        ll_local += math.log2(p)

    lr = ll_local - ll_global
    print(f"  {sec:<12} {n_sec:>8} {ll_global:>12.1f} {ll_local:>12.1f} {lr:>10.1f} {lr/n_sec:>8.4f}")

# Null: if we split data randomly into same-sized groups, how much LR do we get?
# This controls for overfitting
print(f"\n  Null test: random splits of same size as each section:")
for sec in sections_to_test:
    sec_lines = [l for l in lines if l['section'] == sec]
    sec_si, sec_pj = [], []
    for line in sec_lines:
        for i in range(len(line['pfx']) - 1):
            sec_si.append(line['sfx'][i])
            sec_pj.append(line['pfx'][i + 1])
    n_sec = len(sec_si)

    null_lrs = []
    for _ in range(100):
        # Random subset of all pairs, same size
        idxs = random.sample(range(N_total), min(n_sec, N_total))
        rand_si = [sfx_i_arr[i] for i in idxs]
        rand_pj = [pfx_j_arr[i] for i in idxs]
        rand_joint = Counter(zip(rand_si, rand_pj))
        rand_sfx_cts = Counter(rand_si)

        ll_g = sum(math.log2(get_prob(global_joint, global_sfx_cts, (rand_si[i], rand_pj[i])))
                    for i in range(len(rand_si)))
        ll_l = sum(math.log2(get_prob(rand_joint, rand_sfx_cts, (rand_si[i], rand_pj[i])))
                    for i in range(len(rand_si)))
        null_lrs.append(ll_l - ll_g)

    sec_joint_real = Counter(zip(sec_si, sec_pj))
    sec_sfx_cts_real = Counter(sec_si)
    ll_g_real = sum(math.log2(get_prob(global_joint, global_sfx_cts, (sec_si[i], sec_pj[i])))
                    for i in range(n_sec))
    ll_l_real = sum(math.log2(get_prob(sec_joint_real, sec_sfx_cts_real, (sec_si[i], sec_pj[i])))
                    for i in range(n_sec))
    obs_lr = ll_l_real - ll_g_real

    nm, ns = np.mean(null_lrs), np.std(null_lrs)
    z = (obs_lr - nm) / max(ns, 1e-10)
    print(f"  {sec:<12} LR={obs_lr:.1f}, null_LR={nm:.1f}±{ns:.1f}, excess={obs_lr-nm:.1f}, z={z:.1f}")


# ══════════════════════════════════════════════════════════════════
# 42c: "chol daiin" SYNERGY TEST
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("C: SYNERGY TEST — Does (pfx,sfx) class predict better than")
print("    independent prefix × suffix for specific bigrams?")
print("=" * 70)

# For each frequent class bigram, compute:
#   observed_ratio = P(cls_j | cls_i) / P(cls_j)
#   expected_from_parts = [P(pfx_j|pfx_i)/P(pfx_j)] × [P(sfx_j|sfx_i)/P(sfx_j)]
# If observed >> expected_from_parts: genuine synergy
# If observed ≈ expected_from_parts: no synergy (decomposable)

pfx_i_all, pfx_j_all, sfx_i_all, sfx_j_all = [], [], [], []
cls_i_all, cls_j_all = [], []
for line in lines:
    for i in range(len(line['pfx']) - 1):
        pfx_i_all.append(line['pfx'][i])
        pfx_j_all.append(line['pfx'][i + 1])
        sfx_i_all.append(line['sfx'][i])
        sfx_j_all.append(line['sfx'][i + 1])
        cls_i_all.append((line['pfx'][i], line['sfx'][i]))
        cls_j_all.append((line['pfx'][i + 1], line['sfx'][i + 1]))

N_all = len(pfx_i_all)

# Build conditional probability tables
pfx_given_pfx = defaultdict(Counter)
sfx_given_sfx = defaultdict(Counter)
cls_given_cls = defaultdict(Counter)
pfx_j_cts = Counter(pfx_j_all)
sfx_j_cts = Counter(sfx_j_all)
cls_j_cts = Counter(cls_j_all)

for i in range(N_all):
    pfx_given_pfx[pfx_i_all[i]][pfx_j_all[i]] += 1
    sfx_given_sfx[sfx_i_all[i]][sfx_j_all[i]] += 1
    cls_given_cls[cls_i_all[i]][cls_j_all[i]] += 1

# Test specific famous bigrams
test_bigrams = [
    (('ch', 'ol'), ('d', 'aiin'), '"chol daiin"'),
    (('sh', 'dy'), ('qo', 'dy'), '"shdy qody"'),
    (('sh', 'y'), ('qo', 'ain'), '"shy qoain"'),
    (('o', 'X'), ('X', 'iin'), '"oX Xiin"'),
    (('sh', 'dy'), ('qo', 'aiin'), '"shdy qoaiin"'),
    (('ch', 'ol'), ('ch', 'ol'), '"chol chol"'),
    (('qo', 'dy'), ('qo', 'dy'), '"qody qody"'),
    (('o', 'dy'), ('qo', 'dy'), '"ody qody"'),
    (('ch', 'dy'), ('qo', 'ain'), '"chdy qoain"'),
    (('d', 'aiin'), ('ch', 'ol'), '"daiin chol"'),
]

print(f"\n  {'Bigram':<18} {'Count':>6} {'CLS ratio':>10} {'PFX×SFX':>10} {'Synergy':>8}")
print(f"  {'-' * 56}")

for cls_a, cls_b, label in test_bigrams:
    # Class ratio: P(cls_b | cls_a) / P(cls_b)
    cnt_ab = cls_given_cls[cls_a][cls_b]
    cnt_a = sum(cls_given_cls[cls_a].values())
    p_b = cls_j_cts[cls_b] / N_all if N_all > 0 else 1
    cls_ratio = (cnt_ab / cnt_a / p_b) if cnt_a > 0 and p_b > 0 else 0

    # Independent prefix ratio
    pfx_a, sfx_a = cls_a
    pfx_b, sfx_b = cls_b
    cnt_pfx_a = sum(pfx_given_pfx[pfx_a].values())
    pfx_ratio = (pfx_given_pfx[pfx_a][pfx_b] / cnt_pfx_a / (pfx_j_cts[pfx_b] / N_all)) if cnt_pfx_a > 0 and pfx_j_cts[pfx_b] > 0 else 1

    cnt_sfx_a = sum(sfx_given_sfx[sfx_a].values())
    sfx_ratio = (sfx_given_sfx[sfx_a][sfx_b] / cnt_sfx_a / (sfx_j_cts[sfx_b] / N_all)) if cnt_sfx_a > 0 and sfx_j_cts[sfx_b] > 0 else 1

    product_ratio = pfx_ratio * sfx_ratio
    synergy = cls_ratio / product_ratio if product_ratio > 0 else 0

    if cnt_ab >= 5:
        print(f"  {label:<18} {cnt_ab:>6} {cls_ratio:>10.2f} {product_ratio:>10.2f} {synergy:>8.2f}")
    else:
        print(f"  {label:<18} {cnt_ab:>6}   (too few)")

print(f"\n  Synergy > 1.5: genuine interaction (combined class matters)")
print(f"  Synergy ≈ 1.0: decomposable into independent prefix + suffix effects")
print(f"  Synergy < 0.7: combined class is LESS likely than parts predict (anti-synergy)")


# ══════════════════════════════════════════════════════════════════
# 42d: POSITIONAL INFORMATION PROFILE
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("D: POSITIONAL INFORMATION PROFILE")
print("    Entropy of prefix/suffix at each absolute position.")
print("    Does position 0 (line-initial) or position -1 (line-final)")
print("    carry more or less variety than interior positions?")
print("=" * 70)

# Group words by absolute position (0, 1, 2, ..., -2, -1)
# For clarity, use position from start AND from end
by_pos_start = defaultdict(lambda: {'pfx': [], 'sfx': []})
by_pos_end = defaultdict(lambda: {'pfx': [], 'sfx': []})

for line in lines:
    n = len(line['pfx'])
    for i in range(n):
        by_pos_start[min(i, 6)]['pfx'].append(line['pfx'][i])
        by_pos_start[min(i, 6)]['sfx'].append(line['sfx'][i])
        from_end = n - 1 - i
        by_pos_end[min(from_end, 6)]['pfx'].append(line['pfx'][i])
        by_pos_end[min(from_end, 6)]['sfx'].append(line['sfx'][i])

print(f"\n  Position (from start):")
print(f"  {'Pos':>4} {'N':>7} {'H(pfx)':>8} {'H(sfx)':>8} {'Top pfx':>12} {'Top sfx':>12}")
print(f"  {'-' * 55}")
for pos in range(7):
    d = by_pos_start[pos]
    n = len(d['pfx'])
    hp = entropy(d['pfx'])
    hs = entropy(d['sfx'])
    tp = Counter(d['pfx']).most_common(1)[0] if d['pfx'] else ('', 0)
    ts = Counter(d['sfx']).most_common(1)[0] if d['sfx'] else ('', 0)
    label = f"{pos}" if pos < 6 else "6+"
    print(f"  {label:>4} {n:>7} {hp:>8.3f} {hs:>8.3f} {tp[0]:>6}({tp[1]/n*100:.0f}%) {ts[0]:>6}({ts[1]/n*100:.0f}%)")

print(f"\n  Position (from end):")
print(f"  {'Pos':>4} {'N':>7} {'H(pfx)':>8} {'H(sfx)':>8} {'Top pfx':>12} {'Top sfx':>12}")
print(f"  {'-' * 55}")
for pos in range(7):
    d = by_pos_end[pos]
    n = len(d['pfx'])
    hp = entropy(d['pfx'])
    hs = entropy(d['sfx'])
    tp = Counter(d['pfx']).most_common(1)[0] if d['pfx'] else ('', 0)
    ts = Counter(d['sfx']).most_common(1)[0] if d['sfx'] else ('', 0)
    label = f"-{pos}" if pos > 0 else "last"
    print(f"  {label:>4} {n:>7} {hp:>8.3f} {hs:>8.3f} {tp[0]:>6}({tp[1]/n*100:.0f}%) {ts[0]:>6}({ts[1]/n*100:.0f}%)")


# ══════════════════════════════════════════════════════════════════
# 42e: PREDICTIVE ASYMMETRY
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("E: PREDICTIVE ASYMMETRY")
print("    Is MI(word_i→word_{i+1}) symmetric, or does one direction")
print("    carry more information? In natural language, left-to-right")
print("    and right-to-left prediction differ (head-directionality).")
print("=" * 70)

# MI is symmetric: MI(X;Y) = MI(Y;X)
# But CONDITIONAL entropy is not: H(Y|X) ≠ H(X|Y)
# The informative measure: H(pfx_j | pfx_i) vs H(pfx_i | pfx_j)
# If H(Y|X) < H(X|Y) → X predicts Y better than Y predicts X → left-to-right

h_pfx = entropy(pfx_i_all)
h_sfx = entropy(sfx_i_all)

# H(pfx_j | pfx_i) = H(pfx_i, pfx_j) - H(pfx_i)
h_pfx_pair = entropy(list(zip(pfx_i_all, pfx_j_all)))
h_pfxj_given_pfxi = h_pfx_pair - entropy(pfx_i_all)
h_pfxi_given_pfxj = h_pfx_pair - entropy(pfx_j_all)

h_sfx_pair = entropy(list(zip(sfx_i_all, sfx_j_all)))
h_sfxj_given_sfxi = h_sfx_pair - entropy(sfx_i_all)
h_sfxi_given_sfxj = h_sfx_pair - entropy(sfx_j_all)

# Cross-feature: sfx_i → pfx_j
h_cross_pair = entropy(list(zip(sfx_i_all, pfx_j_all)))
h_pfxj_given_sfxi = h_cross_pair - entropy(sfx_i_all)
h_sfxi_given_pfxj = h_cross_pair - entropy(pfx_j_all)

# Reverse cross: pfx_i → sfx_j
h_rcross_pair = entropy(list(zip(pfx_i_all, sfx_j_all)))
h_sfxj_given_pfxi = h_rcross_pair - entropy(pfx_i_all)
h_pfxi_given_sfxj = h_rcross_pair - entropy(sfx_j_all)

print(f"\n  {'Direction':<35} {'H(target|source)':>16} {'H(source|target)':>16}")
print(f"  {'-' * 67}")
print(f"  {'pfx_i → pfx_j (same feature)':<35} {h_pfxj_given_pfxi:>16.4f} {h_pfxi_given_pfxj:>16.4f}")
print(f"  {'sfx_i → sfx_j (same feature)':<35} {h_sfxj_given_sfxi:>16.4f} {h_sfxi_given_sfxj:>16.4f}")
print(f"  {'sfx_i → pfx_j (cross-feature)':<35} {h_pfxj_given_sfxi:>16.4f} {h_sfxi_given_pfxj:>16.4f}")
print(f"  {'pfx_i → sfx_j (cross-feature)':<35} {h_sfxj_given_pfxi:>16.4f} {h_pfxi_given_sfxj:>16.4f}")

print(f"\n  Interpretation:")
print(f"  Lower H(target|source) = source is a better predictor of target")

# The key test: is the cross-feature asymmetry genuine?
# We found MI(sfx_i; pfx_j) >> MI(pfx_i; sfx_j)
# But MI is symmetric... the asymmetry must be in DIFFERENT PAIRS:
# MI(sfx_i; pfx_j) uses (sfx of word i, pfx of word i+1) — boundary adjacent
# MI(pfx_i; sfx_j) uses (pfx of word i, sfx of word i+1) — separated by two stems

# Better test: is FORWARD prediction better than BACKWARD prediction?
# Forward: word_i → word_{i+1}
# Backward: word_{i+1} → word_i (same pairs, just reversed labels)

# For forward: H(cls_j | cls_i)
# For backward: H(cls_i | cls_j)
h_cls_pair = entropy(list(zip(cls_i_all, cls_j_all)))
h_fwd = h_cls_pair - entropy(cls_i_all)
h_bwd = h_cls_pair - entropy(cls_j_all)
print(f"\n  Forward H(class_j | class_i): {h_fwd:.4f}")
print(f"  Backward H(class_i | class_j): {h_bwd:.4f}")
diff = h_fwd - h_bwd
print(f"  Asymmetry (fwd - bwd): {diff:+.4f}")
if abs(diff) < 0.01:
    print(f"  → Essentially SYMMETRIC — no clear head-directionality")
elif diff < 0:
    print(f"  → Forward (left→right) predicts BETTER — consistent with head-initial")
else:
    print(f"  → Backward (right→left) predicts better — consistent with head-final")


# ══════════════════════════════════════════════════════════════════
# SYNTHESIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("two_class_section_grammar SYNTHESIS")
print("=" * 70)

pct_captured = mi_binary / mi_full * 100

print(f"""
  42a: TWO-CLASS MODEL
    Binary A/B captures {pct_captured:.1f}% of sfx→pfx MI (z={z_bin:.1f})
    The suffix system has a clear binary backbone:
      Class A (dy/y/X) → attracts qo, repels sh/ch
      Class B (aiin/ol/al/ain/ar/or/iin/in) → attracts sh/ch/d, repels qo

  42b: SECTION-SPECIFIC GRAMMAR
    (See tables above — LR excess over random splits tests reality)

  42c: "chol daiin" SYNERGY
    (See table — synergy > 1.5 = genuine word-class effect)

  42d: POSITIONAL PROFILE
    (See entropy tables above)

  42e: PREDICTIVE ASYMMETRY
    Forward H(class) = {h_fwd:.4f}, Backward = {h_bwd:.4f}
    {'SYMMETRIC' if abs(diff) < 0.01 else 'ASYMMETRIC (' + ('left→right better' if diff < 0 else 'right→left better') + ')'}
""")

print("[two_class_section_grammar Complete]")
