#!/usr/bin/env python3
"""
Phase 20: Template Subtraction, Function Word Identification,
           Verbal System Mapping, and Element/Planet Correlation
=================================================================

Strategy:
  1. TEMPLATE SUBTRACTION — Remove the 22 roots shared across ≥6 signs.
     What remains per sign should be sign-specific content words.
     Cross-reference these against known astrological properties (element,
     ruling planet, body part, quality, gemstone) for each sign.

  2. qokeedy INVESTIGATION — Is it a single lexeme? Test: does it appear
     in fixed positions? Does it have collocational preferences?

  3. s-ROOT-ol VERBAL SYSTEM — Map all words with s- prefix systematically.
     Test if s- marks verbs/causatives.

  4. p-GALLOWS SENTENCE OPENER — Analyze what p-gallows words ARE and
     what follows them.

  5. ELEMENT CORRELATION — Group signs by element (Fire, Water, Air, Earth).
     Test whether signs sharing an element also share exclusive vocabulary.
"""

import re, json, math
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from common import collapse_echains, full_decompose, gallows_base, parse_morphology, strip_gallows

# ══════════════════════════════════════════════════════════════════
# MORPHOLOGICAL PIPELINE (from Phase 19)
# ══════════════════════════════════════════════════════════════════

SIMPLE_GALLOWS = ["t","k","f","p"]
BENCH_GALLOWS  = ["cth","ckh","cph","cfh"]
COMPOUND_GCH   = ["tch","kch","pch","fch"]
COMPOUND_GSH   = ["tsh","ksh","psh","fsh"]
ALL_GALLOWS    = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

PREFIXES = ['qo','q','so','do','o','d','s','y']
SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol',
            'edy','ody','eedy','dy','sy','ey','y']






def decompose_preserve_echains(word):
    stripped, gals = strip_gallows(word)
    pfx, root, sfx = parse_morphology(stripped)
    bases = [gallows_base(g) for g in gals]
    return dict(original=word, stripped=stripped,
                prefix=pfx or "", root=root, suffix=sfx or "",
                gallows=bases, determinative=bases[0] if bases else "")

# ══════════════════════════════════════════════════════════════════
# ASTROLOGICAL REFERENCE DATA
# ══════════════════════════════════════════════════════════════════

ZODIAC_MAP = {
    "f70v1": "Aries-dark", "f71r": "Aries-light",
    "f71v": "Taurus-light", "f72r1": "Taurus-dark",
    "f72r2": "Gemini", "f72r3": "Cancer",
    "f72v3": "Leo", "f72v2": "Virgo", "f72v1": "Libra",
    "f73r": "Scorpio", "f73v": "Sagittarius", "f70v2": "Pisces",
}

# Canonical sign → base name (merge light/dark variants)
def base_sign(s):
    return s.replace("-dark","").replace("-light","")

