#!/usr/bin/env python3
"""
ANATOMY OF ANOMALOUS PREDICTABILITY
===============================================

word_predictability_decomposition found MI/H = 0.377, ~50% higher than English (~0.2-0.3).
This phase dissects the anomaly.

Sub-analyses:
  46a) MI CONCENTRATION — How is MI distributed across word pairs?
       Cumulative MI curve. Is it 50 pairs or 5,000?

  46b) POSITION 1 DEEP DIVE — What words appear at position 1
       (second word of line)? Is there a function-word bottleneck?

  46c) VOCABULARY-CONTROLLED MI — Is the high MI/H ratio just because
       the VMS has a small effective vocabulary? Compare MI/H at
       matched effective vocabulary sizes using UNK mapping.

  46d) WORD-LEVEL DISTANCE DECAY — MI(word_i, word_{i+k}) for k=1..5.
       Does word-level predictability extend beyond adjacent pairs?

  46e) GENERATIVE MODEL COMPARISON — Generate text from unigram,
       class bigram, and word bigram models. Compare MI/H to actual VMS.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, get_collapsed, get_suffix, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(46)
np.random.seed(46)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']



def get_class(sfx):
    if sfx in ('dy', 'y'): return 'A'
    if sfx in ('X', 'ar', 'in'): return 'M'
    return 'B'  # aiin, ain, iin, al, ol, or

FOLIO_DIR = Path("folios")


print("Loading lines...")
lines = load_lines()

# Build collapsed word sequences per line
line_collapsed = []
all_collapsed = []
for line in lines:
    coll = [get_collapsed(w) for w in line['words']]
    line_collapsed.append(coll)
    all_collapsed.extend(coll)

word_counts = Counter(all_collapsed)
vocab_size = len(word_counts)
N = len(all_collapsed)
print(f"  {len(lines)} lines, {N} word tokens, {vocab_size} types")

# Precompute bigrams
all_bigrams = Counter()
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        all_bigrams[(seq[i], seq[i+1])] += 1
total_bigrams = sum(all_bigrams.values())

# Unigram and bigram entropy
def compute_H_unigram(counts, total):
    H = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            H -= p * math.log2(p)
    return H

def compute_H_bigram(bigram_counts, total_bg):
    """H(W2|W1) = H(W1,W2) - H(W1)"""
    # Joint entropy
    H_joint = 0.0
    for c in bigram_counts.values():
        if c > 0:
            p = c / total_bg
            H_joint -= p * math.log2(p)
    # Marginal H(W1)
    w1_counts = Counter()
    for (w1, w2), c in bigram_counts.items():
        w1_counts[w1] += c
    H_w1 = 0.0
    for c in w1_counts.values():
        if c > 0:
            p = c / total_bg
            H_w1 -= p * math.log2(p)
    return H_joint - H_w1

H_uni = compute_H_unigram(word_counts, N)
H_cond = compute_H_bigram(all_bigrams, total_bigrams)
MI = H_uni - H_cond
print(f"  H(word) = {H_uni:.3f}, H(word|prev) = {H_cond:.3f}, MI = {MI:.3f}, MI/H = {MI/H_uni:.3f}")


# ══════════════════════════════════════════════════════════════════
# 46a: MI CONCENTRATION
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("46a: MI CONCENTRATION")
print("    How is MI distributed across word pairs?")
print("=" * 70)

# Pointwise MI for each bigram type
# PMI(w1,w2) = log2(P(w1,w2) / (P(w1)*P(w2)))
# Contribution to MI = P(w1,w2) * PMI(w1,w2)

pmi_contributions = []
for (w1, w2), count in all_bigrams.items():
    p_joint = count / total_bigrams
    p_w1 = word_counts[w1] / N
    p_w2 = word_counts[w2] / N
    if p_w1 > 0 and p_w2 > 0:
        pmi = math.log2(p_joint / (p_w1 * p_w2))
        contribution = p_joint * pmi
        pmi_contributions.append((w1, w2, count, pmi, contribution))

# Sort by absolute contribution (descending)
pmi_contributions.sort(key=lambda x: abs(x[4]), reverse=True)

total_mi_check = sum(c[4] for c in pmi_contributions)
print(f"\n  Total MI from PMI sum: {total_mi_check:.4f} bits")
print(f"  (Direct MI estimate: {MI:.4f} bits)")

# Cumulative MI curve
cumulative = 0.0
milestones = {10: None, 25: None, 50: None, 100: None, 250: None, 500: None, 1000: None}
for i, (w1, w2, count, pmi, contrib) in enumerate(pmi_contributions):
    cumulative += contrib
    for m in milestones:
        if milestones[m] is None and i + 1 >= m:
            milestones[m] = cumulative / total_mi_check * 100

print(f"\n  Cumulative MI concentration:")
print(f"  {'Top N pairs':>15} {'% of total MI':>15}")
for m in sorted(milestones):
    if milestones[m] is not None:
        print(f"  {m:>15} {milestones[m]:>14.1f}%")

n_types = len(pmi_contributions)
print(f"\n  Total bigram types: {n_types}")

# 50% threshold
cumulative = 0.0
for i, (w1, w2, count, pmi, contrib) in enumerate(pmi_contributions):
    cumulative += contrib
    if cumulative >= 0.5 * total_mi_check:
        print(f"  50% of MI reached at top {i+1} pairs ({(i+1)/n_types*100:.1f}% of types)")
        break

# Top 20 contributors
print(f"\n  Top 20 MI contributors:")
print(f"  {'Word1':>15} {'Word2':>15} {'Count':>6} {'PMI':>7} {'Contrib':>8} {'%MI':>6}")
for w1, w2, count, pmi, contrib in pmi_contributions[:20]:
    print(f"  {w1:>15} {w2:>15} {count:>6} {pmi:>7.2f} {contrib:>8.5f} {contrib/total_mi_check*100:>5.1f}%")

# Positive vs negative contributions
pos_mi = sum(c[4] for c in pmi_contributions if c[4] > 0)
neg_mi = sum(c[4] for c in pmi_contributions if c[4] < 0)
n_pos = sum(1 for c in pmi_contributions if c[4] > 0)
n_neg = sum(1 for c in pmi_contributions if c[4] < 0)
print(f"\n  Positive MI: {pos_mi:.4f} from {n_pos} types")
print(f"  Negative MI: {neg_mi:.4f} from {n_neg} types")
print(f"  Net MI: {pos_mi + neg_mi:.4f}")
print(f"  Negative/positive ratio: {abs(neg_mi)/pos_mi:.3f}")


# ══════════════════════════════════════════════════════════════════
# 46b: POSITION 1 DEEP DIVE
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("46b: POSITION 1 DEEP DIVE")
print("    What words appear at position 1 (second word of line)?")
print("=" * 70)

# Collect words by position
pos_words = defaultdict(list)
for seq in line_collapsed:
    for i, w in enumerate(seq):
        if i == 0:
            pos_words['initial'].append(w)
        elif i == len(seq) - 1:
            pos_words['final'].append(w)
        else:
            pos_words['interior'].append(w)
        if i == 1:
            pos_words['pos1'].append(w)
        if i == 2:
            pos_words['pos2'].append(w)

for pos_name in ['initial', 'pos1', 'pos2', 'interior', 'final']:
    words = pos_words[pos_name]
    if not words:
        continue
    wc = Counter(words)
    n = len(words)
    t = len(wc)
    H = compute_H_unigram(wc, n)
    top5 = wc.most_common(5)
    top5_str = ", ".join(f"{w}({c},{c/n*100:.1f}%)" for w, c in top5)
    concentration = sum(c for _, c in wc.most_common(10)) / n * 100
    print(f"\n  {pos_name}: {n} tokens, {t} types, H={H:.3f} bits")
    print(f"    Top 5: {top5_str}")
    print(f"    Top 10 concentration: {concentration:.1f}%")

# Position 1 suffix distribution
print(f"\n  Position 1 suffix distribution:")
pos1_sfx = Counter()
for w in pos_words['pos1']:
    pos1_sfx[get_suffix(w)] += 1
all_sfx = Counter()
for w in all_collapsed:
    all_sfx[get_suffix(w)] += 1
print(f"  {'Suffix':>8} {'Pos1%':>8} {'All%':>8} {'Ratio':>8}")
for sfx in sorted(set(list(pos1_sfx.keys()) + list(all_sfx.keys()))):
    p1 = pos1_sfx.get(sfx, 0) / len(pos_words['pos1']) * 100
    pa = all_sfx.get(sfx, 0) / N * 100
    ratio = p1 / pa if pa > 0 else 0
    if pa > 0.5:
        print(f"  {sfx:>8} {p1:>7.1f}% {pa:>7.1f}% {ratio:>7.2f}x")

# Position 1 class distribution
print(f"\n  Position 1 class distribution:")
pos1_cls = Counter()
for w in pos_words['pos1']:
    pos1_cls[get_class(get_suffix(w))] += 1
all_cls = Counter()
for w in all_collapsed:
    all_cls[get_class(get_suffix(w))] += 1
print(f"  {'Class':>8} {'Pos1%':>8} {'All%':>8} {'Ratio':>8}")
for cls in ['A', 'M', 'B']:
    p1 = pos1_cls.get(cls, 0) / len(pos_words['pos1']) * 100
    pa = all_cls.get(cls, 0) / N * 100
    ratio = p1 / pa if pa > 0 else 0
    print(f"  {cls:>8} {p1:>7.1f}% {pa:>7.1f}% {ratio:>7.2f}x")

# What unique words ONLY appear at position 1?
pos1_set = set(pos_words['pos1'])
other_set = set(all_collapsed) - pos1_set
pos1_only = set()
for w in pos1_set:
    # Count how often w appears at non-pos1 positions
    other_count = word_counts[w] - Counter(pos_words['pos1'])[w]
    if other_count == 0:
        pos1_only.add(w)
if pos1_only:
    print(f"\n  Words ONLY at position 1: {len(pos1_only)}")
    pos1_wc = Counter(pos_words['pos1'])
    top_excl = sorted(pos1_only, key=lambda w: pos1_wc[w], reverse=True)[:10]
    for w in top_excl:
        print(f"    {w} ({pos1_wc[w]} tokens)")


# ══════════════════════════════════════════════════════════════════
# 46c: VOCABULARY-CONTROLLED MI
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("46c: VOCABULARY-CONTROLLED MI")
print("    Is high MI/H just from small vocabulary?")
print("=" * 70)

# Map rare words to <UNK> at various thresholds
# Then recompute MI/H at each effective vocabulary size
thresholds = [1, 2, 3, 5, 10, 20, 50]

print(f"\n  {'Min freq':>10} {'Eff vocab':>10} {'H(W)':>8} {'H(W|prev)':>10} {'MI':>8} {'MI/H':>8}")

for min_freq in thresholds:
    # Map words below threshold to UNK
    mapped = {}
    for w, c in word_counts.items():
        if c >= min_freq:
            mapped[w] = w
        else:
            mapped[w] = '<UNK>'
    
    # Rebuild counts
    mapped_counts = Counter()
    for w in all_collapsed:
        mapped_counts[mapped[w]] += 1
    
    mapped_bigrams = Counter()
    for seq in line_collapsed:
        mapped_seq = [mapped[get_collapsed(w)] if get_collapsed(w) in mapped else '<UNK>' for w in seq]
        # Actually words are already collapsed
        mapped_seq = [mapped.get(w, '<UNK>') for w in seq]
        for i in range(len(mapped_seq) - 1):
            mapped_bigrams[(mapped_seq[i], mapped_seq[i+1])] += 1
    
    eff_vocab = len(mapped_counts)
    h_uni = compute_H_unigram(mapped_counts, N)
    total_mb = sum(mapped_bigrams.values())
    h_cond = compute_H_bigram(mapped_bigrams, total_mb)
    mi = h_uni - h_cond
    mi_h = mi / h_uni if h_uni > 0 else 0
    print(f"  {min_freq:>10} {eff_vocab:>10} {h_uni:>8.3f} {h_cond:>10.3f} {mi:>8.3f} {mi_h:>8.3f}")

# Compare to shuffled text at original vocabulary
print(f"\n  Shuffled comparison (destroy word order, keep frequencies):")
n_shuffle = 20
shuffle_mi_h = []
for trial in range(n_shuffle):
    # Shuffle words within each line
    shuf_bigrams = Counter()
    total_sb = 0
    for seq in line_collapsed:
        shuf = list(seq)
        random.shuffle(shuf)
        for i in range(len(shuf) - 1):
            shuf_bigrams[(shuf[i], shuf[i+1])] += 1
            total_sb += 1
    h_s = compute_H_bigram(shuf_bigrams, total_sb)
    mi_s = H_uni - h_s
    shuffle_mi_h.append(mi_s / H_uni if H_uni > 0 else 0)

print(f"  Shuffled MI/H: mean={np.mean(shuffle_mi_h):.4f}, std={np.std(shuffle_mi_h):.4f}")
print(f"  Actual MI/H:   {MI/H_uni:.4f}")
print(f"  z-score:        {(MI/H_uni - np.mean(shuffle_mi_h)) / np.std(shuffle_mi_h):.1f}")

# Also compare to GLOBAL shuffle (destroy line structure too)
print(f"\n  Global shuffle (destroy all structure):")
n_gshuffle = 20
global_mi_h = []
for trial in range(n_gshuffle):
    all_shuf = list(all_collapsed)
    random.shuffle(all_shuf)
    # Reconstruct line lengths
    shuf_bigrams = Counter()
    total_gb = 0
    idx = 0
    for seq in line_collapsed:
        n_w = len(seq)
        seg = all_shuf[idx:idx+n_w]
        idx += n_w
        for i in range(len(seg) - 1):
            shuf_bigrams[(seg[i], seg[i+1])] += 1
            total_gb += 1
    h_g = compute_H_bigram(shuf_bigrams, total_gb)
    mi_g = H_uni - h_g
    global_mi_h.append(mi_g / H_uni if H_uni > 0 else 0)

print(f"  Global shuffle MI/H: mean={np.mean(global_mi_h):.4f}, std={np.std(global_mi_h):.4f}")
print(f"  z-score vs global:   {(MI/H_uni - np.mean(global_mi_h)) / np.std(global_mi_h):.1f}")


# ══════════════════════════════════════════════════════════════════
# 46d: WORD-LEVEL DISTANCE DECAY
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("46d: WORD-LEVEL DISTANCE DECAY")
print("    MI(word_i, word_{i+k}) for k=1..5")
print("=" * 70)

for gap in range(1, 6):
    # Collect pairs at distance gap
    gap_bigrams = Counter()
    total_gap = 0
    for seq in line_collapsed:
        for i in range(len(seq) - gap):
            gap_bigrams[(seq[i], seq[i+gap])] += 1
            total_gap += 1
    
    if total_gap == 0:
        continue
    
    h_gap = compute_H_bigram(gap_bigrams, total_gap)
    mi_gap = H_uni - h_gap
    
    # Shuffled null
    shuf_mi = []
    for trial in range(50):
        shuf_bg = Counter()
        total_sb = 0
        for seq in line_collapsed:
            shuf = list(seq)
            random.shuffle(shuf)
            for i in range(len(shuf) - gap):
                shuf_bg[(shuf[i], shuf[i+gap])] += 1
                total_sb += 1
        h_s = compute_H_bigram(shuf_bg, total_sb)
        mi_s = H_uni - h_s
        shuf_mi.append(mi_s)
    
    excess = mi_gap - np.mean(shuf_mi)
    z = excess / np.std(shuf_mi) if np.std(shuf_mi) > 0 else 0
    print(f"  Gap {gap}: MI={mi_gap:.4f}, shuffled={np.mean(shuf_mi):.4f}±{np.std(shuf_mi):.4f}, excess={excess:.4f}, z={z:.1f}")


# ══════════════════════════════════════════════════════════════════
# 46e: GENERATIVE MODEL COMPARISON
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("46e: GENERATIVE MODEL COMPARISON")
print("    Generate text from models, compare MI/H")
print("=" * 70)

# Get class for each word
word_to_class = {}
for w in word_counts:
    word_to_class[w] = get_class(get_suffix(w))

# Build class bigram model
class_bigrams = Counter()
class_unigrams = Counter()
for seq in line_collapsed:
    classes = [word_to_class[w] for w in seq]
    for c in classes:
        class_unigrams[c] += 1
    for i in range(len(classes) - 1):
        class_bigrams[(classes[i], classes[i+1])] += 1

# Words per class
class_words = defaultdict(list)
class_word_probs = {}
for w, c in word_to_class.items():
    class_words[c].append(w)

for cls in class_words:
    words_in_cls = class_words[cls]
    total_cls = sum(word_counts[w] for w in words_in_cls)
    probs = np.array([word_counts[w] / total_cls for w in words_in_cls])
    class_word_probs[cls] = (words_in_cls, probs)

# Word bigram model
word_bigram_probs = defaultdict(lambda: Counter())
for (w1, w2), c in all_bigrams.items():
    word_bigram_probs[w1][w2] += c

def generate_unigram(n_tokens, line_lengths):
    """Generate from unigram distribution"""
    words = list(word_counts.keys())
    probs = np.array([word_counts[w] for w in words], dtype=float)
    probs /= probs.sum()
    
    generated_lines = []
    for length in line_lengths:
        line = list(np.random.choice(words, size=length, p=probs))
        generated_lines.append(line)
    return generated_lines

def generate_class_bigram(line_lengths):
    """Generate from class bigram model + unigram within class"""
    class_list = list(class_unigrams.keys())
    class_probs = np.array([class_unigrams[c] for c in class_list], dtype=float)
    class_probs /= class_probs.sum()
    
    # Transition probs
    class_trans = {}
    for c1 in class_list:
        next_counts = np.array([class_bigrams.get((c1, c2), 0) for c2 in class_list], dtype=float)
        total = next_counts.sum()
        if total > 0:
            class_trans[c1] = next_counts / total
        else:
            class_trans[c1] = class_probs
    
    generated_lines = []
    for length in line_lengths:
        # Start with unigram class
        cls = np.random.choice(class_list, p=class_probs)
        words_cls, probs_cls = class_word_probs[cls]
        line = [np.random.choice(words_cls, p=probs_cls)]
        
        for _ in range(length - 1):
            cls = np.random.choice(class_list, p=class_trans[cls])
            words_cls, probs_cls = class_word_probs[cls]
            line.append(np.random.choice(words_cls, p=probs_cls))
        generated_lines.append(line)
    return generated_lines

def generate_word_bigram(line_lengths):
    """Generate from word bigram model"""
    words = list(word_counts.keys())
    unigram_probs = np.array([word_counts[w] for w in words], dtype=float)
    unigram_probs /= unigram_probs.sum()
    word_to_idx = {w: i for i, w in enumerate(words)}
    
    generated_lines = []
    for length in line_lengths:
        w = np.random.choice(words, p=unigram_probs)
        line = [w]
        for _ in range(length - 1):
            nexts = word_bigram_probs[w]
            if nexts:
                next_words = list(nexts.keys())
                next_probs = np.array([nexts[nw] for nw in next_words], dtype=float)
                next_probs /= next_probs.sum()
                w = np.random.choice(next_words, p=next_probs)
            else:
                w = np.random.choice(words, p=unigram_probs)
            line.append(w)
        generated_lines.append(line)
    return generated_lines

def measure_mi_h(generated_lines):
    """Compute MI/H for generated text"""
    all_gen = []
    for line in generated_lines:
        all_gen.extend(line)
    
    gen_counts = Counter(all_gen)
    gen_N = len(all_gen)
    
    gen_bigrams = Counter()
    for line in generated_lines:
        for i in range(len(line) - 1):
            gen_bigrams[(line[i], line[i+1])] += 1
    gen_total_bg = sum(gen_bigrams.values())
    
    if gen_total_bg == 0 or gen_N == 0:
        return 0, 0, 0
    
    h_uni = compute_H_unigram(gen_counts, gen_N)
    h_cond = compute_H_bigram(gen_bigrams, gen_total_bg)
    mi = h_uni - h_cond
    return h_uni, mi, mi / h_uni if h_uni > 0 else 0

# Get actual line lengths
actual_lengths = [len(seq) for seq in line_collapsed]

n_trials = 10
print(f"\n  Generating {n_trials} samples of each model ({len(actual_lengths)} lines each)...")

results = {'unigram': [], 'class_bigram': [], 'word_bigram': []}

for trial in range(n_trials):
    gen_uni = generate_unigram(N, actual_lengths)
    h, mi, mi_h = measure_mi_h(gen_uni)
    results['unigram'].append((h, mi, mi_h))
    
    gen_cls = generate_class_bigram(actual_lengths)
    h, mi, mi_h = measure_mi_h(gen_cls)
    results['class_bigram'].append((h, mi, mi_h))
    
    gen_wb = generate_word_bigram(actual_lengths)
    h, mi, mi_h = measure_mi_h(gen_wb)
    results['word_bigram'].append((h, mi, mi_h))

print(f"\n  {'Model':>18} {'H(W)':>8} {'MI':>8} {'MI/H':>8}")
print(f"  {'ACTUAL VMS':>18} {H_uni:>8.3f} {MI:>8.3f} {MI/H_uni:>8.3f}")
for model_name in ['unigram', 'class_bigram', 'word_bigram']:
    h_vals = [r[0] for r in results[model_name]]
    mi_vals = [r[1] for r in results[model_name]]
    mi_h_vals = [r[2] for r in results[model_name]]
    print(f"  {model_name:>18} {np.mean(h_vals):>8.3f} {np.mean(mi_vals):>8.3f} {np.mean(mi_h_vals):>8.3f} ± {np.std(mi_h_vals):.3f}")

# How much of MI/H does each model explain?
uni_mi_h = np.mean([r[2] for r in results['unigram']])
cls_mi_h = np.mean([r[2] for r in results['class_bigram']])
wb_mi_h = np.mean([r[2] for r in results['word_bigram']])
actual_mi_h = MI / H_uni

print(f"\n  MI/H decomposition:")
print(f"    Unigram baseline:                  {uni_mi_h:.4f}")
print(f"    Class bigram adds:                +{cls_mi_h - uni_mi_h:.4f} (class syntax)")
print(f"    Word bigram adds:                 +{wb_mi_h - cls_mi_h:.4f} (word-specific)")
print(f"    Actual VMS MI/H:                   {actual_mi_h:.4f}")
print(f"    Word bigram model explains:        {wb_mi_h/actual_mi_h*100:.1f}% of actual")
print(f"    Gap (actual - word bigram):        {actual_mi_h - wb_mi_h:.4f}")

print("\n" + "=" * 70)
print("mutual_information_anatomy COMPLETE")
print("=" * 70)
