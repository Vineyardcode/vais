#!/usr/bin/env python3
"""
NATURAL LANGUAGE vs. SYLLABLE CIPHER
==================================================

cipher_identification_tests narrowed to two hypotheses:
  A) Natural language with non-European phonotactics
  B) Syllable cipher (each VMS word = one plaintext syllable)

Key insight: in natural language, within-word and between-word character
transitions come from the SAME phonological system. In a cipher, they
come from DIFFERENT processes (encoding rules vs. plaintext transitions).

  A) WITHIN-WORD vs BETWEEN-WORD TRANSITION MATRICES
       Compare the full C×C character transition matrices for transitions
       occurring WITHIN words vs BETWEEN words (last char → first char).
       High correlation → same process → natural language.
       Low correlation → different processes → cipher.

  B) CROSS-PREDICTION TEST
       Train char bigram on within-word transitions only, evaluate on
       between-word transitions (and vice versa). If same process,
       cross-prediction should be nearly as good as self-prediction.

  C) WORD LENGTH AUTOCORRELATION
       In natural language, short function words alternate with long
       content words → length correlation > 0. In syllable cipher,
       word length is encoding artifact → correlation ≈ 0.

  D) HAPAX CLUSTERING
       Natural language hapaxes are topic-specific → concentrated in
       certain sections. Cipher hapaxes are encoding accidents →
       uniformly distributed.

  E) CONDITIONAL WORD-LENGTH ENTROPY
       H(length_i+1 | length_i). In natural language, word length
       carries grammatical information → conditional H should be lower
       than marginal H. In cipher, length is about encoding → no gain.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_e, compute_H, get_collapsed, strip_gallows_v2 as strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(54)
np.random.seed(54)

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']


FOLIO_DIR = Path("folios")

# Locus-type filter (2026-07-19, after the Part-D hapax audit): [] keeps
# every locus (the test's original behavior — includes ring/label/radial
# material, which is hapax-enriched and layout-clustered); ['P'] restricts
# to continuous paragraph text. See hapax_locus_readjudication for the
# registered re-adjudication of Part D under both settings.
LOCUS_TYPES = []

def load_lines_with_folios():
    """Load lines with folio provenance for section analysis."""
    lines = []
    folios = []
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        folio_name = fpath.stem
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'): continue
            m = re.match(r'<([^>]+)>', line)
            if LOCUS_TYPES and m:
                tm = re.search(r',[@+*=]?([A-Za-z])', m.group(1))
                if not tm or tm.group(1).upper() not in LOCUS_TYPES:
                    continue
            rest = line[m.end():].strip() if m else line
            if not rest: continue
            words = [w.strip() for w in re.split(r'[.\s,;]+', rest)
                     if w.strip() and re.match(r'^[a-z]+$', w.strip())]
            if len(words) >= 2:
                lines.append(words)
                folios.append(folio_name)
    return lines, folios


# Section mapping
def get_section(folio):
    """Simple section classifier based on folio number."""
    try:
        num = int(re.match(r'f(\d+)', folio).group(1))
    except:
        return 'unknown'
    if num <= 56:
        return 'herbal'
    elif num <= 67:
        return 'astro'
    elif num <= 73:
        return 'cosmo'
    elif num <= 84:
        return 'bio'
    elif num <= 86:
        return 'cosmo2'
    elif num <= 102:
        return 'pharma'
    else:
        return 'text'

print("Loading corpus...")
raw_lines, folios = load_lines_with_folios()
line_collapsed = [[get_collapsed(w) for w in line] for line in raw_lines]
all_collapsed = [w for seq in line_collapsed for w in seq]
N = len(all_collapsed)
vocab = Counter(all_collapsed)
print(f"  {N} tokens, {len(vocab)} types, {len(raw_lines)} lines\n")


# ============================================================
# 54a: WITHIN-WORD vs BETWEEN-WORD TRANSITION MATRICES
# ============================================================
print("=" * 65)
print("A: WITHIN-WORD vs BETWEEN-WORD TRANSITION MATRICES")
print("=" * 65)

# Build within-word and between-word transition matrices
within_bi = Counter()  # (char_i, char_i+1) within same word
within_ctx = Counter()
between_bi = Counter()  # (last_char_of_w1, first_char_of_w2)
between_ctx = Counter()

for line in line_collapsed:
    # Within-word
    for w in line:
        for i in range(len(w) - 1):
            within_bi[(w[i], w[i+1])] += 1
            within_ctx[w[i]] += 1
    # Between-word (adjacent words)
    for i in range(len(line) - 1):
        if line[i] and line[i+1]:
            last_c = line[i][-1]
            first_c = line[i+1][0]
            between_bi[(last_c, first_c)] += 1
            between_ctx[last_c] += 1

# Get all characters
all_chars = sorted(set(c for w in all_collapsed for c in w))
n_chars = len(all_chars)
char_idx = {c: i for i, c in enumerate(all_chars)}

# Build normalized transition matrices
within_matrix = np.zeros((n_chars, n_chars))
between_matrix = np.zeros((n_chars, n_chars))

for (c1, c2), count in within_bi.items():
    total = within_ctx[c1]
    if total > 0:
        within_matrix[char_idx[c1], char_idx[c2]] = count / total

for (c1, c2), count in between_bi.items():
    total = between_ctx[c1]
    if total > 0:
        between_matrix[char_idx[c1], char_idx[c2]] = count / total

# Compare matrices
# Only compare rows where both matrices have data
valid_rows = []
for i, c in enumerate(all_chars):
    if within_ctx[c] >= 50 and between_ctx[c] >= 50:
        valid_rows.append(i)

if valid_rows:
    w_sub = within_matrix[valid_rows, :]
    b_sub = between_matrix[valid_rows, :]
    
    # Flatten and correlate
    w_flat = w_sub.flatten()
    b_flat = b_sub.flatten()
    
    # Remove zero-zero pairs for meaningful correlation
    mask = (w_flat > 0) | (b_flat > 0)
    if np.sum(mask) > 10:
        corr = np.corrcoef(w_flat[mask], b_flat[mask])[0, 1]
        print(f"  Correlation(within-word, between-word) = {corr:.4f}")
        print(f"  Using {len(valid_rows)} characters with >=50 obs in both contexts")
        print(f"  Active cells: {np.sum(mask)} (of {len(mask)})")
    
    # Row-by-row correlation (per character)
    print(f"\n  Per-character correlation (successor distribution within vs between):")
    print(f"  {'Char':>5s}  {'Within_N':>9s}  {'Between_N':>10s}  {'Corr':>7s}  {'Note':>10s}")
    row_corrs = []
    for idx in valid_rows:
        c = all_chars[idx]
        w_row = within_matrix[idx, :]
        b_row = between_matrix[idx, :]
        mask_r = (w_row > 0) | (b_row > 0)
        if np.sum(mask_r) >= 3:
            r = np.corrcoef(w_row[mask_r], b_row[mask_r])[0, 1]
            if not np.isnan(r):
                row_corrs.append((c, within_ctx[c], between_ctx[c], r))
    
    row_corrs.sort(key=lambda x: -x[3])
    for c, wn, bn, r in row_corrs:
        note = 'SIMILAR' if r > 0.5 else 'DIFFERENT' if r < 0.2 else 'MODERATE'
        print(f"  {c:>5s}  {wn:9d}  {bn:10d}  {r:7.3f}  {note:>10s}")
    
    mean_corr = np.mean([x[3] for x in row_corrs])
    print(f"\n  Mean per-character correlation: {mean_corr:.3f}")
    print(f"  Interpretation:")
    print(f"    > 0.5: Same process (natural language)")
    print(f"    0.2-0.5: Partially overlapping (ambiguous)")
    print(f"    < 0.2: Different processes (cipher)")

    # Jensen-Shannon divergence between matrices
    print(f"\n  Jensen-Shannon Divergence per character:")
    jsd_values = []
    for idx in valid_rows:
        c = all_chars[idx]
        w_row = within_matrix[idx, :] + 1e-10
        b_row = between_matrix[idx, :] + 1e-10
        w_row = w_row / w_row.sum()
        b_row = b_row / b_row.sum()
        m_row = (w_row + b_row) / 2
        jsd = 0.5 * np.sum(w_row * np.log2(w_row / m_row)) + \
              0.5 * np.sum(b_row * np.log2(b_row / m_row))
        jsd_values.append((c, jsd))
    
    jsd_values.sort(key=lambda x: x[1])
    print(f"  Mean JSD = {np.mean([x[1] for x in jsd_values]):.4f}")
    print(f"  Most similar: {jsd_values[0][0]} (JSD={jsd_values[0][1]:.4f})")
    print(f"  Most different: {jsd_values[-1][0]} (JSD={jsd_values[-1][1]:.4f})")


# ============================================================
# 54b: CROSS-PREDICTION TEST
# ============================================================
print("\n" + "=" * 65)
print("B: CROSS-PREDICTION TEST")
print("=" * 65)

# Split data
half = len(line_collapsed) // 2
train_lines = line_collapsed[:half]
test_lines = line_collapsed[half:]

# Train within-word model
w_bi = Counter()
w_ctx = Counter()
for line in train_lines:
    for w in line:
        for i in range(len(w) - 1):
            w_bi[(w[i], w[i+1])] += 1
            w_ctx[w[i]] += 1

# Train between-word model
b_bi = Counter()
b_ctx = Counter()
for line in train_lines:
    for i in range(len(line) - 1):
        if line[i] and line[i+1]:
            last_c = line[i][-1]
            first_c = line[i+1][0]
            b_bi[(last_c, first_c)] += 1
            b_ctx[last_c] += 1

# Train combined model
c_bi = Counter()
c_ctx = Counter()
for line in train_lines:
    for w in line:
        for i in range(len(w) - 1):
            c_bi[(w[i], w[i+1])] += 1
            c_ctx[w[i]] += 1
    for i in range(len(line) - 1):
        if line[i] and line[i+1]:
            last_c = line[i][-1]
            first_c = line[i+1][0]
            c_bi[(last_c, first_c)] += 1
            c_ctx[last_c] += 1

def eval_model(model_bi, model_ctx, test_pairs):
    """Evaluate a bigram model on test pairs."""
    total_lp = 0.0
    n = 0
    unseen = 0
    for c1, c2 in test_pairs:
        bc = model_bi.get((c1, c2), 0)
        cc = model_ctx.get(c1, 0)
        if bc > 0 and cc > 0:
            total_lp += -math.log2(bc / cc)
        else:
            total_lp += 10.0  # penalty
            unseen += 1
        n += 1
    return total_lp / n if n > 0 else 999, unseen / n if n > 0 else 1

# Collect test pairs
test_within_pairs = []
test_between_pairs = []
for line in test_lines:
    for w in line:
        for i in range(len(w) - 1):
            test_within_pairs.append((w[i], w[i+1]))
    for i in range(len(line) - 1):
        if line[i] and line[i+1]:
            test_between_pairs.append((line[i][-1], line[i+1][0]))

# Evaluate all models on both test sets
print(f"  Test within-word pairs: {len(test_within_pairs)}")
print(f"  Test between-word pairs: {len(test_between_pairs)}")

print(f"\n  {'Model':>15s}  {'On Within':>10s}  {'On Between':>11s}  {'Unseen_W':>9s}  {'Unseen_B':>9s}")

for name, m_bi, m_ctx in [('Within-word', w_bi, w_ctx),
                           ('Between-word', b_bi, b_ctx),
                           ('Combined', c_bi, c_ctx)]:
    hw, uw = eval_model(m_bi, m_ctx, test_within_pairs)
    hb, ub = eval_model(m_bi, m_ctx, test_between_pairs)
    print(f"  {name:>15s}  {hw:10.3f}  {hb:11.3f}  {uw:8.1%}  {ub:8.1%}")

# Cross-prediction quality
hw_self, _ = eval_model(w_bi, w_ctx, test_within_pairs)
hw_cross, _ = eval_model(w_bi, w_ctx, test_between_pairs)
hb_self, _ = eval_model(b_bi, b_ctx, test_between_pairs)
hb_cross, _ = eval_model(b_bi, b_ctx, test_within_pairs)

print(f"\n  Cross-prediction analysis:")
print(f"  Within→Within:  {hw_self:.3f} bits/char (self)")
print(f"  Within→Between: {hw_cross:.3f} bits/char (cross)")
print(f"  Cross penalty:  {hw_cross - hw_self:+.3f} bits")
print(f"  Between→Between: {hb_self:.3f} bits/char (self)")
print(f"  Between→Within:  {hb_cross:.3f} bits/char (cross)")
print(f"  Cross penalty:   {hb_cross - hb_self:+.3f} bits")

cross_penalty_avg = ((hw_cross - hw_self) + (hb_cross - hb_self)) / 2
print(f"\n  Average cross-prediction penalty: {cross_penalty_avg:+.3f} bits")
print(f"  Interpretation:")
print(f"    Small penalty (<0.5): Similar processes (natural language)")
print(f"    Large penalty (>1.0): Different processes (cipher)")


# ============================================================
# 54c: WORD LENGTH AUTOCORRELATION
# ============================================================
print("\n" + "=" * 65)
print("C: WORD LENGTH AUTOCORRELATION")
print("=" * 65)

# Compute adjacent word length correlation within lines
len_pairs = []
for line in line_collapsed:
    lengths = [len(w) for w in line]
    for i in range(len(lengths) - 1):
        len_pairs.append((lengths[i], lengths[i+1]))

len1 = np.array([p[0] for p in len_pairs])
len2 = np.array([p[1] for p in len_pairs])
len_corr = np.corrcoef(len1, len2)[0, 1]

print(f"  Adjacent word length pairs: {len(len_pairs)}")
print(f"  Correlation(len_i, len_{'{'}i+1{'}'}) = {len_corr:.4f}")

# Permutation test
perm_corrs = []
for _ in range(1000):
    perm_len2 = np.random.permutation(len2)
    perm_corrs.append(np.corrcoef(len1, perm_len2)[0, 1])

z_len = (len_corr - np.mean(perm_corrs)) / np.std(perm_corrs)
print(f"  Permutation null: {np.mean(perm_corrs):.4f} ± {np.std(perm_corrs):.4f}")
print(f"  z-score = {z_len:.1f}")
print(f"  Direction: {'POSITIVE (adjacent lengths correlate)' if z_len > 2 else 'NEGATIVE (lengths anti-correlate)' if z_len < -2 else 'NO SIGNIFICANT CORRELATION'}")

# Also: correlation at different gaps
print(f"\n  Length correlation at different gaps:")
for gap in [1, 2, 3, 4, 5]:
    gap_pairs = []
    for line in line_collapsed:
        lengths = [len(w) for w in line]
        for i in range(len(lengths) - gap):
            gap_pairs.append((lengths[i], lengths[i+gap]))
    if len(gap_pairs) > 100:
        g1 = np.array([p[0] for p in gap_pairs])
        g2 = np.array([p[1] for p in gap_pairs])
        gc = np.corrcoef(g1, g2)[0, 1]
        print(f"    Gap {gap}: r = {gc:.4f} ({len(gap_pairs)} pairs)")

# Word length → next word identity MI
# H(next_word | length_prev) vs H(next_word)
H_word = compute_H(vocab, N)
length_groups = defaultdict(Counter)
for line in line_collapsed:
    for i in range(len(line) - 1):
        length_groups[len(line[i])][line[i+1]] += 1

H_cond = 0.0
total_cond = sum(sum(c.values()) for c in length_groups.values())
for length, next_counts in length_groups.items():
    group_total = sum(next_counts.values())
    weight = group_total / total_cond
    H_cond += weight * compute_H(next_counts, group_total)

MI_len_word = H_word - H_cond
print(f"\n  MI(prev_word_length, next_word):")
print(f"  H(next_word) = {H_word:.3f}")
print(f"  H(next_word | prev_length) = {H_cond:.3f}")
print(f"  MI = {MI_len_word:.4f} bits ({100*MI_len_word/H_word:.2f}% of H)")


# ============================================================
# 54d: HAPAX CLUSTERING
# ============================================================
print("\n" + "=" * 65)
print("D: HAPAX CLUSTERING")
print("=" * 65)

# Identify hapaxes and their folio/section locations
hapaxes = {w for w, c in vocab.items() if c == 1}
print(f"  Total hapaxes: {len(hapaxes)} ({100*len(hapaxes)/len(vocab):.1f}% of types)")

# Find section for each hapax
section_hapax_counts = Counter()
section_total_tokens = Counter()
section_total_types = defaultdict(set)

for line_idx, (line, folio) in enumerate(zip(line_collapsed, folios)):
    section = get_section(folio)
    for w in line:
        section_total_tokens[section] += 1
        section_total_types[section].add(w)
        if w in hapaxes:
            section_hapax_counts[section] += 1

print(f"\n  Hapax distribution by section:")
print(f"  {'Section':>10s}  {'Tokens':>7s}  {'Types':>6s}  {'Hapaxes':>8s}  {'Hapax/Type':>11s}  {'Hapax/Token':>12s}")
for section in sorted(section_hapax_counts.keys()):
    tokens = section_total_tokens[section]
    types = len(section_total_types[section])
    hapax = section_hapax_counts[section]
    print(f"  {section:>10s}  {tokens:7d}  {types:6d}  {hapax:8d}  {hapax/types:10.1%}  {hapax/tokens:11.3%}")

# Concentration test: are hapaxes more concentrated than expected?
# Chi-square test: observed hapax counts vs expected (proportional to tokens)
total_hapax = sum(section_hapax_counts.values())
total_tok = sum(section_total_tokens.values())
expected = {s: total_hapax * section_total_tokens[s] / total_tok
            for s in section_hapax_counts}

chi2 = sum((section_hapax_counts[s] - expected[s])**2 / max(expected[s], 1)
           for s in section_hapax_counts)
df = len(section_hapax_counts) - 1
print(f"\n  Chi-square (hapax concentration) = {chi2:.1f} (df={df})")
print(f"  {'CONCENTRATED (non-uniform)' if chi2 > 15 else 'UNIFORM (consistent with cipher)'}")

# Spatial clustering: are hapaxes clustered in consecutive lines?
hapax_line_positions = []
for line_idx, line in enumerate(line_collapsed):
    for w in line:
        if w in hapaxes:
            hapax_line_positions.append(line_idx)

if len(hapax_line_positions) > 10:
    gaps = np.diff(hapax_line_positions)
    mean_gap = np.mean(gaps)
    std_gap = np.std(gaps)
    B_hapax = (std_gap - mean_gap) / (std_gap + mean_gap) if (std_gap + mean_gap) > 0 else 0
    print(f"\n  Hapax spatial distribution:")
    print(f"  Mean inter-hapax gap: {mean_gap:.1f} lines")
    print(f"  Burstiness B = {B_hapax:.3f}")
    print(f"  {'CLUSTERED (topic-specific)' if B_hapax > 0.1 else 'UNIFORM (encoding artifact)' if B_hapax < 0.05 else 'MILDLY CLUSTERED'}")


# ============================================================
# 54e: CONDITIONAL WORD-LENGTH ENTROPY
# ============================================================
print("\n" + "=" * 65)
print("E: CONDITIONAL WORD-LENGTH ENTROPY")
print("=" * 65)

# H(length_i+1 | length_i) vs H(length)
length_marginal = Counter()
length_bigram = Counter()
length_ctx = Counter()

for line in line_collapsed:
    lengths = [len(w) for w in line]
    for l in lengths:
        length_marginal[l] += 1
    for i in range(len(lengths) - 1):
        length_bigram[(lengths[i], lengths[i+1])] += 1
        length_ctx[lengths[i]] += 1

total_lengths = sum(length_marginal.values())
H_length = compute_H(length_marginal, total_lengths)

total_length_bi = sum(length_bigram.values())
H_length_joint = compute_H(length_bigram, total_length_bi)
H_length_ctx = compute_H(length_ctx, sum(length_ctx.values()))
H_length_cond = H_length_joint - H_length_ctx
MI_length = H_length - H_length_cond

print(f"  H(word_length) = {H_length:.4f} bits")
print(f"  H(word_length | prev_length) = {H_length_cond:.4f} bits")
print(f"  MI(length_i, length_i+1) = {MI_length:.4f} bits")
print(f"  MI/H = {MI_length/H_length:.4f}")

# Permutation test for MI
perm_mi = []
for _ in range(1000):
    perm_lines = []
    for line in line_collapsed:
        perm_line = list(line)
        random.shuffle(perm_line)
        perm_lines.append(perm_line)
    
    p_bi = Counter()
    p_ctx = Counter()
    for line in perm_lines:
        lengths = [len(w) for w in line]
        for i in range(len(lengths) - 1):
            p_bi[(lengths[i], lengths[i+1])] += 1
            p_ctx[lengths[i]] += 1
    
    p_total = sum(p_bi.values())
    p_H_joint = compute_H(p_bi, p_total)
    p_H_ctx = compute_H(p_ctx, sum(p_ctx.values()))
    p_mi = H_length - (p_H_joint - p_H_ctx)
    perm_mi.append(p_mi)

z_mi = (MI_length - np.mean(perm_mi)) / np.std(perm_mi) if np.std(perm_mi) > 0 else 0
print(f"  Permutation null MI: {np.mean(perm_mi):.4f} ± {np.std(perm_mi):.4f}")
print(f"  z-score = {z_mi:.1f}")
print(f"  {'SIGNIFICANT: lengths carry order info' if z_mi > 3 else 'NOT SIGNIFICANT: lengths not ordered'}")

# Length transition matrix
print(f"\n  Most skewed length transitions (observed/expected ratio):")
transitions = []
for (l1, l2), count in length_bigram.items():
    expected = length_ctx[l1] * length_marginal[l2] / total_lengths
    if expected > 5:
        ratio = count / expected
        transitions.append((l1, l2, count, expected, ratio))

transitions.sort(key=lambda x: -abs(x[4] - 1))
print(f"  {'L1→L2':>8s}  {'Obs':>6s}  {'Exp':>7s}  {'Ratio':>6s}")
for l1, l2, obs, exp, ratio in transitions[:10]:
    print(f"  {l1:3d}→{l2:<3d}  {obs:6d}  {exp:7.1f}  {ratio:6.2f}")


# ============================================================
# SYNTHESIS
# ============================================================
print("\n" + "=" * 65)
print("language_vs_cipher SYNTHESIS")
print("=" * 65)
print("""
Natural Language vs. Syllable Cipher discrimination:

54a: Are within-word and between-word char transitions from same process?
54b: Can within-word model predict between-word transitions (and vice versa)?
54c: Are adjacent word lengths correlated (natural language feature)?
54d: Are hapaxes topic-clustered (natural language) or uniform (cipher)?
54e: Does word length carry sequential information?
""")

print("language_vs_cipher complete.")
