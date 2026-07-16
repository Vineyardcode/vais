#!/usr/bin/env python3
"""
HEBREW DEEP ANALYSIS
==========================================
Second stage of the Hebrew hypothesis investigation (follows hebrew_comparison).

Tests:
  1. SHUFFLE CONTROL — Is paradigm structure real or decorative?
  2. CONSONANTAL SKELETON — Does Voynich use Hebrew-like triconsonantal roots + vowel templates?
  3. SUFFIX AGREEMENT — Do adjacent words show inflectional agreement?
  4. BOTANICAL LABEL → HEBREW PLANT NAME — Do label suffixes match Hebrew noun patterns?
  5. GEMATRIA LAYER — Do Voynich words encode Kabbalistic number values?
"""

import re
import json
import math
import random
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from common import classify_folio_v3 as classify_folio, get_root, result_path

# ═══════════════════════════════════════════════════════════════════════════
# PARSER (reused from morphology_full_survey.py)
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



def extract_words_and_lines(txt_path):
    """
    Extract words AND preserve line structure for positional analysis.
    Returns (lines_of_words, label_words, section, language, folio_name)
    where lines_of_words is a list of lists (each inner list = one text line).
    """
    lines = txt_path.read_text(encoding="utf-8").splitlines()
    header_lines = []
    text_lines = []       # list of lists of words, preserving line boundaries
    label_words = []
    folio_name = txt_path.stem

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            header_lines.append(stripped)
            continue
        if not stripped or stripped.startswith("<!"):
            continue
        if re.match(r"^<f\w+>\s", stripped):
            header_lines.append(stripped)
            continue

        m = re.match(r"<([^>]+)>\s*(.*)", stripped)
        if not m:
            continue
        locus = m.group(1)
        text = m.group(2)
        is_label = bool(re.search(r"[,@*+]L", locus))

        # Clean
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
                    label_words.append(tok)
                else:
                    line_words.append(tok)
        if line_words:
            text_lines.append(line_words)

    section, lang = classify_folio(header_lines)
    return text_lines, label_words, section, lang, folio_name


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: SHUFFLE CONTROL
# ═══════════════════════════════════════════════════════════════════════════

def build_paradigm_metrics(decompositions, word_freq):
    """Build paradigm tables and compute structural metrics from parsed decompositions."""
    root_paradigms = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    root_freq = Counter()

    for w, (pfx, onset, body, suf, rem) in decompositions.items():
        root = get_root(onset, body)
        if root and not rem:
            count = word_freq.get(w, 1)
            root_paradigms[root][pfx][suf] += count
            root_freq[root] += count

    # Compute metrics for each root
    metrics = {}
    for root in root_paradigms:
        if root_freq[root] < 30:
            continue
        table = root_paradigms[root]
        all_pfx = set(table.keys())
        all_suf = set()
        for suf_dict in table.values():
            all_suf.update(suf_dict.keys())
        n_filled = sum(1 for p in all_pfx for s in all_suf if table[p].get(s, 0) > 0)
        n_possible = len(all_pfx) * len(all_suf)

        metrics[root] = {
            'n_prefixes': len(all_pfx),
            'n_suffixes': len(all_suf),
            'n_filled': n_filled,
            'n_possible': n_possible,
            'fill_rate': n_filled / n_possible if n_possible > 0 else 0,
            'freq': root_freq[root],
        }

    return metrics


def run_shuffle_control(all_words, parses, word_freq, n_iterations=1000):
    """
    Shuffle test: randomly reassign prefixes and suffixes to words while
    preserving their marginal frequencies, then recompute paradigm metrics.
    If real Voynich structure is in top 1% → structure is real, not decorative.
    """
    # Get real metrics
    real_metrics = build_paradigm_metrics(parses, word_freq)
    real_roots = [r for r in real_metrics if real_metrics[r]['freq'] >= 100]

    if not real_roots:
        return None

    # Aggregate real statistics
    real_avg_fill = sum(real_metrics[r]['fill_rate'] for r in real_roots) / len(real_roots)
    real_avg_pfx = sum(real_metrics[r]['n_prefixes'] for r in real_roots) / len(real_roots)
    real_avg_suf = sum(real_metrics[r]['n_suffixes'] for r in real_roots) / len(real_roots)
    real_n_roots = len(real_roots)

    # Collect decomposition components
    all_pfx_pool = []
    all_onset_body_pool = []
    all_suf_pool = []
    valid_words = []

    for w in all_words:
        pfx, onset, body, suf, rem = parses[w]
        root = get_root(onset, body)
        if root and not rem:
            all_pfx_pool.append(pfx)
            all_onset_body_pool.append((onset, body))
            all_suf_pool.append(suf)
            valid_words.append(w)

    # Run shuffles
    shuffle_fill_rates = []
    shuffle_pfx_counts = []
    shuffle_suf_counts = []
    shuffle_root_counts = []

    print(f"    Running {n_iterations} shuffle iterations...", flush=True)
    for i in range(n_iterations):
        # Shuffle prefixes and suffixes independently
        shuffled_pfx = all_pfx_pool[:]
        shuffled_suf = all_suf_pool[:]
        random.shuffle(shuffled_pfx)
        random.shuffle(shuffled_suf)

        # Reconstruct decompositions with shuffled affixes but original roots
        shuffled_decomps = {}
        for idx, w in enumerate(valid_words):
            _, onset, body, _, _ = parses[w]
            shuffled_decomps[w] = (shuffled_pfx[idx], onset, body, shuffled_suf[idx], "")

        # Build word freq for shuffled corpus (same frequencies)
        sm = build_paradigm_metrics(shuffled_decomps, word_freq)
        s_roots = [r for r in sm if sm[r]['freq'] >= 100]

        if s_roots:
            avg_fill = sum(sm[r]['fill_rate'] for r in s_roots) / len(s_roots)
            avg_pfx = sum(sm[r]['n_prefixes'] for r in s_roots) / len(s_roots)
            avg_suf = sum(sm[r]['n_suffixes'] for r in s_roots) / len(s_roots)
            shuffle_fill_rates.append(avg_fill)
            shuffle_pfx_counts.append(avg_pfx)
            shuffle_suf_counts.append(avg_suf)
            shuffle_root_counts.append(len(s_roots))

        if (i + 1) % 200 == 0:
            print(f"      ...{i+1}/{n_iterations}", flush=True)

    # Compute percentiles
    def percentile_rank(real_val, shuffled_vals):
        """What fraction of shuffled values are <= real value?"""
        below = sum(1 for v in shuffled_vals if v <= real_val)
        return below / len(shuffled_vals) if shuffled_vals else 0.5

    fill_pct = percentile_rank(real_avg_fill, shuffle_fill_rates)
    pfx_pct = percentile_rank(real_avg_pfx, shuffle_pfx_counts)
    suf_pct = percentile_rank(real_avg_suf, shuffle_suf_counts)
    root_pct = percentile_rank(real_n_roots, shuffle_root_counts)

    return {
        'real': {
            'avg_fill_rate': real_avg_fill,
            'avg_n_prefixes': real_avg_pfx,
            'avg_n_suffixes': real_avg_suf,
            'n_roots_freq100': real_n_roots,
        },
        'shuffled': {
            'avg_fill_rate_mean': sum(shuffle_fill_rates) / len(shuffle_fill_rates) if shuffle_fill_rates else 0,
            'avg_fill_rate_std': (sum((v - sum(shuffle_fill_rates)/len(shuffle_fill_rates))**2 for v in shuffle_fill_rates) / len(shuffle_fill_rates))**0.5 if shuffle_fill_rates else 0,
            'avg_n_prefixes_mean': sum(shuffle_pfx_counts) / len(shuffle_pfx_counts) if shuffle_pfx_counts else 0,
            'avg_n_suffixes_mean': sum(shuffle_suf_counts) / len(shuffle_suf_counts) if shuffle_suf_counts else 0,
            'n_roots_mean': sum(shuffle_root_counts) / len(shuffle_root_counts) if shuffle_root_counts else 0,
        },
        'percentiles': {
            'fill_rate': fill_pct,
            'n_prefixes': pfx_pct,
            'n_suffixes': suf_pct,
            'n_roots': root_pct,
        },
        'n_iterations': n_iterations,
    }


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: CONSONANTAL SKELETON EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

