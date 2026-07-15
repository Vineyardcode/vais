#!/usr/bin/env python3
"""
Phase 28 — Statistical Significance, POS Fix, & Long-Root Focus
================================================================

Phase 27 self-audit found critical problems:
  1) 91% of coverage from 1-2 char roots (noise absorption risk)
  2) Section specificity: only 3/10 domain predictions pass
  3) POS mismatches: ho, ch, ol need reclassification
  4) qokedy pattern dominates f78r — need to understand why
  5) esed (1 token), yed (5 tokens) too weak to keep

This phase:
  28a) PERMUTATION TEST — Shuffle section labels, re-run section
       enrichment. Are our gallows distributions better than random?
  28b) RECLASSIFY POS — Fix ho→verb, ch→noun, ol→noun based on data.
       Demote esed, yed to "speculative".
  28c) QOKEDY INVESTIGATION — This pattern appears 100s of times. Is
       our decomposition (qo+k+e+dy) correct, or is qokedy itself a
       word/formula? Compare it as atomic vs decomposed.
  28d) LONG-ROOT CENSUS — Focus ONLY on 3+ char roots. What are the
       most frequent unexplained long roots? These are the real targets.
  28e) BIGRAM STRUCTURE — Do word sequences show real syntactic patterns
       (e.g., "A B" always in that order), or is order random? This
       tests whether we're looking at real language vs cipher/random.
"""

import re, json, sys, io, random
from pathlib import Path
from collections import Counter, defaultdict
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
# PHASE 28a: PERMUTATION TEST (Gallows Section Enrichment)
# ══════════════════════════════════════════════════════════════════

def run_permutation_test(tokens, n_perms=1000):
    print("=" * 76)
    print("PHASE 28a: PERMUTATION TEST — ARE GALLOWS DISTRIBUTIONS REAL?")
    print("=" * 76)
    print()
    print(f"We compute gallows-section enrichment for real data, then shuffle")
    print(f"section labels {n_perms} times to build a null distribution.")
    print(f"If real enrichment is in the top 5%, it's statistically significant.")
    print()

    # Compute real enrichment scores
    det_sections = defaultdict(Counter)
    section_counts = Counter()
    for word, section, folio in tokens:
        d = full_decompose(word)
        det = d['determinative']
        section_counts[section] += 1
        if det:
            det_sections[det][section] += 1

    total = sum(section_counts.values())

    # Define target enrichments to test
    targets = [
        ('k', 'bio', 'k(substance) enriched in bio'),
        ('t', 'cosmo', 't(celestial) enriched in cosmo'),
        ('f', 'herbal-A', 'f(botanical) enriched in herbal'),
        ('p', 'text', 'p(discourse) enriched in text'),
    ]

    real_enrichments = {}
    for det, sec, label in targets:
        det_total = sum(det_sections[det].values())
        sec_total = section_counts.get(sec, 0)
        if det_total > 0 and sec_total > 0:
            observed = det_sections[det].get(sec, 0) / det_total
            expected = sec_total / total
            real_enrichments[(det, sec)] = observed / expected
        else:
            real_enrichments[(det, sec)] = 0.0

    # Print real values
    for det, sec, label in targets:
        enr = real_enrichments[(det, sec)]
        print(f"  REAL: {label}: {enr:.3f}x")

    # Permutation test: shuffle section labels
    print(f"\n  Running {n_perms} permutations...")
    random.seed(42)

    # Precompute: for each token, store (det, section)
    token_dets = []
    token_sects = []
    for word, section, folio in tokens:
        d = full_decompose(word)
        token_dets.append(d['determinative'])
        token_sects.append(section)

    # Count how many permutations produce enrichment >= real
    perm_counts = {(det, sec): 0 for det, sec, _ in targets}

    for perm_i in range(n_perms):
        shuffled_sects = token_sects[:]
        random.shuffle(shuffled_sects)

        perm_det_sects = defaultdict(Counter)
        perm_sec_counts = Counter()
        for i in range(len(token_dets)):
            det = token_dets[i]
            sec = shuffled_sects[i]
            perm_sec_counts[sec] += 1
            if det:
                perm_det_sects[det][sec] += 1

        perm_total = sum(perm_sec_counts.values())
        for det, sec, label in targets:
            det_total = sum(perm_det_sects[det].values())
            sec_total = perm_sec_counts.get(sec, 0)
            if det_total > 0 and sec_total > 0:
                perm_enr = (perm_det_sects[det].get(sec, 0) / det_total) / (sec_total / perm_total)
            else:
                perm_enr = 0.0
            if perm_enr >= real_enrichments[(det, sec)]:
                perm_counts[(det, sec)] += 1

    # Print results
    print(f"\n  RESULTS (p-value = fraction of permutations ≥ real):")
    any_sig = False
    for det, sec, label in targets:
        p = perm_counts[(det, sec)] / n_perms
        real = real_enrichments[(det, sec)]
        sig = "*** SIGNIFICANT" if p < 0.05 else ("* marginal" if p < 0.10 else "not significant")
        if p < 0.05: any_sig = True
        print(f"    {label}: real={real:.3f}x, p={p:.3f} → {sig}")

    if any_sig:
        print(f"\n  At least one gallows-section enrichment is statistically significant.")
        print(f"  This means the gallows distribution is NOT random w.r.t. sections.")
    else:
        print(f"\n  *** NO gallows enrichments reach significance at p<0.05!")
        print(f"  *** The gallows-section associations may be random noise.")

    return real_enrichments, perm_counts


