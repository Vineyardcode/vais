#!/usr/bin/env python3
"""
Herbal Cross-Reference Analysis

The ring text grammar extraction revealed that ch-/sh- root families are
3× enriched in zodiac ring texts vs labels, and that tal-/kal- families
are nearly absent from ring texts. This script:

  1. Parses ALL herbal section folios (A and B) to extract word-level data
  2. Computes root family distributions across herbal-A, herbal-B, pharma
  3. Cross-references ring text vocabulary against herbal vocabulary
  4. Tests whether ring text ch-/sh- enrichment matches herbal-A distribution
  5. Identifies "bridge vocabulary" — words shared between zodiac rings & herbal
  6. Tests whether ring text function words appear in herbal prose
  7. Compares morphological profiles (prefix/suffix distributions)
  8. Maps specific ring text roots to their herbal page contexts
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import get_root, result_path, classify_folio

# ── Section classification ───────────────────────────────────────────────

# Folio ranges for manuscript sections
# Based on standard Voynich section assignments
SECTION_MAP = {}



# ── Parser (from currier_register_comparison.py — fuller version) ────────────────────────

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
    best = None
    best_score = -1
    pfx_opts = [""]
    for pfx in PREFIXES:
        if word.startswith(pfx):
            pfx_opts.append(pfx)
    for pfx in pfx_opts:
        r1 = word[len(pfx):]
        onset_opts = [""]
        for o in ROOT_ONSETS:
            if r1.startswith(o):
                onset_opts.append(o)
        for onset in onset_opts:
            r2 = r1[len(onset):]
            body_opts = [""]
            for b in ROOT_BODIES:
                if r2.startswith(b):
                    body_opts.append(b)
            for body in body_opts:
                r3 = r2[len(body):]
                suf_opts = [""]
                for s in SUFFIXES:
                    if r3 == s:
                        suf_opts.append(s)
                for suf in suf_opts:
                    remainder = "" if suf and r3 == suf else r3 if not suf else r3
                    if suf and r3 == suf:
                        remainder = ""
                    elif not suf:
                        remainder = r3
                    else:
                        remainder = r3  # won't match, handled by r3==s check
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




# ── Root family classification ───────────────────────────────────────────

def root_family(onset):
    """Classify root onset into a family."""
    if onset in ("ch",):
        return "ch-"
    elif onset in ("sh",):
        return "sh-"
    elif onset in ("k", "kch", "ksh"):
        return "k-"
    elif onset in ("t", "tch", "tsh"):
        return "t-"
    elif onset in ("f", "fch", "fsh"):
        return "f-"
    elif onset in ("p", "pch", "psh"):
        return "p-"
    elif onset in ("ckh",):
        return "ckh-"
    elif onset in ("cth",):
        return "cth-"
    elif onset in ("cph",):
        return "cph-"
    elif onset in ("cfh",):
        return "cfh-"
    elif onset == "":
        return "∅"
    return onset + "-"


# ── Data extraction ──────────────────────────────────────────────────────

def clean_token(tok):
    """Clean an IVTFF token for parsing."""
    tok = re.sub(r'\[([^:]+):[^\]]+\]', r'\1', tok)
    tok = re.sub(r'\{([^}]+)\}', r'\1', tok)
    tok = re.sub(r'@\d+;?', '', tok)
    tok = tok.replace('?', '')
    tok = tok.strip(",'")
    return tok


def extract_all_folios():
    """Extract parsed words from all folio files, grouped by section."""
    folio_dir = Path("folios")
    section_data = defaultdict(list)  # section -> [(word, pfx, root, suf, folio)]
    section_words = defaultdict(Counter)  # section -> word frequencies

    for txt_file in sorted(folio_dir.glob("*.txt")):
        section = classify_folio(txt_file)
        folio_name = txt_file.stem

        lines = txt_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line or line.startswith("<!"):
                continue

            m = re.match(r'<([^>]+)>\s*(.*)', line)
            if not m:
                continue

            locus = m.group(1)
            text = m.group(2)

            # Skip labels — we want body/paragraph text only
            is_label = bool(re.search(r'[,@*+]L', locus))
            if is_label:
                continue

            # Also skip ring texts (@Cc) — we have those separately
            if '@Cc' in locus:
                continue

            # Clean text
            text = re.sub(r'<![^>]*>', '', text)
            text = re.sub(r'<%>|<\$>|<->|<\.>', ' ', text)
            text = re.sub(r'<[^>]*>', '', text)
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
            text = re.sub(r'\{([^}]+)\}', r'\1', text)
            text = re.sub(r'@\d+;?', '', text)

            tokens = re.split(r'[.\s,<>\-]+', text)
            for tok in tokens:
                tok = tok.strip()
                if not tok or '?' in tok or "'" in tok:
                    continue
                if re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                    pfx, onset, body, suf, rem = parse_word(tok)
                    if not rem:
                        root = get_root(onset, body)
                        section_data[section].append((tok, pfx, root, suf, folio_name))
                        section_words[section][tok] += 1

    return section_data, section_words


def extract_ring_text_data():
    """Load ring text data from grammar_results.json."""
    with open(result_path("grammar_results.json")) as f:
        data = json.load(f)

    ring_words = Counter()
    ring_roots = Counter()
    ring_families = Counter()
    ring_parsed = []

    for sent in data["tagged_sentences"]:
        for tag in sent["tagged"]:
            word = tag["word"]
            ring_words[word] += 1
            # Re-parse with the fuller parser for consistency
            pfx, onset, body, suf, rem = parse_word(word)
            if not rem:
                root = get_root(onset, body)
                fam = root_family(onset)
                ring_roots[root] += 1
                ring_families[fam] += 1
                ring_parsed.append((word, pfx, root, suf))

    return ring_words, ring_roots, ring_families, ring_parsed


# ══════════════════════════════════════════════════════════════════════════
# PHASES
# ══════════════════════════════════════════════════════════════════════════

def part1_section_profiles(section_data, section_words):
    """Profile each section's basic statistics."""
    print("=" * 72)
    print("SECTION PROFILES")
    print("=" * 72)

    for section in ["herbal-A", "herbal-B", "pharma", "zodiac", "bio", "cosmo", "text"]:
        data = section_data.get(section, [])
        words = section_words.get(section, Counter())
        if not data:
            print(f"\n  {section}: no data")
            continue
        folios = set(d[4] for d in data)
        print(f"\n  {section}:")
        print(f"    Folios: {len(folios)}")
        print(f"    Total parsed tokens: {len(data)}")
        print(f"    Unique words: {len(words)}")
        print(f"    Top 10: {dict(words.most_common(10))}")


