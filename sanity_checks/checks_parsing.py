"""Hand-verified checks for tokenization/parsing helpers in scripts/common."""
from pathlib import Path

from common import (ALL_GALLOWS, classify_folio, classify_folio_header_section,
                    classify_folio_labels_taxonomy, classify_folio_v2,
                    classify_folio_v3, clean_word, collapse_e, collapse_echains,
                    eva_to_glyphs, extract_words_from_line, gallows_base,
                    get_collapsed, get_currier_language, get_gram_prefix,
                    get_prefix, get_suffix, parse_morphology,
                    parse_one_chunk, parse_word_into_chunks,
                    strip_gallows, strip_gallows_v2)


def run():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append(f"{name}: got {got!r}, want {want!r}")

    # ── EVA glyph tokenization ───────────────────────────────────────
    # trigraph beats digraph beats single; boundary at word end must work
    check("glyphs qockhedy", eva_to_glyphs("qockhedy"),
          ['q', 'o', 'ckh', 'e', 'd', 'y'])
    check("glyphs trailing trigraph", eva_to_glyphs("okcth"), ['o', 'k', 'cth'])
    check("glyphs lone trigraph", eva_to_glyphs("cth"), ['cth'])
    check("glyphs trailing digraph", eva_to_glyphs("ach"), ['a', 'ch'])
    check("glyphs sh digraph", eva_to_glyphs("shedy"), ['sh', 'e', 'd', 'y'])

    # ── gallows stripping ────────────────────────────────────────────
    # compound 'tch' must be removed as a unit (it precedes 't' in ALL_GALLOWS)
    assert ALL_GALLOWS.index('tch') < ALL_GALLOWS.index('t')
    check("strip compound", strip_gallows("otchey"), ("oey", ["tch"]))
    check("strip simple", strip_gallows("qokedy"), ("qoedy", ["k"]))
    check("strip none", strip_gallows("aiin"), ("aiin", []))
    check("strip_v2 string", strip_gallows_v2("qokedy"), "qoedy")

    # ── e-chain collapse ─────────────────────────────────────────────
    check("collapse eee", collapse_e("cheeey"), "chey")
    check("collapse == echains", collapse_e("cheeody"), collapse_echains("cheeody"))
    check("get_collapsed", get_collapsed("qokeedy"), "qoedy")

    # ── morphology split (prefix len-guard: len(w) > len(pf)+1) ─────
    # 'qoedy': prefix 'qo' (5 > 3), rest 'edy'; suffix scan: 'edy' fails the
    # len(w) > len(sf) guard (3 !> 3), 'dy' passes -> root 'e'
    check("morph qoedy", parse_morphology("qoedy"), ("qo", "e", "dy"))
    # IMPORTANT fall-through semantics (audit-pinned): the length guard is
    # per-CANDIDATE, not per-position. 'qoy': 'qo' fails (3 !> 3) but the
    # loop falls through to 'q' (3 > 2) -> prefix 'q', then suffix 'y',
    # root 'o'. Faithful to the original scripts.
    check("morph qoy fall-through", parse_morphology("qoy"), ("q", "o", "y"))

    # ── chunk grammar (Mauro slots) ──────────────────────────────────
    # 'daiin' -> glyphs d,a,i,i,n
    #   chunk1: SLOT4_SINGLE 'd' -> ['d'] (a not in SLOT5 -> stop)
    #   chunk2: SLOT2_SINGLE 'a', SLOT4_RUNS 'i','i', SLOT5 'n'
    chunks, unparsed, glyphs = parse_word_into_chunks("daiin")
    check("chunks daiin", chunks, [['d'], ['a', 'i', 'i', 'n']])
    check("chunks daiin unparsed", unparsed, [])
    # parse_one_chunk consumes nothing on a non-slot glyph
    check("one_chunk none", parse_one_chunk(['x'], 0), (None, 0))

    # ── word cleaning / extraction ───────────────────────────────────
    check("clean alt-reading", clean_word("[dain:daiin]"), "dain")
    check("clean curly", clean_word("da{x}in"), "dain")
    check("clean junk", clean_word("Da?In!"), "dain")
    check("extract line", extract_words_from_line("<%>daiin.chol,dar<$>"),
          ["daiin", "chol", "dar"])
    check("extract tags", extract_words_from_line("<!12:30> otedy @123;sh"),
          ["otedy", "sh"])

    # ── taxonomies (documented boundary cases) ───────────────────────
    check("num f58 herbal-A", classify_folio(Path("f58v.txt")), "herbal-A")
    check("num f59 unknown", classify_folio(Path("f59r.txt")), "unknown")
    check("num f65 herbal-A", classify_folio(Path("f65r.txt")), "herbal-A")
    check("num f88 pharma", classify_folio(Path("f88r.txt")), "pharma")
    check("num f90 herbal-B", classify_folio(Path("f90v.txt")), "herbal-B")
    check("v2 agrees", classify_folio_v2("f90v"), "herbal-B")
    check("labels f60 herbal-B", classify_folio_labels_taxonomy("f60r"), "herbal-B")
    check("labels f65 herbal-A", classify_folio_labels_taxonomy("f65r"), "herbal-A")
    check("header section", classify_folio_header_section(["# Herbal, language A"]),
          "herbal")
    check("header v3 tuple", classify_folio_v3(["# Zodiac, language B"]),
          ("astro", "B"))
    check("currier f26 B", get_currier_language(26), "B")
    check("currier f1 A", get_currier_language(1), "A")
    check("currier f75 B", get_currier_language(75), "B")

    # ── prefix/suffix pickers ────────────────────────────────────────
    check("gallows_base ckh", gallows_base("ckh"), "k")
    check("gallows_base cth", gallows_base("cth"), "t")
    check("get_prefix lch", get_prefix("lchedy"), "lch")
    # fall-through: 'qo' fails the len guard (2 !> 2) but 'q' matches (2 > 1)
    check("get_gram_prefix fall-through", get_gram_prefix("qo"), "q")
    check("get_suffix aiin", get_suffix("daiin"), "aiin")
    # fall-through: whole-word 'aiin' fails as suffix 'aiin' (4 !> 4) but
    # matches shorter 'iin' (4 > 3) -> classified suffix 'iin', implied stem 'a'
    check("get_suffix fall-through", get_suffix("aiin"), "iin")

    return fails
