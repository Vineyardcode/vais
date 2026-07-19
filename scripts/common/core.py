"""Shared analysis helpers extracted verbatim from the test scripts.

Every function below is a byte-for-byte copy (modulo the attribution
comment) of the dominant variant found across scripts/, selected by
AST hash with alpha-renaming. tools/build_common.py regenerates this
file; tools/rewrite_scripts.py swaps matching local defs for imports.
Divergent minority variants keep suffixed names (e.g. *_v2).
"""

import io
import json
import urllib.request

import math

import re

import sys

from collections import Counter, defaultdict

from pathlib import Path

try:
    import numpy as np
except ImportError:  # numpy optional for the pure-stdlib helpers
    np = None

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']

GRAM_PREFIXES = ['qo','so','do','q','o','d','y']

PREFIXES = ['qo','q','so','do','o','d','s','y']

SLOT1 = {'ch', 'sh', 'y'}

SLOT2_RUNS = {'e'}

SLOT2_SINGLE = {'q', 'a'}

SLOT3 = {'o'}

SLOT4_RUNS = {'i'}

SLOT4_SINGLE = {'d'}

SLOT5 = {'y', 'p', 'f', 'k', 'l', 'r', 's', 't',
         'cth', 'ckh', 'cph', 'cfh', 'n', 'm'}

SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

FOLIO_DIR = PROJECT_ROOT / 'folios'

DATA_DIR = PROJECT_ROOT / 'data'

RESULTS_DIR = PROJECT_ROOT / 'results'

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']

BENCH_GALLOWS = ["cth", "ckh", "cph", "cfh"]

COMPOUND_GCH = ["tch", "kch", "pch", "fch"]

COMPOUND_GSH = ["tsh", "ksh", "psh", "fsh"]

GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']

MAX_CHUNKS = 6

SIMPLE_GALLOWS = ["t", "k", "f", "p"]


# Declared variant of MORPH_SUFFIXES used by the root-lexicon translation-era
# family (root_lexicon_translation .. derivational_prefix_paradox): no 'sy',
# and 'eedy' is tried before 'edy'/'ody'. Order is
# significant (parse_morphology takes the first endswith match), so these
# two lists produce different decompositions BY DESIGN. The scripts keep a
# local literal copy so the web UI exposes it as a tunable parameter; this
# constant is the canonical reference they are checked against.
MORPH_SUFFIXES_NO_SY = ['aiin', 'ain', 'iin', 'in', 'ar', 'or', 'al', 'ol',
        'eedy', 'edy', 'ody', 'dy', 'ey', 'y']

MORPH_SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol',
        'edy','ody','eedy','dy','sy','ey','y']


# ── parse_morphology: gallows-strip morphology family (19 scripts; two
#    formatting-variant copies unified — semantically identical)
def parse_morphology(stripped_word):
    w = stripped_word
    prefix = ""
    suffix = ""
    for pf in PREFIXES:
        if w.startswith(pf) and len(w) > len(pf) + 1:
            prefix = pf
            w = w[len(pf):]
            break
    for sf in MORPH_SUFFIXES:
        if w.endswith(sf) and len(w) > len(sf):
            suffix = sf
            w = w[:-len(sf)]
            break
    return prefix, w, suffix


# ── get_collapsed: word_order_syntax_test statistical family (20 scripts) — composed of
#    strip_gallows_v2 (string-returning) + collapse_e
def get_collapsed(w): return collapse_e(strip_gallows_v2(w))


def result_path(name):
    """Canonical location for inter-script result files: results/<name>.

    All scripts read AND write their result JSONs through this helper, so
    producers and consumers can never drift apart again (pre-refactor,
    the earliest scripts used the project root while later scripts and the
    committed snapshots used results/).
    """
    RESULTS_DIR.mkdir(exist_ok=True)
    return RESULTS_DIR / name


def utf8_stdout():
    """The UTF-8 stdout wrapper used by 81 scripts (idempotent)."""
    if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    return sys.stdout

