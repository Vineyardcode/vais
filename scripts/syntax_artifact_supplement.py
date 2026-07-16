#!/usr/bin/env python3
"""
Supplement — fixes two methodological flaws in syntax_artifact_attack.

FIX 1 (40b-fix): POSITION CONTROL
  Original 40b assigned shuffled words their ORIGINAL positions,
  creating sparse cells and inflated null MI. 
  
  Correct approach: stratify pairs by (pos_pair × section), then
  independently shuffle prefix_i within its (pos_i, sec) stratum
  and prefix_j within its (pos_j, sec) stratum. This preserves
  positional distributions while destroying pair-level correlations.

FIX 2 (40a-fix): BOUNDARY CHARACTER OVER-CONTROL
  Original 40a conditioned on (last_char_i, first_char_j).
  But first_char_j nearly determines pfx_j — conditioning on it
  is conditioning on a proxy for the OUTCOME. That's like testing
  whether education predicts income after controlling for salary.

  Correct test: condition ONLY on last_char_i (which captures the
  boundary phonotactic from the PRECEDING word, without touching
  the outcome variable).

  Additional test: condition on last_char_i but test suffix→suffix
  MI conditioned on first_char_j (since first char doesn't determine
  suffix). This tests cross-feature effects.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_mi, get_collapsed, get_suffix, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(42)
np.random.seed(42)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']


def get_prefix(w):
    for p in ['qo','lch','lsh','sh','ch','so','do','q','o','d','y','l']:
        if w.startswith(p): return p
    return 'NONE'



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


print("Loading lines...")
lines = load_lines()
lines = annotate_lines(lines)
total_words = sum(len(l['words']) for l in lines)
print(f"  {len(lines)} lines, {total_words} tokens")


# ══════════════════════════════════════════════════════════════════
# FIX 1: 40b — PROPER POSITION-STRATIFIED PERMUTATION
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("40b-FIX: PROPER POSITION-STRATIFIED PERMUTATION TEST")
print("  For each pair, independently resample prefixes from the pool")
print("  at the same (pos_bin, section). This preserves positional and")
print("  section distributions while destroying pair-level correlations.")
print("=" * 70)

def pos_bin(p, n_bins):
    b = int(p * n_bins)
    return min(b, n_bins - 1)


for n_bins in [5, 10, 20]:
    # Collect all pairs with their strata
    pairs = []  # (pfx_i, pfx_j, pos_i, pos_j, sec)
    for line in lines:
        for i in range(len(line['pfx']) - 1):
            pi = pos_bin(line['pos'][i], n_bins)
            pj = pos_bin(line['pos'][i + 1], n_bins)
            pairs.append((line['pfx'][i], line['pfx'][i + 1],
                          pi, pj, line['section']))

    # Also collect suffix pairs
    sfx_pairs = []
    for line in lines:
        for i in range(len(line['sfx']) - 1):
            pi = pos_bin(line['pos'][i], n_bins)
            pj = pos_bin(line['pos'][i + 1], n_bins)
            sfx_pairs.append((line['sfx'][i], line['sfx'][i + 1],
                              pi, pj, line['section']))

    # Build prefix pools by (pos_bin, section)
    pfx_pool = defaultdict(list)
    sfx_pool = defaultdict(list)
    for (pi, pj, pos_i, pos_j, sec) in pairs:
        pfx_pool[(pos_i, sec)].append(pi)
        pfx_pool[(pos_j, sec)].append(pj)
    for (si, sj, pos_i, pos_j, sec) in sfx_pairs:
        sfx_pool[(pos_i, sec)].append(si)
        sfx_pool[(pos_j, sec)].append(sj)

    # Observed MI (plain, not conditional)
    pfx_i_arr = [p[0] for p in pairs]
    pfx_j_arr = [p[1] for p in pairs]
    sfx_i_arr = [s[0] for s in sfx_pairs]
    sfx_j_arr = [s[1] for s in sfx_pairs]

    obs_mi_pfx = compute_mi(pfx_i_arr, pfx_j_arr)
    obs_mi_sfx = compute_mi(sfx_i_arr, sfx_j_arr)

    # Null: independently draw pfx_i from pool(pos_i, sec), pfx_j from pool(pos_j, sec)
    N_PERM = 200
    null_pfx = []
    null_sfx = []
    for _ in range(N_PERM):
        shuf_pfx_i = []
        shuf_pfx_j = []
        for (pi, pj, pos_i, pos_j, sec) in pairs:
            shuf_pfx_i.append(random.choice(pfx_pool[(pos_i, sec)]))
            shuf_pfx_j.append(random.choice(pfx_pool[(pos_j, sec)]))
        null_pfx.append(compute_mi(shuf_pfx_i, shuf_pfx_j))

        shuf_sfx_i = []
        shuf_sfx_j = []
        for (si, sj, pos_i, pos_j, sec) in sfx_pairs:
            shuf_sfx_i.append(random.choice(sfx_pool[(pos_i, sec)]))
            shuf_sfx_j.append(random.choice(sfx_pool[(pos_j, sec)]))
        null_sfx.append(compute_mi(shuf_sfx_i, shuf_sfx_j))

    nm_p, ns_p = np.mean(null_pfx), np.std(null_pfx)
    nm_s, ns_s = np.mean(null_sfx), np.std(null_sfx)
    z_p = (obs_mi_pfx - nm_p) / max(ns_p, 1e-10)
    z_s = (obs_mi_sfx - nm_s) / max(ns_s, 1e-10)

    residual_p = obs_mi_pfx - nm_p
    residual_s = obs_mi_sfx - nm_s
    pct_p = (nm_p / obs_mi_pfx * 100) if obs_mi_pfx > 0 else 0
    pct_s = (nm_s / obs_mi_sfx * 100) if obs_mi_sfx > 0 else 0

    print(f"\n  {n_bins} bins:")
    print(f"    MI(pfx→pfx): obs={obs_mi_pfx:.4f}, null={nm_p:.4f}±{ns_p:.4f}, "
          f"z={z_p:.1f}, pos×sec explains {pct_p:.1f}%")
    print(f"    MI(sfx→sfx): obs={obs_mi_sfx:.4f}, null={nm_s:.4f}±{ns_s:.4f}, "
          f"z={z_s:.1f}, pos×sec explains {pct_s:.1f}%")


# ══════════════════════════════════════════════════════════════════
# FIX 2: 40a — CORRECTED BOUNDARY CHARACTER CONTROL
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("40a-FIX: CORRECTED BOUNDARY CHARACTER CONTROL")
print("  Problem: conditioning on first_char_j nearly determines pfx_j,")
print("  so MI(pfx_i; pfx_j | first_char_j) ≈ 0 by construction.")
print("  Fix: condition ONLY on last_char_i (captures boundary effect")
print("  from preceding word without touching outcome variable).")
print("=" * 70)

# Build arrays
pfx_i_all = []
pfx_j_all = []
sfx_i_all = []
sfx_j_all = []
last_char_arr = []
first_char_arr = []
sec_arr = []
pos_i_arr = []

for line in lines:
    for i in range(len(line['pfx']) - 1):
        pfx_i_all.append(line['pfx'][i])
        pfx_j_all.append(line['pfx'][i + 1])
        sfx_i_all.append(line['sfx'][i])
        sfx_j_all.append(line['sfx'][i + 1])
        last_char_arr.append(line['last_char'][i])
        first_char_arr.append(line['first_char'][i + 1])
        sec_arr.append(line['section'])
        pos_i_arr.append(pos_bin(line['pos'][i], 5))

# Unconditional MI (baseline)
mi_pfx_unc = compute_mi(pfx_i_all, pfx_j_all)
mi_sfx_unc = compute_mi(sfx_i_all, sfx_j_all)

# Test 1: MI(pfx_i; pfx_j | last_char_i)
#   — Does knowing pfx_i still predict pfx_j after controlling for
#     what character ended word_i?
cmi_pfx_last = cond_mi(pfx_i_all, pfx_j_all, last_char_arr)

# Test 2: MI(sfx_i; sfx_j | first_char_j)
#   — first_char_j doesn't determine suffix, so this is safe
cmi_sfx_first = cond_mi(sfx_i_all, sfx_j_all, first_char_arr)

# Test 3: MI(pfx_i; pfx_j | last_char_i × section × pos)
combined_cond = [f"{last_char_arr[i]}_{sec_arr[i]}_{pos_i_arr[i]}"
                 for i in range(len(pfx_i_all))]
cmi_pfx_combined = cond_mi(pfx_i_all, pfx_j_all, combined_cond)

print(f"\n  {'Measure':<50} {'Value':>8}")
print(f"  {'-' * 58}")
print(f"  {'MI(pfx_i; pfx_j) unconditional':<50} {mi_pfx_unc:>8.4f}")
print(f"  {'MI(pfx_i; pfx_j | last_char_i)':<50} {cmi_pfx_last:>8.4f}")
print(f"  {'MI(pfx_i; pfx_j | last_char_i × sec × pos5)':<50} {cmi_pfx_combined:>8.4f}")
print(f"  {'MI(sfx_i; sfx_j) unconditional':<50} {mi_sfx_unc:>8.4f}")
print(f"  {'MI(sfx_i; sfx_j | first_char_j)':<50} {cmi_sfx_first:>8.4f}")

pct_pfx_last = (1 - cmi_pfx_last / mi_pfx_unc) * 100 if mi_pfx_unc > 0 else 0
pct_sfx_first = (1 - cmi_sfx_first / mi_sfx_unc) * 100 if mi_sfx_unc > 0 else 0

print(f"\n  last_char_i explains {pct_pfx_last:.1f}% of pfx→pfx MI")
print(f"  first_char_j explains {pct_sfx_first:.1f}% of sfx→sfx MI")

# Permutation test for the corrected measures
print(f"\n  Permutation tests (200 within-line shuffles):")

null_pfx_last = []
null_pfx_combo = []
null_sfx_first = []

for _ in range(200):
    s_pfx_i = []
    s_pfx_j = []
    s_sfx_i = []
    s_sfx_j = []
    s_last = []
    s_first = []
    s_sec = []
    s_pos = []

    for line in lines:
        n = len(line['pfx'])
        perm = list(range(n))
        random.shuffle(perm)
        for i in range(n - 1):
            ii, jj = perm[i], perm[i + 1]
            s_pfx_i.append(line['pfx'][ii])
            s_pfx_j.append(line['pfx'][jj])
            s_sfx_i.append(line['sfx'][ii])
            s_sfx_j.append(line['sfx'][jj])
            s_last.append(line['last_char'][ii])
            s_first.append(line['first_char'][jj])
            s_sec.append(line['section'])
            s_pos.append(pos_bin(line['pos'][i], 5))

    null_pfx_last.append(cond_mi(s_pfx_i, s_pfx_j, s_last))
    s_combo = [f"{s_last[k]}_{s_sec[k]}_{s_pos[k]}" for k in range(len(s_pfx_i))]
    null_pfx_combo.append(cond_mi(s_pfx_i, s_pfx_j, s_combo))
    null_sfx_first.append(cond_mi(s_sfx_i, s_sfx_j, s_first))

def z_score(obs, null_arr):
    m, s = np.mean(null_arr), np.std(null_arr)
    return (obs - m) / max(s, 1e-10), m, s

z_pl, nm_pl, ns_pl = z_score(cmi_pfx_last, null_pfx_last)
z_pc, nm_pc, ns_pc = z_score(cmi_pfx_combined, null_pfx_combo)
z_sf, nm_sf, ns_sf = z_score(cmi_sfx_first, null_sfx_first)

print(f"\n  {'Measure':<50} {'Obs':>7} {'Null':>12} {'z':>7}")
print(f"  {'-' * 76}")
print(f"  {'MI(pfx→pfx | last_char_i)':<50} {cmi_pfx_last:>7.4f} {nm_pl:>6.4f}±{ns_pl:.4f} {z_pl:>7.1f}")
print(f"  {'MI(pfx→pfx | last_char_i × sec × pos5)':<50} {cmi_pfx_combined:>7.4f} {nm_pc:>6.4f}±{ns_pc:.4f} {z_pc:>7.1f}")
print(f"  {'MI(sfx→sfx | first_char_j)':<50} {cmi_sfx_first:>7.4f} {nm_sf:>6.4f}±{ns_sf:.4f} {z_sf:>7.1f}")


# ══════════════════════════════════════════════════════════════════
# ADDITIONAL: BOUNDARY CHARACTER DECOMPOSITION
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("BOUNDARY DECOMPOSITION: Which boundary transitions drive the signal?")
print("=" * 70)

# For the top boundary transitions (y→q, r→a, etc.), compute how much
# of the prefix MI they contribute
boundary_counts = Counter(zip(last_char_arr, first_char_arr))
total_pairs = len(pfx_i_all)

print(f"\n  {'Boundary':<12} {'Count':>7} {'%':>6} {'MI(pfx)':>10} {'MI(sfx)':>10}")
print(f"  {'-' * 50}")

# For top 15 boundary pairs
for (lc, fc), cnt in boundary_counts.most_common(15):
    indices = [i for i in range(total_pairs)
               if last_char_arr[i] == lc and first_char_arr[i] == fc]
    pfx_i_sub = [pfx_i_all[i] for i in indices]
    pfx_j_sub = [pfx_j_all[i] for i in indices]
    sfx_i_sub = [sfx_i_all[i] for i in indices]
    sfx_j_sub = [sfx_j_all[i] for i in indices]
    mi_p = compute_mi(pfx_i_sub, pfx_j_sub) if len(indices) > 20 else float('nan')
    mi_s = compute_mi(sfx_i_sub, sfx_j_sub) if len(indices) > 20 else float('nan')
    print(f"  {lc}→{fc:<9} {cnt:>7} {cnt/total_pairs*100:>5.1f}% {mi_p:>10.4f} {mi_s:>10.4f}")


# ══════════════════════════════════════════════════════════════════
# SYNTHESIS OF FIXES
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("syntax_artifact_supplement SUPPLEMENT SYNTHESIS")
print("=" * 70)

print(f"""
  40b-FIX (Position Control):
    The original 40b had a bug that inflated null MI with sparse cells.
    The corrected stratified permutation test properly controls for
    position and section while testing for pair-level ordering effects.
    Check z-scores above across 5/10/20 bins.

  40a-FIX (Boundary Characters):
    Original conditioning on (last_char, first_char) was over-controlling
    because first_char nearly determines prefix (collider issue).

    Corrected: MI(pfx→pfx | last_char_i) only — z = {z_pl:.1f}
    With combined control: MI(pfx→pfx | last_char_i × sec × pos) — z = {z_pc:.1f}
    MI(sfx→sfx | first_char_j) — z = {z_sf:.1f}

    {'Prefix syntax SURVIVES corrected boundary control' if z_pl > 3 else 'Prefix syntax is WEAKENED by boundary control'}
    {'Suffix syntax SURVIVES boundary control' if z_sf > 3 else 'Suffix syntax weakened'}

  KEY INSIGHT: In Voynich, boundary characters ARE the morphological
  features (prefix = first chars, suffix = last chars). So "boundary
  phonotactics" vs "morphological agreement" is a false dichotomy.
  The real question is: does word-level ordering exist beyond position
  and section effects? That's what the stratified permutation tests answer.
""")

print("[syntax_artifact_supplement Supplement Complete]")
