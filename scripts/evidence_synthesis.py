#!/usr/bin/env python3
"""
GRAND SYNTHESIS: WHAT IS VOYNICHESE?
=================================================

A full battery of statistical analyses behind us. Time to ask: what kind of system
produces these exact statistical properties?

This test:
  A) GENERATIVE MODEL — Build the simplest model that reproduces
       the observed statistics. How well does it match?

  B) TYPOLOGICAL PROFILE — Measure properties that distinguish
       language types (alphabetic, syllabary, logographic, constructed).

  C) ENTROPY RATE — What is the true character-level entropy of VMS
       and how does it compare to known scripts?

  D) INFORMATION DENSITY — How many bits per word? Per line?
       Does VMS carry information at natural-language rates?

  E) THE VOYNICH FINGERPRINT — A compact statistical fingerprint
       of the manuscript that can be compared against any hypothesis.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_H, get_collapsed, get_gram_prefix, get_suffix, load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(50)
np.random.seed(50)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']
GRAM_PREFIXES = ['qo','so','do','q','o','d','y']




FOLIO_DIR = Path("folios")



print("Loading lines...")
lines = load_lines()

line_collapsed = []
all_collapsed = []
all_raw = []
for line in lines:
    coll = [get_collapsed(w) for w in line['words']]
    line_collapsed.append(coll)
    all_collapsed.extend(coll)
    all_raw.extend(line['words'])

word_counts = Counter(all_collapsed)
N = len(all_collapsed)
V = len(word_counts)
print(f"  {len(lines)} lines, {N} tokens, {V} types")


# ══════════════════════════════════════════════════════════════════
# 50a: GENERATIVE MODEL
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("A: GENERATIVE MODEL")
print("    Build the simplest model that reproduces observed statistics")
print("=" * 70)

# Model 1: Unigram (word frequencies only)
H_unigram = compute_H(word_counts, N)
print(f"\n  Model 1: UNIGRAM")
print(f"  H = {H_unigram:.3f} bits/word")
print(f"  PP = {2**H_unigram:.0f}")

# Model 2: Suffix + Prefix independent marginals, stem|suffix
# This generates a word by: pick suffix (from marginal), pick prefix (from marginal),
# pick stem (from stem|suffix distribution)
sfx_counts = Counter()
gpfx_counts = Counter()
stem_given_sfx = defaultdict(Counter)

for w in all_collapsed:
    sfx = get_suffix(w)
    gpfx = get_gram_prefix(w)
    # "stem" = what's left after removing prefix and suffix
    temp = w
    for gp in GRAM_PREFIXES:
        if temp.startswith(gp) and len(temp) > len(gp):
            temp = temp[len(gp):]
            break
    for sx in SUFFIXES:
        if temp.endswith(sx) and len(temp) > len(sx):
            temp = temp[:-len(sx)]
            break
    sfx_counts[sfx] += 1
    gpfx_counts[gpfx] += 1
    stem_given_sfx[sfx][temp] += 1

H_sfx = compute_H(sfx_counts, N)
H_gpfx = compute_H(gpfx_counts, N)
H_stem_given_sfx = 0.0
for sfx, stems in stem_given_sfx.items():
    n = sfx_counts[sfx]
    h = compute_H(stems, n)
    H_stem_given_sfx += (n / N) * h

H_model2 = H_sfx + H_gpfx + H_stem_given_sfx
print(f"\n  Model 2: INDEPENDENT FEATURES")
print(f"  H(suffix) = {H_sfx:.3f}")
print(f"  H(prefix) = {H_gpfx:.3f}")
print(f"  H(stem|suffix) = {H_stem_given_sfx:.3f}")
print(f"  Total H = {H_model2:.3f} bits/word")
print(f"  PP = {2**H_model2:.0f}")
print(f"  vs unigram: {H_model2 - H_unigram:.3f} bits overhead")

# Model 3: Suffix→prefix bigram + stem|suffix
# Uses real sfx→gpfx transition probabilities for adjacent words
sfx_gpfx_bg = Counter()
sfx_bg_total = Counter()
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        sfx_i = get_suffix(seq[i])
        gpfx_j = get_gram_prefix(seq[i+1])
        sfx_gpfx_bg[(sfx_i, gpfx_j)] += 1
        sfx_bg_total[sfx_i] += 1

H_gpfx_given_sfx = 0.0
for sfx, n in sfx_bg_total.items():
    succs = Counter()
    for (s, g), c in sfx_gpfx_bg.items():
        if s == sfx:
            succs[g] += c
    h = compute_H(succs, n)
    H_gpfx_given_sfx += (n / sum(sfx_bg_total.values())) * h

H_model3 = H_sfx + H_gpfx_given_sfx + H_stem_given_sfx
MI_sfx_gpfx = H_gpfx - H_gpfx_given_sfx
print(f"\n  Model 3: SUFFIX→PREFIX BIGRAM + stem|suffix")
print(f"  H(prefix|prev_suffix) = {H_gpfx_given_sfx:.3f}")
print(f"  MI(sfx→gpfx) = {MI_sfx_gpfx:.3f}")
print(f"  Total H = {H_model3:.3f} bits/word")
print(f"  PP = {2**H_model3:.0f}")
print(f"  vs unigram: {H_model3 - H_unigram:.3f} bits overhead")
print(f"  vs independent: {H_model3 - H_model2:.3f} bits saved")

# Model 4: Full observed word bigram (non-generalizable, in-sample only)
# (just for comparison — we know this overfits)
bg_counts = Counter()
bg_ctx = Counter()
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        bg_counts[(seq[i], seq[i+1])] += 1
        bg_ctx[seq[i]] += 1

H_bigram = 0.0
for w, n in bg_ctx.items():
    succs = Counter()
    for (w1, w2), c in bg_counts.items():
        if w1 == w:
            succs[w2] += c
    h = compute_H(succs, n)
    H_bigram += (n / sum(bg_ctx.values())) * h

print(f"\n  Model 4: FULL WORD BIGRAM (in-sample, overfits)")
print(f"  H = {H_bigram:.3f} bits/word")
print(f"  PP = {2**H_bigram:.0f}")
print(f"  Unigram reduction: {(1 - H_bigram/H_unigram)*100:.1f}%")
print(f"  NOTE: Does NOT generalize (structure_cross_validation)")

# Now: generate text from Model 3 and compare statistics
print(f"\n  --- GENERATING TEXT FROM MODEL 3 ---")

# Build transition tables
sfx_dist = {sfx: c/N for sfx, c in sfx_counts.items()}
sfx_to_gpfx_dist = {}
for sfx in sfx_bg_total:
    succs = {}
    for (s, g), c in sfx_gpfx_bg.items():
        if s == sfx:
            succs[g] = c / sfx_bg_total[s]
    sfx_to_gpfx_dist[sfx] = succs

# For line-initial words, use marginal gpfx distribution
gpfx_dist = {gpfx: c/N for gpfx, c in gpfx_counts.items()}

# Build stem|suffix and suffix distributions
stem_sfx_dist = {}
for sfx, stems in stem_given_sfx.items():
    total = sum(stems.values())
    stem_sfx_dist[sfx] = {s: c/total for s, c in stems.items()}

def sample_from(dist):
    keys = list(dist.keys())
    probs = [dist[k] for k in keys]
    return keys[np.random.choice(len(keys), p=probs)]

# Generate 1000 lines with similar length distribution
line_lengths = [len(seq) for seq in line_collapsed]
gen_lines = []
gen_words = []
for _ in range(1000):
    length = random.choice(line_lengths)
    line = []
    prev_sfx = None
    for pos in range(length):
        # Pick suffix
        sfx = sample_from(sfx_dist)
        
        # Pick prefix: if prev word exists, use transition; else marginal
        if prev_sfx is not None and prev_sfx in sfx_to_gpfx_dist:
            gpfx = sample_from(sfx_to_gpfx_dist[prev_sfx])
        else:
            gpfx = sample_from(gpfx_dist)
        
        # Pick stem
        if sfx in stem_sfx_dist:
            stem = sample_from(stem_sfx_dist[sfx])
        else:
            stem = 'e'
        
        # Assemble word
        word = (gpfx if gpfx != 'X' else '') + stem + (sfx if sfx != 'X' else '')
        line.append(word)
        prev_sfx = sfx
    gen_lines.append(line)
    gen_words.extend(line)

# Compare statistics
gen_counts = Counter(gen_words)
gen_N = len(gen_words)
gen_V = len(gen_counts)
gen_H = compute_H(gen_counts, gen_N)
gen_hapax = sum(1 for c in gen_counts.values() if c == 1)

print(f"\n  Real vs Generated (Model 3, 1000 lines):")
hapax_real = sum(1 for c in word_counts.values() if c == 1)
print(f"  {'Metric':>25} {'Real':>12} {'Generated':>12}")
print(f"  {'Tokens':>25} {N:>12} {gen_N:>12}")
print(f"  {'Types':>25} {V:>12} {gen_V:>12}")
print(f"  {'Type-token ratio':>25} {V/N:>12.4f} {gen_V/gen_N:>12.4f}")
print(f"  {'H(word)':>25} {H_unigram:>12.3f} {gen_H:>12.3f}")
print(f"  {'Hapax %':>25} {hapax_real/V*100:>11.1f}% {gen_hapax/gen_V*100:>11.1f}%")

# Self-repetition rate
real_selfrep = sum(1 for seq in line_collapsed for i in range(len(seq)-1)
                   if seq[i] == seq[i+1])
gen_selfrep = sum(1 for seq in gen_lines for i in range(len(seq)-1)
                  if seq[i] == seq[i+1])
real_pairs = sum(len(seq)-1 for seq in line_collapsed)
gen_pairs = sum(len(seq)-1 for seq in gen_lines)
print(f"  {'Self-rep rate':>25} {real_selfrep/real_pairs*100:>11.1f}% {gen_selfrep/gen_pairs*100:>11.1f}%")

# Zipf exponent
top_real = sorted(word_counts.values(), reverse=True)[:200]
top_gen = sorted(gen_counts.values(), reverse=True)[:200]
ranks = np.arange(1, 201)

from numpy.polynomial import polynomial as P
def fit_zipf(freqs, ranks):
    log_r = np.log10(ranks[:len(freqs)])
    log_f = np.log10(freqs)
    coeffs = np.polyfit(log_r, log_f, 1)
    return -coeffs[0]

zipf_real = fit_zipf(np.array(top_real[:200]), ranks)
zipf_gen = fit_zipf(np.array(top_gen[:min(200, len(top_gen))]), ranks[:min(200, len(top_gen))])
print(f"  {'Zipf exponent':>25} {zipf_real:>12.3f} {zipf_gen:>12.3f}")


# ══════════════════════════════════════════════════════════════════
# 50b: TYPOLOGICAL PROFILE
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("B: TYPOLOGICAL PROFILE")
print("    Properties that distinguish language/script types")
print("=" * 70)

# Key typological measurements
# 1. Character inventory size
char_counts = Counter()
for w in all_raw:
    for c in w:
        char_counts[c] += 1
n_chars = len(char_counts)
total_chars = sum(char_counts.values())
print(f"\n  CHARACTER INVENTORY:")
print(f"  Distinct characters: {n_chars}")
print(f"  Total characters: {total_chars}")
print(f"  H(char): {compute_H(char_counts, total_chars):.3f} bits")
print(f"  Most common: {', '.join(f'{c}({n})' for c, n in char_counts.most_common(10))}")

# 2. Word length distribution
wlens = [len(w) for w in all_collapsed]
print(f"\n  WORD LENGTH DISTRIBUTION:")
print(f"  Mean: {np.mean(wlens):.2f}")
print(f"  Median: {np.median(wlens):.1f}")
print(f"  Std: {np.std(wlens):.2f}")
print(f"  Range: {min(wlens)}-{max(wlens)}")
wlen_counts = Counter(wlens)
for l in sorted(wlen_counts.keys()):
    if wlen_counts[l] > 50:
        print(f"    len={l}: {wlen_counts[l]:>5} ({wlen_counts[l]/N*100:.1f}%)")

# 3. Line length distribution (words per line)
llen = [len(seq) for seq in line_collapsed]
print(f"\n  LINE LENGTH DISTRIBUTION:")
print(f"  Mean: {np.mean(llen):.2f} words/line")
print(f"  Median: {np.median(llen):.1f}")
print(f"  Std: {np.std(llen):.2f}")

# 4. Morphological regularity: what % of vocabulary is analyzable?
n_analyzable = 0
n_has_suffix = 0
n_has_prefix = 0
for w in word_counts:
    sfx = get_suffix(w)
    gpfx = get_gram_prefix(w)
    has_sfx = sfx != 'X'
    has_pfx = gpfx != 'X'
    if has_sfx or has_pfx:
        n_analyzable += 1
    if has_sfx:
        n_has_suffix += 1
    if has_pfx:
        n_has_prefix += 1

print(f"\n  MORPHOLOGICAL REGULARITY (types):")
print(f"  Analyzable (has sfx or pfx): {n_analyzable}/{V} = {n_analyzable/V*100:.1f}%")
print(f"  Has suffix: {n_has_suffix}/{V} = {n_has_suffix/V*100:.1f}%")
print(f"  Has prefix: {n_has_prefix}/{V} = {n_has_prefix/V*100:.1f}%")

# By tokens
n_tok_sfx = sum(c for w, c in word_counts.items() if get_suffix(w) != 'X')
n_tok_pfx = sum(c for w, c in word_counts.items() if get_gram_prefix(w) != 'X')
n_tok_either = sum(c for w, c in word_counts.items() if get_suffix(w) != 'X' or get_gram_prefix(w) != 'X')
print(f"\n  MORPHOLOGICAL REGULARITY (tokens):")
print(f"  Analyzable: {n_tok_either}/{N} = {n_tok_either/N*100:.1f}%")
print(f"  Has suffix: {n_tok_sfx}/{N} = {n_tok_sfx/N*100:.1f}%")
print(f"  Has prefix: {n_tok_pfx}/{N} = {n_tok_pfx/N*100:.1f}%")

# 5. Conditional entropy chain: H(c_n | c_{n-1}, ..., c_1)
# Character-level entropy rate
all_char_text = ' '.join(all_collapsed)
chars_only = [c for c in all_char_text]

# Bigram character entropy
char_bg = Counter()
char_uni = Counter()
for i in range(len(chars_only) - 1):
    char_bg[(chars_only[i], chars_only[i+1])] += 1
    char_uni[chars_only[i]] += 1
char_uni[chars_only[-1]] += 1

H_char_uni = compute_H(char_uni, len(chars_only))

H_char_cond = 0.0
for c1, n1 in char_uni.items():
    succs = Counter()
    for (a, b), cnt in char_bg.items():
        if a == c1:
            succs[b] += cnt
    if sum(succs.values()) > 0:
        h = compute_H(succs, sum(succs.values()))
        H_char_cond += (n1 / len(chars_only)) * h

# Trigram
char_tri = Counter()
char_bi_ctx = Counter()
for i in range(len(chars_only) - 2):
    char_tri[(chars_only[i], chars_only[i+1], chars_only[i+2])] += 1
    char_bi_ctx[(chars_only[i], chars_only[i+1])] += 1

H_char_tri_cond = 0.0
total_bi = sum(char_bi_ctx.values())
for (c1, c2), n_bi in char_bi_ctx.items():
    succs = Counter()
    for (a, b, c), cnt in char_tri.items():
        if a == c1 and b == c2:
            succs[c] += cnt
    if sum(succs.values()) > 0:
        h = compute_H(succs, sum(succs.values()))
        H_char_tri_cond += (n_bi / total_bi) * h


# ══════════════════════════════════════════════════════════════════
# 50c: ENTROPY RATE
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("C: ENTROPY RATE")
print("    True information rate of VMS vs known scripts")
print("=" * 70)

mean_wlen = np.mean(wlens)
bits_per_char_uni = H_char_uni
bits_per_char_bi = H_char_cond
bits_per_char_tri = H_char_tri_cond

print(f"\n  Character-level entropy:")
print(f"  H(char) unigram:  {bits_per_char_uni:.3f} bits/char")
print(f"  H(char|prev 1):   {bits_per_char_bi:.3f} bits/char")
print(f"  H(char|prev 2):   {bits_per_char_tri:.3f} bits/char")
print(f"  Mean word length:  {mean_wlen:.2f} chars")

bits_per_word_char_bi = bits_per_char_bi * mean_wlen
print(f"\n  Implied bits/word (from char bigram): {bits_per_word_char_bi:.2f}")
print(f"  Actual word entropy H(word):           {H_unigram:.2f}")
print(f"  Ratio (word/char-implied):             {H_unigram / bits_per_word_char_bi:.3f}")

# Information per line
mean_words_per_line = np.mean(llen)
mean_chars_per_line = np.mean([sum(len(w) for w in seq) for seq in line_collapsed])
bits_per_line = H_unigram * mean_words_per_line
print(f"\n  Information per line:")
print(f"  Mean words/line:   {mean_words_per_line:.2f}")
print(f"  Mean chars/line:   {mean_chars_per_line:.1f}")
print(f"  Bits/line (word):  {bits_per_line:.1f}")

# Compare with known systems
print(f"\n  COMPARISON WITH KNOWN SYSTEMS:")
print(f"  {'System':>20} {'Chars':>8} {'H(char)':>8} {'H(c|c)':>8} {'Mean wlen':>10} {'H(word)':>8}")
print(f"  {'Voynichese':>20} {n_chars:>8} {bits_per_char_uni:>8.2f} {bits_per_char_bi:>8.2f} {mean_wlen:>10.2f} {H_unigram:>8.2f}")
print(f"  {'English (typ.)':>20} {'26':>8} {'4.07':>8} {'3.30':>8} {'4.7':>10} {'~11':>8}")
print(f"  {'Latin (typ.)':>20} {'23':>8} {'4.01':>8} {'3.20':>8} {'5.5':>10} {'~12':>8}")
print(f"  {'Arabic (typ.)':>20} {'28':>8} {'4.17':>8} {'3.10':>8} {'4.3':>10} {'~11':>8}")
print(f"  {'Chinese (typ.)':>20} {'>3000':>8} {'~11':>8} {'~8':>8} {'1.5':>10} {'~11':>8}")
print(f"  {'Constructed':>20} {'var':>8} {'var':>8} {'close':>8} {'var':>10} {'var':>8}")


# ══════════════════════════════════════════════════════════════════
# 50d: INFORMATION DENSITY ANALYSIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("D: INFORMATION DENSITY")
print("    How much information does VMS actually encode?")
print("=" * 70)

# The key question: VMS has ~35K words. How much INFORMATION is that?
total_info_bits = H_unigram * N
total_info_chars = bits_per_char_bi * total_chars
print(f"\n  Total corpus information content:")
print(f"  Word-level:  {total_info_bits:.0f} bits = {total_info_bits/8:.0f} bytes")
print(f"  Char-level:  {total_info_chars:.0f} bits = {total_info_chars/8:.0f} bytes")

# English equivalent
# English has ~1 bit/char after accounting for redundancy (Shannon's estimate)
# With ~5 chars/word, that's ~5 bits/word of actual information
# VMS has H≈9.6 bits/word but how much of that is morphological redundancy?
morph_redundancy = 1 - (H_model3 / H_unigram) if H_model3 < H_unigram else 0
print(f"\n  Morphological redundancy: {morph_redundancy*100:.1f}%")

# True information after removing morphological structure
true_info = H_unigram - MI_sfx_gpfx  # remove the predictable part
print(f"  H(word) after syntax removal: {true_info:.3f} bits")
print(f"  Total non-redundant info: {true_info * N:.0f} bits = {true_info * N / 8:.0f} bytes")

# Compare: a typical English page
# ~250 words/page × ~10 bits/word (Shannon) × 50% redundancy = ~1250 bits/page
# English book of equivalent length: ~35K words × ~5 bits/word = ~175K bits
eng_equivalent = 35000 * 5
vms_total = true_info * N
print(f"\n  English equivalent (35K words × 5 bits/word): {eng_equivalent:.0f} bits")
print(f"  VMS content: {vms_total:.0f} bits")
print(f"  Ratio VMS/English: {vms_total/eng_equivalent:.2f}")

# Section comparison
print(f"\n  Information density by section:")
for section in sorted(set(line['section'] for line in lines)):
    sec_words = []
    for line in lines:
        if line['section'] == section:
            for w in line['words']:
                sec_words.append(get_collapsed(w))
    if len(sec_words) < 100:
        continue
    sec_counts = Counter(sec_words)
    sec_H = compute_H(sec_counts, len(sec_words))
    sec_V = len(sec_counts)
    sec_TTR = sec_V / len(sec_words)
    print(f"  {section:>12}: N={len(sec_words):>5}, V={sec_V:>5}, H={sec_H:.3f}, TTR={sec_TTR:.3f}")


# ══════════════════════════════════════════════════════════════════
# 50e: THE VOYNICH FINGERPRINT
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("E: THE VOYNICH FINGERPRINT")
print("    A compact statistical profile of the manuscript")
print("=" * 70)

# Collect all key statistics into one fingerprint
print(f"""
  ╔══════════════════════════════════════════════════════════════╗
  ║              THE VOYNICH STATISTICAL FINGERPRINT            ║
  ╠══════════════════════════════════════════════════════════════╣
  ║ CORPUS SIZE                                                 ║
  ║   Tokens:              {N:>10}                              ║
  ║   Types:               {V:>10}                              ║
  ║   Lines (2+ words):    {len(lines):>10}                              ║
  ║   Characters:          {total_chars:>10}                              ║
  ╠══════════════════════════════════════════════════════════════╣
  ║ CHARACTER LEVEL                                             ║
  ║   Alphabet size:       {n_chars:>10}                              ║
  ║   H(char):             {bits_per_char_uni:>10.3f} bits                      ║
  ║   H(char|prev):        {bits_per_char_bi:>10.3f} bits                      ║
  ║   H(char|prev2):       {bits_per_char_tri:>10.3f} bits                      ║
  ╠══════════════════════════════════════════════════════════════╣
  ║ WORD LEVEL                                                  ║
  ║   H(word):             {H_unigram:>10.3f} bits                      ║
  ║   Mean word length:    {mean_wlen:>10.2f} chars                     ║
  ║   Zipf exponent:       {zipf_real:>10.3f}                            ║
  ║   Hapax ratio:         {hapax_real/V*100:>9.1f}%                            ║
  ║   Type-token ratio:    {V/N:>10.4f}                            ║
  ╠══════════════════════════════════════════════════════════════╣
  ║ MORPHOLOGICAL GRAMMAR                                       ║
  ║   Suffixes:            {len(SUFFIXES):>10} types                         ║
  ║   Gram prefixes:       {len(GRAM_PREFIXES):>10} types                         ║
  ║   MI(sfx→gpfx):        {MI_sfx_gpfx:>10.4f} bits (cross-val 94.7%)   ║
  ║   Suffix entropy:      {H_sfx:>10.3f} bits                      ║
  ║   Prefix entropy:      {H_gpfx:>10.3f} bits                      ║
  ║   Direction:            {'L→R (suffix predicts next prefix)':>40} ║
  ║   Asymmetry:            {'Feature-level only, not word-level':>40} ║
  ╠══════════════════════════════════════════════════════════════╣
  ║ SYNTAX                                                      ║
  ║   Syntactic unit:       {'LINE (grammar resets at boundaries)':>40} ║
  ║   Words/line:          {mean_words_per_line:>10.2f}                            ║
  ║   Syntax range:         {'Adjacent words only (gap 1)':>40} ║
  ║   Dominant transition:  {'suffix -dy → prefix qo- (36% of MI)':>40} ║
  ║   Line-initial:         {'d-prefix enriched 2.5×':>40} ║
  ║   Word bigrams:         {'Do NOT generalize (too sparse)':>40} ║
  ╠══════════════════════════════════════════════════════════════╣
  ║ DISTRIBUTIONAL CLASSES                                      ║
  ║   Discrete classes:     {'NO — continuous gradient':>40} ║
  ║   Suffix classes (k=3): {'A={{dy,y}}, M={{X,ar,in}}, B={{aiin,...}}':>40} ║
  ║   Class MI contribution:{'9.6% of info (minor overlay)':>40} ║
  ╠══════════════════════════════════════════════════════════════╣
  ║ WHAT THIS RULES OUT                                         ║
  ║   Random/meaningless:   {'NO — z>100 morphology, z>80 syntax':>40} ║
  ║   Simple cipher:        {'UNLIKELY — morphology too complex':>40} ║
  ║   Constructed lang:     {'UNLIKELY — sparse word bigrams':>40} ║
  ║   Logographic:          {'NO — alphabet too small (18-23)':>40} ║
  ╚══════════════════════════════════════════════════════════════╝
