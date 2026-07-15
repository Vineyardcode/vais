#!/usr/bin/env python3
"""
Phase 77 — Gallows Positional Ecology: Do Paragraph-Initial Gallows
         Function Differently from Body-Text Gallows?

═══════════════════════════════════════════════════════════════════════

CONTEXT: Phase 76 showed vernacular recipe texts CAN produce VMS-level
paragraph-initial concentration (Italian 86%, French 79%, English 74%).
This raises the question: if gallows are just letters appearing at
paragraph starts (like 'T' in 'Take'), they should behave THE SAME
at paragraph starts as elsewhere. If they're functionally different
(structural markers vs letters), their contexts should DIVERGE.

TESTS:

A. SUCCESSOR DIVERGENCE — For each gallows (p,t,k,f), compare:
   P(next_glyph | gallows at paragraph-initial position) vs
   P(next_glyph | gallows at body-text position)
   Measured by Jensen-Shannon divergence. High JSD = different function.

B. WORD-FORM OVERLAP — What fraction of gallows words at paragraph starts
   also appear in body text? Break down per gallows letter.
   If gallows = letters → high overlap expected (same words, same positions)
   If gallows = markers → low overlap (paragraph-initial vocabulary is distinct)

C. CHARACTER-POSITION PROFILE — In body text, are gallows word-initial
   (position 1) or also word-medial (position 2+)?
   If gallows = letters → expect distribution across positions
   If gallows = markers (at para start only) → body-text gallows should
   actually behave differently since they're in a different role

D. COMPOUND vs PLAIN GALLOWS — Compare cph/cfh/ckh/cth with p/f/k/t.
   Do compound (bench) gallows EVER appear at paragraph starts?
   If only PLAIN gallows do paragraph-start duty → the visual form matters,
   consistent with gallows-as-marker or gallows-as-capital-letter.

E. BODY-TEXT GALLOWS RATIO vs PARA-INITIAL RATIO — Within body text
   (excluding paragraph starts), what's the p:t:k:f ratio? Compare
   with the paragraph-initial ratio. Test by section.
   If same role → ratios should be similar
   If different role → ratios should diverge

F. PER-SECTION ANALYSIS — Do herbal/recipe/astro sections show different
   patterns? The astro section is key: it has NO p,k,f at paragraph starts
   (only t). Do p,k,f appear in astro body text?

CRITICAL SKEPTICISM:
  - Phase 71 found 79% of paragraph-initial words are unique to that
    position. That 79% is already very high, but we need to check if
    this is BECAUSE of gallows specificity or despite it.
  - EVA transcription choices may affect results (multi-glyph sequences).
  - Small section sizes (astro: 26 paras) limit statistical power.
"""

import re, sys, io, math, json, os
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import clean_word, eva_to_glyphs, folio_section_v2 as folio_section

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

SEED = 42
np.random.seed(SEED)

# ═══════════════════════════════════════════════════════════════════════
# EVA GLYPH PARSING (from Phase 74)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']
PLAIN_GALLOWS = {'p', 't', 'k', 'f'}
COMPOUND_GALLOWS = set(GALLOWS_TRI)
ALL_GALLOWS = PLAIN_GALLOWS | COMPOUND_GALLOWS | {'th', 'kh', 'ph', 'fh'}



def first_glyph(word):
    g = eva_to_glyphs(word)
    return g[0] if g else ''

def first_char(word):
    return word[0].lower() if word else ''

# ═══════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════

def folio_number(fname):
    m = re.match(r'f(\d+)', fname)
    return int(m.group(1)) if m else 0



