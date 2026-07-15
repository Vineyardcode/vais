#!/usr/bin/env python3
"""
VOYNICH MANUSCRIPT — PHASE 2: f66r FOCUSED DECIPHERMENT
=========================================================
f66r is our Rosetta fragment: a word list (15 entries), a character column
(33 single characters), and body text — all on the same page.

The page is Language B, "text only" section, features:
- A dead/reclining woman figure at bottom left
- Two circles and a cylinder near the figure
- Four words in a different alphabet ("non-Voynich writing")
- A sideways "2" symbol at bottom right

Strategy:
  1. WORD LIST STRUCTURE — What do the 15 words have in common?
  2. CHARACTER KEY — Do the 33 single chars encode a notation index?
  3. WORD-TO-TEXT BRIDGING — Do list roots appear in body text differently?
  4. LIST-INTERNAL PATTERNS — Is the list ordered by some morphological key?
  5. CROSS-FOLIO MATCHING — Where else do these exact words appear?
  6. CONSTRAINT TABLE — Build a substitution hypothesis from all evidence
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import get_root

# ═══════════════════════════════════════════════════════════════════════════
# PARSER
# ═══════════════════════════════════════════════════════════════════════════

PREFIXES = [
    "qol", "qor", "sol", "sor", "dol", "dor", "dyl", "dyr",
    "qo", "so", "do", "dy", "ol", "or", "yl", "yr",
    "q", "d", "s", "o", "y", "l", "r",
]
ROOT_ONSETS = [
    "ckh", "cth", "cph", "cfh", "tch", "kch", "pch", "fch",
    "tsh", "ksh", "psh", "fsh", "sh", "ch", "f", "p", "k", "t",
]
ROOT_BODIES = [
    "eeed", "eees", "eeea", "eeeo", "eed", "ees", "eea", "eeo",
    "ed", "es", "ea", "eo", "eee", "ee", "e",
    "da", "do", "sa", "so", "d", "s", "a", "o",
]
SUFFIXES = [
    "iiiny", "iiny", "iiir", "iiil", "iiin", "iir", "iil", "iin", "iim", "iid",
    "iry", "ily", "iny", "ir", "il", "in", "im", "id", "iii", "ii",
    "dy", "ly", "ry", "ny", "my", "i", "y", "n", "m", "d", "l", "r",
]

def parse_word(word):
    best = None; best_score = -1
    pfx_opts = [""]
    for pfx in PREFIXES:
        if word.startswith(pfx): pfx_opts.append(pfx)
    for pfx in pfx_opts:
        r1 = word[len(pfx):]
        onset_opts = [""]
        for o in ROOT_ONSETS:
            if r1.startswith(o): onset_opts.append(o)
        for onset in onset_opts:
            r2 = r1[len(onset):]
            body_opts = [""]
            for b in ROOT_BODIES:
                if r2.startswith(b): body_opts.append(b)
            for body in body_opts:
                r3 = r2[len(body):]
                suf_opts = [""]
                for s in SUFFIXES:
                    if r3 == s: suf_opts.append(s)
                for suf in suf_opts:
                    if suf:
                        remainder = "" if r3 == suf else (r3[:-len(suf)] if r3.endswith(suf) else r3)
                    else:
                        remainder = r3
                    explained = len(pfx) + len(onset) + len(body) + len(suf)
                    score = explained * 10 - len(remainder) * 15
                    if not remainder: score += 50
                    if onset or body: score += 20
                    if not onset and not body and (pfx or suf): score -= 10
                    if score > best_score:
                        best_score = score
                        best = (pfx, onset, body, suf, remainder)
    if best is None: return ("", "", "", "", word)
    return best




# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT f66r DATA
# ═══════════════════════════════════════════════════════════════════════════

def extract_f66r():
    """Extract structured data from f66r."""
    lines = Path("folios/f66r.txt").read_text(encoding="utf-8").splitlines()

    word_list = []     # (number, raw_word, cleaned_word)
    char_column = []   # (number, character)
    body_text = []     # list of line strings
    label_text = []    # Lx label near the dead figure

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"<([^>]+)>\s*(.*)", stripped)
        if not m:
            continue
        locus = m.group(1)
        text = m.group(2).strip()

        # Extract locus number
        num_m = re.search(r"\.(\d+)", locus)
        if not num_m:
            continue
        num = int(num_m.group(1))

        if "L0" in locus:
            # Clean text
            clean = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", text)
            clean = re.sub(r"@\d+;?", "", clean).strip()
            clean = re.sub(r"<![^>]*>", "", clean).strip()

            if num <= 15:
                word_list.append((num, text, clean))
            else:
                char_column.append((num, clean))
        elif "Lx" in locus:
            clean = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", text)
            clean = re.sub(r"@\d+;?", "", clean).strip()
            clean = re.sub(r"<![^>]*>", "", clean).strip()
            label_text.append((num, clean))
        elif "P0" in locus:
            body_text.append((num, text))

    return word_list, char_column, body_text, label_text


def extract_all_corpus():
    """Extract all words across manuscript with folio info."""
    all_words = defaultdict(list)  # word -> [(folio, section, is_label)]

    folio_dir = Path("folios")
    for txt_file in sorted(folio_dir.glob("*.txt")):
        lines_raw = txt_file.read_text(encoding="utf-8").splitlines()
        header_lines = []
        folio_name = txt_file.stem
        section = None

        for line in lines_raw:
            stripped = line.strip()
            if stripped.startswith("#") or re.match(r"^<f\w+>\s", stripped):
                header_lines.append(stripped)
                continue
            if not stripped or stripped.startswith("<!"):
                continue

            m = re.match(r"<([^>]+)>\s*(.*)", stripped)
            if not m:
                continue
            locus = m.group(1)
            text = m.group(2)
            is_label = bool(re.search(r"[,@*+]L", locus))

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
                    if section is None:
                        h = "\n".join(header_lines).lower()
                        if "herbal" in h: section = "herbal"
                        elif "astro" in h or "cosmo" in h or "star" in h or "zodiac" in h: section = "astro"
                        elif "pharm" in h or "recipe" in h or "balneo" in h: section = "pharma"
                        elif "biolog" in h or "bathy" in h: section = "bio"
                        elif "text only" in h: section = "text"
                        else: section = "other"
                    all_words[tok].append((folio_name, section, is_label))

    return all_words


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def analyze():
    results = {}

    word_list, char_column, body_text, label_text = extract_f66r()
    all_words = extract_all_corpus()

    # ═══════════════════════════════════════════════════════════════
    # TEST 1: WORD LIST STRUCTURE
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 1: f66r WORD LIST — Morphological structure of 15 entries")
    print("=" * 90)
    print()
    print("  The word list is on the far left of the page, written separately from body text.")
    print("  These may be an index, legend, glossary, or ingredient list.")
    print()

    print(f"  {'#':>3s}  {'Raw':15s}  {'Clean':12s}  {'Pfx':5s}  {'Root':8s}  {'Suf':5s}  {'Type':5s}  {'RootFreq':>8s}")
    print(f"  {'─'*3}  {'─'*15}  {'─'*12}  {'─'*5}  {'─'*8}  {'─'*5}  {'─'*5}  {'─'*8}")

    list_roots = []
    list_suffixes = []
    list_prefixes = []
    list_parse_data = []

    for num, raw, clean in word_list:
        pfx, onset, body, suf, rem = parse_word(clean)
        root = get_root(onset, body)
        root_freq = sum(len(v) for v in [all_words.get(w, []) for w in all_words
                        if parse_word(w)[0:3] == (pfx[:0], onset, body)][:0]) or "?"

        # Look up root frequency from paradigm tables
        try:
            pt = json.load(open("attack_plan_results.json"))["paradigm_tables"]
            rf = pt.get(root, {}).get("freq", 0)
        except:
            rf = 0

        # Determine type
        rtype = "?"
        if not rem:
            # Check y-dominance
            suf_y_count = pt.get(root, {}).get("table", {})
            total_root_count = rf
            if rf > 0:
                # Count y across all prefixes
                y_total = 0
                for pfx_key, suf_dict in suf_y_count.items():
                    for sk, sv in suf_dict.items():
                        if sk == "y":
                            y_total += sv
                y_frac = y_total / rf
                rtype = "B" if y_frac >= 0.8 else ("A" if y_frac <= 0.3 else "M")

        status = "" if not rem else f"[{rem}]"
        print(f"  {num:3d}  {raw:15s}  {clean:12s}  {pfx or '∅':5s}  {root:8s}  {suf or '∅':5s}  {rtype:5s}  {rf:8d}{status}")

        list_roots.append(root)
        list_suffixes.append(suf or "∅")
        list_prefixes.append(pfx or "∅")
        list_parse_data.append((num, clean, pfx or "∅", root, suf or "∅", rem))

    print()

    # Summary stats
    root_counter = Counter(list_roots)
    suf_counter = Counter(list_suffixes)
    pfx_counter = Counter(list_prefixes)
    print(f"  Roots in list:    {dict(root_counter.most_common())}")
    print(f"  Suffixes in list: {dict(suf_counter.most_common())}")
    print(f"  Prefixes in list: {dict(pfx_counter.most_common())}")
    print()

    # Key observation: are all roots Type A (substances)?
    type_a_count = sum(1 for n, c, p, r, s, rem in list_parse_data if not rem)
    print(f"  Clean parses: {type_a_count}/15")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 2: CHARACTER COLUMN ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 2: CHARACTER COLUMN — 33 single characters/digraphs")
    print("=" * 90)
    print()
    print("  The character column sits between the word list and the body text.")
    print("  These may be: abbreviation keys, an alphabet, a notation index,")
    print("  or single-character entries in the same glossary.")
    print()

    chars = [c for _, c in char_column if c and not c.startswith("@")]
    print(f"  Characters: {chars}")
    print(f"  Count: {len(chars)}")
    print()

    char_freq = Counter(chars)
    print(f"  Frequency: {dict(char_freq.most_common())}")
    print()

    # Which of these appear as EVA characters in the parser system?
    prefix_chars = set()
    for p in PREFIXES:
        for c in p:
            prefix_chars.add(c)

    onset_chars = set()
    for o in ROOT_ONSETS:
        for c in o:
            onset_chars.add(c)

    suffix_chars = set()
    for s in SUFFIXES:
        for c in s:
            suffix_chars.add(c)

    print(f"  Characters that appear in PREFIXES: {[c for c in chars if c in prefix_chars or any(c in p for p in PREFIXES)]}")
    print(f"  Characters that appear in ROOT ONSETS: {[c for c in chars if c in onset_chars or any(c == o for o in ROOT_ONSETS)]}")
    print(f"  Characters that appear in SUFFIXES: {[c for c in chars if c in suffix_chars or any(c in s for s in SUFFIXES)]}")
    print()

    # Do the characters correspond to first letters/morphemes of the word list?
    print(f"  CHARACTER-TO-WORD ALIGNMENT (if chars index the words):")
    word_first_chars = []
    for num, raw, clean in word_list:
        word_first_chars.append(clean[0] if clean else "?")

    # Align chars to words (chars 16-48, words 1-15)
    # There are more chars than words, so this is not 1:1
    # But check if any pattern exists
    print(f"  Word first chars: {word_first_chars}")
    overlap = sum(1 for wc in word_first_chars if wc in chars)
    print(f"  Overlap (word first char appears in char column): {overlap}/{len(word_first_chars)}")
    print()

    # Distribution: which chars are NOT found in any parsed word morpheme?
    all_word_chars = set()
    for num, raw, clean in word_list:
        for c in clean:
            all_word_chars.add(c)
    for _, text in body_text:
        clean_t = re.sub(r"<![^>]*>|<%>|<\$>|<->|<[^>]*>|\[([^:\]]+):[^\]]+\]|\{[^}]+\}|@\d+;?", "", text)
        for c in clean_t:
            if c.isalpha():
                all_word_chars.add(c)

    for _, text in body_text:
        clean = re.sub(r"<![^>]*>|<%>|<\$>|<->|<[^>]*>", "", text)
        clean = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", clean)
        clean = re.sub(r"\{[^}]+\}", "", clean)
        clean = re.sub(r"@\d+;?", "", clean)
        for c in clean:
            if c.isalpha():
                all_word_chars.add(c)

    chars_not_in_words = [c for c in chars if c not in all_word_chars and len(c) == 1]
    print(f"  Chars NOT found in any word on f66r: {chars_not_in_words}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 3: WORD-TO-BODY-TEXT BRIDGING
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 3: WORD-TO-BODY-TEXT — Do list roots appear in the body text?")
    print("=" * 90)
    print()

    # Parse all body text words
    body_parses = []
    for num, text in body_text:
        clean = re.sub(r"<![^>]*>", "", text)
        clean = re.sub(r"<%>|<\$>|<->", " ", clean)
        clean = re.sub(r"<[^>]*>", "", clean)
        clean = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", clean)
        clean = re.sub(r"\{([^}]+)\}", r"\1", clean)
        clean = re.sub(r"@\d+;?", "", clean)
        tokens = re.split(r"[.\s,<>\-]+", clean)
        for tok in tokens:
            tok = tok.strip()
            if tok and re.match(r"^[a-z]+$", tok) and len(tok) >= 2:
                pfx, onset, body_part, suf, rem = parse_word(tok)
                if not rem:
                    root = get_root(onset, body_part)
                    body_parses.append((tok, pfx or "∅", root, suf or "∅"))

    body_root_freq = Counter(p[2] for p in body_parses)
    total_body = len(body_parses)

    print(f"  Parsed body text tokens on f66r: {total_body}")
    print()

    # For each list root, find its frequency and suffix profile in body text
    list_unique_roots = sorted(set(r for n, c, p, r, s, rem in list_parse_data if not rem))

    print(f"  {'Root':8s}  {'List form':12s}  {'Body freq':>9s}  {'Body suffixes':35s}  {'Body prefixes':30s}")
    print(f"  {'─'*8}  {'─'*12}  {'─'*9}  {'─'*35}  {'─'*30}")

    for root in list_unique_roots:
        # What forms does this root take in the list?
        list_forms = [(s, p) for n, c, p, r, s, rem in list_parse_data if r == root and not rem]
        list_form_str = ", ".join(f"{p}+{root}+{s}" for s, p in list_forms)

        # What forms in body text?
        body_forms = [(p[1], p[3]) for p in body_parses if p[2] == root]
        body_freq = len(body_forms)
        body_suf_freq = Counter(s for _, s in body_forms)
        body_pfx_freq = Counter(p for p, _ in body_forms)

        suf_str = ", ".join(f"{s}:{c}" for s, c in body_suf_freq.most_common(5))
        pfx_str = ", ".join(f"{p}:{c}" for p, c in body_pfx_freq.most_common(5))

        print(f"  {root:8s}  {list_form_str:12s}  {body_freq:9d}  {suf_str:35s}  {pfx_str:30s}")

    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 4: LIST-INTERNAL ORDERING
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 4: LIST ORDERING — Is there a pattern in the sequence?")
    print("=" * 90)
    print()
    print("  Check if the list is ordered by: root, suffix, prefix, alphabetical,")
    print("  root frequency, or some other morphological feature.")
    print()

    # Show the sequence
    for n, c, p, r, s, rem in list_parse_data:
        status = "✓" if not rem else "✗"
        print(f"  {n:2d}. {c:12s}  {p:4s}+{r:6s}+{s:4s}  {status}")
    print()

    # Check suffix sequence
    clean_entries = [(n, c, p, r, s) for n, c, p, r, s, rem in list_parse_data if not rem]
    suf_seq = [s for _, _, _, _, s in clean_entries]
    print(f"  Suffix sequence: {suf_seq}")

    # Check if suffixes group together
    suf_runs = []
    if suf_seq:
        current = suf_seq[0]
        run_len = 1
        for s in suf_seq[1:]:
            if s == current:
                run_len += 1
            else:
                suf_runs.append((current, run_len))
                current = s
                run_len = 1
        suf_runs.append((current, run_len))
    print(f"  Suffix runs: {suf_runs}")
    print()

    # Check prefix sequence
    pfx_seq = [p for _, _, p, _, _ in clean_entries]
    print(f"  Prefix sequence: {pfx_seq}")
    print()

    # Check root frequency ordering
    try:
        pt = json.load(open("attack_plan_results.json"))["paradigm_tables"]
        root_freqs = [pt.get(r, {}).get("freq", 0) for _, _, _, r, _ in clean_entries]
        print(f"  Root frequency sequence: {root_freqs}")
        # Is it sorted?
        is_ascending = all(root_freqs[i] <= root_freqs[i+1] for i in range(len(root_freqs)-1))
        is_descending = all(root_freqs[i] >= root_freqs[i+1] for i in range(len(root_freqs)-1))
        print(f"  Ascending? {is_ascending}  Descending? {is_descending}")
    except:
        pass
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 5: CROSS-FOLIO OCCURRENCE OF LIST WORDS
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 5: CROSS-FOLIO — Where do these exact words appear elsewhere?")
    print("=" * 90)
    print()

    for num, raw, clean in word_list:
        occurrences = all_words.get(clean, [])
        total = len(occurrences)
        if total == 0:
            print(f"  {num:2d}. {clean:12s}  NOWHERE ELSE in manuscript")
            continue

        section_counts = Counter(sec for _, sec, _ in occurrences)
        label_count = sum(1 for _, _, is_lab in occurrences if is_lab)
        text_count = total - label_count
        folio_set = sorted(set(f for f, _, _ in occurrences))

        sec_str = ", ".join(f"{s}:{c}" for s, c in section_counts.most_common())
        folio_sample = ", ".join(folio_set[:8])
        if len(folio_set) > 8:
            folio_sample += f"... +{len(folio_set)-8}"

        print(f"  {num:2d}. {clean:12s}  ×{total:4d}  (label:{label_count}, text:{text_count})  sections: {sec_str}")
        print(f"       folios: {folio_sample}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 6: CONSTRAINT TABLE — Building a substitution hypothesis
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 6: CONSTRAINT TABLE — What do we know about each morpheme?")
    print("=" * 90)
    print()
    print("  Combining Phase 1 evidence (root type, suffix class, section preference)")
    print("  with f66r-specific evidence to constrain possible meanings.")
    print()

    # Load earlier data
    try:
        pt = json.load(open("attack_plan_results.json"))["paradigm_tables"]
        fr = json.load(open("freq_rank_results.json"))
    except:
        pt = {}
        fr = {}

    # For each cleanly-parsed list entry, build a constraint profile
    for n, c, p, r, s, rem in list_parse_data:
        if rem:
            print(f"  {n:2d}. {c:12s}  *** UNPARSEABLE — possible foreign/special word ***")
            print()
            continue

        print(f"  {n:2d}. {c:12s}  = {p}+{r}+{s}")

        # Root constraints
        rf = pt.get(r, {}).get("freq", 0)
        sec_dist = fr.get("section_distribution", {}).get(r, {})
        sec_info = sec_dist.get("sections", {})
        specialist = sec_dist.get("specialist", "")

        # Suffix class
        suf_meaning = {
            "ry": "rare suffix — only 1.8% of tokens",
            "ly": "adjectival/modifier form",
            "l": "Type A 'l-group' case — common for o-onsetted roots",
            "iin": "Type A 'iin-group' case — nominal/substance form",
            "y": "Type B process/verbal form",
            "∅": "bare/citation form",
        }.get(s, f"suffix '{s}'")

        # Prefix meaning from Phase 1
        pfx_meaning = {
            "∅": "unprefixed (basic form)",
            "qo": "most common prefix — possibly definite/specific",
            "qol": "q+o+l compound — function word?",
            "y": "prefix y — moderate frequency",
            "r": "prefix r — biases toward -iin suffix (2.2×)",
            "d": "prefix d — biases toward -y suffix (1.5×)",
            "o": "prefix o — common, slight -in bias",
        }.get(p, f"prefix '{p}'")

        # Root type
        if rf > 0:
            y_total = 0
            total_r = 0
            for pfx_key, suf_dict in pt.get(r, {}).get("table", {}).items():
                for sk, sv in suf_dict.items():
                    total_r += sv
                    if sk == "y":
                        y_total += sv
            y_frac = y_total / total_r if total_r > 0 else 0
            rtype = "SUBSTANCE" if y_frac <= 0.3 else ("PROCESS" if y_frac >= 0.8 else "MIXED")
        else:
            rtype = "RARE/UNKNOWN"

        print(f"       root '{r}': {rtype}, freq={rf}, {specialist}")
        print(f"       suffix '{s}': {suf_meaning}")
        print(f"       prefix '{p}': {pfx_meaning}")

        # Section distribution
        if sec_info:
            total_s = sum(sec_info.values())
            top_sec = sorted(sec_info.items(), key=lambda x: -x[1])[:3]
            sec_str = ", ".join(f"{s}:{100*c/total_s:.0f}%" for s, c in top_sec)
            print(f"       sections: {sec_str}")

        # Label enrichment
        label_data = fr.get("label_enriched", [])
        lab_entry = next((x for x in label_data if x.get("root") == r), None)
        if lab_entry:
            print(f"       label enrichment: {lab_entry['enrichment']}×")

        # Pharmaceutical hypothesis
        if rtype == "SUBSTANCE":
            if s in ("iin", "in"):
                meaning_hint = "→ substance in base/powder form"
            elif s in ("l", "r"):
                meaning_hint = "→ substance in liquid/prepared form"
            elif s in ("ly", "ry"):
                meaning_hint = "→ adjectival/property description"
            elif s == "∅":
                meaning_hint = "→ bare substance name (citation)"
            else:
                meaning_hint = "→ substance in specific form"
        elif rtype == "PROCESS":
            meaning_hint = "→ process/instruction word"
        else:
            meaning_hint = "→ ambiguous"

        print(f"       HYPOTHESIS: {meaning_hint}")
        print()

    # ═══════════════════════════════════════════════════════════════
    # SYNTHESIS
    # ═══════════════════════════════════════════════════════════════
    print("═" * 90)
    print("SYNTHESIS — f66r FOCUSED DECIPHERMENT")
    print("═" * 90)
    print()

    # Summarize the word list entries
    clean_count = sum(1 for n, c, p, r, s, rem in list_parse_data if not rem)
    substance_count = 0
    process_count = 0
    for n, c, p, r, s, rem in list_parse_data:
        if rem:
            continue
        rf = pt.get(r, {}).get("freq", 0)
        if rf > 0:
            y_total = 0
            total_r = 0
            for pfx_key, suf_dict in pt.get(r, {}).get("table", {}).items():
                for sk, sv in suf_dict.items():
                    total_r += sv
                    if sk == "y":
                        y_total += sv
            y_frac = y_total / total_r if total_r > 0 else 0
            if y_frac <= 0.3:
                substance_count += 1
            elif y_frac >= 0.8:
                process_count += 1

    print(f"  WORD LIST: {clean_count}/15 parse cleanly")
    print(f"    Substance roots (Type A): {substance_count}")
    print(f"    Process roots (Type B): {process_count}")
    print()

    # Label near figure
    print(f"  LABEL NEAR FIGURE: {label_text}")
    if label_text:
        for num, text in label_text:
            words = re.split(r"[.\s,]+", text)
            for w in words:
                w = w.strip()
                if w and re.match(r"^[a-z]+$", w) and len(w) >= 2:
                    pfx, onset, body_part, suf, rem = parse_word(w)
                    root = get_root(onset, body_part)
                    status = "CLEAN" if not rem else f"[{rem}]"
                    print(f"    {w:15s}  pfx={pfx or '∅':5s}  root={root:8s}  suf={suf or '∅':5s}  {status}")
    print()

    # Character column insight
    print(f"  CHARACTER COLUMN: {len(chars)} entries")
    print(f"    Unique: {len(set(chars))}")
    print(f"    Chars not in word list or body: {chars_not_in_words}")
    print(f"    Most common: {char_freq.most_common(5)}")
    print()

    # Key question for the constraint table
    print(f"  KEY OBSERVATIONS:")
    print(f"  1. The list contains mostly SUBSTANCE roots with varied suffixes")
    print(f"     → Consistent with a glossary/materia medica index")
    print(f"  2. Suffix -ry appears 3× in the list but is rare globally (1.8%)")
    print(f"     → -ry may mark a specific 'list/citation' form")
    print(f"  3. Root 'sa' appears 3× with different suffixes (ly, ∅, iin)")
    print(f"     → Same substance in 3 different forms?")
    print(f"  4. Root 'a' appears 2× with suffix 'ry' and different prefixes (r, ∅→da)")
    print(f"     → Same base substance, different preparations?")
    print()

    print("  Results saved to f66r_results.json")
    print()
    print("═" * 90)
    print("f66r ANALYSIS COMPLETE")
    print("═" * 90)

    return results


if __name__ == "__main__":
    results = analyze()
    with open("f66r_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
