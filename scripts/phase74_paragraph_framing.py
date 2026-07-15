#!/usr/bin/env python3
"""
Phase 74 — Paragraph Framing Analysis: Do Paragraphs Have Consistent
         Start/End Markers That Define "Code Blocks"?

═══════════════════════════════════════════════════════════════════════

USER OBSERVATION: Many paragraphs from f103r onwards start with a single
letter (gallows). Could they also END with specific letters, creating
"framed" codeblocks that each need to be read differently?

SKEPTICAL APPROACH:
  1. Extract BOTH initial AND final glyphs/words for every paragraph
  2. Compare final-glyph distribution vs BASELINE — are endings special?
  3. Cross-tabulate initial × final to find "frame types"
  4. Test: do different frame types have different internal statistics?
     (word count, vocabulary richness, character entropy, word entropy)
  5. Compare frame types across sections (herbal vs recipe vs balneo)
  6. Recipe section (f103r+): correlate frames with star types
  7. Sequential analysis: do frame types follow each other in patterns?
  8. CRITICAL NULL HYPOTHESIS: Initial glyphs are gallows because gallows
     are word-initial glyphs (I-M-F slot grammar). Final glyphs may just
     be word-final glyphs (y, n, r, l, m). If so, the "framing" is an
     ARTIFACT of the slot grammar, not a code-block structure.

CONTROLS:
  - Compare paragraph-final chars vs word-final chars in general
  - Compare paragraph-final chars vs LINE-final chars
  - If paragraph finals match general word finals, there's NO special
    paragraph-ending signal — it's just the slot grammar at work.
"""

import re, sys, io, math, json, os
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import clean_word, entropy, eva_to_glyphs, folio_section_v2 as folio_section

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
# EVA GLYPH PARSING
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']
ALL_GALLOWS = set(['p', 't', 'k', 'f'] + GALLOWS_TRI + GALLOWS_BI)


def eva_first_glyph(word):
    glyphs = eva_to_glyphs(word)
    return glyphs[0] if glyphs else ''

def eva_last_glyph(word):
    glyphs = eva_to_glyphs(word)
    return glyphs[-1] if glyphs else ''

def eva_first_char(word):
    return word[0].lower() if word else ''

def eva_last_char(word):
    return word[-1].lower() if word else ''

# ═══════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════

def folio_number(fname):
    m = re.match(r'f(\d+)', fname)
    return int(m.group(1)) if m else 0



def parse_folio_extended(filepath):
    """
    Parse a folio file. Return list of paragraphs, each containing:
      - first_word, last_word, first_glyph, last_glyph, first_char, last_char
      - all_words: all words in the paragraph
      - star_comment: star annotation (recipe section)
      - folio, section, line_tags
    Also return all_words (flat), all_lines with paragraph info.
    """
    paragraphs = []
    all_words = []
    all_lines = []
    current_star = None
    para_star = None
    current_para_words = []
    current_para_tags = []
    current_para_is_open = False

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()

        # Track star/comment annotations
        if line.startswith('#'):
            low = line.lower()
            if 'star' in low or 'point' in low:
                current_star = line.lstrip('#').strip()
            continue

        if not line:
            continue

        # Skip pure metadata lines
        m = re.match(r'<([^>]+)>', line)
        if not m:
            continue
        tag = m.group(1)
        rest = line[m.end():].strip()
        if not rest:
            continue

        is_para_start = '@P' in tag or '<%>' in rest
        is_para_end = '<$>' in rest

        # Clean text
        text = rest.replace('<%>', '').replace('<$>', '').strip()
        words = []
        for tok in re.split(r'[.\s]+', text):
            # Split on commas that separate words but keep intra-word commas
            for subtok in re.split(r',', tok):
                subtok = subtok.strip()
                cleaned = clean_word(subtok)
                if cleaned and len(cleaned) >= 1:
                    words.append(cleaned)

        if not words:
            continue

        all_words.extend(words)

        # Determine line type
        line_info = {
            'first_word': words[0],
            'last_word': words[-1],
            'words': words,
            'is_para_start': is_para_start,
            'is_para_end': is_para_end,
            'tag': tag,
        }
        all_lines.append(line_info)

        # If a new paragraph starts, close the previous one if open.
        # AUDIT A4: the previous paragraph's star lives in para_star; the
        # star seen just before THIS line (current_star) annotates the NEW
        # paragraph and must not be consumed or nulled here.
        if is_para_start and current_para_is_open and current_para_words:
            # Close previous paragraph (no explicit <$> ending)
            _finalize_para(paragraphs, current_para_words, current_para_tags,
                           para_star, False)
            current_para_words = []
            current_para_tags = []

        if is_para_start:
            current_para_is_open = True
            current_para_words = list(words)
            current_para_tags = [tag]
            # star was consumed
            para_star = current_star
            current_star = None
        elif current_para_is_open:
            current_para_words.extend(words)
            current_para_tags.append(tag)

        if is_para_end and current_para_is_open and current_para_words:
            # AUDIT A4: was `para_star if is_para_start else
            # getattr(parse_folio_extended, '_last_star', None)` — the
            # function attribute was never set anywhere, so every multi-line
            # paragraph lost its star annotation (test 7a degenerated to
            # "all NONE"). The captured para_star is correct in both cases.
            _finalize_para(paragraphs, current_para_words, current_para_tags,
                           para_star, True)
            current_para_is_open = False
            current_para_words = []
            current_para_tags = []
            para_star = None

    # Close any remaining open paragraph (star captured at its start)
    if current_para_is_open and current_para_words:
        _finalize_para(paragraphs, current_para_words, current_para_tags,
                       para_star, False)

    return paragraphs, all_words, all_lines


