#!/usr/bin/env python3
"""
Line-as-Record, rung 4 (portfolio S7) — characterization of the
Currier-B ordinal signal (N3d)

PROVENANCE: the B intra-line ordinal signal survived rung 2 (per-hand
nulls), rung 3 (composition/layout separation: glyph-dominated,
+0.0513 total with glyph +0.0524 / len +0.0018), and the S9 arc
(significant at p < 0.005 in five independent transliterations). Two
registered items remain: the PARAGRAPH-INITIAL threat (community prior
art: paragraph-opening lines obey different rules — Zandbergen, LAAFU
threads) and the CHARACTERIZATION question (which glyphs, which
interior positions carry the ordering).

STRUCTURE (registered before first execution):
  GATE (comparability): the rung-3 headline (full 4-feature 10-split
    median interior gain for B) is recomputed with rung-3's exact seeds
    and cross-checked against results/line_as_record_ordinal.json —
    abort on divergence.
  T-PARA (adjudicated): paragraph-initial lines (locus marker ,@ or ,*
    — 182 of B's lines) are EXCLUDED and the battery re-run on the
    remaining corpus: 10-split median total interior gain vs
    N_NULLS_PARA=200 within-line-shuffle nulls of the same reduced
    corpus. PASS iff the real median beats ALL nulls (empirical
    p = 1/201 < 0.005; significance-only criterion per the
    human-approved 2026-07-18 standard; effect sizes observational).
  DECOMPOSITION (descriptive ONLY — adjudicates nothing, claims
    nothing new; fixed methodology, no tunable selection after seeing
    results):
      D1 per-bin: interior gain split by m1/m2/m3 (median over splits).
      D2 per-feature: len / first / last / gallows separately.
      D3 per-category: for 'first' and 'last', the per-value
         contribution to that feature's gain (median over splits;
         contributions sum to the feature gain), for every value with
         full-corpus interior support >= MIN_SUPPORT; the top TOP_N by
         |contribution| are reported with their bin-occupancy skew
         (full-corpus obs/exp ratio per m-bin — deterministic).

PRE-REGISTERED OUTCOMES:
  paragraph_confound — T-PARA fails: the ordinal signal does not
      survive removing paragraph-initial lines; the rung-3 finding is
      DEMOTED (carried by the known-different paragraph-initial
      regime); the decomposition is dumped for the record but NOT
      interpreted.
  characterized      — T-PARA passes: the last registered structural
      threat is dismissed and the decomposition tables become the
      program's description of the signal. SUGGESTIVE (supporting
      detail for the quarantined finding), NOT a decode; no table row
      is a "translation" of anything.
Vocabulary discipline: D3 names GLYPH VALUES and their positional
skews; it never names meanings.
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

SEED = 115                # INHERITED from rung 3 — headline cross-checked
R_SPLITS = 10
N_NULLS_PARA = 200        # significance-only battery for T-PARA
MIN_SUPPORT = 200         # D3: full-corpus interior tokens per category
TOP_N = 8
MIN_LINE_WORDS = 5
HOLDOUT_FRAC = 0.2
ALPHA = 0.5

GALLOWS = set('tkpf')
FEATURE_NAMES = ('len', 'first', 'last', 'gallows')
INTERIOR = {'m1', 'm2', 'm3'}
RUNG3_JSON = 'line_as_record_ordinal.json'


# ── loader (rung-3 corpus semantics + paragraph-initial flag) ───────
def load_vms_b():
    """Currier-B lines exactly as rungs 2-3 defined them (file-level
    first $L; MIN_LINE_WORDS), plus a paragraph-initial flag from the
    IVTFF locus marker (',@' first-of-page / ',*' first-of-paragraph)."""
    lines, folios, para = [], [], []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        if not m or m.group(1) != 'B':
            continue
        for line in text.splitlines():
            line = line.strip()
            lm = re.match(r'<([^>]+)>', line)
            if line.startswith('#') or not lm:
                continue
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if len(words) < MIN_LINE_WORDS:
                continue
            lines.append(words)
            folios.append(fpath.stem)
            para.append(bool(re.search(r',[@*]', lm.group(1))))
    return lines, folios, para


# ── instrument (rung-3 local copies) ────────────────────────────────
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


def split_eval(lines, folios, rng):
    """One split. Returns (total_gain, per_bin, per_feature,
    per_category) where per_category maps ('first'|'last', value) ->
    contribution (normalized by ALL interior tokens)."""
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

    f_sums = {f: 0.0 for f in FEATURE_NAMES}
    b_sums = {b: [0.0, 0] for b in INTERIOR}
    c_sums = {}
    n = 0
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
                f_sums[f] += g
                tok += g
                if f in ('first', 'last'):
                    c_sums[(f, fe[f])] = c_sums.get((f, fe[f]), 0.0) + g
            b_sums[b][0] += tok
            b_sums[b][1] += 1
            n += 1
    if n == 0:
        return 0.0, {b: 0.0 for b in INTERIOR}, \
            {f: 0.0 for f in FEATURE_NAMES}, {}
    return (sum(f_sums.values()) / n,
            {b: (s / k if k else 0.0) for b, (s, k) in b_sums.items()},
            {f: s / n for f, s in f_sums.items()},
            {k: v / n for k, v in c_sums.items()})


def median_total(lines, folios):
    return round(statistics.median(
        split_eval(lines, folios, random.Random(SEED + 7 + r))[0]
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
    print('LINE-AS-RECORD, RUNG 4 (S7) — characterization (N3d)')
    print('=' * 76)
    print(f'seed={SEED} (inherited from rung 3) splits={R_SPLITS} '
          f'para-nulls={N_NULLS_PARA} (beat-all, p={1/(N_NULLS_PARA+1):.4f})'
          f' min_support={MIN_SUPPORT} top_n={TOP_N}')

    r3_path = result_path(RUNG3_JSON)
    if not r3_path.exists():
        raise RuntimeError(f'{RUNG3_JSON} missing — run '
                           'line_as_record_ordinal first')
    r3 = json.loads(r3_path.read_text(encoding='utf-8'))
    r3_total = r3['results']['VMS_currier_B']['real']['total']

    lines, folios, para = load_vms_b()
    n_para = sum(para)
    print(f'  B corpus: {len(lines)} lines, {n_para} paragraph-initial')

    # GATE: headline reproduction
    headline = median_total(lines, folios)
    if abs(headline - r3_total) > 1e-9:
        raise RuntimeError(f'headline {headline} != rung-3 recorded '
                           f'{r3_total} — seed/corpus divergence; abort')
    print(f'  gate: headline {headline:+.4f} == rung-3 record  VERIFIED')

    # T-PARA: paragraph-initial lines excluded, significance-only battery
    np_lines = [l for l, p in zip(lines, para) if not p]
    np_folios = [f for f, p in zip(folios, para) if not p]
    real_np = median_total(np_lines, np_folios)
    nulls = [median_total(within_line_shuffle(np_lines, k), np_folios)
             for k in range(N_NULLS_PARA)]
    n_ge = sum(1 for v in nulls if v >= real_np)
    t_para = {'n_lines_kept': len(np_lines), 'n_lines_excluded': n_para,
              'median_gain': real_np, 'null_max': max(nulls),
              'null_median': round(statistics.median(nulls), 4),
              'n_nulls_ge_real': n_ge,
              'p_empirical': round((1 + n_ge) / (N_NULLS_PARA + 1), 4),
              'pass': n_ge == 0}
    print(f'  T-PARA: para-initial excluded -> {len(np_lines)} lines; '
          f'real {real_np:+.4f}  null max {max(nulls):+.4f}  '
          f'nulls>=real {n_ge}  p={t_para["p_empirical"]:.4f} -> '
          f'{"PASS" if t_para["pass"] else "fail"}')

    # DECOMPOSITION (full corpus, descriptive)
    per_split = [split_eval(lines, folios, random.Random(SEED + 7 + r))
                 for r in range(R_SPLITS)]
    d_bin = {b: round(statistics.median(s[1][b] for s in per_split), 4)
             for b in sorted(INTERIOR)}
    d_feat = {f: round(statistics.median(s[2][f] for s in per_split), 4)
              for f in FEATURE_NAMES}
    print(f'  D1 per-bin: ' + '  '.join(f'{b} {v:+.4f}'
                                        for b, v in d_bin.items()))
    print(f'  D2 per-feature: ' + '  '.join(f'{f} {v:+.4f}'
                                            for f, v in d_feat.items()))

    # D3: per-category contributions + full-corpus bin-occupancy skew
    support = {}
    occ = {}
    bin_tot = Counter()
    for line in lines:
        L = len(line)
        for pos, w in enumerate(line):
            b = position_bin(pos, L)
            if b not in INTERIOR:
                continue
            fe = features(w)
            bin_tot[b] += 1
            for f in ('first', 'last'):
                key = (f, fe[f])
                support[key] = support.get(key, 0) + 1
                occ.setdefault(key, Counter())[b] += 1
    total_int = sum(bin_tot.values())
    d_cat = {'first': [], 'last': []}
    for f in ('first', 'last'):
        rows = []
        for (ff, v), sup in support.items():
            if ff != f or sup < MIN_SUPPORT:
                continue
            contrib = round(statistics.median(
                s[3].get((f, v), 0.0) for s in per_split), 5)
            skew = {b: round((occ[(f, v)].get(b, 0) / sup)
                             / (bin_tot[b] / total_int), 3)
                    for b in sorted(INTERIOR)}
            rows.append({'value': v, 'support': sup,
                         'contribution': contrib, 'bin_skew': skew})
        rows.sort(key=lambda r: -abs(r['contribution']))
        d_cat[f] = rows[:TOP_N]
        print(f'  D3 {f}: ' + '  '.join(
            f'{r["value"]}({r["contribution"]:+.4f})' for r in d_cat[f]))

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    if t_para['pass']:
        verdict = 'characterized'
        print('    CHARACTERIZED: the signal survives excluding '
              'paragraph-initial lines (p < 0.005) — the last registered '
              'structural threat is dismissed; the decomposition above is '
              'the program\'s description of the Currier-B ordinal '
              'signal. SUGGESTIVE (supporting detail for the quarantined '
              'finding); NOT a decode; no value is a translation.')
    else:
        verdict = 'paragraph_confound'
        print('    PARAGRAPH CONFOUND: the signal does not survive '
              'excluding paragraph-initial lines — the rung-3 finding is '
              'DEMOTED (carried by the known-different paragraph-initial '
              'regime). Decomposition dumped for the record, NOT '
              'interpreted.')

    with open(result_path('line_as_record_characterization.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'r_splits': R_SPLITS,
                              'n_nulls_para': N_NULLS_PARA,
                              'min_support': MIN_SUPPORT, 'top_n': TOP_N,
                              'min_line_words': MIN_LINE_WORDS,
                              'holdout_frac': HOLDOUT_FRAC,
                              'alpha': ALPHA, 'rung3_json': RUNG3_JSON},
                   'headline': {'total': headline,
                                'rung3_recorded': r3_total,
                                'verified': True},
                   't_para': t_para,
                   'decomposition': {'per_bin': d_bin,
                                     'per_feature': d_feat,
                                     'categories': d_cat},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_as_record_characterization.json')


if __name__ == '__main__':
    main()
