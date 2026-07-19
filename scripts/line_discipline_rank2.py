#!/usr/bin/env python3
"""
Line-Discipline Rank-2 Test (portfolio S3, rung 2c) — do TWO axes
complete the discipline? (N6c)

PROVENANCE: N6 showed B's line texture is forgeable from its lexicon +
a measured 91-cell class-position table + one knob. N6b showed the
table is NOT rank-1 (verdict not_compressible): the dominant axis
(85.7% variance) is the EDGE/paragraph axis (gallows-linked, Grove-word
territory), and placement with it alone fails the line group — the
interior ordering is a second, load-bearing dimension. This rung asks
the completion question: is the discipline EXACTLY two-dimensional?

MODEL M2 (fixed before fitting): deterministic rank-2 SVD
reconstruction of the double-centered log-table — two class axes
(A1, A2), two position profiles (V1, V2), ~36 effective placement
numbers + the single strength knob re-fitted on interior gain over the
N6 grid and frozen. SIGN CONVENTION (declared, cosmetic only): each
component is oriented so its position profile sums larger over the
late bins (m3, pL-1, pL) than the early bins (p1, p2, m1).

TOURNAMENT: identical machinery/bars/seeds as N6/N6b; the run ABORTS
unless B's features and the bars reproduce the committed N6 record.
Entrant G1c = placement with the rank-2 table.

PRE-REGISTERED OUTCOMES:
  gate_failed            — N6 cross-checks fail to reproduce.
  still_not_compressible — G1c does not close the line group: the
                           discipline is more than two-dimensional.
  partial_bind           — line group closes, unfitted group breaks.
  two_axes_sufficient    — G1c closes BOTH groups: B's line discipline
                           is exactly two interpretable axes (edge +
                           interior) plus one knob. SUGGESTIVE,
                           quarantined; the axes ARE the rules.
OBSERVATIONAL (declared, adjudicates nothing): Spearman correlation of
axis 2 with the N5 rank-test class mean-ranks (the interior residue
should live on axis 2), and of both axes with the N6b predictor set
(log class frequency, mean word length, gallows membership).
Vocabulary discipline: compression of statistics; nothing is decoded.
"""
import io
import json
import math
import random
import re
import statistics
import sys
from collections import Counter

import numpy as np

from common import result_path
from common.core import FOLIO_DIR, ivtff_clean_words, eva_to_glyphs, \
    zipf_alpha

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 120                # INHERITED from N6 — all cross-checked
S7_SEED = 115
N4_SEED = 118
N_GEN_SEEDS = 5
N_REPL = 8
LAMBDA_GRID = [0.25 * k for k in range(1, 17)]
S_FLOOR = 1e-4
CLASS_K = 12
MIN_LINE_WORDS = 5
HOLDOUT_FRAC = 0.2
ALPHA = 0.5

GALLOWS = set('tkpf')
S7_FEATURES = ('len', 'first', 'last', 'gallows')
INTERIOR = {'m1', 'm2', 'm3'}
BINS = ('p1', 'p2', 'm1', 'm2', 'm3', 'pL-1', 'pL')
LINE_GROUP = ('line_init_jsd', 'line_final_jsd', 'interior_gain',
              'r_pos', 'r_bi')
UNFIT_GROUP = ('h2_ratio', 'adj_dup', 'adj_near')
N6_JSON = 'line_discipline_tournament.json'
N6B_JSON = 'line_discipline_compression.json'
N5_JSON = 'line_ordinal_rank_test.json'


# ── corpus + instrument (N6 local copies) ───────────────────────────
def load_vms_b():
    lines, folios = [], []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        if not m or m.group(1) != 'B':
            continue
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if len(words) >= MIN_LINE_WORDS:
                lines.append(words)
                folios.append(fpath.stem)
    return lines, folios


def first_glyph(w):
    g = eva_to_glyphs(w)
    return g[0] if g else w[0]


def position_bin(i, L):
    if i == 0:
        return 'p1'
    if i == 1:
        return 'p2'
    if i == L - 1:
        return 'pL'
    if i == L - 2:
        return 'pL-1'
    interior_len = L - 4
    k = (i - 2) * 3 // interior_len
    return ('m1', 'm2', 'm3')[min(k, 2)]


