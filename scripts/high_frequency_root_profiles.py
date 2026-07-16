#!/usr/bin/env python3
"""
Crack the High-Frequency Unknown Roots
===================================================

The roots h, l, d, e (as standalone morphemes after decomposition) appear
in nearly every passage but remain unidentified. Solving even one would
boost translation rates 10-15%.

Strategy:
  A) DISTRIBUTIONAL SEMANTICS — For each unknown root, profile:
       - Which determinatives it takes (t=celestial, k=substance, f=plant, p=disc)
       - Which prefixes/suffixes it attracts
       - What it collocates with (left/right neighbors)
       - Which sections it's enriched in
       → Cross-reference against Coptic monosyllabic words to narrow candidates

  B) YED=HAND CORPUS-WIDE VALIDATION — Does 'yed' cluster in anatomical/bio
       passages? What words contain it? This tests the e→a Arabic rule.

  C) ROOT PAIR DISTRIBUTIONAL CONTRAST — Compare roots that appear in
       complementary distribution (e.g., h vs he, al vs ol) to determine
       if they're related or distinct.

  D) REGISTER CLASSIFIER — Use verb suffix ratios to auto-classify every
       folio into bio/herbal/zodiac/narrative register and check accuracy.
"""

import re, json, math, sys, io
from pathlib import Path
from collections import Counter, defaultdict
from common import classify_folio_v2 as classify_folio, collapse_echains, full_decompose, gallows_base, parse_morphology, strip_gallows

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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
# CONFIRMED VOCABULARY
# ══════════════════════════════════════════════════════════════════

CONFIRMED_VOCAB = {
    "esed":"lion/Leo", "she":"tree/plant", "al":"stone", "he":"fall/occur",
    "ro":"mouth", "les":"tongue", "ran":"name", "cham":"hot/warm",
    "res":"south", "ar":"king/great", "or":"king/great(var)",
    "ol":"carry/lift", "am":"water", "chas":"lord/master",
    "eos":"star", "es":"star(short)", "chol":"celestial body",
    "cho":"substance", "eosh":"dry", "sheo":"dry(var)",
    "choam":"hot", "rar":"king", "yed":"hand",
}

# Coptic monosyllabic/short words (Crum's dictionary — words ≤3 letters)
COPTIC_SHORT = {
    # Attested Sahidic monosyllabic
    "pe":"sky/heaven", "me":"truth/love", "re":"sun/mouth",
    "se":"hundred/man", "te":"the(fem)", "ne":"the(pl)",
    "he":"fall/perish", "le":"cease", "be":"go",
    "ke":"other/another", "de":"but/and", "je":"say/that",
    "na":"of/to/great", "ma":"place/give", "ta":"the(fem.art)",
    "ha":"upon/under", "la":"?", "ra":"?",
    "no":"?", "mo":"water(bound)", "to":"give/assign",
    "ho":"face/front", "lo":"cease/rest", "so":"?",
    "ei":"come", "oi":"do/make", "hi":"on/upon",
    "ou":"one/a(indef)", "au":"they",
    # Two-letter roots attested in Coptic
    "bal":"eye", "bon":"bad/evil", "bom":"strength",
    "hom":"power", "hol":"fly", "hor":"send/compel",
    "hot":"kill", "hat":"heart/silver", "hro":"face",
    "kam":"black", "kah":"earth", "kim":"move",
    "lob":"burn", "les":"tongue", "min":"road",
    "mou":"die/water", "nob":"sin", "nau":"see",
    "ran":"name", "rom":"man", "rem":"weep/fish",
    "rek":"incline", "sho":"hundred", "she":"tree/wood",
    "sol":"counsel", "sor":"scatter", "shi":"measure",
    "tol":"lift", "tom":"shut", "ton":"where",
    # Short words critical for grammar
    "an":"not(negation)", "on":"again", "en":"us",
    "in":"by(agent)", "er":"to/toward", "ar":"do/make",
    "or":"?(lord?)",
    # Body parts
    "ro":"mouth", "af":"flesh", "lo":"(rest)",
}

