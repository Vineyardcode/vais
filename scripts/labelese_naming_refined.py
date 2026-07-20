#!/usr/bin/env python3
"""
Labelese Naming, Refined (N11b) — does the section-naming signal survive
splitting off fragment-labels AND matching the section marginal?

PROVENANCE: N11 found the marginal labels are a distinct register and
section-bound beyond dialect (naming margin +0.043), verdict
labelese_naming_system — SUGGESTIVE, with two caveats flagged in its own
entry: (1) it pooled real word-shaped labels with single-glyph marker
tokens; (2) the naming margin was measured against a running baseline
whose SECTION MARGINAL differed from the labels', so the pharma-label
concentration could inflate it. A reconnaissance confirmed both: the
word-shaped labels are o+gallows+suffix forms concentrated in the
illustrated sections (pharma/zodiac/bio), while the "labels" also
included a tail of stray single glyphs (y, s, d, f). This rung re-tests
the naming claim with both defects removed.

TWO REFINEMENTS (declared before running):
  (1) WORD-SHAPED only: labels parsed to >= MIN_GLYPHS EVA glyphs;
      shorter fragment/marker tokens are analysed separately
      (observational).
  (2) SECTION-MARGINAL-MATCHED baseline: the running-text comparison
      sample is drawn to have the IDENTICAL per-section counts as the
      word-shaped labels, so U*(word;section) reflects word-identity
      specificity at fixed section composition — the concentration
      confound is removed by construction, not just noted.
Everything else (the U* metric, shuffle nulls, the naming/generic
controls and their scale-free gate) is inherited unchanged from N11;
NAMING_MARGIN is unchanged. Fixed-data caveat (Phase 8 §8.7-3): the N11
result and the reconnaissance are already seen; these refinements are
methodological improvements to the SAME criterion, disclosed as such.

PRE-REGISTERED VERDICTS (on the word-shaped labels):
  gate_failed        — naming/generic controls do not separate.
  naming_survives    — U*(word-shaped labels) beats its shuffle null
                       AND the margin over the section-marginal-matched
                       running baseline >= NAMING_MARGIN: the naming
                       signal is real word-identity specificity, NOT the
                       pharma concentration. SUGGESTIVE, quarantined.
  naming_weakened    — 0 < margin < NAMING_MARGIN: real but partly a
                       concentration effect; downgraded.
  naming_was_concentration — margin <= 0 with marginals matched: N11's
                       signal was the section concentration; the naming
                       reading is withdrawn (corpse logged).
Vocabulary discipline: no label is read; "naming" is distributional.
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
from common.core import FOLIO_DIR, ivtff_clean_words, eva_to_glyphs

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 129
N_NULL = 30
R_MATCH = 12
MIN_GLYPHS = 3          # word-shaped label cut (EVA glyphs)
NAMING_MARGIN = 0.03    # inherited from N11, unchanged
CTRL_FACTOR = 3.0
CTRL_FLOOR = 0.005
SECTIONS = 6
POOL_PER = 200
MIN_LINE_WORDS = 5


def vms_section(stem):
    m = re.match(r'f(\d+)', stem)
    if not m:
        return 'unknown'
    n = int(m.group(1))
    if n <= 58 or 65 <= n <= 66:
        return 'herbalA'
    if 67 <= n <= 73:
        return 'zodiac'
    if 75 <= n <= 84:
        return 'bio'
    if 85 <= n <= 86:
        return 'cosmo'
    if 87 <= n <= 102:
        return 'pharma' if n in (88, 89, 99, 100, 101, 102) else 'herbalB'
    if 103 <= n <= 116:
        return 'text'
    return 'unknown'


def locus_type(lid):
    m = re.search(r',[@+*=]?([A-Za-z])', lid)
    return m.group(1).upper() if m else '?'


def load():
    """word-shaped labels, fragment labels, running — each (word, sec)."""
    wlab, frag, running = [], [], []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        sec = vms_section(fpath.stem)
        if sec == 'unknown':
            continue
        for line in fpath.read_text(encoding='utf-8',
                                    errors='replace').splitlines():
            line = line.strip()
            m = re.match(r'<([^>]+)>', line)
            if line.startswith('#') or not m:
                continue
            lt = locus_type(m.group(1))
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if lt == 'L':
                for w in words:
                    (wlab if len(eva_to_glyphs(w)) >= MIN_GLYPHS
                     else frag).append((w, sec))
            elif lt == 'P' and len(words) >= MIN_LINE_WORDS:
                running += [(w, sec) for w in words]
    return wlab, frag, running


def entropy(counter):
    tot = sum(counter.values())
    return -sum(c / tot * math.log2(c / tot)
                for c in counter.values() if c) if tot else 0.0


def uncertainty_coef(xs, secs):
    Hsec = entropy(Counter(secs))
    if Hsec == 0:
        return 0.0
    N = len(xs)
    by_x = defaultdict(Counter)
    for x, s in zip(xs, secs):
        by_x[x][s] += 1
    Hcond = sum((sum(cx.values()) / N) * entropy(cx)
                for cx in by_x.values())
    return (Hsec - Hcond) / Hsec


def excess_U(xs, secs, rng):
    xs, secs = list(xs), list(secs)
    real = uncertainty_coef(xs, secs)
    nulls = []
    for _ in range(N_NULL):
        perm = list(secs)
        rng.shuffle(perm)
        nulls.append(uncertainty_coef(xs, perm))
    return real - statistics.mean(nulls), real, max(nulls)


def build_synth(disjoint, rng):
    if disjoint:
        pools = [[f's{s}_w{i}' for i in range(POOL_PER)]
                 for s in range(SECTIONS)]
    else:
        shared = [f'w{i}' for i in range(POOL_PER)]
        pools = [shared] * SECTIONS
    rows = []
    for s in range(SECTIONS):
        for _ in range(110):
            rows.append((rng.choice(pools[s]), f'S{s}'))
    return rows


def marginal_matched(running, target_persec, rng):
    """Draw running words to match target per-section counts exactly."""
    by_sec = defaultdict(list)
    for w, s in running:
        by_sec[s].append(w)
    out = []
    for s, n in target_persec.items():
        pool = by_sec.get(s, [])
        if not pool:
            continue
        take = rng.sample(pool, n) if n <= len(pool) else \
            [rng.choice(pool) for _ in range(n)]
        out += [(w, s) for w in take]
    return out


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LABELESE NAMING, REFINED (N11b) — word-shaped + marginal-'
          'matched')
    print('=' * 76)
    print(f'seed={SEED} min_glyphs={MIN_GLYPHS} nulls={N_NULL} '
          f'match={R_MATCH} naming_margin={NAMING_MARGIN}')

    wlab, frag, running = load()
    wl_w = [w for w, _ in wlab]
    wl_s = [s for _, s in wlab]
    persec = Counter(wl_s)
    print(f'  word-shaped labels: {len(wlab)} tokens ({len(set(wl_w))} '
          f'types); fragment labels: {len(frag)}; running: {len(running)}')
    print('  word-shaped labels per section: '
          + '  '.join(f'{s}:{persec[s]}' for s in sorted(persec)))

    # controls + gate (inherited)
    un, _, _ = excess_U(*zip(*build_synth(True, random.Random(SEED + 7))),
                        rng=random.Random(SEED + 8))
    gen = build_synth(False, random.Random(SEED + 9))
    ug, _, _ = excess_U([w for w, _ in gen], [s for _, s in gen],
                        random.Random(SEED + 10))
    gate = un >= CTRL_FACTOR * max(ug, CTRL_FLOOR)
    print(f'  controls: P-NAME {un:+.4f} vs P-GEN {ug:+.4f} -> '
          f'{"PASS" if gate else "FAIL"}')

    # word-shaped labels U*
    u_lab, raw_lab, null_lab = excess_U(wl_w, wl_s, random.Random(SEED + 1))
    beats = raw_lab > null_lab

    # section-marginal-matched running baseline
    matched = []
    for k in range(R_MATCH):
        mm = marginal_matched(running, dict(persec),
                              random.Random(SEED + 300 + k))
        u, _, _ = excess_U([w for w, _ in mm], [s for _, s in mm],
                           random.Random(SEED + 400 + k))
        matched.append(u)
    u_run = statistics.mean(matched)
    margin = u_lab - u_run
    print(f'  word-shaped labels U* {u_lab:+.4f} (beats null: {beats})  '
          f'marginal-matched running U* {u_run:+.4f}  margin '
          f'{margin:+.4f}')

    # fragment labels (observational)
    if len(frag) >= 20:
        fw = [w for w, _ in frag]
        fs = [s for _, s in frag]
        u_frag, raw_f, null_f = excess_U(fw, fs, random.Random(SEED + 2))
        print(f'  [fragment labels U* {u_frag:+.4f} (beats null: '
              f'{raw_f > null_f}) — observational]')
    else:
        u_frag = None

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    if not gate:
        verdict = 'gate_failed'
        print('    GATE FAILED: controls do not separate.')
    elif beats and margin >= NAMING_MARGIN:
        verdict = 'naming_survives'
        print(f'    NAMING SURVIVES: with fragments removed and section '
              f'marginals matched, word-shaped labels remain section-'
              f'bound beyond running text (margin {margin:+.4f} >= '
              f'{NAMING_MARGIN}) — the naming signal is real word-'
              'identity specificity, not the pharma concentration. '
              'SUGGESTIVE, quarantined; still F7-bound.')
    elif margin > 0:
        verdict = 'naming_weakened'
        print(f'    NAMING WEAKENED: margin {margin:+.4f} positive but '
              f'below {NAMING_MARGIN} once marginals are matched — the '
              'N11 signal was partly the section concentration; '
              'downgraded.')
    else:
        verdict = 'naming_was_concentration'
        print(f'    NAMING WAS CONCENTRATION: margin {margin:+.4f} <= 0 '
              'with section marginals matched — N11\'s naming signal was '
              'the pharma-label concentration, not word-identity '
              'specificity. The naming reading is withdrawn. Corpse '
              'logged.')

    with open(result_path('labelese_naming_refined.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'min_glyphs': MIN_GLYPHS,
                              'n_null': N_NULL, 'r_match': R_MATCH,
                              'naming_margin': NAMING_MARGIN,
                              'ctrl_factor': CTRL_FACTOR},
                   'results': {'n_word_labels': len(wlab),
                               'n_word_types': len(set(wl_w)),
                               'n_fragment_labels': len(frag),
                               'labels_per_section': dict(persec),
                               'u_word_labels': round(u_lab, 4),
                               'u_word_labels_beats_null': beats,
                               'u_marginal_matched_running':
                                   round(u_run, 4),
                               'naming_margin': round(margin, 4),
                               'u_fragment_labels':
                                   round(u_frag, 4) if u_frag is not None
                                   else None,
                               'ctrl_name': round(un, 4),
                               'ctrl_gen': round(ug, 4), 'gate': gate},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/labelese_naming_refined.json')


if __name__ == '__main__':
    main()
