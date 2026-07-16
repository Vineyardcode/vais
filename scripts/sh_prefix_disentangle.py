#!/usr/bin/env python3
"""
DISENTANGLE h- FROM sh-: IS 's' A REAL GRAM PREFIX?
================================================================

morphology_model_audit discovered that gram prefix 's' completely shadows deriv prefix 'sh':
  - ZERO tokens have gpfx='' AND deriv='sh'
  - 97.6% of deriv='h' tokens have gpfx='s' (2700/2766)
  - The 's' parser steals the first char of 'sh' before deriv can see it

This test determines definitively whether 's' is a real morpheme or a parser artifact.

Tests:
  A) REPARSE WITHOUT 's' AS GRAM PREFIX
       Remove 's' from gram prefix list, reparse entire corpus.
       How many tokens now have deriv='sh'? How many genuine h-only?

  B) RESIDUAL 's' TOKENS — WHAT HAPPENS?
       The 1,444 s+non-h tokens: are these real 's'-prefix words, or do
       they also reparse meaningfully without 's'?

  C) h-VERBAL PREFIX TEST ON CORRECTED COUNTS
       With the s→sh correction, rerun the permutation test.
       Only ~66 tokens may have pure h-prefix. Is that enough evidence?

  D) sh- AS UNIFIED MORPHEME
       With full sh-token set (~3000), test: line position, section dist,
       suffix preferences. Compare to the 258 tokens suffix_bug_cascade_audit identified.

  E) MUTUAL INFORMATION: ARE GRAM AND DERIV ONE SLOT?
       Compute MI(gram_prefix, deriv_prefix). If MI is very high, the
       two-slot model is wrong — they're one combined prefix slot.
"""

import re, json, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
from common import collapse_echains, gallows_base, strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ══════════════════════════════════════════════════════════════════
# MORPHOLOGICAL PIPELINE — TWO VERSIONS
# ══════════════════════════════════════════════════════════════════

SIMPLE_GALLOWS = ["t","k","f","p"]
BENCH_GALLOWS  = ["cth","ckh","cph","cfh"]
COMPOUND_GCH   = ["tch","kch","pch","fch"]
COMPOUND_GSH   = ["tsh","ksh","psh","fsh"]
ALL_GALLOWS    = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

PREFIXES_ORIG    = ['qo','q','so','do','o','d','s','y']
PREFIXES_NO_S    = ['qo','q','so','do','o','d','y']  # 's' removed
SUFFIXES_SHORT   = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']
DERIV_PREFIXES_ORDER = ['lch','lsh','ch','sh','l','h']

CORE_STEMS = {'e','o','ed','eo','od','ol','al','am','ar','or','es','eod','eos','os','a','d','l','r','s'}




def decompose(word, prefix_list=None):
    if prefix_list is None:
        prefix_list = PREFIXES_ORIG
    stripped, gals = strip_gallows(word)
    collapsed = collapse_echains(stripped)
    bases = [gallows_base(g) for g in gals]
    # Gram prefix
    pfx = ""
    temp = collapsed
    for pf in prefix_list:
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

def load_all_tokens():
    tokens = []
    section_map = {
        'bio': 'bio', 'cosmo': 'cosmo', 'herbal': 'herbal',
        'pharma': 'pharma', 'text': 'text', 'zodiac': 'zodiac'
    }
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        section = 'unknown'
        folio_id = ''
        line_idx = 0
        line_count_in_page = 0
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
                folio_id = m.group(1).split(',')[0]
                rest = line[m.end():].strip()
                line_count_in_page += 1
            else:
                rest = line
            if not rest: continue
            words = [w for w in re.split(r'[.\s,;]+', rest) if w.strip()]
            for i, word in enumerate(words):
                word = word.strip()
                if not word or not re.match(r'^[a-z]+$', word): continue
                pos_in_line = i / max(len(words)-1, 1) if len(words) > 1 else 0.5
                tokens.append(dict(word=word, section=section, folio=folio_id,
                                   pos_in_line=pos_in_line, word_idx=i,
                                   line_len=len(words)))
    return tokens

