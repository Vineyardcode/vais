#!/usr/bin/env python3
"""
Phase 26 — Vocabulary Expansion & Cross-Section Validation
============================================================

Phase 25 reached 73.6% corpus-wide coverage with 37 roots. Identified:
  - `cheos` → `chaos` (Greek, prima materia, 64 tokens)
  - `hed` → "pour/descend" (Coptic, 90 tokens, always verbal)
  - `ches` confirmed as variant of `chas` (lord/master)
  - `air` = largest unknown (449 tokens), needs cracking

This phase:
  26a) ADD NEW ROOTS — Integrate cheos, hed, ches→chas, and re-run coverage
  26b) CRACK `air` — Deep distributional analysis against Arabic/Coptic
  26c) CRACK NEXT 5 UNKNOWNS — eo(302), lsh(180), eod(174), od(152), ai(120)
  26d) ZODIAC RE-TRANSLATION — Apply expanded vocabulary to zodiac rings
  26e) HERBAL DEEP DIVE — Profile what makes herbal sections harder and
       identify the herbal-specific unknown roots
"""

import re, json, sys, io, math
from pathlib import Path
from collections import Counter, defaultdict
from common import classify_folio_v2 as classify_folio, collapse_echains, full_decompose, gallows_base, strip_gallows

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
            'eedy','edy','ody','dy','ey','y']




def parse_morphology(w):
    pfx = sfx = ""
    for pf in PREFIXES:
        if w.startswith(pf) and len(w) > len(pf)+1:
            pfx = pf; w = w[len(pf):]; break
    for sf in SUFFIXES:
        if w.endswith(sf) and len(w) > len(sf):
            sfx = sf; w = w[:-len(sf)]; break
    return pfx, w, sfx


# ══════════════════════════════════════════════════════════════════
# EXPANDED VOCABULARY (Phase 26)
# ══════════════════════════════════════════════════════════════════

CONFIRMED_VOCAB = {
    # Phase 1-22 roots
    'esed':'lion','she':'tree/plant','al':'stone','he':'fall/occur',
    'ro':'mouth','les':'tongue','ran':'name','cham':'hot/warm',
    'res':'south','ar':'king/great','or':'king/great',
    'ol':'carry/bear','am':'water','chas':'lord/master',
    'eos':'star','es':'star','chol':'celestial-body','cho':'substance',
    'eosh':'dry','sheo':'dry','choam':'hot','rar':'king',
    'yed':'hand','h':'happen/occur','a':'great-one',
    'e':'this/that','ch':'do/make','l':'remedy/thing','d':'matter/thing',
    # Phase 24
    'ho':'face/aspect',
    # Phase 26 NEW
    'cheos':'chaos/prima-materia',  # Greek loanword, e→a = chaos
    'hed':'pour/descend',           # Coptic, always s-prefixed
    'ches':'lord/master',           # variant of chas (e→a shift)
}

COMPOUND_VOCAB = {
    'lch':  'remedy-making',
    'ed':   'this-matter',
    'che':  'make-this',
    'ched': 'prepare-this',
    'chod': 'substance-matter',
    'alch': 'stone-working/alchemy',
    'sh':   'it-happens',
}

ALL_ROOTS = {}
ALL_ROOTS.update(CONFIRMED_VOCAB)
ALL_ROOTS.update(COMPOUND_VOCAB)

DET_MEANING = {
    'k': 'substance/bodily',
    't': 'celestial/astral',
    'f': 'botanical/plant',
    'p': 'discourse/topic',
}

PREFIX_MEANING = {
    'qo': 'which/that-which',
    'q':  'which',
    'o':  'the',
    'do': 'of-the',
    'd':  'of',
    'so': 'it-[verbs]',
    's':  '[verbal]',
    'y':  '[adjectival]',
}

