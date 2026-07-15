#!/usr/bin/env python3
"""
Phase 100 — Targeted Decipherment with the 25-Class Alphabet

═══════════════════════════════════════════════════════════════════════

OBJECTIVE:
  Treat the 25 equivalence classes (Phase 86) as a 25-symbol alphabet.
  Collapse VMS text to this alphabet and attempt substitution-cipher
  decipherment against candidate natural languages: Latin, Czech,
  German, Italian, French, English.

METHOD:
  1. Collapse all VMS words to 25-class sequences using the
     nearest-neighbour extended mapping (Phase 98).
  2. Compute for collapsed VMS:
     - Unigram frequencies of the 25 classes
     - Bigram (class-pair) frequencies
     - Positional distributions (word-initial, word-final, medial)
     - Word-length distribution
  3. For each candidate NL corpus:
     a. Extract letter-level statistics: unigram, bigram, positional,
        word-length distributions
     b. Compute similarity between VMS class distributions and NL
        letter distributions using JSD (Jensen-Shannon divergence)
     c. Find optimal substitution via:
        - Unigram frequency matching (baseline)
        - Bigram frequency matching via Hungarian algorithm
        - Hill-climbing: swap pairs to maximize bigram log-likelihood
          of the "deciphered" text under the NL bigram model
     d. Apply best substitution and count dictionary word matches
  4. NULL MODEL: For each NL, generate 500 random permutations of
     the 25→26 mapping, apply each, count dictionary hits. Compute
     z-score of the optimized mapping vs null distribution.
  5. Cross-validation: Hold out 20% of VMS text, optimize on 80%,
     test dictionary hit rate on held-out 20%.

CRITICAL SKEPTICISM:
  - 25 equivalence classes ≠ 25 phonemes or letters. C0 alone has
    57 members spanning onset variants (ch.e.d.y, sh.e.y, y, etc.).
    These may represent syllable-types, not single phonemes.
  - Simple substitution is the WEAKEST plausible hypothesis. If VMS
    uses polyalphabetic, homophonic, or transposition ciphering,
    this test will fail — and the failure is informative.
  - The NL alphabets have 22-42 letters; the VMS has exactly 25
    classes. Mismatch in alphabet size requires handling (null symbol,
    merging rare NL letters, etc.).
  - Dictionary hits from frequency matching alone can be spurious.
    Short words (2-3 letters) will match by chance. Must weight by
    word length and compute expected random hit rate.
  - The Czech Bible Kralice is contemporaneous (1613) with the VMS's
    estimated date. Latin Vulgate even older. These are the strongest
    a priori candidates by provenance.
  - Even a POSITIVE result (above-chance dictionary hits) does not
    prove decipherment — it could reflect structural isomorphism
    between two unrelated systems. Must test specificity: does only
    ONE language produce hits, or do multiple?

═══════════════════════════════════════════════════════════════════════
"""

import re, sys, io, math, json, os
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR  = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
FOLIO_DIR   = PROJECT_DIR / 'folios'
DATA_DIR    = PROJECT_DIR / 'data'
LATIN_DIR   = DATA_DIR / 'latin_texts'
VERN_DIR    = DATA_DIR / 'vernacular_texts'
CZECH_DIR   = DATA_DIR / 'czech_bible_kralice'
RESULTS_DIR = PROJECT_DIR / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(42)
random.seed(42)


# ═══════════════════════════════════════════════════════════════════════
# EVA GLYPH TOKENIZER (from Phase 85/98)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']

def eva_to_glyphs(word):
    glyphs = []
    i = 0
    w = word.lower()
    while i < len(w):
        if i + 2 < len(w) and w[i:i+3] in GALLOWS_TRI:
            glyphs.append(w[i:i+3]); i += 3
        elif i + 1 < len(w) and w[i:i+2] in GALLOWS_BI:
            glyphs.append(w[i:i+2]); i += 2
        else:
            glyphs.append(w[i]); i += 1
    return glyphs


# ═══════════════════════════════════════════════════════════════════════
# MAURO'S LOOP GRAMMAR — CHUNK PARSER (from Phase 85/98)
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

def parse_one_chunk(glyphs, pos):
    start = pos
    chunk = []
    if pos < len(glyphs) and glyphs[pos] in SLOT1:
        chunk.append(glyphs[pos]); pos += 1
    if pos < len(glyphs):
        if glyphs[pos] in SLOT2_RUNS:
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT2_RUNS and count < 3:
                chunk.append(glyphs[pos]); pos += 1; count += 1
        elif glyphs[pos] in SLOT2_SINGLE:
            chunk.append(glyphs[pos]); pos += 1
    if pos < len(glyphs) and glyphs[pos] in SLOT3:
        chunk.append(glyphs[pos]); pos += 1
    if pos < len(glyphs):
        if glyphs[pos] in SLOT4_RUNS:
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT4_RUNS and count < 3:
                chunk.append(glyphs[pos]); pos += 1; count += 1
        elif glyphs[pos] in SLOT4_SINGLE:
            chunk.append(glyphs[pos]); pos += 1
    if pos < len(glyphs) and glyphs[pos] in SLOT5:
        chunk.append(glyphs[pos]); pos += 1
    if pos == start:
        return None, pos
    return chunk, pos


