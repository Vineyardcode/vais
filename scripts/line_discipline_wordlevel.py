#!/usr/bin/env python3
"""
Interior Gradient — Word-Level Predictors (S3 rung 7) — does anything
below the onset class predict the residual? (N6k)

PROVENANCE: the interior gradient reduces to onset-class properties
(freq + gallows + length + within-word morphology); its residual is a
floor — NOT phonotactic once onset class is controlled (N6j killed
N6i). The open question: is there ANY word-level property, finer than
the first-glyph class, that predicts a word's interior position once
the class is held fixed? This rung tests the two most motivated
candidates with the N6j-validated method (class-controlled partial
correlation at token resolution — thousands of points, no DOF ceiling).

HYPOTHESES (fixed before running), both position-free WORD-level
properties with real within-onset-class variation:
  (A) FUNCTION vs CONTENT — individual word log-frequency. The oldest
      structural distinction: function words (frequent) vs content
      words (rare). If the line orders words partly by this, then
      WITHIN an onset class, high-frequency words sit at systematically
      different interior positions than low-frequency ones.
  (B) FINE LENGTH — individual word length (class-level length is
      already a principle; this asks whether length matters BELOW the
      class).

METHOD (N6j): over every interior word token of Currier B, class-mean-
center both the normalized interior position u and the candidate
property by the token's onset class, then correlate the residuals (a
partial correlation controlling for onset class). NULL: N_PERM within-
line shuffles (order destroyed, centering recomputed). Two-sided
empirical p. DESCRIPTIVE (observational): per-onset-class mean interior
position, to localize where the gradient/residual lives.

PRE-REGISTERED VERDICTS (primary = the frequency hypothesis A):
  gate_failed              — (reserved; no external gate here).
  residual_frequency_effect — |partial r_freq| significant at two-sided
      p < P_FIRM (0.005): within onset class, word frequency predicts
      interior position — the residual is partly a function/content-word
      effect below the class. SUGGESTIVE, quarantined; direction
      reported.
  residual_length_only     — frequency not significant but within-class
      LENGTH is (p_len < P_FIRM): fine length, not frequency, is the
      sub-class predictor.
  residual_unexplained     — neither predicts position within class at
      the house bar: no word-level property below the onset class
      accounts for the residual. It is a floor at word resolution —
      the interior gradient's residue is, as far as the program can
      measure, irreducible. Corpse logged with the descriptive
      per-class gradient.
Vocabulary discipline: a partial correlation of statistics; nothing
decoded.
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

SEED = 132
N_PERM = 2000
P_FIRM = 0.005
P_WEAK = 0.05
MIN_LINE_WORDS = 5


def load_vms_b():
    lines = []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        if not m or m.group(1) != 'B':
            continue
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if len(words) >= MIN_LINE_WORDS:
                lines.append(words)
    return lines


def first_glyph(w):
    g = eva_to_glyphs(w)
    return g[0] if g else w[0]


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return num / (dx * dy) if dx > 0 and dy > 0 else 0.0


def collect(lines, wfreq, rng=None):
    """Interior tokens: (u, onset class, log word-freq, word length)."""
    us, cls, lf, wl = [], [], [], []
    for line in lines:
        seq = line[:]
        if rng is not None:
            rng.shuffle(seq)
        L = len(seq)
        span = L - 4
        for j in range(2, L - 2):
            w = seq[j]
            us.append((j - 2) / span if span > 0 else 0.5)
            cls.append(first_glyph(w))
            lf.append(math.log(wfreq[w]))
            wl.append(len(w))
    return us, cls, lf, wl


def class_partial(us, cls, xs):
    mu, mx = defaultdict(list), defaultdict(list)
    for u, c, x in zip(us, cls, xs):
        mu[c].append(u)
        mx[c].append(x)
    um = {c: statistics.mean(v) for c, v in mu.items()}
    xm = {c: statistics.mean(v) for c, v in mx.items()}
    uc = [u - um[c] for u, c in zip(us, cls)]
    xc = [x - xm[c] for x, c in zip(xs, cls)]
    return pearson(uc, xc)


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('INTERIOR GRADIENT — WORD-LEVEL PREDICTORS (S3 rung 7) (N6k)')
    print('=' * 76)
    print(f'seed={SEED} perms={N_PERM} firm two-sided p<{P_FIRM}; '
          'class-controlled partial correlations at token resolution')

    lines = load_vms_b()
    wfreq = Counter(w for line in lines for w in line)
    us, cls, lf, wl = collect(lines, wfreq)
    print(f'  {len(lines)} B lines; {len(us)} interior tokens; '
          f'{len(set(cls))} onset classes')

    # descriptive: per-class mean interior position (the gradient)
    byc = defaultdict(list)
    for u, c in zip(us, cls):
        byc[c].append(u)
    gradient = {c: round(statistics.mean(v), 3)
                for c, v in byc.items() if len(v) >= 30}
    print('  per-class mean interior position (early -> late): '
          + '  '.join(f'{c} {u}' for c, u in
                      sorted(gradient.items(), key=lambda kv: kv[1])))

    r_freq = class_partial(us, cls, lf)
    r_len = class_partial(us, cls, wl)
    print(f'  class-controlled partial r: word-frequency {r_freq:+.4f}   '
          f'word-length {r_len:+.4f}')

    rng = random.Random(SEED)
    ge_f = ge_l = 0
    for _ in range(N_PERM):
        nu, nc, nlf, nwl = collect(lines, wfreq, rng)
        if abs(class_partial(nu, nc, nlf)) >= abs(r_freq):
            ge_f += 1
        if abs(class_partial(nu, nc, nwl)) >= abs(r_len):
            ge_l += 1
    p_freq = (1 + ge_f) / (N_PERM + 1)
    p_len = (1 + ge_l) / (N_PERM + 1)
    print(f'  within-line null (two-sided): p(frequency) {p_freq:.4f}  '
          f'p(length) {p_len:.4f}')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    if p_freq < P_FIRM:
        verdict = 'residual_frequency_effect'
        direction = ('later' if r_freq > 0 else 'earlier')
        print(f'    RESIDUAL FREQUENCY EFFECT: within onset class, word '
              f'frequency predicts interior position (partial r '
              f'{r_freq:+.4f}, p {p_freq:.4f} < {P_FIRM}) — frequent '
              f'words sit {direction}. The residual is partly a '
              'function/content-word effect below the class. SUGGESTIVE, '
              'quarantined.')
    elif p_len < P_FIRM:
        verdict = 'residual_length_only'
        print(f'    RESIDUAL LENGTH ONLY: frequency not significant '
              f'(p {p_freq:.4f}) but within-class word length is '
              f'(r {r_len:+.4f}, p {p_len:.4f}) — fine length is the '
              'sub-class predictor. SUGGESTIVE, quarantined.')
    else:
        verdict = 'residual_unexplained'
        print(f'    RESIDUAL UNEXPLAINED: neither word frequency '
              f'(p {p_freq:.4f}) nor length (p {p_len:.4f}) predicts '
              'interior position within onset class at the house bar. No '
              'word-level property below the class accounts for the '
              'residual — it is a floor at word resolution. The interior '
              'gradient is fully a first-glyph-CLASS effect; what orders '
              'the classes beyond frequency/gallows/length/morphology '
              'stays genuinely unexplained. Corpse logged.')

    with open(result_path('line_discipline_wordlevel.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'n_perm': N_PERM,
                              'p_firm': P_FIRM, 'p_weak': P_WEAK,
                              'min_line_words': MIN_LINE_WORDS},
                   'results': {'n_lines': len(lines),
                               'n_interior_tokens': len(us),
                               'partial_r_frequency': round(r_freq, 5),
                               'partial_r_length': round(r_len, 5),
                               'p_frequency': round(p_freq, 4),
                               'p_length': round(p_len, 4),
                               'per_class_gradient': gradient},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_discipline_wordlevel.json')


if __name__ == '__main__':
    main()
