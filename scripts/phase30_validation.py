#!/usr/bin/env python3
"""
Phase 30 — Skeptical Re-Validation & Revised Model Test
========================================================

Phase 29 made bold claims. This phase STRESS-TESTS them:

  30a) NULL MODEL FOR COMPOUND DECOMPOSITION
       With ~15 stems of 1-3 chars using only {a,e,o,d,l,r,s,m,i},
       what fraction of RANDOM strings also decompose? If it's also
       ~99%, our Phase 29 "finding" is an artifact of short stems.

  30b) SPECIFICITY TEST: DO COMPOUNDS PRESERVE PART DISTRIBUTIONS?
       If cheo = che+o is real, then cheo's section distribution should
       resemble a BLEND of che's and o's distributions. If not, it's
       just a string match, not a real compound.

  30c) h- PREFIX PERMUTATION TEST
       Shuffle h- prefix assignment across all roots. How often do
       we get 10/10 "verbs" starting with the same letter by chance?

  30d) SEMITIC CONSTRUCT-CHAIN TEST (smikhut murkevet)
       In Hebrew, repeated NOUN+NOUN construct chains add formality.
       Test: do we see N+N+N chains? Are some roots used in
       "stacking" patterns more than others? Is there positional
       regularity (X always first, Y always second)?

  30e) FULL CORPUS RE-PARSE UNDER REVISED MODEL
       Parse every token into 5-slot model:
       GRAM-PREFIX + DET + DERIV-PREFIX + STEM + SUFFIX
       Measure: what % parse cleanly? What's left over?

  30f) PARADIGM TABLE CONSTRUCTION
       For each stem, list all attested DERIV-PREFIX + STEM combos
       and check for paradigmatic regularity (like verb conjugations).
"""

import re, json, sys, io, math, random
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
# MORPHOLOGICAL PIPELINE (same as prior phases)
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

# Derivational prefixes (revised model)
DERIV_PREFIXES = ['ch','sh','lch','lsh','l','h']  # ordered longest-first where needed




def parse_morphology(w):
    pfx = sfx = ""
    for pf in PREFIXES:
        if w.startswith(pf) and len(w) > len(pf)+1:
            pfx = pf; w = w[len(pf):]; break
    for sf in SUFFIXES:
        if w.endswith(sf) and len(w) > len(sf):
            sfx = sf; w = w[:-len(sf)]; break
    return pfx, w, sfx


def revised_decompose(word):
    """5-slot revised model parse."""
    stripped, gals = strip_gallows(word)
    collapsed = collapse_echains(stripped)
    pfx, root, sfx = parse_morphology(collapsed)
    bases = [gallows_base(g) for g in gals]

    # Now try to split root into deriv-prefix + stem
    deriv = ""
    stem = root
    # Order matters: try longer derivational prefixes first
    for dp in ['lch','lsh','ch','sh','l','h']:
        if root.startswith(dp) and len(root) > len(dp):
            deriv = dp
            stem = root[len(dp):]
            break

    return dict(
        original=word,
        gram_prefix=pfx or "",
        det=bases[0] if bases else "",
        deriv_prefix=deriv,
        stem=stem,
        suffix=sfx or "",
        all_gallows=bases,
        old_root=root  # for comparison
    )

# ══════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════

FOLIO_DIR = Path("folios")




# ══════════════════════════════════════════════════════════════════
# 30a: NULL MODEL — CAN RANDOM STRINGS ALSO DECOMPOSE?
# ══════════════════════════════════════════════════════════════════