SUFFIX_MEANING = {
    'aiin': 'rulers(pl)',  'ain': 'rulers(obl)',
    'iin': '(pl)',         'in': '(pl)',
    'ar': '-er/doer',      'or': '-er',
    'al': 'in/at(place)',  'ol': '(nom)',
    'eedy': '(intens.)',   'edy': '(descr.)',
    'ody': '(prescr.)',    'dy': '',
    'ey': '(of)',          'y':'',
}

# Coptic/Arabic reference for cracking unknowns
COPTIC_CANDIDATES = {
    'air': [
        ('Arabic ayr', 'wild donkey / male animal'),
        ('Arabic ayr/ir', 'phallus / virility'),
        ('Coptic eire/ire', 'to do/make'),
        ('Arabic nayr/nar', 'fire (with n-loss)'),
        ('Coptic hire', 'road/way'),
    ],
    'eo': [
        ('Coptic eio', 'to wash / be clean'),
        ('Coptic io', 'donkey'),
        ('Arabic aw', 'or / and'),
    ],
    'lsh': [
        ('l+sh', 'remedy + it-happens = remedy-happening?'),
        ('Coptic lash', 'to multiply / increase'),
        ('Arabic lashsh', 'unclear'),
    ],
    'eod': [
        ('e+od', 'this + ?od? = demonstrative compound'),
        ('Coptic eiot/iot', 'father'),
        ('Arabic udd', 'stick/branch'),
    ],
    'od': [
        ('Coptic oute/ote', 'to pour/press out'),
        ('Arabic ud', 'stick / aloe-wood'),
        ('Arabic oud', 'aloe-wood (oud perfume)'),
    ],
    'ai': [
        ('Coptic ai', 'house (variant of hi/ei)'),
        ('Arabic ay', 'which / what'),
        ('Coptic hai', 'manner/way'),
    ],
}




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
            tokens = re.split(r'[.\s,]+', text)
            for tok in tokens:
                tok = tok.strip().replace("'","")
                if not tok or '?' in tok: continue
                if re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                    all_data.append({"word":tok,"section":section,
                                     "folio":stem,"locus":locus})
    return all_data


def extract_folio_lines(folio_path):
    lines_out = []
    lines = folio_path.read_text(encoding="utf-8").splitlines()
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
        tokens = re.split(r'[.\s,]+', text)
        clean = []
        for tok in tokens:
            tok = tok.strip().replace("'","")
            if not tok or '?' in tok: continue
            if re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                clean.append(tok)
        if clean:
            lines_out.append({"locus": locus, "tokens": clean})
    return lines_out


def smart_gloss(word):
    dec = full_decompose(word)
    root = dec['root']
    pfx = dec['prefix']
    sfx = dec['suffix']
    det = dec['determinative']
    parts = []

    if pfx:
        parts.append(PREFIX_MEANING.get(pfx, pfx))

    if root == 'e' and det:
        det_word = DET_MEANING.get(det, det)
        parts.append(f"this-{det_word}")
    elif root == 'a' and det:
        det_word = DET_MEANING.get(det, det)
        parts.append(f"{det_word}-noble")
    elif root in ALL_ROOTS:
        if det:
            parts.append(f"[{DET_MEANING.get(det, det)}]")
        parts.append(ALL_ROOTS[root])
    else:
        if det:
            parts.append(f"[{DET_MEANING.get(det, det)}]")
        parts.append(f"?{root}?")

    if sfx:
        parts.append(SUFFIX_MEANING.get(sfx, sfx))

    return " ".join(parts)


# ══════════════════════════════════════════════════════════════════
# 26a: COVERAGE WITH NEW ROOTS
# ══════════════════════════════════════════════════════════════════

