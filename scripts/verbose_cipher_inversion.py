#!/usr/bin/env python3
"""
Verbose Cipher Inversion — prototype (strict model, calibrated on controls)

The research program's three converging signals (forgery_tournament: the
verbose control alone reproduces h2_ratio; space_free_segmentation: word
boundaries 2.7x more recoverable than Latin; forward_process_models: only
a ~13-char verbose scheme reproduces h_char) justify an actual inversion
attempt: IF each Voynich word is a concatenation of glyph-GROUPS, each
group encoding one plaintext letter, can we recover the groups and the
mapping?

ESCALATION LADDER (strict 1:1 mapping at every rung; homophones and
positional variants remain excluded):
  RUNG 1 — blind segmentation (below). OUTCOME (2026-07-16, logged):
    KILLED by the positive control. The blind BPE segmenter recovered
    only 13% of the planted P4 inventory and the known cipher decoded
    worse than grille gibberish. Diagnosis: cross-boundary glyph pairs
    are as frequent as within-group pairs, so frequency-only merging
    cannot see group boundaries. This kill is the pre-registered
    evidence that justifies rung 2.
  RUNG 2 — EM with language-model feedback: alternate (a) Viterbi
    re-segmentation of every word under the current inventory+mapping,
    (b) mapping hill-climb on the new segmentation, (c) inventory
    propose-and-test (swap low-usage groups for high-cohesion pool
    candidates). The same P4/noise-floor adjudication applies.
    OUTCOME (2026-07-16, logged): ALSO KILLED at prototype budget
    (EM_OUTER=4, EM_PROPOSALS=6, EM_RESTARTS=4): P4 recovery 48% (kill
    < 50%), P4 gap +0.115 vs noise floor +0.082 (margin < 0.1). The kill
    missed by 2 points, so the pre-registered escalation is COMPUTE, not
    model freedom. Red flag observed: Currier A scored +0.21 — "better
    than native Latin" — impossible as a decode; the free mapping
    memorized shared vocabulary between train and holdout LINES.
  RUNG 3 — max strength: identical strict 1:1 model and rung-1/2
    machinery, escalated on compute only, plus ONE structural fix:
    FOLIO-LEVEL holdout replaces line-level at every rung. Justification
    (logged 2026-07-17, before the run): same-corpus holdout lines share
    vocabulary with training lines, which is exactly the leak behind the
    rung-2 Currier A artifact; holding out whole folios (real folios for
    the VMS; contiguous PSEUDO_FOLIO_LINES-line pseudo-folios for the
    controls, which have no folio structure) closes it. The noise floor
    is re-measured at this rung under the same holdout, per the rung-2
    lesson that the floor rises with model power.
    OVERNIGHT (max-strength) PROFILE — pre-registered 2026-07-17, run as
    queue item N1 by tools/overnight.py, which splices these values over
    the prototype defaults below (the defaults stay small so the web UI
    and golden-reference path remain fast):
      EM_OUTER=32, EM_PROPOSALS=48, EM_RESTARTS=16, RESTARTS=64,
      TOP_LMS_RUNG2=3.
    (Raised from an initial 16/24/8/32 registration BEFORE any run at
    that budget: the default-budget run measures 93 s on an idle machine
    — the 700 s in the old golden meta was a contended capture — so the
    smaller profile would have finished in well under an hour, against
    an approved overnight window of hours.)
    INCIDENT LOG (2026-07-17, before the first completed rung-3 run):
    the first max-strength launch crashed 24 min in, exposing a latent
    rung-2 objective bug that only fires at high proposal counts: ll_of
    scored an EMPTY count table 0.0 = "perfect", so proposals that made
    every training word unparseable were accepted as improvements until
    the inventory collapsed (and an empty HOLDOUT would have faked
    gap = +native ~ +3.3 — a catastrophic false positive). Fixed before
    any completed rung-3 run: empty tables now score -1e9, total
    collapse returns an explicit degenerate row (gap_bits = -999,
    'degenerate': true). Model, criteria, and budgets unchanged;
    default-budget goldens verified byte-identical after the fix.
    INCIDENT #2 (same day, second launch): crash at the same min() via a
    different hole — the per-iteration usage snapshot goes stale as S
    mutates across 48 accepted proposals, so the swap-candidate filter
    can empty out while usage is non-empty. Fixed with an explicit
    fallback to all of S (fires only where the old code crashed; goldens
    again verified byte-identical). Numbers from the aborted second run
    already confirm the ll_of fix works: P1 rung-2 scores +0.012
    (~native, sane) and the rung-3 noise floor is visibly high (N2
    char-shuffle +0.384) — the pre-registered margin criterion exists
    for exactly this.
    Kill criteria unchanged: P4 planted-inventory recovery >= 50% AND
    P4's holdout gap beats the same-rung noise floor (best of N2/N3/N4)
    by >= 0.1 bits/sym; otherwise no VMS row is interpreted. Homophones
    and positional variants stay excluded unless P4 passes at strict
    settings first and the justification is logged HERE before
    escalating. Even then, a passing VMS row is only ever "consistent
    with a verbose cipher", never "decoded".

STRICT MODEL (rung 1 reference; rung 2 reuses 2-3):
  1. SEGMENTATION (unsupervised, blind to any plaintext): BPE-style
     merges learned on the corpus alone until the segment types covering
     COVERAGE_TARGET of tokens number <= TARGET_GROUPS. One segmentation
     per corpus, reused against every language model — the segmenter
     never sees plaintext feedback.
  2. MAPPING: the top (alphabet-1) segment types map 1:1 to plaintext
     letters (boundary maps to boundary). Words containing unmapped rare
     types are excluded and the exclusion rate reported. Mapping found by
     hill-climbing bigram log-likelihood under the candidate language
     model, RESTARTS random restarts, greedy pair swaps to convergence.
  3. SCORING: mapping optimized on TRAIN folios (1-HOLDOUT_FRAC of
     lines, held out in whole-folio units — see holdout_split), scored
     on HELD-OUT folios never seen by the optimizer. Metric = holdout
     gap: decoded bits/symbol minus the language's own native holdout
     bits/symbol under the same LM. 0 = indistinguishable from real text.

CANDIDATE PLAINTEXTS: Latin (Caesar) and Italian (Dante), each in three
variants: plain, abjad (vowels stripped), abbrev4 (suspension-truncated
to 4 chars) — 6 language models total.

PRE-REGISTERED PROTOCOL AND KILL CRITERIA (before any VMS run):
  A. POSITIVE CONTROL P4 (latin_verbose — we replay the exact planted
     table from controls_foundry, verified by re-encoding P1 and
     comparing to P4 byte-for-byte):
     - INSTRUMENT KILL: if the segmenter recovers < 50% of the planted
       group inventory, or the P4 holdout gap (vs latin/plain LM) is not
       clearly better than every negative control's best gap, the
       instrument cannot invert even a KNOWN verbose cipher at
       manuscript-like statistics -> no VMS row may be interpreted.
     - Also graded (not kill): % of correctly-recovered groups that the
       hill-climb maps to their TRUE letter.
  B. NEGATIVE CONTROLS N2 (char-shuffle), N3 (grille), N4 (self-cite):
     their best gaps across all 6 LMs define the NOISE FLOOR — what a
     free 21-symbol mapping extracts from meaningless text.
  C. VMS (full, Currier A, Currier B per constraint F8): reported as the
     position of its best gap relative to the P4/P1 band vs the noise
     floor. Vocabulary discipline: even a VMS gap beating all negatives
     with margin is "consistent with a verbose cipher", never "decoded".
DOF budget: TARGET_GROUPS, RESTARTS, and the 6 LMs are fixed here; the
segmenter is unsupervised; mapping DOF = one 21-ish-symbol bijection per
(corpus, LM) pair, identical for every corpus including the negatives.
"""
import io
import json
import math
import random
import re
import sys
from collections import Counter

