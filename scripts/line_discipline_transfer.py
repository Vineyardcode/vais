#!/usr/bin/env python3
"""
Line-Discipline Cross-Hand Blind Test (portfolio S3, rung 3) — does a
table measured on Currier A place Currier B's lines? (N6e)

PROVENANCE: the compression ladder (N6..N6d) established that Currier
B's line texture is forgeable from its lexicon + a placement table +
one knob, and that the table is exactly three interpretable axes
(edge/paragraph, interior gradient, pre-final zone). Every rung so far
measured the table ON B — plug-in information the blind-derivation
program must eliminate. This rung takes the first blind step.

SCOPE DISCLOSURE (stated first): this is blind WITH RESPECT TO B, not
blind with respect to the manuscript. The table is measured exclusively
on CURRIER A's lines — a different hand (Davis: different scribes),
different sections, ~5x weaker ordinal signal (S7/N5 gradient) — and
contains zero B positional information. B contributes only its lexicon
(inherent to the placement paradigm) and the single strength knob
LAMBDA, re-fitted on B's interior gain over the N6 grid and frozen
(ladder convention: the knob is the one permitted contact with B).
Deriving the table from principles OUTSIDE the manuscript (paragraph
mechanics, layout models) remains the registered future rung.

WHY THIS TEST IS DECISIVE FOR THE SWITCH PICTURE: the hand gradient
(A ~ 1/5 of B on every ordinal instrument; Parisel 2026a's switch
intensity) predicts the table SHAPE is manuscript-wide and only the
STRENGTH differs by hand. If so, the A-table should close B's
tournament with a LARGER fitted LAMBDA than B's own table needed
(1.25) — the knob absorbing the intensity difference. If A's
preferences differ in shape, no knob setting will close the line group.

MECHANICS: classes = B's top-CLASS_K first-EVA-glyphs + OTHER (a
lexicon-level choice, no positional content; so the A-table plugs into
the identical B placement machinery). Table = P(position-bin | class)
counted on A's lines only, Laplace-smoothed; classes unseen in A fall
back to uniform (declared). Machinery, features, bars, and seeds are
identical to N6 and are cross-checked against its committed JSON —
the run ABORTS on any divergence. Entrant G1e = B's lines placed with
the A-table.

PRE-REGISTERED OUTCOMES:
  gate_failed          — N6 cross-checks fail to reproduce.
  not_transferable     — G1e does not close the line group: the
                         discipline's shape is hand-specific; B's
                         systematization layer is its own. Corpse
                         logged with the per-axis transfer profile.
  partial_bind         — line group closes, unfitted group breaks.
  discipline_transfers — G1e closes BOTH groups: the placement
                         discipline is a manuscript-wide system whose
                         hand difference is (at least largely) a
                         strength difference — the switch-intensity
                         picture made mechanical. SUGGESTIVE,
                         quarantined; not a decode.
OBSERVATIONAL (declared, adjudicates nothing): rank-3 axes of the
A-table vs the B-table (same sign convention), Spearman per axis over
common classes — which of the three rules transfer; and the fitted
LAMBDA vs B's own 1.25.
Vocabulary discipline: transfer of statistics; nothing is decoded.
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
N6D_JSON = 'line_discipline_rank3.json'


# ── corpus + instrument (N6 local copies) ───────────────────────────
def load_vms_hand(hand):
    lines, folios = [], []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        if not m or m.group(1) != hand:
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


def build_table_over(lines, keep):
    """P(position-bin | class) counted on `lines`, over the DECLARED
    class set `keep` (classes unseen here get no row -> uniform
    fallback in placement)."""
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
    return table


def orient(u, v):
    late = v[4] + v[5] + v[6]
    early = v[0] + v[1] + v[2]
    if late < early:
        return -u, -v
    return u, v


def rank3_axes(table):
    classes = sorted(table)
    L = np.array([[math.log(table[c][b]) for b in BINS] for c in classes])
    grand = L.mean()
    row = L.mean(axis=1, keepdims=True) - grand
    col = L.mean(axis=0, keepdims=True) - grand
    resid = L - grand - row - col
    u, sv, vt = np.linalg.svd(resid, full_matrices=False)
    ax = {}
    for k in range(3):
        Ak, Vk = orient(u[:, k] * math.sqrt(sv[k]),
                        vt[k] * math.sqrt(sv[k]))
        ax[f'axis{k + 1}'] = {c: round(float(Ak[i]), 4)
                              for i, c in enumerate(classes)}
    return ax


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
    print('LINE-DISCIPLINE CROSS-HAND BLIND TEST (S3 rung 3) — A-table '
          'on B (N6e)')
    print('=' * 76)
    n6 = json.loads(result_path(N6_JSON).read_text(encoding='utf-8'))
    print(f'seed={SEED} (inherited; cross-checked vs N6); table source: '
          'CURRIER A ONLY')

    b_lines, b_folios = load_vms_hand('B')
    a_lines, a_folios = load_vms_hand('A')
    print(f'  corpora: B {len(b_lines)} lines (placed), A '
          f'{len(a_lines)} lines (table source)')
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

    keep = class_map(b_lines)          # declared: B's class alphabet
    a_table = build_table_over(a_lines, keep)
    b_table = build_table_over(b_lines, keep)

    best_lam, best_err = None, 1e9
    for lam in LAMBDA_GRID:
        g = generate(b_lines, a_table, keep, lam, SEED)
        err = abs(interior_gain(g, b_folios) - fB['interior_gain'])
        if err < best_err:
            best_lam, best_err = lam, err
    print(f'  LAMBDA (A-table on B) fitted on interior gain: {best_lam} '
          f'(|err| {best_err:.4f}; B\'s own table needed 1.25) — FROZEN')

    vecs = [feature_vector(generate(b_lines, a_table, keep, best_lam,
                                    SEED + 200 + k), b_folios)
            for k in range(N_GEN_SEEDS)]
    g1e = {k: round(statistics.mean(v[k] for v in vecs), 4) for k in fB}
    d_line = dist(g1e, fB, LINE_GROUP)
    d_unfit = dist(g1e, fB, UNFIT_GROUP)
    print(f'  G1e (A-table)  D_line {d_line}  D_unfitted {d_unfit}  '
          f'(B-table full: {n6["results"]["G1_discipline"]["dist"]["line"]})')

    # observational: per-axis transfer
    ax_a = rank3_axes(a_table)
    ax_b = rank3_axes(b_table)
    transfer = {}
    for k in ('axis1', 'axis2', 'axis3'):
        common = sorted(set(ax_a[k]) & set(ax_b[k]))
        transfer[k] = spearman([ax_a[k][c] for c in common],
                               [ax_b[k][c] for c in common])
    print('  per-axis transfer (Spearman, A-table vs B-table): '
          + '  '.join(f'{k} {v:+.3f}' for k, v in transfer.items()))

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    line_ok = d_line <= bar_line
    unfit_ok = d_unfit <= bar_unfit
    if not line_ok:
        verdict = 'not_transferable'
        print('    NOT TRANSFERABLE: the A-measured table does not close '
              'B\'s line group at any knob setting — the discipline\'s '
              'shape is (at least partly) hand-specific. Corpse logged '
              'with the per-axis transfer profile above.')
    elif not unfit_ok:
        verdict = 'partial_bind'
        print('    PARTIAL (BIND): line group closes but unfitted '
              'order-texture breaks under the A-table.')
    else:
        verdict = 'discipline_transfers'
        print('    DISCIPLINE TRANSFERS: a table measured exclusively on '
              'Currier A closes Currier B\'s full line texture — the '
              'placement discipline is a manuscript-wide system whose '
              'hand difference is (at least largely) a strength '
              'difference, absorbed by the single knob. The '
              'switch-intensity picture made mechanical. SUGGESTIVE, '
              'quarantined; not a decode.')

    with open(result_path('line_discipline_transfer.json'), 'w',
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
                              'table_source': 'currier_A_only',
                              'n6_json': N6_JSON,
                              'n6d_json': N6D_JSON},
                   'results': {'B': fB,
                               'bar': {'line': bar_line,
                                       'unfitted': bar_unfit},
                               'n_a_lines': len(a_lines),
                               'lambda': best_lam,
                               'lambda_b_own': 1.25,
                               'G1e': {'features': g1e,
                                       'dist': {'line': d_line,
                                                'unfitted': d_unfit}},
                               'n6_g1_dist':
                                   n6['results']['G1_discipline']['dist'],
                               'axis_transfer': transfer},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_discipline_transfer.json')


if __name__ == '__main__':
    main()
