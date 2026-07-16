#!/usr/bin/env python3
"""
Latin Paragraph-Initial Letter Mapping:
         Can VMS Gallows Be Mapped to Latin Letters?

═══════════════════════════════════════════════════════════════════════

BACKGROUND: paragraph_framing confirmed that ~81% of VMS paragraphs start with
one of 4 gallows characters (p=44.9%, t=22.2%, k=10.3%, f=4.0%).

CRITICAL INSIGHT (from user): The EVA transliteration labels (p, t, k, f)
are ARBITRARY. These glyphs could represent ANY four Latin letters. The
question is: do ANY 4 Latin letters, in a medical/herbal text context,
appear as paragraph-initial letters at similar frequencies?

APPROACH:
  1. Download several Latin texts from Project Gutenberg
  2. Also build a medieval Latin medical vocabulary reference
  3. Extract paragraph-initial letter distributions from each text
  4. Also extract sentence-initial and section-initial distributions
  5. Test ALL possible 4-letter mappings: C(26,4) × 4! = 358,800
  6. Score each mapping by distribution fit (L2, chi-squared, KL)
  7. Present best candidates per text/genre
  8. Compare with section-specific VMS distributions
  9. Cross-reference with medieval medical vocabulary knowledge

SKEPTICAL CHECKS:
  - Do the best-fit mappings reach ~81% coverage? (most Latin texts
    won't cluster 81% of starts in just 4 letters)
  - Are the best-fit letters linguistically plausible for a medical text?
  - Do herbal-section and recipe-section mappings converge or diverge?
  - NULL HYPOTHESIS: If random texts also give ~81% coverage in 4 letters,
    the finding is uninformative about content.
"""

import re, sys, io, math, json, os, urllib.request, time
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations, permutations
import numpy as np
from common import clean_word, folio_section_v2 as folio_section

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)
DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'latin_texts'
DATA_DIR.mkdir(parents=True, exist_ok=True)
FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

SEED = 42
np.random.seed(SEED)

# ═══════════════════════════════════════════════════════════════════════
# VMS PARAGRAPH-INITIAL DATA (from paragraph_framing)
# ═══════════════════════════════════════════════════════════════════════

# Gallows-only distribution (normalized within gallows)
VMS_GALLOWS_RAW = {'p': 352, 't': 174, 'k': 81, 'f': 31}
VMS_TOTAL_PARAS = 784
VMS_GALLOWS_TOTAL = sum(VMS_GALLOWS_RAW.values())  # 638
VMS_GALLOWS_COVERAGE = VMS_GALLOWS_TOTAL / VMS_TOTAL_PARAS  # ~81.4%

# Gallows proportions (relative to all paragraphs)
VMS_GALLOWS_PROPS = {g: c/VMS_TOTAL_PARAS for g, c in VMS_GALLOWS_RAW.items()}
# p=0.449, t=0.222, k=0.103, f=0.040

# Relative proportions (within gallows only, sums to 1.0)
VMS_GALLOWS_REL = {g: c/VMS_GALLOWS_TOTAL for g, c in VMS_GALLOWS_RAW.items()}
# p=0.552, t=0.273, k=0.127, f=0.049

# Section-specific distributions (from paragraph_framing)
VMS_SECTION_DIST = {
    'herbal': {'p': 0.34, 't': 0.28, 'k': 0.17, 'f': 0.05},   # 322 paras
    'recipe': {'p': 0.54, 't': 0.21, 'k': 0.07, 'f': 0.05},   # 285 paras
    'balneo': {'p': 0.54, 't': 0.15, 'k': 0.05, 'f': 0.02},   # 93 paras, q=0.11
}

# Full initial distribution (all chars)
VMS_ALL_INITIALS = {
    'p': 352, 't': 174, 'k': 81, 'o': 40, 'f': 31, 'q': 27,
    's': 20, 'd': 16, 'y': 14, 'c': 9, 'e': 6, 'n': 4,
    'w': 4, 'l': 2, 'h': 2, 'a': 1, 'r': 1
}


# ═══════════════════════════════════════════════════════════════════════
# LATIN TEXT DOWNLOAD & PARSING
# ═══════════════════════════════════════════════════════════════════════

