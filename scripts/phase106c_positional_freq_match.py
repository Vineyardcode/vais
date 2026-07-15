#!/usr/bin/env python3
"""
Phase 106c — Positional Frequency Matching Across Languages

Instead of assuming Latin VALUES for abbreviation marks, this test asks:
"For each candidate language, what character BEST MATCHES the positional
frequency profile of each EVA glyph?"

Method:
  1. Compute VMS positional profiles: for each EVA glyph, measure
     P(initial), P(final), P(medial), overall frequency
  2. Compute the same profiles for each candidate language corpus
  3. Find the optimal frequency-rank mapping: match EVA glyphs to
     target language characters by their positional frequency ranks
  4. Apply mapping to f1r and see which language produces the most
     recognizable output

This is NOT a decipherment — it's a statistical compatibility test.
The mapping is constrained only by positional frequency, not by
any assumed sound values.
"""
import re
import glob
from pathlib import Path
from collections import Counter, defaultdict
import math

ROOT = Path(__file__).resolve().parent.parent
FOLIO = ROOT / "folios" / "f1r.txt"
RESULTS = ROOT / "results" / "phase106c_positional_frequency_match.txt"

# ── VMS Glyph Extraction ──────────────────────────────────────────

KNOWN_GLYPHS_ORDER = [
    "cth", "cfh", "cph", "ckh",  # 3-char benched gallows
    "ch", "sh",                    # 2-char benches
    "qo",                          # 2-char prefix
    "ai", "ee", "oi",             # 2-char vowel clusters
    "a", "c", "d", "e", "f", "g", "h", "i",  # singles
    "k", "l", "m", "n", "o", "p", "q", "r",
    "s", "t", "x", "y",
]

def parse_eva_word(word):
    """Parse EVA word into glyph sequence."""
    glyphs = []
    i = 0
    while i < len(word):
        matched = False
        for gl in KNOWN_GLYPHS_ORDER:
            if word[i:i+len(gl)] == gl:
                glyphs.append(gl)
                i += len(gl)
                matched = True
                break
        if not matched:
            glyphs.append(word[i])
            i += 1
    return glyphs

def extract_all_vms_words():
    """Extract ALL VMS words from all folios."""
    words = []
    for fpath in sorted(glob.glob(str(ROOT / "folios" / "*.txt"))):
        with open(fpath, encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not re.match(r"<f\d+", raw):
                    continue
                text = re.sub(r"<[^>]*>|<!.*?>|<%>|<\$>", "", raw).strip()
                text = re.sub(r"\{[^}]*\}", lambda m: m.group(0)[1:-1], text)
                text = re.sub(r"\[([^:\]]+):([^\]]+)\]", r"\1", text)
                text = re.sub(r"\?|@\d+;?", "", text)
                for w in re.split(r"[.,\s]+", text):
                    w = w.strip()
                    if w and len(w) > 0:
                        words.append(w)
    return words

def extract_f1r_words():
    """Extract just f1r words."""
    words = []
    with open(FOLIO, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not re.match(r"<f1r\.", raw):
                continue
            text = re.sub(r"<[^>]*>|<!.*?>|<%>|<\$>", "", raw).strip()
            text = re.sub(r"\{[^}]*\}", lambda m: m.group(0)[1:-1], text)
            text = re.sub(r"\[([^:\]]+):([^\]]+)\]", r"\1", text)
            text = re.sub(r"\?|@\d+;?", "", text)
            for w in re.split(r"[.,]+", text):
                w = w.strip()
                if w:
                    words.append(w)
    return words

def compute_vms_profiles(words):
    """Compute positional frequency profiles for VMS glyphs."""
    initial = Counter()
    final = Counter()
    medial = Counter()
    overall = Counter()
    
    for w in words:
        glyphs = parse_eva_word(w)
        if not glyphs:
            continue
        for idx, g in enumerate(glyphs):
            overall[g] += 1
            if idx == 0:
                initial[g] += 1
            if idx == len(glyphs) - 1:
                final[g] += 1
            if 0 < idx < len(glyphs) - 1:
                medial[g] += 1
    
    total_i = sum(initial.values()) or 1
    total_f = sum(final.values()) or 1
    total_m = sum(medial.values()) or 1
    total_o = sum(overall.values()) or 1
    
    profiles = {}
    all_glyphs = set(overall.keys())
    for g in all_glyphs:
        profiles[g] = {
            "initial": initial[g] / total_i,
            "final": final[g] / total_f,
            "medial": medial[g] / total_m,
            "overall": overall[g] / total_o,
            "count": overall[g],
        }
    return profiles


# ── Language Corpus Processing ─────────────────────────────────────

def load_corpus(path, encoding="utf-8"):
    """Load a text corpus and extract words."""
    text = Path(path).read_text(encoding=encoding, errors="replace")
    # Remove common markup
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"<[^>]*>", "", text)
    # Extract words (alphabetic only, lowercase)
    words = re.findall(r"[a-zäöüßàèéìòùáéíóúâêîôûçñšžčřďťňůýæœ]+", text.lower())
    return [w for w in words if len(w) > 1]  # skip single-char "words"

def load_czech_corpus():
    """Load Czech Bible Kralice (many files)."""
    words = []
    for fpath in sorted(glob.glob(str(ROOT / "data" / "czech_bible_kralice" / "ces1613_*_read.txt"))):
        text = Path(fpath).read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"\d+\.", "", text)  # remove verse numbers
        ws = re.findall(r"[a-záéíóúůýčďěňřšťžæœ]+", text.lower())
        words.extend([w for w in ws if len(w) > 1])
    return words

