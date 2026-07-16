#!/usr/bin/env python3
"""
Run-Length-Conditioned Transition Matrices:
              Verifying & Extending the Currier A Breakpoint Table
═════════════════════════════════════════════════════════════════

PREMISE:
An external Currier A transition probability table (attached image)
shows that run-length CHANGES successor probabilities dramatically:
  - i→n = 56.1%, but ii→n = 94.8%, iii→n = 90.9%
  - e→o = 51.9%, but ee→y = 51.8%, eee→y = 43.0%
The table also annotates word-boundary breakpoints (strong/weak).

run_conditioned_transitions independently computes these transition matrices on our
corpus, separated by Currier A vs B, and tests:

METHOD:
  A. RUN-CONDITIONED SUCCESSOR MATRICES — for each glyph, compute
     P(next | glyph×N) for run lengths N=1,2,3. Verify the external
     table's values AND extend to Currier B.
  B. A vs B TRANSITION DIVERGENCE — for every glyph, measure JSD
     between Currier A and B successor distributions. Which glyphs
     behave DIFFERENTLY across the two languages?
  C. WORD-BOUNDARY PREDICTION — using our I-M-F slot grammar from
     run_length_morphology, predict where word boundaries should fall in the
     transition matrix. Compare to the external breakpoint annotations.
  D. FUNCTIONAL GLYPH TAXONOMY — cluster glyphs by their run-length
     transition signatures into functional classes. Do the classes
     match I/M/F? Do they differ in A vs B?
  E. INFORMATION CONTENT — compute the bits of information carried
     by run-length choice. If ii→n=94.8% while i→n=56.1%, the
     choice of single vs double carries information about what follows.

SKEPTICAL NOTES:
  - Our corpus may differ slightly from the external source
    (different transcription, different folio coverage)
  - Currier A/B assignment is approximate; boundary folios are debated
  - Small counts for iii→X may produce unreliable probabilities
"""

import sys, os, re, math, json
from pathlib import Path
from collections import Counter, defaultdict
from itertools import groupby

_print = print
import numpy as np
from common import eva_to_glyphs_v2 as eva_to_glyphs

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    _print(s, end=end); sys.stdout.flush()
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))


# ═══════════════════════════════════════════════════════════════════════
# DATA LOADING (with Currier A/B split)
# ═══════════════════════════════════════════════════════════════════════

def get_currier_language():
    """Approximate Currier A/B mapping (from misbinding_coherence_test)."""
    currier = {}
    for f in range(1, 25): currier[f] = 'A'
    currier[25]='A'; currier[26]='B'; currier[27]='A'; currier[28]='A'
    currier[29]='A'; currier[30]='A'; currier[31]='B'; currier[32]='A'
    currier[33]='B'; currier[34]='B'; currier[35]='A'; currier[36]='A'
    currier[37]='A'; currier[38]='B'; currier[39]='B'
    currier[40]='B'; currier[41]='B'; currier[42]='B'; currier[43]='A'
    currier[44]='A'; currier[45]='B'; currier[46]='A'; currier[47]='A'
    currier[48]='B'
    currier[49]='A'; currier[50]='B'; currier[51]='A'; currier[52]='A'
    currier[53]='A'; currier[54]='A'; currier[55]='B'; currier[56]='A'
    for f in range(57, 68): currier[f] = 'A'
    for f in range(68, 74): currier[f] = 'B'
    for f in range(75, 85): currier[f] = 'B'
    currier[85]='B'; currier[86]='B'
    for f in range(87, 103): currier[f] = 'B'
    for f in range(103, 117): currier[f] = 'A'
    return currier

def load_vms_words_by_currier():
    """Load words split by Currier language."""
    currier = get_currier_language()
    words_a, words_b, words_all = [], [], []
    for fp in sorted(FOLIO_DIR.glob('*.txt')):
        m = re.match(r'f(\d+)', fp.stem)
        folio_num = int(m.group(1)) if m else None
        lang = currier.get(folio_num) if folio_num else None
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                m2 = re.match(r'<([^>]+)>', line)
                rest = line[m2.end():].strip() if m2 else line
                if not rest: continue
                for tok in re.split(r'[.\s,;]+', rest):
                    tok = tok.strip()
                    if tok and re.match(r'^[a-z]+$', tok):
                        words_all.append(tok)
                        if lang == 'A': words_a.append(tok)
                        elif lang == 'B': words_b.append(tok)
    return words_a, words_b, words_all



