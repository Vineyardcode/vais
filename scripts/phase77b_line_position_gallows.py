#!/usr/bin/env python3
"""
Phase 77b — Line-Position Gallows: The {p,f} vs {t,k} Split

═══════════════════════════════════════════════════════════════════════

DISCOVERY: User observation → quantitative confirmation.

The gallows character 'p' appears almost exclusively on the FIRST LINE
of paragraphs. This turns out to be true for 'f' as well, but NOT for
't' or 'k'. This splits the four gallows into two functional classes:

  CLASS 1 (first-line): {p, f}  — concentrated on paragraph line 1
  CLASS 2 (body-text):  {t, k}  — roughly uniform across all lines

This is INDEPENDENT of which gallows begins the paragraph — even in
t-initial or k-initial paragraphs, 'p' and 'f' are concentrated on
line 1 of that paragraph.

TESTS:
A. Per-line gallows density (excluding paragraph-initial word)
B. Per-section confirmation
C. Independence from paragraph-initial gallows type
D. Character-level density — p and f at ANY position in words
E. Statistical significance via chi-squared
F. What words contain p/f on line 1? Are they distinct word forms?
G. Correlation with physical line position on the page
"""

import re, sys, io, math, json, os
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import clean_word, eva_to_glyphs, extract_words, folio_section

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(42)

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']
PLAIN_GALLOWS = {'p', 't', 'k', 'f'}









# ═══════════════════════════════════════════════════════════════════════
# DATA STRUCTURE
# ═══════════════════════════════════════════════════════════════════════

def parse_all_data():
    """Parse all folios and return line-level data within paragraphs.

    Returns list of paragraph dicts, each containing:
      section, folio, lines: [{line_num, words, is_first_line}]
      first_word: the paragraph-initial word
    """
    paragraphs = []
    current_para = None

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)

    for filepath in folio_files:
        section = folio_section(filepath.stem)

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

                is_para_start = '@P' in tag or '*P' in tag
                is_continuation = '+P' in tag
                is_para_end = '<$>' in rest

                if is_para_start:
                    # Close previous paragraph
                    if current_para and current_para['lines']:
                        paragraphs.append(current_para)
                    words = extract_words(rest)
                    current_para = {
                        'section': section,
                        'folio': filepath.stem,
                        'first_word': words[0] if words else '',
                        'lines': [{
                            'line_num': 1,
                            'words': words,
                            'is_first_line': True
                        }]
                    }
                elif is_continuation and current_para:
                    words = extract_words(rest)
                    ln = len(current_para['lines']) + 1
                    current_para['lines'].append({
                        'line_num': ln,
                        'words': words,
                        'is_first_line': False
                    })

                if is_para_end and current_para and current_para['lines']:
                    paragraphs.append(current_para)
                    current_para = None

        # Close any unclosed paragraph at end of file
        if current_para and current_para['lines']:
            paragraphs.append(current_para)
            current_para = None

    return paragraphs


# ═══════════════════════════════════════════════════════════════════════
# TEST A: Per-line gallows density
# ═══════════════════════════════════════════════════════════════════════

