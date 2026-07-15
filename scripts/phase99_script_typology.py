#!/usr/bin/env python3
"""
Phase 99 — Script Typology Comparison

═══════════════════════════════════════════════════════════════════════

OBJECTIVE:
  Compare VMS chunk statistics against known writing system types:
  alphabets, abugidas, syllabaries, and abjads. Determine if VMS best
  matches a constructed abugida and identify the closest structural
  parallel.

METHOD:
  1. Compute VMS chunk structural metrics:
     - Inventory size, within-unit MI, slot fill rates, positional
       entropy, h_ratio, unit/word ratio, slot predictability
  2. Compute SAME metrics for available NL corpora at multiple levels:
     a. Character level (alphabet model)
     b. Syllable level with onset/nucleus/coda decomposition
        (pseudo-abugida model — NL syllables share the base+modifier
        structure of abugidas)
  3. Reference points from published typology for:
     - Devanagari (abugida): ~36 base consonants, ~12 vowel marks
     - Tibetan (abugida): ~30 base, ~4 vowel marks
     - Ethiopic/Ge'ez (abugida): ~26 base × ~7 orders = 182 symbols
     - Japanese hiragana (syllabary): 46 holistic symbols
     - Cherokee (syllabary): 85 holistic symbols
     - Hebrew (abjad): 22 consonants + optional vowel points
     - Korean Hangul (featural alphabetic syllabary): ~24 jamo in blocks
  4. Define 8-D typological feature vector:
     F1: log2(inventory_size) — alphabet ≈4.5, abugida ≈5-7, syllabary ≈6-7
     F2: within_unit_MI — high for abugida, zero for syllabary
     F3: slot_count — 1 for syllabary, 2-3 for abugida, ~5 for VMS
     F4: mean_fill_rate — fraction of slots actually filled per unit
     F5: onset_dominance — P(onset_filled) / P(any_slot_filled)
     F6: positional_entropy_ratio — H(unit|position) / H(unit)
     F7: h_ratio at unit level
     F8: units_per_word
  5. Euclidean and cosine distances in this space
  6. NULL MODEL: random rotations in feature space

CRITICAL SKEPTICISM:
  - We do NOT have actual abugida/syllabary corpora. Reference points
    are from published parameters, not measured. This introduces
    systematic uncertainty.
  - NL syllable decomposition is an approximation. Romance syllable
    structure is C(C)V(C), not exactly CVC. German allows CCCVCC+.
  - The feature space is hand-designed. Different feature choices could
    yield different distances. Must test sensitivity.
  - The comparison is STRUCTURAL, not phonological. VMS chunks share
    structural features with abugidas, but that doesn't mean VMS IS
    an abugida — it could be a constructed system that independently
    converged on similar structure.
  - Inventory sizes for reference scripts are for the WRITING SYSTEM,
    not corpus statistics. VMS inventory (523 types, 25 classes) sits
    between these levels.
  - Korean Hangul is the best analogy for VMS: featural blocks with
    internal slot structure but holistic selection. Must be included.

═══════════════════════════════════════════════════════════════════════
"""

import re, sys, io, math, json, os
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import clean_word, conditional_entropy, entropy, eva_to_glyphs, extract_words_from_line

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR  = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
FOLIO_DIR   = PROJECT_DIR / 'folios'
DATA_DIR    = PROJECT_DIR / 'data'
LATIN_DIR   = DATA_DIR / 'latin_texts'
VERN_DIR    = DATA_DIR / 'vernacular_texts'
RESULTS_DIR = PROJECT_DIR / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(42)
random.seed(42)


# ═══════════════════════════════════════════════════════════════════════
# VMS CHUNK PARSING (from Phase 85/98)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']



SLOT1 = {'ch', 'sh', 'y'}
SLOT2_RUNS = {'e'}
SLOT2_SINGLE = {'q', 'a'}
SLOT3 = {'o'}
SLOT4_RUNS = {'i'}
SLOT4_SINGLE = {'d'}
SLOT5 = {'y', 'p', 'f', 'k', 'l', 'r', 's', 't',
         'cth', 'ckh', 'cph', 'cfh', 'n', 'm'}
MAX_CHUNKS = 6

def parse_one_chunk_with_slots(glyphs, pos):
    """Returns (glyph_list, slot_assignments, new_pos)."""
    start = pos
    result = []
    if pos < len(glyphs) and glyphs[pos] in SLOT1:
        result.append((glyphs[pos], 1)); pos += 1
    if pos < len(glyphs):
        if glyphs[pos] in SLOT2_RUNS:
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT2_RUNS and count < 3:
                result.append((glyphs[pos], 2)); pos += 1; count += 1
        elif glyphs[pos] in SLOT2_SINGLE:
            result.append((glyphs[pos], 2)); pos += 1
    if pos < len(glyphs) and glyphs[pos] in SLOT3:
        result.append((glyphs[pos], 3)); pos += 1
    if pos < len(glyphs):
        if glyphs[pos] in SLOT4_RUNS:
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT4_RUNS and count < 3:
                result.append((glyphs[pos], 4)); pos += 1; count += 1
        elif glyphs[pos] in SLOT4_SINGLE:
            result.append((glyphs[pos], 4)); pos += 1
    if pos < len(glyphs) and glyphs[pos] in SLOT5:
        result.append((glyphs[pos], 5)); pos += 1
    if pos == start:
        return None, None, pos
    return [g for g, s in result], result, pos


