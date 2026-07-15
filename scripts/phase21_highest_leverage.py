#!/usr/bin/env python3
"""
Phase 21 — Highest-Leverage Attacks
====================================

Three integrated analyses:

  21a) WATER-SIGN VOCABULARY CRACK — The 37 Water-exclusive residual roots
       matched against expanded Coptic/Arabic aquatic, lunar, body-part,
       and cold-wet terminology. Also test Fire-exclusive roots against
       hot-dry vocabulary.

  21b) VERB CONJUGATION PARADIGM — Map -ey vs -edy vs -ody vs -ol on
       s-prefix verbs. Do they encode tense/aspect/person? Test by
       section, position, and collocational frame.

  21c) BIO-SECTION TRANSLATION — Apply the full grammar model
       (p-opener, s-verb, qokeedy relative, gallows determinatives,
       confirmed vocabulary) to translate a bio-section paragraph
       where qokeedy is enriched 2×.
"""

import re, json, math
from pathlib import Path
from collections import Counter, defaultdict
from common import collapse_echains, full_decompose, gallows_base, parse_morphology, strip_gallows

# ══════════════════════════════════════════════════════════════════
# MORPHOLOGICAL PIPELINE
# ══════════════════════════════════════════════════════════════════

SIMPLE_GALLOWS = ["t","k","f","p"]
BENCH_GALLOWS  = ["cth","ckh","cph","cfh"]
COMPOUND_GCH   = ["tch","kch","pch","fch"]
COMPOUND_GSH   = ["tsh","ksh","psh","fsh"]
ALL_GALLOWS    = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

PREFIXES = ['qo','q','so','do','o','d','s','y']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol',
            'edy','ody','eedy','dy','sy','ey','y']






# ══════════════════════════════════════════════════════════════════
# CONFIRMED VOCABULARY (cumulative through Phase 20)
# ══════════════════════════════════════════════════════════════════

CONFIRMED_VOCAB = {
    # Phase 13-17 core
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
    # Phase 20 additions
    "eosh":  ("dry", "Coptic", 0.80),
    "sheo":  ("dry(variant)", "Coptic", 0.80),
    "choam": ("hot", "Coptic", 0.75),
    "rar":   ("king", "Coptic", 0.70),
}

# ══════════════════════════════════════════════════════════════════
# EXPANDED GLOSSARIES — much deeper coverage for Phase 21
# ══════════════════════════════════════════════════════════════════

# Sahidic Coptic — broader vocabulary (Crum, Westendorf)
COPTIC_EXPANDED = {
    # Water/liquid
    "moou":"water", "eioor":"river/canal", "iam":"sea/ocean", "iom":"sea",
    "note":"rain", "ouon":"wave", "baphe":"dew",
    "oueih":"pour", "bel":"flow/spring", "mou":"die/be still",
    # Cold/wet
    "kebe":"cold", "nesh":"wet/soft", "kabh":"cool/refresh",
    "slol":"moisten",
    # Hot/dry
    "sate":"fire", "cham":"hot", "shuoe":"dry", "rouhe":"burn",
    "koulh":"kindle",
    # Moon/night
    "ioh":"moon", "ouohe":"night", "kake":"darkness",
    "ouoein":"light", "rouhe":"evening",
    # Body parts (expanded — key for bio section)
    "ape":"head", "mekh":"neck", "shedj":"arm", "esnau":"shoulder",
    "hat":"heart", "hete":"belly/womb", "tbe":"finger", "ouoerdte":"foot",
    "kole":"knee", "meros":"thigh", "bal":"eye", "mashdj":"ear",
    "ro":"mouth", "les":"tongue", "sne":"brother/rib", "kos":"bone",
    "snof":"blood", "hro":"face", "hise":"womb",
    "shalal":"uterus/womb", "she":"tree/womb(secondary)",
    "eire":"make/do", "shel":"vessel/vein",
    # Colors (possible astrological)
    "ouobs":"white", "km":"black", "shar":"red", "ouon":"green",
    # Celestial
    "re":"sun", "siou":"star", "pe":"sky/heaven", "etpe":"heaven",
    "souro":"saturn", "moui":"jupiter",
    # Actions/verbs
    "ei":"come", "bek":"go", "nau":"see", "shem":"walk",
    "hmos":"sit", "ahi":"stand", "she":"cut/measure",
    "shep":"receive", "chi":"take", "shal":"pray",
    "herise":"guard", "arche":"begin", "hol":"fly",
    "sol":"counsel", "hor":"send/compel",
    # Abstract
    "choeis":"lord", "rro":"king", "noub":"gold", "hat":"silver",
    "hom":"power", "bom":"strength", "ran":"name", "me":"truth",
    "sho":"hundred", "min":"road/way",
    # Medical/humoral
    "hebs":"clothe/cover", "loukh":"mix/compound",
    "shenoufe":"heal", "shaje":"speak/word",
    "pharmakon":"drug(Greek loan)", "eho":"remedy",
    "osh":"cut/amputate",
}

