#!/usr/bin/env python3
"""
Compound Decomposition, h-Verbal Pattern & BARE Class
=================================================================

root_significance_tests revealed three critical structural patterns:
  1) ALL 10 verbal roots (s%>50%) start with h-
  2) 28 roots are >85% bare — compound-initial bound morphemes
  3) Many "unknown" long roots decompose into shorter known parts

This phase tests:
  29a) h- VERBAL PREFIX HYPOTHESIS — Is 'h' a verbal prefix rather than
       root 'happen/occur'? Test: strip h- and see if remaining part
       is an independent root. If h+e, h+o, h+ed, h+eo, h+od, h+ol,
       h+es, h+eod, h+eos all independently exist as roots, then h-
       is a productive verbal prefix.
  29b) SYSTEMATIC COMPOUND DECOMPOSITION — For all long unknown roots,
       test every possible split into 2 shorter known parts. Score by
       whether both parts exist as independent roots.
  29c) BARE CLASS ANALYSIS — What follows bare roots? If ch is always
       followed by specific patterns, it's a bound morpheme. Map the
       collocational structure.
  29d) REVISED MORPHOLOGICAL MODEL — Based on findings, propose an
       updated parse: perhaps h- is verbal, ch- is nominal-compound,
       and the morphology is prefix + h/ch + root + gallows + suffix.
  29e) CHI-SQUARED SECTION CLUSTERING — For every root with N≥20,
       test whether its section distribution is significantly non-random.
"""

import re, json, sys, io, math
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from common import collapse_echains, gallows_base, load_all_tokens, load_folio_lines, strip_gallows

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
# DATA LOADING
# ══════════════════════════════════════════════════════════════════

FOLIO_DIR = Path("folios")




# ══════════════════════════════════════════════════════════════════
# h- VERBAL PREFIX HYPOTHESIS
# ══════════════════════════════════════════════════════════════════

