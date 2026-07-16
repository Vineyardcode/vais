#!/usr/bin/env python3
"""
Slot-Based Morphological Analysis

Based on the Zattera glyph-slot system, this decomposes every Voynich word
into its positional slot components (prefix / root / body / suffix / terminal)
and then runs distributional, paradigmatic, and entropy analyses to test
the prefix-root-suffix morphological theory.

Slot Map (Zattera):
  0: q, d, s          (initial consonant — PREFIX)
  1: y, o             (initial glide — PREFIX)
  2: l, r             (liquid — PREFIX)
  3: f, p, k, t       (gallows — ROOT onset)
  4: ch, sh, ckh, cth (compound gallows — ROOT onset)
  5: e, ee, eee       (bench — ROOT body)
  6: d, s             (mid-consonant — ROOT body)
  7: a, o             (vowel — ROOT body)
  8:                   (rare / implied)
  9: i, ii, iii       (i-series — SUFFIX)
 10: d, l, n, in, iin, m, r  (final — TERMINAL)
 11: y                (terminal — TERMINAL)
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import classify_folio_v3 as classify_folio, entropy_v2 as entropy, result_path

# ── Slot Definitions (Zattera system) ──────────────────────────────────────
# Order matters: longer tokens must be checked before shorter ones in each slot.
# Each slot is a list of EVA tokens that can appear in that position.

SLOT_TOKENS = {
    0:  ["q", "d", "s"],
    1:  ["y", "o"],
    2:  ["l", "r"],
    3:  ["f", "p", "k", "t"],
    4:  ["ckh", "cth", "cph", "cfh", "sch", "sh", "ch"],  # longest first
    5:  ["eee", "ee", "e"],
    6:  ["d", "s"],
    7:  ["a", "o"],
    # slot 8 is rare/empty in most words
    9:  ["iii", "ii", "i"],
    10: ["iin", "in", "n", "m", "d", "l", "r"],
    11: ["y"],
}

# Slots grouped into morphological zones
ZONE_PREFIX = [0, 1, 2]
ZONE_ROOT   = [3, 4, 5, 6, 7]
ZONE_SUFFIX = [9, 10, 11]

ZONE_NAMES = {
    0: "prefix.initial", 1: "prefix.glide", 2: "prefix.liquid",
    3: "root.gallows", 4: "root.compound", 5: "root.bench",
    6: "root.mid", 7: "root.vowel",
    9: "suffix.i-series", 10: "suffix.final", 11: "suffix.terminal",
}

# ── Section Classification (Currier language / page type) ──────────────────



# ── Word Extraction ────────────────────────────────────────────────────────

def extract_words(txt_path):
    """
    Extract clean EVA words from an IVTFF transcription file.
    Returns (words_list, section, language, folio_name).
    """
    lines = txt_path.read_text(encoding="utf-8").splitlines()
    header_lines = []
    word_lines = []
    folio_name = txt_path.stem

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            header_lines.append(stripped)
            continue
        if not stripped or stripped.startswith("<!"):
            continue
        # Skip page headers and locus tags
        if re.match(r"^<f\w+>", stripped):
            header_lines.append(stripped)
            continue
        # Extract the text portion after the locus marker
        m = re.match(r"<[^>]+>\s*(.*)", stripped)
        if m:
            word_lines.append(m.group(1))

    section, lang = classify_folio(header_lines)

    # Parse words from lines
    words = []
    for line in word_lines:
        # Remove inline comments <! ... >
        line = re.sub(r"<![^>]*>", "", line)
        # Remove paragraph markers, line-end markers, labels
        line = re.sub(r"<%>", "", line)
        line = re.sub(r"<\$>", "", line)
        line = re.sub(r"<[^>]*>", "", line)
        # Remove alternative readings [a:b] — take first option
        line = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", line)
        # Remove ligature markers {xx} → xx
        line = re.sub(r"\{([^}]+)\}", r"\1", line)
        # Remove non-EVA annotation markers (@NNN;)
        line = re.sub(r"@\d+;?", "", line)
        # Split on dots, commas, spaces, hyphens (word separators in IVTFF)
        tokens = re.split(r"[.\s,<>\-]+", line)
        for tok in tokens:
            tok = tok.strip()
            # Skip empty, uncertain readings, and non-EVA
            if not tok or "?" in tok or "'" in tok:
                continue
            # Only keep tokens that are purely EVA characters
            if re.match(r"^[a-z]+$", tok) and len(tok) >= 2:
                words.append(tok)

    return words, section, lang, folio_name


# ── Slot Decomposition ─────────────────────────────────────────────────────

def decompose_word(word):
    """
    Decompose an EVA word into its slot components.
    Returns a dict: {slot_number: matched_token, ...} and the remainder.

    Uses greedy left-to-right matching following slot order.
    """
    slots = {}
    pos = 0
    remainder = ""

    # Try each slot in order
    for slot_num in sorted(SLOT_TOKENS.keys()):
        if pos >= len(word):
            break
        matched = False
        for token in SLOT_TOKENS[slot_num]:
            if word[pos:].startswith(token):
                slots[slot_num] = token
                pos += len(token)
                matched = True
                break
        # If slot didn't match, skip it (slot is optional)

    if pos < len(word):
        remainder = word[pos:]

    return slots, remainder


def get_zone(slots):
    """Extract prefix, root, suffix zones from slot decomposition."""
    prefix = "".join(slots.get(s, "") for s in ZONE_PREFIX)
    root   = "".join(slots.get(s, "") for s in ZONE_ROOT)
    suffix = "".join(slots.get(s, "") for s in ZONE_SUFFIX)
    return prefix, root, suffix


# ── Analysis Functions ──────────────────────────────────────────────────────



def find_paradigms(decomposed_words, min_count=5):
    """
    Find paradigmatic sets: groups of words identical except in one slot.
    These reveal which slots carry grammatical vs semantic information.
    """
    paradigms = defaultdict(lambda: defaultdict(int))

    for word, (slots, _) in decomposed_words.items():
        filled_slots = sorted(slots.keys())
        # For each filled slot, create a template with that slot blanked
        for blank_slot in filled_slots:
            template_parts = []
            for s in filled_slots:
                if s == blank_slot:
                    template_parts.append(f"[{ZONE_NAMES.get(s, s)}=___]")
                else:
                    template_parts.append(f"{s}:{slots[s]}")
            template = " ".join(template_parts)
            paradigms[template][slots[blank_slot]] += 1

    # Keep only paradigms where the blanked slot has multiple values
    real_paradigms = {}
    for template, values in paradigms.items():
        if len(values) >= 2 and sum(values.values()) >= min_count:
            real_paradigms[template] = dict(values)

    return real_paradigms


def analyze_suffix_position(folio_words_decomposed):
    """
    Check if suffix distributions change based on position within a paragraph.
    If suffixes encode tense, we might see past-tense at the start and
    present/future later, or vice versa.
    """
    position_suffixes = defaultdict(Counter)  # "start"/"mid"/"end" -> Counter

    for folio, words_data in folio_words_decomposed.items():
        n = len(words_data)
        if n < 3:
            continue
        for i, (word, slots, _) in enumerate(words_data):
            suffix = "".join(slots.get(s, "") for s in ZONE_SUFFIX)
            if not suffix:
                continue
            if i < n * 0.2:
                pos = "para_start"
            elif i > n * 0.8:
                pos = "para_end"
            else:
                pos = "para_mid"
            position_suffixes[pos][suffix] += 1

    return dict(position_suffixes)


def suffix_agreement_analysis(all_words_list):
    """
    Check for case/number agreement: do adjacent words tend to share suffixes?
    Compare the actual suffix-match rate with what random chance would produce.
    """
    suffix_list = []
    for word, slots, _ in all_words_list:
        suffix = "".join(slots.get(s, "") for s in ZONE_SUFFIX)
        suffix_list.append(suffix)

    if len(suffix_list) < 2:
        return None

    # Actual adjacency match rate
    matches = sum(1 for i in range(len(suffix_list) - 1)
                  if suffix_list[i] == suffix_list[i+1] and suffix_list[i])
    total_pairs = len(suffix_list) - 1
    actual_rate = matches / total_pairs if total_pairs > 0 else 0

    # Expected match rate under random shuffling
    suffix_counts = Counter(suffix_list)
    total = sum(suffix_counts.values())
    expected_rate = sum((c/total)**2 for c in suffix_counts.values()) if total > 0 else 0

    return {
        "actual_adjacent_match_rate": actual_rate,
        "expected_random_match_rate": expected_rate,
        "ratio": actual_rate / expected_rate if expected_rate > 0 else 0,
        "total_pairs": total_pairs,
    }


# ── Main Analysis ──────────────────────────────────────────────────────────

def main():
    folios_dir = Path("folios")
    txt_files = sorted(folios_dir.glob("*.txt"))

    print("=" * 80)
    print("VOYNICH MANUSCRIPT — SLOT-BASED MORPHOLOGICAL ANALYSIS")
    print("Testing: Prefix–Root–Suffix Agglutinative Structure (Zattera Slots)")
    print("=" * 80)

    # ── 1. Extract all words from all folios ────────────────────────────
    print("\n[1] EXTRACTING WORDS FROM ALL FOLIOS...")
    all_words = []              # (word, section, lang, folio)
    section_words = defaultdict(list)
    lang_words = defaultdict(list)
    folio_count = 0

    for txt_file in txt_files:
        words, section, lang, folio = extract_words(txt_file)
        if words:
            folio_count += 1
            for w in words:
                all_words.append((w, section, lang, folio))
                section_words[section].append(w)
                lang_words[lang].append(w)

    unique_words = sorted(set(w for w, _, _, _ in all_words))
    print(f"   Folios analyzed: {folio_count}")
    print(f"   Total word tokens: {len(all_words):,}")
    print(f"   Unique word types: {len(unique_words):,}")
    print(f"   Sections: {', '.join(f'{k}({len(v):,})' for k,v in sorted(section_words.items()))}")
    print(f"   Languages: {', '.join(f'{k}({len(v):,})' for k,v in sorted(lang_words.items()))}")

    # ── 2. Decompose all words into slots ───────────────────────────────
    print("\n[2] DECOMPOSING WORDS INTO ZATTERA SLOTS...")
    word_decompositions = {}  # word -> (slots_dict, remainder)
    full_parse_count = 0
    partial_parse_count = 0
    failed_words = Counter()

    for word in unique_words:
        slots, remainder = decompose_word(word)
        word_decompositions[word] = (slots, remainder)
        if not remainder:
            full_parse_count += 1
        else:
            partial_parse_count += 1
            failed_words[remainder] += 1

    total = len(unique_words)
    print(f"   Fully parsed: {full_parse_count}/{total} ({100*full_parse_count/total:.1f}%)")
    print(f"   Partial parse (remainder): {partial_parse_count}/{total} ({100*partial_parse_count/total:.1f}%)")
    print(f"   Most common unparsed remainders:")
    for rem, count in failed_words.most_common(15):
        print(f"     '{rem}': {count}")

    # ── 3. Slot-level frequency analysis ────────────────────────────────
    print("\n[3] SLOT-LEVEL FREQUENCY ANALYSIS")
    print("    (How often each glyph appears in each slot position)\n")

    # Count how often each token appears in each slot (weighted by word frequency)
    word_freq = Counter(w for w, _, _, _ in all_words)
    slot_counters = defaultdict(Counter)
    slot_filled = Counter()
    slot_empty = Counter()

    for word, freq in word_freq.items():
        slots, _ = word_decompositions.get(word, ({}, word))
        for slot_num in sorted(SLOT_TOKENS.keys()):
            if slot_num in slots:
                slot_counters[slot_num][slots[slot_num]] += freq
                slot_filled[slot_num] += freq
            else:
                slot_empty[slot_num] += freq

    total_tokens = sum(word_freq.values())
    print(f"  {'Slot':<6} {'Zone':<20} {'Fill%':>6}  {'Entropy':>8}  {'Distribution'}")
    print(f"  {'─'*6} {'─'*20} {'─'*6}  {'─'*8}  {'─'*40}")
    for slot_num in sorted(SLOT_TOKENS.keys()):
        zone_name = ZONE_NAMES.get(slot_num, f"slot_{slot_num}")
        filled = slot_filled[slot_num]
        fill_pct = 100 * filled / total_tokens if total_tokens else 0
        h = entropy(slot_counters[slot_num])
        dist = ", ".join(f"{tok}:{cnt}" for tok, cnt in
                        slot_counters[slot_num].most_common(8))
        print(f"  {slot_num:<6} {zone_name:<20} {fill_pct:>5.1f}%  {h:>7.3f} b  {dist}")

    # ── 4. Zone-level analysis ──────────────────────────────────────────
    print("\n[4] MORPHOLOGICAL ZONE ANALYSIS")
    print("    (Prefix / Root / Suffix decomposition)\n")

    zone_counter = {"prefix": Counter(), "root": Counter(), "suffix": Counter()}
    for word, freq in word_freq.items():
        slots, _ = word_decompositions.get(word, ({}, word))
        prefix, root, suffix = get_zone(slots)
        if prefix:
            zone_counter["prefix"][prefix] += freq
        if root:
            zone_counter["root"][root] += freq
        if suffix:
            zone_counter["suffix"][suffix] += freq

    for zone_name in ["prefix", "root", "suffix"]:
        counter = zone_counter[zone_name]
        h = entropy(counter)
        total_zone = sum(counter.values())
        unique_zone = len(counter)
        print(f"  {zone_name.upper()}")
        print(f"    Unique forms: {unique_zone}")
        print(f"    Total tokens: {total_zone:,}")
        print(f"    Entropy: {h:.3f} bits")
        print(f"    Top 20:")
        for val, cnt in counter.most_common(20):
            pct = 100 * cnt / total_zone
            print(f"      {val or '(empty)':<15} {cnt:>6,}  ({pct:>5.1f}%)")
        print()

    # ── 5. Paradigm discovery ───────────────────────────────────────────
    print("\n[5] PARADIGM DISCOVERY")
    print("    (Word groups differing in exactly one slot → reveals grammar)\n")

    paradigms = find_paradigms(word_decompositions, min_count=3)
    # Sort by the number of alternations (most productive paradigms first)
    sorted_paradigms = sorted(paradigms.items(),
                              key=lambda x: (-len(x[1]), -sum(x[1].values())))

    shown = 0
    for template, values in sorted_paradigms[:30]:
        if len(values) < 2:
            continue
        total_p = sum(values.values())
        vals_str = ", ".join(f"{v}:{c}" for v, c in
                           sorted(values.items(), key=lambda x: -x[1]))
        print(f"  {template}")
        print(f"    → {vals_str}  (total: {total_p})")
        print()
        shown += 1

    print(f"  Total paradigms found: {len(paradigms)}")
    print(f"  (Showing top {shown})")

    # ── 6. Cross-section comparison ─────────────────────────────────────
    print("\n[6] CROSS-SECTION PREFIX/SUFFIX COMPARISON")
    print("    (Do different sections use different grammatical forms?)\n")

    for zone_name, slot_list in [("PREFIX", ZONE_PREFIX), ("SUFFIX", ZONE_SUFFIX)]:
        print(f"  {zone_name} distribution by manuscript section:")
        section_zone_counters = {}
        for section, words in section_words.items():
            counter = Counter()
            for w in words:
                slots, _ = word_decompositions.get(w, ({}, w))
                val = "".join(slots.get(s, "") for s in slot_list)
                if val:
                    counter[val] += 1
            section_zone_counters[section] = counter

        # Show top values per section
        all_vals = set()
        for c in section_zone_counters.values():
            all_vals.update(v for v, _ in c.most_common(10))
        top_vals = sorted(all_vals)[:15]

        # Header
        sections = sorted(section_zone_counters.keys())
        header = f"    {'':15}" + "".join(f"{s:>10}" for s in sections)
        print(header)
        print(f"    {'─'*15}" + "─" * (10 * len(sections)))
        for val in top_vals:
            row = f"    {val:<15}"
            for sec in sections:
                c = section_zone_counters[sec]
                total_sec = sum(c.values())
                cnt = c.get(val, 0)
                pct = 100 * cnt / total_sec if total_sec > 0 else 0
                row += f"{pct:>9.1f}%"
            print(row)
        print()

    # ── 7. Suffix agreement analysis ────────────────────────────────────
    print("\n[7] SUFFIX AGREEMENT ANALYSIS")
    print("    (Do adjacent words share suffixes more than chance → case agreement?)\n")

    # Build ordered word list per folio
    all_words_decomposed = []
    for word, section, lang, folio in all_words:
        slots, rem = word_decompositions.get(word, ({}, word))
        all_words_decomposed.append((word, slots, rem))

    agreement = suffix_agreement_analysis(all_words_decomposed)
    if agreement:
        print(f"  Adjacent suffix match rate: {agreement['actual_adjacent_match_rate']:.4f}")
        print(f"  Expected random match rate: {agreement['expected_random_match_rate']:.4f}")
        print(f"  Ratio (actual/expected):    {agreement['ratio']:.3f}x")
        if agreement['ratio'] > 1.2:
            print(f"  ⟹ SIGNIFICANT: Adjacent words share suffixes {agreement['ratio']:.1f}x more")
            print(f"    than chance. This supports CASE AGREEMENT in the language.")
        elif agreement['ratio'] > 1.0:
            print(f"  ⟹ Slight tendency for adjacent suffix matching.")
        else:
            print(f"  ⟹ No evidence of suffix agreement.")

    # ── 8. Suffix positional analysis ───────────────────────────────────
    print("\n\n[8] SUFFIX POSITION-IN-PARAGRAPH ANALYSIS")
    print("    (Do suffixes change from paragraph start to end → tense shift?)\n")

    # Rebuild per-folio word lists
    folio_words = defaultdict(list)
    for word, section, lang, folio in all_words:
        slots, rem = word_decompositions.get(word, ({}, word))
        folio_words[folio].append((word, slots, rem))

    position_suffixes = analyze_suffix_position(folio_words)
    if position_suffixes:
        positions = ["para_start", "para_mid", "para_end"]
        # Find top suffixes overall
        all_suffixes = Counter()
        for pos_counter in position_suffixes.values():
            all_suffixes.update(pos_counter)
        top_suffixes = [s for s, _ in all_suffixes.most_common(12)]

        header = f"    {'Suffix':<12}" + "".join(f"{'start':>10}{'mid':>10}{'end':>10}")
        print(header)
        print(f"    {'─'*12}" + "─" * 30)
        for suf in top_suffixes:
            row = f"    {suf:<12}"
            for pos in positions:
                counter = position_suffixes.get(pos, Counter())
                total_pos = sum(counter.values())
                cnt = counter.get(suf, 0)
                pct = 100 * cnt / total_pos if total_pos > 0 else 0
                row += f"{pct:>9.1f}%"
            print(row)

    # ── 9. Language A vs B comparison ───────────────────────────────────
    print("\n\n[9] CURRIER LANGUAGE A vs B — MORPHOLOGICAL COMPARISON")
    print("    (Two 'languages' might just be different tense/register?)\n")

    for zone_name, slot_list in [("PREFIX", ZONE_PREFIX), ("ROOT", ZONE_ROOT), ("SUFFIX", ZONE_SUFFIX)]:
        counters = {}
        for lang_key in ["A", "B"]:
            counter = Counter()
            for w in lang_words.get(lang_key, []):
                slots, _ = word_decompositions.get(w, ({}, w))
                val = "".join(slots.get(s, "") for s in slot_list)
                if val:
                    counter[val] += 1
            counters[lang_key] = counter

        # Top values across both
        combined = Counter()
        for c in counters.values():
            combined.update(c)
        top_vals = [v for v, _ in combined.most_common(10)]

        print(f"  {zone_name}:")
        print(f"    {'':15}{'Lang A':>10}{'Lang B':>10}{'Δ':>10}")
        print(f"    {'─'*15}{'─'*30}")
        for val in top_vals:
            a_total = sum(counters.get("A", Counter()).values()) or 1
            b_total = sum(counters.get("B", Counter()).values()) or 1
            a_pct = 100 * counters.get("A", Counter()).get(val, 0) / a_total
            b_pct = 100 * counters.get("B", Counter()).get(val, 0) / b_total
            delta = b_pct - a_pct
            print(f"    {val:<15}{a_pct:>9.1f}%{b_pct:>9.1f}%{delta:>+9.1f}%")
        print()

    # ── 10. Most common full decompositions ─────────────────────────────
    print("\n[10] TOP 50 WORDS — FULL SLOT DECOMPOSITION\n")
    top_words = word_freq.most_common(50)
    print(f"  {'Word':<18} {'Freq':>6}  {'Prefix':<8} {'Root':<12} {'Suffix':<10} {'Rem':<6}")
    print(f"  {'─'*18} {'─'*6}  {'─'*8} {'─'*12} {'─'*10} {'─'*6}")
    for word, freq in top_words:
        slots, rem = word_decompositions.get(word, ({}, word))
        prefix, root, suffix = get_zone(slots)
        print(f"  {word:<18} {freq:>6}  {prefix or '—':<8} {root or '—':<12} {suffix or '—':<10} {rem or '—':<6}")

    # ── Save decomposition data ─────────────────────────────────────────
    output = {
        "total_tokens": len(all_words),
        "unique_types": len(unique_words),
        "full_parse_rate": full_parse_count / total if total else 0,
        "top_prefixes": dict(zone_counter["prefix"].most_common(50)),
        "top_roots": dict(zone_counter["root"].most_common(50)),
        "top_suffixes": dict(zone_counter["suffix"].most_common(50)),
        "decompositions": {
            word: {
                "slots": {str(k): v for k, v in slots.items()},
                "prefix": get_zone(slots)[0],
                "root": get_zone(slots)[1],
                "suffix": get_zone(slots)[2],
                "remainder": rem,
                "frequency": word_freq[word],
            }
            for word, (slots, rem) in word_decompositions.items()
        },
    }
    out_path = result_path("slot_analysis_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Full decomposition data saved to {out_path}")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
