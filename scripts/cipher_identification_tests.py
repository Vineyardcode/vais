#!/usr/bin/env python3
"""
CIPHER IDENTIFICATION TESTS
=========================================

hypothesis_discriminators excluded mechanical generation (burstiness B=0.246, all words
bursty). Two hypotheses remain:
  A) Natural language (with unusual phonotactics)
  B) Cipher of a natural language

cipher_identification_tests applies classic cryptanalysis tests:

  A) VERBOSE CIPHER EXCLUSION VIA MI
       If VMS words encode plaintext characters, word-word MI should
       be >= character bigram MI of the plaintext (~1.5 bits for European).
       We know VMS word MI ≈ 0.2-0.3 bits. Is this incompatible?

  B) KAPPA TEST (INDEX OF COINCIDENCE)
       Polyalphabetic ciphers lower IC below monalphabetic. Test IC at
       different periods to detect cycling. Also compare VMS IC to
       known language ranges.

  C) HOMOPHONE DETECTION
       If some VMS characters are homophones (multiple chars → same
       plaintext char), characters with similar successor/predecessor
       distributions could be merged. Find candidate merges and test
       if merging reduces cross-validated char entropy.

  D) WORD-INTERNAL STRUCTURE TEST
       Generate random "words" from VMS character bigram model. Compare
       their positional entropy profile to real VMS words. If character
       bigrams fully explain word structure, profiles should match.
       If VMS has ADDITIONAL constraints, real words will differ.

  E) WORD BOUNDARY INFORMATION
       In natural language, word boundaries carry information (word
       segmentation helps predict text). In a cipher, boundaries may
       be artifacts. Test: does knowing word boundaries reduce character
       prediction error beyond what a pure character stream model gives?
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_H, get_collapsed, load_lines_v2 as load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(53)
np.random.seed(53)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']


FOLIO_DIR = Path("folios")



print("Loading corpus...")
raw_lines = load_lines()
line_collapsed = [[get_collapsed(w) for w in line] for line in raw_lines]
all_collapsed = [w for seq in line_collapsed for w in seq]
N = len(all_collapsed)
vocab = Counter(all_collapsed)
word_types = set(vocab.keys())
n_types = len(word_types)
print(f"  {N} tokens, {n_types} types, {len(raw_lines)} lines\n")


# ============================================================
# 53a: VERBOSE CIPHER EXCLUSION VIA MI
# ============================================================
print("=" * 65)
print("A: VERBOSE CIPHER EXCLUSION VIA MI")
print("=" * 65)

# Compute observed word-level MI (within lines)
word_bigram = Counter()
word_unigram = Counter()
total_bigrams = 0
for line in line_collapsed:
    for i in range(len(line) - 1):
        word_bigram[(line[i], line[i+1])] += 1
        word_unigram[line[i]] += 1
        total_bigrams += 1
    if line:
        word_unigram[line[-1]] += 1  # last word in line

# Raw MI
H_word = compute_H(vocab, N)
H_bigram_joint = compute_H(word_bigram, total_bigrams)
H_word_ctx = compute_H(word_unigram, sum(word_unigram.values()))
MI_word_raw = H_word + H_word_ctx - H_bigram_joint

# Bias correction via permutation
n_perm = 200
mi_null = []
for _ in range(n_perm):
    shuffled_lines = []
    for line in line_collapsed:
        sl = list(line)
        random.shuffle(sl)
        shuffled_lines.append(sl)
    sb = Counter()
    su = Counter()
    st = 0
    for line in shuffled_lines:
        for i in range(len(line) - 1):
            sb[(line[i], line[i+1])] += 1
            su[line[i]] += 1
            st += 1
        if line:
            su[line[-1]] += 1
    H_sb = compute_H(sb, st)
    H_su = compute_H(su, sum(su.values()))
    mi_null.append(H_word + H_su - H_sb)

mi_bias = np.mean(mi_null)
mi_genuine = MI_word_raw - mi_bias
mi_std = np.std(mi_null)
z_mi = (MI_word_raw - mi_bias) / mi_std if mi_std > 0 else 0

print(f"  H(word) = {H_word:.3f} bits")
print(f"  Raw word bigram MI = {MI_word_raw:.4f} bits")
print(f"  Bias (permutation) = {mi_bias:.4f} bits")
print(f"  Genuine MI = {mi_genuine:.4f} bits")
print(f"  z-score = {z_mi:.1f}")
print(f"  MI/H = {mi_genuine/H_word:.4f}")

print(f"\n  VERBOSE CIPHER TEST:")
print(f"  If each VMS word encodes a plaintext character:")
print(f"    Required: MI(word_i, word_j) >= MI(char_i, char_j) in plaintext")
print(f"    English char bigram MI ≈ 1.0-1.5 bits")
print(f"    Latin char bigram MI  ≈ 0.8-1.2 bits")
print(f"    VMS word MI observed  = {mi_genuine:.3f} bits")
print(f"  Ratio: VMS / English = {mi_genuine/1.25:.3f}")
print(f"  VERDICT: {'EXCLUDED — MI too low by {:.0f}×'.format(1.25/mi_genuine) if mi_genuine < 0.5 else 'NOT excluded'}")

# Also check: if each word encodes a SYLLABLE
print(f"\n  SYLLABLE CIPHER TEST:")
print(f"  If each VMS word encodes a plaintext syllable:")
print(f"    Syllable bigram MI ≈ 0.2-0.5 bits (estimate)")
print(f"    VMS word MI = {mi_genuine:.3f} bits")
print(f"  VERDICT: {'CONSISTENT — MI in plausible range' if 0.1 < mi_genuine < 0.8 else 'Marginal'}")


# ============================================================
# 53b: KAPPA TEST (INDEX OF COINCIDENCE)
# ============================================================
print("\n" + "=" * 65)
print("B: KAPPA TEST (INDEX OF COINCIDENCE)")
print("=" * 65)

# Concatenate all characters within lines
all_chars_stream = []
for line in line_collapsed:
    for w in line:
        all_chars_stream.extend(list(w))
        all_chars_stream.append(' ')  # word separator
    all_chars_stream.append('\n')  # line separator

# Remove separators for IC computation
chars_only = [c for c in all_chars_stream if c not in (' ', '\n')]
char_freq = Counter(chars_only)
n_chars = len(chars_only)
alphabet_size = len(char_freq)

# Index of Coincidence
IC = sum(f * (f - 1) for f in char_freq.values()) / (n_chars * (n_chars - 1))

# Expected IC for random text with this alphabet
IC_random = 1.0 / alphabet_size

# Expected IC for various languages (approximate)
IC_english = 0.0667
IC_latin = 0.0770
IC_italian = 0.0738
IC_german = 0.0762

print(f"  VMS character IC = {IC:.4f}")
print(f"  Random (uniform, {alphabet_size} chars) IC = {IC_random:.4f}")
print(f"  English IC ≈ {IC_english}")
print(f"  Latin IC   ≈ {IC_latin}")
print(f"  Italian IC ≈ {IC_italian}")
print(f"  German IC  ≈ {IC_german}")
print(f"\n  VMS IC is {'ABOVE' if IC > IC_english else 'BELOW'} English")
print(f"  VMS IC / English IC = {IC/IC_english:.2f}")

# Kappa test at different periods (checking for polyalphabetic)
print(f"\n  Kappa at different periods (displacement IC):")
print(f"  Period  IC_displaced  Ratio_to_base")
chars_array = chars_only[:]
base_ic = IC
for period in [1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 15, 20, 26, 30, 50]:
    if period >= len(chars_array):
        break
    # Count coincidences at this displacement
    coincidences = sum(1 for i in range(len(chars_array) - period)
                       if chars_array[i] == chars_array[i + period])
    kappa = coincidences / (len(chars_array) - period)
    print(f"  {period:6d}  {kappa:.6f}  {kappa/IC:.3f}")

# Check for periodicity: if there's a peak at some period, it suggests polyalphabetic
print(f"\n  If IC drops significantly at small periods and peaks at a specific")
print(f"  period, that would indicate polyalphabetic cipher.")


# ============================================================
# 53c: HOMOPHONE DETECTION
# ============================================================
print("\n" + "=" * 65)
print("C: HOMOPHONE DETECTION")
print("=" * 65)

# For each character, compute its successor and predecessor distributions
# Characters with SIMILAR distributions could be homophones
char_succ = defaultdict(Counter)
char_pred = defaultdict(Counter)
for line in line_collapsed:
    text = ' '.join(line)
    for i in range(len(text) - 1):
        c1, c2 = text[i], text[i+1]
        char_succ[c1][c2] += 1
        char_pred[c2][c1] += 1

all_chars_set = sorted(set(c for c in ''.join(all_collapsed)))
print(f"  Alphabet: {len(all_chars_set)} characters")

# Compute pairwise Jensen-Shannon divergence between successor distributions
def js_divergence(p, q, chars):
    """Jensen-Shannon divergence between two distributions."""
    # Normalize
    total_p = sum(p.values()) + len(chars) * 0.5  # Laplace smoothing
    total_q = sum(q.values()) + len(chars) * 0.5
    js = 0.0
    for c in chars:
        pp = (p.get(c, 0) + 0.5) / total_p
        qq = (q.get(c, 0) + 0.5) / total_q
        mm = (pp + qq) / 2
        if pp > 0 and mm > 0:
            js += 0.5 * pp * math.log2(pp / mm)
        if qq > 0 and mm > 0:
            js += 0.5 * qq * math.log2(qq / mm)
    return js

# Only consider characters with enough data
min_count = 200
freq_chars = [c for c in all_chars_set if sum(char_succ[c].values()) >= min_count]
print(f"  Characters with >= {min_count} successor observations: {len(freq_chars)}")
print(f"  Characters: {' '.join(freq_chars)}")

# Compute all pairwise JSD
all_context_chars = set()
for c in freq_chars:
    all_context_chars.update(char_succ[c].keys())
    all_context_chars.update(char_pred[c].keys())

jsd_matrix = {}
for i, c1 in enumerate(freq_chars):
    for c2 in freq_chars[i+1:]:
        jsd = js_divergence(char_succ[c1], char_succ[c2], list(all_context_chars))
        jsd_matrix[(c1, c2)] = jsd

# Find most similar pairs (potential homophones)
sorted_pairs = sorted(jsd_matrix.items(), key=lambda x: x[1])
print(f"\n  Top 10 most similar character pairs (lowest JSD on successors):")
print(f"  {'Pair':>6s}  {'JSD':>8s}  {'Freq1':>6s}  {'Freq2':>6s}  {'Top_succ_1':>20s}  {'Top_succ_2':>20s}")
for (c1, c2), jsd in sorted_pairs[:10]:
    f1 = sum(char_succ[c1].values())
    f2 = sum(char_succ[c2].values())
    ts1 = ', '.join(f"{c}({n})" for c, n in char_succ[c1].most_common(3))
    ts2 = ', '.join(f"{c}({n})" for c, n in char_succ[c2].most_common(3))
    print(f"  {c1}-{c2:>3s}  {jsd:8.4f}  {f1:6d}  {f2:6d}  {ts1:>20s}  {ts2:>20s}")

# Now test: can we MERGE the most similar pairs without increasing entropy?
# Cross-validate: train character bigram on half the data, test on other half
# Compare entropy with and without merger for the top-5 most similar pairs

print(f"\n  Homophone merge test (cross-validated character bigram entropy):")
half = len(line_collapsed) // 2
train_lines = line_collapsed[:half]
test_lines = line_collapsed[half:]

def char_bigram_entropy(lines, merge_map=None):
    """Cross-validated char bigram entropy."""
    bigram = Counter()
    ctx = Counter()
    for line in lines:
        text = ' '.join(line)
        if merge_map:
            text = ''.join(merge_map.get(c, c) for c in text)
        for i in range(len(text) - 1):
            bigram[(text[i], text[i+1])] += 1
            ctx[text[i]] += 1
    # Evaluate on test
    total_lp = 0.0
    n_test = 0
    for line in test_lines:
        text = ' '.join(line)
        if merge_map:
            text = ''.join(merge_map.get(c, c) for c in text)
        for i in range(len(text) - 1):
            c1, c2 = text[i], text[i+1]
            bc = bigram.get((c1, c2), 0)
            cc = ctx.get(c1, 0)
            if bc > 0 and cc > 0:
                total_lp += -math.log2(bc / cc)
            else:
                total_lp += 10.0  # penalty for unseen
            n_test += 1
    return total_lp / n_test if n_test > 0 else 999

baseline_H = char_bigram_entropy(train_lines)
print(f"  Baseline cross-val H(char|prev) = {baseline_H:.4f}")

for (c1, c2), jsd in sorted_pairs[:5]:
    merge_map = {c2: c1}
    merged_H = char_bigram_entropy(train_lines, merge_map)
    delta = merged_H - baseline_H
    print(f"  Merge {c1}+{c2}: H = {merged_H:.4f} (Δ = {delta:+.4f}) "
          f"{'BETTER' if delta < -0.01 else 'WORSE' if delta > 0.01 else 'NEUTRAL'}")


# ============================================================
# 53d: WORD-INTERNAL STRUCTURE TEST
# ============================================================
print("\n" + "=" * 65)
print("D: WORD-INTERNAL STRUCTURE TEST")
print("=" * 65)

# Build character bigram model from the corpus
char_bi = Counter()
char_ctx = Counter()
for w in all_collapsed:
    seq = '^' + w + '$'
    for i in range(len(seq) - 1):
        char_bi[(seq[i], seq[i+1])] += 1
        char_ctx[seq[i]] += 1

# Generate synthetic words from this model
def generate_word_from_bigram():
    """Generate a word from the character bigram model."""
    word = ''
    prev = '^'
    for _ in range(20):  # max length
        # Get successor distribution
        succs = [(c2, n) for (c1, c2), n in char_bi.items() if c1 == prev]
        if not succs:
            break
        chars, counts = zip(*succs)
        total = sum(counts)
        probs = [c/total for c in counts]
        chosen = np.random.choice(list(chars), p=probs)
        if chosen == '$':
            break
        word += chosen
        prev = chosen
    return word if len(word) >= 2 else None

# Generate many synthetic words
n_synthetic = 50000
synthetic_words = []
for _ in range(n_synthetic):
    w = generate_word_from_bigram()
    if w:
        synthetic_words.append(w)

print(f"  Generated {len(synthetic_words)} synthetic words from char bigram model")

# Compare positional entropy: real vs synthetic
max_pos = 8
real_char_at_pos = defaultdict(Counter)
synth_char_at_pos = defaultdict(Counter)
real_total = Counter()
synth_total = Counter()

for w in all_collapsed:
    for i, c in enumerate(w):
        if i < max_pos:
            real_char_at_pos[i][c] += 1
            real_total[i] += 1

for w in synthetic_words:
    for i, c in enumerate(w):
        if i < max_pos:
            synth_char_at_pos[i][c] += 1
            synth_total[i] += 1

print(f"\n  Positional entropy comparison (real VMS vs char-bigram-generated):")
print(f"  {'Pos':>4s}  {'H_real':>7s}  {'H_synth':>8s}  {'Delta':>7s}  {'Note':>10s}")
for pos in range(max_pos):
    if real_total[pos] < 100 or synth_total[pos] < 100:
        break
    H_real = compute_H(real_char_at_pos[pos], real_total[pos])
    H_synth = compute_H(synth_char_at_pos[pos], synth_total[pos])
    delta = H_real - H_synth
    note = 'SAME' if abs(delta) < 0.05 else 'REAL<SYNTH' if delta < 0 else 'REAL>SYNTH'
    print(f"  {pos+1:4d}  {H_real:7.3f}  {H_synth:8.3f}  {delta:+7.3f}  {note:>10s}")

# Also compare word length distributions
real_lengths = Counter(len(w) for w in all_collapsed)
synth_lengths = Counter(len(w) for w in synthetic_words)
real_total_len = sum(real_lengths.values())
synth_total_len = sum(synth_lengths.values())

print(f"\n  Word length distribution comparison:")
print(f"  {'Len':>4s}  {'Real%':>7s}  {'Synth%':>8s}  {'Delta':>7s}")
for length in range(2, 12):
    rp = 100 * real_lengths.get(length, 0) / real_total_len
    sp = 100 * synth_lengths.get(length, 0) / synth_total_len
    if rp > 0.5 or sp > 0.5:
        print(f"  {length:4d}  {rp:6.1f}%  {sp:7.1f}%  {sp-rp:+6.1f}%")

real_mean_len = np.mean([len(w) for w in all_collapsed])
synth_mean_len = np.mean([len(w) for w in synthetic_words])
print(f"  Mean length: real={real_mean_len:.2f}, synth={synth_mean_len:.2f}")

# Chi-square test: do length distributions differ?
max_len = 12
obs = [real_lengths.get(l, 0) for l in range(2, max_len)]
# Scale synthetic to match real total
scale = real_total_len / synth_total_len
exp = [synth_lengths.get(l, 0) * scale for l in range(2, max_len)]
chi2 = sum((o - e)**2 / max(e, 1) for o, e in zip(obs, exp))
print(f"  Chi-square (length distribution) = {chi2:.1f} (df={max_len-3})")
print(f"  {'DIFFERENT' if chi2 > 20 else 'SIMILAR'} length distributions")


# ============================================================
# 53e: WORD BOUNDARY INFORMATION
# ============================================================
print("\n" + "=" * 65)
print("E: WORD BOUNDARY INFORMATION")
print("=" * 65)

# Test: does knowing word boundaries help predict characters?
# Model 1: Character bigram ignoring word boundaries (stream model)
# Model 2: Character bigram with word boundaries ('^' and '$' markers)
# If word boundaries carry information, Model 2 should be better.

# Build stream model (no boundaries)
stream_bi = Counter()
stream_ctx = Counter()
for line in line_collapsed:
    text = ''.join(line)  # No spaces
    for i in range(len(text) - 1):
        stream_bi[(text[i], text[i+1])] += 1
        stream_ctx[text[i]] += 1

# Build boundary model (with ^ and $ markers)
bound_bi = Counter()
bound_ctx = Counter()
for line in line_collapsed:
    for w in line:
        seq = '^' + w + '$'
        for i in range(len(seq) - 1):
            bound_bi[(seq[i], seq[i+1])] += 1
            bound_ctx[seq[i]] += 1

# Cross-validate: train on first half, test on second half
train = line_collapsed[:len(line_collapsed)//2]
test = line_collapsed[len(line_collapsed)//2:]

# Train stream model
s_bi = Counter()
s_ctx = Counter()
for line in train:
    text = ''.join(line)
    for i in range(len(text) - 1):
        s_bi[(text[i], text[i+1])] += 1
        s_ctx[text[i]] += 1

# Train boundary model
b_bi = Counter()
b_ctx = Counter()
for line in train:
    for w in line:
        seq = '^' + w + '$'
        for i in range(len(seq) - 1):
            b_bi[(seq[i], seq[i+1])] += 1
            b_ctx[seq[i]] += 1

# Test stream model
stream_total_lp = 0.0
stream_n = 0
for line in test:
    text = ''.join(line)
    for i in range(len(text) - 1):
        c1, c2 = text[i], text[i+1]
        bc = s_bi.get((c1, c2), 0)
        cc = s_ctx.get(c1, 0)
        if bc > 0 and cc > 0:
            stream_total_lp += -math.log2(bc / cc)
        else:
            stream_total_lp += 10.0
        stream_n += 1

# Test boundary model — evaluate per character WITHIN words
bound_total_lp = 0.0
bound_n = 0
for line in test:
    for w in line:
        seq = '^' + w + '$'
        for i in range(len(seq) - 1):
            c1, c2 = seq[i], seq[i+1]
            if c2 in ('^', '$'):
                continue  # don't count boundary predictions
            bc = b_bi.get((c1, c2), 0)
            cc = b_ctx.get(c1, 0)
            if bc > 0 and cc > 0:
                bound_total_lp += -math.log2(bc / cc)
            else:
                bound_total_lp += 10.0
            bound_n += 1

stream_H = stream_total_lp / stream_n if stream_n > 0 else 999
bound_H = bound_total_lp / bound_n if bound_n > 0 else 999

print(f"  Stream model (no word boundaries): H = {stream_H:.4f} bits/char")
print(f"  Boundary model (with '^' and '$'): H = {bound_H:.4f} bits/char")
print(f"  Improvement from word boundaries:  {stream_H - bound_H:+.4f} bits/char")
print(f"  Relative improvement:              {100*(stream_H - bound_H)/stream_H:+.1f}%")

# How much of this is from word-initial prediction?
# Test: boundary model improvement at position 1 vs later positions
pos1_stream_lp = 0.0
pos1_stream_n = 0
pos1_bound_lp = 0.0
pos1_bound_n = 0
later_stream_lp = 0.0
later_stream_n = 0
later_bound_lp = 0.0
later_bound_n = 0

for line in test:
    text = ''.join(line)
    word_starts = set()
    pos = 0
    for w in line:
        word_starts.add(pos)
        pos += len(w)
    
    for i in range(len(text) - 1):
        c1, c2 = text[i], text[i+1]
        bc = s_bi.get((c1, c2), 0)
        cc = s_ctx.get(c1, 0)
        lp = -math.log2(bc / cc) if bc > 0 and cc > 0 else 10.0
        if (i+1) in word_starts:  # this is a word-initial character
            pos1_stream_lp += lp
            pos1_stream_n += 1
        else:
            later_stream_lp += lp
            later_stream_n += 1

    for w in line:
        seq = '^' + w + '$'
        for j in range(1, len(seq) - 1):  # skip ^ and $
            c1, c2 = seq[j-1], seq[j]
            if c1 == '^':
                # Word-initial
                bc = b_bi.get(('^', c2), 0)
                cc = b_ctx.get('^', 0)
                lp = -math.log2(bc / cc) if bc > 0 and cc > 0 else 10.0
                pos1_bound_lp += lp
                pos1_bound_n += 1
            else:
                bc = b_bi.get((c1, c2), 0)
                cc = b_ctx.get(c1, 0)
                lp = -math.log2(bc / cc) if bc > 0 and cc > 0 else 10.0
                later_bound_lp += lp
                later_bound_n += 1

if pos1_stream_n > 0 and pos1_bound_n > 0:
    print(f"\n  Word-initial characters:")
    print(f"    Stream: {pos1_stream_lp/pos1_stream_n:.3f} bits/char ({pos1_stream_n} chars)")
    print(f"    Boundary: {pos1_bound_lp/pos1_bound_n:.3f} bits/char ({pos1_bound_n} chars)")
    print(f"    Improvement: {pos1_stream_lp/pos1_stream_n - pos1_bound_lp/pos1_bound_n:+.3f}")
if later_stream_n > 0 and later_bound_n > 0:
    print(f"  Later characters:")
    print(f"    Stream: {later_stream_lp/later_stream_n:.3f} bits/char ({later_stream_n} chars)")
    print(f"    Boundary: {later_bound_lp/later_bound_n:.3f} bits/char ({later_bound_n} chars)")
    print(f"    Improvement: {later_stream_lp/later_stream_n - later_bound_lp/later_bound_n:+.3f}")


# ============================================================
# SYNTHESIS
# ============================================================
print("\n" + "=" * 65)
print("cipher_identification_tests SYNTHESIS")
print("=" * 65)
print("""
Summary of cipher identification tests:

53a: Is word-level MI compatible with verbose/syllable cipher?
53b: Does IC match known languages or show polyalphabetic cycling?
53c: Are there character pairs that could be merged (homophones)?
53d: Does the char bigram model fully explain word internal structure?
53e: Do word boundaries carry information beyond character streams?

Together these tests constrain what kind of system could produce VMS.
""")

print(f"\ncipher_identification_tests complete.")