def parse_word_into_chunks(word_str):
    glyphs = eva_to_glyphs(word_str)
    chunks = []
    unparsed = []
    pos = 0
    while pos < len(glyphs) and len(chunks) < MAX_CHUNKS:
        chunk, new_pos = parse_one_chunk(glyphs, pos)
        if chunk is None:
            unparsed.append(glyphs[pos]); pos += 1
        else:
            chunks.append(chunk); pos = new_pos
    while pos < len(glyphs):
        unparsed.append(glyphs[pos]); pos += 1
    return chunks, unparsed


def chunk_to_str(chunk):
    return '.'.join(chunk)


# ═══════════════════════════════════════════════════════════════════════
# VMS TEXT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════

def clean_word(tok):
    tok = re.sub(r'\[([^:\]]+):[^\]]*\]', r'\1', tok)
    tok = re.sub(r'\{[^}]*\}', '', tok)
    tok = re.sub(r'[^a-z]', '', tok.lower())
    return tok

def extract_words_from_line(text):
    text = text.replace('<%>', '').replace('<$>', '').strip()
    text = re.sub(r'@\d+;', '', text)
    text = re.sub(r'<[^>]*>', '', text)
    words = []
    for tok in re.split(r'[.\s]+', text):
        for subtok in re.split(r',', tok):
            c = clean_word(subtok.strip())
            if c:
                words.append(c)
    return words

def get_currier_language(folio_num):
    lang_b = set()
    for f in [26,27,28,29,31,34,35,38,39,42,43,46,47,49,50,53,54]:
        lang_b.add(f)
    for f in range(75, 85):
        lang_b.add(f)
    for f in range(87, 103):
        lang_b.add(f)
    return 'B' if folio_num in lang_b else 'A'

def parse_all_folios():
    result = {'all': [], 'A': [], 'B': []}
    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)
    for filepath in folio_files:
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num: continue
        fnum = int(m_num.group(1))
        lang = get_currier_language(fnum)
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line: continue
                m = re.match(r'<([^>]+)>', line)
                if not m: continue
                rest = line[m.end():].strip()
                if not rest: continue
                words = extract_words_from_line(rest)
                result['all'].extend(words)
                result[lang].extend(words)
    return result


# ═══════════════════════════════════════════════════════════════════════
# PHASE 86 CLUSTER MAPPING (from Phase 98)
# ═══════════════════════════════════════════════════════════════════════

def load_phase86_clusters():
    json_path = RESULTS_DIR / 'phase86_chunk_equivalence.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    chunk_to_class = {}
    for class_id, info in data['cluster_composition'].items():
        for member in info['members']:
            chunk_to_class[member] = class_id
    return chunk_to_class


def assign_rare_chunks_to_clusters(chunk_to_class, all_chunk_types, word_chunk_pairs):
    mapped = set(chunk_to_class.keys())
    unmapped = [c for c in all_chunk_types if c not in mapped]
    if not unmapped:
        return chunk_to_class

    cluster_left_ctx = defaultdict(Counter)
    cluster_right_ctx = defaultdict(Counter)
    chunk_left_ctx = defaultdict(Counter)
    chunk_right_ctx = defaultdict(Counter)

    for chunks, _ in word_chunk_pairs:
        for i, c in enumerate(chunks):
            if i > 0:
                chunk_left_ctx[c][chunks[i-1]] += 1
            if i < len(chunks) - 1:
                chunk_right_ctx[c][chunks[i+1]] += 1

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
        uc_left_total = sum(uc_left.values()) + 1e-10
        uc_right_total = sum(uc_right.values()) + 1e-10

        for cls_id in all_classes:
            cl = cluster_left_ctx[cls_id]
            cr = cluster_right_ctx[cls_id]
            cl_total = sum(cl.values()) + 1e-10
            cr_total = sum(cr.values()) + 1e-10
            left_score = sum(
                (uc_left[k] / uc_left_total) * (cl[k] / cl_total)
                for k in uc_left if k in cl
            )
            right_score = sum(
                (uc_right[k] / uc_right_total) * (cr[k] / cr_total)
                for k in uc_right if k in cr
            )
            score = left_score + right_score
            if score > best_score:
                best_score = score
                best_cls = cls_id
        extended[uc] = best_cls

    return extended


# ═══════════════════════════════════════════════════════════════════════
# COLLAPSE VMS TO 25-CLASS SEQUENCES
# ═══════════════════════════════════════════════════════════════════════

def collapse_words_to_classes(word_list, chunk_to_class):
    """Convert each VMS word to a sequence of class IDs.
    Returns list of (class_sequence, original_word) pairs.
    """
    results = []
    word_chunk_pairs = []  # for context building

    for w in word_list:
        chunks, unparsed = parse_word_into_chunks(w)
        chunk_ids = [chunk_to_str(c) for c in chunks]
        word_chunk_pairs.append((chunk_ids, w))

    # Get all chunk types
    all_chunk_types = set()
    for cids, _ in word_chunk_pairs:
        all_chunk_types.update(cids)

    # Extend mapping to cover all chunks
    extended = assign_rare_chunks_to_clusters(chunk_to_class, all_chunk_types,
                                              word_chunk_pairs)

    for chunk_ids, w in word_chunk_pairs:
        class_seq = []
        for cid in chunk_ids:
            cls = extended.get(cid, 'C0')  # fallback to C0
            # Convert "C0" -> 0, etc.
            class_seq.append(cls)
        if class_seq:
            results.append((class_seq, w))

    return results