# ═══════════════════════════════════════════════════════════════════════
# RUN-LENGTH AWARE GLYPH SEQUENCES
# ═══════════════════════════════════════════════════════════════════════

def word_to_run_tokens(word):
    """Convert word to glyph-run tokens: 'daiin' → ['d','a','ii','n']"""
    glyphs = eva_to_glyphs(word)
    runs = []
    for key, group in groupby(glyphs):
        n = len(list(group))
        runs.append((key, n))
    return runs

def run_token_label(glyph, n):
    """Label like 'i', 'ii', 'iii', 'e', 'ee', etc."""
    return glyph * n if len(glyph) == 1 else f'{glyph}×{n}'


# ═══════════════════════════════════════════════════════════════════════
# TEST A: RUN-CONDITIONED SUCCESSOR MATRICES
# ═══════════════════════════════════════════════════════════════════════

def test_run_conditioned_transitions(words_a, words_b, words_all):
    pr('═' * 70)
    pr('TEST A: RUN-CONDITIONED SUCCESSOR PROBABILITIES')
    pr('═' * 70)
    pr()

    # External table values for verification (Currier A)
    ext_table = {
        ('i', 1): [('n', 0.5609), ('r', 0.2621)],
        ('ii', 2): [('n', 0.9480), ('r', 0.0281)],
        ('iii', 3): [('n', 0.9091)],
        ('e', 1): [('o', 0.5192), ('y', 0.2865)],
        ('ee', 2): [('y', 0.5182), ('o', 0.2824)],
        ('eee', 3): [('y', 0.4302), ('s', 0.2674)],
        ('q', 1): [('o', 0.9711), ('k', 0.0140)],
        ('ch', 1): [('o', 0.4567), ('e', 0.2510)],
        ('sh', 1): [('o', 0.4661), ('e', 0.3249)],
        ('d', 1): [('a', 0.5040), ('y', 0.2673)],
        ('a', 1): [('i', 0.5196), ('l', 0.1937)],  # a>i+ means i or ii
        ('k', 1): [('e', 0.3043), ('ch', 0.1959)],
        ('o', 1): [('l', 0.2499), ('k', 0.1653)],
    }

    for corpus_label, words in [('CURRIER A', words_a), ('CURRIER B', words_b),
                                 ('ALL VMS', words_all)]:
        pr(f'  ── {corpus_label} ({len(words)} words) ──')
        pr()

        # Build run→successor transition counts
        # A "run" is a consecutive sequence of the same glyph
        # The successor is the FIRST glyph of the next run
        trans = defaultdict(Counter)  # (glyph, run_len) → Counter of successor glyphs

        for w in words:
            runs = word_to_run_tokens(w)
            for idx in range(len(runs) - 1):
                glyph, n = runs[idx]
                next_glyph, _ = runs[idx + 1]
                trans[(glyph, n)][next_glyph] += 1

        # Print for key glyphs
        key_glyphs = ['i', 'e', 'q', 'ch', 'sh', 'd', 'a', 'k', 'o',
                      'y', 'l', 'n', 'r', 't', 'p', 's', 'ckh', 'cth',
                      'cph', 'cfh', 'f', 'm', 'g']

        for g in key_glyphs:
            # Find what run lengths exist
            rlens = sorted(set(n for (gg, n) in trans if gg == g))
            if not rlens:
                continue

            for rlen in rlens:
                total = sum(trans[(g, rlen)].values())
                if total < 5:
                    continue
                top2 = trans[(g, rlen)].most_common(2)
                label = run_token_label(g, rlen)
                line = f'    {label:>8s} →'
                for succ, cnt in top2:
                    pct = cnt / total
                    line += f'  {succ} ({pct:.1%})'
                line += f'  [n={total}]'

                # Compare to external table if available
                ext_key = (label if len(g) == 1 else g, rlen)
                if (label, rlen) in ext_table and corpus_label == 'CURRIER A':
                    ext_vals = ext_table[(label, rlen)]
                    ext_str = ', '.join(f'{s}={p:.1%}' for s, p in ext_vals)
                    line += f'  (ext: {ext_str})'
                elif (g, rlen) in ext_table and corpus_label == 'CURRIER A':
                    ext_vals = ext_table[(g, rlen)]
                    ext_str = ', '.join(f'{s}={p:.1%}' for s, p in ext_vals)
                    line += f'  (ext: {ext_str})'

                pr(line)

            if len(rlens) > 1:
                pr()  # Space between multi-run-length glyphs

        pr()

    return trans


