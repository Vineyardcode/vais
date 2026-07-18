#!/usr/bin/env python3
"""
Line-as-Record, rung 3 (portfolio S7) — composition vs ordinal structure

PROVENANCE (Phase 7 intake, RESEARCH.md): rung 2 (line_as_record_per_hand)
returned B_only — Currier B's interior positional gain (+0.0513) beat all
20 per-hand nulls with margin +0.058. Two alternative explanations
survive rung 2, both identified in the external-findings intake:
  (i)  COMPOSITION: rung-2 nulls shuffle words corpus-wide within the
       hand, destroying the correlation between line content and
       position profile; B pools sections with different lexicons and
       line-length habits (A7 confound).
  (ii) SPACE MANAGEMENT (LAAFU prior art, voynich.ninja threads
       4869/5021): scribal justification — fitting words to line width —
       produces REAL ordinal structure (line-final words ~1 char
       shorter, confirmed there), and it is length-driven.
This rung separates compositional, length-ordinal, and glyph-ordinal
readings of the B signal. All thresholds fixed before first execution.

INSTRUMENT: identical features / bins / folio-holdout / ALPHA as rungs
1-2; all statistics are component-wise MEDIANS over R_SPLITS=10
independent holdout splits. New read-outs: per-feature decomposition
(len vs glyph-identity = first+last+gallows) and PER-FOLIO interior
gains (observational; for correlation against per-folio A/B "switch
intensity" covariates per Phase 7.1a — not adjudicated here).

NULL BATTERIES (N_NULLS=20 each, per hand):
  FOLIO-nulls: word order shuffled WITHIN EACH FOLIO (folio lexicon and
      line lengths preserved) — carries all cross-folio/sectional
      composition; kills explanation (i) if beaten.
  LINE-nulls: each line's own words shuffled IN PLACE (line content,
      length, folio all preserved) — the strictest compositional
      control; only intra-line ORDER is destroyed.
REFERENCE (not a gate): P-JUST — the P1 Latin word stream re-broken by
a greedy width-fitting algorithm (target width ~ N(JUST_WIDTH_MEAN,
JUST_WIDTH_SD) chars). Shows how much interior gain pure justification
produces in THIS instrument, and its len-vs-glyph split. Not a gate
because its width parameters are arbitrary; displayed beside every
verdict.

PRE-REGISTERED ADJUDICATION (Currier B only; A reported observationally
because only B passed rung 2):
  GATE (unchanged): P-REC total median >= 0.30, P1 total median <= 0.05.
  T1 composition: B total median beats ALL 20 FOLIO-null total medians
      AND margin over their median >= 0.05.
  T2 ordinal: same vs the 20 LINE-null total medians.
  T3 glyph-ordinal: B GLYPH-component median beats ALL 20 LINE-null
      glyph medians AND glyph margin >= 0.025 (floor halved: the glyph
      component spans 3 of 4 features; the empirical p ~ 1/21 is the
      primary bar, the floor is an effect-size minimum).
  OUTCOMES:
    gate_failed              — no interpretation.
    compositional_artifact   — T1 and T2 both fail: rung-2 signal was
                               composition; corpse for field structure.
    inconsistent_nulls       — T1 fails but T2 passes (logically the
                               folio bar is easier; this outcome means
                               the batteries disagree): no claim,
                               instrument investigation required.
    line_composition_not_order — T1 passes, T2 fails: word-to-line
                               assignment is non-random beyond folio
                               composition, but intra-line ORDER adds
                               nothing. Read against P-JUST (coherent
                               prose broken at widths shows line-topic
                               composition too). SUGGESTIVE (weak),
                               quarantined.
    length_ordering_only     — T1, T2 pass, T3 fails: intra-line order
                               is real but carried by word LENGTH —
                               consistent with scribal space management
                               (Stolfi), not field vocabulary. Valid
                               kill of the field reading; logged as a
                               corpse for "records", a confirmation for
                               LAAFU-as-layout.
    ordinal_glyph_structure  — all three pass: intra-line ordinal
                               structure in GLYPH IDENTITY beyond
                               length-based space management —
                               consistent with field-like vocabulary
                               ordering in Currier B. SUGGESTIVE,
                               quarantined, NOT a decode.
Vocabulary discipline: no outcome names a field, reads a record, or
uses the word "decoded".
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

SEED = 115
R_SPLITS = 10
N_NULLS = 20
EFFECT_FLOOR = 0.05       # bits/token, total component (rung-2 floor)
GLYPH_FLOOR = 0.025       # glyph component (3 of 4 features; see docstring)
GATE_PREC_MIN = 0.30
GATE_P1_MAX = 0.05
JUST_WIDTH_MEAN = 45.0    # P-JUST target line width, characters
JUST_WIDTH_SD = 5.0
MIN_LINE_WORDS = 5
HOLDOUT_FRAC = 0.2
PSEUDO_FOLIO_LINES = 24
ALPHA = 0.5
PREC_LINES = 4600

CONTROLS = DATA_DIR / 'controls'
GALLOWS = set('tkpf')
FEATURE_NAMES = ('len', 'first', 'last', 'gallows')
GLYPH_FEATURES = ('first', 'last', 'gallows')
INTERIOR = {'m1', 'm2', 'm3'}


# ────────────────────────────────────────────────────────────────────
# corpora (rung-1/2 local-copy loaders)
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
    """Rung-2's P-REC (marginally distinct first-letter field pools)."""
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