SIGN_PROPERTIES = {
    "Aries":       {"element":"Fire",  "modality":"Cardinal", "ruler":"Mars",    "exalt":"Sun",     "body":"head",       "quality":"hot-dry",   "gem":"diamond"},
    "Taurus":      {"element":"Earth", "modality":"Fixed",    "ruler":"Venus",   "exalt":"Moon",    "body":"neck/throat","quality":"cold-dry",  "gem":"emerald"},
    "Gemini":      {"element":"Air",   "modality":"Mutable",  "ruler":"Mercury", "exalt":"",        "body":"arms/lungs", "quality":"hot-wet",   "gem":"agate"},
    "Cancer":      {"element":"Water", "modality":"Cardinal", "ruler":"Moon",    "exalt":"Jupiter", "body":"chest/stom", "quality":"cold-wet",  "gem":"pearl"},
    "Leo":         {"element":"Fire",  "modality":"Fixed",    "ruler":"Sun",     "exalt":"",        "body":"heart/back", "quality":"hot-dry",   "gem":"ruby"},
    "Virgo":       {"element":"Earth", "modality":"Mutable",  "ruler":"Mercury", "exalt":"Mercury", "body":"intestines", "quality":"cold-dry",  "gem":"sapphire"},
    "Libra":       {"element":"Air",   "modality":"Cardinal", "ruler":"Venus",   "exalt":"Saturn",  "body":"kidneys",    "quality":"hot-wet",   "gem":"opal"},
    "Scorpio":     {"element":"Water", "modality":"Fixed",    "ruler":"Mars",    "exalt":"",        "body":"genitals",   "quality":"cold-wet",  "gem":"topaz"},
    "Sagittarius": {"element":"Fire",  "modality":"Mutable",  "ruler":"Jupiter", "exalt":"",        "body":"thighs",     "quality":"hot-dry",   "gem":"turquoise"},
    "Pisces":      {"element":"Water", "modality":"Mutable",  "ruler":"Jupiter", "exalt":"Venus",   "body":"feet",       "quality":"cold-wet",  "gem":"amethyst"},
}

DECAN_RULERS = {
    "Aries":       ["Mars","Sun","Venus"],
    "Taurus":      ["Mercury","Moon","Saturn"],
    "Gemini":      ["Jupiter","Mars","Sun"],
    "Cancer":      ["Venus","Mercury","Moon"],
    "Leo":         ["Saturn","Jupiter","Mars"],
    "Virgo":       ["Sun","Venus","Mercury"],
    "Libra":       ["Moon","Saturn","Jupiter"],
    "Scorpio":     ["Mars","Sun","Venus"],
    "Sagittarius": ["Mercury","Moon","Saturn"],
    "Pisces":      ["Jupiter","Mars","Sun"],  # standard Chaldean
}

# Coptic terms for astrological concepts (attested or plausible)
COPTIC_ASTRO_GLOSSARY = {
    # Elements
    "sate": "fire",  "moou": "water", "teu": "wind/air", "kah": "earth",
    # Qualities
    "cham": "hot", "kebe": "cold", "shuoe": "dry", "nesh": "wet",
    # Planets (Coptic attested)
    "re": "sun",  "ioh": "moon",  "souro": "saturn", "moui": "jupiter",
    "ertosi": "mars",  "ourampe": "venus", "sobou": "mercury",
    # Body parts
    "ape": "head",  "mekh": "neck",  "shedj": "arm",  "esnau": "shoulder",
    "hat": "heart", "hete": "belly", "tbe": "finger", "ouoerdte": "foot",
    "kole": "knee", "meros": "thigh",
    # General astro
    "siou": "star", "noub": "gold", "kake": "darkness", "ouoein": "light",
    "choeis": "lord", "rro": "king",
}

# Arabic terms that might appear (given esed=asad anchor)
ARABIC_ASTRO = {
    "shams": "sun",  "qamar": "moon",  "zuhal": "saturn",
    "mushtari": "jupiter", "mirrikh": "mars",
    "zuhara": "venus", "utarid": "mercury",
    "nar": "fire",  "maa": "water",  "turab": "earth", "hawa": "air",
    "ras": "head",  "qalb": "heart",  "sadr": "chest",
    "asad": "lion", "thawr": "bull",  "hamal": "ram",
    "jady": "goat", "hut": "fish",   "aqrab": "scorpion",
    "qaws": "bow/archer", "dalw": "bucket/aquarius",
}


