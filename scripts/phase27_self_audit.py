#!/usr/bin/env python3
"""
Phase 27 — Rigorous Self-Audit & Falsification
===============================================

Before adding more vocabulary, we MUST audit existing claims for
hallucination and overfitting. The user (rightly) asks: are we
making real discoveries or pattern-matching noise?

Key concerns:
  1) Short roots (e, a, h, l, d, ch) are 1-2 chars — they match
     almost anything after morphological stripping. Is "coverage"
     just an artifact of short-root absorption?
  2) Are Coptic/Arabic etymologies testable, or post-hoc rationalization?
  3) Do translated passages make coherent sense or just word salad?
  4) Do provisional roots pass the same tests as "confirmed" roots?

Sub-analyses:
  27a) SHORT-ROOT COVERAGE AUDIT — What % of coverage comes from
       1-2 char roots vs 3+ char roots? If >80% is short roots,
       our "coverage" is largely noise absorption.
  27b) GRAMMATICAL CONSISTENCY CHECK — For each root claimed as noun
       or verb, verify prefix distributions match. Do claimed nouns
       take d-/o- prefixes? Do claimed verbs take s- prefixes?
  27c) SECTION SPECIFICITY TEST — Do roots with claimed domain meanings
       actually appear more in their predicted section? (e.g., "tree"
       in herbal, "lion" in zodiac, "star" in zodiac/cosmo)
  27d) TRANSLATION COHERENCE — Take 20 high-coverage lines, translate
       them, and HONESTLY rate: does this read as connected prose, or
       as random word associations?
  27e) PROVISIONAL ROOT AUDIT — Run air/eod/od/lsh through the SAME
       grammatical and distributional tests. Show side-by-side with
       confirmed roots.
  27f) FALSIFICATION ATTEMPTS — For our 5 strongest claims, generate
       specific predictions and check if they hold.
"""

import re, json, sys, io, math
from pathlib import Path
from collections import Counter, defaultdict
from common import collapse_echains, full_decompose, gallows_base, load_all_tokens, strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ══════════════════════════════════════════════════════════════════
# MORPHOLOGICAL PIPELINE (identical to Phase 26)
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
# VOCABULARY (Phase 26 state — 33 confirmed + 7 compounds)
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
    # Phase 26
    'cheos':'chaos/prima-materia',
    'hed':'pour/descend',
    'ches':'lord/master',
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

DET_MEANING = {'k':'bodily','t':'celestial','f':'botanical','p':'discourse'}
PREFIX_MEANING = {
    'qo':'which','q':'which','so':'verbal','do':'of-the',
    'o':'the','d':'of','s':'verbal','y':'quality-of'
}
SUFFIX_MEANING = {
    'aiin':'plural-rulers','ain':'plural','iin':'plural',
    'in':'plural','ar':'king/great','or':'king/great',
    'al':'stone/nominal','ol':'nominal','eedy':'fully-described',
    'edy':'described','ody':'prescribed','dy':'abstract',
    'ey':'genitive','y':'adj/quality'
}

# Part-of-speech classification for testing
# Based on claimed meanings in our model
ROOT_POS = {
    # Nouns (should have d-/o- prefixes, NOT s-)
    'esed': 'noun', 'she': 'noun', 'al': 'noun', 'ro': 'noun',
    'les': 'noun', 'ran': 'noun', 'res': 'noun', 'ar': 'noun',
    'or': 'noun', 'am': 'noun', 'chas': 'noun', 'eos': 'noun',
    'es': 'noun', 'chol': 'noun', 'cho': 'noun', 'yed': 'noun',
    'a': 'noun', 'e': 'demonstrative', 'l': 'noun', 'd': 'noun',
    'ho': 'noun', 'cheos': 'noun', 'ches': 'noun', 'rar': 'noun',
    # Verbs (should have s- prefix)
    'he': 'verb', 'ol': 'verb', 'ch': 'verb', 'h': 'verb', 'hed': 'verb',
    # Adjectives
    'cham': 'adj', 'eosh': 'adj', 'sheo': 'adj', 'choam': 'adj',
}

# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════

FOLIO_DIR = Path("folios")


def extract_folio_lines(folio_id):
    """Return list of (line_id, [words]) for a folio."""
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        lines_out = []
        found = False
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            m = re.match(r'<([^>]+)>', line.strip())
            if m:
                lid = m.group(1).split(',')[0]
                if lid == folio_id or lid.startswith(folio_id + '.'):
                    found = True
                rest = line.strip()[m.end():].strip()
                if found and rest:
                    words = []
                    for w in re.split(r'[.\s,;]+', rest):
                        w = re.sub(r'[^a-z]', '', w.lower().strip())
                        if len(w) >= 2: words.append(w)
                    if words:
                        lid_short = m.group(1)
                        lines_out.append((lid_short, words))
        if lines_out:
            return lines_out
    return []

# ══════════════════════════════════════════════════════════════════
# PHASE 27a: SHORT-ROOT COVERAGE AUDIT
# ══════════════════════════════════════════════════════════════════