# ═══════════════════════════════════════════════════════════════════════
# NL CORPUS LOADING
# ═══════════════════════════════════════════════════════════════════════

def load_nl_text(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()
    for marker in ['*** START OF THE PROJECT', '*** START OF THIS PROJECT']:
        idx = raw.find(marker)
        if idx >= 0:
            raw = raw[raw.index('\n', idx) + 1:]
            break
    end_idx = raw.find('*** END OF')
    if end_idx >= 0:
        raw = raw[:end_idx]
    text = raw.lower()
    # Extract words (alpha only, language-appropriate)
    words = re.findall(r'[a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþßœěůířžščťďňáéíóú]+', text)
    return words


def load_czech_bible():
    words = []
    for fp in sorted(CZECH_DIR.glob('ces1613_*_read.txt')):
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read().lower()
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'\d+', '', text)
        ws = re.findall(r'[a-záéíóúůýěžščřďťň]+', text)
        words.extend(ws)
    return words


def load_all_nl_corpora():
    """Load all available NL corpora. Returns dict of name -> word_list."""
    corpora = {}

    # Latin - combine multiple texts for larger corpus
    latin_words = []
    for fname in ['vulgate_genesis.txt', 'caesar.txt', 'apicius.txt',
                   'erasmus.txt', 'galen.txt', 'pliny.txt']:
        fp = LATIN_DIR / fname
        if fp.exists():
            latin_words.extend(load_nl_text(fp))
    if latin_words:
        corpora['Latin'] = latin_words

    # Czech
    czech_words = load_czech_bible()
    if czech_words:
        corpora['Czech'] = czech_words

    # Vernacular texts
    vern_map = {
        'German': ['german_faust.txt', 'german_ortolf_raw.txt'],
        'Italian': ['italian_cucina.txt'],
        'French': ['french_viandier.txt'],
        'English': ['english_cury.txt'],
    }
    for lang, fnames in vern_map.items():
        combined = []
        for fname in fnames:
            fp = VERN_DIR / fname
            if fp.exists():
                combined.extend(load_nl_text(fp))
        if combined:
            corpora[lang] = combined

    return corpora


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL DISTRIBUTIONS
# ═══════════════════════════════════════════════════════════════════════

def compute_unigram_dist(sequences, vocab):
    """Compute unigram frequency distribution over a vocabulary."""
    counts = Counter()
    for seq in sequences:
        for s in seq:
            counts[s] += 1
    total = sum(counts[v] for v in vocab) + 1e-10
    return {v: counts[v] / total for v in vocab}


def compute_bigram_dist(sequences, vocab):
    """Compute bigram frequency distribution."""
    counts = Counter()
    for seq in sequences:
        for i in range(1, len(seq)):
            counts[(seq[i-1], seq[i])] += 1
    total = sum(counts.values()) + 1e-10
    return counts, total


def compute_positional_dist(word_class_pairs, vocab):
    """Compute P(class | position) for initial, medial, final."""
    pos_counts = {'initial': Counter(), 'medial': Counter(), 'final': Counter()}
    for seq, _ in word_class_pairs:
        if len(seq) == 1:
            pos_counts['initial'][seq[0]] += 1
            pos_counts['final'][seq[0]] += 1
        else:
            pos_counts['initial'][seq[0]] += 1
            pos_counts['final'][seq[-1]] += 1
            for s in seq[1:-1]:
                pos_counts['medial'][s] += 1
    result = {}
    for pos, cnt in pos_counts.items():
        total = sum(cnt[v] for v in vocab) + 1e-10
        result[pos] = {v: cnt[v] / total for v in vocab}
    return result


def jsd(p, q, vocab):
    """Jensen-Shannon divergence between two distributions over vocab."""
    eps = 1e-12
    m = {v: 0.5 * (p.get(v, eps) + q.get(v, eps)) for v in vocab}
    kl_pm = sum(p.get(v, eps) * math.log2(p.get(v, eps) / m[v])
                for v in vocab if p.get(v, 0) > 0)
    kl_qm = sum(q.get(v, eps) * math.log2(q.get(v, eps) / m[v])
                for v in vocab if q.get(v, 0) > 0)
    return 0.5 * kl_pm + 0.5 * kl_qm


def word_length_dist(word_class_pairs, max_len=10):
    """Distribution of word lengths (in classes/letters)."""
    counts = Counter()
    for seq, _ in word_class_pairs:
        l = min(len(seq), max_len)
        counts[l] += 1
    total = sum(counts.values()) + 1e-10
    return {i: counts[i] / total for i in range(1, max_len + 1)}


# ═══════════════════════════════════════════════════════════════════════
# NL LETTER STATISTICS
# ═══════════════════════════════════════════════════════════════════════