def part2_root_family_comparison(section_data, ring_families):
    """Compare root family distributions across sections and ring texts."""
    print("\n" + "=" * 72)
    print("ROOT FAMILY DISTRIBUTION COMPARISON")
    print("=" * 72)

    # Compute family distributions per section
    sections = ["herbal-A", "herbal-B", "pharma", "bio", "text"]
    section_families = {}

    for section in sections:
        data = section_data.get(section, [])
        if not data:
            continue
        fam_counts = Counter()
        for word, pfx, root, suf, folio in data:
            # Re-derive onset from root
            for ro in ROOT_ONSETS:
                if root.startswith(ro):
                    fam = root_family(ro)
                    fam_counts[fam] += 1
                    break
            else:
                fam_counts["∅"] += 1
        section_families[section] = fam_counts

    # Add ring text families
    section_families["ring-text"] = ring_families

    # Get all families
    all_fams = set()
    for fams in section_families.values():
        all_fams.update(fams.keys())
    all_fams = sorted(all_fams)

    # Print comparison table
    sections_present = [s for s in sections + ["ring-text"] if s in section_families]
    header = f"  {'Family':8s}" + "".join(f"  {s:>12s}" for s in sections_present)
    print(f"\n{header}")
    print("  " + "-" * (8 + 14 * len(sections_present)))

    for fam in all_fams:
        row = f"  {fam:8s}"
        for section in sections_present:
            total = sum(section_families[section].values())
            count = section_families[section].get(fam, 0)
            pct = 100 * count / total if total else 0
            row += f"  {pct:10.1f}%"
        print(row)

    # Totals
    row = f"  {'TOTAL':8s}"
    for section in sections_present:
        total = sum(section_families[section].values())
        row += f"  {total:10d} "
    print(row)

    # Compute key ratios for ring text vs herbal-A
    if "herbal-A" in section_families:
        print(f"\n  Ring-text / Herbal-A enrichment ratios:")
        herbA = section_families["herbal-A"]
        herbA_total = sum(herbA.values())
        ring_total = sum(ring_families.values())
        for fam in sorted(all_fams):
            h_pct = 100 * herbA.get(fam, 0) / herbA_total if herbA_total else 0
            r_pct = 100 * ring_families.get(fam, 0) / ring_total if ring_total else 0
            if h_pct > 0.5:
                ratio = r_pct / h_pct
                marker = " *** ENRICHED" if ratio > 1.5 else (" ** depleted" if ratio < 0.5 else "")
                print(f"    {fam:8s}  herbalA={h_pct:5.1f}%  ring={r_pct:5.1f}%"
                      f"  ratio={ratio:.2f}×{marker}")


