#!/usr/bin/env python3
"""
Abbreviation Decode Attempt on f1r

Applies JKP's paleographic glyph identifications (thread 2394) and
Cappelli abbreviation mappings to EVA-transcribed f1r text to see
if anything recognizable emerges.

Approach:
  1. Extract clean word tokens from f1r EVA transcription
  2. Apply positional substitution rules (JKP + Cappelli + Pelling)
  3. Show raw substitution output
  4. Try multiple language hypotheses (Latin, Italian)
"""
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
FOLIO = ROOT / "folios" / "f1r.txt"
RESULTS = ROOT / "results" / "f1r_abbreviation_decode.txt"

# ── Extract tokens from folio ──────────────────────────────────────
def extract_tokens(path):
    """Extract EVA word tokens from a folio file, preserving line info."""
    lines = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            # Match folio line markers like <f1r.1,@P0>
            m = re.match(r"<(f\d+[rv]\.\d+),", raw)
            if not m:
                continue
            line_id = m.group(1)
            # Strip the line marker and trailing markers
            text = re.sub(r"<[^>]*>", "", raw).strip()
            # Remove comment-style annotations
            text = re.sub(r"<!.*?>", "", text)
            text = re.sub(r"<%>", "", text)
            text = re.sub(r"<\$>", "", text)
            # Remove uncertain reading brackets but keep content
            text = re.sub(r"\{[^}]*\}", lambda m: m.group(0)[1:-1], text)
            text = re.sub(r"\[([^:\]]+):([^\]]+)\]", r"\1", text)  # keep first variant
            text = re.sub(r"\?", "", text)  # remove uncertainty markers
            text = re.sub(r"@\d+;?", "", text)  # remove reference markers
            # Split on dots and commas (word separators in EVA)
            words = re.split(r"[.,]+", text)
            words = [w.strip() for w in words if w.strip()]
            lines.append((line_id, words))
    return lines


# ── JKP/Cappelli Substitution Rules ──────────────────────────────────
# Based on thread 2394 identifications + Cappelli standard marks
# These are POSITIONAL — the same EVA glyph may map differently
# depending on where it appears in the word.

# Strategy: process each word, applying rules based on position

def decode_word_latin(eva_word):
    """
    Attempt to decode an EVA word into abbreviated Latin using JKP mappings.
    Returns a string with substitutions applied.
    
    Key mappings (JKP thread 2394 + Cappelli + Pelling):
    
    WORD-FINAL:
      y  → -us (most common Latin abbreviation mark; also -um, -os)
      m  → -ris (straight) / -tis (with tail) / -cis (rounded)
           EVA can't distinguish the 3, so we use -ris as default
      s  → -er (c/e with tail → common ending abbreviation)
      n  → -n (nasal bar → -m/-n abbreviation; keep as -n)
      r  → -rum / -tur (2-sign → common for genitive plural)
      l  → -l (numeral 4 shape → keep literal)
      d  → -d (keep literal)
      
    WORD-INITIAL:
      y  → con- / com- (9-sign at word start)
      k  → I (Item = I + -is; at line-initial also "Item")
      q  → q (Latin q, usually followed by u)
      s  → s (keep literal)
      d  → d (keep literal)
      
    GALLOWS (constructed — speculative):
      k  → I/-is (simplest gallows)
      t  → t (variant of k with left loop → possibly -ter/-tis)  
      p  → p (Greek Pi origin? → per-/pro-)
      f  → f (variant of p → possibly far-/for-)
      
    DIGRAPHS / BENCHES:
      ch → ch (cr/ct ligature → keep as digraph for now)
      sh → sh (similar ligature family)
      cth → cth (triple ligature → possibly combination)
      
    MIDDLE CHARACTERS:
      o  → o (the "o problem" — possibly null/separator/vowel)
      a  → a (vowel — possibly genuine)
      e  → e (vowel — possibly genuine)
      i  → i (vowel or stroke)
      ii → ii (double stroke)
      
    We'll try multiple interpretations for ambiguous glyphs.
    """
    if not eva_word:
        return ""
    
    # First, parse the EVA word into a glyph sequence
    glyphs = parse_eva_glyphs(eva_word)
    if not glyphs:
        return eva_word
    
    result = []
    for idx, g in enumerate(glyphs):
        is_first = (idx == 0)
        is_last = (idx == len(glyphs) - 1)
        
        # Apply positional rules
        if is_last:  # WORD-FINAL position
            sub = FINAL_MAP.get(g, g)
        elif is_first:  # WORD-INITIAL position
            sub = INITIAL_MAP.get(g, g)
        else:  # MEDIAL position
            sub = MEDIAL_MAP.get(g, g)
        
        result.append(sub)
    
    return "".join(result)


