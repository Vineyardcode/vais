#!/usr/bin/env python3
"""
Functional Anatomy of the VMS Word
═══════════════════════════════════════════════

word_shape_validation revealed that VMS positional entropy DROPS toward word-final
positions (3.63→2.79), while the verbose cipher does the OPPOSITE.
The ~4 characters {y, n, l, r} dominate finals (~87%).

This test asks: what ROLE do word-final characters play?

Three competing hypotheses:
  A. Terminators — content-free end-of-unit markers
  B. Grammatical morphemes — small inflectional inventory
  C. Content characters — constrained but information-bearing

Each makes different predictions about how much mutual information
each word zone carries with (a) topic, (b) syntactic position, and
(c) neighboring words.

Metrics (all permutation-tested):
  1. H(zone) — raw entropy per zone
  2. MI(zone; folio_section) — topical information
  3. MI(zone; line_position_bin) — syntactic position info
  4. MI(zone; next_word_initial) — forward inter-word grammar
  5. MI(zone; prev_word_final) — backward inter-word grammar
  6. MI(zone; stem) — zone↔stem coupling
  7. Per-character MI with section (top 20 chars)
  8. Per-absolute-position MI curves

Controls:
  - Permutation z-scores (1000 shuffles) for every MI
  - NMI = MI / min(H(X), H(Y)) to normalize for entropy
  - Italian comparison (same decomposition on Dante)

SKEPTICAL NOTES:
  - Section labels are approximate (folio number → section)
  - MI is positively biased in small samples → permutation tests
  - EVA compound glyphs (ch, sh) are handled as single units
"""

import sys
import os
import re
import math
import json
import urllib.request
from pathlib import Path
from collections import Counter, defaultdict

_print = print
import numpy as np
from common import eva_to_glyphs_v2 as eva_to_glyphs, fetch_gutenberg

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    _print(s, end=end)
    sys.stdout.flush()
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

# ═══════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════


def get_section(folio):
    """Approximate section classifier based on folio number."""
    try:
        num = int(re.match(r'f(\d+)', folio).group(1))
    except:
        return 'unknown'
    if num <= 56:   return 'herbal'
    elif num <= 67: return 'astro'
    elif num <= 73: return 'cosmo'
    elif num <= 84: return 'bio'
    elif num <= 86: return 'cosmo2'
    elif num <= 102: return 'pharma'
    else:           return 'text'

def load_vms_structured():
    """
    Load VMS with full provenance: returns list of dicts, one per word.
    Each dict: {word, glyphs, folio, section, line_idx, word_pos_in_line,
                line_len, prev_word, next_word}
    """
    all_records = []
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        folio = fpath.stem
        section = get_section(folio)
        line_idx = 0
        for raw_line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            raw_line = raw_line.strip()
            if raw_line.startswith('#'): continue
            m = re.match(r'<([^>]+)>', raw_line)
            rest = raw_line[m.end():].strip() if m else raw_line
            if not rest: continue
            ws = [w.strip() for w in re.split(r'[.\s,;]+', rest)
                  if w.strip() and re.match(r'^[a-z]+$', w.strip())]
            if len(ws) < 1:
                continue
            line_len = len(ws)
            for i, w in enumerate(ws):
                rec = {
                    'word': w,
                    'glyphs': eva_to_glyphs(w),
                    'folio': folio,
                    'section': section,
                    'line_idx': line_idx,
                    'word_pos': i,
                    'line_len': line_len,
                    'prev_word': ws[i-1] if i > 0 else None,
                    'next_word': ws[i+1] if i < line_len - 1 else None,
                }
                all_records.append(rec)
            line_idx += 1
    return all_records

# ═══════════════════════════════════════════════════════════════════════
# ITALIAN SOURCE FOR COMPARISON
# ═══════════════════════════════════════════════════════════════════════