def compute_lang_profiles(words):
    """Compute positional character frequency profiles for a language."""
    initial = Counter()
    final = Counter()
    medial = Counter()
    overall = Counter()
    
    for w in words:
        chars = list(w)
        for idx, c in enumerate(chars):
            overall[c] += 1
            if idx == 0:
                initial[c] += 1
            if idx == len(chars) - 1:
                final[c] += 1
            if 0 < idx < len(chars) - 1:
                medial[c] += 1
    
    total_i = sum(initial.values()) or 1
    total_f = sum(final.values()) or 1
    total_m = sum(medial.values()) or 1
    total_o = sum(overall.values()) or 1
    
    profiles = {}
    for c in overall:
        profiles[c] = {
            "initial": initial[c] / total_i,
            "final": final[c] / total_f,
            "medial": medial[c] / total_m,
            "overall": overall[c] / total_o,
            "count": overall[c],
        }
    return profiles


# ── Frequency Matching ─────────────────────────────────────────────

def match_by_position(vms_profiles, lang_profiles):
    """
    Match VMS glyphs to language characters using positional frequency.
    
    For each position (initial, final, medial), rank VMS glyphs and
    language chars by frequency, then align ranks.
    
    Final mapping = weighted vote across 3 positions + overall freq.
    """
    # Get ranked lists for each position
    positions = ["initial", "final", "medial", "overall"]
    weights = {"initial": 2.0, "final": 3.0, "medial": 1.0, "overall": 1.0}
    # Final position gets highest weight because that's where abbreviation
    # marks are most distinctive
    
    vms_glyphs = sorted(vms_profiles.keys(), key=lambda g: -vms_profiles[g]["overall"])
    lang_chars = sorted(lang_profiles.keys(), key=lambda c: -lang_profiles[c]["overall"])
    
    # For each VMS glyph, score every language char
    scores = {}  # (vms_glyph, lang_char) → score
    
    for pos in positions:
        vms_ranked = sorted(vms_profiles.keys(), key=lambda g: -vms_profiles[g][pos])
        lang_ranked = sorted(lang_profiles.keys(), key=lambda c: -lang_profiles[c][pos])
        
        # Compute rank for each
        vms_rank = {g: i for i, g in enumerate(vms_ranked)}
        lang_rank = {c: i for i, c in enumerate(lang_ranked)}
        
        max_rank = max(len(vms_rank), len(lang_rank))
        
        for g in vms_profiles:
            for c in lang_profiles:
                key = (g, c)
                if key not in scores:
                    scores[key] = 0.0
                # Score = negative rank distance, weighted
                rank_dist = abs(vms_rank[g] / len(vms_rank) - lang_rank[c] / len(lang_rank))
                # Also consider absolute frequency similarity
                freq_dist = abs(vms_profiles[g][pos] - lang_profiles[c][pos])
                scores[key] -= weights[pos] * (rank_dist + freq_dist)
    
    # Greedy assignment: best score first, no reuse
    mapping = {}
    used_chars = set()
    used_glyphs = set()
    
    # Sort all pairs by score (best first)
    sorted_pairs = sorted(scores.items(), key=lambda x: -x[1])
    
    for (g, c), score in sorted_pairs:
        if g in used_glyphs or c in used_chars:
            continue
        mapping[g] = c
        used_glyphs.add(g)
        used_chars.add(c)
    
    return mapping


def apply_mapping(eva_word, mapping):
    """Apply glyph→char mapping to an EVA word."""
    glyphs = parse_eva_word(eva_word)
    result = []
    for g in glyphs:
        if g in mapping:
            result.append(mapping[g])
        else:
            result.append(f"[{g}]")
    return "".join(result)


def score_output(decoded_words, lang_words_set):
    """Score decoded output by how many tokens match real language words."""
    hits = 0
    for w in decoded_words:
        if w.lower() in lang_words_set and len(w) >= 3:
            hits += 1
    return hits


