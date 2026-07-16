#!/usr/bin/env python3
"""
Resolve the Currier A/B Dichotomy

═══════════════════════════════════════════════════════════════════════

OBJECTIVE:
  Determine whether Currier Language A and Language B represent:
    (a) Two genuinely different encoding/language systems, or
    (b) Registers/topics within one system, or
    (c) Scribal variation (same content, different hand habits)

  CRITICAL FIX: All prior phases (98, 100, ...) used a hardcoded
  get_currier_language() function with ~42% error rate.  This phase
  parses the authoritative $L= tag from the IVTFF folio headers.

METHOD:
  1. CORRECTED CORPUS SPLIT — parse $L=A / $L=B from folio headers.
     Quantify how badly the old hardcoded function was wrong.
  2. 25-CLASS DISTRIBUTIONS — unigram, bigram, positional (initial/
     medial/final), word-length. JSD between A and B at each level.
  3. VOCABULARY OVERLAP — chunk types, word types, class bigrams
     shared vs unique to A or B.
  4. MARKOV CROSS-PERPLEXITY — train chunk-bigram model on A, test
     on B, and vice versa.  Compare to within-language perplexity
     (train/test within A, within B).  If A→B perplexity ≈ A→A, the
     underlying chunk grammar is shared.
  5. INFORMATION-THEORETIC DIVERGENCE — Jensen-Shannon divergence
     between A and B at class-unigram, class-bigram, and glyph levels.
     Permutation test: shuffle folio labels 1000 times, recompute JSD
     each time → p-value for the real A/B split.
  6. CLASSIFIER — nearest-centroid classifier on folio-level class-bigram
     features.  Leave-one-out cross-validated accuracy.  Compare to null
     (shuffled labels, same LOO protocol).
  7. DIFFERENTIAL FEATURES — which specific class bigrams and unigrams
     most distinguish A from B?  Log-odds ratio ranking.
  8. NL FIT BY LANGUAGE — run chunk_alphabet_decipherment-style distribution comparison
     separately on A and B.  Does the same NL best match both?

SKEPTICISM:
  - The hardcoded A/B function was ~42% wrong.  ALL prior A/B results
    (generative_chunk_model baselines, currier_register_comparison, misbinding_coherence_test, run_conditioned_transitions) may be biased.
  - Even with correct tags, 17 folios have NO $L= tag.  We exclude
    them from A/B analysis but include them in 'all'.
  - Currier's own assignments are from the 1970s — they may contain
    errors too.  We report but do not second-guess them.
  - Statistical differences could be section effects (herbal vs pharma
    vs astro) rather than genuine A/B effects.  We test this.

═══════════════════════════════════════════════════════════════════════
"""

import re, sys, io, math, json, os
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import chunk_to_str, clean_word, entropy, eva_to_glyphs, extract_words_from_line, load_chunk_equivalence_clusters, parse_one_chunk, parse_word_into_chunks

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
# EVA GLYPH TOKENIZER (from chunk_fingerprint)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']


# ═══════════════════════════════════════════════════════════════════════
# LOOP GRAMMAR — CHUNK PARSER (from chunk_fingerprint)
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
# VMS TEXT EXTRACTION  (CORRECTED CURRIER ASSIGNMENT)
# ═══════════════════════════════════════════════════════════════════════




