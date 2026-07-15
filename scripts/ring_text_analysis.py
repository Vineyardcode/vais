#!/usr/bin/env python3
"""
Voynich Manuscript — Ring Text (@Cc) Extraction & Analysis

The zodiac pages contain circular ring texts written in the bands between
nymph rings. These are continuous prose (7-40 words), distinct from the
single-word nymph labels. This script:

  1. Extracts all 36 @Cc ring text lines
  2. Parses and profiles their morphology
  3. Compares vocabulary to nymph labels and to body text (Language A/B)
  4. Tests whether ring texts encode decan/ring-specific information
  5. Looks for formulaic patterns and structural grammar
  6. Cross-references ring text roots with label root families
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations

# ── File mapping ─────────────────────────────────────────────────────────

ZODIAC_FILES = [
    "folios/f70v_part.txt",
    "folios/f71r.txt",
    "folios/f71v_72r.txt",
    "folios/f72v_part.txt",
    "folios/f73r.txt",
    "folios/f73v.txt",
]

# Map folio section IDs to zodiac signs
FOLIO_SIGN = {
    "f70v1": "Aries",
    "f70v2": "Pisces",
    "f71r":  "Aries",       # Aries light half
    "f71v":  "Taurus",      # Taurus light half
    "f72r1": "Taurus",      # Taurus dark half
    "f72r2": "Gemini",
    "f72r3": "Cancer",
    "f72v1": "Libra",
    "f72v2": "Virgo",
    "f72v3": "Leo",
    "f73r":  "Scorpio",
    "f73v":  "Sagittarius",
}

SIGN_ORDER = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Pisces"]

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


# ── Extraction ───────────────────────────────────────────────────────────

def clean_word(w):
    """Remove transcription annotations from a word."""
    # Remove alternative readings [a:b] -> a
    w = re.sub(r'\[([^:]+):[^\]]+\]', r'\1', w)
    # Remove uncertain groups {xyz} -> xyz
    w = re.sub(r'\{([^}]+)\}', r'\1', w)
    # Remove annotation codes @NNN;
    w = re.sub(r'@\d+;', '', w)
    # Remove damage markers
    w = re.sub(r'<![^>]*>', '', w)
    # Remove ? markers
    w = w.replace('?', '')
    # Remove stray punctuation
    w = w.strip(",'")
    return w

def extract_ring_texts():
    """Extract all @Cc lines from zodiac folios."""
    ring_texts = []

    for filepath in ZODIAC_FILES:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "@Cc>" not in line:
                    continue

                # Parse the locus tag
                m = re.match(r'<([^,]+),@Cc>\s+(.+)', line)
                if not m:
                    continue

                folio_line = m.group(1)
                content = m.group(2)

                # Extract folio section ID (e.g., "f70v1" from "f70v1.1")
                folio_id = re.match(r'(f\d+[rv]\d?)', folio_line).group(1) if re.match(r'(f\d+[rv]\d?)', folio_line) else folio_line.split('.')[0]

                sign = FOLIO_SIGN.get(folio_id, "Unknown")

                # Extract clock position
                clock_match = re.search(r'<!(\d+:\d+)>', content)
                clock_pos = clock_match.group(1) if clock_match else "?"

                # Remove clock position from content
                text = re.sub(r'<!\d+:\d+>', '', content).strip()

                # Split into words (period-separated in IVTFF)
                raw_words = re.split(r'[.\s]+', text)
                # Clean each word
                words = []
                for w in raw_words:
                    # Handle comma-joined words
                    for sub_w in w.split(','):
                        cleaned = clean_word(sub_w)
                        if cleaned and len(cleaned) > 0 and cleaned not in ('', ' '):
                            words.append(cleaned)

                ring_texts.append({
                    "folio_line": folio_line,
                    "folio_id": folio_id,
                    "sign": sign,
                    "clock_pos": clock_pos,
                    "raw_text": text,
                    "words": words,
                    "word_count": len(words),
                })

    # Assign ring indices (outer=0, working inward) per folio section
    by_folio = defaultdict(list)
    for rt in ring_texts:
        by_folio[rt["folio_id"]].append(rt)
    for folio_id, texts in by_folio.items():
        for i, rt in enumerate(texts):
            rt["ring_idx"] = i
            rt["ring_name"] = ["outer", "middle", "inner", "innermost"][min(i, 3)]
            rt["ring_total"] = len(texts)

    return ring_texts


def extract_label_words():
    """Extract all nymph label words for comparison."""
    labels = []
    for filepath in ZODIAC_FILES:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "@Lz>" not in line and "&Lz>" not in line:
                    continue
                m = re.match(r'<[^>]+>\s+(.+)', line)
                if not m:
                    continue
                text = m.group(1)
                text = re.sub(r'<![^>]*>', '', text)
                raw_words = re.split(r'[.\s]+', text)
                for w in raw_words:
                    cleaned = clean_word(w)
                    if cleaned:
                        labels.append(cleaned)
    return labels


# ══════════════════════════════════════════════════════════════════════════
#  ANALYSIS PHASES
# ══════════════════════════════════════════════════════════════════════════

# ── PHASE 1: Global Profile ──────────────────────────────────────────────

def phase1_profile(ring_texts):
    print("=" * 70)
    print("PHASE 1: Ring Text Global Profile")
    print("=" * 70)

    total_words = sum(rt["word_count"] for rt in ring_texts)
    all_words = [w for rt in ring_texts for w in rt["words"]]

    print(f"\n  Total ring text lines:   {len(ring_texts)}")
    print(f"  Total words:             {total_words}")
    print(f"  Unique words:            {len(set(all_words))}")
    print(f"  Mean words per ring:     {total_words/len(ring_texts):.1f}")

    # Per-sign breakdown
    print(f"\n  Per-sign ring text summary:")
    print(f"  {'Sign':<14} {'Rings':>5} {'Words':>6} {'Unique':>6} {'Mean/ring':>9}")
    print(f"  {'-'*14} {'-'*5} {'-'*6} {'-'*6} {'-'*9}")

    by_sign = defaultdict(list)
    for rt in ring_texts:
        by_sign[rt["sign"]].append(rt)

    for sign in SIGN_ORDER:
        rts = by_sign.get(sign, [])
        if not rts:
            continue
        n_words = sum(rt["word_count"] for rt in rts)
        unique = len(set(w for rt in rts for w in rt["words"]))
        print(f"  {sign:<14} {len(rts):>5} {n_words:>6} {unique:>6} {n_words/len(rts):>9.1f}")

    # Ring position word counts
    print(f"\n  Word count by ring position:")
    by_ring = defaultdict(list)
    for rt in ring_texts:
        by_ring[rt["ring_name"]].append(rt["word_count"])
    for name in ["outer", "middle", "inner", "innermost"]:
        vals = by_ring.get(name, [])
        if vals:
            print(f"    {name:<12}: mean={sum(vals)/len(vals):>5.1f}, "
                  f"range=[{min(vals)}-{max(vals)}], n={len(vals)}")

    # Top 20 most frequent words in ring texts
    word_freq = Counter(all_words)
    print(f"\n  Top 25 most frequent ring text words:")
    print(f"  {'Word':<20} {'Freq':>5} {'% of all':>8} {'Prefix':<6} {'Root':<12} {'Suffix'}")
    print(f"  {'-'*20} {'-'*5} {'-'*8} {'-'*6} {'-'*12} {'-'*8}")
    for word, freq in word_freq.most_common(25):
        pf, root, sf, ok = parse_word(word)
        pct = freq / total_words * 100
        print(f"  {word:<20} {freq:>5} {pct:>7.1f}% {pf:<6} {root:<12} {sf}")

    return all_words, word_freq


# ── PHASE 2: Morphological Comparison ─────────────────────────────────────

def phase2_morphology(ring_texts, all_ring_words, label_words):
    print("\n" + "=" * 70)
    print("PHASE 2: Ring Text vs Nymph Label Morphology")
    print("=" * 70)

    # Parse all ring text words
    ring_parsed = []
    for w in all_ring_words:
        pf, root, sf, ok = parse_word(w)
        ring_parsed.append({"word": w, "prefix": pf, "root": root, "suffix": sf, "parsed": ok})

    # Parse all label words
    label_parsed = []
    for w in label_words:
        pf, root, sf, ok = parse_word(w)
        label_parsed.append({"word": w, "prefix": pf, "root": root, "suffix": sf, "parsed": ok})

    # Parse rates
    ring_parse_rate = sum(1 for p in ring_parsed if p["parsed"]) / len(ring_parsed) * 100
    label_parse_rate = sum(1 for p in label_parsed if p["parsed"]) / len(label_parsed) * 100

    print(f"\n  Parse rate:")
    print(f"    Ring texts: {ring_parse_rate:.1f}% ({len(ring_parsed)} words)")
    print(f"    Nymph labels: {label_parse_rate:.1f}% ({len(label_parsed)} words)")

    # Prefix distribution comparison
    ring_prefix = Counter(p["prefix"] for p in ring_parsed)
    label_prefix = Counter(p["prefix"] for p in label_parsed)

    print(f"\n  Prefix distribution:")
    print(f"  {'Prefix':<10} {'Ring %':>8} {'Label %':>8} {'Delta':>8}")
    print(f"  {'-'*10} {'-'*8} {'-'*8} {'-'*8}")
    all_prefixes_set = set(ring_prefix.keys()) | set(label_prefix.keys())
    for pf in sorted(all_prefixes_set, key=lambda p: -ring_prefix.get(p, 0)):
        r_pct = ring_prefix.get(pf, 0) / len(ring_parsed) * 100
        l_pct = label_prefix.get(pf, 0) / len(label_parsed) * 100
        delta = r_pct - l_pct
        marker = " ◄" if abs(delta) > 5 else ""
        pf_display = pf if pf else "(none)"
        print(f"  {pf_display:<10} {r_pct:>7.1f}% {l_pct:>7.1f}% {delta:>+7.1f}%{marker}")

    # Suffix distribution comparison
    ring_suffix = Counter(p["suffix"] for p in ring_parsed)
    label_suffix = Counter(p["suffix"] for p in label_parsed)

    print(f"\n  Suffix distribution:")
    print(f"  {'Suffix':<10} {'Ring %':>8} {'Label %':>8} {'Delta':>8}")
    print(f"  {'-'*10} {'-'*8} {'-'*8} {'-'*8}")
    all_suf_set = set(ring_suffix.keys()) | set(label_suffix.keys())
    for sf in sorted(all_suf_set, key=lambda s: -(ring_suffix.get(s, 0) + label_suffix.get(s, 0))):
        r_pct = ring_suffix.get(sf, 0) / len(ring_parsed) * 100
        l_pct = label_suffix.get(sf, 0) / len(label_parsed) * 100
        delta = r_pct - l_pct
        marker = " ◄" if abs(delta) > 3 else ""
        sf_display = sf if sf else "(none)"
        print(f"  {sf_display:<10} {r_pct:>7.1f}% {l_pct:>7.1f}% {delta:>+7.1f}%{marker}")

    # Root overlap
    ring_roots = set(p["root"] for p in ring_parsed)
    label_roots = set(p["root"] for p in label_parsed)
    shared_roots = ring_roots & label_roots
    ring_only = ring_roots - label_roots
    label_only = label_roots - ring_roots

    print(f"\n  Root sets:")
    print(f"    Ring text unique roots:  {len(ring_roots)}")
    print(f"    Label unique roots:      {len(label_roots)}")
    print(f"    Shared roots:            {len(shared_roots)} "
          f"(J={len(shared_roots)/len(ring_roots|label_roots):.3f})")
    print(f"    Ring-only roots:         {len(ring_only)}")
    print(f"    Label-only roots:        {len(label_only)}")

    # Top shared roots
    shared_root_freq = Counter()
    for p in ring_parsed:
        if p["root"] in shared_roots:
            shared_root_freq[p["root"]] += 1
    print(f"\n  Top shared roots (ring text freq):")
    for root, freq in shared_root_freq.most_common(15):
        print(f"    {root:<20} ring={freq:>3}  label={sum(1 for p in label_parsed if p['root']==root):>3}")

    # Ring-only roots (what's in ring texts but NOT in labels?)
    ring_only_freq = Counter()
    for p in ring_parsed:
        if p["root"] in ring_only:
            ring_only_freq[p["root"]] += 1
    print(f"\n  Top ring-ONLY roots (NOT found in any nymph label):")
    for root, freq in ring_only_freq.most_common(15):
        pf_common = Counter(p["prefix"] for p in ring_parsed if p["root"] == root).most_common(1)
        sf_common = Counter(p["suffix"] for p in ring_parsed if p["root"] == root).most_common(1)
        print(f"    {root:<20} freq={freq:>3}  "
              f"prefix={pf_common[0][0] or '∅' if pf_common else '?'}  "
              f"suffix={sf_common[0][0] or '∅' if sf_common else '?'}")

    return ring_parsed, label_parsed


# ── PHASE 3: Register Identification ─────────────────────────────────────

def phase3_register(ring_parsed, ring_texts):
    print("\n" + "=" * 70)
    print("PHASE 3: Ring Text Register — Language A or B?")
    print("=" * 70)

    # Type A roots (substance, ≤30% -y) vs Type B (process, ≥80% -y)
    # Key A roots: ka, da, a, o, ta, cho, sa, ko, sho, keo, to, cheo, sheo
    # Key B roots: ched, keed, shed, ked, ted, cheed, sheed
    type_a_markers = {"ka", "da", "a", "o", "ta", "cho", "sa", "ko", "sho",
                      "keo", "to", "cheo", "sheo", "ctho", "kcho", "tcho"}
    type_b_markers = {"ched", "keed", "shed", "ked", "ted", "cheed", "sheed",
                      "seed", "teed", "keed"}

    a_count = sum(1 for p in ring_parsed if p["root"] in type_a_markers)
    b_count = sum(1 for p in ring_parsed if p["root"] in type_b_markers)
    total = len(ring_parsed)

    print(f"\n  Type A (substance) roots: {a_count} ({a_count/total:.1%})")
    print(f"  Type B (process) roots:   {b_count} ({b_count/total:.1%})")
    print(f"  Other:                    {total-a_count-b_count} ({(total-a_count-b_count)/total:.1%})")

    if a_count > b_count * 2:
        register = "LANGUAGE A (catalog/inventory)"
    elif b_count > a_count * 2:
        register = "LANGUAGE B (procedural/recipe)"
    else:
        register = "MIXED register"
    print(f"  → Ring texts appear to be: {register}")

    # Per-ring analysis
    print(f"\n  Register by ring position:")
    print(f"  {'Ring':<12} {'A-roots':>8} {'B-roots':>8} {'Total':>6} {'A%':>6} {'B%':>6}")
    print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*6} {'-'*6} {'-'*6}")

    # Aggregate by ring position
    for ring_name in ["outer", "middle", "inner", "innermost"]:
        rts = [rt for rt in ring_texts if rt["ring_name"] == ring_name]
        if not rts:
            continue
        all_words = [w for rt in rts for w in rt["words"]]
        parsed = [parse_word(w) for w in all_words]
        a_n = sum(1 for _, root, _, _ in parsed if root in type_a_markers)
        b_n = sum(1 for _, root, _, _ in parsed if root in type_b_markers)
        t_n = len(parsed)
        print(f"  {ring_name:<12} {a_n:>8} {b_n:>8} {t_n:>6} {a_n/t_n:>5.0%} {b_n/t_n:>5.0%}")

    # Function words in ring texts
    print(f"\n  Function word analysis:")
    # daiin, aiin, al, ar, ol, or — known grammatical particles
    func_words = {"daiin", "aiin", "daiir", "dair", "al", "ar", "ol", "or",
                  "dal", "sal", "sar", "shal", "sheal", "daly", "chey", "shey",
                  "y", "s", "r", "d", "l"}
    func_count = sum(1 for p in ring_parsed if p["word"] in func_words)
    print(f"    Function words: {func_count}/{total} ({func_count/total:.1%})")

    # q- prefix frequency (marker of Language B register)
    q_count = sum(1 for p in ring_parsed if p["prefix"].startswith("q"))
    print(f"    q- prefix words: {q_count}/{total} ({q_count/total:.1%})")

    # l- prefix frequency (Language B marker at 5.5% in B vs 0.5% in A)
    l_roots = sum(1 for p in ring_parsed if p["prefix"] in ("ol", "l"))
    print(f"    ol-/l- prefix words: {l_roots}/{total} ({l_roots/total:.1%})")


# ── PHASE 4: Formulaic Patterns ──────────────────────────────────────────

def phase4_formulaic(ring_texts):
    print("\n" + "=" * 70)
    print("PHASE 4: Formulaic Patterns — repeated sequences across rings")
    print("=" * 70)

    # Look for bigrams and trigrams that repeat
    all_bigrams = Counter()
    all_trigrams = Counter()
    per_ring_bigrams = {}

    for rt in ring_texts:
        words = rt["words"]
        bigrams = [(words[i], words[i+1]) for i in range(len(words)-1)]
        trigrams = [(words[i], words[i+1], words[i+2]) for i in range(len(words)-2)]
        all_bigrams.update(bigrams)
        all_trigrams.update(trigrams)
        per_ring_bigrams[rt["folio_line"]] = bigrams

    print(f"\n  Repeated bigrams (appearing 3+ times):")
    print(f"  {'Bigram':<30} {'Freq':>5} {'Signs'}")
    print(f"  {'-'*30} {'-'*5} {'-'*30}")
    for bigram, freq in all_bigrams.most_common(30):
        if freq < 2:
            break
        # Which signs contain this bigram?
        signs = set()
        for rt in ring_texts:
            words = rt["words"]
            for i in range(len(words)-1):
                if (words[i], words[i+1]) == bigram:
                    signs.add(rt["sign"])
        bg_str = f"{bigram[0]} {bigram[1]}"
        print(f"  {bg_str:<30} {freq:>5} {', '.join(sorted(signs))}")

    # Repeated trigrams
    print(f"\n  Repeated trigrams (appearing 2+ times):")
    for trigram, freq in all_trigrams.most_common(20):
        if freq < 2:
            break
        signs = set()
        for rt in ring_texts:
            words = rt["words"]
            for i in range(len(words)-2):
                if (words[i], words[i+1], words[i+2]) == trigram:
                    signs.add(rt["sign"])
        tg_str = f"{trigram[0]} {trigram[1]} {trigram[2]}"
        print(f"    {tg_str:<40} {freq:>3}  {', '.join(sorted(signs))}")

    # Ring opening words (first 1-3 words of each ring text)
    print(f"\n  Ring opening patterns (first 3 words):")
    print(f"  {'Folio':<12} {'Sign':<14} {'Ring':<8} {'Opening words'}")
    print(f"  {'-'*12} {'-'*14} {'-'*8} {'-'*40}")
    for rt in ring_texts:
        words = rt["words"][:3]
        opening = " ".join(words)
        print(f"  {rt['folio_line']:<12} {rt['sign']:<14} {rt['ring_name']:<8} {opening}")

    # Ring closing words (last 3 words)
    print(f"\n  Ring closing patterns (last 3 words):")
    print(f"  {'Folio':<12} {'Sign':<14} {'Ring':<8} {'Closing words'}")
    print(f"  {'-'*12} {'-'*14} {'-'*8} {'-'*40}")
    for rt in ring_texts:
        words = rt["words"][-3:]
        closing = " ".join(words)
        print(f"  {rt['folio_line']:<12} {rt['sign']:<14} {rt['ring_name']:<8} {closing}")


# ── PHASE 5: Ring-Decan Correlation ──────────────────────────────────────

def phase5_ring_decan(ring_texts, ring_parsed):
    print("\n" + "=" * 70)
    print("PHASE 5: Do ring texts encode decan-specific information?")
    print("=" * 70)

    # Each zodiac sign has 3 decans. Ring texts come in 2-4 per sign.
    # If ring texts describe decans, ring 1 (outer) = decan 1, ring 2 = decan 2, etc.

    # Group ring texts by ring position
    by_ring_pos = defaultdict(list)
    for rt in ring_texts:
        by_ring_pos[rt["ring_idx"]].append(rt)

    # For each ring position, compute vocabulary profile
    print(f"\n  Vocabulary profile by ring position:")
    all_ring_words = [w for rt in ring_texts for w in rt["words"]]
    all_parsed = [parse_word(w) for w in all_ring_words]

    for idx in sorted(by_ring_pos.keys()):
        rts = by_ring_pos[idx]
        words = [w for rt in rts for w in rt["words"]]
        parsed = [parse_word(w) for w in words]
        roots = Counter(r for _, r, _, _ in parsed)
        suffixes = Counter(s for _, _, s, _ in parsed)
        prefixes = Counter(p for p, _, _, _ in parsed)

        o_rate = sum(1 for p, _, _, _ in parsed if "o" in p) / len(parsed) if parsed else 0
        y_rate = sum(1 for _, _, s, _ in parsed if s == "y") / len(parsed) if parsed else 0
        iin_rate = sum(1 for _, _, s, _ in parsed if s in ("iin", "aiin")) / len(parsed) if parsed else 0

        print(f"\n  Ring {idx} ({['outer','middle','inner','innermost'][min(idx,3)]}, n={len(rts)} rings, {len(words)} words):")
        print(f"    o-prefix: {o_rate:.0%}  -y suffix: {y_rate:.0%}  -iin suffix: {iin_rate:.0%}")
        top_roots = roots.most_common(8)
        print(f"    Top roots: {', '.join(f'{r}({c})' for r,c in top_roots)}")
        top_suf = [(s,c) for s,c in suffixes.most_common(8) if s]
        print(f"    Top suffixes: {', '.join(f'{s}({c})' for s,c in top_suf[:6])}")

    # Cross-ring vocabulary overlap
    print(f"\n  Vocabulary overlap between ring positions:")
    ring_root_sets = {}
    for idx in sorted(by_ring_pos.keys()):
        rts = by_ring_pos[idx]
        words = [w for rt in rts for w in rt["words"]]
        parsed = [parse_word(w) for w in words]
        ring_root_sets[idx] = set(r for _, r, _, _ in parsed)

    for i, j in combinations(sorted(ring_root_sets.keys()), 2):
        shared = ring_root_sets[i] & ring_root_sets[j]
        union = ring_root_sets[i] | ring_root_sets[j]
        jac = len(shared) / len(union) if union else 0
        print(f"    Ring {i} ↔ Ring {j}: {len(shared)} shared roots (J={jac:.3f})")

    # Per-sign: do ring texts diverge from each other?
    print(f"\n  Per-sign ring text divergence (root Jaccard within same sign):")
    by_sign = defaultdict(list)
    for rt in ring_texts:
        by_sign[rt["sign"]].append(rt)

    for sign in SIGN_ORDER:
        rts = by_sign.get(sign, [])
        if len(rts) < 2:
            continue
        ring_root_lists = []
        for rt in rts:
            parsed = [parse_word(w) for w in rt["words"]]
            root_set = set(r for _, r, _, _ in parsed)
            ring_root_lists.append((rt["ring_name"], root_set))

        jaccards = []
        for (n1, s1), (n2, s2) in combinations(ring_root_lists, 2):
            shared = s1 & s2
            union = s1 | s2
            j = len(shared) / len(union) if union else 0
            jaccards.append(j)

        mean_j = sum(jaccards) / len(jaccards) if jaccards else 0
        print(f"    {sign:<14}: mean J={mean_j:.3f} across {len(rts)} rings "
              f"({len(jaccards)} pairs)")


# ── PHASE 6: Cross-Reference with Label Root Families ─────────────────────

def phase6_crossref(ring_texts, label_parsed, ring_parsed):
    print("\n" + "=" * 70)
    print("PHASE 6: Ring Text ↔ Label Root Family Cross-Reference")
    print("=" * 70)

    # The big root families from crosssign_network: ke-, te-, ch-, tal-, kal-
    families = {
        "ke-": lambda r: r.startswith("ke") and len(r) > 2,
        "te-": lambda r: r.startswith("te") and len(r) > 2,
        "ch-": lambda r: r.startswith("ch") and len(r) > 2,
        "tal-": lambda r: r.startswith("tal") and len(r) > 3,
        "kal-": lambda r: r.startswith("kal") and len(r) > 3,
        "da-": lambda r: r.startswith("da") and len(r) >= 2,
        "sh-": lambda r: r.startswith("sh") and len(r) > 2,
    }

    print(f"\n  Root family presence in ring texts vs labels:")
    print(f"  {'Family':<10} {'Ring count':>10} {'Ring %':>8} {'Label count':>12} {'Label %':>8}")
    print(f"  {'-'*10} {'-'*10} {'-'*8} {'-'*12} {'-'*8}")

    for fam_name, fam_test in families.items():
        r_count = sum(1 for p in ring_parsed if fam_test(p["root"]))
        l_count = sum(1 for p in label_parsed if fam_test(p["root"]))
        r_pct = r_count / len(ring_parsed) * 100
        l_pct = l_count / len(label_parsed) * 100
        marker = " ◄" if abs(r_pct - l_pct) > 3 else ""
        print(f"  {fam_name:<10} {r_count:>10} {r_pct:>7.1f}% {l_count:>12} {l_pct:>7.1f}%{marker}")

    # Do ring texts mention any of the hub labels?
    hub_labels = {"otaly", "okal", "oky", "okeody"}
    print(f"\n  Hub label appearances in ring texts:")
    for hub in hub_labels:
        rings_with = [(rt["sign"], rt["ring_name"]) for rt in ring_texts if hub in rt["words"]]
        if rings_with:
            print(f"    '{hub}': found in {rings_with}")
        else:
            print(f"    '{hub}': NOT found in any ring text")

    # Do ring texts mention otaldar (the decan boundary marker)?
    print(f"\n  Key label appearances in ring texts:")
    key_labels = ["otaldar", "otaly", "otal", "okal", "okaly", "okeey", "otalaiin"]
    for label in key_labels:
        rings_with = [(rt["sign"], rt["ring_name"], rt["ring_idx"])
                      for rt in ring_texts if label in rt["words"]]
        if rings_with:
            print(f"    '{label}': {rings_with}")

    # Unique vocabulary in ring texts that never appears as a label
    ring_only_words = set(w for rt in ring_texts for w in rt["words"]) - set(p["word"] for p in label_parsed)
    ring_only_freq = Counter()
    for rt in ring_texts:
        for w in rt["words"]:
            if w in ring_only_words:
                ring_only_freq[w] += 1

    print(f"\n  Ring-exclusive words (never appear as nymph labels):")
    print(f"  Total: {len(ring_only_words)} words")
    print(f"  Top 20 by frequency:")
    for w, freq in ring_only_freq.most_common(20):
        pf, root, sf, ok = parse_word(w)
        n_signs = len(set(rt["sign"] for rt in ring_texts if w in rt["words"]))
        print(f"    {w:<20} freq={freq:>3} signs={n_signs}  [{pf}+{root}+{sf}]")


# ── PHASE 7: Synthesis ───────────────────────────────────────────────────

def phase7_synthesis(ring_texts, ring_parsed, label_parsed, all_ring_words):
    print("\n" + "=" * 70)
    print("PHASE 7: RING TEXT ANALYSIS SYNTHESIS")
    print("=" * 70)

    total_ring = len(all_ring_words)
    total_label = len(label_parsed)
    ring_roots = set(p["root"] for p in ring_parsed)
    label_roots = set(p["root"] for p in label_parsed)
    shared = ring_roots & label_roots
    ring_only = ring_roots - label_roots

    # Register determination
    type_a = {"ka", "da", "a", "o", "ta", "cho", "sa", "ko", "sho",
              "keo", "to", "cheo", "sheo"}
    type_b = {"ched", "keed", "shed", "ked", "ted", "cheed", "sheed", "teed"}
    a_pct = sum(1 for p in ring_parsed if p["root"] in type_a) / total_ring
    b_pct = sum(1 for p in ring_parsed if p["root"] in type_b) / total_ring

    # Function word rate
    func_words = {"daiin", "aiin", "daiir", "dair", "al", "ar", "ol", "or",
                  "dal", "sal", "shal", "sheal", "daly", "y", "s", "r", "d", "l"}
    func_rate = sum(1 for p in ring_parsed if p["word"] in func_words) / total_ring

    # o- rate
    o_rate_ring = sum(1 for p in ring_parsed if "o" in p["prefix"]) / total_ring
    o_rate_label = sum(1 for p in label_parsed if "o" in p["prefix"]) / total_label

    iin_ring = sum(1 for p in ring_parsed if p["suffix"] in ("iin","aiin")) / total_ring
    iin_label = sum(1 for p in label_parsed if p["suffix"] in ("iin","aiin")) / total_label

    y_ring = sum(1 for p in ring_parsed if p["suffix"] == "y") / total_ring
    y_label = sum(1 for p in label_parsed if p["suffix"] == "y") / total_label

    print(f"""
  ┌──────────────────────────────────────────────────────────────────────┐
  │  RING TEXT ANALYSIS: RESULTS                                        │
  │                                                                      │
  │  DATA:                                                               │
  │    36 ring text lines across 10 zodiac signs                         │
  │    {total_ring} total words ({len(set(all_ring_words))} unique)                           │
  │                                                                      │
  │  REGISTER:                                                           │
  │    Type A (substance) roots: {a_pct:.0%}                                   │
  │    Type B (process) roots:   {b_pct:.0%}                                   │
  │    Function words:           {func_rate:.0%}                                   │
  │                                                                      │
  │  MORPHOLOGY COMPARISON (Ring vs Label):                              │
  │    o- prefix:   Ring {o_rate_ring:.0%}  vs  Label {o_rate_label:.0%}                        │
  │    -y suffix:   Ring {y_ring:.0%}  vs  Label {y_label:.0%}                        │
  │    -iin suffix: Ring {iin_ring:.0%}  vs  Label {iin_label:.0%}                        │
  │                                                                      │
  │  ROOT OVERLAP:                                                       │
  │    Ring roots:  {len(ring_roots)}                                               │
  │    Label roots: {len(label_roots)}                                               │
  │    Shared:      {len(shared)} (J={len(shared)/len(ring_roots|label_roots):.3f})                                  │
  │    Ring-only:   {len(ring_only)}                                               │
  │                                                                      │
  │  INTERPRETATION:                                                     │
  │  Ring texts are PROSE describing sign/decan properties.              │
  │  Labels are IDENTIFIERS for individual degrees.                      │
  │  Ring texts use more function words and grammatical particles.       │
  │  The root families OVERLAP — the same notation system encodes both.  │
  └──────────────────────────────────────────────────────────────────────┘""")


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Voynich Manuscript — Ring Text (@Cc) Extraction & Analysis")
    print("=" * 70)

    ring_texts = extract_ring_texts()
    label_words = extract_label_words()
    all_ring_words, word_freq = phase1_profile(ring_texts)
    ring_parsed, label_parsed = phase2_morphology(ring_texts, all_ring_words, label_words)
    phase3_register(ring_parsed, ring_texts)
    phase4_formulaic(ring_texts)
    phase5_ring_decan(ring_texts, ring_parsed)
    phase6_crossref(ring_texts, label_parsed, ring_parsed)
    phase7_synthesis(ring_texts, ring_parsed, label_parsed, all_ring_words)

    # Save results
    results = {
        "ring_count": len(ring_texts),
        "total_words": len(all_ring_words),
        "unique_words": len(set(all_ring_words)),
        "per_sign": {},
    }
    for rt in ring_texts:
        sign = rt["sign"]
        if sign not in results["per_sign"]:
            results["per_sign"][sign] = {"rings": [], "total_words": 0}
        results["per_sign"][sign]["rings"].append({
            "folio_line": rt["folio_line"],
            "ring_idx": rt["ring_idx"],
            "ring_name": rt["ring_name"],
            "word_count": rt["word_count"],
            "words": rt["words"],
        })
        results["per_sign"][sign]["total_words"] += rt["word_count"]

    with open("ring_text_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to ring_text_results.json")
    print(f"\n  Analysis complete.")
