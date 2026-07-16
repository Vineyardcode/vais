#!/usr/bin/env python3
"""
Do VMS Word-Final Chunks Encode Latin Inflectional Endings?

═══════════════════════════════════════════════════════════════════════

QUESTION:
  VMS words have inflectional suffixes (Phases 31/33/37/62).  Do these
  correspond to Latin grammatical case endings (-us, -um, -em, -ae, etc.)?

APPROACH — Five falsifiable tests:

  Test A — ENDING INVENTORY SHAPE
    Compare rank-frequency distribution of VMS endings vs NL endings
    at two granularities: last-1-char and last-2-chars.  Compute L1
    distance and entropy difference.

  Test B — PARADIGM STRUCTURE
    For each "stem" (word minus ending), count distinct endings per stem.
    In Latin, declension classes restrict paradigm fill.  If VMS fill is
    significantly higher → argues AGAINST Latin case system.

  Test C — STEM-ENDING MUTUAL INFORMATION
    MI(stem; ending) and NMI(stem; ending).  In Latin, declension class
    creates moderate NMI.  If VMS NMI is far outside Latin range → argues
    against.

  Test D — ENDING SEQUENCE GRAMMAR
    Build ending→ending bigram matrices for consecutive words.  Compare
    MI, attraction/avoidance patterns, and self-agreement rate.

  Test E — LINE-POSITION SENSITIVITY
    VMS line-final words prefer null suffix (75%).  Does any NL language
    show comparable sentence/line-position × ending skew?

SKEPTICISM NOTES:
  - e_extension_morphology found VMS e-extension rate = 9.1% vs Latin 0.2-0.4%.
    This tests internal chunk morphology, not word endings, but signals
    fundamental structural difference.
  - suffix_bug_cascade_audit parser defines suffixes by VMS-specific rules.  NL comparison
    must use character-level endings to avoid circularity.
  - With only 8 distinct final characters in VMS, chance matches are likely.
  - Any mismatch can be attributed to encoding.  Focus on properties that
    survive simple substitution ciphers.
  - Czech Bible Kralice corpus is available for Bohemian-theory testing.
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import entropy, load_reference_text

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
# VMS LOADING
# ═══════════════════════════════════════════════════════════════════════

SECTION_MAP = {
    'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
    'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
}

def load_vms_lines():
    """Return list of (line_id, section, [words]) preserving line structure."""
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
            lid = m.group(1)
            rest = line[m.end():].strip()
            if not rest:
                continue
            words = []
            for w in re.split(r'[.\s,;]+', rest):
                w = re.sub(r'[^a-z]', '', w.lower().strip())
                if len(w) >= 2:
                    words.append(w)
            if words:
                lines.append((lid, section, words))
    return lines


# ═══════════════════════════════════════════════════════════════════════
# VMS SUFFIX PARSER (suffix_bug_cascade_audit SHORT list — corrected)
# ═══════════════════════════════════════════════════════════════════════

VMS_SUFFIXES = ['aiin', 'ain', 'iin', 'in', 'ar', 'or', 'al', 'ol', 'dy', 'y']

# Gallows trigraphs and digraphs for stripping
GALLOWS_TRI = {'cth', 'ckh', 'cph', 'cfh'}
GALLOWS_DI  = {'kh', 'ph', 'fh', 'th'}

def strip_gallows(word):
    """Remove gallows from EVA word, return (stripped, gallows_list)."""
    gals = []
    result = word
    for g in sorted(GALLOWS_TRI, key=len, reverse=True):
        while g in result:
            idx = result.index(g)
            result = result[:idx] + result[idx+len(g):]
            gals.append(g)
    for g in sorted(GALLOWS_DI, key=len, reverse=True):
        while g in result:
            idx = result.index(g)
            result = result[:idx] + result[idx+len(g):]
            gals.append(g)
    return result, gals


def collapse_echains(word):
    """Collapse runs of 'e' to single 'e' (suffix_bug_cascade_audit convention)."""
    return re.sub(r'e{2,}', 'e', word)


def vms_parse_suffix(word):
    """Parse VMS word into (stem, suffix) using suffix_bug_cascade_audit SHORT parser.
    Returns suffix as string, or '∅' for null suffix."""
    stripped, _ = strip_gallows(word)
    collapsed = collapse_echains(stripped)
    for sf in VMS_SUFFIXES:
        if collapsed.endswith(sf) and len(collapsed) > len(sf):
            return collapsed[:-len(sf)], sf
    return collapsed, '∅'


# ═══════════════════════════════════════════════════════════════════════
# NL TEXT LOADING
# ═══════════════════════════════════════════════════════════════════════



def load_reference_lines(filepath):
    """Load text preserving line/sentence structure. Returns list of word-lists."""
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
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        words = re.findall(r'[a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþßœ]+', line)
        words = [w for w in words if len(w) >= 3]
        if words:
            lines.append(words)
    return lines


def load_czech_bible():
    """Load Czech Bible Kralice as word list."""
    czech_dir = DATA_DIR / 'czech_bible_kralice'
    if not czech_dir.exists():
        return [], []
    words = []
    lines = []
    czech_re = re.compile(r'[a-záéíóúůýčďěňřšťž]+')
    for fpath in sorted(czech_dir.glob('*.txt')):
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if not line:
                continue
            ws = [w for w in czech_re.findall(line.lower()) if len(w) >= 3]
            if ws:
                words.extend(ws)
                lines.append(ws)
    return words, lines


# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL HELPERS
# ═══════════════════════════════════════════════════════════════════════



def mi_from_joint(joint_counts, x_counts, y_counts):
    """MI(X; Y) from joint and marginal Counters."""
    n = sum(joint_counts.values())
    if n == 0:
        return 0.0, 0.0
    h_x = entropy(x_counts)
    h_y = entropy(y_counts)
    h_xy = entropy(joint_counts)
    mi = max(0.0, h_x + h_y - h_xy)
    nmi = mi / min(h_x, h_y) if min(h_x, h_y) > 0.001 else 0.0
    return mi, nmi


def l1_rank_freq(counts_a, counts_b):
    """L1 distance between rank-frequency curves (sorted descending proportions)."""
    freqs_a = sorted(counts_a.values(), reverse=True)
    freqs_b = sorted(counts_b.values(), reverse=True)
    total_a = sum(freqs_a) or 1
    total_b = sum(freqs_b) or 1
    props_a = [f / total_a for f in freqs_a]
    props_b = [f / total_b for f in freqs_b]
    max_len = max(len(props_a), len(props_b))
    a = props_a + [0.0] * (max_len - len(props_a))
    b = props_b + [0.0] * (max_len - len(props_b))
    return sum(abs(x - y) for x, y in zip(a, b))


# ═══════════════════════════════════════════════════════════════════════
# ENDING EXTRACTION (character-level, language-agnostic)
# ═══════════════════════════════════════════════════════════════════════

def extract_endings(words, n_chars=2):
    """Extract last n_chars from each word. Returns (endings Counter, stems dict).
    stems[stem] = set of distinct endings seen with that stem."""
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


def ending_bigrams(words, n_chars=2):
    """Build (ending_i → ending_{i+1}) bigram counter for adjacent words."""
    bigrams = Counter()
    left_counts = Counter()
    right_counts = Counter()
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i+1]
        if len(w1) <= n_chars or len(w2) <= n_chars:
            continue
        e1 = w1[-n_chars:]
        e2 = w2[-n_chars:]
        bigrams[(e1, e2)] += 1
        left_counts[e1] += 1
        right_counts[e2] += 1
    return bigrams, left_counts, right_counts


def ending_self_agreement(words, n_chars=2):
    """Rate at which adjacent words share the same ending."""
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
    # Expected by chance
    end_counts = Counter()
    for w in words:
        if len(w) > n_chars:
            end_counts[w[-n_chars:]] += 1
    n = sum(end_counts.values())
    expected = sum((c/n)**2 for c in end_counts.values()) if n > 0 else 0
    return rate, expected, rate / expected if expected > 0 else 0


# ═══════════════════════════════════════════════════════════════════════
# PARADIGM ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def paradigm_analysis(stems, stem_freq, min_stem_freq=10, top_n_endings=20):
    """Analyze paradigm fill: distinct endings per frequent stem.
    Returns dict with paradigm statistics."""
    frequent = [s for s, f in stem_freq.items() if f >= min_stem_freq and len(s) >= 2]
    if not frequent:
        return {'n_stems': 0, 'mean_size': 0, 'median_size': 0, 'max_size': 0,
                'distribution': {}}
    sizes = [len(stems[s]) for s in frequent]
    dist = Counter(sizes)
    return {
        'n_stems': len(frequent),
        'mean_size': np.mean(sizes),
        'median_size': float(np.median(sizes)),
        'max_size': max(sizes),
        'std_size': float(np.std(sizes)),
        'distribution': dict(sorted(dist.items())),
    }


# ═══════════════════════════════════════════════════════════════════════
# STEM-ENDING MI
# ═══════════════════════════════════════════════════════════════════════

def stem_ending_mi(words, n_chars=2, min_stem_freq=5):
    """Compute MI(stem; ending) using only frequent stems."""
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

    # Filter to frequent stems only (to avoid MI inflation from hapax)
    freq_stems = {s for s, c in stem_counts.items() if c >= min_stem_freq}
    joint_filt = Counter({(s, e): c for (s, e), c in joint.items() if s in freq_stems})
    stem_filt = Counter({s: c for s, c in stem_counts.items() if s in freq_stems})
    end_filt = Counter()
    for (s, e), c in joint_filt.items():
        end_filt[e] += c

    mi, nmi = mi_from_joint(joint_filt, stem_filt, end_filt)
    return mi, nmi, len(freq_stems), entropy(end_filt)


# ═══════════════════════════════════════════════════════════════════════
# LINE-POSITION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def line_position_ending_skew(line_words_list, n_chars=2):
    """Analyze how ending distributions differ between line/sentence positions.
    Positions: initial, medial, final."""
    pos_endings = {'initial': Counter(), 'medial': Counter(), 'final': Counter()}
    for ws in line_words_list:
        if len(ws) < 2:
            continue
        for i, w in enumerate(ws):
            if len(w) <= n_chars:
                continue
            end = w[-n_chars:]
            if i == 0:
                pos_endings['initial'][end] += 1
            elif i == len(ws) - 1:
                pos_endings['final'][end] += 1
            else:
                pos_endings['medial'][end] += 1

    # Compute MI(ending; position)
    joint = Counter()
    pos_marginal = Counter()
    end_marginal = Counter()
    for pos, ec in pos_endings.items():
        for end, cnt in ec.items():
            joint[(end, pos)] += cnt
            pos_marginal[pos] += cnt
            end_marginal[end] += cnt

    mi, nmi = mi_from_joint(joint, end_marginal, pos_marginal)

    # Top ending at each position
    top_per_pos = {}
    for pos in ['initial', 'medial', 'final']:
        total = sum(pos_endings[pos].values())
        if total > 0:
            top = pos_endings[pos].most_common(3)
            top_per_pos[pos] = [(e, c, c/total) for e, c in top]
        else:
            top_per_pos[pos] = []

    return mi, nmi, top_per_pos, pos_endings


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 72)
    pr("latin_inflection_ending_test — Do VMS Word Endings Encode Latin Inflectional Endings?")
    pr("=" * 72)
    pr()

    # ── Load VMS ─────────────────────────────────────────────────────
    pr("Loading VMS corpus...")
    vms_lines = load_vms_lines()
    vms_words_flat = [w for _, _, ws in vms_lines for w in ws]
    vms_line_words = [ws for _, _, ws in vms_lines]
    pr(f"  Words: {len(vms_words_flat)}, Lines: {len(vms_lines)}")
    pr()

    # VMS parser-level suffixes
    vms_parser_endings = Counter()
    vms_parser_stems = defaultdict(set)
    vms_parser_stem_freq = Counter()
    for w in vms_words_flat:
        stem, sfx = vms_parse_suffix(w)
        vms_parser_endings[sfx] += 1
        vms_parser_stems[stem].add(sfx)
        vms_parser_stem_freq[stem] += 1

    pr("VMS parser-level suffix distribution:")
    for sfx, n in vms_parser_endings.most_common():
        pr(f"  {sfx:>6s}: {n:6d} ({100*n/len(vms_words_flat):5.1f}%)")
    pr(f"  H(suffix) = {entropy(vms_parser_endings):.3f} bits")
    pr(f"  Types: {len(vms_parser_endings)}")
    pr()

    # ── Load NL corpora ──────────────────────────────────────────────
    pr("Loading NL reference corpora...")
    pr()

    nl_corpora = {}
    nl_text_files = {
        'Latin-Caesar':    DATA_DIR / 'latin_texts' / 'caesar.txt',
        'Latin-Vulgate':   DATA_DIR / 'latin_texts' / 'vulgate_genesis.txt',
        'Latin-Apicius':   DATA_DIR / 'latin_texts' / 'apicius.txt',
        'Latin-Erasmus':   DATA_DIR / 'latin_texts' / 'erasmus.txt',
        'Latin-Galen':     DATA_DIR / 'latin_texts' / 'galen.txt',
        'Latin-Pliny':     DATA_DIR / 'latin_texts' / 'pliny.txt',
        'Italian-Cucina':  DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt',
        'French-Viandier': DATA_DIR / 'vernacular_texts' / 'french_viandier.txt',
        'English-Cury':    DATA_DIR / 'vernacular_texts' / 'english_cury.txt',
        'German-Faust':    DATA_DIR / 'vernacular_texts' / 'german_faust.txt',
        'German-BvgS':     DATA_DIR / 'vernacular_texts' / 'german_bvgs_raw.txt',
    }

    for name, path in sorted(nl_text_files.items()):
        if not path.exists():
            continue
        words = load_reference_text(path)
        words = [w for w in words if len(w) >= 3]
        lines = load_reference_lines(path)
        if len(words) < 500:
            continue
        nl_corpora[name] = {'words': words, 'lines': lines}
        pr(f"  {name}: {len(words)} words, {len(lines)} lines")

    # Czech Bible
    czech_words, czech_lines = load_czech_bible()
    if czech_words:
        czech_words = [w for w in czech_words if len(w) >= 3]
        nl_corpora['Czech-Bible'] = {'words': czech_words, 'lines': czech_lines}
        pr(f"  Czech-Bible: {len(czech_words)} words, {len(czech_lines)} lines")

    pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST A — ENDING INVENTORY SHAPE
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST A — ENDING INVENTORY SHAPE")
    pr("=" * 72)
    pr()

    for n_chars in [1, 2]:
        pr(f"--- Last {n_chars} character(s) ---")
        pr()

        vms_endings, _, _ = extract_endings(vms_words_flat, n_chars)
        vms_h = entropy(vms_endings)
        vms_n_types = len(vms_endings)
        top2_vms = sum(n for _, n in vms_endings.most_common(2))
        top2_pct_vms = top2_vms / sum(vms_endings.values())

        pr(f"  VMS: {vms_n_types} types, H={vms_h:.3f} bits, "
           f"top-2 conc.={100*top2_pct_vms:.1f}%")
        for e, n in vms_endings.most_common(8):
            pr(f"    -{e}: {n} ({100*n/sum(vms_endings.values()):.1f}%)")
        pr()

        pr(f"  {'Language':>20s}  {'Types':>6s}  {'H(bits)':>7s}  "
           f"{'Top2%':>6s}  {'L1→VMS':>7s}  {'ΔH':>6s}")
        pr(f"  {'─'*20}  {'─'*6}  {'─'*7}  {'─'*6}  {'─'*7}  {'─'*6}")

        nl_hs = []
        nl_l1s = []
        for name, data in sorted(nl_corpora.items()):
            nl_endings, _, _ = extract_endings(data['words'], n_chars)
            nl_h = entropy(nl_endings)
            nl_n_types = len(nl_endings)
            top2_nl = sum(n for _, n in nl_endings.most_common(2))
            top2_pct_nl = top2_nl / sum(nl_endings.values())
            l1 = l1_rank_freq(vms_endings, nl_endings)
            dh = abs(vms_h - nl_h)
            nl_hs.append(nl_h)
            nl_l1s.append(l1)
            pr(f"  {name:>20s}  {nl_n_types:6d}  {nl_h:7.3f}  "
               f"{100*top2_pct_nl:5.1f}%  {l1:7.4f}  {dh:6.3f}")

        pr()
        if nl_hs:
            mean_h = np.mean(nl_hs)
            std_h = np.std(nl_hs)
            z_h = (vms_h - mean_h) / std_h if std_h > 0 else 0
            pr(f"  NL H mean: {mean_h:.3f} ± {std_h:.3f}, VMS z={z_h:.2f}")

            # Separate Latin vs non-Latin
            latin_hs = [nl_hs[i] for i, name in enumerate(sorted(nl_corpora.keys()))
                        if 'Latin' in name]
            if latin_hs:
                lat_mean = np.mean(latin_hs)
                lat_std = np.std(latin_hs)
                z_lat = (vms_h - lat_mean) / lat_std if lat_std > 0 else 0
                pr(f"  Latin-only H mean: {lat_mean:.3f} ± {lat_std:.3f}, VMS z={z_lat:.2f}")
        pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST B — PARADIGM STRUCTURE
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST B — PARADIGM STRUCTURE")
    pr("=" * 72)
    pr()

    for n_chars in [1, 2]:
        pr(f"--- Last {n_chars} character(s), min stem freq=10 ---")
        pr()

        vms_endings, vms_stems, vms_stem_freq = extract_endings(vms_words_flat, n_chars)
        vms_para = paradigm_analysis(vms_stems, vms_stem_freq, min_stem_freq=10)

        pr(f"  VMS: {vms_para['n_stems']} stems, "
           f"mean={vms_para['mean_size']:.2f} ± {vms_para['std_size']:.2f}, "
           f"median={vms_para['median_size']:.1f}, max={vms_para['max_size']}")
        pr(f"    Distribution: {vms_para['distribution']}")
        pr()

        pr(f"  {'Language':>20s}  {'Stems':>6s}  {'Mean':>6s}  {'Std':>6s}  "
           f"{'Median':>7s}  {'Max':>5s}")
        pr(f"  {'─'*20}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*7}  {'─'*5}")

        nl_means = []
        for name, data in sorted(nl_corpora.items()):
            nl_endings, nl_stems, nl_stem_freq = extract_endings(data['words'], n_chars)
            nl_para = paradigm_analysis(nl_stems, nl_stem_freq, min_stem_freq=10)
            if nl_para['n_stems'] > 0:
                nl_means.append(nl_para['mean_size'])
                pr(f"  {name:>20s}  {nl_para['n_stems']:6d}  {nl_para['mean_size']:6.2f}  "
                   f"{nl_para['std_size']:6.2f}  {nl_para['median_size']:7.1f}  "
                   f"{nl_para['max_size']:5d}")

        pr()
        if nl_means:
            mean_m = np.mean(nl_means)
            std_m = np.std(nl_means)
            z_m = (vms_para['mean_size'] - mean_m) / std_m if std_m > 0 else 0
            pr(f"  NL paradigm mean: {mean_m:.2f} ± {std_m:.2f}, VMS z={z_m:.2f}")

            latin_means = [nl_means[i] for i, name in enumerate(sorted(nl_corpora.keys()))
                           if 'Latin' in name]
            if latin_means:
                lat_mean = np.mean(latin_means)
                lat_std = np.std(latin_means)
                z_lat = (vms_para['mean_size'] - lat_mean) / lat_std if lat_std > 0 else 0
                pr(f"  Latin-only paradigm mean: {lat_mean:.2f} ± {lat_std:.2f}, "
                   f"VMS z={z_lat:.2f}")
        pr()

    # Also run with parser-level VMS suffixes (for context)
    pr("--- VMS Parser-level suffixes (11 types), min stem freq=10 ---")
    vms_parser_para = paradigm_analysis(vms_parser_stems, vms_parser_stem_freq,
                                        min_stem_freq=10)
    pr(f"  VMS parser: {vms_parser_para['n_stems']} stems, "
       f"mean={vms_parser_para['mean_size']:.2f} ± {vms_parser_para['std_size']:.2f}, "
       f"median={vms_parser_para['median_size']:.1f}, max={vms_parser_para['max_size']}")
    pr(f"    Distribution: {vms_parser_para['distribution']}")
    pr(f"    (11 possible suffix types → fill rate = "
       f"{100*vms_parser_para['mean_size']/11:.1f}%)")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST C — STEM-ENDING MUTUAL INFORMATION
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST C — STEM-ENDING MUTUAL INFORMATION")
    pr("=" * 72)
    pr()

    for n_chars in [1, 2]:
        pr(f"--- Last {n_chars} character(s), min stem freq=5 ---")
        pr()

        vms_mi, vms_nmi, vms_n_stems, vms_h_end = stem_ending_mi(
            vms_words_flat, n_chars, min_stem_freq=5)
        pr(f"  VMS: MI={vms_mi:.4f} bits, NMI={vms_nmi:.4f}, "
           f"stems={vms_n_stems}, H(ending)={vms_h_end:.3f}")
        pr()

        pr(f"  {'Language':>20s}  {'MI':>7s}  {'NMI':>7s}  {'Stems':>6s}  "
           f"{'H(end)':>7s}")
        pr(f"  {'─'*20}  {'─'*7}  {'─'*7}  {'─'*6}  {'─'*7}")

        nl_nmis = []
        for name, data in sorted(nl_corpora.items()):
            nl_mi, nl_nmi, nl_n_stems, nl_h_end = stem_ending_mi(
                data['words'], n_chars, min_stem_freq=5)
            nl_nmis.append(nl_nmi)
            pr(f"  {name:>20s}  {nl_mi:7.4f}  {nl_nmi:7.4f}  "
               f"{nl_n_stems:6d}  {nl_h_end:7.3f}")

        pr()
        if nl_nmis:
            mean_nmi = np.mean(nl_nmis)
            std_nmi = np.std(nl_nmis)
            z_nmi = (vms_nmi - mean_nmi) / std_nmi if std_nmi > 0 else 0
            pr(f"  NL NMI mean: {mean_nmi:.4f} ± {std_nmi:.4f}, VMS z={z_nmi:.2f}")

            latin_nmis = [nl_nmis[i] for i, name in enumerate(sorted(nl_corpora.keys()))
                          if 'Latin' in name]
            if latin_nmis:
                lat_mean = np.mean(latin_nmis)
                lat_std = np.std(latin_nmis)
                z_lat = (vms_nmi - lat_mean) / lat_std if lat_std > 0 else 0
                pr(f"  Latin-only NMI mean: {lat_mean:.4f} ± {lat_std:.4f}, "
                   f"VMS z={z_lat:.2f}")
        pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST D — ENDING SEQUENCE GRAMMAR
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST D — ENDING SEQUENCE GRAMMAR")
    pr("=" * 72)
    pr()

    n_chars = 2

    pr(f"--- Adjacent ending transitions (last {n_chars} chars) ---")
    pr()

    # VMS
    vms_bi, vms_l, vms_r = ending_bigrams(vms_words_flat, n_chars)
    vms_bi_mi, vms_bi_nmi = mi_from_joint(vms_bi, vms_l, vms_r)
    vms_agree_rate, vms_agree_exp, vms_agree_ratio = ending_self_agreement(
        vms_words_flat, n_chars)

    pr(f"  VMS: MI(end_i→end_j)={vms_bi_mi:.4f} bits, NMI={vms_bi_nmi:.4f}")
    pr(f"  VMS: self-agreement={100*vms_agree_rate:.2f}%, "
       f"expected={100*vms_agree_exp:.2f}%, ratio={vms_agree_ratio:.2f}×")
    pr()

    # Top attractions and avoidances for VMS
    n_total = sum(vms_bi.values())
    vms_contribs = {}
    for (e1, e2), n_ab in vms_bi.items():
        p_ab = n_ab / n_total
        p_a = vms_l[e1] / n_total
        p_b = vms_r[e2] / n_total
        if p_ab > 0 and p_a > 0 and p_b > 0:
            pmi = math.log2(p_ab / (p_a * p_b))
            vms_contribs[(e1, e2)] = (pmi, n_ab, n_ab / (p_a * p_b * n_total))

    pr("  Top 10 VMS attractions (highest obs/exp):")
    by_ratio = sorted(vms_contribs.items(), key=lambda x: x[1][2], reverse=True)
    shown = 0
    for (e1, e2), (pmi, cnt, ratio) in by_ratio:
        if cnt < 20:
            continue
        pr(f"    -{e1}→-{e2}: {cnt:5d}  obs/exp={ratio:.2f}×  pmi={pmi:+.3f}")
        shown += 1
        if shown >= 10:
            break

    pr()
    pr("  Top 10 VMS avoidances (lowest obs/exp, count≥10):")
    by_ratio_low = sorted(vms_contribs.items(), key=lambda x: x[1][2])
    shown = 0
    for (e1, e2), (pmi, cnt, ratio) in by_ratio_low:
        if cnt < 10:
            continue
        pr(f"    -{e1}→-{e2}: {cnt:5d}  obs/exp={ratio:.2f}×  pmi={pmi:+.3f}")
        shown += 1
        if shown >= 10:
            break

    pr()
    pr(f"  {'Language':>20s}  {'MI':>7s}  {'NMI':>7s}  {'Agree%':>7s}  "
       f"{'Exp%':>6s}  {'Ratio':>6s}")
    pr(f"  {'─'*20}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*6}  {'─'*6}")

    nl_agree_ratios = []
    nl_bi_mis = []
    for name, data in sorted(nl_corpora.items()):
        nl_bi, nl_l, nl_r = ending_bigrams(data['words'], n_chars)
        nl_mi, nl_nmi = mi_from_joint(nl_bi, nl_l, nl_r)
        nl_agree, nl_exp, nl_ratio = ending_self_agreement(data['words'], n_chars)
        nl_agree_ratios.append(nl_ratio)
        nl_bi_mis.append(nl_mi)
        pr(f"  {name:>20s}  {nl_mi:7.4f}  {nl_nmi:7.4f}  "
           f"{100*nl_agree:6.2f}%  {100*nl_exp:5.2f}%  {nl_ratio:5.2f}×")

    pr()
    if nl_agree_ratios:
        mean_ratio = np.mean(nl_agree_ratios)
        std_ratio = np.std(nl_agree_ratios)
        z_ratio = (vms_agree_ratio - mean_ratio) / std_ratio if std_ratio > 0 else 0
        pr(f"  NL agreement ratio mean: {mean_ratio:.2f} ± {std_ratio:.2f}, "
           f"VMS z={z_ratio:.2f}")

        mean_mi = np.mean(nl_bi_mis)
        std_mi = np.std(nl_bi_mis)
        z_mi = (vms_bi_mi - mean_mi) / std_mi if std_mi > 0 else 0
        pr(f"  NL bigram MI mean: {mean_mi:.4f} ± {std_mi:.4f}, VMS z={z_mi:.2f}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST E — LINE-POSITION SENSITIVITY
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST E — LINE-POSITION ENDING SENSITIVITY")
    pr("=" * 72)
    pr()

    n_chars = 2

    # VMS (using manuscript lines)
    vms_lp_mi, vms_lp_nmi, vms_lp_top, vms_lp_pos_ends = \
        line_position_ending_skew(vms_line_words, n_chars)

    pr(f"  VMS: MI(ending; line_pos) = {vms_lp_mi:.4f} bits, NMI={vms_lp_nmi:.4f}")
    for pos in ['initial', 'medial', 'final']:
        top = vms_lp_top.get(pos, [])
        top_str = ', '.join(f"-{e} ({100*p:.1f}%)" for e, c, p in top[:3])
        pr(f"    {pos:>8s}: {top_str}")
    pr()

    # Compute VMS parser-level suffix at line-final position
    line_final_parser_sfx = Counter()
    for _, _, ws in vms_lines:
        if ws:
            _, sfx = vms_parse_suffix(ws[-1])
            line_final_parser_sfx[sfx] += 1
    total_lf = sum(line_final_parser_sfx.values())
    pr("  VMS line-final parser suffix:")
    for sfx, n in line_final_parser_sfx.most_common(5):
        pr(f"    {sfx:>6s}: {n:5d} ({100*n/total_lf:5.1f}%)")
    pr()

    pr(f"  {'Language':>20s}  {'MI':>7s}  {'NMI':>7s}  {'Top final':>30s}")
    pr(f"  {'─'*20}  {'─'*7}  {'─'*7}  {'─'*30}")

    nl_lp_mis = []
    nl_lp_nmis = []
    for name, data in sorted(nl_corpora.items()):
        nl_lp_mi, nl_lp_nmi, nl_lp_top, _ = \
            line_position_ending_skew(data['lines'], n_chars)
        nl_lp_mis.append(nl_lp_mi)
        nl_lp_nmis.append(nl_lp_nmi)
        final_top = nl_lp_top.get('final', [])
        final_str = ', '.join(f"-{e} ({100*p:.0f}%)" for e, c, p in final_top[:3])
        pr(f"  {name:>20s}  {nl_lp_mi:7.4f}  {nl_lp_nmi:7.4f}  {final_str:>30s}")

    pr()
    if nl_lp_nmis:
        mean_nmi = np.mean(nl_lp_nmis)
        std_nmi = np.std(nl_lp_nmis)
        z_nmi = (vms_lp_nmi - mean_nmi) / std_nmi if std_nmi > 0 else 0
        pr(f"  NL position NMI mean: {mean_nmi:.4f} ± {std_nmi:.4f}, "
           f"VMS z={z_nmi:.2f}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # CRITICAL ASSESSMENT
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("CRITICAL ASSESSMENT")
    pr("=" * 72)
    pr()

    pr("Test A — Ending Inventory Shape:")
    pr("  See above for z-scores.  Key question: is VMS ending entropy")
    pr("  within the range of NL inflectional languages?")
    pr()

    pr("Test B — Paradigm Structure:")
    pr("  Key question: is VMS paradigm fill (endings per stem) compatible")
    pr("  with Latin's declension-class restriction?")
    pr()

    pr("Test C — Stem-Ending MI:")
    pr("  Key question: does VMS stem-ending coupling match Latin?")
    pr("  Low NMI = low stem-specificity (any stem takes any ending).")
    pr("  High NMI = strong stem-class restriction.")
    pr()

    pr("Test D — Ending Sequence Grammar:")
    pr("  Key question: does VMS ending→ending MI and agreement pattern")
    pr("  match Latin case-sequence grammar?")
    pr()

    pr("Test E — Line-Position Sensitivity:")
    pr("  Key question: does any NL language show comparable line-position")
    pr("  × ending skew?  VMS null-suffix clustering at line ends is the")
    pr("  strongest known positional effect.")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # SAVE
    # ═══════════════════════════════════════════════════════════════════
    results = {
        'vms': {
            'n_words': len(vms_words_flat),
            'parser_suffix_types': len(vms_parser_endings),
            'parser_suffix_H': entropy(vms_parser_endings),
            'parser_paradigm': vms_parser_para,
        },
        'test_results': {
            'note': 'See .txt output for full tables and analysis'
        }
    }

    out_json = RESULTS_DIR / 'latin_inflection_ending_test.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    pr(f"Results saved to {out_json}")

    out_txt = RESULTS_DIR / 'latin_inflection_ending_test.txt'
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))


if __name__ == '__main__':
    main()
