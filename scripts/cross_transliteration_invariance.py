#!/usr/bin/env python3
"""
Cross-Transliteration Invariance Audit (portfolio S9) — is the evidence
about the manuscript, or about one team's reading of it?

Assumption A1 (the transliteration IS the text) is inherited by 100% of
this suite's results (RESEARCH.md Phase 1). This audit recomputes (a) a
compact headline fingerprint and (b) the live S7 Currier-B ordinal
finding on four independent transliterations alongside the suite's
canonical ZL corpus:

  CD  Currier / D'Imperio        data/translit/CD2a-n.txt (IVTFF 2.0)
  GC  Glen Claston v101          data/translit/GC2a-n.txt (IVTFF 2.0)
  FG  FSG (Friedman Study Group) data/translit/FG2a-n.txt (IVTFF 2.0)
  IT  Takeshi Takahashi          data/translit/IT2a-n.txt (IVTFF 2.0)
  (source: voynich.nu/data, fetched 2026-07-18, courtesy R. Zandbergen)

Each file is parsed in ITS OWN alphabet (case-sensitive; @nnn; extended
glyphs mapped to unique private-use characters; words containing
illegibility marks ?%*{} dropped whole, per the T1 policy). Per-page
$L=A/B metadata is read from each file's own headers.

PART 1 — headline fingerprint spread (report-out; S9 cannot be killed,
only starved): six alphabet-computable features per transliteration —
h2_ratio, ttr@5k, zipf_alpha, mean word length, line_init_jsd,
line_final_jsd (compact local definitions; the full 17-feature
fingerprint contains EVA-specific features). A feature is flagged
TRANSLITERATION-SENSITIVE if any alternative deviates from ZL by more
than REL_DEV_FLAG (relative). Flagged features are demoted to
"conditional on the reading" in any future claim.

PART 2 — S7-B ordinal invariance (the live question; pre-registered):
the rung-3 decisive battery (10-split median interior positional gain
vs N_NULLS within-line shuffles, beat ALL nulls AND margin >=
EFFECT_FLOOR) is run on the Currier-B lines of every transliteration,
with the ALPHABET-AGNOSTIC feature set (len bucket, first char, last
char — 'gallows' is EVA-specific and dropped).
  GATE: ZL itself must PASS with the reduced feature set (else the
    audit is inconclusive: the dropped feature was load-bearing).
  USABILITY: a transliteration is usable if it yields >= MIN_B_LINES
    Currier-B lines of >= MIN_LINE_WORDS words.
  OUTCOMES (pre-registered 2026-07-18, before first execution):
    gate_failed      — reduced-feature ZL battery fails; no conclusion.
    robust           — every usable alternative PASSES: the S7-B
                       ordinal finding is transliteration-robust
                       (supports the quarantined rung-3 entry).
    partial          — some usable alternatives pass, some fail: the
                       finding is sensitive to reading choices; flagged,
                       listed, and the failing readings named. No
                       demotion, mandatory investigation.
    artifact_suspect — ZL passes but EVERY usable alternative fails:
                       the rung-3 finding is DEMOTED to
                       artifact-suspect (a property of the ZL reading
                       until shown otherwise).
Currier-A rows are reported observationally (no nulls, no adjudication).
Vocabulary discipline: 'robust' upgrades nothing by itself — it removes
one named objection to a still-quarantined SUGGESTIVE finding.
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
from common.core import DATA_DIR, FOLIO_DIR, ivtff_clean_words, zipf_alpha

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 116
R_SPLITS = 10
N_NULLS = 20
EFFECT_FLOOR = 0.05
REL_DEV_FLAG = 0.20       # part-1 sensitivity flag threshold (relative)
MIN_B_LINES = 500         # usability bar for part 2
MIN_LINE_WORDS = 5
HOLDOUT_FRAC = 0.2
ALPHA = 0.5

TRANSLIT_DIR = DATA_DIR / 'translit'
FILES = {'CD': 'CD2a-n.txt', 'GC': 'GC2a-n.txt',
         'FG': 'FG2a-n.txt', 'IT': 'IT2a-n.txt'}
FEATURE_NAMES = ('len', 'first', 'last')   # alphabet-agnostic (no gallows)
INTERIOR = {'m1', 'm2', 'm3'}


# ────────────────────────────────────────────────────────────────────
# generic IVTFF parsing (file's own alphabet preserved)
# ────────────────────────────────────────────────────────────────────
def clean_generic(rest):
    rest = re.sub(r'@(\d+);',
                  lambda m: chr(0xE000 + int(m.group(1)) % 4000), rest)
    rest = re.sub(r'<![^>]*>', '.', rest)
    rest = re.sub(r'<[^>]*>', '.', rest)
    rest = re.sub(r'\[([^:\[\]]*)(?::[^\[\]]*)+\]', r'\1', rest)
    rest = rest.replace('!', '')
    words = []
    for w in re.split(r'[.\s,;]+', rest):
        w = w.strip()
        if not w:
            continue
        if any(c in w for c in '?%*{}'):
            continue          # illegible: drop whole, never truncate (T1)
        words.append(w)
    return words


def load_ivtff_file(path):
    """(lines, folios, lang_by_folio) from a single IVTFF file."""
    lang_by_folio = {}
    lines, folios = [], []
    for raw in path.read_text(encoding='utf-8',
                              errors='replace').splitlines():
        raw = raw.strip()
        if not raw or raw.startswith('#'):
            continue
        m = re.match(r'<(f[^.>]+)>\s*<!(.*)>\s*$', raw)
        if m:
            lm = re.search(r'\$L=([AB])', m.group(2))
            if lm:
                lang_by_folio[m.group(1)] = lm.group(1)
            continue
        m = re.match(r'<(f[^.>]+)\.[^>]*>\s*(.*)$', raw)
        if not m:
            continue
        words = clean_generic(m.group(2))
        if len(words) >= MIN_LINE_WORDS:
            lines.append(words)
            folios.append(m.group(1))
    return lines, folios, lang_by_folio


def load_zl():
    """The suite's canonical ZL corpus (folios/, markup-clean loader)."""
    lines, folios, lang_by_folio = [], [], {}
    for fpath in sorted(FOLIO_DIR.glob('*.txt')):
        text = fpath.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'\$L=([AB])', text)
        if m:
            lang_by_folio[fpath.stem] = m.group(1)
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not re.match(r'<([^>]+)>', line):
                continue
            words = ivtff_clean_words(line[line.index('>') + 1:].strip())
            if len(words) >= MIN_LINE_WORDS:
                lines.append(words)
                folios.append(fpath.stem)
    return lines, folios, lang_by_folio


