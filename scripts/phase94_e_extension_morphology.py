#!/usr/bin/env python3
"""
Phase 94 — SLOT2 e-Extension: Productive Morphology or Slot Independence?

═══════════════════════════════════════════════════════════════════════

QUESTION:
  Petrasti (Voynich Ninja thread-5216, Aug 2026) observed that many
  VMS words come in pairs: a "base" form with no front vowel and an
  "extended" form with 'e' inserted before 'o':
    chor → cheor    daiin → deaiin    kor → keor    cho → cheo

  Phase 93 found Currier A leaves SLOT2 empty 68.5% vs B's 48.2%.
  The e-extension IS SLOT2 filling in LOOP grammar terms:
    chor  = ch|∅|o|r   (SLOT1=ch, SLOT2=empty, SLOT3=o, SLOT5=r)
    cheor = ch|e|o|r   (SLOT1=ch, SLOT2=e,     SLOT3=o, SLOT5=r)

  CRITICAL QUESTION: Is this alternation PRODUCTIVE MORPHOLOGY (like
  NL inflection: "walk" → "walking") or INDEPENDENT SLOT FILLING
  (like a cipher where each slot is filled independently)?

  If MORPHOLOGY:
    - NOT all bases get extended (selectional restrictions)
    - Base more frequent than extension (Zipf's stem/inflection law)
    - Pairs co-occur in same contexts (same folios, nearby lines)
    - Positional asymmetry (different line positions)
    - Extension rate differs by Currier A/B

  If INDEPENDENT SLOT FILLING:
    - Nearly ALL bases have extended partners (no restrictions)
    - No systematic frequency asymmetry
    - No positional or Currier distribution differences

WHY THIS IS NOT DIMINISHING RETURNS:
  - Phases 91-93 measured SLOT2 at the MACRO level (per-folio averages).
  - This phase works at the MICRO level: individual word pairs.
  - The answer directly discriminates NL morphology from cipher.
  - Petrasti's claim is independently motivated (different researcher,
    different method, same structural observation).

ANTI-CIRCULARITY TEST:
  LOOP grammar makes SLOT2 optional by design. So SOME base+extended
  pairs are guaranteed. The test is whether the pairing rate at SLOT2
  exceeds what we'd see from random glyph insertion at OTHER positions.
  We'll compare e-extension rate at SLOT2 vs random-position insertion.

NL BASELINE:
  In Latin, many words have stem + vowel-extended forms (e.g., "amor"
  / "amoris"). We'll measure analogous pairing rates.
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import clean_word, eva_to_glyphs

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
# EVA GLYPH TOKENIZER + LOOP PARSER (from Phase 85)
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


def parse_one_chunk(glyphs, pos):
    start = pos
    chunk = []
    slots = {}

    if pos < len(glyphs) and glyphs[pos] in SLOT1:
        slots[1] = [glyphs[pos]]
        chunk.append(glyphs[pos]); pos += 1

    if pos < len(glyphs):
        if glyphs[pos] in SLOT2_RUNS:
            s2 = []
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT2_RUNS and count < 3:
                s2.append(glyphs[pos])
                chunk.append(glyphs[pos]); pos += 1; count += 1
            slots[2] = s2
        elif glyphs[pos] in SLOT2_SINGLE:
            slots[2] = [glyphs[pos]]
            chunk.append(glyphs[pos]); pos += 1

    if pos < len(glyphs) and glyphs[pos] in SLOT3:
        slots[3] = [glyphs[pos]]
        chunk.append(glyphs[pos]); pos += 1

    if pos < len(glyphs):
        if glyphs[pos] in SLOT4_RUNS:
            s4 = []
            count = 0
            while pos < len(glyphs) and glyphs[pos] in SLOT4_RUNS and count < 3:
                s4.append(glyphs[pos])
                chunk.append(glyphs[pos]); pos += 1; count += 1
            slots[4] = s4
        elif glyphs[pos] in SLOT4_SINGLE:
            slots[4] = [glyphs[pos]]
            chunk.append(glyphs[pos]); pos += 1

    if pos < len(glyphs) and glyphs[pos] in SLOT5:
        slots[5] = [glyphs[pos]]
        chunk.append(glyphs[pos]); pos += 1

    if pos == start:
        return None, pos, {}
    return chunk, pos, slots


def parse_word_into_chunks(word_str):
    glyphs = eva_to_glyphs(word_str)
    chunks = []
    slots_list = []
    unparsed = []
    pos = 0
    while pos < len(glyphs) and len(chunks) < MAX_CHUNKS:
        chunk, new_pos, slots = parse_one_chunk(glyphs, pos)
        if chunk is None:
            unparsed.append(glyphs[pos]); pos += 1
        else:
            chunks.append(chunk)
            slots_list.append(slots)
            pos = new_pos
    while pos < len(glyphs):
        unparsed.append(glyphs[pos]); pos += 1
    return chunks, slots_list, unparsed, glyphs


def chunk_to_str(chunk):
    return ''.join(chunk)


def word_to_frame(word_str):
    """Create a 'SLOT2-erased frame' for a word: replace SLOT2 content with '_'.
    Returns (frame_str, list of SLOT2 fillers per chunk)."""
    chunks, slots_list, unparsed, glyphs = parse_word_into_chunks(word_str)
    if unparsed:
        return None, None, None
    frame_parts = []
    s2_fillers = []
    for chunk, slots in zip(chunks, slots_list):
        part = ''
        for slot_num in [1, 3, 4, 5]:
            if slot_num in slots:
                part += ''.join(slots[slot_num])
        s2_content = ''.join(slots.get(2, []))
        s2_fillers.append(s2_content)
        frame_parts.append(part)
    frame = '|'.join(frame_parts)
    return frame, s2_fillers, slots_list


def make_e_extended(word_str):
    """For each chunk with empty SLOT2, create the e-extended variant.
    Returns list of (chunk_index, extended_word_str) pairs."""
    chunks, slots_list, unparsed, glyphs = parse_word_into_chunks(word_str)
    if unparsed:
        return []

    results = []
    for ci, (chunk, slots) in enumerate(zip(chunks, slots_list)):
        if 2 not in slots and 3 in slots:
            # This chunk has empty SLOT2 and has 'o' (SLOT3).
            # Insert 'e' before 'o' to create the extended form.
            new_chunks = []
            for cj, (c, s) in enumerate(zip(chunks, slots_list)):
                if cj == ci:
                    # Build chunk with 'e' inserted at SLOT2
                    new_chunk = []
                    if 1 in s:
                        new_chunk.extend(s[1])
                    new_chunk.append('e')  # SLOT2 = 'e'
                    if 3 in s:
                        new_chunk.extend(s[3])
                    if 4 in s:
                        new_chunk.extend(s[4])
                    if 5 in s:
                        new_chunk.extend(s[5])
                    new_chunks.append(''.join(new_chunk))
                else:
                    new_chunks.append(''.join(c))
            extended_word = ''.join(new_chunks)
            results.append((ci, extended_word))

    return results


def make_a_extended(word_str):
    """Same as make_e_extended but insert 'a' instead of 'e'."""
    chunks, slots_list, unparsed, glyphs = parse_word_into_chunks(word_str)
    if unparsed:
        return []

    results = []
    for ci, (chunk, slots) in enumerate(zip(chunks, slots_list)):
        if 2 not in slots and 3 in slots:
            new_chunks = []
            for cj, (c, s) in enumerate(zip(chunks, slots_list)):
                if cj == ci:
                    new_chunk = []
                    if 1 in s:
                        new_chunk.extend(s[1])
                    new_chunk.append('a')
                    if 3 in s:
                        new_chunk.extend(s[3])
                    if 4 in s:
                        new_chunk.extend(s[4])
                    if 5 in s:
                        new_chunk.extend(s[5])
                    new_chunks.append(''.join(new_chunk))
                else:
                    new_chunks.append(''.join(c))
            results.append((ci, ''.join(new_chunks)))
    return results


# ═══════════════════════════════════════════════════════════════════════
# VMS TEXT EXTRACTION (with positional metadata)
# ═══════════════════════════════════════════════════════════════════════



def parse_currier_from_header(filepath):
    counts = Counter()
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('#'):
                if line and not line.startswith('<'):
                    break
                continue
            m = re.search(r"Currier'?s?\s+[Ll]anguage\s+([AB])", line)
            if m:
                counts[m.group(1)] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def load_all_words_with_position():
    """Load all VMS words with positional metadata.
    Returns list of dicts: {word, folio, currier, line_num, word_pos,
                            is_para_start, is_line_start, is_line_end}"""
    records = []
    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: (int(re.match(r'f(\d+)', p.stem).group(1))
                                        if re.match(r'f(\d+)', p.stem) else 0,
                                        p.stem))

    for filepath in folio_files:
        if filepath.suffix != '.txt':
            continue
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num:
            continue

        folio = filepath.stem
        currier = parse_currier_from_header(filepath)

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                m = re.match(r'<([^>]+)>', line)
                if not m:
                    continue
                tag = m.group(1)
                rest = line[m.end():].strip()
                if not rest:
                    continue

                # Parse line tag for position info
                is_para_start = rest.startswith('<%>')
                line_num_m = re.search(r'\.(\d+)', tag)
                line_num = int(line_num_m.group(1)) if line_num_m else 0

                # Extract words
                text = rest.replace('<%>', '').replace('<$>', '').strip()
                text = re.sub(r'@\d+;', '', text)
                text = re.sub(r'<[^>]*>', '', text)

                words_in_line = []
                for tok in re.split(r'[.\s]+', text):
                    for subtok in re.split(r',', tok):
                        c = clean_word(subtok.strip())
                        if c:
                            words_in_line.append(c)

                for wi, w in enumerate(words_in_line):
                    records.append({
                        'word': w,
                        'folio': folio,
                        'currier': currier,
                        'line_num': line_num,
                        'word_pos': wi,
                        'n_words_in_line': len(words_in_line),
                        'is_para_start': is_para_start and wi == 0,
                        'is_line_start': wi == 0,
                        'is_line_end': wi == len(words_in_line) - 1,
                    })

    return records


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL TOOLS
# ═══════════════════════════════════════════════════════════════════════

def pearson_r(x, y):
    if len(x) < 3:
        return 0.0
    x, y = np.array(x, dtype=float), np.array(y, dtype=float)
    mx, my = np.mean(x), np.mean(y)
    dx, dy = x - mx, y - my
    denom = np.sqrt(np.sum(dx**2) * np.sum(dy**2))
    if denom == 0:
        return 0.0
    return float(np.sum(dx * dy) / denom)


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 72)
    pr("  PHASE 94 — SLOT2 e-Extension: Productive Morphology")
    pr("              or Slot Independence?")
    pr("=" * 72)
    pr()

    # ── Step 1: Load data ────────────────────────────────────────────
    pr("STEP 1 — Load VMS words with positional metadata")
    pr("-" * 60)

    records = load_all_words_with_position()
    pr(f"  Total word tokens: {len(records)}")

    # Word frequency
    word_freq = Counter(r['word'] for r in records)
    all_types = set(word_freq.keys())
    pr(f"  Unique word types: {len(all_types)}")

    # Currier distribution
    currier_words = defaultdict(Counter)
    for r in records:
        if r['currier']:
            currier_words[r['currier']][r['word']] += 1
    pr(f"  A tokens: {sum(currier_words['A'].values())}")
    pr(f"  B tokens: {sum(currier_words['B'].values())}")
    pr()

    # ── Step 2: Find base words (empty SLOT2 + o) ───────────────────
    pr("STEP 2 — Identify base words (at least one chunk with empty SLOT2 + 'o')")
    pr("-" * 60)

    # For each word type, check if any chunk has empty SLOT2
    base_words = {}  # word -> list of (chunk_idx, ) for chunks with empty S2
    for wtype in all_types:
        chunks, slots_list, unparsed, glyphs = parse_word_into_chunks(wtype)
        if unparsed:
            continue
        extendable_chunks = []
        for ci, (chunk, slots) in enumerate(zip(chunks, slots_list)):
            if 2 not in slots and 3 in slots:
                extendable_chunks.append(ci)
        if extendable_chunks:
            base_words[wtype] = extendable_chunks

    pr(f"  Word types with ≥1 empty-SLOT2-with-o chunk: {len(base_words)}")
    pr(f"  (out of {len(all_types)} total types = {len(base_words)/len(all_types)*100:.1f}%)")
    pr()

    # ── Step 3: e-Extension pairing ─────────────────────────────────
    pr("STEP 3 — e-Extension pairing: For each base, does the e-extended")
    pr("         variant exist in the corpus?")
    pr("-" * 60)

    e_pairs = []  # (base_word, extended_word, chunk_idx)
    a_pairs = []  # same for a-extension
    no_e_partner = []

    for base, chunk_indices in base_words.items():
        e_extensions = make_e_extended(base)
        a_extensions = make_a_extended(base)

        found_any_e = False
        for ci, ext_word in e_extensions:
            if ext_word in all_types:
                e_pairs.append((base, ext_word, ci))
                found_any_e = True

        for ci, ext_word in a_extensions:
            if ext_word in all_types:
                a_pairs.append((base, ext_word, ci))

        if not found_any_e:
            no_e_partner.append(base)

    n_with_e = len(set(p[0] for p in e_pairs))
    n_with_a = len(set(p[0] for p in a_pairs))

    pr(f"  Base words with e-extended partner: {n_with_e}/{len(base_words)} "
       f"({n_with_e/len(base_words)*100:.1f}%)")
    pr(f"  Base words with a-extended partner: {n_with_a}/{len(base_words)} "
       f"({n_with_a/len(base_words)*100:.1f}%)")
    pr(f"  Total e-extension pairs: {len(e_pairs)}")
    pr(f"  Total a-extension pairs: {len(a_pairs)}")
    pr()

    # ── Step 4: Anti-circularity: random insertion control ───────────
    pr("STEP 4 — Anti-circularity: e-insertion at RANDOM positions")
    pr("-" * 60)
    pr("  If LOOP grammar is just capturing noise, inserting 'e' at")
    pr("  any position should produce equally many 'pairs'.")
    pr()

    # For each base word, try inserting 'e' at each possible glyph position
    # (not just SLOT2) and check if the result exists
    random_insertion_hits = Counter()  # position -> n hits
    slot2_only_hits = 0

    sample_bases = list(base_words.keys())
    for base in sample_bases:
        glyphs = eva_to_glyphs(base)
        n_g = len(glyphs)

        # SLOT2 insertion (what we already measured)
        e_exts = make_e_extended(base)
        for ci, ext in e_exts:
            if ext in all_types:
                slot2_only_hits += 1

        # Random position insertion: insert 'e' before each glyph
        for pos in range(n_g + 1):
            new_glyphs = glyphs[:pos] + ['e'] + glyphs[pos:]
            new_word = ''.join(new_glyphs)
            if new_word in all_types and new_word != base:
                random_insertion_hits[pos] += 1

    pr(f"  SLOT2 insertion hits: {slot2_only_hits}")
    pr(f"  Random-position insertion hits by position:")
    total_random = sum(random_insertion_hits.values())
    avg_random = total_random / max(1, max(random_insertion_hits.keys()) + 1) if random_insertion_hits else 0
    for pos in sorted(random_insertion_hits.keys())[:10]:
        pr(f"    Position {pos}: {random_insertion_hits[pos]} hits")
    if len(random_insertion_hits) > 10:
        pr(f"    ... ({len(random_insertion_hits)} positions total)")
    pr(f"  Total random-position hits: {total_random}")
    pr(f"  Average per position: {avg_random:.1f}")
    pr(f"  SLOT2-specific ratio: {slot2_only_hits / max(1, avg_random):.2f}x above random")
    pr()

    # ── Step 5: Frequency asymmetry ─────────────────────────────────
    pr("STEP 5 — Frequency asymmetry: Is base more frequent than extension?")
    pr("-" * 60)
    pr("  NL prediction: base (lemma) > extended (inflection)")
    pr("  Cipher prediction: no systematic asymmetry")
    pr()

    base_more = 0
    ext_more = 0
    equal_freq = 0
    freq_ratios = []

    # Deduplicate pairs by base word (take first pair per base)
    seen_bases = set()
    unique_pairs = []
    for base, ext, ci in e_pairs:
        if base not in seen_bases:
            seen_bases.add(base)
            unique_pairs.append((base, ext, ci))

    for base, ext, ci in unique_pairs:
        fb = word_freq[base]
        fe = word_freq[ext]
        if fb > fe:
            base_more += 1
        elif fe > fb:
            ext_more += 1
        else:
            equal_freq += 1
        ratio = fb / fe if fe > 0 else float('inf')
        freq_ratios.append((base, ext, fb, fe, ratio))

    pr(f"  Pairs where base freq > extended freq: {base_more}")
    pr(f"  Pairs where extended freq > base freq: {ext_more}")
    pr(f"  Equal frequency: {equal_freq}")
    pr(f"  Ratio (base>ext / ext>base): {base_more / max(1, ext_more):.2f}")
    pr()

    # Show top pairs by combined frequency
    freq_ratios.sort(key=lambda x: x[2] + x[3], reverse=True)
    pr(f"  Top 25 e-extension pairs (by combined frequency):")
    pr(f"  {'Base':<18} {'Freq':>5}  {'Extended':<18} {'Freq':>5}  {'Ratio':>6}")
    pr(f"  {'─'*18} {'─'*5}  {'─'*18} {'─'*5}  {'─'*6}")
    for base, ext, fb, fe, ratio in freq_ratios[:25]:
        ratio_s = f"{ratio:.1f}" if ratio < 100 else ">>1"
        winner = "◄ base" if fb > fe else "► ext" if fe > fb else "= equal"
        pr(f"  {base:<18} {fb:>5}  {ext:<18} {fe:>5}  {ratio_s:>6}  {winner}")
    pr()

    # Overall distribution of log(base_freq/ext_freq)
    log_ratios = [math.log2(r[4]) for r in freq_ratios if r[4] > 0 and r[4] != float('inf')]
    if log_ratios:
        mean_lr = np.mean(log_ratios)
        med_lr = np.median(log_ratios)
        pr(f"  log2(base_freq/ext_freq): mean={mean_lr:.2f}, median={med_lr:.2f}")
        pr(f"    (positive = base more frequent; NL expects positive)")
    pr()

    # ── Step 6: Selectional restrictions ─────────────────────────────
    pr("STEP 6 — Selectional restrictions: Do ALL bases get extended,")
    pr("         or is extension selective?")
    pr("-" * 60)

    # Bin bases by frequency and check extension rate per bin
    freq_bins = [(1, 1), (2, 5), (6, 20), (21, 100), (101, 10000)]
    pr(f"  {'Freq bin':>12}  {'N bases':>8}  {'With e-ext':>10}  {'Rate':>8}")
    pr(f"  {'─'*12}  {'─'*8}  {'─'*10}  {'─'*8}")

    bases_with_e = set(p[0] for p in e_pairs)
    for lo, hi in freq_bins:
        in_bin = [w for w in base_words if lo <= word_freq[w] <= hi]
        with_ext = [w for w in in_bin if w in bases_with_e]
        rate = len(with_ext) / len(in_bin) * 100 if in_bin else 0
        pr(f"  {lo:>5}-{hi:<5}  {len(in_bin):>8}  {len(with_ext):>10}  {rate:>7.1f}%")

    pr()
    pr("  NL prediction: LOWER frequency bases have LOWER extension rate")
    pr("  (rare words have fewer inflected forms in corpus)")
    pr("  Cipher prediction: extension rate ~uniform across frequency bins")
    pr()

    # ── Step 7: Currier A/B distribution of pairs ────────────────────
    pr("STEP 7 — Currier distribution: Do base/extended forms")
    pr("         concentrate in different Currier sections?")
    pr("-" * 60)

    base_in_A = 0
    base_in_B = 0
    ext_in_A = 0
    ext_in_B = 0

    for base, ext, ci in unique_pairs:
        base_in_A += currier_words['A'].get(base, 0)
        base_in_B += currier_words['B'].get(base, 0)
        ext_in_A += currier_words['A'].get(ext, 0)
        ext_in_B += currier_words['B'].get(ext, 0)

    total_base_ab = base_in_A + base_in_B
    total_ext_ab = ext_in_A + ext_in_B

    pr(f"  Base forms:     A={base_in_A:>5} ({base_in_A/max(1,total_base_ab)*100:.1f}%)  "
       f"B={base_in_B:>5} ({base_in_B/max(1,total_base_ab)*100:.1f}%)")
    pr(f"  Extended forms: A={ext_in_A:>5} ({ext_in_A/max(1,total_ext_ab)*100:.1f}%)  "
       f"B={ext_in_B:>5} ({ext_in_B/max(1,total_ext_ab)*100:.1f}%)")

    # Baseline: overall A/B ratio
    all_A = sum(currier_words['A'].values())
    all_B = sum(currier_words['B'].values())
    pr(f"  Corpus baseline: A={all_A/max(1,all_A+all_B)*100:.1f}%, B={all_B/max(1,all_A+all_B)*100:.1f}%")
    pr()

    # Phase 93 predicts: extended forms (SLOT2-filled) should be enriched in B
    ext_b_enrich = (ext_in_B / max(1, total_ext_ab)) / (all_B / max(1, all_A + all_B))
    base_a_enrich = (base_in_A / max(1, total_base_ab)) / (all_A / max(1, all_A + all_B))
    pr(f"  Extended-form B enrichment: {ext_b_enrich:.2f}x")
    pr(f"  Base-form A enrichment: {base_a_enrich:.2f}x")
    pr(f"  (Phase 93 predicts: extended enriched in B, base enriched in A)")
    pr()

    # ── Step 8: Line position analysis ───────────────────────────────
    pr("STEP 8 — Positional distribution: Base vs extended by line position")
    pr("-" * 60)

    # Build word->position stats
    word_positions = defaultdict(lambda: {'line_start': 0, 'line_end': 0,
                                          'mid': 0, 'para_start': 0, 'total': 0})
    for r in records:
        w = r['word']
        word_positions[w]['total'] += 1
        if r['is_para_start']:
            word_positions[w]['para_start'] += 1
        if r['is_line_start']:
            word_positions[w]['line_start'] += 1
        elif r['is_line_end']:
            word_positions[w]['line_end'] += 1
        else:
            word_positions[w]['mid'] += 1

    # Aggregate for base vs extended
    base_pos = Counter()
    ext_pos = Counter()
    for base, ext, ci in unique_pairs:
        for pos_key in ['line_start', 'line_end', 'mid', 'para_start']:
            base_pos[pos_key] += word_positions[base][pos_key]
            ext_pos[pos_key] += word_positions[ext][pos_key]
        base_pos['total'] += word_positions[base]['total']
        ext_pos['total'] += word_positions[ext]['total']

    pr(f"  {'Position':<15} {'Base':>8} {'%':>7}  {'Extended':>8} {'%':>7}")
    pr(f"  {'─'*15} {'─'*8} {'─'*7}  {'─'*8} {'─'*7}")
    for pk in ['line_start', 'mid', 'line_end', 'para_start']:
        bp = base_pos[pk] / max(1, base_pos['total']) * 100
        ep = ext_pos[pk] / max(1, ext_pos['total']) * 100
        pr(f"  {pk:<15} {base_pos[pk]:>8} {bp:>6.1f}%  {ext_pos[pk]:>8} {ep:>6.1f}%")
    pr(f"  {'total':<15} {base_pos['total']:>8}          {ext_pos['total']:>8}")
    pr()

    # ── Step 9: Folio co-occurrence ──────────────────────────────────
    pr("STEP 9 — Folio co-occurrence: Do base and extended forms")
    pr("         appear in the same folios?")
    pr("-" * 60)

    # For each pair, check if both appear in the same folio
    word_folio_sets = defaultdict(set)
    for r in records:
        word_folio_sets[r['word']].add(r['folio'])

    cooccur_count = 0
    separate_count = 0
    for base, ext, ci in unique_pairs:
        base_folios = word_folio_sets[base]
        ext_folios = word_folio_sets[ext]
        shared = base_folios & ext_folios
        if shared:
            cooccur_count += 1
        else:
            separate_count += 1

    pr(f"  Pairs co-occurring in ≥1 folio: {cooccur_count}/{len(unique_pairs)} "
       f"({cooccur_count/max(1,len(unique_pairs))*100:.1f}%)")
    pr(f"  Pairs in completely separate folios: {separate_count}/{len(unique_pairs)} "
       f"({separate_count/max(1,len(unique_pairs))*100:.1f}%)")
    pr()

    # Compute expected co-occurrence under random distribution
    n_folios_total = len(set(r['folio'] for r in records))
    cooccur_expected = 0
    for base, ext, ci in unique_pairs:
        nb = len(word_folio_sets[base])
        ne = len(word_folio_sets[ext])
        # P(overlap) under independence ≈ 1 - P(no overlap)
        # P(no overlap) = C(N-nb, ne) / C(N, ne) ≈ ((N-nb)/N)^ne for large N
        p_no_overlap = 1.0
        for _ in range(min(ne, 30)):  # approximate
            p_no_overlap *= max(0, (n_folios_total - nb)) / n_folios_total
        cooccur_expected += 1 - p_no_overlap

    pr(f"  Expected co-occurrence under independence: {cooccur_expected:.1f}")
    pr(f"  Observed / expected ratio: {cooccur_count / max(0.01, cooccur_expected):.2f}")
    pr(f"  (>1 = pairs co-occur MORE than chance; supports morphological relationship)")
    pr()

    # ── Step 10: NL Latin baseline ───────────────────────────────────
    pr("STEP 10 — NL baseline: 'vowel-extension' pairing in Latin")
    pr("-" * 60)

    # Load Latin text and measure analogous vowel insertion pairing
    latin_files = [
        DATA_DIR / 'latin_texts' / 'caesar.txt',
        DATA_DIR / 'latin_texts' / 'galen.txt',
        DATA_DIR / 'latin_texts' / 'apicius.txt',
    ]

    for lf in latin_files:
        if not lf.exists():
            continue
        with open(lf, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read().lower()
        # Tokenize Latin
        lat_words = re.findall(r'[a-z]+', text)
        lat_types = set(lat_words)
        lat_freq = Counter(lat_words)

        # Find words where inserting 'e' before a vowel creates another word
        vowels = set('aeiou')
        e_insert_pairs = 0
        base_count = 0
        for w in lat_types:
            has_vowel = any(c in vowels for c in w)
            if not has_vowel:
                continue
            base_count += 1
            found = False
            for i, c in enumerate(w):
                if c in vowels and c != 'e':
                    # Insert 'e' before this vowel
                    new_w = w[:i] + 'e' + w[i:]
                    if new_w in lat_types:
                        found = True
                        break
            if found:
                e_insert_pairs += 1

        rate = e_insert_pairs / base_count * 100 if base_count else 0
        pr(f"  {lf.stem:<15}: {len(lat_types):>6} types, "
           f"{e_insert_pairs:>4} vowel-insertion pairs ({rate:.1f}%)")

    pr()

    # ── Step 11: Petrasti's specific examples verification ───────────
    pr("STEP 11 — Verify Petrasti's specific examples from thread-5216")
    pr("-" * 60)

    petrasti_examples = [
        ('chor', 'cheor'),
        ('daiin', 'deaiin'),
        ('kor', 'keor'),
        ('cho', 'cheo'),
        ('chol', 'cheol'),
        ('kaiin', 'keaiin'),
        ('dor', 'deor'),
        ('eees', 'eees'),  # unchanged — base form
    ]

    pr(f"  {'Base':<15} {'Freq':>5}  {'Extended':<15} {'Freq':>5}  {'In corpus?':>10}")
    pr(f"  {'─'*15} {'─'*5}  {'─'*15} {'─'*5}  {'─'*10}")
    for base, ext in petrasti_examples:
        fb = word_freq.get(base, 0)
        fe = word_freq.get(ext, 0)
        status = 'BOTH' if fb > 0 and fe > 0 else 'base only' if fb > 0 else 'ext only' if fe > 0 else 'NEITHER'
        pr(f"  {base:<15} {fb:>5}  {ext:<15} {fe:>5}  {status:>10}")

    # Petrasti's prefix examples
    pr()
    pr("  Petrasti's prefix paradigm for 'daiin':")
    prefix_forms = ['daiin', 'deaiin', 'odaiin', 'ydaiin', 'qodaiin',
                    'chodaiin', 'todaiin', 'tedaiin', 'chedaiin',
                    'sodaiin', 'oldaiin', 'cheodaiin']
    for pf in prefix_forms:
        freq = word_freq.get(pf, 0)
        marker = '✓' if freq > 0 else '✗'
        pr(f"    {marker} {pf:<20} freq={freq}")
    pr()

    # ── SYNTHESIS ────────────────────────────────────────────────────
    pr("=" * 72)
    pr("  SYNTHESIS & VERDICT")
    pr("=" * 72)
    pr()

    # Compute summary metrics
    pairing_rate = n_with_e / len(base_words) * 100 if base_words else 0
    freq_direction = base_more / max(1, ext_more)
    currier_shift = ext_b_enrich

    pr(f"  KEY METRICS:")
    pr(f"  1. e-Extension pairing rate: {pairing_rate:.1f}% of bases have e-partner")
    pr(f"  2. Frequency asymmetry: base>ext {freq_direction:.2f}x more often")
    if log_ratios:
        pr(f"     Median log2(base/ext): {med_lr:.2f}")
    pr(f"  3. Selectional restrictions: {'YES' if pairing_rate < 50 else 'WEAK' if pairing_rate < 80 else 'NO'}")
    pr(f"  4. Currier B enrichment of extended forms: {currier_shift:.2f}x")
    pr(f"  5. Folio co-occurrence ratio (obs/exp): {cooccur_count / max(0.01, cooccur_expected):.2f}")
    pr()

    # Verdict
    morphology_score = 0
    if pairing_rate < 50:
        morphology_score += 2  # strong selectional restriction
    elif pairing_rate < 80:
        morphology_score += 1
    if freq_direction > 1.5:
        morphology_score += 2  # strong frequency asymmetry
    elif freq_direction > 1.2:
        morphology_score += 1
    if currier_shift > 1.2:
        morphology_score += 1  # distributional asymmetry
    if cooccur_count / max(0.01, cooccur_expected) > 1.3:
        morphology_score += 1

    if morphology_score >= 5:
        verdict = 'PRODUCTIVE_MORPHOLOGY'
        pr("  VERDICT: PRODUCTIVE_MORPHOLOGY")
        pr("  The e-extension behaves like NL inflectional morphology:")
        pr("  selective, frequency-asymmetric, and positionally constrained.")
    elif morphology_score >= 3:
        verdict = 'MORPHOLOGY_LEANING'
        pr("  VERDICT: MORPHOLOGY_LEANING")
        pr("  The e-extension shows some NL-like morphological properties")
        pr("  but not all diagnostics are clear-cut.")
    elif morphology_score >= 1:
        verdict = 'AMBIGUOUS'
        pr("  VERDICT: AMBIGUOUS")
        pr("  e-extension patterns don't clearly distinguish morphology")
        pr("  from independent slot filling.")
    else:
        verdict = 'INDEPENDENT_SLOT_FILLING'
        pr("  VERDICT: INDEPENDENT_SLOT_FILLING")
        pr("  SLOT2 filling appears to operate independently, more")
        pr("  consistent with cipher-like slot combination.")

    pr()
    pr("  SKEPTICISM NOTES:")
    pr("  - LOOP grammar DEFINES SLOT2 as optional. Some pairing is")
    pr("    guaranteed by construction. The anti-circularity test (Step 4)")
    pr("    measures whether SLOT2 pairing exceeds random-position insertion.")
    pr("  - Frequency asymmetry could arise from type-frequency correlation:")
    pr("    shorter words (empty SLOT2) may simply be more frequent by Zipf.")
    pr("  - Co-occurrence in folios is expected for common words regardless")
    pr("    of morphological relationship.")
    pr("  - Petrasti's examples are cherry-picked; the systematic rate matters.")
    pr()

    # Save results
    results = {
        'phase': 94,
        'n_base_words': len(base_words),
        'n_with_e_partner': n_with_e,
        'n_with_a_partner': n_with_a,
        'pairing_rate_e': round(pairing_rate, 2),
        'total_e_pairs': len(e_pairs),
        'total_a_pairs': len(a_pairs),
        'freq_base_gt_ext': base_more,
        'freq_ext_gt_base': ext_more,
        'freq_equal': equal_freq,
        'median_log2_ratio': round(float(med_lr), 3) if log_ratios else None,
        'slot2_insertion_hits': slot2_only_hits,
        'random_insertion_avg': round(avg_random, 1),
        'ext_b_enrichment': round(ext_b_enrich, 3),
        'base_a_enrichment': round(base_a_enrich, 3),
        'folio_cooccur_observed': cooccur_count,
        'folio_cooccur_expected': round(cooccur_expected, 1),
        'morphology_score': morphology_score,
        'verdict': verdict,
    }

    out_path = RESULTS_DIR / 'phase94_e_extension.json'
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    pr(f"  Results saved to {out_path}")

    txt_path = RESULTS_DIR / 'phase94_e_extension.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Full output saved to {txt_path}")


if __name__ == '__main__':
    main()
