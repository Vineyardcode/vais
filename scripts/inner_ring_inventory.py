#!/usr/bin/env python3
"""
Innermost Ring Deep-Dive

The innermost rings (ring_idx >= 2) are the shortest ring texts (7-26 words),
closest to the zodiac sign center. Previous analysis found they have:
  - 44% -iin suffix rate (vs 9% outer)
  - 67% o-prefix rate (vs 28% outer)
  - The most formulaic structure

This script performs word-by-word analysis of all 12 inner/innermost rings.

Steps:
  1. Complete inventory — every word cataloged with morphology
  2. Cross-ring comparison — what words/roots repeat across inner rings?
  3. Structural template extraction — what's the sentence skeleton?
  4. Sign-specific vocabulary — what's unique to each sign's inner ring?
  5. The "oteos aiin" formula in inner rings
  6. Inner ring vocabulary vs outer ring vocabulary (same folio)
  7. Inner ring vocabulary vs nymph labels (same folio)
  8. Candidate semantic assignments based on all evidence
"""

import re
import json
from collections import Counter, defaultdict
from pathlib import Path
from common import result_path

# ── Load data ────────────────────────────────────────────────────────────

def load_data():
    with open(result_path("grammar_results.json")) as f:
        grammar = json.load(f)

    # Separate inner rings (idx >= 2) and outer rings (idx < 2)
    inner = []
    outer = []
    for sent in grammar["tagged_sentences"]:
        if sent["ring_idx"] >= 2:
            inner.append(sent)
        else:
            outer.append(sent)

    # Load ring text results for additional context
    with open(result_path("ring_text_results.json")) as f:
        ring_results = json.load(f)

    return inner, outer, grammar, ring_results


# ── Nymph label extraction ──────────────────────────────────────────────

ZODIAC_FILES = [
    "folios/f70v_part.txt", "folios/f71r.txt", "folios/f71v_72r.txt",
    "folios/f72v_part.txt", "folios/f73r.txt", "folios/f73v.txt",
]

FOLIO_SIGN = {
    "f70v1": "Aries", "f70v2": "Pisces",
    "f71r": "Aries", "f71v": "Taurus",
    "f72r1": "Taurus", "f72r2": "Gemini", "f72r3": "Cancer",
    "f72v1": "Libra", "f72v2": "Virgo", "f72v3": "Leo",
    "f73r": "Scorpio", "f73v": "Sagittarius",
}

def extract_nymph_labels():
    """Extract nymph labels per sign."""
    labels_by_sign = defaultdict(list)
    for filepath in ZODIAC_FILES:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Match label locus tags
                if not re.search(r'[@&][Ll]', line):
                    continue
                m = re.match(r'<([^>]+)>\s*(.*)', line)
                if not m:
                    continue
                locus = m.group(1)
                text = m.group(2)

                # Get folio ID
                folio_match = re.match(r'(f\d+[rv]\d?)', locus)
                if not folio_match:
                    continue
                folio_id = folio_match.group(1)
                sign = FOLIO_SIGN.get(folio_id, "Unknown")

                # Clean text
                text = re.sub(r'<![^>]*>', '', text)
                text = re.sub(r'\[([^:]+):[^\]]+\]', r'\1', text)
                text = re.sub(r'\{([^}]+)\}', r'\1', text)
                text = re.sub(r'@\d+;?', '', text)
                text = text.replace('?', '').strip(",'")
                tokens = re.split(r'[.\s,]+', text)
                for tok in tokens:
                    tok = tok.strip()
                    if tok and re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                        labels_by_sign[sign].append(tok)

    return labels_by_sign


# ══════════════════════════════════════════════════════════════════════════
# STEPS
# ══════════════════════════════════════════════════════════════════════════