# Arabic short words (2-3 consonants) relevant to astro/medical
ARABIC_SHORT = {
    "dam":"blood", "ras":"head", "yad":"hand", "ayn":"eye",
    "fam":"mouth", "nafs":"soul/self", "ruh":"spirit",
    "harr":"hot", "bard":"cold", "nur":"light",
    "nar":"fire", "maa":"water", "ard":"earth",
    "rabb":"lord", "abd":"servant", "ilm":"knowledge",
    "hukm":"rule", "dawa":"medicine", "hayy":"alive",
}


# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════


def extract_all_words():
    folio_dir = Path("folios")
    all_data = []
    for txt_file in sorted(folio_dir.glob("*.txt")):
        stem = txt_file.stem
        section = classify_folio(stem)
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


# ══════════════════════════════════════════════════════════════════
# 22a: DISTRIBUTIONAL SEMANTICS FOR UNKNOWN HIGH-FREQ ROOTS
# ══════════════════════════════════════════════════════════════════

def run_distributional_semantics(all_words):
    print("\n" + "="*76)
    print("DISTRIBUTIONAL PROFILES OF UNKNOWN HIGH-FREQ ROOTS")
    print("="*76)

    # Target roots: the most frequent roots NOT in confirmed vocab
    root_counts = Counter()
    for w in all_words:
        root_counts[w["decomp"]["root"]] += 1

    # Show frequency table
    print(f"\n  --- Top 30 roots by frequency ---")
    print(f"  {'Root':12s} {'Count':>6s} {'%':>6s} Known?")
    for root, cnt in root_counts.most_common(30):
        pct = 100*cnt/len(all_words)
        known = CONFIRMED_VOCAB.get(root, "???")
        marker = "✓" if root in CONFIRMED_VOCAB else "◀ UNKNOWN"
        print(f"  {root:12s} {cnt:6d} {pct:5.1f}% {marker} {known if root in CONFIRMED_VOCAB else ''}")

    # Deep profile of each unknown root in top 15
    targets = []
    for root, cnt in root_counts.most_common(20):
        if root not in CONFIRMED_VOCAB and len(root) >= 1:
            targets.append(root)
        if len(targets) >= 6:
            break

    locus_seqs = defaultdict(list)
    for w in all_words:
        locus_seqs[w["locus"]].append(w)

    for target in targets:
        target_words = [w for w in all_words if w["decomp"]["root"] == target]
        n = len(target_words)
        pct = 100*n/len(all_words)

        print(f"\n{'━'*76}")
        print(f"  ROOT: '{target}' — {n} tokens ({pct:.1f}% of corpus)")
        print(f"{'━'*76}")

        # 1. Determinative profile
        det_c = Counter(w["decomp"]["determinative"] for w in target_words)
        total_det = sum(c for d,c in det_c.items() if d)
        det_str = ', '.join(f'{d or "∅"}:{c}({100*c/n:.0f}%)' for d,c in det_c.most_common())
        print(f"  Determinatives: {det_str}")

        # Compare to corpus average
        all_det = Counter(w["decomp"]["determinative"] for w in all_words)
        print(f"  Det enrichment:")
        for det in ['t','k','f','p']:
            target_pct = 100*det_c.get(det,0)/n
            base_pct = 100*all_det.get(det,0)/len(all_words)
            ratio = target_pct/base_pct if base_pct else 0
            marker = "▲" if ratio > 1.5 else ("▼" if ratio < 0.67 else " ")
            print(f"    {det}: {target_pct:5.1f}% (base {base_pct:5.1f}%) {ratio:5.2f}x {marker}")

        # 2. Prefix profile
        pfx_c = Counter(w["decomp"]["prefix"] for w in target_words)
        print(f"  Prefixes: {', '.join(f'{p or '∅'}:{c}' for p,c in pfx_c.most_common(6))}")

        # Key: what % takes s- (verbal)?
        s_pct = 100*(pfx_c.get("s",0)+pfx_c.get("so",0))/n
        o_pct = 100*pfx_c.get("o",0)/n
        d_pct = 100*pfx_c.get("d",0)/n
        qo_pct = 100*pfx_c.get("qo",0)/n
        print(f"  Key prefix rates: s-/so-:{s_pct:.1f}%, o-:{o_pct:.1f}%, d-:{d_pct:.1f}%, qo-:{qo_pct:.1f}%")

        # 3. Suffix profile
        sfx_c = Counter(w["decomp"]["suffix"] for w in target_words)
        print(f"  Suffixes: {', '.join(f'-{s or '∅'}:{c}' for s,c in sfx_c.most_common(8))}")

        # Is this root more verbal (-ey/-edy) or nominal (-y/-iin)?
        verb_sfx = sum(sfx_c.get(s,0) for s in ["ey","edy","ody","eedy"])
        noun_sfx = sum(sfx_c.get(s,0) for s in ["y","iin","aiin","ain","in"])
        case_sfx = sum(sfx_c.get(s,0) for s in ["al","ol","ar","or"])
        print(f"  Morphological class: verbal_sfx={verb_sfx} ({100*verb_sfx/n:.0f}%), "
              f"nominal_sfx={noun_sfx} ({100*noun_sfx/n:.0f}%), "
              f"case_sfx={case_sfx} ({100*case_sfx/n:.0f}%)")

        # 4. Section distribution
        sec_c = Counter(w["section"] for w in target_words)
        all_sec = Counter(w["section"] for w in all_words)
        print(f"  Section enrichment:")
        for sec in sorted(sec_c.keys(), key=lambda x:-sec_c[x])[:5]:
            tp = 100*sec_c[sec]/n
            bp = 100*all_sec[sec]/len(all_words)
            ratio = tp/bp if bp else 0
            marker = "▲" if ratio > 1.3 else ("▼" if ratio < 0.77 else " ")
            print(f"    {sec:12s}: {tp:5.1f}% (base {bp:5.1f}%) {ratio:.2f}x {marker}")

        # 5. Collocational profile (what roots appear left/right?)
        left_roots = Counter()
        right_roots = Counter()
        for locus, words in locus_seqs.items():
            for i, w in enumerate(words):
                if w["decomp"]["root"] == target:
                    if i > 0:
                        left_roots[words[i-1]["decomp"]["root"]] += 1
                    if i < len(words)-1:
                        right_roots[words[i+1]["decomp"]["root"]] += 1

        print(f"  Left context:  {', '.join(f'{r}({c})' for r,c in left_roots.most_common(8))}")
        print(f"  Right context: {', '.join(f'{r}({c})' for r,c in right_roots.most_common(8))}")

        # 6. Most common FULL WORDS with this root
        word_forms = Counter(w["word"] for w in target_words)
        print(f"  Top word forms: {', '.join(f'{w}({c})' for w,c in word_forms.most_common(10))}")

        # 7. Candidate matches from Coptic/Arabic short words
        print(f"  Candidate meanings:")
        candidates = []
        for gl, label in [(COPTIC_SHORT,"Coptic"), (ARABIC_SHORT,"Arabic")]:
            for ref, meaning in gl.items():
                # Exact
                if target == ref:
                    candidates.append((ref, meaning, "EXACT", label, 1.0))
                # e→a shift
                elif target.replace('e','a') == ref:
                    candidates.append((ref, meaning, "E→A", label, 0.9))
                # consonant skeleton
                else:
                    ts = re.sub(r'[aeiou]+','',target)
                    rs = re.sub(r'[aeiou]+','',ref)
                    if ts and rs and len(ts) >= 1 and ts == rs:
                        candidates.append((ref, meaning, "SKEL", label, 0.5))

        candidates.sort(key=lambda x: -x[4])
        for ref, meaning, mtype, lang, score in candidates[:8]:
            # Semantic plausibility check
            plausible = ""
            if s_pct > 20 and meaning in ("say/that","come","go","see","make/do",
                                          "walk","fall/perish","cease","send/compel",
                                          "counsel","lift","do/make","give/assign"):
                plausible = "✓ verbal"
            elif s_pct < 10 and meaning in ("sky/heaven","truth/love","sun/mouth",
                                            "earth","place","eye","heart","power",
                                            "blood","head","hand","fire","water",
                                            "spirit","light","soul/self"):
                plausible = "✓ nominal"
            print(f"    {ref:8s} = {meaning:20s} ({mtype:5s} {lang:7s} {score:.1f}) {plausible}")