def char_bigram_predictability(char_list):
    """H(c|prev) / H(c) — how much does the previous char reduce entropy?"""
    unigram = Counter(char_list)
    total = sum(unigram.values())
    if total < 2:
        return 1.0
    h_uni = -sum((c/total) * math.log2(c/total) for c in unigram.values() if c > 0)

    bigrams = Counter()
    for i in range(1, len(char_list)):
        bigrams[(char_list[i-1], char_list[i])] += 1
    total_bi = sum(bigrams.values())

    h_joint = -sum((c/total_bi) * math.log2(c/total_bi) for c in bigrams.values() if c > 0)
    prev_counts = Counter()
    for (c1, c2), cnt in bigrams.items():
        prev_counts[c1] += cnt
    prev_total = sum(prev_counts.values())
    h_prev = -sum((c/prev_total) * math.log2(c/prev_total) for c in prev_counts.values() if c > 0)
    h_cond = h_joint - h_prev
    if h_uni == 0:
        return 1.0
    return h_cond / h_uni

def chunk_to_str(chunk):
    return '.'.join(chunk)

# ─────────────────────────────────────────────────────────────────────────
# FOLIO -> SECTION TAXONOMIES (consolidated, explicitly named)
#
# Two independent classification methods coexist across research eras:
#   by NUMBER (folio number ranges)  -> herbal-A/B, zodiac, bio, cosmo,
#                                       pharma, text, unknown
#   by HEADER (IVTFF header comments)-> herbal, astro, pharma, bio, text,
#                                       other (+ Currier language A/B)
# They are NOT interchangeable; each script keeps the taxonomy it was
# written with. Named aliases below make the choice explicit at import
# sites. classify_folio_labels_taxonomy is a genuine variant used only by
# herbal_labels.py: folios 58-64 count as herbal-B there (elsewhere:
# 58 -> herbal-A, 59-64 -> unknown).
# ─────────────────────────────────────────────────────────────────────────

def classify_folio_header_section(header_lines):
    """Header-comment taxonomy, section only (root_type_grammar family)."""
    text = "\n".join(header_lines).lower()
    if "herbal" in text:
        return "herbal"
    elif "astro" in text or "cosmo" in text or "star" in text or "zodiac" in text:
        return "astro"
    elif "pharm" in text or "recipe" in text or "balneo" in text:
        return "pharma"
    elif "biolog" in text or "bathy" in text:
        return "bio"
    elif "text only" in text:
        return "text"
    return "other"


def classify_folio_labels_taxonomy(folio_id):
    """Number taxonomy VARIANT used by herbal_labels.py (58-64 -> herbal-B)."""
    m = re.match(r'f(\d+)', folio_id)
    if not m:
        return "unknown"
    num = int(m.group(1))
    if num <= 25:
        return "herbal-A"
    elif 26 <= num <= 56:
        return "herbal-A"
    elif num in (57,):
        return "herbal-A"
    elif 58 <= num <= 66:
        return "herbal-B" if num not in (65, 66) else "herbal-A"
    elif 67 <= num <= 73:
        return "zodiac"
    elif 75 <= num <= 84:
        return "bio"
    elif 85 <= num <= 86:
        return "cosmo"
    elif 87 <= num <= 102:
        if num in (88, 89, 99, 100, 101, 102):
            return "pharma"
        return "herbal-B"
    elif 103 <= num <= 116:
        return "text"
    return "unknown"


def classify_folio(filepath):
    stem = filepath.stem
    m = re.match(r'f(\d+)', stem)
    if not m:
        return "unknown"
    num = int(m.group(1))
    if num <= 58 or 65 <= num <= 66:
        return "herbal-A"
    elif 67 <= num <= 73:
        return "zodiac"
    elif 75 <= num <= 84:
        return "bio"
    elif 85 <= num <= 86:
        return "cosmo"
    elif 87 <= num <= 102:
        if num in (88, 89, 99, 100, 101, 102):
            return "pharma"
        return "herbal-B"
    elif 103 <= num <= 116:
        return "text"
    return "unknown"

