#!/usr/bin/env python3
"""
Phase 106b — Aggressive bench substitution variants on f1r

Try substituting ch/sh benches with JKP's ligature candidates
to see if any combination produces recognizable text.
"""
import re
from pathlib import Path
from itertools import product

ROOT = Path(__file__).resolve().parent.parent
FOLIO = ROOT / "folios" / "f1r.txt"
RESULTS = ROOT / "results" / "phase106b_bench_variants.txt"

def extract_words(path):
    words = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            m = re.match(r"<f\d+[rv]\.\d+", raw)
            if not m: continue
            text = re.sub(r"<[^>]*>|<!.*?>|<%>|<\$>", "", raw).strip()
            text = re.sub(r"\{[^}]*\}", lambda m: m.group(0)[1:-1], text)
            text = re.sub(r"\[([^:\]]+):([^\]]+)\]", r"\1", text)
            text = re.sub(r"\?|@\d+;?", "", text)
            for w in re.split(r"[.,]+", text):
                w = w.strip()
                if w: words.append(w)
    return words

# JKP bench candidates
CH_OPTIONS = ["cr", "ct", "er", "ee", "cc"]
SH_OPTIONS = ["se", "sr", "sc", "ce", "ss"]

# Cappelli positional rules (same as phase106)
def apply_endings(word):
    """Apply word-final abbreviation marks."""
    # Try longest suffixes first
    endings = [
        ("aiin", "aium"), ("oiin", "oium"), ("eiin", "eium"),
        ("ain", "ain"), ("iin", "ium"), ("dy", "dus"), ("ey", "eus"),
        ("am", "aris"), ("ar", "arum"), ("or", "orum"), ("al", "al"),
        ("ol", "ol"), ("an", "an"), ("in", "in"),
        ("y", "us"), ("m", "ris"), ("s", "er"), ("r", "rum"),
    ]
    for eva_end, lat_end in endings:
        if word.endswith(eva_end) and len(word) > len(eva_end):
            return word[:-len(eva_end)] + lat_end
    return word

def apply_beginnings(word):
    """Apply word-initial substitutions."""
    beginnings = [
        ("cth", "ct"), ("cph", "cp"), ("cfh", "cf"), ("ckh", "ck"),
        ("qo", "quo"),
        ("y", "con"), ("k", "I"), ("p", "per"), ("f", "far"),
    ]
    for eva_beg, lat_beg in beginnings:
        if word.startswith(eva_beg) and len(word) > len(eva_beg):
            return lat_beg + word[len(eva_beg):]
    return word

def substitute_benches(word, ch_sub, sh_sub):
    """Replace ch→X and sh→Y throughout."""
    # Must replace longer sequences first to avoid partial matches
    # cth = c + th? or ct + h? — treat as bench-gallows
    word = word.replace("cth", "ct" + ch_sub[1] if len(ch_sub) > 1 else "cth")
    word = word.replace("sch", sh_sub + ch_sub[1] if len(ch_sub) > 1 else "sch")
    word = word.replace("sh", sh_sub)
    word = word.replace("ch", ch_sub)
    return word

def decode_full(eva_word, ch_sub, sh_sub):
    """Full pipeline: benches → beginnings → endings."""
    w = substitute_benches(eva_word, ch_sub, sh_sub)
    w = apply_beginnings(w)
    w = apply_endings(w)
    return w

# Common Latin pharmaceutical/herbal words to scan for
LATIN_PHARMA = {
    "aqua", "oleum", "herba", "radix", "folia", "semen", "cortex",
    "contra", "item", "recipe", "ana", "cum", "per", "pro",
    "datur", "sumat", "misce", "fiat", "adde", "solve",
    "sal", "mel", "cera", "rosa", "salvia", "ruta",
    "ius", "res", "ars", "cor", "sol", "far", "das",
    "est", "sed", "non", "aut", "vel", "sic", "hoc",
    "ter", "bis", "semel", "hora", "die", "nocte",
    "calor", "dolor", "humor", "color", "odor",
    "acer", "arum", "orum", "ius", "alis", "aris",
    "atus", "itus", "utus", "atus", "ensis", "inus",
    "olus", "ulus", "icus", "acus",
    "contra", "supra", "infra", "extra", "intra",
    "accipe", "contere", "distilla",
    "oris", "eris", "iris", "uris",
}