# Voynich "consonants" = gallows + ch/sh
# Voynich "vowels" = bench letters (e), plumes (a, o), and i-series
CONSONANT_CHARS = {'k', 't', 'p', 'f', 'c', 'h', 's', 'd'}
VOWEL_CHARS = {'e', 'a', 'o', 'i'}

ONSET_CONSONANTS = {
    'k': 'K', 't': 'T', 'p': 'P', 'f': 'F',
    'ch': 'CH', 'sh': 'SH',
    'ckh': 'CKH', 'cth': 'CTH', 'cph': 'CPH', 'cfh': 'CFH',
    'kch': 'KCH', 'tch': 'TCH', 'pch': 'PCH', 'fch': 'FCH',
    'ksh': 'KSH', 'tsh': 'TSH', 'psh': 'PSH', 'fsh': 'FSH',
}

# Body patterns → vowel template label
BODY_TEMPLATES = {
    'a': 'a', 'o': 'o', 'e': 'CaCaC',
    'ed': 'CaCaC-d', 'ee': 'CaCaC-CaCaC', 'eed': 'CaCaC-CaCaC-d',
    'eee': 'CaCaC³', 'eeed': 'CaCaC³-d',
    'eo': 'CaCaC-o', 'ea': 'CaCaC-a',
    'da': 'd-a', 'do': 'd-o', 'sa': 's-a', 'so': 's-o',
    'd': 'd', 's': 's',
}


def extract_consonantal_skeleton(parses, word_freq):
    """
    Strip vowel-template from roots, keep only consonantal skeleton.
    Like Hebrew: k-t-b appears as katab, kutib, kātēb, etc. — same skeleton.
    """
    skeleton_groups = defaultdict(list)  # skeleton -> [(full_root, body_template, freq)]
    root_to_skeleton = {}

    for w, (pfx, onset, body, suf, rem) in parses.items():
        if rem:
            continue
        root = get_root(onset, body)
        if not root or not onset:
            continue

        skeleton = ONSET_CONSONANTS.get(onset, onset.upper())
        template = BODY_TEMPLATES.get(body, body)

        key = skeleton
        freq = word_freq.get(w, 1)
        skeleton_groups[key].append((root, template, freq))
        root_to_skeleton[root] = key

    # Aggregate
    skeleton_stats = {}
    for skel, entries in skeleton_groups.items():
        roots = defaultdict(int)
        templates = defaultdict(int)
        total_freq = 0
        for root, template, freq in entries:
            roots[root] += freq
            templates[template] += freq
            total_freq += freq

        skeleton_stats[skel] = {
            'total_freq': total_freq,
            'n_roots': len(roots),
            'n_templates': len(templates),
            'roots': dict(sorted(roots.items(), key=lambda x: -x[1])),
            'templates': dict(sorted(templates.items(), key=lambda x: -x[1])),
        }

    return skeleton_stats, root_to_skeleton


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: SUFFIX AGREEMENT BETWEEN ADJACENT WORDS
# ═══════════════════════════════════════════════════════════════════════════

