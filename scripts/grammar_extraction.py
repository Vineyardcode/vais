#!/usr/bin/env python3
"""
Voynich Manuscript — Ring Text Grammar Extraction

Analyzes the 36 @Cc ring texts as SENTENCES to extract:
  1. Word-class tagging (function / content / prefix-article / suffix-class)
  2. Clause segmentation (comma boundaries, formulaic openers)
  3. Positional grammar (what classes appear where in sentences?)
  4. Adjacency rules (what word classes follow what?)
  5. Agreement patterns (do suffix-matched words cluster?)
  6. Sentence templates (recurring word-class sequences)
  7. Function-word distribution analysis (aiin/al/ar/dal/s/am contexts)
  8. Comparison: ring sentence grammar vs. expected natural-language patterns
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations

# ── Reuse core infrastructure from ring_text_analysis.py ─────────────────

ZODIAC_FILES = [
    "folios/f70v_part.txt",
    "folios/f71r.txt",
    "folios/f71v_72r.txt",
    "folios/f72v_part.txt",
    "folios/f73r.txt",
    "folios/f73v.txt",
]

FOLIO_SIGN = {
    "f70v1": "Aries",   "f70v2": "Pisces",
    "f71r":  "Aries",   "f71v":  "Taurus",
    "f72r1": "Taurus",  "f72r2": "Gemini",
    "f72r3": "Cancer",
    "f72v1": "Libra",   "f72v2": "Virgo",   "f72v3": "Leo",
    "f73r":  "Scorpio", "f73v":  "Sagittarius",
}

SIGN_ORDER = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Pisces"]

# ── Morphological parser ─────────────────────────────────────────────────

PREFIXES  = ["qo", "q", "do", "dy", "so", "sy", "ol", "or", "o", "y", "d", "s"]
ROOT_ONSETS = [
    "ckh","cth","cph","cfh","sch","sh","ch","f","p","k","t",
    "eee","ee","e","da","sa","a","o"
]
ROOT_BODIES = [
    "eee","ee","e","da","sa","do","so","a","o",
    "d","s","l","r","n","m"
]
SUFFIXES_LIST = [
    "aiin","aiir","ain","air","am","an","ar","al","as",
    "iin","iir","in","ir","dy","ey","ly","ry","ny","my",
    "or","ol","od","os","edy","eedy","y","d","l","r","s","g"
]

def parse_word(word):
    best = None
    for pf in PREFIXES + [""]:
        if not word.startswith(pf):
            continue
        rest = word[len(pf):]
        for ro in ROOT_ONSETS:
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
            for sf in SUFFIXES_LIST + [""]:
                if tail == sf:
                    score = (len(pf) > 0) + (len(root_str) > 0) + (len(sf) > 0)
                    if best is None or score > best[3]:
                        best = (pf, root_str, sf, score)
    if best:
        return best[0], best[1], best[2], True
    return "", word, "", False


# ── Text extraction ──────────────────────────────────────────────────────

def clean_word(w):
    w = re.sub(r'\[([^:]+):[^\]]+\]', r'\1', w)
    w = re.sub(r'\{([^}]+)\}', r'\1', w)
    w = re.sub(r'@\d+;', '', w)
    w = re.sub(r'<![^>]*>', '', w)
    w = w.replace('?', '')
    w = w.strip(",'")
    return w


def extract_ring_texts():
    """Extract all @Cc ring text lines, preserving comma structure."""
    ring_texts = []

    for filepath in ZODIAC_FILES:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "@Cc>" not in line:
                    continue

                m = re.match(r'<([^,]+),@Cc>\s+(.+)', line)
                if not m:
                    continue

                folio_line = m.group(1)
                content = m.group(2)

                folio_match = re.match(r'(f\d+[rv]\d?)', folio_line)
                folio_id = folio_match.group(1) if folio_match else folio_line.split('.')[0]
                sign = FOLIO_SIGN.get(folio_id, "Unknown")

                clock_match = re.search(r'<!(\d+:\d+)>', content)
                clock_pos = clock_match.group(1) if clock_match else "?"

                text = re.sub(r'<!\d+:\d+[^>]*>', '', content).strip()
                # Also remove after-gap type markers
                text = re.sub(r'<!long gap>', '', text).strip()
                text = re.sub(r'<!hole>', '', text).strip()

                # Split on dots first (IVTFF word separator)
                raw_tokens = re.split(r'\.', text)

                # For each token, split on commas to get sub-words,
                # but also record comma positions for clause boundary analysis
                words = []
                comma_positions = []  # indices where a comma preceded the word
                for tok in raw_tokens:
                    parts = tok.split(',')
                    for j, part in enumerate(parts):
                        cleaned = clean_word(part)
                        if cleaned and len(cleaned) > 0:
                            if j > 0:
                                comma_positions.append(len(words))
                            words.append(cleaned)

                ring_texts.append({
                    "folio_line": folio_line,
                    "folio_id": folio_id,
                    "sign": sign,
                    "clock_pos": clock_pos,
                    "raw_text": text,
                    "words": words,
                    "comma_positions": comma_positions,
                    "word_count": len(words),
                })

    # Assign ring indices per folio section
    by_folio = defaultdict(list)
    for rt in ring_texts:
        by_folio[rt["folio_id"]].append(rt)
    for folio_id, texts in by_folio.items():
        for i, rt in enumerate(texts):
            rt["ring_idx"] = i

    return ring_texts


# ── Word classification ──────────────────────────────────────────────────

# Function words: high-frequency, unparseable or minimal structure,
# appear across many signs, never as nymph labels
FUNCTION_WORDS = {
    "aiin", "ar", "al", "s", "daiin", "y", "dal", "am",
    "r", "or", "ol", "daiir", "sal", "shal", "dar",
    "d", "l", "dair", "sar", "dy",
}

# Extended: words that might be function words based on frequency + distribution
MAYBE_FUNCTION = {"shey", "chey", "chy", "air"}


def classify_word(word):
    """
    Classify a word into grammatical categories.
    Returns a dict with classification info.
    """
    if word in FUNCTION_WORDS:
        wclass = "FUNC"
    elif word in MAYBE_FUNCTION:
        wclass = "FUNC?"
    elif len(word) <= 2:
        wclass = "PART"  # particle / abbreviation
    else:
        wclass = "CONT"  # content word

    prefix, root, suffix, parsed = parse_word(word)

    # Sub-classify content words
    if wclass == "CONT":
        if prefix.startswith("o"):
            wclass = "O-CONT"   # o-prefixed content (definite/article)
        elif prefix.startswith("q"):
            wclass = "Q-CONT"   # q-prefixed content (rare, perhaps interrogative?)
        elif prefix in ("d", "do", "dy"):
            wclass = "D-CONT"   # d-prefixed
        elif prefix in ("s", "so", "sy"):
            wclass = "S-CONT"   # s-prefixed
        elif prefix in ("y",):
            wclass = "Y-CONT"   # y-prefixed
        elif prefix == "":
            wclass = "BARE"     # bare content word (no prefix)
        # else stays CONT

    # Suffix class
    if suffix in ("aiin", "ain", "aiir"):
        suf_class = "-AIIN"
    elif suffix in ("iin", "iir", "in", "ir"):
        suf_class = "-IIN"
    elif suffix in ("ey", "y", "eedy", "edy", "dy"):
        suf_class = "-Y"
    elif suffix in ("ar", "air", "or"):
        suf_class = "-R"
    elif suffix in ("al", "ol"):
        suf_class = "-L"
    elif suffix in ("am", "an"):
        suf_class = "-M/N"
    elif suffix in ("as", "os", "s"):
        suf_class = "-S"
    elif suffix == "":
        suf_class = "∅"
    else:
        suf_class = f"-{suffix}"

    return {
        "word": word,
        "class": wclass,
        "prefix": prefix,
        "root": root,
        "suffix": suffix,
        "suf_class": suf_class,
        "parsed": parsed,
    }


# ── Coarse word class for template extraction ────────────────────────────

def coarse_class(wclass):
    """Map detailed class to coarse for template matching."""
    if wclass in ("FUNC", "FUNC?", "PART"):
        return "F"
    elif wclass == "O-CONT":
        return "O"
    elif wclass == "Q-CONT":
        return "Q"
    elif wclass in ("D-CONT", "S-CONT", "Y-CONT"):
        return "P"  # other-prefix content
    elif wclass == "BARE":
        return "B"
    else:
        return "C"  # generic content


# ══════════════════════════════════════════════════════════════════════════
# PHASES
# ══════════════════════════════════════════════════════════════════════════

def phase1_word_class_profile(ring_texts):
    """Tag every word and profile the distribution of classes."""
    print("=" * 72)
    print("PHASE 1: WORD-CLASS TAGGING")
    print("=" * 72)

    all_classified = []
    class_counts = Counter()
    suf_counts = Counter()

    for rt in ring_texts:
        classified = [classify_word(w) for w in rt["words"]]
        rt["classified"] = classified
        all_classified.extend(classified)
        for c in classified:
            class_counts[c["class"]] += 1
            suf_counts[c["suf_class"]] += 1

    total = len(all_classified)
    print(f"\nTotal words classified: {total}")

    print(f"\n  Word class distribution:")
    for cls, count in class_counts.most_common():
        pct = 100 * count / total
        print(f"    {cls:10s}  {count:4d}  ({pct:5.1f}%)")

    print(f"\n  Suffix class distribution:")
    for sc, count in suf_counts.most_common(12):
        pct = 100 * count / total
        print(f"    {sc:10s}  {count:4d}  ({pct:5.1f}%)")

    # Show the coarse class distribution
    coarse = Counter()
    for c in all_classified:
        coarse[coarse_class(c["class"])] += 1
    print(f"\n  Coarse classes (for templates):")
    for cc, count in coarse.most_common():
        label = {"F": "Function", "O": "o-Content", "B": "Bare content",
                 "P": "Other-prefix", "Q": "q-Content", "C": "Generic"}[cc]
        pct = 100 * count / total
        print(f"    {cc} ({label:15s})  {count:4d}  ({pct:5.1f}%)")

    return all_classified


def phase2_positional_grammar(ring_texts):
    """Where in sentences do different word classes appear?"""
    print("\n" + "=" * 72)
    print("PHASE 2: POSITIONAL GRAMMAR")
    print("=" * 72)

    # Normalize positions to 0.0-1.0 range within each sentence
    class_positions = defaultdict(list)
    # Also: absolute positions from start (first 5) and from end (last 5)
    class_from_start = defaultdict(Counter)
    class_from_end = defaultdict(Counter)

    for rt in ring_texts:
        n = len(rt["classified"])
        if n < 3:
            continue
        for i, c in enumerate(rt["classified"]):
            cls = coarse_class(c["class"])
            norm_pos = i / (n - 1) if n > 1 else 0.5
            class_positions[cls].append(norm_pos)
            if i < 5:
                class_from_start[cls][i] += 1
            if (n - 1 - i) < 5:
                class_from_end[cls][n - 1 - i] += 1

    print("\n  Mean normalized position (0.0=start, 1.0=end):")
    for cls in sorted(class_positions.keys()):
        positions = class_positions[cls]
        mean_pos = sum(positions) / len(positions)
        # Compute quartiles
        positions.sort()
        q1 = positions[len(positions) // 4]
        median = positions[len(positions) // 2]
        q3 = positions[3 * len(positions) // 4]
        print(f"    {cls}  mean={mean_pos:.3f}  median={median:.3f}  "
              f"Q1={q1:.3f}  Q3={q3:.3f}  n={len(positions)}")

    # Opening word classes (position 0)
    print(f"\n  First word class distribution (position 0):")
    first_words = Counter()
    for rt in ring_texts:
        if rt["classified"]:
            cls = coarse_class(rt["classified"][0]["class"])
            first_words[cls] += 1
    for cls, count in first_words.most_common():
        pct = 100 * count / len(ring_texts)
        print(f"    {cls}  {count:3d}  ({pct:5.1f}%)")

    # Closing word classes
    print(f"\n  Last word class distribution (final position):")
    last_words = Counter()
    for rt in ring_texts:
        if rt["classified"]:
            cls = coarse_class(rt["classified"][-1]["class"])
            last_words[cls] += 1
    for cls, count in last_words.most_common():
        pct = 100 * count / len(ring_texts)
        print(f"    {cls}  {count:3d}  ({pct:5.1f}%)")

    # Second/third word
    print(f"\n  Second word class distribution (position 1):")
    second_words = Counter()
    for rt in ring_texts:
        if len(rt["classified"]) > 1:
            cls = coarse_class(rt["classified"][1]["class"])
            second_words[cls] += 1
    for cls, count in second_words.most_common():
        pct = 100 * count / len(ring_texts)
        print(f"    {cls}  {count:3d}  ({pct:5.1f}%)")


def phase3_adjacency_bigrams(ring_texts):
    """What word classes follow what? Build transition matrix."""
    print("\n" + "=" * 72)
    print("PHASE 3: WORD-CLASS TRANSITION MATRIX")
    print("=" * 72)

    transitions = Counter()
    total_pairs = 0

    for rt in ring_texts:
        classes = [coarse_class(c["class"]) for c in rt["classified"]]
        for i in range(len(classes) - 1):
            transitions[(classes[i], classes[i + 1])] += 1
            total_pairs += 1

    # Build matrix
    all_classes = sorted(set(c for pair in transitions for c in pair))
    print(f"\n  Transition counts (row → col)  [total pairs: {total_pairs}]")
    header = "      " + "".join(f"  {c:>5s}" for c in all_classes)
    print(header)
    for row in all_classes:
        row_total = sum(transitions.get((row, col), 0) for col in all_classes)
        cells = []
        for col in all_classes:
            count = transitions.get((row, col), 0)
            if row_total > 0:
                pct = 100 * count / row_total
                cells.append(f"{count:3d}/{pct:4.0f}%")
            else:
                cells.append(f"  0/  0%")
        print(f"  {row}  " + " ".join(cells))

    # Top transitions
    print(f"\n  Top 15 bigram transitions:")
    for (a, b), count in transitions.most_common(15):
        pct = 100 * count / total_pairs
        print(f"    {a} → {b}   {count:4d}  ({pct:5.1f}%)")

    # Forbidden/rare transitions
    print(f"\n  Rare/absent transitions (expected but count ≤ 1):")
    for a in all_classes:
        for b in all_classes:
            if transitions.get((a, b), 0) <= 1:
                expected = (sum(transitions.get((a, x), 0) for x in all_classes)
                            * sum(transitions.get((x, b), 0) for x in all_classes)
                            / total_pairs) if total_pairs > 0 else 0
                if expected > 3:  # only flag if we'd expect at least 3
                    print(f"    {a} → {b}   count={transitions.get((a, b), 0)}"
                          f"   expected≈{expected:.1f}")

    return transitions


def phase4_function_word_contexts(ring_texts):
    """Deep analysis of each function word's immediate context."""
    print("\n" + "=" * 72)
    print("PHASE 4: FUNCTION WORD CONTEXT WINDOWS")
    print("=" * 72)

    # For each function word, collect its left and right neighbors
    target_funcs = ["aiin", "al", "ar", "s", "daiin", "dal", "am", "dar",
                    "y", "or", "ol", "dy", "r"]

    for func in target_funcs:
        left_words = Counter()
        right_words = Counter()
        left_classes = Counter()
        right_classes = Counter()
        positions_in_sent = []  # normalized 0-1
        occurrences = 0

        for rt in ring_texts:
            words = rt["words"]
            classes = rt["classified"]
            n = len(words)
            for i, w in enumerate(words):
                if w != func:
                    continue
                occurrences += 1
                positions_in_sent.append(i / (n - 1) if n > 1 else 0.5)

                if i > 0:
                    left_words[words[i - 1]] += 1
                    left_classes[coarse_class(classes[i - 1]["class"])] += 1
                else:
                    left_words["⟨START⟩"] += 1
                    left_classes["⟨S⟩"] += 1

                if i < n - 1:
                    right_words[words[i + 1]] += 1
                    right_classes[coarse_class(classes[i + 1]["class"])] += 1
                else:
                    right_words["⟨END⟩"] += 1
                    right_classes["⟨E⟩"] += 1

        if occurrences == 0:
            continue

        mean_pos = sum(positions_in_sent) / len(positions_in_sent)
        # Count how often sentence-final
        n_final = sum(1 for p in positions_in_sent if p > 0.95)

        print(f"\n  ── {func} ── (n={occurrences}, mean_pos={mean_pos:.2f},"
              f" final={n_final})")

        print(f"    Left context (word):  ", end="")
        for w, c in left_words.most_common(6):
            print(f"{w}({c})", end="  ")
        print()

        print(f"    Right context (word): ", end="")
        for w, c in right_words.most_common(6):
            print(f"{w}({c})", end="  ")
        print()

        print(f"    Left class:  ", end="")
        for cls, c in left_classes.most_common():
            print(f"{cls}({c})", end="  ")
        print()

        print(f"    Right class: ", end="")
        for cls, c in right_classes.most_common():
            print(f"{cls}({c})", end="  ")
        print()