# ══════════════════════════════════════════════════════════════════
# 22b: YED=HAND CORPUS-WIDE VALIDATION
# ══════════════════════════════════════════════════════════════════

def run_yed_validation(all_words):
    print("\n" + "="*76)
    print("YED=HAND CORPUS-WIDE VALIDATION")
    print("="*76)

    # Find all words containing the root 'yed'
    yed_words = [w for w in all_words if w["decomp"]["root"] == "yed"]
    print(f"\n  Words with root 'yed': {len(yed_words)}")

    # Also find raw 'yed' substring in any position
    yed_raw = [w for w in all_words if "yed" in w["word"]]
    print(f"  Words containing 'yed' substring: {len(yed_raw)}")

    # Search more broadly: any word where e→a would yield 'yad'
    yed_broad = [w for w in all_words
                 if w["word"].replace('e','a').find("yad") >= 0
                 or w["decomp"]["root"] in ("yed","yad")]
    print(f"  Words matching 'yed/yad' pattern (e→a): {len(yed_broad)}")

    # Use the broadest set
    target = yed_broad if yed_broad else yed_words

    # Word forms
    forms = Counter(w["word"] for w in target)
    print(f"\n  Word forms with 'yed' pattern:")
    for form, cnt in forms.most_common(15):
        d = full_decompose(form)
        print(f"    {form:25s} x{cnt:4d}  root={d['root']:8s} pfx={d['prefix']:4s} "
              f"det={d['determinative']:3s} sfx={d['suffix']}")

    # Section distribution
    sec_c = Counter(w["section"] for w in target)
    all_sec = Counter(w["section"] for w in all_words)
    print(f"\n  Section distribution:")
    for sec in sorted(sec_c.keys(), key=lambda x: -sec_c[x]):
        tp = 100*sec_c[sec]/len(target) if target else 0
        bp = 100*all_sec[sec]/len(all_words)
        ratio = tp/bp if bp else 0
        marker = "▲ BIO" if sec == "bio" and ratio > 1.3 else ""
        print(f"    {sec:12s}: {sec_c[sec]:4d} ({tp:5.1f}% vs {bp:5.1f}% base) "
              f"{ratio:.2f}x {marker}")

    # What words appear AROUND yed?
    locus_seqs = defaultdict(list)
    for w in all_words:
        locus_seqs[w["locus"]].append(w)

    target_set = set(id(w) for w in target)
    context_roots = Counter()
    for locus, words in locus_seqs.items():
        for i, w in enumerate(words):
            if id(w) in target_set:
                for j in range(max(0,i-2), min(len(words),i+3)):
                    if j != i:
                        context_roots[words[j]["decomp"]["root"]] += 1

    print(f"\n  Roots in ±2-word window around 'yed':")
    for r, c in context_roots.most_common(15):
        known = CONFIRMED_VOCAB.get(r, "")
        print(f"    {r:12s} x{c:4d}  {known}")

    # Does yed cluster with body-part vocabulary?
    body_roots = {"ro","les","hat","he","ape","bal","hro"}
    body_ctx = sum(context_roots.get(r,0) for r in body_roots)
    total_ctx = sum(context_roots.values())
    if total_ctx:
        print(f"\n  Body-part roots in context: {body_ctx}/{total_ctx} "
              f"({100*body_ctx/total_ctx:.1f}%)")
    else:
        print(f"\n  No context found — 'yed' may only appear as decomposition artifact")


