#!/usr/bin/env python3
"""
Generative Chunk Model

═══════════════════════════════════════════════════════════════════════

OBJECTIVE:
  Train a Markov (n-gram) model on chunk sequences using the 523 chunk
  types. Generate synthetic VMS text and evaluate its statistical
  fingerprint against the real VMS baseline.

  Then collapse the chunk inventory to the 25 equivalence classes
  (chunk_equivalence_classes clusters) and repeat. Quantify how much of the VMS's
  statistical signature is captured by chunk-level sequential
  dependencies alone. Validate that the 25-class reduction preserves
  essential structure.

METHOD:
  1. Parse all VMS folios into chunk sequences (reusing chunk_fingerprint parser)
  2. Train bigram + trigram Markov models on chunk sequences
     (with word-boundary tokens)
  3. Generate synthetic texts of same length as VMS
  4. Compute fingerprints for real VMS, synthetic-bigram, synthetic-trigram:
     - h_char (conditional entropy ratio at chunk level)
     - h_char at glyph level (the classic VMS metric)
     - Zipf slope, Heaps exponent, TTR, hapax ratio
     - Positional concentration (word-initial/medial/final distributions)
     - Cross-word MI
  5. NULL MODELS:
     a. Shuffled chunks (destroy all sequential structure)
     b. Random bigram (uniform transition probabilities)
  6. Collapse to 25 equivalence classes (chunk_equivalence_classes), re-compute all
  7. Currier A vs B separately

SKEPTICISM:
  - A good Markov model fit does NOT prove the VMS is Markov-generated.
    Many NL texts are well-approximated by bigram models.
  - The test is whether chunk-level Markov captures the ANOMALOUS
    features (low glyph h_char, positional concentration) — not just
    the NL-like ones (Zipf, Heaps).
  - Coverage: chunk_equivalence_classes clusters only covered 57% of chunk tokens.
    We must handle ALL chunks (assign rare ones to nearest cluster).
  - Synthetic text may over-regularize — test with multiple seeds.

═══════════════════════════════════════════════════════════════════════
"""

import re, sys, io, math, json, os
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import chunk_to_str, clean_word, conditional_entropy, entropy, eva_to_glyphs, extract_words_from_line, get_currier_language, load_chunk_equivalence_clusters, parse_one_chunk, parse_word_into_chunks

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
# MAURO'S LOOP GRAMMAR — CHUNK PARSER (from chunk_fingerprint)
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
# VMS TEXT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════




def parse_all_folios():
    """Parse all VMS folios into word lists with Currier labels.
    Returns: dict with keys 'all', 'A', 'B' -> list of word strings
    """
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


def words_to_chunk_sequences(word_list):
    """Convert word list to list of (word_chunks, word_str) pairs.
    word_chunks = list of chunk-ID strings for that word.
    Also returns flat chunk stream with word boundary markers.
    """
    WORD_BOUNDARY = '<W>'
    word_chunk_pairs = []
    chunk_stream = []  # flat stream with boundary tokens
    total_unparsed = 0
    total_glyphs = 0

    for w in word_list:
        chunks, unparsed, glyphs = parse_word_into_chunks(w)
        total_glyphs += len(glyphs)
        total_unparsed += len(unparsed)
        chunk_ids = [chunk_to_str(c) for c in chunks]
        if chunk_ids:
            word_chunk_pairs.append((chunk_ids, w))
            chunk_stream.append(WORD_BOUNDARY)
            chunk_stream.extend(chunk_ids)

    chunk_stream.append(WORD_BOUNDARY)
    return word_chunk_pairs, chunk_stream, total_unparsed, total_glyphs


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL METRICS
# ═══════════════════════════════════════════════════════════════════════



def h_ratio_from_tokens(tokens):
    """Compute H(X|prev) / H(X) for a token sequence."""
    if len(tokens) < 2:
        return float('nan')
    unigram = Counter(tokens)
    bigram = Counter()
    prev_counts = Counter()
    for i in range(1, len(tokens)):
        bigram[(tokens[i-1], tokens[i])] += 1
        prev_counts[tokens[i-1]] += 1
    h_uni = entropy(unigram)
    h_cond = conditional_entropy(bigram, prev_counts)
    return h_cond / h_uni if h_uni > 0 else float('nan')