def get_currier_language_from_header(filepath):
    """Parse the authoritative $L= tag from the IVTFF folio header.
    Returns 'A', 'B', or None if no tag found.
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            # The $L= tag appears in <! ... > metadata lines
            m = re.search(r'\$L=([AB])', line)
            if m:
                return m.group(1)
            # Also check comment lines
            low = line.lower()
            if 'language b' in low:
                return 'B'
            if 'language a' in low:
                return 'A'
            # Stop after first few header lines
            if not line.startswith('#') and not line.startswith('<') and not line == "":
                break
    return None


def get_currier_language_hardcoded(folio_num):
    """The BROKEN hardcoded function from prior phases. Kept for comparison."""
    lang_b = set()
    for f in [26,27,28,29,31,34,35,38,39,42,43,46,47,49,50,53,54]:
        lang_b.add(f)
    for f in range(75, 85):
        lang_b.add(f)
    for f in range(87, 103):
        lang_b.add(f)
    return 'B' if folio_num in lang_b else 'A'


def parse_all_folios_corrected():
    """Parse all VMS folios using CORRECT Currier language from $L= tags.
    Returns:
      word_data: dict 'all'/'A'/'B' -> list of word strings
      folio_data: list of (folio_name, lang, words) per folio
      disagreements: list of (folio_name, hardcoded, actual_tag)
    """
    word_data = {'all': [], 'A': [], 'B': []}
    folio_data = []
    disagreements = []

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)

    for filepath in folio_files:
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num:
            continue
        fnum = int(m_num.group(1))
        folio_name = filepath.stem

        # Correct assignment from header
        lang = get_currier_language_from_header(filepath)
        # Hardcoded (for comparison)
        lang_hc = get_currier_language_hardcoded(fnum)

        if lang and lang != lang_hc:
            disagreements.append((folio_name, lang_hc, lang))

        # Extract words
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
                ws = extract_words_from_line(rest)
                words.extend(ws)

        word_data['all'].extend(words)
        if lang in ('A', 'B'):
            word_data[lang].extend(words)
            folio_data.append((folio_name, lang, words))
        else:
            # No tag — include in 'all' only
            folio_data.append((folio_name, 'U', words))

    return word_data, folio_data, disagreements


# ═══════════════════════════════════════════════════════════════════════
# chunk_equivalence_classes CLUSTER LOADING
# ═══════════════════════════════════════════════════════════════════════



def assign_rare_chunks_to_clusters(chunk_to_class, word_chunk_pairs):
    """Assign unmapped chunk types to nearest cluster by context similarity."""
    all_chunk_types = set()
    for chunks, _ in word_chunk_pairs:
        all_chunk_types.update(chunks)

    mapped = set(chunk_to_class.keys())
    unmapped = [c for c in all_chunk_types if c not in mapped]
    if not unmapped:
        return chunk_to_class

    chunk_left_ctx = defaultdict(Counter)
    chunk_right_ctx = defaultdict(Counter)
    for chunks, _ in word_chunk_pairs:
        for i, c in enumerate(chunks):
            if i > 0:
                chunk_left_ctx[c][chunks[i-1]] += 1
            if i < len(chunks) - 1:
                chunk_right_ctx[c][chunks[i+1]] += 1

    cluster_left_ctx = defaultdict(Counter)
    cluster_right_ctx = defaultdict(Counter)
    for c, cls_id in chunk_to_class.items():
        for ctx, cnt in chunk_left_ctx[c].items():
            cluster_left_ctx[cls_id][ctx] += cnt
        for ctx, cnt in chunk_right_ctx[c].items():
            cluster_right_ctx[cls_id][ctx] += cnt

    all_classes = list(set(chunk_to_class.values()))
    extended = dict(chunk_to_class)
    for uc in unmapped:
        best_cls = all_classes[0]
        best_score = -1
        uc_left = chunk_left_ctx[uc]
        uc_right = chunk_right_ctx[uc]
        uc_lt = sum(uc_left.values()) + 1e-10
        uc_rt = sum(uc_right.values()) + 1e-10
        for cls_id in all_classes:
            cl = cluster_left_ctx[cls_id]
            cr = cluster_right_ctx[cls_id]
            clt = sum(cl.values()) + 1e-10
            crt = sum(cr.values()) + 1e-10
            ls = sum((uc_left[k]/uc_lt)*(cl[k]/clt) for k in uc_left if k in cl)
            rs = sum((uc_right[k]/uc_rt)*(cr[k]/crt) for k in uc_right if k in cr)
            if ls + rs > best_score:
                best_score = ls + rs
                best_cls = cls_id
        extended[uc] = best_cls
    return extended


# ═══════════════════════════════════════════════════════════════════════
# UTILITY: WORDS → CHUNK SEQUENCES → CLASS SEQUENCES
# ═══════════════════════════════════════════════════════════════════════

def words_to_chunk_pairs(word_list):
    """Convert word list to [(chunk_ids, word_str), ...]"""
    pairs = []
    for w in word_list:
        chunks, unparsed, glyphs = parse_word_into_chunks(w)
        chunk_ids = [chunk_to_str(c) for c in chunks]
        if chunk_ids:
            pairs.append((chunk_ids, w))
    return pairs


def collapse_to_classes(chunk_pairs, c2c):
    """Convert chunk sequences to class sequences."""
    return [([c2c.get(c, 'UNK') for c in chunks], w) for chunks, w in chunk_pairs]


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL TOOLS
# ═══════════════════════════════════════════════════════════════════════



def jsd(counter_a, counter_b):
    """Jensen-Shannon divergence between two frequency distributions."""
    all_keys = set(counter_a) | set(counter_b)
    tot_a = sum(counter_a.values()) + 1e-30
    tot_b = sum(counter_b.values()) + 1e-30
    p = {k: counter_a.get(k, 0) / tot_a for k in all_keys}
    q = {k: counter_b.get(k, 0) / tot_b for k in all_keys}
    m = {k: 0.5*(p[k]+q[k]) for k in all_keys}

    def kld(dist, ref):
        return sum(dist[k]*math.log2(dist[k]/ref[k]) for k in all_keys
                   if dist[k] > 0 and ref[k] > 0)
    return 0.5*kld(p, m) + 0.5*kld(q, m)


def log_odds_ratio(count_a, total_a, count_b, total_b, prior=0.5):
    """Log-odds ratio with additive smoothing."""
    rate_a = (count_a + prior) / (total_a + prior*2)
    rate_b = (count_b + prior) / (total_b + prior*2)
    return math.log2(rate_a / rate_b)


# ═══════════════════════════════════════════════════════════════════════
# CHUNK-LEVEL BIGRAM MARKOV MODEL
# ═══════════════════════════════════════════════════════════════════════

class ChunkBigramModel:
    """Simple bigram model on chunk/class sequences with Laplace smoothing."""
    def __init__(self, vocab_size=None):
        self.bigram_counts = Counter()
        self.unigram_counts = Counter()
        self.vocab_size = vocab_size  # for Laplace

    def train(self, class_pairs):
        """Train on list of (class_sequence, word_str) pairs."""
        BOS = '<S>'
        EOS = '</S>'
        for classes, _ in class_pairs:
            seq = [BOS] + classes + [EOS]
            for i in range(len(seq) - 1):
                self.bigram_counts[(seq[i], seq[i+1])] += 1
                self.unigram_counts[seq[i]] += 1
            self.unigram_counts[EOS] += 1
        if self.vocab_size is None:
            self.vocab_size = len(set(
                c for bg in self.bigram_counts for c in bg
            ))

    def log_prob(self, class_pairs):
        """Compute mean log2-prob per token on test data."""
        BOS = '<S>'
        EOS = '</S>'
        total_ll = 0.0
        total_tokens = 0
        V = max(self.vocab_size, 1)
        for classes, _ in class_pairs:
            seq = [BOS] + classes + [EOS]
            for i in range(len(seq) - 1):
                bg = (seq[i], seq[i+1])
                numer = self.bigram_counts[bg] + 1  # Laplace
                denom = self.unigram_counts[seq[i]] + V
                total_ll += math.log2(numer / denom)
                total_tokens += 1
        if total_tokens == 0:
            return 0.0
        return total_ll / total_tokens

    def perplexity(self, class_pairs):
        lp = self.log_prob(class_pairs)
        return 2**(-lp)


# ═══════════════════════════════════════════════════════════════════════
# NL CORPUS LOADING (from chunk_alphabet_decipherment)
# ═══════════════════════════════════════════════════════════════════════

def load_nl_text(path, max_words=100000):
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


def load_all_nl_corpora():
    corpora = {}
    latin_dir = DATA_DIR / 'latin_texts'
    if latin_dir.exists():
        latin_words = []
        for fp in sorted(latin_dir.glob('*.txt')):
            latin_words.extend(load_nl_text(fp, max_words=200000))
        if latin_words:
            corpora['Latin'] = latin_words[:200000]

    czech_dir = DATA_DIR / 'czech_bible_kralice'
    if czech_dir.exists():
        czech_words = []
        for fp in sorted(czech_dir.glob('**/*.txt')):
            czech_words.extend(load_nl_text(fp, max_words=200000))
        if czech_words:
            corpora['Czech'] = czech_words[:200000]

    vern_dir = DATA_DIR / 'vernacular_texts'
    if vern_dir.exists():
        lang_map = {
            'german': 'German', 'italian': 'Italian',
            'french': 'French', 'english': 'English'
        }
        for fp in sorted(vern_dir.glob('*.txt')):
            fname = fp.stem.lower()
            for key, label in lang_map.items():
                if key in fname:
                    ws = load_nl_text(fp, max_words=100000)
                    if label in corpora:
                        corpora[label].extend(ws)
                    else:
                        corpora[label] = ws
                    break
    return corpora


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def run_analysis():
    pr("=" * 72)
    pr("currier_dichotomy_resolution — RESOLVE THE CURRIER A/B DICHOTOMY")
    pr("=" * 72)
    pr()

    results = {}

    # ───────────────────────────────────────────────────────────────────
    # STEP 1: CORRECTED CORPUS SPLIT
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 1: Corrected Currier A/B corpus split")
    pr("─" * 72)
    pr()

    word_data, folio_data, disagreements = parse_all_folios_corrected()

    n_a_folios = sum(1 for _, l, _ in folio_data if l == 'A')
    n_b_folios = sum(1 for _, l, _ in folio_data if l == 'B')
    n_u_folios = sum(1 for _, l, _ in folio_data if l == 'U')

    pr(f"  Folios:  A={n_a_folios}  B={n_b_folios}  Untagged={n_u_folios}  Total={len(folio_data)}")
    pr(f"  Words:   all={len(word_data['all'])}  A={len(word_data['A'])}  B={len(word_data['B'])}")
    pr()

    pr(f"  Disagreements between hardcoded function and $L= tags: {len(disagreements)}")
    if disagreements:
        pr(f"  {'Folio':<20s} {'Hardcoded':>10s} {'$L= tag':>10s}")
        for fname, hc, actual in disagreements[:30]:
            pr(f"  {fname:<20s} {hc:>10s} {actual:>10s}")
        if len(disagreements) > 30:
            pr(f"  ... and {len(disagreements)-30} more")
    pr()

    # Impact assessment
    # Build word lists using the old broken function for comparison
    word_data_old = {'A': [], 'B': []}
    for filepath in sorted(FOLIO_DIR.glob('f*.txt'),
                           key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                           if re.match(r'f(\d+)', p.stem) else 0):
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num:
            continue
        fnum = int(m_num.group(1))
        lang_hc = get_currier_language_hardcoded(fnum)
        words = []
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f_in:
            for line in f_in:
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
        word_data_old[lang_hc].extend(words)

    pr("  IMPACT OF CORRECTION:")
    pr(f"    Old A: {len(word_data_old['A'])} words   →  Correct A: {len(word_data['A'])} words")
    pr(f"    Old B: {len(word_data_old['B'])} words   →  Correct B: {len(word_data['B'])} words")
    moved_to_b = len(word_data['B']) - len(word_data_old['B'])
    pr(f"    Net shift: {abs(moved_to_b)} words moved {'to B' if moved_to_b > 0 else 'to A'}")
    pr()

    results['corpus_split'] = {
        'n_folios_A': n_a_folios, 'n_folios_B': n_b_folios,
        'n_folios_untagged': n_u_folios,
        'n_words_A': len(word_data['A']), 'n_words_B': len(word_data['B']),
        'n_words_all': len(word_data['all']),
        'n_disagreements': len(disagreements),
        'old_A': len(word_data_old['A']), 'old_B': len(word_data_old['B']),
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 2: BUILD CLASS SEQUENCES
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 2: Build class sequences using chunk_equivalence_classes clusters")
    pr("─" * 72)
    pr()

    chunk_to_class = load_chunk_equivalence_clusters()
    pr(f"  chunk_equivalence_classes clusters loaded: {len(chunk_to_class)} chunk→class mappings")

    # Build chunk pairs for all words (needed for rare-chunk assignment)
    all_chunk_pairs = words_to_chunk_pairs(word_data['all'])
    chunk_to_class = assign_rare_chunks_to_clusters(chunk_to_class, all_chunk_pairs)
    pr(f"  After rare-chunk extension: {len(chunk_to_class)} mappings")
    pr()

    # Build per-section class sequences
    sections = {}
    for section_name in ['all', 'A', 'B']:
        cpairs = words_to_chunk_pairs(word_data[section_name])
        cls_pairs = collapse_to_classes(cpairs, chunk_to_class)
        sections[section_name] = {
            'chunk_pairs': cpairs,
            'class_pairs': cls_pairs,
            'words': word_data[section_name],
        }
        pr(f"  {section_name}: {len(cls_pairs)} words → "
           f"{sum(len(cp[0]) for cp in cls_pairs)} class tokens")

    pr()

    # Also build folio-level class features for the classifier
    folio_class_data = []
    for fname, lang, words in folio_data:
        if lang == 'U' or len(words) < 5:
            continue
        cpairs = words_to_chunk_pairs(words)
        cls_pairs = collapse_to_classes(cpairs, chunk_to_class)
        folio_class_data.append((fname, lang, cls_pairs))

    # ───────────────────────────────────────────────────────────────────
    # STEP 3: 25-CLASS DISTRIBUTIONS — A vs B
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 3: 25-class distributions — A vs B")
    pr("─" * 72)
    pr()

    def get_class_stats(cls_pairs):
        """Compute unigram, bigram, positional, word-length distributions."""
        unigram = Counter()
        bigram = Counter()
        initial = Counter()
        final = Counter()
        medial = Counter()
        word_lengths = Counter()

        for classes, _ in cls_pairs:
            word_lengths[len(classes)] += 1
            for i, c in enumerate(classes):
                unigram[c] += 1
                if i == 0:
                    initial[c] += 1
                elif i == len(classes) - 1:
                    final[c] += 1
                else:
                    medial[c] += 1
                if i > 0:
                    bigram[(classes[i-1], c)] += 1

        return {
            'unigram': unigram, 'bigram': bigram,
            'initial': initial, 'final': final, 'medial': medial,
            'word_lengths': word_lengths,
        }

    stats_A = get_class_stats(sections['A']['class_pairs'])
    stats_B = get_class_stats(sections['B']['class_pairs'])

    # Unigram comparison
    pr("  CLASS UNIGRAM FREQUENCIES:")
    pr(f"  {'Class':<8s} {'freq_A':>8s} {'freq_B':>8s} {'diff':>8s} {'log_OR':>8s}")
    tot_A = sum(stats_A['unigram'].values())
    tot_B = sum(stats_B['unigram'].values())
    all_classes = sorted(set(stats_A['unigram']) | set(stats_B['unigram']))

    class_diffs = []
    for c in all_classes:
        fa = stats_A['unigram'].get(c, 0) / max(tot_A, 1)
        fb = stats_B['unigram'].get(c, 0) / max(tot_B, 1)
        lor = log_odds_ratio(stats_A['unigram'].get(c, 0), tot_A,
                             stats_B['unigram'].get(c, 0), tot_B)
        class_diffs.append((c, fa, fb, fa-fb, lor))

    class_diffs.sort(key=lambda x: abs(x[4]), reverse=True)
    for c, fa, fb, diff, lor in class_diffs:
        marker = '***' if abs(lor) > 0.5 else '  *' if abs(lor) > 0.25 else '   '
        pr(f"  {c:<8s} {fa:>8.4f} {fb:>8.4f} {diff:>+8.4f} {lor:>+8.3f} {marker}")

    jsd_unigram = jsd(stats_A['unigram'], stats_B['unigram'])
    pr(f"\n  Unigram JSD(A,B) = {jsd_unigram:.6f}")

    # Bigram JSD
    jsd_bigram = jsd(stats_A['bigram'], stats_B['bigram'])
    pr(f"  Bigram  JSD(A,B) = {jsd_bigram:.6f}")

    # Positional JSDs
    jsd_initial = jsd(stats_A['initial'], stats_B['initial'])
    jsd_final = jsd(stats_A['final'], stats_B['final'])
    jsd_medial = jsd(stats_A['medial'], stats_B['medial'])
    pr(f"  Initial JSD(A,B) = {jsd_initial:.6f}")
    pr(f"  Final   JSD(A,B) = {jsd_final:.6f}")
    pr(f"  Medial  JSD(A,B) = {jsd_medial:.6f}")

    # Word length JSD
    jsd_wl = jsd(stats_A['word_lengths'], stats_B['word_lengths'])
    pr(f"  WordLen JSD(A,B) = {jsd_wl:.6f}")
    pr()

    # Word length distributions
    pr("  WORD LENGTH DISTRIBUTIONS (in class tokens):")
    max_len = max(max(stats_A['word_lengths']), max(stats_B['word_lengths']))
    pr(f"  {'Len':>4s} {'A freq':>8s} {'B freq':>8s} {'diff':>8s}")
    twa = sum(stats_A['word_lengths'].values())
    twb = sum(stats_B['word_lengths'].values())
    for l in range(1, min(max_len+1, 8)):
        fa = stats_A['word_lengths'].get(l, 0) / max(twa, 1)
        fb = stats_B['word_lengths'].get(l, 0) / max(twb, 1)
        pr(f"  {l:>4d} {fa:>8.4f} {fb:>8.4f} {fa-fb:>+8.4f}")
    pr()

    results['distributions'] = {
        'jsd_unigram': jsd_unigram, 'jsd_bigram': jsd_bigram,
        'jsd_initial': jsd_initial, 'jsd_final': jsd_final,
        'jsd_medial': jsd_medial, 'jsd_word_length': jsd_wl,
        'top_differential_classes': [
            {'class': c, 'freq_A': round(fa, 5), 'freq_B': round(fb, 5),
             'log_OR': round(lor, 4)}
            for c, fa, fb, _, lor in class_diffs[:10]
        ],
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 4: VOCABULARY OVERLAP
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 4: Vocabulary overlap — A vs B")
    pr("─" * 72)
    pr()

    # Word-level
    words_A = set(word_data['A'])
    words_B = set(word_data['B'])
    shared_w = words_A & words_B
    only_A_w = words_A - words_B
    only_B_w = words_B - words_A
    jaccard_w = len(shared_w) / max(len(words_A | words_B), 1)

    pr(f"  WORD TYPES:  A={len(words_A)}  B={len(words_B)}  "
       f"shared={len(shared_w)}  A-only={len(only_A_w)}  B-only={len(only_B_w)}")
    pr(f"  Jaccard(word types) = {jaccard_w:.4f}")
    pr()

    # Chunk-level
    chunks_A = set()
    chunks_B = set()
    for chunks, _ in sections['A']['chunk_pairs']:
        chunks_A.update(chunks)
    for chunks, _ in sections['B']['chunk_pairs']:
        chunks_B.update(chunks)
    shared_c = chunks_A & chunks_B
    jaccard_c = len(shared_c) / max(len(chunks_A | chunks_B), 1)

    pr(f"  CHUNK TYPES: A={len(chunks_A)}  B={len(chunks_B)}  "
       f"shared={len(shared_c)}  A-only={len(chunks_A-chunks_B)}  B-only={len(chunks_B-chunks_A)}")
    pr(f"  Jaccard(chunk types) = {jaccard_c:.4f}")
    pr()

    # Class bigram overlap
    bigrams_A = set(stats_A['bigram'])
    bigrams_B = set(stats_B['bigram'])
    shared_bg = bigrams_A & bigrams_B
    jaccard_bg = len(shared_bg) / max(len(bigrams_A | bigrams_B), 1)

    pr(f"  CLASS BIGRAM TYPES: A={len(bigrams_A)}  B={len(bigrams_B)}  "
       f"shared={len(shared_bg)}")
    pr(f"  Jaccard(class bigrams) = {jaccard_bg:.4f}")
    pr()

    # Top A-only and B-only words by frequency
    word_freq_A = Counter(word_data['A'])
    word_freq_B = Counter(word_data['B'])
    top_a_only = sorted(((w, word_freq_A[w]) for w in only_A_w),
                        key=lambda x: -x[1])[:15]
    top_b_only = sorted(((w, word_freq_B[w]) for w in only_B_w),
                        key=lambda x: -x[1])[:15]

    pr("  Top A-only words (not in B):  " +
       ", ".join(f"{w}({n})" for w, n in top_a_only))
    pr("  Top B-only words (not in B):  " +
       ", ".join(f"{w}({n})" for w, n in top_b_only))
    pr()

    results['vocabulary'] = {
        'word_types_A': len(words_A), 'word_types_B': len(words_B),
        'word_shared': len(shared_w), 'word_jaccard': round(jaccard_w, 4),
        'chunk_types_A': len(chunks_A), 'chunk_types_B': len(chunks_B),
        'chunk_shared': len(shared_c), 'chunk_jaccard': round(jaccard_c, 4),
        'class_bigram_types_A': len(bigrams_A),
        'class_bigram_types_B': len(bigrams_B),
        'class_bigram_shared': len(shared_bg),
        'class_bigram_jaccard': round(jaccard_bg, 4),
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 5: MARKOV CROSS-PERPLEXITY
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 5: Markov cross-perplexity — A vs B")
    pr("─" * 72)
    pr()

    # Split each section 80/20 for within-section perplexity
    def split_80_20(pairs):
        n = len(pairs)
        idx = list(range(n))
        random.shuffle(idx)
        cut = int(0.8 * n)
        train = [pairs[i] for i in idx[:cut]]
        test = [pairs[i] for i in idx[cut:]]
        return train, test

    cls_A = sections['A']['class_pairs']
    cls_B = sections['B']['class_pairs']

    train_A, test_A = split_80_20(cls_A)
    train_B, test_B = split_80_20(cls_B)

    # Within-section models
    model_A = ChunkBigramModel(vocab_size=30)
    model_A.train(train_A)
    model_B = ChunkBigramModel(vocab_size=30)
    model_B.train(train_B)

    # Full-section models (for cross-perplexity)
    model_A_full = ChunkBigramModel(vocab_size=30)
    model_A_full.train(cls_A)
    model_B_full = ChunkBigramModel(vocab_size=30)
    model_B_full.train(cls_B)

    ppl_A_on_A = model_A.perplexity(test_A)
    ppl_B_on_B = model_B.perplexity(test_B)
    ppl_A_on_B = model_A_full.perplexity(cls_B)  # trained on A, tested on B
    ppl_B_on_A = model_B_full.perplexity(cls_A)  # trained on B, tested on A

    pr("  Cross-perplexity matrix (class bigrams, Laplace-smoothed):")
    pr(f"  {'Train \\ Test':<16s} {'Test A':>10s} {'Test B':>10s}")
    pr(f"  {'Model A':<16s} {ppl_A_on_A:>10.2f} {ppl_A_on_B:>10.2f}")
    pr(f"  {'Model B':<16s} {ppl_B_on_A:>10.2f} {ppl_B_on_B:>10.2f}")
    pr()

    # Interpretation
    cross_ratio_AB = ppl_A_on_B / max(ppl_A_on_A, 0.01)
    cross_ratio_BA = ppl_B_on_A / max(ppl_B_on_B, 0.01)
    pr(f"  Cross/within ratio: A→B = {cross_ratio_AB:.3f}  B→A = {cross_ratio_BA:.3f}")
    if cross_ratio_AB < 1.15 and cross_ratio_BA < 1.15:
        pr("  → SAME grammar: cross-perplexity ≈ within-perplexity")
    elif cross_ratio_AB < 1.5 and cross_ratio_BA < 1.5:
        pr("  → SIMILAR grammar with moderate divergence")
    else:
        pr("  → DIFFERENT grammar: significant cross-perplexity penalty")
    pr()

    results['cross_perplexity'] = {
        'ppl_A_on_A': round(ppl_A_on_A, 3),
        'ppl_B_on_B': round(ppl_B_on_B, 3),
        'ppl_A_on_B': round(ppl_A_on_B, 3),
        'ppl_B_on_A': round(ppl_B_on_A, 3),
        'ratio_AB': round(cross_ratio_AB, 4),
        'ratio_BA': round(cross_ratio_BA, 4),
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 6: PERMUTATION TEST for JSD significance
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 6: Permutation test — is A/B split significant?")
    pr("─" * 72)
    pr()

    N_PERM = 1000
    # Pool all folio-level data with known labels
    labeled_folios = [(fname, lang, words) for fname, lang, words in folio_data
                      if lang in ('A', 'B') and len(words) >= 5]
    all_labels = [lang for _, lang, _ in labeled_folios]
    all_word_lists = [words for _, _, words in labeled_folios]

    # Real JSD (already computed)
    real_jsd_uni = jsd_unigram
    real_jsd_bg = jsd_bigram

    # Permutation distribution
    null_jsd_uni = []
    null_jsd_bg = []
    pr(f"  Running {N_PERM} permutations (shuffling folio labels)...")

    for perm_i in range(N_PERM):
        shuf_labels = list(all_labels)
        random.shuffle(shuf_labels)

        perm_words = {'A': [], 'B': []}
        for i, lab in enumerate(shuf_labels):
            perm_words[lab].extend(all_word_lists[i])

        perm_pairs_A = words_to_chunk_pairs(perm_words['A'])
        perm_cls_A = collapse_to_classes(perm_pairs_A, chunk_to_class)
        perm_pairs_B = words_to_chunk_pairs(perm_words['B'])
        perm_cls_B = collapse_to_classes(perm_pairs_B, chunk_to_class)

        ps_A = get_class_stats(perm_cls_A)
        ps_B = get_class_stats(perm_cls_B)

        null_jsd_uni.append(jsd(ps_A['unigram'], ps_B['unigram']))
        null_jsd_bg.append(jsd(ps_A['bigram'], ps_B['bigram']))

    null_uni_arr = np.array(null_jsd_uni)
    null_bg_arr = np.array(null_jsd_bg)

    p_uni = np.mean(null_uni_arr >= real_jsd_uni)
    p_bg = np.mean(null_bg_arr >= real_jsd_bg)

    z_uni = (real_jsd_uni - np.mean(null_uni_arr)) / max(np.std(null_uni_arr), 1e-10)
    z_bg = (real_jsd_bg - np.mean(null_bg_arr)) / max(np.std(null_bg_arr), 1e-10)

    pr(f"  Unigram JSD:  real={real_jsd_uni:.6f}  null={np.mean(null_uni_arr):.6f}±{np.std(null_uni_arr):.6f}  z={z_uni:+.2f}  p={p_uni:.4f}")
    pr(f"  Bigram  JSD:  real={real_jsd_bg:.6f}  null={np.mean(null_bg_arr):.6f}±{np.std(null_bg_arr):.6f}  z={z_bg:+.2f}  p={p_bg:.4f}")
    pr()

    if p_uni < 0.01 and p_bg < 0.01:
        pr("  → A/B split is HIGHLY SIGNIFICANT at both unigram and bigram levels")
    elif p_uni < 0.05 or p_bg < 0.05:
        pr("  → A/B split is SIGNIFICANT at one or both levels")
    else:
        pr("  → A/B split is NOT SIGNIFICANT — could arise from random partition")
    pr()

    results['permutation_test'] = {
        'n_permutations': N_PERM,
        'unigram_jsd_real': round(real_jsd_uni, 6),
        'unigram_jsd_null_mean': round(float(np.mean(null_uni_arr)), 6),
        'unigram_jsd_null_std': round(float(np.std(null_uni_arr)), 6),
        'unigram_z': round(z_uni, 3),
        'unigram_p': round(p_uni, 4),
        'bigram_jsd_real': round(real_jsd_bg, 6),
        'bigram_jsd_null_mean': round(float(np.mean(null_bg_arr)), 6),
        'bigram_jsd_null_std': round(float(np.std(null_bg_arr)), 6),
        'bigram_z': round(z_bg, 3),
        'bigram_p': round(p_bg, 4),
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 7: FOLIO-LEVEL CLASSIFIER
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 7: Folio-level classifier — can we distinguish A from B?")
    pr("─" * 72)
    pr()

    # Build feature matrix: class bigram frequencies per folio
    all_bg_types = sorted(set(stats_A['bigram']) | set(stats_B['bigram']))
    bg_to_idx = {bg: i for i, bg in enumerate(all_bg_types)}
    n_features = len(all_bg_types)

    X = np.zeros((len(folio_class_data), n_features))
    y = np.zeros(len(folio_class_data))

    for row, (fname, lang, cls_pairs) in enumerate(folio_class_data):
        bg_counts = Counter()
        for classes, _ in cls_pairs:
            for i in range(len(classes) - 1):
                bg_counts[(classes[i], classes[i+1])] += 1
        total = sum(bg_counts.values()) + 1e-10
        for bg, cnt in bg_counts.items():
            if bg in bg_to_idx:
                X[row, bg_to_idx[bg]] = cnt / total
        y[row] = 1.0 if lang == 'B' else 0.0

    # Nearest-centroid classifier with leave-one-out cross-validation
    # (AUDIT: comment previously claimed "logistic regression" — the printed
    # output was always honest; label corrected to match the implementation)
    centroid_A = np.mean(X[y == 0], axis=0)
    centroid_B = np.mean(X[y == 1], axis=0)

    correct = 0
    predictions = []
    for i in range(len(y)):
        # LOO: recompute centroids without sample i
        mask_A = (y == 0)
        mask_B = (y == 1)
        mask_A[i] = False
        mask_B[i] = False
        if mask_A.sum() == 0 or mask_B.sum() == 0:
            continue
        c_A = np.mean(X[mask_A], axis=0)
        c_B = np.mean(X[mask_B], axis=0)
        dist_A = np.sum((X[i] - c_A)**2)
        dist_B = np.sum((X[i] - c_B)**2)
        pred = 'B' if dist_B < dist_A else 'A'
        actual = 'B' if y[i] == 1 else 'A'
        predictions.append((folio_class_data[i][0], actual, pred))
        if pred == actual:
            correct += 1

    loo_acc = correct / max(len(predictions), 1)
    pr(f"  Nearest-centroid classifier (LOO-CV on class-bigram features):")
    pr(f"  Accuracy: {correct}/{len(predictions)} = {loo_acc:.3f}")
    pr()

    # Null accuracy (majority class)
    n_class_A = sum(1 for _, a, _ in predictions if a == 'A')
    n_class_B = sum(1 for _, a, _ in predictions if a == 'B')
    majority_acc = max(n_class_A, n_class_B) / max(len(predictions), 1)
    pr(f"  Majority baseline: {majority_acc:.3f} ({'A' if n_class_A >= n_class_B else 'B'} dominant)")
    pr(f"  Lift over majority: {loo_acc - majority_acc:+.3f}")
    pr()

    # Show misclassifications
    misclass = [(fn, act, pred) for fn, act, pred in predictions if act != pred]
    if misclass:
        pr(f"  Misclassified folios ({len(misclass)}):")
        for fn, act, pred in misclass[:20]:
            pr(f"    {fn:<20s}  actual={act}  predicted={pred}")
        if len(misclass) > 20:
            pr(f"    ... and {len(misclass)-20} more")
    pr()

    # Permutation test for classifier
    N_PERM_CLF = 500
    null_accs = []
    for _ in range(N_PERM_CLF):
        y_shuf = y.copy()
        np.random.shuffle(y_shuf)
        # AUDIT: the null previously used RESUBSTITUTION (centroids computed
        # with sample i included) while the real metric used LOO — an
        # inflated null that made the test conservative. Same LOO protocol
        # now, via O(1) leave-one-out on class sums.
        mA = (y_shuf == 0)
        mB = (y_shuf == 1)
        nA, nB = int(mA.sum()), int(mB.sum())
        if nA < 2 or nB < 2:
            continue
        sum_A = X[mA].sum(axis=0)
        sum_B = X[mB].sum(axis=0)
        corr_s = 0
        for i in range(len(y_shuf)):
            if y_shuf[i] == 0:
                c_A_s = (sum_A - X[i]) / (nA - 1)
                c_B_s = sum_B / nB
            else:
                c_A_s = sum_A / nA
                c_B_s = (sum_B - X[i]) / (nB - 1)
            d_A = np.sum((X[i] - c_A_s)**2)
            d_B = np.sum((X[i] - c_B_s)**2)
            pred_s = 1 if d_B < d_A else 0
            if pred_s == y_shuf[i]:
                corr_s += 1
        null_accs.append(corr_s / len(y_shuf))

    null_acc_arr = np.array(null_accs)
    clf_p = np.mean(null_acc_arr >= loo_acc)
    clf_z = (loo_acc - np.mean(null_acc_arr)) / max(np.std(null_acc_arr), 1e-10)

    pr(f"  Classifier permutation test ({N_PERM_CLF} shuffles):")
    pr(f"    Real LOO accuracy: {loo_acc:.3f}")
    pr(f"    Null accuracy: {np.mean(null_acc_arr):.3f} ± {np.std(null_acc_arr):.3f}")
    pr(f"    z = {clf_z:+.2f}, p = {clf_p:.4f}")
    pr()

    results['classifier'] = {
        'loo_accuracy': round(loo_acc, 4),
        'majority_baseline': round(majority_acc, 4),
        'n_misclassified': len(misclass),
        'clf_z': round(clf_z, 3),
        'clf_p': round(clf_p, 4),
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 8: DIFFERENTIAL FEATURES — top distinguishing class bigrams
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 8: Differential features — top distinguishing class bigrams")
    pr("─" * 72)
    pr()

    bg_total_A = sum(stats_A['bigram'].values())
    bg_total_B = sum(stats_B['bigram'].values())

    bg_lor = []
    for bg in sorted(set(stats_A['bigram']) | set(stats_B['bigram'])):
        ca = stats_A['bigram'].get(bg, 0)
        cb = stats_B['bigram'].get(bg, 0)
        if ca + cb < 10:
            continue  # skip rare bigrams
        lor = log_odds_ratio(ca, bg_total_A, cb, bg_total_B)
        bg_lor.append((bg, ca, cb, lor))

    bg_lor.sort(key=lambda x: x[3], reverse=True)

    pr("  Top 15 A-enriched class bigrams:")
    pr(f"  {'Bigram':<16s} {'count_A':>8s} {'count_B':>8s} {'log_OR':>8s}")
    for bg, ca, cb, lor in bg_lor[:15]:
        pr(f"  {str(bg):<16s} {ca:>8d} {cb:>8d} {lor:>+8.3f}")

    pr()
    pr("  Top 15 B-enriched class bigrams:")
    pr(f"  {'Bigram':<16s} {'count_A':>8s} {'count_B':>8s} {'log_OR':>8s}")
    for bg, ca, cb, lor in bg_lor[-15:]:
        pr(f"  {str(bg):<16s} {ca:>8d} {cb:>8d} {lor:>+8.3f}")
    pr()

    results['differential_bigrams'] = {
        'A_enriched': [{'bigram': f"{bg[0]}→{bg[1]}", 'count_A': ca, 'count_B': cb,
                        'log_OR': round(lor, 4)}
                       for bg, ca, cb, lor in bg_lor[:15]],
        'B_enriched': [{'bigram': f"{bg[0]}→{bg[1]}", 'count_A': ca, 'count_B': cb,
                        'log_OR': round(lor, 4)}
                       for bg, ca, cb, lor in bg_lor[-15:]],
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 9: NL FIT — SEPARATELY FOR A AND B
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 9: NL distribution fit — separately for A and B")
    pr("─" * 72)
    pr()

    corpora = load_all_nl_corpora()
    pr(f"  Loaded {len(corpora)} NL corpora: {', '.join(corpora.keys())}")
    pr()

    # Compute letter unigram distributions for NL
    nl_letter_dists = {}
    for lang_name, words in corpora.items():
        lcount = Counter()
        for w in words:
            for ch in w:
                lcount[ch] += 1
        nl_letter_dists[lang_name] = lcount

    # For VMS A and B: class unigram distributions (already computed)
    # Compare each VMS section to each NL via JSD on rank-normalized distributions
    def rank_dist(counter, k=25):
        """Return sorted frequency vector (top k), L1-normalized."""
        vals = sorted(counter.values(), reverse=True)[:k]
        total = sum(vals) + 1e-30
        return [v/total for v in vals]

    pr("  Rank-frequency JSD (top-25 classes vs top-25 letters):")
    pr(f"  {'NL Language':<14s} {'JSD vs A':>10s} {'JSD vs B':>10s} {'diff':>10s}")

    nl_fit_results = {}
    for lang_name in sorted(corpora.keys()):
        # Build rank-distribution Counters
        rank_A = Counter({i: v for i, v in enumerate(rank_dist(stats_A['unigram']))})
        rank_B = Counter({i: v for i, v in enumerate(rank_dist(stats_B['unigram']))})
        rank_NL = Counter({i: v for i, v in enumerate(rank_dist(nl_letter_dists[lang_name]))})
        jsd_a = jsd(rank_A, rank_NL)
        jsd_b = jsd(rank_B, rank_NL)
        pr(f"  {lang_name:<14s} {jsd_a:>10.6f} {jsd_b:>10.6f} {jsd_a-jsd_b:>+10.6f}")
        nl_fit_results[lang_name] = {'jsd_A': round(jsd_a, 6), 'jsd_B': round(jsd_b, 6)}

    pr()

    # Entropy comparison
    h_A = entropy(stats_A['unigram'])
    h_B = entropy(stats_B['unigram'])
    pr(f"  Class-unigram entropy: A={h_A:.4f} bits  B={h_B:.4f} bits")
    pr()

    # Word-level entropy
    h_word_A = entropy(Counter(word_data['A']))
    h_word_B = entropy(Counter(word_data['B']))
    pr(f"  Word-unigram entropy: A={h_word_A:.4f} bits  B={h_word_B:.4f} bits")
    pr()

    results['nl_fit'] = nl_fit_results
    results['entropy'] = {
        'class_unigram_A': round(h_A, 4), 'class_unigram_B': round(h_B, 4),
        'word_unigram_A': round(h_word_A, 4), 'word_unigram_B': round(h_word_B, 4),
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 10: SECTION EFFECT TEST
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 10: Section effect — is A/B a proxy for manuscript section?")
    pr("─" * 72)
    pr()

    # Assign sections based on folio number ranges
    def get_section(folio_name):
        m = re.match(r'f(\d+)', folio_name)
        if not m:
            return 'unknown'
        n = int(m.group(1))
        if n <= 57:
            return 'herbal'
        elif n <= 67:
            return 'astro'
        elif n <= 73:
            return 'cosmo'
        elif n <= 84:
            return 'bio'
        elif n <= 86:
            return 'bio_fold'
        elif n <= 102:
            return 'pharma'
        else:
            return 'stars_text'

    section_lang = defaultdict(lambda: Counter())
    section_words = defaultdict(list)
    for fname, lang, words in folio_data:
        if lang == 'U':
            continue
        sec = get_section(fname)
        section_lang[sec][lang] += 1
        section_words[sec].extend(words)

    pr("  Section vs Currier language distribution:")
    pr(f"  {'Section':<14s} {'A folios':>10s} {'B folios':>10s} {'% B':>8s} {'words':>8s}")
    for sec in ['herbal', 'astro', 'cosmo', 'bio', 'bio_fold', 'pharma', 'stars_text']:
        na = section_lang[sec]['A']
        nb = section_lang[sec]['B']
        pct_b = nb / max(na + nb, 1) * 100
        nw = len(section_words.get(sec, []))
        pr(f"  {sec:<14s} {na:>10d} {nb:>10d} {pct_b:>7.1f}% {nw:>8d}")
    pr()

    # Within-section A/B JSD (where sections have both A and B)
    pr("  Within-section A/B JSD (sections with both A and B folios):")
    mixed_sections = [sec for sec in section_lang
                      if section_lang[sec]['A'] > 0 and section_lang[sec]['B'] > 0]

    for sec in mixed_sections:
        sec_words_A = []
        sec_words_B = []
        for fname, lang, words in folio_data:
            if get_section(fname) == sec:
                if lang == 'A':
                    sec_words_A.extend(words)
                elif lang == 'B':
                    sec_words_B.extend(words)

        if len(sec_words_A) < 50 or len(sec_words_B) < 50:
            continue

        cp_A = words_to_chunk_pairs(sec_words_A)
        cl_A = collapse_to_classes(cp_A, chunk_to_class)
        cp_B = words_to_chunk_pairs(sec_words_B)
        cl_B = collapse_to_classes(cp_B, chunk_to_class)

        ss_A = get_class_stats(cl_A)
        ss_B = get_class_stats(cl_B)

        within_jsd = jsd(ss_A['unigram'], ss_B['unigram'])
        pr(f"    {sec:<14s}  A={len(sec_words_A):>5d} words  B={len(sec_words_B):>5d} words  "
           f"JSD={within_jsd:.6f}")
    pr()

    # Compare: between-section JSD for same language
    pr("  Between-section JSD for SAME language (A only, herbal vs others):")
    for sec in ['pharma', 'bio', 'stars_text']:
        if sec not in section_words or 'herbal' not in section_words:
            continue
        # Get A-words from herbal and from this section
        herbal_A = []
        other_A = []
        for fname, lang, words in folio_data:
            if lang != 'A':
                continue
            if get_section(fname) == 'herbal':
                herbal_A.extend(words)
            elif get_section(fname) == sec:
                other_A.extend(words)

        if len(herbal_A) < 50 or len(other_A) < 50:
            continue

        cp_h = words_to_chunk_pairs(herbal_A)
        cl_h = collapse_to_classes(cp_h, chunk_to_class)
        cp_o = words_to_chunk_pairs(other_A)
        cl_o = collapse_to_classes(cp_o, chunk_to_class)

        ss_h = get_class_stats(cl_h)
        ss_o = get_class_stats(cl_o)

        between_jsd = jsd(ss_h['unigram'], ss_o['unigram'])
        pr(f"    herbal-A vs {sec}-A  ({len(herbal_A)} vs {len(other_A)} words)  "
           f"JSD={between_jsd:.6f}")
    pr()

    results['section_analysis'] = {
        'mixed_sections': mixed_sections,
        'section_lang_counts': {sec: dict(counts) for sec, counts in section_lang.items()},
    }

    # ───────────────────────────────────────────────────────────────────
    # STEP 11: GLYPH-LEVEL COMPARISON
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 11: Glyph-level A vs B comparison")
    pr("─" * 72)
    pr()

    glyph_counts_A = Counter()
    glyph_counts_B = Counter()
    for w in word_data['A']:
        for g in eva_to_glyphs(w):
            glyph_counts_A[g] += 1
    for w in word_data['B']:
        for g in eva_to_glyphs(w):
            glyph_counts_B[g] += 1

    glyph_jsd = jsd(glyph_counts_A, glyph_counts_B)
    pr(f"  Glyph-level JSD(A,B) = {glyph_jsd:.6f}")
    pr()

    g_total_A = sum(glyph_counts_A.values())
    g_total_B = sum(glyph_counts_B.values())
    all_glyphs = sorted(set(glyph_counts_A) | set(glyph_counts_B),
                        key=lambda g: -(glyph_counts_A.get(g, 0) + glyph_counts_B.get(g, 0)))

    pr(f"  {'Glyph':<8s} {'freq_A':>8s} {'freq_B':>8s} {'diff':>8s} {'log_OR':>8s}")
    for g in all_glyphs[:25]:
        fa = glyph_counts_A.get(g, 0) / max(g_total_A, 1)
        fb = glyph_counts_B.get(g, 0) / max(g_total_B, 1)
        lor = log_odds_ratio(glyph_counts_A.get(g, 0), g_total_A,
                             glyph_counts_B.get(g, 0), g_total_B)
        marker = '***' if abs(lor) > 0.5 else '  *' if abs(lor) > 0.25 else '   '
        pr(f"  {g:<8s} {fa:>8.4f} {fb:>8.4f} {fa-fb:>+8.4f} {lor:>+8.3f} {marker}")
    pr()

    results['glyph_jsd'] = round(glyph_jsd, 6)

    # ───────────────────────────────────────────────────────────────────
    # STEP 12: SYNTHESIS AND CONCLUSIONS
    # ───────────────────────────────────────────────────────────────────
    pr("─" * 72)
    pr("STEP 12: Synthesis and conclusions")
    pr("─" * 72)
    pr()

    pr("  CRITICAL FINDING 1: PRIOR A/B ASSIGNMENTS WERE WRONG")
    pr(f"    The hardcoded get_currier_language() function in 8+ prior scripts")
    pr(f"    disagrees with the authoritative $L= folio tags on {len(disagreements)} folios.")
    pr(f"    This is a ~{len(disagreements)/len(folio_data)*100:.0f}% error rate.")
    pr(f"    ALL prior A/B results (Phases 3, 63, 68, 98) are contaminated.")
    pr()

    pr("  FINDING 2: DISTRIBUTIONAL DIVERGENCE")
    pr(f"    Class unigram JSD = {jsd_unigram:.6f}")
    pr(f"    Class bigram  JSD = {jsd_bigram:.6f}")
    pr(f"    Glyph-level   JSD = {glyph_jsd:.6f}")
    if p_uni < 0.01:
        pr(f"    Permutation test: SIGNIFICANT (p={p_uni:.4f}, z={z_uni:+.1f})")
    else:
        pr(f"    Permutation test: NOT SIGNIFICANT (p={p_uni:.4f}, z={z_uni:+.1f})")
    pr()

    pr("  FINDING 3: GRAMMAR SHARING")
    pr(f"    Cross-perplexity ratio A→B = {cross_ratio_AB:.3f}, B→A = {cross_ratio_BA:.3f}")
    if cross_ratio_AB < 1.15 and cross_ratio_BA < 1.15:
        pr("    → A and B share essentially the SAME chunk grammar")
    elif cross_ratio_AB < 1.5 and cross_ratio_BA < 1.5:
        pr("    → A and B have SIMILAR but distinguishable grammars")
    else:
        pr("    → A and B have DIFFERENT chunk grammars")
    pr()

    pr("  FINDING 4: VOCABULARY OVERLAP")
    pr(f"    Word Jaccard = {jaccard_w:.4f}")
    pr(f"    Chunk Jaccard = {jaccard_c:.4f}")
    pr(f"    Class bigram Jaccard = {jaccard_bg:.4f}")
    pr()

    pr("  FINDING 5: CLASSIFIER")
    pr(f"    LOO-CV accuracy = {loo_acc:.3f} (majority baseline = {majority_acc:.3f})")
    pr(f"    z = {clf_z:+.2f}, p = {clf_p:.4f}")
    pr()

    pr("  OVERALL ASSESSMENT:")
    if p_uni < 0.01 and loo_acc > majority_acc + 0.1 and cross_ratio_AB < 1.3:
        pr("    A and B differ in VOCABULARY (class distribution) but share")
        pr("    the same GRAMMAR (transition structure). This is consistent with")
        pr("    REGISTER VARIATION within a single encoding system — different")
        pr("    topics or content sections using the same notational rules,")
        pr("    analogous to legal vs medical Latin.")
    elif p_uni >= 0.05:
        pr("    The A/B distinction is NOT statistically significant at the")
        pr("    25-class level. The dichotomy may be an artifact of the")
        pr("    hardcoded misassignment, or it may only manifest at finer")
        pr("    glyph/word levels, not at the chunk-class abstraction.")
    else:
        pr("    A and B show BOTH vocabulary AND grammar divergence,")
        pr("    suggesting more fundamental differences than register alone.")
    pr()

    # ───────────────────────────────────────────────────────────────────
    # SAVE RESULTS
    # ───────────────────────────────────────────────────────────────────
    json_path = RESULTS_DIR / 'currier_dichotomy_resolution.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    txt_path = RESULTS_DIR / 'currier_dichotomy_resolution.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))

    pr(f"  Results saved to {json_path}")
    pr(f"  Log saved to {txt_path}")


if __name__ == '__main__':
    run_analysis()