# ── Main ───────────────────────────────────────────────────────────

def main():
    out = []
    out.append("=" * 80)
    out.append("PHASE 106c — POSITIONAL FREQUENCY MATCHING ACROSS LANGUAGES")
    out.append("=" * 80)
    out.append("")
    out.append("Method: Match VMS EVA glyphs to target language characters")
    out.append("by positional frequency profiles (initial/final/medial),")
    out.append("NOT by assumed Latin sound values.")
    out.append("")
    out.append("Key insight: The abbreviation mark SHAPES come from Latin")
    out.append("scribal tradition, but the LANGUAGE could be anything.")
    out.append("So we match by statistical position, not by meaning.")
    out.append("")
    
    # Load VMS data
    print("Loading VMS corpus...")
    vms_all = extract_all_vms_words()
    vms_f1r = extract_f1r_words()
    vms_profiles = compute_vms_profiles(vms_all)
    
    out.append(f"VMS corpus: {len(vms_all)} tokens")
    out.append(f"VMS f1r: {len(vms_f1r)} tokens")
    out.append(f"VMS distinct glyphs: {len(vms_profiles)}")
    out.append("")
    
    # Show VMS top glyphs by position
    out.append("─" * 80)
    out.append("VMS GLYPH PROFILES (top 15 per position)")
    out.append("─" * 80)
    out.append("")
    for pos in ["initial", "final", "medial", "overall"]:
        ranked = sorted(vms_profiles.items(), key=lambda x: -x[1][pos])[:15]
        out.append(f"  {pos.upper():8s}: " + 
                   " ".join(f"{g}({p[pos]:.3f})" for g, p in ranked))
    out.append("")
    
    # Load language corpora
    corpora = {
        "Latin (Pliny)": ROOT / "data" / "latin_texts" / "pliny.txt",
        "Latin (Vulgate)": ROOT / "data" / "latin_texts" / "vulgate_genesis.txt",
        "Latin (Galen)": ROOT / "data" / "latin_texts" / "galen.txt",
        "Italian (Cucina)": ROOT / "data" / "vernacular_texts" / "italian_cucina.txt",
        "German (Ortolf)": ROOT / "data" / "vernacular_texts" / "german_ortolf_raw.txt",
        "German (Faust)": ROOT / "data" / "vernacular_texts" / "german_faust.txt",
        "French (Viandier)": ROOT / "data" / "vernacular_texts" / "french_viandier.txt",
        "English (Cury)": ROOT / "data" / "vernacular_texts" / "english_cury.txt",
    }
    
    results = []
    
    for lang_name, lang_path in corpora.items():
        print(f"Processing {lang_name}...")
        lang_words = load_corpus(lang_path)
        if len(lang_words) < 500:
            print(f"  Skipping {lang_name}: only {len(lang_words)} words")
            continue
        
        lang_profiles = compute_lang_profiles(lang_words)
        mapping = match_by_position(vms_profiles, lang_profiles)
        
        # Decode f1r
        decoded = [apply_mapping(w, mapping) for w in vms_f1r]
        
        # Score against language vocabulary
        lang_vocab = set(lang_words)
        word_hits = score_output(decoded, lang_vocab)
        
        # Also count 3-letter substring matches as softer metric
        all_trigrams = set()
        for w in lang_words:
            for i in range(len(w) - 2):
                all_trigrams.add(w[i:i+3])
        
        trigram_hits = 0
        for d in decoded:
            for i in range(len(d) - 2):
                if d[i:i+3] in all_trigrams:
                    trigram_hits += 1
        
        results.append({
            "name": lang_name,
            "n_words": len(lang_words),
            "n_chars": len(lang_profiles),
            "mapping": mapping,
            "decoded": decoded,
            "word_hits": word_hits,
            "trigram_hits": trigram_hits,
        })
    
    # Czech
    print("Processing Czech...")
    czech_words = load_czech_corpus()
    if len(czech_words) > 500:
        czech_profiles = compute_lang_profiles(czech_words)
        mapping = match_by_position(vms_profiles, czech_profiles)
        decoded = [apply_mapping(w, mapping) for w in vms_f1r]
        czech_vocab = set(czech_words)
        word_hits = score_output(decoded, czech_vocab)
        all_trigrams = set()
        for w in czech_words:
            for i in range(len(w) - 2):
                all_trigrams.add(w[i:i+3])
        trigram_hits = 0
        for d in decoded:
            for i in range(len(d) - 2):
                if d[i:i+3] in all_trigrams:
                    trigram_hits += 1
        results.append({
            "name": "Czech (Bible Kralice)",
            "n_words": len(czech_words),
            "n_chars": len(czech_profiles),
            "mapping": mapping,
            "decoded": decoded,
            "word_hits": word_hits,
            "trigram_hits": trigram_hits,
        })
    
    # Sort by word hits
    results.sort(key=lambda r: -(r["word_hits"] * 10 + r["trigram_hits"]))
    
    out.append("─" * 80)
    out.append("LANGUAGE RANKING BY DECODED WORD MATCHES")
    out.append("─" * 80)
    out.append("")
    out.append(f"{'Language':<25s} {'Corpus':>8s} {'Chars':>5s} {'Word Hits':>10s} {'Trigram Hits':>12s}")
    out.append("─" * 65)
    for r in results:
        out.append(f"{r['name']:<25s} {r['n_words']:>8d} {r['n_chars']:>5d} "
                   f"{r['word_hits']:>10d} {r['trigram_hits']:>12d}")
    out.append("")
    
    # Show top 3 results in detail
    for rank, r in enumerate(results[:3]):
        out.append("─" * 80)
        out.append(f"#{rank+1}: {r['name']} — MAPPING AND DECODE")
        out.append("─" * 80)
        out.append("")
        
        # Show mapping sorted by VMS frequency
        sorted_map = sorted(r["mapping"].items(), 
                          key=lambda x: -vms_profiles.get(x[0], {}).get("overall", 0))
        out.append("  Glyph mapping (by VMS frequency):")
        for g, c in sorted_map[:25]:
            vp = vms_profiles.get(g, {})
            out.append(f"    EVA-{g:4s} → {c:3s}  "
                       f"(VMS: init={vp.get('initial',0):.3f} "
                       f"fin={vp.get('final',0):.3f} "
                       f"med={vp.get('medial',0):.3f} "
                       f"all={vp.get('overall',0):.3f})")
        out.append("")
        
        # Show decoded f1r
        out.append("  Decoded f1r (first 15 lines):")
        idx = 0
        with open(FOLIO, encoding="utf-8") as f:
            line_count = 0
            for raw in f:
                raw = raw.strip()
                m = re.match(r"<(f1r\.\d+)", raw)
                if not m:
                    continue
                line_id = m.group(1)
                text = re.sub(r"<[^>]*>|<!.*?>|<%>|<\$>", "", raw).strip()
                text = re.sub(r"\{[^}]*\}", lambda m: m.group(0)[1:-1], text)
                text = re.sub(r"\[([^:\]]+):([^\]]+)\]", r"\1", text)
                text = re.sub(r"\?|@\d+;?", "", text)
                line_words = [w.strip() for w in re.split(r"[.,]+", text) if w.strip()]
                n = len(line_words)
                dec_words = r["decoded"][idx:idx+n]
                idx += n
                
                out.append(f"    {line_id}")
                out.append(f"      EVA: {' '.join(line_words)}")
                out.append(f"      DEC: {' '.join(dec_words)}")
                out.append("")
                line_count += 1
                if line_count >= 15:
                    break
        
        # Show word hits
        if r["word_hits"] > 0:
            out.append(f"  Matched real {r['name']} words:")
            lang_w = load_corpus(corpora[r['name']]) if r['name'] != "Czech (Bible Kralice)" else load_czech_corpus()
            lang_v = set(lang_w)
            for eva, dec in zip(vms_f1r, r["decoded"]):
                if dec.lower() in lang_v and len(dec) >= 3:
                    out.append(f"    {eva:20s} → {dec}")
            out.append("")
    
    # ── Assessment ──
    out.append("─" * 80)
    out.append("ASSESSMENT")
    out.append("─" * 80)
    out.append("")
    out.append("This test matches VMS glyphs to language characters purely")
    out.append("by POSITIONAL FREQUENCY — the most common word-final VMS glyph")
    out.append("maps to the most common word-final character in each language,")
    out.append("etc. No assumed sound values. No abbreviation meanings.")
    out.append("")
    out.append("If the VMS uses a simple positional substitution of a known")
    out.append("language, this should produce recognizable text for the correct")
    out.append("language, even without knowing the specific key.")
    out.append("")
    out.append("CRITICAL CAVEAT: This assumes 1-to-1 glyph-to-character mapping.")
    out.append("If the encoding is verbose (1 glyph → multiple chars) or")
    out.append("compressed (multiple glyphs → 1 char), this method cannot work.")
    out.append("It also treats EVA digraphs (ch, sh) as single units, which")
    out.append("may or may not be correct.")
    
    result_text = "\n".join(out)
    print(result_text[-2000:])  # print end
    
    RESULTS.parent.mkdir(exist_ok=True)
    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write(result_text)
    print(f"\nSaved to {RESULTS}")


if __name__ == "__main__":
    main()
