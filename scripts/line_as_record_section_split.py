#!/usr/bin/env python3
"""
Line-as-Record, rung 5 (portfolio S7) — within-section replication of
the Currier-B ordinal signal (N3e)

REGISTERED QUESTION (human-directed, 2026-07-18): is B's ordinal signal
section-confounded within the bio/recipes split? Rung 3's within-folio
nulls controlled section COMPOSITION (each folio's lexicon stays put),
but the ordinal signal could still be section-scoped: present in one
section only, or — worst case — present only in the POOLED corpus
without replicating inside any single section. This rung tests
within-section replication directly.

DESIGN: the B corpus (identical loader/semantics to rungs 2-4; pooled
headline reproduced from rung 3's exact seeds as a gate, abort on
divergence) is split by the repo's folio-number taxonomy (declared):
  bio      folios f75-f84            (693 lines >= MIN_LINE_WORDS)
  recipes  folios f103-f116          (988 lines)
  other_B  all remaining B folios    (981 lines; mostly herbal-B/pharma)
Each subset with >= MIN_LINES lines runs the ordinal battery on ITS OWN
folios: 10-split folio-holdout medians (full 4-feature set), 200
within-line-shuffle nulls, PASS iff the real median beats ALL nulls
(empirical p = 1/201 < 0.005; significance-only per the human-approved
2026-07-18 standard; margins observational).
POWER DISCLOSURE: subsets are 27-39% of the pooled corpus; the beat-all
criterion is scale-adaptive (nulls share each subset's noise), but a
genuine weak signal can still fail in a small subset — outcomes are
worded accordingly and per-subset observational margins are reported.

PRE-REGISTERED OUTCOMES:
  section_general  — every usable subset passes: the signal replicates
      within each major section; the section-confound objection is
      dismissed.
  section_specific — some subsets pass, some fail: the finding's scope
      NARROWS to the passing sections (named); not a kill, a scoping
      result. SUGGESTIVE (scoped) — quarantined as before.
  pooling_artifact — NO subset passes while the pooled gate stands:
      the signal does not replicate inside any single section; the
      rung-3 finding is DEMOTED to 'unresolved — insufficient
      within-section evidence' (ambiguity disclosed: could be pooling
      artifact or per-subset power; either way no section-level support
      exists and promotion is blocked).
Vocabulary discipline: no outcome names fields or meanings; 'passes'
means only 'interior positional structure significant vs within-line
shuffles in that section'.
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
from common.core import FOLIO_DIR, ivtff_clean_words

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 115                # INHERITED from rung 3 — gate cross-checked
R_SPLITS = 10
N_NULLS = 200
MIN_LINES = 500
MIN_LINE_WORDS = 5
HOLDOUT_FRAC = 0.2
ALPHA = 0.5

GALLOWS = set('tkpf')
FEATURE_NAMES = ('len', 'first', 'last', 'gallows')
INTERIOR = {'m1', 'm2', 'm3'}
RUNG3_JSON = 'line_as_record_ordinal.json'


def section_of(stem):
    m = re.match(r'f(\d+)', stem)
    num = int(m.group(1)) if m else -1
    if 75 <= num <= 84:
        return 'bio'
    if 103 <= num <= 116:
        return 'recipes'
    return 'other_B'


def load_vms_b():
    lines, folios, sections = [], [], []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        if not m or m.group(1) != 'B':
            continue
        sec = section_of(fpath.stem)
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if len(words) < MIN_LINE_WORDS:
                continue
            lines.append(words)
            folios.append(fpath.stem)
            sections.append(sec)
    return lines, folios, sections


# ── instrument (rung-3 local copies, full 4-feature set) ────────────
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


def interior_gain(lines, folios, rng):
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
    return round(statistics.median(
        interior_gain(lines, folios, random.Random(SEED + 7 + r))
        for r in range(R_SPLITS)), 4)


def within_line_shuffle(lines, k):
    rng = random.Random(SEED * 1000 + 500 + k)
    out = []
    for line in lines:
        l = line[:]
        rng.shuffle(l)
        out.append(l)
    return out


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LINE-AS-RECORD, RUNG 5 (S7) — within-section replication (N3e)')
    print('=' * 76)
    print(f'seed={SEED} (inherited from rung 3) splits={R_SPLITS} '
          f'nulls={N_NULLS} criterion=beat-all (p={1/(N_NULLS+1):.4f}) '
          f'min_lines={MIN_LINES}')

    r3_path = result_path(RUNG3_JSON)
    if not r3_path.exists():
        raise RuntimeError(f'{RUNG3_JSON} missing — run '
                           'line_as_record_ordinal first')
    r3_total = json.loads(r3_path.read_text(encoding='utf-8'))[
        'results']['VMS_currier_B']['real']['total']

    lines, folios, sections = load_vms_b()
    headline = median_gain(lines, folios)
    if abs(headline - r3_total) > 1e-9:
        raise RuntimeError(f'pooled headline {headline} != rung-3 record '
                           f'{r3_total} — divergence; abort')
    print(f'  gate: pooled headline {headline:+.4f} == rung-3 record  '
          'VERIFIED')

    rows = {}
    for sec in ('bio', 'recipes', 'other_B'):
        s_lines = [l for l, s in zip(lines, sections) if s == sec]
        s_folios = [f for f, s in zip(folios, sections) if s == sec]
        n_folio = len(set(s_folios))
        if len(s_lines) < MIN_LINES:
            rows[sec] = {'usable': False, 'n_lines': len(s_lines)}
            print(f'  {sec}: UNUSABLE ({len(s_lines)} lines)')
            continue
        real = median_gain(s_lines, s_folios)
        nulls = [median_gain(within_line_shuffle(s_lines, k), s_folios)
                 for k in range(N_NULLS)]
        n_ge = sum(1 for v in nulls if v >= real)
        rows[sec] = {'usable': True, 'n_lines': len(s_lines),
                     'n_folios': n_folio, 'median_gain': real,
                     'null_max': max(nulls),
                     'null_median': round(statistics.median(nulls), 4),
                     'margin_observational': round(
                         real - statistics.median(nulls), 4),
                     'n_nulls_ge_real': n_ge,
                     'p_empirical': round((1 + n_ge) / (N_NULLS + 1), 4),
                     'pass': n_ge == 0}
        r = rows[sec]
        print(f'  {sec:<8} {len(s_lines):>4} lines / {n_folio:>2} folios: '
              f'real {real:+.4f}  null max {r["null_max"]:+.4f}  '
              f'nulls>=real {n_ge}  p={r["p_empirical"]:.4f} -> '
              f'{"PASS" if r["pass"] else "fail"}')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    usable = {s: r for s, r in rows.items() if r['usable']}
    passed = sorted(s for s, r in usable.items() if r['pass'])
    failed = sorted(s for s, r in usable.items() if not r['pass'])
    if usable and not failed:
        verdict = 'section_general'
        print(f'    SECTION-GENERAL: the ordinal signal replicates within '
              f'every usable section ({passed}) at p < 0.005 — the '
              'section-confound objection is dismissed.')
    elif passed:
        verdict = 'section_specific'
        print(f'    SECTION-SPECIFIC: passes in {passed}, fails in '
              f'{failed} — the finding\'s scope narrows to the passing '
              'sections. SUGGESTIVE (scoped), quarantined as before.')
    else:
        verdict = 'pooling_artifact'
        print('    POOLING ARTIFACT / UNRESOLVED: no section replicates '
              'the signal on its own — the rung-3 finding is demoted to '
              'unresolved (pooling artifact or per-subset power; either '
              'way promotion is blocked).')

    with open(result_path('line_as_record_section_split.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'r_splits': R_SPLITS,
                              'n_nulls': N_NULLS, 'min_lines': MIN_LINES,
                              'min_line_words': MIN_LINE_WORDS,
                              'holdout_frac': HOLDOUT_FRAC,
                              'alpha': ALPHA,
                              'criterion': 'beat_all_nulls',
                              'taxonomy': 'folio-number: bio f75-84, '
                                          'recipes f103-116, other_B rest',
                              'rung3_json': RUNG3_JSON},
                   'headline': {'total': headline,
                                'rung3_recorded': r3_total,
                                'verified': True},
                   'rows': rows, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_as_record_section_split.json')


if __name__ == '__main__':
    main()
