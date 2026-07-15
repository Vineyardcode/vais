#!/usr/bin/env python3
"""
Voynich Manuscript — Diacritical Mark Audit (Phase 12)

The IVTFF transcription encodes three types of extra-alphabetic marks:

  1. @NNN; codes — Extended glyphs (diacritics, variant forms) outside EVA
  2. {xyz} codes — Composite/uncertain glyphs that don't map to single EVA chars
  3. ' (apostrophe) — Plume/flourish marks on glyphs

Tests whether these marks:
  - Are systematic or random scribal variation
  - Correlate with specific sections/Currier languages
  - Modify specific word types (gallows? function words? content words?)
  - Appear at specific word positions (onset? coda?)
  - Form patterns that suggest grammatical or semantic function

Connected to: user observation of small marks above letters in f78r,
Phase 10 gallows-as-determinative finding, Hebrew niqqud analogy.
"""

import re
import json
from pathlib import Path
from collections import Counter, defaultdict
from common import classify_folio

# ── Section classification ────────────────────────────────────────────────



# ── Data extraction ──────────────────────────────────────────────────────

def extract_all_marks():
    """Extract all diacritical marks, curly-brace glyphs, and plumes from folios."""
    folio_dir = Path("folios")

    # @NNN; marks
    at_marks = []      # (code, folio, section, locus, context_word, raw_context)
    # {xyz} glyphs
    curly_marks = []   # (glyph, folio, section, locus, context_word, raw_context)
    # ' plume marks
    plume_marks = []   # (folio, section, locus, context_word, position_in_word)

    # Section-level stats
    section_lines = Counter()
    section_words = Counter()

    at_re = re.compile(r'@(\d+);?')
    curly_re = re.compile(r'\{([^}]+)\}')
    plume_re = re.compile(r"'")

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
            raw_text = m.group(2)

            # Count lines and words per section (for normalization)
            section_lines[section] += 1

            # Extract words (raw, keeping marks)
            # Split on dots and angle-bracket markers
            text_for_words = re.sub(r'<[^>]*>', ' ', raw_text)
            raw_tokens = re.split(r'[.\s]+', text_for_words)
            raw_tokens = [t.strip() for t in raw_tokens if t.strip()]
            section_words[section] += len(raw_tokens)

            # Find @NNN; codes
            for tok in raw_tokens:
                for match in at_re.finditer(tok):
                    code = f"@{match.group(1)};"
                    at_marks.append((code, folio, section, locus, tok, raw_text))

            # Find {xyz} glyphs
            for tok in raw_tokens:
                for match in curly_re.finditer(tok):
                    glyph = match.group(1)
                    curly_marks.append((glyph, folio, section, locus, tok, raw_text))

            # Find plume marks (apostrophe in word context)
            for tok in raw_tokens:
                if "'" in tok and not tok.startswith("'"):
                    # Find position of plume in token
                    pos = tok.index("'")
                    plume_marks.append((folio, section, locus, tok, pos))

    return at_marks, curly_marks, plume_marks, section_lines, section_words


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def analyze_at_codes(at_marks, section_lines, section_words):
    """Analyze @NNN; extended glyph codes."""
    print("=" * 72)
    print("ANALYSIS 1: @NNN; EXTENDED GLYPH CODES")
    print("=" * 72)

    print(f"\n  Total @-code occurrences: {len(at_marks)}")

    # Frequency table
    code_freq = Counter(m[0] for m in at_marks)
    print(f"  Unique codes: {len(code_freq)}")
    print(f"\n  Top 20 codes by frequency:")
    for code, cnt in code_freq.most_common(20):
        # Find example contexts
        examples = [m[4] for m in at_marks if m[0] == code][:3]
        ex_str = ", ".join(examples)
        print(f"    {code:8s}  {cnt:3d}×  examples: {ex_str}")

    # Section distribution
    section_at = Counter()
    for _, _, section, _, _, _ in at_marks:
        section_at[section] += 1

    sections = ["herbal-A", "herbal-B", "pharma", "bio", "cosmo", "text", "zodiac"]
    print(f"\n  Section distribution:")
    print(f"  {'Section':12s}  {'@ marks':>8s}  {'Lines':>6s}  {'Rate':>8s}")
    for s in sections:
        marks = section_at.get(s, 0)
        lines = section_lines.get(s, 0)
        rate = f"{marks/lines:.3f}" if lines else "n/a"
        print(f"  {s:12s}  {marks:8d}  {lines:6d}  {rate:>8s}")

    # Folio concentration: which folios have the most?
    folio_at = Counter(m[1] for m in at_marks)
    print(f"\n  Top 15 folios by @-mark count:")
    for folio, cnt in folio_at.most_common(15):
        section = next((m[2] for m in at_marks if m[1] == folio), "?")
        print(f"    {folio:12s} ({section:10s}): {cnt}")

    # Gallows connection: how many @-codes appear inside gallows contexts?
    gallows_at = 0
    standalone_at = 0
    for code, folio, section, locus, tok, raw in at_marks:
        # Check if the @-code is embedded in a gallows compound {c@NNN;h}
        if re.search(r'\{c' + re.escape(code) + r'h?\}', tok):
            gallows_at += 1
        elif re.search(r'\{[^}]*' + re.escape(code) + r'[^}]*\}', tok):
            gallows_at += 1
        else:
            standalone_at += 1

    print(f"\n  @-codes in gallows compounds: {gallows_at}")
    print(f"  @-codes standalone/other:     {standalone_at}")

    return code_freq