def phase5_clause_segmentation(ring_texts):
    """Use commas and function words to identify clause boundaries."""
    print("\n" + "=" * 72)
    print("PHASE 5: CLAUSE SEGMENTATION")
    print("=" * 72)

    # Strategy: Split sentences at commas and at recurrent function word
    # sequences that look like clause connectors.
    # Then profile the internal structure of clauses.

    all_clauses = []
    clause_lengths = []

    for rt in ring_texts:
        words = rt["words"]
        classes = rt["classified"]
        comma_pos = set(rt.get("comma_positions", []))

        # Split at comma positions
        clauses = []
        current = []
        for i, (w, c) in enumerate(zip(words, classes)):
            if i in comma_pos and current:
                clauses.append(current)
                current = []
            current.append(c)
        if current:
            clauses.append(current)

        for cl in clauses:
            all_clauses.append(cl)
            clause_lengths.append(len(cl))

        rt["clauses"] = clauses

    print(f"\n  Total clauses (comma-split): {len(all_clauses)}")
    if clause_lengths:
        print(f"  Mean clause length: {sum(clause_lengths)/len(clause_lengths):.1f} words")
        print(f"  Median: {sorted(clause_lengths)[len(clause_lengths)//2]}")
        print(f"  Range: {min(clause_lengths)}-{max(clause_lengths)}")

    # Clause length distribution
    len_dist = Counter(clause_lengths)
    print(f"\n  Clause length distribution:")
    for length in sorted(len_dist.keys()):
        if length <= 15:
            print(f"    {length:2d} words: {'█' * len_dist[length]} ({len_dist[length]})")
        else:
            print(f"    {length:2d}+: {sum(v for k,v in len_dist.items() if k >= length)}")
            break

    # Clause-initial word class
    print(f"\n  Clause-initial word class:")
    init_cls = Counter()
    for cl in all_clauses:
        if cl:
            init_cls[coarse_class(cl[0]["class"])] += 1
    for cls, count in init_cls.most_common():
        pct = 100 * count / len(all_clauses)
        print(f"    {cls}  {count}  ({pct:.1f}%)")

    # Clause-final word class
    print(f"\n  Clause-final word class:")
    final_cls = Counter()
    for cl in all_clauses:
        if cl:
            final_cls[coarse_class(cl[-1]["class"])] += 1
    for cls, count in final_cls.most_common():
        pct = 100 * count / len(all_clauses)
        print(f"    {cls}  {count}  ({pct:.1f}%)")

    # Clause-internal patterns: what is the typical structure?
    print(f"\n  Most common clause templates (coarse class sequences):")
    templates = Counter()
    for cl in all_clauses:
        if len(cl) <= 8:  # only short-medium clauses
            template = " ".join(coarse_class(c["class"]) for c in cl)
            templates[template] += 1
    for template, count in templates.most_common(20):
        if count >= 2:
            print(f"    [{template}]  ×{count}")

    return all_clauses