def main():
    words = extract_words(FOLIO)
    out = []
    out.append("=" * 80)
    out.append("PHASE 106b — BENCH SUBSTITUTION VARIANT SCAN")
    out.append("=" * 80)
    out.append(f"Total f1r tokens: {len(words)}")
    out.append(f"ch variants: {CH_OPTIONS}")
    out.append(f"sh variants: {SH_OPTIONS}")
    out.append(f"Total combinations: {len(CH_OPTIONS) * len(SH_OPTIONS)}")
    out.append("")
    
    # For each ch/sh combination, decode all words and count Latin hits
    best_score = 0
    best_combo = None
    results = []
    
    for ch_sub, sh_sub in product(CH_OPTIONS, SH_OPTIONS):
        decoded = [decode_full(w, ch_sub, sh_sub) for w in words]
        
        # Count tokens that contain recognizable Latin substrings
        hits = []
        for eva, dec in zip(words, decoded):
            dec_lower = dec.lower()
            for lat in LATIN_PHARMA:
                if lat in dec_lower and len(lat) >= 3:
                    hits.append((eva, dec, lat))
                    break
        
        score = len(hits)
        results.append((ch_sub, sh_sub, score, hits, decoded))
        if score > best_score:
            best_score = score
            best_combo = (ch_sub, sh_sub)
    
    # Sort by score
    results.sort(key=lambda x: -x[2])
    
    out.append("─" * 80)
    out.append("RANKING BY LATIN PHARMACEUTICAL WORD HITS (≥3 chars)")
    out.append("─" * 80)
    out.append("")
    for ch_sub, sh_sub, score, hits, _ in results[:10]:
        out.append(f"  ch→{ch_sub}, sh→{sh_sub}: {score} hits")
        for eva, dec, lat_match in hits[:8]:
            out.append(f"    {eva:20s} → {dec:25s} (matched: {lat_match})")
        if len(hits) > 8:
            out.append(f"    ... and {len(hits)-8} more")
        out.append("")
    
    # Show the best combination's full decode
    best_ch, best_sh, best_sc, best_hits, best_decoded = results[0]
    out.append("─" * 80)
    out.append(f"BEST COMBINATION: ch→{best_ch}, sh→{best_sh} ({best_sc} hits)")
    out.append("FULL DECODE OF f1r:")
    out.append("─" * 80)
    out.append("")
    
    # Reconstruct lines
    idx = 0
    with open(FOLIO, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            m = re.match(r"<(f\d+[rv]\.\d+)", raw)
            if not m: continue
            line_id = m.group(1)
            text = re.sub(r"<[^>]*>|<!.*?>|<%>|<\$>", "", raw).strip()
            text = re.sub(r"\{[^}]*\}", lambda m: m.group(0)[1:-1], text)
            text = re.sub(r"\[([^:\]]+):([^\]]+)\]", r"\1", text)
            text = re.sub(r"\?|@\d+;?", "", text)
            line_words = [w.strip() for w in re.split(r"[.,]+", text) if w.strip()]
            n = len(line_words)
            dec_words = best_decoded[idx:idx+n]
            idx += n
            out.append(f"  {line_id}")
            out.append(f"    EVA: {' '.join(line_words)}")
            out.append(f"    DEC: {' '.join(dec_words)}")
            out.append("")
    
    # ── Look for repeated decoded forms that might be real words ──
    from collections import Counter
    ctr = Counter(best_decoded)
    out.append("─" * 80)
    out.append(f"MOST FREQUENT DECODED TOKENS (ch→{best_ch}, sh→{best_sh})")
    out.append("─" * 80)
    out.append("")
    for tok, cnt in ctr.most_common(40):
        out.append(f"  {tok:25s}  ×{cnt}")
    
    # ── Show first line word-by-word with all variants ──
    out.append("")
    out.append("─" * 80)
    out.append("FIRST LINE WORD-BY-WORD — ALL 25 BENCH VARIANTS")
    out.append("─" * 80)
    out.append("")
    first_line_words = words[:10]  # first EVA line
    for w in first_line_words:
        out.append(f"  EVA: {w}")
        variants = set()
        for ch_sub, sh_sub in product(CH_OPTIONS, SH_OPTIONS):
            dec = decode_full(w, ch_sub, sh_sub)
            variants.add(dec)
        for v in sorted(variants):
            out.append(f"       → {v}")
        out.append("")
    
    # ── Honest Assessment ──
    out.append("─" * 80)
    out.append("ASSESSMENT")
    out.append("─" * 80)
    out.append("")
    out.append("The abbreviation substitution produces NO recognizable continuous")
    out.append("text in any variant. Specific problems:")
    out.append("")
    out.append("1. BENCH OPACITY: ch and sh appear in ~40% of tokens but have")
    out.append("   no single definitive substitution. They could represent 5+")
    out.append("   different Latin ligatures each, and the 'correct' mapping may")
    out.append("   vary by position and context.")
    out.append("")
    out.append("2. GALLOWS MYSTERY: k, t, p, f (especially benched variants cth,")
    out.append("   cph, cfh) are composite constructions. Our simple k→I mapping")
    out.append("   is almost certainly wrong for most contexts.")
    out.append("")
    out.append("3. THE 'o' PROBLEM: EVA-o appears in 55 bigrams on f1r alone.")
    out.append("   Whether it's a vowel, null, separator, or something else")
    out.append("   fundamentally changes the decoded output.")
    out.append("")
    out.append("4. ADDITIONAL CIPHER LAYER: If abbreviation is only ONE component")
    out.append("   of a multi-layer encoding (as Phase 105 suggested at ~30%),")
    out.append("   then abbreviation substitution alone cannot produce readable")
    out.append("   text — there's still an alphabet substitution or verbose")
    out.append("   cipher layer underneath/on top.")
    out.append("")
    out.append("5. WRONG UNIT SIZE: JKP argues some EVA characters are 2-4")
    out.append("   components. If EVA character boundaries are wrong, ALL our")
    out.append("   substitutions are operating on incorrect units.")
    out.append("")
    out.append("CONCLUSION: We do NOT have enough information to translate the")
    out.append("manuscript. The abbreviation mappings explain the STRUCTURAL")
    out.append("properties (paradigm fill, suffix distribution) but do not")
    out.append("constitute a decipherment key. A successful decoding would need:")
    out.append("  - Correct character segmentation (not necessarily EVA)")
    out.append("  - Resolution of bench ambiguity (ch, sh → which ligature?)")
    out.append("  - Resolution of gallows composites")
    out.append("  - Identification of any additional cipher layer")
    out.append("  - Knowledge of the source language")
    
    result_text = "\n".join(out)
    print(result_text)
    
    RESULTS.parent.mkdir(exist_ok=True)
    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write(result_text)
    print(f"\nSaved to {RESULTS}")

if __name__ == "__main__":
    main()