def parse_word_full(word_str):
    glyphs = eva_to_glyphs(word_str)
    chunks = []
    unparsed = []
    pos = 0
    while pos < len(glyphs) and len(chunks) < MAX_CHUNKS:
        glyph_list, slot_pairs, new_pos = parse_one_chunk_with_slots(glyphs, pos)
        if glyph_list is None:
            unparsed.append(glyphs[pos]); pos += 1
        else:
            chunks.append(slot_pairs); pos = new_pos
    while pos < len(glyphs):
        unparsed.append(glyphs[pos]); pos += 1
    return chunks, unparsed


def chunk_to_str(slot_pairs):
    return '.'.join(g for g, s in slot_pairs)


# ═══════════════════════════════════════════════════════════════════════
# VMS TEXT EXTRACTION (from Phase 85/98)
# ═══════════════════════════════════════════════════════════════════════



def parse_all_folios():
    words = []
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
                words.extend(extract_words_from_line(rest))
    return words


# ═══════════════════════════════════════════════════════════════════════
# NL TEXT LOADING & SYLLABIFICATION WITH SLOT DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════

VOWELS = set('aeiouyàáâãäåæèéêëìíîïòóôõöùúûüýœěůířžščťďňáéíóú')
CONSONANTS_SPECIAL = {'ch', 'sh', 'th', 'ph', 'sch', 'ck', 'ng', 'qu'}

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
    words = re.findall(r'[a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþßœěůířžščťďňáéíóú]+', text)
    return words


def load_czech_bible():
    """Load Czech Bible Kralice texts."""
    czech_dir = DATA_DIR / 'czech_bible_kralice'
    words = []
    for fp in sorted(czech_dir.glob('ces1613_*_read.txt')):
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read().lower()
        # Remove verse numbers and markup
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'\d+', '', text)
        ws = re.findall(r'[a-záéíóúůýěžščřďťň]+', text)
        words.extend(ws)
    return words


def syllabify_word_with_slots(word, vowels=VOWELS):
    """Syllabify a word and decompose each syllable into
    (onset, nucleus, coda) slots.

    Returns list of (onset_str, nucleus_str, coda_str) tuples.
    """
    if len(word) <= 1:
        if word and word in vowels:
            return [('', word, '')]
        elif word:
            return [(word, '', '')]
        return []

    # Mark vowels vs consonants
    is_v = [c in vowels for c in word]

    # Find syllable boundaries (onset maximization)
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

    # Decompose each syllable into onset/nucleus/coda
    syllables = []
    for k in range(len(boundaries)):
        start = boundaries[k]
        end = boundaries[k+1] if k+1 < len(boundaries) else len(word)
        syl = word[start:end]
        if not syl:
            continue

        # Find nucleus (first vowel cluster)
        syl_chars = list(syl)
        onset = []
        nucleus = []
        coda = []

        state = 'onset'
        for c in syl_chars:
            if state == 'onset':
                if c in vowels:
                    nucleus.append(c)
                    state = 'nucleus'
                else:
                    onset.append(c)
            elif state == 'nucleus':
                if c in vowels:
                    nucleus.append(c)
                else:
                    coda.append(c)
                    state = 'coda'
            else:  # coda
                coda.append(c)

        syllables.append((''.join(onset), ''.join(nucleus), ''.join(coda)))

    return syllables if syllables else [('', word, '')]


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL METRICS
# ═══════════════════════════════════════════════════════════════════════



def h_ratio_from_tokens(tokens):
    if len(tokens) < 2: return float('nan')
    unigram = Counter(tokens)
    bigram = Counter()
    prev_counts = Counter()
    for i in range(1, len(tokens)):
        bigram[(tokens[i-1], tokens[i])] += 1
        prev_counts[tokens[i-1]] += 1
    h_uni = entropy(unigram)
    h_cond = conditional_entropy(bigram, prev_counts)
    return h_cond / h_uni if h_uni > 0 else float('nan')

def mutual_information(pairs):
    """Compute MI from a list of (a, b) pairs."""
    pair_counts = Counter(pairs)
    a_counts = Counter(p[0] for p in pairs)
    b_counts = Counter(p[1] for p in pairs)
    N = len(pairs)
    if N < 10: return float('nan')
    mi = 0.0
    for (a, b), c in pair_counts.items():
        p_ab = c / N
        p_a = a_counts[a] / N
        p_b = b_counts[b] / N
        if p_a > 0 and p_b > 0:
            mi += p_ab * math.log2(p_ab / (p_a * p_b))
    return mi


# ═══════════════════════════════════════════════════════════════════════
# VMS CHUNK STRUCTURAL METRICS
# ═══════════════════════════════════════════════════════════════════════