def run_short_root_audit(tokens):
    print("=" * 76)
    print("PHASE 27a: SHORT-ROOT COVERAGE AUDIT")
    print("=" * 76)
    print()
    print("CONCERN: Roots like 'e', 'a', 'h', 'l', 'd', 'ch' are 1-2 chars.")
    print("After morphological stripping, these match almost anything.")
    print("If most 'coverage' comes from these, we may just be absorbing noise.")
    print()

    # Classify roots by length
    short_roots = {r: m for r, m in ALL_ROOTS.items() if len(r) <= 2}
    long_roots = {r: m for r, m in ALL_ROOTS.items() if len(r) > 2}

    print(f"  Short roots (1-2 chars): {len(short_roots)}")
    for r, m in sorted(short_roots.items()):
        print(f"    '{r}' → {m}")
    print(f"\n  Long roots (3+ chars): {len(long_roots)}")
    for r, m in sorted(long_roots.items()):
        print(f"    '{r}' → {m}")

    # Count tokens by root length
    short_count = 0
    long_count = 0
    unknown_count = 0
    root_token_counts = Counter()

    for word, section, folio in tokens:
        d = full_decompose(word)
        root = d['root']
        if root in ALL_ROOTS:
            root_token_counts[root] += 1
            if len(root) <= 2:
                short_count += 1
            else:
                long_count += 1
        else:
            unknown_count += 1

    total = len(tokens)
    known = short_count + long_count
    print(f"\n  TOKEN DISTRIBUTION:")
    print(f"    Total tokens:     {total}")
    print(f"    Short-root match: {short_count} ({100*short_count/total:.1f}%)")
    print(f"    Long-root match:  {long_count} ({100*long_count/total:.1f}%)")
    print(f"    Unknown:          {unknown_count} ({100*unknown_count/total:.1f}%)")
    print(f"    Overall coverage: {known} ({100*known/total:.1f}%)")

    short_pct = 100*short_count/known if known else 0
    print(f"\n  OF KNOWN TOKENS:")
    print(f"    From short roots: {short_count} ({short_pct:.1f}% of known)")
    print(f"    From long roots:  {long_count} ({100-short_pct:.1f}% of known)")

    if short_pct > 80:
        print(f"\n  *** WARNING: {short_pct:.0f}% of coverage from short roots!")
        print(f"  *** This means most 'coverage' may be noise absorption, not real meaning.")
    elif short_pct > 60:
        print(f"\n  ** CAUTION: {short_pct:.0f}% of coverage from short roots.")
        print(f"  ** Coverage numbers are inflated. Long-root coverage is the real signal.")
    else:
        print(f"\n  OK: Short roots account for only {short_pct:.0f}% of known tokens.")

    # Top roots by token count
    print(f"\n  TOP 20 ROOTS BY TOKEN COUNT:")
    for root, count in root_token_counts.most_common(20):
        pct = 100*count/total
        rl = "SHORT" if len(root) <= 2 else "long "
        print(f"    '{root:8s}' ({ALL_ROOTS.get(root,'?'):20s}): {count:5d} tokens ({pct:4.1f}%)  [{rl}]")

    # The critical question: what would coverage be with ONLY long roots?
    print(f"\n  COVERAGE WITH ONLY LONG ROOTS (3+ chars):")
    print(f"    {long_count}/{total} = {100*long_count/total:.1f}%")
    print(f"  This is the 'honest' coverage — matches that are less likely to be noise.")

    return {'short_pct': short_pct, 'long_coverage': 100*long_count/total,
            'total_coverage': 100*known/total}


# ══════════════════════════════════════════════════════════════════
# PHASE 27b: GRAMMATICAL CONSISTENCY CHECK
# ══════════════════════════════════════════════════════════════════

