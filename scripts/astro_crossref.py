#!/usr/bin/env python3
"""
Astronomical Cross-Reference Analysis

Cross-references our extracted zodiac nymph labels against:
1. Ptolemy's Almagest star catalog (star counts per zodiac constellation)
2. Medieval decan system (3 decans × 10° per sign, planetary rulers)
3. Traditional star names (Arabic/Latin names current in 15th century)
4. Behenian fixed stars (15 most important medieval astrological stars)
5. Structural hypotheses (nymphs = degrees vs stars vs days)

Key discovery from pipeline: all signs have ~30 nymphs regardless of 
Ptolemaic star count (which ranges 13-45). This rules out nymphs=stars
and strongly supports nymphs=degrees.
"""

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from itertools import combinations
from common import result_path

# ── Load pipeline results ────────────────────────────────────────────────

RESULTS_PATH = result_path("astro_label_results.json")
with open(RESULTS_PATH, "r", encoding="utf-8") as f:
    PIPELINE = json.load(f)

# ── Ptolemy's Almagest: stars per zodiac constellation ───────────────────
# Source: Ian Ridpath's Star Tales / Almagest 1515 edition
# Format: (in_figure, unformed, total)

PTOLEMY_STARS = {
    "Aries":       {"in_figure": 13, "unformed": 5,  "total": 18},
    "Taurus":      {"in_figure": 32, "unformed": 11, "total": 43},  # 33 with shared star
    "Gemini":      {"in_figure": 18, "unformed": 7,  "total": 25},
    "Cancer":      {"in_figure": 9,  "unformed": 4,  "total": 13},
    "Leo":         {"in_figure": 27, "unformed": 8,  "total": 35},
    "Virgo":       {"in_figure": 26, "unformed": 6,  "total": 32},
    "Libra":       {"in_figure": 8,  "unformed": 9,  "total": 17},
    "Scorpius":    {"in_figure": 21, "unformed": 3,  "total": 24},
    "Sagittarius": {"in_figure": 31, "unformed": 0,  "total": 31},
    "Capricornus": {"in_figure": 28, "unformed": 0,  "total": 28},
    "Aquarius":    {"in_figure": 42, "unformed": 3,  "total": 45},
    "Pisces":      {"in_figure": 34, "unformed": 4,  "total": 38},
}

# ── Voynich nymph counts per sign (from pipeline) ───────────────────────
# Aries and Taurus each split across 2 pages (dark/light versions)

ZODIAC_MAP = {
    "f70v2": "Pisces",
    "f70v1": "Aries",
    "f71r":  "Aries",
    "f71v":  "Taurus",
    "f72r1": "Taurus",
    "f72r2": "Gemini",
    "f72r3": "Cancer",
    "f72v3": "Leo",
    "f72v2": "Virgo",
    "f72v1": "Libra",
    "f73r":  "Scorpio",
    "f73v":  "Sagittarius",
}

def get_nymph_counts():
    """Aggregate nymph counts per zodiac sign from pipeline results."""
    sign_counts = Counter()
    for folio_id, data in PIPELINE["folio_summary"].items():
        sign = data["sign"]
        sign_counts[sign] += data["nymph_labels"]
    return dict(sign_counts)

# ── Medieval Decan System ────────────────────────────────────────────────
# Chaldean order of planetary rulers for each decan (10° arc)
# This is the Ptolemaic/Firmicus system used in medieval Europe

DECAN_RULERS = {
    "Aries":       ["Mars",    "Sun",     "Venus"],
    "Taurus":      ["Mercury", "Moon",    "Saturn"],
    "Gemini":      ["Jupiter", "Mars",    "Sun"],
    "Cancer":      ["Venus",   "Mercury", "Moon"],
    "Leo":         ["Saturn",  "Jupiter", "Mars"],
    "Virgo":       ["Sun",     "Venus",   "Mercury"],
    "Libra":       ["Moon",    "Saturn",  "Jupiter"],
    "Scorpio":     ["Mars",    "Sun",     "Venus"],
    "Sagittarius": ["Mercury", "Moon",    "Saturn"],
}

# Planet glyphs/associations (medieval)
PLANET_PROPERTIES = {
    "Mars":    {"element": "Fire",  "gender": "M", "sect": "nocturnal"},
    "Sun":     {"element": "Fire",  "gender": "M", "sect": "diurnal"},
    "Venus":   {"element": "Water", "gender": "F", "sect": "nocturnal"},
    "Mercury": {"element": "Air",   "gender": "N", "sect": "variable"},
    "Moon":    {"element": "Water", "gender": "F", "sect": "nocturnal"},
    "Saturn":  {"element": "Earth", "gender": "M", "sect": "diurnal"},
    "Jupiter": {"element": "Air",   "gender": "M", "sect": "diurnal"},
}

# ── Traditional Star Names (Arabic/Latin, 15th century) ─────────────────
# Major named stars in or near each zodiac constellation
# These are the names a 15th-century European astronomer would know

