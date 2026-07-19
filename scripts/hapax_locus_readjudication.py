#!/usr/bin/env python3
"""
Hapax Locus Re-adjudication (N7) — does language_vs_cipher Part D's
hapax-clustering verdict survive removing non-prose loci?

PROVENANCE (operator-directed audit, 2026-07-19): language_vs_cipher is
a pre-audit-era test whose local loader takes every >= 2-word locus of
any IVTFF type. Measurement showed its Part-D hapax corpus is
contaminated by non-paragraph material that is BOTH hapax-enriched
(rings 8.6%, radial 14.2%, labels 11.4% hapax-token rate vs paragraphs
5.1%) AND layout-clustered by section (rings in zodiac/cosmo, labels in
pharma/herbal) — a bias pointing specifically toward Part D's
"CONCENTRATED -> natural language" reading. This instrument re-runs
Part D's EXACT statistics under a clean corpus policy and adjudicates
by the ORIGINAL test's own printed thresholds — same rules, cleaned
data; no new criteria are invented.

REPLICATION (faithful local copies of the legacy pipeline): the
original >= 2-word loader (T1-era defects and all — this is a
re-adjudication of THAT test, not a re-design), gallows-stripped
e-collapsed vocabulary (common.get_collapsed), the original folio-number
section map, hapax = collapsed type with corpus count 1, and Part D's
two statistics with its printed thresholds:
  chi2 over sections (observed hapax tokens vs token-proportional
      expectation): CONCENTRATED iff chi2 > 15 (original rule).
  burstiness B = (std-mean)/(std+mean) of inter-hapax line gaps:
      CLUSTERED iff B > 0.1; UNIFORM iff B < 0.05; else MILD (original
      rule).
GATE: the all-loci policy must reproduce the committed golden's Part-D
numbers (chi2 to 0.1, B to 0.001, parsed from
golden/language_vs_cipher.stdout.txt) — abort otherwise.

POLICIES: 'all' (the original corpus), 'P_only' (paragraph loci only —
the adjudicated decontamination), 'nonP_only' (the removed material,
reported observationally).

PRE-REGISTERED OUTCOMES:
  gate_failed      — golden reproduction fails.
  verdict_survives — P_only still passes every language-favoring
                     classification the all-loci corpus passed
                     (chi2 > 15 if it was; B class not weaker than it
                     was): Part D's conclusion is robust to the
                     contamination; the asterisk is removed.
  verdict_softened — any classification weakens under P_only
                     (CONCENTRATED -> not, or CLUSTERED -> MILD/
                     UNIFORM): part of Part D's language-favoring
                     evidence was layout artifact; the legacy test's
                     Part-D verdict is demoted to "conditional on
                     corpus scope" and the corpse is logged.
Vocabulary discipline: this adjudicates one legacy sub-test's
robustness; it says nothing about language vs cipher itself.
"""
import io
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from common import get_collapsed, result_path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 121                # no randomness used; recorded for convention
CHI2_THRESHOLD = 15.0     # Part D's original printed rule
B_CLUSTERED = 0.1         # Part D's original printed rule
B_UNIFORM = 0.05
MIN_LINE_WORDS = 2        # the legacy loader's filter, kept faithfully

FOLIO_DIR = Path('folios')
GOLDEN = Path('golden') / 'language_vs_cipher.stdout.txt'