# ═══════════════════════════════════════════════════════════════════════
# TEST B: A vs B TRANSITION DIVERGENCE
# ═══════════════════════════════════════════════════════════════════════

def test_ab_divergence(words_a, words_b):
    pr('═' * 70)
    pr('TEST B: CURRIER A vs B — TRANSITION DIVERGENCE')
    pr('═' * 70)
    pr()

    def build_successor_dists(words):
        """Build glyph → successor distribution."""
        succ = defaultdict(Counter)
        for w in words:
            gl = eva_to_glyphs(w)
            for i in range(len(gl) - 1):
                succ[gl[i]][gl[i+1]] += 1
        return succ

    def build_run_successor_dists(words):
        """Build (glyph, runlen) → successor distribution."""
        succ = defaultdict(Counter)
        for w in words:
            runs = word_to_run_tokens(w)
            for i in range(len(runs) - 1):
                g, n = runs[i]
                ng, _ = runs[i+1]
                succ[(g, n)][ng] += 1
        return succ

    succ_a = build_successor_dists(words_a)
    succ_b = build_successor_dists(words_b)

    def jsd(d1, d2):
        all_keys = set(d1.keys()) | set(d2.keys())
        if not all_keys: return 0.0
        t1, t2 = sum(d1.values()), sum(d2.values())
        if t1 == 0 or t2 == 0: return 1.0
        j = 0.0
        for k in all_keys:
            p = d1.get(k, 0) / t1; q = d2.get(k, 0) / t2
            m = (p + q) / 2
            if p > 0 and m > 0: j += 0.5 * p * math.log2(p / m)
            if q > 0 and m > 0: j += 0.5 * q * math.log2(q / m)
        return j

    # Glyph-level divergence
    pr('  Glyph-level successor divergence (A vs B):')
    pr(f'  {"Glyph":>8s} {"JSD":>8s} {"n_A":>7s} {"n_B":>7s} '
       f'{"Top A":>15s} {"Top B":>15s} {"Shift":>10s}')
    pr('  ' + '-' * 75)

    divergences = []
    for g in sorted(set(succ_a.keys()) | set(succ_b.keys())):
        n_a = sum(succ_a[g].values())
        n_b = sum(succ_b[g].values())
        if n_a < 20 or n_b < 20:
            continue
        j = jsd(succ_a[g], succ_b[g])
        top_a = succ_a[g].most_common(1)[0] if succ_a[g] else ('?', 0)
        top_b = succ_b[g].most_common(1)[0] if succ_b[g] else ('?', 0)
        top_a_str = f'{top_a[0]}({top_a[1]/n_a:.0%})'
        top_b_str = f'{top_b[0]}({top_b[1]/n_b:.0%})'
        shift = 'SAME' if top_a[0] == top_b[0] else '◄ DIFFERS'
        divergences.append((g, j, n_a, n_b, top_a_str, top_b_str, shift))

    divergences.sort(key=lambda x: -x[1])
    for g, j, na, nb, ta, tb, shift in divergences:
        pr(f'  {g:>8s} {j:>8.4f} {na:>7d} {nb:>7d} {ta:>15s} {tb:>15s} {shift:>10s}')

    pr()
    mean_jsd = np.mean([d[1] for d in divergences])
    pr(f'  Mean JSD across all glyphs: {mean_jsd:.4f}')
    same_top = sum(1 for d in divergences if 'SAME' in d[6])
    pr(f'  Glyphs with same top successor in A vs B: {same_top}/{len(divergences)}')

    # Run-conditioned divergence
    pr()
    pr('  Run-conditioned divergence (A vs B):')
    rsucc_a = build_run_successor_dists(words_a)
    rsucc_b = build_run_successor_dists(words_b)

    run_divs = []
    for key in sorted(set(rsucc_a.keys()) | set(rsucc_b.keys())):
        g, n = key
        na = sum(rsucc_a[key].values())
        nb = sum(rsucc_b[key].values())
        if na < 10 or nb < 10:
            continue
        j = jsd(rsucc_a[key], rsucc_b[key])
        label = run_token_label(g, n)
        top_a = rsucc_a[key].most_common(1)[0]
        top_b = rsucc_b[key].most_common(1)[0]
        ta = f'{top_a[0]}({top_a[1]/na:.0%})'
        tb = f'{top_b[0]}({top_b[1]/nb:.0%})'
        shift = 'SAME' if top_a[0] == top_b[0] else '◄ DIFFERS'
        run_divs.append((label, j, na, nb, ta, tb, shift))

    run_divs.sort(key=lambda x: -x[1])
    pr(f'  {"Run":>8s} {"JSD":>8s} {"n_A":>7s} {"n_B":>7s} '
       f'{"Top A":>15s} {"Top B":>15s} {"Shift":>10s}')
    pr('  ' + '-' * 75)
    for label, j, na, nb, ta, tb, shift in run_divs[:25]:
        pr(f'  {label:>8s} {j:>8.4f} {na:>7d} {nb:>7d} {ta:>15s} {tb:>15s} {shift:>10s}')

    return divergences, run_divs


