#!/usr/bin/env python3
"""
Phase 34 — ARE THE REMAINING MODEL ASSUMPTIONS VALID?
======================================================

Phases 32-33 caught a suffix artifact that corrupted 4+ findings.
The same class of bug could exist in OTHER parts of the pipeline:

  1. GRAM PREFIX 's' steals from deriv prefix 'sh' (2700 tokens!)
  2. GRAM PREFIX 'do'/'so' may steal from deriv+stem combinations
  3. E-CHAIN COLLAPSE (ee→e) destroys potentially meaningful structure
  4. STEM 'e' at 24.7% may be parsing residue, not a real morpheme

Tests:
  34a) GRAM PREFIX ARTIFACT — Is 's' a real gram prefix or just half of 'sh'?
       Test: do gram prefix 's' tokens WITHOUT deriv 'h' behave differently
       from 'sh' tokens? If 's' is only meaningful before 'h', it's not real.
  34b) ALL GRAM PREFIX VALIDATION — For each gram prefix, check if it has
       independent distributional evidence or is always paired with a
       deriv prefix
  34c) E-CHAIN COLLAPSE — What info does ee→e destroy? Are 'ee' and 'e'
       distributed the same way? Test without collapsing.
  34d) IS STEM 'E' REAL? — Is there evidence that 'e' is a meaningful
       morpheme vs. the minimum residue after stripping?
  34e) SUFFIX FUNCTIONAL GROUPINGS — Do the 10 validated suffixes cluster
       naturally by distribution?
"""

import re, json, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
from common import collapse_echains, gallows_base, load_all_tokens, load_folio_lines, strip_gallows

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
SUFFIXES_SHORT = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']
DERIV_PREFIXES_ORDER = ['lch','lsh','ch','sh','l','h']




def decompose(word, do_collapse=True):
    stripped, gals = strip_gallows(word)
    collapsed = collapse_echains(stripped) if do_collapse else stripped
    bases = [gallows_base(g) for g in gals]
    # Gram prefix
    pfx = ""
    temp = collapsed
    for pf in PREFIXES:
        if temp.startswith(pf) and len(temp) > len(pf)+1:
            pfx = pf; temp = temp[len(pf):]; break
    # Suffix
    sfx = ""
    for sf in SUFFIXES_SHORT:
        if temp.endswith(sf) and len(temp) > len(sf):
            sfx = sf; temp = temp[:-len(sf)]; break
    # Deriv prefix
    deriv = ""
    for dp in DERIV_PREFIXES_ORDER:
        if temp.startswith(dp) and len(temp) > len(dp):
            deriv = dp; temp = temp[len(dp):]; break
    return dict(original=word, gram_prefix=pfx, det=bases[0] if bases else "",
                deriv_prefix=deriv, stem=temp, suffix=sfx,
                all_gallows=bases)


# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════

FOLIO_DIR = Path("folios")





# ══════════════════════════════════════════════════════════════════
# 34a: IS GRAM PREFIX 'S' REAL?
# ══════════════════════════════════════════════════════════════════