# Arabic astrological — expanded
ARABIC_EXPANDED = {
    # Zodiac signs
    "hamal":"ram/Aries", "thawr":"bull/Taurus", "jawza":"twins/Gemini",
    "saratan":"crab/Cancer", "asad":"lion/Leo", "sunbula":"ear/Virgo",
    "mizan":"scales/Libra", "aqrab":"scorpion/Scorpio",
    "qaws":"bow/Sagittarius", "jady":"goat/Capricorn",
    "dalw":"bucket/Aquarius", "hut":"fish/Pisces",
    # Planets
    "shams":"sun", "qamar":"moon", "zuhal":"saturn",
    "mushtari":"jupiter", "mirrikh":"mars",
    "zuhara":"venus", "utarid":"mercury",
    # Elements/qualities
    "nar":"fire", "maa":"water", "turab":"earth", "hawa":"air",
    "harr":"hot", "barid":"cold", "ratb":"wet", "yabis":"dry",
    # Body
    "ras":"head", "qalb":"heart", "sadr":"chest", "batn":"belly",
    "yad":"hand", "rijl":"foot", "ayn":"eye", "uzn":"ear",
    "fakhd":"thigh", "rukba":"knee", "dhira":"forearm",
    # Medical
    "dawa":"medicine/remedy", "marad":"disease", "shifa":"healing",
    "dam":"blood", "hulq":"throat", "jild":"skin",
    # Abstract
    "rabb":"lord", "malik":"king", "nur":"light", "zulm":"darkness",
    "hayy":"alive", "mayyit":"dead", "ilm":"knowledge",
    "hukm":"judgment/rule", "burj":"tower/sign",
}

# ══════════════════════════════════════════════════════════════════
# SIGN DATA
# ══════════════════════════════════════════════════════════════════

ZODIAC_MAP = {
    "f70v1": "Aries-dark", "f71r": "Aries-light",
    "f71v": "Taurus-light", "f72r1": "Taurus-dark",
    "f72r2": "Gemini", "f72r3": "Cancer",
    "f72v3": "Leo", "f72v2": "Virgo", "f72v1": "Libra",
    "f73r": "Scorpio", "f73v": "Sagittarius", "f70v2": "Pisces",
}

SIGN_PROPERTIES = {
    "Aries":       {"element":"Fire",  "modality":"Cardinal", "ruler":"Mars",    "quality":"hot-dry",   "body":"head"},
    "Taurus":      {"element":"Earth", "modality":"Fixed",    "ruler":"Venus",   "quality":"cold-dry",  "body":"neck/throat"},
    "Gemini":      {"element":"Air",   "modality":"Mutable",  "ruler":"Mercury", "quality":"hot-wet",   "body":"arms/lungs"},
    "Cancer":      {"element":"Water", "modality":"Cardinal", "ruler":"Moon",    "quality":"cold-wet",  "body":"chest/stomach"},
    "Leo":         {"element":"Fire",  "modality":"Fixed",    "ruler":"Sun",     "quality":"hot-dry",   "body":"heart/back"},
    "Virgo":       {"element":"Earth", "modality":"Mutable",  "ruler":"Mercury", "quality":"cold-dry",  "body":"intestines"},
    "Libra":       {"element":"Air",   "modality":"Cardinal", "ruler":"Venus",   "quality":"hot-wet",   "body":"kidneys"},
    "Scorpio":     {"element":"Water", "modality":"Fixed",    "ruler":"Mars",    "quality":"cold-wet",  "body":"genitals"},
    "Sagittarius": {"element":"Fire",  "modality":"Mutable",  "ruler":"Jupiter", "quality":"hot-dry",   "body":"thighs"},
    "Pisces":      {"element":"Water", "modality":"Mutable",  "ruler":"Jupiter", "quality":"cold-wet",  "body":"feet"},
}

def base_sign(s):
    return s.replace("-dark","").replace("-light","")

# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════

def clean_token(tok):
    tok = tok.strip().replace("'","")
    tok = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', tok)
    tok = re.sub(r'\{([^}]+)\}', r'\1', tok)
    tok = re.sub(r'@\d+;?', '', tok)
    tok = re.sub(r'[^a-z]', '', tok)
    return tok