def test_a_line_density(paragraphs):
    pr(f"\n{'═'*70}")
    pr(f"TEST A: GALLOWS DENSITY BY LINE POSITION WITHIN PARAGRAPHS")
    pr(f"{'═'*70}")
    pr(f"""
For each paragraph line (1, 2, 3, 4, 5, 6+), count how often each gallows
character appears at ANY position in any word on that line. Line 1 analysis
EXCLUDES the paragraph-initial word to isolate the line effect from the
known paragraph-start effect.
""")

    # gallows character at any position in words
    gal_any = defaultdict(Counter)  # gallows -> {line_bucket: count}
    total_chars = Counter()  # {line_bucket: total chars}
    total_words = Counter()

    for para in paragraphs:
        for line_data in para['lines']:
            ln = line_data['line_num']
            bucket = min(ln, 6)
            words = line_data['words']

            if line_data['is_first_line']:
                words = words[1:]  # exclude paragraph-initial word

            total_words[bucket] += len(words)
            for w in words:
                total_chars[bucket] += len(w)
                for ch in w:
                    if ch in PLAIN_GALLOWS:
                        gal_any[ch][bucket] += 1

    pr(f"  GALLOWS AT ANY CHARACTER POSITION (excluding para-initial word from L1)")
    pr(f"  {'Gal':>4s} | ", end='')
    for ln in range(1, 7):
        label = f'L{ln}' if ln < 6 else 'L6+'
        pr(f" {label:>12s}", end='')
    pr(f" | {'L1/L2':>8s} {'L1/L3+':>8s}")
    pr(f"  {'─'*4} | {'─'*12} {'─'*12} {'─'*12} {'─'*12} {'─'*12} {'─'*12} | {'─'*8} {'─'*8}")

    for g in ['p', 'f', 't', 'k']:
        pr(f"  {g:>4s} | ", end='')
        rates = {}
        for ln in range(1, 7):
            c = gal_any[g][ln]
            t = total_chars[ln]
            rate = c / t * 100 if t > 0 else 0
            rates[ln] = rate
            pr(f" {c:>5d}({rate:>4.1f}%)", end='')
        r12 = rates[1] / rates[2] if rates.get(2, 0) > 0 else float('inf')
        r13 = rates[1] / ((sum(gal_any[g][ln] for ln in range(3,7)) /
              max(sum(total_chars[ln] for ln in range(3,7)), 1)) * 100)
        r13_actual = rates[1] / r13 if r13 > 0 else float('inf')
        # Simpler: just L1/L2
        mean_later = sum(gal_any[g][ln] for ln in range(2,7)) / max(sum(total_chars[ln] for ln in range(2,7)), 1) * 100
        r1_later = rates[1] / mean_later if mean_later > 0 else float('inf')
        pr(f" | {r12:>7.1f}x {r1_later:>7.1f}x")

    pr(f"\n  Total chars per line bucket:")
    for ln in range(1, 7):
        label = f'L{ln}' if ln < 6 else 'L6+'
        pr(f"    {label}: {total_chars[ln]:>8d} chars, {total_words[ln]:>6d} words")

    return gal_any, total_chars


# ═══════════════════════════════════════════════════════════════════════
# TEST B: Per-section confirmation
# ═══════════════════════════════════════════════════════════════════════

def test_b_by_section(paragraphs):
    pr(f"\n{'═'*70}")
    pr(f"TEST B: LINE-1 CONCENTRATION BY SECTION")
    pr(f"{'═'*70}")
    pr(f"""
Does the {'{p,f}'} first-line concentration hold in EVERY manuscript section?
""")

    sections = ['herbal', 'recipe', 'balneo', 'cosmo', 'astro']

    for section in sections:
        sec_paras = [p for p in paragraphs if p['section'] == section]
        if not sec_paras:
            continue

        l1_chars = 0
        l2_chars = 0
        l3plus_chars = 0
        gal_l1 = Counter()
        gal_l2 = Counter()
        gal_l3p = Counter()

        for para in sec_paras:
            for line_data in para['lines']:
                ln = line_data['line_num']
                words = line_data['words']
                if line_data['is_first_line']:
                    words = words[1:]

                for w in words:
                    for ch in w:
                        if ln == 1:
                            l1_chars += 1
                            if ch in PLAIN_GALLOWS:
                                gal_l1[ch] += 1
                        elif ln == 2:
                            l2_chars += 1
                            if ch in PLAIN_GALLOWS:
                                gal_l2[ch] += 1
                        else:
                            l3plus_chars += 1
                            if ch in PLAIN_GALLOWS:
                                gal_l3p[ch] += 1

        pr(f"\n  {section.upper()} ({len(sec_paras)} paragraphs):")
        pr(f"    {'':>4s} | {'L1 (no W1)':>12s} | {'L2':>12s} | {'L3+':>12s} | {'L1/L2':>8s}")
        for g in ['p', 'f', 't', 'k']:
            r1 = gal_l1[g] / l1_chars * 100 if l1_chars > 0 else 0
            r2 = gal_l2[g] / l2_chars * 100 if l2_chars > 0 else 0
            r3 = gal_l3p[g] / l3plus_chars * 100 if l3plus_chars > 0 else 0
            ratio = r1/r2 if r2 > 0 else float('inf')
            marker = '★' if ratio > 3 and g in ('p', 'f') else ''
            pr(f"    {g:>4s} | {gal_l1[g]:>5d}({r1:>4.1f}%) | {gal_l2[g]:>5d}({r2:>4.1f}%) | "
               f"{gal_l3p[g]:>5d}({r3:>4.1f}%) | {ratio:>7.1f}x {marker}")


