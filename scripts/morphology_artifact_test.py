#!/usr/bin/env python3
"""
IS THE MORPHOLOGICAL MODEL REAL OR A PARSING ARTIFACT?
==================================================================

The suffix-artifact audits caught TWO major greedy-parsing bugs (suffix vowel-stealing,
gram prefix 's' shadowing deriv 'sh'). The pattern is clear: sequential
left-to-right stripping creates artifacts whenever one morpheme is a prefix
of another.

CRITICAL: 'o', 'd', and 'l' are SIMULTANEOUSLY prefixes AND core stems.
The parser strips them as prefixes first — the SAME class of bug that
killed 's'/'sh'. How much of the model is real vs parsing accident?

morphology_artifact_test tests this with PARSER-FREE methods:

  A) RAW WORD PREFIX TEST (no parsing)
       Do raw words starting with 'ch', 'sh', 'qo', etc. show different
       suffix endings and line positions? If yes, the patterns are real
       regardless of parsing.

  B) RAW WORD SUFFIX TEST (no parsing)
       Do raw words ending in '-dy', '-y', '-aiin', etc. show different
       prefix distributions? If yes, the suffixes are real.

  C) THE 'o' AND 'd' PROBLEM
       'o' is the biggest gram prefix (6737 tokens under old model)
       AND a core stem. If we DON'T strip 'o' as prefix, what happens?
       Same for 'd'.

  D) PARSE ORDER SENSITIVITY
       Run 3 different parse orders. If the model is real, the core
       findings should be stable. If not, they're parse-order artifacts.

  E) MINIMAL PARSER — SUFFIXES ONLY
       Strip gallows + e-chains + suffixes. Nothing else. Does the
       resulting "root" inventory still show structure?
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
from common import collapse_echains, gallows_base, strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ══════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════

SIMPLE_GALLOWS = ["t","k","f","p"]
BENCH_GALLOWS  = ["cth","ckh","cph","cfh"]
COMPOUND_GCH   = ["tch","kch","pch","fch"]
COMPOUND_GSH   = ["tsh","ksh","psh","fsh"]
ALL_GALLOWS    = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

GRAM_PFXS    = ['qo','q','so','do','o','d','y']       # Post-sh_prefix_disentangle (no 's')
SUFFIXES     = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']
DERIV_PFXS   = ['lch','lsh','ch','sh','l']             # Post-sh_prefix_disentangle (no 'h')

CORE_STEMS = {'e','o','ed','eo','od','ol','al','am','ar','or','es','eod','eos','os','a','d','l','r','s'}




def decompose_configurable(word, gram_list, deriv_list, suffix_list, order='gsd'):
    """
    Configurable parser.
    order = string of 'g','s','d' for: gram, suffix, deriv parse order.
    """
    stripped, gals = strip_gallows(word)
    collapsed = collapse_echains(stripped)
    bases = [gallows_base(g) for g in gals]
    
    temp = collapsed
    gpfx = ""; sfx = ""; deriv = ""
    
    for step in order:
        if step == 'g':
            for pf in gram_list:
                if temp.startswith(pf) and len(temp) > len(pf)+1:
                    gpfx = pf; temp = temp[len(pf):]; break
        elif step == 's':
            for sf in suffix_list:
                if temp.endswith(sf) and len(temp) > len(sf):
                    sfx = sf; temp = temp[:-len(sf)]; break
        elif step == 'd':
            for dp in deriv_list:
                if temp.startswith(dp) and len(temp) > len(dp):
                    deriv = dp; temp = temp[len(dp):]; break
    
    return dict(original=word, gram_prefix=gpfx, det=bases[0] if bases else "",
                deriv_prefix=deriv, stem=temp, suffix=sfx)


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
                rest = line[m.end():].strip()
            else:
                rest = line
            if not rest: continue
            words = [w for w in re.split(r'[.\s,;]+', rest) if w.strip()]
            for i, word in enumerate(words):
                word = word.strip()
                if not word or not re.match(r'^[a-z]+$', word): continue
                pos = i / max(len(words)-1, 1) if len(words) > 1 else 0.5
                tokens.append(dict(word=word, section=section,
                                   pos_in_line=pos, line_len=len(words)))
    return tokens

print("Loading tokens...")
tokens = load_all_tokens()
print(f"  {len(tokens)} tokens loaded\n")

# Pre-compute gallows-stripped + e-collapsed form for parser-free tests
for t in tokens:
    stripped, gals = strip_gallows(t['word'])
    t['stripped'] = collapse_echains(stripped)
    t['gals'] = [gallows_base(g) for g in gals]


# ══════════════════════════════════════════════════════════════════
# 36a: RAW WORD PREFIX TEST — PARSER-FREE
# ══════════════════════════════════════════════════════════════════

print("=" * 70)
print("A: RAW PREFIX TEST — DO WORD-STARTS PREDICT WORD-ENDS?")
print("=" * 70)
print()
print("If 'ch', 'sh', etc. are real prefixes, raw words starting with them")
print("should have different ENDING distributions than other words.")
print("This test uses ZERO parsing — just raw string starts/ends.")
print()

# Test each claimed prefix against raw word endings
# Use the stripped+collapsed form (gallows removed, e-chains collapsed)
# because gallows are internal and e-chains are noisy

all_prefixes_to_test = ['ch','sh','l','qo','o','d','y','q']

# Get raw suffix endings (last 1-4 chars) for each token
def get_raw_endings(toks, suffixes_to_check):
    """For each token, check which claimed suffix it ends with (raw)."""
    counts = Counter()
    for t in toks:
        w = t['stripped']
        matched = '∅'
        for sf in suffixes_to_check:
            if w.endswith(sf) and len(w) > len(sf):
                matched = sf; break
        counts[matched] += 1
    return counts

# Baseline: all tokens
baseline_endings = get_raw_endings(tokens, SUFFIXES)
baseline_total = sum(baseline_endings.values())
baseline_dist = {k: v/baseline_total for k, v in baseline_endings.items()}

print(f"Baseline raw suffix distribution (N={baseline_total}):")
for sf in ['dy','y','aiin','ain','iin','in','ar','or','al','ol','∅']:
    pct = 100 * baseline_dist.get(sf, 0)
    print(f"  {sf:<6}: {pct:>5.1f}%")

print(f"\n{'Prefix':<6} {'N':>6} {'mean_pos':>8} {'%init':>6} | {'dy':>5} {'y':>5} {'aiin':>5} {'iin':>5} {'ol':>5} {'∅':>5} | cosine")

# For each prefix, get tokens starting with it, compute ending dist
prefix_results = {}
for pfx in all_prefixes_to_test:
    # Tokens whose stripped form starts with this prefix
    pfx_toks = [t for t in tokens if t['stripped'].startswith(pfx)]
    if len(pfx_toks) < 50:
        continue
    
    # Ending distribution
    endings = get_raw_endings(pfx_toks, SUFFIXES)
    total = sum(endings.values())
    dist = {k: v/total for k, v in endings.items()}
    
    # Line position
    mean_pos = sum(t['pos_in_line'] for t in pfx_toks) / len(pfx_toks)
    init_rate = sum(1 for t in pfx_toks if t['pos_in_line'] < 0.2) / len(pfx_toks)
    
    # Cosine vs baseline
    keys = set(list(baseline_dist.keys()) + list(dist.keys()))
    dot = sum(baseline_dist.get(k,0) * dist.get(k,0) for k in keys)
    norm_b = sum(v**2 for v in baseline_dist.values())**0.5
    norm_p = sum(v**2 for v in dist.values())**0.5
    cos = dot / max(norm_b * norm_p, 1e-10)
    
    print(f"  {pfx:<6} {len(pfx_toks):>6} {mean_pos:>8.3f} {100*init_rate:>5.1f}% |"
          f" {100*dist.get('dy',0):>4.1f} {100*dist.get('y',0):>4.1f}"
          f" {100*dist.get('aiin',0):>4.1f} {100*dist.get('iin',0):>4.1f}"
          f" {100*dist.get('ol',0):>4.1f} {100*dist.get('∅',0):>4.1f} | {cos:.3f}")
    
    prefix_results[pfx] = dict(n=len(pfx_toks), dist=dist, mean_pos=mean_pos, 
                                init_rate=init_rate, cosine=cos)

# Also test: tokens NOT starting with any claimed prefix
non_pfx_toks = [t for t in tokens if not any(t['stripped'].startswith(p) for p in all_prefixes_to_test)]
if non_pfx_toks:
    endings = get_raw_endings(non_pfx_toks, SUFFIXES)
    total = sum(endings.values())
    dist = {k: v/total for k, v in endings.items()}
    mean_pos = sum(t['pos_in_line'] for t in non_pfx_toks) / len(non_pfx_toks)
    init_rate = sum(1 for t in non_pfx_toks if t['pos_in_line'] < 0.2) / len(non_pfx_toks)
    keys = set(list(baseline_dist.keys()) + list(dist.keys()))
    dot = sum(baseline_dist.get(k,0) * dist.get(k,0) for k in keys)
    norm_b = sum(v**2 for v in baseline_dist.values())**0.5
    norm_p = sum(v**2 for v in dist.values())**0.5
    cos = dot / max(norm_b * norm_p, 1e-10)
    print(f"  {'NONE':<6} {len(non_pfx_toks):>6} {mean_pos:>8.3f} {100*init_rate:>5.1f}% |"
          f" {100*dist.get('dy',0):>4.1f} {100*dist.get('y',0):>4.1f}"
          f" {100*dist.get('aiin',0):>4.1f} {100*dist.get('iin',0):>4.1f}"
          f" {100*dist.get('ol',0):>4.1f} {100*dist.get('∅',0):>4.1f} | {cos:.3f}")

# Chi-squared: test if prefix identity predicts suffix choice
print(f"\n  Chi-squared: does raw prefix predict raw suffix?")
# Build contingency table: prefix (top 6) × suffix (top 6)
top_pfxs = [p for p in all_prefixes_to_test if p in prefix_results]
top_sfxs = ['dy','y','aiin','ain','iin','in','ar','or','al','ol','∅']

# Assign each token to a prefix group
def get_prefix_group(t):
    w = t['stripped']
    for p in ['qo','sh','ch','so','do','q','o','d','y','l']:  # longest first where needed
        if w.startswith(p):
            return p
    return 'NONE'

def get_suffix_group(t):
    w = t['stripped']
    for sf in SUFFIXES:
        if w.endswith(sf) and len(w) > len(sf):
            return sf
    return '∅'

prefix_groups = Counter()
joint = Counter()
suffix_groups = Counter()
for t in tokens:
    pg = get_prefix_group(t)
    sg = get_suffix_group(t)
    prefix_groups[pg] += 1
    suffix_groups[sg] += 1
    joint[(pg, sg)] += 1

N = len(tokens)
chi2 = 0.0
cells = 0
for pg in prefix_groups:
    for sg in suffix_groups:
        obs = joint.get((pg, sg), 0)
        exp = prefix_groups[pg] * suffix_groups[sg] / N
        if exp > 5:
            chi2 += (obs - exp)**2 / exp
            cells += 1

df = (len(prefix_groups) - 1) * (len(suffix_groups) - 1)
cramers_v = (chi2 / (N * min(len(prefix_groups)-1, len(suffix_groups)-1)))**0.5
print(f"  Chi2 = {chi2:.1f}, df = {df}, Cramér's V = {cramers_v:.3f}")
print(f"  (V > 0.1 = moderate association, V > 0.3 = strong)")


# ══════════════════════════════════════════════════════════════════
# 36b: RAW WORD SUFFIX TEST — PARSER-FREE
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("B: RAW SUFFIX TEST — DO WORD-ENDS PREDICT WORD-STARTS?")
print("=" * 70)
print()

# For each claimed suffix, what raw word-starts occur?
print(f"{'Suffix':<6} {'N':>6} {'mean_pos':>8} | {'ch':>5} {'sh':>5} {'qo':>5} {'o':>5} {'d':>5} {'l':>5} {'NONE':>5}")

for sfx in SUFFIXES + ['∅']:
    if sfx == '∅':
        sfx_toks = [t for t in tokens if not any(t['stripped'].endswith(sf) and len(t['stripped']) > len(sf) for sf in SUFFIXES)]
    else:
        sfx_toks = [t for t in tokens if t['stripped'].endswith(sfx) and len(t['stripped']) > len(sfx)]
    
    if len(sfx_toks) < 50:
        continue
    
    # Count prefix starts
    pfx_counts = Counter()
    for t in sfx_toks:
        pfx_counts[get_prefix_group(t)] += 1
    total = sum(pfx_counts.values())
    
    mean_pos = sum(t['pos_in_line'] for t in sfx_toks) / len(sfx_toks)
    
    print(f"  {sfx:<6} {len(sfx_toks):>6} {mean_pos:>8.3f} |"
          f" {100*pfx_counts.get('ch',0)/total:>4.1f}"
          f" {100*pfx_counts.get('sh',0)/total:>4.1f}"
          f" {100*pfx_counts.get('qo',0)/total:>4.1f}"
          f" {100*pfx_counts.get('o',0)/total:>4.1f}"
          f" {100*pfx_counts.get('d',0)/total:>4.1f}"
          f" {100*pfx_counts.get('l',0)/total:>4.1f}"
          f" {100*pfx_counts.get('NONE',0)/total:>4.1f}")


# ══════════════════════════════════════════════════════════════════
# 36c: THE 'o' AND 'd' PROBLEM
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("C: IS 'o' A REAL GRAM PREFIX OR JUST A STEM-INITIAL LETTER?")
print("=" * 70)

# Parse with o and d removed from gram list
GRAM_NO_OD = ['qo','q','so','do','y']  # Remove 'o' and 'd' 

# Parse under standard model (no 's', with 'o','d')
# Parse under no-OD model (no 's', no 'o', no 'd')
for t in tokens:
    d1 = decompose_configurable(t['word'], GRAM_PFXS, DERIV_PFXS, SUFFIXES, 'gsd')
    t['std_gpfx'] = d1['gram_prefix']
    t['std_deriv'] = d1['deriv_prefix']
    t['std_stem'] = d1['stem']
    t['std_sfx'] = d1['suffix']
    
    d2 = decompose_configurable(t['word'], GRAM_NO_OD, DERIV_PFXS, SUFFIXES, 'gsd')
    t['nood_gpfx'] = d2['gram_prefix']
    t['nood_deriv'] = d2['deriv_prefix']
    t['nood_stem'] = d2['stem']
    t['nood_sfx'] = d2['suffix']

# How many change?
changed_od = [t for t in tokens if t['std_stem'] != t['nood_stem']]
print(f"\nTokens that change when removing 'o' and 'd' from gram prefix: {len(changed_od)} ({100*len(changed_od)/len(tokens):.1f}%)")

# What happens to old o-prefix tokens?
o_old = [t for t in tokens if t['std_gpfx'] == 'o']
o_new_deriv = Counter(t['nood_deriv'] for t in o_old)
o_new_stems = Counter(t['nood_stem'] for t in o_old)
print(f"\nOld gram='o' tokens ({len(o_old)}):")
print(f"  New deriv prefixes: {dict(o_new_deriv.most_common(10))}")
print(f"  Top new stems: {o_new_stems.most_common(10)}")
# How many now have stems starting with 'o'?
o_stem_starts_o = sum(1 for t in o_old if t['nood_stem'].startswith('o'))
print(f"  Stems starting with 'o': {o_stem_starts_o} ({100*o_stem_starts_o/len(o_old):.1f}%)")

# What happens to old d-prefix tokens?
d_old = [t for t in tokens if t['std_gpfx'] == 'd']
d_new_deriv = Counter(t['nood_deriv'] for t in d_old)
d_new_stems = Counter(t['nood_stem'] for t in d_old)
print(f"\nOld gram='d' tokens ({len(d_old)}):")
print(f"  New deriv prefixes: {dict(d_new_deriv.most_common(10))}")
print(f"  Top new stems: {d_new_stems.most_common(10)}")
d_stem_starts_d = sum(1 for t in d_old if t['nood_stem'].startswith('d'))
print(f"  Stems starting with 'd': {d_stem_starts_d} ({100*d_stem_starts_d/len(d_old):.1f}%)")

# KEY TEST: Do o-prefix words have different SUFFIX distributions than bare?
# Under the parser-free logic, compare raw endings
o_start = [t for t in tokens if t['stripped'].startswith('o') and not t['stripped'].startswith('ol') 
           and not t['stripped'].startswith('or') and not t['stripped'].startswith('od')]
e_start = [t for t in tokens if t['stripped'].startswith('e') and not any(t['stripped'].startswith(p) for p in all_prefixes_to_test)]
d_start = [t for t in tokens if t['stripped'].startswith('d') and not t['stripped'].startswith('do')]

print(f"\n  Parser-free suffix comparison:")
for label, group in [("o-start", o_start), ("d-start", d_start), ("e-start", e_start)]:
    if len(group) < 30: continue
    endcts = get_raw_endings(group, SUFFIXES)
    total = sum(endcts.values())
    dy_pct = 100*endcts.get('dy',0)/total
    y_pct = 100*endcts.get('y',0)/total
    mean_pos = sum(t['pos_in_line'] for t in group)/len(group)
    print(f"  {label:<10} N={len(group):>5}: dy={dy_pct:.1f}%, y={y_pct:.1f}%, mean_pos={mean_pos:.3f}")

# Conclusive test: does removing 'o' from gram prefixes create the same
# near-zero situation we saw with 's'?
# Check: does 'o' overlap with any deriv prefix?
print(f"\n  Does removing 'o' change deriv prefix counts?")
std_deriv_ct = Counter(t['std_deriv'] for t in tokens)
nood_deriv_ct = Counter(t['nood_deriv'] for t in tokens)
for dp in ['', 'ch', 'sh', 'l', 'lch', 'lsh']:
    label = dp if dp else '∅'
    o_ct = std_deriv_ct.get(dp, 0)
    n_ct = nood_deriv_ct.get(dp, 0)
    if o_ct != n_ct:
        print(f"    {label}: {o_ct} → {n_ct} ({n_ct-o_ct:+d})")
if std_deriv_ct == nood_deriv_ct:
    print(f"    NO CHANGE — 'o' and 'd' don't shadow deriv prefixes")


# ══════════════════════════════════════════════════════════════════
# 36d: PARSE ORDER SENSITIVITY
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("D: PARSE ORDER SENSITIVITY — DOES ORDER MATTER?")
print("=" * 70)

orders = {
    'gsd': 'gram → suffix → deriv (standard)',
    'dsg': 'deriv → suffix → gram',
    'sgd': 'suffix → gram → deriv',
    'sdg': 'suffix → deriv → gram',
    'gds': 'gram → deriv → suffix',
    'dgs': 'deriv → gram → suffix',
}

order_results = {}
for order_code, order_label in orders.items():
    stem_counter = Counter()
    gpfx_counter = Counter()
    deriv_counter = Counter()
    sfx_counter = Counter()
    
    for t in tokens:
        d = decompose_configurable(t['word'], GRAM_PFXS, DERIV_PFXS, SUFFIXES, order_code)
        stem_counter[d['stem']] += 1
        gpfx_counter[d['gram_prefix'] or '∅'] += 1
        deriv_counter[d['deriv_prefix'] or '∅'] += 1
        sfx_counter[d['suffix'] or '∅'] += 1
    
    order_results[order_code] = dict(stems=stem_counter, gpfx=gpfx_counter, 
                                      deriv=deriv_counter, sfx=sfx_counter)
    
    n_stems = len(stem_counter)
    top_stem = stem_counter.most_common(1)[0]
    gpfx_h = -sum((c/len(tokens))*math.log2(c/len(tokens)) for c in gpfx_counter.values() if c > 0)
    deriv_h = -sum((c/len(tokens))*math.log2(c/len(tokens)) for c in deriv_counter.values() if c > 0)
    sfx_h = -sum((c/len(tokens))*math.log2(c/len(tokens)) for c in sfx_counter.values() if c > 0)
    
    print(f"\n  Order: {order_label}")
    print(f"    Distinct stems: {n_stems}, top: {top_stem[0]}({top_stem[1]})")
    print(f"    H(gpfx)={gpfx_h:.2f}, H(deriv)={deriv_h:.2f}, H(sfx)={sfx_h:.2f}")

# Compare: how many tokens get DIFFERENT stems under different orders?
ref_order = 'gsd'
print(f"\n  Stem stability (vs standard order '{ref_order}'):")
for order_code in orders:
    if order_code == ref_order: continue
    # Parse both and compare
    diff = 0
    for t in tokens:
        d1 = decompose_configurable(t['word'], GRAM_PFXS, DERIV_PFXS, SUFFIXES, ref_order)
        d2 = decompose_configurable(t['word'], GRAM_PFXS, DERIV_PFXS, SUFFIXES, order_code)
        if d1['stem'] != d2['stem']:
            diff += 1
    print(f"    {order_code}: {diff} tokens differ ({100*diff/len(tokens):.1f}%)")

# Key question: do paradigm-like tables survive?
# Under each order, count how many core stems appear with each deriv prefix
print(f"\n  Paradigm fill (core stems × deriv prefixes) per order:")
for order_code in ['gsd', 'dsg', 'sdg']:
    fills = 0; possible = 0
    stem_deriv = defaultdict(set)
    for t in tokens:
        d = decompose_configurable(t['word'], GRAM_PFXS, DERIV_PFXS, SUFFIXES, order_code)
        if d['stem'] in CORE_STEMS:
            stem_deriv[d['stem']].add(d['deriv_prefix'] or '∅')
    
    all_derivs = {'∅','ch','sh','l','lch','lsh'}
    for stem in CORE_STEMS:
        fills += len(stem_deriv.get(stem, set()) & all_derivs)
        possible += len(all_derivs)
    
    fill_rate = 100 * fills / max(possible, 1)
    print(f"    {order_code}: {fills}/{possible} cells filled ({fill_rate:.1f}%)")


# ══════════════════════════════════════════════════════════════════
# 36e: MINIMAL PARSER — SUFFIXES ONLY
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("E: MINIMAL PARSER — STRIP ONLY GALLOWS + E-CHAINS + SUFFIXES")
print("=" * 70)

# This is the maximally skeptical model: no prefixes at all
# Just: strip gallows, collapse e-chains, strip suffix → "root"

root_counter = Counter()
root_sfx = defaultdict(Counter)
root_pos = defaultdict(list)
root_sec = defaultdict(Counter)

for t in tokens:
    w = t['stripped']  # already gallows-stripped + e-collapsed
    # Strip suffix only
    sfx = ""
    temp = w
    for sf in SUFFIXES:
        if temp.endswith(sf) and len(temp) > len(sf):
            sfx = sf; temp = temp[:-len(sf)]; break
    
    root = temp
    root_counter[root] += 1
    root_sfx[root][sfx or '∅'] += 1
    root_pos[root].append(t['pos_in_line'])
    root_sec[root][t['section']] += 1

print(f"\nMinimal parser: {len(root_counter)} distinct roots")
print(f"Top 30 roots:")
print(f"  {'Root':<12} {'Count':>6} {'%':>5} | {'Suffixes':<40} | {'mean_pos':>8}")
for root, ct in root_counter.most_common(30):
    pct = 100 * ct / len(tokens)
    sfx_dist = root_sfx[root]
    total_sfx = sum(sfx_dist.values())
    top_sfxs_str = ", ".join(f"{s}={100*c/total_sfx:.0f}%" for s, c in sfx_dist.most_common(4))
    mean_p = sum(root_pos[root]) / len(root_pos[root])
    print(f"  {root:<12} {ct:>6} {pct:>4.1f}% | {top_sfxs_str:<40} | {mean_p:>8.3f}")

# KEY TEST: Do these minimal roots map cleanly to claimed prefix+stem?
# If 'oe' is a top root, it should map to gram=o + stem=e under the parsed model
# If 'che' is a top root, it should map to deriv=ch + stem=e
print(f"\n  Minimal root → parsed decomposition mapping:")
for root, ct in root_counter.most_common(20):
    # Parse this root with standard model (as if it were a word)
    d = decompose_configurable(root, GRAM_PFXS, DERIV_PFXS, [], 'gd')  # no suffixes
    gpfx = d['gram_prefix'] or '∅'
    deriv = d['deriv_prefix'] or '∅'
    stem = d['stem']
    print(f"  {root:<12} → gpfx={gpfx:<4} deriv={deriv:<4} stem={stem:<6}  (N={ct})")


# ══════════════════════════════════════════════════════════════════
# 36f: CRITICAL COMPARISON — PARSED VS RAW STRUCTURE
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("F: PARSED vs RAW — HOW MUCH STRUCTURE COMES FROM PARSING?")
print("=" * 70)

# Compare: entropy of suffix choice given PARSED prefix vs RAW prefix
# If parsing adds structure that isn't in the raw data, parsed H(sfx|pfx)
# will be much lower than raw H(sfx|pfx)

def conditional_entropy(group_key_fn, outcome_fn, toks):
    """Compute H(outcome | group)"""
    groups = defaultdict(Counter)
    for t in toks:
        g = group_key_fn(t)
        o = outcome_fn(t)
        groups[g][o] += 1
    
    N = len(toks)
    h_cond = 0.0
    for g, outcomes in groups.items():
        n_g = sum(outcomes.values())
        p_g = n_g / N
        h_g = 0.0
        for o, ct in outcomes.items():
            p = ct / n_g
            if p > 0:
                h_g -= p * math.log2(p)
        h_cond += p_g * h_g
    return h_cond

# Parse all tokens under standard model
for t in tokens:
    d = decompose_configurable(t['word'], GRAM_PFXS, DERIV_PFXS, SUFFIXES, 'gsd')
    t['p_gpfx'] = d['gram_prefix'] or '∅'
    t['p_deriv'] = d['deriv_prefix'] or '∅'
    t['p_stem'] = d['stem']
    t['p_sfx'] = d['suffix'] or '∅'

# Conditional entropies
h_sfx = conditional_entropy(lambda t: 'all', lambda t: t['p_sfx'], tokens)
h_sfx_given_parsed_pfx = conditional_entropy(
    lambda t: t['p_gpfx'] + '+' + t['p_deriv'], lambda t: t['p_sfx'], tokens)
h_sfx_given_raw_pfx = conditional_entropy(
    lambda t: get_prefix_group(t), lambda t: get_suffix_group(t), tokens)

print(f"\n  H(suffix) = {h_sfx:.3f} bits")
print(f"  H(suffix | parsed_prefix) = {h_sfx_given_parsed_pfx:.3f} bits")
print(f"  H(suffix | raw_prefix) = {h_sfx_given_raw_pfx:.3f} bits")
print(f"  Reduction from parsed prefix: {h_sfx - h_sfx_given_parsed_pfx:.3f} bits ({100*(h_sfx - h_sfx_given_parsed_pfx)/h_sfx:.1f}%)")
print(f"  Reduction from raw prefix:    {h_sfx - h_sfx_given_raw_pfx:.3f} bits ({100*(h_sfx - h_sfx_given_raw_pfx)/h_sfx:.1f}%)")
print(f"  → If both reductions are similar, parsing doesn't add fictional structure")

# Same in reverse: prefix given suffix
h_pfx = conditional_entropy(lambda t: 'all', lambda t: t['p_gpfx'] + '+' + t['p_deriv'], tokens)
h_pfx_given_parsed_sfx = conditional_entropy(
    lambda t: t['p_sfx'], lambda t: t['p_gpfx'] + '+' + t['p_deriv'], tokens)
h_pfx_given_raw_sfx = conditional_entropy(
    lambda t: get_suffix_group(t), lambda t: get_prefix_group(t), tokens)

print(f"\n  H(prefix) = {h_pfx:.3f} bits")
print(f"  H(prefix | parsed_suffix) = {h_pfx_given_parsed_sfx:.3f} bits")
print(f"  H(prefix | raw_suffix) = {h_pfx_given_raw_sfx:.3f} bits")
print(f"  Reduction from parsed suffix: {h_pfx - h_pfx_given_parsed_sfx:.3f} bits")
print(f"  Reduction from raw suffix:    {h_pfx - h_pfx_given_raw_sfx:.3f} bits")


print("\n\n[morphology_artifact_test Complete]")