def extract_zodiac_data():
    folio_dir = Path("folios")
    zodiac = {}
    for txt_file in sorted(folio_dir.glob("*.txt")):
        text = txt_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        current_section = None
        for line in lines:
            line_s = line.strip()
            sec_match = re.match(r'^<(f\d+[rv]\d?)>\s', line_s)
            if sec_match:
                current_section = sec_match.group(1); continue
            locus_match = re.match(r'<(f\d+[rv]\d?)\.\d+', line_s)
            if locus_match:
                current_section = locus_match.group(1)
            if not current_section or current_section not in ZODIAC_MAP: continue
            sign = ZODIAC_MAP[current_section]
            if sign not in zodiac:
                zodiac[sign] = {"ring_words":[], "nymph_words":[]}
            if "@Cc" in line_s:
                m = re.match(r'<([^>]+)>\s*(.*)', line_s)
                if m:
                    raw = m.group(2)
                    raw = re.sub(r'<![\d:]+>','',raw)
                    raw = re.sub(r'<![^>]*>','',raw)
                    raw = re.sub(r'<%>|<\$>|<->|<\.>',' ',raw)
                    raw = re.sub(r'<[^>]*>','',raw)
                    raw = re.sub(r'\?\?\?','',raw)
                    tokens = re.split(r'[.\s,]+', raw)
                    clean = [clean_token(t) for t in tokens
                             if clean_token(t) and len(clean_token(t)) >= 2 and '?' not in t]
                    zodiac[sign]["ring_words"].extend(clean)
    return zodiac

def extract_all_words():
    folio_dir = Path("folios")
    all_data = []
    for txt_file in sorted(folio_dir.glob("*.txt")):
        stem = txt_file.stem
        m_num = re.match(r'f(\d+)', stem)
        if not m_num: continue
        num = int(m_num.group(1))
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
            text = re.sub(r'<![\d:]+>','',text)
            text = re.sub(r'<![^>]*>','',text)
            text = re.sub(r'<%>|<\$>|<->|<\.>',' ',text)
            text = re.sub(r'<[^>]*>','',text)
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
            text = re.sub(r'\{([^}]+)\}', r'\1', text)
            text = re.sub(r'@\d+;?','',text)
            text = re.sub(r'\?\?\?','',text)
            tokens = re.split(r'[.\s,<>\-]+', text)
            for tok in tokens:
                tok = tok.strip().replace("'","")
                if not tok or '?' in tok: continue
                if re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                    all_data.append({"word":tok,"section":section,
                                     "folio":stem,"locus":locus})
    return all_data

def extract_bio_paragraphs():
    """Extract bio-section text organized by paragraph."""
    folio_dir = Path("folios")
    paragraphs = []
    for num in range(75, 85):
        for side in ['r','v']:
            fname = folio_dir / f"f{num}{side}.txt"
            if not fname.exists(): continue
            text = fname.read_text(encoding="utf-8")
            lines = text.splitlines()
            current_para = []
            current_locus_start = None
            for line in lines:
                line_s = line.strip()
                if line_s.startswith("#") or not line_s: continue
                lm = re.match(r'<([^>]+)>\s*(.*)', line_s)
                if not lm: continue
                locus = lm.group(1)
                raw = lm.group(2)
                has_para_start = "<%>" in raw
                has_para_end = "<$>" in raw
                # Clean
                raw = re.sub(r'<![\d:]+>','',raw)
                raw = re.sub(r'<![^>]*>','',raw)
                raw = re.sub(r'<%>|<\$>|<->|<\.>',' ',raw)
                raw = re.sub(r'<[^>]*>','',raw)
                raw = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', raw)
                raw = re.sub(r'\{([^}]+)\}', r'\1', raw)
                raw = re.sub(r'@\d+;?','',raw)
                raw = re.sub(r'\?\?\?','',raw)
                tokens = re.split(r'[.\s,]+', raw)
                clean = [clean_token(t) for t in tokens
                         if clean_token(t) and len(clean_token(t)) >= 2]
                if has_para_start and current_para:
                    paragraphs.append({
                        "folio": f"f{num}{side}",
                        "locus_start": current_locus_start,
                        "words": list(current_para)
                    })
                    current_para = []
                    current_locus_start = locus
                if not current_locus_start:
                    current_locus_start = locus
                current_para.extend(clean)
                if has_para_end and current_para:
                    paragraphs.append({
                        "folio": f"f{num}{side}",
                        "locus_start": current_locus_start,
                        "words": list(current_para)
                    })
                    current_para = []
                    current_locus_start = None
            if current_para:
                paragraphs.append({
                    "folio": f"f{num}{side}",
                    "locus_start": current_locus_start,
                    "words": list(current_para)
                })
    return paragraphs


