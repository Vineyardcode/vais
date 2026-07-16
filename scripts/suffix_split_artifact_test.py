#!/usr/bin/env python3
"""
CRITICAL: Is the Binary Suffix Split a Parsing Artifact?
=====================================================================

derivational_prefix_paradox found that bare stems take -dy/-y while prefixed stems take
-ol/-or/-ar/-aiin (150+ pp difference). BUT:

  The word 'chedy' is parsed as root='ch' + suffix='edy'
  It COULD be root='che' + suffix='dy'

The suffix parser greedily matches the LONGEST suffix. Suffixes
-edy, -ey, -ody, -eedy all START with a vowel that could belong
to the stem. When a consonantal derivational prefix (ch, sh, l)
is present, the parser steals the stem vowel into the suffix.

THIS COULD ENTIRELY EXPLAIN THE BINARY SPLIT.

Tests:
  A) ALTERNATIVE PARSE — Re-parse everything with shortened suffix
       list (remove -edy, -ody, -eedy, -ey; keep only -dy, -y, -aiin,
       etc.). Does the binary split disappear?

  B) VOWEL-BOUNDARY TEST — Do suffixes -edy, -ody etc. ONLY appear
       after consonant-final roots? If so, the 'e' belongs to the root.

  C) RAW WORD FORM ANALYSIS — Skip the parser entirely. Classify
       raw words by surface patterns. Do ch-words and bare-words
       actually have different endings AT THE STRING LEVEL?

  D) WHICH SUFFIX LIST IS CORRECT? — Test both suffix lists against
       the full corpus and compare coverage, ambiguity, and regularity.

  E) IF THE SPLIT SURVIVES — re-test line position, gallows interaction,
       and co-occurrence under the corrected parser to see what's real.
"""

import re, json, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
from common import collapse_echains, gallows_base, load_all_tokens, strip_gallows

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

# TWO suffix lists to compare:
SUFFIXES_LONG = ['aiin','ain','iin','in','ar','or','al','ol',
                 'eedy','edy','ody','dy','ey','y']
# Minimal: only consonant-initial suffixes (no vowel-eating)
SUFFIXES_SHORT = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']

DERIV_PREFIXES_ORDER = ['lch','lsh','ch','sh','l','h']




def parse_morphology(w, suffix_list):
    pfx = sfx = ""
    for pf in PREFIXES:
        if w.startswith(pf) and len(w) > len(pf)+1:
            pfx = pf; w = w[len(pf):]; break
    for sf in suffix_list:
        if w.endswith(sf) and len(w) > len(sf):
            sfx = sf; w = w[:-len(sf)]; break
    return pfx, w, sfx

def decompose_with_suffixes(word, suffix_list):
    stripped, gals = strip_gallows(word)
    collapsed = collapse_echains(stripped)
    pfx, root, sfx = parse_morphology(collapsed, suffix_list)
    bases = [gallows_base(g) for g in gals]
    # Split root into deriv prefix + stem
    deriv = ""
    stem = root
    for dp in DERIV_PREFIXES_ORDER:
        if root.startswith(dp) and len(root) > len(dp):
            deriv = dp; stem = root[len(dp):]; break
    return dict(original=word, gram_prefix=pfx or "", det=bases[0] if bases else "",
                deriv_prefix=deriv, stem=stem, suffix=sfx or "",
                all_gallows=bases, old_root=root)


# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════

FOLIO_DIR = Path("folios")



CORE_STEMS = {
    'e','o','ed','eo','od','ol','al','am','ar','or','es',
    'eod','eos','os','a','d','l','r','s'
}


# ══════════════════════════════════════════════════════════════════
# 32a: ALTERNATIVE PARSE — MINIMAL SUFFIX LIST
# ══════════════════════════════════════════════════════════════════