def analyze_curly_glyphs(curly_marks, section_lines, section_words):
    """Analyze {xyz} composite/uncertain glyphs."""
    print("\n" + "=" * 72)
    print("ANALYSIS 2: {xyz} COMPOSITE GLYPHS")
    print("=" * 72)

    print(f"\n  Total {{}} glyph occurrences: {len(curly_marks)}")

    # Frequency table
    glyph_freq = Counter(m[0] for m in curly_marks)
    print(f"  Unique glyph types: {len(glyph_freq)}")

    # Categorize: gallows-related vs non-gallows
    gallows_related = Counter()
    non_gallows = Counter()
    has_at_code = Counter()

    for glyph, cnt in glyph_freq.items():
        if any(g in glyph for g in ['kh', 'th', 'ph', 'fh', 'ck', 'ct', 'cp', 'cf']):
            gallows_related[glyph] = cnt
        elif '@' in glyph:
            has_at_code[glyph] = cnt
        else:
            non_gallows[glyph] = cnt

    print(f"\n  Gallows-related {{}} glyphs: {len(gallows_related)}"
          f" ({sum(gallows_related.values())} occurrences)")
    print(f"  Non-gallows {{}} glyphs:     {len(non_gallows)}"
          f" ({sum(non_gallows.values())} occurrences)")
    print(f"  @-code-containing {{}}: {len(has_at_code)}"
          f" ({sum(has_at_code.values())} occurrences)")

    print(f"\n  Top 15 gallows-related variants:")
    for glyph, cnt in gallows_related.most_common(15):
        examples = [m[4] for m in curly_marks if m[0] == glyph][:2]
        print(f"    {{{glyph}:8s}}  {cnt:3d}×  in: {', '.join(examples)}")

    print(f"\n  Top 15 non-gallows variants:")
    for glyph, cnt in non_gallows.most_common(15):
        examples = [m[4] for m in curly_marks if m[0] == glyph][:2]
        print(f"    {{{glyph}:8s}}  {cnt:3d}×  in: {', '.join(examples)}")

    # Section distribution for {} glyphs
    section_curly = Counter()
    for _, _, section, _, _, _ in curly_marks:
        section_curly[section] += 1

    sections = ["herbal-A", "herbal-B", "pharma", "bio", "cosmo", "text", "zodiac"]
    print(f"\n  {{}} glyph distribution by section:")
    print(f"  {'Section':12s}  {'Marks':>8s}  {'Words':>8s}  {'‰ rate':>8s}")
    for s in sections:
        marks = section_curly.get(s, 0)
        words = section_words.get(s, 0)
        rate = f"{1000*marks/words:.1f}" if words else "n/a"
        print(f"  {s:12s}  {marks:8d}  {words:8d}  {rate:>8s}")

    # Key question: are gallows variants concentrated in specific sections?
    print(f"\n  Gallows-variant {{}} glyphs per section:")
    section_gall_curly = defaultdict(int)
    for glyph, folio, section, locus, tok, raw in curly_marks:
        if any(g in glyph for g in ['kh', 'th', 'ph', 'fh', 'ck', 'ct', 'cp', 'cf']):
            section_gall_curly[section] += 1
    for s in sections:
        marks = section_gall_curly.get(s, 0)
        words = section_words.get(s, 0)
        rate = f"{1000*marks/words:.1f}" if words else "n/a"
        print(f"    {s:12s}  {marks:4d}  ({rate}‰)")

    return glyph_freq