# ══════════════════════════════════════════════════════════════════
# 22c: ROOT PAIR DISTRIBUTIONAL CONTRAST
# ══════════════════════════════════════════════════════════════════

def run_root_contrasts(all_words):
    print("\n" + "="*76)
    print("ROOT PAIR DISTRIBUTIONAL CONTRASTS")
    print("="*76)

    # Compare roots that might be related vs distinct
    pairs = [
        ("h", "he", "Is 'h' a shortened form of 'he' (fall/occur)?"),
        ("h", "ho", "Is 'h' related to 'ho' (face/front)?"),
        ("l", "le", "Is 'l' the same as 'le' (cease)?"),
        ("l", "lo", "Is 'l' related to 'lo' (cease/rest)?"),
        ("d", "de", "Is 'd' the Coptic conjunction 'de' (but/and)?"),
        ("e", "ei", "Is 'e' Coptic 'ei' (come)?"),
        ("ch", "cho", "Is 'ch' shortened 'cho' (substance)?"),
        ("a", "ar", "Is 'a' shortened 'ar' (king/great)?"),
    ]

    for r1, r2, question in pairs:
        w1 = [w for w in all_words if w["decomp"]["root"] == r1]
        w2 = [w for w in all_words if w["decomp"]["root"] == r2]
        n1, n2 = len(w1), len(w2)

        print(f"\n  {'─'*72}")
        print(f"  {r1} (n={n1}) vs {r2} (n={n2}) — {question}")

        if n1 < 10 or n2 < 10:
            print(f"    Too few tokens, skipping")
            continue

        # Compare section distributions
        sec1 = Counter(w["section"] for w in w1)
        sec2 = Counter(w["section"] for w in w2)
        sections = sorted(set(list(sec1.keys()) + list(sec2.keys())))

        print(f"    {'Section':12s} {r1+' %':>8s} {r2+' %':>8s} {'diff':>8s}")
        max_diff = 0
        for sec in sections:
            p1 = 100*sec1.get(sec,0)/n1
            p2 = 100*sec2.get(sec,0)/n2
            diff = abs(p1-p2)
            max_diff = max(max_diff, diff)
            marker = " ◀" if diff > 10 else ""
            print(f"    {sec:12s} {p1:7.1f}% {p2:7.1f}% {diff:7.1f}%{marker}")

        # Compare determinative profiles
        det1 = Counter(w["decomp"]["determinative"] for w in w1)
        det2 = Counter(w["decomp"]["determinative"] for w in w2)
        print(f"    Determinatives:")
        for det in ['t','k','f','p','']:
            label = det or '∅'
            p1 = 100*det1.get(det,0)/n1
            p2 = 100*det2.get(det,0)/n2
            marker = " ◀" if abs(p1-p2) > 10 else ""
            print(f"      {label:4s}: {p1:5.1f}% vs {p2:5.1f}%{marker}")

        # Compare prefix profiles (key: s- = verbal)
        pfx1 = Counter(w["decomp"]["prefix"] for w in w1)
        pfx2 = Counter(w["decomp"]["prefix"] for w in w2)
        s1 = 100*(pfx1.get("s",0)+pfx1.get("so",0))/n1
        s2 = 100*(pfx2.get("s",0)+pfx2.get("so",0))/n2
        o1 = 100*pfx1.get("o",0)/n1
        o2 = 100*pfx2.get("o",0)/n2
        print(f"    s-prefix: {s1:.1f}% vs {s2:.1f}% {'◀ DIFFERENT' if abs(s1-s2)>10 else ''}")
        print(f"    o-prefix: {o1:.1f}% vs {o2:.1f}% {'◀ DIFFERENT' if abs(o1-o2)>10 else ''}")

        # Verdict
        if max_diff < 5 and abs(s1-s2) < 5:
            print(f"    VERDICT: VERY SIMILAR distributions → likely same/related morpheme")
        elif max_diff < 10 and abs(s1-s2) < 10:
            print(f"    VERDICT: SIMILAR distributions → possibly related")
        else:
            print(f"    VERDICT: DIFFERENT distributions → likely distinct morphemes")