def zipf_slope(counts, top_n=50):
    freqs = sorted(counts.values(), reverse=True)[:top_n]
    if len(freqs) < 5: return float('nan')
    log_ranks = np.log10(np.arange(1, len(freqs) + 1))
    log_freqs = np.log10(np.array(freqs, dtype=float))
    A = np.vstack([log_ranks, np.ones(len(log_ranks))]).T
    slope, _ = np.linalg.lstsq(A, log_freqs, rcond=None)[0]
    return slope

def heaps_exponent(token_list, sample_points=20):
    n = len(token_list)
    if n < 100: return float('nan')
    points = np.linspace(100, n, sample_points, dtype=int)
    log_n, log_v = [], []
    for p in points:
        v = len(set(token_list[:p]))
        log_n.append(math.log10(p))
        log_v.append(math.log10(v))
    log_n = np.array(log_n)
    log_v = np.array(log_v)
    A = np.vstack([log_n, np.ones(len(log_n))]).T
    beta, _ = np.linalg.lstsq(A, log_v, rcond=None)[0]
    return beta

def compute_fingerprint(tokens, label=""):
    """Full statistical fingerprint for a token sequence."""
    n = len(tokens)
    if n < 20:
        return None
    uni = Counter(tokens)
    n_types = len(uni)
    hapax = sum(1 for c in uni.values() if c == 1)
    return {
        'label': label,
        'n_tokens': n,
        'n_types': n_types,
        'hapax_ratio': hapax / n_types if n_types > 0 else 0,
        'ttr': n_types / n,
        'h_ratio': h_ratio_from_tokens(tokens),
        'zipf_slope': zipf_slope(uni),
        'heaps_beta': heaps_exponent(tokens),
    }


def glyph_level_h_char(word_list):
    """Compute glyph-level h_char (the classic VMS metric) from word list."""
    glyphs = []
    for w in word_list:
        gs = eva_to_glyphs(w)
        glyphs.extend(gs)
    return h_ratio_from_tokens(glyphs), len(glyphs)


def cross_word_mi(chunk_stream):
    """Compute mutual information across word boundaries.
    chunk_stream includes <W> boundary tokens.
    """
    BOUNDARY = '<W>'
    # Find pairs of (last_chunk_of_word, first_chunk_of_next_word)
    pairs = []
    for i in range(1, len(chunk_stream) - 1):
        if chunk_stream[i] == BOUNDARY:
            if i > 0 and chunk_stream[i-1] != BOUNDARY and \
               i+1 < len(chunk_stream) and chunk_stream[i+1] != BOUNDARY:
                pairs.append((chunk_stream[i-1], chunk_stream[i+1]))

    if len(pairs) < 10:
        return float('nan')

    pair_counts = Counter(pairs)
    left_counts = Counter(p[0] for p in pairs)
    right_counts = Counter(p[1] for p in pairs)
    N = len(pairs)

    mi = 0.0
    for (l, r), c in pair_counts.items():
        p_lr = c / N
        p_l = left_counts[l] / N
        p_r = right_counts[r] / N
        if p_l > 0 and p_r > 0:
            mi += p_lr * math.log2(p_lr / (p_l * p_r))
    return mi


def positional_concentration(word_chunk_pairs):
    """Measure how concentrated each chunk type is in word-initial,
    medial, or final positions. Returns mean Gini coefficient.
    """
    pos_counts = defaultdict(lambda: [0, 0, 0])  # [initial, medial, final]
    for chunks, _ in word_chunk_pairs:
        for i, c in enumerate(chunks):
            if len(chunks) == 1:
                pos_counts[c][0] += 1  # initial
                pos_counts[c][2] += 1  # also final
            elif i == 0:
                pos_counts[c][0] += 1
            elif i == len(chunks) - 1:
                pos_counts[c][2] += 1
            else:
                pos_counts[c][1] += 1

    gini_values = []
    for c, counts in pos_counts.items():
        total = sum(counts)
        if total < 10:
            continue
        props = sorted([x / total for x in counts])
        # Gini coefficient
        n = len(props)
        gini = sum((2 * (i + 1) - n - 1) * props[i] for i in range(n))
        gini /= (n * sum(props)) if sum(props) > 0 else 1
        gini_values.append(gini)

    return np.mean(gini_values) if gini_values else float('nan')


# ═══════════════════════════════════════════════════════════════════════
# MARKOV MODELS
# ═══════════════════════════════════════════════════════════════════════

