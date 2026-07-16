#!/usr/bin/env python3
"""
WORD TRANSITION NETWORK
===================================

mutual_information_anatomy showed MI is distributed across 3,896+ pair types (genuine
grammar, not fixed phrases), strictly local (gap 1 only), and mostly
word-specific (class model adds ~0%). This test maps the word-level
syntax.

Sub-analyses:
  A) SUCCESSOR ENTROPY — Which words have the most/least constrained
       successors? Find the grammatical "bottleneck" words.

  B) SUFFIX→WORD TRANSITIONS — Does knowing the previous suffix help
       predict the specific next word (not just next class)?

  C) COLLOCATION CLUSTERS — Build PMI network of high-affinity word
       pairs. What clusters emerge?

  D) SECTION VOCABULARY MI — How much word-level MI is from section-
       specific vocabulary vs genuine within-section syntax?

  E) WORD TRANSITION ASYMMETRY — Compare P(w2|w1) vs P(w1|w2). Is
       the head-initial structure visible at word level?
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_H, get_collapsed, get_gram_prefix, get_suffix, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(47)
np.random.seed(47)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']



def get_class(sfx):
    if sfx in ('dy', 'y'): return 'A'
    if sfx in ('X', 'ar', 'in'): return 'M'
    return 'B'  # aiin, ain, iin, al, ol, or

GRAM_PREFIXES = ['qo','so','do','q','o','d','y']


FOLIO_DIR = Path("folios")


print("Loading lines...")
lines = load_lines()

# Build collapsed sequences with sections
line_collapsed = []
line_sections = []
all_collapsed = []
for line in lines:
    coll = [get_collapsed(w) for w in line['words']]
    line_collapsed.append(coll)
    line_sections.append(line['section'])
    all_collapsed.extend(coll)

word_counts = Counter(all_collapsed)
N = len(all_collapsed)
vocab_size = len(word_counts)
print(f"  {len(lines)} lines, {N} tokens, {vocab_size} types")

# Build bigrams
all_bigrams = Counter()
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        all_bigrams[(seq[i], seq[i+1])] += 1
total_bigrams = sum(all_bigrams.values())



# ══════════════════════════════════════════════════════════════════
# 47a: SUCCESSOR ENTROPY PER WORD
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("A: SUCCESSOR ENTROPY PER WORD")
print("    Which words have most/least constrained successors?")
print("=" * 70)

# For each word, compute H(next_word | this_word)
successor_counts = defaultdict(Counter)  # word -> next_word -> count
predecessor_counts = defaultdict(Counter)  # word -> prev_word -> count
word_as_w1 = Counter()  # how often word appears as w1 in bigram
word_as_w2 = Counter()

for (w1, w2), c in all_bigrams.items():
    successor_counts[w1][w2] += c
    predecessor_counts[w2][w1] += c
    word_as_w1[w1] += c
    word_as_w2[w2] += c

# Compute H(successor) for common words (min 20 bigram occurrences as w1)
min_count = 20
word_H_succ = {}
word_H_pred = {}

for w in word_counts:
    if word_as_w1[w] >= min_count:
        word_H_succ[w] = compute_H(successor_counts[w], word_as_w1[w])
    if word_as_w2[w] >= min_count:
        word_H_pred[w] = compute_H(predecessor_counts[w], word_as_w2[w])

# Overall H(word) for comparison
H_uni = compute_H(word_counts, N)

# Sort by successor entropy
sorted_succ = sorted(word_H_succ.items(), key=lambda x: x[1])

print(f"\n  Words with min {min_count} successors: {len(word_H_succ)}")
print(f"  Overall H(word) = {H_uni:.3f} bits")

# Most constrained successors (lowest H)
print(f"\n  MOST CONSTRAINED successors (lowest H):")
print(f"  {'Word':>15} {'H(succ)':>8} {'N(w1)':>8} {'Types':>8} {'Top successor':>20} {'%':>6}")
for w, h in sorted_succ[:20]:
    n = word_as_w1[w]
    types = len(successor_counts[w])
    top_succ = successor_counts[w].most_common(1)[0]
    print(f"  {w:>15} {h:>8.3f} {n:>8} {types:>8} {top_succ[0]:>20} {top_succ[1]/n*100:>5.1f}%")

# Least constrained (highest H)
print(f"\n  LEAST CONSTRAINED successors (highest H):")
sorted_desc = sorted(word_H_succ.items(), key=lambda x: x[1], reverse=True)
print(f"  {'Word':>15} {'H(succ)':>8} {'N(w1)':>8} {'Types':>8} {'Top successor':>20} {'%':>6}")
for w, h in sorted_desc[:20]:
    n = word_as_w1[w]
    types = len(successor_counts[w])
    top_succ = successor_counts[w].most_common(1)[0]
    print(f"  {w:>15} {h:>8.3f} {n:>8} {types:>8} {top_succ[0]:>20} {top_succ[1]/n*100:>5.1f}%")

# Distribution of H(succ)
h_vals = np.array(list(word_H_succ.values()))
print(f"\n  H(successor) distribution:")
print(f"  mean={np.mean(h_vals):.3f}, median={np.median(h_vals):.3f}, std={np.std(h_vals):.3f}")
print(f"  min={np.min(h_vals):.3f}, max={np.max(h_vals):.3f}")

# Correlation between word frequency and H(succ)
freqs = np.array([word_counts[w] for w in word_H_succ])
h_vals_aligned = np.array([word_H_succ[w] for w in word_H_succ])
corr = np.corrcoef(np.log(freqs), h_vals_aligned)[0, 1]
print(f"  Corr(log(freq), H(succ)) = {corr:.3f}")


# ══════════════════════════════════════════════════════════════════
# 47b: SUFFIX→WORD TRANSITIONS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("B: SUFFIX→WORD TRANSITIONS")
print("    Does previous suffix help predict specific next word?")
print("=" * 70)

# For each suffix of w1, compute H(w2 | sfx(w1))
sfx_to_next_word = defaultdict(Counter)
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        sfx = get_suffix(seq[i])
        sfx_to_next_word[sfx][seq[i+1]] += 1

# H(w2 | sfx(w1))
total_bg2 = sum(sum(c.values()) for c in sfx_to_next_word.values())
H_w2_given_sfx = 0.0
for sfx, next_counts in sfx_to_next_word.items():
    sfx_total = sum(next_counts.values())
    p_sfx = sfx_total / total_bg2
    H_w2_in_sfx = compute_H(next_counts, sfx_total)
    H_w2_given_sfx += p_sfx * H_w2_in_sfx

# Also compute H(w2 | class(w1))
cls_to_next_word = defaultdict(Counter)
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        cls = get_class(get_suffix(seq[i]))
        cls_to_next_word[cls][seq[i+1]] += 1

H_w2_given_cls = 0.0
for cls, next_counts in cls_to_next_word.items():
    cls_total = sum(next_counts.values())
    p_cls = cls_total / total_bg2
    H_w2_in_cls = compute_H(next_counts, cls_total)
    H_w2_given_cls += p_cls * H_w2_in_cls

# Also: H(w2 | gpfx(w1))
gpfx_to_next_word = defaultdict(Counter)
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        gpfx = get_gram_prefix(seq[i])
        gpfx_to_next_word[gpfx][seq[i+1]] += 1

H_w2_given_gpfx = 0.0
for gpfx, next_counts in gpfx_to_next_word.items():
    gpfx_total = sum(next_counts.values())
    p_gpfx = gpfx_total / total_bg2
    H_w2_in_gpfx = compute_H(next_counts, gpfx_total)
    H_w2_given_gpfx += p_gpfx * H_w2_in_gpfx

# H(w2) unconditional (from bigram context)
w2_counts = Counter()
for (w1, w2), c in all_bigrams.items():
    w2_counts[w2] += c
H_w2_uncond = compute_H(w2_counts, total_bigrams)

# H(w2 | w1) from full word bigram
# This is already H_cond from before
from collections import OrderedDict
H_joint = 0.0
for c in all_bigrams.values():
    if c > 0:
        p = c / total_bigrams
        H_joint -= p * math.log2(p)
w1_marginal = Counter()
for (w1, w2), c in all_bigrams.items():
    w1_marginal[w1] += c
H_w1 = compute_H(w1_marginal, total_bigrams)
H_w2_given_w1 = H_joint - H_w1

print(f"\n  How much do different features of w1 tell us about w2?")
print(f"  H(w2) unconditional:       {H_w2_uncond:.3f} bits")
print(f"  H(w2 | class(w1)):         {H_w2_given_cls:.3f} bits  (class saves {H_w2_uncond - H_w2_given_cls:.3f})")
print(f"  H(w2 | gpfx(w1)):          {H_w2_given_gpfx:.3f} bits  (gpfx saves {H_w2_uncond - H_w2_given_gpfx:.3f})")
print(f"  H(w2 | sfx(w1)):           {H_w2_given_sfx:.3f} bits  (sfx saves {H_w2_uncond - H_w2_given_sfx:.3f})")
print(f"  H(w2 | w1):                {H_w2_given_w1:.3f} bits  (word saves {H_w2_uncond - H_w2_given_w1:.3f})")

# What fraction of the word-level information is captured by suffix?
word_info = H_w2_uncond - H_w2_given_w1
sfx_info = H_w2_uncond - H_w2_given_sfx
cls_info = H_w2_uncond - H_w2_given_cls
gpfx_info = H_w2_uncond - H_w2_given_gpfx

print(f"\n  Information hierarchy:")
print(f"  Class captures:  {cls_info:.4f} / {word_info:.4f} = {cls_info/word_info*100:.1f}% of word-level info")
print(f"  Gpfx captures:   {gpfx_info:.4f} / {word_info:.4f} = {gpfx_info/word_info*100:.1f}% of word-level info")
print(f"  Suffix captures: {sfx_info:.4f} / {word_info:.4f} = {sfx_info/word_info*100:.1f}% of word-level info")

# Suffix-specific: which suffix most constrains next word?
print(f"\n  Suffix-specific H(w2|sfx(w1)):")
for sfx in ['X'] + SUFFIXES:
    if sfx in sfx_to_next_word:
        n = sum(sfx_to_next_word[sfx].values())
        h = compute_H(sfx_to_next_word[sfx], n)
        types = len(sfx_to_next_word[sfx])
        top = sfx_to_next_word[sfx].most_common(3)
        top_str = ", ".join(f"{w}({c})" for w, c in top)
        print(f"  {sfx:>6}: H={h:.3f}, N={n}, types={types}, top: {top_str}")


# ══════════════════════════════════════════════════════════════════
# 47c: COLLOCATION CLUSTERS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("C: COLLOCATION CLUSTERS")
print("    PMI network of high-affinity word pairs")
print("=" * 70)

# Compute PMI for all pairs with count >= 5
pmi_pairs = []
for (w1, w2), count in all_bigrams.items():
    if count < 5:
        continue
    p_joint = count / total_bigrams
    p_w1 = word_counts[w1] / N
    p_w2 = word_counts[w2] / N
    if p_w1 > 0 and p_w2 > 0:
        pmi = math.log2(p_joint / (p_w1 * p_w2))
        pmi_pairs.append((w1, w2, count, pmi))

pmi_pairs.sort(key=lambda x: x[3], reverse=True)

print(f"\n  Pairs with count >= 5: {len(pmi_pairs)}")
print(f"\n  Top 30 by PMI (min count 5):")
print(f"  {'Word1':>15} {'Word2':>15} {'Count':>6} {'PMI':>7} {'Sfx1':>6} {'Sfx2':>6}")
for w1, w2, count, pmi in pmi_pairs[:30]:
    s1 = get_suffix(w1)
    s2 = get_suffix(w2)
    print(f"  {w1:>15} {w2:>15} {count:>6} {pmi:>7.2f} {s1:>6} {s2:>6}")

# Build adjacency for network analysis
# Use PMI > 1 and count >= 5 as threshold
high_pmi_pairs = [(w1, w2, count, pmi) for w1, w2, count, pmi in pmi_pairs
                  if pmi > 1.0]
print(f"\n  Pairs with PMI > 1 and count >= 5: {len(high_pmi_pairs)}")

# Find connected components using simple BFS
adjacency = defaultdict(set)
for w1, w2, count, pmi in high_pmi_pairs:
    adjacency[w1].add(w2)
    adjacency[w2].add(w1)

visited = set()
components = []
for node in adjacency:
    if node in visited:
        continue
    # BFS
    queue = [node]
    component = set()
    while queue:
        n = queue.pop(0)
        if n in visited:
            continue
        visited.add(n)
        component.add(n)
        for neighbor in adjacency[n]:
            if neighbor not in visited:
                queue.append(neighbor)
    components.append(component)

components.sort(key=len, reverse=True)
print(f"\n  Connected components: {len(components)}")
for i, comp in enumerate(components[:5]):
    words_sorted = sorted(comp, key=lambda w: word_counts[w], reverse=True)
    suffixes = Counter(get_suffix(w) for w in comp)
    sfx_str = ", ".join(f"{s}:{c}" for s, c in suffixes.most_common(5))
    print(f"\n  Component {i+1} ({len(comp)} words): {sfx_str}")
    # Show top 10 words
    for w in words_sorted[:10]:
        # Show edges
        edges_out = [(w2, all_bigrams.get((w, w2), 0)) for w2 in adjacency.get(w, set()) if w2 in comp]
        edges_out.sort(key=lambda x: x[1], reverse=True)
        edge_str = ", ".join(f"→{w2}({c})" for w2, c in edges_out[:3])
        print(f"    {w} (freq={word_counts[w]}, sfx={get_suffix(w)}): {edge_str}")


# ══════════════════════════════════════════════════════════════════
# 47d: SECTION VOCABULARY MI
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("D: SECTION VOCABULARY MI")
print("    How much word MI is from section-specific vocabulary?")
print("=" * 70)

# Compute MI within each section separately
section_results = {}
for sec in sorted(set(line_sections)):
    sec_lines = [line_collapsed[i] for i in range(len(lines)) if line_sections[i] == sec]
    if len(sec_lines) < 20:
        continue
    
    sec_words = []
    for seq in sec_lines:
        sec_words.extend(seq)
    sec_N = len(sec_words)
    sec_wc = Counter(sec_words)
    sec_V = len(sec_wc)
    
    sec_bigrams = Counter()
    for seq in sec_lines:
        for i in range(len(seq) - 1):
            sec_bigrams[(seq[i], seq[i+1])] += 1
    sec_total_bg = sum(sec_bigrams.values())
    
    if sec_total_bg < 10:
        continue
    
    sec_H = compute_H(sec_wc, sec_N)
    # H(w2|w1) within section
    sec_H_joint = 0.0
    for c in sec_bigrams.values():
        if c > 0:
            p = c / sec_total_bg
            sec_H_joint -= p * math.log2(p)
    sec_w1_counts = Counter()
    for (w1, w2), c in sec_bigrams.items():
        sec_w1_counts[w1] += c
    sec_H_w1 = compute_H(sec_w1_counts, sec_total_bg)
    sec_H_cond = sec_H_joint - sec_H_w1
    sec_MI = sec_H - sec_H_cond
    sec_MI_H = sec_MI / sec_H if sec_H > 0 else 0
    
    section_results[sec] = (sec_N, sec_V, sec_H, sec_H_cond, sec_MI, sec_MI_H, len(sec_lines))

print(f"\n  {'Section':>12} {'Lines':>6} {'Tokens':>7} {'Types':>6} {'H(W)':>7} {'H(W|prev)':>10} {'MI':>7} {'MI/H':>7}")
for sec in sorted(section_results):
    sec_N, sec_V, sec_H, sec_H_cond, sec_MI, sec_MI_H, n_lines = section_results[sec]
    print(f"  {sec:>12} {n_lines:>6} {sec_N:>7} {sec_V:>6} {sec_H:>7.3f} {sec_H_cond:>10.3f} {sec_MI:>7.3f} {sec_MI_H:>7.3f}")

# Also compute: if we shuffle words BETWEEN sections but keep within-section
# order, how much MI remains?
print(f"\n  Section-mixing test:")
print(f"  (Shuffle section labels on lines, recompute MI)")
n_shuf = 50
shuf_mi = []
for trial in range(n_shuf):
    # Shuffle section labels
    shuf_indices = list(range(len(line_collapsed)))
    random.shuffle(shuf_indices)
    # Rebuild global bigrams from shuffled line order
    shuf_bg = Counter()
    for idx in shuf_indices:
        seq = line_collapsed[idx]
        for i in range(len(seq) - 1):
            shuf_bg[(seq[i], seq[i+1])] += 1
    shuf_total = sum(shuf_bg.values())
    shuf_H_joint = 0.0
    for c in shuf_bg.values():
        if c > 0:
            p = c / shuf_total
            shuf_H_joint -= p * math.log2(p)
    shuf_w1 = Counter()
    for (w1, w2), c in shuf_bg.items():
        shuf_w1[w1] += c
    shuf_H_w1 = compute_H(shuf_w1, shuf_total)
    shuf_H_cond = shuf_H_joint - shuf_H_w1
    shuf_mi.append(H_uni - shuf_H_cond)

# Note: shuffling line ORDER shouldn't change within-line bigrams
# The MI should be the same since within-line bigrams are identical
print(f"  (Line-order shuffle preserves within-line bigrams)")
print(f"  Shuffled MI: {np.mean(shuf_mi):.4f} ± {np.std(shuf_mi):.4f}")
print(f"  Actual MI:   {H_uni - H_w2_given_w1:.4f}")

# Better test: Within section, shuffle words. Between sections, keep structure.
print(f"\n  Within-section shuffle test:")
print(f"  (Shuffle word order within each line, separately per section)")
ws_mi = []
for trial in range(50):
    ws_bg = Counter()
    for seq in line_collapsed:
        shuf = list(seq)
        random.shuffle(shuf)
        for i in range(len(shuf) - 1):
            ws_bg[(shuf[i], shuf[i+1])] += 1
    ws_total = sum(ws_bg.values())
    ws_H_joint = 0.0
    for c in ws_bg.values():
        if c > 0:
            p = c / ws_total
            ws_H_joint -= p * math.log2(p)
    ws_w1 = Counter()
    for (w1, w2), c in ws_bg.items():
        ws_w1[w1] += c
    ws_H_w1 = compute_H(ws_w1, ws_total)
    ws_H_cond = ws_H_joint - ws_H_w1
    ws_mi.append(H_uni - ws_H_cond)

actual_mi = H_uni - H_w2_given_w1
ws_mean = np.mean(ws_mi)
ws_std = np.std(ws_mi)
print(f"  Within-line shuffled MI: {ws_mean:.4f} ± {ws_std:.4f}")
print(f"  Actual MI:               {actual_mi:.4f}")
print(f"  Excess (word order):     {actual_mi - ws_mean:.4f}")
print(f"  z-score:                 {(actual_mi - ws_mean) / ws_std:.1f}")

# What fraction of shuffled MI is from section vocabulary structure?
# Compare within-line shuffle to global shuffle (cross-section)
gs_mi = []
for trial in range(50):
    all_shuf = list(all_collapsed)
    random.shuffle(all_shuf)
    gs_bg = Counter()
    idx = 0
    for seq in line_collapsed:
        n_w = len(seq)
        seg = all_shuf[idx:idx+n_w]
        idx += n_w
        for i in range(len(seg) - 1):
            gs_bg[(seg[i], seg[i+1])] += 1
    gs_total = sum(gs_bg.values())
    gs_H_joint = 0.0
    for c in gs_bg.values():
        if c > 0:
            p = c / gs_total
            gs_H_joint -= p * math.log2(p)
    gs_w1 = Counter()
    for (w1, w2), c in gs_bg.items():
        gs_w1[w1] += c
    gs_H_w1 = compute_H(gs_w1, gs_total)
    gs_H_cond = gs_H_joint - gs_H_w1
    gs_mi.append(H_uni - gs_H_cond)

gs_mean = np.mean(gs_mi)
print(f"\n  Decomposition:")
print(f"  Global shuffle MI (baseline):         {gs_mean:.4f}")
print(f"  Within-line shuffle MI:               {ws_mean:.4f}")
print(f"  Section/line structure contributes:    {ws_mean - gs_mean:.4f} ({(ws_mean - gs_mean)/(actual_mi - gs_mean)*100:.1f}% of excess)")
print(f"  Word ORDER contributes:               {actual_mi - ws_mean:.4f} ({(actual_mi - ws_mean)/(actual_mi - gs_mean)*100:.1f}% of excess)")
print(f"  Total excess over global:             {actual_mi - gs_mean:.4f}")


# ══════════════════════════════════════════════════════════════════
# 47e: WORD TRANSITION ASYMMETRY
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("E: WORD TRANSITION ASYMMETRY")
print("    Compare P(w2|w1) vs P(w1|w2) — head-initial at word level?")
print("=" * 70)

# For common word pairs, compare forward vs backward transition probabilities
# Forward: P(w2|w1)
# Backward: P(w1|w2)
# Asymmetry: log(P(w2|w1) / P(w1|w2))

# Build reverse bigrams
reverse_bigrams = Counter()
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        reverse_bigrams[(seq[i+1], seq[i])] += 1

# For high-frequency pairs
asym_data = []
for (w1, w2), count in all_bigrams.items():
    if count < 5:
        continue
    p_fwd = count / word_as_w1[w1]
    p_bwd = count / word_as_w2[w2]
    if p_fwd > 0 and p_bwd > 0:
        asym = math.log2(p_fwd / p_bwd)
        asym_data.append((w1, w2, count, p_fwd, p_bwd, asym))

# Forward H(w2|w1) vs backward H(w1|w2)
# Already have H_w2_given_w1
# Compute H(w1|w2) = H(w2,w1) - H(w2) [same joint, different marginal]
H_w2_marginal = compute_H(word_as_w2, total_bigrams)
H_w1_given_w2 = H_joint - H_w2_marginal

print(f"\n  Forward:  H(w2|w1) = {H_w2_given_w1:.4f}")
print(f"  Backward: H(w1|w2) = {H_w1_given_w2:.4f}")
print(f"  Difference: {H_w2_given_w1 - H_w1_given_w2:.4f} (negative = forward more predictable)")

# Asymmetry distribution
asym_vals = np.array([a[5] for a in asym_data])
print(f"\n  Asymmetry log2(P(w2|w1)/P(w1|w2)) distribution:")
print(f"  N pairs = {len(asym_vals)}")
print(f"  mean = {np.mean(asym_vals):.4f}")
print(f"  median = {np.median(asym_vals):.4f}")
print(f"  std = {np.std(asym_vals):.4f}")

# How many are forward-dominant vs backward-dominant?
fwd_dominant = sum(1 for a in asym_vals if a > 0)
bwd_dominant = sum(1 for a in asym_vals if a < 0)
print(f"  Forward-dominant (P(w2|w1) > P(w1|w2)): {fwd_dominant} ({fwd_dominant/len(asym_vals)*100:.1f}%)")
print(f"  Backward-dominant:                       {bwd_dominant} ({bwd_dominant/len(asym_vals)*100:.1f}%)")

# Weighted by count
fwd_weighted = sum(a[2] for a in asym_data if a[5] > 0)
bwd_weighted = sum(a[2] for a in asym_data if a[5] < 0)
total_weighted = fwd_weighted + bwd_weighted
print(f"  Forward-weighted (by count): {fwd_weighted/total_weighted*100:.1f}%")
print(f"  Backward-weighted:           {bwd_weighted/total_weighted*100:.1f}%")

# Most extreme asymmetries
print(f"\n  Most forward-dominant pairs (w1 strongly predicts w2):")
asym_data.sort(key=lambda x: x[5], reverse=True)
print(f"  {'W1':>15} {'W2':>15} {'Count':>6} {'P(w2|w1)':>9} {'P(w1|w2)':>9} {'Asym':>7}")
for w1, w2, count, p_fwd, p_bwd, asym in asym_data[:10]:
    print(f"  {w1:>15} {w2:>15} {count:>6} {p_fwd:>9.3f} {p_bwd:>9.3f} {asym:>7.2f}")

print(f"\n  Most backward-dominant pairs (w2 strongly predicts w1):")
asym_data.sort(key=lambda x: x[5])
print(f"  {'W1':>15} {'W2':>15} {'Count':>6} {'P(w2|w1)':>9} {'P(w1|w2)':>9} {'Asym':>7}")
for w1, w2, count, p_fwd, p_bwd, asym in asym_data[:10]:
    print(f"  {w1:>15} {w2:>15} {count:>6} {p_fwd:>9.3f} {p_bwd:>9.3f} {asym:>7.2f}")

# Permutation test: is the mean asymmetry significantly different from zero?
n_perm = 500
perm_means = []
for trial in range(n_perm):
    # Randomly flip signs
    flipped = asym_vals * np.random.choice([-1, 1], size=len(asym_vals))
    perm_means.append(np.mean(flipped))
z_asym = (np.mean(asym_vals) - np.mean(perm_means)) / np.std(perm_means)
print(f"\n  Mean asymmetry z-score (vs sign-flip null): {z_asym:.1f}")

print("\n" + "=" * 70)
print("word_transition_network COMPLETE")
print("=" * 70)