def build_pjust(rng):
    """P-JUST: the P1 word stream re-broken by greedy width fitting —
    the justification/space-management reference (docstring)."""
    words = [w for line in load_control('latin_plain') for w in line]
    lines, i = [], 0
    while i < len(words):
        target = max(20.0, rng.gauss(JUST_WIDTH_MEAN, JUST_WIDTH_SD))
        row, width = [], 0
        while i < len(words) and width + len(words[i]) + (1 if row else 0) <= target:
            width += len(words[i]) + (1 if row else 0)
            row.append(words[i])
            i += 1
        if not row:               # single word wider than target
            row = [words[i]]
            i += 1
        if len(row) >= MIN_LINE_WORDS:
            lines.append(row)
    return lines


def within_folio_shuffle(lines, folios, k):
    """Word order destroyed within each folio; folio lexicon and line
    lengths preserved (composition null)."""
    rng = random.Random(SEED * 1000 + k)
    by_folio = {}
    for i, f in enumerate(folios):
        by_folio.setdefault(f, []).append(i)
    out = [None] * len(lines)
    for f in sorted(by_folio):
        idx = by_folio[f]
        words = [w for i in idx for w in lines[i]]
        rng.shuffle(words)
        p = 0
        for i in idx:
            out[i] = words[p:p + len(lines[i])]
            p += len(lines[i])
    return out


def within_line_shuffle(lines, k):
    """Each line keeps its own words; only their order is destroyed
    (strictest compositional control)."""
    rng = random.Random(SEED * 1000 + 500 + k)
    out = []
    for line in lines:
        l = line[:]
        rng.shuffle(l)
        out.append(l)
    return out


# ────────────────────────────────────────────────────────────────────
# instrument (rung-2 copies + per-feature / per-folio read-outs)
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


def interior_eval(lines, folios, rng, collect_folios=False):
    """One split. Returns (per_feature_gain_sums, n_tokens, per_folio)
    where per_folio maps folio -> [total_gain_sum, n_tokens]."""
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

    sums = {f: 0.0 for f in FEATURE_NAMES}
    n = 0
    per_folio = {}
    for i in hold_idx:
        line = lines[i]
        L = len(line)
        for pos, w in enumerate(line):
            b = position_bin(pos, L)
            if b not in INTERIOR:
                continue
            fe = features(w)
            tok = 0.0
            for f in FEATURE_NAMES:
                bc = bin_c[f].get(b, Counter())
                g = logp(bc, fe[f], cats[f]) - logp(global_c[f], fe[f],
                                                    cats[f])
                sums[f] += g
                tok += g
            n += 1
            if collect_folios and folios is not None:
                pf = per_folio.setdefault(folios[i], [0.0, 0])
                pf[0] += tok
                pf[1] += 1
    return sums, n, per_folio


