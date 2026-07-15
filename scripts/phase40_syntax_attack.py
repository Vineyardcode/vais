#!/usr/bin/env python3
"""
Phase 40 — ATTACKING PHASE 39: IS "SYNTAX" AN ARTIFACT?
=========================================================

Phase 39 found inter-word ordering effects (z=28-39) and local decay
(gap 3 cutoff). Before accepting "genuine syntax," we must test every
alternative explanation.

THREATS TO THE SYNTAX CLAIM:

1. CROSS-BOUNDARY CHARACTER BIGRAMS
   Probe found y→q at 1.77x, r→a at 2.49x. Words ending in -y are
   followed by qo-words; words ending in -r are followed by a-words.
   If this boundary effect drives the prefix/suffix MI, "syntax" is
   just character-level phonotactics across word gaps.

2. SUFFIX RUNS
   13% of words are in suffix run-2, 3% in run-3. The suffix agreement
   (z=29.3) could be an artifact of repetitive blocks rather than
   grammatical agreement.

3. COARSE POSITION BINS
   Phase 39 used 5 position bins. Fine-grained position effects within
   bins could explain the residual MI.

4. LINE-BOUNDARY EFFECTS
   We treated each line as a sequence, but position=0 and position=1
   (line-initial and line-final) are special. If we exclude those,
   does the signal survive?

Sub-analyses:
  40a) BOUNDARY CHARACTER CONTROL
       Compute MI(pfx_i, pfx_{i+1}) after controlling for boundary
       characters (last char of word i, first char of word i+1).
       If syntax MI → 0 after control → it's phonotactic.

  40b) FINE-GRAINED POSITION CONTROL
       Use 10 and 20 position bins. Does syntax survive?

  40c) SUFFIX RUNS vs AGREEMENT
       Exclude same-suffix pairs. Does cross-suffix prediction exist?
       This separates "runs" from "agreement."

  40d) LINE-EDGE EXCLUSION
       Exclude first and last word of each line. Does syntax survive
       for line-interior words only?

  40e) SECTION-SPECIFIC SYNTAX
       Compute syntax MI per section. If concentrated in one section,
       it may be content-specific, not structural.
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
# CONSTANTS & HELPERS (same as Phase 39)
# ══════════════════════════════════════════════════════════════════

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']


def get_prefix(w):
    for p in ['qo','lch','lsh','sh','ch','so','do','q','o','d','y','l']:
        if w.startswith(p): return p
    return 'NONE'



def cond_mi(x_arr, y_arr, z_arr):
    """MI(X;Y|Z) = sum_z P(z) * MI(X;Y | Z=z)."""
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
        line['pos'] = [i / max(n - 1, 1) for i in range(n)]
        line['last_char'] = [c[-1] if c else '?' for c in line['collapsed']]
        line['first_char'] = [c[0] if c else '?' for c in line['collapsed']]
    return lines


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

print("Loading lines...")
lines = load_lines()
lines = annotate_lines(lines)
total_words = sum(len(l['words']) for l in lines)
print(f"  {len(lines)} lines, {total_words} word tokens")


# ══════════════════════════════════════════════════════════════════
# 40a: BOUNDARY CHARACTER CONTROL
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("40a: BOUNDARY CHARACTER CONTROL")
print("    Is 'syntax' just character phonotactics across word gaps?")
print("=" * 70)

# Build bigram arrays with boundary info
pfx_i_arr = []
pfx_j_arr = []
sfx_i_arr = []
sfx_j_arr = []
boundary_arr = []  # (last_char_i, first_char_j) as conditioning variable

for line in lines:
    for i in range(len(line['pfx']) - 1):
        pfx_i_arr.append(line['pfx'][i])
        pfx_j_arr.append(line['pfx'][i + 1])
        sfx_i_arr.append(line['sfx'][i])
        sfx_j_arr.append(line['sfx'][i + 1])
        boundary_arr.append(f"{line['last_char'][i]}_{line['first_char'][i+1]}")

# Unconditional MI (reproduce Phase 39)
mi_pfx = compute_mi(pfx_i_arr, pfx_j_arr)
mi_sfx = compute_mi(sfx_i_arr, sfx_j_arr)

# MI conditioned on boundary characters
cmi_pfx = cond_mi(pfx_i_arr, pfx_j_arr, boundary_arr)
cmi_sfx = cond_mi(sfx_i_arr, sfx_j_arr, boundary_arr)

# Also condition on last_char_i alone (suffix→prefix dependency)
last_only = [line['last_char'][i] for line in lines for i in range(len(line['pfx'])-1)]
cmi_pfx_last = cond_mi(pfx_i_arr, pfx_j_arr, last_only)
cmi_sfx_last = cond_mi(sfx_i_arr, sfx_j_arr, last_only)

# And first_char_j alone
first_only = [line['first_char'][i+1] for line in lines for i in range(len(line['pfx'])-1)]
cmi_pfx_first = cond_mi(pfx_i_arr, pfx_j_arr, first_only)
cmi_sfx_first = cond_mi(sfx_i_arr, sfx_j_arr, first_only)

print(f"\n  {'Measure':<40} {'Pfx→Pfx':>10} {'Sfx→Sfx':>10}")
print(f"  {'-' * 60}")
print(f"  {'MI (unconditioned, Phase 39)':<40} {mi_pfx:>10.4f} {mi_sfx:>10.4f}")
print(f"  {'MI | last char of word_i':<40} {cmi_pfx_last:>10.4f} {cmi_sfx_last:>10.4f}")
print(f"  {'MI | first char of word_{i+1}':<40} {cmi_pfx_first:>10.4f} {cmi_sfx_first:>10.4f}")
print(f"  {'MI | boundary pair (last,first)':<40} {cmi_pfx:>10.4f} {cmi_sfx:>10.4f}")

pct_pfx_boundary = (1 - cmi_pfx / mi_pfx) * 100 if mi_pfx > 0 else 0
pct_sfx_boundary = (1 - cmi_sfx / mi_sfx) * 100 if mi_sfx > 0 else 0
print(f"\n  Boundary characters explain:")
print(f"    {pct_pfx_boundary:.1f}% of prefix→prefix MI")
print(f"    {pct_sfx_boundary:.1f}% of suffix→suffix MI")

if pct_pfx_boundary > 80 or pct_sfx_boundary > 80:
    print(f"  → WARNING: Most 'syntax' MI is boundary-character phonotactics!")
elif pct_pfx_boundary > 50 or pct_sfx_boundary > 50:
    print(f"  → CAUTION: Boundary chars explain >50% — partial artifact")
else:
    print(f"  → Boundary chars explain <50% — syntax signal is robust")

# Permutation test: shuffle words within lines, preserve boundary structure?
# No — that doesn't make sense. Instead: shuffle within boundary-class bins.
print(f"\n  Permutation test: shuffle within boundary-pair bins...")
N_PERM = 200

null_pfx_cmi = []
null_sfx_cmi = []
for perm in range(N_PERM):
    # For each line, shuffle word order
    shuf_pfx_i = []
    shuf_pfx_j = []
    shuf_sfx_i = []
    shuf_sfx_j = []
    shuf_boundary = []
    for line in lines:
        n = len(line['pfx'])
        perm_idx = list(range(n))
        random.shuffle(perm_idx)
        for i in range(n - 1):
            ii = perm_idx[i]
            jj = perm_idx[i + 1]
            shuf_pfx_i.append(line['pfx'][ii])
            shuf_pfx_j.append(line['pfx'][jj])
            shuf_sfx_i.append(line['sfx'][ii])
            shuf_sfx_j.append(line['sfx'][jj])
            shuf_boundary.append(f"{line['last_char'][ii]}_{line['first_char'][jj]}")

    null_pfx_cmi.append(cond_mi(shuf_pfx_i, shuf_pfx_j, shuf_boundary))
    null_sfx_cmi.append(cond_mi(shuf_sfx_i, shuf_sfx_j, shuf_boundary))

np_m, np_s = np.mean(null_pfx_cmi), np.std(null_pfx_cmi)
ns_m, ns_s = np.mean(null_sfx_cmi), np.std(null_sfx_cmi)
z_pfx_bc = (cmi_pfx - np_m) / max(np_s, 1e-10)
z_sfx_bc = (cmi_sfx - ns_m) / max(ns_s, 1e-10)

print(f"\n  MI | boundary chars, vs within-line shuffle:")
print(f"  {'Feature':<25} {'Observed':>10} {'Null':>15} {'z':>8}")
print(f"  {'-' * 58}")
print(f"  {'MI(pfx→pfx|boundary)':<25} {cmi_pfx:>10.4f} {np_m:>8.4f}±{np_s:.4f} {z_pfx_bc:>8.1f}")
print(f"  {'MI(sfx→sfx|boundary)':<25} {cmi_sfx:>10.4f} {ns_m:>8.4f}±{ns_s:.4f} {z_sfx_bc:>8.1f}")

if z_pfx_bc > 3 or z_sfx_bc > 3:
    print(f"  → Syntax signal SURVIVES boundary-character control")
else:
    print(f"  → DESTROYED: 'syntax' was boundary-character phonotactics")


# ══════════════════════════════════════════════════════════════════
# 40b: FINE-GRAINED POSITION CONTROL
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("40b: FINE-GRAINED POSITION CONTROL")
print("    Does syntax survive with 10 and 20 position bins?")
print("=" * 70)

def pos_bin(p, n_bins):
    b = int(p * n_bins)
    return min(b, n_bins - 1)

for n_bins in [5, 10, 20]:
    # Build position×section conditioner
    pos_sec_arr = []
    pfx_i_list = []
    pfx_j_list = []
    for line in lines:
        for i in range(len(line['pfx']) - 1):
            pi = pos_bin(line['pos'][i], n_bins)
            pj = pos_bin(line['pos'][i + 1], n_bins)
            pfx_i_list.append(line['pfx'][i])
            pfx_j_list.append(line['pfx'][i + 1])
            pos_sec_arr.append(f"{pi}_{pj}_{line['section']}")

    obs_cmi = cond_mi(pfx_i_list, pfx_j_list, pos_sec_arr)

    # Null: shuffle within bins
    null_cmis = []
    for _ in range(100):
        shuf_pfx_i = []
        shuf_pfx_j = []
        shuf_cond = []
        for line in lines:
            n = len(line['pfx'])
            perm_idx = list(range(n))
            random.shuffle(perm_idx)
            for i in range(n - 1):
                ii = perm_idx[i]
                jj = perm_idx[i + 1]
                pi = pos_bin(line['pos'][ii], n_bins)
                pj = pos_bin(line['pos'][jj], n_bins)
                shuf_pfx_i.append(line['pfx'][ii])
                shuf_pfx_j.append(line['pfx'][jj])
                shuf_cond.append(f"{pi}_{pj}_{line['section']}")
        null_cmis.append(cond_mi(shuf_pfx_i, shuf_pfx_j, shuf_cond))

    nm, ns = np.mean(null_cmis), np.std(null_cmis)
    z = (obs_cmi - nm) / max(ns, 1e-10)
    print(f"  {n_bins:>2} bins: MI|pos_pair×sec = {obs_cmi:.4f}, null = {nm:.4f}±{ns:.4f}, z = {z:.1f}")


# ══════════════════════════════════════════════════════════════════
# 40c: SUFFIX RUNS vs AGREEMENT
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("40c: SUFFIX RUNS vs CROSS-SUFFIX AGREEMENT")
print("    Does prefix→prefix MI survive when we EXCLUDE same-suffix pairs?")
print("=" * 70)

# Separate pairs into same-suffix and different-suffix
same_sfx_pfx_i = []
same_sfx_pfx_j = []
diff_sfx_pfx_i = []
diff_sfx_pfx_j = []

diff_sfx_sfx_i = []
diff_sfx_sfx_j = []

for line in lines:
    for i in range(len(line['pfx']) - 1):
        if line['sfx'][i] == line['sfx'][i + 1]:
            same_sfx_pfx_i.append(line['pfx'][i])
            same_sfx_pfx_j.append(line['pfx'][i + 1])
        else:
            diff_sfx_pfx_i.append(line['pfx'][i])
            diff_sfx_pfx_j.append(line['pfx'][i + 1])
            diff_sfx_sfx_i.append(line['sfx'][i])
            diff_sfx_sfx_j.append(line['sfx'][i + 1])

mi_same = compute_mi(same_sfx_pfx_i, same_sfx_pfx_j)
mi_diff = compute_mi(diff_sfx_pfx_i, diff_sfx_pfx_j)
mi_diff_sfx = compute_mi(diff_sfx_sfx_i, diff_sfx_sfx_j)

print(f"\n  Same-suffix adjacent pairs: {len(same_sfx_pfx_i)}")
print(f"  Different-suffix pairs:     {len(diff_sfx_pfx_i)}")
print(f"\n  MI(pfx→pfx) within same-suffix pairs:  {mi_same:.4f}")
print(f"  MI(pfx→pfx) within diff-suffix pairs:   {mi_diff:.4f}")
print(f"  MI(sfx→sfx) within diff-suffix pairs:   {mi_diff_sfx:.4f}")

# Null test for different-suffix pairs only
null_diff = []
for _ in range(200):
    shuf_i = list(diff_sfx_pfx_i)
    random.shuffle(shuf_i)
    null_diff.append(compute_mi(shuf_i, diff_sfx_pfx_j))

nm, ns = np.mean(null_diff), np.std(null_diff)
z_diff = (mi_diff - nm) / max(ns, 1e-10)
print(f"\n  MI(pfx→pfx | diff suffix) vs random shuffle:")
print(f"    Observed: {mi_diff:.4f}, Null: {nm:.4f}±{ns:.4f}, z = {z_diff:.1f}")

if z_diff > 3:
    print(f"  → Prefix ordering survives even between DIFFERENT suffix pairs")
    print(f"    This is NOT just suffix runs")
else:
    print(f"  → Prefix ordering vanishes when suffix runs are excluded")
    print(f"    'Syntax' may be just suffix runs!")

# Also test: suffix→suffix MI excluding same-suffix pairs
null_diff_sfx = []
for _ in range(200):
    shuf_i = list(diff_sfx_sfx_i)
    random.shuffle(shuf_i)
    null_diff_sfx.append(compute_mi(shuf_i, diff_sfx_sfx_j))

nm_s, ns_s = np.mean(null_diff_sfx), np.std(null_diff_sfx)
z_diff_sfx = (mi_diff_sfx - nm_s) / max(ns_s, 1e-10)
print(f"\n  MI(sfx→sfx | diff suffix) vs random shuffle:")
print(f"    Observed: {mi_diff_sfx:.4f}, Null: {nm_s:.4f}±{ns_s:.4f}, z = {z_diff_sfx:.1f}")
print(f"    (Tests whether suffix sequencing is structured beyond same-suffix runs)")


# ══════════════════════════════════════════════════════════════════
# 40d: LINE-EDGE EXCLUSION
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("40d: LINE-EDGE EXCLUSION")
print("    Does syntax survive for interior words only?")
print("=" * 70)

interior_pfx_i = []
interior_pfx_j = []
interior_sfx_i = []
interior_sfx_j = []
all_pfx_i = []
all_pfx_j = []

for line in lines:
    n = len(line['pfx'])
    for i in range(n - 1):
        all_pfx_i.append(line['pfx'][i])
        all_pfx_j.append(line['pfx'][i + 1])
        # Interior: exclude first and last word of line
        if i > 0 and (i + 1) < n - 1:
            interior_pfx_i.append(line['pfx'][i])
            interior_pfx_j.append(line['pfx'][i + 1])
            interior_sfx_i.append(line['sfx'][i])
            interior_sfx_j.append(line['sfx'][i + 1])

mi_all_pfx = compute_mi(all_pfx_i, all_pfx_j)
mi_int_pfx = compute_mi(interior_pfx_i, interior_pfx_j)
mi_int_sfx = compute_mi(interior_sfx_i, interior_sfx_j)

print(f"\n  All pairs: {len(all_pfx_i)}, MI(pfx→pfx) = {mi_all_pfx:.4f}")
print(f"  Interior only: {len(interior_pfx_i)}, MI(pfx→pfx) = {mi_int_pfx:.4f}")
print(f"  Interior only: MI(sfx→sfx) = {mi_int_sfx:.4f}")

# Null for interior
null_int_pfx = []
null_int_sfx = []
for _ in range(200):
    shuf_i = []
    shuf_j = []
    shuf_si = []
    shuf_sj = []
    for line in lines:
        n = len(line['pfx'])
        perm_idx = list(range(n))
        random.shuffle(perm_idx)
        for i in range(n - 1):
            ii = perm_idx[i]
            jj = perm_idx[i + 1]
            if i > 0 and (i + 1) < n - 1:
                shuf_i.append(line['pfx'][ii])
                shuf_j.append(line['pfx'][jj])
                shuf_si.append(line['sfx'][ii])
                shuf_sj.append(line['sfx'][jj])
    null_int_pfx.append(compute_mi(shuf_i, shuf_j))
    null_int_sfx.append(compute_mi(shuf_si, shuf_sj))

nm_ip, ns_ip = np.mean(null_int_pfx), np.std(null_int_pfx)
nm_is, ns_is = np.mean(null_int_sfx), np.std(null_int_sfx)
z_int_pfx = (mi_int_pfx - nm_ip) / max(ns_ip, 1e-10)
z_int_sfx = (mi_int_sfx - nm_is) / max(ns_is, 1e-10)

print(f"\n  Interior-only vs within-line shuffle:")
print(f"  {'Feature':<25} {'Observed':>10} {'Null':>15} {'z':>8}")
print(f"  {'-' * 58}")
print(f"  {'MI(pfx→pfx) interior':<25} {mi_int_pfx:>10.4f} {nm_ip:>8.4f}±{ns_ip:.4f} {z_int_pfx:>8.1f}")
print(f"  {'MI(sfx→sfx) interior':<25} {mi_int_sfx:>10.4f} {nm_is:>8.4f}±{ns_is:.4f} {z_int_sfx:>8.1f}")

if z_int_pfx > 3 or z_int_sfx > 3:
    print(f"  → Syntax survives for interior-only words")
else:
    print(f"  → Syntax was driven by line-edge effects")


# ══════════════════════════════════════════════════════════════════
# 40e: SECTION-SPECIFIC SYNTAX
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("40e: SECTION-SPECIFIC SYNTAX")
print("    Is syntax uniform across sections?")
print("=" * 70)

section_counts = Counter(l['section'] for l in lines)
print(f"\n  {'Section':<12} {'Lines':>6} {'Pairs':>7} {'MI(pfx)':>10} {'MI(sfx)':>10} {'z(pfx)':>8} {'z(sfx)':>8}")
print(f"  {'-' * 63}")

for sec in sorted(section_counts, key=section_counts.get, reverse=True):
    sec_lines = [l for l in lines if l['section'] == sec]
    sec_pairs_p_i = []
    sec_pairs_p_j = []
    sec_pairs_s_i = []
    sec_pairs_s_j = []
    for line in sec_lines:
        for i in range(len(line['pfx']) - 1):
            sec_pairs_p_i.append(line['pfx'][i])
            sec_pairs_p_j.append(line['pfx'][i + 1])
            sec_pairs_s_i.append(line['sfx'][i])
            sec_pairs_s_j.append(line['sfx'][i + 1])

    if len(sec_pairs_p_i) < 50:
        continue

    mi_p = compute_mi(sec_pairs_p_i, sec_pairs_p_j)
    mi_s = compute_mi(sec_pairs_s_i, sec_pairs_s_j)

    # Quick null (50 perms)
    null_p = []
    null_s = []
    for _ in range(50):
        for line in sec_lines:
            n = len(line['pfx'])
            perm_idx = list(range(n))
            random.shuffle(perm_idx)
        # Rebuild
        np_i = []
        np_j = []
        ns_i = []
        ns_j = []
        for line in sec_lines:
            n = len(line['pfx'])
            perm_idx = list(range(n))
            random.shuffle(perm_idx)
            for i in range(n - 1):
                np_i.append(line['pfx'][perm_idx[i]])
                np_j.append(line['pfx'][perm_idx[i + 1]])
                ns_i.append(line['sfx'][perm_idx[i]])
                ns_j.append(line['sfx'][perm_idx[i + 1]])
        null_p.append(compute_mi(np_i, np_j))
        null_s.append(compute_mi(ns_i, ns_j))

    z_p = (mi_p - np.mean(null_p)) / max(np.std(null_p), 1e-10)
    z_s = (mi_s - np.mean(null_s)) / max(np.std(null_s), 1e-10)

    print(f"  {sec:<12} {len(sec_lines):>6} {len(sec_pairs_p_i):>7}"
          f" {mi_p:>10.4f} {mi_s:>10.4f} {z_p:>8.1f} {z_s:>8.1f}")


# ══════════════════════════════════════════════════════════════════
# SYNTHESIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PHASE 40 SYNTHESIS: What survives the attack?")
print("=" * 70)

print(f"""
  40a: BOUNDARY CHARACTER CONTROL
    Boundary chars explain {pct_pfx_boundary:.1f}% of pfx MI, {pct_sfx_boundary:.1f}% of sfx MI
    After boundary control: z(pfx)={z_pfx_bc:.1f}, z(sfx)={z_sfx_bc:.1f}
    {'→ Syntax SURVIVES boundary control' if z_pfx_bc > 3 or z_sfx_bc > 3 else '→ DESTROYED by boundary control'}

  40b: FINE-GRAINED POSITION CONTROL
    (See table above — if z stays high with 20 bins, position is controlled)

  40c: SUFFIX RUNS
    MI(pfx→pfx) excluding same-suffix pairs: z={z_diff:.1f}
    MI(sfx→sfx) excluding same-suffix pairs: z={z_diff_sfx:.1f}
    {'→ NOT just suffix runs' if z_diff > 3 else '→ Might be suffix runs'}

  40d: LINE-EDGE EXCLUSION
    Interior-only: z(pfx)={z_int_pfx:.1f}, z(sfx)={z_int_sfx:.1f}
    {'→ Syntax survives in line interior' if z_int_pfx > 3 or z_int_sfx > 3 else '→ Edge-driven only'}

  40e: SECTION-SPECIFIC
    (See table above — uniform = structural, concentrated = content-specific)

  OVERALL: If ALL tests pass, Phase 39 syntax claim SURVIVES.
  If ANY test demolishes the signal, we must RETRACT accordingly.
""")

print("[Phase 40 Complete]")
