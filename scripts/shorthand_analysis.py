#!/usr/bin/env python3
"""
VOYNICH MANUSCRIPT — PHARMACEUTICAL SHORTHAND HYPOTHESIS
=========================================================
Tests whether Voynichese is a positional notation system (like
Tironian notes, Cistercian numerals, or apothecary shorthand)
rather than a cipher of natural language.

Tests:
  1. f66r LIST DECONSTRUCTION — Map single chars to word list
  2. RECIPE PATTERN DETECTION — Find repeated prefix+suffix frames
     with varying roots (= same preparation, different ingredients)
  3. SECTION-SPECIFIC NOTATION — Herbal vs Pharma vs Astro vs Bio
     should show different morpheme distributions if it's domain notation
  4. POSITIONAL COMPOSITION — Test Tironian/Cistercian structural parallels
  5. FORMULAIC SEQUENCE DETECTION — Find repeated multi-word templates
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from common import classify_folio_v3 as classify_folio, get_root, result_path

# ═══════════════════════════════════════════════════════════════════════════
# PARSER (reused)
# ═══════════════════════════════════════════════════════════════════════════

PREFIXES = [
    "qol", "qor", "sol", "sor", "dol", "dor", "dyl", "dyr",
    "qo", "so", "do", "dy",
    "ol", "or", "yl", "yr",
    "q", "d", "s",
    "o", "y",
    "l", "r",
]

ROOT_ONSETS = [
    "ckh", "cth", "cph", "cfh",
    "tch", "kch", "pch", "fch",
    "tsh", "ksh", "psh", "fsh",
    "sh", "ch",
    "f", "p", "k", "t",
]

ROOT_BODIES = [
    "eeed", "eees", "eeea", "eeeo",
    "eed", "ees", "eea", "eeo",
    "ed", "es", "ea", "eo",
    "eee", "ee", "e",
    "da", "do", "sa", "so",
    "d", "s",
    "a", "o",
]

SUFFIXES = [
    "iiiny", "iiny", "iiir", "iiil", "iiin",
    "iir", "iil", "iin", "iim", "iid",
    "iry", "ily", "iny",
    "ir", "il", "in", "im", "id",
    "iii", "ii",
    "dy", "ly", "ry", "ny", "my",
    "i",
    "y",
    "n", "m", "d", "l", "r",
]


def parse_word(word):
    best = None
    best_score = -1
    prefix_options = [""]
    for pfx in PREFIXES:
        if word.startswith(pfx):
            prefix_options.append(pfx)
    for pfx in prefix_options:
        rest1 = word[len(pfx):]
        onset_options = [""]
        for onset in ROOT_ONSETS:
            if rest1.startswith(onset):
                onset_options.append(onset)
        for onset in onset_options:
            rest2 = rest1[len(onset):]
            body_options = [""]
            for body in ROOT_BODIES:
                if rest2.startswith(body):
                    body_options.append(body)
            for body in body_options:
                rest3 = rest2[len(body):]
                suf_options = [""]
                for suf in SUFFIXES:
                    if rest3 == suf:
                        suf_options.append(suf)
                for suf in SUFFIXES:
                    if rest3.endswith(suf) and rest3 != suf:
                        suf_options.append(suf)
                for suf in suf_options:
                    if suf and rest3.endswith(suf):
                        remainder = rest3[:-len(suf)] if suf else rest3
                    elif suf and rest3 == suf:
                        remainder = ""
                    else:
                        remainder = rest3
                    explained = len(pfx) + len(onset) + len(body) + len(suf)
                    score = explained * 10 - len(remainder) * 15
                    if not remainder:
                        score += 50
                    if onset or body:
                        score += 20
                    if not onset and not body and (pfx or suf):
                        score -= 10
                    if score > best_score:
                        best_score = score
                        best = (pfx, onset, body, suf, remainder)
    if best is None:
        return ("", "", "", "", word)
    return best




# ═══════════════════════════════════════════════════════════════════════════
# DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════



def extract_all_data(txt_files):
    """Extract words preserving line structure, section, language, labels, and folios."""
    all_data = {
        'text_lines': [],           # (folio, section, lang, [words])
        'label_words': [],          # (word, folio, section)
        'folio_info': {},           # folio -> {section, lang}
        'section_words': defaultdict(list),
        'lang_words': defaultdict(list),
    }

    for txt_file in txt_files:
        lines_raw = txt_file.read_text(encoding="utf-8").splitlines()
        header_lines = []
        folio_name = txt_file.stem
        section, lang = None, None

        for line in lines_raw:
            stripped = line.strip()
            if stripped.startswith("#") or re.match(r"^<f\w+>\s", stripped):
                header_lines.append(stripped)
                continue
            if not stripped or stripped.startswith("<!"):
                continue

            m = re.match(r"<([^>]+)>\s*(.*)", stripped)
            if not m:
                continue
            locus = m.group(1)
            text = m.group(2)
            is_label = bool(re.search(r"[,@*+]L", locus))

            text = re.sub(r"<![^>]*>", "", text)
            text = re.sub(r"<%>|<\$>|<->", " ", text)
            text = re.sub(r"<[^>]*>", "", text)
            text = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", text)
            text = re.sub(r"\{([^}]+)\}", r"\1", text)
            text = re.sub(r"@\d+;?", "", text)
            tokens = re.split(r"[.\s,<>\-]+", text)
            line_words = []
            for tok in tokens:
                tok = tok.strip()
                if not tok or "?" in tok or "'" in tok:
                    continue
                if re.match(r"^[a-z]+$", tok) and len(tok) >= 2:
                    if is_label:
                        all_data['label_words'].append((tok, folio_name, section))
                    else:
                        line_words.append(tok)

            if line_words:
                if section is None:
                    section, lang = classify_folio(header_lines)
                    all_data['folio_info'][folio_name] = {'section': section, 'lang': lang}
                all_data['text_lines'].append((folio_name, section, lang, line_words))
                for w in line_words:
                    all_data['section_words'][section].append(w)
                    all_data['lang_words'][lang].append(w)

        if section is None:
            section, lang = classify_folio(header_lines)
            all_data['folio_info'][folio_name] = {'section': section, 'lang': lang}

    return all_data


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: f66r LIST DECONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════

def analyze_f66r():
    """
    f66r has:
      - Column of 15 words (L0 labels, numbered 1-15)
      - Column of single characters (L0 labels, numbered 16-49)
      - Body text (P0 paragraphs)
      - Label text near figure (Lx)

    Test relationships between the word list and character column.
    """
    f66r_words = [
        "rary", "sals", "qorn", "dary", "ykeol",
        "saly", "salf", "fary", "qotesy", "ykaly",
        "doly", "saiin", "qokal", "qolsa", "raral",
    ]

    f66r_chars = [
        "y", "o", "s", "sh", "y", "d", "o", "f",
        None,  # @169 — unknown glyph
        "x", "air", "d", "sh", "y", "f", "f",
        "y", "o", "d", "s", "f", "c",
        None,  # @172 — unknown glyph
        "x", "t", "o",
        None,  # @195 — unknown glyph
        "l", "r", "t", "o", "x", "p", "d",
    ]

    # Parse the 15 words
    word_parses = []
    for w in f66r_words:
        p = parse_word(w)
        word_parses.append({
            'word': w,
            'prefix': p[0] or '∅',
            'onset': p[1] or '∅',
            'body': p[2] or '∅',
            'suffix': p[3] or '∅',
            'remainder': p[4],
            'root': get_root(p[1], p[2]),
        })

    # Test 1a: Do single chars correspond to first letters of words?
    first_letters = [w[0] for w in f66r_words]
    chars_no_none = [c for c in f66r_chars if c is not None and len(c) == 1]

    # Test 1b: Do single chars match the PREFIX of corresponding words?
    # (15 words, 33 chars → chars might map 2-per-word or to something else)

    # Test 1c: Extract prefix distribution of the 15 words
    list_prefixes = Counter(wp['prefix'] for wp in word_parses)
    list_suffixes = Counter(wp['suffix'] for wp in word_parses)
    list_onsets = Counter(wp['onset'] for wp in word_parses)
    list_bodies = Counter(wp['body'] for wp in word_parses)

    # Test 1d: Are the 15 words structurally consistent?
    # (Same template = same notation category)
    templates = Counter()
    for wp in word_parses:
        tmpl = f"{wp['prefix']}+_+{wp['suffix']}"
        templates[tmpl] = templates.get(tmpl, 0) + 1

    # Test 1e: Character frequency in single-char column
    char_freq = Counter(c for c in f66r_chars if c is not None)

    # Test 1f: Check if chars could be abbreviations (Tironian-style)
    # Map each char to which words START with that char
    char_to_words = defaultdict(list)
    for c in set(c for c in f66r_chars if c is not None and len(c) <= 2):
        for w in f66r_words:
            if w.startswith(c):
                char_to_words[c].append(w)

    # Test 1g: Check if 15 words map to known list types
    # Count 15 → could be: 15 ingredients in a recipe, zodiac subset,
    # days (half-month), musical intervals, etc.

    return {
        'words': word_parses,
        'chars': f66r_chars,
        'char_freq': dict(char_freq),
        'first_letters': first_letters,
        'list_prefixes': dict(list_prefixes),
        'list_suffixes': dict(list_suffixes),
        'list_onsets': dict(list_onsets),
        'list_bodies': dict(list_bodies),
        'templates': dict(templates),
        'char_to_words': dict(char_to_words),
    }


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: RECIPE PATTERN DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def detect_recipe_patterns(all_data, parses):
    """
    In pharmaceutical shorthand, a 'recipe' would look like:
      PREFIX + root1 + SUFFIX, PREFIX + root2 + SUFFIX, PREFIX + root3 + SUFFIX
    (Same operation applied to different ingredients)

    Detect sequences where adjacent words share prefix+suffix but differ in root.
    Also detect repeated "frame" patterns across the corpus.
    """
    # Build parsed lines
    parsed_lines = []
    for folio, section, lang, words in all_data['text_lines']:
        parsed = []
        for w in words:
            p = parses.get(w)
            if p and not p[4]:
                parsed.append({
                    'word': w,
                    'prefix': p[0],
                    'root': get_root(p[1], p[2]),
                    'suffix': p[3],
                    'onset': p[1],
                    'body': p[2],
                })
            else:
                parsed.append(None)
        parsed_lines.append((folio, section, lang, words, parsed))

    # Detect "frame sequences" — runs where prefix+suffix stay constant
    frame_runs = []  # (folio, section, frame, [roots], [words])
    for folio, section, lang, words, parsed in parsed_lines:
        i = 0
        while i < len(parsed):
            if parsed[i] is None:
                i += 1
                continue
            frame = (parsed[i]['prefix'], parsed[i]['suffix'])
            run_roots = [parsed[i]['root']]
            run_words = [parsed[i]['word']]
            j = i + 1
            while j < len(parsed) and parsed[j] is not None:
                next_frame = (parsed[j]['prefix'], parsed[j]['suffix'])
                if next_frame == frame and parsed[j]['root'] != run_roots[-1]:
                    run_roots.append(parsed[j]['root'])
                    run_words.append(parsed[j]['word'])
                    j += 1
                else:
                    break
            if len(run_roots) >= 2:
                frame_runs.append({
                    'folio': folio,
                    'section': section,
                    'prefix': frame[0] or '∅',
                    'suffix': frame[1] or '∅',
                    'frame': f"{frame[0] or '∅'}+_+{frame[1] or '∅'}",
                    'roots': run_roots,
                    'words': run_words,
                    'length': len(run_roots),
                })
            i = j

    # Count frame frequencies
    frame_freq = Counter(fr['frame'] for fr in frame_runs)

    # Find the longest runs
    frame_runs.sort(key=lambda x: -x['length'])

    # Detect "template repetition" — same word-skeleton appearing at regular intervals
    # (Like a recipe header repeated for each preparation)
    skeleton_sequences = defaultdict(list)  # skeleton -> list of (folio, line_idx, position)
    for line_idx, (folio, section, lang, words, parsed) in enumerate(parsed_lines):
        for pos, p in enumerate(parsed):
            if p is not None:
                skeleton = f"{p['prefix']}+{p['onset']}+{p['suffix']}"
                skeleton_sequences[skeleton].append((folio, line_idx, pos))

    # Find skeletons that repeat with regular spacing
    regular_skeletons = []
    for skeleton, occurrences in skeleton_sequences.items():
        if len(occurrences) < 10:
            continue
        # Check if occurrences cluster at specific line positions
        positions = [pos for _, _, pos in occurrences]
        pos_counter = Counter(positions)
        total = len(positions)
        # Does this skeleton prefer line-initial (pos=0)?
        initial_frac = pos_counter.get(0, 0) / total
        # Or line-final?
        # We don't know line length easily, so just check pos=0
        regular_skeletons.append({
            'skeleton': skeleton,
            'count': len(occurrences),
            'initial_frac': initial_frac,
            'top_positions': pos_counter.most_common(3),
        })

    regular_skeletons.sort(key=lambda x: -x['count'])

    # Detect "ingredient lists" — lines with high root diversity but constant frame
    ingredient_lines = []
    for folio, section, lang, words, parsed in parsed_lines:
        valid = [p for p in parsed if p is not None]
        if len(valid) < 3:
            continue
        frames = [f"{p['prefix']}+{p['suffix']}" for p in valid]
        roots = [p['root'] for p in valid]
        unique_frames = len(set(frames))
        unique_roots = len(set(roots))
        # Low frame diversity + high root diversity = ingredient list
        if unique_frames <= 2 and unique_roots >= 3:
            ingredient_lines.append({
                'folio': folio,
                'section': section,
                'words': [p['word'] for p in valid],
                'frames': frames,
                'roots': roots,
                'dominant_frame': Counter(frames).most_common(1)[0],
            })

    return {
        'frame_runs': frame_runs[:30],
        'frame_freq': dict(frame_freq.most_common(20)),
        'longest_runs': frame_runs[:10],
        'regular_skeletons': regular_skeletons[:15],
        'ingredient_lines': ingredient_lines[:20],
        'total_frame_runs': len(frame_runs),
        'runs_by_length': dict(Counter(fr['length'] for fr in frame_runs).most_common()),
    }


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: SECTION-SPECIFIC NOTATION
# ═══════════════════════════════════════════════════════════════════════════

def compare_section_notation(all_data, parses):
    """
    If Voynichese is pharmaceutical shorthand, different sections should use
    different morpheme subsets:
    - Herbal: ingredient-focused (diverse roots, plant-specific suffixes)
    - Pharma: preparation-focused (specific prefixes for operations)
    - Astro: different notation entirely (coordinates? times?)
    - Bio: body-part terminology

    Compare prefix, suffix, root, and body distributions across sections.
    """
    section_morphemes = {}
    for section in ['herbal', 'pharma', 'astro', 'bio', 'text']:
        words = all_data['section_words'].get(section, [])
        if len(words) < 100:
            continue

        pfx_c = Counter()
        suf_c = Counter()
        root_c = Counter()
        onset_c = Counter()
        body_c = Counter()
        frame_c = Counter()
        n_parsed = 0

        for w in words:
            p = parses.get(w)
            if p and not p[4]:
                pfx, onset, body, suf, _ = p
                pfx_c[pfx or '∅'] += 1
                suf_c[suf or '∅'] += 1
                root_c[get_root(onset, body)] += 1
                onset_c[onset or '∅'] += 1
                body_c[body or '∅'] += 1
                frame_c[f"{pfx or '∅'}+{suf or '∅'}"] += 1
                n_parsed += 1

        if n_parsed < 50:
            continue

        section_morphemes[section] = {
            'n_words': len(words),
            'n_parsed': n_parsed,
            'prefix': dict(pfx_c.most_common(15)),
            'suffix': dict(suf_c.most_common(15)),
            'root': dict(root_c.most_common(15)),
            'onset': dict(onset_c.most_common(10)),
            'body': dict(body_c.most_common(10)),
            'frame': dict(frame_c.most_common(15)),
            'unique_roots': len(root_c),
            'unique_frames': len(frame_c),
            'root_entropy': _entropy(root_c),
            'frame_entropy': _entropy(frame_c),
            'prefix_entropy': _entropy(pfx_c),
            'suffix_entropy': _entropy(suf_c),
        }

    # Compute pairwise divergence between sections
    section_pairs = []
    sections = list(section_morphemes.keys())
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            s1, s2 = sections[i], sections[j]
            # JSD on prefix distributions
            pfx_jsd = _jsd_from_counters(
                section_morphemes[s1]['prefix'],
                section_morphemes[s2]['prefix']
            )
            # JSD on suffix distributions
            suf_jsd = _jsd_from_counters(
                section_morphemes[s1]['suffix'],
                section_morphemes[s2]['suffix']
            )
            # JSD on root onset distributions
            onset_jsd = _jsd_from_counters(
                section_morphemes[s1]['onset'],
                section_morphemes[s2]['onset']
            )
            section_pairs.append({
                's1': s1, 's2': s2,
                'pfx_jsd': pfx_jsd,
                'suf_jsd': suf_jsd,
                'onset_jsd': onset_jsd,
                'avg_jsd': (pfx_jsd + suf_jsd + onset_jsd) / 3,
            })

    # Section-exclusive morphemes
    section_exclusive = {}
    for section in sections:
        sm = section_morphemes[section]
        exclusive_roots = set()
        for root in sm['root']:
            # Is this root found mainly in this section?
            other_count = 0
            for other_sec in sections:
                if other_sec != section:
                    other_count += section_morphemes[other_sec]['root'].get(root, 0)
            if other_count == 0 and sm['root'][root] >= 5:
                exclusive_roots.add(root)
        section_exclusive[section] = sorted(exclusive_roots,
            key=lambda r: -sm['root'].get(r, 0))[:10]

    return {
        'section_morphemes': section_morphemes,
        'section_pairs': section_pairs,
        'section_exclusive': section_exclusive,
    }


def _entropy(counter):
    total = sum(counter.values())
    if total == 0:
        return 0.0
    return -sum((c/total) * math.log2(c/total) for c in counter.values() if c > 0)


def _jsd_from_counters(c1, c2):
    all_keys = set(list(c1.keys()) + list(c2.keys()))
    t1, t2 = sum(c1.values()), sum(c2.values())
    if t1 == 0 or t2 == 0:
        return 1.0
    p = {k: c1.get(k, 0)/t1 for k in all_keys}
    q = {k: c2.get(k, 0)/t2 for k in all_keys}
    m = {k: (p[k] + q[k]) / 2 for k in all_keys}
    def kl(a, b):
        return sum(a[k] * math.log2(a[k]/b[k]) for k in all_keys if a[k] > 0 and b[k] > 0)
    return math.sqrt((kl(p, m) + kl(q, m)) / 2)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: POSITIONAL COMPOSITION — Tironian/Cistercian parallels
# ═══════════════════════════════════════════════════════════════════════════

def test_positional_composition(parses, word_freq):
    """
    Tironian notes: base symbol + stroke at specific positions = modified meaning.
    Cistercian numerals: staff + 4 quadrant marks = number.
    Voynich: slot 0-2 (prefix) + slot 3-7 (root) + slot 9-11 (suffix).

    Key tests:
    1. COMPOSITIONALITY: Is the "meaning" (usage pattern) of a word predictable
       from its parts? If prefix, root, and suffix contribute independently,
       it's a compositional notation system.
    2. SLOT INDEPENDENCE: Are prefix, root, and suffix choices statistically
       independent? (Cistercian digits in different quadrants are independent.)
    3. INFORMATION DENSITY: How much information does each slot carry?
       Notation systems are designed for maximum info per symbol.
    """
    # Collect parsed words with frequencies
    parsed_words = []
    for w, freq in sorted(word_freq.items(), key=lambda x: -x[1]):
        p = parses.get(w)
        if p and not p[4]:
            parsed_words.append({
                'word': w,
                'prefix': p[0] or '∅',
                'onset': p[1] or '∅',
                'body': p[2] or '∅',
                'suffix': p[3] or '∅',
                'root': get_root(p[1], p[2]),
                'freq': freq,
            })

    if not parsed_words:
        return None

    total = sum(pw['freq'] for pw in parsed_words)

    # Slot independence test using mutual information
    # If slots are independent: I(prefix; suffix) ≈ 0
    # If they're grammar: I(prefix; suffix) > 0
    pfx_suf_joint = Counter()
    pfx_marginal = Counter()
    suf_marginal = Counter()
    pfx_root_joint = Counter()
    root_marginal = Counter()
    root_suf_joint = Counter()

    for pw in parsed_words:
        f = pw['freq']
        pfx_suf_joint[(pw['prefix'], pw['suffix'])] += f
        pfx_root_joint[(pw['prefix'], pw['root'])] += f
        root_suf_joint[(pw['root'], pw['suffix'])] += f
        pfx_marginal[pw['prefix']] += f
        suf_marginal[pw['suffix']] += f
        root_marginal[pw['root']] += f

    def mutual_info(joint, marg1, marg2, total):
        mi = 0.0
        for (a, b), f_ab in joint.items():
            p_ab = f_ab / total
            p_a = marg1[a] / total
            p_b = marg2[b] / total
            if p_ab > 0 and p_a > 0 and p_b > 0:
                mi += p_ab * math.log2(p_ab / (p_a * p_b))
        return mi

    mi_pfx_suf = mutual_info(pfx_suf_joint, pfx_marginal, suf_marginal, total)
    mi_pfx_root = mutual_info(pfx_root_joint, pfx_marginal, root_marginal, total)
    mi_root_suf = mutual_info(root_suf_joint, root_marginal, suf_marginal, total)

    # Entropy of each slot
    h_prefix = _entropy(pfx_marginal)
    h_suffix = _entropy(suf_marginal)
    h_root = _entropy(root_marginal)

    # Normalized mutual information (0 = independent, 1 = fully determined)
    nmi_pfx_suf = mi_pfx_suf / min(h_prefix, h_suffix) if min(h_prefix, h_suffix) > 0 else 0
    nmi_pfx_root = mi_pfx_root / min(h_prefix, h_root) if min(h_prefix, h_root) > 0 else 0
    nmi_root_suf = mi_root_suf / min(h_root, h_suffix) if min(h_root, h_suffix) > 0 else 0

    # Information density: bits per character for each slot zone
    # How many bits does each EVA character contribute?
    pfx_chars = sum(len(pw['prefix'].replace('∅', '')) * pw['freq'] for pw in parsed_words)
    root_chars = sum(len(pw['root'].replace('∅', '')) * pw['freq'] for pw in parsed_words)
    suf_chars = sum(len(pw['suffix'].replace('∅', '')) * pw['freq'] for pw in parsed_words)

    pfx_bits_per_char = (h_prefix * total) / pfx_chars if pfx_chars > 0 else 0
    root_bits_per_char = (h_root * total) / root_chars if root_chars > 0 else 0
    suf_bits_per_char = (h_suffix * total) / suf_chars if suf_chars > 0 else 0

    # Total word entropy vs sum of parts (test additivity)
    word_entropy = _entropy(word_freq)
    parts_entropy = h_prefix + h_root + h_suffix

    # Combinatorial coverage
    n_possible = len(pfx_marginal) * len(root_marginal) * len(suf_marginal)
    n_attested = len(set(
        (pw['prefix'], pw['root'], pw['suffix']) for pw in parsed_words
    ))
    coverage = n_attested / n_possible if n_possible > 0 else 0

    # Tironian comparison: in Tironian notes, the base (= root) carries most info
    # and the modifier (= prefix/suffix) carries less. Same for Cistercian.
    # Test: is root entropy >> prefix/suffix entropy?

    return {
        'total_parsed_tokens': total,
        'slot_entropies': {
            'prefix': h_prefix,
            'root': h_root,
            'suffix': h_suffix,
        },
        'mutual_information': {
            'I(prefix;suffix)': mi_pfx_suf,
            'I(prefix;root)': mi_pfx_root,
            'I(root;suffix)': mi_root_suf,
        },
        'normalized_MI': {
            'NMI(prefix;suffix)': nmi_pfx_suf,
            'NMI(prefix;root)': nmi_pfx_root,
            'NMI(root;suffix)': nmi_root_suf,
        },
        'info_density': {
            'prefix_bits_per_char': pfx_bits_per_char,
            'root_bits_per_char': root_bits_per_char,
            'suffix_bits_per_char': suf_bits_per_char,
        },
        'compositionality': {
            'word_entropy': word_entropy,
            'sum_of_parts_entropy': parts_entropy,
            'ratio': word_entropy / parts_entropy if parts_entropy > 0 else 0,
        },
        'combinatorial': {
            'n_distinct_prefixes': len(pfx_marginal),
            'n_distinct_roots': len(root_marginal),
            'n_distinct_suffixes': len(suf_marginal),
            'n_possible_combinations': n_possible,
            'n_attested': n_attested,
            'coverage': coverage,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: FORMULAIC SEQUENCES
# ═══════════════════════════════════════════════════════════════════════════

def detect_formulaic_sequences(all_data, parses):
    """
    Pharmaceutical texts are highly formulaic:
      "Take X, crush it, mix with Y, boil..."
    Detect multi-word sequences that repeat with substitutions.
    A "template" is a sequence of (prefix, suffix) pairs (frame)
    that appears multiple times with different roots inserted.
    """
    # Extract all frame sequences (as tuples of frames, length 2-5)
    all_frame_seqs = defaultdict(list)  # frame_template -> [(folio, roots, words)]

    for folio, section, lang, words, *_ in all_data['text_lines']:
        # Parse entire line
        parsed = []
        for w in words:
            p = parses.get(w)
            if p and not p[4]:
                parsed.append((w, p[0] or '∅', get_root(p[1], p[2]), p[3] or '∅'))
            else:
                parsed.append(None)

        # Extract n-grams of frames
        for n in range(2, 6):
            for i in range(len(parsed) - n + 1):
                chunk = parsed[i:i+n]
                if any(c is None for c in chunk):
                    continue
                frame_tuple = tuple((c[1], c[3]) for c in chunk)
                roots_tuple = tuple(c[2] for c in chunk)
                words_list = [c[0] for c in chunk]
                all_frame_seqs[frame_tuple].append({
                    'folio': folio,
                    'roots': roots_tuple,
                    'words': words_list,
                })

    # Find templates that repeat with DIFFERENT root fillings
    repeating_templates = []
    for frame_tmpl, uses in all_frame_seqs.items():
        if len(uses) < 3:
            continue
        # Count how many distinct root-tuples fill this template
        distinct_roots = len(set(u['roots'] for u in uses))
        if distinct_roots < 2:
            continue
        # This template recurs with different root content
        repeating_templates.append({
            'frame': [f"{p}+_+{s}" for p, s in frame_tmpl],
            'n_uses': len(uses),
            'n_distinct_roots': distinct_roots,
            'length': len(frame_tmpl),
            'examples': uses[:5],
        })

    repeating_templates.sort(key=lambda x: (-x['length'], -x['n_uses']))

    # Find the most "formulaic" sections
    section_formula_counts = Counter()
    for frame_tmpl, uses in all_frame_seqs.items():
        if len(uses) >= 3:
            for u in uses:
                section_formula_counts[u['folio'][:3]] += 1  # rough section by folio prefix

    return {
        'n_templates_found': len(repeating_templates),
        'templates': repeating_templates[:25],
        'total_frame_ngrams': len(all_frame_seqs),
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("═" * 90)
    print("VOYNICH — PHARMACEUTICAL SHORTHAND HYPOTHESIS")
    print("═" * 90)

    folios_dir = Path("folios")
    txt_files = sorted(folios_dir.glob("*.txt"))

    print("\n  Loading corpus...")
    all_data = extract_all_data(txt_files)

    # Build word frequency and parses
    word_freq = Counter()
    for _, _, _, words in all_data['text_lines']:
        for w in words:
            word_freq[w] += 1
    for w, _, _ in all_data['label_words']:
        word_freq[w] = word_freq.get(w, 0) + 1

    all_unique = sorted(set(word_freq.keys()))
    parses = {w: parse_word(w) for w in all_unique}

    total_words = sum(word_freq.values())
    n_parsed = sum(1 for w in all_unique if not parses[w][4])
    print(f"  {total_words:,} tokens, {len(all_unique):,} types, "
          f"{n_parsed} fully parsed ({100*n_parsed/len(all_unique):.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 1: f66r LIST
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 1: f66r LIST DECONSTRUCTION")
    print("━" * 90)
    print()

    f66r = analyze_f66r()

    print("  15-WORD LIST — Morphological decomposition:")
    print(f"  {'#':>3s}  {'Word':<12s}  {'Prefix':<8s}  {'Root':<8s}  {'Suffix':<8s}  {'Remainder':<10s}")
    print(f"  {'─'*3}  {'─'*12}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*10}")
    for i, wp in enumerate(f66r['words'], 1):
        print(f"  {i:>3d}  {wp['word']:<12s}  {wp['prefix']:<8s}  "
              f"{wp['root']:<8s}  {wp['suffix']:<8s}  {wp['remainder'] or '—':<10s}")

    print()
    print("  PREFIX distribution in list:")
    for pfx, cnt in sorted(f66r['list_prefixes'].items(), key=lambda x: -x[1]):
        print(f"    {pfx:<8s} {cnt}")
    print()
    print("  SUFFIX distribution in list:")
    for suf, cnt in sorted(f66r['list_suffixes'].items(), key=lambda x: -x[1]):
        print(f"    {suf:<8s} {cnt}")
    print()
    print("  FRAME templates (prefix+suffix combos):")
    for tmpl, cnt in sorted(f66r['templates'].items(), key=lambda x: -x[1]):
        print(f"    {tmpl:<25s} {cnt}")

    print()
    print("  SINGLE-CHARACTER COLUMN (33 readable + 3 unknown):")
    chars_str = ', '.join(c if c else '?' for c in f66r['chars'])
    print(f"    {chars_str}")
    print()
    print("  Character frequency:")
    for c, cnt in sorted(f66r['char_freq'].items(), key=lambda x: -x[1]):
        print(f"    {c:<5s} {cnt}")

    print()
    print("  CHAR → WORD initial mapping:")
    for c, words in sorted(f66r['char_to_words'].items()):
        print(f"    '{c}' → could abbreviate: {', '.join(words)}")

    # Key observation: 33 chars for 15 words → ~2.2 chars per word
    # Could be: (a) each word described by 2 chars, or
    # (b) chars are a separate ordered list that runs parallel
    print()
    print(f"  RATIO: {len([c for c in f66r['chars'] if c])} single chars / "
          f"{len(f66r['words'])} words = "
          f"{len([c for c in f66r['chars'] if c])/len(f66r['words']):.1f} chars per word")
    print("  (If 2:1, each word may be described by a 2-char code)")
    print("  (If chars are a separate parallel list, they are an independent column)")

    # Check if 15 words contain all single chars as components
    all_chars_in_words = set()
    for wp in f66r['words']:
        for c in wp['word']:
            all_chars_in_words.add(c)
    single_chars_set = set(c for c in f66r['chars'] if c and len(c) == 1)
    overlap = single_chars_set & all_chars_in_words
    print(f"\n  Single chars appearing in word list: {sorted(overlap)}")
    print(f"  Single chars NOT in word list: {sorted(single_chars_set - all_chars_in_words)}")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 2: RECIPE PATTERNS
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 2: RECIPE PATTERN DETECTION")
    print("        (Same prefix+suffix frame, different roots = same operation, different ingredients)")
    print("━" * 90)
    print()

    recipes = detect_recipe_patterns(all_data, parses)

    print(f"  Total frame-constant runs found: {recipes['total_frame_runs']}")
    print(f"  Run length distribution:")
    for length, count in sorted(recipes['runs_by_length'].items()):
        bar = "█" * min(count, 60)
        print(f"    {length}-word runs: {count:>5d}  {bar}")

    print()
    print(f"  Top 15 most common frames (prefix+suffix combos in runs):")
    print(f"  {'Frame':<25s}  {'Count':>6s}")
    print(f"  {'─'*25}  {'─'*6}")
    for frame, cnt in list(recipes['frame_freq'].items())[:15]:
        print(f"  {frame:<25s}  {cnt:>6d}")

    print()
    print("  LONGEST RECIPE-LIKE RUNS (same frame, varying roots):")
    for r in recipes['longest_runs'][:10]:
        print(f"\n  ┌─ Frame: {r['frame']}  ({r['length']} words, "
              f"folio {r['folio']}, section {r['section']})")
        print(f"  │ Roots: {' → '.join(r['roots'])}")
        print(f"  │ Words: {' '.join(r['words'])}")
        print(f"  └{'─'*70}")

    print()
    print("  INGREDIENT-LIST LINES (low frame diversity, high root diversity):")
    for il in recipes['ingredient_lines'][:10]:
        words_str = ' '.join(il['words'])
        print(f"    [{il['folio']}/{il['section']}] Frame: {il['dominant_frame'][0]} "
              f"({il['dominant_frame'][1]}×)  →  {words_str}")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 3: SECTION-SPECIFIC NOTATION
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 3: SECTION-SPECIFIC NOTATION")
    print("        (Pharmaceutical shorthand → sections should use different morpheme subsets)")
    print("━" * 90)
    print()

    section_result = compare_section_notation(all_data, parses)
    sm = section_result['section_morphemes']

    print(f"  {'Section':<12s}  {'Words':>7s}  {'Parsed':>7s}  {'Roots':>6s}  "
          f"{'Frames':>7s}  {'Root H':>7s}  {'Pfx H':>6s}  {'Suf H':>6s}")
    print(f"  {'─'*12}  {'─'*7}  {'─'*7}  {'─'*6}  {'─'*7}  {'─'*7}  {'─'*6}  {'─'*6}")
    for sec in ['herbal', 'pharma', 'astro', 'bio', 'text']:
        if sec not in sm:
            continue
        s = sm[sec]
        print(f"  {sec:<12s}  {s['n_words']:>7d}  {s['n_parsed']:>7d}  "
              f"{s['unique_roots']:>6d}  {s['unique_frames']:>7d}  "
              f"{s['root_entropy']:>7.2f}  {s['prefix_entropy']:>6.2f}  "
              f"{s['suffix_entropy']:>6.2f}")

    print()
    print("  SECTION DIVERGENCE (Jensen-Shannon Distance):")
    print(f"  {'Sections':<25s}  {'Prefix JSD':>12s}  {'Suffix JSD':>12s}  "
          f"{'Onset JSD':>12s}  {'Average':>10s}")
    print(f"  {'─'*25}  {'─'*12}  {'─'*12}  {'─'*12}  {'─'*10}")
    for sp in sorted(section_result['section_pairs'], key=lambda x: -x['avg_jsd']):
        print(f"  {sp['s1']:<11s} ↔ {sp['s2']:<11s}  {sp['pfx_jsd']:>12.4f}  "
              f"{sp['suf_jsd']:>12.4f}  {sp['onset_jsd']:>12.4f}  "
              f"{sp['avg_jsd']:>10.4f}")

    # Top prefixes per section
    print()
    print("  TOP 5 PREFIXES BY SECTION:")
    for sec in ['herbal', 'pharma', 'astro', 'bio', 'text']:
        if sec not in sm:
            continue
        top5 = list(sm[sec]['prefix'].items())[:5]
        total_pfx = sum(sm[sec]['prefix'].values())
        pfx_str = '  '.join(f"{p}({c},{100*c/total_pfx:.0f}%)" for p, c in top5)
        print(f"    {sec:<12s} {pfx_str}")

    print()
    print("  TOP 5 SUFFIXES BY SECTION:")
    for sec in ['herbal', 'pharma', 'astro', 'bio', 'text']:
        if sec not in sm:
            continue
        top5 = list(sm[sec]['suffix'].items())[:5]
        total_suf = sum(sm[sec]['suffix'].values())
        suf_str = '  '.join(f"{s}({c},{100*c/total_suf:.0f}%)" for s, c in top5)
        print(f"    {sec:<12s} {suf_str}")

    # Section-exclusive roots
    print()
    print("  SECTION-EXCLUSIVE ROOTS (appear only in one section, freq≥5):")
    for sec, roots in section_result['section_exclusive'].items():
        if roots:
            root_str = ', '.join(roots[:8])
            print(f"    {sec:<12s} [{len(roots)} exclusive]: {root_str}")

    # Determine if sections are noticeably different
    avg_jsd = sum(sp['avg_jsd'] for sp in section_result['section_pairs']) / len(section_result['section_pairs']) if section_result['section_pairs'] else 0
    print()
    if avg_jsd > 0.10:
        print(f"  ✓ SIGNIFICANT SECTION DIVERGENCE: avg JSD = {avg_jsd:.4f}")
        print(f"    → Different sections use detectably different notation")
        print(f"    → Consistent with domain-specific shorthand")
    elif avg_jsd > 0.05:
        print(f"  ~ MODERATE SECTION DIVERGENCE: avg JSD = {avg_jsd:.4f}")
    else:
        print(f"  ✗ LOW DIVERGENCE: avg JSD = {avg_jsd:.4f}")
        print(f"    → Sections use similar notation → general-purpose system")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 4: POSITIONAL COMPOSITION
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 4: POSITIONAL COMPOSITION — Tironian/Cistercian structural parallels")
    print("━" * 90)
    print()

    comp = test_positional_composition(parses, word_freq)
    if comp:
        print("  SLOT ENTROPIES (higher = more variety):")
        for slot, h in comp['slot_entropies'].items():
            bar = "█" * int(h * 5)
            print(f"    {slot:<10s} {h:.3f} bits  {bar}")

        print(f"\n  Reference: Tironian base=high, modifier=low")
        print(f"  Reference: Cistercian all quadrants ≈ equal (~3.3 bits each)")

        print(f"\n  MUTUAL INFORMATION (0 = independent, higher = dependent):")
        for pair, mi in comp['mutual_information'].items():
            print(f"    {pair:<25s} {mi:.4f} bits")
        print(f"\n  NORMALIZED MI (0 = independent, 1 = fully determined):")
        for pair, nmi in comp['normalized_MI'].items():
            print(f"    {pair:<25s} {nmi:.4f}")

        # Independence test interpretation
        max_nmi = max(comp['normalized_MI'].values())
        print()
        if max_nmi < 0.05:
            print(f"  ✓ NEAR-INDEPENDENT: Slots are nearly independent (max NMI={max_nmi:.4f})")
            print(f"    → Consistent with positional notation (Cistercian-like)")
            print(f"    → Each slot encodes a SEPARATE dimension of information")
        elif max_nmi < 0.15:
            print(f"  ~ WEAKLY DEPENDENT: Some slot correlation (max NMI={max_nmi:.4f})")
            print(f"    → Partially compositional, some grammatical dependency")
        else:
            print(f"  ✗ DEPENDENT: Strong slot correlation (max NMI={max_nmi:.4f})")
            print(f"    → More like natural language morphology than notation")

        print(f"\n  INFORMATION DENSITY (bits per EVA character):")
        for slot, bpc in comp['info_density'].items():
            print(f"    {slot:<25s} {bpc:.4f}")

        print(f"\n  COMPOSITIONALITY:")
        c = comp['compositionality']
        print(f"    Word entropy (actual):        {c['word_entropy']:.3f} bits")
        print(f"    Sum of part entropies:         {c['sum_of_parts_entropy']:.3f} bits")
        print(f"    Ratio (1.0 = fully compositional): {c['ratio']:.3f}")

        print(f"\n  COMBINATORIAL COVERAGE:")
        cb = comp['combinatorial']
        print(f"    {cb['n_distinct_prefixes']} prefixes × {cb['n_distinct_roots']} roots "
              f"× {cb['n_distinct_suffixes']} suffixes = "
              f"{cb['n_possible_combinations']:,} possible")
        print(f"    {cb['n_attested']:,} attested = {cb['coverage']:.2%} coverage")
        print()
        if cb['coverage'] < 0.05:
            print(f"  → SPARSE: only {cb['coverage']:.1%} of possible combinations attested")
            print(f"    Natural language is typically sparse. But a notation system")
            print(f"    limited to real plants/preparations would also be sparse.")
        elif cb['coverage'] > 0.20:
            print(f"  → DENSE: {cb['coverage']:.0%} coverage → highly productive combinatorics")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 5: FORMULAIC SEQUENCES
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 5: FORMULAIC SEQUENCES — Repeated multi-word templates")
    print("        (Recipe openings, preparation instructions, ingredient lists)")
    print("━" * 90)
    print()

    formulas = detect_formulaic_sequences(all_data, parses)

    print(f"  Total distinct frame n-grams: {formulas['total_frame_ngrams']:,}")
    print(f"  Recurring templates (≥3 uses, ≥2 distinct root fills): {formulas['n_templates_found']}")

    if formulas['templates']:
        print()
        # Group by length
        for target_len in [5, 4, 3, 2]:
            templates_at_len = [t for t in formulas['templates'] if t['length'] == target_len]
            if not templates_at_len:
                continue
            print(f"\n  ── {target_len}-WORD TEMPLATES ──")
            for t in templates_at_len[:6]:
                frame_str = ' | '.join(t['frame'])
                print(f"\n  ┌─ [{frame_str}]  ({t['n_uses']} uses, "
                      f"{t['n_distinct_roots']} distinct root fills)")
                for ex in t['examples'][:3]:
                    roots_str = '+'.join(ex['roots'])
                    words_str = ' '.join(ex['words'])
                    print(f"  │  {ex['folio']}: {words_str}  (roots: {roots_str})")
                print(f"  └{'─'*70}")

    # ═══════════════════════════════════════════════════════════════════
    # GRAND SUMMARY
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("═" * 90)
    print("SUMMARY — PHARMACEUTICAL SHORTHAND HYPOTHESIS")
    print("═" * 90)
    print()

    results = {}

    # f66r assessment
    print("  1. f66r WORD LIST:")
    n_templates = len(f66r['templates'])
    dominant_suf = max(f66r['list_suffixes'].items(), key=lambda x: x[1])
    print(f"     15 words using {n_templates} distinct frames, "
          f"dominant suffix: {dominant_suf[0]} ({dominant_suf[1]}×)")
    print(f"     2.1 single-chars per word → possibly a 2-character index code")
    results['f66r'] = f66r

    # Recipe patterns
    print(f"  2. RECIPE PATTERNS:")
    print(f"     {recipes['total_frame_runs']} frame-constant runs found")
    long_runs = sum(1 for r in recipes['frame_runs'] if r['length'] >= 3)
    print(f"     {long_runs} runs of 3+ words (≈ multi-ingredient recipe lines)")
    results['recipes'] = {
        'total_runs': recipes['total_frame_runs'],
        'runs_by_length': recipes['runs_by_length'],
        'top_frames': recipes['frame_freq'],
    }

    # Section notation
    print(f"  3. SECTION DIVERGENCE: avg JSD = {avg_jsd:.4f}")
    most_diff = max(section_result['section_pairs'], key=lambda x: x['avg_jsd']) if section_result['section_pairs'] else None
    if most_diff:
        print(f"     Most different: {most_diff['s1']} ↔ {most_diff['s2']} "
              f"(JSD={most_diff['avg_jsd']:.4f})")
    results['section_divergence'] = avg_jsd

    # Positional composition
    if comp:
        print(f"  4. SLOT INDEPENDENCE: max NMI = {max_nmi:.4f}")
        if max_nmi < 0.05:
            print(f"     → Prefix, root, and suffix are NEARLY INDEPENDENT")
            print(f"     → Strong evidence for notation system over natural language")
        results['composition'] = comp

    # Formulaic sequences
    print(f"  5. FORMULAIC TEMPLATES: {formulas['n_templates_found']} recurring templates")
    long_templates = sum(1 for t in formulas['templates'] if t['length'] >= 3)
    print(f"     {long_templates} templates of 3+ words → repeated procedural phrases")
    results['formulas'] = {'n_templates': formulas['n_templates_found'],
                           'n_long': long_templates}

    print()
    print("  ── VERDICT ──")
    print()
    evidence_for = 0
    evidence_against = 0

    if comp and max_nmi < 0.10:
        evidence_for += 1
        print("  [+] Slot independence → supports notation/shorthand")
    else:
        evidence_against += 1
        print("  [-] Slot dependence → supports natural language")

    if avg_jsd > 0.08:
        evidence_for += 1
        print("  [+] Section-specific notation → supports domain shorthand")
    else:
        evidence_against += 1
        print("  [-] Uniform notation across sections → supports general language")

    if recipes['total_frame_runs'] > 500:
        evidence_for += 1
        print("  [+] Many recipe-like frame runs → supports preparation notation")
    else:
        evidence_against += 1
        print("  [-] Few recipe patterns")

    if formulas['n_templates_found'] > 50:
        evidence_for += 1
        print("  [+] Recurring formulaic templates → supports procedural shorthand")
    else:
        evidence_against += 1
        print("  [-] Few formulaic templates")

    print()
    print(f"  Score: {evidence_for} for shorthand / {evidence_against} against")
    print()

    with open(result_path('shorthand_results.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Results saved to results/shorthand_results.json")
    print()
    print("═" * 90)
    print("PHARMACEUTICAL SHORTHAND ANALYSIS COMPLETE")
    print("═" * 90)


if __name__ == '__main__':
    main()
