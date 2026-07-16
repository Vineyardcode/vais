#!/usr/bin/env python3
"""
RTL Reading Direction Hypothesis Test

Tests whether Voynichese text reads RIGHT-TO-LEFT (like Hebrew/Arabic)
rather than the assumed left-to-right. If the script is RTL:

  1. What we call "prefixes" (o-, qo-, d-, s-) are actually suffixes
  2. What we call "suffixes" (-y, -iin, -ar) are actually prefixes
  3. Sentence-initial words are actually sentence-final
  4. Bigram transitions would be inverted
  5. Character-reversed words might parse better or comparably

Also tests boustrophedon (alternating direction) and checks if
paragraph markers (<%>, <$>) align with either direction hypothesis.

Connected to: Hebrew-like constructed morphology findings (4),
gallows-as-determinative, and the user's observation that
medieval alchemists drew on Egyptian/Hermetic traditions (which include
RTL Semitic scripts).
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import classify_folio

# ── Morphological parser (LTR — standard) ────────────────────────────────

PREFIXES_LTR = ["qo", "q", "do", "dy", "so", "sy", "ol", "or", "o", "y", "d", "s"]
ROOT_ONSETS_LTR = [
    "ckh","cth","cph","cfh","sch","sh","ch","f","p","k","t",
    "eee","ee","e","da","sa","a","o"
]
ROOT_BODIES = [
    "eee","ee","e","da","sa","do","so","a","o",
    "d","s","l","r","n","m"
]
SUFFIXES_LTR = [
    "aiin","aiir","ain","air","am","an","ar","al","as",
    "iin","iir","in","ir","dy","ey","ly","ry","ny","my",
    "or","ol","od","os","edy","eedy","y","d","l","r","s","g"
]

# ── RTL parser: swap prefix/suffix roles ──────────────────────────────────
# If the text is RTL, what EVA transcribers encode as word-initial is
# actually word-final. So we reverse each word, then try parsing with
# the SAME parser (testing character reversal).
#
# We ALSO test: what if suffixes are really prefixes and vice versa?
# This means building a parser where the old suffixes come first and
# old prefixes come last.

# Mirror the suffix list into prefix position (reversed strings)
PREFIXES_RTL = sorted(set(s[::-1] for s in SUFFIXES_LTR), key=lambda x: -len(x))

# Mirror the prefix list into suffix position (reversed strings)
SUFFIXES_RTL = sorted(set(p[::-1] for p in PREFIXES_LTR), key=lambda x: -len(x))

# Root onsets in RTL = reversed root onsets
ROOT_ONSETS_RTL = sorted(set(ro[::-1] for ro in ROOT_ONSETS_LTR), key=lambda x: -len(x))


def parse_word_ltr(word):
    """Parse word assuming LTR (original direction)."""
    best = None
    for pf in PREFIXES_LTR + [""]:
        if not word.startswith(pf):
            continue
        rest = word[len(pf):]
        for ro in ROOT_ONSETS_LTR:
            if not rest.startswith(ro):
                continue
            mid = rest[len(ro):]
            body_parts = []
            pos = 0
            while pos < len(mid):
                matched = False
                for rb in ROOT_BODIES:
                    if mid[pos:].startswith(rb):
                        body_parts.append(rb)
                        pos += len(rb)
                        matched = True
                        break
                if not matched:
                    break
            root_str = ro + "".join(body_parts)
            tail = mid[pos:]
            for sf in SUFFIXES_LTR + [""]:
                if tail == sf:
                    score = (len(pf) > 0) + (len(root_str) > 0) + (len(sf) > 0)
                    if best is None or score > best[3]:
                        best = (pf, root_str, sf, score)
    if best:
        return best[0], best[1], best[2], True
    return "", word, "", False


def parse_word_reversed(word):
    """Reverse the character sequence and re-parse with LTR parser."""
    return parse_word_ltr(word[::-1])


def parse_word_role_swap(word):
    """Parse with swapped roles: old suffixes as prefixes, old prefixes as suffixes."""
    best = None
    for pf in PREFIXES_RTL + [""]:
        if not word.startswith(pf):
            continue
        rest = word[len(pf):]
        for ro in ROOT_ONSETS_RTL:
            if not rest.startswith(ro):
                continue
            mid = rest[len(ro):]
            body_parts = []
            pos = 0
            while pos < len(mid):
                matched = False
                for rb in ROOT_BODIES:
                    if mid[pos:].startswith(rb):
                        body_parts.append(rb)
                        pos += len(rb)
                        matched = True
                        break
                if not matched:
                    break
            root_str = ro + "".join(body_parts)
            tail = mid[pos:]
            for sf in SUFFIXES_RTL + [""]:
                if tail == sf:
                    score = (len(pf) > 0) + (len(root_str) > 0) + (len(sf) > 0)
                    if best is None or score > best[3]:
                        best = (pf, root_str, sf, score)
    if best:
        return best[0], best[1], best[2], True
    return "", word, "", False


# ── Data extraction ──────────────────────────────────────────────────────

def extract_sentences():
    """Extract sentences from all folios, preserving word order and line structure."""
    folio_dir = Path("folios")
    sentences = []  # [ { "folio": str, "locus": str, "words": [str], "section": str } ]

    for txt_file in sorted(folio_dir.glob("*.txt")):
        section = classify_folio(txt_file)
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

            # Has paragraph start?
            has_para_start = "<%>" in text or "<$>" in text
            has_para_end = False  # Check if next line starts a new paragraph

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

            if clean_tokens:
                sentences.append({
                    "folio": txt_file.stem,
                    "locus": locus,
                    "words": clean_tokens,
                    "section": section,
                    "has_para_start": has_para_start,
                })

    return sentences




# ══════════════════════════════════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════════════════════════════════

def test1_parse_rate_comparison(sentences):
    """Compare parse rates: LTR original vs character-reversed vs role-swapped."""
    print("=" * 72)
    print("TEST 1: PARSE RATE COMPARISON — LTR vs REVERSED vs ROLE-SWAP")
    print("=" * 72)

    all_words = set()
    for s in sentences:
        all_words.update(s["words"])

    ltr_success = 0
    rev_success = 0
    swap_success = 0
    rev_swap_success = 0  # reversed + role swap combined

    ltr_scores = []
    rev_scores = []

    for w in all_words:
        pf, root, sf, ok = parse_word_ltr(w)
        if ok:
            ltr_success += 1
            ltr_scores.append((len(pf) > 0) + (len(root) > 0) + (len(sf) > 0))

        pf2, root2, sf2, ok2 = parse_word_reversed(w)
        if ok2:
            rev_success += 1
            rev_scores.append((len(pf2) > 0) + (len(root2) > 0) + (len(sf2) > 0))

        pf3, root3, sf3, ok3 = parse_word_role_swap(w)
        if ok3:
            swap_success += 1

        # Combined: reverse chars then parse with role-swapped parser
        pf4, root4, sf4, ok4 = parse_word_role_swap(w[::-1])
        if ok4:
            rev_swap_success += 1

    total = len(all_words)
    print(f"\n  Unique words tested: {total}")
    print(f"\n  Parse rates:")
    print(f"    LTR (original):               {ltr_success}/{total} ({100*ltr_success/total:.1f}%)")
    print(f"    Character-reversed (LTR parse):{rev_success}/{total} ({100*rev_success/total:.1f}%)")
    print(f"    Role-swapped parser:           {swap_success}/{total} ({100*swap_success/total:.1f}%)")
    print(f"    Reversed + role-swapped:       {rev_swap_success}/{total} ({100*rev_swap_success/total:.1f}%)")

    # Parse quality: average score
    if ltr_scores:
        ltr_mean = sum(ltr_scores) / len(ltr_scores)
        print(f"\n  Mean parse quality (LTR):     {ltr_mean:.2f} / 3.0")
    if rev_scores:
        rev_mean = sum(rev_scores) / len(rev_scores)
        print(f"  Mean parse quality (reversed): {rev_mean:.2f} / 3.0")

    # Show some examples of words that parse ONLY when reversed
    rev_only = []
    for w in sorted(all_words):
        _, _, _, ok_ltr = parse_word_ltr(w)
        _, _, _, ok_rev = parse_word_reversed(w)
        if ok_rev and not ok_ltr:
            rev_only.append(w)

    ltr_only = []
    for w in sorted(all_words):
        _, _, _, ok_ltr = parse_word_ltr(w)
        _, _, _, ok_rev = parse_word_reversed(w)
        if ok_ltr and not ok_rev:
            ltr_only.append(w)

    print(f"\n  Words that parse ONLY as LTR:     {len(ltr_only)}")
    print(f"  Words that parse ONLY as reversed: {len(rev_only)}")
    print(f"  Words that parse BOTH ways:        {total - len(ltr_only) - len(rev_only) - (total - ltr_success - (rev_success - len(rev_only)))}")

    if rev_only:
        print(f"\n  Examples of reverse-only parses (word → reversed → parse):")
        for w in rev_only[:15]:
            pf, root, sf, _ = parse_word_reversed(w)
            print(f"    {w} → {w[::-1]} → prefix='{pf}' root='{root}' suffix='{sf}'")


def test2_character_distribution_asymmetry(sentences):
    """Check if character distributions at word-start vs word-end are asymmetric
    in a way that reveals reading direction. Natural languages have different
    initial vs final character distributions."""
    print("\n" + "=" * 72)
    print("TEST 2: CHARACTER DISTRIBUTION ASYMMETRY (INITIAL vs FINAL)")
    print("=" * 72)

    all_words = []
    for s in sentences:
        all_words.extend(s["words"])

    # Character at position 0 (word-initial)
    initial_chars = Counter()
    # Character at position -1 (word-final)
    final_chars = Counter()
    # Bigram at word start (first 2 chars)
    initial_bigrams = Counter()
    # Bigram at word end (last 2 chars)
    final_bigrams = Counter()

    for w in all_words:
        if len(w) >= 1:
            initial_chars[w[0]] += 1
            final_chars[w[-1]] += 1
        if len(w) >= 2:
            initial_bigrams[w[:2]] += 1
            final_bigrams[w[-2:]] += 1

    # Entropy of initial vs final distributions
    def entropy(counter):
        total = sum(counter.values())
        return -sum((c/total) * math.log2(c/total)
                    for c in counter.values() if c > 0)

    init_H = entropy(initial_chars)
    final_H = entropy(final_chars)

    print(f"\n  Initial character entropy: {init_H:.3f} bits")
    print(f"  Final character entropy:   {final_H:.3f} bits")
    print(f"  Difference (init - final): {init_H - final_H:.3f} bits")

    # In most LTR scripts: initial entropy < final entropy (prefixes are more
    # constrained than suffixes). In RTL script transcribed as LTR: reversed.
    if init_H < final_H:
        print(f"  → Initial MORE constrained — typical of LTR prefix system")
    else:
        print(f"  → Final MORE constrained — typical of RTL suffix system (or LTR with rich suffixes)")

    print(f"\n  Top 10 initial characters:")
    total_init = sum(initial_chars.values())
    for ch, cnt in initial_chars.most_common(10):
        print(f"    '{ch}': {cnt} ({100*cnt/total_init:.1f}%)")

    print(f"\n  Top 10 final characters:")
    total_final = sum(final_chars.values())
    for ch, cnt in final_chars.most_common(10):
        print(f"    '{ch}': {cnt} ({100*cnt/total_final:.1f}%)")

    init_bH = entropy(initial_bigrams)
    final_bH = entropy(final_bigrams)
    print(f"\n  Initial bigram entropy: {init_bH:.3f} bits")
    print(f"  Final bigram entropy:   {final_bH:.3f} bits")


def test3_bigram_reversal(sentences):
    """Compare inter-word bigram patterns: LTR vs RTL word order.
    Check if reversed word order produces more natural bigram distributions."""
    print("\n" + "=" * 72)
    print("TEST 3: WORD-ORDER BIGRAM PATTERNS (LTR vs RTL)")
    print("=" * 72)

    # Compute word bigrams in both directions
    ltr_bigrams = Counter()
    rtl_bigrams = Counter()

    for s in sentences:
        words = s["words"]
        for i in range(len(words) - 1):
            ltr_bigrams[(words[i], words[i+1])] += 1
            rtl_bigrams[(words[i+1], words[i])] += 1

    # Both distributions should be identical in total — they're just reversed.
    # The interesting test: which direction produces more REPEATED bigrams?
    # Natural language has preferred word sequences; random order doesn't.

    ltr_repeated = sum(1 for _, c in ltr_bigrams.items() if c > 1)
    rtl_repeated = sum(1 for _, c in rtl_bigrams.items() if c > 1)

    print(f"\n  Unique word bigrams (LTR): {len(ltr_bigrams)}")
    print(f"  Bigrams occurring >1 (LTR): {ltr_repeated}")
    print(f"  Bigrams occurring >1 (RTL): {rtl_repeated}")

    # Top bigrams LTR
    print(f"\n  Top 15 word bigrams (LTR = assumed reading direction):")
    for (w1, w2), c in ltr_bigrams.most_common(15):
        print(f"    {w1} → {w2}: {c}")

    print(f"\n  Top 15 word bigrams (RTL = reversed reading direction):")
    for (w1, w2), c in rtl_bigrams.most_common(15):
        print(f"    {w1} → {w2}: {c}")

    # Bigram entropy (lower = more structured)
    def bigram_entropy(bigrams):
        total = sum(bigrams.values())
        return -sum((c/total) * math.log2(c/total) for c in bigrams.values() if c > 0)

    ltr_H = bigram_entropy(ltr_bigrams)
    rtl_H = bigram_entropy(rtl_bigrams)
    print(f"\n  Word bigram entropy (LTR): {ltr_H:.3f} bits")
    print(f"  Word bigram entropy (RTL): {rtl_H:.3f} bits")
    print(f"  Note: these should be identical by symmetry — checking...")

    # More meaningful: first-word and last-word distributions
    # In natural language, sentence-initial and sentence-final words
    # are different populations. Which direction shows more constrained
    # opener/closer sets?

    ltr_openers = Counter()
    ltr_closers = Counter()
    rtl_openers = Counter()
    rtl_closers = Counter()

    for s in sentences:
        if len(s["words"]) >= 2:
            ltr_openers[s["words"][0]] += 1
            ltr_closers[s["words"][-1]] += 1
            rtl_openers[s["words"][-1]] += 1
            rtl_closers[s["words"][0]] += 1

    def top_coverage(counter, n=5):
        total = sum(counter.values())
        top_n = sum(c for _, c in counter.most_common(n))
        return 100 * top_n / total if total else 0

    print(f"\n  Opener concentration (top-5 cover what % of lines?):")
    print(f"    LTR openers: {top_coverage(ltr_openers):.1f}%  ({ltr_openers.most_common(3)})")
    print(f"    RTL openers: {top_coverage(rtl_openers):.1f}%  ({rtl_openers.most_common(3)})")
    print(f"\n  Closer concentration (top-5 cover what %):")
    print(f"    LTR closers: {top_coverage(ltr_closers):.1f}%  ({ltr_closers.most_common(3)})")
    print(f"    RTL closers: {top_coverage(rtl_closers):.1f}%  ({rtl_closers.most_common(3)})")

    ltr_opener_H = entropy_from_counter(ltr_openers)
    rtl_opener_H = entropy_from_counter(rtl_openers)
    ltr_closer_H = entropy_from_counter(ltr_closers)
    rtl_closer_H = entropy_from_counter(rtl_closers)

    print(f"\n  Opener entropy:  LTR={ltr_opener_H:.3f}  RTL={rtl_opener_H:.3f}")
    print(f"  Closer entropy:  LTR={ltr_closer_H:.3f}  RTL={rtl_closer_H:.3f}")
    print(f"\n  Lower entropy = more structured = more likely real openers/closers")
    if ltr_opener_H < rtl_opener_H:
        print(f"  → LTR openers more constrained — supports LTR reading")
    else:
        print(f"  → RTL openers more constrained — supports RTL reading")


def entropy_from_counter(counter):
    total = sum(counter.values())
    if total == 0:
        return 0
    return -sum((c/total) * math.log2(c/total) for c in counter.values() if c > 0)


def test4_prefix_suffix_diagnostics(sentences):
    """Deep dive: are the morphemes we call "prefixes" really initial?
    Check if they appear more consistently at word-start vs word-end.
    A TRUE prefix should have near-100% word-initial occurrence."""
    print("\n" + "=" * 72)
    print("TEST 4: PREFIX/SUFFIX POSITION FIDELITY")
    print("=" * 72)

    all_words = []
    for s in sentences:
        all_words.extend(s["words"])
    word_freq = Counter(all_words)
    vocab = set(word_freq.keys())

    # Check each "prefix": how often at word-start vs word-end?
    print(f"\n  Testing claimed prefixes — are they really word-initial?")
    print(f"  {'Prefix':8s}  {'At start':>10s}  {'At end':>10s}  {'In middle':>10s}  {'Start %':>10s}")
    for pf in PREFIXES_LTR:
        at_start = sum(1 for w in vocab if w.startswith(pf) and len(w) > len(pf))
        at_end = sum(1 for w in vocab if w.endswith(pf) and len(w) > len(pf))
        # In middle = contains it but not at start or end
        in_mid = sum(1 for w in vocab
                    if pf in w[1:-len(pf) if len(pf) > 0 else None]
                    and not w.startswith(pf) and not w.endswith(pf)
                    and len(w) > len(pf) * 2)
        total = at_start + at_end + in_mid
        pct = 100 * at_start / total if total else 0
        print(f"  {pf:8s}  {at_start:10d}  {at_end:10d}  {in_mid:10d}  {pct:9.1f}%")

    print(f"\n  Testing claimed suffixes — are they really word-final?")
    print(f"  {'Suffix':8s}  {'At end':>10s}  {'At start':>10s}  {'In middle':>10s}  {'End %':>10s}")
    for sf in SUFFIXES_LTR[:15]:  # Top 15
        at_end = sum(1 for w in vocab if w.endswith(sf) and len(w) > len(sf))
        at_start = sum(1 for w in vocab if w.startswith(sf) and len(w) > len(sf))
        in_mid = 0  # Simplified — middle counting is complex for variable-length
        total = at_start + at_end
        pct = 100 * at_end / total if total else 0
        print(f"  {sf:8s}  {at_end:10d}  {at_start:10d}  {in_mid:10d}  {pct:9.1f}%")


def test5_palindrome_and_symmetry(sentences):
    """Check for palindromic words and near-palindromes. A script that's
    actually RTL but transcribed LTR would produce false palindromes at
    the boundary between LTR and RTL text segments."""
    print("\n" + "=" * 72)
    print("TEST 5: PALINDROMES AND WORD SYMMETRY")
    print("=" * 72)

    all_words = []
    for s in sentences:
        all_words.extend(s["words"])
    word_freq = Counter(all_words)

    palindromes = []
    near_palindromes = []
    for w in set(all_words):
        if len(w) < 3:
            continue
        rev = w[::-1]
        if w == rev:
            palindromes.append(w)
        elif rev in word_freq:
            near_palindromes.append((w, rev))

    print(f"\n  True palindromes (word == reversed): {len(palindromes)}")
    if palindromes:
        pal_sorted = sorted(palindromes, key=lambda w: -word_freq[w])
        for w in pal_sorted[:20]:
            print(f"    {w} (freq={word_freq[w]})")

    print(f"\n  Reverse-pair words (w and w[::-1] both exist): {len(near_palindromes)}")
    if near_palindromes:
        # Sort by combined frequency
        near_pal_sorted = sorted(near_palindromes,
                                 key=lambda x: -(word_freq[x[0]] + word_freq[x[1]]))
        # Deduplicate (a,b) and (b,a)
        seen = set()
        for w, rev in near_pal_sorted[:30]:
            pair = tuple(sorted([w, rev]))
            if pair in seen:
                continue
            seen.add(pair)
            print(f"    {w} ({word_freq[w]}) ↔ {rev} ({word_freq[rev]})")


def test6_paragraph_marker_direction(sentences):
    """Check paragraph markers (<%>) — do they appear at what transcribers
    call "line start"? If so, and the text is RTL, these markers are at
    the RIGHT side of the physical manuscript (which would be paragraph start
    in RTL scripts like Hebrew)."""
    print("\n" + "=" * 72)
    print("TEST 6: PARAGRAPH MARKER ANALYSIS")
    print("=" * 72)

    folio_dir = Path("folios")
    para_data = {
        "left_marker": 0,   # <%> appears at line start in transcription
        "right_marker": 0,  # <%> appears at line end in transcription
        "total_lines": 0,
        "para_starts": 0,
    }

    # Also check: do paragraph-initial words differ from regular line-initial words?
    para_first_words = Counter()
    non_para_first_words = Counter()

    for txt_file in sorted(folio_dir.glob("*.txt")):
        lines = txt_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            m = re.match(r'<([^>]+)>\s*(.*)', line)
            if not m:
                continue
            text = m.group(2)
            para_data["total_lines"] += 1

            # Check for paragraph markers
            if "<%>" in text or "<$>" in text:
                para_data["para_starts"] += 1
                # Where in the raw text? At start or end?
                stripped = text.strip()
                if stripped.startswith("<%>") or stripped.startswith("<$>"):
                    para_data["left_marker"] += 1
                if stripped.endswith("<%>") or stripped.endswith("<$>"):
                    para_data["right_marker"] += 1

    print(f"\n  Total transcribed lines: {para_data['total_lines']}")
    print(f"  Lines with paragraph markers: {para_data['para_starts']}")
    print(f"  Marker at LEFT (transcription start): {para_data['left_marker']}")
    print(f"  Marker at RIGHT (transcription end):  {para_data['right_marker']}")

    if para_data["left_marker"] > para_data["right_marker"]:
        print(f"\n  Paragraph markers are transcribed as LEFT-aligned.")
        print(f"  In LTR: this = paragraph start (normal)")
        print(f"  In RTL: this = paragraph END (unusual — would expect right-aligned)")
        print(f"  → Supports LTR reading OR transcription convention masks true direction")
    else:
        print(f"\n  Paragraph markers show mixed or right-aligned pattern.")

    # More informative: analyze paragraph-first words vs line-first words
    para_initial = Counter()
    line_initial = Counter()

    for s in sentences:
        if s["words"]:
            if s["has_para_start"]:
                para_initial[s["words"][0]] += 1
            else:
                line_initial[s["words"][0]] += 1

    print(f"\n  Paragraph-initial words (top 10):")
    for w, c in para_initial.most_common(10):
        print(f"    {w}: {c}")
    print(f"\n  Non-paragraph line-initial words (top 10):")
    for w, c in line_initial.most_common(10):
        print(f"    {w}: {c}")

    # Check if paragraph-initial and line-final overlap (would suggest RTL)
    para_set = set(w for w, c in para_initial.most_common(20))
    line_final = Counter()
    for s in sentences:
        if s["words"]:
            line_final[s["words"][-1]] += 1
    final_set = set(w for w, c in line_final.most_common(20))

    overlap = para_set & final_set
    print(f"\n  Top-20 para-initial ∩ top-20 line-final: {len(overlap)} words")
    if overlap:
        print(f"    {overlap}")
    print(f"  (High overlap would suggest para markers are at line END = possible RTL)")


def test7_character_bigram_direction(sentences):
    """Compute character-level bigram entropy in both directions.
    LTR character bigrams should have lower entropy if text is LTR
    (because the parser models LTR patterns)."""
    print("\n" + "=" * 72)
    print("TEST 7: CHARACTER-LEVEL BIGRAM ENTROPY")
    print("=" * 72)

    all_words = []
    for s in sentences:
        all_words.extend(s["words"])

    ltr_bigrams = Counter()
    rtl_bigrams = Counter()

    for w in all_words:
        for i in range(len(w) - 1):
            ltr_bigrams[(w[i], w[i+1])] += 1
            rtl_bigrams[(w[i+1], w[i])] += 1

    ltr_H = entropy_from_counter(ltr_bigrams)
    rtl_H = entropy_from_counter(rtl_bigrams)

    print(f"\n  LTR character bigram entropy: {ltr_H:.3f} bits")
    print(f"  RTL character bigram entropy: {rtl_H:.3f} bits")

    # These should be identical by symmetry — but wait, word boundaries
    # break the symmetry. Let's also check across word boundaries.
    ltr_cross = Counter()
    rtl_cross = Counter()

    for s in sentences:
        words = s["words"]
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i+1]
            if w1 and w2:
                ltr_cross[(w1[-1], w2[0])] += 1
                rtl_cross[(w2[-1], w1[0])] += 1

    ltr_cross_H = entropy_from_counter(ltr_cross)
    rtl_cross_H = entropy_from_counter(rtl_cross)

    print(f"\n  Cross-word boundary bigram entropy:")
    print(f"    LTR (last_char → first_char of next): {ltr_cross_H:.3f} bits")
    print(f"    RTL (last_char of next → first_char):  {rtl_cross_H:.3f} bits")
    if ltr_cross_H < rtl_cross_H:
        print(f"    → LTR cross-boundary MORE structured — supports LTR")
    elif rtl_cross_H < ltr_cross_H:
        print(f"    → RTL cross-boundary MORE structured — supports RTL")
    else:
        print(f"    → Equal — no directional signal from cross-boundary bigrams")

    # Most important: word-final → word-initial character preferences
    print(f"\n  Top 10 cross-word bigrams (LTR: end_of_word → start_of_next):")
    for (c1, c2), cnt in ltr_cross.most_common(10):
        print(f"    '{c1}' → '{c2}': {cnt}")

    print(f"\n  Top 10 cross-word bigrams (RTL: end_of_next → start_of_word):")
    for (c1, c2), cnt in rtl_cross.most_common(10):
        print(f"    '{c1}' → '{c2}': {cnt}")


def test8_synthesis(sentences):
    """Pull everything together."""
    print("\n" + "=" * 72)
    print("TEST 8: RTL SYNTHESIS")
    print("=" * 72)

    print(f"\n  The RTL hypothesis predicts:")
    print(f"    1. Reversed words should parse ≥ as well as LTR words")
    print(f"    2. 'Suffixes' should be more position-constrained than 'prefixes'")
    print(f"    3. Word-final characters should be more diverse than word-initial")
    print(f"    4. Paragraph markers should align with RTL conventions")
    print(f"    5. Line-final words should function as openers")
    print(f"\n  Evidence assessment printed above — check each test result.")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Extracting sentences from all folios...\n")
    sentences = extract_sentences()
    print(f"Total sentences/lines: {len(sentences)}")
    total_words = sum(len(s["words"]) for s in sentences)
    print(f"Total words: {total_words}\n")

    test1_parse_rate_comparison(sentences)
    test2_character_distribution_asymmetry(sentences)
    test3_bigram_reversal(sentences)
    test4_prefix_suffix_diagnostics(sentences)
    test5_palindrome_and_symmetry(sentences)
    test6_paragraph_marker_direction(sentences)
    test7_character_bigram_direction(sentences)
    test8_synthesis(sentences)

    print("\n" + "=" * 72)
    print("RTL test complete.")
    print("=" * 72)
