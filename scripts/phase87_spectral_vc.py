#!/usr/bin/env python3
"""
Phase 87 — Vowel-Consonant Spectral Separation

═══════════════════════════════════════════════════════════════════════

MOTIVATION:

  86 phases have established that VMS chunks are functional characters
  (~25 equivalence classes) with genuine distributional structure.
  But all evidence so far is STATISTICAL — matching distributions,
  h_ratios, Zipf slopes. None of it tests a specifically LINGUISTIC
  prediction.

  In every known alphabetic writing system encoding a natural language,
  characters split into two groups — vowels (~20%) and consonants (~80%)
  — with characteristic alternation patterns (CV, CVC, CVCC...). This
  creates a strong signature in the bigram transition matrix: the SECOND
  EIGENVECTOR of the row-normalized transition matrix separates V from C.

  This is a BINARY, FALSIFIABLE prediction:
  - If VMS chunks encode NL characters → spectral V/C split should appear
  - If VMS is a cipher/hoax/non-alphabetic → no clean spectral split

  CRITICAL ADVANTAGE: This doesn't require knowing the language or the
  cipher. V/C alternation is a UNIVERSAL property of all known languages
  written alphabetically.

APPROACH:
  1. Build chunk-chunk bigram transition matrix (within-word, top N chunks)
  2. Eigendecompose; examine 2nd eigenvector for binary split
  3. Measure spectral gap (λ1 − |λ2|) and split ratio
  4. NL CHARACTER BASELINE: Latin, Italian, English, French (SHOULD split)
  5. NL SYLLABLE CONTROL: same languages at syllable level (should NOT
     split cleanly — syllables already contain V+C internally)
  6. NULL MODELS:
     a) Row-permuted matrix (destroy row structure, keep marginals)
     b) Frequency-preserving shuffle (keep unigram distribution)
  7. Currier A vs B: same V/C assignment in both sublanguages?
  8. Stability: does split change with top-50 vs top-80 vs top-100?

SKEPTICAL CONCERNS:
  - Within-word bigrams are limited (38K). May be too sparse for rare chunks.
  - LOOP grammar's slot structure may create an artificial alternation
    pattern that mimics V/C but has nothing to do with language.
  - The "V/C" interpretation assumes alphabetic encoding. If VMS uses
    a syllabary, abjad, or non-linguistic system, no V/C split is expected.
  - Must distinguish between "any binary split" (trivial) and "a V/C split
    specifically" (requires correct ratio and alternation pattern).
  - Must test whether the WORD-POSITION effect from Phase 86 (chunks
    cluster by initial/medial/final) masquerades as a V/C split.
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import chunk_to_str, clean_word, eva_to_glyphs, extract_words_from_line, get_currier_language, load_reference_text, parse_one_chunk, parse_word_into_chunks

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
# EVA TOKENIZER + LOOP GRAMMAR (from Phase 85/86)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']


SLOT1 = {'ch', 'sh', 'y'}
SLOT2_RUNS = {'e'}; SLOT2_SINGLE = {'q', 'a'}
SLOT3 = {'o'}
SLOT4_RUNS = {'i'}; SLOT4_SINGLE = {'d'}
SLOT5 = {'y', 'p', 'f', 'k', 'l', 'r', 's', 't',
         'cth', 'ckh', 'cph', 'cfh', 'n', 'm'}
MAX_CHUNKS = 6





# ═══════════════════════════════════════════════════════════════════════
# VMS PARSING (from Phase 85/86)
# ═══════════════════════════════════════════════════════════════════════




def parse_vms_with_currier():
    """Parse VMS folios. Returns dict with keys: 'all', 'A', 'B'.
    Each value is list of word-chunk-lists."""
    result = defaultdict(list)
    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)
    for filepath in folio_files:
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num: continue
        fnum = int(m_num.group(1))
        currier = get_currier_language(fnum)
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line: continue
                m = re.match(r'<([^>]+)>', line)
                if not m: continue
                rest = line[m.end():].strip()
                if not rest: continue
                words = extract_words_from_line(rest)
                for w in words:
                    chunks, unparsed, glyphs = parse_word_into_chunks(w)
                    chunk_ids = [chunk_to_str(c) for c in chunks]
                    if chunk_ids:
                        result['all'].append(chunk_ids)
                        result[currier].append(chunk_ids)
    return dict(result)


# ═══════════════════════════════════════════════════════════════════════
# NL TEXT LOADING + SYLLABIFICATION (from Phase 85/86)
# ═══════════════════════════════════════════════════════════════════════

VOWELS_LATIN = set('aeiouyàáâãäåæèéêëìíîïòóôõöùúûüýœ')

def syllabify_word(word, vowels=VOWELS_LATIN):
    if len(word) <= 1: return [word]
    is_v = [c in vowels for c in word]
    boundaries = [0]; i = 1
    while i < len(word):
        if is_v[i] and i > 0 and not is_v[i-1]:
            j = i - 1
            while j > boundaries[-1] and not is_v[j]: j -= 1
            if j > boundaries[-1]: split_at = j + 1
            else: split_at = j if is_v[j] else j + 1
            if split_at > boundaries[-1] and split_at < i:
                boundaries.append(split_at)
        i += 1
    syllables = []
    for k in range(len(boundaries)):
        start = boundaries[k]
        end = boundaries[k+1] if k+1 < len(boundaries) else len(word)
        syl = word[start:end]
        if syl: syllables.append(syl)
    return syllables if syllables else [word]



# ═══════════════════════════════════════════════════════════════════════
# SPECTRAL ANALYSIS CORE
# ═══════════════════════════════════════════════════════════════════════

def build_transition_matrix(word_unit_seqs, top_n=50, min_freq=10):
    """Build bigram transition matrix from within-word unit sequences.

    Args:
        word_unit_seqs: list of lists (each inner list = unit IDs for one word)
        top_n: include only top-N most frequent units
        min_freq: minimum frequency to be included

    Returns:
        symbols: list of unit IDs (length N ≤ top_n)
        T_raw: NxN count matrix
        T_norm: NxN row-normalized probability matrix
        bigram_total: total bigram count used
    """
    # Count unigrams
    unit_counts = Counter()
    for seq in word_unit_seqs:
        for u in seq:
            unit_counts[u] += 1

    # Select top_n that also meet min_freq
    symbols = [u for u, _ in unit_counts.most_common()
               if unit_counts[u] >= min_freq][:top_n]
    sym_set = set(symbols)
    sym_idx = {s: i for i, s in enumerate(symbols)}
    N = len(symbols)

    # Count within-word bigrams
    T_raw = np.zeros((N, N), dtype=float)
    bigram_total = 0
    for seq in word_unit_seqs:
        for i in range(len(seq) - 1):
            a, b = seq[i], seq[i+1]
            if a in sym_idx and b in sym_idx:
                T_raw[sym_idx[a], sym_idx[b]] += 1
                bigram_total += 1

    # Row-normalize
    row_sums = T_raw.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    T_norm = T_raw / row_sums

    return symbols, T_raw, T_norm, bigram_total


def spectral_vc_analysis(symbols, T_norm, T_raw, label="", known_vowels=None):
    """Perform spectral V/C analysis on a transition matrix.

    Returns dict with eigenvalues, eigenvector groups, spectral gap,
    V/C purity score (if known_vowels provided), group sizes, etc.
    """
    N = len(symbols)
    if N < 5:
        return None

    # Eigendecompose the TRANSPOSE (gives left eigenvectors as columns)
    eigenvalues, eigenvectors = np.linalg.eig(T_norm.T)

    # Sort by eigenvalue magnitude (descending)
    order = np.argsort(-np.abs(eigenvalues))
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    # 2nd eigenvector (real part) — the V/C separator
    v2 = eigenvectors[:, 1].real

    # Spectral gap
    gap = abs(eigenvalues[0].real) - abs(eigenvalues[1].real)

    # Split into positive and negative groups
    pos_group = [symbols[i] for i in range(N) if v2[i] > 0]
    neg_group = [symbols[i] for i in range(N) if v2[i] <= 0]

    # Determine which is the smaller group (expected to be "vowels")
    if len(pos_group) <= len(neg_group):
        small_group, large_group = pos_group, neg_group
        small_label, large_label = "V-candidate", "C-candidate"
    else:
        small_group, large_group = neg_group, pos_group
        small_label, large_label = "V-candidate", "C-candidate"

    # Group ratio
    small_ratio = len(small_group) / N if N > 0 else 0

    # Purity (if known vowels provided)
    purity = None
    if known_vowels:
        # How well does the small group match known vowels?
        v_symbols = set(s for s in symbols if s in known_vowels)
        v_in_small = len(set(small_group) & v_symbols)
        v_in_large = len(set(large_group) & v_symbols)
        # Also check if the LARGE group is a better vowel match
        purity_small = v_in_small / len(v_symbols) if v_symbols else 0
        purity_large = v_in_large / len(v_symbols) if v_symbols else 0
        purity = max(purity_small, purity_large)

    # Alternation test: how often do consecutive units cross the V/C boundary?
    # In NL, we expect high alternation (~60-80% of bigrams are CV or VC)
    pos_set = set(pos_group)
    neg_set = set(neg_group)
    sym_idx = {s: i for i, s in enumerate(symbols)}
    cross_count = 0
    total_counted = 0
    for i in range(N):
        for j in range(N):
            ct = T_raw[i, j]
            if ct > 0:
                si_pos = symbols[i] in pos_set
                sj_pos = symbols[j] in pos_set
                if si_pos != sj_pos:
                    cross_count += ct
                total_counted += ct
    alternation_rate = cross_count / total_counted if total_counted > 0 else 0

    # Weight concentration: what fraction of transition WEIGHT crosses?
    # For a true V/C language, this should be 60-80%

    # Ranked 2nd eigenvector
    ranked = sorted(range(N), key=lambda i: v2[i])
    v2_ranked = [(symbols[i], v2[i]) for i in ranked]

    return {
        'label': label,
        'n_symbols': N,
        'eigenvalues_top5': [float(e.real) for e in eigenvalues[:5]],
        'spectral_gap': float(gap),
        'lambda2': float(eigenvalues[1].real),
        'v2_ranked': v2_ranked,
        'small_group': small_group,
        'large_group': large_group,
        'small_ratio': float(small_ratio),
        'alternation_rate': float(alternation_rate),
        'purity': purity,
    }


# ═══════════════════════════════════════════════════════════════════════
# NULL MODELS
# ═══════════════════════════════════════════════════════════════════════

def null_model_row_permuted(T_raw, n_trials=100):
    """Permute rows of T_raw, re-normalize, compute spectral gap and alternation."""
    N = T_raw.shape[0]
    gaps = []
    alts = []
    for _ in range(n_trials):
        perm = np.random.permutation(N)
        T_perm = T_raw[perm, :]
        row_sums = T_perm.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        T_norm_perm = T_perm / row_sums
        evals, evecs = np.linalg.eig(T_norm_perm.T)
        order = np.argsort(-np.abs(evals))
        evals = evals[order]
        gap = abs(evals[0].real) - abs(evals[1].real)
        gaps.append(gap)

        # Alternation from 2nd eigenvector
        v2 = evecs[:, order[1]].real
        pos_set = set(i for i in range(N) if v2[i] > 0)
        cross_ct = 0; total_ct = 0
        for i in range(N):
            for j in range(N):
                ct = T_raw[i, j]
                if ct > 0:
                    if (i in pos_set) != (j in pos_set):
                        cross_ct += ct
                    total_ct += ct
        alts.append(cross_ct / total_ct if total_ct > 0 else 0)

    return {
        'gap_mean': float(np.mean(gaps)),
        'gap_std': float(np.std(gaps)),
        'alt_mean': float(np.mean(alts)),
        'alt_std': float(np.std(alts)),
    }


def null_model_shuffled_bigrams(word_unit_seqs, symbols, n_trials=50, top_n=50):
    """Shuffle chunk assignments within words, rebuild matrix, measure gap."""
    sym_idx = {s: i for i, s in enumerate(symbols)}
    N = len(symbols)
    gaps = []
    alts = []

    for trial in range(n_trials):
        rng = np.random.RandomState(42 + trial)
        T_shuf = np.zeros((N, N), dtype=float)
        for seq in word_unit_seqs:
            # Shuffle the units within each word
            shuf_seq = list(seq)
            rng.shuffle(shuf_seq)
            for i in range(len(shuf_seq) - 1):
                a, b = shuf_seq[i], shuf_seq[i+1]
                if a in sym_idx and b in sym_idx:
                    T_shuf[sym_idx[a], sym_idx[b]] += 1

        row_sums = T_shuf.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        T_norm_shuf = T_shuf / row_sums
        evals, evecs = np.linalg.eig(T_norm_shuf.T)
        order = np.argsort(-np.abs(evals))
        evals = evals[order]
        gap = abs(evals[0].real) - abs(evals[1].real)
        gaps.append(gap)

        v2 = evecs[:, order[1]].real
        pos_set = set(i for i in range(N) if v2[i] > 0)
        cross_ct = 0; total_ct = 0
        for i in range(N):
            for j in range(N):
                ct = T_shuf[i, j]
                if ct > 0:
                    if (i in pos_set) != (j in pos_set):
                        cross_ct += ct
                    total_ct += ct
        alts.append(cross_ct / total_ct if total_ct > 0 else 0)

    return {
        'gap_mean': float(np.mean(gaps)),
        'gap_std': float(np.std(gaps)),
        'alt_mean': float(np.mean(alts)),
        'alt_std': float(np.std(alts)),
    }


# ═══════════════════════════════════════════════════════════════════════
# NL CHARACTER-LEVEL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def nl_character_spectral(name, words, known_vowels, top_n=30):
    """Build character bigrams from words and run spectral analysis."""
    # Build word-level char sequences
    word_char_seqs = [[c for c in w] for w in words if len(w) >= 2]
    symbols, T_raw, T_norm, n_bigrams = build_transition_matrix(
        word_char_seqs, top_n=top_n, min_freq=10)
    result = spectral_vc_analysis(symbols, T_norm, T_raw,
                                   label=name, known_vowels=known_vowels)
    if result:
        result['n_bigrams'] = n_bigrams
    return result


def nl_syllable_spectral(name, words, top_n=50):
    """Build syllable bigrams from words and run spectral analysis."""
    word_syl_seqs = [syllabify_word(w) for w in words if len(w) >= 2]
    # Filter to words with ≥2 syllables
    word_syl_seqs = [s for s in word_syl_seqs if len(s) >= 2]
    symbols, T_raw, T_norm, n_bigrams = build_transition_matrix(
        word_syl_seqs, top_n=top_n, min_freq=10)
    result = spectral_vc_analysis(symbols, T_norm, T_raw, label=name + " (syllables)")
    if result:
        result['n_bigrams'] = n_bigrams
    return result


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 76)
    pr("PHASE 87 — VOWEL-CONSONANT SPECTRAL SEPARATION")
    pr("=" * 76)
    pr()
    pr("  Does the VMS chunk-to-chunk transition matrix reveal a vowel/")
    pr("  consonant split? This tests a specifically LINGUISTIC prediction:")
    pr("  if chunks encode alphabetic characters, the 2nd eigenvector of")
    pr("  the bigram matrix should separate V-like from C-like chunks.")
    pr()

    # ── STEP 1: PARSE VMS INTO CHUNKS ──────────────────────────────────

    pr("─" * 76)
    pr("STEP 1: PARSE VMS & BUILD CHUNK BIGRAM MATRIX")
    pr("─" * 76)
    pr()

    vms_data = parse_vms_with_currier()
    all_word_chunks = vms_data['all']

    pr(f"  Total words: {len(all_word_chunks)}")
    n_multi = sum(1 for wc in all_word_chunks if len(wc) >= 2)
    pr(f"  Words with ≥2 chunks: {n_multi} ({100*n_multi/len(all_word_chunks):.1f}%)")

    # Build transition matrix with top 50 chunks
    TOP_N = 50
    symbols, T_raw, T_norm, n_bigrams = build_transition_matrix(
        all_word_chunks, top_n=TOP_N, min_freq=10)
    pr(f"  Matrix size: {len(symbols)} × {len(symbols)}")
    pr(f"  Within-word bigrams used: {n_bigrams}")

    # Check matrix density
    nonzero = np.count_nonzero(T_raw)
    total_cells = len(symbols) ** 2
    pr(f"  Matrix density: {nonzero}/{total_cells} = {100*nonzero/total_cells:.1f}%")
    pr()

    # ── STEP 2: VMS SPECTRAL ANALYSIS ─────────────────────────────────

    pr("─" * 76)
    pr("STEP 2: VMS CHUNK SPECTRAL ANALYSIS")
    pr("─" * 76)
    pr()

    vms_result = spectral_vc_analysis(symbols, T_norm, T_raw, label="VMS chunks")

    pr(f"  Eigenvalues (top 5): {', '.join(f'{e:.4f}' for e in vms_result['eigenvalues_top5'])}")
    pr(f"  Spectral gap (λ1 − |λ2|): {vms_result['spectral_gap']:.4f}")
    pr(f"  |λ2|: {abs(vms_result['lambda2']):.4f}")
    pr()

    pr(f"  V/C split: {len(vms_result['small_group'])} small / "
       f"{len(vms_result['large_group'])} large "
       f"({100*vms_result['small_ratio']:.0f}% / "
       f"{100*(1-vms_result['small_ratio']):.0f}%)")
    pr(f"  Alternation rate: {100*vms_result['alternation_rate']:.1f}%")
    pr()

    # Show the ranked 2nd eigenvector
    pr("  2nd eigenvector ranking (V/C separator):")
    pr(f"    {'Chunk':>20s}  {'v2 score':>9s}  {'Group':>12s}")
    pr(f"    {'─'*20}  {'─'*9}  {'─'*12}")
    small_set = set(vms_result['small_group'])
    for sym, score in vms_result['v2_ranked']:
        group = "V-candidate" if sym in small_set else "C-candidate"
        pr(f"    {sym:>20s}  {score:+9.4f}  {group:>12s}")
    pr()

    # ── STEP 3: NL CHARACTER BASELINES ────────────────────────────────

    pr("─" * 76)
    pr("STEP 3: NL CHARACTER BASELINES — DO REAL ALPHABETS SHOW V/C SPLIT?")
    pr("─" * 76)
    pr()

    LATIN_VOWELS = set('aeiouy')
    ITALIAN_VOWELS = set('aeiou')
    ENGLISH_VOWELS = set('aeiouy')
    FRENCH_VOWELS = set('aeiouy')

    ref_configs = [
        ('Latin-Caesar', DATA_DIR / 'latin_texts' / 'caesar.txt', LATIN_VOWELS),
        ('Italian-Cucina', DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt', ITALIAN_VOWELS),
        ('English-Cury', DATA_DIR / 'vernacular_texts' / 'english_cury.txt', ENGLISH_VOWELS),
        ('French-Viandier', DATA_DIR / 'vernacular_texts' / 'french_viandier.txt', FRENCH_VOWELS),
    ]

    nl_char_results = {}
    for name, fpath, vowels in ref_configs:
        if not fpath.exists():
            pr(f"  {name}: file not found, skipping")
            continue
        words = load_reference_text(fpath)
        if len(words) < 500:
            pr(f"  {name}: too few words, skipping")
            continue

        result = nl_character_spectral(name, words, vowels, top_n=30)
        if result:
            nl_char_results[name] = result
            pr(f"  {name}:")
            pr(f"    Symbols: {result['n_symbols']}, "
               f"Bigrams: {result['n_bigrams']}")
            pr(f"    Spectral gap: {result['spectral_gap']:.4f}, "
               f"|λ2|: {abs(result['lambda2']):.4f}")
            pr(f"    V/C split: {len(result['small_group'])} / "
               f"{len(result['large_group'])} "
               f"({100*result['small_ratio']:.0f}% / "
               f"{100*(1-result['small_ratio']):.0f}%)")
            pr(f"    V/C purity: {100*result['purity']:.0f}%")
            pr(f"    Alternation rate: {100*result['alternation_rate']:.1f}%")
            pr(f"    Small (V-candidate): {sorted(result['small_group'])}")
            pr()

    # Summary table
    pr("  Summary:")
    pr(f"  {'Text':>18s}  {'Gap':>6s}  {'|λ2|':>6s}  {'V-ratio':>8s}  "
       f"{'Purity':>7s}  {'Alt%':>5s}")
    pr(f"  {'─'*18}  {'─'*6}  {'─'*6}  {'─'*8}  {'─'*7}  {'─'*5}")
    for name, r in nl_char_results.items():
        pr(f"  {name:>18s}  {r['spectral_gap']:6.4f}  {abs(r['lambda2']):6.4f}  "
           f"{r['small_ratio']:8.2f}  {100*r['purity']:6.0f}%  "
           f"{100*r['alternation_rate']:5.1f}")
    pr(f"  {'VMS chunks':>18s}  {vms_result['spectral_gap']:6.4f}  "
       f"{abs(vms_result['lambda2']):6.4f}  "
       f"{vms_result['small_ratio']:8.2f}  {'  N/A':>7s}  "
       f"{100*vms_result['alternation_rate']:5.1f}")
    pr()

    # ── STEP 4: NL SYLLABLE CONTROL ──────────────────────────────────

    pr("─" * 76)
    pr("STEP 4: NL SYLLABLE CONTROL — SYLLABLES SHOULD NOT SPLIT CLEANLY")
    pr("─" * 76)
    pr()
    pr("  If the method is valid, NL syllable bigrams should NOT produce")
    pr("  a clean V/C split — syllables already contain both V and C.")
    pr()

    nl_syl_results = {}
    for name, fpath, _ in ref_configs:
        if not fpath.exists(): continue
        words = load_reference_text(fpath)
        if len(words) < 500: continue

        result = nl_syllable_spectral(name, words, top_n=50)
        if result:
            nl_syl_results[name] = result
            pr(f"  {name} syllables:")
            pr(f"    Symbols: {result['n_symbols']}, "
               f"Bigrams: {result['n_bigrams']}")
            pr(f"    Spectral gap: {result['spectral_gap']:.4f}, "
               f"|λ2|: {abs(result['lambda2']):.4f}")
            pr(f"    Split: {len(result['small_group'])} / "
               f"{len(result['large_group'])} "
               f"({100*result['small_ratio']:.0f}% / "
               f"{100*(1-result['small_ratio']):.0f}%)")
            pr(f"    Alternation: {100*result['alternation_rate']:.1f}%")
            pr()

    pr()

    # ── STEP 5: NULL MODELS ───────────────────────────────────────────

    pr("─" * 76)
    pr("STEP 5: NULL MODELS — IS THE VMS SPECTRAL GAP SIGNIFICANT?")
    pr("─" * 76)
    pr()

    pr("  NULL 1: Row-permuted matrix (destroys row identity, keeps marginals)")
    null1 = null_model_row_permuted(T_raw, n_trials=100)
    z_gap_1 = ((vms_result['spectral_gap'] - null1['gap_mean']) / null1['gap_std']
               if null1['gap_std'] > 1e-10 else float('inf'))
    pr(f"    VMS gap: {vms_result['spectral_gap']:.4f}")
    pr(f"    Null gap: {null1['gap_mean']:.4f} ± {null1['gap_std']:.4f}")
    pr(f"    z-score: {z_gap_1:.2f}")
    z_alt_1 = ((vms_result['alternation_rate'] - null1['alt_mean']) / null1['alt_std']
               if null1['alt_std'] > 1e-10 else float('inf'))
    pr(f"    VMS alternation: {100*vms_result['alternation_rate']:.1f}%")
    pr(f"    Null alternation: {100*null1['alt_mean']:.1f}% ± {100*null1['alt_std']:.1f}%")
    pr(f"    z-score: {z_alt_1:.2f}")
    pr()

    pr("  NULL 2: Within-word chunk shuffle (destroys ordering, keeps word composition)")
    null2 = null_model_shuffled_bigrams(all_word_chunks, symbols, n_trials=50, top_n=TOP_N)
    z_gap_2 = ((vms_result['spectral_gap'] - null2['gap_mean']) / null2['gap_std']
               if null2['gap_std'] > 1e-10 else float('inf'))
    pr(f"    VMS gap: {vms_result['spectral_gap']:.4f}")
    pr(f"    Null gap: {null2['gap_mean']:.4f} ± {null2['gap_std']:.4f}")
    pr(f"    z-score: {z_gap_2:.2f}")
    z_alt_2 = ((vms_result['alternation_rate'] - null2['alt_mean']) / null2['alt_std']
               if null2['alt_std'] > 1e-10 else float('inf'))
    pr(f"    VMS alternation: {100*vms_result['alternation_rate']:.1f}%")
    pr(f"    Null alternation: {100*null2['alt_mean']:.1f}% ± {100*null2['alt_std']:.1f}%")
    pr(f"    z-score: {z_alt_2:.2f}")
    pr()

    # ── STEP 6: CURRIER A vs B CROSS-VALIDATION ──────────────────────

    pr("─" * 76)
    pr("STEP 6: CURRIER A vs B — SAME V/C ASSIGNMENT?")
    pr("─" * 76)
    pr()
    pr("  If the V/C split is linguistic, the same chunks should be")
    pr("  classified as V/C in both Currier sublanguages.")
    pr()

    currier_results = {}
    for lang_key in ['A', 'B']:
        word_chunks = vms_data.get(lang_key, [])
        if len(word_chunks) < 500:
            pr(f"  Currier {lang_key}: too few words ({len(word_chunks)}), skipping")
            continue

        syms_ab, T_raw_ab, T_norm_ab, n_bi_ab = build_transition_matrix(
            word_chunks, top_n=TOP_N, min_freq=5)
        res_ab = spectral_vc_analysis(syms_ab, T_norm_ab, T_raw_ab,
                                       label=f"Currier {lang_key}")
        if res_ab:
            currier_results[lang_key] = res_ab
            pr(f"  Currier {lang_key}:")
            pr(f"    Symbols: {res_ab['n_symbols']}, Bigrams: {n_bi_ab}")
            pr(f"    Spectral gap: {res_ab['spectral_gap']:.4f}")
            pr(f"    V-candidate: {sorted(res_ab['small_group'][:15])}")
            pr(f"    Alternation: {100*res_ab['alternation_rate']:.1f}%")
            pr()

    # Compare A vs B assignments
    if 'A' in currier_results and 'B' in currier_results:
        a_small = set(currier_results['A']['small_group'])
        b_small = set(currier_results['B']['small_group'])
        # Also try flipped B (in case eigenvector sign flips)
        b_large = set(currier_results['B']['large_group'])

        overlap_same = len(a_small & b_small)
        overlap_flip = len(a_small & b_large)
        common = a_small | b_small  # all chunks in either small group
        # Use the larger overlap
        if overlap_flip > overlap_same:
            # Sign flip: B's "small" = A's "large"
            best_overlap = overlap_flip
            b_comparable = b_large
            flip_note = "(eigenvector sign flipped in B)"
        else:
            best_overlap = overlap_same
            b_comparable = b_small
            flip_note = "(same sign)"

        # Jaccard similarity
        union_size = len(a_small | b_comparable)
        jaccard = best_overlap / union_size if union_size > 0 else 0

        pr(f"  A vs B comparison {flip_note}:")
        pr(f"    A V-candidates: {len(a_small)} chunks")
        pr(f"    B V-candidates: {len(b_comparable)} chunks")
        pr(f"    Overlap: {best_overlap} chunks")
        pr(f"    Jaccard similarity: {jaccard:.3f}")
        pr(f"    Shared V-candidates: {sorted(a_small & b_comparable)}")
    pr()

    # ── STEP 7: STABILITY — DIFFERENT TOP-N VALUES ───────────────────

    pr("─" * 76)
    pr("STEP 7: STABILITY — DOES SPLIT CHANGE WITH TOP-N?")
    pr("─" * 76)
    pr()

    stability_results = {}
    for tn in [30, 40, 50, 60, 80, 100]:
        syms_tn, T_raw_tn, T_norm_tn, n_bi_tn = build_transition_matrix(
            all_word_chunks, top_n=tn, min_freq=10)
        res_tn = spectral_vc_analysis(syms_tn, T_norm_tn, T_raw_tn,
                                       label=f"VMS top-{tn}")
        if res_tn:
            stability_results[tn] = res_tn
            pr(f"  Top-{tn:3d}: gap={res_tn['spectral_gap']:.4f}, "
               f"|λ2|={abs(res_tn['lambda2']):.4f}, "
               f"V-ratio={res_tn['small_ratio']:.2f}, "
               f"alt={100*res_tn['alternation_rate']:.1f}%")

    # Check consistency — SIGN-AWARE (eigenvector sign can flip arbitrarily)
    pr()
    pr("  Stability between consecutive top-N values (sign-aware):")
    prev_neg = None; prev_pos = None
    for tn in sorted(stability_results.keys()):
        res = stability_results[tn]
        # Get positive/negative groups from v2 ranking
        neg_g = set(s for s, sc in res['v2_ranked'] if sc <= 0)
        pos_g = set(s for s, sc in res['v2_ranked'] if sc > 0)
        if prev_neg is not None:
            # Check both same-sign and flipped-sign overlap
            same = len(prev_neg & neg_g) + len(prev_pos & pos_g)
            flip = len(prev_neg & pos_g) + len(prev_pos & neg_g)
            prev_total = len(prev_neg | prev_pos)
            best_overlap = max(same, flip)
            note = "(sign flipped)" if flip > same else "(same sign)"
            pr(f"    Top-{prev_tn} → Top-{tn}: {best_overlap}/{prev_total} retained {note}")
        prev_neg = neg_g; prev_pos = pos_g; prev_tn = tn
    pr()

    # ── STEP 8: DOES WORD-POSITION DRIVE THE SPLIT? ──────────────────

    pr("─" * 76)
    pr("STEP 8: CONFOUND CHECK — IS THE SPLIT JUST WORD-POSITION?")
    pr("─" * 76)
    pr()
    pr("  Phase 86 showed chunks cluster mainly by word position (I/M/F).")
    pr("  The spectral split could just be separating initial from final")
    pr("  chunks, not V from C. Test: compute position profiles of each group.")
    pr()

    # Get position profiles for each chunk
    pos_initial = Counter()
    pos_medial = Counter()
    pos_final = Counter()
    pos_single = Counter()  # single-chunk words

    for wc in all_word_chunks:
        if len(wc) == 1:
            pos_single[wc[0]] += 1
        elif len(wc) >= 2:
            pos_initial[wc[0]] += 1
            pos_final[wc[-1]] += 1
            for c in wc[1:-1]:
                pos_medial[c] += 1

    small_set = set(vms_result['small_group'])
    large_set = set(vms_result['large_group'])

    # Average position profile for each group
    def group_position_profile(group_set):
        tot_i = sum(pos_initial.get(c, 0) for c in group_set)
        tot_m = sum(pos_medial.get(c, 0) for c in group_set)
        tot_f = sum(pos_final.get(c, 0) for c in group_set)
        tot_s = sum(pos_single.get(c, 0) for c in group_set)
        total = tot_i + tot_m + tot_f + tot_s
        if total == 0: return (0, 0, 0, 0)
        return (tot_i/total, tot_m/total, tot_f/total, tot_s/total)

    v_prof = group_position_profile(small_set)
    c_prof = group_position_profile(large_set)

    pr(f"  V-candidate position profile: I={100*v_prof[0]:.1f}% M={100*v_prof[1]:.1f}% "
       f"F={100*v_prof[2]:.1f}% S={100*v_prof[3]:.1f}%")
    pr(f"  C-candidate position profile: I={100*c_prof[0]:.1f}% M={100*c_prof[1]:.1f}% "
       f"F={100*c_prof[2]:.1f}% S={100*c_prof[3]:.1f}%")
    pr()

    # If one group is >70% initial and the other >70% final, the split
    # is driven by position, not V/C structure
    v_pos_dominant = max(v_prof[:3]) if v_prof[:3] else 0
    c_pos_dominant = max(c_prof[:3]) if c_prof[:3] else 0
    if v_pos_dominant > 0.60 and c_pos_dominant > 0.60:
        pr("  ⚠ WARNING: Both groups have strong positional bias (>60%)")
        pr("    → The spectral split may be POSITIONAL, not V/C")
        positional_confound = True
    elif v_pos_dominant > 0.70 or c_pos_dominant > 0.70:
        pr("  ⚠ CAUTION: One group has strong positional bias (>70%)")
        pr("    → Partial positional confound possible")
        positional_confound = True
    else:
        pr("  ✓ No strong positional bias in either group")
        positional_confound = False
    pr()

    # Per-chunk position breakdown for V-candidates
    pr("  V-candidate chunks — individual position profiles:")
    pr(f"    {'Chunk':>20s}  {'Count':>6s}  {'Init%':>6s}  {'Med%':>6s}  "
       f"{'Fin%':>6s}  {'Sing%':>6s}")
    pr(f"    {'─'*20}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}")

    chunk_counts_all = Counter()
    for wc in all_word_chunks:
        for c in wc:
            chunk_counts_all[c] += 1

    for c in sorted(vms_result['small_group'],
                    key=lambda x: -chunk_counts_all.get(x, 0)):
        ni = pos_initial.get(c, 0)
        nm = pos_medial.get(c, 0)
        nf = pos_final.get(c, 0)
        ns = pos_single.get(c, 0)
        total = ni + nm + nf + ns
        if total > 0:
            pr(f"    {c:>20s}  {total:6d}  {100*ni/total:5.1f}%  "
               f"{100*nm/total:5.1f}%  {100*nf/total:5.1f}%  {100*ns/total:5.1f}%")
    pr()

    # ── STEP 9: INTERNAL STRUCTURE — DO V-CHUNKS HAVE V-LIKE SLOTS? ──

    pr("─" * 76)
    pr("STEP 9: INTERNAL STRUCTURE — SLOT PATTERN OF V vs C GROUPS")
    pr("─" * 76)
    pr()
    pr("  If the V/C split is real, V-chunks might preferentially fill")
    pr("  the VOWEL slots (S2: e/q/a, S3: o, S4: i/d) while C-chunks")
    pr("  fill CONSONANT slots (S1: ch/sh/y, S5: k/l/r/s/t/...).")
    pr()

    def slot_content_analysis(chunk_str):
        """Return which slots are filled with what category."""
        gs = chunk_str.split('.')
        # Re-parse to identify slot fills
        pos = 0
        slot_fills = {}
        if pos < len(gs) and gs[pos] in SLOT1:
            slot_fills['S1'] = gs[pos]; pos += 1
        if pos < len(gs):
            if gs[pos] in SLOT2_RUNS:
                s2 = []
                while pos < len(gs) and gs[pos] in SLOT2_RUNS:
                    s2.append(gs[pos]); pos += 1
                slot_fills['S2'] = '.'.join(s2)
            elif gs[pos] in SLOT2_SINGLE:
                slot_fills['S2'] = gs[pos]; pos += 1
        if pos < len(gs) and gs[pos] in SLOT3:
            slot_fills['S3'] = gs[pos]; pos += 1
        if pos < len(gs):
            if gs[pos] in SLOT4_RUNS:
                s4 = []
                while pos < len(gs) and gs[pos] in SLOT4_RUNS:
                    s4.append(gs[pos]); pos += 1
                slot_fills['S4'] = '.'.join(s4)
            elif gs[pos] in SLOT4_SINGLE:
                slot_fills['S4'] = gs[pos]; pos += 1
        if pos < len(gs) and gs[pos] in SLOT5:
            slot_fills['S5'] = gs[pos]; pos += 1
        return slot_fills

    # For each group, what fraction of chunks fill each slot?
    def group_slot_profile(group):
        slot_counts = Counter()
        total = 0
        for c in group:
            fills = slot_content_analysis(c)
            for s in fills:
                slot_counts[s] += 1
            total += 1
        return {s: slot_counts[s] / total if total > 0 else 0
                for s in ['S1', 'S2', 'S3', 'S4', 'S5']}

    v_slots = group_slot_profile(vms_result['small_group'])
    c_slots = group_slot_profile(vms_result['large_group'])

    pr(f"  Slot fill rates:")
    pr(f"  {'Slot':>4s}  {'V-group':>8s}  {'C-group':>8s}  {'Slot type':>12s}")
    pr(f"  {'─'*4}  {'─'*8}  {'─'*8}  {'─'*12}")
    slot_types = {'S1': 'consonant', 'S2': 'front-V', 'S3': 'core-V',
                  'S4': 'back-V/d', 'S5': 'consonant'}
    for s in ['S1', 'S2', 'S3', 'S4', 'S5']:
        pr(f"  {s:>4s}  {100*v_slots[s]:7.1f}%  {100*c_slots[s]:7.1f}%  {slot_types[s]:>12s}")
    pr()

    # Check if V-group chunks preferentially fill vowel slots
    v_vowel_slots = (v_slots['S2'] + v_slots['S3'] + v_slots['S4']) / 3
    c_vowel_slots = (c_slots['S2'] + c_slots['S3'] + c_slots['S4']) / 3
    v_cons_slots = (v_slots['S1'] + v_slots['S5']) / 2
    c_cons_slots = (c_slots['S1'] + c_slots['S5']) / 2

    pr(f"  Mean vowel-slot fill:     V-group={100*v_vowel_slots:.1f}%, C-group={100*c_vowel_slots:.1f}%")
    pr(f"  Mean consonant-slot fill: V-group={100*v_cons_slots:.1f}%, C-group={100*c_cons_slots:.1f}%")
    if v_vowel_slots > c_vowel_slots and c_cons_slots > v_cons_slots:
        pr("  ✓ V-group fills vowel slots more; C-group fills consonant slots more")
        slot_consistent = True
    elif c_vowel_slots > v_vowel_slots and v_cons_slots > c_cons_slots:
        pr("  ✓ Labels may be swapped but differentiation exists")
        slot_consistent = True
    else:
        pr("  ✗ No clear vowel-slot vs consonant-slot differentiation")
        slot_consistent = False
    pr()

    # ── SYNTHESIS ──────────────────────────────────────────────────────

    pr("=" * 76)
    pr("SYNTHESIS & VERDICT")
    pr("=" * 76)
    pr()

    # Compute NL averages for comparison
    nl_gaps = [r['spectral_gap'] for r in nl_char_results.values()]
    nl_alts = [r['alternation_rate'] for r in nl_char_results.values()]
    nl_purs = [r['purity'] for r in nl_char_results.values()]
    nl_rats = [r['small_ratio'] for r in nl_char_results.values()]

    if nl_gaps:
        nl_gap_mean = np.mean(nl_gaps)
        nl_gap_std = np.std(nl_gaps)
        nl_alt_mean = np.mean(nl_alts)
        nl_alt_std = np.std(nl_alts)
        nl_pur_mean = np.mean(nl_purs)
        nl_rat_mean = np.mean(nl_rats)
        nl_rat_std = np.std(nl_rats)

        z_gap_nl = ((vms_result['spectral_gap'] - nl_gap_mean) / nl_gap_std
                    if nl_gap_std > 1e-10 else 0)
        z_alt_nl = ((vms_result['alternation_rate'] - nl_alt_mean) / nl_alt_std
                    if nl_alt_std > 1e-10 else 0)
        z_rat_nl = ((vms_result['small_ratio'] - nl_rat_mean) / nl_rat_std
                    if nl_rat_std > 1e-10 else 0)

        pr(f"  1. SPECTRAL GAP")
        pr(f"     VMS:         {vms_result['spectral_gap']:.4f}")
        pr(f"     NL chars:    {nl_gap_mean:.4f} ± {nl_gap_std:.4f}")
        pr(f"     z-score:     {z_gap_nl:+.2f}")
        pr(f"     vs null-1:   z = {z_gap_1:.2f}")
        pr(f"     vs null-2:   z = {z_gap_2:.2f}")
        pr()

        pr(f"  2. V/C RATIO (expected ~0.15-0.25)")
        pr(f"     VMS:         {vms_result['small_ratio']:.2f}")
        pr(f"     NL chars:    {nl_rat_mean:.2f} ± {nl_rat_std:.2f}")
        pr(f"     z-score:     {z_rat_nl:+.2f}")
        pr()

        pr(f"  3. ALTERNATION RATE (expected ~60-80%)")
        pr(f"     VMS:         {100*vms_result['alternation_rate']:.1f}%")
        pr(f"     NL chars:    {100*nl_alt_mean:.1f}% ± {100*nl_alt_std:.1f}%")
        pr(f"     z-score:     {z_alt_nl:+.2f}")
        pr()

        pr(f"  4. POSITIONAL CONFOUND: {'YES' if positional_confound else 'NO'}")
        pr(f"  5. SLOT CONSISTENCY: {'YES' if slot_consistent else 'NO'}")
        pr()

        # NL syllable gaps for comparison
        if nl_syl_results:
            syl_gaps = [r['spectral_gap'] for r in nl_syl_results.values()]
            pr(f"  6. NL SYLLABLE GAPS (control): {[f'{g:.4f}' for g in syl_gaps]}")
            pr(f"     NL syllables should have WEAKER gaps than NL characters.")
            syl_gap_mean = np.mean(syl_gaps)
            pr(f"     NL syl gap mean: {syl_gap_mean:.4f} vs NL char gap mean: {nl_gap_mean:.4f}")
            pr()

        # VERDICT
        gap_significant = z_gap_1 > 2 and z_gap_2 > 2
        gap_in_nl_range = abs(z_gap_nl) < 2
        ratio_in_nl_range = abs(z_rat_nl) < 2
        alt_in_nl_range = abs(z_alt_nl) < 2

        pr(f"  VERDICT:")
        if (gap_significant and gap_in_nl_range and ratio_in_nl_range
                and alt_in_nl_range and not positional_confound):
            pr(f"  ★ SUPPORTED: VMS chunk bigrams show a clear V/C spectral split")
            pr(f"    consistent with NL alphabetic encoding. Spectral gap, V/C ratio,")
            pr(f"    and alternation rate all match natural language characters.")
            verdict = "SUPPORTED"
        elif gap_significant and (gap_in_nl_range or alt_in_nl_range):
            if positional_confound:
                pr(f"  ◐ PARTIALLY SUPPORTED BUT CONFOUNDED: A spectral split exists")
                pr(f"    but may be driven by word-position effects rather than V/C.")
                verdict = "CONFOUNDED"
            else:
                pr(f"  ◐ PARTIALLY SUPPORTED: Significant spectral gap exists but")
                pr(f"    some metrics fall outside the NL character range.")
                verdict = "PARTIALLY_SUPPORTED"
        elif gap_significant:
            pr(f"  ? SIGNIFICANT BUT ANOMALOUS: A spectral split exists but does")
            pr(f"    not match NL V/C patterns. May indicate a non-standard encoding")
            pr(f"    or a structural feature other than V/C alternation.")
            verdict = "ANOMALOUS"
        else:
            pr(f"  ✗ NOT SUPPORTED: No significant spectral gap detected.")
            pr(f"    VMS chunks do not show V/C alternation structure.")
            verdict = "NOT_SUPPORTED"
    else:
        pr(f"  No NL baseline data available for comparison.")
        verdict = "INSUFFICIENT"

    pr()

    # ── SAVE RESULTS ──────────────────────────────────────────────────

    json_out = {
        'vms': {
            'n_symbols': vms_result['n_symbols'],
            'spectral_gap': vms_result['spectral_gap'],
            'lambda2': vms_result['lambda2'],
            'small_ratio': vms_result['small_ratio'],
            'alternation_rate': vms_result['alternation_rate'],
            'v_candidates': vms_result['small_group'],
            'c_candidates': vms_result['large_group'],
        },
        'nl_char': {
            name: {
                'spectral_gap': r['spectral_gap'],
                'small_ratio': r['small_ratio'],
                'alternation_rate': r['alternation_rate'],
                'purity': r['purity'],
            }
            for name, r in nl_char_results.items()
        },
        'nl_syl': {
            name: {
                'spectral_gap': r['spectral_gap'],
                'alternation_rate': r['alternation_rate'],
            }
            for name, r in nl_syl_results.items()
        },
        'null_models': {
            'row_permuted': null1,
            'shuffled_bigrams': null2,
        },
        'currier': {
            lang: {
                'spectral_gap': r['spectral_gap'],
                'v_candidates': r['small_group'],
                'alternation_rate': r['alternation_rate'],
            }
            for lang, r in currier_results.items()
        },
        'positional_confound': positional_confound,
        'slot_consistent': slot_consistent,
        'verdict': verdict,
    }

    with open(RESULTS_DIR / 'phase87_spectral_vc.json', 'w') as f:
        json.dump(json_out, f, indent=2, default=str)

    text_out = ''.join(OUTPUT)
    with open(RESULTS_DIR / 'phase87_spectral_vc.txt', 'w', encoding='utf-8') as f:
        f.write(text_out)

    pr(f"  Saved to results/phase87_spectral_vc.txt/.json")


if __name__ == '__main__':
    main()
