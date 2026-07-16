#!/usr/bin/env python3
"""
STRESS TEST: BIGRAM NULL MODEL & INFORMATION DECOMPOSITION
======================================================================

The deepest remaining skeptical question: Can character-level bigram
constraints explain the observed prefix↔suffix association (MI=0.19 bits)?
If yes, the "morphological system" collapses to phonotactics.

Sub-analyses:
  A) BIGRAM NULL MODEL
       Fit character bigrams from collapsed Voynich words.
       Generate synthetic words from bigram model, matching length dist.
       Compute MI(prefix_group, suffix_group) on synthetic data.
       If synthetic MI ≈ observed MI → morphology is just phonotactics.

  B) MI BY WORD LENGTH
       If prefix↔suffix MI comes from adjacent characters, it should
       decay for long words where prefix and suffix are far apart.
       If MI persists for long words → genuine long-range structure.

  C) ch- VS sh-: ALLOMORPHS OR DISTINCT?
       parser_free_morphology showed ch- is "phonotactic." Does ch- differ from sh-
       in ANY measurable way? Suffix selection, section, position?
       If indistinguishable → allomorphs. If different → distinct.

  D) INFORMATION DECOMPOSITION
       How much of section/position can be predicted from word edges?
       MI(section, prefix), MI(section, suffix), MI(section, both)
       MI(position, prefix), MI(position, suffix)
       This reveals what Voynich word edges actually encode.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import collapse_echains, compute_mi, gallows_base, strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(42)
np.random.seed(42)

# ══════════════════════════════════════════════════════════════════
# CONSTANTS & HELPERS
# ══════════════════════════════════════════════════════════════════

SIMPLE_GALLOWS = ["t","k","f","p"]
BENCH_GALLOWS  = ["cth","ckh","cph","cfh"]
COMPOUND_GCH   = ["tch","kch","pch","fch"]
COMPOUND_GSH   = ["tsh","ksh","psh","fsh"]
ALL_GALLOWS    = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']




def get_collapsed(word):
    stripped, gals = strip_gallows(word)
    return collapse_echains(stripped), [gallows_base(g) for g in gals]

def get_prefix_group(w):
    """Match longest known prefix from collapsed form."""
    for p in ['qo','lch','lsh','sh','ch','so','do','q','o','d','y','l']:
        if w.startswith(p):
            return p
    return 'NONE'

def get_suffix_group(w):
    """Match longest known suffix from collapsed form."""
    for sf in SUFFIXES:
        if w.endswith(sf) and len(w) > len(sf):
            return sf
    return '∅'


def cramers_v(x_arr, y_arr):
    """Cramér's V between two categorical arrays."""
    x_vals = sorted(set(x_arr))
    y_vals = sorted(set(y_arr))
    if len(x_vals) < 2 or len(y_vals) < 2: return 0.0
    x_map = {v:i for i,v in enumerate(x_vals)}
    y_map = {v:i for i,v in enumerate(y_vals)}
    table = np.zeros((len(x_vals), len(y_vals)))
    for xi, yi in zip(x_arr, y_arr):
        table[x_map[xi]][y_map[yi]] += 1
    N = table.sum()
    row_sums = table.sum(axis=1, keepdims=True)
    col_sums = table.sum(axis=0, keepdims=True)
    expected = row_sums * col_sums / N
    mask = expected > 0
    chi2 = np.sum((table[mask] - expected[mask])**2 / expected[mask])
    r, c = table.shape
    denom = N * (min(r, c) - 1)
    return math.sqrt(chi2 / denom) if denom > 0 else 0

def entropy(arr):
    """Shannon entropy of a categorical array."""
    N = len(arr)
    if N == 0: return 0.0
    counts = Counter(arr)
    h = 0.0
    for c in counts.values():
        p = c / N
        if p > 0:
            h -= p * math.log2(p)
    return h

def cond_entropy(x_arr, y_arr):
    """H(Y|X) — entropy of Y given X."""
    N = len(x_arr)
    if N == 0: return 0.0
    groups = defaultdict(list)
    for x, y in zip(x_arr, y_arr):
        groups[x].append(y)
    h = 0.0
    for x_val, ys in groups.items():
        p_x = len(ys) / N
        h += p_x * entropy(ys)
    return h


# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════

FOLIO_DIR = Path("folios")

def load_all_tokens():
    tokens = []
    section_map = {
        'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
        'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
    }
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        section = 'unknown'
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'):
                ll = line.lower()
                for key, val in section_map.items():
                    if key in ll:
                        section = val
                        if val == 'herbal' and '-b' in ll: section = 'herbal-B'
                        elif val == 'herbal': section = 'herbal-A'
                continue
            m = re.match(r'<([^>]+)>', line)
            if m:
                rest = line[m.end():].strip()
            else:
                rest = line
            if not rest: continue
            words = [w for w in re.split(r'[.\s,;]+', rest) if w.strip()]
            for i, word in enumerate(words):
                word = word.strip()
                if not word or not re.match(r'^[a-z]+$', word): continue
                pos = i / max(len(words)-1, 1) if len(words) > 1 else 0.5
                coll, gals = get_collapsed(word)
                tokens.append(dict(
                    word=word, section=section,
                    collapsed=coll, gallows=gals,
                    pos=pos, line_len=len(words),
                    word_idx=i
                ))
    return tokens


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

print("Loading tokens...")
tokens = load_all_tokens()
print(f"  {len(tokens)} tokens loaded")

# Compute observed prefix/suffix arrays
obs_pfx = [get_prefix_group(t['collapsed']) for t in tokens]
obs_sfx = [get_suffix_group(t['collapsed']) for t in tokens]
obs_mi = compute_mi(obs_pfx, obs_sfx)
obs_v = cramers_v(obs_pfx, obs_sfx)

print(f"  Observed MI(prefix, suffix) = {obs_mi:.4f} bits")
print(f"  Observed Cramér's V = {obs_v:.4f}")

# ══════════════════════════════════════════════════════════════════
# 38a: BIGRAM NULL MODEL
# ══════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("A: BIGRAM NULL MODEL")
print("    Can character bigrams explain prefix↔suffix MI?")
print("="*70)

# Fit character bigram model from collapsed forms
collapsed_forms = [t['collapsed'] for t in tokens]
word_lengths = [len(w) for w in collapsed_forms]

# Character bigrams: count transitions including START/END markers
START = '^'
END = '$'
bigram_counts = Counter()
unigram_counts = Counter()

for w in collapsed_forms:
    chars = [START] + list(w) + [END]
    for i in range(len(chars)-1):
        bigram_counts[(chars[i], chars[i+1])] += 1
        unigram_counts[chars[i]] += 1

# Build transition probabilities
all_chars = sorted(set(c for (c1,c2) in bigram_counts for c in [c1,c2]))
transition = {}  # P(next | current)
for c in all_chars:
    total = unigram_counts[c]
    if total == 0: continue
    nexts = {}
    for (c1, c2), count in bigram_counts.items():
        if c1 == c:
            nexts[c2] = count / total
    transition[c] = nexts

# Length distribution for sampling
length_dist = Counter(word_lengths)
length_probs = {l: c/len(word_lengths) for l, c in length_dist.items()}
max_len = max(word_lengths)

# Pre-compute transition arrays for fast sampling
_trans_cache = {}
for c in transition:
    items = [(c2, p) for c2, p in transition[c].items()]
    items_no_end = [(c2, p) for c2, p in items if c2 != END]
    _trans_cache[c] = {
        'all_chars': [x[0] for x in items],
        'all_probs': np.array([x[1] for x in items]),
        'ne_chars': [x[0] for x in items_no_end] if items_no_end else [x[0] for x in items],
        'ne_probs': np.array([x[1] for x in items_no_end]) if items_no_end else np.array([x[1] for x in items]),
    }
    # Normalize
    if _trans_cache[c]['ne_probs'].sum() > 0:
        _trans_cache[c]['ne_probs'] = _trans_cache[c]['ne_probs'] / _trans_cache[c]['ne_probs'].sum()
    if _trans_cache[c]['all_probs'].sum() > 0:
        _trans_cache[c]['all_probs'] = _trans_cache[c]['all_probs'] / _trans_cache[c]['all_probs'].sum()