# ══════════════════════════════════════════════════════════════════
# DATA EXTRACTION
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
                zodiac[sign] = {"ring_lines":[],"nymph_labels":[],"ring_words":[],"nymph_words":[]}
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
                    zodiac[sign]["ring_lines"].append(clean)
                    zodiac[sign]["ring_words"].extend(clean)
            elif "@Lz" in line_s or "&Lz" in line_s:
                m = re.match(r'<([^>]+)>\s*(.*)', line_s)
                if m:
                    raw = m.group(2)
                    raw = re.sub(r'<![\d:]+>','',raw)
                    raw = re.sub(r'<![^>]*>','',raw)
                    raw = re.sub(r'<[^>]*>','',raw)
                    raw = re.sub(r'\?\?\?','',raw)
                    tokens = re.split(r'[.\s,]+', raw)
                    parts = [clean_token(t) for t in tokens
                             if clean_token(t) and len(clean_token(t)) >= 2]
                    if parts:
                        zodiac[sign]["nymph_labels"].append(parts)
                        zodiac[sign]["nymph_words"].extend(parts)
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
        prev_locus = None
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
        # track locus boundaries for sentence segmentation in 19c
    return all_data


# ══════════════════════════════════════════════════════════════════
# 1. TEMPLATE SUBTRACTION
# ══════════════════════════════════════════════════════════════════

