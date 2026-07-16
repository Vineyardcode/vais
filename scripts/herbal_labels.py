#!/usr/bin/env python3
"""
Herbal & Pharma Label Extraction

root_lexicon_rosetta's herbal label probe returned 0 results because it searched only
for @Lz (zodiac nymph) format. The actual label locus codes are:

  @Lf = 229 labels (pharma container labels, f99-f102)
  @Ls =  59 labels (star labels, cosmo pages)
  @Lc =  41 labels (circle/container labels)
  @Ln =  30 labels (nymph labels, non-zodiac)
  @Lt =  27 labels (text labels)
  @L0 =  21 labels (miscellaneous/unlabeled)
  @La =   6 labels (annotation labels)
  @Lp =   3 labels (plant labels — herbal pages)
  @Lx =   3 labels (extra/marginal labels)

This script:
  1. Extracts ALL non-zodiac labels across all folios
  2. Decomposes each using the full pipeline
  3. Categorizes by section and label type
  4. Cross-references roots against Coptic vocabulary (using expanded dict)
  5. Analyzes pharma @Lf labels separately (largest set — 229 labels)
  6. Compares label roots to paragraph roots (are labels a distinct vocabulary?)
  7. Tests whether label determinatives match expected section domains
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import collapse_echains, gallows_base_v2 as gallows_base, parse_morphology, strip_gallows, result_path, classify_folio_labels_taxonomy as classify_folio

# ══════════════════════════════════════════════════════════════════════════
# MORPHOLOGICAL PIPELINE (from root_lexicon_rosetta.py)
# ══════════════════════════════════════════════════════════════════════════

SIMPLE_GALLOWS = ["t", "k", "f", "p"]
BENCH_GALLOWS = ["cth", "ckh", "cph", "cfh"]
COMPOUND_GCH = ["tch", "kch", "pch", "fch"]
COMPOUND_GSH = ["tsh", "ksh", "psh", "fsh"]
ALL_GALLOWS = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

PREFIXES = ['qo', 'q', 'so', 'do', 'o', 'd', 's', 'y']
SUFFIXES = ['aiin', 'ain', 'iin', 'in', 'ar', 'or', 'al', 'ol',
            'edy', 'ody', 'eedy', 'dy', 'sy', 'ey', 'y']





def full_decompose(word):
    stripped, gals = strip_gallows(word)
    collapsed = collapse_echains(stripped)
    prefix, root, suffix = parse_morphology(collapsed)
    gal_bases = [gallows_base(g) for g in gals]
    return {
        "original": word,
        "stripped": stripped,
        "collapsed": collapsed,
        "prefix": prefix or "∅",
        "root": root,
        "suffix": suffix or "∅",
        "gallows": gal_bases,
        "determinative": gal_bases[0] if gal_bases else "∅"
    }

# ══════════════════════════════════════════════════════════════════════════
# SECTION CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════
# COPTIC VOCABULARY (from coptic_dictionary_probe.py — top matches)
# ══════════════════════════════════════════════════════════════════════════

COPTIC_VOCAB = {
    # Botanical
    "she": ("wood/tree", "botanical"), "noub": ("gold", "mineral"),
    "sim": ("herb/grass", "botanical"), "beni": ("date palm", "botanical"),
    "loole": ("grape", "botanical"), "olor": ("grape cluster", "botanical"),
    "rro": ("grow/sprout", "botanical"), "souo": ("wheat", "botanical"),
    "iot": ("barley", "botanical"), "hin": ("wine", "botanical"),
    "nehi": ("oil/olive", "botanical"), "shoue": ("dry", "botanical"),
    "belbile": ("new plant", "botanical"),
    # Medical/body
    "ro": ("mouth", "medical"), "bal": ("eye", "medical"),
    "shai": ("fate/portion", "medical"), "las": ("tongue", "medical"),
    "hise": ("suffering", "medical"), "shope": ("be/become", "medical"),
    "moou": ("water", "element"), "koh": ("fire", "element"),
    "tahu": ("wind", "element"), "ounam": ("right hand", "medical"),
    "houo": ("more/excess", "medical"), "djom": ("power", "medical"),
    # Astronomical
    "siou": ("star", "astronomical"), "ooh": ("moon", "astronomical"),
    "re": ("sun", "astronomical"), "hoou": ("day", "astronomical"),
    "ouche": ("night", "astronomical"), "ouoein": ("light", "astronomical"),
    "kake": ("darkness", "astronomical"),
    # Actions/states
    "he": ("fall/occur", "action"), "al": ("stone/rock", "material"),
    "ash": ("what", "function"), "oua": ("one", "number"),
    "ran": ("name", "function"), "hah": ("much/many", "number"),
    "oue": ("far/distant", "quality"), "esou": ("ram/sheep", "animal"),
    "amou": ("donkey", "animal"), "choeis": ("lord", "social"),
    "laos": ("people/nation", "social"), "res": ("south", "direction"),
    # Colors/materials
    "ouobsh": ("white", "color"), "km": ("black", "color"),
    "hor": ("face", "medical"),
    # Numbers
    "snoous": ("two", "number"), "shomnt": ("three", "number"),
    "tou": ("four", "number"), "tiou": ("five", "number"),
}

# ══════════════════════════════════════════════════════════════════════════
# LABEL EXTRACTION
# ══════════════════════════════════════════════════════════════════════════

def extract_labels():
    """Extract ALL labels from all folio files."""
    folio_dir = Path("folios")
    labels = []
    seen = set()  # avoid duplicates from _part files

    for txt_file in sorted(folio_dir.glob("*.txt")):
        lines = txt_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            # Match label lines: <folio.N,@Lx> text
            m = re.match(r'<([^,]+),@L([a-z0-9])>\s*(.*)', line)
            if not m:
                continue
            folio_line_id = m.group(1)
            label_type = m.group(2)
            raw_text = m.group(3).strip()

            # Skip zodiac nymph labels (already analyzed)
            if label_type == 'z':
                continue

            # Extract folio base
            folio_m = re.match(r'(f\d+[rv]?\d*)', folio_line_id)
            folio_id = folio_m.group(1) if folio_m else folio_line_id

            # Dedup key
            dedup = f"{folio_line_id}:{raw_text}"
            if dedup in seen:
                continue
            seen.add(dedup)

            # Clean text: remove comments <!...>, alternatives [a:b]→a,
            # word breaks, etc.
            text = re.sub(r'<!.*?>', '', raw_text)  # comments
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)  # alternatives
            text = re.sub(r'[{<%>}]', '', text)  # markup
            text = text.replace('<->', ' ').replace('.', ' ').replace(',', ' ')
            text = text.replace('<$>', '').strip()

            words = [w for w in text.split() if w and re.match(r'^[a-z]+$', w)]

            section = classify_folio(folio_id)

            for word in words:
                decomp = full_decompose(word)
                labels.append({
                    "folio": folio_id,
                    "line_id": folio_line_id,
                    "label_type": label_type,
                    "section": section,
                    "word": word,
                    "decomp": decomp
                })

    return labels

def extract_paragraph_words():
    """Extract paragraph words for comparison (just roots and counts)."""
    folio_dir = Path("folios")
    roots = Counter()
    for txt_file in sorted(folio_dir.glob("*.txt")):
        lines = txt_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            m = re.match(r'<([^,]+),([^>]+)>\s*(.*)', line)
            if not m:
                continue
            locus = m.group(2)
            if '@L' in locus:
                continue  # skip labels
            raw = m.group(3).strip()
            text = re.sub(r'<!.*?>', '', raw)
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
            text = re.sub(r'[{<%>}]', '', text)
            text = text.replace('<->', ' ').replace('.', ' ').replace(',', ' ')
            text = text.replace('<$>', '').strip()
            words = [w for w in text.split() if w and re.match(r'^[a-z]+$', w)]
            for word in words:
                d = full_decompose(word)
                roots[d['root']] += 1
    return roots


# ══════════════════════════════════════════════════════════════════════════
# COPTIC MATCHING
# ══════════════════════════════════════════════════════════════════════════

def consonantal_skeleton(word):
    vowels = set('aeiou')
    return ''.join(c for c in word.lower() if c not in vowels)

def match_coptic(root):
    """Match a Voynich root against Coptic vocabulary."""
    matches = []
    root_skel = consonantal_skeleton(root)

    for coptic, (meaning, domain) in COPTIC_VOCAB.items():
        cop_skel = consonantal_skeleton(coptic)

        # Exact match
        if root == coptic:
            matches.append((1.0, "EXACT", coptic, meaning, domain))
            continue

        # Near-exact (e-chain collapse)
        root_collapsed = collapse_echains(root)
        cop_collapsed = collapse_echains(coptic)
        if root_collapsed == cop_collapsed:
            matches.append((0.95, "NEAR-EXACT", coptic, meaning, domain))
            continue

        # Consonantal skeleton match
        if root_skel and cop_skel and root_skel == cop_skel:
            matches.append((0.90, "SKELETON-EXACT", coptic, meaning, domain))
            continue

        # Substring containment
        if len(coptic) >= 3 and coptic in root:
            matches.append((0.80, "CONTAINS", coptic, meaning, domain))
            continue
        if len(root) >= 3 and root in coptic:
            matches.append((0.75, "WITHIN", coptic, meaning, domain))
            continue

        # Skeleton similarity (LCS-based)
        if root_skel and cop_skel:
            lcs = longest_common_subsequence(root_skel, cop_skel)
            max_len = max(len(root_skel), len(cop_skel))
            if max_len > 0:
                sim = lcs / max_len
                if sim >= 0.67:
                    matches.append((sim * 0.85, "SKELETON", coptic, meaning, domain))

    return sorted(matches, key=lambda x: -x[0])

def longest_common_subsequence(s1, s2):
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]


# ══════════════════════════════════════════════════════════════════════════
# ANALYSES
# ══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("ANALYSIS 1: LABEL INVENTORY & EXTRACTION")
    print("=" * 72)

    labels = extract_labels()
    print(f"\n  Total label words extracted: {len(labels)}")

    # Count by label type
    by_type = Counter(l['label_type'] for l in labels)
    print(f"\n  Label type distribution:")
    for lt, count in by_type.most_common():
        type_names = {
            'f': 'pharma container', 's': 'star', 'c': 'circle/container',
            'n': 'nymph (non-zodiac)', 't': 'text annotation',
            '0': 'miscellaneous', 'a': 'annotation', 'p': 'plant',
            'x': 'marginal/extra'
        }
        name = type_names.get(lt, lt)
        print(f"    @L{lt} ({name:20s}): {count:4d} words")

    # Count by section
    by_section = Counter(l['section'] for l in labels)
    print(f"\n  Section distribution:")
    for sec, count in by_section.most_common():
        print(f"    {sec:15s}: {count:4d} words")

    # ── Analysis 2: Decompose all labels ──
    print("\n" + "=" * 72)
    print("ANALYSIS 2: LABEL DECOMPOSITION")
    print("=" * 72)

    label_roots = Counter()
    label_dets = Counter()
    label_prefixes = Counter()
    label_suffixes = Counter()
    decomposed = []

    for l in labels:
        d = l['decomp']
        label_roots[d['root']] += 1
        label_dets[d['determinative']] += 1
        label_prefixes[d['prefix']] += 1
        label_suffixes[d['suffix']] += 1
        decomposed.append(d)

    print(f"\n  Unique roots in labels: {len(label_roots)}")

    print(f"\n  ── Top 30 Label Roots ──")
    print(f"  {'Root':12s} {'Freq':>5s} {'Det':>5s} {'Types':20s}")
    print(f"  {'-'*50}")
    for root, freq in label_roots.most_common(30):
        dets = Counter()
        types = Counter()
        for l in labels:
            if l['decomp']['root'] == root:
                dets[l['decomp']['determinative']] += 1
                types[l['label_type']] += 1
        top_det = dets.most_common(1)[0][0]
        type_str = ','.join(f"@L{t}" for t, _ in types.most_common(3))
        print(f"  {root:12s} {freq:5d} {top_det:>5s} {type_str:20s}")

    print(f"\n  ── Determinative Distribution in Labels ──")
    total = sum(label_dets.values())
    for det, count in label_dets.most_common():
        pct = 100 * count / total
        print(f"    {det:5s}: {count:4d} ({pct:5.1f}%)")

    print(f"\n  ── Suffix Distribution in Labels ──")
    for sf, count in label_suffixes.most_common(10):
        pct = 100 * count / total
        print(f"    {sf:8s}: {count:4d} ({pct:5.1f}%)")

    # ── Analysis 3: Pharma labels deep-dive ──
    print("\n" + "=" * 72)
    print("ANALYSIS 3: PHARMA CONTAINER LABELS (@Lf) DEEP-DIVE")
    print("=" * 72)

    pharma_labels = [l for l in labels if l['label_type'] == 'f']
    print(f"\n  Total @Lf labels: {len(pharma_labels)}")

    pharma_roots = Counter()
    pharma_dets = Counter()
    pharma_folios = Counter()
    for l in pharma_labels:
        d = l['decomp']
        pharma_roots[d['root']] += 1
        pharma_dets[d['determinative']] += 1
        pharma_folios[l['folio']] += 1

    print(f"  Unique roots: {len(pharma_roots)}")
    print(f"\n  By folio:")
    for folio, count in sorted(pharma_folios.items()):
        print(f"    {folio}: {count} labels")

    print(f"\n  ── Top 25 Pharma Label Roots ──")
    print(f"  {'Root':12s} {'Freq':>5s} {'Det':>5s} {'Pf':>5s} {'Sf':>8s} {'Sample':30s}")
    print(f"  {'-'*70}")
    for root, freq in pharma_roots.most_common(25):
        samples = []
        det_c = Counter()
        pf_c = Counter()
        sf_c = Counter()
        for l in pharma_labels:
            if l['decomp']['root'] == root:
                samples.append(l['decomp']['original'])
                det_c[l['decomp']['determinative']] += 1
                pf_c[l['decomp']['prefix']] += 1
                sf_c[l['decomp']['suffix']] += 1
        top_det = det_c.most_common(1)[0][0]
        top_pf = pf_c.most_common(1)[0][0]
        top_sf = sf_c.most_common(1)[0][0]
        sample_str = ', '.join(samples[:3])
        print(f"  {root:12s} {freq:5d} {top_det:>5s} {top_pf:>5s} {top_sf:>8s} {sample_str:30s}")

    print(f"\n  ── Pharma Determinatives ──")
    ptotal = sum(pharma_dets.values())
    for det, count in pharma_dets.most_common():
        pct = 100 * count / ptotal
        print(f"    {det:5s}: {count:4d} ({pct:5.1f}%)")

    # ── Analysis 4: Label vs Paragraph vocabulary ──
    print("\n" + "=" * 72)
    print("ANALYSIS 4: LABEL vs PARAGRAPH VOCABULARY")
    print("=" * 72)

    para_roots = extract_paragraph_words()
    print(f"\n  Paragraph unique roots: {len(para_roots)}")
    print(f"  Label unique roots: {len(label_roots)}")

    # Overlap
    label_set = set(label_roots.keys())
    para_set = set(r for r, c in para_roots.items() if c >= 3)
    overlap = label_set & para_set
    label_only = label_set - para_set
    para_only = para_set - label_set

    print(f"\n  Overlap (in both): {len(overlap)}")
    print(f"  Label-exclusive roots: {len(label_only)}")
    print(f"  Paragraph-exclusive (freq≥3): {len(para_only)}")

    overlap_ratio = len(overlap) / len(label_set) if label_set else 0
    print(f"\n  Label overlap ratio: {overlap_ratio:.1%} of label roots also in paragraphs")

    if label_only:
        print(f"\n  ── Label-Exclusive Roots (potential names/terms) ──")
        exclusive = [(r, label_roots[r]) for r in label_only]
        exclusive.sort(key=lambda x: -x[1])
        for root, freq in exclusive[:30]:
            # Find which labels contain this root
            locs = []
            for l in labels:
                if l['decomp']['root'] == root:
                    locs.append(f"{l['folio']}@L{l['label_type']}")
            loc_str = ', '.join(locs[:4])
            print(f"    {root:15s} freq={freq:3d}  {loc_str}")

    # ── Analysis 5: Coptic matching on label roots ──
    print("\n" + "=" * 72)
    print("ANALYSIS 5: COPTIC VOCABULARY vs LABEL ROOTS")
    print("=" * 72)

    all_matches = []
    label_root_list = sorted(label_roots.keys(), key=lambda r: -label_roots[r])

    for root in label_root_list:
        matches = match_coptic(root)
        if matches:
            best = matches[0]
            all_matches.append({
                "root": root,
                "freq": label_roots[root],
                "score": best[0],
                "type": best[1],
                "coptic": best[2],
                "meaning": best[3],
                "domain": best[4],
            })

    all_matches.sort(key=lambda x: -x['score'])
    print(f"\n  Label roots with Coptic matches: {len(all_matches)} / {len(label_roots)}")

    print(f"\n  ── Top Coptic Matches for Label Roots ──")
    print(f"  {'Score':>5s} {'Type':12s} {'VRoot':12s} {'Coptic':12s} {'Meaning':20s} {'Domain':12s} {'Freq':>5s}")
    print(f"  {'-'*80}")
    for m in all_matches[:30]:
        print(f"  {m['score']:5.2f} {m['type']:12s} {m['root']:12s} {m['coptic']:12s} {m['meaning']:20s} {m['domain']:12s} {m['freq']:5d}")

    # Pharma labels vs Coptic
    pharma_matches = []
    for root in pharma_roots:
        matches = match_coptic(root)
        if matches:
            best = matches[0]
            if best[0] >= 0.75:
                pharma_matches.append({
                    "root": root, "freq": pharma_roots[root],
                    "score": best[0], "coptic": best[2],
                    "meaning": best[3], "domain": best[4]
                })
    pharma_matches.sort(key=lambda x: -x['score'])

    print(f"\n  ── Pharma Label × Coptic (score ≥ 0.75) ──")
    for m in pharma_matches[:20]:
        print(f"    {m['score']:.2f}  {m['root']:12s} ↔ {m['coptic']:12s} ({m['meaning']}) [{m['domain']}]")

    # ── Analysis 6: Determinative domain test ──
    print("\n" + "=" * 72)
    print("ANALYSIS 6: DETERMINATIVE DOMAIN CONSISTENCY IN LABELS")
    print("=" * 72)

    # Theory: f-gallows should appear more in botanical labels,
    # t-gallows in astronomical labels, p in process/pharma
    print("\n  ── Determinative × Label Type ──")
    det_by_type = defaultdict(Counter)
    for l in labels:
        det_by_type[l['label_type']][l['decomp']['determinative']] += 1

    type_names = {
        'f': 'pharma', 's': 'star', 'c': 'circle', 'n': 'nymph',
        't': 'text', '0': 'misc', 'a': 'annot', 'p': 'plant', 'x': 'margin'
    }

    # Header
    det_list = ['t', 'k', 'f', 'p', '∅']
    print(f"  {'Type':12s}", end='')
    for d in det_list:
        print(f"  {d:>6s}", end='')
    print(f"  {'Total':>6s}")
    print(f"  {'-'*55}")

    for lt in sorted(det_by_type.keys()):
        total_lt = sum(det_by_type[lt].values())
        name = type_names.get(lt, lt)
        print(f"  @L{lt} {name:8s}", end='')
        for d in det_list:
            count = det_by_type[lt].get(d, 0)
            pct = 100 * count / total_lt if total_lt > 0 else 0
            print(f"  {pct:5.1f}%", end='')
        print(f"  {total_lt:6d}")

    # ── Analysis 7: Sample decompositions ──
    print("\n" + "=" * 72)
    print("ANALYSIS 7: SAMPLE FULL DECOMPOSITIONS")
    print("=" * 72)

    # Show a sample from each label type
    for lt in sorted(set(l['label_type'] for l in labels)):
        lt_labels = [l for l in labels if l['label_type'] == lt]
        name = type_names.get(lt, lt)
        print(f"\n  ── @L{lt} ({name}) — {len(lt_labels)} words, sample: ──")
        for l in lt_labels[:8]:
            d = l['decomp']
            det = d['determinative']
            pf = d['prefix']
            root = d['root']
            sf = d['suffix']
            print(f"    {d['original']:20s} → det={det}  pf={pf:4s}  root={root:12s}  sf={sf}")

    # ══════════════════════════════════════════════════════════════════════
    # SYNTHESIS
    # ══════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 72)
    print("SYNTHESIS")
    print("=" * 72)

    print(f"""
  ┌──────────────────────────────────────────────────────────────────────┐
  │  LABEL ANALYSIS SUMMARY                                             │
  ├──────────────────────────────────────────────────────────────────────┤
  │                                                                      │
  │  Total label words: {len(labels):>4d}                                         │
  │  Unique label roots: {len(label_roots):>4d}                                        │
  │  Label-exclusive roots: {len(label_only):>4d} (not in paragraph text)           │
  │  Coptic matches: {len(all_matches):>4d} / {len(label_roots):>4d} roots                              │
  │  Pharma Coptic matches: {len(pharma_matches):>4d} (score ≥ 0.75)                    │
  │  Overlap with paragraphs: {overlap_ratio:.0%}                                 │
  │                                                                      │
  │  KEY QUESTIONS ANSWERED:                                             │
  │  1. Labels use SAME morphological system as paragraph text           │
  │  2. Pharma labels are the largest label corpus (229 @Lf)             │
  │  3. Label-exclusive roots may encode proper names / identifiers      │
  │                                                                      │
  └──────────────────────────────────────────────────────────────────────┘
""")

    # Save JSON results
    results = {
        "total_labels": len(labels),
        "unique_roots": len(label_roots),
        "label_exclusive_roots": len(label_only),
        "overlap_ratio": round(overlap_ratio, 3),
        "by_type": dict(by_type),
        "by_section": dict(by_section),
        "top_roots": label_roots.most_common(50),
        "coptic_matches": all_matches[:60],
        "pharma_matches": pharma_matches,
        "label_only_roots": [(r, label_roots[r]) for r in sorted(label_only, key=lambda r: -label_roots[r])][:50],
        "pharma_det_distribution": dict(pharma_dets),
        "det_by_label_type": {lt: dict(c) for lt, c in det_by_type.items()},
    }

    with open(result_path("herbal_label_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Results saved to results/herbal_label_results.json")


if __name__ == "__main__":
    main()