print("Loading tokens...")
tokens = load_all_tokens()
print(f"  {len(tokens)} tokens loaded\n")

# Parse under both models
print("Parsing under ORIGINAL model (with 's')...")
for t in tokens:
    d = decompose(t['word'], PREFIXES_ORIG)
    t['orig_gpfx'] = d['gram_prefix']
    t['orig_deriv'] = d['deriv_prefix']
    t['orig_stem'] = d['stem']
    t['orig_sfx'] = d['suffix']
    t['det'] = d['det']

print("Parsing under NO-S model (without 's')...")
for t in tokens:
    d = decompose(t['word'], PREFIXES_NO_S)
    t['nos_gpfx'] = d['gram_prefix']
    t['nos_deriv'] = d['deriv_prefix']
    t['nos_stem'] = d['stem']
    t['nos_sfx'] = d['suffix']

print("Done.\n")

# ══════════════════════════════════════════════════════════════════
# 35a: REPARSE WITHOUT 's' — IMPACT ASSESSMENT
# ══════════════════════════════════════════════════════════════════

print("=" * 70)
print("A: REPARSE WITHOUT 's' AS GRAM PREFIX")
print("=" * 70)

# How many tokens change?
changed = [t for t in tokens if t['orig_gpfx'] != t['nos_gpfx'] or 
           t['orig_deriv'] != t['nos_deriv'] or t['orig_stem'] != t['nos_stem']]
print(f"\nTokens that change parse: {len(changed)} / {len(tokens)} ({100*len(changed)/len(tokens):.1f}%)")

# Count deriv prefixes under both models
orig_deriv = Counter(t['orig_deriv'] for t in tokens)
nos_deriv = Counter(t['nos_deriv'] for t in tokens)
print(f"\nDeriv prefix counts — ORIGINAL vs NO-S model:")
print(f"  {'Deriv':<8} {'ORIG':>8} {'NO-S':>8} {'Change':>8}")
for dp in ['', 'h', 'ch', 'sh', 'l', 'lch', 'lsh']:
    o = orig_deriv.get(dp, 0)
    n = nos_deriv.get(dp, 0)
    label = dp if dp else '∅'
    print(f"  {label:<8} {o:>8} {n:>8} {n-o:>+8}")

# Gram prefix counts
orig_gpfx_ct = Counter(t['orig_gpfx'] for t in tokens)
nos_gpfx_ct = Counter(t['nos_gpfx'] for t in tokens)
print(f"\nGram prefix counts — ORIGINAL vs NO-S model:")
print(f"  {'GPfx':<8} {'ORIG':>8} {'NO-S':>8} {'Change':>8}")
for gp in ['', 'qo', 'q', 'so', 'do', 'o', 'd', 's', 'y']:
    o = orig_gpfx_ct.get(gp, 0)
    n = nos_gpfx_ct.get(gp, 0)
    label = gp if gp else '∅'
    print(f"  {label:<8} {o:>8} {n:>8} {n-o:>+8}")

# What happened to the old s+h tokens?
s_h_orig = [t for t in tokens if t['orig_gpfx'] == 's' and t['orig_deriv'] == 'h']
print(f"\nOld s+h tokens ({len(s_h_orig)}) — new parse:")
nos_deriv_of_old_sh = Counter(t['nos_deriv'] for t in s_h_orig)
for dp, ct in nos_deriv_of_old_sh.most_common():
    pct = 100 * ct / len(s_h_orig)
    label = dp if dp else '∅'
    print(f"  now deriv='{label}': {ct:>6} ({pct:.1f}%)")