def generate_bigram_word(target_length):
    """Generate a word from bigram model with target length."""
    chars = []
    current = START
    for _ in range(target_length + 10):
        tc = _trans_cache.get(current)
        if not tc:
            break
        if len(chars) < target_length and len(tc['ne_chars']) > 0:
            idx = np.searchsorted(np.cumsum(tc['ne_probs']), random.random())
            idx = min(idx, len(tc['ne_chars']) - 1)
            next_char = tc['ne_chars'][idx]
        elif len(chars) >= target_length:
            # Try to end
            if END in tc['all_chars']:
                return ''.join(chars)
            idx = np.searchsorted(np.cumsum(tc['ne_probs']), random.random())
            idx = min(idx, len(tc['ne_chars']) - 1)
            next_char = tc['ne_chars'][idx]
        else:
            idx = np.searchsorted(np.cumsum(tc['all_probs']), random.random())
            idx = min(idx, len(tc['all_chars']) - 1)
            next_char = tc['all_chars'][idx]
        if next_char == END:
            break
        chars.append(next_char)
        current = next_char
    return ''.join(chars) if chars else 'e'

def generate_synthetic_corpus(n_tokens):
    """Generate n synthetic words matching observed length distribution."""
    lengths = list(length_dist.keys())
    weights = [length_dist[l] for l in lengths]
    target_lengths = random.choices(lengths, weights=weights, k=n_tokens)

    words = []
    for tl in target_lengths:
        w = generate_bigram_word(tl)
        # Retry if empty or very wrong length
        attempts = 0
        while (not w or abs(len(w) - tl) > 2) and attempts < 5:
            w = generate_bigram_word(tl)
            attempts += 1
        words.append(w)
    return words

# Run simulation
N_SIM = 50
synthetic_mis = []
synthetic_vs = []

print(f"\n  Running {N_SIM} bigram simulations...")
for sim in range(N_SIM):
    syn_words = generate_synthetic_corpus(len(tokens))
    syn_pfx = [get_prefix_group(w) for w in syn_words]
    syn_sfx = [get_suffix_group(w) for w in syn_words]
    syn_mi = compute_mi(syn_pfx, syn_sfx)
    syn_v = cramers_v(syn_pfx, syn_sfx)
    synthetic_mis.append(syn_mi)
    synthetic_vs.append(syn_v)
    if (sim+1) % 10 == 0:
        print(f"    ... {sim+1}/{N_SIM} done")

syn_mi_mean = np.mean(synthetic_mis)
syn_mi_std = np.std(synthetic_mis)
syn_v_mean = np.mean(synthetic_vs)
syn_v_std = np.std(synthetic_vs)

z_mi = (obs_mi - syn_mi_mean) / max(syn_mi_std, 1e-10)
z_v = (obs_v - syn_v_mean) / max(syn_v_std, 1e-10)

print(f"\n  RESULTS:")
print(f"  {'Metric':<20} {'Observed':>10} {'Bigram null':>15} {'z-score':>10}")
print(f"  {'-'*55}")
print(f"  {'MI (bits)':<20} {obs_mi:>10.4f} {syn_mi_mean:>8.4f}±{syn_mi_std:.4f} {z_mi:>10.1f}")
print(f"  {'Cramér V':<20} {obs_v:>10.4f} {syn_v_mean:>8.4f}±{syn_v_std:.4f} {z_v:>10.1f}")

if z_mi < 2:
    verdict_38a = "BIGRAMS EXPLAIN IT — morphology may be phonotactic!"
elif z_mi < 5:
    verdict_38a = "Bigrams explain MOST of it — weak residual structure"
else:
    verdict_38a = "GENUINE STRUCTURE beyond bigrams — morphology is real"
print(f"\n  → {verdict_38a}")

