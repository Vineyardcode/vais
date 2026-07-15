#!/usr/bin/env python3
"""
Phase 44 — PARSER-FREE WORD CLASSES AND LINE GRAMMAR
=====================================================

Phase 43 confirmed:
  - Three-class suffix system (A/M/B) captures 80.7% of sfx→pfx MI
  - Grammar is universal across sections (not section-specific)
  - Head-initial structure (L→R prediction z=21.3)
  - Synergy in class bigrams (bootstrap-confirmed)

Key vulnerability: the "class system" comes entirely from our parser.
If the parser assigns suffixes wrong, the classes are wrong.

Phase 44 attacks from a new angle: do WORDS (not parsed features)
naturally cluster into groups that match the class system?

Sub-analyses:
  44a) DISTRIBUTIONAL WORD CLUSTERING — For frequent words, compute
       context vectors (what words appear before and after). SVD + k-means.
       Do natural clusters emerge? How many?

  44b) CLUSTER vs MORPHOLOGICAL CLASS — Do distributional clusters
       match the parsed suffix classes (A/M/B)? If yes → classes are
       real word-level properties. If no → classes are parser artifacts.

  44c) LINE CLASS SEQUENCE — What are the most common class sequences
       within lines? Is there a dominant pattern (e.g., B-A-B-A or
       A-B-A)? How much of within-line structure is explained by class?

  44d) CLASS BIGRAM PERPLEXITY — Build bigram language models at
       different granularities (unigram, 3-class, 11-suffix, word).
       How much does each reduce uncertainty?

  44e) LINE POSITION × CLASS — Which classes appear where in the line?
       Is Class A (dy/y) concentrated in certain positions? Is Class M
       (X/ar/in) line-final?
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, get_collapsed, get_prefix, get_suffix, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(44)
np.random.seed(44)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']




# Three-class system from Phase 43c clustering
def get_sfx_class(sfx):
    if sfx in ('dy', 'y'): return 'A'
    if sfx in ('X', 'ar', 'in'): return 'M'
    return 'B'  # aiin, ain, iin, al, ol, or

FOLIO_DIR = Path("folios")



def annotate_lines(lines):
    for line in lines:
        line['collapsed'] = [get_collapsed(w) for w in line['words']]
        line['pfx'] = [get_prefix(c) for c in line['collapsed']]
        line['sfx'] = [get_suffix(c) for c in line['collapsed']]
        line['cls'] = [get_sfx_class(s) for s in line['sfx']]
    return lines


print("Loading lines...")
lines = load_lines()
lines = annotate_lines(lines)
total_words = sum(len(l['words']) for l in lines)
print(f"  {len(lines)} lines, {total_words} word tokens")

# Build vocabulary
word_counts = Counter()
for line in lines:
    for w in line['collapsed']:
        word_counts[w] += 1
print(f"  {len(word_counts)} word types")


# ══════════════════════════════════════════════════════════════════
# 44a: DISTRIBUTIONAL WORD CLUSTERING
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("44a: DISTRIBUTIONAL WORD CLUSTERING")
print("    Cluster words by what appears before/after them.")
print("    No parsing — purely distributional.")
print("=" * 70)

# Use only frequent words (≥10 tokens)
MIN_FREQ = 10
freq_words = sorted([w for w, c in word_counts.items() if c >= MIN_FREQ])
word_to_idx = {w: i for i, w in enumerate(freq_words)}
n_words = len(freq_words)
print(f"\n  {n_words} words with freq ≥ {MIN_FREQ}")

# Build left/right context vectors
# For each target word, count what words appear before and after it
left_ctx = np.zeros((n_words, n_words), dtype=np.float32)
right_ctx = np.zeros((n_words, n_words), dtype=np.float32)

for line in lines:
    coll = line['collapsed']
    for i in range(len(coll)):
        w = coll[i]
        if w not in word_to_idx:
            continue
        wi = word_to_idx[w]
        if i > 0 and coll[i-1] in word_to_idx:
            left_ctx[wi, word_to_idx[coll[i-1]]] += 1
        if i < len(coll) - 1 and coll[i+1] in word_to_idx:
            right_ctx[wi, word_to_idx[coll[i+1]]] += 1

# Combine left and right context
ctx_matrix = np.hstack([left_ctx, right_ctx])  # shape: (n_words, 2*n_words)

# Normalize rows (PPMI-style: log(observed/expected) clipped at 0)
row_sums = ctx_matrix.sum(axis=1, keepdims=True)
col_sums = ctx_matrix.sum(axis=0, keepdims=True)
total_sum = ctx_matrix.sum()
if total_sum > 0:
    expected = (row_sums * col_sums) / total_sum
    # PPMI
    with np.errstate(divide='ignore', invalid='ignore'):
        pmi = np.log2(np.where(ctx_matrix > 0, ctx_matrix / np.maximum(expected, 1e-10), 1e-10))
    ppmi = np.maximum(pmi, 0)
    # Replace inf/nan
    ppmi = np.nan_to_num(ppmi, nan=0.0, posinf=0.0, neginf=0.0)
else:
    ppmi = ctx_matrix

# SVD for dimensionality reduction
from numpy.linalg import svd
print("  Running SVD...")
U, S, Vt = svd(ppmi, full_matrices=False)
# Use first 20 components
n_comp = min(20, len(S))
word_vecs = U[:, :n_comp] * S[:n_comp]

# k-means clustering
def kmeans(X, k, max_iter=100):
    n = X.shape[0]
    # Random init
    idx = np.random.choice(n, k, replace=False)
    centers = X[idx].copy()
    labels = np.zeros(n, dtype=int)
    for _ in range(max_iter):
        # Assign
        dists = np.zeros((n, k))
        for j in range(k):
            dists[:, j] = np.sum((X - centers[j])**2, axis=1)
        new_labels = np.argmin(dists, axis=1)
        if np.all(new_labels == labels):
            break
        labels = new_labels
        # Update
        for j in range(k):
            mask = labels == j
            if mask.any():
                centers[j] = X[mask].mean(axis=0)
    return labels, centers

# Try k=2,3,4,5,6 and compute within-cluster variance
print("\n  Cluster quality (within-cluster variance ratio):")
total_var = np.var(word_vecs, axis=0).sum()
for k in [2, 3, 4, 5, 6, 8]:
    best_labels = None
    best_inertia = float('inf')
    for trial in range(10):
        labels, centers = kmeans(word_vecs, k)
        inertia = 0
        for j in range(k):
            mask = labels == j
            if mask.any():
                inertia += np.sum((word_vecs[mask] - centers[j])**2)
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels
    explained = 1.0 - best_inertia / (total_var * len(freq_words))
    sizes = [np.sum(best_labels == j) for j in range(k)]
    print(f"    k={k}: explained={explained:.3f}, sizes={sorted(sizes, reverse=True)}")

# Do k=3 in detail with morphological class comparison
print("\n  Detailed k=3 clustering:")
best_labels = None
best_inertia = float('inf')
for trial in range(20):
    labels, centers = kmeans(word_vecs, 3)
    inertia = sum(np.sum((word_vecs[labels == j] - centers[j])**2) for j in range(3))
    if inertia < best_inertia:
        best_inertia = inertia
        best_labels = labels

# Show cluster composition by morphological class
for cl in range(3):
    members = [freq_words[i] for i in range(n_words) if best_labels[i] == cl]
    cls_counts = Counter()
    pfx_counts = Counter()
    sfx_counts = Counter()
    for w in members:
        sfx = get_suffix(w)
        pfx = get_prefix(w)
        cls_counts[get_sfx_class(sfx)] += 1
        pfx_counts[pfx] += 1
        sfx_counts[sfx] += 1

    total_in_cl = len(members)
    print(f"\n  Cluster {cl} ({total_in_cl} words):")
    print(f"    Suffix class: A={cls_counts.get('A',0)} ({cls_counts.get('A',0)/total_in_cl*100:.0f}%), "
          f"M={cls_counts.get('M',0)} ({cls_counts.get('M',0)/total_in_cl*100:.0f}%), "
          f"B={cls_counts.get('B',0)} ({cls_counts.get('B',0)/total_in_cl*100:.0f}%)")
    print(f"    Top prefixes: {pfx_counts.most_common(5)}")
    print(f"    Top suffixes: {sfx_counts.most_common(5)}")
    # Show top 10 most frequent words
    member_freq = sorted(members, key=lambda w: word_counts[w], reverse=True)
    print(f"    Top words: {', '.join(member_freq[:15])}")


# ══════════════════════════════════════════════════════════════════
# 44b: CLUSTER vs MORPHOLOGICAL CLASS AGREEMENT
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("44b: DISTRIBUTIONAL CLUSTER vs MORPHOLOGICAL CLASS")
print("    Do distributional clusters match parsed suffix classes?")
print("=" * 70)

# Assign morphological class to each word
morph_classes = [get_sfx_class(get_suffix(w)) for w in freq_words]

# For each k, compute adjusted mutual information between clusters and morph class
def compute_mi_discrete(labels1, labels2):
    """MI between two label arrays."""
    N = len(labels1)
    joint = Counter(zip(labels1, labels2))
    c1 = Counter(labels1)
    c2 = Counter(labels2)
    mi = 0.0
    for (a, b), n in joint.items():
        p_ab = n / N
        p_a = c1[a] / N
        p_b = c2[b] / N
        if p_ab > 0 and p_a > 0 and p_b > 0:
            mi += p_ab * math.log2(p_ab / (p_a * p_b))
    return mi

def entropy_discrete(labels):
    N = len(labels)
    c = Counter(labels)
    return -sum((v/N) * math.log2(v/N) for v in c.values() if v > 0)

# Test k=3 cluster vs morph class
mi_clust_morph = compute_mi_discrete(best_labels.tolist(), morph_classes)
h_morph = entropy_discrete(morph_classes)
h_clust = entropy_discrete(best_labels.tolist())
nmi = 2 * mi_clust_morph / (h_morph + h_clust) if (h_morph + h_clust) > 0 else 0

print(f"\n  MI(cluster, morph_class) = {mi_clust_morph:.4f}")
print(f"  H(morph_class) = {h_morph:.4f}")
print(f"  H(cluster) = {h_clust:.4f}")
print(f"  Normalized MI = {nmi:.3f}")
print(f"    NMI=0 → no agreement, NMI=1 → perfect agreement")

# Cross-tabulation
print(f"\n  Cross-tabulation (cluster × morph class):")
print(f"  {'Cluster':<10} {'A':>6} {'M':>6} {'B':>6} {'Total':>8}")
for cl in range(3):
    row = [morph_classes[i] for i in range(n_words) if best_labels[i] == cl]
    mc = Counter(row)
    print(f"  {cl:<10} {mc.get('A',0):>6} {mc.get('M',0):>6} {mc.get('B',0):>6} {len(row):>8}")

# Null test: shuffle morph class assignments
null_nmis = []
for _ in range(500):
    shuf_morph = list(morph_classes)
    random.shuffle(shuf_morph)
    mi_null = compute_mi_discrete(best_labels.tolist(), shuf_morph)
    h_null = entropy_discrete(shuf_morph)
    nmi_null = 2 * mi_null / (h_null + h_clust) if (h_null + h_clust) > 0 else 0
    null_nmis.append(nmi_null)

z_nmi = (nmi - np.mean(null_nmis)) / max(np.std(null_nmis), 1e-10)
print(f"\n  Null NMI: {np.mean(null_nmis):.4f}±{np.std(null_nmis):.4f}")
print(f"  z(NMI) = {z_nmi:.1f}")


# ══════════════════════════════════════════════════════════════════
# 44c: LINE CLASS SEQUENCE PATTERNS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("44c: LINE CLASS SEQUENCE PATTERNS")
print("    What are the most common class (A/M/B) patterns within lines?")
print("=" * 70)

# Compute class sequences for lines of common lengths
seq_counts = Counter()
seq_by_len = defaultdict(Counter)
for line in lines:
    seq = ''.join(line['cls'])
    seq_counts[seq] += 1
    seq_by_len[len(line['cls'])][seq] += 1

# Show top patterns for each length
for length in sorted(seq_by_len.keys()):
    if length < 3 or length > 10:
        continue
    total_of_len = sum(seq_by_len[length].values())
    if total_of_len < 20:
        continue
    top = seq_by_len[length].most_common(5)
    print(f"\n  Length {length} ({total_of_len} lines):")
    for seq, cnt in top:
        pct = cnt / total_of_len * 100
        print(f"    {seq}  {cnt:>4} ({pct:.1f}%)")

# Summary: what fraction of class variety is there?
print(f"\n  Overall: {len(seq_counts)} unique class sequences")
top20 = seq_counts.most_common(20)
top20_total = sum(c for _, c in top20)
print(f"  Top 20 sequences cover {top20_total}/{len(lines)} = {top20_total/len(lines)*100:.1f}% of lines")
for seq, cnt in top20:
    print(f"    {seq:<15} {cnt:>4} ({cnt/len(lines)*100:.1f}%)")

# Class bigram within lines
cls_bigrams = Counter()
for line in lines:
    for i in range(len(line['cls']) - 1):
        cls_bigrams[(line['cls'][i], line['cls'][i+1])] += 1

total_bigs = sum(cls_bigrams.values())
print(f"\n  Class bigram frequencies (within lines):")
print(f"  {'Pair':<6} {'Count':>6} {'Obs%':>6} {'Exp%':>6} {'Ratio':>6}")
cls_marginal = Counter()
for line in lines:
    for c in line['cls']:
        cls_marginal[c] += 1
total_cls = sum(cls_marginal.values())

for c1 in ['A', 'M', 'B']:
    for c2 in ['A', 'M', 'B']:
        obs = cls_bigrams.get((c1, c2), 0)
        obs_pct = obs / total_bigs * 100
        exp_pct = (cls_marginal[c1] / total_cls) * (cls_marginal[c2] / total_cls) * 100
        ratio = obs_pct / exp_pct if exp_pct > 0 else 0
        print(f"  {c1}→{c2}   {obs:>6}  {obs_pct:>5.1f}  {exp_pct:>5.1f}  {ratio:>5.2f}")


# ══════════════════════════════════════════════════════════════════
# 44d: CLASS BIGRAM PERPLEXITY
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("44d: CLASS BIGRAM PERPLEXITY")
print("    How much does class/suffix/word context reduce uncertainty?")
print("=" * 70)

# Build sequential class/suffix/word arrays from lines
all_cls = []
all_sfx = []
all_words = []
for line in lines:
    all_cls.extend(line['cls'])
    all_sfx.extend(line['sfx'])
    all_words.extend(line['collapsed'])

def bigram_perplexity(seq, alpha=0.1):
    """Compute perplexity of bigram model with add-alpha smoothing."""
    vocab = set(seq)
    V = len(vocab)
    # Count bigrams and unigrams
    bigrams = Counter()
    unigrams = Counter()
    for i in range(len(seq) - 1):
        bigrams[(seq[i], seq[i+1])] += 1
        unigrams[seq[i]] += 1

    # Compute log probability
    log_prob = 0
    n = 0
    for i in range(len(seq) - 1):
        p = (bigrams[(seq[i], seq[i+1])] + alpha) / (unigrams[seq[i]] + alpha * V)
        log_prob += math.log2(p)
        n += 1

    return 2 ** (-log_prob / n) if n > 0 else 0

def unigram_perplexity(seq, alpha=0.1):
    """Compute perplexity of unigram model."""
    vocab = set(seq)
    V = len(vocab)
    counts = Counter(seq)
    N = len(seq)
    log_prob = 0
    for s in seq:
        p = (counts[s] + alpha) / (N + alpha * V)
        log_prob += math.log2(p)
    return 2 ** (-log_prob / N) if N > 0 else 0

# Compute perplexities
pp_cls_uni = unigram_perplexity(all_cls)
pp_cls_bi = bigram_perplexity(all_cls)
pp_sfx_uni = unigram_perplexity(all_sfx)
pp_sfx_bi = bigram_perplexity(all_sfx)
pp_word_uni = unigram_perplexity(all_words)
pp_word_bi = bigram_perplexity(all_words)

print(f"\n  {'Model':<25} {'Unigram PP':>12} {'Bigram PP':>12} {'Reduction':>10}")
print(f"  {'-'*60}")
print(f"  {'3-class (A/M/B)':<25} {pp_cls_uni:>12.2f} {pp_cls_bi:>12.2f} {(1-pp_cls_bi/pp_cls_uni)*100:>9.1f}%")
print(f"  {'11-suffix':<25} {pp_sfx_uni:>12.2f} {pp_sfx_bi:>12.2f} {(1-pp_sfx_bi/pp_sfx_uni)*100:>9.1f}%")
print(f"  {'word type':<25} {pp_word_uni:>12.2f} {pp_word_bi:>12.2f} {(1-pp_word_bi/pp_word_uni)*100:>9.1f}%")

# Also compute within-line only (exclude cross-line transitions)
line_cls_seqs = [line['cls'] for line in lines]
line_sfx_seqs = [line['sfx'] for line in lines]
line_word_seqs = [line['collapsed'] for line in lines]

def within_line_perplexity(seqs, alpha=0.1):
    """Bigram perplexity computed only within lines."""
    vocab = set()
    for s in seqs:
        vocab.update(s)
    V = len(vocab)

    bigrams = Counter()
    unigrams = Counter()
    n = 0
    for seq in seqs:
        for i in range(len(seq) - 1):
            bigrams[(seq[i], seq[i+1])] += 1
            unigrams[seq[i]] += 1
            n += 1

    if n == 0:
        return 0
    log_prob = 0
    for seq in seqs:
        for i in range(len(seq) - 1):
            p = (bigrams[(seq[i], seq[i+1])] + alpha) / (unigrams[seq[i]] + alpha * V)
            log_prob += math.log2(p)

    return 2 ** (-log_prob / n)

pp_cls_line = within_line_perplexity(line_cls_seqs)
pp_sfx_line = within_line_perplexity(line_sfx_seqs)
pp_word_line = within_line_perplexity(line_word_seqs)

print(f"\n  Within-line bigram perplexity:")
print(f"  {'3-class':<25} {pp_cls_line:.2f}")
print(f"  {'11-suffix':<25} {pp_sfx_line:.2f}")
print(f"  {'word type':<25} {pp_word_line:.2f}")


# ══════════════════════════════════════════════════════════════════
# 44e: LINE POSITION × CLASS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("44e: LINE POSITION × CLASS")
print("    Which classes appear at line-initial, -medial, and -final?")
print("=" * 70)

# Compute class distributions at each normalized position
pos_cls = defaultdict(Counter)  # pos_bin → class → count
# Also absolute positions
abs_pos_cls = defaultdict(Counter)  # abs_pos → class → count
end_pos_cls = defaultdict(Counter)  # pos_from_end → class → count

for line in lines:
    n = len(line['cls'])
    for i, c in enumerate(line['cls']):
        # Normalized position (0-4 bins)
        bin_idx = int(i / n * 5) if n > 1 else 2
        bin_idx = min(bin_idx, 4)
        pos_cls[bin_idx][c] += 1

        # Absolute position from start
        ap = min(i, 5)
        abs_pos_cls[ap][c] += 1

        # Absolute position from end
        ep = min(n - 1 - i, 5)
        end_pos_cls[ep][c] += 1

# Print absolute position from start
print(f"\n  Class distribution by position from start:")
print(f"  {'Pos':>4} {'N':>6} {'%A':>6} {'%M':>6} {'%B':>6}")
for pos in sorted(abs_pos_cls.keys()):
    total = sum(abs_pos_cls[pos].values())
    print(f"  {pos:>4} {total:>6} "
          f"{abs_pos_cls[pos].get('A',0)/total*100:>5.1f} "
          f"{abs_pos_cls[pos].get('M',0)/total*100:>5.1f} "
          f"{abs_pos_cls[pos].get('B',0)/total*100:>5.1f}")

# Print absolute position from end
print(f"\n  Class distribution by position from end:")
print(f"  {'Pos':>4} {'N':>6} {'%A':>6} {'%M':>6} {'%B':>6}")
for pos in sorted(end_pos_cls.keys()):
    total = sum(end_pos_cls[pos].values())
    print(f"  {pos:>4} {total:>6} "
          f"{end_pos_cls[pos].get('A',0)/total*100:>5.1f} "
          f"{end_pos_cls[pos].get('M',0)/total*100:>5.1f} "
          f"{end_pos_cls[pos].get('B',0)/total*100:>5.1f}")

# Chi-squared test for position × class association
# Simple version: compare first position vs last position class distributions
first_cls = Counter()
last_cls = Counter()
for line in lines:
    first_cls[line['cls'][0]] += 1
    last_cls[line['cls'][-1]] += 1

print(f"\n  Line-initial vs line-final class distributions:")
print(f"  {'Position':<12} {'A':>6} {'M':>6} {'B':>6}")
n_first = sum(first_cls.values())
n_last = sum(last_cls.values())
print(f"  {'Initial':<12} {first_cls.get('A',0)/n_first*100:>5.1f}% {first_cls.get('M',0)/n_first*100:>5.1f}% {first_cls.get('B',0)/n_first*100:>5.1f}%")
print(f"  {'Final':<12} {last_cls.get('A',0)/n_last*100:>5.1f}% {last_cls.get('M',0)/n_last*100:>5.1f}% {last_cls.get('B',0)/n_last*100:>5.1f}%")

# Also: what fraction of line-final words are in each SUFFIX (not just class)?
final_sfx = Counter()
for line in lines:
    final_sfx[line['sfx'][-1]] += 1
print(f"\n  Line-final suffix distribution:")
for sfx, cnt in final_sfx.most_common():
    print(f"    {sfx:<8} {cnt:>5} ({cnt/len(lines)*100:.1f}%)")

# Do Class A words predict line endings?
# Test: given a Class A word at position i, how many words remain until line end?
a_words_to_end = []
m_words_to_end = []
b_words_to_end = []
for line in lines:
    n = len(line['cls'])
    for i, c in enumerate(line['cls']):
        remaining = n - 1 - i
        if c == 'A': a_words_to_end.append(remaining)
        elif c == 'M': m_words_to_end.append(remaining)
        else: b_words_to_end.append(remaining)

print(f"\n  Mean words remaining after class occurrence:")
print(f"    A: {np.mean(a_words_to_end):.2f} (n={len(a_words_to_end)})")
print(f"    M: {np.mean(m_words_to_end):.2f} (n={len(m_words_to_end)})")
print(f"    B: {np.mean(b_words_to_end):.2f} (n={len(b_words_to_end)})")


# ══════════════════════════════════════════════════════════════════
# SYNTHESIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PHASE 44 SYNTHESIS")
print("=" * 70)

print("""
  44a: DISTRIBUTIONAL CLUSTERING
    (See cluster composition above)

  44b: CLUSTER-MORPH AGREEMENT
    (See NMI and cross-tabulation above)

  44c: LINE CLASS SEQUENCES
    (See patterns and bigram frequencies above)

  44d: PERPLEXITY
    (See perplexity table above)

  44e: POSITION × CLASS
    (See distribution tables above)

[Phase 44 Complete]
""")