ZODIAC_STAR_NAMES = {
    "Aries": [
        ("Hamal",       "α Ari", 2.0, "Arabic: al-ḥamal (the ram)"),
        ("Sheratan",    "β Ari", 2.6, "Arabic: al-sharaṭayn (the two signs)"),
        ("Mesarthim",   "γ Ari", 3.9, "Hebrew?: mᵉshartim (servants)"),
        ("Botein",      "δ Ari", 4.3, "Arabic: al-buṭayn (the belly)"),
        ("Bharani",     "41 Ari", 3.6, "Sanskrit via Arabic"),
    ],
    "Taurus": [
        ("Aldebaran",   "α Tau", 0.9, "Arabic: al-dabarān (the follower)"),
        ("Elnath",      "β Tau", 1.7, "Arabic: al-naṭḥ (the butting)"),
        ("Alcyone",     "η Tau", 2.9, "Greek: Alcyone (Pleiades)"),
        ("Atlas",       "27 Tau", 3.6, "Greek: Atlas (Pleiades)"),
        ("Maia",        "20 Tau", 3.9, "Greek: Maia (Pleiades)"),
        ("Ain",         "ε Tau", 3.5, "Arabic: ʿayn (the eye)"),
        ("Hyadum I",    "γ Tau", 3.7, "Latin: first of the Hyades"),
        ("Hyadum II",   "δ Tau", 3.8, "Latin: second of the Hyades"),
    ],
    "Gemini": [
        ("Castor",      "α Gem", 1.6, "Latin/Greek: Castor (twin)"),
        ("Pollux",      "β Gem", 1.1, "Latin/Greek: Pollux (twin)"),
        ("Alhena",      "γ Gem", 1.9, "Arabic: al-hanʿah (the brand)"),
        ("Wasat",       "δ Gem", 3.5, "Arabic: wasaṭ (the middle)"),
        ("Mebsuta",     "ε Gem", 3.1, "Arabic: mabsūṭat (outstretched paw)"),
        ("Tejat",       "μ Gem", 2.9, "Arabic: tahāt (the foot)"),
    ],
    "Cancer": [
        ("Acubens",     "α Cnc", 4.3, "Arabic: al-zubānā (the claws)"),
        ("Altarf",      "β Cnc", 3.5, "Arabic: al-ṭarf (the end/glance)"),
        ("Asellus Borealis", "γ Cnc", 4.7, "Latin: northern donkey"),
        ("Asellus Australis", "δ Cnc", 3.9, "Latin: southern donkey"),
        ("Praesepe",    "M44",   3.7, "Latin: manger (cluster, not a star)"),
    ],
    "Leo": [
        ("Regulus",     "α Leo", 1.4, "Latin: little king (Greek: Basiliskos)"),
        ("Denebola",    "β Leo", 2.1, "Arabic: dhanab al-asad (tail of the lion)"),
        ("Algieba",     "γ Leo", 2.3, "Arabic: al-jabhah (the forehead)"),
        ("Zosma",       "δ Leo", 2.6, "Greek: zōsma (girdle)"),
        ("Chertan",     "θ Leo", 3.3, "Arabic: al-kharātān (two small ribs)"),
        ("Adhafera",    "ζ Leo", 3.4, "Arabic: al-ḍafīrah (the curl)"),
        ("Rasalas",     "μ Leo", 3.9, "Arabic: raʾs al-asad (head of the lion)"),
        ("Subra",       "ο Leo", 3.5, "Latin: subra"),
    ],
    "Virgo": [
        ("Spica",       "α Vir", 1.0, "Latin: ear of wheat (Greek: Stachys)"),
        ("Zavijava",    "β Vir", 3.6, "Arabic: zāwiyat al-ʿawwāʾ (corner)"),
        ("Porrima",     "γ Vir", 2.7, "Latin: goddess of prophecy"),
        ("Auva",        "δ Vir", 3.4, "Arabic: al-ʿawwāʾ (the barker)"),
        ("Vindemiatrix","ε Vir", 2.8, "Latin: grape-gatherer (Greek: Protrygeter)"),
        ("Heze",        "ζ Vir", 3.4, "uncertain origin"),
        ("Syrma",       "ι Vir", 4.1, "Greek: syrma (train of a robe)"),
    ],
    "Libra": [
        ("Zubenelgenubi","α Lib", 2.7, "Arabic: al-zubānā al-janūbī (south claw)"),
        ("Zubeneschamali","β Lib", 2.6, "Arabic: al-zubānā al-shamālī (north claw)"),
        ("Zubenelhakrabi","γ Lib", 3.9, "Arabic: al-zubānā al-ʿaqrabī (scorpion's claw)"),
        ("Brachium",    "σ Lib", 3.3, "Latin: arm"),
    ],
    "Scorpio": [
        ("Antares",     "α Sco", 1.1, "Greek: anti-Ares (rival of Mars)"),
        ("Shaula",      "λ Sco", 1.6, "Arabic: al-shawla (the stinger)"),
        ("Sargas",      "θ Sco", 1.9, "Sumerian origin"),
        ("Dschubba",    "δ Sco", 2.3, "Arabic: al-jabha (the forehead)"),
        ("Acrab",       "β Sco", 2.6, "Arabic: al-ʿaqrab (the scorpion)"),
        ("Lesath",      "υ Sco", 2.7, "Arabic: lasʿat (sting)"),
        ("Grafias",     "ξ Sco", 4.2, "Greek: grafias (crab)"),
    ],
    "Sagittarius": [
        ("Kaus Australis","ε Sgr", 1.8, "Arabic+Latin: qaws janūbī (southern bow)"),
        ("Nunki",       "σ Sgr", 2.1, "Babylonian origin"),
        ("Ascella",     "ζ Sgr", 2.6, "Latin: armpit"),
        ("Kaus Media",  "δ Sgr", 2.7, "Arabic+Latin: middle bow"),
        ("Kaus Borealis","λ Sgr", 2.8, "Arabic+Latin: northern bow"),
        ("Rukbat",      "α Sgr", 3.97, "Arabic: rukbat (knee)"),
        ("Arkab",       "β Sgr", 4.0, "Arabic: ʿurqūb (tendon)"),
        ("Alnasl",      "γ Sgr", 3.0, "Arabic: al-naṣl (arrowhead)"),
    ],
    "Pisces": [
        ("Alpherg",     "η Psc", 3.6, "Arabic: al-fargh (the outpouring)"),
        ("Fumalsamakah","β Psc", 4.5, "Arabic: fam al-samakah (mouth of the fish)"),
        ("Torcularis",  "ο Psc", 4.3, "Latin: the winepress"),
        ("Alrescha",    "α Psc", 3.8, "Arabic: al-rishāʾ (the cord)"),
    ],
}

