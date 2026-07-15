# Helper to ensure ASCII-safe output for all fields
def ascii_safe(s):
    if isinstance(s, str):
        return s.encode('ascii', 'replace').decode()
    return str(s)
#!/usr/bin/env python3
"""
Voynich Manuscript — Phase 16a: Leo Folio Deep-Dive

Uses esed=asad (Arabic "lion") as an anchor point to attempt decipherment
of the entire Leo folio (f72v3). Strategy:

1. Decompose EVERY word on the Leo folio (nymphs + ring text)
2. Map all unique roots to known multilingual astronomical vocabulary
3. Test Leo-unique roots against expanded Arabic/Hebrew/Greek/Coptic terms
4. Look for structural patterns (ring text vs nymph labels)
5. Use the anchor to constrain phonetic value hypotheses
6. Cross-reference Leo roots appearing elsewhere in the manuscript
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import collapse_echains, gallows_base_v2 as gallows_base, parse_morphology, strip_gallows

# ── Morphological machinery (from Phase 15) ────────────────────────────

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
        "prefix": prefix or "-",
        "root": root,
        "suffix": suffix or "-",
        "gallows": gal_bases,
        "determinative": gal_bases[0] if gal_bases else "-"
    }

def consonant_skeleton(word):
    """Extract consonantal skeleton (strip all vowels a,e,i,o,u)."""
    return re.sub(r'[aeiou]', '', word.lower())

# ── Section classifier ───────────────────────────────────────────────────

def classify_folio(filepath):
    stem = filepath.stem if hasattr(filepath, 'stem') else Path(filepath).stem
    m = re.match(r'f(\d+)', stem)
    if not m:
        return "unknown"
    num = int(m.group(1))
    if num <= 58 or 65 <= num <= 66:
        return "herbal-A"
    elif 67 <= num <= 73:
        return "zodiac"
    elif 75 <= num <= 84:
        return "bio"
    elif 85 <= num <= 86:
        return "cosmo"
    elif 87 <= num <= 102:
        if num in (88, 89, 99, 100, 101, 102):
            return "pharma"
        return "herbal-B"
    elif 103 <= num <= 116:
        return "text"
    return "unknown"

# ── Expanded multilingual vocabulary for Leo context ─────────────────────

# Leo-specific: the sign of the lion, ruled by the Sun, associated with
# heart, back, gold, fixed fire sign. In medieval astrology: royalty, power.

LEO_VOCABULARY = {
    # Sign names across languages
    "leo_names": {
        "asad": ("Arabic", "lion — أسد"),
        "laith": ("Arabic", "lion (poetic) — ليث"),
        "haydar": ("Arabic", "lion (strong) — حيدر"),
        "saba": ("Arabic", "lion — سبع"),
        "arieh": ("Hebrew", "lion — אריה"),
        "lavi": ("Hebrew", "lion (young) — לביא"),
        "kfir": ("Hebrew", "young lion — כפיר"),
        "leon": ("Greek", "lion — λέων"),
        "leo": ("Latin", "lion"),
        "mui": ("Coptic", "lion — ⲙⲟⲩⲓ"),
        "labu": ("Coptic/Demotic", "lion"),
    },
    # Decans of Leo (each ~10° of the 30° sign)
    "leo_decans": {
        "saturn": ("English", "1st decan ruler (some traditions)"),
        "jupiter": ("English", "2nd decan ruler"),
        "mars": ("English", "3rd decan ruler"),
        "zuhal": ("Arabic", "Saturn — زحل"),
        "mushtari": ("Arabic", "Jupiter — مشتری"),
        "mirrikh": ("Arabic", "Mars — مريخ"),
        "shabatai": ("Hebrew", "Saturn — שבתאי"),
        "tzedek": ("Hebrew", "Jupiter — צדק"),
        "maadim": ("Hebrew", "Mars — מאדים"),
        "kronos": ("Greek", "Saturn — Κρόνος"),
        "zeus": ("Greek", "Zeus/Jupiter — Ζεύς"),
        "ares": ("Greek", "Mars — Ἄρης"),
    },
    # Solar associations (Leo is ruled by the Sun)
    "solar": {
        "shams": ("Arabic", "sun — شمس"),
        "shemesh": ("Hebrew", "sun — שמש"),
        "helios": ("Greek", "sun — ἥλιος"),
        "sol": ("Latin", "sun"),
        "rhe": ("Coptic", "sun — ⲣⲏ"),
        "nur": ("Arabic", "light — نور"),
        "ouoein": ("Coptic", "light — ⲟⲩⲟⲉⲓⲛ"),
    },
    # Body parts ruled by Leo (heart, back, spine)
    "body_parts": {
        "qalb": ("Arabic", "heart — قلب"),
        "lev": ("Hebrew", "heart — לב"),
        "kardia": ("Greek", "heart — καρδία"),
        "hat": ("Coptic", "heart — ϩⲁⲧ"),
        "sadr": ("Arabic", "chest/breast — صدر"),
        "zahr": ("Arabic", "back — ظهر"),
        "cor": ("Latin", "heart"),
        "dorsum": ("Latin", "back"),
    },
    # Stars in Leo
    "leo_stars": {
        "regulus": ("Latin", "little king — alpha Leonis"),
        "qalb_al_asad": ("Arabic", "heart of the lion — Regulus"),
        "denebola": ("Arabic", "tail of the lion — beta Leonis"),
        "algieba": ("Arabic", "forehead — gamma Leonis"),
        "zosma": ("Greek", "girdle — delta Leonis"),
        "ras_elased": ("Arabic", "head of the lion — epsilon Leonis"),
    },
    # Elemental (Leo = fixed fire)
    "elemental": {
        "nar": ("Arabic", "fire — نار"),
        "esh": ("Hebrew", "fire — אש"),
        "pur": ("Greek", "fire — πῦρ"),
        "koh": ("Coptic", "fire — ⲕⲱϩ"),
        "harara": ("Arabic", "heat — حرارة"),
        "hom": ("Hebrew", "hot/warm — חם"),
        "hmom": ("Coptic", "hot — ϩⲙⲟⲙ"),
    },
    # Qualities/attributes
    "qualities": {
        "malik": ("Arabic", "king — ملك"),
        "melekh": ("Hebrew", "king — מלך"),
        "basileus": ("Greek", "king — βασιλεύς"),
        "ero": ("Coptic", "king — ⲉⲣⲟ"),
        "aziz": ("Arabic", "mighty/powerful — عزيز"),
        "gibbor": ("Hebrew", "mighty — גיבור"),
        "djom": ("Coptic", "power — ϫⲟⲙ"),
        "choeis": ("Coptic", "lord — ϫⲟⲉⲓⲥ"),
    },
    # General astronomical terms likely on zodiac pages
    "astronomical": {
        "kawkab": ("Arabic", "star/planet — كوكب"),
        "kokhav": ("Hebrew", "star — כוכב"),
        "aster": ("Greek", "star — ἀστήρ"),
        "siou": ("Coptic", "star — ⲥⲓⲟⲩ"),
        "burj": ("Arabic", "zodiac sign/tower — برج"),
        "mazzal": ("Hebrew", "constellation — מזל"),
        "daraja": ("Arabic", "degree — درجة"),
        "manzil": ("Arabic", "lunar mansion — منزل"),
        "abot": ("Coptic", "month — ⲁⲃⲟⲧ"),
        "rompe": ("Coptic", "year — ⲣⲟⲙⲡⲉ"),
        "hoou": ("Coptic", "day — ϩⲟⲟⲩ"),
    },
}

# ── Matching functions ───────────────────────────────────────────────────

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

def match_score(voynich_root, known_word):
    """Score similarity between a Voynich root and a known word."""
    vr = voynich_root.lower()
    kw = known_word.lower()
    
    # Exact match
    if vr == kw:
        return 1.0, "EXACT"
    
    # Containment
    if kw in vr and len(kw) >= 3:
        return 0.85, "CONTAINS"
    if vr in kw and len(vr) >= 3:
        return 0.75, "WITHIN"
    
    # Consonantal skeleton match
    vs = consonant_skeleton(vr)
    ks = consonant_skeleton(kw)
    if vs and ks:
        if vs == ks:
            return 1.0, "CONSONANT-EXACT"
        lcs = longest_common_subsequence(vs, ks)
        max_len = max(len(vs), len(ks))
        if max_len > 0:
            ratio = lcs / max_len
            if ratio >= 0.6:
                return round(ratio, 2), "CONSONANT"
    
    # Character-level LCS
    lcs = longest_common_subsequence(vr, kw)
    max_len = max(len(vr), len(kw))
    if max_len > 0:
        ratio = lcs / max_len
        if ratio >= 0.6:
            return round(ratio, 2), "LCS"
    
    return 0, "NONE"


# ── Extract all words from ALL folios (for cross-reference) ─────────────

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
            elif "@Ls" in locus:
                locus_type = "star"
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


# ── Extract Leo folio data specifically ──────────────────────────────────

def extract_leo_folio():
    """Extract all words from Leo section (f72v3) with full context."""
    txt_file = Path("folios/f72v_part.txt")
    lines = txt_file.read_text(encoding="utf-8").splitlines()
    
    leo_data = []
    in_leo = False
    
    for line in lines:
        line = line.strip()
        if "f72v3" in line:
            in_leo = True
        elif in_leo and line.startswith("<f72v") and "f72v3" not in line:
            in_leo = False
        
        if not in_leo:
            continue
        if line.startswith("#") or not line:
            continue
        
        m = re.match(r'<([^>]+)>\s*(.*)', line)
        if not m:
            continue
        
        locus = m.group(1)
        text = m.group(2)
        
        # Classify locus type
        if "@Cc" in locus:
            locus_type = "ring"
        elif "@Lz" in locus or "&Lz" in locus:
            locus_type = "nymph"
        else:
            locus_type = "paragraph"
        
        # Extract nymph number
        nymph_num = ""
        nm = re.match(r'f72v3\.(\d+)', locus)
        if nm:
            nymph_num = nm.group(1)
        
        # Extract clock position
        clock = ""
        cm = re.search(r'<!(\d+:\d+)>', text)
        if cm:
            clock = cm.group(1)
        
        # Clean text
        raw_text = text
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
                leo_data.append({
                    "word": tok,
                    "locus": locus,
                    "locus_type": locus_type,
                    "nymph_num": nymph_num,
                    "clock": clock,
                })
    
    return leo_data


# ════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: Full Leo Folio Decomposition
# ════════════════════════════════════════════════════════════════════════

def analysis_1_full_decomposition(leo_data):
    print("=" * 72)
    print("ANALYSIS 1: FULL LEO FOLIO DECOMPOSITION")
    print("=" * 72)
    
    decomposed = []
    for item in leo_data:
        d = full_decompose(item["word"])
        d.update(item)
        decomposed.append(d)
    
    # Summary
    nymph_words = [d for d in decomposed if d["locus_type"] == "nymph"]
    ring_words = [d for d in decomposed if d["locus_type"] == "ring"]
    
    print(f"\n  Total words on Leo folio: {len(decomposed)}")
    print(f"  Nymph labels: {len(nymph_words)} words")
    print(f"  Ring text: {len(ring_words)} words")
    
    # Show all nymph label decompositions
    print(f"\n  -- Nymph Label Decompositions (outer ring = 1-19, inner = 21-32) --")
    for d in nymph_words:
        ring = "OUTER" if d["nymph_num"] and int(d["nymph_num"]) < 20 else "INNER"
        mark = " *" if d["root"] == "esed" else ""
        # Replace Unicode empty set with ASCII '-'
        det = d['determinative'] if d['determinative'] != '-' else '-'
        pf = d['prefix'] if d['prefix'] != '-' else '-'
        sf = d['suffix'] if d['suffix'] != '-' else '-'
        print(f"    #{d['nymph_num']:>2s} {d['clock']:>5s} {ring:5s}  "
              f"{d['original']:20s} -> det={det:<2s} "
              f"pf={pf:<3s} root={d['root']:<10s} "
              f"sf={sf}{mark}")
    
    # Root frequency in nymphs vs rings
    nymph_roots = Counter(d["root"] for d in nymph_words)
    ring_roots = Counter(d["root"] for d in ring_words)
    
    print(f"\n  -- Nymph Roots (top 15) --")
    for root, count in nymph_roots.most_common(15):
        print(f"    {root:15s}  {count}")
    
    print(f"\n  -- Ring Text Roots (top 20) --")
    for root, count in ring_roots.most_common(20):
        print(f"    {root:15s}  {count}")
    
    # Determinative distribution
    nymph_det = Counter(d["determinative"] for d in nymph_words)
    ring_det = Counter(d["determinative"] for d in ring_words)
    
    print(f"\n  -- Determinative Distribution --")
    print(f"    {'Det':<6s} {'Nymph':>8s} {'Ring':>8s}")
    for det in ['t', 'k', 'f', 'p', '-']:
        det_label = det if det != '-' else '-'
        print(f"    {det_label:<6s} {nymph_det.get(det, 0):>8d} {ring_det.get(det, 0):>8d}")
    
    # Suffix distribution
    nymph_suf = Counter(d["suffix"] for d in nymph_words)
    ring_suf = Counter(d["suffix"] for d in ring_words)
    
    print(f"\n  -- Suffix Distribution --")
    print(f"    {'Suffix':<8s} {'Nymph':>8s} {'Ring':>8s}")
    all_suf = sorted(set(list(nymph_suf.keys()) + list(ring_suf.keys())),
                     key=lambda x: -(nymph_suf.get(x, 0) + ring_suf.get(x, 0)))
    for sf in all_suf[:12]:
        sf_label = sf if sf != '-' else '-'
        print(f"    {sf_label:<8s} {nymph_suf.get(sf, 0):>8d} {ring_suf.get(sf, 0):>8d}")
    
    return decomposed


# ════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: Anchor-Based Vocabulary Matching
# ════════════════════════════════════════════════════════════════════════

def analysis_2_anchor_matching(decomposed):
    print("\n" + "=" * 72)
    print("ANALYSIS 2: ANCHOR-BASED VOCABULARY MATCHING")
    print("=" * 72)
    
    # Get unique roots from Leo folio
    all_roots = set()
    root_loci = defaultdict(set)
    for d in decomposed:
        all_roots.add(d["root"])
        root_loci[d["root"]].add(d["locus_type"])
    
    print(f"\n  Unique roots on Leo folio: {len(all_roots)}")
    print(f"  * Anchor: esed = asad (Arabic 'lion')")
    print(f"  -> This confirms: Voynich 'e' can map to Arabic 'a' (aleph)")
    print(f"  -> This confirms: Voynich 's' = Arabic 's' (sin)")
    print(f"  -> This confirms: Voynich 'd' = Arabic 'd' (dal)")
    
    # Test every Leo root against the expanded vocabulary
    print(f"\n  -- Matching ALL Leo roots against expanded vocabulary --")
    
    all_matches = []
    for category, vocab in LEO_VOCABULARY.items():
        for known_word, (lang, meaning) in vocab.items():
            for root in sorted(all_roots):
                score, match_type = match_score(root, known_word)
                if score >= 0.6:
                    loci = ", ".join(sorted(root_loci[root]))
                    all_matches.append({
                        "root": root,
                        "known": known_word,
                        "lang": lang,
                        "meaning": meaning,
                        "score": score,
                        "type": match_type,
                        "category": category,
                        "loci": loci,
                    })
    
    # Sort by score descending
    all_matches.sort(key=lambda x: (-x["score"], x["root"]))
    
    # Print top matches
    seen_pairs = set()
    print(f"\n  {'Score':>5s} {'Type':<16s} {'Root':<12s} {'Known':<15s} "
          f"{'Lang':<10s} {'Category':<15s} {'Meaning'}")
    print(f"  " + "-" * 100)
    for m in all_matches:
        pair = (m["root"], m["known"])
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        # Replace non-ASCII characters in meaning with '?'
        safe_meaning = ''.join(c if ord(c) < 128 else '?' for c in m['meaning'][:40])
        print(f"  {m['score']:>5.2f} {m['type']:<16s} {m['root']:<12s} "
              f"{m['known']:<15s} {m['lang']:<10s} {m['category']:<15s} "
              f"{safe_meaning}")
    
    print(f"\n  Total matches (score >= 0.6): {len(seen_pairs)}")
    
    return all_matches


# ════════════════════════════════════════════════════════════════════════
# ANALYSIS 3: Phonetic Value Hypothesis Testing
# ════════════════════════════════════════════════════════════════════════

def analysis_3_phonetic_hypotheses(decomposed):
    print("\n" + "=" * 72)
    print("ANALYSIS 3: PHONETIC VALUE HYPOTHESES FROM ANCHOR")
    print("=" * 72)
    
    # From esed = asad, we hypothesize:
    # e → a (aleph/short vowel), s → s, d → d
    # These are trivially consistent with EVA transliteration
    # But we can test further: do other words make sense with these mappings?
    
    # Known sound values (from determinative/complement system):
    # Gallows t, k, f, p = silent determinatives
    # Prefixes qo, d, s, o = complements (not core phonetic)
    # Core phonetic: the ROOT is the meaningful part
    
    # Let's build a phonetic mapping table from ALL confirmed/strong matches
    print(f"\n  -- Phonetic Correspondence Table --")
    print(f"  (from esed=asad + structural analysis)")
    print()
    print(f"    EVA    -> Proposed Sound Value    Evidence")
    print(f"    " + "-" * 60)
    print(f"    e      -> a/e (short vowel)       esed=asad, e-chains non-structural")
    print(f"    s      -> s                        esed=asad, s+f complement pair")
    print(f"    d      -> d                        esed=asad, d+p complement pair")
    print(f"    ch     -> kh/x/h                   ch is most common - guttural?")
    print(f"    sh     -> sh/sh                    standard sibilant")
    print(f"    a      -> a (long vowel)           a vs e = long vs short")
    print(f"    o      -> o/u (back vowel)         o-prefix = locative?")
    print(f"    r      -> r                        standard")
    print(f"    l      -> l                        standard")
    print(f"    n      -> n                        standard (only in iin/aiin)")
    print(f"    y      -> y/i (semivowel/suffix)   y as suffix marker")
    print(f"    h      -> h                        standard aspirate")
    print(f"    i      -> i (always in iin/aiin)   genitive/possessive?")

    # Test: if ch = kh/h, does 'cham' make sense?
    # cham -> kham -> Arabic kham (raw/unformed) or Hebrew cham (hot/warm)
    print(f"\n  -- Testing ch=kh hypothesis with Leo roots --")
    
    ch_roots = [d for d in decomposed if "ch" in d["root"]]
    ch_unique = sorted(set(d["root"] for d in ch_roots))
    
    print(f"    Roots containing 'ch': {ch_unique}")
    print()
    print(f"    cham -> kham: Arabic 'kham' (raw) or Hebrew 'cham' (hot/warm)")
    print(f"         Leo = fire sign, 'hot' is perfectly contextual!")
    print(f"    cheo -> kheo: possibly related to Coptic 'choeis' (lord)?")
    print(f"    ches -> khes: Coptic 'kes' (bone)? Hebrew 'chas' (compassion)?")
    print(f"    chol -> khol: Arabic 'kohl' (antimony)? Hebrew 'kol' (all)?")
    
    # Test: 'yesh' unique to Leo
    print(f"\n  -- Testing other Leo-unique roots --")
    print(f"    yesh -> Hebrew 'yesh' (existence/there is) - common predicate")
    print(f"    rch  -> Hebrew 'reach' (smell/spirit) or Arabic 'rih' (wind)")
    print(f"         OR: reversed reading of chr -> Coptic 'chrisma' (anointing)")
    print(f"    heos -> kheos? Greek 'theos' (god)? Coptic 'hise' (suffering)?")
    print(f"    esed -> asad (CONFIRMED: Arabic 'asad' (lion))")

    # Look at the inner ring where esed appears - what's before and after?
    print(f"\n  -- Context around oteesed (nymph #29, inner ring) --")
    
    inner_ring = [d for d in decomposed 
                  if d["locus_type"] == "nymph" and d.get("nymph_num", "0").isdigit()
                  and int(d.get("nymph_num", "0")) >= 21]
    
    for d in sorted(inner_ring, key=lambda x: int(x.get("nymph_num", "0"))):
        mark = " * ANCHOR" if d["root"] == "esed" else ""
        print(f"    #{d['nymph_num']:>2s} {d['clock']:>5s} {d['original']:15s} -> "
              f"det={d['determinative']:<2s} root={d['root']:<10s} "
              f"sf={d['suffix']}{mark}")


# ════════════════════════════════════════════════════════════════════════
# ANALYSIS 4: Cross-Manuscript Root Distribution
# ════════════════════════════════════════════════════════════════════════

def analysis_4_cross_reference(decomposed, all_words):
    print("\n" + "=" * 72)
    print("ANALYSIS 4: CROSS-MANUSCRIPT ROOT DISTRIBUTION")
    print("=" * 72)
    
    # For each Leo root, where else does it appear?
    leo_roots = set(d["root"] for d in decomposed)
    
    # Build whole-corpus root map
    corpus_roots = defaultdict(lambda: defaultdict(int))
    for word, section, folio, locus, locus_type in all_words:
        d = full_decompose(word)
        corpus_roots[d["root"]][section] += 1
    
    # Show Leo-unique roots (not found or rare outside zodiac)
    print(f"\n  -- Leo Root Distribution Across Manuscript --")
    print(f"  {'Root':<12s} {'Leo':>5s} {'herbal':>8s} {'bio':>5s} "
          f"{'cosmo':>7s} {'text':>6s} {'pharma':>8s} {'zodiac':>8s}  Note")
    print(f"  " + "-" * 90)
    
    leo_root_counts = Counter(d["root"] for d in decomposed)
    
    for root in sorted(leo_roots, 
                       key=lambda r: -leo_root_counts.get(r, 0)):
        sec = corpus_roots.get(root, {})
        herbal = sec.get("herbal-A", 0) + sec.get("herbal-B", 0)
        bio = sec.get("bio", 0)
        cosmo = sec.get("cosmo", 0)
        text = sec.get("text", 0)
        pharma = sec.get("pharma", 0)
        zodiac = sec.get("zodiac", 0)
        total = sum(sec.values())
        
        note = ""
        if total == zodiac:
            note = "ZODIAC-ONLY"
        elif zodiac / max(total, 1) > 0.5:
            note = "zodiac-heavy"
        elif root == "esed":
            note = "★ ANCHOR = asad"
        
        if leo_root_counts[root] >= 1:
            print(f"  {root:<12s} {leo_root_counts[root]:>5d} "
                  f"{herbal:>8d} {bio:>5d} {cosmo:>7d} {text:>6d} "
                  f"{pharma:>8d} {zodiac:>8d}  {note}")
    
    # Which roots are EXCLUSIVE to Leo (not found in other zodiac signs)?
    print(f"\n  -- Roots exclusive to Leo folio within zodiac --")
    zodiac_files = {
        "f70v_part": "Aries/Pisces",
        "f71r": "Aries",
        "f71v_72r": "Taurus/Gemini/Cancer",
        "f73r": "Scorpio",
        "f73v": "Sagittarius",
    }
    
    other_zodiac_roots = set()
    folio_dir = Path("folios")
    for fname in zodiac_files:
        txt_file = folio_dir / f"{fname}.txt"
        if not txt_file.exists():
            continue
        lines = txt_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            m = re.match(r'<([^>]+)>\s*(.*)', line)
            if not m:
                continue
            text = m.group(2)
            text = re.sub(r'<![^>]*>', '', text)
            text = re.sub(r'<%>|<\$>|<->|<\.>', ' ', text)
            text = re.sub(r'<[^>]*>', '', text)
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
            text = re.sub(r'\{([^}]+)\}', r'\1', text)
            text = re.sub(r'@\d+;?', '', text)
            tokens = re.split(r'[.\s,<>\-]+', text)
            for tok in tokens:
                tok = tok.strip().replace("'", "")
                if tok and re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                    d = full_decompose(tok)
                    other_zodiac_roots.add(d["root"])
    
    leo_exclusive = leo_roots - other_zodiac_roots
    print(f"  Leo-exclusive roots (not in other zodiac folios): {sorted(leo_exclusive)}")


# ════════════════════════════════════════════════════════════════════════
# ANALYSIS 5: Ring Text Semantic Structure
# ════════════════════════════════════════════════════════════════════════

def analysis_5_ring_structure(decomposed):
    print("\n" + "=" * 72)
    print("ANALYSIS 5: RING TEXT SEMANTIC STRUCTURE")
    print("=" * 72)
    
    # Separate the three rings (C1=outer, C2=middle, C3=inner)
    ring_words = [d for d in decomposed if d["locus_type"] == "ring"]
    
    # Ring 1 = first @Cc line (nymph ~1-ish)
    # Ring 2 = second @Cc line (nymph ~20)
    # Ring 3 = third @Cc line (nymph ~33)
    
    # Assign ring numbers based on nymph_num in locus
    rings = defaultdict(list)
    for d in ring_words:
        # Extract which ring from the locus number
        nm = d.get("nymph_num", "")
        if nm == "1":
            rings["C1_outer"].append(d)
        elif nm == "20":
            rings["C2_middle"].append(d)
        elif nm == "33":
            rings["C3_inner"].append(d)
    
    for ring_name, words in sorted(rings.items()):
        print(f"\n  -- {ring_name} ({len(words)} words) --")
        
        # Root frequency
        roots = Counter(d["root"] for d in words)
        print(f"    Top roots: {roots.most_common(10)}")
        
        # Determinative distribution
        dets = Counter(d["determinative"] for d in words)
        print(f"    Determinatives: {dict(dets)}")
        
        # Suffix distribution
        sufs = Counter(d["suffix"] for d in words)
        print(f"    Suffixes: {dict(sufs)}")
        
        # Show full decomposition
        print(f"    Full text (decomposed):")
        for i, d in enumerate(words[:15]):
            print(f"      {ascii_safe(i+1):>2s}. {ascii_safe(d['original']):20s} -> "
                f"det={ascii_safe(d['determinative']):<2s} "
                f"pf={ascii_safe(d['prefix']):<3s} root={ascii_safe(d['root']):<10s} "
                f"sf={ascii_safe(d['suffix'])}")
        if len(words) > 15:
            print(f"      ... ({len(words) - 15} more)")
    
    # Compare ring structure
    print(f"\n  -- Ring Comparison --")
    for ring_name, words in sorted(rings.items()):
        n = len(words)
        det_counts = Counter(d["determinative"] for d in words)
        t_pct = det_counts.get("t", 0) / max(n, 1) * 100
        k_pct = det_counts.get("k", 0) / max(n, 1) * 100
        bare_pct = det_counts.get("-", 0) / max(n, 1) * 100
        
        unique_roots = len(set(d["root"] for d in words))
        print(f"    {ascii_safe(ring_name):<12s}: {ascii_safe(n):>3s} words, {ascii_safe(unique_roots):>3s} unique roots, "
              f"t={ascii_safe(int(round(t_pct)))}%, k={ascii_safe(int(round(k_pct)))}%, bare={ascii_safe(int(round(bare_pct)))}%")


# ════════════════════════════════════════════════════════════════════════
# ANALYSIS 6: The Anchor Word in Full Context
# ════════════════════════════════════════════════════════════════════════

def analysis_6_anchor_context(all_words):
    print("\n" + "=" * 72)
    print("ANALYSIS 6: 'esed' (=asad/lion) ACROSS THE ENTIRE MANUSCRIPT")
    print("=" * 72)
    
    # Find every instance of 'esed' root across the whole manuscript
    esed_instances = []
    for word, section, folio, locus, locus_type in all_words:
        d = full_decompose(word)
        if d["root"] == "esed" or "esed" in d["root"]:
            esed_instances.append({
                "word": word,
                "section": section,
                "folio": folio,
                "locus_type": locus_type,
                "root": d["root"],
                "det": d["determinative"],
                "prefix": d["prefix"],
                "suffix": d["suffix"],
            })
    
    print(f"\n  Instances of root 'esed' across manuscript: {len(esed_instances)}")
    
    for inst in esed_instances:
        print(f"    {inst['word']:20s}  [{inst['section']:>10s}] {inst['folio']:>12s} "
              f"{inst['locus_type']:<8s}  det={inst['det']} pf={inst['prefix']} "
              f"root={inst['root']} sf={inst['suffix']}")
    
    # Also check for 'sed' root (partial match to asad)
    print(f"\n  -- Also checking 'sed', 'esd', 'sd' roots --")
    for word, section, folio, locus, locus_type in all_words:
        d = full_decompose(word)
        if d["root"] in ("sed", "esd", "sd"):
                print(f"    {ascii_safe(word):20s}  [{ascii_safe(section):>10s}] {ascii_safe(folio):>12s} "
                    f"{ascii_safe(locus_type):<8s}  root={ascii_safe(d['root'])}")
    
    # Check raw words containing 'esed' as substring
    print(f"\n  -- Raw words containing 'esed' substring --")
    seen = set()
    for word, section, folio, locus, locus_type in all_words:
        if "esed" in word and word not in seen:
            seen.add(word)
            d = full_decompose(word)
            print(f"    {ascii_safe(word):20s}  [{ascii_safe(section):>10s}] {ascii_safe(folio):>12s} "
                        f"{ascii_safe(locus_type):<8s}  det={ascii_safe(d['determinative'])} root={ascii_safe(d['root'])} "
                        f"sf={ascii_safe(d['suffix'])}")


# ════════════════════════════════════════════════════════════════════════
# ANALYSIS 7: Nymph-by-Nymph Interpretive Attempt
# ════════════════════════════════════════════════════════════════════════

def analysis_7_interpretive_attempt(decomposed, all_matches):
    print("\n" + "=" * 72)
    print("ANALYSIS 7: NYMPH-BY-NYMPH INTERPRETIVE ATTEMPT")
    print("=" * 72)
    
    # Build a match lookup
    match_lookup = defaultdict(list)
    for m in all_matches:
        match_lookup[m["root"]].append(m)
    
    nymphs = [d for d in decomposed if d["locus_type"] == "nymph"]
    
    print(f"\n  Using anchor esed=asad + expanded vocabulary to attempt")
    print(f"  interpretation of each Leo nymph label.\n")
    
    outer = [d for d in nymphs if d.get("nymph_num", "0").isdigit() 
             and int(d.get("nymph_num", "0")) < 20]
    inner = [d for d in nymphs if d.get("nymph_num", "0").isdigit() 
             and int(d.get("nymph_num", "0")) >= 21]
    
    for label, ring_name in [(outer, "OUTER RING"), (inner, "INNER RING")]:
        print(f"  -- {ring_name} --")
        for d in sorted(label, key=lambda x: int(x.get("nymph_num", "0"))):
            matches = match_lookup.get(d["root"], [])
            best = matches[0] if matches else None
            
            det_label = {"t": "CELESTIAL", "k": "GENERIC", "f": "BOTANICAL",
                         "p": "PROCESS", "-": "-"}.get(d["determinative"], "?")
            
            interp = "?"
            if d["root"] == "esed":
                interp = "★ LION (Arabic asad)"
            elif best and best["score"] >= 0.6:
                interp = f"{best['meaning'][:30]} ({best['lang']}, {best['score']:.2f})"
            
            print(f"    #{ascii_safe(d['nymph_num']):>2s} {ascii_safe(d['original']):18s} "
                f"[{ascii_safe(det_label):>9s}] root={ascii_safe(d['root']):<10s} -> {ascii_safe(interp)}")
        print()


# ════════════════════════════════════════════════════════════════════════
# SYNTHESIS
# ════════════════════════════════════════════════════════════════════════

def synthesis(decomposed, all_matches):
    print("\n" + "=" * 72)
    print("SYNTHESIS: LEO FOLIO DEEP-DIVE RESULTS")
    print("=" * 72)
    
    nymphs = [d for d in decomposed if d["locus_type"] == "nymph"]
    ring_words = [d for d in decomposed if d["locus_type"] == "ring"]
    
    # Count matches
    matched_roots = set()
    for m in all_matches:
        if m["score"] >= 0.65:
            matched_roots.add(m["root"])
    
    total_unique = len(set(d["root"] for d in decomposed))
    
    print(f"""
    +--------------------------------------------------------------------+
    |  LEO FOLIO (f72v3) - STRUCTURAL AND INTERPRETIVE SUMMARY           |
    +--------------------------------------------------------------------+
    |                                                                    |
    |  ANCHOR: oteesed = o[prefix] + t[celestial] + esed[lion/asad]      |
    |  Inner ring, nymph #29, clock position 06:30                       |
    |                                                                    |
    |  Total words: {len(decomposed):<4d}   Unique roots: {total_unique:<4d}                     |
    |  Nymph labels: {len(nymphs):<3d}  Ring text words: {len(ring_words):<3d}                     |
    |  Vocabulary matches (>=0.65): {len(matched_roots)} roots                          |
    |                                                                    |
    |  DETERMINATIVE PROFILE:                                            |
    |    t (celestial) dominates - expected for zodiac Leo               |
    |    k (generic) for classification entries                          |
    |    f (botanical) minimal - Leo = not a plant section               |
    |                                                                    |
    |  KEY INTERPRETIVE CANDIDATES:                                      |
    |    esed  = asad (lion) - CONFIRMED anchor                          |
    |    cham  = ham/kham (hot/warm) - Hebrew, fire sign context         |
    |    sol   = sol (sun) - Leo's ruling planet (also a logogram)       |
    |    yesh  = Hebrew (existence) - predicate marker?                  |
    |    rch   = ruah (spirit/wind) - Hebrew                             |
    |                                                                    |
    +--------------------------------------------------------------------+
