#!/usr/bin/env python3
"""
Phase 109 — Generative Forgery Tournament (strategy S3)

Question: which machine can forge a Voynich? Every proposed generative
mechanism — Rugg grille (N3), Timm-Schinner self-citation (N4), plain
language (P1/P2), monoalphabetic cipher (P3), verbose cipher (P4), abjad
(P5) — is scored on the FULL 17-feature fingerprint (constraint F5: models
are judged on features they were not designed to explain), as z-distance
to the manuscript.

Yardsticks (pre-registered):
  - INTERNAL-TIGHT  = distance between interleaved halves of the VMS
    (even lines vs odd lines: same process, same drift). A generator at or
    under this is statistically indistinguishable from the manuscript.
  - INTERNAL-LOOSE  = distance between the first and second contiguous
    halves (includes real within-manuscript drift, incl. A/B mixture).
    A generator under this is "as close as the manuscript is to itself
    across time".

Pre-registered kill criteria (from RESEARCH.md S3):
  - A generator closing under INTERNAL-LOOSE means the manuscript is
    statistically forgeable by that family (major result).
  - If NO generator family comes within 3x INTERNAL-LOOSE, all currently
    proposed mechanisms are insufficient (major result the other way).
  - Scope limit (honesty per F6): a loss here kills the CALIBRATED
    GENERATOR AS IMPLEMENTED in phase108, not the whole theory family;
    the per-feature breakdown shows WHERE each family fails, which is the
    actionable output.

Constraint F8: rankings are reported against VMS-full, Currier A, and
Currier B separately ($L= header tags, authoritative per phase101).
Constraint F3: controls were verified before this test existed (phase108).
DOF budget: zero fitted parameters in this script — every generator was
frozen in phase108 before this tournament was run; features and yardsticks
are fixed by this docstring.
"""
import io
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

from common import result_path
from common.core import FOLIO_DIR, ivtff_clean_words
from common.fingerprint import FEATURE_ORDER, fingerprint

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

COMMA_BREAK = True          # IVTFF uncertain-space policy (see finding T1)
MIN_LINE_WORDS = 2          # lines shorter than this are skipped
EXCLUDE_FEATURES = ['n_tokens', 'n_types']  # size features excluded from distance

CONTROLS_DIR = FOLIO_DIR.parent / 'data' / 'controls'
if not CONTROLS_DIR.exists():
    CONTROLS_DIR = Path(__file__).resolve().parent.parent / 'data' / 'controls'


def load_control(path):
    return [ln.split() for ln in path.read_text(encoding='utf-8').splitlines()
            if len(ln.split()) >= MIN_LINE_WORDS]


def load_vms_by_currier():
    """(all_lines, A_lines, B_lines) via authoritative $L= header tags."""
    full, a, b = [], [], []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        lang = m.group(1) if m else None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            rest = line[line.index('>') + 1:].strip()
            words = ivtff_clean_words(rest, comma_break=COMMA_BREAK)
            if len(words) < MIN_LINE_WORDS:
                continue
            full.append(words)
            if lang == 'A':
                a.append(words)
            elif lang == 'B':
                b.append(words)
    return full, a, b


def pairwise_z(f1, f2, scales, features):
    """Mean per-feature |difference| in population-scale units."""
    zs = []
    for f in features:
        v1, v2, sd = f1.get(f), f2.get(f), scales.get(f)
        if sd is None or sd < 1e-12:
            continue
        if any(not isinstance(v, float) or math.isnan(v) for v in (v1, v2)):
            continue
        zs.append(abs(v1 - v2) / sd)
    return sum(zs) / len(zs) if zs else float('nan')


