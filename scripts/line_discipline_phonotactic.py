#!/usr/bin/env python3
"""
Line-Discipline Phonotactic Residual (portfolio S3, rung 6) — is the
interior-gradient residual phonotactic, or irreducible at class
resolution? (N6i)

PROVENANCE: the interior gradient (shared axis 2) has been progressively
reduced — N6g (freq+gallows+wlen, R^2 0.498), N6h (+ within-word
morphology wwpos+finality, R^2 0.629, the biggest single gain from
wwpos). A residual (~0.37 of the axis) survives. This rung tests
whether that RESIDUAL is glyph-phonotactic.

DOF DISCIPLINE (stated first, because it governs the design): the axis
is defined over only CLASS_K+1 (~13) first-glyph classes. Piling
features onto 13 points inflates R^2 through overfitting, not insight.
So this is NOT a feature dump. It is a RESIDUAL test with an
overfitting-calibrated null: take r2 = axis2 - (N6h 5-principle
prediction), fit a small DECLARED phonotactic feature set to r2, and
require the fit to beat a shuffle-null (r2 permuted, same features
refit) that measures exactly how much a 4-feature fit to 13 points buys
by chance. If it does not beat that null, the residual is declared
IRREDUCIBLE at class-level resolution — a real floor result, not a
failure.

DECLARED PHONOTACTIC FEATURES (position-free, per class glyph, from B's
glyph stream via common.core.eva_to_glyphs; fixed before running):
  succ_entropy = entropy of the glyph immediately FOLLOWING the class
                 glyph across its word occurrences (low = tightly
                 constrained, e.g. q->o).
  pred_entropy = entropy of the preceding glyph.
  e_follow     = fraction of the class glyph's occurrences followed by
                 'e' (the e-platform).
  bench        = 1 if the class glyph is a bench (ch/sh) else 0.
(OTHER-class '#' set to corpus means / bench 0.)

METHOD: rebuild B's rank-3 decomposition (axis 2 cross-checked vs the
N6d record); r2 = axis2 - Mhat5 (the N6h 5-principle OLS prediction);
OLS r2 ~ phonotactic features (R2_phon); N_PERM permutations of r2
refit -> null R^2; excess = R2_phon - mean(null). Per-feature Spearman
with r2 reported. (Closure/generation is NOT re-tested here — this is a
loadings-residual analysis; if the residual is not even phonotactically
structured, closure is moot.)

PRE-REGISTERED VERDICTS:
  gate_failed              — N6/N6d cross-checks fail.
  residual_phonotactic     — R2_phon >= PHON_TARGET AND excess >=
                             EXCESS_MIN: the residual is phonotactically
                             structured; the interior gradient's last
                             piece is glyph-neighbour constraint.
                             SUGGESTIVE, quarantined.
  residual_partly_phonotactic — excess >= EXCESS_MODEST but below
                             target: phonotactics captures some residual.
  residual_irreducible     — excess < EXCESS_MODEST: phonotactic
                             features do not beat the overfitting null;
                             the residual is not reducible to class-level
                             properties at this resolution. A floor —
                             the interior gradient carries irreducible
                             (or sub-class / glyph-pair) structure.
                             Corpse logged with the per-feature Spearman.
Vocabulary discipline: a reduction of statistics; nothing decoded.
"""
import io
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict

import numpy as np

from common import result_path
from common.core import FOLIO_DIR, ivtff_clean_words, eva_to_glyphs

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 130
N_PERM = 2000
PHON_TARGET = 0.5
EXCESS_MIN = 0.15
EXCESS_MODEST = 0.05
CLASS_K = 12
MIN_LINE_WORDS = 5
ALPHA = 0.5

GALLOWS = set('tkpf')
BENCH = {'ch', 'sh'}
BINS = ('p1', 'p2', 'm1', 'm2', 'm3', 'pL-1', 'pL')
N6D_JSON = 'line_discipline_rank3.json'


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


