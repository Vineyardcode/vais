#!/usr/bin/env python3
"""
Phase 110 — Alphabet-Space Search (strategy S1)

EVA is a transcription CONVENTION, not a discovery: it decides that 'ch'
is two letters and a gallows is one. Every character statistic the field
cites (h2 ~ 2 bits, rigid word grammar) is a statement about EVA strings
(assumption A1). This instrument searches the space of re-codings —
merge frequent bigrams into single units, unify confusable glyphs, drop
rare glyphs — asking: does ANY alphabet within reach make the corpus
statistically ordinary, and does the machinery know the difference
between decoding and destroying?

Search: beam search, breadth BEAM_WIDTH, depth SEARCH_DEPTH. Op space per
step (declared, fixed — DOF accounting):
  - merge one of the TOP_BIGRAMS most frequent symbol bigrams
  - one unification from UNIFY_PAIRS (paleographically confusable pairs)
  - drop-rare: delete symbols rarer than DROP_RARE_PCT
Alphabet size constrained to [ALPHABET_MIN, ALPHABET_MAX].

Objective (OBJECTIVE, UI-exposed):
  language_band = mean |z| distance of char-structural features
  (h1_char, h2_ratio, pos_predict, mean_wlen) from the positive-control
  language band (mean of P1 Latin & P2 Italian; scales = std over the
  9-control + VMS population). Lower = more language-like.

Pre-registered protocol and kill criteria (RESEARCH.md S1):
  1. POSITIVE CONTROL FIRST: run on P4 (latin_verbose). The search must
     substantially close P4's gap to the language band (it contains a
     planted verbose-cipher grouping that merging genuinely undoes).
  2. NEGATIVE CONTROL: run on N3 (grille). KILL: if the search closes
     N3's gap as fully as P4's, the objective cannot distinguish
     "recovering a real underlying alphabet" from "cosmetically
     normalizing table gibberish" -> the instrument dies, and no VMS
     result below may be interpreted.
  3. Only then: VMS (full, Currier A, Currier B separately — F8).
DOF budget: explored configurations are counted and reported; the op
space, beam, depth, objective, and controls order are fixed by this
docstring before any VMS run.
"""
import io
import json
import math
import sys
from collections import Counter

from common import result_path
from common.core import FOLIO_DIR, ivtff_clean_words
from common.fingerprint import char_entropy_stack, positional_predictability

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BEAM_WIDTH = 6
SEARCH_DEPTH = 10
TOP_BIGRAMS = 15
DROP_RARE_PCT = 0.1
ALPHABET_MIN = 15
ALPHABET_MAX = 60
OBJECTIVE = 'language_band'
UNIFY_PAIRS = ['tk', 'fp', 'ao', 'ei']   # paleographically confusable

CONTROLS = FOLIO_DIR.parent / 'data' / 'controls'
# private-use plane for merged symbols
_next_sym = [0xE000]


def load_lines(path):
    return [ln.split() for ln in path.read_text(encoding='utf-8').splitlines()
            if len(ln.split()) >= 2]


def load_vms():
    import re
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
            words = ivtff_clean_words(rest)
            if len(words) < 2:
                continue
            full.append(words)
            (a if lang == 'A' else b if lang == 'B' else []).append(words)
    return full, a, b


def char_features(tokens):
    _, h1, h2 = char_entropy_stack(tokens)
    return {
        'h1_char': h1,
        'h2_ratio': (h2 / h1) if h1 > 0 else float('nan'),
        'pos_predict': positional_predictability(tokens),
        'mean_wlen': sum(len(w) for w in tokens) / max(len(tokens), 1),
    }


_band_feats = ['h1_char', 'h2_ratio', 'pos_predict', 'mean_wlen']


def band_score(feats, band_mu, scales):
    zs = [abs(feats[f] - band_mu[f]) / scales[f] for f in _band_feats
          if not math.isnan(feats[f]) and scales[f] > 1e-12]
    return sum(zs) / len(zs) if zs else float('inf')


def apply_op(tokens, op):
    kind, arg = op
    if kind == 'merge':
        sym = chr(_next_sym[0])
        _next_sym[0] += 1
        return [w.replace(arg, sym) for w in tokens], sym
    if kind == 'unify':
        return [w.replace(arg[0], arg[1]) for w in tokens], None
    if kind == 'drop':
        return [w2 for w in tokens if (w2 := ''.join(c for c in w if c != arg))],\
               None
    raise ValueError(kind)


def candidate_ops(tokens):
    counts = Counter()
    for w in tokens:
        for i in range(len(w) - 1):
            counts[w[i:i + 2]] += 1
    ops = [('merge', bg) for bg, _ in counts.most_common(TOP_BIGRAMS)]
    alpha = Counter(c for w in tokens for c in w)
    total = sum(alpha.values())
    for pair in UNIFY_PAIRS:
        if pair[0] in alpha and pair[1] in alpha:
            ops.append(('unify', pair))
    for c, n in alpha.items():
        if n / total * 100 < DROP_RARE_PCT:
            ops.append(('drop', c))
    return ops


def alphabet_size(tokens):
    return len({c for w in tokens for c in w})


