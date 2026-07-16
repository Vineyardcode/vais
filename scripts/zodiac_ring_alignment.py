#!/usr/bin/env python3
"""
Cross-Zodiac Comparative Reading,
e-Chain Vowel Recovery, and Collocational Grammar
=================================================================

THREE ANALYSES:
  19a — Cross-zodiac ring-text alignment: treat each zodiac page as a
        parallel formulaic text (like Champollion's cartouches).  Identify
        shared "template" vocabulary vs sign-specific "filler" vocabulary.
  19b — e-chain vowel recovery: undo collapse_echains; treat e/ee/eee
        as distinct phonemes; measure vocabulary expansion and
        distributional differences.
  19c — Collocational grammar: for every confirmed-translation word,
        extract bigram/trigram neighborhoods to discover grammar frames.
"""

import re, json, sys
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from common import collapse_echains, full_decompose, gallows_base, parse_morphology, strip_gallows

# ══════════════════════════════════════════════════════════════════
# MORPHOLOGICAL PIPELINE
# ══════════════════════════════════════════════════════════════════

SIMPLE_GALLOWS = ["t", "k", "f", "p"]
BENCH_GALLOWS  = ["cth", "ckh", "cph", "cfh"]
COMPOUND_GCH   = ["tch", "kch", "pch", "fch"]
COMPOUND_GSH   = ["tsh", "ksh", "psh", "fsh"]
ALL_GALLOWS    = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

PREFIXES = ['qo','q','so','do','o','d','s','y']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol',
            'edy','ody','eedy','dy','sy','ey','y']






# NEW: decompose preserving e-chain lengths
def decompose_preserve_echains(word):
    stripped, gals = strip_gallows(word)
    # NO collapse — keep ee, eee intact
    pfx, root, sfx = parse_morphology(stripped)
    bases = [gallows_base(g) for g in gals]
    return dict(original=word, stripped=stripped,
                prefix=pfx or "", root=root, suffix=sfx or "",
                gallows=bases, determinative=bases[0] if bases else "",
                echain_pattern=re.findall(r'e+', stripped))


# ══════════════════════════════════════════════════════════════════
# DATA EXTRACTION
# ══════════════════════════════════════════════════════════════════

ZODIAC_MAP = {
    "f70v1": "Aries-dark", "f71r": "Aries-light",
    "f71v": "Taurus-light", "f72r1": "Taurus-dark",
    "f72r2": "Gemini", "f72r3": "Cancer",
    "f72v3": "Leo", "f72v2": "Virgo", "f72v1": "Libra",
    "f73r": "Scorpio", "f73v": "Sagittarius",
    "f70v2": "Pisces",
}

def clean_token(tok):
    """Clean a single token from transcription notation."""
    tok = tok.strip().replace("'", "")
    # resolve [x:y] alternates — take first reading
    tok = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', tok)
    tok = re.sub(r'\{([^}]+)\}', r'\1', tok)
    tok = re.sub(r'@\d+;?', '', tok)
    tok = re.sub(r'[^a-z]', '', tok)
    return tok

