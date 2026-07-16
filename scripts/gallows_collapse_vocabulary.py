#!/usr/bin/env python3
"""
Gallows Collapse: Revealing the True Vocabulary

═══════════════════════════════════════════════════════════════════════

MOTIVATION: gallows_allograph_test proved all 4 gallows fill the same word slot,
with 78 shared templates. If gallows are informationally redundant
(predictable from context), then the VMS vocabulary is massively
inflated by decorative variation.

This phase answers:
1. How predictable are gallows from context? (mutual information)
2. How much does vocabulary compress when gallows collapse?
3. Does the compressed text look MORE like natural language?
4. Does compound-gallows collapse to simple-gallows further compress?

The answers determine whether the VMS has ~8,500 word types or a much
smaller core vocabulary masked by gallows variation.

TESTS:
A. GALLOWS PREDICTABILITY — Given the successor glyph, can we predict
   which gallows appears? Conditional entropy H(gallows|successor).
   If H ≈ 0: gallows are fully redundant.
   If H ≈ H(gallows): gallows are independent of successor.

B. VOCABULARY COLLAPSE — Replace {p,t,k,f} → [G] and {cph,cth,ckh,cfh}
   → [CG] in all words. Measure type and token compression.

C. LINGUISTIC QUALITY — Compare collapsed vs original:
   - Zipf α exponent (closer to -1 = more natural)
   - Hapax ratio (closer to 0.4-0.5 = more natural)
   - Bigram predictability (higher = more natural)
   - Character entropy

D. TWO-LEVEL COLLAPSE — Also test collapsing {p,f} → P_class and
   {t,k} → T_class (keeping the gallows_allograph_test two-class distinction).
   Compare 4-gallows → 2-class → 1-symbol.

E. COMPOUND COLLAPSE — Test if compound gallows (cph,cfh,cth,ckh)
   are just gallows+ch → can we collapse them to [G]+ch?
"""

import re, sys, io, math
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import clean_word, entropy_v2 as entropy, eva_to_glyphs, folio_section

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(42)

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']
PLAIN_GALLOWS = ['p', 't', 'k', 'f']
COMPOUND_GALLOWS = ['cph', 'cfh', 'cth', 'ckh']


def glyphs_to_word(glyphs):
    return ''.join(glyphs)




# ═══════════════════════════════════════════════════════════════════════
# PARSE ALL WORDS WITH CONTEXT
# ═══════════════════════════════════════════════════════════════════════

def parse_all_words():
    """Parse all words with section and paragraph context."""
    words = []  # list of (word, section, folio, para_id, line_pos)
    para_id = -1
    in_para = False
    line_in_para = 0

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)

    for filepath in folio_files:
        section = folio_section(filepath.stem)
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
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

                is_para_start = '@P' in tag or '*P' in tag
                is_continuation = '+P' in tag

                text = rest.replace('<%>', '').replace('<$>', '').strip()
                text = re.sub(r'@\d+;', '', text)
                text = re.sub(r'<[^>]*>', '', text)

                line_words = []
                for tok in re.split(r'[.\s]+', text):
                    for subtok in re.split(r',', tok):
                        c = clean_word(subtok.strip())
                        if c:
                            line_words.append(c)

                if not line_words:
                    continue

                if is_para_start:
                    para_id += 1
                    in_para = True
                    line_in_para = 1
                elif is_continuation and in_para:
                    line_in_para += 1
                elif not in_para:
                    continue

                for w in line_words:
                    words.append((w, section, filepath.stem, para_id, line_in_para))

    return words


# ═══════════════════════════════════════════════════════════════════════
# COLLAPSE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def collapse_full(word):
    """Replace ALL gallows with G (including compounds → CG)."""
    glyphs = eva_to_glyphs(word)
    new = []
    for g in glyphs:
        if g in PLAIN_GALLOWS:
            new.append('G')
        elif g in COMPOUND_GALLOWS:
            new.append('CG')
        else:
            new.append(g)
    return glyphs_to_word(new)

def collapse_two_class(word):
    """Replace {p,f}→P and {t,k}→T (keep 2-class distinction)."""
    glyphs = eva_to_glyphs(word)
    new = []
    for g in glyphs:
        if g in ('p', 'f'):
            new.append('P')
        elif g in ('t', 'k'):
            new.append('T')
        elif g in ('cph', 'cfh'):
            new.append('CP')
        elif g in ('cth', 'ckh'):
            new.append('CT')
        else:
            new.append(g)
    return glyphs_to_word(new)