def stat_medians(lines, folios, collect_folios=False):
    """Component-wise medians over R_SPLITS splits: total, glyph
    (first+last+gallows), len — bits/token. Optionally per-folio means
    aggregated over the splits in which each folio was held out."""
    per_split = []
    folio_acc = {}
    for r in range(R_SPLITS):
        sums, n, pf = interior_eval(lines, folios,
                                    random.Random(SEED + 7 + r),
                                    collect_folios)
        if n == 0:
            per_split.append({'total': 0.0, 'glyph': 0.0, 'len': 0.0})
            continue
        per_split.append({
            'total': sum(sums.values()) / n,
            'glyph': sum(sums[f] for f in GLYPH_FEATURES) / n,
            'len': sums['len'] / n})
        for f, (s, k) in pf.items():
            acc = folio_acc.setdefault(f, [0.0, 0, 0])
            acc[0] += s
            acc[1] += k
            acc[2] += 1
    out = {c: round(statistics.median(ps[c] for ps in per_split), 4)
           for c in ('total', 'glyph', 'len')}
    out['splits_total'] = [round(ps['total'], 4) for ps in per_split]
    if collect_folios:
        out['per_folio'] = {f: {'mean_gain': round(s / k, 4) if k else 0.0,
                                'n_tokens': k, 'n_splits_heldout': m}
                            for f, (s, k, m) in sorted(folio_acc.items())}
    return out


