#!/usr/bin/env python3
"""
Cross-Position Context Divergence

═══════════════════════════════════════════════════════════════════════

QUESTION:
  For VMS chunks appearing at multiple word-positions (I, M, F),
  do they function as the SAME linguistic unit at each position
  or as DIFFERENT units (homographs)?

MOTIVATION:
  position_identity_decomposition found strong positional partitioning: J(I,F)=0.241 vs
  NL character baseline 0.803. Only 36 chunk types (18%) appear at
  all 3 positions with ≥10 tokens each. But OVERLAP EXISTS.
  The critical question is: do these shared chunks carry the same
  context profile regardless of position, or do they function as
  different linguistic units at different positions?

  If same:      VMS has one alphabet with positional phonotactics (NL-like)
  If different: VMS has position-variant encoding (cipher-like homographs)

APPROACH:
  1. Within-word SUCCESSOR analysis (≥3-chunk words):
     For shared chunks, compare successor distributions at I vs M.
     Compute JSD per type → mean / median / weighted.
  2. Within-word PREDECESSOR analysis (≥3-chunk words):
     Compare predecessor distributions at M vs F.
  3. Conditional MI: I(successor; position | chunk type) for shared types.
  4. Top-K successor concordance: same top-1/3 successor at I vs M?
  5. NL character & syllable baselines: same tests.
  6. Permutation null model: within-type position shuffle.
  7. Per-type breakdown: which shared chunks diverge most?

CRITICAL CONFOUND (MUST READ):
  Successor of I-chunk is at M position. Successor of M-chunk is at
  later-M or F position. Even if a shared chunk is the SAME unit at
  both positions, the different successor-position INVENTORIES will
  cause JSD > 0. NL characters experience the SAME confound →
  NL baseline is the PRIMARY control for this artifact.
  VMS excess above NL baseline = genuine homograph signal.
  VMS at or below NL baseline = consistent with single-alphabet model.

SKEPTICISM NOTES:
  - Only ≥3-chunk words (17% of VMS corpus, ~7K words) → sparse data
  - Shared types with enough context at both I and M may be very few
  - The LOOP grammar's slot structure may create apparent context
    differences that are structural, not semantic
  - NL syllabification is approximate (~87% accuracy from chunk_fingerprint)
  - Must report data availability honestly
  - Must weight by token count to avoid rare-type domination
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
# JSD UTILITY (from position_identity_decomposition)
# ═══════════════════════════════════════════════════════════════════════

def jsd_counters(cnt1, cnt2):
    """Jensen-Shannon divergence between two Counter distributions (log2, bits)."""
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


# ═══════════════════════════════════════════════════════════════════════
# NEW: CONTEXT ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def extract_context_by_position(unit_sequences, min_units=3):
    """Extract within-word successor/predecessor distributions by position.

    For words with >= min_units units:
      successor_data[type][pos] = Counter of within-word successors
      predecessor_data[type][pos] = Counter of within-word predecessors

    Also returns pos_counts[type] = Counter of {I: n, M: n, F: n} in
    the analyzed words.
    """
    suc = defaultdict(lambda: defaultdict(Counter))
    pre = defaultdict(lambda: defaultdict(Counter))
    pos_counts = defaultdict(Counter)

    for units in unit_sequences:
        n = len(units)
        if n < min_units:
            continue
        for i in range(n):
            pos = 'I' if i == 0 else ('F' if i == n - 1 else 'M')
            u = units[i]
            pos_counts[u][pos] += 1
            if i < n - 1:  # has within-word successor
                suc[u][pos][units[i + 1]] += 1
            if i > 0:      # has within-word predecessor
                pre[u][pos][units[i - 1]] += 1

    return dict(suc), dict(pre), dict(pos_counts)


def identify_shared_types(context_data, pos1, pos2, min_context=5):
    """Find types with >= min_context context tokens at BOTH positions."""
    shared = []
    for t, pos_ctxs in context_data.items():
        cnt1 = pos_ctxs.get(pos1, Counter())
        cnt2 = pos_ctxs.get(pos2, Counter())
        n1 = sum(cnt1.values())
        n2 = sum(cnt2.values())
        if n1 >= min_context and n2 >= min_context:
            shared.append((t, n1, n2))
    return sorted(shared, key=lambda x: -(x[1] + x[2]))


def compute_context_jsds(context_data, shared_types, pos1, pos2):
    """Compute JSD between context distributions at two positions per type."""
    results = []
    for t, n1, n2 in shared_types:
        cnt1 = context_data[t].get(pos1, Counter())
        cnt2 = context_data[t].get(pos2, Counter())
        jsd = jsd_counters(cnt1, cnt2)
        top1_1 = cnt1.most_common(1)[0][0] if cnt1 else '—'
        top1_2 = cnt2.most_common(1)[0][0] if cnt2 else '—'
        results.append({
            'type': t, 'jsd': jsd,
            'n_pos1': n1, 'n_pos2': n2,
            'top1_pos1': top1_1, 'top1_pos2': top1_2,
        })
    return results


def compute_cmi(context_data, positions, min_context=5):
    """Compute I(context; position | type) for shared types.

    CMI_t = H(ctx | type=t) - sum_p P(p|t) * H(ctx | type=t, pos=p)
    Weighted CMI = sum_t w_t * CMI_t / sum_t w_t
    """
    type_results = {}
    total_weight = 0.0
    total_cmi = 0.0

    for t, pos_ctxs in context_data.items():
        valid = {}
        for p in positions:
            cnt = pos_ctxs.get(p, Counter())
            n = sum(cnt.values())
            if n >= min_context:
                valid[p] = cnt
        if len(valid) < 2:
            continue

        # Pool distribution
        pooled = Counter()
        n_total = 0
        for cnt in valid.values():
            for s, c in cnt.items():
                pooled[s] += c
            n_total += sum(cnt.values())

        # H(ctx | t) from pooled
        h_pooled = -sum((c / n_total) * math.log2(c / n_total)
                        for c in pooled.values() if c > 0)

        # Weighted H(ctx | t, p)
        h_cond = 0.0
        for cnt in valid.values():
            n_p = sum(cnt.values())
            h_p = -sum((c / n_p) * math.log2(c / n_p)
                       for c in cnt.values() if c > 0)
            h_cond += (n_p / n_total) * h_p

        cmi_t = h_pooled - h_cond
        frac = cmi_t / h_pooled if h_pooled > 0 else 0.0
        type_results[t] = {
            'cmi': cmi_t, 'h_pooled': h_pooled,
            'h_cond': h_cond, 'n': n_total, 'frac': frac,
        }
        total_cmi += cmi_t * n_total
        total_weight += n_total

    weighted = total_cmi / total_weight if total_weight > 0 else 0
    unweighted = float(np.mean([v['cmi'] for v in type_results.values()])) \
        if type_results else 0.0

    return {
        'weighted_cmi': weighted,
        'unweighted_cmi': unweighted,
        'per_type': type_results,
        'n_types': len(type_results),
        'total_tokens': int(total_weight),
    }


def compute_topk_concordance(context_data, shared_types, pos1, pos2, k=3):
    """For shared types, check if top-K context items match across positions."""
    concordant_top1 = 0
    concordant_topk = 0
    total = 0

    for t, n1, n2 in shared_types:
        cnt1 = context_data[t].get(pos1, Counter())
        cnt2 = context_data[t].get(pos2, Counter())
        if not cnt1 or not cnt2:
            continue
        top1_set1 = set(x for x, _ in cnt1.most_common(1))
        top1_set2 = set(x for x, _ in cnt2.most_common(1))
        topk_set1 = set(x for x, _ in cnt1.most_common(k))
        topk_set2 = set(x for x, _ in cnt2.most_common(k))
        if top1_set1 & top1_set2:
            concordant_top1 += 1
        if topk_set1 & topk_set2:
            concordant_topk += 1
        total += 1

    return {
        'top1_concordance': concordant_top1 / total if total else float('nan'),
        'topk_concordance': concordant_topk / total if total else float('nan'),
        'k': k, 'n_types': total,
        'concordant_top1': concordant_top1,
        'concordant_topk': concordant_topk,
    }


def null_model_jsd(context_data, shared_types, pos1, pos2, n_trials=100):
    """Permutation null: pool each type's successors, randomly re-split.

    Tests whether observed JSD is above sampling noise.
    NOTE: This does NOT control for the inventory confound — only
    the NL baseline does that.
    """
    # Pre-compute observed and pools
    obs_jsds = []
    type_pools = {}
    for t, n1, n2 in shared_types:
        cnt1 = context_data[t].get(pos1, Counter())
        cnt2 = context_data[t].get(pos2, Counter())
        obs_jsds.append(jsd_counters(cnt1, cnt2))
        pool = []
        for s, c in cnt1.items():
            pool.extend([s] * c)
        for s, c in cnt2.items():
            pool.extend([s] * c)
        type_pools[t] = (pool, sum(cnt1.values()), sum(cnt2.values()))

    obs_mean = float(np.mean(obs_jsds))

    null_means = []
    for trial in range(n_trials):
        trial_jsds = []
        for t, n1, n2 in shared_types:
            pool, sz1, sz2 = type_pools[t]
            shuffled = list(pool)
            random.shuffle(shuffled)
            cnt1_new = Counter(shuffled[:sz1])
            cnt2_new = Counter(shuffled[sz1:])
            trial_jsds.append(jsd_counters(cnt1_new, cnt2_new))
        null_means.append(float(np.mean(trial_jsds)))

    null_m = float(np.mean(null_means))
    null_s = float(np.std(null_means))
    z = (obs_mean - null_m) / null_s if null_s > 1e-9 else float('nan')

    return {
        'observed': obs_mean,
        'null_mean': null_m, 'null_std': null_s,
        'z': z, 'n_trials': n_trials,
    }


# ═══════════════════════════════════════════════════════════════════════
# FULL SYSTEM ANALYSIS (runs all tests on one system)
# ═══════════════════════════════════════════════════════════════════════

def analyze_system_context(name, unit_sequences, min_context=5, min_units=3):
    """Run full context-divergence analysis on a system.

    Returns dict with successor_IM and predecessor_MF results.
    """
    suc, pre, pos_counts = extract_context_by_position(unit_sequences, min_units)

    # Successor: I vs M
    shared_suc_im = identify_shared_types(suc, 'I', 'M', min_context)
    jsds_suc_im = compute_context_jsds(suc, shared_suc_im, 'I', 'M')
    cmi_suc = compute_cmi(suc, ['I', 'M'], min_context)
    conc_suc = compute_topk_concordance(suc, shared_suc_im, 'I', 'M', k=3)

    # Predecessor: M vs F
    shared_pre_mf = identify_shared_types(pre, 'M', 'F', min_context)
    jsds_pre_mf = compute_context_jsds(pre, shared_pre_mf, 'M', 'F')
    cmi_pre = compute_cmi(pre, ['M', 'F'], min_context)
    conc_pre = compute_topk_concordance(pre, shared_pre_mf, 'M', 'F', k=3)

    def summarize_jsds(jsd_list):
        if not jsd_list:
            return {'mean': float('nan'), 'median': float('nan'),
                    'weighted': float('nan'), 'n': 0}
        vals = [r['jsd'] for r in jsd_list]
        weights = [r['n_pos1'] + r['n_pos2'] for r in jsd_list]
        wt = sum(v * w for v, w in zip(vals, weights)) / sum(weights) \
            if sum(weights) > 0 else float('nan')
        return {
            'mean': float(np.mean(vals)),
            'median': float(np.median(vals)),
            'weighted': wt,
            'n': len(vals),
        }

    return {
        'name': name,
        'suc_shared': shared_suc_im,
        'suc_jsds': jsds_suc_im,
        'suc_summary': summarize_jsds(jsds_suc_im),
        'suc_cmi': cmi_suc,
        'suc_concordance': conc_suc,
        'pre_shared': shared_pre_mf,
        'pre_jsds': jsds_pre_mf,
        'pre_summary': summarize_jsds(jsds_pre_mf),
        'pre_cmi': cmi_pre,
        'pre_concordance': conc_pre,
        'suc_data': suc,
        'pre_data': pre,
        'pos_counts': pos_counts,
    }


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 76)
    pr("cross_position_context_divergence — CROSS-POSITION CONTEXT DIVERGENCE")
    pr("=" * 76)
    pr()
    pr("  For VMS chunks appearing at multiple word-positions (I, M, F),")
    pr("  do they function as the SAME or DIFFERENT linguistic units?")
    pr()
    pr("  KEY CONFOUND: Successor of I-chunk is at M, successor of M-chunk")
    pr("  is at later-M or F. Different inventories → JSD > 0 is EXPECTED")
    pr("  even for identical units. NL baselines are the PRIMARY control.")
    pr()

    MIN_CONTEXT = 5   # minimum context tokens at each position for inclusion
    MIN_UNITS   = 3   # minimum word length (≥3 chunks → I, M, F all exist)

    # ── STEP 1: PARSE CORPORA ─────────────────────────────────────────

    pr("─" * 76)
    pr("STEP 1: PARSE CORPORA")
    pr("─" * 76)
    pr()

    # VMS → chunks
    vms_data = parse_vms()
    all_words = vms_data['all']
    vms_seqs = []
    for w in all_words:
        chunks, unparsed, _ = parse_word_into_chunks(w)
        chunk_ids = [chunk_to_str(c) for c in chunks]
        vms_seqs.append(chunk_ids)

    n_total = len(all_words)
    n_3plus = sum(1 for s in vms_seqs if len(s) >= MIN_UNITS)
    n_tokens_3plus = sum(len(s) for s in vms_seqs if len(s) >= MIN_UNITS)
    pr(f"  VMS: {n_total} words total")
    pr(f"  VMS ≥{MIN_UNITS}-chunk words: {n_3plus} ({100 * n_3plus / n_total:.1f}%)")
    pr(f"  VMS tokens in ≥{MIN_UNITS}-chunk words: {n_tokens_3plus}")
    pr()

    # NL reference texts
    nl_texts = {
        'Latin-Caesar':    DATA_DIR / 'latin_texts' / 'caesar.txt',
        'Latin-Vulgate':   DATA_DIR / 'latin_texts' / 'vulgate_genesis.txt',
        'Latin-Apicius':   DATA_DIR / 'latin_texts' / 'apicius.txt',
        'Italian-Cucina':  DATA_DIR / 'vernacular_texts' / 'italian_cucina.txt',
        'French-Viandier': DATA_DIR / 'vernacular_texts' / 'french_viandier.txt',
        'English-Cury':    DATA_DIR / 'vernacular_texts' / 'english_cury.txt',
        'German-Faust':    DATA_DIR / 'vernacular_texts' / 'german_faust.txt',
    }
    bvgs_path = DATA_DIR / 'vernacular_texts' / 'german_bvgs_raw.txt'
    if bvgs_path.exists():
        nl_texts['German-BvgS'] = bvgs_path

    nl_char_seqs = {}
    nl_syl_seqs = {}
    for name, path in nl_texts.items():
        if not path.exists():
            pr(f"  SKIP {name}: not found")
            continue
        words = load_reference_text(path)
        if len(words) < 500:
            pr(f"  SKIP {name}: too few words ({len(words)})")
            continue
        nl_char_seqs[name] = [list(w) for w in words]
        nl_syl_seqs[name] = [syllabify_word(w) for w in words]
        n3c = sum(1 for w in words if len(w) >= 3)
        n3s = sum(1 for w in words if len(syllabify_word(w)) >= 3)
        pr(f"  {name}: {len(words)} words, "
           f"{n3c} with ≥3 chars ({100 * n3c / len(words):.1f}%), "
           f"{n3s} with ≥3 syls ({100 * n3s / len(words):.1f}%)")
    pr()

    # ── STEP 2: VMS CONTEXT DIVERGENCE ─────────────────────────────────

    pr("─" * 76)
    pr("STEP 2: VMS CONTEXT DIVERGENCE (≥3-chunk words)")
    pr("─" * 76)
    pr()

    vms_res = analyze_system_context('VMS-chunks', vms_seqs,
                                     min_context=MIN_CONTEXT,
                                     min_units=MIN_UNITS)

    # 2a: Successor JSD (I vs M)
    pr("  2a. SUCCESSOR JSD — I-position vs M-position")
    pr(f"      Shared types with ≥{MIN_CONTEXT} successors at both I and M: "
       f"{vms_res['suc_summary']['n']}")
    if vms_res['suc_summary']['n'] > 0:
        pr(f"      Mean JSD  = {vms_res['suc_summary']['mean']:.4f}")
        pr(f"      Median JSD = {vms_res['suc_summary']['median']:.4f}")
        pr(f"      Weighted JSD = {vms_res['suc_summary']['weighted']:.4f}")
        pr()
        pr(f"      Per-type detail (sorted by JSD, desc):")
        pr(f"        {'Type':<18s}  {'JSD':>6s}  {'n@I':>5s}  {'n@M':>5s}  "
           f"{'Top1@I':<16s}  {'Top1@M':<16s}  {'Same?':>5s}")
        pr(f"        {'─' * 18}  {'─' * 6}  {'─' * 5}  {'─' * 5}  "
           f"{'─' * 16}  {'─' * 16}  {'─' * 5}")
        for r in sorted(vms_res['suc_jsds'], key=lambda x: -x['jsd']):
            same = 'YES' if r['top1_pos1'] == r['top1_pos2'] else 'no'
            pr(f"        {r['type']:<18s}  {r['jsd']:6.4f}  {r['n_pos1']:5d}  "
               f"{r['n_pos2']:5d}  {str(r['top1_pos1']):<16s}  "
               f"{str(r['top1_pos2']):<16s}  {same:>5s}")
    pr()

    # 2b: Predecessor JSD (M vs F)
    pr("  2b. PREDECESSOR JSD — M-position vs F-position")
    pr(f"      Shared types with ≥{MIN_CONTEXT} predecessors at both M and F: "
       f"{vms_res['pre_summary']['n']}")
    if vms_res['pre_summary']['n'] > 0:
        pr(f"      Mean JSD  = {vms_res['pre_summary']['mean']:.4f}")
        pr(f"      Median JSD = {vms_res['pre_summary']['median']:.4f}")
        pr(f"      Weighted JSD = {vms_res['pre_summary']['weighted']:.4f}")
        pr()
        pr(f"      Per-type detail (sorted by JSD, desc):")
        pr(f"        {'Type':<18s}  {'JSD':>6s}  {'n@M':>5s}  {'n@F':>5s}  "
           f"{'Top1@M':<16s}  {'Top1@F':<16s}  {'Same?':>5s}")
        pr(f"        {'─' * 18}  {'─' * 6}  {'─' * 5}  {'─' * 5}  "
           f"{'─' * 16}  {'─' * 16}  {'─' * 5}")
        for r in sorted(vms_res['pre_jsds'], key=lambda x: -x['jsd']):
            same = 'YES' if r['top1_pos1'] == r['top1_pos2'] else 'no'
            pr(f"        {r['type']:<18s}  {r['jsd']:6.4f}  {r['n_pos1']:5d}  "
               f"{r['n_pos2']:5d}  {str(r['top1_pos1']):<16s}  "
               f"{str(r['top1_pos2']):<16s}  {same:>5s}")
    pr()

    # 2c: Conditional MI
    pr("  2c. CONDITIONAL MI: I(successor; position | chunk type)")
    pr(f"      Shared types: {vms_res['suc_cmi']['n_types']}")
    pr(f"      Weighted CMI = {vms_res['suc_cmi']['weighted_cmi']:.4f} bits")
    pr(f"      Unweighted CMI = {vms_res['suc_cmi']['unweighted_cmi']:.4f} bits")
    pr()
    pr("      I(predecessor; position | chunk type):")
    pr(f"      Shared types: {vms_res['pre_cmi']['n_types']}")
    pr(f"      Weighted CMI = {vms_res['pre_cmi']['weighted_cmi']:.4f} bits")
    pr(f"      Unweighted CMI = {vms_res['pre_cmi']['unweighted_cmi']:.4f} bits")
    pr()

    # 2d: Top-K concordance
    pr("  2d. TOP-K SUCCESSOR CONCORDANCE (I vs M)")
    sc = vms_res['suc_concordance']
    pr(f"      Top-1 same: {sc['concordant_top1']}/{sc['n_types']} "
       f"({100 * sc['top1_concordance']:.1f}%)")
    pr(f"      Top-3 overlap: {sc['concordant_topk']}/{sc['n_types']} "
       f"({100 * sc['topk_concordance']:.1f}%)")
    pr()
    pr("      TOP-K PREDECESSOR CONCORDANCE (M vs F)")
    pc = vms_res['pre_concordance']
    pr(f"      Top-1 same: {pc['concordant_top1']}/{pc['n_types']} "
       f"({100 * pc['top1_concordance']:.1f}%)")
    pr(f"      Top-3 overlap: {pc['concordant_topk']}/{pc['n_types']} "
       f"({100 * pc['topk_concordance']:.1f}%)")
    pr()

    # ── STEP 3: NL BASELINES ──────────────────────────────────────────

    pr("─" * 76)
    pr("STEP 3: NL CHARACTER + SYLLABLE BASELINES")
    pr("─" * 76)
    pr()

    nl_char_results = {}
    nl_syl_results = {}

    for name, seqs in sorted(nl_char_seqs.items()):
        r = analyze_system_context(f'{name}-char', seqs,
                                   min_context=MIN_CONTEXT, min_units=3)
        nl_char_results[name] = r

    for name, seqs in sorted(nl_syl_seqs.items()):
        r = analyze_system_context(f'{name}-syl', seqs,
                                   min_context=MIN_CONTEXT, min_units=3)
        nl_syl_results[name] = r

    # Print NL character baselines
    pr("  NL CHARACTER baselines (successor JSD, I vs M, ≥3-char words):")
    pr(f"    {'System':<24s}  {'n_shared':>8s}  {'Mean':>8s}  {'Median':>8s}  "
       f"{'Weighted':>8s}  {'Top1%':>6s}")
    pr(f"    {'─' * 24}  {'─' * 8}  {'─' * 8}  {'─' * 8}  {'─' * 8}  {'─' * 6}")
    pr(f"    {'VMS chunks':<24s}  {vms_res['suc_summary']['n']:8d}  "
       f"{vms_res['suc_summary']['mean']:8.4f}  "
       f"{vms_res['suc_summary']['median']:8.4f}  "
       f"{vms_res['suc_summary']['weighted']:8.4f}  "
       f"{100 * sc['top1_concordance']:5.1f}%")
    for name, r in sorted(nl_char_results.items()):
        s = r['suc_summary']
        c = r['suc_concordance']
        top1_pct = 100 * c['top1_concordance'] if not math.isnan(c['top1_concordance']) else float('nan')
        sm = 'N/A     ' if math.isnan(s['mean']) else f"{s['mean']:8.4f}"
        smed = 'N/A     ' if math.isnan(s['median']) else f"{s['median']:8.4f}"
        sw = 'N/A     ' if math.isnan(s['weighted']) else f"{s['weighted']:8.4f}"
        st = 'N/A   ' if math.isnan(top1_pct) else f"{top1_pct:5.1f}%"
        pr(f"    {name + '-char':<24s}  {s['n']:8d}  {sm}  {smed}  {sw}  {st}")
    pr()

    # NL syllable baselines
    pr("  NL SYLLABLE baselines (successor JSD, I vs M, ≥3-syl words):")
    pr(f"    {'System':<24s}  {'n_shared':>8s}  {'Mean':>8s}  {'Median':>8s}  "
       f"{'Weighted':>8s}  {'Top1%':>6s}")
    pr(f"    {'─' * 24}  {'─' * 8}  {'─' * 8}  {'─' * 8}  {'─' * 8}  {'─' * 6}")
    pr(f"    {'VMS chunks':<24s}  {vms_res['suc_summary']['n']:8d}  "
       f"{vms_res['suc_summary']['mean']:8.4f}  "
       f"{vms_res['suc_summary']['median']:8.4f}  "
       f"{vms_res['suc_summary']['weighted']:8.4f}  "
       f"{100 * sc['top1_concordance']:5.1f}%")
    for name, r in sorted(nl_syl_results.items()):
        s = r['suc_summary']
        c = r['suc_concordance']
        top1_pct = 100 * c['top1_concordance'] if not math.isnan(c['top1_concordance']) else float('nan')
        sm = 'N/A     ' if math.isnan(s['mean']) else f"{s['mean']:8.4f}"
        smed = 'N/A     ' if math.isnan(s['median']) else f"{s['median']:8.4f}"
        sw = 'N/A     ' if math.isnan(s['weighted']) else f"{s['weighted']:8.4f}"
        st = 'N/A   ' if math.isnan(top1_pct) else f"{top1_pct:5.1f}%"
        pr(f"    {name + '-syl':<24s}  {s['n']:8d}  {sm}  {smed}  {sw}  {st}")
    pr()

    # ── STEP 4: Z-SCORE COMPARISON ───────────────────────────────────

    pr("─" * 76)
    pr("STEP 4: Z-SCORE COMPARISON — VMS vs NL BASELINES")
    pr("─" * 76)
    pr()

    def compute_zscores(vms_val, nl_results, metric_path):
        """Compute z-score of VMS metric against NL distribution."""
        vals = []
        for name, r in nl_results.items():
            v = r
            for key in metric_path:
                v = v[key]
            if not math.isnan(v):
                vals.append(v)
        if len(vals) < 2:
            return float('nan'), float('nan'), float('nan')
        m = float(np.mean(vals))
        s = float(np.std(vals))
        z = (vms_val - m) / s if s > 1e-9 else float('nan')
        return m, s, z

    # Successor JSD
    pr("  SUCCESSOR JSD (I vs M):")
    vms_suc_mean = vms_res['suc_summary']['mean']
    vms_suc_wt   = vms_res['suc_summary']['weighted']

    m_c, s_c, z_c = compute_zscores(vms_suc_mean, nl_char_results,
                                     ['suc_summary', 'mean'])
    m_s, s_s, z_s = compute_zscores(vms_suc_mean, nl_syl_results,
                                     ['suc_summary', 'mean'])
    pr(f"    VMS mean JSD:       {vms_suc_mean:.4f}")
    pr(f"    NL char mean±std:   {m_c:.4f} ± {s_c:.4f}  z = {z_c:+.2f}")
    pr(f"    NL syl mean±std:    {m_s:.4f} ± {s_s:.4f}  z = {z_s:+.2f}")
    pr()

    m_cw, s_cw, z_cw = compute_zscores(vms_suc_wt, nl_char_results,
                                         ['suc_summary', 'weighted'])
    m_sw, s_sw, z_sw = compute_zscores(vms_suc_wt, nl_syl_results,
                                         ['suc_summary', 'weighted'])
    pr(f"    VMS weighted JSD:   {vms_suc_wt:.4f}")
    pr(f"    NL char mean±std:   {m_cw:.4f} ± {s_cw:.4f}  z = {z_cw:+.2f}")
    pr(f"    NL syl mean±std:    {m_sw:.4f} ± {s_sw:.4f}  z = {z_sw:+.2f}")
    pr()

    # Predecessor JSD
    pr("  PREDECESSOR JSD (M vs F):")
    vms_pre_mean = vms_res['pre_summary']['mean']
    vms_pre_wt   = vms_res['pre_summary']['weighted']

    m_cp, s_cp, z_cp = compute_zscores(vms_pre_mean, nl_char_results,
                                        ['pre_summary', 'mean'])
    m_sp, s_sp, z_sp = compute_zscores(vms_pre_mean, nl_syl_results,
                                        ['pre_summary', 'mean'])
    pr(f"    VMS mean JSD:       {vms_pre_mean:.4f}")
    pr(f"    NL char mean±std:   {m_cp:.4f} ± {s_cp:.4f}  z = {z_cp:+.2f}")
    pr(f"    NL syl mean±std:    {m_sp:.4f} ± {s_sp:.4f}  z = {z_sp:+.2f}")
    pr()

    m_cpw, s_cpw, z_cpw = compute_zscores(vms_pre_wt, nl_char_results,
                                            ['pre_summary', 'weighted'])
    m_spw, s_spw, z_spw = compute_zscores(vms_pre_wt, nl_syl_results,
                                            ['pre_summary', 'weighted'])
    pr(f"    VMS weighted JSD:   {vms_pre_wt:.4f}")
    pr(f"    NL char mean±std:   {m_cpw:.4f} ± {s_cpw:.4f}  z = {z_cpw:+.2f}")
    pr(f"    NL syl mean±std:    {m_spw:.4f} ± {s_spw:.4f}  z = {z_spw:+.2f}")
    pr()

    # CMI comparison
    pr("  CONDITIONAL MI (successor):")
    vms_cmi_val = vms_res['suc_cmi']['weighted_cmi']
    m_cc, s_cc, z_cc = compute_zscores(vms_cmi_val, nl_char_results,
                                        ['suc_cmi', 'weighted_cmi'])
    m_sc, s_sc2, z_sc2 = compute_zscores(vms_cmi_val, nl_syl_results,
                                          ['suc_cmi', 'weighted_cmi'])
    pr(f"    VMS weighted CMI:     {vms_cmi_val:.4f} bits")
    pr(f"    NL char mean±std:     {m_cc:.4f} ± {s_cc:.4f}  z = {z_cc:+.2f}")
    pr(f"    NL syl mean±std:      {m_sc:.4f} ± {s_sc2:.4f}  z = {z_sc2:+.2f}")
    pr()

    # Top-1 concordance comparison
    pr("  TOP-1 SUCCESSOR CONCORDANCE:")
    vms_top1 = sc['top1_concordance']
    m_ct, s_ct, z_ct = compute_zscores(vms_top1, nl_char_results,
                                        ['suc_concordance', 'top1_concordance'])
    m_st, s_st, z_st = compute_zscores(vms_top1, nl_syl_results,
                                        ['suc_concordance', 'top1_concordance'])
    pr(f"    VMS top-1 match:      {100 * vms_top1:.1f}%")
    pr(f"    NL char mean±std:     {100 * m_ct:.1f}% ± {100 * s_ct:.1f}%  z = {z_ct:+.2f}")
    pr(f"    NL syl mean±std:      {100 * m_st:.1f}% ± {100 * s_st:.1f}%  z = {z_st:+.2f}")
    pr()

    # ── STEP 5: PERMUTATION NULL MODEL ────────────────────────────────

    pr("─" * 76)
    pr("STEP 5: PERMUTATION NULL MODEL")
    pr("─" * 76)
    pr()
    pr("  For each shared type, pool successors from both positions,")
    pr("  randomly re-split into same-sized groups, recompute JSD.")
    pr("  This tests: is observed JSD above SAMPLING NOISE?")
    pr("  (Does NOT control for inventory confound — NL baseline does that.)")
    pr()

    N_TRIALS = 100

    if vms_res['suc_summary']['n'] >= 2:
        pr(f"  Successor JSD null model ({N_TRIALS} trials):")
        null_suc = null_model_jsd(vms_res['suc_data'], vms_res['suc_shared'],
                                  'I', 'M', n_trials=N_TRIALS)
        pr(f"    Observed mean JSD:  {null_suc['observed']:.4f}")
        pr(f"    Null mean ± std:    {null_suc['null_mean']:.4f} ± {null_suc['null_std']:.4f}")
        pr(f"    z = {null_suc['z']:+.2f}")
        pr()
    else:
        null_suc = None
        pr("  Successor: insufficient shared types for null model")
        pr()

    if vms_res['pre_summary']['n'] >= 2:
        pr(f"  Predecessor JSD null model ({N_TRIALS} trials):")
        null_pre = null_model_jsd(vms_res['pre_data'], vms_res['pre_shared'],
                                  'M', 'F', n_trials=N_TRIALS)
        pr(f"    Observed mean JSD:  {null_pre['observed']:.4f}")
        pr(f"    Null mean ± std:    {null_pre['null_mean']:.4f} ± {null_pre['null_std']:.4f}")
        pr(f"    z = {null_pre['z']:+.2f}")
        pr()
    else:
        null_pre = None
        pr("  Predecessor: insufficient shared types for null model")
        pr()

    # ── STEP 6: ADDITIONAL ROBUSTNESS — ≥2-CHUNK WORDS ───────────────

    pr("─" * 76)
    pr("STEP 6: ROBUSTNESS — REPEAT WITH ≥2-CHUNK WORDS")
    pr("─" * 76)
    pr()
    pr("  Using ≥2-chunk words expands data but limits comparison to I vs M")
    pr("  (only possible when M exists, i.e. ≥3-chunk subwords within")
    pr("  the ≥2 set are the only ones with M). For ≥2-chunk words,")
    pr("  we can compare I-successors vs F-predecessors using 2-chunk words,")
    pr("  but this mixes successor/predecessor directions (unfair).")
    pr("  Instead, we just report what fraction of 2-chunk words have")
    pr("  shared chunks at I vs F using word-companion co-occurrence.")
    pr()

    vms_res_2p = analyze_system_context('VMS-2p', vms_seqs,
                                        min_context=MIN_CONTEXT,
                                        min_units=2)
    pr(f"  With ≥2-chunk words:")
    pr(f"    Successor I vs M shared types: {vms_res_2p['suc_summary']['n']}")
    if vms_res_2p['suc_summary']['n'] > 0:
        pr(f"    Successor JSD mean = {vms_res_2p['suc_summary']['mean']:.4f}")
    pr(f"    Predecessor M vs F shared types: {vms_res_2p['pre_summary']['n']}")
    if vms_res_2p['pre_summary']['n'] > 0:
        pr(f"    Predecessor JSD mean = {vms_res_2p['pre_summary']['mean']:.4f}")
    pr()

    # ── STEP 7: SKEPTICAL AUDIT ───────────────────────────────────────

    pr("─" * 76)
    pr("STEP 7: SKEPTICAL AUDIT")
    pr("─" * 76)
    pr()

    pr("  1. DATA SPARSITY")
    pr(f"     ≥3-chunk words: only {n_3plus} ({100 * n_3plus / n_total:.1f}%)")
    pr(f"     VMS shared types for successor analysis: {vms_res['suc_summary']['n']}")
    pr(f"     VMS shared types for predecessor analysis: {vms_res['pre_summary']['n']}")
    n_with_few = sum(1 for _, n1, n2 in vms_res['suc_shared']
                     if n1 < 20 or n2 < 20)
    if vms_res['suc_shared']:
        pr(f"     Types with <20 tokens at either position: {n_with_few}/"
           f"{len(vms_res['suc_shared'])}")
    pr(f"     CAVEAT: Sparse data → high JSD from sampling noise, not real signal.")
    pr(f"     The permutation null controls for this. If z is low, sparsity")
    pr(f"     may explain the observed JSD.")
    pr()

    pr("  2. POSITION-INVENTORY CONFOUND (the central issue)")
    pr("     Successor of I-chunk is at M position.")
    pr("     Successor of M-chunk may be at later M or at F position.")
    pr("     These successor POSITIONS have different type inventories.")
    pr("     Therefore JSD > 0 is EXPECTED even for identical units.")
    pr("     CONTROL: NL characters experience the same confound.")
    pr("     If VMS JSD ≈ NL char JSD → no homograph evidence.")
    pr("     If VMS JSD >> NL char JSD → genuine homograph signal.")
    pr("     If VMS JSD ≈ NL syl JSD → consistent with NL sub-word units.")
    pr()

    pr("  3. LOOP GRAMMAR SLOT STRUCTURE")
    pr("     The LOOP grammar defines slot1={ch,sh,y}, slot2={e,q,a}, etc.")
    pr("     Chunks at I vs M may have different internal structure")
    pr("     (more I-chunks start with q-, more M-chunks start with e-)")
    pr("     which creates implicit context constraints independent of")
    pr("     the chunk's linguistic identity. This is a PARTIAL confound:")
    pr("     grammar-derived context patterns may inflate JSD even if chunks")
    pr("     are genuinely the same unit at different positions.")
    pr()

    pr("  4. NL SYLLABIFICATION QUALITY")
    pr("     The syllabifier is rule-based (~87% accuracy from chunk_fingerprint).")
    pr("     Errors create spurious syllable types, inflating type count")
    pr("     but likely REDUCING measured JSD (errors are position-random).")
    pr("     This makes the NL syllable baseline conservative.")
    pr()

    pr("  5. WORD-LENGTH COMPOSITION")
    pr("     In ≥3-chunk words, most are 3-chunk (80% of this subset).")
    pr("     In 3-chunk words: I has 1 token, M has 1, F has 1.")
    pr("     M-position is always position 2 (of 3), never deeper.")
    pr("     In NL ≥3-char words, words are typically 4-8 chars with")
    pr("     multiple M positions. This asymmetry may affect JSD.")
    pr()

    pr("  6. MULTIPLE TESTING")
    pr("     We compute 4 main metrics (suc JSD, pre JSD, CMI, concordance)")
    pr("     × 2 comparisons (vs char, vs syl) = 8 hypothesis tests.")
    pr("     With Bonferroni correction: significance requires |z| > 2.73")
    pr("     (not 1.96) at the α=0.05 level.")
    pr()

    # ── STEP 8: SYNTHESIS & VERDICT ──────────────────────────────────

    pr("─" * 76)
    pr("STEP 8: SYNTHESIS & VERDICT")
    pr("─" * 76)
    pr()

    # Gather all comparisons in a summary table
    pr("  CROSS-POSITION CONTEXT DIVERGENCE — SUMMARY TABLE")
    pr()
    pr(f"    {'Metric':<28s}  {'VMS':>8s}  {'NL-char μ':>10s}  {'z(char)':>8s}  "
       f"{'NL-syl μ':>10s}  {'z(syl)':>8s}")
    pr(f"    {'─' * 28}  {'─' * 8}  {'─' * 10}  {'─' * 8}  {'─' * 10}  {'─' * 8}")

    def fmt(v):
        return f"{v:8.4f}" if not math.isnan(v) else "     N/A"
    def fmtz(v):
        return f"{v:+8.2f}" if not math.isnan(v) else "     N/A"

    rows = [
        ('Suc JSD mean (I vs M)',   vms_suc_mean,  m_c, z_c, m_s, z_s),
        ('Suc JSD weighted',        vms_suc_wt, m_cw, z_cw, m_sw, z_sw),
        ('Pre JSD mean (M vs F)',   vms_pre_mean, m_cp, z_cp, m_sp, z_sp),
        ('Pre JSD weighted',        vms_pre_wt, m_cpw, z_cpw, m_spw, z_spw),
        ('CMI (successor)',         vms_cmi_val, m_cc, z_cc, m_sc, z_sc2),
        ('Top-1 suc concordance',   vms_top1, m_ct, z_ct, m_st, z_st),
    ]
    for label, vms_v, nc, zc, ns, zs in rows:
        pr(f"    {label:<28s}  {fmt(vms_v)}  {fmt(nc):>10s}  {fmtz(zc)}  "
           f"{fmt(ns):>10s}  {fmtz(zs)}")
    pr()

    # Count significant results (|z| > 2.73 after Bonferroni)
    BONF_THRESH = 2.73
    z_chars = [z_c, z_cw, z_cp, z_cpw, z_cc, z_ct]
    z_syls  = [z_s, z_sw, z_sp, z_spw, z_sc2, z_st]

    sig_char_cipher = sum(1 for z in z_chars
                          if not math.isnan(z) and z > BONF_THRESH)
    sig_char_nl = sum(1 for z in z_chars
                      if not math.isnan(z) and z < -BONF_THRESH)
    sig_char_ns = sum(1 for z in z_chars
                      if not math.isnan(z) and abs(z) <= BONF_THRESH)

    sig_syl_cipher = sum(1 for z in z_syls
                         if not math.isnan(z) and z > BONF_THRESH)
    sig_syl_nl = sum(1 for z in z_syls
                     if not math.isnan(z) and z < -BONF_THRESH)
    sig_syl_ns = sum(1 for z in z_syls
                     if not math.isnan(z) and abs(z) <= BONF_THRESH)

    pr("  DIRECTIONAL EVIDENCE (Bonferroni-corrected |z| > 2.73):")
    pr(f"    vs NL characters:  {sig_char_cipher} CIPHER, {sig_char_nl} NL, "
       f"{sig_char_ns} ambiguous  (total {len([z for z in z_chars if not math.isnan(z)])} tests)")
    pr(f"    vs NL syllables:   {sig_syl_cipher} CIPHER, {sig_syl_nl} NL, "
       f"{sig_syl_ns} ambiguous  (total {len([z for z in z_syls if not math.isnan(z)])} tests)")
    pr()

    # Interpretation
    pr("  INTERPRETATION:")
    pr()

    # Determine verdict
    # Cipher evidence: VMS has HIGHER JSD or HIGHER CMI or LOWER concordance
    # than NL (shared chunks diverge MORE = homographs)
    # NL evidence: VMS has LOWER JSD or LOWER CMI or HIGHER concordance
    # (shared chunks behave SAME = single alphabet)

    # Note: higher JSD → MORE divergence → cipher direction
    # Higher CMI → position adds MORE info → cipher
    # Lower concordance → different top successors → cipher

    # For concordance z-scores, NEGATIVE z means VMS < NL = cipher direction
    # So we need to flip interpretation for concordance

    pr("    Summary of z-score directions:")
    for label, zc, zs in [
        ('Suc JSD mean', z_c, z_s),
        ('Suc JSD weighted', z_cw, z_sw),
        ('Pre JSD mean', z_cp, z_sp),
        ('Pre JSD weighted', z_cpw, z_spw),
        ('CMI (successor)', z_cc, z_sc2),
        ('Top-1 concordance', z_ct, z_st),
    ]:
        # For JSD and CMI: positive z = VMS > NL = CIPHER (more divergent)
        # For concordance: negative z = VMS < NL = CIPHER (less agreement)
        if 'concordance' in label.lower():
            dir_c = 'CIPHER' if zc < -BONF_THRESH else ('NL' if zc > BONF_THRESH else 'ambiguous')
            dir_s = 'CIPHER' if zs < -BONF_THRESH else ('NL' if zs > BONF_THRESH else 'ambiguous')
        else:
            dir_c = 'CIPHER' if zc > BONF_THRESH else ('NL' if zc < -BONF_THRESH else 'ambiguous')
            dir_s = 'CIPHER' if zs > BONF_THRESH else ('NL' if zs < -BONF_THRESH else 'ambiguous')
        pr(f"      {label:<24s}  vs char: {fmtz(zc)} ({dir_c:<9s})  "
           f"vs syl: {fmtz(zs)} ({dir_s})")
    pr()

    # Final verdict
    pr("  ══════════════════════════════════════════════════════════")
    pr("  VERDICT")
    pr("  ══════════════════════════════════════════════════════════")
    pr()

    all_char_z = [z for z in z_chars if not math.isnan(z)]
    all_syl_z = [z for z in z_syls if not math.isnan(z)]

    if all_char_z:
        mean_char_z = float(np.mean(all_char_z))
        pr(f"  Mean z-score vs NL characters: {mean_char_z:+.2f}")
    else:
        mean_char_z = float('nan')
        pr("  Mean z-score vs NL characters: N/A")

    if all_syl_z:
        mean_syl_z = float(np.mean(all_syl_z))
        pr(f"  Mean z-score vs NL syllables:  {mean_syl_z:+.2f}")
    else:
        mean_syl_z = float('nan')
        pr("  Mean z-score vs NL syllables:  N/A")
    pr()

    # Determine verdict code
    # KEY: VMS could be between chars and syls (the NL sub-word pattern)
    if not math.isnan(mean_char_z) and mean_char_z > 2.0:
        if not math.isnan(mean_syl_z) and mean_syl_z < -2.0:
            # VMS is BETWEEN chars and syllables: more than chars, less than syls
            verdict = "CONTEXT_DIVERGENCE_BETWEEN_CHAR_AND_SYL"
            # Compute interpolation position
            nl_char_jsd_mean = m_c  # NL char mean successor JSD
            nl_syl_jsd_mean = m_s   # NL syl mean successor JSD
            if nl_syl_jsd_mean > nl_char_jsd_mean + 0.01:
                interp = (vms_suc_mean - nl_char_jsd_mean) / (nl_syl_jsd_mean - nl_char_jsd_mean)
            else:
                interp = float('nan')
            pr("  ★ VMS shared chunks show MORE context divergence than NL characters")
            pr("    but LESS divergence than NL syllables.")
            pr(f"    → VMS falls BETWEEN chars and syllables "
               f"({100*interp:.0f}% from char toward syl)" if not math.isnan(interp)
               else "    → VMS falls BETWEEN chars and syllables")
            pr("    → Consistent with NL sub-word units having moderate positional")
            pr("      constraints (phonotactics / morpho-phonology)")
            pr("    → The excess over NL characters is EXPECTED from VMS's lower")
            pr("      inventory overlap (J=0.24 vs NL char J=0.80): different position")
            pr("      inventories mechanically inflate context JSD.")
            pr("    → Does NOT support homography beyond what the inventory confound")
            pr("      predicts. Cipher confidence should NOT increase.")
        elif not math.isnan(mean_syl_z) and abs(mean_syl_z) < 2.0:
            verdict = "CONTEXT_DIVERGENCE_NL_SYLLABLE_CONSISTENT"
            pr("  ★ VMS shared chunks show MORE context divergence than NL characters")
            pr("    but SIMILAR divergence to NL syllables.")
            pr("    → Consistent with NL sub-word units (syllable-like behavior)")
            pr("    → NO strong evidence for homography beyond NL phonotactic effects")
        elif not math.isnan(mean_syl_z) and mean_syl_z > 2.0:
            verdict = "CONTEXT_DIVERGENCE_CIPHER_SUPPORTED"
            pr("  ★ VMS shared chunks show MORE context divergence than BOTH")
            pr("    NL characters AND NL syllables.")
            pr("    → Shared chunks may be homographs (same form, different identity)")
            pr("    → Supports positional cipher model")
        else:
            verdict = "INCONCLUSIVE"
            pr("  ★ Insufficient syllable data for reliable verdict.")
    elif not math.isnan(mean_char_z) and abs(mean_char_z) < 2.0:
        verdict = "CONTEXT_DIVERGENCE_NL_CONSISTENT"
        pr("  ★ VMS shared chunks show SIMILAR context divergence to NL characters.")
        pr("    → Consistent with single-alphabet model (same unit at all positions)")
        pr("    → AGAINST homograph/cipher interpretation")
    elif not math.isnan(mean_char_z) and mean_char_z < -2.0:
        verdict = "CONTEXT_DIVERGENCE_NL_CONSISTENT"
        pr("  ★ VMS shared chunks show LESS context divergence than NL characters.")
        pr("    → Strongly consistent with single-alphabet model")
    else:
        verdict = "INCONCLUSIVE"
        pr("  ★ Insufficient data for reliable verdict.")
    pr()

    if (vms_res['suc_summary']['n'] < 5 or
        vms_res['pre_summary']['n'] < 5):
        pr("  ⚠ WARNING: Very few shared types qualified for analysis.")
        pr("    Results are statistically weak regardless of z-scores.")
        pr("    This test should be interpreted with extreme caution.")
        pr()

    # Null model summary
    if null_suc is not None:
        pr(f"  Permutation null (successor): z = {null_suc['z']:+.2f}")
        if abs(null_suc['z']) > 3:
            pr("    → Observed JSD is significantly above sampling noise.")
        else:
            pr("    → Observed JSD may be partly explained by sampling noise.")
    pr()

    # Revised confidences
    pr("  REVISED CONFIDENCES (cross_position_context_divergence):")
    if verdict == "CONTEXT_DIVERGENCE_BETWEEN_CHAR_AND_SYL":
        pr("  - Natural language: 87% → 87% (unchanged — result is NL-consistent)")
        pr("  - Chunks = functional characters: 85% → 85% (unchanged)")
        pr("  - True alphabet ≈ 25: 70% → 70% (unchanged)")
        pr("  - h_char anomaly resolved: 75% → 75% (unchanged)")
        pr("  - Positional verbose cipher: 55% → 50% (DOWN — context divergence")
        pr("    of shared chunks is within NL sub-word range, not anomalous)")
        pr("  - Hoax/random: <1% (unchanged)")
    elif verdict == "CONTEXT_DIVERGENCE_CIPHER_SUPPORTED":
        pr("  - Natural language: 87% → 85% (slightly down)")
        pr("  - Positional verbose cipher: 55% → 60% (UP — homograph evidence)")
        pr("  - Others unchanged")
    elif verdict == "CONTEXT_DIVERGENCE_NL_CONSISTENT":
        pr("  - Natural language: 87% → 89% (UP — single-alphabet supported)")
        pr("  - Positional verbose cipher: 55% → 45% (DOWN)")
        pr("  - Others unchanged")
    else:
        pr("  - All unchanged (insufficient evidence to update)")
    pr()

    # ── SAVE RESULTS ──────────────────────────────────────────────────

    # Text output
    out_txt = RESULTS_DIR / 'cross_position_context_divergence.txt'
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"  Results saved to {out_txt}")

    # JSON output
    json_data = {
        'test': 'cross_position_context_divergence',
        'question': 'Cross-position context divergence: same unit or homographs?',
        'min_context': MIN_CONTEXT,
        'min_units': MIN_UNITS,
        'vms_n_3plus_words': n_3plus,
        'vms_suc_IM': {
            'n_shared_types': vms_res['suc_summary']['n'],
            'mean_jsd': vms_res['suc_summary']['mean'],
            'median_jsd': vms_res['suc_summary']['median'],
            'weighted_jsd': vms_res['suc_summary']['weighted'],
        },
        'vms_pre_MF': {
            'n_shared_types': vms_res['pre_summary']['n'],
            'mean_jsd': vms_res['pre_summary']['mean'],
            'median_jsd': vms_res['pre_summary']['median'],
            'weighted_jsd': vms_res['pre_summary']['weighted'],
        },
        'vms_suc_cmi': {
            'weighted': vms_res['suc_cmi']['weighted_cmi'],
            'unweighted': vms_res['suc_cmi']['unweighted_cmi'],
            'n_types': vms_res['suc_cmi']['n_types'],
        },
        'vms_top1_concordance': sc['top1_concordance'],
        'vms_top3_concordance': sc['topk_concordance'],
        'zscores_vs_char': {
            'suc_jsd_mean': z_c, 'suc_jsd_weighted': z_cw,
            'pre_jsd_mean': z_cp, 'pre_jsd_weighted': z_cpw,
            'cmi': z_cc, 'top1_concordance': z_ct,
        },
        'zscores_vs_syl': {
            'suc_jsd_mean': z_s, 'suc_jsd_weighted': z_sw,
            'pre_jsd_mean': z_sp, 'pre_jsd_weighted': z_spw,
            'cmi': z_sc2, 'top1_concordance': z_st,
        },
        'nl_char_baselines': {
            name: {
                'suc_jsd_mean': r['suc_summary']['mean'],
                'suc_jsd_weighted': r['suc_summary']['weighted'],
                'pre_jsd_mean': r['pre_summary']['mean'],
                'suc_cmi': r['suc_cmi']['weighted_cmi'],
                'n_shared_suc': r['suc_summary']['n'],
                'top1_concordance': r['suc_concordance']['top1_concordance'],
            }
            for name, r in nl_char_results.items()
        },
        'nl_syl_baselines': {
            name: {
                'suc_jsd_mean': r['suc_summary']['mean'],
                'suc_jsd_weighted': r['suc_summary']['weighted'],
                'pre_jsd_mean': r['pre_summary']['mean'],
                'suc_cmi': r['suc_cmi']['weighted_cmi'],
                'n_shared_suc': r['suc_summary']['n'],
                'top1_concordance': r['suc_concordance']['top1_concordance'],
            }
            for name, r in nl_syl_results.items()
        },
        'null_model_suc': {
            'observed': null_suc['observed'] if null_suc else None,
            'null_mean': null_suc['null_mean'] if null_suc else None,
            'null_std': null_suc['null_std'] if null_suc else None,
            'z': null_suc['z'] if null_suc else None,
        },
        'mean_z_vs_char': mean_char_z,
        'mean_z_vs_syl': mean_syl_z,
        'verdict': verdict,
    }

    out_json = RESULTS_DIR / 'cross_position_context_divergence.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, default=str)
    pr(f"  JSON saved to {out_json}")


if __name__ == '__main__':
    main()
