#!/usr/bin/env python3
"""
Currier A/B as SLOT2 Regime

═══════════════════════════════════════════════════════════════════════

QUESTION:
  ae_minimal_pairs found that zodiac labels separate into two hemispheres
  via SLOT2 content alone: spring signs fill SLOT2 with 'a' (85%),
  autumn signs with 'e'/'ee' (60%). r(a-frac, e-frac) = -0.9994.

  The classic Currier A/B "two language" distinction (1976) is the
  oldest and most replicated structural finding in VMS studies.
  Currier A dominates herbal folios; B dominates pharma/recipe.

  HYPOTHESIS: SLOT2 a-fraction IS the mechanism behind the Currier
  A/B split. If true, the "two languages" reduce to one language
  with two SLOT2 regimes — a massive structural simplification.

WHY THIS IS HIGH-LEVERAGE:
  - If SLOT2 alone explains Currier A vs B, it unifies 50 years of
    "two language" debate into a single grammar parameter.
  - If it DOESN'T, knowing WHAT ELSE differs is equally valuable.

APPROACH:
  1. Parse Currier A/B from folio headers (not hardcoded like chunk_fingerprint).
  2. Parse all words → LOOP chunks across entire manuscript.
  3. Per-folio: compute SLOT2 a-frac, e-frac, q-frac.
  4. Per-folio: compute competing single features:
     - SLOT1 ch-frac, sh-frac, y-frac
     - SLOT5 profile (top 5 coda fillers)
     - Mean word length (in glyphs), mean chunks per word
     - Gallows frequency (cth, ckh, cph, cfh per word)
  5. For each feature: measure A vs B separation (Cohen's d, accuracy
     with optimal threshold, permutation p-value).
  6. Rank features by classification accuracy.
  7. CRITICAL TEST: After removing SLOT2 content from all words,
     reassign Currier by all OTHER features. If classification
     remains strong, SLOT2 is redundant — A/B involves many features.
  8. Gradient test: Is SLOT2 a-frac uniform WITHIN an A or within B,
     or is there a continuous gradient? (bimodal = real switch;
     unimodal gradient = just one axis of many)

SKEPTICISM:
  - SLOT2 was designed as part of LOOP grammar to fit VMS. High
    correlation with ANY structural feature is partly by construction.
  - Currier A and B folios differ by section (herbal vs pharma) and
    quite possibly by topic. SLOT2 variation could follow topic, not
    drive the A/B classification.
  - Some folios have very few words — noisy estimates. Need minimum
    threshold (≥30 words).
  - Multi-section folio files (f100v_101r.txt) may span A/B boundary.
    Must handle carefully.
  - The gold standard Currier assignments are from the 1970s and
    not universally agreed upon. Some folios are disputed.
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import clean_word, eva_to_glyphs, extract_words_from_line

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR  = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
FOLIO_DIR   = PROJECT_DIR / 'folios'
DATA_DIR    = PROJECT_DIR / 'data'
RESULTS_DIR = PROJECT_DIR / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(42)
random.seed(42)


# ═══════════════════════════════════════════════════════════════════════
# EVA GLYPH TOKENIZER + LOOP PARSER (from chunk_fingerprint)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']



SLOT1 = {'ch', 'sh', 'y'}
SLOT2_RUNS = {'e'}
SLOT2_SINGLE = {'q', 'a'}
SLOT3 = {'o'}
SLOT4_RUNS = {'i'}
SLOT4_SINGLE = {'d'}
SLOT5 = {'y', 'p', 'f', 'k', 'l', 'r', 's', 't',
         'cth', 'ckh', 'cph', 'cfh', 'n', 'm'}
GALLOWS_SET = {'cth', 'ckh', 'cph', 'cfh'}
MAX_CHUNKS = 6


def parse_one_chunk(glyphs, pos):
    start = pos
    chunk = []
    slots_detail = {}  # slot -> list of glyphs in that slot

    # SLOT 1: onset
    if pos < len(glyphs) and glyphs[pos] in SLOT1:
        slots_detail[1] = [glyphs[pos]]
        chunk.append(glyphs[pos]); pos += 1

    # SLOT 2: front vowel
    if pos < len(glyphs):
        if glyphs[pos] in SLOT2_RUNS:
            s2 = []
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT2_RUNS and count < 3:
                s2.append(glyphs[pos])
                chunk.append(glyphs[pos]); pos += 1; count += 1
            slots_detail[2] = s2
        elif glyphs[pos] in SLOT2_SINGLE:
            slots_detail[2] = [glyphs[pos]]
            chunk.append(glyphs[pos]); pos += 1

    # SLOT 3: core 'o'
    if pos < len(glyphs) and glyphs[pos] in SLOT3:
        slots_detail[3] = [glyphs[pos]]
        chunk.append(glyphs[pos]); pos += 1

    # SLOT 4: back vowel
    if pos < len(glyphs):
        if glyphs[pos] in SLOT4_RUNS:
            s4 = []
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT4_RUNS and count < 3:
                s4.append(glyphs[pos])
                chunk.append(glyphs[pos]); pos += 1; count += 1
            slots_detail[4] = s4
        elif glyphs[pos] in SLOT4_SINGLE:
            slots_detail[4] = [glyphs[pos]]
            chunk.append(glyphs[pos]); pos += 1

    # SLOT 5: coda
    if pos < len(glyphs) and glyphs[pos] in SLOT5:
        slots_detail[5] = [glyphs[pos]]
        chunk.append(glyphs[pos]); pos += 1

    if pos == start:
        return None, pos, {}
    return chunk, pos, slots_detail


def parse_word_into_chunks(word_str):
    glyphs = eva_to_glyphs(word_str)
    chunks = []
    slots_list = []  # parallel list of slot dicts per chunk
    unparsed = []
    pos = 0
    while pos < len(glyphs) and len(chunks) < MAX_CHUNKS:
        chunk, new_pos, slots_detail = parse_one_chunk(glyphs, pos)
        if chunk is None:
            unparsed.append(glyphs[pos]); pos += 1
        else:
            chunks.append(chunk)
            slots_list.append(slots_detail)
            pos = new_pos
    while pos < len(glyphs):
        unparsed.append(glyphs[pos]); pos += 1
    return chunks, slots_list, unparsed, glyphs


# ═══════════════════════════════════════════════════════════════════════
# VMS TEXT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════





def parse_currier_from_header(filepath):
    """Parse Currier language from the comment lines in a folio file.
    Returns 'A', 'B', or None if not found.
    Multiple mentions are counted; majority wins."""
    counts = Counter()
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('#'):
                # Stop at first non-comment, non-empty, non-tag line
                if line and not line.startswith('<'):
                    break
                continue
            m = re.search(r"Currier'?s?\s+[Ll]anguage\s+([AB])", line)
            if m:
                counts[m.group(1)] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def folio_section(fname):
    m = re.match(r'f(\d+)', fname)
    if not m:
        return 'unknown'
    n = int(m.group(1))
    if 103 <= n <= 116: return 'recipe'
    elif 75 <= n <= 84: return 'balneo'
    elif 67 <= n <= 73: return 'astro'
    elif 85 <= n <= 86: return 'cosmo'
    elif 87 <= n <= 102: return 'pharma'
    else: return 'herbal'


def load_all_folios():
    """Load all folios. Returns list of dicts with keys:
    filename, folio_num, currier, section, words."""
    folios = []
    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: (int(re.match(r'f(\d+)', p.stem).group(1))
                                        if re.match(r'f(\d+)', p.stem) else 0,
                                        p.stem))

    for filepath in folio_files:
        if filepath.suffix != '.txt':
            continue
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num:
            continue

        fnum = int(m_num.group(1))
        currier = parse_currier_from_header(filepath)
        section = folio_section(filepath.stem)

        words = []
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                m = re.match(r'<([^>]+)>', line)
                if not m:
                    continue
                rest = line[m.end():].strip()
                if not rest:
                    continue
                words.extend(extract_words_from_line(rest))

        folios.append({
            'filename': filepath.stem,
            'folio_num': fnum,
            'currier': currier,
            'section': section,
            'words': words,
        })

    return folios


# ═══════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION PER FOLIO
# ═══════════════════════════════════════════════════════════════════════

def compute_folio_features(words):
    """Compute LOOP-based features for a list of words.
    Returns dict of feature_name -> float."""

    total_chunks = 0
    total_words_parsed = 0
    total_glyphs = 0
    slot2_counts = Counter()  # what fills SLOT2: 'a', 'e', 'ee', 'eee', 'q', 'empty'
    slot1_counts = Counter()  # 'ch', 'sh', 'y', 'empty'
    slot5_counts = Counter()
    gallows_count = 0

    for w in words:
        chunks, slots_list, unparsed, glyphs = parse_word_into_chunks(w)
        total_glyphs += len(glyphs)
        total_words_parsed += 1
        total_chunks += len(chunks)

        # Gallows in the full word
        for g in glyphs:
            if g in GALLOWS_SET:
                gallows_count += 1

        for chunk_glyphs, slots_dict in zip(chunks, slots_list):
            # SLOT 1
            if 1 in slots_dict:
                slot1_counts[slots_dict[1][0]] += 1
            else:
                slot1_counts['empty'] += 1

            # SLOT 2
            if 2 in slots_dict:
                s2_str = ''.join(slots_dict[2])
                slot2_counts[s2_str] += 1
            else:
                slot2_counts['empty'] += 1

            # SLOT 5
            if 5 in slots_dict:
                slot5_counts[slots_dict[5][0]] += 1
            else:
                slot5_counts['empty'] += 1

    if total_chunks == 0:
        return None

    # Fractions
    features = {}
    n = total_chunks

    # SLOT2 features
    features['s2_a_frac'] = slot2_counts.get('a', 0) / n
    features['s2_e_frac'] = (slot2_counts.get('e', 0) +
                              slot2_counts.get('ee', 0) +
                              slot2_counts.get('eee', 0)) / n
    features['s2_q_frac'] = slot2_counts.get('q', 0) / n
    features['s2_empty_frac'] = slot2_counts.get('empty', 0) / n

    # SLOT1 features
    features['s1_ch_frac'] = slot1_counts.get('ch', 0) / n
    features['s1_sh_frac'] = slot1_counts.get('sh', 0) / n
    features['s1_y_frac'] = slot1_counts.get('y', 0) / n
    features['s1_empty_frac'] = slot1_counts.get('empty', 0) / n

    # SLOT5 features
    for coda in ['y', 'l', 'r', 's', 'n', 'k']:
        features[f's5_{coda}_frac'] = slot5_counts.get(coda, 0) / n
    features['s5_gallows_frac'] = sum(slot5_counts.get(g, 0) for g in GALLOWS_SET) / n
    features['s5_empty_frac'] = slot5_counts.get('empty', 0) / n

    # Word-level features
    features['mean_word_len'] = total_glyphs / total_words_parsed if total_words_parsed else 0
    features['mean_chunks_per_word'] = total_chunks / total_words_parsed if total_words_parsed else 0
    features['gallows_per_word'] = gallows_count / total_words_parsed if total_words_parsed else 0

    # Raw counts for diagnostics
    features['n_words'] = total_words_parsed
    features['n_chunks'] = total_chunks

    return features


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL TOOLS
# ═══════════════════════════════════════════════════════════════════════

def cohens_d(a, b):
    """Cohen's d effect size."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    ma, mb = np.mean(a), np.mean(b)
    # Pooled SD
    sa, sb = np.std(a, ddof=1), np.std(b, ddof=1)
    sp = np.sqrt(((na - 1) * sa**2 + (nb - 1) * sb**2) / (na + nb - 2))
    if sp == 0:
        return 0.0
    return (ma - mb) / sp