GUTENBERG_TEXTS = {
    'apicius': {
        'id': 16439,
        'title': 'De Re Coquinaria (Apicius)',
        'genre': 'recipe/culinary',
        'era': 'c. 400 CE (compiled)',
        'url': 'https://www.gutenberg.org/cache/epub/16439/pg16439.txt',
    },
    'galen': {
        'id': 58978,
        'title': 'De Temperamentis (Galen/Linacre)',
        'genre': 'medical treatise',
        'era': 'c. 170 CE / 1521 translation',
        'url': 'https://www.gutenberg.org/cache/epub/58978/pg58978.txt',
    },
    'erasmus': {
        'id': 16561,
        'title': 'Encomium Artis Medicae (Erasmus)',
        'genre': 'medical oration',
        'era': '1518 CE',
        'url': 'https://www.gutenberg.org/cache/epub/16561/pg16561.txt',
    },
    'caesar': {
        'id': 10657,
        'title': 'De Bello Gallico (Caesar)',
        'genre': 'military history (control)',
        'era': '58-50 BCE',
        'url': 'https://www.gutenberg.org/cache/epub/10657/pg10657.txt',
    },
    'vulgate_genesis': {
        'id': 10005,
        'title': 'Vulgate Bible - Genesis',
        'genre': 'biblical (control)',
        'era': 'c. 400 CE',
        'url': 'https://www.gutenberg.org/cache/epub/10005/pg10005.txt',
    },
    'pliny': {
        'id': 60511,
        'title': 'Pliny Natural History (Books I-II)',
        'genre': 'natural history / encyclopedic',
        'era': '77 CE',
        'url': 'https://www.gutenberg.org/cache/epub/60511/pg60511.txt',
    },
}