def parse_all_folios():
    """Parse ALL folio files, returning structured paragraph and word data.

    Returns:
      paragraphs: list of dicts, each with:
        section, folio, words, first_word, para_position (sequential)
      body_words: list of (word, section, folio, word_position_in_para)
        for all NON-paragraph-initial words
      para_init_words: list of (word, section, folio)
        for paragraph-initial words only
    """
    paragraphs = []
    body_words = []
    para_init_words = []

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: folio_number(p.stem))

    for filepath in folio_files:
        fnum = folio_number(filepath.stem)
        section = folio_section(fnum)

        current_para_words = []
        current_para_open = False

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        for line in lines:
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

            is_para_start = '@P' in tag or '<%>' in rest
            is_para_end = '<$>' in rest

            text = rest.replace('<%>', '').replace('<$>', '').strip()
            # Remove inline annotations like @252;
            text = re.sub(r'@\d+;', '', text)
            # Remove <-> and similar inline tags
            text = re.sub(r'<[^>]*>', '', text)

            words = []
            for tok in re.split(r'[.\s]+', text):
                for subtok in re.split(r',', tok):
                    subtok = subtok.strip()
                    cleaned = clean_word(subtok)
                    if cleaned and len(cleaned) >= 1:
                        words.append(cleaned)

            if not words:
                continue

            # Close previous para if new one starts
            if is_para_start and current_para_open and current_para_words:
                _save_paragraph(paragraphs, body_words, para_init_words,
                                current_para_words, section, filepath.stem)
                current_para_words = []

            if is_para_start:
                current_para_open = True
                current_para_words = list(words)
            elif current_para_open:
                current_para_words.extend(words)

            if is_para_end and current_para_open and current_para_words:
                _save_paragraph(paragraphs, body_words, para_init_words,
                                current_para_words, section, filepath.stem)
                current_para_words = []
                current_para_open = False

        # Close any open paragraph at end of file
        if current_para_open and current_para_words:
            _save_paragraph(paragraphs, body_words, para_init_words,
                            current_para_words, section, filepath.stem)

    return paragraphs, body_words, para_init_words


def _save_paragraph(paragraphs, body_words, para_init_words,
                    words, section, folio):
    """Save a complete paragraph."""
    if not words:
        return

    paragraphs.append({
        'section': section,
        'folio': folio,
        'words': words,
        'n_words': len(words),
        'first_word': words[0],
    })

    # First word → para-initial
    para_init_words.append((words[0], section, folio))

    # Remaining words → body
    for i, w in enumerate(words[1:], 1):
        body_words.append((w, section, folio, i))


# ═══════════════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def jsd(p_dist, q_dist, all_keys=None):
    """Jensen-Shannon Divergence between two distributions (dicts)."""
    if all_keys is None:
        all_keys = set(p_dist.keys()) | set(q_dist.keys())
    p_total = sum(p_dist.values())
    q_total = sum(q_dist.values())
    if p_total == 0 or q_total == 0:
        return float('nan')
    m = {}
    for k in all_keys:
        p_val = p_dist.get(k, 0) / p_total
        q_val = q_dist.get(k, 0) / q_total
        m[k] = (p_val + q_val) / 2

    def kl(dist, total, m_dist):
        val = 0
        for k in all_keys:
            p_k = dist.get(k, 0) / total
            m_k = m_dist.get(k, 0)
            if p_k > 0 and m_k > 0:
                val += p_k * math.log2(p_k / m_k)
        return val

    return (kl(p_dist, p_total, m) + kl(q_dist, q_total, m)) / 2


def entropy(counter):
    """Shannon entropy in bits from a Counter."""
    total = sum(counter.values())
    if total == 0:
        return 0
    h = 0
    for c in counter.values():
        if c > 0:
            p = c / total
            h -= p * math.log2(p)
    return h


# ═══════════════════════════════════════════════════════════════════════
# TEST A: SUCCESSOR DIVERGENCE
# ═══════════════════════════════════════════════════════════════════════

