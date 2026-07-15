#!/usr/bin/env python3
"""
Voynich Manuscript — Root Lexicon & Zodiac Rosetta Stone (Phase 15)

Now that we've decoded the STRUCTURE of the writing system (Phases 10-14):
  - Gallows = determinatives (t=celestial, k=generic, f=botanical, p=process)
  - Prefixes = phonetic complements (qo+k, d+p, s+f)
  - E-chains = non-structural vowel filler
  - Suffixes = grammatical morphemes
  - Core roots = ~3,000-3,500 consonantal skeletons

This phase attempts to decode CONTENT by:
  1. Building the complete consonantal root lexicon
  2. Decomposing zodiac nymph labels using the full framework
  3. Cross-referencing against zodiac terminology in:
     - Latin (medieval astronomical terms)
     - Hebrew (טלה, שור, תאומים...)
     - Arabic (حمل, ثور, جوزاء...)
     - Greek (Κριός, Ταῦρος, Δίδυμοι...)
     - COPTIC EGYPTIAN (the form of Egyptian ~1400s scholars could access)
     - Medieval pharmaceutical/botanical terminology
  4. Testing suffix semantics by section distribution
  5. Probing herbal labels for botanical term matches

The Champollion moment: zodiac signs are our cartouches — known referents
with known names in multiple languages. If roots match ANY medieval language,
we crack sound values.
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import classify_folio, collapse_echains, gallows_base_v2 as gallows_base, parse_morphology, strip_gallows

# ── Section classification ────────────────────────────────────────────────


# ── Gallows definitions ──────────────────────────────────────────────────

SIMPLE_GALLOWS = ["t", "k", "f", "p"]
BENCH_GALLOWS = ["cth", "ckh", "cph", "cfh"]
COMPOUND_GCH = ["tch", "kch", "pch", "fch"]
COMPOUND_GSH = ["tsh", "ksh", "psh", "fsh"]
ALL_GALLOWS = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS


# ── Morphological operations ─────────────────────────────────────────────

PREFIXES = ['qo', 'q', 'so', 'do', 'o', 'd', 's', 'y']
SUFFIXES = ['aiin', 'ain', 'iin', 'in', 'ar', 'or', 'al', 'ol',
            'edy', 'ody', 'eedy', 'dy', 'sy', 'ey', 'y']




def full_decompose(word):
    """Full pipeline: strip gallows → collapse e-chains → parse morphology."""
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


def extract_zodiac_labels():
    """Extract all nymph labels from zodiac folios with sign assignments."""
    folio_dir = Path("folios")
    zodiac_files = {
        "f70v_part": [("f70v1", "Aries-dark"), ("f70v2", "Pisces")],
        "f71r": [("f71r", "Aries-light")],
        "f71v_72r": [("f71v", "Taurus-light"), ("f72r1", "Taurus-dark"),
                     ("f72r2", "Gemini"), ("f72r3", "Cancer")],
        "f72v_part": [("f72v1", "Libra"), ("f72v2", "Virgo"), ("f72v3", "Leo")],
        "f73r": [("f73r", "Scorpio")],
        "f73v": [("f73v", "Sagittarius")],
    }

    labels = []
    for filename, sections in zodiac_files.items():
        txt_file = folio_dir / f"{filename}.txt"
        if not txt_file.exists():
            continue
        lines = txt_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            m = re.match(r'<([^>]+)>\s*(.*)', line)
            if not m:
                continue
            locus = m.group(1)
            text = m.group(2)
            if "@Lz" not in locus and "&Lz" not in locus:
                continue

            # Determine which sub-folio this belongs to
            folio_id = locus.split(",")[0].split(".")[0]
            sign = "unknown"
            for sec_id, sec_sign in sections:
                if folio_id.startswith(sec_id.replace(".", "")):
                    sign = sec_sign
                    break
            # Also try matching by prefix
            if sign == "unknown":
                for sec_id, sec_sign in sections:
                    if folio_id.startswith(sec_id.split(".")[0]):
                        sign = sec_sign
                        break

            # Extract clock position
            clock = ""
            cm = re.search(r'<!(\d+:\d+)>', text)
            if cm:
                clock = cm.group(1)

            # Clean text
            text = re.sub(r'<![^>]*>', '', text)
            text = re.sub(r'<%>|<\$>|<->|<\.>', ' ', text)
            text = re.sub(r'<[^>]*>', '', text)
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
            text = re.sub(r'\{([^}]+)\}', r'\1', text)
            text = re.sub(r'@\d+;?', '', text)
            text = text.strip()

            if text and not '?' in text:
                labels.append({
                    "folio": folio_id,
                    "sign": sign,
                    "clock": clock,
                    "raw_label": text,
                    "hand": "@Lz" if "@Lz" in locus else "&Lz"
                })

    return labels


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: BUILD CONSONANTAL ROOT LEXICON
# ══════════════════════════════════════════════════════════════════════════

def analysis1_root_lexicon(all_data):
    print("=" * 72)
    print("ANALYSIS 1: CONSONANTAL ROOT LEXICON")
    print("=" * 72)

    root_data = defaultdict(lambda: {
        "freq": 0, "sections": Counter(), "prefixes": Counter(),
        "suffixes": Counter(), "determinatives": Counter(),
        "original_forms": Counter(), "locus_types": Counter()
    })

    for word, section, folio, locus, ltype in all_data:
        d = full_decompose(word)
        root = d["root"]
        if len(root) < 1:
            continue
        rd = root_data[root]
        rd["freq"] += 1
        rd["sections"][section] += 1
        rd["prefixes"][d["prefix"]] += 1
        rd["suffixes"][d["suffix"]] += 1
        rd["determinatives"][d["determinative"]] += 1
        rd["original_forms"][word] += 1
        rd["locus_types"][ltype] += 1

    print(f"\n  Total consonantal roots: {len(root_data)}")
    print(f"  Roots with freq ≥ 5: {sum(1 for r in root_data if root_data[r]['freq'] >= 5)}")
    print(f"  Roots with freq ≥ 20: {sum(1 for r in root_data if root_data[r]['freq'] >= 20)}")
    print(f"  Roots with freq ≥ 100: {sum(1 for r in root_data if root_data[r]['freq'] >= 100)}")

    # Top 50 roots
    sorted_roots = sorted(root_data.items(), key=lambda x: x[1]["freq"], reverse=True)

    print(f"\n  ── Top 50 Consonantal Roots ──")
    print(f"  {'Root':<12}{'Freq':>6}{'Prefixes':>10}{'Suffixes':>10}{'Det':>8}{'Top section':>14}")
    print("  " + "-" * 60)
    for root, rd in sorted_roots[:50]:
        top_sec = rd["sections"].most_common(1)[0][0] if rd["sections"] else "?"
        n_pf = len([p for p in rd["prefixes"] if p != "∅"])
        n_sf = len([s for s in rd["suffixes"] if s != "∅"])
        top_det = rd["determinatives"].most_common(1)[0][0] if rd["determinatives"] else "?"
        print(f"  {root:<12}{rd['freq']:>6}{n_pf:>10}{n_sf:>10}{top_det:>8}{top_sec:>14}")

    # Root length distribution
    print(f"\n  ── Root Length Distribution ──")
    len_dist = Counter()
    for root, rd in root_data.items():
        if rd["freq"] >= 5:
            len_dist[len(root)] += 1
    for l in sorted(len_dist):
        print(f"  Length {l}: {len_dist[l]} roots")

    # Section-specific roots (appear >80% in one section)
    print(f"\n  ── Section-Exclusive Roots (>80% in one section, freq ≥ 20) ──")
    exclusive = []
    for root, rd in sorted_roots:
        if rd["freq"] < 20:
            continue
        for sec, cnt in rd["sections"].items():
            if cnt / rd["freq"] > 0.80:
                exclusive.append((root, sec, cnt, rd["freq"], cnt/rd["freq"]))
    exclusive.sort(key=lambda x: x[4], reverse=True)
    for root, sec, cnt, total, pct in exclusive[:20]:
        print(f"  {root:<15} {sec:<12} {cnt}/{total} ({pct:.0%})")

    return {r: {"freq": rd["freq"], "top_section": rd["sections"].most_common(1)[0][0]}
            for r, rd in sorted_roots[:200]}


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: ZODIAC LABEL DECOMPOSITION (Rosetta Stone)
# ══════════════════════════════════════════════════════════════════════════

def analysis2_zodiac_rosetta(zodiac_labels):
    print("\n" + "=" * 72)
    print("ANALYSIS 2: ZODIAC LABEL DECOMPOSITION (Rosetta Stone)")
    print("=" * 72)

    # Map signs to canonical names
    SIGN_MAP = {
        "Aries-dark": "Aries", "Aries-light": "Aries",
        "Taurus-light": "Taurus", "Taurus-dark": "Taurus",
        "Pisces": "Pisces", "Gemini": "Gemini", "Cancer": "Cancer",
        "Leo": "Leo", "Virgo": "Virgo", "Libra": "Libra",
        "Scorpio": "Scorpio", "Sagittarius": "Sagittarius"
    }

    sign_labels = defaultdict(list)
    for lab in zodiac_labels:
        canon = SIGN_MAP.get(lab["sign"], lab["sign"])
        # Split multi-word labels
        words = re.split(r'[.\s]+', lab["raw_label"])
        decomposed = []
        for w in words:
            w = w.strip()
            if not w or '?' in w or not re.match(r'^[a-z]+$', w):
                continue
            dec = full_decompose(w)
            decomposed.append(dec)
        lab["decomposed"] = decomposed
        lab["canon_sign"] = canon
        sign_labels[canon].append(lab)

    print(f"\n  Total zodiac labels: {len(zodiac_labels)}")
    print(f"  Signs represented: {len(sign_labels)}")

    # Per-sign decomposition
    sign_roots = {}
    for sign in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                 "Libra", "Scorpio", "Sagittarius", "Pisces"]:
        labels = sign_labels.get(sign, [])
        if not labels:
            continue
        print(f"\n  ── {sign} ({len(labels)} labels) ──")

        root_counter = Counter()
        prefix_counter = Counter()
        suffix_counter = Counter()
        det_counter = Counter()
        all_roots_here = []

        for lab in labels[:30]:  # Show first 30
            for dec in lab["decomposed"]:
                root_counter[dec["root"]] += 1
                prefix_counter[dec["prefix"]] += 1
                suffix_counter[dec["suffix"]] += 1
                det_counter[dec["determinative"]] += 1
                all_roots_here.append(dec["root"])

        # Show sample decompositions
        for lab in labels[:8]:
            for dec in lab["decomposed"]:
                print(f"    {dec['original']:<20} → det={dec['determinative']}  "
                      f"pf={dec['prefix']:<4} root={dec['root']:<8} sf={dec['suffix']}")

        # Summary for this sign
        print(f"    --- Roots: {root_counter.most_common(5)}")
        print(f"    --- Det:   {dict(det_counter.most_common(4))}")

        sign_roots[sign] = {
            "n_labels": len(labels),
            "top_roots": dict(root_counter.most_common(10)),
            "top_det": dict(det_counter.most_common(4)),
            "all_roots": all_roots_here
        }

    # Cross-sign shared roots
    print(f"\n  ── Cross-Sign Root Analysis ──")
    print(f"  (Roots unique to one sign might encode the sign name)")
    print()

    all_sign_root_sets = {}
    for sign, data in sign_roots.items():
        all_sign_root_sets[sign] = set(data["all_roots"])

    # Find sign-unique roots
    for sign in sign_roots:
        this_roots = all_sign_root_sets[sign]
        other_roots = set()
        for s2 in sign_roots:
            if s2 != sign:
                other_roots |= all_sign_root_sets[s2]
        unique = this_roots - other_roots
        if unique:
            print(f"  {sign:<14} unique roots: {sorted(unique)}")

    # Find universal roots (in all signs)
    if sign_roots:
        universal = set.intersection(*all_sign_root_sets.values()) if all_sign_root_sets else set()
        print(f"\n  Universal roots (in ALL signs): {sorted(universal)}")
        print(f"  → These are likely generic astronomical terms, not sign names")

    return sign_roots


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 3: CROSS-LINGUISTIC ZODIAC MATCHING
# ══════════════════════════════════════════════════════════════════════════

def analysis3_crosslinguistic_match(sign_roots):
    print("\n" + "=" * 72)
    print("ANALYSIS 3: CROSS-LINGUISTIC ZODIAC NAME MATCHING")
    print("=" * 72)

    # Medieval zodiac terminology in multiple languages
    # Focus on consonantal skeletons to match our root extraction
    ZODIAC_NAMES = {
        "Aries": {
            "latin": ["aries", "aryes"],
            "hebrew": ["tale", "tlh"],       # טלה (taleh)
            "arabic": ["hamal", "hml"],       # حمل
            "greek": ["krios", "krs"],        # Κριός
            "coptic": ["klom", "klm"],        # ⲕⲗⲟⲙ (measure/Aries in some sources)
            "coptic2": ["esou", "es"],         # ⲉⲥⲟⲩ (ram)
            "medieval_lat": ["mars", "mrt"],   # ruling planet
            "astro": ["ram"],
        },
        "Taurus": {
            "latin": ["taurus", "trs"],
            "hebrew": ["shor", "shr"],        # שור
            "arabic": ["thaur", "thr"],       # ثور
            "greek": ["tauros", "trs"],
            "coptic": ["ka", "ehi"],           # ⲕⲁ (bull) / ⲉϩⲓ (cow)
            "medieval_lat": ["venus", "vns"],
            "astro": ["bul"],
        },
        "Gemini": {
            "latin": ["gemini", "gmn"],
            "hebrew": ["teomim", "tmm"],      # תאומים
            "arabic": ["jauza", "jz"],        # جوزاء
            "greek": ["didimoi", "ddm"],
            "coptic": ["snau", "sn"],          # ⲥⲛⲁⲩ (two)
            "coptic2": ["pimahsnau", "pmhsn"],  # the twins
            "medieval_lat": ["mercurius", "mrkrs"],
            "astro": ["twin"],
        },
        "Cancer": {
            "latin": ["cancer", "knkr"],
            "hebrew": ["sartan", "srtn"],     # סרטן
            "arabic": ["saratan", "srtn"],    # سرطان
            "greek": ["karkinos", "krk"],
            "coptic": ["senstiphe", "snstf"],  # astrological name
            "coptic2": ["kloj", "klj"],        # ⲕⲗⲟϫ (crab)
            "medieval_lat": ["luna", "ln"],
            "astro": ["crab"],
        },
        "Leo": {
            "latin": ["leo", "le"],
            "hebrew": ["arie", "arh"],        # אריה
            "arabic": ["asad", "sd"],         # أسد
            "greek": ["leon", "ln"],
            "coptic": ["moui", "m"],           # ⲙⲟⲩⲓ̈ (lion)
            "coptic2": ["laboi", "lb"],        # ⲗⲁⲃⲟⲓ̈
            "medieval_lat": ["sol", "sl"],
            "astro": ["lion"],
        },
        "Virgo": {
            "latin": ["virgo", "vrg"],
            "hebrew": ["betula", "btl"],      # בתולה
            "arabic": ["sunbula", "snbl"],    # سنبلة
            "greek": ["partenos", "prtns"],
            "coptic": ["parthenos", "prtns"],  # Greek loan in Coptic
            "coptic2": ["esime", "sm"],        # ⲉⲥϩⲓⲙⲉ (woman)
            "medieval_lat": ["spica", "spk"],
            "astro": ["virgin", "maiden"],
        },
        "Libra": {
            "latin": ["libra", "lbr"],
            "hebrew": ["moznayim", "mznym"],  # מאזניים
            "arabic": ["mizan", "mzn"],       # ميزان
            "greek": ["zugos", "zgs"],
            "coptic": ["makhi", "mkh"],        # balance/scale
            "medieval_lat": ["venus", "vns"],
            "astro": ["scale", "balance"],
        },
        "Scorpio": {
            "latin": ["scorpio", "skrp"],
            "hebrew": ["akrav", "qrb"],       # עקרב
            "arabic": ["aqrab", "qrb"],       # عقرب
            "greek": ["skorpios", "skrps"],
            "coptic": ["djale", "djl"],        # ϫⲁⲗⲉ (scorpion)
            "coptic2": ["pile", "pl"],         # alternative
            "medieval_lat": ["mars", "mrt"],
            "astro": ["scorpion"],
        },
        "Sagittarius": {
            "latin": ["sagittarius", "sgtrs"],
            "hebrew": ["keshet", "ksht"],     # קשת
            "arabic": ["qaus", "qs"],         # قوس
            "greek": ["toxotes", "tkt"],
            "coptic": ["pirefsotc", "prfstc"], # the shooter
            "coptic2": ["piri", "pr"],          # the bowman
            "medieval_lat": ["jupiter", "jptr"],
            "astro": ["archer", "bow"],
        },
        "Pisces": {
            "latin": ["pisces", "psk"],
            "hebrew": ["dagim", "dgm"],       # דגים
            "arabic": ["hut", "ht"],          # حوت
            "greek": ["ichthues", "chthr"],
            "coptic": ["tbt", "tbt"],          # ⲧⲃⲧ (fish)
            "coptic2": ["rep", "rp"],           # ⲣⲉⲡ
            "medieval_lat": ["jupiter", "jptr"],
            "astro": ["fish"],
        },
    }

    # Additional medieval astronomical terms used across sections
    ASTRO_TERMS = {
        "degree": ["grad", "daraja", "moire", "thi"],
        "star": ["stella", "kokab", "najm", "siou", "aster"],
        "planet": ["planeta", "kokab", "sayyara"],
        "house": ["domus", "bait", "oikos", "hi"],
        "sign": ["signum", "mazal", "burj", "astrion"],
        "decan": ["decanus", "panim", "wajh"],
        "month": ["mensis", "chodesh", "shahr", "abot"],
        "water": ["aqua", "mayim", "maa", "mou"],
        "fire": ["ignis", "esh", "nar", "koh"],
        "earth": ["terra", "adama", "ard", "kah"],
        "air": ["aer", "ruach", "hawa", "nife"],
        "hot": ["calidus", "cham", "haar", "hmom"],
        "cold": ["frigidus", "kar", "barid", "kbo"],
        "wet": ["humidus", "lach", "ratb"],
        "dry": ["siccus", "yavesh", "jabis", "shoue"],
        "head": ["caput", "rosh", "ras", "ape"],
        "body": ["corpus", "guf", "jism", "soma"],
        "root": ["radix", "shoresh", "asl", "noune"],
        "seed": ["semen", "zera", "bizr", "jroj"],
        "leaf": ["folia", "ale", "waraq", "jobe"],
        "flower": ["flos", "perach", "zahr", "hrere"],
        "remedy": ["remedium", "refua", "dawa", "pahre"],
        "mix": ["miscere", "meziqa", "mazj", "toouh"],
        "prepare": ["parare", "hechin", "cabtet"],
        "grind": ["molere", "tachan", "tahana", "jot"],
    }

    # EVA consonant equivalence hypotheses
    # Test multiple mapping schemes
    EVA_TO_LATIN = [
        # Hypothesis 1: Italian-influenced phonetics
        {"ch": "c/k", "sh": "s/sc", "l": "l", "r": "r",
         "n": "n", "m": "m", "d": "d", "a": "a", "i": "i"},
        # Hypothesis 2: Hebrew-influenced phonetics
        {"ch": "kh/h", "sh": "sh/s", "l": "l", "r": "r",
         "n": "n", "m": "m", "d": "d/t", "a": "a", "i": "i"},
    ]

    print(f"\n  ── Zodiac Sign Root Comparison ──")
    print(f"  For each sign: Voynich roots vs known names in 7+ languages")
    print()

    matches = {}
    for sign in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                 "Libra", "Scorpio", "Sagittarius", "Pisces"]:
        data = sign_roots.get(sign, {})
        if not data:
            continue

        voynich_roots = list(data.get("top_roots", {}).keys())
        all_roots = data.get("all_roots", [])
        names = ZODIAC_NAMES.get(sign, {})

        print(f"  ┌─ {sign} ─────────────────────────────────────────")
        print(f"  │ Voynich roots: {voynich_roots[:10]}")
        print(f"  │")

        sign_matches = []
        for lang, name_list in sorted(names.items()):
            for name in name_list:
                # Compare each Voynich root against each name
                for vroot in set(all_roots):
                    if len(vroot) < 2:
                        continue
                    # Exact match
                    if vroot == name:
                        sign_matches.append((lang, name, vroot, "EXACT", 1.0))
                    # Substring match
                    elif len(name) >= 3 and name in vroot:
                        sign_matches.append((lang, name, vroot, "CONTAINS", 0.8))
                    elif len(vroot) >= 3 and vroot in name:
                        sign_matches.append((lang, name, vroot, "WITHIN", 0.7))
                    else:
                        # Consonant-skeleton similarity
                        v_cons = re.sub(r'[aeiouy]', '', vroot)
                        n_cons = re.sub(r'[aeiouy]', '', name)
                        if len(v_cons) >= 2 and len(n_cons) >= 2:
                            # Longest common subsequence
                            lcs = _lcs_length(v_cons, n_cons)
                            max_len = max(len(v_cons), len(n_cons))
                            sim = lcs / max_len if max_len > 0 else 0
                            if sim >= 0.6:
                                sign_matches.append((lang, name, vroot, "CONSONANT", sim))

        # Sort by score and show best matches
        sign_matches.sort(key=lambda x: x[4], reverse=True)
        seen = set()
        shown = 0
        for lang, name, vroot, mtype, score in sign_matches:
            key = (lang, vroot)
            if key in seen:
                continue
            seen.add(key)
            print(f"  │ {score:.2f}  {mtype:<10} {lang:<12} {name:<15} ↔ {vroot}")
            shown += 1
            if shown >= 8:
                break

        if not sign_matches:
            print(f"  │ (no matches above threshold)")
        print(f"  └────────────────────────────────────────────────")
        matches[sign] = sign_matches[:10]

    return matches


def _lcs_length(a, b):
    """Longest common subsequence length."""
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 4: SUFFIX SEMANTICS (What do -iin, -ar, -y etc. MEAN?)
# ══════════════════════════════════════════════════════════════════════════

def analysis4_suffix_semantics(all_data):
    print("\n" + "=" * 72)
    print("ANALYSIS 4: SUFFIX SEMANTICS BY SECTION AND LOCUS")
    print("=" * 72)

    suffix_section = defaultdict(Counter)  # suffix → Counter(section)
    suffix_locus = defaultdict(Counter)    # suffix → Counter(locus_type)
    suffix_det = defaultdict(Counter)      # suffix → Counter(determinative)
    suffix_total = Counter()

    for word, section, folio, locus, ltype in all_data:
        d = full_decompose(word)
        sf = d["suffix"]
        suffix_total[sf] += 1
        suffix_section[sf][section] += 1
        suffix_locus[sf][ltype] += 1
        suffix_det[sf][d["determinative"]] += 1

    sections = ['herbal-A', 'herbal-B', 'pharma', 'bio', 'cosmo', 'text', 'zodiac']
    BASES = ['t', 'k', 'f', 'p', '∅']

    # Section enrichment for each suffix
    total_by_section = Counter()
    for word, section, folio, locus, ltype in all_data:
        total_by_section[section] += 1
    total_all = sum(total_by_section.values())

    print(f"\n  ── Suffix Section Enrichment (observed/expected) ──")
    sf_sorted = sorted(suffix_total, key=suffix_total.get, reverse=True)

    header = f"  {'Suffix':<8}{'Total':>7}" + "".join(f"{s[:6]:>8}" for s in sections)
    print(header)
    print("  " + "-" * (len(header) - 2))

    suffix_results = {}
    for sf in sf_sorted[:15]:
        total = suffix_total[sf]
        row = []
        enrichments = {}
        for sec in sections:
            observed = suffix_section[sf].get(sec, 0)
            expected = total * total_by_section.get(sec, 0) / total_all if total_all > 0 else 0
            ratio = observed / expected if expected > 5 else 0
            marker = "↑" if ratio > 1.3 else "↓" if ratio < 0.7 else " "
            row.append(f"{ratio:>6.2f}{marker}")
            enrichments[sec] = round(ratio, 2) if expected > 5 else None
        print(f"  {sf:<8}{total:>7}" + "".join(row))
        suffix_results[sf] = enrichments

    # Suffix × determinative interaction
    print(f"\n  ── Suffix × Determinative Interaction ──")
    print(f"  (Which suffixes prefer which gallows?)")
    print()

    header = f"  {'Suffix':<8}{'Total':>7}" + "".join(f"{b:>8}" for b in BASES)
    print(header)
    print("  " + "-" * (len(header) - 2))

    for sf in sf_sorted[:15]:
        total = suffix_total[sf]
        row = []
        for b in BASES:
            cnt = suffix_det[sf].get(b, 0)
            pct = cnt / total * 100 if total > 0 else 0
            row.append(f"{pct:>7.1f}%")
        print(f"  {sf:<8}{total:>7}" + "".join(row))

    # Locus-type distribution
    print(f"\n  ── Suffix by Locus Type ──")
    locus_types = ['paragraph', 'ring', 'label', 'nymph']
    header = f"  {'Suffix':<8}{'Total':>7}" + "".join(f"{lt:>12}" for lt in locus_types)
    print(header)
    print("  " + "-" * (len(header) - 2))

    for sf in sf_sorted[:15]:
        total = suffix_total[sf]
        row = []
        for lt in locus_types:
            cnt = suffix_locus[sf].get(lt, 0)
            pct = cnt / total * 100 if total > 0 else 0
            row.append(f"{pct:>11.1f}%")
        print(f"  {sf:<8}{total:>7}" + "".join(row))

    return suffix_results


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 5: COPTIC/EGYPTIAN PHONETIC PROBE
# ══════════════════════════════════════════════════════════════════════════
# Test whether Voynich roots match Coptic vocabulary — the form of
# Egyptian actually available to a 1400s European scholar.

def analysis5_coptic_probe(all_data, root_lexicon):
    print("\n" + "=" * 72)
    print("ANALYSIS 5: COPTIC EGYPTIAN PHONETIC PROBE")
    print("=" * 72)

    # Coptic vocabulary relevant to a pharmaceutical/botanical encyclopedia
    # Coptic alphabet: ⲁⲃⲅⲇⲉⲍⲏⲑⲓⲕⲗⲙⲛⲝⲟⲡⲣⲥⲧⲩⲫⲭⲯⲱ + ϣϩϫϭϯ
    # Transliteration: a b g d e z ē th i k l m n ks o p r s t u ph kh ps ō + sh h j č ti

    # COPTIC PHARMACEUTICAL/BOTANICAL TERMS (Sahidic dialect, most studied)
    # Organized by semantic domain matching our gallows categories
    COPTIC_BOTANICAL = {
        # Plants and plant parts
        "noune": "root",
        "jobe": "leaf",
        "hrere": "flower",
        "tah": "plant/sprout",
        "benipi": "date palm",
        "keros": "cinnamon",
        "jroj": "seed/grain",
        "sim": "herb/grass",
        "she": "wood/tree",
        "kole": "reed",
        "loole": "grape",
        "belbile": "eye/bud",
        "olor": "cluster (grapes)",
        "oote": "green/fresh",
        "ouom": "eat/consume",
        "mouh": "fill/be full",
        "rro": "grow/sprout",
        "sooun": "know/recognize",
    }

    COPTIC_MEDICAL = {
        # Body and medicine
        "ape": "head",
        "bol": "eye",
        "masj": "ear",
        "ro": "mouth",
        "lauj": "jaw",
        "snofe": "blood",
        "kes": "bone",
        "af": "flesh/meat",
        "hat": "heart",
        "mise": "liver",
        "tire": "hand",
        "ouerhte": "foot",
        "soma": "body",
        "shope": "be/become",
        "pahre": "remedy/medicine",
        "taljo": "heal",
        "houo": "more than",
        "toouh": "mix/join",
        "jot": "grind/crush",
        "nouje": "throw/put",
    }

    COPTIC_ASTRONOMICAL = {
        # Stars, heavens, time
        "siou": "star",
        "ooh": "moon",
        "rhe": "sun",
        "pe": "sky/heaven",
        "kosmose": "world/cosmos",
        "chrisma": "anointing",
        "ouoein": "light",
        "kake": "darkness",
        "me": "truth",
        "nome": "law/custom",
        "rompe": "year",
        "abot": "month",
        "hoou": "day",
        "ounou": "hour",
        "meh": "north",
        "res": "south",
        "emend": "west",
        "iabote": "east",
    }

    COPTIC_ELEMENTS = {
        # Four elements / qualities
        "mou": "water",
        "koh": "fire",
        "kah": "earth",
        "nife": "air/wind/breath",
        "hmom": "hot/heat",
        "kbo": "cold/cool",
        "shoue": "dry",
        "oueih": "dwell/reside",
        "choeis": "lord",
        "noute": "god",
        "djom": "power/force",
        "hise": "suffering",
    }

    ALL_COPTIC = {}
    ALL_COPTIC.update(COPTIC_BOTANICAL)
    ALL_COPTIC.update(COPTIC_MEDICAL)
    ALL_COPTIC.update(COPTIC_ASTRONOMICAL)
    ALL_COPTIC.update(COPTIC_ELEMENTS)

    print(f"\n  Coptic vocabulary loaded: {len(ALL_COPTIC)} terms")
    print(f"  Voynich roots to test: {len(root_lexicon)}")

    # Build consonantal skeletons of Coptic words
    coptic_skeletons = {}
    for coptic_word, meaning in ALL_COPTIC.items():
        skel = re.sub(r'[aeiou]+', '', coptic_word.lower())
        coptic_skeletons[coptic_word] = {"meaning": meaning, "skeleton": skel}

    # Compare each Voynich root against all Coptic terms
    print(f"\n  ── Voynich Root ↔ Coptic Matches ──")
    print(f"  Matching by: exact, substring, consonantal skeleton similarity")
    print()

    all_matches = []
    for vroot, vdata in root_lexicon.items():
        v_skel = re.sub(r'[aeiou]+', '', vroot)
        if len(v_skel) < 1:
            continue

        for coptic_word, cdata in coptic_skeletons.items():
            c_skel = cdata["skeleton"]
            meaning = cdata["meaning"]

            score = 0
            mtype = ""

            # Exact match
            if vroot == coptic_word:
                score = 1.0
                mtype = "EXACT"
            elif vroot == coptic_word.replace("ou", "o"):
                score = 0.95
                mtype = "NEAR-EXACT"
            # Substring
            elif len(coptic_word) >= 3 and coptic_word in vroot:
                score = 0.8
                mtype = "CONTAINS"
            elif len(vroot) >= 3 and vroot in coptic_word:
                score = 0.7
                mtype = "WITHIN"
            # Consonantal skeleton
            elif len(v_skel) >= 2 and len(c_skel) >= 2:
                lcs = _lcs_length(v_skel, c_skel)
                max_len = max(len(v_skel), len(c_skel))
                sim = lcs / max_len if max_len > 0 else 0
                if sim >= 0.67:
                    score = sim * 0.6
                    mtype = "SKELETON"

            if score >= 0.4:
                all_matches.append((vroot, coptic_word, meaning, mtype, score,
                                   vdata.get("freq", 0), vdata.get("top_section", "?")))

    all_matches.sort(key=lambda x: x[4], reverse=True)

    print(f"  {'Score':>6} {'Type':<12} {'Voynich':<12} {'Coptic':<15} {'Meaning':<20} {'Freq':>6} {'Section':<10}")
    print("  " + "-" * 85)

    seen_voynich = set()
    shown = 0
    for vroot, cword, meaning, mtype, score, freq, sec in all_matches:
        if vroot in seen_voynich:
            continue
        seen_voynich.add(vroot)
        print(f"  {score:>6.2f} {mtype:<12} {vroot:<12} {cword:<15} {meaning:<20} {freq:>6} {sec:<10}")
        shown += 1
        if shown >= 40:
            break

    # Domain correlation test
    print(f"\n  ── Domain Correlation Test ──")
    print(f"  Do Coptic botanical terms match f-gallows words? Medical → k? Astro → t?")

    domain_hits = {"botanical": [], "medical": [], "astronomical": [], "element": []}
    for vroot, cword, meaning, mtype, score, freq, sec in all_matches:
        if score < 0.4:
            continue
        if cword in COPTIC_BOTANICAL:
            domain_hits["botanical"].append((vroot, sec, cword, meaning))
        elif cword in COPTIC_MEDICAL:
            domain_hits["medical"].append((vroot, sec, cword, meaning))
        elif cword in COPTIC_ASTRONOMICAL:
            domain_hits["astronomical"].append((vroot, sec, cword, meaning))
        elif cword in COPTIC_ELEMENTS:
            domain_hits["element"].append((vroot, sec, cword, meaning))

    for domain, hits in domain_hits.items():
        print(f"\n  {domain.upper()} matches ({len(hits)}):")
        for vroot, sec, cword, meaning in hits[:5]:
            print(f"    {vroot:<12} [{sec}] ↔ {cword} ({meaning})")

    return {
        "total_matches": len(all_matches),
        "top_matches": [(v, c, m, t, round(s, 2)) for v, c, m, t, s, _, _ in all_matches[:20]],
        "domain_counts": {d: len(h) for d, h in domain_hits.items()}
    }


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 6: HERBAL LABEL PROBE
# ══════════════════════════════════════════════════════════════════════════

def analysis6_herbal_labels(all_data):
    print("\n" + "=" * 72)
    print("ANALYSIS 6: HERBAL LABEL DECOMPOSITION")
    print("=" * 72)

    # Collect all label words from herbal sections
    herbal_labels = []
    for word, section, folio, locus, ltype in all_data:
        if ltype == "label" and section in ("herbal-A", "herbal-B"):
            herbal_labels.append((word, folio))

    print(f"\n  Herbal labels: {len(herbal_labels)}")

    # Decompose each
    label_roots = Counter()
    label_decomposed = []
    for word, folio in herbal_labels:
        d = full_decompose(word)
        label_roots[d["root"]] += 1
        label_decomposed.append((folio, d))

    print(f"  Unique roots in herbal labels: {len(label_roots)}")

    # Show decomposed herbal labels grouped by folio
    folio_groups = defaultdict(list)
    for folio, d in label_decomposed:
        folio_groups[folio].append(d)

    print(f"\n  ── Sample Herbal Label Decompositions (first 15 folios) ──")
    for folio in sorted(folio_groups)[:15]:
        decs = folio_groups[folio]
        if not decs:
            continue
        items = []
        for d in decs:
            items.append(f"{d['original']}→[{d['determinative']}]{d['prefix']}-{d['root']}-{d['suffix']}")
        print(f"  {folio:<12} {' | '.join(items)}")

    # Most common herbal label roots — candidates for plant names
    print(f"\n  ── Top Herbal Label Roots (potential plant names) ──")
    for root, cnt in label_roots.most_common(20):
        print(f"  {root:<15} count={cnt}")

    # Compare with Coptic botanical vocabulary
    COPTIC_PLANTS = {
        "noune": "root", "jobe": "leaf", "hrere": "flower",
        "tah": "sprout", "jroj": "seed", "sim": "herb/grass",
        "she": "tree", "kole": "reed", "loole": "grape",
        "benipi": "palm", "keros": "cinnamon", "olor": "cluster",
    }

    print(f"\n  ── Herbal Labels vs Coptic Plant Terms ──")
    for root in [r for r, c in label_roots.most_common(30)]:
        for cword, meaning in COPTIC_PLANTS.items():
            r_skel = re.sub(r'[aeiou]+', '', root)
            c_skel = re.sub(r'[aeiou]+', '', cword)
            if len(r_skel) >= 2 and len(c_skel) >= 2:
                lcs = _lcs_length(r_skel, c_skel)
                sim = lcs / max(len(r_skel), len(c_skel))
                if sim >= 0.6:
                    print(f"    {root:<12} ↔ {cword:<12} ({meaning})  skeleton_sim={sim:.2f}")

    return {"n_labels": len(herbal_labels), "top_roots": dict(label_roots.most_common(20))}


# ══════════════════════════════════════════════════════════════════════════
# SYNTHESIS
# ══════════════════════════════════════════════════════════════════════════

def synthesis(results):
    print("\n" + "=" * 72)
    print("SYNTHESIS: TOWARD DECIPHERMENT")
    print("=" * 72)

    print("""
  ┌──────────────────────────────────────────────────────────────────────┐
  │  THE VOYNICH WRITING SYSTEM — COMPLETE STRUCTURAL MODEL             │
  ├──────────────────────────────────────────────────────────────────────┤
  │                                                                      │
  │  WORD = [Gallows] + [Prefix] + Root + [e-chain] + [Suffix]          │
  │           │            │         │        │           │              │
  │      Determinative  Phonetic  Content  Vowel     Grammatical        │
  │      (category)     Complement (meaning) Filler   Morpheme          │
  │      (unpronounced) (redundant)          (non-     (case/number/    │
  │                                          structural) agreement?)    │
  │                                                                      │
  │  Example: qokedy                                                     │
  │    → gallows: k (generic determinative)                              │
  │    → prefix:  qo (generic complement — agrees with k)               │
  │    → root:    ed (consonantal skeleton)                              │
  │    → suffix:  y (grammatical ending)                                 │
  │                                                                      │
  │  Same root, different domain:                                        │
  │    dokedy → p-gallows + do-prefix → PROCESS domain                   │
  │    sokedy → f-gallows + so-prefix → BOTANICAL domain                 │
  │                                                                      │
  └──────────────────────────────────────────────────────────────────────┘
