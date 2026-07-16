#!/usr/bin/env python3
"""
Cross-Sign Label Network Analysis

Questions:
  1. Which zodiac signs share the most labels? Does sharing follow
     astrological geometry (triplicities, oppositions, sextiles)?
  2. Do shared labels cluster at specific degree positions?
  3. What is the "vocabulary fingerprint" of each sign?
  4. Can we identify label "families" that span the zodiac in regular patterns?
  5. Do degree-position pairs (e.g., "degree 10 in any sign") share roots?

This builds on all prior phases: label extraction (pipeline), cross-reference
(astro_crossref), ring mapping (ring_decan), and medieval degrees.
"""

import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from common import result_path

# ── Load data ────────────────────────────────────────────────────────────

def load_ring_data():
    with open(result_path("ring_decan_results.json"), encoding="utf-8") as f:
        return json.load(f)

# ── Parser (from pipeline) ───────────────────────────────────────────────
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


# ── Astrological geometry ────────────────────────────────────────────────

SIGN_ORDER = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# Available signs (Capricorn + Aquarius missing)
AVAILABLE = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Pisces"]

ELEMENTS = {
    "Fire":  ["Aries", "Leo", "Sagittarius"],
    "Earth": ["Taurus", "Virgo"],  # Capricorn missing
    "Air":   ["Gemini", "Libra"],  # Aquarius missing
    "Water": ["Cancer", "Scorpio", "Pisces"],
}

MODALITIES = {
    "Cardinal": ["Aries", "Cancer", "Libra"],  # Capricorn missing
    "Fixed":    ["Taurus", "Leo", "Scorpio"],   # Aquarius missing
    "Mutable":  ["Gemini", "Virgo", "Sagittarius", "Pisces"],
}

SIGN_ELEMENT = {}
for elem, signs in ELEMENTS.items():
    for s in signs:
        SIGN_ELEMENT[s] = elem

SIGN_MODALITY = {}
for mod, signs in MODALITIES.items():
    for s in signs:
        SIGN_MODALITY[s] = mod

def sign_distance(s1, s2):
    """Angular distance in signs (0-6)."""
    i1 = SIGN_ORDER.index(s1)
    i2 = SIGN_ORDER.index(s2)
    d = abs(i1 - i2)
    return min(d, 12 - d)

def aspect_type(s1, s2):
    """Classical aspect between signs."""
    d = sign_distance(s1, s2)
    return {0: "conjunction", 1: "semi-sextile", 2: "sextile", 3: "square",
            4: "trine", 5: "quincunx", 6: "opposition"}.get(d, "none")


# ══════════════════════════════════════════════════════════════════════════
#  ANALYSIS PHASES
# ══════════════════════════════════════════════════════════════════════════

def prepare_data(data):
    """Build per-sign label sets and annotate nymphs."""
    signs = {}
    for sign in AVAILABLE:
        nymphs = data[sign]["nymphs"]
        for n in nymphs:
            first_word = n["label"].split(".")[0]
            pf, root, sf, ok = parse_word(first_word)
            n["prefix"] = pf
            n["root"] = root
            n["suffix"] = sf
            n["parsed"] = ok
            n["sign"] = sign
        signs[sign] = {
            "nymphs": nymphs,
            "labels": [n["label"] for n in nymphs],
            "label_set": set(n["label"] for n in nymphs),
            "root_set": set(n["root"] for n in nymphs),
        }
    return signs


# ── Sign-to-Sign Sharing Matrix ─────────────────────────────────