def phase6_sentence_templates(ring_texts):
    """Extract recurring sentence-level templates."""
    print("\n" + "=" * 72)
    print("PHASE 6: SENTENCE-LEVEL TEMPLATES")
    print("=" * 72)

    # For each sentence, convert to coarse class sequence
    # Use sliding windows of 3, 4, 5 classes
    for window_size in (3, 4, 5):
        ngrams = Counter()
        for rt in ring_texts:
            classes = [coarse_class(c["class"]) for c in rt["classified"]]
            for i in range(len(classes) - window_size + 1):
                gram = " ".join(classes[i:i + window_size])
                ngrams[gram] += 1

        print(f"\n  {window_size}-gram class sequences (≥3 occurrences):")
        for gram, count in ngrams.most_common():
            if count < 3:
                break
            print(f"    {gram}  ×{count}")

    # Look for repeated exact word sequences (not just classes)
    print(f"\n  Exact word n-grams (n=2, ≥3 occurrences):")
    word_bigrams = Counter()
    for rt in ring_texts:
        words = rt["words"]
        for i in range(len(words) - 1):
            word_bigrams[(words[i], words[i+1])] += 1
    for (a, b), count in word_bigrams.most_common():
        if count < 3:
            break
        print(f"    '{a} {b}'  ×{count}")

    print(f"\n  Exact word n-grams (n=3, ≥2 occurrences):")
    word_trigrams = Counter()
    for rt in ring_texts:
        words = rt["words"]
        for i in range(len(words) - 2):
            word_trigrams[(words[i], words[i+1], words[i+2])] += 1
    for (a, b, c), count in word_trigrams.most_common():
        if count < 2:
            break
        print(f"    '{a} {b} {c}'  ×{count}")