# ═══════════════════════════════════════════════════════════════════════
# TEST C: WORD-BOUNDARY PREDICTION FROM SLOT GRAMMAR
# ═══════════════════════════════════════════════════════════════════════

def test_word_boundary_prediction(words_all):
    pr()
    pr('═' * 70)
    pr('TEST C: WORD-BOUNDARY PREDICTION FROM SLOT GRAMMAR')
    pr('═' * 70)
    pr()

    # run_length_morphology slot grammar: I*M+F*
    INITIAL = {'q', 'sh', 'ch', 'cth', 'cph'}
    MEDIAL  = {'i', 'e', 'a', 'k', 't', 'o', 'd', 'ckh', 'p', 'f', 'cfh'}
    FINAL   = {'n', 'm', 'g', 'y', 'r', 'l', 's'}

    # Predicted word-boundary transitions: F→I (strong) and F→M (medium)
    # because words end with F and start with I or M
    # Within-word: I→M, M→M, M→F (no boundary)

    # Compute: for each glyph pair (a, b), what % of time does a word
    # boundary fall between them?
    # This uses across-word boundaries
    boundary_trans = Counter()   # (a, b) where a=last glyph of word N, b=first of word N+1
    within_trans = Counter()     # (a, b) within same word

    for w in words_all:
        gl = eva_to_glyphs(w)
        for i in range(len(gl) - 1):
            within_trans[(gl[i], gl[i+1])] += 1

    for i in range(len(words_all) - 1):
        gl1 = eva_to_glyphs(words_all[i])
        gl2 = eva_to_glyphs(words_all[i+1])
        if gl1 and gl2:
            boundary_trans[(gl1[-1], gl2[0])] += 1

    # For each transition pair, compute boundary probability
    pr('  Transition boundary probabilities:')
    pr('  P(boundary | seeing glyph A followed by glyph B)')
    pr()

    # Focus on transitions with sufficient data
    pair_boundary_prob = {}
    for (a, b) in set(boundary_trans.keys()) | set(within_trans.keys()):
        n_bound = boundary_trans.get((a, b), 0)
        n_within = within_trans.get((a, b), 0)
        total = n_bound + n_within
        if total < 20:
            continue
        p_boundary = n_bound / total
        pair_boundary_prob[(a, b)] = (p_boundary, n_bound, n_within, total)

    # Sort by boundary probability
    sorted_pairs = sorted(pair_boundary_prob.items(), key=lambda x: -x[1][0])

    pr('  HIGH BOUNDARY PROBABILITY (likely word breaks):')
    pr(f'  {"A→B":>12s} {"P(break)":>9s} {"Boundary":>9s} {"Within":>8s} '
       f'{"Pos A":>8s} {"Pos B":>8s} {"Grammar":>10s}')
    pr('  ' + '-' * 75)
    for (a, b), (pb, nb, nw, tot) in sorted_pairs[:25]:
        posa = 'I' if a in INITIAL else 'M' if a in MEDIAL else 'F' if a in FINAL else '?'
        posb = 'I' if b in INITIAL else 'M' if b in MEDIAL else 'F' if b in FINAL else '?'
        # Grammar prediction: F→I = strong break, F→M = break, I→M = no break, M→M = no break
        if posa == 'F' and posb == 'I':
            grammar = 'F→I ✓'
        elif posa == 'F' and posb == 'M':
            grammar = 'F→M ✓'
        elif posa == 'F' and posb == 'F':
            grammar = 'F→F ✓'
        elif posa in ('I', 'M') and posb in ('M',):
            grammar = f'{posa}→M ✗'
        else:
            grammar = f'{posa}→{posb} ?'
        pr(f'  {a+"→"+b:>12s} {pb:>9.1%} {nb:>9d} {nw:>8d} '
           f'{posa:>8s} {posb:>8s} {grammar:>10s}')

    pr()
    pr('  LOW BOUNDARY PROBABILITY (within-word transitions):')
    pr(f'  {"A→B":>12s} {"P(break)":>9s} {"Boundary":>9s} {"Within":>8s} '
       f'{"Pos A":>8s} {"Pos B":>8s} {"Grammar":>10s}')
    pr('  ' + '-' * 75)
    for (a, b), (pb, nb, nw, tot) in sorted_pairs[-25:]:
        posa = 'I' if a in INITIAL else 'M' if a in MEDIAL else 'F' if a in FINAL else '?'
        posb = 'I' if b in INITIAL else 'M' if b in MEDIAL else 'F' if b in FINAL else '?'
        if posa == 'F' and posb in ('I', 'M', 'F'):
            grammar = f'F→{posb} ✗!'
        elif posa in ('I', 'M') and posb in ('M',):
            grammar = f'{posa}→M ✓'
        elif posa == 'I' and posb == 'F':
            grammar = 'I→F ✓'
        elif posa == 'M' and posb == 'F':
            grammar = 'M→F ✓'
        else:
            grammar = f'{posa}→{posb} ?'
        pr(f'  {a+"→"+b:>12s} {pb:>9.1%} {nb:>9d} {nw:>8d} '
           f'{posa:>8s} {posb:>8s} {grammar:>10s}')

    # Accuracy: how well does slot grammar predict boundaries?
    correct = 0; total = 0
    for (a, b), (pb, nb, nw, tot) in pair_boundary_prob.items():
        posa = 'I' if a in INITIAL else 'M' if a in MEDIAL else 'F' if a in FINAL else '?'
        posb = 'I' if b in INITIAL else 'M' if b in MEDIAL else 'F' if b in FINAL else '?'
        predicted_boundary = posa == 'F'
        actual_boundary = pb > 0.5
        if predicted_boundary == actual_boundary:
            correct += 1
        total += 1

    pr()
    pr(f'  Slot grammar boundary prediction accuracy: {correct}/{total} '
       f'({correct/total:.1%})')

    return pair_boundary_prob