def run_coverage_update(all_words):
    print("\n" + "="*76)
    print("PHASE 26a: COVERAGE UPDATE WITH NEW ROOTS")
    print("="*76)

    total = len(all_words)
    known = sum(1 for w in all_words if full_decompose(w['word'])['root'] in ALL_ROOTS)
    print(f"\n  Total tokens: {total}")
    print(f"  Known roots:  {known} ({known/total*100:.1f}%)")
    print(f"  Vocabulary:   {len(CONFIRMED_VOCAB)} confirmed + {len(COMPOUND_VOCAB)} compounds = {len(ALL_ROOTS)} total")

    # Per-section coverage
    section_stats = defaultdict(lambda: [0, 0])  # known, total
    for w in all_words:
        dec = full_decompose(w['word'])
        section_stats[w['section']][1] += 1
        if dec['root'] in ALL_ROOTS:
            section_stats[w['section']][0] += 1

    print(f"\n  Per-section coverage:")
    for sect in sorted(section_stats.keys()):
        k, t = section_stats[sect]
        pct = k / t * 100 if t else 0
        print(f"    {sect:<12} {k:>5}/{t:<5} ({pct:.1f}%)")

    # Count new root contributions
    new_roots = {'cheos', 'hed', 'ches'}
    new_count = sum(1 for w in all_words
                    if full_decompose(w['word'])['root'] in new_roots)
    print(f"\n  New roots added this phase: {', '.join(new_roots)}")
    print(f"  Tokens covered by new roots: {new_count}")


# ══════════════════════════════════════════════════════════════════
# 26b: CRACK `air` (449 tokens)
# ══════════════════════════════════════════════════════════════════

