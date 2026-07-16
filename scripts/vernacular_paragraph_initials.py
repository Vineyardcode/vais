#!/usr/bin/env python3
"""
Vernacular Paragraph-Initial Mapping:
         Can ANY Medieval Vernacular Language Produce 81-87% Concentration?

═══════════════════════════════════════════════════════════════════════

BACKGROUND: latin_paragraph_initials showed that NO Latin text concentrates >64% of
paragraph starts in 4 letters. VMS gallows account for 81.4% overall,
87.4% in the recipe section. But could a VERNACULAR language (Italian,
French, Middle English) — especially recipe/herbal texts from the 1430s
era — naturally produce such concentration?

KEY INSIGHT: Recipe texts in all languages heavily use imperative verbs:
  Italian: "Togli" (Take), "Prendi" (Take), "Poni" (Put), "Metti" (Put)
  French: "Prenez" (Take), "Mettez" (Put), "Faictes" (Make)
  Middle English: "Take" (Take), "Make" (Make), "Do" (Do)
This COULD create very high concentration in some letter(s).

TEXTS:
  1. Il libro della cucina del sec. XIV (Italian, 14th c.)     #33954
  2. Le viandier de Taillevent (French, c. 1380-1420)          #26567
  3. The Forme of Cury (Middle English, c. 1390)               #8102

TARGET VMS distributions:
  Overall:  p=44.9%, t=22.2%, k=10.3%, f=4.0% → 81.4% gallows
  Recipe:   p=54.4%, t=21.1%, k=7.0%,  f=4.9% → 87.4% gallows
  Herbal:   p=34.5%, t=28.0%, k=16.8%, f=5.3% → 84.5% gallows

SKEPTICAL CHECKS:
  - Are paragraph breaks in Gutenberg editions REAL or editorial?
  - Does stripping editorial apparatus (Roman numerals, page numbers)
    change the distributions?
  - Are repeated "Togli" starts a genuine recipe convention or modern
    editorial formatting of originally continuous text?
  - NULL: Would ANY random text with many short paragraphs show high
    concentration simply due to formulaic genre conventions?
"""

import re, sys, io, math, json, os, urllib.request, time
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations, permutations
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)
DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'vernacular_texts'
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

SEED = 42
np.random.seed(SEED)

# ═══════════════════════════════════════════════════════════════════════
# VMS DATA (from paragraph_framing/75)
# ═══════════════════════════════════════════════════════════════════════

VMS_GALLOWS_RAW = {'p': 352, 't': 174, 'k': 81, 'f': 31}
VMS_TOTAL_PARAS = 784
VMS_GALLOWS_TOTAL = sum(VMS_GALLOWS_RAW.values())  # 638
VMS_GALLOWS_COVERAGE = VMS_GALLOWS_TOTAL / VMS_TOTAL_PARAS  # ~81.4%
VMS_GALLOWS_PROPS = {g: c/VMS_TOTAL_PARAS for g, c in VMS_GALLOWS_RAW.items()}
VMS_GALLOWS_REL = {g: c/VMS_GALLOWS_TOTAL for g, c in VMS_GALLOWS_RAW.items()}

VMS_SECTION = {
    'overall': {
        'dist': {'p': 352, 't': 174, 'k': 81, 'f': 31},
        'total': 784,
        'gallows_coverage': 0.814,
    },
    'recipe': {
        'dist': {'p': 155, 't': 60, 'k': 20, 'f': 14},
        'total': 285,
        'gallows_coverage': 0.874,
    },
    'herbal': {
        'dist': {'p': 111, 't': 90, 'k': 54, 'f': 17},
        'total': 322,
        'gallows_coverage': 0.845,
    },
}

# ═══════════════════════════════════════════════════════════════════════
# TEXT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

VERNACULAR_TEXTS = {
    'italian_cucina': {
        'id': 33954,
        'title': 'Il libro della cucina del sec. XIV',
        'language': 'Italian (Tuscan)',
        'genre': 'cookbook / recipe collection',
        'era': '14th century (trecento)',
        'url': 'https://www.gutenberg.org/cache/epub/33954/pg33954.txt',
    },
    'french_viandier': {
        'id': 26567,
        'title': 'Le viandier de Taillevent',
        'language': 'French',
        'genre': 'cookbook / recipe collection',
        'era': 'c. 1380-1420 (Charles VI)',
        'url': 'https://www.gutenberg.org/cache/epub/26567/pg26567.txt',
    },
    'english_cury': {
        'id': 8102,
        'title': 'The Forme of Cury',
        'language': 'Middle English',
        'genre': 'cookbook / recipe collection',
        'era': 'c. 1390 (Richard II)',
        'url': 'https://www.gutenberg.org/cache/epub/8102/pg8102.txt',
    },
}

