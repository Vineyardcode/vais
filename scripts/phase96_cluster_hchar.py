"""
Phase 96: Cluster-Level h_char Test + Source Language Matching

KEY QUESTION: Does collapsing VMS chunks to their distributional
clusters (Phase 86, k=25) normalize the h_char anomaly?

If YES → homophones explain the anomaly, and we can match against
source languages at the functional character level.
If NO → the anomaly is structural, not just variant selection.

CRITICAL NULL MODEL: random clustering should NOT produce the same
uplift. If it does, the result is a mathematical artifact.
"""

import os, re, glob, math, json
from collections import Counter, defaultdict
import random

FOLIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "folios")

# ============================================================
# 1. EVA PARSING (from Phase 85/86)
# ============================================================
TRIGRAPHS = {'cth', 'ckh', 'cph', 'cfh'}
DIGRAPHS = {'ch', 'sh', 'th', 'kh', 'ph', 'fh'}

def eva_to_glyphs(token):
    glyphs = []
    i = 0
    t = token.lower()
    while i < len(t):
        if i + 2 < len(t) and t[i:i+3] in TRIGRAPHS:
            glyphs.append(t[i:i+3])
            i += 3
        elif i + 1 < len(t) and t[i:i+2] in DIGRAPHS:
            glyphs.append(t[i:i+2])
            i += 2
        elif t[i].isalpha():
            glyphs.append(t[i])
            i += 1
        else:
            i += 1
    return glyphs

SLOT_RE = [
    re.compile(r'^(q|s|d|l|r|n)$'),
    re.compile(r'^(o|a|e|y)$'),
    re.compile(r'^(k|t|p|f|ckh|cth|cph|cfh)$'),
    re.compile(r'^(ch|sh|kh|th|ph|fh)$'),
    re.compile(r'^(o|a|e|y|i)$'),
    re.compile(r'^(i)$'),
    re.compile(r'^(i)$'),
    re.compile(r'^(r|l|n|m|s|d|y)$'),
]

def parse_one_chunk(glyphs):
    """Greedy left-to-right slot match."""
    slot = 0
    consumed = []
    for g in glyphs:
        matched = False
        for s in range(slot, len(SLOT_RE)):
            if SLOT_RE[s].match(g):
                consumed.append(g)
                slot = s + 1
                matched = True
                break
        if not matched:
            break
    return consumed

def parse_word_into_chunks(glyphs):
    """Parse a glyph sequence into chunks (Mauro's loop grammar)."""
    chunks = []
    pos = 0
    while pos < len(glyphs):
        c = parse_one_chunk(glyphs[pos:])
        if not c:
            chunks.append(('.'.join(glyphs[pos:pos+1]),))
            pos += 1
        else:
            chunks.append(('.'.join(c),))
            pos += len(c)
    return [c[0] for c in chunks]

# ============================================================
# 2. CLUSTER ASSIGNMENTS (Phase 86, k=25)
# ============================================================
CLUSTER_MAP = {}

