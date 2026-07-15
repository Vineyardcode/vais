#!/usr/bin/env python3
"""
Phase 78 — The Allograph Hypothesis: Are p≡t and f≡k?

═══════════════════════════════════════════════════════════════════════

QUESTION: Phase 77b proved {p,f} are first-line characters and {t,k}
are body-text characters. But WHY? Two competing hypotheses:

  H1 (ALLOGRAPH): p is just "first-line t" and f is "first-line k" —
      the same underlying letter written differently on line 1.
      Prediction: replacing p→t in L1 words produces valid L2+ words.
      Context distributions (successor/predecessor) should match.

  H2 (INDEPENDENT): p and f are separate symbols from t and k, with
      different functions (Phase 13: p=process, f=botanical vs
      t=celestial, k=generic).
      Prediction: p→t substitution produces nonsense; contexts diverge.

  H3 (PREFIX/MARKER): p and f are structural markers ADDED to words
      on L1 — not substituting for anything.
      Prediction: STRIPPING p/f from L1 words yields valid words.

TESTS:
A. SUBSTITUTION TEST — Replace p→t in L1 words. What fraction match
   real L2+ vocabulary? Controls: p→k, f→k, f→t, random→random.

B. CONTEXT DISTRIBUTION — JSD between successor distributions:
   {glyph after p on L1} vs {glyph after t on L2+},
   {glyph after f on L1} vs {glyph after k on L2+}.
   If allographs, JSD should be low (similar contexts).

C. DELETION TEST — Strip p/f glyphs from L1 words. What fraction of
   residues are valid L2+ words? Compare with stripping t/k.

D. SLOT POSITION TEST — In the IMF grammar, do p and t occupy the
   same positional slots within words? Do f and k?

E. SEMANTIC RETEST — Redo Phase 13 semantic domain analysis using ONLY
   L2+ data. If p still shows "process" enrichment without L1, the
   semantic classification is real, not a positional artifact.

F. WORD-PAIR MATCHING — For each L1 word containing p, find the most
   similar L2+ word (edit distance). Is that word a t-for-p variant?
"""

import re, sys, io, math
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from common import clean_word, eva_to_glyphs, extract_words, folio_section

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FOLIO_DIR = Path(__file__).resolve().parent.parent / 'folios'
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))

np.random.seed(42)

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']
PLAIN_GALLOWS = {'p', 't', 'k', 'f'}
FIRST_LINE_GLYPHS = {'p', 'f', 'cph', 'cfh'}
BODY_TEXT_GLYPHS = {'t', 'k', 'cth', 'ckh'}


def glyphs_to_word(glyphs):
    return ''.join(glyphs)




def jsd(d1, d2):
    """Jensen-Shannon divergence between two Counter distributions."""
    keys = set(d1) | set(d2)
    if not keys:
        return 0.0
    t1 = sum(d1.values()) or 1
    t2 = sum(d2.values()) or 1
    divergence = 0.0
    for k in keys:
        p = d1.get(k, 0) / t1
        q = d2.get(k, 0) / t2
        m = (p + q) / 2
        if p > 0 and m > 0:
            divergence += p * math.log2(p / m) / 2
        if q > 0 and m > 0:
            divergence += q * math.log2(q / m) / 2
    return divergence


# ═══════════════════════════════════════════════════════════════════════
# PARSE DATA
# ═══════════════════════════════════════════════════════════════════════