# ═══════════════════════════════════════════════════════════════════════
# TEST D: FUNCTIONAL GLYPH TAXONOMY BY RUN-TRANSITION SIGNATURE
# ═══════════════════════════════════════════════════════════════════════

def test_glyph_taxonomy(words_all):
    pr()
    pr('═' * 70)
    pr('TEST D: FUNCTIONAL GLYPH TAXONOMY')
    pr('═' * 70)
    pr()

    INITIAL = {'q', 'sh', 'ch', 'cth', 'cph'}
    MEDIAL  = {'i', 'e', 'a', 'k', 't', 'o', 'd', 'ckh', 'p', 'f', 'cfh'}
    FINAL   = {'n', 'm', 'g', 'y', 'r', 'l', 's'}

    # For each glyph, build a feature vector:
    # [P(word-initial), P(word-medial), P(word-final),
    #  P(next is I), P(next is M), P(next is F),
    #  P(self-repeat), mean_run_length]

    init_ct = Counter(); med_ct = Counter(); fin_ct = Counter()
    total_ct = Counter()
    succ_class = defaultdict(Counter)  # glyph → Counter of successor's positional class
    self_rep = Counter()
    run_lens = defaultdict(list)

    for w in words_all:
        gl = eva_to_glyphs(w)
        if len(gl) == 1:
            init_ct[gl[0]] += 1; fin_ct[gl[0]] += 1; total_ct[gl[0]] += 1
        else:
            init_ct[gl[0]] += 1; total_ct[gl[0]] += 1
            for g in gl[1:-1]:
                med_ct[g] += 1; total_ct[g] += 1
            fin_ct[gl[-1]] += 1; total_ct[gl[-1]] += 1

        # Successor class
        for i in range(len(gl) - 1):
            nxt = gl[i+1]
            cls = 'I' if nxt in INITIAL else 'M' if nxt in MEDIAL else 'F' if nxt in FINAL else '?'
            succ_class[gl[i]][cls] += 1
            if gl[i] == gl[i+1]:
                self_rep[gl[i]] += 1

        # Run lengths
        for key, group in groupby(gl):
            run_lens[key].append(len(list(group)))

    # Build feature table
    pr(f'  {"Glyph":>8s} {"Init%":>7s} {"Med%":>7s} {"Fin%":>7s} '
       f'{"→I":>6s} {"→M":>6s} {"→F":>6s} '
       f'{"Self%":>7s} {"MeanRun":>8s} {"Class":>8s}')
    pr('  ' + '-' * 80)

    glyph_features = {}
    for g in sorted(total_ct, key=lambda x: -total_ct[x]):
        if total_ct[g] < 50: continue
        t = total_ct[g]
        p_init = init_ct.get(g, 0) / t
        p_med = med_ct.get(g, 0) / t
        p_fin = fin_ct.get(g, 0) / t

        sc = succ_class[g]
        sc_total = sum(sc.values())
        p_si = sc.get('I', 0) / sc_total if sc_total else 0
        p_sm = sc.get('M', 0) / sc_total if sc_total else 0
        p_sf = sc.get('F', 0) / sc_total if sc_total else 0

        p_self = self_rep.get(g, 0) / (sc_total) if sc_total else 0
        mean_rl = np.mean(run_lens.get(g, [1]))

        # Classify
        if p_init > 0.5:
            cls = 'INITIAL'
        elif p_fin > 0.5:
            cls = 'FINAL'
        elif p_self > 0.2:
            cls = 'REPEAT'
        elif p_sm > 0.6:
            cls = 'MEDIAL→M'
        elif p_sf > 0.5:
            cls = 'MEDIAL→F'
        else:
            cls = 'MEDIAL'

        glyph_features[g] = {
            'init': p_init, 'med': p_med, 'fin': p_fin,
            'succ_I': p_si, 'succ_M': p_sm, 'succ_F': p_sf,
            'self_rep': p_self, 'mean_run': mean_rl, 'class': cls
        }

        pr(f'  {g:>8s} {p_init:>7.1%} {p_med:>7.1%} {p_fin:>7.1%} '
           f'{p_si:>6.1%} {p_sm:>6.1%} {p_sf:>6.1%} '
           f'{p_self:>7.1%} {mean_rl:>8.2f} {cls:>8s}')

    # Summarize classes
    pr()
    class_counts = Counter(v['class'] for v in glyph_features.values())
    pr('  Glyph class summary:')
    for cls, cnt in class_counts.most_common():
        members = [g for g, v in glyph_features.items() if v['class'] == cls]
        pr(f'    {cls}: {", ".join(members)}')

    return glyph_features