def test_a_successor_divergence(paragraphs, body_words, para_init_words):
    pr(f"\n{'═'*70}")
    pr(f"TEST A: SUCCESSOR DIVERGENCE — Same glyph, different contexts")
    pr(f"{'═'*70}")
    pr(f"""
For each gallows, compare what glyph FOLLOWS it when it appears at
paragraph start vs in body text. If gallows have ONE function, the
successor distributions should be similar (low JSD). If the paragraph-
initial function is different, JSD should be high.
""")

    # Build successor distributions
    # At paragraph start: gallows is the first glyph, successor is the second glyph
    para_init_succ = defaultdict(Counter)  # gallows → successor counts
    for para in paragraphs:
        first_w = para['first_word']
        glyphs = eva_to_glyphs(first_w)
        if len(glyphs) >= 2:
            fg = glyphs[0]
            if fg in PLAIN_GALLOWS:
                para_init_succ[fg][glyphs[1]] += 1

    # In body text: gallows anywhere in a word, successor is next glyph in same word
    body_succ = defaultdict(Counter)
    for (word, section, folio, pos) in body_words:
        glyphs = eva_to_glyphs(word)
        for i, g in enumerate(glyphs[:-1]):
            if g in PLAIN_GALLOWS:
                body_succ[g][glyphs[i+1]] += 1

    # Also: gallows as first glyph of NON-paragraph-initial words in body
    body_initial_succ = defaultdict(Counter)
    for (word, section, folio, pos) in body_words:
        glyphs = eva_to_glyphs(word)
        if len(glyphs) >= 2 and glyphs[0] in PLAIN_GALLOWS:
            body_initial_succ[glyphs[0]][glyphs[1]] += 1

    pr(f"  {'Gallows':>8s} | {'n(para-init)':>12s} {'n(body-all)':>12s} {'n(body-init)':>12s} | "
       f"{'JSD(init/body)':>14s} {'JSD(init/bodyW1)':>16s}")
    pr(f"  {'─'*8} | {'─'*12} {'─'*12} {'─'*12} | {'─'*14} {'─'*16}")

    for g in ['p', 't', 'k', 'f']:
        n_pi = sum(para_init_succ[g].values())
        n_ba = sum(body_succ[g].values())
        n_bi = sum(body_initial_succ[g].values())

        jsd_all = jsd(para_init_succ[g], body_succ[g]) if n_pi > 0 and n_ba > 0 else float('nan')
        jsd_init = jsd(para_init_succ[g], body_initial_succ[g]) if n_pi > 0 and n_bi > 0 else float('nan')

        pr(f"  {g:>8s} | {n_pi:>12d} {n_ba:>12d} {n_bi:>12d} | "
           f"{jsd_all:>14.4f} {jsd_init:>16.4f}")

    # Show the actual distributions for the most informative comparison
    for g in ['p', 't', 'k', 'f']:
        n_pi = sum(para_init_succ[g].values())
        n_bi = sum(body_initial_succ[g].values())
        if n_pi < 5:
            continue

        pr(f"\n  Gallows '{g}' successor distributions:")
        all_keys = set(para_init_succ[g].keys()) | set(body_initial_succ[g].keys())
        pr(f"    {'Succ':>6s} | {'Para-init':>10s} {'%':>6s} | {'Body-init':>10s} {'%':>6s}")
        for key in sorted(all_keys, key=lambda k: -(para_init_succ[g].get(k, 0) + body_initial_succ[g].get(k, 0))):
            pc = para_init_succ[g].get(key, 0)
            bc = body_initial_succ[g].get(key, 0)
            pp = pc/n_pi*100 if n_pi > 0 else 0
            bp = bc/n_bi*100 if n_bi > 0 else 0
            if pc + bc >= 3:
                pr(f"    {key:>6s} | {pc:>10d} {pp:>5.1f}% | {bc:>10d} {bp:>5.1f}%")

    return para_init_succ, body_succ, body_initial_succ


# ═══════════════════════════════════════════════════════════════════════
# TEST B: WORD-FORM OVERLAP
# ═══════════════════════════════════════════════════════════════════════

def test_b_word_overlap(paragraphs, body_words, para_init_words):
    pr(f"\n{'═'*70}")
    pr(f"TEST B: WORD-FORM OVERLAP — Do paragraph-initial words also appear in body?")
    pr(f"{'═'*70}")
    pr(f"""
If gallows = letters, the words starting with gallows at paragraph starts
should also appear throughout body text (like 'Take' appears both at
recipe starts and mid-recipe). If gallows = special markers, paragraph-
initial words would be a SEPARATE vocabulary.
""")

    # Collect word forms
    para_init_set = set()
    para_init_by_gallows = defaultdict(set)
    para_init_counter = Counter()
    for (word, section, folio) in para_init_words:
        fg = first_char(word)
        para_init_set.add(word)
        para_init_counter[word] += 1
        if fg in PLAIN_GALLOWS:
            para_init_by_gallows[fg].add(word)

    body_set = set()
    body_by_first_gallows = defaultdict(set)
    body_counter = Counter()
    for (word, section, folio, pos) in body_words:
        fg = first_char(word)
        body_set.add(word)
        body_counter[word] += 1
        if fg in PLAIN_GALLOWS:
            body_by_first_gallows[fg].add(word)

    # Overall overlap
    overlap = para_init_set & body_set
    only_para = para_init_set - body_set
    only_body = body_set - para_init_set

    pr(f"  Overall:")
    pr(f"    Unique paragraph-initial word forms: {len(para_init_set)}")
    pr(f"    Unique body word forms:              {len(body_set)}")
    pr(f"    Overlap (appear in both):            {len(overlap)} ({len(overlap)/len(para_init_set)*100:.1f}% of para-init)")
    pr(f"    Para-init only:                      {len(only_para)} ({len(only_para)/len(para_init_set)*100:.1f}%)")

    # Per gallows letter
    pr(f"\n  Per gallows letter:")
    pr(f"    {'Gallows':>8s} | {'Para-init forms':>15s} {'Body forms':>12s} {'Overlap':>8s} {'Overlap%':>8s} | {'Para-init only':>14s}")
    pr(f"    {'─'*8} | {'─'*15} {'─'*12} {'─'*8} {'─'*8} | {'─'*14}")

    for g in ['p', 't', 'k', 'f']:
        pi_set = para_init_by_gallows[g]
        bo_set = body_by_first_gallows[g]
        ov = pi_set & bo_set
        pio = pi_set - bo_set
        pr(f"    {g:>8s} | {len(pi_set):>15d} {len(bo_set):>12d} {len(ov):>8d} "
           f"{len(ov)/max(1,len(pi_set))*100:>7.1f}% | {len(pio):>14d}")

    # Show the most common para-init words and whether they appear in body
    pr(f"\n  TOP 25 paragraph-initial words:")
    pr(f"    {'Rank':>4s} {'Word':>15s} {'Para-init#':>10s} {'Body#':>8s} {'Ratio':>8s} {'Status':>10s}")
    for i, (word, count) in enumerate(para_init_counter.most_common(25)):
        body_n = body_counter.get(word, 0)
        fg = first_char(word)
        gallows_mark = '★' if fg in PLAIN_GALLOWS else ' '
        ratio = body_n / count if count > 0 else 0
        status = 'SHARED' if word in overlap else 'PARA-ONLY'
        pr(f"    {i+1:>4d} {word:>15s} {count:>10d} {body_n:>8d} {ratio:>7.1f}x {status:>10s} {gallows_mark}")

    return para_init_set, body_set, overlap, only_para