def run_template_subtraction(zodiac):
    print("\n" + "="*76)
    print("PHASE 20.1: TEMPLATE SUBTRACTION — SIGN-SPECIFIC VOCABULARY")
    print("="*76)

    # Get shared roots (template) from ring text
    sign_root_sets = {}
    sign_root_counts = {}
    for sign, data in zodiac.items():
        roots = [full_decompose(w)["root"] for w in data["ring_words"]]
        sign_root_sets[sign] = set(roots)
        sign_root_counts[sign] = Counter(roots)

    root_in_signs = defaultdict(set)
    for sign, rs in sign_root_sets.items():
        for r in rs:
            root_in_signs[r].add(sign)

    n_signs = len(zodiac)
    # Template = roots in ≥ 6 signs
    template_roots = {r for r, s in root_in_signs.items() if len(s) >= 6}
    print(f"\n  Template vocabulary (≥6 signs): {len(template_roots)} roots")
    print(f"  Template roots: {', '.join(sorted(template_roots))}")

    # Subtract template from each sign's ring text
    print(f"\n  --- Residual (sign-specific) roots after template subtraction ---")
    sign_residual = {}
    for sign in sorted(zodiac.keys()):
        rc = sign_root_counts[sign]
        residual = {r: c for r, c in rc.items() if r not in template_roots}
        sign_residual[sign] = residual
        bs = base_sign(sign)
        props = SIGN_PROPERTIES.get(bs, {})
        elem = props.get("element","?")
        ruler = props.get("ruler","?")
        body = props.get("body","?")
        total_ring = sum(rc.values())
        total_resid = sum(residual.values())
        print(f"\n    {sign:18s} [{elem:5s} | ruler={ruler:8s} | body={body}]")
        print(f"      Ring words: {total_ring}, Residual: {total_resid} ({100*total_resid/total_ring:.0f}%)")
        if residual:
            top = sorted(residual.items(), key=lambda x:-x[1])[:15]
            print(f"      Sign-specific: {', '.join(f'{r}({c})' for r,c in top)}")

    # Group signs by element and test for shared exclusive vocabulary
    print(f"\n  --- Element grouping: do signs share vocabulary by element? ---")
    element_groups = defaultdict(list)
    for sign in zodiac:
        bs = base_sign(sign)
        elem = SIGN_PROPERTIES.get(bs,{}).get("element","?")
        element_groups[elem].append(sign)

    for elem, signs in sorted(element_groups.items()):
        print(f"\n    {elem} signs: {', '.join(signs)}")
        if len(signs) < 2: continue
        # Find roots exclusive to this element group
        elem_roots = set()
        for s in signs:
            elem_roots |= set(sign_residual.get(s,{}).keys())
        # Check which are ONLY in this element's signs
        exclusive = set()
        for r in elem_roots:
            in_elem = any(r in sign_residual.get(s,{}) for s in signs)
            other_signs = [s for s in zodiac if s not in signs]
            in_other = any(r in sign_residual.get(s,{}) for s in other_signs)
            if in_elem and not in_other:
                exclusive.add(r)
        if exclusive:
            print(f"      Element-exclusive roots: {', '.join(sorted(exclusive))}")
        else:
            print(f"      No element-exclusive residual roots")

    # Group by ruler planet
    print(f"\n  --- Ruler grouping: do signs with same ruler share vocabulary? ---")
    ruler_groups = defaultdict(list)
    for sign in zodiac:
        bs = base_sign(sign)
        ruler = SIGN_PROPERTIES.get(bs,{}).get("ruler","?")
        ruler_groups[ruler].append(sign)

    for ruler, signs in sorted(ruler_groups.items()):
        if len(signs) < 2: continue
        # Common residual roots across signs with this ruler
        sets = [set(sign_residual.get(s,{}).keys()) for s in signs]
        shared = sets[0]
        for s in sets[1:]:
            shared &= s
        if shared:
            print(f"    {ruler:10s} rules {', '.join(signs)}: shared residual = {', '.join(sorted(shared))}")
        else:
            print(f"    {ruler:10s} rules {', '.join(signs)}: no shared residual")

    # Match residual roots against Coptic/Arabic astro glossary
    print(f"\n  --- Residual root matching against Coptic/Arabic glossary ---")
    all_residual = set()
    for resid in sign_residual.values():
        all_residual |= set(resid.keys())

    def consonant_skeleton(w):
        return re.sub(r'[aeiou]+','',w.lower())

    matches_found = []
    for r in sorted(all_residual):
        # Check Coptic
        for cw, meaning in COPTIC_ASTRO_GLOSSARY.items():
            if r == cw:
                matches_found.append((r, cw, meaning, "EXACT-coptic"))
            elif r == cw.replace('e','a'):
                matches_found.append((r, cw, meaning, "VOWEL-coptic"))
            else:
                rs = consonant_skeleton(r)
                cs = consonant_skeleton(cw)
                if rs and cs and len(rs) >= 2 and len(cs) >= 2 and rs == cs:
                    matches_found.append((r, cw, meaning, "SKEL-coptic"))
        # Check Arabic
        for aw, meaning in ARABIC_ASTRO.items():
            if r == aw:
                matches_found.append((r, aw, meaning, "EXACT-arabic"))
            else:
                ra = r.replace('e','a')
                if ra == aw:
                    matches_found.append((r, aw, meaning, "VOWEL-arabic"))
                else:
                    rs = consonant_skeleton(r)
                    as_ = consonant_skeleton(aw)
                    if rs and as_ and len(rs) >= 2 and len(as_) >= 2 and rs == as_:
                        matches_found.append((r, aw, meaning, "SKEL-arabic"))

    if matches_found:
        print(f"\n    Matches ({len(matches_found)}):")
        for r, ref, meaning, mtype in sorted(matches_found, key=lambda x:x[0]):
            # Which signs contain this root?
            in_signs = [s for s in zodiac if r in sign_residual.get(s,{})]
            print(f"      {r:12s} ~ {ref:12s} = {meaning:15s} ({mtype:15s}) in {','.join(in_signs)}")
    else:
        print(f"    No glossary matches found in residual roots")

    return sign_residual, template_roots


# ══════════════════════════════════════════════════════════════════
# 2. qokeedy LEXEME INVESTIGATION
# ══════════════════════════════════════════════════════════════════

