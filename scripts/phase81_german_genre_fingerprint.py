#!/usr/bin/env python3
"""
Phase 81 — Medieval German Genre-Matched Fingerprint Test

═══════════════════════════════════════════════════════════════════════

MOTIVATION: Four independent lines of evidence converge on a German
recipe/medical origin for the VMS:

  1. PALEOGRAPHIC: Handwriting analysis (382 samples, 33 properties)
     → 7/10 best matches from Fulda/Mainz, central Germany.
  2. LINGUISTIC: f116v marginalia → German recipe language ("boxleber"
     = buck's liver, "sonim gasmich" = then take goat's milk).
  3. GENRE: VMS statistical fingerprint (word length ~5, high hapax,
     moderate Zipf) is consistent with recipe/instructional text.
  4. PHASE 58: German (Goethe's Faust) ranked 4th closest to VMS
     at distance 2.893 — but that was modern literary German, not
     genre-matched.

HYPOTHESIS: If VMS encodes medieval German recipe/medical text, then
a 14th-century German cookbook should produce the CLOSEST fingerprint
match to VMS across all reference corpora.

TEST DESIGN:
  ┌─────────────────────────────────────────────────────────────┐
  │ RECIPE TEXTS (genre-matched):                               │
  │   • German: Buch von guter Speise (~1350, MHG cookbook)     │
  │   • Latin:  Apicius (ancient Roman cookbook)                 │
  │   • Italian: Il libro della cucina (14th c. Italian)        │
  │   • French: Le Viandier (medieval French)                   │
  │   • English: Forme of Cury (medieval English)               │
  │                                                             │
  │ LITERARY/OTHER TEXTS (genre controls):                      │
  │   • German: Goethe's Faust (modern literary)                │
  │   • Latin:  Caesar's Gallic Wars (classical literary)       │
  │   • Latin:  Vulgate Genesis (religious)                     │
  │                                                             │
  │ TARGET: VMS (EVA transcription, 40K+ tokens)                │
  └─────────────────────────────────────────────────────────────┘

PREDICTIONS (ranked by specificity):
  P1: Recipe texts should be systematically closer to VMS than
      literary texts (genre effect > 0).
  P2: German recipe text should be the single closest match.
  P3: Medieval texts should be closer than modern texts (period effect).
  P4: The genre effect should be larger than the language effect.

SKEPTICISM CHECKLIST:
  ✗ Paleographic origin ≠ language origin (scribe could copy any text)
  ✗ f116v marginalia are SEPARATE from main VMS text (could be unrelated)
  ✗ No raw natural language matches VMS h_char (0.641) — even the best
    match will be ~0.85+. This tests RELATIVE closeness, not identity.
  ✗ Small corpus sizes may produce unstable fingerprints.
  ✗ OCR artifacts in the BvgS text need careful cleaning.
"""

import re, sys, io, math
from pathlib import Path
from collections import Counter
import numpy as np
from common import char_bigram_predictability, clean_word_v2 as clean_word, eva_to_glyphs, hapax_ratio_at_midpoint, index_of_coincidence, load_bvgs, load_reference_text_v2 as load_reference_text, mean_word_length, ttr_at_n, zipf_alpha

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
DATA_DIR  = Path(__file__).resolve().parent.parent / 'data'
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
# TEXT LOADING
# ═══════════════════════════════════════════════════════════════════════





# ═══════════════════════════════════════════════════════════════════════
# FINGERPRINT FUNCTIONS (from Phase 80)
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