def compute_vms_chunk_metrics(word_list):
    """Compute all typological metrics for VMS chunks."""
    all_chunks = []  # list of slot_pairs lists
    all_chunk_strs = []
    words_chunk_counts = []

    for w in word_list:
        chunks, unparsed = parse_word_full(w)
        if not chunks:
            continue
        for sp in chunks:
            all_chunks.append(sp)
            all_chunk_strs.append(chunk_to_str(sp))
        words_chunk_counts.append(len(chunks))

    n_tokens = len(all_chunk_strs)
    n_types = len(set(all_chunk_strs))

    # Slot fill rates (5 slots)
    slot_fill = [0, 0, 0, 0, 0]
    slot_inventories = [set() for _ in range(5)]
    for sp in all_chunks:
        slots_present = set()
        for glyph, slot_num in sp:
            slots_present.add(slot_num)
            if 1 <= slot_num <= 5:
                slot_inventories[slot_num - 1].add(glyph)
        for s in range(1, 6):
            if s in slots_present:
                slot_fill[s-1] += 1
    slot_fill_rates = [c / n_tokens for c in slot_fill]
    mean_fill = sum(slot_fill_rates) / 5

    # Within-chunk MI: MI between adjacent glyphs within chunks
    within_pairs = []
    for sp in all_chunks:
        for i in range(1, len(sp)):
            within_pairs.append((sp[i-1][0], sp[i][0]))
    within_mi = mutual_information(within_pairs) if within_pairs else 0.0

    # Slot-to-slot MI within chunks (structural regularity)
    slot_pairs = []
    for sp in all_chunks:
        slots = [s for _, s in sp]
        for i in range(1, len(slots)):
            slot_pairs.append((slots[i-1], slots[i]))
    slot_mi = mutual_information(slot_pairs) if slot_pairs else 0.0

    # Positional entropy: H(chunk | position_in_word)
    pos_chunks = defaultdict(Counter)  # position -> Counter of chunk types
    for w in word_list:
        chunks, _ = parse_word_full(w)
        for i, sp in enumerate(chunks):
            cstr = chunk_to_str(sp)
            pos_key = 'initial' if i == 0 else ('final' if i == len(chunks)-1 else 'medial')
            pos_chunks[pos_key][cstr] += 1
    pos_entropies = {pos: entropy(cnt) for pos, cnt in pos_chunks.items()}
    h_unconditional = entropy(Counter(all_chunk_strs))
    # Weighted mean positional entropy
    total_pos = sum(sum(cnt.values()) for cnt in pos_chunks.values())
    h_pos_conditional = sum(
        (sum(cnt.values()) / total_pos) * entropy(cnt)
        for cnt in pos_chunks.values()
    ) if total_pos > 0 else 0
    pos_entropy_ratio = h_pos_conditional / h_unconditional if h_unconditional > 0 else 1.0

    # h_ratio at chunk level
    h_ratio = h_ratio_from_tokens(all_chunk_strs)

    # Mean units per word
    mean_upw = np.mean(words_chunk_counts) if words_chunk_counts else 0

    # Onset dominance: P(S1 filled) relative to mean fill rate
    onset_dominance = slot_fill_rates[0] / mean_fill if mean_fill > 0 else 0

    # Slot count (effective: how many slots are typically used)
    mean_glyphs_per_chunk = np.mean([len(sp) for sp in all_chunks])

    return {
        'inventory_size': n_types,
        'log2_inventory': math.log2(n_types) if n_types > 0 else 0,
        'within_unit_mi': within_mi,
        'slot_mi': slot_mi,
        'n_slots': 5,
        'mean_fill_rate': mean_fill,
        'slot_fill_rates': slot_fill_rates,
        'slot_inventory_sizes': [len(s) for s in slot_inventories],
        'onset_dominance': onset_dominance,
        'pos_entropy_ratio': pos_entropy_ratio,
        'h_ratio': h_ratio,
        'units_per_word': mean_upw,
        'mean_glyphs_per_unit': mean_glyphs_per_chunk,
        'n_tokens': n_tokens,
        'n_types': n_types,
    }


# ═══════════════════════════════════════════════════════════════════════
# NL SYLLABLE STRUCTURAL METRICS (same features)
# ═══════════════════════════════════════════════════════════════════════

