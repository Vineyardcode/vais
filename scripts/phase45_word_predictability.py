#!/usr/bin/env python3
"""
Phase 45 — DECOMPOSING WORD-LEVEL PREDICTABILITY
=================================================

Phase 44 found that word-level bigram reduces perplexity by 40.6%,
vastly more than class (0.9%) or suffix (3.7%). But the Voynich
manuscript is notorious for excessive word repetition. How much of
the 40.6% is just words repeating themselves?

Sub-analyses:
  45a) REPETITION CONTRIBUTION — What fraction of word bigram MI is
       from self-repetition (w_i = w_{i+1})? Remove repeated pairs,
       recompute perplexity.

  45b) TOP WORD BIGRAMS — List the most over-represented word pairs.
       Are they collocations or repetitions?

  45c) ZIPF'S LAW — Does the word frequency distribution follow Zipf?
       What's the exponent?

  45d) VOCABULARY GROWTH — Heaps' law: types vs tokens. Compare to
       natural language expectations.

  45e) WORD ENTROPY vs NATURAL LANGUAGE — Compare H(word) and
       H(word|prev_word) to typical natural language values.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, get_collapsed, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(45)
np.random.seed(45)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']


FOLIO_DIR = Path("folios")


print("Loading lines...")
lines = load_lines()
total_words = sum(len(l['words']) for l in lines)
print(f"  {len(lines)} lines, {total_words} word tokens")

# Build collapsed word sequences
all_collapsed = []
line_collapsed = []
for line in lines:
    coll = [get_collapsed(w) for w in line['words']]
    line_collapsed.append(coll)
    all_collapsed.extend(coll)

word_counts = Counter(all_collapsed)
vocab_size = len(word_counts)
print(f"  {vocab_size} word types (collapsed)")


# ══════════════════════════════════════════════════════════════════
# 45a: REPETITION CONTRIBUTION
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("45a: REPETITION CONTRIBUTION")
print("    How much of word bigram predictability is self-repetition?")
print("=" * 70)

# Count all bigrams
all_bigrams = Counter()
self_bigrams = Counter()
non_self_bigrams = Counter()
total_bigrams = 0
total_self = 0
total_non_self = 0

for seq in line_collapsed:
    for i in range(len(seq) - 1):
        w1, w2 = seq[i], seq[i+1]
        all_bigrams[(w1, w2)] += 1
        total_bigrams += 1
        if w1 == w2:
            self_bigrams[(w1, w2)] += 1
            total_self += 1
        else:
            non_self_bigrams[(w1, w2)] += 1
            total_non_self += 1

self_rate = total_self / total_bigrams * 100
print(f"\n  Total bigrams: {total_bigrams}")
print(f"  Self-repetitions (w_i = w_{{i+1}}): {total_self} ({self_rate:.1f}%)")
print(f"  Non-self bigrams: {total_non_self}")

# Expected self-repetition rate under unigram independence
# E[self] = sum(p(w)^2) = sum(c(w)^2/N^2) * N = sum(c(w)^2) / N
N = len(all_collapsed)
expected_self_rate = sum(c**2 for c in word_counts.values()) / N / N * 100
print(f"  Expected self-repetition (unigram null): {expected_self_rate:.1f}%")
print(f"  Observed/Expected ratio: {self_rate / expected_self_rate:.2f}x")

# Perplexity: all pairs, self-only removed, non-self only
def bigram_perplexity_from_pairs(pair_list, vocab):
    """Compute perplexity from list of (w1, w2) pairs."""
    V = len(vocab)
    alpha = 0.1
    bigrams = Counter(pair_list)
    unigrams = Counter(w1 for w1, w2 in pair_list)
    n = len(pair_list)
    if n == 0:
        return 0
    log_prob = 0
    for w1, w2 in pair_list:
        p = (bigrams[(w1, w2)] + alpha) / (unigrams[w1] + alpha * V)
        log_prob += math.log2(p)
    return 2 ** (-log_prob / n)

def unigram_perplexity_from_tokens(tokens, vocab):
    V = len(vocab)
    alpha = 0.1
    counts = Counter(tokens)
    N_tok = len(tokens)
    log_prob = sum(math.log2((counts[w] + alpha) / (N_tok + alpha * V)) for w in tokens)
    return 2 ** (-log_prob / N_tok)

# Build pair lists
all_pairs = []
non_self_pairs = []
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        pair = (seq[i], seq[i+1])
        all_pairs.append(pair)
        if seq[i] != seq[i+1]:
            non_self_pairs.append(pair)

vocab = set(word_counts.keys())
pp_all = bigram_perplexity_from_pairs(all_pairs, vocab)
pp_non_self = bigram_perplexity_from_pairs(non_self_pairs, vocab)
pp_uni = unigram_perplexity_from_tokens(all_collapsed, vocab)

print(f"\n  Perplexity comparison:")
print(f"    Unigram: {pp_uni:.1f}")
print(f"    Bigram (all pairs): {pp_all:.1f}")
print(f"    Bigram (exclude self-rep): {pp_non_self:.1f}")
print(f"    All reduction: {(1 - pp_all/pp_uni)*100:.1f}%")
print(f"    Non-self reduction: {(1 - pp_non_self/pp_uni)*100:.1f}%")
print(f"    Self-repetition contributes: {((pp_non_self - pp_all) / (pp_uni - pp_all))*100:.1f}% of total reduction")

# Compare to natural language self-repetition rates
print(f"\n  Context: natural language self-repetition rates:")
print(f"    English prose: ~0.5-1.0%")
print(f"    Voynich: {self_rate:.1f}%")
print(f"    Voynich / English ratio: ~{self_rate / 0.75:.0f}x")


# ══════════════════════════════════════════════════════════════════
# 45b: TOP WORD BIGRAMS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("45b: TOP WORD BIGRAMS")
print("    Most over-represented word pairs (obs/expected ratio)")
print("=" * 70)

# Compute obs/exp for all bigrams with count >= 5
total_bg = sum(all_bigrams.values())
w_first = Counter(w1 for (w1, w2) in all_bigrams for _ in range(all_bigrams[(w1, w2)]))
w_second = Counter(w2 for (w1, w2) in all_bigrams for _ in range(all_bigrams[(w1, w2)]))

ratios = []
for (w1, w2), cnt in all_bigrams.items():
    if cnt < 5:
        continue
    exp = w_first[w1] * w_second[w2] / total_bg
    ratio = cnt / max(exp, 0.001)
    ratios.append((w1, w2, cnt, exp, ratio, w1 == w2))

ratios.sort(key=lambda x: -x[2])  # sort by count

print(f"\n  Top 50 word bigrams by count:")
print(f"  {'Word1':<12} {'Word2':<12} {'Count':>6} {'Exp':>7} {'Ratio':>6} {'Self?':>5}")
print(f"  {'-'*52}")
for w1, w2, cnt, exp, ratio, is_self in ratios[:50]:
    self_mark = " *" if is_self else ""
    print(f"  {w1:<12} {w2:<12} {cnt:>6} {exp:>7.1f} {ratio:>5.1f}x{self_mark}")

# Count how many of top 50 are self-repetitions
n_self_top50 = sum(1 for r in ratios[:50] if r[5])
print(f"\n  Of top 50 by count: {n_self_top50} are self-repetitions")

# Top by O/E ratio (min count 10)
ratios_oe = [r for r in ratios if r[2] >= 10]
ratios_oe.sort(key=lambda x: -x[4])
print(f"\n  Top 30 by O/E ratio (min count 10):")
print(f"  {'Word1':<12} {'Word2':<12} {'Count':>6} {'Exp':>7} {'Ratio':>6} {'Self?':>5}")
print(f"  {'-'*52}")
for w1, w2, cnt, exp, ratio, is_self in ratios_oe[:30]:
    self_mark = " *" if is_self else ""
    print(f"  {w1:<12} {w2:<12} {cnt:>6} {exp:>7.1f} {ratio:>5.1f}x{self_mark}")


# ══════════════════════════════════════════════════════════════════
# 45c: ZIPF'S LAW
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("45c: ZIPF'S LAW")
print("    Does word frequency follow Zipf's law?")
print("=" * 70)

# Rank words by frequency
ranked = word_counts.most_common()
ranks = np.arange(1, len(ranked) + 1)
freqs = np.array([c for _, c in ranked])

# Fit Zipf exponent: log(freq) = a - b * log(rank)
log_ranks = np.log10(ranks.astype(float))
log_freqs = np.log10(freqs.astype(float))

# Linear regression
A = np.vstack([log_ranks, np.ones(len(log_ranks))]).T
result = np.linalg.lstsq(A, log_freqs, rcond=None)
slope, intercept = result[0]

print(f"\n  Zipf exponent: {-slope:.3f} (natural language: ~1.0)")
print(f"  R² = {1 - np.sum((log_freqs - (slope * log_ranks + intercept))**2) / np.sum((log_freqs - np.mean(log_freqs))**2):.4f}")

# Show top 20 words
print(f"\n  Top 20 words:")
for rank, (word, count) in enumerate(ranked[:20], 1):
    zipf_expected = 10**(slope * np.log10(rank) + intercept)
    print(f"    {rank:>3}. {word:<15} {count:>5}  (Zipf pred: {zipf_expected:.0f})")

# Hapax legomena
hapax = sum(1 for _, c in ranked if c == 1)
dis_legomena = sum(1 for _, c in ranked if c == 2)
print(f"\n  Hapax legomena (count=1): {hapax} ({hapax/len(ranked)*100:.1f}% of types)")
print(f"  Dis legomena (count=2): {dis_legomena} ({dis_legomena/len(ranked)*100:.1f}%)")
print(f"  Context: English prose hapax ≈ 40-50% of types")


# ══════════════════════════════════════════════════════════════════
# 45d: VOCABULARY GROWTH (HEAPS' LAW)
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("45d: VOCABULARY GROWTH (HEAPS' LAW)")
print("    Types vs tokens. V(N) = K * N^beta")
print("=" * 70)

# Compute types seen vs tokens consumed
seen = set()
growth = []
for i, w in enumerate(all_collapsed):
    seen.add(w)
    if (i + 1) % 500 == 0 or i == len(all_collapsed) - 1:
        growth.append((i + 1, len(seen)))

tokens_arr = np.array([g[0] for g in growth], dtype=float)
types_arr = np.array([g[1] for g in growth], dtype=float)

# Fit Heaps' law: log(V) = log(K) + beta * log(N)
log_tokens = np.log10(tokens_arr)
log_types = np.log10(types_arr)
A = np.vstack([log_tokens, np.ones(len(log_tokens))]).T
result = np.linalg.lstsq(A, log_types, rcond=None)
beta, log_K = result[0]

print(f"\n  Heaps' law: V = {10**log_K:.1f} * N^{beta:.3f}")
print(f"    beta = {beta:.3f} (English: ~0.4-0.6, random text: ~1.0)")
print(f"    At N=35747: predicted V = {10**log_K * 35747**beta:.0f}, actual V = {vocab_size}")

# Show growth at checkpoints
print(f"\n  Token checkpoints:")
for n, v in growth:
    if n in [500, 1000, 2000, 5000, 10000, 20000, 35000] or n == growth[-1][0]:
        print(f"    N={n:>6}: V={v:>5} (V/N={v/n:.3f})")


# ══════════════════════════════════════════════════════════════════
# 45e: WORD ENTROPY vs LANGUAGE BENCHMARKS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("45e: WORD ENTROPY AND INFORMATION DENSITY")
print("    How does Voynich compare to natural language?")
print("=" * 70)

# Unigram entropy
h_unigram = -sum((c/N) * math.log2(c/N) for c in word_counts.values())
print(f"\n  H(word) unigram = {h_unigram:.3f} bits")
print(f"    (English: ~9-11 bits, for comparable vocab size)")

# Bigram conditional entropy
bigram_counts = Counter()
unigram_first = Counter()
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        bigram_counts[(seq[i], seq[i+1])] += 1
        unigram_first[seq[i]] += 1

N_bg = sum(bigram_counts.values())
h_bigram_cond = 0
for (w1, w2), cnt in bigram_counts.items():
    p_w1w2 = cnt / N_bg
    p_w2_given_w1 = cnt / unigram_first[w1]
    h_bigram_cond -= p_w1w2 * math.log2(p_w2_given_w1)

print(f"  H(word|prev_word) bigram = {h_bigram_cond:.3f} bits")
print(f"    (English: ~6-7 bits)")

mi_word = h_unigram - h_bigram_cond
print(f"  MI(word; prev_word) = {mi_word:.3f} bits")
print(f"    MI/H ratio = {mi_word/h_unigram:.3f}")
print(f"    (English: ~0.20-0.30)")

# Conditional entropy excluding self-repetitions
bigram_no_self = Counter()
uni_no_self = Counter()
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        if seq[i] != seq[i+1]:
            bigram_no_self[(seq[i], seq[i+1])] += 1
            uni_no_self[seq[i]] += 1

N_ns = sum(bigram_no_self.values())
h_ns = 0
for (w1, w2), cnt in bigram_no_self.items():
    p_w1w2 = cnt / N_ns
    p_w2_given_w1 = cnt / uni_no_self[w1]
    h_ns -= p_w1w2 * math.log2(p_w2_given_w1)

print(f"\n  H(word|prev_word) excluding self-rep = {h_ns:.3f} bits")
print(f"  MI without self-rep = {h_unigram - h_ns:.3f} bits")
print(f"  MI ratio without self-rep = {(h_unigram - h_ns)/h_unigram:.3f}")

# Per-position entropy
print(f"\n  Position-specific word entropy:")
for pos_label, pos_test in [("line-initial", lambda i, n: i == 0),
                              ("position 1", lambda i, n: i == 1),
                              ("interior (2-end-2)", lambda i, n: 2 <= i < n-1),
                              ("line-final", lambda i, n: i == n-1)]:
    pos_words = []
    for seq in line_collapsed:
        n = len(seq)
        for i in range(n):
            if pos_test(i, n):
                pos_words.append(seq[i])
    h_pos = -sum((c/len(pos_words)) * math.log2(c/len(pos_words))
                  for c in Counter(pos_words).values())
    n_types = len(set(pos_words))
    print(f"    {pos_label:<22} H={h_pos:.3f} bits, {len(pos_words)} tokens, {n_types} types")


# ══════════════════════════════════════════════════════════════════
# SYNTHESIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PHASE 45 SYNTHESIS")
print("=" * 70)

print("""
  45a: REPETITION CONTRIBUTION
    (See self-rep rates and perplexity decomposition above)

  45b: TOP WORD BIGRAMS
    (See tables above)

  45c: ZIPF'S LAW
    (See exponent and R² above)

  45d: VOCABULARY GROWTH
    (See Heaps' law fit above)

  45e: ENTROPY COMPARISON
    (See information density measures above)

[Phase 45 Complete]
""")