class ChunkMarkovModel:
    """N-gram Markov model over chunk sequences with word boundaries."""

    def __init__(self, order=1):
        self.order = order
        self.transitions = defaultdict(Counter)
        self.vocabulary = set()
        self.word_boundary = '<W>'

    def train(self, chunk_stream):
        """Train on a chunk stream (flat list including <W> tokens)."""
        self.vocabulary = set(chunk_stream)
        for i in range(self.order, len(chunk_stream)):
            context = tuple(chunk_stream[i - self.order:i])
            self.transitions[context][chunk_stream[i]] += 1

    def generate(self, n_tokens, seed=None):
        """Generate n_tokens from the model."""
        rng = random.Random(seed)
        if not self.transitions:
            return []

        # Start after a word boundary
        start_ctx = tuple([self.word_boundary] * self.order)
        if start_ctx not in self.transitions:
            # fallback: pick random context
            start_ctx = rng.choice(list(self.transitions.keys()))

        context = list(start_ctx)
        output = list(context)

        for _ in range(n_tokens):
            ctx_key = tuple(context[-self.order:])
            if ctx_key not in self.transitions:
                # backoff: use any context ending with the last token
                candidates = [k for k in self.transitions
                              if k[-1] == context[-1]]
                if not candidates:
                    candidates = list(self.transitions.keys())
                ctx_key = rng.choice(candidates)

            dist = self.transitions[ctx_key]
            total = sum(dist.values())
            r = rng.random() * total
            cumulative = 0
            chosen = None
            for tok, cnt in dist.items():
                cumulative += cnt
                if cumulative >= r:
                    chosen = tok
                    break
            if chosen is None:
                chosen = rng.choice(list(dist.keys()))

            output.append(chosen)
            context.append(chosen)

        return output

    def perplexity(self, chunk_stream):
        """Compute perplexity of the model on a held-out chunk stream."""
        log_prob_sum = 0.0
        n = 0
        for i in range(self.order, len(chunk_stream)):
            ctx = tuple(chunk_stream[i - self.order:i])
            tok = chunk_stream[i]
            if ctx in self.transitions:
                dist = self.transitions[ctx]
                total = sum(dist.values())
                count = dist.get(tok, 0)
                # Laplace smoothing
                vocab_size = len(self.vocabulary)
                prob = (count + 1) / (total + vocab_size)
            else:
                prob = 1 / len(self.vocabulary) if self.vocabulary else 1e-10
            log_prob_sum += math.log2(prob)
            n += 1
        if n == 0:
            return float('inf')
        return 2 ** (-log_prob_sum / n)


def stream_to_words(chunk_stream):
    """Convert a chunk stream (with <W> boundaries) back to word-chunk-pairs."""
    BOUNDARY = '<W>'
    words = []
    current = []
    for tok in chunk_stream:
        if tok == BOUNDARY:
            if current:
                words.append(current)
                current = []
        else:
            current.append(tok)
    if current:
        words.append(current)
    return words


def reconstruct_word_str(chunk_ids):
    """Reconstruct an EVA word string from chunk IDs."""
    return ''.join(c.replace('.', '') for c in chunk_ids)


# ═══════════════════════════════════════════════════════════════════════
# chunk_equivalence_classes CLUSTER MAPPING
# ═══════════════════════════════════════════════════════════════════════



def assign_rare_chunks_to_clusters(chunk_to_class, all_chunk_types, word_chunk_pairs):
    """Assign unmapped chunk types to nearest cluster based on
    distributional similarity (left/right context overlap).
    """
    mapped = set(chunk_to_class.keys())
    unmapped = [c for c in all_chunk_types if c not in mapped]

    if not unmapped:
        return chunk_to_class

    # Build context profiles for mapped chunks (by cluster)
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

    # Aggregate cluster contexts
    for c, cls_id in chunk_to_class.items():
        for ctx, cnt in chunk_left_ctx[c].items():
            cluster_left_ctx[cls_id][ctx] += cnt
        for ctx, cnt in chunk_right_ctx[c].items():
            cluster_right_ctx[cls_id][ctx] += cnt

    # For each unmapped chunk, find nearest cluster
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

            # Cosine similarity of context vectors
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


