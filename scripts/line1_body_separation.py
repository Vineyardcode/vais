#!/usr/bin/env python3
"""
Line-1 / Body Separation: Does the VMS Contain Two Encoding Subsystems?

═══════════════════════════════════════════════════════════════════════

MOTIVATION (from Koen's "Alphabet is smaller than you think" video + our data):

  1. The video argues that after removing first-line-only, line-end-only,
     and rare glyphs, VMS has ~13 functional letters — too few for any
     European alphabet (minimum ~18 for Latin).

  2. gallows_positional_ecology/77b showed {p,f} gallows are 12-15× enriched on paragraph
     line 1 (the ENTIRE line, not just word 1). This is a different
     subsystem.

  3. forward_process_models showed the ONLY forward model reproducing h_char=0.641
     uses exactly 13 base characters.

  4. glyph_resegmentation showed 8 of 23 frequent glyphs have >85% positional
     concentration (rigidly I/M/F locked).

  NOBODY HAS MEASURED h_char SEPARATELY for line-1 vs body text.
  If line-1 is a different encoding subsystem, mixing it into the
  corpus contaminates every statistic. The h_char anomaly (0.641)
  might be partially an artifact of this mixture.

TESTS:
  1. Full fingerprint for L1 vs Body (L2+) — separate computation
  2. h_char ratio for each subset with bootstrap CI
  3. Alphabet/glyph inventory comparison
  4. Character frequency JSD between L1 and body
  5. Vocabulary overlap test
  6. SIZE-CONTROLLED NULL: subsample body to L1 size, compute h_char
  7. Cross-boundary word transition analysis
  8. Synthesis: does separating L1 explain the h_char anomaly?

SKEPTICISM NOTES:
  - L1 has only ~2,500 words (~10K glyphs) — marginal for entropy.
    Bootstrap CI is essential.
  - Body text is 93% of the corpus — its h_char should barely differ
    from the whole. If it does differ substantially, that's suspicious
    and we should investigate edge effects in our parsing.
  - Small-sample bias INFLATES entropy (upward bias in H for small n).
    This means L1 h_char may appear HIGHER than it really is. We must
    correct for this.
  - Even if L1 and body differ, the h_char anomaly in body text alone
    (which should be ~0.65 if the whole is 0.641) would still be far
    below any natural language (0.82-0.87). The anomaly cannot be
    EXPLAINED by L1 contamination — but L1 might shift it slightly.
"""

import re, sys, io, math, json, os
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import clean_word, eva_to_glyphs, extract_words, folio_section

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(42)

# ── EVA glyph tokenizer ──────────────────────────────────────────────

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']
PLAIN_GALLOWS = {'p', 't', 'k', 'f'}










# ── Parse all folios into paragraph/line structure ────────────────────

def parse_all_data():
    """Parse all folios and return line-level data within paragraphs.

    Returns list of paragraph dicts, each containing:
      section, folio, lines: [{line_num, words, is_first_line}]
      first_word: the paragraph-initial word
    """
    paragraphs = []
    current_para = None

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)

    for filepath in folio_files:
        section = folio_section(filepath.stem)

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue

                m = re.match(r'<([^>]+)>', line)
                if not m:
                    continue
                tag = m.group(1)
                rest = line[m.end():].strip()
                if not rest:
                    continue

                is_para_start = '@P' in tag or '*P' in tag
                is_continuation = '+P' in tag or '=P' in tag
                is_para_end = '<$>' in rest

                if is_para_start:
                    if current_para and current_para['lines']:
                        paragraphs.append(current_para)
                    words = extract_words(rest)
                    current_para = {
                        'section': section,
                        'folio': filepath.stem,
                        'first_word': words[0] if words else '',
                        'lines': [{
                            'line_num': 1,
                            'words': words,
                            'is_first_line': True,
                            'tag': tag,
                        }]
                    }
                elif is_continuation and current_para:
                    words = extract_words(rest)
                    ln = len(current_para['lines']) + 1
                    current_para['lines'].append({
                        'line_num': ln,
                        'words': words,
                        'is_first_line': False,
                        'tag': tag,
                    })
                elif is_continuation and not current_para:
                    # Orphan continuation — no @P start (e.g. after <$> in
                    # star/label sections).  Create a new paragraph but mark
                    # ALL lines as body text, since there is no paragraph-
                    # initial line.
                    words = extract_words(rest)
                    current_para = {
                        'section': section,
                        'folio': filepath.stem,
                        'first_word': '',
                        'lines': [{
                            'line_num': 1,
                            'words': words,
                            'is_first_line': False,
                            'tag': tag,
                        }]
                    }

                if is_para_end and current_para and current_para['lines']:
                    paragraphs.append(current_para)
                    current_para = None

        if current_para and current_para['lines']:
            paragraphs.append(current_para)
            current_para = None

    return paragraphs


# ── Entropy computations (canonical — matches encoding_model_tournament/65/66/67) ─────

def char_bigram_predictability(char_list):
    """H(c|prev) / H(c) — the h_char ratio."""
    unigram = Counter(char_list)
    total = sum(unigram.values())
    if total < 100:  # conservative minimum
        return float('nan')
    h_uni = -sum((c/total)*math.log2(c/total)
                 for c in unigram.values() if c > 0)
    if h_uni == 0:
        return float('nan')

    bigrams = Counter()
    for i in range(1, len(char_list)):
        bigrams[(char_list[i-1], char_list[i])] += 1
    total_bi = sum(bigrams.values())

    h_joint = -sum((c/total_bi)*math.log2(c/total_bi)
                   for c in bigrams.values() if c > 0)

    prev_counts = Counter()
    for (c1, c2), cnt in bigrams.items():
        prev_counts[c1] += cnt
    prev_total = sum(prev_counts.values())
    h_prev = -sum((c/prev_total)*math.log2(c/prev_total)
                  for c in prev_counts.values() if c > 0)

    h_cond = h_joint - h_prev
    return h_cond / h_uni