# ═══════════════════════════════════════════════════════════════════════
# TEST C: CHARACTER POSITION PROFILE
# ═══════════════════════════════════════════════════════════════════════

def test_c_position_profile(body_words):
    pr(f"\n{'═'*70}")
    pr(f"TEST C: CHARACTER-POSITION PROFILE — Where do gallows appear in words?")
    pr(f"{'═'*70}")
    pr(f"""
In body text, are gallows primarily word-INITIAL (position 1) or do they
also appear word-medially (position 2, 3, ...)?

If gallows = regular letters → expect some medial/final appearances
If gallows = word-initial markers only → expect position-1 dominance

Also compare plain gallows (p,t,k,f) with compound gallows (cph,cfh,ckh,cth).
""")

    # Count positions for each gallows type
    plain_pos = defaultdict(Counter)   # gallows → position → count
    compound_pos = defaultdict(Counter)
    total_by_pos = Counter()

    for (word, section, folio, wpos) in body_words:
        glyphs = eva_to_glyphs(word)
        for i, g in enumerate(glyphs):
            pos = i + 1
            total_by_pos[pos] += 1
            if g in PLAIN_GALLOWS:
                plain_pos[g][pos] += 1
            elif g in COMPOUND_GALLOWS:
                compound_pos[g][pos] += 1

    pr(f"\n  PLAIN GALLOWS position profile (body text only):")
    pr(f"    {'Glyph':>6s} | {'Pos 1':>8s} {'Pos 2':>8s} {'Pos 3':>8s} {'Pos 4':>8s} {'Pos 5+':>8s} | {'Total':>8s} {'%Pos1':>6s}")
    pr(f"    {'─'*6} | {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} | {'─'*8} {'─'*6}")
    for g in ['p', 't', 'k', 'f']:
        dist = plain_pos[g]
        total = sum(dist.values())
        pos5 = sum(v for k, v in dist.items() if k >= 5)
        p1_pct = dist.get(1, 0) / max(total, 1) * 100
        pr(f"    {g:>6s} | {dist.get(1,0):>8d} {dist.get(2,0):>8d} {dist.get(3,0):>8d} {dist.get(4,0):>8d} {pos5:>8d} | {total:>8d} {p1_pct:>5.1f}%")

    pr(f"\n  COMPOUND GALLOWS position profile (body text only):")
    pr(f"    {'Glyph':>6s} | {'Pos 1':>8s} {'Pos 2':>8s} {'Pos 3':>8s} {'Pos 4':>8s} {'Pos 5+':>8s} | {'Total':>8s} {'%Pos1':>6s}")
    pr(f"    {'─'*6} | {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} | {'─'*8} {'─'*6}")
    for g in sorted(COMPOUND_GALLOWS):
        dist = compound_pos[g]
        total = sum(dist.values())
        if total > 0:
            pos5 = sum(v for k, v in dist.items() if k >= 5)
            p1_pct = dist.get(1, 0) / max(total, 1) * 100
            pr(f"    {g:>6s} | {dist.get(1,0):>8d} {dist.get(2,0):>8d} {dist.get(3,0):>8d} {dist.get(4,0):>8d} {pos5:>8d} | {total:>8d} {p1_pct:>5.1f}%")

    return plain_pos, compound_pos


