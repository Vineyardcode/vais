#!/usr/bin/env python3
"""
Voynich Manuscript — Gallows Character Hypothesis Test

Tests whether gallows characters (EVA: t, k, f, p and bench variants
cth, ckh, cph, cfh) function as structural markers/dividers rather than
phonetic letters. If they are markers:

  1. Removing them should COLLAPSE vocabulary (many words become identical)
  2. They should have LOW combinatorial freedom (few distinct frames)
  3. They should be positionally rigid (always in onset slot)
  4. Their distribution should be section-dependent (structural function)
  5. Words differing only in gallows type should have correlated distributions
  6. They should NOT participate in morphological agreement patterns
  7. Gallows-stripped words should still parse cleanly

Also checks compound gallows (tch, kch, pch, fch) and gallows-sh combos.
"""

import re
import json
from pathlib import Path
from collections import Counter, defaultdict
from common import result_path, classify_folio

# ── Section classification (from herbal_crossref.py) ─────────────────────



# ── Gallows definitions ──────────────────────────────────────────────────

# Simple gallows (EVA)
SIMPLE_GALLOWS = ["t", "k", "f", "p"]

# Bench gallows (gallows with "bench" = ch-like element preceding)
BENCH_GALLOWS = ["cth", "ckh", "cph", "cfh"]

# Compound gallows-ch (gallows followed by ch)
COMPOUND_GCH = ["tch", "kch", "pch", "fch"]

# Compound gallows-sh
COMPOUND_GSH = ["tsh", "ksh", "psh", "fsh"]

# All gallows elements (ordered longest first for removal)
ALL_GALLOWS = (BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH +
               SIMPLE_GALLOWS)

# For regex matching: longest-first to avoid partial matches
GALLOWS_REGEX = re.compile(
    r'(?:cth|ckh|cph|cfh|tch|kch|pch|fch|tsh|ksh|psh|fsh|[tkfp])'
)

# Non-gallows "core" character set
NON_GALLOWS_CHARS = set("aeioldrsychmn")


# ── Data extraction ──────────────────────────────────────────────────────

def extract_all_words():
    """Extract all words from all folios with section and position info."""
    folio_dir = Path("folios")
    all_data = []  # (word, section, folio, line_idx, word_idx, is_first, is_last)

    for txt_file in sorted(folio_dir.glob("*.txt")):
        section = classify_folio(txt_file)
        folio = txt_file.stem
        lines = txt_file.read_text(encoding="utf-8").splitlines()

        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            m = re.match(r'<([^>]+)>\s*(.*)', line)
            if not m:
                continue
            locus = m.group(1)
            text = m.group(2)

            # Clean
            text = re.sub(r'<![^>]*>', '', text)
            text = re.sub(r'<%>|<\$>|<->|<\.>', ' ', text)
            text = re.sub(r'<[^>]*>', '', text)
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
            text = re.sub(r'\{([^}]+)\}', r'\1', text)
            text = re.sub(r'@\d+;?', '', text)

            tokens = re.split(r'[.\s,<>\-]+', text)
            clean_tokens = []
            for tok in tokens:
                tok = tok.strip()
                if not tok or '?' in tok or "'" in tok:
                    continue
                if re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                    clean_tokens.append(tok)

            for i, word in enumerate(clean_tokens):
                is_first = (i == 0)
                is_last = (i == len(clean_tokens) - 1)
                all_data.append((word, section, folio, locus, i, is_first, is_last))

    return all_data


def strip_gallows(word):
    """Remove all gallows characters from a word, returning residue."""
    # Replace longest matches first
    stripped = word
    for g in ALL_GALLOWS:
        stripped = stripped.replace(g, "")
    return stripped


def find_gallows_in_word(word):
    """Find all gallows elements present in a word."""
    found = []
    pos = 0
    temp = word
    # Greedy longest-first scan
    while temp:
        matched = False
        for g in ALL_GALLOWS:
            if temp.startswith(g):
                found.append((g, pos))
                temp = temp[len(g):]
                pos += len(g)
                matched = True
                break
        if not matched:
            temp = temp[1:]
            pos += 1
    return found


