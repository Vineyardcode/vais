#!/usr/bin/env python3
"""
Phase 97 — Slot Grammar as h_char Generative Model

═══════════════════════════════════════════════════════════════════════

CENTRAL QUESTION:
  Does the LOOP slot grammar QUANTITATIVELY predict h_char ≈ 0.65?

  Through Phase 96 we've established:
    - h_char ≈ 0.65 at glyph level (far below NL 0.82-0.90)
    - NOT explained by homophones (Phase 96)
    - NOT explained by Currier A/B mixing (Phase 95)
    - NOT explained by Pelling cipher (Phase 85)
    - IS encoding-structural (Phase 96 verdict, 85% confidence)

  The LOOP grammar forces strict slot ordering within chunks:
    S1(onset) → S2(front) → S3(core) → S4(back) → S5(coda)
  Each slot draws from a tiny inventory (1-5 glyphs).
  This MUST reduce bigram entropy, but by how much?

METHOD:
  1. Parse VMS into glyph stream with per-glyph slot annotations
  2. Decompose h_char by transition type:
     a. Within-chunk same-slot (e→e in SLOT2)
     b. Within-chunk slot→slot (SLOT1→SLOT2 etc.)
     c. Cross-chunk within-word (SLOT5→SLOT1 of next chunk)
     d. Cross-word boundary
  3. Build null models:
     A. SLOT-RESAMPLE: keep slot patterns, resample glyphs from P(glyph|slot)
        → isolates "having a slot grammar" from "correlated fills"
     B. SLOT-SHUFFLE: permute glyph assignments within each slot across corpus
        → preserves exact marginals AND slot structure, kills specific sequences
     C. FLAT-SHUFFLE: random permutation of entire glyph stream
        → expected h_char ≈ 1.0 (destroys all structure)
  4. Compare: h_char_obs vs h_char_slot_resample vs h_char_flat
  5. NL baselines: parse Latin/German/etc. into CVC syllable slots,
     apply same decomposition
  6. Currier A vs B separately

PREDICTION:
  If h_char_slot_resample ≈ h_char_obs:
    → slot grammar ALONE explains the anomaly, h_char argument against
      NL collapses
  If h_char_obs < h_char_slot_resample:
    → additional within-slot correlations exist beyond grammar
  If h_char_obs > h_char_slot_resample:
    → slot grammar predicts even lower h_char (unlikely)

═══════════════════════════════════════════════════════════════════════
"""

import os, re, glob, math, json
from collections import Counter, defaultdict
import random

_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLIO_DIR = os.path.join(_PROJECT_DIR, "folios")
LATIN_DIR = os.path.join(_PROJECT_DIR, "data", "latin_texts")
RESULTS_DIR = os.path.join(_PROJECT_DIR, "results")

# ============================================================
# 1. EVA PARSING (from Phase 85)
# ============================================================
TRIGRAPHS = {'cth', 'ckh', 'cph', 'cfh'}
DIGRAPHS = {'ch', 'sh', 'th', 'kh', 'ph', 'fh'}

def eva_to_glyphs(token):
    glyphs = []
    i = 0
    t = token.lower()
    while i < len(t):
        if i + 2 < len(t) and t[i:i+3] in TRIGRAPHS:
            glyphs.append(t[i:i+3]); i += 3
        elif i + 1 < len(t) and t[i:i+2] in DIGRAPHS:
            glyphs.append(t[i:i+2]); i += 2
        elif t[i].isalpha():
            glyphs.append(t[i]); i += 1
        else:
            i += 1
    return glyphs

# ============================================================
# 2. LOOP 5-SLOT GRAMMAR (canonical Phase 85 model)
# ============================================================
SLOT1 = {'ch', 'sh', 'y'}
SLOT2_RUNS = {'e'}
SLOT2_SINGLE = {'q', 'a'}
SLOT3 = {'o'}
SLOT4_RUNS = {'i'}
SLOT4_SINGLE = {'d'}
SLOT5 = {'y', 'p', 'f', 'k', 'l', 'r', 's', 't',
         'cth', 'ckh', 'cph', 'cfh', 'n', 'm'}
MAX_CHUNKS = 6