# ═══════════════════════════════════════════════════════════════════════
# TEST D: COMPOUND vs PLAIN AT PARAGRAPH STARTS
# ═══════════════════════════════════════════════════════════════════════

def test_d_compound_at_para_starts(paragraphs):
    pr(f"\n{'═'*70}")
    pr(f"TEST D: COMPOUND vs PLAIN GALLOWS AT PARAGRAPH STARTS")
    pr(f"{'═'*70}")
    pr(f"""
If paragraph-initial gallows are just the first letter of a word, BOTH plain
(p,t,k,f) AND compound (cph,cfh,ckh,cth) gallows should appear — compound
gallows are just gallows preceded by 'c'. If the paragraph-start function is
specific to the PLAIN gallows visual form (decorative capitals?), compounds
should be absent or rare at paragraph starts.
""")

    plain_count = Counter()
    compound_count = Counter()
    other_count = Counter()

    for para in paragraphs:
        fg = first_glyph(para['first_word'])
        if fg in PLAIN_GALLOWS:
            plain_count[fg] += 1
        elif fg in COMPOUND_GALLOWS:
            compound_count[fg] += 1
        else:
            other_count[fg] += 1

    total = len(paragraphs)
    plain_total = sum(plain_count.values())
    compound_total = sum(compound_count.values())
    other_total = sum(other_count.values())

    pr(f"  Total paragraphs: {total}")
    pr(f"  Start with PLAIN gallows:    {plain_total} ({plain_total/total*100:.1f}%)")
    for g in ['p', 't', 'k', 'f']:
        pr(f"    {g}: {plain_count[g]} ({plain_count[g]/total*100:.1f}%)")
    pr(f"  Start with COMPOUND gallows: {compound_total} ({compound_total/total*100:.1f}%)")
    for g in sorted(COMPOUND_GALLOWS):
        if compound_count[g] > 0:
            pr(f"    {g}: {compound_count[g]} ({compound_count[g]/total*100:.1f}%)")
    pr(f"  Start with other:            {other_total} ({other_total/total*100:.1f}%)")

    # Compare body-text rates
    # If compound gallows are X% of all word-initial glyphs in body text,
    # they should be ~X% of paragraph-initial glyphs IF they're the same thing
    pr(f"\n  SIGNIFICANCE: If gallows are just letters, compound gallows")
    pr(f"  should appear at paragraph starts at their body-text word-initial rate.")

    return plain_count, compound_count, other_count


# ═══════════════════════════════════════════════════════════════════════
# TEST E: BODY-TEXT GALLOWS RATIO vs PARA-INITIAL RATIO
# ═══════════════════════════════════════════════════════════════════════

