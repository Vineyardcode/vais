#!/usr/bin/env python3
"""
Phase 90 — Cross-Word Chunk Dependencies

═══════════════════════════════════════════════════════════════════════

QUESTION:
  Does the anomalously strong cross-word dependency found at the
  glyph level (Phase 62: NMI(last→next_init) = 0.080, z=313, 1.8×
  Italian) persist, strengthen, or vanish at the chunk level?

MOTIVATION:
  Phases 85-89 thoroughly characterized WITHIN-word chunk structure.
  We now know:
  - Chunks behave like NL syllables (entropy, positional concentration)
  - Shared chunks are NOT homographs (Phase 89)
  - Positional cipher confidence is 50/50

  The TMA paradox (Phase 84) remains unresolved: VMS has 1.9× NL mean
  word-order MI but 0.64 vs NL 0.83 character entropy. This paradox
  implicates CROSS-WORD structure — the strongest untested dimension
  at chunk level.

  NL vs cipher/hoax predictions DIVERGE:
  - In NL, syntax operates at word level. Last syllable of word N
    should carry near-zero info about first syllable of word N+1.
    (Morpho-phonological sandhi exists but is weak in written text.)
  - In a positional cipher or generative hoax, sub-word rules may
    not respect word boundaries, creating anomalous cross-boundary MI.

APPROACH:
  1. Parse VMS preserving LINE ORDER (word N, word N+1 must be on
     the same line to be adjacent — line breaks are NOT continuations).
  2. For each consecutive word pair (same line):
     a. Extract F-chunk of word N and I-chunk of word N+1
     b. Also extract within-word consecutive chunk bigrams
  3. Compute:
     a. MI(F_n, I_{n+1}) — cross-boundary chunk MI
     b. MI(consecutive within-word chunks) — within-word chunk MI
     c. RATIO = cross / within — boundary attenuation factor
     d. H(I_{n+1}) and H(I_{n+1} | F_n) — conditional reduction
  4. Same metrics for NL characters AND syllables
  5. Z-score VMS vs NL baselines
  6. Permutation null: shuffle word order within each line
  7. Line-break control: does MI vanish when word pair spans a line?

CRITICAL CONFOUNDS:
  1. INVENTORY CONFOUND: F-chunks and I-chunks draw from different
     type inventories (Phase 88: J(I,F)=0.241). This means marginal
     distributions H(F) and H(I) are computed over DIFFERENT type
     sets. MI > 0 could reflect correlation between position-marker
     features rather than genuine inter-word dependency.
     CONTROL: NL syllables also have position-specific inventories
     (Phase 88: J(I,F)_syls ≈ 0.07). They are the primary baseline.

  2. LINE STRUCTURE: VMS lines are meaningful units (Phase 62: line
     position has z=158-249 MI). Words at line boundaries may not be
     adjacent syntactically. We restrict to same-line pairs.

  3. FREQUENCY CONFOUND: A few very common F-chunk × I-chunk pairs
     (e.g., "e.d.y → q.o.k") might dominate MI. Must check whether
     MI is driven by a handful of bigrams or distributed broadly.

  4. ALPHABET SIZE: VMS has ~125 I-types and ~117 F-types (Phase 88).
     NL chars have ~26. More types → higher H → potentially higher
     raw MI from random co-occurrence. NMI (= MI / min(H_X, H_Y))
     normalizes for this, but only partially.

SKEPTICISM NOTES:
  - The glyph-level result (NMI=0.080) used single characters.
    Chunks are multi-glyph units with fewer types → MI may drop
    simply from coarser grain.
  - Must distinguish GENUINE DEPENDENCY from CONFOUND-COMPATIBLE.
  - If VMS cross-word MI ≈ NL syllable cross-word MI, the anomaly
    vanishes — it was a unit-of-analysis issue, not a real signal.
  - If VMS cross-word MI >> NL syllable cross-word MI, the anomaly
    persists and demands explanation.
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import chunk_to_str, eva_to_glyphs, load_reference_text, parse_one_chunk, parse_word_into_chunks

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
# EVA GLYPH TOKENIZER (from Phase 85)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']



# ═══════════════════════════════════════════════════════════════════════
# MAURO'S LOOP GRAMMAR — CHUNK PARSER (from Phase 85)
# ═══════════════════════════════════════════════════════════════════════

SLOT1 = {'ch', 'sh', 'y'}
SLOT2_RUNS = {'e'}
SLOT2_SINGLE = {'q', 'a'}
SLOT3 = {'o'}
SLOT4_RUNS = {'i'}
SLOT4_SINGLE = {'d'}
SLOT5 = {'y', 'p', 'f', 'k', 'l', 'r', 's', 't',
         'cth', 'ckh', 'cph', 'cfh', 'n', 'm'}
MAX_CHUNKS = 6





# ═══════════════════════════════════════════════════════════════════════
# VMS CORPUS PARSING — LINE-AWARE (adapted from Phase 31)
# ═══════════════════════════════════════════════════════════════════════

SECTION_MAP = {
    'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
    'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
}

def load_vms_lines():
    """Parse VMS folios preserving line order.

    Returns list of (line_id, section, [word_str, ...])
    Only includes words with ≥2 characters.
    """
    lines = []
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        section = 'unknown'
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'):
                ll = line.lower()
                for key, val in SECTION_MAP.items():
                    if key in ll:
                        section = val
                        if val == 'herbal' and '-b' in ll:
                            section = 'herbal-B'
                        elif val == 'herbal':
                            section = 'herbal-A'
                continue
            m = re.match(r'<([^>]+)>', line)
            if not m:
                continue
            lid = m.group(1)
            rest = line[m.end():].strip()
            if not rest:
                continue
            words = []
            for w in re.split(r'[.\s,;]+', rest):
                w = re.sub(r'[^a-z]', '', w.lower().strip())
                if len(w) >= 2:
                    words.append(w)
            if words:
                lines.append((lid, section, words))
    return lines


def vms_lines_to_chunk_lines(vms_lines):
    """Convert word-level lines to chunk-level lines.

    Returns list of (line_id, section, [[chunk_str, ...], [chunk_str, ...], ...])
    Each inner list = chunks for one word.
    """
    chunk_lines = []
    for lid, section, words in vms_lines:
        word_chunks_list = []
        for w in words:
            chunks, unparsed, _ = parse_word_into_chunks(w)
            chunk_ids = [chunk_to_str(c) for c in chunks]
            if chunk_ids:  # skip words that fail to parse
                word_chunks_list.append(chunk_ids)
        if word_chunks_list:
            chunk_lines.append((lid, section, word_chunks_list))
    return chunk_lines


# ═══════════════════════════════════════════════════════════════════════
# NL REF TEXT LOADING + SYLLABIFICATION (from Phase 85)
# ═══════════════════════════════════════════════════════════════════════

VOWELS_LATIN = set('aeiouyàáâãäåæèéêëìíîïòóôõöùúûüýœ')

def syllabify_word(word, vowels=VOWELS_LATIN):
    if len(word) <= 1:
        return [word]
    is_v = [c in vowels for c in word]
    boundaries = [0]
    i = 1
    while i < len(word):
        if is_v[i] and i > 0 and not is_v[i-1]:
            j = i - 1
            while j > boundaries[-1] and not is_v[j]:
                j -= 1
            if j > boundaries[-1]:
                split_at = j + 1
            else:
                split_at = j if is_v[j] else j + 1
            if split_at > boundaries[-1] and split_at < i:
                boundaries.append(split_at)
        i += 1
    syllables = []
    for k in range(len(boundaries)):
        start = boundaries[k]
        end = boundaries[k+1] if k+1 < len(boundaries) else len(word)
        syl = word[start:end]
        if syl:
            syllables.append(syl)
    return syllables if syllables else [word]



def nl_words_to_sentence_lines(words, sentence_len=10):
    """Convert NL word list to pseudo-lines of fixed length.

    We don't have sentence boundaries for all NL texts, so we use
    fixed-length windows. This ensures cross-word pairs are from
    nearby context, parallel to VMS lines.
    """
    lines = []
    for i in range(0, len(words), sentence_len):
        segment = words[i:i + sentence_len]
        if len(segment) >= 2:
            lines.append(segment)
    return lines


# ═══════════════════════════════════════════════════════════════════════
# MI COMPUTATION UTILITIES
# ═══════════════════════════════════════════════════════════════════════

def compute_mi_from_pairs(pairs):
    """Compute MI, NMI, H(X), H(Y), H(Y|X) from a list of (x, y) pairs.

    Returns dict with all information-theoretic measures.
    """
    joint = Counter(pairs)
    x_marg = Counter(x for x, y in pairs)
    y_marg = Counter(y for x, y in pairs)
    n = len(pairs)

    if n == 0:
        return {'mi': 0, 'nmi': 0, 'h_x': 0, 'h_y': 0,
                'h_y_given_x': 0, 'reduction_pct': 0, 'n_pairs': 0,
                'n_x_types': 0, 'n_y_types': 0}

    h_x = -sum((c / n) * math.log2(c / n) for c in x_marg.values() if c > 0)
    h_y = -sum((c / n) * math.log2(c / n) for c in y_marg.values() if c > 0)
    h_joint = -sum((c / n) * math.log2(c / n) for c in joint.values() if c > 0)

    mi = h_x + h_y - h_joint
    # Clamp MI to 0 (can be slightly negative from floating point)
    mi = max(0.0, mi)

    nmi = mi / min(h_x, h_y) if min(h_x, h_y) > 1e-9 else 0.0
    h_y_given_x = h_joint - h_x
    reduction = 100 * mi / h_y if h_y > 1e-9 else 0.0

    return {
        'mi': mi,
        'nmi': nmi,
        'h_x': h_x,
        'h_y': h_y,
        'h_joint': h_joint,
        'h_y_given_x': h_y_given_x,
        'reduction_pct': reduction,
        'n_pairs': n,
        'n_x_types': len(x_marg),
        'n_y_types': len(y_marg),
    }


def compute_top_bigrams(pairs, top_n=20):
    """Return top-N most frequent bigrams and their contribution to MI."""
    joint = Counter(pairs)
    x_marg = Counter(x for x, y in pairs)
    y_marg = Counter(y for x, y in pairs)
    n = len(pairs)
    if n == 0:
        return []

    results = []
    for (x, y), c in joint.most_common(top_n):
        p_xy = c / n
        p_x = x_marg[x] / n
        p_y = y_marg[y] / n
        pmi = math.log2(p_xy / (p_x * p_y)) if p_x > 0 and p_y > 0 else 0
        mi_contrib = p_xy * pmi
        results.append({
            'x': x, 'y': y, 'count': c,
            'pmi': pmi, 'mi_contrib': mi_contrib,
            'p_xy': p_xy, 'p_x': p_x, 'p_y': p_y,
        })
    return results


# ═══════════════════════════════════════════════════════════════════════
# CROSS-WORD + WITHIN-WORD EXTRACTION
# ═══════════════════════════════════════════════════════════════════════

def extract_cross_and_within_pairs(unit_lines, unit_level='chunk'):
    """Extract cross-word boundary and within-word unit bigram pairs.

    Args:
        unit_lines: for VMS chunks: list of (lid, section, [[chunk,...], [chunk,...]])
                    for NL: list of [[unit,...], [unit,...]] (word-level unit lists)
        unit_level: 'chunk' (VMS), 'char', or 'syl' (NL)

    Returns:
        cross_pairs: [(F_chunk_word_n, I_chunk_word_n+1), ...]
        within_pairs: [(chunk_i, chunk_i+1), ...] for consecutive within-word
        cross_1chunk_pairs: [(whole_word_chunk, I_chunk_next), ...] for 1-chunk words
    """
    cross_pairs = []
    within_pairs = []
    cross_1chunk_pairs = []

    if unit_level == 'chunk':
        # VMS format: (lid, section, [[chunks_w1], [chunks_w2], ...])
        for lid, section, words in unit_lines:
            for w_idx in range(len(words)):
                word_units = words[w_idx]
                # Within-word consecutive pairs
                for i in range(len(word_units) - 1):
                    within_pairs.append((word_units[i], word_units[i + 1]))
                # Cross-word: F-chunk of this word → I-chunk of next word
                if w_idx < len(words) - 1:
                    f_chunk = word_units[-1]
                    i_chunk_next = words[w_idx + 1][0]
                    if len(word_units) == 1:
                        cross_1chunk_pairs.append((f_chunk, i_chunk_next))
                    else:
                        cross_pairs.append((f_chunk, i_chunk_next))
    else:
        # NL format: [[units_w1], [units_w2], ...] per line
        for line_words in unit_lines:
            for w_idx in range(len(line_words)):
                word_units = line_words[w_idx]
                for i in range(len(word_units) - 1):
                    within_pairs.append((word_units[i], word_units[i + 1]))
                if w_idx < len(line_words) - 1:
                    f_unit = word_units[-1]
                    i_unit_next = line_words[w_idx + 1][0]
                    if len(word_units) == 1:
                        cross_1chunk_pairs.append((f_unit, i_unit_next))
                    else:
                        cross_pairs.append((f_unit, i_unit_next))

    return cross_pairs, within_pairs, cross_1chunk_pairs


# ═══════════════════════════════════════════════════════════════════════
# NULL MODEL
# ═══════════════════════════════════════════════════════════════════════

def null_model_cross_mi(unit_lines, unit_level, n_trials=100):
    """Shuffle word order within each line, recompute cross-word MI.

    This preserves within-word structure and line composition but
    destroys word-order dependencies.
    """
    null_mis = []
    null_nmis = []

    for trial in range(n_trials):
        shuffled_lines = []
        if unit_level == 'chunk':
            for lid, section, words in unit_lines:
                sw = list(words)
                random.shuffle(sw)
                shuffled_lines.append((lid, section, sw))
        else:
            for line_words in unit_lines:
                sw = list(line_words)
                random.shuffle(sw)
                shuffled_lines.append(sw)

        cross, _, _ = extract_cross_and_within_pairs(shuffled_lines, unit_level)
        result = compute_mi_from_pairs(cross)
        null_mis.append(result['mi'])
        null_nmis.append(result['nmi'])

    return {
        'mi_mean': float(np.mean(null_mis)),
        'mi_std': float(np.std(null_mis)),
        'nmi_mean': float(np.mean(null_nmis)),
        'nmi_std': float(np.std(null_nmis)),
    }


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 76)
    pr("PHASE 90 — CROSS-WORD CHUNK DEPENDENCIES")
    pr("=" * 76)
    pr()
    pr("  Does the glyph-level cross-word MI anomaly (Phase 62: NMI=0.080,")
    pr("  z=313, 1.8× Italian) persist at the chunk level?")
    pr()
    pr("  KEY CONFOUND: F-chunks and I-chunks draw from different inventories.")
    pr("  MI > 0 could reflect inventory correlation, not syntax.")
    pr("  NL syllable baseline is the PRIMARY control.")
    pr()

    N_TRIALS = 100

    # ── STEP 1: PARSE VMS WITH LINE ORDER ────────────────────────────

    pr("─" * 76)
    pr("STEP 1: PARSE VMS (LINE-AWARE)")
    pr("─" * 76)
    pr()

    vms_lines = load_vms_lines()
    vms_chunk_lines = vms_lines_to_chunk_lines(vms_lines)

    n_lines = len(vms_chunk_lines)
    n_words = sum(len(wds) for _, _, wds in vms_chunk_lines)
    n_chunks = sum(len(c) for _, _, wds in vms_chunk_lines for c in wds)

    pr(f"  VMS: {n_lines} lines, {n_words} words, {n_chunks} chunk tokens")

    # Word length distribution in this parse
    wld = Counter()
    for _, _, wds in vms_chunk_lines:
        for w in wds:
            wld[len(w)] += 1
    pr(f"  Word lengths: ", end='')
    for k in sorted(wld.keys()):
        pr(f"{k}-chunk: {wld[k]} ({100*wld[k]/n_words:.1f}%) ", end='')
    pr()

    # Count 1-chunk words (these have ambiguous F/I identity)
    n_1chunk = wld.get(1, 0)
    pr(f"  1-chunk words (F=I, ambiguous): {n_1chunk} ({100*n_1chunk/n_words:.1f}%)")
    pr()

    # ── STEP 2: EXTRACT PAIRS ────────────────────────────────────────

    pr("─" * 76)
    pr("STEP 2: EXTRACT CROSS-WORD AND WITHIN-WORD PAIRS")
    pr("─" * 76)
    pr()

    cross_vms, within_vms, cross_1ch_vms = extract_cross_and_within_pairs(
        vms_chunk_lines, 'chunk')

    # Also get ALL cross pairs (including 1-chunk words) for comparison
    cross_all_vms = cross_vms + cross_1ch_vms

    pr(f"  Cross-word pairs (≥2-chunk words only): {len(cross_vms)}")
    pr(f"  Cross-word pairs (1-chunk words):       {len(cross_1ch_vms)}")
    pr(f"  Cross-word pairs (ALL):                 {len(cross_all_vms)}")
    pr(f"  Within-word consecutive pairs:          {len(within_vms)}")
    pr()

    # ── STEP 3: VMS MI COMPUTATION ───────────────────────────────────

    pr("─" * 76)
    pr("STEP 3: VMS CHUNK-LEVEL MI")
    pr("─" * 76)
    pr()

    mi_cross_vms = compute_mi_from_pairs(cross_vms)
    mi_cross_all_vms = compute_mi_from_pairs(cross_all_vms)
    mi_within_vms = compute_mi_from_pairs(within_vms)

    def print_mi_block(label, result):
        pr(f"  {label}:")
        pr(f"    MI     = {result['mi']:.4f} bits")
        pr(f"    NMI    = {result['nmi']:.4f}")
        pr(f"    H(X)   = {result['h_x']:.4f} bits  ({result['n_x_types']} types)")
        pr(f"    H(Y)   = {result['h_y']:.4f} bits  ({result['n_y_types']} types)")
        pr(f"    H(Y|X) = {result['h_y_given_x']:.4f} bits")
        pr(f"    H(Y) reduction: {result['reduction_pct']:.2f}%")
        pr(f"    N pairs: {result['n_pairs']}")
        pr()

    print_mi_block("CROSS-WORD (≥2-chunk words, F→I)", mi_cross_vms)
    print_mi_block("CROSS-WORD (ALL words, F/whole→I)", mi_cross_all_vms)
    print_mi_block("WITHIN-WORD (consecutive chunks)", mi_within_vms)

    # Ratio
    ratio_vms = mi_cross_vms['mi'] / mi_within_vms['mi'] if mi_within_vms['mi'] > 1e-9 else float('nan')
    ratio_nmi_vms = mi_cross_vms['nmi'] / mi_within_vms['nmi'] if mi_within_vms['nmi'] > 1e-9 else float('nan')
    pr(f"  BOUNDARY ATTENUATION:")
    pr(f"    MI  ratio (cross/within): {ratio_vms:.4f}")
    pr(f"    NMI ratio (cross/within): {ratio_nmi_vms:.4f}")
    pr(f"    → {'Strong boundary effect' if ratio_vms < 0.3 else 'Moderate boundary' if ratio_vms < 0.7 else 'Weak boundary'}")
    pr()

    # Top cross-word bigrams
    pr("  TOP-20 CROSS-WORD CHUNK BIGRAMS (F→I):")
    pr(f"    {'F-chunk':<18s}  {'I-chunk':<18s}  {'Count':>6s}  {'PMI':>7s}  "
       f"{'MI-contrib':>10s}  {'p(x,y)':>8s}")
    pr(f"    {'─'*18}  {'─'*18}  {'─'*6}  {'─'*7}  {'─'*10}  {'─'*8}")
    top_cross = compute_top_bigrams(cross_vms, top_n=20)
    for b in top_cross:
        pr(f"    {b['x']:<18s}  {b['y']:<18s}  {b['count']:6d}  {b['pmi']:+7.3f}  "
           f"{b['mi_contrib']:10.6f}  {b['p_xy']:8.5f}")
    pr()

    # Check MI concentration: what % of total MI comes from top-20 bigrams?
    total_mi_from_top20 = sum(b['mi_contrib'] for b in top_cross)
    pr(f"  MI from top-20 bigrams: {total_mi_from_top20:.4f} / {mi_cross_vms['mi']:.4f} "
       f"= {100*total_mi_from_top20/mi_cross_vms['mi']:.1f}% of total")
    pr()

    # ── STEP 4: NL BASELINES ─────────────────────────────────────────

    pr("─" * 76)
    pr("STEP 4: NL CHARACTER + SYLLABLE BASELINES")
    pr("─" * 76)
    pr()

    nl_texts = {
        'Latin-Caesar':    DATA_DIR / 'latin_texts' / 'caesar.txt',
        'Latin-Vulgate':   DATA_DIR / 'latin_texts' / 'vulgate_genesis.txt',
        'Latin-Apicius':   DATA_DIR / 'latin_texts' / 'apicius.txt',
        'Italian-Cucina':  DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt',
        'French-Viandier': DATA_DIR / 'vernacular_texts' / 'french_viandier.txt',
        'English-Cury':    DATA_DIR / 'vernacular_texts' / 'english_cury.txt',
        'German-Faust':    DATA_DIR / 'vernacular_texts' / 'german_faust.txt',
    }
    bvgs_path = DATA_DIR / 'vernacular_texts' / 'german_bvgs_raw.txt'
    if bvgs_path.exists():
        nl_texts['German-BvgS'] = bvgs_path

    nl_char_results = {}
    nl_syl_results = {}

    # Use same pseudo-line length as VMS mean (VMS has ~5.5 words/line)
    vms_mean_words_per_line = n_words / n_lines if n_lines > 0 else 5
    pseudo_line_len = max(3, round(vms_mean_words_per_line))
    pr(f"  VMS mean words/line: {vms_mean_words_per_line:.1f}")
    pr(f"  NL pseudo-line length: {pseudo_line_len} words")
    pr()

    for name, path in sorted(nl_texts.items()):
        if not path.exists():
            pr(f"  SKIP {name}: not found")
            continue
        words = load_reference_text(path)
        if len(words) < 500:
            pr(f"  SKIP {name}: too few words ({len(words)})")
            continue

        # Character-level
        char_word_units = [list(w) for w in words]
        char_lines = nl_words_to_sentence_lines(char_word_units, pseudo_line_len)
        cross_c, within_c, _ = extract_cross_and_within_pairs(char_lines, 'char')
        mi_cross_c = compute_mi_from_pairs(cross_c)
        mi_within_c = compute_mi_from_pairs(within_c)
        ratio_c = mi_cross_c['mi'] / mi_within_c['mi'] if mi_within_c['mi'] > 1e-9 else float('nan')
        nl_char_results[name] = {
            'mi_cross': mi_cross_c, 'mi_within': mi_within_c,
            'ratio': ratio_c, 'n_words': len(words),
        }

        # Syllable-level
        syl_word_units = [syllabify_word(w) for w in words]
        syl_lines = nl_words_to_sentence_lines(syl_word_units, pseudo_line_len)
        cross_s, within_s, _ = extract_cross_and_within_pairs(syl_lines, 'syl')
        mi_cross_s = compute_mi_from_pairs(cross_s)
        mi_within_s = compute_mi_from_pairs(within_s)
        ratio_s = mi_cross_s['mi'] / mi_within_s['mi'] if mi_within_s['mi'] > 1e-9 else float('nan')
        nl_syl_results[name] = {
            'mi_cross': mi_cross_s, 'mi_within': mi_within_s,
            'ratio': ratio_s, 'n_words': len(words),
        }

    # Print character baselines
    pr("  NL CHARACTER baselines:")
    pr(f"    {'System':<24s}  {'Cross MI':>8s}  {'Cross NMI':>9s}  "
       f"{'Within MI':>9s}  {'Ratio':>6s}  {'H(Y) red%':>9s}")
    pr(f"    {'─'*24}  {'─'*8}  {'─'*9}  {'─'*9}  {'─'*6}  {'─'*9}")
    pr(f"    {'VMS chunks':<24s}  {mi_cross_vms['mi']:8.4f}  {mi_cross_vms['nmi']:9.4f}  "
       f"{mi_within_vms['mi']:9.4f}  {ratio_vms:6.4f}  "
       f"{mi_cross_vms['reduction_pct']:8.2f}%")
    for name, r in sorted(nl_char_results.items()):
        rt = r['ratio']
        pr(f"    {name + '-char':<24s}  {r['mi_cross']['mi']:8.4f}  "
           f"{r['mi_cross']['nmi']:9.4f}  {r['mi_within']['mi']:9.4f}  "
           f"{rt:6.4f}  {r['mi_cross']['reduction_pct']:8.2f}%")
    pr()

    # Print syllable baselines
    pr("  NL SYLLABLE baselines:")
    pr(f"    {'System':<24s}  {'Cross MI':>8s}  {'Cross NMI':>9s}  "
       f"{'Within MI':>9s}  {'Ratio':>6s}  {'H(Y) red%':>9s}")
    pr(f"    {'─'*24}  {'─'*8}  {'─'*9}  {'─'*9}  {'─'*6}  {'─'*9}")
    pr(f"    {'VMS chunks':<24s}  {mi_cross_vms['mi']:8.4f}  {mi_cross_vms['nmi']:9.4f}  "
       f"{mi_within_vms['mi']:9.4f}  {ratio_vms:6.4f}  "
       f"{mi_cross_vms['reduction_pct']:8.2f}%")
    for name, r in sorted(nl_syl_results.items()):
        rt = r['ratio']
        pr(f"    {name + '-syl':<24s}  {r['mi_cross']['mi']:8.4f}  "
           f"{r['mi_cross']['nmi']:9.4f}  {r['mi_within']['mi']:9.4f}  "
           f"{rt:6.4f}  {r['mi_cross']['reduction_pct']:8.2f}%")
    pr()

    # ── STEP 5: Z-SCORE COMPARISON ───────────────────────────────────

    pr("─" * 76)
    pr("STEP 5: Z-SCORE COMPARISON — VMS vs NL BASELINES")
    pr("─" * 76)
    pr()

    def z_score(vms_val, nl_results, path_fn):
        vals = [path_fn(r) for r in nl_results.values()
                if not math.isnan(path_fn(r))]
        if len(vals) < 2:
            return float('nan'), float('nan'), float('nan')
        m = float(np.mean(vals))
        s = float(np.std(vals))
        z = (vms_val - m) / s if s > 1e-9 else float('nan')
        return m, s, z

    metrics = [
        ('Cross MI',      lambda r: r['mi_cross']['mi']),
        ('Cross NMI',     lambda r: r['mi_cross']['nmi']),
        ('Within MI',     lambda r: r['mi_within']['mi']),
        ('Ratio (c/w)',   lambda r: r['ratio']),
        ('H(Y) red. %',   lambda r: r['mi_cross']['reduction_pct']),
    ]

    pr("  METRIC              VMS     NL-char μ±σ     z(char)    NL-syl μ±σ      z(syl)")
    pr("  ─────────────────  ──────  ──────────────  ────────  ──────────────  ────────")

    z_chars_all = {}
    z_syls_all = {}

    for label, fn in metrics:
        vms_val = fn({'mi_cross': mi_cross_vms, 'mi_within': mi_within_vms,
                      'ratio': ratio_vms})
        mc, sc, zc = z_score(vms_val, nl_char_results, fn)
        ms, ss, zs = z_score(vms_val, nl_syl_results, fn)
        z_chars_all[label] = zc
        z_syls_all[label] = zs

        def fmt_ms(m, s):
            if math.isnan(m): return '       N/A    '
            return f"{m:6.4f}±{s:.4f}"
        def fmtz(z):
            if math.isnan(z): return '     N/A'
            return f"{z:+8.2f}"

        pr(f"  {label:<18s}  {vms_val:6.4f}  {fmt_ms(mc, sc):<14s}  {fmtz(zc)}  "
           f"{fmt_ms(ms, ss):<14s}  {fmtz(zs)}")
    pr()

    # ── STEP 6: PERMUTATION NULL MODEL ────────────────────────────────

    pr("─" * 76)
    pr(f"STEP 6: PERMUTATION NULL MODEL ({N_TRIALS} trials)")
    pr("─" * 76)
    pr()
    pr("  Shuffle word order within each VMS line.")
    pr("  Preserves within-word chunk structure and line composition.")
    pr("  Destroys word-order dependencies.")
    pr()

    null_vms = null_model_cross_mi(vms_chunk_lines, 'chunk', n_trials=N_TRIALS)

    z_null_mi = ((mi_cross_vms['mi'] - null_vms['mi_mean']) / null_vms['mi_std']
                 if null_vms['mi_std'] > 1e-9 else float('nan'))
    z_null_nmi = ((mi_cross_vms['nmi'] - null_vms['nmi_mean']) / null_vms['nmi_std']
                  if null_vms['nmi_std'] > 1e-9 else float('nan'))

    pr(f"  Cross MI:  observed = {mi_cross_vms['mi']:.4f},  "
       f"null = {null_vms['mi_mean']:.4f} ± {null_vms['mi_std']:.4f},  "
       f"z = {z_null_mi:+.2f}")
    pr(f"  Cross NMI: observed = {mi_cross_vms['nmi']:.4f},  "
       f"null = {null_vms['nmi_mean']:.4f} ± {null_vms['nmi_std']:.4f},  "
       f"z = {z_null_nmi:+.2f}")
    pr()
    if z_null_mi > 3:
        pr("  → Cross-word MI is SIGNIFICANTLY above word-order shuffle.")
        pr("    Genuine inter-word chunk dependency confirmed.")
    else:
        pr("  → Cross-word MI is NOT significantly above shuffle.")
        pr("    Observed MI may be driven by marginal frequency correlation.")
    pr()

    # Also compute null for NL syllables (one text only, for reference)
    pr("  NL syllable null model (Latin-Caesar only, for reference):")
    caesar_path = DATA_DIR / 'latin_texts' / 'caesar.txt'
    if caesar_path.exists():
        caesar_words = load_reference_text(caesar_path)
        caesar_syl_units = [syllabify_word(w) for w in caesar_words]
        caesar_syl_lines = nl_words_to_sentence_lines(caesar_syl_units, pseudo_line_len)
        null_caesar = null_model_cross_mi(caesar_syl_lines, 'syl', n_trials=50)
        caesar_syl_r = nl_syl_results.get('Latin-Caesar', {})
        if caesar_syl_r:
            obs_mi_c = caesar_syl_r['mi_cross']['mi']
            z_c_null = ((obs_mi_c - null_caesar['mi_mean']) / null_caesar['mi_std']
                        if null_caesar['mi_std'] > 1e-9 else float('nan'))
            pr(f"    Cross MI:  observed = {obs_mi_c:.4f},  "
               f"null = {null_caesar['mi_mean']:.4f} ± {null_caesar['mi_std']:.4f},  "
               f"z = {z_c_null:+.2f}")
    pr()

    # ── STEP 7: ROBUSTNESS CHECKS ────────────────────────────────────

    pr("─" * 76)
    pr("STEP 7: ROBUSTNESS CHECKS")
    pr("─" * 76)
    pr()

    # 7a: Exclude 1-chunk words — already done in cross_vms
    pr("  7a. EXCLUDING 1-CHUNK WORDS (already the default for cross_vms)")
    pr(f"      Cross pairs: {len(cross_vms)} (excludes 1-chunk words at boundary)")
    pr(f"      vs ALL pairs: {len(cross_all_vms)}")
    mi_cross_1ch = compute_mi_from_pairs(cross_1ch_vms, )
    pr(f"      MI from 1-chunk boundaries only: {mi_cross_1ch['mi']:.4f} "
       f"(NMI: {mi_cross_1ch['nmi']:.4f})")
    pr()

    # 7b: pseudo-line length sensitivity
    pr("  7b. PSEUDO-LINE LENGTH SENSITIVITY (NL)")
    pr("      Testing whether NL results depend on pseudo-line length choice.")
    for pll in [5, 8, 15, 50]:
        caesar_path = DATA_DIR / 'latin_texts' / 'caesar.txt'
        if not caesar_path.exists():
            continue
        c_words = load_reference_text(caesar_path)
        c_syl_units = [syllabify_word(w) for w in c_words]
        c_syl_lines_pll = nl_words_to_sentence_lines(c_syl_units, pll)
        cross_pll, within_pll, _ = extract_cross_and_within_pairs(c_syl_lines_pll, 'syl')
        mi_pll = compute_mi_from_pairs(cross_pll)
        pr(f"      Line len={pll:2d}: Cross MI={mi_pll['mi']:.4f}, "
           f"NMI={mi_pll['nmi']:.4f}, N={mi_pll['n_pairs']}")
    pr()

    # 7c: Section-level breakdown
    pr("  7c. VMS CROSS-WORD MI BY SECTION")
    section_pairs = defaultdict(list)
    for lid, section, words in vms_chunk_lines:
        for w_idx in range(len(words) - 1):
            word_units = words[w_idx]
            if len(word_units) >= 2:
                f_chunk = word_units[-1]
                i_chunk_next = words[w_idx + 1][0]
                section_pairs[section].append((f_chunk, i_chunk_next))

    pr(f"    {'Section':<14s}  {'N pairs':>7s}  {'MI':>7s}  {'NMI':>7s}  {'H(Y)red%':>8s}")
    pr(f"    {'─'*14}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*8}")
    for sec in sorted(section_pairs.keys()):
        pairs = section_pairs[sec]
        if len(pairs) < 50:
            continue
        r = compute_mi_from_pairs(pairs)
        pr(f"    {sec:<14s}  {r['n_pairs']:7d}  {r['mi']:7.4f}  "
           f"{r['nmi']:7.4f}  {r['reduction_pct']:7.2f}%")
    pr()

    # ── STEP 8: SKEPTICAL AUDIT ───────────────────────────────────────

    pr("─" * 76)
    pr("STEP 8: SKEPTICAL AUDIT")
    pr("─" * 76)
    pr()

    pr("  1. INVENTORY CONFOUND")
    pr("     F-chunks and I-chunks draw from largely disjoint types")
    pr("     (Phase 88: J(I,F)=0.241). Even random pairing of words")
    pr("     produces MI > 0 if the marginal F/I distributions are")
    pr("     non-uniform. The null model (word shuffle) controls this:")
    pr(f"     null MI = {null_vms['mi_mean']:.4f}, observed MI = {mi_cross_vms['mi']:.4f}.")
    if z_null_mi > 3:
        pr("     GENUINE excess above marginal frequency effect confirmed.")
    else:
        pr("     ⚠ Observed MI is close to shuffled baseline.")
        pr("     The dependency may be entirely from marginal distributions.")
    pr()

    pr("  2. GRAIN SIZE EFFECT")
    pr("     Chunks are coarser than glyphs (523 types vs ~26 glyph types).")
    pr("     Coarser grain → lower MI (information is averaged over slots).")
    pr("     NMI partially controls for this, but the comparison is still")
    pr("     approximate. The primary question is RELATIVE: VMS vs NL at")
    pr("     the same grain, not VMS chunks vs VMS glyphs.")
    pr()

    pr("  3. PSEUDO-LINE CONFOUND (NL only)")
    pr("     NL texts lack line boundaries. We use fixed-length pseudo-lines.")
    pr("     This means every NL pair is 'same sentence' (approximately),")
    pr("     while VMS pairs respect actual line breaks. This gives NL a")
    pr("     slight advantage (fewer random boundary pairs). The pseudo-line")
    pr("     length sensitivity check shows whether this matters.")
    pr()

    pr("  4. 1-CHUNK WORD AMBIGUITY")
    pr(f"     {n_1chunk} VMS words ({100*n_1chunk/n_words:.1f}%) are single-chunk.")
    pr("     Their F-chunk = I-chunk = the only chunk. When a 1-chunk word")
    pr("     is at position N, the 'cross-word' pair is (whole→I_{n+1}).")
    pr("     We exclude these from the primary analysis (cross_vms) but")
    pr("     include them in cross_all_vms for comparison.")
    pr()

    pr("  5. MULTIPLE TESTING")
    pr("     5 metrics × 2 comparisons = 10 tests.")
    pr("     Bonferroni threshold: |z| > 2.81 for α=0.05.")
    pr()

    BONF = 2.81  # for 10 tests

    pr("  6. FREQUENCY CONCENTRATION")
    pr(f"     Top-20 bigrams contribute {100*total_mi_from_top20/mi_cross_vms['mi']:.1f}% of total MI.")
    if total_mi_from_top20 / mi_cross_vms['mi'] > 0.5:
        pr("     ⚠ MI is concentrated in a few bigrams — not broadly distributed.")
        pr("     The signal may reflect a handful of formulaic patterns,")
        pr("     not general syntactic dependency.")
    else:
        pr("     MI is broadly distributed — consistent with general dependency.")
    pr()

    # ── STEP 9: SYNTHESIS & VERDICT ──────────────────────────────────

    pr("─" * 76)
    pr("STEP 9: SYNTHESIS & VERDICT")
    pr("─" * 76)
    pr()

    pr("  SUMMARY TABLE — CROSS-WORD CHUNK MI")
    pr()
    pr(f"    {'Metric':<18s}  {'VMS':>8s}  {'NL-char μ':>10s}  {'z(char)':>8s}  "
       f"{'NL-syl μ':>10s}  {'z(syl)':>8s}")
    pr(f"    {'─'*18}  {'─'*8}  {'─'*10}  {'─'*8}  {'─'*10}  {'─'*8}")

    for label, fn in metrics:
        vms_val = fn({'mi_cross': mi_cross_vms, 'mi_within': mi_within_vms,
                      'ratio': ratio_vms})
        mc, sc, zc = z_score(vms_val, nl_char_results, fn)
        ms, ss, zs = z_score(vms_val, nl_syl_results, fn)

        def fmt(v):
            return f"{v:8.4f}" if not math.isnan(v) else "     N/A"
        def fmtz(v):
            return f"{v:+8.2f}" if not math.isnan(v) else "     N/A"

        mc_s = f"{mc:.4f}" if not math.isnan(mc) else "N/A"
        ms_s = f"{ms:.4f}" if not math.isnan(ms) else "N/A"
        pr(f"    {label:<18s}  {fmt(vms_val)}  {mc_s:>10s}  {fmtz(zc)}  "
           f"{ms_s:>10s}  {fmtz(zs)}")
    pr()

    # Directional count
    z_chars_list = [z_chars_all[k] for k in z_chars_all if not math.isnan(z_chars_all[k])]
    z_syls_list = [z_syls_all[k] for k in z_syls_all if not math.isnan(z_syls_all[k])]

    # For cross-word: HIGHER MI/NMI = MORE dependency = anomalous if VMS > NL
    # HIGHER ratio = LESS boundary attenuation = anomalous
    # So for all metrics, positive z = VMS has more cross-word dependency

    n_sig_char_high = sum(1 for z in z_chars_list if z > BONF)
    n_sig_char_low = sum(1 for z in z_chars_list if z < -BONF)
    n_sig_char_ns = sum(1 for z in z_chars_list if abs(z) <= BONF)

    n_sig_syl_high = sum(1 for z in z_syls_list if z > BONF)
    n_sig_syl_low = sum(1 for z in z_syls_list if z < -BONF)
    n_sig_syl_ns = sum(1 for z in z_syls_list if abs(z) <= BONF)

    pr(f"  DIRECTIONAL EVIDENCE (Bonferroni |z| > {BONF}):")
    pr(f"    vs NL chars:  {n_sig_char_high} ANOMALOUS-HIGH, "
       f"{n_sig_char_low} LOW, {n_sig_char_ns} ambiguous")
    pr(f"    vs NL syls:   {n_sig_syl_high} ANOMALOUS-HIGH, "
       f"{n_sig_syl_low} LOW, {n_sig_syl_ns} ambiguous")
    pr()

    # Null model summary
    pr("  NULL MODEL SUMMARY:")
    pr(f"    VMS word-order shuffle: z(MI) = {z_null_mi:+.2f}")
    genuine_dependency = z_null_mi > 3
    if genuine_dependency:
        pr("    → GENUINE cross-word dependency (exceeds shuffled baseline)")
    else:
        pr("    → NO genuine dependency (explained by marginal frequencies)")
    pr()

    # Determine verdict
    pr("  ══════════════════════════════════════════════════════════")
    pr("  VERDICT")
    pr("  ══════════════════════════════════════════════════════════")
    pr()

    mean_z_char = float(np.mean(z_chars_list)) if z_chars_list else float('nan')
    mean_z_syl = float(np.mean(z_syls_list)) if z_syls_list else float('nan')

    pr(f"  Mean z-score vs NL characters: {mean_z_char:+.2f}" if not math.isnan(mean_z_char)
       else "  Mean z-score vs NL characters: N/A")
    pr(f"  Mean z-score vs NL syllables:  {mean_z_syl:+.2f}" if not math.isnan(mean_z_syl)
       else "  Mean z-score vs NL syllables:  N/A")
    pr()

    if not genuine_dependency:
        verdict = "CROSS_WORD_MI_NOT_GENUINE"
        pr("  ★ Cross-word chunk MI is NOT significantly above word-order shuffle.")
        pr("    The glyph-level anomaly (Phase 62: NMI=0.080) does NOT persist")
        pr("    at chunk level. The observed MI is driven by marginal frequency")
        pr("    correlation (F-chunks and I-chunks have fixed distributions).")
        pr("    → Glyph-level anomaly may have been a unit-of-analysis artifact.")
    elif not math.isnan(mean_z_syl) and abs(mean_z_syl) < 2.0:
        verdict = "CROSS_WORD_MI_NL_SYLLABLE_CONSISTENT"
        pr("  ★ Cross-word chunk MI is genuine (above shuffle) but SIMILAR to")
        pr("    NL syllable baselines.")
        pr("    → The chunk-level cross-word dependency is NORMAL for sub-word units.")
        pr("    → No anomaly when compared at the correct grain.")
        pr("    → The glyph-level anomaly (Phase 62) was likely a grain-size artifact:")
        pr("      glyphs are finer than functional units → inter-word MI was inflated")
        pr("      by sub-glyph positional correlations.")
    elif not math.isnan(mean_z_syl) and mean_z_syl > 2.0:
        verdict = "CROSS_WORD_MI_ANOMALOUS"
        pr("  ★ Cross-word chunk MI is genuine AND exceeds NL syllable baselines.")
        pr("    → The cross-word anomaly persists at chunk level.")
        pr("    → VMS has genuinely stronger inter-word sub-word dependency than NL.")
        pr("    → This is consistent with a cipher or generation mechanism that")
        pr("      operates across word boundaries.")
    elif not math.isnan(mean_z_syl) and mean_z_syl < -2.0:
        verdict = "CROSS_WORD_MI_BELOW_NL"
        pr("  ★ Cross-word chunk MI is genuine but BELOW NL syllable baselines.")
        pr("    → VMS word boundaries attenuate dependencies MORE than NL.")
        pr("    → Strong word-boundary effect — consistent with NL-like syntax.")
    else:
        verdict = "INCONCLUSIVE"
        pr("  ★ Insufficient data for reliable verdict.")
    pr()

    # Confidence updates
    pr("  REVISED CONFIDENCES (Phase 90):")
    if verdict == "CROSS_WORD_MI_NL_SYLLABLE_CONSISTENT":
        pr("  - Natural language: 87% → 88% (UP — cross-word behavior is NL-normal)")
        pr("  - Positional verbose cipher: 50% → 45% (DOWN — no cross-word anomaly)")
        pr("  - All others unchanged")
    elif verdict == "CROSS_WORD_MI_ANOMALOUS":
        pr("  - Natural language: 87% → 85% (DOWN — anomalous cross-word structure)")
        pr("  - Positional verbose cipher: 50% → 55% (UP — cross-boundary mechanism)")
        pr("  - All others unchanged")
    elif verdict == "CROSS_WORD_MI_BELOW_NL":
        pr("  - Natural language: 87% → 89% (UP — strong word-boundary effect)")
        pr("  - Positional verbose cipher: 50% → 45% (DOWN)")
        pr("  - All others unchanged")
    elif verdict == "CROSS_WORD_MI_NOT_GENUINE":
        pr("  - Natural language: 87% → 87% (unchanged — null result)")
        pr("  - Positional verbose cipher: 50% → 50% (unchanged)")
        pr("  - Phase 62 glyph-level anomaly: NEEDS REVALIDATION at chunk level")
    else:
        pr("  - All confidences unchanged (inconclusive)")
    pr()

    # ── SAVE RESULTS ──────────────────────────────────────────────────

    out_txt = RESULTS_DIR / 'phase90_crossword_chunk_mi.txt'
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Results saved to {out_txt}")

    # JSON
    json_data = {
        'phase': 90,
        'question': 'Cross-word chunk MI: does glyph-level anomaly persist?',
        'vms_cross_mi': mi_cross_vms['mi'],
        'vms_cross_nmi': mi_cross_vms['nmi'],
        'vms_within_mi': mi_within_vms['mi'],
        'vms_within_nmi': mi_within_vms['nmi'],
        'vms_ratio': ratio_vms,
        'vms_cross_h_y_reduction': mi_cross_vms['reduction_pct'],
        'vms_cross_n_pairs': mi_cross_vms['n_pairs'],
        'null_model': {
            'mi_mean': null_vms['mi_mean'], 'mi_std': null_vms['mi_std'],
            'z_mi': z_null_mi,
            'nmi_mean': null_vms['nmi_mean'], 'nmi_std': null_vms['nmi_std'],
            'z_nmi': z_null_nmi,
        },
        'zscores_vs_char': {k: z_chars_all[k] for k in z_chars_all},
        'zscores_vs_syl': {k: z_syls_all[k] for k in z_syls_all},
        'mean_z_char': mean_z_char,
        'mean_z_syl': mean_z_syl,
        'nl_char_baselines': {
            name: {
                'cross_mi': r['mi_cross']['mi'],
                'cross_nmi': r['mi_cross']['nmi'],
                'within_mi': r['mi_within']['mi'],
                'ratio': r['ratio'],
                'reduction_pct': r['mi_cross']['reduction_pct'],
            }
            for name, r in nl_char_results.items()
        },
        'nl_syl_baselines': {
            name: {
                'cross_mi': r['mi_cross']['mi'],
                'cross_nmi': r['mi_cross']['nmi'],
                'within_mi': r['mi_within']['mi'],
                'ratio': r['ratio'],
                'reduction_pct': r['mi_cross']['reduction_pct'],
            }
            for name, r in nl_syl_results.items()
        },
        'mi_concentration_top20_pct': 100 * total_mi_from_top20 / mi_cross_vms['mi']
            if mi_cross_vms['mi'] > 1e-9 else float('nan'),
        'verdict': verdict,
    }

    out_json = RESULTS_DIR / 'phase90_crossword_chunk_mi.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, default=str)
    pr(f"  JSON saved to {out_json}")


if __name__ == '__main__':
    main()