def _finalize_para(paragraphs, words, tags, star, has_end_marker):
    """Create a paragraph record and append it."""
    if not words:
        return
    para = {
        'first_word': words[0],
        'last_word': words[-1],
        'first_glyph': eva_first_glyph(words[0]),
        'last_glyph': eva_last_glyph(words[-1]),
        'first_char': eva_first_char(words[0]),
        'last_char': eva_last_char(words[-1]),
        'star_comment': star,
        'all_words': words,
        'n_words': len(words),
        'tags': tags,
        'has_end_marker': has_end_marker,
    }
    paragraphs.append(para)


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL HELPERS
# ═══════════════════════════════════════════════════════════════════════


def h_char_ratio(words):
    """H(c|prev) / H(c) — character conditional entropy ratio."""
    chars = list(''.join(words))
    if len(chars) < 50: return float('nan')
    uni = Counter(chars); tot = sum(uni.values())
    h_uni = -sum((c/tot)*math.log2(c/tot) for c in uni.values() if c > 0)
    if h_uni == 0: return float('nan')
    bi = Counter()
    for i in range(1, len(chars)):
        bi[(chars[i-1], chars[i])] += 1
    tot_bi = sum(bi.values())
    h_joint = -sum((c/tot_bi)*math.log2(c/tot_bi) for c in bi.values() if c > 0)
    prev_c = Counter()
    for (c1,c2), cnt in bi.items(): prev_c[c1] += cnt
    ptot = sum(prev_c.values())
    h_prev = -sum((c/ptot)*math.log2(c/ptot) for c in prev_c.values() if c > 0)
    return (h_joint - h_prev) / h_uni

def ttr(words, cap=None):
    """Type-token ratio."""
    sub = words[:cap] if cap else words
    return len(set(sub)) / len(sub) if sub else 0.0

def mean_wlen(words):
    return float(np.mean([len(w) for w in words])) if words else 0.0