def run_h_prefix_test(tokens):
    print("=" * 76)
    print("h- VERBAL PREFIX HYPOTHESIS")
    print("=" * 76)
    print()
    print("ALL 10 roots with s%>50% start with h: h, he, ho, hed, heo,")
    print("hod, hol, hes, heod, heos. This is remarkable.")
    print()
    print("HYPOTHESIS: h- is the TRUE verbal marker. The s- prefix just")
    print("co-occurs because s+h = 'verbal + verb-stem'. The root is what")
    print("follows h-, not including h- itself.")
    print()

    # Collect all roots and their frequencies
    root_counts = Counter()
    root_prefixes = defaultdict(Counter)
    for word, section, folio in tokens:
        d = full_decompose(word)
        root_counts[d['root']] += 1
        root_prefixes[d['root']][d['prefix']] += 1

    # The verbal roots and their h-stripped remainders
    h_verbs = ['h', 'he', 'ho', 'hed', 'heo', 'hod', 'hol', 'hes', 'heod', 'heos']

    print(f"  {'h-root':8s} {'N':>5s} {'s%':>6s}  {'Remainder':8s} {'Rem-N':>6s} {'Rem-s%':>6s}  {'Rem exists?':12s}")
    
    matches = 0
    for hroot in h_verbs:
        n = root_counts.get(hroot, 0)
        s_pct = 100*(root_prefixes[hroot].get('s',0)+root_prefixes[hroot].get('so',0))/n if n > 0 else 0

        # Strip h- to get remainder
        if hroot == 'h':
            remainder = '(bare)'
            rem_n = 0
            rem_s = 0
            exists = 'h IS the prefix'
        else:
            remainder = hroot[1:]  # strip first char 'h'
            rem_n = root_counts.get(remainder, 0)
            rem_s = 100*(root_prefixes[remainder].get('s',0)+root_prefixes[remainder].get('so',0))/rem_n if rem_n > 0 else 0
            exists = f"YES ({rem_n})" if rem_n >= 5 else (f"marginal ({rem_n})" if rem_n > 0 else "NO")
            if rem_n >= 5:
                matches += 1

        print(f"  {hroot:8s} {n:5d} {s_pct:5.0f}%  {remainder:8s} {rem_n:6d} {rem_s:5.0f}%  {exists}")

    remainder_roots = len([r for r in h_verbs if r != 'h'])
    print(f"\n  RESULT: {matches}/{remainder_roots} h-verbal roots have independent remainders")

    # Critical test: Do the remainders behave as NOUNS when independent?
    print(f"\n  REMAINDER BEHAVIOR (when occurring without h-prefix):")
    print(f"  {'Remainder':8s} {'N':>5s} {'d%':>6s} {'o%':>6s} {'s%':>6s} {'bare%':>6s}  {'POS':8s}")
    
    for hroot in h_verbs:
        if hroot == 'h': continue
        remainder = hroot[1:]
        n = root_counts.get(remainder, 0)
        if n < 5: continue
        pfx = root_prefixes[remainder]
        d_pct = 100*(pfx.get('d',0)+pfx.get('do',0))/n
        o_pct = 100*pfx.get('o',0)/n
        s_pct = 100*(pfx.get('s',0)+pfx.get('so',0))/n
        bare_pct = 100*pfx.get('',0)/n
        
        if s_pct > 50: pos = 'VERB'
        elif bare_pct > 85: pos = 'BARE'
        elif d_pct + o_pct > s_pct and s_pct < 20: pos = 'NOUN'
        else: pos = 'AMBIG'
        
        print(f"  {remainder:8s} {n:5d} {d_pct:6.1f} {o_pct:6.1f} {s_pct:6.1f} {bare_pct:6.1f}  {pos}")

    # Alternative test: is s- just co-occurring with h-, or does s- appear
    # with non-h roots too?
    print(f"\n  s-PREFIX DISTRIBUTION ACROSS ALL ROOTS:")
    s_with_h = 0
    s_without_h = 0
    for root, pfxcounts in root_prefixes.items():
        s_count = pfxcounts.get('s', 0) + pfxcounts.get('so', 0)
        if s_count > 0:
            if root.startswith('h') or root == 'h':
                s_with_h += s_count
            else:
                s_without_h += s_count
    total_s = s_with_h + s_without_h
    print(f"  s-prefix with h-initial roots: {s_with_h} ({100*s_with_h/total_s:.1f}%)")
    print(f"  s-prefix with non-h roots:     {s_without_h} ({100*s_without_h/total_s:.1f}%)")
    
    if s_with_h > 0.8 * total_s:
        print(f"  → s- prefix is OVERWHELMINGLY associated with h- roots.")
        print(f"  → This strongly supports h- as the verbal marker.")
    elif s_with_h > 0.5 * total_s:
        print(f"  → s- is mostly with h-roots but appears elsewhere too.")
        print(f"  → h- is verbal but s- may also independently mark verbal mood.")
    else:
        print(f"  → s- is broadly distributed. h- correlation may be coincidence.")

    # What about non-s prefixes with h-roots?
    print(f"\n  h-ROOT PREFIX DIVERSITY (are h-roots ONLY used with s-?):")
    for hroot in ['h', 'he', 'ho']:
        n = root_counts.get(hroot, 0)
        if n < 20:
            continue
        pfx = root_prefixes[hroot]
        parts = []
        for p in ['', 's', 'so', 'd', 'do', 'o', 'qo', 'q', 'y']:
            if pfx.get(p, 0) > 0:
                parts.append(f"{p or 'bare'}={pfx[p]}({100*pfx[p]/n:.0f}%)")
        print(f"  {hroot:5s} (N={n:5d}): {', '.join(parts)}")

    return {'s_with_h': s_with_h, 's_without_h': s_without_h, 'matches': matches}


# ══════════════════════════════════════════════════════════════════
# SYSTEMATIC COMPOUND DECOMPOSITION
# ══════════════════════════════════════════════════════════════════

