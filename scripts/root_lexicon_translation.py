#!/usr/bin/env python3
"""
Full-Passage Translation with 28 Confirmed Roots
=============================================================

With 28 confirmed root meanings + full grammar model (prefixes, suffixes,
gallows determinatives), attempt multi-line translation of:
  - A complete BIO paragraph (f76r lines 1-20)
  - A complete HERBAL entry (f1r lines 1-14)
  - A complete ZODIAC ring (f72v Pisces, already partially done)

Sub-analyses:
  23a) WORD-BY-WORD GLOSS — decompose + translate every word
  23b) PHRASE ASSEMBLY — compose glossed words into readable phrases
  23c) COVERAGE STATISTICS — what % of roots translated per line/section
  23d) INTERNAL COHERENCE — do bio glosses reference body/conditions?
       Do herbal glosses reference plants/preparations?
  23e) CROSS-SECTION COMPARISON — run on all sections, compare meaning clusters
"""

import re, json, sys, io
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


# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ══════════════════════════════════════════════════════════════════
# MORPHOLOGICAL PIPELINE (from high_frequency_root_profiles)
# ══════════════════════════════════════════════════════════════════

SIMPLE_GALLOWS = ["t","k","f","p"]
BENCH_GALLOWS  = ["cth","ckh","cph","cfh"]
COMPOUND_GCH   = ["tch","kch","pch","fch"]
COMPOUND_GSH   = ["tsh","ksh","psh","fsh"]
ALL_GALLOWS    = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

PREFIXES = ['qo','q','so','do','o','d','s','y']
# Declared variant: common.MORPH_SUFFIXES_NO_SY (kept as a local literal so
# the web UI exposes it as a parameter; see common/core.py for why order matters).
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
# EXPANDED VOCABULARY (28 confirmed + 2 provisional)
# ══════════════════════════════════════════════════════════════════

CONFIRMED_VOCAB = {
    # sentence_translation (Leo ring text)
    'esed': 'lion',         'she': 'tree/plant',
    'al':   'stone',        'he':  'fall/occur',
    'ro':   'mouth',        'les': 'tongue',
    'ran':  'name',         'cham':'hot/warm',
    'res':  'south',
    # Zodiac names (from the zodiac ring analyses)
    'ar':   'king/great',   'or':  'king/great',
    # zodiac_ring_alignment (Morphological system)
    'ol':   'carry/bear',   'am':  'water',
    'chas': 'lord/master',  'eos': 'star',
    'es':   'star',         'chol':'celestial-body',
    'cho':  'substance',
    # template_subtraction-21
    'eosh': 'dry',          'sheo':'dry',
    'choam':'hot',          'rar': 'king',
    'yed':  'hand',
    # high_frequency_root_profiles (High-frequency roots)
    'h':    'happen/occur', 'a':   'great-one',
    'e':    'this/that',    'ch':  'do/make',
    # Provisional
    'l':    'remedy/thing', 'd':   'matter/thing',
}

# Grammar glosses
PREFIX_GLOSS = {
    'qo': 'REL',     # relative pronoun marker
    'q':  'REL',
    'so': 'VERB',     # verbal prefix (s- variant)
    's':  'VERB',
    'do': 'GEN',      # genitive "of"
    'd':  'GEN',
    'o':  'DEF',      # definite article
    'y':  'ADJ',      # adjectival/descriptive
}

SUFFIX_GLOSS = {
    'aiin': 'PL',     # plural
    'ain':  'PL.OBL', # plural oblique
    'iin':  'PL',
    'in':   'PL',
    'ar':   'AGT',    # agent nominal
    'or':   'AGT',
    'al':   'LOC',    # locative/instrumental
    'ol':   'NOM',    # nominalized
    'eedy': 'DESC',   # intensive descriptive
    'edy':  'DESC',   # descriptive (bio register)
    'ody':  'PRESC',  # prescriptive (herbal register)
    'dy':   'ABR',    # abbreviated
    'ey':   'GEN',    # general/genitive
    'y':    'ST',     # stative/construct
}