""")

# What CAN'T we determine computationally?
print("  WHAT COMPUTATIONAL ANALYSIS CANNOT DETERMINE:")
print("  ─────────────────────────────────────────────")
print("  1. What the PHONETIC values of glyphs are")
print("  2. What LANGUAGE is being written (if any)")
print("  3. Whether the morphology encodes MEANING or is decorative")
print("  4. Whether the content is natural text, a cipher, or a code")
print("  5. Specific word translations")
print()
print("  WHAT THE SUITE HAS ESTABLISHED:")
print("  ──────────────────────────────────")
print("  1. The writing system has genuine morphological structure (not random)")
print("  2. The structure is CONSISTENT with a natural agglutinative language")
print("  3. Grammar operates at the morpheme level (suffix→prefix), not word level")
print("  4. Lines are independent syntactic units (sentence-like)")
print("  5. The system is head-initial at morpheme level (like VSO/VOS languages)")
print("  6. Word-specific syntax exists but is too sparse for a 35K corpus to model")
print("  7. The statistical profile EXCLUDES random noise, simple ciphers,")
print("     and most constructed-language models")
print("  8. It is CONSISTENT WITH (but does not prove) a natural language")
print("     written in an agglutinative script with ~20 characters")

print("\n" + "=" * 70)
print("evidence_synthesis COMPLETE — GRAND SYNTHESIS")
print("=" * 70)