def part1_complete_inventory(inner):
    """Catalog every word in inner rings."""
    print("=" * 72)
    print("COMPLETE INNER RING INVENTORY")
    print("=" * 72)

    all_words = Counter()
    all_roots = Counter()
    signs_per_word = defaultdict(set)
    iin_words = []
    o_words = []

    for sent in inner:
        sign = sent["sign"]
        for t in sent["tagged"]:
            all_words[t["word"]] += 1
            signs_per_word[t["word"]].add(sign)
            if t["root"]:
                all_roots[t["root"]] += 1
            if "iin" in t["suf_class"].lower() or "aiin" in t["suf_class"].lower():
                iin_words.append((t["word"], sign, sent["ring_idx"]))
            if t["class"] == "O-CONT":
                o_words.append((t["word"], sign, sent["ring_idx"]))

    total_words = sum(all_words.values())
    print(f"\n  Total inner ring words: {total_words}")
    print(f"  Unique words: {len(all_words)}")
    print(f"  Sentences: {len(inner)}")
    print(f"  Mean length: {total_words/len(inner):.1f} words")

    # All words ranked
    print(f"\n  All inner ring words by frequency:")
    for word, count in all_words.most_common():
        signs = sorted(signs_per_word[word])
        sign_str = "/".join(s[:3] for s in signs)
        print(f"    {word:18s}  {count:2d}×  in {sign_str}")

    # -iin words
    print(f"\n  All -iin/-aiin bearing words ({len(iin_words)} tokens):")
    for word, sign, ring in iin_words:
        print(f"    {word:18s}  {sign:12s}  ring{ring}")

    # o-prefixed words
    print(f"\n  All o-prefixed content words ({len(o_words)} tokens):")
    for word, sign, ring in o_words:
        print(f"    {word:18s}  {sign:12s}  ring{ring}")

    return all_words, signs_per_word


def part2_cross_ring_comparison(inner):
    """What words/patterns repeat across different signs' inner rings?"""
    print("\n" + "=" * 72)
    print("CROSS-RING VOCABULARY COMPARISON")
    print("=" * 72)

    # Vocabulary per sign
    sign_vocab = defaultdict(Counter)
    for sent in inner:
        for t in sent["tagged"]:
            sign_vocab[sent["sign"]][t["word"]] += 1

    # Pairwise Jaccard
    signs = sorted(sign_vocab.keys())
    print(f"\n  Pairwise Jaccard similarity (inner rings only):")
    print(f"  {'':10s}", end="")
    for s in signs:
        print(f"  {s[:3]:>5s}", end="")
    print()

    for s1 in signs:
        v1 = set(sign_vocab[s1].keys())
        print(f"  {s1[:10]:10s}", end="")
        for s2 in signs:
            v2 = set(sign_vocab[s2].keys())
            j = len(v1 & v2) / len(v1 | v2) if (v1 | v2) else 0
            print(f"  {j:5.3f}", end="")
        print()

    # Words appearing in 3+ signs' inner rings
    word_signs = defaultdict(set)
    for sent in inner:
        for t in sent["tagged"]:
            word_signs[t["word"]].add(sent["sign"])

    widespread = [(w, s) for w, s in word_signs.items() if len(s) >= 3]
    widespread.sort(key=lambda x: -len(x[1]))
    print(f"\n  Words in 3+ signs' inner rings:")
    for w, signs_set in widespread:
        print(f"    {w:18s}  in {len(signs_set)} signs: {sorted(s[:3] for s in signs_set)}")

    # Words unique to exactly one sign's inner ring
    unique_per_sign = defaultdict(list)
    for w, s in word_signs.items():
        if len(s) == 1:
            unique_per_sign[list(s)[0]].append(w)
    print(f"\n  Sign-unique inner ring words:")
    for sign in sorted(unique_per_sign.keys()):
        words = unique_per_sign[sign]
        print(f"    {sign:12s}: {len(words)} unique — {', '.join(words[:8])}")