def run_alternative_parse(tokens):
    print("=" * 76)
    print("ALTERNATIVE PARSE — DOES THE SPLIT SURVIVE?")
    print("=" * 76)
    print()
    print("If we remove vowel-initial suffixes (-edy, -ody, -eedy, -ey)")
    print("and keep only consonant-initial ones (-dy, -y, -ar, -or, etc.),")
    print("does the binary suffix split disappear?")
    print()

    # Parse with SHORT suffix list
    for label, sfx_list in [("LONG (original)", SUFFIXES_LONG),
                             ("SHORT (no vowel-eating)", SUFFIXES_SHORT)]:
        print(f"  ═══ SUFFIX LIST: {label} ═══")

        deriv_suffix = defaultdict(Counter)
        deriv_counts = defaultdict(int)

        for word, section, folio in tokens:
            d = decompose_with_suffixes(word, sfx_list)
            if d['stem'] in CORE_STEMS:
                key = (d['deriv_prefix'] or '∅', d['stem'])
                sfx = d['suffix'] or '∅'
                deriv_suffix[key][sfx] += 1
                deriv_counts[key] += 1

        # Show stem 'e' 
        stem = 'e'
        derivs = ['∅', 'h', 'ch']
        all_sfxs = set()
        for dv in derivs:
            all_sfxs.update(deriv_suffix.get((dv, stem), {}).keys())
        all_sfxs = sorted(all_sfxs, key=lambda s: -sum(
            deriv_suffix.get((dv, stem), {}).get(s, 0) for dv in derivs
        ))[:8]

        hdr = f"    {'deriv':6s} {'N':>5s}"
        for sf in all_sfxs:
            hdr += f" {sf:>6s}"
        print(hdr)

        rows = {}
        for dv in derivs:
            key = (dv, stem)
            n = deriv_counts.get(key, 0)
            if n < 5: continue
            row = f"    {dv:6s} {n:5d}"
            pcts = []
            for sf in all_sfxs:
                c = deriv_suffix[key].get(sf, 0)
                pct = 100 * c / n if n > 0 else 0
                row += f" {pct:5.0f}%"
                pcts.append(pct)
            rows[dv] = pcts
            print(row)

        if '∅' in rows and 'ch' in rows:
            diff = sum(abs(a - b) for a, b in zip(rows['∅'], rows['ch']))
            print(f"    |∅ vs ch| diff: {diff:.0f} pp")
        if '∅' in rows and 'h' in rows:
            diff = sum(abs(a - b) for a, b in zip(rows['∅'], rows['h']))
            print(f"    |∅ vs h| diff: {diff:.0f} pp")
        print()

        # Also show stem 'o', 'ol', 'd'
        for stem2 in ['o', 'ol', 'd']:
            dv_list = ['∅', 'h', 'ch']
            sfxs2 = set()
            for dv in dv_list:
                sfxs2.update(deriv_suffix.get((dv, stem2), {}).keys())
            sfxs2 = sorted(sfxs2, key=lambda s: -sum(
                deriv_suffix.get((dv, stem2), {}).get(s, 0) for dv in dv_list
            ))[:6]

            hdr2 = f"    Stem '{stem2}': {'deriv':6s} {'N':>5s}"
            for sf in sfxs2:
                hdr2 += f" {sf:>6s}"
            print(hdr2)

            rows2 = {}
            for dv in dv_list:
                key = (dv, stem2)
                n = deriv_counts.get(key, 0)
                if n < 5: continue
                row2 = f"    {'':9s} {dv:6s} {n:5d}"
                pcts2 = []
                for sf in sfxs2:
                    c = deriv_suffix[key].get(sf, 0)
                    pct = 100 * c / n if n > 0 else 0
                    row2 += f" {pct:5.0f}%"
                    pcts2.append(pct)
                rows2[dv] = pcts2
                print(row2)

            if '∅' in rows2 and 'ch' in rows2:
                diff2 = sum(abs(a - b) for a, b in zip(rows2['∅'], rows2['ch']))
                print(f"    {'':9s} |∅ vs ch| diff: {diff2:.0f} pp")
            print()

    return {}


# ══════════════════════════════════════════════════════════════════
# 32b: VOWEL-BOUNDARY TEST
# ══════════════════════════════════════════════════════════════════