def optimal_threshold_accuracy(vals_a, vals_b):
    """Find threshold that best separates A from B. Vectorized.
    Returns (accuracy, threshold, direction).
    direction: 'above_is_A' or 'below_is_A'."""
    va = np.asarray(vals_a, dtype=float)
    vb = np.asarray(vals_b, dtype=float)
    n = len(va) + len(vb)
    if n == 0:
        return 0.0, 0.0, 'above_is_A'

    all_vals = np.concatenate([va, vb])
    labels = np.concatenate([np.ones(len(va)), np.zeros(len(vb))])

    order = np.argsort(all_vals)
    sorted_vals = all_vals[order]
    sorted_labels = labels[order]

    # Cumulative A-labels from left: for threshold at position i,
    # elements [0..i-1] are below threshold, [i..n-1] are above.
    # "above_is_A": correct = A's above + B's below
    cum_a = np.cumsum(sorted_labels)  # cum_a[i] = # A labels in [0..i]
    total_a = cum_a[-1]
    total_b = n - total_a

    # For split at index i (threshold between sorted_vals[i-1] and sorted_vals[i]):
    # below = [0..i-1], above = [i..n-1]
    # A above = total_a - cum_a[i-1], B below = i - cum_a[i-1] (where cum_a[-1]=0 for i=0 edge)
    # correct_above_is_A = A_above + B_below = (total_a - cum_a_left) + (i - cum_a_left)
    #                     = total_a + i - 2*cum_a_left
    # correct_below_is_A = B_above + A_below = (total_b - (i - cum_a_left)) + cum_a_left
    #                     = total_b - i + 2*cum_a_left

    # Build thresholds at midpoints between distinct sorted values
    diffs = np.diff(sorted_vals)
    valid = diffs > 0
    if not np.any(valid):
        return max(total_a, total_b) / n, sorted_vals[0], 'above_is_A'

    indices = np.where(valid)[0]  # i: threshold between sorted_vals[i] and sorted_vals[i+1]
    cum_a_left = cum_a[indices]  # cum A labels in [0..i]
    split_pos = indices + 1  # number of elements below threshold

    correct_above = total_a + split_pos - 2 * cum_a_left
    correct_below = total_b - split_pos + 2 * cum_a_left

    best_above_idx = np.argmax(correct_above)
    best_below_idx = np.argmax(correct_below)

    if correct_above[best_above_idx] >= correct_below[best_below_idx]:
        best_i = indices[best_above_idx]
        return float(correct_above[best_above_idx]) / n, \
               float((sorted_vals[best_i] + sorted_vals[best_i + 1]) / 2), 'above_is_A'
    else:
        best_i = indices[best_below_idx]
        return float(correct_below[best_below_idx]) / n, \
               float((sorted_vals[best_i] + sorted_vals[best_i + 1]) / 2), 'below_is_A'