def compute_nl_syllable_metrics(word_list, label=""):
    """Compute typological metrics for NL syllables with ONC decomposition."""
    all_syls = []  # list of (onset, nucleus, coda) tuples
    all_syl_strs = []
    words_syl_counts = []

    for w in word_list:
        syls = syllabify_word_with_slots(w)
        if not syls:
            continue
        for s in syls:
            all_syls.append(s)
            all_syl_strs.append(s[0] + '|' + s[1] + '|' + s[2])
        words_syl_counts.append(len(syls))

    n_tokens = len(all_syl_strs)
    n_types = len(set(all_syl_strs))
    if n_tokens < 100:
        return None

    # Slot fill rates (3 slots: onset, nucleus, coda)
    onset_filled = sum(1 for o, n, c in all_syls if o)
    nucleus_filled = sum(1 for o, n, c in all_syls if n)
    coda_filled = sum(1 for o, n, c in all_syls if c)
    slot_fill_rates = [
        onset_filled / n_tokens,
        nucleus_filled / n_tokens,
        coda_filled / n_tokens
    ]
    mean_fill = sum(slot_fill_rates) / 3

    # Slot inventories
    onset_inv = set(o for o, n, c in all_syls if o)
    nucleus_inv = set(n for o, n, c in all_syls if n)
    coda_inv = set(c for o, n, c in all_syls if c)

    # Within-syllable MI: between onset and nucleus, nucleus and coda
    on_pairs = [(o if o else '<empty>', n if n else '<empty>') for o, n, c in all_syls]
    nc_pairs = [(n if n else '<empty>', c if c else '<empty>') for o, n, c in all_syls]
    within_mi_on = mutual_information(on_pairs)
    within_mi_nc = mutual_information(nc_pairs)
    within_mi = (within_mi_on + within_mi_nc) / 2

    # Slot-to-slot MI (trivially ordered: onset→nucleus→coda)
    slot_seq_pairs = []
    for o, n, c in all_syls:
        slots = []
        if o: slots.append('O')
        if n: slots.append('N')
        if c: slots.append('C')
        for i in range(1, len(slots)):
            slot_seq_pairs.append((slots[i-1], slots[i]))
    slot_mi = mutual_information(slot_seq_pairs) if slot_seq_pairs else 0.0

    # Positional entropy
    pos_syls = defaultdict(Counter)
    for w in word_list[:50000]:  # cap for speed
        syls = syllabify_word_with_slots(w)
        for i, s in enumerate(syls):
            sstr = s[0] + '|' + s[1] + '|' + s[2]
            pos_key = 'initial' if i == 0 else ('final' if i == len(syls)-1 else 'medial')
            pos_syls[pos_key][sstr] += 1
    h_unconditional = entropy(Counter(all_syl_strs))
    total_pos = sum(sum(cnt.values()) for cnt in pos_syls.values())
    h_pos_conditional = sum(
        (sum(cnt.values()) / total_pos) * entropy(cnt)
        for cnt in pos_syls.values()
    ) if total_pos > 0 else 0
    pos_entropy_ratio = h_pos_conditional / h_unconditional if h_unconditional > 0 else 1.0

    # h_ratio at syllable level
    h_ratio = h_ratio_from_tokens(all_syl_strs)

    # Mean units per word
    mean_upw = np.mean(words_syl_counts) if words_syl_counts else 0

    # Onset dominance
    onset_dominance = slot_fill_rates[0] / mean_fill if mean_fill > 0 else 0

    # Mean segments per syllable
    mean_seg = np.mean([
        (1 if o else 0) + (1 if n else 0) + (1 if c else 0)
        for o, n, c in all_syls
    ])

    return {
        'label': label,
        'inventory_size': n_types,
        'log2_inventory': math.log2(n_types) if n_types > 0 else 0,
        'within_unit_mi': within_mi,
        'slot_mi': slot_mi,
        'n_slots': 3,
        'mean_fill_rate': mean_fill,
        'slot_fill_rates': slot_fill_rates,
        'slot_inventory_sizes': [len(onset_inv), len(nucleus_inv), len(coda_inv)],
        'onset_dominance': onset_dominance,
        'pos_entropy_ratio': pos_entropy_ratio,
        'h_ratio': h_ratio,
        'units_per_word': mean_upw,
        'mean_glyphs_per_unit': mean_seg,
        'n_tokens': n_tokens,
        'n_types': n_types,
    }


def compute_nl_char_metrics(word_list, label=""):
    """Compute metrics treating each character as an atomic unit (alphabet model)."""
    chars = list(''.join(word_list))
    n_tokens = len(chars)
    n_types = len(set(chars))
    if n_tokens < 100:
        return None

    h_ratio = h_ratio_from_tokens(chars)
    words_char_counts = [len(w) for w in word_list]
    mean_upw = np.mean(words_char_counts) if words_char_counts else 0

    return {
        'label': label,
        'inventory_size': n_types,
        'log2_inventory': math.log2(n_types) if n_types > 0 else 0,
        'within_unit_mi': 0.0,  # characters have no internal structure
        'slot_mi': 0.0,
        'n_slots': 1,
        'mean_fill_rate': 1.0,
        'onset_dominance': 1.0,
        'pos_entropy_ratio': h_ratio,  # position in word = context
        'h_ratio': h_ratio,
        'units_per_word': mean_upw,
        'mean_glyphs_per_unit': 1.0,
        'n_tokens': n_tokens,
        'n_types': n_types,
    }


# ═══════════════════════════════════════════════════════════════════════
# PUBLISHED TYPOLOGICAL REFERENCE POINTS
# ═══════════════════════════════════════════════════════════════════════
#
# These are derived from typological literature and published
# quantitative studies. Sources:
# - Daniels & Bright (1996) "The World's Writing Systems"
# - Sproat (2000) "A Computational Theory of Writing Systems"
# - Published corpus studies for each script
#
# CRITICAL NOTE: These are ESTIMATES, not measured from corpora.
# Uncertainty ≈ ±20% on most parameters. The comparison is indicative,
# not definitive.