def run_s_prefix_test(tokens):
    print("=" * 76)
    print("PHASE 34a: IS GRAM PREFIX 's' A REAL MORPHEME?")
    print("=" * 76)
    print()
    print("Parser splits 'shedy' as s+h+e+dy. But 'sh' is a deriv prefix.")
    print("If 's' only appears before 'h', it's not a real gram prefix —")
    print("it's just the first letter of deriv prefix 'sh'.")
    print()

    # Classify s-prefix tokens
    s_with_h = Counter()  # s+h: what stems?
    s_without_h = Counter()  # s+other: what derivs?
    s_without_h_stem = Counter()
    s_without_h_words = Counter()

    for word, section, folio in tokens:
        d = decompose(word)
        if d['gram_prefix'] == 's':
            if d['deriv_prefix'] == 'h':
                s_with_h[d['stem']] += 1
            else:
                s_without_h[d['deriv_prefix'] or '∅'] += 1
                s_without_h_stem[d['stem']] += 1
                s_without_h_words[word] += 1

    total_s = sum(s_with_h.values()) + sum(s_without_h.values())
    n_s_h = sum(s_with_h.values())
    n_s_other = sum(s_without_h.values())

    print(f"  Total gram_prefix='s' tokens: {total_s}")
    print(f"  s + deriv='h': {n_s_h} ({100*n_s_h/total_s:.0f}%)")
    print(f"  s + deriv=other: {n_s_other} ({100*n_s_other/total_s:.0f}%)")
    print()

    if n_s_other > 0:
        print(f"  s + non-h deriv prefixes: {dict(s_without_h.most_common())}")
        print(f"  s + non-h stems: {dict(s_without_h_stem.most_common(10))}")
        print(f"  s + non-h top words: {dict(s_without_h_words.most_common(10))}")
    print()

    # KEY TEST: Compare section distributions
    # If s+h tokens are just 'sh' (one morpheme), their section distribution
    # should match 'sh' as deriv prefix in other contexts (e.g., from Phase 33)
    s_h_sections = Counter()
    sh_only_sections = Counter()
    s_only_sections = Counter()

    for word, section, folio in tokens:
        d = decompose(word)
        if d['gram_prefix'] == 's' and d['deriv_prefix'] == 'h':
            s_h_sections[section] += 1
        elif d['gram_prefix'] == '' and d['deriv_prefix'] == 'sh':
            sh_only_sections[section] += 1
        elif d['gram_prefix'] == 's' and d['deriv_prefix'] != 'h':
            s_only_sections[section] += 1

    sections = ['herbal-A', 'herbal-B', 'pharma', 'bio', 'text', 'cosmo', 'zodiac']
    n_sh = sum(s_h_sections.values())
    n_sh_only = sum(sh_only_sections.values())
    n_s_only = sum(s_only_sections.values())

    print(f"  SECTION DISTRIBUTIONS:")
    print(f"    {'Section':12s} {'s+h':>7s} {'∅+sh':>7s} {'s+other':>7s}")
    for sec in sections:
        a = 100 * s_h_sections.get(sec, 0) / n_sh if n_sh > 0 else 0
        b = 100 * sh_only_sections.get(sec, 0) / n_sh_only if n_sh_only > 0 else 0
        c = 100 * s_only_sections.get(sec, 0) / n_s_only if n_s_only > 0 else 0
        print(f"    {sec:12s} {a:6.0f}% {b:6.0f}% {c:6.0f}%")

    # Cosine similarity
    def cosine(a_dict, b_dict, keys):
        a = [a_dict.get(k, 0) for k in keys]
        b = [b_dict.get(k, 0) for k in keys]
        dot = sum(x*y for x, y in zip(a, b))
        na = sum(x**2 for x in a) ** 0.5
        nb = sum(x**2 for x in b) ** 0.5
        return dot / (na * nb) if na > 0 and nb > 0 else 0

    cos_sh_vs_sh_only = cosine(s_h_sections, sh_only_sections, sections)
    cos_s_only_vs_sh = cosine(s_only_sections, s_h_sections, sections)

    print(f"\n    Cosine(s+h, ∅+sh): {cos_sh_vs_sh_only:.3f}")
    print(f"    Cosine(s+other, s+h): {cos_s_only_vs_sh:.3f}")

    # LINE POSITION TEST: s+h vs ∅+sh — do they have the same position?
    folio_lines = load_folio_lines()
    s_h_pos = []
    sh_pos = []
    s_other_pos = []

    for lid, section, words in folio_lines:
        if len(words) < 3: continue
        for i, w in enumerate(words):
            d = decompose(w)
            rel_pos = i / (len(words) - 1) if len(words) > 1 else 0.5
            if d['gram_prefix'] == 's' and d['deriv_prefix'] == 'h':
                s_h_pos.append(rel_pos)
            elif d['gram_prefix'] == '' and d['deriv_prefix'] == 'sh':
                sh_pos.append(rel_pos)
            elif d['gram_prefix'] == 's' and d['deriv_prefix'] != 'h':
                s_other_pos.append(rel_pos)

    print(f"\n  LINE POSITION:")
    for label, pos in [("s+h (=sh?)", s_h_pos), ("∅+sh", sh_pos), ("s+other", s_other_pos)]:
        if not pos: continue
        n = len(pos)
        mean = sum(pos) / n
        init = 100 * sum(1 for p in pos if p < 0.2) / n
        final = 100 * sum(1 for p in pos if p > 0.8) / n
        print(f"    {label:15s} N={n:5d}  mean={mean:.3f}  init<.2={init:.0f}%  final>.8={final:.0f}%")

    # VERDICT
    print(f"\n  ═══ VERDICT ═══")
    if n_s_other < 0.15 * total_s:
        print(f"  's' as gram prefix is HIGHLY SUSPECT — {100*n_s_other/total_s:.0f}% non-h usage")
        print(f"  Most 's+h' words are likely just deriv='sh' being mis-split")
    else:
        print(f"  's' has {100*n_s_other/total_s:.0f}% non-h usage — may be a real gram prefix")

    return {}