from common import fetch_gutenberg, result_path
from common.core import DATA_DIR, FOLIO_DIR, ivtff_clean_words, load_reference_text

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 112
TARGET_GROUPS = 24        # segment types allowed to cover COVERAGE_TARGET
COVERAGE_TARGET = 0.95
MAX_MERGES = 400
RESTARTS = 12
HOLDOUT_FRAC = 0.2
PSEUDO_FOLIO_LINES = 24   # control corpora lack folios; hold out blocks of
                          # this many contiguous lines (VMS mean: 23.2)
MIN_LINE_WORDS = 2
LANGS = ['latin', 'italian']
VARIANTS = ['plain', 'abjad', 'abbrev4']
EM_OUTER = 4              # rung-2 EM iterations
EM_PROPOSALS = 6          # inventory swap proposals per iteration
EM_RESTARTS = 4           # hill-climb restarts inside the EM loop
POOL_MIN_FREQ = 50        # candidate n-gram pool threshold
POOL_MAX_LEN = 4
TOP_LMS_RUNG2 = 2         # non-P4 corpora: rung 2 runs on this many best LMs

CONTROLS = DATA_DIR / 'controls'
VOWELS = set('aeiou')


# ────────────────────────────────────────────────────────────────────
# corpora
# ────────────────────────────────────────────────────────────────────
def load_control(name):
    p = CONTROLS / f'{name}.txt'
    return [ln.split() for ln in p.read_text(encoding='utf-8').splitlines()
            if len(ln.split()) >= MIN_LINE_WORDS]


