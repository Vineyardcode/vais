#!/usr/bin/env python3
"""
Phase 108 — Controls Foundry (research charter, Phase 0)

Builds the deterministic control battery into data/controls/ that every
research-program method must run BEFORE the manuscript:

POSITIVE (should look like language / be identified as its true class):
  P1 latin_plain      genuine Latin prose (Caesar, local corpus)
  P2 italian_plain    period vernacular (Dante, cached Gutenberg #1012)
  P3 latin_subst      P1 under monoalphabetic substitution
  P4 latin_verbose    P1 under a verbose cipher (letter -> glyph group,
                      Naibbe-style: deterministic seeded tables)
  P5 latin_abjad      P1 with vowels stripped (consonantal skeleton)

NEGATIVE (must NOT look like language / must be identified as generated):
  N1 vms_word_shuffle Voynich tokens, order shuffled corpus-wide
                      (line lengths preserved)
  N2 vms_char_shuffle Voynich characters shuffled within each line,
                      re-cut at the original word lengths
  N3 grille_table     Rugg-style pseudo-text from prefix/mid/suffix tables
                      fitted to VMS morphology, emitted by a sliding
                      grille walk
  N4 self_citation    Timm & Schinner-style copy-and-modify generation
                      seeded with genuine VMS lines

Every file: one text line per corpus line, space-separated tokens,
size-matched to ~TARGET_TOKENS. Seed pinned; output is byte-reproducible.
"""
import io
import random
import sys
from pathlib import Path

from common import (DATA_DIR, fetch_gutenberg, load_folio_lines,
                    load_reference_text, result_path)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SEED = 108
TARGET_TOKENS = 38000
LINE_LEN_MIN = 6
LINE_LEN_MAX = 10
SELF_CITATION_SEED_LINES = 12
SELF_CITATION_MODS = 9          # modifications applied per copied line
# (calibrated so N4's type/token ratio approaches the manuscript's ~0.21;
#  an under-mutated self-citation control would lose the tournament for
#  the wrong reason. Timm & Schinner's own generator is hapax-rich.)
GRILLE_JUMP_PROB = 0.18         # probability of a non-adjacent table jump

CONTROLS_DIR = DATA_DIR / "controls"

# EVA-ish glyph groups for the verbose cipher (deterministic table basis).
VERBOSE_GROUPS = ['ol', 'or', 'ar', 'al', 'ain', 'aiin', 'dy', 'edy', 'ey',
                  'chol', 'chor', 'che', 'she', 'qok', 'qot', 'ok', 'ot',
                  'da', 'sa', 'ke', 'te', 'so', 'do', 'y', 'o', 'd', 's']


def lines_to_text(lines):
    return "\n".join(" ".join(w for w in line) for line in lines) + "\n"


def chunk_words(words, rng):
    """Cut a flat word list into pseudo-lines of 6-10 words."""
    lines = []
    i = 0
    while i < len(words):
        n = rng.randint(LINE_LEN_MIN, LINE_LEN_MAX)
        lines.append(words[i:i + n])
        i += n
    return [l for l in lines if l]


def cap_tokens(lines, target):
    out, count = [], 0
    for l in lines:
        if count >= target:
            break
        out.append(l)
        count += len(l)
    return out


def build_positive(rng):
    latin = load_reference_text(DATA_DIR / 'latin_texts' / 'caesar.txt')
    italian_raw = fetch_gutenberg(1012)
    italian = [w for w in __import__('re').findall(
        r'[a-zàáâãäåæçèéêëìíîïòóôõöùúûü]+', italian_raw.lower())]

    p1 = cap_tokens(chunk_words(latin, rng), TARGET_TOKENS)
    p2 = cap_tokens(chunk_words(italian, rng), TARGET_TOKENS)

    # P3 monoalphabetic substitution over P1's alphabet
    alpha = sorted({c for line in p1 for w in line for c in w})
    perm = alpha[:]
    rng.shuffle(perm)
    sub = dict(zip(alpha, perm))
    p3 = [[''.join(sub[c] for c in w) for w in line] for line in p1]

    # P4 verbose cipher: each plaintext letter -> a glyph group (1:1 table,
    # deterministic under SEED). Groups concatenate inside a word.
    groups = VERBOSE_GROUPS[:]
    rng.shuffle(groups)
    table = {c: groups[i % len(groups)] for i, c in enumerate(alpha)}
    p4 = [[''.join(table[c] for c in w) for w in line] for line in p1]

    # P5 abjad: strip vowels, drop emptied words
    p5 = [[w2 for w in line if (w2 := ''.join(c for c in w if c not in 'aeiou'))]
          for line in p1]
    p5 = [l for l in p5 if l]
    return {'latin_plain': p1, 'italian_plain': p2, 'latin_subst': p3,
            'latin_verbose': p4, 'latin_abjad': p5}