def part3_structural_templates(inner):
    """Extract sentence skeletons."""
    print("\n" + "=" * 72)
    print("STRUCTURAL TEMPLATES")
    print("=" * 72)

    print(f"\n  Sentence class sequences (inner rings only):")
    for sent in inner:
        sign = sent["sign"][:3]
        ring = sent["ring_idx"]
        n = len(sent["tagged"])
        classes = " ".join(t["coarse"] for t in sent["tagged"])
        print(f"    {sign}r{ring} ({n:2d}w): {classes}")

    # Pattern extraction: opening 3 words
    print(f"\n  Opening 3-word class patterns:")
    openings = Counter()
    for sent in inner:
        if len(sent["tagged"]) >= 3:
            pat = " ".join(t["coarse"] for t in sent["tagged"][:3])
            openings[pat] += 1
    for pat, count in openings.most_common(10):
        print(f"    {pat}  ×{count}")

    # Closing 3 words
    print(f"\n  Closing 3-word class patterns:")
    closings = Counter()
    for sent in inner:
        if len(sent["tagged"]) >= 3:
            pat = " ".join(t["coarse"] for t in sent["tagged"][-3:])
            closings[pat] += 1
    for pat, count in closings.most_common(10):
        print(f"    {pat}  ×{count}")

    # Function word positions within each sentence
    print(f"\n  Function word positions per sentence:")
    for sent in inner:
        sign = sent["sign"][:3]
        ring = sent["ring_idx"]
        n = len(sent["tagged"])
        func_pos = [i for i, t in enumerate(sent["tagged"]) if t["coarse"] == "F"]
        if func_pos:
            norm_pos = [f"{p/max(n-1,1):.2f}" for p in func_pos]
            print(f"    {sign}r{ring} ({n:2d}w): positions {func_pos} = normalized [{', '.join(norm_pos)}]")
        else:
            print(f"    {sign}r{ring} ({n:2d}w): NO function words")


def part4_inner_vs_outer(inner, outer):
    """Compare inner ring vocabulary against outer rings of the same folio."""
    print("\n" + "=" * 72)
    print("INNER vs OUTER RING VOCABULARY (SAME FOLIO)")
    print("=" * 72)

    # Group by folio
    inner_by_folio = defaultdict(set)
    outer_by_folio = defaultdict(set)

    for sent in inner:
        folio_id = re.match(r'(f\d+[rv]\d?)', sent["folio_line"]).group(1)
        for t in sent["tagged"]:
            inner_by_folio[folio_id].add(t["word"])
    for sent in outer:
        folio_id = re.match(r'(f\d+[rv]\d?)', sent["folio_line"]).group(1)
        for t in sent["tagged"]:
            outer_by_folio[folio_id].add(t["word"])

    for folio_id in sorted(inner_by_folio.keys()):
        inner_v = inner_by_folio[folio_id]
        outer_v = outer_by_folio.get(folio_id, set())
        shared = inner_v & outer_v
        inner_only = inner_v - outer_v
        outer_only = outer_v - inner_v
        sign = FOLIO_SIGN.get(folio_id, "?")
        print(f"\n  {folio_id} ({sign}):")
        print(f"    Inner vocab: {len(inner_v)},  Outer vocab: {len(outer_v)}")
        print(f"    Shared: {len(shared)} — {sorted(shared)[:10]}")
        print(f"    Inner-only: {len(inner_only)} — {sorted(inner_only)[:10]}")


def part5_inner_vs_labels(inner, labels_by_sign):
    """Compare inner ring words against nymph labels for the same sign."""
    print("\n" + "=" * 72)
    print("INNER RING vs NYMPH LABELS (SAME SIGN)")
    print("=" * 72)

    inner_by_sign = defaultdict(set)
    for sent in inner:
        for t in sent["tagged"]:
            inner_by_sign[sent["sign"]].add(t["word"])

    for sign in sorted(inner_by_sign.keys()):
        inner_v = inner_by_sign[sign]
        label_v = set(labels_by_sign.get(sign, []))
        shared = inner_v & label_v
        inner_only = inner_v - label_v
        label_only = label_v - inner_v
        print(f"\n  {sign}:")
        print(f"    Inner ring words: {len(inner_v)}")
        print(f"    Nymph labels: {len(label_v)}")
        print(f"    Shared: {len(shared)}", end="")
        if shared:
            print(f" — {sorted(shared)}")
        else:
            print(" — NONE")
        print(f"    Inner-only: {sorted(inner_only)[:8]}")