# What happened to old s+non-h tokens?
s_other_orig = [t for t in tokens if t['orig_gpfx'] == 's' and t['orig_deriv'] != 'h']
print(f"\nOld s+non-h tokens ({len(s_other_orig)}) — new parse:")
nos_deriv_of_old_sother = Counter(t['nos_deriv'] for t in s_other_orig)
for dp, ct in nos_deriv_of_old_sother.most_common():
    pct = 100 * ct / len(s_other_orig)
    label = dp if dp else '∅'
    print(f"  now deriv='{label}': {ct:>6} ({pct:.1f}%)")

# Genuine h-only under NO-S model
h_only_nos = [t for t in tokens if t['nos_deriv'] == 'h']
print(f"\nGenuine h-only under NO-S model: {len(h_only_nos)}")
# What are they?
h_words = Counter(t['word'] for t in h_only_nos)
print(f"  Top h-only words: {h_words.most_common(15)}")
# Gram prefixes of h-only tokens
h_gpfx = Counter(t['nos_gpfx'] for t in h_only_nos)
print(f"  Gram prefixes: {dict(h_gpfx.most_common())}")

# sh- under NO-S model
sh_nos = [t for t in tokens if t['nos_deriv'] == 'sh']
print(f"\nsh- under NO-S model: {len(sh_nos)}")
sh_gpfx = Counter(t['nos_gpfx'] for t in sh_nos)
print(f"  Gram prefixes: {dict(sh_gpfx.most_common())}")


# ══════════════════════════════════════════════════════════════════
# 35b: RESIDUAL 's' ANALYSIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("B: RESIDUAL 's' ANALYSIS — ARE THE s+non-h TOKENS GENUINE?")
print("=" * 70)

# Under NO-S model, what happened to old s+non-h tokens?
# Did removing 's' just make them parseless, or do they parse differently?
print(f"\nOld s+non-h tokens ({len(s_other_orig)}):")
print(f"  Parse changes:")
nos_stems_of_sother = Counter(t['nos_stem'] for t in s_other_orig)
print(f"    Distinct stems: {len(nos_stems_of_sother)}")
print(f"    Top stems: {nos_stems_of_sother.most_common(10)}")

# Check if these stems are in CORE_STEMS or start with 's'
s_stem_words = [t for t in s_other_orig if t['nos_stem'].startswith('s')]
print(f"    Stems starting with 's': {len(s_stem_words)} ({100*len(s_stem_words)/max(len(s_other_orig),1):.1f}%)")
print(f"    → 's' was stripped but is now part of the stem")

# Compare: d-prefix tokens (unambiguous gram prefix)
d_tokens = [t for t in tokens if t['orig_gpfx'] == 'd']
print(f"\nComparison: d-prefix tokens ({len(d_tokens)})")
d_deriv = Counter(t['orig_deriv'] for t in d_tokens)
print(f"  Deriv distribution: {dict(d_deriv.most_common())}")

# Line position comparison: old s+non-h vs d-prefix
if s_other_orig:
    s_mean = sum(t['pos_in_line'] for t in s_other_orig) / len(s_other_orig)
    s_init = sum(1 for t in s_other_orig if t['pos_in_line'] < 0.2) / len(s_other_orig)
    d_mean = sum(t['pos_in_line'] for t in d_tokens) / len(d_tokens)
    d_init = sum(1 for t in d_tokens if t['pos_in_line'] < 0.2) / len(d_tokens)
    print(f"\n  Line position (old s+non-h): mean={s_mean:.3f}, init={100*s_init:.1f}%")
    print(f"  Line position (d-prefix):    mean={d_mean:.3f}, init={100*d_init:.1f}%")

# Section distributions
sections_all = sorted(set(t['section'] for t in tokens))
def section_dist(toks):
    ct = Counter(t['section'] for t in toks)
    total = sum(ct.values())
    return {s: ct.get(s, 0)/max(total,1) for s in sections_all}