def parse_eva_glyphs(word):
    """Parse EVA word into ordered glyph sequence, handling digraphs."""
    glyphs = []
    i = 0
    while i < len(word):
        # Try 4-char sequences first
        if i + 3 < len(word) and word[i:i+4] in KNOWN_GLYPHS:
            glyphs.append(word[i:i+4])
            i += 4
        # Try 3-char sequences (cth, cfh, cph, ckh)
        elif i + 2 < len(word) and word[i:i+3] in KNOWN_GLYPHS:
            glyphs.append(word[i:i+3])
            i += 3
        # Try 2-char sequences (ch, sh, qo, ai, etc.)
        elif i + 1 < len(word) and word[i:i+2] in KNOWN_GLYPHS:
            glyphs.append(word[i:i+2])
            i += 2
        # Single character
        else:
            glyphs.append(word[i])
            i += 1
    return glyphs


# Glyph inventory for parsing (order matters — longer first)
KNOWN_GLYPHS = {
    # 4-char
    "aiin", "oiin", "eiin",
    # 3-char  
    "cth", "cfh", "cph", "ckh", "sch", "ain", "iin",
    # 2-char
    "ch", "sh", "qo", "ai", "ee", "oi", "dy", "ey",
    "ar", "or", "al", "ol", "an", "in", "am",
    # 1-char
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "k", 
    "l", "m", "n", "o", "p", "q", "r", "s", "t", "x", "y",
}

# ── Positional substitution maps ──────────────────────────────────

# Word-final position (JKP's strongest identifications)
FINAL_MAP = {
    "y":    "us",     # 9-sign → -us/-um (most common)
    "dy":   "dus",    # d + -us
    "ey":   "eus",    # e + -us  
    "m":    "ris",    # loop+tail → -ris/-tis/-cis
    "am":   "aris",   # a + -ris
    "s":    "er",     # c/e-tail → -er/-eur
    "r":    "rum",    # 2-sign → -rum/-tur
    "ar":   "arum",   # a + -rum
    "or":   "orum",   # o + -rum
    "n":    "n",      # nasal bar → -n/-m
    "an":   "an",     # a + -n
    "in":   "in",     # i + -n
    "ain":  "ain",    # keep
    "aiin": "aium",   # ai + -um (speculative)
    "iin":  "ium",    # ii + -um
    "al":   "al",     # keep
    "ol":   "ol",     # keep
    "l":    "l",      # numeral 4
    "d":    "d",      # keep
    "ch":   "ch",     # bench → ligature
    "ey":   "eus",    # e + -us
}

# Word-initial position
INITIAL_MAP = {
    "y":    "con",    # 9-sign word-initial → con-/com-
    "k":    "I",      # Item = I + -is
    "t":    "t",      # gallows → t 
    "p":    "per",    # Greek Pi → per-/pro-
    "f":    "far",    # variant p → far-/for-
    "qo":   "quo",    # q + o → quo-/qua- (Pelling: qo = "lo" = Italian "the")
    "s":    "s",      # keep
    "d":    "d",      # keep
    "ch":   "ch",     # bench
    "sh":   "sh",     # bench variant
    "cth":  "cth",    # triple ligature
    "cph":  "cph",    # gallows bench
    "cfh":  "cfh",    # gallows bench
    "ckh":  "ckh",    # gallows bench
    "o":    "o",      # the o-problem
    "a":    "a",      # vowel
    "e":    "e",      # vowel
}

# Medial position (least certain)
MEDIAL_MAP = {
    "o":    "o",      # possibly null/separator — keep for now
    "a":    "a",
    "e":    "e",
    "i":    "i",
    "ii":   "ii",
    "ai":   "ai",
    "ee":   "ee",
    "ch":   "ch",
    "sh":   "sh",
    "cth":  "cth",
    "k":    "I",      # gallows medial — possibly I/-is
    "t":    "t",
    "p":    "per",
    "f":    "far",
    "d":    "d",
    "y":    "us",     # 9-sign medial (rare)
    "r":    "r",
    "l":    "l",
    "n":    "n",
    "s":    "s",
    "ar":   "ar",
    "or":   "or",
    "al":   "al",
    "ol":   "ol",
    "an":   "an",
    "in":   "in",
    "am":   "am",
    "oin":  "oin",
    "ain":  "ain",
    "aiin": "aium",
    "iin":  "ium",
    "qo":   "quo",
}


