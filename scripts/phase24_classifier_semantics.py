#!/usr/bin/env python3
"""
Phase 24 — Classifier Semantics & Compound Root Resolution
============================================================

Phase 23 revealed that despite 67.9% root coverage, translations remain
semantically opaque because:
1. Root 'e' (this/that) appears everywhere — the GALLOWS DETERMINATIVE
   may carry the real nominal meaning (like Mandarin classifiers)
2. Top unknown roots (lch, ed, che) are likely compound forms

Sub-analyses:
  24a) CLASSIFIER-TO-MEANING MAP — For each gallows class (k,t,f,p),
       profile what CONTENT words they classify. Does k+e = "this substance",
       t+e = "this celestial influence", f+e = "this plant"?
  24b) COMPOUND ROOT RESOLUTION — Test whether lch = l+ch, ed = e+d,
       che = ch+e by comparing their distributions to the components
  24c) DAIIN CONTEXT ANALYSIS — At 1,049x, daiin is the most frequent
       word form. Validate d(of)+a(great-one)+iin(pl) by checking context
  24d) CONNECTED PROSE TRANSLATION — Use the highest-coverage bio lines
       to attempt paragraph-level coherent English for f78r
  24e) PREDICTIVE MODEL — Given the grammar and vocabulary, predict what
       a bio paragraph SHOULD say based on medieval medical texts
"""

import re, json, sys, io, math
from pathlib import Path
from collections import Counter, defaultdict
from common import classify_folio_v2 as classify_folio, collapse_echains, gallows_base, strip_gallows

# full_decompose restored as a LOCAL def: this script family uses a
# variant SUFFIXES list (no 'sy', different order), so it must bind to
# the local parse_morphology, not the common one.
def full_decompose(word):
    stripped, gals = strip_gallows(word)
    collapsed = collapse_echains(stripped)
    pfx, root, sfx = parse_morphology(collapsed)
    bases = [gallows_base(g) for g in gals]
    return dict(original=word, stripped=stripped, collapsed=collapsed,
                prefix=pfx or "", root=root, suffix=sfx or "",
                gallows=bases, determinative=bases[0] if bases else "")


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