def beam_search(tokens, band_mu, scales, log_prefix=""):
    start = band_score(char_features(tokens), band_mu, scales)
    beam = [(start, [], tokens)]
    explored = 0
    for depth in range(SEARCH_DEPTH):
        pool = {}
        for score, ops, toks in beam:
            for op in candidate_ops(toks):
                new_toks, _ = apply_op(toks, op)
                a = alphabet_size(new_toks)
                if not (ALPHABET_MIN <= a <= ALPHABET_MAX):
                    continue
                explored += 1
                s = band_score(char_features(new_toks), band_mu, scales)
                key = tuple(sorted(map(str, ops + [op])))
                if key not in pool or pool[key][0] > s:
                    pool[key] = (s, ops + [op], new_toks)
        if not pool:
            break
        beam = sorted(pool.values(), key=lambda x: x[0])[:BEAM_WIDTH]
        if beam[0][0] >= min(b[0] for b in beam):
            pass
    best_s, best_ops, best_toks = min(beam, key=lambda x: x[0])
    if best_s > start:
        best_s, best_ops, best_toks = start, [], tokens
    return {'start': start, 'final': best_s, 'gain': start - best_s,
            'ops': [f"{k}:{a}" for k, a in best_ops],
            'alphabet': alphabet_size(best_toks), 'explored': explored,
            'features_final': char_features(best_toks)}


def main():
    p1 = [w for l in load_lines(CONTROLS / 'latin_plain.txt') for w in l]
    p2 = [w for l in load_lines(CONTROLS / 'italian_plain.txt') for w in l]
    f1, f2 = char_features(p1), char_features(p2)
    band_mu = {f: (f1[f] + f2[f]) / 2 for f in _band_feats}

    # scales from the control+VMS population (same convention as phase109)
    vms_full, vms_a, vms_b = load_vms()
    pop_corpora = [[w for l in load_lines(p) for w in l]
                   for p in sorted(CONTROLS.glob('*.txt'))]
    pop_corpora.append([w for l in vms_full for w in l])
    pop_feats = [char_features(t) for t in pop_corpora]
    scales = {}
    for f in _band_feats:
        vals = [pf[f] for pf in pop_feats if not math.isnan(pf[f])]
        mu = sum(vals) / len(vals)
        scales[f] = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5

    print("=" * 76)
    print("PHASE 110 — ALPHABET-SPACE SEARCH")
    print("=" * 76)
    print(f"objective={OBJECTIVE}  beam={BEAM_WIDTH} depth={SEARCH_DEPTH} "
          f"top_bigrams={TOP_BIGRAMS}  alphabet in [{ALPHABET_MIN},{ALPHABET_MAX}]")
    print(f"language band mu: " + "  ".join(f"{f}={band_mu[f]:.3f}" for f in _band_feats))

    runs = {}
    targets = [
        ('P4_latin_verbose', [w for l in load_lines(CONTROLS / 'latin_verbose.txt') for w in l]),
        ('N3_grille', [w for l in load_lines(CONTROLS / 'grille_table.txt') for w in l]),
        ('VMS_full', [w for l in vms_full for w in l]),
        ('VMS_currier_A', [w for l in vms_a for w in l]),
        ('VMS_currier_B', [w for l in vms_b for w in l]),
    ]
    for name, toks in targets:
        r = beam_search(toks, band_mu, scales)
        runs[name] = r
        print(f"\n  {name}: band-dist {r['start']:.3f} -> {r['final']:.3f}  "
              f"(gain {r['gain']:.3f}, {r['gain'] / max(r['start'], 1e-9):.0%} closed)  "
              f"alphabet {r['alphabet']}  explored {r['explored']:,}")
        print(f"    ops: {' '.join(r['ops']) if r['ops'] else '(none beneficial)'}")

    # pre-registered adjudication
    p4c = runs['P4_latin_verbose']['gain'] / max(runs['P4_latin_verbose']['start'], 1e-9)
    n3c = runs['N3_grille']['gain'] / max(runs['N3_grille']['start'], 1e-9)
    vc = runs['VMS_full']['gain'] / max(runs['VMS_full']['start'], 1e-9)
    print("\n  ADJUDICATION (pre-registered):")
    print(f"    positive control P4: {p4c:.0%} of gap closed "
          f"({'PASS' if p4c >= 0.5 else 'WEAK — interpret with caution'})")
    if n3c >= p4c:
        print(f"    KILL: N3 normalized as easily as P4 ({n3c:.0%} >= {p4c:.0%});"
              f" objective is non-discriminative. VMS rows below are VOID.")
    else:
        print(f"    N3 closed only {n3c:.0%} (< P4 {p4c:.0%}): objective "
              f"discriminates recovery from cosmetics. VMS result interpretable:")
        print(f"    VMS closed {vc:.0%} of its gap to the language band "
              f"(A: {runs['VMS_currier_A']['gain'] / max(runs['VMS_currier_A']['start'], 1e-9):.0%},"
              f" B: {runs['VMS_currier_B']['gain'] / max(runs['VMS_currier_B']['start'], 1e-9):.0%}).")

    with open(result_path('phase110_alphabet_space_search.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'band_mu': band_mu, 'scales': scales, 'runs': runs},
                  fh, indent=1)
    print("\n  -> results/phase110_alphabet_space_search.json")


if __name__ == '__main__':
    main()
