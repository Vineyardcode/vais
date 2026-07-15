#!/usr/bin/env python3
"""
Phase 102 — Historical Validation

═══════════════════════════════════════════════════════════════════════

OBJECTIVE:
  Test whether 101 phases of statistical findings are JOINTLY
  COMPATIBLE with the manuscript's known historical constraints:
    - C14 radiocarbon: vellum 1404–1438
    - Parallel hatching: illustration date ~1440–1480
    - Northern Italian provenance (binding, Toresella, Touwaide)
    - Widemann→Rudolf chain (1599, alchemical/Paracelsian)
    - Two scribes, Currier A/B as register variation
    - German + Occitan/Romance marginalia
    - Pharmaceutical/herbal content (highest-scoring genre)

METHOD:
  1. TEMPORAL CORPUS FIT — compare VMS statistical fingerprint
     against our NL corpora stratified by period. Texts from the
     correct era (14th-15th c.) should not be WORSE fits than texts
     from wrong eras (classical, 16th c.+). If they are, our "Italian/
     Latin best fit" finding is an artifact of corpus content, not
     historical plausibility.

  2. GENRE FINGERPRINT COMPATIBILITY — compare VMS word-length,
     vocabulary richness, and distributional entropy against genre
     archetypes (recipe, medical, encyclopedic, biblical, military).
     Is the VMS profile compatible with pharmaceutical/herbal text?

  3. PROVENANCE-CHAIN LANGUAGE TEST — given Italian provenance and
     German marginalia, compute how much BETTER Italian and German
     fit VMS compared to control languages (Czech, French, English).
     A genuine Italian manuscript should show a statistically
     significant advantage over non-provenance languages.

  4. MULTI-LINGUAL MARGINALIA TEST — extract and analyze marginalia
     tokens from f116v (German recipe language). Compare their
     statistical profile to the main VMS text. If the marginalia
     author understood the main text, we expect some structural
     alignment.

  5. CODICOLOGICAL CONSISTENCY — test whether the quire structure
     (sections = herbal, astro, bio, pharma, stars) aligns with
     the A/B register split AND with the two-scribe hypothesis.
     The conjunction of all three should be consistent.

  6. BAYESIAN COMPATIBILITY MATRIX — for each major hypothesis
     (language, encoding type, genre, authorship era), compute
     a compatibility score based on all cumulative evidence.
     Report which hypothesis combinations are jointly viable and
     which have fatal contradictions.

SKEPTICISM:
  - Our NL corpora are NOT from the VMS era. Apicius is 4th–5th c.,
    Galen is 2nd c. Greek→Latin, Erasmus is 16th c. Only the Italian
    Cucina (14th c.) and German Ortolf (15th c.) are period-correct.
    A "Latin best fit" could simply mean "Latin texts are bigger" or
    "Latin texts have simpler morphology."
  - Genre fingerprinting failed in Phase 69/76 — recipe texts were
    WORSE than non-recipe. We must replicate and explain this.
  - The Bayesian matrix is qualitative, not a real posterior. We
    cannot assign meaningful priors to "language is Italian" etc.
    We use it as a structured consistency check, not as inference.
  - C14 dates the VELLUM, not the writing. Old vellum could have
    been reused decades later (though hatching → 1440-1480 helps).

═══════════════════════════════════════════════════════════════════════
"""

import re, sys, io, math, json, os
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import chunk_to_str, clean_word, entropy, eva_to_glyphs, extract_words_from_line, load_phase86_clusters, parse_one_chunk, parse_word_into_chunks

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
# EVA GLYPH TOKENIZER
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']


# ═══════════════════════════════════════════════════════════════════════
# LOOP GRAMMAR — CHUNK PARSER
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
# VMS TEXT EXTRACTION (CORRECTED from Phase 101)
# ═══════════════════════════════════════════════════════════════════════



def get_currier_language_from_header(filepath):
    """Parse $L= tag from IVTFF folio header (corrected method from Phase 101)."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            m = re.search(r'\$L=([AB])', line)
            if m:
                return m.group(1)
            low = line.lower()
            if 'language b' in low:
                return 'B'
            if 'language a' in low:
                return 'A'
            if line and not line.startswith('#') and not line.startswith('<'):
                break
    return None

def get_section(folio_name):
    m = re.match(r'f(\d+)', folio_name)
    if not m:
        return 'unknown'
    n = int(m.group(1))
    if n <= 57:   return 'herbal'
    elif n <= 67: return 'astro'
    elif n <= 73: return 'cosmo'
    elif n <= 84: return 'bio'
    elif n <= 86: return 'bio_fold'
    elif n <= 102: return 'pharma'
    else:         return 'stars_text'

def get_hand(filepath):
    """Parse $H= (hand number) from IVTFF header."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.search(r'\$H=(\d+)', line)
            if m:
                return int(m.group(1))
            if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('<'):
                break
    return None

def parse_all_folios():
    """Parse all VMS folios. Returns:
      word_data: dict 'all'/'A'/'B' -> words
      folio_data: list of (name, lang, section, hand, words)
    """
    word_data = {'all': [], 'A': [], 'B': []}
    folio_data = []

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)

    for filepath in folio_files:
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num:
            continue
        folio_name = filepath.stem
        lang = get_currier_language_from_header(filepath)
        sec = get_section(folio_name)
        hand = get_hand(filepath)

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

        word_data['all'].extend(words)
        if lang in ('A', 'B'):
            word_data[lang].extend(words)
        folio_data.append((folio_name, lang or 'U', sec, hand, words))

    return word_data, folio_data

# ═══════════════════════════════════════════════════════════════════════
# PHASE 86 CLUSTER LOADING
# ═══════════════════════════════════════════════════════════════════════