# Show what the bigram model generates (sample)
print(f"\n  Sample bigram-generated words:")
sample = generate_synthetic_corpus(20)
print(f"    {', '.join(sample[:20])}")

# Show bigram synthetic prefix/suffix distributions
print(f"\n  Bigram synthetic prefix distribution (one run):")
last_pfx = [get_prefix_group(w) for w in generate_synthetic_corpus(len(tokens))]
pfx_dist = Counter(last_pfx)
for p in ['ch','sh','qo','o','d','y','l','NONE']:
    frac = pfx_dist.get(p, 0) / len(tokens) * 100
    obs_frac = Counter(obs_pfx).get(p, 0) / len(tokens) * 100
    print(f"    {p:<6} syn={frac:5.1f}%  obs={obs_frac:5.1f}%")


# ══════════════════════════════════════════════════════════════════
# 38b: MI BY WORD LENGTH
# ══════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("B: MI BY WORD LENGTH")
print("    Does prefix↔suffix MI persist for long words?")
print("="*70)

# Bin by collapsed form length
length_bins = [(2,4), (5,6), (7,8), (9,12), (13,99)]
bin_labels = ['2-4', '5-6', '7-8', '9-12', '13+']

print(f"\n  {'Length':<8} {'N':>6} {'MI':>8} {'V':>8} | {'Bigram MI':>12} {'z':>8}")
print(f"  {'-'*58}")

for (lo, hi), label in zip(length_bins, bin_labels):
    idx = [i for i, t in enumerate(tokens) if lo <= len(t['collapsed']) <= hi]
    if len(idx) < 50:
        print(f"  {label:<8} {len(idx):>6}  (too few)")
        continue

    bin_pfx = [obs_pfx[i] for i in idx]
    bin_sfx = [obs_sfx[i] for i in idx]
    bin_mi = compute_mi(bin_pfx, bin_sfx)
    bin_v = cramers_v(bin_pfx, bin_sfx)

    # Bigram null for this length bin
    syn_mis_bin = []
    for _ in range(30):
        syn_words = [generate_bigram_word(len(tokens[i]['collapsed'])) for i in idx]
        syn_p = [get_prefix_group(w) for w in syn_words]
        syn_s = [get_suffix_group(w) for w in syn_words]
        syn_mis_bin.append(compute_mi(syn_p, syn_s))

    syn_mean = np.mean(syn_mis_bin)
    syn_std = np.std(syn_mis_bin)
    z = (bin_mi - syn_mean) / max(syn_std, 1e-10)

    print(f"  {label:<8} {len(idx):>6} {bin_mi:>8.4f} {bin_v:>8.4f} |"
          f" {syn_mean:>6.4f}±{syn_std:.4f} {z:>8.1f}")

print(f"\n  If z stays high for long words → structure is morphological, not phonotactic")
print(f"  If z drops for long words → structure is driven by character adjacency")


# ══════════════════════════════════════════════════════════════════
# 38c: ch- VS sh-: ALLOMORPHS OR DISTINCT?
# ══════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("C: ch- VS sh- — ALLOMORPHS OR DISTINCT?")
print("    If ch- is phonotactic (parser_free_morphology), does it differ from sh-?")
print("="*70)

ch_tokens = [t for t in tokens if t['collapsed'].startswith('ch') and not t['collapsed'].startswith('cho')]
sh_tokens = [t for t in tokens if t['collapsed'].startswith('sh') and not t['collapsed'].startswith('sho')]

# Also include cho/sho separately
cho_tokens = [t for t in tokens if t['collapsed'].startswith('cho')]
sho_tokens = [t for t in tokens if t['collapsed'].startswith('sho')]

print(f"\n  ch-words (excl cho-): {len(ch_tokens)}")
print(f"  sh-words (excl sho-): {len(sh_tokens)}")
print(f"  cho-words: {len(cho_tokens)}")
print(f"  sho-words: {len(sho_tokens)}")

# Suffix distributions
def suffix_dist(tok_list):
    sfx = [get_suffix_group(t['collapsed']) for t in tok_list]
    c = Counter(sfx)
    total = max(sum(c.values()), 1)
    return {k: v/total for k, v in c.items()}, c