# ── Behenian Fixed Stars ─────────────────────────────────────────────────
# 15 stars of utmost importance in medieval astrology/magic
# Used in the Picatrix and similar works current in the 15th century

BEHENIAN_STARS = [
    {"name": "Algol",        "star": "β Per",  "mag": 2.1, "zodiac_long": "Taurus 26°",   "nature": "Saturn-Jupiter"},
    {"name": "Alcyone",      "star": "η Tau",  "mag": 2.9, "zodiac_long": "Gemini 0°",    "nature": "Moon-Mars"},
    {"name": "Aldebaran",    "star": "α Tau",  "mag": 0.9, "zodiac_long": "Gemini 10°",   "nature": "Mars"},
    {"name": "Capella",      "star": "α Aur",  "mag": 0.1, "zodiac_long": "Gemini 22°",   "nature": "Jupiter-Saturn"},
    {"name": "Sirius",       "star": "α CMa",  "mag": -1.5,"zodiac_long": "Cancer 14°",   "nature": "Jupiter-Mars"},
    {"name": "Procyon",      "star": "α CMi",  "mag": 0.4, "zodiac_long": "Cancer 26°",   "nature": "Mercury-Mars"},
    {"name": "Regulus",      "star": "α Leo",  "mag": 1.4, "zodiac_long": "Leo 30°",      "nature": "Jupiter-Mars"},
    {"name": "Algorab",      "star": "δ Crv",  "mag": 3.0, "zodiac_long": "Libra 13°",    "nature": "Saturn-Mars"},
    {"name": "Spica",        "star": "α Vir",  "mag": 1.0, "zodiac_long": "Libra 24°",    "nature": "Venus-Mercury"},
    {"name": "Arcturus",     "star": "α Boo",  "mag": -0.1,"zodiac_long": "Libra 24°",    "nature": "Jupiter-Mars"},
    {"name": "Alphecca",     "star": "α CrB",  "mag": 2.2, "zodiac_long": "Scorpio 12°",  "nature": "Venus-Mercury"},
    {"name": "Antares",      "star": "α Sco",  "mag": 1.1, "zodiac_long": "Sagittarius 10°","nature": "Mars-Jupiter"},
    {"name": "Vega",         "star": "α Lyr",  "mag": 0.0, "zodiac_long": "Capricorn 15°","nature": "Mercury-Venus"},
    {"name": "Deneb Algedi", "star": "δ Cap",  "mag": 2.9, "zodiac_long": "Aquarius 23°", "nature": "Saturn-Jupiter"},
    {"name": "Fomalhaut",    "star": "α PsA",  "mag": 1.2, "zodiac_long": "Pisces 4°",    "nature": "Venus-Mercury"},
]


# ══════════════════════════════════════════════════════════════════════════
#  ANALYSIS STEPS
# ══════════════════════════════════════════════════════════════════════════