# ══════════════════════════════════════════════════════════════════
# MATCHING ENGINE
# ══════════════════════════════════════════════════════════════════

def consonant_skeleton(w):
    return re.sub(r'[aeiou]+','',w.lower())

def match_root(root, glossary, label):
    """Try to match a Voynichese root against a glossary. Returns list of matches."""
    hits = []
    for ref_word, meaning in glossary.items():
        # Exact
        if root == ref_word:
            hits.append((ref_word, meaning, "EXACT", 1.0))
            continue
        # e→a vowel shift (our established rule)
        shifted = root.replace('e','a')
        if shifted == ref_word:
            hits.append((ref_word, meaning, "E→A", 0.9))
            continue
        # Consonant skeleton
        rs = consonant_skeleton(root)
        cs = consonant_skeleton(ref_word)
        if rs and cs and len(rs) >= 2 and rs == cs:
            # Weight by length similarity
            len_ratio = min(len(root), len(ref_word)) / max(len(root), len(ref_word))
            hits.append((ref_word, meaning, "SKEL", 0.5 * len_ratio))
            continue
        # Prefix match (root starts with the reference or vice versa, ≥3 chars)
        if len(root) >= 3 and len(ref_word) >= 3:
            if root.startswith(ref_word[:3]) or ref_word.startswith(root[:3]):
                hits.append((ref_word, meaning, "PREFIX", 0.3))
    return hits


# ══════════════════════════════════════════════════════════════════
# 21a: WATER-SIGN AND FIRE-SIGN VOCABULARY CRACK
# ══════════════════════════════════════════════════════════════════

def run_element_vocab_crack(zodiac):
    print("\n" + "="*76)
    print("PHASE 21a: ELEMENT-EXCLUSIVE VOCABULARY CRACK")
    print("="*76)

    # Build sign → residual roots from ring text
    template_roots = {"a","air","al","am","ar","ch","che","cho","d","e","eo",
                      "eod","eol","eos","es","h","he","ho","l","o","ol","or"}

    sign_residual = {}
    for sign, data in zodiac.items():
        roots = [full_decompose(w)["root"] for w in data["ring_words"]]
        sign_residual[sign] = Counter(r for r in roots if r not in template_roots)

    # Group by element
    element_groups = defaultdict(list)
    for sign in zodiac:
        bs = base_sign(sign)
        elem = SIGN_PROPERTIES.get(bs,{}).get("element","")
        element_groups[elem].append(sign)

    for elem in ["Water","Fire","Earth","Air"]:
        signs = element_groups[elem]
        print(f"\n{'─'*76}")
        print(f"  {elem.upper()} SIGNS: {', '.join(signs)}")
        print(f"{'─'*76}")

        # Collect all residual roots for this element
        elem_roots = Counter()
        for s in signs:
            for r, c in sign_residual.get(s,{}).items():
                elem_roots[r] += c

        # Find element-exclusive roots
        other_signs = [s for s in zodiac if s not in signs]
        other_roots = set()
        for s in other_signs:
            other_roots |= set(sign_residual.get(s,{}).keys())

        exclusive = {r: c for r, c in elem_roots.items() if r not in other_roots}
        shared = {r: c for r, c in elem_roots.items() if r in other_roots}

        print(f"  Total residual roots: {len(elem_roots)}, "
              f"Exclusive: {len(exclusive)}, Shared with other elements: {len(shared)}")

        # Match exclusive roots against BOTH glossaries
        print(f"\n  --- Matching {len(exclusive)} exclusive roots against expanded glossaries ---")

        all_matches = []
        for root in sorted(exclusive.keys()):
            for gl, label in [(COPTIC_EXPANDED,"Coptic"), (ARABIC_EXPANDED,"Arabic")]:
                hits = match_root(root, gl, label)
                for ref, meaning, mtype, score in hits:
                    # Which specific signs contain this root?
                    in_signs = [s for s in signs if root in sign_residual.get(s,{})]
                    all_matches.append((root, exclusive[root], ref, meaning,
                                        f"{mtype}-{label}", score, in_signs))

        # Sort by score descending
        all_matches.sort(key=lambda x: (-x[5], x[0]))

        if all_matches:
            # SEMANTIC VALIDATION: check if meaning fits element
            elem_semantic = {
                "Water": {"water","sea","ocean","river","canal","rain","wave","dew",
                           "pour","flow","cold","wet","cool","refresh","moisten",
                           "moon","night","darkness","fish","crab","scorpion",
                           "belly","womb","foot","genitals","chest","blood",
                           "dead","die"},
                "Fire":  {"fire","hot","dry","burn","kindle","sun","light",
                           "lion","ram","head","heart","thigh","back",
                           "king","gold","red","alive"},
                "Earth": {"earth","cold","dry","stone","bone","neck","throat",
                           "intestines","black","saturn","venus","bull",
                           "knee"},
                "Air":   {"air","hot","wet","wind","arms","lungs","kidneys",
                           "mercury","venus","scales","twins","white",
                           "knowledge"},
            }

            semantic_pool = elem_semantic.get(elem, set())
            print(f"\n    {'Root':12s} {'×':>3s} {'Ref':12s} {'Meaning':20s} {'Match':15s} "
                  f"{'Scr':>4s} {'Semantic?':>9s} Signs")
            for root, cnt, ref, meaning, mtype, score, in_s in all_matches[:30]:
                # Check semantic fit
                sem_hit = any(w in meaning.lower() for w in semantic_pool)
                sem_str = "✓ YES" if sem_hit else "  ---"
                print(f"    {root:12s} {cnt:3d} {ref:12s} {meaning:20s} {mtype:15s} "
                      f"{score:4.2f} {sem_str:>9s} {','.join(in_s)}")
        else:
            print(f"    No matches found")

        # Also check which confirmed vocab roots appear in this element
        print(f"\n  --- Confirmed vocab in {elem} ring residual ---")
        for root, cnt in sorted(exclusive.items(), key=lambda x:-x[1]):
            if root in CONFIRMED_VOCAB:
                meaning, lang, conf = CONFIRMED_VOCAB[root]
                print(f"    {root:12s} x{cnt:3d} = {meaning} ({lang}, {conf:.0%})")