def part3_vocabulary_overlap(section_words, ring_words):
    """Jaccard overlap between ring text vocabulary and each section."""
    print("\n" + "=" * 72)
    print("VOCABULARY OVERLAP (RING TEXT vs SECTIONS)")
    print("=" * 72)

    ring_vocab = set(ring_words.keys())
    print(f"\n  Ring text unique words: {len(ring_vocab)}")

    for section in ["herbal-A", "herbal-B", "pharma", "bio", "text"]:
        words = section_words.get(section, Counter())
        if not words:
            continue
        sect_vocab = set(words.keys())
        shared = ring_vocab & sect_vocab
        jaccard = len(shared) / len(ring_vocab | sect_vocab) if (ring_vocab | sect_vocab) else 0
        ring_coverage = 100 * len(shared) / len(ring_vocab) if ring_vocab else 0
        print(f"\n  Ring vs {section}:")
        print(f"    {section} unique words: {len(sect_vocab)}")
        print(f"    Shared: {len(shared)}")
        print(f"    Jaccard: {jaccard:.4f}")
        print(f"    Ring coverage: {ring_coverage:.1f}% of ring words found in {section}")

        # Top shared words by ring frequency
        shared_by_freq = sorted(shared, key=lambda w: ring_words[w], reverse=True)
        print(f"    Top shared (by ring freq): ", end="")
        for w in shared_by_freq[:12]:
            print(f"{w}({ring_words[w]})", end=" ")
        print()

        # Ring-exclusive words (not in this section)
        ring_only = ring_vocab - sect_vocab
        top_ring_only = sorted(ring_only, key=lambda w: ring_words[w], reverse=True)
        print(f"    Top ring-only (not in {section}): ", end="")
        for w in top_ring_only[:10]:
            print(f"{w}({ring_words[w]})", end=" ")
        print()

    # Special: how much ring vocabulary appears NOWHERE in any herbal text?
    all_herbal = set()
    for section in ["herbal-A", "herbal-B", "pharma"]:
        all_herbal.update(section_words.get(section, {}).keys())
    ring_unique = ring_vocab - all_herbal
    print(f"\n  Ring words NOT found in any herbal/pharma text: {len(ring_unique)}"
          f" ({100*len(ring_unique)/len(ring_vocab):.1f}%)")
    top_unique = sorted(ring_unique, key=lambda w: ring_words[w], reverse=True)
    print(f"    Top examples: ", end="")
    for w in top_unique[:15]:
        print(f"{w}({ring_words[w]})", end=" ")
    print()