cluster_data = {
    0: ['y','ch.e.d.y','ch.y','ch.e.y','d.y','ch.o.l','sh.e.d.y','ch.d.y','ch.o.r','sh.e.y','ch.e.e.y','ch.e.o.l','sh.y','sh.o.l','ch.o','q.o.l','sh.e.e.y','sh.o','ch.e.o','ch.o.d.y','sh.e.o.l','ch.a.r','sh.o.r','ch.e.o.r','ch.e.o.d.y','ch.a.l','sh.d.y','sh.e.e.d.y','ch.e.e.d.y','sh.e.o','ch.a.i.i.n','sh.e.o.d.y','ch.e.s','ch.o.s','sh.o.d.y','ch.e.o.s','ch.e.e.s','sh.e.o.r','sh.a.r','ch.l','ch.e.e.o','y.d.y','ch.a.m','q.o.r','sh.a.l','ch.o.y','ch.a.i.n','sh.e.s','ch.o.m','sh.a.i.i.n','sh.e.o.s','ch.e.e.o.r','sh.o.y','ch.e.e.o.d.y','m','q.o.d.y','sh.o.s'],
    1: ['q.o.k','o.k','o.t','q.o.t','y.k','y.t','cth','ch.o.k','ch.ckh','ckh','ch.e.k','ch.o.t','ch.k','ch.cth','cph','sh.e.k','sh.ckh','ch.e.t','ch.t','ch.e.ckh','q.o.ckh','sh.o.k','ch.e.o.k','o.cth','sh.e.ckh','sh.k','o.ckh','sh.cth','ch.e.e.k','ch.o.ckh','ch.e.p','ch.e.cth','cfh','ch.o.cth','sh.o.t','sh.e.e.k','q.o.cth','sh.e.t','ch.e.o.t','ch.cph','sh.e.o.k','sh.e.cth','sh.t','ch.e.f'],
    2: ['e.e.y','e.d.y','e.e.d.y','e.y','e.o.l','e.o.d.y','e.e.e.y','e.e.s','e.o','e.e.o.d.y','e.o.r','e.e.o.l','e.e.o','e.o.s','e.e.o.r','e.e.e.d.y','e.s','e.e.e.s','e.e.o.s'],
    3: ['a.i.i.n','a.r','a.l','a.i.n','a.m','a.i.r','a','a.i.i.i.n','a.i.i.r','a.n','a.s','a.i.m','a.y','a.i.l','a.d.y','a.i.s','i.i.n'],
    4: ['d','o.d','ch.e.d','ch.d','ch.o.d','sh.e.d','y.d','q.o.d','ch.e.o.d','sh.d','sh.o.d','sh.e.o.d','ch.e.e.d'],
    5: ['o.l','o.r','o','o.d.y','o.s','o.i.i.n','o.m','o.y','o.i.i.i.n','o.i.i.r','o.i.n'],
    6: ['o.p','q.o.p','o.f','y.p','q.o.f','ch.p','ch.o.p','y.f'],
    7: ['e','e.d','e.e.d','e.e','e.o.d','e.e.o.d'],
    8: ['ch.e','sh.e','ch.e.e','sh.e.e'],
    9: ['k','t','p','f'],
    10: ['s','l','r','d.l'],
    11: ['e.k','e.t','e.p'],
    12: ['ch','sh'],
    13: ['q.o','q'],
    14: ['a.i.i','a.i'],
    15: ['ch.s'],
    16: ['y.s'],
    17: ['e.e.e'],
    18: ['a.k'],
    19: ['a.d'],
    20: ['e.e.e.d'],
    21: ['d.k'],
    22: ['y.y'],
    23: ['q.k'],
    24: ['y.o.k'],
}

for cid, members in cluster_data.items():
    for m in members:
        CLUSTER_MAP[m] = cid

# ============================================================
# 3. PARSE VMS INTO CHUNK SEQUENCES AND CLUSTER SEQUENCES
# ============================================================
def parse_folio_dir(folio_dir, folio_filter=None):
    """Parse folios into (words, chunk_sequences, cluster_sequences).
    folio_filter: if provided, only include folios matching this function.
    """
    all_words = []
    all_chunk_seqs = []  # each word -> list of chunk strings
    all_cluster_seqs = []  # each word -> list of cluster IDs
    unmapped_chunks = Counter()
    
    for fpath in sorted(glob.glob(os.path.join(folio_dir, "f*.txt"))):
        fname = os.path.basename(fpath)
        # Extract folio number
        m_fnum = re.match(r'f(\d+)', fname)
        if not m_fnum:
            continue
        fnum = int(m_fnum.group(1))
        
        if folio_filter and not folio_filter(fnum):
            continue
        
        with open(fpath, 'r', encoding='utf-8') as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                m = re.match(r'<[^>]+>\s*(.*)', line)
                if not m:
                    continue
                content = m.group(1)
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'\[[^\]]*\]', '', content)
                tokens = re.split(r'[.\s,;]+', content)
                tokens = [t.strip() for t in tokens if t.strip()
                          and not t.startswith('!') and not t.startswith('%')
                          and t != '?' and len(t) > 0]
                
                for tok in tokens:
                    glyphs = eva_to_glyphs(tok)
                    if not glyphs:
                        continue
                    chunks = parse_word_into_chunks(glyphs)
                    clusters = []
                    for c in chunks:
                        if c in CLUSTER_MAP:
                            clusters.append(CLUSTER_MAP[c])
                        else:
                            unmapped_chunks[c] += 1
                            clusters.append(-1)  # unmapped
                    
                    all_words.append(tok)
                    all_chunk_seqs.append(chunks)
                    all_cluster_seqs.append(clusters)
    
    return all_words, all_chunk_seqs, all_cluster_seqs, unmapped_chunks

