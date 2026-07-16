#!/usr/bin/env python3
"""
Reverse-Engineering the Script: What Character-Merging
              Pattern Reproduces the VMS Fingerprint?
═════════════════════════════════════════════════════════════════

PREMISE:
encoding_model_tournament showed VMS matches natural language on 6/7 fingerprint stats,
but H(c|prev)/H(c) = 0.641 vs Italian 0.839 — a +1.7σ anomaly that NO
encoding model could explain. This is the residual fingerprint of
whatever script or encoding system produced Voynichese.

HYPOTHESIS:
If VMS is natural language written in a partially syllabic script, some
EVA "characters" would represent common plaintext bigrams or trigrams.
Merging frequent plaintext character sequences into single symbols would:
 - LOWER H(c|prev)/H(c) (forced transitions within merged units)
 - SHORTEN mean word length (fewer symbols per word)
 - PRESERVE vocabulary dynamics (same words, just shorter spelling)
 - PRESERVE word-level bigrams (word identity unchanged)

METHOD:
1. Start with Italian text (Dante, 50K words)
2. Count all character bigrams
3. Iteratively merge the most frequent bigram into a single new symbol
   (Byte Pair Encoding — BPE)
4. After each merge step, recompute all 7 fingerprint statistics
5. Find the merge count that minimizes L2 distance to VMS
6. Also: compare WHICH specific merge pattern the VMS EVA glyph system
   corresponds to

ADDITIONAL TESTS:
 A. BPE on Italian → find optimal merge count for VMS match
 B. Analyze VMS's own EVA compound glyphs (ch, sh, etc.) — how much of
    the bigram anomaly do they already explain?
 C. Compare the VMS bigram transition matrix structure to the BPE-merged
    Italian matrix
 D. Test: does the VMS "positional specialization" pattern emerge
    naturally from BPE-merged Italian?

SKEPTICAL NOTES:
 - BPE is a greedy algorithm; optimal merges may not be the only path
 - Italian may not be the source language
 - The bigram anomaly might have other explanations (formulaic construction,
   limited character set, cipher with constrained rules)
 - We test one language; results should be directional, not definitive
"""

import sys, os, re, math, json, random, urllib.request
from pathlib import Path
from collections import Counter, defaultdict

_print = print
import numpy as np
from common import eva_to_glyphs_v2 as eva_to_glyphs, fetch_gutenberg, load_vms_words

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    _print(s, end=end); sys.stdout.flush()
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))


# ═══════════════════════════════════════════════════════════════════════
# DATA LOADING (from encoding_model_tournament)
# ═══════════════════════════════════════════════════════════════════════




def load_italian_words():
    raw = fetch_gutenberg(1012)
    text = raw.lower()
    text = re.sub(r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþß\' ]+', ' ', text)
    words = [w for w in text.split() if len(w) >= 1]
    return words[:50000]


# ═══════════════════════════════════════════════════════════════════════
# FINGERPRINT FUNCTIONS (from encoding_model_tournament)
# ═══════════════════════════════════════════════════════════════════════

def char_bigram_predictability(char_list):
    """H(c|prev) / H(c)"""
    unigram = Counter(char_list)
    total = sum(unigram.values())
    if total < 2: return 1.0
    h_uni = -sum((c/total)*math.log2(c/total) for c in unigram.values() if c > 0)
    bigrams = Counter()
    for i in range(1, len(char_list)):
        bigrams[(char_list[i-1], char_list[i])] += 1
    total_bi = sum(bigrams.values())
    h_joint = -sum((c/total_bi)*math.log2(c/total_bi) for c in bigrams.values() if c > 0)
    prev_counts = Counter()
    for (c1, c2), cnt in bigrams.items():
        prev_counts[c1] += cnt
    prev_total = sum(prev_counts.values())
    h_prev = -sum((c/prev_total)*math.log2(c/prev_total) for c in prev_counts.values() if c > 0)
    h_cond = h_joint - h_prev
    return h_cond / h_uni if h_uni > 0 else 1.0

def heaps_exponent(words):
    n = len(words)
    if n < 100: return 0.0
    sample_points = np.linspace(100, n, 20, dtype=int)
    vocab_at = {}; running = set(); idx = 0
    for pt in sorted(sample_points):
        while idx < pt: running.add(words[idx]); idx += 1
        vocab_at[pt] = len(running)
    log_n = np.array([math.log(pt) for pt in sample_points])
    log_v = np.array([math.log(vocab_at[pt]) for pt in sample_points])
    A = np.vstack([log_n, np.ones(len(log_n))]).T
    return float(np.linalg.lstsq(A, log_v, rcond=None)[0][0])