def run_null_model_test(tokens):
    print("=" * 76)
    print("PHASE 30a: NULL MODEL — COMPOUND DECOMPOSITION ARTIFACT TEST")
    print("=" * 76)
    print()
    print("SKEPTICAL QUESTION: With ~15 short stems (1-3 chars) drawn from")
    print("only ~9 distinct characters {a,e,o,d,l,r,s,m,i}, might ANY")
    print("random 3-5 char string decompose into two 'known' parts?")
    print()

    # Get the actual root frequency table
    root_counts = Counter()
    for word, section, folio in tokens:
        d = full_decompose(word)
        root_counts[d['root']] += 1

    # The set of "real" roots we used in Phase 29 (N≥10)
    real_roots = {r for r, c in root_counts.items() if c >= 10}

    # Characters actually used in roots
    root_chars = set()
    for r in real_roots:
        root_chars.update(r)
    root_chars = sorted(root_chars)
    print(f"  Characters in real roots (N≥10): {''.join(root_chars)} ({len(root_chars)} chars)")
    print(f"  Number of real roots (N≥10): {len(real_roots)}")
    print(f"  Lengths: {Counter(len(r) for r in real_roots)}")
    print()

    # Generate random strings and test decomposability
    random.seed(42)
    n_random = 5000

    for strlen in [3, 4, 5, 6]:
        decomposable = 0
        for _ in range(n_random):
            rand_str = ''.join(random.choices(root_chars, k=strlen))
            # Try all split points
            found = False
            for i in range(1, len(rand_str)):
                p1, p2 = rand_str[:i], rand_str[i:]
                if p1 in real_roots and p2 in real_roots:
                    found = True
                    break
            if found:
                decomposable += 1
        pct = 100 * decomposable / n_random
        print(f"  Random {strlen}-char strings decomposable: {decomposable}/{n_random} ({pct:.1f}%)")

    # MORE STRICT TEST: use only the N≥5 threshold from Phase 29
    real_roots_5 = {r for r, c in root_counts.items() if c >= 5}
    print(f"\n  With N≥5 threshold ({len(real_roots_5)} roots):")
    for strlen in [3, 4, 5]:
        decomposable = 0
        for _ in range(n_random):
            rand_str = ''.join(random.choices(root_chars, k=strlen))
            found = False
            for i in range(1, len(rand_str)):
                p1, p2 = rand_str[:i], rand_str[i:]
                if p1 in real_roots_5 and p2 in real_roots_5:
                    found = True
                    break
            if found:
                decomposable += 1
        pct = 100 * decomposable / n_random
        print(f"  Random {strlen}-char strings decomposable: {decomposable}/{n_random} ({pct:.1f}%)")

    # EVEN STRICTER: only use the ~15 "core stems" from revised model
    core_stems = {'e','o','ed','eo','od','ol','al','am','ar','or','es','eod','eos','os','a','d','l','r','s'}
    print(f"\n  With ONLY 'core stems' ({len(core_stems)} stems):")
    for strlen in [3, 4, 5]:
        decomposable = 0
        for _ in range(n_random):
            rand_str = ''.join(random.choices(root_chars, k=strlen))
            found = False
            for i in range(1, len(rand_str)):
                p1, p2 = rand_str[:i], rand_str[i:]
                if p1 in core_stems and p2 in core_stems:
                    found = True
                    break
            if found:
                decomposable += 1
        pct = 100 * decomposable / n_random
        print(f"  Random {strlen}-char strings decomposable: {decomposable}/{n_random} ({pct:.1f}%)")

    # FINAL TEST: are ACTUAL long roots MORE decomposable than random?
    actual_unknowns = [r for r, c in root_counts.items() if len(r) >= 3 and c >= 10]
    actual_decomp = 0
    for root in actual_unknowns:
        for i in range(1, len(root)):
            p1, p2 = root[:i], root[i:]
            if root_counts.get(p1,0) >= 5 and root_counts.get(p2,0) >= 5:
                actual_decomp += 1
                break
    actual_pct = 100 * actual_decomp / len(actual_unknowns) if actual_unknowns else 0

    # Generate random strings with SAME length distribution as actual unknowns
    length_dist = [len(r) for r in actual_unknowns]
    random_decomp = 0
    n_trials = 1000
    random_pcts = []
    for trial in range(n_trials):
        trial_decomp = 0
        for slen in length_dist:
            rand_str = ''.join(random.choices(root_chars, k=slen))
            for i in range(1, len(rand_str)):
                p1, p2 = rand_str[:i], rand_str[i:]
                if root_counts.get(p1,0) >= 5 and root_counts.get(p2,0) >= 5:
                    trial_decomp += 1
                    break
        random_pcts.append(100 * trial_decomp / len(length_dist))

    avg_random_pct = sum(random_pcts) / len(random_pcts)
    sd_random = (sum((x - avg_random_pct)**2 for x in random_pcts) / len(random_pcts))**0.5

    print(f"\n  HEAD-TO-HEAD COMPARISON:")
    print(f"  Actual long roots decomposable: {actual_decomp}/{len(actual_unknowns)} ({actual_pct:.1f}%)")
    print(f"  Random strings (same lengths):  avg {avg_random_pct:.1f}% (SD {sd_random:.1f}%)")
    z_score = (actual_pct - avg_random_pct) / sd_random if sd_random > 0 else 0
    print(f"  Z-score: {z_score:.2f}")

    if z_score > 2:
        print(f"  → ACTUAL roots decompose MORE than random (z={z_score:.1f}). Compounds are REAL.")
    elif z_score > 0:
        print(f"  → Actual roots decompose slightly more, but not significantly.")
        print(f"  → COMPOUND DECOMPOSITION MAY BE PARTLY ARTIFACTUAL.")
    else:
        print(f"  → Random strings decompose JUST AS WELL. Phase 29 compounding is AN ARTIFACT.")
        print(f"  → RETRACT the compound decomposition claim.")

    return {'actual_pct': actual_pct, 'random_pct': avg_random_pct, 'z_score': z_score}