def collapse_stream(chunk_stream, chunk_to_class):
    """Replace chunk IDs in stream with their class IDs."""
    return [chunk_to_class.get(c, c) for c in chunk_stream]


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def full_fingerprint_suite(chunk_stream, word_chunk_pairs, word_list, label):
    """Compute all metrics for a text representation."""
    # Chunk-level (excluding boundary tokens)
    chunks_only = [c for c in chunk_stream if c != '<W>']
    fp = compute_fingerprint(chunks_only, label=label)
    if fp is None:
        return None

    # Glyph-level h_char
    fp['glyph_h_char'], fp['n_glyphs'] = glyph_level_h_char(word_list)

    # Cross-word MI
    fp['cross_word_mi'] = cross_word_mi(chunk_stream)

    # Positional concentration
    fp['positional_gini'] = positional_concentration(word_chunk_pairs)

    # Word-level stats
    word_strs = [''.join(c.replace('.', '') for c in wc) for wc, _ in word_chunk_pairs]
    word_counts = Counter(word_strs)
    fp['word_types'] = len(word_counts)
    fp['word_tokens'] = len(word_strs)
    fp['word_ttr'] = fp['word_types'] / fp['word_tokens'] if fp['word_tokens'] > 0 else 0
    fp['word_zipf'] = zipf_slope(word_counts)
    fp['mean_chunks_per_word'] = np.mean([len(wc) for wc, _ in word_chunk_pairs])

    return fp