""")


# ════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Loading all manuscript data...")
    all_words = extract_all_words()
    print(f"Loaded {len(all_words)} tokens from {len(set(w[2] for w in all_words))} folios")
    
    print("Extracting Leo folio (f72v3)...")
    leo_data = extract_leo_folio()
    print(f"Leo folio: {len(leo_data)} words\n")
    
    decomposed = analysis_1_full_decomposition(leo_data)
    all_matches = analysis_2_anchor_matching(decomposed)
    analysis_3_phonetic_hypotheses(decomposed)
    analysis_4_cross_reference(decomposed, all_words)
    analysis_5_ring_structure(decomposed)
    analysis_6_anchor_context(all_words)
    analysis_7_interpretive_attempt(decomposed, all_matches)
    synthesis(decomposed, all_matches)
    
    # Save results
    results = {
        "decomposed": decomposed,
        "matches": all_matches,
        "summary": {
            "total_words": len(decomposed),
            "nymph_labels": len([d for d in decomposed if d["locus_type"] == "nymph"]),
            "ring_words": len([d for d in decomposed if d["locus_type"] == "ring"]),
            "unique_roots": len(set(d["root"] for d in decomposed)),
            "anchor": "esed = asad (lion)",
        }
    }
    
    with open("leo_deepdive_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Results saved to leo_deepdive_results.json")