def hand_subset(lines, folios, lang_by_folio, hand):
    ls, fs = [], []
    for line, fol in zip(lines, folios):
        base = fol.split('.')[0]
        if lang_by_folio.get(base) == hand:
            ls.append(line)
            fs.append(base)
    return ls, fs


# ────────────────────────────────────────────────────────────────────
# part 1: compact headline fingerprint (alphabet-computable)
# ────────────────────────────────────────────────────────────────────
def entropy(counter):
    tot = sum(counter.values())
    return -sum(c / tot * math.log2(c / tot)
                for c in counter.values() if c) if tot else 0.0


def jsd(p, q):
    keys = set(p) | set(q)
    sp, sq = sum(p.values()) or 1, sum(q.values()) or 1
    d = 0.0
    for k in keys:
        a, b = p.get(k, 0) / sp, q.get(k, 0) / sq
        m = (a + b) / 2
        if a:
            d += a / 2 * math.log2(a / m)
        if b:
            d += b / 2 * math.log2(b / m)
    return d


def fingerprint(lines):
    words = [w for line in lines for w in line]
    stream = []
    for w in words:
        stream.extend(w)
        stream.append(' ')
    uni = Counter(stream)
    big = Counter(zip(stream, stream[1:]))
    h1 = entropy(uni)
    # conditional entropy via joint minus marginal of first symbol
    marg = Counter()
    for (a, b), c in big.items():
        marg[a] += c
    h2 = entropy(big) - entropy(marg)
    init_first = Counter(line[0][0] for line in lines)
    other_first = Counter(w[0] for line in lines for w in line[1:])
    final_last = Counter(line[-1][-1] for line in lines)
    other_last = Counter(w[-1] for line in lines for w in line[:-1])
    return {'h2_ratio': round(h2 / h1, 4) if h1 else 0.0,
            'ttr_5000': round(len(set(words[:5000])) /
                              max(len(words[:5000]), 1), 4),
            'zipf_alpha': round(zipf_alpha(words), 4),
            'mean_wlen': round(sum(len(w) for w in words) / len(words), 4),
            'line_init_jsd': round(jsd(init_first, other_first), 4),
            'line_final_jsd': round(jsd(final_last, other_last), 4),
            'n_lines': len(lines), 'n_tokens': len(words),
            'alphabet': len({c for w in words for c in w})}