def hapax_ratio_at_midpoint(words):
    mid = len(words) // 2
    freq = Counter(words[:mid])
    return sum(1 for c in freq.values() if c == 1) / max(len(freq), 1)

def word_bigram_predictability(words):
    n = len(words)
    if n < 100: return 1.0
    unigram = Counter(words)
    total = sum(unigram.values())
    h_uni = -sum((c/total)*math.log2(c/total) for c in unigram.values() if c > 0)
    bigrams = Counter()
    for i in range(1, n): bigrams[(words[i-1], words[i])] += 1
    total_bi = sum(bigrams.values())
    h_joint = -sum((c/total_bi)*math.log2(c/total_bi) for c in bigrams.values() if c > 0)
    prev_counts = Counter()
    for (w1, w2), cnt in bigrams.items(): prev_counts[w1] += cnt
    prev_total = sum(prev_counts.values())
    h_prev = -sum((c/prev_total)*math.log2(c/prev_total) for c in prev_counts.values() if c > 0)
    h_cond = h_joint - h_prev
    return h_cond / h_uni if h_uni > 0 else 1.0

def ttr_at_n(words, n=5000):
    subset = words[:min(n, len(words))]
    return len(set(subset)) / len(subset)

def zipf_alpha(words):
    freq = Counter(words)
    ranked = sorted(freq.values(), reverse=True)
    n = min(len(ranked), 500)
    if n < 10: return 0.0
    log_rank = np.log(np.arange(1, n+1))
    log_freq = np.log(np.array(ranked[:n], dtype=float))
    A = np.vstack([log_rank, np.ones(n)]).T
    return float(-np.linalg.lstsq(A, log_freq, rcond=None)[0][0])

def mean_word_length_fn(words):
    return float(np.mean([len(w) for w in words]))

def compute_fingerprint(words, char_list, label=''):
    return {
        'label': label,
        'n_tokens': len(words),
        'n_types': len(set(words)),
        'heaps_beta': heaps_exponent(words),
        'hapax_ratio_mid': hapax_ratio_at_midpoint(words),
        'char_bigram_pred': char_bigram_predictability(char_list),
        'word_bigram_pred': word_bigram_predictability(words),
        'mean_word_len': mean_word_length_fn(words),
        'ttr_5000': ttr_at_n(words, 5000),
        'zipf_alpha': zipf_alpha(words),
    }


# ═══════════════════════════════════════════════════════════════════════
# BPE (BYTE PAIR ENCODING) ENGINE
# ═══════════════════════════════════════════════════════════════════════

def words_to_symbol_sequences(words):
    """Convert word list to list of symbol-lists (initially 1 char each)."""
    return [list(w) for w in words]

def count_pairs(sequences):
    """Count all adjacent symbol pairs across all sequences."""
    pairs = Counter()
    for seq in sequences:
        for i in range(len(seq) - 1):
            pairs[(seq[i], seq[i+1])] += 1
    return pairs

def merge_pair(sequences, pair, new_symbol):
    """Replace all occurrences of 'pair' with 'new_symbol' in all sequences."""
    a, b = pair
    new_seqs = []
    for seq in sequences:
        new_seq = []
        i = 0
        while i < len(seq):
            if i < len(seq) - 1 and seq[i] == a and seq[i+1] == b:
                new_seq.append(new_symbol)
                i += 2
            else:
                new_seq.append(seq[i])
                i += 1
        new_seqs.append(new_seq)
    return new_seqs

def sequences_to_words(sequences):
    """Convert symbol-lists back to word strings."""
    return [''.join(seq) for seq in sequences]

def sequences_to_chars(sequences):
    """Flatten symbol-lists to a single character (symbol) list."""
    chars = []
    for seq in sequences:
        chars.extend(seq)
    return chars


# ═══════════════════════════════════════════════════════════════════════
# TEST A: BPE SWEEP — find optimal merge count
# ═══════════════════════════════════════════════════════════════════════

