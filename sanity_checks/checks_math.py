"""Hand-verified checks for the statistical helpers in scripts/common.

Every expected value below is derived independently in the comments —
never by calling the function under test.
"""
import math
from collections import Counter

from common import (char_bigram_predictability, compute_H, compute_mi,
                    conditional_entropy, entropy, entropy_v2,
                    hapax_ratio_at_midpoint, index_of_coincidence,
                    ttr_at_n, zipf_alpha)


def run():
    fails = []

    def check(name, got, want, tol=1e-9):
        ok = (math.isclose(got, want, rel_tol=0, abs_tol=tol)
              if isinstance(want, float) else got == want)
        if not ok:
            fails.append(f"{name}: got {got!r}, want {want!r}")

    # ── entropy ──────────────────────────────────────────────────────
    # uniform over 4 symbols: H = log2(4) = 2 exactly
    check("entropy uniform-4", entropy(Counter(a=1, b=1, c=1, d=1)), 2.0)
    check("entropy_v2 uniform-4", entropy_v2(Counter(a=1, b=1, c=1, d=1)), 2.0)
    # single symbol: H = 0
    check("entropy single", entropy(Counter(a=7)), 0.0)
    # empty: defined 0
    check("entropy empty", entropy(Counter()), 0.0)
    # H(1/4,3/4) = -(0.25 log2 0.25 + 0.75 log2 0.75)
    #            = 0.5 + 0.75*log2(4/3) = 0.8112781244591328
    check("entropy 1:3", entropy(Counter(a=1, b=3)), 0.8112781244591328)
    # entropy and entropy_v2 must agree on an arbitrary case
    c = Counter(a=5, b=2, c=9, d=1)
    check("entropy == entropy_v2", entropy(c), entropy_v2(c), tol=1e-12)
    # compute_H(counts, total): equals entropy when total == sum(counts)
    check("compute_H matches entropy", compute_H(c, sum(c.values())),
          entropy(c), tol=1e-12)

    # ── mutual information ───────────────────────────────────────────
    # independent: MI = 0
    check("MI independent", compute_mi(['a','a','b','b'], ['c','d','c','d']), 0.0)
    # identical binary: MI = H(X) = 1
    check("MI identical", compute_mi(['a','a','b','b'], ['a','a','b','b']), 1.0)
    # hand case X=[a,a,a,b], Y=[c,c,d,d]:
    #   joint (a,c)=1/2, (a,d)=1/4, (b,d)=1/4; pX(a)=3/4, pY(c)=1/2
    #   MI = .5*log2(.5/(.75*.5)) + .25*log2(.25/(.75*.5)) + .25*log2(.25/(.25*.5))
    #      = .5*log2(4/3) + .25*log2(2/3) + .25*1 = 0.31127812445913283
    check("MI hand 2x2", compute_mi(['a','a','a','b'], ['c','c','d','d']),
          0.31127812445913283)
    check("MI empty", compute_mi([], []), 0.0)

    # ── conditional entropy H(Y|X) = H(X,Y) - H(X) ───────────────────
    # deterministic alternation a,b,a,b,a: bigrams (a,b)x2,(b,a)x2;
    # prev-marginal a=2,b=2 -> H(joint)=1, H(X)=1 -> H(Y|X)=0
    check("condH deterministic",
          conditional_entropy(Counter({('a','b'): 2, ('b','a'): 2}),
                              Counter({'a': 2, 'b': 2})), 0.0)
    # fair-coin pairs, Y independent of X:
    # joint uniform over 4 pairs -> H=2; H(X)=1 -> H(Y|X)=1
    check("condH independent",
          conditional_entropy(Counter({('a','c'):1,('a','d'):1,('b','c'):1,('b','d'):1}),
                              Counter({'a': 2, 'b': 2})), 1.0)

    # ── char bigram predictability = H(c|prev)/H(c) ──────────────────
    # perfectly deterministic successor: ratio 0
    check("cbp deterministic", char_bigram_predictability(list("abababab")), 0.0)
    # degenerate input (<2 chars): defined 1.0
    check("cbp tiny", char_bigram_predictability(list("a")), 1.0)

    # ── index of coincidence ─────────────────────────────────────────
    # "aabb": sum c(c-1) = 2+2 = 4; n(n-1) = 12 -> 1/3
    check("IC aabb", index_of_coincidence(list("aabb")), 1/3)
    # all same: 1.0 exactly
    check("IC monotone", index_of_coincidence(list("aaaa")), 1.0)
    # all distinct: 0.0
    check("IC distinct", index_of_coincidence(list("abcd")), 0.0)

    # ── zipf alpha: freq(r) = round(6000/r) has slope ~1 ─────────────
    words = []
    for r in range(1, 51):
        words += [f"w{r}"] * max(1, round(6000 / r))
    a = zipf_alpha(words)
    if not (0.95 <= a <= 1.05):
        fails.append(f"zipf_alpha synthetic 1/r: got {a}, want ~1.0")

    # ── ttr / hapax ──────────────────────────────────────────────────
    # 4 types over 8 tokens -> 0.5
    check("ttr", ttr_at_n(list("aabbccdd"), n=8), 0.5)
    # first half of [a,a,b, ...] = [a,a,b] wait: midpoint of 6 tokens = 3
    # tokens [x,x,y | ...]: freq x=2,y=1 -> hapax 1 of 2 types = 0.5
    check("hapax@mid", hapax_ratio_at_midpoint(['x','x','y','z','z','z']), 0.5)

    return fails