def load_vms_by_currier():
    """Returns {'full'|'A'|'B': (lines, folio_ids)} — folio ids run
    parallel to lines so holdout_split can hold out whole folios."""
    out = {'full': ([], []), 'A': ([], []), 'B': ([], [])}
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        lang = m.group(1) if m else None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if len(words) < MIN_LINE_WORDS:
                continue
            for key in (('full', lang) if lang in ('A', 'B') else ('full',)):
                out[key][0].append(words)
                out[key][1].append(fpath.stem)
    return out


def holdout_split(lines, folios, rng):
    """Folio-level holdout (rung-3 structural fix). Whole folios (VMS) or
    contiguous PSEUDO_FOLIO_LINES-line pseudo-folios (controls, folios=None)
    are held out until HOLDOUT_FRAC of the lines is reached. Returns
    (idx, cut): idx[:cut] = train line indices, idx[cut:] = holdout.

    Rationale: line-level holdout shares vocabulary between train and
    holdout lines of the same corpus, which let a free 21-symbol mapping
    memorize its way to +0.21 bits/sym on Currier A at rung 2 ("better
    than native Latin" — impossible as a decode). Held-out FOLIOS share
    far less local vocabulary, so generalization is tested for real."""
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
    return train + hold, len(train)


def language_corpus(lang):
    if lang == 'latin':
        words = load_reference_text(DATA_DIR / 'latin_texts' / 'caesar.txt')
        words = [re.sub(r'[^a-z]', '', w.lower()) for w in words]
    else:
        raw = fetch_gutenberg(1012)
        words = re.findall(r'[a-z]+', raw.lower())
    return [w for w in words if w]


def apply_variant(words, variant):
    if variant == 'plain':
        return words
    if variant == 'abjad':
        out = [''.join(c for c in w if c not in VOWELS) for w in words]
        return [w for w in out if w]
    if variant == 'abbrev4':
        return [w[:4] for w in words]
    raise ValueError(variant)


# ────────────────────────────────────────────────────────────────────
# language models: letter-bigram with boundary symbol ' '
# ────────────────────────────────────────────────────────────────────
def bigram_model(words, holdout_frac, rng):
    """Returns (logP dict, alphabet, native holdout bits/symbol)."""
    idx = list(range(len(words)))
    rng.shuffle(idx)
    cut = int(len(words) * (1 - holdout_frac))
    train = [words[i] for i in idx[:cut]]
    hold = [words[i] for i in idx[cut:]]

    def stream(ws):
        s = []
        for w in ws:
            s.extend(w)
            s.append(' ')
        return s

    tr = stream(train)
    counts = Counter(zip(tr, tr[1:]))
    marg = Counter(tr[:-1])
    alphabet = sorted(set(tr))
    V = len(alphabet)
    logp = {}
    for a in alphabet:
        for b in alphabet:
            logp[(a, b)] = math.log2((counts.get((a, b), 0) + 0.5)
                                     / (marg.get(a, 0) + 0.5 * V))
    ho = stream(hold)
    floor = math.log2(0.5 / (0.5 * V))
    pairs = list(zip(ho, ho[1:]))
    native = -sum(logp.get((x, y), floor) for x, y in pairs) / max(len(pairs), 1)
    return logp, alphabet, native


# ────────────────────────────────────────────────────────────────────
# unsupervised segmentation (blind BPE, per corpus)
# ────────────────────────────────────────────────────────────────────
def learn_segmentation(lines, target_groups, coverage_target, max_merges):
    seqs = [list(w) for line in lines for w in line]
    for _ in range(max_merges):
        freq = Counter(t for s in seqs for t in s)
        total = sum(freq.values())
        run, need = 0, None
        for i, (_, n) in enumerate(freq.most_common(), 1):
            run += n
            if run / total >= coverage_target:
                need = i
                break
        if need is not None and need <= target_groups:
            break
        pairs = Counter()
        for s in seqs:
            for i in range(len(s) - 1):
                pairs[(s[i], s[i + 1])] += 1
        if not pairs:
            break
        (a, b), n = pairs.most_common(1)[0]
        if n < 2:
            break
        ab = a + b
        for s in seqs:
            i = 0
            while i < len(s) - 1:
                if s[i] == a and s[i + 1] == b:
                    s[i:i + 2] = [ab]
                else:
                    i += 1
    # rebuild per-word segments
    out, k = [], 0
    for line in lines:
        row = []
        for _ in line:
            row.append(seqs[k])
            k += 1
        out.append(row)
    return out