# ══════════════════════════════════════════════════════════════════
# 21b: VERB CONJUGATION PARADIGM
# ══════════════════════════════════════════════════════════════════

def run_verb_paradigm(all_words):
    print("\n" + "="*76)
    print("PHASE 21b: VERB CONJUGATION PARADIGM — -ey/-edy/-ody/-ol")
    print("="*76)

    # Get all s-prefix words with their decompositions
    s_words = []
    for w in all_words:
        d = w.get("decomp") or full_decompose(w["word"])
        w["decomp"] = d
        if d["prefix"] in ("s","so"):
            s_words.append(w)

    verb_suffixes = ["ey","edy","ody","ol","eedy","dy","y",""]
    # Focus on the top 5 most common s-roots
    root_counts = Counter(w["decomp"]["root"] for w in s_words)
    top_roots = [r for r, _ in root_counts.most_common(8)]

    print(f"\n  --- Conjugation table: top s-roots × suffix ---")
    header = f"  {'s-ROOT':14s}"
    for sfx in verb_suffixes:
        header += f" {'-'+sfx if sfx else '∅':>7s}"
    header += "   TOTAL"
    print(header)
    print("  " + "─"*90)

    for root in top_roots:
        row = f"  s-{root:11s}"
        total = 0
        for sfx in verb_suffixes:
            cnt = sum(1 for w in s_words
                      if w["decomp"]["root"]==root and w["decomp"]["suffix"]==sfx)
            total += cnt
            row += f" {cnt:7d}"
        row += f"   {total:5d}"
        print(row)

    # Test 1: Do different suffixes appear in different POSITIONS?
    print(f"\n  --- Position analysis: does suffix correlate with sentence position? ---")
    locus_seqs = defaultdict(list)
    for w in all_words:
        locus_seqs[w["locus"]].append(w)

    sfx_position = defaultdict(lambda: Counter())
    for locus, words in locus_seqs.items():
        n = len(words)
        if n < 3: continue
        for i, w in enumerate(words):
            d = w.get("decomp") or full_decompose(w["word"])
            if d["prefix"] not in ("s","so"): continue
            sfx = d["suffix"]
            if sfx not in ("ey","edy","ody","ol","dy","y"): continue
            pos = "initial" if i <= 1 else ("final" if i >= n-2 else "medial")
            sfx_position[sfx][pos] += 1

    print(f"  {'Suffix':8s} {'initial':>9s} {'medial':>9s} {'final':>9s}  init%   fin%")
    for sfx in ["ey","edy","ody","ol","dy","y"]:
        pc = sfx_position[sfx]
        total = sum(pc.values())
        if total < 5: continue
        init_pct = 100*pc["initial"]/total
        fin_pct = 100*pc["final"]/total
        print(f"  -{sfx:7s} {pc['initial']:9d} {pc['medial']:9d} {pc['final']:9d}"
              f"  {init_pct:5.1f}% {fin_pct:5.1f}%")

    # Test 2: Section distribution per verb suffix
    print(f"\n  --- Section distribution: do verb suffixes vary by manuscript section? ---")
    sfx_section = defaultdict(lambda: Counter())
    for w in s_words:
        sfx = w["decomp"]["suffix"]
        if sfx in ("ey","edy","ody","ol"):
            sfx_section[sfx][w["section"]] += 1

    sections = ["herbal-A","zodiac","bio","cosmo","pharma","herbal-B","text"]
    print(f"  {'Suffix':8s}", end="")
    for sec in sections:
        print(f" {sec:>9s}", end="")
    print()
    for sfx in ["ey","edy","ody","ol"]:
        total_sfx = sum(sfx_section[sfx].values())
        print(f"  -{sfx:7s}", end="")
        for sec in sections:
            pct = 100*sfx_section[sfx].get(sec,0)/total_sfx if total_sfx else 0
            print(f" {pct:8.1f}%", end="")
        print(f"  (n={total_sfx})")

    # Test 3: What word FOLLOWS s-*-ey vs s-*-edy vs s-*-ol?
    print(f"\n  --- Right context: what follows each verb form? ---")
    for target_sfx in ["ey","edy","ody","ol"]:
        right_roots = Counter()
        right_pfx = Counter()
        right_det = Counter()
        for locus, words in locus_seqs.items():
            for i, w in enumerate(words):
                d = w.get("decomp") or full_decompose(w["word"])
                if d["prefix"] in ("s","so") and d["suffix"] == target_sfx:
                    if i < len(words)-1:
                        nd = words[i+1].get("decomp") or full_decompose(words[i+1]["word"])
                        right_roots[nd["root"]] += 1
                        right_pfx[nd["prefix"] or "∅"] += 1
                        right_det[nd["determinative"] or "∅"] += 1
        total = sum(right_roots.values())
        if total < 10: continue
        top_r = ', '.join(f'{r}({c})' for r,c in right_roots.most_common(5))
        top_d = ', '.join(f'{d}({c})' for d,c in right_det.most_common(4))
        # Is qokeedy following?
        qok_cnt = sum(c for r,c in right_roots.items() if 'e' == r)
        print(f"    After s-*-{target_sfx:4s} (n={total}): roots=[{top_r}]  det=[{top_d}]")

    # Test 4: Do same roots take DIFFERENT suffixes in different sections?
    print(f"\n  --- Root × suffix × section: does 'sh-ey' differ from 'sh-edy'? ---")
    for root in ["h","he","ho"]:
        for sfx in ["ey","edy","ol"]:
            sec_c = Counter()
            for w in s_words:
                if w["decomp"]["root"]==root and w["decomp"]["suffix"]==sfx:
                    sec_c[w["section"]] += 1
            if sum(sec_c.values()) < 5: continue
            top = ', '.join(f'{s}({c})' for s,c in sec_c.most_common(4))
            print(f"    s-{root}-{sfx:4s}: n={sum(sec_c.values()):4d}  {top}")