# ═══════════════════════════════════════════════════════════════════════
# TEST E: INFORMATION CONTENT OF RUN-LENGTH CHOICE
# ═══════════════════════════════════════════════════════════════════════

def test_runlength_information(words_all):
    pr()
    pr('═' * 70)
    pr('TEST E: INFORMATION CONTENT OF RUN-LENGTH CHOICE')
    pr('═' * 70)
    pr()

    # For each glyph that forms runs: how many bits of successor info
    # does the run length carry?
    # H(next | glyph) vs H(next | glyph, run_length)
    # ΔH = additional bits from knowing the run length

    trans = defaultdict(Counter)  # (glyph, runlen) → successor
    trans_agg = defaultdict(Counter)  # glyph → successor (ignoring run length)

    for w in words_all:
        runs = word_to_run_tokens(w)
        for i in range(len(runs) - 1):
            g, n = runs[i]
            ng, _ = runs[i+1]
            trans[(g, n)][ng] += 1
            trans_agg[g][ng] += 1

    def entropy(counter):
        total = sum(counter.values())
        if total == 0: return 0
        return -sum((c/total) * math.log2(c/total) for c in counter.values() if c > 0)

    pr(f'  {"Glyph":>8s} {"H(next)":>8s} {"H(next|len)":>12s} {"ΔH":>8s} '
       f'{"Runs":>6s} {"MaxLen":>7s} {"Info gain":>10s}')
    pr('  ' + '-' * 65)

    info_gains = []
    for g in sorted(trans_agg, key=lambda x: -sum(trans_agg[x].values())):
        total_agg = sum(trans_agg[g].values())
        if total_agg < 50: continue

        h_agg = entropy(trans_agg[g])

        # Weighted average H(next | glyph, runlen)
        rlens = sorted(set(n for (gg, n) in trans if gg == g))
        if len(rlens) < 2:
            continue  # Only one run length — no info from run length

        h_cond = 0
        for rlen in rlens:
            n_rl = sum(trans[(g, rlen)].values())
            h_rl = entropy(trans[(g, rlen)])
            h_cond += (n_rl / total_agg) * h_rl

        delta_h = h_agg - h_cond
        max_rlen = max(rlens)

        info_gains.append((g, h_agg, h_cond, delta_h, max_rlen))
        significance = 'HIGH' if delta_h > 0.3 else 'moderate' if delta_h > 0.1 else 'low'
        pr(f'  {g:>8s} {h_agg:>8.3f} {h_cond:>12.3f} {delta_h:>8.3f} '
           f'{total_agg:>6d} {max_rlen:>7d} {significance:>10s}')

    pr()
    if info_gains:
        top = max(info_gains, key=lambda x: x[3])
        pr(f'  Highest information gain: {top[0]} (ΔH = {top[3]:.3f} bits)')
        pr(f'  → Knowing the run length of {top[0]} gives {top[3]:.3f} additional')
        pr(f'    bits of information about what glyph comes next.')

    return info_gains