def main():
    features = [f for f in FEATURE_ORDER if f not in EXCLUDE_FEATURES]

    vms_full, vms_a, vms_b = load_vms_by_currier()
    corpora = {'VMS_full': vms_full, 'VMS_currier_A': vms_a,
               'VMS_currier_B': vms_b,
               'VMS_half_even': vms_full[0::2], 'VMS_half_odd': vms_full[1::2],
               'VMS_half_first': vms_full[:len(vms_full) // 2],
               'VMS_half_second': vms_full[len(vms_full) // 2:]}
    for p in sorted(CONTROLS_DIR.glob('*.txt')):
        corpora[p.stem] = load_control(p)

    fps = {k: fingerprint(v, k) for k, v in corpora.items()}

    # population scale per feature: std across the 9 controls + VMS_full
    pop = [fps[k] for k in fps
           if k in ('VMS_full',) or not k.startswith('VMS')]
    scales = {}
    for f in features:
        vals = [p[f] for p in pop
                if isinstance(p[f], float) and not math.isnan(p[f])]
        if len(vals) >= 3:
            mu = sum(vals) / len(vals)
            scales[f] = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5

    tight = pairwise_z(fps['VMS_half_even'], fps['VMS_half_odd'], scales, features)
    loose = pairwise_z(fps['VMS_half_first'], fps['VMS_half_second'], scales, features)

    entrants = [k for k in fps if not k.startswith('VMS')]
    print("=" * 76)
    print("PHASE 109 — GENERATIVE FORGERY TOURNAMENT")
    print("=" * 76)
    print(f"features scored: {len(features)}  |  fitted parameters here: 0")
    print(f"yardstick INTERNAL-TIGHT (even/odd halves):        {tight:.3f}")
    print(f"yardstick INTERNAL-LOOSE (first/second halves):    {loose:.3f}")
    print(f"forgeability bar = INTERNAL-LOOSE; insufficiency bar = 3x = {3 * loose:.3f}")

    results = {}
    for target in ('VMS_full', 'VMS_currier_A', 'VMS_currier_B'):
        ranking = sorted(
            ((pairwise_z(fps[e], fps[target], scales, features), e)
             for e in entrants))
        results[target] = [(e, round(d, 4)) for d, e in ranking]
        print(f"\n  ranking vs {target}:")
        for d, e in ranking:
            verdict = ("  << UNDER LOOSE YARDSTICK (forgeable)" if d <= loose
                       else "")
            print(f"    {e:<18} z-dist {d:6.3f}{verdict}")

    # per-feature breakdown for the top-2 entrants vs VMS_full
    top2 = [e for _, e in sorted(
        ((pairwise_z(fps[e], fps['VMS_full'], scales, features), e)
         for e in entrants))][:2]
    print(f"\n  per-feature |z| breakdown vs VMS_full (top 2: {', '.join(top2)}):")
    print(f"    {'feature':<16}" + "".join(f"{e[:14]:>16}" for e in top2))
    for f in features:
        row = f"    {f:<16}"
        for e in top2:
            v1, v2 = fps[e].get(f), fps['VMS_full'].get(f)
            sd = scales.get(f)
            if (sd and sd > 1e-12 and isinstance(v1, float) and isinstance(v2, float)
                    and not (math.isnan(v1) or math.isnan(v2))):
                row += f"{abs(v1 - v2) / sd:>16.2f}"
            else:
                row += f"{'-':>16}"
        print(row)

    # adjudicate pre-registered criteria
    best_d, best = min((pairwise_z(fps[e], fps['VMS_full'], scales, features), e)
                       for e in entrants)
    print("\n  ADJUDICATION (pre-registered):")
    if best_d <= loose:
        print(f"    {best} closes under INTERNAL-LOOSE ({best_d:.3f} <= {loose:.3f})"
              f" -> manuscript statistically forgeable by this family AS CALIBRATED.")
    elif best_d <= 3 * loose:
        print(f"    best entrant {best} at {best_d:.3f}: inside 3x LOOSE"
              f" ({3 * loose:.3f}) but above LOOSE ({loose:.3f})"
              f" -> partially adequate; see per-feature breakdown for the gap.")
    else:
        print(f"    no entrant within 3x INTERNAL-LOOSE ({3 * loose:.3f});"
              f" best = {best} at {best_d:.3f}"
              f" -> all mechanisms AS CALIBRATED are insufficient.")

    out = {
        'features': features,
        'yardsticks': {'internal_tight': tight, 'internal_loose': loose},
        'rankings': results,
        'fingerprints': {k: {f: (None if isinstance(v, float) and math.isnan(v)
                                 else v) for f, v in fp.items()}
                         for k, fp in fps.items()},
    }
    with open(result_path('phase109_forgery_tournament.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(out, fh, indent=1)
    print("\n  -> results/phase109_forgery_tournament.json")


if __name__ == '__main__':
    main()