def class_map(lines):
    freq = Counter(first_glyph(w) for line in lines for w in line)
    return {c for c, _ in freq.most_common(CLASS_K)}


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
    axes = []
    for k in range(3):
        Ak, _ = orient(u[:, k] * math.sqrt(sv[k]), vt[k] * math.sqrt(sv[k]))
        axes.append(Ak)
    return axes


def ols_fit(A, M):
    beta, *_ = np.linalg.lstsq(M, A, rcond=None)
    pred = M @ beta
    ss_res = float(((A - pred) ** 2).sum())
    ss_tot = float(((A - A.mean()) ** 2).sum())
    return pred, (1 - ss_res / ss_tot if ss_tot > 0 else 0.0)


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for k, i in enumerate(order):
            r[i] = k
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx)
                    * sum((b - my) ** 2 for b in ry))
    return round(num / den, 3) if den else 0.0


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LINE-DISCIPLINE PHONOTACTIC RESIDUAL (S3 rung 6) — reduce the '
          'residual? (N6i)')
    print('=' * 76)
    n6d = json.loads(result_path(N6D_JSON).read_text(encoding='utf-8'))
    print(f'seed={SEED} perms={N_PERM} phon_target>={PHON_TARGET} '
          f'excess_min>={EXCESS_MIN}; DOF-honest residual test')

    b_lines, _ = load_vms_b()
    keep = class_map(b_lines)
    classes = sorted(set(keep) | {'#'})
    table = build_table(b_lines, keep)
    axis2 = decompose3(table, classes)[1]
    a2_rec = np.array([n6d['results']['axes']['axis2'][c] for c in classes])
    if float(np.abs(axis2 - a2_rec).max()) > 1e-3:
        raise RuntimeError('axis2 != N6d record — abort')
    print('  rank-3 axis 2 reproduces the N6d record  VERIFIED')

    # N6h 5-principle prediction -> residual
    freq = Counter(first_glyph(w) if first_glyph(w) in keep else '#'
                   for line in b_lines for w in line)
    wl, wwpos_acc = {}, {}
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
    corpus_ww = (sum(a[0] for a in wwpos_acc.values())
                 / sum(a[1] for a in wwpos_acc.values()))

    def ww(c):
        a = wwpos_acc.get(c)
        return a[0] / a[1] if (c != '#' and a and a[1]) else corpus_ww

    def fin(c):
        a = wwpos_acc.get(c)
        return a[2] / a[1] if (c != '#' and a and a[1]) else 0.0

    def z(v):
        v = np.asarray(v, float)
        return (v - v.mean()) / (v.std() if v.std() > 0 else 1.0)

    ones = np.ones(len(classes))
    M5 = np.column_stack([
        ones, z([math.log(freq[c]) for c in classes]),
        np.array([1.0 if c and c[0] in GALLOWS else 0.0 for c in classes]),
        z([statistics.mean(wl[c]) for c in classes]),
        z([ww(c) for c in classes]), z([fin(c) for c in classes])])
    pred5, r2_5 = ols_fit(axis2, M5)
    residual = axis2 - pred5
    print(f'  N6h 5-principle interior R^2 {r2_5:.3f}; residual variance '
          f'{float((residual ** 2).sum()):.4f}')

    # phonotactic features from the glyph stream
    succ, pred, efol = defaultdict(Counter), defaultdict(Counter), \
        defaultdict(lambda: [0, 0])
    for line in b_lines:
        for w in line:
            gl = eva_to_glyphs(w)
            for i, g in enumerate(gl):
                nxt = gl[i + 1] if i + 1 < len(gl) else '$'
                prv = gl[i - 1] if i > 0 else '^'
                succ[g][nxt] += 1
                pred[g][prv] += 1
                efol[g][1] += 1
                if nxt == 'e':
                    efol[g][0] += 1

    def ent(counter):
        tot = sum(counter.values())
        return -sum(c / tot * math.log2(c / tot)
                    for c in counter.values() if c) if tot else 0.0

    mean_se = statistics.mean(ent(succ[g]) for g in succ)
    mean_pe = statistics.mean(ent(pred[g]) for g in pred)
    phon = {
        'succ_entropy': np.array([ent(succ[c]) if c in succ else mean_se
                                  for c in classes]),
        'pred_entropy': np.array([ent(pred[c]) if c in pred else mean_pe
                                  for c in classes]),
        'e_follow': np.array([(efol[c][0] / efol[c][1])
                              if (c in efol and efol[c][1]) else 0.0
                              for c in classes]),
        'bench': np.array([1.0 if c in BENCH else 0.0 for c in classes]),
    }
    for name, v in phon.items():
        print(f'  {name:<13} Spearman with residual '
              f'{spearman(list(residual), list(v)):+.3f}')

    Mp = np.column_stack([ones, z(phon['succ_entropy']),
                          z(phon['pred_entropy']), z(phon['e_follow']),
                          phon['bench']])
    _, r2_phon = ols_fit(residual, Mp)
    prng = np.random.default_rng(SEED)
    nulls = []
    for _ in range(N_PERM):
        perm = residual.copy()
        prng.shuffle(perm)
        nulls.append(ols_fit(perm, Mp)[1])
    null_mean = float(np.mean(nulls))
    excess = r2_phon - null_mean
    n_ge = sum(1 for v in nulls if v >= r2_phon)
    p_emp = (1 + n_ge) / (N_PERM + 1)
    print(f'  phonotactic R^2 on residual {r2_phon:.3f}  overfitting-null '
          f'mean {null_mean:.3f} (max {max(nulls):.3f})  excess '
          f'{excess:+.3f}  empirical p {p_emp:.4f}')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    if r2_phon >= PHON_TARGET and excess >= EXCESS_MIN:
        verdict = 'residual_phonotactic'
        print('    RESIDUAL PHONOTACTIC: the interior-gradient residual '
              'is glyph-phonotactic structure above the overfitting '
              'null. SUGGESTIVE, quarantined.')
    elif excess >= EXCESS_MODEST:
        verdict = 'residual_partly_phonotactic'
        print(f'    RESIDUAL PARTLY PHONOTACTIC: phonotactics captures '
              f'some residual (excess {excess:+.3f}) but not to target.')
    else:
        verdict = 'residual_irreducible'
        print(f'    RESIDUAL IRREDUCIBLE (at class resolution): '
              f'phonotactic features do not beat the overfitting null '
              f'(R^2 {r2_phon:.3f} vs null {null_mean:.3f}, excess '
              f'{excess:+.3f}). After frequency, gallows, length, '
              'within-word morphology AND glyph-neighbour phonotactics, '
              'the interior gradient carries structure not reducible to '
              'class-level properties — a floor. It is either genuinely '
              'primitive or lives at sub-class / glyph-pair resolution '
              '(the next frontier). Corpse logged.')

    with open(result_path('line_discipline_phonotactic.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'n_perm': N_PERM,
                              'phon_target': PHON_TARGET,
                              'excess_min': EXCESS_MIN,
                              'excess_modest': EXCESS_MODEST,
                              'features': ['succ_entropy', 'pred_entropy',
                                           'e_follow', 'bench'],
                              'n6d_json': N6D_JSON},
                   'results': {'n6h_interior_r2': round(r2_5, 4),
                               'phon_r2_on_residual': round(r2_phon, 4),
                               'overfitting_null': round(null_mean, 4),
                               'overfitting_null_max': round(max(nulls), 4),
                               'excess': round(excess, 4),
                               'empirical_p': round(p_emp, 4),
                               'per_feature_spearman':
                                   {n: spearman(list(residual), list(v))
                                    for n, v in phon.items()},
                               'classes': classes},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_discipline_phonotactic.json')


if __name__ == '__main__':
    main()