# Parse all VMS
words_all, chunks_all, clusters_all, unmapped = parse_folio_dir(FOLIO_DIR)
# Parse Currier A (folios 1-57)
words_a, chunks_a, clusters_a, _ = parse_folio_dir(FOLIO_DIR, lambda f: f <= 57)
# Parse Currier B (folios 75-116)
words_b, chunks_b, clusters_b, _ = parse_folio_dir(FOLIO_DIR, lambda f: f >= 75)

print("=" * 70)
print("PHASE 96: CLUSTER-LEVEL h_char + LANGUAGE MATCHING")
print("=" * 70)
print(f"\nVMS ALL: {len(words_all)} words, {sum(len(c) for c in chunks_all)} chunks, {sum(len(c) for c in clusters_all)} cluster tokens")
print(f"Currier A: {len(words_a)} words")
print(f"Currier B: {len(words_b)} words")
print(f"Unmapped chunk types: {len(unmapped)} ({sum(unmapped.values())} tokens)")
print(f"Top unmapped: {unmapped.most_common(10)}")

# ============================================================
# 4. COMPUTE h_char AT DIFFERENT LEVELS
# ============================================================
def compute_hchar(sequence):
    """Compute h_char ratio from a flat sequence of symbols."""
    if len(sequence) < 2:
        return None, None, None
    
    # Unigram entropy
    counts = Counter(sequence)
    total = len(sequence)
    h1 = -sum((c/total) * math.log2(c/total) for c in counts.values())
    
    # Bigram conditional entropy H(X_i | X_{i-1})
    bigram_counts = Counter()
    context_counts = Counter()
    for i in range(1, len(sequence)):
        bigram_counts[(sequence[i-1], sequence[i])] += 1
        context_counts[sequence[i-1]] += 1
    
    h2 = 0
    for (prev, curr), count in bigram_counts.items():
        p_bigram = count / (total - 1)
        p_cond = count / context_counts[prev]
        h2 -= p_bigram * math.log2(p_cond)
    
    ratio = h2 / h1 if h1 > 0 else 0
    return h1, h2, ratio

def flatten_sequences(word_seqs):
    """Flatten list of word-sequences into a single sequence."""
    flat = []
    for seq in word_seqs:
        flat.extend(seq)
    return flat

# Glyph-level h_char (baseline)
glyph_seqs_all = [eva_to_glyphs(w) for w in words_all]
flat_glyphs = flatten_sequences(glyph_seqs_all)
h1_g, h2_g, hchar_glyph = compute_hchar(flat_glyphs)

# Chunk-level h_char
flat_chunks = flatten_sequences(chunks_all)
h1_c, h2_c, hchar_chunk = compute_hchar(flat_chunks)

# Cluster-level h_char (THE KEY TEST)
flat_clusters = flatten_sequences(clusters_all)
# Remove unmapped (-1)
flat_clusters_clean = [c for c in flat_clusters if c >= 0]
h1_cl, h2_cl, hchar_cluster = compute_hchar(flat_clusters_clean)

print(f"\n--- h_char at different levels (VMS ALL) ---")
print(f"  Glyph level:   H1={h1_g:.4f}  H2={h2_g:.4f}  h_char={hchar_glyph:.4f}")
print(f"  Chunk level:   H1={h1_c:.4f}  H2={h2_c:.4f}  h_char={hchar_chunk:.4f}")
print(f"  Cluster level: H1={h1_cl:.4f}  H2={h2_cl:.4f}  h_char={hchar_cluster:.4f}")
print(f"  NL char range: 0.82 - 0.90")

# Currier A and B separately
flat_cl_a = [c for seq in clusters_a for c in seq if c >= 0]
flat_cl_b = [c for seq in clusters_b for c in seq if c >= 0]
_, _, hchar_cl_a = compute_hchar(flat_cl_a)
_, _, hchar_cl_b = compute_hchar(flat_cl_b)
print(f"\n  Cluster level A: h_char={hchar_cl_a:.4f}")
print(f"  Cluster level B: h_char={hchar_cl_b:.4f}")