# ══════════════════════════════════════════════════════════════════
# PHASE 28b: POS RECLASSIFICATION
# ══════════════════════════════════════════════════════════════════

def run_pos_reclassification(tokens):
    print()
    print("=" * 76)
    print("PHASE 28b: POS RECLASSIFICATION BASED ON DATA")
    print("=" * 76)
    print()
    print("Phase 27 found POS mismatches. We reclassify based on prefix distributions.")
    print("Rule: if s% > 50% → verb. If d%+o% > s% and s%<20% → noun. Else → ambiguous.")
    print()

    # Compute prefix distributions for ALL roots with N≥10
    root_stats = defaultdict(lambda: {'total': 0, 'prefixes': Counter(), 'sections': Counter()})
    for word, section, folio in tokens:
        d = full_decompose(word)
        root = d['root']
        root_stats[root]['total'] += 1
        root_stats[root]['prefixes'][d['prefix']] += 1
        root_stats[root]['sections'][section] += 1

    print(f"  {'Root':10s} {'N':>6s} {'d%':>6s} {'o%':>6s} {'s%':>6s} {'y%':>6s} {'bare%':>6s}  DATA-POS   NOTES")

    all_classified = []
    for root in sorted(root_stats.keys(), key=lambda r: -root_stats[r]['total']):
        stats = root_stats[root]
        n = stats['total']
        if n < 10: continue
        pfx = stats['prefixes']
        d_pct = 100*(pfx.get('d',0)+pfx.get('do',0))/n
        o_pct = 100*pfx.get('o',0)/n
        s_pct = 100*(pfx.get('s',0)+pfx.get('so',0))/n
        y_pct = 100*pfx.get('y',0)/n
        bare_pct = 100*pfx.get('',0)/n

        # Classify by data
        if s_pct > 50:
            data_pos = 'VERB'
        elif (d_pct + o_pct) > s_pct and s_pct < 20 and bare_pct < 85:
            data_pos = 'NOUN'
        elif bare_pct > 85:
            data_pos = 'BARE'  # almost always bare — possibly a function word or compound-initial
        else:
            data_pos = 'AMBIG'

        notes = ""
        # Flag root length
        if len(root) <= 2:
            notes += "short "
        if n < 20:
            notes += "low-N "

        all_classified.append((root, n, d_pct, o_pct, s_pct, y_pct, bare_pct, data_pos, notes))

        if n >= 20:  # Only print roots with enough data
            print(f"  {root:10s} {n:6d} {d_pct:6.1f} {o_pct:6.1f} {s_pct:6.1f} {y_pct:6.1f} {bare_pct:6.1f}  {data_pos:10s} {notes}")

    # Summary
    pos_counts = Counter(pos for root, n, d_p, o_p, s_p, y_p, b_p, pos, notes in all_classified if n >= 20)
    print(f"\n  POS distribution (N≥20 roots):")
    for pos, count in pos_counts.most_common():
        print(f"    {pos}: {count} roots")

    # Critical reclassifications
    print(f"\n  CRITICAL RECLASSIFICATIONS:")
    reclasses = [
        ('ho', 'noun→VERB', '98.5% s-prefix, 0% d/o'),
        ('ch', 'verb→BARE', '0.9% s-prefix, 89.3% bare — compound-initial, not free verb'),
        ('ol', 'verb→NOUN', '3.8% s-prefix, 48% bare, 22% qo — relativized noun'),
        ('cho', 'noun→BARE', '93.5% bare — always compound-initial'),
        ('chol', 'noun→BARE', '94.4% bare — always compound-initial'),
    ]
    for root, change, evidence in reclasses:
        print(f"    {root:8s}: {change:20s} — {evidence}")

    # Demotions
    print(f"\n  DEMOTIONS (insufficient evidence):")
    demotions = [
        ('esed', 'lion', 1, 'Only 1 token in entire corpus'),
        ('yed', 'hand', 5, 'Only 5 tokens'),
        ('rar', 'king', 0, 'Check actual count'),
        ('eosh', 'dry', 0, 'Check actual count'),
        ('sheo', 'dry', 0, 'Check actual count'),
        ('choam', 'hot', 0, 'Check actual count'),
    ]
    for root, meaning, expected_n, reason in demotions:
        actual_n = root_stats.get(root, {}).get('total', 0)
        status = "KEEP" if actual_n >= 20 else ("DEMOTE" if actual_n >= 5 else "REMOVE")
        print(f"    {root:8s} ({meaning:15s}): {actual_n:4d} tokens → {status} ({reason})")

    return all_classified


