#!/usr/bin/env python3
"""
S9 follow-up — sensitivity-normalized effect floors for the
cross-transliteration S7-B ordinal battery (N2b)

REGISTERED QUESTION (carried in from N2's PARTIAL verdict): does the
fixed 0.05 bits/token effect floor mechanically penalize finer-grained
transliterations? N2 found the S7-B ordinal signal beats ALL nulls in
every usable reading (empirical-p 5/5) while GC (162-symbol alphabet)
missed the fixed floor by 0.0013 and CD (991 B-lines) by more.

FULL DISCLOSURE: this registration is written AFTER seeing N2's
outcome, so it is not blind. The protections against wishful scaling:
  (a) the normalization is MEASURED, not chosen — each reading's floor
      scales by its own instrument sensitivity ρ, obtained from a
      planted signal, with no free parameter that selects any
      particular reading's outcome;
  (b) it is SYMMETRIC — floors rise for more-sensitive readings just as
      they fall for less-sensitive ones; the previously-passing
      readings (ZL, FG, IT) are exposed to flipping to FAIL;
  (c) the anchor is ZL: rho_ZL = 1 by construction, so the original
      registered floor is unchanged for the canonical corpus;
  (d) battery values (median gains, null batteries) are NOT recomputed
      with fresh randomness: N2's exact seed streams are reused and the
      values are cross-checked against results/
      cross_transliteration_invariance.json — any mismatch aborts.

SENSITIVITY MEASUREMENT: for each reading R, the IMPLANT corpus sorts
every B-hand line's own words by the deterministic key (first char,
last char) in R's own codepoint order — a maximal intra-line ordinal
signal expressed in R's own alphabet, with line content, lengths, and
folio structure untouched. S_R = (median-over-splits interior gain of
the implant corpus) − (R's null median). rho_R = S_R / S_ZL.
ASSUMPTION (declared): the attenuation RATIO between readings is
approximately strength-independent (linear mixing), so the full-
strength implant estimates the ratio relevant at the ~0.05 scale.

SCALE-NORMALIZED FLOOR: floor_R = FLOOR_BASE × rho_R (FLOOR_BASE =
0.05, the original registration). Re-adjudication per reading: PASS =
beats ALL its nulls (unchanged from N2) AND margin >= floor_R.

PRE-REGISTERED OUTCOMES:
  reference_flip        — ZL fails its (unchanged) floor, or a reading
                          that passed N2 fails ONLY because
                          normalization RAISED its floor: instrument
                          inconsistency; no claim, investigate.
  floor_artifact_robust — every usable reading passes under normalized
                          floors: N2's PARTIAL was a floor-scaling
                          artifact; S9 verdict upgrades to ROBUST (same
                          caveat language as N2: removes one named
                          objection to the still-quarantined rung-3
                          finding; upgrades nothing else).
  partial_stands        — at least one usable reading still fails:
                          sensitivity does not (fully) explain the
                          misses; N2's PARTIAL stands on content
                          grounds. The rho table is still the product.
Vocabulary discipline: no outcome touches the manuscript's meaning;
this is an instrument-calibration experiment.
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

SEED = 116                # INHERITED from N2 — battery values must match
R_SPLITS = 10
N_NULLS = 20
FLOOR_BASE = 0.05
MIN_B_LINES = 500
MIN_LINE_WORDS = 5
HOLDOUT_FRAC = 0.2
ALPHA = 0.5

TRANSLIT_DIR = DATA_DIR / 'translit'
FILES = {'CD': 'CD2a-n.txt', 'GC': 'GC2a-n.txt',
         'FG': 'FG2a-n.txt', 'IT': 'IT2a-n.txt'}
FEATURE_NAMES = ('len', 'first', 'last')
INTERIOR = {'m1', 'm2', 'm3'}
N2_JSON = 'cross_transliteration_invariance.json'


# ── loaders (local copies, identical to N2's) ───────────────────────
def clean_generic(rest):
    rest = re.sub(r'@(\d+);',
                  lambda m: chr(0xE000 + int(m.group(1)) % 4000), rest)
    rest = re.sub(r'<![^>]*>', '.', rest)
    rest = re.sub(r'<[^>]*>', '.', rest)
    rest = re.sub(r'\[([^:\[\]]*)(?::[^\[\]]*)+\]', r'\1', rest)
    rest = rest.replace('!', '')
    words = []
    for w in re.split(r'[.\s,;]+', rest):
        w = w.strip()
        if not w:
            continue
        if any(c in w for c in '?%*{}'):
            continue
        words.append(w)
    return words


def load_ivtff_file(path):
    lang_by_folio = {}
    lines, folios = [], []
    for raw in path.read_text(encoding='utf-8',
                              errors='replace').splitlines():
        raw = raw.strip()
        if not raw or raw.startswith('#'):
            continue
        m = re.match(r'<(f[^.>]+)>\s*<!(.*)>\s*$', raw)
        if m:
            lm = re.search(r'\$L=([AB])', m.group(2))
            if lm:
                lang_by_folio[m.group(1)] = lm.group(1)
            continue
        m = re.match(r'<(f[^.>]+)\.[^>]*>\s*(.*)$', raw)
        if not m:
            continue
        words = clean_generic(m.group(2))
        if len(words) >= MIN_LINE_WORDS:
            lines.append(words)
            folios.append(m.group(1))
    return lines, folios, lang_by_folio


def load_zl():
    lines, folios, lang_by_folio = [], [], {}
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        if m:
            lang_by_folio[fpath.stem] = m.group(1)
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if len(words) >= MIN_LINE_WORDS:
                lines.append(words)
                folios.append(fpath.stem)
    return lines, folios, lang_by_folio


def hand_subset(lines, folios, lang_by_folio, hand):
    ls, fs = [], []
    for line, fol in zip(lines, folios):
        base = fol.split('.')[0]
        if lang_by_folio.get(base) == hand:
            ls.append(line)
            fs.append(base)
    return ls, fs


# ── instrument (identical to N2's part 2) ───────────────────────────
def features(w):
    return {'len': str(min(len(w), 7)) if len(w) < 7 else '7+',
            'first': w[0], 'last': w[-1]}


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


def implant(lines):
    """Maximal intra-line ordinal signal: each line's own words sorted
    by (first char, last char) in the reading's own codepoint order.
    Deterministic; content/lengths/folios untouched."""
    return [sorted(line, key=lambda w: (w[0], w[-1])) for line in lines]


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('S9 FOLLOW-UP (N2b) — sensitivity-normalized effect floors')
    print('=' * 76)
    print(f'seed={SEED} (inherited from N2; battery values cross-checked) '
          f'floor_base={FLOOR_BASE} anchor=ZL')

    n2_path = result_path(N2_JSON)
    if not n2_path.exists():
        raise RuntimeError(f'{N2_JSON} missing — run '
                           'cross_transliteration_invariance first')
    n2 = json.loads(n2_path.read_text(encoding='utf-8'))

    corpora = {'ZL': load_zl()}
    for tag, fname in FILES.items():
        corpora[tag] = load_ivtff_file(TRANSLIT_DIR / fname)

    rows = {}
    for tag, (lines, folios, langs) in corpora.items():
        b_lines, b_folios = hand_subset(lines, folios, langs, 'B')
        if len(b_lines) < MIN_B_LINES:
            rows[tag] = {'usable': False, 'n_B_lines': len(b_lines)}
            print(f'  {tag}: UNUSABLE ({len(b_lines)} B-lines)')
            continue
        real = median_gain(b_lines, b_folios)
        nulls = [median_gain(within_line_shuffle(b_lines, k), b_folios)
                 for k in range(N_NULLS)]
        null_med = round(statistics.median(nulls), 4)
        margin = round(real - null_med, 4)
        # cross-check against N2's recorded battery (same seed streams)
        n2b = n2['part2'][tag]['B']
        for mine, theirs, name in ((real, n2b['median_gain'], 'median_gain'),
                                   (null_med, n2b['null_median'],
                                    'null_median'),
                                   (margin, n2b['margin'], 'margin')):
            if abs(mine - theirs) > 1e-9:
                raise RuntimeError(f'{tag} {name}: recomputed {mine} != '
                                   f'N2 recorded {theirs} — seed streams '
                                   'diverged; aborting (registration '
                                   'requires identical battery values)')
        S = round(median_gain(implant(b_lines), b_folios) - null_med, 4)
        rows[tag] = {'usable': True, 'n_B_lines': len(b_lines),
                     'median_gain': real, 'null_median': null_med,
                     'null_max': max(nulls), 'margin': margin,
                     'implant_response': S}
        print(f'  {tag}: margin {margin:+.4f}  implant response {S:+.4f}  '
              f'[{len(b_lines)} B-lines]')

    S_zl = rows['ZL']['implant_response']
    for tag, row in rows.items():
        if not row['usable']:
            continue
        rho = round(row['implant_response'] / S_zl, 4)
        floor = round(FLOOR_BASE * rho, 4)
        row['rho'] = rho
        row['floor_normalized'] = floor
        row['beats_all'] = row['median_gain'] > row['null_max']
        row['pass_normalized'] = (row['beats_all']
                                  and row['margin'] >= floor)
        row['pass_n2_fixed'] = (row['beats_all']
                                and row['margin'] >= FLOOR_BASE)
        print(f'  {tag}: rho {rho:.4f} -> floor {floor:.4f}  margin '
              f'{row["margin"]:+.4f} -> '
              f'{"PASS" if row["pass_normalized"] else "fail"} '
              f'(was {"PASS" if row["pass_n2_fixed"] else "fail"} at '
              f'fixed {FLOOR_BASE})')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    usable = {t: r for t, r in rows.items() if r['usable']}
    zl_ok = usable['ZL']['pass_normalized']
    raised_flips = [t for t, r in usable.items()
                    if r['pass_n2_fixed'] and not r['pass_normalized']
                    and r['floor_normalized'] > FLOOR_BASE]
    fails = [t for t, r in usable.items() if not r['pass_normalized']]
    if not zl_ok or raised_flips:
        verdict = 'reference_flip'
        print(f'    REFERENCE FLIP (ZL ok={zl_ok}, raised-floor flips: '
              f'{raised_flips}): instrument inconsistency; no claim.')
    elif not fails:
        verdict = 'floor_artifact_robust'
        print('    FLOOR ARTIFACT CONFIRMED: every usable reading passes '
              'under sensitivity-normalized floors — N2 PARTIAL was a '
              'floor-scaling artifact; S9 upgrades to ROBUST (removes one '
              'named objection to the quarantined rung-3 finding; '
              'upgrades nothing else).')
    else:
        verdict = 'partial_stands'
        print(f'    PARTIAL STANDS: still failing under normalized floors: '
              f'{fails} — sensitivity does not (fully) explain the misses.')

    with open(result_path('transliteration_floor_calibration.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'r_splits': R_SPLITS,
                              'n_nulls': N_NULLS,
                              'floor_base': FLOOR_BASE,
                              'min_b_lines': MIN_B_LINES,
                              'min_line_words': MIN_LINE_WORDS,
                              'holdout_frac': HOLDOUT_FRAC,
                              'alpha': ALPHA, 'anchor': 'ZL',
                              'implant': 'sort_by_first_last',
                              'features': list(FEATURE_NAMES),
                              'n2_json': N2_JSON},
                   'rows': rows, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/transliteration_floor_calibration.json')


if __name__ == '__main__':
    main()