def part1_sharing_matrix(signs):
    print("=" * 70)
    print("Sign-to-Sign Label Sharing Matrix")
    print("=" * 70)

    # Jaccard similarity of label sets for all sign pairs
    pairs = []
    for s1, s2 in combinations(AVAILABLE, 2):
        shared = signs[s1]["label_set"] & signs[s2]["label_set"]
        union = signs[s1]["label_set"] | signs[s2]["label_set"]
        jaccard = len(shared) / len(union) if union else 0
        pairs.append((s1, s2, len(shared), jaccard, shared))

    # Print matrix
    abbrevs = {s: s[:3] for s in AVAILABLE}
    print(f"\n  Label Jaccard similarity (shared labels / union):")
    print(f"  {'':>5}", end="")
    for s in AVAILABLE:
        print(f" {abbrevs[s]:>5}", end="")
    print()
    print(f"  {'':>5}", end="")
    for _ in AVAILABLE:
        print(f" {'-----':>5}", end="")
    print()

    jaccard_matrix = {}
    for s1 in AVAILABLE:
        print(f"  {abbrevs[s1]:>5}", end="")
        for s2 in AVAILABLE:
            if s1 == s2:
                print(f"  {'---':>4}", end="")
            else:
                key = tuple(sorted([s1, s2]))
                if key not in jaccard_matrix:
                    shared = signs[s1]["label_set"] & signs[s2]["label_set"]
                    union = signs[s1]["label_set"] | signs[s2]["label_set"]
                    jaccard_matrix[key] = len(shared) / len(union) if union else 0
                j = jaccard_matrix[key]
                print(f" {j:>5.3f}", end="")
        print()

    # Top 10 most similar pairs
    pairs_sorted = sorted(pairs, key=lambda x: -x[3])
    print(f"\n  Top 10 most similar sign pairs:")
    print(f"  {'Pair':<30} {'Shared':>6} {'Jaccard':>8} {'Aspect':<14} {'Element':<6} {'Shared labels'}")
    print(f"  {'-'*30} {'-'*6} {'-'*8} {'-'*14} {'-'*6} {'-'*30}")
    for s1, s2, count, j, shared in pairs_sorted[:10]:
        asp = aspect_type(s1, s2)
        same_elem = "YES" if SIGN_ELEMENT.get(s1) == SIGN_ELEMENT.get(s2) else ""
        shared_str = ", ".join(sorted(shared)[:5])
        if len(shared) > 5:
            shared_str += f" (+{len(shared)-5})"
        print(f"  {s1+'↔'+s2:<30} {count:>6} {j:>8.4f} {asp:<14} {same_elem:<6} {shared_str}")

    # Bottom 5 least similar
    print(f"\n  Bottom 5 least similar sign pairs:")
    for s1, s2, count, j, shared in pairs_sorted[-5:]:
        asp = aspect_type(s1, s2)
        print(f"  {s1+'↔'+s2:<30} {count:>6} {j:>8.4f} {asp:<14}")

    return pairs_sorted


# ── Astrological Geometry Test ──────────────────────────────────

