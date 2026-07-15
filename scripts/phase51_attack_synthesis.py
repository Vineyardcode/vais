#!/usr/bin/env python3
"""
Phase 51 — ATTACKING THE SYNTHESIS
====================================

Phase 50 declared "diminishing returns" and wrote a synthesis. 
Phase 51 asks: IS THE SYNTHESIS WRONG?

Five skeptical attacks on our own conclusions:

  51a) IS MORPHOLOGICAL MI JUST CHARACTER MI?
       Suffix→prefix MI (z=116.7) might be entirely explained by
       last_char→first_char transitions. If so, "morphological grammar"
       is a fancy name for character patterns.

  51b) IS LOW H(char|prev) A TRANSCRIPTION ARTIFACT?
       EVA compound glyphs (ch, sh, etc.) might artificially lower
       character entropy. Recompute at the GLYPH level.

  51c) CAN WE ACTUALLY EXCLUDE CONSTRUCTED LANGUAGE?
       Sparse word bigrams happen with ANY 3K vocabulary in 35K tokens.
       Generate text from known constructed-language-like models and 
       compare sparsity.

  51d) THE COMPOSITIONALITY TEST
       If words = prefix+stem+suffix, we should be able to predict
       NOVEL words from seen parts. Can we? Or is the vocabulary
       a closed lexicon that just LOOKS morphological?

  51e) COMPARISON TO TABLE/ALGORITHM-GENERATED TEXT
       Rugg (2004) proposed VMS was made with a Cardan grille.
       Generate grille-like text and compare statistics.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_H, get_collapsed, get_gram_prefix, get_suffix, load_lines_v2 as load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(51)
np.random.seed(51)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']
GRAM_PREFIXES = ['qo','so','do','q','o','d','y']




FOLIO_DIR = Path("folios")



print("Loading lines...")
raw_lines = load_lines()
line_collapsed = [[get_collapsed(w) for w in line] for line in raw_lines]
all_collapsed = [w for seq in line_collapsed for w in seq]
all_raw = [w for line in raw_lines for w in line]
N = len(all_collapsed)
V = len(set(all_collapsed))
print(f"  {len(raw_lines)} lines, {N} tokens, {V} types")


# ══════════════════════════════════════════════════════════════════
# 51a: IS MORPHOLOGICAL MI JUST CHARACTER MI?
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("51a: IS MORPHOLOGICAL MI JUST CHARACTER MI?")
print("    Does suffix→prefix MI survive after controlling for")
print("    last_char→first_char?")
print("=" * 70)

# Strategy: Compute MI(suffix_i, prefix_{i+1} | last_char_i, first_char_{i+1})
# If this conditional MI ≈ 0, then morphological MI is entirely explained
# by character-level transitions.

# Collect all transitions with their character-level controls
transitions = []
for seq in line_collapsed:
    for i in range(len(seq) - 1):
        w1, w2 = seq[i], seq[i+1]
        sfx = get_suffix(w1)
        gpfx = get_gram_prefix(w2)
        lc = w1[-1] if w1 else '?'
        fc = w2[0] if w2 else '?'
        transitions.append((sfx, gpfx, lc, fc))

n_trans = len(transitions)

# MI(sfx, gpfx) unconditional
sfx_gpfx = Counter((t[0], t[1]) for t in transitions)
sfx_marg = Counter(t[0] for t in transitions)
gpfx_marg = Counter(t[1] for t in transitions)

mi_morph = 0.0
for (sfx, gpfx), c in sfx_gpfx.items():
    p_j = c / n_trans
    p_sfx = sfx_marg[sfx] / n_trans
    p_gpfx = gpfx_marg[gpfx] / n_trans
    if p_sfx > 0 and p_gpfx > 0:
        mi_morph += p_j * math.log2(p_j / (p_sfx * p_gpfx))

# MI(last_char, first_char) unconditional
lc_fc = Counter((t[2], t[3]) for t in transitions)
lc_marg = Counter(t[2] for t in transitions)
fc_marg = Counter(t[3] for t in transitions)

mi_char = 0.0
for (lc, fc), c in lc_fc.items():
    p_j = c / n_trans
    p_lc = lc_marg[lc] / n_trans
    p_fc = fc_marg[fc] / n_trans
    if p_lc > 0 and p_fc > 0:
        mi_char += p_j * math.log2(p_j / (p_lc * p_fc))

print(f"\n  MI(suffix, next_prefix) = {mi_morph:.4f} bits")
print(f"  MI(last_char, first_char) = {mi_char:.4f} bits")

# Now: MI(sfx, gpfx | lc, fc) = H(sfx, gpfx | lc, fc) - H(sfx|lc,fc) - H(gpfx|lc,fc) + ...
# Easier: compute MI(sfx, gpfx) within each (lc, fc) stratum, then average
# Conditional MI = sum over (lc,fc) of p(lc,fc) * MI(sfx,gpfx | lc,fc)

strata = defaultdict(list)
for t in transitions:
    strata[(t[2], t[3])].append((t[0], t[1]))

cond_mi = 0.0
for (lc, fc), pairs in strata.items():
    n_s = len(pairs)
    p_stratum = n_s / n_trans
    
    # MI(sfx, gpfx) within this stratum
    sfx_c = Counter(p[0] for p in pairs)
    gpfx_c = Counter(p[1] for p in pairs)
    joint_c = Counter(pairs)
    
    mi_s = 0.0
    for (sfx, gpfx), c in joint_c.items():
        p_j = c / n_s
        p_sfx = sfx_c[sfx] / n_s
        p_gpfx = gpfx_c[gpfx] / n_s
        if p_sfx > 0 and p_gpfx > 0:
            mi_s += p_j * math.log2(p_j / (p_sfx * p_gpfx))
    
    cond_mi += p_stratum * mi_s

print(f"\n  MI(sfx, gpfx | last_char, first_char) = {cond_mi:.4f} bits")
print(f"  Unconditional MI(sfx, gpfx): {mi_morph:.4f}")
print(f"  Explained by characters: {(1 - cond_mi/mi_morph)*100:.1f}%")
print(f"  RESIDUAL (morphology beyond characters): {cond_mi:.4f} bits ({cond_mi/mi_morph*100:.1f}%)")

# Permutation test on the conditional MI
n_shuf = 200
shuf_cond_mi = []
for trial in range(n_shuf):
    # Within each (lc, fc) stratum, shuffle the (sfx, gpfx) pairing
    shuf_mi = 0.0
    for (lc, fc), pairs in strata.items():
        n_s = len(pairs)
        if n_s < 2:
            continue
        p_stratum = n_s / n_trans
        sfxs = [p[0] for p in pairs]
        gpfxs = [p[1] for p in pairs]
        random.shuffle(gpfxs)
        
        sfx_c = Counter(sfxs)
        gpfx_c = Counter(gpfxs)
        joint_c = Counter(zip(sfxs, gpfxs))
        
        mi_s = 0.0
        for (sfx, gpfx), c in joint_c.items():
            p_j = c / n_s
            p_sfx = sfx_c[sfx] / n_s
            p_gpfx = gpfx_c[gpfx] / n_s
            if p_sfx > 0 and p_gpfx > 0:
                mi_s += p_j * math.log2(p_j / (p_sfx * p_gpfx))
        
        shuf_mi += p_stratum * mi_s
    shuf_cond_mi.append(shuf_mi)

z_cond = (cond_mi - np.mean(shuf_cond_mi)) / np.std(shuf_cond_mi)
print(f"\n  Shuffled conditional MI: {np.mean(shuf_cond_mi):.4f} ± {np.std(shuf_cond_mi):.4f}")
print(f"  z-score (morph BEYOND characters): {z_cond:.1f}")

# Also: what fraction of suffix info is in the last char?
# If suffix is fully determined by last char, then sfx→gpfx IS lc→gpfx
sfx_by_lastchar = defaultdict(Counter)
for w in all_collapsed:
    sfx = get_suffix(w)
    lc = w[-1] if w else '?'
    sfx_by_lastchar[lc][sfx] += 1

print(f"\n  Suffix given last character:")
for lc in sorted(sfx_by_lastchar.keys()):
    total = sum(sfx_by_lastchar[lc].values())
    if total < 50: continue
    top = sfx_by_lastchar[lc].most_common(3)
    top_str = ", ".join(f"{s}:{c/total*100:.0f}%" for s, c in top)
    h = compute_H(sfx_by_lastchar[lc], total)
    print(f"  last='{lc}' (N={total:>5}): H(sfx|lc)={h:.3f}, top: {top_str}")

# Reverse: prefix given first char
gpfx_by_firstchar = defaultdict(Counter)
for w in all_collapsed:
    gpfx = get_gram_prefix(w)
    fc = w[0] if w else '?'
    gpfx_by_firstchar[fc][gpfx] += 1

print(f"\n  Prefix given first character:")
for fc in sorted(gpfx_by_firstchar.keys()):
    total = sum(gpfx_by_firstchar[fc].values())
    if total < 50: continue
    top = gpfx_by_firstchar[fc].most_common(3)
    top_str = ", ".join(f"{g}:{c/total*100:.0f}%" for g, c in top)
    h = compute_H(gpfx_by_firstchar[fc], total)
    print(f"  first='{fc}' (N={total:>5}): H(gpfx|fc)={h:.3f}, top: {top_str}")


# ══════════════════════════════════════════════════════════════════
# 51b: IS LOW H(char|prev) A TRANSCRIPTION ARTIFACT?
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("51b: IS LOW H(char|prev) A TRANSCRIPTION ARTIFACT?")
print("    EVA compound glyphs may inflate character count and")
print("    deflate conditional entropy")
print("=" * 70)

# EVA "characters" known to be compound glyphs:
# ch, sh, cth, ckh, cph, cfh (bench-type gallows)
# These are VISUAL UNITS in the manuscript that EVA splits into 2-3 letters.
# If we treat these as single glyphs, the alphabet shrinks and
# H(char|prev) may change dramatically.

# Define a glyph-level tokenization
GLYPH_MAP = [
    # Order matters: longest first
    ('cth', 'G1'), ('ckh', 'G2'), ('cph', 'G3'), ('cfh', 'G4'),
    ('tch', 'G5'), ('kch', 'G6'), ('pch', 'G7'), ('fch', 'G8'),
    ('tsh', 'G9'), ('ksh', 'GA'), ('psh', 'GB'), ('fsh', 'GC'),
    ('ch', 'C'), ('sh', 'S'),
    ('ii', 'I'),  # ii is probably a single glyph (connected)
    ('ee', 'E'),  # ee might be a single glyph
    ('ai', 'A'),  # ain-like combination
]

def to_glyphs(w):
    """Convert EVA word to glyph sequence"""
    result = []
    i = 0
    while i < len(w):
        matched = False
        for eva, glyph in GLYPH_MAP:
            if w[i:i+len(eva)] == eva:
                result.append(glyph)
                i += len(eva)
                matched = True
                break
        if not matched:
            result.append(w[i])
            i += 1
    return result

# Compute H(char|prev) at EVA level vs glyph level
# EVA level (raw)
eva_chars = []
for w in all_raw:
    eva_chars.extend(list(w))
    eva_chars.append(' ')  # word boundary

eva_bg = Counter()
eva_uni = Counter()
for i in range(len(eva_chars) - 1):
    eva_bg[(eva_chars[i], eva_chars[i+1])] += 1
    eva_uni[eva_chars[i]] += 1
eva_uni[eva_chars[-1]] += 1

H_eva_uni = compute_H(eva_uni, len(eva_chars))
H_eva_cond = 0.0
for c1, n1 in eva_uni.items():
    succs = Counter()
    for (a, b), cnt in eva_bg.items():
        if a == c1: succs[b] += cnt
    if sum(succs.values()) > 0:
        h = compute_H(succs, sum(succs.values()))
        H_eva_cond += (n1 / len(eva_chars)) * h

# Glyph level
glyph_chars = []
for w in all_raw:
    glyph_chars.extend(to_glyphs(w))
    glyph_chars.append(' ')

glyph_bg = Counter()
glyph_uni = Counter()
for i in range(len(glyph_chars) - 1):
    glyph_bg[(glyph_chars[i], glyph_chars[i+1])] += 1
    glyph_uni[glyph_chars[i]] += 1
glyph_uni[glyph_chars[-1]] += 1

H_glyph_uni = compute_H(glyph_uni, len(glyph_chars))
H_glyph_cond = 0.0
for c1, n1 in glyph_uni.items():
    succs = Counter()
    for (a, b), cnt in glyph_bg.items():
        if a == c1: succs[b] += cnt
    if sum(succs.values()) > 0:
        h = compute_H(succs, sum(succs.values()))
        H_glyph_cond += (n1 / len(glyph_chars)) * h

n_eva = len(set(eva_uni.keys()))
n_glyph = len(set(glyph_uni.keys()))

print(f"\n  EVA character level:")
print(f"  Alphabet size: {n_eva}")
print(f"  H(char): {H_eva_uni:.3f} bits")
print(f"  H(char|prev): {H_eva_cond:.3f} bits")
print(f"  Total chars: {len(eva_chars)}")

print(f"\n  Glyph level (compound glyphs merged):")
print(f"  Alphabet size: {n_glyph}")
print(f"  H(glyph): {H_glyph_uni:.3f} bits")
print(f"  H(glyph|prev): {H_glyph_cond:.3f} bits")
print(f"  Total glyphs: {len(glyph_chars)}")

# The real comparison: bits per word
mean_eva_per_word = np.mean([len(w) for w in all_raw])
mean_glyph_per_word = np.mean([len(to_glyphs(w)) for w in all_raw])
print(f"\n  Mean EVA chars/word: {mean_eva_per_word:.2f}")
print(f"  Mean glyphs/word: {mean_glyph_per_word:.2f}")
print(f"  Bits/word (EVA bigram): {H_eva_cond * mean_eva_per_word:.2f}")
print(f"  Bits/word (glyph bigram): {H_glyph_cond * mean_glyph_per_word:.2f}")

# What does English look like at these sample sizes?
# English has ~4.07 H(char), ~3.3 H(char|prev).
# But that's with 26 chars. If we merged 'th', 'sh', 'ch', 'qu' etc
# into single glyphs, English H(char|prev) would also drop.
# The fair comparison is bits-per-word, not bits-per-glyph.

print(f"\n  CRITICAL COMPARISON (bits per word from character model):")
print(f"  VMS (EVA):   {H_eva_cond * mean_eva_per_word:.2f} bits/word")
print(f"  VMS (glyph): {H_glyph_cond * mean_glyph_per_word:.2f} bits/word")
print(f"  English*:    ~{3.3 * 4.7:.1f} bits/word (3.3 × 4.7 chars)")
print(f"  * English values are literature estimates")


# ══════════════════════════════════════════════════════════════════
# 51c: CAN WE EXCLUDE CONSTRUCTED LANGUAGE?
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("51c: CAN WE EXCLUDE CONSTRUCTED LANGUAGE?")
print("    Is sparse word bigram just a corpus size effect?")
print("=" * 70)

# Generate text from a REGULAR constructed-language-like model:
# - Fixed set of stems (200)
# - Fixed set of suffixes (10) and prefixes (7)
# - Rigid word-class system: Class A words followed by Class B words
# - Same corpus size as VMS

# Then test: does this constructed text also have sparse bigrams?

stems_cl = [f"stem{i}" for i in range(200)]
sfx_cl = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
pfx_cl = ['P', 'Q', 'R', 'S', 'T', 'U', 'V']

# Word classes: even sfx = class A, odd sfx = class B
# Rule: A words must be followed by B words and vice versa (rigid alternation)
cl_vocab = []
for stem in stems_cl:
    for sfx in sfx_cl:
        for pfx in pfx_cl:
            cl_vocab.append(pfx + stem + sfx)

# Generate text with rigid class alternation + Zipf frequency
# Assign Zipf frequencies to words
n_words_cl = len(sfx_cl) * len(pfx_cl) * len(stems_cl)
# Use Zipf with exponent 1.0
zipf_weights_a = np.array([1.0 / (i + 1) for i in range(n_words_cl // 2)])
zipf_weights_b = np.array([1.0 / (i + 1) for i in range(n_words_cl // 2)])
zipf_weights_a /= zipf_weights_a.sum()
zipf_weights_b /= zipf_weights_b.sum()

# Split vocab into A and B
vocab_a = [w for w in cl_vocab if sfx_cl.index(w[-1]) % 2 == 0]
vocab_b = [w for w in cl_vocab if sfx_cl.index(w[-1]) % 2 == 1]
random.shuffle(vocab_a)
random.shuffle(vocab_b)
vocab_a = vocab_a[:len(zipf_weights_a)]
vocab_b = vocab_b[:len(zipf_weights_b)]

# Generate 35K tokens
cl_text = []
is_a = True  # Start with class A
line_lengths = [len(seq) for seq in line_collapsed]
for length in random.choices(line_lengths, k=len(line_collapsed)):
    line = []
    for _ in range(length):
        if is_a:
            w = np.random.choice(len(vocab_a), p=zipf_weights_a[:len(vocab_a)] / zipf_weights_a[:len(vocab_a)].sum())
            line.append(vocab_a[w])
        else:
            w = np.random.choice(len(vocab_b), p=zipf_weights_b[:len(vocab_b)] / zipf_weights_b[:len(vocab_b)].sum())
            line.append(vocab_b[w])
        is_a = not is_a
    cl_text.append(line)

cl_all = [w for line in cl_text for w in line]
cl_N = len(cl_all)
cl_V = len(set(cl_all))

# Cross-validate word bigrams on the constructed text
even_cl = [cl_text[i] for i in range(0, len(cl_text), 2)]
odd_cl = [cl_text[i] for i in range(1, len(cl_text), 2)]

# Train bigram on even, test on odd
train_bg = Counter()
train_uni = Counter()
for seq in even_cl:
    for i in range(len(seq) - 1):
        train_bg[(seq[i], seq[i+1])] += 1
        train_uni[seq[i]] += 1

# Test: fraction of bigrams unseen
test_bg = Counter()
for seq in odd_cl:
    for i in range(len(seq) - 1):
        test_bg[(seq[i], seq[i+1])] += 1

unseen_cl = sum(c for bg, c in test_bg.items() if bg not in train_bg)
total_test_cl = sum(test_bg.values())
frac_unseen_cl = unseen_cl / total_test_cl if total_test_cl > 0 else 0

# Same for VMS
even_vms = [line_collapsed[i] for i in range(0, len(line_collapsed), 2)]
odd_vms = [line_collapsed[i] for i in range(1, len(line_collapsed), 2)]

vms_train_bg = Counter()
for seq in even_vms:
    for i in range(len(seq) - 1):
        vms_train_bg[(seq[i], seq[i+1])] += 1

vms_test_bg = Counter()
for seq in odd_vms:
    for i in range(len(seq) - 1):
        vms_test_bg[(seq[i], seq[i+1])] += 1

unseen_vms = sum(c for bg, c in vms_test_bg.items() if bg not in vms_train_bg)
total_test_vms = sum(vms_test_bg.values())
frac_unseen_vms = unseen_vms / total_test_vms if total_test_vms > 0 else 0

# Also compute for a UNIGRAM model (random word-by-word, no grammar)
uni_text = []
all_flat = list(all_collapsed)
for length in [len(seq) for seq in line_collapsed]:
    line = random.choices(all_flat, k=length)
    uni_text.append(line)

even_uni = [uni_text[i] for i in range(0, len(uni_text), 2)]
odd_uni = [uni_text[i] for i in range(1, len(uni_text), 2)]

uni_train_bg = Counter()
for seq in even_uni:
    for i in range(len(seq) - 1):
        uni_train_bg[(seq[i], seq[i+1])] += 1

uni_test_bg = Counter()
for seq in odd_uni:
    for i in range(len(seq) - 1):
        uni_test_bg[(seq[i], seq[i+1])] += 1

unseen_uni = sum(c for bg, c in uni_test_bg.items() if bg not in uni_train_bg)
total_test_uni = sum(uni_test_bg.values())
frac_unseen_uni = unseen_uni / total_test_uni if total_test_uni > 0 else 0

print(f"\n  Bigram sparsity comparison:")
print(f"  {'Model':>25} {'N':>8} {'V':>8} {'%Unseen':>10}")
print(f"  {'VMS':>25} {N:>8} {V:>8} {frac_unseen_vms*100:>9.1f}%")
print(f"  {'Constructed (rigid AB)':>25} {cl_N:>8} {cl_V:>8} {frac_unseen_cl*100:>9.1f}%")
print(f"  {'Unigram (no grammar)':>25} {N:>8} {V:>8} {frac_unseen_uni*100:>9.1f}%")
print(f"\n  If constructed lang has LESS unseen than VMS, our 'excludes constructed'")
print(f"  claim may be wrong.")


# ══════════════════════════════════════════════════════════════════
# 51d: THE COMPOSITIONALITY TEST
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("51d: THE COMPOSITIONALITY TEST")
print("    If words = pfx+stem+sfx, novel combinations should exist")
print("=" * 70)

# In a truly agglutinative language, if stem X appears with suffix A
# and suffix B, and stem Y appears with suffix A, we'd expect stem Y
# with suffix B to also appear. How often does this hold?

# Parse all words
parsed = {}
for w in set(all_collapsed):
    sfx = get_suffix(w)
    gpfx = get_gram_prefix(w)
    # Extract "core" = what's between prefix and suffix
    core = w
    for gp in GRAM_PREFIXES:
        if core.startswith(gp) and len(core) > len(gp):
            core = core[len(gp):]
            break
    for sx in SUFFIXES:
        if core.endswith(sx) and len(core) > len(sx):
            core = core[:-len(sx)]
            break
    parsed[w] = (gpfx, core, sfx)

# Build stem-suffix matrix
stem_sfx_matrix = defaultdict(set)
sfx_stem_matrix = defaultdict(set)
for w, (gpfx, core, sfx) in parsed.items():
    if core and len(core) >= 1:  # meaningful stem
        stem_sfx_matrix[core].add(sfx)
        sfx_stem_matrix[sfx].add(core)

# Count stems that appear with multiple suffixes
multi_sfx_stems = {s: sset for s, sset in stem_sfx_matrix.items() if len(sset) >= 2}
print(f"\n  Stems with 1 suffix: {sum(1 for s, v in stem_sfx_matrix.items() if len(v) == 1)}")
print(f"  Stems with 2+ suffixes: {len(multi_sfx_stems)}")
print(f"  Stems with 3+ suffixes: {sum(1 for s, v in stem_sfx_matrix.items() if len(v) >= 3)}")

# Paradigm completeness test:
# For each pair of stems that share at least 2 suffixes,
# what fraction of the "expected" paradigm cells are filled?
paradigm_fills = []
common_stems = [s for s, v in stem_sfx_matrix.items() if len(v) >= 3]
all_sfx_set = set()
for s in common_stems:
    all_sfx_set.update(stem_sfx_matrix[s])

# For each common stem: how many of the most-common suffixes does it have?
top_suffixes = ['X', 'y', 'dy', 'aiin', 'ain', 'ar', 'or', 'al', 'ol', 'in', 'iin']
for stem in sorted(common_stems, key=lambda s: -len(stem_sfx_matrix[s]))[:20]:
    sfx_set = stem_sfx_matrix[stem]
    fill = len(sfx_set & set(top_suffixes)) / len(top_suffixes) * 100
    paradigm_fills.append(fill)
    # Count tokens
    tok = sum(Counter(all_collapsed).get(w, 0) for w, (_, c, _) in parsed.items() if c == stem)

# Compositionality prediction:
# If stem S has suffixes {A, B} and stem T has suffixes {A, C},
# does stem S also appear with suffix C? Does T appear with B?
n_predicted = 0
n_found = 0
n_tested = 0

# For each pair of stems sharing a suffix...
from itertools import combinations
frequent_stems = [s for s, v in stem_sfx_matrix.items() 
                  if len(v) >= 2 and sum(Counter(all_collapsed).get(w, 0) 
                  for w, (_, c, _) in parsed.items() if c == s) >= 10]

print(f"\n  Frequent stems (2+ suffixes, 10+ tokens): {len(frequent_stems)}")

# For each frequent stem, check: for every suffix it DOESN'T have,
# could we predict it based on analogy?
word_set = set(all_collapsed)
fill_predictions = []
for stem in frequent_stems:
    known_sfx = stem_sfx_matrix[stem]
    unknown_sfx = set(top_suffixes) - known_sfx
    for sfx in unknown_sfx:
        # Does ANY other stem with the same suffix set overlap share this suffix?
        # (i.e., is the gap a genuine one or just vocab not covered?)
        # Build the hypothetical word
        hypo_word = stem + (sfx if sfx != 'X' else '')
        # Check if ANY prefix variant exists
        found = hypo_word in word_set
        if not found:
            for gp in GRAM_PREFIXES:
                if (gp + hypo_word) in word_set:
                    found = True
                    break
        fill_predictions.append(found)

total_gaps = len(fill_predictions)
filled_gaps = sum(fill_predictions)
print(f"\n  Paradigm gap analysis:")
print(f"  Total gaps (stem×suffix combinations NOT directly observed): {total_gaps}")
print(f"  Gaps filled by prefix variants: {filled_gaps} ({filled_gaps/total_gaps*100:.1f}%)")
print(f"  True gaps (never observed): {total_gaps - filled_gaps} ({(total_gaps-filled_gaps)/total_gaps*100:.1f}%)")

# How does this compare to a random lexicon?
# Shuffle suffix assignments across words and recompute
n_shuf = 100
shuf_fills = []
all_words_list = list(set(all_collapsed))
for trial in range(n_shuf):
    # Assign random suffixes to each word
    shuf_sfx = {w: random.choice(top_suffixes) for w in all_words_list}
    shuf_stem_sfx = defaultdict(set)
    for w in all_words_list:
        _, core, _ = parsed.get(w, ('X', w, 'X'))
        shuf_stem_sfx[core].add(shuf_sfx[w])
    
    shuf_freq_stems = [s for s, v in shuf_stem_sfx.items() 
                       if len(v) >= 2]
    shuf_f = 0
    shuf_t = 0
    for stem in shuf_freq_stems[:len(frequent_stems)]:
        known = shuf_stem_sfx[stem]
        unknown = set(top_suffixes) - known
        for sfx in unknown:
            hypo = stem + (sfx if sfx != 'X' else '')
            found = hypo in word_set
            if not found:
                for gp in GRAM_PREFIXES:
                    if (gp + hypo) in word_set:
                        found = True
                        break
            shuf_t += 1
            if found: shuf_f += 1
    if shuf_t > 0:
        shuf_fills.append(shuf_f / shuf_t * 100)

if shuf_fills:
    print(f"\n  Random baseline fill rate: {np.mean(shuf_fills):.1f}% ± {np.std(shuf_fills):.1f}%")
    print(f"  Observed fill rate: {filled_gaps/total_gaps*100:.1f}%")
    z_fill = (filled_gaps/total_gaps*100 - np.mean(shuf_fills)) / np.std(shuf_fills) if np.std(shuf_fills) > 0 else 0
    print(f"  z-score: {z_fill:.1f}")


# ══════════════════════════════════════════════════════════════════
# 51e: CARDAN GRILLE / TABLE-GENERATED TEXT
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("51e: CARDAN GRILLE / TABLE-GENERATED TEXT")
print("    Does table-based generation produce VMS-like statistics?")
print("=" * 70)

# Rugg (2004): Words generated by sliding a template over a table
# of syllables. This produces:
# 1. Prefix-like elements from left columns
# 2. Middle elements from central columns  
# 3. Suffix-like elements from right columns
# 4. Line-internal patterns from consistent column use within a line
# 5. Line-boundary resets when the grille is repositioned

# Simulate a simple 3-column grille:
# Col 1 (prefix): weighted random from observed prefix distribution
# Col 2 (middle): weighted random from observed stem distribution
# Col 3 (suffix): weighted random from observed suffix distribution
# KEY PROPERTY: within a line, the "window position" shifts slowly,
# creating local dependencies

pfx_list = [''] + [gp for gp in GRAM_PREFIXES]
sfx_list_g = [''] + list(SUFFIXES)

# Get frequency distributions
pfx_freq = Counter()
mid_freq = Counter()
sfx_freq = Counter()
for w, (gpfx, core, sfx) in parsed.items():
    count = Counter(all_collapsed)[w]
    pfx_freq[gpfx if gpfx != 'X' else ''] += count
    mid_freq[core] += count
    sfx_freq[sfx if sfx != 'X' else ''] += count

def weighted_choice(freq_dict):
    items = list(freq_dict.keys())
    weights = np.array([freq_dict[k] for k in items], dtype=float)
    weights /= weights.sum()
    return items[np.random.choice(len(items), p=weights)]

# Generate grille text: N_ROWS positions per line
# Within a line, the "row" shifts by 0 or 1 with each word
# At line boundaries, row resets to random position
grille_text = []
for length in [len(seq) for seq in line_collapsed]:
    line = []
    # Within a line, prefix choice is sticky (shifts slowly)
    # This creates local dependencies like suffix→prefix
    prev_pfx = weighted_choice(pfx_freq)
    for pos in range(length):
        # Prefix: 70% chance of keeping same type as previous, 30% new
        if random.random() < 0.3:
            pfx = weighted_choice(pfx_freq)
        else:
            pfx = prev_pfx
        mid = weighted_choice(mid_freq)
        sfx = weighted_choice(sfx_freq)
        word = pfx + mid + sfx
        line.append(word)
        prev_pfx = pfx
    grille_text.append(line)

grille_all = [w for line in grille_text for w in line]
grille_N = len(grille_all)
grille_V = len(set(grille_all))
grille_H = compute_H(Counter(grille_all), grille_N)

# Compute suffix→prefix MI on grille text
grille_sfx_gpfx = Counter()
grille_sfx_m = Counter()
grille_gpfx_m = Counter()
grille_trans = 0
for seq in grille_text:
    for i in range(len(seq) - 1):
        s = get_suffix(seq[i])
        g = get_gram_prefix(seq[i+1])
        grille_sfx_gpfx[(s, g)] += 1
        grille_sfx_m[s] += 1
        grille_gpfx_m[g] += 1
        grille_trans += 1

grille_mi = 0.0
for (s, g), c in grille_sfx_gpfx.items():
    p_j = c / grille_trans
    p_s = grille_sfx_m[s] / grille_trans
    p_g = grille_gpfx_m[g] / grille_trans
    if p_s > 0 and p_g > 0:
        grille_mi += p_j * math.log2(p_j / (p_s * p_g))

# Cross-line MI for grille
grille_cross = Counter()
grille_cross_sfx = Counter()
grille_cross_gpfx = Counter()
grille_cross_n = 0
for i in range(len(grille_text) - 1):
    if grille_text[i] and grille_text[i+1]:
        s = get_suffix(grille_text[i][-1])
        g = get_gram_prefix(grille_text[i+1][0])
        grille_cross[(s, g)] += 1
        grille_cross_sfx[s] += 1
        grille_cross_gpfx[g] += 1
        grille_cross_n += 1

grille_cross_mi = 0.0
for (s, g), c in grille_cross.items():
    p_j = c / grille_cross_n
    p_s = grille_cross_sfx[s] / grille_cross_n
    p_g = grille_cross_gpfx[g] / grille_cross_n
    if p_s > 0 and p_g > 0:
        grille_cross_mi += p_j * math.log2(p_j / (p_s * p_g))

# Character-level entropy for grille
grille_chars = []
for w in grille_all:
    grille_chars.extend(list(w))
    grille_chars.append(' ')

grille_char_bg = Counter()
grille_char_uni = Counter()
for i in range(len(grille_chars) - 1):
    grille_char_bg[(grille_chars[i], grille_chars[i+1])] += 1
    grille_char_uni[grille_chars[i]] += 1

H_grille_char_cond = 0.0
for c1, n1 in grille_char_uni.items():
    succs = Counter()
    for (a, b), cnt in grille_char_bg.items():
        if a == c1: succs[b] += cnt
    if sum(succs.values()) > 0:
        h = compute_H(succs, sum(succs.values()))
        H_grille_char_cond += (n1 / len(grille_chars)) * h

# Compare statistics
hapax_vms = sum(1 for c in Counter(all_collapsed).values() if c == 1) / V * 100
hapax_grille = sum(1 for c in Counter(grille_all).values() if c == 1) / grille_V * 100

selfrep_vms = sum(1 for seq in line_collapsed for i in range(len(seq)-1) if seq[i]==seq[i+1]) / sum(len(seq)-1 for seq in line_collapsed) * 100
selfrep_gr = sum(1 for seq in grille_text for i in range(len(seq)-1) if seq[i]==seq[i+1]) / sum(len(seq)-1 for seq in grille_text) * 100

print(f"\n  {'Metric':>30} {'VMS':>12} {'Grille':>12}")
print(f"  {'Tokens':>30} {N:>12} {grille_N:>12}")
print(f"  {'Types':>30} {V:>12} {grille_V:>12}")
print(f"  {'H(word)':>30} {8.481:>12.3f} {grille_H:>12.3f}")
print(f"  {'Hapax %':>30} {hapax_vms:>11.1f}% {hapax_grille:>11.1f}%")
print(f"  {'Self-rep %':>30} {selfrep_vms:>11.1f}% {selfrep_gr:>11.1f}%")
print(f"  {'MI(sfx→gpfx) within-line':>30} {mi_morph:>12.4f} {grille_mi:>12.4f}")
print(f"  {'MI(sfx→gpfx) cross-line':>30} {0.0106:>12.4f} {grille_cross_mi:>12.4f}")
print(f"  {'Cross/within ratio':>30} {0.0106/mi_morph:>12.3f} {grille_cross_mi/grille_mi:>12.3f}" if grille_mi > 0 else "")
print(f"  {'H(char|prev)':>30} {1.922:>12.3f} {H_grille_char_cond:>12.3f}")
print(f"  {'Type-token ratio':>30} {V/N:>12.4f} {grille_V/grille_N:>12.4f}")

# What matches and what doesn't?
print(f"\n  GRILLE MODEL MATCHES:")
matches = 0
mismatches = 0
if abs(grille_mi - mi_morph) / mi_morph < 0.5:
    print(f"  ✓ Within-line MI similar")
    matches += 1
else:
    print(f"  ✗ Within-line MI differs ({grille_mi:.4f} vs {mi_morph:.4f})")
    mismatches += 1

if grille_cross_mi < grille_mi * 0.3:
    print(f"  ✓ Cross-line MI drops (grille resets)")
    matches += 1
else:
    print(f"  ✗ Cross-line MI doesn't drop enough")
    mismatches += 1

if abs(hapax_grille - hapax_vms) < 10:
    print(f"  ✓ Hapax ratio similar")
    matches += 1
else:
    print(f"  ✗ Hapax ratio differs")
    mismatches += 1

if abs(grille_H - 8.481) < 2:
    print(f"  ✓ Word entropy similar")
    matches += 1
else:
    print(f"  ✗ Word entropy differs")
    mismatches += 1

print(f"\n  Score: {matches} match, {mismatches} mismatch out of {matches+mismatches}")

print("\n" + "=" * 70)
print("PHASE 51 COMPLETE — ATTACKING THE SYNTHESIS")
print("=" * 70)
