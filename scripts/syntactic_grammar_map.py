#!/usr/bin/env python3
"""
MAPPING THE SYNTACTIC GRAMMAR
==========================================

syntax_artifact_attack proved syntax is real (z=80-128, survives all attacks).
Now we ask: what does the grammar LOOK like?

Key questions:
1. Do combined (prefix,suffix) class transitions exceed the sum of
   independent prefix and suffix effects? Or is "syntax" fully
   decomposable into separate prefix ordering + suffix ordering?
2. Does trigram structure exist beyond pairwise bigrams?
3. Is cross-line continuity real or marginal?
4. What are the "grammatical rules" — which specific transitions
   carry the MI, and do they generalize across sections?
5. After excluding the dominant sh→qo pattern, does the rest of
   the prefix ordering survive?

Sub-analyses:
  41a) INTERACTION TEST — Is syntax more than pfx + sfx independently?
       MI(class_i; class_j) vs MI(pfx_i; pfx_j) + MI(sfx_i; sfx_j)
       If class MI > sum: genuine prefix×suffix interaction (word classes)
       If class MI ≈ sum: no word classes, just independent channels

  41b) TRIGRAM TEST — Does 3-word structure exist beyond bigrams?
       MI(pfx_i; pfx_{i+2} | pfx_{i+1}) — conditional on the middle word,
       does the first word help predict the third?

  41c) CROSS-LINE SYNTAX — deeper test with proper controls
       Do lines chain, or is each line an independent utterance?

  41d) sh→qo DECOMPOSITION — Remove sh→qo; what's left?
       How much of the total prefix MI depends on this one pattern?

  41e) SUFFIX ORDERING GRAMMAR — Beyond runs
       Which different-suffix transitions are enriched? Is there a
       suffix "harmony" or "complement" system?
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





def cond_mi(x_arr, y_arr, z_arr):
    N = len(x_arr)
    if N == 0: return 0.0
    groups = defaultdict(list)
    for i in range(N):
        groups[z_arr[i]].append(i)
    cmi = 0.0
    for z_val, indices in groups.items():
        p_z = len(indices) / N
        xs = [x_arr[i] for i in indices]
        ys = [y_arr[i] for i in indices]
        cmi += p_z * compute_mi(xs, ys)
    return cmi


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
        line['cls'] = [(line['pfx'][i], line['sfx'][i]) for i in range(n)]
        line['pos'] = [i / max(n - 1, 1) for i in range(n)]
    return lines


print("Loading lines...")
lines = load_lines()
lines = annotate_lines(lines)
total_words = sum(len(l['words']) for l in lines)
print(f"  {len(lines)} lines, {total_words} word tokens")


# ══════════════════════════════════════════════════════════════════
# 41a: INTERACTION TEST — prefix×suffix synergy
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("41a: INTERACTION TEST")
print("    Is syntax more than independent prefix + suffix channels?")
print("    If MI(class→class) > MI(pfx→pfx) + MI(sfx→sfx),")
print("    there are genuine word classes (prefix×suffix combinations)")
print("    that matter beyond their individual components.")
print("=" * 70)

# Build pair arrays
pfx_i_arr, pfx_j_arr = [], []
sfx_i_arr, sfx_j_arr = [], []
cls_i_arr, cls_j_arr = [], []

for line in lines:
    for i in range(len(line['pfx']) - 1):
        pfx_i_arr.append(line['pfx'][i])
        pfx_j_arr.append(line['pfx'][i + 1])
        sfx_i_arr.append(line['sfx'][i])
        sfx_j_arr.append(line['sfx'][i + 1])
        cls_i_arr.append(line['cls'][i])
        cls_j_arr.append(line['cls'][i + 1])

mi_pfx = compute_mi(pfx_i_arr, pfx_j_arr)
mi_sfx = compute_mi(sfx_i_arr, sfx_j_arr)
mi_cls = compute_mi(cls_i_arr, cls_j_arr)

# The interaction is: MI(class) - MI(pfx) - MI(sfx)
# But this is not correct information-theoretically because class
# carries more information than either component. We need:
# MI(cls_i; cls_j) = MI(pfx_i,sfx_i; pfx_j,sfx_j)
#  = MI(pfx_i; pfx_j) + MI(sfx_i; sfx_j | pfx_i, pfx_j)
#    + MI(pfx_i; sfx_j | pfx_j) + ... (complex decomposition)
#
# Simpler: test MI(pfx_i; sfx_j) and MI(sfx_i; pfx_j) — cross-feature
# These capture "does the prefix of word i predict the suffix of word j?"

mi_pfx_to_sfx = compute_mi(pfx_i_arr, sfx_j_arr)  # pfx_i → sfx_j
mi_sfx_to_pfx = compute_mi(sfx_i_arr, pfx_j_arr)  # sfx_i → pfx_j

# And within-word: MI(pfx; sfx) for same word (morphology_artifact_test found this)
all_pfx = []
all_sfx = []
for line in lines:
    for i in range(len(line['pfx'])):
        all_pfx.append(line['pfx'][i])
        all_sfx.append(line['sfx'][i])
mi_within = compute_mi(all_pfx, all_sfx)

print(f"\n  {'Measure':<40} {'MI (bits)':>10}")
print(f"  {'-' * 50}")
print(f"  {'MI(pfx_i → pfx_j) same feature':<40} {mi_pfx:>10.4f}")
print(f"  {'MI(sfx_i → sfx_j) same feature':<40} {mi_sfx:>10.4f}")
print(f"  {'MI(pfx_i → sfx_j) cross-feature':<40} {mi_pfx_to_sfx:>10.4f}")
print(f"  {'MI(sfx_i → pfx_j) cross-feature':<40} {mi_sfx_to_pfx:>10.4f}")
print(f"  {'MI(class_i → class_j) combined':<40} {mi_cls:>10.4f}")
print(f"  {'Sum: MI(pfx) + MI(sfx)':<40} {mi_pfx + mi_sfx:>10.4f}")
print(f"  {'MI(pfx, sfx) within-word':<40} {mi_within:>10.4f}")

interaction = mi_cls - mi_pfx - mi_sfx
print(f"\n  Interaction: MI(class) - MI(pfx) - MI(sfx) = {interaction:.4f} bits")
pct_interaction = (interaction / mi_cls * 100) if mi_cls > 0 else 0
print(f"  Interaction as % of total class MI: {pct_interaction:.1f}%")

# Permutation test for cross-feature MI
print(f"\n  Permutation test for cross-feature MI:")
null_p2s = []
null_s2p = []
for _ in range(200):
    shuf_p_i = []
    shuf_p_j = []
    shuf_s_i = []
    shuf_s_j = []
    for line in lines:
        n = len(line['pfx'])
        perm = list(range(n))
        random.shuffle(perm)
        for i in range(n - 1):
            ii, jj = perm[i], perm[i + 1]
            shuf_p_i.append(line['pfx'][ii])
            shuf_p_j.append(line['pfx'][jj])
            shuf_s_i.append(line['sfx'][ii])
            shuf_s_j.append(line['sfx'][jj])
    null_p2s.append(compute_mi(shuf_p_i, shuf_s_j))
    null_s2p.append(compute_mi(shuf_s_i, shuf_p_j))

z_p2s = (mi_pfx_to_sfx - np.mean(null_p2s)) / max(np.std(null_p2s), 1e-10)
z_s2p = (mi_sfx_to_pfx - np.mean(null_s2p)) / max(np.std(null_s2p), 1e-10)

print(f"  MI(pfx_i→sfx_j): obs={mi_pfx_to_sfx:.4f}, null={np.mean(null_p2s):.4f}±{np.std(null_p2s):.4f}, z={z_p2s:.1f}")
print(f"  MI(sfx_i→pfx_j): obs={mi_sfx_to_pfx:.4f}, null={np.mean(null_s2p):.4f}±{np.std(null_s2p):.4f}, z={z_s2p:.1f}")

if z_p2s > 3 or z_s2p > 3:
    print(f"  → Cross-feature syntax EXISTS: prefixes predict following suffixes (or vice versa)")
    print(f"    This means there are genuine WORD CLASSES, not just independent affix channels")
else:
    print(f"  → No cross-feature syntax: prefix and suffix ordering are independent channels")


# ══════════════════════════════════════════════════════════════════
# 41b: TRIGRAM TEST — Beyond pairwise bigrams?
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("41b: TRIGRAM TEST — Does 3-word structure exist beyond bigrams?")
print("    MI(pfx_i; pfx_{i+2} | pfx_{i+1}): does knowing the first word's")
print("    prefix help predict the third, BEYOND what the middle tells you?")
print("=" * 70)

# Build trigram arrays
pfx_a, pfx_b, pfx_c = [], [], []
sfx_a, sfx_b, sfx_c = [], [], []

for line in lines:
    for i in range(len(line['pfx']) - 2):
        pfx_a.append(line['pfx'][i])
        pfx_b.append(line['pfx'][i + 1])
        pfx_c.append(line['pfx'][i + 2])
        sfx_a.append(line['sfx'][i])
        sfx_b.append(line['sfx'][i + 1])
        sfx_c.append(line['sfx'][i + 2])

# MI(a; c) unconditional
mi_ac_pfx = compute_mi(pfx_a, pfx_c)
mi_ac_sfx = compute_mi(sfx_a, sfx_c)

# MI(a; c | b) — conditional on middle word
cmi_ac_pfx = cond_mi(pfx_a, pfx_c, pfx_b)
cmi_ac_sfx = cond_mi(sfx_a, sfx_c, sfx_b)

# For comparison: MI(a; b)
mi_ab_pfx = compute_mi(pfx_a, pfx_b)
mi_ab_sfx = compute_mi(sfx_a, sfx_b)

print(f"\n  {'Measure':<40} {'Prefix':>10} {'Suffix':>10}")
print(f"  {'-' * 60}")
print(f"  {'MI(word_i; word_{i+1})':<40} {mi_ab_pfx:>10.4f} {mi_ab_sfx:>10.4f}")
print(f"  {'MI(word_i; word_{i+2})':<40} {mi_ac_pfx:>10.4f} {mi_ac_sfx:>10.4f}")
print(f"  {'MI(word_i; word_{i+2} | word_{i+1})':<40} {cmi_ac_pfx:>10.4f} {cmi_ac_sfx:>10.4f}")

# If CMI(a;c|b) > 0: the first word contains info about the third
# that the middle word doesn't carry. This would be genuine 3-word syntax.

# Permutation test
print(f"\n  Permutation test (shuffle within lines):")
null_cmi_pfx = []
null_cmi_sfx = []
for _ in range(200):
    sp_a, sp_b, sp_c = [], [], []
    ss_a, ss_b, ss_c = [], [], []
    for line in lines:
        n = len(line['pfx'])
        perm = list(range(n))
        random.shuffle(perm)
        for i in range(n - 2):
            sp_a.append(line['pfx'][perm[i]])
            sp_b.append(line['pfx'][perm[i + 1]])
            sp_c.append(line['pfx'][perm[i + 2]])
            ss_a.append(line['sfx'][perm[i]])
            ss_b.append(line['sfx'][perm[i + 1]])
            ss_c.append(line['sfx'][perm[i + 2]])
    null_cmi_pfx.append(cond_mi(sp_a, sp_c, sp_b))
    null_cmi_sfx.append(cond_mi(ss_a, ss_c, ss_b))

z_tri_p = (cmi_ac_pfx - np.mean(null_cmi_pfx)) / max(np.std(null_cmi_pfx), 1e-10)
z_tri_s = (cmi_ac_sfx - np.mean(null_cmi_sfx)) / max(np.std(null_cmi_sfx), 1e-10)

print(f"  MI(pfx_i;pfx_{'{i+2}'}|pfx_{'{i+1}'}): obs={cmi_ac_pfx:.4f}, null={np.mean(null_cmi_pfx):.4f}±{np.std(null_cmi_pfx):.4f}, z={z_tri_p:.1f}")
print(f"  MI(sfx_i;sfx_{'{i+2}'}|sfx_{'{i+1}'}): obs={cmi_ac_sfx:.4f}, null={np.mean(null_cmi_sfx):.4f}±{np.std(null_cmi_sfx):.4f}, z={z_tri_s:.1f}")

if z_tri_p > 3 or z_tri_s > 3:
    print(f"  → TRIGRAM SYNTAX EXISTS — 3-word dependencies beyond pairwise")
else:
    print(f"  → No trigram syntax — pairwise bigrams capture all ordering info")


# ══════════════════════════════════════════════════════════════════
# 41c: CROSS-LINE SYNTAX — deeper test
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("41c: CROSS-LINE SYNTAX")
print("    Do lines chain together, or is each an independent utterance?")
print("=" * 70)

# Build cross-line pairs (last word of line k → first word of line k+1)
# Only for consecutive lines in same section
cross_pfx_i, cross_pfx_j = [], []
cross_sfx_i, cross_sfx_j = [], []
cross_secs = []

prev = None
for line in lines:
    if prev and prev['section'] == line['section']:
        cross_pfx_i.append(prev['pfx'][-1])
        cross_pfx_j.append(line['pfx'][0])
        cross_sfx_i.append(prev['sfx'][-1])
        cross_sfx_j.append(line['sfx'][0])
        cross_secs.append(line['section'])
    prev = line

obs_cross_pfx = compute_mi(cross_pfx_i, cross_pfx_j)
obs_cross_sfx = compute_mi(cross_sfx_i, cross_sfx_j)

# Null: shuffle line order within section
by_sec = defaultdict(list)
for i, line in enumerate(lines):
    by_sec[line['section']].append(i)

null_xp, null_xs = [], []
for _ in range(500):
    sp_i, sp_j, ss_i, ss_j = [], [], [], []
    for sec, idxs in by_sec.items():
        perm = list(idxs)
        random.shuffle(perm)
        for k in range(len(perm) - 1):
            li = lines[perm[k]]
            lj = lines[perm[k + 1]]
            sp_i.append(li['pfx'][-1])
            sp_j.append(lj['pfx'][0])
            ss_i.append(li['sfx'][-1])
            ss_j.append(lj['sfx'][0])
    null_xp.append(compute_mi(sp_i, sp_j))
    null_xs.append(compute_mi(ss_i, ss_j))

z_xp = (obs_cross_pfx - np.mean(null_xp)) / max(np.std(null_xp), 1e-10)
z_xs = (obs_cross_sfx - np.mean(null_xs)) / max(np.std(null_xs), 1e-10)

print(f"\n  Cross-line pairs: {len(cross_pfx_i)}")
print(f"  MI(pfx last→first): obs={obs_cross_pfx:.4f}, null={np.mean(null_xp):.4f}±{np.std(null_xp):.4f}, z={z_xp:.1f}")
print(f"  MI(sfx last→first): obs={obs_cross_sfx:.4f}, null={np.mean(null_xs):.4f}±{np.std(null_xs):.4f}, z={z_xs:.1f}")

# Compare to within-line adjacent pairs
print(f"\n  For comparison:")
print(f"    Within-line MI(pfx): {mi_pfx:.4f}")
print(f"    Cross-line MI(pfx):  {obs_cross_pfx:.4f} ({obs_cross_pfx/mi_pfx*100:.0f}% of within-line)")
print(f"    Within-line MI(sfx): {mi_sfx:.4f}")
print(f"    Cross-line MI(sfx):  {obs_cross_sfx:.4f} ({obs_cross_sfx/mi_sfx*100:.0f}% of within-line)")

# Test: does cross-line MI vary by section?
print(f"\n  Per-section cross-line MI:")
for sec in sorted(set(cross_secs)):
    idxs = [i for i, s in enumerate(cross_secs) if s == sec]
    if len(idxs) < 30:
        continue
    xp_i = [cross_pfx_i[i] for i in idxs]
    xp_j = [cross_pfx_j[i] for i in idxs]
    xs_i = [cross_sfx_i[i] for i in idxs]
    xs_j = [cross_sfx_j[i] for i in idxs]
    print(f"    {sec:<12} n={len(idxs):>5} MI(pfx)={compute_mi(xp_i, xp_j):.4f} MI(sfx)={compute_mi(xs_i, xs_j):.4f}")


# ══════════════════════════════════════════════════════════════════
# 41d: sh→qo DECOMPOSITION — How dependent is syntax on one pattern?
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("41d: sh→qo DECOMPOSITION")
print("    How much prefix MI depends on the sh→qo transition?")
print("    If we remove all sh→qo pairs, what fraction of MI remains?")
print("=" * 70)

# Compute MI with and without sh→qo
N = len(pfx_i_arr)
joint_pfx = Counter(zip(pfx_i_arr, pfx_j_arr))
pfx_i_counts = Counter(pfx_i_arr)
pfx_j_counts = Counter(pfx_j_arr)

# Total MI decomposition by pair
mi_contributions = {}
for (a, b), n_ab in joint_pfx.items():
    p_ab = n_ab / N
    p_a = pfx_i_counts[a] / N
    p_b = pfx_j_counts[b] / N
    contrib = p_ab * math.log2(p_ab / (p_a * p_b)) if p_ab > 0 and p_a > 0 and p_b > 0 else 0
    mi_contributions[(a, b)] = contrib

total_mi = sum(mi_contributions.values())
sorted_contribs = sorted(mi_contributions.items(), key=lambda x: -abs(x[1]))

print(f"\n  Total MI(pfx→pfx) = {total_mi:.4f} bits")
print(f"\n  Top 15 contributions (positive = attraction, negative = avoidance):")
print(f"  {'Transition':<20} {'MI contrib':>10} {'% of total':>10} {'Count':>7}")
print(f"  {'-' * 47}")

cum_pct = 0
for (a, b), contrib in sorted_contribs[:15]:
    pct = contrib / total_mi * 100
    cum_pct += pct
    cnt = joint_pfx[(a, b)]
    print(f"  {a}→{b:<13} {contrib:>10.4f} {pct:>9.1f}% {cnt:>7}")
print(f"  {'':>20} {'Cumulative':>10} {cum_pct:>9.1f}%")

sh_qo_contrib = mi_contributions.get(('sh', 'qo'), 0)
sh_qo_pct = sh_qo_contrib / total_mi * 100 if total_mi > 0 else 0
print(f"\n  sh→qo specifically: {sh_qo_contrib:.4f} bits = {sh_qo_pct:.1f}% of total prefix MI")

# Remove all pairs involving sh or qo
no_sh_qo_pfx_i = []
no_sh_qo_pfx_j = []
for i in range(len(pfx_i_arr)):
    if pfx_i_arr[i] not in ('sh', 'qo') and pfx_j_arr[i] not in ('sh', 'qo'):
        no_sh_qo_pfx_i.append(pfx_i_arr[i])
        no_sh_qo_pfx_j.append(pfx_j_arr[i])

mi_no_sh_qo = compute_mi(no_sh_qo_pfx_i, no_sh_qo_pfx_j)
print(f"\n  MI excluding all sh/qo words: {mi_no_sh_qo:.4f} (was {mi_pfx:.4f})")

# Null for the no-sh/qo subset
null_no = []
for _ in range(200):
    si, sj = [], []
    for line in lines:
        n = len(line['pfx'])
        perm = list(range(n))
        random.shuffle(perm)
        for i in range(n - 1):
            ii, jj = perm[i], perm[i + 1]
            pi, pj = line['pfx'][ii], line['pfx'][jj]
            if pi not in ('sh', 'qo') and pj not in ('sh', 'qo'):
                si.append(pi)
                sj.append(pj)
    null_no.append(compute_mi(si, sj))

z_no = (mi_no_sh_qo - np.mean(null_no)) / max(np.std(null_no), 1e-10)
print(f"  z-score without sh/qo: {z_no:.1f} (null={np.mean(null_no):.4f}±{np.std(null_no):.4f})")

if z_no > 3:
    print(f"  → Prefix syntax SURVIVES removal of sh and qo")
else:
    print(f"  → WARNING: Prefix syntax depends heavily on sh→qo pattern")


# ══════════════════════════════════════════════════════════════════
# 41e: SUFFIX ORDERING GRAMMAR
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("41e: SUFFIX ORDERING GRAMMAR")
print("    Mapping suffix→suffix transitions for DIFFERENT-suffix pairs.")
print("    What are the 'grammatical rules' of suffix sequencing?")
print("=" * 70)

# Build different-suffix MI decomposition
diff_sfx_i, diff_sfx_j = [], []
for i in range(len(sfx_i_arr)):
    if sfx_i_arr[i] != sfx_j_arr[i]:
        diff_sfx_i.append(sfx_i_arr[i])
        diff_sfx_j.append(sfx_j_arr[i])

N_diff = len(diff_sfx_i)
joint_diff = Counter(zip(diff_sfx_i, diff_sfx_j))
row_cts = Counter(diff_sfx_i)
col_cts = Counter(diff_sfx_j)

# MI decomposition
contribs = {}
for (a, b), n_ab in joint_diff.items():
    p_ab = n_ab / N_diff
    p_a = row_cts[a] / N_diff
    p_b = col_cts[b] / N_diff
    if p_ab > 0 and p_a > 0 and p_b > 0:
        contribs[(a, b)] = p_ab * math.log2(p_ab / (p_a * p_b))

total_sfx_mi = sum(contribs.values())
sorted_sfx = sorted(contribs.items(), key=lambda x: -x[1])

print(f"\n  Different-suffix pairs: {N_diff}")
print(f"  Total MI: {total_sfx_mi:.4f} bits")
print(f"\n  TOP ATTRACTIONS (positive MI contributions):")
print(f"  {'Transition':<20} {'MI contrib':>10} {'Count':>7} {'Obs/Exp':>8}")
print(f"  {'-' * 47}")
for (a, b), contrib in sorted_sfx[:12]:
    cnt = joint_diff[(a, b)]
    exp = row_cts[a] * col_cts[b] / N_diff
    ratio = cnt / max(exp, 0.1)
    print(f"  {a}→{b:<13} {contrib:>10.4f} {cnt:>7} {ratio:>8.2f}")

print(f"\n  TOP AVOIDANCES (negative MI contributions):")
sorted_sfx_neg = sorted(contribs.items(), key=lambda x: x[1])
for (a, b), contrib in sorted_sfx_neg[:12]:
    cnt = joint_diff[(a, b)]
    exp = row_cts[a] * col_cts[b] / N_diff
    ratio = cnt / max(exp, 0.1)
    print(f"  {a}→{b:<13} {contrib:>10.4f} {cnt:>7} {ratio:>8.2f}")

# TEST: Suffix symmetry — is X→Y ≈ Y→X (harmonic) or X→Y ≠ Y→X (directional)?
print(f"\n  DIRECTIONALITY: Is suffix ordering symmetric or directional?")
print(f"  {'Pair':<12} {'A→B cnt':>8} {'B→A cnt':>8} {'A→B ratio':>10} {'B→A ratio':>10} {'Symmetric?':>10}")
print(f"  {'-' * 58}")

checked = set()
for (a, b), _ in sorted_sfx[:20]:
    pair = tuple(sorted([a, b]))
    if pair in checked or a == b:
        continue
    checked.add(pair)
    ab_cnt = joint_diff.get((a, b), 0)
    ba_cnt = joint_diff.get((b, a), 0)
    ab_exp = row_cts[a] * col_cts[b] / N_diff if N_diff > 0 else 1
    ba_exp = row_cts[b] * col_cts[a] / N_diff if N_diff > 0 else 1
    ab_ratio = ab_cnt / max(ab_exp, 0.1)
    ba_ratio = ba_cnt / max(ba_exp, 0.1)
    sym = "~SYM" if abs(ab_ratio - ba_ratio) < 0.3 else "ASYM"
    print(f"  {a}/{b:<9} {ab_cnt:>8} {ba_cnt:>8} {ab_ratio:>10.2f} {ba_ratio:>10.2f} {sym:>10}")


# ══════════════════════════════════════════════════════════════════
# SYNTHESIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("syntactic_grammar_map SYNTHESIS: The Grammar of Voynichese")
print("=" * 70)

print(f"""
  41a: PREFIX×SUFFIX INTERACTION
    MI(class→class) = {mi_cls:.4f}
    MI(pfx) + MI(sfx) = {mi_pfx + mi_sfx:.4f}
    Interaction (excess) = {interaction:.4f} ({pct_interaction:.1f}% of class MI)
    Cross-feature: pfx_i→sfx_j z={z_p2s:.1f}, sfx_i→pfx_j z={z_s2p:.1f}
    {'→ WORD CLASSES EXIST — prefix and suffix channels interact' if z_p2s > 3 or z_s2p > 3 else '→ Independent channels, no word classes'}

  41b: TRIGRAM SYNTAX
    MI(word_i; word_{{i+2}} | word_{{i+1}}): pfx z={z_tri_p:.1f}, sfx z={z_tri_s:.1f}
    {'→ 3-WORD DEPENDENCIES EXIST beyond bigrams' if z_tri_p > 3 or z_tri_s > 3 else '→ Bigrams capture all syntax'}

  41c: CROSS-LINE CONTINUITY
    Cross-line MI: pfx z={z_xp:.1f}, sfx z={z_xs:.1f}
    Cross-line = {obs_cross_pfx/mi_pfx*100:.0f}% of within-line (pfx), {obs_cross_sfx/mi_sfx*100:.0f}% (sfx)
    {'→ Lines are CONNECTED — text-level coherence' if z_xp > 3 or z_xs > 3 else '→ Lines are approximately independent utterances'}

  41d: sh→qo DEPENDENCY
    sh→qo = {sh_qo_pct:.1f}% of total prefix MI
    Without ALL sh/qo words: z={z_no:.1f}
    {'→ Prefix syntax survives without sh/qo' if z_no > 3 else '→ Prefix syntax depends on sh→qo'}

  41e: SUFFIX ORDERING
    Rich structure in suffix transitions — see tables above.
    Cross-suffix MI for different-suffix pairs: {total_sfx_mi:.4f} bits
""")

print("[syntactic_grammar_map Complete]")
