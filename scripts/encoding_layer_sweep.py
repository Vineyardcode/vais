#!/usr/bin/env python3
"""
ENCODING LAYER PARAMETER SWEEP
══════════════════════════════════════════════════════════════════════

STRATEGIC RATIONALE:

94 phases have established ONE central unsolved anomaly:
  h_char_ratio (H(c|prev)/H(c)) = 0.641 for VMS
  vs 0.82-0.90 for ALL tested natural languages.

Phases 59-61 tested encoding transformations on Italian (Dante) only,
finding that a positional verbose cipher gets close on h_char but fails
on word shape (anti-correlated positional entropy). script_reverse_engineering showed BPE
merging fails. encoding_model_tournament's tournament tested 7 models on Italian only.

WHAT'S NEVER BEEN DONE:
  Apply a parametric FAMILY of encoding transformations to MULTIPLE
  source languages simultaneously and find which (language, encoding)
  combination minimizes distance to VMS across ALL 6 fingerprint metrics.

This is NOT testing a specific cipher hypothesis. It's asking:
  "For each reference language, what is the MINIMUM possible
   fingerprint distance to VMS under ANY plausible encoding,
   and which language permits the closest approach?"

If German achieves closer-than-Italian under some encoding, that's
a LANGUAGE CONSTRAINT. If no encoding on any language reaches h_char<0.70,
that constrains the ENCODING CLASS needed.

ENCODING FAMILY (5 transformations, each with 1-3 parameters):

  E1: NULL (identity) — baseline, no encoding.

  E2: VOWEL EXPANSION — Each vowel expands to a deterministic 2-char
      sequence. Parameter: expansion_prob (0.3 to 1.0). This is the
      forward_process_models/60 mechanism that matched h_char.
      At p=1.0: all vowels expand. At p=0.5: half do.

  E3: POSITIONAL SUBSTITUTION — Characters map to different output
      depending on word position (initial/medial/final). Parameter:
      n_zones (2 to 5). This tests positional_verbose_cipher's mechanism.

  E4: COMBINED (E2+E3) — Vowel expansion WITH positional variants.
      Parameters: expansion_prob × n_zones.

  E5: BIGRAM COLLAPSE — Common character pairs merge into single
      symbols. Parameter: n_merges (0 to 30). Tests whether the
      script has a partially syllabic/abugida structure.

SOURCE LANGUAGES (all available in data/):
  German Faust, German BvgS, Latin Caesar, Latin Vulgate,
  Latin Apicius, Italian Cucina, French Viandier, English Cury.

METRIC BATTERY (6 metrics from german_genre_fingerprint):
  h_char_ratio, heaps_beta, hapax_ratio_mid, mean_word_len,
  zipf_alpha, ttr_5000.

VMS TARGET: same VMS_TARGET dict from german_genre_fingerprint/82.

PREDICTIONS (pre-registered skepticism):

  P1: Combined E4 (vowel expansion + positional) on Italian or German
      will achieve the closest overall distance. forward_process_models-60 showed
      this works on Italian; we test if it works BETTER on German.
      SKEPTIC: word_shape_validation showed positional entropy is anti-correlated.

  P2: No encoding on any language will push h_char BELOW 0.60.
      The VMS value (0.641) is achievable, but 0.55 would require
      implausibly strong deterministic sequences.
      SKEPTIC: If an encoding DOES get below 0.60, it means our
      h_char target may be wrong (EVA artifact).

  P3: Heaps β and Zipf α will be DESTROYED by strong encodings.
      Expansion encodings create predictable multi-char tokens that
      reduce effective vocabulary growth. The constraint is: encoding
      strong enough to hit h_char=0.641 will overshoot other metrics.
      SKEPTIC: Maybe word-level vocabulary metrics are preserved if
      encoding only operates WITHIN words.

  P4: The LANGUAGE matters more than the encoding. Languages with
      natural h_char closer to VMS will need less aggressive encoding
      to reach the target, and thus will preserve other metrics better.
      SKEPTIC: All tested NL have h_char ≈ 0.82-0.87 — the spread
      is small relative to the gap to 0.641.

  P5: German will NOT outperform Italian. Despite german_genre_fingerprint's proximity,
      the Faust-VMS match was driven by vocabulary richness (TTR/Zipf),
      not h_char. Italian (encoding_model_tournament finding) remains the best source
      candidate overall.
      SKEPTIC: Medieval German (BvgS) has different properties than
      Modern German (Faust). Must test both.
"""