def run_qokeedy_analysis(all_words):
    print("\n" + "="*76)
    print("PHASE 20.2: IS qokeedy A SINGLE LEXEME?")
    print("="*76)

    # Find all forms matching qok*dy or qok*y pattern
    candidates = ["qokeedy","qokedy","qokeeedy","qokeey","qokedy",
                   "qokeody","qokeeey"]
    # Actually find all words starting with qok and ending with y/dy
    qok_words = []
    for w in all_words:
        word = w["word"]
        if word.startswith("qok") and (word.endswith("dy") or word.endswith("y")):
            qok_words.append(w)

    word_forms = Counter(w["word"] for w in qok_words)
    print(f"\n  qok*y/dy word forms: {len(word_forms)} unique, {len(qok_words)} tokens")
    for form, cnt in word_forms.most_common(15):
        d = full_decompose(form)
        print(f"    {form:25s} x{cnt:4d}  root={d['root']:10s} "
              f"pfx={d['prefix']} det={d['determinative']} sfx={d['suffix']}")

    # Positional analysis: where do these appear in sentences?
    print(f"\n  --- Position in text lines ---")
    # Build per-locus sequences
    locus_seqs = defaultdict(list)
    for w in all_words:
        locus_seqs[w["locus"]].append(w["word"])

    positions = Counter()  # "first", "last", "medial"
    for locus, words in locus_seqs.items():
        if len(words) < 3: continue
        for i, w in enumerate(words):
            if w.startswith("qok") and (w.endswith("dy") or w.endswith("y")):
                if i == 0:
                    positions["first"] += 1
                elif i == len(words)-1:
                    positions["last"] += 1
                else:
                    positions["medial"] += 1

    total_pos = sum(positions.values())
    if total_pos:
        print(f"    first: {positions['first']} ({100*positions['first']/total_pos:.1f}%)")
        print(f"    medial: {positions['medial']} ({100*positions['medial']/total_pos:.1f}%)")
        print(f"    last: {positions['last']} ({100*positions['last']/total_pos:.1f}%)")

    # What precedes/follows qokeedy?
    print(f"\n  --- Collocational neighbors ---")
    left = Counter()
    right = Counter()
    for locus, words in locus_seqs.items():
        for i, w in enumerate(words):
            if w.startswith("qok") and (w.endswith("dy") or w.endswith("y")):
                if i > 0:
                    ld = full_decompose(words[i-1])
                    left[ld["root"]] += 1
                if i < len(words)-1:
                    rd = full_decompose(words[i+1])
                    right[rd["root"]] += 1

    print(f"    Left (what precedes qok*y): {', '.join(f'{r}({c})' for r,c in left.most_common(10))}")
    print(f"    Right (what follows qok*y): {', '.join(f'{r}({c})' for r,c in right.most_common(10))}")

    # Section distribution
    print(f"\n  --- Section distribution ---")
    sec_dist = Counter(w["section"] for w in qok_words)
    all_sec = Counter(w["section"] for w in all_words)
    for sec in sorted(sec_dist.keys(), key=lambda x:-sec_dist[x]):
        pct = 100*sec_dist[sec]/len(qok_words)
        base = 100*all_sec[sec]/len(all_words)
        print(f"    {sec:12s}: {sec_dist[sec]:5d} ({pct:5.1f}% vs {base:5.1f}% base)")

    # Does the right context differ from random words?
    # Check if qokeedy is followed by specific determinative types
    print(f"\n  --- What follows qok*y: determinative profile ---")
    right_det = Counter()
    for locus, words in locus_seqs.items():
        for i, w in enumerate(words):
            if w.startswith("qok") and (w.endswith("dy") or w.endswith("y")):
                if i < len(words)-1:
                    rd = full_decompose(words[i+1])
                    right_det[rd["determinative"] or "none"] += 1
    total_rd = sum(right_det.values())
    if total_rd:
        for det in ['t','k','f','p','none']:
            pct = 100*right_det.get(det,0)/total_rd
            print(f"      {det:6s}: {pct:5.1f}%")


# ══════════════════════════════════════════════════════════════════
# 3. s-ROOT-ol VERBAL SYSTEM
# ══════════════════════════════════════════════════════════════════