def collapse_compound_to_simple(word):
    """Replace compound gallows with simple+ch: cph→p+ch, cth→t+ch etc."""
    glyphs = eva_to_glyphs(word)
    new = []
    for g in glyphs:
        if g == 'cph': new.extend(['p', 'ch'])
        elif g == 'cfh': new.extend(['f', 'ch'])
        elif g == 'cth': new.extend(['t', 'ch'])
        elif g == 'ckh': new.extend(['k', 'ch'])
        else: new.append(g)
    return glyphs_to_word(new)


# ═══════════════════════════════════════════════════════════════════════
# INFORMATION THEORY
# ═══════════════════════════════════════════════════════════════════════


def conditional_entropy(joint_counter, condition_counter):
    """H(X|Y) from joint and marginal counts."""
    # joint_counter: Counter of (x, y) pairs
    # condition_counter: Counter of y values
    total = sum(joint_counter.values())
    if total == 0: return 0.0
    h = 0.0
    for (x, y), count in joint_counter.items():
        if count > 0:
            p_xy = count / total
            p_y = condition_counter[y] / total
            if p_y > 0:
                h -= p_xy * math.log2(p_xy / p_y)
    return h

def mutual_information(joint_counter, x_counter, y_counter):
    """I(X;Y) = H(X) - H(X|Y)."""
    hx = entropy(x_counter)
    hx_given_y = conditional_entropy(joint_counter, y_counter)
    return hx - hx_given_y


# ═══════════════════════════════════════════════════════════════════════
# LINGUISTIC METRICS
# ═══════════════════════════════════════════════════════════════════════

def zipf_alpha(word_counter, max_rank=500):
    """Estimate Zipf α via log-log regression on top ranks."""
    freqs = sorted(word_counter.values(), reverse=True)[:max_rank]
    if len(freqs) < 10: return 0.0
    log_ranks = np.log(np.arange(1, len(freqs) + 1))
    log_freqs = np.log(np.array(freqs, dtype=float))
    # Linear regression
    A = np.vstack([log_ranks, np.ones(len(log_ranks))]).T
    alpha, _ = np.linalg.lstsq(A, log_freqs, rcond=None)[0]
    return alpha

def hapax_ratio(word_counter):
    """Fraction of word types appearing exactly once."""
    total_types = len(word_counter)
    hapax = sum(1 for c in word_counter.values() if c == 1)
    return hapax / total_types if total_types else 0.0

def bigram_entropy(word_list):
    """Average word bigram entropy (predictability of next word)."""
    bigrams = Counter()
    unigrams = Counter()
    for i in range(len(word_list) - 1):
        bigrams[(word_list[i], word_list[i+1])] += 1
        unigrams[word_list[i]] += 1
    return conditional_entropy(bigrams, unigrams)