def part6_oteos_aiin_analysis(inner):
    """Deep analysis of the 'oteos aiin' formula in inner rings."""
    print("\n" + "=" * 72)
    print("'oteos aiin' AND OTHER FORMULAE IN INNER RINGS")
    print("=" * 72)

    for sent in inner:
        words = sent["words"]
        sign = sent["sign"]
        ring = sent["ring_idx"]
        # Check for oteos...aiin
        for i in range(len(words) - 1):
            if words[i] == "oteos" and words[i+1] == "aiin":
                left = words[max(0,i-2):i]
                right = words[i+2:min(len(words),i+5)]
                print(f"    {sign:12s} ring{ring}: ...{' '.join(left)} [oteos aiin] {' '.join(right)}...")

    # Other repeated bigrams in inner rings
    print(f"\n  All bigrams in inner rings (count >= 2):")
    bigrams = Counter()
    for sent in inner:
        words = sent["words"]
        for i in range(len(words) - 1):
            bigrams[(words[i], words[i+1])] += 1
    for (a, b), count in bigrams.most_common():
        if count < 2:
            break
        print(f"    '{a} {b}'  ×{count}")

    # Repeated single words across inner rings of different signs
    print(f"\n  All repeated words (appearing in 2+ inner ring sentences):")
    word_sents = defaultdict(list)
    for sent in inner:
        sign = sent["sign"]
        for t in sent["tagged"]:
            word_sents[t["word"]].append(sign)
    for word, occurrences in sorted(word_sents.items(), key=lambda x: -len(x[1])):
        if len(occurrences) >= 2:
            signs = Counter(occurrences)
            print(f"    {word:18s}  {len(occurrences)}× in {dict(signs)}")


def part7_morpheme_patterns(inner):
    """Look for stem+suffix patterns that might encode systematic info."""
    print("\n" + "=" * 72)
    print("MORPHEME PATTERN ANALYSIS")
    print("=" * 72)

    # Group words by their root
    root_words = defaultdict(list)
    for sent in inner:
        for t in sent["tagged"]:
            if t["root"] and t["root"] != t["word"]:  # has meaningful parse
                root_words[t["root"]].append({
                    "word": t["word"],
                    "prefix": t["prefix"],
                    "suffix": t["suffix"],
                    "sign": sent["sign"],
                    "ring": sent["ring_idx"],
                })

    print(f"\n  Roots appearing with multiple forms in inner rings:")
    for root, forms in sorted(root_words.items(), key=lambda x: -len(x[1])):
        if len(forms) >= 2:
            form_strs = [f"{f['word']}({f['sign'][:3]})" for f in forms]
            suffixes = set(f["suffix"] for f in forms)
            prefixes = set(f["prefix"] for f in forms)
            print(f"    root={root:8s}  forms: {', '.join(form_strs)}")
            print(f"        prefixes={prefixes}  suffixes={suffixes}")

    # Look for ot- prefix pattern (very common in inner rings)
    print(f"\n  Words beginning with 'ot' in inner rings:")
    ot_words = []
    for sent in inner:
        for t in sent["tagged"]:
            if t["word"].startswith("ot"):
                ot_words.append((t["word"], sent["sign"], sent["ring_idx"]))
    ot_counter = Counter(w for w, s, r in ot_words)
    for word, count in ot_counter.most_common():
        signs = [s for w, s, r in ot_words if w == word]
        print(f"    {word:18s}  {count}× in {Counter(s[:3] for s in signs)}")

    # Look for ok- prefix pattern
    print(f"\n  Words beginning with 'ok' in inner rings:")
    ok_words = []
    for sent in inner:
        for t in sent["tagged"]:
            if t["word"].startswith("ok"):
                ok_words.append((t["word"], sent["sign"], sent["ring_idx"]))
    ok_counter = Counter(w for w, s, r in ok_words)
    for word, count in ok_counter.most_common():
        signs = [s for w, s, r in ok_words if w == word]
        print(f"    {word:18s}  {count}× in {Counter(s[:3] for s in signs)}")

    # ch- words
    print(f"\n  Words beginning with 'ch' in inner rings:")
    ch_words = []
    for sent in inner:
        for t in sent["tagged"]:
            if t["word"].startswith("ch"):
                ch_words.append((t["word"], sent["sign"], sent["ring_idx"]))
    ch_counter = Counter(w for w, s, r in ch_words)
    for word, count in ch_counter.most_common():
        signs = [s for w, s, r in ch_words if w == word]
        print(f"    {word:18s}  {count}× in {Counter(s[:3] for s in signs)}")