# ══════════════════════════════════════════════════════════════════
# 30b: DISTRIBUTIONAL SPECIFICITY — DO COMPOUNDS BLEND PARENTS?
# ══════════════════════════════════════════════════════════════════

def run_distribution_blend_test(tokens):
    print()
    print("=" * 76)
    print("PHASE 30b: DO COMPOUNDS INHERIT PARENT DISTRIBUTIONS?")
    print("=" * 76)
    print()
    print("If cheo = che+o is a REAL compound, its section distribution should")
    print("resemble a blend of che's and o's distributions. Test via cosine")
    print("similarity between compound dist and average-of-parents dist.")
    print()

    # Build section distributions for all roots
    root_sections = defaultdict(Counter)
    root_counts = Counter()
    section_counts = Counter()
    sections_list = ['bio','cosmo','herbal-A','herbal-B','pharma','text','zodiac','unknown']

    for word, section, folio in tokens:
        d = full_decompose(word)
        root = d['root']
        root_sections[root][section] += 1
        root_counts[root] += 1
        section_counts[section] += 1

    def section_vec(root):
        n = root_counts.get(root, 0)
        if n == 0: return [0]*len(sections_list)
        return [root_sections[root].get(s, 0)/n for s in sections_list]

    def cosine_sim(v1, v2):
        dot = sum(a*b for a, b in zip(v1, v2))
        n1 = sum(a*a for a in v1)**0.5
        n2 = sum(b*b for b in v2)**0.5
        if n1 == 0 or n2 == 0: return 0
        return dot / (n1 * n2)

    def blend_vec(v1, v2):
        return [(a+b)/2 for a, b in zip(v1, v2)]

    # Test the specific compounds from Phase 29
    test_compounds = [
        ('cheo', 'che', 'o'),
        ('ech', 'e', 'ch'),
        ('heo', 'he', 'o'),
        ('chd', 'ch', 'd'),
        ('eol', 'e', 'ol'),
        ('hod', 'ho', 'd'),
        ('ald', 'al', 'd'),
        ('lche', 'l', 'che'),
        ('chl', 'ch', 'l'),
        ('alsh', 'al', 'sh'),
        ('chor', 'ch', 'or'),
        ('aram', 'ar', 'am'),
        ('cheol', 'che', 'ol'),
        ('chal', 'ch', 'al'),
        ('arch', 'ar', 'ch'),
        ('esh', 'e', 'sh'),
        ('alam', 'al', 'am'),
        ('lam', 'l', 'am'),
    ]

    print(f"  {'Compound':10s} {'N':>5s}  {'cos(C,blend)':>12s} {'cos(C,p1)':>10s} {'cos(C,p2)':>10s}  Verdict")

    real_sims = []
    for compound, p1, p2 in test_compounds:
        n = root_counts.get(compound, 0)
        if n < 10: continue

        vc = section_vec(compound)
        v1 = section_vec(p1)
        v2 = section_vec(p2)
        vb = blend_vec(v1, v2)

        sim_blend = cosine_sim(vc, vb)
        sim_p1 = cosine_sim(vc, v1)
        sim_p2 = cosine_sim(vc, v2)

        verdict = "SUPPORTS" if sim_blend > 0.85 else ("WEAK" if sim_blend > 0.7 else "AGAINST")
        print(f"  {compound:10s} {n:5d}  {sim_blend:12.3f} {sim_p1:10.3f} {sim_p2:10.3f}  {verdict}")
        real_sims.append(sim_blend)

    # Null model: random pairs of roots
    random.seed(42)
    common_roots = [r for r, c in root_counts.items() if c >= 20]
    null_sims = []
    for _ in range(500):
        r1, r2 = random.sample(common_roots, 2)
        r3 = random.choice(common_roots)
        v1 = section_vec(r1)
        v2 = section_vec(r2)
        v3 = section_vec(r3)
        vb = blend_vec(v1, v2)
        null_sims.append(cosine_sim(v3, vb))

    avg_real = sum(real_sims) / len(real_sims) if real_sims else 0
    avg_null = sum(null_sims) / len(null_sims) if null_sims else 0
    print(f"\n  Average cosine(compound, blend): {avg_real:.3f}")
    print(f"  Average cosine(random, blend):   {avg_null:.3f}")

    if avg_real > avg_null + 0.05:
        print(f"  → Compounds resemble parent blends MORE than random. Supports real compounding.")
    elif avg_real > avg_null - 0.05:
        print(f"  → No difference from random. Compounds may be DISTRIBUTIONAL ARTIFACTS.")
    else:
        print(f"  → Compounds resemble parents LESS than random. Compounding claim is WRONG.")

    return {'avg_real': avg_real, 'avg_null': avg_null}