if len(s_other_orig) > 50:
    s_sec = section_dist(s_other_orig)
    d_sec = section_dist(d_tokens)
    y_tokens = [t for t in tokens if t['orig_gpfx'] == 'y']
    y_sec = section_dist(y_tokens)
    
    print(f"\n  Section distributions:")
    print(f"  {'Section':<12} {'s+non-h':>8} {'d-pfx':>8} {'y-pfx':>8}")
    for sec in sections_all:
        print(f"  {sec:<12} {100*s_sec[sec]:>7.1f}% {100*d_sec[sec]:>7.1f}% {100*y_sec[sec]:>7.1f}%")
    
    # Cosine similarity
    import numpy as np
    def cosine(a, b):
        a_v = [a.get(s,0) for s in sections_all]
        b_v = [b.get(s,0) for s in sections_all]
        dot = sum(x*y for x,y in zip(a_v, b_v))
        norm_a = sum(x*x for x in a_v)**0.5
        norm_b = sum(x*x for x in b_v)**0.5
        return dot / max(norm_a * norm_b, 1e-10)
    
    print(f"\n  Cosine(s+non-h, d-pfx): {cosine(s_sec, d_sec):.3f}")
    print(f"  Cosine(s+non-h, y-pfx): {cosine(s_sec, y_sec):.3f}")
    print(f"  Cosine(d-pfx, y-pfx):   {cosine(d_sec, y_sec):.3f}")


# ══════════════════════════════════════════════════════════════════
# 35c: h-VERBAL PREFIX PERMUTATION TEST (CORRECTED)
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("C: h-VERBAL PREFIX TEST ON CORRECTED DATA")
print("=" * 70)

# Under NO-S model: how many stems have h- prefix?
h_stems_nos = set(t['nos_stem'] for t in tokens if t['nos_deriv'] == 'h')
sh_stems_nos = set(t['nos_stem'] for t in tokens if t['nos_deriv'] == 'sh')
bare_stems_nos = set(t['nos_stem'] for t in tokens if t['nos_deriv'] == '')
all_stems_nos = set(t['nos_stem'] for t in tokens)

print(f"\nUnder NO-S model:")
print(f"  Stems with h-prefix:  {len(h_stems_nos)} ({h_stems_nos if len(h_stems_nos)<30 else 'too many'})")
print(f"  Stems with sh-prefix: {len(sh_stems_nos)} ({sh_stems_nos if len(sh_stems_nos)<30 else 'too many'})")
print(f"  Stems bare:           {len(bare_stems_nos)}")

# The compound_model_validation test: do h-initial stems exist independently WITHOUT h?
# Under corrected model, h- tokens are (genuinely) prefixed with h-
# Check: for each h-stem, does it also appear as bare stem?
h_also_bare = h_stems_nos & bare_stems_nos
sh_also_bare = sh_stems_nos & bare_stems_nos
print(f"\n  h-stems that also appear bare: {len(h_also_bare)}/{len(h_stems_nos)}")
if h_also_bare:
    print(f"    {h_also_bare}")
print(f"  sh-stems that also appear bare: {len(sh_also_bare)}/{len(sh_stems_nos)}")
if sh_also_bare and len(sh_also_bare) < 30:
    print(f"    {sh_also_bare}")

# Core stem overlap
h_core = h_stems_nos & CORE_STEMS
sh_core = sh_stems_nos & CORE_STEMS
print(f"\n  h-stems in CORE_STEMS: {h_core}")
print(f"  sh-stems in CORE_STEMS: {sh_core}")

# Count: how many tokens have genuine h- under NO-S?
h_count_nos = sum(1 for t in tokens if t['nos_deriv'] == 'h')
sh_count_nos = sum(1 for t in tokens if t['nos_deriv'] == 'sh')
print(f"\n  Token counts: h-prefix = {h_count_nos}, sh-prefix = {sh_count_nos}")

# Line position test for h- under corrected model
if h_count_nos > 20:
    h_toks = [t for t in tokens if t['nos_deriv'] == 'h']
    h_mean = sum(t['pos_in_line'] for t in h_toks) / len(h_toks)
    h_init = sum(1 for t in h_toks if t['pos_in_line'] < 0.2) / len(h_toks)
    h_final = sum(1 for t in h_toks if t['pos_in_line'] > 0.8) / len(h_toks)
    print(f"\n  h-prefix line position (NO-S model): mean={h_mean:.3f}, init={100*h_init:.1f}%, final={100*h_final:.1f}%")