DET_GLOSS = {
    't': 'CEL',       # celestial classifier
    'k': 'SUB',       # substance classifier
    'f': 'BOT',       # botanical classifier
    'p': 'DIS',       # discourse/sentence marker
}


def gloss_word(word):
    """Produce a gloss for a single Voynichese word."""
    dec = full_decompose(word)

    parts = []
    unknown_root = False

    # Prefix
    if dec['prefix']:
        pg = PREFIX_GLOSS.get(dec['prefix'], dec['prefix'])
        parts.append(pg)

    # Determinative/gallows
    if dec['determinative']:
        dg = DET_GLOSS.get(dec['determinative'], dec['determinative'])
        parts.append(f"[{dg}]")

    # Root meaning
    root = dec['root']
    if root in CONFIRMED_VOCAB:
        parts.append(CONFIRMED_VOCAB[root])
    elif root:
        parts.append(f"?{root}?")
        unknown_root = True

    # Suffix
    if dec['suffix']:
        sg = SUFFIX_GLOSS.get(dec['suffix'], dec['suffix'])
        parts.append(f"-{sg}")

    gloss = ".".join(parts) if parts else f"?{word}?"
    return {
        'word': word,
        'decomp': dec,
        'gloss': gloss,
        'root': root,
        'root_known': root in CONFIRMED_VOCAB,
        'unknown_root': unknown_root,
    }


def gloss_line(text):
    """Gloss all words in a line of text."""
    # Clean the line
    text = re.sub(r'<![\d:]+>','',text)
    text = re.sub(r'<![^>]*>','',text)
    text = re.sub(r'<%>|<\$>|<->|<\.>',' ',text)
    text = re.sub(r'<[^>]*>','',text)
    text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
    text = re.sub(r'\{([^}]+)\}', r'\1', text)
    text = re.sub(r'@\d+;?','',text)
    text = re.sub(r'\?\?\?','',text)
    tokens = re.split(r'[.\s,]+', text)
    results = []
    for tok in tokens:
        tok = tok.strip().replace("'","")
        if not tok or '?' in tok: continue
        if not re.match(r'^[a-z]+$', tok): continue
        if len(tok) < 2: continue
        results.append(gloss_word(tok))
    return results


# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════


def load_folio_lines(folio_name):
    """Load all text lines from a folio."""
    fpath = Path("folios") / f"{folio_name}.txt"
    if not fpath.exists():
        print(f"  WARNING: {fpath} not found")
        return []
    lines = fpath.read_text(encoding="utf-8").splitlines()
    result = []
    for line in lines:
        line = line.strip()
        if line.startswith("#") or not line: continue
        lm = re.match(r'<([^>]+)>\s*(.*)', line)
        if not lm: continue
        locus = lm.group(1)
        text = lm.group(2)
        if text.strip().startswith("<!") and len(text.strip()) < 30: continue
        result.append({'locus': locus, 'raw': text})
    return result

def load_all_folios():
    """Load all folios for cross-section analysis."""
    folio_dir = Path("folios")
    all_folios = {}
    for txt_file in sorted(folio_dir.glob("*.txt")):
        stem = txt_file.stem
        section = classify_folio(stem)
        lines = load_folio_lines(stem)
        if lines:
            all_folios[stem] = {'section': section, 'lines': lines}
    return all_folios


# ══════════════════════════════════════════════════════════════════
# 23a: WORD-BY-WORD TRANSLATION OF TARGET PASSAGES
# ══════════════════════════════════════════════════════════════════