def part2_geometry(signs, pairs):
    print("\n" + "=" * 70)
    print("Does label sharing follow astrological geometry?")
    print("=" * 70)

    # Group pairs by aspect type
    by_aspect = defaultdict(list)
    for s1, s2, count, j, shared in pairs:
        asp = aspect_type(s1, s2)
        by_aspect[asp].append(j)

    print(f"\n  Mean Jaccard by classical aspect:")
    print(f"  {'Aspect':<16} {'Mean J':>8} {'N pairs':>8} {'Sharing prediction'}")
    print(f"  {'-'*16} {'-'*8} {'-'*8} {'-'*25}")
    overall_mean = sum(j for _, _, _, j, _ in pairs) / len(pairs)
    for asp in ["conjunction", "semi-sextile", "sextile", "square",
                "trine", "quincunx", "opposition"]:
        vals = by_aspect[asp]
        if vals:
            mean_j = sum(vals) / len(vals)
            # Trine/sextile = harmonious (should share MORE if astrological)
            # Square/opposition = dissonant (should share LESS)
            pred = ""
            if asp in ("trine", "sextile"):
                pred = "harmonious → more?"
            elif asp in ("square", "opposition"):
                pred = "dissonant → less?"
            marker = " ◄" if abs(mean_j - overall_mean) > 0.005 else ""
            print(f"  {asp:<16} {mean_j:>8.4f} {len(vals):>8} {pred}{marker}")

    print(f"  {'OVERALL':<16} {overall_mean:>8.4f} {len(pairs):>8}")

    # Group by element (triplicity)
    print(f"\n  Mean Jaccard by element pairing:")
    by_elem_pair = defaultdict(list)
    for s1, s2, count, j, shared in pairs:
        e1 = SIGN_ELEMENT.get(s1, "?")
        e2 = SIGN_ELEMENT.get(s2, "?")
        key = "SAME" if e1 == e2 else f"{min(e1,e2)}+{max(e1,e2)}"
        by_elem_pair[key].append(j)

    for key in sorted(by_elem_pair.keys()):
        vals = by_elem_pair[key]
        mean_j = sum(vals) / len(vals)
        marker = " ◄" if key == "SAME" else ""
        print(f"    {key:<16}: J={mean_j:.4f} (n={len(vals)}){marker}")

    # Group by modality
    print(f"\n  Mean Jaccard by modality pairing:")
    by_mod_pair = defaultdict(list)
    for s1, s2, count, j, shared in pairs:
        m1 = SIGN_MODALITY.get(s1, "?")
        m2 = SIGN_MODALITY.get(s2, "?")
        key = "SAME" if m1 == m2 else f"{min(m1,m2)}+{max(m1,m2)}"
        by_mod_pair[key].append(j)

    for key in sorted(by_mod_pair.keys()):
        vals = by_mod_pair[key]
        mean_j = sum(vals) / len(vals)
        print(f"    {key:<24}: J={mean_j:.4f} (n={len(vals)})")

    # Sign distance vs Jaccard
    print(f"\n  Jaccard vs angular distance (signs apart):")
    by_dist = defaultdict(list)
    for s1, s2, count, j, shared in pairs:
        d = sign_distance(s1, s2)
        by_dist[d].append(j)

    for d in sorted(by_dist.keys()):
        vals = by_dist[d]
        mean_j = sum(vals) / len(vals)
        bar = "█" * int(mean_j * 200)
        print(f"    {d} signs apart: J={mean_j:.4f} (n={len(vals):>2}) {bar}")


# ── Degree-Position Sharing ─────────────────────────────────────

def part3_degree_position(signs):
    print("\n" + "=" * 70)
    print("Do same degree-positions share roots across signs?")
    print("=" * 70)

    # For each degree 1-30, collect (sign, root, suffix, label) across all signs
    by_degree = defaultdict(list)
    for sign_name, sd in signs.items():
        for n in sd["nymphs"]:
            by_degree[n["degree"]].append(n)

    print(f"\n  Root diversity at each degree position:")
    print(f"  {'Degree':>6} {'Signs':>5} {'Unique roots':>12} {'Most common root':<18} "
          f"{'Root freq':>9} {'Concentration':>13}")
    print(f"  {'-'*6} {'-'*5} {'-'*12} {'-'*18} {'-'*9} {'-'*13}")

    concentrated_degrees = []
    for deg in range(1, 31):
        nymphs = by_degree[deg]
        if not nymphs:
            continue
        n_signs = len(set(n["sign"] for n in nymphs))
        roots = Counter(n["root"] for n in nymphs)
        top_root, top_freq = roots.most_common(1)[0]
        concentration = top_freq / len(nymphs)
        print(f"  {deg:>6}° {n_signs:>5} {len(roots):>12} {top_root:<18} "
              f"{top_freq:>9} {concentration:>12.0%}")
        if concentration > 0.25:
            concentrated_degrees.append((deg, top_root, top_freq, concentration, nymphs))

    # Any degree where ≥3 signs use the same root?
    print(f"\n  Degrees where one root dominates (>25% concentration):")
    for deg, root, freq, conc, nymphs in concentrated_degrees:
        root_signs = [n["sign"][:3] for n in nymphs if n["root"] == root]
        print(f"    Degree {deg}°: root '{root}' in {freq}/{len(nymphs)} signs "
              f"({conc:.0%}) — {', '.join(root_signs)}")

    # Decan position (1-10) sharing
    print(f"\n  Root sharing by decan-degree position (1-10):")
    by_decan_pos = defaultdict(list)
    for sign_name, sd in signs.items():
        for n in sd["nymphs"]:
            dp = ((n["degree"] - 1) % 10) + 1  # 1-10 within decan
            by_decan_pos[dp].append(n)

    for dp in range(1, 11):
        nymphs = by_decan_pos[dp]
        roots = Counter(n["root"] for n in nymphs)
        top_root, top_freq = roots.most_common(1)[0]
        unique = len(roots)
        labels = Counter(n["label"] for n in nymphs)
        shared_labels = sum(1 for v in labels.values() if v > 1)
        print(f"    Position {dp:>2}: {len(nymphs)} nymphs, {unique} unique roots, "
              f"top='{top_root}'({top_freq}), {shared_labels} shared labels")


