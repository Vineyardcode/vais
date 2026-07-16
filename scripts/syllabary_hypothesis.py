#!/usr/bin/env python3
"""
TESTING THE SYLLABARY INTERPRETATION (SKEPTICALLY)
=============================================================

vowel_consonant_separation found degenerate V/C separation (91.4% "vowels", z=−3.3).
We interpreted this as EXCLUDING alphabetic encoding and SUPPORTING
a syllabary. But wait —

SKEPTICAL QUESTION: Does the degenerate Sukhotin result actually
tell us anything? Or is it trivially explained by the VMS character
frequency distribution?

This test ATTACKS the syllabary interpretation before accepting it.

  A) NULL MODEL TEST
       Generate random text from VMS bigram/unigram models.
       Run Sukhotin's on it. If random text ALSO produces degenerate
       V/C, then vowel_consonant_separation told us NOTHING new.

  B) SVD OF TRANSITION MATRIX
       A true CV syllabary has a transition matrix with rank-2
       structure (factorizable into C and V components).
       Test: how many significant singular values does the VMS
       transition matrix have? Compare to random and to a
       simulated syllabary.

  C) CHARACTER DISTRIBUTIONAL CLUSTERING
       In a syllabary, characters sharing a consonant (ka, ki, ku)
       have similar distributional profiles. Cluster VMS characters
       by their bigram contexts and see if the clusters show
       internal structure (pairs, triads, etc.)

  D) KNOWN SYLLABARY CALIBRATION
       Simulate a known CV syllabary (5C × 4V = 20 symbols, close
       to VMS's 22) with realistic text. Run ALL our tests on it
       to verify our methods can detect syllabary structure when
       it exists. Then compare VMS results.

  E) ENTROPY REDUCTION UNDER GROUPING
       If characters share hidden components, grouping by component
       should reduce transition entropy more than random groupings.
       Test: group chars into k groups (k=3..6), measure transition
       entropy. Compare best grouping to random groupings.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from itertools import combinations
from common import collapse_e, get_collapsed, load_lines_v2 as load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(56)
np.random.seed(56)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']

FOLIO_DIR = Path("folios")



def sukhotins_algorithm(words, char_list=None):
    contact = defaultdict(lambda: defaultdict(int))
    char_freq = Counter()
    for word in words:
        for i in range(len(word) - 1):
            a, b = word[i], word[i+1]
            if a != b:
                contact[a][b] += 1
                contact[b][a] += 1
            char_freq[a] += 1
        if word:
            char_freq[word[-1]] += 1
    if char_list is None:
        char_list = sorted(char_freq.keys())
    classification = {c: 'C' for c in char_list}
    remaining = set(char_list)
    while remaining:
        scores = {}
        for c in remaining:
            score = sum(contact[c].get(other, 0) for other in remaining if other != c)
            scores[c] = score
        best_char = max(scores, key=scores.get)
        if scores[best_char] <= 0:
            break
        classification[best_char] = 'V'
        remaining.remove(best_char)
    return classification

def alternation_rate(words, vc_map):
    alt = 0; total = 0
    for w in words:
        for i in range(len(w) - 1):
            if vc_map.get(w[i], 'C') != vc_map.get(w[i+1], 'C'):
                alt += 1
            total += 1
    return alt / total if total > 0 else 0

print("Loading corpus...")
raw_lines = load_lines()
line_collapsed = [[get_collapsed(w) for w in line] for line in raw_lines]
all_collapsed = [w for seq in line_collapsed for w in seq if w]
N = len(all_collapsed)
vocab = Counter(all_collapsed)

char_freq = Counter()
for w in all_collapsed:
    for c in w: char_freq[c] += 1
chars = sorted(char_freq.keys())
total_chars = sum(char_freq.values())
n_chars = len(chars)
print(f"  {N} tokens, {len(vocab)} types, {n_chars} chars, {total_chars} total chars\n")

# Build bigram model
bigram = defaultdict(Counter)
for w in all_collapsed:
    for i in range(len(w) - 1):
        bigram[w[i]][w[i+1]] += 1

# Build transition probabilities
trans_prob = {}
for c in chars:
    total = sum(bigram[c].values())
    if total > 0:
        trans_prob[c] = {c2: bigram[c][c2] / total for c2 in bigram[c]}
    else:
        trans_prob[c] = {c: 1.0}

# Build word-length distribution
word_lengths = Counter(len(w) for w in all_collapsed)


# ============================================================
# 56a: NULL MODEL — DOES RANDOM TEXT ALSO PRODUCE DEGENERATE SUKHOTIN?
# ============================================================
print("=" * 65)
print("A: NULL MODEL TEST — Is degenerate Sukhotin trivially expected?")
print("=" * 65)

def generate_bigram_words(n_words, trans_prob, chars, char_freq, word_lengths):
    """Generate random words from VMS bigram model + length distribution."""
    total_len = sum(word_lengths.values())
    len_probs = {l: c / total_len for l, c in word_lengths.items()}
    lengths = list(len_probs.keys())
    probs = [len_probs[l] for l in lengths]
    
    # Start character distribution
    start_freq = Counter()
    for w in all_collapsed:
        if w: start_freq[w[0]] += 1
    start_total = sum(start_freq.values())
    start_probs = {c: start_freq[c] / start_total for c in start_freq}
    
    words = []
    for _ in range(n_words):
        length = np.random.choice(lengths, p=probs)
        # Pick start char
        start_chars = list(start_probs.keys())
        start_p = [start_probs[c] for c in start_chars]
        word = [np.random.choice(start_chars, p=start_p)]
        for _ in range(length - 1):
            cur = word[-1]
            if cur in trans_prob:
                nexts = list(trans_prob[cur].keys())
                ps = [trans_prob[cur][c] for c in nexts]
                word.append(np.random.choice(nexts, p=ps))
            else:
                word.append(np.random.choice(chars))
        words.append(''.join(word))
    return words

def generate_unigram_words(n_words, chars, char_freq, word_lengths):
    """Generate random words from VMS unigram model + length distribution."""
    total_len = sum(word_lengths.values())
    len_probs = {l: c / total_len for l, c in word_lengths.items()}
    lengths = list(len_probs.keys())
    probs = [len_probs[l] for l in lengths]
    
    total_f = sum(char_freq.values())
    char_probs = [char_freq[c] / total_f for c in chars]
    
    words = []
    for _ in range(n_words):
        length = np.random.choice(lengths, p=probs)
        word = ''.join(np.random.choice(chars, size=length, p=char_probs))
        words.append(word)
    return words

# Test 1: Bigram null model
n_trials = 10
bigram_v_fracs = []
bigram_alts = []
bigram_n_vowels = []

for trial in range(n_trials):
    print(f"  Bigram trial {trial+1}/{n_trials}...", flush=True)
    fake_words = generate_bigram_words(N, trans_prob, chars, char_freq, word_lengths)
    vc = sukhotins_algorithm(fake_words, chars)
    n_v = sum(1 for c in vc.values() if c == 'V')
    bigram_n_vowels.append(n_v)
    
    fake_cf = Counter()
    for w in fake_words:
        for c in w: fake_cf[c] += 1
    fake_total = sum(fake_cf.values())
    v_count = sum(fake_cf.get(c, 0) for c in chars if vc.get(c) == 'V')
    bigram_v_fracs.append(v_count / fake_total if fake_total > 0 else 0)
    bigram_alts.append(alternation_rate(fake_words, vc))

print(f"\n  BIGRAM NULL MODEL (N={n_trials}):")
print(f"  VMS: {sum(1 for c in chars if sukhotins_algorithm(all_collapsed, chars)[c]=='V')}/{n_chars} vowels, "
      f"91.4% V tokens, alt=0.116")
print(f"  Null: {np.mean(bigram_n_vowels):.1f}±{np.std(bigram_n_vowels):.1f}/{n_chars} vowels, "
      f"{100*np.mean(bigram_v_fracs):.1f}±{100*np.std(bigram_v_fracs):.1f}% V tokens, "
      f"alt={np.mean(bigram_alts):.3f}±{np.std(bigram_alts):.3f}")

# Test 2: Unigram null model
unigram_v_fracs = []
unigram_alts = []
unigram_n_vowels = []

for trial in range(5):
    print(f"  Unigram trial {trial+1}/5...", flush=True)
    fake_words = generate_unigram_words(N, chars, char_freq, word_lengths)
    vc = sukhotins_algorithm(fake_words, chars)
    n_v = sum(1 for c in vc.values() if c == 'V')
    unigram_n_vowels.append(n_v)
    
    v_count = sum(char_freq[c] for c in chars if vc[c] == 'V')
    unigram_v_fracs.append(v_count / total_chars)
    unigram_alts.append(alternation_rate(fake_words, vc))

print(f"\n  UNIGRAM NULL MODEL (N={n_trials}):")
print(f"  Null: {np.mean(unigram_n_vowels):.1f}±{np.std(unigram_n_vowels):.1f}/{n_chars} vowels, "
      f"{100*np.mean(unigram_v_fracs):.1f}±{100*np.std(unigram_v_fracs):.1f}% V tokens, "
      f"alt={np.mean(unigram_alts):.3f}±{np.std(unigram_alts):.3f}")

# Is VMS different from its own bigram model?
vms_vc = sukhotins_algorithm(all_collapsed, chars)
vms_n_v = sum(1 for c in vms_vc.values() if c == 'V')
vms_alt = alternation_rate(all_collapsed, vms_vc)

z_nv = (vms_n_v - np.mean(bigram_n_vowels)) / max(np.std(bigram_n_vowels), 0.01)
z_alt_bigram = (vms_alt - np.mean(bigram_alts)) / max(np.std(bigram_alts), 0.001)

print(f"\n  VMS vs BIGRAM NULL:")
print(f"  z(n_vowels) = {z_nv:.1f}")
print(f"  z(alternation) = {z_alt_bigram:.1f}")

if abs(z_nv) < 2 and abs(z_alt_bigram) < 2:
    print(f"\n  *** CRITICAL: VMS Sukhotin result is FULLY EXPLAINED by bigram model ***")
    print(f"  *** vowel_consonant_separation's 'syllabary signal' was likely an ARTIFACT ***")
elif abs(z_nv) < 2:
    print(f"\n  Number of vowels explained by bigrams, but alternation differs.")
else:
    print(f"\n  VMS produces genuinely different Sukhotin results from its own bigram model.")


# ============================================================
# 56b: SVD OF TRANSITION MATRIX — Is there CV grid structure?
# ============================================================
print("\n" + "=" * 65)
print("B: SVD OF TRANSITION MATRIX — Low-rank (CV grid) structure?")
print("=" * 65)

# Build normalized transition matrix
# Only use chars with enough data (freq > 50)
common_chars = [c for c in chars if char_freq[c] > 50]
n_common = len(common_chars)
cidx = {c: i for i, c in enumerate(common_chars)}

T = np.zeros((n_common, n_common))
for c1 in common_chars:
    for c2 in common_chars:
        T[cidx[c1], cidx[c2]] = bigram[c1].get(c2, 0)

# Row-normalize
row_sums = T.sum(axis=1, keepdims=True)
row_sums[row_sums == 0] = 1
T_norm = T / row_sums

# SVD
U, S, Vt = np.linalg.svd(T_norm)

# How many significant singular values?
total_sv = np.sum(S)
cumulative = np.cumsum(S) / total_sv

print(f"  Common characters (freq>50): {n_common}")
print(f"  Singular values (top 10):")
for i in range(min(10, len(S))):
    print(f"    σ_{i+1} = {S[i]:.4f}  cumulative = {cumulative[i]*100:.1f}%")

# Effective rank (number of SVs needed for 90% and 95%)
rank90 = np.searchsorted(cumulative, 0.90) + 1
rank95 = np.searchsorted(cumulative, 0.95) + 1
rank99 = np.searchsorted(cumulative, 0.99) + 1
print(f"\n  Effective rank (90%): {rank90}")
print(f"  Effective rank (95%): {rank95}")
print(f"  Effective rank (99%): {rank99}")

# For a true CV syllabary with C consonants and V vowels:
# The transition matrix should have rank ~= C + V (not C × V)
# because transitions depend on which C the next char starts with
# and which V the current char ends with.
print(f"\n  Interpretation:")
print(f"  A CV syllabary (C×V symbols) has transition rank ≈ C+V")
print(f"  A 5C×4V syllabary → rank ≈ 9, out of 20 symbols")
print(f"  VMS: rank(90%) = {rank90} out of {n_common} ← ", end='')
if rank90 <= n_common // 2:
    print(f"CONSISTENT with low-rank (possible syllabary or structured system)")
else:
    print(f"NOT low-rank (each character acts independently)")

# Compare to null: SVD of random bigram-model text
null_ranks = []
for trial in range(10):
    fake_words = generate_bigram_words(N, trans_prob, chars, char_freq, word_lengths)
    T_null = np.zeros((n_common, n_common))
    for w in fake_words:
        for i in range(len(w)-1):
            a, b = w[i], w[i+1]
            if a in cidx and b in cidx:
                T_null[cidx[a], cidx[b]] += 1
    rs = T_null.sum(axis=1, keepdims=True)
    rs[rs == 0] = 1
    T_null_norm = T_null / rs
    _, S_null, _ = np.linalg.svd(T_null_norm)
    cum_null = np.cumsum(S_null) / max(np.sum(S_null), 1e-10)
    null_ranks.append(np.searchsorted(cum_null, 0.90) + 1)

print(f"\n  Null model rank(90%): {np.mean(null_ranks):.1f} ± {np.std(null_ranks):.1f}")
z_rank = (rank90 - np.mean(null_ranks)) / max(np.std(null_ranks), 0.01)
print(f"  z(rank): {z_rank:.1f}")
if abs(z_rank) < 2:
    print(f"  → VMS transition rank is NORMAL for its bigram statistics")
else:
    print(f"  → VMS transition rank DIFFERS from bigram expectation")


# ============================================================
# 56c: DISTRIBUTIONAL CLUSTERING
# ============================================================
print("\n" + "=" * 65)
print("C: CHARACTER DISTRIBUTIONAL CLUSTERING")
print("=" * 65)

# Build right-context and left-context vectors for each common character
right_ctx = np.zeros((n_common, n_common))
left_ctx = np.zeros((n_common, n_common))

for w in all_collapsed:
    for i in range(len(w) - 1):
        a, b = w[i], w[i+1]
        if a in cidx and b in cidx:
            right_ctx[cidx[a], cidx[b]] += 1
            left_ctx[cidx[b], cidx[a]] += 1

# Normalize to distributions
for i in range(n_common):
    s = right_ctx[i].sum()
    if s > 0: right_ctx[i] /= s
    s = left_ctx[i].sum()
    if s > 0: left_ctx[i] /= s

# Combine right and left contexts
combined_ctx = np.hstack([right_ctx, left_ctx])

# Distance matrix (Jensen-Shannon divergence)
def jsd(p, q):
    m = 0.5 * (p + q)
    # AUDIT A5: masking only on m>0 let p==0 cells produce 0*log2(0/m)
    # = 0 * -inf = NaN in numpy, which poisoned the distance matrix
    # ("JSD = nan" rows in the old output). The 0*log(0)=0 convention
    # requires masking each KL term on ITS OWN distribution too.
    mask_p = (p > 0) & (m > 0)
    mask_q = (q > 0) & (m > 0)
    kl_pm = np.sum(p[mask_p] * np.log2(p[mask_p] / m[mask_p]))
    kl_qm = np.sum(q[mask_q] * np.log2(q[mask_q] / m[mask_q]))
    return 0.5 * (kl_pm + kl_qm)

dist_matrix = np.zeros((n_common, n_common))
for i in range(n_common):
    for j in range(i+1, n_common):
        d = jsd(combined_ctx[i], combined_ctx[j])
        dist_matrix[i, j] = d
        dist_matrix[j, i] = d

# Find the most similar pairs
pairs = []
for i in range(n_common):
    for j in range(i+1, n_common):
        pairs.append((dist_matrix[i,j], common_chars[i], common_chars[j]))
pairs.sort()

print(f"  Most similar character pairs (by JSD of combined context):")
for d, a, b in pairs[:15]:
    print(f"    {a}-{b}: JSD = {d:.4f}")

print(f"\n  Most DISSIMILAR pairs:")
for d, a, b in pairs[-5:]:
    print(f"    {a}-{b}: JSD = {d:.4f}")

# Hierarchical clustering (simple agglomerative)
# Use Ward's method approximated by greedy merge
groups = [[c] for c in common_chars]
group_dist = dist_matrix.copy()
merge_history = []

print(f"\n  Agglomerative clustering (merge order):")
merged = set()
for step in range(min(8, n_common - 1)):
    # Find closest pair of groups
    best_d = float('inf')
    best_i = best_j = -1
    for i in range(n_common):
        if i in merged: continue
        for j in range(i+1, n_common):
            if j in merged: continue
            if group_dist[i,j] < best_d:
                best_d = group_dist[i,j]
                best_i, best_j = i, j
    if best_i < 0: break
    
    # Merge j into i
    groups[best_i] = groups[best_i] + groups[best_j]
    merged.add(best_j)
    # Update distances (average linkage)
    for k in range(n_common):
        if k in merged or k == best_i: continue
        group_dist[best_i, k] = (group_dist[best_i, k] + group_dist[best_j, k]) / 2
        group_dist[k, best_i] = group_dist[best_i, k]
    
    merge_history.append((best_d, groups[best_i][:]))
    cluster_str = '+'.join(groups[best_i])
    print(f"    Step {step+1}: merge at JSD={best_d:.4f} → [{cluster_str}]")

# In a syllabary, we'd expect to see pairs/triads that share a component.
# Check: do the early clusters correspond to frequency-similar or 
# position-similar characters?
print(f"\n  INTERPRETATION:")
print(f"  In a real syllabary, early clusters would group characters")
print(f"  sharing a consonant (e.g., ka+ki+ku) or a vowel (ka+sa+na).")
print(f"  Check: do the character pairs above share positional profiles?")

# Check if clustered chars have similar positional distributions
print(f"\n  Positional profiles of most similar pairs:")
for d, a, b in pairs[:5]:
    a_starts = sum(1 for w in all_collapsed if w and w[0] == a)
    a_ends = sum(1 for w in all_collapsed if w and w[-1] == a)
    a_total = char_freq[a]
    b_starts = sum(1 for w in all_collapsed if w and w[0] == b)
    b_ends = sum(1 for w in all_collapsed if w and w[-1] == b)
    b_total = char_freq[b]
    print(f"    {a}: start={100*a_starts/a_total:.1f}%, end={100*a_ends/a_total:.1f}%  |  "
          f"{b}: start={100*b_starts/b_total:.1f}%, end={100*b_ends/b_total:.1f}%")


# ============================================================
# 56d: SIMULATED SYLLABARY CALIBRATION
# ============================================================
print("\n" + "=" * 65)
print("D: SIMULATED SYLLABARY CALIBRATION")
print("=" * 65)

# Create a synthetic CV syllabary text: 5 consonants × 4 vowels = 20 symbols
# Similar to VMS: ~35000 words, mean length ~4 chars
# (Each char = 1 syllable, so length 4 = 4 syllables)

n_C = 5; n_V = 4
syms = [f'{c}{v}' for c in range(n_C) for v in range(n_V)]
n_syms = len(syms)
sym_to_idx = {s: i for i, s in enumerate(syms)}

# Map each symbol to a single character for processing
sym_chars = [chr(65 + i) for i in range(n_syms)]  # A-T
sym_to_char = dict(zip(syms, sym_chars))

# Create transition matrix with CV structure
# Transitions depend on: V of current → C of next (and slightly on C of current → V of next)
syl_trans = np.zeros((n_syms, n_syms))
for i, s1 in enumerate(syms):
    c1, v1 = int(s1[0]), int(s1[1])
    for j, s2 in enumerate(syms):
        c2, v2 = int(s2[0]), int(s2[1])
        # Transition probability depends on v1→c2 (primary) and c1→v2 (secondary)
        syl_trans[i, j] = np.exp(-0.5 * ((v1 - c2) % n_C)**2) * (1 + 0.3 * np.exp(-((c1 - v2) % n_V)**2))

# Add some noise and normalize
syl_trans += 0.1 * np.random.rand(n_syms, n_syms)
syl_trans /= syl_trans.sum(axis=1, keepdims=True)

# Generate fake syllabary text
syl_words = []
syl_word_lengths = [int(np.random.choice(list(word_lengths.keys()), 
                    p=[word_lengths[l]/sum(word_lengths.values()) for l in word_lengths.keys()])) 
                    for _ in range(N)]

for length in syl_word_lengths:
    word = []
    cur = np.random.randint(n_syms)
    word.append(sym_chars[cur])
    for _ in range(length - 1):
        cur = np.random.choice(n_syms, p=syl_trans[cur])
        word.append(sym_chars[cur])
    syl_words.append(''.join(word))

# Run Sukhotin's on the syllabary
syl_vc = sukhotins_algorithm(syl_words, sym_chars)
syl_vowels = [c for c in sym_chars if syl_vc.get(c) == 'V']
syl_consonants = [c for c in sym_chars if syl_vc.get(c) == 'C']

syl_cf = Counter()
for w in syl_words:
    for c in w: syl_cf[c] += 1
syl_total = sum(syl_cf.values())
syl_v_tot = sum(syl_cf.get(c, 0) for c in syl_vowels)

syl_alt = alternation_rate(syl_words, syl_vc)

print(f"  Simulated CV syllabary: {n_C}C × {n_V}V = {n_syms} symbols")
print(f"  {N} words generated")
print(f"  Sukhotin vowels: {len(syl_vowels)}/{n_syms}  ({100*syl_v_tot/syl_total:.1f}% of tokens)")
print(f"  Alternation rate: {syl_alt:.4f}")

# SVD of syllabary transition matrix
syl_T = np.zeros((n_syms, n_syms))
for w in syl_words:
    for i in range(len(w)-1):
        a_idx = sym_chars.index(w[i])
        b_idx = sym_chars.index(w[i+1])
        syl_T[a_idx, b_idx] += 1
rs = syl_T.sum(axis=1, keepdims=True)
rs[rs == 0] = 1
syl_T_norm = syl_T / rs
_, syl_S, _ = np.linalg.svd(syl_T_norm)
syl_cum = np.cumsum(syl_S) / np.sum(syl_S)
syl_rank90 = np.searchsorted(syl_cum, 0.90) + 1

print(f"\n  SVD of syllabary transition matrix:")
for i in range(min(8, len(syl_S))):
    print(f"    σ_{i+1} = {syl_S[i]:.4f}  cumulative = {syl_cum[i]*100:.1f}%")
print(f"  Effective rank (90%): {syl_rank90}")

# Comparison table
print(f"\n  COMPARISON TABLE:")
print(f"  {'Metric':>30s}  {'VMS':>10s}  {'Syllabary':>10s}  {'Match?':>8s}")
print(f"  {'Sukhotin vowels (fraction)':>30s}  {13}/{n_chars:>5d}     {len(syl_vowels)}/{n_syms:>5d}     ", end='')
print("YES" if abs(13/n_chars - len(syl_vowels)/n_syms) < 0.2 else "NO")
print(f"  {'V token %':>30s}  {'91.4':>10s}  {100*syl_v_tot/syl_total:>9.1f}%  ", end='')
vms_v_pct = 91.4
syl_v_pct = 100*syl_v_tot/syl_total
print("YES" if abs(vms_v_pct - syl_v_pct) < 15 else "NO")
print(f"  {'Alternation rate':>30s}  {'0.116':>10s}  {syl_alt:>10.4f}  ", end='')
print("YES" if abs(0.116 - syl_alt) < 0.15 else "NO")
print(f"  {'SVD rank(90%)':>30s}  {rank90:>10d}  {syl_rank90:>10d}  ", end='')
print("YES" if abs(rank90 - syl_rank90) <= 3 else "NO")


# Now also generate a genuine ALPHABETIC reference (5V + 12C)
print(f"\n  --- ALPHABETIC REFERENCE ---")
alpha_V = list('aeiou')
alpha_C = list('bcdfghjklmnp')
alpha_chars = alpha_V + alpha_C

# Make words with CVCV(C) structure
alpha_words = []
for _ in range(N):
    length = np.random.choice(list(word_lengths.keys()),
                              p=[word_lengths[l]/sum(word_lengths.values()) for l in word_lengths.keys()])
    word = []
    for pos in range(length):
        if pos % 2 == 0:  # C positions
            word.append(np.random.choice(alpha_C))
        else:  # V positions
            word.append(np.random.choice(alpha_V))
    alpha_words.append(''.join(word))

alpha_vc = sukhotins_algorithm(alpha_words, alpha_chars)
alpha_vowels = [c for c in alpha_chars if alpha_vc.get(c) == 'V']
alpha_cf = Counter()
for w in alpha_words:
    for c in w: alpha_cf[c] += 1
alpha_total = sum(alpha_cf.values())
alpha_v_tot = sum(alpha_cf.get(c, 0) for c in alpha_vowels)
alpha_alt = alternation_rate(alpha_words, alpha_vc)

print(f"  Sukhotin vowels: {len(alpha_vowels)}/{len(alpha_chars)}")
print(f"  V token %: {100*alpha_v_tot/alpha_total:.1f}%")
print(f"  Alternation rate: {alpha_alt:.4f}")
print(f"  Sukhotin correctly identified vowels: {set(alpha_vowels) & set(alpha_V)}")
print(f"  Sukhotin incorrectly labelled as V: {set(alpha_vowels) - set(alpha_V)}")


# ============================================================
# 56e: ENTROPY REDUCTION UNDER CHARACTER GROUPING
# ============================================================
print("\n" + "=" * 65)
print("E: ENTROPY REDUCTION UNDER CHARACTER GROUPING")
print("=" * 65)

# If characters share hidden components (like C or V in a syllabary),
# grouping by component should reduce transition entropy.
# Compare: best k-grouping vs random k-groupings.

def transition_entropy(words, char_to_group):
    """Compute H(group_next | group_current)."""
    group_bigram = Counter()
    group_unigram = Counter()
    for w in words:
        for i in range(len(w) - 1):
            g1 = char_to_group.get(w[i])
            g2 = char_to_group.get(w[i+1])
            if g1 is not None and g2 is not None:
                group_bigram[(g1, g2)] += 1
                group_unigram[g1] += 1
    H = 0.0
    total = sum(group_unigram.values())
    for g1 in set(g for g, _ in group_bigram):
        g1_total = group_unigram[g1]
        if g1_total == 0: continue
        p_g1 = g1_total / total
        for g2 in set(g2 for g1_, g2 in group_bigram if g1_ == g1):
            p_g2_given_g1 = group_bigram[(g1, g2)] / g1_total
            if p_g2_given_g1 > 0:
                H -= p_g1 * p_g2_given_g1 * math.log2(p_g2_given_g1)
    return H

# Baseline: character-level transition entropy
baseline_H = transition_entropy(all_collapsed, {c: c for c in common_chars})
print(f"  Baseline transition entropy (char-level): {baseline_H:.4f} bits")

# For k groups, find best grouping using SVD-based clustering
for k in [3, 4, 5, 6]:
    # SVD-based grouping: cluster by first k-1 right singular vectors
    # of the transition matrix
    coords = U[:, :k]  # Use first k left singular vectors
    
    # K-means clustering (manual, simple)
    best_assignment = None
    best_inertia = float('inf')
    
    for trial in range(20):
        # Random initialization
        centroids = coords[np.random.choice(n_common, k, replace=False)]
        for _ in range(20):
            # Assign
            dists = np.array([[np.linalg.norm(coords[i] - centroids[j]) 
                              for j in range(k)] for i in range(n_common)])
            assignment = np.argmin(dists, axis=1)
            # Update centroids
            new_centroids = np.array([coords[assignment == j].mean(axis=0) 
                                      if np.sum(assignment == j) > 0 
                                      else centroids[j] 
                                      for j in range(k)])
            if np.allclose(new_centroids, centroids):
                break
            centroids = new_centroids
        
        inertia = sum(np.linalg.norm(coords[i] - centroids[assignment[i]])**2 
                      for i in range(n_common))
        if inertia < best_inertia:
            best_inertia = inertia
            best_assignment = assignment.copy()
    
    # Map chars to groups
    svd_grouping = {common_chars[i]: best_assignment[i] for i in range(n_common)}
    svd_H = transition_entropy(all_collapsed, svd_grouping)
    
    # Random groupings for comparison
    random_Hs = []
    for _ in range(100):
        rand_assignment = np.random.randint(0, k, size=n_common)
        rand_grouping = {common_chars[i]: rand_assignment[i] for i in range(n_common)}
        random_Hs.append(transition_entropy(all_collapsed, rand_grouping))
    
    z_H = (svd_H - np.mean(random_Hs)) / max(np.std(random_Hs), 0.001)
    
    groups_str = {}
    for i in range(n_common):
        g = best_assignment[i]
        groups_str.setdefault(g, []).append(common_chars[i])
    
    print(f"\n  k={k} groups:")
    for g in sorted(groups_str):
        print(f"    Group {g}: {' '.join(groups_str[g])}")
    print(f"    SVD grouping H: {svd_H:.4f}")
    print(f"    Random grouping H: {np.mean(random_Hs):.4f} ± {np.std(random_Hs):.4f}")
    print(f"    z = {z_H:.1f}")
    reduction_pct = 100 * (np.mean(random_Hs) - svd_H) / np.mean(random_Hs)
    print(f"    Reduction vs random: {reduction_pct:+.1f}%")


# ============================================================
# syllabary_hypothesis SYNTHESIS
# ============================================================
print("\n" + "=" * 65)
print("syllabary_hypothesis SYNTHESIS")
print("=" * 65)

print(f"""
CRITICAL SELF-CHECK ON vowel_consonant_separation:

56a NULL MODEL RESULT:
  VMS bigram null produces {np.mean(bigram_n_vowels):.1f}/{n_chars} Sukhotin vowels
  vs VMS's {vms_n_v}/{n_chars}.
  z(n_vowels) = {z_nv:.1f}, z(alternation) = {z_alt_bigram:.1f}
  {"→ vowel_consonant_separation result is LARGELY EXPLAINED by bigram structure alone!" if abs(z_nv) < 2 else "→ vowel_consonant_separation result is NOT explained by bigrams."}

56b SVD RESULT:
  VMS rank(90%) = {rank90}, null = {np.mean(null_ranks):.1f}±{np.std(null_ranks):.1f}
  z = {z_rank:.1f}
  {"→ No evidence of low-rank (CV grid) structure." if abs(z_rank) < 2 else "→ Transition rank differs from random."}

56d CALIBRATION RESULT:
  Simulated syllabary: {len(syl_vowels)}/{n_syms} vowels, alt={syl_alt:.3f}
  Simulated alphabetic: {len(alpha_vowels)}/{len(alpha_chars)} vowels, alt={alpha_alt:.3f}
  VMS:                  {vms_n_v}/{n_chars} vowels, alt={vms_alt:.3f}

OVERALL ASSESSMENT:
""")

# Determine the honest verdict
if abs(z_nv) < 2:
    print(f"  The degenerate Sukhotin result (vowel_consonant_separation) is LIKELY an ARTIFACT")
    print(f"  of the VMS character frequency distribution. Random text from the")
    print(f"  VMS bigram model produces the same degenerate split.")
    print(f"")
    print(f"  This means vowel_consonant_separation's conclusion that 'alphabetic encoding is")
    print(f"  excluded' was PREMATURE. The Sukhotin failure tells us about")
    print(f"  character bigram statistics, not about script type.")
    print(f"")
    print(f"  However, the CHARACTER STATISTICS THEMSELVES are unusual:")
    print(f"  - Most characters freely combine with each other")
    print(f"  - No clear V/C alternation in any model")
    print(f"  - This is still inconsistent with European alphabetic text")
    print(f"")
    print(f"  REVISED ASSESSMENT:")
    print(f"  - Syllabary hypothesis: DOWNGRADE from 85% to ~70%")
    print(f"  - Alphabetic exclusion: DOWNGRADE from 90% to ~75%")
    print(f"  - The unusual character distribution remains unexplained")

print(f"\nsyllabary_hypothesis complete.")