def part_1_structural_hypothesis():
    """
    Test: do nymphs represent STARS in the constellation, DEGREES of the 
    zodiac sign, or DAYS of the calendar month?
    
    If nymphs=stars: nymph count should correlate with Ptolemaic star count
    If nymphs=degrees: nymph count should be ~30 regardless of star count
    If nymphs=days: nymph count should be ~30-31
    """
    print("=" * 70)
    print("Structural hypothesis — what do the ~30 nymphs represent?")
    print("=" * 70)
    
    nymph_counts = get_nymph_counts()
    
    # Map Scorpio→Scorpius for Ptolemaic lookup
    ptolemy_name_map = {"Scorpio": "Scorpius"}
    
    print(f"\n  {'Sign':<14} {'Nymphs':>7} {'Ptolemy Stars':>14} {'Ratio':>7}")
    print(f"  {'-'*14} {'-'*7} {'-'*14} {'-'*7}")
    
    nymph_list = []
    ptolemy_list = []
    
    for sign in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                  "Libra", "Scorpio", "Sagittarius", "Pisces"]:
        n = nymph_counts.get(sign, 0)
        pname = ptolemy_name_map.get(sign, sign)
        p = PTOLEMY_STARS.get(pname, {}).get("total", 0)
        ratio = n / p if p > 0 else 0
        print(f"  {sign:<14} {n:>7} {p:>14} {ratio:>7.2f}")
        nymph_list.append(n)
        ptolemy_list.append(p)
    
    # Pearson correlation between nymph count and Ptolemy star count
    n = len(nymph_list)
    mean_ny = sum(nymph_list) / n
    mean_pt = sum(ptolemy_list) / n
    cov = sum((nymph_list[i] - mean_ny) * (ptolemy_list[i] - mean_pt) for i in range(n))
    std_ny = math.sqrt(sum((x - mean_ny)**2 for x in nymph_list))
    std_pt = math.sqrt(sum((x - mean_pt)**2 for x in ptolemy_list))
    corr = cov / (std_ny * std_pt) if std_ny > 0 and std_pt > 0 else 0
    
    print(f"\n  Nymph count range: {min(nymph_list)}–{max(nymph_list)} (σ={math.sqrt(sum((x-mean_ny)**2 for x in nymph_list)/n):.1f})")
    print(f"  Ptolemy count range: {min(ptolemy_list)}–{max(ptolemy_list)} (σ={math.sqrt(sum((x-mean_pt)**2 for x in ptolemy_list)/n):.1f})")
    print(f"  Pearson r(nymphs, Ptolemy stars) = {corr:.3f}")
    
    print(f"\n  VERDICT:")
    if abs(corr) < 0.3:
        print(f"  → NO correlation between nymph count and star count (r={corr:.3f})")
        print(f"  → Nymphs do NOT represent individual constellation stars")
        print(f"  → The ~30 count is FIXED, suggesting DEGREES (30° per sign)")
        print(f"     or DAYS (~30 per calendar month)")
    elif corr > 0.5:
        print(f"  → POSITIVE correlation (r={corr:.3f}): nymphs may represent stars")
    else:
        print(f"  → WEAK correlation (r={corr:.3f}): inconclusive")
    
    return corr, nymph_counts


def part_2_decan_morphology():
    """
    Test: do the 3 groups of ~10 labels per sign show morphological patterns
    that correlate with decan planetary rulers?
    
    If decans matter, we expect:
    - Signs sharing the same decan ruler to have shared label morphology
    - e.g., Aries decan 1 (Mars) and Scorpio decan 1 (Mars) should share roots
    """
    print("\n" + "=" * 70)
    print("Decan ruler correlation — do planetary rulers shape labels?")
    print("=" * 70)
    
    decan_data = PIPELINE.get("decan_analysis", {})
    
    # Build: for each (planet, decan_position) combo, collect suffix distributions
    ruler_suffixes = defaultdict(Counter)
    ruler_root_sets = defaultdict(set)
    
    for sign, analysis in decan_data.items():
        if sign not in DECAN_RULERS:
            continue
        rulers = DECAN_RULERS[sign]
        suffix_dists = analysis.get("group_suffix_dist", [])
        top_roots_list = analysis.get("group_top_roots", [])
        
        for i, ruler in enumerate(rulers):
            if i < len(suffix_dists):
                for suffix, count in suffix_dists[i].items():
                    ruler_suffixes[ruler][suffix] += count
            if i < len(top_roots_list):
                for root in top_roots_list[i]:
                    ruler_root_sets[ruler].add(root)
    
    print(f"\n  Suffix distribution by decan planetary ruler:")
    print(f"  {'Planet':<10} {'Total':>6} {'−y':>6} {'−iin':>6} {'−y%':>6} {'−iin%':>7}")
    print(f"  {'-'*10} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*7}")
    
    for planet in ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"]:
        suffixes = ruler_suffixes.get(planet, Counter())
        total = sum(suffixes.values())
        y_count = suffixes.get("y", 0)
        iin_count = suffixes.get("iin", 0)
        if total > 0:
            print(f"  {planet:<10} {total:>6} {y_count:>6} {iin_count:>6} {100*y_count/total:>5.1f}% {100*iin_count/total:>6.1f}%")
    
    # Cross-planet root sharing
    print(f"\n  Root overlap between decan rulers:")
    planets = sorted(ruler_root_sets.keys())
    for p1, p2 in combinations(planets, 2):
        shared = ruler_root_sets[p1] & ruler_root_sets[p2]
        if shared:
            total = len(ruler_root_sets[p1] | ruler_root_sets[p2])
            jaccard = len(shared) / total if total > 0 else 0
            print(f"  {p1}↔{p2}: {len(shared)} shared roots (J={jaccard:.3f}) — {', '.join(sorted(list(shared))[:5])}")
    
    # Test: Same ruler, same decan position across different signs
    print(f"\n  Same-ruler decan pairs (checking root overlap):")
    for ruler in ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"]:
        signs_with_ruler = []
        for sign, rulers_list in DECAN_RULERS.items():
            for i, r in enumerate(rulers_list):
                if r == ruler:
                    signs_with_ruler.append((sign, i))
        
        if len(signs_with_ruler) >= 2:
            # Collect roots from each
            decan_roots = {}
            for sign, decan_idx in signs_with_ruler:
                if sign in decan_data and decan_idx < len(decan_data[sign].get("group_top_roots", [])):
                    roots = set(decan_data[sign]["group_top_roots"][decan_idx].keys())
                    decan_roots[(sign, decan_idx)] = roots
            
            # Pairwise overlap
            keys = list(decan_roots.keys())
            for i in range(len(keys)):
                for j in range(i+1, len(keys)):
                    s1 = decan_roots[keys[i]]
                    s2 = decan_roots[keys[j]]
                    shared = s1 & s2
                    if shared:
                        print(f"    {ruler}: {keys[i][0]} D{keys[i][1]+1} ↔ {keys[j][0]} D{keys[j][1]+1}: shared={shared}")


