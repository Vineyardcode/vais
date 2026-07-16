#!/usr/bin/env python3
"""
Abjad/Consonantal Hypothesis: Vowel-Stripping Fingerprint Test

═══════════════════════════════════════════════════════════════════════

MOTIVATION: Three independent analyses converge on 13 functional VMS letters:
  (a) Hebrew consonantal alphabet reduced to 13 after removing homophones
  (b) Voynich Talk video: positional variant collapse → ~13 functional glyphs
  (c) forward_process_models: verbose positional cipher with 13 underlying characters
      is the ONLY model reproducing VMS h_char anomaly (0.641)

If VMS uses a consonantal/abjad writing system (consonants only, vowels
omitted like Hebrew/Arabic), then 13 letters is perfectly adequate.
The Voynich Talk video's conclusion that "13 is a disaster for European
languages" becomes "13 is normal for an abjad."

Lisa Fagin Davis notes: no punctuation, no majuscule/minuscule,
extremely low word-level entropy (Bowern & Lindemann). All consistent
with a consonantal system.

THIS PHASE TESTS: If we strip vowels from known natural languages,
do the resulting statistical fingerprints match VMS more closely?

TESTS:
A. BASELINE — Full fingerprint for each reference text (normal)
B. VOWEL-STRIPPED — Remove all vowels, recompute fingerprints
C. VMS COMPARISON — Distance from each (normal, stripped) to VMS target
D. SPECIFIC ANOMALY CHECK — Does stripping reproduce:
   - h_char ratio ≈ 0.641 (char bigram predictability)
   - mean word length ≈ 4.94
   - low word-level entropy
   - Heaps β ≈ 0.753
   - Hapax ratio ≈ 0.656
E. ALPHABET SIZE — Does the effective alphabet shrink to ~13?
F. CONSONANT CLUSTER PATTERNS — Does stripping create VMS-like
   anti-alternation (consecutive same-class characters)?
G. WORD LENGTH DISTRIBUTION — Compare shape against VMS distribution
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import char_bigram_predictability, clean_word_v2 as clean_word, eva_to_glyphs, hapax_ratio_at_midpoint, index_of_coincidence, mean_word_length, ttr_at_n, zipf_alpha

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(42)

# ═══════════════════════════════════════════════════════════════════════
# EVA GLYPH PARSING (for VMS)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']



def parse_vms_words():
    """Parse all VMS words, return (words_list, glyph_chars_list)."""
    words = []
    all_glyphs = []

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)

    for filepath in folio_files:
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

                text = rest.replace('<%>', '').replace('<$>', '').strip()
                text = re.sub(r'@\d+;', '', text)
                text = re.sub(r'<[^>]*>', '', text)

                for tok in re.split(r'[.\s]+', text):
                    for subtok in re.split(r',', tok):
                        c = clean_word(subtok.strip())
                        if c:
                            words.append(c)
                            all_glyphs.extend(eva_to_glyphs(c))

    return words, all_glyphs


# ═══════════════════════════════════════════════════════════════════════
# VOWEL STRIPPING
# ═══════════════════════════════════════════════════════════════════════

# Standard vowels for each language family
VOWELS_BASIC = set('aeiou')
VOWELS_LATIN = set('aeiouy')  # y is semi-vowel in Latin
VOWELS_EXTENDED = set('aeiouàáâãäåæèéêëìíîïòóôõöùúûüýÿ')

def strip_vowels(text, vowel_set=VOWELS_EXTENDED):
    """Remove all vowel characters from a string."""
    return ''.join(c for c in text if c.lower() not in vowel_set)

def load_reference_text(filepath):
    """Load a reference text file, return lowercase words (alpha only)."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()

    # Strip Gutenberg headers/footers if present
    start_marker = '*** START OF'
    end_marker = '*** END OF'
    start_idx = raw.find(start_marker)
    end_idx = raw.find(end_marker)
    if start_idx >= 0:
        raw = raw[raw.index('\n', start_idx) + 1:]
    if end_idx >= 0:
        raw = raw[:end_idx]

    text = raw.lower()
    # Keep only letters (including accented) and spaces
    text = re.sub(r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþß\s]+', ' ', text)
    words = [w for w in text.split() if len(w) >= 1]
    return words

def strip_vowels_from_words(words, vowel_set=VOWELS_EXTENDED):
    """Strip vowels from each word, discard empty results."""
    stripped = []
    for w in words:
        s = strip_vowels(w, vowel_set)
        if s:  # Only keep non-empty results
            stripped.append(s)
    return stripped