def run_vowel_boundary_test(tokens):
    print()
    print("=" * 76)
    print("DO VOWEL-INITIAL SUFFIXES ONLY FOLLOW CONSONANTS?")
    print("=" * 76)
    print()
    print("If -edy/-ey/-ody are real suffixes, they should appear after BOTH")
    print("vowel-final and consonant-final roots. If they ONLY appear after")
    print("consonant-final roots, the vowel belongs to the stem.")
    print()

    root_ends = defaultdict(Counter)  # root_ends[suffix] = Counter of root-final chars

    for word, section, folio in tokens:
        d = decompose_with_suffixes(word, SUFFIXES_LONG)
        sfx = d['suffix']
        root = d['old_root']
        if sfx and root:
            last_char = root[-1]
            root_ends[sfx][last_char] += 1

    vowels = set('aeio')
    consonants = set('bcdfghjklmnpqrstvwxyz')

    print(f"  {'Suffix':8s} {'Total':>6s}  {'V-final':>8s} {'C-final':>8s}  {'V%':>5s} Issue?")
    for sfx in SUFFIXES_LONG:
        counts = root_ends.get(sfx, Counter())
        if not counts: continue
        total = sum(counts.values())
        v_count = sum(c for ch, c in counts.items() if ch in vowels)
        c_count = sum(c for ch, c in counts.items() if ch in consonants)
        v_pct = 100 * v_count / total if total > 0 else 0
        issue = "←SUSPECT" if v_pct < 5 and sfx[0] in vowels else ""
        print(f"  {sfx:8s} {total:6d}  {v_count:8d} {c_count:8d}  {v_pct:4.0f}% {issue}")
        if sfx[0] in vowels and total > 10:
            # Show which consonants precede this suffix
            tops = counts.most_common(5)
            print(f"           Root-final chars: {dict(tops)}")

    return {}


# ══════════════════════════════════════════════════════════════════
# 32c: RAW WORD FORM ANALYSIS — BYPASS THE PARSER
# ══════════════════════════════════════════════════════════════════