def run_passage_translation(folio_name, label, max_lines=30):
    """Translate a full passage word-by-word."""
    print(f"\n{'='*76}")
    print(f"FULL TRANSLATION — {label} ({folio_name})")
    print(f"{'='*76}")

    lines = load_folio_lines(folio_name)
    if not lines:
        return []

    all_glosses = []
    total_roots = 0
    known_roots = 0
    line_stats = []

    for i, linedata in enumerate(lines[:max_lines]):
        locus = linedata['locus']
        raw = linedata['raw']
        glossed = gloss_line(raw)
        if not glossed:
            continue

        # Stats for this line
        n_total = len(glossed)
        n_known = sum(1 for g in glossed if g['root_known'])
        pct = n_known / n_total * 100 if n_total else 0
        total_roots += n_total
        known_roots += n_known

        print(f"\n  {'─'*72}")
        print(f"  {locus} ({n_known}/{n_total} roots known = {pct:.0f}%)")
        print(f"  {'─'*72}")

        # Print original words
        words_str = " ".join(g['word'] for g in glossed)
        print(f"  VOY: {words_str}")

        # Print glosses
        gloss_str = " ".join(g['gloss'] for g in glossed)
        print(f"  GLO: {gloss_str}")

        # Print readable phrase attempt
        phrase_parts = []
        for g in glossed:
            dec = g['decomp']
            root = dec['root']
            pfx = dec['prefix']
            sfx = dec['suffix']
            det = dec['determinative']

            if root in CONFIRMED_VOCAB:
                meaning = CONFIRMED_VOCAB[root]
                # Build phrase fragment
                frag = ""
                if pfx in ('qo','q'): frag += "which-"
                elif pfx in ('d','do'): frag += "of-"
                elif pfx == 'o': frag += "the-"
                elif pfx in ('s','so'): frag += "V:"
                elif pfx == 'y': frag += "adj:"

                if det: frag += f"({DET_GLOSS.get(det,'?')})."

                frag += meaning

                if sfx in ('aiin','ain','iin','in'): frag += "(PL)"
                elif sfx in ('ar','or'): frag += "(-er)"
                elif sfx in ('al',): frag += "(-place)"
                elif sfx in ('ol',): frag += "(-NOM)"
                elif sfx in ('edy','eedy'): frag += "(-DESC)"
                elif sfx == 'ody': frag += "(-PRESC)"
                elif sfx in ('ey','y'): frag += "(-of)"
                elif sfx == 'dy': frag += "(~)"

                phrase_parts.append(frag)
            else:
                phrase_parts.append(f"[{g['word']}]")

        phrase = " | ".join(phrase_parts)
        print(f"  ENG: {phrase}")

        line_stats.append({
            'locus': locus, 'n_total': n_total,
            'n_known': n_known, 'pct': pct,
            'glosses': glossed
        })
        all_glosses.extend(glossed)

    # Summary
    overall_pct = known_roots / total_roots * 100 if total_roots else 0
    print(f"\n  {'='*72}")
    print(f"  SUMMARY: {known_roots}/{total_roots} roots translated ({overall_pct:.1f}%)")
    print(f"  {'='*72}")

    return line_stats


# ══════════════════════════════════════════════════════════════════
# 23b: UNKNOWN ROOT CENSUS
# ══════════════════════════════════════════════════════════════════

def run_unknown_census(all_stats):
    """Identify the most common untranslated roots."""
    print(f"\n{'='*76}")
    print(f"UNKNOWN ROOT CENSUS")
    print(f"{'='*76}")

    unknown_counter = Counter()
    known_counter = Counter()
    for stat_list in all_stats:
        for ls in stat_list:
            for g in ls['glosses']:
                root = g['root']
                if g['root_known']:
                    known_counter[root] += 1
                elif root:
                    unknown_counter[root] += 1

    print(f"\n  Top 20 UNKNOWN roots (most translation-blocking):")
    print(f"  {'Root':<12} {'Count':>6}  {'Example words'}")
    print(f"  {'─'*60}")
    # Collect example words for each unknown root
    unknown_examples = defaultdict(set)
    for stat_list in all_stats:
        for ls in stat_list:
            for g in ls['glosses']:
                if not g['root_known'] and g['root']:
                    unknown_examples[g['root']].add(g['word'])

    for root, count in unknown_counter.most_common(20):
        examples = list(unknown_examples[root])[:3]
        ex_str = ", ".join(examples)
        print(f"  {root:<12} {count:>6}  {ex_str}")

    print(f"\n  Top 20 KNOWN roots (most translated):")
    print(f"  {'Root':<12} {'Count':>6}  {'Meaning'}")
    print(f"  {'─'*60}")
    for root, count in known_counter.most_common(20):
        meaning = CONFIRMED_VOCAB.get(root, '?')
        print(f"  {root:<12} {count:>6}  {meaning}")

    return unknown_counter