def extract_zodiac_data():
    """Extract all zodiac folio data: ring text, nymph labels, paragraphs."""
    folio_dir = Path("folios")
    zodiac = {}  # sign -> { "ring_lines": [...], "nymph_labels": [...] }

    for txt_file in sorted(folio_dir.glob("*.txt")):
        text = txt_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        current_section = None

        for line in lines:
            line_s = line.strip()
            # Detect section headers like <f70v1> or <f72v3>
            sec_match = re.match(r'^<(f\d+[rv]\d?)>\s', line_s)
            if sec_match:
                current_section = sec_match.group(1)
                continue
            # Also detect inline section id from locus tags
            locus_match = re.match(r'<(f\d+[rv]\d?)\.\d+', line_s)
            if locus_match:
                current_section = locus_match.group(1)

            if not current_section or current_section not in ZODIAC_MAP:
                continue
            sign = ZODIAC_MAP[current_section]
            if sign not in zodiac:
                zodiac[sign] = {"ring_lines": [], "nymph_labels": [],
                                "ring_words": [], "nymph_words": []}

            # Ring text
            if "@Cc" in line_s:
                m = re.match(r'<([^>]+)>\s*(.*)', line_s)
                if m:
                    raw = m.group(2)
                    # Strip time marker
                    raw = re.sub(r'<![\d:]+>', '', raw)
                    # Remove editorial marks
                    raw = re.sub(r'<![^>]*>', '', raw)
                    raw = re.sub(r'<%>|<\$>|<->|<\.>', ' ', raw)
                    raw = re.sub(r'<[^>]*>', '', raw)
                    raw = re.sub(r'\?\?\?', '', raw)
                    tokens = re.split(r'[.\s,]+', raw)
                    clean = []
                    for tok in tokens:
                        ct = clean_token(tok)
                        if ct and len(ct) >= 2 and '?' not in tok:
                            clean.append(ct)
                    zodiac[sign]["ring_lines"].append(clean)
                    zodiac[sign]["ring_words"].extend(clean)

            # Nymph labels
            elif "@Lz" in line_s or "&Lz" in line_s:
                m = re.match(r'<([^>]+)>\s*(.*)', line_s)
                if m:
                    raw = m.group(2)
                    raw = re.sub(r'<![\d:]+>', '', raw)
                    raw = re.sub(r'<![^>]*>', '', raw)
                    raw = re.sub(r'<[^>]*>', '', raw)
                    raw = re.sub(r'\?\?\?', '', raw)
                    tokens = re.split(r'[.\s,]+', raw)
                    label_parts = []
                    for tok in tokens:
                        ct = clean_token(tok)
                        if ct and len(ct) >= 2:
                            label_parts.append(ct)
                    if label_parts:
                        zodiac[sign]["nymph_labels"].append(label_parts)
                        zodiac[sign]["nymph_words"].extend(label_parts)

    return zodiac

def extract_all_words():
    """Extract ALL tokens from the corpus with section tagging."""
    folio_dir = Path("folios")
    all_data = []
    for txt_file in sorted(folio_dir.glob("*.txt")):
        stem = txt_file.stem
        m = re.match(r'f(\d+)', stem)
        if not m: continue
        num = int(m.group(1))
        if num <= 58 or 65 <= num <= 66: section = "herbal-A"
        elif 67 <= num <= 73: section = "zodiac"
        elif 75 <= num <= 84: section = "bio"
        elif 85 <= num <= 86: section = "cosmo"
        elif 87 <= num <= 102:
            section = "pharma" if num in (88,89,99,100,101,102) else "herbal-B"
        elif 103 <= num <= 116: section = "text"
        else: section = "unknown"

        lines = txt_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line: continue
            lm = re.match(r'<([^>]+)>\s*(.*)', line)
            if not lm: continue
            locus = lm.group(1)
            text = lm.group(2)
            text = re.sub(r'<![\d:]+>', '', text)
            text = re.sub(r'<![^>]*>', '', text)
            text = re.sub(r'<%>|<\$>|<->|<\.>', ' ', text)
            text = re.sub(r'<[^>]*>', '', text)
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
            text = re.sub(r'\{([^}]+)\}', r'\1', text)
            text = re.sub(r'@\d+;?', '', text)
            text = re.sub(r'\?\?\?', '', text)
            tokens = re.split(r'[.\s,<>\-]+', text)
            for tok in tokens:
                tok = tok.strip().replace("'", "")
                if not tok or '?' in tok: continue
                if re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                    all_data.append({"word": tok, "section": section,
                                     "folio": stem, "locus": locus})
    return all_data


# ══════════════════════════════════════════════════════════════════
# 19a  CROSS-ZODIAC COMPARATIVE ALIGNMENT
# ══════════════════════════════════════════════════════════════════