def download_text(key, info):
    """Download a text from Gutenberg, cache locally."""
    filepath = DATA_DIR / f"{key}.txt"
    if filepath.exists():
        pr(f"  [cached] {key}: {filepath.name}")
        return filepath.read_text(encoding='utf-8', errors='replace')

    pr(f"  [downloading] {key} from {info['url']}...")
    try:
        req = urllib.request.Request(
            info['url'],
            headers={'User-Agent': 'VoynichResearch/1.0 (academic)'}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        filepath.write_text(text, encoding='utf-8')
        pr(f"    → {len(text)} chars saved")
        time.sleep(2)  # be polite
        return text
    except Exception as e:
        pr(f"    → FAILED: {e}")
        return None


def strip_gutenberg_boilerplate(text):
    """Remove Project Gutenberg header/footer."""
    # Find start
    start_markers = [
        '*** START OF THE PROJECT GUTENBERG',
        '*** START OF THIS PROJECT GUTENBERG',
        '*END*THE SMALL PRINT',
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
        if idx >= 0:
            # Skip to next line after marker
            nl = text.find('\n', idx)
            if nl >= 0:
                start_idx = nl + 1
            break

    end_idx = len(text)
    for marker in end_markers:
        idx = text.find(marker)
        if idx >= 0:
            end_idx = idx
            break

    return text[start_idx:end_idx]


def extract_paragraphs(text):
    """Split text into paragraphs (blank-line separated blocks)."""
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Split on blank lines
    blocks = re.split(r'\n\s*\n', text)
    paragraphs = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Skip very short blocks (titles, page numbers, etc.)
        if len(block) < 20:
            continue
        # Skip blocks that are mostly non-letter (apparatus criticus, etc.)
        letters = sum(1 for c in block if c.isalpha())
        if letters < len(block) * 0.4:
            continue
        paragraphs.append(block)
    return paragraphs


def extract_sentences(text):
    """Split text into sentences (period/colon delimited)."""
    # Simple sentence splitting on . or : followed by space + uppercase
    sents = re.split(r'(?<=[.:])\s+(?=[A-Z])', text)
    return [s.strip() for s in sents if len(s.strip()) > 10]


def first_letter(text):
    """Get the first alphabetic character of a text block."""
    for ch in text:
        if ch.isalpha():
            return ch.upper()
    return None


def compute_initial_distribution(texts, label=""):
    """Compute the first-letter distribution from a list of text blocks."""
    counter = Counter()
    total = 0
    for t in texts:
        ch = first_letter(t)
        if ch:
            counter[ch] += 1
            total += 1
    return counter, total


# ═══════════════════════════════════════════════════════════════════════
# MEDIEVAL LATIN MEDICAL VOCABULARY REFERENCE
# ═══════════════════════════════════════════════════════════════════════

def build_medieval_medical_vocab():
    """
    Build expected paragraph-initial distributions for different
    types of medieval Latin medical texts, based on known vocabulary.

    Sources: Circa Instans, Antidotarium Nicolai, Regimen Sanitatis,
    Tacuinum Sanitatis, etc.
    """
    distributions = {}

    # 1. HERBAL (Circa Instans style) — entries organized by plant
    # The ~300 most common medieval medicinal plants:
    herbal_plants = {
        'A': 35,  # Absinthe, Aloe, Artemisia, Anise, Amygdalum, Acorus, etc.
        'B': 12,  # Borago, Betonica, Buglossa, Bdellium, etc.
        'C': 30,  # Camomilla, Cannabis, Centaurea, Coriandrum, Crocus, Cassia, etc.
        'D': 8,   # Dictamnus, Daucus, Diptamus, Draguntea, etc.
        'E': 10,  # Euphorbium, Enula, Epithymum, etc.
        'F': 8,   # Feniculum, Fumaria, Frangula, etc.
        'G': 8,   # Gentiana, Galanga, Galbanum, etc.
        'H': 6,   # Hyssopus, Hypericum, Hedera, etc.
        'I': 6,   # Iris, Iusquiamus, Ippocratis, etc.
        'J': 2,   # Juniperus, etc.
        'K': 0,   # Latin barely uses K
        'L': 10,  # Lactuca, Lilium, Lavandula, Linum, etc.
        'M': 15,  # Melissa, Mentha, Myristica, Mandragora, Malva, etc.
        'N': 5,   # Nigella, Nasturtium, Nux, etc.
        'O': 5,   # Origanum, Opium, Olibanum, etc.
        'P': 25,  # Plantago, Piper, Peonia, Petroselinum, Portulaca, etc.
        'Q': 2,   # Quercus, etc.
        'R': 12,  # Rosa, Ruta, Rosmarinus, Rhabarbarum, etc.
        'S': 20,  # Salvia, Sambucus, Scabiosa, Senna, Staphisagria, etc.
        'T': 8,   # Tanacetum, Thymus, Terebinthina, etc.
        'U': 5,   # Urtica, etc.
        'V': 10,  # Valeriana, Verbena, Viola, Vinca, etc.
        'X': 1,   # Xilobalsamum, etc.
        'Z': 2,   # Zingiber, Zedoaria, etc.
    }
    distributions['herbal_alphabetical'] = herbal_plants

    # 2. RECIPE / PHARMACEUTICAL (Antidotarium Nicolai style)
    # Entries start with the recipe name or instruction verb
    recipe_vocab = {
        'A': 20,  # Accipe (take), Aliter (alternatively), Ad (for/against)
        'C': 15,  # Contra (against), Cum (when), Confectio, Cura
        'D': 12,  # De (about), Da (give), Deinde
        'E': 8,   # Est, Et (and), Electuarium, Emplastrum
        'F': 10,  # Fiat (let be made), Facies (you will make)
        'I': 12,  # Item (likewise), In (in), Idem
        'M': 5,   # Misce (mix), Mittis (put)
        'N': 5,   # Nota (note), Nomen, Nihil
        'P': 15,  # Piper (pepper), Praeparatio, Pone, Pulvis
        'Q': 5,   # Quod (which), Quomodo (how), Quartum
        'R': 25,  # Recipe (take!) — THE most common in recipe texts
        'S': 15,  # Si (if), Sic (thus), Suffundis, Sume
        'T': 12,  # Teres (grind), Tolle (take away), Tunc
        'U': 3,   # Ut (so that), Unguentum
        'V': 5,   # Virtus (property), Valet
    }
    distributions['recipe_pharma'] = recipe_vocab

    # 3. MEDICAL TREATISE (De Morbis style)
    # Section headings and discussion paragraphs
    treatise_vocab = {
        'A': 10,  # Ac, At, Atque, Ad
        'C': 15,  # Cum, Calidus, Caeterum, Corpus
        'D': 15,  # De (about — VERY common in headings), Deinde
        'E': 10,  # Est, Et, Etenim, Ergo
        'F': 3,   # Fit, Fuerit
        'H': 5,   # Hoc, Haec, Huic
        'I': 10,  # In, Itaque, Item, Iam
        'N': 8,   # Non, Nec, Nam, Neque
        'P': 12,  # Porro, Praeterea, Per, Post
        'Q': 12,  # Quod, Quae, Qui, Quippe, Quomodo
        'R': 3,   # Reliqua, Rursum
        'S': 12,  # Si, Sed, Sic, Siquidem
        'T': 5,   # Tum, Tamen
        'U': 5,   # Ut, Verum (=V)
        'V': 8,   # Verum, Vel
    }
    distributions['medical_treatise'] = treatise_vocab

    # 4. MIXED HERBAL+RECIPE (what VMS might be)
    # Combine plant entries with recipe instructions
    mixed_vocab = {}
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        h = herbal_plants.get(letter, 0)
        r = recipe_vocab.get(letter, 0)
        mixed_vocab[letter] = h + r
    distributions['mixed_herbal_recipe'] = mixed_vocab

    return distributions


# ═══════════════════════════════════════════════════════════════════════
# COMBINATORIAL MAPPING ENGINE
# ═══════════════════════════════════════════════════════════════════════

def test_all_4letter_mappings(latin_dist, vms_dist_rel, vms_coverage):
    """
    Test all possible mappings of 4 VMS gallows → 4 Latin letters.

    For each 4-letter subset of the Latin alphabet:
      For each permutation mapping VMS (p,t,k,f) → Latin (a,b,c,d):
        Compute coverage (sum of 4 Latin letter proportions)
        Compute L2 distance between relative proportions
        Compute chi-squared goodness-of-fit

    Returns top N best mappings sorted by score.
    """
    # Normalize Latin distribution
    total_latin = sum(latin_dist.values())
    if total_latin == 0:
        return []
    latin_props = {k: v/total_latin for k, v in latin_dist.items()}

    # Get all letters that appear
    latin_letters = sorted([k for k, v in latin_dist.items() if v > 0])

    vms_order = ['p', 't', 'k', 'f']
    vms_rel = [vms_dist_rel[g] for g in vms_order]  # relative proportions

    results = []
    n_tested = 0

    for combo in combinations(latin_letters, 4):
        combo_coverage = sum(latin_props.get(c, 0) for c in combo)
        combo_counts = [latin_dist.get(c, 0) for c in combo]
        combo_total = sum(combo_counts)

        if combo_total < 4:
            continue

        # Relative proportions within the 4-letter subset
        combo_rel = [c/combo_total for c in combo_counts]

        for perm in permutations(range(4)):
            n_tested += 1
            # Map VMS gallows to Latin letters according to permutation
            # perm[i] tells us which Latin letter maps to VMS gallows[i]
            mapped_rel = [combo_rel[perm[i]] for i in range(4)]

            # L2 distance between relative proportions
            l2 = math.sqrt(sum((a - b)**2 for a, b in zip(vms_rel, mapped_rel)))

            # Coverage penalty (how far from VMS's 81.4%)
            coverage_diff = abs(combo_coverage - vms_coverage)

            # Combined score: lower is better
            score = l2 + coverage_diff

            mapping = {vms_order[i]: combo[perm[i]] for i in range(4)}

            results.append({
                'mapping': mapping,
                'latin_letters': combo,
                'coverage': combo_coverage,
                'l2_relative': l2,
                'coverage_diff': coverage_diff,
                'score': score,
                'mapped_props': {vms_order[i]: mapped_rel[i] for i in range(4)},
            })

    # Sort by score (best first)
    results.sort(key=lambda x: x['score'])
    return results[:50], n_tested


def test_4letter_mappings_fast(latin_dist, vms_dist_rel, vms_coverage):
    """
    Optimized version: pre-sort Latin letters by frequency and
    use early pruning to skip unpromising combinations.
    """
    total_latin = sum(latin_dist.values())
    if total_latin == 0:
        return [], 0
    latin_props = {k: v/total_latin for k, v in latin_dist.items()}

    latin_letters = sorted([k for k, v in latin_dist.items() if v > 0])

    vms_order = ['p', 't', 'k', 'f']
    vms_rel = np.array([vms_dist_rel[g] for g in vms_order])

    best = []
    best_score = float('inf')
    n_tested = 0
    n_combos = 0

    for combo in combinations(latin_letters, 4):
        n_combos += 1
        combo_coverage = sum(latin_props.get(c, 0) for c in combo)
        coverage_diff = abs(combo_coverage - vms_coverage)

        # Early prune: if coverage diff alone exceeds best score, skip
        if coverage_diff > best_score + 0.2:
            continue

        combo_counts = [latin_dist.get(c, 0) for c in combo]
        combo_total = sum(combo_counts)
        if combo_total < 4:
            continue

        combo_rel = np.array([c/combo_total for c in combo_counts])

        for perm in permutations(range(4)):
            n_tested += 1
            mapped_rel = np.array([combo_rel[perm[i]] for i in range(4)])
            l2 = float(np.sqrt(np.sum((vms_rel - mapped_rel)**2)))
            score = l2 + coverage_diff

            if len(best) < 50 or score < best[-1]['score']:
                mapping = {vms_order[i]: combo[perm[i]] for i in range(4)}
                entry = {
                    'mapping': mapping,
                    'latin_letters': combo,
                    'coverage': combo_coverage,
                    'l2_relative': l2,
                    'coverage_diff': coverage_diff,
                    'score': score,
                    'mapped_props': {vms_order[i]: float(mapped_rel[i])
                                     for i in range(4)},
                }
                best.append(entry)
                best.sort(key=lambda x: x['score'])
                best = best[:50]
                best_score = best[-1]['score'] if best else float('inf')

    return best, n_tested


# ═══════════════════════════════════════════════════════════════════════
# VMS DATA LOADING (for section-specific analysis)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']

def eva_first_glyph(word):
    w = word.lower()
    if len(w) >= 3 and w[:3] in GALLOWS_TRI: return w[:3]
    if len(w) >= 2 and w[:2] in GALLOWS_BI: return w[:2]
    return w[0] if w else ''


def folio_number(fname):
    m = re.match(r'f(\d+)', fname)
    return int(m.group(1)) if m else 0



def load_vms_para_initials_by_section():
    """Load VMS paragraph-initial distributions by section from folios."""
    section_initials = defaultdict(Counter)
    folio_files = sorted(FOLIO_DIR.glob('*.txt'))

    for fpath in folio_files:
        fname = fpath.stem
        fnum = folio_number(fname)
        section = folio_section(fnum)

        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
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

                is_para_start = '@P' in tag or '<%>' in rest
                if not is_para_start:
                    continue

                text = rest.replace('<%>', '').replace('<$>', '').strip()
                words = []
                for tok in re.split(r'[.\s]+', text):
                    for subtok in re.split(r',', tok):
                        c = clean_word(subtok.strip())
                        if c:
                            words.append(c)

                if words:
                    g = eva_first_glyph(words[0])
                    if g:
                        section_initials[section][g] += 1

    return dict(section_initials)


# ═══════════════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def analyze_latin_text(key, text, info):
    """Full analysis of one Latin text."""
    pr(f"\n{'─'*70}")
    pr(f"TEXT: {info['title']}")
    pr(f"Genre: {info['genre']} | Era: {info['era']}")
    pr(f"{'─'*70}")

    # Strip boilerplate
    clean = strip_gutenberg_boilerplate(text)
    pr(f"Text length: {len(clean):,} chars after boilerplate removal")

    # Extract paragraphs
    paras = extract_paragraphs(clean)
    pr(f"Paragraphs extracted: {len(paras)}")

    if len(paras) < 20:
        pr(f"  → Too few paragraphs for meaningful analysis, skipping")
        return None

    # Paragraph-initial distribution
    para_dist, para_total = compute_initial_distribution(paras, "paragraph")
    pr(f"\nParagraph-initial letter distribution (n={para_total}):")
    for letter, count in sorted(para_dist.items(), key=lambda x: -x[1])[:15]:
        pct = count / para_total * 100
        bar = '█' * int(pct / 2)
        pr(f"  {letter}: {count:4d} ({pct:5.1f}%) {bar}")

    # Top-4 coverage
    top4 = sorted(para_dist.items(), key=lambda x: -x[1])[:4]
    top4_coverage = sum(v for _, v in top4) / para_total
    top4_letters = [k for k, _ in top4]
    pr(f"\nTop-4 letters: {top4_letters} → coverage: {top4_coverage:.1%}")
    pr(f"VMS gallows coverage: {VMS_GALLOWS_COVERAGE:.1%}")
    pr(f"Gap: {abs(top4_coverage - VMS_GALLOWS_COVERAGE):.1%}")

    # Sentence-initial distribution
    sents = extract_sentences(clean)
    sent_dist, sent_total = compute_initial_distribution(sents, "sentence")
    if sent_total > 20:
        pr(f"\nSentence-initial letter distribution (n={sent_total}):")
        for letter, count in sorted(sent_dist.items(), key=lambda x: -x[1])[:10]:
            pct = count / sent_total * 100
            pr(f"  {letter}: {count:4d} ({pct:5.1f}%)")

        sent_top4 = sorted(sent_dist.items(), key=lambda x: -x[1])[:4]
        sent_top4_cov = sum(v for _, v in sent_top4) / sent_total
        pr(f"  Top-4 sentence-initial coverage: {sent_top4_cov:.1%}")

    # Test mappings
    pr(f"\nTesting all 4-letter mappings against VMS gallows distribution...")
    best_para, n_tested_para = test_4letter_mappings_fast(
        para_dist, VMS_GALLOWS_REL, VMS_GALLOWS_COVERAGE
    )
    pr(f"  Tested {n_tested_para:,} mappings")

    if best_para:
        pr(f"\n  TOP 10 PARAGRAPH-INITIAL MAPPINGS:")
        pr(f"  {'Rank':>4} {'Score':>7} {'L2':>7} {'Cov%':>6} {'p→':>4} {'t→':>4} {'k→':>4} {'f→':>4}")
        for i, r in enumerate(best_para[:10]):
            m = r['mapping']
            pr(f"  {i+1:4d} {r['score']:.4f} {r['l2_relative']:.4f} "
               f"{r['coverage']:.1%} "
               f"{m['p']:>4} {m['t']:>4} {m['k']:>4} {m['f']:>4}")

        # Best mapping interpretation
        best = best_para[0]
        pr(f"\n  BEST MAPPING: {best['mapping']}")
        pr(f"  Score: {best['score']:.4f} (L2={best['l2_relative']:.4f}, "
           f"CovΔ={best['coverage_diff']:.4f})")
        pr(f"  Coverage: {best['coverage']:.1%} (VMS: {VMS_GALLOWS_COVERAGE:.1%})")
        pr(f"  Proportions (within 4 letters):")
        for g in ['p', 't', 'k', 'f']:
            vms_val = VMS_GALLOWS_REL[g]
            lat_val = best['mapped_props'][g]
            pr(f"    VMS {g} → Latin {best['mapping'][g]}: "
               f"VMS={vms_val:.3f}, Latin={lat_val:.3f}, "
               f"Δ={abs(vms_val-lat_val):.3f}")

    return {
        'key': key,
        'title': info['title'],
        'genre': info['genre'],
        'n_paragraphs': para_total,
        'para_dist': dict(para_dist),
        'top4_coverage': top4_coverage,
        'top4_letters': top4_letters,
        'n_sentences': sent_total if sent_total > 20 else 0,
        'sent_dist': dict(sent_dist) if sent_total > 20 else {},
        'best_mappings_para': best_para[:20] if best_para else [],
        'n_tested': n_tested_para,
    }


def analyze_vocab_distribution(name, dist):
    """Analyze a vocabulary-based distribution."""
    pr(f"\n{'─'*70}")
    pr(f"VOCABULARY MODEL: {name}")
    pr(f"{'─'*70}")

    total = sum(dist.values())
    pr(f"Total entries: {total}")

    pr(f"\nLetter distribution:")
    for letter, count in sorted(dist.items(), key=lambda x: -x[1])[:15]:
        if count == 0:
            continue
        pct = count / total * 100
        bar = '█' * int(pct / 2)
        pr(f"  {letter}: {count:4d} ({pct:5.1f}%) {bar}")

    top4 = sorted(dist.items(), key=lambda x: -x[1])[:4]
    top4_coverage = sum(v for _, v in top4) / total
    top4_letters = [k for k, _ in top4]
    pr(f"\nTop-4 letters: {top4_letters} → coverage: {top4_coverage:.1%}")
    pr(f"VMS gallows coverage: {VMS_GALLOWS_COVERAGE:.1%}")

    # Test mappings
    pr(f"\nTesting all 4-letter mappings...")
    best, n_tested = test_4letter_mappings_fast(
        dist, VMS_GALLOWS_REL, VMS_GALLOWS_COVERAGE
    )
    pr(f"  Tested {n_tested:,} mappings")

    if best:
        pr(f"\n  TOP 10 MAPPINGS:")
        pr(f"  {'Rank':>4} {'Score':>7} {'L2':>7} {'Cov%':>6} {'p→':>4} {'t→':>4} {'k→':>4} {'f→':>4}")
        for i, r in enumerate(best[:10]):
            m = r['mapping']
            pr(f"  {i+1:4d} {r['score']:.4f} {r['l2_relative']:.4f} "
               f"{r['coverage']:.1%} "
               f"{m['p']:>4} {m['t']:>4} {m['k']:>4} {m['f']:>4}")

        best_m = best[0]
        pr(f"\n  BEST: {best_m['mapping']} (score={best_m['score']:.4f})")

    return {
        'name': name,
        'total': total,
        'dist': dict(dist),
        'top4_coverage': top4_coverage,
        'top4_letters': top4_letters,
        'best_mappings': best[:20] if best else [],
    }


# ═══════════════════════════════════════════════════════════════════════
# CROSS-REFERENCE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def cross_reference_analysis(all_results, vocab_results):
    """Look for convergence across texts and vocabulary models."""
    pr(f"\n{'═'*70}")
    pr(f"CROSS-REFERENCE ANALYSIS")
    pr(f"{'═'*70}")

    # Collect all best mappings
    mapping_votes = Counter()
    letter_assignments = defaultdict(Counter)

    for r in all_results:
        if r and r.get('best_mappings_para'):
            for rank, m in enumerate(r['best_mappings_para'][:5]):
                weight = 5 - rank  # top mapping gets weight 5
                mapping_key = tuple(sorted(m['mapping'].items()))
                mapping_votes[mapping_key] += weight
                for vms_g, latin_l in m['mapping'].items():
                    letter_assignments[vms_g][latin_l] += weight

    for r in vocab_results:
        if r and r.get('best_mappings'):
            for rank, m in enumerate(r['best_mappings'][:5]):
                weight = 5 - rank
                mapping_key = tuple(sorted(m['mapping'].items()))
                mapping_votes[mapping_key] += weight
                for vms_g, latin_l in m['mapping'].items():
                    letter_assignments[vms_g][latin_l] += weight

    pr(f"\nLetter assignment votes (across all sources, weighted by rank):")
    for vms_g in ['p', 't', 'k', 'f']:
        pr(f"  VMS '{vms_g}' → ", end='')
        top = letter_assignments[vms_g].most_common(5)
        parts = [f"{l}({w})" for l, w in top]
        pr(', '.join(parts))

    # Top consensus mappings
    pr(f"\nTop consensus mappings (total weighted votes):")
    for mapping, votes in mapping_votes.most_common(10):
        m_dict = dict(mapping)
        pr(f"  votes={votes:3d}  p→{m_dict['p']} t→{m_dict['t']} "
           f"k→{m_dict['k']} f→{m_dict['f']}")

    # Coverage analysis
    pr(f"\nTop-4 coverage comparison:")
    pr(f"  VMS gallows:         {VMS_GALLOWS_COVERAGE:.1%}")
    for r in all_results:
        if r:
            pr(f"  {r['key']:20s}  {r['top4_coverage']:.1%}  {r['top4_letters']}")
    for r in vocab_results:
        if r:
            pr(f"  {r['name']:20s}  {r['top4_coverage']:.1%}  {r['top4_letters']}")


def skeptical_analysis(all_results, vocab_results):
    """Critical evaluation of findings."""
    pr(f"\n{'═'*70}")
    pr(f"SKEPTICAL ANALYSIS")
    pr(f"{'═'*70}")

    # Q1: Is ~81% coverage in 4 letters unusual?
    pr(f"\n1. IS 81% COVERAGE IN 4 LETTERS UNUSUAL FOR LATIN?")
    coverages = []
    for r in all_results:
        if r:
            coverages.append((r['key'], r['top4_coverage']))
    for r in vocab_results:
        if r:
            coverages.append((r['name'], r['top4_coverage']))

    if coverages:
        avg_cov = np.mean([c for _, c in coverages])
        pr(f"  Average top-4 coverage across sources: {avg_cov:.1%}")
        pr(f"  VMS gallows coverage: {VMS_GALLOWS_COVERAGE:.1%}")
        if VMS_GALLOWS_COVERAGE > avg_cov + 0.10:
            pr(f"  → VMS is SIGNIFICANTLY more concentrated than typical Latin")
            pr(f"    This suggests gallows are NOT simple letter substitutions,")
            pr(f"    OR the text has unusual structural constraints.")
        elif VMS_GALLOWS_COVERAGE > avg_cov:
            pr(f"  → VMS is somewhat more concentrated than average Latin")
        else:
            pr(f"  → VMS concentration is comparable to Latin — mapping plausible")

    # Q2: Do best mappings make linguistic sense?
    pr(f"\n2. DO BEST MAPPINGS MAKE LINGUISTIC SENSE?")
    pr(f"  For a medical/herbal text, we'd expect frequent paragraph-initial letters to be:")
    pr(f"  D (De...), C (Contra/Cum...), S (Si/Sed...), P (Piper/Praeparatio...),")
    pr(f"  R (Recipe...), A (Accipe/Ad...), I (Item/In...), E (Est/Et...)")
    pr(f"  Letters K, X, Z should be very rare in Latin.")

    # Q3: Herbal vs Recipe convergence
    pr(f"\n3. SECTION-SPECIFIC ANALYSIS")
    pr(f"  VMS herbal:  p=34%, t=28%, k=17%, f=5% (more balanced)")
    pr(f"  VMS recipe:  p=54%, t=21%, k=7%,  f=5% (p-dominated)")
    pr(f"  VMS balneo:  p=54%, t=15%, k=5%,  f=2% (p-dominated)")
    pr(f"  If gallows = Latin letters, the SAME 4 letters should work for all sections.")
    pr(f"  The VMS sections show DIFFERENT relative frequencies → either:")
    pr(f"    a) Different genre of text uses different words (plausible)")
    pr(f"    b) Gallows are not simple letter substitutions")

    # Q4: Could gallows be something other than letters?
    pr(f"\n4. ALTERNATIVE HYPOTHESES")
    pr(f"  Gallows could be:")
    pr(f"  a) Paragraph-TYPE markers (herbal=p, recipe=t, instruction=k, note=f)")
    pr(f"  b) Abbreviated words (not single letters)")
    pr(f"  c) Coptic-style structural markers")
    pr(f"  d) Simple letter substitutions (what this phase tests)")
    pr(f"  e) Section-specific cipher elements")

    # Q5: Information content
    pr(f"\n5. INFORMATION CONTENT CHECK")
    h_gallows = -sum(p * math.log2(p) for p in VMS_GALLOWS_REL.values() if p > 0)
    pr(f"  Entropy of gallows distribution: {h_gallows:.3f} bits")
    pr(f"  Max possible (uniform 4): {math.log2(4):.3f} bits")
    pr(f"  Efficiency: {h_gallows/math.log2(4):.1%}")
    pr(f"  This means the gallows carry {h_gallows:.2f} bits of information")
    pr(f"  per paragraph start — consistent with choosing from ~{2**h_gallows:.1f}")
    pr(f"  equiprobable options (not 4 equal → not 4 random letters)")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("═" * 70)
    pr("latin_paragraph_initials — LATIN PARAGRAPH-INITIAL LETTER MAPPING")
    pr("Can VMS gallows be mapped to Latin letters?")
    pr("═" * 70)

    pr(f"\nVMS Gallows Paragraph-Initial Distribution (n={VMS_TOTAL_PARAS}):")
    for g in ['p', 't', 'k', 'f']:
        pct = VMS_GALLOWS_PROPS[g] * 100
        bar = '█' * int(pct / 2)
        pr(f"  {g}: {VMS_GALLOWS_RAW[g]:4d} ({pct:5.1f}%) {bar}")
    pr(f"  Total gallows: {VMS_GALLOWS_TOTAL} ({VMS_GALLOWS_COVERAGE:.1%})")

    # ─── Part 1: Download and analyze Latin texts ───
    pr(f"\n{'═'*70}")
    pr(f"PART 1: EMPIRICAL LATIN TEXT ANALYSIS")
    pr(f"{'═'*70}")

    pr(f"\nDownloading Latin texts from Project Gutenberg...")
    all_results = []
    for key, info in GUTENBERG_TEXTS.items():
        text = download_text(key, info)
        if text:
            result = analyze_latin_text(key, text, info)
            all_results.append(result)
        else:
            all_results.append(None)

    # ─── Part 2: Medieval medical vocabulary models ───
    pr(f"\n{'═'*70}")
    pr(f"PART 2: MEDIEVAL LATIN MEDICAL VOCABULARY MODELS")
    pr(f"{'═'*70}")

    vocab_dists = build_medieval_medical_vocab()
    vocab_results = []
    for name, dist in vocab_dists.items():
        result = analyze_vocab_distribution(name, dist)
        vocab_results.append(result)

    # ─── Part 3: Section-specific VMS analysis ───
    pr(f"\n{'═'*70}")
    pr(f"PART 3: VMS SECTION-SPECIFIC DISTRIBUTIONS")
    pr(f"{'═'*70}")

    section_data = load_vms_para_initials_by_section()
    for section, counter in sorted(section_data.items()):
        total = sum(counter.values())
        if total < 10:
            continue
        pr(f"\n  Section: {section} (n={total})")
        gallows = ['p', 't', 'k', 'f']
        g_sum = sum(counter.get(g, 0) for g in gallows)
        pr(f"  Gallows coverage: {g_sum/total:.1%}")
        for g, cnt in sorted(counter.items(), key=lambda x: -x[1])[:8]:
            pct = cnt / total * 100
            is_g = ' ← GALLOWS' if g in gallows else ''
            pr(f"    {g:>4}: {cnt:3d} ({pct:5.1f}%){is_g}")

    # ─── Part 4: Cross-reference ───
    cross_reference_analysis(all_results, vocab_results)

    # ─── Part 5: Skeptical analysis ───
    skeptical_analysis(all_results, vocab_results)

    # ─── Summary ───
    pr(f"\n{'═'*70}")
    pr(f"latin_paragraph_initials SUMMARY")
    pr(f"{'═'*70}")

    # Collect all unique best mapping letter-sets
    all_best_sets = set()
    for r in all_results:
        if r and r.get('best_mappings_para'):
            m = r['best_mappings_para'][0]['mapping']
            all_best_sets.add(frozenset(m.values()))
    for r in vocab_results:
        if r and r.get('best_mappings'):
            m = r['best_mappings'][0]['mapping']
            all_best_sets.add(frozenset(m.values()))

    pr(f"\nUnique 4-letter sets from best mappings: {len(all_best_sets)}")
    for s in all_best_sets:
        pr(f"  {sorted(s)}")

    # Check if any Latin text naturally has ~81% in 4 letters
    high_coverage = []
    for r in all_results:
        if r and r['top4_coverage'] >= 0.70:
            high_coverage.append(r)

    if high_coverage:
        pr(f"\nTexts with ≥70% top-4 coverage (comparable to VMS 81%):")
        for r in high_coverage:
            pr(f"  {r['key']}: {r['top4_coverage']:.1%} {r['top4_letters']}")
    else:
        pr(f"\nNO Latin text reaches 70% coverage in top-4 letters.")
        pr(f"This suggests VMS 81% gallows concentration is UNUSUAL.")

    pr(f"\n{'═'*70}")
    pr(f"KEY FINDINGS:")
    pr(f"{'═'*70}")

    pr(f"""
1. VMS gallows account for {VMS_GALLOWS_COVERAGE:.1%} of paragraph starts.
   This extreme concentration needs explanation.

2. Best-fit Latin letter mappings are reported above per text/model.

3. The critical question is whether ANY Latin text genre naturally
   concentrates ~81% of paragraph starts in just 4 letters.

4. Section-specific VMS distributions (herbal=balanced, recipe=p-heavy)
   should ideally be explained by the same 4-letter mapping with
   different genres of Latin text.
""")

    # ─── Save results ───
    results_json = {
        'vms_gallows': VMS_GALLOWS_RAW,
        'vms_coverage': VMS_GALLOWS_COVERAGE,
        'vms_gallows_relative': VMS_GALLOWS_REL,
        'text_results': [],
        'vocab_results': [],
        'section_data': {k: dict(v) for k, v in section_data.items()},
    }

    for r in all_results:
        if r:
            # Remove non-serializable items
            safe = {k: v for k, v in r.items() if k != 'best_mappings_para'}
            safe['best_mappings_para'] = r.get('best_mappings_para', [])[:10]
            results_json['text_results'].append(safe)

    for r in vocab_results:
        if r:
            safe = {k: v for k, v in r.items() if k != 'best_mappings'}
            safe['best_mappings'] = r.get('best_mappings', [])[:10]
            results_json['vocab_results'].append(safe)

    out_json = RESULTS_DIR / 'latin_paragraph_initials.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results_json, f, indent=2, ensure_ascii=False, default=str)
    pr(f"\nJSON results → {out_json}")

    out_txt = RESULTS_DIR / 'latin_paragraph_initials.txt'
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"Full output → {out_txt}")


if __name__ == '__main__':
    main()