def _fast_optimal_acc(all_vals_sorted, labels_sorted, n, total_a, total_b):
    """Inner fast path for permutation test — already sorted."""
    cum_a = np.cumsum(labels_sorted)
    diffs = np.diff(all_vals_sorted)
    valid = diffs > 0
    if not np.any(valid):
        return max(total_a, total_b) / n
    indices = np.where(valid)[0]
    cum_a_left = cum_a[indices]
    split_pos = indices + 1
    best_above = np.max(total_a + split_pos - 2 * cum_a_left)
    best_below = np.max(total_b - split_pos + 2 * cum_a_left)
    return max(best_above, best_below) / n


def permutation_test_accuracy(vals_a, vals_b, observed_acc, n_perm=10000):
    """How often does random A/B assignment achieve >= observed accuracy?"""
    all_vals = np.concatenate([np.asarray(vals_a, dtype=float),
                                np.asarray(vals_b, dtype=float)])
    na = len(vals_a)
    n = len(all_vals)

    # Pre-sort values (fixed across permutations); permute labels instead
    order = np.argsort(all_vals)
    sorted_vals = all_vals[order]

    count_ge = 0
    for _ in range(n_perm):
        # Random labels: na ones, rest zeros
        perm_labels = np.zeros(n)
        perm_labels[np.random.choice(n, na, replace=False)] = 1.0
        # Re-order labels to match sorted values
        sorted_labels = perm_labels[order]
        acc = _fast_optimal_acc(sorted_vals, sorted_labels, n, na, n - na)
        if acc >= observed_acc:
            count_ge += 1

    return count_ge / n_perm