ch_sfx_d, ch_sfx_c = suffix_dist(ch_tokens)
sh_sfx_d, sh_sfx_c = suffix_dist(sh_tokens)

all_sfx = sorted(set(list(ch_sfx_d.keys()) + list(sh_sfx_d.keys())))
print(f"\n  Suffix distributions:")
print(f"  {'Suffix':<8} {'ch-':>8} {'sh-':>8} {'Δ':>8}")
print(f"  {'-'*32}")
for sf in all_sfx:
    ch_f = ch_sfx_d.get(sf, 0) * 100
    sh_f = sh_sfx_d.get(sf, 0) * 100
    print(f"  {sf:<8} {ch_f:>7.1f}% {sh_f:>7.1f}% {ch_f-sh_f:>+7.1f}%")

# Section distributions
SECTIONS = ['bio','cosmo','herbal-A','herbal-B','pharma','text','zodiac','unknown']
ch_sec = Counter(t['section'] for t in ch_tokens)
sh_sec = Counter(t['section'] for t in sh_tokens)
ch_total = max(sum(ch_sec.values()), 1)
sh_total = max(sum(sh_sec.values()), 1)

print(f"\n  Section distributions:")
print(f"  {'Section':<12} {'ch-':>8} {'sh-':>8} {'Δ':>8}")
print(f"  {'-'*36}")
for s in SECTIONS:
    ch_f = ch_sec.get(s, 0) / ch_total * 100
    sh_f = sh_sec.get(s, 0) / sh_total * 100
    if ch_f > 0.1 or sh_f > 0.1:
        print(f"  {s:<12} {ch_f:>7.1f}% {sh_f:>7.1f}% {ch_f-sh_f:>+7.1f}%")

# Position
ch_pos = np.mean([t['pos'] for t in ch_tokens])
sh_pos = np.mean([t['pos'] for t in sh_tokens])
ch_init = sum(1 for t in ch_tokens if t['word_idx'] == 0) / max(len(ch_tokens), 1) * 100
sh_init = sum(1 for t in sh_tokens if t['word_idx'] == 0) / max(len(sh_tokens), 1) * 100
ch_final = sum(1 for t in ch_tokens if t['word_idx'] == t['line_len'] - 1) / max(len(ch_tokens), 1) * 100
sh_final = sum(1 for t in sh_tokens if t['word_idx'] == t['line_len'] - 1) / max(len(sh_tokens), 1) * 100

print(f"\n  Position:")
print(f"  {'Metric':<15} {'ch-':>8} {'sh-':>8}")
print(f"  {'mean pos':<15} {ch_pos:>8.3f} {sh_pos:>8.3f}")
print(f"  {'% line-init':<15} {ch_init:>7.1f}% {sh_init:>7.1f}%")
print(f"  {'% line-final':<15} {ch_final:>7.1f}% {sh_final:>7.1f}%")

# Chi-squared test: suffix × {ch, sh}
ch_sfx_list = [get_suffix_group(t['collapsed']) for t in ch_tokens]
sh_sfx_list = [get_suffix_group(t['collapsed']) for t in sh_tokens]
combined_sfx = ch_sfx_list + sh_sfx_list
combined_pfx = ['ch'] * len(ch_sfx_list) + ['sh'] * len(sh_sfx_list)
v_ch_sh = cramers_v(combined_pfx, combined_sfx)
mi_ch_sh = compute_mi(combined_pfx, combined_sfx)

print(f"\n  Chi-squared association (suffix × ch/sh):")
print(f"    Cramér's V = {v_ch_sh:.4f}")
print(f"    MI = {mi_ch_sh:.4f} bits")

if v_ch_sh < 0.05:
    print(f"    → INDISTINGUISHABLE (V < 0.05) — ch/sh are allomorphs")
elif v_ch_sh < 0.10:
    print(f"    → WEAK difference — may be allomorphs with slight bias")
else:
    print(f"    → DISTINCT morphemes (V ≥ 0.10) — ch ≠ sh in suffix selection")

