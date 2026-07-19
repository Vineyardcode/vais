#!/usr/bin/env python3
"""
Line-Class Family Test (portfolio S5/S6 bridge) — what KIND of process
orders Currier B's lines? (N4)

PROVENANCE: the S7 ladder established (quarantined SUGGESTIVE, robust
across five transliterations, all sections, paragraph-controlled) that
Currier B's lines order their words by word-INITIAL glyph class,
front-loaded in the early interior. This instrument asks the next
registered question: which calibrated GENERATIVE FAMILY does that
ordering profile most resemble — natural language (S-portfolio:
language family), typed records (S5 codebook/nomenclator family),
positional notation (S6 numeral family), or copy-hoax (Timm family)?

REPRESENTATION (fixed, no fitting to the manuscript): each line -> the
sequence of its words' FIRST GLYPHS, binned to the corpus's top
CLASS_K first-glyphs + OTHER. Two holdout structure signatures, both
normalized by the unigram class entropy so different alphabets are
comparable:
  r_pos = (unigram loss - positional-model loss) / unigram loss,
          positional model = P(class | S7 position bin)
  r_bi  = (unigram loss - bigram loss) / unigram loss,
          bigram model = P(class | previous class), START at line start
Both with the standard folio-holdout (10 splits, medians; pseudo-folio
blocks for controls). Note the families are NOT distinguished by either
number alone (a strict positional system is also neighbor-predictable);
they are distinguished by the PROFILE (r_pos, r_bi).

FAMILY CENTROIDS (controls first, per charter):
  P1    latin_plain pseudo-lines      — natural language
  PREC  synthetic records (rung-2/3 generator: first-letter field
        pools) — typed records; its class IS the field marker
  PNUM  synthetic positional notation (NEW S6 positive control, seeded:
        place-from-end determines a first-letter place-pool; most-
        significant first; places skipped with p=0.15 like omitted
        zeros; 5-9 places) — numeral family
  N4    self_citation control         — copy-hoax family
  N1    vms_word_shuffle              — no-structure reference row
        (reported, not a centroid)

PRE-REGISTERED DECISION RULE (F4-compliant):
  GATE: the four family centroids must separate — min pairwise centroid
    distance > 2 x the maximum within-corpus split RMS (spread), else
    gate_failed: no reading.
  CLASSIFICATION: B is assigned to the family of its nearest centroid
    (Euclidean in (r_pos, r_bi)) ONLY if d_nearest < 0.5 x d_second;
    otherwise NONE_OF_THE_ABOVE (explicit arm; the graveyard's F4).
  Currier A is reported observationally (no assignment).
OUTCOMES: gate_failed | family_language | family_records |
  family_positional | family_hoax | none_of_the_above.
Vocabulary discipline: 'family_records' means "B's line-class ordering
profile is nearest the synthetic-records reference and clearly so" —
it does NOT mean B is records, and nothing here reads a record.
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

SEED = 118
R_SPLITS = 10
CLASS_K = 12              # top first-glyph classes; rest -> OTHER
MARGIN_RATIO = 0.5        # d_nearest < ratio * d_second, else none-arm
GATE_SEP = 2.0            # min centroid dist > GATE_SEP * max split RMS
PNUM_LINES = 4600
PNUM_SKIP = 0.15
MIN_LINE_WORDS = 5
HOLDOUT_FRAC = 0.2
PSEUDO_FOLIO_LINES = 24
ALPHA = 0.5

CONTROLS = DATA_DIR / 'controls'
INTERIOR_BINS = ('p1', 'p2', 'm1', 'm2', 'm3', 'pL-1', 'pL')


# ── corpora ─────────────────────────────────────────────────────────
def load_control(name):
    p = CONTROLS / f'{name}.txt'
    return [ln.split() for ln in p.read_text(encoding='utf-8').splitlines()
            if len(ln.split()) >= MIN_LINE_WORDS]


def load_vms_hand(hand):
    lines, folios = [], []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        if not m or m.group(1) != hand:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if len(words) >= MIN_LINE_WORDS:
                lines.append(words)
                folios.append(fpath.stem)
    return lines, folios


def build_prec(rng):
    """Rung-2/3 record generator (first-letter field pools)."""
    vocab = sorted({w for line in load_control('latin_plain') for w in line})
    pools = [[], [], [], []]
    for w in vocab:
        c = w[0]
        pools[0 if c <= 'f' else 1 if c <= 'm' else 2 if c <= 's' else 3
              ].append(w)
    lines = []
    while len(lines) < 4600:
        row = [rng.choice(pools[0])]
        row += [rng.choice(pools[1]) for _ in range(rng.randint(1, 3))]
        if rng.random() < 0.5:
            row.append(rng.choice(pools[2]))
        row += [rng.choice(pools[3]) for _ in range(rng.randint(1, 4))]
        if len(row) >= MIN_LINE_WORDS:
            lines.append(row)
    return lines


def build_pnum(rng):
    """P-NUM (S6 positive control): positional notation as lines. Place
    k (from the END = units) draws from a first-letter place pool;
    most-significant place first; places skipped with PNUM_SKIP (like
    omitted zeros) -> length variation. 9 place pools over the Latin
    vocabulary's first letters."""
    vocab = sorted({w for line in load_control('latin_plain') for w in line})
    bands = 'abc def ghi jkl mno pqr stu vwx yz'.split()
    pools = [[w for w in vocab if w[0] in band] for band in bands]
    pools = [p for p in pools if p]   # drop empty bands (e.g. yz in Caesar)
    lines = []
    while len(lines) < PNUM_LINES:
        n_places = rng.randint(5, 9)
        row = []
        for place in range(n_places - 1, -1, -1):   # MSD first
            if rng.random() < PNUM_SKIP:
                continue
            row.append(rng.choice(pools[place % len(pools)]))
        if len(row) >= MIN_LINE_WORDS:
            lines.append(row)
    return lines