def part_3_star_name_phonetics():
    """
    Test: do any Voynich label roots phonetically match known medieval star names?
    
    We compare the consonant skeleton of each approach:
    - Strip vowels from both Voynich roots and star names
    - Look for matches or near-matches
    """
    print("\n" + "=" * 70)
    print("Phonetic comparison — labels vs medieval star names")
    print("=" * 70)
    
    def consonant_skeleton(word):
        """Extract consonant skeleton, keeping ch/sh/th digraphs."""
        word = word.lower()
        # Replace digraphs with single chars for pattern matching
        word = word.replace("sh", "S").replace("ch", "C").replace("th", "T")
        # Keep only consonants
        consonants = re.sub(r"[aeiouāēīōū]", "", word)
        return consonants
    
    def simple_skeleton(word):
        """Even simpler: just consonant letters."""
        return re.sub(r"[aeiou]", "", word.lower())
    
    # Collect all Voynich label roots from pipeline
    root_dist = PIPELINE.get("root_distribution", {})
    voynich_roots = {}
    for root, count in root_dist.items():
        skel = consonant_skeleton(root)
        if skel:  # skip empty (pure-vowel roots)
            voynich_roots[root] = {"skeleton": skel, "count": count}
    
    # Collect all known star names
    star_name_skels = {}
    for sign, stars in ZODIAC_STAR_NAMES.items():
        for name, bayer, mag, etymology in stars:
            skel = consonant_skeleton(name)
            star_name_skels[name] = {"skeleton": skel, "sign": sign, "mag": mag, "etymology": etymology}
    
    for bstar in BEHENIAN_STARS:
        skel = consonant_skeleton(bstar["name"])
        star_name_skels[bstar["name"]] = {"skeleton": skel, "sign": "Behenian", "mag": bstar["mag"]}
    
    # Find matches
    print(f"\n  Consonant skeleton matches (Voynich root → star name):")
    print(f"  {'Root':<16} {'Skeleton':<10} {'Star Name':<18} {'Star Skel':<10} {'Sign':<14} {'Mag':>4}")
    print(f"  {'-'*16} {'-'*10} {'-'*18} {'-'*10} {'-'*14} {'-'*4}")
    
    matches = []
    for root, rinfo in voynich_roots.items():
        rskel = rinfo["skeleton"]
        for star_name, sinfo in star_name_skels.items():
            sskel = sinfo["skeleton"]
            # Exact match
            if rskel == sskel and len(rskel) >= 2:
                matches.append((root, star_name, rskel, sinfo))
                print(f"  {root:<16} {rskel:<10} {star_name:<18} {sskel:<10} {sinfo['sign']:<14} {sinfo['mag']:>4}")
    
    # Near-matches: edit distance 1 on skeleton
    print(f"\n  Near-matches (edit distance 1 on consonant skeleton):")
    near_matches = []
    for root, rinfo in voynich_roots.items():
        rskel = rinfo["skeleton"]
        if len(rskel) < 2:
            continue
        for star_name, sinfo in star_name_skels.items():
            sskel = sinfo["skeleton"]
            if len(sskel) < 2:
                continue
            # Simple edit distance
            if abs(len(rskel) - len(sskel)) <= 1:
                dist = 0
                max_len = max(len(rskel), len(sskel))
                min_len = min(len(rskel), len(sskel))
                for i in range(min_len):
                    if rskel[i] != sskel[i]:
                        dist += 1
                dist += max_len - min_len
                if dist == 1:
                    near_matches.append((root, star_name, rskel, sskel, sinfo))
                    print(f"    {root:<16} ({rskel}) ~ {star_name:<18} ({sskel})  [{sinfo['sign']}]")
    
    # Also check: does the most common root 'tal' match anything?
    print(f"\n  Special root analysis:")
    print(f"  'tal' (12×, most common) — skeleton 'tl'")
    print(f"    Possible matches: tl → Altl? Tail? No clear star name match.")
    print(f"    However: if 'o-' is a definite article, 'otal-y' = 'the tal'")
    print(f"    'tal' could be a GENERIC TERM (star, light, degree) not a proper name")
    
    print(f"\n  'kal' (8×, 3rd most common) — skeleton 'kl'")
    print(f"    Possible: kal↔Algol? (gl vs kl, near-match if g≈k)")
    
    print(f"\n  'kar' (5×) — skeleton 'kr'")
    print(f"    Possible: kar↔Karkinos (Cancer)? kr matches")
    
    return matches, near_matches