def run_crack_air(all_words):
    print("\n" + "="*76)
    print("PHASE 26b: CRACKING ROOT 'air' (449 tokens)")
    print("="*76)

    locus_seqs = defaultdict(list)
    for w in all_words:
        locus_seqs[w['locus']].append(w)

    air_contexts = []
    for locus, words in locus_seqs.items():
        for i, w in enumerate(words):
            dec = full_decompose(w['word'])
            if dec['root'] == 'air':
                left = [words[j] for j in range(max(0,i-3), i)]
                right = [words[j] for j in range(i+1, min(len(words), i+4))]
                air_contexts.append({
                    'word': w['word'], 'locus': locus,
                    'section': w['section'], 'dec': dec,
                    'left': left, 'right': right,
                })

    print(f"\n  Total 'air'-root tokens: {len(air_contexts)}")

    # Section distribution
    sect = Counter(c['section'] for c in air_contexts)
    print(f"\n  Sections: {dict(sect.most_common())}")

    # Prefix distribution — tells us if it's a noun or verb
    pfx = Counter(c['dec']['prefix'] for c in air_contexts if c['dec']['prefix'])
    print(f"\n  Prefixes: {dict(pfx.most_common())}")
    # d-prefix dominant? → genitive → noun
    # s-prefix dominant? → verbal → verb

    # Suffix distribution
    sfx = Counter(c['dec']['suffix'] for c in air_contexts if c['dec']['suffix'])
    print(f"\n  Suffixes: {dict(sfx.most_common())}")

    # Determinative distribution
    det = Counter(c['dec']['determinative'] for c in air_contexts if c['dec']['determinative'])
    print(f"\n  Determinatives: {dict(det.most_common())}")

    # Top word forms
    forms = Counter(c['word'] for c in air_contexts)
    print(f"\n  Top word forms:")
    for form, cnt in forms.most_common(15):
        d = full_decompose(form)
        print(f"    {form:<20} {cnt:>4}  pfx={d['prefix']:<3} sfx={d['suffix']:<5} det={d['determinative']}")

    # Known-root collocates
    left_roots = Counter()
    right_roots = Counter()
    for c in air_contexts:
        for lw in c['left']:
            ld = full_decompose(lw['word'])
            if ld['root'] in ALL_ROOTS:
                left_roots[ld['root']] += 1
        for rw in c['right']:
            rd = full_decompose(rw['word'])
            if rd['root'] in ALL_ROOTS:
                right_roots[rd['root']] += 1

    print(f"\n  Left collocates (known roots):")
    for root, cnt in left_roots.most_common(10):
        print(f"    {root:<10} ({ALL_ROOTS.get(root,''):<20}): {cnt}")

    print(f"\n  Right collocates (known roots):")
    for root, cnt in right_roots.most_common(10):
        print(f"    {root:<10} ({ALL_ROOTS.get(root,''):<20}): {cnt}")

    # Context examples — show 10 full contexts with glosses
    print(f"\n  Context examples (10 from each major section):")
    shown_by_sect = Counter()
    for c in air_contexts:
        if shown_by_sect[c['section']] >= 5:
            continue
        shown_by_sect[c['section']] += 1
        left_gloss = " | ".join(smart_gloss(lw['word']) for lw in c['left'])
        right_gloss = " | ".join(smart_gloss(rw['word']) for rw in c['right'])
        print(f"    {c['locus']} ({c['section']}):")
        print(f"      ...{left_gloss} | **{smart_gloss(c['word'])}** | {right_gloss}...")

    # Coptic/Arabic candidates comparison
    print(f"\n  CANDIDATE IDENTIFICATIONS:")
    for name, meaning in COPTIC_CANDIDATES.get('air', []):
        print(f"    {name}: {meaning}")

    # Key test: is 'air' nominal (takes d-prefix predominantly)?
    d_pct = pfx.get('d', 0) / len(air_contexts) * 100
    s_pct = pfx.get('s', 0) / len(air_contexts) * 100
    o_pct = pfx.get('o', 0) / len(air_contexts) * 100
    qo_pct = pfx.get('qo', 0) / len(air_contexts) * 100

    print(f"\n  GRAMMATICAL PROFILE:")
    print(f"    d- (genitive) = {d_pct:.1f}% → {'NOUN' if d_pct > 20 else 'mixed'}")
    print(f"    s- (verbal)   = {s_pct:.1f}% → {'VERB' if s_pct > 20 else 'mixed'}")
    print(f"    o- (article)  = {o_pct:.1f}% → nominal reference")
    print(f"    qo- (rel.)    = {qo_pct:.1f}% → relative clause")

    # Compare to known nouns and verbs
    # Known nouns: al, am, ar, or (high d- prefix)
    # Known verbs: h, he (high s- prefix)
    print(f"\n  COMPARISON TO KNOWN ROOTS:")
    for ref_root in ['al','am','ar','h','he','ch','l']:
        ref_tokens = [w for w in all_words if full_decompose(w['word'])['root'] == ref_root]
        ref_pfx = Counter(full_decompose(w['word'])['prefix'] for w in ref_tokens
                         if full_decompose(w['word'])['prefix'])
        ref_total = len(ref_tokens) if ref_tokens else 1
        ref_d = ref_pfx.get('d',0) / ref_total * 100
        ref_s = ref_pfx.get('s',0) / ref_total * 100
        ref_o = ref_pfx.get('o',0) / ref_total * 100
        print(f"    {ref_root:<6} ({ALL_ROOTS[ref_root]:<14}): d={ref_d:.0f}% s={ref_s:.0f}% o={ref_o:.0f}%")


# ══════════════════════════════════════════════════════════════════
# 26c: CRACK NEXT 5 UNKNOWNS
# ══════════════════════════════════════════════════════════════════

