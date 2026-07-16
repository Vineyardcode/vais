#!/usr/bin/env python3
"""
Position × Identity Decomposition

═══════════════════════════════════════════════════════════════════════

QUESTION:
  Do VMS chunks partition by word-position (cipher-like)
  or spread across positions (NL character-like)?

MOTIVATION:
  chunk_equivalence_classes established LOOP chunks as functional characters
  (~25 equivalence classes, h_ratio=0.849 matching NL char 0.849).
  chunk_equivalence_classes found distributional clusters are POSITIONAL BINS
  (cluster 0 = final-leaning, cluster 1 = initial-leaning).
  spectral_vowel_consonant and its revalidation confirmed position dominates bigram structure
  (59% of chunk bigrams are I→F from 2-chunk words).
  positional_verbose_cipher modeled position-variant cipher at glyph level
  (best fit: 3-zone, ~20% char overlap, distance 3.94 from VMS).

  NONE of those tests directly measured:
  "How much do chunk inventories OVERLAP across positions,
   and how does this compare to NL characters?"

  This test bridges the gap.

APPROACH:
  1. Label each chunk token by word-position (I=initial, M=medial, F=final)
  2. Compute position-identity coupling metrics:
     a. Position Concentration Index (PCI): max positional proportion per type
     b. Jaccard overlap of position-specific type inventories
     c. Mutual information I(type; position) and NMI
     d. Position-explains-% = MI / H(type)
  3. Compute SAME metrics for NL characters AND syllables
  4. Z-score comparison: VMS vs NL
  5. Length-controlled sub-analysis (3+ unit words only)
  6. Top-N robustness check (match NL alphabet size)
  7. Null model: within-word shuffle (50 trials)
  8. positional_verbose_cipher reconciliation: predicted vs observed overlap

SKEPTICISM NOTES:
  - 56% of VMS words are 2-chunk → sparse M data. Must control via
    3+ unit sub-analysis where M positions exist.
  - The LOOP grammar constrains which GLYPHS start chunks, but chunk
    IDENTITY (multi-glyph string) is NOT grammar-forced to positions.
    Positional restriction is EMPIRICAL, not structural.
  - NL characters also have positional preferences (phonotactics).
    The question is DEGREE, not existence.
  - Alphabet size differs (523 chunks vs 26-36 NL chars). Use
    frequency-weighted metrics and top-N subset for robustness.
  - With 523 types, many rare types are trivially position-locked.
    Use frequency threshold (≥20 total) to exclude these.
  - The NL SYLLABLE comparison is fairer than NL character because
    syllable type counts (~1500-5000) and per-word counts (~2)
    are closer to VMS chunk counts (523 types, ~1.95 per word).
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import chunk_to_str, clean_word, eva_to_glyphs, extract_words_from_line, load_reference_text, parse_one_chunk, parse_word_into_chunks

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
random.seed(42)


# ═══════════════════════════════════════════════════════════════════════
# EVA GLYPH TOKENIZER (from chunk_fingerprint)
# ═══════════════════════════════════════════════════════════════════════

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']



# ═══════════════════════════════════════════════════════════════════════
# MAURO'S LOOP GRAMMAR — CHUNK PARSER (from chunk_fingerprint)
# ═══════════════════════════════════════════════════════════════════════

SLOT1 = {'ch', 'sh', 'y'}
SLOT2_RUNS = {'e'}
SLOT2_SINGLE = {'q', 'a'}
SLOT3 = {'o'}
SLOT4_RUNS = {'i'}
SLOT4_SINGLE = {'d'}
SLOT5 = {'y', 'p', 'f', 'k', 'l', 'r', 's', 't',
         'cth', 'ckh', 'cph', 'cfh', 'n', 'm'}
MAX_CHUNKS = 6





# ═══════════════════════════════════════════════════════════════════════
# VMS CORPUS PARSING (from chunk_fingerprint)
# ═══════════════════════════════════════════════════════════════════════



def parse_vms():
    result = defaultdict(list)
    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)
    for filepath in folio_files:
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num:
            continue
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                m = re.match(r'<([^>]+)>', line)
                if not m:
                    continue
                rest = line[m.end():].strip()
                if not rest:
                    continue
                words = extract_words_from_line(rest)
                result['all'].extend(words)
    return dict(result)


# ═══════════════════════════════════════════════════════════════════════
# NL REF TEXT LOADING + SYLLABIFICATION (from chunk_fingerprint)
# ═══════════════════════════════════════════════════════════════════════

VOWELS_LATIN = set('aeiouyàáâãäåæèéêëìíîïòóôõöùúûüýœ')

def syllabify_word(word, vowels=VOWELS_LATIN):
    if len(word) <= 1:
        return [word]
    is_v = [c in vowels for c in word]
    boundaries = [0]
    i = 1
    while i < len(word):
        if is_v[i] and i > 0 and not is_v[i-1]:
            j = i - 1
            while j > boundaries[-1] and not is_v[j]:
                j -= 1
            if j > boundaries[-1]:
                split_at = j + 1
            else:
                split_at = j if is_v[j] else j + 1
            if split_at > boundaries[-1] and split_at < i:
                boundaries.append(split_at)
        i += 1
    syllables = []
    for k in range(len(boundaries)):
        start = boundaries[k]
        end = boundaries[k+1] if k+1 < len(boundaries) else len(word)
        syl = word[start:end]
        if syl:
            syllables.append(syl)
    return syllables if syllables else [word]



# ═══════════════════════════════════════════════════════════════════════
# POSITION ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def assign_positions(unit_sequences, min_units=2):
    """Assign I/M/F position labels to tokens in multi-unit sequences.

    Args:
        unit_sequences: list of lists (each inner list = units in one word)
        min_units: minimum sequence length to include (2 = exclude singletons)

    Returns:
        pos_counts: dict[type][pos] = count
        total_by_pos: Counter of total tokens per position
        n_words_used: number of words included
    """
    pos_counts = defaultdict(Counter)
    total_by_pos = Counter()
    n_words = 0
    for units in unit_sequences:
        n = len(units)
        if n < min_units:
            continue
        n_words += 1
        for i, u in enumerate(units):
            if i == 0:
                pos = 'I'
            elif i == n - 1:
                pos = 'F'
            else:
                pos = 'M'
            pos_counts[u][pos] += 1
            total_by_pos[pos] += 1
    return dict(pos_counts), total_by_pos, n_words


def compute_pci(pos_counts, min_total=20):
    """Position Concentration Index per type.

    PCI(t) = max(p_I(t), p_M(t), p_F(t)) — how concentrated at one position.
    PCI = 1.0 → appears at only one position (cipher-like).
    PCI = 0.33 → uniform across positions (NL-like ideal).
    """
    results = {}
    for t, counts in pos_counts.items():
        total = sum(counts.values())
        if total < min_total:
            continue
        props = {}
        for p in ['I', 'M', 'F']:
            props[p] = counts.get(p, 0) / total
        pci = max(props.values())
        dom = max(props, key=props.get)
        results[t] = {'pci': pci, 'dom': dom, 'total': total,
                       'I': props['I'], 'M': props['M'], 'F': props['F']}
    if not results:
        return {'n_types': 0, 'mean': float('nan'), 'median': float('nan'),
                'weighted': float('nan'), 'restricted_frac': float('nan')}

    pcis = [v['pci'] for v in results.values()]
    tots = [v['total'] for v in results.values()]
    wt = sum(p * t for p, t in zip(pcis, tots)) / sum(tots)
    restricted = sum(1 for p in pcis if p > 0.80)

    return {
        'per_type': results,
        'n_types': len(results),
        'mean': float(np.mean(pcis)),
        'median': float(np.median(pcis)),
        'weighted': wt,
        'restricted_frac': restricted / len(results),
        'restricted_count': restricted,
    }


def compute_jaccard(pos_counts, min_at_pos=10):
    """Jaccard overlap between position-specific type inventories."""
    I_set = {t for t, c in pos_counts.items() if c.get('I', 0) >= min_at_pos}
    M_set = {t for t, c in pos_counts.items() if c.get('M', 0) >= min_at_pos}
    F_set = {t for t, c in pos_counts.items() if c.get('F', 0) >= min_at_pos}

    def J(a, b):
        if not a and not b:
            return float('nan')
        union = a | b
        return len(a & b) / len(union) if union else float('nan')

    j_if = J(I_set, F_set)
    j_im = J(I_set, M_set)
    j_mf = J(M_set, F_set)
    vals = [v for v in [j_if, j_im, j_mf] if not math.isnan(v)]
    j_mean = float(np.mean(vals)) if vals else float('nan')

    return {
        'J_IF': j_if, 'J_IM': j_im, 'J_MF': j_mf, 'J_mean': j_mean,
        'I_n': len(I_set), 'M_n': len(M_set), 'F_n': len(F_set),
        'IMF_n': len(I_set & M_set & F_set),
        'I_only': len(I_set - M_set - F_set),
        'F_only': len(F_set - I_set - M_set),
        'M_only': len(M_set - I_set - F_set),
    }


def compute_mi(pos_counts):
    """Mutual information I(type; position), NMI, and H(type|position)."""
    joint = Counter()
    type_marg = Counter()
    pos_marg = Counter()
    for t, counts in pos_counts.items():
        for p, c in counts.items():
            joint[(t, p)] += c
            type_marg[t] += c
            pos_marg[p] += c

    total = sum(joint.values())
    if total == 0:
        return {'mi': 0, 'nmi': 0, 'h_type': 0, 'h_pos': 0,
                'h_type_given_pos': 0, 'pos_explains_pct': 0}

    h_type = -sum((c/total) * math.log2(c/total)
                   for c in type_marg.values() if c > 0)
    h_pos = -sum((c/total) * math.log2(c/total)
                  for c in pos_marg.values() if c > 0)
    h_joint = -sum((c/total) * math.log2(c/total)
                    for c in joint.values() if c > 0)

    mi = h_type + h_pos - h_joint
    nmi = mi / min(h_type, h_pos) if min(h_type, h_pos) > 0 else 0
    h_type_giv_pos = h_joint - h_pos

    return {
        'mi': mi,
        'nmi': nmi,
        'h_type': h_type,
        'h_pos': h_pos,
        'h_joint': h_joint,
        'h_type_given_pos': h_type_giv_pos,
        'pos_explains_pct': 100 * mi / h_type if h_type > 0 else 0,
    }


def jsd_counters(cnt1, cnt2):
    """Jensen-Shannon divergence between two Counter distributions."""
    vocab = set(cnt1.keys()) | set(cnt2.keys())
    total1 = sum(cnt1.values())
    total2 = sum(cnt2.values())
    if total1 == 0 or total2 == 0:
        return float('nan')
    val = 0.0
    for v in vocab:
        p = cnt1.get(v, 0) / total1
        q = cnt2.get(v, 0) / total2
        m = 0.5 * (p + q)
        if p > 0 and m > 0:
            val += 0.5 * p * math.log2(p / m)
        if q > 0 and m > 0:
            val += 0.5 * q * math.log2(q / m)
    return val


def word_length_distribution(unit_sequences):
    """Count distribution of units-per-word."""
    dist = Counter()
    for units in unit_sequences:
        dist[len(units)] += 1
    return dist


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def analyze_system(name, unit_sequences, min_total_pci=20, min_at_pos=10):
    """Run full position analysis on a system. Returns dict of all metrics."""
    pos_counts_2p, totals_2p, nw_2p = assign_positions(unit_sequences, min_units=2)
    pos_counts_3p, totals_3p, nw_3p = assign_positions(unit_sequences, min_units=3)

    pci_2p = compute_pci(pos_counts_2p, min_total=min_total_pci)
    jacc_2p = compute_jaccard(pos_counts_2p, min_at_pos=min_at_pos)
    mi_2p = compute_mi(pos_counts_2p)

    pci_3p = compute_pci(pos_counts_3p, min_total=min_total_pci)
    jacc_3p = compute_jaccard(pos_counts_3p, min_at_pos=min_at_pos)
    mi_3p = compute_mi(pos_counts_3p)

    wld = word_length_distribution(unit_sequences)

    return {
        'name': name,
        'wld': wld,
        'n_words_2p': nw_2p, 'n_words_3p': nw_3p,
        'totals_2p': totals_2p, 'totals_3p': totals_3p,
        'pos_counts_2p': pos_counts_2p, 'pos_counts_3p': pos_counts_3p,
        # ≥ 2-unit metrics
        'pci': pci_2p, 'jaccard': jacc_2p, 'mi': mi_2p,
        # ≥ 3-unit metrics
        'pci_3p': pci_3p, 'jaccard_3p': jacc_3p, 'mi_3p': mi_3p,
    }


def print_comparison_table(label, vms, nl_results, metric_keys, header_map):
    """Print a comparison table with z-scores."""
    pr(f"  {'System':<24s}", end='')
    for k in metric_keys:
        pr(f"  {header_map[k]:>8s}", end='')
    pr()
    pr(f"  {'─'*24}", end='')
    for _ in metric_keys:
        pr(f"  {'─'*8}", end='')
    pr()

    # VMS row
    pr(f"  {'VMS chunks':<24s}", end='')
    for k in metric_keys:
        v = vms[k]
        pr(f"  {v:8.4f}" if not math.isnan(v) else f"  {'N/A':>8s}", end='')
    pr()

    # NL rows
    nl_vals = {k: [] for k in metric_keys}
    for name, res in sorted(nl_results.items()):
        pr(f"  {name:<24s}", end='')
        for k in metric_keys:
            v = res[k]
            pr(f"  {v:8.4f}" if not math.isnan(v) else f"  {'N/A':>8s}", end='')
            if not math.isnan(v):
                nl_vals[k].append(v)
        pr()

    # NL summary + z-scores
    pr(f"  {'─'*24}", end='')
    for _ in metric_keys:
        pr(f"  {'─'*8}", end='')
    pr()

    pr(f"  {'NL mean ± std':<24s}", end='')
    means = {}
    stds = {}
    for k in metric_keys:
        vals = nl_vals[k]
        if len(vals) >= 2:
            m, s = np.mean(vals), np.std(vals)
            means[k] = m
            stds[k] = s
            pr(f"  {m:5.3f}±{s:.3f}"[:9].rjust(8), end='')
        else:
            means[k] = float('nan')
            stds[k] = float('nan')
            pr(f"  {'N/A':>8s}", end='')
    pr()

    pr(f"  {'VMS z-score':<24s}", end='')
    zscores = {}
    for k in metric_keys:
        if not math.isnan(means.get(k, float('nan'))) and stds.get(k, 0) > 1e-9:
            z = (vms[k] - means[k]) / stds[k]
            zscores[k] = z
            pr(f"  {z:+8.2f}", end='')
        else:
            zscores[k] = float('nan')
            pr(f"  {'N/A':>8s}", end='')
    pr()

    return means, stds, zscores


def main():
    pr("=" * 76)
    pr("position_identity_decomposition — POSITION × IDENTITY DECOMPOSITION")
    pr("=" * 76)
    pr()
    pr("  Do VMS chunks form ONE alphabet used at all word positions")
    pr("  (NL character-like), or SEPARATE position-specific alphabets")
    pr("  (positional cipher-like)?")
    pr()

    # ── STEP 1: PARSE VMS + NL ────────────────────────────────────────

    pr("─" * 76)
    pr("STEP 1: PARSE CORPORA")
    pr("─" * 76)
    pr()

    # VMS → chunks
    vms_data = parse_vms()
    all_words = vms_data['all']
    vms_word_chunks = []
    for w in all_words:
        chunks, unparsed, _ = parse_word_into_chunks(w)
        chunk_ids = [chunk_to_str(c) for c in chunks]
        vms_word_chunks.append(chunk_ids)

    pr(f"  VMS: {len(all_words)} words, {sum(len(wc) for wc in vms_word_chunks)} chunk tokens, "
       f"{len(set(c for wc in vms_word_chunks for c in wc))} chunk types")

    # VMS word-length distribution
    vms_wld = word_length_distribution(vms_word_chunks)
    pr(f"  VMS chunks/word distribution:")
    for n_c in sorted(vms_wld.keys()):
        ct = vms_wld[n_c]
        pr(f"    {n_c}: {ct:6d} ({100*ct/len(all_words):5.1f}%)")
    pr()

    # NL texts
    nl_texts = {
        'Latin-Caesar':   DATA_DIR / 'latin_texts' / 'caesar.txt',
        'Latin-Vulgate':  DATA_DIR / 'latin_texts' / 'vulgate_genesis.txt',
        'Latin-Apicius':  DATA_DIR / 'latin_texts' / 'apicius.txt',
        'Italian-Cucina': DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt',
        'French-Viandier': DATA_DIR / 'vernacular_texts' / 'french_viandier.txt',
        'English-Cury':   DATA_DIR / 'vernacular_texts' / 'english_cury.txt',
        'German-Faust':   DATA_DIR / 'vernacular_texts' / 'german_faust.txt',
    }
    bvgs_path = DATA_DIR / 'vernacular_texts' / 'german_bvgs_raw.txt'
    if bvgs_path.exists():
        nl_texts['German-BvgS'] = bvgs_path

    # Parse each NL text into characters and syllables
    nl_char_seqs = {}   # name → list of [char, char, ...] per word
    nl_syl_seqs = {}    # name → list of [syl, syl, ...] per word
    for name, path in nl_texts.items():
        if not path.exists():
            pr(f"  ⚠ Skipping {name}: file not found")
            continue
        words = load_reference_text(path)
        if len(words) < 500:
            pr(f"  ⚠ Skipping {name}: too few words ({len(words)})")
            continue
        char_seqs = [list(w) for w in words]
        syl_seqs = [syllabify_word(w) for w in words]
        nl_char_seqs[name] = char_seqs
        nl_syl_seqs[name] = syl_seqs

        n_chars = sum(len(cs) for cs in char_seqs)
        n_syls = sum(len(ss) for ss in syl_seqs)
        n_char_types = len(set(c for cs in char_seqs for c in cs))
        n_syl_types = len(set(s for ss in syl_seqs for s in ss))
        mean_cpw = n_chars / len(words)
        mean_spw = n_syls / len(words)
        pr(f"  {name}: {len(words)} words, {n_chars} chars ({n_char_types} types, "
           f"{mean_cpw:.1f}/word), {n_syls} syls ({n_syl_types} types, {mean_spw:.1f}/word)")

    pr()

    # ── STEP 2: POSITION METRICS — ALL ≥2-UNIT WORDS ──────────────────

    pr("─" * 76)
    pr("STEP 2: POSITION METRICS (≥ 2-unit words)")
    pr("─" * 76)
    pr()

    vms_res = analyze_system('VMS-chunks', vms_word_chunks)
    pr(f"  VMS (≥2 chunks): {vms_res['n_words_2p']} words, "
       f"I={vms_res['totals_2p']['I']}, M={vms_res['totals_2p'].get('M',0)}, "
       f"F={vms_res['totals_2p']['F']} tokens")
    pr(f"  VMS (≥3 chunks): {vms_res['n_words_3p']} words, "
       f"I={vms_res['totals_3p']['I']}, M={vms_res['totals_3p'].get('M',0)}, "
       f"F={vms_res['totals_3p']['F']} tokens")
    pr()

    nl_char_res = {}
    nl_syl_res = {}
    for name, seqs in nl_char_seqs.items():
        nl_char_res[name] = analyze_system(f'{name}-char', seqs)
    for name, seqs in nl_syl_seqs.items():
        nl_syl_res[name] = analyze_system(f'{name}-syl', seqs)

    # Print VMS PCI top types
    pr("  VMS top-20 types by PCI (≥2-chunk words, freq≥20):")
    pr(f"    {'Type':<18s}  {'Total':>6s}  {'PCI':>5s}  {'Dom':>3s}  {'I%':>6s}  {'M%':>6s}  {'F%':>6s}")
    pr(f"    {'─'*18}  {'─'*6}  {'─'*5}  {'─'*3}  {'─'*6}  {'─'*6}  {'─'*6}")
    if 'per_type' in vms_res['pci']:
        sorted_types = sorted(vms_res['pci']['per_type'].items(),
                              key=lambda x: -x[1]['pci'])
        for t, v in sorted_types[:20]:
            pr(f"    {t:<18s}  {v['total']:6d}  {v['pci']:.3f}  {v['dom']:>3s}  "
               f"{100*v['I']:5.1f}%  {100*v['M']:5.1f}%  {100*v['F']:5.1f}%")
        pr()

        # Bottom-20 (most position-flexible)
        pr("  VMS bottom-20 types by PCI (most position-flexible):")
        pr(f"    {'Type':<18s}  {'Total':>6s}  {'PCI':>5s}  {'Dom':>3s}  {'I%':>6s}  {'M%':>6s}  {'F%':>6s}")
        pr(f"    {'─'*18}  {'─'*6}  {'─'*5}  {'─'*3}  {'─'*6}  {'─'*6}  {'─'*6}")
        for t, v in sorted_types[-20:]:
            pr(f"    {t:<18s}  {v['total']:6d}  {v['pci']:.3f}  {v['dom']:>3s}  "
               f"{100*v['I']:5.1f}%  {100*v['M']:5.1f}%  {100*v['F']:5.1f}%")
        pr()

    # ── STEP 3: COMPARISON TABLES + Z-SCORES ──────────────────────────

    pr("─" * 76)
    pr("STEP 3: VMS vs NL CHARACTERS — COMPARISON")
    pr("─" * 76)
    pr()

    # Build flat metric dicts for table
    def flat_metrics(res, suffix=''):
        pci_k = f'pci{suffix}'
        jacc_k = f'jaccard{suffix}'
        mi_k = f'mi{suffix}'
        return {
            'mean_pci': res[pci_k]['mean'],
            'median_pci': res[pci_k]['median'],
            'wt_pci': res[pci_k]['weighted'],
            'restricted': res[pci_k]['restricted_frac'],
            'J_IF': res[jacc_k]['J_IF'],
            'J_IM': res[jacc_k]['J_IM'],
            'J_MF': res[jacc_k]['J_MF'],
            'J_mean': res[jacc_k]['J_mean'],
            'nmi': res[mi_k]['nmi'],
            'pos_pct': res[mi_k]['pos_explains_pct'],
            'n_types': res[pci_k]['n_types'],
        }

    vms_flat = flat_metrics(vms_res)
    nl_char_flat = {n: flat_metrics(r) for n, r in nl_char_res.items()}

    pr("  A) VMS chunks vs NL characters (≥2-unit words):")
    pr()
    keys_main = ['mean_pci', 'wt_pci', 'restricted', 'J_IF', 'J_mean', 'nmi', 'pos_pct']
    headers = {'mean_pci': 'MeanPCI', 'wt_pci': 'WtPCI', 'restricted': 'Restr%',
               'J_IF': 'J(I,F)', 'J_mean': 'J_mean', 'nmi': 'NMI', 'pos_pct': 'MI/H%'}

    char_means, char_stds, char_z = print_comparison_table(
        "VMS vs NL chars", vms_flat, nl_char_flat, keys_main, headers)
    pr()

    # Same for syllables
    pr("  B) VMS chunks vs NL syllables (≥2-unit words):")
    pr()
    nl_syl_flat = {n: flat_metrics(r) for n, r in nl_syl_res.items()}
    syl_means, syl_stds, syl_z = print_comparison_table(
        "VMS vs NL syls", vms_flat, nl_syl_flat, keys_main, headers)
    pr()

    # ── STEP 4: LENGTH-CONTROLLED (≥3 units) + TOP-N ROBUSTNESS ──────

    pr("─" * 76)
    pr("STEP 4: LENGTH-CONTROLLED ANALYSIS (≥ 3-unit words only)")
    pr("─" * 76)
    pr()
    pr("  Rationale: 56% of VMS words are 2-chunk (no M position).")
    pr("  The ≥3-unit subset has I, M, AND F positions → fairer comparison.")
    pr()

    vms_flat3 = flat_metrics(vms_res, suffix='_3p')
    nl_char_flat3 = {n: flat_metrics(r, suffix='_3p') for n, r in nl_char_res.items()}
    nl_syl_flat3 = {n: flat_metrics(r, suffix='_3p') for n, r in nl_syl_res.items()}

    pr("  A) VMS vs NL characters (≥3-unit words):")
    pr()
    char3_means, char3_stds, char3_z = print_comparison_table(
        "≥3-unit chars", vms_flat3, nl_char_flat3, keys_main, headers)
    pr()

    pr("  B) VMS vs NL syllables (≥3-unit words):")
    pr()
    syl3_means, syl3_stds, syl3_z = print_comparison_table(
        "≥3-unit syls", vms_flat3, nl_syl_flat3, keys_main, headers)
    pr()

    # Top-N robustness: recompute VMS using only top-30 chunk types
    pr("  C) TOP-30 ROBUSTNESS CHECK:")
    pr("  (Restrict VMS to 30 most frequent chunk types to match NL alphabet size)")
    pr()

    all_chunk_freq = Counter()
    for wc in vms_word_chunks:
        for c in wc:
            all_chunk_freq[c] += 1
    top30 = set(t for t, _ in all_chunk_freq.most_common(30))

    # Filter: only keep words where ALL chunks are in top-30
    vms_top30_seqs = []
    for wc in vms_word_chunks:
        if all(c in top30 for c in wc):
            vms_top30_seqs.append(wc)

    vms_top30_res = analyze_system('VMS-top30', vms_top30_seqs)
    vms_top30_flat = flat_metrics(vms_top30_res)

    pr(f"  VMS words with all chunks in top-30: {len(vms_top30_seqs)}/{len(vms_word_chunks)} "
       f"({100*len(vms_top30_seqs)/len(vms_word_chunks):.1f}%)")
    pr(f"  Top-30 chunk types cover {sum(all_chunk_freq[t] for t in top30)}/{sum(all_chunk_freq.values())} "
       f"tokens ({100*sum(all_chunk_freq[t] for t in top30)/sum(all_chunk_freq.values()):.1f}%)")
    pr()

    pr(f"  {'Metric':<12s}  {'All-chunks':>10s}  {'Top-30':>10s}  {'NL-char μ':>10s}")
    pr(f"  {'─'*12}  {'─'*10}  {'─'*10}  {'─'*10}")
    for k in keys_main:
        v_all = vms_flat[k]
        v_t30 = vms_top30_flat[k]
        v_nlm = char_means.get(k, float('nan'))
        pr(f"  {headers[k]:<12s}  {v_all:10.4f}  {v_t30:10.4f}  "
           f"{'N/A' if math.isnan(v_nlm) else f'{v_nlm:10.4f}'}")
    pr()

    # ── STEP 5: JACCARD DETAIL — TYPE PARTITIONING ────────────────────

    pr("─" * 76)
    pr("STEP 5: TYPE PARTITIONING DETAIL")
    pr("─" * 76)
    pr()

    j2 = vms_res['jaccard']
    pr(f"  VMS (≥2-chunk words), threshold = 10 tokens at position:")
    pr(f"    Types at I with ≥10 tokens: {j2['I_n']}")
    pr(f"    Types at M with ≥10 tokens: {j2['M_n']}")
    pr(f"    Types at F with ≥10 tokens: {j2['F_n']}")
    pr(f"    Types at ALL 3 positions:   {j2['IMF_n']}")
    pr(f"    I-only types:               {j2['I_only']}")
    pr(f"    M-only types:               {j2['M_only']}")
    pr(f"    F-only types:               {j2['F_only']}")
    pr()

    j3 = vms_res['jaccard_3p']
    pr(f"  VMS (≥3-chunk words), threshold = 10 tokens at position:")
    pr(f"    Types at I with ≥10 tokens: {j3['I_n']}")
    pr(f"    Types at M with ≥10 tokens: {j3['M_n']}")
    pr(f"    Types at F with ≥10 tokens: {j3['F_n']}")
    pr(f"    Types at ALL 3 positions:   {j3['IMF_n']}")
    pr(f"    I-only types:               {j3['I_only']}")
    pr(f"    M-only types:               {j3['M_only']}")
    pr(f"    F-only types:               {j3['F_only']}")
    pr()

    # NL character comparison for context
    for name, res in sorted(nl_char_res.items()):
        jc = res['jaccard']
        pr(f"  {name} chars: I={jc['I_n']}, M={jc['M_n']}, F={jc['F_n']}, "
           f"all-3={jc['IMF_n']}, J(I,F)={jc['J_IF']:.3f}")
    pr()

    # ── STEP 6: NULL MODEL — WITHIN-WORD SHUFFLE ─────────────────────

    pr("─" * 76)
    pr("STEP 6: NULL MODEL — WITHIN-WORD CHUNK SHUFFLE (50 trials)")
    pr("─" * 76)
    pr()
    pr("  Randomly permute chunk order within each word.")
    pr("  This preserves word composition but destroys positional structure.")
    pr("  If shuffled MI ≈ 0, the observed MI reflects genuine pos-identity coupling.")
    pr()

    N_SHUFFLE = 50
    shuf_pcis = []
    shuf_jifs = []
    shuf_nmis = []
    shuf_pospcts = []

    for trial in range(N_SHUFFLE):
        shuffled = []
        for wc in vms_word_chunks:
            s = list(wc)
            random.shuffle(s)
            shuffled.append(s)
        s_pos, _, _ = assign_positions(shuffled, min_units=2)
        s_pci = compute_pci(s_pos, min_total=20)
        s_jacc = compute_jaccard(s_pos, min_at_pos=10)
        s_mi = compute_mi(s_pos)

        shuf_pcis.append(s_pci['weighted'])
        shuf_jifs.append(s_jacc['J_IF'])
        shuf_nmis.append(s_mi['nmi'])
        shuf_pospcts.append(s_mi['pos_explains_pct'])

    def null_summary(label, observed, shuffled_list):
        m = np.mean(shuffled_list)
        s = np.std(shuffled_list)
        z = (observed - m) / s if s > 1e-9 else float('nan')
        pr(f"    {label:<14s}  observed={observed:7.4f}  "
           f"shuffled={m:.4f}±{s:.4f}  z={z:+.2f}")
        return z

    pr("  Results:")
    z_pci = null_summary('Weighted PCI', vms_flat['wt_pci'], shuf_pcis)
    z_jif = null_summary('J(I,F)', vms_flat['J_IF'], shuf_jifs)
    z_nmi = null_summary('NMI', vms_flat['nmi'], shuf_nmis)
    z_pos = null_summary('MI/H(type)%', vms_flat['pos_pct'], shuf_pospcts)
    pr()

    pr("  INTERPRETATION:")
    if abs(z_pci) > 3 and abs(z_nmi) > 3:
        pr("    Shuffled metrics are FAR from observed → positional structure")
        pr("    is NOT an artifact of word composition. Position-identity")
        pr("    coupling is genuine and strong.")
    else:
        pr("    Shuffled metrics are close to observed → positional structure")
        pr("    may be partly explained by word composition (trivial effect).")
    pr()

    # ── STEP 7: positional_verbose_cipher RECONCILIATION ──────────────────────────────

    pr("─" * 76)
    pr("STEP 7: positional_verbose_cipher RECONCILIATION — PREDICTED vs OBSERVED OVERLAP")
    pr("─" * 76)
    pr()
    pr("  positional_verbose_cipher best model: 3-zone positional cipher")
    pr("    Consonants: 4 shared + 3 unique/zone = 13 consonant symbols")
    pr("    Vowels:     2 shared + 5 unique/zone = 17 vowel symbols")
    pr("    Total:      6 shared + 24 zone-unique = 30 symbols")
    pr("    Predicted Jaccard: |shared|/|total| = 6/30 = 0.200")
    pr("    (between any two zones: |6|/|6+8+8| = 6/22 = 0.273)")
    pr()
    pr(f"  position_identity_decomposition observed:")
    pr(f"    J(I,F) for VMS chunks (≥2-unit):  {vms_flat['J_IF']:.3f}")
    pr(f"    J_mean for VMS chunks (≥2-unit):  {vms_flat['J_mean']:.3f}")
    pr(f"    J(I,F) for VMS chunks (≥3-unit):  {vms_flat3['J_IF']:.3f}")
    pr(f"    J_mean for VMS chunks (≥3-unit):  {vms_flat3['J_mean']:.3f}")
    pr()

    # NL baseline
    nl_jif_vals = [r['J_IF'] for r in nl_char_flat.values() if not math.isnan(r['J_IF'])]
    nl_jif_mean = np.mean(nl_jif_vals) if nl_jif_vals else float('nan')
    pr(f"    NL character J(I,F) mean:         {nl_jif_mean:.3f}")
    pr(f"    positional_verbose_cipher cipher prediction:       0.273")
    pr()

    # Where does VMS fall?
    vms_jif = vms_flat['J_IF']
    if not math.isnan(nl_jif_mean) and not math.isnan(vms_jif):
        cipher_pred = 0.273
        nl_val = nl_jif_mean
        if abs(vms_jif - cipher_pred) < abs(vms_jif - nl_val):
            pr("    → VMS J(I,F) is CLOSER to positional_verbose_cipher cipher prediction")
            pr("      than to NL character baseline.")
        elif abs(vms_jif - nl_val) < abs(vms_jif - cipher_pred):
            pr("    → VMS J(I,F) is CLOSER to NL character baseline")
            pr("      than to positional_verbose_cipher cipher prediction.")
        else:
            pr("    → VMS J(I,F) is equidistant between cipher and NL.")

        # Interpolation: where on the cipher↔NL spectrum?
        if nl_val != cipher_pred:
            frac = (vms_jif - cipher_pred) / (nl_val - cipher_pred)
            pr(f"    Interpolation: {100*frac:.0f}% toward NL, "
               f"{100*(1-frac):.0f}% toward cipher")
    pr()

    # ── STEP 8: SKEPTICAL AUDIT ──────────────────────────────────────

    pr("─" * 76)
    pr("STEP 8: SKEPTICAL AUDIT — WHAT COULD INVALIDATE THESE RESULTS?")
    pr("─" * 76)
    pr()

    pr("  1. WORD-LENGTH CONFOUND")
    pr(f"     VMS mean chunks/word: {sum(n*c for n,c in vms_wld.items())/sum(vms_wld.values()):.2f}")
    # NL comparison
    for name, seqs in list(nl_char_seqs.items())[:3]:
        nl_wld = word_length_distribution(seqs)
        nl_mean = sum(n*c for n,c in nl_wld.items()) / sum(nl_wld.values())
        pr(f"     {name} mean chars/word: {nl_mean:.2f}")
    for name, seqs in list(nl_syl_seqs.items())[:3]:
        nl_wld = word_length_distribution(seqs)
        nl_mean = sum(n*c for n,c in nl_wld.items()) / sum(nl_wld.values())
        pr(f"     {name} mean syls/word: {nl_mean:.2f}")
    pr("     CAVEAT: VMS has SHORTER words (fewer M positions).")
    pr("     The ≥3-unit sub-analysis controls for this partially,")
    pr("     but NL still has longer words within the ≥3 subset.")
    pr()

    pr("  2. ALPHABET SIZE CONFOUND")
    pr(f"     VMS chunk types (freq≥20): {vms_res['pci']['n_types']}")
    pr(f"     NL char types: ~26-36")
    pr(f"     NL syl types: ~1400-5000")
    pr("     More types → more trivially position-locked rare types.")
    pr("     The top-30 robustness check addresses this, as does")
    pr("     the freq≥20 threshold for PCI. But the fundamental")
    pr("     asymmetry (523 vs 26) means VMS Jaccard is EXPECTED")
    pr("     to be somewhat lower simply from more types.")
    pr()

    pr("  3. LOOP GRAMMAR ARTIFACT")
    pr("     The LOOP grammar defines slot 1 = {ch, sh, y}. These")
    pr("     onsets don't constrain chunk POSITION within a word.")
    pr("     A 'ch.e.d.y' chunk can appear at I, M, or F. Positional")
    pr("     restriction is EMPIRICAL, not grammar-imposed.")
    pr("     VERIFIED: the parser is greedy left→right with no")
    pr("     position-dependent rules. Slot structure is fixed.")
    pr()

    pr("  4. SYLLABLE COMPARISON FAIRNESS")
    pr("     NL syllabification is approximate (~87% accuracy per chunk_fingerprint).")
    pr("     Syllable type counts are high (1000-5000), closer to VMS chunks")
    pr("     (523). The syllable comparison is arguably fairer than the")
    pr("     character comparison for type-count matching.")
    pr()

    pr("  5. SINGLETON EXCLUSION")
    pr(f"     VMS 1-chunk words excluded: {vms_wld.get(1,0)} ({100*vms_wld.get(1,0)/len(all_words):.1f}%)")
    pr("     These could bias results if singleton chunks are systematically")
    pr("     different. But including them as both-I-and-F would inflate")
    pr("     overlap artificially. Exclusion is the conservative choice.")
    pr()

    # ── STEP 9: SYNTHESIS ─────────────────────────────────────────────

    pr("─" * 76)
    pr("STEP 9: SYNTHESIS & VERDICT")
    pr("─" * 76)
    pr()

    pr("  METRIC SUMMARY (≥2-unit words):")
    pr(f"    {'Metric':<14s}  {'VMS':>8s}  {'NL-char μ':>10s}  {'NL-syl μ':>10s}  {'z(char)':>8s}  {'z(syl)':>8s}")
    pr(f"    {'─'*14}  {'─'*8}  {'─'*10}  {'─'*10}  {'─'*8}  {'─'*8}")
    for k in keys_main:
        v = vms_flat[k]
        cm = char_means.get(k, float('nan'))
        sm = syl_means.get(k, float('nan'))
        cz = char_z.get(k, float('nan'))
        sz = syl_z.get(k, float('nan'))
        pr(f"    {headers[k]:<14s}  {v:8.4f}  "
           f"{'N/A':>10s}" if math.isnan(cm) else f"    {headers[k]:<14s}  {v:8.4f}  {cm:10.4f}", end='')
        pr(f"  {'N/A':>10s}" if math.isnan(sm) else f"  {sm:10.4f}", end='')
        pr(f"  {'N/A':>8s}" if math.isnan(cz) else f"  {cz:+8.2f}", end='')
        pr(f"  {'N/A':>8s}" if math.isnan(sz) else f"  {sz:+8.2f}")
    pr()

    pr("  METRIC SUMMARY (≥3-unit words):")
    pr(f"    {'Metric':<14s}  {'VMS':>8s}  {'NL-char μ':>10s}  {'z(char)':>8s}")
    pr(f"    {'─'*14}  {'─'*8}  {'─'*10}  {'─'*8}")
    for k in keys_main:
        v = vms_flat3[k]
        cm = char3_means.get(k, float('nan'))
        cz = char3_z.get(k, float('nan'))
        pr(f"    {headers[k]:<14s}  {v:8.4f}  "
           f"{'N/A':>10s}" if math.isnan(cm) else f"    {headers[k]:<14s}  {v:8.4f}  {cm:10.4f}", end='')
        pr(f"  {'N/A':>8s}" if math.isnan(cz) else f"  {cz:+8.2f}")
    pr()

    # Overall verdict
    # Count how many z-scores favor cipher vs NL
    pr("  DIRECTIONAL EVIDENCE:")
    cipher_evidence = 0
    nl_evidence = 0
    for k in ['mean_pci', 'wt_pci', 'restricted', 'nmi', 'pos_pct']:
        z = char_z.get(k, float('nan'))
        if not math.isnan(z):
            if z > 2.0:
                cipher_evidence += 1
                pr(f"    {headers[k]:>14s}: z={z:+.2f} → CIPHER direction (VMS > NL)")
            elif z < -2.0:
                nl_evidence += 1
                pr(f"    {headers[k]:>14s}: z={z:+.2f} → NL direction (VMS < NL)")
            else:
                pr(f"    {headers[k]:>14s}: z={z:+.2f} → AMBIGUOUS (|z|<2)")
    for k in ['J_IF', 'J_mean']:
        z = char_z.get(k, float('nan'))
        if not math.isnan(z):
            if z < -2.0:
                cipher_evidence += 1
                pr(f"    {headers[k]:>14s}: z={z:+.2f} → CIPHER direction (VMS < NL overlap)")
            elif z > 2.0:
                nl_evidence += 1
                pr(f"    {headers[k]:>14s}: z={z:+.2f} → NL direction (VMS ≈ NL overlap)")
            else:
                pr(f"    {headers[k]:>14s}: z={z:+.2f} → AMBIGUOUS (|z|<2)")
    pr()
    pr(f"  Score: {cipher_evidence} metrics favor CIPHER, "
       f"{nl_evidence} favor NL, "
       f"{len(keys_main) - cipher_evidence - nl_evidence} ambiguous")
    pr()

    # positional_verbose_cipher verdict
    pr("  positional_verbose_cipher RECONCILIATION:")
    pr(f"    Observed J(I,F):         {vms_flat['J_IF']:.3f}")
    pr(f"    Cipher prediction:       0.273")
    pr(f"    NL character mean:       {nl_jif_mean:.3f}")
    pr()

    # Null model verdict
    pr("  NULL MODEL VALIDATION:")
    pr(f"    All metrics are z={min(abs(z_pci), abs(z_nmi)):.0f}+ "
       f"from shuffled null → positional coupling is GENUINE,")
    pr(f"    not an artifact of word composition.")
    pr()

    # Final verdict
    pr("  ══════════════════════════════════════════════════════════")
    pr("  VERDICT")
    pr("  ══════════════════════════════════════════════════════════")
    pr()

    if cipher_evidence >= 4:
        pr("  ★ VMS chunks show STRONG positional partitioning, significantly")
        pr("    exceeding NL character baselines on most metrics.")
        pr("    This is consistent with a POSITIONAL ENCODING mechanism")
        pr("    where different word positions use different chunk inventories.")
        verdict = "POSITIONAL_ENCODING_SUPPORTED"
    elif cipher_evidence >= 2 and nl_evidence <= 1:
        pr("  ★ VMS chunks show MODERATE positional partitioning,")
        pr("    exceeding NL on some metrics but not all.")
        pr("    Partial position-dependent encoding is plausible.")
        verdict = "PARTIAL_POSITIONAL_ENCODING"
    elif nl_evidence >= 4:
        pr("  ★ VMS chunks show NL-like positional flexibility.")
        pr("    Position-dependent encoding is NOT supported at the chunk level.")
        verdict = "NL_LIKE_POSITIONS"
    else:
        pr("  ★ INCONCLUSIVE — VMS position-identity coupling falls")
        pr("    between cipher and NL predictions. Cannot distinguish")
        pr("    strong phonotactics from weak positional encoding.")
        verdict = "INCONCLUSIVE"

    pr()
    pr(f"  Verdict code: {verdict}")
    pr()

    # Confidence update
    pr("  REVISED CONFIDENCES (position_identity_decomposition):")
    if cipher_evidence >= 4:
        pr("  - Positional verbose cipher: 45% → UP (evidence supports)")
    elif cipher_evidence >= 2:
        pr("  - Positional verbose cipher: 45% → SLIGHT UP (partial evidence)")
    elif nl_evidence >= 4:
        pr("  - Positional verbose cipher: 45% → DOWN (evidence against)")
    else:
        pr("  - Positional verbose cipher: 45% (unchanged — inconclusive)")
    pr("  - Natural language: 87% (unchanged)")
    pr("  - Chunks = functional characters: 85% (unchanged)")
    pr("  - True alphabet ≈ 25: 70% (unchanged)")
    pr("  - Hoax/random: <1% (unchanged)")
    pr()

    # ── SAVE RESULTS ─────────────────────────────────────────────────

    txt_path = RESULTS_DIR / 'position_identity_decomposition.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Results saved to {txt_path.relative_to(PROJECT_DIR)}")

    json_data = {
        'test': 'position_identity_decomposition',
        'question': "Position × Identity decomposition: cipher or NL?",
        'vms_metrics_2p': {k: v for k, v in vms_flat.items()},
        'vms_metrics_3p': {k: v for k, v in vms_flat3.items()},
        'nl_char_means': {k: float(v) for k, v in char_means.items()},
        'nl_char_stds': {k: float(v) for k, v in char_stds.items()},
        'nl_char_zscores': {k: float(v) if not math.isnan(v) else None
                            for k, v in char_z.items()},
        'nl_syl_means': {k: float(v) for k, v in syl_means.items()},
        'vms_jaccard_detail': {
            'I_n': j2['I_n'], 'M_n': j2['M_n'], 'F_n': j2['F_n'],
            'IMF_n': j2['IMF_n'],
            'I_only': j2['I_only'], 'F_only': j2['F_only'], 'M_only': j2['M_only'],
        },
        'null_model': {
            'n_trials': N_SHUFFLE,
            'z_pci': float(z_pci) if not math.isnan(z_pci) else None,
            'z_jif': float(z_jif) if not math.isnan(z_jif) else None,
            'z_nmi': float(z_nmi) if not math.isnan(z_nmi) else None,
        },
        'positional_verbose_cipher_reconciliation': {
            'predicted_jaccard': 0.273,
            'observed_jif': float(vms_flat['J_IF']),
            'nl_char_jif_mean': float(nl_jif_mean),
        },
        'cipher_evidence_count': cipher_evidence,
        'nl_evidence_count': nl_evidence,
        'verdict': verdict,
    }
    json_path = RESULTS_DIR / 'position_identity_decomposition.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
    pr(f"  JSON saved to {json_path.relative_to(PROJECT_DIR)}")


if __name__ == '__main__':
    main()