# ────────────────────────────────────────────────────────────────────
# part 2: S7 rung-3 decisive battery, alphabet-agnostic features
# ────────────────────────────────────────────────────────────────────
def features(w):
    return {'len': str(min(len(w), 7)) if len(w) < 7 else '7+',
            'first': w[0], 'last': w[-1]}


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


def interior_gain(lines, folios, rng):
    train_idx, hold_idx = holdout_split(lines, folios, rng)
    global_c = {f: Counter() for f in FEATURE_NAMES}
    bin_c = {f: {} for f in FEATURE_NAMES}
    for i in train_idx:
        line = lines[i]
        L = len(line)
        for pos, w in enumerate(line):
            b = position_bin(pos, L)
            fe = features(w)
            for f in FEATURE_NAMES:
                global_c[f][fe[f]] += 1
                bin_c[f].setdefault(b, Counter())[fe[f]] += 1
    cats = {f: sorted(global_c[f]) for f in FEATURE_NAMES}

    def logp(counter, val, catlist):
        tot = sum(counter.values())
        v = len(catlist) + 1
        return math.log2((counter.get(val, 0) + ALPHA) / (tot + ALPHA * v))

    s, n = 0.0, 0
    for i in hold_idx:
        line = lines[i]
        L = len(line)
        for pos, w in enumerate(line):
            b = position_bin(pos, L)
            if b not in INTERIOR:
                continue
            fe = features(w)
            for f in FEATURE_NAMES:
                bc = bin_c[f].get(b, Counter())
                s += (logp(bc, fe[f], cats[f])
                      - logp(global_c[f], fe[f], cats[f]))
            n += 1
    return s / n if n else 0.0


def median_gain(lines, folios):
    return round(statistics.median(
        interior_gain(lines, folios, random.Random(SEED + 7 + r))
        for r in range(R_SPLITS)), 4)


def within_line_shuffle(lines, k):
    rng = random.Random(SEED * 1000 + 500 + k)
    out = []
    for line in lines:
        l = line[:]
        rng.shuffle(l)
        out.append(l)
    return out