# ══════════════════════════════════════════════════════════════════
# PHASE 28c: QOKEDY INVESTIGATION
# ══════════════════════════════════════════════════════════════════

def run_qokedy_investigation(tokens):
    print()
    print("=" * 76)
    print("PHASE 28c: QOKEDY PATTERN INVESTIGATION")
    print("=" * 76)
    print()
    print("qokedy (and variants qokeedy, qokchdy etc.) dominate f78r.")
    print("QUESTION: Is our parsing qo+k+e+dy correct, or is this an")
    print("atomic word/formula that we're wrongly decomposing?")
    print()

    # Count all tokens that decompose to root 'e' with qo- prefix
    qo_e_tokens = Counter()
    other_e_tokens = Counter()
    all_word_forms = Counter()
    
    for word, section, folio in tokens:
        all_word_forms[word] += 1
        d = full_decompose(word)
        if d['root'] == 'e':
            if d['prefix'].startswith('qo') or d['prefix'] == 'q':
                qo_e_tokens[word] += 1
            else:
                other_e_tokens[word] += 1

    # Show the qokedy family
    print(f"  WORDS DECOMPOSING TO qo-prefix + 'e' root:")
    print(f"  {'Word':20s} {'Count':>6s}  Decomposition")
    qo_total = 0
    for word, count in qo_e_tokens.most_common(20):
        d = full_decompose(word)
        decomp = f"pfx={d['prefix']}, det={d['determinative']}, root={d['root']}, sfx={d['suffix']}"
        print(f"  {word:20s} {count:6d}  {decomp}")
        qo_total += count
    print(f"  {'TOTAL':20s} {qo_total:6d}")

    # What fraction of ALL tokens is this?
    print(f"\n  qo+e family: {qo_total}/{len(tokens)} = {100*qo_total/len(tokens):.1f}% of all tokens")

    # Now check: do these words have real positional preferences?
    # In natural language, words appear in specific positions within lines.
    # If qokedy is a real word, it should have preferred positions.
    print(f"\n  POSITIONAL ANALYSIS (where does qokedy[-like] appear in lines?):")
    folio_lines = load_folio_lines()
    
    qo_positions = Counter()  # position in line (0=first, etc.)
    qo_line_lengths = Counter()
    non_qo_positions = Counter()
    
    for lid, section, words in folio_lines:
        n = len(words)
        for i, w in enumerate(words):
            d = full_decompose(w)
            if d['root'] == 'e' and (d['prefix'].startswith('qo') or d['prefix'] == 'q'):
                # Normalize position to 0-9 range
                norm_pos = int(i / n * 10) if n > 0 else 0
                qo_positions[norm_pos] += 1
                qo_line_lengths[n] += 1
            else:
                norm_pos = int(i / n * 10) if n > 0 else 0
                non_qo_positions[norm_pos] += 1

    print(f"  Position (0=start, 9=end):")
    print(f"  {'Pos':>4s} {'qo+e':>7s} {'other':>7s} {'qo+e%':>7s} {'other%':>7s} {'ratio':>7s}")
    for pos in range(10):
        qo = qo_positions.get(pos, 0)
        nq = non_qo_positions.get(pos, 0)
        qo_pct = 100*qo/qo_total if qo_total > 0 else 0
        nq_total = sum(non_qo_positions.values())
        nq_pct = 100*nq/nq_total if nq_total > 0 else 0
        ratio = qo_pct/nq_pct if nq_pct > 0 else 0
        print(f"  {pos:4d} {qo:7d} {nq:7d} {qo_pct:6.1f}% {nq_pct:6.1f}% {ratio:6.2f}x")

    # Test: Consecutive qokedy — how often does qokedy follow qokedy?
    print(f"\n  CONSECUTIVE qo+e PATTERNS:")
    consecutive = 0
    total_qo_after = 0
    for lid, section, words in folio_lines:
        for i in range(len(words)-1):
            d1 = full_decompose(words[i])
            d2 = full_decompose(words[i+1])
            is1 = d1['root'] == 'e' and (d1['prefix'].startswith('qo') or d1['prefix'] == 'q')
            is2 = d2['root'] == 'e' and (d2['prefix'].startswith('qo') or d2['prefix'] == 'q')
            if is1:
                total_qo_after += 1
                if is2:
                    consecutive += 1
    if total_qo_after > 0:
        print(f"  Times qo+e followed by another qo+e: {consecutive}/{total_qo_after} = {100*consecutive/total_qo_after:.1f}%")
        print(f"  Expected if random (given {100*qo_total/len(tokens):.1f}% frequency): {100*qo_total/len(tokens):.1f}%")
        print(f"  Ratio observed/expected: {(consecutive/total_qo_after) / (qo_total/len(tokens)):.2f}x")

    # Alternative decomposition test: what if we DON'T decompose these?
    # Count unique raw word forms in the qo+k+e family
    print(f"\n  UNIQUE WORD FORMS in qo+e family: {len(qo_e_tokens)}")
    print(f"  If this were a single formulaic word, we'd expect ~few forms.")
    print(f"  Many distinct forms suggest real morphological variation.")

    # Show the variety of suffixes
    sfx_counts = Counter()
    det_counts = Counter()
    for word in qo_e_tokens:
        d = full_decompose(word)
        sfx_counts[d['suffix']] += qo_e_tokens[word]
        det_counts[d['determinative']] += qo_e_tokens[word]
    print(f"  Suffix variety: {dict(sfx_counts.most_common(10))}")
    print(f"  Det variety: {dict(det_counts.most_common(5))}")

    return {'qo_total': qo_total, 'pct': 100*qo_total/len(tokens)}


