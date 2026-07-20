#!/usr/bin/env python3
"""
Hapax-Clustering Discriminator Calibration (N9) — does "hapaxes cluster
→ language" actually discriminate language from non-language?

PROVENANCE (operator-directed, 2026-07-20): language_vs_cipher Part D
reads high hapax spatial clustering (burstiness B) as evidence of
natural language ("topic-specific"), low/uniform as cipher. N7 showed
the VMS clustering is real and locus-robust; the errata on that test
reframed what it discriminates. But the underlying INFERENCE — that
clustering is DIAGNOSTIC of language — was never calibrated against the
control battery, because Part D predates the charter. This instrument
does exactly that calibration, and it can abandon the inference.

Note on definition (addressing a review point): "hapax" here is the
STRICT once-occurring form, count == 1 over the collapsed vocabulary,
identical to Part D's `{w for w,c in vocab.items() if c == 1}`. It has
NOT been relaxed to "rare words". The question under test is not the
definition but whether the STATISTIC computed on strict hapaxes
separates language from non-language.

STATISTIC (Part D's, faithfully): per corpus, collapse each word
(gallows-strip + e-collapse, common.get_collapsed), hapax = collapsed
type with corpus count 1, burstiness B = (std - mean)/(std + mean) of
gaps between consecutive hapax LINE positions (Part D's exact formula
and its printed threshold: B > 0.1 = CLUSTERED). Also report hapax rate
(hapaxes / tokens) and TTR, since burstiness of a once-only set is
partly an arithmetic function of density — that confound is the point.

CORPORA (control battery, all size-matched, ~36-40k tokens):
  LANGUAGE positives: P1 latin_plain, P2 italian_plain.
  CIPHER positive:    P4 latin_verbose (language under a cipher — Part D
                      would predict this NON-clustered if its logic held).
  NON-LANGUAGE negatives: N3 grille_table (mechanical gibberish, no
                      topics), N4 self_citation (copy-modify hoax).
  Reference: VMS (vms_word_shuffle stands in for the manuscript's own
                      tokens; the live manuscript B was 0.591 in Part D).

PRE-REGISTERED ADJUDICATION (Part D's own threshold, B_CLUSTERED = 0.1):
  discriminator_valid   — the language positives (P1 AND P2) are
                          CLUSTERED (B > 0.1) AND the non-language
                          negatives (N3 AND N4) are NOT (B <= 0.1):
                          burstiness separates the classes; Part D's
                          inference is calibrated and stands.
  discriminator_broken  — a non-language negative (N3 or N4) is
                          CLUSTERED at or above the language positives'
                          level (B_neg >= min(B_P1, B_P2)): high hapax
                          burstiness is NOT diagnostic of language;
                          Part D's "clustered → language" inference is
                          ABANDONED (reframed to "clustering is real but
                          uninformative about language vs non-language";
                          ledger entry 14, which claims only that the
                          clustering is real and locus-robust — never
                          that it proves language — is unaffected and is
                          annotated with this result).
  inconclusive          — anything else (e.g. positives not clustered):
                          the statistic behaves unexpectedly on
                          controls; no inference either way.
Vocabulary discipline: this calibrates one legacy inference; it makes
no claim about what the manuscript is.
"""
import io
import json
import math
import statistics
import sys
from collections import Counter

from common import get_collapsed, result_path
from common.core import DATA_DIR

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 124                # no randomness; recorded for convention
B_CLUSTERED = 0.1         # Part D's printed threshold
MIN_LINE_WORDS = 2        # Part D's loader filter

CONTROLS = DATA_DIR / 'controls'
CORPORA = [
    ('P1_latin', 'latin_plain', 'language+'),
    ('P2_italian', 'italian_plain', 'language+'),
    ('P4_verbose_cipher', 'latin_verbose', 'cipher'),
    ('N3_grille', 'grille_table', 'nonlang-'),
    ('N4_self_citation', 'self_citation', 'nonlang-'),
    ('VMS_wordshuffle', 'vms_word_shuffle', 'reference'),
]


def load(name):
    p = CONTROLS / f'{name}.txt'
    lines = [ln.split() for ln in
             p.read_text(encoding='utf-8').splitlines()]
    return [[get_collapsed(w) for w in line] for line in lines
            if len(line) >= MIN_LINE_WORDS]