# ══════════════════════════════════════════════════════════════════
# 23c: INTERNAL COHERENCE TEST
# ══════════════════════════════════════════════════════════════════

def run_coherence_test(bio_stats, herbal_stats):
    """Check if translations are internally coherent."""
    print(f"\n{'='*76}")
    print(f"INTERNAL COHERENCE TEST")
    print(f"{'='*76}")

    # Define semantic fields
    body_words = {'happen/occur', 'fall/occur', 'mouth', 'tongue', 'hand', 'hot/warm'}
    plant_words = {'tree/plant', 'substance', 'dry', 'hot/warm', 'water'}
    astro_words = {'star', 'celestial-body', 'king/great', 'lion', 'south'}
    action_words = {'do/make', 'carry/bear', 'happen/occur', 'fall/occur'}
    gram_words = {'this/that', 'great-one', 'remedy/thing', 'matter/thing'}

    for label, stats in [("BIO", bio_stats), ("HERBAL", herbal_stats)]:
        meaning_counts = Counter()
        det_counts = Counter()
        pfx_counts = Counter()
        sfx_counts = Counter()

        for ls in stats:
            for g in ls['glosses']:
                if g['root_known']:
                    meaning = CONFIRMED_VOCAB.get(g['root'],'')
                    meaning_counts[meaning] += 1
                det = g['decomp']['determinative']
                if det: det_counts[det] += 1
                pfx = g['decomp']['prefix']
                if pfx: pfx_counts[pfx] += 1
                sfx = g['decomp']['suffix']
                if sfx: sfx_counts[sfx] += 1

        n_body = sum(meaning_counts[w] for w in body_words if w in meaning_counts)
        n_plant = sum(meaning_counts[w] for w in plant_words if w in meaning_counts)
        n_astro = sum(meaning_counts[w] for w in astro_words if w in meaning_counts)
        n_action = sum(meaning_counts[w] for w in action_words if w in meaning_counts)
        n_gram = sum(meaning_counts[w] for w in gram_words if w in meaning_counts)
        n_total = sum(meaning_counts.values())

        print(f"\n  {label} SECTION SEMANTIC FIELD DISTRIBUTION:")
        print(f"  {'─'*60}")
        print(f"  Body/condition words:  {n_body:>4} ({n_body/n_total*100:.1f}%)" if n_total else "")
        print(f"  Plant/substance words: {n_plant:>4} ({n_plant/n_total*100:.1f}%)" if n_total else "")
        print(f"  Astro/celestial words: {n_astro:>4} ({n_astro/n_total*100:.1f}%)" if n_total else "")
        print(f"  Action/process words:  {n_action:>4} ({n_action/n_total*100:.1f}%)" if n_total else "")
        print(f"  Grammar/function:      {n_gram:>4} ({n_gram/n_total*100:.1f}%)" if n_total else "")
        print(f"  Total known meanings:  {n_total}")

        print(f"\n  Top meanings in {label}:")
        for meaning, cnt in meaning_counts.most_common(10):
            print(f"    {meaning:<20} {cnt:>4}")

        print(f"\n  Determinative distribution in {label}:")
        total_det = sum(det_counts.values())
        for det, cnt in det_counts.most_common():
            dlabel = DET_GLOSS.get(det, det)
            print(f"    {dlabel}({det}): {cnt:>4} ({cnt/total_det*100:.1f}%)" if total_det else "")

        print(f"\n  Suffix distribution in {label}:")
        total_sfx = sum(sfx_counts.values())
        for sfx, cnt in sfx_counts.most_common(8):
            slabel = SUFFIX_GLOSS.get(sfx, sfx)
            print(f"    {slabel}({sfx}): {cnt:>4} ({cnt/total_sfx*100:.1f}%)" if total_sfx else "")

    # COHERENCE VERDICT
    print(f"\n  {'='*60}")
    print(f"  COHERENCE VERDICT:")
    print(f"  {'='*60}")


