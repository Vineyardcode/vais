"""Hand-verified checks for common/fingerprint.py (research instrument)."""
import math

from common.fingerprint import (adjacency_repetition, char_entropy_stack,
                                fingerprint, levenshtein,
                                line_effect_scores, positional_predictability)


def run():
    fails = []

    def check(name, got, want, tol=1e-9):
        ok = (math.isclose(got, want, rel_tol=0, abs_tol=tol)
              if isinstance(want, float) else got == want)
        if not ok:
            fails.append(f"{name}: got {got!r}, want {want!r}")

    # levenshtein hand cases
    check("lev identical", levenshtein("abc", "abc"), 0)
    check("lev sub", levenshtein("abc", "axc"), 1)
    check("lev kitten", levenshtein("kitten", "sitting"), 3)
    check("lev empty", levenshtein("", "ab"), 2)

    # entropy stack on a fully deterministic stream:
    # tokens ['ab','ab',...] -> stream a,b,' ',a,b,' ',... every char's
    # successor is determined -> h2 = 0; alphabet {a,b,' '} -> h0=log2(3);
    # uniform thirds -> h1 = log2(3)
    h0, h1, h2 = char_entropy_stack(['ab'] * 50)
    check("stack h0", h0, math.log2(3))
    check("stack h1", h1, math.log2(3), tol=1e-9)
    check("stack h2 deterministic", h2, 0.0, tol=1e-9)

    # adjacency repetition: line [x, x, y, xz] ->
    # pairs (x,x) exact; (x,y) dist 1/1=1.0 no; (y,xz) dist 2/2 no
    ax, an = adjacency_repetition([['x', 'x', 'y', 'xz']])
    check("adj exact", ax, 1 / 3)
    check("adj near none", an, 0.0)
    # near-repeat: abcd vs abce -> 1/4 = 0.25 <= threshold
    ax2, an2 = adjacency_repetition([['abcd', 'abce']])
    check("adj near hit", an2, 1.0)

    # line effects: identical-start words everywhere -> both JSD 0
    li, lf = line_effect_scores([['aa', 'ab', 'ac', 'ad']] * 5)
    check("line init zero", li, 0.0)
    check("line final JSD>0 case",
          line_effect_scores([['xa', 'aa', 'aa', 'ay']] * 5)[1] > 0, True)

    # positional predictability: perfectly rigid words -> per-position
    # entropy 0 -> ratio 0
    pp = positional_predictability(['abc'] * 200)
    check("pos rigid", pp, 0.0)

    # fingerprint smoke: all features present, no exceptions
    fp = fingerprint([['dain', 'daiin', 'chol'] * 10] * 40, label='t')
    for k in ('h2_ratio', 'adj_near', 'line_init_jsd', 'zipf_alpha'):
        if k not in fp:
            fails.append(f"fingerprint missing {k}")

    return fails