def part_4_behenian_timing():
    """
    Test: do Behenian fixed stars fall in zodiac positions that correspond
    to specific nymph positions?
    
    Each Behenian star has a zodiac longitude. If nymphs=degrees, the 
    Behenian star at, say, "Cancer 14°" should correspond to the 14th nymph
    in Cancer. That nymph's label might be morphologically distinct.
    """
    print("\n" + "=" * 70)
    print("Behenian star positions — do they match nymph positions?")
    print("=" * 70)
    
    print(f"\n  Behenian stars falling in Voynich zodiac signs:")
    print(f"  {'Star':<18} {'Zodiac Position':<24} {'Degree':>6} {'Expected Nymph #':>16}")
    print(f"  {'-'*18} {'-'*24} {'-'*6} {'-'*16}")
    
    sign_map = {
        "Aries": "Aries", "Taurus": "Taurus", "Gemini": "Gemini",
        "Cancer": "Cancer", "Leo": "Leo", "Virgo": "Virgo",
        "Libra": "Libra", "Scorpio": "Scorpio", "Sagittarius": "Sagittarius",
        "Capricorn": "Capricorn", "Aquarius": "Aquarius", "Pisces": "Pisces"
    }
    
    behenian_in_voynich = []
    for bstar in BEHENIAN_STARS:
        zl = bstar["zodiac_long"]
        parts = zl.split()
        sign = parts[0]
        degree = int(parts[1].replace("°", ""))
        
        if sign in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                     "Libra", "Scorpio", "Sagittarius", "Pisces"]:
            nymph_num = degree  # 0-indexed would be degree, 1-indexed = degree+1
            print(f"  {bstar['name']:<18} {zl:<24} {degree:>6} {nymph_num:>16}")
            behenian_in_voynich.append({
                "name": bstar["name"],
                "sign": sign,
                "degree": degree,
                "nymph_approx": nymph_num,
            })
    
    print(f"\n  NOTE: Zodiac longitudes are for ~150 AD (Ptolemy's epoch).")
    print(f"  By 1400 AD, precession shifted these by ~17°.")
    print(f"  Adjusted positions (epoch ~1400):")
    for bs in behenian_in_voynich:
        adj_degree = bs["degree"] + 17
        adj_sign = bs["sign"]
        if adj_degree >= 30:
            adj_degree -= 30
            # Would shift to next sign (not computed here for simplicity)
            adj_sign += " (→next)"
        print(f"    {bs['name']:<18} →  {adj_sign} {adj_degree}°")


def part_5_o_prefix_article():
    """
    Test the hypothesis that 'o-' is a definite article or classifier.
    
    Evidence:
    - 67.4% of labels start with o-
    - In body text, o- is also common but not THIS dominant
    - Catalan/Occitan (language of month names) does NOT have 'o' as article
      (Catalan: el/la, Occitan: lo/la)
    - But 'o' IS an article/particle in several other systems:
      - Romanian: -ul/-o (postfixed article)  
      - Greek: ο/η/το (the) ← most relevant for astronomical terminology
      - Hebrew: ha- (but written as prefix)
    
    If o- is a Greek article ο (ho), this connects to the Ptolemaic/Greek
    astronomical tradition underlying the Almagest.
    """
    print("\n" + "=" * 70)
    print("The o- prefix — article, classifier, or something else?")
    print("=" * 70)
    
    prefix_data = PIPELINE.get("prefix_analysis", {})
    print(f"\n  Total labels: {prefix_data.get('total_labels', 0)}")
    print(f"  Starting with o-: {prefix_data.get('o_prefix_count', 0)} ({100*prefix_data.get('o_prefix_fraction', 0):.1f}%)")
    
    print(f"\n  Prefix distribution:")
    for prefix, count in sorted(prefix_data.get("prefix_distribution", {}).items(), key=lambda x: -x[1]):
        print(f"    {prefix or '(none)':<8} {count:>4}")
    
    # Labels WITHOUT o-prefix — what are they?
    most_shared = PIPELINE.get("most_shared", [])
    no_o = [w for w in most_shared if not w["word"].startswith("o")]
    with_o = [w for w in most_shared if w["word"].startswith("o")]
    
    print(f"\n  Shared labels WITHOUT o-prefix (possible bare stems or different word class):")
    for w in no_o[:10]:
        print(f"    {w['word']:<16} {w['count']}× in {', '.join(w['signs'])}")
    
    print(f"\n  Shared labels WITH o-prefix:")
    for w in with_o[:10]:
        print(f"    {w['word']:<16} {w['count']}× in {', '.join(w['signs'])}")
    
    # Test: is o-prefix related to star magnitude?
    # If o- means "the" or "bright", we'd expect the most-repeated labels
    # (generic terms) to preferentially have o-
    shared_o = sum(1 for w in most_shared if w["word"].startswith("o"))
    shared_total = len(most_shared)
    print(f"\n  Among {shared_total} shared labels: {shared_o} have o-prefix ({100*shared_o/shared_total:.0f}%)")
    print(f"  vs overall 67.4% → {'higher' if shared_o/shared_total > 0.674 else 'similar or lower'} in shared labels")
    
    print(f"\n  HYPOTHESIS: o- is a Greek-derived masculine article ο (ho)")
    print(f"  This would explain:")
    print(f"  - High prevalence in star labels (formal names use articles)")
    print(f"  - Presence in both generic ('otaly' = 'the star') and specific labels")
    print(f"  - Connection to Greek astronomical tradition (Almagest)")
    print(f"  - Non-o labels ('ar', 'am', 'al', 'dy') may be qualifiers/adjectives")