def test_suffix_agreement(text_lines, parses, n_shuffles=500):
    """
    For each pair of adjacent words in running text, check if their
    suffixes match. Compare real match rate against shuffled baseline.
    Hebrew adjective-noun agreement: same gender/number suffix → high match rate.
    """
    # Collect adjacent suffix pairs from real text
    real_pairs = []
    for line in text_lines:
        parsed_line = []
        for w in line:
            p = parses.get(w)
            if p and not p[4]:  # fully parsed
                parsed_line.append(p)
        for i in range(len(parsed_line) - 1):
            suf1 = parsed_line[i][3]
            suf2 = parsed_line[i + 1][3]
            if suf1 or suf2:  # at least one has suffix
                real_pairs.append((suf1, suf2))

    if len(real_pairs) < 100:
        return None

    # Compute real exact-match rate
    real_exact = sum(1 for s1, s2 in real_pairs if s1 == s2) / len(real_pairs)

    # Compute real suffix-class match rate
    # Group suffixes into classes (like Hebrew gender/number)
    def suffix_class(suf):
        if not suf:
            return 'null'
        if suf.startswith('iii'):
            return 'iii-series'
        if suf.startswith('ii'):
            return 'ii-series'
        if suf.startswith('i') and len(suf) > 1:
            return 'i-series'
        if suf.endswith('y'):
            return 'y-terminal'
        if suf in ('l', 'r', 'n', 'm', 'd'):
            return f'final-{suf}'
        return 'other'

    real_class = sum(1 for s1, s2 in real_pairs
                     if suffix_class(s1) == suffix_class(s2)) / len(real_pairs)

    # Also check: do suffixes cluster at specific LINE POSITIONS?
    # (Hebrew: verb first → different suffix pattern than noun later)
    position_suffix = defaultdict(Counter)  # position -> suffix counter
    for line in text_lines:
        parsed_line = []
        for w in line:
            p = parses.get(w)
            if p and not p[4]:
                parsed_line.append(p)
        for i, (pfx, onset, body, suf, rem) in enumerate(parsed_line):
            if len(parsed_line) >= 3:
                if i == 0:
                    pos = 'first'
                elif i == len(parsed_line) - 1:
                    pos = 'last'
                else:
                    pos = 'middle'
                position_suffix[pos][suf] += 1

    # Shuffle test: scramble suffixes within each line
    shuffle_exact_rates = []
    shuffle_class_rates = []
    all_suffixes = [s for s1, s2 in real_pairs for s in (s1, s2)]

    for _ in range(n_shuffles):
        shuffled = all_suffixes[:]
        random.shuffle(shuffled)
        shuffled_pairs = [(shuffled[i*2], shuffled[i*2+1])
                          for i in range(len(real_pairs))]
        s_exact = sum(1 for s1, s2 in shuffled_pairs if s1 == s2) / len(shuffled_pairs)
        s_class = sum(1 for s1, s2 in shuffled_pairs
                      if suffix_class(s1) == suffix_class(s2)) / len(shuffled_pairs)
        shuffle_exact_rates.append(s_exact)
        shuffle_class_rates.append(s_class)

    shuffle_exact_mean = sum(shuffle_exact_rates) / len(shuffle_exact_rates)
    shuffle_class_mean = sum(shuffle_class_rates) / len(shuffle_class_rates)

    # Z-scores
    def zscore(real, shuffled):
        mean = sum(shuffled) / len(shuffled)
        std = (sum((v - mean)**2 for v in shuffled) / len(shuffled))**0.5
        return (real - mean) / std if std > 0 else 0

    z_exact = zscore(real_exact, shuffle_exact_rates)
    z_class = zscore(real_class, shuffle_class_rates)

    # Position analysis
    position_analysis = {}
    for pos in ['first', 'middle', 'last']:
        if pos in position_suffix:
            total = sum(position_suffix[pos].values())
            top5 = position_suffix[pos].most_common(5)
            position_analysis[pos] = {
                'total': total,
                'top5': [(s or '∅', c, f"{c/total:.1%}") for s, c, _ in
                         [(s, c, c/total) for s, c in top5]],
            }

    return {
        'n_pairs': len(real_pairs),
        'real_exact_match': real_exact,
        'real_class_match': real_class,
        'shuffle_exact_mean': shuffle_exact_mean,
        'shuffle_class_mean': shuffle_class_mean,
        'z_exact': z_exact,
        'z_class': z_class,
        'position_analysis': position_analysis,
    }


# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: BOTANICAL LABEL → HEBREW PLANT NAME
# ═══════════════════════════════════════════════════════════════════════════

# Hebrew noun derivation patterns relevant to plant names:
# -ah (feminine singular) → many plant names: dagan-ah, shoshan-ah
# -it (diminutive/feminine) → plant names
# -on (diminutive masculine) → common for plants: rimon (pomegranate)
# -im (masculine plural)
# -ot (feminine plural)
# me-...-et (participle form) → descriptive names
# Various mishkal (vowel template) patterns: qatl, qitl, qotl, qatal, etc.

HEBREW_PLANT_SUFFIXES = {
    'feminine_sg': ['-ah', '-et', '-it'],     # שושנה, שמרנית
    'masc_sg': ['-∅', '-on', '-an'],          # רימון, אגוז
    'fem_plural': ['-ot'],                     # plural
    'masc_plural': ['-im'],                    # plural
}

# Map Voynich suffix classes to potential Hebrew equivalents
VOYNICH_TO_HEBREW_SUFFIX = {
    # -y terminal: could map to Hebrew -i (adjective) or -ay
    'y': 'adj/-i',
    'ly': 'adj/-li?',
    'ry': 'adj/-ri?',
    'dy': '?-di',
    # -m final: Hebrew -im (masc plural) or -am
    'm': '-im/-am (plural?)',
    'im': '-im (masc plural)',
    # -n final: Hebrew -on/-an (diminutive)
    'n': '-on/-an',
    'in': '-in',
    'iin': '-iin (intensive?)',
    # -l final: Hebrew -el/-al
    'l': '-el/-al',
    'il': '-il',
    # -r final: Hebrew -er/-ar
    'r': '-er/-ar',
    'ir': '-ir',
}


def test_botanical_labels(label_words, para_words, parses):
    """
    Compare morphological profile of label words (plant names)
    against paragraph text (running prose).
    Test if labels pattern like Hebrew plant nouns.
    """
    label_decomps = {'prefix': Counter(), 'onset': Counter(),
                     'body': Counter(), 'suffix': Counter(), 'root': Counter()}
    para_decomps = {'prefix': Counter(), 'onset': Counter(),
                    'body': Counter(), 'suffix': Counter(), 'root': Counter()}

    for w in label_words:
        p = parses.get(w)
        if p and not p[4]:
            pfx, onset, body, suf, _ = p
            label_decomps['prefix'][pfx or '∅'] += 1
            label_decomps['onset'][onset or '∅'] += 1
            label_decomps['body'][body or '∅'] += 1
            label_decomps['suffix'][suf or '∅'] += 1
            label_decomps['root'][get_root(onset, body)] += 1

    for w in para_words:
        p = parses.get(w)
        if p and not p[4]:
            pfx, onset, body, suf, _ = p
            para_decomps['prefix'][pfx or '∅'] += 1
            para_decomps['onset'][onset or '∅'] += 1
            para_decomps['body'][body or '∅'] += 1
            para_decomps['suffix'][suf or '∅'] += 1
            para_decomps['root'][get_root(onset, body)] += 1

    # Hebrew plant name predictions:
    # 1) Labels should have MORE ∅-prefix than text (Hebrew nouns often unprefixed)
    # 2) Labels should prefer certain suffix classes (like -ah/-it/-on equivalents)
    # 3) Labels should have FEWER distinct prefix types (nouns don't conjugate like verbs)

    label_total = sum(label_decomps['prefix'].values())
    para_total = sum(para_decomps['prefix'].values())

    label_null_pfx = label_decomps['prefix'].get('∅', 0) / label_total if label_total > 0 else 0
    para_null_pfx = para_decomps['prefix'].get('∅', 0) / para_total if para_total > 0 else 0

    # Suffix profile comparison
    label_suf_total = sum(label_decomps['suffix'].values())
    para_suf_total = sum(para_decomps['suffix'].values())

    suffix_comparison = []
    all_sufs = set(label_decomps['suffix'].keys()) | set(para_decomps['suffix'].keys())
    for suf in sorted(all_sufs, key=lambda s: -(label_decomps['suffix'].get(s, 0) + para_decomps['suffix'].get(s, 0))):
        l_frac = label_decomps['suffix'].get(suf, 0) / label_suf_total if label_suf_total > 0 else 0
        p_frac = para_decomps['suffix'].get(suf, 0) / para_suf_total if para_suf_total > 0 else 0
        ratio = l_frac / p_frac if p_frac > 0 else float('inf')
        hebrew_equiv = VOYNICH_TO_HEBREW_SUFFIX.get(suf, '?')
        suffix_comparison.append({
            'suffix': suf,
            'label_frac': l_frac,
            'para_frac': p_frac,
            'ratio': ratio,
            'hebrew_equiv': hebrew_equiv,
        })

    # Body pattern comparison (Hebrew mishkal)
    body_comparison = []
    all_bodies = set(label_decomps['body'].keys()) | set(para_decomps['body'].keys())
    label_body_total = sum(label_decomps['body'].values())
    para_body_total = sum(para_decomps['body'].values())
    for body in sorted(all_bodies, key=lambda b: -(label_decomps['body'].get(b, 0) + para_decomps['body'].get(b, 0))):
        l_frac = label_decomps['body'].get(body, 0) / label_body_total if label_body_total > 0 else 0
        p_frac = para_decomps['body'].get(body, 0) / para_body_total if para_body_total > 0 else 0
        body_comparison.append({
            'body': body,
            'label_frac': l_frac,
            'para_frac': p_frac,
            'template': BODY_TEMPLATES.get(body, body),
        })

    return {
        'label_null_prefix_rate': label_null_pfx,
        'para_null_prefix_rate': para_null_pfx,
        'label_total': label_total,
        'para_total': para_total,
        'suffix_comparison': suffix_comparison[:20],
        'body_comparison': body_comparison[:15],
        'label_unique_prefixes': len(label_decomps['prefix']),
        'para_unique_prefixes': len(para_decomps['prefix']),
        'label_prefix_dist': dict(label_decomps['prefix'].most_common(10)),
        'para_prefix_dist': dict(para_decomps['prefix'].most_common(10)),
    }


# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: GEMATRIA LAYER
# ═══════════════════════════════════════════════════════════════════════════

# Hypothetical gematria mapping: each Voynich slot position ≈ a place value
# Approach 1: Assign values based on slot position (units, tens, hundreds)
# Approach 2: Frequency-rank mapping to Hebrew letter values (alef=1...tav=400)
# Approach 3: Test if word-value sums per line show patterns

# Hebrew gematria values for reference:
HEBREW_GEMATRIA = {
    'alef': 1, 'bet': 2, 'gimel': 3, 'dalet': 4, 'he': 5,
    'vav': 6, 'zayin': 7, 'chet': 8, 'tet': 9, 'yod': 10,
    'kaf': 20, 'lamed': 30, 'mem': 40, 'nun': 50, 'samekh': 60,
    'ayin': 70, 'pe': 80, 'tsade': 90, 'qof': 100, 'resh': 200,
    'shin': 300, 'tav': 400,
}

# Kabbalistic significant numbers
KABBALISTIC_NUMBERS = {
    26: "YHWH (יהוה)",
    72: "Shem HaMephorash (72 names of God)",
    10: "Sefirot",
    22: "Hebrew letters",
    32: "Paths of Wisdom (10 sefirot + 22 letters)",
    42: "42-letter Name of God",
    45: "Adam (אדם) in full gematria",
    52: "YHWH in milui",
    86: "Elohim (אלהים)",
    91: "YHWH + Adonai combined",
    137: "Kabbalah (קבלה)",
    314: "Shaddai (שדי)",
    358: "Mashiach (משיח) = Nachash (נחש)",
}

# EVA character frequency ranking → position in gematria mapping
# We'll use a slot-based system: each character at each position gets a value
# based on its rank-frequency at that slot position

def compute_gematria_values(all_words, parses, word_freq):
    """
    Assign gematria values to Voynich characters using frequency-rank mapping.
    Then test whether word values cluster around kabbalistic numbers.
    """
    # Approach: assign values to prefix, onset, body, suffix components
    # based on frequency ranking (most frequent = lowest value, like alef=1)

    # Count component frequencies
    pfx_freq = Counter()
    onset_freq = Counter()
    body_freq = Counter()
    suf_freq = Counter()

    for w in all_words:
        p = parses.get(w)
        if p and not p[4]:
            pfx, onset, body, suf, _ = p
            count = word_freq.get(w, 1)
            if pfx: pfx_freq[pfx] += count
            if onset: onset_freq[onset] += count
            if body: body_freq[body] += count
            if suf: suf_freq[suf] += count

    # Assign values by rank (1-indexed)
    def rank_values(counter, scale=1):
        ranked = sorted(counter.keys(), key=lambda x: -counter[x])
        return {item: (i + 1) * scale for i, item in enumerate(ranked)}

    pfx_val = rank_values(pfx_freq, 100)    # prefixes = hundreds
    onset_val = rank_values(onset_freq, 10)   # onsets = tens
    body_val = rank_values(body_freq, 1)      # bodies = units
    suf_val = rank_values(suf_freq, 1)        # suffixes = additional units

    # Compute word values
    word_values = []
    for w in all_words:
        p = parses.get(w)
        if p and not p[4]:
            pfx, onset, body, suf, _ = p
            val = 0
            if pfx: val += pfx_val.get(pfx, 0)
            if onset: val += onset_val.get(onset, 0)
            if body: val += body_val.get(body, 0)
            if suf: val += suf_val.get(suf, 0)
            word_values.append((w, val))

    if not word_values:
        return None

    # Test 1: Do individual word values cluster around kabbalistic numbers?
    value_counter = Counter(v for _, v in word_values)
    value_list = [v for _, v in word_values]

    # Check proximity to kabbalistic numbers
    kab_hits = {}
    for kab_num, kab_name in KABBALISTIC_NUMBERS.items():
        # Count words with value within ±2 of this number
        near = sum(1 for v in value_list if abs(v - kab_num) <= 2)
        # Expected by chance: assume uniform distribution over range
        val_range = max(value_list) - min(value_list) + 1
        expected = len(value_list) * 5 / val_range  # ±2 = 5 values out of range
        ratio = near / expected if expected > 0 else 0
        kab_hits[kab_num] = {
            'name': kab_name,
            'observed': near,
            'expected': round(expected, 1),
            'ratio': ratio,
        }

    # Test 2: Line-sum analysis — do line sums show patterns?
    # (We'll compute this in main using the text_lines structure)

    # Test 3: Simple character-level gematria
    # Assign each EVA character a value by frequency rank
    char_freq = Counter()
    for w in all_words:
        for c in w:
            char_freq[c] += word_freq.get(w, 1)

    char_val = rank_values(char_freq)

    # Compute simple character-sum values
    char_word_values = []
    for w in all_words:
        val = sum(char_val.get(c, 0) for c in w)
        char_word_values.append((w, val))

    char_value_list = [v for _, v in char_word_values]

    # Check character-level kabbalistic hits
    char_kab_hits = {}
    if char_value_list:
        char_val_range = max(char_value_list) - min(char_value_list) + 1
        for kab_num, kab_name in KABBALISTIC_NUMBERS.items():
            near = sum(1 for v in char_value_list if abs(v - kab_num) <= 2)
            expected = len(char_value_list) * 5 / char_val_range if char_val_range > 0 else 0
            ratio = near / expected if expected > 0 else 0
            char_kab_hits[kab_num] = {
                'name': kab_name,
                'observed': near,
                'expected': round(expected, 1),
                'ratio': ratio,
            }

    return {
        'morpheme_gematria': {
            'prefix_values': dict(sorted(pfx_val.items(), key=lambda x: x[1])[:10]),
            'onset_values': dict(sorted(onset_val.items(), key=lambda x: x[1])[:10]),
            'body_values': dict(sorted(body_val.items(), key=lambda x: x[1])[:10]),
            'suffix_values': dict(sorted(suf_val.items(), key=lambda x: x[1])[:10]),
            'kabbalistic_hits': kab_hits,
            'value_range': (min(value_list), max(value_list)),
            'mean_value': sum(value_list) / len(value_list),
        },
        'character_gematria': {
            'char_values': dict(sorted(char_val.items(), key=lambda x: x[1])),
            'kabbalistic_hits': char_kab_hits,
            'value_range': (min(char_value_list), max(char_value_list)) if char_value_list else (0, 0),
            'mean_value': sum(char_value_list) / len(char_value_list) if char_value_list else 0,
        },
    }