# ══════════════════════════════════════════════════════════════════
# 34b: ALL GRAM PREFIX VALIDATION
# ══════════════════════════════════════════════════════════════════

def run_all_gram_prefix_validation(tokens):
    print()
    print("=" * 76)
    print("PHASE 34b: ARE ALL GRAM PREFIXES REAL?")
    print("=" * 76)
    print()
    print("For each gram prefix, check: what deriv prefix follows?")
    print("If a gram prefix ALWAYS pairs with the same deriv prefix,")
    print("they might be one morpheme, not two.")
    print()

    gpfx_deriv = defaultdict(Counter)
    gpfx_total = Counter()
    for word, section, folio in tokens:
        d = decompose(word)
        gp = d['gram_prefix'] or '∅'
        dp = d['deriv_prefix'] or '∅'
        gpfx_deriv[gp][dp] += 1
        gpfx_total[gp] += 1

    for gp in ['∅', 'qo', 'q', 'so', 'do', 'o', 'd', 's', 'y']:
        n = gpfx_total.get(gp, 0)
        if n < 50: continue
        derivs = gpfx_deriv[gp]
        top = derivs.most_common(5)
        top_str = ", ".join(f"{dp}={c}({100*c/n:.0f}%)" for dp, c in top)
        # Entropy of deriv given this gram prefix
        entropy = 0
        for dp, c in derivs.items():
            p = c / n
            if p > 0:
                entropy -= p * math.log2(p)
        print(f"  gpfx='{gp}' (N={n:5d}): H(deriv|gpfx)={entropy:.2f} bits")
        print(f"    {top_str}")
        print()

    # SPECIFIC CONCERN: do compound gram prefixes overlap with deriv?
    # 'so' = s + o? or 'so' = real prefix?
    # 'do' = d + o? or 'do' = real prefix?
    print(f"  OVERLAP CHECK:")
    print(f"  Are 'so','do' just 's'/'d' + 'o' (two gram prefixes)?")
    print()

    # Compare: words with gpfx='so' vs words with gpfx='s' that have stem starting with 'o'
    so_stemstart = Counter()
    s_stemstart = Counter()
    do_stemstart = Counter()
    d_stemstart = Counter()

    for word, section, folio in tokens:
        d = decompose(word)
        if d['gram_prefix'] == 'so':
            so_stemstart[d['stem'][:2] if d['stem'] else '?'] += 1
        elif d['gram_prefix'] == 's':
            s_stemstart[d['stem'][:2] if d['stem'] else '?'] += 1
        elif d['gram_prefix'] == 'do':
            do_stemstart[d['stem'][:2] if d['stem'] else '?'] += 1
        elif d['gram_prefix'] == 'd':
            d_stemstart[d['stem'][:2] if d['stem'] else '?'] += 1

    print(f"  gpfx='so' stem starts: {dict(so_stemstart.most_common(5))}")
    print(f"  gpfx='s' stem starts:  {dict(s_stemstart.most_common(5))}")
    print(f"  gpfx='do' stem starts: {dict(do_stemstart.most_common(5))}")
    print(f"  gpfx='d' stem starts:  {dict(d_stemstart.most_common(5))}")

    return {}


# ══════════════════════════════════════════════════════════════════
# 34c: E-CHAIN COLLAPSE AUDIT
# ══════════════════════════════════════════════════════════════════