def load_lines(policy):
    """The legacy loader, faithfully (>=2 [a-z]+ words, naive token
    regex), plus the locus-type policy."""
    lines, folios = [], []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        for line in fpath.read_text(encoding='utf-8',
                                    errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'):
                continue
            m = re.match(r'<([^>]+)>', line)
            if m:
                tm = re.search(r',[@+*=]?([A-Za-z])', m.group(1))
                ltype = tm.group(1).upper() if tm else None
                if policy == 'P_only' and ltype != 'P':
                    continue
                if policy == 'nonP_only' and ltype == 'P':
                    continue
            elif policy != 'all':
                continue
            rest = line[m.end():].strip() if m else line
            if not rest:
                continue
            words = [w.strip() for w in re.split(r'[.\s,;]+', rest)
                     if w.strip() and re.match(r'^[a-z]+$', w.strip())]
            if len(words) >= MIN_LINE_WORDS:
                lines.append(words)
                folios.append(fpath.stem)
    return lines, folios


def get_section(folio):
    try:
        num = int(re.match(r'f(\d+)', folio).group(1))
    except Exception:
        return 'unknown'
    if num <= 56:
        return 'herbal'
    elif num <= 67:
        return 'astro'
    elif num <= 73:
        return 'cosmo'
    elif num <= 84:
        return 'bio'
    elif num <= 86:
        return 'cosmo2'
    elif num <= 102:
        return 'pharma'
    return 'text'


def part_d(policy):
    """Part D's statistics, replicated faithfully."""
    raw_lines, folios = load_lines(policy)
    line_collapsed = [[get_collapsed(w) for w in line]
                      for line in raw_lines]
    vocab = Counter(w for line in line_collapsed for w in line)
    hapaxes = {w for w, c in vocab.items() if c == 1}

    sec_hapax, sec_tokens = Counter(), Counter()
    for line, folio in zip(line_collapsed, folios):
        section = get_section(folio)
        for w in line:
            sec_tokens[section] += 1
            if w in hapaxes:
                sec_hapax[section] += 1
    total_hapax = sum(sec_hapax.values())
    total_tok = sum(sec_tokens.values())
    expected = {s: total_hapax * sec_tokens[s] / total_tok
                for s in sec_hapax}
    chi2 = sum((sec_hapax[s] - expected[s]) ** 2 / max(expected[s], 1)
               for s in sec_hapax)

    positions = [i for i, line in enumerate(line_collapsed)
                 for w in line if w in hapaxes]
    gaps = [b - a for a, b in zip(positions, positions[1:])]
    mean_gap = statistics.mean(gaps)
    std_gap = statistics.pstdev(gaps)
    B = ((std_gap - mean_gap) / (std_gap + mean_gap)
         if (std_gap + mean_gap) > 0 else 0.0)

    chi_class = 'CONCENTRATED' if chi2 > CHI2_THRESHOLD else 'UNIFORM'
    b_class = ('CLUSTERED' if B > B_CLUSTERED else
               'UNIFORM' if B < B_UNIFORM else 'MILD')
    return {'n_lines': len(raw_lines), 'n_tokens': total_tok,
            'n_types': len(vocab), 'n_hapax': len(hapaxes),
            'chi2': round(chi2, 1), 'chi_class': chi_class,
            'burstiness': round(B, 3), 'b_class': b_class}


def parse_golden():
    t = GOLDEN.read_text(encoding='utf-8', errors='replace', newline='')
    chi = float(re.search(
        r'Chi-square \(hapax concentration\) = ([\d.]+)', t).group(1))
    b = float(re.search(r'Burstiness B = ([\d.-]+)', t).group(1))
    return chi, b


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('HAPAX LOCUS RE-ADJUDICATION (N7) — Part D, same rules, '
          'clean corpus')
    print('=' * 76)
    print(f'original thresholds: chi2 > {CHI2_THRESHOLD} = CONCENTRATED; '
          f'B > {B_CLUSTERED} = CLUSTERED, < {B_UNIFORM} = UNIFORM')

    rows = {p: part_d(p) for p in ('all', 'P_only', 'nonP_only')}
    for p, r in rows.items():
        print(f'  {p:<9} {r["n_lines"]:>5} lines {r["n_tokens"]:>6} tok '
              f'{r["n_hapax"]:>5} hapax | chi2 {r["chi2"]:>6} '
              f'({r["chi_class"]}) | B {r["burstiness"]:+.3f} '
              f'({r["b_class"]})')

    g_chi, g_b = parse_golden()
    a = rows['all']
    gate_ok = (abs(a['chi2'] - g_chi) <= 0.1
               and abs(a['burstiness'] - g_b) <= 0.001)
    print(f'\n  gate: all-loci reproduces golden Part D '
          f'(chi2 {g_chi}, B {g_b}) -> {"PASS" if gate_ok else "FAIL"}')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    p = rows['P_only']
    if not gate_ok:
        verdict = 'gate_failed'
        print('    GATE FAILED: replication does not reproduce the '
              'committed golden; no reading.')
    else:
        chi_ok = (p['chi_class'] == 'CONCENTRATED'
                  if a['chi_class'] == 'CONCENTRATED' else True)
        order = {'UNIFORM': 0, 'MILD': 1, 'CLUSTERED': 2}
        b_ok = order[p['b_class']] >= order[a['b_class']]
        if chi_ok and b_ok:
            verdict = 'verdict_survives'
            print('    VERDICT SURVIVES: on paragraph-only text, Part D '
                  'still passes every language-favoring classification '
                  'it passed on the contaminated corpus (chi2 '
                  f'{a["chi2"]} -> {p["chi2"]}, B {a["burstiness"]:+.3f} '
                  f'-> {p["burstiness"]:+.3f}). The contamination '
                  'asterisk is removed; the hapax-clustering evidence '
                  'is a property of the running text.')
        else:
            verdict = 'verdict_softened'
            print('    VERDICT SOFTENED: decontamination weakens the '
                  f'classification (chi2 {a["chi2"]} -> {p["chi2"]}, '
                  f'{a["chi_class"]} -> {p["chi_class"]}; B '
                  f'{a["burstiness"]:+.3f} -> {p["burstiness"]:+.3f}, '
                  f'{a["b_class"]} -> {p["b_class"]}) — part of Part '
                  'D\'s language-favoring evidence was layout artifact. '
                  'The legacy verdict is demoted to conditional-on-'
                  'corpus-scope; corpse logged.')

    with open(result_path('hapax_locus_readjudication.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED,
                              'chi2_threshold': CHI2_THRESHOLD,
                              'b_clustered': B_CLUSTERED,
                              'b_uniform': B_UNIFORM,
                              'min_line_words': MIN_LINE_WORDS},
                   'golden_ref': {'chi2': g_chi, 'burstiness': g_b},
                   'gate_ok': gate_ok,
                   'rows': rows, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/hapax_locus_readjudication.json')


if __name__ == '__main__':
    main()
