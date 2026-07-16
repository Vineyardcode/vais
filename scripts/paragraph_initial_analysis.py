#!/usr/bin/env python3
"""
Paragraph-Initial Letter Analysis & Star Marker Correlation
═══════════════════════════════════════════════════════════════════════

OBSERVATION: many paragraphs seem to start with the same letter/glyph.
In f103r (recipe section), paragraphs are marked with different star types
(dark, light, dotted) and many start with similar-looking characters.

SKEPTICAL APPROACH:
  1. Measure paragraph-initial character distribution across entire MS
  2. Compare to BASELINE character frequency — if 'o' is 15% of all chars,
     we'd EXPECT it to be ~15% of paragraph-initial chars by chance
  3. Chi-squared test: is the deviation from baseline significant?
  4. Control test: compare LINE-initial chars (not just paragraphs)
  5. Compare paragraph-initial WORDS to general word frequency
  6. Section-by-section breakdown (herbal vs recipe vs astro)
  7. Star marker type vs. initial character correlation (recipe section)
  8. SELF-CRITIQUE: Could this be an artifact of transcription conventions?

NULL HYPOTHESIS: Paragraph-initial characters are drawn from the same
distribution as all characters. Any apparent concentration is just because
some characters are common everywhere.
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import os
from common import eva_to_glyphs, folio_section_v2 as folio_section

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end)
    sys.stdout.flush()
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

# ═══════════════════════════════════════════════════════════════════════
# EVA GLYPH PARSING
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth','ckh','cph','cfh']
GALLOWS_BI  = ['ch','sh','th','kh','ph','fh']

def eva_first_glyph(word):
    """Return the first EVA glyph of a word (handling digraphs/trigraphs)."""
    if not word:
        return ''
    w = word.lower()
    for tri in GALLOWS_TRI:
        if w.startswith(tri):
            return tri
    for bi in GALLOWS_BI:
        if w.startswith(bi):
            return bi
    return w[0]


def eva_first_char(word):
    """Return just the first EVA character (single letter, not glyph)."""
    if not word:
        return ''
    return word[0].lower()

# ═══════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════

# Approximate section assignments based on folio ranges
SECTIONS = {
    'herbal': list(range(1, 67)) + list(range(87, 103)),  # f1-f66, f87-f102
    'astro': list(range(67, 74)),  # f67-f73
    'balneo': list(range(75, 85)),  # f75-f84
    'cosmo': list(range(85, 87)),  # f85-f86 (rosettes)
    'pharma': list(range(88, 103)),  # overlaps with herbal
    'recipe': list(range(103, 117)),  # f103-f116 (stars section)
}

def folio_number(fname):
    """Extract numeric folio number from filename like f103r.txt."""
    m = re.match(r'f(\d+)', fname)
    if m:
        return int(m.group(1))
    return 0


def parse_folio(filepath):
    """
    Parse a folio file. Return:
      - paragraphs: list of {first_word, first_glyph, first_char, star_comment, words, line_tag}
      - all_words: flat list of all words
      - all_lines: list of {first_word, words, is_para_start}
      - star_annotations: list of comment lines before paragraphs
    """
    paragraphs = []
    all_words = []
    all_lines = []
    current_star = None

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()

        # Track star/comment annotations
        if line.startswith('#'):
            # Look for star descriptions
            low = line.lower()
            if 'star' in low or 'point' in low:
                current_star = line.lstrip('#').strip()
            continue

        if not line or line.startswith('<f') and '>' in line and line.endswith('>'):
            # Skip pure tag lines without text
            if not line or not re.search(r'>\s*\S', line):
                continue

        # Extract tag and text
        m = re.match(r'<([^>]+)>', line)
        if not m:
            continue
        tag = m.group(1)
        rest = line[m.end():].strip()
        if not rest:
            continue

        # Determine if this is a paragraph start
        is_para_start = '@P' in tag or '<%>' in rest

        # Clean the text: remove <%> and <$> markers
        text = rest.replace('<%>', '').replace('<$>', '').strip()

        # Extract words
        words = []
        for tok in re.split(r'[.\s,;]+', text):
            tok = tok.strip()
            # Remove variant markers like [ch:ee], {ikh}, etc.
            tok = re.sub(r'\[([^:\]]+):[^\]]*\]', r'\1', tok)
            tok = re.sub(r'\{[^}]*\}', '', tok)
            tok = re.sub(r"[^a-z]", '', tok.lower())
            if tok and len(tok) >= 1:
                words.append(tok)

        if not words:
            continue

        all_words.extend(words)

        line_info = {
            'first_word': words[0],
            'words': words,
            'is_para_start': is_para_start,
            'tag': tag,
        }
        all_lines.append(line_info)

        if is_para_start:
            para = {
                'first_word': words[0],
                'first_glyph': eva_first_glyph(words[0]),
                'first_char': eva_first_char(words[0]),
                'star_comment': current_star,
                'words': words,
                'tag': tag,
            }
            paragraphs.append(para)
            current_star = None  # consumed

    return paragraphs, all_words, all_lines


# ═══════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def chi_squared_test(observed_counts, expected_probs, total_observed):
    """
    Chi-squared goodness-of-fit test.
    observed_counts: Counter of categories
    expected_probs: dict of category -> expected probability
    total_observed: sum of observed counts
    Returns: chi2 statistic, degrees of freedom, approximate p-value
    """
    all_cats = set(list(observed_counts.keys()) + list(expected_probs.keys()))
    chi2 = 0.0
    df = 0
    for cat in sorted(all_cats):
        obs = observed_counts.get(cat, 0)
        exp = expected_probs.get(cat, 0.0) * total_observed
        if exp < 1.0:
            continue  # Skip categories with expected < 1 (chi2 unreliable)
        chi2 += (obs - exp) ** 2 / exp
        df += 1
    df = max(df - 1, 1)  # degrees of freedom = categories - 1

    # Approximate p-value using Wilson-Hilferty approximation
    if df > 0:
        z = ((chi2 / df) ** (1/3) - (1 - 2/(9*df))) / math.sqrt(2/(9*df))
        # Standard normal CDF approximation
        p_approx = 0.5 * (1 + math.erf(-z / math.sqrt(2)))
    else:
        p_approx = 1.0
    return chi2, df, p_approx


def main():
    pr("=" * 75)
    pr("paragraph_initial_analysis: PARAGRAPH-INITIAL LETTER ANALYSIS")
    pr("Skeptical revalidation of paragraph-start patterns")
    pr("=" * 75)

    # ─── Load all folios ─────────────────────────────────────────────
    all_paragraphs = []
    all_words_global = []
    all_lines_global = []
    section_paragraphs = defaultdict(list)
    section_words = defaultdict(list)

    folio_files = sorted(FOLIO_DIR.glob('*.txt'))
    for fp in folio_files:
        fnum = folio_number(fp.stem)
        sec = folio_section(fnum)
        paras, words, lines = parse_folio(fp)
        all_paragraphs.extend(paras)
        all_words_global.extend(words)
        all_lines_global.extend(lines)
        for p in paras:
            p['section'] = sec
            p['folio'] = fp.stem
        section_paragraphs[sec].extend(paras)
        section_words[sec].extend(words)

    pr(f"\nTotal paragraphs detected: {len(all_paragraphs)}")
    pr(f"Total words: {len(all_words_global)}")
    pr(f"Total lines: {len(all_lines_global)}")

    # ─── 1. BASELINE: Character frequency across entire MS ───────────
    pr("\n" + "─" * 75)
    pr("1. BASELINE CHARACTER FREQUENCIES (entire manuscript)")
    pr("─" * 75)

    all_chars = []
    for w in all_words_global:
        all_chars.extend(list(w.lower()))

    char_freq = Counter(all_chars)
    total_chars = sum(char_freq.values())
    char_probs = {c: n/total_chars for c, n in char_freq.items()}

    pr(f"\nTotal characters: {total_chars}")
    pr(f"Unique characters: {len(char_freq)}")
    pr("\nTop 15 characters by frequency:")
    for c, n in char_freq.most_common(15):
        pr(f"  '{c}': {n:6d} ({100*n/total_chars:.1f}%)")

    # ─── 2. PARAGRAPH-INITIAL first character ────────────────────────
    pr("\n" + "─" * 75)
    pr("2. PARAGRAPH-INITIAL FIRST CHARACTER (all paragraphs)")
    pr("─" * 75)

    para_first_chars = Counter(p['first_char'] for p in all_paragraphs)
    total_paras = len(all_paragraphs)

    pr(f"\nParagraph-initial character distribution (n={total_paras}):")
    for c, n in para_first_chars.most_common(15):
        expected = char_probs.get(c, 0) * 100
        actual = 100 * n / total_paras
        ratio = actual / expected if expected > 0 else float('inf')
        pr(f"  '{c}': {n:4d} ({actual:.1f}%)  "
           f"[baseline: {expected:.1f}%, ratio: {ratio:.2f}x]")

    # Chi-squared test
    chi2, df, p_val = chi_squared_test(para_first_chars, char_probs, total_paras)
    pr(f"\nChi-squared test vs baseline character freq:")
    pr(f"  χ² = {chi2:.1f}, df = {df}, p ≈ {p_val:.2e}")
    if p_val < 0.001:
        pr("  >>> SIGNIFICANT: paragraph-initial chars differ from baseline")
    elif p_val < 0.05:
        pr("  >>> Marginally significant")
    else:
        pr("  >>> NOT significant — could be baseline frequency alone")

    # ─── 3. PARAGRAPH-INITIAL first GLYPH (handling digraphs) ────────
    pr("\n" + "─" * 75)
    pr("3. PARAGRAPH-INITIAL FIRST GLYPH (digraph-aware)")
    pr("─" * 75)

    para_first_glyphs = Counter(p['first_glyph'] for p in all_paragraphs)
    pr(f"\nTop 15 paragraph-initial glyphs:")
    for g, n in para_first_glyphs.most_common(15):
        pr(f"  '{g}': {n:4d} ({100*n/total_paras:.1f}%)")

    # ─── 4. PARAGRAPH-INITIAL first WORD ─────────────────────────────
    pr("\n" + "─" * 75)
    pr("4. PARAGRAPH-INITIAL FIRST WORD")
    pr("─" * 75)

    para_first_words = Counter(p['first_word'] for p in all_paragraphs)
    word_freq_global = Counter(all_words_global)
    total_words = len(all_words_global)

    pr(f"\nTop 20 paragraph-initial words:")
    for w, n in para_first_words.most_common(20):
        global_pct = 100 * word_freq_global.get(w, 0) / total_words
        para_pct = 100 * n / total_paras
        ratio = para_pct / global_pct if global_pct > 0 else float('inf')
        pr(f"  '{w}': {n:4d} ({para_pct:.1f}%)  "
           f"[global: {global_pct:.2f}%, ratio: {ratio:.1f}x]")

    # ─── 5. CONTROL: LINE-INITIAL characters ─────────────────────────
    pr("\n" + "─" * 75)
    pr("5. CONTROL: LINE-INITIAL first character (ALL lines, not just paragraphs)")
    pr("─" * 75)

    line_first_chars = Counter(l['first_word'][0].lower() for l in all_lines_global if l['first_word'])
    total_lines = len(all_lines_global)

    pr(f"\nLine-initial character distribution (n={total_lines}):")
    for c, n in line_first_chars.most_common(10):
        expected = char_probs.get(c, 0) * 100
        actual = 100 * n / total_lines
        ratio = actual / expected if expected > 0 else float('inf')
        pr(f"  '{c}': {n:4d} ({actual:.1f}%)  "
           f"[baseline: {expected:.1f}%, ratio: {ratio:.2f}x]")

    chi2_l, df_l, p_val_l = chi_squared_test(line_first_chars, char_probs, total_lines)
    pr(f"\nChi-squared test (line-initial vs baseline):")
    pr(f"  χ² = {chi2_l:.1f}, df = {df_l}, p ≈ {p_val_l:.2e}")

    # ─── 6. PARAGRAPH vs LINE-INITIAL comparison ─────────────────────
    pr("\n" + "─" * 75)
    pr("6. PARAGRAPH-INITIAL vs LINE-INITIAL (is paragraph-start special?)")
    pr("─" * 75)

    non_para_lines = [l for l in all_lines_global if not l['is_para_start']]
    non_para_first = Counter(l['first_word'][0].lower() for l in non_para_lines if l['first_word'])
    total_non_para = len(non_para_lines)

    pr(f"\nParagraph-start lines: {total_paras}")
    pr(f"Non-paragraph lines: {total_non_para}")
    pr(f"\nComparison (paragraph-initial vs non-paragraph line-initial):")
    pr(f"  {'Char':<6} {'Para%':>7} {'Line%':>7} {'Ratio':>7}")
    for c, n in para_first_chars.most_common(10):
        para_pct = 100 * n / total_paras
        line_n = non_para_first.get(c, 0)
        line_pct = 100 * line_n / total_non_para if total_non_para > 0 else 0
        ratio = para_pct / line_pct if line_pct > 0 else float('inf')
        pr(f"  '{c}'    {para_pct:6.1f}% {line_pct:6.1f}% {ratio:6.2f}x")

    # Chi-squared: paragraph-initial vs non-paragraph-initial
    non_para_probs = {c: n/total_non_para for c, n in non_para_first.items()}
    chi2_pv, df_pv, p_val_pv = chi_squared_test(para_first_chars, non_para_probs, total_paras)
    pr(f"\nChi-squared test (para-initial vs non-para line-initial):")
    pr(f"  χ² = {chi2_pv:.1f}, df = {df_pv}, p ≈ {p_val_pv:.2e}")
    if p_val_pv < 0.001:
        pr("  >>> SIGNIFICANT: para-initial IS different from line-initial")
    else:
        pr("  >>> Not significantly different — paragraph starts may not be special")

    # ─── 7. SECTION BREAKDOWN ────────────────────────────────────────
    pr("\n" + "─" * 75)
    pr("7. SECTION-BY-SECTION PARAGRAPH-INITIAL ANALYSIS")
    pr("─" * 75)

    for sec in ['herbal', 'astro', 'balneo', 'recipe']:
        paras = section_paragraphs.get(sec, [])
        if not paras:
            continue
        pr(f"\n  === {sec.upper()} section ({len(paras)} paragraphs) ===")
        first_chars = Counter(p['first_char'] for p in paras)
        first_glyphs = Counter(p['first_glyph'] for p in paras)
        first_words = Counter(p['first_word'] for p in paras)
        n = len(paras)

        pr(f"  Top 5 first chars:  ", end='')
        for c, cnt in first_chars.most_common(5):
            pr(f"'{c}'={cnt}({100*cnt/n:.0f}%) ", end='')
        pr()

        pr(f"  Top 5 first glyphs: ", end='')
        for g, cnt in first_glyphs.most_common(5):
            pr(f"'{g}'={cnt}({100*cnt/n:.0f}%) ", end='')
        pr()

        pr(f"  Top 5 first words:  ", end='')
        for w, cnt in first_words.most_common(5):
            pr(f"'{w}'={cnt}({100*cnt/n:.0f}%) ", end='')
        pr()

        # Concentration metric: what fraction of paragraphs start with
        # the single most common character?
        top_char, top_count = first_chars.most_common(1)[0]
        concentration = top_count / n
        pr(f"  Concentration: {100*concentration:.0f}% start with '{top_char}'")

    # ─── 8. STAR MARKER ANALYSIS (recipe section) ────────────────────
    pr("\n" + "─" * 75)
    pr("8. STAR MARKER TYPE vs. INITIAL CHARACTER (recipe section)")
    pr("─" * 75)

    recipe_paras = section_paragraphs.get('recipe', [])
    if recipe_paras:
        pr(f"\nRecipe section paragraphs with star annotations: ")

        star_types = defaultdict(list)
        no_star = []
        for p in recipe_paras:
            star = p.get('star_comment', None)
            if star:
                # Normalize star description
                low = star.lower()
                if 'dark' in low:
                    stype = 'DARK'
                elif 'light' in low and 'dot' in low:
                    stype = 'LIGHT_DOTTED'
                elif 'light' in low:
                    stype = 'LIGHT'
                else:
                    stype = 'OTHER'

                # Count points
                pm = re.search(r'(\d+)\s*point', low)
                points = int(pm.group(1)) if pm else 0

                star_types[stype].append({
                    'first_word': p['first_word'],
                    'first_glyph': p['first_glyph'],
                    'first_char': p['first_char'],
                    'star_raw': star,
                    'points': points,
                    'folio': p.get('folio', '?'),
                })
            else:
                no_star.append(p)

        for stype in sorted(star_types.keys()):
            entries = star_types[stype]
            pr(f"\n  {stype} stars ({len(entries)} paragraphs):")
            fc = Counter(e['first_char'] for e in entries)
            fg = Counter(e['first_glyph'] for e in entries)
            fw = Counter(e['first_word'] for e in entries)
            n = len(entries)

            pr(f"    First chars:  ", end='')
            for c, cnt in fc.most_common(5):
                pr(f"'{c}'={cnt}({100*cnt/n:.0f}%) ", end='')
            pr()

            pr(f"    First glyphs: ", end='')
            for g, cnt in fg.most_common(5):
                pr(f"'{g}'={cnt}({100*cnt/n:.0f}%) ", end='')
            pr()

            pr(f"    First words:  ", end='')
            for w, cnt in fw.most_common(5):
                pr(f"'{w}'={cnt}({100*cnt/n:.0f}%) ", end='')
            pr()

            # Show actual first words for each paragraph
            pr(f"    All entries:")
            for e in entries:
                pr(f"      {e['folio']:>8s} | {e['star_raw']:<35s} | {e['first_word']}")

        if no_star:
            pr(f"\n  NO STAR annotation ({len(no_star)} paragraphs):")
            for p in no_star[:10]:
                pr(f"      {p.get('folio','?'):>8s} | {p['first_word']}")

    # ─── 9. WORD-POSITION ANALYSIS: first word of para vs word #2+ ──
    pr("\n" + "─" * 75)
    pr("9. FIRST WORD vs. ALL OTHER WORDS (vocabulary overlap)")
    pr("─" * 75)

    para_first_word_set = set(p['first_word'] for p in all_paragraphs)
    all_word_set = set(all_words_global)
    non_first_words = set()
    for p in all_paragraphs:
        for w in p['words'][1:]:
            non_first_words.add(w)

    only_first = para_first_word_set - non_first_words
    pr(f"\nUnique paragraph-initial words: {len(para_first_word_set)}")
    pr(f"Words that appear ONLY para-initially: {len(only_first)}")
    if only_first:
        pr(f"  Examples: {sorted(only_first)[:20]}")

    # ─── 10. GALLOWS-INITIAL PARAGRAPH TEST ──────────────────────────
    pr("\n" + "─" * 75)
    pr("10. GALLOWS-INITIAL PARAGRAPHS (are gallows over-represented?)")
    pr("─" * 75)

    gallows_set = set(['t', 'k', 'f', 'p', 'cth', 'ckh', 'cph', 'cfh'])

    # Paragraph-initial
    para_gallows = sum(1 for p in all_paragraphs if p['first_glyph'] in gallows_set)
    para_gallows_pct = 100 * para_gallows / total_paras

    # All word-initial
    all_word_first_glyphs = [eva_first_glyph(w) for w in all_words_global]
    all_gallows = sum(1 for g in all_word_first_glyphs if g in gallows_set)
    all_gallows_pct = 100 * all_gallows / len(all_word_first_glyphs)

    # Line-initial (non-paragraph)
    non_para_word_first = [l['first_word'] for l in non_para_lines if l['first_word']]
    non_para_gallows = sum(1 for w in non_para_word_first if eva_first_glyph(w) in gallows_set)
    non_para_gallows_pct = 100 * non_para_gallows / max(len(non_para_word_first), 1)

    pr(f"\n  Gallows-initial rate:")
    pr(f"    All words:          {all_gallows:5d}/{len(all_word_first_glyphs):5d} = {all_gallows_pct:.1f}%")
    pr(f"    Non-para lines:     {non_para_gallows:5d}/{len(non_para_word_first):5d} = {non_para_gallows_pct:.1f}%")
    pr(f"    Paragraph-initial:  {para_gallows:5d}/{total_paras:5d} = {para_gallows_pct:.1f}%")
    ratio = para_gallows_pct / all_gallows_pct if all_gallows_pct > 0 else 0
    pr(f"    Enrichment ratio:   {ratio:.2f}x vs all words")

    # ─── 11. SPECIFIC GLYPH BREAKDOWN FOR RECIPE SECTION ────────────
    pr("\n" + "─" * 75)
    pr("11. f103r-f116v: INITIAL GLYPH DEEP DIVE")
    pr("─" * 75)

    recipe_paras_all = [p for p in all_paragraphs
                        if folio_number(p.get('folio', 'f0')) >= 103]
    if recipe_paras_all:
        pr(f"\nRecipe-range paragraphs: {len(recipe_paras_all)}")
        fg = Counter(p['first_glyph'] for p in recipe_paras_all)
        n = len(recipe_paras_all)
        pr(f"\nFirst glyph distribution:")
        for g, cnt in fg.most_common():
            bar = '█' * int(50 * cnt / n)
            pr(f"  {g:<5s} {cnt:3d} ({100*cnt/n:5.1f}%) {bar}")

        # What follows the initial glyph?
        pr(f"\nSecond glyph after paragraph-initial glyph:")
        for init_g in [x[0] for x in fg.most_common(5)]:
            seconds = []
            for p in recipe_paras_all:
                glyphs = eva_to_glyphs(p['first_word'])
                if len(glyphs) >= 2 and glyphs[0] == init_g:
                    seconds.append(glyphs[1])
            sec_count = Counter(seconds)
            pr(f"  After '{init_g}': ", end='')
            for s, c in sec_count.most_common(5):
                pr(f"'{s}'={c} ", end='')
            pr()

    # ─── 12. SKEPTICAL SELF-ASSESSMENT ───────────────────────────────
    pr("\n" + "═" * 75)
    pr("12. SKEPTICAL SELF-ASSESSMENT")
    pr("═" * 75)
    pr("""
POTENTIAL CONFOUNDS TO CHECK:
  a) Is 'paragraph' detection reliable? @P0 vs +P0 in IVTFF format may
     not map cleanly onto visual paragraph breaks. Cross-check with images.
  b) Transcription bias: Did transcribers use <%> markers consistently?
     If some folios lack proper paragraph markers, our counts are skewed.
  c) Character frequency: If the top 3 characters make up >40% of all chars,
     it's NOT surprising that they dominate paragraph starts too.
     The chi-squared test above directly tests this.
  d) Line-wrap artifact: If paragraphs always start at the left margin
     and lines wrap mid-word, the 'first character' of a continuation
     line is random, while the first character of a paragraph is chosen.
     This WOULD create a real signal — but it might reflect orthographic
     convention rather than meaning.
  e) Star markers: The transcription uses # comments for star types.
     These may not be perfectly consistent across transcribers. The
     dark/light/dotted distinction should be verified against images.
    """)

    # ─── SAVE ────────────────────────────────────────────────────────
    outpath = RESULTS_DIR / 'paragraph_initial_analysis.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.writelines(OUTPUT)
    pr(f"\nResults saved to {outpath}")


if __name__ == '__main__':
    main()