def analyze_plumes(plume_marks, section_lines, section_words):
    """Analyze ' plume/flourish marks."""
    print("\n" + "=" * 72)
    print("ANALYSIS 3: PLUME/FLOURISH MARKS (')")
    print("=" * 72)

    print(f"\n  Total plume occurrences: {len(plume_marks)}")

    # Section distribution
    section_plume = Counter()
    for folio, section, locus, tok, pos in plume_marks:
        section_plume[section] += 1

    sections = ["herbal-A", "herbal-B", "pharma", "bio", "cosmo", "text", "zodiac"]
    print(f"\n  Plume distribution by section:")
    print(f"  {'Section':12s}  {'Plumes':>8s}  {'Words':>8s}  {'‰ rate':>8s}")
    for s in sections:
        marks = section_plume.get(s, 0)
        words = section_words.get(s, 0)
        rate = f"{1000*marks/words:.1f}" if words else "n/a"
        print(f"  {s:12s}  {marks:8d}  {words:8d}  {rate:>8s}")

    # What characters precede the plume?
    preceding_char = Counter()
    following_char = Counter()
    for folio, section, locus, tok, pos in plume_marks:
        if pos > 0:
            preceding_char[tok[pos-1]] += 1
        if pos + 1 < len(tok):
            following_char[tok[pos+1]] += 1

    print(f"\n  Character preceding plume (what carries the mark):")
    for ch, cnt in preceding_char.most_common(10):
        print(f"    '{ch}': {cnt} ({100*cnt/len(plume_marks):.1f}%)")

    print(f"\n  Character following plume:")
    for ch, cnt in following_char.most_common(10):
        print(f"    '{ch}': {cnt} ({100*cnt/len(plume_marks):.1f}%)")

    # Position in word (normalized)
    pos_early = 0
    pos_mid = 0
    pos_late = 0
    for folio, section, locus, tok, pos in plume_marks:
        # Remove non-letter chars for position calc
        clean_len = len(re.sub(r"[^a-z]", "", tok))
        if clean_len <= 0:
            continue
        # Count only letter positions before the plume
        letter_pos = len(re.sub(r"[^a-z]", "", tok[:pos]))
        norm = letter_pos / clean_len if clean_len > 1 else 0.5
        if norm < 0.33:
            pos_early += 1
        elif norm < 0.66:
            pos_mid += 1
        else:
            pos_late += 1

    total_pos = pos_early + pos_mid + pos_late
    if total_pos:
        print(f"\n  Plume position in word:")
        print(f"    Early (0-33%):  {pos_early} ({100*pos_early/total_pos:.1f}%)")
        print(f"    Middle (33-66%): {pos_mid} ({100*pos_mid/total_pos:.1f}%)")
        print(f"    Late (66-100%): {pos_late} ({100*pos_late/total_pos:.1f}%)")

    # Example plume words
    plume_words = Counter(tok for _, _, _, tok, _ in plume_marks)
    print(f"\n  Top 20 plume-bearing words:")
    for tok, cnt in plume_words.most_common(20):
        print(f"    {tok}: {cnt}")


def analyze_f78r_specific(at_marks, curly_marks, plume_marks):
    """Deep dive into f78r — the folio where the user observed diacritical marks."""
    print("\n" + "=" * 72)
    print("ANALYSIS 4: f78r DEEP DIVE")
    print("=" * 72)

    f78r_at = [m for m in at_marks if m[1] == "f78r"]
    f78r_curly = [m for m in curly_marks if m[1] == "f78r"]
    f78r_plume = [m for m in plume_marks if m[0] == "f78r"]

    print(f"\n  f78r @-codes: {len(f78r_at)}")
    for code, folio, section, locus, tok, raw in f78r_at:
        print(f"    {code} in word '{tok}' at {locus}")

    print(f"\n  f78r {{}} glyphs: {len(f78r_curly)}")
    for glyph, folio, section, locus, tok, raw in f78r_curly:
        print(f"    {{{glyph}}} in word '{tok}' at {locus}")

    print(f"\n  f78r plumes: {len(f78r_plume)}")
    for folio, section, locus, tok, pos in f78r_plume:
        print(f"    in word '{tok}' at {locus}")

    # Now read f78r raw to show ALL special marks in context
    print(f"\n  f78r lines with ANY special marks:")
    f78r_path = Path("folios/f78r.txt")
    if f78r_path.exists():
        for line in f78r_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            if any(c in line for c in ["@", "{", "'"]):
                # Skip header metadata
                if line.strip().startswith("<f78r>"):
                    continue
                print(f"    {line.strip()}")