# Line position for sh-
sh_toks = [t for t in tokens if t['nos_deriv'] == 'sh']
if sh_toks:
    sh_mean = sum(t['pos_in_line'] for t in sh_toks) / len(sh_toks)
    sh_init = sum(1 for t in sh_toks if t['pos_in_line'] < 0.2) / len(sh_toks)
    sh_final = sum(1 for t in sh_toks if t['pos_in_line'] > 0.8) / len(sh_toks)
    print(f"  sh-prefix line position (NO-S model): mean={sh_mean:.3f}, init={100*sh_init:.1f}%, final={100*sh_final:.1f}%")

# Compare to bare and other derivs
bare_toks = [t for t in tokens if t['nos_deriv'] == '' and t['nos_gpfx'] == '']
if bare_toks:
    bare_mean = sum(t['pos_in_line'] for t in bare_toks) / len(bare_toks)
    bare_init = sum(1 for t in bare_toks if t['pos_in_line'] < 0.2) / len(bare_toks)
    print(f"  bare line position:                    mean={bare_mean:.3f}, init={100*bare_init:.1f}%")

ch_toks = [t for t in tokens if t['nos_deriv'] == 'ch']
if ch_toks:
    ch_mean = sum(t['pos_in_line'] for t in ch_toks) / len(ch_toks)
    ch_init = sum(1 for t in ch_toks if t['pos_in_line'] < 0.2) / len(ch_toks)
    print(f"  ch-prefix line position:               mean={ch_mean:.3f}, init={100*ch_init:.1f}%")

l_toks = [t for t in tokens if t['nos_deriv'] == 'l']
if l_toks:
    l_mean = sum(t['pos_in_line'] for t in l_toks) / len(l_toks)
    l_final = sum(1 for t in l_toks if t['pos_in_line'] > 0.8) / len(l_toks)
    print(f"  l-prefix line position:                mean={l_mean:.3f}, final={100*l_final:.1f}%")

# Permutation test: do h-prefix stems exist as bare more than random?
# Shuffle which stems get h- prefix label, count how many also appear bare
if h_count_nos > 20 and len(h_stems_nos) > 3:
    actual_overlap = len(h_also_bare)
    actual_rate = actual_overlap / len(h_stems_nos) if h_stems_nos else 0
    
    # Get all unique stems and their prefix assignments
    stem_set = list(all_stems_nos)
    n_h_stems = len(h_stems_nos)
    
    random.seed(42)
    null_overlaps = []
    for _ in range(10000):
        fake_h_stems = set(random.sample(stem_set, min(n_h_stems, len(stem_set))))
        null_overlap = len(fake_h_stems & bare_stems_nos)
        null_overlaps.append(null_overlap)
    
    null_mean = sum(null_overlaps) / len(null_overlaps)
    null_std = (sum((x - null_mean)**2 for x in null_overlaps) / len(null_overlaps))**0.5
    z = (actual_overlap - null_mean) / max(null_std, 0.01)
    p_above = sum(1 for x in null_overlaps if x >= actual_overlap) / len(null_overlaps)
    
    print(f"\n  Permutation test (h-stems also bare):")
    print(f"    Actual: {actual_overlap}/{len(h_stems_nos)} = {100*actual_rate:.1f}%")
    print(f"    Null:   {null_mean:.1f} ± {null_std:.1f}")
    print(f"    z = {z:.2f}, p = {p_above:.4f}")
else:
    print(f"\n  Too few h-prefix tokens ({h_count_nos}) for permutation test")