def run_crack_unknowns(all_words):
    print("\n" + "="*76)
    print("PHASE 26c: CRACKING NEXT 5 UNKNOWN ROOTS")
    print("="*76)

    targets = ['eo', 'lsh', 'eod', 'od', 'ai']

    locus_seqs = defaultdict(list)
    for w in all_words:
        locus_seqs[w['locus']].append(w)

    for target in targets:
        contexts = []
        for locus, words in locus_seqs.items():
            for i, w in enumerate(words):
                dec = full_decompose(w['word'])
                if dec['root'] == target:
                    left = [words[j] for j in range(max(0,i-3), i)]
                    right = [words[j] for j in range(i+1, min(len(words), i+4))]
                    contexts.append({
                        'word': w['word'], 'locus': locus,
                        'section': w['section'], 'dec': dec,
                        'left': left, 'right': right,
                    })

        if not contexts:
            continue

        print(f"\n  {'━'*68}")
        print(f"  ROOT '{target}' — {len(contexts)} tokens")
        print(f"  {'━'*68}")

        # Section
        sect = Counter(c['section'] for c in contexts)
        print(f"  Sections: {dict(sect.most_common())}")

        # Prefix/suffix/det
        pfx = Counter(c['dec']['prefix'] for c in contexts if c['dec']['prefix'])
        sfx = Counter(c['dec']['suffix'] for c in contexts if c['dec']['suffix'])
        det = Counter(c['dec']['determinative'] for c in contexts if c['dec']['determinative'])
        print(f"  Prefixes: {dict(pfx.most_common(5))}")
        print(f"  Suffixes: {dict(sfx.most_common(5))}")
        print(f"  Determinatives: {dict(det.most_common())}")

        # Top forms
        forms = Counter(c['word'] for c in contexts)
        print(f"  Top forms: {', '.join(f'{f}({c})' for f,c in forms.most_common(5))}")

        # Collocates
        lr = Counter()
        rr = Counter()
        for c in contexts:
            for lw in c['left']:
                ld = full_decompose(lw['word'])
                if ld['root'] in ALL_ROOTS:
                    lr[ld['root']] += 1
            for rw in c['right']:
                rd = full_decompose(rw['word'])
                if rd['root'] in ALL_ROOTS:
                    rr[rd['root']] += 1

        left_str = ", ".join(f"{ALL_ROOTS[r]}({c})" for r,c in lr.most_common(5))
        right_str = ", ".join(f"{ALL_ROOTS[r]}({c})" for r,c in rr.most_common(5))
        print(f"  Left collocates: {left_str}")
        print(f"  Right collocates: {right_str}")

        # Grammatical profile
        total = len(contexts)
        d_pct = pfx.get('d',0)/total*100
        s_pct = pfx.get('s',0)/total*100
        o_pct = pfx.get('o',0)/total*100
        print(f"  Grammar: d={d_pct:.0f}% s={s_pct:.0f}% o={o_pct:.0f}% → {'NOUN' if d_pct > s_pct else 'VERB'}")

        # e→a shift
        shifted = target.replace('e','a')
        if shifted != target:
            print(f"  e→a shift: '{target}' → '{shifted}'")

        # Candidates
        if target in COPTIC_CANDIDATES:
            print(f"  Candidates:")
            for name, meaning in COPTIC_CANDIDATES[target]:
                print(f"    {name}: {meaning}")

        # Compound test: can it decompose?
        if len(target) >= 3:
            for split in range(1, len(target)):
                c1 = target[:split]
                c2 = target[split:]
                if c1 in ALL_ROOTS and c2 in ALL_ROOTS:
                    print(f"  COMPOUND? {c1}({ALL_ROOTS[c1]}) + {c2}({ALL_ROOTS[c2]})")

        # Context examples
        print(f"  Context examples:")
        for c in contexts[:5]:
            left_gloss = " | ".join(smart_gloss(lw['word']) for lw in c['left'][-2:])
            right_gloss = " | ".join(smart_gloss(rw['word']) for rw in c['right'][:2])
            print(f"    {c['locus']} ({c['section']}): ...{left_gloss} | **{smart_gloss(c['word'])}** | {right_gloss}...")


# ══════════════════════════════════════════════════════════════════
# 26d: ZODIAC RE-TRANSLATION
# ══════════════════════════════════════════════════════════════════