def parse_one_chunk_with_slots(glyphs, pos):
    """Parse one chunk, returning (glyph_list, slot_assignments, new_pos).
    slot_assignments is a list of (glyph, slot_number) pairs.
    """
    start = pos
    result = []

    # SLOT 1: onset
    if pos < len(glyphs) and glyphs[pos] in SLOT1:
        result.append((glyphs[pos], 1)); pos += 1

    # SLOT 2: front vowel
    if pos < len(glyphs):
        if glyphs[pos] in SLOT2_RUNS:
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT2_RUNS and count < 3:
                result.append((glyphs[pos], 2)); pos += 1; count += 1
        elif glyphs[pos] in SLOT2_SINGLE:
            result.append((glyphs[pos], 2)); pos += 1

    # SLOT 3: core 'o'
    if pos < len(glyphs) and glyphs[pos] in SLOT3:
        result.append((glyphs[pos], 3)); pos += 1

    # SLOT 4: back vowel
    if pos < len(glyphs):
        if glyphs[pos] in SLOT4_RUNS:
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT4_RUNS and count < 3:
                result.append((glyphs[pos], 4)); pos += 1; count += 1
        elif glyphs[pos] in SLOT4_SINGLE:
            result.append((glyphs[pos], 4)); pos += 1

    # SLOT 5: coda
    if pos < len(glyphs) and glyphs[pos] in SLOT5:
        result.append((glyphs[pos], 5)); pos += 1

    if pos == start:
        return None, None, pos
    return [g for g, s in result], result, pos


def parse_word_full(word_str):
    """Parse a word into chunks with full slot annotations.
    Returns list of chunks, each chunk = list of (glyph, slot) pairs.
    Also returns list of unparsed glyphs.
    """
    glyphs = eva_to_glyphs(word_str)
    chunks = []
    unparsed = []
    pos = 0
    while pos < len(glyphs) and len(chunks) < MAX_CHUNKS:
        glyph_list, slot_pairs, new_pos = parse_one_chunk_with_slots(glyphs, pos)
        if glyph_list is None:
            unparsed.append(glyphs[pos])
            pos += 1
        else:
            chunks.append(slot_pairs)
            pos = new_pos
    while pos < len(glyphs):
        unparsed.append(glyphs[pos])
        pos += 1
    return chunks, unparsed


# ============================================================
# 3. BUILD ANNOTATED GLYPH STREAM
# ============================================================
def build_annotated_stream(folio_dir, folio_filter=None):
    """Build a glyph stream with transition-type annotations.
    Returns:
      glyph_stream: list of glyphs
      slot_stream: list of slot numbers (1-5, 0 for unparsed)
      trans_types: list of transition types (len = len(glyph_stream)-1)
        'ws' = within-slot (same slot, same chunk, e.g. e→e in SLOT2)
        'sc' = slot-change (different slot, same chunk)
        'cc' = cross-chunk (within same word)
        'cw' = cross-word (word boundary)
    """
    glyph_stream = []
    slot_stream = []
    trans_types = []

    for fpath in sorted(glob.glob(os.path.join(folio_dir, "f*.txt"))):
        fname = os.path.basename(fpath)
        m_fnum = re.match(r'f(\d+)', fname)
        if not m_fnum:
            continue
        fnum = int(m_fnum.group(1))
        if folio_filter and not folio_filter(fnum):
            continue

        with open(fpath, 'r', encoding='utf-8') as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                m = re.match(r'<[^>]+>\s*(.*)', line)
                if not m:
                    continue
                content = m.group(1)
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'\[[^\]]*\]', '', content)
                tokens = re.split(r'[.\s,;]+', content)
                tokens = [t.strip() for t in tokens if t.strip()
                          and not t.startswith('!')
                          and not t.startswith('%')
                          and t != '?' and len(t) > 0]

                for tok in tokens:
                    chunks, unparsed = parse_word_full(tok)
                    if not chunks and not unparsed:
                        continue

                    word_start = len(glyph_stream)

                    for ci, chunk in enumerate(chunks):
                        for gi, (glyph, slot) in enumerate(chunk):
                            glyph_stream.append(glyph)
                            slot_stream.append(slot)

                            if len(glyph_stream) > 1:
                                if len(glyph_stream) - 1 == word_start and ci == 0 and gi == 0:
                                    # First glyph of new word
                                    trans_types.append('cw')
                                elif gi == 0 and ci > 0:
                                    # First glyph of new chunk (same word)
                                    trans_types.append('cc')
                                elif slot == slot_stream[-2]:
                                    # Same slot as previous glyph
                                    trans_types.append('ws')
                                else:
                                    # Different slot, same chunk
                                    trans_types.append('sc')

                    # Handle unparsed glyphs
                    for ug in unparsed:
                        glyph_stream.append(ug)
                        slot_stream.append(0)
                        if len(glyph_stream) > 1:
                            trans_types.append('sc')  # best guess

    return glyph_stream, slot_stream, trans_types