def char_entropy_from_words(word_list):
    """Character-level entropy of the text."""
    chars = Counter()
    for w in word_list:
        for g in eva_to_glyphs(w):
            chars[g] += 1
    return entropy(chars)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 72)
    pr("gallows_collapse_vocabulary — GALLOWS COLLAPSE: REVEALING THE TRUE VOCABULARY")
    pr("=" * 72)
    pr()

    all_data = parse_all_words()
    all_words = [w for w, _, _, _, _ in all_data]
    pr(f"Total word tokens: {len(all_words)}")
    pr(f"Total word types: {len(set(all_words))}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST A: GALLOWS PREDICTABILITY
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST A: GALLOWS PREDICTABILITY (Mutual Information)")
    pr("=" * 72)
    pr()
    pr("Can we predict which gallows appears from context?")
    pr("If H(gallows|successor) ≈ 0 → gallows fully redundant")
    pr("If H(gallows|successor) ≈ H(gallows) → gallows independent")
    pr()

    # Collect gallows-successor pairs
    gallows_succ_joint = Counter()  # (gallows, successor)
    gallows_counter = Counter()
    succ_counter = Counter()
    gallows_pred_joint = Counter()  # (gallows, predecessor)
    pred_counter = Counter()
    # Also: gallows given full remaining context (pred + succ)
    gallows_context_joint = Counter()  # (gallows, (pred, succ))
    context_counter = Counter()

    for w in all_words:
        glyphs = eva_to_glyphs(w)
        for i, g in enumerate(glyphs):
            if g in PLAIN_GALLOWS:
                gallows_counter[g] += 1
                succ = glyphs[i+1] if i+1 < len(glyphs) else '<END>'
                pred = glyphs[i-1] if i > 0 else '<START>'
                gallows_succ_joint[(g, succ)] += 1
                succ_counter[succ] += 1
                gallows_pred_joint[(g, pred)] += 1
                pred_counter[pred] += 1
                ctx = (pred, succ)
                gallows_context_joint[(g, ctx)] += 1
                context_counter[ctx] += 1

    h_gallows = entropy(gallows_counter)
    h_g_given_succ = conditional_entropy(gallows_succ_joint, succ_counter)
    h_g_given_pred = conditional_entropy(gallows_pred_joint, pred_counter)
    h_g_given_ctx = conditional_entropy(gallows_context_joint, context_counter)
    mi_succ = h_gallows - h_g_given_succ
    mi_pred = h_gallows - h_g_given_pred
    mi_ctx = h_gallows - h_g_given_ctx

    pr(f"H(gallows) = {h_gallows:.4f} bits  (max = {math.log2(4):.4f} for 4 equally likely)")
    pr(f"  Gallows distribution: {dict(gallows_counter.most_common())}")
    pr()
    pr(f"H(gallows | successor glyph) = {h_g_given_succ:.4f} bits")
    pr(f"  → MI(gallows; successor) = {mi_succ:.4f} bits ({mi_succ/h_gallows:.1%} of gallows entropy)")
    pr(f"  → Successor explains {mi_succ/h_gallows:.1%} of gallows choice")
    pr()
    pr(f"H(gallows | predecessor glyph) = {h_g_given_pred:.4f} bits")
    pr(f"  → MI(gallows; predecessor) = {mi_pred:.4f} bits ({mi_pred/h_gallows:.1%} of gallows entropy)")
    pr()
    pr(f"H(gallows | both pred+succ) = {h_g_given_ctx:.4f} bits")
    pr(f"  → MI(gallows; context) = {mi_ctx:.4f} bits ({mi_ctx/h_gallows:.1%} of gallows entropy)")
    pr(f"  → Context explains {mi_ctx/h_gallows:.1%} of gallows choice")
    pr()

    # How well can we predict gallows from successor alone?
    pr("Gallows prediction accuracy from successor glyph:")
    correct = 0
    total = 0
    succ_best_gallows = {}
    for succ_g in succ_counter:
        best = None
        best_count = 0
        for g in PLAIN_GALLOWS:
            c = gallows_succ_joint.get((g, succ_g), 0)
            if c > best_count:
                best_count = c
                best = g
        succ_best_gallows[succ_g] = best

    for (g, s), count in gallows_succ_joint.items():
        if succ_best_gallows.get(s) == g:
            correct += count
        total += count
    pr(f"  Accuracy (majority vote per successor): {correct}/{total} = {correct/total:.1%}")
    pr(f"  Baseline (always predict most common gallows 'k'): {gallows_counter['k']/total:.1%}")
    pr()

    # Prediction from (pred, succ) context
    ctx_best = {}
    for ctx_val in context_counter:
        best = None
        best_count = 0
        for g in PLAIN_GALLOWS:
            c = gallows_context_joint.get((g, ctx_val), 0)
            if c > best_count:
                best_count = c
                best = g
        ctx_best[ctx_val] = best

    correct_ctx = 0
    for (g, ctx_val), count in gallows_context_joint.items():
        if ctx_best.get(ctx_val) == g:
            correct_ctx += count
    pr(f"  Accuracy (majority vote per pred+succ context): {correct_ctx}/{total} = {correct_ctx/total:.1%}")
    pr()

    # Two-class prediction: can we at least predict CLASS A vs B?
    pr("Two-class prediction ({p,f} vs {t,k}):")
    class_succ_joint = Counter()
    class_counter = Counter()
    for (g, s), count in gallows_succ_joint.items():
        cls = 'A' if g in ('p', 'f') else 'B'
        class_succ_joint[(cls, s)] += count
        class_counter[cls] += count

    h_class = entropy(class_counter)
    h_class_given_succ = conditional_entropy(class_succ_joint, succ_counter)
    pr(f"  H(class) = {h_class:.4f} bits")
    pr(f"  H(class | successor) = {h_class_given_succ:.4f} bits")
    pr(f"  → MI = {h_class - h_class_given_succ:.4f} bits ({(h_class - h_class_given_succ)/h_class:.1%} of class entropy)")

    # Prediction accuracy for class
    succ_best_class = {}
    for succ_g in succ_counter:
        best = None; best_c = 0
        for cls in ['A', 'B']:
            c = class_succ_joint.get((cls, succ_g), 0)
            if c > best_c:
                best_c = c; best = cls
        succ_best_class[succ_g] = best

    correct_class = 0
    total_class = 0
    for (cls, s), count in class_succ_joint.items():
        if succ_best_class.get(s) == cls:
            correct_class += count
        total_class += count
    pr(f"  Two-class accuracy from successor: {correct_class}/{total_class} = {correct_class/total_class:.1%}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST B: VOCABULARY COLLAPSE
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST B: VOCABULARY COLLAPSE")
    pr("=" * 72)
    pr()

    original_counter = Counter(all_words)
    original_types = len(original_counter)
    original_tokens = sum(original_counter.values())

    # Full collapse: all gallows → G
    collapsed_full = [collapse_full(w) for w in all_words]
    full_counter = Counter(collapsed_full)
    full_types = len(full_counter)

    # Two-class collapse: {p,f}→P, {t,k}→T
    collapsed_two = [collapse_two_class(w) for w in all_words]
    two_counter = Counter(collapsed_two)
    two_types = len(two_counter)

    # Compound decompose first, then full collapse
    collapsed_comp = [collapse_full(collapse_compound_to_simple(w)) for w in all_words]
    comp_counter = Counter(collapsed_comp)
    comp_types = len(comp_counter)

    pr(f"{'Method':<30s} {'Types':>8s} {'Reduction':>10s} {'% of orig':>10s}")
    pr("-" * 62)
    pr(f"{'Original':<30s} {original_types:>8d} {'':>10s} {'100.0%':>10s}")
    pr(f"{'Two-class ({p,f}→P, {t,k}→T)':<30s} {two_types:>8d} {original_types - two_types:>+10d} {two_types/original_types:>10.1%}")
    pr(f"{'Full collapse (all→G)':<30s} {full_types:>8d} {original_types - full_types:>+10d} {full_types/original_types:>10.1%}")
    pr(f"{'Compound→simple then →G':<30s} {comp_types:>8d} {original_types - comp_types:>+10d} {comp_types/original_types:>10.1%}")
    pr()

    # How many word types MERGE under each collapse?
    pr("Merge analysis (full collapse):")
    merge_groups = defaultdict(set)
    for w in original_counter:
        collapsed = collapse_full(w)
        merge_groups[collapsed].add(w)

    merge_sizes = Counter(len(v) for v in merge_groups.values())
    pr(f"  Collapsed types that map to 1 original: {merge_sizes.get(1, 0)}")
    pr(f"  Collapsed types that merge 2 originals: {merge_sizes.get(2, 0)}")
    pr(f"  Collapsed types that merge 3 originals: {merge_sizes.get(3, 0)}")
    pr(f"  Collapsed types that merge 4+ originals: {sum(v for k, v in merge_sizes.items() if k >= 4)}")
    pr()

    # Show biggest merges
    big_merges = sorted(merge_groups.items(), key=lambda x: len(x[1]), reverse=True)
    pr("Top 15 merge groups (full collapse):")
    for collapsed, originals in big_merges[:15]:
        total_freq = sum(original_counter[w] for w in originals)
        parts = sorted(originals, key=lambda w: -original_counter[w])
        parts_str = ', '.join(f"{w}({original_counter[w]})" for w in parts[:6])
        if len(parts) > 6:
            parts_str += f", ...+{len(parts)-6} more"
        pr(f"  {collapsed:20s} [{len(originals)} types, {total_freq} tokens]: {parts_str}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST C: LINGUISTIC QUALITY COMPARISON
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST C: LINGUISTIC QUALITY COMPARISON")
    pr("=" * 72)
    pr()

    datasets = [
        ("Original", all_words, original_counter),
        ("Two-class", collapsed_two, two_counter),
        ("Full collapse", collapsed_full, full_counter),
        ("Compound→simple→G", collapsed_comp, comp_counter),
    ]

    pr(f"{'Metric':<25s}", end='')
    for name, _, _ in datasets:
        pr(f" {name:>16s}", end='')
    pr()
    pr("-" * (25 + 17 * len(datasets)))

    # Zipf alpha
    pr(f"{'Zipf α (ideal ≈ -1.0)':<25s}", end='')
    for name, wlist, counter in datasets:
        alpha = zipf_alpha(counter)
        pr(f" {alpha:>16.3f}", end='')
    pr()

    # Hapax ratio
    pr(f"{'Hapax ratio':<25s}", end='')
    for name, wlist, counter in datasets:
        hr = hapax_ratio(counter)
        pr(f" {hr:>16.3f}", end='')
    pr()

    # TTR
    pr(f"{'TTR (types/tokens)':<25s}", end='')
    for name, wlist, counter in datasets:
        ttr = len(counter) / sum(counter.values())
        pr(f" {ttr:>16.3f}", end='')
    pr()

    # Character entropy
    pr(f"{'Glyph entropy (bits)':<25s}", end='')
    for name, wlist, counter in datasets:
        ce = char_entropy_from_words(wlist)
        pr(f" {ce:>16.3f}", end='')
    pr()

    # Word entropy
    pr(f"{'Word entropy (bits)':<25s}", end='')
    for name, wlist, counter in datasets:
        we = entropy(counter)
        pr(f" {we:>16.3f}", end='')
    pr()

    # Bigram entropy (word-level)
    pr(f"{'Word bigram H (bits)':<25s}", end='')
    for name, wlist, counter in datasets:
        be = bigram_entropy(wlist)
        pr(f" {be:>16.3f}", end='')
    pr()

    pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST D: DOES LINE POSITION ADD INFORMATION BEYOND SUCCESSOR?
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST D: LINE POSITION vs SUCCESSOR — Independent or redundant?")
    pr("=" * 72)
    pr()
    pr("Does knowing line position help predict gallows BEYOND what")
    pr("the successor glyph already tells us?")
    pr()

    # Collect gallows with line-position AND successor
    gallows_line_succ = Counter()  # (gallows, (line_is_1, successor))
    line_succ_counter = Counter()
    gallows_line_joint = Counter()
    line_counter = Counter()

    for w, sec, folio, para_id, line_pos in all_data:
        glyphs = eva_to_glyphs(w)
        is_l1 = (line_pos == 1)
        for i, g in enumerate(glyphs):
            if g in PLAIN_GALLOWS:
                succ = glyphs[i+1] if i+1 < len(glyphs) else '<END>'
                ctx = (is_l1, succ)
                gallows_line_succ[(g, ctx)] += 1
                line_succ_counter[ctx] += 1
                gallows_line_joint[(g, is_l1)] += 1
                line_counter[is_l1] += 1

    h_g_given_line = conditional_entropy(gallows_line_joint, line_counter)
    h_g_given_line_succ = conditional_entropy(gallows_line_succ, line_succ_counter)

    mi_line = h_gallows - h_g_given_line
    mi_line_succ = h_gallows - h_g_given_line_succ

    pr(f"H(gallows) = {h_gallows:.4f} bits")
    pr(f"H(gallows | line_position) = {h_g_given_line:.4f} bits")
    pr(f"  → MI(gallows; line) = {mi_line:.4f} bits ({mi_line/h_gallows:.1%})")
    pr()
    pr(f"H(gallows | successor) = {h_g_given_succ:.4f} bits")
    pr(f"H(gallows | line + successor) = {h_g_given_line_succ:.4f} bits")
    pr(f"  → MI(gallows; line+succ) = {mi_line_succ:.4f} bits ({mi_line_succ/h_gallows:.1%})")
    pr()
    pr(f"Additional info from line beyond successor: {h_g_given_succ - h_g_given_line_succ:.4f} bits")
    pr(f"Additional info from successor beyond line: {h_g_given_line - h_g_given_line_succ:.4f} bits")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST E: SECTION-LEVEL COLLAPSE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST E: SECTION-LEVEL COMPRESSION")
    pr("=" * 72)
    pr()
    pr("Does gallows collapse affect sections differently?")
    pr()

    section_words = defaultdict(list)
    for w, sec, _, _, _ in all_data:
        section_words[sec].append(w)

    pr(f"{'Section':<10s} {'Orig types':>12s} {'Collapsed':>12s} {'Reduction':>12s} {'% compress':>12s}")
    pr("-" * 60)
    for sec in ['herbal', 'recipe', 'balneo', 'cosmo', 'astro']:
        if sec not in section_words:
            continue
        sw = section_words[sec]
        orig_t = len(set(sw))
        coll_t = len(set(collapse_full(w) for w in sw))
        pr(f"{sec:<10s} {orig_t:>12d} {coll_t:>12d} {orig_t - coll_t:>+12d} {(orig_t - coll_t)/orig_t:>12.1%}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST F: RESIDUAL GALLOWS INFORMATION
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST F: RESIDUAL INFORMATION — What gallows encode beyond context")
    pr("=" * 72)
    pr()
    pr("After accounting for successor and line position, how much")
    pr("unexplained gallows entropy remains?")
    pr()

    # Add section into the context
    gallows_full_ctx = Counter()
    full_ctx_counter = Counter()
    for w, sec, folio, para_id, line_pos in all_data:
        glyphs = eva_to_glyphs(w)
        is_l1 = (line_pos == 1)
        for i, g in enumerate(glyphs):
            if g in PLAIN_GALLOWS:
                succ = glyphs[i+1] if i+1 < len(glyphs) else '<END>'
                pred = glyphs[i-1] if i > 0 else '<START>'
                ctx = (pred, succ, is_l1, sec)
                gallows_full_ctx[(g, ctx)] += 1
                full_ctx_counter[ctx] += 1

    h_g_given_full = conditional_entropy(gallows_full_ctx, full_ctx_counter)
    mi_full = h_gallows - h_g_given_full

    pr(f"H(gallows | pred + succ + line + section) = {h_g_given_full:.4f} bits")
    pr(f"  → MI(gallows; all_context) = {mi_full:.4f} bits ({mi_full/h_gallows:.1%})")
    pr(f"  → RESIDUAL unexplained entropy: {h_g_given_full:.4f} bits ({h_g_given_full/h_gallows:.1%})")
    pr()

    if h_g_given_full < 0.5 * h_gallows:
        pr("⚠ MORE THAN HALF of gallows entropy is explained by context.")
        pr("  Gallows are significantly redundant with their surroundings.")
    elif h_g_given_full > 0.8 * h_gallows:
        pr("■ Most gallows entropy survives conditioning on context.")
        pr("  Gallows carry substantial INDEPENDENT information.")
    else:
        pr("● Gallows are partially predictable from context but retain")
        pr("  significant independent information.")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # SYNTHESIS
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("gallows_collapse_vocabulary — SYNTHESIS")
    pr("=" * 72)
    pr()
    pr(f"Original vocabulary: {original_types} types / {original_tokens} tokens")
    pr(f"After full gallows collapse: {full_types} types ({full_types/original_types:.1%} of original)")
    pr(f"Vocabulary inflation from gallows: {original_types - full_types} types ({(original_types - full_types)/original_types:.1%})")
    pr()
    pr(f"Gallows entropy budget:")
    pr(f"  Total: {h_gallows:.4f} bits")
    pr(f"  Explained by successor: {mi_succ:.4f} bits ({mi_succ/h_gallows:.1%})")
    pr(f"  Explained by predecessor: {mi_pred:.4f} bits ({mi_pred/h_gallows:.1%})")
    pr(f"  Explained by line position: {mi_line:.4f} bits ({mi_line/h_gallows:.1%})")
    pr(f"  Explained by all context: {mi_full:.4f} bits ({mi_full/h_gallows:.1%})")
    pr(f"  RESIDUAL (independent): {h_g_given_full:.4f} bits ({h_g_given_full/h_gallows:.1%})")
    pr()

    # Save
    outpath = RESULTS_DIR / 'gallows_collapse_vocabulary.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"\nResults saved to {outpath}")


if __name__ == '__main__':
    main()