def compute_entropy(counter):
    """Shannon entropy from a Counter."""
    total = sum(counter.values())
    if total == 0:
        return 0.0
    return -sum((c/total)*math.log2(c/total)
                for c in counter.values() if c > 0)


def jsd(p_counter, q_counter):
    """Jensen-Shannon divergence between two frequency distributions."""
    all_keys = set(p_counter) | set(q_counter)
    p_total = sum(p_counter.values())
    q_total = sum(q_counter.values())
    if p_total == 0 or q_total == 0:
        return float('nan')
    m = {}
    for k in all_keys:
        m[k] = 0.5 * p_counter.get(k, 0)/p_total + 0.5 * q_counter.get(k, 0)/q_total
    kl_pm = sum((p_counter.get(k,0)/p_total) * math.log2((p_counter.get(k,0)/p_total) / m[k])
                for k in all_keys
                if p_counter.get(k,0) > 0 and m[k] > 0)
    kl_qm = sum((q_counter.get(k,0)/q_total) * math.log2((q_counter.get(k,0)/q_total) / m[k])
                for k in all_keys
                if q_counter.get(k,0) > 0 and m[k] > 0)
    return 0.5 * kl_pm + 0.5 * kl_qm


def words_to_glyphs(words):
    """Convert word list to flat glyph sequence (no word boundaries)."""
    glyphs = []
    for w in words:
        glyphs.extend(eva_to_glyphs(w))
    return glyphs


def words_to_glyphs_with_boundaries(words):
    """Convert word list to glyph sequence WITH space boundaries."""
    glyphs = []
    for i, w in enumerate(words):
        glyphs.extend(eva_to_glyphs(w))
        if i < len(words) - 1:
            glyphs.append(' ')
    return glyphs


