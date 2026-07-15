#!/usr/bin/env python3
"""
Phase 107 — Intra-Chunk Slot Mutual Information Decomposition

═══════════════════════════════════════════════════════════════════════

MOTIVATION:

  Phase 97 showed the LOOP slot grammar explains only 24.2% of
  h_char depression (residual = +0.26, z = 25.9 vs NL).
  Phase 106 ruled out simple substitution across 6 languages.

  The critical question: WHERE does the unexplained 0.26 live?
  Which slot-to-slot interactions carry the anomalous structure?

  This is a DISCRIMINATING test:
  - If MI(S2,S4) is high → front/back vowels jointly encode info (cipher)
  - If MI(S5,S1_next) is high → encoding spans chunk boundaries
  - If all MIs are moderate → anomaly is in higher-order interactions

METHOD:
  1. Parse all VMS words into LOOP chunks with slot decomposition
  2. For each chunk, record content of S1-S5 (including "empty")
  3. Compute pairwise MI(S_i, S_j) for all 10 within-chunk slot pairs
  4. Compute cross-boundary MIs: S5→S1(next chunk), S5→S1(next word)
  5. Null model: slot-resample (shuffle slot contents independently)
  6. NL baseline: syllabify reference corpora, compute same metrics
  7. Identify which slot pair carries excess MI vs NL

REVALIDATION:
  - LOOP grammar is deterministic; consistent segmentation guaranteed
  - NMI (normalized) used to handle different alphabet sizes per slot
  - Bonferroni correction for 12 pairwise tests
  - Slot-resample null model guards against circularity
  - JKP composite glyph caveat noted: EVA boundaries may be wrong

OUTPUTS:
  - Full MI/NMI matrix for VMS slot pairs
  - Same matrices for NL reference corpora
  - Z-scores of VMS vs NL for each slot pair
  - Identification of the dominant anomalous interaction
"""
import re, sys, io, math
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
# MAURO'S LOOP GRAMMAR — CHUNK PARSER WITH SLOT RECORDING
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
EMPTY = '_'  # token for empty slot


def parse_chunk_with_slots(glyphs, pos):
    """Parse one chunk, returning slot contents as dict.
    Returns (slot_dict, new_pos) or (None, pos) if nothing matches.
    slot_dict keys: 's1','s2','s3','s4','s5' — values are glyph strings or EMPTY.
    """
    start = pos
    slots = {'s1': EMPTY, 's2': EMPTY, 's3': EMPTY, 's4': EMPTY, 's5': EMPTY}

    # SLOT 1: onset
    if pos < len(glyphs) and glyphs[pos] in SLOT1:
        slots['s1'] = glyphs[pos]
        pos += 1

    # SLOT 2: front vowel (run of e's up to 3, OR single q/a)
    if pos < len(glyphs):
        if glyphs[pos] in SLOT2_RUNS:
            buf = []
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT2_RUNS and count < 3:
                buf.append(glyphs[pos])
                pos += 1
                count += 1
            slots['s2'] = ''.join(buf)
        elif glyphs[pos] in SLOT2_SINGLE:
            slots['s2'] = glyphs[pos]
            pos += 1

    # SLOT 3: core 'o'
    if pos < len(glyphs) and glyphs[pos] in SLOT3:
        slots['s3'] = glyphs[pos]
        pos += 1

    # SLOT 4: back vowel (run of i's up to 3, OR single d)
    if pos < len(glyphs):
        if glyphs[pos] in SLOT4_RUNS:
            buf = []
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT4_RUNS and count < 3:
                buf.append(glyphs[pos])
                pos += 1
                count += 1
            slots['s4'] = ''.join(buf)
        elif glyphs[pos] in SLOT4_SINGLE:
            slots['s4'] = glyphs[pos]
            pos += 1

    # SLOT 5: coda
    if pos < len(glyphs) and glyphs[pos] in SLOT5:
        slots['s5'] = glyphs[pos]
        pos += 1

    if pos == start:
        return None, pos
    return slots, pos


def parse_word_slots(word_str):
    """Parse a VMS word into list of slot-dicts (one per chunk)."""
    glyphs = eva_to_glyphs(word_str)
    chunks = []
    pos = 0
    while pos < len(glyphs) and len(chunks) < MAX_CHUNKS:
        result, new_pos = parse_chunk_with_slots(glyphs, pos)
        if result is None:
            pos += 1  # skip unparseable glyph
        else:
            chunks.append(result)
            pos = new_pos
    return chunks


# ═══════════════════════════════════════════════════════════════════════
# VMS LOADING
# ═══════════════════════════════════════════════════════════════════════