def test_line_sum_patterns(text_lines, parses, word_freq):
    """Test whether line-level word-value sums show isotopic patterns."""
    # Character-level values by frequency rank
    char_freq = Counter()
    for line in text_lines:
        for w in line:
            for c in w:
                char_freq[c] += 1
    ranked = sorted(char_freq.keys(), key=lambda x: -char_freq[x])
    char_val = {c: i + 1 for i, c in enumerate(ranked)}

    line_sums = []
    for line in text_lines:
        if len(line) < 2:
            continue
        line_val = sum(sum(char_val.get(c, 0) for c in w) for w in line)
        line_sums.append(line_val)

    if len(line_sums) < 50:
        return None

    mean_sum = sum(line_sums) / len(line_sums)
    std_sum = (sum((v - mean_sum)**2 for v in line_sums) / len(line_sums))**0.5

    # Test: is the variance of line sums LOWER than expected?
    # If there's a gematria constraint, line sums should cluster
    # Compare to shuffled text (shuffle words across lines)
    all_line_words = [w for line in text_lines for w in line if len(line) >= 2]
    line_lengths = [len(line) for line in text_lines if len(line) >= 2]

    shuffle_stds = []
    for _ in range(200):
        shuffled = all_line_words[:]
        random.shuffle(shuffled)
        idx = 0
        s_sums = []
        for length in line_lengths:
            s_line = shuffled[idx:idx + length]
            idx += length
            s_val = sum(sum(char_val.get(c, 0) for c in w) for w in s_line)
            s_sums.append(s_val)
        if s_sums:
            s_mean = sum(s_sums) / len(s_sums)
            s_std = (sum((v - s_mean)**2 for v in s_sums) / len(s_sums))**0.5
            shuffle_stds.append(s_std)

    shuffle_std_mean = sum(shuffle_stds) / len(shuffle_stds) if shuffle_stds else 0

    # Modular analysis: do line sums cluster modulo significant numbers?
    mod_analysis = {}
    for mod_val in [10, 22, 26, 42, 72]:
        residues = [s % mod_val for s in line_sums]
        residue_counts = Counter(residues)
        # Chi-square test: are residues uniformly distributed?
        expected = len(line_sums) / mod_val
        chi2 = sum((c - expected)**2 / expected for c in residue_counts.values()
                    if expected > 0)
        # Top residues
        top_residues = residue_counts.most_common(3)
        mod_analysis[mod_val] = {
            'chi2': chi2,
            'df': mod_val - 1,
            'top_residues': top_residues,
            'expected_uniform': round(expected, 1),
        }

    return {
        'n_lines': len(line_sums),
        'mean_line_sum': mean_sum,
        'std_line_sum': std_sum,
        'shuffle_std_mean': shuffle_std_mean,
        'variance_ratio': std_sum / shuffle_std_mean if shuffle_std_mean > 0 else 0,
        'modular_analysis': mod_analysis,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    random.seed(42)

    print("═" * 90)
    print("VOYNICH MANUSCRIPT — HEBREW DEEP ANALYSIS")
    print("═" * 90)

    folios_dir = Path("folios")
    txt_files = sorted(folios_dir.glob("*.txt"))

    # ── Extract all data ────────────────────────────────────────────────
    print("\n  Loading and parsing corpus...")
    all_text_lines = []   # list of lists (preserving line structure)
    all_para_words = []
    all_label_words = []
    word_freq = Counter()

    for txt_file in txt_files:
        text_lines, labels, section, lang, folio = extract_words_and_lines(txt_file)
        all_text_lines.extend(text_lines)
        for line in text_lines:
            for w in line:
                all_para_words.append(w)
                word_freq[w] += 1
        all_label_words.extend(labels)

    for w in all_label_words:
        word_freq[w] = word_freq.get(w, 0) + 1

    all_unique = sorted(set(all_para_words + all_label_words))
    parses = {}
    for w in all_unique:
        parses[w] = parse_word(w)

    fully_parsed = sum(1 for w in all_unique if not parses[w][4])
    print(f"  Corpus: {len(all_para_words):,} paragraph tokens, "
          f"{len(all_label_words):,} label tokens")
    print(f"  {len(all_unique):,} unique types, {fully_parsed} fully parsed "
          f"({100*fully_parsed/len(all_unique):.1f}%)")
    print(f"  {len(all_text_lines):,} text lines preserved")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 1: SHUFFLE CONTROL
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 1: SHUFFLE CONTROL — Is paradigm structure real or random?")
    print("━" * 90)
    print()
    print("  If paradigm regularity is higher than 99% of random reshuffles,")
    print("  we reject the 'meaningless verbose code' hypothesis.")
    print()

    shuffle_result = run_shuffle_control(all_para_words, parses, word_freq, n_iterations=1000)

    if shuffle_result:
        r = shuffle_result
        print(f"  {'Metric':<30s}  {'REAL':>10s}  {'Shuffled µ':>12s}  {'Percentile':>12s}")
        print(f"  {'─'*30}  {'─'*10}  {'─'*12}  {'─'*12}")
        print(f"  {'Avg grid fill rate':<30s}  {r['real']['avg_fill_rate']:>10.4f}  "
              f"{r['shuffled']['avg_fill_rate_mean']:>12.4f}  {r['percentiles']['fill_rate']:>11.1%}")
        print(f"  {'Avg # prefixes per root':<30s}  {r['real']['avg_n_prefixes']:>10.1f}  "
              f"{r['shuffled']['avg_n_prefixes_mean']:>12.1f}  {r['percentiles']['n_prefixes']:>11.1%}")
        print(f"  {'Avg # suffixes per root':<30s}  {r['real']['avg_n_suffixes']:>10.1f}  "
              f"{r['shuffled']['avg_n_suffixes_mean']:>12.1f}  {r['percentiles']['n_suffixes']:>11.1%}")
        print(f"  {'# roots with freq≥100':<30s}  {r['real']['n_roots_freq100']:>10d}  "
              f"{r['shuffled']['n_roots_mean']:>12.1f}  {r['percentiles']['n_roots']:>11.1%}")

        print()
        # The KEY test: fill rate should be LOWER in real data than shuffled
        # because real grammar creates SPARSE paradigm tables (not every prefix×suffix combo occurs)
        # while random assignment fills the grid more completely
        if r['percentiles']['fill_rate'] < 0.05:
            print("  ✓ REAL GRAMMAR SIGNAL: Fill rate is LOWER than 95% of shuffles")
            print("    → Real Voynich has sparser, more structured paradigm tables")
            print("    → Inconsistent with random/decorative morphology")
        elif r['percentiles']['fill_rate'] > 0.95:
            print("  ✗ ANTI-SIGNAL: Fill rate is HIGHER than shuffled")
            print("    → Paradigm tables are MORE filled than expected → possible verbose code")
        else:
            print(f"  ~ INCONCLUSIVE: Fill rate at {r['percentiles']['fill_rate']:.0%} percentile")

        if r['percentiles']['n_roots'] > 0.95:
            print("  ✓ ROOT CONCENTRATION: More distinct roots than shuffled")
            print("    → Morphemes are not randomly assigned to roots")
        elif r['percentiles']['n_roots'] < 0.05:
            print("  → FEWER roots than shuffled (morphemes spread across more roots)")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 2: CONSONANTAL SKELETON
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 2: CONSONANTAL SKELETON EXTRACTION")
    print("        (Hebrew-style: strip vowels, keep only consonantal root)")
    print("━" * 90)
    print()

    skeleton_stats, root_to_skeleton = extract_consonantal_skeleton(parses, word_freq)

    # Sort by frequency
    sorted_skeletons = sorted(skeleton_stats.items(), key=lambda x: -x[1]['total_freq'])

    print(f"  Found {len(skeleton_stats)} consonantal skeletons from {len(root_to_skeleton)} full roots")
    print(f"  Hebrew has ~1,500 productive roots; a medical/herbal text uses ~300-500")
    print()
    print(f"  {'Skeleton':<10s}  {'Freq':>6s}  {'# Roots':>8s}  {'# Templates':>12s}  Roots (with vowel templates)")
    print(f"  {'─'*10}  {'─'*6}  {'─'*8}  {'─'*12}  {'─'*50}")

    for skel, stats in sorted_skeletons[:20]:
        roots_str = ', '.join(f"{r}({f})" for r, f in list(stats['roots'].items())[:6])
        templates_str = ', '.join(stats['templates'].keys())
        print(f"  {skel:<10s}  {stats['total_freq']:>6d}  {stats['n_roots']:>8d}  "
              f"{stats['n_templates']:>12d}  {roots_str}")

    print()
    # Hebrew prediction: each consonantal skeleton should appear with MULTIPLE
    # vowel templates (like Hebrew k-t-b → katab, koteb, ketubah, etc.)
    multi_template = sum(1 for s in skeleton_stats.values() if s['n_templates'] >= 3)
    two_template = sum(1 for s in skeleton_stats.values() if s['n_templates'] == 2)
    single_template = sum(1 for s in skeleton_stats.values() if s['n_templates'] == 1)

    print(f"  Skeletons with ≥3 vowel templates: {multi_template} "
          f"({100*multi_template/len(skeleton_stats):.0f}%)")
    print(f"  Skeletons with 2 vowel templates:  {two_template} "
          f"({100*two_template/len(skeleton_stats):.0f}%)")
    print(f"  Skeletons with 1 vowel template:   {single_template} "
          f"({100*single_template/len(skeleton_stats):.0f}%)")
    print()

    if multi_template / len(skeleton_stats) > 0.3:
        print(f"  ✓ STRONG MISHKAL PATTERN: {multi_template}/{len(skeleton_stats)} skeletons "
              f"show multiple vowel templates")
        print(f"    → Consistent with Hebrew consonantal root + vowel template system")
    elif multi_template / len(skeleton_stats) > 0.15:
        print(f"  ~ PARTIAL MISHKAL: some skeletons show vowel variation")
    else:
        print(f"  ✗ WEAK MISHKAL: most skeletons have only one vowel pattern")

    # Show the top multi-template skeletons in detail
    print()
    print("  Detailed vowel template analysis for top skeletons:")
    for skel, stats in sorted_skeletons[:8]:
        if stats['n_templates'] >= 2:
            print(f"\n  ┌─ {skel}: {stats['n_templates']} templates, total freq {stats['total_freq']}")
            for tmpl, freq in sorted(stats['templates'].items(), key=lambda x: -x[1]):
                pct = freq / stats['total_freq']
                bar = "█" * int(pct * 30)
                print(f"  │  {tmpl:<15s} {freq:>5d} ({pct:>5.1%}) {bar}")
            print(f"  └{'─'*60}")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 3: SUFFIX AGREEMENT
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 3: SUFFIX AGREEMENT — Do adjacent words show inflectional agreement?")
    print("        (Hebrew: noun-adjective pairs share gender/number suffixes)")
    print("━" * 90)
    print()

    agreement_result = test_suffix_agreement(all_text_lines, parses)

    if agreement_result:
        a = agreement_result
        print(f"  Adjacent word pairs analyzed: {a['n_pairs']:,}")
        print()
        print(f"  {'Match type':<25s}  {'Real':>8s}  {'Shuffled µ':>12s}  {'Z-score':>10s}")
        print(f"  {'─'*25}  {'─'*8}  {'─'*12}  {'─'*10}")
        print(f"  {'Exact suffix match':<25s}  {a['real_exact_match']:>7.1%}  "
              f"{a['shuffle_exact_mean']:>11.1%}  {a['z_exact']:>10.2f}")
        print(f"  {'Suffix class match':<25s}  {a['real_class_match']:>7.1%}  "
              f"{a['shuffle_class_mean']:>11.1%}  {a['z_class']:>10.2f}")

        print()
        if a['z_exact'] > 3.0:
            print(f"  ✓ STRONG AGREEMENT: Z={a['z_exact']:.1f} — adjacent words share suffixes")
            print(f"    far more than chance. Consistent with noun-adjective agreement!")
        elif a['z_exact'] > 2.0:
            print(f"  ~ MODERATE AGREEMENT: Z={a['z_exact']:.1f} — some suffix correlation")
        elif a['z_exact'] > 0:
            print(f"  → WEAK AGREEMENT: Z={a['z_exact']:.1f} — slight above-chance correlation")
        else:
            print(f"  ✗ NO AGREEMENT: Z={a['z_exact']:.1f} — no inflectional agreement detected")

        # Positional analysis
        if a['position_analysis']:
            print()
            print("  Suffix distribution by position within line (Hebrew: verb-first → specific suffix):")
            for pos in ['first', 'middle', 'last']:
                if pos in a['position_analysis']:
                    pa = a['position_analysis'][pos]
                    top_str = '  '.join(f"{s}({c},{pct})" for s, c, pct in pa['top5'])
                    print(f"    {pos:>7s} (n={pa['total']:>5d}): {top_str}")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 4: BOTANICAL LABELS
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 4: BOTANICAL LABELS — Do plant names match Hebrew noun patterns?")
    print("━" * 90)
    print()

    botanical_result = test_botanical_labels(all_label_words, all_para_words, parses)

    if botanical_result:
        b = botanical_result
        print(f"  Labels parsed: {b['label_total']}, Paragraph parsed: {b['para_total']}")
        print()
        print(f"  ∅-prefix rate: Labels={b['label_null_prefix_rate']:.1%} vs "
              f"Para={b['para_null_prefix_rate']:.1%}")
        print(f"  Unique prefix types: Labels={b['label_unique_prefixes']} vs "
              f"Para={b['para_unique_prefixes']}")
        print()

        if b['label_null_prefix_rate'] > b['para_null_prefix_rate']:
            print("  ✓ Labels have MORE unprefixed forms than text")
            print("    → Consistent with Hebrew nouns (unprefixed) vs verbs (prefixed)")
        else:
            print("  ✗ Labels have FEWER unprefixed forms (unexpected for noun-labels)")

        print()
        print("  Suffix profile comparison (Labels vs Paragraph text):")
        print(f"  {'Suffix':<10s}  {'Label%':>8s}  {'Para%':>8s}  {'Ratio':>8s}  Hebrew equivalent")
        print(f"  {'─'*10}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*25}")
        for sc in b['suffix_comparison'][:15]:
            ratio_str = f"{sc['ratio']:.1f}×" if sc['ratio'] < 100 else "∞"
            print(f"  {sc['suffix']:<10s}  {sc['label_frac']:>7.1%}  {sc['para_frac']:>7.1%}  "
                  f"{ratio_str:>8s}  {sc['hebrew_equiv']}")

        print()
        print("  Vowel template (mishkal) comparison:")
        print(f"  {'Body':<10s}  {'Label%':>8s}  {'Para%':>8s}  Template")
        print(f"  {'─'*10}  {'─'*8}  {'─'*8}  {'─'*20}")
        for bc in b['body_comparison'][:10]:
            print(f"  {bc['body']:<10s}  {bc['label_frac']:>7.1%}  {bc['para_frac']:>7.1%}  "
                  f"{bc['template']}")

        # Label prefix distribution
        print()
        print("  Label prefix distribution:")
        for pfx, cnt in sorted(b['label_prefix_dist'].items(), key=lambda x: -x[1]):
            pct = cnt / b['label_total']
            bar = "█" * int(pct * 40)
            print(f"    {pfx or '∅':<8s} {cnt:>4d} ({pct:>5.1%}) {bar}")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 5: GEMATRIA
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("━" * 90)
    print("TEST 5: GEMATRIA LAYER — Do word values cluster around Kabbalistic numbers?")
    print("━" * 90)
    print()

    gematria_result = compute_gematria_values(all_para_words, parses, word_freq)
    line_sum_result = test_line_sum_patterns(all_text_lines, parses, word_freq)

    if gematria_result:
        g = gematria_result

        # Character-level gematria values
        print("  Character → value mapping (by frequency rank):")
        cv = g['character_gematria']['char_values']
        char_str = '  '.join(f"{c}={v}" for c, v in sorted(cv.items(), key=lambda x: x[1]))
        print(f"    {char_str}")
        print(f"    Value range: {g['character_gematria']['value_range']}")
        print(f"    Mean word value: {g['character_gematria']['mean_value']:.1f}")
        print()

        # Morpheme-level gematria
        print("  Morpheme-level value mapping:")
        print(f"    Top prefixes:  " + ', '.join(f"{k}={v}" for k, v in
              sorted(g['morpheme_gematria']['prefix_values'].items(), key=lambda x: x[1])))
        print(f"    Top onsets:    " + ', '.join(f"{k}={v}" for k, v in
              sorted(g['morpheme_gematria']['onset_values'].items(), key=lambda x: x[1])))
        print(f"    Top bodies:    " + ', '.join(f"{k}={v}" for k, v in
              sorted(g['morpheme_gematria']['body_values'].items(), key=lambda x: x[1])))
        print(f"    Top suffixes:  " + ', '.join(f"{k}={v}" for k, v in
              sorted(g['morpheme_gematria']['suffix_values'].items(), key=lambda x: x[1])))
        print()

        # Kabbalistic number hits (character-level)
        print("  Character-level: Kabbalistic number proximity (observed vs expected):")
        print(f"  {'Number':>8s}  {'Name':<35s}  {'Observed':>10s}  {'Expected':>10s}  {'Ratio':>8s}")
        print(f"  {'─'*8}  {'─'*35}  {'─'*10}  {'─'*10}  {'─'*8}")
        char_hits = g['character_gematria']['kabbalistic_hits']
        for num in sorted(char_hits.keys()):
            h = char_hits[num]
            print(f"  {num:>8d}  {h['name']:<35s}  {h['observed']:>10d}  "
                  f"{h['expected']:>10.1f}  {h['ratio']:>7.1f}×")

        significant_char = [num for num, h in char_hits.items() if h['ratio'] > 2.0]
        print()
        if significant_char:
            print(f"  ⚡ Character-level clustering detected near: "
                  f"{', '.join(str(n) for n in significant_char)}")
        else:
            print("  → No significant character-level clustering around Kabbalistic numbers")

        # Morpheme-level hits
        print()
        print("  Morpheme-level: Kabbalistic number proximity:")
        print(f"  {'Number':>8s}  {'Name':<35s}  {'Observed':>10s}  {'Expected':>10s}  {'Ratio':>8s}")
        print(f"  {'─'*8}  {'─'*35}  {'─'*10}  {'─'*10}  {'─'*8}")
        morph_hits = g['morpheme_gematria']['kabbalistic_hits']
        for num in sorted(morph_hits.keys()):
            h = morph_hits[num]
            print(f"  {num:>8d}  {h['name']:<35s}  {h['observed']:>10d}  "
                  f"{h['expected']:>10.1f}  {h['ratio']:>7.1f}×")

        significant_morph = [num for num, h in morph_hits.items() if h['ratio'] > 2.0]
        print()
        if significant_morph:
            print(f"  ⚡ Morpheme-level clustering detected near: "
                  f"{', '.join(str(n) for n in significant_morph)}")
        else:
            print("  → No significant morpheme-level clustering around Kabbalistic numbers")

    if line_sum_result:
        ls = line_sum_result
        print()
        print("  LINE-SUM ANALYSIS:")
        print(f"    Lines analyzed: {ls['n_lines']}")
        print(f"    Mean line sum: {ls['mean_line_sum']:.1f}")
        print(f"    Real std dev: {ls['std_line_sum']:.1f}")
        print(f"    Shuffled std dev: {ls['shuffle_std_mean']:.1f}")
        print(f"    Variance ratio (real/shuffled): {ls['variance_ratio']:.3f}")
        print()
        if ls['variance_ratio'] < 0.9:
            print("    ✓ Line sums are MORE REGULAR than shuffled → possible isopsephy constraint!")
        elif ls['variance_ratio'] > 1.1:
            print("    → Line sums are MORE variable than shuffled (no sum constraint)")
        else:
            print("    ~ Line sums have normal variance (no clear constraint)")

        print()
        print("  MODULAR ANALYSIS (do line sums cluster modulo significant numbers?):")
        print(f"  {'Modulus':>8s}  {'χ²':>8s}  {'df':>4s}  Significance  Top residues")
        print(f"  {'─'*8}  {'─'*8}  {'─'*4}  {'─'*12}  {'─'*30}")
        for mod_val in sorted(ls['modular_analysis'].keys()):
            ma = ls['modular_analysis'][mod_val]
            # Rough significance: chi2 > 2*df is suggestive
            sig = "SIGNIFICANT" if ma['chi2'] > 3 * ma['df'] else \
                  "suggestive" if ma['chi2'] > 2 * ma['df'] else "none"
            top_str = ', '.join(f"{r}({c})" for r, c in ma['top_residues'])
            print(f"  {mod_val:>8d}  {ma['chi2']:>8.1f}  {ma['df']:>4d}  {sig:<12s}  {top_str}")

    # ═══════════════════════════════════════════════════════════════════
    # GRAND SUMMARY
    # ═══════════════════════════════════════════════════════════════════
    print()
    print("═" * 90)
    print("GRAND SUMMARY — HEBREW DEEP ANALYSIS")
    print("═" * 90)
    print()

    results = {}

    if shuffle_result:
        fill_p = shuffle_result['percentiles']['fill_rate']
        real_grammar = fill_p < 0.05 or fill_p > 0.95
        print(f"  1. SHUFFLE CONTROL:     {'REAL STRUCTURE' if real_grammar else 'INCONCLUSIVE':>20s}"
              f"  (fill at {fill_p:.0%} percentile)")
        results['shuffle'] = shuffle_result

    if skeleton_stats:
        multi_pct = multi_template / len(skeleton_stats)
        print(f"  2. CONSONANTAL ROOTS:   {f'{multi_template} multi-template ({multi_pct:.0%})':>20s}"
              f"  (Hebrew predicts >30%)")
        results['skeletons'] = {skel: {k: v for k, v in stats.items() if k != 'roots'}
                                for skel, stats in sorted_skeletons[:30]}

    if agreement_result:
        z = agreement_result['z_exact']
        label = "STRONG" if z > 3 else "MODERATE" if z > 2 else "WEAK" if z > 0 else "NONE"
        print(f"  3. SUFFIX AGREEMENT:    {label:>20s}  (Z={z:.1f})")
        results['agreement'] = agreement_result

    if botanical_result:
        null_diff = botanical_result['label_null_prefix_rate'] - botanical_result['para_null_prefix_rate']
        label = "NOUN-LIKE" if null_diff > 0.05 else "SIMILAR" if abs(null_diff) < 0.05 else "VERB-LIKE"
        print(f"  4. BOTANICAL LABELS:    {label:>20s}  "
              f"(∅-pfx diff: {null_diff:+.1%})")
        results['botanical'] = botanical_result

    if gematria_result:
        any_sig = bool(significant_char) or bool(significant_morph)
        print(f"  5. GEMATRIA LAYER:      {'CLUSTERS FOUND' if any_sig else 'NO SIGNAL':>20s}")
        results['gematria'] = {
            'character_range': gematria_result['character_gematria']['value_range'],
            'significant_char_numbers': significant_char,
            'significant_morph_numbers': significant_morph,
        }

    if line_sum_result:
        vr = line_sum_result['variance_ratio']
        label = "CONSTRAINED" if vr < 0.9 else "NORMAL" if vr < 1.1 else "FREE"
        print(f"  6. LINE SUM PATTERN:    {label:>20s}  (variance ratio: {vr:.3f})")
        results['line_sums'] = line_sum_result

    # Save
    with open(result_path('hebrew_deep_results.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print()
    print(f"  Results saved to results/hebrew_deep_results.json")
    print()
    print("═" * 90)
    print("DEEP ANALYSIS COMPLETE")
    print("═" * 90)


if __name__ == '__main__':
    main()