# ============================================================
# 5. NULL MODEL: RANDOM CLUSTERING
# ============================================================
print(f"\n--- NULL MODEL: random cluster assignment ---")
all_chunk_types = list(set(flat_chunks))
n_random = 50
random_hchars = []
random.seed(42)

for trial in range(n_random):
    # Randomly assign chunk types to 25 clusters
    random_map = {c: random.randint(0, 24) for c in all_chunk_types}
    random_flat = [random_map[c] for c in flat_chunks]
    _, _, rh = compute_hchar(random_flat)
    random_hchars.append(rh)

mean_rh = sum(random_hchars) / len(random_hchars)
std_rh = (sum((x - mean_rh)**2 for x in random_hchars) / len(random_hchars)) ** 0.5
z_score = (hchar_cluster - mean_rh) / std_rh if std_rh > 0 else 0

print(f"  Random cluster h_char: mean={mean_rh:.4f} ± {std_rh:.4f}")
print(f"  Distributional cluster h_char: {hchar_cluster:.4f}")
print(f"  z-score vs random: {z_score:+.2f}")
print(f"  → {'BETTER than random' if hchar_cluster > mean_rh + 2*std_rh else 'NOT significantly better than random' if hchar_cluster > mean_rh else 'WORSE than random'}")

# ============================================================
# 6. CLUSTER-LEVEL FINGERPRINT
# ============================================================
def compute_fingerprint(words, cluster_seqs, label):
    """Compute 6D fingerprint at cluster level."""
    flat = [c for seq in cluster_seqs for c in seq if c >= 0]
    
    # h_char
    _, _, hchar = compute_hchar(flat)
    
    # Word-level stats (cluster words)
    cluster_words = ['_'.join(str(c) for c in seq if c >= 0) for seq in cluster_seqs]
    word_counts = Counter(cluster_words)
    types = len(word_counts)
    tokens = len(cluster_words)
    
    # TTR
    ttr = types / tokens if tokens > 0 else 0
    
    # hapax
    hapax = sum(1 for c in word_counts.values() if c == 1)
    hapax_ratio = hapax / types if types > 0 else 0
    
    # mean word length (in clusters)
    wlen = sum(len(seq) for seq in cluster_seqs) / len(cluster_seqs) if cluster_seqs else 0
    
    # Heaps (simple: slope of log-log types vs tokens)
    seen = set()
    n_points = min(tokens, 20)
    step = max(1, tokens // n_points)
    log_tok = []
    log_typ = []
    for i, w in enumerate(cluster_words):
        seen.add(w)
        if (i + 1) % step == 0 or i == tokens - 1:
            if i + 1 > 1:
                log_tok.append(math.log(i + 1))
                log_typ.append(math.log(len(seen)))
    
    if len(log_tok) > 1:
        n = len(log_tok)
        sx = sum(log_tok)
        sy = sum(log_typ)
        sxy = sum(x*y for x, y in zip(log_tok, log_typ))
        sxx = sum(x*x for x in log_tok)
        heaps = (n * sxy - sx * sy) / (n * sxx - sx * sx) if (n * sxx - sx * sx) != 0 else 0
    else:
        heaps = 0
    
    # Zipf
    freqs = sorted(word_counts.values(), reverse=True)
    log_rank = [math.log(i+1) for i in range(len(freqs))]
    log_freq = [math.log(f) for f in freqs]
    if len(log_rank) > 1:
        n = len(log_rank)
        sx = sum(log_rank)
        sy = sum(log_freq)
        sxy = sum(x*y for x, y in zip(log_rank, log_freq))
        sxx = sum(x*x for x in log_rank)
        zipf = -((n * sxy - sx * sy) / (n * sxx - sx * sx)) if (n * sxx - sx * sx) != 0 else 0
    else:
        zipf = 0
    
    return {
        'label': label,
        'h_char': hchar,
        'heaps': heaps,
        'hapax': hapax_ratio,
        'wlen': wlen,
        'zipf': zipf,
        'ttr': ttr,
        'types': types,
        'tokens': tokens,
    }

vms_fp = compute_fingerprint(words_all, clusters_all, 'VMS_ALL_cluster')
vms_a_fp = compute_fingerprint(words_a, clusters_a, 'VMS_A_cluster')
vms_b_fp = compute_fingerprint(words_b, clusters_b, 'VMS_B_cluster')

print(f"\n--- Cluster-level fingerprints ---")
print(f"{'Label':<20} {'h_char':<8} {'Heaps':<8} {'hapax':<8} {'wlen':<8} {'Zipf':<8} {'TTR':<8} {'Types':<8} {'Tokens':<8}")
for fp in [vms_fp, vms_a_fp, vms_b_fp]:
    print(f"{fp['label']:<20} {fp['h_char']:<8.4f} {fp['heaps']:<8.4f} {fp['hapax']:<8.4f} {fp['wlen']:<8.2f} {fp['zipf']:<8.4f} {fp['ttr']:<8.4f} {fp['types']:<8} {fp['tokens']:<8}")

# ============================================================
# 7. SOURCE LANGUAGE COMPARISON
# ============================================================
def compute_nl_fingerprint(filepath, label):
    """Compute character-level fingerprint for a NL text."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read().lower()
    
    # Extract words (alpha only)
    words = re.findall(r'[a-záàâãäåæçèéêëìíîïñòóôõöùúûüýþ]+', text)
    if len(words) < 100:
        return None
    
    # Character sequence (within words, no spaces)
    chars = list(''.join(words))
    _, _, hchar = compute_hchar(chars)
    
    # Word stats
    word_counts = Counter(words)
    types = len(word_counts)
    tokens = len(words)
    ttr = types / tokens if tokens > 0 else 0
    hapax = sum(1 for c in word_counts.values() if c == 1)
    hapax_ratio = hapax / types if types > 0 else 0
    wlen = sum(len(w) for w in words) / len(words)
    
    # Heaps
    seen = set()
    n_points = min(tokens, 20)
    step = max(1, tokens // n_points)
    log_tok = []
    log_typ = []
    for i, w in enumerate(words):
        seen.add(w)
        if (i + 1) % step == 0 or i == tokens - 1:
            if i + 1 > 1:
                log_tok.append(math.log(i + 1))
                log_typ.append(math.log(len(seen)))
    
    if len(log_tok) > 1:
        n = len(log_tok)
        sx = sum(log_tok)
        sy = sum(log_typ)
        sxy = sum(x*y for x, y in zip(log_tok, log_typ))
        sxx = sum(x*x for x in log_tok)
        heaps = (n * sxy - sx * sy) / (n * sxx - sx * sx) if (n * sxx - sx * sx) != 0 else 0
    else:
        heaps = 0
    
    # Zipf
    freqs = sorted(word_counts.values(), reverse=True)
    log_rank = [math.log(i+1) for i in range(len(freqs))]
    log_freq = [math.log(f) for f in freqs]
    if len(log_rank) > 1:
        n = len(log_rank)
        sx = sum(log_rank)
        sy = sum(log_freq)
        sxy = sum(x*y for x, y in zip(log_rank, log_freq))
        sxx = sum(x*x for x in log_rank)
        zipf = -((n * sxy - sx * sy) / (n * sxx - sx * sx)) if (n * sxx - sx * sx) != 0 else 0
    else:
        zipf = 0
    
    return {
        'label': label,
        'h_char': hchar,
        'heaps': heaps,
        'hapax': hapax_ratio,
        'wlen': wlen,
        'zipf': zipf,
        'ttr': ttr,
        'types': types,
        'tokens': tokens,
    }

# Gather all source language files
source_files = []
latin_dir = r"c:\projects\voynich_slop\data\latin_texts"
vern_dir = r"c:\projects\voynich_slop\data\vernacular_texts"
czech_dir = r"c:\projects\voynich_slop\data\czech_bible_kralice"

for f in glob.glob(os.path.join(latin_dir, "*.txt")):
    source_files.append((f, "Latin:" + os.path.basename(f).replace('.txt','')))
for f in glob.glob(os.path.join(vern_dir, "*.txt")):
    source_files.append((f, os.path.basename(f).replace('.txt','').replace('_',' ')))

# Czech: concatenate a sample
czech_files = sorted(glob.glob(os.path.join(czech_dir, "*.txt")))
if czech_files:
    czech_text = ""
    for cf in czech_files[:50]:  # first 50 chapters
        try:
            with open(cf, 'r', encoding='utf-8', errors='ignore') as fh:
                czech_text += fh.read() + " "
        except:
            pass
    if len(czech_text) > 1000:
        czech_tmpfile = r"c:\projects\voynich_slop\data\czech_bible_kralice\czech_sample.tmp"
        with open(czech_tmpfile, 'w', encoding='utf-8') as fh:
            fh.write(czech_text)
        source_files.append((czech_tmpfile, "Czech:bible_kralice"))

# Compute NL fingerprints
nl_fps = []
for fpath, label in source_files:
    fp = compute_nl_fingerprint(fpath, label)
    if fp:
        nl_fps.append(fp)

print(f"\n--- Source language fingerprints (character level) ---")
print(f"{'Label':<30} {'h_char':<8} {'Heaps':<8} {'hapax':<8} {'wlen':<8} {'Zipf':<8} {'TTR':<8}")
for fp in sorted(nl_fps, key=lambda x: x['label']):
    print(f"{fp['label']:<30} {fp['h_char']:<8.4f} {fp['heaps']:<8.4f} {fp['hapax']:<8.4f} {fp['wlen']:<8.2f} {fp['zipf']:<8.4f} {fp['ttr']:<8.4f}")

# ============================================================
# 8. DISTANCE CALCULATION
# ============================================================
def distance_6d(fp1, fp2):
    """6D normalized Euclidean distance."""
    keys = ['h_char', 'heaps', 'hapax', 'wlen', 'zipf', 'ttr']
    d2 = 0
    for k in keys:
        if fp2[k] != 0:
            d2 += ((fp1[k] - fp2[k]) / fp2[k]) ** 2
    return math.sqrt(d2)

print(f"\n--- Distance: VMS cluster-level vs NL character-level ---")
print(f"{'NL corpus':<30} {'dist_ALL':<12} {'dist_A':<12} {'dist_B':<12}")
results = []
for nl_fp in sorted(nl_fps, key=lambda x: x['label']):
    d_all = distance_6d(vms_fp, nl_fp)
    d_a = distance_6d(vms_a_fp, nl_fp)
    d_b = distance_6d(vms_b_fp, nl_fp)
    print(f"{nl_fp['label']:<30} {d_all:<12.4f} {d_a:<12.4f} {d_b:<12.4f}")
    results.append((nl_fp['label'], d_all, d_a, d_b))

# Best matches
print(f"\n--- Best matches ---")
print(f"  VMS ALL best:  {min(results, key=lambda x: x[1])}")
print(f"  VMS A best:    {min(results, key=lambda x: x[2])}")
print(f"  VMS B best:    {min(results, key=lambda x: x[3])}")

# ============================================================
# 9. COMPARE WITH GLYPH-LEVEL DISTANCES (for reference)
# ============================================================
VMS_GLYPH_TARGET = {'h_char': 0.653, 'heaps': 0.7506, 'hapax': 0.7188, 'wlen': 5.053, 'zipf': 0.9237, 'ttr': 0.377}
VMS_A_GLYPH = {'h_char': 0.6758, 'heaps': 0.7682, 'hapax': 0.7363, 'wlen': 4.898, 'zipf': 0.9191, 'ttr': 0.377}
VMS_B_GLYPH = {'h_char': 0.6208, 'heaps': 0.7698, 'hapax': 0.4954, 'wlen': 5.115, 'zipf': 0.9662, 'ttr': 0.252}

print(f"\n--- Comparison: cluster-level vs glyph-level distances ---")
print(f"{'NL corpus':<30} {'cluster_A':<12} {'glyph_A':<12} {'cluster_B':<12} {'glyph_B':<12}")
for nl_fp in sorted(nl_fps, key=lambda x: x['label']):
    d_cl_a = distance_6d(vms_a_fp, nl_fp)
    d_gl_a = distance_6d(VMS_A_GLYPH, nl_fp)
    d_cl_b = distance_6d(vms_b_fp, nl_fp)
    d_gl_b = distance_6d(VMS_B_GLYPH, nl_fp)
    print(f"{nl_fp['label']:<30} {d_cl_a:<12.4f} {d_gl_a:<12.4f} {d_cl_b:<12.4f} {d_gl_b:<12.4f}")

# Clean temp file
try:
    os.remove(r"c:\projects\voynich_slop\data\czech_bible_kralice\czech_sample.tmp")
except:
    pass

print(f"\n{'='*70}")
print("PHASE 96 COMPLETE")
print(f"{'='*70}")