def run_verbal_system(all_words):
    print("\n" + "="*76)
    print("PHASE 20.3: s- PREFIX VERBAL SYSTEM MAPPING")
    print("="*76)

    # Find all words with s- prefix
    s_words = []
    for w in all_words:
        d = full_decompose(w["word"])
        w["decomp"] = d
        if d["prefix"] == "s" or d["prefix"] == "so":
            s_words.append(w)

    print(f"\n  Total s-/so- prefix words: {len(s_words)}")

    # Root distribution
    s_roots = Counter(w["decomp"]["root"] for w in s_words)
    print(f"\n  Top roots with s- prefix:")
    for root, cnt in s_roots.most_common(20):
        # What suffix do they take?
        suffixes = Counter(w["decomp"]["suffix"] for w in s_words if w["decomp"]["root"]==root)
        top_sfx = ', '.join(f'-{s}({c})' if s else f'∅({c})' for s,c in suffixes.most_common(3))
        print(f"    s-{root:12s} x{cnt:4d}  suffixes: {top_sfx}")

    # Compare: do s- words take different suffixes than non-s words?
    print(f"\n  --- Suffix profile: s- prefix vs all ---")
    s_sfx = Counter(w["decomp"]["suffix"] for w in s_words)
    all_sfx = Counter(w["decomp"]["suffix"] for w in all_words if "decomp" in w)
    print(f"    {'Suffix':8s} {'s-%':>8s} {'all%':>8s} {'ratio':>8s}")
    for sfx in sorted(s_sfx.keys(), key=lambda x:-s_sfx[x])[:10]:
        label = sfx or "∅"
        sp = 100*s_sfx[sfx]/len(s_words)
        ap = 100*all_sfx.get(sfx,0)/len(all_words)
        ratio = sp/ap if ap > 0 else 0
        print(f"    {label:8s} {sp:7.1f}% {ap:7.1f}% {ratio:7.2f}x")

    # s- + determinative interaction
    print(f"\n  --- s- prefix + determinative ---")
    s_det = Counter(w["decomp"]["determinative"] for w in s_words)
    total_s = len(s_words)
    for det in ['t','k','f','p','']:
        label = det or "none"
        pct = 100*s_det.get(det,0)/total_s
        print(f"    s-{label:6s}: {s_det.get(det,0):5d} ({pct:5.1f}%)")

    # The s-ROOT-ol pattern specifically
    s_ol = [w for w in s_words if w["decomp"]["suffix"] == "ol"]
    print(f"\n  --- s-*-ol verbal forms: {len(s_ol)} tokens ---")
    sol_roots = Counter(w["decomp"]["root"] for w in s_ol)
    for root, cnt in sol_roots.most_common(15):
        det = Counter(w["decomp"]["determinative"] for w in s_ol if w["decomp"]["root"]==root)
        det_str = ', '.join(f'{d or "∅"}({c})' for d,c in det.most_common())
        print(f"    s-{root:10s}-ol x{cnt:4d}  det: {det_str}")

    # Section distribution of s- words vs corpus
    print(f"\n  --- s- prefix section distribution ---")
    s_sec = Counter(w["section"] for w in s_words)
    all_sec_c = Counter(w["section"] for w in all_words)
    for sec in sorted(s_sec.keys(), key=lambda x:-s_sec[x]):
        sp = 100*s_sec[sec]/len(s_words)
        ap = 100*all_sec_c[sec]/len(all_words)
        print(f"    {sec:12s}: {sp:5.1f}% (vs {ap:5.1f}% base) {sp/ap:.2f}x")


# ══════════════════════════════════════════════════════════════════
# 4. p-GALLOWS SENTENCE OPENER
# ══════════════════════════════════════════════════════════════════