# ── Label Family Analysis ───────────────────────────────────────

def part4_label_families(signs):
    print("\n" + "=" * 70)
    print("Label Families — root clusters spanning the zodiac")
    print("=" * 70)

    # Group all nymphs by root
    by_root = defaultdict(list)
    for sign_name, sd in signs.items():
        for n in sd["nymphs"]:
            by_root[n["root"]].append(n)

    # Roots appearing in 3+ signs
    multi_sign_roots = {}
    for root, nymphs in by_root.items():
        sign_set = set(n["sign"] for n in nymphs)
        if len(sign_set) >= 3:
            multi_sign_roots[root] = {
                "count": len(nymphs),
                "signs": sign_set,
                "nymphs": nymphs,
            }

    print(f"\n  Roots appearing in 3+ signs ({len(multi_sign_roots)} found):")
    print(f"  {'Root':<14} {'N':>3} {'Signs':>5} {'Degrees':<40} {'Suffixes'}")
    print(f"  {'-'*14} {'-'*3} {'-'*5} {'-'*40} {'-'*20}")

    for root in sorted(multi_sign_roots.keys(), key=lambda r: -multi_sign_roots[r]["count"]):
        info = multi_sign_roots[root]
        degrees = [f"{n['sign'][:3]}°{n['degree']}" for n in info["nymphs"]]
        suffixes = Counter(n["suffix"] for n in info["nymphs"])
        suf_str = ", ".join(f"{s}({c})" for s, c in suffixes.most_common(3))
        deg_str = ", ".join(degrees[:6])
        if len(degrees) > 6:
            deg_str += f" (+{len(degrees)-6})"
        print(f"  {root:<14} {info['count']:>3} {len(info['signs']):>5} {deg_str:<40} {suf_str}")

    # Root family = roots sharing a common onset
    print(f"\n  Root families (same onset, different body):")
    onsets = defaultdict(list)
    for root in by_root.keys():
        for onset in ["tal", "kal", "kar", "tar", "ch", "ke", "te", "pa"]:
            if root.startswith(onset) and len(root) > len(onset):
                onsets[onset + "-"].append(root)
                break

    for onset, roots in sorted(onsets.items(), key=lambda x: -len(x[1])):
        if len(roots) < 3:
            continue
        total = sum(len(by_root[r]) for r in roots)
        sign_coverage = len(set(n["sign"] for r in roots for n in by_root[r]))
        print(f"    {onset} family: {len(roots)} roots, {total} labels, "
              f"{sign_coverage}/{len(AVAILABLE)} signs")
        for r in sorted(roots, key=lambda r: -len(by_root[r])):
            n_signs = len(set(n["sign"] for n in by_root[r]))
            print(f"      {r:<20} {len(by_root[r]):>3} labels in {n_signs} signs")

    # Suffix patterns across root families
    print(f"\n  Suffix variation within multi-sign roots:")
    print(f"  (Do roots take different suffixes in different signs?)")
    for root in sorted(multi_sign_roots.keys(), key=lambda r: -multi_sign_roots[r]["count"])[:10]:
        info = multi_sign_roots[root]
        by_sign_suffix = defaultdict(list)
        for n in info["nymphs"]:
            by_sign_suffix[n["sign"]].append(n["suffix"])
        suffix_sets = [set(v) for v in by_sign_suffix.values()]
        all_suffixes = set().union(*suffix_sets)
        if len(all_suffixes) > 1:
            print(f"    {root}: {dict((s[:3], list(set(v))) for s, v in by_sign_suffix.items())}")