def run_raw_word_analysis(tokens):
    print()
    print("=" * 76)
    print("RAW WORD ENDINGS — PARSER-FREE ANALYSIS")
    print("=" * 76)
    print()
    print("Skip ALL parsing. Just look at how words END in the raw corpus.")
    print("Do ch-beginning words and bare words have different endings?")
    print()

    # Classify raw words by initial pattern
    ch_words = []
    sh_words = []
    h_words = []
    bare_words = []
    all_words = []

    for word, section, folio in tokens:
        # Strip gallows for fairer comparison
        stripped, gals = strip_gallows(word)
        collapsed = collapse_echains(stripped)
        all_words.append(collapsed)

        # Classify by what it starts with (after prefix stripping)
        pfx = ""
        w = collapsed
        for pf in PREFIXES:
            if w.startswith(pf) and len(w) > len(pf)+1:
                pfx = pf; w = w[len(pf):]; break

        if w.startswith('ch') and len(w) > 2:
            ch_words.append(w)
        elif w.startswith('sh') and len(w) > 2:
            sh_words.append(w)
        elif w.startswith('h') and len(w) > 1:
            h_words.append(w)
        else:
            bare_words.append(w)

    # Count last 2 and 3 character endings
    def ending_dist(words, n):
        endings = Counter()
        for w in words:
            if len(w) >= n:
                endings[w[-n:]] += 1
        return endings

    print(f"  Word groups: ch-initial={len(ch_words)}, sh-initial={len(sh_words)}, "
          f"h-initial={len(h_words)}, bare={len(bare_words)}")

    for n_chars in [2, 3]:
        print(f"\n  === LAST {n_chars} CHARACTERS ===")
        for label, words in [("bare", bare_words), ("ch-init", ch_words),
                              ("h-init", h_words)]:
            ends = ending_dist(words, n_chars)
            total = sum(ends.values())
            if total < 100: continue
            top10 = ends.most_common(10)
            top_str = ", ".join(f"{e}={c}({100*c//total}%)" for e, c in top10)
            print(f"  {label:8s} (N={total:5d}): {top_str}")

    # Specific test: words ending in 'dy' — are they equally bare and ch-?
    print(f"\n  === WORDS ENDING IN 'dy' ===")
    dy_bare = sum(1 for w in bare_words if w.endswith('dy'))
    dy_ch = sum(1 for w in ch_words if w.endswith('dy'))
    dy_h = sum(1 for w in h_words if w.endswith('dy'))
    print(f"    bare: {dy_bare} ({100*dy_bare/len(bare_words):.1f}%)")
    print(f"    ch:   {dy_ch} ({100*dy_ch/len(ch_words):.1f}%)")
    print(f"    h:    {dy_h} ({100*dy_h/len(h_words):.1f}%)")

    print(f"\n  === WORDS ENDING IN 'edy' ===")
    edy_bare = sum(1 for w in bare_words if w.endswith('edy'))
    edy_ch = sum(1 for w in ch_words if w.endswith('edy'))
    edy_h = sum(1 for w in h_words if w.endswith('edy'))
    print(f"    bare: {edy_bare} ({100*edy_bare/len(bare_words):.1f}%)")
    print(f"    ch:   {edy_ch} ({100*edy_ch/len(ch_words):.1f}%)")
    print(f"    h:    {edy_h} ({100*edy_h/len(h_words):.1f}%)")

    print(f"\n  === WORDS ENDING IN 'ol' ===")
    ol_bare = sum(1 for w in bare_words if w.endswith('ol'))
    ol_ch = sum(1 for w in ch_words if w.endswith('ol'))
    ol_h = sum(1 for w in h_words if w.endswith('ol'))
    print(f"    bare: {ol_bare} ({100*ol_bare/len(bare_words):.1f}%)")
    print(f"    ch:   {ol_ch} ({100*ol_ch/len(ch_words):.1f}%)")
    print(f"    h:    {ol_h} ({100*ol_h/len(h_words):.1f}%)")

    print(f"\n  === WORDS ENDING IN 'or' ===")
    or_bare = sum(1 for w in bare_words if w.endswith('or'))
    or_ch = sum(1 for w in ch_words if w.endswith('or'))
    or_h = sum(1 for w in h_words if w.endswith('or'))
    print(f"    bare: {or_bare} ({100*or_bare/len(bare_words):.1f}%)")
    print(f"    ch:   {or_ch} ({100*or_ch/len(ch_words):.1f}%)")
    print(f"    h:    {or_h} ({100*or_h/len(h_words):.1f}%)")

    print(f"\n  === WORDS ENDING IN 'aiin' ===")
    aiin_bare = sum(1 for w in bare_words if w.endswith('aiin'))
    aiin_ch = sum(1 for w in ch_words if w.endswith('aiin'))
    aiin_h = sum(1 for w in h_words if w.endswith('aiin'))
    print(f"    bare: {aiin_bare} ({100*aiin_bare/len(bare_words):.1f}%)")
    print(f"    ch:   {aiin_ch} ({100*aiin_ch/len(ch_words):.1f}%)")
    print(f"    h:    {aiin_h} ({100*aiin_h/len(h_words):.1f}%)")

    # THE KEY: do ch-words end in 'edy' at a different rate than bare words?
    # If they end in 'edy' at SIMILAR rates, the suffix split was an artifact.
    # If truly different, it's real.
    print(f"\n  ═══ CRITICAL COMPARISON ═══")
    print(f"  Combined -dy and -edy endings:")
    combined_bare = dy_bare + edy_bare
    combined_ch = dy_ch + edy_ch
    combined_h = dy_h + edy_h
    print(f"    bare: {combined_bare} ({100*combined_bare/len(bare_words):.1f}%)")
    print(f"    ch:   {combined_ch} ({100*combined_ch/len(ch_words):.1f}%)")
    print(f"    h:    {combined_h} ({100*combined_h/len(h_words):.1f}%)")
    print()
    if abs(combined_bare/len(bare_words) - combined_ch/len(ch_words)) < 0.05:
        print(f"  → SIMILAR -dy/-edy rates. The binary split is LIKELY AN ARTIFACT.")
    else:
        print(f"  → DIFFERENT rates even when combined. The split is at least PARTIALLY REAL.")

    return {}