def test_e_ratio_comparison(paragraphs, body_words, para_init_words):
    pr(f"\n{'═'*70}")
    pr(f"TEST E: GALLOWS RATIO — Paragraph-initial vs Body-text")
    pr(f"{'═'*70}")
    pr(f"""
If gallows serve the SAME function everywhere, their proportions (p:t:k:f)
should be similar at paragraph starts and in body text. If the paragraph-
initial role is different (structural markers), the ratios should diverge.
""")

    # Para-initial gallows ratio (first glyph of first word)
    pi_gallows = Counter()
    pi_total = 0
    for (word, section, folio) in para_init_words:
        fg = first_glyph(word)
        if fg in PLAIN_GALLOWS:
            pi_gallows[fg] += 1
        pi_total += 1

    # Body-text: gallows as first glyph of ANY non-para-initial word
    body_word_init_gallows = Counter()
    body_word_total = 0
    for (word, section, folio, pos) in body_words:
        fg = first_glyph(word)
        if fg in PLAIN_GALLOWS:
            body_word_init_gallows[fg] += 1
        body_word_total += 1

    # Body-text: gallows at ANY character position
    body_char_gallows = Counter()
    body_char_total = 0
    for (word, section, folio, pos) in body_words:
        for g in eva_to_glyphs(word):
            if g in PLAIN_GALLOWS:
                body_char_gallows[g] += 1
            body_char_total += 1

    pr(f"\n  {'Context':>25s} | ", end='')
    for g in ['p', 't', 'k', 'f']:
        pr(f"{'  '+g:>8s}", end='')
    pr(f" | {'Total':>8s} {'Gal%':>6s}")
    pr(f"  {'─'*25} | {'─'*32} | {'─'*8} {'─'*6}")

    # Para-initial
    pi_gal_total = sum(pi_gallows.values())
    pr(f"  {'Para-initial (1st glyph)':>25s} | ", end='')
    for g in ['p', 't', 'k', 'f']:
        pct = pi_gallows[g] / pi_total * 100 if pi_total > 0 else 0
        pr(f"{pct:>7.1f}%", end='')
    pr(f" | {pi_gal_total:>8d} {pi_gal_total/pi_total*100:>5.1f}%")

    # Body word-initial
    bwi_gal_total = sum(body_word_init_gallows.values())
    pr(f"  {'Body word-initial':>25s} | ", end='')
    for g in ['p', 't', 'k', 'f']:
        pct = body_word_init_gallows[g] / body_word_total * 100 if body_word_total > 0 else 0
        pr(f"{pct:>7.1f}%", end='')
    pr(f" | {bwi_gal_total:>8d} {bwi_gal_total/body_word_total*100:>5.1f}%")

    # Body any-position
    bca_gal_total = sum(body_char_gallows.values())
    pr(f"  {'Body any-char-position':>25s} | ", end='')
    for g in ['p', 't', 'k', 'f']:
        pct = body_char_gallows[g] / body_char_total * 100 if body_char_total > 0 else 0
        pr(f"{pct:>7.1f}%", end='')
    pr(f" | {bca_gal_total:>8d} {bca_gal_total/body_char_total*100:>5.1f}%")

    # Relative ratios within gallows
    pr(f"\n  WITHIN-GALLOWS PROPORTIONS (normalized to sum=1):")
    pr(f"  {'Context':>25s} | ", end='')
    for g in ['p', 't', 'k', 'f']:
        pr(f"{'  '+g:>8s}", end='')
    pr()

    for label, counter in [
        ('Para-initial', pi_gallows),
        ('Body word-initial', body_word_init_gallows),
        ('Body any-position', body_char_gallows),
    ]:
        total_g = sum(counter[g] for g in PLAIN_GALLOWS)
        pr(f"  {label:>25s} | ", end='')
        for g in ['p', 't', 'k', 'f']:
            pct = counter[g] / total_g * 100 if total_g > 0 else 0
            pr(f"{pct:>7.1f}%", end='')
        pr()

    # JSD between para-initial and body distributions
    jsd_wi = jsd(
        {g: pi_gallows[g] for g in PLAIN_GALLOWS},
        {g: body_word_init_gallows[g] for g in PLAIN_GALLOWS}
    )
    jsd_ca = jsd(
        {g: pi_gallows[g] for g in PLAIN_GALLOWS},
        {g: body_char_gallows[g] for g in PLAIN_GALLOWS}
    )
    pr(f"\n  JSD(para-initial vs body-word-initial): {jsd_wi:.4f}")
    pr(f"  JSD(para-initial vs body-any-position):  {jsd_ca:.4f}")
    pr(f"  (0 = identical, 1 = maximally different)")

    # Per-section analysis
    pr(f"\n  PER-SECTION gallows ratios (para-initial vs body-word-initial):")

    sections = ['herbal', 'recipe', 'balneo', 'cosmo', 'astro']
    for section in sections:
        sec_pi = Counter()
        sec_bi = Counter()

        for (word, sec, folio) in para_init_words:
            if sec != section:
                continue
            fg = first_glyph(word)
            if fg in PLAIN_GALLOWS:
                sec_pi[fg] += 1

        for (word, sec, folio, pos) in body_words:
            if sec != section:
                continue
            fg = first_glyph(word)
            if fg in PLAIN_GALLOWS:
                sec_bi[fg] += 1

        sec_pi_total = sum(sec_pi.values())
        sec_bi_total = sum(sec_bi.values())

        if sec_pi_total < 3 or sec_bi_total < 3:
            pr(f"\n    {section}: too few samples (pi={sec_pi_total}, bi={sec_bi_total})")
            continue

        sec_jsd = jsd(
            {g: sec_pi[g] for g in PLAIN_GALLOWS},
            {g: sec_bi[g] for g in PLAIN_GALLOWS}
        )

        pr(f"\n    {section} (pi={sec_pi_total}, body={sec_bi_total}, JSD={sec_jsd:.4f}):")
        pr(f"      {'':>6s} | ", end='')
        for g in ['p', 't', 'k', 'f']:
            pr(f"{'  '+g:>8s}", end='')
        pr()
        pr(f"      {'pi':>6s} | ", end='')
        for g in ['p', 't', 'k', 'f']:
            pct = sec_pi[g] / sec_pi_total * 100 if sec_pi_total > 0 else 0
            pr(f"{pct:>7.1f}%", end='')
        pr()
        pr(f"      {'body':>6s} | ", end='')
        for g in ['p', 't', 'k', 'f']:
            pct = sec_bi[g] / sec_bi_total * 100 if sec_bi_total > 0 else 0
            pr(f"{pct:>7.1f}%", end='')
        pr()

    return pi_gallows, body_word_init_gallows, body_char_gallows