# Same test for sh-
if sh_count_nos > 20 and len(sh_stems_nos) > 3:
    actual_overlap_sh = len(sh_also_bare)
    actual_rate_sh = actual_overlap_sh / len(sh_stems_nos) if sh_stems_nos else 0
    
    stem_set = list(all_stems_nos)
    n_sh_stems = len(sh_stems_nos)
    
    random.seed(43)
    null_overlaps_sh = []
    for _ in range(10000):
        fake_sh_stems = set(random.sample(stem_set, min(n_sh_stems, len(stem_set))))
        null_overlap_sh = len(fake_sh_stems & bare_stems_nos)
        null_overlaps_sh.append(null_overlap_sh)
    
    null_mean_sh = sum(null_overlaps_sh) / len(null_overlaps_sh)
    null_std_sh = (sum((x - null_mean_sh)**2 for x in null_overlaps_sh) / len(null_overlaps_sh))**0.5
    z_sh = (actual_overlap_sh - null_mean_sh) / max(null_std_sh, 0.01)
    p_above_sh = sum(1 for x in null_overlaps_sh if x >= actual_overlap_sh) / len(null_overlaps_sh)
    
    print(f"\n  Permutation test (sh-stems also bare):")
    print(f"    Actual: {actual_overlap_sh}/{len(sh_stems_nos)} = {100*actual_rate_sh:.1f}%")
    print(f"    Null:   {null_mean_sh:.1f} ± {null_std_sh:.1f}")
    print(f"    z = {z_sh:.2f}, p = {p_above_sh:.4f}")


# ══════════════════════════════════════════════════════════════════
# 35d: sh- AS UNIFIED MORPHEME — FULL ANALYSIS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("D: sh- AS UNIFIED MORPHEME (NO-S MODEL)")
print("=" * 70)

sh_all = [t for t in tokens if t['nos_deriv'] == 'sh']
print(f"\nTotal sh-prefix tokens: {len(sh_all)}")

# Section distribution
sh_sec = Counter(t['section'] for t in sh_all)
total_sec = Counter(t['section'] for t in tokens)
print(f"\n  Section distribution:")
print(f"  {'Section':<12} {'sh-':>6} {'%sh':>7} {'Corpus%':>8} {'Ratio':>6}")
for sec in sorted(total_sec.keys()):
    sh_ct = sh_sec.get(sec, 0)
    sh_pct = 100 * sh_ct / len(sh_all) if sh_all else 0
    corpus_pct = 100 * total_sec[sec] / len(tokens)
    ratio = sh_pct / max(corpus_pct, 0.01)
    print(f"  {sec:<12} {sh_ct:>6} {sh_pct:>6.1f}% {corpus_pct:>7.1f}% {ratio:>5.2f}x")

# Suffix distribution
sh_sfx = Counter(t['nos_sfx'] for t in sh_all)
print(f"\n  Suffix distribution:")
for sfx, ct in sh_sfx.most_common():
    label = sfx if sfx else '∅'
    print(f"    {label:<8}: {ct:>5} ({100*ct/len(sh_all):.1f}%)")

# Stem distribution
sh_stems = Counter(t['nos_stem'] for t in sh_all)
print(f"\n  Top stems under sh-:")
for stem, ct in sh_stems.most_common(15):
    print(f"    {stem:<8}: {ct:>5} ({100*ct/len(sh_all):.1f}%)")

# Gram prefix distribution of sh-
sh_gpfx2 = Counter(t['nos_gpfx'] for t in sh_all)
print(f"\n  Gram prefix distribution:")
for gp, ct in sh_gpfx2.most_common():
    label = gp if gp else '∅'
    print(f"    {label:<8}: {ct:>5} ({100*ct/len(sh_all):.1f}%)")

# Compare old sh- (258 tokens) to new sh- (~3000 tokens)
# Under ORIG parser, how many had deriv='sh'?
sh_orig = [t for t in tokens if t['orig_deriv'] == 'sh']
print(f"\n  Comparison:")
print(f"    Old parser sh- tokens: {len(sh_orig)}")
print(f"    New parser sh- tokens: {len(sh_all)}")
print(f"    Net gain:              {len(sh_all) - len(sh_orig)}")