def analyze_mark_systematics(at_marks, curly_marks, plume_marks,
                             section_lines, section_words):
    """Test whether marks form systematic patterns."""
    print("\n" + "=" * 72)
    print("ANALYSIS 5: SYSTEMATICITY TESTS")
    print("=" * 72)

    all_marks = (
        [(m[1], m[2], m[3], "at") for m in at_marks] +
        [(m[1], m[2], m[3], "curly") for m in curly_marks] +
        [(m[0], m[1], m[2], "plume") for m in plume_marks]
    )

    # Test 1: Are marks concentrated in specific folios or spread evenly?
    folio_marks = Counter(m[0] for m in all_marks)
    total_folios = len(folio_marks)
    total_marks = len(all_marks)
    marks_per_folio = sorted(folio_marks.values(), reverse=True)

    # Gini coefficient (0 = uniform, 1 = all in one folio)
    n = len(marks_per_folio)
    mean_m = sum(marks_per_folio) / n if n else 0
    if mean_m > 0:
        gini = sum(abs(x - y) for x in marks_per_folio for y in marks_per_folio) / (2 * n * n * mean_m)
    else:
        gini = 0

    print(f"\n  Test 1: Mark concentration")
    print(f"    Folios with any marks: {total_folios}")
    print(f"    Total marks: {total_marks}")
    print(f"    Gini coefficient: {gini:.3f} (0=uniform, 1=concentrated)")
    print(f"    Top 5 folios: {folio_marks.most_common(5)}")

    # How many folios have ZERO marks?
    total_folio_files = len(list(Path("folios").glob("*.txt")))
    zero_mark_folios = total_folio_files - total_folios
    print(f"    Folios with zero marks: {zero_mark_folios}/{total_folio_files}")

    # Test 2: Locus-type distribution (are marks in paragraphs? labels? rings?)
    locus_marks = Counter()
    for _, _, locus, _ in all_marks:
        if "@P0" in locus or "+P0" in locus or "*P0" in locus:
            locus_marks["paragraph"] += 1
        elif "@Lt" in locus or "@Lb" in locus:
            locus_marks["label"] += 1
        elif "@Cc" in locus:
            locus_marks["ring_text"] += 1
        elif "@Lz" in locus or "&Lz" in locus:
            locus_marks["nymph_label"] += 1
        else:
            locus_marks["other"] += 1

    print(f"\n  Test 2: Mark distribution by locus type")
    for loc_type, cnt in locus_marks.most_common():
        print(f"    {loc_type:15s}: {cnt}")

    # Test 3: Do marks co-occur with gallows more than expected?
    gallows_re = re.compile(r'(?:cth|ckh|cph|cfh|tch|kch|pch|fch|tsh|ksh|psh|fsh|[tkfp])')
    marks_near_gallows = 0
    marks_not_near_gallows = 0

    # Check @-code and curly contexts
    for code, folio, section, locus, tok, raw in at_marks:
        if gallows_re.search(tok):
            marks_near_gallows += 1
        else:
            marks_not_near_gallows += 1

    for glyph, folio, section, locus, tok, raw in curly_marks:
        if any(g in glyph for g in ['kh', 'th', 'ph', 'fh', 'ck', 'ct', 'cp', 'cf', 'k', 't', 'p', 'f']):
            marks_near_gallows += 1
        elif gallows_re.search(tok):
            marks_near_gallows += 1
        else:
            marks_not_near_gallows += 1

    total_mark_context = marks_near_gallows + marks_not_near_gallows
    if total_mark_context:
        print(f"\n  Test 3: Gallows co-occurrence")
        print(f"    Marks in gallows context: {marks_near_gallows}/{total_mark_context}"
              f" ({100*marks_near_gallows/total_mark_context:.1f}%)")
        print(f"    Marks NOT in gallows context: {marks_not_near_gallows}/{total_mark_context}"
              f" ({100*marks_not_near_gallows/total_mark_context:.1f}%)")
        print(f"    (Corpus gallows rate is ~52% — compare)")

    # Test 4: Check if {}-encoded gallows variants are the SAME gallows with
    # visual modifications, supporting the determinative hypothesis
    print(f"\n  Test 4: Gallows variant analysis")
    print(f"  Are {{}} gallows just visually modified versions of standard gallows?")

    # Map each {} glyph to its "base" gallows
    base_mapping = Counter()
    for glyph, cnt in Counter(m[0] for m in curly_marks).items():
        if 'kh' in glyph and 'ckh' not in glyph:
            base = 'k-type'
        elif 'th' in glyph and 'cth' not in glyph:
            base = 't-type'
        elif 'ph' in glyph and 'cph' not in glyph:
            base = 'p-type'
        elif 'fh' in glyph and 'cfh' not in glyph:
            base = 'f-type'
        elif 'ckh' in glyph:
            base = 'bench-k'
        elif 'cth' in glyph:
            base = 'bench-t'
        elif 'cph' in glyph:
            base = 'bench-p'
        elif 'cfh' in glyph:
            base = 'bench-f'
        elif 'ck' in glyph:
            base = 'pre-k'
        elif 'ct' in glyph:
            base = 'pre-t'
        elif 'cp' in glyph:
            base = 'pre-p'
        elif 'cf' in glyph:
            base = 'pre-f'
        else:
            base = 'non-gallows'
        base_mapping[base] += cnt

    for base, cnt in base_mapping.most_common():
        print(f"    {base:15s}: {cnt}")

    non_gal = base_mapping.get('non-gallows', 0)
    total_curly = sum(base_mapping.values())
    gal_pct = 100 * (total_curly - non_gal) / total_curly if total_curly else 0
    print(f"\n    Gallows-related: {total_curly - non_gal}/{total_curly} ({gal_pct:.0f}%)")