def test_bpe_sweep(italian_words, vms_fp, stat_keys):
    pr('═' * 70)
    pr('TEST A: BPE MERGE SWEEP ON ITALIAN')
    pr('═' * 70)
    pr()
    pr('  Iteratively merging most frequent character bigrams in Italian.')
    pr('  After each merge, recomputing all 7 fingerprint statistics.')
    pr('  Finding merge count that minimizes L2 distance to VMS.')
    pr()

    sequences = words_to_symbol_sequences(italian_words)
    merge_log = []  # (step, merged_pair, new_symbol, fingerprint, l2)

    # Compute VMS target as vector
    vms_vec = np.array([vms_fp[k] for k in stat_keys])

    # Store all fingerprints for z-normalization later
    all_fps = [vms_fp]

    # Step 0: unmerged Italian
    chars0 = sequences_to_chars(sequences)
    words0 = sequences_to_words(sequences)
    fp0 = compute_fingerprint(words0, chars0, 'BPE-0')
    all_fps.append(fp0)
    merge_log.append((0, None, None, fp0))

    # Run BPE for up to 150 merges (Italian has ~30 base chars, so
    # 150 merges would create ~180 total symbols — well beyond any
    # reasonable script size, ensuring we bracket the optimum)
    max_merges = 150
    step_size = 1  # Compute fingerprint at every step up to 30, then every 5
    
    pr(f'  Running {max_merges} BPE merge steps...')
    
    for step in range(1, max_merges + 1):
        pairs = count_pairs(sequences)
        if not pairs:
            pr(f'  No more pairs at step {step}. Stopping.')
            break
        best_pair = pairs.most_common(1)[0][0]
        new_sym = best_pair[0] + best_pair[1]  # Concatenate symbols
        sequences = merge_pair(sequences, best_pair, new_sym)

        # Compute fingerprint at selected steps
        if step <= 40 or step % 5 == 0:
            chars_i = sequences_to_chars(sequences)
            words_i = sequences_to_words(sequences)
            fp_i = compute_fingerprint(words_i, chars_i, f'BPE-{step}')
            all_fps.append(fp_i)
            merge_log.append((step, best_pair, new_sym, fp_i))

            if step <= 20 or step % 10 == 0:
                n_syms = len(set(c for seq in sequences for c in seq))
                pr(f'    Step {step:3d}: merged {best_pair[0]}+{best_pair[1]} → {new_sym}  '
                   f'[{n_syms} symbols, wlen={fp_i["mean_word_len"]:.2f}, '
                   f'H(c|p)/H(c)={fp_i["char_bigram_pred"]:.4f}]')

    # Now z-normalize all fingerprints together and compute L2 from VMS
    pr()
    pr('  Computing L2 distances (z-normalized)...')

    n_entries = len(merge_log)
    stat_matrix = np.zeros((n_entries + 1, len(stat_keys)))  # +1 for VMS
    stat_matrix[0] = vms_vec
    for i, (step, pair, sym, fp) in enumerate(merge_log):
        stat_matrix[i+1] = np.array([fp[k] for k in stat_keys])

    means = stat_matrix.mean(axis=0)
    stds = stat_matrix.std(axis=0)
    stds[stds == 0] = 1
    z_matrix = (stat_matrix - means) / stds
    vms_z = z_matrix[0]

    # Compute L2 for each BPE step
    results = []
    for i, (step, pair, sym, fp) in enumerate(merge_log):
        dist = float(np.sqrt(np.sum((z_matrix[i+1] - vms_z) ** 2)))
        results.append((step, pair, sym, fp, dist))

    # Find optimum
    best_idx = min(range(len(results)), key=lambda i: results[i][4])
    best_step, best_pair_opt, best_sym, best_fp, best_dist = results[best_idx]

    pr()
    pr(f'  OPTIMAL: {best_step} BPE merges (L2={best_dist:.3f})')
    pr()

    # Print trajectory table
    pr(f'  {"Step":>5s} {"Merges":>7s} {"H(c|p)/H(c)":>12s} {"Mean wlen":>10s} '
       f'{"Heaps β":>10s} {"TTR@5K":>10s} {"L2 dist":>10s}')
    pr('  ' + '-' * 70)
    for step, pair, sym, fp, dist in results:
        if step <= 30 or step % 10 == 0 or step == best_step:
            marker = ' ◄◄◄' if step == best_step else ''
            pr(f'  {step:>5d} {"":>7s} {fp["char_bigram_pred"]:>12.4f} '
               f'{fp["mean_word_len"]:>10.3f} {fp["heaps_beta"]:>10.4f} '
               f'{fp["ttr_5000"]:>10.4f} {dist:>10.3f}{marker}')

    # VMS target for comparison
    pr(f'  {"VMS":>5s} {"target":>7s} {vms_fp["char_bigram_pred"]:>12.4f} '
       f'{vms_fp["mean_word_len"]:>10.3f} {vms_fp["heaps_beta"]:>10.4f} '
       f'{vms_fp["ttr_5000"]:>10.4f} {"0.000":>10s}')

    return results, best_step, best_fp, best_dist