CONFIRMED_VOCAB = {
    'esed':'lion','she':'tree/plant','al':'stone','he':'fall/occur',
    'ro':'mouth','les':'tongue','ran':'name','cham':'hot/warm',
    'res':'south','ar':'king/great','or':'king/great',
    'ol':'carry/bear','am':'water','chas':'lord/master',
    'eos':'star','es':'star','chol':'celestial-body','cho':'substance',
    'eosh':'dry','sheo':'dry','choam':'hot','rar':'king',
    'yed':'hand','h':'happen/occur','a':'great-one',
    'e':'this/that','ch':'do/make','l':'remedy/thing','d':'matter/thing',
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


# ══════════════════════════════════════════════════════════════════
# 24a: CLASSIFIER-TO-MEANING MAP
# ══════════════════════════════════════════════════════════════════

def run_classifier_semantics(all_words):
    print("\n" + "="*76)
    print("PHASE 24a: CLASSIFIER (GALLOWS DETERMINATIVE) SEMANTIC MAP")
    print("="*76)

    # For each gallows class, collect what roots they classify
    det_root_counts = defaultdict(Counter)  # det -> root -> count
    det_section = defaultdict(Counter)       # det -> section -> count
    det_suffix = defaultdict(Counter)        # det -> suffix -> count
    det_prefix = defaultdict(Counter)        # det -> prefix -> count
    det_total = Counter()
    no_det_roots = Counter()

    for w in all_words:
        dec = full_decompose(w['word'])
        root = dec['root']
        det = dec['determinative']
        section = w['section']

        if det:
            det_root_counts[det][root] += 1
            det_section[det][section] += 1
            if dec['suffix']: det_suffix[det][dec['suffix']] += 1
            if dec['prefix']: det_prefix[det][dec['prefix']] += 1
            det_total[det] += 1
        else:
            no_det_roots[root] += 1

    for det in ['k','t','f','p']:
        total = det_total[det]
        print(f"\n  {'='*68}")
        print(f"  CLASSIFIER '{det}' — {total} tokens")
        print(f"  {'='*68}")

        # Top roots with this determinative
        print(f"\n  Top roots classified by '{det}':")
        for root, cnt in det_root_counts[det].most_common(15):
            pct = cnt / total * 100
            meaning = CONFIRMED_VOCAB.get(root, f"?{root}?")
            print(f"    {root:<10} {cnt:>5} ({pct:>5.1f}%)  {meaning}")

        # Section distribution
        print(f"\n  Section distribution for '{det}':")
        for sect, cnt in det_section[det].most_common():
            pct = cnt / total * 100
            print(f"    {sect:<12} {cnt:>5} ({pct:>5.1f}%)")

        # Suffix distribution
        print(f"\n  Top suffixes with '{det}':")
        total_sfx = sum(det_suffix[det].values())
        for sfx, cnt in det_suffix[det].most_common(8):
            pct = cnt / total_sfx * 100 if total_sfx else 0
            print(f"    -{sfx:<8} {cnt:>5} ({pct:>5.1f}%)")

        # Prefix distribution
        print(f"\n  Top prefixes with '{det}':")
        total_pfx = sum(det_prefix[det].values())
        for pfx, cnt in det_prefix[det].most_common(6):
            pct = cnt / total_pfx * 100 if total_pfx else 0
            print(f"    {pfx}-{'':<7} {cnt:>5} ({pct:>5.1f}%)")

    # CRUCIAL: What does e+DET mean?
    print(f"\n  {'='*68}")
    print(f"  CRITICAL: ROOT 'e' + DETERMINATIVE COMBINATIONS")
    print(f"  {'='*68}")

    # For root 'e', what words appear with each determinative?
    e_det_forms = defaultdict(Counter)  # det -> full_word -> count
    e_det_section = defaultdict(Counter)
    for w in all_words:
        dec = full_decompose(w['word'])
        if dec['root'] == 'e' and dec['determinative']:
            det = dec['determinative']
            e_det_forms[det][w['word']] += 1
            e_det_section[det][w['section']] += 1

    for det in ['k','t','f','p']:
        if det not in e_det_forms: continue
        total = sum(e_det_forms[det].values())
        print(f"\n  e + {det}-determinative ({total} tokens):")
        for word, cnt in e_det_forms[det].most_common(8):
            dec = full_decompose(word)
            print(f"    {word:<20} {cnt:>4}  pfx={dec['prefix']:<3} sfx={dec['suffix']}")
        print(f"  Sections: {dict(e_det_section[det].most_common(5))}")

    # What about 'a' + DET?
    print(f"\n  {'='*68}")
    print(f"  ROOT 'a' + DETERMINATIVE COMBINATIONS")
    print(f"  {'='*68}")

    a_det_forms = defaultdict(Counter)
    a_det_section = defaultdict(Counter)
    for w in all_words:
        dec = full_decompose(w['word'])
        if dec['root'] == 'a' and dec['determinative']:
            det = dec['determinative']
            a_det_forms[det][w['word']] += 1
            a_det_section[det][w['section']] += 1

    for det in ['k','t','f','p']:
        if det not in a_det_forms: continue
        total = sum(a_det_forms[det].values())
        print(f"\n  a + {det}-determinative ({total} tokens):")
        for word, cnt in a_det_forms[det].most_common(8):
            dec = full_decompose(word)
            print(f"    {word:<20} {cnt:>4}  pfx={dec['prefix']:<3} sfx={dec['suffix']}")
        print(f"  Sections: {dict(a_det_section[det].most_common(5))}")


# ══════════════════════════════════════════════════════════════════
# 24b: COMPOUND ROOT RESOLUTION
# ══════════════════════════════════════════════════════════════════

def run_compound_resolution(all_words):
    print("\n" + "="*76)
    print("PHASE 24b: COMPOUND ROOT RESOLUTION")
    print("="*76)

    # Hypothesis: lch = l + ch, ed = e + d, che = ch + e
    compounds = {
        'lch':  ('l', 'ch', "remedy+do/make = 'remedy-making'?"),
        'ed':   ('e', 'd',  "this/that+matter = 'this matter'?"),
        'che':  ('ch', 'e', "do/make+this = 'make this'?"),
        'sh':   ('s', 'h',  "VERB+happen = verbal prefix + root?"),
        'ched': ('ch', 'ed',"do/make+this-matter = compound?"),
        'chod': ('cho', 'd',"substance+matter?"),
        'ho':   ('h', 'o',  "happen+DEF article? or Coptic ho=face?"),
        'alch': ('al', 'ch',"stone+do/make?"),
    }

    # Get distributional profiles for each
    compound_profiles = {}
    component_profiles = {}

    for w in all_words:
        dec = full_decompose(w['word'])
        root = dec['root']
        if root in compounds or root in CONFIRMED_VOCAB:
            if root not in compound_profiles:
                compound_profiles[root] = {
                    'count': 0, 'sections': Counter(),
                    'dets': Counter(), 'prefixes': Counter(),
                    'suffixes': Counter(), 'forms': Counter()
                }
            p = compound_profiles[root]
            p['count'] += 1
            p['sections'][w['section']] += 1
            if dec['determinative']:
                p['dets'][dec['determinative']] += 1
            if dec['prefix']:
                p['prefixes'][dec['prefix']] += 1
            if dec['suffix']:
                p['suffixes'][dec['suffix']] += 1
            p['forms'][w['word']] += 1

    for compound, (comp1, comp2, hypothesis) in compounds.items():
        cp = compound_profiles.get(compound)
        c1 = compound_profiles.get(comp1)
        c2 = compound_profiles.get(comp2)

        if not cp or cp['count'] < 5:
            print(f"\n  '{compound}' — too few tokens ({cp['count'] if cp else 0}), skipping")
            continue

        print(f"\n  {'─'*68}")
        print(f"  '{compound}' (n={cp['count']}) = '{comp1}' + '{comp2}'?")
        print(f"  Hypothesis: {hypothesis}")
        print(f"  {'─'*68}")

        # Compare section distributions
        print(f"  Section distribution:")
        all_sections = set()
        for prof in [cp, c1, c2]:
            if prof:
                all_sections.update(prof['sections'].keys())

        print(f"  {'Section':<12} {compound:>8} {comp1:>8} {comp2:>8}")
        for sect in sorted(all_sections):
            cp_pct = cp['sections'].get(sect,0) / cp['count'] * 100
            c1_pct = c1['sections'].get(sect,0) / c1['count'] * 100 if c1 and c1['count'] else 0
            c2_pct = c2['sections'].get(sect,0) / c2['count'] * 100 if c2 and c2['count'] else 0
            print(f"    {sect:<12} {cp_pct:>7.1f}% {c1_pct:>7.1f}% {c2_pct:>7.1f}%")

        # Determinative comparison
        print(f"  Determinatives:")
        for det in 'tkfp':
            cp_pct = cp['dets'].get(det,0) / cp['count'] * 100
            c1_pct = c1['dets'].get(det,0) / c1['count'] * 100 if c1 and c1['count'] else 0
            c2_pct = c2['dets'].get(det,0) / c2['count'] * 100 if c2 and c2['count'] else 0
            print(f"    {det}: {cp_pct:>6.1f}% {c1_pct:>6.1f}% {c2_pct:>6.1f}%")

        # Top forms
        print(f"  Top word forms with root '{compound}':")
        for form, cnt in cp['forms'].most_common(5):
            print(f"    {form:<25} {cnt:>4}")

        # Verdict
        # Simple test: if compound's distribution is closer to one component
        # than the other, it's likely dominated by that component
        if c1 and c2 and c1['count'] > 10 and c2['count'] > 10:
            diff1 = sum(abs(cp['sections'].get(s,0)/cp['count'] - c1['sections'].get(s,0)/c1['count'])
                       for s in all_sections)
            diff2 = sum(abs(cp['sections'].get(s,0)/cp['count'] - c2['sections'].get(s,0)/c2['count'])
                       for s in all_sections)
            closer = comp1 if diff1 < diff2 else comp2
            print(f"  VERDICT: Distribution closer to '{closer}' (diff1={diff1:.2f}, diff2={diff2:.2f})")


# ══════════════════════════════════════════════════════════════════
# 24c: DAIIN CONTEXT ANALYSIS
# ══════════════════════════════════════════════════════════════════

def run_daiin_analysis(all_words):
    print("\n" + "="*76)
    print("PHASE 24c: DAIIN CONTEXT ANALYSIS (most frequent word: 1,049x)")
    print("="*76)

    # Find all daiin occurrences and their neighbors
    # Build sequence per locus
    locus_sequences = defaultdict(list)
    for w in all_words:
        locus_sequences[w['locus']].append(w)

    daiin_contexts = []
    for locus, words in locus_sequences.items():
        for i, w in enumerate(words):
            if w['word'] == 'daiin':
                left = [words[j]['word'] for j in range(max(0,i-3), i)]
                right = [words[j]['word'] for j in range(i+1, min(len(words),i+4))]
                daiin_contexts.append({
                    'locus': locus,
                    'section': w['section'],
                    'left': left,
                    'right': right,
                })

    print(f"\n  Total 'daiin' occurrences: {len(daiin_contexts)}")

    # Section distribution
    section_counts = Counter(c['section'] for c in daiin_contexts)
    print(f"\n  Section distribution:")
    for sect, cnt in section_counts.most_common():
        pct = cnt / len(daiin_contexts) * 100
        print(f"    {sect:<12} {cnt:>5} ({pct:>5.1f}%)")

    # Left context — what PRECEDES daiin?
    left_words = Counter()
    left_roots = Counter()
    for c in daiin_contexts:
        if c['left']:
            left_words[c['left'][-1]] += 1
            dec = full_decompose(c['left'][-1])
            left_roots[dec['root']] += 1

    print(f"\n  Words immediately BEFORE 'daiin' (top 15):")
    for word, cnt in left_words.most_common(15):
        dec = full_decompose(word)
        meaning = CONFIRMED_VOCAB.get(dec['root'], f"?{dec['root']}?")
        print(f"    {word:<20} {cnt:>4}  root={dec['root']}, meaning={meaning}")

    # Right context — what FOLLOWS daiin?
    right_words = Counter()
    right_roots = Counter()
    for c in daiin_contexts:
        if c['right']:
            right_words[c['right'][0]] += 1
            dec = full_decompose(c['right'][0])
            right_roots[dec['root']] += 1

    print(f"\n  Words immediately AFTER 'daiin' (top 15):")
    for word, cnt in right_words.most_common(15):
        dec = full_decompose(word)
        meaning = CONFIRMED_VOCAB.get(dec['root'], f"?{dec['root']}?")
        print(f"    {word:<20} {cnt:>4}  root={dec['root']}, meaning={meaning}")

    # Left root summary
    print(f"\n  Root distribution BEFORE daiin:")
    for root, cnt in left_roots.most_common(10):
        meaning = CONFIRMED_VOCAB.get(root, f"?{root}?")
        print(f"    {root:<10} {cnt:>4}  ({meaning})")

    # Right root summary
    print(f"\n  Root distribution AFTER daiin:")
    for root, cnt in right_roots.most_common(10):
        meaning = CONFIRMED_VOCAB.get(root, f"?{root}?")
        print(f"    {root:<10} {cnt:>4}  ({meaning})")

    # AIIN analysis — compare with daiin
    aiin_contexts = []
    for locus, words in locus_sequences.items():
        for i, w in enumerate(words):
            if w['word'] == 'aiin':
                left = [words[j]['word'] for j in range(max(0,i-3), i)]
                right = [words[j]['word'] for j in range(i+1, min(len(words),i+4))]
                aiin_contexts.append({
                    'locus': locus,
                    'section': w['section'],
                    'left': left,
                    'right': right,
                })

    print(f"\n  Total 'aiin' occurrences: {len(aiin_contexts)}")
    aiin_section = Counter(c['section'] for c in aiin_contexts)
    print(f"  Section: {dict(aiin_section.most_common())}")

    aiin_left = Counter()
    for c in aiin_contexts:
        if c['left']:
            aiin_left[c['left'][-1]] += 1

    print(f"\n  Words immediately BEFORE 'aiin' (top 10):")
    for word, cnt in aiin_left.most_common(10):
        dec = full_decompose(word)
        meaning = CONFIRMED_VOCAB.get(dec['root'], f"?{dec['root']}?")
        print(f"    {word:<20} {cnt:>4}  root={dec['root']}, meaning={meaning}")


# ══════════════════════════════════════════════════════════════════
# 24d: CONNECTED PROSE TRANSLATION (f78r)
# ══════════════════════════════════════════════════════════════════

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

def smart_gloss(word):
    """Produce a more readable gloss using classifier semantics."""
    dec = full_decompose(word)
    root = dec['root']
    pfx = dec['prefix']
    sfx = dec['suffix']
    det = dec['determinative']

    parts = []

    # Prefix
    if pfx:
        parts.append(PREFIX_MEANING.get(pfx, pfx))

    # For demonstrative + classifier: merge into one concept
    if root == 'e' and det:
        # e + k = "this bodily [thing]"
        # e + t = "this celestial [influence]"
        det_word = DET_MEANING.get(det, det)
        parts.append(f"this-{det_word}")
    elif root == 'a' and det:
        det_word = DET_MEANING.get(det, det)
        parts.append(f"{det_word}-noble")
    elif root in CONFIRMED_VOCAB:
        if det:
            parts.append(f"[{DET_MEANING.get(det, det)}]")
        parts.append(CONFIRMED_VOCAB[root])
    else:
        if det:
            parts.append(f"[{DET_MEANING.get(det, det)}]")
        parts.append(f"?{root}?")

    # Suffix
    if sfx:
        parts.append(SUFFIX_MEANING.get(sfx, sfx))

    return " ".join(parts)


def run_connected_translation():
    print("\n" + "="*76)
    print("PHASE 24d: CONNECTED PROSE TRANSLATION — f78r (BIO)")
    print("="*76)

    print("\n  Using classifier-merged glossing (e+k = 'this bodily [thing]', etc.)")
    print("  Medieval medical context: nymph figures describe bodily conditions")
    print("  under astrological influences\n")

    fpath = Path("folios/f78r.txt")
    lines = fpath.read_text(encoding="utf-8").splitlines()

    for line in lines:
        line = line.strip()
        if line.startswith("#") or not line: continue
        lm = re.match(r'<([^>]+)>\s*(.*)', line)
        if not lm: continue
        locus = lm.group(1)
        text = lm.group(2)

        # Clean
        text = re.sub(r'<![\d:]+>','',text)
        text = re.sub(r'<![^>]*>','',text)
        text = re.sub(r'<%>|<\$>|<->|<\.>',' ',text)
        text = re.sub(r'<[^>]*>','',text)
        text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
        text = re.sub(r'\{([^}]+)\}', r'\1', text)
        text = re.sub(r'@\d+;?','',text)

        tokens = re.split(r'[.\s,]+', text)
        glosses = []
        n_known = 0
        n_total = 0
        for tok in tokens:
            tok = tok.strip().replace("'","")
            if not tok or '?' in tok: continue
            if not re.match(r'^[a-z]+$', tok) or len(tok) < 2: continue
            g = smart_gloss(tok)
            dec = full_decompose(tok)
            n_total += 1
            if dec['root'] in CONFIRMED_VOCAB:
                n_known += 1
            glosses.append(g)

        if not glosses: continue
        pct = n_known / n_total * 100 if n_total else 0

        print(f"  {locus} [{n_known}/{n_total}={pct:.0f}%]")
        # Show VOY
        voy_toks = []
        for tok in tokens:
            tok = tok.strip().replace("'","")
            if not tok or '?' in tok: continue
            if not re.match(r'^[a-z]+$', tok) or len(tok) < 2: continue
            voy_toks.append(tok)
        print(f"    VOY: {' '.join(voy_toks)}")
        print(f"    ENG: {' | '.join(glosses)}")
        print()

    # Also try f76r lines 12-17 (near the 100% line)
    print(f"\n  {'='*68}")
    print(f"  f76r lines 12-17 (around the 100%-translated line)")
    print(f"  {'='*68}\n")

    fpath = Path("folios/f76r.txt")
    lines = fpath.read_text(encoding="utf-8").splitlines()
    target_lines = []
    for line in lines:
        line = line.strip()
        lm = re.match(r'<(f76r\.\d+)', line)
        if lm:
            line_num_match = re.search(r'\.(\d+)', lm.group(1))
            if line_num_match:
                ln = int(line_num_match.group(1))
                if 11 <= ln <= 18:
                    target_lines.append(line)

    for line in target_lines:
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
        glosses = []
        n_known = 0; n_total = 0
        voy_toks = []
        for tok in tokens:
            tok = tok.strip().replace("'","")
            if not tok or '?' in tok: continue
            if not re.match(r'^[a-z]+$', tok) or len(tok) < 2: continue
            g = smart_gloss(tok)
            dec = full_decompose(tok)
            n_total += 1
            if dec['root'] in CONFIRMED_VOCAB: n_known += 1
            glosses.append(g)
            voy_toks.append(tok)

        if not glosses: continue
        pct = n_known / n_total * 100 if n_total else 0
        print(f"  {locus} [{n_known}/{n_total}={pct:.0f}%]")
        print(f"    VOY: {' '.join(voy_toks)}")
        print(f"    ENG: {' | '.join(glosses)}")
        print()


# ══════════════════════════════════════════════════════════════════
# 24e: PREDICTIVE MODEL — WHAT SHOULD A BIO PARAGRAPH SAY?
# ══════════════════════════════════════════════════════════════════

def run_predictive_model(all_words):
    print("\n" + "="*76)
    print("PHASE 24e: PREDICTIVE MODEL — BIO PARAGRAPH CONTENT EXPECTATIONS")
    print("="*76)

    print("""
  Medieval astrological-medical texts (e.g., Picatrix, Albumasar) describe:
  - Which celestial body RULES (ar/or) each body part
  - What BEFALLS (h/he) the body under each influence
  - What SUBSTANCE (cho/l) or PREPARATION (ch-ol) treats conditions
  - Which GREAT ONES (a/ar) influence the outcome

  Bio sections (nymph figures in tubs/channels) should describe:
  - Bodily conditions under astrological influence
  - Water (am) treatments and preparations (ch-ol)
  - References to rulers/planets (ar/or) as governing forces

  TESTING: Do our translations match this template?
""")

    # Count co-occurrence patterns in bio sections
    bio_words = [w for w in all_words if w['section'] == 'bio']
    herbal_words = [w for w in all_words if w['section'].startswith('herbal')]

    for label, words in [("BIO", bio_words), ("HERBAL", herbal_words)]:
        # Build pairs within same locus
        locus_seqs = defaultdict(list)
        for w in words:
            locus_seqs[w['locus']].append(w['word'])

        root_pairs = Counter()
        det_root_pairs = Counter()
        for locus, seq in locus_seqs.items():
            for i in range(len(seq)-1):
                dec1 = full_decompose(seq[i])
                dec2 = full_decompose(seq[i+1])
                r1 = dec1['root']
                r2 = dec2['root']
                if r1 in CONFIRMED_VOCAB and r2 in CONFIRMED_VOCAB:
                    m1 = CONFIRMED_VOCAB[r1]
                    m2 = CONFIRMED_VOCAB[r2]
                    root_pairs[(m1, m2)] += 1
                if dec1['determinative'] and r2 in CONFIRMED_VOCAB:
                    d1 = DET_MEANING.get(dec1['determinative'], dec1['determinative'])
                    m2 = CONFIRMED_VOCAB[r2]
                    det_root_pairs[(d1, m2)] += 1

        print(f"\n  {label}: Top meaning-pair bigrams (known-root → known-root):")
        for (m1, m2), cnt in root_pairs.most_common(20):
            print(f"    {m1:<18} → {m2:<18} {cnt:>4}")

        print(f"\n  {label}: Top classifier→meaning bigrams:")
        for (d1, m2), cnt in det_root_pairs.most_common(15):
            print(f"    [{d1}] → {m2:<18} {cnt:>4}")

    # Unique to bio vs herbal
    bio_pair_set = set()
    herbal_pair_set = set()
    for label, words in [("BIO", bio_words), ("HERBAL", herbal_words)]:
        locus_seqs = defaultdict(list)
        for w in words:
            locus_seqs[w['locus']].append(w['word'])
        for locus, seq in locus_seqs.items():
            for i in range(len(seq)-1):
                dec1 = full_decompose(seq[i])
                dec2 = full_decompose(seq[i+1])
                r1 = CONFIRMED_VOCAB.get(dec1['root'],'')
                r2 = CONFIRMED_VOCAB.get(dec2['root'],'')
                if r1 and r2:
                    pair = f"{r1} -> {r2}"
                    if label == "BIO":
                        bio_pair_set.add(pair)
                    else:
                        herbal_pair_set.add(pair)

    bio_only = bio_pair_set - herbal_pair_set
    herbal_only = herbal_pair_set - bio_pair_set

    print(f"\n  Meaning pairs UNIQUE to BIO ({len(bio_only)}):")
    for p in sorted(bio_only)[:15]:
        print(f"    {p}")

    print(f"\n  Meaning pairs UNIQUE to HERBAL ({len(herbal_only)}):")
    for p in sorted(herbal_only)[:15]:
        print(f"    {p}")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("PHASE 24: CLASSIFIER SEMANTICS & COMPOUND ROOT RESOLUTION")
    print("="*76)

    all_words = extract_all_words()
    print(f"Loaded {len(all_words)} word tokens")

    run_classifier_semantics(all_words)
    run_compound_resolution(all_words)
    run_daiin_analysis(all_words)
    run_connected_translation()
    run_predictive_model(all_words)

    Path("results").mkdir(exist_ok=True)
    Path("results/phase24_results.json").write_text(
        json.dumps({"phase": 24}, indent=2), encoding="utf-8"
    )
    print(f"\n  Results saved to results/phase24_results.json")


if __name__ == "__main__":
    main()