def run_19a(zodiac):
    print("\n" + "=" * 76)
    print("CROSS-ZODIAC COMPARATIVE RING TEXT ALIGNMENT")
    print("=" * 76)
    print("""
  RATIONALE: Medieval astrological manuals describe each zodiac sign using a
  formulaic template ("X is the house of Y, of the Z triplicity...").  If the
  ring text follows such a template, the SAME function words and grammar
  markers should recur at similar positions across all 12 signs, while
  DIFFERENT content words (planet names, element names, body parts) should
  fill the same structural slots. By overlaying all 12 ring texts we can
  separate template vocabulary from sign-specific vocabulary.
    """)

    # — 1. Overview of ring text per sign ——————————————————————————
    print("  --- Ring text inventory ---")
    for sign in sorted(zodiac.keys()):
        rw = zodiac[sign]["ring_words"]
        rl = zodiac[sign]["ring_lines"]
        print(f"    {sign:18s}  {len(rl)} ring(s)  {len(rw)} words")

    # — 2. Per-sign vocabulary sets ————————————————————————————————
    sign_roots = {}
    for sign, data in zodiac.items():
        roots = []
        for w in data["ring_words"]:
            d = full_decompose(w)
            roots.append(d["root"])
        sign_roots[sign] = roots

    # — 3. TEMPLATE vocabulary: roots that appear in ≥ N signs ————
    root_in_signs = defaultdict(set)
    root_total_ring = Counter()
    for sign, roots in sign_roots.items():
        for r in roots:
            root_in_signs[r].add(sign)
            root_total_ring[r] += 1

    n_signs = len(zodiac)
    print(f"\n  --- Roots shared across multiple signs (of {n_signs} total) ---")
    thresholds = [n_signs, max(1, n_signs-1), max(1, n_signs-2),
                  max(1, int(n_signs*0.75)), max(1, int(n_signs*0.5))]
    for thresh in sorted(set(thresholds), reverse=True):
        shared = [r for r, signs in root_in_signs.items() if len(signs) >= thresh]
        if shared:
            print(f"\n    Present in ≥{thresh}/{n_signs} signs ({len(shared)} roots):")
            for r in sorted(shared, key=lambda x: -root_total_ring[x])[:25]:
                signs_abbr = ",".join(sorted(s[:3] for s in root_in_signs[r]))
                print(f"      {r:15s} x{root_total_ring[r]:4d}  ({len(root_in_signs[r]):2d} signs)")

    # — 4. SIGN-SPECIFIC vocabulary: roots that appear in only 1-2 signs
    exclusive = [(r, next(iter(signs))) for r, signs in root_in_signs.items()
                 if len(signs) == 1 and root_total_ring[r] >= 2]
    exclusive.sort(key=lambda x: -root_total_ring[x[0]])

    print(f"\n  --- Sign-EXCLUSIVE roots (1 sign only, freq ≥ 2): {len(exclusive)} ---")
    for r, sign in exclusive[:30]:
        print(f"      {r:15s} x{root_total_ring[r]:4d}  ONLY in {sign}")

    # — 5. POSITIONAL ALIGNMENT: Compare word positions across outer rings
    #    Use ONLY the first (outer) ring line per sign for alignment
    print(f"\n  --- Positional alignment of OUTER ring texts ---")
    outer_rings = {}
    for sign, data in zodiac.items():
        if data["ring_lines"]:
            tokens = data["ring_lines"][0]
            decomposed = [full_decompose(w) for w in tokens]
            outer_rings[sign] = decomposed

    # Check what appears at each ordinal position
    max_len = max(len(v) for v in outer_rings.values())
    # For positions 0-9 (the opening of each ring), show what root appears
    print(f"\n    Positions 0-9 of each outer ring line:")
    print(f"    {'Sign':18s}", end="")
    for pos in range(min(10, max_len)):
        print(f" {'P'+str(pos):>10s}", end="")
    print()
    print(f"    {'-'*118}")

    for sign in sorted(outer_rings.keys()):
        dec = outer_rings[sign]
        print(f"    {sign:18s}", end="")
        for pos in range(min(10, max_len)):
            if pos < len(dec):
                root = dec[pos]["root"]
                det = dec[pos]["determinative"]
                tag = f"{det}{root}" if det else root
                print(f" {tag:>10s}", end="")
            else:
                print(f" {'':>10s}", end="")
        print()

    # — 6. FIRST-WORD analysis: what is the opening word of each ring?
    print(f"\n  --- Opening word pattern per ring ---")
    print(f"    {'Sign':18s} {'Ring 1 opener':25s} {'Ring 2 opener':25s} {'Ring 3 opener':25s}")
    for sign in sorted(zodiac.keys()):
        openers = []
        for ring_line in zodiac[sign]["ring_lines"][:3]:
            if ring_line:
                w = ring_line[0]
                d = full_decompose(w)
                openers.append(f"{w} ({d['prefix']}-{d['determinative']}-{d['root']}-{d['suffix']})")
            else:
                openers.append("—")
        while len(openers) < 3:
            openers.append("—")
        print(f"    {sign:18s} {openers[0]:25s} {openers[1]:25s} {openers[2]:25s}")

    # — 7. Repeated PHRASES: bigrams shared across signs ——————————
    print(f"\n  --- Cross-sign shared bigrams (ring text) ---")
    sign_bigrams = {}
    for sign, data in zodiac.items():
        bigrams = []
        for ring_line in data["ring_lines"]:
            decomposed = [full_decompose(w) for w in ring_line]
            for i in range(len(decomposed) - 1):
                bg = (decomposed[i]["root"], decomposed[i+1]["root"])
                bigrams.append(bg)
        sign_bigrams[sign] = set(bigrams)

    # Find bigrams present in ≥ 4 signs
    all_bg = defaultdict(set)
    bg_total = Counter()
    for sign, bgs in sign_bigrams.items():
        for bg in bgs:
            all_bg[bg].add(sign)
            bg_total[bg] += 1

    shared_bg = [(bg, signs) for bg, signs in all_bg.items() if len(signs) >= 4]
    shared_bg.sort(key=lambda x: -len(x[1]))
    print(f"    Bigrams in ≥4 signs: {len(shared_bg)}")
    for bg, signs in shared_bg[:20]:
        print(f"      {bg[0]:10s} → {bg[1]:10s}  ({len(signs)} signs)")

    # — 8. SUFFIX PATTERN per sign: what suffixes dominate?
    print(f"\n  --- Suffix distribution per sign (ring text) ---")
    print(f"    {'Sign':18s} {'n':>5s} {'-y':>6s} {'-dy':>6s} {'-al':>6s} {'-ol':>6s} {'-ar':>6s} {'-or':>6s} {'-aiin':>6s} {'-edy':>6s} {'(none)':>6s}")
    for sign in sorted(zodiac.keys()):
        words = zodiac[sign]["ring_words"]
        decomps = [full_decompose(w) for w in words]
        n = len(decomps)
        if n == 0: continue
        sc = Counter(d["suffix"] for d in decomps)
        print(f"    {sign:18s} {n:5d}", end="")
        for sfx in ['y','dy','al','ol','ar','or','aiin','edy','']:
            pct = 100 * sc.get(sfx, 0) / n
            print(f" {pct:5.1f}%", end="")
        print()

    # — 9. DETERMINATIVE distribution per sign: does gallows usage vary?
    print(f"\n  --- Determinative distribution per sign (ring text) ---")
    print(f"    {'Sign':18s} {'n':>5s} {'t':>6s} {'k':>6s} {'f':>6s} {'p':>6s} {'none':>6s}")
    for sign in sorted(zodiac.keys()):
        words = zodiac[sign]["ring_words"]
        decomps = [full_decompose(w) for w in words]
        n = len(decomps)
        if n == 0: continue
        dc = Counter(d["determinative"] for d in decomps)
        print(f"    {sign:18s} {n:5d}", end="")
        for det in ['t','k','f','p','']:
            pct = 100 * dc.get(det, 0) / n
            print(f" {pct:5.1f}%", end="")
        print()

    return root_in_signs, outer_rings