# ── Sign Vocabulary Fingerprints ─────────────────────────────────

def part5_fingerprints(signs):
    print("\n" + "=" * 70)
    print("Sign Vocabulary Fingerprints")
    print("=" * 70)

    # For each sign, what makes it unique?
    all_roots = set()
    for sd in signs.values():
        all_roots.update(sd["root_set"])

    print(f"\n  Total unique roots across all zodiac labels: {len(all_roots)}")

    for sign in AVAILABLE:
        sd = signs[sign]
        unique_roots = sd["root_set"] - set().union(*(s["root_set"] for s_name, s in signs.items() if s_name != sign))
        shared_roots = sd["root_set"] - unique_roots

        nymphs = sd["nymphs"]
        o_rate = sum(1 for n in nymphs if "o" in n["prefix"]) / len(nymphs)
        y_rate = sum(1 for n in nymphs if n["suffix"] == "y") / len(nymphs)
        iin_rate = sum(1 for n in nymphs if n["suffix"] in ("iin", "aiin")) / len(nymphs)

        suffix_dist = Counter(n["suffix"] for n in nymphs)
        top_suf = suffix_dist.most_common(3)
        suf_str = ", ".join(f"{s}({c})" for s, c in top_suf if s)

        print(f"\n  {sign} ({SIGN_ELEMENT.get(sign, '?')}/{SIGN_MODALITY.get(sign, '?')}):")
        print(f"    Roots: {len(sd['root_set'])} total, {len(unique_roots)} UNIQUE to this sign")
        print(f"    o-rate: {o_rate:.0%}  -y: {y_rate:.0%}  -iin: {iin_rate:.0%}")
        print(f"    Top suffixes: {suf_str}")
        if unique_roots:
            unique_list = sorted(unique_roots)[:8]
            print(f"    Signature roots: {', '.join(unique_list)}", end="")
            if len(unique_roots) > 8:
                print(f" (+{len(unique_roots)-8} more)")
            else:
                print()

    # Cluster signs by root Jaccard
    print(f"\n  Sign clustering by root overlap:")
    root_pairs = []
    for s1, s2 in combinations(AVAILABLE, 2):
        shared = signs[s1]["root_set"] & signs[s2]["root_set"]
        union = signs[s1]["root_set"] | signs[s2]["root_set"]
        j = len(shared) / len(union) if union else 0
        root_pairs.append((s1, s2, j))

    root_pairs.sort(key=lambda x: -x[2])
    print(f"  Top root-sharing pairs:")
    for s1, s2, j in root_pairs[:5]:
        shared = signs[s1]["root_set"] & signs[s2]["root_set"]
        asp = aspect_type(s1, s2)
        print(f"    {s1}↔{s2}: J={j:.3f} ({len(shared)} roots) [{asp}]")

    print(f"  Bottom root-sharing pairs:")
    for s1, s2, j in root_pairs[-3:]:
        asp = aspect_type(s1, s2)
        print(f"    {s1}↔{s2}: J={j:.3f} [{asp}]")


# ── Network Topology & Hub Labels ───────────────────────────────