def parse_all_data():
    """Parse all folios returning line-level paragraph data."""
    paragraphs = []
    current_para = None

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)

    for filepath in folio_files:
        section = folio_section(filepath.stem)
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                m = re.match(r'<([^>]+)>', line)
                if not m:
                    continue
                tag = m.group(1)
                rest = line[m.end():].strip()
                if not rest:
                    continue
                is_para_start = '@P' in tag or '*P' in tag
                is_continuation = '+P' in tag

                if is_para_start:
                    if current_para and current_para['lines']:
                        paragraphs.append(current_para)
                    words = extract_words(rest)
                    current_para = {
                        'section': section,
                        'folio': filepath.stem,
                        'first_word': words[0] if words else '',
                        'lines': [{'line_num': 1, 'words': words, 'is_first_line': True}]
                    }
                elif is_continuation and current_para:
                    words = extract_words(rest)
                    ln = len(current_para['lines']) + 1
                    current_para['lines'].append({
                        'line_num': ln,
                        'words': words,
                        'is_first_line': False
                    })

    if current_para and current_para['lines']:
        paragraphs.append(current_para)

    return paragraphs


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def main():
    pr("=" * 72)
    pr("PHASE 78 — THE ALLOGRAPH HYPOTHESIS: ARE p≡t AND f≡k?")
    pr("=" * 72)
    pr()

    paragraphs = parse_all_data()
    pr(f"Parsed {len(paragraphs)} paragraphs")

    # Collect L1 words (excl W1) and L2+ words
    l1_words = []   # (word, section)
    l2_words = []   # (word, section)
    for p in paragraphs:
        for line_data in p['lines']:
            words = line_data['words']
            section = p['section']
            if line_data['is_first_line']:
                for w in words[1:]:  # exclude W1
                    l1_words.append((w, section))
            else:
                for w in words:
                    l2_words.append((w, section))

    pr(f"L1 words (excl W1): {len(l1_words)}")
    pr(f"L2+ words: {len(l2_words)}")

    l2_vocab = set(w for w, _ in l2_words)
    l2_word_counter = Counter(w for w, _ in l2_words)
    l1_vocab = set(w for w, _ in l1_words)
    l1_word_counter = Counter(w for w, _ in l1_words)

    pr(f"L1 unique types: {len(l1_vocab)}")
    pr(f"L2+ unique types: {len(l2_vocab)}")

    # ═══════════════════════════════════════════════════════════════════
    # TEST A: SUBSTITUTION TEST
    # ═══════════════════════════════════════════════════════════════════
    pr()
    pr("=" * 72)
    pr("TEST A: SUBSTITUTION TEST")
    pr("=" * 72)
    pr()
    pr("For each L1 word containing a target glyph, substitute it and")
    pr("check if the result appears in L2+ vocabulary.")
    pr()

    # Collect L1 words that contain p (as a glyph)
    def words_with_glyph(word_list, target_glyph):
        """Return words that contain the target glyph."""
        result = []
        for w, sec in word_list:
            glyphs = eva_to_glyphs(w)
            if target_glyph in glyphs:
                result.append(w)
        return result

    def substitute_glyph(word, old_glyph, new_glyph):
        """Replace all instances of old_glyph with new_glyph in word."""
        glyphs = eva_to_glyphs(word)
        new_glyphs = [new_glyph if g == old_glyph else g for g in glyphs]
        return glyphs_to_word(new_glyphs)

    def substitution_match_rate(words, old_g, new_g, vocab):
        """For each word, substitute old→new, check if result is in vocab."""
        matches = 0
        total = len(words)
        matched_pairs = []
        for w in words:
            subbed = substitute_glyph(w, old_g, new_g)
            if subbed in vocab:
                matches += 1
                matched_pairs.append((w, subbed))
        rate = matches / total if total else 0
        return matches, total, rate, matched_pairs

    # Hypothesis tests
    l1_p_words = words_with_glyph(l1_words, 'p')
    l1_f_words = words_with_glyph(l1_words, 'f')
    l2_t_words = words_with_glyph(l2_words, 't')
    l2_k_words = words_with_glyph(l2_words, 'k')

    pr(f"L1 words with 'p' glyph: {len(l1_p_words)}")
    pr(f"L1 words with 'f' glyph: {len(l1_f_words)}")
    pr(f"L2+ words with 't' glyph: {len(l2_t_words)}")
    pr(f"L2+ words with 'k' glyph: {len(l2_k_words)}")
    pr()

    # H1 predictions (allograph): p→t and f→k should have HIGH match
    pr("H1 (allograph) predictions:")
    m, t, r, pairs_pt = substitution_match_rate(l1_p_words, 'p', 't', l2_vocab)
    pr(f"  p→t on L1 words: {m}/{t} = {r:.1%} match L2+ vocab")
    m, t, r, pairs_fk = substitution_match_rate(l1_f_words, 'f', 'k', l2_vocab)
    pr(f"  f→k on L1 words: {m}/{t} = {r:.1%} match L2+ vocab")
    pr()

    # Controls (should be LOWER if allograph is correct)
    pr("Controls (should be lower if H1 correct):")
    m, t, r, _ = substitution_match_rate(l1_p_words, 'p', 'k', l2_vocab)
    pr(f"  p→k on L1 words: {m}/{t} = {r:.1%} match L2+ vocab")
    m, t, r, _ = substitution_match_rate(l1_p_words, 'p', 'f', l2_vocab)
    pr(f"  p→f on L1 words: {m}/{t} = {r:.1%} match L2+ vocab")
    m, t, r, _ = substitution_match_rate(l1_f_words, 'f', 't', l2_vocab)
    pr(f"  f→t on L1 words: {m}/{t} = {r:.1%} match L2+ vocab")
    m, t, r, _ = substitution_match_rate(l1_f_words, 'f', 'p', l2_vocab)
    pr(f"  f→p on L1 words: {m}/{t} = {r:.1%} match L2+ vocab")
    pr()

    # Reverse direction: t→p on L2+ should also work
    pr("Reverse direction (L2+ → L1 vocab):")
    m, t, r, _ = substitution_match_rate(l2_t_words, 't', 'p', l1_vocab)
    pr(f"  t→p on L2+ words: {m}/{t} = {r:.1%} match L1 vocab")
    m, t, r, _ = substitution_match_rate(l2_k_words, 'k', 'f', l1_vocab)
    pr(f"  k→f on L2+ words: {m}/{t} = {r:.1%} match L1 vocab")
    pr()

    # H3 predictions (prefix): stripping p/f should yield valid words
    pr("H3 (prefix/marker) predictions:")
    def strip_glyph(word, target):
        glyphs = eva_to_glyphs(word)
        stripped = [g for g in glyphs if g != target]
        return glyphs_to_word(stripped) if stripped else ''

    strip_match = 0
    strip_total = 0
    for w in l1_p_words:
        residue = strip_glyph(w, 'p')
        if residue and residue in l2_vocab:
            strip_match += 1
        strip_total += 1
    pr(f"  Strip p from L1 p-words → L2+ match: {strip_match}/{strip_total} = {strip_match/strip_total:.1%}")

    strip_match = 0
    strip_total = 0
    for w in l1_f_words:
        residue = strip_glyph(w, 'f')
        if residue and residue in l2_vocab:
            strip_match += 1
        strip_total += 1
    pr(f"  Strip f from L1 f-words → L2+ match: {strip_match}/{strip_total} = {strip_match/strip_total:.1%}")
    pr()

    # Control: strip t/k from L2+ words
    l2_t_sample = l2_t_words[:500]
    l2_k_sample = l2_k_words[:500]
    sm = sum(1 for w in l2_t_sample if strip_glyph(w, 't') in l2_vocab)
    pr(f"  Control: strip t from L2+ t-words → L2+ match: {sm}/{len(l2_t_sample)} = {sm/len(l2_t_sample):.1%}")
    sm = sum(1 for w in l2_k_sample if strip_glyph(w, 'k') in l2_vocab)
    pr(f"  Control: strip k from L2+ k-words → L2+ match: {sm}/{len(l2_k_sample)} = {sm/len(l2_k_sample):.1%}")
    pr()

    # Show example matched pairs
    pr("Example p→t matches (L1 word → L2+ word):")
    for orig, subbed in pairs_pt[:20]:
        freq = l2_word_counter.get(subbed, 0)
        pr(f"  {orig:20s} → {subbed:20s} (L2+ freq: {freq})")
    pr()
    pr("Example f→k matches (L1 word → L2+ word):")
    for orig, subbed in pairs_fk[:20]:
        freq = l2_word_counter.get(subbed, 0)
        pr(f"  {orig:20s} → {subbed:20s} (L2+ freq: {freq})")

    # ═══════════════════════════════════════════════════════════════════
    # TEST B: CONTEXT DISTRIBUTION (Successor JSD)
    # ═══════════════════════════════════════════════════════════════════
    pr()
    pr("=" * 72)
    pr("TEST B: CONTEXT DISTRIBUTION (Successor & Predecessor JSD)")
    pr("=" * 72)
    pr()
    pr("If p≡t, then the glyph AFTER p should have the same distribution")
    pr("as the glyph AFTER t. Low JSD = similar contexts = allograph support.")
    pr()

    def get_successor_dist(words_with_sec, target_glyph):
        """Get distribution of glyph immediately after target."""
        succ = Counter()
        for w, _ in words_with_sec:
            glyphs = eva_to_glyphs(w)
            for i, g in enumerate(glyphs):
                if g == target_glyph and i + 1 < len(glyphs):
                    succ[glyphs[i + 1]] += 1
        return succ

    def get_predecessor_dist(words_with_sec, target_glyph):
        """Get distribution of glyph immediately before target."""
        pred = Counter()
        for w, _ in words_with_sec:
            glyphs = eva_to_glyphs(w)
            for i, g in enumerate(glyphs):
                if g == target_glyph and i > 0:
                    pred[glyphs[i - 1]] += 1
        return pred

    # Successor distributions
    p_succ_l1 = get_successor_dist(l1_words, 'p')
    t_succ_l2 = get_successor_dist(l2_words, 't')
    f_succ_l1 = get_successor_dist(l1_words, 'f')
    k_succ_l2 = get_successor_dist(l2_words, 'k')

    # Cross comparisons for controls
    p_succ_l2 = get_successor_dist(l2_words, 'p')
    t_succ_l1 = get_successor_dist(l1_words, 't')
    k_succ_l1 = get_successor_dist(l1_words, 'k')
    f_succ_l2 = get_successor_dist(l2_words, 'f')

    pr("SUCCESSOR JSD (lower = more similar contexts):")
    pr(f"  H1 predictions (should be LOW):")
    pr(f"    JSD(p_L1_succ, t_L2_succ) = {jsd(p_succ_l1, t_succ_l2):.4f}  [p≡t test]")
    pr(f"    JSD(f_L1_succ, k_L2_succ) = {jsd(f_succ_l1, k_succ_l2):.4f}  [f≡k test]")
    pr()
    pr(f"  Controls (should be HIGHER if H1 correct):")
    pr(f"    JSD(p_L1_succ, k_L2_succ) = {jsd(p_succ_l1, k_succ_l2):.4f}  [p≡k? no]")
    pr(f"    JSD(f_L1_succ, t_L2_succ) = {jsd(f_succ_l1, t_succ_l2):.4f}  [f≡t? no]")
    pr()
    pr(f"  Same-glyph baselines:")
    pr(f"    JSD(p_L1_succ, p_L2_succ) = {jsd(p_succ_l1, p_succ_l2):.4f}  [p=p across lines]")
    pr(f"    JSD(t_L1_succ, t_L2_succ) = {jsd(t_succ_l1, t_succ_l2):.4f}  [t=t across lines]")
    pr(f"    JSD(f_L1_succ, f_L2_succ) = {jsd(f_succ_l1, f_succ_l2):.4f}  [f=f across lines]")
    pr(f"    JSD(k_L1_succ, k_L2_succ) = {jsd(k_succ_l1, k_succ_l2):.4f}  [k=k across lines]")
    pr()

    # Predecessor distributions
    p_pred_l1 = get_predecessor_dist(l1_words, 'p')
    t_pred_l2 = get_predecessor_dist(l2_words, 't')
    f_pred_l1 = get_predecessor_dist(l1_words, 'f')
    k_pred_l2 = get_predecessor_dist(l2_words, 'k')
    p_pred_l2 = get_predecessor_dist(l2_words, 'p')
    k_pred_l1 = get_predecessor_dist(l1_words, 'k')

    pr("PREDECESSOR JSD:")
    pr(f"  H1 predictions (should be LOW):")
    pr(f"    JSD(p_L1_pred, t_L2_pred) = {jsd(p_pred_l1, t_pred_l2):.4f}  [p≡t test]")
    pr(f"    JSD(f_L1_pred, k_L2_pred) = {jsd(f_pred_l1, k_pred_l2):.4f}  [f≡k test]")
    pr()
    pr(f"  Same-glyph baselines:")
    pr(f"    JSD(p_L1_pred, p_L2_pred) = {jsd(p_pred_l1, p_pred_l2):.4f}  [p=p across lines]")
    pr(f"    JSD(k_L1_pred, k_L2_pred) = {jsd(k_pred_l1, k_pred_l2):.4f}  [k=k across lines]")
    pr()

    # Show the actual distributions for inspection
    pr("Top successors (for interpretation):")
    for label, dist in [("p on L1", p_succ_l1), ("t on L2+", t_succ_l2),
                         ("f on L1", f_succ_l1), ("k on L2+", k_succ_l2)]:
        top = dist.most_common(8)
        total = sum(dist.values())
        parts = [f"{g}:{c/total:.2%}" for g, c in top]
        pr(f"  {label:12s}: {', '.join(parts)}")
    pr()

    # ═══════════════════════════════════════════════════════════════════
    # TEST C: DELETION TEST
    # ═══════════════════════════════════════════════════════════════════
    pr("=" * 72)
    pr("TEST C: DELETION TEST — What remains after stripping gallows?")
    pr("=" * 72)
    pr()
    pr("If p/f are PREFIXED markers on L1, stripping them should leave")
    pr("coherent residues. If they're integral to the word, residues")
    pr("should be nonsensical fragment.")
    pr()

    # For L1 p-words: where does p appear in the word?
    p_positions = Counter()
    f_positions = Counter()
    for w in l1_p_words:
        glyphs = eva_to_glyphs(w)
        for i, g in enumerate(glyphs):
            if g == 'p':
                # Normalize: first, middle, last
                if i == 0:
                    p_positions['first'] += 1
                elif i == len(glyphs) - 1:
                    p_positions['last'] += 1
                else:
                    p_positions['middle'] += 1

    for w in l1_f_words:
        glyphs = eva_to_glyphs(w)
        for i, g in enumerate(glyphs):
            if g == 'f':
                if i == 0:
                    f_positions['first'] += 1
                elif i == len(glyphs) - 1:
                    f_positions['last'] += 1
                else:
                    f_positions['middle'] += 1

    pr(f"Position of 'p' glyph within L1 p-words:")
    total_p = sum(p_positions.values())
    for pos in ['first', 'middle', 'last']:
        pr(f"  {pos}: {p_positions[pos]}/{total_p} = {p_positions[pos]/total_p:.1%}")

    pr(f"\nPosition of 'f' glyph within L1 f-words:")
    total_f = sum(f_positions.values())
    for pos in ['first', 'middle', 'last']:
        pr(f"  {pos}: {f_positions[pos]}/{total_f} = {f_positions[pos]/total_f:.1%}")
    pr()

    # Analyze residues after stripping
    pr("Residue analysis (strip first p/f glyph only):")
    def strip_first_occurrence(word, target):
        glyphs = eva_to_glyphs(word)
        new = []
        removed = False
        for g in glyphs:
            if g == target and not removed:
                removed = True
                continue
            new.append(g)
        return glyphs_to_word(new) if new else ''

    p_residues = Counter()
    f_residues = Counter()
    for w in l1_p_words:
        r = strip_first_occurrence(w, 'p')
        if r:
            p_residues[r] += 1
    for w in l1_f_words:
        r = strip_first_occurrence(w, 'f')
        if r:
            f_residues[r] += 1

    # What fraction of residues are valid words on L2+?
    p_res_match = sum(1 for r in p_residues if r in l2_vocab)
    f_res_match = sum(1 for r in f_residues if r in l2_vocab)
    pr(f"p-residues matching L2+ vocab: {p_res_match}/{len(p_residues)} types = {p_res_match/len(p_residues):.1%}")
    pr(f"f-residues matching L2+ vocab: {f_res_match}/{len(f_residues)} types = {f_res_match/len(f_residues):.1%}")
    pr()

    # Show top residues and whether they match
    pr("Top 15 p-residues:")
    for r, c in p_residues.most_common(15):
        in_l2 = "✓ L2+" if r in l2_vocab else "✗ NOT in L2+"
        t_version = substitute_glyph(r, 'placeholder', 'placeholder')  # identity
        # Check: is the original word = 'p' + residue? And does 't' + residue exist?
        t_word = 't' + r if eva_to_glyphs(r)[0] != 't' else r
        pr(f"  '{r}' (×{c}) — {in_l2}")
    pr()
    pr("Top 15 f-residues:")
    for r, c in f_residues.most_common(15):
        in_l2 = "✓ L2+" if r in l2_vocab else "✗ NOT in L2+"
        pr(f"  '{r}' (×{c}) — {in_l2}")

    # ═══════════════════════════════════════════════════════════════════
    # TEST D: SLOT POSITION TEST
    # ═══════════════════════════════════════════════════════════════════
    pr()
    pr("=" * 72)
    pr("TEST D: SLOT POSITION — Where do gallows appear in words?")
    pr("=" * 72)
    pr()
    pr("If p≡t (allographs), they should appear at the SAME positions")
    pr("within words. Normalized position = glyph_index / word_length.")
    pr()

    def glyph_positions(word_list, target):
        """Get normalized positions (0-1) of target glyph in words."""
        positions = []
        for w, _ in word_list:
            glyphs = eva_to_glyphs(w)
            n = len(glyphs)
            if n < 2:
                continue
            for i, g in enumerate(glyphs):
                if g == target:
                    positions.append(i / (n - 1))  # 0=first, 1=last
        return positions

    # Get positions
    p_pos_l1 = glyph_positions(l1_words, 'p')
    t_pos_l2 = glyph_positions(l2_words, 't')
    f_pos_l1 = glyph_positions(l1_words, 'f')
    k_pos_l2 = glyph_positions(l2_words, 'k')
    t_pos_l1 = glyph_positions(l1_words, 't')
    k_pos_l1 = glyph_positions(l1_words, 'k')
    p_pos_l2 = glyph_positions(l2_words, 'p')

    pr("Mean normalized position (0=word-start, 1=word-end):")
    for label, pos in [("p on L1", p_pos_l1), ("t on L2+", t_pos_l2),
                        ("t on L1", t_pos_l1), ("p on L2+", p_pos_l2),
                        ("f on L1", f_pos_l1), ("k on L2+", k_pos_l2),
                        ("k on L1", k_pos_l1)]:
        if pos:
            pr(f"  {label:12s}: mean={np.mean(pos):.3f}, std={np.std(pos):.3f}, n={len(pos)}")
        else:
            pr(f"  {label:12s}: n=0")
    pr()

    # Position distribution histogram (binned)
    pr("Position distribution (5 bins: 0-0.2, 0.2-0.4, ..., 0.8-1.0):")
    bins = [0, 0.2, 0.4, 0.6, 0.8, 1.001]
    for label, pos in [("p_L1", p_pos_l1), ("t_L2", t_pos_l2),
                        ("f_L1", f_pos_l1), ("k_L2", k_pos_l2)]:
        if not pos:
            continue
        hist, _ = np.histogram(pos, bins=bins)
        total = sum(hist)
        pcts = [f"{h/total:.0%}" for h in hist]
        pr(f"  {label:6s}: {' | '.join(pcts)}")

    # ═══════════════════════════════════════════════════════════════════
    # TEST E: SEMANTIC RETEST (L2+ ONLY)
    # ═══════════════════════════════════════════════════════════════════
    pr()
    pr("=" * 72)
    pr("TEST E: SEMANTIC DOMAIN — Gallows section distribution on L2+ ONLY")
    pr("=" * 72)
    pr()
    pr("Phase 13 found t=celestial, k=generic, f=botanical, p=process.")
    pr("But if p/f are concentrated on L1 and L1 has different content,")
    pr("the semantic assignments might be positional artifacts.")
    pr("Retesting using ONLY L2+ gallows occurrences.")
    pr()

    # Count gallows by section on L2+ only
    section_gallows_l2 = defaultdict(Counter)
    section_total_l2 = Counter()
    for w, sec in l2_words:
        glyphs = eva_to_glyphs(w)
        gset = set(glyphs)
        for g in ['p', 't', 'k', 'f']:
            if g in gset:
                section_gallows_l2[g][sec] += 1
        section_total_l2[sec] += 1

    # Also on L1 for comparison
    section_gallows_l1 = defaultdict(Counter)
    section_total_l1 = Counter()
    for w, sec in l1_words:
        glyphs = eva_to_glyphs(w)
        gset = set(glyphs)
        for g in ['p', 't', 'k', 'f']:
            if g in gset:
                section_gallows_l1[g][sec] += 1
        section_total_l1[sec] += 1

    sections = ['herbal', 'recipe', 'balneo', 'cosmo', 'astro']

    pr("L2+ section enrichment (observed/expected ratio):")
    for g in ['p', 't', 'k', 'f']:
        total_g = sum(section_gallows_l2[g].values())
        total_w = sum(section_total_l2.values())
        if total_g == 0:
            pr(f"  {g}: no L2+ occurrences")
            continue
        parts = []
        for sec in sections:
            obs = section_gallows_l2[g].get(sec, 0)
            exp = total_g * section_total_l2.get(sec, 0) / total_w if total_w else 0
            ratio = obs / exp if exp > 0 else 0
            parts.append(f"{sec}={ratio:.2f}")
        pr(f"  {g}: {', '.join(parts)}")

    pr()
    pr("L1 section enrichment (for comparison):")
    for g in ['p', 't', 'k', 'f']:
        total_g = sum(section_gallows_l1[g].values())
        total_w = sum(section_total_l1.values())
        if total_g == 0:
            pr(f"  {g}: no L1 occurrences")
            continue
        parts = []
        for sec in sections:
            obs = section_gallows_l1[g].get(sec, 0)
            exp = total_g * section_total_l1.get(sec, 0) / total_w if total_w else 0
            ratio = obs / exp if exp > 0 else 0
            parts.append(f"{sec}={ratio:.2f}")
        pr(f"  {g}: {', '.join(parts)}")

    # ═══════════════════════════════════════════════════════════════════
    # TEST F: WORD-PAIR MATCHING (Edit Distance)
    # ═══════════════════════════════════════════════════════════════════
    pr()
    pr("=" * 72)
    pr("TEST F: WORD-PAIR MATCHING — Nearest L2+ neighbor for L1 p-words")
    pr("=" * 72)
    pr()
    pr("For each L1 word with p, find its closest L2+ word by glyph edit")
    pr("distance. Is the match typically a t-for-p substitution?")
    pr()

    def glyph_edit_distance(w1, w2):
        """Levenshtein distance at glyph level."""
        g1 = eva_to_glyphs(w1)
        g2 = eva_to_glyphs(w2)
        n, m = len(g1), len(g2)
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(n + 1):
            dp[i][0] = i
        for j in range(m + 1):
            dp[0][j] = j
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = 0 if g1[i-1] == g2[j-1] else 1
                dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
        return dp[n][m]

    # Sample L1 p-words (top 50 most frequent)
    l1_p_counter = Counter(l1_p_words)
    top_p_words = [w for w, _ in l1_p_counter.most_common(50)]

    # For each, find closest L2+ word
    l2_common = [w for w, c in l2_word_counter.most_common(2000)]  # search space

    pr(f"Matching top {len(top_p_words)} L1 p-words against {len(l2_common)} common L2+ words:")
    pr()

    edit_1_matches = 0
    t_for_p_matches = 0
    total_tested = 0

    for pw in top_p_words[:30]:  # limit for speed
        best_dist = 999
        best_match = ''
        for lw in l2_common:
            d = glyph_edit_distance(pw, lw)
            if d < best_dist:
                best_dist = d
                best_match = lw
            if d == 0:
                break
        # Check if the match is a p→t substitution
        t_substituted = substitute_glyph(pw, 'p', 't')
        is_pt_swap = (best_match == t_substituted)
        if best_dist <= 1:
            edit_1_matches += 1
        if is_pt_swap and best_dist <= 1:
            t_for_p_matches += 1
        total_tested += 1
        pr(f"  {pw:18s} → best: {best_match:18s} (dist={best_dist}) "
           f"{'[p→t MATCH]' if is_pt_swap else ''}")

    pr()
    pr(f"Edit distance ≤ 1: {edit_1_matches}/{total_tested}")
    pr(f"Of those, p→t substitution: {t_for_p_matches}/{edit_1_matches}")

    # Do same for f-words
    l1_f_counter = Counter(l1_f_words)
    top_f_words = [w for w, _ in l1_f_counter.most_common(30)]

    pr()
    pr(f"Matching top L1 f-words against L2+ vocabulary:")
    pr()

    f_edit_1 = 0
    fk_matches = 0
    f_tested = 0
    for fw in top_f_words[:20]:
        best_dist = 999
        best_match = ''
        for lw in l2_common:
            d = glyph_edit_distance(fw, lw)
            if d < best_dist:
                best_dist = d
                best_match = lw
            if d == 0:
                break
        k_substituted = substitute_glyph(fw, 'f', 'k')
        is_fk = (best_match == k_substituted)
        if best_dist <= 1:
            f_edit_1 += 1
        if is_fk and best_dist <= 1:
            fk_matches += 1
        f_tested += 1
        pr(f"  {fw:18s} → best: {best_match:18s} (dist={best_dist}) "
           f"{'[f→k MATCH]' if is_fk else ''}")

    pr()
    pr(f"Edit distance ≤ 1: {f_edit_1}/{f_tested}")
    pr(f"Of those, f→k substitution: {fk_matches}/{f_edit_1 if f_edit_1 else 1}")

    # ═══════════════════════════════════════════════════════════════════
    # SYNTHESIS
    # ═══════════════════════════════════════════════════════════════════
    pr()
    pr("=" * 72)
    pr("PHASE 78 SYNTHESIS")
    pr("=" * 72)
    pr()
    pr("Hypothesis scoreboard:")
    pr()
    pr("  H1 (ALLOGRAPH: p≡t, f≡k):")
    pr("    Test A (substitution): reported above")
    pr("    Test B (context JSD): reported above")
    pr("    Test D (slot position): reported above")
    pr("    Test F (nearest neighbor): reported above")
    pr()
    pr("  H2 (INDEPENDENT SYMBOLS):")
    pr("    Test E (semantic retest): reported above")
    pr()
    pr("  H3 (PREFIX/MARKER added to words):")
    pr("    Test A (deletion): reported above")
    pr("    Test C (position within word): reported above")
    pr()

    # Save results
    outpath = RESULTS_DIR / 'phase78_allograph_test.txt'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f"\nResults saved to {outpath}")

if __name__ == '__main__':
    main()