# ═══════════════════════════════════════════════════════════════════════
# TEST B: VMS EVA GLYPH ANALYSIS — how much do compound glyphs explain?
# ═══════════════════════════════════════════════════════════════════════

def test_eva_glyph_contribution(vms_words):
    pr()
    pr('═' * 70)
    pr('TEST B: EVA COMPOUND GLYPH CONTRIBUTION TO BIGRAM ANOMALY')
    pr('═' * 70)
    pr()

    # Raw characters (no glyph merging)
    raw_chars = []
    for w in vms_words:
        raw_chars.extend(list(w))
    h_ratio_raw = char_bigram_predictability(raw_chars)

    # EVA glyphs (ch, sh, etc. merged)
    glyph_chars = []
    for w in vms_words:
        glyph_chars.extend(eva_to_glyphs(w))
    h_ratio_glyph = char_bigram_predictability(glyph_chars)

    pr(f'  Raw EVA characters (no merging):')
    pr(f'    Alphabet size: {len(set(raw_chars))}')
    pr(f'    H(c|prev)/H(c) = {h_ratio_raw:.4f}')
    pr()
    pr(f'  EVA glyphs (ch/sh/th merged):')
    pr(f'    Alphabet size: {len(set(glyph_chars))}')
    pr(f'    H(c|prev)/H(c) = {h_ratio_glyph:.4f}')
    pr()

    # How much of the gap from Italian (0.839) does glyph merging explain?
    italian_ratio = 0.839  # From encoding_model_tournament
    gap_total = italian_ratio - h_ratio_raw
    gap_after_glyph = italian_ratio - h_ratio_glyph
    explained = (gap_total - gap_after_glyph) / gap_total if gap_total != 0 else 0

    pr(f'  Gap from Italian (0.839):')
    pr(f'    Raw:   0.839 - {h_ratio_raw:.4f} = {gap_total:.4f}')
    pr(f'    Glyph: 0.839 - {h_ratio_glyph:.4f} = {gap_after_glyph:.4f}')
    pr(f'    EVA compound glyphs explain {explained:.1%} of the bigram anomaly')
    pr()

    # Which specific bigrams are most "forced" in VMS?
    pr('  Top 20 most deterministic bigram transitions in VMS (EVA glyphs):')
    bigrams = Counter()
    for w in vms_words:
        gl = eva_to_glyphs(w)
        for i in range(len(gl)-1):
            bigrams[(gl[i], gl[i+1])] += 1

    # For each first glyph, compute entropy of successor distribution
    succ_dist = defaultdict(Counter)
    for (g1, g2), cnt in bigrams.items():
        succ_dist[g1][g2] += cnt

    glyph_info = []
    for g1, succs in succ_dist.items():
        total = sum(succs.values())
        if total < 20:  # Skip rare characters
            continue
        h = -sum((c/total)*math.log2(c/total) for c in succs.values() if c > 0)
        top_succ = succs.most_common(1)[0]
        glyph_info.append((g1, h, total, top_succ[0], top_succ[1]/total))

    glyph_info.sort(key=lambda x: x[1])  # Sort by entropy (most deterministic first)

    pr(f'  {"Glyph":>8s} {"H(next)":>8s} {"Count":>7s} {"Top succ":>10s} {"P(top)":>8s}')
    pr('  ' + '-' * 50)
    for g1, h, total, top_s, p_top in glyph_info[:20]:
        pr(f'  {g1:>8s} {h:>8.3f} {total:>7d} {top_s:>10s} {p_top:>8.1%}')

    return h_ratio_raw, h_ratio_glyph


# ═══════════════════════════════════════════════════════════════════════
# TEST C: POSITIONAL SPECIALIZATION FROM BPE
# ═══════════════════════════════════════════════════════════════════════

