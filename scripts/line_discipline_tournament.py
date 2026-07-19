#!/usr/bin/env python3
"""
Line-Discipline Tournament (portfolio S3, rung 2) — is Currier B's line
texture REDUCIBLE to (lexicon, class-position table, one knob)? (N6)

PROVENANCE: phase 109 established that no calibrated generator forges
the manuscript, with the line-boundary effects as the universal moat;
the S7 ladder then characterized a robust intra-line ordinal residue in
Currier B (glyph-class-carried, front-loaded); N4 showed B's ordering
profile is language-like plus that residue. This rung asks the
charter's designated promotion question: can a LANGUAGE-LIKE SUBSTRATE
plus a minimal LINE-DISCIPLINE layer reproduce the full line texture
without breaking the features it was not fitted to?

HONEST LABEL (F1/F2 discipline, stated first): this is a DIAGNOSTIC
REDUCTION TEST, not a blind generator — exactly as phase 109 labeled
the word-shuffle "diagnostic, not generator". The discipline layer's
parameters are MEASURED from the target:
  - class-position preference table P(position-bin | first-EVA-glyph
    class), estimated from Currier B (~13 classes x 7 bins of plug-in
    information, Laplace-smoothed), and
  - ONE placement-strength knob LAMBDA, fitted on ONE fitted feature
    (interior ordinal gain) over the declared grid LAMBDA_GRID, then
    frozen.
The registered claim under test is a COMPRESSION claim: "B's line
texture = its lexicon + ~91 measured numbers + one knob". Deriving the
table from an independent mechanism (blind generation) is a future
rung; nothing here is one.

ENTRANTS (all placement-only reassemblies; each line keeps its own
words, so lexicon/length features are held fixed by construction and
every ORDER-SENSITIVE feature remains informative):
  G0  ablation: LAMBDA=0 (uniform within-line shuffle) — the
      N1-word-shuffle analogue. INSTRUMENT GATE: G0 must FAIL the line
      features (else this feature set cannot see the moat).
  G1  the diagnostic: placement weight ~ P(bin|class)^LAMBDA, sampled
      without replacement position-by-position.
  G2  reference true-generator: the latin_verbose control corpus
      re-placed with B's table and G1's LAMBDA (classes missing from
      the table get uniform preference) — reported observationally.

FEATURES (computed identically for B and every entrant; means over
N_GEN_SEEDS generation seeds):
  LINE GROUP (fitted/targeted): line_init_jsd, line_final_jsd
    (first/last-char JSD of edge words vs others, S9 definitions),
    interior ordinal gain (S7 rung-3 instrument, 4 features, split
    seeds fixed at rung-3 values; B's value must reproduce the rung-3
    record or the run aborts), r_pos, r_bi (N4 definitions).
  UNFITTED GROUP (order-sensitive, F5): h2_ratio, adjacent-duplicate
    rate, adjacent-near rate (Levenshtein exactly 1). Also reported
    (held fixed by construction for G0/G1, informative for G2):
    ttr_5000, zipf_alpha, mean_wlen.
Feature noise scale s_f = std over N_REPL folio-drop replicates of B
(floored at S_FLOOR). Distance D_group(X) = mean over the group of
|f(X) - f(B)| / s_f.

FORGEABILITY BAR (phase-109 convention): BAR_group = the same distance
between B's contiguous halves (first-half folios vs second-half). An
entrant "closes" a group iff D_group <= BAR_group.

PRE-REGISTERED OUTCOMES:
  gate_failed             — G0 closes the line group (or B's interior
                            gain fails to reproduce the rung-3 record):
                            instrument cannot discriminate; no reading.
  discipline_insufficient — G1 does not close the line group: the moat
                            is NOT reducible to lexicon + table + knob;
                            the corpse ships with coordinates (which
                            features stayed open).
  partial_forgery_bind    — G1 closes the line group but breaks the
                            unfitted group: buying the moat costs
                            order-texture elsewhere — a new bind
                            theorem, logged like the Timm bind.
  line_texture_reducible  — G1 closes BOTH groups: Currier B's line
                            texture is statistically forgeable from its
                            lexicon plus one measured table and one
                            knob. SUGGESTIVE, quarantined — a major
                            structural claim, and still NOT a decode:
                            it names a mechanism family, not a meaning.
Vocabulary discipline: outcomes speak of reducibility and forgeability
of STATISTICS, never of what the manuscript says.
"""
import io
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict

from common import result_path
from common.core import FOLIO_DIR, DATA_DIR, ivtff_clean_words, \
    eva_to_glyphs, zipf_alpha

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 120
S7_SEED = 115             # rung-3 split-seed base (interior gain gate)
N4_SEED = 118             # family-test seed base (r_pos/r_bi splits)
N_GEN_SEEDS = 5           # generation seeds per entrant
N_REPL = 8                # folio-drop replicates for the noise scale
LAMBDA_GRID = [0.25 * k for k in range(1, 17)]   # 0.25 .. 4.0
S_FLOOR = 1e-4
CLASS_K = 12
MIN_LINE_WORDS = 5
HOLDOUT_FRAC = 0.2
PSEUDO_FOLIO_LINES = 24
ALPHA = 0.5

GALLOWS = set('tkpf')
S7_FEATURES = ('len', 'first', 'last', 'gallows')
INTERIOR = {'m1', 'm2', 'm3'}
LINE_GROUP = ('line_init_jsd', 'line_final_jsd', 'interior_gain',
              'r_pos', 'r_bi')
UNFIT_GROUP = ('h2_ratio', 'adj_dup', 'adj_near')
REPORT_ONLY = ('ttr_5000', 'zipf_alpha', 'mean_wlen')
RUNG3_JSON = 'line_as_record_ordinal.json'
CONTROLS = DATA_DIR / 'controls'


# ── corpus ──────────────────────────────────────────────────────────
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


def load_control(name):
    p = CONTROLS / f'{name}.txt'
    return [ln.split() for ln in p.read_text(encoding='utf-8').splitlines()
            if len(ln.split()) >= MIN_LINE_WORDS]


# ── shared instrument pieces (local copies, prior-rung definitions) ─
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


# ── the discipline layer ────────────────────────────────────────────
def build_table(lines):
    """P(position-bin | class) measured from B, Laplace-smoothed."""
    keep = class_map(lines)
    counts = {}
    for line in lines:
        L = len(line)
        for j, w in enumerate(line):
            c = first_glyph(w)
            c = c if c in keep else '#'
            counts.setdefault(c, Counter())[position_bin(j, L)] += 1
    bins = ('p1', 'p2', 'm1', 'm2', 'm3', 'pL-1', 'pL')
    table = {}
    for c, cnt in counts.items():
        tot = sum(cnt.values())
        table[c] = {b: (cnt.get(b, 0) + ALPHA) / (tot + ALPHA * len(bins))
                    for b in bins}
    return table, keep