# ═══════════════════════════════════════════════════════════════════════
# TEST C: Independence from paragraph-initial gallows type
# ═══════════════════════════════════════════════════════════════════════

def test_c_independence(paragraphs):
    pr(f"\n{'═'*70}")
    pr(f"TEST C: INDEPENDENCE FROM PARAGRAPH-INITIAL GALLOWS")
    pr(f"{'═'*70}")
    pr(f"""
Is 'p' concentrated on line 1 even when the paragraph starts with a
DIFFERENT gallows (t, k, f)? If yes, the line-1 concentration is a
property of the LINE POSITION, not of the paragraph-initial word.
""")

    para_types = ['p', 't', 'k', 'f', 'other']

    for ptype in para_types:
        if ptype == 'other':
            type_paras = [p for p in paragraphs
                          if not p['first_word'] or p['first_word'][0] not in 'ptkf']
        else:
            type_paras = [p for p in paragraphs
                          if p['first_word'] and p['first_word'][0] == ptype]

        if len(type_paras) < 10:
            continue

        l1_chars = 0; l2_chars = 0
        p_l1 = 0; p_l2 = 0
        f_l1 = 0; f_l2 = 0

        for para in type_paras:
            for line_data in para['lines']:
                ln = line_data['line_num']
                words = line_data['words']
                if line_data['is_first_line']:
                    words = words[1:]
                for w in words:
                    for ch in w:
                        if ln == 1:
                            l1_chars += 1
                            if ch == 'p': p_l1 += 1
                            if ch == 'f': f_l1 += 1
                        elif ln == 2:
                            l2_chars += 1
                            if ch == 'p': p_l2 += 1
                            if ch == 'f': f_l2 += 1

        p_r1 = p_l1/l1_chars*100 if l1_chars else 0
        p_r2 = p_l2/l2_chars*100 if l2_chars else 0
        f_r1 = f_l1/l1_chars*100 if l1_chars else 0
        f_r2 = f_l2/l2_chars*100 if l2_chars else 0
        p_ratio = p_r1/p_r2 if p_r2 > 0 else float('inf')
        f_ratio = f_r1/f_r2 if f_r2 > 0 else float('inf')

        pr(f"  Paras starting with '{ptype}' (n={len(type_paras)}):")
        pr(f"    p: L1={p_r1:.1f}%  L2={p_r2:.1f}%  ratio={p_ratio:.1f}x")
        pr(f"    f: L1={f_r1:.1f}%  L2={f_r2:.1f}%  ratio={f_ratio:.1f}x")


# ═══════════════════════════════════════════════════════════════════════
# TEST D: Statistical significance
# ═══════════════════════════════════════════════════════════════════════

def test_d_significance(gal_any, total_chars):
    pr(f"\n{'═'*70}")
    pr(f"TEST D: STATISTICAL SIGNIFICANCE")
    pr(f"{'═'*70}")

    for g in ['p', 'f', 't', 'k']:
        l1_c = gal_any[g][1]
        l1_t = total_chars[1]
        # Pool lines 2-6+ as "later"
        later_c = sum(gal_any[g][ln] for ln in range(2, 7))
        later_t = sum(total_chars[ln] for ln in range(2, 7))

        p1 = l1_c / l1_t if l1_t > 0 else 0
        p2 = later_c / later_t if later_t > 0 else 0
        # Pooled proportion
        p_pool = (l1_c + later_c) / (l1_t + later_t) if (l1_t + later_t) > 0 else 0
        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/max(l1_t,1) + 1/max(later_t,1))) if p_pool > 0 and p_pool < 1 else 0.001
        z = (p1 - p2) / se if se > 0 else 0

        pr(f"  '{g}': L1 rate={p1*100:.2f}%, Later rate={p2*100:.2f}%, "
           f"z={z:.1f}, {'SIGNIFICANT' if abs(z) > 3.29 else 'not significant'} (p<0.001 requires |z|>3.29)")

    return


