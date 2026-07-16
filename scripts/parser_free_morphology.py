#!/usr/bin/env python3
"""
PARSER-FREE MORPHOLOGICAL ANALYSIS
===============================================

morphology_artifact_test proved: the morphological SYSTEM is real (MI=0.19 bits) but
specific stem assignments are unreliable (44% change with parse order).

This phase works ONLY with stable, parser-free features:
  - Raw word starts (after gallows strip + e-collapse)
  - Raw word ends
  - Line position
  - Section distribution

Core questions:
  37a) ARE PREFIXES MEANINGFUL OR PHONOTACTIC?
       Does adding 'ch' to word-base X change section/position?
       Compare che+dy vs e+dy, che+y vs e+y, etc.
       If ch- is just a sound pattern with no meaning, section dists
       should be identical. If it carries meaning, they should differ.

  37b) THE DAIIN/AIIN COMPLEX
       daiin=807, aiin=554. Is daiin = d+aiin, or a single lexeme?
       Compare distributional profile of daiin to other d-prefix words.
       If daiin behaves like d+X, its section/position should match
       d+[other] words. If it's a unique lexeme, it won't.

  37c) WHAT DO THE EDGES ACTUALLY ENCODE?
       Section distribution by prefix: does ch- mean "herbal"?
       Line position by suffix: does -aiin mean "line-medial"?
       Find which edge features carry section/position information.

  37d) RAW WORD CLUSTERING
       Group the top N most common collapsed word forms.
       Compute pairwise distributional similarity (section + position
       profiles). Do natural clusters form?

  37e) ARE SUFFIXES INFLECTIONAL OR DERIVATIONAL?
       If inflectional: same base + different suffix → same section dist.
       If derivational: same base + different suffix → different section.
       Test with matched pairs: chedy/chey, shedy/shey, qoedy/qoey, etc.
"""

import re, sys, io, math, random
from pathlib import Path
from collections import Counter, defaultdict
from common import collapse_echains, gallows_base, strip_gallows

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ══════════════════════════════════════════════════════════════════
# CONSTANTS & HELPERS
# ══════════════════════════════════════════════════════════════════

SIMPLE_GALLOWS = ["t","k","f","p"]
BENCH_GALLOWS  = ["cth","ckh","cph","cfh"]
COMPOUND_GCH   = ["tch","kch","pch","fch"]
COMPOUND_GSH   = ["tsh","ksh","psh","fsh"]
ALL_GALLOWS    = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

SUFFIXES = ['aiin','ain','iin','in','ar','or','al','ol','dy','y']




def get_collapsed(word):
    """Gallows-strip, e-collapse → normalized form."""
    stripped, gals = strip_gallows(word)
    return collapse_echains(stripped), [gallows_base(g) for g in gals]

def raw_suffix(w):
    """Match longest suffix from normalized word."""
    for sf in SUFFIXES:
        if w.endswith(sf) and len(w) > len(sf):
            return sf
    return '∅'

def raw_base(w):
    """After removing suffix, what's left?"""
    sf = raw_suffix(w)
    if sf == '∅':
        return w
    return w[:-len(sf)]

SECTIONS_ORDER = ['bio','cosmo','herbal-A','herbal-B','pharma','text','zodiac','unknown']

def section_vec(toks, sections=SECTIONS_ORDER):
    ct = Counter(t['section'] for t in toks)
    total = max(sum(ct.values()), 1)
    return [ct.get(s, 0)/total for s in sections]