# ────────────────────────────────────────────────────────────────────
# mapping search
# ────────────────────────────────────────────────────────────────────
def decode_counts(seg_lines, mapped_types):
    """Bigram counts over (type-or-None) stream incl. boundaries; words
    containing unmapped types are excluded whole."""
    C = Counter()
    excl = tot = 0
    for line in seg_lines:
        prev = ' '
        for word in line:
            tot += 1
            if any(t not in mapped_types for t in word):
                excl += 1
                prev = ' '
                continue
            for t in word:
                C[(prev, t)] += 1
                prev = t
            C[(prev, ' ')] += 1
            prev = ' '
    return C, (excl / max(tot, 1))


def ll_of(C, assign, logp, floor):
    s = n = 0
    for (a, b), c in C.items():
        pa = assign.get(a, ' ') if a != ' ' else ' '
        pb = assign.get(b, ' ') if b != ' ' else ' '
        s += c * logp.get((pa, pb), floor)
        n += c
    if n == 0:
        # An empty count table used to score 0.0 = "perfect" (all real
        # averages are negative), so EM proposals that made EVERY word
        # unparseable were accepted as improvements until the inventory
        # collapsed (observed at the rung-3 budget, 2026-07-17) — and an
        # empty HOLDOUT table would have faked gap = +native. Empty is
        # the worst possible score, not the best.
        return -1e9
    return s / n


def hill_climb(C, types, letters, logp, floor, rng):
    """Greedy pair-swap ascent with delta evaluation: a swap of the
    letters assigned to t1,t2 only changes C-entries touching t1 or t2."""
    touching = {t: [] for t in types}
    for (a, b), c in C.items():
        if a in touching:
            touching[a].append(((a, b), c))
        if b in touching and a != b:
            touching[b].append(((a, b), c))

    def local_ll(assign, t1, t2):
        seen = set()
        s = 0.0
        for key, c in touching[t1] + touching[t2]:
            if key in seen:
                continue
            seen.add(key)
            a, b = key
            pa = assign.get(a, ' ') if a != ' ' else ' '
            pb = assign.get(b, ' ') if b != ' ' else ' '
            s += c * logp.get((pa, pb), floor)
        return s

    best_assign, best_ll = None, -1e18
    for r in range(RESTARTS):
        letters_perm = letters[:]
        if r > 0:
            rng.shuffle(letters_perm)   # r == 0: frequency-rank alignment
        assign = dict(zip(types, letters_perm))
        improved = True
        while improved:
            improved = False
            for i in range(len(types)):
                for j in range(i + 1, len(types)):
                    t1, t2 = types[i], types[j]
                    before = local_ll(assign, t1, t2)
                    assign[t1], assign[t2] = assign[t2], assign[t1]
                    if local_ll(assign, t1, t2) > before + 1e-12:
                        improved = True
                    else:
                        assign[t1], assign[t2] = assign[t2], assign[t1]
        cur = ll_of(C, assign, logp, floor)
        if cur > best_ll:
            best_ll, best_assign = cur, dict(assign)
    return best_assign, best_ll


# ────────────────────────────────────────────────────────────────────
# rung 2: EM with language-model feedback (strict 1:1 held)
# ────────────────────────────────────────────────────────────────────
def build_pool(lines):
    """Candidate group pool: frequent n-grams scored by internal
    cohesion (average pairwise PMI), plus every single glyph."""
    char_freq = Counter(c for line in lines for w in line for c in w)
    total = sum(char_freq.values())
    ngram_freq = Counter()
    for line in lines:
        for w in line:
            for n in range(2, POOL_MAX_LEN + 1):
                for i in range(len(w) - n + 1):
                    ngram_freq[w[i:i + n]] += 1
    pool = {}
    for g, f in ngram_freq.items():
        if f < POOL_MIN_FREQ:
            continue
        exp = total * math.prod(char_freq[c] / total for c in g)
        pool[g] = (f, math.log2(f / exp) / (len(g) - 1))   # (freq, cohesion)
    singles = {c: (f, 0.0) for c, f in char_freq.items()}
    return pool, singles


