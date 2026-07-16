#!/usr/bin/env python3
"""
ROOT-TYPE GRAMMAR — the substance/process root split
========================================
Dig deeper into the Type A (substance) / Type B (process) root split.

Tests:
  1. TYPE A/B VALIDATION — Is the split bimodal or a continuum?
  2. LINE-LEVEL GRAMMAR — Do A and B roots alternate in lines? (noun-verb-noun)
  3. THE q- PREFIX ANOMALY — Why does q- overwhelmingly select suffix -l?
  4. SUFFIX PARADIGM STRUCTURE — Are -iin, -r, -l, -in, -m truly "cases"?
  5. LINE-POSITION EFFECTS — Does -y appear more in certain positions?
  6. PROCESS-ROOT SEQUENCES — What happens around ched/kee/keed clusters?
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from common import get_root, result_path, classify_folio_header_section as classify_folio

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




# ═══════════════════════════════════════════════════════════════════════════
# DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════



def extract_parsed_lines(txt_files):
    """Extract all text as parsed lines: each line = list of (word, pfx, root, suf)."""
    all_lines = []  # (folio, section, [(word, pfx, root, suf), ...])

    for txt_file in txt_files:
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

            if parsed_line:
                if section is None:
                    section = classify_folio(header_lines)
                all_lines.append((folio_name, section, parsed_line))

    return all_lines


# ═══════════════════════════════════════════════════════════════════════════
# CLASSIFY ROOTS AS TYPE A OR TYPE B
# ═══════════════════════════════════════════════════════════════════════════

def classify_roots(all_lines):
    """Compute y-dominance for each root and classify A vs B."""
    root_suf = defaultdict(Counter)
    for folio, section, line in all_lines:
        for word, pfx, root, suf in line:
            root_suf[root][suf] += 1

    root_class = {}
    root_ydominance = {}
    for root, sufs in root_suf.items():
        total = sum(sufs.values())
        if total < 5:
            continue
        y_frac = sufs.get("y", 0) / total
        root_ydominance[root] = y_frac
        if y_frac >= 0.80:
            root_class[root] = "B"
        elif y_frac <= 0.30:
            root_class[root] = "A"
        else:
            root_class[root] = "M"  # mixed

    return root_class, root_ydominance, root_suf


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def analyze(all_lines):
    results = {}

    root_class, root_ydominance, root_suf = classify_roots(all_lines)

    # Count totals
    total_tokens = sum(len(line) for _, _, line in all_lines)
    type_a = {r for r, c in root_class.items() if c == "A"}
    type_b = {r for r, c in root_class.items() if c == "B"}
    type_m = {r for r, c in root_class.items() if c == "M"}
    freq_a = sum(sum(root_suf[r].values()) for r in type_a)
    freq_b = sum(sum(root_suf[r].values()) for r in type_b)
    freq_m = sum(sum(root_suf[r].values()) for r in type_m)

    # ═══════════════════════════════════════════════════════════════
    # TEST 1: IS THE A/B SPLIT BIMODAL OR A CONTINUUM?
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 1: TYPE A/B SPLIT — Bimodal or continuum?")
    print("=" * 90)
    print()
    print(f"  Total classified roots: {len(root_class)}")
    print(f"  Type A (substance, y<30%):  {len(type_a):3d} roots, {freq_a:6d} tokens ({100*freq_a/total_tokens:.1f}%)")
    print(f"  Type M (mixed, 30-80%):     {len(type_m):3d} roots, {freq_m:6d} tokens ({100*freq_m/total_tokens:.1f}%)")
    print(f"  Type B (process, y≥80%):    {len(type_b):3d} roots, {freq_b:6d} tokens ({100*freq_b/total_tokens:.1f}%)")
    print()

    # Histogram of y-dominance
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    bin_labels = ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%",
                  "50-60%", "60-70%", "70-80%", "80-90%", "90-100%"]
    bin_counts = [0] * 10
    bin_tokens = [0] * 10
    for root, yd in root_ydominance.items():
        for i in range(10):
            if bins[i] <= yd < bins[i + 1]:
                bin_counts[i] += 1
                bin_tokens[i] += sum(root_suf[root].values())
                break

    print(f"  Y-DOMINANCE DISTRIBUTION (suffix -y as fraction of all suffixes):")
    print(f"  {'Range':10s}  {'Roots':>6s}  {'Tokens':>7s}  Bar")
    print(f"  {'─' * 10}  {'─' * 6}  {'─' * 7}  {'─' * 40}")
    for i in range(10):
        bar = "█" * (bin_counts[i] * 2)
        print(f"  {bin_labels[i]:10s}  {bin_counts[i]:6d}  {bin_tokens[i]:7d}  {bar}")
    print()

    # Gap test: is there a desert in the middle?
    low_zone = sum(bin_counts[:3])   # 0-30%
    mid_zone = sum(bin_counts[3:8])  # 30-80%
    high_zone = sum(bin_counts[8:])  # 80-100%
    print(f"  Zone counts: A-zone(0-30%)={low_zone}, M-zone(30-80%)={mid_zone}, B-zone(80-100%)={high_zone}")
    if mid_zone < (low_zone + high_zone) * 0.3:
        print(f"  ✓ BIMODAL: Clear gap between A and B types")
        print(f"    → The split is NOT arbitrary — roots really ARE two distinct classes")
    else:
        print(f"  ~ CONTINUUM: Some roots fall in the middle zone")
        print(f"    → The A/B boundary is somewhat arbitrary")
    print()

    # List the Mixed (M) roots — these are the most interesting
    mixed_roots = [(r, root_ydominance[r], sum(root_suf[r].values())) for r in type_m]
    mixed_roots.sort(key=lambda x: -x[2])
    print(f"  MIXED-TYPE ROOTS (30-80% suffix -y, freq≥5):")
    print(f"  {'Root':12s}  {'y%':>6s}  {'Freq':>6s}  Suffix profile")
    print(f"  {'─' * 12}  {'─' * 6}  {'─' * 6}  {'─' * 40}")
    for root, yd, freq in mixed_roots[:20]:
        top_suf = root_suf[root].most_common(4)
        suf_str = ", ".join(f"{s}:{c}" for s, c in top_suf)
        print(f"  {root:12s}  {100*yd:5.1f}%  {freq:6d}  {suf_str}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 2: LINE-LEVEL GRAMMAR — A/B alternation patterns
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 2: LINE-LEVEL GRAMMAR — Do A and B roots alternate?")
    print("=" * 90)
    print()
    print("  If Type B = verbs, we'd expect patterns like:")
    print("  ...A B A B... (noun-verb-noun-verb) or ...A A B A A B...")
    print("  If random, the type sequence should match null expectation")
    print()

    # Encode each line as an A/B/M sequence
    type_sequences = []
    bigram_counts = Counter()
    trigram_counts = Counter()
    for folio, section, line in all_lines:
        seq = []
        for word, pfx, root, suf in line:
            cls = root_class.get(root, "?")
            if cls in ("A", "B", "M"):
                seq.append(cls)
        if len(seq) >= 2:
            type_sequences.append(seq)
            for i in range(len(seq) - 1):
                bigram_counts[(seq[i], seq[i + 1])] += 1
            for i in range(len(seq) - 2):
                trigram_counts[(seq[i], seq[i + 1], seq[i + 2])] += 1

    # Compute observed vs expected bigram rates
    total_bigrams = sum(bigram_counts.values())
    type_freq_in_seq = Counter()
    for seq in type_sequences:
        for t in seq:
            type_freq_in_seq[t] += 1
    total_type_tokens = sum(type_freq_in_seq.values())

    print(f"  Type frequencies in sequences: A={type_freq_in_seq['A']} ({100*type_freq_in_seq['A']/total_type_tokens:.1f}%), "
          f"B={type_freq_in_seq['B']} ({100*type_freq_in_seq['B']/total_type_tokens:.1f}%), "
          f"M={type_freq_in_seq['M']} ({100*type_freq_in_seq['M']/total_type_tokens:.1f}%)")
    print()

    print(f"  BIGRAM TRANSITION MATRIX (observed / expected / ratio):")
    print(f"  {'':4s}  {'→ A':>14s}  {'→ B':>14s}  {'→ M':>14s}")
    print(f"  {'─' * 4}  {'─' * 14}  {'─' * 14}  {'─' * 14}")

    p = {}
    for t in "ABM":
        p[t] = type_freq_in_seq[t] / total_type_tokens

    for t1 in "ABM":
        print(f"  {t1:4s}", end="")
        for t2 in "ABM":
            obs = bigram_counts.get((t1, t2), 0)
            exp = p[t1] * p[t2] * total_bigrams
            ratio = obs / exp if exp > 0 else 0
            print(f"  {obs:5d}/{exp:5.0f} {ratio:.2f}×", end="")
        print()
    print()

    # Key question: does B→A happen more than expected? (verb→noun transition)
    ba_obs = bigram_counts.get(("B", "A"), 0)
    ba_exp = p["B"] * p["A"] * total_bigrams
    ab_obs = bigram_counts.get(("A", "B"), 0)
    ab_exp = p["A"] * p["B"] * total_bigrams
    bb_obs = bigram_counts.get(("B", "B"), 0)
    bb_exp = p["B"] * p["B"] * total_bigrams
    aa_obs = bigram_counts.get(("A", "A"), 0)
    aa_exp = p["A"] * p["A"] * total_bigrams

    print(f"  KEY TRANSITIONS:")
    print(f"    A→A: {aa_obs:5d} obs / {aa_exp:5.0f} exp = {aa_obs/aa_exp:.3f}×  {'(A clusters with A)' if aa_obs/aa_exp > 1.05 else ''}")
    print(f"    A→B: {ab_obs:5d} obs / {ab_exp:5.0f} exp = {ab_obs/ab_exp:.3f}×")
    print(f"    B→A: {ba_obs:5d} obs / {ba_exp:5.0f} exp = {ba_obs/ba_exp:.3f}×")
    print(f"    B→B: {bb_obs:5d} obs / {bb_exp:5.0f} exp = {bb_obs/bb_exp:.3f}×  {'(B clusters with B)' if bb_obs/bb_exp > 1.05 else ''}")
    print()

    if bb_obs / bb_exp > 1.2:
        print(f"  ✗ B→B CLUSTERING: Process-roots cluster together ({bb_obs/bb_exp:.2f}×)")
        print(f"    → NOT noun-verb alternation. Processes appear in RUNS.")
    elif aa_obs / aa_exp > 1.1 and bb_obs / bb_exp > 1.1:
        print(f"  ~ WEAK CLUSTERING: both types cluster slightly")
    elif ab_obs / ab_exp > 1.0 and ba_obs / ba_exp > 1.0:
        print(f"  ✓ ALTERNATION: A↔B transitions are enriched")
        print(f"    → Consistent with noun-verb-noun grammar")
    print()

    # Top trigrams
    print(f"  TOP 15 TYPE TRIGRAMS:")
    print(f"  {'Pattern':10s}  {'Count':>6s}  {'Expected':>8s}  {'Ratio':>6s}")
    print(f"  {'─' * 10}  {'─' * 6}  {'─' * 8}  {'─' * 6}")
    total_trigrams = sum(trigram_counts.values())
    trig_ranked = []
    for (t1, t2, t3), count in trigram_counts.items():
        exp = p[t1] * p[t2] * p[t3] * total_trigrams
        ratio = count / exp if exp > 0 else 0
        trig_ranked.append((f"{t1}-{t2}-{t3}", count, exp, ratio))
    trig_ranked.sort(key=lambda x: -x[1])
    for pat, count, exp, ratio in trig_ranked[:15]:
        marker = "  ← " + ("clustered" if ratio > 1.15 else "depleted" if ratio < 0.85 else "")
        print(f"  {pat:10s}  {count:6d}  {exp:8.0f}  {ratio:5.2f}×{marker}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 3: THE q- PREFIX ANOMALY
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 3: THE q- PREFIX ANOMALY")
    print("=" * 90)
    print()
    print("  Prefix q- (bare, without o-) selects suffix -l at 49%.")
    print("  No other prefix does this. What's going on?")
    print()

    # Collect all q- words
    q_words = []
    qo_words = []
    bare_words = []
    for folio, section, line in all_lines:
        for word, pfx, root, suf in line:
            if pfx == "q":
                q_words.append((word, root, suf, section))
            elif pfx == "qo":
                qo_words.append((word, root, suf, section))
            elif pfx == "∅":
                bare_words.append((word, root, suf, section))

    print(f"  q- words: {len(q_words)}")
    print(f"  qo- words: {len(qo_words)}")
    print()

    # q- suffix distribution
    q_suf = Counter(w[2] for w in q_words)
    qo_suf = Counter(w[2] for w in qo_words)
    bare_suf = Counter(w[2] for w in bare_words)

    print(f"  SUFFIX DISTRIBUTION COMPARISON:")
    all_sufs = sorted(set(list(q_suf.keys()) + list(qo_suf.keys()) + list(bare_suf.keys())),
                      key=lambda s: -(q_suf.get(s, 0) + qo_suf.get(s, 0)))
    print(f"  {'Suffix':8s}  {'q-':>10s}  {'qo-':>10s}  {'∅':>10s}")
    print(f"  {'─' * 8}  {'─' * 10}  {'─' * 10}  {'─' * 10}")
    for suf in all_sufs[:12]:
        q_pct = 100 * q_suf.get(suf, 0) / len(q_words) if q_words else 0
        qo_pct = 100 * qo_suf.get(suf, 0) / len(qo_words) if qo_words else 0
        bare_pct = 100 * bare_suf.get(suf, 0) / len(bare_words) if bare_words else 0
        print(f"  {suf:8s}  {q_pct:8.1f}%  {qo_pct:8.1f}%  {bare_pct:8.1f}%")
    print()

    # q- root distribution — which roots does q- attach to?
    q_root = Counter(w[1] for w in q_words)
    qo_root = Counter(w[1] for w in qo_words)
    print(f"  q- TOP ROOTS:  {', '.join(f'{r}:{c}' for r, c in q_root.most_common(10))}")
    print(f"  qo- TOP ROOTS: {', '.join(f'{r}:{c}' for r, c in qo_root.most_common(10))}")
    print()

    # q- root TYPE distribution
    q_type_a = sum(c for r, c in q_root.items() if r in type_a)
    q_type_b = sum(c for r, c in q_root.items() if r in type_b)
    qo_type_a = sum(c for r, c in qo_root.items() if r in type_a)
    qo_type_b = sum(c for r, c in qo_root.items() if r in type_b)
    print(f"  q-  attaches to: Type A = {q_type_a} ({100*q_type_a/len(q_words):.1f}%), "
          f"Type B = {q_type_b} ({100*q_type_b/len(q_words):.1f}%)")
    print(f"  qo- attaches to: Type A = {qo_type_a} ({100*qo_type_a/len(qo_words):.1f}%), "
          f"Type B = {qo_type_b} ({100*qo_type_b/len(qo_words):.1f}%)")
    print()

    # q- section distribution
    q_sec = Counter(w[3] for w in q_words)
    qo_sec = Counter(w[3] for w in qo_words)
    print(f"  q-  sections: {', '.join(f'{s}:{c}' for s, c in q_sec.most_common())}")
    print(f"  qo- sections: {', '.join(f'{s}:{c}' for s, c in qo_sec.most_common())}")
    print()

    # What are the actual q- words?
    q_word_freq = Counter(w[0] for w in q_words)
    print(f"  TOP 15 ACTUAL q- WORDS:")
    for word, count in q_word_freq.most_common(15):
        root = [w[1] for w in q_words if w[0] == word][0]
        suf = [w[2] for w in q_words if w[0] == word][0]
        print(f"    {word:15s}  ×{count:3d}  root={root}, suf={suf}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 4: SUFFIX PARADIGM — Are -iin, -r, -l, -in, -m "cases"?
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 4: SUFFIX PARADIGM — Testing the 'case system' hypothesis")
    print("=" * 90)
    print()
    print("  If suffixes are cases/forms of the same substance, then:")
    print("  (a) Each Type A root should have a CONSISTENT case paradigm")
    print("  (b) The ratios between cases should be similar across roots")
    print("  (c) Line context should predict which case appears")
    print()

    # For each Type A root (freq≥50), compute suffix ratios
    top_a_roots = [(r, sum(root_suf[r].values())) for r in type_a
                   if sum(root_suf[r].values()) >= 50]
    top_a_roots.sort(key=lambda x: -x[1])

    case_suffixes = ["iin", "r", "l", "in", "m", "∅", "dy", "ly"]

    print(f"  CASE PARADIGM for top Type A roots (% of each suffix):")
    print(f"  {'Root':8s}  {'Freq':>5s}", end="")
    for cs in case_suffixes:
        print(f"  {cs:>6s}", end="")
    print(f"  {'Entropy':>8s}")
    print(f"  {'─' * 8}  {'─' * 5}", end="")
    for _ in case_suffixes:
        print(f"  {'─' * 6}", end="")
    print(f"  {'─' * 8}")

    paradigm_vectors = {}
    for root, freq in top_a_roots[:20]:
        sufs = root_suf[root]
        total = sum(sufs.values())
        vec = []
        print(f"  {root:8s}  {freq:5d}", end="")
        for cs in case_suffixes:
            pct = 100 * sufs.get(cs, 0) / total
            vec.append(sufs.get(cs, 0) / total)
            print(f"  {pct:5.1f}%", end="")
        # Entropy
        H = sum(-v * math.log2(v) for v in vec if v > 0)
        print(f"  {H:7.2f}b")
        paradigm_vectors[root] = vec

    print()

    # Compute pairwise correlation between paradigm vectors
    print(f"  PARADIGM SIMILARITY (cosine similarity between suffix profiles):")
    print(f"  Top A roots cluster into sub-groups by suffix shape?")
    print()

    # Group by dominant suffix
    groups = defaultdict(list)
    for root, freq in top_a_roots[:20]:
        sufs = root_suf[root]
        dom = sufs.most_common(1)[0][0]
        groups[dom].append(root)

    for dom_suf, members in sorted(groups.items(), key=lambda x: -len(x[1])):
        if len(members) >= 2:
            # avg cosine sim within group
            sims = []
            for r1, r2 in combinations(members, 2):
                if r1 in paradigm_vectors and r2 in paradigm_vectors:
                    v1, v2 = paradigm_vectors[r1], paradigm_vectors[r2]
                    dot = sum(a * b for a, b in zip(v1, v2))
                    n1 = math.sqrt(sum(a ** 2 for a in v1))
                    n2 = math.sqrt(sum(b ** 2 for b in v2))
                    sims.append(dot / (n1 * n2) if n1 * n2 > 0 else 0)
            avg_sim = sum(sims) / len(sims) if sims else 0
            print(f"  Group '{dom_suf}'-dominant: {members}  avg cosine={avg_sim:.3f}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 5: LINE-POSITION OF SUFFIX -y
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 5: LINE-POSITION EFFECTS — Where does suffix -y appear?")
    print("=" * 90)
    print()
    print("  If -y marks verbs, they should have preferred positions in the line")
    print("  (e.g., verb-second in Germanic, verb-final in Latin/Japanese)")
    print()

    # Normalize position in line to [0, 1]
    y_positions = []
    non_y_positions = []
    pos_suf_counts = defaultdict(Counter)  # normalized_pos_bin -> suffix counts

    for folio, section, line in all_lines:
        n = len(line)
        if n < 3:
            continue
        for i, (word, pfx, root, suf) in enumerate(line):
            norm_pos = i / (n - 1)  # 0 = first, 1 = last
            pos_bin = int(norm_pos * 10)
            pos_bin = min(pos_bin, 9)
            pos_suf_counts[pos_bin][suf] += 1
            if suf == "y":
                y_positions.append(norm_pos)
            else:
                non_y_positions.append(norm_pos)

    # Compare distributions
    y_mean = sum(y_positions) / len(y_positions) if y_positions else 0
    ny_mean = sum(non_y_positions) / len(non_y_positions) if non_y_positions else 0
    print(f"  Mean normalized position:")
    print(f"    suffix -y:     {y_mean:.4f}  (0=line-start, 1=line-end)")
    print(f"    other suffix:  {ny_mean:.4f}")
    print()

    # Position histogram
    print(f"  SUFFIX -y RATE BY LINE POSITION:")
    print(f"  {'Position':10s}  {'-y count':>9s}  {'total':>7s}  {'-y rate':>8s}  Bar")
    print(f"  {'─' * 10}  {'─' * 9}  {'─' * 7}  {'─' * 8}  {'─' * 30}")
    for b in range(10):
        total = sum(pos_suf_counts[b].values())
        y_ct = pos_suf_counts[b].get("y", 0)
        rate = y_ct / total if total > 0 else 0
        label = f"{b * 10}-{(b + 1) * 10}%"
        bar = "█" * int(rate * 60)
        print(f"  {label:10s}  {y_ct:9d}  {total:7d}  {100*rate:6.1f}%  {bar}")
    print()

    # Also check: first word and last word suffix distributions
    first_suf = Counter()
    last_suf = Counter()
    for folio, section, line in all_lines:
        if len(line) >= 2:
            first_suf[line[0][3]] += 1
            last_suf[line[-1][3]] += 1

    print(f"  FIRST-WORD suffix distribution (top 5):")
    for suf, cnt in first_suf.most_common(5):
        print(f"    {suf:8s}  {cnt:5d}  ({100*cnt/sum(first_suf.values()):.1f}%)")
    print()
    print(f"  LAST-WORD suffix distribution (top 5):")
    for suf, cnt in last_suf.most_common(5):
        print(f"    {suf:8s}  {cnt:5d}  ({100*cnt/sum(last_suf.values()):.1f}%)")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 6: PROCESS-ROOT SEQUENCES — What's around B-clusters?
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 6: PROCESS-ROOT SEQUENCES — Context around Type B clusters")
    print("=" * 90)
    print()
    print("  Type B roots co-occur in runs (Test 2 showed B→B clustering).")
    print("  What Type A roots appear BEFORE and AFTER these runs?")
    print("  (= what substances are being processed?)")
    print()

    # Find B-runs of length ≥ 2 and record flanking A roots
    b_run_before = Counter()  # root that appears right before a B-run
    b_run_after = Counter()   # root that appears right after a B-run
    b_run_lengths = Counter()
    b_run_examples = []

    for folio, section, line in all_lines:
        # Build type sequence
        seq = [(word, pfx, root, suf, root_class.get(root, "?")) for word, pfx, root, suf in line]
        # Find B-runs
        i = 0
        while i < len(seq):
            if seq[i][4] == "B":
                j = i
                while j < len(seq) and seq[j][4] == "B":
                    j += 1
                run_len = j - i
                if run_len >= 2:
                    b_run_lengths[run_len] += 1
                    # What's before?
                    if i > 0 and seq[i - 1][4] == "A":
                        b_run_before[seq[i - 1][2]] += 1
                    # What's after?
                    if j < len(seq) and seq[j][4] == "A":
                        b_run_after[seq[j][2]] += 1
                    # Record example
                    if len(b_run_examples) < 30:
                        start = max(0, i - 2)
                        end = min(len(seq), j + 2)
                        example = []
                        for k in range(start, end):
                            w, pf, rt, sf, cl = seq[k]
                            marker = "**" if cl == "B" else "  "
                            example.append(f"{marker}{w}({pf}+{rt}+{sf})[{cl}]{marker}")
                        b_run_examples.append((folio, " | ".join(example)))
                i = j
            else:
                i += 1

    print(f"  B-RUN LENGTH DISTRIBUTION:")
    for length, count in sorted(b_run_lengths.items()):
        print(f"    length {length}: {count} runs")
    print()

    print(f"  TYPE A ROOT BEFORE B-RUNS (top 10):")
    for root, count in b_run_before.most_common(10):
        print(f"    {root:12s}  ×{count}")
    print()

    print(f"  TYPE A ROOT AFTER B-RUNS (top 10):")
    for root, count in b_run_after.most_common(10):
        print(f"    {root:12s}  ×{count}")
    print()

    print(f"  EXAMPLE B-RUNS WITH CONTEXT (first 15):")
    for folio, example in b_run_examples[:15]:
        print(f"    [{folio}] {example}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # SYNTHESIS
    # ═══════════════════════════════════════════════════════════════
    print("═" * 90)
    print("SYNTHESIS — ROOT-TYPE GRAMMAR — the substance/process root split")
    print("═" * 90)
    print()

    # Summarize key findings
    if mid_zone < (low_zone + high_zone) * 0.3:
        print(f"  1. A/B SPLIT: BIMODAL — clear gap ({low_zone} A, {mid_zone} M, {high_zone} B)")
    else:
        print(f"  1. A/B SPLIT: Continuum with peaks ({low_zone} A, {mid_zone} M, {high_zone} B)")

    if bb_obs / bb_exp > 1.15:
        print(f"  2. LINE GRAMMAR: B-roots CLUSTER ({bb_obs/bb_exp:.2f}× expected) — instruction sequences")
    elif ab_obs / ab_exp > 1.05 and ba_obs / ba_exp > 1.05:
        print(f"  2. LINE GRAMMAR: A↔B alternation — noun-verb pattern")
    else:
        print(f"  2. LINE GRAMMAR: No strong sequencing pattern")

    q_l_rate = 100 * q_suf.get("l", 0) / len(q_words) if q_words else 0
    print(f"  3. q- PREFIX: Selects suffix -l at {q_l_rate:.0f}%, attaches to Type A roots")
    print(f"     → q- may be a QUANTIFIER or DETERMINER, not an operation")

    y_first_rate = 100 * first_suf.get("y", 0) / sum(first_suf.values())
    y_last_rate = 100 * last_suf.get("y", 0) / sum(last_suf.values())
    print(f"  4. POSITION: -y at line start={y_first_rate:.1f}%, line end={y_last_rate:.1f}%")
    if y_last_rate > y_first_rate + 5:
        print(f"     → -y words gravitate toward LINE END (verb-final?)")
    elif y_first_rate > y_last_rate + 5:
        print(f"     → -y words gravitate toward LINE START")
    else:
        print(f"     → -y words distributed relatively evenly")

    total_b_runs = sum(b_run_lengths.values())
    print(f"  5. B-RUNS: {total_b_runs} runs of ≥2 process-roots found")
    if b_run_before:
        top_before = b_run_before.most_common(3)
        print(f"     → Most common A-root BEFORE B-runs: {', '.join(f'{r}' for r, _ in top_before)}")
    if b_run_after:
        top_after = b_run_after.most_common(3)
        print(f"     → Most common A-root AFTER B-runs: {', '.join(f'{r}' for r, _ in top_after)}")
    print()

    # Populate results (was previously left empty -> JSON output was always {})
    results["root_classes"] = {
        "A": len(type_a), "M": len(type_m), "B": len(type_b),
        "tokens_A": freq_a, "tokens_M": freq_m, "tokens_B": freq_b,
    }
    results["ydominance_zones"] = {
        "A_0_30": low_zone, "M_30_80": mid_zone, "B_80_100": high_zone,
        "bimodal": mid_zone < (low_zone + high_zone) * 0.3,
    }
    results["bigram_ratios"] = {
        "AA": aa_obs / aa_exp if aa_exp else None,
        "AB": ab_obs / ab_exp if ab_exp else None,
        "BA": ba_obs / ba_exp if ba_exp else None,
        "BB": bb_obs / bb_exp if bb_exp else None,
    }
    results["q_prefix"] = {
        "n_q": len(q_words), "n_qo": len(qo_words),
        "q_l_rate": q_suf.get("l", 0) / len(q_words) if q_words else None,
    }
    results["y_position"] = {"first_pct": y_first_rate, "last_pct": y_last_rate}
    results["b_runs_ge2"] = sum(b_run_lengths.values())

    print("  Results saved to results/root_type_grammar_results.json")
    print()
    print("═" * 90)
    print("ANALYSIS COMPLETE")
    print("═" * 90)

    return results


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    folio_dir = Path("folios")
    txt_files = sorted(folio_dir.glob("*.txt"))
    print(f"  Loading {len(txt_files)} folios...")
    all_lines = extract_parsed_lines(txt_files)
    print(f"  Extracted {len(all_lines)} parsed lines")
    print()

    results = analyze(all_lines)

    with open(result_path("root_type_grammar_results.json"), "w") as f:
        json.dump(results, f, indent=2, default=str)