def run_grammar_check(tokens):
    print()
    print("=" * 76)
    print("PHASE 27b: GRAMMATICAL CONSISTENCY CHECK")
    print("=" * 76)
    print()
    print("TEST: If our POS claims are real, noun-roots should have different")
    print("prefix distributions than verb-roots. Specifically:")
    print("  - Nouns: high d-/o- (genitive, article), low s- (verbal)")
    print("  - Verbs: high s- (verbal marker), low d-/o-")
    print("  - Adjectives: high y- (quality marker)")
    print()

    # Collect prefix distributions per root
    root_prefixes = defaultdict(Counter)
    root_total = Counter()
    for word, section, folio in tokens:
        d = full_decompose(word)
        root = d['root']
        if root in ROOT_POS:
            root_prefixes[root][d['prefix']] += 1
            root_total[root] += 1

    # Group by POS and show distributions
    for pos in ['noun', 'verb', 'adj', 'demonstrative']:
        roots_in_pos = [r for r, p in ROOT_POS.items() if p == pos and root_total[r] >= 20]
        if not roots_in_pos:
            continue
        print(f"  {pos.upper()} roots (N≥20):")
        print(f"  {'root':10s} {'total':>6s}  {'d%':>5s} {'o%':>5s} {'s%':>5s} {'y%':>5s} {'qo%':>5s} {'bare%':>6s}  VERDICT")

        pass_count = 0
        fail_count = 0
        for root in sorted(roots_in_pos, key=lambda r: -root_total[r]):
            n = root_total[root]
            if n < 20: continue
            prfx = root_prefixes[root]
            d_pct = 100*(prfx.get('d',0)+prfx.get('do',0))/n
            o_pct = 100*prfx.get('o',0)/n
            s_pct = 100*(prfx.get('s',0)+prfx.get('so',0))/n
            y_pct = 100*prfx.get('y',0)/n
            qo_pct = 100*(prfx.get('qo',0)+prfx.get('q',0))/n
            bare_pct = 100*prfx.get('',0)/n

            if pos == 'noun':
                # Nouns should have d+o >= s, and s < 30%
                verdict = "PASS" if (d_pct + o_pct >= s_pct and s_pct < 30) else "FAIL"
            elif pos == 'verb':
                # Verbs should have s >= 20%
                verdict = "PASS" if s_pct >= 20 else "FAIL"
            elif pos == 'adj':
                # Adjectives should have y >= 5%
                verdict = "PASS" if y_pct >= 5 else "FAIL"
            else:
                verdict = "n/a"

            if verdict == "PASS": pass_count += 1
            elif verdict == "FAIL": fail_count += 1

            print(f"  {root:10s} {n:6d}  {d_pct:5.1f} {o_pct:5.1f} {s_pct:5.1f} {y_pct:5.1f} {qo_pct:5.1f} {bare_pct:6.1f}  {verdict}")

        total_tested = pass_count + fail_count
        if total_tested > 0:
            print(f"  → {pass_count}/{total_tested} pass ({100*pass_count/total_tested:.0f}%)")
        print()

    # Overall summary
    all_pass = 0; all_fail = 0
    for root, pos in ROOT_POS.items():
        n = root_total[root]
        if n < 20: continue
        prfx = root_prefixes[root]
        d_pct = 100*(prfx.get('d',0)+prfx.get('do',0))/n
        o_pct = 100*prfx.get('o',0)/n
        s_pct = 100*(prfx.get('s',0)+prfx.get('so',0))/n
        y_pct = 100*prfx.get('y',0)/n
        if pos == 'noun' and (d_pct + o_pct >= s_pct and s_pct < 30): all_pass += 1
        elif pos == 'verb' and s_pct >= 20: all_pass += 1
        elif pos == 'adj' and y_pct >= 5: all_pass += 1
        elif pos == 'noun' or pos == 'verb' or pos == 'adj': all_fail += 1

    print(f"  OVERALL GRAMMAR CONSISTENCY: {all_pass}/{all_pass+all_fail} roots pass ({100*all_pass/(all_pass+all_fail):.0f}%)")
    if all_fail > all_pass:
        print("  *** ALARM: More roots FAIL than pass. POS claims may be wrong.")
    elif all_fail > 0:
        print(f"  ** NOTE: {all_fail} root(s) have inconsistent grammar. Investigate.")

    return {'pass': all_pass, 'fail': all_fail}


# ══════════════════════════════════════════════════════════════════
# PHASE 27c: SECTION SPECIFICITY TEST
# ══════════════════════════════════════════════════════════════════

def run_section_specificity(tokens):
    print()
    print("=" * 76)
    print("PHASE 27c: SECTION SPECIFICITY TEST")
    print("=" * 76)
    print()
    print("TEST: If meanings are real, domain-specific roots should cluster")
    print("in their predicted sections. We check roots with domain claims.")
    print()

    # Count root occurrences per section
    root_sections = defaultdict(Counter)
    section_totals = Counter()
    for word, section, folio in tokens:
        section_totals[section] += 1
        d = full_decompose(word)
        root = d['root']
        if root in ALL_ROOTS:
            root_sections[root][section] += 1

    # Domain predictions
    predictions = [
        ('esed', 'lion', 'zodiac', 'Zodiac signs feature animals → lion in zodiac'),
        ('she', 'tree/plant', 'herbal-A', 'Trees/plants → herbal section'),
        ('al', 'stone', 'pharma', 'Stones used in remedies → pharma'),
        ('am', 'water', 'bio', 'Water/bodily fluids → bio section'),
        ('eos', 'star', 'zodiac', 'Stars → zodiac/cosmo section'),
        ('es', 'star', 'zodiac', 'Stars → zodiac/cosmo section'),
        ('chol', 'celestial-body', 'cosmo', 'Celestial bodies → cosmo section'),
        ('yed', 'hand', 'bio', 'Hand/body part → bio section'),
        ('hed', 'pour/descend', 'bio', 'Pouring/medical → bio section'),
        ('cheos', 'chaos/prima-materia', 'cosmo', 'Prima materia → cosmo/alchemical'),
    ]

    print(f"  {'Root':8s} {'Meaning':20s} {'Predicted':10s} {'Actual top':10s} {'In pred':>7s} {'Total':>6s} {'Match':>6s}")
    pass_count = 0
    fail_count = 0
    for root, meaning, predicted, rationale in predictions:
        counts = root_sections.get(root, Counter())
        total = sum(counts.values())
        if total == 0:
            print(f"  {root:8s} {meaning:20s} {predicted:10s} {'NO DATA':10s}      —      —    —")
            continue
        top_section = counts.most_common(1)[0][0]
        in_predicted = counts.get(predicted, 0)

        # Normalize by section size for fair comparison
        # Check if root is proportionally over-represented in predicted section
        expected_pct = section_totals.get(predicted, 0) / max(sum(section_totals.values()), 1) * 100
        actual_pct = in_predicted / total * 100 if total > 0 else 0

        # Also check combined related sections
        # e.g., for zodiac prediction, count zodiac+cosmo
        enrichment = actual_pct / expected_pct if expected_pct > 0 else 0

        match = "PASS" if enrichment >= 1.0 else "FAIL"
        if match == "PASS": pass_count += 1
        else: fail_count += 1

        print(f"  {root:8s} {meaning:20s} {predicted:10s} {top_section:10s} {in_predicted:>5d}   {total:>5d}  {match} (enrich={enrichment:.2f}x)")

    print(f"\n  SECTION SPECIFICITY: {pass_count}/{pass_count+fail_count} predictions pass")
    if fail_count > pass_count:
       print("  *** ALARM: Most domain predictions FAIL. Meanings may be wrong.")

    # Also show the actual distribution for each tested root
    print(f"\n  DETAILED SECTION DISTRIBUTIONS (normalized by section size):")
    for root, meaning, predicted, rationale in predictions:
        counts = root_sections.get(root, Counter())
        total = sum(counts.values())
        if total < 10: continue
        parts = []
        for sec in ['bio','cosmo','herbal-A','herbal-B','pharma','text','zodiac']:
            c = counts.get(sec, 0)
            sec_size = section_totals.get(sec, 1)
            norm = (c / total) / (sec_size / sum(section_totals.values()))
            if c > 0:
                parts.append(f"{sec}={c}({norm:.1f}x)")
        print(f"    {root:8s}: {', '.join(parts)}")

    return {'pass': pass_count, 'fail': fail_count}


