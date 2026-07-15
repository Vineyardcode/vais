#!/usr/bin/env python3
"""
Phase 31 — The Derivational Prefix Paradox
============================================

Phase 30 established:
  - Paradigm tables are stunningly regular (6.2/7 avg fill)
  - BUT derivational prefixes DON'T change section distribution
  - So what DO ch-, h-, sh-, l- actually change?

This phase tests EVERY other axis of variation:

  31a) SUFFIX SELECTION — Do different deriv prefixes prefer different suffixes?
       (If ch+e prefers -dy and h+e prefers -in, that's inflectional marking)

  31b) LINE POSITION — Do deriv forms prefer line-initial, medial, or final?
       (If h-forms cluster at verbs-first position, that's syntactic)

  31c) GALLOWS CO-OCCURRENCE — Does deriv prefix interact with determinative?
       (If ch+k+e ≠ ch+t+e in frequency, the prefix-det pairing matters)

  31d) BARE PREFIX INVESTIGATION — ch(4068), h(2042), sh(394) appearing
       alone. What are they? Test: position, section, suffix patterns.

  31e) EXPANDED STEM SET — Test air, an, om, oo, i, ai as additional stems.
       Do they fill paradigm slots like the core 19?

  31f) INFLECTION vs DERIVATION TEST — If this is inflection, forms of the
       same stem should occur on the SAME LINE (different cases of same word).
       If derivation, they should occur on DIFFERENT lines (different words).
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

DERIV_PREFIXES_ORDER = ['lch','lsh','ch','sh','l','h']




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
# 31a: SUFFIX SELECTION — DO DERIV PREFIXES CHANGE SUFFIX CHOICE?
# ══════════════════════════════════════════════════════════════════

def run_suffix_selection(tokens):
    print("=" * 76)
    print("PHASE 31a: SUFFIX SELECTION BY DERIVATIONAL PREFIX")
    print("=" * 76)
    print()
    print("If ch+e and h+e are grammatically different (noun vs verb),")
    print("they should prefer different suffixes.")
    print()

    # For each (deriv_prefix, stem), count suffix distribution
    deriv_suffix = defaultdict(Counter)  # deriv_suffix[(deriv, stem)][suffix] = count
    deriv_counts = defaultdict(int)

    for word, section, folio in tokens:
        d = revised_decompose(word)
        if d['stem'] in CORE_STEMS:
            key = (d['deriv_prefix'] or '∅', d['stem'])
            sfx = d['suffix'] or '∅'
            deriv_suffix[key][sfx] += 1
            deriv_counts[key] += 1

    # For top stems, compare suffix distributions across deriv prefixes
    derivs = ['∅', 'h', 'ch', 'sh', 'l']
    top_stems = ['e', 'o', 'ol', 'ed', 'eo', 'al', 'ar', 'd', 'or', 'es', 'od', 'am']

    for stem in top_stems:
        total_for_stem = sum(deriv_counts.get((dv, stem), 0) for dv in derivs)
        if total_for_stem < 50:
            continue

        print(f"  ═══ STEM '{stem}' ═══")
        # Collect all suffixes that appear
        all_sfxs = set()
        for dv in derivs:
            all_sfxs.update(deriv_suffix.get((dv, stem), {}).keys())
        all_sfxs = sorted(all_sfxs, key=lambda s: -sum(deriv_suffix.get((dv, stem), {}).get(s, 0) for dv in derivs))
        top_sfxs = all_sfxs[:8]

        # Header
        hdr = f"  {'deriv':6s} {'N':>5s}"
        for sf in top_sfxs:
            hdr += f" {sf:>6s}"
        print(hdr)

        rows = {}
        for dv in derivs:
            key = (dv, stem)
            n = deriv_counts.get(key, 0)
            if n < 5: continue
            row = f"  {dv:6s} {n:5d}"
            pcts = []
            for sf in top_sfxs:
                c = deriv_suffix[key].get(sf, 0)
                pct = 100 * c / n if n > 0 else 0
                row += f" {pct:5.0f}%"
                pcts.append(pct)
            print(row)
            rows[dv] = pcts

        # Are h-forms different from ∅-forms in suffix choice?
        if '∅' in rows and 'h' in rows:
            # Jensen-Shannon-like difference: sum of |p1-p2|
            diff = sum(abs(a - b) for a, b in zip(rows['∅'], rows['h']))
            print(f"    |∅ vs h| suffix diff: {diff:.0f} pct-points")
        if '∅' in rows and 'ch' in rows:
            diff = sum(abs(a - b) for a, b in zip(rows['∅'], rows['ch']))
            print(f"    |∅ vs ch| suffix diff: {diff:.0f} pct-points")
        print()

    return {}


# ══════════════════════════════════════════════════════════════════
# 31b: LINE POSITION — WHERE DO DERIV FORMS APPEAR?
# ══════════════════════════════════════════════════════════════════

def run_line_position(tokens):
    print()
    print("=" * 76)
    print("PHASE 31b: LINE POSITION BY DERIVATIONAL PREFIX")
    print("=" * 76)
    print()
    print("If h-forms are verbs, they should cluster at specific line positions")
    print("(e.g., verb-second in SOV, or verb-first in VSO).")
    print()

    folio_lines = load_folio_lines()

    # For each word in a line, record its relative position
    deriv_positions = defaultdict(list)  # deriv_positions[deriv] = [relative_pos_0_to_1, ...]

    for lid, section, words in folio_lines:
        if len(words) < 3: continue  # Need at least 3 words for meaningful position
        decomposed = [revised_decompose(w) for w in words]
        for i, d in enumerate(decomposed):
            if d['stem'] not in CORE_STEMS:
                continue
            rel_pos = i / (len(words) - 1) if len(words) > 1 else 0.5
            deriv = d['deriv_prefix'] or '∅'
            deriv_positions[deriv].append(rel_pos)

    # Report position distributions
    print(f"  {'Deriv':6s} {'N':>6s}  {'Mean':>6s} {'StdDev':>6s}  {'Init<.2':>7s} {'Mid.2-.8':>8s} {'Final>.8':>8s}")

    for deriv in ['∅', 'h', 'ch', 'sh', 'l', 'lch', 'lsh']:
        positions = deriv_positions.get(deriv, [])
        if len(positions) < 20:
            continue
        n = len(positions)
        mean = sum(positions) / n
        variance = sum((p - mean)**2 for p in positions) / n
        sd = variance ** 0.5

        initial = sum(1 for p in positions if p < 0.2) / n
        medial = sum(1 for p in positions if 0.2 <= p <= 0.8) / n
        final = sum(1 for p in positions if p > 0.8) / n

        print(f"  {deriv:6s} {n:6d}  {mean:6.3f} {sd:6.3f}  {100*initial:6.1f}% {100*medial:7.1f}% {100*final:7.1f}%")

    # Specific test: is h- more initial than ∅?
    h_pos = deriv_positions.get('h', [])
    bare_pos = deriv_positions.get('∅', [])
    if h_pos and bare_pos:
        h_mean = sum(h_pos) / len(h_pos)
        bare_mean = sum(bare_pos) / len(bare_pos)
        # Approximate t-test
        h_var = sum((p - h_mean)**2 for p in h_pos) / len(h_pos)
        bare_var = sum((p - bare_mean)**2 for p in bare_pos) / len(bare_pos)
        se = (h_var/len(h_pos) + bare_var/len(bare_pos))**0.5
        t_stat = (h_mean - bare_mean) / se if se > 0 else 0
        print(f"\n  h- vs bare mean position: {h_mean:.3f} vs {bare_mean:.3f}, t={t_stat:.2f}")
        if abs(t_stat) > 2:
            direction = "MORE INITIAL" if h_mean < bare_mean else "MORE FINAL"
            print(f"  → h- forms are significantly {direction} than bare forms.")
        else:
            print(f"  → No significant position difference between h- and bare.")

    # Same for ch-
    ch_pos = deriv_positions.get('ch', [])
    if ch_pos and bare_pos:
        ch_mean = sum(ch_pos) / len(ch_pos)
        ch_var = sum((p - ch_mean)**2 for p in ch_pos) / len(ch_pos)
        se = (ch_var/len(ch_pos) + bare_var/len(bare_pos))**0.5
        t_stat = (ch_mean - bare_mean) / se if se > 0 else 0
        print(f"  ch- vs bare mean position: {ch_mean:.3f} vs {bare_mean:.3f}, t={t_stat:.2f}")
        if abs(t_stat) > 2:
            direction = "MORE INITIAL" if ch_mean < bare_mean else "MORE FINAL"
            print(f"  → ch- forms are significantly {direction} than bare forms.")
        else:
            print(f"  → No significant position difference between ch- and bare.")

    return {}


# ══════════════════════════════════════════════════════════════════
# 31c: GALLOWS × DERIV PREFIX INTERACTION
# ══════════════════════════════════════════════════════════════════

def run_gallows_deriv_interaction(tokens):
    print()
    print("=" * 76)
    print("PHASE 31c: GALLOWS DETERMINATIVE × DERIV PREFIX INTERACTION")
    print("=" * 76)
    print()

    # Count (det, deriv) combinations
    det_deriv = Counter()
    det_counts = Counter()
    deriv_counts_all = Counter()

    for word, section, folio in tokens:
        d = revised_decompose(word)
        if d['stem'] not in CORE_STEMS:
            continue
        det = d['det'] or '∅'
        deriv = d['deriv_prefix'] or '∅'
        det_deriv[(det, deriv)] += 1
        det_counts[det] += 1
        deriv_counts_all[deriv] += 1

    total = sum(det_deriv.values())
    dets = ['∅', 'k', 't', 'f', 'p']
    derivs = ['∅', 'h', 'ch', 'sh', 'l']

    # Contingency table
    print(f"  {'':8s}", end="")
    for dv in derivs:
        print(f" {dv:>7s}", end="")
    print(f" {'Total':>7s}")

    for det in dets:
        row_total = det_counts.get(det, 0)
        print(f"  {det:8s}", end="")
        for dv in derivs:
            c = det_deriv.get((det, dv), 0)
            print(f" {c:7d}", end="")
        print(f" {row_total:7d}")

    # Expected vs observed for each cell
    print(f"\n  OBSERVED / EXPECTED RATIOS (>1.5 or <0.5 = interesting):")
    print(f"  {'':8s}", end="")
    for dv in derivs:
        print(f" {dv:>7s}", end="")
    print()

    interesting = []
    for det in dets:
        print(f"  {det:8s}", end="")
        for dv in derivs:
            observed = det_deriv.get((det, dv), 0)
            expected = det_counts.get(det, 0) * deriv_counts_all.get(dv, 0) / total if total > 0 else 0
            ratio = observed / expected if expected > 0 else 0
            marker = "*" if (ratio > 1.5 or ratio < 0.5) and observed > 10 else " "
            print(f" {ratio:6.2f}{marker}", end="")
            if marker == "*":
                interesting.append((det, dv, observed, expected, ratio))
        print()

    if interesting:
        print(f"\n  SIGNIFICANT DET×DERIV INTERACTIONS:")
        for det, dv, obs, exp, ratio in interesting:
            direction = "ATTRACTS" if ratio > 1 else "REPELS"
            print(f"    det={det} × deriv={dv}: {ratio:.2f}x ({obs}/{exp:.0f}) — {direction}")

    return {}


# ══════════════════════════════════════════════════════════════════
# 31d: BARE PREFIX INVESTIGATION
# ══════════════════════════════════════════════════════════════════

def run_bare_prefix_investigation(tokens):
    print()
    print("=" * 76)
    print("PHASE 31d: BARE PREFIX WORDS (ch, h, sh as stems)")  
    print("=" * 76)
    print()
    print("ch(4068), h(2042), sh(394) appear as standalone stems — no further")
    print("material after the deriv prefix. Are these function words or errors?")
    print()

    folio_lines = load_folio_lines()

    bare_prefixes = ['ch', 'h', 'sh', 'l']

    for bp in bare_prefixes:
        # Gather stats: gram_prefix, det, suffix, position
        gram_dist = Counter()
        det_dist = Counter()
        sfx_dist = Counter()
        section_dist = Counter()
        positions = []
        total = 0

        for lid, section, words in folio_lines:
            decomposed = [revised_decompose(w) for w in words]
            for i, d in enumerate(decomposed):
                if d['old_root'] == bp:
                    total += 1
                    gram_dist[d['gram_prefix'] or '∅'] += 1
                    det_dist[d['det'] or '∅'] += 1
                    sfx_dist[d['suffix'] or '∅'] += 1
                    section_dist[section] += 1
                    if len(words) > 1:
                        positions.append(i / (len(words) - 1))

        if total < 20:
            continue

        print(f"  === '{bp}' as standalone root (N={total}) ===")
        print(f"    Gram-prefix: {dict(gram_dist.most_common(5))}")
        print(f"    Determinative: {dict(det_dist.most_common(5))}")
        print(f"    Suffix: {dict(sfx_dist.most_common(5))}")
        
        # Section enrichment
        total_corpus = sum(section_dist.values())
        top_sec = section_dist.most_common(1)[0] if section_dist else ('?', 0)
        print(f"    Top section: {top_sec[0]} ({100*top_sec[1]/total:.0f}%)")

        # Position
        if positions:
            mean_pos = sum(positions) / len(positions)
            init_pct = 100 * sum(1 for p in positions if p < 0.2) / len(positions)
            final_pct = 100 * sum(1 for p in positions if p > 0.8) / len(positions)
            print(f"    Mean position: {mean_pos:.3f} (initial: {init_pct:.0f}%, final: {final_pct:.0f}%)")

        # Compare: bare 'ch' vs 'ch+e' (ch with a stem) — are they in different positions?
        if bp == 'ch':
            ch_with_stem_pos = []
            for lid, section, words in folio_lines:
                decomposed = [revised_decompose(w) for w in words]
                for i, d in enumerate(decomposed):
                    if d['deriv_prefix'] == 'ch' and d['stem'] in CORE_STEMS:
                        if len(words) > 1:
                            ch_with_stem_pos.append(i / (len(words) - 1))
            if ch_with_stem_pos and positions:
                bare_mean = sum(positions) / len(positions)
                stem_mean = sum(ch_with_stem_pos) / len(ch_with_stem_pos)
                print(f"    Bare 'ch' position: {bare_mean:.3f} vs ch+STEM: {stem_mean:.3f}")
                if abs(bare_mean - stem_mean) > 0.03:
                    print(f"    → Different positions suggest different grammatical roles")
                else:
                    print(f"    → Same positions — bare ch may just be ch+∅ (null stem)")
        print()

    return {}


# ══════════════════════════════════════════════════════════════════
# 31e: EXPANDED STEM SET TEST
# ══════════════════════════════════════════════════════════════════

def run_expanded_stems(tokens):
    print()
    print("=" * 76)
    print("PHASE 31e: EXPANDED STEM SET TEST")
    print("=" * 76)
    print()
    print("Test candidate stems: air, an, om, oo, i, ai, ir.")
    print("Do they fill paradigm slots like the core 19?")
    print()

    candidates = ['air', 'an', 'om', 'oo', 'i', 'ai', 'ir', 'ald', 'iir']

    root_counts = Counter()
    for word, section, folio in tokens:
        d = full_decompose(word)
        root_counts[d['root']] += 1

    derivs = ['∅', 'h', 'ch', 'sh', 'l', 'lch', 'lsh']

    print(f"  {'Candidate':10s}", end="")
    for dv in derivs:
        print(f" {dv:>6s}", end="")
    print(f" {'TOTAL':>7s} {'Fill':>5s}")

    for cand in candidates:
        vals = []
        for dv in derivs:
            if dv == '∅':
                root_key = cand
            else:
                root_key = dv + cand
            vals.append(root_counts.get(root_key, 0))
        total = sum(vals)
        if total < 5: continue
        filled = sum(1 for v in vals if v > 0)

        print(f"  {cand:10s}", end="")
        for v in vals:
            if v > 0:
                print(f" {v:6d}", end="")
            else:
                print(f" {'—':>6s}", end="")
        print(f" {total:7d} {filled}/{len(derivs)}")

    # Also test: which stems have the MOST regular paradigms?
    print(f"\n  ALL STEMS ranked by paradigm regularity:")
    all_stems = set()
    for word, section, folio in tokens:
        d = revised_decompose(word)
        if len(d['stem']) >= 1:
            all_stems.add(d['stem'])

    stem_paradigms = []
    for stem in all_stems:
        vals = []
        for dv in derivs:
            if dv == '∅':
                root_key = stem
            else:
                root_key = dv + stem
            vals.append(root_counts.get(root_key, 0))
        total = sum(vals)
        if total < 20: continue
        filled = sum(1 for v in vals if v > 0)
        stem_paradigms.append((stem, total, filled, vals))

    stem_paradigms.sort(key=lambda x: (-x[2], -x[1]))

    print(f"  {'Stem':10s}", end="")
    for dv in derivs:
        print(f" {dv:>6s}", end="")
    print(f" {'TOTAL':>7s} {'Fill':>5s}")

    for stem, total, filled, vals in stem_paradigms[:25]:
        print(f"  {stem:10s}", end="")
        for v in vals:
            if v > 0:
                print(f" {v:6d}", end="")
            else:
                print(f" {'—':>6s}", end="")
        print(f" {total:7d} {filled}/{len(derivs)}")

    return {}


# ══════════════════════════════════════════════════════════════════
# 31f: INFLECTION vs DERIVATION — SAME-LINE CO-OCCURRENCE
# ══════════════════════════════════════════════════════════════════

def run_inflection_test(tokens):
    print()
    print("=" * 76)
    print("PHASE 31f: INFLECTION vs DERIVATION — SAME-LINE TEST")
    print("=" * 76)
    print()
    print("INFLECTION: Different forms of the same stem appear on the SAME line")
    print("  (like 'he sees the man and the man sees him')")
    print("DERIVATION: Different forms appear on DIFFERENT lines")
    print("  (like 'teacher' and 'teach' don't co-occur)")
    print()

    folio_lines = load_folio_lines()

    # For each line, collect which (deriv, stem) pairs appear
    same_line_pairs = Counter()  # (deriv1+stem, deriv2+stem) on same line
    total_lines_checked = 0

    for lid, section, words in folio_lines:
        decomposed = [revised_decompose(w) for w in words]
        # Get unique (deriv, stem) pairs on this line
        forms_on_line = set()
        for d in decomposed:
            if d['stem'] in CORE_STEMS:
                form = (d['deriv_prefix'] or '∅', d['stem'])
                forms_on_line.add(form)

        if len(forms_on_line) < 2:
            continue
        total_lines_checked += 1

        # Count co-occurrences of different deriv forms of SAME stem
        forms_list = sorted(forms_on_line)
        for i in range(len(forms_list)):
            for j in range(i+1, len(forms_list)):
                (d1, s1), (d2, s2) = forms_list[i], forms_list[j]
                if s1 == s2 and d1 != d2:
                    # Different deriv forms of same stem on same line!
                    same_line_pairs[(d1+'+'+s1, d2+'+'+s2)] += 1

    print(f"  Lines with 2+ core-stem forms: {total_lines_checked}")
    print(f"  Same-stem different-deriv co-occurrences: {sum(same_line_pairs.values())}")

    if same_line_pairs:
        print(f"\n  TOP SAME-LINE PAIRS (same stem, different derivation):")
        for (f1, f2), count in same_line_pairs.most_common(25):
            print(f"    {f1:10s} + {f2:10s}: {count} lines")

    # Compare: how often do DIFFERENT stems co-occur on same line?
    diff_stem_cooccur = 0
    for lid, section, words in folio_lines:
        decomposed = [revised_decompose(w) for w in words]
        stems_on_line = set()
        for d in decomposed:
            if d['stem'] in CORE_STEMS:
                stems_on_line.add(d['stem'])
        if len(stems_on_line) >= 2:
            diff_stem_cooccur += 1

    print(f"\n  Lines with 2+ DIFFERENT core stems: {diff_stem_cooccur}")
    print(f"  Lines with same-stem different-deriv: "
          f"{sum(1 for lid, sec, words in folio_lines if _has_deriv_pair(words))}")

    # Ratio
    if total_lines_checked > 0:
        pct_with_deriv_variation = 100 * sum(same_line_pairs.values()) / total_lines_checked
        print(f"\n  {pct_with_deriv_variation:.1f}% of multi-form lines have same-stem deriv variation")
        if pct_with_deriv_variation > 30:
            print(f"  → HIGH co-occurrence. Looks like INFLECTION (case/number marking).")
        elif pct_with_deriv_variation > 10:
            print(f"  → MODERATE co-occurrence. Could be inflection or free derivation.")
        else:
            print(f"  → LOW co-occurrence. More consistent with DERIVATION (different lexemes).")

    return {}


def _has_deriv_pair(words):
    """Helper: does this word list contain two different deriv forms of the same stem?"""
    forms = set()
    for w in words:
        d = revised_decompose(w)
        if d['stem'] in CORE_STEMS:
            forms.add((d['deriv_prefix'] or '∅', d['stem']))
    stems_with_deriv = defaultdict(set)
    for deriv, stem in forms:
        stems_with_deriv[stem].add(deriv)
    return any(len(dset) >= 2 for dset in stems_with_deriv.values())


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("PHASE 31: THE DERIVATIONAL PREFIX PARADOX")
    print("=" * 76)

    tokens = load_all_tokens()
    print(f"Loaded {len(tokens)} word tokens\n")

    run_suffix_selection(tokens)
    run_line_position(tokens)
    run_gallows_deriv_interaction(tokens)
    run_bare_prefix_investigation(tokens)
    run_expanded_stems(tokens)
    run_inflection_test(tokens)

    print()
    print("=" * 76)
    print("PHASE 31: SYNTHESIS")
    print("=" * 76)
    print()
    print("  If deriv prefixes change SUFFIX SELECTION → grammatical categories")
    print("  If deriv prefixes change LINE POSITION → syntactic roles")
    print("  If deriv prefixes change GALLOWS CHOICE → semantic classification")
    print("  If deriv forms CO-OCCUR on same line → inflectional paradigm")
    print("  If deriv forms DON'T co-occur → derivational (different words)")

    json.dump({'status': 'complete'}, open(Path("results/phase31_results.json"), 'w'), indent=2)
    print(f"\n  Results saved to results/phase31_results.json")


if __name__ == '__main__':
    import contextlib
    outpath = Path("results/phase31_output.txt")
    with open(outpath, 'w', encoding='utf-8') as f:
        with contextlib.redirect_stdout(f):
            main()
    print(open(outpath, encoding='utf-8').read())