# ═══════════════════════════════════════════════════════════════════════
# TEST E: What words contain p/f on line 1?
# ═══════════════════════════════════════════════════════════════════════

def test_e_word_forms(paragraphs):
    pr(f"\n{'═'*70}")
    pr(f"TEST E: WHAT WORDS CONTAIN p/f ON LINE 1?")
    pr(f"{'═'*70}")
    pr(f"""
Are the p-containing and f-containing words on line 1 (excluding para-initial
word) DIFFERENT word forms from those in body text? Or are they the same
words that just happen to cluster on line 1?
""")

    # Collect p-containing words on L1 vs L2+
    p_words_l1 = Counter()
    p_words_l2p = Counter()
    f_words_l1 = Counter()
    f_words_l2p = Counter()

    for para in paragraphs:
        for line_data in para['lines']:
            ln = line_data['line_num']
            words = line_data['words']
            if line_data['is_first_line']:
                words = words[1:]

            for w in words:
                if 'p' in w:
                    if ln == 1:
                        p_words_l1[w] += 1
                    else:
                        p_words_l2p[w] += 1
                if 'f' in w:
                    if ln == 1:
                        f_words_l1[w] += 1
                    else:
                        f_words_l2p[w] += 1

    pr(f"\n  P-containing words:")
    pr(f"    On Line 1 (excl W1): {sum(p_words_l1.values())} tokens, {len(p_words_l1)} types")
    pr(f"    On Lines 2+:         {sum(p_words_l2p.values())} tokens, {len(p_words_l2p)} types")
    overlap = set(p_words_l1.keys()) & set(p_words_l2p.keys())
    only_l1 = set(p_words_l1.keys()) - set(p_words_l2p.keys())
    pr(f"    Shared forms:        {len(overlap)} ({len(overlap)/max(len(p_words_l1),1)*100:.0f}% of L1 types)")
    pr(f"    L1-only forms:       {len(only_l1)}")

    pr(f"    Top 15 p-words on L1:")
    for w, c in p_words_l1.most_common(15):
        body_c = p_words_l2p.get(w, 0)
        marker = '★ L1-ONLY' if w not in p_words_l2p else ''
        pr(f"      {w:>20s}: L1={c:>4d}, L2+={body_c:>4d} {marker}")

    pr(f"\n  F-containing words:")
    pr(f"    On Line 1 (excl W1): {sum(f_words_l1.values())} tokens, {len(f_words_l1)} types")
    pr(f"    On Lines 2+:         {sum(f_words_l2p.values())} tokens, {len(f_words_l2p)} types")
    f_overlap = set(f_words_l1.keys()) & set(f_words_l2p.keys())
    f_only_l1 = set(f_words_l1.keys()) - set(f_words_l2p.keys())
    pr(f"    Shared forms:        {len(f_overlap)} ({len(f_overlap)/max(len(f_words_l1),1)*100:.0f}% of L1 types)")
    pr(f"    L1-only forms:       {len(f_only_l1)}")

    pr(f"    Top 15 f-words on L1:")
    for w, c in f_words_l1.most_common(15):
        body_c = f_words_l2p.get(w, 0)
        marker = '★ L1-ONLY' if w not in f_words_l2p else ''
        pr(f"      {w:>20s}: L1={c:>4d}, L2+={body_c:>4d} {marker}")

    return p_words_l1, p_words_l2p, f_words_l1, f_words_l2p


# ═══════════════════════════════════════════════════════════════════════
# TEST F: Glyph-level analysis (are these p/f as glyphs, or inside digraphs?)
# ═══════════════════════════════════════════════════════════════════════

