#!/usr/bin/env python3
"""
Phase 105 — Re-testing Cappelli Abbreviation Marks vs VMS Suffixes

═══════════════════════════════════════════════════════════════════════

MOTIVATION:
  Phase 73 tested whether abbreviated Latin matches VMS's global
  fingerprint (h_char, Zipf, Heaps, etc.) and found it CANNOT explain
  h_char = 0.64.  That result stands.

  But Phase 104 discovered that VMS endings have three extreme anomalies
  vs all 12 NL languages:
    1. Low ending entropy (H=2.66 at last-1; z = -4.4 vs Latin)
    2. High paradigm fill (3.05 endings/stem; z = +14 vs Latin)
    3. Low stem-ending NMI (0.62; z = -14 vs Latin)

  Phase 73 NEVER tested these metrics.  This is a critical gap because
  Cappelli's abbreviation system is a MANY-TO-ONE mapping:
    - Sign ˊ (apostrophe/9) replaces -us, -os, -is, -s
    - Sign 2 replaces -ur, -tur
    - Sign 4 replaces -rum, -ram, -rius
    - Sign 7 replaces -et, -que
    - Sign 3 replaces -m, -em, -est
    - Tilde ~ replaces m/n before consonants

  This many-to-one compression should:
    ↓ REDUCE ending entropy (fewer distinct marks)
    ↑ INCREASE paradigm fill (stems that took -us AND -um now both → mark 1)
    ↓ REDUCE stem-ending NMI (marks are less stem-specific than endings)

  KEY QUESTION: Does abbreviated Latin move TOWARD VMS on the Phase 104
  metrics that seemed to rule out Latin?

APPROACH:
  1. Build a comprehensive Cappelli abbreviation rule set from the
     actual Lexicon Abbreviaturarum introduction (pp. XIX-XXVI)
  2. Apply at densities 0.0-1.0 to all 6 Latin corpora
  3. Measure Phase 104 metrics on the ABBREVIATED text:
     - H(last-1), H(last-2) of abbreviated words
     - Paradigm fill (endings per stem)
     - NMI(stem; ending)
     - Ending transition MI and self-agreement
  4. Also re-measure h_char (Phase 73's decisive metric)
  5. Compare: raw Latin → abbreviated Latin → VMS on each metric

SKEPTICISM NOTES:
  - Even if abbreviation moves Latin toward VMS on ending metrics,
    the h_char gap (Phase 73) remains unexplained.
  - Abbreviation alone cannot be the full story — at best, it could
    be ONE component of a multi-layer encoding.
  - The many-to-one collapse MIGHT trivially produce low NMI regardless
    of source language.  We test this by also abbreviating Italian,
    German, and Czech to check whether the effect is Latin-specific.
  - The abbreviation density is a free parameter.  High density (0.9)
    gives the best match by construction.  We must check whether
    any density produces a joint match on multiple metrics simultaneously.
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import entropy

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

# ═══════════════════════════════════════════════════════════════════════
# CAPPELLI ABBREVIATION RULES
# ═══════════════════════════════════════════════════════════════════════
#
# Reconstructed from Cappelli's introduction (pp. XIX-XXVI):
#
# The medieval system uses ~8 marks that replace Latin endings.
# We model the marks as single characters M1-M8.  In the output,
# a word like "dominus" → "domin" + M1 (mark for -us group).
#
# MARK GROUPS (many-to-one):
#   M1 = apostrophe/comma mark: -us, -os, -is, (final -s)
#   M2 = 2-like mark: -ur, -tur
#   M3 = crossed-2/4 mark: -rum, -ram, -rius, -orum
#   M4 = 7/& mark: -et (also standalone et)
#   M5 = 3-like mark: -m (after vowel), -em, -um, -am
#   M6 = semicolon/period: -bus, -ibus (after b); -que (after q)
#   M7 = tilde mark: nasal bar (m/n before consonant → ~)
#   M8 = general contraction mark (above word): various omissions
#
# Plus whole-word abbreviations and prefix compressions.

# Suffix rules: (endings grouped by which mark replaces them)
# Ordered longest-first within each group for greedy matching.
# Format: (suffix, mark_char, min_remaining_chars)
SUFFIX_MARK_RULES = [
    # M1 group: apostrophe = -us, -os, -is, -s
    ('ibus', '1', 2),    # dative/ablative plural → M1 (sometimes M6 after b)
    ('ius',  '1', 2),
    ('us',   '1', 2),
    ('os',   '1', 2),
    ('is',   '1', 2),

    # M2 group: 2-mark = -ur, -tur, -atur, -itur
    ('atur', '2', 2),
    ('itur', '2', 2),
    ('etur', '2', 2),
    ('tur',  '2', 2),
    ('ur',   '2', 2),

    # M3 group: 4-mark = -rum, -orum, -arum, -ram, -rius
    ('orum', '3', 2),
    ('arum', '3', 2),
    ('rium', '3', 2),
    ('rum',  '3', 2),
    ('ram',  '3', 2),

    # M4 group: 7/& mark = -et (only as suffix, not standalone)
    # Also -que but that's an enclitic, not a suffix

    # M5 group: 3-mark = -m, -em, -um, -am (after vowels, on line)
    ('onem', '5', 2),    # -tionem etc.
    ('em',   '5', 2),
    ('um',   '5', 2),
    ('am',   '5', 2),

    # M6 group: semicolon/period = -bus (after b), -que (enclitic)
    ('bus',  '6', 2),
    ('que',  '6', 1),    # enclitic -que

    # Generic -er, -it, -nt endings (less consistently abbreviated)
    ('nt',   '8', 2),    # 3rd plural
    ('er',   '8', 2),    # agent nouns, comparatives
    ('it',   '8', 2),    # 3rd singular
]

# Whole-word abbreviations (very common words → short forms)
WORD_ABBREVIATIONS = {
    'et':       '4',      # sign 7/&
    'est':      'e8',     # e + general mark
    'sunt':     's8',
    'non':      'n8',
    'sed':      's4',     # s + et-sign
    'enim':     'en',
    'autem':    'a8',
    'tamen':    'tn',
    'igitur':   'ig',
    'quod':     'qd',
    'quam':     'q5',     # q + M5
    'quia':     'qa',
    'cum':      '9',      # the 9-sign
    'aut':      'a8',
    'vel':      'vl',
    'ergo':     'eg',
    'item':     'it',
    'etiam':    'e48',    # et + i + am
    'ante':     'a8e',
    'post':     'p8',
    'inter':    'i8',
    'unde':     'u8',
    'eius':     'ei1',    # ei + us-mark
    'esse':     'ee',
    'deus':     'd1',     # nomina sacra
    'dominus':  'dn1',
    'noster':   'nr',
    'vester':   'vr',
}

# Prefix compressions
PREFIX_RULES = [
    ('contra', 'c9a'),
    ('contr',  'c9'),
    ('cons',   'c9s'),
    ('con',    'c9'),
    ('com',    'c9'),
    ('per',    'p8'),
    ('par',    'p8'),
    ('prae',   'p6'),
    ('pre',    'p6'),
    ('pro',    'p5'),
    ('trans',  't5'),
    ('super',  's6'),
    ('inter',  'i5'),
]

VOWELS = set('aeiou')
MARK_CHARS = set('123456789')  # marks 1-9

def abbreviate_word(word, density, rng):
    """Apply Cappelli abbreviation rules to a Latin word.
    density: 0.0-1.0 probability of applying each rule."""
    if not word or len(word) < 2:
        return word

    # 1. Whole-word abbreviation
    if word in WORD_ABBREVIATIONS and rng.random() < density:
        return WORD_ABBREVIATIONS[word]

    result = word

    # 2. Prefix abbreviation
    for prefix, repl in PREFIX_RULES:
        if result.startswith(prefix) and len(result) > len(prefix) + 1:
            if rng.random() < density * 0.6:
                result = repl + result[len(prefix):]
            break

    # 3. Suffix abbreviation (mark replaces ending)
    for suffix, mark, min_rem in SUFFIX_MARK_RULES:
        if result.endswith(suffix) and len(result) - len(suffix) >= min_rem:
            if rng.random() < density * 0.85:
                result = result[:-len(suffix)] + mark
            break

    # 4. Nasal bar: m/n before consonant → mark 7
    if len(result) >= 3 and rng.random() < density * 0.4:
        new = []
        i = 0
        while i < len(result):
            if (i < len(result) - 1 and result[i] in 'mn'
                and result[i+1] not in VOWELS and result[i+1].isalpha()):
                new.append('7')
            else:
                new.append(result[i])
            i += 1
        result = ''.join(new)

    return result


def abbreviate_text(words, density, rng):
    """Apply abbreviation to a list of words."""
    return [abbreviate_word(w, density, rng) for w in words]


# ═══════════════════════════════════════════════════════════════════════
# TEXT LOADING (reused from Phase 104)
# ═══════════════════════════════════════════════════════════════════════

SECTION_MAP = {
    'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
    'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
}

def load_vms_words():
    """Load VMS corpus as flat word list + line-structured list."""
    lines = []
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        section = 'unknown'
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'):
                ll = line.lower()
                for key, val in SECTION_MAP.items():
                    if key in ll:
                        section = val
                continue
            m = re.match(r'<([^>]+)>', line)
            if not m:
                continue
            rest = line[m.end():].strip()
            if not rest:
                continue
            words = []
            for w in re.split(r'[.\s,;]+', rest):
                w = re.sub(r'[^a-z]', '', w.lower().strip())
                if len(w) >= 2:
                    words.append(w)
            if words:
                lines.append(words)
    flat = [w for ws in lines for w in ws]
    return flat, lines


def load_reference_text(filepath):
    """Load text file, strip Gutenberg headers, return lowercase word list."""
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
    return [w for w in words if len(w) >= 3]


def load_czech_bible():
    """Load Czech Bible Kralice."""
    czech_dir = DATA_DIR / 'czech_bible_kralice'
    if not czech_dir.exists():
        return []
    words = []
    czech_re = re.compile(r'[a-záéíóúůýčďěňřšťž]+')
    for fpath in sorted(czech_dir.glob('*.txt')):
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            ws = [w for w in czech_re.findall(line.lower()) if len(w) >= 3]
            words.extend(ws)
    return words


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL HELPERS (from Phase 104)
# ═══════════════════════════════════════════════════════════════════════



def mi_from_joint(joint_counts, x_counts, y_counts):
    n = sum(joint_counts.values())
    if n == 0:
        return 0.0, 0.0
    h_x = entropy(x_counts)
    h_y = entropy(y_counts)
    h_xy = entropy(joint_counts)
    mi = max(0.0, h_x + h_y - h_xy)
    nmi = mi / min(h_x, h_y) if min(h_x, h_y) > 0.001 else 0.0
    return mi, nmi


def extract_endings(words, n_chars=2):
    endings = Counter()
    stems = defaultdict(set)
    stem_freq = Counter()
    for w in words:
        if len(w) <= n_chars:
            continue
        end = w[-n_chars:]
        stem = w[:-n_chars]
        endings[end] += 1
        stems[stem].add(end)
        stem_freq[stem] += 1
    return endings, stems, stem_freq


def paradigm_fill(stems, stem_freq, min_stem_freq=10):
    frequent = [s for s, f in stem_freq.items() if f >= min_stem_freq and len(s) >= 2]
    if not frequent:
        return 0.0, 0, 0.0
    sizes = [len(stems[s]) for s in frequent]
    return float(np.mean(sizes)), len(frequent), float(np.std(sizes))


def stem_ending_nmi(words, n_chars=2, min_stem_freq=5):
    joint = Counter()
    stem_counts = Counter()
    end_counts = Counter()
    for w in words:
        if len(w) <= n_chars:
            continue
        stem = w[:-n_chars]
        end = w[-n_chars:]
        joint[(stem, end)] += 1
        stem_counts[stem] += 1
        end_counts[end] += 1
    freq_stems = {s for s, c in stem_counts.items() if c >= min_stem_freq}
    joint_filt = Counter({(s, e): c for (s, e), c in joint.items() if s in freq_stems})
    stem_filt = Counter({s: c for s, c in stem_counts.items() if s in freq_stems})
    end_filt = Counter()
    for (s, e), c in joint_filt.items():
        end_filt[e] += c
    mi, nmi = mi_from_joint(joint_filt, stem_filt, end_filt)
    return mi, nmi, len(freq_stems)


def ending_self_agreement(words, n_chars=2):
    same = 0
    total = 0
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i+1]
        if len(w1) <= n_chars or len(w2) <= n_chars:
            continue
        total += 1
        if w1[-n_chars:] == w2[-n_chars:]:
            same += 1
    if total == 0:
        return 0, 0, 0
    rate = same / total
    end_counts = Counter()
    for w in words:
        if len(w) > n_chars:
            end_counts[w[-n_chars:]] += 1
    n = sum(end_counts.values())
    expected = sum((c/n)**2 for c in end_counts.values()) if n > 0 else 0
    return rate, expected, rate / expected if expected > 0 else 0


def ending_bigram_mi(words, n_chars=2):
    bigrams = Counter()
    left = Counter()
    right = Counter()
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i+1]
        if len(w1) <= n_chars or len(w2) <= n_chars:
            continue
        e1 = w1[-n_chars:]
        e2 = w2[-n_chars:]
        bigrams[(e1, e2)] += 1
        left[e1] += 1
        right[e2] += 1
    mi, nmi = mi_from_joint(bigrams, left, right)
    return mi, nmi


def h_char_ratio(words):
    """Compute h_char = H(c|prev) / H(c) from word list.
    This is the character conditional entropy ratio — the key Phase 73 metric."""
    # Build character bigram counts from word interiors
    # Include word boundary as a special character
    unigram = Counter()
    bigram = Counter()
    for w in words:
        seq = '^' + w + '$'
        for c in seq:
            unigram[c] += 1
        for i in range(len(seq) - 1):
            bigram[(seq[i], seq[i+1])] += 1
    h_c = entropy(unigram)
    h_bigram = entropy(bigram)
    # H(c|prev) = H(c, prev) - H(prev) = H(bigram) - H(unigram)
    # But we need to be careful: H(bigram) = H(c1, c2), H(prev) = H(c1)
    # Actually: H(c|prev) ≈ H(bigram_pair) - H(unigram_of_first)
    prev_counts = Counter()
    for (c1, c2), n in bigram.items():
        prev_counts[c1] += n
    h_prev = entropy(prev_counts)
    h_joint = entropy(bigram)
    h_cond = h_joint - h_prev
    if h_c > 0:
        return max(0.0, h_cond / h_c)
    return 0.0


# ═══════════════════════════════════════════════════════════════════════
# MARK-AWARENESS: separate mark-endings from char-endings
# ═══════════════════════════════════════════════════════════════════════

def has_mark_ending(word):
    """Check if word ends with an abbreviation mark (digit character)."""
    return word and word[-1] in MARK_CHARS


def classify_endings_by_mark(words):
    """Separate words into mark-ended and letter-ended.
    Returns (mark_ended_words, letter_ended_words, mark_rate)."""
    mark_words = [w for w in words if has_mark_ending(w)]
    letter_words = [w for w in words if not has_mark_ending(w)]
    rate = len(mark_words) / len(words) if words else 0
    return mark_words, letter_words, rate


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def analyze_corpus(words, label, n_chars_list=[1, 2]):
    """Compute Phase 104 metrics for a word list."""
    results = {'label': label, 'n_words': len(words)}

    for nc in n_chars_list:
        endings, stems, stem_freq = extract_endings(words, nc)
        h_end = entropy(endings)
        n_types = len(endings)
        fill, n_stems, fill_std = paradigm_fill(stems, stem_freq, min_stem_freq=10)
        mi, nmi, n_mi_stems = stem_ending_nmi(words, nc, min_stem_freq=5)
        agree_rate, agree_exp, agree_ratio = ending_self_agreement(words, nc)
        bi_mi, bi_nmi = ending_bigram_mi(words, nc)

        results[f'last{nc}'] = {
            'H_ending': h_end,
            'n_types': n_types,
            'paradigm_fill': fill,
            'paradigm_n_stems': n_stems,
            'paradigm_std': fill_std,
            'stem_end_MI': mi,
            'stem_end_NMI': nmi,
            'n_mi_stems': n_mi_stems,
            'agree_ratio': agree_ratio,
            'bigram_MI': bi_mi,
        }

    # h_char
    results['h_char'] = h_char_ratio(words)

    # top endings
    for nc in n_chars_list:
        endings, _, _ = extract_endings(words, nc)
        top5 = endings.most_common(5)
        total = sum(endings.values())
        results[f'top5_last{nc}'] = [(e, c, c/total) for e, c in top5]

    return results


def print_comparison_table(vms_r, raw_results, abbrev_results_by_density):
    """Print a nice comparison table: VMS vs raw Latin vs abbreviated Latin at various densities."""

    for nc in [1, 2]:
        pr(f"\n{'='*80}")
        pr(f"  COMPARISON TABLE — Last {nc} character(s)")
        pr(f"{'='*80}")
        pr()

        metrics = [
            ('H(ending)',     f'last{nc}', 'H_ending',      '{:.3f}'),
            ('# types',       f'last{nc}', 'n_types',       '{:d}'),
            ('Paradigm fill', f'last{nc}', 'paradigm_fill', '{:.2f}'),
            ('# stems',       f'last{nc}', 'paradigm_n_stems', '{:d}'),
            ('NMI(stem;end)', f'last{nc}', 'stem_end_NMI',  '{:.4f}'),
            ('MI(stem;end)',  f'last{nc}', 'stem_end_MI',   '{:.4f}'),
            ('Agree ratio',   f'last{nc}', 'agree_ratio',   '{:.2f}'),
            ('Bigram MI',     f'last{nc}', 'bigram_MI',     '{:.4f}'),
        ]

        # Header
        densities = sorted(abbrev_results_by_density.keys())
        header = f"  {'Metric':>18s}  {'VMS':>8s}"
        for name, r_list in raw_results.items():
            header += f"  {name[:8]:>8s}"
        for d in densities:
            header += f"  {'d='+str(d):>8s}"
        pr(header)
        pr(f"  {'─'*18}  {'─'*8}" + f"  {'─'*8}" * len(raw_results) +
           f"  {'─'*8}" * len(densities))

        for metric_name, group, key, fmt in metrics:
            row = f"  {metric_name:>18s}"
            # VMS
            val = vms_r[group][key]
            if 'd' in fmt:
                row += f"  {int(val):>8d}"
            else:
                row += f"  {fmt.format(val):>8s}"
            # Raw
            for name, r_list in raw_results.items():
                vals = [r[group][key] for r in r_list if group in r]
                avg = np.mean(vals) if vals else 0
                if 'd' in fmt:
                    row += f"  {avg:>8.0f}"
                else:
                    row += f"  {fmt.format(avg):>8s}"
            # Abbreviated at each density
            for d in densities:
                vals = [r[group][key] for r in abbrev_results_by_density[d] if group in r]
                avg = np.mean(vals) if vals else 0
                if 'd' in fmt:
                    row += f"  {avg:>8.0f}"
                else:
                    row += f"  {fmt.format(avg):>8s}"
            pr(row)

        # Also h_char
        row = f"  {'h_char':>18s}"
        row += f"  {vms_r['h_char']:>8.4f}"
        for name, r_list in raw_results.items():
            vals = [r['h_char'] for r in r_list]
            row += f"  {np.mean(vals):>8.4f}"
        for d in densities:
            vals = [r['h_char'] for r in abbrev_results_by_density[d]]
            row += f"  {np.mean(vals):>8.4f}"
        pr(row)

    pr()


def main():
    pr("=" * 80)
    pr("Phase 105 — Re-testing Cappelli Abbreviation Marks vs VMS Suffixes")
    pr("=" * 80)
    pr()
    pr("Critical revalidation of Phase 73's methodology:")
    pr("  Phase 73 tested h_char (valid failure) but NEVER tested ending metrics.")
    pr("  Phase 104 found VMS endings are 14-20σ from Latin on paradigm fill & NMI.")
    pr("  Cappelli marks are many-to-one → should REDUCE NMI and INCREASE fill.")
    pr("  This phase asks: does abbreviation explain the Phase 104 anomalies?")
    pr()

    # ── Load VMS ─────────────────────────────────────────────────────
    pr("Loading VMS...")
    vms_words, vms_lines = load_vms_words()
    vms_results = analyze_corpus(vms_words, 'VMS')
    pr(f"  VMS: {len(vms_words)} words")
    pr(f"  h_char = {vms_results['h_char']:.4f}")
    for nc in [1, 2]:
        pr(f"  H(last-{nc}) = {vms_results[f'last{nc}']['H_ending']:.3f}, "
           f"fill = {vms_results[f'last{nc}']['paradigm_fill']:.2f}, "
           f"NMI = {vms_results[f'last{nc}']['stem_end_NMI']:.4f}")
    pr()

    # ── Load NL corpora ──────────────────────────────────────────────
    pr("Loading reference corpora...")

    latin_files = {
        'Caesar':  DATA_DIR / 'latin_texts' / 'caesar.txt',
        'Apicius': DATA_DIR / 'latin_texts' / 'apicius.txt',
        'Galen':   DATA_DIR / 'latin_texts' / 'galen.txt',
        'Pliny':   DATA_DIR / 'latin_texts' / 'pliny.txt',
        'Vulgate': DATA_DIR / 'latin_texts' / 'vulgate_genesis.txt',
        'Erasmus': DATA_DIR / 'latin_texts' / 'erasmus.txt',
    }

    vernacular_files = {
        'Italian':  DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt',
        'German':   DATA_DIR / 'vernacular_texts' / 'german_faust.txt',
    }

    latin_corpora = {}
    for name, path in latin_files.items():
        if path.exists():
            words = load_reference_text(path)
            if len(words) >= 500:
                latin_corpora[name] = words
                pr(f"  Latin-{name}: {len(words)} words")

    vernacular_corpora = {}
    for name, path in vernacular_files.items():
        if path.exists():
            words = load_reference_text(path)
            if len(words) >= 500:
                vernacular_corpora[name] = words
                pr(f"  {name}: {len(words)} words")

    czech_words = load_czech_bible()
    if czech_words:
        czech_words = [w for w in czech_words if len(w) >= 3]
        vernacular_corpora['Czech'] = czech_words
        pr(f"  Czech: {len(czech_words)} words")

    pr()

    # ── Analyze raw Latin ────────────────────────────────────────────
    pr("=" * 80)
    pr("SECTION 1 — RAW LATIN BASELINE")
    pr("=" * 80)
    pr()

    raw_latin_results = []
    for name, words in sorted(latin_corpora.items()):
        r = analyze_corpus(words, f'Latin-{name}')
        raw_latin_results.append(r)
        pr(f"  {name:>10s}: h_char={r['h_char']:.4f}  "
           f"H1={r['last1']['H_ending']:.3f}  fill1={r['last1']['paradigm_fill']:.2f}  "
           f"NMI1={r['last1']['stem_end_NMI']:.4f}  "
           f"H2={r['last2']['H_ending']:.3f}  fill2={r['last2']['paradigm_fill']:.2f}  "
           f"NMI2={r['last2']['stem_end_NMI']:.4f}")

    pr()

    # ── Apply abbreviation at various densities ──────────────────────
    pr("=" * 80)
    pr("SECTION 2 — ABBREVIATED LATIN (Cappelli rules)")
    pr("=" * 80)
    pr()

    densities = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    rng = np.random.RandomState(42)

    abbrev_results_by_density = {}

    for density in densities:
        pr(f"--- Density = {density:.1f} ---")
        density_results = []

        for name, words in sorted(latin_corpora.items()):
            abbr_words = abbreviate_text(words, density, rng)
            r = analyze_corpus(abbr_words, f'Abbr-{name}-d{density}')

            # Mark statistics
            mark_words, letter_words, mark_rate = classify_endings_by_mark(abbr_words)

            r['mark_rate'] = mark_rate
            r['n_mark_words'] = len(mark_words)
            density_results.append(r)

            pr(f"  {name:>10s}: mark_rate={100*mark_rate:.1f}%  h_char={r['h_char']:.4f}  "
               f"H1={r['last1']['H_ending']:.3f}  fill1={r['last1']['paradigm_fill']:.2f}  "
               f"NMI1={r['last1']['stem_end_NMI']:.4f}  "
               f"H2={r['last2']['H_ending']:.3f}  fill2={r['last2']['paradigm_fill']:.2f}  "
               f"NMI2={r['last2']['stem_end_NMI']:.4f}")

        abbrev_results_by_density[density] = density_results
        pr()

    # ── Comparison table ─────────────────────────────────────────────
    pr("=" * 80)
    pr("SECTION 3 — COMPARISON: VMS vs Raw Latin vs Abbreviated Latin")
    pr("=" * 80)

    # Compute raw Latin means for the table
    print_comparison_table(
        vms_results,
        {'RawLat': raw_latin_results},
        {d: abbrev_results_by_density[d] for d in [0.0, 0.4, 0.8, 1.0]}
    )

    # ── Direction analysis ───────────────────────────────────────────
    pr("=" * 80)
    pr("SECTION 4 — DIRECTION ANALYSIS: Does abbreviation move Latin toward VMS?")
    pr("=" * 80)
    pr()

    for nc in [1, 2]:
        pr(f"--- Last {nc} character(s) ---")
        pr()

        vms_val = {
            'H': vms_results[f'last{nc}']['H_ending'],
            'fill': vms_results[f'last{nc}']['paradigm_fill'],
            'NMI': vms_results[f'last{nc}']['stem_end_NMI'],
            'agree': vms_results[f'last{nc}']['agree_ratio'],
            'bi_MI': vms_results[f'last{nc}']['bigram_MI'],
        }

        raw_vals = {k: np.mean([r[f'last{nc}'][key] for r in raw_latin_results])
                    for k, key in [('H', 'H_ending'), ('fill', 'paradigm_fill'),
                                   ('NMI', 'stem_end_NMI'), ('agree', 'agree_ratio'),
                                   ('bi_MI', 'bigram_MI')]}

        pr(f"  {'Metric':>18s}  {'VMS':>8s}  {'RawLat':>8s}  {'Gap':>8s}  ", end='')
        for d in [0.4, 0.8, 1.0]:
            pr(f"  {'d='+str(d):>8s}", end='')
        pr(f"  {'% gap closed':>13s}")

        pr(f"  {'─'*18}  {'─'*8}  {'─'*8}  {'─'*8}  " + f"  {'─'*8}" * 3 + f"  {'─'*13}")

        for metric in ['H', 'fill', 'NMI', 'agree', 'bi_MI']:
            gap = vms_val[metric] - raw_vals[metric]
            row = f"  {metric:>18s}  {vms_val[metric]:8.4f}  {raw_vals[metric]:8.4f}  {gap:+8.4f}  "

            key_map = {'H': 'H_ending', 'fill': 'paradigm_fill', 'NMI': 'stem_end_NMI',
                       'agree': 'agree_ratio', 'bi_MI': 'bigram_MI'}

            for d in [0.4, 0.8, 1.0]:
                abbr_val = np.mean([r[f'last{nc}'][key_map[metric]]
                                   for r in abbrev_results_by_density[d]])
                row += f"  {abbr_val:8.4f}"

            # % gap closed at d=1.0
            abbr_final = np.mean([r[f'last{nc}'][key_map[metric]]
                                 for r in abbrev_results_by_density[1.0]])
            if abs(gap) > 0.0001:
                closed = 100 * (abbr_final - raw_vals[metric]) / gap
                row += f"  {closed:+12.1f}%"
            else:
                row += f"  {'N/A':>13s}"
            pr(row)

        # h_char direction
        gap = vms_results['h_char'] - np.mean([r['h_char'] for r in raw_latin_results])
        raw_hc = np.mean([r['h_char'] for r in raw_latin_results])
        row = f"  {'h_char':>18s}  {vms_results['h_char']:8.4f}  {raw_hc:8.4f}  {gap:+8.4f}  "
        for d in [0.4, 0.8, 1.0]:
            abbr_hc = np.mean([r['h_char'] for r in abbrev_results_by_density[d]])
            row += f"  {abbr_hc:8.4f}"
        abbr_final_hc = np.mean([r['h_char'] for r in abbrev_results_by_density[1.0]])
        if abs(gap) > 0.0001:
            closed = 100 * (abbr_final_hc - raw_hc) / gap
            row += f"  {closed:+12.1f}%"
        else:
            row += f"  {'N/A':>13s}"
        pr(row)
        pr()

    # ── Vernacular control ───────────────────────────────────────────
    pr("=" * 80)
    pr("SECTION 5 — CONTROL: Abbreviation applied to non-Latin languages")
    pr("=" * 80)
    pr()
    pr("Does abbreviation trivially produce VMS-like metrics from ANY language?")
    pr("If yes → abbreviation effect is not Latin-specific → weaker evidence.")
    pr()

    for name, words in sorted(vernacular_corpora.items()):
        raw_r = analyze_corpus(words, f'{name}-raw')
        abbr_words = abbreviate_text(words, 1.0, rng)
        abbr_r = analyze_corpus(abbr_words, f'{name}-abbr1.0')
        _, _, mark_rate = classify_endings_by_mark(abbr_words)

        pr(f"  {name:>10s} (mark_rate at d=1.0: {100*mark_rate:.1f}%):")
        for nc in [1, 2]:
            raw_h = raw_r[f'last{nc}']['H_ending']
            raw_fill = raw_r[f'last{nc}']['paradigm_fill']
            raw_nmi = raw_r[f'last{nc}']['stem_end_NMI']
            abbr_h = abbr_r[f'last{nc}']['H_ending']
            abbr_fill = abbr_r[f'last{nc}']['paradigm_fill']
            abbr_nmi = abbr_r[f'last{nc}']['stem_end_NMI']
            pr(f"    last-{nc}: H {raw_h:.3f}→{abbr_h:.3f}  "
               f"fill {raw_fill:.2f}→{abbr_fill:.2f}  "
               f"NMI {raw_nmi:.4f}→{abbr_nmi:.4f}")
        pr(f"    h_char: {raw_r['h_char']:.4f}→{abbr_r['h_char']:.4f}")
        pr()

    # ── Top endings comparison ───────────────────────────────────────
    pr("=" * 80)
    pr("SECTION 6 — TOP ENDINGS: VMS vs Abbreviated Latin at d=1.0")
    pr("=" * 80)
    pr()

    pr("VMS top endings (last-1):")
    for e, c, p in vms_results['top5_last1']:
        pr(f"  -{e}: {100*p:.1f}%")
    pr()

    pr("VMS top endings (last-2):")
    for e, c, p in vms_results['top5_last2']:
        pr(f"  -{e}: {100*p:.1f}%")
    pr()

    # Average over all Latin corpora at d=1.0
    all_abbr_words = []
    for name, words in sorted(latin_corpora.items()):
        all_abbr_words.extend(abbreviate_text(words, 1.0, rng))
    abbr_all_r = analyze_corpus(all_abbr_words, 'AllLatinAbbr-d1.0')

    pr("Abbreviated Latin (all corpora, d=1.0) top endings (last-1):")
    for e, c, p in abbr_all_r['top5_last1']:
        pr(f"  -{e}: {100*p:.1f}%")
    pr()

    pr("Abbreviated Latin (all corpora, d=1.0) top endings (last-2):")
    for e, c, p in abbr_all_r['top5_last2']:
        pr(f"  -{e}: {100*p:.1f}%")
    pr()

    # ── Mark inventory comparison ────────────────────────────────────
    pr("=" * 80)
    pr("SECTION 7 — MARK INVENTORY: Cappelli marks vs VMS suffix types")
    pr("=" * 80)
    pr()

    # Count how many words end with each mark
    mark_counter = Counter()
    for w in all_abbr_words:
        if w and w[-1] in MARK_CHARS:
            mark_counter[w[-1]] += 1
    total_marks = sum(mark_counter.values())

    pr("Cappelli mark distribution (all Latin, d=1.0):")
    mark_labels = {
        '1': 'M1 (-us/-os/-is/-ibus)',
        '2': 'M2 (-ur/-tur)',
        '3': 'M3 (-rum/-orum/-ram)',
        '4': 'M4 (et/7-sign)',
        '5': 'M5 (-um/-em/-am/-onem)',
        '6': 'M6 (-bus/-que)',
        '7': 'M7 (nasal bar)',
        '8': 'M8 (-er/-nt/-it/general)',
        '9': 'M9 (cum)',
    }
    for mark, count in sorted(mark_counter.items(), key=lambda x: -x[1]):
        label = mark_labels.get(mark, f'M{mark}')
        pr(f"  {label:>30s}: {count:6d} ({100*count/total_marks:5.1f}%)")
    pr(f"  {'Total mark-ended words':>30s}: {total_marks:6d} "
       f"({100*total_marks/len(all_abbr_words):5.1f}% of all words)")
    pr(f"  {'Distinct mark types':>30s}: {len(mark_counter):6d}")
    pr()

    pr("VMS parser suffix distribution (Phase 104):")
    pr("  (Using last-1 character distribution as proxy)")
    vms_l1 = Counter()
    for w in vms_words:
        if w:
            vms_l1[w[-1]] += 1
    total_vms = sum(vms_l1.values())
    for ch, count in vms_l1.most_common(10):
        pr(f"  {'-'+ch:>8s}: {count:6d} ({100*count/total_vms:5.1f}%)")
    pr(f"  Distinct last-1 types: {len(vms_l1)}")
    pr()

    pr(f"  Cappelli: {len(mark_counter)} mark types, H={entropy(mark_counter):.3f} bits")
    pr(f"  VMS last-1: {len(vms_l1)} types, H={entropy(vms_l1):.3f} bits")
    pr()

    # ── Critical assessment ──────────────────────────────────────────
    pr("=" * 80)
    pr("SECTION 8 — CRITICAL ASSESSMENT")
    pr("=" * 80)
    pr()

    pr("WHAT ABBREVIATION EXPLAINS:")
    pr("  - See direction analysis above for % gap closed on each metric.")
    pr("  - Focus on: H(ending), paradigm fill, NMI, h_char")
    pr()
    pr("WHAT ABBREVIATION DOES NOT EXPLAIN:")
    pr("  - Phase 73 showed h_char remains ~0.85 (VMS needs 0.64).")
    pr("  - This phase measures whether abbreviation even moves h_char.")
    pr()
    pr("CONTROLS:")
    pr("  - Vernacular languages show whether the effect is Latin-specific.")
    pr("  - Density sweep shows whether the effect saturates or scales.")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # SAVE
    # ═══════════════════════════════════════════════════════════════════
    out_txt = RESULTS_DIR / 'phase105_cappelli_retest.txt'
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"\nResults saved to {out_txt}")

    results_json = {
        'vms': {k: v for k, v in vms_results.items() if not k.startswith('top5')},
        'densities_tested': densities,
        'n_latin_corpora': len(latin_corpora),
        'n_vernacular_corpora': len(vernacular_corpora),
    }
    out_json = RESULTS_DIR / 'phase105_cappelli_retest.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results_json, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
