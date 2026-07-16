#!/usr/bin/env python3
"""
Egyptian Connection Deep-Dive

The Voynich gallows have been confirmed as semantic determinatives
with four mapped domains:
  t = celestial/astronomical
  k = generic/default
  f = botanical/plant
  p = process/transformation

This phase tests whether the ENTIRE Voynich writing system follows
Egyptian hieroglyphic structural principles — not just determinatives,
but also phonetic complements, logograms, and consonantal roots.

Generated predictions from the Egyptian writing system model:

  P1: Prefixes are phonetic complements (agree with determinative type)
  P2: High-frequency short words are logograms (low paradigm diversity)
  P3: Vowel chains (e/ee/eee) are non-structural (consonantal skeleton)
  P4: Four gallows = Hermetic quaternary (4 elements / 4 humors)
  P5: Prefix × gallows × suffix = systematic classification grid
  P6: Co-occurring words on same folio share determinatives > chance

Historical context:
  - Horapollo's Hieroglyphica rediscovered ~1419 (Voynich dating window)
  - Medieval alchemists believed Egyptian priests encoded wisdom in symbols
  - Hermetic tradition built on quaternaries (4 elements, 4 humors)
  - Ramon Llull's Ars Magna (1305) created a systematic concept-notation
  - Hildegard von Bingen's Lingua Ignota (12th c.) invented a classified
    vocabulary with letter-substitution
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import classify_folio, gallows_base_v2 as gallows_base, strip_gallows, result_path

# ── Section classification ────────────────────────────────────────────────


# ── Gallows definitions ──────────────────────────────────────────────────

SIMPLE_GALLOWS = ["t", "k", "f", "p"]
BENCH_GALLOWS = ["cth", "ckh", "cph", "cfh"]
COMPOUND_GCH = ["tch", "kch", "pch", "fch"]
COMPOUND_GSH = ["tsh", "ksh", "psh", "fsh"]
ALL_GALLOWS = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

GALLOWS_REGEX = re.compile(
    r'(cth|ckh|cph|cfh|tch|kch|pch|fch|tsh|ksh|psh|fsh|[tkfp])'
)


def gallows_tier(g):
    if g in SIMPLE_GALLOWS:
        return "simple"
    elif g in BENCH_GALLOWS:
        return "bench"
    elif g in COMPOUND_GCH or g in COMPOUND_GSH:
        return "compound"
    return "unknown"

# ── Morphological parser ─────────────────────────────────────────────────

# True prefixes (from the corrected prefix inventory)
PREFIXES = ['qo', 'q', 'so', 'do', 'o', 'd', 's', 'y']
# True suffixes
SUFFIXES = ['aiin', 'ain', 'iin', 'in', 'ar', 'or', 'al', 'ol',
            'edy', 'ody', 'eedy', 'dy', 'sy', 'ey', 'y']

def parse_morphology(stripped_word):
    """Parse a gallows-stripped word into prefix + root + suffix."""
    w = stripped_word
    prefix = ""
    suffix = ""

    # Extract prefix (longest match first)
    for pf in PREFIXES:
        if w.startswith(pf) and len(w) > len(pf) + 1:
            prefix = pf
            w = w[len(pf):]
            break

    # Extract suffix (longest match first)
    for sf in SUFFIXES:
        if w.endswith(sf) and len(w) > len(sf):
            suffix = sf
            w = w[:-len(sf)]
            break

    root = w
    return prefix, root, suffix

# ── Data extraction ──────────────────────────────────────────────────────

def extract_all_words():
    folio_dir = Path("folios")
    all_data = []

    for txt_file in sorted(folio_dir.glob("*.txt")):
        section = classify_folio(txt_file)
        folio = txt_file.stem
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

            if "@Cc" in locus:
                locus_type = "ring"
            elif "@Lt" in locus or "@Lb" in locus:
                locus_type = "label"
            elif "@Lz" in locus or "&Lz" in locus:
                locus_type = "nymph"
            else:
                locus_type = "paragraph"

            text = re.sub(r'<![^>]*>', '', text)
            text = re.sub(r'<%>|<\$>|<->|<\.>', ' ', text)
            text = re.sub(r'<[^>]*>', '', text)
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
            text = re.sub(r'\{([^}]+)\}', r'\1', text)
            text = re.sub(r'@\d+;?', '', text)

            tokens = re.split(r'[.\s,<>\-]+', text)
            for tok in tokens:
                tok = tok.strip().replace("'", "")
                if not tok or '?' in tok:
                    continue
                if re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                    all_data.append((tok, section, folio, locus, locus_type))

    return all_data




# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: PHONETIC COMPLEMENT TEST
# ══════════════════════════════════════════════════════════════════════════
# Egyptian prediction: prefixes are phonetic complements that "agree" with
# the determinative. If so, each prefix should preferentially co-occur
# with specific gallows types. We measure mutual information.

def analysis1_phonetic_complement(all_data):
    print("=" * 72)
    print("ANALYSIS 1: PHONETIC COMPLEMENT TEST (Prefix × Gallows Agreement)")
    print("=" * 72)

    prefix_gallows = defaultdict(Counter)  # prefix → Counter(gallows_base)
    prefix_total = Counter()
    gallows_total = Counter()
    total_with_both = 0

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        if not gals or len(stripped) < 2:
            continue
        prefix, root, suffix = parse_morphology(stripped)
        if not prefix:
            prefix = "∅"  # bare (no prefix)

        for g in gals:
            base = gallows_base(g)
            prefix_gallows[prefix][base] += 1
            prefix_total[prefix] += 1
            gallows_total[base] += 1
            total_with_both += 1

    # Compute pointwise mutual information for each prefix × gallows pair
    print(f"\n  Total tokens with prefix + gallows: {total_with_both}")
    print(f"  Distinct prefixes: {len(prefix_total)}")
    print()

    print("  ── Prefix × Gallows Observed Frequencies ──")
    BASES = ['t', 'k', 'f', 'p']
    prefixes_sorted = sorted(prefix_total, key=prefix_total.get, reverse=True)

    header = f"  {'Prefix':<10}" + "".join(f"{'  '+b:>8}" for b in BASES) + f"{'Total':>8}" + f"{'Dominant':>10}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    results = {}
    for pf in prefixes_sorted[:15]:
        row = []
        total = prefix_total[pf]
        dom_base = ""
        dom_pct = 0
        for b in BASES:
            cnt = prefix_gallows[pf][b]
            pct = cnt / total * 100 if total > 0 else 0
            row.append(f"{cnt:>5}({pct:4.0f}%)")
            if pct > dom_pct:
                dom_pct = pct
                dom_base = b
        print(f"  {pf:<10}" + "".join(f"{r:>8}" for r in row) + f"{total:>8}" + f"{'  '+dom_base+' '+str(int(dom_pct))+'%':>10}")

        results[pf] = {
            "total": total,
            "dominant": dom_base,
            "dominant_pct": round(dom_pct, 1),
            "profile": {b: prefix_gallows[pf][b] for b in BASES}
        }

    # Compute mutual information
    print("\n  ── Pointwise Mutual Information (PMI) ──")
    print("  PMI > 0 means prefix and gallows co-occur MORE than expected")
    print("  PMI < 0 means they co-occur LESS than expected")
    print()

    pmi_results = {}
    significant_pairs = []
    for pf in prefixes_sorted[:10]:
        for b in BASES:
            observed = prefix_gallows[pf][b]
            if observed < 5:
                continue
            p_joint = observed / total_with_both
            p_prefix = prefix_total[pf] / total_with_both
            p_gallows = gallows_total[b] / total_with_both
            if p_prefix > 0 and p_gallows > 0:
                pmi = math.log2(p_joint / (p_prefix * p_gallows))
                key = f"{pf}+{b}"
                pmi_results[key] = round(pmi, 3)
                if abs(pmi) > 0.3:
                    significant_pairs.append((key, pmi, observed))

    significant_pairs.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"  {'Pair':<15}{'PMI':>8}{'Count':>8}  Interpretation")
    print("  " + "-" * 55)
    for key, pmi, cnt in significant_pairs[:20]:
        direction = "ATTRACT" if pmi > 0 else "REPEL"
        print(f"  {key:<15}{pmi:>+8.3f}{cnt:>8}  {direction}")

    # Egyptian complementarity test: does each prefix have ONE dominant gallows?
    print("\n  ── Egyptian Complementarity Assessment ──")
    prefix_specificity = {}
    for pf in prefixes_sorted[:10]:
        total = prefix_total[pf]
        if total < 20:
            continue
        counts = [prefix_gallows[pf][b] for b in BASES]
        max_pct = max(counts) / total * 100
        # Entropy as measure of specificity (lower = more specific)
        probs = [c / total for c in counts if c > 0]
        entropy = -sum(p * math.log2(p) for p in probs)
        max_entropy = math.log2(len(BASES))  # 2.0 bits for 4 categories
        specificity = 1 - (entropy / max_entropy)
        prefix_specificity[pf] = {
            "entropy": round(entropy, 3),
            "specificity": round(specificity, 3),
            "max_pct": round(max_pct, 1)
        }
        verdict = "COMPLEMENT" if specificity > 0.15 else "NON-SPECIFIC"
        print(f"  {pf:<10}  entropy={entropy:.3f}  specificity={specificity:.3f}  max_share={max_pct:.1f}%  → {verdict}")

    return {"prefix_profiles": results, "pmi": pmi_results, "specificity": prefix_specificity}


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: LOGOGRAM DETECTION
# ══════════════════════════════════════════════════════════════════════════
# Egyptian prediction: high-frequency short words are logograms with
# LESS gallows variation because they represent fixed concepts.

def analysis2_logogram_detection(all_data):
    print("\n" + "=" * 72)
    print("ANALYSIS 2: LOGOGRAM DETECTION (Frequency vs Paradigm Diversity)")
    print("=" * 72)

    word_freq = Counter()
    stripped_forms = defaultdict(set)  # stripped → set of gallowed forms
    stripped_gallows_types = defaultdict(set)  # stripped → set of gallows bases used
    stripped_freq = Counter()

    for word, section, folio, locus, ltype in all_data:
        word_freq[word] += 1
        stripped, gals = strip_gallows(word)
        if len(stripped) < 1:
            continue
        stripped_forms[stripped].add(word)
        stripped_freq[stripped] += 1
        for g in gals:
            stripped_gallows_types[stripped].add(gallows_base(g))

    # For each stripped word: frequency vs paradigm size
    print(f"\n  Total stripped forms: {len(stripped_freq)}")

    # Bin by frequency
    freq_bins = [
        ("1-5", 1, 5),
        ("6-20", 6, 20),
        ("21-50", 21, 50),
        ("51-100", 51, 100),
        ("101-200", 101, 200),
        ("201-500", 201, 500),
        ("501+", 501, 99999),
    ]

    print(f"\n  {'Freq bin':<12}{'Roots':>8}{'Avg forms':>12}{'Avg gal.types':>16}{'Logogram?':>12}")
    print("  " + "-" * 58)

    bin_results = {}
    for label, lo, hi in freq_bins:
        roots_in_bin = [s for s, f in stripped_freq.items() if lo <= f <= hi]
        if not roots_in_bin:
            continue
        avg_forms = sum(len(stripped_forms[s]) for s in roots_in_bin) / len(roots_in_bin)
        avg_gal = sum(len(stripped_gallows_types[s]) for s in roots_in_bin) / len(roots_in_bin)
        # Logographic signature: high frequency but low paradigm diversity
        is_logo = "YES" if avg_gal < 2.0 and lo >= 51 else ""
        print(f"  {label:<12}{len(roots_in_bin):>8}{avg_forms:>12.1f}{avg_gal:>16.2f}{is_logo:>12}")
        bin_results[label] = {
            "count": len(roots_in_bin),
            "avg_forms": round(avg_forms, 2),
            "avg_gallows_types": round(avg_gal, 2)
        }

    # Top candidates: high frequency, low paradigm diversity (ratio)
    print("\n  ── Potential Logograms (high freq, low diversity relative to freq) ──")
    candidates = []
    for s, freq in stripped_freq.items():
        if freq < 30:
            continue
        n_forms = len(stripped_forms[s])
        n_gal = len(stripped_gallows_types[s])
        # Diversity ratio: forms per log2(freq) — lower = more logographic
        diversity_ratio = n_forms / max(1, math.log2(freq))
        candidates.append((s, freq, n_forms, n_gal, diversity_ratio))

    candidates.sort(key=lambda x: x[4])
    print(f"  {'Stripped':<15}{'Freq':>8}{'Forms':>8}{'GalTypes':>10}{'DivRatio':>10}  Assessment")
    print("  " + "-" * 65)
    logo_results = {}
    for s, freq, nf, ng, dr in candidates[:25]:
        assessment = "LOGOGRAM" if dr < 1.5 and ng <= 2 else "MIXED" if dr < 2.5 else "PRODUCTIVE"
        print(f"  {s:<15}{freq:>8}{nf:>8}{ng:>10}{dr:>10.2f}  {assessment}")
        logo_results[s] = {
            "freq": freq, "forms": nf, "gallows_types": ng,
            "diversity_ratio": round(dr, 2), "assessment": assessment
        }

    # Correlation: frequency vs paradigm size
    freqs = []
    paradigms = []
    for s in stripped_freq:
        f = stripped_freq[s]
        if f >= 5:
            freqs.append(math.log2(f))
            paradigms.append(len(stripped_forms[s]))

    if freqs:
        n = len(freqs)
        mean_f = sum(freqs) / n
        mean_p = sum(paradigms) / n
        cov = sum((freqs[i] - mean_f) * (paradigms[i] - mean_p) for i in range(n)) / n
        std_f = (sum((x - mean_f) ** 2 for x in freqs) / n) ** 0.5
        std_p = (sum((x - mean_p) ** 2 for x in paradigms) / n) ** 0.5
        r = cov / (std_f * std_p) if std_f > 0 and std_p > 0 else 0
        print(f"\n  Pearson r(log2_freq, paradigm_size): {r:.3f}")
        print(f"  Interpretation: {'STRONG' if r > 0.7 else 'MODERATE' if r > 0.4 else 'WEAK'} positive correlation")
        print(f"  Egyptian prediction: logograms should show WEAKER correlation (flat diversity at high freq)")
    else:
        r = 0

    return {"freq_bins": bin_results, "logogram_candidates": logo_results, "correlation_r": round(r, 3)}


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 3: VOWEL-CHAIN EQUIVALENCE (Consonantal Skeleton Test)
# ══════════════════════════════════════════════════════════════════════════
# Egyptian prediction: vowels are not structurally significant. If so,
# oedy/oeedy/oeeedy should share IDENTICAL gallows profiles, because
# e/ee/eee variations are vowel quantity marks, not semantic distinctions.

def analysis3_vowel_chain_equivalence(all_data):
    print("\n" + "=" * 72)
    print("ANALYSIS 3: VOWEL-CHAIN EQUIVALENCE (Consonantal Skeleton Test)")
    print("=" * 72)

    # Build consonantal skeletons by collapsing e-chains
    def consonantal_skeleton(word):
        """Collapse e/ee/eee chains into a single 'E' marker."""
        return re.sub(r'e+', 'E', word)

    # Group stripped words by skeleton
    skeleton_groups = defaultdict(lambda: defaultdict(Counter))
    # skeleton → {variant_stripped → Counter(gallows_base)}
    skeleton_totals = defaultdict(Counter)
    skeleton_variant_count = defaultdict(set)

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        if len(stripped) < 2:
            continue
        skel = consonantal_skeleton(stripped)
        skeleton_variant_count[skel].add(stripped)
        for g in gals:
            skeleton_groups[skel][stripped][gallows_base(g)] += 1
            skeleton_totals[skel][gallows_base(g)] += 1

    # Find skeletons with multiple e-chain variants
    multi_variant = {s: v for s, v in skeleton_variant_count.items()
                     if len(v) >= 2 and 'E' in s}

    print(f"\n  Skeletons with e-chain variants: {len(multi_variant)}")

    # For each multi-variant skeleton, compare gallows profiles
    BASES = ['t', 'k', 'f', 'p']
    print(f"\n  ── Gallows Profile Comparison for e-chain Variants ──")
    print(f"  (Egyptian prediction: profiles should be SIMILAR across variants)")
    print()

    cosine_scores = []
    results = {}
    for skel in sorted(multi_variant, key=lambda s: sum(skeleton_totals[s].values()), reverse=True)[:30]:
        variants = sorted(skeleton_groups[skel].keys(),
                         key=lambda v: sum(skeleton_groups[skel][v].values()), reverse=True)

        # Only analyze if at least 2 variants have ≥10 gallows tokens
        rich_variants = [v for v in variants
                        if sum(skeleton_groups[skel][v].values()) >= 10]
        if len(rich_variants) < 2:
            continue

        print(f"  Skeleton: {skel}")
        variant_profiles = {}
        for v in rich_variants[:4]:
            total = sum(skeleton_groups[skel][v].values())
            profile = [skeleton_groups[skel][v].get(b, 0) / total for b in BASES]
            pcts = [f"{p*100:5.1f}%" for p in profile]
            dom = BASES[profile.index(max(profile))]
            print(f"    {v:<20} n={total:>4}  t={pcts[0]}  k={pcts[1]}  f={pcts[2]}  p={pcts[3]}  dom={dom}")
            variant_profiles[v] = profile

        # Pairwise cosine similarity
        if len(rich_variants) >= 2:
            pairs_sim = []
            for i in range(len(rich_variants)):
                for j in range(i + 1, len(rich_variants)):
                    a = [skeleton_groups[skel][rich_variants[i]].get(b, 0) for b in BASES]
                    b_vec = [skeleton_groups[skel][rich_variants[j]].get(b, 0) for b in BASES]
                    dot = sum(x * y for x, y in zip(a, b_vec))
                    norm_a = sum(x ** 2 for x in a) ** 0.5
                    norm_b = sum(x ** 2 for x in b_vec) ** 0.5
                    cos = dot / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0
                    pairs_sim.append(cos)
                    cosine_scores.append(cos)
            avg_sim = sum(pairs_sim) / len(pairs_sim)
            verdict = "EQUIVALENT" if avg_sim > 0.95 else "SIMILAR" if avg_sim > 0.85 else "DIFFERENT"
            print(f"    → avg cosine similarity: {avg_sim:.3f}  [{verdict}]")
            results[skel] = {
                "variants": list(rich_variants[:4]),
                "avg_cosine": round(avg_sim, 3),
                "verdict": verdict
            }
        print()

    if cosine_scores:
        overall_avg = sum(cosine_scores) / len(cosine_scores)
        high_sim = sum(1 for c in cosine_scores if c > 0.95) / len(cosine_scores) * 100
        print(f"  ── Vowel-Chain Equivalence Summary ──")
        print(f"  Overall mean cosine: {overall_avg:.3f}")
        print(f"  Pairs with cos > 0.95: {high_sim:.1f}%")
        print(f"  Egyptian prediction: cos should be HIGH (≥0.90) if vowels are non-structural")
        print(f"  Result: {'CONFIRMED' if overall_avg > 0.85 else 'PARTIAL' if overall_avg > 0.70 else 'REJECTED'} — vowels are {'non-structural' if overall_avg > 0.85 else 'partially structural' if overall_avg > 0.70 else 'structurally significant'}")
    else:
        overall_avg = 0
        high_sim = 0

    return {"skeleton_comparisons": results, "overall_cosine": round(overall_avg, 3), "high_sim_pct": round(high_sim, 1)}


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 4: HERMETIC QUATERNARY MAPPING
# ══════════════════════════════════════════════════════════════════════════
# Medieval alchemy uses quaternary systems: 4 elements (fire/air/water/earth),
# 4 humors (choleric/sanguine/phlegmatic/melancholic), 4 qualities
# (hot/cold/wet/dry). If gallows map to these, we should see specific
# co-occurrence patterns in pharma sections.

def analysis4_hermetic_quaternary(all_data):
    print("\n" + "=" * 72)
    print("ANALYSIS 4: HERMETIC QUATERNARY MAPPING")
    print("=" * 72)

    # Hypothesis: t=Fire/Hot, k=Earth/Cold, f=Water/Wet, p=Air/Dry
    # In pharmaceutical text, recipes should combine multiple elements
    # (as humoral medicine requires balancing). Test: gallows co-occurrence
    # patterns within paragraphs and within words.

    # Within-paragraph gallows co-occurrence
    para_gallows = defaultdict(Counter)  # (folio, locus) → Counter(gallows_base)
    folio_section = {}

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        for g in gals:
            para_gallows[(folio, locus)][gallows_base(g)] += 1
        folio_section[folio] = section

    BASES = ['t', 'k', 'f', 'p']
    section_cooccurrence = defaultdict(Counter)  # section → Counter of base-pairs

    for (folio, locus), counts in para_gallows.items():
        section = folio_section.get(folio, "unknown")
        # Count co-occurring gallows types in this paragraph
        present = [b for b in BASES if counts[b] > 0]
        for i, b1 in enumerate(present):
            for b2 in present[i + 1:]:
                pair = tuple(sorted([b1, b2]))
                section_cooccurrence[section][pair] += 1

    print(f"\n  ── Gallows Pair Co-occurrence by Section (paragraphs containing both) ──")
    ALL_PAIRS = [('f', 'k'), ('f', 'p'), ('f', 't'), ('k', 'p'), ('k', 't'), ('p', 't')]
    sections = ['herbal-A', 'herbal-B', 'pharma', 'bio', 'cosmo', 'text', 'zodiac']

    header = f"  {'Section':<12}" + "".join(f"{p[0]+'+'+p[1]:>8}" for p in ALL_PAIRS)
    print(header)
    print("  " + "-" * (len(header) - 2))

    cooccurrence_results = {}
    for sec in sections:
        total_paras = sum(1 for (f, l) in para_gallows if folio_section.get(f) == sec)
        row = []
        sec_data = {}
        for pair in ALL_PAIRS:
            cnt = section_cooccurrence[sec].get(pair, 0)
            pct = cnt / total_paras * 100 if total_paras > 0 else 0
            row.append(f"{pct:>7.1f}%")
            sec_data[pair[0] + "+" + pair[1]] = {"count": cnt, "pct": round(pct, 1)}
        print(f"  {sec:<12}" + "".join(row))
        cooccurrence_results[sec] = sec_data

    # Multi-word gallows sequences within paragraphs (quaternary balance test)
    print(f"\n  ── Quaternary Completeness (paragraphs with all 4 gallows types) ──")
    completeness = defaultdict(lambda: {"complete": 0, "three": 0, "two": 0, "one": 0, "total": 0})
    for (folio, locus), counts in para_gallows.items():
        section = folio_section.get(folio, "unknown")
        present = sum(1 for b in BASES if counts[b] > 0)
        completeness[section]["total"] += 1
        if present == 4:
            completeness[section]["complete"] += 1
        elif present == 3:
            completeness[section]["three"] += 1
        elif present == 2:
            completeness[section]["two"] += 1
        elif present == 1:
            completeness[section]["one"] += 1

    print(f"  {'Section':<12}{'All-4':>8}{'3-of-4':>8}{'2-of-4':>8}{'1-only':>8}{'Total':>8}")
    print("  " + "-" * 50)
    completeness_results = {}
    for sec in sections:
        d = completeness[sec]
        t = d["total"]
        pct4 = d["complete"] / t * 100 if t > 0 else 0
        print(f"  {sec:<12}{d['complete']:>8}{d['three']:>8}{d['two']:>8}{d['one']:>8}{t:>8}  ({pct4:.1f}% complete)")
        completeness_results[sec] = {
            "all_4": d["complete"], "three": d["three"], "two": d["two"],
            "one": d["one"], "total": t, "pct_complete": round(pct4, 1)
        }

    # Within-WORD multiple gallows test
    print(f"\n  ── Multi-Gallows Words (words with ≥2 different gallows bases) ──")
    multi_gal_words = Counter()
    multi_gal_section = defaultdict(int)
    total_gallowed_section = defaultdict(int)

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        if gals:
            total_gallowed_section[section] += 1
            bases_in_word = set(gallows_base(g) for g in gals)
            if len(bases_in_word) >= 2:
                multi_gal_words[word] += 1
                multi_gal_section[section] += 1

    print(f"\n  Section distribution of multi-gallows words:")
    print(f"  {'Section':<12}{'Multi':>8}{'Total':>8}{'Rate':>8}")
    print("  " + "-" * 35)
    for sec in sections:
        mg = multi_gal_section[sec]
        tg = total_gallowed_section[sec]
        rate = mg / tg * 100 if tg > 0 else 0
        print(f"  {sec:<12}{mg:>8}{tg:>8}{rate:>7.1f}%")

    print(f"\n  Most common multi-gallows words:")
    for w, c in multi_gal_words.most_common(15):
        stripped, gals = strip_gallows(w)
        bases = [gallows_base(g) for g in gals]
        print(f"    {w:<25} count={c:>4}  bases={'+'.join(bases)}  root={stripped}")

    return {"cooccurrence": cooccurrence_results, "completeness": completeness_results}


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 5: CLASSIFICATION GRID COMPLETENESS
# ══════════════════════════════════════════════════════════════════════════
# Philosophical language prediction: the system should produce a REGULAR,
# NON-REDUNDANT classification grid where prefix × gallows × suffix
# combinations are systematic.

def analysis5_classification_grid(all_data):
    print("\n" + "=" * 72)
    print("ANALYSIS 5: CLASSIFICATION GRID (Prefix × Gallows × Suffix)")
    print("=" * 72)

    # Build the 3D grid: prefix × gallows_base × suffix
    grid = defaultdict(int)  # (prefix, gallows, suffix) → count
    prefix_set = set()
    suffix_set = set()
    BASES = ['t', 'k', 'f', 'p']

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        if not gals or len(stripped) < 2:
            continue
        prefix, root, suffix = parse_morphology(stripped)
        if not prefix:
            prefix = "∅"
        if not suffix:
            suffix = "∅"

        prefix_set.add(prefix)
        suffix_set.add(suffix)

        for g in gals:
            grid[(prefix, gallows_base(g), suffix)] += 1

    total_cells = len(prefix_set) * len(BASES) * len(suffix_set)
    filled_cells = sum(1 for v in grid.values() if v > 0)
    fill_rate = filled_cells / total_cells * 100 if total_cells > 0 else 0

    print(f"\n  Grid dimensions: {len(prefix_set)} prefixes × 4 gallows × {len(suffix_set)} suffixes")
    print(f"  Total possible cells: {total_cells}")
    print(f"  Filled cells: {filled_cells}")
    print(f"  Fill rate: {fill_rate:.1f}%")
    print(f"  Philosophical language prediction: fill rate should be HIGH (>50%) if systematic")

    # Marginal: Prefix × Gallows (summed over suffixes)
    print(f"\n  ── Prefix × Gallows Marginal ──")
    pf_sorted = sorted(prefix_set, key=lambda p: sum(grid.get((p, b, s), 0)
                       for b in BASES for s in suffix_set), reverse=True)[:10]

    header = f"  {'Prefix':<10}" + "".join(f"{b:>8}" for b in BASES) + f"{'Total':>8}{'Fill':>8}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    pg_results = {}
    for pf in pf_sorted:
        row = []
        total = 0
        filled = 0
        for b in BASES:
            cnt = sum(grid.get((pf, b, s), 0) for s in suffix_set)
            total += cnt
            if cnt > 0:
                filled += 1
            row.append(f"{cnt:>8}")
        print(f"  {pf:<10}" + "".join(row) + f"{total:>8}{filled:>6}/4")
        pg_results[pf] = {"t": row[0].strip(), "k": row[1].strip(), "f": row[2].strip(), "p": row[3].strip()}

    # Marginal: Suffix × Gallows (summed over prefixes)
    print(f"\n  ── Suffix × Gallows Marginal ──")
    sf_sorted = sorted(suffix_set, key=lambda s: sum(grid.get((p, b, s), 0)
                       for b in BASES for p in prefix_set), reverse=True)[:15]

    header = f"  {'Suffix':<10}" + "".join(f"{b:>8}" for b in BASES) + f"{'Total':>8}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    sg_results = {}
    for sf in sf_sorted:
        row = []
        total = 0
        for b in BASES:
            cnt = sum(grid.get((p, b, sf), 0) for p in prefix_set)
            total += cnt
            row.append(f"{cnt:>8}")
        print(f"  {sf:<10}" + "".join(row) + f"{total:>8}")
        sg_results[sf] = {"t": row[0].strip(), "k": row[1].strip(), "f": row[2].strip(), "p": row[3].strip()}

    # Independence test: are prefix and gallows independent, or do they interact?
    print(f"\n  ── Independence Test ──")
    print(f"  If prefix choice and gallows choice are INDEPENDENT, the grid is")
    print(f"  purely combinatorial. If DEPENDENT, some combinations are preferred.")
    print()

    # Chi-square-like measure
    total_all = sum(grid.values())
    chi2 = 0
    expected_grid = {}
    for pf in pf_sorted[:8]:
        pf_total = sum(grid.get((pf, b, s), 0) for b in BASES for s in suffix_set)
        for b in BASES:
            gal_total = sum(grid.get((p, b, s), 0) for p in prefix_set for s in suffix_set)
            observed = sum(grid.get((pf, b, s), 0) for s in suffix_set)
            expected = (pf_total * gal_total / total_all) if total_all > 0 else 0
            if expected > 5:
                chi2 += (observed - expected) ** 2 / expected
                expected_grid[(pf, b)] = {"observed": observed, "expected": round(expected, 1)}

    df = (min(8, len(pf_sorted)) - 1) * 3
    print(f"  Chi-square statistic: {chi2:.1f}  (df={df})")
    print(f"  {'DEPENDENT' if chi2 > df * 3 else 'INDEPENDENT'}: prefix and gallows choices are {'NOT' if chi2 > df * 3 else ''} independent")

    if chi2 > df * 3:
        print(f"\n  Largest deviations from independence:")
        deviations = []
        for (pf, b), vals in expected_grid.items():
            if vals["expected"] > 10:
                ratio = vals["observed"] / vals["expected"]
                deviations.append((pf, b, vals["observed"], vals["expected"], ratio))
        deviations.sort(key=lambda x: abs(x[4] - 1), reverse=True)
        for pf, b, obs, exp, ratio in deviations[:10]:
            direction = "OVER" if ratio > 1 else "UNDER"
            print(f"    {pf}+{b}: observed={obs} expected={exp:.0f} ratio={ratio:.2f}× [{direction}]")

    return {
        "fill_rate": round(fill_rate, 1),
        "grid_dims": {"prefixes": len(prefix_set), "suffixes": len(suffix_set)},
        "prefix_gallows": pg_results,
        "chi_square": round(chi2, 1),
        "dependent": chi2 > df * 3
    }


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 6: FOLIO-LEVEL DETERMINATIVE CONSISTENCY
# ══════════════════════════════════════════════════════════════════════════
# Egyptian prediction: words co-occurring on the same folio (describing
# the same illustration) should share determinatives more than chance.

def analysis6_folio_consistency(all_data):
    print("\n" + "=" * 72)
    print("ANALYSIS 6: FOLIO-LEVEL DETERMINATIVE CONSISTENCY")
    print("=" * 72)

    # For each folio, compute the gallows entropy (how concentrated on one type)
    folio_gallows = defaultdict(Counter)  # folio → Counter(gallows_base)
    folio_section = {}

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        for g in gals:
            folio_gallows[folio][gallows_base(g)] += 1
        folio_section[folio] = section

    BASES = ['t', 'k', 'f', 'p']

    print(f"\n  Folios with gallows data: {len(folio_gallows)}")

    # Compute entropy for each folio
    folio_entropy = {}
    for folio, counts in folio_gallows.items():
        total = sum(counts.values())
        if total < 10:
            continue
        probs = [counts.get(b, 0) / total for b in BASES]
        probs = [p for p in probs if p > 0]
        entropy = -sum(p * math.log2(p) for p in probs)
        folio_entropy[folio] = entropy

    # Group by section and compare
    section_entropies = defaultdict(list)
    for folio, ent in folio_entropy.items():
        section_entropies[folio_section.get(folio, "unknown")].append(ent)

    sections = ['herbal-A', 'herbal-B', 'pharma', 'bio', 'cosmo', 'text', 'zodiac']
    print(f"\n  ── Average Gallows Entropy per Section ──")
    print(f"  (Lower entropy = more concentrated on one gallows type = more consistent)")
    print(f"  (Max entropy for 4 types = 2.00 bits)")
    print()
    print(f"  {'Section':<12}{'Mean H':>8}{'Min H':>8}{'Max H':>8}{'Folios':>8}")
    print("  " + "-" * 42)

    entropy_results = {}
    for sec in sections:
        ents = section_entropies.get(sec, [])
        if not ents:
            continue
        mean_h = sum(ents) / len(ents)
        print(f"  {sec:<12}{mean_h:>8.3f}{min(ents):>8.3f}{max(ents):>8.3f}{len(ents):>8}")
        entropy_results[sec] = {
            "mean": round(mean_h, 3), "min": round(min(ents), 3),
            "max": round(max(ents), 3), "n_folios": len(ents)
        }

    # Most consistent (lowest entropy) folios
    print(f"\n  ── Most Determinative-Consistent Folios (lowest entropy) ──")
    sorted_folios = sorted(folio_entropy.items(), key=lambda x: x[1])
    for folio, ent in sorted_folios[:15]:
        counts = folio_gallows[folio]
        total = sum(counts.values())
        dom = max(BASES, key=lambda b: counts.get(b, 0))
        dom_pct = counts.get(dom, 0) / total * 100
        sec = folio_section.get(folio, "unknown")
        profile = " ".join(f"{b}={counts.get(b, 0)}" for b in BASES)
        print(f"  {folio:<12} H={ent:.3f}  dom={dom}({dom_pct:.0f}%)  [{sec}]  {profile}")

    # Most diverse (highest entropy) folios
    print(f"\n  ── Most Determinative-Diverse Folios (highest entropy) ──")
    for folio, ent in sorted_folios[-15:]:
        counts = folio_gallows[folio]
        total = sum(counts.values())
        dom = max(BASES, key=lambda b: counts.get(b, 0))
        dom_pct = counts.get(dom, 0) / total * 100
        sec = folio_section.get(folio, "unknown")
        profile = " ".join(f"{b}={counts.get(b, 0)}" for b in BASES)
        print(f"  {folio:<12} H={ent:.3f}  dom={dom}({dom_pct:.0f}%)  [{sec}]  {profile}")

    # Compare intra-folio consistency vs inter-folio (within same section)
    print(f"\n  ── Intra-Folio vs Inter-Folio Similarity ──")
    print(f"  Egyptian prediction: intra-folio consistency should be HIGHER")
    print(f"  than inter-folio (same section), because each folio discusses")
    print(f"  one topic/illustration.")
    print()

    intra_cos = []
    inter_cos = []

    # For each section, compute pairwise cosine between folios
    for sec in sections:
        sec_folios = [f for f, s in folio_section.items() if s == sec and f in folio_entropy]
        if len(sec_folios) < 2:
            continue

        # Section-level profile
        sec_profile = [sum(folio_gallows[f].get(b, 0) for f in sec_folios) for b in BASES]

        for f in sec_folios:
            f_profile = [folio_gallows[f].get(b, 0) for b in BASES]
            f_total = sum(f_profile)
            if f_total < 10:
                continue
            # Intra-folio "consistency" = cosine of folio vs section average
            dot = sum(a * b for a, b in zip(f_profile, sec_profile))
            norm_f = sum(a ** 2 for a in f_profile) ** 0.5
            norm_s = sum(a ** 2 for a in sec_profile) ** 0.5
            if norm_f > 0 and norm_s > 0:
                intra_cos.append(dot / (norm_f * norm_s))

        # Inter-folio: pairwise between folios in same section
        for i in range(len(sec_folios)):
            for j in range(i + 1, min(i + 5, len(sec_folios))):
                fi = sec_folios[i]
                fj = sec_folios[j]
                a_vec = [folio_gallows[fi].get(b, 0) for b in BASES]
                b_vec = [folio_gallows[fj].get(b, 0) for b in BASES]
                if sum(a_vec) < 10 or sum(b_vec) < 10:
                    continue
                dot = sum(a * b for a, b in zip(a_vec, b_vec))
                na = sum(a ** 2 for a in a_vec) ** 0.5
                nb = sum(a ** 2 for a in b_vec) ** 0.5
                if na > 0 and nb > 0:
                    inter_cos.append(dot / (na * nb))

    if intra_cos and inter_cos:
        mean_intra = sum(intra_cos) / len(intra_cos)
        mean_inter = sum(inter_cos) / len(inter_cos)
        print(f"  Mean folio→section cosine: {mean_intra:.3f}  (n={len(intra_cos)})")
        print(f"  Mean folio↔folio cosine:   {mean_inter:.3f}  (n={len(inter_cos)})")
        print(f"  Egyptian prediction: folio→section should be ≥ folio↔folio")
        ratio = mean_intra / mean_inter if mean_inter > 0 else 0
        print(f"  Ratio: {ratio:.3f}")
    else:
        mean_intra = mean_inter = 0

    return {"entropy_by_section": entropy_results,
            "mean_intra_cos": round(mean_intra, 3) if intra_cos else None,
            "mean_inter_cos": round(mean_inter, 3) if inter_cos else None}


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 7: EGYPTIAN STRUCTURAL COMPARISON SYNTHESIS
# ══════════════════════════════════════════════════════════════════════════

def analysis7_synthesis(all_data, results):
    print("\n" + "=" * 72)
    print("SYNTHESIS: EGYPTIAN WRITING SYSTEM STRUCTURAL COMPARISON")
    print("=" * 72)

    print("""
  ┌──────────────────────────────────────────────────────────────────┐
  │  EGYPTIAN HIEROGLYPHIC          VOYNICH MANUSCRIPT               │
  │  STRUCTURE                      STRUCTURE                        │
  ├──────────────────────────────────────────────────────────────────┤
  │  Determinatives                 Gallows characters               │
  │  (unpronounced category         (t=celestial, k=generic,         │
  │   markers after words)           f=botanical, p=process)         │
  │                                                                  │
  │  Phonetic complements           Prefixes (qo-, do-, so-)        │
  │  (signs repeating part of       (co-select with specific         │
  │   the word's pronunciation)      gallows types?)                 │
  │                                                                  │
  │  Logograms                      High-frequency words             │
  │  (single signs for common       (aiin, ol, ar — if low           │
  │   words + determinative)         paradigm diversity)             │
  │                                                                  │
  │  Consonantal skeleton           Core root (after stripping       │
  │  (vowels not written or          gallows + prefix + suffix)      │
  │   inconsistently marked)                                        │
  │                                                                  │
  │  Bilateral/trilateral signs     Root morphemes                   │
  │  (2-3 consonant groups)         (2-4 glyph sequences)           │
  │                                                                  │
  │  Grammatical endings            Suffixes (-iin, -ar, -y,        │
  │  (case, number, gender           -edy, -dy, -sy)                │
  │   markers after roots)                                          │
  └──────────────────────────────────────────────────────────────────┘
""")

    # Scorecard
    print("  ── Prediction Scorecard ──")
    print()

    r1 = results.get("analysis1", {})
    r2 = results.get("analysis2", {})
    r3 = results.get("analysis3", {})
    r5 = results.get("analysis5", {})
    r6 = results.get("analysis6", {})

    # P1: Phonetic complements
    specific = r1.get("specificity", {})
    n_complement = sum(1 for v in specific.values() if v.get("specificity", 0) > 0.15)
    n_total_spec = len(specific)
    p1_score = n_complement / n_total_spec if n_total_spec > 0 else 0
    p1_verdict = "CONFIRMED" if p1_score > 0.5 else "PARTIAL" if p1_score > 0.25 else "REJECTED"
    print(f"  P1 Phonetic complements:  {n_complement}/{n_total_spec} prefixes show gallows preference  [{p1_verdict}]")

    # P2: Logograms
    r2_logos = r2.get("logogram_candidates", {})
    n_logos = sum(1 for v in r2_logos.values() if v.get("assessment") == "LOGOGRAM")
    corr = r2.get("correlation_r", 0)
    p2_verdict = "CONFIRMED" if n_logos >= 3 else "PARTIAL" if n_logos >= 1 else "REJECTED"
    print(f"  P2 Logogram detection:    {n_logos} logograms found, r={corr}  [{p2_verdict}]")

    # P3: Consonantal skeleton
    vowel_cos = r3.get("overall_cosine", 0)
    p3_verdict = "CONFIRMED" if vowel_cos > 0.85 else "PARTIAL" if vowel_cos > 0.70 else "REJECTED"
    print(f"  P3 Vowel-chain equiv:     mean cosine={vowel_cos:.3f}  [{p3_verdict}]")

    # P4: Hermetic quaternary (qualitative — just report)
    print(f"  P4 Hermetic quaternary:   (qualitative — see Analysis 4 above)")

    # P5: Classification grid
    fill = r5.get("fill_rate", 0)
    dep = r5.get("dependent", False)
    p5_verdict = "CONFIRMED" if dep and fill > 20 else "PARTIAL" if dep else "REJECTED"
    print(f"  P5 Classification grid:   fill={fill:.1f}%, dependent={dep}  [{p5_verdict}]")

    # P6: Folio consistency
    intra = r6.get("mean_intra_cos")
    inter = r6.get("mean_inter_cos")
    if intra and inter:
        p6_verdict = "CONFIRMED" if intra >= inter * 0.98 else "REJECTED"
        print(f"  P6 Folio consistency:     intra={intra:.3f} inter={inter:.3f}  [{p6_verdict}]")
    else:
        p6_verdict = "INSUFFICIENT DATA"
        print(f"  P6 Folio consistency:     [{p6_verdict}]")

    verdicts = [p1_verdict, p2_verdict, p3_verdict, p5_verdict, p6_verdict]
    confirmed = sum(1 for v in verdicts if v == "CONFIRMED")
    partial = sum(1 for v in verdicts if v == "PARTIAL")
    rejected = sum(1 for v in verdicts if v == "REJECTED")

    print(f"\n  ── Overall Assessment ──")
    print(f"  Confirmed: {confirmed}/5   Partial: {partial}/5   Rejected: {rejected}/5")
    print()

    if confirmed + partial >= 4:
        print("  CONCLUSION: The Voynich manuscript employs a writing system with")
        print("  STRONG structural parallels to Egyptian hieroglyphic writing.")
        print("  Gallows are determinatives, prefixes function as phonetic")
        print("  complements, and the morphological system follows a consonantal")
        print("  skeleton model. This is consistent with a 15th-century scholar")
        print("  designing a 'philosophical language' inspired by Horapollo's")
        print("  description of Egyptian hieroglyphics.")
    elif confirmed + partial >= 2:
        print("  CONCLUSION: The Voynich writing system shows PARTIAL parallels")
        print("  to Egyptian hieroglyphics, particularly in its determinative")
        print("  system. The remaining features may reflect a hybrid system")
        print("  combining Egyptian-like classification with other traditions")
        print("  (Hebrew morphology, alchemical notation).")
    else:
        print("  CONCLUSION: The Egyptian parallel is LIMITED to determinatives.")
        print("  The deeper structural features (logograms, phonetic complements)")
        print("  do not follow Egyptian patterns, suggesting a different")
        print("  organizing principle.")

    return {
        "scorecard": {
            "P1_phonetic_complement": p1_verdict,
            "P2_logogram": p2_verdict,
            "P3_vowel_equivalence": p3_verdict,
            "P4_hermetic": "QUALITATIVE",
            "P5_classification_grid": p5_verdict,
            "P6_folio_consistency": p6_verdict
        },
        "totals": {"confirmed": confirmed, "partial": partial, "rejected": rejected}
    }


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    all_data = extract_all_words()
    print(f"Loaded {len(all_data)} tokens from {len(set(w[2] for w in all_data))} folios\n")

    results = {}
    results["analysis1"] = analysis1_phonetic_complement(all_data)
    results["analysis2"] = analysis2_logogram_detection(all_data)
    results["analysis3"] = analysis3_vowel_chain_equivalence(all_data)
    results["analysis4"] = analysis4_hermetic_quaternary(all_data)
    results["analysis5"] = analysis5_classification_grid(all_data)
    results["analysis6"] = analysis6_folio_consistency(all_data)
    results["analysis7"] = analysis7_synthesis(all_data, results)

    # Save results
    out = result_path("egyptian_connection_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
