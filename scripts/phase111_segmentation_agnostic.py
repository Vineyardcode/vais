#!/usr/bin/env python3
"""
Phase 111 — Segmentation-Agnostic Modeling (strategy S4)

Assumption A2 says the manuscript's spaces are word boundaries. This
instrument deletes every space, learns a segmentation from raw character
statistics alone (greedy BPE, NUM_MERGES merges, learned per corpus,
never across line breaks), and then asks: do the learned unit boundaries
rediscover the original spaces?

Score: boundary F1 of BPE-unit boundaries against the corpus's original
space positions, minus the F1 of a density-matched random-boundary
baseline (RANDOM_TRIALS seeded trials). "Excess F1" > 0 means the spaces
are recoverable from character statistics alone — they carry segmental
signal, not just visual rhythm.

Pre-registered protocol and kill criteria (RESEARCH.md S4):
  - Controls first: P1 (Latin; spaces are real word boundaries — excess
    F1 must be clearly positive or the instrument is broken and dies),
    N2 (char-shuffled VMS; spaces are meaningless relative to content by
    construction — excess F1 must be ~0 or the instrument is broken).
  - Then VMS. KILL for A2: if VMS excess F1 is indistinguishable from N2's,
    spaces carry no segmental signal and every word-level statistic in the
    suite (Zipf, Heaps, TTR, morphology, slot grammar) is demoted to
    "statements about a visual layout convention".
DOF: NUM_MERGES and the BPE algorithm are fixed here before any VMS run;
no per-corpus tuning.
"""
import io
import json
import random
import sys
from collections import Counter

from common import result_path
from common.core import FOLIO_DIR, ivtff_clean_words
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

NUM_MERGES = 200
RANDOM_TRIALS = 20
RANDOM_SEED = 111
MIN_LINE_WORDS = 2

CONTROLS = FOLIO_DIR.parent / 'data' / 'controls'


def load_control(path):
    return [ln.split() for ln in path.read_text(encoding='utf-8').splitlines()
            if len(ln.split()) >= MIN_LINE_WORDS]


def load_vms():
    lines = []
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if len(words) >= MIN_LINE_WORDS:
                lines.append(words)
    return lines


def bpe_learn(lines, num_merges):
    """Greedy BPE on space-stripped lines (each line an independent
    symbol sequence). Returns the merge list."""
    seqs = [list(''.join(words)) for words in lines]
    merges = []
    for _ in range(num_merges):
        counts = Counter()
        for s in seqs:
            for i in range(len(s) - 1):
                counts[(s[i], s[i + 1])] += 1
        if not counts:
            break
        (a, b), n = counts.most_common(1)[0]
        if n < 2:
            break
        merges.append((a, b))
        ab = a + b
        for s in seqs:
            i = 0
            while i < len(s) - 1:
                if s[i] == a and s[i + 1] == b:
                    s[i:i + 2] = [ab]
                else:
                    i += 1
    return merges, seqs


def boundary_f1(lines, seqs):
    """F1 of BPE-unit boundaries vs original space positions, per line.
    Boundaries are indexed by character offset in the space-stripped line."""
    tp = fp = fn = 0
    for words, seq in zip(lines, seqs):
        true_b = set()
        off = 0
        for w in words[:-1]:
            off += len(w)
            true_b.add(off)
        pred_b = set()
        off = 0
        for unit in seq[:-1]:
            off += len(unit)
            pred_b.add(off)
        tp += len(true_b & pred_b)
        fp += len(pred_b - true_b)
        fn += len(true_b - pred_b)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return 2 * prec * rec / (prec + rec) if prec + rec else 0.0, prec, rec


def random_baseline(lines, seqs, rng):
    """Same boundary density, uniformly random positions."""
    tp = fp = fn = 0
    for words, seq in zip(lines, seqs):
        true_b = set()
        off = 0
        for w in words[:-1]:
            off += len(w)
            true_b.add(off)
        n_chars = sum(len(w) for w in words)
        k = min(len(seq) - 1, n_chars - 1) if n_chars > 1 else 0
        pred_b = set(rng.sample(range(1, n_chars), k)) if k > 0 else set()
        tp += len(true_b & pred_b)
        fp += len(pred_b - true_b)
        fn += len(true_b - pred_b)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return 2 * prec * rec / (prec + rec) if prec + rec else 0.0


def run_corpus(name, lines):
    merges, seqs = bpe_learn(lines, NUM_MERGES)
    f1, prec, rec = boundary_f1(lines, seqs)
    rng = random.Random(RANDOM_SEED)
    base = sum(random_baseline(lines, seqs, rng)
               for _ in range(RANDOM_TRIALS)) / RANDOM_TRIALS
    return {'f1': f1, 'precision': prec, 'recall': rec,
            'random_f1': base, 'excess_f1': f1 - base,
            'merges_learned': len(merges)}


def main():
    print("=" * 76)
    print("PHASE 111 — SEGMENTATION-AGNOSTIC MODELING (does BPE rediscover spaces?)")
    print("=" * 76)
    print(f"merges={NUM_MERGES}  random baseline: {RANDOM_TRIALS} trials, seed {RANDOM_SEED}\n")

    targets = [
        ('P1_latin_plain', load_control(CONTROLS / 'latin_plain.txt')),
        ('P2_italian_plain', load_control(CONTROLS / 'italian_plain.txt')),
        ('P4_latin_verbose', load_control(CONTROLS / 'latin_verbose.txt')),
        ('N2_vms_char_shuffle', load_control(CONTROLS / 'vms_char_shuffle.txt')),
        ('N3_grille', load_control(CONTROLS / 'grille_table.txt')),
        ('VMS_full', load_vms()),
    ]
    out = {}
    print(f"  {'corpus':<22}{'F1':>8}{'rand-F1':>9}{'excess':>9}")
    for name, lines in targets:
        r = run_corpus(name, lines)
        out[name] = r
        print(f"  {name:<22}{r['f1']:>8.3f}{r['random_f1']:>9.3f}{r['excess_f1']:>9.3f}")

    print("\n  ADJUDICATION (pre-registered):")
    p1x, n2x, vx = (out['P1_latin_plain']['excess_f1'],
                    out['N2_vms_char_shuffle']['excess_f1'],
                    out['VMS_full']['excess_f1'])
    if p1x < 0.1:
        print(f"    INSTRUMENT DEAD: P1 excess F1 {p1x:.3f} < 0.1 — BPE cannot "
              f"even rediscover Latin spaces; no conclusion possible.")
    elif n2x > p1x / 2:
        print(f"    INSTRUMENT DEAD: N2 excess F1 {n2x:.3f} not near zero — "
              f"baseline mis-specified; no conclusion possible.")
    else:
        print(f"    instrument OK (P1 {p1x:.3f} >> N2 {n2x:.3f}).")
        if vx <= n2x + 0.05:
            print(f"    A2 KILLED: VMS excess F1 {vx:.3f} indistinguishable from "
                  f"shuffled control — spaces carry no segmental signal; all "
                  f"word-level suite results demoted.")
        else:
            print(f"    A2 SURVIVES: VMS excess F1 {vx:.3f} > shuffle bar "
                  f"{n2x + 0.05:.3f} — spaces are recoverable from character "
                  f"statistics; word tokenization carries real signal "
                  f"(strength relative to Latin: {vx / p1x:.0%}).")

    with open(result_path('phase111_segmentation_agnostic.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(out, fh, indent=1)
    print("\n  -> results/phase111_segmentation_agnostic.json")


if __name__ == '__main__':
    main()
