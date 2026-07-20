#!/usr/bin/env python3
"""
Line-Discipline Morphology Derivation (portfolio S3, rung 5) — does the
interior gradient reduce to WITHIN-WORD glyph morphology? (N6h)

PROVENANCE: N6g (rung 4) reduced the two shared discipline axes ~half
to position-independent class properties (log-freq + gallows + word-
length): the EDGE axis passed (R^2 0.53, Grove/LAAFU quantified) but
the INTERIOR gradient missed the bar (R^2 0.50) and the derived table
did not close the moat. The interior gradient's residual — its sh/q-
early -> r-late glyph-identity ordering — was named the program's
sharpest open target. This rung tests a specific structural hypothesis
for that residual.

HYPOTHESIS (fixed before running): the line's interior word-ordering
MIRRORS within-word glyph morphology. In Voynichese, q is almost purely
word-INITIAL (the qo- onset), sh/ch are word-initial benches, while
r/l/n occur later in words. If a word is placed in the line by the
typical WITHIN-WORD position of its first glyph — word-initial-type
glyphs early in the line, word-final-type glyphs late — then the
interior gradient reduces to morphology. This is a position-free
predictor of a position effect: within-WORD position predicting within-
LINE position is a real structural claim, not circular (the two axes
are distinct).

NEW PRINCIPLES (added to N6g's freq+gallows+wlen; all position-free):
  wwpos    = mean normalized within-word position of the class glyph
             over ALL its occurrences in B (0 = always word-initial,
             1 = always word-final); OTHER-class set to the corpus mean.
  finality = fraction of the class glyph's occurrences that are word-
             final.
Method is N6g's, with the 5-principle design matrix; a 3-principle
baseline is refit in-script so the R^2 GAIN attributable to morphology
is measured directly (and cross-checked against the N6g record).

PRE-REGISTERED VERDICTS (focus: the interior gradient, axis 2):
  gate_failed              — N6/N6d cross-checks or the 3-principle
                             baseline (vs N6g) fail to reproduce.
  interior_morphology_reduced — enriched interior R^2 >= R2_TARGET AND
                             the gain over the 3-principle baseline >=
                             DELTA_MIN: the interior gradient is
                             substantially a within-word-morphology
                             effect. If the enriched derived table also
                             closes the moat that is noted as the
                             stronger result. SUGGESTIVE, quarantined.
  modest_improvement       — gain >= DELTA_MODEST but interior R^2 below
                             target: morphology helps but does not
                             dominate the residual.
  no_improvement           — gain < DELTA_MODEST: within-word position
                             does not explain the interior gradient;
                             the residual is deeper still (corpse logged
                             with the beta on wwpos so the sign/size is
                             on record).
Vocabulary discipline: a reduction of statistics to other statistics;
nothing decoded.
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

SEED = 127
S7_SEED = 115
N4_SEED = 118
N_GEN_SEEDS = 5
N_PERM = 200
LAMBDA_GRID = [0.25 * k for k in range(1, 17)]
R2_TARGET = 0.70          # enriched interior R^2 for "reduced"
DELTA_MIN = 0.10          # interior R^2 gain over the 3-principle model
DELTA_MODEST = 0.05
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
N6_JSON = 'line_discipline_tournament.json'
N6D_JSON = 'line_discipline_rank3.json'
N6G_JSON = 'line_discipline_derivation.json'


# ── corpus + instrument (ladder local copies) ───────────────────────
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
    rp, rb = r_profile(lines, folios)
    return {
        'line_init_jsd': round(jsd(init_first, other_first), 4),
        'line_final_jsd': round(jsd(final_last, other_last), 4),
        'interior_gain': interior_gain(lines, folios),
        'r_pos': rp, 'r_bi': rb,
    }


def build_table(lines, keep):
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


def decompose3(table, classes):
    L = np.array([[math.log(table[c][b]) for b in BINS] for c in classes])
    grand = L.mean()
    row = L.mean(axis=1, keepdims=True) - grand
    col = L.mean(axis=0, keepdims=True) - grand
    resid = L - grand - row - col
    u, sv, vt = np.linalg.svd(resid, full_matrices=False)
    axes, profs = [], []
    for k in range(3):
        Ak, Vk = orient(u[:, k] * math.sqrt(sv[k]),
                        vt[k] * math.sqrt(sv[k]))
        axes.append(Ak)
        profs.append(Vk)
    return grand, row, col, axes, profs


def table_from(grand, row, col, axes, profs, classes):
    L = grand + row + col
    for Ak, Vk in zip(axes, profs):
        L = L + np.outer(Ak, Vk)
    P = np.exp(L)
    P = P / P.sum(axis=1, keepdims=True)
    return {c: {b: float(P[i, j]) for j, b in enumerate(BINS)}
            for i, c in enumerate(classes)}


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


def ols_fit(A, M):
    """Return (predicted, R2). M includes the intercept column."""
    beta, *_ = np.linalg.lstsq(M, A, rcond=None)
    pred = M @ beta
    ss_res = float(((A - pred) ** 2).sum())
    ss_tot = float(((A - A.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return pred, r2, beta


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LINE-DISCIPLINE MORPHOLOGY DERIVATION (S3 rung 5) — '
          'reduce the interior gradient? (N6h)')
    print('=' * 76)
    n6 = json.loads(result_path(N6_JSON).read_text(encoding='utf-8'))
    n6d = json.loads(result_path(N6D_JSON).read_text(encoding='utf-8'))
    n6g = json.loads(result_path(N6G_JSON).read_text(encoding='utf-8'))
    print(f'seed={SEED} perms={N_PERM} target R^2>={R2_TARGET}, gain>='
          f'{DELTA_MIN}; principles = freq+gallows+wlen (+ wwpos, '
          'finality = within-word morphology)')

    b_lines, b_folios = load_vms_b()
    fB = feature_vector(b_lines, b_folios)
    for k in LINE_GROUP:
        if abs(fB[k] - n6['results']['B'][k]) > 1e-9:
            raise RuntimeError(f'B feature {k} != N6 record — abort')
    s = {k: v for k, v in n6['results']['noise_scale'].items()}
    bar_line = n6['results']['bar']['line']
    print(f'  B features + bar reproduce N6 (bar_line {bar_line})  '
          'VERIFIED')

    keep = class_map(b_lines)
    classes = sorted(set(keep) | {'#'})
    table = build_table(b_lines, keep)
    grand, row, col, axes, profs = decompose3(table, classes)
    # cross-check axis1 vs N6d record (sign-oriented identically)
    a1_rec = np.array([n6d['results']['axes']['axis1'][c] for c in classes])
    if float(np.abs(axes[0] - a1_rec).max()) > 1e-3:
        raise RuntimeError('rank-3 axis1 != N6d record — abort')
    print('  rank-3 decomposition reproduces the N6d axes  VERIFIED')

    # base principles (N6g) + within-word morphology
    freq = Counter(first_glyph(w) if first_glyph(w) in keep else '#'
                   for line in b_lines for w in line)
    wl = {}
    wwpos_acc = {}          # glyph -> [sum norm-pos, count, final-count]
    for line in b_lines:
        for w in line:
            c = first_glyph(w)
            c = c if c in keep else '#'
            wl.setdefault(c, []).append(len(w))
            gl = eva_to_glyphs(w)
            n = len(gl)
            for i, g in enumerate(gl):
                acc = wwpos_acc.setdefault(g, [0.0, 0, 0])
                acc[0] += (i / (n - 1)) if n > 1 else 0.5
                acc[1] += 1
                if i == n - 1:
                    acc[2] += 1
    corpus_wwpos = (sum(a[0] for a in wwpos_acc.values())
                    / sum(a[1] for a in wwpos_acc.values()))

    def ww(c):   # within-word position of the class glyph
        if c == '#' or c not in wwpos_acc:
            return corpus_wwpos
        a = wwpos_acc[c]
        return a[0] / a[1] if a[1] else corpus_wwpos

    def fin(c):  # word-finality of the class glyph
        if c == '#' or c not in wwpos_acc or wwpos_acc[c][1] == 0:
            return 0.0
        return wwpos_acc[c][2] / wwpos_acc[c][1]

    def z(v):
        return (v - v.mean()) / (v.std() if v.std() > 0 else 1.0)

    col_freq = z(np.array([math.log(freq[c]) for c in classes]))
    col_gal = np.array([1.0 if c and c[0] in GALLOWS else 0.0
                        for c in classes])
    col_wlen = z(np.array([statistics.mean(wl[c]) for c in classes]))
    col_ww = z(np.array([ww(c) for c in classes]))
    col_fin = z(np.array([fin(c) for c in classes]))
    ones = np.ones(len(classes))
    M3 = np.column_stack([ones, col_freq, col_gal, col_wlen])
    M5 = np.column_stack([ones, col_freq, col_gal, col_wlen,
                          col_ww, col_fin])
    print('  within-word position by class (0=initial, 1=final): '
          + '  '.join(f'{c} {ww(c):.2f}' for c in
                      sorted(classes, key=ww)))

    derived_axes = list(axes)
    fit = {}
    prng = np.random.default_rng(SEED)
    names5 = ('const', 'freq', 'gallows', 'wlen', 'wwpos', 'finality')
    for k in (0, 1, 2):
        pred3, r2_3, _ = ols_fit(axes[k], M3)
        pred5, r2_5, beta5 = ols_fit(axes[k], M5)
        nulls = []
        for _ in range(N_PERM):
            perm = axes[k].copy()
            prng.shuffle(perm)
            nulls.append(ols_fit(perm, M5)[1])
        null_mean = float(np.mean(nulls))
        fit[k + 1] = {'r2_3principle': round(r2_3, 4),
                      'r2': round(r2_5, 4),
                      'gain': round(r2_5 - r2_3, 4),
                      'null_r2': round(null_mean, 4),
                      'excess': round(r2_5 - null_mean, 4),
                      'beta': {n: round(float(b), 4)
                               for n, b in zip(names5, beta5)}}
        if k in (0, 1):
            derived_axes[k] = pred5
        b = fit[k + 1]['beta']
        print(f'  axis{k + 1}: R^2 {r2_5:.3f} (3-principle {r2_3:.3f}, '
              f'gain {r2_5 - r2_3:+.3f})  wwpos-beta {b["wwpos"]:+.2f}  '
              f'finality-beta {b["finality"]:+.2f}')

    # cross-check: 3-principle interior R^2 reproduces N6g
    base_ok = abs(fit[2]['r2_3principle']
                  - n6g['results']['fit']['2']['r2']) <= 0.02
    print(f'  gate: 3-principle interior R^2 {fit[2]["r2_3principle"]} '
          f'~ N6g {n6g["results"]["fit"]["2"]["r2"]} -> '
          f'{"PASS" if base_ok else "FAIL"}')

    # enriched derived table (predicted axes 1,2 + measured axis 3)
    dtable = table_from(grand, row, col, derived_axes, profs, classes)
    best_lam, best_err = None, 1e9
    for lam in LAMBDA_GRID:
        g = generate(b_lines, dtable, keep, lam, SEED)
        err = abs(interior_gain(g, b_folios) - fB['interior_gain'])
        if err < best_err:
            best_lam, best_err = lam, err
    vecs = [feature_vector(generate(b_lines, dtable, keep, best_lam,
                                    SEED + 200 + k), b_folios)
            for k in range(N_GEN_SEEDS)]
    mean_vec = {k: statistics.mean(v[k] for v in vecs) for k in fB}
    d_line = round(statistics.mean(abs(mean_vec[k] - fB[k]) / s[k]
                                   for k in LINE_GROUP), 3)
    print(f'  enriched derived table, lambda {best_lam}: D_line {d_line} '
          f'(bar {bar_line}; measured rank-3 was '
          f'{n6d["results"]["G1d"]["dist"]["line"]}; N6g 3-principle was '
          f'{n6g["results"]["derived_d_line"]})')

    # ── pre-registered adjudication (focus: interior gradient) ──────
    print('\n  ADJUDICATION (pre-registered):')
    a2 = fit[2]
    gain, r2 = a2['gain'], a2['r2']
    closes = d_line <= bar_line
    print(f'    interior R^2 {r2} (target {R2_TARGET}), gain over '
          f'3-principle {gain:+.3f} (min {DELTA_MIN}); wwpos-beta '
          f'{a2["beta"]["wwpos"]:+.3f}; derived table closes: {closes}')
    if not base_ok:
        verdict = 'gate_failed'
        print('    GATE FAILED: baseline does not reproduce N6g.')
    elif r2 >= R2_TARGET and gain >= DELTA_MIN:
        verdict = 'interior_morphology_reduced'
        print('    INTERIOR MORPHOLOGY REDUCED: within-word glyph '
              'position captures the interior gradient — the line orders '
              'words by the typical word-position of their first glyph '
              '(word-initial-type early, word-final-type late). '
              + ('The enriched table also CLOSES the moat. '
                 if closes else '')
              + 'SUGGESTIVE, quarantined.')
    elif gain >= DELTA_MODEST:
        verdict = 'modest_improvement'
        print('    MODEST IMPROVEMENT: within-word position helps '
              f'(gain {gain:+.3f}) but the interior gradient is not '
              'dominated by it; residual remains.')
    else:
        verdict = 'no_improvement'
        print('    NO IMPROVEMENT: within-word position does not explain '
              f'the interior gradient (gain {gain:+.3f}); the residual is '
              'deeper. Corpse logged with the wwpos beta.')

    with open(result_path('line_discipline_morphology.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'n_perm': N_PERM,
                              'r2_target': R2_TARGET,
                              'delta_min': DELTA_MIN,
                              'delta_modest': DELTA_MODEST,
                              'principles': ['log_freq', 'gallows',
                                             'wlen', 'wwpos', 'finality'],
                              'lambda_grid': LAMBDA_GRID,
                              'n6_json': N6_JSON, 'n6d_json': N6D_JSON,
                              'n6g_json': N6G_JSON},
                   'results': {'fit': fit, 'base_gate': base_ok,
                               'derived_lambda': best_lam,
                               'derived_d_line': d_line,
                               'bar_line': bar_line,
                               'n6g_3principle_d_line':
                                   n6g['results']['derived_d_line'],
                               'measured_rank3_d_line':
                                   n6d['results']['G1d']['dist']['line'],
                               'wwpos_by_class':
                                   {c: round(ww(c), 4) for c in classes},
                               'classes': classes},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_discipline_morphology.json')


if __name__ == '__main__':
    main()