def classify_folio_v2(stem):
    m_num = re.match(r'f(\d+)', stem)
    if not m_num: return "unknown"
    num = int(m_num.group(1))
    if num <= 58 or 65 <= num <= 66: return "herbal-A"
    elif 67 <= num <= 73: return "zodiac"
    elif 75 <= num <= 84: return "bio"
    elif 85 <= num <= 86: return "cosmo"
    elif 87 <= num <= 102:
        return "pharma" if num in (88,89,99,100,101,102) else "herbal-B"
    elif 103 <= num <= 116: return "text"
    return "unknown"

def classify_folio_v3(header_lines):
    text = "\n".join(header_lines).lower()
    if "herbal" in text:
        section = "herbal"
    elif "astro" in text or "cosmo" in text or "star" in text or "zodiac" in text:
        section = "astro"
    elif "pharm" in text or "recipe" in text or "balneo" in text:
        section = "pharma"
    elif "biolog" in text or "bathy" in text:
        section = "bio"
    elif "text only" in text:
        section = "text"
    else:
        section = "other"
    lang = "B" if "language b" in text else "A" if "language a" in text else "?"
    return section, lang

def clean_word(tok):
    tok = re.sub(r'\[([^:\]]+):[^\]]*\]', r'\1', tok)
    tok = re.sub(r'\{[^}]*\}', '', tok)
    tok = re.sub(r'[^a-z]', '', tok.lower())
    return tok

def clean_word_v2(tok):
    tok = re.sub(r'[^a-z]', '', tok.lower())
    return tok if len(tok) >= 1 else ''

def collapse_e(w): return re.sub(r'e+', 'e', w)

def collapse_echains(word):
    return re.sub(r'e+', 'e', word)

def compute_H(counts, total):
    H = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            H -= p * math.log2(p)
    return H

def compute_mi(x_arr, y_arr):
    """Mutual information between two categorical arrays."""
    N = len(x_arr)
    if N == 0: return 0.0
    joint = Counter(zip(x_arr, y_arr))
    x_counts = Counter(x_arr)
    y_counts = Counter(y_arr)
    mi = 0.0
    for (x,y), n_xy in joint.items():
        p_xy = n_xy / N
        p_x = x_counts[x] / N
        p_y = y_counts[y] / N
        if p_xy > 0 and p_x > 0 and p_y > 0:
            mi += p_xy * math.log2(p_xy / (p_x * p_y))
    return mi

def conditional_entropy(bigrams_counter, unigram_counter):
    """H(Y|X) from joint bigram counts and marginal X counts."""
    # H(Y|X) = H(X,Y) - H(X)
    h_joint = entropy(bigrams_counter)
    h_x = entropy(unigram_counter)
    return h_joint - h_x

def entropy(counter):
    total = sum(counter.values())
    if total == 0:
        return 0.0
    return -sum((c/total)*math.log2(c/total) for c in counter.values() if c > 0)

def entropy_v2(counter):
    total = sum(counter.values())
    if total == 0:
        return 0.0
    h = 0.0
    for count in counter.values():
        if count > 0:
            p = count / total
            h -= p * math.log2(p)
    return h

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

def eva_to_glyphs_v2(word):
    glyphs = []
    i = 0
    while i < len(word):
        if i+2 < len(word) and word[i:i+3] in ('cth','ckh','cph','cfh'):
            glyphs.append(word[i:i+3]); i += 3
        elif i+1 < len(word) and word[i:i+2] in ('ch','sh','th','kh','ph','fh'):
            glyphs.append(word[i:i+2]); i += 2
        else:
            glyphs.append(word[i]); i += 1
    return glyphs

def extract_words(text):
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

def fetch_gutenberg(ebook_id):
    """Project Gutenberg text with header/footer stripped.

    Downloads are cached raw in data/gutenberg_cache/pg<id>.txt, so once the
    cache is populated (tools/prefetch_gutenberg.py) every network test runs
    fully offline and reproducibly.
    """
    cache_dir = DATA_DIR / 'gutenberg_cache'
    cache = cache_dir / f'pg{ebook_id}.txt'
    if cache.exists():
        data = cache.read_text(encoding='utf-8', errors='replace')
    else:
        url = f'https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (VoynichResearch)'})
        resp = urllib.request.urlopen(req, timeout=30)
        data = resp.read().decode('utf-8', errors='replace')
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(data, encoding='utf-8')
    start = data.find('*** START OF')
    end = data.find('*** END OF')
    if start > 0 and end > 0:
        return data[data.index('\n', start)+1:end]
    return data

