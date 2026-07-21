#!/usr/bin/env python3
"""
Phonotactic Interior Gradient, Class-Controlled (S3 rung 6b) — does
glyph-pair phonotactic constraint predict interior position BEYOND the
onset class? (N6j)

PROVENANCE: N6i found the interior-gradient residual phonotactically
structured but SOFT (empirical p 0.0205, DOF-fragile at ~13 class
points). This rung re-tests at higher resolution — but the first design
attempt exposed the real obstacle, which dictates the correct test:

  onset successor-entropy is a DETERMINISTIC FUNCTION of the first
  glyph, and the first glyph IS the class. So "onset-se predicts
  interior position" is merely the S7 class-position effect
  re-parametrized — it cannot separate a phonotactic LAW ("constrained
  onsets sit earlier") from "the class q happens to sit early". A
  first-execution check confirmed this: raw onset-se vs position is
  collinear with class, and the glyph-pair variant even reverses sign.

THE CORRECT TEST (fixed before the run that counts): control for onset
class. Within each first-glyph class, second-glyph variation gives the
glyph-PAIR successor-entropy se2 real within-class variance. If
phonotactic constraint is a genuine positional law, se2 should predict
interior position WITHIN classes (onset held fixed). Operationally:
class-mean-center both u (normalized interior position) and se2 by the
token's onset class, then correlate the residuals — a partial
correlation of position with glyph-pair constraint controlling for
onset identity. NULL: N_PERM within-line shuffles (order destroyed,
class means and centering recomputed each time). Interior tokens with a
definable glyph pair (>= 2 glyphs) only.

PRE-REGISTERED VERDICTS:
  phonotactic_firmed     — |partial r| significant at two-sided
                           empirical p < P_FIRM (0.005): glyph-pair
                           phonotactic constraint predicts interior
                           position beyond the onset class — a genuine
                           phonotactic effect, N6i firmed past the house
                           bar and free of the class confound.
                           SUGGESTIVE, quarantined.
  phonotactic_weak       — P_FIRM <= p < P_WEAK (0.05): a within-class
                           effect exists but not past the house bar.
  phonotactic_is_class_confound — p >= P_WEAK: with onset class
                           controlled, glyph-pair constraint does NOT
                           predict position. N6i's "phonotactic residual"
                           was the onset-class effect re-expressed, not
                           a phonotactic law; N6i downgraded. (Reported
                           for the record: the RAW onset-se correlation,
                           which by construction just mirrors the class
                           effect.)
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

SEED = 131
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


def entropy(counter):
    tot = sum(counter.values())
    return -sum(c / tot * math.log2(c / tot)
                for c in counter.values() if c) if tot else 0.0


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return num / (dx * dy) if dx > 0 and dy > 0 else 0.0


def collect(lines, se2_of, se_of, rng=None):
    """Interior tokens: (u, onset class, se2, se). Optionally shuffled."""
    us, cls, se2s, ses = [], [], [], []
    for line in lines:
        seq = line[:]
        if rng is not None:
            rng.shuffle(seq)
        L = len(seq)
        span = L - 4
        for j in range(2, L - 2):
            w = seq[j]
            gl = eva_to_glyphs(w)
            if len(gl) < 2:
                continue
            us.append((j - 2) / span if span > 0 else 0.5)
            cls.append(gl[0])
            se2s.append(se2_of(gl))
            ses.append(se_of(gl))
    return us, cls, se2s, ses


def class_partial(us, cls, se2s):
    """Pearson of u and se2 after class-mean-centering both (partial
    correlation controlling for onset class)."""
    mu, ms = defaultdict(list), defaultdict(list)
    for u, c, s in zip(us, cls, se2s):
        mu[c].append(u)
        ms[c].append(s)
    umean = {c: statistics.mean(v) for c, v in mu.items()}
    smean = {c: statistics.mean(v) for c, v in ms.items()}
    uc = [u - umean[c] for u, c in zip(us, cls)]
    sc = [s - smean[c] for s, c in zip(se2s, cls)]
    return pearson(uc, sc)


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('PHONOTACTIC INTERIOR GRADIENT, CLASS-CONTROLLED (S3 rung 6b) '
          '(N6j)')
    print('=' * 76)
    print(f'seed={SEED} perms={N_PERM} firm two-sided p<{P_FIRM}; '
          'glyph-pair constraint, onset class controlled')

    lines = load_vms_b()
    succ, succ2 = defaultdict(Counter), defaultdict(Counter)
    for line in lines:
        for w in line:
            gl = eva_to_glyphs(w)
            for i, g in enumerate(gl):
                succ[g][gl[i + 1] if i + 1 < len(gl) else '$'] += 1
            if len(gl) >= 2:
                succ2[(gl[0], gl[1])][gl[2] if len(gl) > 2 else '$'] += 1
    se_glyph = {g: entropy(c) for g, c in succ.items()}
    se2_pair = {p: entropy(c) for p, c in succ2.items()}
    mse = sum(se_glyph.values()) / len(se_glyph)
    mse2 = sum(se2_pair.values()) / len(se2_pair)

    def se_of(gl):
        return se_glyph.get(gl[0], mse)

    def se2_of(gl):
        return se2_pair.get((gl[0], gl[1]), mse2)

    us, cls, se2s, ses = collect(lines, se2_of, se_of)
    print(f'  {len(lines)} B lines; {len(us)} interior tokens with a '
          f'glyph pair; {len(set(cls))} onset classes')

    # raw onset-se (collinear-with-class baseline) and the real test
    raw_r = pearson(us, ses)
    real_r = class_partial(us, cls, se2s)
    print(f'  RAW onset-se vs position {raw_r:+.4f} (collinear with '
          'class — not the test)')
    print(f'  class-controlled glyph-pair-se2 vs position (PARTIAL) '
          f'{real_r:+.4f}  <- the test')

    rng = random.Random(SEED)
    n_ge = 0
    nmax = 0.0
    for _ in range(N_PERM):
        nu, nc, ns2, _ = collect(lines, se2_of, se_of, rng)
        nr = class_partial(nu, nc, ns2)
        if abs(nr) >= abs(real_r):
            n_ge += 1
        nmax = max(nmax, abs(nr))
    p_emp = (1 + n_ge) / (N_PERM + 1)
    print(f'  within-line null (two-sided): p {p_emp:.4f}  '
          f'(null max |r| {nmax:.4f})')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    if p_emp < P_FIRM:
        verdict = 'phonotactic_firmed'
        print(f'    PHONOTACTIC FIRMED: with onset class controlled, '
              f'glyph-pair constraint predicts interior position (partial '
              f'r {real_r:+.4f}, p {p_emp:.4f} < {P_FIRM}) — a genuine '
              'phonotactic effect beyond the class confound; N6i firmed. '
              'SUGGESTIVE, quarantined.')
    elif p_emp < P_WEAK:
        verdict = 'phonotactic_weak'
        print(f'    PHONOTACTIC WEAK: within-class effect present '
              f'(r {real_r:+.4f}, p {p_emp:.4f}) but not past the house '
              'bar.')
    else:
        verdict = 'phonotactic_is_class_confound'
        print(f'    PHONOTACTIC IS CLASS CONFOUND: with onset class '
              f'controlled, glyph-pair constraint does NOT predict '
              f'position (partial r {real_r:+.4f}, p {p_emp:.4f} >= '
              f'{P_WEAK}). N6i\'s "phonotactic residual" was the onset-'
              'class effect re-expressed (raw onset-se '
              f'{raw_r:+.4f} just mirrors the class-position effect), '
              'not a phonotactic law. N6i downgraded — the interior '
              'gradient\'s residual is NOT demonstrably phonotactic once '
              'class is controlled. Corpse logged.')

    with open(result_path('line_discipline_phonotactic_token.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'n_perm': N_PERM,
                              'p_firm': P_FIRM, 'p_weak': P_WEAK,
                              'min_line_words': MIN_LINE_WORDS},
                   'results': {'n_lines': len(lines),
                               'n_interior_pair_tokens': len(us),
                               'raw_onset_se_r': round(raw_r, 5),
                               'class_controlled_partial_r':
                                   round(real_r, 5),
                               'p_two_sided': round(p_emp, 4),
                               'null_max_abs_r': round(nmax, 5)},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_discipline_phonotactic_token.json')


if __name__ == '__main__':
    main()
