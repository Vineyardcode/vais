#!/usr/bin/env python3
"""
Line-as-Record, rung 2 (portfolio S7) — per-hand adjudication

MOTIVATION AND PROVENANCE (disclosed in full, per charter): S7 rung 1
(line_as_record_structures, 2026-07-17) adjudicated on VMS_full and was
KILLED (interior margin +0.033 < 0.05 over the pooled N1 shuffle). Its
log recorded, post hoc, that Currier B alone cleared the margin (+0.077)
while A showed nothing (-0.006). That observation is the reason this
rung exists — which is exactly why this rung may NOT simply re-run the
same test per hand: re-testing the same data with a criterion chosen
because B passed it is the forked-path move the graveyard is full of.

WHY THIS IS A STRICTLY HARDER TEST than the motivating observation:
  (a) PER-HAND NULLS. Rung 1 compared each hand against the POOLED
      word-shuffle — a mismatched baseline (different lexicon and line
      lengths). Here each hand is compared against N_NULLS=20 shuffles
      of ITSELF (word order destroyed corpus-wide within the hand, line
      lengths and folio assignment preserved).
  (b) MULTI-SPLIT STABILITY. Rung 1 used a single folio-holdout split;
      a one-split margin can be split luck. Every statistic here is the
      MEDIAN over R_SPLITS=10 independent folio-holdout splits, and the
      nulls get the identical treatment.
  (c) EMPIRICAL SIGNIFICANCE + EFFECT FLOOR. A hand PASSES only if its
      median gain exceeds ALL 20 of its null medians (empirical
      p ~ 1/21 = 0.048) AND beats the null MEDIAN by >= EFFECT_FLOOR
      = 0.05 bits/token (the rung-1 margin, kept as an effect-size
      floor, not the only bar).
All thresholds fixed before this script's first execution.

INSTRUMENT (unchanged from rung 1, local copies): 4 surface features
(length bucket, first glyph, last glyph, gallows), position bins with
INTERIOR thirds as the headline, Laplace ALPHA, folio-level holdout
(whole folios for VMS hands; PSEUDO_FOLIO_LINES-line blocks for
controls). Gate re-checked per run under the same multi-split scheme:
P-REC median >= GATE_PREC_MIN and P1 median <= GATE_P1_MAX.

PRE-REGISTERED OUTCOMES (tools/overnight.py re-derives mechanically):
  gate_failed        — instrument gate failed; no interpretation.
  killed_split_luck  — NEITHER hand passes: the rung-1 B observation
                       was split luck / baseline mismatch; corpse
                       logged, per-hand S7 dies at this instrument.
  B_only             — B passes, A fails: consistent with line-level
                       field structure in Currier B only (SUGGESTIVE,
                       quarantined; matches the motivating pattern but
                       is only now, for the first time, a registered
                       test of it).
  A_only             — A passes, B fails: contrary to the motivating
                       pattern; reported SUGGESTIVE with an explicit
                       extra-suspicion flag (the motivating observation
                       failed to replicate while its complement fired).
  both               — both hands pass: consistent with per-hand field
                       structure (SUGGESTIVE, quarantined).
Vocabulary discipline: no outcome names a field or reads a record.
"""
import io
import json
import math
import random
import re
import statistics
import sys
from collections import Counter

from common import result_path
from common.core import DATA_DIR, FOLIO_DIR, ivtff_clean_words

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 114
R_SPLITS = 10             # independent folio-holdout splits per statistic
N_NULLS = 20              # per-hand null shuffles (empirical p ~ 1/21)
EFFECT_FLOOR = 0.05       # bits/token over the null MEDIAN (rung-1 margin)
GATE_PREC_MIN = 0.30
GATE_P1_MAX = 0.05
MIN_LINE_WORDS = 5
HOLDOUT_FRAC = 0.2
PSEUDO_FOLIO_LINES = 24
ALPHA = 0.5
PREC_LINES = 4600

CONTROLS = DATA_DIR / 'controls'
GALLOWS = set('tkpf')


# ────────────────────────────────────────────────────────────────────
# corpora (local copies of the rung-1 loaders)
# ────────────────────────────────────────────────────────────────────
def load_control(name):
    p = CONTROLS / f'{name}.txt'
    return [ln.split() for ln in p.read_text(encoding='utf-8').splitlines()
            if len(ln.split()) >= MIN_LINE_WORDS]


def load_vms_by_currier():
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
    """Rung-1's corrected P-REC (marginally distinct first-letter pools)."""
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


def null_shuffle(lines, k):
    """Within-corpus word-order shuffle preserving line lengths (and,
    by index, folio assignment) — the per-hand artifact baseline."""
    rng = random.Random(SEED * 1000 + k)
    words = [w for line in lines for w in line]
    rng.shuffle(words)
    out, i = [], 0
    for line in lines:
        out.append(words[i:i + len(line)])
        i += len(line)
    return out


# ────────────────────────────────────────────────────────────────────
# instrument (local copies of rung 1)
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


def features(w):
    return {'len': str(min(len(w), 7)) if len(w) < 7 else '7+',
            'first': w[0],
            'last': w[-1],
            'gallows': '1' if any(c in GALLOWS for c in w) else '0'}


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