def holdout_split(lines, folios, rng):
    groups = {}
    for i, f in enumerate(folios):
        groups.setdefault(f, []).append(i)
    keys = sorted(groups)
    rng.shuffle(keys)
    target = HOLDOUT_FRAC * len(lines)
    held, n_held = set(), 0
    for k in keys:
        if n_held >= target:
            break
        held.add(k)
        n_held += len(groups[k])
    train = [i for k in sorted(groups) if k not in held for i in groups[k]]
    hold = [i for k in sorted(groups) if k in held for i in groups[k]]
    return train, hold


def s7_features(w):
    return {'len': str(min(len(w), 7)) if len(w) < 7 else '7+',
            'first': w[0], 'last': w[-1],
            'gallows': '1' if any(c in GALLOWS for c in w) else '0'}


def interior_gain_split(lines, folios, rng):
    train_idx, hold_idx = holdout_split(lines, folios, rng)
    global_c = {f: Counter() for f in S7_FEATURES}
    bin_c = {f: {} for f in S7_FEATURES}
    for i in train_idx:
        line = lines[i]
        L = len(line)
        for pos, w in enumerate(line):
            b = position_bin(pos, L)
            fe = s7_features(w)
            for f in S7_FEATURES:
                global_c[f][fe[f]] += 1
                bin_c[f].setdefault(b, Counter())[fe[f]] += 1
    cats = {f: sorted(global_c[f]) for f in S7_FEATURES}

    def logp(counter, val, catlist):
        tot = sum(counter.values())
        v = len(catlist) + 1
        return math.log2((counter.get(val, 0) + ALPHA) / (tot + ALPHA * v))

    s, n = 0.0, 0
    for i in hold_idx:
        line = lines[i]
        L = len(line)
        for pos, w in enumerate(line):
            b = position_bin(pos, L)
            if b not in INTERIOR:
                continue
            fe = s7_features(w)
            for f in S7_FEATURES:
                bc = bin_c[f].get(b, Counter())
                s += (logp(bc, fe[f], cats[f])
                      - logp(global_c[f], fe[f], cats[f]))
            n += 1
    return s / n if n else 0.0


def interior_gain(lines, folios):
    return round(statistics.median(
        interior_gain_split(lines, folios, random.Random(S7_SEED + 7 + r))
        for r in range(10)), 4)


def class_map(lines):
    freq = Counter(first_glyph(w) for line in lines for w in line)
    return {c for c, _ in freq.most_common(CLASS_K)}


def r_profile(lines, folios):
    keep = class_map(lines)

    def to_cls(line):
        return [(first_glyph(w) if first_glyph(w) in keep else '#')
                for w in line]

    def one(rng):
        train_idx, hold_idx = holdout_split(lines, folios, rng)
        uni, pos_c, bi_c = Counter(), {}, {}
        for i in train_idx:
            cls = to_cls(lines[i])
            L = len(cls)
            prev = '^'
            for j, c in enumerate(cls):
                uni[c] += 1
                pos_c.setdefault(position_bin(j, L), Counter())[c] += 1
                bi_c.setdefault(prev, Counter())[c] += 1
                prev = c
        V = len(set(uni) | {'#'}) + 1

        def logp(counter, val):
            tot = sum(counter.values())
            return math.log2((counter.get(val, 0) + ALPHA)
                             / (tot + ALPHA * V))

        lu = lp = lb = 0.0
        n = 0
        for i in hold_idx:
            cls = to_cls(lines[i])
            L = len(cls)
            prev = '^'
            for j, c in enumerate(cls):
                lu -= logp(uni, c)
                lp -= logp(pos_c.get(position_bin(j, L), Counter()), c)
                lb -= logp(bi_c.get(prev, Counter()), c)
                prev = c
                n += 1
        if n == 0 or lu == 0:
            return 0.0, 0.0
        return (lu - lp) / lu, (lu - lb) / lu

    pts = [one(random.Random(N4_SEED + 7 + r)) for r in range(10)]
    return (round(statistics.median(p[0] for p in pts), 4),
            round(statistics.median(p[1] for p in pts), 4))


def jsd(p, q):
    keys = set(p) | set(q)
    sp, sq = sum(p.values()) or 1, sum(q.values()) or 1
    d = 0.0
    for k in keys:
        a, b = p.get(k, 0) / sp, q.get(k, 0) / sq
        m = (a + b) / 2
        if a:
            d += a / 2 * math.log2(a / m)
        if b:
            d += b / 2 * math.log2(b / m)
    return d