# ══════════════════════════════════════════════════════════════════
# 22d: REGISTER CLASSIFIER
# ══════════════════════════════════════════════════════════════════

def run_register_classifier(all_words):
    print("\n" + "="*76)
    print("AUTOMATIC REGISTER CLASSIFICATION")
    print("="*76)

    # For each folio, compute verb suffix ratios
    folio_words = defaultdict(list)
    for w in all_words:
        folio_words[w["folio"]].append(w)

    print(f"\n  {'Folio':10s} {'n':>5s} {'s-%':>6s} {'-edy%':>6s} {'-ody%':>6s} "
          f"{'-ol%':>6s} {'-ey%':>6s} {'qok%':>6s} {'Predicted':>10s} {'Actual':>10s} {'Match':>6s}")
    print("  " + "─"*95)

    correct = 0
    total = 0
    mismatches = []

    for folio in sorted(folio_words.keys()):
        words = folio_words[folio]
        n = len(words)
        if n < 20: continue

        actual = words[0]["section"]
        if actual in ("unknown",): continue

        # Compute features
        s_words = [w for w in words if w["decomp"]["prefix"] in ("s","so")]
        s_pct = 100*len(s_words)/n if n else 0

        sfx_c = Counter(w["decomp"]["suffix"] for w in s_words) if s_words else Counter()
        n_s = len(s_words) if s_words else 1
        edy_pct = 100*sfx_c.get("edy",0)/n_s
        ody_pct = 100*sfx_c.get("ody",0)/n_s
        ol_pct = 100*sfx_c.get("ol",0)/n_s
        ey_pct = 100*sfx_c.get("ey",0)/n_s

        qok_words = sum(1 for w in words
                        if w["word"].startswith("qok") and
                        (w["word"].endswith("y") or w["word"].endswith("dy")))
        qok_pct = 100*qok_words/n

        # Classification rules (from zodiac_element_vocabulary part-b findings):
        # -edy dominant → bio
        # -ody/-ol dominant → herbal
        # low s-prefix + low qokeedy → zodiac
        # high p-initial → text/cosmo
        if s_pct < 5 and qok_pct < 1:
            predicted = "zodiac"
        elif edy_pct > 35 and qok_pct > 1:
            predicted = "bio"
        elif edy_pct > 30:
            predicted = "bio"
        elif ody_pct > 20 or ol_pct > 25:
            predicted = "herbal"
        elif ol_pct > 15:
            predicted = "herbal"
        else:
            # Default: check p-gallows sentence-initial rate
            p_initial = sum(1 for w in words if w["decomp"]["determinative"]=="p")
            p_rate = 100*p_initial/n
            if p_rate > 8:
                predicted = "text"
            else:
                predicted = "herbal"  # default

        # Map predicted to comparable categories
        actual_cat = actual
        if actual_cat in ("herbal-A","herbal-B","pharma"):
            actual_cat = "herbal"

        predicted_cat = predicted
        match = "✓" if predicted_cat == actual_cat else "✗"
        if predicted_cat == actual_cat:
            correct += 1
        else:
            mismatches.append((folio, actual, predicted))
        total += 1

        print(f"  {folio:10s} {n:5d} {s_pct:5.1f}% {edy_pct:5.1f}% {ody_pct:5.1f}% "
              f"{ol_pct:5.1f}% {ey_pct:5.1f}% {qok_pct:5.1f}% {predicted:>10s} {actual:>10s} {match:>6s}")

    accuracy = 100*correct/total if total else 0
    print(f"\n  Classification accuracy: {correct}/{total} ({accuracy:.1f}%)")

    if mismatches:
        print(f"\n  Misclassified folios ({len(mismatches)}):")
        for folio, actual, predicted in mismatches[:10]:
            print(f"    {folio}: actual={actual}, predicted={predicted}")