def run_pgallows_analysis(all_words):
    print("\n" + "="*76)
    print("PHASE 20.4: p-GALLOWS SENTENCE-OPENER ANALYSIS")
    print("="*76)

    # Get all p-gallows words
    p_words = []
    for w in all_words:
        if "decomp" not in w:
            w["decomp"] = full_decompose(w["word"])
        if w["decomp"]["determinative"] == "p":
            p_words.append(w)

    print(f"\n  Total p-gallows words: {len(p_words)}")

    # Root profile
    p_roots = Counter(w["decomp"]["root"] for w in p_words)
    print(f"\n  Top p-gallows roots:")
    for root, cnt in p_roots.most_common(15):
        print(f"    p-{root:12s} x{cnt:4d}")

    # Prefix interaction
    print(f"\n  --- p-gallows prefix distribution ---")
    p_pfx = Counter(w["decomp"]["prefix"] for w in p_words)
    for pfx, cnt in p_pfx.most_common():
        print(f"    {pfx or '∅':8s}-p-*: {cnt:5d} ({100*cnt/len(p_words):.1f}%)")

    # What FOLLOWS p-gallows words?
    print(f"\n  --- What follows p-gallows words? ---")
    locus_seqs = defaultdict(list)
    for w in all_words:
        locus_seqs[w["locus"]].append(w)

    right_det_after_p = Counter()
    right_root_after_p = Counter()
    for locus, words in locus_seqs.items():
        for i, w in enumerate(words):
            if w["decomp"]["determinative"] == "p" and i < len(words)-1:
                nxt = words[i+1]
                right_det_after_p[nxt["decomp"]["determinative"] or "none"] += 1
                right_root_after_p[nxt["decomp"]["root"]] += 1

    total_r = sum(right_det_after_p.values())
    print(f"  Next-word determinative after p-gallows:")
    for det in ['t','k','f','p','none']:
        pct = 100*right_det_after_p.get(det,0)/total_r if total_r else 0
        print(f"    → {det:6s}: {pct:5.1f}%")

    print(f"\n  Next-word root (top 10) after p-gallows:")
    for root, cnt in right_root_after_p.most_common(10):
        print(f"    → {root:12s} x{cnt}")

    # Sentence-initial p-gallows word forms
    print(f"\n  --- Most common sentence-initial p-gallows words ---")
    initial_p = Counter()
    for locus, words in locus_seqs.items():
        if len(words) >= 3 and words[0]["decomp"]["determinative"] == "p":
            initial_p[words[0]["word"]] += 1

    for word, cnt in initial_p.most_common(10):
        d = full_decompose(word)
        print(f"    {word:25s} x{cnt:4d}  root={d['root']:10s} sfx={d['suffix']}")

    # Compare: what section types prefer p-gallows sentence openers?
    print(f"\n  --- Sentence-initial p-gallows by section ---")
    init_p_sec = Counter()
    init_all_sec = Counter()
    for locus, words in locus_seqs.items():
        if len(words) >= 3:
            init_all_sec[words[0].get("section","")] += 1
            if words[0]["decomp"]["determinative"] == "p":
                init_p_sec[words[0]["section"]] += 1

    for sec in sorted(init_p_sec.keys(), key=lambda x:-init_p_sec[x]):
        p_rate = 100*init_p_sec[sec]/init_all_sec[sec] if init_all_sec[sec] else 0
        print(f"    {sec:12s}: {init_p_sec[sec]}/{init_all_sec[sec]} sentences start with p ({p_rate:.1f}%)")


# ══════════════════════════════════════════════════════════════════
# 5. NYMPH LABEL VOCABULARY — DOES IT ENCODE ASTROLOGICAL DATA?
# ══════════════════════════════════════════════════════════════════