def entropy(counter):
    tot = sum(counter.values())
    return -sum(c / tot * math.log2(c / tot)
                for c in counter.values() if c) if tot else 0.0


def lev_is_1(a, b):
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        return sum(1 for x, y in zip(a, b) if x != y) == 1
    if la > lb:
        a, b, la, lb = b, a, lb, la
    i = j = diff = 0
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
        else:
            diff += 1
            if diff > 1:
                return False
            j += 1
    return True


def feature_vector(lines, folios):
    words = [w for line in lines for w in line]
    stream = []
    for w in words:
        stream.extend(w)
        stream.append(' ')
    uni = Counter(stream)
    big = Counter(zip(stream, stream[1:]))
    marg = Counter()
    for (a, b), c in big.items():
        marg[a] += c
    h1 = entropy(uni)
    init_first = Counter(line[0][0] for line in lines)
    other_first = Counter(w[0] for line in lines for w in line[1:])
    final_last = Counter(line[-1][-1] for line in lines)
    other_last = Counter(w[-1] for line in lines for w in line[:-1])
    dup = near = pairs = 0
    for line in lines:
        for a, b in zip(line, line[1:]):
            pairs += 1
            if a == b:
                dup += 1
            elif lev_is_1(a, b):
                near += 1
    rp, rb = r_profile(lines, folios)
    return {
        'line_init_jsd': round(jsd(init_first, other_first), 4),
        'line_final_jsd': round(jsd(final_last, other_last), 4),
        'interior_gain': interior_gain(lines, folios),
        'r_pos': rp, 'r_bi': rb,
        'h2_ratio': round((entropy(big) - entropy(marg)) / h1, 4)
        if h1 else 0.0,
        'adj_dup': round(dup / max(pairs, 1), 4),
        'adj_near': round(near / max(pairs, 1), 4),
        'ttr_5000': round(len(set(words[:5000])) /
                          max(len(words[:5000]), 1), 4),
        'zipf_alpha': round(zipf_alpha(words), 4),
        'mean_wlen': round(sum(len(w) for w in words) / len(words), 4),
    }


def build_table(lines):
    keep = class_map(lines)
    counts = {}
    for line in lines:
        L = len(line)
        for j, w in enumerate(line):
            c = first_glyph(w)
            c = c if c in keep else '#'
            counts.setdefault(c, Counter())[position_bin(j, L)] += 1
    table = {}
    for c, cnt in counts.items():
        tot = sum(cnt.values())
        table[c] = {b: (cnt.get(b, 0) + ALPHA) / (tot + ALPHA * len(BINS))
                    for b in BINS}
    return table, keep


def orient(u, v):
    """Declared sign convention: profile larger over late bins."""
    late = v[4] + v[5] + v[6]
    early = v[0] + v[1] + v[2]
    if late < early:
        return -u, -v
    return u, v


def compress_rank2(table):
    classes = sorted(table)
    L = np.array([[math.log(table[c][b]) for b in BINS] for c in classes])
    grand = L.mean()
    row = L.mean(axis=1, keepdims=True) - grand
    col = L.mean(axis=0, keepdims=True) - grand
    resid = L - grand - row - col
    u, sv, vt = np.linalg.svd(resid, full_matrices=False)
    A1, V1 = orient(u[:, 0] * math.sqrt(sv[0]),
                    vt[0] * math.sqrt(sv[0]))
    A2, V2 = orient(u[:, 1] * math.sqrt(sv[1]),
                    vt[1] * math.sqrt(sv[1]))
    L2 = grand + row + col + np.outer(A1, V1) + np.outer(A2, V2)
    P2 = np.exp(L2)
    P2 = P2 / P2.sum(axis=1, keepdims=True)
    table2 = {c: {b: float(P2[i, j]) for j, b in enumerate(BINS)}
              for i, c in enumerate(classes)}
    var2 = float((sv[0] ** 2 + sv[1] ** 2) / (sv ** 2).sum())
    ax = {
        'axis1': {c: round(float(A1[i]), 4)
                  for i, c in enumerate(classes)},
        'axis2': {c: round(float(A2[i]), 4)
                  for i, c in enumerate(classes)},
        'profile1': {b: round(float(V1[j]), 4)
                     for j, b in enumerate(BINS)},
        'profile2': {b: round(float(V2[j]), 4)
                     for j, b in enumerate(BINS)},
    }
    return table2, ax, var2