def run_zodiac_translation():
    print("\n" + "="*76)
    print("PHASE 26d: ZODIAC RING RE-TRANSLATION")
    print("="*76)

    zodiac_folios = ['f72v1', 'f72v2', 'f72v3', 'f73r', 'f73v']
    folio_dir = Path("folios")

    all_zodiac_known = 0
    all_zodiac_total = 0

    for fname in zodiac_folios:
        fpath = folio_dir / f"{fname}.txt"
        if not fpath.exists():
            # Try without version number
            alt = folio_dir / f"{fname.rstrip('0123456789')}.txt"
            if not alt.exists():
                continue
            fpath = alt

        print(f"\n  {'='*60}")
        print(f"  {fname}")
        print(f"  {'='*60}\n")

        folio_lines = extract_folio_lines(fpath)
        for fl in folio_lines:
            glosses = []
            n_known = 0
            n_total = 0
            for tok in fl['tokens']:
                dec = full_decompose(tok)
                n_total += 1
                if dec['root'] in ALL_ROOTS:
                    n_known += 1
                glosses.append(smart_gloss(tok))

            if not n_total:
                continue
            pct = n_known / n_total * 100
            all_zodiac_known += n_known
            all_zodiac_total += n_total

            marker = "*" if pct == 100 else " "
            print(f"  {marker}{fl['locus']} [{n_known}/{n_total}={pct:.0f}%]")
            print(f"    VOY: {' '.join(fl['tokens'])}")
            print(f"    ENG: {', '.join(glosses)}")
            print()

    if all_zodiac_total:
        overall_pct = all_zodiac_known / all_zodiac_total * 100
        print(f"\n  ZODIAC OVERALL: {all_zodiac_known}/{all_zodiac_total} = {overall_pct:.1f}%")


# ══════════════════════════════════════════════════════════════════
# 26e: HERBAL DEEP DIVE
# ══════════════════════════════════════════════════════════════════