# ══════════════════════════════════════════════════════════════════
# 19b  E-CHAIN VOWEL RECOVERY
# ══════════════════════════════════════════════════════════════════

def run_19b(all_words):
    print("\n" + "=" * 76)
    print("E-CHAIN VOWEL RECOVERY")
    print("=" * 76)
    print("""
  Earlier analysis proved root='e' is a parsing artifact from collapse_echains().
  Here we UNDO the collapse: treat e, ee, eee as distinct phonemes.
  This should expand the effective vocabulary and reveal patterns
  hidden by the collapse.
    """)

    # Decompose with and without collapse
    collapsed_roots = Counter()
    preserved_roots = Counter()
    word_pairs = []  # (collapsed_root, preserved_root)
    echain_data = []

    for wdata in all_words:
        w = wdata["word"]
        d_collapsed = full_decompose(w)
        d_preserved = decompose_preserve_echains(w)

        collapsed_roots[d_collapsed["root"]] += 1
        preserved_roots[d_preserved["root"]] += 1
        word_pairs.append((d_collapsed["root"], d_preserved["root"]))
        echain_data.append({
            "word": w,
            "collapsed_root": d_collapsed["root"],
            "preserved_root": d_preserved["root"],
            "echains": d_preserved["echain_pattern"],
            "section": wdata["section"],
        })

    print(f"  Unique roots WITH collapse:    {len(collapsed_roots)}")
    print(f"  Unique roots WITHOUT collapse:  {len(preserved_roots)}")
    print(f"  Vocabulary expansion:           {len(preserved_roots) - len(collapsed_roots)} new roots "
          f"(+{100*(len(preserved_roots)-len(collapsed_roots))/len(collapsed_roots):.1f}%)")

    # What does root='e' split into?
    print(f"\n  --- What root='e' becomes after recovery ---")
    e_splits = Counter()
    for d in echain_data:
        if d["collapsed_root"] == "e":
            e_splits[d["preserved_root"]] += 1

    print(f"  root='e' splits into {len(e_splits)} distinct roots:")
    for root, count in e_splits.most_common(25):
        print(f"    {root:20s} x{count:5d}")

    # Distributional test: do the split roots behave differently?
    print(f"\n  --- Do split e-roots distribute differently? ---")
    top_split = [r for r, c in e_splits.most_common(6) if r != "e"]
    print(f"    Testing top split roots: {', '.join(top_split)}")

    split_by_section = {r: Counter() for r in top_split}
    for d in echain_data:
        if d["preserved_root"] in split_by_section:
            split_by_section[d["preserved_root"]][d["section"]] += 1

    sections = sorted(set(d["section"] for d in echain_data))
    print(f"\n    {'Root':15s}", end="")
    for sec in sections:
        print(f" {sec:>10s}", end="")
    print()
    for root in top_split:
        total = sum(split_by_section[root].values())
        if total == 0: continue
        print(f"    {root:15s}", end="")
        for sec in sections:
            pct = 100 * split_by_section[root].get(sec, 0) / total
            print(f" {pct:9.1f}%", end="")
        print()

    # Compare distributional divergence: JSD between split roots
    print(f"\n  --- Jensen-Shannon divergence between top split e-roots ---")
    import math
    def jsd(p, q, keys):
        """JSD between two count dicts."""
        tp = sum(p[k] for k in keys) or 1
        tq = sum(q[k] for k in keys) or 1
        div = 0
        for k in keys:
            pk = (p[k] / tp) if p[k] else 0
            qk = (q[k] / tq) if q[k] else 0
            mk = (pk + qk) / 2
            if pk > 0 and mk > 0:
                div += pk * math.log2(pk / mk) / 2
            if qk > 0 and mk > 0:
                div += qk * math.log2(qk / mk) / 2
        return div

    for r1, r2 in combinations(top_split[:4], 2):
        d = jsd(split_by_section[r1], split_by_section[r2], sections)
        print(f"    JSD({r1:10s}, {r2:10s}) = {d:.4f}  {'DIFFERENT' if d > 0.05 else 'similar'}")

    # E-chain length encoding test: does chain length vary by section?
    print(f"\n  --- E-chain length frequency by section ---")
    echain_sec = defaultdict(lambda: Counter())
    for d in echain_data:
        for ec in d["echains"]:
            echain_sec[d["section"]][len(ec)] += 1

    print(f"    {'Section':12s} {'e×1':>8s} {'e×2':>8s} {'e×3':>8s} {'e×4+':>8s} {'ratio 2:1':>10s}")
    for sec in sorted(sections):
        c = echain_sec[sec]
        t = sum(c.values()) or 1
        ratio = c[2] / c[1] if c[1] else 0
        print(f"    {sec:12s} {c[1]:8d} {c[2]:8d} {c[3]:8d} {sum(c[n] for n in c if n>=4):8d} {ratio:10.3f}")

    # What are the most information-rich preserved roots?
    print(f"\n  --- Top 20 preserved roots that were HIDDEN by collapse ---")
    hidden = []
    for root, count in preserved_roots.most_common():
        if root not in collapsed_roots and count >= 10:
            hidden.append((root, count))
    for root, count in hidden[:20]:
        print(f"    {root:20s} x{count:5d}  (invisible under collapse)")

    return preserved_roots, e_splits