# ══════════════════════════════════════════════════════════════════
# PHASE 28d: LONG-ROOT CENSUS
# ══════════════════════════════════════════════════════════════════

def run_long_root_census(tokens):
    print()
    print("=" * 76)
    print("PHASE 28d: LONG-ROOT CENSUS (3+ chars only)")
    print("=" * 76)
    print()
    print("Short roots inflate coverage. The real signal is in longer roots")
    print("that are less likely to match by accident. Listing ALL roots with")
    print("3+ chars and N≥10.")
    print()

    # Known long roots
    known_long = {
        'che','cho','chol','cham','chas','ches','cheos','ched','chod',
        'alch','lch','she','les','ran','res','eos','eosh','sheo','choam',
        'rar','esed','yed','hed'
    }

    root_counts = Counter()
    root_sections = defaultdict(Counter)
    root_prefixes = defaultdict(Counter)
    root_suffixes = defaultdict(Counter)

    for word, section, folio in tokens:
        d = full_decompose(word)
        root = d['root']
        if len(root) >= 3:
            root_counts[root] += 1
            root_sections[root][section] += 1
            root_prefixes[root][d['prefix']] += 1
            root_suffixes[root][d['suffix']] += 1

    print(f"  UNKNOWN LONG ROOTS (3+ chars, N≥10):")
    print(f"  {'Root':12s} {'N':>5s}  {'Top section':12s} {'Top pfx':>8s} {'Top sfx':>8s}  {'d%':>5s} {'o%':>5s} {'s%':>5s}")
    
    unknown_total = 0
    unknown_list = []
    for root, count in root_counts.most_common(100):
        if root in known_long or count < 10: continue
        n = count
        top_sec = root_sections[root].most_common(1)[0][0] if root_sections[root] else '?'
        top_pfx = root_prefixes[root].most_common(1)[0][0] or 'bare'
        top_sfx = root_suffixes[root].most_common(1)[0][0] or 'bare'
        d_pct = 100*(root_prefixes[root].get('d',0)+root_prefixes[root].get('do',0))/n
        o_pct = 100*root_prefixes[root].get('o',0)/n
        s_pct = 100*(root_prefixes[root].get('s',0)+root_prefixes[root].get('so',0))/n
        print(f"  {root:12s} {n:5d}  {top_sec:12s} {top_pfx:>8s} {top_sfx:>8s}  {d_pct:5.1f} {o_pct:5.1f} {s_pct:5.1f}")
        unknown_total += count
        unknown_list.append((root, count))

    print(f"\n  Total unknown long-root tokens: {unknown_total}")
    print(f"  Total long-root tokens (known+unknown): {sum(root_counts.values())}")
    total = len(tokens)
    print(f"  Unknown long roots as % of corpus: {100*unknown_total/total:.1f}%")

    # Also show known long roots for comparison
    print(f"\n  KNOWN LONG ROOTS (for comparison):")
    print(f"  {'Root':12s} {'N':>5s}  {'Top section':12s}")
    for root, count in root_counts.most_common(100):
        if root in known_long and count >= 5:
            top_sec = root_sections[root].most_common(1)[0][0]
            print(f"  {root:12s} {count:5d}  {top_sec:12s}")

    return unknown_list


