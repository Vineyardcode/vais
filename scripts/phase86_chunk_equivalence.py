#!/usr/bin/env python3
"""
Phase 86 — Chunk Equivalence Class Discovery

═══════════════════════════════════════════════════════════════════════

MOTIVATION:

  Phase 85 found 523 chunk types — too many for an alphabet (~30)
  but too few for a syllabary (~3000). The chunk h_ratio (0.818)
  matches NL characters (0.849, z=-1.70), NOT NL syllables (0.50).

  HYPOTHESIS: Many of the 523 chunk types are distributional
  VARIANTS of a smaller set of functional units (~20-40).
  If we cluster chunks by how they behave in context, we should
  find the TRUE ALPHABET SIZE of VMS.

  WHY THIS MATTERS: If we can collapse 523 chunks into ~30
  equivalence classes AND the collapsed text has NL-character-like
  statistics, this would confirm:
    - Chunks are the atomic units (not EVA glyphs)
    - The "true alphabet" has ~30 symbols with allographic variants
    - The h_char anomaly is a measurement artifact

APPROACH:
  1. Parse VMS into chunks, extract per-chunk distributional features:
     - Left-context distribution (what precedes this chunk)
     - Right-context distribution (what follows this chunk)
     - Word-position profile (P(initial), P(medial), P(final))
     - Slot skeleton (which of 5 grammar slots are filled)
  2. Compute pairwise JSD distance matrix for frequent chunks
  3. Agglomerative clustering (average-linkage)
  4. Sweep k=10..100: silhouette score + collapsed-text metrics
  5. NULL MODEL: random merging at same k (50 trials)
  6. CROSS-CHECK: cluster NL syllables — should NOT collapse to ~30

SKEPTICISM:
  - Distributional clustering can always produce clusters — the
    question is whether they're BETTER than random merging.
  - Rare chunks (<20 tokens) have noisy distributions; must exclude.
  - Slot skeleton alone might dominate — must test features separately.
  - If the optimal k is sensitive to linkage method, it's not robust.
  - NL syllables should NOT cluster down to alphabet size — if they
    do, the method is flawed and proves nothing about VMS.
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random

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
    return chunks, unparsed, glyphs


def chunk_to_str(chunk):
    return '.'.join(chunk)


def slot_pattern(chunk_glyphs):
    """Return binary tuple: (s1,s2,s3,s4,s5) for which slots are filled."""
    slots = [0, 0, 0, 0, 0]
    pos = 0
    gs = list(chunk_glyphs)
    if pos < len(gs) and gs[pos] in SLOT1:
        slots[0] = 1; pos += 1
    if pos < len(gs):
        if gs[pos] in SLOT2_RUNS:
            slots[1] = 1
            while pos < len(gs) and gs[pos] in SLOT2_RUNS: pos += 1
        elif gs[pos] in SLOT2_SINGLE:
            slots[1] = 1; pos += 1
    if pos < len(gs) and gs[pos] in SLOT3:
        slots[2] = 1; pos += 1
    if pos < len(gs):
        if gs[pos] in SLOT4_RUNS:
            slots[3] = 1
            while pos < len(gs) and gs[pos] in SLOT4_RUNS: pos += 1
        elif gs[pos] in SLOT4_SINGLE:
            slots[3] = 1; pos += 1
    if pos < len(gs) and gs[pos] in SLOT5:
        slots[4] = 1; pos += 1
    return tuple(slots)


# ═══════════════════════════════════════════════════════════════════════
# VMS PARSING (from Phase 85)
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

def parse_vms():
    result = defaultdict(list)
    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)
    for filepath in folio_files:
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num: continue
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
    return dict(result)


# ═══════════════════════════════════════════════════════════════════════
# NL TEXT LOADING & SYLLABIFICATION (from Phase 85)
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

def load_reference_text(filepath):
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
    words = re.findall(r'[a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþßœ]+', text)
    return words


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL METRICS
# ═══════════════════════════════════════════════════════════════════════

def entropy(counts):
    total = sum(counts.values())
    if total == 0: return 0.0
    return -sum((c/total) * math.log2(c/total) for c in counts.values() if c > 0)

def conditional_entropy(bigrams_counter, unigram_counter):
    h_joint = entropy(bigrams_counter)
    h_x = entropy(unigram_counter)
    return h_joint - h_x

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
    log_n = []
    log_v = []
    for p in points:
        v = len(set(token_list[:p]))
        log_n.append(math.log10(p))
        log_v.append(math.log10(v))
    log_n = np.array(log_n)
    log_v = np.array(log_v)
    A = np.vstack([log_n, np.ones(len(log_n))]).T
    beta, _ = np.linalg.lstsq(A, log_v, rcond=None)[0]
    return beta

def compute_unit_fingerprint(unit_tokens):
    """Compute full statistical fingerprint for a sequence of atomic units."""
    n = len(unit_tokens)
    if n < 20: return None
    unigram = Counter(unit_tokens)
    n_types = len(unigram)
    hapax = sum(1 for c in unigram.values() if c == 1)
    bigrams = Counter()
    prev_counts = Counter()
    for i in range(1, n):
        bigrams[(unit_tokens[i-1], unit_tokens[i])] += 1
        prev_counts[unit_tokens[i-1]] += 1
    h_uni = entropy(unigram)
    h_cond = conditional_entropy(bigrams, prev_counts)
    h_ratio = h_cond / h_uni if h_uni > 0 else float('nan')
    return {
        'n_tokens': n, 'n_types': n_types,
        'hapax_ratio': hapax / n_types if n_types > 0 else 0,
        'hapax_count': hapax,
        'ttr': n_types / n,
        'h_unigram': h_uni, 'h_cond': h_cond, 'h_ratio': h_ratio,
        'zipf_slope': zipf_slope(unigram),
        'heaps_beta': heaps_exponent(unit_tokens),
    }


# ═══════════════════════════════════════════════════════════════════════
# DISTRIBUTIONAL FEATURE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════

def extract_distributional_features(word_chunks_list, min_freq=20):
    """Extract distributional features for each chunk type.

    Args:
        word_chunks_list: list of lists of chunk-ID strings (one per word)
        min_freq: minimum token count to include a chunk

    Returns:
        frequent_chunks: list of chunk IDs (sorted by frequency)
        features: dict mapping chunk_id -> feature dict
        chunk_counts: Counter of all chunk IDs
    """
    # Flatten to get counts
    all_chunks = []
    for wc in word_chunks_list:
        all_chunks.extend(wc)
    chunk_counts = Counter(all_chunks)

    # Frequent chunks only
    frequent = [c for c, n in chunk_counts.most_common() if n >= min_freq]
    freq_set = set(frequent)

    pr(f"  Chunks with >= {min_freq} tokens: {len(frequent)} / {len(chunk_counts)}")
    pr(f"  Token coverage of frequent chunks: "
       f"{100*sum(chunk_counts[c] for c in frequent)/len(all_chunks):.1f}%")

    # Context distributions
    left_ctx = defaultdict(Counter)   # chunk -> Counter of what precedes
    right_ctx = defaultdict(Counter)  # chunk -> Counter of what follows

    # Word-position profile
    pos_initial = Counter()
    pos_medial = Counter()
    pos_final = Counter()

    # Build bigram context from within-word chunk sequences
    # Use <W> for word boundary
    BOUNDARY = '<W>'
    for wc in word_chunks_list:
        if not wc:
            continue
        # Record positions
        pos_initial[wc[0]] += 1
        if len(wc) > 1:
            pos_final[wc[-1]] += 1
            for c in wc[1:-1]:
                pos_medial[c] += 1
        else:
            pos_final[wc[0]] += 1  # single-chunk word: both initial and final

        # Record left/right contexts (within word)
        for i, c in enumerate(wc):
            if i == 0:
                left_ctx[c][BOUNDARY] += 1
            else:
                left_ctx[c][wc[i-1]] += 1
            if i == len(wc) - 1:
                right_ctx[c][BOUNDARY] += 1
            else:
                right_ctx[c][wc[i+1]] += 1

    # Build feature vectors
    # Context vocabulary: frequent chunks + boundary token
    ctx_vocab = sorted(frequent) + [BOUNDARY]
    ctx_idx = {c: i for i, c in enumerate(ctx_vocab)}
    ctx_dim = len(ctx_vocab)

    features = {}
    for c in frequent:
        total_occ = chunk_counts[c]

        # Left context distribution (smoothed)
        left_vec = np.zeros(ctx_dim, dtype=float)
        for ctx_tok, ct in left_ctx[c].items():
            if ctx_tok in ctx_idx:
                left_vec[ctx_idx[ctx_tok]] = ct
            # else: rare context token, ignored
        left_total = left_vec.sum()
        if left_total > 0:
            left_vec = (left_vec + 0.01) / (left_total + 0.01 * ctx_dim)  # Laplace smoothing
        else:
            left_vec = np.ones(ctx_dim) / ctx_dim

        # Right context distribution (smoothed)
        right_vec = np.zeros(ctx_dim, dtype=float)
        for ctx_tok, ct in right_ctx[c].items():
            if ctx_tok in ctx_idx:
                right_vec[ctx_idx[ctx_tok]] = ct
        right_total = right_vec.sum()
        if right_total > 0:
            right_vec = (right_vec + 0.01) / (right_total + 0.01 * ctx_dim)
        else:
            right_vec = np.ones(ctx_dim) / ctx_dim

        # Word position features
        n_init = pos_initial.get(c, 0)
        n_med = pos_medial.get(c, 0)
        n_fin = pos_final.get(c, 0)
        pos_total = n_init + n_med + n_fin
        if pos_total > 0:
            pos_vec = np.array([n_init / pos_total,
                                n_med / pos_total,
                                n_fin / pos_total])
        else:
            pos_vec = np.array([1/3, 1/3, 1/3])

        # Slot skeleton
        # Parse the chunk string back to glyphs to get slot pattern
        chunk_glyphs = c.split('.')
        skel = slot_pattern(chunk_glyphs)

        features[c] = {
            'left_ctx': left_vec,
            'right_ctx': right_vec,
            'pos_vec': pos_vec,
            'slot_skel': np.array(skel, dtype=float),
            'count': total_occ,
        }

    return frequent, features, chunk_counts


# ═══════════════════════════════════════════════════════════════════════
# DISTANCE COMPUTATION (Jensen-Shannon Divergence)
# ═══════════════════════════════════════════════════════════════════════

def jsd(p, q):
    """Jensen-Shannon divergence between two probability distributions."""
    m = 0.5 * (p + q)
    # Clip to avoid log(0)
    eps = 1e-12
    p_safe = np.clip(p, eps, None)
    q_safe = np.clip(q, eps, None)
    m_safe = np.clip(m, eps, None)
    kl_pm = np.sum(p_safe * np.log2(p_safe / m_safe))
    kl_qm = np.sum(q_safe * np.log2(q_safe / m_safe))
    return 0.5 * (kl_pm + kl_qm)


def compute_distance_matrix(frequent_chunks, features,
                            w_left=1.0, w_right=1.0, w_pos=0.5, w_skel=0.5):
    """Compute pairwise distance matrix using weighted JSD.

    The distance is: w_left*JSD(left) + w_right*JSD(right) +
                     w_pos*JSD(pos) + w_skel*hamming(skel)

    Returns: NxN numpy distance matrix
    """
    N = len(frequent_chunks)
    dist = np.zeros((N, N), dtype=float)

    for i in range(N):
        fi = features[frequent_chunks[i]]
        for j in range(i+1, N):
            fj = features[frequent_chunks[j]]

            d_left = jsd(fi['left_ctx'], fj['left_ctx'])
            d_right = jsd(fi['right_ctx'], fj['right_ctx'])

            # JSD for position vectors (pad to avoid issues with zeros)
            p_pos = fi['pos_vec'] + 1e-12
            q_pos = fj['pos_vec'] + 1e-12
            p_pos /= p_pos.sum()
            q_pos /= q_pos.sum()
            d_pos = jsd(p_pos, q_pos)

            # Hamming distance for slot skeleton (normalized)
            d_skel = np.mean(fi['slot_skel'] != fj['slot_skel'])

            d_total = (w_left * d_left + w_right * d_right +
                       w_pos * d_pos + w_skel * d_skel)
            dist[i, j] = d_total
            dist[j, i] = d_total

    return dist


# ═══════════════════════════════════════════════════════════════════════
# AGGLOMERATIVE CLUSTERING (average-linkage, from scratch)
# ═══════════════════════════════════════════════════════════════════════

def agglomerative_cluster(dist_matrix, n_items):
    """Average-linkage agglomerative clustering.

    Returns: merge_history - list of (i, j, distance) triples,
             giving the order of merges from N clusters down to 1.
    """
    N = n_items
    # Active clusters: map cluster_id -> set of original indices
    clusters = {i: {i} for i in range(N)}
    active = set(range(N))

    # Initialize inter-cluster distances (same as point distances)
    # Use a dict for efficient lookup
    cdist = {}
    for i in range(N):
        for j in range(i+1, N):
            cdist[(i, j)] = dist_matrix[i, j]

    merge_history = []
    next_id = N

    while len(active) > 1:
        # Find closest pair
        min_d = float('inf')
        mi, mj = -1, -1
        for i in active:
            for j in active:
                if j <= i:
                    continue
                key = (min(i,j), max(i,j))
                d = cdist.get(key, float('inf'))
                if d < min_d:
                    min_d = d
                    mi, mj = i, j

        if mi < 0:
            break

        # Merge mi and mj into new cluster
        new_members = clusters[mi] | clusters[mj]
        new_id = next_id
        next_id += 1
        clusters[new_id] = new_members
        merge_history.append((mi, mj, min_d))

        # Update distances: average linkage
        active.discard(mi)
        active.discard(mj)
        ni = len(clusters[mi])
        nj = len(clusters[mj])

        for k in list(active):
            key_ik = (min(mi, k), max(mi, k))
            key_jk = (min(mj, k), max(mj, k))
            d_ik = cdist.get(key_ik, float('inf'))
            d_jk = cdist.get(key_jk, float('inf'))
            # Average linkage: weighted mean
            d_new = (ni * d_ik + nj * d_jk) / (ni + nj)
            cdist[(min(new_id, k), max(new_id, k))] = d_new

        active.add(new_id)

        # Clean up old entries (optional, saves memory)
        del clusters[mi]
        del clusters[mj]

    return merge_history, clusters


def cut_dendrogram(merge_history, n_items, k):
    """Cut the dendrogram to produce exactly k clusters.

    Returns: list of sets, each containing original item indices.
    """
    # Start with each item in its own cluster
    clusters = {i: {i} for i in range(n_items)}
    next_id = n_items

    # Apply merges until we have k clusters
    n_merges_to_apply = n_items - k
    for idx in range(min(n_merges_to_apply, len(merge_history))):
        mi, mj, _ = merge_history[idx]
        new_members = clusters[mi] | clusters[mj]
        clusters[next_id] = new_members
        del clusters[mi]
        del clusters[mj]
        next_id += 1

    return list(clusters.values())


# ═══════════════════════════════════════════════════════════════════════
# SILHOUETTE SCORE (from scratch)
# ═══════════════════════════════════════════════════════════════════════

def silhouette_score(dist_matrix, cluster_labels, n_items):
    """Compute mean silhouette score.

    cluster_labels: array of length n_items, each entry is the cluster ID.
    """
    unique_labels = set(cluster_labels)
    if len(unique_labels) <= 1 or len(unique_labels) >= n_items:
        return 0.0

    scores = []
    for i in range(n_items):
        my_label = cluster_labels[i]
        my_cluster = [j for j in range(n_items)
                      if cluster_labels[j] == my_label and j != i]
        if not my_cluster:
            scores.append(0.0)
            continue

        # a(i) = mean distance to same-cluster points
        a_i = np.mean([dist_matrix[i, j] for j in my_cluster])

        # b(i) = min over other clusters of mean distance
        b_i = float('inf')
        for label in unique_labels:
            if label == my_label:
                continue
            other = [j for j in range(n_items) if cluster_labels[j] == label]
            if other:
                mean_d = np.mean([dist_matrix[i, j] for j in other])
                b_i = min(b_i, mean_d)

        if b_i == float('inf'):
            scores.append(0.0)
        else:
            s_i = (b_i - a_i) / max(a_i, b_i) if max(a_i, b_i) > 0 else 0
            scores.append(s_i)

    return np.mean(scores)


# ═══════════════════════════════════════════════════════════════════════
# COLLAPSE & RECOMPUTE
# ═══════════════════════════════════════════════════════════════════════

def collapse_and_fingerprint(word_chunks_list, chunk_to_class, class_name="collapsed"):
    """Collapse chunk IDs to class IDs and compute fingerprint.

    chunk_to_class: dict mapping chunk_id -> class_id (string or int)
    Chunks not in the dict are mapped to themselves.
    """
    collapsed_tokens = []
    for wc in word_chunks_list:
        for c in wc:
            collapsed_tokens.append(str(chunk_to_class.get(c, c)))

    fp = compute_unit_fingerprint(collapsed_tokens)
    return fp, collapsed_tokens


# ═══════════════════════════════════════════════════════════════════════
# NULL MODEL: RANDOM MERGING
# ═══════════════════════════════════════════════════════════════════════

def random_merge_fingerprint(word_chunks_list, frequent_chunks, all_chunk_types, k, n_trials=50):
    """Merge chunks into k random groups and compute collapsed fingerprint.

    Returns: dict with mean and std of each metric across trials.
    """
    metrics = defaultdict(list)

    for trial in range(n_trials):
        rng = random.Random(42 + trial)
        # Assign each chunk type to a random group
        chunk_to_class = {}
        for c in all_chunk_types:
            chunk_to_class[c] = str(rng.randint(0, k - 1))

        fp, _ = collapse_and_fingerprint(word_chunks_list, chunk_to_class)
        if fp:
            for key in ['h_ratio', 'hapax_ratio', 'zipf_slope', 'heaps_beta',
                         'n_types', 'ttr']:
                metrics[key].append(fp[key])

    result = {}
    for key, vals in metrics.items():
        arr = np.array(vals)
        result[key + '_mean'] = float(np.mean(arr))
        result[key + '_std'] = float(np.std(arr))

    return result


# ═══════════════════════════════════════════════════════════════════════
# NL SYLLABLE CLUSTERING (cross-check)
# ═══════════════════════════════════════════════════════════════════════

def nl_syllable_clustering_check(ref_name, ref_words, target_k_values):
    """Cluster NL syllables and check if they collapse to alphabet size.

    If they do, the method is flawed. NL syllables should NOT cluster
    down to ~30 groups with good metrics.
    """
    # Syllabify
    word_syls = []
    all_syls = []
    for w in ref_words:
        syls = syllabify_word(w)
        word_syls.append(syls)
        all_syls.extend(syls)

    syl_counts = Counter(all_syls)
    n_syl_types = len(syl_counts)

    # Get frequent syllables
    min_freq_nl = 20
    frequent_syls = [s for s, n in syl_counts.most_common() if n >= min_freq_nl]

    if len(frequent_syls) < 50:
        return None  # Not enough data

    # Random merging only (full clustering too expensive for NL with many syllable types)
    results = {}
    for k in target_k_values:
        rm = random_merge_fingerprint(word_syls, frequent_syls,
                                       list(syl_counts.keys()), k, n_trials=30)
        results[k] = rm

    # Also get the uncollapsed fingerprint
    base_fp = compute_unit_fingerprint(all_syls)

    return {
        'n_syl_types': n_syl_types,
        'n_frequent': len(frequent_syls),
        'base_fingerprint': base_fp,
        'random_merge': results,
    }


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 76)
    pr("PHASE 86 — CHUNK EQUIVALENCE CLASS DISCOVERY")
    pr("=" * 76)
    pr()
    pr("  Can 523 VMS chunk types be clustered into a smaller set of")
    pr("  functional equivalence classes? If yes, what is the 'true")
    pr("  alphabet size' of VMS, and does collapsing to it produce")
    pr("  NL-character-like statistics?")
    pr()

    # ── STEP 1: PARSE VMS ──────────────────────────────────────────────

    pr("─" * 76)
    pr("STEP 1: PARSE VMS INTO CHUNKS")
    pr("─" * 76)
    pr()

    vms_data = parse_vms()
    all_words = vms_data['all']
    pr(f"  Total VMS words: {len(all_words)}")

    word_chunks_list = []
    all_chunks_flat = []
    for w in all_words:
        chunks, unparsed, glyphs = parse_word_into_chunks(w)
        chunk_ids = [chunk_to_str(c) for c in chunks]
        word_chunks_list.append(chunk_ids)
        all_chunks_flat.extend(chunk_ids)

    chunk_counts = Counter(all_chunks_flat)
    pr(f"  Total chunk tokens: {len(all_chunks_flat)}")
    pr(f"  Unique chunk types: {len(chunk_counts)}")
    pr()

    # ── STEP 2: EXTRACT DISTRIBUTIONAL FEATURES ────────────────────────

    pr("─" * 76)
    pr("STEP 2: DISTRIBUTIONAL FEATURE EXTRACTION")
    pr("─" * 76)
    pr()

    MIN_FREQ = 20
    frequent, features, _ = extract_distributional_features(
        word_chunks_list, min_freq=MIN_FREQ)

    pr()
    pr("  Feature dimensionality per chunk:")
    sample = features[frequent[0]]
    pr(f"    Left context:  {len(sample['left_ctx'])} dims")
    pr(f"    Right context: {len(sample['right_ctx'])} dims")
    pr(f"    Word position: {len(sample['pos_vec'])} dims")
    pr(f"    Slot skeleton: {len(sample['slot_skel'])} dims")
    pr()

    # Show some example position profiles
    pr("  Example word-position profiles (top 15 chunks):")
    pr(f"    {'Chunk':>20s}  {'Count':>6s}  {'Init%':>6s}  {'Med%':>6s}  {'Fin%':>6s}  Slots")
    pr(f"    {'─'*20}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*10}")
    for c in frequent[:15]:
        f = features[c]
        pv = f['pos_vec']
        skel = ''.join(str(int(s)) for s in f['slot_skel'])
        pr(f"    {c:>20s}  {f['count']:6d}  {100*pv[0]:5.1f}%  {100*pv[1]:5.1f}%  {100*pv[2]:5.1f}%  {skel}")
    pr()

    # ── STEP 3: DISTANCE MATRIX ───────────────────────────────────────

    pr("─" * 76)
    pr("STEP 3: PAIRWISE DISTANCE MATRIX (JSD-based)")
    pr("─" * 76)
    pr()

    N = len(frequent)
    pr(f"  Computing {N}x{N} distance matrix...")

    dist = compute_distance_matrix(frequent, features)

    # Summary statistics
    upper_tri = dist[np.triu_indices(N, k=1)]
    pr(f"  Distance stats: mean={np.mean(upper_tri):.4f}, "
       f"std={np.std(upper_tri):.4f}, "
       f"min={np.min(upper_tri):.4f}, max={np.max(upper_tri):.4f}")
    pr()

    # Show top 10 closest pairs
    pr("  Top 10 closest chunk pairs:")
    pair_dists = []
    for i in range(N):
        for j in range(i+1, N):
            pair_dists.append((dist[i, j], frequent[i], frequent[j]))
    pair_dists.sort()
    for d_val, c1, c2 in pair_dists[:10]:
        s1 = ''.join(str(int(s)) for s in features[c1]['slot_skel'])
        s2 = ''.join(str(int(s)) for s in features[c2]['slot_skel'])
        pr(f"    d={d_val:.4f}  {c1:>20s} [{s1}]  ~  {c2:<20s} [{s2}]")
    pr()

    # ── STEP 4: AGGLOMERATIVE CLUSTERING ───────────────────────────────

    pr("─" * 76)
    pr("STEP 4: AGGLOMERATIVE CLUSTERING (average-linkage)")
    pr("─" * 76)
    pr()

    pr(f"  Clustering {N} frequent chunks...")
    merge_history, final_clusters = agglomerative_cluster(dist, N)
    pr(f"  Merge history: {len(merge_history)} merges recorded")
    pr()

    # ── STEP 5: SWEEP k — SILHOUETTE + COLLAPSED METRICS ──────────────

    pr("─" * 76)
    pr("STEP 5: SWEEP k = cluster count")
    pr("─" * 76)
    pr()

    K_VALUES = [10, 15, 20, 25, 30, 35, 40, 50, 60, 80, 100, 150, 200]
    # Filter to valid range
    K_VALUES = [k for k in K_VALUES if k < N]

    sweep_results = {}

    pr(f"  {'k':>5s}  {'Silh':>6s}  {'h_rat':>6s}  {'hapax':>6s}  "
       f"{'Zipf':>6s}  {'Heaps':>6s}  {'Types':>6s}")
    pr(f"  {'─'*5}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}")

    for k in K_VALUES:
        # Cut dendrogram
        cluster_sets = cut_dendrogram(merge_history, N, k)

        # Build chunk-to-class mapping
        chunk_to_class = {}
        for cls_idx, members in enumerate(cluster_sets):
            for m in members:
                chunk_to_class[frequent[m]] = f"C{cls_idx}"

        # Also map infrequent chunks: assign to nearest frequent chunk's class
        for c in chunk_counts:
            if c not in chunk_to_class:
                # Simple: assign to "RARE" catch-all
                chunk_to_class[c] = "RARE"

        # Collapse and compute fingerprint
        fp, collapsed_tokens = collapse_and_fingerprint(
            word_chunks_list, chunk_to_class)

        # Silhouette score
        labels = np.zeros(N, dtype=int)
        for cls_idx, members in enumerate(cluster_sets):
            for m in members:
                labels[m] = cls_idx
        sil = silhouette_score(dist, labels, N)

        sweep_results[k] = {
            'silhouette': sil,
            'fingerprint': fp,
            'cluster_sets': cluster_sets,
            'chunk_to_class': chunk_to_class,
        }

        if fp:
            pr(f"  {k:5d}  {sil:6.3f}  {fp['h_ratio']:6.4f}  "
               f"{fp['hapax_ratio']:6.4f}  {fp['zipf_slope']:6.3f}  "
               f"{fp['heaps_beta']:6.3f}  {fp['n_types']:6d}")
        else:
            pr(f"  {k:5d}  {sil:6.3f}  [insufficient data]")

    pr()

    # NL reference values for comparison
    pr("  NL CHARACTER reference values:")
    pr(f"    h_ratio:     0.849 ± 0.018")
    pr(f"    hapax_ratio: ~0 (alphabet is closed)")
    pr(f"    Zipf slope:  varies by language")
    pr(f"    Alphabet:    26-36 types")
    pr()

    # ── STEP 6: FIND OPTIMAL k ────────────────────────────────────────

    pr("─" * 76)
    pr("STEP 6: OPTIMAL k ANALYSIS")
    pr("─" * 76)
    pr()

    # Best silhouette
    best_sil_k = max(K_VALUES, key=lambda k: sweep_results[k]['silhouette'])
    best_sil = sweep_results[best_sil_k]['silhouette']
    pr(f"  Best silhouette: k={best_sil_k}, silhouette={best_sil:.4f}")

    # Best h_ratio match to NL characters (0.849)
    NL_CHAR_H_RATIO = 0.849
    best_h_k = min(K_VALUES,
                   key=lambda k: abs(sweep_results[k]['fingerprint']['h_ratio'] - NL_CHAR_H_RATIO)
                   if sweep_results[k]['fingerprint'] else float('inf'))
    best_h = sweep_results[best_h_k]['fingerprint']['h_ratio']
    pr(f"  Best h_ratio match to NL chars (0.849): k={best_h_k}, h_ratio={best_h:.4f}")

    # Combined criterion: silhouette > 0.1 AND closest h_ratio to NL
    viable = [k for k in K_VALUES
              if sweep_results[k]['silhouette'] > 0.05 and sweep_results[k]['fingerprint']]
    if viable:
        best_combined_k = min(viable,
                              key=lambda k: abs(sweep_results[k]['fingerprint']['h_ratio'] - NL_CHAR_H_RATIO))
        pr(f"  Best combined (silh>0.05 + h_ratio): k={best_combined_k}")
    else:
        best_combined_k = best_sil_k
        pr(f"  No k with silhouette > 0.05; using best silhouette k={best_combined_k}")

    pr()

    # Show cluster composition at the optimal k
    opt_k = best_combined_k
    opt_clusters = sweep_results[opt_k]['cluster_sets']
    pr(f"  Cluster composition at k={opt_k}:")
    pr(f"  {'Cls':>4s}  {'Size':>5s}  {'Members (top 5 by frequency)':40s}")
    pr(f"  {'─'*4}  {'─'*5}  {'─'*60}")

    for cls_idx, members in enumerate(sorted(opt_clusters, key=lambda s: -len(s))):
        member_chunks = [frequent[m] for m in sorted(members)]
        # Sort by frequency
        member_chunks.sort(key=lambda c: -chunk_counts[c])
        top5 = ', '.join(member_chunks[:5])
        extra = f" + {len(member_chunks)-5} more" if len(member_chunks) > 5 else ""
        pr(f"  {cls_idx:4d}  {len(members):5d}  {top5}{extra}")
    pr()

    # ── STEP 7: NULL MODEL — RANDOM MERGING ────────────────────────────

    pr("─" * 76)
    pr("STEP 7: NULL MODEL — RANDOM MERGING")
    pr("─" * 76)
    pr()
    pr("  If random merging at the same k produces equally good metrics,")
    pr("  then distributional clustering tells us nothing special.")
    pr()

    all_chunk_types = list(chunk_counts.keys())
    null_k_values = [best_sil_k, best_h_k, best_combined_k, 25, 30, 50]
    null_k_values = sorted(set(k for k in null_k_values if k < N))

    pr(f"  {'k':>5s}  {'Metric':>10s}  {'Clustered':>10s}  {'RandMean':>10s}  "
       f"{'RandStd':>10s}  {'z-score':>8s}  {'Better?':>8s}")
    pr(f"  {'─'*5}  {'─'*10}  {'─'*10}  {'─'*10}  {'─'*10}  {'─'*8}  {'─'*8}")

    json_null = {}
    for k in null_k_values:
        rm = random_merge_fingerprint(word_chunks_list, frequent, all_chunk_types, k)
        json_null[k] = rm
        fp = sweep_results[k]['fingerprint'] if k in sweep_results else None
        if not fp:
            continue

        for metric in ['h_ratio', 'hapax_ratio', 'zipf_slope', 'heaps_beta']:
            val = fp[metric]
            rm_mean = rm.get(metric + '_mean', float('nan'))
            rm_std = rm.get(metric + '_std', float('nan'))
            if rm_std > 1e-10:
                z = (val - rm_mean) / rm_std
            else:
                z = float('nan')

            # "Better" = closer to NL character values
            if metric == 'h_ratio':
                better = "YES" if abs(val - 0.849) < abs(rm_mean - 0.849) else "NO"
            elif metric == 'hapax_ratio':
                better = "YES" if val < rm_mean else "NO"  # lower hapax = closer to closed alphabet
            else:
                better = f"|z|={abs(z):.1f}"

            pr(f"  {k:5d}  {metric:>10s}  {val:10.4f}  {rm_mean:10.4f}  "
               f"{rm_std:10.4f}  {z:8.2f}  {better:>8s}")

    pr()

    # ── STEP 8: FEATURE ABLATION ──────────────────────────────────────

    pr("─" * 76)
    pr("STEP 8: FEATURE ABLATION — WHAT DRIVES CLUSTERING?")
    pr("─" * 76)
    pr()
    pr("  Test whether slot skeleton alone dominates the clustering.")
    pr("  Recompute distances with each feature set alone.")
    pr()

    feature_sets = {
        'context_only': {'w_left': 1.0, 'w_right': 1.0, 'w_pos': 0.0, 'w_skel': 0.0},
        'skeleton_only': {'w_left': 0.0, 'w_right': 0.0, 'w_pos': 0.0, 'w_skel': 1.0},
        'position_only': {'w_left': 0.0, 'w_right': 0.0, 'w_pos': 1.0, 'w_skel': 0.0},
        'all_features': {'w_left': 1.0, 'w_right': 1.0, 'w_pos': 0.5, 'w_skel': 0.5},
    }

    ablation_results = {}
    pr(f"  {'Feature Set':>16s}  {'k':>4s}  {'Silh':>6s}  {'h_ratio':>7s}  {'Types':>6s}")
    pr(f"  {'─'*16}  {'─'*4}  {'─'*6}  {'─'*7}  {'─'*6}")

    test_k = opt_k  # use the optimal k from full features

    for fname, weights in feature_sets.items():
        dist_abl = compute_distance_matrix(frequent, features, **weights)
        mh_abl, _ = agglomerative_cluster(dist_abl, N)
        cs_abl = cut_dendrogram(mh_abl, N, test_k)

        # Build mapping
        c2c_abl = {}
        for cls_idx, members in enumerate(cs_abl):
            for m in members:
                c2c_abl[frequent[m]] = f"C{cls_idx}"
        for c in chunk_counts:
            if c not in c2c_abl:
                c2c_abl[c] = "RARE"

        fp_abl, _ = collapse_and_fingerprint(word_chunks_list, c2c_abl)
        labels_abl = np.zeros(N, dtype=int)
        for cls_idx, members in enumerate(cs_abl):
            for m in members:
                labels_abl[m] = cls_idx
        sil_abl = silhouette_score(dist_abl, labels_abl, N)

        ablation_results[fname] = {
            'silhouette': sil_abl,
            'fingerprint': fp_abl,
        }

        if fp_abl:
            pr(f"  {fname:>16s}  {test_k:4d}  {sil_abl:6.3f}  "
               f"{fp_abl['h_ratio']:7.4f}  {fp_abl['n_types']:6d}")
    pr()

    # ── STEP 9: MIN_FREQ SENSITIVITY ──────────────────────────────────

    pr("─" * 76)
    pr("STEP 9: MINIMUM FREQUENCY THRESHOLD SENSITIVITY")
    pr("─" * 76)
    pr()
    pr("  Does the optimal k change with different chunk inclusion thresholds?")
    pr()

    for mf in [10, 20, 50]:
        freq_mf, feat_mf, _ = extract_distributional_features(
            word_chunks_list, min_freq=mf)
        N_mf = len(freq_mf)
        if N_mf < 20:
            pr(f"  min_freq={mf}: only {N_mf} chunks — too few")
            continue

        dist_mf = compute_distance_matrix(freq_mf, feat_mf)
        mh_mf, _ = agglomerative_cluster(dist_mf, N_mf)

        # Test a few k values
        best_sil_mf = -1
        best_k_mf = -1
        for k_test in [20, 25, 30, 35, 40, 50]:
            if k_test >= N_mf:
                continue
            cs_mf = cut_dendrogram(mh_mf, N_mf, k_test)
            labels_mf = np.zeros(N_mf, dtype=int)
            for ci, members in enumerate(cs_mf):
                for m in members:
                    labels_mf[m] = ci
            s_mf = silhouette_score(dist_mf, labels_mf, N_mf)
            if s_mf > best_sil_mf:
                best_sil_mf = s_mf
                best_k_mf = k_test

        pr(f"  min_freq={mf:3d}: {N_mf:4d} chunks, best k={best_k_mf}, silhouette={best_sil_mf:.4f}")
    pr()

    # ── STEP 10: NL SYLLABLE CROSS-CHECK ──────────────────────────────

    pr("─" * 76)
    pr("STEP 10: NL SYLLABLE CROSS-CHECK")
    pr("─" * 76)
    pr()
    pr("  If NL syllables also cluster to ~30 groups with good metrics,")
    pr("  the method is FLAWED and proves nothing about VMS specifically.")
    pr()

    ref_files = {
        'Latin-Caesar': DATA_DIR / 'latin_texts' / 'caesar.txt',
        'Italian-Cucina': DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt',
    }

    for name, fpath in ref_files.items():
        if not fpath.exists():
            pr(f"  {name}: file not found, skipping")
            continue

        ref_words = load_reference_text(fpath)
        if len(ref_words) < 1000:
            pr(f"  {name}: too few words ({len(ref_words)}), skipping")
            continue

        # Syllabify and get base stats
        all_syls = []
        word_syls = []
        for w in ref_words:
            syls = syllabify_word(w)
            word_syls.append(syls)
            all_syls.extend(syls)

        syl_counts = Counter(all_syls)
        base_fp = compute_unit_fingerprint(all_syls)

        pr(f"  {name}: {len(ref_words)} words, {len(all_syls)} syllables, "
           f"{len(syl_counts)} types")
        if base_fp:
            pr(f"    Base h_ratio={base_fp['h_ratio']:.4f}, "
               f"hapax={base_fp['hapax_ratio']:.4f}")

        # Random merging at key k values
        pr(f"    Random merge to k=30: ", end='')
        rm30 = random_merge_fingerprint(word_syls, [],
                                         list(syl_counts.keys()), 30, n_trials=30)
        pr(f"h_ratio={rm30.get('h_ratio_mean',0):.4f}±{rm30.get('h_ratio_std',0):.4f}, "
           f"types={rm30.get('n_types_mean',0):.1f}")

        pr(f"    Random merge to k={opt_k}: ", end='')
        rmk = random_merge_fingerprint(word_syls, [],
                                        list(syl_counts.keys()), opt_k, n_trials=30)
        pr(f"h_ratio={rmk.get('h_ratio_mean',0):.4f}±{rmk.get('h_ratio_std',0):.4f}, "
           f"types={rmk.get('n_types_mean',0):.1f}")
    pr()

    # ── STEP 11: CLUSTER COHERENCE — SHARED SLOT SKELETONS ────────────

    pr("─" * 76)
    pr("STEP 11: CLUSTER COHERENCE — DO CLUSTERS SHARE SLOT SKELETONS?")
    pr("─" * 76)
    pr()
    pr("  If clusters are linguistically meaningful, members should share")
    pr("  similar slot-filling patterns. Compute intra-cluster skeleton entropy.")
    pr()

    opt_clusters_sorted = sorted(opt_clusters, key=lambda s: -len(s))
    total_skel_entropy = 0
    n_multi = 0

    pr(f"  {'Cls':>4s}  {'Size':>5s}  {'SkelEntropy':>12s}  {'DominantSkel':>14s}  {'DomPct':>7s}")
    pr(f"  {'─'*4}  {'─'*5}  {'─'*12}  {'─'*14}  {'─'*7}")

    for cls_idx, members in enumerate(opt_clusters_sorted[:30]):
        member_chunks = [frequent[m] for m in members]
        skels = []
        for c in member_chunks:
            skel = ''.join(str(int(s)) for s in features[c]['slot_skel'])
            skels.append(skel)
        skel_counter = Counter(skels)
        skel_h = entropy(skel_counter)
        dom_skel, dom_count = skel_counter.most_common(1)[0]
        dom_pct = 100 * dom_count / len(skels)

        total_skel_entropy += skel_h * len(members)
        n_multi += len(members)

        pr(f"  {cls_idx:4d}  {len(members):5d}  {skel_h:12.3f}  "
           f"{dom_skel:>14s}  {dom_pct:6.1f}%")

    avg_skel_entropy = total_skel_entropy / n_multi if n_multi > 0 else 0
    pr()
    pr(f"  Weighted average intra-cluster skeleton entropy: {avg_skel_entropy:.4f}")
    pr(f"  (0 = perfect skeleton coherence; higher = mixed skeletons)")
    pr()

    # ── SYNTHESIS ──────────────────────────────────────────────────────

    pr("=" * 76)
    pr("SYNTHESIS & VERDICT")
    pr("=" * 76)
    pr()

    # Gather key results
    opt_fp = sweep_results[opt_k]['fingerprint']
    opt_sil = sweep_results[opt_k]['silhouette']

    pr(f"  1. OPTIMAL CLUSTER COUNT")
    pr(f"     Best silhouette k:        {best_sil_k}")
    pr(f"     Best NL-char h_ratio k:   {best_h_k}")
    pr(f"     Combined optimal k:       {opt_k}")
    pr(f"     Silhouette at optimal k:  {opt_sil:.4f}")
    pr()

    pr(f"  2. COLLAPSED METRICS AT k={opt_k}")
    if opt_fp:
        pr(f"     h_ratio:    {opt_fp['h_ratio']:.4f}  (NL char: 0.849)")
        pr(f"     hapax:      {opt_fp['hapax_ratio']:.4f}")
        pr(f"     Zipf slope: {opt_fp['zipf_slope']:.4f}")
        pr(f"     Heaps beta: {opt_fp['heaps_beta']:.4f}")
        pr(f"     Types:      {opt_fp['n_types']}")
    pr()

    pr(f"  3. VS RANDOM MERGING AT k={opt_k}")
    if opt_k in json_null:
        rm = json_null[opt_k]
        for metric in ['h_ratio', 'hapax_ratio']:
            val = opt_fp[metric] if opt_fp else float('nan')
            rm_mean = rm.get(metric + '_mean', float('nan'))
            rm_std = rm.get(metric + '_std', float('nan'))
            z = (val - rm_mean) / rm_std if rm_std > 1e-10 else float('nan')
            pr(f"     {metric}: clustered={val:.4f}, random={rm_mean:.4f}±{rm_std:.4f}, z={z:.2f}")
    pr()

    pr(f"  4. FEATURE ABLATION")
    for fname, res in ablation_results.items():
        fp = res['fingerprint']
        if fp:
            pr(f"     {fname:16s}: h_ratio={fp['h_ratio']:.4f}, sil={res['silhouette']:.3f}")
    pr()

    pr(f"  5. CLUSTER COHERENCE")
    pr(f"     Average intra-cluster skeleton entropy: {avg_skel_entropy:.4f}")
    if avg_skel_entropy < 0.5:
        pr(f"     → GOOD: clusters largely share slot skeletons")
    elif avg_skel_entropy < 1.0:
        pr(f"     → MODERATE: some skeleton mixing within clusters")
    else:
        pr(f"     → POOR: clusters mix different slot skeletons freely")
    pr()

    # Determine verdict
    # Key question: does distributional clustering produce BETTER results
    # than random merging? And does the optimal k suggest an alphabet?
    if opt_fp and opt_k in json_null:
        rm = json_null[opt_k]
        h_val = opt_fp['h_ratio']
        h_rm = rm.get('h_ratio_mean', 0)
        h_rm_std = rm.get('h_ratio_std', 1)
        z_h = (h_val - h_rm) / h_rm_std if h_rm_std > 1e-10 else 0

        clustered_closer = abs(h_val - 0.849) < abs(h_rm - 0.849)
        sil_above_thresh = opt_sil > 0.05
        k_in_alphabet_range = 20 <= opt_k <= 50

        pr(f"  VERDICT:")
        if clustered_closer and sil_above_thresh and k_in_alphabet_range:
            pr(f"     ★ SUPPORTED: Distributional clustering finds ~{opt_k} equivalence")
            pr(f"       classes with better NL-char match than random merging.")
            pr(f"       This suggests a 'true alphabet' of ~{opt_k} functional units.")
            verdict = "SUPPORTED"
        elif clustered_closer and k_in_alphabet_range:
            pr(f"     ◐ PARTIALLY SUPPORTED: k={opt_k} is in alphabet range and")
            pr(f"       clustering beats random, but silhouette is weak ({opt_sil:.3f}).")
            pr(f"       Clusters may not be sharply defined.")
            verdict = "PARTIALLY_SUPPORTED"
        elif not clustered_closer:
            pr(f"     ✗ NOT SUPPORTED: Distributional clustering does NOT produce")
            pr(f"       better NL-character match than random merging at k={opt_k}.")
            pr(f"       The 523 chunk types do not reduce to a clean alphabet.")
            verdict = "NOT_SUPPORTED"
        else:
            pr(f"     ? INCONCLUSIVE: k={opt_k} is outside alphabet range (20-50).")
            pr(f"       Result ambiguous — may indicate a different unit structure.")
            verdict = "INCONCLUSIVE"
    else:
        pr(f"  VERDICT: INSUFFICIENT DATA for determination.")
        verdict = "INSUFFICIENT"

    pr()

    # ── SAVE RESULTS ──────────────────────────────────────────────────

    json_out = {
        'n_frequent_chunks': len(frequent),
        'min_freq_threshold': MIN_FREQ,
        'optimal_k': {
            'best_silhouette_k': best_sil_k,
            'best_h_ratio_k': best_h_k,
            'combined_k': opt_k,
        },
        'sweep': {
            str(k): {
                'silhouette': sweep_results[k]['silhouette'],
                'h_ratio': sweep_results[k]['fingerprint']['h_ratio'] if sweep_results[k]['fingerprint'] else None,
                'hapax_ratio': sweep_results[k]['fingerprint']['hapax_ratio'] if sweep_results[k]['fingerprint'] else None,
                'n_types': sweep_results[k]['fingerprint']['n_types'] if sweep_results[k]['fingerprint'] else None,
                'zipf_slope': sweep_results[k]['fingerprint']['zipf_slope'] if sweep_results[k]['fingerprint'] else None,
                'heaps_beta': sweep_results[k]['fingerprint']['heaps_beta'] if sweep_results[k]['fingerprint'] else None,
            }
            for k in K_VALUES
        },
        'null_model_random': {str(k): v for k, v in json_null.items()},
        'ablation': {
            fname: {
                'silhouette': res['silhouette'],
                'h_ratio': res['fingerprint']['h_ratio'] if res['fingerprint'] else None,
            }
            for fname, res in ablation_results.items()
        },
        'cluster_coherence': {
            'avg_skeleton_entropy': avg_skel_entropy,
        },
        'verdict': verdict,
    }

    # Save cluster composition at optimal k
    opt_cluster_comp = {}
    for cls_idx, members in enumerate(opt_clusters_sorted):
        member_chunks = [frequent[m] for m in sorted(members)]
        member_chunks.sort(key=lambda c: -chunk_counts[c])
        opt_cluster_comp[f"C{cls_idx}"] = {
            'size': len(members),
            'members': member_chunks,
            'total_tokens': sum(chunk_counts[c] for c in member_chunks),
        }
    json_out['cluster_composition'] = opt_cluster_comp

    with open(RESULTS_DIR / 'phase86_chunk_equivalence.json', 'w') as f:
        json.dump(json_out, f, indent=2, default=str)

    text_out = ''.join(OUTPUT)
    with open(RESULTS_DIR / 'phase86_chunk_equivalence.txt', 'w', encoding='utf-8') as f:
        f.write(text_out)

    pr()
    pr(f"  Results saved to results/phase86_chunk_equivalence.txt/.json")


if __name__ == '__main__':
    main()