# ═══════════════════════════════════════════════════════════════════════
# ADJUDICATION
# ═══════════════════════════════════════════════════════════════════════

def adjudicate(divergences, run_divs, boundary_accuracy, info_gains):
    pr()
    pr('═' * 70)
    pr('ADJUDICATION')
    pr('═' * 70)
    pr()

    pr('  1. EXTERNAL TABLE VERIFICATION:')
    pr('     Our independently computed transition probabilities should')
    pr('     match the external Currier A table. Differences indicate')
    pr('     transcription or corpus coverage variations.')
    pr()

    pr('  2. A vs B DIVERGENCE:')
    mean_jsd = np.mean([d[1] for d in divergences]) if divergences else 0
    same_top = sum(1 for d in divergences if 'SAME' in d[6])
    total_g = len(divergences)
    pr(f'     Mean glyph JSD: {mean_jsd:.4f}')
    pr(f'     Same top successor: {same_top}/{total_g}')
    if mean_jsd < 0.05:
        pr('     → A and B use nearly IDENTICAL transition rules')
        pr('       This supports "same language, different scribes" hypothesis')
    elif mean_jsd < 0.15:
        pr('     → A and B show MODERATE transition differences')
        pr('       Could be dialect, register, or topic variation')
    else:
        pr('     → A and B show LARGE transition differences')
        pr('       Supports genuine different languages/encodings')
    pr()

    # Run-conditioned divergence
    if run_divs:
        run_mean = np.mean([d[1] for d in run_divs])
        pr(f'     Run-conditioned mean JSD: {run_mean:.4f}')
        if run_mean > mean_jsd * 1.5:
            pr('     → Run-length transitions AMPLIFY A/B differences')
        else:
            pr('     → Run-length transitions show similar A/B divergence')
    pr()

    pr('  3. WORD-BOUNDARY PREDICTION:')
    pr(f'     Slot grammar predicts boundaries with {boundary_accuracy:.1%} accuracy')
    if boundary_accuracy > 0.80:
        pr('     → STRONG: I-M-F grammar captures word structure')
    elif boundary_accuracy > 0.65:
        pr('     → MODERATE: grammar captures most but not all structure')
    else:
        pr('     → WEAK: grammar needs refinement')
    pr()

    pr('  4. RUN-LENGTH INFORMATION CONTENT:')
    if info_gains:
        i_gain = next((x for x in info_gains if x[0] == 'i'), None)
        e_gain = next((x for x in info_gains if x[0] == 'e'), None)
        if i_gain:
            pr(f'     i: knowing run length gives {i_gain[3]:.3f} bits about next glyph')
            pr(f'        H(next|i) = {i_gain[1]:.3f}, H(next|i,runlen) = {i_gain[2]:.3f}')
        if e_gain:
            pr(f'     e: knowing run length gives {e_gain[3]:.3f} bits about next glyph')
            pr(f'        H(next|e) = {e_gain[1]:.3f}, H(next|e,runlen) = {e_gain[2]:.3f}')
        pr()
        if i_gain and i_gain[3] > 0.5:
            pr('     → VERY HIGH information in i-run length choice.')
            pr('       Run length is NOT redundant — it encodes structural info.')
        elif i_gain and i_gain[3] > 0.2:
            pr('     → SIGNIFICANT information in run length.')
    pr()

    pr('  REVISED CONFIDENCES (run_conditioned_transitions):')
    pr('    - NL in unknown script: 80% (unchanged)')
    pr('    - Script has positional slot grammar (I-M-F): 95% (unchanged)')
    pr('    - i-run length is informationally loaded: NEW')
    pr('    - Currier A and B share transition structure: to be scored')
    pr('    - Simple substitution cipher: <5% (unchanged)')
    pr('    - Hoax/random: <3% (unchanged)')


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr('╔' + '═'*68 + '╗')
    pr('║  run_conditioned_transitions: Run-Conditioned Transitions (A vs B)                ║')
    pr('╚' + '═'*68 + '╝')
    pr()

    np.random.seed(42)

    pr('Loading VMS by Currier language...')
    words_a, words_b, words_all = load_vms_words_by_currier()
    pr(f'  Currier A: {len(words_a)} words')
    pr(f'  Currier B: {len(words_b)} words')
    pr(f'  Total:     {len(words_all)} words')
    pr()

    # TEST A
    trans = test_run_conditioned_transitions(words_a, words_b, words_all)

    # TEST B
    divergences, run_divs = test_ab_divergence(words_a, words_b)

    # TEST C
    pair_bp = test_word_boundary_prediction(words_all)
    # Extract accuracy
    INITIAL = {'q', 'sh', 'ch', 'cth', 'cph'}
    MEDIAL  = {'i', 'e', 'a', 'k', 't', 'o', 'd', 'ckh', 'p', 'f', 'cfh'}
    FINAL   = {'n', 'm', 'g', 'y', 'r', 'l', 's'}
    correct = 0; total = 0
    for (a, b), (pb, nb, nw, tot) in pair_bp.items():
        posa = 'F' if a in FINAL else 'I' if a in INITIAL else 'M'
        predicted_boundary = posa == 'F'
        actual_boundary = pb > 0.5
        if predicted_boundary == actual_boundary:
            correct += 1
        total += 1
    boundary_acc = correct / total if total else 0

    # TEST D
    glyph_features = test_glyph_taxonomy(words_all)

    # TEST E
    info_gains = test_runlength_information(words_all)

    # ADJUDICATION
    adjudicate(divergences, run_divs, boundary_acc, info_gains)

    # Save
    out_path = RESULTS_DIR / 'run_conditioned_transitions_output.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f'\nSaved to {out_path}')

    json_data = {
        'n_words_a': len(words_a),
        'n_words_b': len(words_b),
        'ab_divergence': [(g, j, na, nb) for g, j, na, nb, _, _, _ in divergences],
        'glyph_features': glyph_features,
        'info_gains': [(g, ha, hc, dh, ml) for g, ha, hc, dh, ml in info_gains],
        'boundary_accuracy': boundary_acc,
    }
    json_path = RESULTS_DIR / 'run_conditioned_transitions_output.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, default=str)
    pr(f'Saved to {json_path}')


if __name__ == '__main__':
    main()