def folio_section(fname):
    m = re.match(r'f(\d+)', fname)
    if not m:
        return 'unknown'
    n = int(m.group(1))
    if 103 <= n <= 116: return 'recipe'
    elif 75 <= n <= 84: return 'balneo'
    elif 67 <= n <= 73: return 'astro'
    elif 85 <= n <= 86: return 'cosmo'
    else: return 'herbal'

def folio_section_v2(fnum):
    """Assign a section label to a folio number."""
    if 103 <= fnum <= 116:
        return 'recipe'
    elif 75 <= fnum <= 84:
        return 'balneo'
    elif 67 <= fnum <= 73:
        return 'astro'
    elif 85 <= fnum <= 86:
        return 'cosmo'
    else:
        return 'herbal'

def full_decompose(word):
    stripped, gals = strip_gallows(word)
    collapsed = collapse_echains(stripped)
    pfx, root, sfx = parse_morphology(collapsed)
    bases = [gallows_base(g) for g in gals]
    return dict(original=word, stripped=stripped, collapsed=collapsed,
                prefix=pfx or "", root=root, suffix=sfx or "",
                gallows=bases, determinative=bases[0] if bases else "")

def gallows_base(g):
    for b in 'tkfp':
        if b in g: return b
    return g

def gallows_base_v2(g):
    for base in ['t', 'k', 'f', 'p']:
        if base in g:
            return base
    return g

def get_currier_language(folio_num):
    lang_b = set()
    for f in [26,27,28,29,31,34,35,38,39,42,43,46,47,49,50,53,54]:
        lang_b.add(f)
    for f in range(75, 85):
        lang_b.add(f)
    for f in range(87, 103):
        lang_b.add(f)
    return 'B' if folio_num in lang_b else 'A'

def get_gram_prefix(w):
    for gp in GRAM_PREFIXES:
        if w.startswith(gp) and len(w) > len(gp):
            return gp
    return 'X'

def get_prefix(w):
    for p in ['qo','lch','lsh','sh','ch','so','do','q','o','d','y','l']:
        if w.startswith(p): return p
    return 'X'

def get_root(onset, body):
    """Combine root onset + body into a single root string."""
    return onset + body

def get_suffix(w):
    for sf in SUFFIXES:
        if w.endswith(sf) and len(w) > len(sf): return sf
    return 'X'

def hapax_ratio_at_midpoint(words):
    """Fraction of vocabulary that are hapax legomena at corpus midpoint."""
    mid = len(words) // 2
    freq = Counter(words[:mid])
    hapax = sum(1 for c in freq.values() if c == 1)
    return hapax / max(len(freq), 1)

def index_of_coincidence(char_list):
    """Friedman's IC: probability two random chars are the same."""
    freq = Counter(char_list)
    n = sum(freq.values())
    if n < 2:
        return 0.0
    return sum(c * (c-1) for c in freq.values()) / (n * (n-1))

def load_all_tokens():
    """Load all tokens with section tags."""
    tokens = []
    section_map = {
        'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
        'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
    }
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        section = 'unknown'
        folio_id = ''
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'):
                ll = line.lower()
                for key, val in section_map.items():
                    if key in ll:
                        section = val
                        if val == 'herbal' and '-b' in ll: section = 'herbal-B'
                        elif val == 'herbal': section = 'herbal-A'
                continue
            m = re.match(r'<([^>]+)>', line)
            if m:
                folio_id = m.group(1).split(',')[0]
                rest = line[m.end():].strip()
            else:
                rest = line
            if not rest: continue
            for word in re.split(r'[.\s,;]+', rest):
                word = re.sub(r'[^a-z]', '', word.lower().strip())
                if len(word) >= 2:
                    tokens.append((word, section, folio_id))
    return tokens