def phase7_suffix_agreement(ring_texts):
    """Do adjacent content words show suffix agreement patterns?"""
    print("\n" + "=" * 72)
    print("PHASE 7: SUFFIX AGREEMENT PATTERNS")
    print("=" * 72)

    # For each pair of adjacent content words, check if suffixes match
    agreement_count = 0
    disagreement_count = 0
    adjacent_content = 0
    suf_pair_counts = Counter()

    for rt in ring_texts:
        classes = rt["classified"]
        for i in range(len(classes) - 1):
            c1, c2 = classes[i], classes[i + 1]
            # Both must be content words
            if c1["class"] in ("FUNC", "FUNC?", "PART") or \
               c2["class"] in ("FUNC", "FUNC?", "PART"):
                continue
            adjacent_content += 1
            s1, s2 = c1["suf_class"], c2["suf_class"]
            suf_pair_counts[(s1, s2)] += 1
            if s1 == s2 and s1 != "∅":
                agreement_count += 1
            else:
                disagreement_count += 1

    if adjacent_content > 0:
        agree_pct = 100 * agreement_count / adjacent_content
        print(f"\n  Adjacent content-word pairs: {adjacent_content}")
        print(f"  Suffix agreement: {agreement_count} ({agree_pct:.1f}%)")
        print(f"  Suffix disagreement: {disagreement_count}")

    # Expected agreement by chance
    suf_dist = Counter()
    for rt in ring_texts:
        for c in rt["classified"]:
            if c["class"] not in ("FUNC", "FUNC?", "PART"):
                suf_dist[c["suf_class"]] += 1
    total_content = sum(suf_dist.values())
    expected = sum((count / total_content) ** 2 for count in suf_dist.values())
    print(f"  Expected agreement by chance: {100 * expected:.1f}%")
    if adjacent_content > 0:
        ratio = agree_pct / (100 * expected) if expected > 0 else 0
        print(f"  Observed/Expected ratio: {ratio:.2f}×")
        if ratio > 1.5:
            print(f"  → SUFFIX AGREEMENT DETECTED (words with matching suffixes cluster)")
        elif ratio < 0.7:
            print(f"  → SUFFIX ANTI-AGREEMENT (adjacent words tend to have DIFFERENT suffixes)")
        else:
            print(f"  → Near chance levels")

    # Top suffix pair transitions
    print(f"\n  Top suffix-pair transitions (content → content):")
    for (s1, s2), count in suf_pair_counts.most_common(15):
        pct = 100 * count / adjacent_content if adjacent_content else 0
        marker = " ←AGREE" if s1 == s2 and s1 != "∅" else ""
        print(f"    {s1:8s} → {s2:8s}  {count:3d}  ({pct:4.1f}%){marker}")

    # Window-based: do words 2-3 apart also show agreement?
    print(f"\n  Agreement at distance 2 (skip-1):")
    skip1_agree = 0
    skip1_total = 0
    for rt in ring_texts:
        classes = rt["classified"]
        for i in range(len(classes) - 2):
            c1, c3 = classes[i], classes[i + 2]
            if c1["class"] in ("FUNC", "FUNC?", "PART") or \
               c3["class"] in ("FUNC", "FUNC?", "PART"):
                continue
            skip1_total += 1
            if c1["suf_class"] == c3["suf_class"] and c1["suf_class"] != "∅":
                skip1_agree += 1
    if skip1_total > 0:
        skip1_pct = 100 * skip1_agree / skip1_total
        skip1_ratio = skip1_pct / (100 * expected) if expected > 0 else 0
        print(f"    Pairs: {skip1_total}, agreement: {skip1_agree} ({skip1_pct:.1f}%)"
              f"  ratio={skip1_ratio:.2f}×")


