#!/usr/bin/env python3
"""
Full Morphological Attack Plan

Executes the 5-step decipherment strategy:
  1. Improved parser (fixes sh-words, al/ol/ar/or endings)
  2. Full paradigm/declension tables per root
  3. Root–imagery correlation (labels on herbal/pharma pages)
  4. Prefix substitution hypothesis test (qo- vs o- etc.)
  5. I-series mapping (daiin vs dain vs daiiin)

Based on Zattera glyph-slot system.
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from common import classify_folio_v3 as classify_folio, entropy_v2 as entropy, get_root, result_path

# ════════════════════════════════════════════════════════════════════════════
# 1. IMPROVED PARSER
# ════════════════════════════════════════════════════════════════════════════
#
# Key fix: the old parser couldn't handle "sh" when it acts as a root-onset
# because it consumed 's' at slot 0 first. Now we attempt MULTIPLE parse
# paths and pick the best (most slots filled, least remainder).
#
# Also fixes: al/ol/ar/or as suffix-final combinations, and handles the
# common patterns like "shedy" = sh(root) + e(bench) + d(mid) + y(terminal).

# ── Token Sets ──────────────────────────────────────────────────────────

PREFIXES = [
    # Ordered by length descending, then frequency
    "qol", "qor", "sol", "sor", "dol", "dor", "dyl", "dyr",
    "qo", "so", "do", "dy",
    "ol", "or", "yl", "yr",
    "q", "d", "s",
    "o", "y",
    "l", "r",
]

ROOT_ONSETS = [
    # Compound gallows (slot 3+4 combined)
    "ckh", "cth", "cph", "cfh",
    # Simple gallows + compound
    "tch", "kch", "pch", "fch",
    "tsh", "ksh", "psh", "fsh",
    # Compound (slot 4)
    "sh", "ch",
    # Simple gallows (slot 3)
    "f", "p", "k", "t",
]

ROOT_BODIES = [
    # bench + mid + vowel combos (slots 5-7), longest first
    "eeed", "eees", "eeea", "eeeo",
    "eed", "ees", "eea", "eeo",
    "ed", "es", "ea", "eo",
    "eee", "ee", "e",
    "da", "do", "sa", "so",
    "d", "s",
    "a", "o",
]

SUFFIXES = [
    # i-series + final + terminal (slots 9-11), longest first
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
    """
    Parse an EVA word into (prefix, root_onset, root_body, suffix, remainder)
    using best-path selection.

    Tries all valid prefix consumptions, then root onset, then body, then suffix.
    Returns the parse that explains the most of the word.
    """
    best = None
    best_score = -1

    # Try each possible prefix (including empty prefix)
    prefix_options = [""]  # empty prefix
    for pfx in PREFIXES:
        if word.startswith(pfx):
            prefix_options.append(pfx)

    for pfx in prefix_options:
        rest1 = word[len(pfx):]

        # Try each possible root onset (including none)
        onset_options = [""]
        for onset in ROOT_ONSETS:
            if rest1.startswith(onset):
                onset_options.append(onset)

        for onset in onset_options:
            rest2 = rest1[len(onset):]

            # Try each possible root body (including none)
            body_options = [""]
            for body in ROOT_BODIES:
                if rest2.startswith(body):
                    body_options.append(body)

            for body in body_options:
                rest3 = rest2[len(body):]

                # Try each possible suffix (including none)
                suf_options = [""]
                for suf in SUFFIXES:
                    if rest3 == suf:  # suffix must consume the rest
                        suf_options.append(suf)

                # Also try suffix that consumes end, leaving middle remainder
                for suf in SUFFIXES:
                    if rest3.endswith(suf) and rest3 != suf:
                        suf_options.append(suf)

                for suf in suf_options:
                    if suf and rest3.endswith(suf):
                        remainder = rest3[:-len(suf)] if suf else rest3
                    elif suf and rest3 == suf:
                        remainder = ""
                    else:
                        remainder = rest3

                    # Score: more explained characters = better, prefer no remainder
                    explained = len(pfx) + len(onset) + len(body) + len(suf)
                    score = explained * 10 - len(remainder) * 15
                    # Bonus for complete parse
                    if not remainder:
                        score += 50
                    # Bonus for having a root (onset or body)
                    if onset or body:
                        score += 20
                    # Penalty for prefix-only or suffix-only parses
                    if not onset and not body and (pfx or suf):
                        score -= 10

                    if score > best_score:
                        best_score = score
                        best = (pfx, onset, body, suf, remainder)

    if best is None:
        return ("", "", "", "", word)
    return best




# ════════════════════════════════════════════════════════════════════════════
# WORD EXTRACTION (same as before, improved)
# ════════════════════════════════════════════════════════════════════════════



def extract_words_and_labels(txt_path):
    """
    Extract (paragraph_words, label_words, section, language, folio_name).
    Labels are lines with L in the locus type.
    """
    lines = txt_path.read_text(encoding="utf-8").splitlines()
    header_lines = []
    para_words = []
    label_words = []
    folio_name = txt_path.stem

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            header_lines.append(stripped)
            continue
        if not stripped or stripped.startswith("<!"):
            continue
        if re.match(r"^<f\w+>\s", stripped):
            header_lines.append(stripped)
            continue

        # Check if this is a label line
        m = re.match(r"<([^>]+)>\s*(.*)", stripped)
        if not m:
            continue
        locus = m.group(1)
        text = m.group(2)
        is_label = bool(re.search(r"[,@*+]L", locus))

        # Clean the text
        text = re.sub(r"<![^>]*>", "", text)
        text = re.sub(r"<%>|<\$>|<->", " ", text)
        text = re.sub(r"<[^>]*>", "", text)
        text = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", text)
        text = re.sub(r"\{([^}]+)\}", r"\1", text)
        text = re.sub(r"@\d+;?", "", text)
        tokens = re.split(r"[.\s,<>\-]+", text)
        for tok in tokens:
            tok = tok.strip()
            if not tok or "?" in tok or "'" in tok:
                continue
            if re.match(r"^[a-z]+$", tok) and len(tok) >= 2:
                if is_label:
                    label_words.append(tok)
                else:
                    para_words.append(tok)

    section, lang = classify_folio(header_lines)
    return para_words, label_words, section, lang, folio_name


# ════════════════════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════



# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    folios_dir = Path("folios")
    txt_files = sorted(folios_dir.glob("*.txt"))

    print("=" * 90)
    print("VOYNICH MANUSCRIPT — FULL MORPHOLOGICAL ATTACK PLAN")
    print("=" * 90)

    # ── Extract all data ────────────────────────────────────────────────
    print("\n" + "━" * 90)
    print("DATA EXTRACTION")
    print("━" * 90)

    all_para = []       # (word, section, lang, folio)
    all_labels = []     # (word, section, lang, folio)
    section_words = defaultdict(list)
    lang_words = defaultdict(list)
    folio_words = defaultdict(list)  # folio -> [(word, is_label), ...]

    for txt_file in txt_files:
        para, labels, section, lang, folio = extract_words_and_labels(txt_file)
        for w in para:
            all_para.append((w, section, lang, folio))
            section_words[section].append(w)
            lang_words[lang].append(w)
            folio_words[folio].append((w, False))
        for w in labels:
            all_labels.append((w, section, lang, folio))
            folio_words[folio].append((w, True))

    all_words = [w for w, _, _, _ in all_para]
    word_freq = Counter(all_words)
    label_freq = Counter(w for w, _, _, _ in all_labels)
    unique_words = sorted(set(all_words))

    print(f"  Paragraph tokens: {len(all_para):,}")
    print(f"  Label tokens:     {len(all_labels):,}")
    print(f"  Unique types:     {len(unique_words):,}")

    # ── Parse all words ─────────────────────────────────────────────────
    print("\n" + "━" * 90)
    print("IMPROVED PARSER — MULTI-PATH SLOT DECOMPOSITION")
    print("━" * 90)

    all_unique = sorted(set(all_words + [w for w, _, _, _ in all_labels]))
    parses = {}  # word -> (prefix, onset, body, suffix, remainder)
    full_count = 0
    partial_count = 0

    for w in all_unique:
        p = parse_word(w)
        parses[w] = p
        if not p[4]:  # no remainder
            full_count += 1
        else:
            partial_count += 1

    total = len(all_unique)
    print(f"  Total unique words: {total}")
    print(f"  Fully parsed:       {full_count} ({100*full_count/total:.1f}%)")
    print(f"  With remainder:     {partial_count} ({100*partial_count/total:.1f}%)")

    # Show remainder distribution
    remainder_counter = Counter()
    for w, (pfx, onset, body, suf, rem) in parses.items():
        if rem:
            remainder_counter[rem] += word_freq.get(w, 1)
    print(f"\n  Top 15 remainders (by frequency):")
    for rem, cnt in remainder_counter.most_common(15):
        print(f"    '{rem}': {cnt}")

    # Show some example parses
    print(f"\n  Example parses of top words:")
    print(f"  {'Word':<18} {'Prefix':<8} {'Onset':<8} {'Body':<8} {'Suffix':<8} {'Rem':<8}")
    print(f"  {'─'*18} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    for w, cnt in word_freq.most_common(40):
        pfx, onset, body, suf, rem = parses[w]
        print(f"  {w:<18} {pfx or '—':<8} {onset or '—':<8} {body or '—':<8} {suf or '—':<8} {rem or '—':<8}")

    # ── 2. PARADIGM / DECLENSION TABLES ─────────────────────────────────
    print("\n" + "━" * 90)
    print("PARADIGM / DECLENSION TABLES PER ROOT")
    print("━" * 90)

    # Group words by root
    root_paradigms = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    root_freq = Counter()

    for w in all_words:
        pfx, onset, body, suf, rem = parses[w]
        root = get_root(onset, body)
        if root and not rem:
            root_paradigms[root][pfx][suf] += 1
            root_freq[root] += 1

    # Print top roots with their full paradigm tables
    print(f"\n  Found {len(root_paradigms)} unique roots (fully parsed words only)")
    print(f"\n  Top 25 roots with their prefix × suffix paradigm tables:\n")

    for root, freq in root_freq.most_common(25):
        paradigm = root_paradigms[root]
        # Collect all prefixes and suffixes for this root
        all_pfx = sorted(paradigm.keys(), key=lambda x: -sum(paradigm[x].values()))
        all_suf = set()
        for pfx_dict in paradigm.values():
            all_suf.update(pfx_dict.keys())
        all_suf = sorted(all_suf, key=lambda s: -sum(paradigm[p].get(s, 0) for p in all_pfx))

        # Limit to top prefixes/suffixes to keep table readable
        show_pfx = all_pfx[:8]
        show_suf = all_suf[:10]

        total_forms = sum(sum(d.values()) for d in paradigm.values())
        n_forms = sum(1 for p in all_pfx for s in all_suf if paradigm[p].get(s, 0) > 0)

        print(f"  ┌─ ROOT: {root!r}  (freq: {freq}, {n_forms} attested forms)")
        # Header row
        hdr = f"  │ {'pfx╲suf':<10}"
        for suf in show_suf:
            hdr += f" {suf or '∅':>7}"
        print(hdr)
        print(f"  │ {'─'*10}" + "─" * (8 * len(show_suf)))

        for pfx in show_pfx:
            row = f"  │ {pfx or '∅':<10}"
            for suf in show_suf:
                cnt = paradigm[pfx].get(suf, 0)
                if cnt > 0:
                    row += f" {cnt:>7}"
                else:
                    row += f" {'·':>7}"
            print(row)
        print(f"  └{'─'*78}")
        print()

    # ── 3. ROOT–IMAGERY CORRELATION ─────────────────────────────────────
    print("\n" + "━" * 90)
    print("ROOT–IMAGERY CORRELATION (LABEL vs PARAGRAPH ROOTS)")
    print("━" * 90)

    # Compare root distributions in labels vs paragraph text
    label_roots = Counter()
    para_roots = Counter()
    label_prefixes = Counter()
    para_prefixes = Counter()
    label_suffixes = Counter()
    para_suffixes = Counter()

    for w, _, _, _ in all_labels:
        pfx, onset, body, suf, rem = parses.get(w, ("","","","",w))
        root = get_root(onset, body)
        if root and not rem:
            label_roots[root] += 1
            label_prefixes[pfx] += 1
            label_suffixes[suf] += 1

    for w, _, _, _ in all_para:
        pfx, onset, body, suf, rem = parses.get(w, ("","","","",w))
        root = get_root(onset, body)
        if root and not rem:
            para_roots[root] += 1
            para_prefixes[pfx] += 1
            para_suffixes[suf] += 1

    print(f"\n  Label words (fully parsed): {sum(label_roots.values())}")
    print(f"  Paragraph words (fully parsed): {sum(para_roots.values())}")

    # Roots that appear primarily in labels (potential plant/substance names)
    print(f"\n  ROOTS ENRICHED IN LABELS (potential noun/name roots):")
    print(f"  {'Root':<15} {'Label':>8} {'Para':>8} {'Label%':>8} {'Para%':>8} {'Ratio':>8}")
    print(f"  {'─'*15} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    label_total = sum(label_roots.values()) or 1
    para_total = sum(para_roots.values()) or 1

    enriched = []
    for root in set(label_roots.keys()) | set(para_roots.keys()):
        lc = label_roots.get(root, 0)
        pc = para_roots.get(root, 0)
        lpct = lc / label_total
        ppct = pc / para_total
        if lc >= 2:
            ratio = lpct / ppct if ppct > 0 else float('inf')
            enriched.append((root, lc, pc, lpct, ppct, ratio))

    enriched.sort(key=lambda x: -x[5])
    for root, lc, pc, lpct, ppct, ratio in enriched[:25]:
        ratio_str = f"{ratio:.1f}x" if ratio < 1000 else "∞"
        print(f"  {root:<15} {lc:>8} {pc:>8} {100*lpct:>7.1f}% {100*ppct:>7.1f}% {ratio_str:>8}")

    # Compare prefix/suffix usage in labels vs paragraphs
    print(f"\n  PREFIX DISTRIBUTION: Labels vs Paragraphs")
    print(f"  {'Prefix':<10} {'Label%':>10} {'Para%':>10} {'Δ':>10}")
    print(f"  {'─'*10} {'─'*10} {'─'*10} {'─'*10}")
    lt = sum(label_prefixes.values()) or 1
    pt = sum(para_prefixes.values()) or 1
    all_pfxs = set(label_prefixes) | set(para_prefixes)
    pfx_sorted = sorted(all_pfxs, key=lambda x: -(label_prefixes.get(x,0)/lt + para_prefixes.get(x,0)/pt))
    for pfx in pfx_sorted[:12]:
        lp = 100 * label_prefixes.get(pfx, 0) / lt
        pp = 100 * para_prefixes.get(pfx, 0) / pt
        print(f"  {pfx or '∅':<10} {lp:>9.1f}% {pp:>9.1f}% {lp-pp:>+9.1f}%")

    print(f"\n  SUFFIX DISTRIBUTION: Labels vs Paragraphs")
    print(f"  {'Suffix':<10} {'Label%':>10} {'Para%':>10} {'Δ':>10}")
    print(f"  {'─'*10} {'─'*10} {'─'*10} {'─'*10}")
    lt = sum(label_suffixes.values()) or 1
    pt = sum(para_suffixes.values()) or 1
    all_sufs = set(label_suffixes) | set(para_suffixes)
    suf_sorted = sorted(all_sufs, key=lambda x: -(label_suffixes.get(x,0)/lt + para_suffixes.get(x,0)/pt))
    for suf in suf_sorted[:12]:
        lp = 100 * label_suffixes.get(suf, 0) / lt
        pp = 100 * para_suffixes.get(suf, 0) / pt
        print(f"  {suf or '∅':<10} {lp:>9.1f}% {pp:>9.1f}% {lp-pp:>+9.1f}%")

    # ── 4. PREFIX SUBSTITUTION HYPOTHESIS ───────────────────────────────
    print("\n" + "━" * 90)
    print("PREFIX SUBSTITUTION HYPOTHESIS")
    print("━" * 90)
    print("  Testing: Do words with different prefixes but same root+suffix")
    print("  appear in the same syntactic positions (= prefix is grammatical)?\n")

    # For each root+suffix combination, find all prefix variants
    root_suf_to_prefixes = defaultdict(lambda: Counter())
    for w in all_words:
        pfx, onset, body, suf, rem = parses[w]
        root = get_root(onset, body)
        if root and not rem:
            key = (root, suf)
            root_suf_to_prefixes[key][pfx] += 1

    # Find pairs that share root+suffix but differ in prefix
    print(f"  Root+Suffix pairs with multiple prefix variants (top 30):\n")
    print(f"  {'Root+Suffix':<25} {'Prefixes (freq)':}")
    print(f"  {'─'*25} {'─'*60}")

    multi_prefix = {k: v for k, v in root_suf_to_prefixes.items() if len(v) >= 2}
    top_pairs = sorted(multi_prefix.items(), key=lambda x: -sum(x[1].values()))

    for (root, suf), prefixes in top_pairs[:30]:
        key_str = f"{root}+{suf or '∅'}"
        pfx_str = ", ".join(f"{p or '∅'}({c})" for p, c in prefixes.most_common(8))
        print(f"  {key_str:<25} {pfx_str}")

    # Bigram context test: for top prefix pairs, do they appear before/after the same words?
    print(f"\n  CONTEXT TEST: Do prefix variants appear in similar bigram contexts?")
    print(f"  (If yes, prefixes are grammatical modifiers, not semantic roots)\n")

    # Build word-to-context mapping
    word_contexts = defaultdict(Counter)  # word -> Counter of (prev_word, next_word)
    for folio, words_data in folio_words.items():
        wlist = [w for w, is_label in words_data if not is_label]
        for i, w in enumerate(wlist):
            if i > 0:
                word_contexts[w][("prev", wlist[i-1])] += 1
            if i < len(wlist) - 1:
                word_contexts[w][("next", wlist[i+1])] += 1

    # For top root+suffix, measure context overlap between prefix variants
    print(f"  {'Root+Suf':<20} {'Pfx1':>6} {'Pfx2':>6} {'Shared ctx':>11} {'Overlap':>8}")
    print(f"  {'─'*20} {'─'*6} {'─'*6} {'─'*11} {'─'*8}")

    for (root, suf), prefixes in top_pairs[:20]:
        pfx_list = [p for p, _ in prefixes.most_common(4)]
        if len(pfx_list) < 2:
            continue
        for p1, p2 in combinations(pfx_list[:3], 2):
            w1 = p1 + root + suf
            w2 = p2 + root + suf
            if w1 not in word_contexts or w2 not in word_contexts:
                continue
            ctx1 = set(word_contexts[w1].keys())
            ctx2 = set(word_contexts[w2].keys())
            shared = len(ctx1 & ctx2)
            total_ctx = len(ctx1 | ctx2)
            overlap = shared / total_ctx if total_ctx > 0 else 0
            key_str = f"{root}+{suf or '∅'}"
            print(f"  {key_str:<20} {p1 or '∅':>6} {p2 or '∅':>6} {shared:>11} {overlap:>7.1%}")

    # ── 5. I-SERIES MAPPING ─────────────────────────────────────────────
    print("\n" + "━" * 90)
    print("I-SERIES ANALYSIS (i / ii / iii → grammatical opposition)")
    print("━" * 90)

    # Find words that are identical except for i-series variation
    print(f"\n  Words differing ONLY in i-series count:\n")

    # Group by (prefix, root, final, terminal) — varying only i-count
    i_groups = defaultdict(lambda: defaultdict(int))
    for w in all_words:
        pfx, onset, body, suf, rem = parses[w]
        if rem:
            continue
        # Extract i-count from suffix
        i_count = 0
        rest_suf = suf
        for pattern, count in [("iii", 3), ("ii", 2), ("i", 1)]:
            if suf.startswith(pattern):
                i_count = count
                rest_suf = suf[len(pattern):]
                break

        if i_count > 0:
            key = (pfx, get_root(onset, body), rest_suf)
            i_groups[key][i_count] += 1

    # Find groups with multiple i-counts
    print(f"  {'Prefix+Root+Final':<30} {'i(×1)':>8} {'ii(×2)':>8} {'iii(×3)':>8} {'Pattern':}")
    print(f"  {'─'*30} {'─'*8} {'─'*8} {'─'*8} {'─'*30}")

    multi_i = {k: v for k, v in i_groups.items() if len(v) >= 2}
    i_sorted = sorted(multi_i.items(), key=lambda x: -sum(x[1].values()))

    i1_total = 0
    i2_total = 0
    i3_total = 0
    shown = 0

    for (pfx, root, rest_suf), counts in i_sorted:
        c1 = counts.get(1, 0)
        c2 = counts.get(2, 0)
        c3 = counts.get(3, 0)
        i1_total += c1
        i2_total += c2
        i3_total += c3

        if shown < 30:
            key_str = f"{pfx or '∅'}+{root}+{rest_suf or '∅'}"
            # Word forms
            forms = []
            if c1:
                forms.append(f"{pfx}{root}i{rest_suf}({c1})")
            if c2:
                forms.append(f"{pfx}{root}ii{rest_suf}({c2})")
            if c3:
                forms.append(f"{pfx}{root}iii{rest_suf}({c3})")
            print(f"  {key_str:<30} {c1:>8} {c2:>8} {c3:>8} {' / '.join(forms)}")
            shown += 1

    print(f"\n  TOTALS across all i-variant groups:")
    print(f"    i  (single): {i1_total:>6}")
    print(f"    ii (double): {i2_total:>6}")
    print(f"    iii(triple): {i3_total:>6}")
    i_ratio_12 = i2_total / i1_total if i1_total > 0 else 0
    i_ratio_23 = i3_total / i2_total if i2_total > 0 else 0
    print(f"    Ratio ii/i:   {i_ratio_12:.2f}")
    print(f"    Ratio iii/ii: {i_ratio_23:.2f}")

    # Positional analysis: do i/ii/iii appear at different positions in sentences?
    print(f"\n  POSITIONAL DISTRIBUTION of i-series in word sequences:")
    i_positions = {1: Counter(), 2: Counter(), 3: Counter()}

    for folio, words_data in folio_words.items():
        wlist = [w for w, is_label in words_data if not is_label]
        n = len(wlist)
        if n < 5:
            continue
        for idx, w in enumerate(wlist):
            pfx, onset, body, suf, rem = parses.get(w, ("","","","",w))
            if rem:
                continue
            i_count = 0
            for pattern, count in [("iii", 3), ("ii", 2), ("i", 1)]:
                if suf.startswith(pattern):
                    i_count = count
                    break
            if i_count == 0:
                continue
            rel_pos = idx / n  # 0.0 = start, 1.0 = end
            if rel_pos < 0.33:
                i_positions[i_count]["start"] += 1
            elif rel_pos < 0.67:
                i_positions[i_count]["middle"] += 1
            else:
                i_positions[i_count]["end"] += 1

    print(f"  {'i-count':<10} {'Start%':>10} {'Middle%':>10} {'End%':>10}")
    print(f"  {'─'*10} {'─'*10} {'─'*10} {'─'*10}")
    for ic in [1, 2, 3]:
        total_ic = sum(i_positions[ic].values()) or 1
        s = 100 * i_positions[ic].get("start", 0) / total_ic
        m = 100 * i_positions[ic].get("middle", 0) / total_ic
        e = 100 * i_positions[ic].get("end", 0) / total_ic
        print(f"  {'i'*ic:<10} {s:>9.1f}% {m:>9.1f}% {e:>9.1f}%")

    # Context: what words typically FOLLOW i vs ii vs iii words?
    print(f"\n  FOLLOWING-WORD DISTRIBUTION (what comes after i/ii/iii words):")
    i_following = {1: Counter(), 2: Counter(), 3: Counter()}
    for folio, words_data in folio_words.items():
        wlist = [w for w, is_label in words_data if not is_label]
        for idx in range(len(wlist) - 1):
            w = wlist[idx]
            pfx, onset, body, suf, rem = parses.get(w, ("","","","",w))
            if rem:
                continue
            i_count = 0
            for pattern, count in [("iii", 3), ("ii", 2), ("i", 1)]:
                if suf.startswith(pattern):
                    i_count = count
                    break
            if i_count == 0:
                continue
            next_w = wlist[idx + 1]
            i_following[i_count][next_w] += 1

    for ic in [1, 2, 3]:
        print(f"\n  After {'i'*ic}-words (top 10):")
        for w, cnt in i_following[ic].most_common(10):
            print(f"    {w:<18} {cnt}")

    # ── 6. CURRIER A vs B — MORPHOLOGICAL FINGERPRINT ───────────────────
    print("\n" + "━" * 90)
    print("CURRIER LANGUAGE A vs B — FULL MORPHOLOGICAL FINGERPRINT")
    print("━" * 90)

    for lang_label, lang_key in [("Language A", "A"), ("Language B", "B")]:
        words = lang_words.get(lang_key, [])
        pfx_c = Counter()
        root_c = Counter()
        suf_c = Counter()
        for w in words:
            pfx, onset, body, suf, rem = parses.get(w, ("","","","",w))
            root = get_root(onset, body)
            if not rem:
                pfx_c[pfx] += 1
                root_c[root] += 1
                suf_c[suf] += 1

        print(f"\n  {lang_label} ({len(words):,} tokens):")
        print(f"    Top prefixes: {', '.join(f'{p or '∅'}({c})' for p, c in pfx_c.most_common(8))}")
        print(f"    Top roots:    {', '.join(f'{r}({c})' for r, c in root_c.most_common(8))}")
        print(f"    Top suffixes: {', '.join(f'{s or '∅'}({c})' for s, c in suf_c.most_common(8))}")

    # Check which roots are EXCLUSIVE to A or B
    a_roots = Counter()
    b_roots = Counter()
    for w in lang_words.get("A", []):
        pfx, onset, body, suf, rem = parses.get(w, ("","","","",w))
        root = get_root(onset, body)
        if root and not rem:
            a_roots[root] += 1
    for w in lang_words.get("B", []):
        pfx, onset, body, suf, rem = parses.get(w, ("","","","",w))
        root = get_root(onset, body)
        if root and not rem:
            b_roots[root] += 1

    print(f"\n  Roots EXCLUSIVE to Language A (≥5 occurrences, absent from B):")
    for root, cnt in a_roots.most_common():
        if cnt >= 5 and root not in b_roots:
            print(f"    {root}: {cnt}")

    print(f"\n  Roots EXCLUSIVE to Language B (≥5 occurrences, absent from A):")
    for root, cnt in b_roots.most_common():
        if cnt >= 5 and root not in a_roots:
            print(f"    {root}: {cnt}")

    print(f"\n  Roots with BIGGEST A vs B shift:")
    print(f"  {'Root':<15} {'A%':>8} {'B%':>8} {'Δ':>8}")
    print(f"  {'─'*15} {'─'*8} {'─'*8} {'─'*8}")
    at = sum(a_roots.values()) or 1
    bt = sum(b_roots.values()) or 1
    shifts = []
    for root in set(a_roots) | set(b_roots):
        ap = a_roots.get(root, 0) / at
        bp = b_roots.get(root, 0) / bt
        shifts.append((root, ap, bp, abs(bp - ap)))
    shifts.sort(key=lambda x: -x[3])
    for root, ap, bp, delta in shifts[:20]:
        print(f"  {root:<15} {100*ap:>7.1f}% {100*bp:>7.1f}% {100*(bp-ap):>+7.1f}%")

    # ── SAVE FULL RESULTS ───────────────────────────────────────────────
    print("\n" + "━" * 90)
    print("SAVING RESULTS")
    print("━" * 90)

    results = {
        "parse_stats": {
            "total_unique": total,
            "fully_parsed": full_count,
            "parse_rate": full_count / total if total else 0,
        },
        "decompositions": {},
        "paradigm_tables": {},
        "label_enriched_roots": [],
        "i_series_groups": [],
    }

    for w, (pfx, onset, body, suf, rem) in parses.items():
        results["decompositions"][w] = {
            "prefix": pfx, "root_onset": onset, "root_body": body,
            "suffix": suf, "remainder": rem,
            "root": get_root(onset, body),
            "frequency": word_freq.get(w, 0),
        }

    for root, freq in root_freq.most_common(100):
        paradigm = root_paradigms[root]
        table = {}
        for pfx, suf_dict in paradigm.items():
            table[pfx or "∅"] = {s or "∅": c for s, c in suf_dict.items()}
        results["paradigm_tables"][root] = {"freq": freq, "table": table}

    for root, lc, pc, lpct, ppct, ratio in enriched[:50]:
        results["label_enriched_roots"].append({
            "root": root, "label_count": lc, "para_count": pc,
            "ratio": ratio if ratio < 1e6 else None,
        })

    for (pfx, root, rest_suf), counts in i_sorted[:50]:
        results["i_series_groups"].append({
            "prefix": pfx, "root": root, "rest_suffix": rest_suf,
            "i1": counts.get(1, 0), "i2": counts.get(2, 0), "i3": counts.get(3, 0),
        })

    out_path = result_path("morphology_full_survey_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  Saved to {out_path}")

    print("\n" + "=" * 90)
    print("ATTACK PLAN COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()
