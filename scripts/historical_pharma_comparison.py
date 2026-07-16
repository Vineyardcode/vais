#!/usr/bin/env python3
"""
HISTORICAL PHARMACEUTICAL COMPARISON
===================================================================
We've established:
  - Two root types: A (substance/poly-suffix) and B (process/mono-y)
  - B-roots appear in sequential runs (procedural sequences)
  - Language A = inventory register (76% substance), Language B = recipe register (38% process)
  - cho-family roots are A-exclusive (ingredient catalog)
  - ched/keed/shed/ked are B-exclusive (process vocabulary)
  - ka enriched AFTER B-runs (result/product word?)

Now: compare these patterns against structural features of ACTUAL 15th-century
pharmaceutical manuscripts to test whether Voynichese functions as a pharmaceutical
notation system.

Tests:
  1. RECIPE GRAMMAR — Do process words (B) precede substance words (A) like "Take X, Mix Y"?
  2. LINE-INITIAL MARKERS — Do lines start with a restricted vocabulary (recipe imperatives)?
  3. INGREDIENT REUSE — Do substance roots recur across folios like a pharmacopoeia?
  4. RECIPE LENGTH & STRUCTURE — Folio-level statistics vs medieval recipe norms
  5. COMPOUND vs SIMPLE — Does suffix complexity correlate with multi-ingredient recipes?
  6. CROSS-REFERENCE PATTERNS — Do folios share ingredient sets like recipe collections?
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import get_root, result_path

# ═══════════════════════════════════════════════════════════════════════════
# PARSER (reused)
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
# DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def load_corpus():
    """Load all folios, parse words, return structured data."""
    folio_dir = Path("folios")
    txt_files = sorted(folio_dir.glob("*.txt"))

    # Build root classifier from full corpus first
    root_suf_global = defaultdict(Counter)
    all_parsed = []  # (word, pfx, root, suf, folio, section, lang, is_label, line_pos, line_len)
    folio_lines = defaultdict(list)  # folio -> [(line_words)]
    folio_meta = {}  # folio -> {section, lang}

    for txt_file in txt_files:
        lines_raw = txt_file.read_text(encoding="utf-8").splitlines()
        folio_name = txt_file.stem
        section = None
        lang = None
        header_lines = []

        for line in lines_raw:
            stripped = line.strip()
            if stripped.startswith("#") or re.match(r"^<f\w+>\s", stripped):
                header_lines.append(stripped)
                continue
            if not stripped or stripped.startswith("<!"):
                continue

        # Determine section and language from headers
        h = "\n".join(header_lines).lower()
        if "herbal" in h: section = "herbal"
        elif "astro" in h or "cosmo" in h or "star" in h or "zodiac" in h: section = "astro"
        elif "pharm" in h or "recipe" in h or "balneo" in h: section = "pharma"
        elif "biolog" in h or "bathy" in h: section = "bio"
        elif "text only" in h: section = "text"
        else: section = "other"

        if "language b" in h: lang = "B"
        elif "language a" in h: lang = "A"
        else: lang = "?"

        folio_meta[folio_name] = {"section": section, "lang": lang}

        for line in lines_raw:
            stripped = line.strip()
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

            line_words = []
            valid_tokens = []
            for tok in tokens:
                tok = tok.strip()
                if not tok or "?" in tok or "'" in tok:
                    continue
                if re.match(r"^[a-z]+$", tok) and len(tok) >= 2:
                    valid_tokens.append(tok)

            for i, tok in enumerate(valid_tokens):
                pfx, onset, body, suf, rem = parse_word(tok)
                if not rem:
                    root = get_root(onset, body)
                    root_suf_global[root][suf or "∅"] += 1
                    entry = {
                        "word": tok, "pfx": pfx or "∅", "root": root,
                        "suf": suf or "∅", "folio": folio_name,
                        "section": section, "lang": lang,
                        "is_label": is_label,
                        "line_pos": i, "line_len": len(valid_tokens),
                    }
                    all_parsed.append(entry)
                    line_words.append(entry)

            if line_words and not is_label:
                folio_lines[folio_name].append(line_words)

    # Classify roots
    root_class = {}
    for root, sufs in root_suf_global.items():
        total = sum(sufs.values())
        if total < 5: continue
        y_frac = sufs.get("y", 0) / total
        if y_frac >= 0.80: root_class[root] = "B"
        elif y_frac <= 0.30: root_class[root] = "A"
        else: root_class[root] = "M"

    return all_parsed, folio_lines, folio_meta, root_class


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def analyze():
    print(f"  Loading corpus...")
    all_parsed, folio_lines, folio_meta, root_class = load_corpus()
    body_text = [e for e in all_parsed if not e["is_label"]]
    print(f"  Total parsed tokens: {len(all_parsed)}")
    print(f"  Body text tokens: {len(body_text)}")
    print(f"  Folios with lines: {len(folio_lines)}")
    print()

    results = {}

    # ═══════════════════════════════════════════════════════════════
    # TEST 1: RECIPE GRAMMAR — B→A transitions
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 1: RECIPE GRAMMAR — Process→Substance ordering")
    print("=" * 90)
    print()
    print("  In pharmaceutical recipes, the pattern is: VERB + NOUN ('Take saffron, mix with...')")
    print("  If Voynichese is recipe notation, B-roots should be followed by A-roots.")
    print()

    # Count all bigram type transitions
    transitions = Counter()  # (type1, type2) -> count
    total_bigrams = 0
    for folio, lines in folio_lines.items():
        for line in lines:
            for i in range(len(line) - 1):
                t1 = root_class.get(line[i]["root"], "?")
                t2 = root_class.get(line[i+1]["root"], "?")
                if t1 in ("A", "B") and t2 in ("A", "B"):
                    transitions[(t1, t2)] += 1
                    total_bigrams += 1

    print(f"  BIGRAM TYPE TRANSITIONS (A=substance, B=process):")
    print(f"  {'':12s}  → Substance  → Process")
    for t1 in ["A", "B"]:
        row = f"  {('Substance' if t1=='A' else 'Process'):12s}"
        for t2 in ["A", "B"]:
            c = transitions.get((t1, t2), 0)
            pct = 100 * c / total_bigrams if total_bigrams else 0
            row += f"  {c:6d} ({pct:4.1f}%)"
        print(row)
    print()

    # Expected under independence
    # compute marginals
    row_a = transitions.get(("A","A"),0) + transitions.get(("A","B"),0)
    row_b = transitions.get(("B","A"),0) + transitions.get(("B","B"),0)
    col_a = transitions.get(("A","A"),0) + transitions.get(("B","A"),0)
    col_b = transitions.get(("A","B"),0) + transitions.get(("B","B"),0)

    # B→A observed vs expected
    ba_obs = transitions.get(("B", "A"), 0)
    ba_exp = row_b * col_a / total_bigrams if total_bigrams else 0
    ba_ratio = ba_obs / ba_exp if ba_exp > 0 else 0

    # B→B observed vs expected
    bb_obs = transitions.get(("B", "B"), 0)
    bb_exp = row_b * col_b / total_bigrams if total_bigrams else 0
    bb_ratio = bb_obs / bb_exp if bb_exp > 0 else 0

    # A→B observed vs expected
    ab_obs = transitions.get(("A", "B"), 0)
    ab_exp = row_a * col_b / total_bigrams if total_bigrams else 0
    ab_ratio = ab_obs / ab_exp if ab_exp > 0 else 0

    print(f"  KEY TRANSITION RATIOS (observed / expected under independence):")
    print(f"    B→A (process then substance): {ba_obs}/{ba_exp:.0f} = {ba_ratio:.3f}×")
    print(f"    B→B (process then process):   {bb_obs}/{bb_exp:.0f} = {bb_ratio:.3f}×")
    print(f"    A→B (substance then process): {ab_obs}/{ab_exp:.0f} = {ab_ratio:.3f}×")
    print()

    if bb_ratio > 1.2 and ba_ratio < 1.0:
        print(f"  → Process words CLUSTER (B→B enriched) but DON'T preferentially precede substances")
        print(f"    NOT classic 'Take X' recipe grammar; more like procedural BLOCKS")
    elif ba_ratio > 1.1:
        print(f"  → B→A enriched: SUPPORTS recipe grammar (process→substance)")
    else:
        print(f"  → No strong directional preference")
    print()

    # What follows B-RUNS specifically?
    print(f"  WHAT FOLLOWS B-RUNS (≥2 consecutive process roots)?")
    after_brun = Counter()
    after_brun_roots = Counter()
    brun_count = 0
    for folio, lines in folio_lines.items():
        for line in lines:
            i = 0
            while i < len(line):
                if root_class.get(line[i]["root"]) == "B":
                    j = i
                    while j < len(line) and root_class.get(line[j]["root"]) == "B":
                        j += 1
                    if j - i >= 2:
                        brun_count += 1
                        if j < len(line):
                            next_type = root_class.get(line[j]["root"], "?")
                            after_brun[next_type] += 1
                            after_brun_roots[line[j]["root"]] += 1
                        else:
                            after_brun["END"] += 1
                    i = j
                else:
                    i += 1

    print(f"  Total B-runs: {brun_count}")
    for typ in ["A", "B", "M", "?", "END"]:
        c = after_brun.get(typ, 0)
        pct = 100 * c / brun_count if brun_count else 0
        label = {"A": "Substance", "B": "Process", "M": "Mixed", "?": "Unknown", "END": "Line-end"}[typ]
        print(f"    → {label:12s}: {c:5d} ({pct:5.1f}%)")
    print()

    print(f"  TOP 10 ROOTS AFTER B-RUNS:")
    for root, cnt in after_brun_roots.most_common(10):
        rt = root_class.get(root, "?")
        print(f"    {root:8s}  {cnt:5d}  type={rt}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 2: LINE-INITIAL MARKERS
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 2: LINE-INITIAL VOCABULARY — Recipe imperatives?")
    print("=" * 90)
    print()
    print("  Medieval recipes start lines with restricted vocabulary:")
    print("  'Recipe' (Take), 'Misce' (Mix), 'Adde' (Add), 'Fiat' (Let it be made)")
    print("  If Voynichese has recipe structure, line-initial words should be:")
    print("  1. A restricted set (low entropy)")
    print("  2. Enriched in process roots or specific function words")
    print()

    line_initial_words = Counter()
    line_initial_roots = Counter()
    line_initial_types = Counter()
    non_initial_roots = Counter()
    non_initial_types = Counter()
    total_lines = 0

    for folio, lines in folio_lines.items():
        for line in lines:
            if len(line) < 2:
                continue
            total_lines += 1
            first = line[0]
            line_initial_words[first["word"]] += 1
            line_initial_roots[first["root"]] += 1
            line_initial_types[root_class.get(first["root"], "?")] += 1

            for entry in line[1:]:
                non_initial_roots[entry["root"]] += 1
                non_initial_types[root_class.get(entry["root"], "?")] += 1

    print(f"  Total lines (≥2 words): {total_lines}")
    print(f"  Unique line-initial words: {len(line_initial_words)}")
    print(f"  Unique line-initial roots: {len(line_initial_roots)}")
    print()

    # Entropy of line-initial roots vs non-initial
    total_init = sum(line_initial_roots.values())
    total_non = sum(non_initial_roots.values())
    h_init = -sum((c/total_init) * math.log2(c/total_init)
                  for c in line_initial_roots.values() if c > 0)
    h_non = -sum((c/total_non) * math.log2(c/total_non)
                 for c in non_initial_roots.values() if c > 0)

    print(f"  Root entropy (line-initial): {h_init:.2f} bits")
    print(f"  Root entropy (non-initial):  {h_non:.2f} bits")
    print(f"  Ratio: {h_init/h_non:.3f}  (< 1.0 means initial is more restricted)")
    print()

    # Top 15 line-initial words
    print(f"  TOP 15 LINE-INITIAL WORDS:")
    print(f"  {'Word':14s}  {'Count':>6s}  {'%':>6s}  {'Root':8s}  {'Type':4s}")
    print(f"  {'─'*14}  {'─'*6}  {'─'*6}  {'─'*8}  {'─'*4}")
    for word, cnt in line_initial_words.most_common(15):
        pct = 100 * cnt / total_lines
        pfx, onset, body, suf, rem = parse_word(word)
        root = get_root(onset, body)
        rt = root_class.get(root, "?")
        print(f"  {word:14s}  {cnt:6d}  {pct:5.1f}%  {root:8s}  {rt:4s}")
    print()

    # Type distribution: initial vs non-initial
    print(f"  ROOT TYPE AT LINE START vs REST:")
    for typ, label in [("A", "Substance"), ("B", "Process"), ("M", "Mixed")]:
        ci = line_initial_types.get(typ, 0)
        pi = 100 * ci / total_init if total_init else 0
        cn = non_initial_types.get(typ, 0)
        pn = 100 * cn / total_non if total_non else 0
        ratio = pi / pn if pn > 0 else 0
        marker = " ← ENRICHED at start" if ratio > 1.3 else (" ← DEPLETED at start" if ratio < 0.7 else "")
        print(f"    {label:12s}  Start: {pi:5.1f}%  Rest: {pn:5.1f}%  Ratio: {ratio:.2f}×{marker}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 3: INGREDIENT REUSE ACROSS FOLIOS
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 3: INGREDIENT REUSE — Cross-folio root sharing")
    print("=" * 90)
    print()
    print("  A pharmacopoeia reuses the same ingredients across many recipes.")
    print("  Each folio = one recipe/entry. How many folios share each root?")
    print()

    root_folios = defaultdict(set)
    folio_roots = defaultdict(set)
    for e in body_text:
        root_folios[e["root"]].add(e["folio"])
        folio_roots[e["folio"]].add(e["root"])

    # Distribution of folio coverage per root
    n_folios = len(folio_lines)
    coverage = []
    for root, folios in root_folios.items():
        if root_class.get(root) in ("A", "B"):
            coverage.append((root, len(folios), root_class.get(root)))

    coverage.sort(key=lambda x: -x[1])

    print(f"  TOP 20 MOST WIDESPREAD ROOTS:")
    print(f"  {'Root':8s}  {'Folios':>7s}  {'Coverage':>9s}  {'Type':4s}")
    print(f"  {'─'*8}  {'─'*7}  {'─'*9}  {'─'*4}")
    for root, nf, rt in coverage[:20]:
        pct = 100 * nf / n_folios
        print(f"  {root:8s}  {nf:7d}  {pct:7.1f}%  {rt}")
    print()

    # Average coverage for substance vs process roots
    a_cov = [nf for _, nf, rt in coverage if rt == "A"]
    b_cov = [nf for _, nf, rt in coverage if rt == "B"]
    a_mean = sum(a_cov) / len(a_cov) if a_cov else 0
    b_mean = sum(b_cov) / len(b_cov) if b_cov else 0

    print(f"  Mean folio coverage:")
    print(f"    Substance roots: {a_mean:.1f} folios ({100*a_mean/n_folios:.1f}%)")
    print(f"    Process roots:   {b_mean:.1f} folios ({100*b_mean/n_folios:.1f}%)")
    print()

    if a_mean > b_mean * 1.3:
        print(f"  → Substance roots are MORE widespread — consistent with shared ingredient pool")
    elif b_mean > a_mean * 1.3:
        print(f"  → Process roots are MORE widespread — procedures are shared, ingredients local")
    else:
        print(f"  → Similar coverage")
    print()

    # Unique roots per folio
    roots_per_folio = [len(roots) for roots in folio_roots.values()]
    mean_rpf = sum(roots_per_folio) / len(roots_per_folio) if roots_per_folio else 0
    print(f"  Unique roots per folio: mean={mean_rpf:.1f}, min={min(roots_per_folio)}, max={max(roots_per_folio)}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 4: RECIPE LENGTH & STRUCTURE
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 4: RECIPE LENGTH — Folio statistics by section")
    print("=" * 90)
    print()
    print("  Medieval recipes are 3-15 lines. Herbal entries are shorter (1-5 lines per plant).")
    print("  If folios = recipes, line count should match these norms.")
    print()

    section_stats = defaultdict(list)
    for folio, lines in folio_lines.items():
        sec = folio_meta.get(folio, {}).get("section", "?")
        lang = folio_meta.get(folio, {}).get("lang", "?")
        n_lines = len(lines)
        n_words = sum(len(line) for line in lines)
        n_substance = sum(1 for line in lines for e in line if root_class.get(e["root"]) == "A")
        n_process = sum(1 for line in lines for e in line if root_class.get(e["root"]) == "B")
        section_stats[sec].append({
            "folio": folio, "lang": lang, "lines": n_lines,
            "words": n_words, "substance": n_substance, "process": n_process
        })

    print(f"  {'Section':10s}  {'Folios':>6s}  {'Avg lines':>10s}  {'Avg words':>10s}  {'Subst %':>8s}  {'Proc %':>7s}")
    print(f"  {'─'*10}  {'─'*6}  {'─'*10}  {'─'*10}  {'─'*8}  {'─'*7}")

    for sec in ["herbal", "pharma", "astro", "bio", "text", "other"]:
        entries = section_stats.get(sec, [])
        if not entries: continue
        n = len(entries)
        avg_lines = sum(e["lines"] for e in entries) / n
        avg_words = sum(e["words"] for e in entries) / n
        total_sub = sum(e["substance"] for e in entries)
        total_proc = sum(e["process"] for e in entries)
        total_w = sum(e["words"] for e in entries)
        sub_pct = 100 * total_sub / total_w if total_w else 0
        proc_pct = 100 * total_proc / total_w if total_w else 0
        print(f"  {sec:10s}  {n:6d}  {avg_lines:10.1f}  {avg_words:10.1f}  {sub_pct:7.1f}%  {proc_pct:6.1f}%")
    print()

    # Compare Language A vs B within sections
    print(f"  BY LANGUAGE WITHIN SECTION:")
    print(f"  {'Section':10s}  {'Lang':4s}  {'Folios':>6s}  {'Avg lines':>10s}  {'Avg words':>10s}  {'Subst %':>8s}  {'Proc %':>7s}")
    print(f"  {'─'*10}  {'─'*4}  {'─'*6}  {'─'*10}  {'─'*10}  {'─'*8}  {'─'*7}")

    for sec in ["herbal", "pharma", "astro", "bio"]:
        for lang in ["A", "B"]:
            entries = [e for e in section_stats.get(sec, []) if e["lang"] == lang]
            if not entries: continue
            n = len(entries)
            avg_lines = sum(e["lines"] for e in entries) / n
            avg_words = sum(e["words"] for e in entries) / n
            total_sub = sum(e["substance"] for e in entries)
            total_proc = sum(e["process"] for e in entries)
            total_w = sum(e["words"] for e in entries)
            sub_pct = 100 * total_sub / total_w if total_w else 0
            proc_pct = 100 * total_proc / total_w if total_w else 0
            print(f"  {sec:10s}  {lang:4s}  {n:6d}  {avg_lines:10.1f}  {avg_words:10.1f}  {sub_pct:7.1f}%  {proc_pct:6.1f}%")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 5: SUFFIX COMPLEXITY → RECIPE COMPLEXITY
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 5: SUFFIX COMPLEXITY — Do compound recipes use more suffix variety?")
    print("=" * 90)
    print()
    print("  In pharmaceutical notation, compounds (multi-ingredient preparations)")
    print("  need more grammatical marking than simples (single herbs).")
    print("  Prediction: folios with MORE unique roots should have MORE suffix types.")
    print()

    # For each folio: count unique roots, unique suffixes, unique prefixes
    folio_complexity = []
    for folio, lines in folio_lines.items():
        all_entries = [e for line in lines for e in line]
        if len(all_entries) < 10: continue
        n_roots = len(set(e["root"] for e in all_entries))
        n_sufs = len(set(e["suf"] for e in all_entries))
        n_pfxs = len(set(e["pfx"] for e in all_entries))
        n_words = len(all_entries)
        sec = folio_meta.get(folio, {}).get("section", "?")
        lang = folio_meta.get(folio, {}).get("lang", "?")
        folio_complexity.append({
            "folio": folio, "section": sec, "lang": lang,
            "n_words": n_words, "n_roots": n_roots,
            "n_suf": n_sufs, "n_pfx": n_pfxs
        })

    # Correlation: n_roots vs n_suffixes
    if len(folio_complexity) > 10:
        xs = [fc["n_roots"] for fc in folio_complexity]
        ys = [fc["n_suf"] for fc in folio_complexity]
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / len(xs)
        std_x = math.sqrt(sum((x - mean_x)**2 for x in xs) / len(xs))
        std_y = math.sqrt(sum((y - mean_y)**2 for y in ys) / len(ys))
        corr = cov / (std_x * std_y) if std_x * std_y > 0 else 0
        print(f"  Pearson r(unique_roots, unique_suffixes) = {corr:.3f}")

        # Also n_roots vs n_prefixes
        ys2 = [fc["n_pfx"] for fc in folio_complexity]
        mean_y2 = sum(ys2) / len(ys2)
        cov2 = sum((x - mean_x) * (y - mean_y2) for x, y in zip(xs, ys2)) / len(xs)
        std_y2 = math.sqrt(sum((y - mean_y2)**2 for y in ys2) / len(ys2))
        corr2 = cov2 / (std_x * std_y2) if std_x * std_y2 > 0 else 0
        print(f"  Pearson r(unique_roots, unique_prefixes) = {corr2:.3f}")
        print()

        if corr > 0.7:
            print(f"  → STRONG correlation: more ingredients → more suffix types")
            print(f"    Consistent with grammatical marking scaling with recipe complexity")
        elif corr > 0.4:
            print(f"  → MODERATE correlation: some relationship between ingredients and grammar")
        else:
            print(f"  → WEAK correlation: suffix variety doesn't scale with ingredient count")
        print()

        # Breakdown by section
        print(f"  COMPLEXITY BY SECTION:")
        print(f"  {'Section':10s}  {'Folios':>6s}  {'Avg roots':>10s}  {'Avg suf':>8s}  {'Avg pfx':>8s}  {'Ratio S/R':>10s}")
        print(f"  {'─'*10}  {'─'*6}  {'─'*10}  {'─'*8}  {'─'*8}  {'─'*10}")
        for sec in ["herbal", "pharma", "astro", "bio", "text"]:
            entries = [fc for fc in folio_complexity if fc["section"] == sec]
            if not entries: continue
            n = len(entries)
            ar = sum(e["n_roots"] for e in entries) / n
            asuf = sum(e["n_suf"] for e in entries) / n
            apfx = sum(e["n_pfx"] for e in entries) / n
            ratio = asuf / ar if ar > 0 else 0
            print(f"  {sec:10s}  {n:6d}  {ar:10.1f}  {asuf:8.1f}  {apfx:8.1f}  {ratio:10.3f}")
        print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 6: CROSS-REFERENCE / INGREDIENT SHARING BETWEEN FOLIOS
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 6: FOLIO SIMILARITY — Ingredient sharing network")
    print("=" * 90)
    print()
    print("  A pharmacopoeia has recipes that share ingredients.")
    print("  Measure Jaccard similarity of root sets between folio pairs.")
    print()

    # Jaccard similarities between all folio pairs (sample for efficiency)
    folio_list = [f for f in folio_roots if len(folio_roots[f]) >= 5]
    n_pairs = 0
    jaccard_sums = defaultdict(lambda: [0, 0])  # (sec1, sec2) -> [sum_jaccard, count]
    all_jaccards = []

    # Deterministic pair window (next 49 folios in sorted order)
    for i in range(len(folio_list)):
        for j in range(i + 1, min(i + 50, len(folio_list))):
            f1, f2 = folio_list[i], folio_list[j]
            r1, r2 = folio_roots[f1], folio_roots[f2]
            inter = len(r1 & r2)
            union = len(r1 | r2)
            jacc = inter / union if union > 0 else 0
            all_jaccards.append(jacc)

            s1 = folio_meta.get(f1, {}).get("section", "?")
            s2 = folio_meta.get(f2, {}).get("section", "?")
            key = tuple(sorted([s1, s2]))
            jaccard_sums[key][0] += jacc
            jaccard_sums[key][1] += 1

    if all_jaccards:
        mean_j = sum(all_jaccards) / len(all_jaccards)
        print(f"  Overall mean Jaccard (root set overlap): {mean_j:.3f}")
        print(f"  Pairs sampled: {len(all_jaccards)}")
        print()

        print(f"  MEAN JACCARD BY SECTION PAIR:")
        print(f"  {'Section pair':25s}  {'Mean Jaccard':>13s}  {'Pairs':>6s}")
        print(f"  {'─'*25}  {'─'*13}  {'─'*6}")
        sorted_pairs = sorted(jaccard_sums.items(), key=lambda x: -x[1][0]/x[1][1] if x[1][1] > 0 else 0)
        for key, (jsum, cnt) in sorted_pairs:
            if cnt >= 5:
                mean = jsum / cnt
                print(f"  {key[0]+' × '+key[1]:25s}  {mean:13.3f}  {cnt:6d}")
        print()

        # Within-section vs between-section
        within = []
        between = []
        for key, (jsum, cnt) in jaccard_sums.items():
            if cnt < 5: continue
            mean = jsum / cnt
            if key[0] == key[1]:
                within.append(mean)
            else:
                between.append(mean)

        if within and between:
            w_mean = sum(within) / len(within)
            b_mean = sum(between) / len(between)
            print(f"  Within-section mean Jaccard:  {w_mean:.3f}")
            print(f"  Between-section mean Jaccard: {b_mean:.3f}")
            print(f"  Ratio: {w_mean/b_mean:.2f}×")
            print()
            if w_mean > b_mean * 1.3:
                print(f"  → Folios in the SAME section share MORE roots — domain-specific vocabulary")
            else:
                print(f"  → Root sharing is similar within and between sections")
            print()

    # ═══════════════════════════════════════════════════════════════
    # SYNTHESIS
    # ═══════════════════════════════════════════════════════════════
    print("═" * 90)
    print("SYNTHESIS — PHARMACEUTICAL COMPARISON")
    print("═" * 90)
    print()

    print(f"  1. RECIPE GRAMMAR:")
    print(f"     B→A ratio: {ba_ratio:.3f}× {'(supports)' if ba_ratio > 1.1 else '(does not support)'} verb→noun ordering")
    print(f"     B→B ratio: {bb_ratio:.3f}× — process words cluster in blocks")
    print()

    print(f"  2. LINE-INITIAL RESTRICTION:")
    print(f"     Entropy ratio: {h_init/h_non:.3f}")
    init_sub = line_initial_types.get("A", 0) / total_init * 100 if total_init else 0
    init_proc = line_initial_types.get("B", 0) / total_init * 100 if total_init else 0
    print(f"     Start: {init_sub:.0f}% substance / {init_proc:.0f}% process")
    print()

    print(f"  3. INGREDIENT REUSE:")
    print(f"     Substance coverage: {a_mean:.1f} folios, Process: {b_mean:.1f} folios")
    print()

    print(f"  4. FOLIO STRUCTURE:")
    for sec in ["herbal", "pharma", "astro", "bio"]:
        entries = section_stats.get(sec, [])
        if entries:
            avg_l = sum(e["lines"] for e in entries) / len(entries)
            avg_w = sum(e["words"] for e in entries) / len(entries)
            print(f"     {sec:10s}: {avg_l:.0f} lines, {avg_w:.0f} words/folio")
    print()

    print(f"  5. COMPLEXITY CORRELATION: r={corr:.3f}" if len(folio_complexity) > 10 else "  5. N/A")
    print()

    if all_jaccards:
        print(f"  6. ROOT SHARING: mean Jaccard={mean_j:.3f}")
    print()

    # Scorecard
    score_for = 0
    score_against = 0

    # 1. Recipe grammar
    if bb_ratio > 1.2:
        score_for += 1  # process clustering (recipe blocks)
    if ba_ratio > 1.1:
        score_for += 1  # verb-noun ordering
    elif ba_ratio < 0.9:
        score_against += 1

    # 2. Line-initial restriction
    if h_init / h_non < 0.92:
        score_for += 1
    else:
        score_against += 1

    # 3. Substance roots widespread
    if a_mean > b_mean * 1.2:
        score_for += 1

    # 4. Complexity correlation
    if len(folio_complexity) > 10 and corr > 0.5:
        score_for += 1
    elif len(folio_complexity) > 10 and corr < 0.3:
        score_against += 1

    # 5. Within-section sharing
    if within and between and w_mean > b_mean * 1.2:
        score_for += 1

    print(f"  PHARMACEUTICAL SCORECARD: {score_for} FOR / {score_against} AGAINST")
    print()
    print("═" * 90)
    print("PHARMACEUTICAL COMPARISON COMPLETE")
    print("═" * 90)

    results["transitions"] = {f"{k[0]}->{k[1]}": v for k, v in transitions.items()}
    results["ba_ratio"] = ba_ratio
    results["bb_ratio"] = bb_ratio
    results["line_initial_entropy_ratio"] = h_init / h_non if h_non > 0 else 0
    results["substance_coverage"] = a_mean
    results["process_coverage"] = b_mean
    results["complexity_corr"] = corr if len(folio_complexity) > 10 else None
    results["mean_jaccard"] = mean_j if all_jaccards else None
    results["score_for"] = score_for
    results["score_against"] = score_against

    return results


if __name__ == "__main__":
    results = analyze()
    with open(result_path("pharma_results.json"), "w") as f:
        json.dump(results, f, indent=2, default=str)
