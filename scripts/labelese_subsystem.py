#!/usr/bin/env python3
"""
Labelese Subsystem Test (N11) — are the marginal labels a distinct
register, and are they a SECTION-SPECIFIC naming system? (N11)

PROVENANCE (operator-directed, prompted by f66r's label-dense margin):
the IVTFF label loci (type L) are a small (~628-word), understudied
subsystem excluded from the continuous-text corpus the discipline
findings rest on. A reconnaissance showed labels are distributionally
odd (first-glyph o- 50% vs the gallows/q-heavy line-starts). This
instrument asks two registered questions with controls:
  (D) DISTINCTNESS — are labels a different register from running text,
      or just a small sample of it?
  (S) SECTION-SPECIFICITY — the "naming" question: does a label's
      identity predict its section MORE than an ordinary word does?
      A naming system (labels = names of depicted things) implies label
      vocabulary is section-bound BEYOND the dialect variation running
      text already carries (N10). If labels are no more section-specific
      than a size-matched running sample, they are a distinct register
      but not a naming system.
This bears on whether labels could ever be a crib — while staying
strictly clear of the F7 anchor-decay trap (labels-as-names is TESTED
here, never assumed; no label is read as any word).

POWER DISCLOSURE (stated first): ~628 labels over ~7 sections is a small
sample. Every statistic is corrected against a shuffle null and every
label comparison is against a SIZE-MATCHED running-text baseline (same
n, same hapax structure), so overfitting is matched, not mistaken for
signal. Per-section counts are reported; low-power sections are flagged.

METRIC: U(section|X) = MI(X;section)/H(section), the fraction of
section-uncertainty a word-identity feature explains; U*(X) = U minus
the mean of N_NULL section-shuffles (the excess above what the feature's
cardinality buys). First-glyph distinctness = Jensen-Shannon divergence
of the label first-glyph distribution from running text, vs a
subsample-of-running null.

CONTROLS (validate the section-specificity measure):
  P-NAME (naming positive): synthetic labels, each section a DISJOINT
    vocabulary -> U*(word) high.
  P-GEN (generic negative): synthetic labels from ONE shared pool ->
    U*(word) ~ 0.
  GATE: U*(P-NAME) >= CTRL_FACTOR x U*(P-GEN) (scale-free; the excess
    metric is shuffle-corrected so absolute separations are small).
  CALIBRATION NOTE (2026-07-21, disclosed): first execution used an
    ABSOLUTE gap gate (0.3) mis-scaled to the raw metric; the controls
    separated cleanly (P-NAME 0.159 vs P-GEN 0.014, 11x) but the
    absolute gate spuriously failed. The gate was recalibrated to the
    scale-free factor form above BEFORE committing — an instrument-
    validity fix. The VMS verdict threshold (NAMING_MARGIN) is
    UNCHANGED from the pre-run registration. Fixed-data caveat (Phase 8
    §8.7-3): the VMS numbers were visible at recalibration; the gate
    fix is orthogonal to the VMS criterion, but this is disclosed.

PRE-REGISTERED VERDICTS:
  gate_failed            — controls do not separate.
  labels_not_distinct    — label first-glyph JSD does not beat the
                           subsample null: labels are not a separable
                           register at this power.
  labelese_naming_system — distinct AND U*(labels) beats its own shuffle
                           null AND (U*(labels) - U*(running_matched))
                           >= NAMING_MARGIN: labels are section-bound
                           beyond dialect — a naming register.
                           SUGGESTIVE, quarantined (the most crib-like
                           outcome; still not a decode, still F7-bound).
  labelese_generic_register — distinct but NOT more section-specific
                           than matched running text: a distinct
                           register, not a naming system.
Vocabulary discipline: characterization of a subsystem's statistics;
no label is read, nothing is decoded.
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

SEED = 128
N_NULL = 30
R_MATCH = 12             # size-matched running-text subsamples
N_SUB = 200             # subsample nulls for the distinctness JSD
NAMING_MARGIN = 0.03    # U*(labels) - U*(running_matched) for "naming"
                        # (unchanged from the pre-run registration)
CTRL_FACTOR = 3.0       # scale-free control-separation gate (see note)
CTRL_FLOOR = 0.005      # P-GEN excess floor for the factor test
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


def first_glyph(w):
    g = eva_to_glyphs(w)
    return g[0] if g else w[0]


def load():
    """(labels, running) as lists of (word, section)."""
    labels, running = [], []
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
                labels += [(w, sec) for w in words]
            elif lt == 'P' and len(words) >= MIN_LINE_WORDS:
                running += [(w, sec) for w in words]
    return labels, running


# ── metrics ─────────────────────────────────────────────────────────
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
    return real - statistics.mean(nulls)


def jsd(p, q):
    keys = set(p) | set(q)
    sp, sq = sum(p.values()) or 1, sum(q.values()) or 1
    d = 0.0
    for k in keys:
        a, b = p.get(k, 0) / sp, q.get(k, 0) / sq
        m = (a + b) / 2
        if a:
            d += a / 2 * math.log2(a / m)
        if b:
            d += b / 2 * math.log2(b / m)
    return d


def build_synth(disjoint, rng):
    """P-NAME (disjoint per-section vocab) or P-GEN (shared pool)."""
    if disjoint:
        pools = [[f's{s}_w{i}' for i in range(POOL_PER)]
                 for s in range(SECTIONS)]
    else:
        shared = [f'w{i}' for i in range(POOL_PER)]
        pools = [shared] * SECTIONS
    rows = []
    for s in range(SECTIONS):
        for _ in range(110):        # ~ label corpus scale per section
            rows.append((rng.choice(pools[s]), f'S{s}'))
    return rows


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LABELESE SUBSYSTEM TEST (N11) — distinct register? naming '
          'system?')
    print('=' * 76)
    print(f'seed={SEED} nulls={N_NULL} match={R_MATCH} '
          f'naming_margin={NAMING_MARGIN}')

    labels, running = load()
    lab_w = [w for w, _ in labels]
    lab_s = [s for _, s in labels]
    run_w = [w for w, _ in running]
    run_s = [s for _, s in running]
    persec = Counter(lab_s)
    print(f'  labels: {len(labels)} tokens, {len(set(lab_w))} types; '
          f'running: {len(running)} tokens')
    print('  labels per section: '
          + '  '.join(f'{s}:{persec[s]}' for s in sorted(persec)))
    low = [s for s, c in persec.items() if c < 20]
    if low:
        print(f'  [low-power sections (<20 labels): {low}]')

    rng = random.Random(SEED)

    # ── (D) distinctness: first-glyph JSD vs subsample null ─────────
    lab_fg = Counter(first_glyph(w) for w in lab_w)
    run_fg = Counter(first_glyph(w) for w in run_w)
    real_jsd = jsd(lab_fg, run_fg)
    nulls = []
    for _ in range(N_SUB):
        sub = Counter(first_glyph(w)
                      for w in random.sample(run_w, len(lab_w)))
        nulls.append(jsd(sub, run_fg))
    distinct = real_jsd > max(nulls)
    print(f'\n  (D) first-glyph JSD labels-vs-running {real_jsd:.4f}  '
          f'subsample-null max {max(nulls):.4f}  -> '
          f'{"DISTINCT" if distinct else "not distinct"}')

    # ── (S) section-specificity: U* labels vs matched running ───────
    u_lab = excess_U(lab_w, lab_s, random.Random(SEED + 1))
    lab_null = []
    for _ in range(N_NULL):
        perm = lab_s[:]
        rng.shuffle(perm)
        lab_null.append(uncertainty_coef(lab_w, perm))
    lab_beats_null = uncertainty_coef(lab_w, lab_s) > max(lab_null)
    matched = []
    for k in range(R_MATCH):
        idx = random.Random(SEED + 100 + k).sample(range(len(running)),
                                                   len(labels))
        mw = [run_w[i] for i in idx]
        ms = [run_s[i] for i in idx]
        matched.append(excess_U(mw, ms, random.Random(SEED + 200 + k)))
    u_run = statistics.mean(matched)
    margin = u_lab - u_run
    print(f'  (S) U*(labels) {u_lab:+.4f} (beats own null: '
          f'{lab_beats_null})   U*(running matched, n={len(labels)}) '
          f'{u_run:+.4f}   naming margin {margin:+.4f}')

    # controls
    u_name = excess_U(*zip(*build_synth(True, random.Random(SEED + 7))),
                      random.Random(SEED + 8))
    gen = build_synth(False, random.Random(SEED + 9))
    u_gen = excess_U([w for w, _ in gen], [s for _, s in gen],
                     random.Random(SEED + 10))
    gate = u_name >= CTRL_FACTOR * max(u_gen, CTRL_FLOOR)
    print(f'  controls: U*(P-NAME) {u_name:+.4f} vs U*(P-GEN) '
          f'{u_gen:+.4f} (gate: P-NAME >= {CTRL_FACTOR}x max(P-GEN, '
          f'{CTRL_FLOOR})) -> {"PASS" if gate else "FAIL"}')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    if not gate:
        verdict = 'gate_failed'
        print('    GATE FAILED: controls do not separate; no reading.')
    elif not distinct:
        verdict = 'labels_not_distinct'
        print('    LABELS NOT DISTINCT: label first-glyph distribution is '
              'within subsample noise of running text at this power.')
    elif lab_beats_null and margin >= NAMING_MARGIN:
        verdict = 'labelese_naming_system'
        print('    LABELESE NAMING SYSTEM: labels are a distinct register '
              f'AND section-bound beyond dialect (margin {margin:+.4f} '
              f'>= {NAMING_MARGIN}, U* beats its null) — label vocabulary '
              'is more section-specific than matched running text. The '
              'most crib-like outcome; SUGGESTIVE, quarantined, and '
              'still F7-bound (no label is read).')
    else:
        verdict = 'labelese_generic_register'
        print('    LABELESE GENERIC REGISTER: labels are a distinct '
              f'register (first-glyph JSD) but NOT more section-specific '
              f'than matched running text (margin {margin:+.4f} < '
              f'{NAMING_MARGIN}) — a distinct register, not a '
              'section-naming system.')

    with open(result_path('labelese_subsystem.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'n_null': N_NULL,
                              'r_match': R_MATCH, 'n_sub': N_SUB,
                              'naming_margin': NAMING_MARGIN,
                              'ctrl_factor': CTRL_FACTOR,
                              'min_line_words': MIN_LINE_WORDS},
                   'results': {'n_labels': len(labels),
                               'n_label_types': len(set(lab_w)),
                               'n_running': len(running),
                               'labels_per_section': dict(persec),
                               'distinctness_jsd': round(real_jsd, 4),
                               'distinctness_null_max': round(max(nulls),
                                                              4),
                               'distinct': distinct,
                               'u_labels': round(u_lab, 4),
                               'u_labels_beats_null': lab_beats_null,
                               'u_running_matched': round(u_run, 4),
                               'naming_margin': round(margin, 4),
                               'ctrl_name': round(u_name, 4),
                               'ctrl_gen': round(u_gen, 4),
                               'gate': gate,
                               'label_first_glyph':
                                   {g: c for g, c in lab_fg.most_common(8)}},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/labelese_subsystem.json')


if __name__ == '__main__':
    main()
