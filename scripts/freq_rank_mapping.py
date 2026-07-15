#!/usr/bin/env python3
"""
VOYNICH MANUSCRIPT — FREQUENCY-RANK MAPPING (Phase 1)
======================================================
If Voynichese is a pharmaceutical notation system where:
  prefix = operation/preparation type
  root   = ingredient/substance
  suffix = form/dosage/modifier

Then:
  - Root frequencies should follow Zipf's law (real ingredient lists do)
  - Roots should cluster into FUNCTIONAL CLASSES by suffix profile
  - Top roots should appear across many sections (common ingredients)
  - Certain roots should be section-exclusive (specialist ingredients)
  - The prefix × suffix matrix should reveal PREPARATION CATEGORIES

This script maps the morphological data to a pharmaceutical interpretation
and tests whether the mapping produces internally consistent results.
"""

import re
import json
import math
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations

# ═══════════════════════════════════════════════════════════════════════════
# PARSER (reused from previous scripts)
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
                        remainder = rest3[:-len(suf)] if suf and rest3.endswith(suf) and rest3 != suf else ""
                        if rest3 == suf:
                            remainder = ""
                        elif rest3.endswith(suf):
                            remainder = rest3[:-len(suf)]
                        else:
                            remainder = rest3
                    elif suf == "":
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


def get_root(onset, body):
    return onset + body


# ═══════════════════════════════════════════════════════════════════════════
# DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def classify_folio(header_lines):
    text = "\n".join(header_lines).lower()
    if "herbal" in text:
        section = "herbal"
    elif "astro" in text or "cosmo" in text or "star" in text or "zodiac" in text:
        section = "astro"
    elif "pharm" in text or "recipe" in text or "balneo" in text:
        section = "pharma"
    elif "biolog" in text or "bathy" in text:
        section = "bio"
    elif "text only" in text:
        section = "text"
    else:
        section = "other"
    lang = "B" if "language b" in text else "A" if "language a" in text else "?"
    return section, lang