# ============================================================
# 4. ENTROPY COMPUTATIONS
# ============================================================
def compute_hchar(sequence):
    """Compute h_char = H2/H1 for a glyph sequence."""
    if len(sequence) < 2:
        return None, None, None

    counts = Counter(sequence)
    total = len(sequence)
    h1 = -sum((c / total) * math.log2(c / total) for c in counts.values())
    if h1 < 1e-10:
        return h1, 0.0, 0.0

    bigram_counts = Counter()
    context_counts = Counter()
    for i in range(1, len(sequence)):
        bigram_counts[(sequence[i-1], sequence[i])] += 1
        context_counts[sequence[i-1]] += 1

    h2 = 0.0
    for (prev, curr), count in bigram_counts.items():
        p_bigram = count / (total - 1)
        p_cond = count / context_counts[prev]
        h2 -= p_bigram * math.log2(p_cond)

    return h1, h2, h2 / h1


def compute_conditional_entropy_by_type(glyph_stream, trans_types):
    """Decompose H2 by transition type.
    Returns dict: type → (count, H2_contribution, weighted_entropy).
    """
    # Group bigrams by transition type
    type_bigrams = defaultdict(list)
    for i, tt in enumerate(trans_types):
        type_bigrams[tt].append((glyph_stream[i], glyph_stream[i+1]))

    total_bigrams = len(trans_types)
    results = {}

    for tt, bigrams in type_bigrams.items():
        n = len(bigrams)
        frac = n / total_bigrams

        # Compute conditional entropy for this transition type
        bg_counts = Counter(bigrams)
        ctx_counts = Counter(b[0] for b in bigrams)

        h2_local = 0.0
        for (prev, curr), count in bg_counts.items():
            p_bg = count / n
            p_cond = count / ctx_counts[prev]
            h2_local -= p_bg * math.log2(p_cond)

        # Contribution to overall H2 = fraction * local_H2
        results[tt] = {
            'count': n,
            'fraction': frac,
            'H2_local': h2_local,
            'H2_contribution': frac * h2_local,
        }

    return results


# ============================================================
# 5. NULL MODELS
# ============================================================
def model_slot_resample(glyph_stream, slot_stream, trans_types, n_iter=50):
    """Null Model A: Keep slot patterns, resample glyphs from P(glyph|slot).
    Preserves: slot grammar structure, slot inventories, transition types.
    Destroys: specific glyph-to-glyph correlations within and across slots.
    """
    # Build P(glyph|slot)
    slot_glyphs = defaultdict(list)
    for g, s in zip(glyph_stream, slot_stream):
        slot_glyphs[s].append(g)

    slot_distributions = {}
    for s, gs in slot_glyphs.items():
        counts = Counter(gs)
        total = len(gs)
        slot_distributions[s] = [(g, c/total) for g, c in counts.items()]

    hchars = []
    for _ in range(n_iter):
        synthetic = []
        for s in slot_stream:
            dist = slot_distributions[s]
            r = random.random()
            cumul = 0.0
            for g, p in dist:
                cumul += p
                if r < cumul:
                    synthetic.append(g)
                    break
            else:
                synthetic.append(dist[-1][0])

        _, _, hc = compute_hchar(synthetic)
        if hc is not None:
            hchars.append(hc)

    return sum(hchars) / len(hchars), min(hchars), max(hchars)


def model_slot_shuffle(glyph_stream, slot_stream, n_iter=50):
    """Null Model B: Shuffle glyphs within each slot across the entire corpus.
    Preserves: exact marginals per slot, slot structure.
    Destroys: sequential ordering of glyphs within each slot.
    """
    # Group indices by slot
    slot_indices = defaultdict(list)
    for i, s in enumerate(slot_stream):
        slot_indices[s].append(i)

    hchars = []
    for _ in range(n_iter):
        synthetic = list(glyph_stream)
        for s, indices in slot_indices.items():
            glyphs_at_slot = [glyph_stream[i] for i in indices]
            random.shuffle(glyphs_at_slot)
            for idx, g in zip(indices, glyphs_at_slot):
                synthetic[idx] = g

        _, _, hc = compute_hchar(synthetic)
        if hc is not None:
            hchars.append(hc)

    return sum(hchars) / len(hchars), min(hchars), max(hchars)


