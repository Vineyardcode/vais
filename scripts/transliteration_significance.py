#!/usr/bin/env python3
"""
S9 follow-up 2 (N2c) — significance-only cross-reading battery for the
S7-B ordinal signal: 200 nulls, no effect floor

PROVENANCE AND AUTHORIZATION (disclosed in full): N2 returned PARTIAL —
every usable reading beat ALL 20 of its nulls (empirical p ~ 0.048,
5/5), but GC and CD missed the fixed 0.05 bits/token effect floor. N2b
refuted the floor-scaling explanation (GC/CD are MORE sensitive to
planted order, rho ~ 1.12) and its symmetric re-adjudication arm
self-invalidated (reference_flip: FG's raised floor flipped it). The
conclusion recorded there: all five margins sit within ±0.01 of a floor
calibrated in a different feature regime, so the floor cannot decide
the cross-reading question at these margins. THIS registration drops
the effect floor entirely and decides on significance alone, with a
battery large enough to be discriminating. Criteria change explicitly
approved by the human operator on 2026-07-18 ("register the larger
null battery and run it").

KNOWN-OUTCOME DISCLOSURE: N2's data already shows every reading beating
its 20 nulls, so a 20-null version of this test would be vacuous. The
battery here is 10x larger: the maximum of 200 null medians is almost
surely larger than the maximum of 20, so no reading's pass is
predetermined by anything already observed.

DESIGN (all inherited from N2 for exact comparability):
  Same corpora (ZL canonical + CD/GC/FG/IT from data/translit/), same
  B-hand subsets, same alphabet-agnostic features (len/first/last),
  same 10-split medians with the SAME split seeds (real median gains
  are cross-checked against results/cross_transliteration_invariance
  .json and the run ABORTS on any divergence), and the null seed
  stream is a STRICT SUPERSET of N2's: shuffles k=0..199 with N2's
  exact formula, so nulls 0..19 are byte-identical to N2's battery
  (max of the first 20 is cross-checked too).

PRE-REGISTERED CRITERION (per reading): PASS iff the real median gain
exceeds ALL N_NULLS=200 null medians — empirical p = 1/201 < 0.005.
No effect floor. Margins over the null median are reported as
observational effect sizes only.

PRE-REGISTERED OUTCOMES:
  reference_not_significant — ZL fails: the reduced-feature signal does
      not survive a tight significance bar even in the canonical
      reading; no claim about alternates; the cross-reading support
      argument for the rung-3 finding collapses (the rung-3 finding
      itself, full-feature ZL, is untouched by this instrument).
  robust_significance   — ZL passes and EVERY usable alternative
      passes: the S7-B ordinal signal is significant at p < 0.005 in
      five independent readings; the cross-reading objection to the
      quarantined rung-3 finding is resolved in favor of robustness.
      (Still SUGGESTIVE, still quarantined, still not a decode.)
  partial_significance  — ZL passes, some alternatives fail (named):
      the PARTIAL verdict stands at significance level.
  artifact_suspect_significance — ZL passes, ALL usable alternatives
      fail: the finding is demoted to artifact-suspect (a property of
      the ZL reading until shown otherwise).
Vocabulary discipline: 'robust_significance' removes one named
objection to a quarantined SUGGESTIVE finding; it names no field,
reads no record, upgrades nothing else.
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

SEED = 116                # INHERITED from N2 — comparability by construction
R_SPLITS = 10
N_NULLS = 200             # 10x N2; empirical p = 1/201 < 0.005
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


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('S9 FOLLOW-UP 2 (N2c) — significance-only battery, 200 nulls')
    print('=' * 76)
    print(f'seed={SEED} (inherited from N2; superset null stream) '
          f'splits={R_SPLITS} nulls={N_NULLS} criterion=beat-all '
          f'(p={1 / (N_NULLS + 1):.4f}); NO effect floor '
          '(human-approved criteria change 2026-07-18)')

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
        # cross-checks: real median and the first-20 null max vs N2
        n2b = n2['part2'][tag]['B']
        if abs(real - n2b['median_gain']) > 1e-9:
            raise RuntimeError(f'{tag} median_gain {real} != N2 '
                               f'{n2b["median_gain"]} — seed divergence')
        if abs(max(nulls[:20]) - n2b['null_max']) > 1e-9:
            raise RuntimeError(f'{tag} first-20 null max diverges from N2')
        n_ge = sum(1 for v in nulls if v >= real)
        p_emp = (1 + n_ge) / (N_NULLS + 1)
        rows[tag] = {'usable': True, 'n_B_lines': len(b_lines),
                     'median_gain': real,
                     'null_max': max(nulls),
                     'null_median': round(statistics.median(nulls), 4),
                     'margin_observational': round(
                         real - statistics.median(nulls), 4),
                     'n_nulls_ge_real': n_ge,
                     'p_empirical': round(p_emp, 4),
                     'pass': n_ge == 0}
        r = rows[tag]
        print(f'  {tag}: real {real:+.4f}  null max {r["null_max"]:+.4f}  '
              f'nulls>=real {n_ge}  p={r["p_empirical"]:.4f} -> '
              f'{"PASS" if r["pass"] else "fail"}   '
              f'[{len(b_lines)} B-lines]')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    usable = {t: r for t, r in rows.items() if r['usable']}
    zl_ok = usable['ZL']['pass']
    alts = {t: r for t, r in usable.items() if t != 'ZL'}
    alt_pass = sorted(t for t, r in alts.items() if r['pass'])
    alt_fail = sorted(t for t, r in alts.items() if not r['pass'])
    if not zl_ok:
        verdict = 'reference_not_significant'
        print('    REFERENCE NOT SIGNIFICANT: ZL fails at p < 0.005 with '
              'reduced features — the cross-reading support argument '
              'collapses; no claim about alternates.')
    elif alts and not alt_fail:
        verdict = 'robust_significance'
        print(f'    ROBUST AT SIGNIFICANCE: all usable readings pass at '
              f'p < 0.005 ({["ZL"] + alt_pass}). The cross-reading '
              'objection to the quarantined rung-3 finding is resolved '
              'in favor of robustness. Still SUGGESTIVE, still '
              'quarantined, not a decode.')
    elif alt_pass:
        verdict = 'partial_significance'
        print(f'    PARTIAL AT SIGNIFICANCE: pass {alt_pass}, fail '
              f'{alt_fail} — the PARTIAL verdict stands at significance '
              'level.')
    else:
        verdict = 'artifact_suspect_significance'
        print(f'    ARTIFACT-SUSPECT: ZL passes but all alternatives fail '
              f'({alt_fail}) at p < 0.005 — demoted to artifact-suspect.')

    with open(result_path('transliteration_significance.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'r_splits': R_SPLITS,
                              'n_nulls': N_NULLS,
                              'min_b_lines': MIN_B_LINES,
                              'min_line_words': MIN_LINE_WORDS,
                              'holdout_frac': HOLDOUT_FRAC,
                              'alpha': ALPHA,
                              'criterion': 'beat_all_nulls',
                              'features': list(FEATURE_NAMES),
                              'n2_json': N2_JSON},
                   'rows': rows, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/transliteration_significance.json')


if __name__ == '__main__':
    main()