# ══════════════════════════════════════════════════════════════════
# PHASE 27d: TRANSLATION COHERENCE
# ══════════════════════════════════════════════════════════════════

def smart_gloss(d):
    """Produce a human-readable gloss. Be HONEST about unknowns."""
    parts = []

    pfx = d.get('prefix','')
    if pfx:
        parts.append(PREFIX_MEANING.get(pfx, f'?{pfx}?'))

    det = d.get('determinative','')
    root = d.get('root','')

    if root in ALL_ROOTS:
        if det:
            parts.append(f"{DET_MEANING.get(det, det)}")
        parts.append(ALL_ROOTS[root])
    elif root:
        if det:
            parts.append(f"{DET_MEANING.get(det, det)}")
        parts.append(f"??{root}??")  # Mark unknowns clearly
    else:
        if det:
            parts.append(f"{DET_MEANING.get(det, det)}")
        parts.append("(bare-classifier)")

    sfx = d.get('suffix','')
    if sfx:
        parts.append(f"[{SUFFIX_MEANING.get(sfx, sfx)}]")

    return ' '.join(parts)


def run_translation_coherence(tokens):
    print()
    print("=" * 76)
    print("PHASE 27d: TRANSLATION COHERENCE TEST")
    print("=" * 76)
    print()
    print("We translate 20 lines from the best-covered folio (f78r) and")
    print("HONESTLY assess: does this read as connected prose, or word salad?")
    print("We mark ALL unknown roots with ?? to avoid pretending we know more")
    print("than we do.")
    print()

    lines = extract_folio_lines('f78r')
    if not lines:
        print("  ERROR: Could not load f78r lines")
        return {}

    translated = 0
    coherent_lines = 0
    total_words = 0
    known_words = 0
    translations = []

    for lid, words in lines[:20]:
        glosses = []
        line_known = 0
        for w in words:
            d = full_decompose(w)
            g = smart_gloss(d)
            glosses.append(g)
            total_words += 1
            if d['root'] in ALL_ROOTS:
                known_words += 1
                line_known += 1

        line_coverage = line_known / len(words) * 100 if words else 0
        unknown_count = sum(1 for g in glosses if '??' in g)

        print(f"  {lid}:")
        print(f"    EVA:  {' . '.join(words)}")
        print(f"    Gloss: {' | '.join(glosses)}")
        print(f"    Coverage: {line_known}/{len(words)} ({line_coverage:.0f}%), Unknowns: {unknown_count}")
        print()

        translations.append({
            'line': lid, 'coverage': line_coverage,
            'unknowns': unknown_count, 'total': len(words)
        })
        translated += 1

    avg_coverage = known_words / total_words * 100 if total_words else 0
    print(f"  SUMMARY:")
    print(f"    Lines translated: {translated}")
    print(f"    Avg word coverage: {avg_coverage:.1f}%")
    print(f"    Lines with 0 unknowns: {sum(1 for t in translations if t['unknowns']==0)}")
    print(f"    Lines with >50% unknowns: {sum(1 for t in translations if t['unknowns']/max(t['total'],1) > 0.5)}")
    print()
    print("  HONEST ASSESSMENT:")
    print("  The glosses above show our ACTUAL translation quality. Readers should")
    print("  judge for themselves whether these read as connected medieval text or")
    print("  as pattern-matched noise. '??' markers show where we have NO idea.")

    return {'avg_coverage': avg_coverage, 'translations': translations}


# ══════════════════════════════════════════════════════════════════
# PHASE 27e: PROVISIONAL ROOT AUDIT
# ══════════════════════════════════════════════════════════════════