def test_positional_specialization(italian_words, vms_words, optimal_step):
    pr()
    pr('═' * 70)
    pr('TEST C: DOES BPE-MERGED ITALIAN DEVELOP POSITIONAL SPECIALIZATION?')
    pr('═' * 70)
    pr()

    # Apply optimal BPE steps to Italian
    sequences = words_to_symbol_sequences(italian_words)
    for step in range(optimal_step):
        pairs = count_pairs(sequences)
        if not pairs: break
        best_pair = pairs.most_common(1)[0][0]
        new_sym = best_pair[0] + best_pair[1]
        sequences = merge_pair(sequences, best_pair, new_sym)

    # Measure positional specialization: for each symbol, what fraction
    # of its occurrences are in initial/medial/final position?
    init_counts = Counter()
    med_counts = Counter()
    final_counts = Counter()
    total_counts = Counter()

    for seq in sequences:
        if len(seq) == 1:
            init_counts[seq[0]] += 1
            final_counts[seq[0]] += 1
            total_counts[seq[0]] += 1
        else:
            init_counts[seq[0]] += 1
            total_counts[seq[0]] += 1
            for s in seq[1:-1]:
                med_counts[s] += 1
                total_counts[s] += 1
            final_counts[seq[-1]] += 1
            total_counts[seq[-1]] += 1

    # Same for VMS
    vms_init = Counter()
    vms_med = Counter()
    vms_final = Counter()
    vms_total = Counter()

    for w in vms_words:
        gl = eva_to_glyphs(w)
        if len(gl) == 1:
            vms_init[gl[0]] += 1; vms_final[gl[0]] += 1; vms_total[gl[0]] += 1
        else:
            vms_init[gl[0]] += 1; vms_total[gl[0]] += 1
            for g in gl[1:-1]:
                vms_med[g] += 1; vms_total[g] += 1
            vms_final[gl[-1]] += 1; vms_total[gl[-1]] += 1

    def position_entropy(init, med, final, total_c, min_count=50):
        """For each symbol, compute entropy of its positional distribution.
        Return mean entropy (lower = more specialized)."""
        entropies = []
        for sym in total_c:
            if total_c[sym] < min_count: continue
            t = total_c[sym]
            probs = [init.get(sym, 0)/t, med.get(sym, 0)/t, final.get(sym, 0)/t]
            probs = [p for p in probs if p > 0]
            h = -sum(p * math.log2(p) for p in probs)
            entropies.append(h)
        return np.mean(entropies) if entropies else 0

    bpe_pos_h = position_entropy(init_counts, med_counts, final_counts, total_counts)
    vms_pos_h = position_entropy(vms_init, vms_med, vms_final, vms_total)

    # Also compute for raw Italian (no BPE)
    raw_init = Counter(); raw_med = Counter(); raw_final = Counter(); raw_total = Counter()
    for w in italian_words:
        chars = list(w)
        if len(chars) == 1:
            raw_init[chars[0]] += 1; raw_final[chars[0]] += 1; raw_total[chars[0]] += 1
        else:
            raw_init[chars[0]] += 1; raw_total[chars[0]] += 1
            for c in chars[1:-1]:
                raw_med[c] += 1; raw_total[c] += 1
            raw_final[chars[-1]] += 1; raw_total[chars[-1]] += 1

    raw_pos_h = position_entropy(raw_init, raw_med, raw_final, raw_total)

    pr(f'  Mean positional entropy (lower = more specialized):')
    pr(f'    Italian (raw):       {raw_pos_h:.4f}')
    pr(f'    Italian (BPE-{optimal_step:d}):  {bpe_pos_h:.4f}')
    pr(f'    VMS (EVA glyphs):    {vms_pos_h:.4f}')
    pr()

    if bpe_pos_h < raw_pos_h:
        drop = (raw_pos_h - bpe_pos_h) / raw_pos_h
        pr(f'  BPE merging INCREASES positional specialization by {drop:.1%}')
        if abs(bpe_pos_h - vms_pos_h) < abs(raw_pos_h - vms_pos_h):
            pr(f'  → BPE-merged Italian is CLOSER to VMS positional pattern')
        else:
            pr(f'  → But still NOT as specialized as VMS')
    else:
        pr(f'  BPE merging does NOT increase positional specialization')

    # Show top positionally-specialized symbols in BPE Italian vs VMS
    pr()
    pr(f'  Top positionally-specialized symbols (BPE-{optimal_step} Italian):')
    spec_bpe = []
    for sym in total_counts:
        if total_counts[sym] < 50: continue
        t = total_counts[sym]
        max_pos = max(init_counts.get(sym,0), med_counts.get(sym,0), final_counts.get(sym,0))
        spec_bpe.append((sym, max_pos/t, t))
    spec_bpe.sort(key=lambda x: -x[1])
    pr(f'  {"Symbol":>12s} {"Max pos %":>10s} {"Count":>7s}')
    for sym, ratio, cnt in spec_bpe[:15]:
        pr(f'  {sym:>12s} {ratio:>10.1%} {cnt:>7d}')

    pr()
    pr(f'  Top positionally-specialized glyphs (VMS):')
    spec_vms = []
    for sym in vms_total:
        if vms_total[sym] < 50: continue
        t = vms_total[sym]
        max_pos = max(vms_init.get(sym,0), vms_med.get(sym,0), vms_final.get(sym,0))
        spec_vms.append((sym, max_pos/t, t))
    spec_vms.sort(key=lambda x: -x[1])
    pr(f'  {"Glyph":>12s} {"Max pos %":>10s} {"Count":>7s}')
    for sym, ratio, cnt in spec_vms[:15]:
        pr(f'  {sym:>12s} {ratio:>10.1%} {cnt:>7d}')

    return bpe_pos_h, vms_pos_h, raw_pos_h