def burstiness(lines):
    vocab = Counter(w for line in lines for w in line)
    hap = {w for w, c in vocab.items() if c == 1}
    positions = [i for i, line in enumerate(lines)
                 for w in line if w in hap]
    if len(positions) < 10:
        return None
    gaps = [b - a for a, b in zip(positions, positions[1:])]
    mean = statistics.mean(gaps)
    std = statistics.pstdev(gaps)
    B = (std - mean) / (std + mean) if (std + mean) > 0 else 0.0
    ntok = sum(vocab.values())
    return {'B': round(B, 3), 'n_hapax': len(hap), 'n_types': len(vocab),
            'n_tokens': ntok, 'hapax_rate': round(len(hap) / ntok, 3),
            'ttr': round(len(vocab) / ntok, 3)}


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('HAPAX-CLUSTERING DISCRIMINATOR CALIBRATION (N9)')
    print('=' * 76)
    print(f'Part D threshold: B > {B_CLUSTERED} = CLUSTERED (= '
          '"language"). Question: does it separate language from '
          'non-language on the controls?')
    print('  (hapax = strict count==1 on the collapsed vocabulary, as '
          'in Part D — NOT relaxed to "rare words")')

    rows = {}
    for label, fname, cls in CORPORA:
        r = burstiness(load(fname))
        if r is None:
            rows[label] = {'class': cls, 'B': None,
                           'note': '<10 hapaxes — statistic undefined'}
            print(f'  {label:<18} [{cls:<9}] B    n/a  (<10 hapaxes)')
            continue
        r['class'] = cls
        rows[label] = r
        verdict = 'CLUSTERED' if r['B'] > B_CLUSTERED else 'uniform'
        print(f'  {label:<18} [{cls:<9}] B {r["B"]:+.3f} ({verdict})  '
              f'hapax_rate {r["hapax_rate"]:.3f}  ttr {r["ttr"]:.3f}  '
              f'({r["n_hapax"]} hapaxes / {r["n_tokens"]} tok)')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    bP1, bP2 = rows['P1_latin']['B'], rows['P2_italian']['B']
    negs = [rows[n]['B'] for n in ('N3_grille', 'N4_self_citation')
            if rows[n]['B'] is not None]
    pos_clustered = bP1 > B_CLUSTERED and bP2 > B_CLUSTERED
    neg_clustered = any(b > B_CLUSTERED for b in negs)
    neg_matches_pos = bool(negs) and max(negs) >= min(bP1, bP2)
    if not pos_clustered:
        verdict = 'inconclusive'
        print(f'    INCONCLUSIVE: language positives are not both '
              f'clustered (P1 {bP1:+.3f}, P2 {bP2:+.3f}) — the statistic '
              'behaves unexpectedly on controls; no inference.')
    elif neg_matches_pos:
        verdict = 'discriminator_broken'
        print(f'    DISCRIMINATOR BROKEN: a non-language negative '
              f'(N3 {bN3:+.3f}, N4 {bN4:+.3f}) clusters at or above the '
              f'language positives (min P1/P2 {min(bP1, bP2):+.3f}). '
              'High hapax burstiness is NOT diagnostic of language — '
              'Part D\'s "clustered → language" inference is ABANDONED. '
              '(Ledger entry 14 claims only that the VMS clustering is '
              'real and locus-robust, never that it proves language; it '
              'stands, annotated with this calibration.)')
    elif not neg_clustered:
        verdict = 'discriminator_valid'
        print(f'    DISCRIMINATOR VALID: language positives cluster '
              f'(P1 {bP1:+.3f}, P2 {bP2:+.3f}) and non-language '
              f'negatives do not (N3 {bN3:+.3f}, N4 {bN4:+.3f}) — '
              'burstiness separates the classes; Part D\'s inference is '
              'calibrated.')
    else:
        verdict = 'discriminator_weak'
        print(f'    DISCRIMINATOR WEAK: a negative clusters (N3 '
              f'{bN3:+.3f}, N4 {bN4:+.3f}) but below the positives — '
              'burstiness leans language-ward but is not clean; Part D\'s '
              'inference is downgraded to suggestive-only.')

    with open(result_path('hapax_clustering_calibration.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'b_clustered': B_CLUSTERED,
                              'min_line_words': MIN_LINE_WORDS},
                   'rows': rows, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/hapax_clustering_calibration.json')


if __name__ == '__main__':
    main()