# ── Alternative decode: Pelling's "qo = lo" (Italian article) ─────

def decode_word_italian(eva_word):
    """Same as Latin but with qo→lo (Italian 'the') per Pelling."""
    if not eva_word:
        return ""
    glyphs = parse_eva_glyphs(eva_word)
    if not glyphs:
        return eva_word
    
    result = []
    for idx, g in enumerate(glyphs):
        is_first = (idx == 0)
        is_last = (idx == len(glyphs) - 1)
        
        if is_last:
            sub = FINAL_MAP.get(g, g)
        elif is_first:
            sub = INITIAL_IT_MAP.get(g, INITIAL_MAP.get(g, g))
        else:
            sub = MEDIAL_IT_MAP.get(g, MEDIAL_MAP.get(g, g))
        
        result.append(sub)
    
    return "".join(result)


INITIAL_IT_MAP = {
    "qo":  "lo",     # Pelling: qo = "lo" (Italian definite article)
    "y":   "con",    # same as Latin
    "k":   "I",
}

MEDIAL_IT_MAP = {
    "qo":  "lo",
}


# ── Alternative: "o" as null/separator ────────────────────────────

def decode_word_o_null(eva_word):
    """Treat EVA-o as null (separator/space filler)."""
    if not eva_word:
        return ""
    glyphs = parse_eva_glyphs(eva_word)
    if not glyphs:
        return eva_word
    
    result = []
    for idx, g in enumerate(glyphs):
        is_first = (idx == 0)
        is_last = (idx == len(glyphs) - 1)
        
        if g == "o":
            continue  # skip o entirely
        
        if is_last:
            sub = FINAL_MAP.get(g, g)
        elif is_first:
            sub = INITIAL_MAP.get(g, g)
        else:
            sub = MEDIAL_MAP.get(g, g)
        
        result.append(sub)
    
    return "".join(result)


# ── Run all decodings ──────────────────────────────────────────────