def model_flat_shuffle(glyph_stream, n_iter=20):
    """Null Model C: Complete random shuffle of all glyphs.
    Preserves: unigram frequencies only.
    Destroys: all sequential structure.
    """
    hchars = []
    for _ in range(n_iter):
        synthetic = list(glyph_stream)
        random.shuffle(synthetic)
        _, _, hc = compute_hchar(synthetic)
        if hc is not None:
            hchars.append(hc)
    return sum(hchars) / len(hchars), min(hchars), max(hchars)


# ============================================================
# 6. NL BASELINE: CVC SYLLABLE-SLOT DECOMPOSITION
# ============================================================
NL_VOWELS = set('aeiouyàáâãäåæèéêëìíîïòóôõöùúûüýÿœ')

def nl_char_to_slot(ch):
    """Simple V/C classification for NL characters."""
    return 'V' if ch.lower() in NL_VOWELS else 'C'

def nl_compute_hchar_with_slot_resample(text, n_iter=30):
    """For an NL text, compute observed h_char, then build a CVC slot
    model and compute slot-resample h_char for comparison.
    """
    # Clean text to lowercase alphabetic
    chars = [c.lower() for c in text if c.isalpha()]
    if len(chars) < 100:
        return None

    h1_obs, h2_obs, hc_obs = compute_hchar(chars)

    # Assign CVC slots: each character gets a slot based on V/C
    # and its position within a V/C run
    slots = []
    run_start = 0
    for i, ch in enumerate(chars):
        cv = nl_char_to_slot(ch)
        if i == 0:
            slots.append(cv + '0')
        elif nl_char_to_slot(chars[i-1]) == cv:
            run_pos = i - run_start
            slots.append(cv + str(min(run_pos, 3)))
        else:
            run_start = i
            slots.append(cv + '0')

    # Build P(char|slot) and resample
    slot_chars = defaultdict(list)
    for c, s in zip(chars, slots):
        slot_chars[s].append(c)

    slot_dists = {}
    for s, cs in slot_chars.items():
        counts = Counter(cs)
        total = len(cs)
        slot_dists[s] = [(c, n/total) for c, n in counts.items()]

    hchars_resample = []
    for _ in range(n_iter):
        synthetic = []
        for s in slots:
            dist = slot_dists[s]
            r = random.random()
            cumul = 0.0
            for g, p in dist:
                cumul += p
                if r < cumul:
                    synthetic.append(g)
                    break
            else:
                synthetic.append(dist[-1][0])
        _, _, hc = compute_hchar(synthetic)
        if hc is not None:
            hchars_resample.append(hc)

    hc_resample = sum(hchars_resample) / len(hchars_resample) if hchars_resample else None
    n_slots = len(set(slots))

    return {
        'n_chars': len(chars),
        'h_char_obs': round(hc_obs, 4),
        'h_char_slot_resample': round(hc_resample, 4) if hc_resample else None,
        'n_slot_types': n_slots,
        'ratio_obs_to_resample': round(hc_obs / hc_resample, 4) if hc_resample else None,
    }


# ============================================================
# 7. SLOT INVENTORY ANALYSIS
# ============================================================
def analyze_slot_inventories(glyph_stream, slot_stream):
    """Report per-slot inventory and entropy."""
    slot_data = defaultdict(Counter)
    for g, s in zip(glyph_stream, slot_stream):
        slot_data[s][g] += 1

    results = {}
    for s in sorted(slot_data.keys()):
        counts = slot_data[s]
        total = sum(counts.values())
        h = -sum((c/total) * math.log2(c/total) for c in counts.values())
        n_types = len(counts)
        top = counts.most_common(8)
        results[s] = {
            'n_tokens': total,
            'n_types': n_types,
            'entropy': round(h, 4),
            'max_entropy': round(math.log2(n_types), 4) if n_types > 1 else 0.0,
            'top_glyphs': top,
        }
    return results