# ══════════════════════════════════════════════════════════════════
# 30c: h- PREFIX PERMUTATION TEST
# ══════════════════════════════════════════════════════════════════

def run_h_prefix_permutation(tokens):
    print()
    print("=" * 76)
    print("PHASE 30c: h- VERBAL PREFIX — PERMUTATION TEST")
    print("=" * 76)
    print()
    print("Is it remarkable that 10/10 verbal roots start with 'h'?")
    print("Or could this happen by chance given the character frequencies?")
    print()

    root_counts = Counter()
    root_prefixes = defaultdict(Counter)
    for word, section, folio in tokens:
        d = full_decompose(word)
        root_counts[d['root']] += 1
        root_prefixes[d['root']][d['prefix']] += 1

    # Get all roots with N≥20 and their s% (verbal score)
    all_roots_N20 = []
    for root, n in root_counts.items():
        if n < 20: continue
        pfx = root_prefixes[root]
        s_pct = (pfx.get('s',0) + pfx.get('so',0)) / n
        all_roots_N20.append((root, n, s_pct))

    # How many start with h?
    h_initial = [r for r, n, sp in all_roots_N20 if r.startswith('h') and not r.startswith('ch')]
    total = len(all_roots_N20)
    h_count = len(h_initial)
    print(f"  Roots with N≥20: {total}")
    print(f"  h-initial roots: {h_count} ({100*h_count/total:.1f}%)")

    # Verbal roots (s%>50%)
    verbal = [(r, n, sp) for r, n, sp in all_roots_N20 if sp > 0.5]
    verbal_h = [r for r, n, sp in verbal if r.startswith('h') and not r.startswith('ch')]
    print(f"  Verbal roots (s%>50%): {len(verbal)}")
    print(f"  Verbal AND h-initial: {len(verbal_h)}")
    print()

    # Permutation test: shuffle s% values across roots, count how often
    # ALL verbal roots share a common first letter
    random.seed(42)
    n_perms = 10000
    count_all_same = 0

    s_pcts = [sp for _, _, sp in all_roots_N20]
    root_names = [r for r, _, _ in all_roots_N20]

    for _ in range(n_perms):
        shuffled = s_pcts[:]
        random.shuffle(shuffled)
        # Find "verbal" under shuffled assignment
        perm_verbal = [root_names[i] for i, sp in enumerate(shuffled) if sp > 0.5]
        if len(perm_verbal) < 2:
            continue
        # Check if all share any common first letter
        first_chars = [r[0] for r in perm_verbal if len(r) > 0]
        if len(first_chars) < 2:
            continue
        if len(set(first_chars)) == 1:
            count_all_same += 1

    p_value = count_all_same / n_perms
    print(f"  Permutation test (10,000 shuffles):")
    print(f"  P(all verbal roots share first letter) = {p_value:.4f}")

    if p_value < 0.001:
        print(f"  → HIGHLY SIGNIFICANT. h- verbal prefix is NOT a coincidence.")
    elif p_value < 0.05:
        print(f"  → Significant at p<0.05. h- pattern is real but not overwhelmingly rare.")
    else:
        print(f"  → NOT SIGNIFICANT. h-initial verbal pattern could occur by chance.")

    # Additional: what's the base rate of h-initial among ALL roots?
    print(f"\n  Base rate: {h_count}/{total} = {100*h_count/total:.1f}% of roots are h-initial")
    print(f"  Expected verbal h-initial by chance: {len(verbal) * h_count/total:.1f} out of {len(verbal)}")
    print(f"  Observed: {len(verbal_h)} (all of them)")

    return {'p_value': p_value, 'n_verbal': len(verbal), 'n_verbal_h': len(verbal_h)}