def compute_nl_letter_stats(word_list):
    """Compute letter-level statistics for an NL corpus."""
    # Get all letters used
    all_letters = Counter()
    for w in word_list:
        for c in w:
            all_letters[c] += 1

    # Keep only letters with reasonable frequency (≥ 0.01% of total)
    total_chars = sum(all_letters.values())
    min_freq = total_chars * 0.0001
    vocab = sorted(c for c, n in all_letters.items() if n >= min_freq)

    # Convert words to letter sequences (filtering rare chars)
    vocab_set = set(vocab)
    letter_words = []
    for w in word_list:
        filtered = [c for c in w if c in vocab_set]
        if filtered:
            letter_words.append((filtered, w))

    unigram = compute_unigram_dist([seq for seq, _ in letter_words], vocab)
    bigram_counts, bigram_total = compute_bigram_dist(
        [seq for seq, _ in letter_words], vocab)
    positional = compute_positional_dist(letter_words, vocab)
    wl_dist = word_length_dist(letter_words)

    # Build dictionary (unique word forms for matching)
    dictionary = set(word_list)

    return {
        'vocab': vocab,
        'unigram': unigram,
        'bigram_counts': bigram_counts,
        'bigram_total': bigram_total,
        'positional': positional,
        'word_length_dist': wl_dist,
        'letter_words': letter_words,
        'dictionary': dictionary,
        'n_words': len(word_list),
    }


# ═══════════════════════════════════════════════════════════════════════
# SUBSTITUTION CIPHER OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════

def frequency_rank_mapping(vms_unigram, nl_unigram, vms_vocab, nl_vocab):
    """Map VMS classes to NL letters by frequency rank."""
    vms_ranked = sorted(vms_vocab, key=lambda v: vms_unigram.get(v, 0), reverse=True)
    nl_ranked = sorted(nl_vocab, key=lambda v: nl_unigram.get(v, 0), reverse=True)

    mapping = {}
    for i, vc in enumerate(vms_ranked):
        if i < len(nl_ranked):
            mapping[vc] = nl_ranked[i]
        else:
            mapping[vc] = nl_ranked[-1]  # map excess to least frequent
    return mapping


def bigram_log_likelihood(vms_words_collapsed, mapping, nl_bigram_counts,
                          nl_bigram_total, nl_vocab):
    """Compute log-likelihood of mapped VMS text under NL bigram model."""
    nl_vocab_size = len(nl_vocab)
    ll = 0.0
    n = 0
    for class_seq, _ in vms_words_collapsed:
        mapped = [mapping.get(c, '?') for c in class_seq]
        for i in range(1, len(mapped)):
            pair = (mapped[i-1], mapped[i])
            count = nl_bigram_counts.get(pair, 0)
            # Laplace smoothing
            prob = (count + 1) / (nl_bigram_total + nl_vocab_size * nl_vocab_size)
            ll += math.log2(prob)
            n += 1
    return ll / n if n > 0 else -float('inf')


def hill_climb_mapping(vms_words_collapsed, initial_mapping, nl_stats,
                       n_iterations=5000, temperature_start=1.0):
    """Hill-climbing optimization of substitution mapping.
    Maximize bigram log-likelihood of mapped text under NL model.
    Uses simulated annealing with linear cooling.
    """
    rng = random.Random(42)
    mapping = dict(initial_mapping)
    vms_classes = list(mapping.keys())
    nl_vocab = nl_stats['vocab']

    best_ll = bigram_log_likelihood(
        vms_words_collapsed, mapping,
        nl_stats['bigram_counts'], nl_stats['bigram_total'], nl_vocab)
    best_mapping = dict(mapping)

    for iteration in range(n_iterations):
        temperature = temperature_start * (1 - iteration / n_iterations)

        # Swap two random class→letter assignments
        c1, c2 = rng.sample(vms_classes, 2)
        mapping[c1], mapping[c2] = mapping[c2], mapping[c1]

        new_ll = bigram_log_likelihood(
            vms_words_collapsed, mapping,
            nl_stats['bigram_counts'], nl_stats['bigram_total'], nl_vocab)

        delta = new_ll - best_ll
        if delta > 0 or (temperature > 0.01 and
                         rng.random() < math.exp(delta / (temperature + 1e-10))):
            if new_ll > best_ll:
                best_ll = new_ll
                best_mapping = dict(mapping)
        else:
            # Revert
            mapping[c1], mapping[c2] = mapping[c2], mapping[c1]

    return best_mapping, best_ll


def apply_mapping(vms_words_collapsed, mapping):
    """Apply a substitution mapping and return 'deciphered' words."""
    result = []
    for class_seq, orig_word in vms_words_collapsed:
        mapped = ''.join(mapping.get(c, '?') for c in class_seq)
        result.append((mapped, orig_word))
    return result


def count_dictionary_hits(deciphered_words, dictionary, min_len=1):
    """Count how many deciphered words appear in the NL dictionary."""
    hits = Counter()  # by word length
    totals = Counter()
    hit_examples = defaultdict(list)
    for mapped, orig in deciphered_words:
        wlen = len(mapped)
        if wlen >= min_len:
            totals[wlen] += 1
            if mapped in dictionary:
                hits[wlen] += 1
                if len(hit_examples[wlen]) < 5:
                    hit_examples[wlen].append((mapped, orig))

    total_hits = sum(hits.values())
    total_words = sum(totals.values())
    return {
        'total_hits': total_hits,
        'total_words': total_words,
        'hit_rate': total_hits / total_words if total_words > 0 else 0,
        'by_length': {l: {'hits': hits[l], 'total': totals[l],
                          'rate': hits[l] / totals[l] if totals[l] > 0 else 0}
                      for l in sorted(totals.keys())},
        'examples': dict(hit_examples),
    }


# ═══════════════════════════════════════════════════════════════════════
# NULL MODEL: RANDOM PERMUTATION BASELINE
# ═══════════════════════════════════════════════════════════════════════

