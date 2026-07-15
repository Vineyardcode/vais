#!/usr/bin/env python3
"""
Voynich Manuscript — Astronomical Label-Illustration Extraction Pipeline

Extracts all labels from zodiac/astronomical folios, cross-references them
with known anchors (zodiac signs, month names in Latin script, star positions),
and applies our morphological parser to discover semantic patterns.

Known zodiac-month anchors (Latin-script month names found on folios):
  f70v2 = Pisces    = March    ("Marc")
  f70v1 = Aries(D)  = April    ("Aberil")
  f71r  = Aries(L)  = April    ("Aberil")
  f71v  = Taurus(L) = May      ("May")
  f72r1 = Taurus(D) = May      ("May")
  f72r2 = Gemini    = June     ("Yuny")
  f72r3 = Cancer    = July     ("Jollet")
  f72v3 = Leo       = August   ("Augst")
  f72v2 = Virgo     = Sept     ("Septembr")
  f72v1 = Libra     = October  ("Octembre")
  f73r  = Scorpio   = November ("Novembre")
  f73v  = Sagittarius = Dec    ("Decembre")
  [missing: Capricorn=Jan, Aquarius=Feb]

Each zodiac page has ~30 nymphs arranged in concentric rings, each holding
a labeled star.  The labels are tagged @Lz or &Lz in the IVTFF transcription.
Additional astro folios (f67r, f67v, f68r, f68v, f69r, f69v) have star labels 
(@Ls), circular text (@Cc), and sector labels (@L0, @Ri).
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import result_path

# ── Zattera Slot System (from slot_analysis.py) ──────────────────────────

SLOT_TOKENS = {
    0:  ["q", "d", "s"],
    1:  ["y", "o"],
    2:  ["l", "r"],
    3:  ["f", "p", "k", "t"],
    4:  ["ckh", "cth", "cph", "cfh", "sch", "sh", "ch"],
    5:  ["eee", "ee", "e"],
    6:  ["d", "s"],
    7:  ["a", "o"],
    9:  ["iii", "ii", "i"],
    10: ["iin", "in", "n", "m", "d", "l", "r"],
    11: ["y"],
}

ZONE_PREFIX = [0, 1, 2]
ZONE_ROOT   = [3, 4, 5, 6, 7]
ZONE_SUFFIX = [9, 10, 11]

PREFIXES  = ["qo", "q", "do", "dy", "so", "sy", "ol", "or", "o", "y", "d", "s"]
ROOT_ONSETS = [
    "ckh","cth","cph","cfh","sch","sh","ch","f","p","k","t",
    "eee","ee","e","da","sa","a","o"
]
ROOT_BODIES = [
    "eee","ee","e","da","sa","do","so","a","o",
    "d","s","l","r","n","m"
]
SUFFIXES = [
    "aiin","aiir","ain","air","am","an","ar","al","as",
    "iin","iir","in","ir","dy","ey","ly","ry","ny","my",
    "or","ol","od","os","edy","eedy","y","d","l","r","s","g"
]

def parse_word_multi(word):
    """Multi-path greedy parser. Returns (prefix, root, suffix, success)."""
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
            for sf in SUFFIXES + [""]:
                if tail == sf:
                    score = (len(pf) > 0) + (len(root_str) > 0) + (len(sf) > 0)
                    if best is None or score > best[3]:
                        best = (pf, root_str, sf, score)
    if best:
        return best[0], best[1], best[2], True
    return "", word, "", False

def decompose_word(word):
    """Slot decomposition."""
    slots = {}
    pos = 0
    for slot_num in sorted(SLOT_TOKENS.keys()):
        if pos >= len(word):
            break
        for token in SLOT_TOKENS[slot_num]:
            if word[pos:].startswith(token):
                slots[slot_num] = token
                pos += len(token)
                break
    remainder = word[pos:] if pos < len(word) else ""
    return slots, remainder


# ── Zodiac Folio Metadata ────────────────────────────────────────────────

ZODIAC_MAP = {
    "f70v2": {"sign": "Pisces",      "month": "March",     "latin": "Marc",      "element": "Water", "modality": "Mutable"},
    "f70v1": {"sign": "Aries",       "month": "April",     "latin": "Aberil",    "element": "Fire",  "modality": "Cardinal", "note": "dark"},
    "f71r":  {"sign": "Aries",       "month": "April",     "latin": "Aberil",    "element": "Fire",  "modality": "Cardinal", "note": "light"},
    "f71v":  {"sign": "Taurus",      "month": "May",       "latin": "May",       "element": "Earth", "modality": "Fixed", "note": "light"},
    "f72r1": {"sign": "Taurus",      "month": "May",       "latin": "May",       "element": "Earth", "modality": "Fixed", "note": "dark"},
    "f72r2": {"sign": "Gemini",      "month": "June",      "latin": "Yuny",      "element": "Air",   "modality": "Mutable"},
    "f72r3": {"sign": "Cancer",      "month": "July",      "latin": "Jollet",    "element": "Water", "modality": "Cardinal"},
    "f72v3": {"sign": "Leo",         "month": "August",    "latin": "Augst",     "element": "Fire",  "modality": "Fixed"},
    "f72v2": {"sign": "Virgo",       "month": "September", "latin": "Septembr",  "element": "Earth", "modality": "Mutable"},
    "f72v1": {"sign": "Libra",       "month": "October",   "latin": "Octembre",  "element": "Air",   "modality": "Cardinal"},
    "f73r":  {"sign": "Scorpio",     "month": "November",  "latin": "Novembre",  "element": "Water", "modality": "Fixed"},
    "f73v":  {"sign": "Sagittarius", "month": "December",  "latin": "Decembre",  "element": "Fire",  "modality": "Mutable"},
}

# Other astro folios (non-zodiac)
ASTRO_FOLIOS = [
    "f67r", "f67v", "f68r", "f68v", "f69r", "f69v_70r",
]

FOLIOS_DIR = Path("folios")


# ── Label Extraction ──────────────────────────────────────────────────────

def extract_astro_labels(txt_path):
    """
    Extract labels from an astronomical folio transcription.
    
    Label types:
      @Lz / &Lz  = zodiac nymph labels (star-bearing figures)
      @Ls / &Ls  = star labels (non-zodiac astro pages)
      @Ri         = radial labels
      @L0 / &L0  = sector/scattered labels
      @Cc / +Cc   = circular text bands
    
    Returns a list of dicts: {locus, locus_type, clock_pos, text, words, folio_id}
    """
    text = txt_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    
    labels = []
    current_folio_id = None
    
    for line in lines:
        stripped = line.strip()
        
        # Track folio sub-page IDs (e.g., <f70v1>, <f72r2>)
        folio_header = re.match(r"^<(f\d+\w*\d*)>", stripped)
        if folio_header:
            current_folio_id = folio_header.group(1)
            continue
        
        # Skip pure comments
        if stripped.startswith("#") or not stripped:
            continue
        
        # Parse locus-tagged lines
        locus_match = re.match(r"<([^>]+)>\s*(.*)", stripped)
        if not locus_match:
            continue
        
        locus_tag = locus_match.group(1)
        raw_text = locus_match.group(2).strip()
        
        # Determine locus type
        locus_type = None
        if "Lz" in locus_tag:
            locus_type = "nymph_label"
        elif "Ls" in locus_tag:
            locus_type = "star_label"
        elif "Ri" in locus_tag:
            locus_type = "radial_label"
        elif "L0" in locus_tag:
            locus_type = "sector_label"
        elif "Cc" in locus_tag:
            locus_type = "circular_text"
        elif "Pb" in locus_tag:
            locus_type = "block_text"
        elif "P0" in locus_tag:
            locus_type = "paragraph"
        else:
            locus_type = "other"
        
        # Extract clock position if present
        clock_match = re.search(r"<!(\d{1,2}:\d{2})>", raw_text)
        clock_pos = clock_match.group(1) if clock_match else None
        
        # Clean the text
        clean = raw_text
        clean = re.sub(r"<![^>]*>", "", clean)           # remove clock-position comments
        clean = re.sub(r"<!.*?>", "", clean)              # other inline comments
        clean = re.sub(r"<%>", "", clean)                 # paragraph start
        clean = re.sub(r"<\$>", "", clean)                # paragraph end
        clean = re.sub(r"<-?>", "", clean)
        clean = re.sub(r"<[^>]*>", "", clean)             # remaining tags
        clean = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", clean)  # [a:b] → a
        clean = re.sub(r"\{([^}]+)\}", r"\1", clean)     # {xx} → xx
        clean = re.sub(r"@\d+;?", "", clean)              # annotation markers
        clean = re.sub(r"<!\w+>", "", clean)
        
        # Extract individual words
        tokens = re.split(r"[.\s,<>\-]+", clean)
        words = []
        for tok in tokens:
            tok = tok.strip()
            if not tok or "?" in tok or "'" in tok:
                continue
            if re.match(r"^[a-z]+$", tok) and len(tok) >= 2:
                words.append(tok)
        
        if not words:
            continue
        
        labels.append({
            "folio_id": current_folio_id,
            "locus": locus_tag,
            "locus_type": locus_type,
            "clock_pos": clock_pos,
            "raw_text": raw_text.strip(),
            "clean_text": clean.strip(),
            "words": words,
        })
    
    return labels


# ── Analysis Functions ────────────────────────────────────────────────────

def analyze_labels_morphologically(labels_by_folio):
    """Parse all labels through the multi-path parser and collect morphological stats."""
    results = {}
    all_parsed = []
    
    for folio_id, labels in labels_by_folio.items():
        folio_parsed = []
        for lab in labels:
            if lab["locus_type"] != "nymph_label" and lab["locus_type"] != "star_label":
                continue
            for word in lab["words"]:
                prefix, root, suffix, ok = parse_word_multi(word)
                slots, remainder = decompose_word(word)
                parsed = {
                    "word": word,
                    "prefix": prefix,
                    "root": root,
                    "suffix": suffix,
                    "parsed": ok,
                    "slots": slots,
                    "remainder": remainder,
                    "folio_id": folio_id,
                    "clock_pos": lab["clock_pos"],
                }
                folio_parsed.append(parsed)
                all_parsed.append(parsed)
        results[folio_id] = folio_parsed
    
    return results, all_parsed


def cross_zodiac_root_analysis(parsed_by_folio, zodiac_map):
    """
    For each zodiac page, collect root distributions and test:
    1. Root repertoire per sign — are certain roots sign-specific?
    2. Root sharing across signs — do signs with related properties share roots?
    3. Element/modality grouping — do Fire signs share roots vs Water signs?
    """
    sign_roots = defaultdict(Counter)
    element_roots = defaultdict(Counter)
    modality_roots = defaultdict(Counter)
    
    for folio_id, parsed_list in parsed_by_folio.items():
        meta = zodiac_map.get(folio_id)
        if not meta:
            continue
        for p in parsed_list:
            if p["parsed"] and p["root"]:
                sign_roots[meta["sign"]][p["root"]] += 1
                element_roots[meta["element"]][p["root"]] += 1
                modality_roots[meta["modality"]][p["root"]] += 1
    
    return dict(sign_roots), dict(element_roots), dict(modality_roots)


def find_label_hapax_and_shared(all_parsed, zodiac_map):
    """
    Identify:
    - Labels unique to one zodiac sign (potential proper names/star names)
    - Labels shared across multiple signs (potential common terms like 'star', 'bright')
    """
    word_to_signs = defaultdict(set)
    word_counts = Counter()
    
    for p in all_parsed:
        folio_id = p["folio_id"]
        meta = zodiac_map.get(folio_id, {})
        sign = meta.get("sign", folio_id)
        word_to_signs[p["word"]].add(sign)
        word_counts[p["word"]] += 1
    
    unique_to_sign = {}  # word → sign (appears in only one sign)
    shared_words = {}    # word → set of signs
    
    for word, signs in word_to_signs.items():
        if len(signs) == 1:
            unique_to_sign[word] = list(signs)[0]
        else:
            shared_words[word] = sorted(signs)
    
    return unique_to_sign, shared_words, dict(word_counts)


def clock_position_analysis(all_parsed, zodiac_map):
    """
    Test whether nymph labels at the same clock position across different
    zodiac signs share morphological properties (e.g., same root = same 
    degree or decan position meaning the same thing across signs).
    """
    clock_roots = defaultdict(Counter)
    clock_prefixes = defaultdict(Counter)
    clock_suffixes = defaultdict(Counter)
    
    for p in all_parsed:
        if not p["clock_pos"] or not p["parsed"]:
            continue
        cp = p["clock_pos"]
        if p["root"]:
            clock_roots[cp][p["root"]] += 1
        if p["prefix"]:
            clock_prefixes[cp][p["prefix"]] += 1
        if p["suffix"]:
            clock_suffixes[cp][p["suffix"]] += 1
    
    return dict(clock_roots), dict(clock_prefixes), dict(clock_suffixes)


def suffix_distribution_across_signs(all_parsed, zodiac_map):
    """
    Compare suffix distributions across zodiac signs to test whether
    suffixes encode some consistent property (e.g., magnitude, gender, decan).
    """
    sign_suffixes = defaultdict(Counter)
    
    for p in all_parsed:
        meta = zodiac_map.get(p["folio_id"], {})
        sign = meta.get("sign", p["folio_id"])
        if p["parsed"] and p["suffix"]:
            sign_suffixes[sign][p["suffix"]] += 1
    
    return dict(sign_suffixes)


def prefix_o_analysis(all_parsed, zodiac_map):
    """
    The prefix 'o' was previously identified as dominant in labels.
    Test its distribution: what fraction of nymph labels start with 'o-'?
    Compare to non-label text.
    """
    total_labels = 0
    o_prefix_labels = 0
    prefix_dist = Counter()
    
    for p in all_parsed:
        total_labels += 1
        if p["prefix"]:
            prefix_dist[p["prefix"]] += 1
        if p["word"].startswith("o"):
            o_prefix_labels += 1
    
    return {
        "total_labels": total_labels,
        "o_prefix_count": o_prefix_labels,
        "o_prefix_fraction": o_prefix_labels / total_labels if total_labels > 0 else 0,
        "prefix_distribution": dict(prefix_dist.most_common(20)),
    }


def root_type_classification(all_parsed):
    """
    Classify each label root as Type A (substance) or Type B (process) 
    using the bimodal y-fraction criterion from Phase 1.
    Labels in zodiac sections should overwhelmingly be Type A (substance).
    """
    root_y_frac = defaultdict(lambda: {"y_count": 0, "total": 0})
    
    for p in all_parsed:
        if not p["parsed"] or not p["root"]:
            continue
        root = p["root"]
        root_y_frac[root]["total"] += 1
        if p["suffix"] in ("y", "dy", "ey", "ly", "ry", "ny", "my", "edy", "eedy"):
            root_y_frac[root]["y_count"] += 1
    
    types = {"A": [], "B": [], "M": []}
    for root, data in root_y_frac.items():
        if data["total"] < 2:
            continue
        frac = data["y_count"] / data["total"]
        if frac > 0.8:
            types["B"].append((root, frac))
        elif frac < 0.3:
            types["A"].append((root, frac))
        else:
            types["M"].append((root, frac))
    
    return types


def compare_zodiac_vs_nonzodiac_stars(zodiac_labels, star_labels):
    """Compare nymph labels from zodiac pages with star labels from other astro pages."""
    zodiac_words = set()
    for lab in zodiac_labels:
        for w in lab["words"]:
            zodiac_words.add(w)
    
    star_words = set()
    for lab in star_labels:
        for w in lab["words"]:
            star_words.add(w)
    
    shared = zodiac_words & star_words
    zodiac_only = zodiac_words - star_words
    star_only = star_words - zodiac_words
    
    return {
        "zodiac_unique_words": len(zodiac_words),
        "star_unique_words": len(star_words),
        "shared_count": len(shared),
        "shared_words": sorted(shared),
        "zodiac_only_count": len(zodiac_only),
        "star_only_count": len(star_only),
        "jaccard": len(shared) / len(zodiac_words | star_words) if (zodiac_words | star_words) else 0,
    }


def find_decan_patterns(all_parsed, zodiac_map):
    """
    Each zodiac sign spans 30 degrees, divided into 3 decans of 10 degrees each.
    The 30 nymphs per sign could represent individual degrees or decan sub-groups.
    Test whether nymphs cluster into groups of ~10 by root or suffix pattern.
    
    Inner ring = 1st decan? Middle = 2nd? Outer = 3rd?
    Or: groups of 10 sequential nymphs share roots?
    """
    sign_label_sequences = defaultdict(list)  # sign → list of (clock_pos, word, parsed)
    
    for p in all_parsed:
        meta = zodiac_map.get(p["folio_id"], {})
        sign = meta.get("sign", None)
        if sign and p["clock_pos"]:
            # Convert clock position to numeric for ordering
            h, m = p["clock_pos"].split(":")
            numeric = float(h) * 60 + float(m)
            sign_label_sequences[sign].append({
                "clock_numeric": numeric,
                "word": p["word"],
                "root": p["root"],
                "suffix": p["suffix"],
                "prefix": p["prefix"],
            })
    
    # Sort each sign's labels by clock position
    for sign in sign_label_sequences:
        sign_label_sequences[sign].sort(key=lambda x: x["clock_numeric"])
    
    # Test: in each sign, split the 30 labels into thirds and check root overlap
    decan_analysis = {}
    for sign, labels in sign_label_sequences.items():
        n = len(labels)
        if n < 6:
            continue
        third = n // 3
        groups = [labels[:third], labels[third:2*third], labels[2*third:]]
        group_roots = [Counter(l["root"] for l in g if l["root"]) for g in groups]
        group_suffixes = [Counter(l["suffix"] for l in g if l["suffix"]) for g in groups]
        
        decan_analysis[sign] = {
            "total_labels": n,
            "group_sizes": [len(g) for g in groups],
            "group_root_diversity": [len(gr) for gr in group_roots],
            "group_suffix_dist": [dict(gs.most_common(5)) for gs in group_suffixes],
            "group_top_roots": [dict(gr.most_common(5)) for gr in group_roots],
        }
    
    return decan_analysis


def ring_analysis(labels_by_folio, zodiac_map):
    """
    Zodiac pages have labels tagged as appearing in 'inner ring', 'outer ring',
    or 'top row'. We can infer ring membership from the locus tag numbering.
    
    In the IVTFF, label numbering typically follows: outer ring first, then inner ring.
    The comment structure tells us which ring each label belongs to.
    """
    ring_data = defaultdict(lambda: defaultdict(list))  # sign → ring → words
    
    # We'll use the actual transcription structure: labels between 
    # certain circular text bands belong to specific rings
    for folio_id, labels in labels_by_folio.items():
        meta = zodiac_map.get(folio_id)
        if not meta:
            continue
        sign = meta["sign"]
        
        ring = "unknown"
        for lab in labels:
            # Ring transitions indicated by circular text bands
            if lab["locus_type"] == "circular_text":
                ring = "transition"
                continue
            if lab["locus_type"] == "nymph_label":
                # First set of nymph labels = outer ring (or top row)
                ring_data[sign][ring].append(lab["words"])
    
    return dict(ring_data)


# ── Main Pipeline ─────────────────────────────────────────────────────────

def main():
    results = {}
    
    # ──────────────────────────────────────────────────────────────────────
    # 1. EXTRACT all labels from zodiac folios
    # ──────────────────────────────────────────────────────────────────────
    print("=" * 70)
    print("PHASE 1: Extracting labels from zodiac folios")
    print("=" * 70)
    
    all_zodiac_labels = []
    labels_by_folio = {}
    
    zodiac_files = {
        "f70v_part.txt": ["f70v1", "f70v2"],
        "f71r.txt":      ["f71r"],
        "f71v_72r.txt":  ["f71v", "f72r1", "f72r2", "f72r3"],
        "f72v_part.txt": ["f72v1", "f72v2", "f72v3"],
        "f73r.txt":      ["f73r"],
        "f73v.txt":      ["f73v"],
    }
    
    for filename, folio_ids in zodiac_files.items():
        path = FOLIOS_DIR / filename
        if not path.exists():
            print(f"  WARNING: {filename} not found")
            continue
        labels = extract_astro_labels(path)
        for lab in labels:
            fid = lab["folio_id"]
            if fid in ZODIAC_MAP:
                if fid not in labels_by_folio:
                    labels_by_folio[fid] = []
                labels_by_folio[fid].append(lab)
                all_zodiac_labels.append(lab)
    
    total_labels = sum(len(v) for v in labels_by_folio.values())
    nymph_labels = [l for l in all_zodiac_labels if l["locus_type"] == "nymph_label"]
    circ_text = [l for l in all_zodiac_labels if l["locus_type"] == "circular_text"]
    
    print(f"\n  Total locus entries extracted: {total_labels}")
    print(f"  Nymph labels: {len(nymph_labels)}")
    print(f"  Circular text bands: {len(circ_text)}")
    print(f"  Zodiac pages covered: {len(labels_by_folio)}")
    
    # Breakdown per zodiac sign
    print("\n  Per-sign breakdown:")
    folio_summary = {}
    for fid in sorted(labels_by_folio.keys()):
        meta = ZODIAC_MAP[fid]
        nl = sum(1 for l in labels_by_folio[fid] if l["locus_type"] == "nymph_label")
        ct = sum(1 for l in labels_by_folio[fid] if l["locus_type"] == "circular_text")
        all_words = []
        for l in labels_by_folio[fid]:
            all_words.extend(l["words"])
        print(f"    {fid:8s}  {meta['sign']:12s} ({meta['month']:>9s})  "
              f"labels={nl:2d}  circ_text={ct:1d}  total_words={len(all_words):3d}")
        folio_summary[fid] = {
            "sign": meta["sign"], "month": meta["month"],
            "nymph_labels": nl, "circular_bands": ct, 
            "total_words": len(all_words)
        }
    
    results["folio_summary"] = folio_summary
    
    # ──────────────────────────────────────────────────────────────────────
    # 2. EXTRACT labels from non-zodiac astro folios
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 2: Extracting labels from non-zodiac astro folios")
    print("=" * 70)
    
    all_star_labels = []
    astro_labels_by_folio = {}
    
    astro_files = ["f67r.txt", "f67v.txt", "f68r.txt", "f68v.txt", "f69r.txt", "f69v_70r.txt"]
    for filename in astro_files:
        path = FOLIOS_DIR / filename
        if not path.exists():
            print(f"  WARNING: {filename} not found")
            continue
        labels = extract_astro_labels(path)
        folio_key = filename.replace(".txt", "")
        astro_labels_by_folio[folio_key] = labels
        for lab in labels:
            if lab["locus_type"] in ("star_label", "sector_label", "radial_label"):
                all_star_labels.append(lab)
    
    print(f"  Non-zodiac astro pages: {len(astro_labels_by_folio)}")
    print(f"  Star/sector/radial labels: {len(all_star_labels)}")
    
    for fkey, labels in sorted(astro_labels_by_folio.items()):
        stars = sum(1 for l in labels if l["locus_type"] == "star_label")
        sectors = sum(1 for l in labels if l["locus_type"] == "sector_label")
        radials = sum(1 for l in labels if l["locus_type"] == "radial_label")
        print(f"    {fkey:15s}  stars={stars:2d}  sectors={sectors:2d}  radials={radials:2d}")
    
    # ──────────────────────────────────────────────────────────────────────
    # 3. MORPHOLOGICAL ANALYSIS of zodiac labels
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 3: Morphological analysis of zodiac nymph labels")
    print("=" * 70)
    
    parsed_by_folio, all_parsed = analyze_labels_morphologically(labels_by_folio)
    
    parse_ok = sum(1 for p in all_parsed if p["parsed"])
    print(f"\n  Total nymph/star label words: {len(all_parsed)}")
    print(f"  Successfully parsed: {parse_ok} ({100*parse_ok/len(all_parsed):.1f}%)")
    
    # Prefix analysis
    prefix_stats = prefix_o_analysis(all_parsed, ZODIAC_MAP)
    print(f"\n  o-prefix fraction in labels: {prefix_stats['o_prefix_fraction']:.1%}")
    print(f"  Prefix distribution:")
    for pf, ct in sorted(prefix_stats["prefix_distribution"].items(), key=lambda x: -x[1])[:10]:
        print(f"    {pf:6s}  {ct:3d}")
    
    results["prefix_analysis"] = prefix_stats
    
    # Root distribution
    root_counts = Counter()
    for p in all_parsed:
        if p["parsed"] and p["root"]:
            root_counts[p["root"]] += 1
    
    print(f"\n  Unique roots in labels: {len(root_counts)}")
    print(f"  Top 20 roots:")
    for root, ct in root_counts.most_common(20):
        # Find which signs contain this root
        signs_with = set()
        for p in all_parsed:
            if p["root"] == root and p["parsed"]:
                meta = ZODIAC_MAP.get(p["folio_id"], {})
                s = meta.get("sign", "?")
                signs_with.add(s)
        print(f"    {root:12s}  {ct:3d}  signs={','.join(sorted(signs_with))}")
    
    results["root_distribution"] = dict(root_counts.most_common(50))
    
    # Suffix distribution
    suffix_counts = Counter()
    for p in all_parsed:
        if p["parsed"] and p["suffix"]:
            suffix_counts[p["suffix"]] += 1
    
    print(f"\n  Suffix distribution:")
    for sf, ct in suffix_counts.most_common(15):
        print(f"    {sf:6s}  {ct:3d}")
    
    results["suffix_distribution"] = dict(suffix_counts.most_common(30))
    
    # Root type classification
    types = root_type_classification(all_parsed)
    print(f"\n  Root type classification (from label words only):")
    print(f"    Type A (substance): {len(types['A'])} roots")
    print(f"    Type B (process):   {len(types['B'])} roots")
    print(f"    Mixed:              {len(types['M'])} roots")
    
    results["root_types_in_labels"] = {
        "A": [(r, round(f, 2)) for r, f in types["A"]],
        "B": [(r, round(f, 2)) for r, f in types["B"]],
        "M": [(r, round(f, 2)) for r, f in types["M"]],
    }
    
    # ──────────────────────────────────────────────────────────────────────
    # 4. CROSS-ZODIAC ROOT ANALYSIS
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 4: Cross-zodiac root analysis")
    print("=" * 70)
    
    sign_roots, element_roots, modality_roots = cross_zodiac_root_analysis(
        parsed_by_folio, ZODIAC_MAP
    )
    
    print("\n  Root repertoire per zodiac sign:")
    for sign in ["Pisces", "Aries", "Taurus", "Gemini", "Cancer", "Leo",
                  "Virgo", "Libra", "Scorpio", "Sagittarius"]:
        if sign in sign_roots:
            roots = sign_roots[sign]
            top5 = roots.most_common(5)
            top_str = ", ".join(f"{r}({c})" for r, c in top5)
            print(f"    {sign:12s}  {len(roots):2d} unique roots  top: {top_str}")
    
    print("\n  Root overlap by ELEMENT:")
    elements = sorted(element_roots.keys())
    for i, e1 in enumerate(elements):
        for e2 in elements[i+1:]:
            shared = set(element_roots[e1].keys()) & set(element_roots[e2].keys())
            total = set(element_roots[e1].keys()) | set(element_roots[e2].keys())
            jaccard = len(shared) / len(total) if total else 0
            print(f"    {e1:6s} ↔ {e2:6s}  shared={len(shared):2d}  jaccard={jaccard:.3f}")
    
    print("\n  Root overlap by MODALITY:")
    modalities = sorted(modality_roots.keys())
    for i, m1 in enumerate(modalities):
        for m2 in modalities[i+1:]:
            shared = set(modality_roots[m1].keys()) & set(modality_roots[m2].keys())
            total = set(modality_roots[m1].keys()) | set(modality_roots[m2].keys())
            jaccard = len(shared) / len(total) if total else 0
            print(f"    {m1:8s} ↔ {m2:8s}  shared={len(shared):2d}  jaccard={jaccard:.3f}")
    
    results["element_jaccard"] = {}
    for i, e1 in enumerate(elements):
        for e2 in elements[i+1:]:
            shared = set(element_roots[e1].keys()) & set(element_roots[e2].keys())
            total = set(element_roots[e1].keys()) | set(element_roots[e2].keys())
            results["element_jaccard"][f"{e1}-{e2}"] = round(len(shared)/len(total), 3) if total else 0
    
    # ──────────────────────────────────────────────────────────────────────
    # 5. UNIQUE vs SHARED LABELS
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 5: Label uniqueness analysis")
    print("=" * 70)
    
    unique_to_sign, shared_words, word_counts = find_label_hapax_and_shared(
        all_parsed, ZODIAC_MAP
    )
    
    print(f"\n  Labels unique to one sign: {len(unique_to_sign)}")
    print(f"  Labels shared across signs: {len(shared_words)}")
    print(f"  Total unique label words: {len(word_counts)}")
    
    print(f"\n  Most-shared labels (appear in most signs):")
    for word, signs in sorted(shared_words.items(), key=lambda x: -len(x[1]))[:15]:
        count = word_counts[word]
        prefix, root, suffix, ok = parse_word_multi(word)
        morph = f"{prefix}|{root}|{suffix}" if ok else "UNPARSED"
        print(f"    {word:15s}  {count:2d}×  in {len(signs)} signs  {morph:20s}  [{', '.join(signs)}]")
    
    results["shared_label_count"] = len(shared_words)
    results["unique_label_count"] = len(unique_to_sign)
    results["most_shared"] = [
        {"word": w, "count": word_counts[w], "signs": s}
        for w, s in sorted(shared_words.items(), key=lambda x: -len(x[1]))[:20]
    ]
    
    # ──────────────────────────────────────────────────────────────────────
    # 6. ZODIAC vs NON-ZODIAC STAR LABEL COMPARISON
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 6: Zodiac nymph labels vs non-zodiac star labels")
    print("=" * 70)
    
    comparison = compare_zodiac_vs_nonzodiac_stars(nymph_labels, all_star_labels)
    print(f"\n  Zodiac nymph unique words: {comparison['zodiac_unique_words']}")
    print(f"  Non-zodiac star unique words: {comparison['star_unique_words']}")
    print(f"  Shared vocabulary: {comparison['shared_count']}")
    print(f"  Jaccard similarity: {comparison['jaccard']:.3f}")
    if comparison['shared_words']:
        print(f"  Shared words: {', '.join(comparison['shared_words'][:20])}")
    
    results["zodiac_vs_star_comparison"] = comparison
    
    # ──────────────────────────────────────────────────────────────────────
    # 7. SUFFIX PATTERNS ACROSS SIGNS
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 7: Suffix consistency across zodiac signs")
    print("=" * 70)
    
    sign_sfx = suffix_distribution_across_signs(all_parsed, ZODIAC_MAP)
    
    print("\n  Top suffixes per sign:")
    for sign in ["Pisces", "Aries", "Taurus", "Gemini", "Cancer", "Leo",
                  "Virgo", "Libra", "Scorpio", "Sagittarius"]:
        if sign in sign_sfx:
            top = sign_sfx[sign].most_common(5)
            sfx_str = ", ".join(f"{s}({c})" for s, c in top)
            total = sum(sign_sfx[sign].values())
            print(f"    {sign:12s}  n={total:2d}  {sfx_str}")
    
    results["suffix_by_sign"] = {s: dict(c.most_common(10)) for s, c in sign_sfx.items()}
    
    # ──────────────────────────────────────────────────────────────────────
    # 8. CLOCK POSITION CORRELATION
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 8: Clock position correlation (decan/degree test)")
    print("=" * 70)
    
    clock_roots, clock_pfx, clock_sfx = clock_position_analysis(all_parsed, ZODIAC_MAP)
    
    print(f"\n  Unique clock positions: {len(clock_roots)}")
    print(f"\n  Root variety by position (top positions):")
    for cp, roots in sorted(clock_roots.items(), key=lambda x: -sum(x[1].values()))[:10]:
        total = sum(roots.values())
        top = roots.most_common(3)
        top_str = ", ".join(f"{r}({c})" for r, c in top)
        print(f"    {cp:6s}  n={total:2d}  roots: {top_str}")
    
    # ──────────────────────────────────────────────────────────────────────
    # 9. DECAN PATTERN TEST
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 9: Decan grouping test (thirds of nymph sequences)")
    print("=" * 70)
    
    decan = find_decan_patterns(all_parsed, ZODIAC_MAP)
    
    for sign in ["Pisces", "Aries", "Taurus", "Gemini", "Cancer", "Leo",
                  "Virgo", "Libra", "Scorpio", "Sagittarius"]:
        if sign not in decan:
            continue
        d = decan[sign]
        print(f"\n  {sign} ({d['total_labels']} labels, groups: {d['group_sizes']}):")
        for i, (roots, sfx) in enumerate(zip(d["group_top_roots"], d["group_suffix_dist"])):
            root_str = ", ".join(f"{r}({c})" for r, c in sorted(roots.items(), key=lambda x: -x[1])[:3])
            sfx_str = ", ".join(f"{s}({c})" for s, c in sorted(sfx.items(), key=lambda x: -x[1])[:3])
            print(f"    Group {i+1}: roots=[{root_str}]  suffixes=[{sfx_str}]")
    
    results["decan_analysis"] = {}
    for sign, d in decan.items():
        results["decan_analysis"][sign] = d
    
    # ──────────────────────────────────────────────────────────────────────
    # 10. COMPLETE LABEL INVENTORY
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 10: Complete label inventory for semantic assignment")
    print("=" * 70)
    
    # Build the master table: every nymph label with its zodiac context
    inventory = []
    for p in all_parsed:
        meta = ZODIAC_MAP.get(p["folio_id"], {})
        entry = {
            "word": p["word"],
            "folio": p["folio_id"],
            "sign": meta.get("sign", "?"),
            "month": meta.get("month", "?"),
            "element": meta.get("element", "?"),
            "clock": p["clock_pos"],
            "prefix": p["prefix"],
            "root": p["root"],
            "suffix": p["suffix"],
            "parsed": p["parsed"],
        }
        inventory.append(entry)
    
    print(f"\n  Total label inventory entries: {len(inventory)}")
    print(f"\n  Sample entries:")
    for entry in inventory[:10]:
        print(f"    {entry['word']:15s}  {entry['sign']:12s}  @{entry['clock'] or '?':6s}  "
              f"{entry['prefix']}|{entry['root']}|{entry['suffix']}")
    
    results["label_inventory"] = inventory
    
    # ──────────────────────────────────────────────────────────────────────
    # 11. SYNTHESIS: Anchor-ready mappings
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SYNTHESIS: Key findings for semantic assignment")
    print("=" * 70)
    
    # What fraction of labels are parseable?
    parseable = sum(1 for p in all_parsed if p["parsed"])
    total = len(all_parsed)
    
    # Most common root = most common concept in star labels
    top_root = root_counts.most_common(1)[0] if root_counts else ("?", 0)
    
    # Labels are overwhelmingly o-prefixed 
    o_frac = prefix_stats["o_prefix_fraction"]
    
    # How many labels unique vs shared
    uniqueness_ratio = len(unique_to_sign) / (len(unique_to_sign) + len(shared_words)) if (unique_to_sign or shared_words) else 0
    
    synthesis = {
        "parse_rate": round(parseable / total, 3) if total else 0,
        "label_count": total,
        "o_prefix_dominance": round(o_frac, 3),
        "unique_to_sign_fraction": round(uniqueness_ratio, 3),
        "top_root": top_root[0],
        "top_root_count": top_root[1],
        "zodiac_star_jaccard": comparison["jaccard"],
        "type_A_roots_in_labels": len(types["A"]),
        "type_B_roots_in_labels": len(types["B"]),
    }
    
    print(f"\n  Parse rate for labels: {synthesis['parse_rate']:.1%}")
    print(f"  Total label words: {synthesis['label_count']}")
    print(f"  o-prefix dominance: {synthesis['o_prefix_dominance']:.1%}")
    print(f"  Labels unique to one sign: {synthesis['unique_to_sign_fraction']:.1%}")
    print(f"  Top root: '{synthesis['top_root']}' ({synthesis['top_root_count']}×)")
    print(f"  Zodiac↔Star vocabulary Jaccard: {synthesis['zodiac_star_jaccard']:.3f}")
    print(f"  Type A roots: {synthesis['type_A_roots_in_labels']}  Type B: {synthesis['type_B_roots_in_labels']}")
    
    # Key semantic candidates
    print(f"\n  SEMANTIC CANDIDATES (most-shared labels = likely common nouns):")
    print(f"  These appear across many signs, suggesting generic terms like")
    print(f"  'star', 'bright', 'first', 'degree', etc.:")
    for item in results["most_shared"][:10]:
        pf, rt, sf, ok = parse_word_multi(item["word"])
        print(f"    '{item['word']}' → {pf}|{rt}|{sf}  ({item['count']}× in {len(item['signs'])} signs)")
    
    print(f"\n  SIGN-SPECIFIC LABELS (possible star proper names):")
    sign_specific_samples = defaultdict(list)
    for word, sign in unique_to_sign.items():
        sign_specific_samples[sign].append(word)
    for sign in sorted(sign_specific_samples.keys()):
        words = sign_specific_samples[sign][:5]
        print(f"    {sign:12s}: {', '.join(words)}")
    
    results["synthesis"] = synthesis
    
    # ── Save results ─────────────────────────────────────────────────────
    output_path = result_path("astro_label_results.json")
    
    # Serialize: convert Counter objects and sets
    def clean_for_json(obj):
        if isinstance(obj, dict):
            return {str(k): clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [clean_for_json(i) for i in obj]
        elif isinstance(obj, set):
            return sorted(list(obj))
        elif isinstance(obj, Counter):
            return dict(obj.most_common())
        return obj
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clean_for_json(results), f, indent=2, ensure_ascii=False)
    
    print(f"\n  Results saved to {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()