def run_echain_test(tokens):
    print()
    print("=" * 76)
    print("PHASE 34c: DOES E-CHAIN COLLAPSE DESTROY MEANINGFUL INFO?")
    print("=" * 76)
    print()

    # Count e-chain lengths in the raw corpus (after gallows removal)
    echain_lengths = Counter()
    echain_contexts = defaultdict(Counter)  # context → echain_length distribution

    for word, section, folio in tokens:
        stripped, gals = strip_gallows(word)
        # Find all e-chains
        for m in re.finditer(r'(e+)', stripped):
            elen = len(m.group(1))
            echain_lengths[elen] += 1
            # Context: what's before and after?
            before = stripped[max(0,m.start()-1):m.start()] if m.start() > 0 else '^'
            after = stripped[m.end():m.end()+1] if m.end() < len(stripped) else '$'
            echain_contexts[(before, after)][elen] += 1

    print(f"  E-chain length distribution (after gallows removal):")
    total_chains = sum(echain_lengths.values())
    for length, count in sorted(echain_lengths.items()):
        pct = 100 * count / total_chains
        print(f"    e×{length}: {count:6d} ({pct:5.1f}%)")

    # KEY: do different e-chain lengths have different SECTION distributions?
    print(f"\n  SECTION DISTRIBUTION by e-chain length:")
    echain_section = defaultdict(Counter)
    for word, section, folio in tokens:
        stripped, gals = strip_gallows(word)
        max_elen = 0
        for m in re.finditer(r'(e+)', stripped):
            max_elen = max(max_elen, len(m.group(1)))
        if max_elen > 0:
            echain_section[min(max_elen, 4)][section] += 1

    sections = ['herbal-A', 'herbal-B', 'pharma', 'bio', 'text', 'cosmo', 'zodiac']
    print(f"    {'elen':5s}", end="")
    for sec in sections:
        print(f" {sec:>9s}", end="")
    print()
    for elen in [1, 2, 3, 4]:
        n = sum(echain_section[elen].values())
        if n < 50: continue
        print(f"    e×{elen:1d}  ", end="")
        for sec in sections:
            pct = 100 * echain_section[elen].get(sec, 0) / n
            print(f" {pct:8.0f}%", end="")
        print(f"  (N={n})")

    # KEY TEST: Parse WITH and WITHOUT e-chain collapse
    # Does collapsing change the stem distribution?
    print(f"\n  STEM COMPARISON: with vs without e-collapse:")
    stem_collapsed = Counter()
    stem_raw = Counter()
    for word, section, folio in tokens:
        dc = decompose(word, do_collapse=True)
        dr = decompose(word, do_collapse=False)
        stem_collapsed[dc['stem']] += 1
        stem_raw[dr['stem']] += 1

    # How many tokens change stem?
    n_changed = 0
    for word, section, folio in tokens:
        dc = decompose(word, do_collapse=True)
        dr = decompose(word, do_collapse=False)
        if dc['stem'] != dr['stem']:
            n_changed += 1

    print(f"    Tokens whose stem changes: {n_changed} ({100*n_changed/len(tokens):.1f}%)")
    print(f"\n    Top stems WITHOUT collapse:")
    for s, c in stem_raw.most_common(15):
        print(f"      {s:12s}: {c:6d}")
    print(f"\n    Top stems WITH collapse:")
    for s, c in stem_collapsed.most_common(15):
        print(f"      {s:12s}: {c:6d}")

    # Are 'e' and 'ee' the same or different?
    print(f"\n  SPECIFIC: Are 'e' and 'ee' the same morpheme?")
    e_sec = Counter()
    ee_sec = Counter()
    for word, section, folio in tokens:
        dr = decompose(word, do_collapse=False)
        if dr['stem'] == 'e':
            e_sec[section] += 1
        elif dr['stem'] == 'ee':
            ee_sec[section] += 1

    n_e = sum(e_sec.values())
    n_ee = sum(ee_sec.values())
    print(f"    stem='e': {n_e}, stem='ee': {n_ee}")
    if n_e > 0 and n_ee > 0:
        print(f"    {'Section':12s} {'e':>6s} {'ee':>6s}")
        for sec in sections:
            a = 100 * e_sec.get(sec, 0) / n_e
            b = 100 * ee_sec.get(sec, 0) / n_ee
            print(f"    {sec:12s} {a:5.0f}% {b:5.0f}%")

    # Suffix preference
    e_sfx = Counter()
    ee_sfx = Counter()
    for word, section, folio in tokens:
        dr = decompose(word, do_collapse=False)
        if dr['stem'] == 'e':
            e_sfx[dr['suffix'] or '∅'] += 1
        elif dr['stem'] == 'ee':
            ee_sfx[dr['suffix'] or '∅'] += 1

    print(f"\n    Suffix preference:")
    print(f"    stem='e': {dict(e_sfx.most_common(6))}")
    print(f"    stem='ee': {dict(ee_sfx.most_common(6))}")

    return {}