def compute_fingerprint(words, name=''):
    """Compute full statistical fingerprint for a word list."""
    if not words:
        return None

    glyphs = words_to_glyphs(words)
    glyph_counter = Counter(glyphs)
    n_tokens = len(words)
    n_types = len(set(words))
    n_glyphs = len(glyphs)
    n_glyph_types = len(glyph_counter)

    # h_char ratio (glyph level — canonical)
    h_char = char_bigram_predictability(glyphs)

    # H(char)
    h_c = compute_entropy(glyph_counter)

    # Hapax ratio at midpoint
    mid = n_tokens // 2
    if mid > 0:
        mid_types = set(words[:mid])
        mid_hapax = sum(1 for w in mid_types
                        if Counter(words[:mid])[w] == 1)
        hapax_ratio = mid_hapax / len(mid_types) if mid_types else 0
    else:
        hapax_ratio = float('nan')

    # Mean word length (in glyphs)
    wlens = [len(eva_to_glyphs(w)) for w in words]
    mean_wlen = np.mean(wlens)

    # TTR at 5000 tokens (or max available)
    ttr_size = min(5000, n_tokens)
    ttr = len(set(words[:ttr_size])) / ttr_size

    # Zipf alpha (simple OLS on log-log rank-freq)
    word_freq = Counter(words)
    freqs = sorted(word_freq.values(), reverse=True)
    if len(freqs) > 1:
        ranks = np.arange(1, len(freqs) + 1, dtype=float)
        log_r = np.log(ranks)
        log_f = np.log(np.array(freqs, dtype=float))
        # OLS: log_f = a - alpha * log_r
        A = np.vstack([log_r, np.ones(len(log_r))]).T
        try:
            result = np.linalg.lstsq(A, log_f, rcond=None)
            alpha = -result[0][0]
        except Exception:
            alpha = float('nan')
    else:
        alpha = float('nan')

    # IC (index of coincidence)
    ic = sum(c*(c-1) for c in glyph_counter.values()) / (n_glyphs*(n_glyphs-1)) if n_glyphs > 1 else 0

    return {
        'name': name,
        'n_tokens': n_tokens,
        'n_types': n_types,
        'n_glyphs': n_glyphs,
        'n_glyph_types': n_glyph_types,
        'h_char': h_char,
        'h_c': h_c,
        'hapax_ratio': hapax_ratio,
        'mean_wlen': mean_wlen,
        'ttr': ttr,
        'zipf_alpha': alpha,
        'ic': ic,
        'glyph_counter': glyph_counter,
        'word_freq': word_freq,
    }


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 76)
    pr("line1_body_separation — LINE-1 / BODY SEPARATION: TWO ENCODING SUBSYSTEMS?")
    pr("=" * 76)
    pr()
    pr("  Does paragraph line 1 use a different encoding system from")
    pr("  lines 2+? If so, mixing them contaminates all statistics.")
    pr("  The h_char anomaly (0.641) might be partially an artifact.")
    pr()

    # ── STEP 1: PARSE AND SPLIT ──────────────────────────────────────
    pr("─" * 76)
    pr("STEP 1: PARSE AND SPLIT CORPUS")
    pr("─" * 76)
    pr()

    paragraphs = parse_all_data()

    # Split words by line position
    all_words = []
    l1_words = []       # paragraph line 1 (ALL words including para-initial)
    l1_no_w1 = []       # paragraph line 1 EXCLUDING para-initial word
    body_words = []     # lines 2+
    l1_last_words = []  # last word on each L1 line
    l2_first_words = [] # first word on each L2 line

    for para in paragraphs:
        for line_data in para['lines']:
            words = line_data['words']
            all_words.extend(words)

            if line_data['is_first_line']:
                l1_words.extend(words)
                if len(words) > 1:
                    l1_no_w1.extend(words[1:])
                if words:
                    l1_last_words.append(words[-1])
            else:
                body_words.extend(words)
                if line_data['line_num'] == 2 and words:
                    l2_first_words.append(words[0])

    pr(f"  Paragraphs:         {len(paragraphs)}")
    pr(f"  Total words:        {len(all_words)}")
    pr(f"  Line-1 words:       {len(l1_words)} ({len(l1_words)/len(all_words)*100:.1f}%)")
    pr(f"  Line-1 (no W1):    {len(l1_no_w1)}")
    pr(f"  Body words (L2+):  {len(body_words)} ({len(body_words)/len(all_words)*100:.1f}%)")
    pr(f"  L1→L2 transitions: {len(l2_first_words)}")
    pr()

    # Verify: total should match
    assert len(l1_words) + len(body_words) == len(all_words), \
        f"Split error: {len(l1_words)} + {len(body_words)} != {len(all_words)}"
    pr(f"  ✓ Split verified: {len(l1_words)} + {len(body_words)} = {len(all_words)}")
    pr()

    # ── STEP 2: FULL FINGERPRINT FOR EACH SUBSET ─────────────────────
    pr("─" * 76)
    pr("STEP 2: FULL FINGERPRINT FOR EACH SUBSET")
    pr("─" * 76)
    pr()

    fp_all  = compute_fingerprint(all_words, 'VMS (all)')
    fp_l1   = compute_fingerprint(l1_words, 'Line-1 (all)')
    fp_l1nw = compute_fingerprint(l1_no_w1, 'Line-1 (no W1)')
    fp_body = compute_fingerprint(body_words, 'Body (L2+)')

    subsets = [fp_all, fp_l1, fp_l1nw, fp_body]

    pr(f"  {'Subset':<20s} {'Tokens':>8s} {'Types':>8s} {'Glyphs':>8s} "
       f"{'GlyphTyp':>8s} {'h_char':>8s} {'H(c)':>8s} {'hapax':>8s} "
       f"{'wlen':>8s} {'TTR':>8s} {'Zipf':>8s} {'IC':>8s}")
    pr(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} "
       f"{'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")

    for fp in subsets:
        h = fp['h_char']
        pr(f"  {fp['name']:<20s} {fp['n_tokens']:>8d} {fp['n_types']:>8d} "
           f"{fp['n_glyphs']:>8d} {fp['n_glyph_types']:>8d} "
           f"{'nan' if math.isnan(h) else f'{h:.4f}':>8s} "
           f"{fp['h_c']:>8.4f} ")
        hap = fp['hapax_ratio']
        hap_s = 'nan' if math.isnan(hap) else f'{hap:.4f}'
        za = fp['zipf_alpha']
        za_s = 'nan' if math.isnan(za) else f'{za:.4f}'
        pr(f"           {hap_s:>8s} "
           f"{fp['mean_wlen']:>8.2f} {fp['ttr']:>8.4f} "
           f"{za_s:>8s} "
           f"{fp['ic']:>8.5f}")

    pr()
    # Compute deltas
    if not math.isnan(fp_body['h_char']) and not math.isnan(fp_all['h_char']):
        delta = fp_body['h_char'] - fp_all['h_char']
        pr(f"  h_char delta (Body − All): {delta:+.4f}")
        pr(f"  h_char delta (L1 − All):   {fp_l1['h_char'] - fp_all['h_char']:+.4f}")
        pr(f"  h_char delta (L1 − Body):  {fp_l1['h_char'] - fp_body['h_char']:+.4f}")
        pr()
        pr(f"  INTERPRETATION: If L1 is a different system, removing it should CHANGE")
        pr(f"  the body h_char. VMS whole = {fp_all['h_char']:.4f}. If body-only is ≈ same,")
        pr(f"  then L1 is NOT contaminating the measurement.")
    pr()

    # ── STEP 3: BOOTSTRAP CI FOR h_char ──────────────────────────────
    pr("─" * 76)
    pr("STEP 3: BOOTSTRAP CONFIDENCE INTERVALS FOR h_char")
    pr("─" * 76)
    pr()
    pr("  L1 has only ~10K glyphs — entropy estimates may be noisy.")
    pr("  Bootstrap resampling at word level to estimate uncertainty.")
    pr()

    n_boot = 500
    boot_results = {}

    for name, words in [('VMS (all)', all_words),
                        ('Line-1', l1_words),
                        ('Body (L2+)', body_words)]:
        boot_hchars = []
        for _ in range(n_boot):
            idx = np.random.randint(0, len(words), size=len(words))
            sample = [words[i] for i in idx]
            glyphs = words_to_glyphs(sample)
            h = char_bigram_predictability(glyphs)
            if not math.isnan(h):
                boot_hchars.append(h)

        if boot_hchars:
            mean_ = np.mean(boot_hchars)
            ci_lo = np.percentile(boot_hchars, 2.5)
            ci_hi = np.percentile(boot_hchars, 97.5)
            boot_results[name] = (mean_, ci_lo, ci_hi)
            pr(f"  {name:<20s}  mean={mean_:.4f}  95%CI=[{ci_lo:.4f}, {ci_hi:.4f}]")
        else:
            pr(f"  {name:<20s}  FAILED — insufficient data for bootstrap")

    pr()

    # Check if CIs overlap
    if 'Line-1' in boot_results and 'Body (L2+)' in boot_results:
        l1_lo, l1_hi = boot_results['Line-1'][1], boot_results['Line-1'][2]
        body_lo, body_hi = boot_results['Body (L2+)'][1], boot_results['Body (L2+)'][2]
        overlap = l1_lo <= body_hi and body_lo <= l1_hi
        pr(f"  L1 CI:   [{l1_lo:.4f}, {l1_hi:.4f}]")
        pr(f"  Body CI: [{body_lo:.4f}, {body_hi:.4f}]")
        pr(f"  Overlap: {'YES — NOT statistically distinguishable' if overlap else 'NO — SIGNIFICANTLY DIFFERENT'}")
    pr()

    # ── STEP 4: SIZE-CONTROLLED NULL MODEL ────────────────────────────
    pr("─" * 76)
    pr("STEP 4: SIZE-CONTROLLED NULL MODEL")
    pr("─" * 76)
    pr()
    pr("  CRITICAL: Small samples have upward-biased entropy estimates.")
    pr("  To test whether L1's h_char differs from body's, we must compare")
    pr("  L1 to random subsamples of body at the SAME SIZE.")
    pr()

    l1_size = len(l1_words)
    n_null = 200
    null_hchars = []

    for _ in range(n_null):
        idx = np.random.choice(len(body_words), size=l1_size, replace=False)
        sample = [body_words[i] for i in idx]
        glyphs = words_to_glyphs(sample)
        h = char_bigram_predictability(glyphs)
        if not math.isnan(h):
            null_hchars.append(h)

    if null_hchars and not math.isnan(fp_l1['h_char']):
        null_mean = np.mean(null_hchars)
        null_std = np.std(null_hchars)
        null_lo = np.percentile(null_hchars, 2.5)
        null_hi = np.percentile(null_hchars, 97.5)
        z_score = (fp_l1['h_char'] - null_mean) / null_std if null_std > 0 else 0

        pr(f"  Body subsampled to L1 size ({l1_size} words):")
        pr(f"    Null h_char: mean={null_mean:.4f}  std={null_std:.4f}  95%=[{null_lo:.4f}, {null_hi:.4f}]")
        pr(f"    Observed L1 h_char: {fp_l1['h_char']:.4f}")
        pr(f"    z-score: {z_score:.2f}")
        pr()
        if abs(z_score) > 2.0:
            pr(f"  → L1 h_char is SIGNIFICANTLY DIFFERENT from body at same size (|z|>2)")
        elif abs(z_score) > 1.5:
            pr(f"  → L1 h_char shows MARGINAL difference from body at same size (1.5<|z|<2)")
        else:
            pr(f"  → L1 h_char is NOT significantly different from body at same size (|z|<1.5)")
        pr()

        # Does body-subsampled h_char differ from full-body h_char?
        # (This tells us about SIZE BIAS)
        if not math.isnan(fp_body['h_char']):
            size_bias = null_mean - fp_body['h_char']
            pr(f"  SIZE BIAS CHECK:")
            pr(f"    Full body h_char:      {fp_body['h_char']:.4f}")
            pr(f"    Subsampled body h_char: {null_mean:.4f}")
            pr(f"    Size bias: {size_bias:+.4f}")
            pr(f"    → {'Significant' if abs(size_bias) > 0.01 else 'Negligible'} size effect "
               f"({'upward' if size_bias > 0 else 'downward'} bias at smaller sample)")
    pr()

    # ── STEP 5: ALPHABET / GLYPH INVENTORY COMPARISON ─────────────────
    pr("─" * 76)
    pr("STEP 5: GLYPH INVENTORY COMPARISON")
    pr("─" * 76)
    pr()

    l1_glyphs_counter = fp_l1['glyph_counter']
    body_glyphs_counter = fp_body['glyph_counter']

    l1_types = set(l1_glyphs_counter.keys())
    body_types = set(body_glyphs_counter.keys())
    all_types = l1_types | body_types
    l1_only = l1_types - body_types
    body_only = body_types - l1_types
    shared = l1_types & body_types

    pr(f"  L1 glyph types:     {len(l1_types)}")
    pr(f"  Body glyph types:   {len(body_types)}")
    pr(f"  Shared:             {len(shared)}")
    pr(f"  L1-only:            {len(l1_only)}: {sorted(l1_only)}")
    pr(f"  Body-only:          {len(body_only)}: {sorted(body_only)}")
    pr()

    # Frequency comparison
    pr(f"  GLYPH FREQUENCY COMPARISON (top 15):")
    pr(f"  {'Glyph':<8s} {'L1 freq':>10s} {'Body freq':>10s} {'L1/Body':>10s}")
    pr(f"  {'─'*8} {'─'*10} {'─'*10} {'─'*10}")

    l1_total = sum(l1_glyphs_counter.values())
    body_total = sum(body_glyphs_counter.values())

    # Sort by combined frequency
    combined = Counter()
    for g in all_types:
        combined[g] = l1_glyphs_counter.get(g, 0) + body_glyphs_counter.get(g, 0)

    for g, _ in combined.most_common(20):
        l1f = l1_glyphs_counter.get(g, 0) / l1_total * 100
        bf = body_glyphs_counter.get(g, 0) / body_total * 100
        ratio = l1f / bf if bf > 0 else float('inf')
        marker = ''
        if ratio > 2.0: marker = '★★ L1-enriched'
        elif ratio > 1.5: marker = '★ L1-enriched'
        elif ratio < 0.5: marker = '★★ body-enriched'
        elif ratio < 0.67: marker = '★ body-enriched'
        pr(f"  {g:<8s} {l1f:>9.2f}% {bf:>9.2f}% {ratio:>9.2f}x  {marker}")

    pr()

    # JSD
    jsd_val = jsd(l1_glyphs_counter, body_glyphs_counter)
    pr(f"  Jensen-Shannon divergence (L1 vs Body): {jsd_val:.4f} bits")
    pr(f"  (0 = identical distributions, 1 = completely different)")
    pr()

    # What JSD would we expect from random splits?
    jsd_nulls = []
    for _ in range(200):
        n_split = len(l1_words)
        idx = np.random.choice(len(all_words), size=n_split, replace=False)
        mask = np.zeros(len(all_words), dtype=bool)
        mask[idx] = True
        subset_a = [all_words[i] for i in range(len(all_words)) if mask[i]]
        subset_b = [all_words[i] for i in range(len(all_words)) if not mask[i]]
        ca = Counter(words_to_glyphs(subset_a))
        cb = Counter(words_to_glyphs(subset_b))
        jsd_nulls.append(jsd(ca, cb))

    jsd_null_mean = np.mean(jsd_nulls)
    jsd_null_std = np.std(jsd_nulls)
    jsd_z = (jsd_val - jsd_null_mean) / jsd_null_std if jsd_null_std > 0 else 0
    pr(f"  Random-split null: mean JSD={jsd_null_mean:.4f} std={jsd_null_std:.4f}")
    pr(f"  Observed JSD z-score: {jsd_z:.1f}")
    pr(f"  → {'L1 and Body have SIGNIFICANTLY different glyph distributions' if jsd_z > 3 else 'L1 and Body glyph distributions are NOT strongly different'}")
    pr()

    # ── STEP 6: VOCABULARY OVERLAP ────────────────────────────────────
    pr("─" * 76)
    pr("STEP 6: VOCABULARY OVERLAP TEST")
    pr("─" * 76)
    pr()

    l1_vocab = set(l1_words)
    body_vocab = set(body_words)
    shared_vocab = l1_vocab & body_vocab
    l1_only_vocab = l1_vocab - body_vocab
    body_only_vocab = body_vocab - l1_vocab

    pr(f"  L1 word types:    {len(l1_vocab)}")
    pr(f"  Body word types:  {len(body_vocab)}")
    pr(f"  Shared types:     {len(shared_vocab)} ({len(shared_vocab)/len(l1_vocab)*100:.1f}% of L1 vocab)")
    pr(f"  L1-only types:    {len(l1_only_vocab)} ({len(l1_only_vocab)/len(l1_vocab)*100:.1f}% of L1 vocab)")
    pr(f"  Body-only types:  {len(body_only_vocab)}")
    pr()

    # Token coverage: what fraction of L1 TOKENS are shared words?
    l1_shared_tokens = sum(1 for w in l1_words if w in body_vocab)
    pr(f"  L1 tokens that also appear in body: {l1_shared_tokens}/{len(l1_words)} "
       f"({l1_shared_tokens/len(l1_words)*100:.1f}%)")
    pr()

    # Null model: random subsample of body to L1 size — how many unique types
    # overlap with the rest?
    null_overlaps = []
    body_words_arr = np.array(body_words)
    for _ in range(200):
        idx = np.random.choice(len(body_words), size=len(l1_words), replace=False)
        mask = np.ones(len(body_words), dtype=bool)
        mask[idx] = False
        sub = set(body_words_arr[idx])
        rest = set(body_words_arr[mask])
        null_overlaps.append(len(sub & rest) / len(sub) * 100)

    null_ov_mean = np.mean(null_overlaps)
    null_ov_std = np.std(null_overlaps)
    actual_ov = len(shared_vocab) / len(l1_vocab) * 100
    ov_z = (actual_ov - null_ov_mean) / null_ov_std if null_ov_std > 0 else 0

    pr(f"  NULL MODEL (random body subsample, same size):")
    pr(f"    Expected overlap: {null_ov_mean:.1f}% (std={null_ov_std:.1f}%)")
    pr(f"    Actual L1↔body overlap: {actual_ov:.1f}%")
    pr(f"    z-score: {ov_z:.1f}")
    if ov_z < -2:
        pr(f"    → L1 vocabulary is SIGNIFICANTLY LESS overlapping than expected")
        pr(f"      (supports two-subsystem hypothesis)")
    elif ov_z < -1:
        pr(f"    → L1 vocabulary shows MARGINAL lower overlap")
    else:
        pr(f"    → L1 vocabulary overlap is NORMAL for a random subset")
        pr(f"      (does NOT support two-subsystem hypothesis)")
    pr()

    # Top L1-only words
    l1_only_freq = Counter()
    for w in l1_words:
        if w in l1_only_vocab:
            l1_only_freq[w] += 1

    pr(f"  TOP 20 L1-ONLY WORDS (never appear in body text):")
    for w, c in l1_only_freq.most_common(20):
        pr(f"    {w:<20s}  count={c}")
    pr()

    # ── STEP 7: CROSS-BOUNDARY TRANSITION ANALYSIS ────────────────────
    pr("─" * 76)
    pr("STEP 7: CROSS-BOUNDARY TRANSITION ANALYSIS")
    pr("─" * 76)
    pr()
    pr("  If L1 is a different system, there should be a discontinuity")
    pr("  at the L1→L2 boundary. We test last-glyph-of-L1 → first-glyph-of-L2")
    pr("  transitions vs within-L1 and within-body transitions.")
    pr()

    # Collect glyph bigrams at different positions
    within_l1_bigrams = Counter()    # consecutive glyphs WITHIN a L1 line
    within_body_bigrams = Counter()  # consecutive glyphs WITHIN body lines
    cross_bigrams = Counter()        # last glyph of L1 → first glyph of L2
    within_body_line_bigrams = Counter()  # last glyph of line N → first glyph of line N+1 (within body)

    for para in paragraphs:
        prev_line_last_glyph = None
        prev_is_l1 = False

        for line_data in para['lines']:
            words = line_data['words']
            if not words:
                continue

            glyphs = words_to_glyphs(words)
            if not glyphs:
                continue

            # Within-line bigrams
            for i in range(1, len(glyphs)):
                if line_data['is_first_line']:
                    within_l1_bigrams[(glyphs[i-1], glyphs[i])] += 1
                else:
                    within_body_bigrams[(glyphs[i-1], glyphs[i])] += 1

            # Cross-line transition
            if prev_line_last_glyph is not None:
                if prev_is_l1 and not line_data['is_first_line']:
                    # L1 → L2 boundary
                    cross_bigrams[(prev_line_last_glyph, glyphs[0])] += 1
                elif not prev_is_l1 and not line_data['is_first_line']:
                    # Body → Body line boundary
                    within_body_line_bigrams[(prev_line_last_glyph, glyphs[0])] += 1

            prev_line_last_glyph = glyphs[-1]
            prev_is_l1 = line_data['is_first_line']

    # Compute entropy of transition distributions
    h_within_body = compute_entropy(within_body_bigrams)
    h_cross = compute_entropy(cross_bigrams)
    h_body_line = compute_entropy(within_body_line_bigrams)

    pr(f"  Within-L1 bigram types:     {len(within_l1_bigrams)}")
    pr(f"  Within-Body bigram types:   {len(within_body_bigrams)}")
    pr(f"  L1→L2 cross bigrams:        {len(cross_bigrams)} (from {sum(cross_bigrams.values())} transitions)")
    pr(f"  Body→Body line bigrams:     {len(within_body_line_bigrams)} (from {sum(within_body_line_bigrams.values())} transitions)")
    pr()

    # Compare cross-boundary JSD to within-body-line JSD
    jsd_cross_vs_bodyline = jsd(cross_bigrams, within_body_line_bigrams)
    pr(f"  JSD (L1→L2 vs Body→Body line transitions): {jsd_cross_vs_bodyline:.4f}")
    pr(f"  → {'HIGH — L1→L2 boundary is DIFFERENT' if jsd_cross_vs_bodyline > 0.05 else 'LOW — L1→L2 boundary is SIMILAR to body line breaks'}")
    pr()

    # What are the most common final glyphs on L1 and first glyphs on L2?
    l1_final = Counter()
    l2_initial = Counter()
    body_final = Counter()
    body_initial = Counter()

    for para in paragraphs:
        for i, line_data in enumerate(para['lines']):
            words = line_data['words']
            if not words:
                continue
            glyphs = words_to_glyphs(words)
            if not glyphs:
                continue

            if line_data['is_first_line']:
                l1_final[glyphs[-1]] += 1
            elif line_data['line_num'] == 2:
                l2_initial[glyphs[0]] += 1
            else:
                # Generic body
                body_final[glyphs[-1]] += 1
                if i + 1 < len(para['lines']):
                    pass  # next line's first glyph is body_initial
                body_initial[glyphs[0]] += 1

    pr(f"  TOP 5 FINAL GLYPHS on L1: {l1_final.most_common(5)}")
    pr(f"  TOP 5 FIRST GLYPHS on L2: {l2_initial.most_common(5)}")
    pr(f"  TOP 5 FINAL GLYPHS in body: {body_final.most_common(5)}")
    pr(f"  TOP 5 FIRST GLYPHS in body: {body_initial.most_common(5)}")
    pr()

    # ── STEP 8: WHAT HAPPENS TO THE 13-CHARACTER ESTIMATE? ────────────
    pr("─" * 76)
    pr("STEP 8: FUNCTIONAL ALPHABET SIZE IN BODY TEXT ONLY")
    pr("─" * 76)
    pr()
    pr("  The video argues VMS has ~13 functional letters after removing")
    pr("  first-line-only and line-end-only glyphs. What's the count")
    pr("  after we actually separate L1 from body?")
    pr()

    # Count glyphs in body text by word position (I/M/F)
    body_pos_counts = {'I': Counter(), 'M': Counter(), 'F': Counter()}

    for w in body_words:
        glyphs = eva_to_glyphs(w)
        for i, g in enumerate(glyphs):
            if len(glyphs) == 1:
                body_pos_counts['I'][g] += 1  # single-glyph word = initial
            elif i == 0:
                body_pos_counts['I'][g] += 1
            elif i == len(glyphs) - 1:
                body_pos_counts['F'][g] += 1
            else:
                body_pos_counts['M'][g] += 1

    # A glyph is "functional in position X" if it appears there ≥1% of the time
    threshold = 0.01  # 1%
    pos_totals = {pos: sum(c.values()) for pos, c in body_pos_counts.items()}

    pr(f"  Body text glyph counts by position:")
    pr(f"    Initial: {pos_totals['I']} glyphs")
    pr(f"    Medial:  {pos_totals['M']} glyphs")
    pr(f"    Final:   {pos_totals['F']} glyphs")
    pr()

    functional = {'I': set(), 'M': set(), 'F': set()}
    for pos in ['I', 'M', 'F']:
        total = pos_totals[pos]
        for g, c in body_pos_counts[pos].items():
            if c / total >= threshold:
                functional[pos].add(g)

    pr(f"  Functional glyphs (≥1% in position) — BODY ONLY:")
    pr(f"    Initial: {len(functional['I'])} — {sorted(functional['I'])}")
    pr(f"    Medial:  {len(functional['M'])} — {sorted(functional['M'])}")
    pr(f"    Final:   {len(functional['F'])} — {sorted(functional['F'])}")
    pr()

    # Glyphs functional in ALL three positions
    all_three = functional['I'] & functional['M'] & functional['F']
    at_least_two = (functional['I'] & functional['M']) | (functional['I'] & functional['F']) | (functional['M'] & functional['F'])
    any_pos = functional['I'] | functional['M'] | functional['F']

    pr(f"  Functional in all 3 positions (I+M+F): {len(all_three)} — {sorted(all_three)}")
    pr(f"  Functional in ≥2 positions:           {len(at_least_two)} — {sorted(at_least_two)}")
    pr(f"  Functional in ≥1 position:            {len(any_pos)} — {sorted(any_pos)}")
    pr()

    # Now same for L1 — what glyphs does L1 add?
    l1_pos_counts = {'I': Counter(), 'M': Counter(), 'F': Counter()}
    for w in l1_words:
        glyphs = eva_to_glyphs(w)
        for i, g in enumerate(glyphs):
            if len(glyphs) == 1:
                l1_pos_counts['I'][g] += 1
            elif i == 0:
                l1_pos_counts['I'][g] += 1
            elif i == len(glyphs) - 1:
                l1_pos_counts['F'][g] += 1
            else:
                l1_pos_counts['M'][g] += 1

    l1_functional = {'I': set(), 'M': set(), 'F': set()}
    l1_pos_totals = {pos: sum(c.values()) for pos, c in l1_pos_counts.items()}
    for pos in ['I', 'M', 'F']:
        total = l1_pos_totals[pos]
        for g, c in l1_pos_counts[pos].items():
            if total > 0 and c / total >= threshold:
                l1_functional[pos].add(g)

    pr(f"  Functional glyphs (≥1% in position) — LINE-1 ONLY:")
    pr(f"    Initial: {len(l1_functional['I'])} — {sorted(l1_functional['I'])}")
    pr(f"    Medial:  {len(l1_functional['M'])} — {sorted(l1_functional['M'])}")
    pr(f"    Final:   {len(l1_functional['F'])} — {sorted(l1_functional['F'])}")
    pr()

    # What glyphs are functional on L1 but NOT in body?
    l1_any = l1_functional['I'] | l1_functional['M'] | l1_functional['F']
    l1_extra = l1_any - any_pos
    body_extra = any_pos - l1_any
    pr(f"  Glyphs functional on L1 but NOT in body: {len(l1_extra)} — {sorted(l1_extra)}")
    pr(f"  Glyphs functional in body but NOT on L1: {len(body_extra)} — {sorted(body_extra)}")
    pr()

    # ── STEP 9: POSITIONAL VARIANT CHECK ──────────────────────────────
    pr("─" * 76)
    pr("STEP 9: POSITIONAL VARIANT HYPOTHESIS — CAN WE MERGE IN BODY?")
    pr("─" * 76)
    pr()
    pr("  The video argues that complementary-distribution pairs could be")
    pr("  positional variants (like Arabic letter forms). In body-only text,")
    pr("  do we see cleaner complementary distribution?")
    pr()

    # For each glyph, compute positional profile in body text
    body_all_glyphs = sum(pos_totals.values())
    pr(f"  {'Glyph':<8s} {'I%':>8s} {'M%':>8s} {'F%':>8s} {'Total':>8s} {'Profile':>20s}")
    pr(f"  {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*20}")

    glyph_profiles = {}
    for g in sorted(any_pos, key=lambda x: -(body_pos_counts['I'].get(x,0) +
                                              body_pos_counts['M'].get(x,0) +
                                              body_pos_counts['F'].get(x,0))):
        ci = body_pos_counts['I'].get(g, 0)
        cm = body_pos_counts['M'].get(g, 0)
        cf = body_pos_counts['F'].get(g, 0)
        total = ci + cm + cf
        if total == 0:
            continue
        pi = ci / total * 100
        pm = cm / total * 100
        pf = cf / total * 100

        # Classify
        profile = []
        if pi > 10: profile.append('I')
        if pm > 10: profile.append('M')
        if pf > 10: profile.append('F')
        profile_str = '+'.join(profile) if profile else '?'

        glyph_profiles[g] = (pi, pm, pf, profile_str)
        pr(f"  {g:<8s} {pi:>7.1f}% {pm:>7.1f}% {pf:>7.1f}% {total:>8d} {profile_str:>20s}")

    pr()

    # Count compressed alphabet
    profile_groups = defaultdict(list)
    for g, (pi, pm, pf, prof) in glyph_profiles.items():
        profile_groups[prof].append(g)

    pr(f"  POSITIONAL PROFILE GROUPS (body text):")
    for prof in sorted(profile_groups):
        members = profile_groups[prof]
        pr(f"    {prof:<12s}: {len(members)} glyphs — {sorted(members)}")

    pr()

    # Count: how many COMPRESSED letters if we merge ALL I-only, M-only, F-only
    # glyphs that could be variants?
    i_only = [g for g, (pi, pm, pf, prof) in glyph_profiles.items() if prof == 'I']
    m_only = [g for g, (pi, pm, pf, prof) in glyph_profiles.items() if prof == 'M']
    f_only = [g for g, (pi, pm, pf, prof) in glyph_profiles.items() if prof == 'F']
    imf = [g for g, (pi, pm, pf, prof) in glyph_profiles.items() if prof == 'I+M+F']

    pr(f"  Position-restricted glyphs (body only):")
    pr(f"    I-only:   {len(i_only)} — {sorted(i_only)}")
    pr(f"    M-only:   {len(m_only)} — {sorted(m_only)}")
    pr(f"    F-only:   {len(f_only)} — {sorted(f_only)}")
    pr(f"    I+M+F:    {len(imf)} — {sorted(imf)}")
    pr()

    # Maximum possible compression: if ALL I-only are variants of something,
    # ALL M-only are variants of something, ALL F-only are variants of something
    # then the "true alphabet" = I+M+F glyphs + max(I-only, M-only, F-only)
    # (since each "true letter" needs one form per position)
    max_compressed = len(imf) + max(len(i_only), len(m_only), len(f_only))
    min_compressed = len(imf)  # if ALL restricted glyphs are variants of IMF glyphs

    pr(f"  COMPRESSED ALPHABET ESTIMATE (body only):")
    pr(f"    Unrestricted (I+M+F) core: {len(imf)} letters")
    pr(f"    Maximum (all restricted are independent): {len(any_pos)} letters")
    pr(f"    Minimum (all restricted are variants): {min_compressed} letters")
    pr(f"    Best estimate (restricted fill missing slots): {max_compressed} letters")
    pr()

    # ── STEP 10: SYNTHESIS ────────────────────────────────────────────
    pr("─" * 76)
    pr("STEP 10: SYNTHESIS AND CRITICAL ASSESSMENT")
    pr("─" * 76)
    pr()

    h_all = fp_all['h_char']
    h_l1 = fp_l1['h_char']
    h_body = fp_body['h_char']

    # Key question 1: Does removing L1 change h_char?
    pr("  Q1: DOES REMOVING LINE-1 CHANGE h_char?")
    if not math.isnan(h_all) and not math.isnan(h_body):
        delta_body = h_body - h_all
        pr(f"      h_char (all):  {h_all:.4f}")
        pr(f"      h_char (body): {h_body:.4f}")
        pr(f"      Delta:         {delta_body:+.4f}")
        if abs(delta_body) < 0.01:
            pr(f"      → NEGLIGIBLE CHANGE. L1 is NOT contaminating the measurement.")
            q1_result = 'negligible'
        elif abs(delta_body) < 0.03:
            pr(f"      → SMALL CHANGE. L1 has minor effect on h_char.")
            q1_result = 'small'
        else:
            pr(f"      → SUBSTANTIAL CHANGE. L1 significantly affects h_char.")
            q1_result = 'substantial'
    else:
        q1_result = 'unknown'
    pr()

    # Key question 2: Is L1 h_char different from body h_char?
    pr("  Q2: IS L1 h_char DIFFERENT FROM BODY h_char?")
    if not math.isnan(h_l1) and not math.isnan(h_body):
        delta_l1_body = h_l1 - h_body
        pr(f"      h_char (L1):   {h_l1:.4f}")
        pr(f"      h_char (body): {h_body:.4f}")
        pr(f"      Delta:         {delta_l1_body:+.4f}")
        if 'Line-1' in boot_results and 'Body (L2+)' in boot_results:
            l1_ci = boot_results['Line-1']
            body_ci = boot_results['Body (L2+)']
            ci_overlap = l1_ci[1] <= body_ci[2] and body_ci[1] <= l1_ci[2]
            pr(f"      Bootstrap CIs overlap: {'YES' if ci_overlap else 'NO'}")
    pr()

    # Key question 3: Does body-only h_char approach natural language?
    pr("  Q3: DOES BODY-ONLY h_char APPROACH NATURAL LANGUAGE (~0.83)?")
    if not math.isnan(h_body):
        gap_all = 0.83 - h_all
        gap_body = 0.83 - h_body
        gap_closed = 1 - (gap_body / gap_all) if gap_all != 0 else 0
        pr(f"      Natural lang range: 0.82-0.87")
        pr(f"      VMS (all):      {h_all:.4f}  (gap to 0.83: {gap_all:.4f})")
        pr(f"      VMS (body):     {h_body:.4f}  (gap to 0.83: {gap_body:.4f})")
        pr(f"      Gap closed:     {gap_closed*100:.1f}%")
        if gap_closed < 5:
            pr(f"      → VIRTUALLY NO GAP CLOSURE. The h_char anomaly is intrinsic")
            pr(f"        to the encoding system, not an artifact of L1 contamination.")
        elif gap_closed < 20:
            pr(f"      → MODEST GAP CLOSURE ({gap_closed:.0f}%). L1 explains some but not most.")
        else:
            pr(f"      → SIGNIFICANT GAP CLOSURE ({gap_closed:.0f}%). L1 is a real confound.")
    pr()

    # Key question 4: Do L1 and body use different glyph distributions?
    pr("  Q4: DO L1 AND BODY USE DIFFERENT GLYPH DISTRIBUTIONS?")
    pr(f"      JSD: {jsd_val:.4f} (z={jsd_z:.1f} vs random split)")
    if jsd_z > 5:
        pr(f"      → VERY DIFFERENT distributions (z>{jsd_z:.0f})")
    elif jsd_z > 3:
        pr(f"      → SIGNIFICANTLY DIFFERENT distributions")
    elif jsd_z > 2:
        pr(f"      → MARGINALLY DIFFERENT distributions")
    else:
        pr(f"      → NOT SIGNIFICANTLY DIFFERENT from random split")
    pr()

    # Key question 5: Functional alphabet in body
    pr("  Q5: FUNCTIONAL ALPHABET SIZE IN BODY TEXT")
    pr(f"      Unrestricted (I+M+F) core: {len(imf)} glyphs")
    pr(f"      Total functional (any position): {len(any_pos)} glyphs")
    pr(f"      Best compressed estimate: {max_compressed} letters")
    pr()

    # Overall assessment
    pr("  OVERALL ASSESSMENT:")
    pr()

    # Count how many signals indicate different subsystems
    signals_different = 0
    signals_same = 0

    if q1_result in ('negligible',):
        signals_same += 1
    elif q1_result in ('substantial',):
        signals_different += 1

    if jsd_z > 3:
        signals_different += 1
    else:
        signals_same += 1

    if 'Line-1' in boot_results and 'Body (L2+)' in boot_results:
        ci_overlap = boot_results['Line-1'][1] <= boot_results['Body (L2+)'][2] and \
                     boot_results['Body (L2+)'][1] <= boot_results['Line-1'][2]
        if not ci_overlap:
            signals_different += 1
        else:
            signals_same += 1

    pr(f"  Signals for DIFFERENT subsystems: {signals_different}")
    pr(f"  Signals for SAME system:          {signals_same}")
    pr()

    if signals_different > signals_same:
        pr("  VERDICT: There is evidence that L1 and body text are statistically")
        pr("  different subsystems. However, removing L1 does NOT substantially")
        pr("  explain the h_char anomaly — the anomaly is intrinsic.")
    elif signals_same > signals_different:
        pr("  VERDICT: L1 and body text are NOT strongly distinguishable as")
        pr("  separate encoding systems. The glyph distribution differences")
        pr("  (driven by {p,f} enrichment) are real but do not constitute")
        pr("  a fully separate system — they represent a positional/structural")
        pr("  overlay on the same underlying encoding.")
    else:
        pr("  VERDICT: Mixed evidence. L1 shows some distributional differences")
        pr("  from body text, but these are modest and do not explain the")
        pr("  core h_char anomaly.")
    pr()

    pr("  CRITICAL CAVEATS:")
    pr("  1. L1 is only ~7% of the corpus. Removing it changes almost nothing")
    pr("     about corpus-level statistics. This is EXPECTED and does NOT prove")
    pr("     L1 is the same system — it just means the mixture effect is small.")
    pr("  2. Small-sample bias inflates entropy estimates for L1. The bootstrap")
    pr("     CI accounts for this, but point estimates should be treated cautiously.")
    pr("  3. Even if L1 IS a different system, the body-only h_char would still")
    pr("     be far below natural language (~0.83). The anomaly is NOT explained")
    pr("     by L1 contamination.")
    pr("  4. The glyph distribution difference (if significant) could reflect")
    pr("     TOPIC differences (first lines = section headers?) rather than")
    pr("     encoding differences.")
    pr("  5. Body text alone retains the positional slot grammar (I-M-F)")
    pr("     established in glyph_resegmentation-67 — that structure is intrinsic.")
    pr()

    # ── Save ──────────────────────────────────────────────────────────
    outpath = RESULTS_DIR / 'line1_body_separation.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Results saved: {outpath}")


if __name__ == '__main__':
    main()