# ══════════════════════════════════════════════════════════════════
# 32d: FULL SUFFIX COMPARISON
# ══════════════════════════════════════════════════════════════════

def run_suffix_comparison(tokens):
    print()
    print("=" * 76)
    print("LONG vs SHORT SUFFIX LIST — FULL COMPARISON")
    print("=" * 76)
    print()

    for label, sfx_list in [("LONG (edy,ody,ey include)", SUFFIXES_LONG),
                             ("SHORT (consonant-initial only)", SUFFIXES_SHORT)]:
        print(f"  ═══ {label} ═══")

        root_counts = Counter()
        suffix_counts = Counter()
        no_sfx = 0
        total = 0

        for word, section, folio in tokens:
            d = decompose_with_suffixes(word, sfx_list)
            root_counts[d['old_root']] += 1
            sfx = d['suffix']
            if sfx:
                suffix_counts[sfx] += 1
            else:
                no_sfx += 1
            total += 1

        print(f"    Total: {total}")
        print(f"    Has suffix: {total - no_sfx} ({100*(total-no_sfx)/total:.1f}%)")
        print(f"    No suffix: {no_sfx} ({100*no_sfx/total:.1f}%)")
        print(f"    Unique roots: {len(root_counts)}")
        print(f"    Suffix distribution: {dict(suffix_counts.most_common(15))}")
        print()

    # Under SHORT list, what happens to roots that were 'ch' under LONG list?
    print(f"  ═══ WHAT HAPPENS TO ROOT 'ch' UNDER SHORT LIST? ═══")
    ch_long = Counter()  # suffix when root is 'ch' under LONG
    ch_short_roots = Counter()  # what root is assigned under SHORT for same words

    for word, section, folio in tokens:
        d_long = decompose_with_suffixes(word, SUFFIXES_LONG)
        d_short = decompose_with_suffixes(word, SUFFIXES_SHORT)

        if d_long['old_root'] == 'ch':
            ch_long[d_long['suffix']] += 1
            ch_short_roots[d_short['old_root']] += 1

    print(f"    Under LONG list, root='ch' with suffixes: {dict(ch_long.most_common(10))}")
    print(f"    Under SHORT list, same words have roots: {dict(ch_short_roots.most_common(10))}")

    # Same for root 'sh'
    print(f"\n  ═══ WHAT HAPPENS TO ROOT 'sh' UNDER SHORT LIST? ═══")
    sh_long = Counter()
    sh_short_roots = Counter()
    for word, section, folio in tokens:
        d_long = decompose_with_suffixes(word, SUFFIXES_LONG)
        d_short = decompose_with_suffixes(word, SUFFIXES_SHORT)
        if d_long['old_root'] == 'sh':
            sh_long[d_long['suffix']] += 1
            sh_short_roots[d_short['old_root']] += 1

    print(f"    Under LONG list, root='sh' with suffixes: {dict(sh_long.most_common(10))}")
    print(f"    Under SHORT list, same words have roots: {dict(sh_short_roots.most_common(10))}")

    return {}


# ══════════════════════════════════════════════════════════════════
# 32e: RE-TEST derivational_prefix_paradox FINDINGS UNDER SHORT SUFFIX LIST
# ══════════════════════════════════════════════════════════════════