# ══════════════════════════════════════════════════════════════════
# 19c  COLLOCATIONAL GRAMMAR
# ══════════════════════════════════════════════════════════════════

# Confirmed translations (from the Coptic probes and sentence_translation)
CONFIRMED_VOCAB = {
    "esed":  ("lion/Leo", "Arabic", 1.00),
    "she":   ("tree/plant", "Coptic", 1.00),
    "al":    ("stone", "Coptic", 1.00),
    "he":    ("fall/occur", "Coptic", 1.00),
    "ro":    ("mouth", "Coptic", 1.00),
    "les":   ("tongue", "Coptic", 0.95),
    "ran":   ("name", "Coptic", 0.95),
    "cham":  ("hot/warm", "Coptic", 0.90),
    "res":   ("south", "Coptic", 0.90),
    "ar":    ("king/great", "Coptic", 0.75),
    "or":    ("king/great(var)", "Coptic", 0.70),
    "ol":    ("carry/lift", "Coptic", 0.70),
    "am":    ("water/lion", "Coptic", 0.70),
    "chas":  ("lord/master", "Coptic", 0.85),
    "eos":   ("star", "Coptic", 0.85),
    "es":    ("star(short)", "Coptic", 0.80),
    "chol":  ("celestial body", "Coptic", 0.70),
    "cho":   ("substance(herbal)", "pattern", 0.70),
}