def part8_synthesis(inner, all_words, signs_per_word):
    """Synthesize findings into candidate semantic model."""
    print("\n" + "=" * 72)
    print("SYNTHESIS — CANDIDATE SEMANTIC MODEL")
    print("=" * 72)

    total = sum(all_words.values())
    func_words = {"aiin", "ar", "al", "s", "daiin", "dal", "am", "dar",
                  "y", "or", "ol", "dy", "r", "air", "o"}

    # Classify inner ring vocabulary
    func_count = sum(all_words.get(fw, 0) for fw in func_words)
    func_pct = 100 * func_count / total
    print(f"\n  Inner ring total: {total} words")
    print(f"  Function words: {func_count} ({func_pct:.1f}%)")

    # Count o-prefixed, -iin words
    iin_count = 0
    o_count = 0
    for sent in inner:
        for t in sent["tagged"]:
            if "iin" in t["suffix"].lower() or "aiin" in t["suffix"].lower():
                iin_count += 1
            if t["class"] == "O-CONT":
                o_count += 1

    print(f"  -iin/-aiin tokens: {iin_count} ({100*iin_count/total:.1f}%)")
    print(f"  o-prefixed content: {o_count} ({100*o_count/total:.1f}%)")

    # The Cancer innermost ring (ring3) is unique — let's highlight it
    print(f"\n  CANCER INNERMOST RING (ring3, 9 words):")
    for sent in inner:
        if sent["ring_idx"] == 3:
            print(f"    {' '.join(sent['words'])}")
            print(f"    Structure: {' '.join(t['coarse'] for t in sent['tagged'])}")
            print(f"    This is the MOST formulaic ring. Structure:")
            print(f"    okeos aiin | olaiin oraiin | octheolarl okeeody | oteos aiin | koly")
            print(f"    = [B F] [O O] [B B] [B F] [B]")
            print(f"    Two 'X aiin' frames bookending o-prefixed -iin words")

    # Print all inner rings as a comparative table
    print(f"\n  ALL INNER RINGS — COMPARATIVE TABLE:")
    print(f"  {'Sign':12s} {'Ring':4s} {'Len':4s} {'Func%':6s} {'o-%':5s} {'-iin%':6s} {'First word':16s} {'Last word':16s}")
    for sent in inner:
        n = len(sent["tagged"])
        n_func = sum(1 for t in sent["tagged"] if t["coarse"] == "F")
        n_o = sum(1 for t in sent["tagged"] if t["class"] == "O-CONT")
        n_iin = sum(1 for t in sent["tagged"]
                    if "iin" in t.get("suffix", "").lower() or "aiin" in t.get("suffix", "").lower())
        print(f"  {sent['sign']:12s}  r{sent['ring_idx']}  {n:3d}  {100*n_func/n:5.1f} {100*n_o/n:5.1f} {100*n_iin/n:5.1f}"
              f"  {sent['words'][0]:16s} {sent['words'][-1]:16s}")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    inner, outer, grammar, ring_results = load_data()
    labels_by_sign = extract_nymph_labels()

    print(f"Loaded {len(inner)} inner ring sentences, {len(outer)} outer ring sentences\n")

    all_words, signs_per_word = part1_complete_inventory(inner)
    part2_cross_ring_comparison(inner)
    part3_structural_templates(inner)
    part4_inner_vs_outer(inner, outer)
    part5_inner_vs_labels(inner, labels_by_sign)
    part6_oteos_aiin_analysis(inner)
    part7_morpheme_patterns(inner)
    part8_synthesis(inner, all_words, signs_per_word)

    print(f"\n\nDone.")