def phase8_sentence_structure_typology(ring_texts):
    """Classify sentences into structural types based on class patterns."""
    print("\n" + "=" * 72)
    print("PHASE 8: SENTENCE STRUCTURE TYPOLOGY")
    print("=" * 72)

    # Compute ratio of function words, o-content, bare content per sentence
    type_features = []
    for rt in ring_texts:
        classes = rt["classified"]
        n = len(classes)
        if n < 3:
            continue
        n_func = sum(1 for c in classes if coarse_class(c["class"]) == "F")
        n_ocont = sum(1 for c in classes if coarse_class(c["class"]) == "O")
        n_bare = sum(1 for c in classes if coarse_class(c["class"]) == "B")
        n_pref = sum(1 for c in classes if coarse_class(c["class"]) == "P")

        type_features.append({
            "folio": rt["folio_line"],
            "sign": rt["sign"],
            "ring": rt["ring_idx"],
            "n": n,
            "func_pct": 100 * n_func / n,
            "o_pct": 100 * n_ocont / n,
            "bare_pct": 100 * n_bare / n,
            "pref_pct": 100 * n_pref / n,
            "starts_with": coarse_class(classes[0]["class"]),
            "ends_with": coarse_class(classes[-1]["class"]),
            "first_word": rt["words"][0],
            "last_word": rt["words"][-1],
        })

    # Cluster by starting pattern
    by_start = defaultdict(list)
    for feat in type_features:
        by_start[feat["starts_with"]].append(feat)

    print(f"\n  Sentences by opening class:")
    for cls in sorted(by_start.keys()):
        items = by_start[cls]
        signs = Counter(f["sign"] for f in items)
        rings = Counter(f["ring"] for f in items)
        avg_func = sum(f["func_pct"] for f in items) / len(items)
        print(f"    Opens with {cls}: {len(items)} sentences"
              f"  avg func%={avg_func:.1f}%"
              f"  signs={dict(signs)}")

    # Check: do innermost rings have a consistent structure?
    print(f"\n  Structure by ring position:")
    by_ring = defaultdict(list)
    for feat in type_features:
        by_ring[feat["ring"]].append(feat)
    for ring_idx in sorted(by_ring.keys()):
        items = by_ring[ring_idx]
        avg_func = sum(f["func_pct"] for f in items) / len(items)
        avg_o = sum(f["o_pct"] for f in items) / len(items)
        avg_n = sum(f["n"] for f in items) / len(items)
        openers = Counter(f["first_word"] for f in items)
        closers = Counter(f["last_word"] for f in items)
        ring_label = ["Outer", "Middle", "Inner", "Innermost"][ring_idx] if ring_idx < 4 else f"Ring{ring_idx}"
        print(f"    {ring_label} (n={len(items)}): avg_len={avg_n:.0f}"
              f"  func%={avg_func:.1f}  o%={avg_o:.1f}")
        print(f"      Openers: {dict(openers.most_common(5))}")
        print(f"      Closers: {dict(closers.most_common(5))}")

    # Print full tagged sentences for the 3 shortest (innermost) rings
    print(f"\n  FULLY TAGGED SHORTEST SENTENCES:")
    shortest = sorted(type_features, key=lambda x: x["n"])[:6]
    for feat in shortest:
        folio = feat["folio"]
        # Find matching ring text
        for rt in ring_texts:
            if rt["folio_line"] == folio:
                break
        tagged = " ".join(
            f"{c['word']}[{coarse_class(c['class'])}{c['suf_class']}]"
            for c in rt["classified"]
        )
        print(f"\n    {folio} ({feat['sign']} ring{feat['ring']}, {feat['n']}w):")
        print(f"    {tagged}")