# ══════════════════════════════════════════════════════════════════
# 35e: MUTUAL INFORMATION — ARE GRAM AND DERIV ONE SLOT?
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("E: MUTUAL INFORMATION — GRAM × DERIV PREFIX")
print("=" * 70)

# Under ORIGINAL parser
gpfx_deriv_orig = Counter((t['orig_gpfx'] or '∅', t['orig_deriv'] or '∅') for t in tokens)
# Under NO-S parser
gpfx_deriv_nos = Counter((t['nos_gpfx'] or '∅', t['nos_deriv'] or '∅') for t in tokens)

def compute_mi(joint_counts):
    total = sum(joint_counts.values())
    # Marginals
    px = Counter()
    py = Counter()
    for (x, y), ct in joint_counts.items():
        px[x] += ct
        py[y] += ct
    mi = 0.0
    for (x, y), ct in joint_counts.items():
        pxy = ct / total
        p_x = px[x] / total
        p_y = py[y] / total
        if pxy > 0 and p_x > 0 and p_y > 0:
            mi += pxy * math.log2(pxy / (p_x * p_y))
    # Normalized MI (MI / min(H(X), H(Y)))
    hx = -sum((c/total)*math.log2(c/total) for c in px.values() if c > 0)
    hy = -sum((c/total)*math.log2(c/total) for c in py.values() if c > 0)
    nmi = mi / min(hx, hy) if min(hx, hy) > 0 else 0
    return mi, nmi, hx, hy

mi_orig, nmi_orig, hx_orig, hy_orig = compute_mi(gpfx_deriv_orig)
mi_nos, nmi_nos, hx_nos, hy_nos = compute_mi(gpfx_deriv_nos)

print(f"\nORIGINAL parser:")
print(f"  H(gram_prefix) = {hx_orig:.3f} bits")
print(f"  H(deriv_prefix) = {hy_orig:.3f} bits")
print(f"  MI(gram, deriv) = {mi_orig:.3f} bits")
print(f"  Normalized MI = {nmi_orig:.3f}")
print(f"  → {nmi_orig*100:.1f}% of prefix diversity is shared (redundant)")

print(f"\nNO-S parser:")
print(f"  H(gram_prefix) = {hx_nos:.3f} bits")
print(f"  H(deriv_prefix) = {hy_nos:.3f} bits")
print(f"  MI(gram, deriv) = {mi_nos:.3f} bits")
print(f"  Normalized MI = {nmi_nos:.3f}")
print(f"  → {nmi_nos*100:.1f}% of prefix diversity is shared (redundant)")

# Joint distribution table (NO-S model)
print(f"\n  Joint distribution (NO-S model) — top cells:")
print(f"  {'Gram+Deriv':<15} {'Count':>7} {'%':>6}")
for (gp, dp), ct in gpfx_deriv_nos.most_common(20):
    pct = 100 * ct / len(tokens)
    print(f"  {gp}+{dp:<10} {ct:>7} {pct:>5.1f}%")

# Chi-squared test: are gram and deriv independent?
# Under NO-S model
gpfx_vals = sorted(set(g for g, d in gpfx_deriv_nos.keys()))
deriv_vals = sorted(set(d for g, d in gpfx_deriv_nos.keys()))
total_n = len(tokens)

chi2 = 0.0
df = 0
gpfx_marginal = Counter(t['nos_gpfx'] or '∅' for t in tokens)
deriv_marginal = Counter(t['nos_deriv'] or '∅' for t in tokens)

for gp in gpfx_vals:
    for dp in deriv_vals:
        observed = gpfx_deriv_nos.get((gp, dp), 0)
        expected = gpfx_marginal[gp] * deriv_marginal[dp] / total_n
        if expected > 5:
            chi2 += (observed - expected)**2 / expected
            df += 1