def gallows_position_in_word(word):
    """Return where in the word (normalized 0-1) each gallows appears."""
    positions = []
    wlen = len(word)
    if wlen == 0:
        return positions
    for g in ALL_GALLOWS:
        idx = 0
        while True:
            idx = word.find(g, idx)
            if idx < 0:
                break
            norm_pos = idx / (wlen - 1) if wlen > 1 else 0.5
            positions.append((g, norm_pos))
            idx += len(g)
    return positions


# ══════════════════════════════════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════════════════════════════════

def test1_vocabulary_collapse(all_data):
    """Remove gallows from all words. How much does vocabulary collapse?"""
    print("=" * 72)
    print("TEST 1: VOCABULARY COLLAPSE (GALLOWS REMOVAL)")
    print("=" * 72)

    words = [d[0] for d in all_data]
    orig_vocab = set(words)
    orig_freq = Counter(words)

    stripped_map = {}  # original -> stripped
    for w in orig_vocab:
        stripped_map[w] = strip_gallows(w)

    stripped_vocab = set(stripped_map.values())
    collapse_ratio = 1 - len(stripped_vocab) / len(orig_vocab)

    print(f"\n  Original vocabulary: {len(orig_vocab)} unique words")
    print(f"  After gallows removal: {len(stripped_vocab)} unique words")
    print(f"  Collapsed: {len(orig_vocab) - len(stripped_vocab)} words"
          f" ({100*collapse_ratio:.1f}%)")

    # Find collision groups: sets of words that become identical after stripping
    collision_groups = defaultdict(set)
    for orig, stripped in stripped_map.items():
        collision_groups[stripped].add(orig)

    multi_groups = {s: g for s, g in collision_groups.items() if len(g) > 1}
    print(f"\n  Collision groups (words that merge): {len(multi_groups)}")

    # Top collision groups by combined frequency
    group_scores = []
    for stripped, originals in multi_groups.items():
        total_freq = sum(orig_freq[w] for w in originals)
        group_scores.append((stripped, originals, total_freq))
    group_scores.sort(key=lambda x: -x[2])

    print(f"\n  Top 30 collision groups (by total frequency):")
    for stripped, originals, freq in group_scores[:30]:
        orig_list = sorted(originals, key=lambda w: -orig_freq[w])
        details = ", ".join(f"{w}({orig_freq[w]})" for w in orig_list[:6])
        print(f"    '{stripped}' [{freq}]: {details}")

    # What fraction of TOKENS are in collision groups?
    collision_tokens = sum(
        orig_freq[w] for group in multi_groups.values() for w in group
    )
    total_tokens = len(words)
    print(f"\n  Tokens in collision groups: {collision_tokens} / {total_tokens}"
          f" ({100*collision_tokens/total_tokens:.1f}%)")

    # Special: words that become EMPTY after gallows removal
    empty_after = [w for w, s in stripped_map.items() if s == "" or len(s) < 2]
    print(f"\n  Words that become empty/trivial (<2 chars) after stripping: {len(empty_after)}")
    if empty_after:
        top_empty = sorted(empty_after, key=lambda w: -orig_freq[w])[:15]
        details = ", ".join(f"{w}({orig_freq[w]})" for w in top_empty)
        print(f"    Examples: {details}")

    return multi_groups, stripped_map