def null_model_dict_hits(vms_words_collapsed, nl_stats, n_perms=500,
                         min_len=3):
    """Generate random substitution mappings and count dictionary hits.
    Returns distribution of hit rates for null comparison.
    """
    rng = random.Random(12345)
    vms_classes = sorted(set(c for seq, _ in vms_words_collapsed for c in seq))
    nl_vocab = list(nl_stats['vocab'])
    dictionary = nl_stats['dictionary']

    null_rates = []
    null_hits_total = []
    for _ in range(n_perms):
        # Random bijective-ish mapping
        shuffled_nl = list(nl_vocab)
        rng.shuffle(shuffled_nl)
        mapping = {}
        for i, vc in enumerate(vms_classes):
            mapping[vc] = shuffled_nl[i % len(shuffled_nl)]

        deciphered = apply_mapping(vms_words_collapsed, mapping)
        result = count_dictionary_hits(deciphered, dictionary, min_len=min_len)
        null_rates.append(result['hit_rate'])
        null_hits_total.append(result['total_hits'])

    return {
        'mean_rate': np.mean(null_rates),
        'std_rate': np.std(null_rates),
        'mean_hits': np.mean(null_hits_total),
        'std_hits': np.std(null_hits_total),
        'max_rate': np.max(null_rates),
        'rates': null_rates,
    }


# ═══════════════════════════════════════════════════════════════════════
# DISTRIBUTION COMPARISON (VMS vs NL structural similarity)
# ═══════════════════════════════════════════════════════════════════════

def compare_distributions(vms_stats, nl_stats_dict):
    """Compare VMS class distributions against each NL's letter dists.
    Returns structural similarity scores (NOT based on specific mapping).
    """
    results = {}
    for lang, nl_stats in nl_stats_dict.items():
        # Word length distribution comparison
        vms_wl = vms_stats['word_length_dist']
        nl_wl = nl_stats['word_length_dist']
        all_lengths = set(vms_wl.keys()) | set(nl_wl.keys())
        wl_jsd = jsd(vms_wl, nl_wl, all_lengths)

        # Unigram entropy comparison
        vms_uni_vals = list(vms_stats['unigram'].values())
        nl_uni_vals = list(nl_stats['unigram'].values())
        vms_h = -sum(p * math.log2(p) for p in vms_uni_vals if p > 0)
        nl_h = -sum(p * math.log2(p) for p in nl_uni_vals if p > 0)

        # Number of effective symbols
        vms_n_eff = len(vms_stats['vms_vocab'])
        nl_n_eff = len(nl_stats['vocab'])

        results[lang] = {
            'wl_jsd': wl_jsd,
            'vms_unigram_h': vms_h,
            'nl_unigram_h': nl_h,
            'entropy_ratio': vms_h / nl_h if nl_h > 0 else float('nan'),
            'vms_alphabet_size': vms_n_eff,
            'nl_alphabet_size': nl_n_eff,
            'size_ratio': vms_n_eff / nl_n_eff if nl_n_eff > 0 else 0,
        }
    return results