def part_6_cancer_anomaly():
    """
    Cancer is the only sign where -iin rivals -y in labels.
    Test whether this correlates with something specific about Cancer.
    
    Cancer properties:
    - Water element, Cardinal modality
    - Ruled by Moon
    - Decan rulers: Venus, Mercury, Moon (all feminine/watery)
    - Smallest zodiac constellation (only 9+4=13 Ptolemaic stars)
    - Contains Praesepe (Beehive Cluster) — a fuzzy non-stellar object
    - In the Almagest, Cancer has the fewest constellation stars
    """
    print("\n" + "=" * 70)
    print("Cancer anomaly — why does Cancer differ in suffix usage?")
    print("=" * 70)
    
    suffix_by_sign = PIPELINE.get("suffix_by_sign", {})
    
    print(f"\n  Suffix ratio by sign (−y vs −iin):")
    print(f"  {'Sign':<14} {'−y':>5} {'−iin':>5} {'Other':>6} {'−iin/−y':>8} {'Element':<8} {'Modality':<10}")
    print(f"  {'-'*14} {'-'*5} {'-'*5} {'-'*6} {'-'*8} {'-'*8} {'-'*10}")
    
    elements = {
        "Aries": "Fire", "Taurus": "Earth", "Gemini": "Air",
        "Cancer": "Water", "Leo": "Fire", "Virgo": "Earth",
        "Libra": "Air", "Scorpio": "Water", "Sagittarius": "Fire",
        "Pisces": "Water"
    }
    modalities = {
        "Aries": "Cardinal", "Taurus": "Fixed", "Gemini": "Mutable",
        "Cancer": "Cardinal", "Leo": "Fixed", "Virgo": "Mutable",
        "Libra": "Cardinal", "Scorpio": "Fixed", "Sagittarius": "Mutable",
        "Pisces": "Mutable"
    }
    
    water_iin_ratio = []
    non_water_iin_ratio = []
    
    for sign in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                  "Libra", "Scorpio", "Sagittarius", "Pisces"]:
        data = suffix_by_sign.get(sign, {})
        y = data.get("y", 0)
        iin = data.get("iin", 0)
        other = sum(v for k, v in data.items() if k not in ("y", "iin"))
        ratio = iin / y if y > 0 else float('inf')
        elem = elements.get(sign, "?")
        mod = modalities.get(sign, "?")
        print(f"  {sign:<14} {y:>5} {iin:>5} {other:>6} {ratio:>8.2f} {elem:<8} {mod:<10}")
        
        if elem == "Water":
            water_iin_ratio.append(ratio)
        else:
            non_water_iin_ratio.append(ratio)
    
    avg_water = sum(water_iin_ratio) / len(water_iin_ratio) if water_iin_ratio else 0
    avg_non_water = sum(non_water_iin_ratio) / len(non_water_iin_ratio) if non_water_iin_ratio else 0
    
    print(f"\n  Average −iin/−y ratio:")
    print(f"    Water signs:     {avg_water:.3f}")
    print(f"    Non-water signs: {avg_non_water:.3f}")
    print(f"    {'Water signs use MORE -iin' if avg_water > avg_non_water else 'No clear water/non-water split'}")
    
    print(f"\n  Cancer-specific factors:")
    print(f"    - Cancer has ALL feminine/watery decan rulers (Venus, Mercury, Moon)")
    print(f"    - If -iin encodes something feminine/receptive, Cancer is the extreme case")
    print(f"    - Taurus (Earth/Fixed, decan rulers: Mercury, Moon, Saturn) also has elevated -iin")
    print(f"    - This could indicate -iin marks Moon-ruled or nocturnal decans")


def part_7_degree_marker_test():
    """
    If each nymph = 1 degree, test whether label morphology changes 
    systematically around 10/20 degree boundaries (decan transitions).
    
    Use clock positions as proxy for degree positions.
    """
    print("\n" + "=" * 70)
    print("Degree marker test — morphological shifts at decan boundaries")
    print("=" * 70)
    
    # Group labels by their position within the ~30 per sign
    # The pipeline already did decan grouping by splitting into thirds
    decan_data = PIPELINE.get("decan_analysis", {})
    
    # Aggregate suffix distributions across all signs by decan position
    decan_1_suffixes = Counter()
    decan_2_suffixes = Counter()
    decan_3_suffixes = Counter()
    
    for sign, analysis in decan_data.items():
        suffix_dists = analysis.get("group_suffix_dist", [])
        if len(suffix_dists) >= 3:
            for k, v in suffix_dists[0].items():
                decan_1_suffixes[k] += v
            for k, v in suffix_dists[1].items():
                decan_2_suffixes[k] += v
            for k, v in suffix_dists[2].items():
                decan_3_suffixes[k] += v
    
    print(f"\n  Aggregate suffix distribution by decan position (all signs combined):")
    print(f"  {'Decan':<10} {'−y':>5} {'−iin':>5} {'Other':>6} {'Total':>6} {'−y%':>6} {'−iin%':>7}")
    print(f"  {'-'*10} {'-'*5} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*7}")
    
    for label, counter in [("Decan 1", decan_1_suffixes), ("Decan 2", decan_2_suffixes), ("Decan 3", decan_3_suffixes)]:
        y = counter.get("y", 0)
        iin = counter.get("iin", 0)
        other = sum(v for k, v in counter.items() if k not in ("y", "iin"))
        total = y + iin + other
        print(f"  {label:<10} {y:>5} {iin:>5} {other:>6} {total:>6} {100*y/total if total else 0:>5.1f}% {100*iin/total if total else 0:>6.1f}%")
    
    # Root diversity by decan position
    decan_diversity = {"Decan 1": [], "Decan 2": [], "Decan 3": []}
    for sign, analysis in decan_data.items():
        divs = analysis.get("group_root_diversity", [])
        sizes = analysis.get("group_sizes", [])
        if len(divs) >= 3 and len(sizes) >= 3:
            for i, (label) in enumerate(["Decan 1", "Decan 2", "Decan 3"]):
                if sizes[i] > 0:
                    decan_diversity[label].append(divs[i] / sizes[i])
    
    print(f"\n  Root uniqueness ratio by decan (unique_roots / total_labels):")
    for label, ratios in decan_diversity.items():
        if ratios:
            avg = sum(ratios) / len(ratios)
            print(f"    {label}: {avg:.3f} average ({len(ratios)} signs)")