# ═══════════════════════════════════════════════════════════════════════
# TEST F: PARAGRAPH-INITIAL WORD DIVERSITY
# ═══════════════════════════════════════════════════════════════════════

def test_f_word_diversity(paragraphs, para_init_words):
    pr(f"\n{'═'*70}")
    pr(f"TEST F: PARAGRAPH-INITIAL WORD DIVERSITY")
    pr(f"{'═'*70}")
    pr(f"""
Medieval recipe texts have ONE dominant opening word ('Togli' 28.8%,
'Pour' 45.2%, 'Take' 31.0%). If VMS gallows are first letters of such
words, VMS should also show a small number of dominant paragraph-initial
word forms. If gallows are structural markers prepended to diverse content,
we should see MANY different word forms all starting with the same gallows.
""")

    # Overall diversity
    all_para_words = [w for (w, s, f) in para_init_words]
    total = len(all_para_words)
    counter = Counter(all_para_words)
    n_unique = len(counter)
    ttr = n_unique / total if total > 0 else 0

    pr(f"  Total paragraph-initial tokens: {total}")
    pr(f"  Unique word forms: {n_unique}")
    pr(f"  Type-token ratio (TTR): {ttr:.3f}")
    pr(f"  Most common word: '{counter.most_common(1)[0][0]}' = {counter.most_common(1)[0][1]} ({counter.most_common(1)[0][1]/total*100:.1f}%)")

    # Per gallows letter
    pr(f"\n  PER-GALLOWS DIVERSITY:")
    for g in ['p', 't', 'k', 'f']:
        g_words = [w for w in all_para_words if first_char(w) == g]
        g_counter = Counter(g_words)
        g_total = len(g_words)
        g_unique = len(g_counter)
        g_ttr = g_unique / g_total if g_total > 0 else 0

        pr(f"\n    Gallows '{g}': {g_total} tokens, {g_unique} unique forms (TTR={g_ttr:.3f})")
        pr(f"      Top 10 forms:")
        for word, count in g_counter.most_common(10):
            pct = count / g_total * 100 if g_total > 0 else 0
            bar = '█' * int(pct / 2)
            pr(f"        {word:>20s}: {count:>4d} ({pct:>5.1f}%) {bar}")

    # Comparison table
    pr(f"\n  COMPARISON: VMS vs Medieval Recipe Texts")
    pr(f"  {'Text':>30s} | {'Top word':>15s} {'%':>6s} | {'TTR (para-init)':>15s}")
    pr(f"  {'─'*30} | {'─'*15} {'─'*6} | {'─'*15}")
    top_word, top_count = counter.most_common(1)[0]
    pr(f"  {'VMS (all sections)':>30s} | {top_word:>15s} {top_count/total*100:>5.1f}% | {ttr:>15.3f}")
    pr(f"  {'Italian (Il libro cucina)':>30s} | {'togli':>15s} {'28.8%':>6s} | {'~0.28':>15s}")
    pr(f"  {'French (Viandier)':>30s} | {'pour':>15s} {'45.2%':>6s} | {'~0.26':>15s}")
    pr(f"  {'English (Forme of Cury)':>30s} | {'take':>15s} {'31.0%':>6s} | {'~0.26':>15s}")


# ═══════════════════════════════════════════════════════════════════════
# SYNTHESIS
# ═══════════════════════════════════════════════════════════════════════