def main():
    lines = extract_tokens(FOLIO)
    
    out = []
    out.append("=" * 80)
    out.append("f1r_abbreviation_decode — ABBREVIATION DECODE ATTEMPT ON FOLIO 1r")
    out.append("=" * 80)
    out.append("")
    out.append("Method: Apply JKP paleographic identifications (thread 2394)")
    out.append("and Cappelli abbreviation mappings positionally to EVA tokens.")
    out.append("")
    out.append("Mappings used:")
    out.append("  FINAL: y→-us, m→-ris, s→-er, r→-rum, aiin→-aium, iin→-ium")
    out.append("  INITIAL: y→con-, k→I, p→per-, f→far-, qo→quo-/lo-")  
    out.append("  MEDIAL: o→o (kept), a→a, e→e, ch→ch, sh→sh")
    out.append("  GALLOWS: k→I, t→t, p→per, f→far")
    out.append("")
    
    # ── Decode A: Latin abbreviation (direct) ──
    out.append("─" * 80)
    out.append("DECODE A: Latin Abbreviation (JKP + Cappelli)")
    out.append("─" * 80)
    out.append("")
    
    all_latin = []
    for line_id, words in lines:
        eva_str = " ".join(words)
        decoded = [decode_word_latin(w) for w in words]
        dec_str = " ".join(decoded)
        out.append(f"  {line_id}")
        out.append(f"    EVA:  {eva_str}")
        out.append(f"    LAT:  {dec_str}")
        out.append("")
        all_latin.extend(decoded)
    
    # ── Decode B: Italian (qo = lo) ──
    out.append("─" * 80)
    out.append("DECODE B: Italian Hypothesis (qo→lo per Pelling)")
    out.append("─" * 80)
    out.append("")
    
    all_italian = []
    for line_id, words in lines:
        eva_str = " ".join(words)
        decoded = [decode_word_italian(w) for w in words]
        dec_str = " ".join(decoded)
        out.append(f"  {line_id}")
        out.append(f"    EVA:  {eva_str}")
        out.append(f"    ITA:  {dec_str}")
        out.append("")
        all_italian.extend(decoded)
    
    # ── Decode C: o-as-null ──
    out.append("─" * 80)
    out.append("DECODE C: Latin + o-as-null (EVA-o removed)")
    out.append("─" * 80)
    out.append("")
    
    all_onull = []
    for line_id, words in lines:
        eva_str = " ".join(words)
        decoded = [decode_word_o_null(w) for w in words]
        dec_str = " ".join(decoded)
        out.append(f"  {line_id}")
        out.append(f"    EVA:  {eva_str}")
        out.append(f"    NUL:  {dec_str}")
        out.append("")
        all_onull.extend(decoded)
    
    # ── Frequency analysis of decoded tokens ──
    out.append("─" * 80)
    out.append("FREQUENCY ANALYSIS OF DECODED TOKENS")
    out.append("─" * 80)
    out.append("")
    
    for label, tokens in [("Latin", all_latin), ("Italian", all_italian), ("o-null", all_onull)]:
        ctr = Counter(tokens)
        out.append(f"  {label} — top 30 decoded tokens:")
        for tok, cnt in ctr.most_common(30):
            out.append(f"    {tok:20s}  {cnt:3d}")
        out.append("")
    
    # ── Look for recognizable Latin/Italian words ──
    out.append("─" * 80)
    out.append("RECOGNIZABLE WORD SCAN")
    out.append("─" * 80)
    out.append("")
    
    # Common Latin words that might emerge
    latin_words = {
        "et", "in", "de", "est", "ad", "per", "cum", "non", "sed",
        "que", "qui", "quod", "ius", "ius", "res", "orum", "arum",
        "ius", "us", "um", "er", "is", "it", "at", "ut",
        "oleum", "aqua", "herba", "radix", "folia", "semen",
        "contra", "pro", "item", "id", "hoc", "hic", "ille",
        "dus", "tus", "ris", "rum", "mus", "nus", "rus", "lus",
        "con", "com", "dis", "ter", "tur", "tis", "cis",
        "dal", "sol", "sal", "mal", "cor", "dor",
    }
    
    italian_words = {
        "il", "lo", "la", "le", "li", "di", "del", "della",
        "con", "per", "che", "chi", "come", "olio", "acqua",
        "erba", "radice", "foglia", "seme", "sale", "sol",
        "dar", "far", "cor",
    }
    
    out.append("  Latin matches in Decode A:")
    lat_matches = [(w, t) for w, t in zip([w for _, ws in lines for w in ws], all_latin) 
                   if t.lower() in latin_words]
    for eva, dec in lat_matches:
        out.append(f"    {eva:20s} → {dec}")
    
    out.append("")
    out.append("  Italian matches in Decode B:")
    ita_matches = [(w, t) for w, t in zip([w for _, ws in lines for w in ws], all_italian) 
                   if t.lower() in italian_words]
    for eva, dec in ita_matches:
        out.append(f"    {eva:20s} → {dec}")
    
    out.append("")
    out.append("  Latin matches in Decode C (o-null):")
    nul_matches = [(w, t) for w, t in zip([w for _, ws in lines for w in ws], all_onull) 
                   if t.lower() in latin_words]
    for eva, dec in nul_matches:
        out.append(f"    {eva:20s} → {dec}")
    
    # ── Assessment ──
    out.append("")
    out.append("─" * 80)
    out.append("ASSESSMENT")
    out.append("─" * 80)
    out.append("")
    out.append("This is a MECHANICAL substitution — it applies JKP's glyph")
    out.append("identifications as if they were a simple cipher key. This is")
    out.append("almost certainly an oversimplification because:")
    out.append("  1. The same EVA glyph may represent different abbreviations")
    out.append("     depending on context (e.g., EVA-y = -us/-um/-os/-con)")
    out.append("  2. Gallows are composite constructions, not single letters")
    out.append("  3. EVA character boundaries may be wrong (composite glyphs)")
    out.append("  4. There may be additional encoding layers (verbose cipher,")
    out.append("     alphabet substitution) on top of the abbreviation")
    out.append("  5. We don't know the underlying language")
    out.append("")
    out.append("The purpose is to see if ANY recognizable patterns emerge,")
    out.append("not to produce a translation.")
    
    result_text = "\n".join(out)
    print(result_text)
    
    RESULTS.parent.mkdir(exist_ok=True)
    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write(result_text)
    print(f"\nResults saved to {RESULTS}")


if __name__ == "__main__":
    main()