# ═══════════════════════════════════════════════════════════════════════
# DOWNLOAD & PARSE
# ═══════════════════════════════════════════════════════════════════════

def download_text(key, info):
    filepath = DATA_DIR / f"{key}.txt"
    if filepath.exists():
        pr(f"  [cached] {key}: {filepath.name}")
        return filepath.read_text(encoding='utf-8', errors='replace')
    pr(f"  [downloading] {key} from {info['url']}...")
    try:
        req = urllib.request.Request(info['url'],
            headers={'User-Agent': 'VoynichResearch/1.0 (academic)'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        filepath.write_text(text, encoding='utf-8')
        pr(f"    → {len(text)} chars saved")
        time.sleep(2)
        return text
    except Exception as e:
        pr(f"    → FAILED: {e}")
        return None


def strip_gutenberg_boilerplate(text):
    """Remove Project Gutenberg header/footer."""
    start_markers = [
        '*** START OF THE PROJECT GUTENBERG',
        '*** START OF THIS PROJECT GUTENBERG',
    ]
    end_markers = [
        '*** END OF THE PROJECT GUTENBERG',
        '*** END OF THIS PROJECT GUTENBERG',
        'End of the Project Gutenberg',
        'End of Project Gutenberg',
    ]
    start_idx = 0
    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            nl = text.find('\n', idx)
            start_idx = nl + 1 if nl != -1 else idx + len(marker)
            break
    end_idx = len(text)
    for marker in end_markers:
        idx = text.find(marker)
        if idx != -1 and idx > start_idx:
            end_idx = idx
            break
    return text[start_idx:end_idx].strip()


def extract_recipe_body_italian(text):
    """Extract the actual recipe section from the Italian cookbook.
    The real recipes start after 'INCOMINCIASI IL LIBRO DE LA COCINA.'
    and end before 'ANNOTAZIONI'.
    """
    # Find start of recipes
    start_markers = [
        'INCOMINCIASI IL LIBRO DE LA COCINA',
        'IL LIBRO DELLA COCINA',
        'Dei Cauli',
    ]
    start_idx = 0
    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            start_idx = idx
            break

    # Find end of recipes (before annotations/notes)
    end_markers = ['ANNOTAZIONI', 'CORREGGI', 'INDICE\n  DEI\n  CAPITOLI']
    end_idx = len(text)
    for marker in end_markers:
        idx = text.find(marker)
        if idx != -1 and idx > start_idx:
            end_idx = idx
            break

    return text[start_idx:end_idx].strip()


def extract_recipe_body_french(text):
    """Extract the recipe body from Viandier de Taillevent.
    Skip table of contents at start and notes at end.
    """
    # Find start of actual recipes (after table of contents)
    # The recipes start with "Potaiges lyans" or similar
    start_markers = [
        'Potaiges lyans',
        'Chaudun de porc',
        'Pour faire chaudun',
    ]
    start_idx = 0
    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            start_idx = idx
            break

    # Find end
    end_markers = [
        'NOTES SUR LA VERSION',
        'Espices appartenantes',
        'Du chapellet fait',
    ]
    end_idx = len(text)
    for marker in end_markers:
        idx = text.find(marker)
        if idx != -1 and idx > start_idx:
            end_idx = idx
            break

    return text[start_idx:end_idx].strip()


def extract_recipe_body_english(text):
    """Extract recipe body from Forme of Cury.
    The actual recipes are numbered (I, II, etc.) and start with
    recipe titles in caps.

    Structure: Recipes from 'FOR TO MAKE GRONDEN BENES' through
    'EXPLICIT DE COQUINA QUE EST OPTIMA MEDICINA', with meat
    recipes ending at 'EXPLICIT SERVICIUM DE CARNIBUS' and fish
    recipes following after 'Hic incipit Servicium de Pissibus'.
    """
    # Find start of recipes
    start_markers = [
        'FOR TO MAKE GRONDEN BENES',
        'CABOCHES IN POTAGE',
    ]
    start_idx = 0
    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            start_idx = idx
            break

    # End at the last EXPLICIT (before INDEX AND GLOSSARY)
    end_markers = [
        'EXPLICIT DE COQUINA',
        'INDEX AND GLOSSARY',
    ]
    end_idx = len(text)
    for marker in end_markers:
        idx = text.find(marker, start_idx)
        if idx != -1 and idx < end_idx:
            end_idx = idx
            break

    return text[start_idx:end_idx].strip()


def normalize_gutenberg_doublespace(text):
    """Gutenberg texts are often double-spaced: every line followed by
    a blank line. Real paragraph breaks are 4+ newlines (two blank lines).

    Normalize: join double-spaced lines within paragraphs, keep real
    paragraph breaks as double newlines.
    """
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Replace real paragraph breaks (4+ newlines) with a marker
    marker = '\n<<<PARA>>>\n'
    text = re.sub(r'\n{4,}', marker, text)
    # Now remaining \n\n are just double-spacing within paragraphs
    # Join them: replace \n\n with single space (joining line-wrapped text)
    text = re.sub(r'\n\n', ' ', text)
    # Replace single \n with space too (standard line wrapping)
    text = re.sub(r'\n', ' ', text)
    # Restore paragraph breaks as double newlines
    text = text.replace('<<<PARA>>>', '\n\n')
    # Clean up extra spaces
    text = re.sub(r'  +', ' ', text)
    return text


def extract_paragraphs_generic(text, min_len=10):
    """Split text into paragraphs by double newlines.
    Returns list of paragraph texts."""
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Split on blank lines
    raw_paras = re.split(r'\n\s*\n', text)
    paras = []
    for p in raw_paras:
        p = p.strip()
        if len(p) >= min_len:
            paras.append(p)
    return paras


def get_first_word(para):
    """Get the first word of a paragraph, stripping leading markers."""
    # Strip leading whitespace, bullet markers, numbering
    text = para.strip()
    # Remove leading paragraph markers: =, _, *, #, etc.
    text = re.sub(r'^[=_*#¶§†‡•→]+\s*', '', text)
    # Remove leading Roman numeral numbering like "I.", "II.", "XLIII.", "XX.II."
    text = re.sub(r'^[IVXLCDM]+[\.\s]+(?:[IVXLCDM]+[\.\s]+)*', '', text)
    # Remove regular numbering like "1.", "23.", etc.
    text = re.sub(r'^\d+[\.\)]\s*', '', text)
    # Remove leading brackets like "[1]", "(Page 5)", etc.
    text = re.sub(r'^\[[\d\w]+\]\s*', '', text)
    text = re.sub(r'^\(Page\s+\d+\)\s*', '', text, flags=re.IGNORECASE)
    # Strip wrapper formatting
    text = re.sub(r'^[=_]+', '', text).strip()

    # Get first word
    m = re.match(r'[A-Za-zÀ-ÿ]+', text)
    if m:
        return m.group(0)
    return None


def get_initial_letter(para):
    """Get the paragraph-initial letter, with careful cleaning."""
    word = get_first_word(para)
    if word:
        return word[0].upper()
    return None


def compute_distribution(letters):
    """Compute frequency distribution from list of letters."""
    counter = Counter(letters)
    total = sum(counter.values())
    if total == 0:
        return {}, 0
    dist = {}
    for letter, count in counter.most_common():
        dist[letter] = count / total
    return dist, total


def test_all_mappings(dist, n_letters, total_items):
    """Test all possible 4-letter mappings from the given distribution.

    Returns sorted list of (score, mapping_dict, coverage, l2) tuples.
    """
    available = [letter for letter in dist.keys() if letter.isalpha()]
    if len(available) < 4:
        return []

    vms_ordered = ['p', 't', 'k', 'f']
    vms_props = [VMS_GALLOWS_PROPS[g] for g in vms_ordered]
    vms_coverage = VMS_GALLOWS_COVERAGE

    results = []
    tested = 0
    for combo in combinations(available, 4):
        for perm in permutations(combo):
            tested += 1
            # Map: VMS gallows → Latin letters
            mapping = dict(zip(vms_ordered, perm))
            # Get proportions for these 4 letters
            latin_props = [dist.get(l, 0) for l in perm]
            coverage = sum(latin_props)

            # L2 distance between VMS and Latin proportion vectors
            l2 = sum((v - l) ** 2 for v, l in zip(vms_props, latin_props))

            # Coverage delta penalty
            cov_delta = abs(vms_coverage - coverage)

            # Combined score (lower = better)
            score = l2 + cov_delta

            results.append((score, mapping, coverage, l2))

    results.sort(key=lambda x: x[0])
    return results


def find_best_coverage_match(dist, available_letters, target_coverage):
    """Find which 4 letters give the closest coverage to target."""
    if len(available_letters) < 4:
        return None, 0

    best_combo = None
    best_gap = float('inf')
    for combo in combinations(available_letters, 4):
        cov = sum(dist.get(l, 0) for l in combo)
        gap = abs(target_coverage - cov)
        if gap < best_gap:
            best_gap = gap
            best_combo = combo
    return best_combo, best_gap


# ═══════════════════════════════════════════════════════════════════════
# ITALIAN-SPECIFIC PARSING
# ═══════════════════════════════════════════════════════════════════════

def parse_italian_recipes(text):
    """Parse Italian cookbook into recipe paragraphs.

    The Italian cookbook uses these conventions:
    - Section headers in = signs: =Dei Cauli.=
    - Sub-recipes marked by _italic_ markers: _A fare i Cauli bianchi_
    - Recipe text paragraphs starting with "Togli", "Metti", "Poni", etc.

    CRITICAL: Gutenberg text is double-spaced (each line separated by
    blank line). Real paragraph breaks are 4+ newlines. Must normalize.
    """
    body = extract_recipe_body_italian(text)
    body = normalize_gutenberg_doublespace(body)

    # Now split on double-newline (which marks real paragraph/recipe boundaries)
    paras = extract_paragraphs_generic(body, min_len=10)
    return paras


def parse_french_recipes(text):
    """Parse French cookbook into recipe paragraphs.

    Viandier uses ¶ markers for new recipes and section headers.
    Also double-spaced Gutenberg formatting.
    """
    body = extract_recipe_body_french(text)
    body = normalize_gutenberg_doublespace(body)

    # Split by ¶ markers (pilcrow = recipe/paragraph markers)
    parts = re.split(r'¶', body)
    paras = []
    for part in parts:
        text_clean = part.strip()
        if len(text_clean) >= 10:
            paras.append(text_clean)

    # If we didn't get many ¶-delimited paras, fall back to double-newline
    if len(paras) < 20:
        paras = extract_paragraphs_generic(body)

    return paras


def parse_english_recipes(text):
    """Parse Middle English cookbook into recipe paragraphs.

    Forme of Cury uses recipe titles in ALL CAPS followed by Roman numeral.
    Each recipe starts with its title and then "Take..." or "Make..."

    CRITICAL: The text has extensive inline footnotes like:
      [1] Funges. Mushrooms.
      [2] dyce hem. Dice them.
    These must be STRIPPED — they are editor's notes, not recipe text.
    Also double-spaced Gutenberg formatting.
    """
    body = extract_recipe_body_english(text)
    body = normalize_gutenberg_doublespace(body)

    # Now strip footnote paragraphs (paragraphs starting with [number])
    paras_raw = extract_paragraphs_generic(body, min_len=10)
    paras = []
    for p in paras_raw:
        stripped = p.strip()
        # Skip footnote paragraphs
        if re.match(r'^\[\d+\]', stripped):
            continue
        # Skip "See p." references
        if re.match(r'^See p\.', stripped, re.IGNORECASE):
            continue
        # Skip pure editorial markers
        if re.match(r'^Vide\b', stripped):
            continue
        paras.append(p)

    return paras


# ═══════════════════════════════════════════════════════════════════════
# ANALYSIS FOR FIRST WORDS (not just first letters)
# ═══════════════════════════════════════════════════════════════════════

def analyze_first_words(paras, top_n=20):
    """Analyze which words start paragraphs, not just letters."""
    words = []
    for para in paras:
        w = get_first_word(para)
        if w:
            words.append(w.lower())
    return Counter(words).most_common(top_n)


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def analyze_text(key, info, text):
    """Full analysis of one vernacular text."""
    pr(f"\n{'─'*70}")
    pr(f"TEXT: {info['title']}")
    pr(f"Language: {info['language']} | Genre: {info['genre']} | Era: {info['era']}")
    pr(f"{'─'*70}")

    # Strip Gutenberg boilerplate
    clean = strip_gutenberg_boilerplate(text)
    pr(f"Text length: {len(clean):,} chars after boilerplate removal")

    # Parse into paragraphs using language-specific parser
    if 'italian' in key:
        paras = parse_italian_recipes(clean)
    elif 'french' in key:
        paras = parse_french_recipes(clean)
    elif 'english' in key:
        paras = parse_english_recipes(clean)
    else:
        paras = extract_paragraphs_generic(clean)

    pr(f"Recipe paragraphs extracted: {len(paras)}")

    if len(paras) < 10:
        pr("  WARNING: Too few paragraphs extracted, trying generic parser...")
        paras = extract_paragraphs_generic(clean)
        pr(f"  Generic parser: {len(paras)} paragraphs")

    # Show a few example paragraph starts for verification
    pr(f"\n  SAMPLE PARAGRAPH STARTS (first 10):")
    for i, para in enumerate(paras[:10]):
        preview = para[:80].replace('\n', ' ')
        pr(f"    {i+1:3d}. {preview}...")

    # ─── FIRST-WORD Analysis ───
    pr(f"\n  TOP PARAGRAPH-INITIAL WORDS:")
    first_words = analyze_first_words(paras)
    for word, count in first_words[:15]:
        pct = count / len(paras) * 100
        bar = '█' * int(pct / 2)
        pr(f"    {word:20s}: {count:4d} ({pct:5.1f}%) {bar}")

    # Group first words by initial letter
    word_by_letter = defaultdict(list)
    for word, count in first_words:
        letter = word[0].upper()
        word_by_letter[letter].append((word, count))

    # ─── LETTER Analysis ───
    letters = []
    for para in paras:
        l = get_initial_letter(para)
        if l:
            letters.append(l)

    if not letters:
        pr("  ERROR: No letters extracted!")
        return None

    dist, total = compute_distribution(letters)
    counter = Counter(letters)

    pr(f"\n  Paragraph-initial letter distribution (n={total}):")
    for letter, pct in sorted(dist.items(), key=lambda x: -x[1])[:20]:
        count = counter[letter]
        bar = '█' * int(pct * 50)
        pr(f"    {letter}:  {count:4d} ({pct*100:5.1f}%) {bar}")
        # Show which words contribute
        if letter in word_by_letter:
            words_str = ', '.join(f"{w}({c})" for w, c in word_by_letter[letter][:5])
            pr(f"         words: {words_str}")

    # Top-4 coverage
    top4 = sorted(dist.items(), key=lambda x: -x[1])[:4]
    top4_letters = [l for l, _ in top4]
    top4_coverage = sum(p for _, p in top4)
    pr(f"\n  Top-4 letters: {top4_letters} → coverage: {top4_coverage*100:.1f}%")
    pr(f"  VMS gallows coverage: {VMS_GALLOWS_COVERAGE*100:.1f}%")
    pr(f"  Gap: {(top4_coverage - VMS_GALLOWS_COVERAGE)*100:.1f}%")

    # ─── MAPPING Analysis ───
    pr(f"\n  Testing all 4-letter mappings against VMS gallows distribution...")
    results = test_all_mappings(dist, len(dist), total)
    pr(f"    Tested {len(results):,} mappings")

    if results:
        pr(f"\n  TOP 10 PARAGRAPH-INITIAL MAPPINGS:")
        pr(f"  {'Rank':>4s} {'Score':>8s} {'L2':>8s} {'Cov%':>6s}   {'p→':>4s} {'t→':>4s} {'k→':>4s} {'f→':>4s}")
        for i, (score, mapping, coverage, l2) in enumerate(results[:10]):
            pr(f"  {i+1:4d} {score:.4f} {l2:.4f} {coverage*100:5.1f}%"
               f"    {mapping['p']:>4s} {mapping['t']:>4s} {mapping['k']:>4s} {mapping['f']:>4s}")

        best_score, best_map, best_cov, best_l2 = results[0]
        pr(f"\n  BEST MAPPING: {best_map}")
        pr(f"  Score: {best_score:.4f} (L2={best_l2:.4f}, CovΔ={abs(VMS_GALLOWS_COVERAGE-best_cov):.4f})")
        pr(f"  Coverage: {best_cov*100:.1f}% (VMS: {VMS_GALLOWS_COVERAGE*100:.1f}%)")
        pr(f"  Proportions (within 4 letters):")
        vms_ordered = ['p', 't', 'k', 'f']
        for g in vms_ordered:
            l = best_map[g]
            vms_prop = VMS_GALLOWS_REL[g]
            if best_cov > 0:
                lat_prop = dist.get(l, 0) / best_cov
            else:
                lat_prop = 0
            pr(f"    VMS {g} → {info['language'][:3]} {l}: VMS={vms_prop:.3f}, Lang={lat_prop:.3f}, Δ={abs(vms_prop-lat_prop):.3f}")

    # ─── BEST COVERAGE MATCH ───
    available = [l for l in dist.keys() if l.isalpha()]
    best_combo, best_gap = find_best_coverage_match(dist, available, VMS_GALLOWS_COVERAGE)
    if best_combo:
        combo_cov = sum(dist.get(l, 0) for l in best_combo)
        pr(f"\n  CLOSEST COVERAGE MATCH to VMS 81.4%:")
        pr(f"    Letters: {best_combo} → {combo_cov*100:.1f}% (gap={best_gap*100:.1f}%)")

    # ─── COMPARE WITH VMS RECIPE SECTION specifically ───
    pr(f"\n  COMPARISON WITH VMS RECIPE SECTION (87.4% gallows, 285 paras):")
    vms_recipe = VMS_SECTION['recipe']
    vms_r_total = vms_recipe['total']
    vms_r_cov = vms_recipe['gallows_coverage']
    vms_r_props = {g: c/vms_r_total for g, c in vms_recipe['dist'].items()}

    # Find best combo for recipe-section coverage
    best_r_combo, best_r_gap = find_best_coverage_match(dist, available, vms_r_cov)
    if best_r_combo:
        r_cov = sum(dist.get(l, 0) for l in best_r_combo)
        pr(f"    Closest 4 letters to 87.4%: {best_r_combo} → {r_cov*100:.1f}% (gap={best_r_gap*100:.1f}%)")

    return {
        'key': key,
        'title': info['title'],
        'language': info['language'],
        'era': info['era'],
        'n_paragraphs': len(paras),
        'n_letters': total,
        'distribution': {l: round(p, 4) for l, p in dist.items()},
        'top4_letters': top4_letters,
        'top4_coverage': round(top4_coverage, 4),
        'coverage_gap': round(top4_coverage - VMS_GALLOWS_COVERAGE, 4),
        'best_mapping': results[0] if results else None,
        'first_words': first_words[:20],
    }


def analyze_without_headers(key, info, text):
    """Re-analyze Italian text, separating section headers from recipe body.

    Section headers (= ... = or _ ... _) are editorial chapter headings,
    not recipe paragraphs. Count them separately to see if D-inflation
    from 'Dei', 'Del', 'Delle' section headers is artificial.
    """
    if 'italian' not in key:
        return None

    pr(f"\n{'─'*70}")
    pr(f"ITALIAN TEXT: Recipe-Body-Only Analysis (Excluding Section Headers)")
    pr(f"{'─'*70}")

    clean = strip_gutenberg_boilerplate(text)
    paras = parse_italian_recipes(clean)

    # Classify paragraphs as headers vs body
    headers = []
    body_paras = []
    for para in paras:
        stripped = para.strip()
        # Section headers: start with = or _ markers
        if (stripped.startswith('=') or stripped.startswith('_')
            or stripped.startswith('INCOMINCIASI')
            or stripped.startswith('EXPLICIT')
            or re.match(r'^[A-Z\s]{10,}$', stripped)):
            headers.append(para)
        else:
            body_paras.append(para)

    pr(f"  Total paragraphs: {len(paras)}")
    pr(f"  Section headers:  {len(headers)}")
    pr(f"  Recipe body:      {len(body_paras)}")

    # Analyze headers separately
    header_letters = [get_initial_letter(h) for h in headers]
    header_letters = [l for l in header_letters if l]
    header_dist, header_total = compute_distribution(header_letters)
    pr(f"\n  HEADER initial letters (n={header_total}):")
    for l, p in sorted(header_dist.items(), key=lambda x: -x[1])[:10]:
        pr(f"    {l}: {Counter(header_letters)[l]:4d} ({p*100:5.1f}%)")

    # Analyze recipe body only
    body_letters = [get_initial_letter(p) for p in body_paras]
    body_letters = [l for l in body_letters if l]
    body_dist, body_total = compute_distribution(body_letters)
    body_counter = Counter(body_letters)

    pr(f"\n  RECIPE BODY initial letters (n={body_total}):")
    for l, p in sorted(body_dist.items(), key=lambda x: -x[1])[:15]:
        pr(f"    {l}: {body_counter[l]:4d} ({p*100:5.1f}%)")

    # Top-4 in body only
    top4_body = sorted(body_dist.items(), key=lambda x: -x[1])[:4]
    top4_cov = sum(p for _, p in top4_body)
    top4_letters = [l for l, _ in top4_body]
    pr(f"\n  Top-4 body-only letters: {top4_letters} → {top4_cov*100:.1f}%")
    pr(f"  VMS overall: 81.4%, VMS recipe: 87.4%")

    # First words in body
    pr(f"\n  TOP BODY-ONLY paragraph-initial words:")
    body_words = analyze_first_words(body_paras)
    for word, count in body_words[:10]:
        pct = count / len(body_paras) * 100
        pr(f"    {word:20s}: {count:4d} ({pct:5.1f}%)")

    return {
        'n_headers': len(headers),
        'n_body': len(body_paras),
        'body_top4_letters': top4_letters,
        'body_top4_coverage': round(top4_cov, 4),
        'body_distribution': {l: round(p, 4) for l, p in body_dist.items()},
    }


# ═══════════════════════════════════════════════════════════════════════
# CROSS-TEXT COMPARISON
# ═══════════════════════════════════════════════════════════════════════

def cross_compare(all_results):
    """Compare all texts against each other and against VMS."""
    pr(f"\n{'═'*70}")
    pr(f"CROSS-TEXT COMPARISON")
    pr(f"{'═'*70}")

    pr(f"\n  {'Text':<30s} {'Lang':<10s} {'Paras':>6s} {'Top4 Cov':>9s} {'Gap':>8s} {'Top-4 Letters':<20s}")
    pr(f"  {'─'*30} {'─'*10} {'─'*6} {'─'*9} {'─'*8} {'─'*20}")
    pr(f"  {'VMS (overall)':<30s} {'Voynich':<10s} {784:>6d} {'81.4%':>9s} {'—':>8s} {'p, t, k, f':<20s}")
    pr(f"  {'VMS (recipe only)':<30s} {'Voynich':<10s} {285:>6d} {'87.4%':>9s} {'—':>8s} {'p, t, k, f':<20s}")
    pr(f"  {'VMS (herbal only)':<30s} {'Voynich':<10s} {322:>6d} {'84.5%':>9s} {'—':>8s} {'p, t, k, f':<20s}")

    for r in all_results:
        if r is None:
            continue
        gap_str = f"{r['coverage_gap']*100:+.1f}%"
        letters_str = ', '.join(r['top4_letters'])
        pr(f"  {r['title'][:30]:<30s} {r['language'][:10]:<10s} {r['n_paragraphs']:>6d} "
           f"{r['top4_coverage']*100:>8.1f}% {gap_str:>8s} {letters_str:<20s}")

    # ─── First-word dominance comparison ───
    pr(f"\n  FIRST-WORD DOMINANCE (most common paragraph-opening word per text):")
    for r in all_results:
        if r is None or not r['first_words']:
            continue
        top_word, top_count = r['first_words'][0]
        pct = top_count / r['n_paragraphs'] * 100
        top3_str = ', '.join(f"{w}({c})" for w, c in r['first_words'][:3])
        pr(f"    {r['title'][:30]:<30s}: {top3_str}")
        pr(f"      Top word '{top_word}' = {pct:.1f}% of paragraphs")

    # ─── Can we explain VMS with any vernacular? ───
    pr(f"\n  KEY QUESTION: Does any vernacular text reach ≥80% in top-4 letters?")
    any_high = False
    for r in all_results:
        if r is None:
            continue
        if r['top4_coverage'] >= 0.75:
            pr(f"    ✓ {r['title'][:30]}: {r['top4_coverage']*100:.1f}% (CLOSE)")
            any_high = True
        elif r['top4_coverage'] >= 0.65:
            pr(f"    ~ {r['title'][:30]}: {r['top4_coverage']*100:.1f}% (moderate)")
        else:
            pr(f"    ✗ {r['title'][:30]}: {r['top4_coverage']*100:.1f}% (low)")

    if not any_high:
        pr(f"    → NO vernacular text reaches 75% in 4 letters")
    else:
        pr(f"    → Some texts approach VMS levels — investigate further!")


# ═══════════════════════════════════════════════════════════════════════
# SKEPTICAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def skeptical_analysis(all_results):
    pr(f"\n{'═'*70}")
    pr(f"SKEPTICAL ANALYSIS")
    pr(f"{'═'*70}")

    pr(f"""
1. PARAGRAPH BOUNDARY RELIABILITY
   Gutenberg texts use MODERN EDITORIAL paragraph breaks, not original
   manuscript formatting. The VMS paragraph breaks reflect ACTUAL
   manuscript layout. This is an imperfect comparison.

   However, for recipe texts specifically, paragraph breaks typically
   correspond to individual recipes — which IS how the VMS recipe
   section appears to be structured (one recipe per paragraph).

2. FORMULAIC GENRE CONVENTIONS
   Recipe texts ARE highly formulaic. Every recipe starts with an
   imperative verb ("Take X...", "Togli X...", "Prenez X...").
   This means recipe collections SHOULD show high first-letter
   concentration — possibly even approaching VMS levels.

   If they DON'T reach 81%, that's a strong signal that VMS gallows
   are not simple letter substitutions even in a recipe context.

   If they DO reach 81%, we need to check whether the PROPORTIONAL
   distribution also matches (not just total coverage).

3. EDITORIAL ARTIFACTS
   Some first "letters" may be:
   - Roman numeral section numbers (I, V, X, L, C, D, M)
   - Formatting markers (=, _, ¶)
   - Page numbers
   Our parser strips these, but imperfectly.

4. TEXT SIZE MISMATCH
   VMS recipe section: 285 paragraphs in ~14 folios
   Vernacular texts: varies widely
   We should note where paragraph counts are similar.""")

    # ─── Concentration entropy ───
    pr(f"\n5. ENTROPY COMPARISON")
    pr(f"   VMS gallows entropy: 1.575 bits (4 symbols)")

    for r in all_results:
        if r is None:
            continue
        dist = r['distribution']
        # Top-4 entropy
        top4 = sorted(dist.items(), key=lambda x: -x[1])[:4]
        top4_total = sum(p for _, p in top4)
        if top4_total > 0:
            top4_norm = [(l, p/top4_total) for l, p in top4]
            entropy = -sum(p * math.log2(p) for _, p in top4_norm if p > 0)
            pr(f"   {r['title'][:30]}: {entropy:.3f} bits (VMS: 1.575)")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("═" * 70)
    pr("vernacular_paragraph_initials: Vernacular Paragraph-Initial Mapping")
    pr("═" * 70)
    pr(f"\nTarget VMS distributions:")
    pr(f"  Overall: p=44.9%, t=22.2%, k=10.3%, f=4.0% → {VMS_GALLOWS_COVERAGE*100:.1f}% gallows")
    pr(f"  Recipe:  p=54.4%, t=21.1%, k=7.0%,  f=4.9% → 87.4% gallows")
    pr(f"  Herbal:  p=34.5%, t=28.0%, k=16.8%, f=5.3% → 84.5% gallows")

    pr(f"\nDownloading vernacular texts...")
    all_results = []

    for key, info in VERNACULAR_TEXTS.items():
        text = download_text(key, info)
        if text:
            result = analyze_text(key, info, text)
            all_results.append(result)

    # Italian-specific: separate headers vs recipe body
    italian_body_result = None
    key = 'italian_cucina'
    info = VERNACULAR_TEXTS[key]
    text = download_text(key, info)
    if text:
        italian_body_result = analyze_without_headers(key, info, text)

    # Cross-comparison
    cross_compare(all_results)

    # Skeptical analysis
    skeptical_analysis(all_results)

    # ─── FINAL SUMMARY ───
    pr(f"\n{'═'*70}")
    pr(f"vernacular_paragraph_initials SUMMARY")
    pr(f"{'═'*70}")

    coverages = [r['top4_coverage'] for r in all_results if r]
    if coverages:
        max_cov = max(coverages)
        max_text = [r for r in all_results if r and r['top4_coverage'] == max_cov][0]
        min_cov = min(coverages)
        avg_cov = sum(coverages) / len(coverages)

        pr(f"\n  Highest top-4 coverage: {max_cov*100:.1f}% ({max_text['title']})")
        pr(f"  Lowest top-4 coverage:  {min_cov*100:.1f}%")
        pr(f"  Average top-4 coverage: {avg_cov*100:.1f}%")
        pr(f"  VMS overall gallows:    {VMS_GALLOWS_COVERAGE*100:.1f}%")
        pr(f"  VMS recipe gallows:     87.4%")

        if max_cov >= 0.80:
            pr(f"\n  ★ AT LEAST ONE VERNACULAR TEXT REACHES VMS LEVELS")
            pr(f"    This means the VMS concentration is NOT necessarily")
            pr(f"    unusual for recipe collections in this era.")
        elif max_cov >= 0.70:
            pr(f"\n  ~ Vernacular texts get CLOSER than Latin (~{max_cov*100:.0f}% vs 64%)")
            pr(f"    but still fall short of VMS 81-87%.")
            pr(f"    The gap is smaller, suggesting recipe conventions")
            pr(f"    contribute but don't fully explain gallows concentration.")
        else:
            pr(f"\n  ✗ Even vernacular recipe texts don't reach VMS levels.")
            pr(f"    The gallows concentration remains anomalous.")

    pr(f"\n{'═'*70}")
    pr(f"KEY FINDINGS:")
    pr(f"{'═'*70}")
    pr(f"""
1. Recipe collections are MORE concentrated than general texts
   because of formulaic imperative verbs.

2. The critical question is whether this formula-driven concentration
   reaches the VMS level (81-87%) in ANY language.

3. If yes: gallows COULD be simple letter substitutions in a
   recipe-dominant text.
   If no: gallows are NOT simple letter substitutions, even in
   the most favorable genre context.

4. First-word analysis reveals whether concentration comes from
   one dominant word (like Italian 'Togli' = ~50% of starts)
   or from several words sharing an initial letter.
""")

    # Save results
    json_path = RESULTS_DIR / 'vernacular_paragraph_initials.json'
    serializable = []
    for r in all_results:
        if r is None:
            continue
        sr = dict(r)
        if sr.get('best_mapping'):
            score, mapping, cov, l2 = sr['best_mapping']
            sr['best_mapping'] = {
                'score': round(score, 4),
                'mapping': mapping,
                'coverage': round(cov, 4),
                'l2': round(l2, 4),
            }
        serializable.append(sr)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)

    txt_path = RESULTS_DIR / 'vernacular_paragraph_initials.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))

    pr(f"\nJSON results → {json_path}")
    pr(f"Full output → {txt_path}")


if __name__ == '__main__':
    main()