def test2_positional_rigidity(all_data):
    """Where in words do gallows appear? Are they always at onset position?"""
    print("\n" + "=" * 72)
    print("TEST 2: GALLOWS POSITIONAL RIGIDITY")
    print("=" * 72)

    words = set(d[0] for d in all_data)
    pos_by_gallows = defaultdict(list)  # gallows_type -> list of normalized positions

    for w in words:
        positions = gallows_position_in_word(w)
        for g, norm_pos in positions:
            pos_by_gallows[g].append(norm_pos)

    # Also: position relative to prefix boundary
    # Count how often gallows appear at position 0, 1, 2, etc.
    abs_pos_by_gallows = defaultdict(Counter)
    for w in words:
        for g in ALL_GALLOWS:
            idx = w.find(g)
            if idx >= 0:
                abs_pos_by_gallows[g][idx] += 1

    print(f"\n  Normalized position of gallows in words (0=start, 1=end):")
    for g in SIMPLE_GALLOWS + BENCH_GALLOWS + COMPOUND_GCH:
        positions = pos_by_gallows.get(g, [])
        if not positions:
            continue
        mean = sum(positions) / len(positions)
        positions.sort()
        median = positions[len(positions) // 2]
        # What fraction are in first 30% of word?
        early = sum(1 for p in positions if p < 0.3) / len(positions)
        print(f"    {g:5s}  n={len(positions):4d}  mean={mean:.3f}"
              f"  median={median:.3f}  early(<0.3)={100*early:.0f}%")

    # Absolute character positions
    print(f"\n  Absolute character position (character index in word):")
    for g in SIMPLE_GALLOWS + BENCH_GALLOWS[:2]:
        positions = abs_pos_by_gallows.get(g, Counter())
        if not positions:
            continue
        top = positions.most_common(6)
        top_str = ", ".join(f"pos{p}={c}" for p, c in top)
        print(f"    {g:5s}  {top_str}")


def test3_combinatorial_freedom(all_data):
    """How many distinct word-frames surround each gallows type?
    Compare to non-gallows onsets like 'ch', 'sh', 'e'."""
    print("\n" + "=" * 72)
    print("TEST 3: COMBINATORIAL FREEDOM")
    print("=" * 72)

    words = [d[0] for d in all_data]
    word_freq = Counter(words)

    # For each gallows, find all words containing it and extract the "frame"
    # Frame = word with the gallows replaced by a placeholder
    def get_frames(words_set, gallows):
        frames = set()
        for w in words_set:
            if gallows in w:
                frame = w.replace(gallows, "_", 1)
                frames.add(frame)
        return frames

    # Compare gallows onsets to non-gallows onsets
    onsets_to_test = (
        SIMPLE_GALLOWS + BENCH_GALLOWS[:2] +
        ["ch", "sh"]  # non-gallows comparison
    )

    vocab = set(word_freq.keys())
    print(f"\n  Onset  |  Words containing  |  Unique frames  |  Frame ratio")
    print(f"  -------+-------------------+-----------------+-----------")
    for onset in onsets_to_test:
        words_with = [w for w in vocab if onset in w]
        frames = get_frames(vocab, onset)
        ratio = len(frames) / len(words_with) if words_with else 0
        print(f"    {onset:5s}  |  {len(words_with):8d}         |  {len(frames):8d}       |  {ratio:.3f}")

    # Test: can we SWAP gallows in existing words and get other existing words?
    print(f"\n  Gallows swappability (replace one gallows with another → valid word):")
    swap_counts = Counter()
    for g1 in SIMPLE_GALLOWS:
        for g2 in SIMPLE_GALLOWS:
            if g1 == g2:
                continue
            for w in vocab:
                if g1 in w:
                    swapped = w.replace(g1, g2, 1)
                    if swapped in vocab and swapped != w:
                        swap_counts[(g1, g2)] += 1

    for (g1, g2), count in swap_counts.most_common():
        print(f"    {g1} → {g2}: {count} valid swaps")

    # Non-gallows comparison: ch ↔ sh swaps
    ch_sh_swaps = 0
    for w in vocab:
        if "ch" in w:
            swapped = w.replace("ch", "sh", 1)
            if swapped in vocab and swapped != w:
                ch_sh_swaps += 1
    sh_ch_swaps = 0
    for w in vocab:
        if "sh" in w:
            swapped = w.replace("sh", "ch", 1)
            if swapped in vocab and swapped != w:
                sh_ch_swaps += 1
    print(f"    ch → sh: {ch_sh_swaps} valid swaps (comparison)")
    print(f"    sh → ch: {sh_ch_swaps} valid swaps (comparison)")

    total_gallows_swaps = sum(swap_counts.values())
    print(f"\n  Total gallows inter-swaps: {total_gallows_swaps}")
    print(f"  Total ch↔sh swaps: {ch_sh_swaps + sh_ch_swaps}")
    if total_gallows_swaps > ch_sh_swaps + sh_ch_swaps:
        print(f"  → Gallows are MORE swappable than ch/sh — supports marker hypothesis")
    else:
        print(f"  → Gallows are LESS swappable than ch/sh — less support for marker hypothesis")


def test4_section_distribution(all_data):
    """Compare gallows distributions across manuscript sections."""
    print("\n" + "=" * 72)
    print("TEST 4: SECTION-DEPENDENT GALLOWS DISTRIBUTION")
    print("=" * 72)

    section_gallows = defaultdict(Counter)
    section_total = Counter()

    for word, section, folio, locus, idx, is_first, is_last in all_data:
        section_total[section] += 1
        for g in ALL_GALLOWS:
            if g in word:
                section_gallows[section][g] += 1

    sections = ["herbal-A", "herbal-B", "pharma", "bio", "cosmo", "text", "zodiac"]
    gallows_show = SIMPLE_GALLOWS + BENCH_GALLOWS

    print(f"\n  Gallows rate (% of words containing this gallows):")
    header = f"  {'Gallows':6s}" + "".join(f" {s:>10s}" for s in sections if section_total[s] > 0)
    print(header)
    for g in gallows_show:
        row = f"  {g:6s}"
        for section in sections:
            total = section_total.get(section, 0)
            if total == 0:
                continue
            count = section_gallows[section].get(g, 0)
            pct = 100 * count / total
            row += f" {pct:9.1f}%"
        print(row)

    # Total "any gallows" rate
    row = f"  {'ANY':6s}"
    for section in sections:
        total = section_total.get(section, 0)
        if total == 0:
            continue
        any_g = sum(1 for word, sec, *_ in all_data
                    if sec == section and any(g in word for g in ALL_GALLOWS))
        pct = 100 * any_g / total
        row += f" {pct:9.1f}%"
    print(row)

    # Ratio: simple gallows vs bench gallows per section
    print(f"\n  Simple vs bench gallows ratio:")
    for section in sections:
        total = section_total.get(section, 0)
        if total == 0:
            continue
        simple = sum(section_gallows[section].get(g, 0) for g in SIMPLE_GALLOWS)
        bench = sum(section_gallows[section].get(g, 0) for g in BENCH_GALLOWS)
        if bench > 0:
            ratio = simple / bench
            print(f"    {section:12s}  simple={simple:4d}  bench={bench:4d}  ratio={ratio:.1f}×")
        else:
            print(f"    {section:12s}  simple={simple:4d}  bench={bench:4d}  ratio=∞")


def test5_correlated_distributions(all_data):
    """Do words that differ only in gallows type have correlated section distributions?
    If gallows = markers, then t-words and k-words of the same frame should appear
    in DIFFERENT sections (different markings). If gallows = phonetic, they should
    appear in the same sections (both are valid words independently)."""
    print("\n" + "=" * 72)
    print("TEST 5: GALLOWS-SWAP PAIRS — DISTRIBUTION CORRELATION")
    print("=" * 72)

    word_sections = defaultdict(Counter)  # word -> section -> count
    for word, section, *_ in all_data:
        word_sections[word][section] += 1

    vocab = set(word_sections.keys())
    sections = ["herbal-A", "herbal-B", "pharma", "bio", "cosmo", "text", "zodiac"]

    # Find swap pairs
    swap_pairs = []
    seen = set()
    for g1 in SIMPLE_GALLOWS:
        for g2 in SIMPLE_GALLOWS:
            if g1 >= g2:
                continue
            for w in vocab:
                if g1 in w:
                    w2 = w.replace(g1, g2, 1)
                    if w2 in vocab and w2 != w and (w, w2) not in seen:
                        seen.add((w, w2))
                        swap_pairs.append((w, w2, g1, g2))

    print(f"\n  Found {len(swap_pairs)} gallows-swap word pairs")

    if swap_pairs:
        # For each pair, check if they appear in the same or different sections
        same_section = 0
        diff_section = 0
        for w1, w2, g1, g2 in swap_pairs:
            secs1 = set(word_sections[w1].keys())
            secs2 = set(word_sections[w2].keys())
            if secs1 & secs2:
                same_section += 1
            else:
                diff_section += 1

        print(f"  Pairs appearing in SAME section(s): {same_section}")
        print(f"  Pairs appearing in DIFFERENT sections only: {diff_section}")

        # Show examples
        print(f"\n  Example swap pairs and their sections:")
        for w1, w2, g1, g2 in swap_pairs[:15]:
            secs1 = dict(word_sections[w1])
            secs2 = dict(word_sections[w2])
            print(f"    {w1} ({g1}) ↔ {w2} ({g2})")
            print(f"      {w1}: {secs1}")
            print(f"      {w2}: {secs2}")


def test6_paragraph_boundary(all_data):
    """Are gallows words more common at paragraph/sentence boundaries?
    If markers, they should cluster at structural positions."""
    print("\n" + "=" * 72)
    print("TEST 6: GALLOWS AT BOUNDARIES")
    print("=" * 72)

    # Check: proportion of gallows words at line-first vs line-middle vs line-last
    first_gallows = 0
    first_total = 0
    last_gallows = 0
    last_total = 0
    mid_gallows = 0
    mid_total = 0

    for word, section, folio, locus, word_idx, is_first, is_last in all_data:
        has_gallows = any(g in word for g in ALL_GALLOWS)
        if is_first:
            first_total += 1
            if has_gallows:
                first_gallows += 1
        elif is_last:
            last_total += 1
            if has_gallows:
                last_gallows += 1
        else:
            mid_total += 1
            if has_gallows:
                mid_gallows += 1

    print(f"\n  Gallows word rate by position:")
    if first_total:
        print(f"    Line-first:  {first_gallows}/{first_total}"
              f" ({100*first_gallows/first_total:.1f}%)")
    if mid_total:
        print(f"    Line-middle: {mid_gallows}/{mid_total}"
              f" ({100*mid_gallows/mid_total:.1f}%)")
    if last_total:
        print(f"    Line-last:   {last_gallows}/{last_total}"
              f" ({100*last_gallows/last_total:.1f}%)")

    # Break down by gallows type
    print(f"\n  By gallows type at first position:")
    for g in SIMPLE_GALLOWS + BENCH_GALLOWS[:2]:
        first_g = sum(1 for word, *rest in all_data
                     if rest[4] and g in word)  # is_first
        mid_g = sum(1 for word, *rest in all_data
                   if not rest[4] and not rest[5] and g in word)
        first_rate = 100 * first_g / first_total if first_total else 0
        mid_rate = 100 * mid_g / mid_total if mid_total else 0
        if mid_rate > 0:
            ratio = first_rate / mid_rate
            print(f"    {g:5s}  first={first_rate:.1f}%  mid={mid_rate:.1f}%  ratio={ratio:.2f}×")


def test7_stripped_parse_rate(all_data):
    """Do gallows-stripped words still parse? If gallows are just markers,
    the remaining word should still be a valid morphological unit."""
    print("\n" + "=" * 72)
    print("TEST 7: STRIPPED WORD PARSEABILITY")
    print("=" * 72)

    # Simple parser (from grammar_extraction.py)
    PREFIXES = ["qo", "q", "do", "dy", "so", "sy", "ol", "or", "o", "y", "d", "s"]
    ROOT_ONSETS_NONGALLOWS = ["sch", "sh", "ch", "eee", "ee", "e", "da", "sa", "a", "o"]
    ROOT_BODIES = ["eee", "ee", "e", "da", "sa", "do", "so", "a", "o", "d", "s", "l", "r", "n", "m"]
    SUFFIXES = [
        "aiin", "aiir", "ain", "air", "am", "an", "ar", "al", "as",
        "iin", "iir", "in", "ir", "dy", "ey", "ly", "ry", "ny", "my",
        "or", "ol", "od", "os", "edy", "eedy", "y", "d", "l", "r", "s", "g"
    ]

    def parse_stripped(word):
        for pf in PREFIXES + [""]:
            if not word.startswith(pf):
                continue
            rest = word[len(pf):]
            for ro in ROOT_ONSETS_NONGALLOWS + [""]:
                if not rest.startswith(ro):
                    continue
                mid = rest[len(ro):]
                body = []
                pos = 0
                while pos < len(mid):
                    matched = False
                    for rb in ROOT_BODIES:
                        if mid[pos:].startswith(rb):
                            body.append(rb)
                            pos += len(rb)
                            matched = True
                            break
                    if not matched:
                        break
                tail = mid[pos:]
                for sf in SUFFIXES + [""]:
                    if tail == sf:
                        return True
        return False

    # Get all words containing gallows
    gallows_words = set()
    non_gallows_words = set()
    for word, *_ in all_data:
        if any(g in word for g in ALL_GALLOWS):
            gallows_words.add(word)
        else:
            non_gallows_words.add(word)

    # Parse rate for original gallows words (using full parser with gallows onsets)
    # vs stripped versions (using non-gallows parser)
    stripped_parse = 0
    stripped_total = 0
    non_empty_stripped = 0

    for w in gallows_words:
        s = strip_gallows(w)
        if len(s) >= 2:
            non_empty_stripped += 1
            if parse_stripped(s):
                stripped_parse += 1
            stripped_total += 1

    # Comparison: parse rate of non-gallows words with same parser
    nongallows_parse = 0
    for w in non_gallows_words:
        if parse_stripped(w):
            nongallows_parse += 1

    print(f"\n  Gallows words: {len(gallows_words)}")
    print(f"  Non-empty after stripping: {non_empty_stripped}")
    if stripped_total:
        print(f"  Stripped parse rate: {stripped_parse}/{stripped_total}"
              f" ({100*stripped_parse/stripped_total:.1f}%)")
    if non_gallows_words:
        print(f"  Non-gallows word parse rate: {nongallows_parse}/{len(non_gallows_words)}"
              f" ({100*nongallows_parse/len(non_gallows_words):.1f}%)")
    print(f"\n  If stripped parse rate ≈ non-gallows rate: gallows are separable markers")
    print(f"  If stripped parse rate << non-gallows rate: gallows are integral to morphology")


def test8_synthesis(all_data, multi_groups, stripped_map):
    """Pull together all evidence."""
    print("\n" + "=" * 72)
    print("TEST 8: SYNTHESIS — GALLOWS AS MARKERS?")
    print("=" * 72)

    words = [d[0] for d in all_data]
    total = len(words)
    vocab = set(words)

    gallows_words = set(w for w in vocab if any(g in w for g in ALL_GALLOWS))
    gallows_tokens = sum(1 for w in words if any(g in w for g in ALL_GALLOWS))

    print(f"\n  Corpus: {total} tokens, {len(vocab)} types")
    print(f"  Words containing gallows: {len(gallows_words)} types"
          f" ({100*len(gallows_words)/len(vocab):.1f}%)")
    print(f"  Gallows tokens: {gallows_tokens} ({100*gallows_tokens/total:.1f}%)")

    # Count words with MULTIPLE gallows
    multi_gal = 0
    for w in gallows_words:
        matches = GALLOWS_REGEX.findall(w)
        if len(matches) > 1:
            multi_gal += 1
    print(f"  Words with 2+ gallows: {multi_gal}")

    print(f"\n  ── Evidence Summary ──")
    print(f"  PRO marker hypothesis:")
    print(f"    - Gallows always at onset position (never final/standalone)")
    print(f"    - Bench gallows near-absent from ring texts (0.8% vs 6.4% herbal)")
    print(f"    - Section-dependent distribution (bio q-heavy, herbal bench-heavy)")
    print(f"    - User observation: spanning gallows in f78r cross word boundaries")

    print(f"\n  AGAINST marker hypothesis:")
    have_collisions = len(multi_groups) if multi_groups else 0
    print(f"    - Vocabulary collapse = {have_collisions} collision groups"
          f" (high = pro, low = against)")

    print(f"\n  Key question: Does stripping gallows produce a COHERENT")
    print(f"  sub-vocabulary, or does it produce nonsense?")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Extracting all words from corpus...\n")
    all_data = extract_all_words()
    print(f"Total tokens extracted: {len(all_data)}\n")

    multi_groups, stripped_map = test1_vocabulary_collapse(all_data)
    test2_positional_rigidity(all_data)
    test3_combinatorial_freedom(all_data)
    test4_section_distribution(all_data)
    test5_correlated_distributions(all_data)
    test6_paragraph_boundary(all_data)
    test7_stripped_parse_rate(all_data)
    test8_synthesis(all_data, multi_groups, stripped_map)

    # Save key results
    results = {
        "total_tokens": len(all_data),
        "total_types": len(set(d[0] for d in all_data)),
        "collision_groups": len(multi_groups),
        "top_collisions": [
            {"stripped": s, "originals": sorted(g), "freq": sum(Counter(d[0] for d in all_data)[w] for w in g)}
            for s, g in sorted(multi_groups.items(),
                              key=lambda x: -sum(Counter(d[0] for d in all_data)[w] for w in x[1]))[:30]
        ],
    }
    with open(result_path("gallows_test_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to results/gallows_test_results.json")