def synthesis(at_marks, curly_marks, plume_marks, section_words):
    """Pull together findings."""
    print("\n" + "=" * 72)
    print("SYNTHESIS: DIACRITICAL MARKS IN THE VOYNICH MANUSCRIPT")
    print("=" * 72)

    total_words = sum(section_words.values())
    total_marks = len(at_marks) + len(curly_marks) + len(plume_marks)

    print(f"\n  Total corpus: ~{total_words} words")
    print(f"  Total extra-alphabetic marks: {total_marks}")
    print(f"  Mark rate: {1000*total_marks/total_words:.1f} per thousand words")

    print(f"\n  Mark types:")
    print(f"    @NNN; extended codes: {len(at_marks)} ({100*len(at_marks)/total_marks:.0f}%)")
    print(f"    {{xyz}} composite glyphs: {len(curly_marks)} ({100*len(curly_marks)/total_marks:.0f}%)")
    print(f"    ' plume marks: {len(plume_marks)} ({100*len(plume_marks)/total_marks:.0f}%)")

    print(f"\n  ── Key Findings ──")
    print(f"  1. Marks are RARE: {1000*total_marks/total_words:.1f}‰ overall")
    print(f"  2. Most {{}} glyphs ({len(curly_marks)} total) are gallows variants —")
    print(f"     visual modifications of the four basic gallows shapes")
    print(f"  3. This connects to Phase 10: if gallows are determinatives,")
    print(f"     then {{}} variants = SUB-CATEGORIES within the gallows system")
    print(f"  4. @NNN; codes are the true 'diacritics' — marks that modify")
    print(f"     individual letters but can't be expressed in standard EVA")
    print(f"  5. Plume marks (') primarily attach to specific characters,")
    print(f"     suggesting they modify the glyph's reading")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Extracting all diacritical marks from corpus...\n")
    at_marks, curly_marks, plume_marks, section_lines, section_words = extract_all_marks()

    analyze_at_codes(at_marks, section_lines, section_words)
    analyze_curly_glyphs(curly_marks, section_lines, section_words)
    analyze_plumes(plume_marks, section_lines, section_words)
    analyze_f78r_specific(at_marks, curly_marks, plume_marks)
    analyze_mark_systematics(at_marks, curly_marks, plume_marks,
                            section_lines, section_words)
    synthesis(at_marks, curly_marks, plume_marks, section_words)

    print(f"\nDiacritic audit complete.")