# ═══════════════════════════════════════════════════════════════════════
# TEST D: TRANSITION MATRIX STRUCTURAL COMPARISON
# ═══════════════════════════════════════════════════════════════════════

def test_transition_structure(italian_words, vms_words, optimal_step):
    pr()
    pr('═' * 70)
    pr('TEST D: TRANSITION MATRIX STRUCTURE — BPE ITALIAN vs VMS')
    pr('═' * 70)
    pr()

    # Build BPE Italian at optimal step
    sequences = words_to_symbol_sequences(italian_words)
    for step in range(optimal_step):
        pairs = count_pairs(sequences)
        if not pairs: break
        best_pair = pairs.most_common(1)[0][0]
        new_sym = best_pair[0] + best_pair[1]
        sequences = merge_pair(sequences, best_pair, new_sym)

    # Transition matrix properties for BPE Italian
    bpe_chars = sequences_to_chars(sequences)
    bpe_bigrams = Counter()
    for i in range(1, len(bpe_chars)):
        bpe_bigrams[(bpe_chars[i-1], bpe_chars[i])] += 1

    bpe_symbols = sorted(set(bpe_chars))
    n_bpe = len(bpe_symbols)

    # How many transitions are actually used vs possible?
    bpe_nonzero = len(bpe_bigrams)
    bpe_possible = n_bpe * n_bpe
    bpe_density = bpe_nonzero / bpe_possible

    # Same for VMS
    vms_gl_chars = []
    for w in vms_words:
        vms_gl_chars.extend(eva_to_glyphs(w))
    vms_bigrams = Counter()
    for i in range(1, len(vms_gl_chars)):
        vms_bigrams[(vms_gl_chars[i-1], vms_gl_chars[i])] += 1

    vms_symbols = sorted(set(vms_gl_chars))
    n_vms = len(vms_symbols)
    vms_nonzero = len(vms_bigrams)
    vms_possible = n_vms * n_vms
    vms_density = vms_nonzero / vms_possible

    # Raw Italian
    raw_chars = []
    for w in italian_words:
        raw_chars.extend(list(w))
    raw_bigrams = Counter()
    for i in range(1, len(raw_chars)):
        raw_bigrams[(raw_chars[i-1], raw_chars[i])] += 1
    raw_symbols = sorted(set(raw_chars))
    n_raw = len(raw_symbols)
    raw_nonzero = len(raw_bigrams)
    raw_possible = n_raw * n_raw
    raw_density = raw_nonzero / raw_possible

    pr(f'  {"":>20s} {"Symbols":>8s} {"Nonzero":>8s} {"Possible":>9s} {"Density":>8s}')
    pr('  ' + '-' * 58)
    pr(f'  {"Italian (raw)":>20s} {n_raw:>8d} {raw_nonzero:>8d} {raw_possible:>9d} {raw_density:>8.3f}')
    pr(f'  {"Italian BPE-"+str(optimal_step):>20s} {n_bpe:>8d} {bpe_nonzero:>8d} {bpe_possible:>9d} {bpe_density:>8.3f}')
    pr(f'  {"VMS (EVA glyphs)":>20s} {n_vms:>8d} {vms_nonzero:>8d} {vms_possible:>9d} {vms_density:>8.3f}')
    pr()

    # Concentration: what fraction of total is in top-10 bigrams?
    bpe_top10 = sum(c for _, c in Counter(bpe_bigrams).most_common(10))
    bpe_total = sum(bpe_bigrams.values())
    vms_top10 = sum(c for _, c in Counter(vms_bigrams).most_common(10))
    vms_total = sum(vms_bigrams.values())
    raw_top10 = sum(c for _, c in Counter(raw_bigrams).most_common(10))
    raw_total = sum(raw_bigrams.values())

    pr(f'  Top-10 bigram concentration:')
    pr(f'    Italian (raw):     {raw_top10/raw_total:.1%}')
    pr(f'    Italian BPE-{optimal_step}:  {bpe_top10/bpe_total:.1%}')
    pr(f'    VMS (EVA glyphs):  {vms_top10/vms_total:.1%}')
    pr()

    # Successor entropy distribution
    def successor_entropy_dist(bigrams_counter):
        succ = defaultdict(Counter)
        for (a, b), c in bigrams_counter.items():
            succ[a][b] += c
        entropies = []
        for a, scounts in succ.items():
            total = sum(scounts.values())
            if total < 10: continue
            h = -sum((c/total)*math.log2(c/total) for c in scounts.values() if c > 0)
            entropies.append(h)
        return entropies

    bpe_se = successor_entropy_dist(bpe_bigrams)
    vms_se = successor_entropy_dist(vms_bigrams)
    raw_se = successor_entropy_dist(raw_bigrams)

    pr(f'  Mean successor entropy per symbol:')
    pr(f'    Italian (raw):     {np.mean(raw_se):.3f} bits (σ={np.std(raw_se):.3f})')
    pr(f'    Italian BPE-{optimal_step}:  {np.mean(bpe_se):.3f} bits (σ={np.std(bpe_se):.3f})')
    pr(f'    VMS (EVA glyphs):  {np.mean(vms_se):.3f} bits (σ={np.std(vms_se):.3f})')

    return {
        'bpe_density': bpe_density, 'vms_density': vms_density,
        'bpe_mean_succ_h': float(np.mean(bpe_se)),
        'vms_mean_succ_h': float(np.mean(vms_se)),
    }