def viterbi_segment(word, groups_by_first, assign, logp, floor, prev=' '):
    """Best segmentation of `word` into inventory groups under the LM.
    Returns (score, segments) or None if unparseable."""
    n = len(word)
    # dp[i] = (score, last_letter, backpointer)
    dp = [None] * (n + 1)
    dp[0] = (0.0, prev, None, None)
    for i in range(n):
        if dp[i] is None:
            continue
        sc, last, _, _ = dp[i]
        for g in groups_by_first.get(word[i], ()):
            j = i + len(g)
            if j > n or word[i:j] != g:
                continue
            step = sc + logp.get((last, assign[g]), floor)
            if dp[j] is None or step > dp[j][0]:
                dp[j] = (step, assign[g], i, g)
    if dp[n] is None:
        return None
    segs = []
    j = n
    while j > 0:
        _, _, i, g = dp[j]
        segs.append(g)
        j = i
    return dp[n][0], segs[::-1]


def em_invert(lines, idx, cut, lm, seed):
    """Rung-2 EM. Returns result dict (same shape as rung 1 entries)."""
    logp, alphabet, native = lm
    letters = [a for a in alphabet if a != ' ']
    L = len(letters)
    floor = math.log2(0.5 / (0.5 * len(alphabet)))
    rng = random.Random(seed)

    pool, singles = build_pool(lines)
    # init inventory: high-cohesion multigrams (70%), frequent singles (rest)
    multi = sorted(pool, key=lambda g: -(pool[g][0] * max(pool[g][1], 0.0)))
    S = list(dict.fromkeys(multi[:int(L * 0.7)]))
    for c, _ in sorted(singles.items(), key=lambda kv: -kv[1][0]):
        if len(S) >= L:
            break
        if c not in S:
            S.append(c)

    train_lines = [lines[i] for i in idx[:cut]]
    hold_lines = [lines[i] for i in idx[cut:]]

    def segment_all(ws_lines, S_, assign_):
        gbf = {}
        for g in S_:
            gbf.setdefault(g[0], []).append(g)
        for v in gbf.values():
            v.sort(key=len, reverse=True)
        C = Counter()
        excl = tot = 0
        for line in ws_lines:
            prev = ' '
            for w in line:
                tot += 1
                r = viterbi_segment(w, gbf, assign_, logp, floor, prev)
                if r is None:
                    excl += 1
                    prev = ' '
                    continue
                for g in r[1]:
                    C[(prev, g)] += 1
                    prev = g
                C[(prev, ' ')] += 1
                prev = ' '
        return C, excl / max(tot, 1)

    global RESTARTS
    saved_restarts = RESTARTS
    RESTARTS = EM_RESTARTS
    try:
        assign = dict(zip(S, letters))
        best_ll = -1e18
        degenerate = False
        for it in range(EM_OUTER):
            C_tr, _ = segment_all(train_lines, S, assign)
            assign, ll = hill_climb(C_tr, S, letters, logp, floor, rng)
            # inventory proposals: swap lowest-usage member for best outsider
            usage = Counter()
            for (a, b), c in C_tr.items():
                if b != ' ':
                    usage[b] += c
            if not usage:
                # total training-coverage collapse: no train word parses
                # under the current inventory. Unreachable now that ll_of
                # rejects empty tables, but the 2026-07-17 crash proved
                # this corner exists — stop and flag rather than min()
                # over an empty candidate set.
                degenerate = True
                break
            outsiders = [g for g in multi if g not in assign][:EM_PROPOSALS]
            for u in outsiders:
                # usage is a per-outer-iteration snapshot, but S mutates
                # with each accepted proposal; at high EM_PROPOSALS the
                # eligibility filter (singles, or snapshot-used) can go
                # empty while S is fine (2026-07-17 crash #2). Fall back
                # to all of S: a stale-usage-0 member is a legitimate
                # swap-out candidate.
                cand = [g for g in S if len(g) == 1 or usage[g] > 0]
                worst = min(cand or S, key=lambda g: usage[g])
                S2 = [u if g == worst else g for g in S]
                assign2 = dict(assign)
                assign2[u] = assign2.pop(worst)
                C2, _ = segment_all(train_lines, S2, assign2)
                assign2, ll2 = hill_climb(C2, S2, letters, logp, floor, rng)
                if ll2 > ll + 1e-9:
                    S, assign, ll, C_tr = S2, assign2, ll2, C2
            if ll <= best_ll + 1e-9:
                break
            best_ll = ll
        C_ho, excl_ho = segment_all(hold_lines, S, assign)
        if degenerate or not C_ho:
            # no scoreable holdout content: report an explicit degenerate
            # row (sentinel gap far below any real value) instead of
            # letting an empty table score as a perfect decode
            return {'gap_bits': -999.0, 'holdout_bits': None,
                    'native_bits': round(native, 4),
                    'excluded_words': round(excl_ho, 4),
                    'degenerate': True,
                    'inventory': sorted(S, key=len)}, assign
        ho_ll = ll_of(C_ho, assign, logp, floor)
        return {'gap_bits': round(native - (-ho_ll), 4),
                'holdout_bits': round(-ho_ll, 4),
                'native_bits': round(native, 4),
                'excluded_words': round(excl_ho, 4),
                'inventory': sorted(S, key=len)}, assign
    finally:
        RESTARTS = saved_restarts