# ══════════════════════════════════════════════════════════════════
# 23d: CROSS-SECTION COVERAGE
# ══════════════════════════════════════════════════════════════════

def run_cross_section_coverage():
    """Measure translation coverage across all sections."""
    print(f"\n{'='*76}")
    print(f"CROSS-SECTION TRANSLATION COVERAGE")
    print(f"{'='*76}")

    all_folios = load_all_folios()

    section_stats = defaultdict(lambda: {'total': 0, 'known': 0, 'words': 0})
    folio_coverages = []

    for stem, fdata in sorted(all_folios.items()):
        section = fdata['section']
        n_total = 0
        n_known = 0
        n_words = 0

        for linedata in fdata['lines']:
            glossed = gloss_line(linedata['raw'])
            n_words += len(glossed)
            for g in glossed:
                if g['root']:
                    n_total += 1
                    if g['root_known']:
                        n_known += 1

        section_stats[section]['total'] += n_total
        section_stats[section]['known'] += n_known
        section_stats[section]['words'] += n_words

        pct = n_known / n_total * 100 if n_total else 0
        folio_coverages.append((stem, section, n_words, n_known, n_total, pct))

    print(f"\n  Section-level coverage:")
    print(f"  {'Section':<12} {'Words':>7} {'Known':>7} {'Total':>7} {'Coverage':>9}")
    print(f"  {'─'*50}")
    for sect in ['herbal-A','herbal-B','zodiac','bio','cosmo','pharma','text']:
        s = section_stats[sect]
        pct = s['known'] / s['total'] * 100 if s['total'] else 0
        print(f"  {sect:<12} {s['words']:>7} {s['known']:>7} {s['total']:>7} {pct:>8.1f}%")

    total_w = sum(s['words'] for s in section_stats.values())
    total_k = sum(s['known'] for s in section_stats.values())
    total_t = sum(s['total'] for s in section_stats.values())
    total_pct = total_k / total_t * 100 if total_t else 0
    print(f"  {'─'*50}")
    print(f"  {'TOTAL':<12} {total_w:>7} {total_k:>7} {total_t:>7} {total_pct:>8.1f}%")

    # Top/bottom folios
    folio_coverages.sort(key=lambda x: -x[5])
    print(f"\n  Top 10 highest-coverage folios:")
    print(f"  {'Folio':<20} {'Section':<12} {'Words':>6} {'Cov%':>6}")
    print(f"  {'─'*50}")
    for stem, sect, nw, nk, nt, pct in folio_coverages[:10]:
        print(f"  {stem:<20} {sect:<12} {nw:>6} {pct:>5.1f}%")

    print(f"\n  Bottom 10 lowest-coverage folios (>20 words):")
    bottom = [x for x in folio_coverages if x[2] > 20]
    bottom.sort(key=lambda x: x[5])
    print(f"  {'Folio':<20} {'Section':<12} {'Words':>6} {'Cov%':>6}")
    print(f"  {'─'*50}")
    for stem, sect, nw, nk, nt, pct in bottom[:10]:
        print(f"  {stem:<20} {sect:<12} {nw:>6} {pct:>5.1f}%")

    return section_stats