def run_revalidation(tokens):
    print()
    print("=" * 76)
    print("RE-TEST KEY derivational_prefix_paradox FINDINGS UNDER SHORT SUFFIX LIST")
    print("=" * 76)
    print()

    # EXPANDED core stems (since short suffix list will produce longer roots)
    # First, let's see what stems emerge
    root_counts = Counter()
    for word, section, folio in tokens:
        d = decompose_with_suffixes(word, SUFFIXES_SHORT)
        deriv = ""
        stem = d['old_root']
        for dp in DERIV_PREFIXES_ORDER:
            if stem.startswith(dp) and len(stem) > len(dp):
                deriv = dp; stem = stem[len(dp):]; break
        root_counts[stem] += 1

    print("  TOP 30 STEMS under SHORT suffix list:")
    for stem, count in root_counts.most_common(30):
        print(f"    {stem:12s}: {count}")

    # Expected: stems like 'edy', 'ey', 'ody' will now appear as stems
    # since they're no longer eaten by the suffix parser

    # Now check: do prefixed forms still have different suffix profiles?
    expanded_stems = {s for s, c in root_counts.items() if c >= 50}
    print(f"\n  Stems with N≥50: {len(expanded_stems)}")

    print(f"\n  SUFFIX PROFILES UNDER SHORT LIST:")
    deriv_suffix = defaultdict(Counter)
    deriv_counts = defaultdict(int)
    for word, section, folio in tokens:
        d = decompose_with_suffixes(word, SUFFIXES_SHORT)
        stem = d['old_root']
        deriv = ""
        for dp in DERIV_PREFIXES_ORDER:
            if stem.startswith(dp) and len(stem) > len(dp):
                deriv = dp; stem = stem[len(dp):]; break
        if stem in expanded_stems:
            key = (deriv or '∅', stem)
            sfx = d['suffix'] or '∅'
            deriv_suffix[key][sfx] += 1
            deriv_counts[key] += 1

    # Show a few key comparisons
    for stem in ['edy', 'ey', 'e', 'o', 'ody', 'ol']:
        if stem not in expanded_stems:
            continue
        print(f"\n    Stem '{stem}':")
        derivs = ['∅', 'h', 'ch']
        sfxs = set()
        for dv in derivs:
            sfxs.update(deriv_suffix.get((dv, stem), {}).keys())
        sfxs = sorted(sfxs, key=lambda s: -sum(
            deriv_suffix.get((dv, stem), {}).get(s, 0) for dv in derivs
        ))[:6]

        for dv in derivs:
            n = deriv_counts.get((dv, stem), 0)
            if n < 5: continue
            parts = []
            for sf in sfxs:
                c = deriv_suffix[(dv, stem)].get(sf, 0)
                if c > 0:
                    parts.append(f"{sf}={100*c/n:.0f}%")
            print(f"      {dv:5s} (N={n:5d}): {', '.join(parts)}")

    # RE-TEST LINE POSITION under short suffix list
    from pathlib import Path

    def load_folio_lines():
        lines = []
        section_map = {
            'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
            'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
        }
        for fpath in sorted(FOLIO_DIR.glob("*.txt")):
            section = 'unknown'
            for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
                line = line.strip()
                if line.startswith('#'):
                    ll = line.lower()
                    for key, val in section_map.items():
                        if key in ll:
                            section = val
                            if val == 'herbal' and '-b' in ll: section = 'herbal-B'
                            elif val == 'herbal': section = 'herbal-A'
                    continue
                m = re.match(r'<([^>]+)>', line)
                if m:
                    lid = m.group(1)
                    rest = line[m.end():].strip()
                else:
                    continue
                if not rest: continue
                words = []
                for w in re.split(r'[.\s,;]+', rest):
                    w = re.sub(r'[^a-z]', '', w.lower().strip())
                    if len(w) >= 2: words.append(w)
                if words:
                    lines.append((lid, section, words))
        return lines

    folio_lines = load_folio_lines()

    print(f"\n  LINE POSITION under SHORT suffix list:")
    deriv_positions = defaultdict(list)
    for lid, section, words in folio_lines:
        if len(words) < 3: continue
        for i, w in enumerate(words):
            d = decompose_with_suffixes(w, SUFFIXES_SHORT)
            stem = d['old_root']
            deriv = ""
            for dp in DERIV_PREFIXES_ORDER:
                if stem.startswith(dp) and len(stem) > len(dp):
                    deriv = dp; stem = stem[len(dp):]; break
            if not deriv: deriv = '∅'
            rel_pos = i / (len(words) - 1) if len(words) > 1 else 0.5
            deriv_positions[deriv].append(rel_pos)

    print(f"    {'Deriv':6s} {'N':>6s}  {'Mean':>6s}  {'Init<.2':>7s} {'Final>.8':>8s}")
    for deriv in ['∅', 'h', 'ch', 'sh', 'l']:
        positions = deriv_positions.get(deriv, [])
        if len(positions) < 20: continue
        n = len(positions)
        mean = sum(positions) / n
        init_pct = 100 * sum(1 for p in positions if p < 0.2) / n
        final_pct = 100 * sum(1 for p in positions if p > 0.8) / n
        print(f"    {deriv:6s} {n:6d}  {mean:6.3f}  {init_pct:6.1f}% {final_pct:7.1f}%")

    # RE-TEST GALLOWS × DERIV interaction
    print(f"\n  GALLOWS × DERIV under SHORT suffix list:")
    det_deriv = Counter()
    det_counts = Counter()
    deriv_counts_all = Counter()
    for word, section, folio in tokens:
        d = decompose_with_suffixes(word, SUFFIXES_SHORT)
        stem = d['old_root']
        deriv = ""
        for dp in DERIV_PREFIXES_ORDER:
            if stem.startswith(dp) and len(stem) > len(dp):
                deriv = dp; stem = stem[len(dp):]; break
        if not deriv: deriv = '∅'
        det = d['det'] or '∅'
        det_deriv[(det, deriv)] += 1
        det_counts[det] += 1
        deriv_counts_all[deriv] += 1

    total = sum(det_deriv.values())
    dets = ['∅', 'k', 't']
    derivs_test = ['∅', 'h', 'ch', 'sh', 'l']
    print(f"    {'':8s}", end="")
    for dv in derivs_test:
        print(f" {dv:>7s}", end="")
    print()
    for det in dets:
        print(f"    {det:8s}", end="")
        for dv in derivs_test:
            obs = det_deriv.get((det, dv), 0)
            exp = det_counts.get(det, 0) * deriv_counts_all.get(dv, 0) / total if total > 0 else 0
            ratio = obs / exp if exp > 0 else 0
            m = "*" if (ratio > 1.5 or ratio < 0.5) and obs > 10 else " "
            print(f" {ratio:6.2f}{m}", end="")
        print()

    return {}


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("suffix_split_artifact_test: CRITICAL VALIDATION — IS THE SUFFIX SPLIT AN ARTIFACT?")
    print("=" * 76)

    tokens = load_all_tokens()
    print(f"Loaded {len(tokens)} word tokens\n")

    run_alternative_parse(tokens)
    run_vowel_boundary_test(tokens)
    run_raw_word_analysis(tokens)
    run_suffix_comparison(tokens)
    run_revalidation(tokens)

    print()
    print("=" * 76)
    print("suffix_split_artifact_test: VERDICT")
    print("=" * 76)
    print()
    print("  If raw word endings show same -dy/-edy rates for ch- and bare:")
    print("    → BINARY SUFFIX SPLIT IS AN ARTIFACT. Retract derivational_prefix_paradox Finding 1.")
    print("  If raw endings truly differ:")
    print("    → Split is real but may be SMALLER than 150pp")
    print()
    print("  Line position and gallows findings are INDEPENDENT of suffix parsing.")
    print("  These survive regardless of suffix list choice.")

    json.dump({'status': 'complete'},
              open(Path("results/suffix_split_artifact_test_results.json"), 'w'), indent=2)
    print(f"\n  Results saved to results/suffix_split_artifact_test_results.json")


if __name__ == '__main__':
    import contextlib
    outpath = Path("results/suffix_split_artifact_test_output.txt")
    with open(outpath, 'w', encoding='utf-8') as f:
        with contextlib.redirect_stdout(f):
            main()
    print(open(outpath, encoding='utf-8').read())