def run_herbal_analysis(all_words):
    print("\n" + "="*76)
    print("PHASE 26e: HERBAL SECTION DEEP DIVE")
    print("="*76)

    herbal = [w for w in all_words if w['section'].startswith('herbal')]
    bio = [w for w in all_words if w['section'] == 'bio']

    print(f"\n  Herbal tokens: {len(herbal)}")
    print(f"  Bio tokens:    {len(bio)}")

    # Coverage comparison
    h_known = sum(1 for w in herbal if full_decompose(w['word'])['root'] in ALL_ROOTS)
    b_known = sum(1 for w in bio if full_decompose(w['word'])['root'] in ALL_ROOTS)
    print(f"\n  Herbal coverage: {h_known}/{len(herbal)} = {h_known/len(herbal)*100:.1f}%")
    print(f"  Bio coverage:    {b_known}/{len(bio)} = {b_known/len(bio)*100:.1f}%")

    # What unknown roots are herbal-specific?
    herbal_unknown = Counter()
    bio_unknown = Counter()
    for w in herbal:
        dec = full_decompose(w['word'])
        if dec['root'] not in ALL_ROOTS and len(dec['root']) >= 2:
            herbal_unknown[dec['root']] += 1
    for w in bio:
        dec = full_decompose(w['word'])
        if dec['root'] not in ALL_ROOTS and len(dec['root']) >= 2:
            bio_unknown[dec['root']] += 1

    herbal_only_roots = set(herbal_unknown.keys()) - set(bio_unknown.keys())

    print(f"\n  Unknown roots in herbal: {len(herbal_unknown)}")
    print(f"  Unknown roots in bio: {len(bio_unknown)}")
    print(f"  Herbal-only unknown roots: {len(herbal_only_roots)}")

    print(f"\n  Top unknown roots in HERBAL (all):")
    for root, cnt in herbal_unknown.most_common(15):
        bio_cnt = bio_unknown.get(root, 0)
        marker = " [HERBAL-ONLY]" if root in herbal_only_roots else ""
        shifted = root.replace('e','a')
        shift_note = f" (→{shifted})" if shifted != root else ""
        print(f"    {root:<10} herbal:{cnt:>4}  bio:{bio_cnt:>4}{marker}{shift_note}")

    print(f"\n  Top HERBAL-ONLY unknown roots:")
    herbal_only_ranked = sorted(herbal_only_roots,
                                key=lambda r: -herbal_unknown.get(r, 0))
    for root in herbal_only_ranked[:15]:
        cnt = herbal_unknown[root]
        shifted = root.replace('e','a')
        shift_note = f" → {shifted}" if shifted != root else ""
        print(f"    {root:<10} {cnt:>4} tokens{shift_note}")

    # What determinatives dominate in herbal vs bio?
    herbal_det = Counter(full_decompose(w['word'])['determinative']
                         for w in herbal if full_decompose(w['word'])['determinative'])
    bio_det = Counter(full_decompose(w['word'])['determinative']
                      for w in bio if full_decompose(w['word'])['determinative'])

    print(f"\n  Determinative distribution:")
    print(f"  {'Det':<5} {'Herbal':>8} {'%':>6} {'Bio':>8} {'%':>6}")
    for det in 'ktfp':
        h_cnt = herbal_det.get(det, 0)
        b_cnt = bio_det.get(det, 0)
        h_pct = h_cnt / len(herbal) * 100
        b_pct = b_cnt / len(bio) * 100
        print(f"    {det:<3} {h_cnt:>8} {h_pct:>5.1f}% {b_cnt:>8} {b_pct:>5.1f}%")

    # Translate best herbal page (most tokens)
    herbal_folio_counts = Counter(w['folio'] for w in herbal)
    best_herbal = herbal_folio_counts.most_common(3)
    print(f"\n  Largest herbal folios: {best_herbal}")

    # Translate top herbal folio
    if best_herbal:
        top_folio = best_herbal[0][0]
        fpath = Path(f"folios/{top_folio}.txt")
        if fpath.exists():
            print(f"\n  {'='*60}")
            print(f"  {top_folio} — HERBAL TRANSLATION")
            print(f"  {'='*60}\n")

            folio_lines = extract_folio_lines(fpath)
            total_k = 0
            total_t = 0
            for fl in folio_lines[:15]:  # First 15 lines
                glosses = []
                n_known = 0; n_total = 0
                for tok in fl['tokens']:
                    dec = full_decompose(tok)
                    n_total += 1
                    if dec['root'] in ALL_ROOTS:
                        n_known += 1
                    glosses.append(smart_gloss(tok))
                if not n_total: continue
                pct = n_known / n_total * 100
                total_k += n_known
                total_t += n_total
                marker = "*" if pct == 100 else " "
                print(f"  {marker}{fl['locus']} [{n_known}/{n_total}={pct:.0f}%]")
                print(f"    VOY: {' '.join(fl['tokens'])}")
                print(f"    ENG: {', '.join(glosses)}")
                print()

            if total_t:
                print(f"  {top_folio} coverage (first 15 lines): {total_k}/{total_t} = {total_k/total_t*100:.1f}%")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("PHASE 26: VOCABULARY EXPANSION & CROSS-SECTION VALIDATION")
    print("="*76)

    all_words = extract_all_words()
    print(f"Loaded {len(all_words)} word tokens")

    run_coverage_update(all_words)     # 26a
    run_crack_air(all_words)           # 26b
    run_crack_unknowns(all_words)      # 26c
    run_zodiac_translation()           # 26d
    run_herbal_analysis(all_words)     # 26e

    Path("results").mkdir(exist_ok=True)
    results = {
        "phase": 26,
        "vocabulary_size": len(ALL_ROOTS),
        "confirmed_roots": len(CONFIRMED_VOCAB),
        "compounds": len(COMPOUND_VOCAB),
    }
    Path("results/phase26_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(f"\n  Results saved to results/phase26_results.json")


if __name__ == "__main__":
    main()