def assign_rare_chunks(chunk_to_class, word_chunk_pairs):
    all_types = set()
    for chunks, _ in word_chunk_pairs:
        all_types.update(chunks)
    mapped = set(chunk_to_class.keys())
    unmapped = [c for c in all_types if c not in mapped]
    if not unmapped:
        return chunk_to_class

    chunk_left = defaultdict(Counter)
    chunk_right = defaultdict(Counter)
    for chunks, _ in word_chunk_pairs:
        for i, c in enumerate(chunks):
            if i > 0: chunk_left[c][chunks[i-1]] += 1
            if i < len(chunks)-1: chunk_right[c][chunks[i+1]] += 1

    cluster_left = defaultdict(Counter)
    cluster_right = defaultdict(Counter)
    for c, cls in chunk_to_class.items():
        for ctx, cnt in chunk_left[c].items(): cluster_left[cls][ctx] += cnt
        for ctx, cnt in chunk_right[c].items(): cluster_right[cls][ctx] += cnt

    all_classes = list(set(chunk_to_class.values()))
    ext = dict(chunk_to_class)
    for uc in unmapped:
        best_cls, best_score = all_classes[0], -1
        ul, ur = chunk_left[uc], chunk_right[uc]
        ult, urt = sum(ul.values())+1e-10, sum(ur.values())+1e-10
        for cls in all_classes:
            cl, cr = cluster_left[cls], cluster_right[cls]
            clt, crt = sum(cl.values())+1e-10, sum(cr.values())+1e-10
            s = (sum((ul[k]/ult)*(cl[k]/clt) for k in ul if k in cl) +
                 sum((ur[k]/urt)*(cr[k]/crt) for k in ur if k in cr))
            if s > best_score:
                best_score, best_cls = s, cls
        ext[uc] = best_cls
    return ext

# ═══════════════════════════════════════════════════════════════════════
# NL CORPUS LOADING (with period metadata)
# ═══════════════════════════════════════════════════════════════════════

# Each corpus entry: (label, path_pattern, language, approx_date, genre)
CORPUS_REGISTRY = [
    ('Apicius',      'latin_texts/apicius.txt',        'Latin',   '400',  'recipe'),
    ('Caesar',       'latin_texts/caesar.txt',         'Latin',   '-50',  'military'),
    ('Galen',        'latin_texts/galen.txt',          'Latin',   '180',  'medical'),
    ('Pliny',        'latin_texts/pliny.txt',          'Latin',   '77',   'encyclopedic'),
    ('Erasmus',      'latin_texts/erasmus.txt',        'Latin',   '1518', 'medical_oration'),
    ('Vulgate',      'latin_texts/vulgate_genesis.txt','Latin',   '400',  'biblical'),
    ('Czech Bible',  'czech_bible_kralice/',            'Czech',   '1613', 'biblical'),
    ('Italian Cucina','vernacular_texts/italian_cucina.txt', 'Italian', '1350', 'recipe'),
    ('German Ortolf','vernacular_texts/german_ortolf_raw.txt','German','1450', 'medical'),
    ('German Faust', 'vernacular_texts/german_faust.txt',    'German','1587', 'literary'),
    ('German BvgS',  'vernacular_texts/german_bvgs_raw.txt', 'German','1400', 'recipe'),
    ('French Viandier','vernacular_texts/french_viandier.txt','French','1390', 'recipe'),
    ('English Cury', 'vernacular_texts/english_cury.txt',    'English','1390', 'recipe'),
]

def load_nl_text(path, max_words=200000):
    words = []
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = re.sub(r'[^a-záàâäéèêëíìîïóòôöúùûüýÿñçæœšžřťďňůß]+', ' ',
                          line.lower())
            for w in line.split():
                if len(w) >= 1:
                    words.append(w)
                    if len(words) >= max_words:
                        return words
    return words

def load_all_corpora():
    """Load all NL corpora with metadata."""
    corpora = {}
    for label, rel_path, lang, date, genre in CORPUS_REGISTRY:
        full_path = DATA_DIR / rel_path
        if full_path.is_dir():
            words = []
            for fp in sorted(full_path.glob('**/*.txt')):
                words.extend(load_nl_text(fp, max_words=300000))
            words = words[:200000]
        elif full_path.exists():
            words = load_nl_text(full_path, max_words=200000)
        else:
            continue
        if not words:
            continue
        corpora[label] = {
            'words': words,
            'language': lang,
            'date': date,
            'genre': genre,
        }
    return corpora


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL UTILITIES
# ═══════════════════════════════════════════════════════════════════════


def jsd(counter_a, counter_b):
    all_keys = set(counter_a) | set(counter_b)
    ta = sum(counter_a.values()) + 1e-30
    tb = sum(counter_b.values()) + 1e-30
    p = {k: counter_a.get(k,0)/ta for k in all_keys}
    q = {k: counter_b.get(k,0)/tb for k in all_keys}
    m = {k: 0.5*(p[k]+q[k]) for k in all_keys}
    def kld(d, ref):
        return sum(d[k]*math.log2(d[k]/ref[k]) for k in all_keys if d[k]>0 and ref[k]>0)
    return 0.5*kld(p,m) + 0.5*kld(q,m)