# ══════════════════════════════════════════════════════════════════
# PHASE 28e: BIGRAM STRUCTURE TEST
# ══════════════════════════════════════════════════════════════════

def run_bigram_test(tokens):
    print()
    print("=" * 76)
    print("PHASE 28e: BIGRAM STRUCTURE TEST — IS THIS REAL LANGUAGE?")
    print("=" * 76)
    print()
    print("QUESTION: Do word-pairs show directional preferences (A→B more")
    print("common than B→A)? Real language has syntax; random sequences don't.")
    print()

    # Build bigrams from folio lines
    folio_lines = load_folio_lines()
    bigrams = Counter()
    reverse_bigrams = Counter()
    unigrams = Counter()

    for lid, section, words in folio_lines:
        decomposed = [full_decompose(w) for w in words]
        # Use (root, determinative, prefix-class) as abstract word type
        types = []
        for d in decomposed:
            # Abstract: just root + prefix-class + det
            pfx_class = 'nominal' if d['prefix'] in ['d','do','o','qo','q','y'] else ('verbal' if d['prefix'] in ['s','so'] else 'bare')
            types.append((d['root'], d['determinative'] or '_', pfx_class))
        
        for i in range(len(types) - 1):
            a, b = types[i], types[i+1]
            bigrams[(a, b)] += 1
            reverse_bigrams[(b, a)] += 1
            unigrams[a] += 1
        if types:
            unigrams[types[-1]] += 1

    # Find strongly directional bigrams (A→B >> B→A or vice versa)
    print(f"  Total bigram types: {len(bigrams)}")
    print(f"  Total bigram tokens: {sum(bigrams.values())}")
    
    # Compute directionality for frequent bigrams
    directional = []
    for (a, b), count in bigrams.most_common(500):
        if count < 5: continue
        rev_count = bigrams.get((b, a), 0)
        if a == b: continue  # skip self-loops
        total = count + rev_count
        if total < 10: continue
        ratio = count / rev_count if rev_count > 0 else count
        directional.append((a, b, count, rev_count, ratio))

    directional.sort(key=lambda x: -x[4])

    print(f"\n  TOP 20 MOST DIRECTIONAL BIGRAMS (A→B vs B→A):")
    print(f"  {'A':30s} → {'B':30s}  {'A→B':>5s} {'B→A':>5s} {'ratio':>7s}")
    for a, b, ab, ba, ratio in directional[:20]:
        a_str = f"{a[2]}:{a[1]}:{a[0]}" if a[0] else f"{a[2]}:{a[1]}"
        b_str = f"{b[2]}:{b[1]}:{b[0]}" if b[0] else f"{b[2]}:{b[1]}"
        print(f"  {a_str:30s} → {b_str:30s}  {ab:5d} {ba:5d} {ratio:7.1f}x")

    # Overall directionality score: for all bigrams with N≥10, what fraction
    # show >2x directionality?
    tested = 0
    directional_count = 0
    for (a, b), count in bigrams.items():
        if count < 5 or a == b: continue
        rev = bigrams.get((b, a), 0)
        if count + rev < 10: continue
        tested += 1
        ratio = max(count, rev) / min(count, rev) if min(count, rev) > 0 else max(count, rev)
        if ratio > 2:
            directional_count += 1

    if tested > 0:
        dir_pct = 100*directional_count/tested
        print(f"\n  DIRECTIONALITY SCORE: {directional_count}/{tested} frequent bigrams show >2x asymmetry ({dir_pct:.0f}%)")
        print(f"  In natural language, expect 50-80%.")
        print(f"  In random text, expect ~0%.")
        print(f"  In a cipher of natural language, expect similar to natural.")
        if dir_pct > 40:
            print(f"  → RESULT: Strong directional structure. This looks like real language.")
        elif dir_pct > 20:
            print(f"  → RESULT: Moderate structure. Could be language with some formulaic elements.")
        else:
            print(f"  → RESULT: Weak structure. Concerning — might be random or very formulaic.")

    # Entropy comparison: compute bigram entropy vs shuffled
    print(f"\n  BIGRAM ENTROPY TEST:")
    total_bg = sum(bigrams.values())
    bg_probs = [c/total_bg for c in bigrams.values()]
    real_entropy = -sum(p * (p and (p > 0) and __import__('math').log2(p)) for p in bg_probs if p > 0)
    print(f"  Real bigram entropy: {real_entropy:.2f} bits")

    # Shuffled: randomize word order within each line, recompute
    random.seed(42)
    shuffled_bigrams = Counter()
    for lid, section, words in folio_lines:
        shuffled_words = words[:]
        random.shuffle(shuffled_words)
        decomposed = [full_decompose(w) for w in shuffled_words]
        types = []
        for d in decomposed:
            pfx_class = 'nominal' if d['prefix'] in ['d','do','o','qo','q','y'] else ('verbal' if d['prefix'] in ['s','so'] else 'bare')
            types.append((d['root'], d['determinative'] or '_', pfx_class))
        for i in range(len(types) - 1):
            shuffled_bigrams[types[i], types[i+1]] += 1

    total_sbg = sum(shuffled_bigrams.values())
    sbg_probs = [c/total_sbg for c in shuffled_bigrams.values()]
    shuffled_entropy = -sum(p * __import__('math').log2(p) for p in sbg_probs if p > 0)
    print(f"  Shuffled bigram entropy: {shuffled_entropy:.2f} bits")
    print(f"  Difference: {shuffled_entropy - real_entropy:.2f} bits")
    if shuffled_entropy > real_entropy:
        print(f"  → Real text has LOWER entropy (more structure) than shuffled. Consistent with language.")
    else:
        print(f"  → Real text has HIGHER entropy than shuffled. Unusual — possible random generation.")

    return {'directionality_pct': dir_pct if tested > 0 else 0}


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("PHASE 28: STATISTICAL SIGNIFICANCE, POS FIX & LONG-ROOT FOCUS")
    print("=" * 76)

    tokens = load_all_tokens()
    print(f"Loaded {len(tokens)} word tokens\n")

    # 28a: Permutation test
    r_28a_enrich, r_28a_perms = run_permutation_test(tokens, n_perms=1000)

    # 28b: POS reclassification
    r_28b = run_pos_reclassification(tokens)

    # 28c: qokedy investigation
    r_28c = run_qokedy_investigation(tokens)

    # 28d: Long-root census
    r_28d = run_long_root_census(tokens)

    # 28e: Bigram structure test
    r_28e = run_bigram_test(tokens)

    # Summary
    print()
    print("=" * 76)
    print("PHASE 28: OVERALL SUMMARY")
    print("=" * 76)
    print()
    print("  28a — Permutation test: see p-values above")
    print("  28b — POS reclassification: ho→verb, ch→bare, ol→noun, cho/chol→bare")
    print("  28c — qokedy: see positional and consecutive analysis")
    print("  28d — Long-root census: real targets for vocabulary expansion")
    print("  28e — Bigram test: directionality score indicates language structure")

    results = {
        'permutation_enrichments': {f"{k[0]}_{k[1]}": v for k, v in r_28a_enrich.items()},
        'long_root_unknowns': [(r, c) for r, c in r_28d[:20]],
        'bigram_directionality': r_28e.get('directionality_pct', 0),
    }
    json.dump(results, open(Path("results/phase28_results.json"), 'w'), indent=2, default=str)
    print(f"\n  Results saved to results/phase28_results.json")


if __name__ == '__main__':
    import contextlib
    outpath = Path("results/phase28_output.txt")
    with open(outpath, 'w', encoding='utf-8') as f:
        with contextlib.redirect_stdout(f):
            main()
    print(open(outpath, encoding='utf-8').read())