# ══════════════════════════════════════════════════════════════════
# 30d: SEMITIC CONSTRUCT-CHAIN TEST (smikhut murkevet)
# ══════════════════════════════════════════════════════════════════

def run_construct_chain_test(tokens):
    print()
    print("=" * 76)
    print("PHASE 30d: SEMITIC CONSTRUCT-CHAIN TEST (SMIKHUT MURKEVET)")
    print("=" * 76)
    print()
    print("In Hebrew, smikhut murkevet chains nouns: X-shel-Y-shel-Z.")
    print("This adds formality/specificity. Test for analogous patterns:")
    print("  1) Do consecutive words share morphological structure?")
    print("  2) Are there repeated root sequences (X-Y-X, X-X, X-Y-Y)?")
    print("  3) Do bare (prefix-less) words chain together specifically?")
    print()

    folio_lines = load_folio_lines()

    # Build root sequences from lines
    root_bigrams = Counter()
    root_trigrams = Counter()
    root_self_repeat = 0
    root_total_bigrams = 0
    prefix_chains = Counter()  # (pfx1, pfx2) patterns
    deriv_chains = Counter()   # (deriv1, deriv2) patterns

    for lid, section, words in folio_lines:
        if len(words) < 2: continue
        decomposed = [revised_decompose(w) for w in words]

        for i in range(len(decomposed) - 1):
            d1, d2 = decomposed[i], decomposed[i+1]
            r1, r2 = d1['old_root'], d2['old_root']
            root_bigrams[(r1, r2)] += 1
            root_total_bigrams += 1
            if r1 == r2:
                root_self_repeat += 1
            prefix_chains[(d1['gram_prefix'], d2['gram_prefix'])] += 1
            deriv_chains[(d1['deriv_prefix'], d2['deriv_prefix'])] += 1

        for i in range(len(decomposed) - 2):
            d1, d2, d3 = decomposed[i], decomposed[i+1], decomposed[i+2]
            r1, r2, r3 = d1['old_root'], d2['old_root'], d3['old_root']
            root_trigrams[(r1, r2, r3)] += 1

    # Self-repetition rate
    print(f"  Root self-repetition (X-X): {root_self_repeat}/{root_total_bigrams} "
          f"({100*root_self_repeat/root_total_bigrams:.2f}%)")

    # Expected self-repetition under random (sum of p_i^2)
    root_counts = Counter()
    for word, section, folio in tokens:
        d = full_decompose(word)
        root_counts[d['root']] += 1
    total_tokens = sum(root_counts.values())
    expected_self = sum((c/total_tokens)**2 for c in root_counts.values())
    print(f"  Expected self-repeat under random: {100*expected_self:.2f}%")
    ratio = (root_self_repeat/root_total_bigrams) / expected_self if expected_self > 0 else 0
    print(f"  Ratio observed/expected: {ratio:.2f}x")
    if ratio > 2:
        print(f"  → STRONG self-repetition pattern. Construct-chain-like behavior.")
    elif ratio > 1.5:
        print(f"  → Moderate self-repetition. Some construct chaining possible.")
    else:
        print(f"  → Near baseline. No special self-repetition pattern.")

    # Most common root bigrams
    print(f"\n  TOP 20 ROOT BIGRAMS:")
    print(f"  {'Root1':8s} {'Root2':8s} {'Count':>5s}")
    for (r1, r2), count in root_bigrams.most_common(20):
        print(f"  {r1:8s} {r2:8s} {count:5d}")

    # Construct chain patterns: X-Y-X (ABA)
    print(f"\n  ABA TRIGRAMS (X-Y-X pattern, construct-chain candidates):")
    aba_count = 0
    aba_total = 0
    aba_examples = Counter()
    for (r1, r2, r3), count in root_trigrams.items():
        aba_total += count
        if r1 == r3 and r1 != r2:
            aba_count += count
            aba_examples[(r1, r2, r3)] += count
    print(f"  ABA trigrams: {aba_count}/{aba_total} ({100*aba_count/aba_total:.2f}%)")

    # Expected ABA under random
    # P(ABA) = sum_i p_i^2 * (1 - p_i) roughly
    expected_aba = sum((c/total_tokens)**2 * (1 - c/total_tokens) for c in root_counts.values())
    print(f"  Expected ABA under random: {100*expected_aba:.2f}%")
    aba_ratio = (aba_count/aba_total) / expected_aba if expected_aba > 0 else 0
    print(f"  Ratio: {aba_ratio:.2f}x")

    print(f"\n  TOP ABA EXAMPLES:")
    for (r1, r2, r3), count in aba_examples.most_common(15):
        print(f"  {r1}-{r2}-{r1}: {count}")

    # Derivational prefix chains
    print(f"\n  DERIVATIONAL PREFIX CHAINS (what follows what):")
    print(f"  {'Deriv1':6s} {'Deriv2':6s} {'Count':>5s} {'%':>6s}")
    deriv_total = sum(deriv_chains.values())
    for (d1, d2), count in deriv_chains.most_common(20):
        d1_show = d1 if d1 else '∅'
        d2_show = d2 if d2 else '∅'
        print(f"  {d1_show:6s} {d2_show:6s} {count:5d} {100*count/deriv_total:5.1f}%")

    # Test: do ch-words tend to follow each other (compound construct)?
    ch_follows_ch = 0
    ch_total = 0
    for (r1, r2), count in root_bigrams.items():
        if r1.startswith('ch'):
            ch_total += count
            if r2.startswith('ch'):
                ch_follows_ch += count

    ch_base_rate = sum(c for r, c in root_counts.items() if r.startswith('ch')) / total_tokens
    ch_follow_pct = ch_follows_ch / ch_total if ch_total > 0 else 0
    print(f"\n  ch-root follows ch-root: {100*ch_follow_pct:.1f}% (base rate: {100*ch_base_rate:.1f}%)")
    if ch_follow_pct > ch_base_rate * 1.5:
        print(f"  → ch-words chain together {ch_follow_pct/ch_base_rate:.1f}x above baseline!")
    else:
        print(f"  → ch-chaining is near baseline. No construct chain detected.")

    return {'self_repeat_ratio': ratio, 'aba_ratio': aba_ratio}