def part4_function_words_in_herbal(section_words, ring_words):
    """Do ring text function words appear in herbal prose?"""
    print("\n" + "=" * 72)
    print("FUNCTION WORDS IN HERBAL CONTEXT")
    print("=" * 72)

    func_words = ["aiin", "ar", "al", "s", "daiin", "dal", "am", "dar",
                   "y", "or", "ol", "dy", "r", "air", "shey", "chey", "chy"]

    print(f"\n  {'Word':10s}  {'Ring':>6s}  {'HerbA':>8s}  {'HerbB':>8s}"
          f"  {'Pharma':>8s}  {'Bio':>6s}  {'Text':>6s}")
    print("  " + "-" * 65)

    for fw in func_words:
        row = f"  {fw:10s}"
        row += f"  {ring_words.get(fw, 0):6d}"
        for section in ["herbal-A", "herbal-B", "pharma", "bio", "text"]:
            words = section_words.get(section, Counter())
            row += f"  {words.get(fw, 0):8d}"
        print(row)

    # Compute per-section rates
    print(f"\n  Function word rate (% of total tokens):")
    func_set = set(func_words)
    for section in ["ring-text", "herbal-A", "herbal-B", "pharma", "bio", "text"]:
        if section == "ring-text":
            total = sum(ring_words.values())
            func_count = sum(ring_words.get(fw, 0) for fw in func_words)
        else:
            words = section_words.get(section, Counter())
            total = sum(words.values())
            func_count = sum(words.get(fw, 0) for fw in func_words)
        if total:
            pct = 100 * func_count / total
            print(f"    {section:12s}  {func_count:5d} / {total:6d}  ({pct:.1f}%)")


def part5_prefix_suffix_comparison(section_data, ring_parsed):
    """Compare morphological profiles across sections and ring texts."""
    print("\n" + "=" * 72)
    print("MORPHOLOGICAL PROFILE COMPARISON")
    print("=" * 72)

    # Prefix distribution per section
    sections = ["herbal-A", "herbal-B", "pharma", "bio", "text"]
    pfx_dists = {}
    suf_dists = {}

    for section in sections:
        data = section_data.get(section, [])
        if not data:
            continue
        pfx_counts = Counter()
        suf_counts = Counter()
        for word, pfx, root, suf, folio in data:
            # Bucket prefixes
            if pfx.startswith("o"):
                pfx_counts["o-"] += 1
            elif pfx.startswith("q"):
                pfx_counts["q-"] += 1
            elif pfx.startswith("d") or pfx.startswith("s"):
                pfx_counts["d/s-"] += 1
            elif pfx.startswith("y"):
                pfx_counts["y-"] += 1
            elif pfx == "":
                pfx_counts["∅"] += 1
            else:
                pfx_counts["other"] += 1

            # Bucket suffixes
            if suf in ("y", "dy", "ly", "ry", "ny", "my", "ily", "iry", "iny"):
                suf_counts["-y"] += 1
            elif suf in ("iin", "iir", "iil", "iiny", "iiiny", "ii", "iii"):
                suf_counts["-iin"] += 1
            elif suf in ("in", "ir", "il", "id", "im"):
                suf_counts["-Cr"] += 1
            elif suf in ("n", "m", "d", "l", "r"):
                suf_counts["-C"] += 1
            elif suf == "":
                suf_counts["∅"] += 1
            else:
                suf_counts["other"] += 1
        pfx_dists[section] = pfx_counts
        suf_dists[section] = suf_counts

    # Ring text prefix/suffix
    ring_pfx = Counter()
    ring_suf = Counter()
    for word, pfx, root, suf in ring_parsed:
        if pfx.startswith("o"):
            ring_pfx["o-"] += 1
        elif pfx.startswith("q"):
            ring_pfx["q-"] += 1
        elif pfx.startswith("d") or pfx.startswith("s"):
            ring_pfx["d/s-"] += 1
        elif pfx.startswith("y"):
            ring_pfx["y-"] += 1
        elif pfx == "":
            ring_pfx["∅"] += 1
        else:
            ring_pfx["other"] += 1

        if suf in ("y", "dy", "ly", "ry", "ny", "my", "ily", "iry", "iny"):
            ring_suf["-y"] += 1
        elif suf in ("iin", "iir", "iil", "iiny", "iiiny", "ii", "iii"):
            ring_suf["-iin"] += 1
        elif suf in ("in", "ir", "il", "id", "im"):
            ring_suf["-Cr"] += 1
        elif suf in ("n", "m", "d", "l", "r"):
            ring_suf["-C"] += 1
        elif suf == "":
            ring_suf["∅"] += 1
        else:
            ring_suf["other"] += 1

    pfx_dists["ring-text"] = ring_pfx
    suf_dists["ring-text"] = ring_suf

    # Print prefix table
    all_pfx = sorted(set(p for d in pfx_dists.values() for p in d))
    sections_present = [s for s in ["ring-text"] + sections if s in pfx_dists]

    print(f"\n  PREFIX DISTRIBUTION:")
    header = f"  {'Prefix':8s}" + "".join(f" {s:>12s}" for s in sections_present)
    print(header)
    for pfx in all_pfx:
        row = f"  {pfx:8s}"
        for section in sections_present:
            total = sum(pfx_dists[section].values())
            count = pfx_dists[section].get(pfx, 0)
            pct = 100 * count / total if total else 0
            row += f" {pct:10.1f}%"
        print(row)

    # Print suffix table
    print(f"\n  SUFFIX DISTRIBUTION:")
    all_suf = sorted(set(s for d in suf_dists.values() for s in d))
    header = f"  {'Suffix':8s}" + "".join(f" {s:>12s}" for s in sections_present)
    print(header)
    for sf in all_suf:
        row = f"  {sf:8s}"
        for section in sections_present:
            total = sum(suf_dists[section].values())
            count = suf_dists[section].get(sf, 0)
            pct = 100 * count / total if total else 0
            row += f" {pct:10.1f}%"
        print(row)