def part6_network(signs):
    print("\n" + "=" * 70)
    print("Label Network Topology — hubs, bridges, isolates")
    print("=" * 70)

    # Build label → sign mapping
    label_signs = defaultdict(set)
    label_info = {}
    for sign_name, sd in signs.items():
        for n in sd["nymphs"]:
            label_signs[n["label"]].add(sign_name)
            if n["label"] not in label_info:
                label_info[n["label"]] = n

    # Categorize labels
    hubs = {l: s for l, s in label_signs.items() if len(s) >= 3}
    bridges = {l: s for l, s in label_signs.items() if len(s) == 2}
    isolates = {l: s for l, s in label_signs.items() if len(s) == 1}

    print(f"\n  Label topology:")
    print(f"    Hub labels (3+ signs):     {len(hubs):>4}")
    print(f"    Bridge labels (2 signs):   {len(bridges):>4}")
    print(f"    Isolate labels (1 sign):   {len(isolates):>4}")
    print(f"    Total unique labels:       {len(label_signs):>4}")

    # Hub analysis
    if hubs:
        print(f"\n  HUB LABELS (appear in 3+ signs):")
        print(f"  {'Label':<24} {'Signs':>5} {'Root':<14} {'Suffix':<8} {'Degree positions'}")
        print(f"  {'-'*24} {'-'*5} {'-'*14} {'-'*8} {'-'*30}")
        for label in sorted(hubs.keys(), key=lambda l: -len(hubs[l])):
            s_list = hubs[label]
            info = label_info[label]
            # Get degree in each sign
            deg_positions = []
            for sn, sd in signs.items():
                for n in sd["nymphs"]:
                    if n["label"] == label:
                        deg_positions.append(f"{sn[:3]}°{n['degree']}")
            deg_str = ", ".join(deg_positions)
            print(f"  {label:<24} {len(s_list):>5} {info['root']:<14} "
                  f"{info['suffix']:<8} {deg_str}")

    # Bridge analysis — which pairs do bridges connect most?
    print(f"\n  Bridge connectivity (which sign-pairs are linked by shared labels?):")
    pair_bridges = Counter()
    for label, s_list in bridges.items():
        pair = tuple(sorted(s_list))
        pair_bridges[pair] += 1

    for pair, count in pair_bridges.most_common(10):
        asp = aspect_type(pair[0], pair[1])
        same_elem = " [same element]" if SIGN_ELEMENT.get(pair[0]) == SIGN_ELEMENT.get(pair[1]) else ""
        print(f"    {pair[0]}↔{pair[1]}: {count} shared labels ({asp}){same_elem}")

    # Do bridges prefer certain aspects?
    bridge_aspect_counts = Counter()
    for pair, count in pair_bridges.items():
        asp = aspect_type(pair[0], pair[1])
        bridge_aspect_counts[asp] += count

    print(f"\n  Bridge labels by aspect type:")
    total_bridges = sum(bridge_aspect_counts.values())
    # Expected distribution (count of available pairs per aspect)
    aspect_pair_counts = Counter()
    for s1, s2 in combinations(AVAILABLE, 2):
        asp = aspect_type(s1, s2)
        aspect_pair_counts[asp] += 1

    total_pairs = sum(aspect_pair_counts.values())
    print(f"  {'Aspect':<16} {'Bridges':>8} {'% bridges':>10} {'Pairs':>6} {'Expected %':>10} {'Ratio':>8}")
    print(f"  {'-'*16} {'-'*8} {'-'*10} {'-'*6} {'-'*10} {'-'*8}")
    for asp in ["semi-sextile", "sextile", "square", "trine", "quincunx", "opposition"]:
        b_count = bridge_aspect_counts.get(asp, 0)
        b_pct = b_count / total_bridges * 100 if total_bridges else 0
        p_count = aspect_pair_counts.get(asp, 0)
        p_pct = p_count / total_pairs * 100 if total_pairs else 0
        ratio = (b_pct / p_pct) if p_pct > 0 else 0
        marker = " ◄" if ratio > 1.3 or ratio < 0.7 else ""
        print(f"  {asp:<16} {b_count:>8} {b_pct:>9.1f}% {p_count:>6} {p_pct:>9.1f}% {ratio:>7.2f}×{marker}")