def phase9_comparative_syntax(ring_texts):
    """Compare ring text syntax to natural language expectations."""
    print("\n" + "=" * 72)
    print("PHASE 9: COMPARATIVE SYNTAX ANALYSIS")
    print("=" * 72)

    # In natural Semitic languages (Hebrew, Arabic):
    # - VSO or SVO word order
    # - Function words (articles, prepositions) precede nouns
    # - Construct state: NOUN-NOUN chains without articles
    # - Verb agrees with subject in gender/number
    #
    # If Voynichese is a Semitic-like constructed language:
    # - o- prefix = article → should precede content words
    # - Function words (al, ar, aiin) should appear between content chunks
    # - -y/-iin suffixes = gender → should show agreement

    # Test 1: Does o-prefix ALWAYS precede a content context?
    print(f"\n  Test 1: o-prefix content words and right neighbors")
    o_right = Counter()
    for rt in ring_texts:
        classes = rt["classified"]
        for i in range(len(classes) - 1):
            if coarse_class(classes[i]["class"]) == "O":
                right = coarse_class(classes[i + 1]["class"])
                o_right[right] += 1
    total_o = sum(o_right.values())
    for cls, count in o_right.most_common():
        pct = 100 * count / total_o if total_o else 0
        print(f"    o-CONT → {cls}  {count}  ({pct:.1f}%)")

    # Test 2: Function words between content blocks
    # Look at F-position: is F always between content words?
    print(f"\n  Test 2: Function word neighborhoods")
    f_context = Counter()
    for rt in ring_texts:
        classes = rt["classified"]
        for i in range(len(classes)):
            if coarse_class(classes[i]["class"]) != "F":
                continue
            left = coarse_class(classes[i-1]["class"]) if i > 0 else "⟨S⟩"
            right = coarse_class(classes[i+1]["class"]) if i < len(classes) - 1 else "⟨E⟩"
            f_context[(left, right)] += 1
    print(f"    Left_of_F → F → Right_of_F:")
    for (l, r), count in f_context.most_common(12):
        print(f"    {l} → F → {r}   ×{count}")

    # Test 3: VERB-SUBJECT-OBJECT test
    # In a verbal system, the first content word should often be a "verb" (action)
    # We can't know verbs from nouns yet, but we can check: is the first
    # content word typically o-prefixed (=noun) or bare (=possible verb)?
    print(f"\n  Test 3: First content word in each sentence")
    first_content = Counter()
    for rt in ring_texts:
        for c in rt["classified"]:
            if coarse_class(c["class"]) not in ("F",):
                first_content[c["class"]] += 1
                break
    for cls, count in first_content.most_common():
        pct = 100 * count / sum(first_content.values())
        print(f"    {cls:10s}  {count}  ({pct:.1f}%)")

    # Test 4: Sentence-final words — languages tend to have consistent endings
    print(f"\n  Test 4: Sentence-final word suffix classes")
    final_suf = Counter()
    for rt in ring_texts:
        if rt["classified"]:
            final_suf[rt["classified"][-1]["suf_class"]] += 1
    for sc, count in final_suf.most_common():
        pct = 100 * count / len(ring_texts)
        print(f"    {sc:10s}  {count}  ({pct:.1f}%)")

    # Test 5: Content-Function alternation rate
    # Natural languages tend to alternate between content and function words
    # Gibberish would show random alternation
    print(f"\n  Test 5: Content↔Function alternation rate")
    alternations = 0
    non_alternations = 0
    for rt in ring_texts:
        classes = [coarse_class(c["class"]) for c in rt["classified"]]
        binary = ["F" if c == "F" else "C" for c in classes]
        for i in range(len(binary) - 1):
            if binary[i] != binary[i + 1]:
                alternations += 1
            else:
                non_alternations += 1
    total_trans = alternations + non_alternations
    if total_trans > 0:
        alt_rate = 100 * alternations / total_trans
        print(f"    Alternations: {alternations} ({alt_rate:.1f}%)")
        print(f"    Non-alternations: {non_alternations} ({100-alt_rate:.1f}%)")
        # Expected if random: 2 * p_func * p_content
        # Rough: ~16% function words, so expected alternation = 2*0.16*0.84 = 26.9%
        n_func_total = sum(1 for rt in ring_texts
                          for c in rt["classified"]
                          if coarse_class(c["class"]) == "F")
        n_total = sum(len(rt["classified"]) for rt in ring_texts)
        p_func = n_func_total / n_total if n_total > 0 else 0
        expected_alt = 200 * p_func * (1 - p_func)
        print(f"    Expected if random: {expected_alt:.1f}%")
        if alt_rate > expected_alt * 1.3:
            print(f"    → ELEVATED alternation: content-function-content rhythm")
        elif alt_rate < expected_alt * 0.7:
            print(f"    → REDUCED alternation: content words cluster together")
        else:
            print(f"    → Near random levels")