# ══════════════════════════════════════════════════════════════════
# 23e: SYNTHESIS — BEST TRANSLATED LINES
# ══════════════════════════════════════════════════════════════════

def run_best_translations(bio_stats, herbal_stats):
    """Find the lines with highest translation rates for showcase."""
    print(f"\n{'='*76}")
    print(f"BEST TRANSLATED LINES (SHOWCASE)")
    print(f"{'='*76}")

    all_lines = []
    for ls in bio_stats:
        all_lines.append(('BIO', ls))
    for ls in herbal_stats:
        all_lines.append(('HERBAL', ls))

    # Sort by coverage percentage (min 4 words)
    candidates = [(sect, ls) for sect, ls in all_lines
                  if ls['n_total'] >= 4 and ls['pct'] >= 50]
    candidates.sort(key=lambda x: (-x[1]['pct'], -x[1]['n_total']))

    print(f"\n  Lines with >=50% root coverage (min 4 words):")
    for sect, ls in candidates[:15]:
        locus = ls['locus']
        pct = ls['pct']
        n = ls['n_total']
        nk = ls['n_known']

        # Build readable gloss
        phrase_parts = []
        for g in ls['glosses']:
            dec = g['decomp']
            root = dec['root']
            pfx = dec['prefix']
            sfx = dec['suffix']
            det = dec['determinative']

            if root in CONFIRMED_VOCAB:
                meaning = CONFIRMED_VOCAB[root]
                frag = ""
                if pfx in ('qo','q'): frag += "which-"
                elif pfx in ('d','do'): frag += "of-"
                elif pfx == 'o': frag += "the-"
                elif pfx in ('s','so'): frag += ""  # verbal
                elif pfx == 'y': frag += ""

                frag += meaning

                if sfx in ('aiin','ain','iin','in'): frag += "s"
                elif sfx in ('edy','eedy'): frag += "(desc.)"
                elif sfx == 'ody': frag += "(presc.)"
                elif sfx == 'ol': frag += "(nom.)"

                phrase_parts.append(frag)
            else:
                phrase_parts.append(f"[?]")

        print(f"\n  {'─'*68}")
        print(f"  {sect} | {locus} | {nk}/{n} = {pct:.0f}%")
        voy = " ".join(g['word'] for g in ls['glosses'])
        print(f"  VOY: {voy}")
        print(f"  ENG: {' '.join(phrase_parts)}")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("root_lexicon_translation: FULL-PASSAGE TRANSLATION WITH 28 CONFIRMED ROOTS")
    print("="*76)
    print(f"Vocabulary: {len(CONFIRMED_VOCAB)} roots confirmed")
    print(f"Grammar: prefixes ({len(PREFIX_GLOSS)}), suffixes ({len(SUFFIX_GLOSS)}), determinatives ({len(DET_GLOSS)})")

    # 23a: Translate target passages
    bio_stats = run_passage_translation("f76r", "BIO SECTION", max_lines=30)
    herbal_stats = run_passage_translation("f1r", "HERBAL SECTION", max_lines=20)

    # Also try a second bio folio for comparison
    bio_stats2 = run_passage_translation("f78r", "BIO SECTION 2", max_lines=20)

    # 23b: Unknown root census
    run_unknown_census([bio_stats, herbal_stats, bio_stats2])

    # 23c: Internal coherence
    run_coherence_test(bio_stats + bio_stats2, herbal_stats)

    # 23d: Cross-section coverage
    run_cross_section_coverage()

    # 23e: Best translations
    run_best_translations(bio_stats + bio_stats2, herbal_stats)

    # Save results
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    results_dir.joinpath("root_lexicon_translation_results.json").write_text(
        json.dumps({"phase": 23, "vocab_size": len(CONFIRMED_VOCAB)}, indent=2),
        encoding="utf-8"
    )
    print(f"\n  Results saved to results/root_lexicon_translation_results.json")


if __name__ == "__main__":
    main()