# ============================================================
# 8. SLOT-TO-SLOT TRANSITION ANALYSIS
# ============================================================
def slot_transition_matrix(slot_stream, trans_types):
    """Build transition probability matrix between slots.
    Only considers within-chunk transitions (ws and sc types).
    """
    trans = Counter()
    for i, tt in enumerate(trans_types):
        if tt in ('ws', 'sc'):
            s_from = slot_stream[i]
            s_to = slot_stream[i+1]
            trans[(s_from, s_to)] += 1

    # Also cross-chunk and cross-word
    cross_chunk = Counter()
    cross_word = Counter()
    for i, tt in enumerate(trans_types):
        if tt == 'cc':
            cross_chunk[(slot_stream[i], slot_stream[i+1])] += 1
        elif tt == 'cw':
            cross_word[(slot_stream[i], slot_stream[i+1])] += 1

    return trans, cross_chunk, cross_word


# ============================================================
# MAIN EXECUTION
# ============================================================
def main():
    random.seed(42)
    print("=" * 72)
    print("  PHASE 97 — SLOT GRAMMAR AS h_char GENERATIVE MODEL")
    print("=" * 72)

    # ----- Step 1: Build annotated streams -----
    print("\n▸ Building annotated glyph streams...")
    gs_all, ss_all, tt_all = build_annotated_stream(FOLIO_DIR)
    gs_a, ss_a, tt_a = build_annotated_stream(FOLIO_DIR, lambda f: f <= 57)
    gs_b, ss_b, tt_b = build_annotated_stream(FOLIO_DIR, lambda f: f >= 75)

    print(f"  ALL: {len(gs_all):,} glyphs, {len(tt_all):,} transitions")
    print(f"  Currier A: {len(gs_a):,} glyphs")
    print(f"  Currier B: {len(gs_b):,} glyphs")

    # ----- Step 2: Observed h_char -----
    print("\n" + "=" * 72)
    print("  OBSERVED h_char")
    print("=" * 72)
    for label, gs in [('ALL', gs_all), ('Currier A', gs_a), ('Currier B', gs_b)]:
        h1, h2, hc = compute_hchar(gs)
        print(f"  {label:12s}: H1={h1:.4f}  H2={h2:.4f}  h_char={hc:.4f}")

    # ----- Step 3: Transition type decomposition -----
    print("\n" + "=" * 72)
    print("  h_char DECOMPOSITION BY TRANSITION TYPE")
    print("=" * 72)

    for label, gs, tt in [('ALL', gs_all, tt_all), ('A', gs_a, tt_a), ('B', gs_b, tt_b)]:
        print(f"\n  --- {label} ---")
        decomp = compute_conditional_entropy_by_type(gs, tt)
        h1_all, _, hc_all = compute_hchar(gs)

        total_h2_reconstructed = 0
        print(f"  {'Type':6s}  {'Count':>8s}  {'Frac':>6s}  {'H2_local':>8s}  {'H2_contrib':>10s}  {'% of H2':>7s}")
        print(f"  {'─'*6}  {'─'*8}  {'─'*6}  {'─'*8}  {'─'*10}  {'─'*7}")

        h2_total = sum(d['H2_contribution'] for d in decomp.values())

        for tt_type in ['ws', 'sc', 'cc', 'cw']:
            if tt_type in decomp:
                d = decomp[tt_type]
                pct = d['H2_contribution'] / h2_total * 100 if h2_total > 0 else 0
                total_h2_reconstructed += d['H2_contribution']
                type_labels = {'ws': 'W-slot', 'sc': 'S-slot', 'cc': 'X-chnk', 'cw': 'X-word'}
                print(f"  {type_labels[tt_type]:6s}  {d['count']:8d}  {d['fraction']:6.3f}  "
                      f"{d['H2_local']:8.4f}  {d['H2_contribution']:10.4f}  {pct:6.1f}%")

        h2_recon_ratio = total_h2_reconstructed / h1_all if h1_all > 0 else 0
        print(f"  {'':6s}  {'':8s}  {'':6s}  {'':8s}  {total_h2_reconstructed:10.4f}  (h_char={h2_recon_ratio:.4f})")

    # ----- Step 4: Slot inventory analysis -----
    print("\n" + "=" * 72)
    print("  PER-SLOT INVENTORY AND ENTROPY")
    print("=" * 72)

    slot_inv = analyze_slot_inventories(gs_all, ss_all)
    for s in sorted(slot_inv.keys()):
        d = slot_inv[s]
        slot_names = {0: 'UNPARSE', 1: 'S1-onset', 2: 'S2-front',
                      3: 'S3-core', 4: 'S4-back', 5: 'S5-coda'}
        name = slot_names.get(s, f'S{s}')
        top_str = ', '.join(f"{g}({c})" for g, c in d['top_glyphs'])
        print(f"  {name:10s}: {d['n_tokens']:6d} tokens, {d['n_types']:2d} types, "
              f"H={d['entropy']:.3f}/{d['max_entropy']:.3f}  [{top_str}]")

    # ----- Step 5: Slot transition matrix -----
    print("\n" + "=" * 72)
    print("  SLOT-TO-SLOT TRANSITION MATRIX (within-chunk)")
    print("=" * 72)

    within_trans, cross_chunk, cross_word = slot_transition_matrix(ss_all, tt_all)

    all_slots = sorted(set(ss_all))
    slot_names_short = {0: '?', 1: 'S1', 2: 'S2', 3: 'S3', 4: 'S4', 5: 'S5'}

    print(f"\n  {'':5s}", end='')
    for s_to in all_slots:
        print(f"  {slot_names_short.get(s_to, '?'):>5s}", end='')
    print()

    for s_from in all_slots:
        row_total = sum(within_trans[(s_from, s_to)] for s_to in all_slots)
        print(f"  {slot_names_short.get(s_from, '?'):5s}", end='')
        for s_to in all_slots:
            c = within_trans[(s_from, s_to)]
            if c > 0 and row_total > 0:
                print(f"  {c/row_total:5.2f}", end='')
            else:
                print(f"  {'─':>5s}", end='')
        print(f"  (n={row_total})")

    # Cross-chunk
    print(f"\n  Cross-chunk transitions (top 10):")
    for (s_from, s_to), c in cross_chunk.most_common(10):
        print(f"    {slot_names_short.get(s_from,'?')}→{slot_names_short.get(s_to,'?')}: {c}")

    print(f"\n  Cross-word transitions (top 10):")
    for (s_from, s_to), c in cross_word.most_common(10):
        print(f"    {slot_names_short.get(s_from,'?')}→{slot_names_short.get(s_to,'?')}: {c}")

    # ----- Step 6: NULL MODELS -----
    print("\n" + "=" * 72)
    print("  NULL MODEL COMPARISON")
    print("=" * 72)

    _, _, hc_obs = compute_hchar(gs_all)
    print(f"\n  Observed h_char (ALL):     {hc_obs:.4f}")

    print("\n  Running Model A: Slot-Resample (50 iterations)...")
    hc_sr_mean, hc_sr_min, hc_sr_max = model_slot_resample(gs_all, ss_all, tt_all, n_iter=50)
    print(f"  Slot-Resample h_char:     {hc_sr_mean:.4f}  [{hc_sr_min:.4f}, {hc_sr_max:.4f}]")

    print("\n  Running Model B: Slot-Shuffle (50 iterations)...")
    hc_ss_mean, hc_ss_min, hc_ss_max = model_slot_shuffle(gs_all, ss_all, n_iter=50)
    print(f"  Slot-Shuffle h_char:      {hc_ss_mean:.4f}  [{hc_ss_min:.4f}, {hc_ss_max:.4f}]")

    print("\n  Running Model C: Flat-Shuffle (20 iterations)...")
    hc_fs_mean, hc_fs_min, hc_fs_max = model_flat_shuffle(gs_all, n_iter=20)
    print(f"  Flat-Shuffle h_char:      {hc_fs_mean:.4f}  [{hc_fs_min:.4f}, {hc_fs_max:.4f}]")

    # Quantify what the slot grammar explains
    gap_obs_to_flat = hc_fs_mean - hc_obs
    gap_model_to_flat = hc_fs_mean - hc_sr_mean
    pct_explained = gap_model_to_flat / gap_obs_to_flat * 100 if gap_obs_to_flat > 0 else 0

    print(f"\n  ─── SLOT GRAMMAR EXPLANATORY POWER ───")
    print(f"  Gap: Observed → Flat-shuffle:     {gap_obs_to_flat:.4f}")
    print(f"  Gap: Slot-resample → Flat-shuffle: {gap_model_to_flat:.4f}")
    print(f"  Slot grammar explains: {pct_explained:.1f}% of h_char depression")

    residual = hc_sr_mean - hc_obs
    print(f"  Residual (Slot-resample − Observed): {residual:+.4f}")
    if abs(residual) < 0.02:
        print(f"  → Slot grammar FULLY EXPLAINS h_char anomaly (residual < 0.02)")
    elif residual > 0.02:
        print(f"  → Additional correlations BEYOND slot grammar ({residual:.4f} unexplained)")
    else:
        print(f"  → Observed h_char HIGHER than slot model predicts (unexpected)")

    # ----- Step 6b: Currier A/B null models -----
    print("\n  --- Currier A ---")
    _, _, hc_a_obs = compute_hchar(gs_a)
    hc_a_sr_mean, _, _ = model_slot_resample(gs_a, ss_a, tt_a, n_iter=30)
    print(f"  Observed: {hc_a_obs:.4f}  Slot-resample: {hc_a_sr_mean:.4f}  "
          f"Residual: {hc_a_sr_mean - hc_a_obs:+.4f}")

    print("\n  --- Currier B ---")
    _, _, hc_b_obs = compute_hchar(gs_b)
    hc_b_sr_mean, _, _ = model_slot_resample(gs_b, ss_b, tt_b, n_iter=30)
    print(f"  Observed: {hc_b_obs:.4f}  Slot-resample: {hc_b_sr_mean:.4f}  "
          f"Residual: {hc_b_sr_mean - hc_b_obs:+.4f}")

    # ----- Step 7: NL BASELINES -----
    print("\n" + "=" * 72)
    print("  NL BASELINE: CVC SLOT-RESAMPLE COMPARISON")
    print("=" * 72)
    print("  (How much does syllable/CVC structure explain NL h_char?)")

    nl_results = {}
    for fname in sorted(os.listdir(LATIN_DIR)):
        fpath = os.path.join(LATIN_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        with open(fpath, 'r', encoding='utf-8', errors='replace') as fh:
            text = fh.read()
        label = fname.replace('.txt', '')
        result = nl_compute_hchar_with_slot_resample(text, n_iter=30)
        if result:
            nl_results[label] = result
            obs = result['h_char_obs']
            sr = result['h_char_slot_resample']
            ratio = result['ratio_obs_to_resample']
            n_sl = result['n_slot_types']
            resid = sr - obs if sr else None
            print(f"  {label:30s}: h_obs={obs:.4f}  h_slot_resample={sr:.4f}  "
                  f"residual={resid:+.4f}  n_slots={n_sl}")

    # ----- Step 8: Summary comparison table -----
    print("\n" + "=" * 72)
    print("  SUMMARY COMPARISON TABLE")
    print("=" * 72)

    print(f"\n  {'System':30s}  {'h_obs':>7s}  {'h_slot':>7s}  {'resid':>7s}  {'%_explained':>11s}")
    print(f"  {'─'*30}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*11}")

    # VMS
    for label, hc_o, hc_s in [('VMS ALL', hc_obs, hc_sr_mean),
                                ('VMS Currier A', hc_a_obs, hc_a_sr_mean),
                                ('VMS Currier B', hc_b_obs, hc_b_sr_mean)]:
        resid = hc_s - hc_o
        pct = (1.0 - hc_s) / (1.0 - hc_o) * 100 if (1.0 - hc_o) > 0 else 0
        # Actually, % explained = (flat - slot_resample) / (flat - obs)
        # Using flat ≈ 1.0 approximation:
        pct2 = (1.0 - hc_s) / (1.0 - hc_o) * 100 if (1.0 - hc_o) > 0 else 0
        print(f"  {label:30s}  {hc_o:7.4f}  {hc_s:7.4f}  {resid:+7.4f}  "
              f"{(hc_fs_mean - hc_s)/(hc_fs_mean - hc_o)*100:10.1f}%")

    # NL
    for label, res in sorted(nl_results.items()):
        obs = res['h_char_obs']
        sr = res['h_char_slot_resample']
        resid = sr - obs if sr else 0
        # For NL, flat shuffle ≈ 1.0
        pct = (1.0 - sr) / (1.0 - obs) * 100 if (1.0 - obs) > 0 else 0
        print(f"  {label:30s}  {obs:7.4f}  {sr:7.4f}  {resid:+7.4f}  ~{pct:9.1f}%")

    # ----- Step 9: KEY DIAGNOSTIC -----
    print("\n" + "=" * 72)
    print("  KEY DIAGNOSTIC: IS VMS h_char ANOMALOUS GIVEN ITS SLOT GRAMMAR?")
    print("=" * 72)

    # Compare VMS residual to NL residuals
    nl_residuals = [r['h_char_slot_resample'] - r['h_char_obs']
                    for r in nl_results.values()
                    if r['h_char_slot_resample'] is not None]

    vms_residual = hc_sr_mean - hc_obs

    if nl_residuals:
        nl_mean_resid = sum(nl_residuals) / len(nl_residuals)
        nl_std_resid = (sum((r - nl_mean_resid)**2 for r in nl_residuals) / len(nl_residuals)) ** 0.5
        z_vms = (vms_residual - nl_mean_resid) / nl_std_resid if nl_std_resid > 0 else float('inf')

        print(f"\n  VMS residual (slot_resample - observed): {vms_residual:+.4f}")
        print(f"  NL mean residual:                        {nl_mean_resid:+.4f}")
        print(f"  NL std residual:                         {nl_std_resid:.4f}")
        print(f"  VMS z-score vs NL residuals:             {z_vms:+.2f}")

        if abs(z_vms) < 2.0:
            print(f"\n  → VMS residual is WITHIN NL range (|z| < 2)")
            print(f"    The slot grammar explains the h_char anomaly to the same")
            print(f"    extent that CVC structure explains NL h_char.")
            print(f"    h_char IS NOT ANOMALOUS once slot grammar is accounted for.")
            verdict = "SLOT_GRAMMAR_EXPLAINS"
        else:
            print(f"\n  → VMS residual is OUTSIDE NL range (|z| = {abs(z_vms):.1f})")
            if vms_residual > nl_mean_resid:
                print(f"    VMS has MORE additional correlation beyond slot grammar than NL")
                print(f"    The slot grammar does NOT fully explain h_char.")
                verdict = "ADDITIONAL_CORRELATIONS"
            else:
                print(f"    VMS has LESS correlation beyond slot grammar than NL")
                print(f"    The slot grammar over-predicts the anomaly.")
                verdict = "SLOT_OVER_PREDICTS"
    else:
        verdict = "NO_NL_BASELINE"
        z_vms = None

    # ----- Step 10: Final verdict -----
    print("\n" + "=" * 72)
    print("  PHASE 97 VERDICT")
    print("=" * 72)

    print(f"\n  Observed h_char (VMS):           {hc_obs:.4f}")
    print(f"  Slot-resample h_char (VMS):      {hc_sr_mean:.4f}")
    print(f"  Slot-shuffle h_char (VMS):       {hc_ss_mean:.4f}")
    print(f"  Flat-shuffle h_char (VMS):       {hc_fs_mean:.4f}")
    print(f"  NL typical range:                0.82 — 0.90")
    print(f"  VMS residual:                    {vms_residual:+.4f}")
    print(f"  VMS z-score vs NL residuals:     {z_vms:+.2f}" if z_vms is not None else "  (no z-score)")
    print(f"  Verdict:                         {verdict}")

    print("\n" + "=" * 72)
    print("  PHASE 97 COMPLETE")
    print("=" * 72)

    # Save results
    results = {
        'h_char_observed': {'all': round(hc_obs, 4),
                            'a': round(hc_a_obs, 4),
                            'b': round(hc_b_obs, 4)},
        'h_char_slot_resample': {'all': round(hc_sr_mean, 4),
                                  'a': round(hc_a_sr_mean, 4),
                                  'b': round(hc_b_sr_mean, 4)},
        'h_char_slot_shuffle': round(hc_ss_mean, 4),
        'h_char_flat_shuffle': round(hc_fs_mean, 4),
        'pct_explained_by_slot_grammar': round(pct_explained, 1),
        'vms_residual': round(vms_residual, 4),
        'z_score_vs_nl': round(z_vms, 2) if z_vms is not None else None,
        'verdict': verdict,
        'nl_baselines': {k: v for k, v in nl_results.items()},
    }

    with open(os.path.join(RESULTS_DIR, 'phase97_slot_grammar_hchar.json'), 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n  Results saved to results/phase97_slot_grammar_hchar.json")


if __name__ == '__main__':
    main()
