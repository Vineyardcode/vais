#!/usr/bin/env python3
"""
Line-Discipline Principled Derivation (portfolio S3, rung 4) — do the
two manuscript-wide axes REDUCE to position-independent class
properties? (N6g)

PROVENANCE: the discipline ladder established that Currier B's line
texture is three placement rules (N6d), two of them manuscript-wide
(N6e): axis 1 (edge/paragraph) and axis 2 (interior gradient). Every
rung so far MEASURED the class-position table from the manuscript. This
rung asks the standing "derive from principles" question at the level
that is honestly buildable.

SCOPE DISCLOSURE (stated first): "principles" here means POSITION-
INDEPENDENT CLASS PROPERTIES measured from the token stream — glyph
frequency, gallows-membership, word length — NONE of which carry any
position information. Showing that a class's line-PLACEMENT loading is a
lawful function of these is a REDUCTIVE derivation: the discipline
stops being an arbitrary ~13-number per-axis table and becomes a few
coefficients on interpretable properties. It is NOT derivation from a
mechanism outside the manuscript (scribal layout physics, paragraph
mechanics) — that remains the open frontier and is not claimed here.

DECLARED PRINCIPLES (fixed before running; all position-free, per
class over the top-CLASS_K first-EVA-glyph classes + OTHER):
  freq    = log token frequency of the class in Currier B
  gallows = 1 if the class glyph is a gallows base (t/k/p/f) else 0
  wlen    = mean word length of the class's tokens
(z-scored; a constant term is included.)

METHOD: rebuild B's rank-3 decomposition (cross-checked against the
N6d axes); for each shared axis k in {1,2}, ordinary least squares
A_k ~ 1 + freq + gallows + wlen over the classes, giving predicted
loadings Ahat_k and R^2. Calibration: the same fit on N_PERM
permutations of A_k gives a chance-R^2 null; excess = R^2 - mean null.
Then the DERIVED table replaces axis-1 and axis-2 loadings with
Ahat_1, Ahat_2 (profiles, row/col/grand, and the B-specific axis 3 kept
as measured), refits the single strength knob on interior gain, places
B's own lines, and its line-group distance D_line is scored against the
phase-109 contiguous-halves bar (bar, noise scale, and B's feature
vector are loaded from the committed N6 record; run ABORTS on any
cross-check mismatch). Axis 3's R^2 is reported observationally
(expected LOW — it is B-specific and not claimed derivable).

PRE-REGISTERED VERDICTS:
  gate_failed          — N6/N6d cross-checks fail to reproduce.
  shared_axes_derived  — BOTH shared axes have R^2 excess >= R2_EXCESS
                         over their shuffle null AND the derived-axes
                         table closes the line group (D_line <=
                         bar_line): the two manuscript-wide rules reduce
                         to frequency + gallows + length. SUGGESTIVE,
                         quarantined — the discipline is explained, not
                         just described, at the reductive level.
  axis1_only           — only axis 1 (edge) qualifies (excess and, with
                         axis 2 kept measured, closure holds): the
                         edge rule reduces to the principles (Grove/
                         LAAFU made quantitative), the interior gradient
                         does not. SUGGESTIVE, quarantined.
  not_derived          — neither shared axis reduces / the derived
                         table fails to close: the discipline is not
                         captured by these principles; corpse logged
                         with the per-axis R^2 so the next candidate
                         principle set is informed.
Vocabulary discipline: a reduction of statistics to other statistics;
nothing about the manuscript's meaning is claimed or decoded.
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

SEED = 126
S7_SEED = 115
N4_SEED = 118
N_GEN_SEEDS = 5
N_PERM = 200
LAMBDA_GRID = [0.25 * k for k in range(1, 17)]
R2_EXCESS = 0.25          # min R^2 above the shuffle null for "derived"
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
    print('LINE-DISCIPLINE PRINCIPLED DERIVATION (S3 rung 4) — reduce '
          'the shared axes? (N6g)')
    print('=' * 76)
    n6 = json.loads(result_path(N6_JSON).read_text(encoding='utf-8'))
    n6d = json.loads(result_path(N6D_JSON).read_text(encoding='utf-8'))
    print(f'seed={SEED} perms={N_PERM} r2_excess>={R2_EXCESS}; '
          'principles = log-freq + gallows + word-length (position-free)')

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

    # principles (position-independent) per class
    freq = Counter(first_glyph(w) if first_glyph(w) in keep else '#'
                   for line in b_lines for w in line)
    wl = {}
    for line in b_lines:
        for w in line:
            c = first_glyph(w)
            c = c if c in keep else '#'
            wl.setdefault(c, []).append(len(w))
    P = {'freq': np.array([math.log(freq[c]) for c in classes]),
         'gallows': np.array([1.0 if c and c[0] in GALLOWS else 0.0
                              for c in classes]),
         'wlen': np.array([statistics.mean(wl[c]) for c in classes])}
    def z(v):
        return (v - v.mean()) / (v.std() if v.std() > 0 else 1.0)
    M = np.column_stack([np.ones(len(classes)), z(P['freq']),
                         P['gallows'], z(P['wlen'])])

    derived_axes = list(axes)
    fit = {}
    prng = np.random.default_rng(SEED)
    for k in (0, 1, 2):
        pred, r2, beta = ols_fit(axes[k], M)
        nulls = []
        for _ in range(N_PERM):
            perm = axes[k].copy()
            prng.shuffle(perm)
            nulls.append(ols_fit(perm, M)[1])
        null_mean = float(np.mean(nulls))
        excess = r2 - null_mean
        fit[k + 1] = {'r2': round(r2, 4), 'null_r2': round(null_mean, 4),
                      'excess': round(excess, 4),
                      'beta': {n: round(float(b), 4) for n, b in
                               zip(('const', 'freq', 'gallows', 'wlen'),
                                   beta)}}
        if k in (0, 1):
            derived_axes[k] = pred
        print(f'  axis{k + 1}: R^2 {r2:.3f}  null {null_mean:.3f}  '
              f'excess {excess:+.3f}   beta '
              + ' '.join(f'{n}{b:+.2f}' for n, b in
                         fit[k + 1]['beta'].items() if n != 'const'))

    # derived table: predicted shared axes (1,2) + measured axis 3
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
    print(f'  derived-axes table (Ahat_1, Ahat_2 + measured axis3), '
          f'lambda {best_lam}: D_line {d_line} (bar {bar_line}; measured '
          f'rank-3 was {n6d["results"]["G1d"]["dist"]["line"]})')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    a1_ok = fit[1]['excess'] >= R2_EXCESS
    a2_ok = fit[2]['excess'] >= R2_EXCESS
    closes = d_line <= bar_line
    print(f'    axis1 excess {fit[1]["excess"]:+.3f} (>= {R2_EXCESS}: '
          f'{a1_ok}); axis2 excess {fit[2]["excess"]:+.3f} ({a2_ok}); '
          f'derived table closes: {closes}')
    print(f'    (axis3 excess {fit[3]["excess"]:+.3f} — reported, '
          'expected low: B-specific)')
    gate = True  # cross-checks already enforced above
    if not gate:
        verdict = 'gate_failed'
    elif a1_ok and a2_ok and closes:
        verdict = 'shared_axes_derived'
        print('    SHARED AXES DERIVED: both manuscript-wide rules reduce '
              'to log-frequency + gallows + word-length, and the derived '
              'table still closes the moat. The discipline is explained '
              '(reductively), not just described. SUGGESTIVE, '
              'quarantined; external-mechanism derivation still open.')
    elif a1_ok and closes:
        verdict = 'axis1_only'
        print('    AXIS 1 ONLY: the edge/paragraph rule reduces to the '
              'principles (Grove/LAAFU made quantitative) and closure '
              'holds; the interior gradient (axis 2) does not reduce to '
              'this property set. SUGGESTIVE, quarantined.')
    else:
        verdict = 'not_derived'
        print('    NOT DERIVED: the shared axes are not captured by '
              'log-frequency + gallows + word-length at the closure bar '
              '— the discipline is not (yet) reducible to these '
              'principles. Corpse logged with per-axis R^2 for the next '
              'candidate set.')

    with open(result_path('line_discipline_derivation.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'n_perm': N_PERM,
                              'r2_excess': R2_EXCESS,
                              'principles': ['log_freq', 'gallows',
                                             'wlen'],
                              'lambda_grid': LAMBDA_GRID,
                              'n6_json': N6_JSON, 'n6d_json': N6D_JSON},
                   'results': {'fit': fit, 'derived_lambda': best_lam,
                               'derived_d_line': d_line,
                               'bar_line': bar_line,
                               'measured_rank3_d_line':
                                   n6d['results']['G1d']['dist']['line'],
                               'classes': classes},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_discipline_derivation.json')


if __name__ == '__main__':
    main()