def build_negative(rng):
    vms_lines = [words for _, _, words in load_folio_lines() if len(words) >= 2]

    # N1: global word shuffle, original line lengths
    all_words = [w for l in vms_lines for w in l]
    shuffled = all_words[:]
    rng.shuffle(shuffled)
    n1, i = [], 0
    for l in vms_lines:
        n1.append(shuffled[i:i + len(l)])
        i += len(l)

    # N2: per-line character shuffle, re-cut at original word lengths
    n2 = []
    for l in vms_lines:
        chars = [c for w in l for c in w]
        rng.shuffle(chars)
        out, j = [], 0
        for w in l:
            out.append(''.join(chars[j:j + len(w)]))
            j += len(w)
        n2.append(out)

    # N3: grille tables fitted to VMS morphology. Three columns sampled from
    # empirical word thirds; a "grille" walks the table with mostly-adjacent
    # cell moves, occasionally jumping (Rugg's sliding-grille flavour).
    def third_split(w):
        a = max(1, len(w) // 3)
        b = max(a + 1, 2 * len(w) // 3)
        return w[:a], w[a:b], w[b:]
    pres, mids, sufs = [], [], []
    for w in all_words:
        if len(w) >= 3:
            p, m, s = third_split(w)
            pres.append(p); mids.append(m); sufs.append(s)
    T = 40
    tp = [pres[rng.randrange(len(pres))] for _ in range(T)]
    tm = [mids[rng.randrange(len(mids))] for _ in range(T)]
    ts = [sufs[rng.randrange(len(sufs))] for _ in range(T)]
    n3, pos, made = [], 0, 0
    while made < TARGET_TOKENS:
        line = []
        for _ in range(rng.randint(LINE_LEN_MIN, LINE_LEN_MAX)):
            if rng.random() < GRILLE_JUMP_PROB:
                pos = rng.randrange(T)
            else:
                pos = (pos + 1) % T
            line.append(tp[pos] + tm[(pos + made) % T] + ts[pos])
            made += 1
        n3.append(line)

    # N4: self-citation. Seed with genuine lines, then repeatedly copy a
    # previous line and modify it. The mutation repertoire matches Timm &
    # Schinner's description: glyph substitution within confusion sets,
    # glyph insertion/deletion, word duplication-with-edit, word deletion.
    # Anything narrower produces a vocabulary too small to rival the
    # manuscript, and the tournament would kill the theory for an artifact
    # of this implementation rather than on its merits.
    confus = {'o': 'a', 'a': 'o', 'k': 't', 't': 'k', 'e': 'o',
              'd': 's', 's': 'd', 'l': 'r', 'r': 'l', 'y': 'o'}
    glyph_pool = sorted({c for w in all_words for c in w})

    def mutate_word(w):
        if not w:
            return w
        op = rng.random()
        j = rng.randrange(len(w))
        if op < 0.5:                                  # substitute
            return w[:j] + confus.get(w[j], w[j]) + w[j + 1:]
        if op < 0.75:                                 # insert
            return w[:j] + glyph_pool[rng.randrange(len(glyph_pool))] + w[j:]
        if len(w) > 2:                                # delete
            return w[:j] + w[j + 1:]
        return w

    n4 = [list(l) for l in vms_lines[:SELF_CITATION_SEED_LINES]]
    made = sum(len(l) for l in n4)
    while made < TARGET_TOKENS:
        src = list(n4[rng.randrange(len(n4))])
        for _ in range(SELF_CITATION_MODS):
            if not src:
                break
            op = rng.random()
            i = rng.randrange(len(src))
            if op < 0.6:
                src[i] = mutate_word(src[i])
            elif op < 0.85:
                src.insert(min(i + 1, len(src)), mutate_word(src[i]))
            elif len(src) > 3:
                src.pop(i)
        n4.append(src)
        made += len(src)
    return {'vms_word_shuffle': n1, 'vms_char_shuffle': n2,
            'grille_table': n3, 'self_citation': n4}


def main():
    rng = random.Random(SEED)
    CONTROLS_DIR.mkdir(parents=True, exist_ok=True)
    corpora = {}
    corpora.update(build_positive(rng))
    corpora.update(build_negative(rng))

    print("=" * 72)
    print("PHASE 108 — CONTROLS FOUNDRY (seed=%d)" % SEED)
    print("=" * 72)
    manifest = {}
    for name, lines in corpora.items():
        path = CONTROLS_DIR / f"{name}.txt"
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(lines_to_text(lines))
        toks = sum(len(l) for l in lines)
        types = len({w for l in lines for w in l})
        manifest[name] = {'tokens': toks, 'types': types, 'lines': len(lines)}
        print(f"  {name:<18} {toks:>7,} tokens  {types:>6,} types  "
              f"{len(lines):>5,} lines")
    import json
    with open(result_path('phase108_controls_manifest.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=1)
    print("\n  Written to data/controls/ + manifest to results/.")
    print("  Deterministic: rerunning reproduces byte-identical corpora.")


if __name__ == '__main__':
    main()