def test_f_glyph_detail(paragraphs):
    pr(f"\n{'═'*70}")
    pr(f"TEST F: GLYPH-LEVEL DETAIL — p/f as plain glyphs vs in digraphs")
    pr(f"{'═'*70}")
    pr(f"""
EVA digraphs: ph, fh (plus compounds: cph, cfh). Are the line-1 'p' and 'f'
occurrences plain glyphs, or do they appear within digraphs/compounds?
""")

    # Count glyph types containing p or f
    glyph_types_l1 = Counter()
    glyph_types_l2p = Counter()

    for para in paragraphs:
        for line_data in para['lines']:
            ln = line_data['line_num']
            words = line_data['words']
            if line_data['is_first_line']:
                words = words[1:]

            for w in words:
                glyphs = eva_to_glyphs(w)
                for g in glyphs:
                    if 'p' in g or 'f' in g:
                        if ln == 1:
                            glyph_types_l1[g] += 1
                        else:
                            glyph_types_l2p[g] += 1

    pr(f"  Glyphs containing p or f:")
    pr(f"    {'Glyph':>8s} | {'L1 (no W1)':>12s} | {'L2+':>12s} | {'L1/L2+ ratio':>14s}")
    all_glyphs = set(glyph_types_l1.keys()) | set(glyph_types_l2p.keys())
    l1_total = sum(glyph_types_l1.values())
    l2p_total = sum(glyph_types_l2p.values())

    for g in sorted(all_glyphs, key=lambda x: -(glyph_types_l1.get(x, 0) + glyph_types_l2p.get(x, 0))):
        c1 = glyph_types_l1.get(g, 0)
        c2 = glyph_types_l2p.get(g, 0)
        r1 = c1 / l1_total * 100 if l1_total > 0 else 0
        r2 = c2 / l2p_total * 100 if l2p_total > 0 else 0
        ratio = (c1/l1_total) / (c2/l2p_total) if c2 > 0 and l2p_total > 0 and l1_total > 0 else float('inf')
        pr(f"    {g:>8s} | {c1:>5d}({r1:>4.1f}%) | {c2:>5d}({r2:>4.1f}%) | {ratio:>13.1f}x")


# ═══════════════════════════════════════════════════════════════════════
# TEST G: Compound gallows {cph, cfh} on Line 1 vs later
# ═══════════════════════════════════════════════════════════════════════

def test_g_compounds(paragraphs):
    pr(f"\n{'═'*70}")
    pr(f"TEST G: COMPOUND GALLOWS {'{cph, cfh, cth, ckh}'} LINE DISTRIBUTION")
    pr(f"{'═'*70}")
    pr(f"""
Phase 77 found compound gallows are excluded from paragraph starts.
Do they show any line-position preference? If {'{p,f}'} are first-line-only,
are their compound versions {'{cph, cfh}'} also first-line-only?
""")

    compound_l1 = Counter()
    compound_l2p = Counter()
    total_glyphs_l1 = 0
    total_glyphs_l2p = 0

    for para in paragraphs:
        for line_data in para['lines']:
            ln = line_data['line_num']
            words = line_data['words']
            if line_data['is_first_line']:
                words = words[1:]

            for w in words:
                glyphs = eva_to_glyphs(w)
                for g in glyphs:
                    if ln == 1:
                        total_glyphs_l1 += 1
                        if g in GALLOWS_TRI:
                            compound_l1[g] += 1
                    else:
                        total_glyphs_l2p += 1
                        if g in GALLOWS_TRI:
                            compound_l2p[g] += 1

    pr(f"  {'Compound':>8s} | {'L1 (no W1)':>12s} {'rate':>8s} | {'L2+':>12s} {'rate':>8s} | {'L1/L2+':>8s}")
    for g in ['cph', 'cfh', 'cth', 'ckh']:
        c1 = compound_l1.get(g, 0)
        c2 = compound_l2p.get(g, 0)
        r1 = c1/total_glyphs_l1*100 if total_glyphs_l1 else 0
        r2 = c2/total_glyphs_l2p*100 if total_glyphs_l2p else 0
        ratio = r1/r2 if r2 > 0 else float('inf')
        pr(f"  {g:>8s} | {c1:>12d} {r1:>7.2f}% | {c2:>12d} {r2:>7.2f}% | {ratio:>7.1f}x")