def run_analysis():
    pr("=" * 72)
    pr("generative_chunk_model — GENERATIVE CHUNK MODEL")
    pr("=" * 72)
    pr()

    # ── Step 1: Parse VMS ──
    pr("─" * 72)
    pr("STEP 1: Parse VMS into chunk sequences")
    pr("─" * 72)

    word_data = parse_all_folios()
    results = {}

    for section in ['all', 'A', 'B']:
        words = word_data[section]
        wcp, stream, n_unp, n_gly = words_to_chunk_sequences(words)
        chunks_only = [c for c in stream if c != '<W>']
        pr(f"\n  [{section}] Words: {len(words):,}, Chunks: {len(chunks_only):,}, "
           f"Unparsed glyphs: {n_unp} / {n_gly} ({100*n_unp/n_gly:.1f}%)")
        pr(f"  Chunk types: {len(set(chunks_only))}, "
           f"Mean chunks/word: {len(chunks_only)/len(wcp):.2f}")

        results[section] = {
            'words': words,
            'word_chunk_pairs': wcp,
            'chunk_stream': stream,
            'n_chunk_tokens': len(chunks_only),
            'n_chunk_types': len(set(chunks_only)),
        }

    # ── Step 2: Compute VMS baseline fingerprints ──
    pr()
    pr("─" * 72)
    pr("STEP 2: VMS baseline fingerprints")
    pr("─" * 72)

    baselines = {}
    for section in ['all', 'A', 'B']:
        r = results[section]
        fp = full_fingerprint_suite(
            r['chunk_stream'], r['word_chunk_pairs'], r['words'],
            label=f"VMS_{section}"
        )
        baselines[section] = fp
        pr(f"\n  [{section}] Chunk h_ratio: {fp['h_ratio']:.4f}, "
           f"Glyph h_char: {fp['glyph_h_char']:.4f}")
        pr(f"          Zipf: {fp['zipf_slope']:.3f}, Heaps: {fp['heaps_beta']:.3f}, "
           f"TTR: {fp['ttr']:.4f}, Hapax: {fp['hapax_ratio']:.3f}")
        pr(f"          Cross-word MI: {fp['cross_word_mi']:.4f}, "
           f"Pos Gini: {fp['positional_gini']:.4f}")
        pr(f"          Word types: {fp['word_types']}, Word TTR: {fp['word_ttr']:.4f}")

    # ── Step 3: Train Markov models ──
    pr()
    pr("─" * 72)
    pr("STEP 3: Train bigram and trigram Markov models")
    pr("─" * 72)

    stream_all = results['all']['chunk_stream']
    n_total = len(stream_all)

    # Split 80/20 for cross-validation
    split_idx = int(n_total * 0.8)
    train_stream = stream_all[:split_idx]
    test_stream = stream_all[split_idx:]

    bigram_model = ChunkMarkovModel(order=1)
    bigram_model.train(train_stream)

    trigram_model = ChunkMarkovModel(order=2)
    trigram_model.train(train_stream)

    # Train full models (for generation)
    bigram_full = ChunkMarkovModel(order=1)
    bigram_full.train(stream_all)

    trigram_full = ChunkMarkovModel(order=2)
    trigram_full.train(stream_all)

    # Perplexity on held-out data
    ppl_bi = bigram_model.perplexity(test_stream)
    ppl_tri = trigram_model.perplexity(test_stream)

    pr(f"\n  Bigram model: {len(bigram_full.transitions)} contexts, "
       f"held-out perplexity: {ppl_bi:.2f}")
    pr(f"  Trigram model: {len(trigram_full.transitions)} contexts, "
       f"held-out perplexity: {ppl_tri:.2f}")

    # ── Step 4: Generate synthetic texts ──
    pr()
    pr("─" * 72)
    pr("STEP 4: Generate synthetic texts and compute fingerprints")
    pr("─" * 72)

    gen_length = results['all']['n_chunk_tokens'] + \
                 len([c for c in stream_all if c == '<W>'])
    N_SEEDS = 10  # generate 10 independent samples

    syn_fingerprints = {'bigram': [], 'trigram': []}

    for model_name, model in [('bigram', bigram_full), ('trigram', trigram_full)]:
        for seed_i in range(N_SEEDS):
            syn_stream = model.generate(gen_length, seed=42 + seed_i)
            syn_words = stream_to_words(syn_stream)
            syn_wcp = [(w, reconstruct_word_str(w)) for w in syn_words if w]
            syn_word_strs = [ws for _, ws in syn_wcp]

            fp = full_fingerprint_suite(
                syn_stream, syn_wcp, syn_word_strs,
                label=f"syn_{model_name}_{seed_i}"
            )
            if fp:
                syn_fingerprints[model_name].append(fp)

    for model_name in ['bigram', 'trigram']:
        fps = syn_fingerprints[model_name]
        if not fps:
            continue
        pr(f"\n  Synthetic {model_name} (mean ± std over {len(fps)} seeds):")
        for key in ['h_ratio', 'glyph_h_char', 'zipf_slope', 'heaps_beta',
                     'ttr', 'hapax_ratio', 'cross_word_mi', 'positional_gini',
                     'word_ttr', 'mean_chunks_per_word']:
            vals = [fp[key] for fp in fps if not math.isnan(fp.get(key, float('nan')))]
            if vals:
                pr(f"    {key:25s}: {np.mean(vals):.4f} ± {np.std(vals):.4f}  "
                   f"(VMS: {baselines['all'].get(key, float('nan')):.4f})")

    # ── Step 5: Null models ──
    pr()
    pr("─" * 72)
    pr("STEP 5: Null models (shuffled chunks, uniform bigram)")
    pr("─" * 72)

    # NULL 1: Shuffled chunk stream (destroy sequential structure)
    null_shuffle_fps = []
    chunks_only_all = [c for c in stream_all if c != '<W>']
    word_lengths = [len(wc) for wc, _ in results['all']['word_chunk_pairs']]

    for seed_i in range(N_SEEDS):
        rng = random.Random(42 + seed_i)
        shuffled = list(chunks_only_all)
        rng.shuffle(shuffled)
        # Re-insert word boundaries at original positions
        null_stream = []
        idx = 0
        for wlen in word_lengths:
            null_stream.append('<W>')
            for _ in range(wlen):
                if idx < len(shuffled):
                    null_stream.append(shuffled[idx])
                    idx += 1
        null_stream.append('<W>')

        null_words = stream_to_words(null_stream)
        null_wcp = [(w, reconstruct_word_str(w)) for w in null_words if w]
        null_word_strs = [ws for _, ws in null_wcp]

        fp = full_fingerprint_suite(
            null_stream, null_wcp, null_word_strs,
            label=f"null_shuffle_{seed_i}"
        )
        if fp:
            null_shuffle_fps.append(fp)

    pr(f"\n  Shuffled null (mean ± std over {len(null_shuffle_fps)} seeds):")
    for key in ['h_ratio', 'glyph_h_char', 'zipf_slope', 'heaps_beta',
                 'ttr', 'hapax_ratio', 'cross_word_mi', 'positional_gini']:
        vals = [fp[key] for fp in null_shuffle_fps if not math.isnan(fp.get(key, float('nan')))]
        if vals:
            pr(f"    {key:25s}: {np.mean(vals):.4f} ± {np.std(vals):.4f}  "
               f"(VMS: {baselines['all'].get(key, float('nan')):.4f})")

    # NULL 2: Uniform random bigram (same vocabulary, uniform transitions)
    null_uniform_fps = []
    vocab = list(set(chunks_only_all))
    for seed_i in range(N_SEEDS):
        rng = random.Random(42 + seed_i)
        uni_stream = ['<W>']
        for wlen in word_lengths:
            for _ in range(wlen):
                uni_stream.append(rng.choice(vocab))
            uni_stream.append('<W>')

        uni_words = stream_to_words(uni_stream)
        uni_wcp = [(w, reconstruct_word_str(w)) for w in uni_words if w]
        uni_word_strs = [ws for _, ws in uni_wcp]

        fp = full_fingerprint_suite(
            uni_stream, uni_wcp, uni_word_strs,
            label=f"null_uniform_{seed_i}"
        )
        if fp:
            null_uniform_fps.append(fp)

    pr(f"\n  Uniform random (mean ± std over {len(null_uniform_fps)} seeds):")
    for key in ['h_ratio', 'glyph_h_char', 'zipf_slope', 'heaps_beta',
                 'ttr', 'hapax_ratio', 'cross_word_mi', 'positional_gini']:
        vals = [fp[key] for fp in null_uniform_fps if not math.isnan(fp.get(key, float('nan')))]
        if vals:
            pr(f"    {key:25s}: {np.mean(vals):.4f} ± {np.std(vals):.4f}  "
               f"(VMS: {baselines['all'].get(key, float('nan')):.4f})")

    # ── Step 6: Z-scores for synthetic vs VMS ──
    pr()
    pr("─" * 72)
    pr("STEP 6: Statistical comparison (z-scores: synthetic vs VMS)")
    pr("─" * 72)

    comparison_keys = ['h_ratio', 'glyph_h_char', 'zipf_slope', 'heaps_beta',
                       'ttr', 'cross_word_mi', 'positional_gini',
                       'word_ttr', 'mean_chunks_per_word']

    pr(f"\n  {'Metric':<26s} {'VMS':>8s} {'Bi_mean':>8s} {'Bi_z':>8s} "
       f"{'Tri_mean':>8s} {'Tri_z':>8s} {'Shuf_z':>8s} {'Uni_z':>8s}")
    pr(f"  {'─'*26} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")

    z_scores = {}
    for key in comparison_keys:
        vms_val = baselines['all'].get(key, float('nan'))
        if math.isnan(vms_val):
            continue

        row = {'vms': vms_val}
        line = f"  {key:<26s} {vms_val:>8.4f}"

        for model_name, fps_list in [('bigram', syn_fingerprints['bigram']),
                                     ('trigram', syn_fingerprints['trigram']),
                                     ('shuffle', null_shuffle_fps),
                                     ('uniform', null_uniform_fps)]:
            vals = [fp[key] for fp in fps_list
                    if key in fp and not math.isnan(fp.get(key, float('nan')))]
            if vals and np.std(vals) > 0:
                m = np.mean(vals)
                s = np.std(vals)
                z = (vms_val - m) / s
                line += f" {m:>8.4f} {z:>8.2f}"
                row[f'{model_name}_mean'] = m
                row[f'{model_name}_z'] = z
            else:
                line += f" {'N/A':>8s} {'N/A':>8s}"

        pr(line)
        z_scores[key] = row

    # ── Step 7: Collapse to 25 equivalence classes ──
    pr()
    pr("─" * 72)
    pr("STEP 7: Collapse to 25 equivalence classes (chunk_equivalence_classes)")
    pr("─" * 72)

    chunk_to_class = load_chunk_equivalence_clusters()
    all_chunk_types = set(c for c in chunks_only_all)
    mapped_count = sum(1 for c in all_chunk_types if c in chunk_to_class)
    pr(f"\n  chunk_equivalence_classes mapped: {mapped_count} / {len(all_chunk_types)} chunk types")

    # Extend mapping to cover all chunks
    chunk_to_class_ext = assign_rare_chunks_to_clusters(
        chunk_to_class, all_chunk_types,
        results['all']['word_chunk_pairs']
    )
    mapped_ext = sum(1 for c in all_chunk_types if c in chunk_to_class_ext)
    pr(f"  After extension: {mapped_ext} / {len(all_chunk_types)} chunk types mapped")
    n_classes = len(set(chunk_to_class_ext.values()))
    pr(f"  Number of equivalence classes used: {n_classes}")

    # Collapse VMS
    collapsed_stream = collapse_stream(stream_all, chunk_to_class_ext)
    collapsed_chunks = [c for c in collapsed_stream if c != '<W>']
    collapsed_wcp = []
    for wc, ws in results['all']['word_chunk_pairs']:
        coll_wc = [chunk_to_class_ext.get(c, c) for c in wc]
        collapsed_wcp.append((coll_wc, ws))

    vms_coll_fp = compute_fingerprint(collapsed_chunks, label="VMS_collapsed_25")
    pr(f"\n  VMS collapsed: h_ratio={vms_coll_fp['h_ratio']:.4f}, "
       f"types={vms_coll_fp['n_types']}, TTR={vms_coll_fp['ttr']:.6f}")

    # Train collapsed Markov models
    coll_bigram = ChunkMarkovModel(order=1)
    coll_bigram.train(collapsed_stream)
    coll_trigram = ChunkMarkovModel(order=2)
    coll_trigram.train(collapsed_stream)

    pr(f"  Collapsed bigram: {len(coll_bigram.transitions)} contexts")
    pr(f"  Collapsed trigram: {len(coll_trigram.transitions)} contexts")

    # Generate from collapsed models
    coll_gen_len = len(collapsed_stream)
    coll_syn_fps = {'bigram': [], 'trigram': []}

    for model_name, model in [('bigram', coll_bigram), ('trigram', coll_trigram)]:
        for seed_i in range(N_SEEDS):
            syn = model.generate(coll_gen_len, seed=42 + seed_i)
            syn_chunks = [c for c in syn if c != '<W>']
            fp = compute_fingerprint(syn_chunks, label=f"coll_syn_{model_name}_{seed_i}")
            if fp:
                coll_syn_fps[model_name].append(fp)

    pr(f"\n  Collapsed comparison:")
    pr(f"  {'Metric':<20s} {'VMS':>8s} {'Bi_mean':>8s} {'Bi_z':>8s} {'Tri_mean':>8s} {'Tri_z':>8s}")
    pr(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")

    for key in ['h_ratio', 'zipf_slope', 'heaps_beta', 'ttr', 'hapax_ratio']:
        vms_val = vms_coll_fp.get(key, float('nan'))
        if math.isnan(vms_val):
            continue
        line = f"  {key:<20s} {vms_val:>8.4f}"
        for mn in ['bigram', 'trigram']:
            vals = [fp[key] for fp in coll_syn_fps[mn]
                    if not math.isnan(fp.get(key, float('nan')))]
            if vals and np.std(vals) > 0:
                m = np.mean(vals)
                z = (vms_val - m) / np.std(vals)
                line += f" {m:>8.4f} {z:>8.2f}"
            else:
                line += f" {'N/A':>8s} {'N/A':>8s}"
        pr(line)

    # ── Step 8: Currier A vs B comparison ──
    pr()
    pr("─" * 72)
    pr("STEP 8: Currier A vs B — separate generative models")
    pr("─" * 72)

    for section in ['A', 'B']:
        stream_sec = results[section]['chunk_stream']
        bi_sec = ChunkMarkovModel(order=1)
        bi_sec.train(stream_sec)

        # Generate
        sec_fps = []
        for seed_i in range(N_SEEDS):
            syn = bi_sec.generate(len(stream_sec), seed=42 + seed_i)
            syn_chunks = [c for c in syn if c != '<W>']
            fp = compute_fingerprint(syn_chunks, label=f"syn_{section}_{seed_i}")
            if fp:
                sec_fps.append(fp)

        vms_fp = baselines[section]
        pr(f"\n  Currier {section}:")
        pr(f"  {'Metric':<20s} {'VMS':>8s} {'Syn_mean':>8s} {'z':>8s}")
        pr(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*8}")
        for key in ['h_ratio', 'glyph_h_char', 'zipf_slope', 'cross_word_mi',
                     'positional_gini']:
            v = vms_fp.get(key, float('nan'))
            if math.isnan(v): continue
            vals = [fp[key] for fp in sec_fps if not math.isnan(fp.get(key, float('nan')))]
            if vals and np.std(vals) > 0:
                m = np.mean(vals)
                z = (v - m) / np.std(vals)
                pr(f"  {key:<20s} {v:>8.4f} {m:>8.4f} {z:>8.2f}")
            else:
                pr(f"  {key:<20s} {v:>8.4f} {'N/A':>8s} {'N/A':>8s}")

    # ── Step 9: Cross-validation of Markov model ──
    pr()
    pr("─" * 72)
    pr("STEP 9: 5-fold cross-validation of Markov models")
    pr("─" * 72)

    n_folds = 5
    fold_size = len(stream_all) // n_folds
    cv_ppl_bi = []
    cv_ppl_tri = []

    for fold in range(n_folds):
        test_start = fold * fold_size
        test_end = test_start + fold_size
        cv_train = stream_all[:test_start] + stream_all[test_end:]
        cv_test = stream_all[test_start:test_end]

        bi_cv = ChunkMarkovModel(order=1)
        bi_cv.train(cv_train)
        cv_ppl_bi.append(bi_cv.perplexity(cv_test))

        tri_cv = ChunkMarkovModel(order=2)
        tri_cv.train(cv_train)
        cv_ppl_tri.append(tri_cv.perplexity(cv_test))

    pr(f"\n  5-fold CV perplexity:")
    pr(f"    Bigram:  {np.mean(cv_ppl_bi):.2f} ± {np.std(cv_ppl_bi):.2f}")
    pr(f"    Trigram: {np.mean(cv_ppl_tri):.2f} ± {np.std(cv_ppl_tri):.2f}")
    pr(f"    Reduction (bi→tri): {100*(1 - np.mean(cv_ppl_tri)/np.mean(cv_ppl_bi)):.1f}%")

    # ── Step 10: Summary ──
    pr()
    pr("─" * 72)
    pr("STEP 10: Summary and Verdict")
    pr("─" * 72)

    # Aggregate z-scores for synthetic bigram vs VMS
    bi_z_vals = [abs(z_scores[k].get('bigram_z', float('nan')))
                 for k in z_scores if not math.isnan(z_scores[k].get('bigram_z', float('nan')))]
    tri_z_vals = [abs(z_scores[k].get('trigram_z', float('nan')))
                  for k in z_scores if not math.isnan(z_scores[k].get('trigram_z', float('nan')))]

    pr(f"\n  Mean |z| (synthetic vs VMS):")
    if bi_z_vals:
        pr(f"    Bigram:  {np.mean(bi_z_vals):.2f} (max: {np.max(bi_z_vals):.2f})")
    if tri_z_vals:
        pr(f"    Trigram: {np.mean(tri_z_vals):.2f} (max: {np.max(tri_z_vals):.2f})")

    pr(f"\n  Key findings:")
    vms_hr = baselines['all']['h_ratio']
    for mn in ['bigram', 'trigram']:
        fps = syn_fingerprints[mn]
        hr_vals = [fp['h_ratio'] for fp in fps]
        if hr_vals:
            pr(f"    {mn} chunk h_ratio: {np.mean(hr_vals):.4f} vs VMS {vms_hr:.4f} "
               f"(captures {100*np.mean(hr_vals)/vms_hr:.1f}% of VMS value)")

    gh_vals_bi = [fp['glyph_h_char'] for fp in syn_fingerprints['bigram']
                  if not math.isnan(fp.get('glyph_h_char', float('nan')))]
    vms_gh = baselines['all']['glyph_h_char']
    if gh_vals_bi:
        pr(f"    Bigram glyph h_char: {np.mean(gh_vals_bi):.4f} vs VMS {vms_gh:.4f}")

    # Save results
    save_data = {
        'baselines': {k: {kk: vv for kk, vv in v.items() if isinstance(vv, (int, float, str))}
                      for k, v in baselines.items() if v},
        'perplexity': {'bigram': ppl_bi, 'trigram': ppl_tri},
        'cv_perplexity': {
            'bigram_mean': float(np.mean(cv_ppl_bi)),
            'bigram_std': float(np.std(cv_ppl_bi)),
            'trigram_mean': float(np.mean(cv_ppl_tri)),
            'trigram_std': float(np.std(cv_ppl_tri)),
        },
        'z_scores': z_scores,
        'synthetic_bigram_means': {},
        'synthetic_trigram_means': {},
        'collapsed_25': {
            'n_classes': n_classes,
            'vms_h_ratio': vms_coll_fp['h_ratio'],
            'vms_types': vms_coll_fp['n_types'],
        },
    }

    for mn in ['bigram', 'trigram']:
        fps = syn_fingerprints[mn]
        means = {}
        for key in ['h_ratio', 'glyph_h_char', 'zipf_slope', 'heaps_beta',
                     'ttr', 'hapax_ratio', 'cross_word_mi', 'positional_gini',
                     'word_ttr', 'mean_chunks_per_word']:
            vals = [fp[key] for fp in fps if not math.isnan(fp.get(key, float('nan')))]
            if vals:
                means[key] = {'mean': float(np.mean(vals)), 'std': float(np.std(vals))}
        save_data[f'synthetic_{mn}_means'] = means

    json_path = RESULTS_DIR / 'generative_chunk_model.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, default=str)
    pr(f"\n  Results saved to {json_path}")

    txt_path = RESULTS_DIR / 'generative_chunk_model.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Log saved to {txt_path}")


if __name__ == '__main__':
    run_analysis()