def run_compound_decomposition(tokens):
    print()
    print("=" * 76)
    print("SYSTEMATIC COMPOUND DECOMPOSITION")
    print("=" * 76)
    print()
    print("For each unknown long root, try ALL possible splits into two")
    print("shorter parts. Score by whether both parts exist as roots.")
    print()

    # Build frequency table for ALL roots (not just "known")
    root_counts = Counter()
    for word, section, folio in tokens:
        d = full_decompose(word)
        root_counts[d['root']] += 1

    # All roots with N≥10 are "real enough" to be compound parts
    real_roots = {r for r, c in root_counts.items() if c >= 10}
    
    # Known roots from our vocabulary (high confidence)
    known_roots = {
        'e','a','h','l','d','ch','al','am','ar','or','ol','ho',
        'he','es','ro','she','les','ran','res','eos','chas','ches',
        'cho','chol','cham','hed','cheos','lch','ed','che','ched',
        'chod','alch','sh','air','lsh','eod','od'
    }

    # Target: unknown long roots with N≥10
    unknowns = [(r, c) for r, c in root_counts.most_common(500)
                if len(r) >= 3 and c >= 10 and r not in known_roots]

    print(f"  Testing {len(unknowns)} unknown long roots for compound structure...")
    print()
    print(f"  {'Root':12s} {'N':>5s}  {'Split':20s} {'Part1-N':>7s} {'Part2-N':>7s} {'Score':>6s}")

    decomposed = []
    for root, count in unknowns:
        best_split = None
        best_score = 0
        
        # Try all possible split points
        for i in range(1, len(root)):
            part1 = root[:i]
            part2 = root[i:]
            
            if not part1 or not part2:
                continue
            
            n1 = root_counts.get(part1, 0)
            n2 = root_counts.get(part2, 0)
            
            # Score: both parts must exist independently
            if n1 >= 5 and n2 >= 5:
                # Prefer splits where both parts are frequent
                score = min(n1, n2)
                # Bonus if both are in known_roots
                if part1 in known_roots: score *= 2
                if part2 in known_roots: score *= 2
                
                if score > best_score:
                    best_score = score
                    best_split = (part1, part2, n1, n2)

        if best_split:
            p1, p2, n1, n2 = best_split
            known1 = "✓" if p1 in known_roots else " "
            known2 = "✓" if p2 in known_roots else " "
            print(f"  {root:12s} {count:5d}  {p1}{known1}+{p2}{known2}         {n1:7d} {n2:7d} {best_score:6d}")
            decomposed.append((root, count, p1, p2, n1, n2, best_score))
        else:
            # No valid decomposition found
            decomposed.append((root, count, None, None, 0, 0, 0))

    # Summary
    has_decomp = sum(1 for _, _, p1, _, _, _, _ in decomposed if p1 is not None)
    no_decomp = sum(1 for _, _, p1, _, _, _, _ in decomposed if p1 is None)
    print(f"\n  RESULTS:")
    print(f"    Decomposable: {has_decomp}/{len(decomposed)} ({100*has_decomp/len(decomposed):.0f}%)")
    print(f"    Atomic (no split): {no_decomp}/{len(decomposed)} ({100*no_decomp/len(decomposed):.0f}%)")

    # Show the top undecomposable roots — these are truly novel
    print(f"\n  TOP ATOMIC (non-decomposable) LONG ROOTS:")
    for root, count, p1, p2, n1, n2, score in decomposed:
        if p1 is None and count >= 15:
            print(f"    {root:12s}: {count:5d} tokens — genuinely unknown")

    return decomposed


# ══════════════════════════════════════════════════════════════════
# BARE CLASS COLLOCATIONAL ANALYSIS
# ══════════════════════════════════════════════════════════════════