def battery(real, null_meds, floor, component):
    """Empirical-p + effect-floor test of one component vs one battery."""
    vals = [nm[component] for nm in null_meds]
    margin = round(real[component] - statistics.median(vals), 4)
    return {'pass': real[component] > max(vals) and margin >= floor,
            'beats_all': real[component] > max(vals),
            'margin': margin, 'null_max': max(vals),
            'null_median': round(statistics.median(vals), 4)}


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LINE-AS-RECORD, RUNG 3 (S7) — composition vs ordinal structure')
    print('=' * 76)
    print(f'seed={SEED} splits={R_SPLITS} nulls/battery={N_NULLS} '
          f'floors: total={EFFECT_FLOOR} glyph={GLYPH_FLOOR}')
    print(f'P-JUST width ~ N({JUST_WIDTH_MEAN}, {JUST_WIDTH_SD}) chars '
          '(reference, not a gate)')

    vms = load_vms_by_currier()
    results = {}

    # gate + references
    for cname, lines, folios in [
            ('PREC_records', build_prec(random.Random(SEED)), None),
            ('P1_latin_plain', load_control('latin_plain'), None),
            ('PJUST_justified', build_pjust(random.Random(SEED + 1)), None)]:
        row = stat_medians(lines, folios)
        row['n_lines'] = len(lines)
        results[cname] = row
        print(f'  {cname:<16} total {row["total"]:+.4f}  glyph '
              f'{row["glyph"]:+.4f}  len {row["len"]:+.4f}  '
              f'({len(lines)} lines)')
    gate_ok = (results['PREC_records']['total'] >= GATE_PREC_MIN
               and results['P1_latin_plain']['total'] <= GATE_P1_MAX)
    print(f'  gate: {"PASS" if gate_ok else "FAIL"}')

    # hands: real statistic + two null batteries each
    for hand in ('A', 'B'):
        lines, folios = vms[hand]
        real = stat_medians(lines, folios, collect_folios=True)
        real['n_lines'] = len(lines)
        fol_nulls, lin_nulls = [], []
        for k in range(N_NULLS):
            fol_nulls.append(stat_medians(
                within_folio_shuffle(lines, folios, k), folios))
            lin_nulls.append(stat_medians(
                within_line_shuffle(lines, k), folios))
        row = {'real': real,
               'folio_nulls': {c: [nm[c] for nm in fol_nulls]
                               for c in ('total', 'glyph', 'len')},
               'line_nulls': {c: [nm[c] for nm in lin_nulls]
                              for c in ('total', 'glyph', 'len')},
               't1_composition': battery(real, fol_nulls, EFFECT_FLOOR,
                                         'total'),
               't2_ordinal': battery(real, lin_nulls, EFFECT_FLOOR,
                                     'total'),
               't3_glyph': battery(real, lin_nulls, GLYPH_FLOOR, 'glyph')}
        results[f'VMS_currier_{hand}'] = row
        print(f'  Currier {hand}: total {real["total"]:+.4f} (glyph '
              f'{real["glyph"]:+.4f}, len {real["len"]:+.4f})')
        for tname in ('t1_composition', 't2_ordinal', 't3_glyph'):
            t = row[tname]
            print(f'    {tname:<15} margin {t["margin"]:+.4f} (null max '
                  f'{t["null_max"]:+.4f}) -> '
                  f'{"PASS" if t["pass"] else "fail"}')

    # ── pre-registered adjudication (Currier B only) ────────────────
    print('\n  ADJUDICATION (pre-registered, Currier B; A observational):')
    b = results['VMS_currier_B']
    t1, t2, t3 = (b['t1_composition']['pass'], b['t2_ordinal']['pass'],
                  b['t3_glyph']['pass'])
    if not gate_ok:
        verdict = 'gate_failed'
        print('    INSTRUMENT GATE FAILED: no interpretation.')
    elif not t1 and not t2:
        verdict = 'compositional_artifact'
        print('    KILLED: B fails both null batteries — the rung-2 signal '
              'was composition, not order. Corpse for field structure.')
    elif not t1 and t2:
        verdict = 'inconsistent_nulls'
        print('    INCONSISTENT NULLS (folio bar failed, line bar passed): '
              'no claim; instrument investigation required.')
    elif t1 and not t2:
        verdict = 'line_composition_not_order'
        print('    LINE COMPOSITION, NOT ORDER: word-to-line assignment is '
              'non-random beyond folio composition, but intra-line order '
              'adds nothing. Read against the P-JUST reference. SUGGESTIVE '
              '(weak), quarantined.')
    elif not t3:
        verdict = 'length_ordering_only'
        print('    LENGTH ORDERING ONLY: intra-line order is real but '
              'carried by word length — consistent with scribal space '
              'management (LAAFU/Stolfi), not field vocabulary. The field '
              'reading is killed; the layout reading is confirmed.')
    else:
        verdict = 'ordinal_glyph_structure'
        print('    ORDINAL GLYPH STRUCTURE: B\'s intra-line order carries '
              'glyph-identity signal beyond length-based space management '
              '— consistent with field-like vocabulary ordering in Currier '
              'B. SUGGESTIVE, quarantined, NOT a decode.')

    with open(result_path('line_as_record_ordinal.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'r_splits': R_SPLITS,
                              'n_nulls': N_NULLS,
                              'effect_floor': EFFECT_FLOOR,
                              'glyph_floor': GLYPH_FLOOR,
                              'gate_prec_min': GATE_PREC_MIN,
                              'gate_p1_max': GATE_P1_MAX,
                              'just_width_mean': JUST_WIDTH_MEAN,
                              'just_width_sd': JUST_WIDTH_SD,
                              'min_line_words': MIN_LINE_WORDS,
                              'holdout_frac': HOLDOUT_FRAC,
                              'holdout_unit': 'folio',
                              'pseudo_folio_lines': PSEUDO_FOLIO_LINES,
                              'alpha': ALPHA},
                   'results': results, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_as_record_ordinal.json')


if __name__ == '__main__':
    main()