def ordinal_battery(lines, folios):
    real = median_gain(lines, folios)
    nulls = [median_gain(within_line_shuffle(lines, k), folios)
             for k in range(N_NULLS)]
    margin = round(real - statistics.median(nulls), 4)
    return {'median_gain': real, 'null_max': max(nulls),
            'null_median': round(statistics.median(nulls), 4),
            'margin': margin,
            'pass': real > max(nulls) and margin >= EFFECT_FLOOR}


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('CROSS-TRANSLITERATION INVARIANCE (S9) — A1 audit')
    print('=' * 76)
    print(f'seed={SEED} splits={R_SPLITS} nulls={N_NULLS} '
          f'floor={EFFECT_FLOOR} rel_dev_flag={REL_DEV_FLAG} '
          f'min_B_lines={MIN_B_LINES} features={FEATURE_NAMES}')

    corpora = {'ZL': load_zl()}
    for tag, fname in FILES.items():
        corpora[tag] = load_ivtff_file(TRANSLIT_DIR / fname)

    # part 1 — fingerprint spread
    prints = {}
    for tag, (lines, folios, langs) in corpora.items():
        fp = fingerprint(lines)
        prints[tag] = fp
        print(f'  {tag}: {fp["n_lines"]} lines, {fp["n_tokens"]} tokens, '
              f'alphabet {fp["alphabet"]}  h2r {fp["h2_ratio"]:.3f}  '
              f'init_jsd {fp["line_init_jsd"]:.3f}  final_jsd '
              f'{fp["line_final_jsd"]:.3f}')
    feat_keys = ('h2_ratio', 'ttr_5000', 'zipf_alpha', 'mean_wlen',
                 'line_init_jsd', 'line_final_jsd')
    sensitive = {}
    for k in feat_keys:
        base = prints['ZL'][k]
        devs = {t: round(abs(prints[t][k] - base) / abs(base), 4)
                if base else None for t in FILES}
        flagged = [t for t, d in devs.items() if d is not None
                   and d > REL_DEV_FLAG]
        sensitive[k] = {'zl': base, 'rel_dev': devs, 'flagged': flagged}
    n_flags = sum(1 for k in sensitive if sensitive[k]['flagged'])
    print(f'\n  PART 1: {n_flags}/{len(feat_keys)} headline features '
          f'flagged transliteration-sensitive (>{REL_DEV_FLAG:.0%} vs ZL):')
    for k, row in sensitive.items():
        if row['flagged']:
            print(f'    {k}: flagged in {row["flagged"]} '
                  f'(devs {row["rel_dev"]})')

    # part 2 — S7-B ordinal battery per transliteration
    print('\n  PART 2: S7-B ordinal battery (reduced features), per '
          'transliteration:')
    part2 = {}
    for tag, (lines, folios, langs) in corpora.items():
        b_lines, b_folios = hand_subset(lines, folios, langs, 'B')
        a_lines, a_folios = hand_subset(lines, folios, langs, 'A')
        usable = len(b_lines) >= MIN_B_LINES
        row = {'n_B_lines': len(b_lines), 'n_A_lines': len(a_lines),
               'usable': usable}
        if usable:
            row['B'] = ordinal_battery(b_lines, b_folios)
            row['A_median_gain_observational'] = (
                median_gain(a_lines, a_folios) if len(a_lines) >= MIN_B_LINES
                else None)
            b = row['B']
            print(f'    {tag}: B {b["median_gain"]:+.4f} (null max '
                  f'{b["null_max"]:+.4f}, margin {b["margin"]:+.4f}) -> '
                  f'{"PASS" if b["pass"] else "fail"}   '
                  f'[{len(b_lines)} B-lines]')
        else:
            print(f'    {tag}: UNUSABLE ({len(b_lines)} B-lines < '
                  f'{MIN_B_LINES})')
        part2[tag] = row

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    zl_pass = part2['ZL'].get('B', {}).get('pass', False)
    alts = {t: part2[t] for t in FILES if part2[t]['usable']}
    alt_pass = [t for t, r in alts.items() if r['B']['pass']]
    alt_fail = [t for t, r in alts.items() if not r['B']['pass']]
    if not zl_pass:
        verdict = 'gate_failed'
        print('    GATE FAILED: ZL does not pass with the reduced '
              '(alphabet-agnostic) feature set — the dropped gallows '
              'feature was load-bearing; audit inconclusive.')
    elif alts and not alt_fail:
        verdict = 'robust'
        print(f'    ROBUST: S7-B ordinal signal passes in every usable '
              f'alternative transliteration ({alt_pass}). One named '
              'objection to the rung-3 finding is removed; the finding '
              'itself stays quarantined SUGGESTIVE.')
    elif alt_pass:
        verdict = 'partial'
        print(f'    PARTIAL: passes in {alt_pass}, fails in {alt_fail} — '
              'the finding is sensitive to reading choices; '
              'investigation required before any promotion.')
    else:
        verdict = 'artifact_suspect'
        print(f'    ARTIFACT-SUSPECT: ZL passes but every usable '
              f'alternative fails ({alt_fail}) — the rung-3 finding is '
              'DEMOTED to artifact-suspect (a property of the ZL '
              'reading until shown otherwise).')

    with open(result_path('cross_transliteration_invariance.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'r_splits': R_SPLITS,
                              'n_nulls': N_NULLS,
                              'effect_floor': EFFECT_FLOOR,
                              'rel_dev_flag': REL_DEV_FLAG,
                              'min_b_lines': MIN_B_LINES,
                              'min_line_words': MIN_LINE_WORDS,
                              'holdout_frac': HOLDOUT_FRAC,
                              'alpha': ALPHA,
                              'features': list(FEATURE_NAMES),
                              'files': FILES},
                   'fingerprints': prints, 'sensitivity': sensitive,
                   'part2': part2, 'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/cross_transliteration_invariance.json')


if __name__ == '__main__':
    main()