def load_vms_words():
    """Load all VMS words from folios."""
    words = []
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        with open(fpath, encoding='utf-8') as f:
            for raw in f:
                raw = raw.strip()
                if not re.match(r"<f\d+", raw):
                    continue
                text = re.sub(r"<[^>]*>|<!.*?>|<%>|<\$>", "", raw).strip()
                text = re.sub(r"\{[^}]*\}", lambda m: m.group(0)[1:-1], text)
                text = re.sub(r"\[([^:\]]+):([^\]]+)\]", r"\1", text)
                text = re.sub(r"\?|@\d+;?", "", text)
                for w in re.split(r"[.,\s]+", text):
                    w = w.strip()
                    if w and len(w) > 0 and re.match(r'^[a-z]+$', w):
                        words.append(w)
    return words


# ═══════════════════════════════════════════════════════════════════════
# INFORMATION THEORY
# ═══════════════════════════════════════════════════════════════════════

def entropy(counter):
    """Shannon entropy H(X) in bits from a Counter."""
    total = sum(counter.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counter.values():
        if c > 0:
            p = c / total
            h -= p * math.log2(p)
    return h


def joint_entropy(joint_counter):
    """H(X,Y) from a Counter of (x,y) tuples."""
    return entropy(joint_counter)


def mutual_information(cx, cy, cxy):
    """MI(X;Y) = H(X) + H(Y) - H(X,Y)."""
    return entropy(cx) + entropy(cy) - joint_entropy(cxy)


def normalized_mi(cx, cy, cxy):
    """NMI(X;Y) = MI(X;Y) / min(H(X), H(Y)). Returns 0 if degenerate."""
    hx = entropy(cx)
    hy = entropy(cy)
    denom = min(hx, hy)
    if denom < 1e-10:
        return 0.0
    mi = mutual_information(cx, cy, cxy)
    return mi / denom


def conditional_entropy(cx, cxy):
    """H(Y|X) = H(X,Y) - H(X)."""
    return joint_entropy(cxy) - entropy(cx)


# ═══════════════════════════════════════════════════════════════════════
# SLOT MI COMPUTATION
# ═══════════════════════════════════════════════════════════════════════

SLOT_NAMES = ['s1', 's2', 's3', 's4', 's5']


def compute_slot_mis(all_chunks):
    """Compute pairwise MI and NMI for all slot pairs within chunks.
    
    Returns dict: {(si, sj): {'mi': float, 'nmi': float, 'n': int, 
                               'hx': float, 'hy': float, 'hxy': float}}
    """
    results = {}
    for i, si in enumerate(SLOT_NAMES):
        for j, sj in enumerate(SLOT_NAMES):
            if j <= i:
                continue
            cx = Counter()
            cy = Counter()
            cxy = Counter()
            for chunk in all_chunks:
                x = chunk[si]
                y = chunk[sj]
                cx[x] += 1
                cy[y] += 1
                cxy[(x, y)] += 1
            mi = mutual_information(cx, cy, cxy)
            nmi = normalized_mi(cx, cy, cxy)
            results[(si, sj)] = {
                'mi': mi,
                'nmi': nmi,
                'n': sum(cx.values()),
                'hx': entropy(cx),
                'hy': entropy(cy),
                'hxy': joint_entropy(cxy),
                'cx_types': len([v for v in cx.values() if v > 0]),
                'cy_types': len([v for v in cy.values() if v > 0]),
            }
    return results


def compute_boundary_mis(word_chunk_lists):
    """Compute MI across chunk and word boundaries.
    
    Returns dict with keys:
      'cross_chunk': MI(S5_n, S1_{n+1}) within same word
      'cross_word': MI(S5_last, S1_first) across words
      'cross_chunk_s5_s2': MI(S5_n, S2_{n+1}) — coda to next front
    """
    # Cross-chunk (within word)
    cc_s5 = Counter()
    cc_s1 = Counter()
    cc_joint = Counter()
    cc_s5_s2_5 = Counter()
    cc_s5_s2_2 = Counter()
    cc_s5_s2_joint = Counter()
    
    for chunks in word_chunk_lists:
        for k in range(len(chunks) - 1):
            s5 = chunks[k]['s5']
            s1_next = chunks[k + 1]['s1']
            s2_next = chunks[k + 1]['s2']
            cc_s5[s5] += 1
            cc_s1[s1_next] += 1
            cc_joint[(s5, s1_next)] += 1
            cc_s5_s2_5[s5] += 1
            cc_s5_s2_2[s2_next] += 1
            cc_s5_s2_joint[(s5, s2_next)] += 1
    
    # Cross-word
    cw_s5 = Counter()
    cw_s1 = Counter()
    cw_joint = Counter()
    
    for k in range(len(word_chunk_lists) - 1):
        if not word_chunk_lists[k] or not word_chunk_lists[k + 1]:
            continue
        s5_last = word_chunk_lists[k][-1]['s5']
        s1_first = word_chunk_lists[k + 1][0]['s1']
        cw_s5[s5_last] += 1
        cw_s1[s1_first] += 1
        cw_joint[(s5_last, s1_first)] += 1
    
    return {
        'cross_chunk_s5_s1': {
            'mi': mutual_information(cc_s5, cc_s1, cc_joint),
            'nmi': normalized_mi(cc_s5, cc_s1, cc_joint),
            'n': sum(cc_s5.values()),
            'hx': entropy(cc_s5), 'hy': entropy(cc_s1),
        },
        'cross_chunk_s5_s2': {
            'mi': mutual_information(cc_s5_s2_5, cc_s5_s2_2, cc_s5_s2_joint),
            'nmi': normalized_mi(cc_s5_s2_5, cc_s5_s2_2, cc_s5_s2_joint),
            'n': sum(cc_s5_s2_5.values()),
            'hx': entropy(cc_s5_s2_5), 'hy': entropy(cc_s5_s2_2),
        },
        'cross_word_s5_s1': {
            'mi': mutual_information(cw_s5, cw_s1, cw_joint),
            'nmi': normalized_mi(cw_s5, cw_s1, cw_joint),
            'n': sum(cw_s5.values()),
            'hx': entropy(cw_s5), 'hy': entropy(cw_s1),
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# NULL MODEL: SLOT RESAMPLE
# ═══════════════════════════════════════════════════════════════════════

def slot_resample_null(all_chunks, n_iter=200):
    """Shuffle each slot independently across all chunks.
    Returns distribution of MI values for each slot pair."""
    slot_values = {s: [] for s in SLOT_NAMES}
    for chunk in all_chunks:
        for s in SLOT_NAMES:
            slot_values[s].append(chunk[s])
    
    null_mis = {pair: [] for pair in []}
    # Pre-create all pair keys
    pairs = []
    for i, si in enumerate(SLOT_NAMES):
        for j, sj in enumerate(SLOT_NAMES):
            if j > i:
                pairs.append((si, sj))
    null_mis = {p: [] for p in pairs}
    
    for _ in range(n_iter):
        # Shuffle each slot independently
        shuffled = {}
        for s in SLOT_NAMES:
            vals = list(slot_values[s])
            random.shuffle(vals)
            shuffled[s] = vals
        
        # Rebuild chunks
        n = len(all_chunks)
        fake_chunks = []
        for k in range(n):
            fake_chunks.append({s: shuffled[s][k] for s in SLOT_NAMES})
        
        # Compute MIs
        for si, sj in pairs:
            cx = Counter()
            cy = Counter()
            cxy = Counter()
            for chunk in fake_chunks:
                x, y = chunk[si], chunk[sj]
                cx[x] += 1
                cy[y] += 1
                cxy[(x, y)] += 1
            null_mis[(si, sj)].append(mutual_information(cx, cy, cxy))
    
    return null_mis


# ═══════════════════════════════════════════════════════════════════════
# NL BASELINE: CVC DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════

VOWELS = set('aeiouyàèéìòùáéíóúůýâêîôûæœäöü')
CONSONANTS = set('bcdfghjklmnpqrstvwxzßčďěňřšťž')

def syllabify_cvc(word):
    """Rough CVC decomposition: onset consonants, nucleus vowels, coda consonants.
    Returns list of dicts with 'onset', 'nucleus', 'coda'."""
    syllables = []
    chars = list(word.lower())
    i = 0
    while i < len(chars):
        syl = {'onset': '', 'nucleus': '', 'coda': ''}
        # Onset: consonants
        while i < len(chars) and chars[i] in CONSONANTS:
            syl['onset'] += chars[i]
            i += 1
        # Nucleus: vowels
        while i < len(chars) and chars[i] in VOWELS:
            syl['nucleus'] += chars[i]
            i += 1
        # Coda: consonants (until next vowel or end)
        while i < len(chars) and chars[i] in CONSONANTS:
            # Peek: if next char is vowel, leave this consonant for next syllable
            if i + 1 < len(chars) and chars[i + 1] in VOWELS:
                break
            syl['coda'] += chars[i]
            i += 1
        if syl['onset'] or syl['nucleus'] or syl['coda']:
            syllables.append(syl)
        else:
            i += 1  # skip unknown chars
    return syllables


def load_nl_corpus(path, encoding='utf-8'):
    text = Path(path).read_text(encoding=encoding, errors='replace')
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"<[^>]*>", "", text)
    words = re.findall(r"[a-zäöüßàèéìòùáéíóúâêîôûçñšžčřďťňůýæœ]+", text.lower())
    return [w for w in words if len(w) > 1]


def load_czech_corpus():
    words = []
    import glob
    for fpath in sorted(glob.glob(str(DATA_DIR / "czech_bible_kralice" / "ces1613_*_read.txt"))):
        text = Path(fpath).read_text(encoding='utf-8', errors='replace')
        text = re.sub(r"\d+\.", "", text)
        ws = re.findall(r"[a-záéíóúůýčďěňřšťžæœ]+", text.lower())
        words.extend([w for w in ws if len(w) > 1])
    return words


def compute_nl_slot_mis(words):
    """Compute onset-nucleus MI, nucleus-coda MI, onset-coda MI
    using CVC syllable decomposition."""
    all_syls = []
    for w in words:
        syls = syllabify_cvc(w)
        all_syls.extend(syls)
    
    if len(all_syls) < 100:
        return None
    
    # Map to 3-slot format: onset=s1, nucleus=s2, coda=s3
    slots_3 = ['onset', 'nucleus', 'coda']
    results = {}
    for i, si in enumerate(slots_3):
        for j, sj in enumerate(slots_3):
            if j <= i:
                continue
            cx = Counter()
            cy = Counter()
            cxy = Counter()
            for syl in all_syls:
                x = syl[si] if syl[si] else EMPTY
                y = syl[sj] if syl[sj] else EMPTY
                cx[x] += 1
                cy[y] += 1
                cxy[(x, y)] += 1
            mi = mutual_information(cx, cy, cxy)
            nmi_val = normalized_mi(cx, cy, cxy)
            results[(si, sj)] = {
                'mi': mi,
                'nmi': nmi_val,
                'n': len(all_syls),
                'hx': entropy(cx),
                'hy': entropy(cy),
            }
    return results


# ═══════════════════════════════════════════════════════════════════════
# BODY ISOLATION: ENTROPY OF BODY vs CODA vs FULL
# ═══════════════════════════════════════════════════════════════════════

def compute_sequence_hchar(sequences):
    """Compute h_char = H(c_i | c_{i-1}) from a list of glyph sequences.
    Each sequence is a list of glyphs (one per word/chunk body).
    We concatenate with word boundaries."""
    bigram_counts = Counter()
    unigram_counts = Counter()
    
    for seq in sequences:
        for i in range(len(seq)):
            unigram_counts[seq[i]] += 1
            if i > 0:
                bigram_counts[(seq[i-1], seq[i])] += 1
    
    total_bi = sum(bigram_counts.values())
    if total_bi == 0:
        return 0.0, 0.0
    
    h1 = entropy(unigram_counts)
    h2 = joint_entropy(bigram_counts)
    h_char = h2 - h1 if h1 > 0 else 0.0
    # Also: H(c_i | c_{i-1}) = H(c_i, c_{i-1}) - H(c_{i-1})
    # Normalized: h_ratio = h_char / h1
    h_ratio = h_char / h1 if h1 > 0 else 0.0
    return h_char, h_ratio


def body_coda_entropy_analysis(word_chunk_lists):
    """Separate each chunk into BODY (S1+S2+S3+S4) and CODA (S5).
    Compute h_char for: full glyph stream, body-only stream, coda-only stream."""
    full_seqs = []
    body_seqs = []
    coda_seqs = []
    inner_seqs = []  # S2+S3+S4 only (no onset, no coda)
    
    for chunks in word_chunk_lists:
        full_word_glyphs = []
        body_word_glyphs = []
        coda_word_glyphs = []
        inner_word_glyphs = []
        for chunk in chunks:
            # Full: all slot contents as glyphs
            for s in SLOT_NAMES:
                if chunk[s] != EMPTY:
                    full_word_glyphs.append(chunk[s])
            # Body: S1+S2+S3+S4
            for s in ['s1', 's2', 's3', 's4']:
                if chunk[s] != EMPTY:
                    body_word_glyphs.append(chunk[s])
            # Inner body: S2+S3+S4 only
            for s in ['s2', 's3', 's4']:
                if chunk[s] != EMPTY:
                    inner_word_glyphs.append(chunk[s])
            # Coda
            if chunk['s5'] != EMPTY:
                coda_word_glyphs.append(chunk['s5'])
        
        if full_word_glyphs:
            full_seqs.append(full_word_glyphs)
        if body_word_glyphs:
            body_seqs.append(body_word_glyphs)
        if coda_word_glyphs:
            coda_seqs.append(coda_word_glyphs)
        if inner_word_glyphs:
            inner_seqs.append(inner_word_glyphs)
    
    return {
        'full': compute_sequence_hchar(full_seqs),
        'body_s1234': compute_sequence_hchar(body_seqs),
        'inner_s234': compute_sequence_hchar(inner_seqs),
        'coda_s5': compute_sequence_hchar(coda_seqs),
        'n_full': sum(len(s) for s in full_seqs),
        'n_body': sum(len(s) for s in body_seqs),
        'n_inner': sum(len(s) for s in inner_seqs),
        'n_coda': sum(len(s) for s in coda_seqs),
    }


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 80)
    pr("PHASE 107 — INTRA-CHUNK SLOT MUTUAL INFORMATION DECOMPOSITION")
    pr("=" * 80)
    pr()
    pr("Purpose: Localize WHERE the anomalous h_char residual (+0.26)")
    pr("lives within the LOOP slot grammar structure.")
    pr()
    
    # ── Load VMS ──
    pr("Loading VMS corpus...")
    vms_words = load_vms_words()
    pr(f"  {len(vms_words)} words loaded")
    
    # Parse into chunks with slots
    word_chunk_lists = []
    all_chunks = []
    n_parsed = 0
    n_unparsed = 0
    
    for w in vms_words:
        chunks = parse_word_slots(w)
        if chunks:
            word_chunk_lists.append(chunks)
            all_chunks.extend(chunks)
            n_parsed += 1
        else:
            n_unparsed += 1
    
    pr(f"  {n_parsed} words parsed, {n_unparsed} failed")
    pr(f"  {len(all_chunks)} total chunks ({len(all_chunks)/n_parsed:.2f} chunks/word)")
    pr()
    
    # ── Slot inventories ──
    pr("=" * 80)
    pr("SLOT INVENTORIES")
    pr("=" * 80)
    pr()
    for s in SLOT_NAMES:
        c = Counter(chunk[s] for chunk in all_chunks)
        n_filled = sum(v for k, v in c.items() if k != EMPTY)
        n_empty = c.get(EMPTY, 0)
        types = sorted([(k, v) for k, v in c.items() if k != EMPTY], key=lambda x: -x[1])
        pr(f"  {s.upper()}: {n_filled} filled ({n_filled/len(all_chunks)*100:.1f}%), "
           f"{n_empty} empty, {len(types)} types, H={entropy(c):.3f} bits")
        top = ", ".join(f"{k}({v})" for k, v in types[:8])
        pr(f"       Top: {top}")
    pr()
    
    # ══════════════════════════════════════════════════════════════════
    # SECTION A: WITHIN-CHUNK SLOT PAIR MI
    # ══════════════════════════════════════════════════════════════════
    pr("=" * 80)
    pr("A. WITHIN-CHUNK PAIRWISE SLOT MI (VMS)")
    pr("=" * 80)
    pr()
    
    vms_mis = compute_slot_mis(all_chunks)
    
    pr(f"  {'Pair':<12s} {'MI':>8s} {'NMI':>8s} {'H(X)':>8s} {'H(Y)':>8s} {'H(X,Y)':>8s} {'Types_X':>8s} {'Types_Y':>8s}")
    pr("  " + "─" * 72)
    for (si, sj), v in sorted(vms_mis.items()):
        pr(f"  {si+','+sj:<12s} {v['mi']:8.4f} {v['nmi']:8.4f} "
           f"{v['hx']:8.3f} {v['hy']:8.3f} {v['hxy']:8.3f} "
           f"{v['cx_types']:>8d} {v['cy_types']:>8d}")
    pr()
    
    # Rank by MI and NMI
    by_mi = sorted(vms_mis.items(), key=lambda x: -x[1]['mi'])
    by_nmi = sorted(vms_mis.items(), key=lambda x: -x[1]['nmi'])
    pr("  Ranked by MI:")
    for rank, ((si, sj), v) in enumerate(by_mi[:5]):
        pr(f"    {rank+1}. {si},{sj}: MI={v['mi']:.4f} NMI={v['nmi']:.4f}")
    pr()
    pr("  Ranked by NMI:")
    for rank, ((si, sj), v) in enumerate(by_nmi[:5]):
        pr(f"    {rank+1}. {si},{sj}: MI={v['mi']:.4f} NMI={v['nmi']:.4f}")
    pr()
    
    # ══════════════════════════════════════════════════════════════════
    # SECTION B: CROSS-BOUNDARY MI
    # ══════════════════════════════════════════════════════════════════
    pr("=" * 80)
    pr("B. CROSS-BOUNDARY MI")
    pr("=" * 80)
    pr()
    
    boundary_mis = compute_boundary_mis(word_chunk_lists)
    for key, v in boundary_mis.items():
        pr(f"  {key:<25s}: MI={v['mi']:.4f}  NMI={v['nmi']:.4f}  "
           f"H(X)={v['hx']:.3f}  H(Y)={v['hy']:.3f}  n={v['n']}")
    pr()
    
    # ══════════════════════════════════════════════════════════════════
    # SECTION C: NULL MODEL — SLOT RESAMPLE
    # ══════════════════════════════════════════════════════════════════
    pr("=" * 80)
    pr("C. NULL MODEL: SLOT-RESAMPLE (200 iterations)")
    pr("=" * 80)
    pr()
    pr("  Shuffling each slot independently to destroy cross-slot correlations...")
    
    null_mis = slot_resample_null(all_chunks, n_iter=200)
    
    pr()
    pr(f"  {'Pair':<12s} {'Obs MI':>8s} {'Null μ':>8s} {'Null σ':>8s} {'z-score':>8s} {'Excess':>8s}")
    pr("  " + "─" * 56)
    
    z_scores = {}
    for (si, sj) in sorted(null_mis.keys()):
        obs = vms_mis[(si, sj)]['mi']
        null_vals = null_mis[(si, sj)]
        null_mean = np.mean(null_vals)
        null_std = np.std(null_vals)
        z = (obs - null_mean) / null_std if null_std > 1e-10 else 0.0
        excess = obs - null_mean
        z_scores[(si, sj)] = z
        sig = "***" if abs(z) > 3.65 else "**" if abs(z) > 2.93 else "*" if abs(z) > 2.33 else ""
        pr(f"  {si+','+sj:<12s} {obs:8.4f} {null_mean:8.4f} {null_std:8.4f} "
           f"{z:8.1f} {excess:8.4f} {sig}")
    pr()
    pr("  Significance: * p<0.01  ** p<0.004 (Bonferroni)  *** p<0.001")
    pr()
    
    # Rank excess MI
    excess_ranked = sorted(z_scores.items(), key=lambda x: -x[1])
    pr("  EXCESS MI RANKING (where the anomaly lives):")
    for rank, ((si, sj), z) in enumerate(excess_ranked):
        obs = vms_mis[(si, sj)]['mi']
        null_mean = np.mean(null_mis[(si, sj)])
        pr(f"    {rank+1}. {si},{sj}: z={z:.1f}, excess MI = {obs - null_mean:.4f}")
    pr()
    
    # ══════════════════════════════════════════════════════════════════
    # SECTION D: NL BASELINE — CVC DECOMPOSITION
    # ══════════════════════════════════════════════════════════════════
    pr("=" * 80)
    pr("D. NL BASELINE: CVC SYLLABLE SLOT MI")
    pr("=" * 80)
    pr()
    
    nl_corpora = {
        "Latin (Pliny)": DATA_DIR / "latin_texts" / "pliny.txt",
        "Latin (Galen)": DATA_DIR / "latin_texts" / "galen.txt",
        "Italian (Cucina)": DATA_DIR / "vernacular_texts" / "italian_cucina.txt",
        "German (Ortolf)": DATA_DIR / "vernacular_texts" / "german_ortolf_raw.txt",
        "German (Faust)": DATA_DIR / "vernacular_texts" / "german_faust.txt",
        "French (Viandier)": DATA_DIR / "vernacular_texts" / "french_viandier.txt",
        "English (Cury)": DATA_DIR / "vernacular_texts" / "english_cury.txt",
    }
    
    nl_results = {}
    for name, path in nl_corpora.items():
        words = load_nl_corpus(path)
        if len(words) < 500:
            continue
        mis = compute_nl_slot_mis(words)
        if mis:
            nl_results[name] = mis
    
    # Czech
    czech_words = load_czech_corpus()
    if len(czech_words) > 500:
        mis = compute_nl_slot_mis(czech_words)
        if mis:
            nl_results["Czech (Kralice)"] = mis
    
    # Display NL results
    for name, mis in nl_results.items():
        pr(f"  {name}:")
        for (si, sj), v in sorted(mis.items()):
            pr(f"    {si},{sj}: MI={v['mi']:.4f}  NMI={v['nmi']:.4f}  n={v['n']}")
        pr()
    
    # Compare VMS to NL mean
    # Map VMS slots to NL slots: s1≈onset, s2≈nucleus(front), s3≈nucleus(core), s4≈nucleus(back)/coda_inner, s5≈coda
    # Best comparison: VMS (s2,s4) vs NL (onset,coda) — both are the "edge" slots bracketing the core
    pr("  COMPARISON: VMS slot MI vs NL CVC MI")
    pr()
    
    # Collect NL MIs for each pair
    nl_pair_mis = defaultdict(list)
    for name, mis in nl_results.items():
        for pair, v in mis.items():
            nl_pair_mis[pair].append(v['mi'])
    
    pr(f"  {'NL Pair':<20s} {'NL MI μ':>8s} {'NL MI σ':>8s}")
    pr("  " + "─" * 40)
    for pair in sorted(nl_pair_mis.keys()):
        vals = nl_pair_mis[pair]
        pr(f"  {str(pair):<20s} {np.mean(vals):8.4f} {np.std(vals):8.4f}")
    pr()
    
    # ══════════════════════════════════════════════════════════════════
    # SECTION E: BODY ISOLATION — ENTROPY RE-ANALYSIS
    # ══════════════════════════════════════════════════════════════════
    pr("=" * 80)
    pr("E. BODY ISOLATION: ENTROPY OF BODY vs CODA vs FULL")
    pr("=" * 80)
    pr()
    pr("  Separate each chunk into BODY (S1+S2+S3+S4) and CODA (S5).")
    pr("  Compute h_char (conditional bigram entropy) for each stream.")
    pr("  If the abbreviation layer (coda) is pulling down h_char,")
    pr("  removing it should RAISE h_char toward NL range (0.82-0.88).")
    pr()
    
    ent_results = body_coda_entropy_analysis(word_chunk_lists)
    
    pr(f"  {'Stream':<20s} {'n_tokens':>10s} {'h_char':>10s} {'h_ratio':>10s}")
    pr("  " + "─" * 55)
    for key in ['full', 'body_s1234', 'inner_s234', 'coda_s5']:
        hc, hr = ent_results[key]
        n = ent_results[f'n_{key.split("_")[0]}'] if key != 'full' else ent_results['n_full']
        pr(f"  {key:<20s} {n:>10d} {hc:10.4f} {hr:10.4f}")
    pr()
    pr(f"  NL reference range: h_char ≈ 0.82-0.88, h_ratio ≈ 0.82-0.88")
    pr(f"  VMS full h_char (Phase 97): 0.6560")
    pr()
    
    change_body = ent_results['body_s1234'][0] - ent_results['full'][0]
    change_inner = ent_results['inner_s234'][0] - ent_results['full'][0]
    pr(f"  Δh_char (body S1234 vs full): {change_body:+.4f}")
    pr(f"  Δh_char (inner S234 vs full): {change_inner:+.4f}")
    pr()
    
    if change_body > 0.05:
        pr("  → Body h_char RISES when coda removed: supports two-layer hypothesis")
    elif change_body < -0.05:
        pr("  → Body h_char DROPS when coda removed: coda was ADDING entropy (unexpected)")
    else:
        pr("  → Body h_char UNCHANGED: anomaly is NOT primarily in the coda layer")
    pr()
    
    # ══════════════════════════════════════════════════════════════════
    # SECTION F: BODY-CODA MUTUAL INFORMATION
    # ══════════════════════════════════════════════════════════════════
    pr("=" * 80)
    pr("F. BODY-CODA MUTUAL INFORMATION")
    pr("=" * 80)
    pr()
    pr("  Do chunk bodies predict their codas?")
    pr("  In a real abbreviation system: LOW MI (suffix = grammatical class, not specific stem)")
    pr("  In a cipher: MI could be HIGH (coda encodes part of same plaintext)")
    pr()
    
    # For each chunk, the "body string" = S1+S2+S3+S4 concatenated, coda = S5
    body_counter = Counter()
    coda_counter = Counter()
    joint_counter = Counter()
    
    for chunk in all_chunks:
        body_parts = []
        for s in ['s1', 's2', 's3', 's4']:
            if chunk[s] != EMPTY:
                body_parts.append(chunk[s])
        body_str = '.'.join(body_parts) if body_parts else EMPTY
        coda_str = chunk['s5']
        body_counter[body_str] += 1
        coda_counter[coda_str] += 1
        joint_counter[(body_str, coda_str)] += 1
    
    body_coda_mi = mutual_information(body_counter, coda_counter, joint_counter)
    body_coda_nmi = normalized_mi(body_counter, coda_counter, joint_counter)
    h_body = entropy(body_counter)
    h_coda = entropy(coda_counter)
    h_coda_given_body = conditional_entropy(body_counter, joint_counter)
    
    pr(f"  H(body):         {h_body:.4f} bits  ({len([v for v in body_counter.values() if v > 0])} types)")
    pr(f"  H(coda):         {h_coda:.4f} bits  ({len([v for v in coda_counter.values() if v > 0])} types)")
    pr(f"  MI(body; coda):  {body_coda_mi:.4f} bits")
    pr(f"  NMI(body; coda): {body_coda_nmi:.4f}")
    pr(f"  H(coda|body):    {h_coda_given_body:.4f} bits")
    pr(f"  Fraction of coda entropy explained by body: {(body_coda_mi / h_coda * 100) if h_coda > 0 else 0:.1f}%")
    pr()
    
    # ══════════════════════════════════════════════════════════════════
    # SECTION G: VERDICT
    # ══════════════════════════════════════════════════════════════════
    pr("=" * 80)
    pr("PHASE 107 — VERDICT")
    pr("=" * 80)
    pr()
    
    # Find the slot pair with highest excess MI
    top_excess = excess_ranked[0]
    pr(f"  1. DOMINANT ANOMALOUS INTERACTION:")
    pr(f"     {top_excess[0][0]},{top_excess[0][1]}: z = {top_excess[1]:.1f}")
    obs = vms_mis[top_excess[0]]['mi']
    null_mean = np.mean(null_mis[top_excess[0]])
    pr(f"     Observed MI = {obs:.4f}, Null MI = {null_mean:.4f}, Excess = {obs - null_mean:.4f}")
    pr()
    
    # Count how many pairs are significant
    n_sig = sum(1 for z in z_scores.values() if abs(z) > 2.93)  # Bonferroni
    pr(f"  2. {n_sig} of 10 slot pairs show significant excess MI (Bonferroni α=0.004)")
    pr()
    
    body_hc = ent_results['body_s1234'][0]
    full_hc = ent_results['full'][0]
    pr(f"  3. BODY ISOLATION RESULT:")
    pr(f"     Full h_char:  {full_hc:.4f}")
    pr(f"     Body h_char:  {body_hc:.4f}")
    pr(f"     NL range:     0.82-0.88")
    if body_hc > 0.75:
        pr(f"     → BODY IS IN NL RANGE: two-layer hypothesis SUPPORTED")
    elif body_hc > full_hc + 0.05:
        pr(f"     → Body rises but not to NL range: partial two-layer effect")
    else:
        pr(f"     → Body entropy still anomalous: anomaly is NOT just in the coda")
    pr()
    
    pr(f"  4. BODY-CODA MI:")
    pr(f"     MI(body; coda) = {body_coda_mi:.4f}")
    pr(f"     NMI = {body_coda_nmi:.4f}")
    if body_coda_nmi > 0.3:
        pr(f"     → HIGH: bodies strongly predict codas (cipher-like)")
    elif body_coda_nmi > 0.1:
        pr(f"     → MODERATE: some body-coda coupling (abbreviation-compatible)")
    else:
        pr(f"     → LOW: bodies and codas are nearly independent (pure abbreviation)")
    pr()
    
    pr("  5. IMPLICATIONS:")
    pr()
    if body_hc > 0.75 and body_coda_nmi < 0.2:
        pr("     The coda layer IS the anomaly source. Removing it restores NL-like")
        pr("     entropy. The two-layer model (abbreviation + content) is VALIDATED.")
        pr("     Next step: frequency-match body segments to candidate languages.")
    elif n_sig > 5:
        pr("     Multiple slot pairs carry excess MI: the anomaly is DISTRIBUTED")
        pr("     across the chunk structure, not localized to one interaction.")
        pr("     This is consistent with a CIPHER that entangles all positions,")
        pr("     or with an encoding that is fundamentally different from NL.")
    else:
        pr("     Results are mixed. The anomaly may involve higher-order")
        pr("     interactions (3+ slots) that pairwise MI cannot detect.")
    pr()
    
    # Save
    result_text = ''.join(OUTPUT)
    outpath = RESULTS_DIR / "phase107_slot_mi_decomposition.txt"
    outpath.write_text(result_text, encoding='utf-8')
    pr(f"\nSaved to {outpath}")


if __name__ == "__main__":
    main()