# ────────────────────────────────────────────────────────────────────
# planted-table replay (positive-control ground truth)
# ────────────────────────────────────────────────────────────────────
def replay_planted_table():
    """Re-derive controls_foundry's P4 letter->group table by replaying
    its exact rng sequence, then verify against the control files.

    The constants and helpers below are LOCAL COPIES of controls_foundry's
    (importing that module re-wraps sys.stdout and closes ours). Any drift
    between the copies and the foundry is caught by the re-encoding
    verification at the end — a mismatch aborts the run.
    """
    F_SEED, F_TARGET, F_MIN, F_MAX = 108, 38000, 6, 10
    F_GROUPS = ['ol', 'or', 'ar', 'al', 'ain', 'aiin', 'dy', 'edy', 'ey',
                'chol', 'chor', 'che', 'she', 'qok', 'qot', 'ok', 'ot',
                'da', 'sa', 'ke', 'te', 'so', 'do', 'y', 'o', 'd', 's']

    def chunk_words(words, rng):
        lines, i = [], 0
        while i < len(words):
            n = rng.randint(F_MIN, F_MAX)
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

    rng = random.Random(F_SEED)
    latin = load_reference_text(DATA_DIR / 'latin_texts' / 'caesar.txt')
    italian_raw = fetch_gutenberg(1012)
    italian = re.findall(r'[a-zàáâãäåæçèéêëìíîïòóôõöùúûü]+', italian_raw.lower())
    p1 = cap_tokens(chunk_words(latin, rng), F_TARGET)
    cap_tokens(chunk_words(italian, rng), F_TARGET)
    alpha = sorted({c for line in p1 for w in line for c in w})
    perm = alpha[:]
    rng.shuffle(perm)                         # consumes P3's shuffle
    groups = F_GROUPS[:]
    rng.shuffle(groups)
    table = {c: groups[i % len(groups)] for i, c in enumerate(alpha)}
    # verification: re-encode P1 -> must equal P4 exactly
    p1_file = load_control('latin_plain')
    p4_file = load_control('latin_verbose')
    for lp, lv in list(zip(p1_file, p4_file))[:200]:
        for wp, wv in zip(lp, lv):
            if ''.join(table[c] for c in wp) != wv:
                raise RuntimeError('planted-table replay FAILED verification')
    return table