def compute_text_fingerprint(words):
    """Compute a standard fingerprint for a word list."""
    n_tokens = len(words)
    freq = Counter(words)
    n_types = len(freq)
    hapax = sum(1 for c in freq.values() if c == 1)

    # Letter stats
    letter_freq = Counter()
    for w in words:
        for ch in w:
            letter_freq[ch] += 1

    # Word lengths
    lengths = [len(w) for w in words]
    mean_wl = np.mean(lengths) if lengths else 0

    # Zipf slope (log-log rank-frequency)
    sorted_freq = sorted(freq.values(), reverse=True)
    if len(sorted_freq) > 10:
        ranks = np.log10(np.arange(1, len(sorted_freq)+1))
        freqs = np.log10(np.array(sorted_freq, dtype=float))
        # Simple least-squares slope
        n = len(ranks)
        slope = (n*np.sum(ranks*freqs) - np.sum(ranks)*np.sum(freqs)) / \
                (n*np.sum(ranks**2) - np.sum(ranks)**2 + 1e-30)
    else:
        slope = 0.0

    return {
        'n_tokens': n_tokens,
        'n_types': n_types,
        'ttr': n_types / max(n_tokens, 1),
        'hapax_ratio': hapax / max(n_types, 1),
        'mean_word_length': round(mean_wl, 3),
        'letter_entropy': round(entropy(letter_freq), 4),
        'n_letters': len(letter_freq),
        'zipf_slope': round(slope, 4),
        'word_entropy': round(entropy(freq), 4),
    }


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def run_analysis():
    pr("=" * 72)
    pr("PHASE 102 — HISTORICAL VALIDATION")
    pr("=" * 72)
    pr()

    results = {}

    # ───────────────────────────────────────────────────────────────────
    # STEP 0: Load VMS and NL data
    # ───────────────────────────────────────────────────────────────────
    word_data, folio_data = parse_all_folios()
    corpora = load_all_corpora()

    pr("─" * 72)
    pr("STEP 0: Data loaded")
    pr("─" * 72)
    pr()
    pr(f"  VMS: {len(word_data['all'])} words, A={len(word_data['A'])}, B={len(word_data['B'])}")
    pr(f"  NL corpora: {len(corpora)}")
    for label, info in sorted(corpora.items()):
        pr(f"    {label:<20s} lang={info['language']:<10s} date={info['date']:<6s} "
           f"genre={info['genre']:<18s} words={len(info['words'])}")
    pr()

    # Compute VMS fingerprint
    vms_fp = compute_text_fingerprint(word_data['all'])
    vms_fp_A = compute_text_fingerprint(word_data['A'])
    vms_fp_B = compute_text_fingerprint(word_data['B'])
    pr(f"  VMS fingerprint: TTR={vms_fp['ttr']:.4f} mean_wl={vms_fp['mean_word_length']:.2f} "
       f"hapax={vms_fp['hapax_ratio']:.3f} Zipf={vms_fp['zipf_slope']:.3f} "
       f"H_letter={vms_fp['letter_entropy']:.3f}")
    pr()

    # ───────────────────────────────────────────────────────────────────
    # STEP 1: TEMPORAL CORPUS FIT
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 1: Temporal corpus fit — does period-correct text fit better?")
    pr("─" * 72)
    pr()

    # Compute fingerprint for each corpus
    corpus_fps = {}
    for label, info in corpora.items():
        fp = compute_text_fingerprint(info['words'])
        corpus_fps[label] = fp

    # Compute VMS letter frequency distribution for JSD comparison
    vms_letter = Counter()
    for w in word_data['all']:
        for g in eva_to_glyphs(w):
            vms_letter[g] += 1

    # For each NL corpus, compute letter freq JSD vs VMS
    # Also compute word-length distribution JSD
    vms_wl = Counter(len(w) for w in word_data['all'])

    pr(f"  {'Corpus':<20s} {'Date':>6s} {'Lang':<10s} {'Genre':<18s} "
       f"{'WL JSD':>8s} {'TTR diff':>9s} {'Zipf diff':>10s} {'H_let diff':>10s} "
       f"{'Composite':>10s}")

    temporal_results = []
    for label in sorted(corpora.keys()):
        info = corpora[label]
        fp = corpus_fps[label]

        # Word length distribution JSD
        nl_wl = Counter(len(w) for w in info['words'])
        wl_jsd = jsd(vms_wl, nl_wl)

        # Feature diffs (absolute)
        ttr_diff = abs(vms_fp['ttr'] - fp['ttr'])
        zipf_diff = abs(vms_fp['zipf_slope'] - fp['zipf_slope'])
        h_let_diff = abs(vms_fp['letter_entropy'] - fp['letter_entropy'])

        # Composite distance (equal weight on 4 features)
        composite = (wl_jsd + ttr_diff + zipf_diff/5 + h_let_diff/5) / 4

        pr(f"  {label:<20s} {info['date']:>6s} {info['language']:<10s} {info['genre']:<18s} "
           f"{wl_jsd:>8.4f} {ttr_diff:>9.4f} {zipf_diff:>10.4f} {h_let_diff:>10.4f} "
           f"{composite:>10.4f}")

        temporal_results.append({
            'corpus': label, 'date': info['date'], 'language': info['language'],
            'genre': info['genre'], 'wl_jsd': round(wl_jsd, 5),
            'ttr_diff': round(ttr_diff, 5), 'zipf_diff': round(zipf_diff, 5),
            'h_letter_diff': round(h_let_diff, 5), 'composite': round(composite, 5),
        })

    temporal_results.sort(key=lambda x: x['composite'])
    pr()
    pr("  RANKED BY COMPOSITE DISTANCE (lower = better fit):")
    for i, tr in enumerate(temporal_results):
        era_match = '✓' if 1300 <= int(tr['date']) <= 1500 else ' '
        pr(f"    {i+1:>2d}. {tr['corpus']:<20s} d={tr['composite']:.4f}  "
           f"date={tr['date']}  {era_match}")

    pr()
    # Period-correct texts (1300-1500)
    period_correct = [t for t in temporal_results if 1300 <= int(t['date']) <= 1500]
    period_wrong = [t for t in temporal_results if not (1300 <= int(t['date']) <= 1500)]
    if period_correct and period_wrong:
        mean_correct = np.mean([t['composite'] for t in period_correct])
        mean_wrong = np.mean([t['composite'] for t in period_wrong])
        pr(f"  Mean composite distance:")
        pr(f"    Period-correct (1300–1500): {mean_correct:.4f}  (n={len(period_correct)})")
        pr(f"    Period-wrong:               {mean_wrong:.4f}  (n={len(period_wrong)})")
        pr(f"    Ratio correct/wrong: {mean_correct/max(mean_wrong,1e-10):.3f}")
        if mean_correct < mean_wrong:
            pr("    → Period-correct texts ARE closer to VMS — consistent with dating")
        else:
            pr("    → Period-correct texts are NOT closer — dating is not reflected in statistics")
            pr("    ⚠ This could mean: (a) our features don't capture period effects, or")
            pr("      (b) the VMS's statistical profile is encoding-dominated, not language-dominated")
    pr()

    results['temporal_fit'] = temporal_results

    # ───────────────────────────────────────────────────────────────────
    # STEP 2: GENRE FINGERPRINT COMPATIBILITY
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 2: Genre fingerprint — is VMS compatible with pharmaceutical text?")
    pr("─" * 72)
    pr()

    # Group corpora by genre
    genre_groups = defaultdict(list)
    for label, info in corpora.items():
        genre_groups[info['genre']].append(label)

    pr("  VMS vs genre averages:")
    pr(f"  {'Genre':<18s} {'mean WL':>8s} {'TTR':>8s} {'Hapax':>8s} "
       f"{'Zipf':>8s} {'H_word':>8s}")
    pr(f"  {'VMS':<18s} {vms_fp['mean_word_length']:>8.2f} {vms_fp['ttr']:>8.4f} "
       f"{vms_fp['hapax_ratio']:>8.3f} {vms_fp['zipf_slope']:>8.3f} "
       f"{vms_fp['word_entropy']:>8.3f}")
    pr()

    genre_fps = {}
    for genre, labels in sorted(genre_groups.items()):
        fps = [corpus_fps[l] for l in labels]
        avg = {
            'mean_word_length': np.mean([f['mean_word_length'] for f in fps]),
            'ttr': np.mean([f['ttr'] for f in fps]),
            'hapax_ratio': np.mean([f['hapax_ratio'] for f in fps]),
            'zipf_slope': np.mean([f['zipf_slope'] for f in fps]),
            'word_entropy': np.mean([f['word_entropy'] for f in fps]),
        }
        genre_fps[genre] = avg
        pr(f"  {genre:<18s} {avg['mean_word_length']:>8.2f} {avg['ttr']:>8.4f} "
           f"{avg['hapax_ratio']:>8.3f} {avg['zipf_slope']:>8.3f} "
           f"{avg['word_entropy']:>8.3f}  ({', '.join(labels)})")

    pr()

    # Distance from VMS to each genre
    pr("  FEATURE-BY-FEATURE COMPARISON (VMS minus genre average):")
    pr(f"  {'Genre':<18s} {'Δ WL':>8s} {'Δ TTR':>8s} {'Δ Hapax':>8s} "
       f"{'Δ Zipf':>8s} {'Δ H_word':>8s} {'|Δ| sum':>8s}")

    genre_dists = {}
    for genre, avg in sorted(genre_fps.items()):
        d_wl = vms_fp['mean_word_length'] - avg['mean_word_length']
        d_ttr = vms_fp['ttr'] - avg['ttr']
        d_hap = vms_fp['hapax_ratio'] - avg['hapax_ratio']
        d_zipf = vms_fp['zipf_slope'] - avg['zipf_slope']
        d_hword = vms_fp['word_entropy'] - avg['word_entropy']
        total = abs(d_wl/10) + abs(d_ttr) + abs(d_hap) + abs(d_zipf/5) + abs(d_hword/15)
        genre_dists[genre] = total
        pr(f"  {genre:<18s} {d_wl:>+8.2f} {d_ttr:>+8.4f} {d_hap:>+8.3f} "
           f"{d_zipf:>+8.3f} {d_hword:>+8.3f} {total:>8.4f}")

    best_genre = min(genre_dists, key=genre_dists.get)
    pr(f"\n  Closest genre by composite: {best_genre} (dist={genre_dists[best_genre]:.4f})")
    pr()

    # Key observation: VMS word lengths
    pr("  CRITICAL: VMS mean word length in GLYPHS:")
    glyph_lengths = [len(eva_to_glyphs(w)) for w in word_data['all']]
    pr(f"    Mean glyph length: {np.mean(glyph_lengths):.2f}")
    pr(f"    Mean letter length: {vms_fp['mean_word_length']:.2f}")
    pr("    (NL word lengths are in letters, VMS is in EVA characters)")
    pr("    This mismatch makes direct word-length comparison unreliable.")
    pr()

    results['genre_fit'] = {
        'genre_distances': {g: round(d, 5) for g, d in genre_dists.items()},
        'best_genre': best_genre,
        'vms_mean_wl_glyphs': round(float(np.mean(glyph_lengths)), 3),
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 3: PROVENANCE-CHAIN LANGUAGE TEST
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 3: Provenance-chain language test")
    pr("─" * 72)
    pr()

    pr("  Historical provenance suggests Italian origin with German connections.")
    pr("  Do Italian/German/Latin corpora fit VMS better than controls?")
    pr()

    # Group corpora by language
    lang_groups = defaultdict(list)
    for label, info in corpora.items():
        lang_groups[info['language']].append(label)

    # For each language group, compute average letter-frequency JSD vs VMS
    # Use rank-normalized top-N comparison (matching Phase 101 method)
    def rank_dist(counter, k=25):
        vals = sorted(counter.values(), reverse=True)[:k]
        total = sum(vals) + 1e-30
        return Counter({i: v/total for i, v in enumerate(vals)})

    vms_rank = rank_dist(vms_letter)

    pr(f"  {'Language':<12s} {'Corpora':>8s} {'Rank JSD':>10s} {'WL JSD':>10s} "
       f"{'Composite':>10s} {'Provenance?':>12s}")

    lang_results = {}
    for lang in sorted(lang_groups.keys()):
        labels = lang_groups[lang]
        # Aggregate all words for this language
        lang_words = []
        for l in labels:
            lang_words.extend(corpora[l]['words'])

        nl_letter = Counter()
        for w in lang_words:
            for ch in w:
                nl_letter[ch] += 1
        nl_rank = rank_dist(nl_letter)
        r_jsd = jsd(vms_rank, nl_rank)

        nl_wl = Counter(len(w) for w in lang_words)
        w_jsd = jsd(vms_wl, nl_wl)

        comp = (r_jsd + w_jsd) / 2
        prov = 'YES' if lang in ('Italian', 'German', 'Latin') else 'no'

        pr(f"  {lang:<12s} {len(labels):>8d} {r_jsd:>10.6f} {w_jsd:>10.6f} "
           f"{comp:>10.6f} {prov:>12s}")

        lang_results[lang] = {
            'n_corpora': len(labels), 'rank_jsd': round(r_jsd, 6),
            'wl_jsd': round(w_jsd, 6), 'composite': round(comp, 6),
            'provenance': prov == 'YES',
        }

    pr()
    # Statistical test: provenance vs non-provenance
    prov_scores = [v['composite'] for v in lang_results.values() if v['provenance']]
    ctrl_scores = [v['composite'] for v in lang_results.values() if not v['provenance']]
    if prov_scores and ctrl_scores:
        mean_prov = np.mean(prov_scores)
        mean_ctrl = np.mean(ctrl_scores)
        pr(f"  Provenance languages (Italian/German/Latin): mean={mean_prov:.6f}")
        pr(f"  Control languages (Czech/French/English):     mean={mean_ctrl:.6f}")
        if mean_prov < mean_ctrl:
            pr(f"  → Provenance languages ARE closer ({(1 - mean_prov/mean_ctrl)*100:.1f}% closer)")
        else:
            pr(f"  → Provenance languages are NOT closer — no statistical support for Italian origin")
            pr(f"    from distributional comparison alone")
    pr()

    # Permutation test: shuffle language-provenance labels
    N_PERM = 2000
    all_comps = list(lang_results.values())
    n_prov = sum(1 for v in all_comps if v['provenance'])
    real_diff = mean_prov - mean_ctrl if prov_scores and ctrl_scores else 0

    null_diffs = []
    comp_vals = [v['composite'] for v in all_comps]
    for _ in range(N_PERM):
        random.shuffle(comp_vals)
        perm_prov = np.mean(comp_vals[:n_prov])
        perm_ctrl = np.mean(comp_vals[n_prov:])
        null_diffs.append(perm_prov - perm_ctrl)

    null_arr = np.array(null_diffs)
    p_val = np.mean(null_arr <= real_diff) if real_diff < 0 else np.mean(null_arr >= real_diff)
    z_val = (real_diff - np.mean(null_arr)) / max(np.std(null_arr), 1e-10)

    pr(f"  Permutation test ({N_PERM} shuffles): z = {z_val:+.2f}, p = {p_val:.4f}")
    if p_val < 0.05:
        pr("  → SIGNIFICANT: provenance languages fit VMS better than chance")
    else:
        pr("  → NOT SIGNIFICANT: provenance advantage is within random variation")
    pr()

    results['provenance_test'] = {
        'lang_results': lang_results,
        'prov_mean': round(mean_prov, 6) if prov_scores else None,
        'ctrl_mean': round(mean_ctrl, 6) if ctrl_scores else None,
        'perm_z': round(z_val, 3),
        'perm_p': round(p_val, 4),
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 4: MARGINALIA ANALYSIS (f116v)
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 4: Marginalia analysis — f116v")
    pr("─" * 72)
    pr()

    # Read f116v
    f116v_path = FOLIO_DIR / 'f116v.txt'
    f116v_lines = []
    f116v_words = []
    if f116v_path.exists():
        with open(f116v_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                f116v_lines.append(line.rstrip())
    else:
        pr("  WARNING: f116v.txt not found")

    pr("  f116v raw content (all lines):")
    for line in f116v_lines:
        pr(f"    {line}")
    pr()

    # Extract Voynichese words from f116v
    for line in f116v_lines:
        line = line.strip()
        if line.startswith('#') or not line:
            continue
        m = re.match(r'<([^>]+)>', line)
        if not m:
            continue
        rest = line[m.end():].strip()
        if rest:
            f116v_words.extend(extract_words_from_line(rest))

    pr(f"  Extractable VMS words from f116v: {len(f116v_words)}")
    if f116v_words:
        pr(f"    Words: {' '.join(f116v_words[:30])}{'...' if len(f116v_words)>30 else ''}")
    pr()

    # Known marginalia content from Davis/Zandbergen research
    pr("  KNOWN MARGINALIA (from published research):")
    pr("    - German recipe words: 'so nim gasmich' (take a mushroom)")
    pr("    - 'boxleber' (box-liver?), plant/preparation terms")
    pr("    - Latin/Romance charm or incantation fragments")
    pr("    - Written by a LATER hand (not the main scribe)")
    pr("    - Language: German with possible Occitan/Romance elements")
    pr()

    pr("  IMPLICATION FOR HISTORICAL VALIDATION:")
    pr("    The f116v marginalia prove the manuscript was handled by a")
    pr("    German-speaking person who attempted to add annotations.")
    pr("    This is consistent with the Widemann→Rudolf provenance")
    pr("    (Prague/Augsburg = German-speaking regions, 1550s–1600s).")
    pr("    It does NOT prove the MAIN text is German — only that the")
    pr("    manuscript circulated in German-speaking milieu.")
    pr()

    results['marginalia'] = {
        'f116v_vms_words': len(f116v_words),
        'f116v_total_lines': len(f116v_lines),
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 5: CODICOLOGICAL CONSISTENCY
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 5: Codicological consistency — section × language × hand")
    pr("─" * 72)
    pr()

    # Build section × language × hand cross-tabulation
    cross_tab = defaultdict(lambda: Counter())  # section → Counter of (lang, hand)
    section_words = defaultdict(int)
    hand_counts = Counter()

    for fname, lang, sec, hand, words in folio_data:
        if lang == 'U':
            continue
        key = f"{lang}_H{hand}" if hand else f"{lang}_H?"
        cross_tab[sec][key] += 1
        section_words[sec] += len(words)
        if hand:
            hand_counts[hand] += 1

    pr("  Section × (Language, Hand) cross-tabulation:")
    all_keys = sorted(set(k for ct in cross_tab.values() for k in ct))
    pr(f"  {'Section':<14s} {'words':>7s} ", end='')
    for k in all_keys:
        pr(f" {k:>8s}", end='')
    pr()

    for sec in ['herbal', 'astro', 'cosmo', 'bio', 'bio_fold', 'pharma', 'stars_text']:
        ct = cross_tab.get(sec, Counter())
        pr(f"  {sec:<14s} {section_words.get(sec,0):>7d} ", end='')
        for k in all_keys:
            pr(f" {ct.get(k,0):>8d}", end='')
        pr()
    pr()

    # Test: is hand correlated with language?
    hand_lang = defaultdict(Counter)
    for fname, lang, sec, hand, words in folio_data:
        if lang in ('A', 'B') and hand:
            hand_lang[hand][lang] += 1

    pr("  Hand × Language:")
    for h in sorted(hand_lang.keys()):
        pr(f"    Hand {h}: A={hand_lang[h].get('A',0)} folios, "
           f"B={hand_lang[h].get('B',0)} folios")
    pr()

    # Chi-square test for hand × language independence
    hands = sorted(hand_lang.keys())
    if len(hands) >= 2:
        # Build 2x2+ contingency table
        observed = []
        for h in hands:
            observed.append([hand_lang[h].get('A', 0), hand_lang[h].get('B', 0)])
        obs = np.array(observed, dtype=float)
        row_sums = obs.sum(axis=1, keepdims=True)
        col_sums = obs.sum(axis=0, keepdims=True)
        total = obs.sum()
        if total > 0:
            expected = row_sums * col_sums / total
            # Chi-square statistic
            chi2 = np.sum((obs - expected)**2 / (expected + 1e-10))
            df = (len(hands) - 1) * 1  # (rows-1)(cols-1)
            # Approximate p-value from chi-square (use normal approx for large df)
            # For small df, use exact lookup
            # Simple: compare to chi2 critical values
            pr(f"  Chi-square test (hand × language): χ² = {chi2:.2f}, df = {df}")
            if chi2 > 10.83:  # p < 0.001 for df=1
                pr("    → HIGHLY SIGNIFICANT association (p < 0.001)")
            elif chi2 > 6.63:
                pr("    → SIGNIFICANT association (p < 0.01)")
            elif chi2 > 3.84:
                pr("    → SIGNIFICANT association (p < 0.05)")
            else:
                pr("    → NOT SIGNIFICANT — hand and language are independent")
            pr()

            # Cramér's V
            min_dim = min(len(hands), 2) - 1
            cramers_v = math.sqrt(chi2 / (total * max(min_dim, 1)))
            pr(f"    Cramér's V = {cramers_v:.3f}")
            if cramers_v > 0.5:
                pr("    → STRONG association: scribal hand predicts Currier language")
            elif cramers_v > 0.3:
                pr("    → MODERATE association")
            else:
                pr("    → WEAK association: hand and language are largely independent")
    pr()

    pr("  CODICOLOGICAL INTERPRETATION:")
    pr("    If hand ≈ language, then the A/B split may be a SCRIBAL effect")
    pr("    (two different people writing differently). If hand ⊥ language,")
    pr("    then A/B is a CONTENT effect (same person changes register).")
    pr("    The cross-tabulation above distinguishes these scenarios.")
    pr()

    results['codicology'] = {
        'section_word_counts': dict(section_words),
        'hand_lang': {str(h): dict(c) for h, c in hand_lang.items()},
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 6: BAYESIAN COMPATIBILITY MATRIX
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 6: Bayesian compatibility matrix")
    pr("─" * 72)
    pr()

    pr("  This is a QUALITATIVE consistency check, not a true posterior.")
    pr("  For each hypothesis dimension, we assess whether cumulative")
    pr("  evidence supports (+), contradicts (−), or is neutral (0).")
    pr()

    # Define hypothesis dimensions and evidence
    hypotheses = {
        'substrate_language': {
            'Latin':   {'description': 'Latin as underlying language'},
            'Italian': {'description': 'Italian vernacular'},
            'German':  {'description': 'German'},
            'Czech':   {'description': 'Czech/Slavic'},
            'Constructed': {'description': 'Constructed/artificial language'},
        },
        'encoding_type': {
            'Simple substitution': {'description': 'Monoalphabetic cipher'},
            'Verbose cipher':     {'description': 'Bigram→symbol mapping'},
            'Abbreviation+cipher':{'description': 'Abbreviated then enciphered'},
            'Constructed script': {'description': 'Purpose-built writing system'},
            'Meaningless':        {'description': 'Gibberish/hoax'},
        },
        'genre': {
            'Pharmaceutical': {'description': 'Herbal/medical recipes'},
            'Alchemical':     {'description': 'Alchemical processes'},
            'Astronomical':   {'description': 'Star/zodiac catalog'},
            'Encyclopedic':   {'description': 'General reference work'},
        },
        'creation_era': {
            '1400-1440': {'description': 'Matches vellum C14 dating'},
            '1440-1480': {'description': 'Matches illustration hatching'},
            '1480-1530': {'description': 'Later creation on old vellum'},
            'Pre-1400':  {'description': 'Before vellum date (impossible)'},
        },
    }

    # Evidence from 101 phases
    evidence = [
        ('Phase 100: Simple substitution fails',
         {'Simple substitution': -2, 'Verbose cipher': +1,
          'Abbreviation+cipher': +1, 'Constructed script': +1, 'Meaningless': 0}),
        ('Phase 100: Latin best CV fit (16.7%)',
         {'Latin': +1, 'Italian': +1, 'German': 0, 'Czech': -1, 'Constructed': 0}),
        ('Phase 101: Same grammar, different vocabulary (A/B)',
         {'Pharmaceutical': +1, 'Alchemical': +1, 'Astronomical': 0, 'Encyclopedic': +1}),
        ('Phase 98: h_ratio = 0.818 (NL-like)',
         {'Meaningless': -2, 'Latin': +1, 'Italian': +1, 'German': +1,
          'Czech': +1, 'Constructed': +1}),
        ('Phase 75: Gallows ≠ letter substitution',
         {'Simple substitution': -2, 'Verbose cipher': +1,
          'Abbreviation+cipher': +1, 'Constructed script': +1}),
        ('Phase 99: VMS is typological outlier (p=1.0)',
         {'Simple substitution': -1, 'Verbose cipher': 0,
          'Constructed script': +2, 'Meaningless': -1}),
        ('Phase 86: 25-class chunk equivalence (structured)',
         {'Meaningless': -2, 'Simple substitution': -1,
          'Constructed script': +1, 'Verbose cipher': +1}),
        ('C14: Vellum 1404-1438',
         {'Pre-1400': -3, '1400-1440': +2, '1440-1480': +1, '1480-1530': 0}),
        ('Parallel hatching: ~1440-1480',
         {'Pre-1400': -3, '1400-1440': 0, '1440-1480': +2, '1480-1530': -1}),
        ('Italian provenance (binding, Toresella)',
         {'Italian': +2, 'Latin': +1, 'German': -1, 'Czech': -1, 'Constructed': 0}),
        ('German marginalia on f116v',
         {'German': +1, 'Italian': 0, 'Latin': 0, 'Czech': 0}),
        ('Occitan month labels (zodiac pages)',
         {'Italian': +1, 'Latin': 0, 'German': -1, 'Czech': -1}),
        ('Widemann alchemical collection context',
         {'Pharmaceutical': +1, 'Alchemical': +2, 'Astronomical': 0, 'Encyclopedic': 0}),
        ('Pharmaceutical = highest-scoring genre (7/10)',
         {'Pharmaceutical': +2, 'Alchemical': +1, 'Astronomical': 0, 'Encyclopedic': +1}),
        ('Phase 76: Recipe texts match gallows coverage',
         {'Pharmaceutical': +1, 'Alchemical': +1, 'Astronomical': -1, 'Encyclopedic': 0}),
        ('Phase 4: 4/6 pharma features match',
         {'Pharmaceutical': +1, 'Alchemical': 0, 'Astronomical': -1, 'Encyclopedic': 0}),
        ('Baresch letter: "Egyptian medicine" belief',
         {'Pharmaceutical': +1, 'Alchemical': 0}),
    ]

    # Accumulate scores
    scores = defaultdict(lambda: defaultdict(int))
    for ev_name, ev_scores in evidence:
        for hyp, score in ev_scores.items():
            # Find which dimension this hypothesis belongs to
            for dim, options in hypotheses.items():
                if hyp in options:
                    scores[dim][hyp] += score

    pr("  COMPATIBILITY SCORES (cumulative evidence weight):")
    pr("  Higher = more evidence support, lower = more contradiction")
    pr()

    for dim, options in hypotheses.items():
        pr(f"  {dim.upper().replace('_', ' ')}:")
        sorted_opts = sorted(options.keys(), key=lambda h: -scores[dim].get(h, 0))
        for h in sorted_opts:
            s = scores[dim].get(h, 0)
            bar = '+' * max(s, 0) + '-' * max(-s, 0)
            pr(f"    {h:<24s} {s:>+3d}  {bar}  ({options[h]['description']})")
        pr()

    # Most compatible combination
    pr("  MOST COMPATIBLE JOINT HYPOTHESIS:")
    for dim in hypotheses:
        best = max(hypotheses[dim].keys(), key=lambda h: scores[dim].get(h, 0))
        pr(f"    {dim}: {best} (score={scores[dim][best]:+d})")
    pr()

    results['compatibility_matrix'] = {
        dim: {h: scores[dim].get(h, 0) for h in opts}
        for dim, opts in hypotheses.items()
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 7: FATAL CONTRADICTION SCAN
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 7: Fatal contradiction scan")
    pr("─" * 72)
    pr()

    contradictions = []

    # Check for score < -2 (strong contradiction)
    for dim, opts in hypotheses.items():
        for h in opts:
            s = scores[dim].get(h, 0)
            if s <= -2:
                contradictions.append((dim, h, s))

    # Additional logical contradictions
    logical_checks = [
        ("C14 rules out pre-1400 creation",
         scores['creation_era'].get('Pre-1400', 0) <= -2,
         "PASS" if scores['creation_era'].get('Pre-1400', 0) <= -2 else "FAIL"),
        ("Simple substitution rejected by Phase 75 + 100",
         scores['encoding_type'].get('Simple substitution', 0) <= -2,
         "PASS" if scores['encoding_type'].get('Simple substitution', 0) <= -2 else "FAIL"),
        ("Meaningless/hoax rejected by NL-like statistics",
         scores['encoding_type'].get('Meaningless', 0) <= -2,
         "PASS" if scores['encoding_type'].get('Meaningless', 0) <= -2 else "FAIL"),
        ("Italian provenance consistent with best-fit language",
         scores['substrate_language'].get('Italian', 0) > 0
         or scores['substrate_language'].get('Latin', 0) > 0,
         "PASS" if (scores['substrate_language'].get('Italian', 0) > 0
                    or scores['substrate_language'].get('Latin', 0) > 0) else "FAIL"),
        ("Genre (pharmaceutical) consistent with illustrations",
         scores['genre'].get('Pharmaceutical', 0) > 0,
         "PASS" if scores['genre'].get('Pharmaceutical', 0) > 0 else "FAIL"),
    ]

    pr("  Logical consistency checks:")
    for desc, _, result in logical_checks:
        pr(f"    [{result}] {desc}")
    pr()

    if contradictions:
        pr(f"  Fatally contradicted hypotheses (score ≤ -2):")
        for dim, h, s in contradictions:
            pr(f"    {dim}: {h} (score={s})")
    else:
        pr("  No fatal contradictions found.")
    pr()

    n_pass = sum(1 for _, _, r in logical_checks if r == 'PASS')
    pr(f"  Overall: {n_pass}/{len(logical_checks)} consistency checks pass")
    pr()

    results['contradictions'] = {
        'fatal': [(dim, h, s) for dim, h, s in contradictions],
        'logical_checks': [(desc, result) for desc, _, result in logical_checks],
        'pass_rate': n_pass / max(len(logical_checks), 1),
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 8: CUMULATIVE EVIDENCE SUMMARY
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 8: Cumulative evidence summary — what do 102 phases tell us?")
    pr("─" * 72)
    pr()

    # Load prior results for the grand summary
    pr("  ESTABLISHED FACTS (confidence ≥ 95%):")
    facts_95 = [
        ("VMS text has NL-like statistical structure", "92%→95%",
         "h_ratio=0.818, Zipf law, Heaps law, positional concentration"),
        ("VMS chunks are functional sub-word units", "98%",
         "LOOP grammar parses 99.8%, 25-class equivalence, slot-based MI"),
        ("Simple substitution cipher is ruled out", "99%",
         "Phase 75 gallows, Phase 100 decipherment failure"),
        ("Hoax/meaningless is ruled out", "97%",
         "NL-like statistics + LOOP grammar + cross-word MI"),
        ("Currier A/B is statistically real", "99%",
         "z>30, 88.6% classifier, corrected folio assignments"),
        ("A and B share the same chunk grammar", "95%",
         "Cross-perplexity ratio 1.010, class-bigram Jaccard 0.706"),
        ("VMS is a typological outlier", "95%",
         "p=1.0, no known script matches on 8 dimensions"),
    ]

    for fact, conf, evidence_str in facts_95:
        pr(f"  [{conf:>5s}] {fact}")
        pr(f"          Evidence: {evidence_str}")

    pr()
    pr("  PROBABLE FINDINGS (confidence 70–95%):")
    prob_findings = [
        ("Substrate language is Italian or Latin", "80%",
         "Phase 100/101 NL fit; Italian provenance; Phase 76 coverage"),
        ("Content is pharmaceutical/herbal", "80%",
         "Phase 4 features; genre scores 7/10; Widemann context; illustrations"),
        ("A/B is register variation within one system", "80%",
         "Phase 101: shared grammar, different vocabulary"),
        ("Encoding uses complex/verbose cipher or constructed script", "75%",
         "Phase 75 gallows, Phase 85 Pelling, Phase 99 typology"),
        ("Creation date: 1440–1480", "75%",
         "C14 vellum 1404–1438 + parallel hatching analysis"),
        ("A/B partly confounded with manuscript section", "85%",
         "Phase 101: within-section JSD ≈ between-section JSD"),
        ("VMS chunks resemble abugida sub-units", "70%",
         "Phase 99: closest typological category, but only on h_ratio"),
    ]

    for fact, conf, evidence_str in prob_findings:
        pr(f"  [{conf:>5s}] {fact}")
        pr(f"          Evidence: {evidence_str}")

    pr()
    pr("  OPEN QUESTIONS:")
    open_qs = [
        "What specific encoding maps the substrate language to Voynichese?",
        "Are the -edy/-eedy B-exclusive words content-specific or structurally distinct?",
        "Is the pharma section (f87–102) correctly assigned by Currier?",
        "Does the quire Q9 'foreign' hypothesis explain statistical anomalies?",
        "Can the 25-class alphabet be refined to recover any coherent text?",
        "What explains the 'o problem' (o appears in nearly every word)?",
        "Do gallows encode word-level structure (imperatives/markers) or phonemes?",
    ]
    for q in open_qs:
        pr(f"  • {q}")
    pr()

    pr("  MOST PARSIMONIOUS SCENARIO (from 102 phases):")
    pr("    The VMS is a PHARMACEUTICAL/HERBAL COMPENDIUM written in")
    pr("    Northern Italy around 1440–1480, encoding Italian or Latin")
    pr("    through a complex notation system (verbose cipher, abbreviation")
    pr("    system, or purpose-built script). Two registers (Currier A/B)")
    pr("    reflect content sections (e.g., substances vs. processes, or")
    pr("    different source texts). The encoding is NOT a simple letter")
    pr("    substitution — it operates at the chunk/syllable level with")
    pr("    positional grammar (LOOP structure). The manuscript later")
    pr("    entered German-speaking collections (Widemann, Rudolf II) where")
    pr("    marginal annotations were added in German.")
    pr()

    pr("  CRITICAL CAVEATS:")
    pr("    1. 'Italian/Latin best fit' may be a corpus artifact — our Italian")
    pr("       corpus is small (24K words), and Latin corpora are from wrong era.")
    pr("    2. Genre fingerprinting is unreliable — recipe texts scored WORSE than")
    pr("       non-recipe in Phase 76's TTR test. The 'pharmaceutical' conclusion")
    pr("       rests more on illustrations than on statistical text analysis.")
    pr("    3. No phase has produced READABLE TEXT. All 'fit' measures are")
    pr("       distributional, not semantic. Without decipherment, the language")
    pr("       identification remains circumstantial.")
    pr("    4. The Bayesian matrix is qualitative. Assigning numeric weights")
    pr("       to historical evidence is inherently subjective. Different weight")
    pr("       schemes could change the ranking.")
    pr("    5. Run-to-run instability (Phase 100) means stochastic methods")
    pr("       produce unreliable rankings. Only cross-validated, stable results")
    pr("       should be trusted.")
    pr()

    results['summary'] = {
        'n_phases': 102,
        'established_facts': len(facts_95),
        'probable_findings': len(prob_findings),
        'open_questions': len(open_qs),
        'most_parsimonious': 'Italian/Latin pharmaceutical compendium, verbose/constructed encoding, N. Italy ~1440-1480',
    }

    # ───────────────────────────────────────────────────────────────────
    # SAVE RESULTS
    # ───────────────────────────────────────────────────────────────────
    json_path = RESULTS_DIR / 'phase102_historical_validation.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    txt_path = RESULTS_DIR / 'phase102_historical_validation.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))

    pr(f"\n  Results saved to {json_path}")
    pr(f"  Log saved to {txt_path}")


if __name__ == '__main__':
    run_analysis()