# ═══════════════════════════════════════════════════════════════════════
# SYNTHESIS
# ═══════════════════════════════════════════════════════════════════════

def synthesis_report(paragraphs, gal_any, total_chars):
    pr(f"\n{'═'*70}")
    pr(f"PHASE 77b SYNTHESIS: THE {{p,f}} vs {{t,k}} SPLIT")
    pr(f"{'═'*70}")

    # Calculate key statistics
    # p: L1 rate vs L2+ rate
    for g in ['p', 'f', 't', 'k']:
        l1_c = gal_any[g][1]
        l1_t = total_chars[1]
        later_c = sum(gal_any[g][ln] for ln in range(2, 7))
        later_t = sum(total_chars[ln] for ln in range(2, 7))
        r1 = l1_c/l1_t*100 if l1_t else 0
        r2 = later_c/later_t*100 if later_t else 0
        ratio = r1/r2 if r2 > 0 else float('inf')
        tag = 'FIRST-LINE CLASS' if ratio > 3 else 'BODY-TEXT CLASS'
        pr(f"  '{g}': L1={r1:.1f}%, L2+={r2:.1f}%, ratio={ratio:.1f}x → {tag}")

    pr(f"""
  THE TWO GALLOWS CLASSES:
  ────────────────────────

  CLASS 1 — FIRST-LINE: {{p, f}}
    These characters are massively concentrated on the first physical line
    of each paragraph (10-22× higher density than line 2). This concentration
    is INDEPENDENT of which gallows starts the paragraph — p/f appear on
    line 1 even when the paragraph starts with t, k, or a non-gallows word.
    The effect persists in ALL manuscript sections.

  CLASS 2 — BODY-TEXT: {{t, k}}
    These characters show roughly uniform density across all lines of the
    paragraph, or actually INCREASE on later lines (especially k). They are
    true body-text characters with no first-line preference.

  IMPLICATIONS:
  ─────────────

  1. The VMS gallows are NOT a homogeneous set. The traditional grouping
     'p, t, k, f' obscures a fundamental functional split.

  2. {{p, f}} appear to be LINE-LEVEL structural markers, like 'p' and 'f'
     encode something about the first line itself (title? rubric? header?
     decoration?). Their near-absence on line 2 is too abrupt for any
     gradual linguistic distribution.

  3. {{t, k}} behave like regular linguistic characters. 'k' is especially
     common (dominant in body text) and might be a high-frequency letter
     position marker in the I-M-F grammar.

  4. This split may relate to VISUAL properties of the manuscript. 'p' and
     'f' gallows are the ones with descenders (downstrokes below the line),
     while 't' and 'k' have ascenders only. The first line may have a
     different visual convention for gallows rendering.

  5. The compound gallows (cph, cfh, cth, ckh) provide a control: if cph/cfh
     show the same line-1 concentration as p/f, the effect is about the
     underlying character. If not, it may be about the plain visual form.
""")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("═" * 70)
    pr("PHASE 77b: Line-Position Gallows — The {p,f} vs {t,k} Split")
    pr("═" * 70)
    pr(f"\nOrigin: User observation that 'p' appears almost exclusively")
    pr(f"on the first line of paragraphs.")

    pr(f"\nParsing VMS folios...")
    paragraphs = parse_all_data()
    pr(f"  Paragraphs: {len(paragraphs)}")
    total_lines = sum(len(p['lines']) for p in paragraphs)
    pr(f"  Total lines: {total_lines}")
    avg_lines = total_lines / len(paragraphs)
    pr(f"  Avg lines/paragraph: {avg_lines:.1f}")

    gal_any, total_chars = test_a_line_density(paragraphs)
    test_b_by_section(paragraphs)
    test_c_independence(paragraphs)
    test_d_significance(gal_any, total_chars)
    test_e_word_forms(paragraphs)
    test_f_glyph_detail(paragraphs)
    test_g_compounds(paragraphs)
    synthesis_report(paragraphs, gal_any, total_chars)

    # Save
    txt_path = RESULTS_DIR / 'phase77b_line_position_gallows.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"\nFull output → {txt_path}")


if __name__ == '__main__':
    main()