def phase10_synthesis(ring_texts):
    """Pull together findings into a grammatical model."""
    print("\n" + "=" * 72)
    print("PHASE 10: GRAMMATICAL MODEL SYNTHESIS")
    print("=" * 72)

    # Summarize findings
    # Count key stats for the synthesis
    all_words = [w for rt in ring_texts for w in rt["words"]]
    all_classes = [c for rt in ring_texts for c in rt["classified"]]

    n_func = sum(1 for c in all_classes if coarse_class(c["class"]) == "F")
    n_ocont = sum(1 for c in all_classes if coarse_class(c["class"]) == "O")
    n_bare = sum(1 for c in all_classes if coarse_class(c["class"]) == "B")
    n_other = len(all_classes) - n_func - n_ocont - n_bare

    print(f"\n  Corpus: {len(ring_texts)} sentences, {len(all_words)} words")
    print(f"  Function words: {n_func} ({100*n_func/len(all_words):.1f}%)")
    print(f"  o-content: {n_ocont} ({100*n_ocont/len(all_words):.1f}%)")
    print(f"  Bare content: {n_bare} ({100*n_bare/len(all_words):.1f}%)")
    print(f"  Other-prefixed: {n_other} ({100*n_other/len(all_words):.1f}%)")

    # Print all sentences as coarse class sequences for visual pattern scan
    print(f"\n  ALL SENTENCE CLASS SEQUENCES:")
    for rt in ring_texts:
        classes = [coarse_class(c["class"]) for c in rt["classified"]]
        seq = " ".join(classes)
        sign = rt["sign"][:3]
        ring = rt["ring_idx"]
        print(f"    {sign}r{ring} ({len(classes):2d}w): {seq}")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ring_texts = extract_ring_texts()
    print(f"Extracted {len(ring_texts)} ring text sentences\n")

    all_classified = phase1_word_class_profile(ring_texts)
    phase2_positional_grammar(ring_texts)
    transitions = phase3_adjacency_bigrams(ring_texts)
    phase4_function_word_contexts(ring_texts)
    all_clauses = phase5_clause_segmentation(ring_texts)
    phase6_sentence_templates(ring_texts)
    phase7_suffix_agreement(ring_texts)
    phase8_sentence_structure_typology(ring_texts)
    phase9_comparative_syntax(ring_texts)
    phase10_synthesis(ring_texts)

    # Save structured results
    results = {
        "n_sentences": len(ring_texts),
        "n_words": sum(len(rt["words"]) for rt in ring_texts),
        "tagged_sentences": [],
    }
    for rt in ring_texts:
        tagged = []
        for c in rt["classified"]:
            tagged.append({
                "word": c["word"],
                "class": c["class"],
                "coarse": coarse_class(c["class"]),
                "prefix": c["prefix"],
                "root": c["root"],
                "suffix": c["suffix"],
                "suf_class": c["suf_class"],
            })
        results["tagged_sentences"].append({
            "folio_line": rt["folio_line"],
            "sign": rt["sign"],
            "ring_idx": rt["ring_idx"],
            "words": rt["words"],
            "tagged": tagged,
            "comma_positions": rt.get("comma_positions", []),
        })

    with open("grammar_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\nResults saved to grammar_results.json")
