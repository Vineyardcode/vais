#!/usr/bin/env python3
"""
S7-R (N5) — independent re-implementation of the Currier-B intra-line
ordinal measurement (PHASE8_DRAFT.md §8.7-1)

PURPOSE: the top-ranked weakness of the B ordinal finding is shared
instrument DNA — every S7 rung uses the same features, position bins,
Laplace-smoothed log-loss estimator, and holdout scheme, and the null
batteries randomize data, never design. This instrument re-asks the
core existence question with a methodologically disjoint design.

INDEPENDENCE SCOPE (full disclosure): this is an independent
IMPLEMENTATION, not an independent AUTHOR — the same agent wrote both.
It shares with v1 only what defines the phenomenon: the corpus
(Currier-B lines, file-level $L, >= MIN_LINE_WORDS words), the interior
(positions 3rd..(L-2)th), and the null concept (within-line shuffle =
order destroyed, content kept). Everything else differs:
  v1: raw first character; 7 discrete position bins; Laplace-smoothed
      P(f|bin) holdout log-loss; 10-split folio-holdout medians.
  v2: word class = first EVA GLYPH via common.core.eva_to_glyphs
      (hand-verified in sanity_checks; 'ch'/'sh'/'cth' are classes of
      their own, unlike v1); NO bins — continuous normalized interior
      rank u = (j-2+0.5)/(L-4); NO smoothing, NO training, NO holdout —
      the statistic fits nothing:
        T = sum_c n_c (mean_u_c - mean_u)^2 / sum_c n_c
      (weighted between-class variance of mean interior rank, over
      classes with >= MIN_SUPPORT interior tokens); inference by
      permutation only (N_PERM within-line shuffles, fresh seed).
SENSITIVITY SCOPE (declared): T detects MEAN-rank separation between
classes — the aspect the rung-4 characterization reported (q-/c-/o-
initial early-skew). Structure with identical class means would be
invisible here; a non-replication therefore flags v1 as
design-artifact-SUSPECT, it does not prove artifact.

PRE-REGISTERED CRITERIA:
  GATE: P-REC rejects (p < 0.005) AND P1 latin does not (p >= 0.05)
    AND N1 word-shuffle does not (p >= 0.05), else gate_failed.
  B ADJUDICATION: p < 0.005 -> replicated (the §8.7-1 objection is
    answered at implementation level; author-level independence remains
    open and is stated wherever the finding is reported);
    0.005 <= p < 0.05 -> ambiguous (no claim either way);
    p >= 0.05 -> not_replicated: the v1 finding is flagged
    DESIGN-ARTIFACT-SUSPECT pending a third-party implementation —
    a registered demotion with teeth.
  A is reported observationally.
Vocabulary discipline: unchanged — nothing here decodes anything.
"""
import io
import json
import random
import re
import statistics
import sys
from collections import Counter, defaultdict

from common import result_path
from common.core import DATA_DIR, FOLIO_DIR, eva_to_glyphs, ivtff_clean_words

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 119
N_PERM = 1000
MIN_SUPPORT = 100         # interior tokens per class to enter T
MIN_LINE_WORDS = 5
P_REPLICATE = 0.005
P_NULLBAND = 0.05
PREC_LINES = 4600

CONTROLS = DATA_DIR / 'controls'


def load_control(name):
    p = CONTROLS / f'{name}.txt'
    return [ln.split() for ln in p.read_text(encoding='utf-8').splitlines()
            if len(ln.split()) >= MIN_LINE_WORDS]


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


def build_prec(rng):
    """The S7 positive-control concept (first-letter field pools),
    fresh rng stream."""
    vocab = sorted({w for line in load_control('latin_plain') for w in line})
    pools = [[], [], [], []]
    for w in vocab:
        c = w[0]
        pools[0 if c <= 'f' else 1 if c <= 'm' else 2 if c <= 's' else 3
              ].append(w)
    lines = []
    while len(lines) < PREC_LINES:
        row = [rng.choice(pools[0])]
        row += [rng.choice(pools[1]) for _ in range(rng.randint(1, 3))]
        if rng.random() < 0.5:
            row.append(rng.choice(pools[2]))
        row += [rng.choice(pools[3]) for _ in range(rng.randint(1, 4))]
        if len(row) >= MIN_LINE_WORDS:
            lines.append(row)
    return lines


# ────────────────────────────────────────────────────────────────────
def first_glyph(w):
    g = eva_to_glyphs(w)
    return g[0] if g else w[0]


