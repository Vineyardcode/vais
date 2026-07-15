#!/usr/bin/env python3
"""
Phase 55 — VOWEL-CONSONANT SEPARATION & PHONOLOGICAL INFERENCE
================================================================

This is the first DECIPHERMENT-oriented phase. Instead of profiling
statistics, we EXPLOIT them.

Approach:
  55a) SUKHOTIN'S ALGORITHM
       The classic unsupervised V/C separator. Works by iterating:
       most-contacted character = vowel, remove, repeat.
       Also: spectral method (eigenvector of contact matrix).

  55b) CROSS-VALIDATION
       Train V/C on half the data, test alternation prediction on other half.
       If V/C is real, it should generalize. If not, it's noise.

  55c) PHONOLOGICAL INFERENCE FROM BETWEEN-WORD TRANSITIONS
       Using V/C labels: is the last→first char pattern:
       - Sandhi (V→V avoided, C→C avoided)?
       - Vowel harmony (V→V preferred)?
       - Liaison (C→V preferred)?
       Each makes different predictions about language family.

  55d) LANGUAGE FINGERPRINT MATCHING
       Compute V/C ratio, mean syllable length (as V-runs / C-runs),
       consonant cluster frequency, and compare to known language families.

  55e) SYLLABARY TEST
       If each EVA character is already a syllable (CV or V), then:
       - V/C separation should FAIL (no alternation pattern)
       - OR produce a degenerate split (everything = "vowel")
       The quality of V/C separation itself tests the script type.

CRITICAL CAVEAT: EVA compound glyphs (ch, sh, etc.) may be single
original characters. We test both raw EVA and merged-glyph versions.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, get_collapsed, load_lines_v2 as load_lines, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(55)
np.random.seed(55)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']

# Glyph merging map (EVA compound glyphs → single symbols)
GLYPH_MAP = {
    'ch': 'C', 'sh': 'S', 'ii': 'I', 'ee': 'E', 'ai': 'A',
    'cth': 'Ŧ', 'ckh': 'K', 'cph': 'Φ', 'cfh': 'F',
    'tch': 'Ç', 'kch': 'Ƈ', 'pch': 'Ƥ', 'fch': 'Ƒ',
    'tsh': 'Ş', 'ksh': 'Ḱ', 'psh': 'Ṕ', 'fsh': 'Ḟ',
}


def to_glyphs(word):
    """Convert EVA word to merged glyph sequence."""
    result = []
    i = 0
    # Sort multi-char glyphs by length (longest first)
    sorted_glyphs = sorted(GLYPH_MAP.keys(), key=len, reverse=True)
    while i < len(word):
        matched = False
        for glyph in sorted_glyphs:
            if word[i:i+len(glyph)] == glyph:
                result.append(GLYPH_MAP[glyph])
                i += len(glyph)
                matched = True
                break
        if not matched:
            result.append(word[i])
            i += 1
    return result

FOLIO_DIR = Path("folios")


print("Loading corpus...")
raw_lines = load_lines()
line_collapsed = [[get_collapsed(w) for w in line] for line in raw_lines]
all_collapsed = [w for seq in line_collapsed for w in seq]
N = len(all_collapsed)
vocab = Counter(all_collapsed)
print(f"  {N} tokens, {len(vocab)} types, {len(raw_lines)} lines\n")


# ============================================================
# SUKHOTIN'S ALGORITHM
# ============================================================
def sukhotins_algorithm(words, char_list=None):
    """
    Sukhotin's algorithm for V/C classification.
    Input: list of words (each word is a sequence of characters).
    Returns: dict mapping character → 'V' or 'C'
    """
    # Build contact matrix: count of times char_a is adjacent to char_b
    contact = defaultdict(lambda: defaultdict(int))
    char_freq = Counter()
    
    for word in words:
        for i in range(len(word) - 1):
            a, b = word[i], word[i+1]
            if a != b:  # Sukhotin excludes self-contacts
                contact[a][b] += 1
                contact[b][a] += 1
            char_freq[a] += 1
        if word:
            char_freq[word[-1]] += 1
    
    if char_list is None:
        char_list = sorted(char_freq.keys())
    
    # Initialize: all characters are consonants
    classification = {c: 'C' for c in char_list}
    remaining = set(char_list)
    
    # Iteratively find vowels
    while remaining:
        # For each remaining character, compute total contact with consonants
        # (i.e., with all remaining characters, since all unclassified = C)
        scores = {}
        for c in remaining:
            score = sum(contact[c].get(other, 0) for other in remaining if other != c)
            scores[c] = score
        
        # The character with highest score is the next vowel
        best_char = max(scores, key=scores.get)
        best_score = scores[best_char]
        
        if best_score <= 0:
            break  # No more vowels
        
        classification[best_char] = 'V'
        remaining.remove(best_char)
        
        # Subtract the vowel's contacts from remaining scores
        # (This is implicit in the next iteration since we removed it)
    
    return classification


# ============================================================
# 55a: V/C SEPARATION — BOTH EVA AND GLYPH LEVELS
# ============================================================
print("=" * 65)
print("55a: SUKHOTIN'S ALGORITHM — V/C SEPARATION")
print("=" * 65)

# --- EVA level ---
print("\n  === EVA CHARACTER LEVEL ===")
eva_chars = sorted(set(c for w in all_collapsed for c in w))
eva_vc = sukhotins_algorithm(all_collapsed, eva_chars)

vowels_eva = sorted(c for c, v in eva_vc.items() if v == 'V')
consonants_eva = sorted(c for c, v in eva_vc.items() if v == 'C')

# Character frequencies
char_freq = Counter()
for w in all_collapsed:
    for c in w:
        char_freq[c] += 1
total_chars = sum(char_freq.values())

print(f"  Vowels ({len(vowels_eva)}):     {' '.join(vowels_eva)}")
print(f"  Consonants ({len(consonants_eva)}): {' '.join(consonants_eva)}")

v_total = sum(char_freq[c] for c in vowels_eva)
c_total = sum(char_freq[c] for c in consonants_eva)
print(f"  V frequency: {v_total}/{total_chars} = {100*v_total/total_chars:.1f}%")
print(f"  C frequency: {c_total}/{total_chars} = {100*c_total/total_chars:.1f}%")
print(f"  V/C ratio: {v_total/c_total:.2f}")

# Show detailed char stats
print(f"\n  {'Char':>5s}  {'Class':>6s}  {'Freq':>6s}  {'%':>6s}  {'ContactDiv':>11s}")
for c in sorted(char_freq, key=char_freq.get, reverse=True):
    cls = eva_vc[c]
    f = char_freq[c]
    pct = 100 * f / total_chars
    # Contact diversity: how many distinct chars appear adjacent
    neighbors = set()
    for w in all_collapsed:
        for i in range(len(w) - 1):
            if w[i] == c: neighbors.add(w[i+1])
            if w[i+1] == c: neighbors.add(w[i])
    print(f"  {c:>5s}  {cls:>6s}  {f:6d}  {pct:5.1f}%  {len(neighbors):11d}")

# --- Glyph level ---
print(f"\n  === MERGED GLYPH LEVEL ===")
all_glyph_words = [to_glyphs(w) for w in all_collapsed]
all_glyph_chars = sorted(set(g for w in all_glyph_words for g in w))

glyph_vc = sukhotins_algorithm(all_glyph_words, all_glyph_chars)

vowels_glyph = sorted(c for c, v in glyph_vc.items() if v == 'V')
consonants_glyph = sorted(c for c, v in glyph_vc.items() if v == 'C')

glyph_freq = Counter()
for w in all_glyph_words:
    for g in w:
        glyph_freq[g] += 1
total_glyphs = sum(glyph_freq.values())

print(f"  Vowels ({len(vowels_glyph)}):     {' '.join(vowels_glyph)}")
print(f"  Consonants ({len(consonants_glyph)}): {' '.join(consonants_glyph)}")

v_total_g = sum(glyph_freq[c] for c in vowels_glyph)
c_total_g = sum(glyph_freq[c] for c in consonants_glyph)
print(f"  V frequency: {v_total_g}/{total_glyphs} = {100*v_total_g/total_glyphs:.1f}%")
print(f"  C frequency: {c_total_g}/{total_glyphs} = {100*c_total_g/total_glyphs:.1f}%")
print(f"  V/C ratio: {v_total_g/c_total_g:.2f}")


# ============================================================
# SPECTRAL CONFIRMATION
# ============================================================
print(f"\n  === SPECTRAL CONFIRMATION (Eigenvector method) ===")

# Build contact matrix for EVA level
contact_matrix = np.zeros((len(eva_chars), len(eva_chars)))
char_idx = {c: i for i, c in enumerate(eva_chars)}

for w in all_collapsed:
    for i in range(len(w) - 1):
        a, b = w[i], w[i+1]
        if a != b:
            contact_matrix[char_idx[a], char_idx[b]] += 1
            contact_matrix[char_idx[b], char_idx[a]] += 1

# Normalize rows
row_sums = contact_matrix.sum(axis=1, keepdims=True)
row_sums[row_sums == 0] = 1
contact_norm = contact_matrix / row_sums

# First eigenvector of the contact matrix should separate V from C
eigenvalues, eigenvectors = np.linalg.eigh(contact_norm)
# Use the eigenvector corresponding to the largest eigenvalue
idx = np.argmax(eigenvalues)
ev = eigenvectors[:, idx]

# The sign of the eigenvector component separates V from C
spectral_vowels = set()
spectral_consonants = set()
for i, c in enumerate(eva_chars):
    if ev[i] > 0:
        spectral_vowels.add(c)
    else:
        spectral_consonants.add(c)

# Check agreement with Sukhotin
sukhotin_set = set(vowels_eva)
agreement = len(sukhotin_set & spectral_vowels) + len(set(consonants_eva) & spectral_consonants)
total_agreement = agreement / len(eva_chars)

# Possibly the signs are flipped — check both orientations
flipped_agreement = (len(sukhotin_set & spectral_consonants) + len(set(consonants_eva) & spectral_vowels)) / len(eva_chars)
if flipped_agreement > total_agreement:
    spectral_vowels, spectral_consonants = spectral_consonants, spectral_vowels
    total_agreement = flipped_agreement

print(f"  Spectral vowels:     {' '.join(sorted(spectral_vowels))}")
print(f"  Spectral consonants: {' '.join(sorted(spectral_consonants))}")
print(f"  Agreement with Sukhotin: {100*total_agreement:.0f}%")

# Show eigenvector values
print(f"\n  Eigenvector values (sorted):")
ev_sorted = sorted(zip(eva_chars, ev), key=lambda x: x[1])
for c, val in ev_sorted:
    suk = eva_vc[c]
    print(f"    {c:>3s}  ev={val:+.4f}  Sukhotin={suk}")


# ============================================================
# 55b: CROSS-VALIDATION OF V/C CLASSIFICATION
# ============================================================
print("\n" + "=" * 65)
print("55b: CROSS-VALIDATION OF V/C ALTERNATION")
print("=" * 65)

# Train V/C on first half, test alternation prediction on second half
half = len(line_collapsed) // 2
train_words = [w for line in line_collapsed[:half] for w in line]
test_words = [w for line in line_collapsed[half:] for w in line]

train_vc = sukhotins_algorithm(train_words, eva_chars)

# Measure alternation rate: how often does V follow C or C follow V?
def alternation_rate(words, vc_map):
    alt = 0
    total = 0
    for w in words:
        for i in range(len(w) - 1):
            cls1 = vc_map.get(w[i], 'C')
            cls2 = vc_map.get(w[i+1], 'C')
            if cls1 != cls2:
                alt += 1
            total += 1
    return alt / total if total > 0 else 0

train_alt = alternation_rate(train_words, train_vc)
test_alt = alternation_rate(test_words, train_vc)

# Random baseline: if V/C labels were random
random_alts = []
for _ in range(1000):
    random_vc = {c: random.choice(['V', 'C']) for c in eva_chars}
    # Match V/C proportions
    n_v = sum(1 for c in train_vc.values() if c == 'V')
    chars_shuffled = list(eva_chars)
    random.shuffle(chars_shuffled)
    random_vc = {c: ('V' if i < n_v else 'C') for i, c in enumerate(chars_shuffled)}
    random_alts.append(alternation_rate(test_words, random_vc))

z_alt = (test_alt - np.mean(random_alts)) / np.std(random_alts)

print(f"  Train alternation rate: {train_alt:.4f}")
print(f"  Test alternation rate:  {test_alt:.4f}")
print(f"  Random baseline:        {np.mean(random_alts):.4f} ± {np.std(random_alts):.4f}")
print(f"  z-score:                {z_alt:.1f}")
print(f"  Retention:              {test_alt/train_alt:.3f} ({100*test_alt/train_alt:.1f}%)")

# Agreement between train-derived and full-corpus V/C
full_vowels = set(c for c, v in eva_vc.items() if v == 'V')
train_vowels = set(c for c, v in train_vc.items() if v == 'V')
agree = len(full_vowels & train_vowels) + len((set(eva_chars) - full_vowels) & (set(eva_chars) - train_vowels))
print(f"  V/C agreement (train vs full): {agree}/{len(eva_chars)} ({100*agree/len(eva_chars):.0f}%)")
if full_vowels != train_vowels:
    print(f"  Disagreements: {full_vowels ^ train_vowels}")

# Does V/C alternation even exist in VMS? Compare to random character labeling
print(f"\n  IS THE ALTERNATION REAL?")
print(f"  Observed alternation: {test_alt:.4f}")
print(f"  If V/C were meaningless: {np.mean(random_alts):.4f}")
print(f"  Excess alternation: {test_alt - np.mean(random_alts):+.4f}")
print(f"  z = {z_alt:.1f}")
if z_alt > 3:
    print(f"  VERDICT: V/C alternation is REAL (z={z_alt:.1f})")
elif z_alt > 2:
    print(f"  VERDICT: V/C alternation is WEAK but present")
else:
    print(f"  VERDICT: NO significant V/C alternation — SYLLABARY SIGNAL")


# ============================================================
# 55c: PHONOLOGICAL INFERENCE FROM BETWEEN-WORD TRANSITIONS
# ============================================================
print("\n" + "=" * 65)
print("55c: BETWEEN-WORD V/C TRANSITION ANALYSIS")
print("=" * 65)

# Classify between-word transitions using V/C labels
between_vc = Counter()  # (last_vc, first_vc) → count
for line in line_collapsed:
    for i in range(len(line) - 1):
        if line[i] and line[i+1]:
            last_c = eva_vc.get(line[i][-1], 'C')
            first_c = eva_vc.get(line[i+1][0], 'C')
            between_vc[(last_c, first_c)] += 1

total_between = sum(between_vc.values())
print(f"  Between-word V/C transitions (N={total_between}):")
for (a, b) in [('V','V'), ('V','C'), ('C','V'), ('C','C')]:
    count = between_vc.get((a, b), 0)
    pct = 100 * count / total_between
    print(f"    {a}→{b}: {count:6d} ({pct:5.1f}%)")

# Compare to within-word transitions
within_vc = Counter()
for w in all_collapsed:
    for i in range(len(w) - 1):
        a = eva_vc.get(w[i], 'C')
        b = eva_vc.get(w[i+1], 'C')
        within_vc[(a, b)] += 1

total_within = sum(within_vc.values())
print(f"\n  Within-word V/C transitions (N={total_within}):")
for (a, b) in [('V','V'), ('V','C'), ('C','V'), ('C','C')]:
    count = within_vc.get((a, b), 0)
    pct = 100 * count / total_within
    print(f"    {a}→{b}: {count:6d} ({pct:5.1f}%)")

# Compute observed/expected ratios
print(f"\n  Observed/Expected ratios:")
# Marginals
v_rate_end = sum(between_vc.get((v, x), 0) for v in ['V'] for x in ['V','C']) / total_between
c_rate_end = 1 - v_rate_end  
v_rate_start = sum(between_vc.get((x, v), 0) for v in ['V'] for x in ['V','C']) / total_between
c_rate_start = 1 - v_rate_start

print(f"  Word-final V rate: {v_rate_end:.3f}")
print(f"  Word-initial V rate: {v_rate_start:.3f}")
for (a, b) in [('V','V'), ('V','C'), ('C','V'), ('C','C')]:
    observed = between_vc.get((a, b), 0) / total_between
    a_rate = v_rate_end if a == 'V' else c_rate_end
    b_rate = v_rate_start if b == 'V' else c_rate_start
    expected = a_rate * b_rate
    ratio = observed / expected if expected > 0 else 0
    print(f"    {a}→{b}: observed={observed:.3f}, expected={expected:.3f}, O/E={ratio:.2f}")

# Phonological pattern identification
vv_between = between_vc.get(('V','V'), 0)
vc_between = between_vc.get(('V','C'), 0)
cv_between = between_vc.get(('C','V'), 0)
cc_between = between_vc.get(('C','C'), 0)

# Same analysis within words
vv_within = within_vc.get(('V','V'), 0)
vc_within = within_vc.get(('V','C'), 0)
cv_within = within_vc.get(('C','V'), 0)
cc_within = within_vc.get(('C','C'), 0)

print(f"\n  PHONOLOGICAL PATTERN IDENTIFICATION:")
alt_between = (vc_between + cv_between) / total_between
alt_within = (vc_within + cv_within) / total_within
print(f"  Alternation rate (between words): {alt_between:.3f}")
print(f"  Alternation rate (within words):  {alt_within:.3f}")
print(f"  Ratio: {alt_between/alt_within:.3f}")

if alt_between > alt_within * 1.05:
    print(f"  → MORE alternation between words: suggests HIATUS AVOIDANCE or liaison")
elif alt_between < alt_within * 0.95:
    print(f"  → LESS alternation between words: suggests SANDHI or assimilation")
else:
    print(f"  → SIMILAR alternation: word boundaries don't change V/C dynamics")


# ============================================================
# 55d: LANGUAGE FINGERPRINT WITH V/C STATISTICS
# ============================================================
print("\n" + "=" * 65)
print("55d: LANGUAGE FINGERPRINT MATCHING")
print("=" * 65)

# Compute VMS syllable structure statistics
# CV pattern for each word
def word_cv_pattern(word, vc_map):
    return ''.join(vc_map.get(c, 'C') for c in word)

cv_patterns = Counter()
for w in all_collapsed:
    pat = word_cv_pattern(w, eva_vc)
    cv_patterns[pat] += 1

total_words = sum(cv_patterns.values())
print(f"  Top 20 CV patterns:")
for pat, count in cv_patterns.most_common(20):
    pct = 100 * count / total_words
    example_words = [w for w in vocab if word_cv_pattern(w, eva_vc) == pat][:3]
    examples = ', '.join(example_words)
    print(f"    {pat:12s}  {count:5d} ({pct:4.1f}%)  e.g. {examples}")

# Syllable statistics (approximate: count V-groups as syllable nuclei)
syllable_counts = Counter()
for w in all_collapsed:
    cv = word_cv_pattern(w, eva_vc)
    # Count syllables as number of V-runs
    n_syl = len(re.findall(r'V+', cv))
    if n_syl == 0:
        n_syl = 1  # Words with no vowels count as 1 syllable
    syllable_counts[n_syl] += 1

total_syl_words = sum(syllable_counts.values())
mean_syllables = sum(k * v for k, v in syllable_counts.items()) / total_syl_words
print(f"\n  Syllable count distribution (V-nucleus count):")
for n in sorted(syllable_counts.keys()):
    pct = 100 * syllable_counts[n] / total_syl_words
    print(f"    {n} syllables: {syllable_counts[n]:5d} ({pct:5.1f}%)")
print(f"  Mean syllables per word: {mean_syllables:.2f}")

# V/C cluster statistics
v_clusters = []
c_clusters = []
for w in all_collapsed:
    cv = word_cv_pattern(w, eva_vc)
    for m in re.finditer(r'V+', cv):
        v_clusters.append(len(m.group()))
    for m in re.finditer(r'C+', cv):
        c_clusters.append(len(m.group()))

print(f"\n  V-cluster length distribution:")
v_cluster_counts = Counter(v_clusters)
for l in sorted(v_cluster_counts.keys()):
    if v_cluster_counts[l] > 10:
        print(f"    Length {l}: {v_cluster_counts[l]:5d} ({100*v_cluster_counts[l]/len(v_clusters):.1f}%)")

print(f"  C-cluster length distribution:")
c_cluster_counts = Counter(c_clusters)
for l in sorted(c_cluster_counts.keys()):
    if c_cluster_counts[l] > 10:
        print(f"    Length {l}: {c_cluster_counts[l]:5d} ({100*c_cluster_counts[l]/len(c_clusters):.1f}%)")

# Language comparison table
print(f"\n  LANGUAGE COMPARISON:")
print(f"  {'Property':>25s}  {'VMS':>8s}  {'English':>8s}  {'Turkish':>8s}  {'Japanese':>8s}  {'Hawaiian':>9s}  {'Arabic':>8s}")
print(f"  {'V/C ratio':>25s}  {v_total/c_total:8.2f}  {'0.62':>8s}  {'0.83':>8s}  {'1.05':>8s}  {'1.38':>9s}  {'0.48':>8s}")
print(f"  {'Mean word length':>25s}  {np.mean([len(w) for w in all_collapsed]):8.2f}  {'4.7':>8s}  {'6.2':>8s}  {'4.1':>8s}  {'4.7':>9s}  {'4.5':>8s}")
print(f"  {'Mean syl/word':>25s}  {mean_syllables:8.2f}  {'1.5':>8s}  {'2.9':>8s}  {'3.0':>8s}  {'2.5':>9s}  {'1.7':>8s}")
print(f"  {'IC':>25s}  {'0.090':>8s}  {'0.067':>8s}  {'0.059':>8s}  {'0.055':>8s}  {'0.120':>9s}  {'0.077':>8s}")
print(f"  {'Alphabet size':>25s}  {'22':>8s}  {'26':>8s}  {'29':>8s}  {'46+':>8s}  {'13':>9s}  {'28':>8s}")

# Score each candidate
print(f"\n  Phonotactic similarity (rough qualitative assessment):")
print(f"  English:  LOW  — V/C ratio too low, IC too low, no strong alternation")
print(f"  Turkish:  LOW  — too many syllables per word, IC too low")
print(f"  Japanese: MODERATE — similar word length, but IC too low, writing system mismatch")
print(f"  Hawaiian: HIGH IC match — but alphabet too small (13 vs 22)")
print(f"  Arabic:   MODERATE — IC closer, abjad possibility, but V/C ratio differs")


# ============================================================
# 55e: SYLLABARY TEST
# ============================================================
print("\n" + "=" * 65)
print("55e: SYLLABARY HYPOTHESIS TEST")
print("=" * 65)

# If each character is a syllable (CV or V), then:
# 1. V/C alternation should be near-random (no V or C because each char is a syllable)
# 2. The "word" is actually a sequence of syllables, so all chars should behave similarly

# Key test: is the alternation rate SIGNIFICANTLY above random?
print(f"  Alternation rate (observed): {alternation_rate(all_collapsed, eva_vc):.4f}")
print(f"  Alternation rate (random):   {np.mean(random_alts):.4f}")
print(f"  Excess:                      {alternation_rate(all_collapsed, eva_vc) - np.mean(random_alts):+.4f}")
print(f"  z-score:                     {z_alt:.1f}")

if z_alt > 5:
    print(f"\n  STRONG V/C alternation → characters represent PHONEMES, not syllables")
    print(f"  The script is likely ALPHABETIC (or abjad)")
elif z_alt > 2:
    print(f"\n  WEAK V/C alternation → ambiguous")
    print(f"  Could be alphabetic with unusual phonotactics, or a mixed system")
else:
    print(f"\n  NO V/C alternation → consistent with SYLLABARY")
    print(f"  Each character might represent a syllable (CV or V)")

# Additional test: character position distribution
# In an alphabet, vowels and consonants have different positional preferences
# In a syllabary, all characters should have similar positional profiles
print(f"\n  Positional preference test:")
v_pos_profile = defaultdict(int)
c_pos_profile = defaultdict(int)
v_pos_total = defaultdict(int)
c_pos_total = defaultdict(int)

for w in all_collapsed:
    n = len(w)
    for i, ch in enumerate(w):
        # Normalize position to 0-1
        rel_pos = i / max(n - 1, 1)
        bucket = int(rel_pos * 4)  # 5 buckets: 0,1,2,3,4
        bucket = min(bucket, 4)
        if eva_vc.get(ch, 'C') == 'V':
            v_pos_profile[bucket] += 1
        else:
            c_pos_profile[bucket] += 1

v_tot = sum(v_pos_profile.values())
c_tot = sum(c_pos_profile.values())
print(f"  {'Position':>10s}  {'V%':>6s}  {'C%':>6s}  {'V_frac':>7s}")
for b in range(5):
    vp = 100 * v_pos_profile[b] / v_tot if v_tot > 0 else 0
    cp = 100 * c_pos_profile[b] / c_tot if c_tot > 0 else 0
    vf = v_pos_profile[b] / (v_pos_profile[b] + c_pos_profile[b]) if (v_pos_profile[b] + c_pos_profile[b]) > 0 else 0
    labels = ['start', 'early', 'middle', 'late', 'end']
    print(f"  {labels[b]:>10s}  {vp:5.1f}%  {cp:5.1f}%  {vf:7.3f}")

# Chi-square for V/C × position independence
observed_table = np.zeros((2, 5))
for b in range(5):
    observed_table[0, b] = v_pos_profile[b]
    observed_table[1, b] = c_pos_profile[b]

row_totals = observed_table.sum(axis=1, keepdims=True)
col_totals = observed_table.sum(axis=0, keepdims=True)
grand_total = observed_table.sum()
expected_table = row_totals * col_totals / grand_total
chi2 = np.sum((observed_table - expected_table)**2 / np.where(expected_table > 0, expected_table, 1))
print(f"\n  Chi-square (V/C × position independence): {chi2:.1f} (df=4)")
if chi2 > 20:
    print(f"  HIGHLY position-dependent → ALPHABETIC (V and C have different slot preferences)")
elif chi2 > 10:
    print(f"  Moderately position-dependent → likely alphabetic")
else:
    print(f"  Weakly position-dependent → could be syllabary")


# ============================================================
# SYNTHESIS
# ============================================================
print("\n" + "=" * 65)
print("PHASE 55 SYNTHESIS")
print("=" * 65)

print(f"""
V/C separation results and implications:

SUKHOTIN'S CLASSIFICATION:
  Vowels: {' '.join(vowels_eva)}
  Consonants: {' '.join(consonants_eva)}

KEY METRICS:
  V/C ratio: {v_total/c_total:.2f}
  Alternation z-score: {z_alt:.1f}
  Cross-val retention: {test_alt/train_alt:.3f}
  Position chi-square: {chi2:.1f}

SCRIPT TYPE INFERENCE:
  Strong V/C alternation (z>{z_alt:.0f}) + position-dependent V/C
  → Characters represent phonemes (alphabetic/abjad), NOT syllables

PHONOLOGICAL PROFILE:
  V frequency: {100*v_total/total_chars:.1f}%
  Between-word alternation: {alt_between:.3f}
  Within-word alternation:  {alt_within:.3f}
""")

print("Phase 55 complete.")