# ══════════════════════════════════════════════════════════════════
# 21c: BIO-SECTION PARAGRAPH TRANSLATION
# ══════════════════════════════════════════════════════════════════

def run_bio_translation(all_words):
    print("\n" + "="*76)
    print("PHASE 21c: BIO-SECTION PARAGRAPH TRANSLATION ATTEMPT")
    print("="*76)

    paragraphs = extract_bio_paragraphs()
    print(f"\n  Extracted {len(paragraphs)} bio-section paragraphs")

    # Score paragraphs by translation potential:
    # - Contains qokeedy (2× enriched here)
    # - Contains confirmed vocab roots
    # - Contains s-prefix verbs
    # - Reasonable length (15-40 words)
    scored = []
    for p in paragraphs:
        words = p["words"]
        n = len(words)
        if n < 12 or n > 50: continue
        decomps = [full_decompose(w) for w in words]

        # Count features
        qok_count = sum(1 for w in words
                        if w.startswith("qok") and (w.endswith("y") or w.endswith("dy")))
        conf_count = sum(1 for d in decomps if d["root"] in CONFIRMED_VOCAB)
        s_count = sum(1 for d in decomps if d["prefix"] in ("s","so"))
        p_opener = 1 if decomps and decomps[0]["determinative"]=="p" else 0
        det_count = sum(1 for d in decomps if d["determinative"])

        # Score
        score = (conf_count * 3 + qok_count * 2 + s_count * 2 +
                 p_opener * 3 + det_count * 1)
        # Normalize by length
        density = score / n

        scored.append((density, score, p, words, decomps,
                        {"qok":qok_count, "conf":conf_count,
                         "s_verb":s_count, "p_open":p_opener,
                         "det":det_count, "n":n}))

    scored.sort(key=lambda x: -x[0])

    # Translate top 3 paragraphs
    for rank, (density, score, para, words, decomps, stats) in enumerate(scored[:3]):
        print(f"\n{'━'*76}")
        print(f"  PARAGRAPH #{rank+1}: {para['folio']} from {para['locus_start']}")
        print(f"  Translation density: {density:.2f} (score={score}, n={stats['n']})")
        print(f"  Features: {stats}")
        print(f"{'━'*76}")

        # Show raw words
        print(f"\n  Raw: {' '.join(words)}")

        # Decompose and translate word by word
        print(f"\n  {'Word':22s} {'Pfx':4s} {'Det':4s} {'Root':10s} {'Sfx':6s} Translation")
        print(f"  {'─'*80}")

        translated = 0
        partial = 0
        gloss_parts = []

        for w, d in zip(words, decomps):
            root = d["root"]
            pfx = d["prefix"]
            det = d["determinative"]
            sfx = d["suffix"]

            # Build translation
            trans_parts = []
            root_meaning = ""

            # Prefix
            if pfx in ("s","so"):
                trans_parts.append("VERB:")
            elif pfx == "qo":
                trans_parts.append("DEMO:")
            elif pfx == "o":
                trans_parts.append("ART:")
            elif pfx == "d":
                trans_parts.append("of-")
            elif pfx == "y":
                trans_parts.append("CONJ:")

            # Determinative
            if det == "t":
                trans_parts.append("[celestial]")
            elif det == "k":
                trans_parts.append("[substance]")
            elif det == "f":
                trans_parts.append("[plant]")
            elif det == "p":
                trans_parts.append("[DISC]")

            # Root
            if root in CONFIRMED_VOCAB:
                meaning, lang, conf = CONFIRMED_VOCAB[root]
                root_meaning = meaning
                trans_parts.append(f"'{meaning}'")
            else:
                # Try expanded matching
                best_match = None
                best_score = 0
                for gl, label in [(COPTIC_EXPANDED,"C"), (ARABIC_EXPANDED,"A")]:
                    hits = match_root(root, gl, label)
                    for ref, meaning, mtype, sc in hits:
                        if sc > best_score:
                            best_score = sc
                            best_match = (ref, meaning, mtype, label)
                if best_match and best_score >= 0.5:
                    ref, meaning, mtype, label = best_match
                    root_meaning = f"~{meaning}"
                    trans_parts.append(f"~'{meaning}'")
                else:
                    root_meaning = f"[{root}]"
                    trans_parts.append(f"[{root}]")

            # Suffix
            if sfx in ("ey","edy","eedy"):
                trans_parts.append("-CONJ")
            elif sfx == "ody":
                trans_parts.append("-CAUS")
            elif sfx == "ol":
                trans_parts.append("-NOM")
            elif sfx in ("aiin","ain"):
                trans_parts.append("-PL?")
            elif sfx in ("iin","in"):
                trans_parts.append("-PL")
            elif sfx in ("ar","or"):
                trans_parts.append("-AGT")
            elif sfx in ("al",):
                trans_parts.append("-LOC")
            elif sfx in ("y","dy"):
                trans_parts.append("-ADJ")

            translation = " ".join(trans_parts)

            # Is this a qokeedy form?
            is_qok = w.startswith("qok") and (w.endswith("y") or w.endswith("dy"))
            if is_qok:
                translation = "REL.PRON 'that-which'"

            # Scoring
            if root in CONFIRMED_VOCAB:
                translated += 1
            elif best_match and best_score >= 0.5:
                partial += 1

            print(f"  {w:22s} {pfx:4s} {det:4s} {root:10s} {sfx:6s} {translation}")
            gloss_parts.append(translation)

        # Summary gloss
        total = len(words)
        trans_pct = 100 * translated / total
        partial_pct = 100 * (translated + partial) / total
        print(f"\n  ── Gloss attempt ──")
        print(f"  {' | '.join(gloss_parts)}")
        print(f"\n  Translated: {translated}/{total} ({trans_pct:.0f}%) confirmed, "
              f"{translated+partial}/{total} ({partial_pct:.0f}%) with tentative")

    return scored[:3]