def pearson_r(x, y):
    if len(x) < 3:
        return 0.0
    x, y = np.array(x), np.array(y)
    mx, my = np.mean(x), np.mean(y)
    dx, dy = x - mx, y - my
    denom = np.sqrt(np.sum(dx**2) * np.sum(dy**2))
    if denom == 0:
        return 0.0
    return float(np.sum(dx * dy) / denom)


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 72)
    pr("  currier_slot2_regime — Currier A/B as SLOT2 Regime")
    pr("=" * 72)
    pr()

    # ── Step 1: Load folios ──────────────────────────────────────────
    pr("STEP 1 — Load folios and parse Currier language from headers")
    pr("-" * 60)

    folios = load_all_folios()
    pr(f"  Total folio files loaded: {len(folios)}")

    # Parse Currier assignments
    currier_counts = Counter(f['currier'] for f in folios)
    pr(f"  Currier A: {currier_counts.get('A', 0)} files")
    pr(f"  Currier B: {currier_counts.get('B', 0)} files")
    pr(f"  Unassigned: {currier_counts.get(None, 0)} files")

    # Show unassigned
    unassigned = [f['filename'] for f in folios if f['currier'] is None]
    if unassigned:
        pr(f"  Unassigned folios: {', '.join(unassigned[:20])}")
        if len(unassigned) > 20:
            pr(f"    ... and {len(unassigned) - 20} more")
    pr()

    # ── Step 2: Compute features per folio ───────────────────────────
    pr("STEP 2 — Compute LOOP slot features per folio")
    pr("-" * 60)

    MIN_WORDS = 30  # require at least 30 words for stable estimates
    folio_data = []

    for f in folios:
        if f['currier'] not in ('A', 'B'):
            continue
        if len(f['words']) < MIN_WORDS:
            continue
        features = compute_folio_features(f['words'])
        if features is None:
            continue
        folio_data.append({
            'filename': f['filename'],
            'folio_num': f['folio_num'],
            'currier': f['currier'],
            'section': f['section'],
            'n_words': len(f['words']),
            'features': features,
        })

    n_a = sum(1 for fd in folio_data if fd['currier'] == 'A')
    n_b = sum(1 for fd in folio_data if fd['currier'] == 'B')
    pr(f"  Folios with ≥{MIN_WORDS} words and Currier label: {len(folio_data)}")
    pr(f"    Currier A: {n_a}")
    pr(f"    Currier B: {n_b}")

    # Summary table: top 10 A and top 10 B by SLOT2 a-fraction
    pr()
    pr("  Sample SLOT2 a-fractions:")
    pr(f"  {'Folio':<20} {'Currier':>8} {'Section':>8} {'Words':>6} {'S2a%':>7} {'S2e%':>7} {'S2q%':>7}")
    pr(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*6} {'─'*7} {'─'*7} {'─'*7}")
    sorted_by_s2a = sorted(folio_data, key=lambda x: x['features']['s2_a_frac'], reverse=True)
    for fd in sorted_by_s2a[:8]:
        f = fd['features']
        pr(f"  {fd['filename']:<20} {fd['currier']:>8} {fd['section']:>8} "
           f"{fd['n_words']:>6} {f['s2_a_frac']*100:>6.1f}% {f['s2_e_frac']*100:>6.1f}% {f['s2_q_frac']*100:>6.1f}%")
    pr(f"  {'...'}")
    for fd in sorted_by_s2a[-8:]:
        f = fd['features']
        pr(f"  {fd['filename']:<20} {fd['currier']:>8} {fd['section']:>8} "
           f"{fd['n_words']:>6} {f['s2_a_frac']*100:>6.1f}% {f['s2_e_frac']*100:>6.1f}% {f['s2_q_frac']*100:>6.1f}%")
    pr()

    # ── Step 3: Feature-by-feature A/B separation ───────────────────
    pr("STEP 3 — Feature-by-feature Currier A vs B separation")
    pr("-" * 60)

    # Define features to test
    feature_names = [
        's2_a_frac', 's2_e_frac', 's2_q_frac', 's2_empty_frac',
        's1_ch_frac', 's1_sh_frac', 's1_y_frac', 's1_empty_frac',
        's5_y_frac', 's5_l_frac', 's5_r_frac', 's5_s_frac', 's5_n_frac',
        's5_k_frac', 's5_gallows_frac', 's5_empty_frac',
        'mean_word_len', 'mean_chunks_per_word', 'gallows_per_word',
    ]

    results_table = []

    for fname in feature_names:
        vals_a = [fd['features'][fname] for fd in folio_data if fd['currier'] == 'A']
        vals_b = [fd['features'][fname] for fd in folio_data if fd['currier'] == 'B']

        mean_a = np.mean(vals_a) if vals_a else 0
        mean_b = np.mean(vals_b) if vals_b else 0
        d = cohens_d(vals_a, vals_b)
        acc, thresh, direction = optimal_threshold_accuracy(vals_a, vals_b)

        results_table.append({
            'feature': fname,
            'mean_A': mean_a,
            'mean_B': mean_b,
            'cohens_d': d,
            'accuracy': acc,
            'threshold': thresh,
            'direction': direction,
        })

    # Sort by accuracy descending
    results_table.sort(key=lambda x: x['accuracy'], reverse=True)

    pr(f"  {'Feature':<22} {'Mean A':>8} {'Mean B':>8} {'Cohen d':>8} {'Accuracy':>9}")
    pr(f"  {'─'*22} {'─'*8} {'─'*8} {'─'*8} {'─'*9}")
    for r in results_table:
        pr(f"  {r['feature']:<22} {r['mean_A']:>8.4f} {r['mean_B']:>8.4f} "
           f"{r['cohens_d']:>+8.3f} {r['accuracy']*100:>8.1f}%")
    pr()

    # ── Step 4: Permutation tests on top features ────────────────────
    pr("STEP 4 — Permutation tests on top 5 features")
    pr("-" * 60)

    top5 = results_table[:5]
    perm_results = {}

    for r in top5:
        fname = r['feature']
        vals_a = [fd['features'][fname] for fd in folio_data if fd['currier'] == 'A']
        vals_b = [fd['features'][fname] for fd in folio_data if fd['currier'] == 'B']
        p = permutation_test_accuracy(vals_a, vals_b, r['accuracy'], n_perm=10000)
        perm_results[fname] = p
        pr(f"  {fname:<22} acc={r['accuracy']*100:.1f}%  perm-p={p:.4f}  "
           f"({'SIGNIFICANT' if p < 0.01 else 'marginal' if p < 0.05 else 'NOT sig'})")

    pr()

    # ── Step 5: SLOT2 distribution detail ────────────────────────────
    pr("STEP 5 — SLOT2 a-fraction distribution: Currier A vs B")
    pr("-" * 60)

    vals_a = sorted([fd['features']['s2_a_frac'] for fd in folio_data if fd['currier'] == 'A'])
    vals_b = sorted([fd['features']['s2_a_frac'] for fd in folio_data if fd['currier'] == 'B'])

    # Histograms (text-based)
    bins = np.linspace(0, 0.5, 11)  # 0%, 5%, 10%, ... 50%
    hist_a, _ = np.histogram(vals_a, bins=bins)
    hist_b, _ = np.histogram(vals_b, bins=bins)

    pr("  SLOT2 a-fraction distribution (text histogram):")
    pr(f"  {'Bin':>12}  {'A folios':>10}  {'B folios':>10}")
    for i in range(len(hist_a)):
        lo = bins[i] * 100
        hi = bins[i + 1] * 100
        bar_a = '█' * hist_a[i]
        bar_b = '█' * hist_b[i]
        pr(f"  {lo:4.0f}-{hi:4.0f}%    {hist_a[i]:>3} {bar_a:<15}  {hist_b[i]:>3} {bar_b}")
    pr()

    # Within-group statistics
    pr(f"  Currier A: mean={np.mean(vals_a)*100:.1f}%, sd={np.std(vals_a)*100:.1f}%, "
       f"range=[{min(vals_a)*100:.1f}%, {max(vals_a)*100:.1f}%]")
    pr(f"  Currier B: mean={np.mean(vals_b)*100:.1f}%, sd={np.std(vals_b)*100:.1f}%, "
       f"range=[{min(vals_b)*100:.1f}%, {max(vals_b)*100:.1f}%]")

    # Overlap check: how many B folios have s2_a_frac above the A median?
    median_a = np.median(vals_a)
    b_above_a_med = sum(1 for v in vals_b if v >= median_a)
    a_below_b_med = sum(1 for v in vals_a if v <= np.median(vals_b)) if vals_b else 0
    pr(f"  B folios above A median ({median_a*100:.1f}%): {b_above_a_med}/{len(vals_b)}")
    pr(f"  A folios below B median ({np.median(vals_b)*100:.1f}%): {a_below_b_med}/{len(vals_a)}")
    pr()

    # ── Step 6: Bimodality test ──────────────────────────────────────
    pr("STEP 6 — Bimodality: Is SLOT2 a-frac bimodal or gradient?")
    pr("-" * 60)

    all_s2a = [fd['features']['s2_a_frac'] for fd in folio_data]
    all_labels = [fd['currier'] for fd in folio_data]

    # Compute Hartigan's dip-like measure: gap between clusters
    sorted_all = sorted(all_s2a)
    n_all = len(sorted_all)
    # Look for largest gap in sorted values
    max_gap = 0
    gap_pos = 0
    for i in range(len(sorted_all) - 1):
        gap = sorted_all[i + 1] - sorted_all[i]
        if gap > max_gap:
            max_gap = gap
            gap_pos = i

    # If bimodal, the gap should split A and B cleanly
    below_gap = [all_labels[j] for j in range(n_all)
                 if sorted(zip(all_s2a, all_labels))[j][0] <= sorted_all[gap_pos]]
    above_gap = [all_labels[j] for j in range(n_all)
                 if sorted(zip(all_s2a, all_labels))[j][0] > sorted_all[gap_pos]]

    # Actually do it properly
    paired_sorted = sorted(zip(all_s2a, all_labels))
    below = [l for v, l in paired_sorted if v <= paired_sorted[gap_pos][0]]
    above = [l for v, l in paired_sorted if v > paired_sorted[gap_pos][0]]

    pr(f"  Largest gap in sorted s2_a_frac: {max_gap*100:.2f}% "
       f"(between position {gap_pos} and {gap_pos+1})")
    pr(f"  Values around gap: ...{sorted_all[max(0,gap_pos-1)]*100:.1f}%, "
       f"{sorted_all[gap_pos]*100:.1f}% | {sorted_all[min(gap_pos+1, n_all-1)]*100:.1f}%, "
       f"{sorted_all[min(gap_pos+2, n_all-1)]*100:.1f}%...")
    pr(f"  Below gap: {Counter(below)}")
    pr(f"  Above gap: {Counter(above)}")

    # Coefficient of bimodality: BC = (skew² + 1) / (kurtosis + 3*(n-1)²/((n-2)*(n-3)))
    # Simpler: report within-group SD vs between-group gap
    mean_a_val = np.mean(vals_a)
    mean_b_val = np.mean(vals_b)
    within_sd = np.sqrt((np.var(vals_a) * len(vals_a) + np.var(vals_b) * len(vals_b)) /
                        (len(vals_a) + len(vals_b)))
    between_gap = abs(mean_a_val - mean_b_val)
    separation_ratio = between_gap / within_sd if within_sd > 0 else float('inf')
    pr(f"  Between-group gap: {between_gap*100:.2f}%")
    pr(f"  Within-group pooled SD: {within_sd*100:.2f}%")
    pr(f"  Separation ratio (gap/SD): {separation_ratio:.2f}")
    pr(f"    (>2 = clear separation, 1-2 = overlap, <1 = mixed)")
    pr()

    # ── Step 7: Section confound check ───────────────────────────────
    pr("STEP 7 — Section confound: Does section predict SLOT2 a-frac")
    pr("         independently of Currier label?")
    pr("-" * 60)

    section_data = defaultdict(list)
    for fd in folio_data:
        section_data[(fd['section'], fd['currier'])].append(fd['features']['s2_a_frac'])

    pr(f"  {'Section':<12} {'Currier':>8} {'N':>4} {'Mean s2a%':>10} {'SD':>8}")
    pr(f"  {'─'*12} {'─'*8} {'─'*4} {'─'*10} {'─'*8}")
    for (sec, cur) in sorted(section_data.keys()):
        vals = section_data[(sec, cur)]
        pr(f"  {sec:<12} {cur:>8} {len(vals):>4} {np.mean(vals)*100:>9.1f}% {np.std(vals)*100:>7.1f}%")
    pr()

    # Within herbal only (has both A and B)
    herbal_a = [fd['features']['s2_a_frac'] for fd in folio_data
                if fd['section'] == 'herbal' and fd['currier'] == 'A']
    herbal_b = [fd['features']['s2_a_frac'] for fd in folio_data
                if fd['section'] == 'herbal' and fd['currier'] == 'B']

    if herbal_a and herbal_b:
        d_herbal = cohens_d(herbal_a, herbal_b)
        acc_herbal, _, _ = optimal_threshold_accuracy(herbal_a, herbal_b)
        pr(f"  WITHIN HERBAL SECTION (controls for topic):")
        pr(f"    A: n={len(herbal_a)}, mean s2a={np.mean(herbal_a)*100:.1f}%")
        pr(f"    B: n={len(herbal_b)}, mean s2a={np.mean(herbal_b)*100:.1f}%")
        pr(f"    Cohen's d = {d_herbal:+.3f}, threshold accuracy = {acc_herbal*100:.1f}%")
    else:
        pr("  (Cannot test within-herbal: insufficient A or B folios in herbal section)")
    pr()

    # ── Step 8: SLOT2-removed residual classification ────────────────
    pr("STEP 8 — After removing SLOT2: Can other features still classify A/B?")
    pr("-" * 60)

    # Build feature matrix excluding SLOT2 features
    non_s2_features = [f for f in feature_names if not f.startswith('s2_')]
    pr(f"  Features used (excluding SLOT2): {len(non_s2_features)}")
    pr(f"    {', '.join(non_s2_features)}")
    pr()

    # For each non-SLOT2 feature, measure accuracy
    non_s2_results = []
    for fname in non_s2_features:
        va = [fd['features'][fname] for fd in folio_data if fd['currier'] == 'A']
        vb = [fd['features'][fname] for fd in folio_data if fd['currier'] == 'B']
        acc, thresh, direction = optimal_threshold_accuracy(va, vb)
        d = cohens_d(va, vb)
        non_s2_results.append({'feature': fname, 'accuracy': acc, 'cohens_d': d,
                               'mean_A': np.mean(va), 'mean_B': np.mean(vb)})

    non_s2_results.sort(key=lambda x: x['accuracy'], reverse=True)

    pr(f"  {'Feature':<22} {'Mean A':>8} {'Mean B':>8} {'Cohen d':>8} {'Accuracy':>9}")
    pr(f"  {'─'*22} {'─'*8} {'─'*8} {'─'*8} {'─'*9}")
    for r in non_s2_results:
        pr(f"  {r['feature']:<22} {r['mean_A']:>8.4f} {r['mean_B']:>8.4f} "
           f"{r['cohens_d']:>+8.3f} {r['accuracy']*100:>8.1f}%")
    pr()

    best_non_s2 = non_s2_results[0]
    best_s2 = next(r for r in results_table if r['feature'].startswith('s2_'))
    pr(f"  Best SLOT2 feature:     {best_s2['feature']:<22} accuracy={best_s2['accuracy']*100:.1f}%")
    pr(f"  Best non-SLOT2 feature: {best_non_s2['feature']:<22} accuracy={best_non_s2['accuracy']*100:.1f}%")
    pr(f"  Accuracy drop from removing SLOT2: {(best_s2['accuracy'] - best_non_s2['accuracy'])*100:+.1f}pp")
    pr()

    if best_non_s2['accuracy'] > 0.80:
        pr("  VERDICT: NON-SLOT2 features ALSO separate A/B well.")
        pr("  → SLOT2 is ONE component but NOT the sole mechanism.")
        residual_verdict = 'MULTI_FEATURE'
    elif best_non_s2['accuracy'] > 0.65:
        pr("  VERDICT: Non-SLOT2 features show MODERATE A/B separation.")
        pr("  → SLOT2 is the DOMINANT single feature but not the only one.")
        residual_verdict = 'SLOT2_DOMINANT'
    else:
        pr("  VERDICT: Non-SLOT2 features FAIL to classify A/B.")
        pr("  → SLOT2 IS the Currier distinction. One parameter, two regimes.")
        residual_verdict = 'SLOT2_IS_CURRIER'
    pr()

    # ── Step 9: Folio-order gradient ─────────────────────────────────
    pr("STEP 9 — Folio-order gradient: Does SLOT2 a-frac track folio order?")
    pr("-" * 60)

    sorted_folios = sorted(folio_data, key=lambda fd: fd['folio_num'])
    folio_nums = [fd['folio_num'] for fd in sorted_folios]
    s2a_vals = [fd['features']['s2_a_frac'] for fd in sorted_folios]
    currier_labels = [fd['currier'] for fd in sorted_folios]

    r_folio_s2a = pearson_r(folio_nums, s2a_vals)
    pr(f"  r(folio_number, s2_a_frac) = {r_folio_s2a:.4f}")
    pr(f"  (positive = later folios have MORE 'a' in SLOT2)")
    pr()

    # Show per-folio scatter (A vs B colored)
    pr(f"  {'Folio':>8} {'Cur':>4} {'S2a%':>7}  Plot")
    pr(f"  {'─'*8} {'─'*4} {'─'*7}  {'─'*40}")
    for fd in sorted_folios[:10]:
        bar_len = int(fd['features']['s2_a_frac'] * 100)
        marker = 'A' if fd['currier'] == 'A' else 'B'
        bar = marker * min(bar_len, 40)
        pr(f"  f{fd['folio_num']:>5}   {fd['currier']:>2} {fd['features']['s2_a_frac']*100:>6.1f}%  |{bar}")
    if len(sorted_folios) > 20:
        pr(f"  {'...':>8}")
    for fd in sorted_folios[-10:]:
        bar_len = int(fd['features']['s2_a_frac'] * 100)
        marker = 'A' if fd['currier'] == 'A' else 'B'
        bar = marker * min(bar_len, 40)
        pr(f"  f{fd['folio_num']:>5}   {fd['currier']:>2} {fd['features']['s2_a_frac']*100:>6.1f}%  |{bar}")
    pr()

    # ── Step 10: Cross-correlation of top features ───────────────────
    pr("STEP 10 — Feature cross-correlation (top 6): Is SLOT2 redundant")
    pr("          with other features, or independent?")
    pr("-" * 60)

    top_features = [r['feature'] for r in results_table[:6]]
    pr(f"  Features: {', '.join(top_features)}")
    pr()

    # Correlation matrix
    pr(f"  {'':>22}", end='')
    for tf in top_features:
        pr(f" {tf[:7]:>8}", end='')
    pr()

    for tf1 in top_features:
        v1 = [fd['features'][tf1] for fd in folio_data]
        pr(f"  {tf1:<22}", end='')
        for tf2 in top_features:
            v2 = [fd['features'][tf2] for fd in folio_data]
            r = pearson_r(v1, v2)
            pr(f" {r:>+8.3f}", end='')
        pr()
    pr()

    # ── Step 11: Synthesis and verdict ───────────────────────────────
    pr("=" * 72)
    pr("  SYNTHESIS & VERDICT")
    pr("=" * 72)
    pr()

    # Collect key numbers
    s2_acc = best_s2['accuracy']
    s2_d = abs(best_s2['cohens_d'])
    non_s2_acc = best_non_s2['accuracy']
    s2_perm = perm_results.get(best_s2['feature'], 1.0)

    pr(f"  KEY FINDINGS:")
    pr(f"  1. Best SLOT2 feature for A/B classification:")
    pr(f"     {best_s2['feature']}: accuracy={s2_acc*100:.1f}%, |d|={s2_d:.2f}, perm-p={s2_perm:.4f}")
    pr(f"  2. Best non-SLOT2 feature: {best_non_s2['feature']}: accuracy={non_s2_acc*100:.1f}%")
    pr(f"  3. Separation ratio (gap/SD): {separation_ratio:.2f}")
    pr(f"  4. Residual test: {residual_verdict}")
    pr(f"  5. r(folio_order, s2_a_frac) = {r_folio_s2a:.4f}")
    pr()

    # Composite verdict
    if s2_acc >= 0.90 and s2_perm < 0.01 and residual_verdict == 'SLOT2_IS_CURRIER':
        verdict = 'SLOT2_IS_CURRIER'
        pr("  VERDICT: SLOT2_IS_CURRIER")
        pr("  The Currier A/B distinction reduces to a single LOOP grammar")
        pr("  parameter: the filler of SLOT2 (front vowel position).")
        pr("  'Two languages' → one language with two SLOT2 regimes.")
    elif s2_acc >= 0.80 and s2_perm < 0.01 and residual_verdict == 'SLOT2_DOMINANT':
        verdict = 'SLOT2_DOMINANT_BUT_NOT_SOLE'
        pr("  VERDICT: SLOT2_DOMINANT_BUT_NOT_SOLE")
        pr("  SLOT2 is the strongest single predictor of Currier A/B,")
        pr("  but other features (onset, coda, word length) contribute too.")
        pr("  The 'two languages' are substantially but not fully explained")
        pr("  by SLOT2 content.")
    elif s2_acc >= 0.70 and s2_perm < 0.05:
        verdict = 'SLOT2_CONTRIBUTES'
        pr("  VERDICT: SLOT2_CONTRIBUTES")
        pr("  SLOT2 is a significant but not dominant component of Currier A/B.")
        pr("  Multiple grammatical features differ between A and B.")
    else:
        verdict = 'SLOT2_NOT_DECISIVE'
        pr("  VERDICT: SLOT2_NOT_DECISIVE")
        pr("  SLOT2 does NOT meaningfully separate Currier A from B.")
        pr("  The zodiac_galenic_axis/92 zodiac finding does not generalize manuscript-wide.")

    pr()
    pr("  SKEPTICISM NOTES:")
    pr("  - Classification accuracy is measured with OPTIMAL threshold (best-case).")
    pr("    Real out-of-sample accuracy would be lower.")
    pr("  - Currier labels from the 1970s are not ground truth; some are disputed.")
    pr("  - If SLOT2 and section correlate, the 'A/B = SLOT2' story may really be")
    pr("    'A/B = section = topic = vocabulary', which is less interesting.")
    pr("  - SLOT2 was DESIGNED to accommodate both 'a' and 'e'. High variation")
    pr("    in SLOT2 content across sections is EXPECTED by the grammar's design.")
    pr()

    # ── Save results ─────────────────────────────────────────────────
    results = {
        'phase': 93,
        'n_folios_A': n_a,
        'n_folios_B': n_b,
        'min_words_threshold': MIN_WORDS,
        'best_s2_feature': best_s2['feature'],
        'best_s2_accuracy': round(s2_acc, 4),
        'best_s2_cohens_d': round(best_s2['cohens_d'], 4),
        'best_s2_perm_p': round(s2_perm, 4),
        'best_non_s2_feature': best_non_s2['feature'],
        'best_non_s2_accuracy': round(non_s2_acc, 4),
        'separation_ratio': round(separation_ratio, 3),
        'residual_verdict': residual_verdict,
        'r_folio_order_s2a': round(r_folio_s2a, 4),
        'verdict': verdict,
        'all_features_ranked': [
            {'feature': r['feature'], 'accuracy': round(r['accuracy'], 4),
             'cohens_d': round(r['cohens_d'], 4),
             'mean_A': round(r['mean_A'], 5), 'mean_B': round(r['mean_B'], 5)}
            for r in results_table
        ],
    }

    out_path = RESULTS_DIR / 'currier_slot2_regime_currier_slot2.json'
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    pr(f"  Results saved to {out_path}")

    # Save full output
    txt_path = RESULTS_DIR / 'currier_slot2_regime_currier_slot2.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Full output saved to {txt_path}")


if __name__ == '__main__':
    main()
