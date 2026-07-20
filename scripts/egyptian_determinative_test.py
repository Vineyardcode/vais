#!/usr/bin/env python3
"""
Egyptian Determinative Test (N10) — are the gallows semantic
determinatives, or just dialectal vocabulary?

PROVENANCE: the pre-charter egyptian_connection test asserts (5/5
CONFIRMED, no controls) that the gallows t/k/f/p are semantic
determinatives mapping to content domains. That test has no ledger
standing (its status errata). This instrument gives the CORE claim a
controlled trial with a pre-registered kill, so it can be supported or
killed honestly instead of self-confirmed.

THE TESTABLE CLAIM AND ITS DISCRIMINATOR: a determinative (Egyptian
sense) is a semantic classifier SEPARABLE from the phonetic root. Its
signature is that it predicts a word's SECTION (its meaning-domain)
MORE than the root does — because the root is phonetic and shared
across topics, while the determinative carries the semantic category.
The mundane alternative is DIALECT: whole vocabularies differ by
section, so the ROOT carries the section information and the gallows
merely ride along (the well-known fact that gallows frequencies vary
by section is exactly this, and is NOT a determinative system).
  Determinative -> U*(gallows) > U*(root)
  Dialect       -> U*(root)    >= U*(gallows)
where U*(X) is the section-predictiveness of feature X (below).

FEATURES per word: gallows = the primary gallows base present
(t/k/p/f) or 'none' (5 categories — the "4 determinatives + unmarked"
of the hypothesis); root = gallows-stripped, e-collapsed form. SECTION
= folio-number taxonomy (herbal-A/B, zodiac, bio, cosmo, pharma, text).

METRIC (cardinality-fair): U(section|X) = MI(X;section)/H(section), the
fraction of section-uncertainty X explains. High-cardinality features
(roots) inflate this by chance, so we subtract a shuffle null:
U*(X) = U(section|X) - mean over N_NULL of U(section|X_shuffled), where
X_shuffled permutes X's labels across tokens (preserving X's marginal).
U* is the section information in X ABOVE what its cardinality alone
buys. Reported for gallows and root; the comparison is the verdict.

CONTROLS (the instrument must separate the two hypotheses):
  P-DET (determinative positive): synthetic sections; each token = a
    root drawn from a pool SHARED across sections + a section-specific
    determinative marker. Roots carry no section info; the marker
    carries all of it. Must show U*(marker) >> U*(root).
  P-DIA (dialect positive / determinative negative): synthetic
    sections; each with its OWN disjoint root vocabulary, marker
    assigned section-INDEPENDENTLY. Roots carry the section info; the
    marker none. Must show U*(root) >> U*(marker).
  GATE: P-DET shows marker>root AND P-DIA shows root>marker (the
    instrument distinguishes the mechanisms), else gate_failed.

PRE-REGISTERED VERDICTS (Currier A, B, and pooled reported; adjudicate
on pooled VMS):
  gate_failed             — controls do not separate.
  determinative_supported — U*(gallows) > U*(root) by >= MARGIN and the
    profile matches P-DET: gallows behave like semantic determinatives.
    SUGGESTIVE, quarantined — this would revive the Egyptian core claim
    as a real (not self-scored) finding.
  dialect_not_determinative — U*(root) >= U*(gallows): the
    gallows-section association is dialectal vocabulary variation, not a
    determinative system. The Egyptian determinative claim is killed on
    its core prediction (logged with equal prominence).
  ambiguous               — neither dominates by MARGIN.
Vocabulary discipline: a test of one structural claim; nothing decoded.
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
from common.core import FOLIO_DIR, ivtff_clean_words, strip_gallows, \
    collapse_e, gallows_base

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 125
N_NULL = 30
MARGIN = 0.005            # min U* gap for a directional verdict
SECTIONS = 6             # synthetic control sections
ROOTS_PER = 250
TOKENS_PER_SECTION = 6000
MIN_LINE_WORDS = 2


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


def primary_gallows(word):
    stripped, found = strip_gallows(word)
    return gallows_base(found[0]) if found else 'none'


def load_vms(hand=None):
    """(gallows, root, section) per word, optionally one Currier hand."""
    rows = []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        lang = m.group(1) if m else None
        if hand and lang != hand:
            continue
        section = vms_section(fpath.stem)
        if section == 'unknown':
            continue
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            for w in ivtff_clean_words(line[line.index('>') + 1:].strip()):
                g = primary_gallows(w)
                root = collapse_e(strip_gallows(w)[0])
                rows.append((g, root or '_', section))
    return rows


def build_p_det(rng):
    """Shared roots + section-specific determinative."""
    pool = [f'r{i}' for i in range(ROOTS_PER)]
    markers = [f'd{s}' for s in range(SECTIONS)]
    rows = []
    for s in range(SECTIONS):
        for _ in range(TOKENS_PER_SECTION):
            rows.append((markers[s], rng.choice(pool), f'S{s}'))
    return rows


def build_p_dia(rng):
    """Disjoint root vocab per section + section-independent marker."""
    pools = [[f's{s}_r{i}' for i in range(ROOTS_PER)]
             for s in range(SECTIONS)]
    markers = [f'd{s}' for s in range(SECTIONS)]
    rows = []
    for s in range(SECTIONS):
        for _ in range(TOKENS_PER_SECTION):
            rows.append((rng.choice(markers), rng.choice(pools[s]),
                         f'S{s}'))
    return rows


# ── information metric ──────────────────────────────────────────────
def entropy(counter):
    tot = sum(counter.values())
    return -sum(c / tot * math.log2(c / tot)
                for c in counter.values() if c) if tot else 0.0


def uncertainty_coef(xs, secs):
    """U(section|X) = MI(X;section) / H(section)."""
    Hsec = entropy(Counter(secs))
    if Hsec == 0:
        return 0.0
    joint = Counter(zip(xs, secs))
    xmarg = Counter(xs)
    N = len(xs)
    # H(section|X) = sum_x p(x) H(section|x)
    by_x = defaultdict(Counter)
    for (x, s), c in joint.items():
        by_x[x][s] += c
    Hcond = sum((sum(cx.values()) / N) * entropy(cx)
                for cx in by_x.values())
    return (Hsec - Hcond) / Hsec


def excess_U(xs, secs, rng):
    real = uncertainty_coef(xs, secs)
    nulls = []
    idx = list(range(len(xs)))
    for _ in range(N_NULL):
        perm = xs[:]
        rng.shuffle(perm)
        nulls.append(uncertainty_coef(perm, secs))
    return round(real - statistics.mean(nulls), 5), round(real, 5)


def analyse(rows, tag, rng):
    gall = [r[0] for r in rows]
    root = [r[1] for r in rows]
    secs = [r[2] for r in rows]
    ug, ug_raw = excess_U(gall, secs, rng)
    ur, ur_raw = excess_U(root, secs, rng)
    print(f'  {tag:<20} U*(gallows) {ug:+.5f} (raw {ug_raw:.4f}, '
          f'{len(set(gall))} cats)   U*(root) {ur:+.5f} '
          f'(raw {ur_raw:.4f}, {len(set(root))} cats)   n={len(rows)}')
    return {'u_gallows': ug, 'u_root': ur,
            'u_gallows_raw': ug_raw, 'u_root_raw': ur_raw,
            'n_gallows_cats': len(set(gall)),
            'n_root_cats': len(set(root)), 'n_tokens': len(rows)}


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('EGYPTIAN DETERMINATIVE TEST (N10) — classifier or dialect?')
    print('=' * 76)
    print(f'seed={SEED} nulls={N_NULL} margin={MARGIN}; U* = section-'
          'predictiveness above the cardinality-shuffle null')

    res = {}
    res['P_DET'] = analyse(build_p_det(random.Random(SEED)),
                           'P-DET (determinative)', random.Random(SEED + 1))
    res['P_DIA'] = analyse(build_p_dia(random.Random(SEED + 2)),
                           'P-DIA (dialect)', random.Random(SEED + 3))
    res['VMS_full'] = analyse(load_vms(None), 'VMS pooled',
                              random.Random(SEED + 4))
    res['VMS_A'] = analyse(load_vms('A'), 'VMS Currier A',
                           random.Random(SEED + 5))
    res['VMS_B'] = analyse(load_vms('B'), 'VMS Currier B',
                           random.Random(SEED + 6))

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    det, dia = res['P_DET'], res['P_DIA']
    gate = (det['u_gallows'] > det['u_root']
            and dia['u_root'] > dia['u_gallows'])
    print(f'    gate: P-DET marker>root ({det["u_gallows"]:.4f} > '
          f'{det["u_root"]:.4f}) and P-DIA root>marker '
          f'({dia["u_root"]:.4f} > {dia["u_gallows"]:.4f}) -> '
          f'{"PASS" if gate else "FAIL"}')
    v = res['VMS_full']
    diff = v['u_gallows'] - v['u_root']
    if not gate:
        verdict = 'gate_failed'
        print('    GATE FAILED: controls do not separate the mechanisms; '
              'no reading.')
    elif diff >= MARGIN:
        verdict = 'determinative_supported'
        print(f'    DETERMINATIVE SUPPORTED: U*(gallows) exceeds U*(root) '
              f'by {diff:+.5f} (>= {MARGIN}) — gallows predict section '
              'more than the root does, the determinative signature. '
              'The Egyptian core claim is SUPPORTED (SUGGESTIVE, '
              'quarantined).')
    elif v['u_root'] >= v['u_gallows']:
        verdict = 'dialect_not_determinative'
        print(f'    DIALECT, NOT DETERMINATIVE: U*(root) {v["u_root"]:.5f} '
              f'>= U*(gallows) {v["u_gallows"]:.5f} — the section '
              'information lives in the ROOT vocabulary, not the '
              'gallows. The gallows-section association is dialectal '
              'variation, not a determinative system. The Egyptian '
              'determinative claim is KILLED on its core prediction.')
    else:
        verdict = 'ambiguous'
        print(f'    AMBIGUOUS: U*(gallows) {v["u_gallows"]:.5f} vs '
              f'U*(root) {v["u_root"]:.5f} — neither dominates by '
              f'{MARGIN}; no claim.')

    with open(result_path('egyptian_determinative_test.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'n_null': N_NULL,
                              'margin': MARGIN, 'sections': SECTIONS,
                              'roots_per': ROOTS_PER,
                              'tokens_per_section': TOKENS_PER_SECTION},
                   'results': res, 'gate_pass': gate, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/egyptian_determinative_test.json')


if __name__ == '__main__':
    main()