def synthesis(test_a, test_b, test_c, test_d, test_e, paragraphs):
    pr(f"\n{'═'*70}")
    pr(f"PHASE 77 SYNTHESIS")
    pr(f"{'═'*70}")

    para_init_succ, body_succ, body_init_succ = test_a
    para_init_set, body_set, overlap, only_para = test_b
    plain_pos, compound_pos = test_c
    plain_pi, compound_pi, other_pi = test_d
    pi_gal, body_wi_gal, body_ca_gal = test_e

    # 1. Successor divergence summary
    pr(f"\n  1. SUCCESSOR DIVERGENCE:")
    for g in ['p', 't', 'k', 'f']:
        n_pi = sum(para_init_succ[g].values())
        n_bi = sum(body_init_succ[g].values())
        if n_pi > 5 and n_bi > 5:
            j = jsd(para_init_succ[g], body_init_succ[g])
            if j > 0.1:
                pr(f"     '{g}' successors DIVERGE between para-init and body (JSD={j:.3f})")
            else:
                pr(f"     '{g}' successors SIMILAR in both contexts (JSD={j:.3f})")

    # 2. Word overlap summary
    overlap_pct = len(overlap) / max(len(para_init_set), 1) * 100
    pr(f"\n  2. WORD OVERLAP:")
    pr(f"     {overlap_pct:.1f}% of paragraph-initial word forms also appear in body text")
    if overlap_pct < 30:
        pr(f"     → STRONG evidence for functionally distinct paragraph-initial vocabulary")
    elif overlap_pct < 50:
        pr(f"     → Moderate evidence for distinct vocabulary")
    else:
        pr(f"     → Para-initial words are largely drawn from body vocabulary")

    # 3. Compound gallows
    compound_total = sum(compound_pi.values())
    plain_total = sum(plain_pi.values())
    pr(f"\n  3. COMPOUND GALLOWS AT PARA STARTS:")
    pr(f"     Plain gallows: {plain_total} ({plain_total/len(paragraphs)*100:.1f}%)")
    pr(f"     Compound gallows: {compound_total} ({compound_total/len(paragraphs)*100:.1f}%)")
    if compound_total == 0:
        pr(f"     → ZERO compound gallows at paragraph starts — supports form-specific function")
    elif compound_total < 5:
        pr(f"     → Near-zero compound gallows — strongly supports form-specific function")
    else:
        pr(f"     → Compound gallows also appear — weakens form-specific hypothesis")

    # 4. Body-text position profile
    pr(f"\n  4. POSITION PROFILE (body text):")
    for g in ['p', 't', 'k', 'f']:
        total = sum(plain_pos[g].values())
        p1 = plain_pos[g].get(1, 0)
        if total > 0:
            p1_pct = p1 / total * 100
            if p1_pct > 80:
                pr(f"     '{g}': {p1_pct:.0f}% word-initial → primarily a word-starter in body text too")
            elif p1_pct > 50:
                pr(f"     '{g}': {p1_pct:.0f}% word-initial → mostly word-initial but some medial use")
            else:
                pr(f"     '{g}': {p1_pct:.0f}% word-initial → substantial medial presence")

    # 5. Ratio divergence
    pi_total = sum(pi_gal.values())
    bi_total = sum(body_wi_gal.values())
    if pi_total > 10 and bi_total > 10:
        j = jsd(
            {g: pi_gal[g] for g in PLAIN_GALLOWS},
            {g: body_wi_gal[g] for g in PLAIN_GALLOWS}
        )
        pr(f"\n  5. RATIO DIVERGENCE (JSD={j:.4f}):")
        if j > 0.1:
            pr(f"     p:t:k:f ratios STRONGLY DIFFER between para-init and body → DIFFERENT function")
        elif j > 0.03:
            pr(f"     p:t:k:f ratios show MODERATE divergence → partially different function")
        else:
            pr(f"     p:t:k:f ratios are SIMILAR → consistent with same function")

    # 6. Overall verdict
    pr(f"\n  VERDICT:")
    pr(f"  ─────────")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("═" * 70)
    pr("PHASE 77: Gallows Positional Ecology")
    pr("═" * 70)
    pr(f"\nQuestion: Do paragraph-initial gallows function DIFFERENTLY from")
    pr(f"body-text gallows, or are they the SAME characters in the SAME role?")

    pr(f"\nParsing VMS folios...")
    paragraphs, body_words, para_init_words = parse_all_folios()
    pr(f"  Paragraphs: {len(paragraphs)}")
    pr(f"  Body words: {len(body_words)}")
    pr(f"  Para-initial words: {len(para_init_words)}")

    # Run all tests
    test_a_result = test_a_successor_divergence(paragraphs, body_words, para_init_words)
    test_b_result = test_b_word_overlap(paragraphs, body_words, para_init_words)
    test_c_result = test_c_position_profile(body_words)
    test_d_result = test_d_compound_at_para_starts(paragraphs)
    test_e_result = test_e_ratio_comparison(paragraphs, body_words, para_init_words)
    test_f_word_diversity(paragraphs, para_init_words)

    synthesis(test_a_result, test_b_result, test_c_result, test_d_result,
              test_e_result, paragraphs)

    # Save
    txt_path = RESULTS_DIR / 'phase77_gallows_ecology.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"\nFull output → {txt_path}")


if __name__ == '__main__':
    main()
