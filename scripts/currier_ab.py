#!/usr/bin/env python3
"""
VOYNICH MANUSCRIPT — PHASE 3: CURRIER A↔B REGISTER ANALYSIS
=============================================================
Currier's Language A is predominantly herbal + pharma sections.
Currier's Language B is astro + bio + text sections.

Section × Language distribution:
  herbal   A=94  B=30
  pharma   A=9   B=0
  astro    A=3   B=27
  bio      A=0   B=18
  text     A=0   B=2

Is this a register difference (simples vs compounds, herbs vs astrology),
a scribe difference, or actually meaningful for decipherment?

Tests:
  1. ROOT FREQUENCY COMPARISON — Do A and B use different roots?
  2. MORPHEME PROFILE — Different prefix/suffix distributions?
  3. TYPE A vs TYPE B ROOT RATIOS — More substance or process words?
  4. RECIPE PATTERN DIFFERENCES — Different procedural structures?
  5. SHARED ROOTS WITH RANK SHIFT — Same roots at different frequencies?
  6. HERBAL A vs HERBAL B — Control: same section, different language
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


def get_root(onset, body):
    return onset + body


# ═══════════════════════════════════════════════════════════════════════════
# DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def extract_by_language(txt_files):
    """Extract parsed words grouped by Currier language A or B."""
    lang_data = {"A": [], "B": [], "?": []}  # list of (word, pfx, root, suf, folio, section)
    lang_lines = {"A": [], "B": [], "?": []}  # list of (folio, section, [(word, pfx, root, suf)])

    for txt_file in txt_files:
        lines_raw = txt_file.read_text(encoding="utf-8").splitlines()
        header_lines = []
        folio_name = txt_file.stem
        section = None
        lang = None

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
            if is_label:
                continue

            text = re.sub(r"<![^>]*>", "", text)
            text = re.sub(r"<%>|<\$>|<->", " ", text)
            text = re.sub(r"<[^>]*>", "", text)
            text = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", text)
            text = re.sub(r"\{([^}]+)\}", r"\1", text)
            text = re.sub(r"@\d+;?", "", text)
            tokens = re.split(r"[.\s,<>\-]+", text)

            parsed_line = []
            for tok in tokens:
                tok = tok.strip()
                if not tok or "?" in tok or "'" in tok:
                    continue
                if re.match(r"^[a-z]+$", tok) and len(tok) >= 2:
                    pfx, onset, body, suf, rem = parse_word(tok)
                    if not rem:
                        root = get_root(onset, body)
                        parsed_line.append((tok, pfx or "∅", root, suf or "∅"))

                        if section is None:
                            h = "\n".join(header_lines).lower()
                            if "herbal" in h: section = "herbal"
                            elif "astro" in h or "cosmo" in h or "star" in h or "zodiac" in h: section = "astro"
                            elif "pharm" in h or "recipe" in h or "balneo" in h: section = "pharma"
                            elif "biolog" in h or "bathy" in h: section = "bio"
                            elif "text only" in h: section = "text"
                            else: section = "other"
                        if lang is None:
                            h = "\n".join(header_lines).lower()
                            if "language b" in h: lang = "B"
                            elif "language a" in h: lang = "A"
                            else: lang = "?"

                        lang_data[lang].append((tok, pfx or "∅", root, suf or "∅", folio_name, section))

            if parsed_line and lang:
                lang_lines[lang].append((folio_name, section, parsed_line))

    return lang_data, lang_lines


# ═══════════════════════════════════════════════════════════════════════════
# ROOT CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def classify_root_type(all_data):
    """Classify roots as A (substance) or B (process) using combined data."""
    root_suf = defaultdict(Counter)
    for lang in all_data:
        for word, pfx, root, suf, folio, section in all_data[lang]:
            root_suf[root][suf] += 1

    root_class = {}
    for root, sufs in root_suf.items():
        total = sum(sufs.values())
        if total < 5: continue
        y_frac = sufs.get("y", 0) / total
        if y_frac >= 0.80: root_class[root] = "B"
        elif y_frac <= 0.30: root_class[root] = "A"
        else: root_class[root] = "M"
    return root_class


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def jsd(p, q):
    """Jensen-Shannon divergence."""
    all_keys = set(list(p.keys()) + list(q.keys()))
    m = {}
    for k in all_keys:
        m[k] = 0.5 * p.get(k, 0) + 0.5 * q.get(k, 0)
    kl_pm = sum(p.get(k, 0) * math.log2(p[k] / m[k]) for k in all_keys if p.get(k, 0) > 0 and m[k] > 0)
    kl_qm = sum(q.get(k, 0) * math.log2(q[k] / m[k]) for k in all_keys if q.get(k, 0) > 0 and m[k] > 0)
    return math.sqrt(0.5 * kl_pm + 0.5 * kl_qm)


def analyze():
    folio_dir = Path("folios")
    txt_files = sorted(folio_dir.glob("*.txt"))
    print(f"  Loading {len(txt_files)} folios...")

    lang_data, lang_lines = extract_by_language(txt_files)
    root_class = classify_root_type(lang_data)
    results = {}

    total_a = len(lang_data["A"])
    total_b = len(lang_data["B"])
    print(f"  Language A tokens: {total_a}")
    print(f"  Language B tokens: {total_b}")
    print(f"  Language ? tokens: {len(lang_data['?'])}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 1: ROOT FREQUENCY COMPARISON
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 1: ROOT FREQUENCY COMPARISON — A vs B")
    print("=" * 90)
    print()

    root_freq_a = Counter(e[2] for e in lang_data["A"])
    root_freq_b = Counter(e[2] for e in lang_data["B"])

    # Rank in A and B
    rank_a = {r: i + 1 for i, (r, _) in enumerate(root_freq_a.most_common())}
    rank_b = {r: i + 1 for i, (r, _) in enumerate(root_freq_b.most_common())}

    all_roots = set(list(rank_a.keys()) + list(rank_b.keys()))

    print(f"  Roots in A only: {sum(1 for r in all_roots if r in rank_a and r not in rank_b)}")
    print(f"  Roots in B only: {sum(1 for r in all_roots if r in rank_b and r not in rank_a)}")
    print(f"  Roots in both: {sum(1 for r in all_roots if r in rank_a and r in rank_b)}")
    print()

    # Top 20 roots in each language with rank in the other
    print(f"  TOP 20 ROOTS IN LANGUAGE A:")
    print(f"  {'Rank':>4s}  {'Root':8s}  {'A freq':>7s}  {'A %':>6s}  {'B rank':>7s}  {'B freq':>7s}  {'B %':>6s}  {'Type':4s}  {'Shift':8s}")
    print(f"  {'─'*4}  {'─'*8}  {'─'*7}  {'─'*6}  {'─'*7}  {'─'*7}  {'─'*6}  {'─'*4}  {'─'*8}")

    for i, (root, freq) in enumerate(root_freq_a.most_common(20)):
        pct_a = 100 * freq / total_a
        r_b = rank_b.get(root, "—")
        f_b = root_freq_b.get(root, 0)
        pct_b = 100 * f_b / total_b if total_b > 0 else 0
        rt = root_class.get(root, "?")
        shift = ""
        if isinstance(r_b, int) and abs(r_b - (i + 1)) > 5:
            shift = "↑B" if r_b < i + 1 else "↓B"
        print(f"  {i+1:4d}  {root:8s}  {freq:7d}  {pct_a:5.1f}%  {r_b:>7}  {f_b:7d}  {pct_b:5.1f}%  {rt:4s}  {shift}")
    print()

    print(f"  TOP 20 ROOTS IN LANGUAGE B:")
    print(f"  {'Rank':>4s}  {'Root':8s}  {'B freq':>7s}  {'B %':>6s}  {'A rank':>7s}  {'A freq':>7s}  {'A %':>6s}  {'Type':4s}  {'Shift':8s}")
    print(f"  {'─'*4}  {'─'*8}  {'─'*7}  {'─'*6}  {'─'*7}  {'─'*7}  {'─'*6}  {'─'*4}  {'─'*8}")

    for i, (root, freq) in enumerate(root_freq_b.most_common(20)):
        pct_b = 100 * freq / total_b
        r_a = rank_a.get(root, "—")
        f_a = root_freq_a.get(root, 0)
        pct_a = 100 * f_a / total_a if total_a > 0 else 0
        rt = root_class.get(root, "?")
        shift = ""
        if isinstance(r_a, int) and abs(r_a - (i + 1)) > 5:
            shift = "↑A" if r_a < i + 1 else "↓A"
        print(f"  {i+1:4d}  {root:8s}  {freq:7d}  {pct_b:5.1f}%  {r_a:>7}  {f_a:7d}  {pct_a:5.1f}%  {rt:4s}  {shift}")
    print()

    # JSD between root distributions
    dist_a = {r: f / total_a for r, f in root_freq_a.items()}
    dist_b = {r: f / total_b for r, f in root_freq_b.items()}
    root_jsd = jsd(dist_a, dist_b)
    print(f"  Root distribution JSD(A, B) = {root_jsd:.4f}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 2: MORPHEME PROFILE
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 2: MORPHEME PROFILES — Prefix and suffix distributions")
    print("=" * 90)
    print()

    pfx_a = Counter(e[1] for e in lang_data["A"])
    pfx_b = Counter(e[1] for e in lang_data["B"])
    suf_a = Counter(e[3] for e in lang_data["A"])
    suf_b = Counter(e[3] for e in lang_data["B"])

    print(f"  PREFIX COMPARISON:")
    print(f"  {'Prefix':8s}  {'A count':>8s}  {'A %':>6s}  {'B count':>8s}  {'B %':>6s}  {'Ratio B/A':>9s}")
    print(f"  {'─'*8}  {'─'*8}  {'─'*6}  {'─'*8}  {'─'*6}  {'─'*9}")

    all_pfx = sorted(set(list(pfx_a.keys()) + list(pfx_b.keys())),
                     key=lambda x: -(pfx_a.get(x, 0) + pfx_b.get(x, 0)))
    for pfx in all_pfx[:15]:
        ca, cb = pfx_a.get(pfx, 0), pfx_b.get(pfx, 0)
        pa, pb = 100 * ca / total_a, 100 * cb / total_b
        ratio = pb / pa if pa > 0 else float('inf')
        marker = "  ← A-enriched" if ratio < 0.7 else ("  ← B-enriched" if ratio > 1.5 else "")
        print(f"  {pfx:8s}  {ca:8d}  {pa:5.1f}%  {cb:8d}  {pb:5.1f}%  {ratio:8.2f}×{marker}")
    print()

    print(f"  SUFFIX COMPARISON:")
    print(f"  {'Suffix':8s}  {'A count':>8s}  {'A %':>6s}  {'B count':>8s}  {'B %':>6s}  {'Ratio B/A':>9s}")
    print(f"  {'─'*8}  {'─'*8}  {'─'*6}  {'─'*8}  {'─'*6}  {'─'*9}")

    all_suf = sorted(set(list(suf_a.keys()) + list(suf_b.keys())),
                     key=lambda x: -(suf_a.get(x, 0) + suf_b.get(x, 0)))
    for suf in all_suf[:15]:
        ca, cb = suf_a.get(suf, 0), suf_b.get(suf, 0)
        pa, pb = 100 * ca / total_a, 100 * cb / total_b
        ratio = pb / pa if pa > 0 else float('inf')
        marker = "  ← A-enriched" if ratio < 0.7 else ("  ← B-enriched" if ratio > 1.5 else "")
        print(f"  {suf:8s}  {ca:8d}  {pa:5.1f}%  {cb:8d}  {pb:5.1f}%  {ratio:8.2f}×{marker}")
    print()

    # JSD for prefixes and suffixes
    pfx_dist_a = {p: c / total_a for p, c in pfx_a.items()}
    pfx_dist_b = {p: c / total_b for p, c in pfx_b.items()}
    suf_dist_a = {s: c / total_a for s, c in suf_a.items()}
    suf_dist_b = {s: c / total_b for s, c in suf_b.items()}

    pfx_jsd = jsd(pfx_dist_a, pfx_dist_b)
    suf_jsd = jsd(suf_dist_a, suf_dist_b)
    print(f"  Prefix JSD(A, B) = {pfx_jsd:.4f}")
    print(f"  Suffix JSD(A, B) = {suf_jsd:.4f}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 3: TYPE A/B ROOT RATIOS
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 3: SUBSTANCE vs PROCESS ROOT RATIOS by language")
    print("=" * 90)
    print()

    type_counts_a = Counter()
    type_counts_b = Counter()
    for e in lang_data["A"]:
        type_counts_a[root_class.get(e[2], "?")] += 1
    for e in lang_data["B"]:
        type_counts_b[root_class.get(e[2], "?")] += 1

    for rtype, label in [("A", "Substance"), ("B", "Process"), ("M", "Mixed"), ("?", "Unknown")]:
        ca = type_counts_a.get(rtype, 0)
        cb = type_counts_b.get(rtype, 0)
        pa = 100 * ca / total_a if total_a else 0
        pb = 100 * cb / total_b if total_b else 0
        print(f"  {label:12s}  Lang A: {ca:6d} ({pa:5.1f}%)   Lang B: {cb:6d} ({pb:5.1f}%)")

    print()

    a_substance_rate = type_counts_a.get("A", 0) / total_a if total_a else 0
    b_substance_rate = type_counts_b.get("A", 0) / total_b if total_b else 0
    print(f"  Substance ratio: A={100*a_substance_rate:.1f}%, B={100*b_substance_rate:.1f}%")
    if a_substance_rate > b_substance_rate + 0.05:
        print(f"  → Language A is MORE substance-heavy (more ingredient listing)")
    elif b_substance_rate > a_substance_rate + 0.05:
        print(f"  → Language B is MORE substance-heavy")
    else:
        print(f"  → Similar substance/process ratios")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 4: RECIPE PATTERNS
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 4: RECIPE PATTERNS — B-run (process sequence) comparison")
    print("=" * 90)
    print()

    def count_b_runs(lines):
        """Count Type B root runs in lines."""
        run_lengths = Counter()
        total_tokens = 0
        for folio, section, line in lines:
            total_tokens += len(line)
            i = 0
            while i < len(line):
                word, pfx, root, suf = line[i]
                if root_class.get(root) == "B":
                    j = i
                    while j < len(line) and root_class.get(line[j][2]) == "B":
                        j += 1
                    if j - i >= 2:
                        run_lengths[j - i] += 1
                    i = j
                else:
                    i += 1
        return run_lengths, total_tokens

    runs_a, tokens_a = count_b_runs(lang_lines["A"])
    runs_b, tokens_b = count_b_runs(lang_lines["B"])

    total_runs_a = sum(runs_a.values())
    total_runs_b = sum(runs_b.values())
    rate_a = total_runs_a / tokens_a * 1000 if tokens_a else 0
    rate_b = total_runs_b / tokens_b * 1000 if tokens_b else 0

    print(f"  Language A: {total_runs_a} B-runs in {tokens_a} tokens ({rate_a:.1f} per 1000)")
    print(f"  Language B: {total_runs_b} B-runs in {tokens_b} tokens ({rate_b:.1f} per 1000)")
    print()

    print(f"  B-RUN LENGTH DISTRIBUTION:")
    print(f"  {'Length':>6s}  {'Lang A':>8s}  {'Lang B':>8s}")
    print(f"  {'─'*6}  {'─'*8}  {'─'*8}")
    all_lengths = sorted(set(list(runs_a.keys()) + list(runs_b.keys())))
    for length in all_lengths:
        print(f"  {length:6d}  {runs_a.get(length, 0):8d}  {runs_b.get(length, 0):8d}")
    print()

    if rate_b > rate_a * 1.3:
        print(f"  → Language B has MORE process sequences ({rate_b/rate_a:.1f}× more per token)")
    elif rate_a > rate_b * 1.3:
        print(f"  → Language A has MORE process sequences ({rate_a/rate_b:.1f}× more per token)")
    else:
        print(f"  → Similar process sequence rates")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 5: RANK SHIFT ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 5: RANK SHIFT — Same roots at different positions")
    print("=" * 90)
    print()
    print("  Roots that dramatically shift rank between A and B may represent")
    print("  domain-specific terms (e.g., an astrology-specific ingredient)")
    print()

    shifts = []
    for root in all_roots:
        if root in rank_a and root in rank_b:
            ra, rb = rank_a[root], rank_b[root]
            fa = root_freq_a[root] / total_a
            fb = root_freq_b[root] / total_b
            if root_freq_a[root] >= 10 and root_freq_b[root] >= 10:
                log_ratio = math.log2(fb / fa) if fa > 0 and fb > 0 else 0
                shifts.append((root, ra, rb, root_freq_a[root], root_freq_b[root], log_ratio))

    shifts.sort(key=lambda x: -x[5])

    print(f"  TOP 10 B-ENRICHED ROOTS (higher rank in B than A):")
    print(f"  {'Root':8s}  {'A rank':>7s}  {'B rank':>7s}  {'A freq':>7s}  {'B freq':>7s}  {'log2(B/A)':>10s}  {'Type':4s}")
    print(f"  {'─'*8}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*10}  {'─'*4}")
    for root, ra, rb, fa, fb, lr in shifts[:10]:
        rt = root_class.get(root, "?")
        print(f"  {root:8s}  {ra:7d}  {rb:7d}  {fa:7d}  {fb:7d}  {lr:+9.2f}  {rt:4s}")
    print()

    shifts.sort(key=lambda x: x[5])
    print(f"  TOP 10 A-ENRICHED ROOTS (higher rank in A than B):")
    print(f"  {'Root':8s}  {'A rank':>7s}  {'B rank':>7s}  {'A freq':>7s}  {'B freq':>7s}  {'log2(B/A)':>10s}  {'Type':4s}")
    print(f"  {'─'*8}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*10}  {'─'*4}")
    for root, ra, rb, fa, fb, lr in shifts[:10]:
        rt = root_class.get(root, "?")
        print(f"  {root:8s}  {ra:7d}  {rb:7d}  {fa:7d}  {fb:7d}  {lr:+9.2f}  {rt:4s}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 6: HERBAL A vs HERBAL B — Same section control
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 6: HERBAL-A vs HERBAL-B — Same section, different language")
    print("=" * 90)
    print()
    print("  The herbal section has both A and B folios. If the language difference")
    print("  is just scribal, the morpheme profiles should be similar.")
    print("  If it's a register difference, they should diverge even within herbal.")
    print()

    herbal_a = [e for e in lang_data["A"] if e[5] == "herbal"]
    herbal_b = [e for e in lang_data["B"] if e[5] == "herbal"]
    ha_total = len(herbal_a)
    hb_total = len(herbal_b)

    print(f"  Herbal-A tokens: {ha_total}")
    print(f"  Herbal-B tokens: {hb_total}")
    print()

    if ha_total > 100 and hb_total > 100:
        # Root distribution comparison
        ha_roots = Counter(e[2] for e in herbal_a)
        hb_roots = Counter(e[2] for e in herbal_b)
        ha_dist = {r: c / ha_total for r, c in ha_roots.items()}
        hb_dist = {r: c / hb_total for r, c in hb_roots.items()}
        herbal_root_jsd = jsd(ha_dist, hb_dist)

        # Suffix comparison
        ha_suf = Counter(e[3] for e in herbal_a)
        hb_suf = Counter(e[3] for e in herbal_b)
        ha_suf_dist = {s: c / ha_total for s, c in ha_suf.items()}
        hb_suf_dist = {s: c / hb_total for s, c in hb_suf.items()}
        herbal_suf_jsd = jsd(ha_suf_dist, hb_suf_dist)

        # Prefix comparison
        ha_pfx = Counter(e[1] for e in herbal_a)
        hb_pfx = Counter(e[1] for e in herbal_b)
        ha_pfx_dist = {p: c / ha_total for p, c in ha_pfx.items()}
        hb_pfx_dist = {p: c / hb_total for p, c in hb_pfx.items()}
        herbal_pfx_jsd = jsd(ha_pfx_dist, hb_pfx_dist)

        print(f"  Within-herbal JSD:")
        print(f"    Root JSD:   {herbal_root_jsd:.4f}  (overall A↔B: {root_jsd:.4f})")
        print(f"    Suffix JSD: {herbal_suf_jsd:.4f}  (overall A↔B: {suf_jsd:.4f})")
        print(f"    Prefix JSD: {herbal_pfx_jsd:.4f}  (overall A↔B: {pfx_jsd:.4f})")
        print()

        if herbal_root_jsd < root_jsd * 0.7:
            print(f"  ✓ WITHIN-HERBAL DIVERGENCE IS SMALLER than overall")
            print(f"    → Much of A↔B difference is due to SECTION, not language")
        elif herbal_root_jsd > root_jsd * 0.9:
            print(f"  ✗ WITHIN-HERBAL DIVERGENCE IS SIMILAR to overall")
            print(f"    → A↔B difference is real WITHIN sections — true register split")
        else:
            print(f"  ~ PARTIAL: within-herbal is moderately smaller than overall")
        print()

        # Top divergent roots within herbal
        print(f"  TOP HERBAL ROOTS THAT DIFFER BETWEEN A and B:")
        print(f"  {'Root':8s}  {'Herb-A':>8s}  {'A %':>6s}  {'Herb-B':>8s}  {'B %':>6s}  {'log2(B/A)':>10s}")
        print(f"  {'─'*8}  {'─'*8}  {'─'*6}  {'─'*8}  {'─'*6}  {'─'*10}")
        h_shifts = []
        for root in set(list(ha_roots.keys()) + list(hb_roots.keys())):
            fa = ha_roots.get(root, 0)
            fb = hb_roots.get(root, 0)
            if fa >= 5 and fb >= 5:
                pa = fa / ha_total
                pb = fb / hb_total
                lr = math.log2(pb / pa)
                h_shifts.append((root, fa, fb, pa, pb, lr))

        h_shifts.sort(key=lambda x: -abs(x[5]))
        for root, fa, fb, pa, pb, lr in h_shifts[:15]:
            direction = "B-heavy" if lr > 0 else "A-heavy"
            print(f"  {root:8s}  {fa:8d}  {100*pa:5.1f}%  {fb:8d}  {100*pb:5.1f}%  {lr:+9.2f}  {direction}")
        print()

    # ═══════════════════════════════════════════════════════════════
    # SYNTHESIS
    # ═══════════════════════════════════════════════════════════════
    print("═" * 90)
    print("SYNTHESIS — CURRIER A↔B REGISTER ANALYSIS")
    print("═" * 90)
    print()

    print(f"  1. ROOT JSD(A,B) = {root_jsd:.4f}")
    print(f"     Prefix JSD = {pfx_jsd:.4f}, Suffix JSD = {suf_jsd:.4f}")
    print()

    # Substance/process ratio summary
    a_sub = type_counts_a.get("A", 0) / total_a * 100
    b_sub = type_counts_b.get("A", 0) / total_b * 100
    a_proc = type_counts_a.get("B", 0) / total_a * 100
    b_proc = type_counts_b.get("B", 0) / total_b * 100
    print(f"  2. SUBSTANCE/PROCESS: A={a_sub:.0f}%/{a_proc:.0f}%, B={b_sub:.0f}%/{b_proc:.0f}%")

    print(f"  3. B-RUNS: A={rate_a:.1f}/1000tok, B={rate_b:.1f}/1000tok")
    print()

    # Populate results (was previously left empty -> JSON output was always {})
    results["tokens"] = {"A": total_a, "B": total_b, "?": len(lang_data["?"])}
    results["root_jsd"] = root_jsd
    results["prefix_jsd"] = pfx_jsd
    results["suffix_jsd"] = suf_jsd
    results["type_counts_A"] = dict(type_counts_a)
    results["type_counts_B"] = dict(type_counts_b)
    results["b_runs_per_1000"] = {"A": rate_a, "B": rate_b}
    if ha_total > 100 and hb_total > 100:
        results["herbal_within_jsd"] = {
            "root": herbal_root_jsd, "suffix": herbal_suf_jsd,
            "prefix": herbal_pfx_jsd,
        }

    print("  Results saved to currier_ab_results.json")
    print()
    print("═" * 90)
    print("CURRIER A↔B ANALYSIS COMPLETE")
    print("═" * 90)

    return results


if __name__ == "__main__":
    results = analyze()
    with open("currier_ab_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