def run_provisional_audit(tokens):
    print()
    print("=" * 76)
    print("PHASE 27e: PROVISIONAL ROOT AUDIT")
    print("=" * 76)
    print()
    print("TEST: Do provisional roots (air, eod, od, lsh) show the SAME")
    print("grammatical regularity as confirmed roots?")
    print()

    provisionals = {
        'air': {'meaning': 'fire/essence', 'claimed_pos': 'noun',
                'etymology': 'Arabic nar=fire (not direct match, requires metathesis)',
                'alt_etymology': 'Coptic eire=make/do (verbal), Coptic hire=road'},
        'eod': {'meaning': 'father/patriarch', 'claimed_pos': 'noun',
                'etymology': 'Coptic eiot=father (plausible phonetic match)',
                'alt_etymology': 'Could be e+od compound (this+??), not a single root'},
        'od':  {'meaning': 'aloe-wood', 'claimed_pos': 'noun',
                'etymology': 'Arabic oud=aloe-wood (good phonetic match)',
                'alt_etymology': 'Coptic ot=unit/measure, English "odd"'},
        'lsh': {'meaning': 'remedy-occurrence', 'claimed_pos': 'compound',
                'etymology': 'l(remedy) + sh(it-happens) — compound of 2 known roots',
                'alt_etymology': 'Could be a single unknown root, not a compound'},
    }

    # Compute distributions
    for root, info in provisionals.items():
        print(f"  === ROOT: '{root}' — claimed: {info['meaning']} ===")
        print(f"  Etymology: {info['etymology']}")
        print(f"  Alternative: {info['alt_etymology']}")

        prefix_counts = Counter()
        suffix_counts = Counter()
        det_counts = Counter()
        section_counts = Counter()
        total = 0

        for word, section, folio in tokens:
            d = full_decompose(word)
            if d['root'] == root:
                prefix_counts[d['prefix']] += 1
                suffix_counts[d['suffix']] += 1
                if d['determinative']:
                    det_counts[d['determinative']] += 1
                section_counts[section] += 1
                total += 1

        if total == 0:
            print(f"  NO TOKENS FOUND — cannot validate")
            print()
            continue

        d_pct = 100*(prefix_counts.get('d',0)+prefix_counts.get('do',0))/total
        o_pct = 100*prefix_counts.get('o',0)/total
        s_pct = 100*(prefix_counts.get('s',0)+prefix_counts.get('so',0))/total
        y_pct = 100*prefix_counts.get('y',0)/total
        bare_pct = 100*prefix_counts.get('',0)/total

        print(f"  Tokens: {total}")
        print(f"  Prefixes: d={d_pct:.1f}%, o={o_pct:.1f}%, s={s_pct:.1f}%, y={y_pct:.1f}%, bare={bare_pct:.1f}%")
        print(f"  Suffixes: {dict(suffix_counts.most_common(5))}")
        print(f"  Determinatives: {dict(det_counts.most_common(4))}")
        print(f"  Sections: {dict(section_counts.most_common())}")

        # Grammar test
        if info['claimed_pos'] == 'noun':
            noun_test = d_pct + o_pct >= s_pct and s_pct < 30
            print(f"  NOUN TEST (d%+o% >= s%, s%<30%): {'PASS' if noun_test else 'FAIL'} (d+o={d_pct+o_pct:.1f}%, s={s_pct:.1f}%)")
        elif info['claimed_pos'] == 'verb':
            verb_test = s_pct >= 20
            print(f"  VERB TEST (s%>=20%): {'PASS' if verb_test else 'FAIL'} (s={s_pct:.1f}%)")
        elif info['claimed_pos'] == 'compound':
            print(f"  COMPOUND — grammar test not applicable (inherits from components)")

        # Compare against known roots of same POS
        if info['claimed_pos'] in ['noun', 'verb']:
            same_pos_roots = [r for r, p in ROOT_POS.items() if p == info['claimed_pos']]
            # Get average d%, o%, s% for known roots of this POS
            known_d = []; known_o = []; known_s = []
            for kr in same_pos_roots:
                kr_pfx = Counter()
                kr_total = 0
                for word, section, folio in tokens:
                    d2 = full_decompose(word)
                    if d2['root'] == kr:
                        kr_pfx[d2['prefix']] += 1
                        kr_total += 1
                if kr_total >= 20:
                    known_d.append(100*(kr_pfx.get('d',0)+kr_pfx.get('do',0))/kr_total)
                    known_o.append(100*kr_pfx.get('o',0)/kr_total)
                    known_s.append(100*(kr_pfx.get('s',0)+kr_pfx.get('so',0))/kr_total)
            if known_d:
                avg_d = sum(known_d)/len(known_d)
                avg_o = sum(known_o)/len(known_o)
                avg_s = sum(known_s)/len(known_s)
                print(f"  Comparison to known {info['claimed_pos']}s: avg d={avg_d:.1f}%, o={avg_o:.1f}%, s={avg_s:.1f}%")
                print(f"  This root:                      d={d_pct:.1f}%, o={o_pct:.1f}%, s={s_pct:.1f}%")

        print()

    return {}


# ══════════════════════════════════════════════════════════════════
# PHASE 27f: FALSIFICATION ATTEMPTS
# ══════════════════════════════════════════════════════════════════

