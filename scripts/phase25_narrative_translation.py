#!/usr/bin/env python3
"""
Phase 25 — Narrative Reconstruction & Remaining Root Resolution
================================================================

Phase 24 proved that gallows determinatives ARE the content words (like
Mandarin classifiers), with root 'e' as grammatical glue.  Six 100%-coverage
f78r lines now produce intelligible medical-astrological sequences.

This phase:
  25a) UNKNOWN ROOT CENSUS — Profile every remaining unknown root by frequency,
       section, collocates, and morphological context to crack more roots
  25b) HO VALIDATION — Test whether 'ho'=face/front (Coptic) holds: does
       it co-occur with body-part roots in bio sections?
  25c) ALCH VALIDATION — Does 'alch' appear with substance/preparation
       words? Confirm the alchemy connection
  25d) COHERENT PARAGRAPH TRANSLATION — Take f78r lines 1-15 and produce
       a connected English paragraph using classifier semantics + medical
       template, also translate f76r best passage
  25e) FULL VOCABULARY TABLE — Compile all cracked roots, compounds,
       and grammatical morphemes into a single reference table

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
# VOCABULARY (29 confirmed + compounds from Phase 24)
# ══════════════════════════════════════════════════════════════════

CONFIRMED_VOCAB = {
    'esed':'lion','she':'tree/plant','al':'stone','he':'fall/occur',
    'ro':'mouth','les':'tongue','ran':'name','cham':'hot/warm',
    'res':'south','ar':'king/great','or':'king/great',
    'ol':'carry/bear','am':'water','chas':'lord/master',
    'eos':'star','es':'star','chol':'celestial-body','cho':'substance',
    'eosh':'dry','sheo':'dry','choam':'hot','rar':'king',
    'yed':'hand','h':'happen/occur','a':'great-one',
    'e':'this/that','ch':'do/make','l':'remedy/thing','d':'matter/thing',
    'ho':'face/front',     # Coptic ho, confirmed Phase 24
}

# Compound resolutions from Phase 24
COMPOUND_VOCAB = {
    'lch':  'remedy-making',
    'ed':   'this-matter',
    'che':  'make-this',
    'ched': 'prepare-this',
    'chod': 'substance-matter',
    'alch': 'stone-working (alchemy)',
    'sh':   'it-happens',
}

# Merge for glossing
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
    'aiin': 'ones(pl)',
    'ain':  'ones(obl)',
    'iin':  '(pl)',
    'in':   '(pl)',
    'ar':   '-er/doer',
    'or':   '-er',
    'al':   'in/at(place)',
    'ol':   '(nominalized)',
    'eedy': '(intensely-described)',
    'edy':  '(described)',
    'ody':  '(prescribed)',
    'dy':   '(abr.)',
    'ey':   '(gen/of)',
    'y':    '(-state)',
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
    """Extract parsed lines from a single folio file."""
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
    """Produce a readable gloss using classifier semantics."""
    dec = full_decompose(word)
    root = dec['root']
    pfx = dec['prefix']
    sfx = dec['suffix']
    det = dec['determinative']

    parts = []
    if pfx:
        parts.append(PREFIX_MEANING.get(pfx, pfx))

    # Demonstrative + classifier → fused concept
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


def smart_gloss_short(word):
    """Shorter gloss for paragraph construction — no brackets."""
    dec = full_decompose(word)
    root = dec['root']
    pfx = dec['prefix']
    sfx = dec['suffix']
    det = dec['determinative']

    # Build semantic meaning
    det_label = ''
    if det:
        det_map = {'k':'bodily','t':'celestial','f':'plant','p':'discourse'}
        det_label = det_map.get(det, det)

    pfx_label = ''
    if pfx:
        pfx_map = {'qo':'which','q':'which','o':'the','do':'of the',
                    'd':'of','so':'it-','s':'verbal','y':'adj.'}
        pfx_label = pfx_map.get(pfx, pfx)

    sfx_label = ''
    if sfx:
        sfx_map = {'aiin':'rulers','ain':'rulers(obl)','iin':'s','in':'s',
                    'ar':'agent','or':'agent','al':'place','ol':'(nom)',
                    'edy':'(descr.)','ody':'(prescr.)','eedy':'(intens.)',
                    'dy':'','ey':'(of)','y':''}
        sfx_label = sfx_map.get(sfx, sfx)

    # Core meaning
    if root == 'e' and det:
        core = f"this {det_label} [thing]" if det_label else "this"
    elif root == 'a' and det:
        core = f"the {det_label} noble" if det_label else "the great one"
    elif root in ALL_ROOTS:
        base = ALL_ROOTS[root]
        if det_label:
            core = f"{det_label} {base}"
        else:
            core = base
    else:
        core = f"?{root}?"

    # Assemble
    result = ''
    if pfx_label:
        result = pfx_label + ' '
    result += core
    if sfx_label:
        result += ' ' + sfx_label
    return result.strip()


# ══════════════════════════════════════════════════════════════════
# 25a: UNKNOWN ROOT CENSUS
# ══════════════════════════════════════════════════════════════════

def run_unknown_census(all_words):
    print("\n" + "="*76)
    print("PHASE 25a: REMAINING UNKNOWN ROOT CENSUS")
    print("="*76)

    unknown_profiles = defaultdict(lambda: {
        'count': 0, 'sections': Counter(), 'dets': Counter(),
        'prefixes': Counter(), 'suffixes': Counter(),
        'left_roots': Counter(), 'right_roots': Counter(),
        'forms': Counter(),
    })

    # Build locus sequences for collocate analysis
    locus_seqs = defaultdict(list)
    for w in all_words:
        locus_seqs[w['locus']].append(w)

    # Profile unknowns
    for w in all_words:
        dec = full_decompose(w['word'])
        root = dec['root']
        if root in ALL_ROOTS:
            continue
        if len(root) < 2:
            continue  # Skip single-char unknowns

        p = unknown_profiles[root]
        p['count'] += 1
        p['sections'][w['section']] += 1
        if dec['determinative']:
            p['dets'][dec['determinative']] += 1
        if dec['prefix']:
            p['prefixes'][dec['prefix']] += 1
        if dec['suffix']:
            p['suffixes'][dec['suffix']] += 1
        p['forms'][w['word']] += 1

    # Add collocate info
    for locus, words in locus_seqs.items():
        for i, w in enumerate(words):
            dec = full_decompose(w['word'])
            root = dec['root']
            if root in ALL_ROOTS or len(root) < 2:
                continue
            if root not in unknown_profiles:
                continue
            if i > 0:
                left_dec = full_decompose(words[i-1]['word'])
                if left_dec['root'] in ALL_ROOTS:
                    unknown_profiles[root]['left_roots'][left_dec['root']] += 1
            if i < len(words)-1:
                right_dec = full_decompose(words[i+1]['word'])
                if right_dec['root'] in ALL_ROOTS:
                    unknown_profiles[root]['right_roots'][right_dec['root']] += 1

    # Sort by frequency
    ranked = sorted(unknown_profiles.items(), key=lambda x: -x[1]['count'])

    print(f"\n  {len(ranked)} unknown roots found. Top 25:\n")

    for root, p in ranked[:25]:
        print(f"  {'─'*68}")
        print(f"  ROOT '{root}' — {p['count']} tokens")
        print(f"  {'─'*68}")

        # Section distribution
        sect_str = ", ".join(f"{s}:{c}" for s,c in p['sections'].most_common(4))
        print(f"    Sections: {sect_str}")

        # Determinatives
        if p['dets']:
            det_str = ", ".join(f"{d}:{c}" for d,c in p['dets'].most_common())
            print(f"    Determinatives: {det_str}")
        else:
            print(f"    Determinatives: (none / bare root)")

        # Affixes
        if p['prefixes']:
            pfx_str = ", ".join(f"{pf}:{c}" for pf,c in p['prefixes'].most_common(3))
            print(f"    Prefixes: {pfx_str}")
        if p['suffixes']:
            sfx_str = ", ".join(f"{sf}:{c}" for sf,c in p['suffixes'].most_common(3))
            print(f"    Suffixes: {sfx_str}")

        # Top word forms
        top_forms = ", ".join(f"{f}({c})" for f,c in p['forms'].most_common(5))
        print(f"    Top forms: {top_forms}")

        # Collocates
        if p['left_roots']:
            l_str = ", ".join(f"{ALL_ROOTS[r]}({c})" for r,c in p['left_roots'].most_common(4))
            print(f"    Left collocates (known): {l_str}")
        if p['right_roots']:
            r_str = ", ".join(f"{ALL_ROOTS[r]}({c})" for r,c in p['right_roots'].most_common(4))
            print(f"    Right collocates (known): {r_str}")

        # Attempt Coptic/Arabic identification
        # Apply e→a shift
        shifted = root.replace('e','a')
        if shifted != root:
            print(f"    e→a shift: '{root}' → '{shifted}'")

        print()

    # Coverage report
    total_tokens = len(all_words)
    known_count = sum(1 for w in all_words
                      if full_decompose(w['word'])['root'] in ALL_ROOTS)
    unknown_count = total_tokens - known_count
    print(f"\n  COVERAGE SUMMARY:")
    print(f"    Total tokens:   {total_tokens}")
    print(f"    Known roots:    {known_count} ({known_count/total_tokens*100:.1f}%)")
    print(f"    Unknown roots:  {unknown_count} ({unknown_count/total_tokens*100:.1f}%)")

    # If we crack the top 10 unknowns, how much would coverage improve?
    top10_tokens = sum(p['count'] for _, p in ranked[:10])
    new_coverage = (known_count + top10_tokens) / total_tokens * 100
    print(f"    If top 10 unknowns cracked: {new_coverage:.1f}% coverage (+{top10_tokens} tokens)")

    return ranked


# ══════════════════════════════════════════════════════════════════
# 25b: HO VALIDATION
# ══════════════════════════════════════════════════════════════════

def run_ho_validation(all_words):
    print("\n" + "="*76)
    print("PHASE 25b: 'ho' (=FACE/FRONT?) VALIDATION")
    print("="*76)

    # Collect ho contexts
    locus_seqs = defaultdict(list)
    for w in all_words:
        locus_seqs[w['locus']].append(w)

    ho_contexts = []
    for locus, words in locus_seqs.items():
        for i, w in enumerate(words):
            dec = full_decompose(w['word'])
            if dec['root'] == 'ho':
                left = []
                right = []
                for j in range(max(0,i-3), i):
                    left.append(words[j]['word'])
                for j in range(i+1, min(len(words), i+4)):
                    right.append(words[j]['word'])
                ho_contexts.append({
                    'word': w['word'],
                    'locus': locus,
                    'section': w['section'],
                    'left': left,
                    'right': right,
                    'dec': dec,
                })

    print(f"\n  Total 'ho'-root tokens: {len(ho_contexts)}")

    # Section distribution
    sect_counts = Counter(c['section'] for c in ho_contexts)
    print(f"\n  Section distribution:")
    for sect, cnt in sect_counts.most_common():
        pct = cnt / len(ho_contexts) * 100
        print(f"    {sect:<12} {cnt:>4} ({pct:.1f}%)")

    # Word forms
    form_counts = Counter(c['word'] for c in ho_contexts)
    print(f"\n  Word forms:")
    for form, cnt in form_counts.most_common(10):
        dec = full_decompose(form)
        print(f"    {form:<20} {cnt:>4}  pfx={dec['prefix']:<3} sfx={dec['suffix']:<5} det={dec['determinative']}")

    # Body-part collocates test: if ho=face, it should co-occur with
    # ro=mouth, les=tongue, yed=hand, am=water (washing)
    body_roots = {'ro','les','yed','am','he','she','al'}
    body_collocates = Counter()
    all_collocates = Counter()
    for c in ho_contexts:
        for neighbor in c['left'] + c['right']:
            ndec = full_decompose(neighbor)
            nroot = ndec['root']
            if nroot in ALL_ROOTS:
                all_collocates[nroot] += 1
            if nroot in body_roots:
                body_collocates[nroot] += 1

    print(f"\n  Body-part collocates of 'ho':")
    for root, cnt in body_collocates.most_common():
        print(f"    {root:<10} ({ALL_ROOTS.get(root,'')}): {cnt} co-occurrences")

    print(f"\n  All known-root collocates of 'ho' (top 15):")
    for root, cnt in all_collocates.most_common(15):
        print(f"    {root:<10} ({ALL_ROOTS.get(root,''):<18}): {cnt}")

    # Compare: in bio sections, does ho appear near body-part words?
    bio_ho = [c for c in ho_contexts if c['section'] == 'bio']
    herbal_ho = [c for c in ho_contexts if c['section'].startswith('herbal')]

    for label, subset in [("BIO", bio_ho), ("HERBAL", herbal_ho)]:
        if not subset:
            print(f"\n  {label}: No 'ho' tokens")
            continue
        print(f"\n  {label} 'ho' contexts ({len(subset)}):")
        for c in subset[:8]:
            left_gloss = [smart_gloss(w) for w in c['left']]
            right_gloss = [smart_gloss(w) for w in c['right']]
            print(f"    {c['locus']}: ...{' | '.join(left_gloss)} | **{smart_gloss(c['word'])}** | {' | '.join(right_gloss)}...")


# ══════════════════════════════════════════════════════════════════
# 25c: ALCH VALIDATION
# ══════════════════════════════════════════════════════════════════

def run_alch_validation(all_words):
    print("\n" + "="*76)
    print("PHASE 25c: 'alch' (=ALCHEMY/STONE-WORKING?) VALIDATION")
    print("="*76)

    locus_seqs = defaultdict(list)
    for w in all_words:
        locus_seqs[w['locus']].append(w)

    alch_contexts = []
    for locus, words in locus_seqs.items():
        for i, w in enumerate(words):
            dec = full_decompose(w['word'])
            if dec['root'] == 'alch':
                left = [words[j]['word'] for j in range(max(0,i-3), i)]
                right = [words[j]['word'] for j in range(i+1, min(len(words), i+4))]
                alch_contexts.append({
                    'word': w['word'],
                    'locus': locus,
                    'section': w['section'],
                    'left': left,
                    'right': right,
                    'dec': dec,
                })

    print(f"\n  Total 'alch'-root tokens: {len(alch_contexts)}")

    if not alch_contexts:
        print("  No 'alch' tokens found — root may only appear as part of longer forms.")
        # Search for any word containing 'alch' as substring
        alch_words = Counter()
        for w in all_words:
            if 'alch' in w['word']:
                alch_words[w['word']] += 1
        if alch_words:
            print(f"\n  Words containing 'alch' substring:")
            for word, cnt in alch_words.most_common(15):
                dec = full_decompose(word)
                print(f"    {word:<25} {cnt:>4}  root={dec['root']}, det={dec['determinative']}")
        return

    sect_counts = Counter(c['section'] for c in alch_contexts)
    print(f"\n  Section distribution:")
    for sect, cnt in sect_counts.most_common():
        print(f"    {sect:<12} {cnt:>4}")

    form_counts = Counter(c['word'] for c in alch_contexts)
    print(f"\n  Word forms:")
    for form, cnt in form_counts.most_common():
        dec = full_decompose(form)
        print(f"    {form:<20} {cnt:>4}  pfx={dec['prefix']:<3} sfx={dec['suffix']:<5} det={dec['determinative']}")

    # Collocates
    print(f"\n  Context examples:")
    for c in alch_contexts[:15]:
        left_gloss = [smart_gloss(w) for w in c['left']]
        right_gloss = [smart_gloss(w) for w in c['right']]
        print(f"    {c['locus']} ({c['section']}):")
        print(f"      ...{' | '.join(left_gloss)} | **{smart_gloss(c['word'])}** | {' | '.join(right_gloss)}...")

    # Check for substance/preparation collocates
    prep_roots = {'ch','cho','chol','cham','choam','l','am','al'}
    prep_collocates = Counter()
    for c in alch_contexts:
        for neighbor in c['left'] + c['right']:
            ndec = full_decompose(neighbor)
            if ndec['root'] in prep_roots:
                prep_collocates[ndec['root']] += 1

    if prep_collocates:
        print(f"\n  Substance/preparation collocates:")
        for root, cnt in prep_collocates.most_common():
            print(f"    {root:<10} ({ALL_ROOTS.get(root,''):<18}): {cnt}")


# ══════════════════════════════════════════════════════════════════
# 25d: COHERENT PARAGRAPH TRANSLATION
# ══════════════════════════════════════════════════════════════════

def run_paragraph_translation():
    print("\n" + "="*76)
    print("PHASE 25d: COHERENT PARAGRAPH TRANSLATION")
    print("="*76)

    print("""
  Using classifier-merged semantics + medical text template to produce
  readable English paragraphs from Voynichese.

  Template (medieval astrological-medical):
  "Concerning [body part / condition], [celestial influence] governs [it].
   The [substance / remedy] is made [from / with] [ingredients].
   The great ones / rulers [prescribe / carry] [the treatment]."
