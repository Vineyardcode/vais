#!/usr/bin/env python3
"""
Axis-3 in Hand A (portfolio S3, rung 3b) — is the pre-final-zone rule
absent, inverted, or secretly shared in Currier A? (N6f)

PROVENANCE: N6d found Currier B's placement discipline is exactly three
axes; N6e found axes 1-2 transfer to hand A (rho +0.92/+0.83) while
axis 3 — the pre-final-zone rule — showed a NEGATIVE cross-table
correlation (-0.46). But that number compared two independently-run
SVDs, and components with close singular values can mix identities:
"inverted" could be an artifact of component bookkeeping. This rung
characterizes A's axis-3 content properly.

METHOD (fixed before running): no SVD is run on A at all. B's axes are
loaded from the committed N6d record and held FIXED; hand A's
double-centered log-table is REGRESSED onto each fixed B component:
  beta_k(A) = <resid_A, outer(A_k, V_k)> / ||outer(A_k, V_k)||^2
so beta ~ +1 means A carries the same-shaped rule at B's strength,
0 = absent, negative = reversed. Significance for axis 3 by permutation:
N_NULLS within-line shuffles of A -> null tables -> null |beta_3|
distribution; significant iff |beta_3(A)| exceeds ALL nulls
(p = 1/(N_NULLS+1) < 0.005, the house standard).
CROSS-CHECK (model-free, no SVD anywhere): per-class pre-final-zone
occupancy skew (bins m3 + pL-1, the positive support of B's profile 3)
computed from raw counts in A and B; its A-vs-B Spearman must AGREE IN
SIGN with beta_3 before any directional claim.

GATES: (a) B's table rebuilt here must reproduce the N6d axes
(cross-checked); (b) CONTINUITY — beta_1(A) and beta_2(A) must be
positive and each exceed all N_NULLS nulls (the method must recover the
known axis-1/2 transfer, else it cannot be trusted on axis 3).

PRE-REGISTERED OUTCOMES:
  gate_failed        — any gate fails.
  axis3_absent_in_A  — |beta_3(A)| does not beat the null battery:
                       hand A has no measurable pre-final-zone rule;
                       B's axis 3 is an innovation of B.
  axis3_inverted_in_A— beta_3(A) < 0, beats all nulls, AND the
                       bin-level Spearman is negative: the rule exists
                       in A with REVERSED sign — a qualitative hand
                       difference. SUGGESTIVE, quarantined.
  axis3_shared_weak  — beta_3(A) > 0, beats all nulls, AND the
                       bin-level Spearman is positive: N6e's -0.46 was
                       component-mixing artifact; axis 3 is shared
                       (weaker). SUGGESTIVE, quarantined (revises the
                       N6e reading).
  discordant_methods — beta significant but the bin-level cross-check
                       disagrees in sign: no claim; instrument
                       investigation required.
Vocabulary discipline: characterization of statistics; nothing decoded.
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
from common.core import FOLIO_DIR, ivtff_clean_words, eva_to_glyphs

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 122
N_NULLS = 200
MIN_LINE_WORDS = 5
ALPHA = 0.5
CLASS_K = 12

BINS = ('p1', 'p2', 'm1', 'm2', 'm3', 'pL-1', 'pL')
PREFINAL = ('m3', 'pL-1')     # positive support of B's profile 3 (N6d)
N6D_JSON = 'line_discipline_rank3.json'


def load_vms_hand(hand):
    lines = []
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
    return lines


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


def centered_log(table, classes):
    L = np.array([[math.log(table[c][b]) for b in BINS] for c in classes])
    grand = L.mean()
    row = L.mean(axis=1, keepdims=True) - grand
    col = L.mean(axis=0, keepdims=True) - grand
    return L - grand - row - col


def betas(resid, components):
    out = []
    for comp in components:
        denom = float((comp ** 2).sum())
        out.append(float((resid * comp).sum() / denom) if denom else 0.0)
    return out


def within_line_shuffle(lines, k):
    rng = random.Random(SEED * 1000 + k)
    out = []
    for line in lines:
        l = line[:]
        rng.shuffle(l)
        out.append(l)
    return out


def prefinal_skew(lines, keep):
    """Model-free per-class pre-final-zone occupancy ratio (obs/exp)."""
    per, tot = {}, Counter()
    for line in lines:
        L = len(line)
        for j, w in enumerate(line):
            c = first_glyph(w)
            c = c if c in keep else '#'
            b = position_bin(j, L)
            d = per.setdefault(c, [0, 0])
            d[1] += 1
            if b in PREFINAL:
                d[0] += 1
            tot[b] += 1
    base = sum(tot[b] for b in PREFINAL) / sum(tot.values())
    return {c: (n / m) / base for c, (n, m) in per.items() if m >= 100}


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
    print('AXIS-3 IN HAND A (S3 rung 3b) — absent, inverted, or shared? '
          '(N6f)')
    print('=' * 76)
    print(f'seed={SEED} nulls={N_NULLS} (beat-all, p<0.005) '
          f'prefinal bins={PREFINAL}')

    n6d = json.loads(result_path(N6D_JSON).read_text(encoding='utf-8'))
    axes = n6d['results']['axes']
    classes = sorted(axes['axis1'])
    b_lines = load_vms_hand('B')
    a_lines = load_vms_hand('A')
    keep = set(classes) - {'#'}
    print(f'  corpora: B {len(b_lines)} lines (reference), A '
          f'{len(a_lines)} lines (characterized); {len(classes)} classes')

    # gate (a): rebuild B's table -> its centered residual must project
    # onto its own N6d axes at beta ~ 1
    b_table = build_table(b_lines, keep)
    resid_b = centered_log(b_table, classes)
    comps = []
    for k in (1, 2, 3):
        Ak = np.array([axes[f'axis{k}'][c] for c in classes])
        Vk = np.array([axes[f'profile{k}'][b] for b in BINS])
        comps.append(np.outer(Ak, Vk))
    beta_b = betas(resid_b, comps)
    gate_a = all(abs(x - 1.0) < 0.05 for x in beta_b)
    print(f'  gate a: B self-projection betas '
          f'{[round(x, 3) for x in beta_b]} (each ~1.0) -> '
          f'{"PASS" if gate_a else "FAIL"}')

    # A's projections + null battery
    a_table = build_table(a_lines, keep)
    resid_a = centered_log(a_table, classes)
    beta_a = betas(resid_a, comps)
    null_abs = {1: [], 2: [], 3: []}
    for k in range(N_NULLS):
        nt = build_table(within_line_shuffle(a_lines, k), keep)
        nb = betas(centered_log(nt, classes), comps)
        for i in (1, 2, 3):
            null_abs[i].append(abs(nb[i - 1]))
    sig = {i: abs(beta_a[i - 1]) > max(null_abs[i]) for i in (1, 2, 3)}
    for i in (1, 2, 3):
        print(f'  beta_{i}(A) = {beta_a[i - 1]:+.3f}  null max |beta| '
              f'{max(null_abs[i]):.3f}  -> '
              f'{"significant" if sig[i] else "not significant"}')

    gate_b = sig[1] and sig[2] and beta_a[0] > 0 and beta_a[1] > 0
    print(f'  gate b (continuity: axes 1-2 positive + significant) -> '
          f'{"PASS" if gate_b else "FAIL"}')

    # model-free cross-check
    sk_a = prefinal_skew(a_lines, keep)
    sk_b = prefinal_skew(b_lines, keep)
    common = sorted(set(sk_a) & set(sk_b))
    rho_bins = spearman([sk_a[c] for c in common],
                        [sk_b[c] for c in common])
    print(f'  bin-level pre-final skew, A vs B (Spearman, '
          f'{len(common)} classes): {rho_bins:+.3f}')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    b3 = beta_a[2]
    if not (gate_a and gate_b):
        verdict = 'gate_failed'
        print('    GATE FAILED: no reading.')
    elif not sig[3]:
        verdict = 'axis3_absent_in_A'
        print(f'    AXIS 3 ABSENT IN A: |beta_3| = {abs(b3):.3f} does not '
              'beat the null battery — hand A has no measurable '
              'pre-final-zone rule; B\'s axis 3 is an innovation of B. '
              '(This also resolves N6e\'s -0.46 as noise/component '
              'mixing, not inversion.)')
    elif b3 < 0 and rho_bins < 0:
        verdict = 'axis3_inverted_in_A'
        print(f'    AXIS 3 INVERTED IN A: beta_3 = {b3:+.3f} (beats all '
              f'nulls), bin-level check agrees ({rho_bins:+.3f}) — the '
              'pre-final-zone rule exists in A with REVERSED sign. A '
              'qualitative hand difference. SUGGESTIVE, quarantined.')
    elif b3 > 0 and rho_bins > 0:
        verdict = 'axis3_shared_weak'
        print(f'    AXIS 3 SHARED (WEAK): beta_3 = {b3:+.3f} (beats all '
              f'nulls), bin-level agrees ({rho_bins:+.3f}) — N6e\'s '
              '-0.46 was component mixing; axis 3 is shared. '
              'SUGGESTIVE, quarantined (revises the N6e reading).')
    else:
        verdict = 'discordant_methods'
        print(f'    DISCORDANT METHODS: beta_3 = {b3:+.3f} significant '
              f'but bin-level check is {rho_bins:+.3f} — no claim; '
              'instrument investigation required.')

    with open(result_path('line_discipline_axis3_handA.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'n_nulls': N_NULLS,
                              'min_line_words': MIN_LINE_WORDS,
                              'alpha': ALPHA, 'class_k': CLASS_K,
                              'prefinal_bins': list(PREFINAL),
                              'n6d_json': N6D_JSON},
                   'results': {'beta_b_self': [round(x, 4)
                                               for x in beta_b],
                               'beta_a': [round(x, 4) for x in beta_a],
                               'null_max_abs': {str(i): round(
                                   max(null_abs[i]), 4)
                                   for i in (1, 2, 3)},
                               'significant': {str(i): sig[i]
                                               for i in (1, 2, 3)},
                               'rho_bins': rho_bins,
                               'prefinal_skew_A': {c: round(sk_a[c], 3)
                                                   for c in common},
                               'prefinal_skew_B': {c: round(sk_b[c], 3)
                                                   for c in common},
                               'n_a_lines': len(a_lines),
                               'n_b_lines': len(b_lines)},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_discipline_axis3_handA.json')


if __name__ == '__main__':
    main()