REFERENCE_SCRIPTS = {
    # ── ALPHABETS ──
    'Latin_alphabet': {
        'type': 'alphabet',
        'log2_inventory': math.log2(26),    # 26 letters
        'within_unit_mi': 0.0,              # no internal structure
        'n_slots': 1,
        'mean_fill_rate': 1.0,
        'onset_dominance': 1.0,
        'pos_entropy_ratio': 0.85,          # NL char h_ratio ≈ 0.82-0.90
        'h_ratio': 0.85,                    # typical NL char
        'units_per_word': 5.0,              # avg Latin word ~5 chars
    },
    'Cyrillic_alphabet': {
        'type': 'alphabet',
        'log2_inventory': math.log2(33),
        'within_unit_mi': 0.0,
        'n_slots': 1,
        'mean_fill_rate': 1.0,
        'onset_dominance': 1.0,
        'pos_entropy_ratio': 0.84,
        'h_ratio': 0.84,
        'units_per_word': 5.5,
    },

    # ── ABJADS ──
    'Hebrew_abjad': {
        'type': 'abjad',
        'log2_inventory': math.log2(27),    # 22 consonants + 5 final forms
        'within_unit_mi': 0.05,             # minimal: optional nikkud
        'n_slots': 2,                       # consonant + optional vowel point
        'mean_fill_rate': 0.55,             # vowel points often absent
        'onset_dominance': 1.5,             # consonant always present
        'pos_entropy_ratio': 0.82,
        'h_ratio': 0.78,                    # lower due to root pattern (CCC)
        'units_per_word': 4.0,
    },
    'Arabic_abjad': {
        'type': 'abjad',
        'log2_inventory': math.log2(36),    # 28 base + contextual forms
        'within_unit_mi': 0.08,
        'n_slots': 2,
        'mean_fill_rate': 0.58,
        'onset_dominance': 1.4,
        'pos_entropy_ratio': 0.80,
        'h_ratio': 0.76,
        'units_per_word': 4.5,
    },

    # ── ABUGIDAS ──
    'Devanagari_abugida': {
        'type': 'abugida',
        'log2_inventory': math.log2(48),    # ~36 consonants + 12 vowel marks
        'within_unit_mi': 0.45,             # vowel mark partially predicts consonant class
        'n_slots': 3,                       # consonant + vowel + optional virama/conjunct
        'mean_fill_rate': 0.72,             # vowel mark ~90%, conjunct ~25%
        'onset_dominance': 1.15,            # consonant base always present
        'pos_entropy_ratio': 0.88,
        'h_ratio': 0.82,
        'units_per_word': 3.5,              # aksharas per word
    },
    'Tibetan_abugida': {
        'type': 'abugida',
        'log2_inventory': math.log2(34),    # 30 base + 4 vowel marks
        'within_unit_mi': 0.35,
        'n_slots': 4,                       # prefix + root + vowel + suffix
        'mean_fill_rate': 0.62,
        'onset_dominance': 1.1,
        'pos_entropy_ratio': 0.86,
        'h_ratio': 0.80,
        'units_per_word': 2.8,
    },
    'Ethiopic_abugida': {
        'type': 'abugida',
        'log2_inventory': math.log2(182),   # 26 base × 7 orders
        'within_unit_mi': 0.55,             # high: base predicts order pattern
        'n_slots': 2,                       # consonant + vowel order
        'mean_fill_rate': 0.95,             # every character has a vowel order
        'onset_dominance': 1.02,
        'pos_entropy_ratio': 0.90,
        'h_ratio': 0.84,
        'units_per_word': 3.0,
    },
    'Thai_abugida': {
        'type': 'abugida',
        'log2_inventory': math.log2(76),    # 44 consonants + 32 vowels/marks
        'within_unit_mi': 0.40,
        'n_slots': 4,                       # initial + vowel + final + tone
        'mean_fill_rate': 0.65,
        'onset_dominance': 1.12,
        'pos_entropy_ratio': 0.87,
        'h_ratio': 0.81,
        'units_per_word': 3.2,
    },

    # ── SYLLABARIES ──
    'Japanese_hiragana': {
        'type': 'syllabary',
        'log2_inventory': math.log2(46),
        'within_unit_mi': 0.0,              # holistic symbols, no internal structure
        'n_slots': 1,                       # atomic
        'mean_fill_rate': 1.0,
        'onset_dominance': 1.0,
        'pos_entropy_ratio': 0.88,
        'h_ratio': 0.86,
        'units_per_word': 3.5,
    },
    'Cherokee_syllabary': {
        'type': 'syllabary',
        'log2_inventory': math.log2(85),
        'within_unit_mi': 0.0,
        'n_slots': 1,
        'mean_fill_rate': 1.0,
        'onset_dominance': 1.0,
        'pos_entropy_ratio': 0.85,
        'h_ratio': 0.83,
        'units_per_word': 3.0,
    },

    # ── FEATURAL ──
    'Korean_Hangul': {
        'type': 'featural_alphabetic_syllabary',
        'log2_inventory': math.log2(2350),  # ~2350 common syllable blocks
        'within_unit_mi': 0.60,             # strong: jamo predict each other
        'n_slots': 3,                       # initial jamo + medial + final
        'mean_fill_rate': 0.78,             # final often absent
        'onset_dominance': 1.05,
        'pos_entropy_ratio': 0.85,
        'h_ratio': 0.72,                    # lower due to constrained blocks
        'units_per_word': 2.5,              # syllable blocks per word
    },
}


# ═══════════════════════════════════════════════════════════════════════
# TYPOLOGICAL DISTANCE COMPUTATION
# ═══════════════════════════════════════════════════════════════════════

FEATURE_KEYS = [
    'log2_inventory', 'within_unit_mi', 'n_slots', 'mean_fill_rate',
    'onset_dominance', 'pos_entropy_ratio', 'h_ratio', 'units_per_word'
]

def to_feature_vector(metrics_dict):
    """Extract 8-D feature vector."""
    return np.array([metrics_dict.get(k, 0.0) for k in FEATURE_KEYS], dtype=float)


def normalize_features(vectors_dict):
    """Z-normalize features across all systems."""
    all_vecs = list(vectors_dict.values())
    mat = np.array(all_vecs)
    mu = mat.mean(axis=0)
    sigma = mat.std(axis=0)
    sigma[sigma < 1e-10] = 1.0  # avoid division by zero
    normalized = {}
    for name, vec in vectors_dict.items():
        normalized[name] = (vec - mu) / sigma
    return normalized, mu, sigma


def euclidean_distance(a, b):
    return np.sqrt(np.sum((a - b) ** 2))


def cosine_distance(a, b):
    dot = np.dot(a, b)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-10 or nb < 1e-10:
        return 1.0
    return 1.0 - dot / (na * nb)


# ═══════════════════════════════════════════════════════════════════════
# NULL MODEL: PERMUTATION TEST
# ═══════════════════════════════════════════════════════════════════════