""")

    for folio_name, line_range, section_label in [
        ("f78r", (1, 47), "BIO (nymph figures, bodily conditions)"),
        ("f76r", (1, 30), "BIO (nymph figures, near 100% lines)"),
        ("f1r",  (1, 20), "HERBAL-A (first herbal page)"),
    ]:
        fpath = Path(f"folios/{folio_name}.txt")
        if not fpath.exists():
            print(f"\n  {folio_name}: file not found")
            continue

        print(f"\n  {'='*68}")
        print(f"  {folio_name} — {section_label}")
        print(f"  {'='*68}\n")

        folio_lines = extract_folio_lines(fpath)

        # Filter to line range
        filtered = []
        for fl in folio_lines:
            lm = re.search(r'\.(\d+)', fl['locus'])
            if lm:
                ln = int(lm.group(1))
                if line_range[0] <= ln <= line_range[1]:
                    filtered.append(fl)
            else:
                filtered.append(fl)

        if not filtered:
            print(f"  No lines in range {line_range}")
            continue

        # For the paragraph reconstruction, we'll produce:
        # 1. Line-by-line word+gloss
        # 2. Then a connected paragraph attempt

        all_glossed = []  # list of (locus, voy_tokens, eng_glosses, coverage)

        for fl in filtered:
            glosses = []
            short_glosses = []
            n_known = 0
            n_total = 0
            for tok in fl['tokens']:
                dec = full_decompose(tok)
                n_total += 1
                if dec['root'] in ALL_ROOTS:
                    n_known += 1
                glosses.append(smart_gloss(tok))
                short_glosses.append(smart_gloss_short(tok))

            pct = n_known / n_total * 100 if n_total else 0
            all_glossed.append((fl['locus'], fl['tokens'], glosses,
                                short_glosses, pct, n_known, n_total))

            # Print line-by-line
            print(f"  {fl['locus']} [{n_known}/{n_total}={pct:.0f}%]")
            print(f"    VOY: {' '.join(fl['tokens'])}")
            print(f"    ENG: {', '.join(short_glosses)}")
            print()

        # Summary statistics
        total_known = sum(g[5] for g in all_glossed)
        total_words = sum(g[6] for g in all_glossed)
        overall_pct = total_known / total_words * 100 if total_words else 0

        # Lines with 100% coverage
        full_lines = [(g[0], g[3]) for g in all_glossed if g[4] == 100]

        print(f"\n  SUMMARY for {folio_name}:")
        print(f"    Total words: {total_words}")
        print(f"    Known roots: {total_known} ({overall_pct:.1f}%)")
        print(f"    Lines at 100% coverage: {len(full_lines)}")

        if full_lines:
            print(f"\n  CONNECTED PARAGRAPH (100%-coverage lines only):\n")
            paragraph_parts = []
            for locus, short_g in full_lines:
                sentence = ", ".join(short_g)
                # Simple article/flow cleanup
                sentence = sentence.replace("  ", " ")
                paragraph_parts.append(f"    [{locus}] {sentence}")
            print("\n".join(paragraph_parts))

        # Full connected attempt — join ALL lines into flowing text
        print(f"\n  FULL CONNECTED ATTEMPT (all lines, ?root? = unknown):\n")
        for g in all_glossed:
            locus, voy_toks, _, short_g, pct, _, _ = g
            line_text = ", ".join(short_g)
            marker = "*" if pct == 100 else " "
            print(f"    {marker}{locus}: {line_text}")

        print()


# ══════════════════════════════════════════════════════════════════
# 25e: FULL VOCABULARY TABLE
# ══════════════════════════════════════════════════════════════════

def run_vocabulary_table(all_words):
    print("\n" + "="*76)
    print("PHASE 25e: COMPLETE VOCABULARY REFERENCE TABLE")
    print("="*76)

    # Count frequency for each root
    root_freq = Counter()
    for w in all_words:
        dec = full_decompose(w['word'])
        root_freq[dec['root']] += 1

    print(f"\n  ┌{'─'*12}┬{'─'*8}┬{'─'*30}┬{'─'*20}┐")
    print(f"  │ {'ROOT':<10} │ {'COUNT':>6} │ {'MEANING':<28} │ {'SOURCE':<18} │")
    print(f"  ├{'─'*12}┼{'─'*8}┼{'─'*30}┼{'─'*20}┤")

    # Sort by frequency
    for root in sorted(CONFIRMED_VOCAB.keys(), key=lambda r: -root_freq.get(r, 0)):
        meaning = CONFIRMED_VOCAB[root]
        freq = root_freq.get(root, 0)
        source = "Coptic (Sahidic)"
        if root in ('esed','ar','or','rar','chas','yed','res'):
            source = "Arabic"
        elif root in ('eos','es','eosh','sheo','choam','cham'):
            source = "Coptic+Arabic"
        elif root in ('e','a','d','h','ch','l'):
            source = "Coptic root"
        print(f"  │ {root:<10} │ {freq:>6} │ {meaning:<28} │ {source:<18} │")

    print(f"  ├{'─'*12}┼{'─'*8}┼{'─'*30}┼{'─'*20}┤")
    print(f"  │ {'COMPOUND':<10} │ {'COUNT':>6} │ {'MEANING':<28} │ {'COMPONENTS':<18} │")
    print(f"  ├{'─'*12}┼{'─'*8}┼{'─'*30}┼{'─'*20}┤")

    for root in sorted(COMPOUND_VOCAB.keys(), key=lambda r: -root_freq.get(r, 0)):
        meaning = COMPOUND_VOCAB[root]
        freq = root_freq.get(root, 0)
        print(f"  │ {root:<10} │ {freq:>6} │ {meaning:<28} │ {'compound':<18} │")

    print(f"  └{'─'*12}┴{'─'*8}┴{'─'*30}┴{'─'*20}┘")

    # Grammar summary
    print(f"\n  GRAMMAR MORPHEMES:")
    print(f"\n  Prefixes:")
    for pfx, meaning in PREFIX_MEANING.items():
        # Count
        pfx_count = sum(1 for w in all_words
                        if full_decompose(w['word'])['prefix'] == pfx)
        print(f"    {pfx}-{'':<6} {pfx_count:>6}  {meaning}")

    print(f"\n  Suffixes:")
    for sfx, meaning in SUFFIX_MEANING.items():
        sfx_count = sum(1 for w in all_words
                        if full_decompose(w['word'])['suffix'] == sfx)
        print(f"    -{sfx:<8} {sfx_count:>6}  {meaning}")

    print(f"\n  Gallows Determinatives:")
    for det, meaning in DET_MEANING.items():
        det_count = sum(1 for w in all_words
                        if full_decompose(w['word'])['determinative'] == det)
        print(f"    [{det}]{'':<6} {det_count:>6}  {meaning}")

    # Total morphemes accounted for
    total = len(all_words)
    roots_known = sum(1 for w in all_words if full_decompose(w['word'])['root'] in ALL_ROOTS)
    print(f"\n  FINAL COVERAGE: {roots_known}/{total} = {roots_known/total*100:.1f}%")
    print(f"  Known roots: {len(CONFIRMED_VOCAB)} confirmed + {len(COMPOUND_VOCAB)} compounds = {len(ALL_ROOTS)} total")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("PHASE 25: NARRATIVE RECONSTRUCTION & REMAINING ROOT RESOLUTION")
    print("="*76)

    all_words = extract_all_words()
    print(f"Loaded {len(all_words)} word tokens")

    unknown_ranked = run_unknown_census(all_words)   # 25a
    run_ho_validation(all_words)                     # 25b
    run_alch_validation(all_words)                   # 25c
    run_paragraph_translation()                      # 25d
    run_vocabulary_table(all_words)                   # 25e

    Path("results").mkdir(exist_ok=True)
    results = {
        "phase": 25,
        "total_confirmed_roots": len(CONFIRMED_VOCAB),
        "total_compound_roots": len(COMPOUND_VOCAB),
        "total_vocabulary": len(ALL_ROOTS),
    }
    Path("results/phase25_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(f"\n  Results saved to results/phase25_results.json")


if __name__ == "__main__":
    main()
