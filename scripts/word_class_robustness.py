#!/usr/bin/env python3
"""
ATTACKING THE CLASS SYSTEM
======================================

two_class_section_grammar found:
  - Three-class suffix system captures 80.1% of sfx→pfx MI
  - Section-specific grammar (z=49-92)
  - Genuine synergy in class bigrams
  - Left→right prediction better (−0.089 bits)
  - Line-final most constrained

ALL of these must be attacked:

  43a) SECTION GRAMMAR: MARGINALS OR RULES?
       two_class_section_grammar's part-b null shuffled random subsets, preserving GLOBAL marginals.
       If a section has different prefix/suffix frequencies (vocabulary), its
       transition matrix will differ even without different conditional rules.
       TEST: Generate null by independently permuting prefix and suffix
       arrays WITHIN each section (preserves section marginals, destroys
       conditionals). If section LR is still large → marginals explain it.
       If LR drops → genuine conditional rules.

  43b) PREDICTIVE ASYMMETRY: PERMUTATION TEST
       0.089 bits of L→R advantage is untested. Two controls:
       1) Reverse all lines: if asymmetry flips sign → genuine direction.
       2) Shuffle word order within lines: asymmetry should → ~0.

  43c) OPTIMAL CLASS COUNT
       Binary captures 35.7%, three captures 80.1%. Is three the elbow?
       Hierarchical clustering of suffix profiles into k=2,3,4,5,6,7,8
       classes. Plot MI captured vs k.

  43d) SYNERGY BOOTSTRAP
       "chdy qoain" has synergy=2.63 but only 38 examples. Bootstrap
       1000 resamples of word pairs, compute synergy CI for each bigram.
       Is the CI above 1.0?

  43e) TOP SECTION DISCRIMINATORS
       For the transitions that contribute most to section LR, show the
       actual conditional probabilities per section. Are they different
       conditionals (rules) or just different marginals?
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_mi, get_collapsed, get_prefix, get_suffix, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(43)
np.random.seed(43)

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

def cond_entropy(target, source):
    """H(target|source)"""
    N = len(target)
    if N == 0: return 0.0
    joint = Counter(zip(source, target))
    src_counts = Counter(source)
    h = 0.0
    for (s, t), n_st in joint.items():
        p_st = n_st / N
        p_s = src_counts[s] / N
        if p_st > 0 and p_s > 0:
            h -= p_st * math.log2(p_st / p_s)
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
    return lines


print("Loading lines...")
lines = load_lines()
lines = annotate_lines(lines)
total_words = sum(len(l['words']) for l in lines)
print(f"  {len(lines)} lines, {total_words} word tokens")

# Build adjacent pairs with section labels
pairs = []
for line in lines:
    for i in range(len(line['pfx']) - 1):
        pairs.append({
            'pfx_i': line['pfx'][i], 'sfx_i': line['sfx'][i],
            'pfx_j': line['pfx'][i+1], 'sfx_j': line['sfx'][i+1],
            'section': line['section']
        })
print(f"  {len(pairs)} adjacent pairs")


# ══════════════════════════════════════════════════════════════════
# 43a: SECTION GRAMMAR — MARGINALS OR RULES?
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("43a: SECTION GRAMMAR — MARGINALS vs RULES")
print("    two_class_section_grammar part b found z=49-92, but the null preserved GLOBAL marginals.")
print("    Now: shuffle within section → preserves section marginals,")
print("    destroys conditionals. If LR drops to near null → marginals did it.")
print("=" * 70)

major_sections = ['text', 'herbal-A', 'bio', 'pharma']

for sec in major_sections:
    sec_pairs = [p for p in pairs if p['section'] == sec]
    N = len(sec_pairs)
    if N < 100:
        print(f"\n  {sec}: too few pairs ({N}), skipping")
        continue

    # Observed sfx_i → pfx_j transition matrix (Laplace-smoothed)
    sfx_vals = sorted(set(p['sfx_i'] for p in pairs))
    pfx_vals = sorted(set(p['pfx_j'] for p in pairs))

    def compute_ll(pair_list, trans_probs):
        """Log-likelihood of pair_list under given transition probs."""
        ll = 0.0
        for p in pair_list:
            s, pf = p['sfx_i'], p['pfx_j']
            prob = trans_probs.get((s, pf), 1e-10)
            ll += math.log(prob)
        return ll

    def fit_transition(pair_list):
        """Fit sfx→pfx transition matrix with Laplace smoothing."""
        alpha = 0.5
        joint = Counter((p['sfx_i'], p['pfx_j']) for p in pair_list)
        sfx_totals = Counter(p['sfx_i'] for p in pair_list)
        n_pfx = len(pfx_vals)
        probs = {}
        for s in sfx_vals:
            denom = sfx_totals[s] + alpha * n_pfx
            for pf in pfx_vals:
                probs[(s, pf)] = (joint[(s, pf)] + alpha) / denom
        return probs

    # Global transition matrix
    global_trans = fit_transition(pairs)
    # Section-specific transition matrix
    sec_trans = fit_transition(sec_pairs)

    ll_global = compute_ll(sec_pairs, global_trans)
    ll_local = compute_ll(sec_pairs, sec_trans)
    lr_obs = ll_local - ll_global

    # NULL 1 (from two_class_section_grammar): random subsets preserving global marginals
    null_lr_global = []
    all_pairs_list = list(pairs)
    n_perms = 500
    for _ in range(n_perms):
        subset = random.sample(all_pairs_list, N)
        sub_trans = fit_transition(subset)
        ll_g = compute_ll(subset, global_trans)
        ll_l = compute_ll(subset, sub_trans)
        null_lr_global.append(ll_l - ll_g)

    z_global = (lr_obs - np.mean(null_lr_global)) / max(np.std(null_lr_global), 1e-10)

    # NULL 2 (NEW): shuffle sfx_i and pfx_j INDEPENDENTLY within section
    # This preserves section marginal frequencies but destroys conditionals
    null_lr_marginal = []
    sec_sfx = [p['sfx_i'] for p in sec_pairs]
    sec_pfx = [p['pfx_j'] for p in sec_pairs]
    for _ in range(n_perms):
        shuf_sfx = list(sec_sfx)
        shuf_pfx = list(sec_pfx)
        random.shuffle(shuf_sfx)
        random.shuffle(shuf_pfx)
        fake_pairs = [{'sfx_i': s, 'pfx_j': p_} for s, p_ in zip(shuf_sfx, shuf_pfx)]
        fake_trans = fit_transition(fake_pairs)
        ll_g = compute_ll(fake_pairs, global_trans)
        ll_l = compute_ll(fake_pairs, fake_trans)
        null_lr_marginal.append(ll_l - ll_g)

    z_marginal = (lr_obs - np.mean(null_lr_marginal)) / max(np.std(null_lr_marginal), 1e-10)

    print(f"\n  {sec} ({N} pairs):")
    print(f"    Observed LR (local - global): {lr_obs:.1f}")
    print(f"    Null 1 (random subset, global marginals): mean={np.mean(null_lr_global):.1f}±{np.std(null_lr_global):.1f}")
    print(f"      z(global null) = {z_global:.1f}")
    print(f"    Null 2 (shuffled within section, section marginals): mean={np.mean(null_lr_marginal):.1f}±{np.std(null_lr_marginal):.1f}")
    print(f"      z(marginal null) = {z_marginal:.1f}")
    print(f"    If z(marginal) >> 0: genuine RULES beyond marginal frequencies")
    print(f"    If z(marginal) ≈ 0 but z(global) >> 0: just marginal frequency shifts")


# ══════════════════════════════════════════════════════════════════
# 43b: PREDICTIVE ASYMMETRY PERMUTATION TEST
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("43b: PREDICTIVE ASYMMETRY PERMUTATION TEST")
print("    forward H(class_j|class_i)=5.230 < backward 5.319")
print("    Asymmetry = −0.089. Is this real?")
print("    Test 1: Reverse lines → asymmetry should flip sign")
print("    Test 2: Shuffle within lines → asymmetry should → 0")
print("=" * 70)

def compute_asymmetry(line_list):
    """Compute forward - backward conditional entropy for class pairs.
    class = (pfx, sfx). Lower H = better prediction."""
    fwd_src = []
    fwd_tgt = []
    for line in line_list:
        for i in range(len(line['pfx']) - 1):
            cls_i = (line['pfx'][i], line['sfx'][i])
            cls_j = (line['pfx'][i+1], line['sfx'][i+1])
            fwd_src.append(cls_i)
            fwd_tgt.append(cls_j)

    h_fwd = cond_entropy(fwd_tgt, fwd_src)
    h_bwd = cond_entropy(fwd_src, fwd_tgt)
    return h_fwd - h_bwd, h_fwd, h_bwd, len(fwd_src)

# Observed
asym_obs, h_fwd_obs, h_bwd_obs, n_pairs_obs = compute_asymmetry(lines)
print(f"\n  Observed: H(fwd)={h_fwd_obs:.4f}, H(bwd)={h_bwd_obs:.4f}, asym={asym_obs:.4f}")

# Test 1: Reverse all lines
reversed_lines = []
for line in lines:
    rev = dict(line)
    rev['pfx'] = list(reversed(line['pfx']))
    rev['sfx'] = list(reversed(line['sfx']))
    reversed_lines.append(rev)

asym_rev, h_fwd_rev, h_bwd_rev, _ = compute_asymmetry(reversed_lines)
print(f"\n  Reversed: H(fwd)={h_fwd_rev:.4f}, H(bwd)={h_bwd_rev:.4f}, asym={asym_rev:.4f}")
print(f"    Flip check: original sign={'+' if asym_obs > 0 else '-'}, reversed sign={'+' if asym_rev > 0 else '-'}")
if (asym_obs < 0 and asym_rev > 0) or (asym_obs > 0 and asym_rev < 0):
    print(f"    → Sign FLIPPED — genuine directional structure")
else:
    print(f"    → Sign did NOT flip — asymmetry may be a statistical artifact")

# Test 2: Shuffle within lines (destroy order, preserve line composition)
n_shuf_trials = 100
shuf_asymmetries = []
for _ in range(n_shuf_trials):
    shuf_lines = []
    for line in lines:
        n = len(line['pfx'])
        perm = list(range(n))
        random.shuffle(perm)
        sl = dict(line)
        sl['pfx'] = [line['pfx'][p] for p in perm]
        sl['sfx'] = [line['sfx'][p] for p in perm]
        shuf_lines.append(sl)
    a, _, _, _ = compute_asymmetry(shuf_lines)
    shuf_asymmetries.append(a)

z_asym = (asym_obs - np.mean(shuf_asymmetries)) / max(np.std(shuf_asymmetries), 1e-10)
print(f"\n  Shuffled null: mean asym={np.mean(shuf_asymmetries):.4f}±{np.std(shuf_asymmetries):.4f}")
print(f"    z(asymmetry) = {z_asym:.1f}")
print(f"    Observed = {asym_obs:.4f}, null range = [{min(shuf_asymmetries):.4f}, {max(shuf_asymmetries):.4f}]")

# Also compute per-channel asymmetry for sfx→pfx specifically
def compute_channel_asymmetry(line_list):
    """sfx_i→pfx_j channel asymmetry specifically."""
    sfx_i_arr = []
    pfx_j_arr = []
    for line in line_list:
        for i in range(len(line['pfx']) - 1):
            sfx_i_arr.append(line['sfx'][i])
            pfx_j_arr.append(line['pfx'][i+1])

    h_fwd = cond_entropy(pfx_j_arr, sfx_i_arr)  # H(pfx_j | sfx_i)
    h_bwd = cond_entropy(sfx_i_arr, pfx_j_arr)  # H(sfx_i | pfx_j)
    return h_fwd - h_bwd

asym_sp_obs = compute_channel_asymmetry(lines)
asym_sp_rev = compute_channel_asymmetry(reversed_lines)
sp_shuf = []
for _ in range(100):
    shuf_lines = []
    for line in lines:
        n = len(line['pfx'])
        perm = list(range(n))
        random.shuffle(perm)
        sl = dict(line)
        sl['pfx'] = [line['pfx'][p] for p in perm]
        sl['sfx'] = [line['sfx'][p] for p in perm]
        shuf_lines.append(sl)
    sp_shuf.append(compute_channel_asymmetry(shuf_lines))

z_sp = (asym_sp_obs - np.mean(sp_shuf)) / max(np.std(sp_shuf), 1e-10)
print(f"\n  sfx→pfx channel specifically:")
print(f"    Observed asym={asym_sp_obs:.4f}, reversed={asym_sp_rev:.4f}")
print(f"    Shuffled null: {np.mean(sp_shuf):.4f}±{np.std(sp_shuf):.4f}, z={z_sp:.1f}")


# ══════════════════════════════════════════════════════════════════
# 43c: OPTIMAL CLASS COUNT
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("43c: OPTIMAL CLASS COUNT")
print("    Binary A/B captures 35.7%, three A/M/B captures 80.1%.")
print("    What about 4, 5, 6, 7, 8 classes?")
print("    Hierarchical clustering of suffix → following-prefix profiles.")
print("=" * 70)

# Build suffix → following-prefix profile matrix
sfx_all = sorted(set(p['sfx_i'] for p in pairs))
pfx_all = sorted(set(p['pfx_j'] for p in pairs))

# Build transition count matrix
sfx_to_pfx_counts = defaultdict(Counter)
for p in pairs:
    sfx_to_pfx_counts[p['sfx_i']][p['pfx_j']] += 1

# Convert to probability profiles
profiles = {}
for s in sfx_all:
    total = sum(sfx_to_pfx_counts[s].values())
    if total > 0:
        profiles[s] = np.array([sfx_to_pfx_counts[s].get(pf, 0) / total for pf in pfx_all])

# Full MI
sfx_i_arr = [p['sfx_i'] for p in pairs]
pfx_j_arr = [p['pfx_j'] for p in pairs]
mi_full = compute_mi(sfx_i_arr, pfx_j_arr)
print(f"\n  Full MI(sfx→pfx) = {mi_full:.4f} ({len(sfx_all)} suffix values)")

# Jensen-Shannon divergence for clustering
def jsd(p, q):
    m = 0.5 * (p + q)
    kl_pm = np.sum(p * np.log2(np.clip(p / np.clip(m, 1e-10, None), 1e-10, None)))
    kl_qm = np.sum(q * np.log2(np.clip(q / np.clip(m, 1e-10, None), 1e-10, None)))
    return 0.5 * (kl_pm + kl_qm)

# Agglomerative clustering
class Cluster:
    def __init__(self, members, profile, count):
        self.members = members
        self.profile = profile
        self.count = count

# Initialize: each suffix is its own cluster
clusters = {}
for s in sfx_all:
    if s in profiles:
        count = sum(sfx_to_pfx_counts[s].values())
        clusters[s] = Cluster([s], profiles[s], count)

merge_history = []
mi_at_k = {}

def compute_class_mi(cluster_dict):
    """MI between cluster labels and pfx_j."""
    cls_labels = []
    for p in pairs:
        for cname, cl in cluster_dict.items():
            if p['sfx_i'] in cl.members:
                cls_labels.append(cname)
                break
    return compute_mi(cls_labels, pfx_j_arr)

mi_at_k[len(clusters)] = mi_full
print(f"  k={len(clusters):2d} classes: MI={mi_full:.4f} ({mi_full/mi_full*100:.1f}%)")

while len(clusters) > 2:
    # Find the pair with minimum JSD
    cnames = list(clusters.keys())
    best_jsd = float('inf')
    best_pair = None
    for i in range(len(cnames)):
        for j in range(i+1, len(cnames)):
            d = jsd(clusters[cnames[i]].profile, clusters[cnames[j]].profile)
            if d < best_jsd:
                best_jsd = d
                best_pair = (cnames[i], cnames[j])

    # Merge
    c1, c2 = clusters[best_pair[0]], clusters[best_pair[1]]
    new_count = c1.count + c2.count
    new_profile = (c1.profile * c1.count + c2.profile * c2.count) / new_count
    new_name = f"{best_pair[0]}+{best_pair[1]}"
    new_members = c1.members + c2.members
    clusters[new_name] = Cluster(new_members, new_profile, new_count)
    del clusters[best_pair[0]]
    del clusters[best_pair[1]]

    k = len(clusters)
    mi_k = compute_class_mi(clusters)
    mi_at_k[k] = mi_k
    merge_msg = f"  k={k:2d} classes: MI={mi_k:.4f} ({mi_k/mi_full*100:.1f}%)"
    merge_msg += f"  [merged: {sorted(c1.members)} + {sorted(c2.members)} → JSD={best_jsd:.4f}]"
    merge_history.append((k, mi_k, best_jsd, sorted(c1.members), sorted(c2.members)))

    if k <= 8 or k == len(sfx_all) - 1:
        print(merge_msg)

# Print elbow analysis
print(f"\n  k={2:2d} classes: MI={mi_at_k[2]:.4f} ({mi_at_k[2]/mi_full*100:.1f}%)")

print(f"\n  Elbow analysis (MI % captured):")
for k in sorted(mi_at_k.keys()):
    pct = mi_at_k[k] / mi_full * 100
    bar = '#' * int(pct / 2)
    print(f"    k={k:2d}: {pct:5.1f}% {bar}")

# Identify sharpest drop
drops = []
ks = sorted(mi_at_k.keys())
for i in range(len(ks) - 1):
    drop = mi_at_k[ks[i+1]] - mi_at_k[ks[i]]
    drops.append((ks[i], ks[i+1], drop))
drops.sort(key=lambda x: x[2])  # biggest drops (most negative) first
print(f"\n  Biggest MI drops (merging from k to k-1):")
for k_from, k_to, drop in drops[:5]:
    pct_drop = drop / mi_full * 100
    print(f"    k={k_from} → k={k_to}: ΔMI={drop:.4f} ({pct_drop:+.1f}%)")


# ══════════════════════════════════════════════════════════════════
# 43d: SYNERGY BOOTSTRAP
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("43d: SYNERGY BOOTSTRAP")
print("    Bootstrap CIs for synergy values.")
print("    Is 'chdy qoain' (synergy=2.63, N=38) robust?")
print("=" * 70)

# Define the bigrams to test (from two_class_section_grammar part c)
test_bigrams = [
    ("chol", "daiin"),
    ("shdy", "qody"),
    ("shy", "qoain"),
    ("oX", "Xiin"),
    ("shdy", "qoaiin"),
    ("chol", "chol"),
    ("qody", "qody"),
    ("ody", "qody"),
    ("chdy", "qoain"),
    ("daiin", "chol"),
]

# Build class representation for each pair
def parse_class(word_str):
    """Parse 'chol' into (pfx='ch', sfx='ol'), 'qody' into (pfx='qo', sfx='dy')"""
    for p in ['qo','lch','lsh','sh','ch','so','do','q','o','d','y','l']:
        if word_str.startswith(p):
            rest = word_str[len(p):]
            if rest == '':
                rest = 'X'
            return (p, rest)
    return ('X', word_str if word_str != 'X' else 'X')

# Pre-compute observed frequencies
N_total = len(pairs)
class_pair_counts = Counter()
pfx_pair_counts = Counter()
sfx_pair_counts = Counter()

for p in pairs:
    cls_i = (p['pfx_i'], p['sfx_i'])
    cls_j = (p['pfx_j'], p['sfx_j'])
    class_pair_counts[(cls_i, cls_j)] += 1
    pfx_pair_counts[(p['pfx_i'], p['pfx_j'])] += 1
    sfx_pair_counts[(p['sfx_i'], p['sfx_j'])] += 1

cls_i_counts = Counter()
cls_j_counts = Counter()
pfx_i_counts = Counter()
pfx_j_counts = Counter()
sfx_i_counts = Counter()
sfx_j_counts = Counter()
for p in pairs:
    cls_i_counts[(p['pfx_i'], p['sfx_i'])] += 1
    cls_j_counts[(p['pfx_j'], p['sfx_j'])] += 1
    pfx_i_counts[p['pfx_i']] += 1
    pfx_j_counts[p['pfx_j']] += 1
    sfx_i_counts[p['sfx_i']] += 1
    sfx_j_counts[p['sfx_j']] += 1

def compute_synergy_from_counts(cls_pair_ct, pfx_pair_ct, sfx_pair_ct,
                                 cls_i_ct, cls_j_ct, pfx_i_ct, pfx_j_ct,
                                 sfx_i_ct, sfx_j_ct, N, ci, cj):
    """Compute synergy for class pair (ci, cj)."""
    pi, si = ci
    pj, sj = cj

    # Class ratio: P(cls_j|cls_i) / P(cls_j)
    n_ci = cls_i_ct.get(ci, 0)
    n_cj = cls_j_ct.get(cj, 0)
    n_cicj = cls_pair_ct.get((ci, cj), 0)
    if n_ci == 0 or n_cj == 0: return None
    p_cj = n_cj / N
    p_cj_given_ci = n_cicj / n_ci
    cls_ratio = p_cj_given_ci / p_cj if p_cj > 0 else 0

    # Prefix ratio: P(pfx_j|pfx_i) / P(pfx_j)
    n_pi = pfx_i_ct.get(pi, 0)
    n_pj = pfx_j_ct.get(pj, 0)
    n_pipj = pfx_pair_ct.get((pi, pj), 0)
    if n_pi == 0 or n_pj == 0: return None
    p_pj = n_pj / N
    p_pj_given_pi = n_pipj / n_pi
    pfx_ratio = p_pj_given_pi / p_pj if p_pj > 0 else 0

    # Suffix ratio: P(sfx_j|sfx_i) / P(sfx_j)
    n_si = sfx_i_ct.get(si, 0)
    n_sj = sfx_j_ct.get(sj, 0)
    n_sisj = sfx_pair_ct.get((si, sj), 0)
    if n_si == 0 or n_sj == 0: return None
    p_sj = n_sj / N
    p_sj_given_si = n_sisj / n_si
    sfx_ratio = p_sj_given_si / p_sj if p_sj > 0 else 0

    product = pfx_ratio * sfx_ratio
    synergy = cls_ratio / product if product > 0 else 0
    return synergy

print()
n_boot = 500

# Vectorize: pre-encode all pair features as integer arrays for fast bootstrap
all_pfx_i_vals = sorted(set(p['pfx_i'] for p in pairs))
all_pfx_j_vals = sorted(set(p['pfx_j'] for p in pairs))
all_sfx_i_vals = sorted(set(p['sfx_i'] for p in pairs))
all_sfx_j_vals = sorted(set(p['sfx_j'] for p in pairs))

pfx_i_to_idx = {v: i for i, v in enumerate(all_pfx_i_vals)}
pfx_j_to_idx = {v: i for i, v in enumerate(all_pfx_j_vals)}
sfx_i_to_idx = {v: i for i, v in enumerate(all_sfx_i_vals)}
sfx_j_to_idx = {v: i for i, v in enumerate(all_sfx_j_vals)}

# Encode all pairs as flat integer arrays
arr_pfx_i = np.array([pfx_i_to_idx[p['pfx_i']] for p in pairs])
arr_pfx_j = np.array([pfx_j_to_idx[p['pfx_j']] for p in pairs])
arr_sfx_i = np.array([sfx_i_to_idx[p['sfx_i']] for p in pairs])
arr_sfx_j = np.array([sfx_j_to_idx[p['sfx_j']] for p in pairs])

# Encode class pairs: (pfx_i, sfx_i) and (pfx_j, sfx_j) as single ints
n_pi = len(all_pfx_i_vals)
n_si = len(all_sfx_i_vals)
n_pj = len(all_pfx_j_vals)
n_sj = len(all_sfx_j_vals)
arr_cls_i = arr_pfx_i * n_si + arr_sfx_i
arr_cls_j = arr_pfx_j * n_sj + arr_sfx_j
n_cls_i = n_pi * n_si
n_cls_j = n_pj * n_sj

def fast_synergy(idx, ci_pi, ci_si, cj_pj, cj_sj):
    """Compute synergy for a specific class pair using indexed arrays."""
    sub_pfx_i = arr_pfx_i[idx]
    sub_pfx_j = arr_pfx_j[idx]
    sub_sfx_i = arr_sfx_i[idx]
    sub_sfx_j = arr_sfx_j[idx]
    sub_cls_i = arr_cls_i[idx]
    sub_cls_j = arr_cls_j[idx]
    N = len(idx)

    ci_code = ci_pi * n_si + ci_si
    cj_code = cj_pj * n_sj + cj_sj

    # Class counts
    n_ci = np.sum(sub_cls_i == ci_code)
    n_cj = np.sum(sub_cls_j == cj_code)
    n_cicj = np.sum((sub_cls_i == ci_code) & (sub_cls_j == cj_code))
    if n_ci == 0 or n_cj == 0:
        return None
    cls_ratio = (n_cicj / n_ci) / (n_cj / N)

    # Prefix counts
    n_pi_ct = np.sum(sub_pfx_i == ci_pi)
    n_pj_ct = np.sum(sub_pfx_j == cj_pj)
    n_pipj = np.sum((sub_pfx_i == ci_pi) & (sub_pfx_j == cj_pj))
    if n_pi_ct == 0 or n_pj_ct == 0:
        return None
    pfx_ratio = (n_pipj / n_pi_ct) / (n_pj_ct / N)

    # Suffix counts
    n_si_ct = np.sum(sub_sfx_i == ci_si)
    n_sj_ct = np.sum(sub_sfx_j == cj_sj)
    n_sisj = np.sum((sub_sfx_i == ci_si) & (sub_sfx_j == cj_sj))
    if n_si_ct == 0 or n_sj_ct == 0:
        return None
    sfx_ratio = (n_sisj / n_si_ct) / (n_sj_ct / N)

    product = pfx_ratio * sfx_ratio
    return cls_ratio / product if product > 0 else None

all_idx = np.arange(N_total)

for word_i_str, word_j_str in test_bigrams:
    ci = parse_class(word_i_str)
    cj = parse_class(word_j_str)
    count = class_pair_counts.get((ci, cj), 0)

    # Encode to integer indices
    ci_pi = pfx_i_to_idx.get(ci[0])
    ci_si = sfx_i_to_idx.get(ci[1])
    cj_pj = pfx_j_to_idx.get(cj[0])
    cj_sj = sfx_j_to_idx.get(cj[1])
    if any(x is None for x in [ci_pi, ci_si, cj_pj, cj_sj]):
        print(f"  '{word_i_str} {word_j_str}': missing index mapping")
        continue

    obs_syn = fast_synergy(all_idx, ci_pi, ci_si, cj_pj, cj_sj)
    if obs_syn is None or count < 5:
        print(f"  '{word_i_str} {word_j_str}': N={count}, too few or missing")
        continue

    # Bootstrap
    boot_syns = []
    for _ in range(n_boot):
        idx = np.random.choice(N_total, N_total, replace=True)
        s = fast_synergy(idx, ci_pi, ci_si, cj_pj, cj_sj)
        if s is not None:
            boot_syns.append(s)

    if len(boot_syns) < 100:
        print(f"  '{word_i_str} {word_j_str}': N={count}, insufficient bootstrap samples")
        continue

    lo = np.percentile(boot_syns, 2.5)
    hi = np.percentile(boot_syns, 97.5)
    print(f"  '{word_i_str} {word_j_str}': N={count}, synergy={obs_syn:.2f}, 95% CI=[{lo:.2f}, {hi:.2f}]"
          f"{'  *** sig > 1.0' if lo > 1.0 else ''}")


# ══════════════════════════════════════════════════════════════════
# 43e: TOP SECTION DISCRIMINATORS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("43e: TOP SECTION DISCRIMINATORS")
print("    Which sfx→pfx transitions contribute most to section differences?")
print("    Show conditionals P(pfx_j|sfx_i) per section for top transitions.")
print("=" * 70)

# For each section, compute P(pfx_j|sfx_i) and compare to global
# Find the transitions with largest absolute deviation from global

global_joint = Counter((p['sfx_i'], p['pfx_j']) for p in pairs)
global_sfx = Counter(p['sfx_i'] for p in pairs)

# Global conditionals
global_cond = {}
for s in sfx_all:
    for pf in pfx_all:
        denom = global_sfx[s]
        if denom > 0:
            global_cond[(s, pf)] = global_joint[(s, pf)] / denom
        else:
            global_cond[(s, pf)] = 0.0

# Per-section conditionals and deviations
all_devs = []  # (section, sfx, pfx, obs_cond, global_cond, deviation, N_sfx_in_sec)

for sec in major_sections:
    sec_pairs_list = [p for p in pairs if p['section'] == sec]
    sec_joint = Counter((p['sfx_i'], p['pfx_j']) for p in sec_pairs_list)
    sec_sfx_ct = Counter(p['sfx_i'] for p in sec_pairs_list)

    for s in sfx_all:
        for pf in pfx_all:
            denom = sec_sfx_ct[s]
            if denom < 20:  # need reasonable count
                continue
            obs = sec_joint[(s, pf)] / denom
            glob = global_cond.get((s, pf), 0.0)
            dev = obs - glob
            all_devs.append((sec, s, pf, obs, glob, dev, denom))

# Sort by absolute deviation
all_devs.sort(key=lambda x: abs(x[5]), reverse=True)

print(f"\n  Top 20 section-discriminating transitions:")
print(f"  {'Section':<12} {'sfx→pfx':<12} {'P(sec)':<8} {'P(global)':<10} {'Δ':>8} {'N(sfx)':<8}")
print(f"  {'-'*60}")
for sec, s, pf, obs, glob, dev, n_sfx in all_devs[:20]:
    print(f"  {sec:<12} {s}→{pf:<6} {obs:>.3f}    {glob:.3f}      {dev:>+.3f}  {n_sfx:<8}")

# Now check: are these deviations from different conditionals or marginals?
# If only marginals differ: P(pfx|sfx,sec) ≈ P(pfx|sfx) always.
# The deviation IS the conditional difference. But is the deviation driven
# by sfx having different frequency, or by genuinely different P(pfx|sfx)?
print(f"\n  Marginal frequency comparison (top discriminating suffix values):")
top_sfx_secs = set((d[0], d[1]) for d in all_devs[:20])
for sec, sfx_val in sorted(top_sfx_secs):
    sec_pairs_list = [p for p in pairs if p['section'] == sec]
    sec_sfx_ct = Counter(p['sfx_i'] for p in sec_pairs_list)
    n_sec = len(sec_pairs_list)
    n_glob = len(pairs)
    frac_sec = sec_sfx_ct[sfx_val] / n_sec if n_sec > 0 else 0
    frac_glob = global_sfx[sfx_val] / n_glob
    print(f"    {sec:<12} suffix '{sfx_val}': {frac_sec:.3f} (section) vs {frac_glob:.3f} (global)"
          f"  ratio={frac_sec/frac_glob:.2f}x" if frac_glob > 0 else "")

# KEY TEST: Compare section conditionals after matching marginals
# For each section's top deviations, compute expected deviation from marginals alone
print(f"\n  Decomposition: Is the deviation from conditionals or marginals?")
print(f"  For each top transition, expected = P(pfx_j,sec) / P(pfx_j,global)")
print(f"  If actual_dev >> expected_dev → genuine conditional difference")

for sec in major_sections:
    sec_pairs_list = [p for p in pairs if p['section'] == sec]
    sec_pfx_j_ct = Counter(p['pfx_j'] for p in sec_pairs_list)
    n_sec = len(sec_pairs_list)
    global_pfx_j_ct = Counter(p['pfx_j'] for p in pairs)
    n_glob = len(pairs)

    sec_devs = [d for d in all_devs[:20] if d[0] == sec]
    if not sec_devs:
        continue
    print(f"\n  {sec}:")
    for _, s, pf, obs, glob, dev, n_sfx in sec_devs[:5]:
        # What would P(pfx|sfx) be if the section just had different pfx marginals
        # but same conditionals as global?
        pfx_ratio = (sec_pfx_j_ct[pf] / n_sec) / (global_pfx_j_ct[pf] / n_glob) if global_pfx_j_ct[pf] > 0 else 1.0
        expected_obs = glob * pfx_ratio  # if conditional same but marginal different
        marginal_dev = expected_obs - glob
        conditional_dev = dev - marginal_dev
        print(f"    {s}→{pf}: actual_Δ={dev:+.3f}, marginal_Δ={marginal_dev:+.3f}, "
              f"conditional_Δ={conditional_dev:+.3f}")


# ══════════════════════════════════════════════════════════════════
# SYNTHESIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("word_class_robustness SYNTHESIS")
print("=" * 70)

print("""
  43a: SECTION GRAMMAR — MARGINALS vs RULES
    (See section results above. If z(marginal) >> 0 → real rules)

  43b: PREDICTIVE ASYMMETRY
    (See reversal and shuffle tests above)

  43c: OPTIMAL CLASS COUNT
    (See elbow analysis above)

  43d: SYNERGY BOOTSTRAP
    (See CIs above)

  43e: SECTION DISCRIMINATORS
    (See conditional decomposition above)

[word_class_robustness Complete]
""")