INTERIOR = {'m1', 'm2', 'm3'}
FEATURE_NAMES = ('len', 'first', 'last', 'gallows')


def interior_gain(lines, folios, rng):
    """Held-out interior log-loss reduction of P(f|bin) vs P(f),
    bits/token (one split)."""
    train_idx, hold_idx = holdout_split(lines, folios, rng)
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
    cats = {f: sorted(global_c[f]) for f in FEATURE_NAMES}

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
            fe = features(w)
            for f in FEATURE_NAMES:
                bc = bin_c[f].get(b, Counter())
                s += (logp(bc, fe[f], cats[f])
                      - logp(global_c[f], fe[f], cats[f]))
            n += 1
    return s / n if n else 0.0


def median_gain(lines, folios):
    """Median interior gain over R_SPLITS independent holdout splits."""
    gains = [interior_gain(lines, folios, random.Random(SEED + 7 + r))
             for r in range(R_SPLITS)]
    return round(statistics.median(gains), 4), [round(g, 4) for g in gains]


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LINE-AS-RECORD, RUNG 2 (S7) — per-hand adjudication')
    print('=' * 76)
    print(f'seed={SEED} splits={R_SPLITS} nulls/hand={N_NULLS} '
          f'effect_floor={EFFECT_FLOOR} gates: P-REC>={GATE_PREC_MIN}, '
          f'P1<={GATE_P1_MAX} (all statistics = median over splits)')

    vms = load_vms_by_currier()
    results = {}

    # instrument gate under the multi-split scheme
    for cname, lines, folios in [
            ('PREC_records', build_prec(random.Random(SEED)), None),
            ('P1_latin_plain', load_control('latin_plain'), None)]:
        med, gains = median_gain(lines, folios)
        results[cname] = {'median_gain': med, 'split_gains': gains,
                          'n_lines': len(lines)}
        print(f'  {cname:<16} median interior {med:+.4f} bits/token '
              f'({len(lines)} lines)')
    prec = results['PREC_records']['median_gain']
    p1 = results['P1_latin_plain']['median_gain']
    gate_ok = prec >= GATE_PREC_MIN and p1 <= GATE_P1_MAX
    print(f'  gate: {"PASS" if gate_ok else "FAIL"}')

    # per-hand statistic vs per-hand null battery
    for hand in ('A', 'B'):
        lines, folios = vms[hand]
        med, gains = median_gain(lines, folios)
        null_meds = []
        for k in range(N_NULLS):
            nm, _ = median_gain(null_shuffle(lines, k), folios)
            null_meds.append(nm)
        beat_all = med > max(null_meds)
        margin = round(med - statistics.median(null_meds), 4)
        passed = beat_all and margin >= EFFECT_FLOOR
        results[f'VMS_currier_{hand}'] = {
            'median_gain': med, 'split_gains': gains,
            'null_medians': sorted(null_meds),
            'null_max': max(null_meds),
            'null_median': round(statistics.median(null_meds), 4),
            'margin_over_null_median': margin,
            'beats_all_nulls': beat_all, 'pass': passed,
            'n_lines': len(lines)}
        print(f'  Currier {hand}: median {med:+.4f}  null max '
              f'{max(null_meds):+.4f}  null median '
              f'{statistics.median(null_meds):+.4f}  margin {margin:+.4f} '
              f'-> {"PASS" if passed else "fail"}')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    a = results['VMS_currier_A']['pass']
    b = results['VMS_currier_B']['pass']
    if not gate_ok:
        verdict = 'gate_failed'
        print('    INSTRUMENT GATE FAILED: no interpretation.')
    elif not a and not b:
        verdict = 'killed_split_luck'
        print('    KILLED: neither hand passes the per-hand null battery — '
              'the rung-1 Currier-B observation was split luck / baseline '
              'mismatch. Corpse logged.')
    elif b and not a:
        verdict = 'B_only'
        print('    B ONLY: consistent with line-level field structure in '
              'Currier B (SUGGESTIVE, quarantined; first registered test '
              'of the rung-1 observation). NOT a decode.')
    elif a and not b:
        verdict = 'A_only'
        print('    A ONLY (contrary to the motivating pattern): SUGGESTIVE '
              'with extra suspicion — the motivating observation failed to '
              'replicate while its complement fired.')
    else:
        verdict = 'both'
        print('    BOTH hands pass: consistent with per-hand field '
              'structure (SUGGESTIVE, quarantined). NOT a decode.')

    with open(result_path('line_as_record_per_hand.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'r_splits': R_SPLITS,
                              'n_nulls': N_NULLS,
                              'effect_floor': EFFECT_FLOOR,
                              'gate_prec_min': GATE_PREC_MIN,
                              'gate_p1_max': GATE_P1_MAX,
                              'min_line_words': MIN_LINE_WORDS,
                              'holdout_frac': HOLDOUT_FRAC,
                              'holdout_unit': 'folio',
                              'pseudo_folio_lines': PSEUDO_FOLIO_LINES,
                              'alpha': ALPHA},
                   'results': results, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_as_record_per_hand.json')


if __name__ == '__main__':
    main()
