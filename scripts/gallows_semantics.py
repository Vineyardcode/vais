#!/usr/bin/env python3
"""
Voynich Manuscript — Gallows-Stripped Semantic Clustering (Phase 13)

Now that we know gallows are determinatives (Phase 10), strip them from
every word and analyze the REAL vocabulary (~4,795 stripped forms).

Key questions:
  1. Which stripped roots attract which gallows types?
  2. Do the same roots get DIFFERENT gallows in different sections?
  3. Can we identify what each gallows TYPE means (mineral/plant/celestial/process)?
  4. Do gallows-type profiles cluster into interpretable semantic fields?
  5. What is the relationship between gallows tier (simple/bench/compound)
     and the stripped root it modifies?

This is the closest approach to actual decipherment — mapping the
determinative system to semantic categories.
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from common import classify_folio, gallows_base_v2 as gallows_base, strip_gallows

# ── Section classification ────────────────────────────────────────────────


# ── Gallows definitions ──────────────────────────────────────────────────

SIMPLE_GALLOWS = ["t", "k", "f", "p"]
BENCH_GALLOWS = ["cth", "ckh", "cph", "cfh"]
COMPOUND_GCH = ["tch", "kch", "pch", "fch"]
COMPOUND_GSH = ["tsh", "ksh", "psh", "fsh"]
ALL_GALLOWS = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

GALLOWS_REGEX = re.compile(
    r'(cth|ckh|cph|cfh|tch|kch|pch|fch|tsh|ksh|psh|fsh|[tkfp])'
)


# Gallows "tier": simple=1, bench=2, compound=3
def gallows_tier(g):
    if g in SIMPLE_GALLOWS:
        return "simple"
    elif g in BENCH_GALLOWS:
        return "bench"
    elif g in COMPOUND_GCH or g in COMPOUND_GSH:
        return "compound"
    return "unknown"

# ── Data extraction ──────────────────────────────────────────────────────

def extract_all_words():
    folio_dir = Path("folios")
    all_data = []

    for txt_file in sorted(folio_dir.glob("*.txt")):
        section = classify_folio(txt_file)
        folio = txt_file.stem
        lines = txt_file.read_text(encoding="utf-8").splitlines()

        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            m = re.match(r'<([^>]+)>\s*(.*)', line)
            if not m:
                continue
            locus = m.group(1)
            text = m.group(2)

            # Determine locus type
            if "@Cc" in locus:
                locus_type = "ring"
            elif "@Lt" in locus or "@Lb" in locus:
                locus_type = "label"
            elif "@Lz" in locus or "&Lz" in locus:
                locus_type = "nymph"
            else:
                locus_type = "paragraph"

            text = re.sub(r'<![^>]*>', '', text)
            text = re.sub(r'<%>|<\$>|<->|<\.>', ' ', text)
            text = re.sub(r'<[^>]*>', '', text)
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
            text = re.sub(r'\{([^}]+)\}', r'\1', text)
            text = re.sub(r'@\d+;?', '', text)

            tokens = re.split(r'[.\s,<>\-]+', text)
            for tok in tokens:
                tok = tok.strip().replace("'", "")
                if not tok or '?' in tok:
                    continue
                if re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                    all_data.append((tok, section, folio, locus, locus_type))

    return all_data




def extract_gallows_ordered(word):
    """Extract gallows in left-to-right order from a word."""
    found = []
    pos = 0
    while pos < len(word):
        matched = False
        for g in ALL_GALLOWS:  # longest first
            if word[pos:].startswith(g):
                found.append(g)
                pos += len(g)
                matched = True
                break
        if not matched:
            pos += 1
    return found


# ══════════════════════════════════════════════════════════════════════════
# ANALYSES
# ══════════════════════════════════════════════════════════════════════════

def analysis1_root_gallows_profiles(all_data):
    """For each stripped root, build a gallows-type profile: which gallows
    does this root attract, and in what proportions?"""
    print("=" * 72)
    print("ANALYSIS 1: ROOT → GALLOWS TYPE PROFILES")
    print("=" * 72)

    root_gallows = defaultdict(Counter)   # stripped_root → Counter of gallows bases
    root_total = Counter()                # stripped_root → total occurrences (incl. bare)
    root_bare = Counter()                 # stripped_root → occurrences with NO gallows

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        if len(stripped) < 1:
            continue
        root_total[stripped] += 1
        if not gals:
            root_bare[stripped] += 1
        for g in gals:
            root_gallows[stripped][gallows_base(g)] += 1

    # Focus on roots with enough data (>= 20 occurrences)
    freq_roots = [(r, root_total[r]) for r in root_total if root_total[r] >= 20]
    freq_roots.sort(key=lambda x: -x[1])

    print(f"\n  Roots with ≥ 20 occurrences: {len(freq_roots)}")
    print(f"\n  {'Root':<15s}  {'Total':>5s}  {'Bare':>5s}  {'Bare%':>5s}"
          f"  {'t':>5s}  {'k':>5s}  {'f':>3s}  {'p':>4s}  {'Dominant':>8s}  {'Ratio':>6s}")
    print("  " + "-" * 80)

    root_profiles = {}
    for root, total in freq_roots[:80]:
        bare = root_bare.get(root, 0)
        bare_pct = 100 * bare / total
        gp = root_gallows[root]
        t_ct = gp.get('t', 0)
        k_ct = gp.get('k', 0)
        f_ct = gp.get('f', 0)
        p_ct = gp.get('p', 0)
        gallows_total = t_ct + k_ct + f_ct + p_ct

        if gallows_total > 0:
            dominant = max(['t', 'k', 'f', 'p'], key=lambda x: gp.get(x, 0))
            dom_ct = gp[dominant]
            ratio = dom_ct / gallows_total
        else:
            dominant = "-"
            ratio = 0

        root_profiles[root] = {
            "total": total, "bare": bare,
            "t": t_ct, "k": k_ct, "f": f_ct, "p": p_ct,
            "dominant": dominant, "ratio": ratio
        }

        print(f"  {root:<15s}  {total:5d}  {bare:5d}  {bare_pct:4.0f}%"
              f"  {t_ct:5d}  {k_ct:5d}  {f_ct:3d}  {p_ct:4d}"
              f"  {dominant:>8s}  {ratio:5.0%}")

    # Gallows exclusivity: roots that ONLY take one gallows type
    exclusive = []
    for root, total in freq_roots:
        gp = root_gallows[root]
        gallows_types_used = [b for b in ['t', 'k', 'f', 'p'] if gp.get(b, 0) > 0]
        gallows_total = sum(gp.values())
        if len(gallows_types_used) == 1 and gallows_total >= 5:
            exclusive.append((root, gallows_types_used[0], gallows_total, total))

    print(f"\n  Roots exclusive to ONE gallows type (≥ 5 gallows occurrences): {len(exclusive)}")
    exclusive.sort(key=lambda x: -x[2])
    for root, g, gal_ct, total in exclusive[:20]:
        print(f"    {root:<15s}  only '{g}'  ({gal_ct} gallows / {total} total)")

    return root_profiles, root_gallows, root_total, root_bare


def analysis2_section_gallows_shift(all_data, root_gallows, root_total):
    """For high-frequency roots, does the gallows profile change across sections?
    If root X takes k- in herbal but t- in pharma, the gallows marks the DOMAIN."""
    print("\n" + "=" * 72)
    print("ANALYSIS 2: SECTION-DEPENDENT GALLOWS SHIFTS")
    print("=" * 72)

    sections = ["herbal-A", "herbal-B", "pharma", "bio", "cosmo", "text", "zodiac"]

    # Build per-section gallows profiles for each root
    root_section_gallows = defaultdict(lambda: defaultdict(Counter))
    root_section_total = defaultdict(Counter)

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        if len(stripped) < 1:
            continue
        root_section_total[stripped][section] += 1
        for g in gals:
            root_section_gallows[stripped][section][gallows_base(g)] += 1

    # Find roots that show different dominant gallows in different sections
    # Require: root appears in ≥ 3 sections with ≥ 5 gallowed tokens each
    shifting_roots = []

    for root in root_total:
        if root_total[root] < 30:
            continue
        section_dominants = {}
        for section in sections:
            gp = root_section_gallows[root][section]
            total_g = sum(gp.values())
            if total_g < 5:
                continue
            dominant = max(['t', 'k', 'f', 'p'], key=lambda x: gp.get(x, 0))
            section_dominants[section] = (dominant, gp[dominant], total_g)

        if len(section_dominants) >= 2:
            # Check if dominant gallows differs across sections
            dom_set = set(d[0] for d in section_dominants.values())
            if len(dom_set) > 1:
                shifting_roots.append((root, section_dominants))

    shifting_roots.sort(key=lambda x: -root_total[x[0]])

    print(f"\n  Roots with DIFFERENT dominant gallows across sections: {len(shifting_roots)}")
    print(f"\n  Top 30 shifting roots:")
    for root, sec_doms in shifting_roots[:30]:
        print(f"\n    '{root}' (total={root_total[root]}):")
        for section, (dom, dom_ct, total_g) in sorted(sec_doms.items()):
            gp = root_section_gallows[root][section]
            profile = " ".join(f"{b}={gp.get(b,0)}" for b in ['t', 'k', 'f', 'p'])
            print(f"      {section:12s}  dominant={dom}  ({profile})  total_gal={total_g}")

    # Also find roots with STABLE gallows across sections (same dominant everywhere)
    stable_roots = []
    for root in root_total:
        if root_total[root] < 30:
            continue
        section_dominants = {}
        for section in sections:
            gp = root_section_gallows[root][section]
            total_g = sum(gp.values())
            if total_g < 5:
                continue
            dominant = max(['t', 'k', 'f', 'p'], key=lambda x: gp.get(x, 0))
            section_dominants[section] = dominant

        if len(section_dominants) >= 3:
            dom_set = set(section_dominants.values())
            if len(dom_set) == 1:
                stable_roots.append((root, list(dom_set)[0], len(section_dominants)))

    stable_roots.sort(key=lambda x: -root_total[x[0]])
    print(f"\n  Roots with STABLE gallows (same dominant in ≥ 3 sections): {len(stable_roots)}")
    for root, dom, n_sections in stable_roots[:20]:
        print(f"    '{root}'  always '{dom}'  ({n_sections} sections)")

    return shifting_roots, stable_roots


def analysis3_gallows_semantics(all_data, root_gallows, root_total, root_bare):
    """Attempt to assign semantic meaning to each gallows type by examining
    which sections they dominate and what roots they modify."""
    print("\n" + "=" * 72)
    print("ANALYSIS 3: GALLOWS TYPE SEMANTIC PROFILES")
    print("=" * 72)

    sections = ["herbal-A", "herbal-B", "pharma", "bio", "cosmo", "text", "zodiac"]

    # For each gallows base (t, k, f, p), compute:
    # 1. Section distribution (where does this gallows appear most?)
    # 2. Tier distribution (simple vs bench vs compound)
    # 3. Most common host roots

    gallows_section = defaultdict(Counter)  # base → section → count
    gallows_tier_dist = defaultdict(Counter)  # base → tier → count
    gallows_hosts = defaultdict(Counter)  # base → stripped_root → count
    gallows_locus = defaultdict(Counter)  # base → locus_type → count

    for word, section, folio, locus, ltype in all_data:
        gals = extract_gallows_ordered(word)
        stripped, _ = strip_gallows(word)
        for g in gals:
            base = gallows_base(g)
            tier = gallows_tier(g)
            gallows_section[base][section] += 1
            gallows_tier_dist[base][tier] += 1
            if len(stripped) >= 2:
                gallows_hosts[base][stripped] += 1
            gallows_locus[base][ltype] += 1

    for base in ['t', 'k', 'f', 'p']:
        total = sum(gallows_section[base].values())
        print(f"\n  ── GALLOWS '{base}' (total: {total}) ──")

        # Section profile
        print(f"  Section distribution:")
        for section in sections:
            cnt = gallows_section[base].get(section, 0)
            pct = 100 * cnt / total if total else 0
            bar = "█" * int(pct / 2)
            print(f"    {section:12s}  {cnt:5d}  ({pct:4.1f}%)  {bar}")

        # Tier distribution
        print(f"  Tier distribution:")
        for tier in ["simple", "bench", "compound"]:
            cnt = gallows_tier_dist[base].get(tier, 0)
            pct = 100 * cnt / total if total else 0
            print(f"    {tier:12s}  {cnt:5d}  ({pct:4.1f}%)")

        # Locus type
        print(f"  Locus distribution:")
        for lt in ["paragraph", "ring", "label", "nymph"]:
            cnt = gallows_locus[base].get(lt, 0)
            pct = 100 * cnt / total if total else 0
            print(f"    {lt:12s}  {cnt:5d}  ({pct:4.1f}%)")

        # Top host roots
        print(f"  Top 10 host roots (stripped):")
        for root, cnt in gallows_hosts[base].most_common(10):
            pct = 100 * cnt / total if total else 0
            print(f"    {root:<15s}  {cnt:5d}  ({pct:4.1f}%)")

    # Cross-gallows comparison: which roots are shared vs exclusive?
    print(f"\n  ── CROSS-GALLOWS ROOT SHARING ──")
    all_roots_by_gal = {}
    for base in ['t', 'k', 'f', 'p']:
        all_roots_by_gal[base] = set(
            r for r, c in gallows_hosts[base].items() if c >= 3
        )

    for b1 in ['t', 'k', 'f', 'p']:
        for b2 in ['t', 'k', 'f', 'p']:
            if b1 >= b2:
                continue
            shared = all_roots_by_gal[b1] & all_roots_by_gal[b2]
            only_b1 = all_roots_by_gal[b1] - all_roots_by_gal[b2]
            only_b2 = all_roots_by_gal[b2] - all_roots_by_gal[b1]
            print(f"  {b1} ∩ {b2}: {len(shared)} shared, "
                  f"{len(only_b1)} only-{b1}, {len(only_b2)} only-{b2}")

    # Jaccard similarity
    print(f"\n  Jaccard similarity between gallows root sets:")
    for b1 in ['t', 'k', 'f', 'p']:
        for b2 in ['t', 'k', 'f', 'p']:
            if b1 >= b2:
                continue
            s1 = all_roots_by_gal[b1]
            s2 = all_roots_by_gal[b2]
            if s1 | s2:
                jac = len(s1 & s2) / len(s1 | s2)
                print(f"    {b1} ~ {b2}: {jac:.3f}")


def analysis4_bench_vs_simple(all_data):
    """Compare what bench gallows modify vs what simple gallows modify.
    Phase 10 showed bench concentrate in herbal/pharma — do they also
    modify different ROOT types?"""
    print("\n" + "=" * 72)
    print("ANALYSIS 4: BENCH vs SIMPLE GALLOWS — ROOT DIFFERENCES")
    print("=" * 72)

    simple_roots = Counter()
    bench_roots = Counter()

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        if len(stripped) < 2:
            continue
        for g in gals:
            if g in SIMPLE_GALLOWS:
                simple_roots[stripped] += 1
            elif g in BENCH_GALLOWS:
                bench_roots[stripped] += 1

    # Roots that prefer bench over simple (or vice versa)
    all_roots = set(simple_roots.keys()) | set(bench_roots.keys())

    bench_pref = []
    simple_pref = []
    for root in all_roots:
        s = simple_roots.get(root, 0)
        b = bench_roots.get(root, 0)
        total = s + b
        if total < 10:
            continue
        bench_ratio = b / total
        if bench_ratio > 0.4:
            bench_pref.append((root, b, s, total, bench_ratio))
        elif bench_ratio < 0.1:
            simple_pref.append((root, b, s, total, bench_ratio))

    bench_pref.sort(key=lambda x: -x[4])
    simple_pref.sort(key=lambda x: x[4])

    print(f"\n  Roots preferring BENCH gallows (bench > 40% of all gallows):")
    print(f"  {'Root':<15s}  {'Bench':>5s}  {'Simple':>6s}  {'Total':>5s}  {'Bench%':>6s}")
    for root, b, s, total, ratio in bench_pref[:20]:
        print(f"  {root:<15s}  {b:5d}  {s:6d}  {total:5d}  {100*ratio:5.1f}%")

    print(f"\n  Roots preferring SIMPLE gallows (bench < 10% of all gallows):")
    for root, b, s, total, ratio in simple_pref[:20]:
        print(f"  {root:<15s}  {b:5d}  {s:6d}  {total:5d}  {100*ratio:5.1f}%")

    # What's special about bench-preferring roots?
    # Check their section distribution
    print(f"\n  Section distribution of bench-preferring roots vs simple-preferring:")
    bench_root_set = set(r[0] for r in bench_pref)
    simple_root_set = set(r[0] for r in simple_pref)

    sections = ["herbal-A", "herbal-B", "pharma", "bio", "cosmo", "text", "zodiac"]
    bench_sections = Counter()
    simple_sections = Counter()

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        if stripped in bench_root_set:
            bench_sections[section] += 1
        elif stripped in simple_root_set:
            simple_sections[section] += 1

    b_total = sum(bench_sections.values())
    s_total = sum(simple_sections.values())
    print(f"\n  {'Section':12s}  {'Bench-pref':>10s}  {'Simple-pref':>11s}")
    for section in sections:
        b = bench_sections.get(section, 0)
        s = simple_sections.get(section, 0)
        b_pct = f"{100*b/b_total:.1f}%" if b_total else "n/a"
        s_pct = f"{100*s/s_total:.1f}%" if s_total else "n/a"
        print(f"  {section:12s}  {b_pct:>10s}  {s_pct:>11s}")


def analysis5_gallows_combinatorics(all_data):
    """Map the full combinatorial space: for each stripped root, which
    gallows combinations actually occur? This reveals the 'paradigm table'
    of the determinative system."""
    print("\n" + "=" * 72)
    print("ANALYSIS 5: DETERMINATIVE PARADIGM TABLES")
    print("=" * 72)

    # For each stripped root, collect all attested gallows combinations
    root_forms = defaultdict(Counter)  # stripped → original_word → count

    for word, section, folio, locus, ltype in all_data:
        stripped, gals = strip_gallows(word)
        if len(stripped) < 2:
            continue
        root_forms[stripped][word] += 1

    # Focus on roots with rich paradigms (many distinct gallows forms)
    paradigm_size = []
    for root, forms in root_forms.items():
        n_forms = len(forms)
        total = sum(forms.values())
        if total >= 15:
            paradigm_size.append((root, n_forms, total, forms))

    paradigm_size.sort(key=lambda x: -x[1])

    print(f"\n  Roots with richest paradigms (most distinct gallowed forms):")
    print(f"\n  {'Root':<12s}  {'Forms':>5s}  {'Total':>5s}  Attested forms")
    print("  " + "-" * 70)
    for root, n_forms, total, forms in paradigm_size[:25]:
        top_forms = forms.most_common(8)
        form_str = ", ".join(f"{w}({c})" for w, c in top_forms)
        print(f"  {root:<12s}  {n_forms:5d}  {total:5d}  {form_str}")

    # Average paradigm size
    if paradigm_size:
        avg_forms = sum(x[1] for x in paradigm_size) / len(paradigm_size)
        print(f"\n  Average paradigm size (roots with ≥ 15 tokens): {avg_forms:.1f} forms")

    # Check: how many slots in the paradigm are filled?
    # Maximum possible = 4 simple + 4 bench + 4 compound-ch + 4 compound-sh + 1 bare = 17
    # But in practice most roots won't have all combinations
    bases_used = Counter()
    for root, n_forms, total, forms in paradigm_size:
        bases = set()
        for w in forms:
            gals = extract_gallows_ordered(w)
            if not gals:
                bases.add("bare")
            for g in gals:
                bases.add(gallows_base(g))
        bases_used[len(bases)] += 1

    print(f"\n  Number of distinct gallows bases per root (incl. bare):")
    for n, cnt in sorted(bases_used.items()):
        print(f"    {n} bases: {cnt} roots")


def analysis6_semantic_field_hypothesis(all_data, root_gallows, root_total):
    """Test specific hypotheses about gallows meaning based on section content.
    - t = astrological/celestial (if enriched in zodiac/cosmo)?
    - k = botanical/substance (if enriched in herbal)?
    - p = procedural/processing (if enriched in pharma recipes)?
    - f = rare/special category?"""
    print("\n" + "=" * 72)
    print("ANALYSIS 6: SEMANTIC FIELD HYPOTHESIS TEST")
    print("=" * 72)

    sections = ["herbal-A", "herbal-B", "pharma", "bio", "cosmo", "text", "zodiac"]

    # For each gallows base, compute enrichment/depletion per section
    # relative to the overall gallows distribution
    gallows_section_tokens = defaultdict(Counter)
    section_tokens = Counter()

    for word, section, folio, locus, ltype in all_data:
        section_tokens[section] += 1
        gals = extract_gallows_ordered(word)
        for g in gals:
            gallows_section_tokens[gallows_base(g)][section] += 1

    # Total per gallows
    gallows_totals = {b: sum(gallows_section_tokens[b].values()) for b in ['t', 'k', 'f', 'p']}
    corpus_total = sum(section_tokens.values())

    print(f"\n  Enrichment/depletion of each gallows per section (observed/expected ratio):")
    print(f"\n  {'Section':12s}", end="")
    for b in ['t', 'k', 'f', 'p']:
        print(f"  {b:>8s}", end="")
    print()

    for section in sections:
        sec_frac = section_tokens[section] / corpus_total
        print(f"  {section:12s}", end="")
        for b in ['t', 'k', 'f', 'p']:
            observed = gallows_section_tokens[b].get(section, 0)
            expected = gallows_totals[b] * sec_frac
            if expected > 0:
                ratio = observed / expected
                # Highlight strong enrichment/depletion
                marker = ""
                if ratio > 1.3:
                    marker = " ↑"
                elif ratio < 0.7:
                    marker = " ↓"
                print(f"  {ratio:7.2f}×{marker}", end="")
            else:
                print(f"  {'n/a':>8s}", end="")
        print()

    # Strongest signals
    print(f"\n  Strongest enrichment signals (ratio > 1.3):")
    signals = []
    for section in sections:
        sec_frac = section_tokens[section] / corpus_total
        for b in ['t', 'k', 'f', 'p']:
            observed = gallows_section_tokens[b].get(section, 0)
            expected = gallows_totals[b] * sec_frac
            if expected > 10:
                ratio = observed / expected
                signals.append((b, section, ratio, observed, expected))

    signals.sort(key=lambda x: -x[2])
    for b, section, ratio, obs, exp in signals[:10]:
        print(f"    '{b}' in {section:12s}: {ratio:.2f}× enriched ({obs:.0f} observed vs {exp:.0f} expected)")

    signals.sort(key=lambda x: x[2])
    print(f"\n  Strongest depletion signals (ratio < 0.7):")
    for b, section, ratio, obs, exp in signals[:10]:
        print(f"    '{b}' in {section:12s}: {ratio:.2f}× ({obs:.0f} observed vs {exp:.0f} expected)")

    # t/k ratio per section as a signature
    print(f"\n  t/k ratio per section (signature metric):")
    for section in sections:
        t_ct = gallows_section_tokens['t'].get(section, 0)
        k_ct = gallows_section_tokens['k'].get(section, 0)
        if k_ct > 0:
            ratio = t_ct / k_ct
            print(f"    {section:12s}  t={t_ct:5d}  k={k_ct:5d}  t/k={ratio:.2f}")


def analysis7_synthesis(all_data, root_profiles, shifting_roots, stable_roots):
    """Pull it all together."""
    print("\n" + "=" * 72)
    print("SYNTHESIS: GALLOWS AS SEMANTIC DETERMINATIVES")
    print("=" * 72)

    total_words = len(all_data)
    words_with_gallows = sum(1 for w, *_ in all_data
                            if any(g in w for g in ALL_GALLOWS))

    print(f"\n  Corpus: {total_words} tokens")
    print(f"  Words with gallows: {words_with_gallows} ({100*words_with_gallows/total_words:.1f}%)")
    print(f"  Roots with shifting gallows across sections: {len(shifting_roots)}")
    print(f"  Roots with stable gallows across sections: {len(stable_roots)}")

    shift_pct = 100 * len(shifting_roots) / (len(shifting_roots) + len(stable_roots)) if (shifting_roots or stable_roots) else 0
    print(f"  Shift rate: {shift_pct:.0f}% of multi-section roots change dominant gallows")

    print(f"\n  ── Interpretation ──")
    print(f"  If shift rate is HIGH: gallows mark section/domain context")
    print(f"    → Same concept gets different determinative in different context")
    print(f"    → Like Egyptian: same word can get different determinatives")
    print(f"  If shift rate is LOW: gallows mark inherent word property")
    print(f"    → The determinative is part of the word's identity")
    print(f"    → Like Chinese radicals: fixed semantic component")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Extracting corpus for gallows semantic clustering...\n")
    all_data = extract_all_words()
    print(f"Total tokens: {len(all_data)}\n")

    root_profiles, root_gallows, root_total, root_bare = analysis1_root_gallows_profiles(all_data)
    shifting, stable = analysis2_section_gallows_shift(all_data, root_gallows, root_total)
    analysis3_gallows_semantics(all_data, root_gallows, root_total, root_bare)
    analysis4_bench_vs_simple(all_data)
    analysis5_gallows_combinatorics(all_data)
    analysis6_semantic_field_hypothesis(all_data, root_gallows, root_total)
    analysis7_synthesis(all_data, root_profiles, shifting, stable)

    # Save results
    results = {
        "shifting_roots": len(shifting),
        "stable_roots": len(stable),
        "root_profiles": {r: p for r, p in root_profiles.items()},
    }
    with open("gallows_semantics_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to gallows_semantics_results.json")