# ══════════════════════════════════════════════════════════════════
# 34d: IS STEM 'E' A REAL MORPHEME?
# ══════════════════════════════════════════════════════════════════

def run_stem_e_test(tokens):
    print()
    print("=" * 76)
    print("PHASE 34d: IS STEM 'e' A REAL MORPHEME OR PARSING RESIDUE?")
    print("=" * 76)
    print()
    print("24.7% of tokens have stem='e'. This is suspicious — it could be")
    print("the minimum leftover after stripping all affixes.")
    print()

    # Test 1: Does stem 'e' have nonrandom section distribution?
    stem_sections = defaultdict(Counter)
    stem_totals = Counter()
    for word, section, folio in tokens:
        d = decompose(word)
        stem = d['stem']
        stem_sections[stem][section] += 1
        stem_totals[stem] += 1

    sections = ['herbal-A', 'herbal-B', 'pharma', 'bio', 'text', 'cosmo', 'zodiac']
    corpus_dist = Counter()
    for word, section, folio in tokens:
        corpus_dist[section] += 1
    corpus_total = sum(corpus_dist.values())

    print(f"  Section distribution of stem 'e' vs corpus:")
    print(f"    {'Section':12s} {'e':>6s} {'corpus':>7s} {'diff':>6s}")
    chi2_e = 0
    for sec in sections:
        e_pct = 100 * stem_sections['e'].get(sec, 0) / stem_totals['e']
        c_pct = 100 * corpus_dist.get(sec, 0) / corpus_total
        diff = e_pct - c_pct
        print(f"    {sec:12s} {e_pct:5.0f}% {c_pct:6.0f}% {diff:+5.0f}")
        obs = stem_sections['e'].get(sec, 0)
        exp = stem_totals['e'] * corpus_dist.get(sec, 0) / corpus_total
        if exp > 0:
            chi2_e += (obs - exp) ** 2 / exp

    df = len(sections) - 1
    print(f"\n    Chi2(e vs corpus): {chi2_e:.1f} (df={df})")
    print(f"    {'→ stem e differs from corpus' if chi2_e > 18.5 else '→ stem e matches corpus'}")

    # Compare with other frequent stems
    print(f"\n  Chi2 for top stems (how much does each differ from corpus?):")
    chi2_vals = []
    for stem in ['e', 'a', 'o', 'ar', 'ol', 'al', 'd', 'eo', 'or', 'ed',
                  'ch', 'l', 'h', 'am', 'es']:
        n = stem_totals.get(stem, 0)
        if n < 100: continue
        chi2 = 0
        for sec in sections:
            obs = stem_sections[stem].get(sec, 0)
            exp = n * corpus_dist.get(sec, 0) / corpus_total
            if exp > 0:
                chi2 += (obs - exp) ** 2 / exp
        chi2_vals.append((stem, n, chi2))
    
    chi2_vals.sort(key=lambda x: -x[2])
    for stem, n, chi2 in chi2_vals:
        sig = "***" if chi2 > 18.5 else "   "
        print(f"    {stem:6s} (N={n:5d}): chi2={chi2:8.1f} {sig}")

    # Test 2: If stem 'e' is just residue, it should have the SAME
    # suffix distribution regardless of deriv prefix (since the "stem"
    # isn't contributing meaning)
    print(f"\n  Suffix distribution of stem 'e' by deriv prefix:")
    e_sfx_by_deriv = defaultdict(Counter)
    for word, section, folio in tokens:
        d = decompose(word)
        if d['stem'] == 'e':
            dp = d['deriv_prefix'] or '∅'
            e_sfx_by_deriv[dp][d['suffix'] or '∅'] += 1

    all_sfxs = sorted(set(s for c in e_sfx_by_deriv.values() for s in c.keys()),
                       key=lambda s: -sum(c.get(s, 0) for c in e_sfx_by_deriv.values()))[:8]

    hdr = f"    {'deriv':6s} {'N':>5s}"
    for sf in all_sfxs:
        hdr += f" {sf:>6s}"
    print(hdr)

    for dp in ['∅', 'h', 'ch', 'sh', 'l', 'lch', 'lsh']:
        n = sum(e_sfx_by_deriv[dp].values())
        if n < 20: continue
        row = f"    {dp:6s} {n:5d}"
        for sf in all_sfxs:
            c = e_sfx_by_deriv[dp].get(sf, 0)
            row += f" {100*c/n:5.0f}%"
        print(row)

    # Test 3: minimal stem test — what if 'e' is just the connector
    # between prefix and suffix? If so, words parsed as pfx+deriv+e+sfx
    # should be THE SAME as pfx+deriv+sfx with no stem.
    # Count: how many words are JUST prefix+deriv+e+suffix with nothing else?
    just_e = 0
    e_total = 0
    for word, section, folio in tokens:
        d = decompose(word)
        if d['stem'] == 'e':
            e_total += 1
            # Is 'e' the ONLY vocalic content?
            stripped, gals = strip_gallows(word)
            non_e = re.sub(r'e+', '', stripped)
            non_e = re.sub(r'[aio]', '', non_e)
            # If everything except consonants and 'e' is accounted for by
            # prefixes/suffixes, then 'e' is just connecting tissue
            just_e += 1

    print(f"\n  Total stem='e' tokens: {e_total}")

    return {}