# ═══════════════════════════════════════════════════════════════════════
# FINGERPRINT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def heaps_exponent(words):
    """Fit Heaps' law V(n) = K * n^β via log-log regression."""
    n = len(words)
    if n < 100:
        return 0.0
    sample_points = np.linspace(100, n, 20, dtype=int)
    vocab_at = {}
    running = set()
    idx = 0
    for pt in sorted(sample_points):
        while idx < pt:
            running.add(words[idx])
            idx += 1
        vocab_at[pt] = len(running)
    log_n = np.array([math.log(pt) for pt in sample_points])
    log_v = np.array([math.log(vocab_at[pt]) for pt in sample_points])
    A = np.vstack([log_n, np.ones(len(log_n))]).T
    result = np.linalg.lstsq(A, log_v, rcond=None)
    return float(result[0][0])



def word_bigram_predictability(words):
    """H(w|prev_w) / H(w) — word-level predictability ratio."""
    n = len(words)
    if n < 100:
        return 1.0
    unigram = Counter(words)
    total = sum(unigram.values())
    h_uni = -sum((c/total) * math.log2(c/total) for c in unigram.values() if c > 0)

    bigrams = Counter()
    for i in range(1, n):
        bigrams[(words[i-1], words[i])] += 1
    total_bi = sum(bigrams.values())
    h_joint = -sum((c/total_bi) * math.log2(c/total_bi) for c in bigrams.values() if c > 0)
    prev_counts = Counter()
    for (w1, w2), cnt in bigrams.items():
        prev_counts[w1] += cnt
    prev_total = sum(prev_counts.values())
    h_prev = -sum((c/prev_total) * math.log2(c/prev_total) for c in prev_counts.values() if c > 0)
    h_cond = h_joint - h_prev
    if h_uni == 0:
        return 1.0
    return h_cond / h_uni





def compute_fingerprint(words, char_list, label):
    """Compute the full statistical fingerprint."""
    n_types = len(set(words))
    alphabet = sorted(set(char_list))
    return {
        'label': label,
        'n_tokens': len(words),
        'n_types': n_types,
        'alphabet_size': len(alphabet),
        'heaps_beta': heaps_exponent(words),
        'hapax_ratio_mid': hapax_ratio_at_midpoint(words),
        'h_char_ratio': char_bigram_predictability(char_list),
        'h_word_ratio': word_bigram_predictability(words),
        'mean_word_len': mean_word_length(words),
        'ttr_5000': ttr_at_n(words, 5000),
        'zipf_alpha': zipf_alpha(words),
        'ic': index_of_coincidence(char_list),
    }


# ═══════════════════════════════════════════════════════════════════════
# WORD LENGTH DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════

def word_length_distribution(words, max_len=15):
    """Return word length distribution as fraction, lengths 1..max_len."""
    lens = [min(len(w), max_len) for w in words]
    freq = Counter(lens)
    total = len(lens)
    return {l: freq.get(l, 0) / total for l in range(1, max_len + 1)}

def wld_distance(dist1, dist2):
    """L1 (Manhattan) distance between two word length distributions."""
    all_keys = set(dist1.keys()) | set(dist2.keys())
    return sum(abs(dist1.get(k, 0) - dist2.get(k, 0)) for k in all_keys)


# ═══════════════════════════════════════════════════════════════════════
# CONSONANT CLUSTER ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def alternation_score(words):
    """Measure vowel-consonant alternation.
    For stripped words this measures consecutive-same character repetition.
    Returns fraction of consecutive char pairs that are different."""
    changes = 0
    total = 0
    for w in words:
        for i in range(1, len(w)):
            total += 1
            if w[i] != w[i-1]:
                changes += 1
    return changes / total if total > 0 else 0


# ═══════════════════════════════════════════════════════════════════════
# DISTANCE METRIC
# ═══════════════════════════════════════════════════════════════════════

VMS_TARGET = {
    'h_char_ratio': 0.641,
    'heaps_beta': 0.753,
    'hapax_ratio_mid': 0.656,
    'mean_word_len': 4.94,
    'zipf_alpha': 0.942,
    'ttr_5000': 0.342,
}