def part6_bridge_vocabulary(section_data, section_words, ring_words):
    """Find words that appear in BOTH ring texts AND herbal-A, ranked by
    informativeness (not just function words)."""
    print("\n" + "=" * 72)
    print("BRIDGE VOCABULARY (RING ↔ HERBAL-A)")
    print("=" * 72)

    herbA_words = section_words.get("herbal-A", Counter())
    ring_vocab = set(ring_words.keys())
    herbA_vocab = set(herbA_words.keys())
    bridge = ring_vocab & herbA_vocab

    # Function words (to filter out)
    func_set = {"aiin", "ar", "al", "s", "daiin", "dal", "am", "dar",
                "y", "or", "ol", "dy", "r", "air", "shey", "chey", "chy",
                "o", "d", "daiir", "shal", "sal", "sar", "dair"}

    content_bridge = bridge - func_set
    print(f"\n  Total bridge words: {len(bridge)}")
    print(f"  Content bridge (excl function words): {len(content_bridge)}")

    # Score bridge words by combined frequency importance
    ring_total = sum(ring_words.values())
    herbA_total = sum(herbA_words.values())

    bridge_scores = []
    for w in content_bridge:
        r_freq = ring_words[w]
        h_freq = herbA_words[w]
        # Geometric mean of relative frequencies (rewards high in both)
        r_rel = r_freq / ring_total
        h_rel = h_freq / herbA_total
        score = math.sqrt(r_rel * h_rel)
        bridge_scores.append((w, r_freq, h_freq, score))

    bridge_scores.sort(key=lambda x: -x[3])

    print(f"\n  Top 30 bridge words (by geometric mean of relative freq):")
    print(f"  {'Word':16s}  {'Ring':>5s}  {'HerbA':>6s}  {'Score':>8s}")
    for w, rf, hf, sc in bridge_scores[:30]:
        # Parse the word
        pfx, onset, body, suf, rem = parse_word(w)
        root = get_root(onset, body)
        fam = root_family(onset)
        print(f"  {w:16s}  {rf:5d}  {hf:6d}  {sc:8.5f}  [{fam} {root}]")

    # Which herbal folios contain the top bridge words?
    print(f"\n  Top bridge words — herbal folio distribution:")
    herbA_data = section_data.get("herbal-A", [])
    for w, rf, hf, sc in bridge_scores[:15]:
        folio_counts = Counter()
        for word, pfx, root, suf, folio in herbA_data:
            if word == w:
                folio_counts[folio] += 1
        top_folios = folio_counts.most_common(8)
        print(f"    {w:16s}  in {len(folio_counts)} folios: {dict(top_folios)}")

    return bridge_scores