def permutation_test_distances(vms_vec, reference_vecs, n_perms=1000):
    """Test whether VMS's closest match is significant.

    Permute VMS features independently and re-compute distances.
    Returns p-value: fraction of permutations where a random system
    is as close to any reference as the real VMS.
    """
    real_distances = {name: euclidean_distance(vms_vec, rvec)
                      for name, rvec in reference_vecs.items()}
    real_min = min(real_distances.values())

    closer_count = 0
    for _ in range(n_perms):
        perm_vec = np.array([
            np.random.choice([v[i] for v in reference_vecs.values()])
            for i in range(len(vms_vec))
        ])
        perm_min = min(euclidean_distance(perm_vec, rvec)
                       for rvec in reference_vecs.values())
        if perm_min <= real_min:
            closer_count += 1

    return closer_count / n_perms


# ═══════════════════════════════════════════════════════════════════════
# FEATURE SENSITIVITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def leave_one_out_sensitivity(vms_vec_norm, ref_vecs_norm, ref_names):
    """Drop each feature and check if nearest-neighbour changes."""
    n_features = len(FEATURE_KEYS)
    baseline_nn = min(ref_names, key=lambda n: euclidean_distance(vms_vec_norm, ref_vecs_norm[n]))

    results = {}
    for drop_idx in range(n_features):
        mask = [True] * n_features
        mask[drop_idx] = False
        vms_reduced = vms_vec_norm[mask]
        nn = min(ref_names, key=lambda n: euclidean_distance(vms_reduced, ref_vecs_norm[n][mask]))
        results[FEATURE_KEYS[drop_idx]] = {
            'nearest': nn,
            'changed': nn != baseline_nn
        }
    return baseline_nn, results


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def run_analysis():
    pr("=" * 72)
    pr("PHASE 99 — SCRIPT TYPOLOGY COMPARISON")
    pr("=" * 72)
    pr()

    # ── Step 1: VMS chunk metrics ──
    pr("─" * 72)
    pr("STEP 1: VMS chunk structural metrics")
    pr("─" * 72)

    vms_words = parse_all_folios()
    vms_metrics = compute_vms_chunk_metrics(vms_words)
    pr(f"\n  VMS chunks: {vms_metrics['n_tokens']:,} tokens, {vms_metrics['n_types']} types")
    pr(f"  log2(inventory): {vms_metrics['log2_inventory']:.2f}")
    pr(f"  Within-chunk MI: {vms_metrics['within_unit_mi']:.4f}")
    pr(f"  Slot MI: {vms_metrics['slot_mi']:.4f}")
    pr(f"  Slot fill rates: " + ', '.join(
        f"S{i+1}={r:.3f}" for i, r in enumerate(vms_metrics['slot_fill_rates'])))
    pr(f"  Mean fill rate: {vms_metrics['mean_fill_rate']:.3f}")
    pr(f"  Onset dominance: {vms_metrics['onset_dominance']:.3f}")
    pr(f"  Positional entropy ratio: {vms_metrics['pos_entropy_ratio']:.4f}")
    pr(f"  h_ratio (chunk level): {vms_metrics['h_ratio']:.4f}")
    pr(f"  Units/word: {vms_metrics['units_per_word']:.3f}")
    pr(f"  Mean glyphs/chunk: {vms_metrics['mean_glyphs_per_unit']:.3f}")

    # ── Step 2: NL syllable metrics ──
    pr()
    pr("─" * 72)
    pr("STEP 2: NL reference corpora — syllable-level metrics")
    pr("─" * 72)

    nl_corpora = {}

    # Latin texts
    for fname in ['vulgate_genesis.txt', 'caesar.txt', 'apicius.txt',
                   'erasmus.txt', 'galen.txt', 'pliny.txt']:
        fp = LATIN_DIR / fname
        if fp.exists():
            words = load_reference_text(fp)
            label = 'Latin_' + fname.replace('.txt', '')
            syl_m = compute_nl_syllable_metrics(words, label=label + '_syl')
            char_m = compute_nl_char_metrics(words, label=label + '_char')
            if syl_m:
                nl_corpora[label + '_syl'] = syl_m
            if char_m:
                nl_corpora[label + '_char'] = char_m

    # Vernacular texts
    for fname in ['german_faust.txt', 'german_ortolf_raw.txt',
                   'italian_cucina.txt', 'french_viandier.txt',
                   'english_cury.txt']:
        fp = VERN_DIR / fname
        if fp.exists():
            words = load_reference_text(fp)
            label = fname.replace('.txt', '')
            syl_m = compute_nl_syllable_metrics(words, label=label + '_syl')
            char_m = compute_nl_char_metrics(words, label=label + '_char')
            if syl_m:
                nl_corpora[label + '_syl'] = syl_m
            if char_m:
                nl_corpora[label + '_char'] = char_m

    # Czech Bible
    czech_words = load_czech_bible()
    if czech_words:
        syl_m = compute_nl_syllable_metrics(czech_words[:200000], label='Czech_kralice_syl')
        char_m = compute_nl_char_metrics(czech_words[:200000], label='Czech_kralice_char')
        if syl_m:
            nl_corpora['Czech_kralice_syl'] = syl_m
        if char_m:
            nl_corpora['Czech_kralice_char'] = char_m

    pr(f"\n  Loaded {len(nl_corpora)} NL corpus analyses")
    pr(f"\n  {'Corpus':<35s} {'type':<6s} {'inv':>5s} {'w_MI':>6s} {'fill':>5s} "
       f"{'h_rat':>6s} {'u/w':>5s} {'pos_e':>6s}")
    pr(f"  {'─'*35} {'─'*6} {'─'*5} {'─'*6} {'─'*5} {'─'*6} {'─'*5} {'─'*6}")

    for name, m in sorted(nl_corpora.items()):
        mtype = 'syl' if '_syl' in name else 'char'
        pr(f"  {name:<35s} {mtype:<6s} {m['n_types']:>5d} "
           f"{m['within_unit_mi']:>6.3f} {m['mean_fill_rate']:>5.3f} "
           f"{m['h_ratio']:>6.4f} {m['units_per_word']:>5.2f} "
           f"{m['pos_entropy_ratio']:>6.4f}")

    # ── Step 3: Typological feature space ──
    pr()
    pr("─" * 72)
    pr("STEP 3: Typological feature space (8 dimensions)")
    pr("─" * 72)

    # Collect all systems for comparison
    all_systems = {}

    # VMS
    all_systems['VMS_chunks'] = to_feature_vector(vms_metrics)

    # Reference scripts (from literature)
    for name, params in REFERENCE_SCRIPTS.items():
        all_systems[name] = to_feature_vector(params)

    # NL syllable-level comparisons (computed empirically)
    for name, m in nl_corpora.items():
        if '_syl' in name:  # only syllable-level for typological comparison
            all_systems[name] = to_feature_vector(m)

    # Print raw feature vectors
    pr(f"\n  {'System':<35s}" + ''.join(f" {k[:8]:>8s}" for k in FEATURE_KEYS))
    pr(f"  {'─'*35}" + ''.join(' ─'*4 for _ in FEATURE_KEYS))

    for name in sorted(all_systems.keys()):
        vec = all_systems[name]
        line = f"  {name:<35s}"
        for v in vec:
            line += f" {v:>8.3f}"
        pr(line)

    # Normalize
    norm_systems, mu, sigma = normalize_features(all_systems)

    # ── Step 4: Distances from VMS to each system ──
    pr()
    pr("─" * 72)
    pr("STEP 4: Distances from VMS to each reference system")
    pr("─" * 72)

    vms_norm = norm_systems['VMS_chunks']
    ref_names = [n for n in sorted(all_systems.keys()) if n != 'VMS_chunks']

    distances = {}
    for name in ref_names:
        d_euc = euclidean_distance(vms_norm, norm_systems[name])
        d_cos = cosine_distance(vms_norm, norm_systems[name])
        distances[name] = {'euclidean': d_euc, 'cosine': d_cos}

    # Sort by euclidean distance
    sorted_by_euc = sorted(distances.items(), key=lambda x: x[1]['euclidean'])

    pr(f"\n  {'System':<35s} {'Type':<12s} {'Euclidean':>10s} {'Cosine':>10s}")
    pr(f"  {'─'*35} {'─'*12} {'─'*10} {'─'*10}")
    for name, d in sorted_by_euc:
        stype = REFERENCE_SCRIPTS.get(name, {}).get('type', 'NL_syl')
        pr(f"  {name:<35s} {stype:<12s} {d['euclidean']:>10.3f} {d['cosine']:>10.3f}")

    # ── Step 5: Group by script type ──
    pr()
    pr("─" * 72)
    pr("STEP 5: Mean distance by script type")
    pr("─" * 72)

    type_distances = defaultdict(list)
    for name, d in distances.items():
        if name in REFERENCE_SCRIPTS:
            stype = REFERENCE_SCRIPTS[name]['type']
        elif '_syl' in name:
            stype = 'NL_syllable'
        else:
            stype = 'other'
        type_distances[stype].append(d['euclidean'])

    pr(f"\n  {'Script Type':<30s} {'Mean dist':>10s} {'Min dist':>10s} {'N':>5s}")
    pr(f"  {'─'*30} {'─'*10} {'─'*10} {'─'*5}")
    for stype in sorted(type_distances.keys()):
        dists = type_distances[stype]
        pr(f"  {stype:<30s} {np.mean(dists):>10.3f} {np.min(dists):>10.3f} {len(dists):>5d}")

    # ── Step 6: Permutation test ──
    pr()
    pr("─" * 72)
    pr("STEP 6: Permutation test — is nearest match significant?")
    pr("─" * 72)

    ref_vecs = {n: norm_systems[n] for n in ref_names if n in REFERENCE_SCRIPTS}
    p_val = permutation_test_distances(vms_norm, ref_vecs, n_perms=2000)
    nearest = sorted_by_euc[0][0]
    nearest_d = sorted_by_euc[0][1]['euclidean']
    pr(f"\n  Nearest reference: {nearest} (d={nearest_d:.3f})")
    pr(f"  Permutation p-value: {p_val:.4f}")
    pr(f"  (Fraction of random feature combinations closer to ANY reference)")

    # ── Step 7: Feature sensitivity (leave-one-out) ──
    pr()
    pr("─" * 72)
    pr("STEP 7: Feature sensitivity — leave-one-out nearest neighbour")
    pr("─" * 72)

    ref_only = {n: norm_systems[n] for n in ref_names if n in REFERENCE_SCRIPTS}
    baseline_nn, sensitivity = leave_one_out_sensitivity(vms_norm, ref_only, list(ref_only.keys()))
    pr(f"\n  Baseline nearest neighbour: {baseline_nn}")
    pr(f"\n  {'Dropped feature':<25s} {'New NN':<30s} {'Changed?':<10s}")
    pr(f"  {'─'*25} {'─'*30} {'─'*10}")
    n_changed = 0
    for feat, res in sensitivity.items():
        changed_str = "YES" if res['changed'] else "no"
        if res['changed']:
            n_changed += 1
        pr(f"  {feat:<25s} {res['nearest']:<30s} {changed_str:<10s}")
    pr(f"\n  Stability: {8 - n_changed}/8 features can be dropped without changing NN")

    # ── Step 8: Dimensional analysis — which features drive the match? ──
    pr()
    pr("─" * 72)
    pr("STEP 8: Per-feature comparison with nearest reference")
    pr("─" * 72)

    nn_vec = norm_systems[baseline_nn]
    pr(f"\n  VMS vs {baseline_nn}:")
    pr(f"  {'Feature':<25s} {'VMS_raw':>8s} {'Ref_raw':>8s} {'VMS_z':>8s} {'Ref_z':>8s} {'|diff|':>8s}")
    pr(f"  {'─'*25} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")

    vms_raw = to_feature_vector(vms_metrics)
    nn_name = baseline_nn
    if nn_name in REFERENCE_SCRIPTS:
        nn_raw = to_feature_vector(REFERENCE_SCRIPTS[nn_name])
    else:
        nn_raw = to_feature_vector(nl_corpora.get(nn_name, {}))

    for i, feat in enumerate(FEATURE_KEYS):
        pr(f"  {feat:<25s} {vms_raw[i]:>8.3f} {nn_raw[i]:>8.3f} "
           f"{vms_norm[i]:>8.3f} {nn_vec[i]:>8.3f} "
           f"{abs(vms_norm[i] - nn_vec[i]):>8.3f}")

    # ── Step 9: VMS vs Korean Hangul deep comparison ──
    pr()
    pr("─" * 72)
    pr("STEP 9: VMS vs Korean Hangul — structural deep comparison")
    pr("─" * 72)

    hangul = REFERENCE_SCRIPTS['Korean_Hangul']
    pr(f"\n  {'Feature':<25s} {'VMS':>10s} {'Hangul':>10s} {'Match?':>10s}")
    pr(f"  {'─'*25} {'─'*10} {'─'*10} {'─'*10}")

    comparisons = [
        ('Slot count', vms_metrics['n_slots'], hangul['n_slots']),
        ('Mean fill rate', vms_metrics['mean_fill_rate'], hangul['mean_fill_rate']),
        ('Within-unit MI', vms_metrics['within_unit_mi'], hangul['within_unit_mi']),
        ('h_ratio', vms_metrics['h_ratio'], hangul['h_ratio']),
        ('Units/word', vms_metrics['units_per_word'], hangul['units_per_word']),
        ('Onset dominance', vms_metrics['onset_dominance'], hangul['onset_dominance']),
        ('Pos entropy ratio', vms_metrics['pos_entropy_ratio'], hangul['pos_entropy_ratio']),
        ('log2(inventory)', vms_metrics['log2_inventory'], hangul['log2_inventory']),
    ]

    for label, vms_val, hangul_val in comparisons:
        if isinstance(vms_val, float) and isinstance(hangul_val, float):
            ratio = vms_val / hangul_val if hangul_val != 0 else float('inf')
            match = "CLOSE" if 0.7 < ratio < 1.3 else "DIFFER"
        else:
            match = "CLOSE" if vms_val == hangul_val else "DIFFER"
        pr(f"  {label:<25s} {vms_val:>10.3f} {hangul_val:>10.3f} {match:>10s}")

    # ── Step 10: Summary ──
    pr()
    pr("─" * 72)
    pr("STEP 10: Summary and Verdict")
    pr("─" * 72)

    # Best matches by type
    pr(f"\n  Top 5 closest systems to VMS:")
    for i, (name, d) in enumerate(sorted_by_euc[:5]):
        stype = REFERENCE_SCRIPTS.get(name, {}).get('type', 'NL_syllable')
        pr(f"    {i+1}. {name} ({stype}): d={d['euclidean']:.3f}")

    pr(f"\n  Top 3 closest by type:")
    for stype in ['abugida', 'syllabary', 'alphabet', 'abjad',
                   'featural_alphabetic_syllabary', 'NL_syllable']:
        if stype in type_distances:
            dists = type_distances[stype]
            pr(f"    {stype:<35s}: mean={np.mean(dists):.3f}, min={np.min(dists):.3f}")

    # Save results
    save_data = {
        'vms_metrics': {k: v for k, v in vms_metrics.items()
                        if not isinstance(v, (list, np.ndarray))},
        'vms_slot_fill_rates': vms_metrics['slot_fill_rates'],
        'vms_slot_inventory_sizes': vms_metrics['slot_inventory_sizes'],
        'distances': {n: d for n, d in distances.items()},
        'type_distances': {t: {'mean': float(np.mean(d)), 'min': float(np.min(d)),
                               'n': len(d)}
                           for t, d in type_distances.items()},
        'nearest_neighbour': baseline_nn,
        'permutation_p_value': p_val,
        'sensitivity_stability': f"{8 - n_changed}/8",
        'nl_syllable_metrics': {
            name: {k: v for k, v in m.items()
                   if not isinstance(v, (list, np.ndarray))}
            for name, m in nl_corpora.items()
        },
    }

    json_path = RESULTS_DIR / 'phase99_script_typology.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, default=str)
    pr(f"\n  Results saved to {json_path}")

    txt_path = RESULTS_DIR / 'phase99_script_typology.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Log saved to {txt_path}")


if __name__ == '__main__':
    run_analysis()
