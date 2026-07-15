"""Hand-verified checks for common.core.ivtff_clean_words (finding T1)."""
from common.core import ivtff_clean_words


def run():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append(f"{name}: got {got!r}, want {want!r}")

    # metadata comment must vanish entirely (was: 'la' phantom from $L=A)
    check("metadata comment",
          ivtff_clean_words("<! $Q=S $P=C $F=b $L=A>"), [])

    # alternate reading -> first alternative, never fused
    check("alternate first",
          ivtff_clean_words("chofa[r:n]y"), ["chofary"])
    check("alternate 3-way",
          ivtff_clean_words("yk[eee:ech:e]o"), ["ykeeeo"])

    # '!' is padding, not a break
    check("padding", ivtff_clean_words("ch!ol"), ["chol"])

    # illegible glyph kills the whole word, never truncates
    check("illegible drop", ivtff_clean_words("cho%or.daiin"), ["daiin"])
    check("star drop", ivtff_clean_words("sh*y.ol"), ["ol"])

    # inline tags act as breaks; single-glyph words survive (min_word_len=1)
    check("tag break + short word",
          ivtff_clean_words("shol<-> y.qokal"), ["shol", "y", "qokal"])

    # comma: break by default, join when comma_break=False
    check("comma break", ivtff_clean_words("okal,dy"), ["okal", "dy"])
    check("comma join",
          ivtff_clean_words("okal,dy", comma_break=False), ["okaldy"])

    # min_word_len filter
    check("min len 2", ivtff_clean_words("y.ol.daiin", min_word_len=2),
          ["ol", "daiin"])

    return fails