def run_19c(all_words):
    print("\n" + "=" * 76)
    print("COLLOCATIONAL GRAMMAR ANALYSIS")
    print("=" * 76)
    print("""
  For each word with a confirmed translation, extract its immediate
  bigram/trigram neighborhood.  If grammar is consistent, the same
  frames should recur.  E.g. if o-t-esed-y = "the celestial lion",
  does o-t-X-y appear around other nouns?
    """)

    # Build running token sequence per folio/locus
    folio_sequences = defaultdict(list)
    for wdata in all_words:
        d = full_decompose(wdata["word"])
        folio_sequences[wdata["folio"]].append({
            **d, "section": wdata["section"], "locus": wdata["locus"]
        })

    # Build flat sequence with boundaries
    full_seq = []
    for folio in sorted(folio_sequences.keys()):
        full_seq.extend(folio_sequences[folio])

    # For each confirmed word, find all occurrences and collect neighbors
    print(f"  --- Bigram neighborhoods of confirmed words ---\n")

    for vocab_root, (meaning, source, conf) in sorted(CONFIRMED_VOCAB.items(),
                                                        key=lambda x: -x[1][2]):
        # Find all positions of this root
        positions = [i for i, w in enumerate(full_seq) if w["root"] == vocab_root]
        if len(positions) < 3:
            continue

        # Collect left and right neighbors
        left_roots = Counter()
        right_roots = Counter()
        left_words = Counter()
        right_words = Counter()
        frames = Counter()  # (prefix, det, _, suffix) frame
        word_frames = Counter()  # complete word-level frame

        for pos in positions:
            w = full_seq[pos]
            frame = f"{w['prefix']}-{w['determinative']}-ROOT-{w['suffix']}"
            frames[frame] += 1

            if pos > 0:
                lw = full_seq[pos-1]
                left_roots[lw["root"]] += 1
                left_words[lw["original"]] += 1
            if pos < len(full_seq) - 1:
                rw = full_seq[pos+1]
                right_roots[rw["root"]] += 1
                right_words[rw["original"]] += 1

            # Trigram: left_root + this + right_root
            if 0 < pos < len(full_seq) - 1:
                tri = (full_seq[pos-1]["root"], vocab_root, full_seq[pos+1]["root"])
                word_frames[tri] += 1

        print(f"  ROOT: {vocab_root:10s} = {meaning:20s} (conf {conf:.2f}, {len(positions)} occurrences)")
        print(f"    Morphological frames:")
        for frame, cnt in frames.most_common(5):
            print(f"      {frame:30s} x{cnt}")
        print(f"    Left neighbors (top 5 roots): ", end="")
        print("  ".join(f"{r}({c})" for r, c in left_roots.most_common(5)))
        print(f"    Right neighbors (top 5 roots): ", end="")
        print("  ".join(f"{r}({c})" for r, c in right_roots.most_common(5)))
        # Show recurring trigrams
        recurrent = [(t, c) for t, c in word_frames.items() if c >= 3]
        if recurrent:
            recurrent.sort(key=lambda x: -x[1])
            print(f"    Recurring trigrams:")
            for tri, cnt in recurrent[:5]:
                # Translate where possible
                parts = []
                for r in tri:
                    if r in CONFIRMED_VOCAB:
                        parts.append(f"{r}={CONFIRMED_VOCAB[r][0]}")
                    else:
                        parts.append(r)
                print(f"      {' | '.join(parts):50s} x{cnt}")
        print()

    # — FRAME EXTRACTION: o-DET-X-SUFFIX patterns ————————————————
    print(f"\n  --- Grammatical frame extraction ---")
    print(f"  Looking for recurring PREFIX-DET-*-SUFFIX frames:\n")

    frame_members = defaultdict(list)
    for w in full_seq:
        if w["root"] and w["determinative"]:
            frame = f"{w['prefix']}-{w['determinative']}-*-{w['suffix']}"
            frame_members[frame].append(w["root"])

    # Show frames with many DISTINCT roots (= productive templates)
    frame_stats = []
    for frame, roots in frame_members.items():
        unique = len(set(roots))
        if unique >= 5 and len(roots) >= 20:
            frame_stats.append((frame, len(roots), unique, Counter(roots).most_common(8)))
    frame_stats.sort(key=lambda x: -x[1])

    print(f"  {'Frame':35s} {'Tokens':>7s} {'Unique':>7s}  Top fillers")
    print(f"  {'-'*100}")
    for frame, total, unique, top in frame_stats[:25]:
        fillers = ", ".join(f"{r}({c})" for r, c in top)
        print(f"  {frame:35s} {total:7d} {unique:7d}  {fillers}")

    # — WORD-ORDER test: does determinative predict position? ——————
    print(f"\n  --- Word position vs determinative (sentence-initial, medial, final) ---")
    # Use locus boundaries to define "sentences" (each locus = one line)
    locus_groups = defaultdict(list)
    for w in full_seq:
        locus_groups[w["locus"]].append(w)

    pos_det = {"initial": Counter(), "medial": Counter(), "final": Counter()}
    for locus, words in locus_groups.items():
        if len(words) < 3:
            continue
        if words[0]["determinative"]:
            pos_det["initial"][words[0]["determinative"]] += 1
        if words[-1]["determinative"]:
            pos_det["final"][words[-1]["determinative"]] += 1
        for w in words[1:-1]:
            if w["determinative"]:
                pos_det["medial"][w["determinative"]] += 1

    print(f"    {'Position':10s} {'t%':>8s} {'k%':>8s} {'f%':>8s} {'p%':>8s}")
    for pos_name in ["initial", "medial", "final"]:
        total = sum(pos_det[pos_name].values()) or 1
        print(f"    {pos_name:10s}", end="")
        for det in 'tkfp':
            pct = 100 * pos_det[pos_name].get(det, 0) / total
            print(f" {pct:7.1f}%", end="")
        print()


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 76)
    print("zodiac_ring_alignment: CROSS-ZODIAC ALIGNMENT, VOWEL RECOVERY, GRAMMAR")
    print("=" * 76)

    print("\nLoading zodiac data...")
    zodiac = extract_zodiac_data()
    print(f"  Found {len(zodiac)} zodiac signs")

    print("\nLoading full corpus...")
    all_words = extract_all_words()
    print(f"  {len(all_words)} tokens from {len(set(w['folio'] for w in all_words))} folios")

    # Run all three analyses
    root_in_signs, outer_rings = run_19a(zodiac)
    preserved_roots, e_splits = run_19b(all_words)
    run_19c(all_words)

    # Save results
    results = {
        "zodiac_signs_found": list(zodiac.keys()),
        "ring_words_per_sign": {s: len(d["ring_words"]) for s, d in zodiac.items()},
        "shared_roots_all_signs": [r for r, signs in root_in_signs.items()
                                    if len(signs) == len(zodiac)],
        "vocabulary_expansion_pct": round(100*(len(preserved_roots)-
            len(Counter(full_decompose(w["word"])["root"] for w in all_words)))/
            max(1, len(Counter(full_decompose(w["word"])["root"] for w in all_words))), 1),
        "e_root_split_count": len(e_splits),
    }

    Path("results").mkdir(exist_ok=True)
    Path("results/zodiac_ring_alignment_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n  Results saved to results/zodiac_ring_alignment_results.json")
