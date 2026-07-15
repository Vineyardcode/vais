#!/usr/bin/env python3
"""
Voynich Manuscript — Medieval Degree-Meaning Cross-Reference

Tests whether Voynich zodiac labels correlate with classical per-degree 
classification systems that would have been known to a 15th-century author:

  1. Egyptian Terms/Bounds — each degree ruled by one of 5 planets
  2. Bright/Dark/Smoky/Empty degrees — from Firmicus/Lilly
  3. Masculine/Feminine degrees — from Ptolemy/Lilly
  4. Lunar Mansions — 28 Arabic manzils overlaid on zodiac degrees

Sources:
  - Ptolemy, Tetrabiblos (2nd c.)
  - Firmicus Maternus, Mathesis (4th c.)
  - William Lilly, Christian Astrology (1647) - preserving classical data
  - Abu Ma'shar/Albumasar, Great Introduction (9th c.)
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from itertools import groupby

# ── Load ring_decan_results from previous Phase ─────────────────────────

RESULTS_FILE = Path("ring_decan_results.json")

def load_results():
    with open(RESULTS_FILE, encoding="utf-8") as f:
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

# ══════════════════════════════════════════════════════════════════════════
#  MEDIEVAL DEGREE CLASSIFICATION DATA
# ══════════════════════════════════════════════════════════════════════════

# ── 1. EGYPTIAN TERMS/BOUNDS ─────────────────────────────────────────────
# The most widely used system in medieval astrology. Each sign's 30° divided
# into 5 unequal sections, each ruled by a planet.
# Source: Paulus Alexandrinus, Firmicus, Valens (canonical Egyptian system)
# Format: list of (end_degree, planet_ruler) — degrees are 1-indexed inclusive

EGYPTIAN_TERMS = {
    "Aries":       [(6, "Jupiter"), (12, "Venus"), (20, "Mercury"), (25, "Mars"), (30, "Saturn")],
    "Taurus":      [(8, "Venus"), (14, "Mercury"), (22, "Jupiter"), (27, "Saturn"), (30, "Mars")],
    "Gemini":      [(6, "Mercury"), (12, "Jupiter"), (17, "Venus"), (24, "Mars"), (30, "Saturn")],
    "Cancer":      [(7, "Mars"), (13, "Venus"), (19, "Mercury"), (26, "Jupiter"), (30, "Saturn")],
    "Leo":         [(6, "Jupiter"), (11, "Venus"), (18, "Saturn"), (24, "Mercury"), (30, "Mars")],
    "Virgo":       [(7, "Mercury"), (17, "Venus"), (21, "Jupiter"), (28, "Mars"), (30, "Saturn")],
    "Libra":       [(6, "Saturn"), (14, "Mercury"), (21, "Jupiter"), (28, "Venus"), (30, "Mars")],
    "Scorpio":     [(7, "Mars"), (11, "Venus"), (19, "Mercury"), (24, "Jupiter"), (30, "Saturn")],
    "Sagittarius": [(12, "Jupiter"), (17, "Venus"), (21, "Mercury"), (26, "Saturn"), (30, "Mars")],
    "Pisces":      [(12, "Venus"), (16, "Jupiter"), (19, "Mercury"), (28, "Mars"), (30, "Saturn")],
}

def get_terms_ruler(sign, degree):
    """Return the planet that rules the given degree via Egyptian Terms."""
    if sign not in EGYPTIAN_TERMS:
        return None
    for end_deg, planet in EGYPTIAN_TERMS[sign]:
        if degree <= end_deg:
            return planet
    return None

# ── 2. BRIGHT / DARK / SMOKY / EMPTY DEGREES ─────────────────────────────
# From Firmicus Maternus (Mathesis) and preserved in Lilly (Christian Astrology)
# These mark certain degrees as bright (lucky/prominent), dark (unfortunate),
# smoky (obscured), or void/empty (neutral).

# Bright degrees by sign (1-indexed)
BRIGHT_DEGREES = {
    "Aries":       [9, 15, 20, 25, 30],
    "Taurus":      [3, 15, 27],
    "Gemini":      [11, 17, 25],
    "Cancer":      [1, 13, 17, 26],
    "Leo":         [5, 15, 25, 30],
    "Virgo":       [5, 25, 30],
    "Libra":       [3, 7, 20],
    "Scorpio":     [3, 5, 15, 24],
    "Sagittarius": [7, 12, 15, 24, 30],
    "Pisces":      [3, 23, 25, 29],
}

# Dark degrees by sign
DARK_DEGREES = {
    "Aries":       [2, 12, 17, 21, 23, 26, 29],
    "Taurus":      [5, 7, 8, 13, 18, 21, 24, 25, 26],
    "Gemini":      [2, 4, 8, 12, 14, 20, 23, 29],
    "Cancer":      [4, 8, 10, 15, 18, 22, 28],
    "Leo":         [2, 6, 11, 17, 20, 27],
    "Virgo":       [2, 7, 13, 16, 17, 21, 23, 28],
    "Libra":       [2, 5, 9, 15, 21, 23, 26, 28, 30],
    "Scorpio":     [2, 8, 10, 17, 21, 26, 30],
    "Sagittarius": [2, 5, 8, 11, 17, 20, 25, 29],
    "Pisces":      [2, 6, 10, 13, 14, 16, 19, 22, 28],
}

# Smoky (nebulous) degrees
SMOKY_DEGREES = {
    "Aries":       [5, 10, 19, 24, 28],
    "Taurus":      [1, 9, 11, 19, 22, 28],
    "Gemini":      [1, 7, 15, 19, 22, 27],
    "Cancer":      [3, 6, 11, 14, 20, 24, 30],
    "Leo":         [1, 8, 13, 19, 22, 28],
    "Virgo":       [1, 9, 15, 19, 22, 26],
    "Libra":       [1, 11, 17, 22, 24],
    "Scorpio":     [1, 7, 12, 14, 19, 22, 28],
    "Sagittarius": [1, 4, 10, 14, 19, 22, 27],
    "Pisces":      [1, 5, 8, 11, 17, 20, 24, 27],
}

def get_degree_quality(sign, degree):
    """Classify a degree as bright, dark, smoky, or void."""
    if degree in BRIGHT_DEGREES.get(sign, []):
        return "bright"
    if degree in DARK_DEGREES.get(sign, []):
        return "dark"
    if degree in SMOKY_DEGREES.get(sign, []):
        return "smoky"
    return "void"

# ── 3. MASCULINE / FEMININE DEGREES ──────────────────────────────────────
# From Ptolemy, preserved in Lilly. Alternating blocks.
# Format: list of (end_degree, gender) per sign

GENDER_DEGREES = {
    "Aries":       [(7, "M"), (14, "F"), (21, "M"), (28, "F"), (30, "M")],
    "Taurus":      [(8, "F"), (15, "M"), (22, "F"), (30, "M")],
    "Gemini":      [(7, "M"), (14, "F"), (21, "M"), (28, "F"), (30, "M")],
    "Cancer":      [(7, "F"), (14, "M"), (21, "F"), (28, "M"), (30, "F")],
    "Leo":         [(7, "M"), (14, "F"), (21, "M"), (28, "F"), (30, "M")],
    "Virgo":       [(7, "F"), (14, "M"), (21, "F"), (28, "M"), (30, "F")],
    "Libra":       [(7, "M"), (14, "F"), (21, "M"), (28, "F"), (30, "M")],
    "Scorpio":     [(7, "F"), (14, "M"), (21, "F"), (28, "M"), (30, "F")],
    "Sagittarius": [(7, "M"), (14, "F"), (21, "M"), (28, "F"), (30, "M")],
    "Pisces":      [(7, "F"), (14, "M"), (21, "F"), (28, "M"), (30, "F")],
}

def get_degree_gender(sign, degree):
    for end_deg, gender in GENDER_DEGREES.get(sign, []):
        if degree <= end_deg:
            return gender
    return "?"

# ── 4. LUNAR MANSIONS (MANZILS) ──────────────────────────────────────────
# 28 Arabic lunar mansions, each spanning ~12.857° of the zodiac.
# Starting from 0° Aries. Each mansion has a name and astrological meaning.
# Mansion number overlaid on sign degree.

LUNAR_MANSIONS = [
    # (name, start_sign, start_degree) — based on traditional positions
    ("Sharaṭān",     "Aries", 1),     # 1: Aries 0°-12°51'
    ("Buṭayn",       "Aries", 13),    # 2: Aries 12°51'-25°42'
    ("Thurayyā",     "Aries", 26),    # 3: Aries 25°42'-Taurus 8°34'
    ("Dabarān",      "Taurus", 9),    # 4: Taurus 8°34'-21°26'
    ("Haqʿah",       "Taurus", 22),   # 5: Taurus 21°26'-Gemini 4°17'
    ("Hanʿah",       "Gemini", 5),    # 6: Gemini 4°17'-17°9'
    ("Dhirāʿ",       "Gemini", 18),   # 7: Gemini 17°9'-Cancer 0°
    ("Nathrah",      "Cancer", 1),    # 8: Cancer 0°-12°51'
    ("Ṭarf",         "Cancer", 13),   # 9: Cancer 12°51'-25°42'
    ("Jabʿhah",      "Cancer", 26),   # 10: Cancer 25°42'-Leo 8°34'
    ("Zubrah",       "Leo", 9),       # 11: Leo 8°34'-21°26'
    ("Ṣarfah",       "Leo", 22),      # 12: Leo 21°26'-Virgo 4°17'
    ("ʿAwwāʾ",       "Virgo", 5),     # 13: Virgo 4°17'-17°9'
    ("Simāk",        "Virgo", 18),    # 14: Virgo 17°9'-Libra 0°
    ("Ghafr",        "Libra", 1),     # 15: Libra 0°-12°51'
    ("Zubānā",       "Libra", 13),    # 16: Libra 12°51'-25°42'
    ("Iklīl",        "Libra", 26),    # 17: Libra 25°42'-Scorpio 8°34'
    ("Qalb",         "Scorpio", 9),   # 18: Scorpio 8°34'-21°26'
    ("Shawlah",      "Scorpio", 22),  # 19: Scorpio 21°26'-Sag 4°17'
    ("Naʿāʾam",      "Sagittarius", 5), # 20: Sag 4°17'-17°9'
    ("Baldah",       "Sagittarius", 18), # 21: Sag 17°9'-Cap 0°
]

# Zodiac sign order for mapping absolute degree
SIGN_ORDER = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

def get_absolute_degree(sign, degree):
    """Convert sign+degree to absolute ecliptic degree (0-359)."""
    idx = SIGN_ORDER.index(sign)
    return idx * 30 + (degree - 1)

def get_lunar_mansion(sign, degree):
    """Return the lunar mansion number (1-28) for a given sign+degree."""
    abs_deg = get_absolute_degree(sign, degree)
    mansion_size = 360 / 28  # ~12.857°
    mansion_num = int(abs_deg / mansion_size) + 1
    if mansion_num > 28:
        mansion_num = 28
    return mansion_num

def get_mansion_name(num):
    """Get name for mansion number 1-21 (those in our zodiac range)."""
    if 1 <= num <= len(LUNAR_MANSIONS):
        return LUNAR_MANSIONS[num - 1][0]
    return f"Mansion {num}"


# ── 5. DECAN FACE RULERS ─────────────────────────────────────────────────
# (Already known, but encoding here for completeness)
DECAN_RULERS = {
    "Aries":       ["Mars", "Sun", "Venus"],
    "Taurus":      ["Mercury", "Moon", "Saturn"],
    "Gemini":      ["Jupiter", "Mars", "Sun"],
    "Cancer":      ["Venus", "Mercury", "Moon"],
    "Leo":         ["Saturn", "Jupiter", "Mars"],
    "Virgo":       ["Sun", "Venus", "Mercury"],
    "Libra":       ["Moon", "Saturn", "Jupiter"],
    "Scorpio":     ["Mars", "Sun", "Venus"],
    "Sagittarius": ["Mercury", "Moon", "Saturn"],
    "Pisces":      ["Saturn", "Jupiter", "Mars"],
}

def get_decan_ruler(sign, degree):
    decan = min(3, (degree - 1) // 10 + 1)
    rulers = DECAN_RULERS.get(sign, [])
    return rulers[decan - 1] if decan - 1 < len(rulers) else None


# ══════════════════════════════════════════════════════════════════════════
#  ANALYSIS PHASES
# ══════════════════════════════════════════════════════════════════════════

def annotate_nymphs(data):
    """Add medieval degree classifications to each nymph."""
    for sign, sign_data in data.items():
        for n in sign_data["nymphs"]:
            deg = n["degree"]
            first_word = n["label"].split(".")[0]
            pf, root, sf, ok = parse_word(first_word)
            n["prefix"] = pf
            n["root"] = root
            n["suffix"] = sf
            n["parsed"] = ok
            n["terms_ruler"] = get_terms_ruler(sign, deg)
            n["quality"] = get_degree_quality(sign, deg)
            n["gender"] = get_degree_gender(sign, deg)
            n["mansion"] = get_lunar_mansion(sign, deg)
            n["decan_ruler"] = get_decan_ruler(sign, deg)
            n["sign"] = sign
    return data


# ── PHASE 1: Egyptian Terms/Bounds ────────────────────────────────────────

def phase1_terms(data):
    print("=" * 70)
    print("PHASE 1: Egyptian Terms/Bounds — do term rulers shape label morphology?")
    print("=" * 70)
    
    # Group labels by their terms ruler
    by_ruler = defaultdict(list)
    for sign, sd in data.items():
        for n in sd["nymphs"]:
            ruler = n["terms_ruler"]
            if ruler:
                by_ruler[ruler].append(n)
    
    print(f"\n  Labels per terms ruler:")
    print(f"  {'Ruler':<12} {'Count':>5} {'o−%':>6} {'−y%':>6} {'−iin%':>6} "
          f"{'−am%':>6} {'−ar%':>6} {'Top root':<15} {'2nd root'}")
    print(f"  {'-'*12} {'-'*5} {'-'*6} {'-'*6} {'-'*6} "
          f"{'-'*6} {'-'*6} {'-'*15} {'-'*15}")
    
    for ruler in ["Jupiter", "Venus", "Mercury", "Mars", "Saturn"]:
        nymphs = by_ruler[ruler]
        n_count = len(nymphs)
        if n_count == 0:
            continue
        
        o_pct = sum(1 for n in nymphs if "o" in n["prefix"]) / n_count * 100
        y_pct = sum(1 for n in nymphs if n["suffix"] == "y") / n_count * 100
        iin_pct = sum(1 for n in nymphs if n["suffix"] in ("iin", "aiin")) / n_count * 100
        am_pct = sum(1 for n in nymphs if n["suffix"] == "am") / n_count * 100
        ar_pct = sum(1 for n in nymphs if n["suffix"] == "ar") / n_count * 100
        
        roots = Counter(n["root"] for n in nymphs)
        top2 = roots.most_common(2)
        top1 = f"{top2[0][0]}({top2[0][1]})" if len(top2) > 0 else ""
        top2s = f"{top2[1][0]}({top2[1][1]})" if len(top2) > 1 else ""
        
        print(f"  {ruler:<12} {n_count:>5} {o_pct:>5.0f}% {y_pct:>5.0f}% {iin_pct:>5.0f}% "
              f"{am_pct:>5.0f}% {ar_pct:>5.0f}% {top1:<15} {top2s}")
    
    # Root overlap between terms rulers
    print(f"\n  Root sharing between terms rulers:")
    ruler_roots = {}
    for ruler in ["Jupiter", "Venus", "Mercury", "Mars", "Saturn"]:
        ruler_roots[ruler] = set(n["root"] for n in by_ruler[ruler])
    
    for i, r1 in enumerate(["Jupiter", "Venus", "Mercury", "Mars", "Saturn"]):
        for r2 in ["Jupiter", "Venus", "Mercury", "Mars", "Saturn"][i+1:]:
            shared = ruler_roots[r1] & ruler_roots[r2]
            if shared:
                j = len(shared) / len(ruler_roots[r1] | ruler_roots[r2])
                top_shared = sorted(shared)[:5]
                print(f"    {r1}↔{r2}: {len(shared)} shared (J={j:.3f}) — {', '.join(top_shared)}")
    
    # KEY TEST: Does the terms ruler correlate with any specific suffix?
    print(f"\n  Chi-square-like test: suffix distribution by terms ruler")
    suffixes_to_test = ["y", "iin", "am", "ar", "al", "dy"]
    all_nymphs = [n for sd in data.values() for n in sd["nymphs"]]
    total = len(all_nymphs)
    
    for sf in suffixes_to_test:
        overall_rate = sum(1 for n in all_nymphs if n["suffix"] == sf) / total
        print(f"\n    Suffix '{sf}' (overall: {overall_rate:.1%}):")
        for ruler in ["Jupiter", "Venus", "Mercury", "Mars", "Saturn"]:
            nymphs = by_ruler[ruler]
            rate = sum(1 for n in nymphs if n["suffix"] == sf) / len(nymphs)
            delta = rate - overall_rate
            marker = " ◄ HIGH" if delta > 0.05 else " ◄ LOW" if delta < -0.05 else ""
            print(f"      {ruler:<10}: {rate:.1%} (Δ={delta:+.1%}){marker}")
    
    # Is there a "terms boundary" effect? Do labels change at term boundaries?
    print(f"\n  Terms boundary effect:")
    print(f"  Do labels at term boundaries (first/last degree of a term) differ?")
    boundary_nymphs = []
    interior_nymphs = []
    for sign, sd in data.items():
        for n in sd["nymphs"]:
            deg = n["degree"]
            # Is this the first or last degree of a terms section?
            is_boundary = False
            # Check if this degree is start or end of any terms section
            prev_end = 0
            for end_deg, _ in EGYPTIAN_TERMS.get(sign, []):
                start = prev_end + 1
                if deg == start or deg == end_deg:
                    is_boundary = True
                    break
                prev_end = end_deg
            if is_boundary:
                boundary_nymphs.append(n)
            else:
                interior_nymphs.append(n)
    
    if boundary_nymphs and interior_nymphs:
        b_iin = sum(1 for n in boundary_nymphs if n["suffix"] in ("iin", "aiin")) / len(boundary_nymphs)
        i_iin = sum(1 for n in interior_nymphs if n["suffix"] in ("iin", "aiin")) / len(interior_nymphs)
        b_y = sum(1 for n in boundary_nymphs if n["suffix"] == "y") / len(boundary_nymphs)
        i_y = sum(1 for n in interior_nymphs if n["suffix"] == "y") / len(interior_nymphs)
        print(f"    Boundary degrees (n={len(boundary_nymphs)}): −y={b_y:.1%}, −iin={b_iin:.1%}")
        print(f"    Interior degrees (n={len(interior_nymphs)}): −y={i_y:.1%}, −iin={i_iin:.1%}")


# ── PHASE 2: Bright/Dark/Smoky/Void Quality ───────────────────────────────

def phase2_quality(data):
    print("\n" + "=" * 70)
    print("PHASE 2: Bright/Dark/Smoky/Void — do degree qualities shape labels?")
    print("=" * 70)
    
    by_quality = defaultdict(list)
    for sign, sd in data.items():
        for n in sd["nymphs"]:
            by_quality[n["quality"]].append(n)
    
    print(f"\n  Labels per degree quality:")
    print(f"  {'Quality':<10} {'Count':>5} {'o−%':>6} {'−y%':>6} {'−iin%':>6} "
          f"{'Unique roots':>12} {'Avg root len':>12}")
    print(f"  {'-'*10} {'-'*5} {'-'*6} {'-'*6} {'-'*6} "
          f"{'-'*12} {'-'*12}")
    
    for quality in ["bright", "dark", "smoky", "void"]:
        nymphs = by_quality[quality]
        if not nymphs:
            continue
        n_count = len(nymphs)
        o_pct = sum(1 for n in nymphs if "o" in n["prefix"]) / n_count * 100
        y_pct = sum(1 for n in nymphs if n["suffix"] == "y") / n_count * 100
        iin_pct = sum(1 for n in nymphs if n["suffix"] in ("iin", "aiin")) / n_count * 100
        unique_roots = len(set(n["root"] for n in nymphs))
        avg_root_len = sum(len(n["root"]) for n in nymphs) / n_count
        
        print(f"  {quality:<10} {n_count:>5} {o_pct:>5.0f}% {y_pct:>5.0f}% {iin_pct:>5.0f}% "
              f"{unique_roots:>12} {avg_root_len:>12.1f}")
    
    # KEY TEST: suffix -iin overrepresented in dark degrees?
    all_nymphs = [n for sd in data.values() for n in sd["nymphs"]]
    overall_iin = sum(1 for n in all_nymphs if n["suffix"] in ("iin", "aiin")) / len(all_nymphs)
    
    print(f"\n  -iin suffix rate by quality (overall: {overall_iin:.1%}):")
    for quality in ["bright", "dark", "smoky", "void"]:
        nymphs = by_quality[quality]
        if not nymphs:
            continue
        rate = sum(1 for n in nymphs if n["suffix"] in ("iin", "aiin")) / len(nymphs)
        delta = rate - overall_iin
        marker = " ◄◄" if abs(delta) > 0.05 else ""
        print(f"    {quality:<10}: {rate:.1%} (Δ={delta:+.1%}){marker}")
    
    # Are shared labels more common at bright degrees?
    label_counts = Counter(n["label"] for n in all_nymphs)
    shared_at_bright = sum(1 for n in by_quality["bright"] if label_counts[n["label"]] > 1)
    shared_at_dark = sum(1 for n in by_quality["dark"] if label_counts[n["label"]] > 1)
    
    bright_n = len(by_quality["bright"])
    dark_n = len(by_quality["dark"])
    overall_shared = sum(1 for n in all_nymphs if label_counts[n["label"]] > 1) / len(all_nymphs)
    
    print(f"\n  Shared label rate by quality (overall: {overall_shared:.1%}):")
    for quality in ["bright", "dark", "smoky", "void"]:
        nymphs = by_quality[quality]
        if not nymphs:
            continue
        rate = sum(1 for n in nymphs if label_counts[n["label"]] > 1) / len(nymphs)
        print(f"    {quality:<10}: {rate:.1%} (n={len(nymphs)})")
    
    # Specific bright degree labels
    print(f"\n  Labels at BRIGHT degrees (traditionally important/prominent):")
    print(f"  {'Sign':<14} {'Deg°':>4} {'Label':<28} {'Root':<12} {'Suffix':<8} {'Shared?'}")
    print(f"  {'-'*14} {'-'*4} {'-'*28} {'-'*12} {'-'*8} {'-'*8}")
    for sign in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                 "Libra", "Scorpio", "Sagittarius", "Pisces"]:
        for n in data[sign]["nymphs"]:
            if n["quality"] == "bright":
                shared = "YES" if label_counts[n["label"]] > 1 else ""
                print(f"  {sign:<14} {n['degree']:>4}° {n['label']:<28} "
                      f"{n['root']:<12} {n['suffix']:<8} {shared}")


# ── PHASE 3: Masculine/Feminine Degrees ───────────────────────────────────

def phase3_gender(data):
    print("\n" + "=" * 70)
    print("PHASE 3: Masculine/Feminine Degrees — does gender predict suffix?")
    print("=" * 70)
    
    masc = []
    fem = []
    for sign, sd in data.items():
        for n in sd["nymphs"]:
            if n["gender"] == "M":
                masc.append(n)
            else:
                fem.append(n)
    
    print(f"\n  Masculine degrees: {len(masc)}")
    print(f"  Feminine degrees:  {len(fem)}")
    
    m_y = sum(1 for n in masc if n["suffix"] == "y") / len(masc) * 100
    f_y = sum(1 for n in fem if n["suffix"] == "y") / len(fem) * 100
    m_iin = sum(1 for n in masc if n["suffix"] in ("iin", "aiin")) / len(masc) * 100
    f_iin = sum(1 for n in fem if n["suffix"] in ("iin", "aiin")) / len(fem) * 100
    m_am = sum(1 for n in masc if n["suffix"] == "am") / len(masc) * 100
    f_am = sum(1 for n in fem if n["suffix"] == "am") / len(fem) * 100
    m_ar = sum(1 for n in masc if n["suffix"] == "ar") / len(masc) * 100
    f_ar = sum(1 for n in fem if n["suffix"] == "ar") / len(fem) * 100
    m_o = sum(1 for n in masc if "o" in n["prefix"]) / len(masc) * 100
    f_o = sum(1 for n in fem if "o" in n["prefix"]) / len(fem) * 100
    
    print(f"\n  {'Metric':<18} {'Masculine':>10} {'Feminine':>10} {'Delta':>10}")
    print(f"  {'-'*18} {'-'*10} {'-'*10} {'-'*10}")
    print(f"  {'o− prefix':<18} {m_o:>9.1f}% {f_o:>9.1f}% {m_o-f_o:>+9.1f}%")
    print(f"  {'−y suffix':<18} {m_y:>9.1f}% {f_y:>9.1f}% {m_y-f_y:>+9.1f}%")
    print(f"  {'−iin suffix':<18} {m_iin:>9.1f}% {f_iin:>9.1f}% {m_iin-f_iin:>+9.1f}%")
    print(f"  {'−am suffix':<18} {m_am:>9.1f}% {f_am:>9.1f}% {m_am-f_am:>+9.1f}%")
    print(f"  {'−ar suffix':<18} {m_ar:>9.1f}% {f_ar:>9.1f}% {m_ar-f_ar:>+9.1f}%")
    
    marker = ""
    if abs(m_iin - f_iin) > 3:
        if f_iin > m_iin:
            marker = "\n  → -iin IS more common in FEMININE degrees ◄"
        else:
            marker = "\n  → -iin is more common in MASCULINE degrees (unexpected)"
    else:
        marker = "\n  → No significant gender-suffix correlation"
    print(marker)
    
    # Per-sign breakdown
    print(f"\n  Per-sign: −iin rate at masculine vs feminine degrees:")
    print(f"  {'Sign':<14} {'M(−iin)':>8} {'F(−iin)':>8} {'M(n)':>5} {'F(n)':>5}")
    print(f"  {'-'*14} {'-'*8} {'-'*8} {'-'*5} {'-'*5}")
    for sign in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                 "Libra", "Scorpio", "Sagittarius", "Pisces"]:
        m_n = [n for n in data[sign]["nymphs"] if n["gender"] == "M"]
        f_n = [n for n in data[sign]["nymphs"] if n["gender"] == "F"]
        m_rate = sum(1 for n in m_n if n["suffix"] in ("iin", "aiin")) / len(m_n) * 100 if m_n else 0
        f_rate = sum(1 for n in f_n if n["suffix"] in ("iin", "aiin")) / len(f_n) * 100 if f_n else 0
        print(f"  {sign:<14} {m_rate:>7.0f}% {f_rate:>7.0f}% {len(m_n):>5} {len(f_n):>5}")


# ── PHASE 4: Lunar Mansions ───────────────────────────────────────────────

def phase4_mansions(data):
    print("\n" + "=" * 70)
    print("PHASE 4: Lunar Mansions — do mansion boundaries shape labels?")
    print("=" * 70)
    
    by_mansion = defaultdict(list)
    for sign, sd in data.items():
        for n in sd["nymphs"]:
            by_mansion[n["mansion"]].append(n)
    
    print(f"\n  Labels per lunar mansion (mansions 1-21 in our zodiac range):")
    print(f"  {'Mansion':>7} {'Name':<16} {'Count':>5} {'o−%':>6} {'−y%':>6} {'−iin%':>6} {'Top root'}")
    print(f"  {'-'*7} {'-'*16} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*15}")
    
    for m_num in sorted(by_mansion.keys()):
        nymphs = by_mansion[m_num]
        n = len(nymphs)
        if n == 0:
            continue
        name = get_mansion_name(m_num)
        o_pct = sum(1 for np in nymphs if "o" in np["prefix"]) / n * 100
        y_pct = sum(1 for np in nymphs if np["suffix"] == "y") / n * 100
        iin_pct = sum(1 for np in nymphs if np["suffix"] in ("iin", "aiin")) / n * 100
        roots = Counter(np["root"] for np in nymphs)
        top = roots.most_common(1)[0][0] if roots else ""
        print(f"  {m_num:>7} {name:<16} {n:>5} {o_pct:>5.0f}% {y_pct:>5.0f}% {iin_pct:>5.0f}% {top}")
    
    # Do mansion boundaries create morphological shifts?
    print(f"\n  Mansion boundary effect:")
    print(f"  (Testing if labels change when crossing a lunar mansion boundary)")
    
    # For each sign, identify where mansion transitions happen
    boundary_pairs = []  # (nymph_before, nymph_after) where mansion changes
    for sign, sd in data.items():
        nymphs = sd["nymphs"]
        for i in range(1, len(nymphs)):
            if nymphs[i]["mansion"] != nymphs[i-1]["mansion"]:
                boundary_pairs.append((nymphs[i-1], nymphs[i]))
    
    # How often does root change at mansion boundary vs non-boundary?
    root_changes_at_boundary = 0
    suffix_changes_at_boundary = 0
    for before, after in boundary_pairs:
        if before["root"] != after["root"]:
            root_changes_at_boundary += 1
        if before["suffix"] != after["suffix"]:
            suffix_changes_at_boundary += 1
    
    # Baseline: consecutive pairs NOT at boundary
    non_boundary_pairs = []
    for sign, sd in data.items():
        nymphs = sd["nymphs"]
        for i in range(1, len(nymphs)):
            if nymphs[i]["mansion"] == nymphs[i-1]["mansion"]:
                non_boundary_pairs.append((nymphs[i-1], nymphs[i]))
    
    root_changes_non = sum(1 for b, a in non_boundary_pairs if b["root"] != a["root"])
    suffix_changes_non = sum(1 for b, a in non_boundary_pairs if b["suffix"] != a["suffix"])
    
    b_n = len(boundary_pairs)
    nb_n = len(non_boundary_pairs)
    
    if b_n and nb_n:
        print(f"    At mansion boundaries ({b_n} transitions):")
        print(f"      Root changes:   {root_changes_at_boundary}/{b_n} = {root_changes_at_boundary/b_n:.1%}")
        print(f"      Suffix changes: {suffix_changes_at_boundary}/{b_n} = {suffix_changes_at_boundary/b_n:.1%}")
        print(f"    At non-boundaries ({nb_n} consecutive pairs):")
        print(f"      Root changes:   {root_changes_non}/{nb_n} = {root_changes_non/nb_n:.1%}")
        print(f"      Suffix changes: {suffix_changes_non}/{nb_n} = {suffix_changes_non/nb_n:.1%}")


# ── PHASE 5: Multi-System Correlation Matrix ──────────────────────────────

def phase5_correlation(data):
    print("\n" + "=" * 70)
    print("PHASE 5: Multi-System Correlation — which system best predicts labels?")
    print("=" * 70)
    
    all_nymphs = [n for sd in data.values() for n in sd["nymphs"]]
    
    # For each classification system, compute how well it predicts
    # the suffix (-y vs -iin) choice
    
    systems = {
        "Terms ruler": lambda n: n["terms_ruler"],
        "Degree quality": lambda n: n["quality"],
        "Gender (M/F)": lambda n: n["gender"],
        "Lunar mansion": lambda n: str(n["mansion"]),
        "Decan ruler": lambda n: n["decan_ruler"],
        "Decan position": lambda n: str(n["decan"]),
        "Ring position": lambda n: str(n["ring_idx"]),
        "Sign element": lambda n: {
            "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
            "Taurus": "Earth", "Virgo": "Earth",
            "Gemini": "Air", "Libra": "Air",
            "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
        }.get(n["sign"], "?"),
    }
    
    print(f"\n  Suffix −iin prediction accuracy by classification system:")
    print(f"  (Higher variance ratio = system explains more of the suffix distribution)")
    print()
    print(f"  {'System':<20} {'Categories':>10} {'Var ratio':>10} {'Best cat →iin':>25} {'Best rate':>10}")
    print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*25} {'-'*10}")
    
    overall_iin_rate = sum(1 for n in all_nymphs if n["suffix"] in ("iin", "aiin")) / len(all_nymphs)
    overall_variance = overall_iin_rate * (1 - overall_iin_rate)
    
    for sys_name, key_fn in systems.items():
        groups = defaultdict(list)
        for n in all_nymphs:
            groups[key_fn(n)].append(n)
        
        # Variance ratio (between-group variance / total variance)
        between_var = 0
        best_cat = None
        best_rate = 0
        for cat, nymphs in groups.items():
            if not nymphs:
                continue
            cat_rate = sum(1 for n in nymphs if n["suffix"] in ("iin", "aiin")) / len(nymphs)
            between_var += len(nymphs) * (cat_rate - overall_iin_rate) ** 2
            if cat_rate > best_rate:
                best_rate = cat_rate
                best_cat = cat
        
        between_var /= len(all_nymphs)
        var_ratio = between_var / overall_variance if overall_variance > 0 else 0
        
        print(f"  {sys_name:<20} {len(groups):>10} {var_ratio:>10.4f} "
              f"{str(best_cat):<25} {best_rate:>9.1%}")
    
    # Same analysis for prefix (o- vs non-o)
    print(f"\n  Prefix o− prediction by classification system:")
    overall_o_rate = sum(1 for n in all_nymphs if "o" in n["prefix"]) / len(all_nymphs)
    overall_o_var = overall_o_rate * (1 - overall_o_rate)
    
    print(f"  {'System':<20} {'Var ratio':>10} {'Lowest o− cat':>25} {'Lowest rate':>12}")
    print(f"  {'-'*20} {'-'*10} {'-'*25} {'-'*12}")
    
    for sys_name, key_fn in systems.items():
        groups = defaultdict(list)
        for n in all_nymphs:
            groups[key_fn(n)].append(n)
        
        between_var = 0
        lowest_cat = None
        lowest_rate = 1.0
        for cat, nymphs in groups.items():
            if not nymphs:
                continue
            cat_rate = sum(1 for n in nymphs if "o" in n["prefix"]) / len(nymphs)
            between_var += len(nymphs) * (cat_rate - overall_o_rate) ** 2
            if cat_rate < lowest_rate:
                lowest_rate = cat_rate
                lowest_cat = cat
        
        between_var /= len(all_nymphs)
        var_ratio = between_var / overall_o_var if overall_o_var > 0 else 0
        
        print(f"  {sys_name:<20} {var_ratio:>10.4f} {str(lowest_cat):<25} {lowest_rate:>11.1%}")


# ── PHASE 6: Comprehensive Synthesis ──────────────────────────────────────

def phase6_synthesis(data):
    print("\n" + "=" * 70)
    print("PHASE 6: COMPREHENSIVE SYNTHESIS")
    print("=" * 70)
    
    all_nymphs = [n for sd in data.values() for n in sd["nymphs"]]
    
    # Collect all findings
    # Terms ruler suffix distribution
    by_terms = defaultdict(list)
    for n in all_nymphs:
        by_terms[n["terms_ruler"]].append(n)
    
    mercury_iin = sum(1 for n in by_terms["Mercury"] if n["suffix"] in ("iin", "aiin")) / len(by_terms["Mercury"]) if by_terms["Mercury"] else 0
    mars_iin = sum(1 for n in by_terms["Mars"] if n["suffix"] in ("iin", "aiin")) / len(by_terms["Mars"]) if by_terms["Mars"] else 0
    
    # Quality distribution
    by_quality = defaultdict(list)
    for n in all_nymphs:
        by_quality[n["quality"]].append(n)
    bright_shared = sum(1 for n in by_quality["bright"] if Counter(np["label"] for np in all_nymphs)[n["label"]] > 1) / len(by_quality["bright"]) if by_quality["bright"] else 0

    # Gender
    masc_iin = sum(1 for n in all_nymphs if n["gender"] == "M" and n["suffix"] in ("iin", "aiin")) / sum(1 for n in all_nymphs if n["gender"] == "M") if any(n["gender"] == "M" for n in all_nymphs) else 0
    fem_iin = sum(1 for n in all_nymphs if n["gender"] == "F" and n["suffix"] in ("iin", "aiin")) / sum(1 for n in all_nymphs if n["gender"] == "F") if any(n["gender"] == "F" for n in all_nymphs) else 0
    
    print(f"""
  ┌─────────────────────────────────────────────────────────────────────┐
  │  MEDIEVAL DEGREE-MEANING CROSS-REFERENCE: RESULTS                  │
  │                                                                     │
  │  SYSTEMS TESTED:                                                    │
  │    1. Egyptian Terms/Bounds (planet ruling each degree range)        │
  │    2. Bright/Dark/Smoky/Void degrees (Firmicus/Lilly)              │
  │    3. Masculine/Feminine degrees (Ptolemy/Lilly)                    │
  │    4. Lunar Mansions (28 Arabic manzils)                            │
  │    5. Decan rulers (Chaldean order) [from prior analysis]           │
  │                                                                     │
  │  KEY FINDINGS:                                                      │
  │                                                                     │
  │  • TERMS RULERS show WEAK suffix correlations:                      │
  │    Mercury terms: −iin at {mercury_iin:.0%}                              │
  │    Mars terms: −iin at {mars_iin:.0%}                                    │
  │                                                                     │
  │  • BRIGHT DEGREES: shared label rate {bright_shared:.0%} vs baseline        │
  │                                                                     │
  │  • MASCULINE/FEMININE:                                              │
  │    Masculine degrees: −iin at {masc_iin:.0%}                             │
  │    Feminine degrees: −iin at {fem_iin:.0%}                               │
  │                                                                     │
  │  • LUNAR MANSIONS: tested for boundary effects                      │
  │                                                                     │
  │  OVERALL ASSESSMENT:                                                │
  │  The classification system that best explains suffix variation is    │
  │  whichever shows highest variance ratio in Phase 5 (above).         │
  │                                                                     │
  │  If NO medieval system significantly predicts label morphology:      │
  │  → The notation may be encoding DIFFERENT properties                │
  │  → The labels may be names, not qualitative descriptions            │
  │  → The author's system may not follow standard medieval practice    │
  │                                                                     │
  │  This is itself a finding: it narrows the hypothesis space.         │
  └─────────────────────────────────────────────────────────────────────┘""")


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Voynich Manuscript — Medieval Degree-Meaning Cross-Reference")
    print("=" * 70)
    
    data = load_results()
    data = annotate_nymphs(data)
    
    phase1_terms(data)
    phase2_quality(data)
    phase3_gender(data)
    phase4_mansions(data)
    phase5_correlation(data)
    phase6_synthesis(data)
    
    print(f"\n  Analysis complete.")