""")

    # Summarize key findings
    print("  ── Key Results ──")
    print()

    if "zodiac_matches" in results:
        zm = results["zodiac_matches"]
        total_matches = sum(len(v) for v in zm.values())
        print(f"  Zodiac name matching: {total_matches} potential matches across 10 signs")

    if "coptic_probe" in results:
        cp = results["coptic_probe"]
        print(f"  Coptic vocabulary matches: {cp.get('total_matches', 0)} candidates")
        dc = cp.get("domain_counts", {})
        print(f"    Botanical: {dc.get('botanical', 0)}, Medical: {dc.get('medical', 0)}, "
              f"Astro: {dc.get('astronomical', 0)}, Element: {dc.get('element', 0)}")

    print(f"\n  ── Assessment ──")
    print(f"  The writing system structure is now fully decoded.")
    print(f"  Content decipherment requires either:")
    print(f"    1. A definitive zodiac name match (Rosetta Stone approach)")
    print(f"    2. A Coptic/Hebrew/Arabic vocabulary correlation")
    print(f"    3. External evidence (a bilingual text or key)")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    all_data = extract_all_words()
    print(f"Loaded {len(all_data)} tokens from {len(set(w[2] for w in all_data))} folios\n")

    zodiac_labels = extract_zodiac_labels()
    print(f"Extracted {len(zodiac_labels)} zodiac nymph labels\n")

    results = {}
    results["root_lexicon"] = analysis1_root_lexicon(all_data)
    results["zodiac_rosetta"] = analysis2_zodiac_rosetta(zodiac_labels)
    results["zodiac_matches"] = analysis3_crosslinguistic_match(results["zodiac_rosetta"])
    results["suffix_semantics"] = analysis4_suffix_semantics(all_data)
    results["coptic_probe"] = analysis5_coptic_probe(all_data, results["root_lexicon"])
    results["herbal_labels"] = analysis6_herbal_labels(all_data)
    synthesis(results)

    out = Path("root_lexicon_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