def fingerprint_distance(fp, target=VMS_TARGET):
    """Euclidean distance in normalised fingerprint space."""
    dims = []
    for key, vms_val in target.items():
        if key in fp and vms_val != 0:
            dims.append(((fp[key] - vms_val) / vms_val) ** 2)
    return math.sqrt(sum(dims)) if dims else float('inf')


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 72)
    pr("abjad_hypothesis — ABJAD/CONSONANTAL HYPOTHESIS: VOWEL-STRIPPING TEST")
    pr("=" * 72)
    pr()

    # ── STEP 1: Load VMS ──────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 1: VMS BASELINE FINGERPRINT")
    pr("─" * 72)
    vms_words, vms_glyphs = parse_vms_words()
    vms_fp = compute_fingerprint(vms_words, vms_glyphs, "VMS (EVA glyphs)")
    pr(f"  Tokens: {vms_fp['n_tokens']:,}   Types: {vms_fp['n_types']:,}")
    pr(f"  Alphabet size: {vms_fp['alphabet_size']}")
    pr(f"  h_char ratio:  {vms_fp['h_char_ratio']:.4f}")
    pr(f"  h_word ratio:  {vms_fp['h_word_ratio']:.4f}")
    pr(f"  Heaps β:       {vms_fp['heaps_beta']:.4f}")
    pr(f"  Hapax mid:     {vms_fp['hapax_ratio_mid']:.4f}")
    pr(f"  Mean wlen:     {vms_fp['mean_word_len']:.2f}")
    pr(f"  TTR@5000:      {vms_fp['ttr_5000']:.4f}")
    pr(f"  Zipf α:        {vms_fp['zipf_alpha']:.4f}")
    pr(f"  IC:            {vms_fp['ic']:.5f}")
    pr()

    vms_wld = word_length_distribution(vms_words)
    pr("  Word length distribution (VMS):")
    for l in range(1, 12):
        bar = '█' * int(vms_wld.get(l, 0) * 100)
        pr(f"    {l:2d}: {vms_wld.get(l, 0):.3f}  {bar}")
    pr()

    # ── STEP 2: Load reference texts ─────────────────────────────────
    pr("─" * 72)
    pr("STEP 2: REFERENCE TEXTS — NORMAL vs VOWEL-STRIPPED")
    pr("─" * 72)
    pr()

    ref_files = {
        'Latin (Caesar)': DATA_DIR / 'latin_texts' / 'caesar.txt',
        'Latin (Vulgate)': DATA_DIR / 'latin_texts' / 'vulgate_genesis.txt',
        'Latin (Apicius)': DATA_DIR / 'latin_texts' / 'apicius.txt',
        'Italian (Cucina)': DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt',
        'French (Viandier)': DATA_DIR / 'vernacular_texts' / 'french_viandier.txt',
        'English (Cury)': DATA_DIR / 'vernacular_texts' / 'english_cury.txt',
    }

    results = []  # (label, fp_normal, fp_stripped, dist_normal, dist_stripped)

    for lang_label, filepath in ref_files.items():
        if not filepath.exists():
            pr(f"  SKIP: {filepath} not found")
            continue

        words_full = load_reference_text(filepath)
        if len(words_full) < 200:
            pr(f"  SKIP: {lang_label} too short ({len(words_full)} words)")
            continue

        # Limit to comparable size with VMS
        cap = min(len(words_full), 40000)
        words_full = words_full[:cap]

        chars_full = list(''.join(words_full))
        fp_normal = compute_fingerprint(words_full, chars_full, f"{lang_label}")

        # Strip vowels
        words_stripped = strip_vowels_from_words(words_full)
        chars_stripped = list(''.join(words_stripped))
        fp_stripped = compute_fingerprint(words_stripped, chars_stripped,
                                          f"{lang_label} (no vowels)")

        dist_normal = fingerprint_distance(fp_normal)
        dist_stripped = fingerprint_distance(fp_stripped)

        results.append((lang_label, fp_normal, fp_stripped, dist_normal, dist_stripped))

        pr(f"  {lang_label}:")
        pr(f"    Normal:  {fp_normal['n_tokens']:>6,} tok, {fp_normal['n_types']:>5,} types, "
           f"alpha={fp_normal['alphabet_size']:>2}, "
           f"h_char={fp_normal['h_char_ratio']:.3f}, "
           f"wlen={fp_normal['mean_word_len']:.2f}, "
           f"Heaps={fp_normal['heaps_beta']:.3f}, "
           f"hapax={fp_normal['hapax_ratio_mid']:.3f}, "
           f"Zipf={fp_normal['zipf_alpha']:.3f}")
        pr(f"    Stripped: {fp_stripped['n_tokens']:>6,} tok, {fp_stripped['n_types']:>5,} types, "
           f"alpha={fp_stripped['alphabet_size']:>2}, "
           f"h_char={fp_stripped['h_char_ratio']:.3f}, "
           f"wlen={fp_stripped['mean_word_len']:.2f}, "
           f"Heaps={fp_stripped['heaps_beta']:.3f}, "
           f"hapax={fp_stripped['hapax_ratio_mid']:.3f}, "
           f"Zipf={fp_stripped['zipf_alpha']:.3f}")
        pr(f"    Distance to VMS: normal={dist_normal:.4f}  stripped={dist_stripped:.4f}"
           f"  {'← CLOSER' if dist_stripped < dist_normal else '→ FARTHER'}")
        pr()

    # ── STEP 3: Summary table ─────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 3: DISTANCE COMPARISON TABLE")
    pr("─" * 72)
    pr()
    pr(f"  VMS TARGET:  h_char={VMS_TARGET['h_char_ratio']:.3f}  "
       f"Heaps={VMS_TARGET['heaps_beta']:.3f}  "
       f"hapax={VMS_TARGET['hapax_ratio_mid']:.3f}  "
       f"wlen={VMS_TARGET['mean_word_len']:.2f}  "
       f"Zipf={VMS_TARGET['zipf_alpha']:.3f}  "
       f"TTR={VMS_TARGET['ttr_5000']:.3f}")
    pr()
    pr(f"  {'Language':<25s} {'Dist(normal)':>12s} {'Dist(stripped)':>14s} {'Delta':>8s} {'Verdict':>10s}")
    pr(f"  {'─'*25} {'─'*12} {'─'*14} {'─'*8} {'─'*10}")

    for lang_label, fp_n, fp_s, dist_n, dist_s in results:
        delta = dist_s - dist_n
        verdict = "CLOSER" if delta < 0 else "FARTHER"
        pr(f"  {lang_label:<25s} {dist_n:>12.4f} {dist_s:>14.4f} {delta:>+8.4f} {verdict:>10s}")
    pr()

    # ── STEP 4: Dimension-by-dimension analysis ──────────────────────
    pr("─" * 72)
    pr("STEP 4: DIMENSION-BY-DIMENSION — WHICH STATS MOVE TOWARD VMS?")
    pr("─" * 72)
    pr()

    dims = ['h_char_ratio', 'heaps_beta', 'hapax_ratio_mid', 'mean_word_len',
            'zipf_alpha', 'ttr_5000']
    dim_names = ['h_char', 'Heaps β', 'Hapax', 'WordLen', 'Zipf α', 'TTR']

    pr(f"  {'Language':<22s}", end='')
    for dn in dim_names:
        pr(f"  {dn:>10s}", end='')
    pr()
    pr(f"  {'─'*22}", end='')
    for _ in dim_names:
        pr(f"  {'─'*10}", end='')
    pr()

    # VMS row
    pr(f"  {'VMS TARGET':<22s}", end='')
    for d in dims:
        pr(f"  {VMS_TARGET[d]:>10.3f}", end='')
    pr()

    for lang_label, fp_n, fp_s, _, _ in results:
        # Normal values
        pr(f"  {lang_label[:20]:<22s}", end='')
        for d in dims:
            pr(f"  {fp_n[d]:>10.3f}", end='')
        pr()
        # Stripped values with arrows
        pr(f"  {'  (no vowels)':<22s}", end='')
        for d in dims:
            val = fp_s[d]
            vms_v = VMS_TARGET[d]
            normal_gap = abs(fp_n[d] - vms_v)
            stripped_gap = abs(val - vms_v)
            arrow = '→' if stripped_gap < normal_gap else '←'  # → means toward VMS
            pr(f"  {val:>8.3f}{arrow:>2s}", end='')
        pr()
    pr()
    pr("  Key: → = moved toward VMS target, ← = moved away from VMS target")
    pr()

    # ── STEP 5: Alphabet size analysis ────────────────────────────────
    pr("─" * 72)
    pr("STEP 5: ALPHABET SIZE — DOES STRIPPING HIT ~13?")
    pr("─" * 72)
    pr()
    pr(f"  VMS (EVA glyphs): {vms_fp['alphabet_size']} distinct glyphs")
    pr(f"  VMS (after run_length_morphology functional collapse): ~13 functional units")
    pr()

    for lang_label, fp_n, fp_s, _, _ in results:
        pr(f"  {lang_label}: {fp_n['alphabet_size']} → {fp_s['alphabet_size']} "
           f"(lost {fp_n['alphabet_size'] - fp_s['alphabet_size']} vowel chars)")
    pr()

    # ── STEP 6: Word length distribution comparison ───────────────────
    pr("─" * 72)
    pr("STEP 6: WORD LENGTH DISTRIBUTION — SHAPE COMPARISON")
    pr("─" * 72)
    pr()

    pr(f"  {'Language':<28s} {'WLD dist(normal)':>16s} {'WLD dist(stripped)':>18s} {'Verdict':>10s}")
    pr(f"  {'─'*28} {'─'*16} {'─'*18} {'─'*10}")

    for lang_label, fp_n, fp_s, _, _ in results:
        words_full = load_reference_text(ref_files[lang_label])[:40000]
        words_stripped = strip_vowels_from_words(words_full)

        wld_n = word_length_distribution(words_full)
        wld_s = word_length_distribution(words_stripped)

        d_n = wld_distance(vms_wld, wld_n)
        d_s = wld_distance(vms_wld, wld_s)
        v = "CLOSER" if d_s < d_n else "FARTHER"
        pr(f"  {lang_label:<28s} {d_n:>16.4f} {d_s:>18.4f} {v:>10s}")

    pr()

    # Show one illustrative WLD comparison
    if results:
        best_lang = min(results, key=lambda r: fingerprint_distance(r[2]))[0]
        words_best = load_reference_text(ref_files[best_lang])[:40000]
        words_best_s = strip_vowels_from_words(words_best)
        wld_best_s = word_length_distribution(words_best_s)

        pr(f"  WLD comparison: VMS vs {best_lang} (stripped)")
        pr(f"    {'Len':>4s}  {'VMS':>6s}  {'Stripped':>8s}  VMS-bar / Stripped-bar")
        for l in range(1, 12):
            v = vms_wld.get(l, 0)
            s = wld_best_s.get(l, 0)
            vbar = '█' * int(v * 80)
            sbar = '░' * int(s * 80)
            pr(f"    {l:>4d}  {v:>.3f}  {s:>.3f}    {vbar}")
            pr(f"    {'':>4s}  {'':>6s}  {'':>8s}    {sbar}")
    pr()

    # ── STEP 7: Alternation / cluster analysis ────────────────────────
    pr("─" * 72)
    pr("STEP 7: CONSONANT CLUSTERING — ANTI-ALTERNATION TEST")
    pr("─" * 72)
    pr()
    pr("  VMS shows extreme anti-alternation (z = -54.7 from vowel_consonant_separation).")
    pr("  Does vowel stripping increase consonant clustering?")
    pr()

    vms_alt = alternation_score(vms_words)
    pr(f"  VMS alternation score: {vms_alt:.4f}")
    pr()

    for lang_label, fp_n, fp_s, _, _ in results:
        words_full = load_reference_text(ref_files[lang_label])[:40000]
        words_stripped = strip_vowels_from_words(words_full)

        alt_n = alternation_score(words_full)
        alt_s = alternation_score(words_stripped)

        pr(f"  {lang_label:<25s}  normal={alt_n:.4f}  stripped={alt_s:.4f}  "
           f"VMS={vms_alt:.4f}  "
           f"{'→ CLOSER' if abs(alt_s - vms_alt) < abs(alt_n - vms_alt) else '← FARTHER'}")
    pr()

    # ── STEP 8: The critical h_char test ──────────────────────────────
    pr("─" * 72)
    pr("STEP 8: THE CRITICAL h_char TEST — DOES STRIPPING HIT 0.641?")
    pr("─" * 72)
    pr()
    pr("  VMS h_char ratio (H(c|prev)/H(c)) = 0.641")
    pr("  This is the signature anomaly no encoding model reproduces (forward_process_models).")
    pr("  Natural language is typically 0.55-0.70.")
    pr("  The question: does vowel stripping push h_char TOWARD 0.641?")
    pr()

    for lang_label, fp_n, fp_s, _, _ in results:
        h_n = fp_n['h_char_ratio']
        h_s = fp_s['h_char_ratio']
        gap_n = abs(h_n - 0.641)
        gap_s = abs(h_s - 0.641)
        direction = "→ VMS" if gap_s < gap_n else "← AWAY"
        pr(f"  {lang_label:<25s}  normal={h_n:.4f}  stripped={h_s:.4f}  "
           f"gap: {gap_n:.4f} → {gap_s:.4f}  {direction}")
    pr()

    # ── STEP 9: IC analysis ───────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 9: INDEX OF COINCIDENCE")
    pr("─" * 72)
    pr()
    pr(f"  VMS IC: {vms_fp['ic']:.5f}")
    pr()

    for lang_label, fp_n, fp_s, _, _ in results:
        ic_n = fp_n['ic']
        ic_s = fp_s['ic']
        gap_n = abs(ic_n - vms_fp['ic'])
        gap_s = abs(ic_s - vms_fp['ic'])
        verdict = "→ CLOSER" if gap_s < gap_n else "← FARTHER"
        pr(f"  {lang_label:<25s}  normal={ic_n:.5f}  stripped={ic_s:.5f}  {verdict}")
    pr()

    # ── STEP 10: Final synthesis ──────────────────────────────────────
    pr("=" * 72)
    pr("SYNTHESIS: ABJAD HYPOTHESIS ASSESSMENT")
    pr("=" * 72)
    pr()

    # Count how many languages got closer on each dimension
    closer_counts = defaultdict(int)
    total_counts = defaultdict(int)
    for lang_label, fp_n, fp_s, _, _ in results:
        for d in dims:
            total_counts[d] += 1
            normal_gap = abs(fp_n[d] - VMS_TARGET[d])
            stripped_gap = abs(fp_s[d] - VMS_TARGET[d])
            if stripped_gap < normal_gap:
                closer_counts[d] += 1

    pr("  Fraction of languages where stripping moved TOWARD VMS:")
    pr()
    for d, dn in zip(dims, dim_names):
        frac = closer_counts[d] / total_counts[d] if total_counts[d] > 0 else 0
        bar = '█' * int(frac * 30)
        pr(f"    {dn:<12s}  {closer_counts[d]}/{total_counts[d]}  ({frac:.0%})  {bar}")
    pr()

    # Overall distance comparison
    closer_overall = sum(1 for _, _, _, dn, ds in results if ds < dn)
    pr(f"  Languages closer to VMS after stripping: {closer_overall}/{len(results)}")
    pr()

    # Best match
    if results:
        best = min(results, key=lambda r: r[4])  # lowest stripped distance
        pr(f"  Best overall match (stripped): {best[0]}")
        pr(f"    Distance: {best[4]:.4f} (vs normal {best[3]:.4f})")
        pr()

    # Critical assessment
    pr("  CRITICAL ASSESSMENT:")
    pr("  ─────────────────────")

    # h_char assessment
    h_closers = sum(1 for _, fp_n, fp_s, _, _ in results
                    if abs(fp_s['h_char_ratio'] - 0.641) < abs(fp_n['h_char_ratio'] - 0.641))
    pr(f"  • h_char (0.641): {h_closers}/{len(results)} languages move toward VMS")

    # word length assessment
    wlen_closers = sum(1 for _, fp_n, fp_s, _, _ in results
                       if abs(fp_s['mean_word_len'] - 4.94) < abs(fp_n['mean_word_len'] - 4.94))
    pr(f"  • Word length (4.94): {wlen_closers}/{len(results)} move toward VMS")

    # Heaps assessment
    heaps_closers = sum(1 for _, fp_n, fp_s, _, _ in results
                        if abs(fp_s['heaps_beta'] - 0.753) < abs(fp_n['heaps_beta'] - 0.753))
    pr(f"  • Heaps β (0.753): {heaps_closers}/{len(results)} move toward VMS")

    pr()
    pr("  VERDICT:")
    if closer_overall > len(results) / 2:
        pr("  Vowel stripping moves MAJORITY of languages closer to VMS.")
        pr("  The abjad/consonantal hypothesis gains significant support.")
        if h_closers > len(results) / 2:
            pr("  CRITICALLY: h_char moves toward 0.641 — the signature anomaly")
            pr("  that no encoding model could reproduce is explained by")
            pr("  consonantal writing.")
        else:
            pr("  However, h_char does NOT consistently move toward 0.641.")
            pr("  This is a serious obstacle for the hypothesis.")
    else:
        pr("  Vowel stripping does NOT consistently move languages toward VMS.")
        pr("  The abjad hypothesis is WEAKENED by this evidence.")
        if h_closers > len(results) / 2:
            pr("  Note: h_char DOES move closer, suggesting partial consonantal")
            pr("  behavior, but the full fingerprint diverges.")
    pr()

    # ── Save results ──────────────────────────────────────────────────
    outpath = RESULTS_DIR / 'abjad_hypothesis.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"Results saved to {outpath}")


if __name__ == '__main__':
    main()