# ══════════════════════════════════════════════════════════════════
# 30e: FULL CORPUS RE-PARSE UNDER REVISED MODEL
# ══════════════════════════════════════════════════════════════════

def run_full_reparse(tokens):
    print()
    print("=" * 76)
    print("PHASE 30e: FULL CORPUS RE-PARSE — 5-SLOT MODEL")
    print("=" * 76)
    print()

    # Known stems that we're confident about
    known_stems = {
        'e','o','ed','eo','od','ol','al','am','ar','or','es',
        'eod','eos','os','a','d','l','r','s'
    }

    total = 0
    clean_parse = 0  # stem is in known_stems
    deriv_parse = 0  # has deriv prefix + known stem
    bare_root = 0    # stem not known, no deriv prefix
    unknown_deriv = 0  # has deriv prefix but unknown stem

    stem_counts = Counter()
    unknown_stems = Counter()
    slot_combos = Counter()

    for word, section, folio in tokens:
        total += 1
        d = revised_decompose(word)

        stem = d['stem']
        deriv = d['deriv_prefix']
        stem_counts[stem] += 1

        # Classify parse quality
        if stem in known_stems:
            clean_parse += 1
            if deriv:
                deriv_parse += 1
        else:
            unknown_stems[stem] += 1
            if deriv:
                unknown_deriv += 1
            else:
                bare_root += 1

        # Track slot combinations
        combo = (
            'G' if d['gram_prefix'] else '_',
            'D' if d['det'] else '_',
            'V' if d['deriv_prefix'] else '_',
            'S',  # stem always present
            'X' if d['suffix'] else '_'
        )
        slot_combos[combo] += 1

    print(f"  Total tokens: {total}")
    print(f"  Clean parse (known stem): {clean_parse} ({100*clean_parse/total:.1f}%)")
    print(f"    Of which with deriv prefix: {deriv_parse} ({100*deriv_parse/total:.1f}%)")
    print(f"  Unknown stem, no deriv: {bare_root} ({100*bare_root/total:.1f}%)")
    print(f"  Unknown stem, has deriv: {unknown_deriv} ({100*unknown_deriv/total:.1f}%)")

    print(f"\n  TOP 20 UNKNOWN STEMS (not in core set):")
    print(f"  {'Stem':12s} {'N':>5s}")
    for stem, count in unknown_stems.most_common(20):
        print(f"  {stem:12s} {count:5d}")

    # Are unknown stems just compound-concatenations of known stems?
    decomposable_unknowns = 0
    total_unknown_tokens = 0
    for stem, count in unknown_stems.items():
        total_unknown_tokens += count
        for i in range(1, len(stem)):
            p1, p2 = stem[:i], stem[i:]
            if p1 in known_stems and p2 in known_stems:
                decomposable_unknowns += count
                break

    if total_unknown_tokens > 0:
        print(f"\n  Unknown stems that decompose into known stem pairs:")
        print(f"    {decomposable_unknowns}/{total_unknown_tokens} tokens "
              f"({100*decomposable_unknowns/total_unknown_tokens:.1f}%)")

    print(f"\n  SLOT COMBINATION FREQUENCY (top 15):")
    print(f"  {'Pattern':10s} {'Count':>6s} {'%':>6s}  Description")
    for combo, count in slot_combos.most_common(15):
        pct = 100*count/total
        desc_parts = []
        if combo[0] == 'G': desc_parts.append('gram-pfx')
        if combo[1] == 'D': desc_parts.append('det')
        if combo[2] == 'V': desc_parts.append('deriv')
        desc_parts.append('STEM')
        if combo[4] == 'X': desc_parts.append('suffix')
        desc = '+'.join(desc_parts)
        print(f"  {''.join(combo):10s} {count:6d} {pct:5.1f}%  {desc}")

    return {'clean_parse_pct': 100*clean_parse/total,
            'unknown_decomposable_pct': 100*decomposable_unknowns/total_unknown_tokens if total_unknown_tokens > 0 else 0}