def load_italian_structured():
    """Load Italian and create word records with pseudo-sections."""
    raw = fetch_gutenberg(1012)
    text = raw.lower()
    text = re.sub(r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþß]+', ' ', text)
    words = [w for w in text.split() if len(w) >= 1][:50000]

    # Split into pseudo-sections (5 equal chunks) for MI comparison
    chunk_size = len(words) // 5
    section_names = ['sec_A', 'sec_B', 'sec_C', 'sec_D', 'sec_E']

    # Group into lines of ~8 words (VMS average)
    records = []
    line_words = []
    line_idx = 0
    for wi, w in enumerate(words):
        sec = section_names[min(wi // chunk_size, 4)]
        line_words.append((w, sec))
        if len(line_words) >= 8 or wi == len(words) - 1:
            line_len = len(line_words)
            for i, (lw, ls) in enumerate(line_words):
                records.append({
                    'word': lw,
                    'glyphs': list(lw),  # Italian: 1 char = 1 glyph
                    'folio': f'chunk_{wi // chunk_size}',
                    'section': ls,
                    'line_idx': line_idx,
                    'word_pos': i,
                    'line_len': line_len,
                    'prev_word': line_words[i-1][0] if i > 0 else None,
                    'next_word': line_words[i+1][0] if i < line_len - 1 else None,
                })
            line_words = []
            line_idx += 1
    return records

# ═══════════════════════════════════════════════════════════════════════
# WORD ZONE DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════

def decompose_word(glyphs):
    """
    Decompose glyph list into (first, middle, last).
    len=1: first=g[0], middle=None, last=None
    len=2: first=g[0], middle=None, last=g[1]
    len>=3: first=g[0], middle=tuple(g[1:-1]), last=g[-1]
    """
    n = len(glyphs)
    if n == 0: return (None, None, None)
    if n == 1: return (glyphs[0], None, None)
    if n == 2: return (glyphs[0], None, glyphs[-1])
    return (glyphs[0], tuple(glyphs[1:-1]), glyphs[-1])

# ═══════════════════════════════════════════════════════════════════════
# INFORMATION-THEORETIC FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def entropy(counts):
    """Shannon entropy from a Counter or dict of counts."""
    total = sum(counts.values())
    if total <= 0: return 0.0
    H = 0.0
    for n in counts.values():
        if n > 0:
            p = n / total
            H -= p * math.log2(p)
    return H

def entropy_from_labels(labels):
    """Entropy from a flat list of labels."""
    return entropy(Counter(labels))

def mutual_information(xs, ys):
    """
    MI(X; Y) from paired lists of labels.
    Uses MI = H(X) + H(Y) - H(X,Y).
    Returns (MI, H_x, H_y, H_xy, NMI).
    """
    assert len(xs) == len(ys)
    n = len(xs)
    if n == 0:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    cx = Counter(xs)
    cy = Counter(ys)
    cxy = Counter(zip(xs, ys))
    H_x = entropy(cx)
    H_y = entropy(cy)
    H_xy = entropy(cxy)
    MI = H_x + H_y - H_xy
    # Clip to >= 0 (floating point can produce tiny negatives)
    MI = max(0.0, MI)
    denom = min(H_x, H_y)
    NMI = MI / denom if denom > 0 else 0.0
    return (MI, H_x, H_y, H_xy, NMI)

def permutation_test_mi(xs, ys, n_perms=1000, rng=None):
    """
    Permutation z-score for MI(X; Y).
    Shuffles Y, recomputes MI, returns (observed_MI, mean_null, std_null, z).
    """
    if rng is None:
        rng = np.random.default_rng(42)
    observed = mutual_information(xs, ys)[0]
    ys_arr = list(ys)
    null_mis = []
    for _ in range(n_perms):
        rng.shuffle(ys_arr)
        null_mi = mutual_information(xs, ys_arr)[0]
        null_mis.append(null_mi)
    null_mis = np.array(null_mis)
    mu = null_mis.mean()
    sigma = null_mis.std()
    z = (observed - mu) / sigma if sigma > 0 else 0.0
    return (observed, mu, sigma, z)

# ═══════════════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def line_position_bin(word_pos, line_len):
    """Bin word position into: initial, early, mid, late, final."""
    if line_len <= 1: return 'only'
    if word_pos == 0: return 'line_initial'
    if word_pos == line_len - 1: return 'line_final'
    rel = word_pos / (line_len - 1)
    if rel <= 0.33: return 'line_early'
    if rel >= 0.67: return 'line_late'
    return 'line_mid'

def analyze_zone_mi(records, name='VMS', n_perms=500):
    """
    Core analysis: compute MI of each word zone with context variables.
    Returns a dict of results.
    """
    rng = np.random.default_rng(42)

    # Decompose all words
    firsts, middles, lasts = [], [], []
    sections, line_pos_bins = [], []
    next_initials, prev_finals = [], []
    stems = []  # middle as hashable key

    # Track which records have each zone
    first_indices = []
    middle_indices = []
    last_indices = []

    for i, rec in enumerate(records):
        g = rec['glyphs']
        f, m, l = decompose_word(g)
        pos_bin = line_position_bin(rec['word_pos'], rec['line_len'])

        if f is not None:
            first_indices.append(i)
            firsts.append(f)

        if m is not None:
            middle_indices.append(i)
            # Use the middle glyph sequence as a hashable key
            middles.append('|'.join(m) if isinstance(m, tuple) else str(m))

        if l is not None:
            last_indices.append(i)
            lasts.append(l)

    pr(f"\n  {name}: {len(records)} words, "
       f"{len(firsts)} with first, {len(middles)} with middle, {len(lasts)} with last")

    # Zone entropy
    H_first = entropy(Counter(firsts))
    H_mid = entropy(Counter(middles))
    H_last = entropy(Counter(lasts))
    pr(f"  H(first)={H_first:.3f}, H(middle)={H_mid:.3f}, H(last)={H_last:.3f}")

    results = {
        'name': name,
        'n_words': len(records),
        'n_first': len(firsts),
        'n_middle': len(middles),
        'n_last': len(lasts),
        'H_first': round(H_first, 4),
        'H_middle': round(H_mid, 4),
        'H_last': round(H_last, 4),
        'zone_mi': {},
    }

    # ── MI with section (topic) ──
    pr(f"\n  MI(zone; section) — topical information:")
    for zone_name, zone_vals, indices in [
        ('first', firsts, first_indices),
        ('middle', middles, middle_indices),
        ('last', lasts, last_indices),
    ]:
        sec_labels = [records[i]['section'] for i in indices]
        mi, hx, hy, hxy, nmi = mutual_information(zone_vals, sec_labels)
        obs, mu, sigma, z = permutation_test_mi(zone_vals, sec_labels, n_perms, rng)
        pr(f"    {zone_name:>7}: MI={obs:.4f} bits  NMI={nmi:.4f}  "
           f"z={z:+.1f}  (null={mu:.4f}±{sigma:.4f})")
        results['zone_mi'][f'{zone_name}_section'] = {
            'MI': round(obs, 5), 'NMI': round(nmi, 5),
            'z': round(z, 2), 'null_mean': round(mu, 5), 'null_std': round(sigma, 5),
            'H_zone': round(hx, 4), 'H_section': round(hy, 4),
        }

    # ── MI with line position (syntax) ──
    pr(f"\n  MI(zone; line_position) — syntactic position:")
    for zone_name, zone_vals, indices in [
        ('first', firsts, first_indices),
        ('middle', middles, middle_indices),
        ('last', lasts, last_indices),
    ]:
        pos_labels = [line_position_bin(records[i]['word_pos'], records[i]['line_len'])
                      for i in indices]
        mi, hx, hy, hxy, nmi = mutual_information(zone_vals, pos_labels)
        obs, mu, sigma, z = permutation_test_mi(zone_vals, pos_labels, n_perms, rng)
        pr(f"    {zone_name:>7}: MI={obs:.4f} bits  NMI={nmi:.4f}  "
           f"z={z:+.1f}  (null={mu:.4f}±{sigma:.4f})")
        results['zone_mi'][f'{zone_name}_linepos'] = {
            'MI': round(obs, 5), 'NMI': round(nmi, 5),
            'z': round(z, 2), 'null_mean': round(mu, 5), 'null_std': round(sigma, 5),
        }

    # ── MI with next word's initial (forward grammar) ──
    pr(f"\n  MI(zone; next_word_initial) — forward grammar:")
    for zone_name, zone_vals, indices in [
        ('first', firsts, first_indices),
        ('middle', middles, middle_indices),
        ('last', lasts, last_indices),
    ]:
        # Pair zone value with the next word's first glyph
        z_vals = []
        next_vals = []
        for vi, idx in enumerate(indices):
            nw = records[idx]['next_word']
            if nw is not None:
                ng = eva_to_glyphs(nw) if name == 'VMS' else list(nw)
                if len(ng) >= 1:
                    z_vals.append(zone_vals[vi])
                    next_vals.append(ng[0])
        if len(z_vals) < 100:
            pr(f"    {zone_name:>7}: insufficient data ({len(z_vals)} pairs)")
            continue
        mi, hx, hy, hxy, nmi = mutual_information(z_vals, next_vals)
        obs, mu, sigma, z = permutation_test_mi(z_vals, next_vals, n_perms, rng)
        pr(f"    {zone_name:>7}: MI={obs:.4f} bits  NMI={nmi:.4f}  "
           f"z={z:+.1f}  (null={mu:.4f}±{sigma:.4f})")
        results['zone_mi'][f'{zone_name}_next_init'] = {
            'MI': round(obs, 5), 'NMI': round(nmi, 5),
            'z': round(z, 2), 'null_mean': round(mu, 5), 'null_std': round(sigma, 5),
        }

    # ── MI with prev word's final (backward grammar) ──
    pr(f"\n  MI(zone; prev_word_final) — backward grammar:")
    for zone_name, zone_vals, indices in [
        ('first', firsts, first_indices),
        ('middle', middles, middle_indices),
        ('last', lasts, last_indices),
    ]:
        z_vals = []
        prev_vals = []
        for vi, idx in enumerate(indices):
            pw = records[idx]['prev_word']
            if pw is not None:
                pg = eva_to_glyphs(pw) if name == 'VMS' else list(pw)
                if len(pg) >= 1:
                    z_vals.append(zone_vals[vi])
                    prev_vals.append(pg[-1])
        if len(z_vals) < 100:
            pr(f"    {zone_name:>7}: insufficient data ({len(z_vals)} pairs)")
            continue
        mi, hx, hy, hxy, nmi = mutual_information(z_vals, prev_vals)
        obs, mu, sigma, z = permutation_test_mi(z_vals, prev_vals, n_perms, rng)
        pr(f"    {zone_name:>7}: MI={obs:.4f} bits  NMI={nmi:.4f}  "
           f"z={z:+.1f}  (null={mu:.4f}±{sigma:.4f})")
        results['zone_mi'][f'{zone_name}_prev_final'] = {
            'MI': round(obs, 5), 'NMI': round(nmi, 5),
            'z': round(z, 2), 'null_mean': round(mu, 5), 'null_std': round(sigma, 5),
        }

    # ── MI(zone; stem) — zone↔core coupling ──
    pr(f"\n  MI(zone; stem) — how much does zone tell you about word core?")
    # For first: stem = middle+last; for last: stem = first+middle
    # This tests whether the ending is redundant with the rest of the word
    for zone_name, zone_vals, indices in [
        ('first', firsts, first_indices),
        ('last', lasts, last_indices),
    ]:
        z_vals = []
        stem_vals = []
        for vi, idx in enumerate(indices):
            g = records[idx]['glyphs']
            if len(g) < 2: continue
            if zone_name == 'first':
                stem = '|'.join(g[1:])
            else:
                stem = '|'.join(g[:-1])
            z_vals.append(zone_vals[vi])
            stem_vals.append(stem)
        if len(z_vals) < 100:
            pr(f"    {zone_name:>7}: insufficient data ({len(z_vals)} pairs)")
            continue
        mi, hx, hy, hxy, nmi = mutual_information(z_vals, stem_vals)
        obs, mu, sigma, z = permutation_test_mi(z_vals, stem_vals, n_perms, rng)
        pr(f"    {zone_name:>7}: MI={obs:.4f} bits  NMI={nmi:.4f}  "
           f"z={z:+.1f}  (null={mu:.4f}±{sigma:.4f})")
        results['zone_mi'][f'{zone_name}_stem'] = {
            'MI': round(obs, 5), 'NMI': round(nmi, 5),
            'z': round(z, 2), 'null_mean': round(mu, 5), 'null_std': round(sigma, 5),
        }

    return results

def per_character_section_mi(records, name='VMS', n_perms=500, top_n=20):
    """
    For each of the top-N most frequent characters, compute MI(char_presence; section).
    This tells us which specific characters carry topical information.
    """
    rng = np.random.default_rng(99)

    # Count all glyph frequencies
    glyph_counts = Counter()
    for rec in records:
        for g in rec['glyphs']:
            glyph_counts[g] += 1

    top_glyphs = [g for g, _ in glyph_counts.most_common(top_n)]
    pr(f"\n  Per-character MI with section (top {top_n} chars):")
    pr(f"  {'Char':>6}  {'Freq':>6}  {'MI':>8}  {'NMI':>8}  {'z':>6}  Role")

    results = {}
    for glyph in top_glyphs:
        # Binary: does this char appear in this word?
        presence = []
        sec_labels = []
        for rec in records:
            present = 1 if glyph in rec['glyphs'] else 0
            presence.append(present)
            sec_labels.append(rec['section'])
        mi, hx, hy, hxy, nmi = mutual_information(presence, sec_labels)
        obs, mu, sigma, z = permutation_test_mi(presence, sec_labels, n_perms, rng)

        # Determine position role of this character
        pos_counts = Counter()
        for rec in records:
            g = rec['glyphs']
            n = len(g)
            for i, c in enumerate(g):
                if c == glyph:
                    if i == 0: pos_counts['first'] += 1
                    elif i == n-1: pos_counts['last'] += 1
                    else: pos_counts['middle'] += 1
        total_occ = sum(pos_counts.values())
        if total_occ > 0:
            dominant = pos_counts.most_common(1)[0]
            role = f"{dominant[0]}({dominant[1]/total_occ:.0%})"
        else:
            role = "?"

        sig = "***" if z > 3.3 else "**" if z > 2.6 else "*" if z > 2.0 else ""
        pr(f"  {glyph:>6}  {glyph_counts[glyph]:>6}  {obs:.5f}  {nmi:.5f}  {z:>+5.1f}  {role} {sig}")

        results[glyph] = {
            'freq': glyph_counts[glyph],
            'MI': round(obs, 6), 'NMI': round(nmi, 6),
            'z': round(z, 2), 'dominant_position': role,
        }

    return results

def per_position_mi_curve(records, name='VMS', max_pos=8, n_perms=500):
    """
    For each absolute character position (0..max_pos-1), compute:
      MI(char_at_pos; section) — topical information at this position
      MI(char_at_pos; line_position) — syntactic info at this position
    """
    rng = np.random.default_rng(77)

    pr(f"\n  Per-position MI curves (positions 0–{max_pos-1}):")
    pr(f"  {'Pos':>4}  {'N':>6}  {'H(c)':>6}  "
       f"{'MI_sec':>8}  {'z_sec':>6}  {'MI_lpos':>8}  {'z_lpos':>6}")

    results = {}
    for pos in range(max_pos):
        chars = []
        secs = []
        lpos = []
        for rec in records:
            g = rec['glyphs']
            if pos < len(g):
                chars.append(g[pos])
                secs.append(rec['section'])
                lpos.append(line_position_bin(rec['word_pos'], rec['line_len']))

        if len(chars) < 200:
            pr(f"  {pos:>4}  {len(chars):>6}  (insufficient data)")
            continue

        H_c = entropy(Counter(chars))

        mi_sec, _, _, _, nmi_sec = mutual_information(chars, secs)
        obs_sec, mu_sec, sig_sec, z_sec = permutation_test_mi(chars, secs, n_perms, rng)

        mi_lpos, _, _, _, nmi_lpos = mutual_information(chars, lpos)
        obs_lpos, mu_lpos, sig_lpos, z_lpos = permutation_test_mi(chars, lpos, n_perms, rng)

        pr(f"  {pos:>4}  {len(chars):>6}  {H_c:>6.3f}  "
           f"{obs_sec:>8.5f}  {z_sec:>+5.1f}  {obs_lpos:>8.5f}  {z_lpos:>+5.1f}")

        results[pos] = {
            'n': len(chars), 'H_char': round(H_c, 4),
            'MI_section': round(obs_sec, 6), 'z_section': round(z_sec, 2),
            'NMI_section': round(nmi_sec, 6),
            'MI_linepos': round(obs_lpos, 6), 'z_linepos': round(z_lpos, 2),
            'NMI_linepos': round(nmi_lpos, 6),
        }

    return results

def final_char_section_distribution(records, name='VMS'):
    """
    Show the distribution of final characters across sections.
    If finals are terminators, they should be uniformly distributed.
    If grammatical, they may shift with section type.
    """
    pr(f"\n  Final character × section distribution ({name}):")

    # Get top-6 final characters
    final_counts = Counter()
    for rec in records:
        g = rec['glyphs']
        if len(g) >= 2:
            final_counts[g[-1]] += 1

    top_finals = [c for c, _ in final_counts.most_common(6)]
    sections = sorted(set(rec['section'] for rec in records))

    # Count final char per section
    table = defaultdict(Counter)
    sec_totals = Counter()
    for rec in records:
        g = rec['glyphs']
        if len(g) >= 2:
            table[rec['section']][g[-1]] += 1
            sec_totals[rec['section']] += 1

    # Print header
    header = f"  {'Section':>10}"
    for c in top_finals:
        header += f"  {c:>6}"
    header += f"  {'Total':>6}"
    pr(header)

    results = {}
    for sec in sections:
        if sec_totals[sec] < 50: continue
        row = f"  {sec:>10}"
        sec_data = {}
        for c in top_finals:
            frac = table[sec][c] / sec_totals[sec] if sec_totals[sec] > 0 else 0
            row += f"  {frac:>6.1%}"
            sec_data[c] = round(frac, 4)
        row += f"  {sec_totals[sec]:>6}"
        pr(row)
        results[sec] = sec_data

    # Chi-squared test (manual — no scipy)
    # Test independence of final char and section
    pr(f"\n  Chi-squared independence test (final char × section):")
    observed = []
    expected_grand = []
    total_all = sum(sec_totals[s] for s in sections if sec_totals[s] >= 50)
    valid_sections = [s for s in sections if sec_totals[s] >= 50]

    chi2 = 0.0
    df = 0
    for sec in valid_sections:
        for c in top_finals:
            obs = table[sec][c]
            exp = (final_counts[c] / total_all) * sec_totals[sec]
            if exp > 0:
                chi2 += (obs - exp)**2 / exp
                df += 1
    df = max(1, df - len(valid_sections) - len(top_finals) + 1)
    pr(f"  χ²={chi2:.1f}, df={df}")
    # Rough p-value interpretation
    if chi2 / df > 3:
        pr(f"  χ²/df={chi2/df:.1f} — STRONG section dependence")
    elif chi2 / df > 1.5:
        pr(f"  χ²/df={chi2/df:.1f} — moderate section dependence")
    else:
        pr(f"  χ²/df={chi2/df:.1f} — weak/no section dependence")

    return {'chi2': round(chi2, 2), 'df': df, 'chi2_per_df': round(chi2/df, 2),
            'table': results}


# ═══════════════════════════════════════════════════════════════════════
# HYPOTHESIS ADJUDICATION
# ═══════════════════════════════════════════════════════════════════════

def adjudicate(vms_results, ita_results, vms_char_mi, vms_pos_curve):
    """
    Score the three hypotheses based on all evidence.
    """
    pr("\n" + "="*70)
    pr("HYPOTHESIS ADJUDICATION")
    pr("="*70)

    # Extract key MI values
    zm = vms_results['zone_mi']

    # 1. Final carries topical info?
    final_sec = zm.get('last_section', {})
    first_sec = zm.get('first_section', {})
    mid_sec = zm.get('middle_section', {})

    final_sec_z = final_sec.get('z', 0)
    first_sec_z = first_sec.get('z', 0)
    mid_sec_z = mid_sec.get('z', 0)

    final_sec_nmi = final_sec.get('NMI', 0)
    first_sec_nmi = first_sec.get('NMI', 0)
    mid_sec_nmi = mid_sec.get('NMI', 0)

    pr(f"\n  1. Topical information by zone:")
    pr(f"     First:  NMI={first_sec_nmi:.4f}  z={first_sec_z:+.1f}")
    pr(f"     Middle: NMI={mid_sec_nmi:.4f}  z={mid_sec_z:+.1f}")
    pr(f"     Last:   NMI={final_sec_nmi:.4f}  z={final_sec_z:+.1f}")

    # 2. Final participates in grammar?
    final_next = zm.get('last_next_init', {})
    final_prev = zm.get('last_prev_final', {})
    first_next = zm.get('first_next_init', {})
    first_prev = zm.get('first_prev_final', {})

    pr(f"\n  2. Inter-word grammar by zone:")
    pr(f"     First  → next_init:  NMI={first_next.get('NMI',0):.4f}  z={first_next.get('z',0):+.1f}")
    pr(f"     Last   → next_init:  NMI={final_next.get('NMI',0):.4f}  z={final_next.get('z',0):+.1f}")
    pr(f"     First  ← prev_final: NMI={first_prev.get('NMI',0):.4f}  z={first_prev.get('z',0):+.1f}")
    pr(f"     Last   ← prev_final: NMI={final_prev.get('NMI',0):.4f}  z={final_prev.get('z',0):+.1f}")

    # 3. Final coupled to stem?
    final_stem = zm.get('last_stem', {})
    first_stem = zm.get('first_stem', {})

    pr(f"\n  3. Zone↔stem coupling:")
    pr(f"     First ↔ rest:  NMI={first_stem.get('NMI',0):.4f}  z={first_stem.get('z',0):+.1f}")
    pr(f"     Last  ↔ rest:  NMI={final_stem.get('NMI',0):.4f}  z={final_stem.get('z',0):+.1f}")

    # 4. Line position sensitivity?
    final_lpos = zm.get('last_linepos', {})
    first_lpos = zm.get('first_linepos', {})

    pr(f"\n  4. Line position sensitivity:")
    pr(f"     First:  NMI={first_lpos.get('NMI',0):.4f}  z={first_lpos.get('z',0):+.1f}")
    pr(f"     Last:   NMI={final_lpos.get('NMI',0):.4f}  z={final_lpos.get('z',0):+.1f}")

    # Score hypotheses
    pr(f"\n  SCORING:")
    scores = {'terminator': 0, 'grammar': 0, 'content': 0}
    evidence = []

    # Test A: Terminators predict MI(final; section) ≈ 0
    if final_sec_z < 2.0:
        scores['terminator'] += 2
        evidence.append("Final has NO significant topical MI → terminator +2")
    elif final_sec_z < 5.0:
        scores['grammar'] += 1
        evidence.append(f"Final has weak topical MI (z={final_sec_z:.1f}) → grammar +1")
    else:
        scores['content'] += 2
        evidence.append(f"Final has strong topical MI (z={final_sec_z:.1f}) → content +2")

    # Test B: Grammar predicts MI(final; next_word_initial) >> 0
    final_next_z = final_next.get('z', 0)
    if final_next_z > 10:
        scores['grammar'] += 3
        evidence.append(f"Final→next_init strong (z={final_next_z:.1f}) → grammar +3")
    elif final_next_z > 3:
        scores['grammar'] += 1
        scores['content'] += 1
        evidence.append(f"Final→next_init moderate (z={final_next_z:.1f}) → grammar +1, content +1")
    else:
        scores['terminator'] += 1
        evidence.append(f"Final→next_init weak (z={final_next_z:.1f}) → terminator +1")

    # Test C: Terminators predict LOW MI(final; stem)
    final_stem_z = final_stem.get('z', 0)
    final_stem_nmi = final_stem.get('NMI', 0)
    if final_stem_z < 2.0:
        scores['terminator'] += 2
        evidence.append(f"Final↔stem decoupled (z={final_stem_z:.1f}) → terminator +2")
    elif final_stem_nmi < 0.05:
        scores['grammar'] += 1
        evidence.append(f"Final↔stem weak coupling (NMI={final_stem_nmi:.4f}) → grammar +1")
    else:
        scores['content'] += 2
        evidence.append(f"Final↔stem coupled (NMI={final_stem_nmi:.4f}) → content +2")

    # Test D: Grammar predicts MI(final; line_position) > 0
    final_lpos_z = final_lpos.get('z', 0)
    if final_lpos_z > 5:
        scores['grammar'] += 2
        evidence.append(f"Final sensitive to line position (z={final_lpos_z:.1f}) → grammar +2")
    elif final_lpos_z > 2:
        scores['grammar'] += 1
        evidence.append(f"Final weakly line-position sensitive (z={final_lpos_z:.1f}) → grammar +1")
    else:
        scores['terminator'] += 1
        evidence.append(f"Final NOT line-position sensitive → terminator +1")

    # Test E: Compare final MI ratio to Italian
    ita_zm = ita_results['zone_mi']
    ita_final_sec_nmi = ita_zm.get('last_section', {}).get('NMI', 0)
    ita_first_sec_nmi = ita_zm.get('first_section', {}).get('NMI', 0)
    if ita_first_sec_nmi > 0:
        ita_ratio = ita_final_sec_nmi / ita_first_sec_nmi
    else:
        ita_ratio = 0
    if first_sec_nmi > 0:
        vms_ratio = final_sec_nmi / first_sec_nmi
    else:
        vms_ratio = 0
    pr(f"\n  Final/First topical NMI ratio:")
    pr(f"    VMS:     {vms_ratio:.3f}")
    pr(f"    Italian: {ita_ratio:.3f}")
    if vms_ratio < 0.3 * ita_ratio:
        scores['terminator'] += 1
        evidence.append(f"VMS final carries much LESS topic info than Italian → terminator +1")
    elif vms_ratio > 0.7 * ita_ratio:
        scores['content'] += 1
        evidence.append(f"VMS final carries similar topic info to Italian → content +1")
    else:
        scores['grammar'] += 1
        evidence.append(f"VMS final carries intermediate topic info → grammar +1")

    pr(f"\n  Evidence chain:")
    for e in evidence:
        pr(f"    • {e}")

    pr(f"\n  HYPOTHESIS SCORES:")
    pr(f"    Terminator (content-free markers):  {scores['terminator']}")
    pr(f"    Grammar (inflectional morphemes):   {scores['grammar']}")
    pr(f"    Content (constrained but semantic):  {scores['content']}")

    winner = max(scores, key=scores.get)
    # Check if it's decisive
    sorted_scores = sorted(scores.values(), reverse=True)
    margin = sorted_scores[0] - sorted_scores[1]

    if margin >= 3:
        pr(f"\n  VERDICT: {winner.upper()} — clear winner (margin={margin})")
    elif margin >= 1:
        pr(f"\n  VERDICT: {winner.upper()} — lean (margin={margin})")
    else:
        pr(f"\n  VERDICT: INCONCLUSIVE — no clear winner")

    return {'scores': scores, 'winner': winner, 'margin': margin,
            'evidence': evidence, 'vms_ratio': round(vms_ratio, 4),
            'ita_ratio': round(ita_ratio, 4)}

# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("="*70)
    pr("word_functional_anatomy: Functional Anatomy of the VMS Word")
    pr("="*70)
    pr()
    pr("QUESTION: What role do word-final characters play?")
    pr("  A. Terminators — content-free end markers")
    pr("  B. Grammatical morphemes — small inflectional set")
    pr("  C. Content characters — constrained but information-bearing")
    pr()

    # ── Load VMS ──
    pr("Loading VMS with full provenance...")
    vms_records = load_vms_structured()
    pr(f"  {len(vms_records)} words loaded")

    section_counts = Counter(r['section'] for r in vms_records)
    pr(f"  Sections: {dict(section_counts.most_common())}")

    # Quick sanity: final character distribution
    final_chars = Counter()
    for r in vms_records:
        g = r['glyphs']
        if len(g) >= 2:
            final_chars[g[-1]] += 1
    total_final = sum(final_chars.values())
    pr(f"\n  Final character distribution (words ≥ 2 glyphs):")
    for c, n in final_chars.most_common(8):
        pr(f"    {c:>4}: {n:>5} ({n/total_final:.1%})")

    # ── Load Italian for comparison ──
    pr("\nFetching Italian source text...")
    try:
        ita_records = load_italian_structured()
        pr(f"  {len(ita_records)} Italian words loaded")
        have_italian = True
    except Exception as e:
        pr(f"  WARN: Could not load Italian: {e}")
        pr(f"  Proceeding with VMS-only analysis")
        have_italian = False

    # ═══════════════════════════════════════════════════════════════════
    # ANALYSIS 1: Zone-level MI matrix
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "="*70)
    pr("ANALYSIS 1: Zone-level MI with context variables")
    pr("="*70)

    vms_results = analyze_zone_mi(vms_records, 'VMS', n_perms=500)

    if have_italian:
        pr("\n  --- Italian comparison ---")
        ita_results = analyze_zone_mi(ita_records, 'Italian', n_perms=500)
    else:
        ita_results = {'zone_mi': {}}

    # ═══════════════════════════════════════════════════════════════════
    # ANALYSIS 2: Per-character MI with section
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "="*70)
    pr("ANALYSIS 2: Per-character topical information")
    pr("="*70)

    vms_char_mi = per_character_section_mi(vms_records, 'VMS', n_perms=500, top_n=20)

    # ═══════════════════════════════════════════════════════════════════
    # ANALYSIS 3: Per-position MI curves
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "="*70)
    pr("ANALYSIS 3: Position-resolved information curves")
    pr("="*70)

    vms_pos_curve = per_position_mi_curve(vms_records, 'VMS', max_pos=8, n_perms=500)

    if have_italian:
        pr("\n  --- Italian comparison ---")
        ita_pos_curve = per_position_mi_curve(ita_records, 'Italian', max_pos=8, n_perms=500)
    else:
        ita_pos_curve = {}

    # ═══════════════════════════════════════════════════════════════════
    # ANALYSIS 4: Final char × section cross-tab
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "="*70)
    pr("ANALYSIS 4: Final character distribution across sections")
    pr("="*70)

    vms_final_dist = final_char_section_distribution(vms_records, 'VMS')

    if have_italian:
        pr("\n  --- Italian comparison ---")
        ita_final_dist = final_char_section_distribution(ita_records, 'Italian')
    else:
        ita_final_dist = {}

    # ═══════════════════════════════════════════════════════════════════
    # ADJUDICATION
    # ═══════════════════════════════════════════════════════════════════
    verdict = adjudicate(vms_results, ita_results, vms_char_mi, vms_pos_curve)

    # ═══════════════════════════════════════════════════════════════════
    # SKEPTICAL CAVEATS
    # ═══════════════════════════════════════════════════════════════════
    pr("\n" + "="*70)
    pr("SKEPTICAL CAVEATS")
    pr("="*70)
    pr("""
  1. Section labels are APPROXIMATE. The folio→section mapping is a rough
     community consensus, not ground truth. MI with section is a lower
     bound on topical information (finer-grained topics would show more).

  2. MI bias. In small samples, MI is positively biased. Our permutation
     z-scores correct for this, but the RAW MI values should not be
     compared across different sample sizes without normalization (NMI).

  3. EVA transcription artifacts. The glyph segmentation (ch, sh, etc.)
     affects what counts as "first" and "last." We use EVA compound
     glyphs as atomic units, consistent with the encoding-model tests.

  4. Zone boundaries are arbitrary. A 1-char first + 1-char last
     decomposition may miss multi-character prefixes/suffixes. But
     synthesis_stress_test showed 95.6% of morphological MI is single-character,
     so 1-char zones capture the dominant signal.

  5. Italian comparison is weak. Pseudo-sections (sequential chunks)
     don't have the topical coherence of VMS's illustrated sections.
     Italian MI values are LOWER BOUNDS on what a real section
     structure would produce.

  6. The hypothesis test is NOT exhaustive. "Terminator," "grammar,"
     and "content" are simplified categories. Real writing systems
     often have characters serving multiple roles simultaneously.
""")

    # ═══════════════════════════════════════════════════════════════════
    # OUTPUT
    # ═══════════════════════════════════════════════════════════════════
    output = {
        'test': 'word_functional_anatomy',
        'title': 'Functional Anatomy of the VMS Word',
        'vms_results': vms_results,
        'ita_results': ita_results if have_italian else None,
        'vms_char_mi': vms_char_mi,
        'vms_pos_curve': vms_pos_curve,
        'ita_pos_curve': ita_pos_curve if have_italian else None,
        'vms_final_dist': vms_final_dist,
        'ita_final_dist': ita_final_dist if have_italian else None,
        'verdict': verdict,
    }

    json_path = RESULTS_DIR / 'word_functional_anatomy_output.json'
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    pr(f"\nResults saved to {json_path}")

    txt_path = RESULTS_DIR / 'word_functional_anatomy_output.txt'
    with open(txt_path, 'w') as f:
        f.write(''.join(OUTPUT))
    pr(f"Full output saved to {txt_path}")

if __name__ == '__main__':
    main()