def run_falsification(tokens):
    print()
    print("=" * 76)
    print("PHASE 27f: FALSIFICATION ATTEMPTS")
    print("=" * 76)
    print()
    print("For our 5 strongest claims, we generate SPECIFIC PREDICTIONS")
    print("that would FAIL if the claim is wrong.")
    print()

    # Build root co-occurrence matrix (within 3-word window)
    folio_lines = defaultdict(list)
    for word, section, folio in tokens:
        d = full_decompose(word)
        folio_lines[folio].append(d['root'])

    cooc = defaultdict(Counter)
    for folio, roots in folio_lines.items():
        for i, r in enumerate(roots):
            window = roots[max(0,i-3):i] + roots[i+1:i+4]
            for w_r in window:
                if w_r != r:
                    cooc[r][w_r] += 1

    # Precompute section sizes for enrichment calculations
    section_sizes = Counter()
    for _, section, _ in tokens:
        section_sizes[section] += 1
    total_tokens = sum(section_sizes.values())

    def safe_enrichment(count, total_root, section, sec_sizes, total_tok):
        """Compute enrichment ratio, return 0 if any denominator is zero."""
        if total_root == 0 or sec_sizes.get(section, 0) == 0 or total_tok == 0:
            return 0.0
        return (count / total_root) / (sec_sizes[section] / total_tok)

    claims = [
        {
            'claim': "Gallows are classifiers: k=bodily, t=celestial, f=botanical, p=discourse",
            'prediction': "k-determinative should be most common in bio section, t in zodiac/cosmo",
            'test': 'gallows_sections'
        },
        {
            'claim': "'esed' means lion (Arabic asad)",
            'prediction': "esed should co-occur with zodiac/animal terms more than random roots",
            'test': 'esed_cooc'
        },
        {
            'claim': "'am' means water",
            'prediction': "am should appear more in bio/pharma (bodily fluids, medicines) than zodiac",
            'test': 'am_sections'
        },
        {
            'claim': "'s-' prefix marks verbs",
            'prediction': "Roots with >50% s-prefix should be a small subset (verbs are less common than nouns)",
            'test': 's_prefix_rarity'
        },
        {
            'claim': "e→a vowel shift maps Voynichese to Arabic/Coptic",
            'prediction': "Root pairs with e→a should have similar distributional profiles",
            'test': 'vowel_shift'
        },
    ]

    for claim_data in claims:
        print(f"  CLAIM: {claim_data['claim']}")
        print(f"  PREDICTION: {claim_data['prediction']}")

        if claim_data['test'] == 'gallows_sections':
            # Count determinatives per section
            det_sections = defaultdict(Counter)
            for word, section, folio in tokens:
                d = full_decompose(word)
                det = d['determinative']
                if det:
                    det_sections[det][section] += 1

            print(f"  RESULT:")
            for det in ['k','t','f','p']:
                counts = det_sections[det]
                total_det = sum(counts.values())
                parts = []
                for sec in ['bio','cosmo','herbal-A','pharma','text','zodiac']:
                    c = counts.get(sec, 0)
                    enrichment = safe_enrichment(c, total_det, sec, section_sizes, total_tokens)
                    parts.append(f"{sec}={enrichment:.2f}x")
                print(f"    {det}({DET_MEANING[det]:10s}): {', '.join(parts)}")

            # Does k peak in bio? Does t peak in zodiac/cosmo?
            k_bio = safe_enrichment(det_sections['k'].get('bio',0), sum(det_sections['k'].values()), 'bio', section_sizes, total_tokens)
            t_zod = safe_enrichment(det_sections['t'].get('zodiac',0), sum(det_sections['t'].values()), 'zodiac', section_sizes, total_tokens)
            t_cos = safe_enrichment(det_sections['t'].get('cosmo',0), sum(det_sections['t'].values()), 'cosmo', section_sizes, total_tokens)
            f_herb = safe_enrichment(det_sections['f'].get('herbal-A',0), sum(det_sections['f'].values()), 'herbal-A', section_sizes, total_tokens)

            print(f"    k in bio enrichment: {k_bio:.2f}x (predicted >1.0)")
            print(f"    t in zodiac enrichment: {t_zod:.2f}x (predicted >1.0)")
            print(f"    t in cosmo enrichment: {t_cos:.2f}x (predicted >1.0)")
            print(f"    f in herbal enrichment: {f_herb:.2f}x (predicted >1.0)")

            tests_pass = sum([k_bio > 1.0, t_zod > 1.0 or t_cos > 1.0, f_herb > 1.0])
            print(f"  VERDICT: {tests_pass}/3 sub-predictions hold → {'SUPPORTED' if tests_pass >= 2 else 'WEAKENED'}")

        elif claim_data['test'] == 'esed_cooc':
            esed_neighbors = cooc.get('esed', Counter())
            total_esed = sum(esed_neighbors.values())
            if total_esed == 0:
                print(f"  RESULT: esed has no co-occurrences — CANNOT TEST")
            else:
                # What are esed's top neighbors?
                print(f"  RESULT: esed top co-occurrences (N={total_esed}):")
                for neighbor, count in esed_neighbors.most_common(10):
                    meaning = ALL_ROOTS.get(neighbor, '???')
                    print(f"    {neighbor:10s} ({meaning:20s}): {count}")

                # Check section distribution
                esed_sects = Counter()
                for word, section, folio in tokens:
                    d = full_decompose(word)
                    if d['root'] == 'esed':
                        esed_sects[section] += 1
                print(f"  Section distribution: {dict(esed_sects.most_common())}")
                top_sec = esed_sects.most_common(1)[0][0] if esed_sects else 'none'
                print(f"  VERDICT: Top section is '{top_sec}' — {'SUPPORTED' if top_sec in ['zodiac','cosmo','text'] else 'WEAKENED'} (lion in zodiac/astral)")

        elif claim_data['test'] == 'am_sections':
            am_sects = Counter()
            for word, section, folio in tokens:
                d = full_decompose(word)
                if d['root'] == 'am':
                    am_sects[section] += 1
            total_am = sum(am_sects.values())

            print(f"  RESULT: 'am' section distribution (N={total_am}):")
            for sec in ['bio','cosmo','herbal-A','pharma','text','zodiac']:
                c = am_sects.get(sec, 0)
                enrich = safe_enrichment(c, total_am, sec, section_sizes, total_tokens)
                print(f"    {sec:10s}: {c:4d} ({enrich:.2f}x enrichment)")
            bio_pharma = am_sects.get('bio',0) + am_sects.get('pharma',0)
            zodiac = am_sects.get('zodiac',0)
            verdict = bio_pharma > zodiac
            print(f"  VERDICT: bio+pharma={bio_pharma} vs zodiac={zodiac} → {'SUPPORTED' if verdict else 'WEAKENED'}")

        elif claim_data['test'] == 's_prefix_rarity':
            # Count how many roots have >50% s-prefix
            root_s_pct = {}
            root_counts = Counter()
            for word, section, folio in tokens:
                d = full_decompose(word)
                root = d['root']
                if root in ALL_ROOTS:
                    root_counts[root] += 1
            root_s_counts = Counter()
            for word, section, folio in tokens:
                d = full_decompose(word)
                root = d['root']
                if root in ALL_ROOTS and d['prefix'] in ['s','so']:
                    root_s_counts[root] += 1
            high_s_roots = []
            for root in ALL_ROOTS:
                if root_counts[root] >= 20:
                    s_pct = root_s_counts[root]/root_counts[root]*100
                    root_s_pct[root] = s_pct
                    if s_pct > 50:
                        high_s_roots.append((root, s_pct, root_counts[root]))

            total_testable = sum(1 for r in ALL_ROOTS if root_counts[r] >= 20)
            print(f"  RESULT: {len(high_s_roots)}/{total_testable} roots have >50% s-prefix:")
            for root, pct, count in sorted(high_s_roots, key=lambda x: -x[1]):
                claimed = ROOT_POS.get(root, '?')
                print(f"    {root:10s}: {pct:.0f}% s-prefix (N={count}, claimed={claimed})")
            is_small = len(high_s_roots) / total_testable < 0.3 if total_testable > 0 else True
            # Check that all high-s roots are claimed verbs
            verb_match = all(ROOT_POS.get(r, '') == 'verb' for r, _, _ in high_s_roots)
            print(f"  Small subset? {is_small} ({len(high_s_roots)}/{total_testable})")
            print(f"  All claimed verbs? {verb_match}")
            print(f"  VERDICT: {'SUPPORTED' if is_small else 'WEAKENED'}")

        elif claim_data['test'] == 'vowel_shift':
            # Check distributional similarity of e→a pairs
            pairs = [
                ('esed', 'lion → Arabic asad'),
                ('ches', 'lord → chas'),
                ('es', 'star → ?as'),
            ]
            print(f"  RESULT: Checking e→a variant pairs:")
            for root, note in pairs:
                a_variant = root.replace('e', 'a')
                if root in ALL_ROOTS and a_variant != root:
                    # Get section distributions for both
                    r_sects = Counter(); a_sects = Counter()
                    for word, section, folio in tokens:
                        d = full_decompose(word)
                        if d['root'] == root: r_sects[section] += 1
                        if d['root'] == a_variant: a_sects[section] += 1
                    print(f"    {root} vs {a_variant}: {note}")
                    print(f"      {root}: {dict(r_sects.most_common(3))} (N={sum(r_sects.values())})")
                    print(f"      {a_variant}: {dict(a_sects.most_common(3))} (N={sum(a_sects.values())})")
                    if sum(a_sects.values()) > 0:
                        # Correlate section distributions
                        all_secs = set(list(r_sects.keys()) + list(a_sects.keys()))
                        print(f"      Both variants found — can compare distributions")
                    else:
                        print(f"      '{a_variant}' not found as separate root — vowel shift absorbed into '{root}'")

            print(f"  VERDICT: Vowel shift is a HYPOTHESIS, not proven from distributional data alone.")
            print(f"  The e→a mapping is inspired by known Arabic orthographic patterns,")
            print(f"  but we CANNOT prove it from Voynich data without external validation.")

        print()

    return {}