# ═══════════════════════════════════════════════════════════════════════
# ADJUDICATION
# ═══════════════════════════════════════════════════════════════════════

def adjudicate(bpe_results, best_step, best_fp, best_dist, vms_fp,
               h_raw, h_glyph, bpe_pos_h, vms_pos_h, raw_pos_h,
               trans_info, stat_keys):
    pr()
    pr('═' * 70)
    pr('ADJUDICATION')
    pr('═' * 70)
    pr()

    pr(f'  Optimal BPE merge count: {best_step}')
    pr(f'  L2 distance at optimum:  {best_dist:.3f}')
    pr(f'  L2 at step 0 (raw):     {bpe_results[0][4]:.3f}')
    pr(f'  Improvement:             {(bpe_results[0][4] - best_dist)/bpe_results[0][4]:.1%}')
    pr()

    pr(f'  Fingerprint at optimum vs VMS:')
    for k in stat_keys:
        v = vms_fp[k]
        b = best_fp[k]
        delta = b - v
        pr(f'    {k:>20s}:  VMS={v:.4f}  BPE-{best_step}={b:.4f}  Δ={delta:+.4f}')
    pr()

    # Key question: does BPE close the char-bigram gap?
    char_gap_before = abs(0.839 - vms_fp['char_bigram_pred'])
    char_gap_after = abs(best_fp['char_bigram_pred'] - vms_fp['char_bigram_pred'])
    pr(f'  Character bigram gap:')
    pr(f'    Before BPE (Italian vs VMS): {char_gap_before:.4f}')
    pr(f'    After BPE-{best_step} (merged vs VMS): {char_gap_after:.4f}')
    if char_gap_after < char_gap_before:
        pr(f'    → BPE CLOSES {(char_gap_before-char_gap_after)/char_gap_before:.0%} of the gap')
    else:
        pr(f'    → BPE does NOT close the gap (opened it further)')
    pr()

    # Positional specialization
    pr(f'  Positional specialization:')
    pr(f'    BPE moves Italian from {raw_pos_h:.4f} to {bpe_pos_h:.4f} '
       f'(VMS target: {vms_pos_h:.4f})')
    if abs(bpe_pos_h - vms_pos_h) < abs(raw_pos_h - vms_pos_h):
        pr(f'    → BPE moves Italian CLOSER to VMS positional pattern')
    else:
        pr(f'    → BPE does NOT move Italian closer to VMS')
    pr()

    # Transition matrix
    pr(f'  Transition matrix density:')
    pr(f'    BPE: {trans_info["bpe_density"]:.3f}  VMS: {trans_info["vms_density"]:.3f}')
    pr(f'    Mean successor entropy:')
    pr(f'    BPE: {trans_info["bpe_mean_succ_h"]:.3f}  VMS: {trans_info["vms_mean_succ_h"]:.3f}')
    pr()

    # Interpretation
    pr('  INTERPRETATION:')
    pr()
    if best_step > 0 and best_dist < bpe_results[0][4]:
        pr(f'    Merging the {best_step} most common Italian character bigrams')
        pr(f'    into single symbols reduces the VMS-Italian distance by')
        pr(f'    {(bpe_results[0][4] - best_dist)/bpe_results[0][4]:.1%}.')
        if best_step <= 30:
            pr(f'    {best_step} merges is plausible for a partially syllabic script')
            pr(f'    (e.g., a script with ~{26 + best_step} symbols, some representing')
            pr(f'    common digraphs or syllables).')
        elif best_step <= 80:
            pr(f'    {best_step} merges implies a large syllabary (~{26 + best_step} symbols),')
            pr(f'    comparable to Ethiopic or Cherokee.')
        else:
            pr(f'    {best_step} merges implies an implausibly large symbol set.')
            pr(f'    BPE may be overfitting or the anomaly has a different source.')
    else:
        pr(f'    BPE merging does NOT improve the VMS match.')
        pr(f'    The character bigram anomaly likely has a source other than')
        pr(f'    bigram-to-symbol merging (e.g., positional constraints,')
        pr(f'    cipher rules, or a fundamentally different script type).')

    pr()
    pr('  REVISED CONFIDENCES (script_reverse_engineering):')

    # Assess syllabary hypothesis
    if best_step > 5 and char_gap_after < char_gap_before * 0.5:
        pr('    - NL with syllabary-like script: 80% (strengthened)')
        pr('      BPE demonstrates that character merging can reproduce')
        pr('      the VMS char-bigram ratio while preserving NL dynamics')
    elif char_gap_after < char_gap_before * 0.8:
        pr('    - NL with partially syllabic script: 75% (compatible)')
        pr('      BPE partially closes the gap; other script features')
        pr('      likely contribute')
    else:
        pr('    - NL with alphabetic script: still viable')
        pr('      The char-bigram anomaly may come from constrained')
        pr('      character sequences / positional rules, not merging')

    pr('    - Simple monoalphabetic cipher: WEAKENED')
    pr('      (Cannot explain H(c|prev)/H(c) = 0.641 since substitution')
    pr('       preserves the ratio at 0.839)')
    pr('    - Hoax/random: <3% (unchanged)')


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr('╔' + '═'*68 + '╗')
    pr('║  script_reverse_engineering: Reverse-Engineering the Script via BPE Merging        ║')
    pr('╚' + '═'*68 + '╝')
    pr()

    random.seed(42); np.random.seed(42)

    # Load data
    pr('Loading VMS...')
    vms_words = load_vms_words()
    vms_glyphs = []
    for w in vms_words: vms_glyphs.extend(eva_to_glyphs(w))
    pr(f'  VMS: {len(vms_words)} words, {len(vms_glyphs)} glyphs, '
       f'{len(set(vms_glyphs))} glyph types')

    pr('Loading Italian (Dante)...')
    italian_words = load_italian_words()
    pr(f'  Italian: {len(italian_words)} words')
    pr()

    # VMS fingerprint
    vms_fp = compute_fingerprint(vms_words, vms_glyphs, 'VMS')

    stat_keys = ['heaps_beta', 'hapax_ratio_mid', 'char_bigram_pred',
                 'word_bigram_pred', 'mean_word_len', 'ttr_5000', 'zipf_alpha']

    # TEST A: BPE sweep
    bpe_results, best_step, best_fp, best_dist = test_bpe_sweep(
        italian_words, vms_fp, stat_keys)

    # TEST B: EVA glyph contribution
    h_raw, h_glyph = test_eva_glyph_contribution(vms_words)

    # TEST C: Positional specialization
    bpe_pos_h, vms_pos_h, raw_pos_h = test_positional_specialization(
        italian_words, vms_words, best_step)

    # TEST D: Transition matrix structure
    trans_info = test_transition_structure(italian_words, vms_words, best_step)

    # ADJUDICATION
    adjudicate(bpe_results, best_step, best_fp, best_dist, vms_fp,
               h_raw, h_glyph, bpe_pos_h, vms_pos_h, raw_pos_h,
               trans_info, stat_keys)

    # Save
    out_path = RESULTS_DIR / 'script_reverse_engineering_output.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f'\nSaved to {out_path}')

    json_data = {
        'optimal_merges': best_step,
        'optimal_l2': best_dist,
        'raw_l2': bpe_results[0][4],
        'vms_fingerprint': vms_fp,
        'optimal_fingerprint': best_fp,
        'bpe_trajectory': [(s, str(p), str(sym), d) for s, p, sym, fp, d in bpe_results],
        'h_ratio_raw': h_raw,
        'h_ratio_glyph': h_glyph,
        'positional_entropy': {
            'raw_italian': raw_pos_h,
            'bpe_italian': bpe_pos_h,
            'vms': vms_pos_h,
        },
        'transition_info': trans_info,
    }
    json_path = RESULTS_DIR / 'script_reverse_engineering_output.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, default=str)
    pr(f'Saved to {json_path}')


if __name__ == '__main__':
    main()