# ────────────────────────────────────────────────────────────────────
def main():
    rng = random.Random(SEED)
    print('=' * 76)
    print('VERBOSE CIPHER INVERSION — strict 1:1 ladder (folio-level holdout)')
    print('=' * 76)
    print(f'seed={SEED} target_groups={TARGET_GROUPS} restarts={RESTARTS} '
          f'holdout={HOLDOUT_FRAC} (whole folios; controls: pseudo-folios '
          f'of {PSEUDO_FOLIO_LINES} lines)')
    print(f'EM budget: outer={EM_OUTER} proposals={EM_PROPOSALS} '
          f'em_restarts={EM_RESTARTS} top_lms_rung2={TOP_LMS_RUNG2}')

    # language models
    lms = {}
    for lang in LANGS:
        base = language_corpus(lang)
        for var in VARIANTS:
            words = apply_variant(base, var)
            logp, alphabet, native = bigram_model(words, HOLDOUT_FRAC,
                                                  random.Random(SEED + 1))
            lms[f'{lang}/{var}'] = (logp, alphabet, native)
            print(f'  LM {lang}/{var:<8} alphabet={len(alphabet):>2} '
                  f'native holdout={native:.3f} bits/sym')

    table = replay_planted_table()
    planted_groups = set(table.values())
    inv_table = {}
    for c, g in table.items():
        inv_table.setdefault(g, c)
    print(f'\n  planted P4 table replayed and VERIFIED '
          f'({len(planted_groups)} groups)')

    vms = load_vms_by_currier()
    corpora = [
        ('P4_latin_verbose', load_control('latin_verbose'), None),
        ('P1_latin_plain', load_control('latin_plain'), None),
        ('N2_char_shuffle', load_control('vms_char_shuffle'), None),
        ('N3_grille', load_control('grille_table'), None),
        ('N4_self_citation', load_control('self_citation'), None),
        ('VMS_full',) + vms['full'],
        ('VMS_currier_A',) + vms['A'],
        ('VMS_currier_B',) + vms['B'],
    ]

    # holdout split on whole FOLIOS (charter rule 3; rung-3 structural fix)
    # — computed once per corpus and shared by both rungs.
    splits = {cname: holdout_split(lines, folios, random.Random(SEED + 7))
              for cname, lines, folios in corpora}

    results = {}
    for cname, lines, folios in corpora:
        idx, cut = splits[cname]

        seg_all = learn_segmentation(lines, TARGET_GROUPS, COVERAGE_TARGET,
                                     MAX_MERGES)
        seg_train = [seg_all[i] for i in idx[:cut]]
        seg_hold = [seg_all[i] for i in idx[cut:]]
        type_freq = Counter(t for line in seg_all for w in line for t in w)

        row = {'n_lines': len(lines), 'n_types': len(type_freq),
               'n_holdout_lines': len(idx) - cut}
        # inventory recovery grading (positive control only)
        if cname == 'P4_latin_verbose':
            top = {t for t, _ in type_freq.most_common(TARGET_GROUPS)}
            rec = len(top & planted_groups) / len(planted_groups)
            row['inventory_recovery'] = rec
            print(f'\n  {cname}: segmenter recovered '
                  f'{rec:.0%} of the planted group inventory')

        best = None
        for lm_name, (logp, alphabet, native) in lms.items():
            letters = [a for a in alphabet if a != ' ']
            types = [t for t, _ in type_freq.most_common(len(letters))]
            C_tr, excl_tr = decode_counts(seg_train, set(types))
            C_ho, excl_ho = decode_counts(seg_hold, set(types))
            floor = math.log2(0.5 / (0.5 * len(alphabet)))
            assign, _ = hill_climb(C_tr, types, letters, logp, floor,
                                   random.Random(SEED + 13))
            ho_ll = ll_of(C_ho, assign, logp, floor)
            gap = native - (-ho_ll)      # negative gap: worse than native
            entry = {'gap_bits': round(-(-ho_ll) + native, 4),
                     'holdout_bits': round(-ho_ll, 4),
                     'native_bits': round(native, 4),
                     'excluded_words': round(excl_ho, 4)}
            if cname == 'P4_latin_verbose' and lm_name == 'latin/plain':
                correct = sum(1 for t, l in assign.items()
                              if inv_table.get(t) == l)
                entry['mapping_accuracy'] = round(correct / len(assign), 4)
            row[lm_name] = entry
            if best is None or entry['gap_bits'] > best[1]:
                best = (lm_name, entry['gap_bits'])
        row['best_lm'], row['best_gap'] = best
        results[cname] = row
        print(f'  {cname:<18} best LM {best[0]:<15} '
              f'holdout gap {best[1]:+.3f} bits/sym  '
              f'(0 = native text; more negative = less language-like)')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    p4 = results['P4_latin_verbose']
    neg_best = max(results[n]['best_gap']
                   for n in ('N2_char_shuffle', 'N3_grille', 'N4_self_citation'))
    rec = p4.get('inventory_recovery', 0.0)
    acc = p4.get('latin/plain', {}).get('mapping_accuracy', 0.0)
    print(f'    P4 inventory recovery: {rec:.0%} (kill < 50%)')
    print(f'    P4 mapping accuracy on latin/plain: {acc:.0%}')
    print(f'    P4 best gap {p4["best_gap"]:+.3f} vs noise floor '
          f'{neg_best:+.3f} (best negative)')
    instrument_ok = rec >= 0.5 and p4['best_gap'] - neg_best >= 0.1
    if not instrument_ok:
        print('    RUNG 1 KILLED: blind segmentation cannot invert a known '
              'verbose cipher. Escalating to rung 2 (EM with LM feedback) '
              'per the pre-registered ladder.')
    else:
        print('    rung 1 OK: known cipher inverted above the noise floor.')

    # ── RUNG 2: EM with language-model feedback ─────────────────────
    results2 = {}
    lm_items = list(lms.items())
    for cname, lines, folios in corpora:
        idx, cut = splits[cname]        # same folio-level split as rung 1
        # P4 gets all LMs (it must FIND latin/plain); others: top rung-1 LMs
        if cname == 'P4_latin_verbose':
            todo = lm_items
        else:
            ranked = sorted(lm_items,
                            key=lambda kv: -results[cname][kv[0]]['gap_bits'])
            todo = ranked[:TOP_LMS_RUNG2]
        row = {}
        best = None
        for lm_name, lm in todo:
            entry, assign = em_invert(lines, idx, cut, lm, SEED + 29)
            if cname == 'P4_latin_verbose':
                inv_set = set(entry['inventory'])
                entry['inventory_recovery'] = round(
                    len(inv_set & planted_groups) / len(planted_groups), 4)
                if lm_name == 'latin/plain':
                    correct = sum(1 for t, l in assign.items()
                                  if inv_table.get(t) == l)
                    entry['mapping_accuracy'] = round(correct / len(assign), 4)
            row[lm_name] = entry
            if best is None or entry['gap_bits'] > best[1]:
                best = (lm_name, entry['gap_bits'])
        row['best_lm'], row['best_gap'] = best
        results2[cname] = row
        extra = ''
        if cname == 'P4_latin_verbose':
            lp = row.get('latin/plain', {})
            extra = (f"  [recovery {lp.get('inventory_recovery', 0):.0%}, "
                     f"mapping {lp.get('mapping_accuracy', 0):.0%} on latin/plain]")
        print(f'  RUNG2 {cname:<18} best LM {best[0]:<15} '
              f'holdout gap {best[1]:+.3f}{extra}')

    print('\n  RUNG 2 ADJUDICATION (pre-registered):')
    p4b = results2['P4_latin_verbose']
    neg2 = max(results2[n]['best_gap']
               for n in ('N2_char_shuffle', 'N3_grille', 'N4_self_citation'))
    lp = p4b.get('latin/plain', {})
    rec2 = lp.get('inventory_recovery', 0.0)
    acc2 = lp.get('mapping_accuracy', 0.0)
    print(f'    P4 inventory recovery: {rec2:.0%} (kill < 50%), '
          f'mapping accuracy: {acc2:.0%}')
    print(f'    P4 best gap {p4b["best_gap"]:+.3f} '
          f'({p4b["best_lm"]}) vs noise floor {neg2:+.3f}')
    ok2 = rec2 >= 0.5 and p4b['best_gap'] - neg2 >= 0.1
    if not ok2:
        print('    RUNG 2 KILLED at this budget (see EM budget line above): '
              'EM cannot invert the known cipher clearly better than noise. '
              'VMS rows NOT interpretable; the pre-registered escalation '
              'policy (docstring ladder) is compute first, never model '
              'freedom.')
    else:
        print('    rung 2 instrument OK.')
        for v in ('VMS_full', 'VMS_currier_A', 'VMS_currier_B'):
            g = results2[v]['best_gap']
            verdict = ('above the noise floor -> CONSISTENT WITH a verbose '
                       'cipher (NOT a decode)' if g - neg2 >= 0.1 else
                       'within the noise floor -> nothing beyond free-mapping '
                       'noise at this rung')
            print(f'    {v}: best gap {g:+.3f} ({results2[v]["best_lm"]}) — '
                  f'{verdict}')

    with open(result_path('verbose_cipher_inversion.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'target_groups': TARGET_GROUPS,
                              'restarts': RESTARTS, 'em_outer': EM_OUTER,
                              'em_proposals': EM_PROPOSALS,
                              'em_restarts': EM_RESTARTS,
                              'top_lms_rung2': TOP_LMS_RUNG2,
                              'holdout_frac': HOLDOUT_FRAC,
                              'holdout_unit': 'folio',
                              'pseudo_folio_lines': PSEUDO_FOLIO_LINES},
                   'rung1': {'noise_floor': neg_best, 'results': results},
                   'rung2': {'noise_floor': neg2, 'results': results2}},
                  fh, indent=1)
    print('\n  -> results/verbose_cipher_inversion.json')


if __name__ == '__main__':
    main()