# ── class sequences + models ────────────────────────────────────────
def class_map(lines):
    freq = Counter(w[0] for line in lines for w in line)
    keep = {c for c, _ in freq.most_common(CLASS_K)}
    return keep


def to_classes(line, keep):
    return [(w[0] if w[0] in keep else '#') for w in line]


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
    if folios is None:
        folios = [i // PSEUDO_FOLIO_LINES for i in range(len(lines))]
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


def profile_split(lines, folios, keep, rng):
    """One split -> (r_pos, r_bi)."""
    train_idx, hold_idx = holdout_split(lines, folios, rng)
    uni = Counter()
    pos_c = {}
    bi_c = {}
    for i in train_idx:
        cls = to_classes(lines[i], keep)
        L = len(cls)
        prev = '^'
        for j, c in enumerate(cls):
            uni[c] += 1
            pos_c.setdefault(position_bin(j, L), Counter())[c] += 1
            bi_c.setdefault(prev, Counter())[c] += 1
            prev = c
    cats = sorted(set(uni) | {'#'})
    V = len(cats) + 1

    def logp(counter, val):
        tot = sum(counter.values())
        return math.log2((counter.get(val, 0) + ALPHA) / (tot + ALPHA * V))

    lu = lp = lb = 0.0
    n = 0
    for i in hold_idx:
        cls = to_classes(lines[i], keep)
        L = len(cls)
        prev = '^'
        for j, c in enumerate(cls):
            lu -= logp(uni, c)
            lp -= logp(pos_c.get(position_bin(j, L), Counter()), c)
            lb -= logp(bi_c.get(prev, Counter()), c)
            prev = c
            n += 1
    if n == 0 or lu == 0:
        return 0.0, 0.0
    return (lu - lp) / lu, (lu - lb) / lu


def profile(lines, folios):
    keep = class_map(lines)
    pts = [profile_split(lines, folios, keep, random.Random(SEED + 7 + r))
           for r in range(R_SPLITS)]
    r_pos = statistics.median(p[0] for p in pts)
    r_bi = statistics.median(p[1] for p in pts)
    cx = statistics.median(p[0] for p in pts)
    cy = statistics.median(p[1] for p in pts)
    rms = math.sqrt(statistics.mean((p[0] - cx) ** 2 + (p[1] - cy) ** 2
                                    for p in pts))
    return {'r_pos': round(r_pos, 4), 'r_bi': round(r_bi, 4),
            'split_rms': round(rms, 4), 'n_lines': len(lines),
            'n_classes': len(keep) + 1}


def dist(a, b):
    return math.sqrt((a['r_pos'] - b['r_pos']) ** 2
                     + (a['r_bi'] - b['r_bi']) ** 2)


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('LINE-CLASS FAMILY TEST (S5/S6) — which process orders B? (N4)')
    print('=' * 76)
    print(f'seed={SEED} splits={R_SPLITS} class_k={CLASS_K} margin='
          f'{MARGIN_RATIO} gate_sep={GATE_SEP}')

    b_lines, b_folios = load_vms_hand('B')
    a_lines, a_folios = load_vms_hand('A')
    corpora = {
        'P1_language': (load_control('latin_plain'), None),
        'PREC_records': (build_prec(random.Random(SEED)), None),
        'PNUM_positional': (build_pnum(random.Random(SEED + 1)), None),
        'N4_hoax': (load_control('self_citation'), None),
        'N1_shuffle_ref': (load_control('vms_word_shuffle'), None),
        'VMS_currier_B': (b_lines, b_folios),
        'VMS_currier_A': (a_lines, a_folios),
    }
    prof = {}
    for name, (lines, folios) in corpora.items():
        prof[name] = profile(lines, folios)
        p = prof[name]
        print(f'  {name:<16} r_pos {p["r_pos"]:+.4f}  r_bi {p["r_bi"]:+.4f}'
              f'  (rms {p["split_rms"]:.4f}, {p["n_lines"]} lines, '
              f'{p["n_classes"]} classes)')

    centroids = {'family_language': 'P1_language',
                 'family_records': 'PREC_records',
                 'family_positional': 'PNUM_positional',
                 'family_hoax': 'N4_hoax'}

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    cvals = {k: prof[v] for k, v in centroids.items()}
    pairs = [(k1, k2) for i, k1 in enumerate(cvals) for k2 in
             list(cvals)[i + 1:]]
    min_sep = min(dist(cvals[a], cvals[b]) for a, b in pairs)
    max_rms = max(prof[v]['split_rms'] for v in centroids.values())
    gate_ok = min_sep > GATE_SEP * max_rms
    print(f'    gate: min centroid separation {min_sep:.4f} vs '
          f'{GATE_SEP} x max spread {GATE_SEP * max_rms:.4f} -> '
          f'{"PASS" if gate_ok else "FAIL"}')
    b = prof['VMS_currier_B']
    dists = sorted(((dist(b, cvals[k]), k) for k in cvals))
    d1, fam1 = dists[0]
    d2, fam2 = dists[1]
    print(f'    B distances: ' + ', '.join(f'{k} {d:.4f}'
                                           for d, k in dists))
    if not gate_ok:
        verdict = 'gate_failed'
        print('    GATE FAILED: family centroids do not separate; no '
              'reading.')
    elif d1 < MARGIN_RATIO * d2:
        verdict = fam1
        print(f'    ASSIGNED {fam1.upper()} (d {d1:.4f} < '
              f'{MARGIN_RATIO} x {d2:.4f} to {fam2}): B\'s line-class '
              'ordering profile is nearest this calibrated family — a '
              'family-level reading only; nothing is decoded.')
    else:
        verdict = 'none_of_the_above'
        print(f'    NONE OF THE ABOVE (nearest {fam1} d {d1:.4f}, second '
              f'{fam2} d {d2:.4f} — margin rule not met): B\'s ordering '
              'profile matches no calibrated family clearly. The '
              'F4-mandated arm; an honest and informative outcome.')

    a = prof['VMS_currier_A']
    ad = sorted(((dist(a, cvals[k]), k) for k in cvals))
    print(f'    A (observational): nearest {ad[0][1]} d {ad[0][0]:.4f}, '
          f'second {ad[1][1]} d {ad[1][0]:.4f}')

    with open(result_path('line_class_family_test.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'r_splits': R_SPLITS,
                              'class_k': CLASS_K,
                              'margin_ratio': MARGIN_RATIO,
                              'gate_sep': GATE_SEP,
                              'pnum_lines': PNUM_LINES,
                              'pnum_skip': PNUM_SKIP,
                              'min_line_words': MIN_LINE_WORDS,
                              'holdout_frac': HOLDOUT_FRAC,
                              'pseudo_folio_lines': PSEUDO_FOLIO_LINES,
                              'alpha': ALPHA},
                   'profiles': prof,
                   'gate': {'min_separation': round(min_sep, 4),
                            'max_spread': round(max_rms, 4),
                            'pass': gate_ok},
                   'b_distances': [[round(d, 4), k] for d, k in dists],
                   'a_distances': [[round(d, 4), k] for d, k in ad],
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/line_class_family_test.json')


if __name__ == '__main__':
    main()