def chi_squared_test(observed, expected_probs, total_obs):
    """Chi-squared goodness-of-fit. Returns (chi2, df, p_approx)."""
    all_cats = set(list(observed.keys()) + list(expected_probs.keys()))
    chi2 = 0.0
    df = 0
    for cat in sorted(all_cats):
        obs = observed.get(cat, 0)
        exp = expected_probs.get(cat, 0.0) * total_obs
        if exp < 1.0: continue
        chi2 += (obs - exp) ** 2 / exp
        df += 1
    df = max(df - 1, 1)
    if df > 0:
        z = ((chi2 / df) ** (1/3) - (1 - 2/(9*df))) / math.sqrt(2/(9*df))
        p = 0.5 * (1 + math.erf(-z / math.sqrt(2)))
    else:
        p = 1.0
    return chi2, df, p


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 75)
    pr("PHASE 74: PARAGRAPH FRAMING ANALYSIS")
    pr("Do paragraphs have consistent start/end markers defining code blocks?")
    pr("=" * 75)

    # ─── Load all folios ─────────────────────────────────────────────
    all_paragraphs = []
    all_words_flat = []
    all_lines_flat = []
    section_paras = defaultdict(list)
    folio_paras = defaultdict(list)

    folio_files = sorted(FOLIO_DIR.glob('*.txt'))
    for fp in folio_files:
        fnum = folio_number(fp.stem)
        sec = folio_section(fnum)
        paras, words, lines = parse_folio_extended(fp)
        all_words_flat.extend(words)
        all_lines_flat.extend(lines)
        for p in paras:
            p['section'] = sec
            p['folio'] = fp.stem
            p['folio_num'] = fnum
        all_paragraphs.extend(paras)
        section_paras[sec].extend(paras)
        folio_paras[fp.stem].extend(paras)

    pr(f"\nLoaded {len(folio_files)} folio files")
    pr(f"Total paragraphs: {len(all_paragraphs)}")
    pr(f"  with <$> end marker: {sum(1 for p in all_paragraphs if p['has_end_marker'])}")
    pr(f"  without end marker: {sum(1 for p in all_paragraphs if not p['has_end_marker'])}")
    pr(f"Total words: {len(all_words_flat)}")
    pr(f"Total lines: {len(all_lines_flat)}")
    pr(f"\nSection breakdown:")
    for sec in ['herbal', 'astro', 'balneo', 'recipe', 'cosmo']:
        n = len(section_paras.get(sec, []))
        if n > 0:
            pr(f"  {sec:12s}: {n:4d} paragraphs")

    # ═══════════════════════════════════════════════════════════════════
    # 1. BASELINE: Character frequencies in all positions
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("1. BASELINE: CHARACTER & GLYPH FREQUENCIES")
    pr("=" * 75)

    # Character frequency
    all_chars = list(''.join(all_words_flat))
    char_freq = Counter(all_chars)
    total_chars = len(all_chars)
    char_probs = {c: n/total_chars for c, n in char_freq.items()}

    # Word-final character frequency (baseline for paragraph endings)
    word_final_chars = Counter(w[-1].lower() for w in all_words_flat if w)
    total_wf = sum(word_final_chars.values())
    wf_probs = {c: n/total_wf for c, n in word_final_chars.items()}

    # Word-initial character frequency (baseline for paragraph starts)
    word_init_chars = Counter(w[0].lower() for w in all_words_flat if w)
    total_wi = sum(word_init_chars.values())
    wi_probs = {c: n/total_wi for c, n in word_init_chars.items()}

    # Word-final GLYPH frequency
    word_final_glyphs = Counter(eva_last_glyph(w) for w in all_words_flat if w)
    total_wfg = sum(word_final_glyphs.values())
    wfg_probs = {g: n/total_wfg for g, n in word_final_glyphs.items()}

    pr(f"\nTotal characters: {total_chars}")
    pr(f"\nWord-FINAL character distribution (all words):")
    for c, n in word_final_chars.most_common(10):
        pr(f"  '{c}': {n:6d} ({100*n/total_wf:.1f}%)")
    pr(f"\nWord-FINAL glyph distribution (all words):")
    for g, n in word_final_glyphs.most_common(10):
        pr(f"  '{g}': {n:6d} ({100*n/total_wfg:.1f}%)")
    pr(f"\nWord-INITIAL character distribution (all words):")
    for c, n in word_init_chars.most_common(10):
        pr(f"  '{c}': {n:6d} ({100*n/total_wi:.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # 2. PARAGRAPH-INITIAL ANALYSIS (reconfirm Phase 71)
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("2. PARAGRAPH-INITIAL CHARACTERS & GLYPHS")
    pr("=" * 75)

    para_first_chars = Counter(p['first_char'] for p in all_paragraphs)
    para_first_glyphs = Counter(p['first_glyph'] for p in all_paragraphs)
    n_paras = len(all_paragraphs)

    pr(f"\nParagraph-initial character (n={n_paras}):")
    for c, n in para_first_chars.most_common(15):
        wi_pct = wi_probs.get(c, 0) * 100
        para_pct = 100 * n / n_paras
        ratio = para_pct / wi_pct if wi_pct > 0 else float('inf')
        pr(f"  '{c}': {n:4d} ({para_pct:.1f}%)  "
           f"[word-initial baseline: {wi_pct:.1f}%, ratio: {ratio:.2f}x]")

    chi2_i, df_i, p_i = chi_squared_test(para_first_chars, wi_probs, n_paras)
    pr(f"\n  Chi-squared vs word-initial baseline: χ²={chi2_i:.1f}, df={df_i}, p≈{p_i:.2e}")
    gallows_init = sum(1 for p in all_paragraphs if p['first_glyph'] in ALL_GALLOWS)
    pr(f"  Gallows-initial paragraphs: {gallows_init}/{n_paras} ({100*gallows_init/n_paras:.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # 3. PARAGRAPH-FINAL ANALYSIS — THE NEW INVESTIGATION
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("3. PARAGRAPH-FINAL CHARACTERS & GLYPHS")
    pr("=" * 75)

    para_last_chars = Counter(p['last_char'] for p in all_paragraphs)
    para_last_glyphs = Counter(p['last_glyph'] for p in all_paragraphs)

    pr(f"\nParagraph-final character (n={n_paras}):")
    for c, n in para_last_chars.most_common(15):
        wf_pct = wf_probs.get(c, 0) * 100
        para_pct = 100 * n / n_paras
        ratio = para_pct / wf_pct if wf_pct > 0 else float('inf')
        pr(f"  '{c}': {n:4d} ({para_pct:.1f}%)  "
           f"[word-final baseline: {wf_pct:.1f}%, ratio: {ratio:.2f}x]")

    chi2_f, df_f, p_f = chi_squared_test(para_last_chars, wf_probs, n_paras)
    pr(f"\n  Chi-squared vs word-final baseline: χ²={chi2_f:.1f}, df={df_f}, p≈{p_f:.2e}")
    if p_f < 0.001:
        pr("  >>> SIGNIFICANT: paragraph-final chars differ from word-final baseline")
    else:
        pr("  >>> NOT significant — endings match general word endings")

    pr(f"\nParagraph-final glyph (n={n_paras}):")
    for g, n in para_last_glyphs.most_common(15):
        wfg_pct = wfg_probs.get(g, 0) * 100
        para_pct = 100 * n / n_paras
        ratio = para_pct / wfg_pct if wfg_pct > 0 else float('inf')
        pr(f"  '{g}': {n:4d} ({para_pct:.1f}%)  "
           f"[word-final baseline: {wfg_pct:.1f}%, ratio: {ratio:.2f}x]")

    chi2_fg, df_fg, p_fg = chi_squared_test(para_last_glyphs, wfg_probs, n_paras)
    pr(f"\n  Chi-squared vs word-final glyph baseline: χ²={chi2_fg:.1f}, df={df_fg}, p≈{p_fg:.2e}")

    # ─── CONTROL: Line-final vs paragraph-final ──────────────────────
    pr("\n" + "─" * 75)
    pr("3b. CONTROL: Line-final vs paragraph-final")
    pr("─" * 75)

    non_para_end_lines = [l for l in all_lines_flat if not l['is_para_end']]
    line_final_chars = Counter(l['last_word'][-1].lower() for l in non_para_end_lines if l['last_word'])
    total_lf = sum(line_final_chars.values())
    lf_probs = {c: n/total_lf for c, n in line_final_chars.items()}

    pr(f"\nNon-paragraph-ending lines: {total_lf}")
    pr(f"\n  {'Char':<6} {'Para%':>7} {'Line%':>7} {'WdEnd%':>7} {'P/L ratio':>10}")
    for c, n in para_last_chars.most_common(10):
        para_pct = 100 * n / n_paras
        line_pct = lf_probs.get(c, 0) * 100
        wf_pct = wf_probs.get(c, 0) * 100
        ratio = para_pct / line_pct if line_pct > 0 else float('inf')
        pr(f"  '{c}'    {para_pct:6.1f}% {line_pct:6.1f}% {wf_pct:6.1f}% {ratio:9.2f}x")

    chi2_pl, df_pl, p_pl = chi_squared_test(para_last_chars, lf_probs, n_paras)
    pr(f"\n  Chi-squared (para-final vs non-para line-final): χ²={chi2_pl:.1f}, df={df_pl}, p≈{p_pl:.2e}")
    if p_pl < 0.001:
        pr("  >>> SIGNIFICANT: para-final chars differ from general line endings")
    else:
        pr("  >>> NOT significant — paragraph endings match line endings")

    # ═══════════════════════════════════════════════════════════════════
    # 4. PARAGRAPH-FINAL WORD ANALYSIS
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("4. PARAGRAPH-FINAL WORDS")
    pr("=" * 75)

    para_last_words = Counter(p['last_word'] for p in all_paragraphs)
    global_word_freq = Counter(all_words_flat)
    total_words = len(all_words_flat)

    pr(f"\nTop 20 paragraph-final words:")
    for w, n in para_last_words.most_common(20):
        gw_pct = 100 * global_word_freq.get(w, 0) / total_words
        para_pct = 100 * n / n_paras
        ratio = para_pct / gw_pct if gw_pct > 0 else float('inf')
        pr(f"  '{w}': {n:4d} ({para_pct:.1f}%)  "
           f"[global: {gw_pct:.2f}%, ratio: {ratio:.1f}x]")

    # Words that ONLY appear paragraph-finally
    only_final = set()
    for w in para_last_words:
        # Count appearances NOT as last word of a paragraph
        non_final_count = global_word_freq.get(w, 0) - para_last_words[w]
        if non_final_count <= 0:
            only_final.add(w)

    pr(f"\nWords appearing ONLY as paragraph-final: {len(only_final)}")
    if only_final:
        examples = sorted(only_final)[:20]
        pr(f"  Examples: {examples}")

    # ═══════════════════════════════════════════════════════════════════
    # 5. CROSS-TABULATION: INITIAL × FINAL (Frame Types)
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("5. CROSS-TABULATION: INITIAL × FINAL GLYPH (Frame Types)")
    pr("=" * 75)

    frame_types = Counter((p['first_glyph'], p['last_glyph']) for p in all_paragraphs)

    # Summary by first glyph
    pr(f"\nFrame type distribution (initial → final):")
    for (fg, lg), n in frame_types.most_common(25):
        pr(f"  {fg:>5s} → {lg:<5s}: {n:4d} ({100*n/n_paras:.1f}%)")

    # Contingency: are init and final INDEPENDENT?
    pr(f"\n  INDEPENDENCE TEST: If init and final are independent,")
    pr(f"  P(init=X, final=Y) = P(init=X) × P(final=Y)")
    pr()

    init_probs = {c: n/n_paras for c, n in para_first_glyphs.items()}
    final_probs = {c: n/n_paras for c, n in para_last_glyphs.items()}

    # Chi-squared test for independence
    chi2_indep = 0.0
    df_indep = 0
    for (ig, fg), obs in frame_types.items():
        exp = init_probs.get(ig, 0) * final_probs.get(fg, 0) * n_paras
        if exp >= 1.0:
            chi2_indep += (obs - exp) ** 2 / exp
            df_indep += 1
    df_indep = max(df_indep - 1, 1)
    if df_indep > 0:
        z = ((chi2_indep / df_indep) ** (1/3) - (1 - 2/(9*df_indep))) / math.sqrt(2/(9*df_indep))
        p_indep = 0.5 * (1 + math.erf(-z / math.sqrt(2)))
    else:
        p_indep = 1.0

    pr(f"  Chi-squared independence test: χ²={chi2_indep:.1f}, df={df_indep}, p≈{p_indep:.2e}")
    if p_indep < 0.001:
        pr("  >>> SIGNIFICANT: initial and final glyphs are NOT independent")
        pr("  >>> (But this could still be section-driven — see section analysis)")
    else:
        pr("  >>> NOT significant — initial and final glyphs appear independent")

    # ─── Show conditional distributions ──────────────────────────────
    pr(f"\n  Final glyph distribution GIVEN initial glyph:")
    for ig in ['p', 't', 'k', 'f', 'q', 'o', 'd']:
        paras_with_ig = [p for p in all_paragraphs if p['first_glyph'] == ig]
        if len(paras_with_ig) < 5:
            continue
        fg_dist = Counter(p['last_glyph'] for p in paras_with_ig)
        n_ig = len(paras_with_ig)
        top3 = fg_dist.most_common(5)
        top_str = ', '.join(f"{g}={100*c/n_ig:.0f}%" for g, c in top3)
        pr(f"    init='{ig}' (n={n_ig:3d}): {top_str}")

    # ═══════════════════════════════════════════════════════════════════
    # 6. SECTION-BY-SECTION FRAME ANALYSIS
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("6. SECTION-BY-SECTION PARAGRAPH FRAMING")
    pr("=" * 75)

    for sec in ['herbal', 'astro', 'balneo', 'recipe']:
        paras = section_paras.get(sec, [])
        if len(paras) < 5:
            continue
        n_sec = len(paras)

        pr(f"\n  === {sec.upper()} ({n_sec} paragraphs) ===")

        # Initial
        sec_init = Counter(p['first_glyph'] for p in paras)
        top_init = sec_init.most_common(5)
        pr(f"    First glyph:  {', '.join(f'{g}={n}({100*n/n_sec:.0f}%)' for g,n in top_init)}")

        # Final
        sec_final = Counter(p['last_glyph'] for p in paras)
        top_final = sec_final.most_common(5)
        pr(f"    Last glyph:   {', '.join(f'{g}={n}({100*n/n_sec:.0f}%)' for g,n in top_final)}")

        # Frame types
        sec_frames = Counter((p['first_glyph'], p['last_glyph']) for p in paras)
        top_frames = sec_frames.most_common(5)
        pr(f"    Top frames:   {', '.join(f'{ig}→{fg}={n}' for (ig,fg),n in top_frames)}")

        # Mean paragraph length
        wlens = [p['n_words'] for p in paras]
        pr(f"    Mean para len: {np.mean(wlens):.1f} words (range {min(wlens)}-{max(wlens)})")

        # Last word analysis
        sec_last_words = Counter(p['last_word'] for p in paras)
        top_lw = sec_last_words.most_common(5)
        pr(f"    Top final words: {', '.join(f'{w}={n}' for w,n in top_lw)}")

    # ═══════════════════════════════════════════════════════════════════
    # 7. RECIPE SECTION DEEP DIVE (f103r onwards)
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("7. RECIPE SECTION (f103r-f116v) DEEP DIVE")
    pr("=" * 75)

    recipe_paras = section_paras.get('recipe', [])
    n_recipe = len(recipe_paras)

    if n_recipe < 10:
        pr("  Not enough recipe paragraphs for analysis.")
    else:
        # ─── 7a: Star type vs frame type correlation ─────────────────
        pr(f"\n  7a. STAR TYPE vs FRAME TYPE CORRELATION")
        pr("  " + "─" * 65)

        star_frames = defaultdict(list)
        for p in recipe_paras:
            star = p.get('star_comment', None)
            if star:
                # Normalize star type
                sl = star.lower()
                if 'dark' in sl:
                    stype = 'DARK'
                elif 'dotted' in sl:
                    stype = 'DOTTED'
                elif 'light' in sl:
                    stype = 'LIGHT'
                else:
                    stype = 'OTHER'
            else:
                stype = 'NONE'
            star_frames[stype].append(p)

        for stype in sorted(star_frames.keys()):
            sp = star_frames[stype]
            n_st = len(sp)
            if n_st < 3:
                continue
            init_d = Counter(p['first_glyph'] for p in sp)
            final_d = Counter(p['last_glyph'] for p in sp)
            frame_d = Counter((p['first_glyph'], p['last_glyph']) for p in sp)

            pr(f"\n    {stype} stars (n={n_st}):")
            top_i = init_d.most_common(3)
            top_f = final_d.most_common(3)
            top_fr = frame_d.most_common(5)
            pr(f"      Init:   {', '.join(f'{g}={100*n/n_st:.0f}%' for g,n in top_i)}")
            pr(f"      Final:  {', '.join(f'{g}={100*n/n_st:.0f}%' for g,n in top_f)}")
            pr(f"      Frames: {', '.join(f'{ig}→{fg}={n}' for (ig,fg),n in top_fr)}")

        # ─── 7b: Sequential frame patterns ───────────────────────────
        pr(f"\n  7b. SEQUENTIAL FRAME PATTERNS (recipe section)")
        pr("  " + "─" * 65)

        # Sort recipe paragraphs by folio then position
        recipe_sorted = sorted(recipe_paras, key=lambda p: (p['folio_num'], p['folio'], p['tags'][0] if p['tags'] else ''))

        # Bigram analysis of frame types
        frame_seq = [(p['first_glyph'], p['last_glyph']) for p in recipe_sorted]
        frame_bigrams = Counter()
        for i in range(1, len(frame_seq)):
            frame_bigrams[(frame_seq[i-1], frame_seq[i])] += 1

        pr(f"\n    Frame-to-frame transitions (top 15):")
        for (f1, f2), n in frame_bigrams.most_common(15):
            pr(f"      ({f1[0]}→{f1[1]}) then ({f2[0]}→{f2[1]}): {n}")

        # Is there a pattern in initial glyphs across sequential paragraphs?
        init_seq = [p['first_glyph'] for p in recipe_sorted]
        init_bigrams = Counter()
        for i in range(1, len(init_seq)):
            init_bigrams[(init_seq[i-1], init_seq[i])] += 1

        pr(f"\n    Initial glyph bigrams (paragraph N → paragraph N+1):")
        for (g1, g2), n in init_bigrams.most_common(10):
            pr(f"      {g1} → {g2}: {n}")

        # Autocorrelation: does the same initial glyph repeat?
        same_init = sum(1 for i in range(1, len(init_seq)) if init_seq[i] == init_seq[i-1])
        expected_same = sum(c * (c-1) for c in Counter(init_seq).values()) / max(len(init_seq) - 1, 1)
        pr(f"\n    Same initial glyph in consecutive paragraphs:")
        pr(f"      Observed: {same_init}/{len(init_seq)-1} ({100*same_init/(len(init_seq)-1):.1f}%)")
        pr(f"      Expected (if random): {expected_same:.1f} ({100*expected_same/(len(init_seq)-1):.1f}%)")

        # ─── 7c: Paragraph ending patterns in recipe section ─────────
        pr(f"\n  7c. RECIPE FINAL WORD/GLYPH DETAILED ANALYSIS")
        pr("  " + "─" * 65)

        recipe_last_glyphs = Counter(p['last_glyph'] for p in recipe_paras)
        recipe_last_words = Counter(p['last_word'] for p in recipe_paras)

        pr(f"\n    Final glyph distribution (recipe, n={n_recipe}):")
        for g, n in recipe_last_glyphs.most_common(10):
            wfg_pct = wfg_probs.get(g, 0) * 100
            r_pct = 100 * n / n_recipe
            ratio = r_pct / wfg_pct if wfg_pct > 0 else float('inf')
            pr(f"      '{g}': {n:4d} ({r_pct:.1f}%)  [word-final baseline: {wfg_pct:.1f}%, ratio: {ratio:.2f}x]")

        pr(f"\n    Final word distribution (recipe, top 15):")
        for w, n in recipe_last_words.most_common(15):
            pr(f"      '{w}': {n:3d} ({100*n/n_recipe:.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # 8. DO FRAME TYPES HAVE DIFFERENT INTERNAL STATISTICS?
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("8. INTERNAL STATISTICS BY FRAME TYPE")
    pr("   (Do different frames = different 'code blocks'?)")
    pr("=" * 75)

    # Group paragraphs by initial glyph (the clearest signal)
    init_groups = defaultdict(list)
    for p in all_paragraphs:
        init_groups[p['first_glyph']].append(p)

    pr(f"\n  Statistics by initial glyph (minimum 10 paragraphs):")
    pr(f"  {'Init':<6} {'N':>4} {'MeanLen':>8} {'MeanWL':>7} {'TTR':>6} {'h_char':>7}  Top final glyphs")

    for ig, paras in sorted(init_groups.items(), key=lambda x: -len(x[1])):
        if len(paras) < 10:
            continue
        words_all = [w for p in paras for w in p['all_words']]
        mlen = np.mean([p['n_words'] for p in paras])
        mwl = mean_wlen(words_all)
        t = ttr(words_all, 500)
        hc = h_char_ratio(words_all) if len(words_all) >= 100 else float('nan')
        fg_dist = Counter(p['last_glyph'] for p in paras)
        top_fg = ', '.join(f"{g}={100*n/len(paras):.0f}%" for g, n in fg_dist.most_common(3))

        pr(f"  {ig:<6} {len(paras):4d} {mlen:8.1f} {mwl:7.2f} {t:6.3f} {hc:7.4f}  {top_fg}")

    # ─── Compare p-initial vs t-initial vs k-initial internal stats ──
    pr(f"\n  Pairwise comparison of major initial-glyph groups:")
    major_inits = ['p', 't', 'k', 'f']
    for i, g1 in enumerate(major_inits):
        for g2 in major_inits[i+1:]:
            p1 = init_groups.get(g1, [])
            p2 = init_groups.get(g2, [])
            if len(p1) < 10 or len(p2) < 10:
                continue
            w1 = [w for p in p1 for w in p['all_words']]
            w2 = [w for p in p2 for w in p['all_words']]
            hc1 = h_char_ratio(w1) if len(w1) >= 100 else float('nan')
            hc2 = h_char_ratio(w2) if len(w2) >= 100 else float('nan')
            ttr1 = ttr(w1, 500)
            ttr2 = ttr(w2, 500)
            mwl1 = mean_wlen(w1)
            mwl2 = mean_wlen(w2)
            # Vocabulary overlap
            v1 = set(w1); v2 = set(w2)
            jaccard = len(v1 & v2) / len(v1 | v2) if (v1 | v2) else 0
            pr(f"    {g1} vs {g2}: h_char {hc1:.4f} vs {hc2:.4f} (Δ={hc1-hc2:+.4f}), "
               f"TTR {ttr1:.3f} vs {ttr2:.3f}, wlen {mwl1:.2f} vs {mwl2:.2f}, "
               f"vocab Jaccard={jaccard:.3f}")

    # ═══════════════════════════════════════════════════════════════════
    # 9. RECIPE-SPECIFIC FRAME TYPE INTERNAL ANALYSIS
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("9. RECIPE SECTION: FRAME TYPE INTERNAL STATISTICS")
    pr("=" * 75)

    recipe_init_groups = defaultdict(list)
    for p in recipe_paras:
        recipe_init_groups[p['first_glyph']].append(p)

    pr(f"\n  {'Init':<6} {'N':>4} {'MeanLen':>8} {'MeanWL':>7} {'TTR':>6} {'h_char':>7}  Top final")
    for ig, paras in sorted(recipe_init_groups.items(), key=lambda x: -len(x[1])):
        if len(paras) < 5:
            continue
        words_all = [w for p in paras for w in p['all_words']]
        mlen = np.mean([p['n_words'] for p in paras])
        mwl = mean_wlen(words_all)
        t = ttr(words_all, 500)
        hc = h_char_ratio(words_all) if len(words_all) >= 100 else float('nan')
        fg_dist = Counter(p['last_glyph'] for p in paras)
        top_fg = ', '.join(f"{g}={100*n/len(paras):.0f}%" for g, n in fg_dist.most_common(3))
        pr(f"  {ig:<6} {len(paras):4d} {mlen:8.1f} {mwl:7.2f} {t:6.3f} {hc:7.4f}  {top_fg}")

    # ─── Recipe: different frames = different word distributions? ─────
    pr(f"\n  Vocabulary overlap between recipe frame types:")
    recipe_major = ['p', 't', 'k', 'f']
    for i, g1 in enumerate(recipe_major):
        for g2 in recipe_major[i+1:]:
            p1 = recipe_init_groups.get(g1, [])
            p2 = recipe_init_groups.get(g2, [])
            if len(p1) < 5 or len(p2) < 5:
                continue
            w1 = set(w for p in p1 for w in p['all_words'])
            w2 = set(w for p in p2 for w in p['all_words'])
            jaccard = len(w1 & w2) / len(w1 | w2) if (w1 | w2) else 0
            only1 = w1 - w2; only2 = w2 - w1
            pr(f"    {g1} vs {g2}: Jaccard={jaccard:.3f}, only-{g1}={len(only1)}, only-{g2}={len(only2)}")

    # ═══════════════════════════════════════════════════════════════════
    # 10. THE "CODE BLOCK" HYPOTHESIS TEST
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("10. THE 'CODE BLOCK' HYPOTHESIS: ARE FRAMES MEANINGFUL?")
    pr("=" * 75)

    pr("""
  HYPOTHESIS: Each paragraph is a "code block" where the initial (and
  possibly final) glyph specifies how to read the content differently.

  PREDICTIONS if this is true:
    A) Initial glyphs should be highly concentrated (→ few "block types")
    B) Final glyphs should ALSO be concentrated (→ block-end markers)
    C) Initial and final should be CORRELATED (→ frame defines block)
    D) Different frame types should have DIFFERENT internal statistics
       (different h_char, different vocabulary, different word distributions)
    E) Frame types should NOT change with section — the "reading rule"
       should be consistent across the manuscript

  PREDICTIONS if this is just the I-M-F slot grammar:
    A) Initial concentration = gallows are word-initial glyphs ✓
    B) Final concentration = y/n/r/l/m are word-final glyphs ✓
    C) NO special correlation beyond section effects
    D) No meaningful difference in internal statistics
    E) Section differences reflect content, not reading rules
""")

    # Test A: Initial concentration
    top1_init = para_first_glyphs.most_common(1)[0]
    top4_init = sum(n for _, n in para_first_glyphs.most_common(4))
    pr(f"  Test A (initial concentration):")
    pr(f"    Top initial: '{top1_init[0]}' = {100*top1_init[1]/n_paras:.1f}%")
    pr(f"    Top 4 sum: {100*top4_init/n_paras:.1f}%")
    pr(f"    Verdict: {'CONCENTRATED' if top4_init/n_paras > 0.8 else 'MODERATE'}")

    # Test B: Final concentration
    top1_final = para_last_glyphs.most_common(1)[0]
    top4_final = sum(n for _, n in para_last_glyphs.most_common(4))
    pr(f"\n  Test B (final concentration):")
    pr(f"    Top final: '{top1_final[0]}' = {100*top1_final[1]/n_paras:.1f}%")
    pr(f"    Top 4 sum: {100*top4_final/n_paras:.1f}%")
    pr(f"    Word-final baseline top-4: {100*sum(n for _,n in word_final_glyphs.most_common(4))/total_wfg:.1f}%")
    pr(f"    Verdict: {'CONCENTRATED' if top4_final/n_paras > 0.8 else 'NOT CONCENTRATED'}")
    pr(f"    vs baseline: {'MORE concentrated' if top4_final/n_paras > sum(n for _,n in word_final_glyphs.most_common(4))/total_wfg + 0.05 else 'SIMILAR to baseline'}")

    # Test C: Independence
    pr(f"\n  Test C (initial-final correlation):")
    pr(f"    Chi-squared independence: χ²={chi2_indep:.1f}, p≈{p_indep:.2e}")
    pr(f"    Verdict: {'CORRELATED' if p_indep < 0.01 else 'INDEPENDENT'}")

    # Test D: Internal statistics difference
    pr(f"\n  Test D (different internal statistics by frame type):")
    if len(init_groups.get('p', [])) >= 10 and len(init_groups.get('t', [])) >= 10:
        w_p = [w for p in init_groups['p'] for w in p['all_words']]
        w_t = [w for p in init_groups['t'] for w in p['all_words']]
        hc_p = h_char_ratio(w_p)
        hc_t = h_char_ratio(w_t)
        pr(f"    h_char: p-initial={hc_p:.4f}, t-initial={hc_t:.4f}, Δ={abs(hc_p-hc_t):.4f}")
        pr(f"    wlen: p={mean_wlen(w_p):.3f}, t={mean_wlen(w_t):.3f}")
        pr(f"    TTR: p={ttr(w_p, 500):.3f}, t={ttr(w_t, 500):.3f}")
        v_p = set(w_p); v_t = set(w_t)
        j = len(v_p & v_t) / len(v_p | v_t) if (v_p | v_t) else 0
        pr(f"    Vocab Jaccard: {j:.3f}")

        delta_hc = abs(hc_p - hc_t)
        if delta_hc > 0.03:
            pr(f"    Verdict: DIFFERENT internal statistics (Δh_char={delta_hc:.4f} > 0.03)")
        else:
            pr(f"    Verdict: SIMILAR internal statistics (Δh_char={delta_hc:.4f} ≤ 0.03)")

    # Test E: Cross-section consistency
    pr(f"\n  Test E (cross-section consistency of frame distribution):")
    for sec in ['herbal', 'balneo', 'recipe']:
        sp = section_paras.get(sec, [])
        if len(sp) < 10:
            continue
        init_d = Counter(p['first_glyph'] for p in sp)
        n_s = len(sp)
        top3 = ', '.join(f"{g}={100*n/n_s:.0f}%" for g, n in init_d.most_common(3))
        final_d = Counter(p['last_glyph'] for p in sp)
        ftop3 = ', '.join(f"{g}={100*n/n_s:.0f}%" for g, n in final_d.most_common(3))
        pr(f"    {sec:12s}: init=[{top3}]  final=[{ftop3}]")

    # ═══════════════════════════════════════════════════════════════════
    # 11. RECIPE: INDIVIDUAL PARAGRAPH DUMP (first 30)
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("11. RECIPE PARAGRAPHS: FIRST 30 (folio, star, initial→final, length)")
    pr("=" * 75)

    recipe_sorted_2 = sorted(recipe_paras,
                              key=lambda p: (p['folio_num'], p['folio'],
                                             p['tags'][0] if p['tags'] else ''))
    pr(f"\n  {'#':>3} {'Folio':<8} {'Star':<25} {'Init':>5} {'Final':>5} {'Nw':>4} {'First word':<16} {'Last word':<16}")
    for i, p in enumerate(recipe_sorted_2[:30]):
        star = (p.get('star_comment') or 'none')[:24]
        pr(f"  {i+1:3d} {p['folio']:<8} {star:<25} {p['first_glyph']:>5} {p['last_glyph']:>5} {p['n_words']:4d} {p['first_word'][:15]:<16} {p['last_word'][:15]:<16}")

    # ═══════════════════════════════════════════════════════════════════
    # 12. SECOND-TO-LAST AND LAST WORD PATTERNS
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("12. PARAGRAPH-ENDING WORD PAIRS (last 2 words)")
    pr("=" * 75)

    ending_pairs = Counter()
    for p in all_paragraphs:
        if len(p['all_words']) >= 2:
            ending_pairs[(p['all_words'][-2], p['all_words'][-1])] += 1

    pr(f"\n  Top 15 paragraph-ending word pairs:")
    for (w1, w2), n in ending_pairs.most_common(15):
        pr(f"    '{w1} {w2}': {n}")

    # ═══════════════════════════════════════════════════════════════════
    # 13. SKEPTICAL SELF-ASSESSMENT
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "=" * 75)
    pr("13. SKEPTICAL SELF-ASSESSMENT")
    pr("=" * 75)
    pr("""
  WHAT WE FOUND:
    1. Paragraph-initial glyphs are STRONGLY concentrated on gallows (p,t,k,f)
       — confirmed from Phase 71.
    2. Paragraph-final glyphs: [to be filled by results]
    3. Initial × final correlation: [to be filled by results]
    4. Internal statistics difference: [to be filled by results]

  CRITICAL QUESTIONS:
    a) Is the initial-glyph concentration real or a slot-grammar artifact?
       → The I-M-F grammar means gallows CAN start words. But the
         paragraph-initial rate (82%) far exceeds the word-initial rate
         for gallows (~11%). So it's NOT just slot grammar.
    b) Is the final-glyph concentration (if any) beyond what word-final
       frequencies predict?
       → This is the KEY question. If paragraph-final matches word-final
         baseline, there's no special paragraph-end marker.
    c) Could the "framing" be a transcription artifact?
       → The <%> and <$> markers in the IVTFF format come from the
         transcription, not the manuscript. But paragraph breaks are
         visible in the manuscript as indentation/gaps.
    d) Could different initial glyphs just be different WORDS that happen
       to start with gallows, carrying different semantic content?
       → Phase 71 showed 451 words appear ONLY paragraph-initially.
         These might be heading/title words.
""")

    # ═══════════════════════════════════════════════════════════════════
    # SAVE RESULTS
    # ═══════════════════════════════════════════════════════════════════
    outpath = RESULTS_DIR / 'phase74_paragraph_framing.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"\nResults saved to {outpath}")

    # Save structured data for further analysis
    json_data = {
        'n_paragraphs': n_paras,
        'para_first_chars': dict(para_first_chars),
        'para_last_chars': dict(para_last_chars),
        'para_first_glyphs': dict(para_first_glyphs),
        'para_last_glyphs': dict(para_last_glyphs),
        'frame_types': {f"{k[0]}->{k[1]}": v for k, v in frame_types.items()},
        'word_final_glyphs': dict(word_final_glyphs.most_common(20)),
        'word_init_chars': dict(word_init_chars.most_common(20)),
        'chi2_final_vs_baseline': {'chi2': chi2_f, 'df': df_f, 'p': p_f},
        'chi2_independence': {'chi2': chi2_indep, 'df': df_indep, 'p': p_indep},
    }
    json_path = RESULTS_DIR / 'phase74_paragraph_framing.json'
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    pr(f"JSON data saved to {json_path}")


if __name__ == '__main__':
    main()