def compute_fingerprint(words, char_list, label):
    """Compute the full statistical fingerprint."""
    return {
        'label': label,
        'n_tokens': len(words),
        'n_types': len(set(words)),
        'alphabet_size': len(set(char_list)),
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

def dimension_delta(fp, dim_key, target=VMS_TARGET):
    """Normalised deviation on a single dimension."""
    if dim_key in fp and dim_key in target and target[dim_key] != 0:
        return (fp[dim_key] - target[dim_key]) / target[dim_key]
    return float('nan')


# ═══════════════════════════════════════════════════════════════════════
# BOOTSTRAP CONFIDENCE INTERVALS
# ═══════════════════════════════════════════════════════════════════════

def bootstrap_distance(words, n_boot=200, sample_frac=0.8):
    """Bootstrap the fingerprint distance to get confidence interval."""
    n = len(words)
    sample_size = int(n * sample_frac)
    distances = []
    for _ in range(n_boot):
        idx = np.random.choice(n, sample_size, replace=True)
        sample_words = [words[i] for i in idx]
        sample_chars = list(''.join(sample_words))
        fp = compute_fingerprint(sample_words, sample_chars, "boot")
        distances.append(fingerprint_distance(fp))
    return np.mean(distances), np.percentile(distances, 2.5), np.percentile(distances, 97.5)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 76)
    pr("PHASE 81 — MEDIEVAL GERMAN GENRE-MATCHED FINGERPRINT TEST")
    pr("=" * 76)
    pr()
    pr("  Testing whether medieval German recipe text produces the closest")
    pr("  statistical fingerprint match to VMS across all reference corpora.")
    pr()

    # ── STEP 1: Load VMS ──────────────────────────────────────────────
    pr("─" * 76)
    pr("STEP 1: VMS BASELINE")
    pr("─" * 76)
    vms_words, vms_glyphs = parse_vms_words()
    vms_fp = compute_fingerprint(vms_words, vms_glyphs, "VMS")
    pr(f"  Tokens: {vms_fp['n_tokens']:,}   Types: {vms_fp['n_types']:,}   "
       f"Alphabet: {vms_fp['alphabet_size']}")
    pr(f"  h_char={vms_fp['h_char_ratio']:.4f}  Heaps={vms_fp['heaps_beta']:.4f}  "
       f"hapax={vms_fp['hapax_ratio_mid']:.4f}  wlen={vms_fp['mean_word_len']:.2f}  "
       f"Zipf={vms_fp['zipf_alpha']:.4f}  TTR={vms_fp['ttr_5000']:.4f}  "
       f"IC={vms_fp['ic']:.5f}")
    pr()

    vms_wld = word_length_distribution(vms_words)

    # ── STEP 2: Load all reference corpora ────────────────────────────
    pr("─" * 76)
    pr("STEP 2: REFERENCE CORPORA")
    pr("─" * 76)
    pr()

    # Define corpora with metadata
    CORPORA = [
        # (label, filepath, genre, language, period, loader)
        ("German BvgS", DATA_DIR / 'vernacular_texts' / 'german_bvgs_raw.txt',
         'recipe', 'German', 'medieval', 'bvgs'),
        ("Latin Apicius", DATA_DIR / 'latin_texts' / 'apicius.txt',
         'recipe', 'Latin', 'ancient', 'standard'),
        ("Italian Cucina", DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt',
         'recipe', 'Italian', 'medieval', 'standard'),
        ("French Viandier", DATA_DIR / 'vernacular_texts' / 'french_viandier.txt',
         'recipe', 'French', 'medieval', 'standard'),
        ("English Cury", DATA_DIR / 'vernacular_texts' / 'english_cury.txt',
         'recipe', 'English', 'medieval', 'standard'),
        ("German Faust", DATA_DIR / 'vernacular_texts' / 'german_faust.txt',
         'literary', 'German', 'modern', 'gutenberg'),
        ("Latin Caesar", DATA_DIR / 'latin_texts' / 'caesar.txt',
         'literary', 'Latin', 'ancient', 'standard'),
        ("Latin Vulgate", DATA_DIR / 'latin_texts' / 'vulgate_genesis.txt',
         'religious', 'Latin', 'ancient', 'standard'),
    ]

    results = []  # (label, genre, language, period, fp, distance, words)

    for label, filepath, genre, language, period, loader in CORPORA:
        if not filepath.exists():
            pr(f"  SKIP: {filepath.name} not found")
            continue

        if loader == 'bvgs':
            words = load_bvgs(filepath)
        else:
            words = load_reference_text(filepath)

        if len(words) < 200:
            pr(f"  SKIP: {label} too short ({len(words)} words)")
            continue

        # Cap to comparable size
        cap = min(len(words), 40000)
        words = words[:cap]
        chars = list(''.join(words))
        fp = compute_fingerprint(words, chars, label)
        dist = fingerprint_distance(fp)

        results.append((label, genre, language, period, fp, dist, words))

        pr(f"  {label:<20s} [{genre:<8s}] [{language:<8s}] [{period:<8s}]")
        pr(f"    {fp['n_tokens']:>6,} tokens, {fp['n_types']:>5,} types, "
           f"alphabet={fp['alphabet_size']}")
        pr(f"    h_char={fp['h_char_ratio']:.4f}  Heaps={fp['heaps_beta']:.4f}  "
           f"hapax={fp['hapax_ratio_mid']:.4f}  wlen={fp['mean_word_len']:.2f}  "
           f"Zipf={fp['zipf_alpha']:.4f}  TTR={fp['ttr_5000']:.4f}  "
           f"IC={fp['ic']:.5f}")
        pr(f"    Distance to VMS: {dist:.4f}")
        pr()

    # ── STEP 3: RANKED DISTANCE TABLE ─────────────────────────────────
    pr("─" * 76)
    pr("STEP 3: RANKED DISTANCE TO VMS (closest first)")
    pr("─" * 76)
    pr()

    pr(f"  VMS TARGET: h_char={VMS_TARGET['h_char_ratio']:.3f}  "
       f"Heaps={VMS_TARGET['heaps_beta']:.3f}  "
       f"hapax={VMS_TARGET['hapax_ratio_mid']:.3f}  "
       f"wlen={VMS_TARGET['mean_word_len']:.2f}  "
       f"Zipf={VMS_TARGET['zipf_alpha']:.3f}  "
       f"TTR={VMS_TARGET['ttr_5000']:.3f}")
    pr()

    ranked = sorted(results, key=lambda r: r[5])

    pr(f"  {'Rank':>4s}  {'Corpus':<20s} {'Genre':<9s} {'Language':<9s} "
       f"{'Period':<9s} {'Distance':>8s}")
    pr(f"  {'─'*4}  {'─'*20} {'─'*9} {'─'*9} {'─'*9} {'─'*8}")

    for i, (label, genre, language, period, fp, dist, _) in enumerate(ranked, 1):
        marker = " ★" if genre == 'recipe' and language == 'German' else ""
        pr(f"  {i:>4d}  {label:<20s} {genre:<9s} {language:<9s} "
           f"{period:<9s} {dist:>8.4f}{marker}")
    pr()

    # ── STEP 4: PREDICTION TESTS ─────────────────────────────────────
    pr("─" * 76)
    pr("STEP 4: PREDICTION TESTS")
    pr("─" * 76)
    pr()

    # P1: Recipe vs non-recipe (genre effect)
    recipe_dists = [r[5] for r in results if r[1] == 'recipe']
    nonrecipe_dists = [r[5] for r in results if r[1] != 'recipe']

    recipe_mean = np.mean(recipe_dists) if recipe_dists else float('inf')
    nonrecipe_mean = np.mean(nonrecipe_dists) if nonrecipe_dists else float('inf')

    pr("  P1: GENRE EFFECT — Are recipe texts closer to VMS?")
    pr(f"      Mean distance (recipe):     {recipe_mean:.4f}  (n={len(recipe_dists)})")
    pr(f"      Mean distance (non-recipe): {nonrecipe_mean:.4f}  (n={len(nonrecipe_dists)})")
    pr(f"      Genre effect: {nonrecipe_mean - recipe_mean:+.4f}")
    p1_pass = recipe_mean < nonrecipe_mean
    pr(f"      VERDICT: {'CONFIRMED — recipe texts are closer' if p1_pass else 'REFUTED — non-recipe texts are closer'}")
    pr()

    # P2: Is German recipe the closest?
    closest = ranked[0] if ranked else None
    pr("  P2: GERMAN RECIPE CLOSEST — Is BvgS ranked #1?")
    if closest:
        pr(f"      Closest corpus: {closest[0]} (distance {closest[5]:.4f})")
        p2_pass = closest[2] == 'German' and closest[1] == 'recipe'
        pr(f"      VERDICT: {'CONFIRMED — German recipe is #1' if p2_pass else 'REFUTED — German recipe is NOT #1'}")
        if not p2_pass:
            # Find where German recipe actually ranks
            for i, r in enumerate(ranked, 1):
                if r[2] == 'German' and r[1] == 'recipe':
                    pr(f"      (German recipe ranks #{i} at distance {r[5]:.4f})")
                    break
    pr()

    # P3: Medieval vs modern (period effect)
    medieval_dists = [r[5] for r in results if r[3] == 'medieval']
    modern_dists = [r[5] for r in results if r[3] == 'modern']
    ancient_dists = [r[5] for r in results if r[3] == 'ancient']

    pr("  P3: PERIOD EFFECT — Are medieval texts closer to VMS?")
    if medieval_dists:
        pr(f"      Mean distance (medieval): {np.mean(medieval_dists):.4f}  (n={len(medieval_dists)})")
    if modern_dists:
        pr(f"      Mean distance (modern):   {np.mean(modern_dists):.4f}  (n={len(modern_dists)})")
    if ancient_dists:
        pr(f"      Mean distance (ancient):  {np.mean(ancient_dists):.4f}  (n={len(ancient_dists)})")
    p3_pass = (medieval_dists and modern_dists and
               np.mean(medieval_dists) < np.mean(modern_dists))
    pr(f"      VERDICT: {'CONFIRMED — medieval closer than modern' if p3_pass else 'MIXED or INSUFFICIENT DATA'}")
    pr()

    # P4: Genre effect vs language effect
    # Compare German recipe vs German literary (genre effect within language)
    german_recipe = [r for r in results if r[2] == 'German' and r[1] == 'recipe']
    german_literary = [r for r in results if r[2] == 'German' and r[1] != 'recipe']
    # Compare German recipe vs Latin recipe (language effect within genre)
    latin_recipe = [r for r in results if r[2] == 'Latin' and r[1] == 'recipe']

    pr("  P4: GENRE vs LANGUAGE EFFECT")
    p4_pass = False
    if german_recipe and german_literary:
        genre_effect = german_literary[0][5] - german_recipe[0][5]
        pr(f"      German recipe: {german_recipe[0][5]:.4f}")
        pr(f"      German literary: {german_literary[0][5]:.4f}")
        pr(f"      Genre effect (within German): {genre_effect:+.4f}")
        if genre_effect > 0:
            pr(f"      → Recipe is closer than literary (supports hypothesis)")
        else:
            pr(f"      → Literary is CLOSER than recipe (AGAINST hypothesis)")
    if german_recipe and latin_recipe:
        lang_effect = latin_recipe[0][5] - german_recipe[0][5]
        pr(f"      Latin recipe: {latin_recipe[0][5]:.4f}")
        pr(f"      Language effect (within recipe): {lang_effect:+.4f}")
        if lang_effect > 0:
            pr(f"      → German recipe closer than Latin recipe (supports hypothesis)")
        else:
            pr(f"      → Latin recipe is CLOSER than German recipe (AGAINST hypothesis)")
    if german_recipe and german_literary and latin_recipe:
        # P4 is CONFIRMED only if genre effect favors recipe AND is larger
        genre_favors_recipe = genre_effect > 0
        lang_favors_german = lang_effect > 0
        p4_pass = genre_favors_recipe and abs(genre_effect) > abs(lang_effect)
        if genre_favors_recipe:
            pr(f"      VERDICT: {'GENRE DOMINANT — recipe closer' if p4_pass else 'LANGUAGE DOMINANT'}"
               f" (genre={genre_effect:+.4f}, language={lang_effect:+.4f})")
        else:
            pr(f"      VERDICT: REFUTED — genre effect goes WRONG DIRECTION"
               f" (literary closer by {abs(genre_effect):.4f})")
    pr()

    # ── STEP 5: DIMENSION-BY-DIMENSION ANALYSIS ──────────────────────
    pr("─" * 76)
    pr("STEP 5: DIMENSION-BY-DIMENSION ANALYSIS")
    pr("─" * 76)
    pr()

    dims = ['h_char_ratio', 'heaps_beta', 'hapax_ratio_mid',
            'mean_word_len', 'zipf_alpha', 'ttr_5000']
    dim_short = ['h_char', 'Heaps', 'hapax', 'wlen', 'Zipf', 'TTR']

    pr(f"  {'Corpus':<20s}", end='')
    for d in dim_short:
        pr(f"  {d:>8s}", end='')
    pr(f"  {'DIST':>8s}")

    pr(f"  {'─'*20}", end='')
    for _ in dim_short:
        pr(f"  {'─'*8}", end='')
    pr(f"  {'─'*8}")

    # VMS target row
    pr(f"  {'VMS TARGET':<20s}", end='')
    for d in dims:
        pr(f"  {VMS_TARGET[d]:>8.3f}", end='')
    pr(f"  {'—':>8s}")

    for label, genre, language, period, fp, dist, _ in ranked:
        tag = f"{label}"
        pr(f"  {tag:<20s}", end='')
        for d in dims:
            val = fp[d]
            vms = VMS_TARGET[d]
            dev = abs(val - vms) / vms
            # Color code: close (<10%) = bold, moderate (10-25%) = normal, far (>25%) = dim
            if dev < 0.10:
                pr(f"  {val:>7.3f}*", end='')
            elif dev < 0.25:
                pr(f"  {val:>8.3f}", end='')
            else:
                pr(f"  {val:>7.3f}!", end='')
            pass
        pr(f"  {dist:>8.4f}")
    pr()
    pr("  Key: * = within 10% of VMS, ! = more than 25% from VMS, (blank) = 10-25%")
    pr()

    # ── STEP 6: WORD LENGTH DISTRIBUTION COMPARISON ───────────────────
    pr("─" * 76)
    pr("STEP 6: WORD LENGTH DISTRIBUTION COMPARISON")
    pr("─" * 76)
    pr()

    pr(f"  {'Corpus':<20s} {'WLD L1 dist':>12s}")
    pr(f"  {'─'*20} {'─'*12}")

    wld_results = []
    for label, genre, language, period, fp, dist, words in ranked:
        wld = word_length_distribution(words)
        wld_d = wld_distance(vms_wld, wld)
        wld_results.append((label, wld_d, wld))
        pr(f"  {label:<20s} {wld_d:>12.4f}")

    pr()

    # Show VMS WLD and best match side by side
    if wld_results:
        best_wld = min(wld_results, key=lambda x: x[1])
        pr(f"  WLD comparison: VMS vs {best_wld[0]} (closest WLD match)")
        pr(f"    {'Len':>4s}  {'VMS':>6s}  {best_wld[0][:12]:>12s}")
        for l in range(1, 12):
            v = vms_wld.get(l, 0)
            b = best_wld[2].get(l, 0)
            v_bar = '█' * int(v * 60)
            b_bar = '░' * int(b * 60)
            pr(f"    {l:>4d}  {v:.3f}  {b:.3f}  VMS: {v_bar}")
            pr(f"    {'':>4s}  {'':>6s}  {'':>12s}  ref: {b_bar}")
    pr()

    # ── STEP 7: BOOTSTRAP CONFIDENCE ─────────────────────────────────
    pr("─" * 76)
    pr("STEP 7: BOOTSTRAP CONFIDENCE INTERVALS (200 resamples)")
    pr("─" * 76)
    pr()
    pr("  Testing stability of distance rankings with resampling...")
    pr()

    boot_results = []
    for label, genre, language, period, fp, dist, words in results:
        if len(words) >= 500:
            mean_d, lo, hi = bootstrap_distance(words, n_boot=200)
            boot_results.append((label, mean_d, lo, hi, dist))
            pr(f"  {label:<20s}  point={dist:.4f}  boot_mean={mean_d:.4f}  "
               f"95%CI=[{lo:.4f}, {hi:.4f}]")

    pr()

    # Check if rankings are stable
    if len(boot_results) >= 2:
        boot_ranked = sorted(boot_results, key=lambda x: x[1])
        pr(f"  Bootstrap ranking (by mean):")
        for i, (label, mean_d, lo, hi, _) in enumerate(boot_ranked, 1):
            pr(f"    #{i}: {label:<20s}  mean={mean_d:.4f}  [{lo:.4f}, {hi:.4f}]")

        # Check overlap between #1 and #2
        if len(boot_ranked) >= 2:
            r1 = boot_ranked[0]
            r2 = boot_ranked[1]
            overlap = r1[3] > r2[2]  # r1.hi > r2.lo
            pr()
            if overlap:
                pr(f"  ⚠ WARNING: CIs overlap between #{1} ({r1[0]}) and #{2} ({r2[0]})")
                pr(f"    Ranking difference is NOT statistically robust.")
            else:
                pr(f"  Rankings are stable — no CI overlap between #{1} and #{2}.")
    pr()

    # ── STEP 7b: SIZE-NORMALIZED COMPARISON ───────────────────────────
    pr("─" * 76)
    pr("STEP 7b: SIZE-NORMALIZED COMPARISON (all corpora subsampled)")
    pr("─" * 76)
    pr()
    pr("  BvgS has only ~8K tokens vs 14-40K for others.")
    pr("  Heaps β, hapax ratio, and TTR are all sensitive to corpus size.")
    pr("  To remove this confound, subsample all corpora to BvgS's size.")
    pr()

    # Find the smallest corpus size
    min_size = min(len(w) for _, _, _, _, _, _, w in results)
    pr(f"  Subsampling all corpora to {min_size:,} tokens (BvgS size)")
    pr(f"  Using 50 random subsamples per corpus, averaging distances.")
    pr()

    n_subsamples = 50
    normalized_results = []

    for label, genre, language, period, fp, dist, words in results:
        n = len(words)
        if n <= min_size:
            # Already at or below target size — just compute once
            chars = list(''.join(words[:min_size]))
            sub_fp = compute_fingerprint(words[:min_size], chars, label)
            sub_dist = fingerprint_distance(sub_fp)
            normalized_results.append((label, genre, language, sub_dist, dist))
        else:
            # Subsample repeatedly and average
            sub_dists = []
            for _ in range(n_subsamples):
                idx = np.random.choice(n, min_size, replace=False)
                idx.sort()
                sub_words = [words[i] for i in idx]
                sub_chars = list(''.join(sub_words))
                sub_fp = compute_fingerprint(sub_words, sub_chars, label)
                sub_dists.append(fingerprint_distance(sub_fp))
            mean_sub = np.mean(sub_dists)
            normalized_results.append((label, genre, language, mean_sub, dist))

    norm_ranked = sorted(normalized_results, key=lambda r: r[3])

    pr(f"  {'Rank':>4s}  {'Corpus':<20s} {'Genre':<9s} {'Norm Dist':>10s} "
       f"{'Full Dist':>10s} {'Delta':>8s}")
    pr(f"  {'─'*4}  {'─'*20} {'─'*9} {'─'*10} {'─'*10} {'─'*8}")

    for i, (label, genre, language, norm_d, full_d) in enumerate(norm_ranked, 1):
        delta = norm_d - full_d
        marker = " ★" if genre == 'recipe' and language == 'German' else ""
        pr(f"  {i:>4d}  {label:<20s} {genre:<9s} {norm_d:>10.4f} "
           f"{full_d:>10.4f} {delta:>+8.4f}{marker}")

    pr()

    # Retest P1 with normalized distances
    norm_recipe = [r[3] for r in normalized_results if r[1] == 'recipe']
    norm_nonrecipe = [r[3] for r in normalized_results if r[1] != 'recipe']
    if norm_recipe and norm_nonrecipe:
        nr_mean = np.mean(norm_recipe)
        nnr_mean = np.mean(norm_nonrecipe)
        pr(f"  SIZE-NORMALIZED P1: recipe mean={nr_mean:.4f}  "
           f"non-recipe mean={nnr_mean:.4f}  "
           f"{'RECIPE CLOSER' if nr_mean < nnr_mean else 'NON-RECIPE CLOSER'}")

    # Retest P2 with normalized
    if norm_ranked:
        pr(f"  SIZE-NORMALIZED P2: #1 is {norm_ranked[0][0]} "
           f"({norm_ranked[0][1]}, {norm_ranked[0][2]}) "
           f"at distance {norm_ranked[0][3]:.4f}")
        for i, r in enumerate(norm_ranked, 1):
            if r[2] == 'German' and r[1] == 'recipe':
                pr(f"  SIZE-NORMALIZED P2: German recipe ranks #{i} "
                   f"at distance {r[3]:.4f}")
                break
    pr()

    # ── STEP 8: SPECIFIC ANOMALY CHECK ────────────────────────────────
    pr("─" * 76)
    pr("STEP 8: h_char ANOMALY — DOES ANY CORPUS APPROACH 0.641?")
    pr("─" * 76)
    pr()
    pr("  VMS h_char (H(c|prev)/H(c)) = 0.641 — the signature anomaly.")
    pr("  No natural language or encoding model has reproduced this (Phase 59).")
    pr("  All natural languages cluster around 0.82-0.90.")
    pr()

    for label, genre, language, period, fp, dist, _ in ranked:
        dev_pct = 100 * abs(fp['h_char_ratio'] - 0.641) / 0.641
        pr(f"  {label:<20s}  h_char={fp['h_char_ratio']:.4f}  "
           f"deviation={dev_pct:.1f}%")
    pr()
    pr("  NOTE: This confirms that h_char anomaly remains unexplained.")
    pr("  Even the closest match is ~25-40% away from VMS value.")
    pr("  Phase 81 tests RELATIVE closeness, not identity.")
    pr()

    # ── STEP 9: SYNTHESIS ─────────────────────────────────────────────
    pr("─" * 76)
    pr("STEP 9: SYNTHESIS AND CRITICAL ASSESSMENT")
    pr("─" * 76)
    pr()

    n_predictions = 4
    n_confirmed = sum([p1_pass,
                       p2_pass if closest else False,
                       p3_pass,
                       p4_pass if
                        (german_recipe and german_literary and latin_recipe) else False])

    pr(f"  PREDICTIONS TESTED: {n_predictions}")
    pr(f"  CONFIRMED: {n_confirmed}")
    pr(f"  REFUTED: {n_predictions - n_confirmed}")
    pr()

    pr("  P1 (recipe closer than literary):    "
       f"{'CONFIRMED ✓' if p1_pass else 'REFUTED ✗'}")
    pr("  P2 (German recipe is #1):            "
       f"{'CONFIRMED ✓' if (closest and p2_pass) else 'REFUTED ✗'}")
    pr("  P3 (medieval closer than modern):    "
       f"{'CONFIRMED ✓' if p3_pass else 'MIXED/REFUTED ✗'}")
    if german_recipe and german_literary and latin_recipe:
        pr("  P4 (genre > language effect):        "
           f"{'CONFIRMED ✓' if p4_pass else 'REFUTED ✗'}")
    pr()

    # Critical caveats
    pr("  CRITICAL CAVEATS:")
    pr("  1. The h_char anomaly (0.641) remains unexplained by ANY natural")
    pr("     language, including medieval German. This means the VMS text")
    pr("     is NOT raw plaintext in any language — some encoding or")
    pr("     transformation process is involved.")
    pr("  2. Small corpus effects: BvgS is only ~10K words vs 40K for VMS.")
    pr("     Fingerprints are less stable at smaller sizes.")
    pr("  3. OCR artifacts in the BvgS text may distort results.")
    pr("  4. Paleographic origin (Fulda/Mainz) locates the SCRIBE, not the")
    pr("     language. A German scribe could copy Latin, Italian, or Hebrew text.")
    pr("  5. f116v marginalia are physically separate from VMS text body.")
    pr("     German words on f116v could be personal notes, unrelated to content.")
    pr("  6. Recipe genre effects might simply reflect formulaic structure")
    pr("     that any repetitive instructional text would share.")
    pr()

    # Overall assessment
    pr("  OVERALL ASSESSMENT:")
    if n_confirmed >= 3:
        pr("  Strong convergent evidence: Multiple independent statistical")
        pr("  predictions confirmed. Genre-matched medieval German text is a")
        pr("  strong candidate for the VMS source language, with the caveat")
        pr("  that significant encoding/transformation must be involved.")
    elif n_confirmed >= 2:
        pr("  Moderate evidence: Some predictions confirmed, but results are")
        pr("  mixed. German recipe text shows affinity to VMS, but not")
        pr("  dramatically more than other recipe/instructional texts.")
    elif n_confirmed >= 1:
        pr("  Weak evidence: Few predictions confirmed. The German origin")
        pr("  hypothesis is not strongly supported by statistical fingerprinting.")
    else:
        pr("  Refuted: No predictions confirmed. The statistical evidence does")
        pr("  not support a German recipe origin for VMS.")
    pr()

    # ── Save ──────────────────────────────────────────────────────────
    outpath = RESULTS_DIR / 'phase81_german_genre_fingerprint.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Results saved: {outpath}")


if __name__ == '__main__':
    main()