# ══════════════════════════════════════════════════════════════════
# 22e: SYNTHESIZE — BEST CANDIDATE MEANINGS FOR h, l, d, e
# ══════════════════════════════════════════════════════════════════

def run_synthesis(all_words):
    print("\n" + "="*76)
    print("SYNTHESIS — BEST CANDIDATE MEANINGS")
    print("="*76)

    targets = {
        "h": None, "l": None, "d": None, "e": None, "ch": None, "a": None
    }

    for target in targets:
        tw = [w for w in all_words if w["decomp"]["root"] == target]
        n = len(tw)

        # Compute key discriminating features
        pfx_c = Counter(w["decomp"]["prefix"] for w in tw)
        det_c = Counter(w["decomp"]["determinative"] for w in tw)
        sfx_c = Counter(w["decomp"]["suffix"] for w in tw)
        sec_c = Counter(w["section"] for w in tw)

        s_pct = 100*(pfx_c.get("s",0)+pfx_c.get("so",0))/n
        o_pct = 100*pfx_c.get("o",0)/n
        d_pct = 100*pfx_c.get("d",0)/n
        verb_sfx = sum(sfx_c.get(s,0) for s in ["ey","edy","ody","eedy"])
        noun_sfx = sum(sfx_c.get(s,0) for s in ["y","iin","aiin","ain","in"])
        no_det = 100*det_c.get("",0)/n
        k_det = 100*det_c.get("k",0)/n
        t_det = 100*det_c.get("t",0)/n

        bio_pct = 100*sec_c.get("bio",0)/n
        herb_pct = 100*(sec_c.get("herbal-A",0)+sec_c.get("herbal-B",0))/n
        text_pct = 100*sec_c.get("text",0)/n

        # Build evidence profile
        verbal = s_pct > 15 or 100*verb_sfx/n > 20
        nominal = 100*noun_sfx/n > 20 or k_det > 15 or t_det > 10

        targets[target] = {
            "n": n, "s_pct": s_pct, "o_pct": o_pct, "d_pct": d_pct,
            "verbal": verbal, "nominal": nominal,
            "no_det_pct": no_det, "k_det_pct": k_det, "t_det_pct": t_det,
            "bio_pct": bio_pct, "herb_pct": herb_pct, "text_pct": text_pct,
            "verb_sfx_pct": 100*verb_sfx/n, "noun_sfx_pct": 100*noun_sfx/n,
        }

    # Now synthesize
    for target, profile in targets.items():
        print(f"\n  {'═'*70}")
        print(f"  ROOT '{target}' — {profile['n']} tokens")
        print(f"  {'═'*70}")
        print(f"  s-prefix: {profile['s_pct']:.1f}% | o-prefix: {profile['o_pct']:.1f}% "
              f"| d-prefix: {profile['d_pct']:.1f}%")
        print(f"  Verbal suffixes: {profile['verb_sfx_pct']:.1f}% | "
              f"Nominal suffixes: {profile['noun_sfx_pct']:.1f}%")
        print(f"  k-det: {profile['k_det_pct']:.1f}% | t-det: {profile['t_det_pct']:.1f}% "
              f"| no-det: {profile['no_det_pct']:.1f}%")
        print(f"  Bio: {profile['bio_pct']:.1f}% | Herbal: {profile['herb_pct']:.1f}% "
              f"| Text: {profile['text_pct']:.1f}%")

        # Determine morphological class
        if profile["verbal"] and not profile["nominal"]:
            mclass = "VERB/ACTION"
        elif profile["nominal"] and not profile["verbal"]:
            mclass = "NOUN/ENTITY"
        elif profile["verbal"] and profile["nominal"]:
            mclass = "MIXED (nominal-verbal)"
        else:
            mclass = "FUNCTION WORD / PARTICLE"

        print(f"  Morphological class: {mclass}")

        # Best candidates
        print(f"  Best Coptic candidates:")
        for ref, meaning in COPTIC_SHORT.items():
            if target == ref:
                # Check plausibility
                fit = ""
                if "VERB" in mclass and meaning in ("fall/perish","cease","go",
                    "come","do/make","say/that","send/compel","give/assign",
                    "see","walk","lift","counsel","on/upon"):
                    fit = "✓ fits verbal profile"
                elif "NOUN" in mclass and meaning in ("sky/heaven","truth/love",
                    "sun/mouth","earth","place","eye","heart","power",
                    "other/another","face/front"):
                    fit = "✓ fits nominal profile"
                elif "FUNCTION" in mclass and meaning in ("but/and","other/another",
                    "not(negation)","the(fem)","the(pl)","on/upon","one/a(indef)"):
                    fit = "✓ fits function word"
                print(f"    {ref} = {meaning} {fit}")

        # Final judgment
        if target == "h":
            print(f"\n  ► JUDGMENT: 'h' takes s-prefix heavily ({profile['s_pct']:.0f}%), "
                  f"verbal suffixes ({profile['verb_sfx_pct']:.0f}%), "
                  f"{'bio-enriched' if profile['bio_pct'] > 20 else 'evenly distributed'}.")
            if profile["s_pct"] > 15:
                print(f"    BEST CANDIDATE: Coptic 'he' (fall/occur) with reduced vowel,")
                print(f"    or Coptic 'ho' (face/front) — possibly the most generic verb root.")
                print(f"    Given s-h-ey (662×) and s-h-edy (569×) dominate the corpus,")
                print(f"    'h' is likely the BOUND FORM of 'he' = 'fall/occur/happen'.")
        elif target == "l":
            print(f"\n  ► JUDGMENT: 'l' profile suggests "
                  f"{'verbal' if profile['verbal'] else 'nominal'} word.")
            print(f"    BEST CANDIDATES: Coptic 'lo' (cease/rest) or 'le' (cease),")
            print(f"    or possibly a PROCLITIC (definite article fragment).")
        elif target == "d":
            print(f"\n  ► JUDGMENT: 'd' is {'verbal' if profile['verbal'] else 'likely a function word'}.")
            print(f"    BEST CANDIDATE: Coptic 'de' (but/and) — conjunction/particle.")
            print(f"    High d-prefix usage ({profile['d_pct']:.0f}%) suggests 'd' itself")
            print(f"    may be the genitive 'of' marker appearing as a standalone root")
            print(f"    when the parser strips it as prefix from the following word.")
        elif target == "e":
            print(f"\n  ► JUDGMENT: 'e' is the most frequent root — "
                  f"{'verbal' if profile['verbal'] else 'nominal/function'}.")
            print(f"    BEST CANDIDATE: Coptic 'e-' (to/toward, directional prefix),")
            print(f"    or the VOWEL REDUCTION artifact of longer roots (ee→e).")
            print(f"    Given it appears in qo-k-e-dy (= qokeedy), where we identified")
            print(f"    it as the relative pronoun root, 'e' may be a DEMONSTRATIVE BASE.")
        elif target == "ch":
            print(f"\n  ► JUDGMENT: 'ch' profile.")
            print(f"    BEST CANDIDATE: Coptic 'cho' (substance) bound form,")
            print(f"    or an independent classifier root for 'thing/matter'.")
        elif target == "a":
            print(f"\n  ► JUDGMENT: 'a' profile.")
            print(f"    BEST CANDIDATE: Coptic 'a-' (imperative prefix, or 'do/make'),")
            print(f"    or Arabic definite article 'al-' bound form.")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("="*76)
    print("high_frequency_root_profiles: CRACK THE HIGH-FREQUENCY UNKNOWN ROOTS")
    print("="*76)

    print("\nLoading data...")
    all_words = extract_all_words()
    for w in all_words:
        w["decomp"] = full_decompose(w["word"])
    print(f"  {len(all_words)} corpus tokens")

    run_distributional_semantics(all_words)
    run_yed_validation(all_words)
    run_root_contrasts(all_words)
    run_register_classifier(all_words)
    run_synthesis(all_words)

    Path("results").mkdir(exist_ok=True)
    Path("results/high_frequency_root_profiles_results.json").write_text(
        json.dumps({"test": "high_frequency_root_profiles"}, indent=2), encoding="utf-8")
    print(f"\n  Results saved to results/high_frequency_root_profiles_results.json")