def rank_statistic(class_lines):
    """T over lines given as per-line class lists. Interior = positions
    2..L-3 (0-based); u = (j-2+0.5)/(L-4). Classes with < MIN_SUPPORT
    interior tokens are excluded from T (declared)."""
    sums = defaultdict(float)
    counts = Counter()
    for cls in class_lines:
        L = len(cls)
        span = L - 4
        for j in range(2, L - 2):
            u = (j - 2 + 0.5) / span
            sums[cls[j]] += u
            counts[cls[j]] += 1
    keep = {c for c, n in counts.items() if n >= MIN_SUPPORT}
    tot_n = sum(counts[c] for c in keep)
    if not keep or tot_n == 0:
        return 0.0, {}
    grand = sum(sums[c] for c in keep) / tot_n
    T = sum(counts[c] * ((sums[c] / counts[c]) - grand) ** 2
            for c in keep) / tot_n
    means = {c: round(sums[c] / counts[c], 4) for c in keep}
    return T, means


def permutation_test(lines, rng):
    class_lines = [[first_glyph(w) for w in line] for line in lines]
    T_real, means = rank_statistic(class_lines)
    n_ge = 0
    for _ in range(N_PERM):
        perm = []
        for cls in class_lines:
            c2 = cls[:]
            rng.shuffle(c2)
            perm.append(c2)
        T_p, _ = rank_statistic(perm)
        if T_p >= T_real:
            n_ge += 1
    p = (1 + n_ge) / (N_PERM + 1)
    counts = Counter(c for cls in class_lines
                     for c in cls[2:len(cls) - 2])
    return {'T': round(T_real, 6), 'n_perm_ge': n_ge,
            'p': round(p, 4), 'n_lines': len(lines),
            'class_means': {c: means[c] for c in sorted(means)},
            'class_support': {c: counts[c] for c in sorted(means)}}


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('S7-R (N5) — independent re-implementation: rank-based ordinal '
          'test')
    print('=' * 76)
    print(f'seed={SEED} perms={N_PERM} min_support={MIN_SUPPORT} '
          f'replicate p<{P_REPLICATE}, null band p>={P_NULLBAND}; '
          'no bins, no smoothing, no holdout — pure permutation')

    corpora = {
        'PREC_records': build_prec(random.Random(SEED)),
        'P1_latin': load_control('latin_plain'),
        'N1_shuffle': load_control('vms_word_shuffle'),
        'VMS_currier_B': load_vms_hand('B'),
        'VMS_currier_A': load_vms_hand('A'),
    }
    rows = {}
    for name, lines in corpora.items():
        rows[name] = permutation_test(lines, random.Random(SEED + 13))
        r = rows[name]
        print(f'  {name:<14} T {r["T"]:.6f}  perms>=T {r["n_perm_ge"]:>4} '
              f' p={r["p"]:.4f}  ({r["n_lines"]} lines, '
              f'{len(r["class_means"])} classes)')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    gate_ok = (rows['PREC_records']['p'] < P_REPLICATE
               and rows['P1_latin']['p'] >= P_NULLBAND
               and rows['N1_shuffle']['p'] >= P_NULLBAND)
    print(f'    gate: PREC p={rows["PREC_records"]["p"]:.4f} (<'
          f'{P_REPLICATE}), P1 p={rows["P1_latin"]["p"]:.4f} (>='
          f'{P_NULLBAND}), N1 p={rows["N1_shuffle"]["p"]:.4f} (>='
          f'{P_NULLBAND}) -> {"PASS" if gate_ok else "FAIL"}')
    pb = rows['VMS_currier_B']['p']
    if not gate_ok:
        verdict = 'gate_failed'
        print('    GATE FAILED: no reading.')
    elif pb < P_REPLICATE:
        verdict = 'replicated'
        print(f'    REPLICATED (B p={pb:.4f} < {P_REPLICATE}): the '
              'intra-line class-ordering signal survives a bin-free, '
              'smoothing-free, holdout-free, EVA-glyph-classed rank '
              'statistic — the §8.7-1 objection is answered at the '
              'IMPLEMENTATION level (author-level independence remains '
              'open, as disclosed).')
    elif pb < P_NULLBAND:
        verdict = 'ambiguous'
        print(f'    AMBIGUOUS (p={pb:.4f}): no claim either way; a third '
              'design is required.')
    else:
        verdict = 'not_replicated'
        print(f'    NOT REPLICATED (p={pb:.4f}): the v1 finding is '
              'flagged DESIGN-ARTIFACT-SUSPECT pending a third-party '
              'implementation.')
    pa = rows['VMS_currier_A']['p']
    print(f'    A (observational): p={pa:.4f}')
    if verdict == 'replicated':
        bm = rows['VMS_currier_B']['class_means']
        ordered = sorted(bm.items(), key=lambda kv: kv[1])
        print('    B class mean interior ranks (early -> late): '
              + '  '.join(f'{c} {u:.3f}' for c, u in ordered))

    with open(result_path('line_ordinal_rank_test.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'n_perm': N_PERM,
                              'min_support': MIN_SUPPORT,
                              'min_line_words': MIN_LINE_WORDS,
                              'p_replicate': P_REPLICATE,
                              'p_nullband': P_NULLBAND,
                              'classes': 'first EVA glyph '
                                         '(common.core.eva_to_glyphs)'},
                   'rows': rows, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_ordinal_rank_test.json')


if __name__ == '__main__':
    main()