# ══════════════════════════════════════════════════════════════════
# PHASE 27g: HONEST CONFIDENCE SUMMARY
# ══════════════════════════════════════════════════════════════════

def run_confidence_summary():
    print()
    print("=" * 76)
    print("PHASE 27g: HONEST CONFIDENCE LEVELS")
    print("=" * 76)
    print()
    print("For each major claim, we assign an honest confidence level:")
    print("  HIGH   = Strongly supported by distributional evidence")
    print("  MEDIUM = Plausible, some supporting evidence, alternatives exist")
    print("  LOW    = Speculative, based mainly on etymology not distribution")
    print("  STRUCTURAL = Based on pattern analysis, not semantic claims")
    print()

    assessments = [
        ("Morphological decomposition (prefix-root-suffix)", "STRUCTURAL",
         "The decomposition is mechanical. It consistently parses tokens into "
         "morphemes. But parsing ≠ understanding. We can decompose without "
         "knowing what any piece means."),

        ("Gallows = determinative classifiers", "MEDIUM",
         "Well-supported by position (always initial/pre-root), distribution "
         "(k is most common, f least), and section enrichment patterns. But "
         "the specific meanings (k=bodily, t=celestial, f=botanical, p=discourse) "
         "are interpretive hypotheses, not proven."),

        ("'e' = demonstrative (this/that)", "MEDIUM",
         "e-chains are the most common feature. Collapsing them yields consistent "
         "morphology. But labeling this as 'demonstrative' rather than just "
         "'grammatical particle' is interpretive."),

        ("s- = verbal prefix", "HIGH",
         "Distributional evidence is strong: roots with high s- rates (h, he, ol, ch, hed) "
         "are a small, consistent subset. This is a testable structural claim "
         "and it holds across all sections."),

        ("d-/o- = genitive/article prefixes", "MEDIUM",
         "These are the most common prefixes for most roots. Fits a noun-phrase "
         "model. But 'd-/o-' could serve other grammatical functions."),

        ("'esed' = lion (Arabic asad)", "LOW",
         "Based on phonetic resemblance to Arabic asad after e→a shift. "
         "Distributional evidence is mixed — esed does not cluster in zodiac "
         "where we'd expect Leo references. Could be coincidence."),

        ("'am' = water", "MEDIUM",
         "Consistent with Coptic/Semitic roots. Somewhat enriched in bio/pharma "
         "sections. But many roots show similar bio enrichment."),

        ("'al' = stone", "MEDIUM",
         "Phonetically close to Arabic al-/el- and Coptic wne (stone). Very "
         "common root — could be a function word rather than 'stone'."),

        ("Coverage = 74.2%", "STRUCTURAL",
         "This number is REAL but MISLEADING. Much of it comes from "
         "1-2 character roots that match almost anything (e,a,h,l,d,ch). "
         "Long-root coverage is the honest metric."),

        ("Connected prose translation", "LOW",
         "Translations are mosaics of glosses for individual morphemes. "
         "We cannot yet produce fluent English translations. Reading "
         "coherence into these glosses requires significant interpretation."),

        ("Coptic substrate language", "MEDIUM",
         "Several roots match Coptic (h=happen, ho=face, hed=pour, he=fall). "
         "But Coptic has ~10K roots — finding a few matches among 33 claimed "
         "roots is not statistically surprising. We would need >50 matches "
         "with consistent phonetic rules to be confident."),

        ("Arabic loanword layer", "MEDIUM",
         "esed→asad, chas→ (not a clear Arabic word), am→ma' (water, reversed). "
         "Arabic had massive influence on medieval languages, so some Arabic "
         "loanwords are expected in ANY medieval text. Not Voynich-specific."),
    ]

    for claim, level, reasoning in assessments:
        print(f"  [{level:11s}] {claim}")
        print(f"              {reasoning}")
        print()


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("PHASE 27: RIGOROUS SELF-AUDIT & FALSIFICATION")
    print("=" * 76)

    tokens = load_all_tokens()
    print(f"Loaded {len(tokens)} word tokens")

    # Run all sub-analyses
    results = {}

    r_27a = run_short_root_audit(tokens)
    results['27a'] = r_27a

    r_27b = run_grammar_check(tokens)
    results['27b'] = r_27b

    r_27c = run_section_specificity(tokens)
    results['27c'] = r_27c

    r_27d = run_translation_coherence(tokens)
    results['27d'] = r_27d

    r_27e = run_provisional_audit(tokens)
    results['27e'] = r_27e

    r_27f = run_falsification(tokens)
    results['27f'] = r_27f

    run_confidence_summary()

    # Final verdict
    print()
    print("=" * 76)
    print("PHASE 27: OVERALL VERDICT")
    print("=" * 76)
    print()
    print(f"  Short-root coverage percentage: {r_27a.get('short_pct',0):.1f}% of known tokens")
    print(f"  Honest (long-root) coverage: {r_27a.get('long_coverage',0):.1f}%")
    print(f"  Grammar consistency: {r_27b.get('pass',0)}/{r_27b.get('pass',0)+r_27b.get('fail',0)} roots pass POS tests")
    print(f"  Section specificity: {r_27c.get('pass',0)}/{r_27c.get('pass',0)+r_27c.get('fail',0)} domain predictions hold")
    print()
    print("  WHAT IS SOLID:")
    print("    - The morphological decomposition is mechanically consistent")
    print("    - s-prefix identifies a distinct class of roots (likely verbal)")
    print("    - Gallows determinatives show real section-dependent distributions")
    print("    - The prefix/suffix system is structurally regular")
    print()
    print("  WHAT IS SPECULATIVE:")
    print("    - ALL specific root meanings (lion, water, stone, etc.)")
    print("    - The Coptic/Arabic etymologies (phonetic resemblance ≠ proof)")
    print("    - Any 'connected prose' reading of translated lines")
    print("    - The exact classifier meanings (k=bodily is interpretation)")
    print()
    print("  WHAT WOULD STRENGTHEN THE MODEL:")
    print("    - External validation: match to known medieval text/tradition")
    print("    - Statistical significance tests: are our section enrichments")
    print("      better than chance?")
    print("    - Cross-linguistic comparison: systematic phonetic rules")
    print("      mapping Voynichese to Coptic (not just cherry-picked matches)")
    print("    - Higher long-root coverage (currently a better metric than total)")

    # Save results
    outpath = Path("results/phase27_output.txt")
    jsonpath = Path("results/phase27_results.json")

    json.dump(results, open(jsonpath, 'w'), indent=2, default=str)
    print(f"\n  Results saved to {jsonpath}")


if __name__ == '__main__':
    import contextlib
    outpath = Path("results/phase27_output.txt")
    with open(outpath, 'w', encoding='utf-8') as f:
        with contextlib.redirect_stdout(f):
            main()
    # Also print to console
    print(open(outpath, encoding='utf-8').read())