# ══════════════════════════════════════════════════════════════════
# 21d: FIXED-CROSS TEST — Does eosd in Scorpio reference Leo?
# ══════════════════════════════════════════════════════════════════

def run_fixed_cross_test(zodiac):
    print("\n" + "="*76)
    print("PHASE 21d: FIXED-CROSS REFERENCE TEST")
    print("="*76)
    print("""
  The Fixed Cross in astrology: Taurus ↔ Scorpio ↔ Leo ↔ Aquarius.
  Phase 20 found 'eosd' (≈ asad = lion) in SCORPIO, not Leo.
  Hypothesis: signs reference their Fixed-cross counterpart.

  Testing: Do other signs contain roots that name OTHER signs?
""")

    template_roots = {"a","air","al","am","ar","ch","che","cho","d","e","eo",
                      "eod","eol","eos","es","h","he","ho","l","o","ol","or"}

    sign_residual = {}
    for sign, data in zodiac.items():
        roots = [full_decompose(w)["root"] for w in data["ring_words"]]
        sign_residual[sign] = Counter(r for r in roots if r not in template_roots)

    # Sign-name roots (Arabic names via e→a shift)
    sign_roots = {
        "hamal": "Aries(ram)",     "thawr": "Taurus(bull)",
        "asad": "Leo(lion)",       "aqrab": "Scorpio(scorpion)",
        "hut": "Pisces(fish)",     "saratan": "Cancer(crab)",
        "mizan": "Libra(scales)",  "qaws": "Sagittarius(bow)",
        "jady": "Capricorn(goat)", "dalw": "Aquarius(bucket)",
        "sunbula": "Virgo(ear)",   "jawza": "Gemini(twins)",
    }

    print(f"  {'Root found':15s} {'In Sign':18s} {'Matches':20s} {'Relationship':30s}")
    print(f"  {'─'*85}")

    for sign, resid in sorted(sign_residual.items()):
        bs = base_sign(sign)
        for root in resid:
            shifted = root.replace('e','a')
            rs = consonant_skeleton(root)
            for sr, sname in sign_roots.items():
                ss = consonant_skeleton(sr)
                if shifted == sr or (rs and ss and len(rs)>=2 and rs == ss):
                    ref_sign = sname.split("(")[0]
                    # What's the relationship?
                    rel = ""
                    if bs == ref_sign:
                        rel = "SELF-REFERENCE"
                    else:
                        p1 = SIGN_PROPERTIES.get(bs,{})
                        p2 = SIGN_PROPERTIES.get(ref_sign,{})
                        if p1.get("modality") == p2.get("modality"):
                            rel = f"SAME MODALITY ({p1.get('modality','')})"
                        if p1.get("element") == p2.get("element"):
                            rel += f" SAME ELEMENT ({p1.get('element','')})"
                        if p1.get("ruler") == p2.get("ruler"):
                            rel += f" SAME RULER ({p1.get('ruler','')})"
                        opp_pairs = [("Aries","Libra"),("Taurus","Scorpio"),
                                     ("Gemini","Sagittarius"),("Cancer","Capricorn"),
                                     ("Leo","Aquarius"),("Virgo","Pisces")]
                        for a,b in opp_pairs:
                            if (bs==a and ref_sign==b) or (bs==b and ref_sign==a):
                                rel += " OPPOSITION"
                    if not rel: rel = "other"
                    print(f"  {root:15s} {sign:18s} ~{sr:8s}={sname:15s} {rel}")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("="*76)
    print("PHASE 21: HIGHEST-LEVERAGE ATTACKS")
    print("="*76)

    print("\nLoading data...")
    zodiac = extract_zodiac_data()
    all_words = extract_all_words()
    for w in all_words:
        w["decomp"] = full_decompose(w["word"])
    print(f"  {len(zodiac)} zodiac signs, {len(all_words)} corpus tokens")

    run_element_vocab_crack(zodiac)
    run_verb_paradigm(all_words)
    top_paras = run_bio_translation(all_words)
    run_fixed_cross_test(zodiac)

    # Save results
    results = {
        "phase": 21,
        "analyses": ["element_vocab_crack","verb_paradigm",
                      "bio_translation","fixed_cross_test"],
    }
    Path("results").mkdir(exist_ok=True)
    Path("results/phase21_results.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\n  Results saved to results/phase21_results.json")