# ═══════════════════════════════════════════════════════════════════════
# POSITIONAL PATTERN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def positional_pattern_match(vms_positional, nl_positional, mapping,
                             vms_vocab, nl_vocab):
    """Measure how well the mapping preserves positional patterns.
    Compare P(mapped_class|position) vs P(letter|position) in NL.
    """
    scores = {}
    for pos in ['initial', 'medial', 'final']:
        vms_dist = vms_positional.get(pos, {})
        nl_dist = nl_positional.get(pos, {})
        # Map VMS distribution to NL letter space
        mapped_dist = {}
        for vc, freq in vms_dist.items():
            nl_letter = mapping.get(vc, '?')
            mapped_dist[nl_letter] = mapped_dist.get(nl_letter, 0) + freq
        # JSD between mapped VMS and actual NL
        all_letters = set(mapped_dist.keys()) | set(nl_dist.keys())
        total_m = sum(mapped_dist.values()) + 1e-10
        total_n = sum(nl_dist.values()) + 1e-10
        p = {l: mapped_dist.get(l, 0) / total_m for l in all_letters}
        q = {l: nl_dist.get(l, 0) / total_n for l in all_letters}
        scores[pos] = jsd(p, q, all_letters)
    return scores


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def run_analysis():
    pr("=" * 72)
    pr("PHASE 100 — TARGETED DECIPHERMENT WITH 25-CLASS ALPHABET")
    pr("=" * 72)
    pr()

    # ── Step 1: Load and collapse VMS ──
    pr("─" * 72)
    pr("STEP 1: Collapse VMS to 25-class alphabet")
    pr("─" * 72)

    vms_words = parse_all_folios()
    chunk_to_class = load_phase86_clusters()

    vms_collapsed = collapse_words_to_classes(vms_words['all'], chunk_to_class)
    vms_collapsed_A = collapse_words_to_classes(vms_words['A'], chunk_to_class)
    vms_collapsed_B = collapse_words_to_classes(vms_words['B'], chunk_to_class)

    # Get VMS class vocabulary (actually used)
    vms_class_vocab = sorted(set(c for seq, _ in vms_collapsed for c in seq))

    pr(f"\n  VMS words collapsed: {len(vms_collapsed):,}")
    pr(f"  VMS class vocabulary: {len(vms_class_vocab)} classes")
    pr(f"  Classes used: {', '.join(vms_class_vocab)}")

    # VMS class statistics
    vms_unigram = compute_unigram_dist([seq for seq, _ in vms_collapsed], vms_class_vocab)
    vms_bigram_counts, vms_bigram_total = compute_bigram_dist(
        [seq for seq, _ in vms_collapsed], vms_class_vocab)
    vms_positional = compute_positional_dist(vms_collapsed, vms_class_vocab)
    vms_wl = word_length_dist(vms_collapsed)

    pr(f"\n  Class frequency ranking:")
    for cls in sorted(vms_class_vocab, key=lambda c: vms_unigram.get(c, 0), reverse=True):
        pr(f"    {cls}: {vms_unigram[cls]:.4f}")

    pr(f"\n  Word length distribution (in classes):")
    for l in sorted(vms_wl.keys()):
        pr(f"    len={l}: {vms_wl[l]:.4f}")

    # ── Step 2: Load NL corpora and compute letter statistics ──
    pr()
    pr("─" * 72)
    pr("STEP 2: NL reference corpora — letter-level statistics")
    pr("─" * 72)

    nl_corpora = load_all_nl_corpora()
    nl_stats_dict = {}

    for lang, word_list in nl_corpora.items():
        stats = compute_nl_letter_stats(word_list)
        nl_stats_dict[lang] = stats
        pr(f"\n  {lang}: {len(word_list):,} words, "
           f"{len(stats['vocab'])} effective letters, "
           f"{len(stats['dictionary']):,} unique forms")
        # Top 10 letters
        top_letters = sorted(stats['vocab'],
                            key=lambda c: stats['unigram'].get(c, 0),
                            reverse=True)[:10]
        uni = stats['unigram']
        top_str = ' '.join(f'{c}={uni[c]:.3f}' for c in top_letters)
        pr(f"    Top 10: {top_str}")

    # ── Step 3: Structural distribution comparison ──
    pr()
    pr("─" * 72)
    pr("STEP 3: Structural distribution comparison (no mapping needed)")
    pr("─" * 72)

    vms_stats_for_comparison = {
        'unigram': vms_unigram,
        'vms_vocab': vms_class_vocab,
        'word_length_dist': vms_wl,
    }
    dist_comparison = compare_distributions(vms_stats_for_comparison, nl_stats_dict)

    pr(f"\n  {'Language':<12s} {'WL JSD':>8s} {'VMS H':>8s} {'NL H':>8s} "
       f"{'H ratio':>8s} {'VMS α':>6s} {'NL α':>6s} {'α ratio':>8s}")
    pr(f"  {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6} {'─'*6} {'─'*8}")
    for lang in sorted(dist_comparison.keys()):
        d = dist_comparison[lang]
        pr(f"  {lang:<12s} {d['wl_jsd']:>8.4f} {d['vms_unigram_h']:>8.3f} "
           f"{d['nl_unigram_h']:>8.3f} {d['entropy_ratio']:>8.3f} "
           f"{d['vms_alphabet_size']:>6d} {d['nl_alphabet_size']:>6d} "
           f"{d['size_ratio']:>8.2f}")

    # ── Step 4: Frequency-based mapping + hill-climbing ──
    pr()
    pr("─" * 72)
    pr("STEP 4: Substitution cipher optimization per language")
    pr("─" * 72)

    decipherment_results = {}

    for lang in sorted(nl_stats_dict.keys()):
        pr(f"\n  ── {lang} ──")
        nl_stats = nl_stats_dict[lang]

        # Step 4a: Frequency rank mapping (baseline)
        freq_mapping = frequency_rank_mapping(
            vms_unigram, nl_stats['unigram'],
            vms_class_vocab, nl_stats['vocab'])

        freq_ll = bigram_log_likelihood(
            vms_collapsed, freq_mapping,
            nl_stats['bigram_counts'], nl_stats['bigram_total'],
            nl_stats['vocab'])
        pr(f"    Frequency-rank mapping bigram LL: {freq_ll:.4f}")

        # Step 4b: Hill-climbing optimization
        best_mapping, best_ll = hill_climb_mapping(
            vms_collapsed, freq_mapping, nl_stats,
            n_iterations=8000, temperature_start=2.0)
        pr(f"    Hill-climb optimized bigram LL: {best_ll:.4f} "
           f"(improvement: {best_ll - freq_ll:+.4f})")

        # Step 4c: Apply mapping and count dictionary hits
        deciphered = apply_mapping(vms_collapsed, best_mapping)
        dict_results = count_dictionary_hits(deciphered, nl_stats['dictionary'],
                                             min_len=1)
        pr(f"    Dictionary hits (all): {dict_results['total_hits']:,} / "
           f"{dict_results['total_words']:,} = {dict_results['hit_rate']:.4f}")

        # Hits by length
        pr(f"    {'Len':>6s} {'Hits':>8s} {'Total':>8s} {'Rate':>8s}")
        for l in sorted(dict_results['by_length'].keys()):
            bl = dict_results['by_length'][l]
            pr(f"    {l:>6d} {bl['hits']:>8d} {bl['total']:>8d} {bl['rate']:>8.4f}")

        # Examples of hits for length ≥ 3
        for l in sorted(dict_results['examples'].keys()):
            if l >= 3:
                exs = dict_results['examples'][l]
                ex_str = ', '.join(f'{m}←{o}' for m, o in exs[:3])
                pr(f"    Len-{l} examples: {ex_str}")

        # Step 4d: Positional pattern match
        pos_scores = positional_pattern_match(
            vms_positional, nl_stats['positional'], best_mapping,
            vms_class_vocab, nl_stats['vocab'])
        pr(f"    Positional JSD: initial={pos_scores['initial']:.4f} "
           f"medial={pos_scores['medial']:.4f} final={pos_scores['final']:.4f}")

        # Store the mapping for display
        decipherment_results[lang] = {
            'freq_ll': freq_ll,
            'best_ll': best_ll,
            'dict_hits': dict_results,
            'positional_jsd': pos_scores,
            'mapping': best_mapping,
        }

    # ── Step 5: Null model comparison ──
    pr()
    pr("─" * 72)
    pr("STEP 5: Null model — random permutation baseline")
    pr("─" * 72)

    null_results = {}
    for lang in sorted(nl_stats_dict.keys()):
        pr(f"\n  ── {lang} ── (500 random permutations, min_len≥3)")
        null = null_model_dict_hits(vms_collapsed, nl_stats_dict[lang],
                                    n_perms=500, min_len=3)

        # Compute z-score for the optimized mapping
        opt_hits_3plus = sum(
            v['hits'] for l, v in decipherment_results[lang]['dict_hits']['by_length'].items()
            if l >= 3)
        opt_total_3plus = sum(
            v['total'] for l, v in decipherment_results[lang]['dict_hits']['by_length'].items()
            if l >= 3)
        opt_rate_3plus = opt_hits_3plus / opt_total_3plus if opt_total_3plus > 0 else 0

        z_score = ((opt_rate_3plus - null['mean_rate']) / null['std_rate']
                    if null['std_rate'] > 0 else 0)

        pr(f"    Null mean rate (≥3): {null['mean_rate']:.4f} ± {null['std_rate']:.4f}")
        pr(f"    Null max rate: {null['max_rate']:.4f}")
        pr(f"    Optimized rate (≥3): {opt_rate_3plus:.4f}")
        pr(f"    z-score: {z_score:+.2f}")
        pr(f"    Null mean hits: {null['mean_hits']:.1f} ± {null['std_hits']:.1f}")
        pr(f"    Optimized hits (≥3): {opt_hits_3plus}")

        null_results[lang] = {
            'null_mean_rate': null['mean_rate'],
            'null_std_rate': null['std_rate'],
            'null_max_rate': null['max_rate'],
            'opt_rate_3plus': opt_rate_3plus,
            'opt_hits_3plus': opt_hits_3plus,
            'z_score': z_score,
        }

    # ── Step 6: Cross-validation ──
    pr()
    pr("─" * 72)
    pr("STEP 6: Cross-validation (80/20 train/test split)")
    pr("─" * 72)

    rng = random.Random(42)
    indices = list(range(len(vms_collapsed)))
    rng.shuffle(indices)
    split = int(0.8 * len(indices))
    train_idx = set(indices[:split])
    test_idx = set(indices[split:])
    vms_train = [vms_collapsed[i] for i in range(len(vms_collapsed)) if i in train_idx]
    vms_test = [vms_collapsed[i] for i in range(len(vms_collapsed)) if i in test_idx]

    pr(f"\n  Train: {len(vms_train):,} words, Test: {len(vms_test):,} words")

    cv_results = {}
    for lang in sorted(nl_stats_dict.keys()):
        nl_stats = nl_stats_dict[lang]
        # Optimize on train
        freq_map = frequency_rank_mapping(
            compute_unigram_dist([s for s, _ in vms_train], vms_class_vocab),
            nl_stats['unigram'], vms_class_vocab, nl_stats['vocab'])
        opt_map, _ = hill_climb_mapping(vms_train, freq_map, nl_stats,
                                         n_iterations=5000, temperature_start=2.0)
        # Test on held-out
        test_deciphered = apply_mapping(vms_test, opt_map)
        test_hits = count_dictionary_hits(test_deciphered, nl_stats['dictionary'],
                                          min_len=3)
        train_deciphered = apply_mapping(vms_train, opt_map)
        train_hits = count_dictionary_hits(train_deciphered, nl_stats['dictionary'],
                                           min_len=3)

        pr(f"\n  {lang}: train rate={train_hits['hit_rate']:.4f}, "
           f"test rate={test_hits['hit_rate']:.4f}, "
           f"test hits={test_hits['total_hits']}/{test_hits['total_words']}")

        cv_results[lang] = {
            'train_rate': train_hits['hit_rate'],
            'test_rate': test_hits['hit_rate'],
            'test_hits': test_hits['total_hits'],
            'test_total': test_hits['total_words'],
        }

    # ── Step 7: Best mapping display ──
    pr()
    pr("─" * 72)
    pr("STEP 7: Best mapping summary")
    pr("─" * 72)

    # Rank languages by z-score
    ranked = sorted(null_results.items(), key=lambda x: x[1]['z_score'], reverse=True)

    pr(f"\n  {'Language':<12s} {'z-score':>8s} {'Hit rate':>8s} {'Null mean':>10s} "
       f"{'CV test':>8s} {'Bigram LL':>10s}")
    pr(f"  {'─'*12} {'─'*8} {'─'*8} {'─'*10} {'─'*8} {'─'*10}")
    for lang, nr in ranked:
        cv = cv_results.get(lang, {})
        dr = decipherment_results.get(lang, {})
        pr(f"  {lang:<12s} {nr['z_score']:>+8.2f} {nr['opt_rate_3plus']:>8.4f} "
           f"{nr['null_mean_rate']:>10.4f} {cv.get('test_rate', 0):>8.4f} "
           f"{dr.get('best_ll', 0):>10.4f}")

    # Display the best language's mapping
    best_lang = ranked[0][0] if ranked else None
    if best_lang:
        best_map = decipherment_results[best_lang]['mapping']
        pr(f"\n  Best language: {best_lang}")
        pr(f"  Mapping (class → letter):")
        for cls in sorted(best_map.keys()):
            freq = vms_unigram.get(cls, 0)
            pr(f"    {cls} (freq={freq:.4f}) → '{best_map[cls]}'")

        # Show some deciphered text samples
        deciphered = apply_mapping(vms_collapsed[:50], best_map)
        pr(f"\n  First 50 words deciphered ({best_lang}):")
        line = "    "
        for mapped, orig in deciphered:
            if len(line) + len(mapped) + 1 > 72:
                pr(line)
                line = "    "
            line += mapped + " "
        if line.strip():
            pr(line)

    # ── Step 8: Specificity test ──
    pr()
    pr("─" * 72)
    pr("STEP 8: Specificity — do multiple languages produce similar scores?")
    pr("─" * 72)

    z_scores = [nr['z_score'] for _, nr in ranked]
    if len(z_scores) >= 2:
        best_z = z_scores[0]
        second_z = z_scores[1]
        gap = best_z - second_z
        pr(f"\n  Best z-score: {best_z:+.2f} ({ranked[0][0]})")
        pr(f"  Second z-score: {second_z:+.2f} ({ranked[1][0]})")
        pr(f"  Gap: {gap:.2f}")
        if gap < 1.0:
            pr(f"  ⚠ LOW SPECIFICITY: Top two languages within 1σ of each other")
            pr(f"    This means the mapping is NOT language-specific — the hits")
            pr(f"    are likely driven by structural similarity, not decipherment.")
        elif gap < 2.0:
            pr(f"  ⚠ MODERATE SPECIFICITY: Top two separated by 1-2σ")
        else:
            pr(f"  ✓ HIGH SPECIFICITY: Top language clearly separated (>{gap:.1f}σ)")

    # ── Step 9: Critical assessment ──
    pr()
    pr("─" * 72)
    pr("STEP 9: Critical assessment")
    pr("─" * 72)

    pr(f"""
  CRITICAL NOTES ON METHODOLOGY:

  1. THE 25 CLASSES ARE NOT LETTERS. Each class contains multiple
     chunk variants (C0 has 57 members, C1 has 44). The mapping
     class→letter conflates structurally different chunks. This
     necessarily introduces noise.

  2. ALPHABET SIZE MISMATCH. VMS has 25 classes; NL alphabets have
     22-42 effective letters. When the NL has more letters than VMS
     classes, the mapping is necessarily lossy (multiple NL letters
     map to zero VMS classes). When VMS has more, some classes map
     to the same NL letter.

  3. WORD LENGTH MISMATCH. VMS "words" average ~2 classes (because
     each class = a chunk ≈ 1 syllable). NL words average 4-6 letters.
     This fundamental mismatch means dictionary matching is comparing
     2-class VMS words against 2-letter NL words — which are mostly
     function words (in, et, de, je). High hit rates on short words
     are EXPECTED by chance.

  4. THE BIGRAM MODEL IS LANGUAGE-GENERIC. Optimizing bigram LL
     will find ANY permutation that makes the text look vaguely like
     the target language's bigram statistics. This does not prove the
     VMS IS that language — only that bigram structure is transferable.

  5. MEANINGFUL DECIPHERMENT requires: (a) coherent multi-word
     phrases in the output, (b) topic-appropriate vocabulary matching
     the manuscript's illustrations, (c) consistent grammar. None of
     these are tested here — only dictionary word frequency.

  6. EXPECTED OUTCOME: Modest above-chance dictionary hits for ALL
     languages (because the 25-class VMS shares structural properties
     with NL text), with no single language dramatically outperforming
     others. This would indicate the VMS has NL-like STRUCTURE without
     being recoverable as a simple substitution cipher.
""")

    # ── Save results ──
    save_data = {
        'vms_class_vocab': vms_class_vocab,
        'vms_n_words': len(vms_collapsed),
        'dist_comparison': dist_comparison,
        'null_results': null_results,
        'cv_results': cv_results,
        'decipherment_summary': {
            lang: {
                'freq_ll': dr['freq_ll'],
                'best_ll': dr['best_ll'],
                'total_hits': dr['dict_hits']['total_hits'],
                'total_words': dr['dict_hits']['total_words'],
                'hit_rate': dr['dict_hits']['hit_rate'],
                'positional_jsd': dr['positional_jsd'],
            }
            for lang, dr in decipherment_results.items()
        },
        'best_language': best_lang,
        'best_mapping': {k: v for k, v in decipherment_results.get(best_lang, {}).get('mapping', {}).items()},
    }

    json_path = RESULTS_DIR / 'phase100_decipherment.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, default=str)
    pr(f"\n  Results saved to {json_path}")

    txt_path = RESULTS_DIR / 'phase100_decipherment.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Log saved to {txt_path}")


if __name__ == '__main__':
    run_analysis()
