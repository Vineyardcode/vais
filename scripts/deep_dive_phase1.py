#!/usr/bin/env python3
"""
VOYNICH MANUSCRIPT — PHASE 1 DEEP DIVE
========================================
The frequency-rank mapping revealed two root types:
  TYPE A (substances): ka, da, a, o, ta, cho — poly-suffix, noun-like
  TYPE B (processes):   ched, kee, keed, shed — mono-suffix -y, verb-like

This script stress-tests that finding:
  1. WORD ORDER — Do Type A and B roots have positional preferences within lines?
     (nouns before verbs? verbs before nouns? any consistent syntax?)
  2. VERB CHAINS — Are the high-PMI Type B pairs actually adjacent (sequential instructions)?
  3. THE q- ANOMALY — Why does prefix q- massively prefer suffix -l?
  4. SUFFIX ALTERNATION — When the same root appears multiple times in a line,
     does it cycle through suffixes? (= different preparations of same ingredient)
  5. THE da PUZZLE — da is 85% unprefixed, 43% suffix -iin. Is da+iin a single
     lexeme (a fixed word) or truly compositional?
  6. ADJACENCY BIGRAMS — What prefix+suffix frames appear next to each other?
     This reveals the actual "sentence structure" of the notation.
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict

# ═══════════════════════════════════════════════════════════════════════════
# PARSER (reused)
# ═══════════════════════════════════════════════════════════════════════════

PREFIXES = [
    "qol", "qor", "sol", "sor", "dol", "dor", "dyl", "dyr",
    "qo", "so", "do", "dy",
    "ol", "or", "yl", "yr",
    "q", "d", "s",
    "o", "y",
    "l", "r",
]

ROOT_ONSETS = [
    "ckh", "cth", "cph", "cfh",
    "tch", "kch", "pch", "fch",
    "tsh", "ksh", "psh", "fsh",
    "sh", "ch",
    "f", "p", "k", "t",
]

ROOT_BODIES = [
    "eeed", "eees", "eeea", "eeeo",
    "eed", "ees", "eea", "eeo",
    "ed", "es", "ea", "eo",
    "eee", "ee", "e",
    "da", "do", "sa", "so",
    "d", "s",
    "a", "o",
]

SUFFIXES = [
    "iiiny", "iiny", "iiir", "iiil", "iiin",
    "iir", "iil", "iin", "iim", "iid",
    "iry", "ily", "iny",
    "ir", "il", "in", "im", "id",
    "iii", "ii",
    "dy", "ly", "ry", "ny", "my",
    "i",
    "y",
    "n", "m", "d", "l", "r",
]


def parse_word(word):
    best = None
    best_score = -1
    prefix_options = [""]
    for pfx in PREFIXES:
        if word.startswith(pfx):
            prefix_options.append(pfx)
    for pfx in prefix_options:
        rest1 = word[len(pfx):]
        onset_options = [""]
        for onset in ROOT_ONSETS:
            if rest1.startswith(onset):
                onset_options.append(onset)
        for onset in onset_options:
            rest2 = rest1[len(onset):]
            body_options = [""]
            for body in ROOT_BODIES:
                if rest2.startswith(body):
                    body_options.append(body)
            for body in body_options:
                rest3 = rest2[len(body):]
                suf_options = [""]
                for suf in SUFFIXES:
                    if rest3 == suf:
                        suf_options.append(suf)
                for suf in suf_options:
                    if suf:
                        if rest3 == suf:
                            remainder = ""
                        elif rest3.endswith(suf):
                            remainder = rest3[:-len(suf)]
                        else:
                            remainder = rest3
                    else:
                        remainder = rest3
                    explained = len(pfx) + len(onset) + len(body) + len(suf)
                    score = explained * 10 - len(remainder) * 15
                    if not remainder:
                        score += 50
                    if onset or body:
                        score += 20
                    if not onset and not body and (pfx or suf):
                        score -= 10
                    if score > best_score:
                        best_score = score
                        best = (pfx, onset, body, suf, remainder)
    if best is None:
        return ("", "", "", "", word)
    return best


def get_root(onset, body):
    return onset + body


# ═══════════════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════════════

def classify_folio(header_lines):
    text = "\n".join(header_lines).lower()
    if "herbal" in text:
        return "herbal"
    elif "astro" in text or "cosmo" in text or "star" in text or "zodiac" in text:
        return "astro"
    elif "pharm" in text or "recipe" in text or "balneo" in text:
        return "pharma"
    elif "biolog" in text or "bathy" in text:
        return "bio"
    elif "text only" in text:
        return "text"
    return "other"


def load_lines():
    """Return list of (folio, section, [(word, pfx, root, suf), ...])"""
    folio_dir = Path("folios")
    lines = []
    for txt_file in sorted(folio_dir.glob("*.txt")):
        raw = txt_file.read_text(encoding="utf-8").splitlines()
        header = []
        section = None
        for line in raw:
            s = line.strip()
            if s.startswith("#") or re.match(r"^<f\w+>\s", s):
                header.append(s)
                continue
            if not s or s.startswith("<!"):
                continue
            m = re.match(r"<([^>]+)>\s*(.*)", s)
            if not m:
                continue
            locus, text = m.group(1), m.group(2)
            if re.search(r"[,@*+]L", locus):
                continue  # skip labels for word-order analysis
            text = re.sub(r"<![^>]*>", "", text)
            text = re.sub(r"<%>|<\$>|<->", " ", text)
            text = re.sub(r"<[^>]*>", "", text)
            text = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", text)
            text = re.sub(r"\{([^}]+)\}", r"\1", text)
            text = re.sub(r"@\d+;?", "", text)
            tokens = re.split(r"[.\s,<>\-]+", text)
            parsed = []
            for tok in tokens:
                tok = tok.strip()
                if not tok or "?" in tok or "'" in tok:
                    continue
                if re.match(r"^[a-z]+$", tok) and len(tok) >= 2:
                    pfx, onset, body, suf, rem = parse_word(tok)
                    if not rem:
                        root = get_root(onset, body)
                        parsed.append((tok, pfx or "∅", root, suf or "∅"))
            if parsed:
                if section is None:
                    section = classify_folio(header)
                lines.append((txt_file.stem, section, parsed))
    return lines


# Type classification
TYPE_A_ROOTS = {"ka", "da", "a", "o", "ta", "cho", "ko", "sa", "cheo", "sho",
                "keo", "to", "cha", "do", "sheo", "ch"}
TYPE_B_ROOTS = {"ched", "kee", "keed", "shed", "che", "ked", "she", "ted",
                "chee", "kch", "tch", "d", "k", "t"}


def root_type(root):
    if root in TYPE_A_ROOTS:
        return "A"
    elif root in TYPE_B_ROOTS:
        return "B"
    return "?"


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSES
# ═══════════════════════════════════════════════════════════════════════════

def test1_word_order(lines):
    """Test positional preferences of Type A vs Type B within lines."""
    print("=" * 90)
    print("TEST 1: WORD ORDER — Positional preferences of nouns vs verbs")
    print("=" * 90)
    print()
    print("  If there's syntax, Type A (nouns) and Type B (verbs) should")
    print("  have different positional distributions within lines.")
    print()

    # For each parsed word in a line, record its relative position (0.0 = first, 1.0 = last)
    type_a_positions = []
    type_b_positions = []
    # Also: absolute position (first word, last word, middle)
    type_a_abs = Counter()  # 'first', 'last', 'middle'
    type_b_abs = Counter()

    for folio, section, parsed in lines:
        n = len(parsed)
        if n < 3:
            continue
        for i, (word, pfx, root, suf) in enumerate(parsed):
            rt = root_type(root)
            rel_pos = i / (n - 1)
            if rt == "A":
                type_a_positions.append(rel_pos)
                if i == 0:
                    type_a_abs['first'] += 1
                elif i == n - 1:
                    type_a_abs['last'] += 1
                else:
                    type_a_abs['middle'] += 1
            elif rt == "B":
                type_b_positions.append(rel_pos)
                if i == 0:
                    type_b_abs['first'] += 1
                elif i == n - 1:
                    type_b_abs['last'] += 1
                else:
                    type_b_abs['middle'] += 1

    a_mean = sum(type_a_positions) / len(type_a_positions) if type_a_positions else 0
    b_mean = sum(type_b_positions) / len(type_b_positions) if type_b_positions else 0
    a_total = sum(type_a_abs.values())
    b_total = sum(type_b_abs.values())

    print(f"  Type A (noun-like) tokens: {len(type_a_positions)}")
    print(f"  Type B (verb-like) tokens: {len(type_b_positions)}")
    print()
    print(f"  MEAN RELATIVE POSITION (0=start, 1=end):")
    print(f"    Type A: {a_mean:.3f}")
    print(f"    Type B: {b_mean:.3f}")
    print(f"    Δ = {b_mean - a_mean:.3f}", end="")
    if abs(b_mean - a_mean) > 0.02:
        if b_mean > a_mean:
            print("  → Type B tends toward LINE END (verb-final?)")
        else:
            print("  → Type B tends toward LINE START (verb-initial?)")
    else:
        print("  → No significant positional difference")
    print()

    print(f"  ABSOLUTE POSITION:")
    print(f"  {'Type':8s}  {'First':>8s}  {'Middle':>8s}  {'Last':>8s}  {'First%':>8s}  {'Last%':>8s}")
    print(f"  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}")
    for label, abs_c, total in [("A", type_a_abs, a_total), ("B", type_b_abs, b_total)]:
        f_pct = 100 * abs_c['first'] / total if total else 0
        l_pct = 100 * abs_c['last'] / total if total else 0
        print(f"  Type {label}   {abs_c['first']:8d}  {abs_c['middle']:8d}  {abs_c['last']:8d}  {f_pct:7.1f}%  {l_pct:7.1f}%")
    print()

    # Bigram transitions: what follows what?
    trans = Counter()  # (prev_type, next_type)
    for folio, section, parsed in lines:
        for i in range(len(parsed) - 1):
            t1 = root_type(parsed[i][2])
            t2 = root_type(parsed[i + 1][2])
            if t1 != "?" and t2 != "?":
                trans[(t1, t2)] += 1

    total_trans = sum(trans.values())
    print(f"  TYPE TRANSITIONS (bigrams):")
    print(f"  {'Transition':15s}  {'Count':>7s}  {'%':>7s}  {'Expected%':>10s}  {'O/E':>6s}")
    print(f"  {'─'*15}  {'─'*7}  {'─'*7}  {'─'*10}  {'─'*6}")

    a_frac = len(type_a_positions) / (len(type_a_positions) + len(type_b_positions))
    b_frac = 1 - a_frac
    for t1, t2 in [("A", "A"), ("A", "B"), ("B", "A"), ("B", "B")]:
        count = trans.get((t1, t2), 0)
        obs_pct = 100 * count / total_trans if total_trans else 0
        exp_frac1 = a_frac if t1 == "A" else b_frac
        exp_frac2 = a_frac if t2 == "A" else b_frac
        exp_pct = 100 * exp_frac1 * exp_frac2
        oe = obs_pct / exp_pct if exp_pct > 0 else 0
        label = f"  {t1} → {t2}"
        print(f"  {label:15s}  {count:7d}  {obs_pct:6.1f}%  {exp_pct:9.1f}%  {oe:5.2f}×")
    print()

    # Does B→B chain length differ from A→A?
    print(f"  CHAIN LENGTHS (consecutive same-type runs):")
    for target_type, label in [("A", "Type A"), ("B", "Type B")]:
        chain_lengths = []
        for folio, section, parsed in lines:
            run = 0
            for word, pfx, root, suf in parsed:
                if root_type(root) == target_type:
                    run += 1
                else:
                    if run > 0:
                        chain_lengths.append(run)
                    run = 0
            if run > 0:
                chain_lengths.append(run)
        if chain_lengths:
            avg = sum(chain_lengths) / len(chain_lengths)
            max_c = max(chain_lengths)
            long = sum(1 for c in chain_lengths if c >= 3)
            print(f"    {label}: avg={avg:.2f}, max={max_c}, runs≥3: {long}")
    print()


def test2_verb_chains(lines):
    """Examine Type B adjacency — are process-words sequential instructions?"""
    print("=" * 90)
    print("TEST 2: VERB CHAINS — Adjacent Type B (process) words")
    print("=" * 90)
    print()

    # Find all B→B adjacent pairs with actual words
    bb_pairs = Counter()
    bb_examples = defaultdict(list)
    for folio, section, parsed in lines:
        for i in range(len(parsed) - 1):
            w1, p1, r1, s1 = parsed[i]
            w2, p2, r2, s2 = parsed[i + 1]
            if root_type(r1) == "B" and root_type(r2) == "B":
                key = (r1, r2)
                bb_pairs[key] += 1
                if len(bb_examples[key]) < 3:
                    bb_examples[key].append((folio, w1, w2))

    print(f"  Total B→B adjacent pairs: {sum(bb_pairs.values())}")
    print(f"  Distinct B→B root pairs: {len(bb_pairs)}")
    print()
    print(f"  TOP 20 B→B PAIRS:")
    print(f"  {'Root1':10s}  {'Root2':10s}  {'Count':>6s}  Examples")
    print(f"  {'─'*10}  {'─'*10}  {'─'*6}  {'─'*40}")
    for (r1, r2), count in bb_pairs.most_common(20):
        exs = bb_examples[(r1, r2)]
        ex_str = "; ".join(f"{w1} {w2}" for _, w1, w2 in exs[:2])
        print(f"  {r1:10s}  {r2:10s}  {count:6d}  {ex_str}")
    print()

    # Show actual multi-B sequences (3+ consecutive B words)
    print(f"  LONG VERB CHAINS (3+ consecutive Type B):")
    long_chains = []
    for folio, section, parsed in lines:
        chain = []
        for word, pfx, root, suf in parsed:
            if root_type(root) == "B":
                chain.append((word, pfx, root, suf))
            else:
                if len(chain) >= 3:
                    long_chains.append((folio, section, chain[:]))
                chain = []
        if len(chain) >= 3:
            long_chains.append((folio, section, chain[:]))

    long_chains.sort(key=lambda x: -len(x[2]))
    for folio, section, chain in long_chains[:15]:
        words = " ".join(w for w, _, _, _ in chain)
        frames = " | ".join(f"{p}+{r}+{s}" for _, p, r, s in chain)
        print(f"    [{len(chain)}] {folio} ({section}): {words}")
        print(f"         {frames}")
    print()


def test3_q_anomaly(lines):
    """Why does prefix q- overwhelmingly select suffix -l?"""
    print("=" * 90)
    print("TEST 3: THE q- ANOMALY — Why q- loves suffix -l")
    print("=" * 90)
    print()

    # Collect all q-prefixed words
    q_words = Counter()
    q_roots = Counter()
    q_root_suf = Counter()
    q_contexts = defaultdict(list)  # store surrounding words

    for folio, section, parsed in lines:
        for i, (word, pfx, root, suf) in enumerate(parsed):
            if pfx == "q":
                q_words[word] += 1
                q_roots[root] += 1
                q_root_suf[(root, suf)] += 1
                # Context: previous and next word
                prev_w = parsed[i-1][0] if i > 0 else "^"
                next_w = parsed[i+1][0] if i < len(parsed)-1 else "$"
                if len(q_contexts[word]) < 3:
                    q_contexts[word].append((folio, prev_w, word, next_w))

    print(f"  Total q- words: {sum(q_words.values())}")
    print(f"  Distinct q- words: {len(q_words)}")
    print()
    print(f"  TOP q- WORDS:")
    for word, count in q_words.most_common(15):
        pfx, onset, body, suf, _ = parse_word(word)
        root = get_root(onset, body)
        ctxs = q_contexts[word]
        ctx_str = "; ".join(f"...{p} [{w}] {n}..." for _, p, w, n in ctxs[:2])
        print(f"    {word:15s}  count={count:4d}  root={root:8s} suf={suf or '∅':5s}  {ctx_str}")
    print()

    print(f"  q- ROOT × SUFFIX:")
    for (root, suf), count in q_root_suf.most_common(15):
        print(f"    q+{root}+{suf or '∅'}: {count}")
    print()

    # Compare q- to qo- (which is much more common)
    print(f"  COMPARISON: q- vs qo- suffix distributions:")
    q_sufs = Counter()
    qo_sufs = Counter()
    for folio, section, parsed in lines:
        for word, pfx, root, suf in parsed:
            if pfx == "q":
                q_sufs[suf] += 1
            elif pfx == "qo":
                qo_sufs[suf] += 1

    all_sufs = sorted(set(list(q_sufs.keys()) + list(qo_sufs.keys())),
                       key=lambda s: -(q_sufs.get(s, 0) + qo_sufs.get(s, 0)))
    q_tot = sum(q_sufs.values())
    qo_tot = sum(qo_sufs.values())
    print(f"  {'Suffix':>8s}  {'q-':>8s}  {'q-%':>7s}  {'qo-':>8s}  {'qo-%':>7s}  {'Ratio':>7s}")
    print(f"  {'─'*8}  {'─'*8}  {'─'*7}  {'─'*8}  {'─'*7}  {'─'*7}")
    for suf in all_sufs[:10]:
        qc = q_sufs.get(suf, 0)
        qoc = qo_sufs.get(suf, 0)
        qp = 100 * qc / q_tot if q_tot else 0
        qop = 100 * qoc / qo_tot if qo_tot else 0
        ratio = qp / qop if qop > 0 else float('inf')
        print(f"  {suf or '∅':>8s}  {qc:8d}  {qp:6.1f}%  {qoc:8d}  {qop:6.1f}%  {ratio:6.1f}×")
    print()


def test4_suffix_alternation(lines):
    """When the same root appears multiple times in a line, does the suffix change?"""
    print("=" * 90)
    print("TEST 4: SUFFIX ALTERNATION — Same root, different suffixes in one line")
    print("=" * 90)
    print()

    # For each line, find roots that appear 2+ times
    alternation_events = []  # (root, [suffixes...], folio, [words...])
    same_suffix_count = 0
    diff_suffix_count = 0

    for folio, section, parsed in lines:
        root_entries = defaultdict(list)
        for word, pfx, root, suf in parsed:
            root_entries[root].append((word, pfx, suf))
        for root, entries in root_entries.items():
            if len(entries) >= 2:
                suffixes = [e[2] for e in entries]
                words = [e[0] for e in entries]
                if len(set(suffixes)) > 1:
                    diff_suffix_count += 1
                    alternation_events.append((root, suffixes, folio, words))
                else:
                    same_suffix_count += 1

    total = same_suffix_count + diff_suffix_count
    print(f"  Lines with repeated root: {total}")
    print(f"    Same suffix (repetition): {same_suffix_count} ({100*same_suffix_count/total:.1f}%)")
    print(f"    Different suffix (alternation): {diff_suffix_count} ({100*diff_suffix_count/total:.1f}%)")
    print()

    # Is alternation more common for Type A or Type B?
    a_alt = sum(1 for r, _, _, _ in alternation_events if root_type(r) == "A")
    b_alt = sum(1 for r, _, _, _ in alternation_events if root_type(r) == "B")
    a_same = 0
    b_same = 0
    for folio, section, parsed in lines:
        root_entries = defaultdict(list)
        for word, pfx, root, suf in parsed:
            root_entries[root].append(suf)
        for root, sufs in root_entries.items():
            if len(sufs) >= 2 and len(set(sufs)) == 1:
                if root_type(root) == "A":
                    a_same += 1
                elif root_type(root) == "B":
                    b_same += 1

    print(f"  TYPE A roots:")
    print(f"    Alternation: {a_alt}  Same: {a_same}  Alt rate: {100*a_alt/(a_alt+a_same):.1f}%")
    print(f"  TYPE B roots:")
    print(f"    Alternation: {b_alt}  Same: {b_same}  Alt rate: {100*b_alt/(b_alt+b_same):.1f}%")
    print()

    # What suffix transitions are most common?
    suffix_transitions = Counter()
    for root, suffixes, folio, words in alternation_events:
        for i in range(len(suffixes) - 1):
            if suffixes[i] != suffixes[i+1]:
                suffix_transitions[(suffixes[i], suffixes[i+1])] += 1

    print(f"  TOP SUFFIX TRANSITIONS (within alternation events):")
    print(f"  {'From':>8s}  {'To':>8s}  {'Count':>6s}")
    print(f"  {'─'*8}  {'─'*8}  {'─'*6}")
    for (s1, s2), count in suffix_transitions.most_common(20):
        print(f"  {s1 or '∅':>8s}  {s2 or '∅':>8s}  {count:6d}")
    print()

    # Show examples of suffix alternation for Type A roots
    print(f"  EXAMPLES — Type A suffix alternation:")
    shown = set()
    for root, suffixes, folio, words in alternation_events:
        if root_type(root) == "A" and root not in shown and len(set(suffixes)) >= 2:
            word_str = ", ".join(words[:5])
            suf_str = " → ".join(suffixes[:5])
            print(f"    {root:8s} in {folio}: {word_str}")
            print(f"             suffixes: {suf_str}")
            shown.add(root)
            if len(shown) >= 10:
                break
    print()


def test5_daiin_lexeme(lines):
    """Is 'daiin' a fixed lexeme or truly compositional da+iin?"""
    print("=" * 90)
    print("TEST 5: THE daiin QUESTION — Fixed lexeme or compositional?")
    print("=" * 90)
    print()

    # daiin = da + iin
    # If compositional: da+iin should behave like other da+X forms
    # If fixed: daiin should have its own distributional identity

    # Collect contexts for daiin vs other da-words
    daiin_prev = Counter()
    daiin_next = Counter()
    other_da_prev = Counter()
    other_da_next = Counter()
    daiin_positions = []
    other_da_positions = []

    for folio, section, parsed in lines:
        n = len(parsed)
        for i, (word, pfx, root, suf) in enumerate(parsed):
            if root == "da":
                rel = i / (n - 1) if n > 1 else 0.5
                prev_frame = ""
                next_frame = ""
                if i > 0:
                    pw, pp, pr, ps = parsed[i-1]
                    prev_frame = f"{pp}+{pr}+{ps}"
                if i < n - 1:
                    nw, np, nr, ns = parsed[i+1]
                    next_frame = f"{np}+{nr}+{ns}"

                if suf == "iin" and pfx == "∅":
                    daiin_positions.append(rel)
                    if prev_frame:
                        daiin_prev[prev_frame] += 1
                    if next_frame:
                        daiin_next[next_frame] += 1
                else:
                    other_da_positions.append(rel)
                    if prev_frame:
                        other_da_prev[prev_frame] += 1
                    if next_frame:
                        other_da_next[next_frame] += 1

    print(f"  'daiin' (∅+da+iin) occurrences: {len(daiin_positions)}")
    print(f"  Other da-words: {len(other_da_positions)}")
    print()

    d_mean = sum(daiin_positions) / len(daiin_positions) if daiin_positions else 0
    o_mean = sum(other_da_positions) / len(other_da_positions) if other_da_positions else 0
    print(f"  Mean position: daiin={d_mean:.3f}, other-da={o_mean:.3f}, Δ={d_mean - o_mean:.3f}")
    print()

    # What precedes daiin vs other da-words?
    print(f"  WHAT PRECEDES daiin:")
    for frame, count in daiin_prev.most_common(10):
        print(f"    {frame:30s}  {count}")
    print()
    print(f"  WHAT PRECEDES other da-words:")
    for frame, count in other_da_prev.most_common(10):
        print(f"    {frame:30s}  {count}")
    print()

    print(f"  WHAT FOLLOWS daiin:")
    for frame, count in daiin_next.most_common(10):
        print(f"    {frame:30s}  {count}")
    print()
    print(f"  WHAT FOLLOWS other da-words:")
    for frame, count in other_da_next.most_common(10):
        print(f"    {frame:30s}  {count}")
    print()

    # Also test okaiin, otaiin, etc. — are all X+a+iin the same pattern?
    print(f"  ALL *aiin WORDS (any prefix + root ending in 'a' + suffix 'iin'):")
    aiin_words = Counter()
    for folio, section, parsed in lines:
        for word, pfx, root, suf in parsed:
            if suf == "iin" and root.endswith("a"):
                aiin_words[word] += 1
    for word, count in aiin_words.most_common(15):
        pfx, onset, body, suf, _ = parse_word(word)
        root = get_root(onset, body)
        print(f"    {word:15s}  count={count:5d}  = {pfx or '∅'}+{root}+{suf}")
    print()


def test6_adjacency_bigrams(lines):
    """What frame (prefix+suffix) patterns appear next to each other?"""
    print("=" * 90)
    print("TEST 6: ADJACENCY BIGRAMS — Frame-to-frame transitions")
    print("=" * 90)
    print()
    print("  This reveals the actual 'sentence grammar' — what construction")
    print("  follows what construction, independent of which root fills the slot.")
    print()

    # Frame = prefix + suffix (ignoring root)
    frame_bigrams = Counter()
    frame_trigrams = Counter()

    for folio, section, parsed in lines:
        frames = [(pfx, suf) for word, pfx, root, suf in parsed]
        for i in range(len(frames) - 1):
            frame_bigrams[(frames[i], frames[i+1])] += 1
        for i in range(len(frames) - 2):
            frame_trigrams[(frames[i], frames[i+1], frames[i+2])] += 1

    total_bi = sum(frame_bigrams.values())
    print(f"  Total frame bigrams: {total_bi}")
    print()

    print(f"  TOP 25 FRAME BIGRAMS:")
    print(f"  {'Frame 1':20s}  {'Frame 2':20s}  {'Count':>6s}  {'%':>6s}")
    print(f"  {'─'*20}  {'─'*20}  {'─'*6}  {'─'*6}")
    for (f1, f2), count in frame_bigrams.most_common(25):
        pct = 100 * count / total_bi
        f1_str = f"{f1[0]}+_+{f1[1]}"
        f2_str = f"{f2[0]}+_+{f2[1]}"
        print(f"  {f1_str:20s}  {f2_str:20s}  {count:6d}  {pct:5.1f}%")
    print()

    total_tri = sum(frame_trigrams.values())
    print(f"  TOP 20 FRAME TRIGRAMS:")
    print(f"  {'Frame 1':15s}  {'Frame 2':15s}  {'Frame 3':15s}  {'Count':>6s}")
    print(f"  {'─'*15}  {'─'*15}  {'─'*15}  {'─'*6}")
    for (f1, f2, f3), count in frame_trigrams.most_common(20):
        f1s = f"{f1[0]}+_+{f1[1]}"
        f2s = f"{f2[0]}+_+{f2[1]}"
        f3s = f"{f3[0]}+_+{f3[1]}"
        print(f"  {f1s:15s}  {f2s:15s}  {f3s:15s}  {count:6d}")
    print()

    # LINE-INITIAL and LINE-FINAL frame preferences
    print(f"  LINE-INITIAL FRAMES (first word of line):")
    initial_frames = Counter()
    final_frames = Counter()
    for folio, section, parsed in lines:
        if parsed:
            w, p, r, s = parsed[0]
            initial_frames[(p, s)] += 1
            w, p, r, s = parsed[-1]
            final_frames[(p, s)] += 1

    total_init = sum(initial_frames.values())
    for (pfx, suf), count in initial_frames.most_common(10):
        pct = 100 * count / total_init
        print(f"    {pfx}+_+{suf}: {count} ({pct:.1f}%)")
    print()

    total_fin = sum(final_frames.values())
    print(f"  LINE-FINAL FRAMES:")
    for (pfx, suf), count in final_frames.most_common(10):
        pct = 100 * count / total_fin
        print(f"    {pfx}+_+{suf}: {count} ({pct:.1f}%)")
    print()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Loading folios...")
    lines = load_lines()
    print(f"Loaded {len(lines)} text lines")
    print()

    test1_word_order(lines)
    test2_verb_chains(lines)
    test3_q_anomaly(lines)
    test4_suffix_alternation(lines)
    test5_daiin_lexeme(lines)
    test6_adjacency_bigrams(lines)

    print("=" * 90)
    print("DEEP DIVE COMPLETE")
    print("=" * 90)