def part7_root_mapping(section_data, ring_parsed):
    """Map specific ring text roots to their herbal page contexts to test
    whether ring roots describe botanical properties."""
    print("\n" + "=" * 72)
    print("RING TEXT ROOT → HERBAL CONTEXT MAPPING")
    print("=" * 72)

    # Get the most common roots in ring texts
    ring_root_counts = Counter(root for word, pfx, root, suf in ring_parsed)

    # Get herbal-A root usage with folio context
    herbA_data = section_data.get("herbal-A", [])
    herbA_root_folios = defaultdict(Counter)  # root -> folio -> count
    herbA_root_total = Counter()

    for word, pfx, root, suf, folio in herbA_data:
        herbA_root_folios[root][folio] += 1
        herbA_root_total[root] += 1

    # For top 20 ring text roots: where do they appear in herbal-A?
    print(f"\n  Top 20 ring text roots → herbal-A distribution:")
    for root, ring_count in ring_root_counts.most_common(20):
        herbA_count = herbA_root_total.get(root, 0)
        n_folios = len(herbA_root_folios.get(root, {}))
        fam = root_family(root[:2] if len(root) >= 2 else root)
        if herbA_count > 0:
            top_folios = dict(herbA_root_folios[root].most_common(5))
            print(f"    {root:10s} [{fam:5s}]  ring={ring_count:3d}  herbA={herbA_count:4d}"
                  f"  in {n_folios:3d} folios  top: {top_folios}")
        else:
            print(f"    {root:10s} [{fam:5s}]  ring={ring_count:3d}  herbA=   0  RING-ONLY ROOT")

    # Reverse: what are the most common herbal-A roots NOT in ring texts?
    ring_roots_set = set(ring_root_counts.keys())
    herbA_only = [(r, c) for r, c in herbA_root_total.most_common(50)
                  if r not in ring_roots_set]
    print(f"\n  Top 15 herbal-A roots absent from ring texts:")
    for root, count in herbA_only[:15]:
        fam = root_family(root[:2] if len(root) >= 2 else root)
        n_folios = len(herbA_root_folios.get(root, {}))
        print(f"    {root:10s} [{fam:5s}]  herbA={count:4d}  in {n_folios:3d} folios")