def place_line(words, table, keep, lam, rng):
    """Fill positions 0..L-1 sampling without replacement with weight
    P(bin|class)^lam. lam=0 = uniform shuffle (G0)."""
    L = len(words)
    remaining = list(words)
    rng.shuffle(remaining)          # tie-break order is random
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


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LINE-DISCIPLINE TOURNAMENT (S3 rung 2) — reduction test (N6)')
    print('=' * 76)
    print(f'seed={SEED} gen_seeds={N_GEN_SEEDS} repl={N_REPL} '
          f'lambda_grid={LAMBDA_GRID[0]}..{LAMBDA_GRID[-1]} '
          f'bar=contiguous-halves (phase-109 convention)')

    b_lines, b_folios = load_vms_b()
    fB = feature_vector(b_lines, b_folios)
    r3 = json.loads((result_path(RUNG3_JSON)).read_text(encoding='utf-8'))
    r3_gain = r3['results']['VMS_currier_B']['real']['total']
    if abs(fB['interior_gain'] - r3_gain) > 1e-9:
        raise RuntimeError(f'B interior gain {fB["interior_gain"]} != '
                           f'rung-3 record {r3_gain} — abort')
    print(f'  B features reproduce the rung-3 record '
          f'(interior_gain {fB["interior_gain"]:+.4f})  VERIFIED')

    # noise scale from folio-drop replicates
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

    # forgeability bar: contiguous halves
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
    print(f'  bar (contiguous halves): line {bar_line}  unfitted '
          f'{bar_unfit}')

    table, keep = build_table(b_lines)

    # fit LAMBDA on interior gain only (G1 seed 0), declared grid
    best_lam, best_err = None, 1e9
    for lam in LAMBDA_GRID:
        g = generate(b_lines, table, keep, lam, SEED)
        err = abs(interior_gain(g, b_folios) - fB['interior_gain'])
        if err < best_err:
            best_lam, best_err = lam, err
    print(f'  LAMBDA fitted on interior gain only: {best_lam} '
          f'(|err| {best_err:.4f}) — FROZEN')

    entrants = {'G0_ablation': 0.0, 'G1_discipline': best_lam}
    results = {'B': fB, 'bar': {'line': bar_line, 'unfitted': bar_unfit},
               'lambda': best_lam, 'noise_scale': s}
    dists = {}
    for name, lam in entrants.items():
        vecs = [feature_vector(generate(b_lines, table, keep, lam,
                                        SEED + 200 + k), b_folios)
                for k in range(N_GEN_SEEDS)]
        mean_vec = {k: round(statistics.mean(v[k] for v in vecs), 4)
                    for k in fB}
        dists[name] = {'line': dist(mean_vec, fB, LINE_GROUP),
                       'unfitted': dist(mean_vec, fB, UNFIT_GROUP)}
        results[name] = {'features': mean_vec, 'dist': dists[name]}
        print(f'  {name:<14} D_line {dists[name]["line"]:>7}  '
              f'D_unfitted {dists[name]["unfitted"]:>7}')

    # G2 reference: verbose-latin substrate re-placed with B's table
    g2_lines = load_control('latin_verbose')
    g2_folios = [f'blk{i // PSEUDO_FOLIO_LINES}'
                 for i in range(len(g2_lines))]
    g2 = [feature_vector(generate(g2_lines, table, keep, best_lam,
                                  SEED + 300 + k), g2_folios)
          for k in range(N_GEN_SEEDS)]
    g2_vec = {k: round(statistics.mean(v[k] for v in g2), 4) for k in fB}
    results['G2_verbose_ref'] = {
        'features': g2_vec,
        'dist': {'line': dist(g2_vec, fB, LINE_GROUP),
                 'unfitted': dist(g2_vec, fB, UNFIT_GROUP)}}
    print(f'  G2_verbose_ref (observational) D_line '
          f'{results["G2_verbose_ref"]["dist"]["line"]}  D_unfitted '
          f'{results["G2_verbose_ref"]["dist"]["unfitted"]}')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    g0_fails = dists['G0_ablation']['line'] > bar_line
    print(f'    gate: G0 D_line {dists["G0_ablation"]["line"]} must '
          f'exceed bar {bar_line} -> '
          f'{"PASS" if g0_fails else "FAIL"}')
    g1_line = dists['G1_discipline']['line'] <= bar_line
    g1_unfit = dists['G1_discipline']['unfitted'] <= bar_unfit
    if not g0_fails:
        verdict = 'gate_failed'
        print('    GATE FAILED: the ablation already closes the line '
              'group — this feature set cannot see the moat; no reading.')
    elif not g1_line:
        verdict = 'discipline_insufficient'
        print('    DISCIPLINE INSUFFICIENT: lexicon + table + one knob '
              'do NOT close the line group — the moat is not reducible '
              'to placement discipline at this budget. Corpse logged '
              'with coordinates (see per-feature table).')
    elif not g1_unfit:
        verdict = 'partial_forgery_bind'
        print('    PARTIAL FORGERY (BIND): the line group closes but the '
              'unfitted order-texture breaks — buying the moat costs '
              'adjacency/entropy texture. A new bind theorem; logged '
              'with the same prominence as the Timm bind.')
    else:
        verdict = 'line_texture_reducible'
        print('    LINE TEXTURE REDUCIBLE: G1 closes BOTH groups — '
              'Currier B\'s line texture is statistically forgeable '
              'from its lexicon plus one measured class-position table '
              'and one strength knob. SUGGESTIVE, quarantined; a '
              'mechanism-family claim, NOT a decode.')

    with open(result_path('line_discipline_tournament.json'), 'w',
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
                              'rung3_json': RUNG3_JSON},
                   'results': results, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_discipline_tournament.json')


if __name__ == '__main__':
    main()