def load_bvgs(filepath):
    """Load Buch von guter Speise with aggressive OCR cleaning.

    The text is a Google Books OCR of an 1844 scholarly edition.
    CRITICAL: The first occurrence of the incipit is in the modern German
    foreword (line ~108), quoting the title. The ACTUAL recipe text starts
    at line ~242 with the standalone line "Dis buch sagt von guter spise".
    We must find the SECOND occurrence, or better, the standalone line.

    We need to:
    - Skip the entire modern German foreword (Vorwort, lines 1-241)
    - Start at the actual recipe poem/text
    - Remove "Digitized by Google" lines
    - Remove footnote markers (superscript numbers, asterisks)
    - Remove modern German footnotes by the 1844 editor
    - Remove page numbers
    - Remove scholarly apparatus (Vgl., vergl., Anm., bibliographic refs)
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    # Find the STANDALONE incipit line (not the foreword's quotation).
    # The foreword quotes it inline: 'cipit: „dis buch sagt...'
    # The actual recipe text has it as a standalone line.
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        # Match standalone line (not embedded in a longer sentence)
        if stripped.startswith('dis buch sagt von guter spise'):
            start_idx = i
            # Don't break — take the LAST match if there are multiple,
            # but actually in this text the standalone one comes second
            break
    # If first match was in the foreword (has surrounding scholarly text),
    # search for the next one
    if start_idx < 200:  # foreword is in first ~240 lines
        for i, line in enumerate(lines[start_idx + 1:], start=start_idx + 1):
            stripped = line.strip().lower()
            if stripped.startswith('dis buch sagt von guter spise'):
                start_idx = i
                break

    # Collect recipe text, filtering out noise aggressively
    recipe_lines = []
    for line in lines[start_idx:]:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip "Digitized by Google" and similar
        if 'digitized by' in line.lower():
            continue

        # Skip page numbers (standalone digits)
        if re.match(r'^\d+\s*$', line):
            continue

        # Skip footnote lines (start with special characters or *)
        if re.match(r'^[\*\)°]', line):
            continue
        if re.match(r'^[¹²³⁴⁵⁶⁷⁸⁹⁰]', line):
            continue

        # Skip scholarly apparatus lines
        # - Lines with = sign (glosses like "Pflanze = plant")
        if '=' in line and len(line) < 150:
            continue

        # - Lines starting with Vgl./vergl./vgl (cross-references)
        if re.match(r'^[Vv]gl\.?\s|^[Vv]ergl\.?\s', line):
            continue

        # - Lines with (Fol. references to manuscript folios
        if re.search(r'\(Fol\.\s*\d+', line):
            continue

        # - Lines that are mostly Latin/bibliographic (contain multiple
        #   capitalized Latin words like "Sed nostra omnis")
        latin_caps = len(re.findall(r'\b[A-Z][a-z]{3,}\b', line))
        if latin_caps >= 3 and len(line) < 120:
            continue

        # - Lines referencing other works/scholars
        if re.search(r'Boner|Schindler|Schmeller|Lexer|Grimm|Weinhold', line):
            continue

        # Remove inline footnote markers like ') or 1) or *)
        line = re.sub(r'\s*[\*¹²³⁴⁵⁶⁷⁸⁹⁰]*\)', '', line)
        # Remove superscript-style markers
        line = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]', '', line)

        recipe_lines.append(line)

    text = ' '.join(recipe_lines).lower()
    # Keep only German letters (including umlauts and ß) and spaces
    text = re.sub(r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþßœ\s]+', ' ', text)
    words = [w for w in text.split() if len(w) >= 1]
    return words

def load_folio_lines():
    """Return list of (line_id, section, [raw_words]) preserving line structure."""
    lines = []
    section_map = {
        'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
        'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
    }
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        section = 'unknown'
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'):
                ll = line.lower()
                for key, val in section_map.items():
                    if key in ll:
                        section = val
                        if val == 'herbal' and '-b' in ll: section = 'herbal-B'
                        elif val == 'herbal': section = 'herbal-A'
                continue
            m = re.match(r'<([^>]+)>', line)
            if m:
                lid = m.group(1)
                rest = line[m.end():].strip()
            else:
                continue
            if not rest: continue
            words = []
            for w in re.split(r'[.\s,;]+', rest):
                w = re.sub(r'[^a-z]', '', w.lower().strip())
                if len(w) >= 2: words.append(w)
            if words:
                lines.append((lid, section, words))
    return lines

def ivtff_locus_type(lid):
    """IVTFF locus type letter from a locus id like 'f75r.1,@P0' ->
    'P' (paragraph), 'L' (label), 'C' (circle), 'R' (radial), ... or
    None when the tag carries no type code."""
    m = re.search(r',[@+*=]?([A-Za-z])', lid)
    return m.group(1).upper() if m else None


def load_folio_lines_ivtff(comma_break=True, min_word_len=1,
                           locus_types=None):
    """IVTFF-aware replacement for load_folio_lines. Same return shape:
    list of (line_id, section, [words]).

    Fixes three defects of the naive loaders (documented in RESEARCH.md,
    finding T1): (1) inline <!...> metadata/comments leaked phantom tokens
    such as 'la' from '$L=A'; (2) alternate readings [r:n] were fused into
    nonexistent words ('chofarny'); (3) words containing illegible glyphs
    (%, *, ?) were silently truncated into phantom forms instead of being
    excluded.

    Policy (each a declared choice, not an accident):
    - <!...> comments and all other inline <...> tags removed; tags become
      word breaks (never fuse text across a gap marker).
    - [x:y:...] alternate readings -> first alternative (transcriber's
      preferred reading per IVTFF convention).
    - '!' is alignment padding -> removed, no break ('ch!ol' == 'chol').
    - Words containing illegible marks (%, *, ?) or residual non-EVA
      characters are dropped whole (a token with an unreadable glyph is
      not a countable word; truncating it fabricates one).
    - comma_break: IVTFF ',' is an UNCERTAIN space. True (default) treats
      it as a break like '.'; False joins across it. Sensitivity to this
      knob is part of the assumption audit.
    - min_word_len: default 1 keeps genuine single-glyph words (the legacy
      loaders' len>=2 filter dropped ~5.6% of real tokens).
    - locus_types: None (default) keeps every locus (legacy behavior).
      A collection like {'P'} restricts to those IVTFF locus types
      (P paragraph, L label, C circle, R radial, ...) — added 2026-07-19
      after the Part-D hapax audit showed label/ring loci are hapax-
      enriched and layout-clustered (see hapax_locus_readjudication).
    """
    lines = []
    section_map = {
        'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
        'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
    }
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        section = 'unknown'
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'):
                ll = line.lower()
                for key, val in section_map.items():
                    if key in ll:
                        section = val
                        if val == 'herbal' and '-b' in ll: section = 'herbal-B'
                        elif val == 'herbal': section = 'herbal-A'
                continue
            m = re.match(r'<([^>]+)>', line)
            if not m:
                continue
            lid = m.group(1)
            if locus_types is not None and \
                    ivtff_locus_type(lid) not in locus_types:
                continue
            rest = line[m.end():].strip()
            if not rest:
                continue
            words = ivtff_clean_words(rest, comma_break=comma_break,
                                      min_word_len=min_word_len)
            if words:
                lines.append((lid, section, words))
    return lines

def ivtff_clean_words(rest, comma_break=True, min_word_len=1):
    """Pure IVTFF text-line cleaner (policy documented on
    load_folio_lines_ivtff). Returns the list of clean words."""
    rest = re.sub(r'<![^>]*>', '.', rest)
    rest = re.sub(r'<[^>]*>', '.', rest)
    rest = re.sub(r'\[([^:\[\]]*)(?::[^\[\]]*)+\]', r'\1', rest)
    rest = rest.replace('!', '')
    sep = r'[.\s,;]+' if comma_break else r'[.\s;]+'
    if not comma_break:
        rest = rest.replace(',', '')
    words = []
    for w in re.split(sep, rest):
        w = w.lower().strip()
        if not w:
            continue
        if not re.fullmatch(r'[a-z]+', w):
            continue  # illegible/rare-glyph word: drop whole, never truncate
        if len(w) >= min_word_len:
            words.append(w)
    return words

def load_lines():
    """Load all lines as lists of words, with section metadata."""
    lines = []
    section_map = {
        'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
        'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
    }
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        section = 'unknown'
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'):
                ll = line.lower()
                for key, val in section_map.items():
                    if key in ll:
                        section = val
                        if val == 'herbal' and '-b' in ll:
                            section = 'herbal-B'
                        elif val == 'herbal':
                            section = 'herbal-A'
                continue
            m = re.match(r'<([^>]+)>', line)
            rest = line[m.end():].strip() if m else line
            if not rest:
                continue
            words = [w.strip() for w in re.split(r'[.\s,;]+', rest)
                     if w.strip() and re.match(r'^[a-z]+$', w.strip())]
            if len(words) >= 2:
                lines.append({'section': section, 'words': words})
    return lines

def load_lines_v2():
    lines = []
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'): continue
            m = re.match(r'<([^>]+)>', line)
            rest = line[m.end():].strip() if m else line
            if not rest: continue
            words = [w.strip() for w in re.split(r'[.\s,;]+', rest)
                     if w.strip() and re.match(r'^[a-z]+$', w.strip())]
            if len(words) >= 2:
                lines.append(words)
    return lines

def load_chunk_equivalence_clusters():
    json_path = RESULTS_DIR / 'chunk_equivalence_classes.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    chunk_to_class = {}
    for class_id, info in data['cluster_composition'].items():
        for member in info['members']:
            chunk_to_class[member] = class_id
    return chunk_to_class

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

def load_reference_text_v2(filepath):
    """Load a reference text file, return lowercase words (alpha only)."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()

    # Strip Gutenberg headers/footers if present
    start_marker = '*** START OF'
    end_marker = '*** END OF'
    start_idx = raw.find(start_marker)
    end_idx = raw.find(end_marker)
    if start_idx >= 0:
        raw = raw[raw.index('\n', start_idx) + 1:]
    if end_idx >= 0:
        raw = raw[:end_idx]

    text = raw.lower()
    text = re.sub(r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþßœ\s]+', ' ', text)
    words = [w for w in text.split() if len(w) >= 1]
    return words

def load_vms_words():
    words = []
    for fp in sorted(FOLIO_DIR.glob('*.txt')):
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                m = re.match(r'<([^>]+)>', line)
                rest = line[m.end():].strip() if m else line
                if not rest: continue
                for tok in re.split(r'[.\s,;]+', rest):
                    tok = tok.strip()
                    if tok and re.match(r'^[a-z]+$', tok):
                        words.append(tok)
    return words

def mean_word_length(words):
    return float(np.mean([len(w) for w in words]))

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

def strip_gallows(word):
    found = []
    temp = word
    for g in ALL_GALLOWS:
        while g in temp:
            found.append(g)
            temp = temp.replace(g, "", 1)
    return temp, found

def strip_gallows_v2(w):
    temp = w
    for g in ALL_GALLOWS:
        while g in temp:
            temp = temp.replace(g, '', 1)
    return temp

def ttr_at_n(words, n=5000):
    """Type-token ratio at first n tokens."""
    subset = words[:min(n, len(words))]
    return len(set(subset)) / len(subset) if subset else 0

def zipf_alpha(words):
    """Zipf exponent: slope of log(rank) vs log(freq)."""
    freq = Counter(words)
    ranked = sorted(freq.values(), reverse=True)
    n = min(len(ranked), 500)  # Top 500 words
    if n < 10:
        return 0.0
    log_rank = np.log(np.arange(1, n+1))
    log_freq = np.log(np.array(ranked[:n], dtype=float))
    A = np.vstack([log_rank, np.ones(n)]).T
    result = np.linalg.lstsq(A, log_freq, rcond=None)
    return float(-result[0][0])


# Descriptive aliases for the taxonomy families (see block above).
classify_folio_by_number = classify_folio
classify_folio_by_number_v2 = classify_folio_v2
classify_folio_by_header = classify_folio_v3  # returns (section, currier_lang)
