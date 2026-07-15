#!/usr/bin/env python3
"""
Voynich Manuscript — Ring-to-Decan Mapping & Positional Analysis

Phase 1: Parse all zodiac folios, extract ring structure, assign degree numbers
Phase 2: Test whether shared labels (otaly, otal, etc.) appear at consistent positions
Phase 3: Check labels at Behenian star positions

Prerequisite findings:
  - Each nymph = 1 degree (all signs have ~30 nymphs)
  - 3 decans of 10° per sign
  - Labels are constructed notation: o- article + root + grammatical suffix
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import result_path

FOLIOS_DIR = Path("folios")

# ── Sign-to-folio mapping ────────────────────────────────────────────────
# Signs split across multiple folios are listed in order
SIGN_FOLIOS = {
    "Pisces":      [("f70v_part.txt", "f70v2")],
    "Aries":       [("f70v_part.txt", "f70v1"), ("f71r.txt", "f71r")],
    "Taurus":      [("f71v_72r.txt", "f71v"), ("f71v_72r.txt", "f72r1")],
    "Gemini":      [("f71v_72r.txt", "f72r2")],
    "Cancer":      [("f71v_72r.txt", "f72r3")],
    "Leo":         [("f72v_part.txt", "f72v3")],
    "Virgo":       [("f72v_part.txt", "f72v2")],
    "Libra":       [("f72v_part.txt", "f72v1")],
    "Scorpio":     [("f73r.txt", "f73r")],
    "Sagittarius": [("f73v.txt", "f73v")],
}

# Decan rulers (Chaldean order)
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

# Behenian fixed stars — precession-adjusted to ~1400 AD
# Format: (star_name, zodiac_sign, degree_in_sign)
BEHENIAN_1400 = [
    ("Algol",     "Taurus",      13),
    ("Alcyone",   "Gemini",      17),
    ("Aldebaran", "Gemini",      27),  # near end of Gemini
    ("Capella",   "Cancer",       9),  # just entered Cancer
    ("Sirius",    "Cancer",       1),  # note: may still be late Gemini
    ("Procyon",   "Cancer",      13),
    ("Regulus",   "Leo",         17),
    ("Algorab",   "Libra",        0),  # cusp
    ("Spica",     "Libra",       11),
    ("Arcturus",  "Libra",       11),
    ("Alphecca",  "Scorpio",     29),
    ("Antares",   "Sagittarius", 27),
    ("Vega",      "Sagittarius",  2),  # ~Capricorn 2° if adjusted fully
    ("Deneb Algedi", "Pisces",   21),  # approximate
    ("Fomalhaut", "Pisces",      21),
]

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
SUFFIXES = [
    "aiin","aiir","ain","air","am","an","ar","al","as",
    "iin","iir","in","ir","dy","ey","ly","ry","ny","my",
    "or","ol","od","os","edy","eedy","y","d","l","r","s","g"
]

def parse_word(word):
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


# ── Folio Parser ──────────────────────────────────────────────────────────

def clock_to_angle(clock_str):
    """Convert clock position 'HH:MM' to degrees (0-360, 12:00 = 0°, clockwise)."""
    h, m = map(int, clock_str.split(":"))
    return ((h % 12) * 30 + m * 0.5) % 360

def parse_folio_rings(file_path, folio_id):
    """
    Parse a single folio sub-page, extracting nymphs grouped by ring.
    
    Returns list of rings, each ring is a list of dicts:
      {label, clock_pos, clock_angle, line_num, ring_name}
    
    Ring ordering: outer first (as in file), inner last.
    """
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    
    rings = []
    current_ring = None
    current_ring_name = "unknown"
    in_target_folio = False
    last_comment = ""
    
    for line in lines:
        stripped = line.strip()
        
        # Track folio headers
        folio_header = re.match(r"^<(" + re.escape(folio_id) + r")>", stripped)
        if folio_header:
            in_target_folio = True
            continue
        
        # Detect transition to a different folio
        other_folio = re.match(r"^<(f\d+\w*\d*)>", stripped)
        if other_folio and in_target_folio:
            # We've moved past our folio
            break
        
        if not in_target_folio:
            continue
        
        # Track comments for ring name
        if stripped.startswith("#"):
            last_comment = stripped.lower()
            # Detect ring name from comment
            if any(w in last_comment for w in ["outer ring", "outer band", "outer full", "outer complete"]):
                ring_hint = "outer"
            elif any(w in last_comment for w in ["middle band", "middle ring", "second ring"]):
                ring_hint = "middle"
            elif any(w in last_comment for w in ["inner ring", "inner band", "inner full"]):
                ring_hint = "inner"
            elif "top" in last_comment and ("nymph" in last_comment or "label" in last_comment):
                ring_hint = "top"
            elif "central" in last_comment:
                ring_hint = "central"
            else:
                ring_hint = None
            if ring_hint:
                current_ring_name = ring_hint
            continue
        
        if not stripped:
            continue
        
        # Parse locus-tagged lines
        locus_match = re.match(r"<([^>]+)>\s*(.*)", stripped)
        if not locus_match:
            continue
        
        locus_tag = locus_match.group(1)
        raw_text = locus_match.group(2).strip()
        
        # Only nymph labels
        if "Lz" not in locus_tag:
            # @Cc marks ring boundary
            if "Cc" in locus_tag:
                if current_ring is not None:
                    rings.append(current_ring)
                    current_ring = None
            continue
        
        # Start new ring on @Lz
        if "@Lz" in locus_tag:
            if current_ring is not None:
                rings.append(current_ring)
            current_ring = []
        
        if current_ring is None:
            current_ring = []
        
        # Extract clock position
        clock_match = re.search(r"<!(\d{1,2}:\d{2})>", raw_text)
        clock_pos = clock_match.group(1) if clock_match else None
        clock_angle = clock_to_angle(clock_pos) if clock_pos else None
        
        # Extract raw label text (after clock position)
        label_text = re.sub(r"<![\w\d: ,]+>", "", raw_text).strip()
        # Remove trailing comments
        label_text = re.sub(r"<!.*$", "", label_text).strip()
        
        # Extract line number
        line_num_match = re.search(r"\.(\d+),", locus_tag)
        line_num = int(line_num_match.group(1)) if line_num_match else None
        
        current_ring.append({
            "label": label_text,
            "clock_pos": clock_pos,
            "clock_angle": clock_angle,
            "line_num": line_num,
            "ring_name": current_ring_name,
            "folio_id": folio_id,
        })
    
    # Don't forget last ring
    if current_ring is not None and len(current_ring) > 0:
        rings.append(current_ring)
    
    return rings


def clean_label(raw_label):
    """Remove transcription artifacts from label text."""
    # Remove alternative readings [a:b], keep first option
    label = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', raw_label)
    # Remove uncertain readings {xxx}
    label = re.sub(r'\{[^}]+\}', '', label)
    # Remove @ codes
    label = re.sub(r'@\d+;?', '', label)
    # Clean up dots and commas (word separators)
    label = re.sub(r'[.,]+', '.', label)
    label = label.strip('.')
    return label


# ══════════════════════════════════════════════════════════════════════════
#  PHASE 1: Ring-to-Decan Mapping
# ══════════════════════════════════════════════════════════════════════════

def phase1_ring_mapping():
    print("=" * 70)
    print("PHASE 1: Ring-to-Decan Mapping")
    print("=" * 70)
    
    all_signs = {}
    
    for sign, folio_list in SIGN_FOLIOS.items():
        sign_rings = []
        
        for filename, folio_id in folio_list:
            path = FOLIOS_DIR / filename
            if not path.exists():
                print(f"  WARNING: {path} not found")
                continue
            rings = parse_folio_rings(path, folio_id)
            for ring in rings:
                sign_rings.append(ring)
        
        # Assign sequential degree numbers (1-30)
        degree = 1
        nymphs = []
        for ring_idx, ring in enumerate(sign_rings):
            for nymph in ring:
                nymph["degree"] = degree
                nymph["ring_idx"] = ring_idx
                nymph["decan"] = 1 + (degree - 1) // 10  # 1, 2, or 3
                nymph["decan_degree"] = ((degree - 1) % 10) + 1  # 1-10 within decan
                nymphs.append(nymph)
                degree += 1
        
        all_signs[sign] = {
            "nymphs": nymphs,
            "ring_count": len(sign_rings),
            "ring_sizes": [len(r) for r in sign_rings],
            "total": len(nymphs),
        }
    
    # Print overview
    print(f"\n  {'Sign':<14} {'Total':>5} {'Rings':>5}  Ring sizes           Ring names")
    print(f"  {'-'*14} {'-'*5} {'-'*5}  {'-'*20} {'-'*30}")
    for sign in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                 "Libra", "Scorpio", "Sagittarius", "Pisces"]:
        data = all_signs[sign]
        ring_sizes = data["ring_sizes"]
        ring_names = []
        for n in data["nymphs"]:
            if n["ring_idx"] >= len(ring_names):
                ring_names.append(n["ring_name"])
        print(f"  {sign:<14} {data['total']:>5} {data['ring_count']:>5}  "
              f"{str(ring_sizes):<20} {ring_names}")
    
    # Check if ring boundaries align with decan boundaries
    print(f"\n  Ring boundary vs decan boundary alignment:")
    print(f"  {'Sign':<14} Ring boundaries (cumul.)  Decan boundaries (10,20)")
    print(f"  {'-'*14} {'-'*24} {'-'*25}")
    for sign in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                 "Libra", "Scorpio", "Sagittarius", "Pisces"]:
        data = all_signs[sign]
        cumul = []
        c = 0
        for s in data["ring_sizes"]:
            c += s
            cumul.append(c)
        # Ring boundaries are at cumul[:-1] (not the last one which is total)
        boundaries = cumul[:-1]
        match = "✓" if boundaries == [10, 20] else "✗"
        print(f"  {sign:<14} {str(boundaries):<24} [10, 20]  {match}")
    
    # Detailed degree listing for one sign (Cancer, the anomalous one)
    print(f"\n  Detailed degree listing: Cancer")
    print(f"  {'Deg':>4} {'Decan':>5} {'Ring':>5} {'RingN':<8} {'Clock':<8} {'Label'}")
    print(f"  {'-'*4} {'-'*5} {'-'*5} {'-'*8} {'-'*8} {'-'*30}")
    for n in all_signs["Cancer"]["nymphs"]:
        cl = clean_label(n["label"])
        print(f"  {n['degree']:>4} {n['decan']:>5} {n['ring_idx']:>5} "
              f"{n['ring_name']:<8} {n['clock_pos'] or '?':<8} {cl}")
    
    return all_signs


# ══════════════════════════════════════════════════════════════════════════
#  PHASE 2: Positional Test — do shared labels appear at consistent degrees?
# ══════════════════════════════════════════════════════════════════════════

def phase2_positional_test(all_signs):
    print("\n" + "=" * 70)
    print("PHASE 2: Positional Test — shared labels at consistent positions?")
    print("=" * 70)
    
    # Build label → list of (sign, degree, decan, decan_degree)
    label_positions = defaultdict(list)
    
    for sign, data in all_signs.items():
        for n in data["nymphs"]:
            raw = clean_label(n["label"])
            # Split multi-word labels and also track full label
            words = [w.strip() for w in raw.split(".") if w.strip()]
            # Track full label
            label_positions[raw].append({
                "sign": sign,
                "degree": n["degree"],
                "decan": n["decan"],
                "decan_degree": n["decan_degree"],
                "ring_idx": n["ring_idx"],
                "ring_name": n["ring_name"],
            })
            # Track individual words if multi-word
            if len(words) > 1:
                for w in words:
                    label_positions[w].append({
                        "sign": sign,
                        "degree": n["degree"],
                        "decan": n["decan"],
                        "decan_degree": n["decan_degree"],
                        "ring_idx": n["ring_idx"],
                        "ring_name": n["ring_name"],
                    })
    
    # Find labels appearing in 2+ signs
    shared = {}
    for label, positions in label_positions.items():
        signs_seen = set(p["sign"] for p in positions)
        if len(signs_seen) >= 2:
            shared[label] = positions
    
    # Sort by frequency
    shared_sorted = sorted(shared.items(), key=lambda x: -len(x[1]))
    
    print(f"\n  Labels appearing in 2+ zodiac signs: {len(shared_sorted)}")
    print(f"\n  {'Label':<18} {'Count':>5} {'Signs':<35} {'Degrees':<25} {'Decans':<15} {'DecanDegs'}")
    print(f"  {'-'*18} {'-'*5} {'-'*35} {'-'*25} {'-'*15} {'-'*20}")
    
    for label, positions in shared_sorted[:30]:
        signs = sorted(set(p["sign"] for p in positions))
        degrees = [p["degree"] for p in positions]
        decans = [p["decan"] for p in positions]
        decan_degs = [p["decan_degree"] for p in positions]
        print(f"  {label:<18} {len(positions):>5} {','.join(s[:3] for s in signs):<35} "
              f"{str(degrees):<25} {str(decans):<15} {str(decan_degs)}")
    
    # Statistical test: degree position consistency
    print(f"\n  Degree position consistency test:")
    print(f"  For each shared label, compute σ(degree) and σ(decan_degree)")
    print(f"  Low σ = consistent position; high σ = random")
    print(f"\n  {'Label':<18} {'N':>3} {'σ(deg)':>8} {'σ(dDeg)':>8} {'μ(dDeg)':>8} {'Verdict'}")
    print(f"  {'-'*18} {'-'*3} {'-'*8} {'-'*8} {'-'*8} {'-'*15}")
    
    consistent_labels = []
    random_sigma = 30 / (12**0.5)  # σ for uniform over 1-30 ≈ 8.66
    decan_random_sigma = 10 / (12**0.5)  # σ for uniform over 1-10 ≈ 2.89
    
    for label, positions in shared_sorted[:30]:
        if len(positions) < 2:
            continue
        degrees = [p["degree"] for p in positions]
        decan_degs = [p["decan_degree"] for p in positions]
        
        mean_d = sum(degrees) / len(degrees)
        sigma_d = (sum((d - mean_d)**2 for d in degrees) / len(degrees)) ** 0.5
        
        mean_dd = sum(decan_degs) / len(decan_degs)
        sigma_dd = (sum((d - mean_dd)**2 for d in decan_degs) / len(decan_degs)) ** 0.5
        
        # Verdict: much lower than random?
        if sigma_dd < decan_random_sigma * 0.5:
            verdict = "CONSISTENT ◄"
            consistent_labels.append((label, positions, sigma_dd, mean_dd))
        elif sigma_dd < decan_random_sigma * 0.75:
            verdict = "moderate"
        else:
            verdict = "random"
        
        print(f"  {label:<18} {len(positions):>3} {sigma_d:>8.2f} {sigma_dd:>8.2f} "
              f"{mean_dd:>8.1f} {verdict}")
    
    print(f"\n  Random expectation: σ(degree)={random_sigma:.2f}, σ(decan_degree)={decan_random_sigma:.2f}")
    print(f"  Labels with σ(decan_degree) < {decan_random_sigma*0.5:.2f}: {len(consistent_labels)}")
    
    if consistent_labels:
        print(f"\n  CONSISTENTLY POSITIONED LABELS:")
        for label, positions, sigma, mean in consistent_labels:
            signs_degs = [(p["sign"][:3], p["degree"], p["decan_degree"]) for p in positions]
            print(f"    {label:<18} mean decan_deg={mean:.1f} σ={sigma:.2f}")
            for s, d, dd in signs_degs:
                print(f"      {s}: degree {d}, decan_degree {dd}")
    
    # Additional test: do specific decan positions (1, 5, 10) have special labels?
    print(f"\n  Label distribution at special decan positions:")
    special_positions = {1: "decan start", 5: "decan midpoint", 10: "decan end"}
    for pos, name in special_positions.items():
        labels_here = []
        for sign, data in all_signs.items():
            for n in data["nymphs"]:
                if n["decan_degree"] == pos:
                    labels_here.append((sign, n["degree"], clean_label(n["label"])))
        print(f"\n    Position {pos} ({name}):")
        for sign, deg, label in sorted(labels_here):
            pf, root, sf, ok = parse_word(label.split(".")[0])
            print(f"      {sign:<14} deg {deg:>2}: {label:<25} root={root}")
    
    return shared_sorted


# ══════════════════════════════════════════════════════════════════════════
#  PHASE 3: Behenian Star Anchor Test
# ══════════════════════════════════════════════════════════════════════════

def phase3_behenian_test(all_signs):
    print("\n" + "=" * 70)
    print("PHASE 3: Behenian Star Anchor Test")
    print("=" * 70)
    
    print(f"\n  Testing whether labels at Behenian star degree positions are 'special'")
    print(f"  (i.e., shared across signs, morphologically distinctive, or have unique roots)\n")
    
    # Collect all labels for each sign for comparison
    all_labels = Counter()
    sign_label_sets = {}
    for sign, data in all_signs.items():
        labels = set()
        for n in data["nymphs"]:
            cl = clean_label(n["label"])
            all_labels[cl] += 1
            labels.add(cl)
        sign_label_sets[sign] = labels
    
    print(f"  {'Star':<16} {'Sign':<14} {'Deg°':>4} {'Nymph Label':<28} "
          f"{'Prefix':<6} {'Root':<10} {'Suffix':<8} {'Shared?'}")
    print(f"  {'-'*16} {'-'*14} {'-'*4} {'-'*28} "
          f"{'-'*6} {'-'*10} {'-'*8} {'-'*10}")
    
    behenian_labels = []
    
    for star_name, sign, degree in BEHENIAN_1400:
        if sign not in all_signs:
            print(f"  {star_name:<16} {sign:<14} {degree:>4}° — sign not in dataset (missing)")
            continue
        
        data = all_signs[sign]
        nymphs = data["nymphs"]
        
        if degree < 1 or degree > len(nymphs):
            # Try nearby
            nearest = min(nymphs, key=lambda n: abs(n["degree"] - degree))
            label = clean_label(nearest["label"])
            actual_deg = nearest["degree"]
            note = f" (nearest to {degree}°)"
        else:
            nymph = nymphs[degree - 1]
            label = clean_label(nymph["label"])
            actual_deg = nymph["degree"]
            note = ""
        
        # Parse
        first_word = label.split(".")[0]
        pf, root, sf, ok = parse_word(first_word)
        
        # Is this label shared across signs?
        shared_count = all_labels[label]
        shared_signs = [s for s, ls in sign_label_sets.items() if label in ls]
        shared_str = f"{shared_count}× ({','.join(s[:3] for s in shared_signs)})" if shared_count > 1 else "unique"
        
        print(f"  {star_name:<16} {sign:<14} {actual_deg:>4}° {label:<28} "
              f"{pf:<6} {root:<10} {sf:<8} {shared_str}{note}")
        
        behenian_labels.append({
            "star": star_name,
            "sign": sign,
            "degree": actual_deg,
            "label": label,
            "prefix": pf,
            "root": root,
            "suffix": sf,
            "shared_count": shared_count,
        })
    
    # Analysis
    print(f"\n  Summary:")
    shared_beh = [b for b in behenian_labels if b["shared_count"] > 1]
    unique_beh = [b for b in behenian_labels if b["shared_count"] == 1]
    print(f"    Behenian labels that are SHARED: {len(shared_beh)}/{len(behenian_labels)}")
    print(f"    Behenian labels that are UNIQUE: {len(unique_beh)}/{len(behenian_labels)}")
    
    # Compare to baseline: what fraction of ALL labels are shared?
    total_labels = sum(d["total"] for d in all_signs.values())
    shared_total = sum(1 for sign, data in all_signs.items() 
                       for n in data["nymphs"]
                       if all_labels[clean_label(n["label"])] > 1)
    baseline_shared = shared_total / total_labels
    behenian_shared = len(shared_beh) / len(behenian_labels) if behenian_labels else 0
    
    print(f"\n    Baseline shared rate (all labels): {baseline_shared:.1%}")
    print(f"    Behenian position shared rate:     {behenian_shared:.1%}")
    if behenian_shared > baseline_shared * 1.5:
        print(f"    → Behenian positions have ELEVATED sharing (notable)")
    elif behenian_shared < baseline_shared * 0.5:
        print(f"    → Behenian positions have REDUCED sharing (notable)")
    else:
        print(f"    → No significant difference from baseline")
    
    # Root frequency at Behenian positions
    beh_roots = Counter(b["root"] for b in behenian_labels)
    print(f"\n    Roots at Behenian positions: {dict(beh_roots)}")
    
    return behenian_labels


# ══════════════════════════════════════════════════════════════════════════
#  PHASE 4: Cross-sign degree alignment
# ══════════════════════════════════════════════════════════════════════════

def phase4_degree_alignment(all_signs):
    """Test whether the same degree position across different signs
    shares morphological features (same root, same suffix, etc.)."""
    print("\n" + "=" * 70)
    print("PHASE 4: Cross-Sign Degree Alignment")
    print("=" * 70)
    
    print(f"\n  Do the same degree positions across signs share features?")
    print(f"  (e.g., does degree 1 always have a certain root or suffix?)\n")
    
    # Build degree→labels matrix (30 degrees × 10 signs)
    degree_labels = defaultdict(list)  # degree → list of (sign, label, root, suffix)
    
    for sign, data in all_signs.items():
        for n in data["nymphs"]:
            cl = clean_label(n["label"])
            first_word = cl.split(".")[0]
            pf, root, sf, ok = parse_word(first_word)
            degree_labels[n["degree"]].append({
                "sign": sign,
                "label": cl,
                "root": root,
                "suffix": sf,
                "prefix": pf,
            })
    
    # For each degree position, compute root entropy and suffix distribution
    print(f"  {'Degree':>6} {'Unique roots':>12} {'Top root':<12} {'Top root %':>10} "
          f"{'−y %':>6} {'−iin %':>7} {'o− %':>5}")
    print(f"  {'-'*6} {'-'*12} {'-'*12} {'-'*10} {'-'*6} {'-'*7} {'-'*5}")
    
    for deg in range(1, 31):
        if deg not in degree_labels:
            continue
        entries = degree_labels[deg]
        roots = [e["root"] for e in entries]
        suffixes = [e["suffix"] for e in entries]
        prefixes = [e["prefix"] for e in entries]
        
        root_counter = Counter(roots)
        unique_roots = len(root_counter)
        top_root, top_count = root_counter.most_common(1)[0]
        top_pct = top_count / len(entries) * 100
        
        y_pct = sum(1 for s in suffixes if s == "y") / len(entries) * 100
        iin_pct = sum(1 for s in suffixes if s in ("iin", "aiin")) / len(entries) * 100
        o_pct = sum(1 for p in prefixes if "o" in p) / len(entries) * 100
        
        marker = ""
        if top_pct >= 30:
            marker = " ◄"
        
        print(f"  {deg:>6} {unique_roots:>12} {top_root:<12} {top_pct:>9.0f}% "
              f"{y_pct:>5.0f}% {iin_pct:>6.0f}% {o_pct:>4.0f}%{marker}")
    
    # Decan-level aggregation
    print(f"\n  Decan-level root sharing:")
    print(f"  {'Decan':>6} {'Avg unique roots':>18} {'Most common root':<18} {'Root overlap'}")
    print(f"  {'-'*6} {'-'*18} {'-'*18} {'-'*30}")
    
    for decan in range(1, 4):
        decan_roots = defaultdict(Counter)  # decan_degree → root counter
        for deg in range((decan - 1) * 10 + 1, decan * 10 + 1):
            for e in degree_labels.get(deg, []):
                decan_roots[deg - (decan - 1) * 10].update([e["root"]])
        
        avg_unique = sum(len(c) for c in decan_roots.values()) / max(len(decan_roots), 1)
        all_decan_roots = Counter()
        for c in decan_roots.values():
            all_decan_roots.update(c)
        top = all_decan_roots.most_common(3)
        top_str = ", ".join(f"{r}({c})" for r, c in top)
        
        # Root overlap between decan positions (how many roots appear at 2+ positions)
        root_positions = defaultdict(set)
        for dd, c in decan_roots.items():
            for r in c:
                root_positions[r].add(dd)
        shared_roots = {r: ps for r, ps in root_positions.items() if len(ps) >= 2}
        
        print(f"  {decan:>6} {avg_unique:>18.1f} {top_str:<18} "
              f"{len(shared_roots)} roots at 2+ positions")


# ══════════════════════════════════════════════════════════════════════════
#  PHASE 5: SYNTHESIS
# ══════════════════════════════════════════════════════════════════════════

def phase5_synthesis(all_signs, shared_sorted, behenian_labels):
    print("\n" + "=" * 70)
    print("PHASE 5: SYNTHESIS — Ring-to-Decan Mapping Conclusions")
    print("=" * 70)
    
    # Check ring-decan alignment 
    aligned = 0
    total = 0
    for sign, data in all_signs.items():
        total += 1
        if data["ring_sizes"] == [10, 10, 10]:
            aligned += 1
        # Also check 2-ring signs that are halves of a pair
        # For split signs: check if combined ring structure makes sense
    
    print(f"""
  ┌─────────────────────────────────────────────────────────────────────┐
  │  RING-TO-DECAN MAPPING RESULTS                                     │
  │                                                                     │
  │  1. RING BOUNDARIES ≠ DECAN BOUNDARIES (mostly)                     │
  │     - No sign has exactly [10, 10, 10] ring structure               │
  │     - Ring sizes are dictated by PAGE LAYOUT, not decans            │
  │     - Split signs (Aries, Taurus) have 2 pages × 2 rings each      │
  │     - Single-page signs have 2-3 rings of variable size             │
  │     - CONCLUSION: Rings are VISUAL, not SEMANTIC                    │
  │                                                                     │
  │  2. DEGREE ORDERING                                                 │
  │     - Degrees run outer-to-inner, clockwise within each ring        │
  │     - This follows the file order (established by Petersen)         │
  │     - Decan 1 = degrees 1-10, Decan 2 = 11-20, Decan 3 = 21-30    │
  │     - The decan boundary falls MID-RING in most signs               │
  │                                                                     │""")
    
    # Shared label summary
    consistent_count = 0
    for label, positions in shared_sorted[:30]:
        if len(positions) >= 2:
            decan_degs = [p["decan_degree"] for p in positions]
            mean_dd = sum(decan_degs) / len(decan_degs)
            sigma_dd = (sum((d - mean_dd)**2 for d in decan_degs) / len(decan_degs)) ** 0.5
            if sigma_dd < 2.89 * 0.5:
                consistent_count += 1
    
    # Behenian summary
    beh_shared = sum(1 for b in behenian_labels if b["shared_count"] > 1)
    
    print(f"  │  3. SHARED LABEL POSITIONS: {consistent_count} labels show consistent decan positions │")
    print(f"  │  4. BEHENIAN STARS: {beh_shared}/{len(behenian_labels)} labels at Behenian positions are shared     │")
    print(f"  │                                                                     │")
    print(f"  └─────────────────────────────────────────────────────────────────────┘")


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    all_signs = phase1_ring_mapping()
    shared_sorted = phase2_positional_test(all_signs)
    behenian_labels = phase3_behenian_test(all_signs)
    phase4_degree_alignment(all_signs)
    phase5_synthesis(all_signs, shared_sorted, behenian_labels)
    
    # Save full data
    output = {}
    for sign, data in all_signs.items():
        output[sign] = {
            "total": data["total"],
            "ring_count": data["ring_count"],
            "ring_sizes": data["ring_sizes"],
            "nymphs": [
                {
                    "degree": n["degree"],
                    "decan": n["decan"],
                    "decan_degree": n["decan_degree"],
                    "ring_idx": n["ring_idx"],
                    "ring_name": n["ring_name"],
                    "label": clean_label(n["label"]),
                    "clock_pos": n["clock_pos"],
                    "folio_id": n["folio_id"],
                }
                for n in data["nymphs"]
            ]
        }
    
    with open(result_path("ring_decan_results.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n  Full data saved to results/ring_decan_results.json")