# Also: ch-section vs sh-section
combined_sec = [t['section'] for t in ch_tokens] + [t['section'] for t in sh_tokens]
combined_pfx_sec = ['ch'] * len(ch_tokens) + ['sh'] * len(sh_tokens)
v_ch_sh_sec = cramers_v(combined_pfx_sec, combined_sec)
print(f"    Section × ch/sh: V = {v_ch_sh_sec:.4f}")


# ══════════════════════════════════════════════════════════════════
# 38d: INFORMATION DECOMPOSITION
# ══════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("D: INFORMATION DECOMPOSITION")
print("    What do word edges actually encode?")
print("="*70)

sections = [t['section'] for t in tokens]
# Bin position into 5 bins
pos_bins = []
for t in tokens:
    p = t['pos']
    if p < 0.2: pos_bins.append('P0-20')
    elif p < 0.4: pos_bins.append('P20-40')
    elif p < 0.6: pos_bins.append('P40-60')
    elif p < 0.8: pos_bins.append('P60-80')
    else: pos_bins.append('P80-100')

# Compute all MIs
h_sec = entropy(sections)
h_pos = entropy(pos_bins)
h_pfx = entropy(obs_pfx)
h_sfx = entropy(obs_sfx)

mi_sec_pfx = compute_mi(sections, obs_pfx)
mi_sec_sfx = compute_mi(sections, obs_sfx)
mi_pos_pfx = compute_mi(pos_bins, obs_pfx)
mi_pos_sfx = compute_mi(pos_bins, obs_sfx)

# Combined: prefix + suffix → section/position
combined_edge = [f"{p}|{s}" for p, s in zip(obs_pfx, obs_sfx)]
mi_sec_both = compute_mi(sections, combined_edge)
mi_pos_both = compute_mi(pos_bins, combined_edge)
mi_pfx_sfx = compute_mi(obs_pfx, obs_sfx)

print(f"\n  Entropies:")
print(f"    H(section)  = {h_sec:.3f} bits")
print(f"    H(position) = {h_pos:.3f} bits")
print(f"    H(prefix)   = {h_pfx:.3f} bits")
print(f"    H(suffix)   = {h_sfx:.3f} bits")

print(f"\n  Mutual Information (bits):")
print(f"  {'':>20} {'Section':>10} {'Position':>10}")
print(f"  {'-'*40}")
print(f"  {'Prefix alone':<20} {mi_sec_pfx:>10.4f} {mi_pos_pfx:>10.4f}")
print(f"  {'Suffix alone':<20} {mi_sec_sfx:>10.4f} {mi_pos_sfx:>10.4f}")
print(f"  {'Prefix+Suffix':<20} {mi_sec_both:>10.4f} {mi_pos_both:>10.4f}")
print(f"  {'Prefix↔Suffix':<20} {mi_pfx_sfx:>10.4f}  (internal)")

print(f"\n  As % of target entropy:")
print(f"  {'':>20} {'Section':>10} {'Position':>10}")
print(f"  {'-'*40}")
print(f"  {'Prefix alone':<20} {100*mi_sec_pfx/h_sec:>9.1f}% {100*mi_pos_pfx/h_pos:>9.1f}%")
print(f"  {'Suffix alone':<20} {100*mi_sec_sfx/h_sec:>9.1f}% {100*mi_pos_sfx/h_pos:>9.1f}%")
print(f"  {'Prefix+Suffix':<20} {100*mi_sec_both/h_sec:>9.1f}% {100*mi_pos_both/h_pos:>9.1f}%")

