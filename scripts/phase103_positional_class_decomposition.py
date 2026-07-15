#!/usr/bin/env python3
"""
Phase 103 — Positional Decomposition of the 25-Class Chunk Alphabet

═══════════════════════════════════════════════════════════════════════

QUESTION:
  Is the extreme positional restriction of VMS chunks (J(I,F)=0.241)
  a cipher signature or just an artifact of the LOOP slot grammar?

  Specifically:
  1. When we decompose the 25 equivalence classes by word position
     (I/M/F), what are the effective sub-alphabet sizes at each position?
  2. Do NL syllables show comparable position restriction when
     decomposed the same way?  If so, it's grammar, not cipher.
  3. Which reference language's positional letter profile best matches
     VMS positional class profile?
  4. Does the F→I cross-word transition behave like a word-boundary
     reset (MI ≈ 0) or carry structure (MI > 0)?

APPROACH:
  1. Parse VMS into chunks → assign to 25 equivalence classes (from Phase 86)
  2. Label each class token by word position (I/M/F)
  3. Build position-stratified class profiles:
     - P(class|position=I), P(class|position=M), P(class|position=F)
     - Count effective sub-alphabet at each position (≥1% threshold)
     - Classify each class as I-dominant, F-dominant, M-dominant, universal
  4. Build 4 transition matrices: I→M, M→M, M→F, F→I (cross-word)
     - Compute MI for each; test F→I ≈ product of marginals?
  5. For NL reference corpora: syllabify, cluster into ~25 classes by
     distributional similarity, repeat steps 2-4.  Compare J(I,F),
     sub-alphabet sizes, MI ratios.
  6. Positional letter profile comparison: for each NL language, compute
     P(letter|initial), P(letter|final) — rank-correlate with VMS
     P(class|I), P(class|F) after mapping by frequency rank.
  7. Null model: within-word chunk-position shuffle (100 trials)

SKEPTICISM NOTES:
  - The 25 classes are skeleton-dominated (Phase 86 ablation: skeleton-only
    silhouette=0.848 vs all-features 0.250).  Position restriction could
    be 100% structural (onset chunks are initial, coda chunks are final)
    rather than cryptographic.  Must test this explicitly.
  - 56% of VMS words are 2-chunk → medial position (M) is sparse.
    Sub-alphabet size for M will be unreliable.  Focus on I vs F.
  - NL syllable clustering into 25 classes may not be meaningful (Phase 86
    showed NL syllables should NOT cluster this way).  If NL clustering
    fails, the comparison is invalid and we note this.
  - Reference language matching by positional profile is indirect; we're
    comparing shapes, not identities.  A match proves consistency, not
    identity.
  - The F→I MI test reuses the Phase 90 framework but at class level
    (25×25 matrix) rather than raw chunk level (523×523).  The coarser
    grain should give more stable estimates but less resolution.
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import chunk_to_str, clean_word, entropy, eva_to_glyphs, load_reference_text, parse_one_chunk, parse_word_into_chunks

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
# VMS PARSING — LINE-AWARE (from Phase 90)
# ═══════════════════════════════════════════════════════════════════════

SECTION_MAP = {
    'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
    'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
}


def load_vms_lines():
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
    chunk_lines = []
    for lid, section, words in vms_lines:
        word_chunks_list = []
        for w in words:
            chunks, unparsed, _ = parse_word_into_chunks(w)
            chunk_ids = [chunk_to_str(c) for c in chunks]
            if chunk_ids:
                word_chunks_list.append(chunk_ids)
        if word_chunks_list:
            chunk_lines.append((lid, section, word_chunks_list))
    return chunk_lines


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



# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL HELPERS
# ═══════════════════════════════════════════════════════════════════════


def mi_from_bigram_counter(bigram_counts, left_counts, right_counts):
    """Compute MI(X;Y) from bigram and marginal counts."""
    n = sum(bigram_counts.values())
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    h_x = entropy(left_counts)
    h_y = entropy(right_counts)
    h_xy = entropy(bigram_counts)
    mi = h_x + h_y - h_xy
    nmi = mi / min(h_x, h_y) if min(h_x, h_y) > 0.001 else 0.0
    return mi, nmi, h_x, h_y

def jaccard(set_a, set_b):
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

def spearman_rank_corr(x, y):
    """Spearman rank correlation between two vectors."""
    n = len(x)
    if n < 3:
        return 0.0
    rx = np.argsort(np.argsort(-np.array(x, dtype=float))).astype(float)
    ry = np.argsort(np.argsort(-np.array(y, dtype=float))).astype(float)
    d = rx - ry
    return 1.0 - 6.0 * np.sum(d**2) / (n * (n**2 - 1))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 86 EQUIVALENCE CLASS RECONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════

def build_equivalence_classes(all_chunk_tokens, k=25):
    """Reproduce Phase 86 clustering: agglomerative with JSD on
    distributional features.  Returns dict: chunk_str → class_id."""

    # Count chunks
    freq = Counter(all_chunk_tokens)
    min_freq = 20
    frequent = [c for c, f in freq.items() if f >= min_freq]
    frequent_set = set(frequent)

    if len(frequent) < k:
        pr(f"  WARNING: only {len(frequent)} frequent chunks, reducing k to {len(frequent)}")
        k = len(frequent)

    # Build context features (left, right distributions)
    left_ctx = defaultdict(Counter)
    right_ctx = defaultdict(Counter)
    for tokens in all_chunk_tokens_by_word:
        for i, t in enumerate(tokens):
            if t not in frequent_set:
                continue
            if i > 0 and tokens[i-1] in frequent_set:
                left_ctx[t][tokens[i-1]] += 1
            if i < len(tokens) - 1 and tokens[i+1] in frequent_set:
                right_ctx[t][tokens[i+1]] += 1

    # Build word-position features
    pos_profile = defaultdict(lambda: [0, 0, 0])  # [I, M, F]
    for tokens in all_chunk_tokens_by_word:
        n = len(tokens)
        if n < 2:
            continue
        for i, t in enumerate(tokens):
            if t not in frequent_set:
                continue
            if i == 0:
                pos_profile[t][0] += 1
            elif i == n - 1:
                pos_profile[t][2] += 1
            else:
                pos_profile[t][1] += 1

    # Build slot skeleton feature
    skel = {}
    for c in frequent:
        glyphs = c.split('.')
        skel[c] = slot_pattern(glyphs)

    # Feature matrix: context (left+right) + position + skeleton
    all_types_sorted = sorted(frequent)
    type_to_idx = {t: i for i, t in enumerate(all_types_sorted)}
    n_types = len(all_types_sorted)

    feature_vecs = []
    for t in all_types_sorted:
        # Left context distribution (n_types dims)
        lc = np.zeros(n_types)
        for c2, cnt in left_ctx[t].items():
            if c2 in type_to_idx:
                lc[type_to_idx[c2]] = cnt
        lc_sum = lc.sum()
        if lc_sum > 0:
            lc /= lc_sum

        # Right context distribution (n_types dims)
        rc = np.zeros(n_types)
        for c2, cnt in right_ctx[t].items():
            if c2 in type_to_idx:
                rc[type_to_idx[c2]] = cnt
        rc_sum = rc.sum()
        if rc_sum > 0:
            rc /= rc_sum

        # Position profile (3 dims)
        pp = np.array(pos_profile[t], dtype=float)
        pp_sum = pp.sum()
        if pp_sum > 0:
            pp /= pp_sum

        # Skeleton (5 dims)
        sk = np.array(skel.get(t, (0,0,0,0,0)), dtype=float)

        feature_vecs.append(np.concatenate([lc, rc, pp, sk]))

    feature_matrix = np.array(feature_vecs)

    # JSD distance matrix
    n = len(all_types_sorted)
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            d = _jsd_vec(feature_matrix[i], feature_matrix[j])
            dist[i, j] = d
            dist[j, i] = d

    # Agglomerative clustering (average linkage)
    labels = _agglomerative_avg_linkage(dist, k)

    chunk_to_class = {}
    for i, t in enumerate(all_types_sorted):
        chunk_to_class[t] = int(labels[i])

    # Assign rare chunks to nearest class
    if frequent_set != set(freq.keys()):
        class_centroids = defaultdict(lambda: np.zeros(feature_matrix.shape[1]))
        class_counts_c = Counter()
        for i, t in enumerate(all_types_sorted):
            cl = labels[i]
            class_centroids[cl] += feature_matrix[i]
            class_counts_c[cl] += 1
        for cl in class_centroids:
            class_centroids[cl] /= class_counts_c[cl]

        for c in freq:
            if c in chunk_to_class:
                continue
            # Assign by slot skeleton match to nearest class
            sk = np.array(slot_pattern(c.split('.')), dtype=float)
            best_cl = 0
            best_d = float('inf')
            for cl, centroid in class_centroids.items():
                d = np.sum((sk - centroid[-5:])**2)
                if d < best_d:
                    best_d = d
                    best_cl = cl
            chunk_to_class[c] = best_cl

    return chunk_to_class


def _jsd_vec(p, q):
    """Jensen-Shannon divergence between two non-negative vectors."""
    p = p + 1e-12
    q = q + 1e-12
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)
    kl_pm = np.sum(p * np.log2(p / m))
    kl_qm = np.sum(q * np.log2(q / m))
    return 0.5 * (kl_pm + kl_qm)


def _agglomerative_avg_linkage(dist_matrix, k):
    """Simple average-linkage agglomerative clustering.
    Returns array of cluster labels."""
    n = dist_matrix.shape[0]
    # Each point starts as its own cluster
    clusters = {i: [i] for i in range(n)}
    active = set(range(n))

    # Precompute linkage distances
    link_dist = dist_matrix.copy()

    while len(active) > k:
        # Find closest pair
        best_i, best_j = -1, -1
        best_d = float('inf')
        active_list = sorted(active)
        for idx_a in range(len(active_list)):
            for idx_b in range(idx_a + 1, len(active_list)):
                i, j = active_list[idx_a], active_list[idx_b]
                if link_dist[i, j] < best_d:
                    best_d = link_dist[i, j]
                    best_i, best_j = i, j

        # Merge j into i
        ni = len(clusters[best_i])
        nj = len(clusters[best_j])
        clusters[best_i].extend(clusters[best_j])
        del clusters[best_j]
        active.remove(best_j)

        # Update distances (average linkage)
        for other in active:
            if other == best_i:
                continue
            new_d = (link_dist[best_i, other] * ni + link_dist[best_j, other] * nj) / (ni + nj)
            link_dist[best_i, other] = new_d
            link_dist[other, best_i] = new_d

    # Assign labels
    labels = np.zeros(n, dtype=int)
    for cl_id, (_, members) in enumerate(sorted(clusters.items())):
        for m in members:
            labels[m] = cl_id
    return labels


# ═══════════════════════════════════════════════════════════════════════
# NL SYLLABLE CLUSTERING (simplified: cluster by slot-like features)
# ═══════════════════════════════════════════════════════════════════════

def cluster_nl_syllables(words, k=25, min_freq=20, max_types=300):
    """Syllabify NL words, cluster frequent syllable types by
    distributional context into k classes."""
    # Syllabify
    word_syls = []
    for w in words:
        syls = syllabify_word(w)
        if syls:
            word_syls.append(syls)

    # Flatten for frequency count
    flat = [s for ws in word_syls for s in ws]
    freq = Counter(flat)
    frequent = [s for s, f in freq.items() if f >= min_freq]
    # Cap at max_types to keep O(n²) clustering tractable
    if len(frequent) > max_types:
        frequent = sorted(frequent, key=lambda s: freq[s], reverse=True)[:max_types]
    frequent_set = set(frequent)

    if len(frequent) < k:
        k = min(len(frequent), k)
    if k < 2:
        return {}, word_syls, k

    # Position profiles
    pos_profile = defaultdict(lambda: [0, 0, 0])
    for ws in word_syls:
        n = len(ws)
        if n < 2:
            continue
        for i, s in enumerate(ws):
            if s not in frequent_set:
                continue
            if i == 0:
                pos_profile[s][0] += 1
            elif i == n - 1:
                pos_profile[s][2] += 1
            else:
                pos_profile[s][1] += 1

    # Left/right context
    left_ctx = defaultdict(Counter)
    right_ctx = defaultdict(Counter)
    for ws in word_syls:
        for i, s in enumerate(ws):
            if s not in frequent_set:
                continue
            if i > 0 and ws[i-1] in frequent_set:
                left_ctx[s][ws[i-1]] += 1
            if i < len(ws) - 1 and ws[i+1] in frequent_set:
                right_ctx[s][ws[i+1]] += 1

    sorted_types = sorted(frequent)
    type_to_idx = {t: i for i, t in enumerate(sorted_types)}
    n_types = len(sorted_types)

    features = []
    for t in sorted_types:
        lc = np.zeros(n_types)
        for c2, cnt in left_ctx[t].items():
            if c2 in type_to_idx:
                lc[type_to_idx[c2]] = cnt
        s = lc.sum()
        if s > 0: lc /= s

        rc = np.zeros(n_types)
        for c2, cnt in right_ctx[t].items():
            if c2 in type_to_idx:
                rc[type_to_idx[c2]] = cnt
        s = rc.sum()
        if s > 0: rc /= s

        pp = np.array(pos_profile[t], dtype=float)
        s = pp.sum()
        if s > 0: pp /= s

        features.append(np.concatenate([lc, rc, pp]))

    feat_mat = np.array(features)

    # JSD distance
    n = len(sorted_types)
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            d = _jsd_vec(feat_mat[i], feat_mat[j])
            dist[i, j] = d
            dist[j, i] = d

    labels = _agglomerative_avg_linkage(dist, k)

    syl_to_class = {}
    for i, t in enumerate(sorted_types):
        syl_to_class[t] = int(labels[i])

    # Rare syllables → nearest class by position profile
    if len(syl_to_class) < len(freq):
        class_pos = defaultdict(lambda: np.zeros(3))
        class_cnt = Counter()
        for i, t in enumerate(sorted_types):
            cl = labels[i]
            pp = np.array(pos_profile[t], dtype=float)
            s = pp.sum()
            if s > 0: pp /= s
            class_pos[cl] += pp
            class_cnt[cl] += 1
        for cl in class_pos:
            class_pos[cl] /= class_cnt[cl]

        for s_type in freq:
            if s_type in syl_to_class:
                continue
            pp = np.array(pos_profile.get(s_type, [0,0,0]), dtype=float)
            s = pp.sum()
            if s > 0:
                pp /= s
            best_cl, best_d = 0, float('inf')
            for cl, cp in class_pos.items():
                d = np.sum((pp - cp)**2)
                if d < best_d:
                    best_d = d
                    best_cl = cl
            syl_to_class[s_type] = best_cl

    return syl_to_class, word_syls, k


# ═══════════════════════════════════════════════════════════════════════
# POSITION DECOMPOSITION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def positional_decomposition(word_units_list, unit_to_class, label="VMS"):
    """Core analysis: decompose class inventory by word position.

    Args:
        word_units_list: list of lists (each = units in one word)
        unit_to_class: dict mapping unit string to class id
        label: name for display

    Returns dict with all results.
    """
    # Count class occurrences by position
    pos_counts = defaultdict(Counter)  # pos → Counter(class → count)
    total_by_pos = Counter()
    n_words = 0
    n_units = 0

    # Also track per-class position profile
    class_pos_counts = defaultdict(Counter)  # class → Counter(pos → count)

    for units in word_units_list:
        n = len(units)
        if n < 2:
            continue
        n_words += 1
        for i, u in enumerate(units):
            cl = unit_to_class.get(u)
            if cl is None:
                continue
            if i == 0:
                pos = 'I'
            elif i == n - 1:
                pos = 'F'
            else:
                pos = 'M'
            pos_counts[pos][cl] += 1
            class_pos_counts[cl][pos] += 1
            total_by_pos[pos] += 1
            n_units += 1

    # Effective sub-alphabet at each position (≥1% of position's tokens)
    sub_alpha = {}
    for pos in ['I', 'M', 'F']:
        total = total_by_pos[pos]
        if total == 0:
            sub_alpha[pos] = 0
            continue
        threshold = 0.01 * total
        active = [cl for cl, cnt in pos_counts[pos].items() if cnt >= threshold]
        sub_alpha[pos] = len(active)

    # Also: effective sub-alphabet at ≥0.1% threshold (more generous)
    sub_alpha_01 = {}
    for pos in ['I', 'M', 'F']:
        total = total_by_pos[pos]
        if total == 0:
            sub_alpha_01[pos] = 0
            continue
        threshold = 0.001 * total
        active = [cl for cl, cnt in pos_counts[pos].items() if cnt >= threshold]
        sub_alpha_01[pos] = len(active)

    # Classify each class as I-dominant, M-dominant, F-dominant, or universal
    class_types = {}
    class_pci = {}
    all_classes = set()
    for cl, counts in class_pos_counts.items():
        all_classes.add(cl)
        total = sum(counts.values())
        if total < 5:
            class_types[cl] = 'rare'
            class_pci[cl] = 1.0
            continue
        props = {p: counts.get(p, 0) / total for p in ['I', 'M', 'F']}
        max_pos = max(props, key=props.get)
        pci = props[max_pos]
        class_pci[cl] = pci

        # Entropy of position distribution
        h_pos = -sum(p * math.log2(p) for p in props.values() if p > 0)
        if h_pos < 0.5:      # very concentrated (< ~0.5 bits of 1.58 max)
            class_types[cl] = f'{max_pos}-locked'
        elif h_pos < 1.0:    # somewhat concentrated
            class_types[cl] = f'{max_pos}-dominant'
        else:                 # distributed
            class_types[cl] = 'universal'

    # Jaccard overlap of position-specific type inventories
    I_types = set(cl for cl, cnt in pos_counts['I'].items() if cnt >= 5)
    F_types = set(cl for cl, cnt in pos_counts['F'].items() if cnt >= 5)
    M_types = set(cl for cl, cnt in pos_counts['M'].items() if cnt >= 5)
    j_if = jaccard(I_types, F_types)
    j_im = jaccard(I_types, M_types)
    j_mf = jaccard(M_types, F_types)

    # Mutual information I(class; position)
    # Joint distribution
    joint = Counter()
    for pos in ['I', 'M', 'F']:
        for cl, cnt in pos_counts[pos].items():
            joint[(cl, pos)] += cnt
    class_marginal = Counter()
    for (cl, pos), cnt in joint.items():
        class_marginal[cl] += cnt
    total_all = sum(joint.values())

    mi_class_pos = 0.0
    if total_all > 0:
        for (cl, pos), cnt in joint.items():
            p_joint = cnt / total_all
            p_cl = class_marginal[cl] / total_all
            p_pos = total_by_pos[pos] / total_all
            if p_joint > 0 and p_cl > 0 and p_pos > 0:
                mi_class_pos += p_joint * math.log2(p_joint / (p_cl * p_pos))

    h_class = entropy(class_marginal)
    h_pos_global = entropy(total_by_pos)
    nmi_class_pos = mi_class_pos / min(h_class, h_pos_global) if min(h_class, h_pos_global) > 0.001 else 0.0

    return {
        'label': label,
        'n_words': n_words,
        'n_units': n_units,
        'n_classes': len(all_classes),
        'sub_alpha_1pct': sub_alpha,
        'sub_alpha_01pct': sub_alpha_01,
        'class_types': class_types,
        'class_pci': class_pci,
        'j_if': j_if,
        'j_im': j_im,
        'j_mf': j_mf,
        'mi_class_pos': mi_class_pos,
        'nmi_class_pos': nmi_class_pos,
        'h_class': h_class,
        'h_pos': h_pos_global,
        'pos_counts': {p: dict(c) for p, c in pos_counts.items()},
        'total_by_pos': dict(total_by_pos),
        'class_pos_counts': {cl: dict(c) for cl, c in class_pos_counts.items()},
    }


def build_transition_matrices(word_units_list, unit_to_class, lines_data=None):
    """Build I→M, M→M, M→F, F→I transition matrices at class level.

    For F→I (cross-word), needs lines_data = list of (line_id, section, word_chunks_list)
    to ensure word pairs are on the same line.

    Returns dict of {name: (bigram_counter, left_counter, right_counter)}.
    """
    result = {}

    # Within-word transitions
    im_bi = Counter(); im_l = Counter(); im_r = Counter()
    mm_bi = Counter(); mm_l = Counter(); mm_r = Counter()
    mf_bi = Counter(); mf_l = Counter(); mf_r = Counter()

    for units in word_units_list:
        n = len(units)
        if n < 2:
            continue
        classes = []
        for u in units:
            cl = unit_to_class.get(u)
            if cl is not None:
                classes.append(cl)
            else:
                classes.append(-1)

        for i in range(n - 1):
            if classes[i] == -1 or classes[i+1] == -1:
                continue
            # Determine position labels
            if i == 0:
                p_left = 'I'
            elif i == n - 1:
                p_left = 'F'
            else:
                p_left = 'M'

            if i + 1 == 0:
                p_right = 'I'
            elif i + 1 == n - 1:
                p_right = 'F'
            else:
                p_right = 'M'

            pair = (classes[i], classes[i+1])
            if p_left == 'I' and p_right == 'M':
                im_bi[pair] += 1; im_l[classes[i]] += 1; im_r[classes[i+1]] += 1
            elif p_left == 'I' and p_right == 'F':
                # 2-chunk word: I→F directly (most common case)
                im_bi[pair] += 1; im_l[classes[i]] += 1; im_r[classes[i+1]] += 1
                mf_bi[pair] += 1; mf_l[classes[i]] += 1; mf_r[classes[i+1]] += 1
            elif p_left == 'M' and p_right == 'M':
                mm_bi[pair] += 1; mm_l[classes[i]] += 1; mm_r[classes[i+1]] += 1
            elif p_left == 'M' and p_right == 'F':
                mf_bi[pair] += 1; mf_l[classes[i]] += 1; mf_r[classes[i+1]] += 1

    result['I→(M/F)'] = (im_bi, im_l, im_r)
    result['M→M'] = (mm_bi, mm_l, mm_r)
    result['(I/M)→F'] = (mf_bi, mf_l, mf_r)

    # Cross-word F→I transitions (need line structure)
    fi_bi = Counter(); fi_l = Counter(); fi_r = Counter()

    if lines_data is not None:
        for lid, section, word_chunks_list in lines_data:
            for w_idx in range(len(word_chunks_list) - 1):
                w1 = word_chunks_list[w_idx]
                w2 = word_chunks_list[w_idx + 1]
                if len(w1) < 1 or len(w2) < 1:
                    continue
                f_chunk = w1[-1]
                i_chunk = w2[0]
                f_cl = unit_to_class.get(f_chunk)
                i_cl = unit_to_class.get(i_chunk)
                if f_cl is not None and i_cl is not None:
                    fi_bi[(f_cl, i_cl)] += 1
                    fi_l[f_cl] += 1
                    fi_r[i_cl] += 1

    result['F→I (cross-word)'] = (fi_bi, fi_l, fi_r)

    return result


def positional_letter_profile(words):
    """Compute P(letter|initial), P(letter|medial), P(letter|final) for NL text."""
    init_counts = Counter()
    mid_counts = Counter()
    final_counts = Counter()

    for w in words:
        if len(w) < 2:
            continue
        init_counts[w[0]] += 1
        final_counts[w[-1]] += 1
        for c in w[1:-1]:
            mid_counts[c] += 1

    return init_counts, mid_counts, final_counts


def frequency_shape_distance(vms_pos_counts, nl_pos_counts, pos='I'):
    """Compare frequency distribution shapes between VMS classes-at-position
    and NL letters-at-position using L1 distance between normalized
    rank-frequency curves.

    Lower distance = more similar frequency shapes.

    NOTE: We compare SHAPES (how concentrated is the distribution?)
    not identities (which symbol is most common?).  This is valid
    because we don't know the mapping.
    """
    vms_c = vms_pos_counts.get(pos, {})
    if not vms_c or not nl_pos_counts:
        return float('inf')

    vms_freqs = sorted(vms_c.values(), reverse=True)
    nl_freqs = sorted(nl_pos_counts.values(), reverse=True)

    # Normalize to proportions
    vms_total = sum(vms_freqs)
    nl_total = sum(nl_pos_counts.values())
    if vms_total == 0 or nl_total == 0:
        return float('inf')
    vms_props = np.array([f / vms_total for f in vms_freqs])
    nl_props = np.array([f / nl_total for f in nl_freqs])

    # Pad to same length
    max_len = max(len(vms_props), len(nl_props))
    vms_padded = np.zeros(max_len)
    nl_padded = np.zeros(max_len)
    vms_padded[:len(vms_props)] = vms_props
    nl_padded[:len(nl_props)] = nl_props

    # L1 distance between rank-frequency curves
    l1 = np.sum(np.abs(vms_padded - nl_padded))

    # Also compute effective number (entropy-based) for comparison
    vms_h = -sum(p * math.log2(p) for p in vms_props if p > 0)
    nl_h = -sum(p * math.log2(p) for p in nl_props if p > 0)
    h_diff = abs(vms_h - nl_h)

    return l1, h_diff, vms_h, nl_h


# ═══════════════════════════════════════════════════════════════════════
# SLOT GRAMMAR CONTROL: how much position restriction is just grammar?
# ═══════════════════════════════════════════════════════════════════════

def slot_grammar_baseline(word_units_list, unit_to_class):
    """For each class, compute what fraction of its position restriction
    is explained by slot skeleton alone.

    If a class contains only coda-slot chunks (slot 5 only), it MUST be final.
    If it contains only onset-slot chunks (slot 1 only), it MUST be initial.
    The question is: does position restriction EXCEED what skeleton predicts?
    """
    # For each class, collect the slot patterns of its member chunks
    class_skeletons = defaultdict(list)
    # We need to map class → member chunks
    # Build inverse: class → set of chunk types
    class_members = defaultdict(set)
    for chunk_str, cl in unit_to_class.items():
        class_members[cl].add(chunk_str)

    for cl, members in class_members.items():
        for m in members:
            glyphs = m.split('.')
            sp = slot_pattern(glyphs)
            class_skeletons[cl].append(sp)

    # For each class, determine if skeleton FORCES a position
    grammar_forced = {}
    for cl, skels in class_skeletons.items():
        has_onset = any(s[0] == 1 for s in skels)
        has_coda = any(s[4] == 1 for s in skels)
        has_nucleus_only = any(s[0] == 0 and s[4] == 0 for s in skels)

        # A class is "onset-forced" if ALL members start with slot 1
        all_onset = all(s[0] == 1 for s in skels)
        all_coda_only = all(s[0] == 0 and s[1] == 0 and s[2] == 0 and s[3] == 0 and s[4] == 1 for s in skels)
        # More nuanced: "coda-containing" = has slot 5 but not slot 1
        no_onset_has_coda = all(s[0] == 0 and s[4] == 1 for s in skels)

        if all_onset:
            grammar_forced[cl] = 'onset-forced-I'
        elif all_coda_only:
            grammar_forced[cl] = 'coda-forced-F'
        elif no_onset_has_coda:
            grammar_forced[cl] = 'coda-leaning-F'
        else:
            grammar_forced[cl] = 'not-forced'

    return grammar_forced, class_members


# ═══════════════════════════════════════════════════════════════════════
# NULL MODEL: within-word position shuffle
# ═══════════════════════════════════════════════════════════════════════

def null_model_shuffle(word_units_list, unit_to_class, n_trials=100):
    """Shuffle chunk positions within each word, compute J(I,F).
    Lightweight version — only computes the Jaccard metric, not the full decomposition.
    Returns distribution of J(I,F) under null."""
    j_if_null = []
    for trial in range(n_trials):
        I_counts = Counter()
        F_counts = Counter()
        for units in word_units_list:
            n = len(units)
            if n < 2:
                continue
            s = list(units)
            random.shuffle(s)
            cl_i = unit_to_class.get(s[0])
            cl_f = unit_to_class.get(s[-1])
            if cl_i is not None:
                I_counts[cl_i] += 1
            if cl_f is not None:
                F_counts[cl_f] += 1
        I_types = set(cl for cl, cnt in I_counts.items() if cnt >= 5)
        F_types = set(cl for cl, cnt in F_counts.items() if cnt >= 5)
        j_if_null.append(jaccard(I_types, F_types))
    return np.array(j_if_null)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

# Need this global for build_equivalence_classes
all_chunk_tokens_by_word = []

def main():
    global all_chunk_tokens_by_word

    pr("=" * 72)
    pr("Phase 103 — Positional Decomposition of the 25-Class Chunk Alphabet")
    pr("=" * 72)
    pr()

    # ── Step 1: Load VMS, parse into chunks ──────────────────────────
    pr("Step 1: Loading VMS corpus and parsing into chunks...")
    vms_lines = load_vms_lines()
    chunk_lines = vms_lines_to_chunk_lines(vms_lines)

    n_lines = len(chunk_lines)
    n_words = sum(len(wc) for _, _, wc in chunk_lines)
    n_chunks = sum(sum(len(w) for w in wc) for _, _, wc in chunk_lines)
    pr(f"  Lines: {n_lines}")
    pr(f"  Words: {n_words}")
    pr(f"  Chunk tokens: {n_chunks}")
    pr()

    # Build flat word-chunks list for clustering
    word_chunks_flat = []
    for lid, sec, wc_list in chunk_lines:
        for wc in wc_list:
            word_chunks_flat.append(wc)

    all_chunk_tokens_by_word = word_chunks_flat

    all_chunk_tokens = [c for wc in word_chunks_flat for c in wc]
    chunk_freq = Counter(all_chunk_tokens)
    pr(f"  Unique chunk types: {len(chunk_freq)}")
    pr(f"  Frequent (≥20): {sum(1 for f in chunk_freq.values() if f >= 20)}")
    pr()

    # ── Step 2: Build 25 equivalence classes ─────────────────────────
    pr("Step 2: Building 25 equivalence classes (Phase 86 reproduction)...")
    chunk_to_class = build_equivalence_classes(all_chunk_tokens, k=25)
    n_classes = len(set(chunk_to_class.values()))
    pr(f"  Classes: {n_classes}")

    # Print class membership summary
    class_members_map = defaultdict(list)
    for c, cl in sorted(chunk_to_class.items()):
        class_members_map[cl].append(c)

    pr()
    pr("  Class membership:")
    for cl in sorted(class_members_map.keys()):
        members = class_members_map[cl]
        total_tok = sum(chunk_freq.get(m, 0) for m in members)
        top3 = sorted(members, key=lambda m: chunk_freq.get(m, 0), reverse=True)[:3]
        pr(f"    C{cl:02d} ({len(members):3d} types, {total_tok:6d} tok): "
           f"{', '.join(top3)}{'...' if len(members) > 3 else ''}")
    pr()

    # ── Step 3: Positional decomposition ─────────────────────────────
    pr("Step 3: Positional decomposition of VMS chunk classes...")
    pr()

    vms_result = positional_decomposition(word_chunks_flat, chunk_to_class, "VMS")

    pr(f"  Words used (≥2 chunks): {vms_result['n_words']}")
    pr(f"  Unit tokens: {vms_result['n_units']}")
    pr(f"  Active classes: {vms_result['n_classes']}")
    pr()

    pr("  Effective sub-alphabet sizes:")
    pr(f"    At ≥1% threshold:   I={vms_result['sub_alpha_1pct']['I']:2d}  "
       f"M={vms_result['sub_alpha_1pct']['M']:2d}  "
       f"F={vms_result['sub_alpha_1pct']['F']:2d}")
    pr(f"    At ≥0.1% threshold: I={vms_result['sub_alpha_01pct']['I']:2d}  "
       f"M={vms_result['sub_alpha_01pct']['M']:2d}  "
       f"F={vms_result['sub_alpha_01pct']['F']:2d}")
    pr()

    pr("  Jaccard overlap of position-specific class inventories:")
    pr(f"    J(I,F) = {vms_result['j_if']:.4f}")
    pr(f"    J(I,M) = {vms_result['j_im']:.4f}")
    pr(f"    J(M,F) = {vms_result['j_mf']:.4f}")
    pr()

    pr(f"  MI(class; position) = {vms_result['mi_class_pos']:.4f} bits")
    pr(f"  NMI(class; position) = {vms_result['nmi_class_pos']:.4f}")
    pr(f"  H(class) = {vms_result['h_class']:.4f} bits")
    pr(f"  H(position) = {vms_result['h_pos']:.4f} bits")
    pr()

    # Print per-class position profiles
    pr("  Per-class position profiles:")
    pr(f"  {'Class':>8s}  {'P(I)':>6s}  {'P(M)':>6s}  {'P(F)':>6s}  {'PCI':>5s}  {'Type':>14s}  {'Tokens':>6s}")
    pr(f"  {'─'*8}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*5}  {'─'*14}  {'─'*6}")

    for cl in sorted(vms_result['class_pos_counts'].keys()):
        counts = vms_result['class_pos_counts'][cl]
        total = sum(counts.values())
        pi = counts.get('I', 0) / total if total > 0 else 0
        pm = counts.get('M', 0) / total if total > 0 else 0
        pf = counts.get('F', 0) / total if total > 0 else 0
        pci = vms_result['class_pci'].get(cl, 0)
        ctype = vms_result['class_types'].get(cl, '?')
        pr(f"  C{cl:02d}       {pi:6.3f}  {pm:6.3f}  {pf:6.3f}  {pci:5.3f}  {ctype:>14s}  {total:6d}")
    pr()

    # ── Step 4: Slot grammar baseline ────────────────────────────────
    pr("Step 4: Slot grammar baseline — how much is forced by structure?")
    pr()
    grammar_forced, class_members_sets = slot_grammar_baseline(word_chunks_flat, chunk_to_class)

    n_forced = sum(1 for v in grammar_forced.values() if 'forced' in v)
    n_leaning = sum(1 for v in grammar_forced.values() if 'leaning' in v)
    n_free = sum(1 for v in grammar_forced.values() if v == 'not-forced')

    pr(f"  Grammar-forced classes: {n_forced}")
    pr(f"  Grammar-leaning classes: {n_leaning}")
    pr(f"  Structurally free classes: {n_free}")
    pr()

    for cl in sorted(grammar_forced.keys()):
        status = grammar_forced[cl]
        actual = vms_result['class_types'].get(cl, '?')
        match = '✓' if ('forced' in status and 'locked' in actual) else \
                '~' if ('leaning' in status and 'dominant' in actual) else \
                '✗' if (status == 'not-forced' and 'locked' in actual) else ' '
        pr(f"    C{cl:02d}: grammar={status:<20s}  observed={actual:<16s}  {match}")
    pr()

    # Count excess: classes that are position-locked but NOT grammar-forced
    excess = []
    for cl in sorted(grammar_forced.keys()):
        if grammar_forced[cl] == 'not-forced':
            actual = vms_result['class_types'].get(cl, '?')
            if 'locked' in actual or 'dominant' in actual:
                excess.append(cl)

    pr(f"  EXCESS position restriction (locked/dominant but NOT grammar-forced): "
       f"{len(excess)} classes")
    if excess:
        for cl in excess:
            members = sorted(class_members_sets.get(cl, set()),
                             key=lambda m: chunk_freq.get(m, 0), reverse=True)[:5]
            pr(f"    C{cl:02d}: {', '.join(members)}")
    pr()

    # ── Step 5: Transition matrices ──────────────────────────────────
    pr("Step 5: Position-conditioned transition matrices...")
    pr()

    transitions = build_transition_matrices(word_chunks_flat, chunk_to_class, chunk_lines)

    for name, (bi, lc, rc) in sorted(transitions.items()):
        mi, nmi, hx, hy = mi_from_bigram_counter(bi, lc, rc)
        n_pairs = sum(bi.values())
        pr(f"  {name:>20s}: {n_pairs:6d} pairs  MI={mi:.4f}  NMI={nmi:.4f}  "
           f"H(L)={hx:.3f}  H(R)={hy:.3f}")
    pr()

    # F→I independence test: is observed MI close to 0?
    fi_bi, fi_l, fi_r = transitions['F→I (cross-word)']
    fi_mi, fi_nmi, fi_hx, fi_hy = mi_from_bigram_counter(fi_bi, fi_l, fi_r)
    im_bi, im_l, im_r = transitions['I→(M/F)']
    im_mi, im_nmi, _, _ = mi_from_bigram_counter(im_bi, im_l, im_r)

    pr(f"  F→I / I→(M/F) MI ratio: {fi_mi / im_mi:.4f}" if im_mi > 0 else
       f"  F→I / I→(M/F) MI ratio: N/A")

    # Permutation null for F→I: shuffle word order within lines
    pr()
    pr("  F→I permutation null (100 trials, word-order shuffle within lines)...")
    fi_null_mis = []
    for trial in range(100):
        shuffled_lines = []
        for lid, sec, wc_list in chunk_lines:
            s = list(wc_list)
            random.shuffle(s)
            shuffled_lines.append((lid, sec, s))
        fi_null_bi = Counter()
        fi_null_l = Counter()
        fi_null_r = Counter()
        for lid, sec, wc_list in shuffled_lines:
            for w_idx in range(len(wc_list) - 1):
                w1 = wc_list[w_idx]
                w2 = wc_list[w_idx + 1]
                if len(w1) < 1 or len(w2) < 1:
                    continue
                f_cl = chunk_to_class.get(w1[-1])
                i_cl = chunk_to_class.get(w2[0])
                if f_cl is not None and i_cl is not None:
                    fi_null_bi[(f_cl, i_cl)] += 1
                    fi_null_l[f_cl] += 1
                    fi_null_r[i_cl] += 1
        null_mi, _, _, _ = mi_from_bigram_counter(fi_null_bi, fi_null_l, fi_null_r)
        fi_null_mis.append(null_mi)

    fi_null_arr = np.array(fi_null_mis)
    fi_z = (fi_mi - fi_null_arr.mean()) / fi_null_arr.std() if fi_null_arr.std() > 0 else 0
    pr(f"  F→I observed MI:  {fi_mi:.4f}")
    pr(f"  F→I null mean MI: {fi_null_arr.mean():.4f} ± {fi_null_arr.std():.4f}")
    pr(f"  F→I z-score:      {fi_z:.2f}")
    pr()

    # ── Step 6: Null model — position shuffle ────────────────────────
    pr("Step 6: Position-shuffle null model (100 trials)...")
    j_if_null = null_model_shuffle(word_chunks_flat, chunk_to_class, n_trials=100)
    j_if_z = (vms_result['j_if'] - j_if_null.mean()) / j_if_null.std() if j_if_null.std() > 0 else 0
    pr(f"  Observed J(I,F):    {vms_result['j_if']:.4f}")
    pr(f"  Null J(I,F) mean:   {j_if_null.mean():.4f} ± {j_if_null.std():.4f}")
    pr(f"  Z-score:            {j_if_z:.2f}")
    pr()

    # ── Step 7: NL reference comparison ──────────────────────────────
    pr("Step 7: NL reference comparison — syllable-level decomposition")
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

    nl_results = {}
    nl_letter_profiles = {}

    for name, path in sorted(nl_texts.items()):
        if not path.exists():
            pr(f"  {name}: FILE NOT FOUND, skipping")
            continue

        words = load_reference_text(path)
        if len(words) < 500:
            pr(f"  {name}: too few words ({len(words)}), skipping")
            continue

        pr(f"  {name} ({len(words)} words):")

        # Syllable-level clustering
        syl_to_class_nl, word_syls, k_actual = cluster_nl_syllables(words, k=25)
        if k_actual < 5:
            pr(f"    Too few syllable clusters ({k_actual}), skipping")
            continue

        # Positional decomposition at syllable-class level
        nl_res = positional_decomposition(word_syls, syl_to_class_nl, name)
        nl_results[name] = nl_res

        pr(f"    Classes: {nl_res['n_classes']}  "
           f"Sub-α(≥1%): I={nl_res['sub_alpha_1pct']['I']} M={nl_res['sub_alpha_1pct']['M']} F={nl_res['sub_alpha_1pct']['F']}  "
           f"J(I,F)={nl_res['j_if']:.4f}  MI(cl;pos)={nl_res['mi_class_pos']:.4f}  "
           f"NMI={nl_res['nmi_class_pos']:.4f}")

        # Letter-level positional profiles
        init_c, mid_c, final_c = positional_letter_profile(words)
        nl_letter_profiles[name] = (init_c, mid_c, final_c)

        # Cross-word F→I at syllable-class level (pseudo-lines of 7 words)
        pseudo_lines = []
        for i in range(0, len(word_syls), 7):
            batch = word_syls[i:i+7]
            if len(batch) >= 3:
                pseudo_lines.append((f"nl_{i}", 'nl', batch))
        nl_trans = build_transition_matrices(word_syls, syl_to_class_nl, pseudo_lines)
        nl_fi_bi, nl_fi_l, nl_fi_r = nl_trans['F→I (cross-word)']
        nl_fi_mi, nl_fi_nmi, _, _ = mi_from_bigram_counter(nl_fi_bi, nl_fi_l, nl_fi_r)
        nl_im_bi, nl_im_l, nl_im_r = nl_trans['I→(M/F)']
        nl_im_mi, _, _, _ = mi_from_bigram_counter(nl_im_bi, nl_im_l, nl_im_r)
        fi_ratio_nl = nl_fi_mi / nl_im_mi if nl_im_mi > 0 else float('nan')
        pr(f"    F→I MI={nl_fi_mi:.4f}  I→(M/F) MI={nl_im_mi:.4f}  ratio={fi_ratio_nl:.4f}")

    pr()

    # ── Step 8: Comparison summary ───────────────────────────────────
    pr("=" * 72)
    pr("COMPARISON SUMMARY")
    pr("=" * 72)
    pr()

    # Sub-alphabet sizes
    pr("Effective sub-alphabet sizes at ≥1% threshold:")
    pr(f"  {'System':>20s}  {'|A_I|':>6s}  {'|A_M|':>6s}  {'|A_F|':>6s}  {'J(I,F)':>7s}  {'NMI':>6s}")
    pr(f"  {'─'*20}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*7}  {'─'*6}")
    pr(f"  {'VMS chunks':>20s}  {vms_result['sub_alpha_1pct']['I']:6d}  "
       f"{vms_result['sub_alpha_1pct']['M']:6d}  {vms_result['sub_alpha_1pct']['F']:6d}  "
       f"{vms_result['j_if']:7.4f}  {vms_result['nmi_class_pos']:6.4f}")

    nl_j_ifs = []
    nl_nmis = []
    for name, res in sorted(nl_results.items()):
        pr(f"  {name:>20s}  {res['sub_alpha_1pct']['I']:6d}  "
           f"{res['sub_alpha_1pct']['M']:6d}  {res['sub_alpha_1pct']['F']:6d}  "
           f"{res['j_if']:7.4f}  {res['nmi_class_pos']:6.4f}")
        nl_j_ifs.append(res['j_if'])
        nl_nmis.append(res['nmi_class_pos'])
    pr()

    if nl_j_ifs:
        mean_j = np.mean(nl_j_ifs)
        std_j = np.std(nl_j_ifs)
        z_j = (vms_result['j_if'] - mean_j) / std_j if std_j > 0 else 0
        pr(f"  NL syllable-class J(I,F) mean: {mean_j:.4f} ± {std_j:.4f}")
        pr(f"  VMS J(I,F) z-score vs NL syllable-classes: {z_j:.2f}")
        pr()

        mean_nmi = np.mean(nl_nmis)
        std_nmi = np.std(nl_nmis)
        z_nmi = (vms_result['nmi_class_pos'] - mean_nmi) / std_nmi if std_nmi > 0 else 0
        pr(f"  NL syllable-class NMI mean: {mean_nmi:.4f} ± {std_nmi:.4f}")
        pr(f"  VMS NMI z-score vs NL syllable-classes: {z_nmi:.2f}")
        pr()

    # ── Step 9: Positional profile rank-correlation ──────────────────
    pr("=" * 72)
    pr("POSITIONAL FREQUENCY PROFILE — LANGUAGE TRIANGULATION")
    pr("=" * 72)
    pr()
    pr("Frequency distribution shape comparison")
    pr("(L1 distance between rank-frequency curves; lower = more similar):")
    pr()

    pr(f"  {'Language':>20s}  {'L1(I)':>7s}  {'L1(F)':>7s}  {'L1_mean':>8s}  "
       f"{'ΔH(I)':>7s}  {'ΔH(F)':>7s}  {'VMS_H(I)':>8s}  {'NL_H(I)':>8s}  "
       f"{'VMS_H(F)':>8s}  {'NL_H(F)':>8s}")
    pr(f"  {'─'*20}  {'─'*7}  {'─'*7}  {'─'*8}  {'─'*7}  {'─'*7}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}")

    best_match = ('', float('inf'))
    for name, (init_c, mid_c, final_c) in sorted(nl_letter_profiles.items()):
        res_i = frequency_shape_distance(vms_result['pos_counts'], init_c, 'I')
        res_f = frequency_shape_distance(vms_result['pos_counts'], final_c, 'F')
        if isinstance(res_i, float) or isinstance(res_f, float):
            continue
        l1_i, dh_i, vms_hi, nl_hi = res_i
        l1_f, dh_f, vms_hf, nl_hf = res_f
        l1_mean = (l1_i + l1_f) / 2
        pr(f"  {name:>20s}  {l1_i:7.4f}  {l1_f:7.4f}  {l1_mean:8.4f}  "
           f"{dh_i:7.4f}  {dh_f:7.4f}  {vms_hi:8.4f}  {nl_hi:8.4f}  "
           f"{vms_hf:8.4f}  {nl_hf:8.4f}")
        if l1_mean < best_match[1]:
            best_match = (name, l1_mean)
    pr()
    pr(f"  Best match: {best_match[0]} (L1_mean = {best_match[1]:.4f})")
    pr()

    # ── Step 10: Critical assessment ─────────────────────────────────
    pr("=" * 72)
    pr("CRITICAL ASSESSMENT")
    pr("=" * 72)
    pr()

    # Determine key findings
    vms_sub_i = vms_result['sub_alpha_1pct']['I']
    vms_sub_f = vms_result['sub_alpha_1pct']['F']
    vms_sub_m = vms_result['sub_alpha_1pct']['M']

    pr(f"Q1: Are sub-alphabet sizes equal across positions?")
    pr(f"    |A_I|={vms_sub_i}, |A_M|={vms_sub_m}, |A_F|={vms_sub_f}")
    if abs(vms_sub_i - vms_sub_f) <= 3:
        pr(f"    |A_I| ≈ |A_F|: YES (Δ={abs(vms_sub_i - vms_sub_f)})")
        pr(f"    → CONSISTENT with positional cipher (same plaintext alphabet at I and F)")
    else:
        pr(f"    |A_I| ≠ |A_F|: NO (Δ={abs(vms_sub_i - vms_sub_f)})")
        pr(f"    → INCONSISTENT with simple positional cipher")
    pr()

    pr(f"Q2: How much position restriction exceeds grammar?")
    pr(f"    Grammar-forced: {n_forced} classes")
    pr(f"    Excess locked/dominant: {len(excess)} classes")
    if len(excess) > 0:
        pr(f"    → {len(excess)} classes show position restriction BEYOND grammar")
        pr(f"    → This is evidence for cipher-like positional encoding")
    else:
        pr(f"    → ALL position restriction explained by grammar")
        pr(f"    → NO evidence for cipher-like positional encoding")
    pr()

    pr(f"Q3: Does F→I cross-word transition reset?")
    pr(f"    F→I MI = {fi_mi:.4f}")
    pr(f"    F→I z-score vs word-shuffle null: {fi_z:.2f}")
    if fi_z > 3:
        pr(f"    → F→I carries GENUINE cross-word dependency (z={fi_z:.1f})")
        pr(f"    → NOT a clean reset — word-to-word structure exists at class level")
    elif fi_z > 2:
        pr(f"    → F→I shows WEAK cross-word dependency (z={fi_z:.1f})")
    else:
        pr(f"    → F→I consistent with independence (z={fi_z:.1f})")
        pr(f"    → Word-boundary RESET confirmed at class level")
    pr()

    if nl_j_ifs:
        pr(f"Q4: Is VMS position restriction comparable to NL syllable classes?")
        pr(f"    VMS J(I,F) = {vms_result['j_if']:.4f}")
        pr(f"    NL syllable-class J(I,F) = {mean_j:.4f} ± {std_j:.4f}")
        pr(f"    z = {z_j:.2f}")
        if abs(z_j) < 2:
            pr(f"    → VMS position restriction is NORMAL for syllable-level units")
            pr(f"    → Position restriction is GRAMMATICAL, not cipher-like")
        elif z_j < -2:
            pr(f"    → VMS is MORE position-restricted than NL syllable-classes")
            pr(f"    → Excess restriction suggests cipher contribution")
        else:
            pr(f"    → VMS is LESS position-restricted than NL syllable-classes")
            pr(f"    → Anomalous in opposite direction")
        pr()

    pr(f"Q5: Which language best matches VMS positional profile?")
    pr(f"    Best: {best_match[0]} (L1 = {best_match[1]:.4f})")
    if best_match[1] < 0.3:
        pr(f"    → STRONG match — VMS freq. distribution shape resembles {best_match[0]}")
    elif best_match[1] < 0.6:
        pr(f"    → MODERATE match — some resemblance to {best_match[0]}")
    else:
        pr(f"    → WEAK match — no language profile closely matches VMS")
    pr()

    # ── Save results ─────────────────────────────────────────────────
    results = {
        'vms': {
            'n_words': vms_result['n_words'],
            'n_units': vms_result['n_units'],
            'n_classes': vms_result['n_classes'],
            'sub_alpha_1pct': vms_result['sub_alpha_1pct'],
            'sub_alpha_01pct': vms_result['sub_alpha_01pct'],
            'j_if': vms_result['j_if'],
            'j_im': vms_result['j_im'],
            'j_mf': vms_result['j_mf'],
            'mi_class_pos': vms_result['mi_class_pos'],
            'nmi_class_pos': vms_result['nmi_class_pos'],
            'class_types': {str(k): v for k, v in vms_result['class_types'].items()},
            'class_pci': {str(k): v for k, v in vms_result['class_pci'].items()},
        },
        'grammar_control': {
            'n_forced': n_forced,
            'n_leaning': n_leaning,
            'n_free': n_free,
            'excess_classes': [int(c) for c in excess],
        },
        'transitions': {},
        'fi_crossword': {
            'mi': fi_mi,
            'nmi': fi_nmi,
            'null_mean': float(fi_null_arr.mean()),
            'null_std': float(fi_null_arr.std()),
            'z_score': float(fi_z),
        },
        'null_model_j_if': {
            'observed': vms_result['j_if'],
            'null_mean': float(j_if_null.mean()),
            'null_std': float(j_if_null.std()),
            'z_score': float(j_if_z),
        },
        'nl_comparisons': {},
        'language_triangulation': {},
        'best_language_match': best_match[0],
    }

    for name, (bi, lc, rc) in transitions.items():
        mi, nmi, hx, hy = mi_from_bigram_counter(bi, lc, rc)
        results['transitions'][name] = {
            'n_pairs': sum(bi.values()),
            'mi': mi, 'nmi': nmi, 'h_left': hx, 'h_right': hy
        }

    for name, res in nl_results.items():
        results['nl_comparisons'][name] = {
            'j_if': res['j_if'],
            'nmi_class_pos': res['nmi_class_pos'],
            'sub_alpha_1pct': res['sub_alpha_1pct'],
        }

    for name, (init_c, mid_c, final_c) in nl_letter_profiles.items():
        res_i = frequency_shape_distance(vms_result['pos_counts'], init_c, 'I')
        res_f = frequency_shape_distance(vms_result['pos_counts'], final_c, 'F')
        if isinstance(res_i, float) or isinstance(res_f, float):
            continue
        l1_i, dh_i, vms_hi, nl_hi = res_i
        l1_f, dh_f, vms_hf, nl_hf = res_f
        results['language_triangulation'][name] = {
            'L1_I': l1_i, 'L1_F': l1_f, 'L1_mean': (l1_i + l1_f) / 2,
            'dH_I': dh_i, 'dH_F': dh_f,
        }

    out_json = RESULTS_DIR / 'phase103_positional_class_decomposition.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    pr(f"Results saved to {out_json}")

    out_txt = RESULTS_DIR / 'phase103_positional_class_decomposition.txt'
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"Log saved to {out_txt}")


if __name__ == '__main__':
    main()