def run_bare_class_analysis(tokens):
    print()
    print("=" * 76)
    print("BARE CLASS ANALYSIS — WHAT FOLLOWS BARE ROOTS?")
    print("=" * 76)
    print()
    print("28 roots are >85% bare (no prefix). These may be bound morphemes")
    print("that combine with what follows. We map what immediately follows.")
    print()

    # Load line-structured data
    folio_lines = load_folio_lines()

    # Key bare roots to investigate: ch, cho, chol, ches, ched, chod, cham, chal
    bare_targets = ['ch', 'cho', 'la', 'lb', 'ih', 'che', 'ched', 'chol', 'chod', 'ches', 'cham']

    for target_root in bare_targets:
        # Find instances in lines and what follows
        following_roots = Counter()
        following_words = Counter()
        preceding_roots = Counter()
        total_found = 0

        for lid, section, words in folio_lines:
            decomposed = [full_decompose(w) for w in words]
            for i, d in enumerate(decomposed):
                if d['root'] == target_root:
                    total_found += 1
                    if i + 1 < len(decomposed):
                        following_roots[decomposed[i+1]['root']] += 1
                        following_words[words[i+1]] += 1
                    if i > 0:
                        preceding_roots[decomposed[i-1]['root']] += 1

        if total_found < 10:
            continue

        print(f"  === {target_root} (N={total_found}) ===")
        print(f"    FOLLOWING ROOTS (top 8): {dict(following_roots.most_common(8))}")
        print(f"    PRECEDING ROOTS (top 8): {dict(preceding_roots.most_common(8))}")
        
        # Is the following root highly concentrated?
        if following_roots:
            top_follow_pct = following_roots.most_common(1)[0][1] / total_found * 100
            top3_pct = sum(c for _, c in following_roots.most_common(3)) / total_found * 100
            print(f"    Top-1 following root: {top_follow_pct:.0f}%, Top-3: {top3_pct:.0f}%")
            if top_follow_pct > 40:
                top_root = following_roots.most_common(1)[0][0]
                print(f"    → {target_root} is strongly bound to '{top_root}' — likely a compound prefix")
        print()

    return {}


# ══════════════════════════════════════════════════════════════════
# REVISED MORPHOLOGICAL MODEL
# ══════════════════════════════════════════════════════════════════

def run_revised_model(tokens):
    print()
    print("=" * 76)
    print("REVISED MORPHOLOGICAL MODEL")
    print("=" * 76)
    print()
    print("Based on Phases 27-29 findings, propose a revised parse model.")
    print()

    root_counts = Counter()
    root_prefixes = defaultdict(Counter)
    for word, section, folio in tokens:
        d = full_decompose(word)
        root_counts[d['root']] += 1
        root_prefixes[d['root']][d['prefix']] += 1

    # Test: What if we parse ch- as a prefix (not a gallows)?
    # In current pipeline, 'ch' is extracted as the root after gallows stripping.
    # But ch- always appears bare (89%) — it may be a derivational prefix.

    # Count ch-initial roots
    ch_roots = [(r, c) for r, c in root_counts.items() if r.startswith('ch') and c >= 10]
    ch_roots.sort(key=lambda x: -x[1])

    print(f"  ch-INITIAL ROOTS (N≥10): {len(ch_roots)}")
    print(f"  {'Root':12s} {'N':>5s}  {'After ch-':10s} {'After-N':>7s}")
    for root, count in ch_roots:
        after = root[2:] if len(root) > 2 else '(bare)'
        after_n = root_counts.get(after, 0) if after != '(bare)' else 0
        print(f"  {root:12s} {count:5d}  {after:10s} {after_n:7d}")

    # Count h-initial roots (verbal class)
    h_roots = [(r, c) for r, c in root_counts.items()
               if r.startswith('h') and not r.startswith('ch') and c >= 10]
    h_roots.sort(key=lambda x: -x[1])

    print(f"\n  h-INITIAL ROOTS (non-ch, N≥10): {len(h_roots)}")
    print(f"  {'Root':12s} {'N':>5s}  {'After h-':10s} {'After-N':>7s}")
    for root, count in h_roots:
        after = root[1:] if len(root) > 1 else '(bare)'
        after_n = root_counts.get(after, 0) if after != '(bare)' else 0
        print(f"  {root:12s} {count:5d}  {after:10s} {after_n:7d}")

    # Proposed revised model:
    print(f"\n  ══════════════════════════════════════════════════")
    print(f"  PROPOSED REVISED MORPHOLOGICAL MODEL")
    print(f"  ══════════════════════════════════════════════════")
    print(f"")
    print(f"  OLD MODEL:")
    print(f"    WORD = [prefix] + [gallows] + ROOT + [suffix]")
    print(f"    prefix ∈ {{qo, q, so, do, o, d, s, y}}")
    print(f"    gallows ∈ {{k, t, f, p}} (classifiers)")
    print(f"    ROOT = semantic kernel")
    print(f"")
    print(f"  REVISED MODEL:")
    print(f"    WORD = [GRAM-PREFIX] + [GALLOWS-DET] + [DERIV-PREFIX] + STEM + [SUFFIX]")
    print(f"    GRAM-PREFIX ∈ {{qo, q, o, d, y}}  (grammatical: relative, article, genitive, adj)")
    print(f"    GALLOWS-DET ∈ {{k, t, f, p}}       (classifier determinative)")
    print(f"    DERIV-PREFIX ∈ {{ch-, h-, sh-, l-}} (derivational prefixes)")
    print(f"      ch- = nominalizer/agent  (ch+e='make-this', ch+o='substance')")
    print(f"      h-  = verbalizer          (h+e='fall', h+o='face/turn', h+ed='pour')")
    print(f"      sh- = causative?           (sh+e='tree/plant', sh+eo='dry')")
    print(f"      l-  = instrumental?        (l+ch='remedy-making', l+sh='remedy-occur')")
    print(f"    STEM = core lexical root (e, o, ed, eo, od, ol, al, am, ar, es...)")
    print(f"    SUFFIX = inflectional marker")
    print(f"")
    print(f"  KEY INSIGHT: What we've been calling separate roots (ch, che, cho,")
    print(f"  chol, he, ho, hed, she, sheo, lch) may actually be DERIVATIONAL")
    print(f"  PREFIX + STEM combinations, not atomic roots.")
    print(f"")

    # Test this model: re-parse some common words
    print(f"  RE-PARSE EXAMPLES under revised model:")
    test_words = [
        'qokeedy', 'shedy', 'otedy', 'chedy', 'qokchedy',
        'dam', 'otar', 'olkedy', 'sokol', 'shedair',
        'dshedy', 'qokain', 'schedy', 'dalchedy'
    ]
    
    for word in test_words:
        d = full_decompose(word)
        root = d['root']
        
        # Try to split root into derivational prefix + stem
        deriv = ''
        stem = root
        for dp in ['ch', 'sh', 'h', 'l']:
            if root.startswith(dp) and len(root) > len(dp):
                deriv = dp + '-'
                stem = root[len(dp):]
                break
        
        gram = d['prefix'] or '∅'
        det = d['determinative'] or '∅'
        sfx = d['suffix'] or '∅'
        
        old_parse = f"[{gram}]+[{det}]+{root}+[{sfx}]"
        new_parse = f"[{gram}]+[{det}]+{deriv}{stem}+[{sfx}]" if deriv else old_parse
        
        print(f"  {word:16s} OLD: {old_parse:35s} NEW: {new_parse}")

    return {}