# ── Synthesis ───────────────────────────────────────────────────

def part7_synthesis(signs, pairs):
    print("\n" + "=" * 70)
    print("CROSS-SIGN NETWORK SYNTHESIS")
    print("=" * 70)

    # Collect key metrics
    all_nymphs = [n for sd in signs.values() for n in sd["nymphs"]]
    label_signs = defaultdict(set)
    for sign_name, sd in signs.items():
        for n in sd["nymphs"]:
            label_signs[n["label"]].add(sign_name)

    n_hubs = sum(1 for s in label_signs.values() if len(s) >= 3)
    n_bridges = sum(1 for s in label_signs.values() if len(s) == 2)
    n_isolates = sum(1 for s in label_signs.values() if len(s) == 1)

    # Best aspect correlation
    by_aspect = defaultdict(list)
    for s1, s2, count, j, shared in pairs:
        asp = aspect_type(s1, s2)
        by_aspect[asp].append(j)

    overall_j = sum(j for _, _, _, j, _ in pairs) / len(pairs)
    best_asp = max(by_aspect.items(), key=lambda x: sum(x[1])/len(x[1]))
    worst_asp = min(by_aspect.items(), key=lambda x: sum(x[1])/len(x[1]))

    # Same element vs different
    same_elem_j = []
    diff_elem_j = []
    for s1, s2, count, j, shared in pairs:
        if SIGN_ELEMENT.get(s1) == SIGN_ELEMENT.get(s2):
            same_elem_j.append(j)
        else:
            diff_elem_j.append(j)

    se_mean = sum(same_elem_j) / len(same_elem_j) if same_elem_j else 0
    de_mean = sum(diff_elem_j) / len(diff_elem_j) if diff_elem_j else 0

    print(f"""
  ┌──────────────────────────────────────────────────────────────────────┐
  │  CROSS-SIGN LABEL NETWORK: RESULTS                                  │
  │                                                                      │
  │  NETWORK STRUCTURE:                                                  │
  │    Hub labels (3+ signs):   {n_hubs:>4}                                      │
  │    Bridge labels (2 signs): {n_bridges:>4}                                      │
  │    Isolate labels (1 sign): {n_isolates:>4}                                      │
  │    → {n_isolates/(n_hubs+n_bridges+n_isolates)*100:.0f}% of labels are UNIQUE to a single sign               │
  │                                                                      │
  │  ASTROLOGICAL GEOMETRY:                                              │
  │    Overall mean Jaccard:    {overall_j:.4f}                                  │
  │    Same element:            {se_mean:.4f}                                  │
  │    Different element:       {de_mean:.4f}                                  │
  │    Best aspect:  {best_asp[0]:<14} J={sum(best_asp[1])/len(best_asp[1]):.4f}                         │
  │    Worst aspect: {worst_asp[0]:<14} J={sum(worst_asp[1])/len(worst_asp[1]):.4f}                         │
  │                                                                      │
  │  INTERPRETATION:                                                     │
  │  If same-element >> different-element → TRIPLICITY matters           │
  │  If aspect distance correlates → ANGULAR geometry matters            │
  │  If both are flat → labels are assigned by DEGREE POSITION alone     │
  │  (i.e., "degree 15 in any sign" encodes the same concept)           │
  └──────────────────────────────────────────────────────────────────────┘""")


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Voynich Manuscript — Cross-Sign Label Network Analysis")
    print("=" * 70)

    data = load_ring_data()
    signs = prepare_data(data)

    pairs = part1_sharing_matrix(signs)
    part2_geometry(signs, pairs)
    part3_degree_position(signs)
    part4_label_families(signs)
    part5_fingerprints(signs)
    part6_network(signs)
    part7_synthesis(signs, pairs)

    print(f"\n  Analysis complete.")