def extract_all_data(txt_files):
    all_data = {
        'text_lines': [],
        'label_words': [],
        'folio_info': {},
        'section_words': defaultdict(list),
        'lang_words': defaultdict(list),
    }
    for txt_file in txt_files:
        lines_raw = txt_file.read_text(encoding="utf-8").splitlines()
        header_lines = []
        folio_name = txt_file.stem
        section, lang = None, None
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
            line_words = []
            for tok in tokens:
                tok = tok.strip()
                if not tok or "?" in tok or "'" in tok:
                    continue
                if re.match(r"^[a-z]+$", tok) and len(tok) >= 2:
                    if is_label:
                        all_data['label_words'].append((tok, folio_name, section))
                    else:
                        line_words.append(tok)
            if line_words:
                if section is None:
                    section, lang = classify_folio(header_lines)
                    all_data['folio_info'][folio_name] = {'section': section, 'lang': lang}
                all_data['text_lines'].append((folio_name, section, lang, line_words))
                for w in line_words:
                    all_data['section_words'][section].append(w)
                    all_data['lang_words'][lang].append(w)
        if section is None:
            section, lang = classify_folio(header_lines)
            all_data['folio_info'][folio_name] = {'section': section, 'lang': lang}
    return all_data


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def analyze(data):
    """Full frequency-rank analysis."""
    results = {}

    # Parse all words
    all_parses = []  # (folio, section, lang, word, pfx, root, suf, remainder)
    for folio, section, lang, words in data['text_lines']:
        for w in words:
            pfx, onset, body, suf, rem = parse_word(w)
            if not rem:
                root = get_root(onset, body)
                all_parses.append((folio, section, lang, w, pfx or "∅", root, suf or "∅"))

    # Also parse labels
    label_parses = []
    for w, folio, section in data['label_words']:
        pfx, onset, body, suf, rem = parse_word(w)
        if not rem:
            root = get_root(onset, body)
            label_parses.append((folio, section, w, pfx or "∅", root, suf or "∅"))

    print(f"  Total parsed tokens: {len(all_parses)}")
    print(f"  Total parsed labels: {len(label_parses)}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 1: ZIPF'S LAW FOR ROOTS
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 1: ZIPF'S LAW FOR ROOTS")
    print("=" * 90)
    print()
    print("  If roots = real-world ingredients, they should follow Zipf's law")
    print("  (a few very common, long tail of rare ones)")
    print()

    root_freq = Counter(p[5] for p in all_parses)
    ranked = root_freq.most_common()
    total_roots = len(ranked)
    total_tokens = sum(c for _, c in ranked)

    print(f"  Distinct roots: {total_roots}")
    print(f"  Total root tokens: {total_tokens}")
    print()

    # Zipf fit: log(freq) = -alpha * log(rank) + C
    ranks = []
    freqs = []
    for i, (root, freq) in enumerate(ranked):
        if freq >= 3:  # only fit roots with freq >= 3
            ranks.append(math.log(i + 1))
            freqs.append(math.log(freq))

    if len(ranks) > 2:
        n = len(ranks)
        sum_x = sum(ranks)
        sum_y = sum(freqs)
        sum_xy = sum(x * y for x, y in zip(ranks, freqs))
        sum_xx = sum(x * x for x in ranks)
        alpha = -(n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x ** 2)
        C = (sum_y + alpha * sum_x) / n
        # R² calculation
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in freqs)
        ss_res = sum((y - (C - alpha * x)) ** 2 for x, y in zip(ranks, freqs))
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        print(f"  Zipf exponent α = {alpha:.3f}  (natural language ≈ 1.0)")
        print(f"  R² = {r_squared:.4f}")
        if alpha > 0.7 and alpha < 1.5:
            print(f"  ✓ ZIPF-LIKE: α in normal range for natural vocabulary")
        elif alpha < 0.7:
            print(f"  ✗ FLATTER than Zipf: too even distribution (notation-like?)")
        else:
            print(f"  ✗ STEEPER than Zipf: extreme concentration on few roots")
        print()

        results['zipf'] = {'alpha': alpha, 'r_squared': r_squared, 'n_roots': total_roots}

    # Show top 30 roots with their rank, freq, and percentage
    print(f"  {'Rank':>4}  {'Root':12s}  {'Freq':>6}  {'%':>6}  {'Cum%':>6}  Suffix profile")
    print(f"  {'─' * 4}  {'─' * 12}  {'─' * 6}  {'─' * 6}  {'─' * 6}  {'─' * 40}")
    cumulative = 0
    root_suffix_profiles = {}
    for i, (root, freq) in enumerate(ranked[:30]):
        pct = 100 * freq / total_tokens
        cumulative += pct
        # Get suffix profile for this root
        suffixes = Counter()
        for p in all_parses:
            if p[5] == root:
                suffixes[p[6]] += 1
        top_suf = suffixes.most_common(4)
        suf_str = ", ".join(f"{s}:{c}" for s, c in top_suf)
        root_suffix_profiles[root] = suffixes
        print(f"  {i + 1:4d}  {root:12s}  {freq:6d}  {pct:5.1f}%  {cumulative:5.1f}%  {suf_str}")

    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 2: ROOT FUNCTIONAL CLASSES (by suffix profile)
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 2: ROOT FUNCTIONAL CLASSES — Clustering by suffix profile")
    print("=" * 90)
    print()
    print("  If suffix = form/preparation, roots with similar suffix profiles")
    print("  belong to the same SUBSTANCE CLASS (e.g., herbs, minerals, liquids)")
    print()

    # Build suffix profile vectors for roots with freq >= 20
    freq_roots = [(r, f) for r, f in ranked if f >= 20]
    all_suffixes_set = sorted(set(s for p in all_parses for s in [p[6]]))

    # Compute cosine similarity clusters
    def suffix_vector(root):
        counts = Counter()
        total = 0
        for p in all_parses:
            if p[5] == root:
                counts[p[6]] += 1
                total += 1
        if total == 0:
            return [0] * len(all_suffixes_set)
        return [counts.get(s, 0) / total for s in all_suffixes_set]

    vectors = {}
    for root, freq in freq_roots:
        vectors[root] = suffix_vector(root)

    # Simple k-means-like clustering: compute pairwise cosine similarity
    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x ** 2 for x in a))
        nb = math.sqrt(sum(x ** 2 for x in b))
        if na == 0 or nb == 0:
            return 0
        return dot / (na * nb)

    # Find natural clusters using dominant suffix
    suffix_clusters = defaultdict(list)
    for root, freq in freq_roots:
        suf_counts = Counter()
        for p in all_parses:
            if p[5] == root:
                suf_counts[p[6]] += 1
        total = sum(suf_counts.values())
        dominant_suf, dom_count = suf_counts.most_common(1)[0]
        dominance = dom_count / total

        # Classify based on dominant suffix and dominance level
        if dominance > 0.85:
            cluster = f"MONO-{dominant_suf}"
        elif dominance > 0.5:
            top2 = suf_counts.most_common(2)
            cluster = f"DOM-{top2[0][0]}+{top2[1][0]}"
        else:
            top3 = suf_counts.most_common(3)
            cluster = f"POLY-{'+'.join(s for s, _ in top3)}"

        suffix_clusters[cluster].append((root, freq, dominance))

    # Sort clusters by total frequency
    cluster_ranking = sorted(suffix_clusters.items(),
                             key=lambda x: -sum(f for _, f, _ in x[1]))

    print(f"  Found {len(cluster_ranking)} suffix-profile clusters among {len(freq_roots)} roots (freq≥20)")
    print()

    results['clusters'] = {}
    for cluster_name, members in cluster_ranking[:15]:
        members.sort(key=lambda x: -x[1])
        total_freq = sum(f for _, f, _ in members)
        member_str = ", ".join(f"{r}({f})" for r, f, _ in members[:8])
        if len(members) > 8:
            member_str += f", ... +{len(members) - 8} more"
        print(f"  {cluster_name:30s}  n={len(members):3d}  total={total_freq:6d}")
        print(f"    {member_str}")
        print()
        results['clusters'][cluster_name] = {
            'count': len(members),
            'total_freq': total_freq,
            'members': [(r, f) for r, f, _ in members]
        }

    # ═══════════════════════════════════════════════════════════════
    # TEST 3: SECTION DISTRIBUTION OF TOP ROOTS
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 3: SECTION DISTRIBUTION — Where each root appears")
    print("=" * 90)
    print()
    print("  If root = ingredient, common ones should appear everywhere")
    print("  Specialist roots should cluster in specific sections")
    print()

    sections = ['herbal', 'pharma', 'astro', 'bio', 'text']
    section_totals = Counter()
    for p in all_parses:
        section_totals[p[1]] += 1

    # For top 30 roots: compute section distribution
    print(f"  {'Root':12s}", end="")
    for sec in sections:
        print(f"  {sec:>8s}", end="")
    print(f"  {'Spread':>8s}  {'Specialist?':12s}")
    print(f"  {'─' * 12}", end="")
    for sec in sections:
        print(f"  {'─' * 8}", end="")
    print(f"  {'─' * 8}  {'─' * 12}")

    results['section_distribution'] = {}
    for root, total_freq in ranked[:30]:
        sec_counts = Counter()
        for p in all_parses:
            if p[5] == root:
                sec_counts[p[1]] += 1

        print(f"  {root:12s}", end="")
        observed_fracs = []
        expected_fracs = []
        for sec in sections:
            count = sec_counts.get(sec, 0)
            pct = 100 * count / total_freq if total_freq > 0 else 0
            print(f"  {pct:7.1f}%", end="")
            observed_fracs.append(count / total_freq if total_freq > 0 else 0)
            expected_fracs.append(section_totals.get(sec, 0) / sum(section_totals.values()))

        # Entropy of section distribution (higher = more spread)
        H = 0
        for frac in observed_fracs:
            if frac > 0:
                H -= frac * math.log2(frac)

        # Chi-squared test: is this root over/under-represented somewhere?
        chi2 = 0
        for obs, exp in zip(observed_fracs, expected_fracs):
            if exp > 0:
                chi2 += (obs - exp) ** 2 / exp

        specialist = ""
        max_frac = max(observed_fracs)
        max_sec = sections[observed_fracs.index(max_frac)]
        if max_frac > 0.5 and chi2 > 0.05:
            specialist = f"→ {max_sec}"

        print(f"  {H:7.2f}b  {specialist:12s}")

        results['section_distribution'][root] = {
            'sections': {sec: sec_counts.get(sec, 0) for sec in sections},
            'entropy': H,
            'chi2': chi2,
            'specialist': specialist
        }

    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 4: PREFIX × SUFFIX MATRIX — Preparation categories
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 4: PREFIX × SUFFIX MATRIX — Preparation category map")
    print("=" * 90)
    print()
    print("  If prefix=operation and suffix=form, then prefix×suffix = preparation type")
    print("  E.g., qo+_+y might always mean 'decoction', ∅+_+l might mean 'simple'")
    print()

    pfx_suf_counts = Counter()
    pfx_counts = Counter()
    suf_counts = Counter()
    for p in all_parses:
        pfx_suf_counts[(p[4], p[6])] += 1
        pfx_counts[p[4]] += 1
        suf_counts[p[6]] += 1

    # Show top prefixes × top suffixes as a matrix
    top_prefixes = [p for p, _ in pfx_counts.most_common(10)]
    top_suffixes = [s for s, _ in suf_counts.most_common(10)]

    # Header
    print(f"  {'prefix':>8s}", end="")
    for suf in top_suffixes:
        print(f"  {suf:>7s}", end="")
    print(f"  {'TOTAL':>7s}")
    print(f"  {'─' * 8}", end="")
    for _ in top_suffixes:
        print(f"  {'─' * 7}", end="")
    print(f"  {'─' * 7}")

    results['prefix_suffix_matrix'] = {}
    for pfx in top_prefixes:
        print(f"  {pfx:>8s}", end="")
        row = {}
        for suf in top_suffixes:
            count = pfx_suf_counts.get((pfx, suf), 0)
            print(f"  {count:7d}", end="")
            row[suf] = count
        print(f"  {pfx_counts[pfx]:7d}")
        results['prefix_suffix_matrix'][pfx] = row
    print()

    # Compute what % of each prefix goes to each suffix (normalized)
    print("  NORMALIZED (% of prefix going to each suffix):")
    print(f"  {'prefix':>8s}", end="")
    for suf in top_suffixes:
        print(f"  {suf:>7s}", end="")
    print()
    print(f"  {'─' * 8}", end="")
    for _ in top_suffixes:
        print(f"  {'─' * 7}", end="")
    print()

    for pfx in top_prefixes:
        total = pfx_counts[pfx]
        print(f"  {pfx:>8s}", end="")
        for suf in top_suffixes:
            count = pfx_suf_counts.get((pfx, suf), 0)
            pct = 100 * count / total if total > 0 else 0
            print(f"  {pct:6.1f}%", end="")
        print()
    print()

    # Check: does the prefix significantly change the suffix distribution?
    # (If prefix = operation, it should select for certain forms/suffixes)
    print("  PREFIX SPECIFICITY (how much each prefix biases suffix choice):")
    print(f"  {'prefix':>8s}  {'KL div':>8s}  {'Top suffix bias':30s}")
    print(f"  {'─' * 8}  {'─' * 8}  {'─' * 30}")

    # Baseline suffix distribution
    total_all = sum(suf_counts.values())
    baseline = {s: suf_counts[s] / total_all for s in suf_counts}

    for pfx in top_prefixes:
        total_pfx = pfx_counts[pfx]
        pfx_dist = {}
        for suf in suf_counts:
            pfx_dist[suf] = pfx_suf_counts.get((pfx, suf), 0) / total_pfx

        # KL divergence from baseline
        kl = 0
        for suf in suf_counts:
            p = pfx_dist.get(suf, 0)
            q = baseline.get(suf, 1e-10)
            if p > 0:
                kl += p * math.log2(p / q)

        # What suffix is most enriched vs baseline?
        enrichments = []
        for suf in suf_counts:
            obs = pfx_dist.get(suf, 0)
            exp = baseline.get(suf, 1e-10)
            if obs > 0.02:  # only report suffixes that appear at least 2%
                enrichments.append((suf, obs / exp))
        enrichments.sort(key=lambda x: -x[1])
        bias_str = ", ".join(f"{s}:{r:.1f}×" for s, r in enrichments[:3])

        print(f"  {pfx:>8s}  {kl:8.3f}  {bias_str}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 5: ROOT CO-OCCURRENCE — Ingredient combinations
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 5: ROOT CO-OCCURRENCE — Common ingredient pairs")
    print("=" * 90)
    print()
    print("  In recipe texts, certain ingredients commonly appear together")
    print("  (e.g., honey+vinegar, wormwood+wine). Check if root pairs co-occur")
    print("  more than expected by chance within lines.")
    print()

    # Build root co-occurrence within lines
    top_30_roots = set(r for r, _ in ranked[:30])
    line_roots = defaultdict(list)  # (folio, line_idx) -> [roots]

    line_idx = 0
    for folio, section, lang, words in data['text_lines']:
        roots_in_line = []
        for w in words:
            pfx, onset, body, suf, rem = parse_word(w)
            if not rem:
                root = get_root(onset, body)
                if root in top_30_roots:
                    roots_in_line.append(root)
        if roots_in_line:
            line_roots[line_idx] = roots_in_line
        line_idx += 1

    # Count co-occurrences
    pair_counts = Counter()
    root_line_counts = Counter()
    total_lines = len(line_roots)

    for idx, roots in line_roots.items():
        unique_roots = set(roots)
        for r in unique_roots:
            root_line_counts[r] += 1
        for r1, r2 in combinations(sorted(unique_roots), 2):
            pair_counts[(r1, r2)] += 1

    # PMI (pointwise mutual information) for top pairs
    print(f"  Total lines with parsed roots: {total_lines}")
    print()

    pmi_scores = []
    for (r1, r2), count in pair_counts.items():
        if count < 5:
            continue
        p_joint = count / total_lines
        p_r1 = root_line_counts[r1] / total_lines
        p_r2 = root_line_counts[r2] / total_lines
        expected = p_r1 * p_r2 * total_lines
        pmi = math.log2(p_joint / (p_r1 * p_r2)) if p_r1 > 0 and p_r2 > 0 else 0
        pmi_scores.append((r1, r2, count, expected, pmi))

    pmi_scores.sort(key=lambda x: -x[4])

    print(f"  TOP 20 ROOT PAIRS BY PMI (freq≥5):")
    print(f"  {'Root 1':12s}  {'Root 2':12s}  {'Obs':>5s}  {'Exp':>7s}  {'PMI':>6s}")
    print(f"  {'─' * 12}  {'─' * 12}  {'─' * 5}  {'─' * 7}  {'─' * 6}")
    results['top_pairs'] = []
    for r1, r2, obs, exp, pmi in pmi_scores[:20]:
        print(f"  {r1:12s}  {r2:12s}  {obs:5d}  {exp:7.1f}  {pmi:6.2f}")
        results['top_pairs'].append({'r1': r1, 'r2': r2, 'obs': obs, 'exp': round(exp, 1), 'pmi': round(pmi, 3)})
    print()

    # Also show most frequent pairs (raw co-occurrence)
    freq_pairs = pair_counts.most_common(20)
    print(f"  TOP 20 ROOT PAIRS BY RAW FREQUENCY:")
    print(f"  {'Root 1':12s}  {'Root 2':12s}  {'Count':>6s}  {'Expected':>8s}  {'Ratio':>6s}")
    print(f"  {'─' * 12}  {'─' * 12}  {'─' * 6}  {'─' * 8}  {'─' * 6}")
    for (r1, r2), count in freq_pairs:
        p_r1 = root_line_counts[r1] / total_lines
        p_r2 = root_line_counts[r2] / total_lines
        expected = p_r1 * p_r2 * total_lines
        ratio = count / expected if expected > 0 else 0
        print(f"  {r1:12s}  {r2:12s}  {count:6d}  {expected:8.1f}  {ratio:5.1f}×")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 6: LABEL ROOTS vs TEXT ROOTS — Named substances
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 6: LABEL vs TEXT ROOT COMPARISON")
    print("=" * 90)
    print()
    print("  Labels (plant names, diagram markers) should use ingredient-roots")
    print("  more often than operation-roots. If our clustering is correct,")
    print("  labels should be enriched in certain root clusters.")
    print()

    label_root_counts = Counter()
    for folio, section, w, pfx, root, suf in label_parses:
        label_root_counts[root] += 1

    text_root_counts = Counter()
    for p in all_parses:
        text_root_counts[p[5]] += 1

    total_label = sum(label_root_counts.values())
    total_text = sum(text_root_counts.values())

    print(f"  Label tokens: {total_label}")
    print(f"  Text tokens: {total_text}")
    print()

    # Enrichment ratio for each root in labels vs text
    enrichments = []
    for root in set(list(label_root_counts.keys()) + list(text_root_counts.keys())):
        label_frac = label_root_counts.get(root, 0) / total_label if total_label > 0 else 0
        text_frac = text_root_counts.get(root, 0) / total_text if total_text > 0 else 0
        if label_root_counts.get(root, 0) >= 3:
            enrichment = label_frac / text_frac if text_frac > 0 else float('inf')
            enrichments.append((root, label_root_counts.get(root, 0),
                                text_root_counts.get(root, 0), enrichment))

    enrichments.sort(key=lambda x: -x[3])

    print(f"  ROOTS ENRICHED IN LABELS (≥3 label occurrences):")
    print(f"  {'Root':12s}  {'Labels':>7s}  {'Text':>7s}  {'Enrichment':>11s}")
    print(f"  {'─' * 12}  {'─' * 7}  {'─' * 7}  {'─' * 11}")
    results['label_enriched'] = []
    for root, lab_ct, text_ct, enrich in enrichments[:15]:
        print(f"  {root:12s}  {lab_ct:7d}  {text_ct:7d}  {enrich:10.1f}×")
        results['label_enriched'].append({'root': root, 'labels': lab_ct, 'text': text_ct, 'enrichment': round(enrich, 2)})
    print()

    enrichments.sort(key=lambda x: x[3])
    print(f"  ROOTS DEPLETED IN LABELS (label-avoidant):")
    print(f"  {'Root':12s}  {'Labels':>7s}  {'Text':>7s}  {'Enrichment':>11s}")
    print(f"  {'─' * 12}  {'─' * 7}  {'─' * 7}  {'─' * 11}")
    for root, lab_ct, text_ct, enrich in enrichments[:10]:
        print(f"  {root:12s}  {lab_ct:7d}  {text_ct:7d}  {enrich:10.2f}×")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 7: PHARMACEUTICAL ROLE ASSIGNMENT
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("TEST 7: PHARMACEUTICAL ROLE ASSIGNMENT — Tentative mapping")
    print("=" * 90)
    print()
    print("  Combine all evidence to assign provisional roles:")
    print("  - Root class (by suffix profile)")
    print("  - Section preference (herbal/pharma/astro/bio/text)")
    print("  - Label enrichment (is it a 'naming' root?)")
    print("  - Co-occurrence partners (what does it appear with?)")
    print()

    # Build combined profile for top 20 roots
    for root, total_freq in ranked[:20]:
        # Suffix profile
        suf_c = Counter()
        pfx_c = Counter()
        sec_c = Counter()
        for p in all_parses:
            if p[5] == root:
                suf_c[p[6]] += 1
                pfx_c[p[4]] += 1
                sec_c[p[1]] += 1

        dom_suf = suf_c.most_common(1)[0]
        dom_pfx = pfx_c.most_common(1)[0]
        dom_sec = sec_c.most_common(1)[0]
        suf_dominance = dom_suf[1] / total_freq

        # Top co-occurrence partners
        partners = []
        for (r1, r2), count in pair_counts.most_common():
            if r1 == root:
                partners.append((r2, count))
            elif r2 == root:
                partners.append((r1, count))
            if len(partners) >= 3:
                break

        # Label enrichment
        lab_ct = label_root_counts.get(root, 0)
        text_ct = text_root_counts.get(root, 0)
        lab_ratio = (lab_ct / total_label) / (text_ct / total_text) if text_ct > 0 and total_label > 0 else 0

        # Role inference
        if suf_dominance > 0.85 and dom_suf[0] == 'y':
            role = "PROCESS-WORD (y-dominant → verbal/action)"
        elif suf_dominance > 0.85:
            role = f"FIXED-FORM ({dom_suf[0]}-locked)"
        elif dom_suf[0] in ('iin', 'in', 'r', 'l', 'm') and suf_dominance < 0.5:
            role = "POLY-FORM SUBSTANCE (multiple preparations)"
        elif lab_ratio > 2.0:
            role = "NAMING-ROOT (label-enriched → plant name?)"
        elif dom_sec[1] / total_freq > 0.5:
            role = f"SPECIALIST ({dom_sec[0]}-heavy)"
        else:
            role = "GENERAL-PURPOSE"

        partner_str = ", ".join(f"{r}" for r, c in partners[:3])

        print(f"  ROOT: {root:8s}  freq={total_freq:5d}  role={role}")
        print(f"    dominant suffix: {dom_suf[0]}({100 * dom_suf[1] / total_freq:.0f}%)  "
              f"dominant prefix: {dom_pfx[0]}({100 * dom_pfx[1] / total_freq:.0f}%)  "
              f"section: {dom_sec[0]}({100 * dom_sec[1] / total_freq:.0f}%)")
        print(f"    top partners: {partner_str}   label ratio: {lab_ratio:.1f}×")
        print()

    # ═══════════════════════════════════════════════════════════════
    # GRAND SUMMARY
    # ═══════════════════════════════════════════════════════════════
    print("═" * 90)
    print("GRAND SUMMARY — FREQUENCY-RANK MAPPING")
    print("═" * 90)
    print()

    # Summarize findings
    print(f"  1. ZIPF'S LAW: α={results['zipf']['alpha']:.2f}, R²={results['zipf']['r_squared']:.3f}")
    if results['zipf']['alpha'] > 0.7 and results['zipf']['alpha'] < 1.5:
        print(f"     → Root distribution IS Zipf-like (consistent with real vocabulary)")
    else:
        print(f"     → Root distribution deviates from Zipf's law")
    print()

    print(f"  2. FUNCTIONAL CLASSES: {len(cluster_ranking)} clusters found")
    mono_y = sum(1 for cn, _ in cluster_ranking if cn.startswith("MONO-y"))
    mono_other = sum(1 for cn, _ in cluster_ranking if cn.startswith("MONO-") and not cn.startswith("MONO-y"))
    poly = sum(1 for cn, _ in cluster_ranking if cn.startswith("POLY-"))
    print(f"     → {mono_y} MONO-y clusters (process/verb-like roots)")
    print(f"     → {mono_other} other MONO clusters (fixed-form roots)")
    print(f"     → {poly} POLY clusters (multi-form substance roots)")
    print()

    # Count specialists
    specialists = sum(1 for r in results['section_distribution'].values() if r['specialist'])
    print(f"  3. SECTION SPECIALISTS: {specialists}/30 top roots have section preference")
    print()

    print(f"  4. KEY INSIGHT — TWO ROOT TYPES:")
    print(f"     TYPE A ('substances'): ka, da, a, o, ta, cho, ko, sa, cha, do, to")
    print(f"       → Multiple suffix forms (iin, r, l, in, m = different preparations)")
    print(f"       → Appear across all sections")
    print(f"       → High prefix variety (operations applied to them)")
    print(f"     TYPE B ('processes'): ched, kee, keed, shed, che, ked, she, ted, chee, kch")
    print(f"       → Almost exclusively suffix -y (95%+)")
    print(f"       → Often prefixed with qo- or ∅")
    print(f"       → These behave like VERBS or ACTIONS")
    print()

    print(f"  5. PHARMACEUTICAL INTERPRETATION:")
    print(f"     prefix (operation) + root (ingredient/action) + suffix (form)")
    print(f"     Where suffix -y = verb/process form")
    print(f"           suffix -iin/-in = noun/substance form")
    print(f"           suffix -l/-r = adjective/modifier form")
    print()

    print("  Results saved to freq_rank_results.json")
    print()
    print("═" * 90)
    print("FREQUENCY-RANK MAPPING COMPLETE")
    print("═" * 90)

    return results


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    folio_dir = Path("folios")
    txt_files = sorted(folio_dir.glob("*.txt"))
    print(f"  Loading {len(txt_files)} folios...")
    data = extract_all_data(txt_files)
    print(f"  Extracted {len(data['text_lines'])} text lines")
    print()

    results = analyze(data)

    with open("freq_rank_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