# ══════════════════════════════════════════════════════════════════
# CHI-SQUARED SECTION CLUSTERING
# ══════════════════════════════════════════════════════════════════

def run_chi_squared(tokens):
    print()
    print("=" * 76)
    print("CHI-SQUARED SECTION CLUSTERING")
    print("=" * 76)
    print()
    print("For every root with N≥20, test whether its section distribution")
    print("is significantly non-random (chi-squared goodness of fit).")
    print()

    # Section sizes
    section_counts = Counter()
    root_sections = defaultdict(Counter)
    root_counts = Counter()
    for word, section, folio in tokens:
        section_counts[section] += 1
        d = full_decompose(word)
        root = d['root']
        root_sections[root][section] += 1
        root_counts[root] += 1

    total = sum(section_counts.values())
    sections = sorted(section_counts.keys())
    expected_fracs = {s: section_counts[s]/total for s in sections}

    # Chi-squared test for each root
    results = []
    for root in sorted(root_counts.keys(), key=lambda r: -root_counts[r]):
        n = root_counts[root]
        if n < 20: continue

        chi2 = 0
        for s in sections:
            observed = root_sections[root].get(s, 0)
            expected = n * expected_fracs[s]
            if expected > 0:
                chi2 += (observed - expected)**2 / expected

        # Degrees of freedom = number of sections - 1
        df = len(sections) - 1
        
        # Approximate p-value using chi-squared CDF
        # For df=6 (7 sections - 1), critical values:
        # p<0.05: chi2 > 12.59
        # p<0.01: chi2 > 16.81
        # p<0.001: chi2 > 22.46
        if df == 6:
            if chi2 > 22.46: p_approx = '<0.001'
            elif chi2 > 16.81: p_approx = '<0.01'
            elif chi2 > 12.59: p_approx = '<0.05'
            else: p_approx = '>0.05'
        elif df == 5:
            if chi2 > 20.52: p_approx = '<0.001'
            elif chi2 > 15.09: p_approx = '<0.01'
            elif chi2 > 11.07: p_approx = '<0.05'
            else: p_approx = '>0.05'
        else:
            # Generic: chi2 > 2*df is roughly p<0.05 for large df
            if chi2 > 3*df: p_approx = '<0.001'
            elif chi2 > 2.5*df: p_approx = '<0.01'
            elif chi2 > 2*df: p_approx = '<0.05'
            else: p_approx = '>0.05'

        # Find most enriched section
        max_enrich = 0
        max_sec = ''
        for s in sections:
            if expected_fracs[s] > 0:
                enrich = (root_sections[root].get(s, 0) / n) / expected_fracs[s]
                if enrich > max_enrich:
                    max_enrich = enrich
                    max_sec = s

        results.append((root, n, chi2, p_approx, max_sec, max_enrich))

    # Display results
    sig_count = 0
    print(f"  {'Root':12s} {'N':>5s}  {'χ²':>8s}  {'p':>8s}  {'Peak section':12s} {'Enrich':>7s}")
    for root, n, chi2, p_approx, max_sec, max_enrich in results[:60]:
        sig = "*" if '<' in p_approx else " "
        if '<' in p_approx: sig_count += 1
        print(f"  {root:12s} {n:5d}  {chi2:8.1f}  {p_approx:>8s}{sig} {max_sec:12s} {max_enrich:6.2f}x")

    total_tested = len(results)
    print(f"\n  SUMMARY: {sig_count}/{total_tested} roots show significant section clustering at p<0.05")
    print(f"  Expected by chance (5%): {total_tested * 0.05:.0f}")
    
    if sig_count > total_tested * 0.1:
        print(f"  → Significantly more roots cluster than expected by chance.")
        print(f"  → Root-section associations are REAL, even if we can't name them.")
    elif sig_count > total_tested * 0.05:
        print(f"  → About what we'd expect by chance. Section clustering is weak.")
    else:
        print(f"  → Fewer than chance. Roots are evenly distributed across sections.")

    # Bonferroni correction
    bonf = sum(1 for _, _, chi2, _, _, _ in results if chi2 > 22.46)  # rough p<0.001
    print(f"  Bonferroni-surviving (p<0.001): {bonf}/{total_tested}")

    return results


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("compound_decomposition: COMPOUND DECOMPOSITION, h-VERBAL & BARE CLASS")
    print("=" * 76)

    tokens = load_all_tokens()
    print(f"Loaded {len(tokens)} word tokens\n")

    r_29a = run_h_prefix_test(tokens)
    r_29b = run_compound_decomposition(tokens)
    r_29c = run_bare_class_analysis(tokens)
    r_29d = run_revised_model(tokens)
    r_29e = run_chi_squared(tokens)

    # Final summary
    print()
    print("=" * 76)
    print("compound_decomposition: KEY TAKEAWAYS")
    print("=" * 76)
    print()
    print("  1. h- verbal prefix hypothesis: see 29a results")
    print("  2. Compound decomposition: see 29b split table")
    print("  3. BARE class: see 29c following-root patterns")
    print("  4. Revised model: prefix + det + deriv-prefix + stem + suffix")
    print("  5. Chi-squared: see 29e section clustering significance")

    results = {
        'h_prefix': r_29a,
        'compounds_found': sum(1 for _, _, p1, _, _, _, _ in r_29b if p1 is not None),
        'compounds_total': len(r_29b),
    }
    json.dump(results, open(Path("results/compound_decomposition_results.json"), 'w'), indent=2, default=str)
    print(f"\n  Results saved to results/compound_decomposition_results.json")


if __name__ == '__main__':
    import contextlib
    outpath = Path("results/compound_decomposition_output.txt")
    with open(outpath, 'w', encoding='utf-8') as f:
        with contextlib.redirect_stdout(f):
            main()
    print(open(outpath, encoding='utf-8').read())