df = max(df - (len(gpfx_vals) + len(deriv_vals) - 1), 1)
print(f"\n  Chi2(gram, deriv | NO-S) = {chi2:.1f}, df={df}")
print(f"  → If chi2 >> df, gram and deriv are NOT independent")


# ══════════════════════════════════════════════════════════════════
# 35f: COMBINED PREFIX MODEL — ALTERNATIVE TO GRAM+DERIV
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("F: COMBINED PREFIX MODEL — SINGLE SLOT ALTERNATIVE")
print("=" * 70)

# Instead of gram_prefix + deriv_prefix, what if there's ONE prefix?
# Under NO-S model, combine gram+deriv into a single field
for t in tokens:
    gp = t['nos_gpfx'] or ''
    dp = t['nos_deriv'] or ''
    t['combined_prefix'] = gp + dp if (gp or dp) else ''

combined = Counter(t['combined_prefix'] for t in tokens)
print(f"\nCombined prefix inventory ({len(combined)} distinct):")
print(f"  {'Prefix':<12} {'Count':>7} {'%':>6}")
for pfx, ct in combined.most_common(25):
    label = pfx if pfx else '∅'
    print(f"  {label:<12} {ct:>7} {100*ct/len(tokens):>5.1f}%")

# How many tokens have BOTH gram and deriv (excluding ∅)?
both = sum(1 for t in tokens if t['nos_gpfx'] and t['nos_deriv'])
only_gram = sum(1 for t in tokens if t['nos_gpfx'] and not t['nos_deriv'])
only_deriv = sum(1 for t in tokens if not t['nos_gpfx'] and t['nos_deriv'])
neither = sum(1 for t in tokens if not t['nos_gpfx'] and not t['nos_deriv'])
print(f"\n  Both gram+deriv: {both:>6} ({100*both/len(tokens):.1f}%)")
print(f"  Only gram:       {only_gram:>6} ({100*only_gram/len(tokens):.1f}%)")
print(f"  Only deriv:      {only_deriv:>6} ({100*only_deriv/len(tokens):.1f}%)")
print(f"  Neither:         {neither:>6} ({100*neither/len(tokens):.1f}%)")

# Are there invalid/impossible combinations?
print(f"\n  qo + deriv (should be rare):")
qo_deriv = Counter(t['nos_deriv'] for t in tokens if t['nos_gpfx'] == 'qo')
for dp, ct in qo_deriv.most_common():
    label = dp if dp else '∅'
    print(f"    qo+{label}: {ct}")

print(f"\n  o + deriv:")
o_deriv = Counter(t['nos_deriv'] for t in tokens if t['nos_gpfx'] == 'o')
for dp, ct in o_deriv.most_common():
    label = dp if dp else '∅'
    print(f"    o+{label}: {ct}")


# ══════════════════════════════════════════════════════════════════
# 35g: WHAT DID WE LEARN? SUMMARY STATISTICS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("G: sh_prefix_disentangle SUMMARY")
print("=" * 70)

print(f"""
KEY FINDINGS:
  1. Removing 's' from gram prefixes reclassifies {len(changed)} tokens ({100*len(changed)/len(tokens):.1f}%)
  2. Old s+h tokens ({len(s_h_orig)}) now parse as: {dict(nos_deriv_of_old_sh.most_common(3))}
  3. Genuine h-only tokens under corrected model: {h_count_nos}
  4. sh- tokens under corrected model: {sh_count_nos}
  5. MI(gram, deriv) drops from {nmi_orig:.3f} to {nmi_nos:.3f} when 's' removed
  6. Tokens with BOTH gram+deriv: {both} ({100*both/len(tokens):.1f}%)

VERDICT on 's' as gram prefix:
  If genuine h-only tokens under NO-S ({h_count_nos}) are very few (<100),
  then 's' was NEVER a real gram prefix — it was always the first char of 'sh'.
  
  If MI drops significantly when 's' is removed, the original model had
  a spurious dependency between gram and deriv that the NO-S model eliminates.
""")

print("\n[sh_prefix_disentangle Complete]")
