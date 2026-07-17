#!/usr/bin/env python3
"""
Line-as-Record Structures (portfolio S7) — positional field information

HYPOTHESIS (SPECULATIVE tier, RESEARCH.md): the LINE, not the word, is
the encoding unit — each line a RECORD with ordered fields drawing on
field-specific vocabularies (inventory rows, tables, recipe headers).
Motivation: the line-boundary effects are the moat (line_init_jsd 0.164
/ line_final_jsd 0.084 vs ~0.001 for prose; no calibrated generator in
the forgery tournament reproduces them). S7 is the only portfolio
strategy that models the line directly, relaxing assumption A3.

WHAT IS MEASURED (fixed feature set — the declared DOF budget):
  Per token, 4 surface features requiring NO parser assumptions:
    word-length bucket (1..6, 7+), first glyph, last glyph,
    gallows presence (contains t/k/p/f).
  Per line of >= MIN_LINE_WORDS words, positions are binned:
    p1, p2 (first two), pL-1, pL (last two), and the INTERIOR split
    into fractional thirds m1/m2/m3.
  On TRAIN folios, per-bin feature distributions P(f|bin) are estimated
  with Laplace ALPHA; on HELD-OUT folios the mean log-loss reduction vs
  the position-agnostic P(f) is measured in bits/token ("positional
  gain"), per feature and summed. Holdout = whole folios (VMS) /
  contiguous PSEUDO_FOLIO_LINES-line blocks (controls) — the rung-3
  lesson from verbose_cipher_inversion.
  HEADLINE = INTERIOR gain (m1+m2+m3 tokens only). The line EDGES are
  the already-established anomaly; RECORDS require interior field
  structure, which prose does not have. Edge gain is reported for the
  record but adjudicates nothing.

CORPORA (controls FIRST, per charter):
  P-REC  synthetic record corpus (positive control, generated here,
         deterministic SEED): P1's Latin vocabulary partitioned into 4
         disjoint field pools by a fixed surface hash; each line = field
         sequence 1,[2],3+ with optional/repeatable fields (variable
         length 3-10). The instrument MUST detect this or it is dead.
  P1     latin_plain — genuine prose in pseudo-lines: must show ~zero
         positional gain (its "lines" are arbitrary chunk boundaries).
  N1     vms_word_shuffle — THE pre-registered kill comparator: the
         manuscript's own tokens and line lengths, order destroyed;
         whatever "structure" it shows is line-length + lexicon
         artifact, not records.
  N3     grille_table — table-generated words, no line semantics.
  VMS    full, Currier A, Currier B separately (constraint F8).

PRE-REGISTERED ADJUDICATION (fixed 2026-07-17, before the first run;
tools/overnight.py re-derives it mechanically from the JSON):
  INSTRUMENT GATE: P-REC interior gain >= 0.30 bits/token AND P1
    interior gain <= 0.05 bits/token. Fail -> instrument too weak or
    too loose; NO VMS interpretation.
  KILL: VMS_full interior gain - N1 interior gain < 0.05 bits/token ->
    VMS positional structure is a line-length artifact; the record
    hypothesis loses this instrument (corpse logged with full numbers).
  POSITIVE (quarantined SUGGESTIVE, never "decoded"): VMS_full beats N1
    by >= 0.05 AND Currier A and B EACH beat N1 by >= 0.05 (F8
    concordance). Discordant hands -> "no claim; discordance is data".
Vocabulary discipline: a positive here means "consistent with
line-level field structure" — it names no fields and reads no records.
"""
import io
import json
import math
import random
import re
import sys
from collections import Counter

from common import result_path
from common.core import DATA_DIR, FOLIO_DIR, ivtff_clean_words

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 113
MIN_LINE_WORDS = 5        # lines below this have no interior; excluded
HOLDOUT_FRAC = 0.2
PSEUDO_FOLIO_LINES = 24   # controls lack folios (VMS mean 23.2 lines)
ALPHA = 0.5               # Laplace smoothing for P(f|bin) and P(f)
PREC_LINES = 4600         # size-match the manuscript's line count
GATE_PREC_MIN = 0.30      # instrument gate: P-REC interior gain >= this
GATE_P1_MAX = 0.05        # instrument gate: P1 interior gain <= this
KILL_MARGIN = 0.05        # VMS - N1 interior margin (bits/token)

CONTROLS = DATA_DIR / 'controls'
GALLOWS = set('tkpf')