# ══════════════════════════════════════════════════════════════════
# 30f: PARADIGM TABLE — STEM × DERIVATIONAL PREFIX
# ══════════════════════════════════════════════════════════════════

def run_paradigm_tables(tokens):
    print()
    print("=" * 76)
    print("PHASE 30f: PARADIGM TABLES — STEM × DERIVATIONAL PREFIX")
    print("=" * 76)
    print()
    print("If ch-, h-, sh-, l- are real derivational prefixes, each stem")
    print("should occur with multiple prefixes, forming a regular paradigm.")
    print()

    known_stems = {
        'e','o','ed','eo','od','ol','al','am','ar','or','es',
        'eod','eos','os','a','d','l','r','s'
    }

    # Count: for each (deriv_prefix, stem) pair
    paradigm = defaultdict(Counter)  # paradigm[stem][deriv] = count
    root_counts = Counter()

    for word, section, folio in tokens:
        d = revised_decompose(word)
        if d['stem'] in known_stems:
            paradigm[d['stem']][d['deriv_prefix'] or '∅'] += 1
        root_counts[d['old_root']] += 1

    # Display paradigm table
    derivs = ['∅', 'h', 'ch', 'sh', 'l', 'lch', 'lsh']
    stems = sorted(known_stems, key=lambda s: -sum(paradigm[s].values()))

    print(f"  {'STEM':6s}", end="")
    for dv in derivs:
        print(f" {dv:>6s}", end="")
    print(f" {'TOTAL':>7s}  {'Filldness':>8s}")

    for stem in stems:
        row = paradigm[stem]
        vals = [row.get(dv, 0) for dv in derivs]
        total = sum(vals)
        if total < 10: continue
        filled = sum(1 for v in vals if v > 0)
        filledness = filled / len(derivs)
        print(f"  {stem:6s}", end="")
        for v in vals:
            if v > 0:
                print(f" {v:6d}", end="")
            else:
                print(f" {'—':>6s}", end="")
        print(f" {total:7d}  {100*filledness:.0f}%")

    # How "paradigmatic" is this? In a real morphological system, stems
    # should fill multiple slots. Count average slots filled per stem.
    fill_rates = []
    for stem in stems:
        vals = [paradigm[stem].get(dv, 0) for dv in derivs]
        total = sum(vals)
        if total >= 10:
            filled = sum(1 for v in vals if v > 0)
            fill_rates.append(filled)

    avg_fill = sum(fill_rates) / len(fill_rates) if fill_rates else 0
    max_fill = max(fill_rates) if fill_rates else 0
    print(f"\n  Average slots filled per stem: {avg_fill:.1f}/{len(derivs)}")
    print(f"  Max: {max_fill}/{len(derivs)}")

    # Compare: in a random assignment, how many slots would be filled?
    # This is basically: given N tokens distributed across 7 bins,
    # expected filled bins = 7 * (1 - (1 - 1/7)^N)
    for stem in stems[:5]:
        total = sum(paradigm[stem].values())
        if total < 10: continue
        expected_filled = len(derivs) * (1 - (1 - 1/len(derivs))**total)
        actual_filled = sum(1 for dv in derivs if paradigm[stem].get(dv, 0) > 0)
        print(f"  {stem}: actual={actual_filled}, expected-if-random={expected_filled:.1f}")

    # KEY TEST: Do the derivational prefixes change the section distribution?
    # If ch-e and h-e have different section profiles, derivation is real.
    print(f"\n  DERIVATION CHANGES SECTION DISTRIBUTION?")
    sections_list = ['bio','cosmo','herbal-A','herbal-B','pharma','text','zodiac','unknown']

    for stem in ['e', 'o', 'ol', 'ed', 'eo']:
        print(f"\n  Stem '{stem}':")
        for dv in ['∅', 'h', 'ch', 'sh', 'l']:
            if dv == '∅':
                root_key = stem
            else:
                root_key = dv + stem
            n = root_counts.get(root_key, 0)
            if n < 15: continue
            # Mini-distribution
            sec_dist = defaultdict(int)
            for word, section, folio in tokens:
                d = full_decompose(word)
                if d['root'] == root_key:
                    sec_dist[section] += 1
            top_sec = max(sec_dist, key=sec_dist.get) if sec_dist else '?'
            top_pct = 100*sec_dist[top_sec]/n if n > 0 else 0
            s_pct = 100*(Counter(d2['prefix'] for w2, s2, f2 in tokens
                                 if (d2 := full_decompose(w2))['root'] == root_key).get('s', 0)
                         + Counter(d2['prefix'] for w2, s2, f2 in tokens
                                   if (d2 := full_decompose(w2))['root'] == root_key).get('so', 0)) / n if n > 0 else 0
            print(f"    {dv:3s}+{stem:4s} (N={n:5d}): peak={top_sec:10s}({top_pct:.0f}%)")

    return {'avg_fill': avg_fill}


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("PHASE 30: SKEPTICAL RE-VALIDATION & REVISED MODEL TEST")
    print("=" * 76)

    tokens = load_all_tokens()
    print(f"Loaded {len(tokens)} word tokens\n")

    r30a = run_null_model_test(tokens)
    r30b = run_distribution_blend_test(tokens)
    r30c = run_h_prefix_permutation(tokens)
    r30d = run_construct_chain_test(tokens)
    r30e = run_full_reparse(tokens)
    r30f = run_paradigm_tables(tokens)

    # Final summary
    print()
    print("=" * 76)
    print("PHASE 30: VALIDATION VERDICTS")
    print("=" * 76)
    print()
    print(f"  30a Compound null model: z={r30a['z_score']:.2f} "
          f"(actual {r30a['actual_pct']:.1f}% vs random {r30a['random_pct']:.1f}%)")
    print(f"  30b Distribution blend: real={r30b['avg_real']:.3f} vs null={r30b['avg_null']:.3f}")
    print(f"  30c h-prefix permutation: p={r30c['p_value']:.4f}")
    print(f"  30d Construct chains: self-repeat {r30d['self_repeat_ratio']:.2f}x, "
          f"ABA {r30d['aba_ratio']:.2f}x")
    print(f"  30e Revised model coverage: {r30e['clean_parse_pct']:.1f}% clean parse")
    print(f"  30f Paradigm fill: avg {r30f['avg_fill']:.1f}/7 slots")

    results = {
        'null_model': r30a,
        'blend_test': r30b,
        'h_permutation': r30c,
        'construct_chains': r30d,
        'reparse': r30e,
        'paradigm': r30f,
    }
    json.dump(results, open(Path("results/phase30_results.json"), 'w'), indent=2, default=str)
    print(f"\n  Results saved to results/phase30_results.json")


if __name__ == '__main__':
    import contextlib
    outpath = Path("results/phase30_output.txt")
    with open(outpath, 'w', encoding='utf-8') as f:
        with contextlib.redirect_stdout(f):
            main()
    print(open(outpath, encoding='utf-8').read())