def cosine(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    na = sum(x*x for x in a)**0.5
    nb = sum(x*x for x in b)**0.5
    return dot / max(na * nb, 1e-10)


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
                coll, gals = get_collapsed(word)
                tokens.append(dict(word=word, section=section,
                                   pos_in_line=pos, line_len=len(words),
                                   collapsed=coll, gals=gals))
    return tokens

print("Loading tokens...")
tokens = load_all_tokens()
print(f"  {len(tokens)} tokens loaded")

# Index by collapsed form
by_collapsed = defaultdict(list)
for t in tokens:
    by_collapsed[t['collapsed']].append(t)

print(f"  {len(by_collapsed)} distinct collapsed forms\n")


# ══════════════════════════════════════════════════════════════════
# 37a: ARE PREFIXES MEANINGFUL OR PHONOTACTIC?
# ══════════════════════════════════════════════════════════════════

print("=" * 70)
print("37a: ARE PREFIXES MEANINGFUL?")
print("    Test: does adding a prefix change section/position distribution?")
print("=" * 70)

# Strategy: find matched pairs where base is the same, prefix differs.
# E.g., collapsed forms 'edy' vs 'chedy' vs 'shedy' vs 'lchedy'
# If ch- is meaningful, section dist of 'chedy' ≠ 'edy'.
# If ch- is phonotactic, section dist of 'chedy' ≈ 'edy'.

# Build table of bases and their observed prefixed variants
base_to_forms = defaultdict(dict)  # base → {prefix: collapsed_form}
all_prefixes_raw = ['ch','sh','l','lch','lsh','qo','o','d','y','q']

for coll, toks in by_collapsed.items():
    if len(toks) < 15:  # need enough tokens for distributional comparison
        continue
    # Determine the raw base (after suffix strip)
    base = raw_base(coll)
    sfx = raw_suffix(coll)
    
    # Check if this base starts with a prefix
    matched_pfx = ''
    for p in sorted(all_prefixes_raw, key=len, reverse=True):  # longest first
        if base.startswith(p) and len(base) > len(p):
            matched_pfx = p
            break
    
    inner_base = base[len(matched_pfx):] if matched_pfx else base
    key = (inner_base, sfx)
    
    if matched_pfx:
        base_to_forms[key][matched_pfx] = coll
    else:
        base_to_forms[key]['∅'] = coll

# Find bases with both bare and at least one prefixed form
print(f"\n  Matched prefix pairs (base + suffix constant, prefix varies):\n")
print(f"  {'Base+Sfx':<14} {'Form A':<14} {'N_A':>5} {'Form B':<14} {'N_B':>5} | {'Sec cosine':>10} {'Δpos':>6}")

pair_cosines = []
inflectional_tests = []

for (inner, sfx), forms in sorted(base_to_forms.items(), key=lambda x: -sum(len(by_collapsed.get(f,[])) for f in x[1].values())):
    if '∅' not in forms:
        continue
    bare_form = forms['∅']
    bare_toks = by_collapsed[bare_form]
    if len(bare_toks) < 20:
        continue
    
    bare_sec = section_vec(bare_toks)
    bare_pos = sum(t['pos_in_line'] for t in bare_toks) / len(bare_toks)
    
    for pfx, pfx_form in sorted(forms.items()):
        if pfx == '∅':
            continue
        pfx_toks = by_collapsed[pfx_form]
        if len(pfx_toks) < 20:
            continue
        
        pfx_sec = section_vec(pfx_toks)
        pfx_pos = sum(t['pos_in_line'] for t in pfx_toks) / len(pfx_toks)
        
        cos = cosine(bare_sec, pfx_sec)
        dpos = pfx_pos - bare_pos
        
        base_label = inner + '+' + sfx if sfx != '∅' else inner
        pair_cosines.append((pfx, cos, dpos, base_label, len(bare_toks), len(pfx_toks)))
        
        if len(pair_cosines) <= 25:
            print(f"  {base_label:<14} {bare_form:<14} {len(bare_toks):>5} {pfx_form:<14} {len(pfx_toks):>5} | {cos:>10.3f} {dpos:>+6.3f}")

# Aggregate by prefix: average cosine and average Δposition
print(f"\n  Aggregate prefix effects (mean over matched pairs):")
pfx_agg = defaultdict(lambda: {'cos': [], 'dpos': [], 'n': 0})
for pfx, cos, dpos, label, n_bare, n_pfx in pair_cosines:
    pfx_agg[pfx]['cos'].append(cos)
    pfx_agg[pfx]['dpos'].append(dpos)
    pfx_agg[pfx]['n'] += 1

print(f"  {'Prefix':<8} {'Pairs':>5} {'Mean cos':>9} {'Std cos':>8} {'Mean Δpos':>10} | Verdict")
for pfx in sorted(pfx_agg.keys()):
    d = pfx_agg[pfx]
    if d['n'] < 2:
        continue
    mean_cos = sum(d['cos']) / len(d['cos'])
    std_cos = (sum((c - mean_cos)**2 for c in d['cos']) / len(d['cos']))**0.5
    mean_dpos = sum(d['dpos']) / len(d['dpos'])
    
    if mean_cos > 0.95:
        verdict = "PHONOTACTIC (no section change)"
    elif mean_cos > 0.85:
        verdict = "WEAK meaning signal"
    else:
        verdict = "MEANINGFUL (section changes)"
    
    print(f"  {pfx:<8} {d['n']:>5} {mean_cos:>9.3f} {std_cos:>8.3f} {mean_dpos:>+10.3f} | {verdict}")


# ══════════════════════════════════════════════════════════════════
# 37b: THE DAIIN/AIIN COMPLEX
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("37b: THE DAIIN/AIIN COMPLEX — IS daiin = d + aiin?")
print("=" * 70)

# All collapsed forms ending in 'aiin'
aiin_family = {coll: toks for coll, toks in by_collapsed.items() 
               if coll.endswith('aiin') and len(toks) >= 10}

print(f"\n  Collapsed forms ending in 'aiin' (N≥10):")
print(f"  {'Form':<16} {'N':>5} {'mean_pos':>8} | {'bio':>5} {'herbA':>6} {'text':>5} {'cosmo':>5} {'pharma':>6}")
for coll in sorted(aiin_family, key=lambda c: -len(aiin_family[c])):
    toks = aiin_family[coll]
    sv = section_vec(toks)
    mp = sum(t['pos_in_line'] for t in toks) / len(toks)
    print(f"  {coll:<16} {len(toks):>5} {mp:>8.3f} |"
          f" {100*sv[0]:>4.1f} {100*sv[2]:>5.1f} {100*sv[5]:>5.1f}"
          f" {100*sv[1]:>5.1f} {100*sv[4]:>5.1f}")

# Compare: daiin vs other d-prefix words
daiin_toks = by_collapsed.get('daiin', [])
d_other_toks = [t for coll, toks in by_collapsed.items() 
                for t in toks if coll.startswith('d') and coll != 'daiin']
aiin_toks = by_collapsed.get('aiin', [])

# Also compare daiin to ALL words ending in -aiin
all_aiin_toks = [t for coll, toks in by_collapsed.items() 
                 for t in toks if coll.endswith('aiin')]

print(f"\n  Distributional comparison:")
for label, toks in [('daiin', daiin_toks), ('aiin', aiin_toks), 
                     ('d+other', d_other_toks), ('all *aiin', all_aiin_toks)]:
    if not toks: continue
    sv = section_vec(toks)
    mp = sum(t['pos_in_line'] for t in toks) / len(toks)
    init = sum(1 for t in toks if t['pos_in_line'] < 0.2) / len(toks)
    print(f"  {label:<14} N={len(toks):>5}: pos={mp:.3f} init={100*init:.1f}%"
          f"  bio={100*sv[0]:.1f}% hA={100*sv[2]:.1f}% txt={100*sv[5]:.1f}%")

# Cosine similarities
if daiin_toks and aiin_toks and d_other_toks:
    cos_da = cosine(section_vec(daiin_toks), section_vec(aiin_toks))
    cos_dd = cosine(section_vec(daiin_toks), section_vec(d_other_toks))
    cos_dall = cosine(section_vec(daiin_toks), section_vec(all_aiin_toks))
    print(f"\n  Cosine(daiin, aiin) = {cos_da:.3f}")
    print(f"  Cosine(daiin, d+other) = {cos_dd:.3f}")
    print(f"  Cosine(daiin, all *aiin) = {cos_dall:.3f}")
    print(f"  → If daiin≈d+other, d- is the controlling prefix")
    print(f"  → If daiin≈aiin, d- doesn't change meaning")
    print(f"  → If daiin≈all_aiin, -aiin controls the distribution")

# Line position profile of daiin
if daiin_toks:
    pos_bins = [0]*5
    for t in daiin_toks:
        b = min(int(t['pos_in_line'] * 5), 4)
        pos_bins[b] += 1
    total = sum(pos_bins)
    print(f"\n  daiin line position profile:")
    for i, ct in enumerate(pos_bins):
        bar = '█' * int(50 * ct/total)
        print(f"    [{i*20}-{(i+1)*20}%]: {100*ct/total:>5.1f}% {bar}")


# ══════════════════════════════════════════════════════════════════
# 37c: WHAT DO THE EDGES ENCODE?
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("37c: WHAT DO EDGES ENCODE? (Section + position by raw prefix/suffix)")
print("=" * 70)

# Section enrichment by raw prefix (parser-free)
print(f"\n  Section enrichment by raw prefix (observed/expected):")
corpus_sec = section_vec(tokens)
all_pfx_tokens = defaultdict(list)
for t in tokens:
    c = t['collapsed']
    for p in sorted(all_prefixes_raw, key=len, reverse=True):
        if c.startswith(p):
            all_pfx_tokens[p].append(t)
            break
    else:
        all_pfx_tokens['NONE'].append(t)

print(f"  {'Pfx':<6} {'N':>6} | {'bio':>6} {'cosmo':>6} {'herbA':>6} {'herbB':>6} {'pharma':>6} {'text':>6}")
for pfx in ['ch','sh','l','lch','lsh','qo','o','d','y','q','NONE']:
    toks = all_pfx_tokens.get(pfx, [])
    if len(toks) < 50: continue
    sv = section_vec(toks)
    # Show enrichment relative to corpus
    enrichments = []
    for i, s in enumerate(SECTIONS_ORDER[:6]):
        ratio = sv[i] / max(corpus_sec[i], 0.001)
        enrichments.append(f"{ratio:>5.2f}x")
    print(f"  {pfx:<6} {len(toks):>6} | {' '.join(enrichments)}")

# Same for suffixes
print(f"\n  Section enrichment by raw suffix:")
sfx_tokens = defaultdict(list)
for t in tokens:
    sf = raw_suffix(t['collapsed'])
    sfx_tokens[sf].append(t)

print(f"  {'Sfx':<6} {'N':>6} | {'bio':>6} {'cosmo':>6} {'herbA':>6} {'herbB':>6} {'pharma':>6} {'text':>6}")
for sfx in SUFFIXES + ['∅']:
    toks = sfx_tokens.get(sfx, [])
    if len(toks) < 50: continue
    sv = section_vec(toks)
    enrichments = []
    for i in range(6):
        ratio = sv[i] / max(corpus_sec[i], 0.001)
        enrichments.append(f"{ratio:>5.2f}x")
    print(f"  {sfx:<6} {len(toks):>6} | {' '.join(enrichments)}")

# Line position by prefix
print(f"\n  Line position by raw prefix:")
print(f"  {'Pfx':<6} {'N':>6} {'mean':>6} {'init%':>6} {'final%':>7}")
for pfx in ['ch','sh','l','lch','lsh','qo','o','d','y','q','NONE']:
    toks = all_pfx_tokens.get(pfx, [])
    if len(toks) < 50: continue
    mp = sum(t['pos_in_line'] for t in toks) / len(toks)
    init = sum(1 for t in toks if t['pos_in_line'] < 0.2) / len(toks)
    final = sum(1 for t in toks if t['pos_in_line'] > 0.8) / len(toks)
    print(f"  {pfx:<6} {len(toks):>6} {mp:>6.3f} {100*init:>5.1f}% {100*final:>6.1f}%")

# Line position by suffix
print(f"\n  Line position by raw suffix:")
print(f"  {'Sfx':<6} {'N':>6} {'mean':>6} {'init%':>6} {'final%':>7}")
for sfx in SUFFIXES + ['∅']:
    toks = sfx_tokens.get(sfx, [])
    if len(toks) < 50: continue
    mp = sum(t['pos_in_line'] for t in toks) / len(toks)
    init = sum(1 for t in toks if t['pos_in_line'] < 0.2) / len(toks)
    final = sum(1 for t in toks if t['pos_in_line'] > 0.8) / len(toks)
    print(f"  {sfx:<6} {len(toks):>6} {mp:>6.3f} {100*init:>5.1f}% {100*final:>6.1f}%")


# ══════════════════════════════════════════════════════════════════
# 37d: RAW WORD CLUSTERING
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("37d: RAW WORD CLUSTERING (top collapsed forms)")
print("=" * 70)

# For top N collapsed forms, build feature vector: section(8) + position(5)
# Then find natural clusters

top_forms = sorted(by_collapsed.keys(), key=lambda c: -len(by_collapsed[c]))[:80]

# Build feature vectors
form_features = {}
for coll in top_forms:
    toks = by_collapsed[coll]
    sv = section_vec(toks)
    # Position histogram (5 bins)
    pos_bins = [0]*5
    for t in toks:
        b = min(int(t['pos_in_line'] * 5), 4)
        pos_bins[b] += 1
    total = max(sum(pos_bins), 1)
    pv = [b/total for b in pos_bins]
    
    form_features[coll] = sv + pv  # 13-dim vector

# Pairwise cosine similarity matrix
forms_list = list(form_features.keys())
n = len(forms_list)

# Find most similar and most dissimilar pairs
pairs = []
for i in range(n):
    for j in range(i+1, n):
        c = cosine(form_features[forms_list[i]], form_features[forms_list[j]])
        pairs.append((c, forms_list[i], forms_list[j]))

pairs.sort(reverse=True)

print(f"\n  Top 15 most similar pairs (section+position cosine):")
for cos_val, a, b in pairs[:15]:
    print(f"    {a:<14} ↔ {b:<14}  cos={cos_val:.4f}  N={len(by_collapsed[a])},{len(by_collapsed[b])}")

print(f"\n  Top 10 most dissimilar pairs:")
for cos_val, a, b in pairs[-10:]:
    n_a, n_b = len(by_collapsed[a]), len(by_collapsed[b])
    if n_a > 30 and n_b > 30:  # only show if both have decent N
        print(f"    {a:<14} ↔ {b:<14}  cos={cos_val:.4f}  N={n_a},{n_b}")

# Simple k-means-like clustering (k=5)
# Use greedy approach: pick seed = most dissimilar form, then nearest remaining
random.seed(42)
K = 6
centers = [form_features[forms_list[0]]]
center_forms = [forms_list[0]]
remaining = list(range(1, n))

for _ in range(K-1):
    # Pick form most distant from all current centers
    best_dist = -1
    best_idx = remaining[0]
    for idx in remaining:
        min_cos_to_centers = min(cosine(form_features[forms_list[idx]], c) for c in centers)
        if min_cos_to_centers < best_dist or best_dist < 0:
            # We want the one with LOWEST max cosine (most different)
            pass
        dist = 1 - min(cosine(form_features[forms_list[idx]], c) for c in centers)
        if dist > best_dist:
            best_dist = dist
            best_idx = idx
    centers.append(form_features[forms_list[best_idx]])
    center_forms.append(forms_list[best_idx])
    remaining.remove(best_idx)

# Assign each form to nearest center
clusters = defaultdict(list)
for i in range(n):
    best_c = 0
    best_cos = -1
    for c_idx, center in enumerate(centers):
        cos_val = cosine(form_features[forms_list[i]], center)
        if cos_val > best_cos:
            best_cos = cos_val
            best_c = c_idx
    clusters[best_c].append((forms_list[i], len(by_collapsed[forms_list[i]])))

print(f"\n  {K}-cluster grouping (seed-based):")
for c_idx in range(K):
    members = clusters[c_idx]
    members.sort(key=lambda x: -x[1])
    total_toks = sum(ct for _, ct in members)
    
    # Aggregate section vector for cluster
    cluster_toks = []
    for coll, _ in members:
        cluster_toks.extend(by_collapsed[coll])
    sv = section_vec(cluster_toks)
    mp = sum(t['pos_in_line'] for t in cluster_toks) / max(len(cluster_toks),1)
    
    top_3 = ", ".join(f"{f}({ct})" for f, ct in members[:5])
    sec_str = " ".join(f"{SECTIONS_ORDER[i][:4]}={100*sv[i]:.0f}%" for i in range(6) if sv[i] > 0.05)
    print(f"\n  Cluster {c_idx} (seed={center_forms[c_idx]}, {len(members)} forms, {total_toks} tokens):")
    print(f"    Section: {sec_str}")
    print(f"    Position: mean={mp:.3f}")
    print(f"    Members: {top_3}")


# ══════════════════════════════════════════════════════════════════
# 37e: ARE SUFFIXES INFLECTIONAL OR DERIVATIONAL?
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("37e: ARE SUFFIXES INFLECTIONAL OR DERIVATIONAL?")
print("    Inflectional → same base + diff suffix = same section dist")
print("    Derivational → same base + diff suffix = different sections")
print("=" * 70)

# Find bases that appear with multiple suffixes (both N>20)
base_index = defaultdict(lambda: defaultdict(list))  # base → suffix → tokens
for t in tokens:
    c = t['collapsed']
    sf = raw_suffix(c)
    base = raw_base(c)
    base_index[base][sf].append(t)

# For each base, compare section dists across suffixes
base_comparisons = []

for base in sorted(base_index.keys(), key=lambda b: -sum(len(toks) for toks in base_index[b].values())):
    sfx_dict = base_index[base]
    # Need at least 2 suffixes each with N>20
    valid_sfxs = [(sf, toks) for sf, toks in sfx_dict.items() if len(toks) > 20]
    if len(valid_sfxs) < 2:
        continue
    
    # Pairwise cosine between suffix variants
    for i in range(len(valid_sfxs)):
        for j in range(i+1, len(valid_sfxs)):
            sf_a, toks_a = valid_sfxs[i]
            sf_b, toks_b = valid_sfxs[j]
            cos_val = cosine(section_vec(toks_a), section_vec(toks_b))
            base_comparisons.append((base, sf_a, sf_b, cos_val, len(toks_a), len(toks_b)))

print(f"\n  Found {len(base_comparisons)} base×suffix pairs to compare\n")

if base_comparisons:
    all_cosines = [c[3] for c in base_comparisons]
    mean_cos = sum(all_cosines) / len(all_cosines)
    print(f"  Mean section cosine between suffix variants: {mean_cos:.3f}")
    print(f"  (>0.95 = strongly inflectional, <0.85 = derivational)\n")
    
    # Show detail
    print(f"  {'Base':<12} {'Sfx A':<6} {'N_A':>5} {'Sfx B':<6} {'N_B':>5} {'Cosine':>7}")
    for base, sf_a, sf_b, cos_val, n_a, n_b in sorted(base_comparisons, key=lambda x: x[3])[:15]:
        print(f"  {base:<12} {sf_a:<6} {n_a:>5} {sf_b:<6} {n_b:>5} {cos_val:>7.3f}")
    print(f"  ...")
    for base, sf_a, sf_b, cos_val, n_a, n_b in sorted(base_comparisons, key=lambda x: -x[3])[:10]:
        print(f"  {base:<12} {sf_a:<6} {n_a:>5} {sf_b:<6} {n_b:>5} {cos_val:>7.3f}")

    # Permutation test: compare observed mean cosine to shuffled
    random.seed(42)
    null_cosines = []
    all_sec_vecs = [section_vec(toks) for base_dict in base_index.values() 
                     for sf, toks in base_dict.items() if len(toks) > 20]
    
    for _ in range(1000):
        shuffled = random.sample(all_sec_vecs, min(len(base_comparisons)*2, len(all_sec_vecs)))
        sample_cos = []
        for i in range(0, len(shuffled)-1, 2):
            sample_cos.append(cosine(shuffled[i], shuffled[i+1]))
        if sample_cos:
            null_cosines.append(sum(sample_cos)/len(sample_cos))
    
    if null_cosines:
        null_mean = sum(null_cosines) / len(null_cosines)
        null_std = (sum((x-null_mean)**2 for x in null_cosines)/len(null_cosines))**0.5
        z = (mean_cos - null_mean) / max(null_std, 0.001)
        print(f"\n  Permutation test:")
        print(f"    Observed mean cosine: {mean_cos:.3f}")
        print(f"    Null (random pairs):  {null_mean:.3f} ± {null_std:.3f}")
        print(f"    z = {z:.2f}")
        print(f"    → If z >> 0, suffix variants of same base have MORE similar")
        print(f"      section profiles than random = INFLECTIONAL")

# Also test: does suffix TYPE predict section at all?
print(f"\n  Direct test: do suffixes differ in section distribution?")
sfx_sec_vecs = {}
for sfx in SUFFIXES:
    toks = sfx_tokens.get(sfx, [])
    if len(toks) > 50:
        sfx_sec_vecs[sfx] = section_vec(toks)

# Pairwise cosine between suffixes
sfx_keys = list(sfx_sec_vecs.keys())
sfx_pairs = []
for i in range(len(sfx_keys)):
    for j in range(i+1, len(sfx_keys)):
        c = cosine(sfx_sec_vecs[sfx_keys[i]], sfx_sec_vecs[sfx_keys[j]])
        sfx_pairs.append((sfx_keys[i], sfx_keys[j], c))

sfx_pairs.sort(key=lambda x: x[2])
print(f"\n  Suffix pairwise section cosines:")
print(f"  Most DIFFERENT:")
for a, b, c in sfx_pairs[:5]:
    print(f"    {a:<6} ↔ {b:<6}: {c:.3f}")
print(f"  Most SIMILAR:")
for a, b, c in sfx_pairs[-5:]:
    print(f"    {a:<6} ↔ {b:<6}: {c:.3f}")
mean_sfx_cos = sum(c for _,_,c in sfx_pairs) / len(sfx_pairs) if sfx_pairs else 0
print(f"  Mean pairwise cosine between suffixes: {mean_sfx_cos:.3f}")


print("\n\n[parser_free_morphology Complete]")