# ────────────────────────────────────────────────────────────────────
# corpora
# ────────────────────────────────────────────────────────────────────
def load_control(name):
    p = CONTROLS / f'{name}.txt'
    return [ln.split() for ln in p.read_text(encoding='utf-8').splitlines()
            if len(ln.split()) >= MIN_LINE_WORDS]


def load_vms_by_currier():
    """{'full'|'A'|'B': (lines, folio_ids)} via the markup-clean cleaner
    (finding T1); folio ids parallel to lines for whole-folio holdout."""
    out = {'full': ([], []), 'A': ([], []), 'B': ([], [])}
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        lang = m.group(1) if m else None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if len(words) < MIN_LINE_WORDS:
                continue
            for key in (('full', lang) if lang in ('A', 'B') else ('full',)):
                out[key][0].append(words)
                out[key][1].append(fpath.stem)
    return out


def build_prec(rng):
    """P-REC synthetic record corpus (positive control). Vocabulary from
    the P1 control, partitioned into 4 disjoint field pools by FIRST
    LETTER band, so pools differ in the MARGINAL surface statistics the
    instrument measures — as the fields of a real inventory (numerals,
    names, units, notes) do.
    CONTROL-DESIGN CORRECTION (2026-07-17, logged per charter): v1
    partitioned pools by (len+ord(first)) % 4, which differs only in the
    JOINT (length, first) distribution while every measured MARGINAL
    stays near-uniform — the positive control was invisible to this
    (deliberately marginal) instrument by construction, and the gate
    failed at P-REC -0.01. Pools were redesigned to be marginally
    distinct; the pre-registered gate/kill THRESHOLDS are untouched.
    (Sequence disclosure: the v1 run had already printed VMS rows —
    interior ~ +0.02/-0.01/+0.07, edges ~ +0.3-0.4 — before the
    correction; the redesign uses none of those numbers.)
    Schema per line: field0, field1 x1-3, [field2 optional p=0.5],
    field3 x1-4  -> line length 3-9 (only >= MIN_LINE_WORDS kept)."""
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
# holdout split (whole folios / pseudo-folio blocks; cf. rung 3)
# ────────────────────────────────────────────────────────────────────
def holdout_split(lines, folios, rng):
    if folios is None:
        folios = [i // PSEUDO_FOLIO_LINES for i in range(len(lines))]
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


# ────────────────────────────────────────────────────────────────────
# features and position bins
# ────────────────────────────────────────────────────────────────────
def features(w):
    return {'len': str(min(len(w), 7)) if len(w) < 7 else '7+',
            'first': w[0],
            'last': w[-1],
            'gallows': '1' if any(c in GALLOWS for c in w) else '0'}


def position_bin(i, L):
    """p1/p2 | m1/m2/m3 (interior thirds) | pL-1/pL."""
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

INTERIOR = {'m1', 'm2', 'm3'}
FEATURE_NAMES = ('len', 'first', 'last', 'gallows')


def positional_gain(lines, folios, rng):
    """Held-out log-loss reduction of P(f|bin) vs P(f), bits/token,
    split into interior and edge bins. Returns the result row."""
    train_idx, hold_idx = holdout_split(lines, folios, rng)

    # train counts
    global_c = {f: Counter() for f in FEATURE_NAMES}
    bin_c = {f: {} for f in FEATURE_NAMES}
    for i in train_idx:
        line = lines[i]
        L = len(line)
        for pos, w in enumerate(line):
            b = position_bin(pos, L)
            fe = features(w)
            for f in FEATURE_NAMES:
                global_c[f][fe[f]] += 1
                bin_c[f].setdefault(b, Counter())[fe[f]] += 1

    # category spaces fixed from train (unseen holdout values smoothed in)
    cats = {f: sorted(global_c[f]) for f in FEATURE_NAMES}

    def logp(counter, val, catlist):
        tot = sum(counter.values())
        v = len(catlist) + 1              # +1: unseen-category slot
        return math.log2((counter.get(val, 0) + ALPHA) / (tot + ALPHA * v))

    sums = {'interior': [0.0, 0], 'edge': [0.0, 0]}
    per_feature = {f: [0.0, 0] for f in FEATURE_NAMES}
    for i in hold_idx:
        line = lines[i]
        L = len(line)
        for pos, w in enumerate(line):
            b = position_bin(pos, L)
            region = 'interior' if b in INTERIOR else 'edge'
            fe = features(w)
            tok_gain = 0.0
            for f in FEATURE_NAMES:
                bc = bin_c[f].get(b, Counter())
                g = (logp(bc, fe[f], cats[f])
                     - logp(global_c[f], fe[f], cats[f]))
                tok_gain += g
                if region == 'interior':
                    per_feature[f][0] += g
                    per_feature[f][1] += 1
            sums[region][0] += tok_gain
            sums[region][1] += 1

    def mean(pair):
        return round(pair[0] / pair[1], 4) if pair[1] else 0.0

    return {'n_lines': len(lines),
            'n_train_lines': len(train_idx), 'n_hold_lines': len(hold_idx),
            'interior_gain': mean(sums['interior']),
            'interior_tokens': sums['interior'][1],
            'edge_gain': mean(sums['edge']),
            'edge_tokens': sums['edge'][1],
            'per_feature_interior': {f: mean(p)
                                     for f, p in per_feature.items()}}


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LINE-AS-RECORD STRUCTURES (S7) — positional field information')
    print('=' * 76)
    print(f'seed={SEED} min_line={MIN_LINE_WORDS} holdout={HOLDOUT_FRAC} '
          f'(whole folios; controls: {PSEUDO_FOLIO_LINES}-line blocks) '
          f'alpha={ALPHA}')
    print(f'gates: P-REC interior >= {GATE_PREC_MIN}, P1 interior <= '
          f'{GATE_P1_MAX}, kill margin (VMS - N1) < {KILL_MARGIN}')

    vms = load_vms_by_currier()
    corpora = [
        ('PREC_records', build_prec(random.Random(SEED)), None),
        ('P1_latin_plain', load_control('latin_plain'), None),
        ('N1_word_shuffle', load_control('vms_word_shuffle'), None),
        ('N3_grille', load_control('grille_table'), None),
        ('VMS_full',) + vms['full'],
        ('VMS_currier_A',) + vms['A'],
        ('VMS_currier_B',) + vms['B'],
    ]

    results = {}
    for cname, lines, folios in corpora:
        row = positional_gain(lines, folios, random.Random(SEED + 7))
        results[cname] = row
        print(f'  {cname:<16} interior {row["interior_gain"]:+.4f} '
              f'bits/token ({row["interior_tokens"]:>6} tok)   edge '
              f'{row["edge_gain"]:+.4f} ({row["edge_tokens"]:>6} tok)')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    prec = results['PREC_records']['interior_gain']
    p1 = results['P1_latin_plain']['interior_gain']
    n1 = results['N1_word_shuffle']['interior_gain']
    gate_ok = prec >= GATE_PREC_MIN and p1 <= GATE_P1_MAX
    print(f'    gate: P-REC {prec:+.4f} (need >= {GATE_PREC_MIN}) and '
          f'P1 {p1:+.4f} (need <= {GATE_P1_MAX}) -> '
          f'{"PASS" if gate_ok else "FAIL"}')
    verdict = None
    if not gate_ok:
        verdict = 'instrument_gate_failed'
        print('    INSTRUMENT GATE FAILED: no VMS interpretation.')
    else:
        margins = {v: round(results[v]['interior_gain'] - n1, 4)
                   for v in ('VMS_full', 'VMS_currier_A', 'VMS_currier_B')}
        print(f'    N1 artifact baseline: {n1:+.4f}; VMS margins over N1: '
              + ', '.join(f'{v} {m:+.4f}' for v, m in margins.items()))
        if margins['VMS_full'] < KILL_MARGIN:
            verdict = 'killed_line_length_artifact'
            print(f'    KILL: VMS_full margin {margins["VMS_full"]:+.4f} '
                  f'< {KILL_MARGIN} — interior positional structure is a '
                  'line-length artifact at this instrument.')
        elif all(m >= KILL_MARGIN for m in margins.values()):
            verdict = 'consistent_with_records'
            print('    POSITIVE (quarantined): all three VMS rows beat the '
                  'N1 artifact baseline — CONSISTENT WITH line-level field '
                  'structure. NOT a decode; names no fields.')
        else:
            verdict = 'discordant_hands'
            print('    DISCORDANT: VMS_full beats N1 but Currier hands '
                  'disagree — no claim (discordance is data, F8).')

    with open(result_path('line_as_record_structures.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'min_line_words': MIN_LINE_WORDS,
                              'holdout_frac': HOLDOUT_FRAC,
                              'holdout_unit': 'folio',
                              'pseudo_folio_lines': PSEUDO_FOLIO_LINES,
                              'alpha': ALPHA,
                              'gate_prec_min': GATE_PREC_MIN,
                              'gate_p1_max': GATE_P1_MAX,
                              'kill_margin': KILL_MARGIN},
                   'results': results, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_as_record_structures.json')


if __name__ == '__main__':
    main()