def run_nymph_analysis(zodiac):
    print("\n" + "="*76)
    print("PHASE 20.5: NYMPH LABEL VOCABULARY — ASTROLOGICAL CONTENT TEST")
    print("="*76)

    # For each sign, decompose nymph label words and profile
    print(f"\n  --- Nymph label root profiles per sign ---")
    sign_nymph_roots = {}
    for sign in sorted(zodiac.keys()):
        words = zodiac[sign]["nymph_words"]
        roots = [full_decompose(w)["root"] for w in words]
        sign_nymph_roots[sign] = Counter(roots)
        n = len(roots)
        top = sign_nymph_roots[sign].most_common(8)
        bs = base_sign(sign)
        elem = SIGN_PROPERTIES.get(bs,{}).get("element","?")
        print(f"    {sign:18s} [{elem}] {n:3d} words: "
              f"{', '.join(f'{r}({c})' for r,c in top)}")

    # Cross-sign nymph vocabulary overlap
    print(f"\n  --- Which nymph roots are sign-exclusive? ---")
    nymph_root_signs = defaultdict(set)
    nymph_root_total = Counter()
    for sign, rc in sign_nymph_roots.items():
        for r, c in rc.items():
            nymph_root_signs[r].add(sign)
            nymph_root_total[r] += c

    # Universal nymph roots (in ≥8 signs)
    universal = [(r,c) for r, c in nymph_root_total.items()
                 if len(nymph_root_signs[r]) >= 8]
    universal.sort(key=lambda x:-x[1])
    print(f"\n    Universal nymph roots (≥8 signs): {len(universal)}")
    for r, c in universal[:15]:
        print(f"      {r:12s} x{c:4d}  ({len(nymph_root_signs[r])} signs)")

    # Exclusive nymph roots
    excl = [(r, next(iter(nymph_root_signs[r])), nymph_root_total[r])
            for r in nymph_root_signs if len(nymph_root_signs[r]) == 1
            and nymph_root_total[r] >= 2]
    excl.sort(key=lambda x:-x[2])
    print(f"\n    Sign-exclusive nymph roots (freq ≥2): {len(excl)}")
    for r, sign, cnt in excl[:20]:
        bs = base_sign(sign)
        props = SIGN_PROPERTIES.get(bs,{})
        print(f"      {r:12s} x{cnt:4d}  ONLY in {sign:18s} [{props.get('element','?')}/{props.get('ruler','?')}]")

    # Do nymph suffix patterns vary by sign?
    print(f"\n  --- Nymph label suffix profiles ---")
    for sign in sorted(zodiac.keys()):
        words = zodiac[sign]["nymph_words"]
        decomps = [full_decompose(w) for w in words]
        n = len(decomps)
        if n == 0: continue
        sfx_c = Counter(d["suffix"] for d in decomps)
        y_pct = 100*(sfx_c.get("y",0)+sfx_c.get("dy",0)+sfx_c.get("ey",0))/n
        l_pct = 100*(sfx_c.get("al",0)+sfx_c.get("ol",0))/n
        r_pct = 100*(sfx_c.get("ar",0)+sfx_c.get("or",0))/n
        print(f"    {sign:18s} n={n:3d}  -y/-dy/-ey: {y_pct:4.0f}%  -al/-ol: {l_pct:4.0f}%  -ar/-or: {r_pct:4.0f}%")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("="*76)
    print("PHASE 20: TEMPLATE SUBTRACTION + GRAMMAR INVESTIGATIONS")
    print("="*76)

    print("\nLoading data...")
    zodiac = extract_zodiac_data()
    all_words = extract_all_words()
    print(f"  {len(zodiac)} zodiac signs, {len(all_words)} corpus tokens")

    # Ensure decompositions
    for w in all_words:
        if "decomp" not in w:
            w["decomp"] = full_decompose(w["word"])

    sign_residual, template_roots = run_template_subtraction(zodiac)
    run_qokeedy_analysis(all_words)
    run_verbal_system(all_words)
    run_pgallows_analysis(all_words)
    run_nymph_analysis(zodiac)

    # Save
    results = {
        "template_roots": sorted(template_roots),
        "sign_residual_counts": {s: dict(r) for s, r in sign_residual.items()},
    }
    Path("results").mkdir(exist_ok=True)
    Path("results/phase20_results.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\n  Results saved to results/phase20_results.json")