def part8_synthesis(section_data, section_words, ring_words, ring_families, ring_parsed):
    """Synthesize cross-reference findings."""
    print("\n" + "=" * 72)
    print("CROSS-REFERENCE SYNTHESIS")
    print("=" * 72)

    herbA_words = section_words.get("herbal-A", Counter())
    herbA_vocab = set(herbA_words.keys())
    ring_vocab = set(ring_words.keys())

    shared = ring_vocab & herbA_vocab
    ring_total = sum(ring_words.values())
    shared_tokens = sum(ring_words[w] for w in shared)

    print(f"\n  Ring text vocabulary: {len(ring_vocab)} types, {ring_total} tokens")
    print(f"  Herbal-A vocabulary: {len(herbA_vocab)} types")
    print(f"  Shared types: {len(shared)} ({100*len(shared)/len(ring_vocab):.1f}% of ring)")
    print(f"  Shared reach: {shared_tokens} of {ring_total} ring tokens"
          f" ({100*shared_tokens/ring_total:.1f}%) come from herbal-shared words")

    # Does ring text ch-/sh- enrichment match herbal-A?
    print(f"\n  Root family alignment test:")
    print(f"    If ring texts and herbal-A share the same register, their root")
    print(f"    family distributions should be SIMILAR (ratio ≈ 1.0×).")
    print(f"    If ring texts have a DIFFERENT register, ratios will diverge.")

    # Compute Jensen-Shannon divergence between ring and herbal-A families
    herbA_data = section_data.get("herbal-A", [])
    herbA_fam = Counter()
    for word, pfx, root, suf, folio in herbA_data:
        for ro in ROOT_ONSETS:
            if root.startswith(ro):
                herbA_fam[root_family(ro)] += 1
                break
        else:
            herbA_fam["∅"] += 1

    all_fams = set(ring_families.keys()) | set(herbA_fam.keys())
    ring_total_fam = sum(ring_families.values())
    herbA_total_fam = sum(herbA_fam.values())

    jsd = 0
    for fam in all_fams:
        p = ring_families.get(fam, 0) / ring_total_fam if ring_total_fam else 0
        q = herbA_fam.get(fam, 0) / herbA_total_fam if herbA_total_fam else 0
        m = (p + q) / 2
        if p > 0 and m > 0:
            jsd += 0.5 * p * math.log2(p / m)
        if q > 0 and m > 0:
            jsd += 0.5 * q * math.log2(q / m)

    print(f"    Jensen-Shannon divergence (ring vs herbal-A families): {jsd:.4f}")
    if jsd < 0.02:
        print(f"    → VERY SIMILAR distributions — same register")
    elif jsd < 0.05:
        print(f"    → Similar with minor differences")
    elif jsd < 0.10:
        print(f"    → Moderately different")
    else:
        print(f"    → SUBSTANTIALLY different registers")

    # Also compute vs herbal-B, bio for comparison
    for comp_section in ["herbal-B", "bio", "text"]:
        comp_data = section_data.get(comp_section, [])
        if not comp_data:
            continue
        comp_fam = Counter()
        for word, pfx, root, suf, folio in comp_data:
            for ro in ROOT_ONSETS:
                if root.startswith(ro):
                    comp_fam[root_family(ro)] += 1
                    break
            else:
                comp_fam["∅"] += 1

        comp_total = sum(comp_fam.values())
        jsd_comp = 0
        combined_fams = set(ring_families.keys()) | set(comp_fam.keys())
        for fam in combined_fams:
            p = ring_families.get(fam, 0) / ring_total_fam if ring_total_fam else 0
            q = comp_fam.get(fam, 0) / comp_total if comp_total else 0
            m = (p + q) / 2
            if p > 0 and m > 0:
                jsd_comp += 0.5 * p * math.log2(p / m)
            if q > 0 and m > 0:
                jsd_comp += 0.5 * q * math.log2(q / m)
        print(f"    JSD (ring vs {comp_section}): {jsd_comp:.4f}")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Extracting all folios...\n")
    section_data, section_words = extract_all_folios()

    print("Loading ring text data...\n")
    ring_words, ring_roots, ring_families, ring_parsed = extract_ring_text_data()

    part1_section_profiles(section_data, section_words)
    part2_root_family_comparison(section_data, ring_families)
    part3_vocabulary_overlap(section_words, ring_words)
    part4_function_words_in_herbal(section_words, ring_words)
    part5_prefix_suffix_comparison(section_data, ring_parsed)
    bridge_scores = part6_bridge_vocabulary(section_data, section_words, ring_words)
    part7_root_mapping(section_data, ring_parsed)
    part8_synthesis(section_data, section_words, ring_words, ring_families, ring_parsed)

    # Save results
    results = {
        "sections": {},
        "bridge_words": [],
    }
    for section in section_words:
        results["sections"][section] = {
            "total_tokens": sum(section_words[section].values()),
            "unique_words": len(section_words[section]),
            "top_20": dict(section_words[section].most_common(20)),
        }
    for w, rf, hf, sc in bridge_scores[:50]:
        results["bridge_words"].append({
            "word": w, "ring_freq": rf, "herbA_freq": hf, "score": sc
        })

    with open(result_path("herbal_crossref_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\nResults saved to results/herbal_crossref_results.json")