# Breakdown: which prefixes carry the most section info?
print(f"\n  Per-prefix section information:")
print(f"  {'Prefix':<8} {'N':>6} {'MI contrib':>10} {'Top section':>15}")
print(f"  {'-'*45}")
pfx_counts = Counter(obs_pfx)
for pfx in sorted(pfx_counts.keys(), key=lambda x: pfx_counts[x], reverse=True):
    idx = [i for i, p in enumerate(obs_pfx) if p == pfx]
    pfx_secs = [sections[i] for i in idx]
    sec_ct = Counter(pfx_secs)
    total = sum(sec_ct.values())
    top_sec = sec_ct.most_common(1)[0]
    # MI contribution: weighted by P(prefix)
    p_pfx = len(idx) / len(tokens)
    h_sec_given_pfx = entropy(pfx_secs)
    mi_contrib = p_pfx * (h_sec - h_sec_given_pfx)
    print(f"  {pfx:<8} {len(idx):>6} {mi_contrib:>10.4f} {top_sec[0]}({100*top_sec[1]/total:.0f}%)")

# Breakdown: which suffixes carry the most position info?
print(f"\n  Per-suffix position information:")
print(f"  {'Suffix':<8} {'N':>6} {'MI contrib':>10} {'Mean pos':>10} {'Init%':>8}")
print(f"  {'-'*48}")
sfx_counts = Counter(obs_sfx)
for sfx in sorted(sfx_counts.keys(), key=lambda x: sfx_counts[x], reverse=True):
    idx = [i for i, s in enumerate(obs_sfx) if s == sfx]
    sfx_pos = [pos_bins[i] for i in idx]
    sfx_raw_pos = [tokens[i]['pos'] for i in idx]
    sfx_init = sum(1 for i in idx if tokens[i]['word_idx'] == 0) / max(len(idx), 1) * 100
    p_sfx = len(idx) / len(tokens)
    h_pos_given_sfx = entropy(sfx_pos)
    mi_contrib = p_sfx * (h_pos - h_pos_given_sfx)
    print(f"  {sfx:<8} {len(idx):>6} {mi_contrib:>10.4f} {np.mean(sfx_raw_pos):>10.3f} {sfx_init:>7.1f}%")

# The synergy question: does prefix+suffix together tell us MORE
# than prefix and suffix separately?
redundancy = mi_sec_pfx + mi_sec_sfx - mi_sec_both
synergy = mi_sec_both - max(mi_sec_pfx, mi_sec_sfx)
print(f"\n  Section information budget:")
print(f"    Prefix provides:  {mi_sec_pfx:.4f} bits")
print(f"    Suffix provides:  {mi_sec_sfx:.4f} bits")
print(f"    Together provide: {mi_sec_both:.4f} bits")
print(f"    Sum would be:     {mi_sec_pfx + mi_sec_sfx:.4f} bits")
print(f"    Redundancy:       {redundancy:.4f} bits")
print(f"    Synergy:          {synergy:.4f} bits")
if redundancy > 0.01:
    print(f"    → Prefix and suffix carry OVERLAPPING section info ({redundancy:.3f} bits redundant)")
elif synergy > 0.01:
    print(f"    → Prefix and suffix carry COMPLEMENTARY section info ({synergy:.3f} bits synergy)")
else:
    print(f"    → Prefix and suffix carry INDEPENDENT section info")


# ══════════════════════════════════════════════════════════════════
# SYNTHESIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("SYNTHESIS: What Survives All Tests?")
print("="*70)

print(f"""
  BIGRAM NULL MODEL:
    Observed MI = {obs_mi:.4f}, Bigram null MI = {syn_mi_mean:.4f}±{syn_mi_std:.4f}
    z = {z_mi:.1f}
    Verdict: {verdict_38a}

  CH- vs SH-:
    Suffix selection V = {v_ch_sh:.4f}
    Section association V = {v_ch_sh_sec:.4f}
    Position: ch mean={ch_pos:.3f}, sh mean={sh_pos:.3f}

  INFORMATION BUDGET:
    Word edges (prefix+suffix) encode {100*mi_sec_both/h_sec:.1f}% of section info
    Word edges encode {100*mi_pos_both/h_pos:.1f}% of position info
    Internal prefix↔suffix MI = {mi_pfx_sfx:.4f} bits

  If bigram z >> 5: Voynich has genuine morphological structure
  If bigram z < 2: "Morphology" is just character-level phonotactics
  If ch/sh V < 0.05: They are allomorphs, not distinct prefixes
""")

print("\n[bigram_null_stress_test Complete]")