# ══════════════════════════════════════════════════════════════════
# 34e: SUFFIX FUNCTIONAL GROUPINGS
# ══════════════════════════════════════════════════════════════════

def run_suffix_groupings(tokens):
    print()
    print("=" * 76)
    print("PHASE 34e: DO THE 10 SUFFIXES CLUSTER FUNCTIONALLY?")
    print("=" * 76)
    print()

    # Build suffix × section distribution matrix
    suffix_section = defaultdict(Counter)
    suffix_total = Counter()
    for word, section, folio in tokens:
        d = decompose(word)
        sfx = d['suffix'] or '∅'
        suffix_section[sfx][section] += 1
        suffix_total[sfx] += 1

    sections = ['herbal-A', 'herbal-B', 'pharma', 'bio', 'text', 'cosmo', 'zodiac']
    sfxs = ['dy', 'y', 'ol', 'or', 'ar', 'al', 'aiin', 'ain', 'iin', 'in', '∅']

    print(f"  Section distribution by suffix:")
    print(f"    {'sfx':6s} {'N':>6s}", end="")
    for sec in sections:
        print(f" {sec[:6]:>6s}", end="")
    print()
    for sfx in sfxs:
        n = suffix_total.get(sfx, 0)
        if n < 50: continue
        print(f"    {sfx:6s} {n:6d}", end="")
        for sec in sections:
            pct = 100 * suffix_section[sfx].get(sec, 0) / n
            print(f" {pct:5.0f}%", end="")
        print()

    # Pairwise cosine similarity between suffixes
    def cosine(a_dict, b_dict, keys):
        a = [a_dict.get(k, 0) for k in keys]
        b = [b_dict.get(k, 0) for k in keys]
        dot = sum(x*y for x, y in zip(a, b))
        na = sum(x**2 for x in a) ** 0.5
        nb = sum(x**2 for x in b) ** 0.5
        return dot / (na * nb) if na > 0 and nb > 0 else 0

    print(f"\n  Pairwise cosine similarity (section distribution):")
    active_sfxs = [s for s in sfxs if suffix_total.get(s, 0) >= 100]
    print(f"    {'':6s}", end="")
    for s in active_sfxs:
        print(f" {s:>5s}", end="")
    print()
    for s1 in active_sfxs:
        print(f"    {s1:6s}", end="")
        for s2 in active_sfxs:
            cos = cosine(suffix_section[s1], suffix_section[s2], sections)
            print(f" {cos:5.2f}", end="")
        print()

    # Build suffix × deriv prefix distribution
    print(f"\n  Suffix × deriv prefix distribution:")
    suffix_deriv = defaultdict(Counter)
    for word, section, folio in tokens:
        d = decompose(word)
        sfx = d['suffix'] or '∅'
        dp = d['deriv_prefix'] or '∅'
        suffix_deriv[sfx][dp] += 1

    derivs = ['∅', 'h', 'ch', 'sh', 'l']
    print(f"    {'sfx':6s} {'N':>6s}", end="")
    for dp in derivs:
        print(f" {dp:>6s}", end="")
    print()
    for sfx in sfxs:
        n = suffix_total.get(sfx, 0)
        if n < 50: continue
        print(f"    {sfx:6s} {n:6d}", end="")
        for dp in derivs:
            pct = 100 * suffix_deriv[sfx].get(dp, 0) / n
            print(f" {pct:5.0f}%", end="")
        print()

    # Build suffix × gram prefix distribution
    print(f"\n  Suffix × gram prefix distribution:")
    suffix_gpfx = defaultdict(Counter)
    for word, section, folio in tokens:
        d = decompose(word)
        sfx = d['suffix'] or '∅'
        gp = d['gram_prefix'] or '∅'
        suffix_gpfx[sfx][gp] += 1

    gpfxs = ['∅', 'qo', 'q', 'o', 'd', 's', 'y', 'so', 'do']
    print(f"    {'sfx':6s} {'N':>6s}", end="")
    for gp in gpfxs:
        print(f" {gp:>5s}", end="")
    print()
    for sfx in sfxs:
        n = suffix_total.get(sfx, 0)
        if n < 50: continue
        print(f"    {sfx:6s} {n:6d}", end="")
        for gp in gpfxs:
            pct = 100 * suffix_gpfx[sfx].get(gp, 0) / n
            print(f" {pct:4.0f}%", end="")
        print()

    # LINE POSITION by suffix
    print(f"\n  Line position by suffix:")
    folio_lines = load_folio_lines()
    sfx_pos = defaultdict(list)
    for lid, section, words in folio_lines:
        if len(words) < 4: continue
        for i, w in enumerate(words):
            d = decompose(w)
            sfx = d['suffix'] or '∅'
            rel_pos = i / (len(words) - 1) if len(words) > 1 else 0.5
            sfx_pos[sfx].append(rel_pos)

    print(f"    {'sfx':6s} {'N':>6s} {'Mean':>6s} {'Init':>6s} {'Final':>6s}")
    for sfx in sfxs:
        positions = sfx_pos.get(sfx, [])
        if len(positions) < 100: continue
        n = len(positions)
        mean = sum(positions) / n
        init = 100 * sum(1 for p in positions if p < 0.2) / n
        final = 100 * sum(1 for p in positions if p > 0.8) / n
        print(f"    {sfx:6s} {n:6d} {mean:6.3f} {init:5.0f}% {final:5.0f}%")

    # HIERARCHICAL CLUSTERING: -aiin vs -ain vs -iin vs -in
    print(f"\n  ═══ ARE -aiin/-ain/-iin/-in RELATED? ═══")
    in_group = ['aiin', 'ain', 'iin', 'in']
    print(f"  Cosine similarities:")
    for i, s1 in enumerate(in_group):
        for s2 in in_group[i+1:]:
            cos = cosine(suffix_section[s1], suffix_section[s2], sections)
            cos_d = cosine(suffix_deriv[s1], suffix_deriv[s2], derivs)
            print(f"    {s1:5s} vs {s2:5s}: section={cos:.3f}  deriv={cos_d:.3f}")

    print(f"\n  ═══ ARE -ar/-or/-al/-ol RELATED? ═══")
    r_group = ['ar', 'or', 'al', 'ol']
    for i, s1 in enumerate(r_group):
        for s2 in r_group[i+1:]:
            cos = cosine(suffix_section[s1], suffix_section[s2], sections)
            cos_d = cosine(suffix_deriv[s1], suffix_deriv[s2], derivs)
            print(f"    {s1:5s} vs {s2:5s}: section={cos:.3f}  deriv={cos_d:.3f}")

    return {}


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("PHASE 34: ARE THE REMAINING MODEL ASSUMPTIONS VALID?")
    print("=" * 76)

    tokens = load_all_tokens()
    print(f"Loaded {len(tokens)} word tokens\n")

    run_s_prefix_test(tokens)
    run_all_gram_prefix_validation(tokens)
    run_echain_test(tokens)
    run_stem_e_test(tokens)
    run_suffix_groupings(tokens)

    json.dump({'status': 'complete'},
              open(Path("results/phase34_results.json"), 'w'), indent=2)
    print(f"\n  Results saved to results/phase34_results.json")


if __name__ == '__main__':
    import contextlib
    outpath = Path("results/phase34_output.txt")
    with open(outpath, 'w', encoding='utf-8') as f:
        with contextlib.redirect_stdout(f):
            main()
    print(open(outpath, encoding='utf-8').read())