def place_line(words, table, keep, lam, rng):
    L = len(words)
    remaining = list(words)
    rng.shuffle(remaining)
    out = []
    for j in range(L):
        b = position_bin(j, L)
        if lam == 0 or len(remaining) == 1:
            out.append(remaining.pop())
            continue
        weights = []
        for w in remaining:
            c = first_glyph(w)
            c = c if c in keep else '#'
            p = table.get(c, {}).get(b, 1.0 / 7)
            weights.append(p ** lam)
        tot = sum(weights)
        x = rng.random() * tot
        acc = 0.0
        pick = 0
        for i, wt in enumerate(weights):
            acc += wt
            if x <= acc:
                pick = i
                break
        out.append(remaining.pop(pick))
    return out


def generate(lines, table, keep, lam, seed):
    rng = random.Random(seed)
    return [place_line(line, table, keep, lam, rng) for line in lines]


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for rank, i in enumerate(order):
            r[i] = rank
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx)
                    * sum((b - my) ** 2 for b in ry))
    return round(num / den, 3) if den else 0.0


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LINE-DISCIPLINE RANK-2 TEST (S3 rung 2c) — two-axis test (N6c)')
    print('=' * 76)
    n6 = json.loads(result_path(N6_JSON).read_text(encoding='utf-8'))
    n6b = json.loads(result_path(N6B_JSON).read_text(encoding='utf-8'))
    print(f'seed={SEED} (inherited; cross-checked vs N6/N6b)')

    b_lines, b_folios = load_vms_b()
    fB = feature_vector(b_lines, b_folios)
    for k, v in n6['results']['B'].items():
        if abs(fB[k] - v) > 1e-9:
            raise RuntimeError(f'B feature {k}: {fB[k]} != N6 record {v}')
    print('  B features reproduce the N6 record  VERIFIED')

    folio_set = sorted(set(b_folios))
    repl_vecs = []
    for r in range(N_REPL):
        rng = random.Random(SEED + 100 + r)
        drop = set(rng.sample(folio_set, max(1, len(folio_set) // 5)))
        keep_idx = [i for i, f in enumerate(b_folios) if f not in drop]
        repl_vecs.append(feature_vector([b_lines[i] for i in keep_idx],
                                        [b_folios[i] for i in keep_idx]))
    s = {k: max(statistics.pstdev([v[k] for v in repl_vecs]), S_FLOOR)
         for k in fB}
    half = len(folio_set) // 2
    h1f = set(folio_set[:half])
    idx1 = [i for i, f in enumerate(b_folios) if f in h1f]
    idx2 = [i for i, f in enumerate(b_folios) if f not in h1f]
    v1 = feature_vector([b_lines[i] for i in idx1],
                        [b_folios[i] for i in idx1])
    v2 = feature_vector([b_lines[i] for i in idx2],
                        [b_folios[i] for i in idx2])

    def dist(vec, ref, group):
        return round(statistics.mean(abs(vec[k] - ref[k]) / s[k]
                                     for k in group), 3)

    bar_line = dist(v1, v2, LINE_GROUP)
    bar_unfit = dist(v1, v2, UNFIT_GROUP)
    if (abs(bar_line - n6['results']['bar']['line']) > 1e-9
            or abs(bar_unfit - n6['results']['bar']['unfitted']) > 1e-9):
        raise RuntimeError('bars do not reproduce N6 record — abort')
    print(f'  bars reproduce N6 (line {bar_line}, unfitted {bar_unfit})  '
          'VERIFIED')

    table, keep = build_table(b_lines)
    table2, ax, var2 = compress_rank2(table)
    print(f'  rank-2 variance share of centered log-table: {var2:.1%}')
    print('  axis1 (edge, low -> high): '
          + '  '.join(f'{c} {a:+.3f}' for c, a in
                      sorted(ax['axis1'].items(), key=lambda kv: kv[1])))
    print('  axis2 (interior, low -> high): '
          + '  '.join(f'{c} {a:+.3f}' for c, a in
                      sorted(ax['axis2'].items(), key=lambda kv: kv[1])))
    print('  profile2: ' + '  '.join(f'{b} {v:+.3f}'
                                     for b, v in ax['profile2'].items()))

    best_lam, best_err = None, 1e9
    for lam in LAMBDA_GRID:
        g = generate(b_lines, table2, keep, lam, SEED)
        err = abs(interior_gain(g, b_folios) - fB['interior_gain'])
        if err < best_err:
            best_lam, best_err = lam, err
    print(f'  LAMBDA (rank-2 table) fitted on interior gain: {best_lam} '
          f'(|err| {best_err:.4f}) — FROZEN')

    vecs = [feature_vector(generate(b_lines, table2, keep, best_lam,
                                    SEED + 200 + k), b_folios)
            for k in range(N_GEN_SEEDS)]
    g1c = {k: round(statistics.mean(v[k] for v in vecs), 4) for k in fB}
    d_line = dist(g1c, fB, LINE_GROUP)
    d_unfit = dist(g1c, fB, UNFIT_GROUP)
    print(f'  G1c (rank-2)  D_line {d_line}  D_unfitted {d_unfit}  '
          f'(N6 full {n6["results"]["G1_discipline"]["dist"]["line"]}; '
          f'N6b rank-1 {n6b["results"]["G1b"]["dist"]["line"]})')

    # observational correlations
    n5 = json.loads(result_path(N5_JSON).read_text(encoding='utf-8'))
    n5_means = n5['rows']['VMS_currier_B']['class_means']
    common = sorted(set(ax['axis2']) & set(n5_means))
    corr_n5 = spearman([ax['axis2'][c] for c in common],
                       [n5_means[c] for c in common])
    freq = Counter(first_glyph(w) if first_glyph(w) in keep else '#'
                   for line in b_lines for w in line)
    classes = sorted(ax['axis1'])
    preds = {
        'log_class_freq': [math.log(freq[c]) for c in classes],
        'gallows_initial': [1.0 if c and c[0] in GALLOWS else 0.0
                            for c in classes],
    }
    corr = {'axis2_vs_n5_mean_ranks': corr_n5}
    for name, xs in preds.items():
        corr[f'axis1_vs_{name}'] = spearman(
            [ax['axis1'][c] for c in classes], xs)
        corr[f'axis2_vs_{name}'] = spearman(
            [ax['axis2'][c] for c in classes], xs)
    print('  observational correlations: '
          + '  '.join(f'{k} {v:+.3f}' for k, v in corr.items()))

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    line_ok = d_line <= bar_line
    unfit_ok = d_unfit <= bar_unfit
    if not line_ok:
        verdict = 'still_not_compressible'
        print('    STILL NOT COMPRESSIBLE: two axes do not close the '
              'line group — the discipline is more than two-dimensional.')
    elif not unfit_ok:
        verdict = 'partial_bind'
        print('    PARTIAL (BIND): line group closes but unfitted '
              'order-texture breaks under the rank-2 table.')
    else:
        verdict = 'two_axes_sufficient'
        print('    TWO AXES SUFFICIENT: the rank-2 table closes BOTH '
              'groups — Currier B\'s line discipline is exactly two '
              'interpretable axes (edge/paragraph + interior ordering) '
              'plus one strength knob (~37 numbers). SUGGESTIVE, '
              'quarantined; the axes above ARE the rules. Deriving each '
              'axis from independent principles is the registered '
              'blind-generation rung.')

    with open(result_path('line_discipline_rank2.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 's7_seed': S7_SEED,
                              'n4_seed': N4_SEED,
                              'n_gen_seeds': N_GEN_SEEDS,
                              'n_repl': N_REPL,
                              'lambda_grid': LAMBDA_GRID,
                              'class_k': CLASS_K, 's_floor': S_FLOOR,
                              'min_line_words': MIN_LINE_WORDS,
                              'holdout_frac': HOLDOUT_FRAC,
                              'alpha': ALPHA,
                              'line_group': list(LINE_GROUP),
                              'unfitted_group': list(UNFIT_GROUP),
                              'n6_json': N6_JSON, 'n6b_json': N6B_JSON,
                              'n5_json': N5_JSON},
                   'results': {'B': fB,
                               'bar': {'line': bar_line,
                                       'unfitted': bar_unfit},
                               'var_share2': round(var2, 4),
                               'axes': ax, 'lambda': best_lam,
                               'G1c': {'features': g1c,
                                       'dist': {'line': d_line,
                                                'unfitted': d_unfit}},
                               'n6_g1_dist':
                                   n6['results']['G1_discipline']['dist'],
                               'n6b_g1b_dist':
                                   n6b['results']['G1b']['dist'],
                               'correlations': corr},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_discipline_rank2.json')


if __name__ == '__main__':
    main()