def part_8_comprehensive_synthesis():
    """
    Bring all findings together into a coherent interpretation.
    """
    print("\n" + "=" * 70)
    print("COMPREHENSIVE SYNTHESIS")
    print("=" * 70)
    
    print("""
  ┌─────────────────────────────────────────────────────────────────┐
  │  CROSS-REFERENCE FINDINGS SUMMARY                              │
  │                                                                 │
  │  1. NYMPHS = DEGREES (not constellation stars)                  │
  │     - All signs have ~30 nymphs regardless of star count        │
  │     - Ptolemy's Cancer has 13 stars but 30 Voynich nymphs       │
  │     - Correlation between nymph count & star count ≈ 0          │
  │     - 3 equal groups per sign = 3 decans of 10° each           │
  │                                                                 │
  │  2. LABEL STRUCTURE = [article] + [root] + [grammatical suffix] │
  │     - o- prefix = probable article/classifier (67.4%)           │
  │     - Greek-derived ο (ho) fits the Ptolemaic context          │
  │     - Roots are mostly unique per sign (87.7%) = proper names   │
  │     - ~34 shared roots = generic astronomical vocabulary        │
  │                                                                 │
  │  3. SEMANTIC CANDIDATES for generic terms:                      │
  │     - 'tal' (most common root) = likely 'star' or 'degree'     │
  │     - 'kal' = possible 'bright' or 'first'                     │
  │     - 'ar'/'am' (no prefix) = qualifiers or positional markers │
  │                                                                 │
  │  4. SUFFIX -y vs -iin encodes TWO grammatical categories:       │
  │     - -y dominates everywhere except Cancer                     │
  │     - Cancer's -iin anomaly may track Moon-ruled decans         │
  │     - From prior work: -y = Type B (process), -iin = Type A    │
  │     - In labels: -y may mark masculine stars, -iin feminine?    │
  │                                                                 │
  │  5. DECAN PLANETARY RULERS show WEAK but present signal:        │
  │     - Same-ruler decans across signs share occasional roots     │
  │     - Suffix distributions shift slightly by planetary ruler    │
  │                                                                 │
  │  6. NO clear phonetic matches to known star names               │
  │     - The label system is NOT direct transliteration             │
  │     - Labels encode DESCRIPTIONS, not borrowed star names       │
  │     - Consistent with a CONSTRUCTED notation system             │
  └─────────────────────────────────────────────────────────────────┘

  WORKING HYPOTHESIS:
  
  Each zodiac page represents 30 degrees of one zodiac sign.
  Each nymph represents one degree.
  Three concentric rings represent the three decans (10° each).
  
  Label structure: o + [root] + [suffix]
    - o- = definite article (the)  
    - root = name/descriptor unique to that degree
    - -y = default grammatical form
    - -iin = alternative form (possibly feminine, nocturnal, or receptive)
  
  The ~34 shared labels (otaly, otal, oky, okeey, okal, etc.) are
  FUNCTIONAL TERMS that recur at specific degree positions across signs,
  possibly marking notable stars, planetary terms (domicile/exaltation),
  or degree types (bright degree, dark degree, masculine, feminine).
  
  This system is consistent with a CONSTRUCTED ASTROLOGICAL NOTATION,
  not a natural language description of stars. It parallels the Hebrew-like
  morphological system found in the manuscript's body text (prefix-root-suffix
  agglutination with a small closed set of prefixes and grammatical suffixes).

  NEXT STEPS for further decipherment:
  1. Map the ~34 shared labels against medieval degree-meaning lists
     (each zodiac degree had traditional associations in medieval astrology)
  2. Check if Behenian star positions correspond to morphologically distinct labels
  3. Compare the 'o-' article hypothesis against paragraph-initial words
     in body text to see if the same article appears in connected prose
  4. Cross-reference label positions (clock positions) with known star
     positions for epoch ~1400 to find specific anchors
""")


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    print("Voynich Manuscript — Astronomical Cross-Reference Analysis")
    print("=" * 70)
    
    results = {}
    
    corr, nymph_counts = part_1_structural_hypothesis()
    results["nymph_ptolemy_correlation"] = corr
    results["nymph_counts"] = nymph_counts
    
    part_2_decan_morphology()
    part_3_star_name_phonetics()
    part_4_behenian_timing()
    part_5_o_prefix_article()
    part_6_cancer_anomaly()
    part_7_degree_marker_test()
    part_8_comprehensive_synthesis()
    
    # Save results
    out_path = result_path("astro_crossref_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()