import re, sys, io, math
from pathlib import Path
from collections import Counter
import numpy as np
from common import clean_word_v2 as clean_word, eva_to_glyphs, load_bvgs, load_reference_text_v2 as load_reference_text, mean_word_length, ttr_at_n

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
DATA_DIR  = Path(__file__).resolve().parent.parent / 'data'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(83)


# ═══════════════════════════════════════════════════════════════════════
# EVA PARSING (from german_genre_fingerprint)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']



def parse_vms_words():
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
# TEXT LOADING (from german_genre_fingerprint/82)
# ═══════════════════════════════════════════════════════════════════════




# ═══════════════════════════════════════════════════════════════════════
# FINGERPRINT METRICS (from german_genre_fingerprint)
# ═══════════════════════════════════════════════════════════════════════

def heaps_exponent(words):
    n = len(words)
    if n < 100:
        return float('nan')
    sample_points = np.linspace(max(10, n//20), n, min(20, n//5), dtype=int)
    if len(sample_points) < 3:
        return float('nan')
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

def hapax_ratio_at_midpoint(words):
    mid = len(words) // 2
    if mid < 10:
        return float('nan')
    freq = Counter(words[:mid])
    hapax = sum(1 for c in freq.values() if c == 1)
    return hapax / max(len(freq), 1)

def char_bigram_predictability(char_list):
    unigram = Counter(char_list)
    total = sum(unigram.values())
    if total < 50:
        return float('nan')
    h_uni = -sum((c/total) * math.log2(c/total) for c in unigram.values() if c > 0)
    bigrams = Counter()
    for i in range(1, len(char_list)):
        bigrams[(char_list[i-1], char_list[i])] += 1
    total_bi = sum(bigrams.values())
    h_joint = -sum((c/total_bi) * math.log2(c/total_bi) for c in bigrams.values() if c > 0)
    prev_counts = Counter()
    for (c1, c2), cnt in bigrams.items():
        prev_counts[c1] += cnt
    prev_total = sum(prev_counts.values())
    h_prev = -sum((c/prev_total) * math.log2(c/prev_total) for c in prev_counts.values() if c > 0)
    h_cond = h_joint - h_prev
    if h_uni == 0:
        return 1.0
    return h_cond / h_uni



def zipf_alpha_fn(words):
    freq = Counter(words)
    ranked = sorted(freq.values(), reverse=True)
    n = min(len(ranked), 500)
    if n < 10:
        return float('nan')
    log_rank = np.log(np.arange(1, n+1))
    log_freq = np.log(np.array(ranked[:n], dtype=float))
    A = np.vstack([log_rank, np.ones(n)]).T
    result = np.linalg.lstsq(A, log_freq, rcond=None)
    return float(-result[0][0])

def compute_fingerprint(words, char_list):
    return {
        'h_char_ratio': char_bigram_predictability(char_list),
        'heaps_beta': heaps_exponent(words),
        'hapax_ratio_mid': hapax_ratio_at_midpoint(words),
        'mean_word_len': mean_word_length(words),
        'zipf_alpha': zipf_alpha_fn(words),
        'ttr_5000': ttr_at_n(words, 5000),
    }


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
    dims = []
    for key, vms_val in target.items():
        v = fp.get(key, float('nan'))
        if vms_val != 0 and not math.isnan(v):
            dims.append(((v - vms_val) / vms_val) ** 2)
    return math.sqrt(sum(dims)) if dims else float('inf')


# ═══════════════════════════════════════════════════════════════════════
# ENCODING TRANSFORMATIONS
# ═══════════════════════════════════════════════════════════════════════

# Language-specific vowel sets
VOWELS = set('aeiouyàáâãäåæèéêëìíîïòóôõöùúûüý')

def identify_vowels(word):
    """Return list of (index, is_vowel) for each char in word."""
    return [(i, c in VOWELS) for i, c in enumerate(word)]


def encode_null(words):
    """E1: Identity — no transformation."""
    return words


def encode_vowel_expansion(words, expansion_prob=1.0):
    """E2: Vowel expansion — vowels become deterministic 2-char sequences.

    Each vowel maps to itself + a fixed successor char.
    e.g., 'a' → 'a1', 'e' → 'e2', 'i' → 'i3', 'o' → 'o4', 'u' → 'u5'
    The successor chars are DETERMINISTIC (always the same for a given vowel),
    which is EXACTLY what produces low h_char — the successor is perfectly
    predicted from the preceding vowel.

    expansion_prob: probability each vowel instance is expanded.
    At 1.0, all vowels expand (strongest effect on h_char).
    At 0.5, half expand (more realistic as a practical cipher).
    """
    EXPANSION = {'a': 'a1', 'e': 'e2', 'i': 'i3', 'o': 'o4', 'u': 'u5',
                 'y': 'y6', 'à': 'à1', 'á': 'á1', 'â': 'â1',
                 'ã': 'ã1', 'ä': 'ä1', 'å': 'å1', 'è': 'è2',
                 'é': 'é2', 'ê': 'ê2', 'ë': 'ë2', 'ì': 'ì3',
                 'í': 'í3', 'î': 'î3', 'ï': 'ï3', 'ò': 'ò4',
                 'ó': 'ó4', 'ô': 'ô4', 'õ': 'õ4', 'ö': 'ö4',
                 'ù': 'ù5', 'ú': 'ú5', 'û': 'û5', 'ü': 'ü5',
                 'ý': 'ý6'}
    rng = np.random.RandomState(83)
    result = []
    for w in words:
        encoded = []
        for c in w:
            if c in EXPANSION and rng.random() < expansion_prob:
                encoded.append(EXPANSION[c])
            else:
                encoded.append(c)
        result.append(''.join(encoded))
    return result


def encode_positional_sub(words, n_zones=3):
    """E3: Positional substitution — char maps depend on word position.

    Each character gets a zone-specific variant.
    initial 'a' → 'a_I', medial 'a' → 'a_M', final 'a' → 'a_F'.
    This multiplies the effective alphabet while keeping character
    predictability within zones.
    """
    result = []
    zone_labels = _zone_labels(n_zones)
    for w in words:
        n = len(w)
        encoded = []
        for i, c in enumerate(w):
            z = _get_zone(i, n, zone_labels)
            encoded.append(c + z)
        result.append(''.join(encoded))
    return result


def encode_combined(words, expansion_prob=1.0, n_zones=3):
    """E4: Combined vowel expansion + positional substitution."""
    expanded = encode_vowel_expansion(words, expansion_prob)
    return encode_positional_sub(expanded, n_zones)


def encode_bigram_collapse(words, n_merges=10):
    """E5: Merge most-frequent character bigrams into single symbols.

    This simulates a partially syllabic/abugida script where common
    pairs are written as single glyphs. Should REDUCE alphabet while
    INCREASING bigram predictability (pushing h_char DOWN).
    """
    # Find most frequent bigrams across all words
    bigram_freq = Counter()
    for w in words:
        for i in range(len(w) - 1):
            bigram_freq[(w[i], w[i+1])] += 1

    # Merge top n_merges bigrams
    merges = bigram_freq.most_common(n_merges)
    merge_pairs = [(a + b, chr(0x0100 + idx)) for idx, ((a, b), _) in enumerate(merges)]

    result = []
    for w in words:
        encoded = w
        for bigram_str, replacement in merge_pairs:
            encoded = encoded.replace(bigram_str, replacement)
        result.append(encoded)
    return result


def _zone_labels(n_zones):
    if n_zones == 2:
        return ['I', 'F']
    elif n_zones == 3:
        return ['I', 'M', 'F']
    elif n_zones == 4:
        return ['I', 'E', 'L', 'F']
    else:
        return ['I', 'E', 'M', 'L', 'F']

def _get_zone(pos, word_len, zone_labels):
    if word_len <= 1:
        return zone_labels[0]
    n = len(zone_labels)
    frac = pos / (word_len - 1)
    idx = min(int(frac * n), n - 1)
    return zone_labels[idx]


# ═══════════════════════════════════════════════════════════════════════
# PARAMETER SWEEP
# ═══════════════════════════════════════════════════════════════════════

def build_encoding_configs():
    """Build the full parameter grid for all encoding families."""
    configs = []

    # E1: Null
    configs.append(('E1_null', lambda w: encode_null(w), {}))

    # E2: Vowel expansion at different probabilities
    for p in [0.3, 0.5, 0.7, 0.85, 1.0]:
        label = f'E2_vowexp_p{p:.0%}'.replace('%', '')
        configs.append((label, lambda w, _p=p: encode_vowel_expansion(w, _p), {'exp_p': p}))

    # E3: Positional substitution at different zone counts
    for z in [2, 3, 4, 5]:
        label = f'E3_possub_z{z}'
        configs.append((label, lambda w, _z=z: encode_positional_sub(w, _z), {'zones': z}))

    # E4: Combined — grid of expansion_prob × zones
    for p in [0.5, 0.7, 1.0]:
        for z in [2, 3, 5]:
            label = f'E4_comb_p{p:.0%}z{z}'.replace('%', '')
            configs.append((label,
                            lambda w, _p=p, _z=z: encode_combined(w, _p, _z),
                            {'exp_p': p, 'zones': z}))

    # E5: Bigram collapse at different merge counts
    for m in [5, 10, 15, 20, 30]:
        label = f'E5_collapse_m{m}'
        configs.append((label, lambda w, _m=m: encode_bigram_collapse(w, _m), {'merges': m}))

    return configs


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 80)
    pr("encoding_layer_sweep — ENCODING LAYER PARAMETER SWEEP")
    pr("  What (language × encoding) minimizes distance to VMS?")
    pr("=" * 80)
    pr()

    # ── STEP 1: VMS Baseline ─────────────────────────────────────────
    pr("─" * 80)
    pr("STEP 1: VMS BASELINE")
    pr("─" * 80)
    vms_words, vms_glyphs = parse_vms_words()
    vms_fp = compute_fingerprint(vms_words, vms_glyphs)
    pr(f"  Tokens: {len(vms_words):,}   Types: {len(set(vms_words)):,}")
    pr(f"  h_char={vms_fp['h_char_ratio']:.4f}  Heaps={vms_fp['heaps_beta']:.4f}  "
       f"hapax={vms_fp['hapax_ratio_mid']:.4f}  wlen={vms_fp['mean_word_len']:.2f}  "
       f"Zipf={vms_fp['zipf_alpha']:.4f}  TTR={vms_fp['ttr_5000']:.4f}")
    pr()

    # ── STEP 2: Load reference corpora ───────────────────────────────
    pr("─" * 80)
    pr("STEP 2: REFERENCE CORPORA")
    pr("─" * 80)
    pr()

    CORPORA = [
        ("German_Faust", DATA_DIR / 'vernacular_texts' / 'german_faust.txt', 'gutenberg'),
        ("German_BvgS", DATA_DIR / 'vernacular_texts' / 'german_bvgs_raw.txt', 'bvgs'),
        ("Latin_Caesar", DATA_DIR / 'latin_texts' / 'caesar.txt', 'standard'),
        ("Latin_Vulgate", DATA_DIR / 'latin_texts' / 'vulgate_genesis.txt', 'standard'),
        ("Latin_Apicius", DATA_DIR / 'latin_texts' / 'apicius.txt', 'standard'),
        ("Italian_Cucina", DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt', 'standard'),
        ("French_Viandier", DATA_DIR / 'vernacular_texts' / 'french_viandier.txt', 'standard'),
        ("English_Cury", DATA_DIR / 'vernacular_texts' / 'english_cury.txt', 'standard'),
    ]

    loaded_corpora = {}
    for label, filepath, loader in CORPORA:
        if not filepath.exists():
            pr(f"  SKIP: {filepath.name} not found")
            continue
        if loader == 'bvgs':
            words = load_bvgs(filepath)
        else:
            words = load_reference_text(filepath)
        cap = min(len(words), 30000)
        words = words[:cap]
        if len(words) < 500:
            pr(f"  SKIP: {label} too short ({len(words)} words)")
            continue

        # Compute baseline fingerprint
        chars = list(''.join(words))
        fp = compute_fingerprint(words, chars)
        dist = fingerprint_distance(fp)
        loaded_corpora[label] = words
        pr(f"  {label:<20s} tokens={len(words):>6,}  "
           f"h_char={fp['h_char_ratio']:.4f}  "
           f"baseline_dist={dist:.4f}")

    pr(f"\n  Loaded {len(loaded_corpora)} corpora for encoding sweep.\n")

    # ── STEP 3: PARAMETER SWEEP ──────────────────────────────────────
    pr("─" * 80)
    pr("STEP 3: PARAMETER SWEEP — {0} languages × {1} encodings = {2} tests".format(
        len(loaded_corpora), len(build_encoding_configs()),
        len(loaded_corpora) * len(build_encoding_configs())))
    pr("─" * 80)
    pr()

    configs = build_encoding_configs()
    all_results = []   # (dist, label, enc_name, fp, params)

    for lang_label, words in loaded_corpora.items():
        pr(f"  Testing {lang_label}...")
        best_dist = float('inf')
        best_enc = None

        for enc_name, enc_fn, params in configs:
            try:
                encoded_words = enc_fn(words)
                encoded_chars = list(''.join(encoded_words))
                fp = compute_fingerprint(encoded_words, encoded_chars)
                dist = fingerprint_distance(fp)

                all_results.append((dist, lang_label, enc_name, fp, params))

                if dist < best_dist:
                    best_dist = dist
                    best_enc = enc_name
            except Exception as e:
                pr(f"    ERROR: {lang_label} + {enc_name}: {e}")

        pr(f"    Best: {best_enc}  dist={best_dist:.4f}")

    pr()

    # ── STEP 4: RANKED RESULTS ───────────────────────────────────────
    pr("─" * 80)
    pr("STEP 4: TOP 30 (language × encoding) COMBINATIONS")
    pr("─" * 80)
    pr()

    all_results.sort(key=lambda x: x[0])

    header = (f"  {'Rank':>4s}  {'Language':<20s}  {'Encoding':<22s}  "
              f"{'dist':>7s}  {'h_char':>7s}  {'heaps':>7s}  {'hapax':>7s}  "
              f"{'wlen':>7s}  {'zipf':>7s}  {'ttr':>7s}")
    pr(header)
    pr("  " + "─" * (len(header) - 2))

    for i, (dist, lang, enc, fp, params) in enumerate(all_results[:30], 1):
        pr(f"  {i:>4d}  {lang:<20s}  {enc:<22s}  {dist:>7.4f}  "
           f"{fp['h_char_ratio']:>7.4f}  {fp['heaps_beta']:>7.4f}  "
           f"{fp['hapax_ratio_mid']:>7.4f}  {fp['mean_word_len']:>7.2f}  "
           f"{fp['zipf_alpha']:>7.4f}  {fp['ttr_5000']:>7.4f}")

    pr()

    # VMS target row for reference
    pr(f"  {'':>4s}  {'VMS TARGET':<20s}  {'':22s}  {'0.0000':>7s}  "
       f"{VMS_TARGET['h_char_ratio']:>7.4f}  {VMS_TARGET['heaps_beta']:>7.4f}  "
       f"{VMS_TARGET['hapax_ratio_mid']:>7.4f}  {VMS_TARGET['mean_word_len']:>7.2f}  "
       f"{VMS_TARGET['zipf_alpha']:>7.4f}  {VMS_TARGET['ttr_5000']:>7.4f}")
    pr()

    # ── STEP 5: BEST PER LANGUAGE ────────────────────────────────────
    pr("─" * 80)
    pr("STEP 5: BEST ENCODING PER LANGUAGE (what does each language need?)")
    pr("─" * 80)
    pr()

    best_per_lang = {}
    for dist, lang, enc, fp, params in all_results:
        if lang not in best_per_lang or dist < best_per_lang[lang][0]:
            best_per_lang[lang] = (dist, enc, fp, params)

    pr(f"  {'Language':<20s}  {'Best Encoding':<22s}  {'dist':>7s}  "
       f"{'h_char':>7s}  {'Δh_char':>8s}  {'wlen':>7s}  {'Δwlen':>7s}")
    pr("  " + "─" * 95)

    for lang in sorted(best_per_lang.keys(), key=lambda k: best_per_lang[k][0]):
        dist, enc, fp, params = best_per_lang[lang]
        delta_h = fp['h_char_ratio'] - VMS_TARGET['h_char_ratio']
        delta_w = fp['mean_word_len'] - VMS_TARGET['mean_word_len']
        pr(f"  {lang:<20s}  {enc:<22s}  {dist:>7.4f}  "
           f"{fp['h_char_ratio']:>7.4f}  {delta_h:>+8.4f}  "
           f"{fp['mean_word_len']:>7.2f}  {delta_w:>+7.2f}")

    pr()

    # ── STEP 6: BEST PER ENCODING FAMILY ─────────────────────────────
    pr("─" * 80)
    pr("STEP 6: BEST LANGUAGE PER ENCODING FAMILY (what does each encoding do best?)")
    pr("─" * 80)
    pr()

    families = {'E1': [], 'E2': [], 'E3': [], 'E4': [], 'E5': []}
    for dist, lang, enc, fp, params in all_results:
        family = enc[:2]
        if family in families:
            families[family].append((dist, lang, enc, fp, params))

    for fam in ['E1', 'E2', 'E3', 'E4', 'E5']:
        fam_names = {'E1': 'NULL (identity)', 'E2': 'VOWEL EXPANSION',
                     'E3': 'POSITIONAL SUB', 'E4': 'COMBINED (E2+E3)',
                     'E5': 'BIGRAM COLLAPSE'}
        fam_results = sorted(families[fam], key=lambda x: x[0])
        if not fam_results:
            continue
        pr(f"  {fam} — {fam_names[fam]}:")
        for dist, lang, enc, fp, params in fam_results[:3]:
            pr(f"    {lang:<20s}  {enc:<22s}  dist={dist:.4f}  "
               f"h_char={fp['h_char_ratio']:.4f}  wlen={fp['mean_word_len']:.2f}")
        pr()

    # ── STEP 7: h_char DEEP DIVE ────────────────────────────────────
    pr("─" * 80)
    pr("STEP 7: h_char ANOMALY — WHICH ENCODINGS APPROACH 0.641?")
    pr("─" * 80)
    pr()

    pr("  Closest to VMS h_char (0.641), regardless of other metrics:")
    hchar_sorted = sorted(all_results, key=lambda x: abs(x[3]['h_char_ratio'] - 0.641))
    for i, (dist, lang, enc, fp, params) in enumerate(hchar_sorted[:15], 1):
        delta = fp['h_char_ratio'] - 0.641
        pr(f"    {i:>2d}. {lang:<20s} {enc:<22s} h_char={fp['h_char_ratio']:.4f} "
           f"(Δ={delta:>+.4f})  overall_dist={dist:.4f}")

    pr()

    # Check: does ANY encoding get h_char below 0.70?
    sub_070 = [(d, l, e, f, p) for d, l, e, f, p in all_results if f['h_char_ratio'] < 0.70]
    pr(f"  Encodings achieving h_char < 0.70: {len(sub_070)} / {len(all_results)}")
    if sub_070:
        for dist, lang, enc, fp, params in sorted(sub_070, key=lambda x: x[3]['h_char_ratio'])[:10]:
            pr(f"    {lang:<20s} {enc:<22s} h_char={fp['h_char_ratio']:.4f}  "
               f"dist={dist:.4f}  heaps={fp['heaps_beta']:.4f}  "
               f"zipf={fp['zipf_alpha']:.4f}")
    else:
        pr("    NONE — h_char anomaly persists under all tested encodings!")
    pr()

    # ── STEP 8: THE ENCODING-LANGUAGE CONSTRAINT MATRIX ──────────────
    pr("─" * 80)
    pr("STEP 8: CONSTRAINT ANALYSIS — What the sweep tells us")
    pr("─" * 80)
    pr()

    # Analyze which metric is the binding constraint for the top results
    pr("  Which metric kills the top-ranked (lang × encoding) combos?")
    pr("  (Largest normalized deviation from VMS target)")
    pr()
    for i, (dist, lang, enc, fp, params) in enumerate(all_results[:10], 1):
        worst_metric = None
        worst_dev = 0
        for key, vms_val in VMS_TARGET.items():
            v = fp.get(key, float('nan'))
            if not math.isnan(v) and vms_val != 0:
                dev = abs((v - vms_val) / vms_val)
                if dev > worst_dev:
                    worst_dev = dev
                    worst_metric = key
        pr(f"    {i:>2d}. {lang:<20s} {enc:<22s} dist={dist:.4f}  "
           f"WORST: {worst_metric} (Δ={worst_dev:.3f})")
    pr()

    # ── STEP 9: PREDICTION TESTS ────────────────────────────────────
    pr("─" * 80)
    pr("STEP 9: PREDICTION TESTS")
    pr("─" * 80)
    pr()

    top_result = all_results[0] if all_results else None
    top_hchar = hchar_sorted[0] if hchar_sorted else None

    # P1: Does E4 (combined) on Italian/German win?
    pr("  P1: Does COMBINED encoding (E4) win?")
    if top_result:
        is_e4 = top_result[2].startswith('E4')
        is_it_or_de = 'Italian' in top_result[1] or 'German' in top_result[1]
        pr(f"      Winner: {top_result[1]} + {top_result[2]} (dist={top_result[0]:.4f})")
        pr(f"      VERDICT: {'CONFIRMED' if is_e4 and is_it_or_de else 'REFUTED'}")
    pr()

    # P2: Does any encoding push h_char below 0.60?
    pr("  P2: Can any encoding push h_char below 0.60?")
    sub_060 = [r for r in all_results if r[3]['h_char_ratio'] < 0.60]
    if sub_060:
        pr(f"      YES — {len(sub_060)} combos achieve h_char < 0.60")
        pr(f"      VERDICT: REFUTED — target may be reachable")
    else:
        pr(f"      NO — minimum h_char = {hchar_sorted[0][3]['h_char_ratio']:.4f}")
        pr(f"      VERDICT: CONFIRMED — 0.60 is a floor for tested encodings")
    pr()

    # P3: Do strong encodings destroy Heaps/Zipf?
    pr("  P3: Do strong encodings (E2 p=1.0, E4) destroy vocabulary metrics?")
    strong_encs = [r for r in all_results
                   if 'p100' in r[2] or r[2].startswith('E4')]
    if strong_encs:
        heaps_vals = [r[3]['heaps_beta'] for r in strong_encs
                      if not math.isnan(r[3]['heaps_beta'])]
        zipf_vals = [r[3]['zipf_alpha'] for r in strong_encs
                     if not math.isnan(r[3]['zipf_alpha'])]
        if heaps_vals:
            pr(f"      Heaps β range under strong encoding: "
               f"[{min(heaps_vals):.4f}, {max(heaps_vals):.4f}]  "
               f"(VMS: {VMS_TARGET['heaps_beta']:.4f})")
        if zipf_vals:
            pr(f"      Zipf α range under strong encoding: "
               f"[{min(zipf_vals):.4f}, {max(zipf_vals):.4f}]  "
               f"(VMS: {VMS_TARGET['zipf_alpha']:.4f})")
        # Are they within 20% of VMS?
        heaps_ok = any(abs(v - VMS_TARGET['heaps_beta'])/VMS_TARGET['heaps_beta'] < 0.20
                       for v in heaps_vals)
        zipf_ok = any(abs(v - VMS_TARGET['zipf_alpha'])/VMS_TARGET['zipf_alpha'] < 0.20
                      for v in zipf_vals)
        pr(f"      Heaps preserved (<20% deviation): {'YES' if heaps_ok else 'NO'}")
        pr(f"      Zipf preserved (<20% deviation): {'YES' if zipf_ok else 'NO'}")
        pr(f"      VERDICT: {'REFUTED — metrics preserved!' if heaps_ok and zipf_ok else 'CONFIRMED — encoding damages vocabulary growth'}")
    pr()

    # P4: Does language matter more than encoding?
    pr("  P4: Does LANGUAGE matter more than ENCODING?")
    # Compute per-language best distance and per-encoding best distance
    lang_bests = {}
    enc_bests = {}
    for dist, lang, enc, fp, params in all_results:
        fam = enc[:2]
        if lang not in lang_bests or dist < lang_bests[lang]:
            lang_bests[lang] = dist
        if fam not in enc_bests or dist < enc_bests[fam]:
            enc_bests[fam] = dist
    lang_spread = max(lang_bests.values()) - min(lang_bests.values())
    enc_spread = max(enc_bests.values()) - min(enc_bests.values())
    pr(f"      Language best-distance spread: {lang_spread:.4f}")
    pr(f"      Encoding best-distance spread: {enc_spread:.4f}")
    pr(f"      VERDICT: {'CONFIRMED — language variation > encoding variation' if lang_spread > enc_spread else 'REFUTED — encoding matters more than language'}")
    pr()

    # P5: Does Italian beat German?
    pr("  P5: Does Italian outperform German overall?")
    it_best = best_per_lang.get('Italian_Cucina', (float('inf'),))[0]
    de_faust_best = best_per_lang.get('German_Faust', (float('inf'),))[0]
    de_bvgs_best = best_per_lang.get('German_BvgS', (float('inf'),))[0]
    pr(f"      Italian Cucina best:  {it_best:.4f}")
    pr(f"      German Faust best:   {de_faust_best:.4f}")
    pr(f"      German BvgS best:    {de_bvgs_best:.4f}")
    if it_best < de_faust_best and it_best < de_bvgs_best:
        pr(f"      VERDICT: CONFIRMED — Italian remains best source candidate")
    else:
        winner = "Faust" if de_faust_best < de_bvgs_best else "BvgS"
        pr(f"      VERDICT: REFUTED — German ({winner}) beats Italian!")
    pr()

    # ── STEP 10: CRITICAL SYNTHESIS ──────────────────────────────────
    pr("─" * 80)
    pr("STEP 10: CRITICAL SYNTHESIS")
    pr("─" * 80)
    pr()

    pr("  1. THE h_char CONSTRAINT:")
    if sub_070:
        pr(f"     {len(sub_070)} encoding(s) achieve h_char < 0.70.")
        best_hchar_result = sorted(sub_070, key=lambda x: abs(x[3]['h_char_ratio'] - 0.641))[0]
        pr(f"     Closest to 0.641: {best_hchar_result[1]} + {best_hchar_result[2]}")
        pr(f"     h_char={best_hchar_result[3]['h_char_ratio']:.4f}, "
           f"BUT overall dist={best_hchar_result[0]:.4f}")
        pr(f"     → The encoding that fixes h_char BREAKS other metrics.")
    else:
        pr(f"     NO encoding achieves h_char < 0.70. Tested range: "
           f"{hchar_sorted[0][3]['h_char_ratio']:.4f} to "
           f"{hchar_sorted[-1][3]['h_char_ratio']:.4f}")
        pr(f"     → The h_char anomaly cannot be reproduced by simple")
        pr(f"       vowel expansion, positional substitution, bigram collapse,")
        pr(f"       or their combination. A MORE COMPLEX mechanism is needed.")
    pr()

    pr("  2. OVERALL WINNER:")
    if top_result:
        pr(f"     {top_result[1]} + {top_result[2]} at dist={top_result[0]:.4f}")
        pr(f"     Fingerprint: h_char={top_result[3]['h_char_ratio']:.4f}  "
           f"heaps={top_result[3]['heaps_beta']:.4f}  "
           f"wlen={top_result[3]['mean_word_len']:.2f}")
    pr()

    pr("  3. LANGUAGE RANKING (best achievable distance under ANY encoding):")
    for lang in sorted(best_per_lang.keys(), key=lambda k: best_per_lang[k][0]):
        dist, enc, fp, params = best_per_lang[lang]
        pr(f"     {lang:<20s}  {dist:.4f}  (via {enc})")
    pr()

    pr("  4. WHAT THIS MEANS FOR DECIPHERMENT:")
    pr(f"     The (language, encoding) approach reveals the VMS fingerprint's")
    pr(f"     achievability envelope: how close can any known language GET to")
    pr(f"     VMS under parametric encoding. The gap between the best result")
    if top_result:
        pr(f"     ({top_result[0]:.4f}) and zero is the RESIDUAL that must be")
    pr(f"     explained by either:")
    pr(f"       a) The correct source language not being in our corpus")
    pr(f"       b) A more sophisticated encoding than tested here")
    pr(f"       c) Properties of the VMS script itself (EVA artifacts)")
    pr(f"       d) VMS being a constructed system, not encoded NL")
    pr()

    # ── Save results ─────────────────────────────────────────────────
    outpath = RESULTS_DIR / 'encoding_layer_sweep_encoding_sweep.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.writelines(OUTPUT)
    pr(f"  Results saved to {outpath.name}")


if __name__ == '__main__':
    main()
