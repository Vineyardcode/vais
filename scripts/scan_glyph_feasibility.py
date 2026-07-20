#!/usr/bin/env python3
"""
Raw-Scan Glyph Feasibility (portfolio S2, rung 0) — can transliteration
-free analysis get off the ground with in-repo scans and no CV stack?
(N8)

PURPOSE: S2 is the only portfolio strategy that fully escapes
assumption A1 (the transliteration IS the text) — it would rebuild the
token stream from folio images with no human alphabet. Its registered
kill (F10 gate) is instability: "if cluster count is unstable (±30%)
across folios/scan qualities, transliteration-free analysis is
unreliable at this scan quality." This rung 0 asks the cheaper prior
question: with the repository's own scans (201 PNGs, ~1400x2000 RGB)
and this environment's tooling (numpy + Pillow; no OpenCV/scipy/GPU),
does a naive pipeline see anything at all worth clustering?

PIPELINE (fixed before running): seeded sample of N_FOLIOS folios that
have both .png and .txt; central CROP_FRAC crop (avoids scan borders);
greyscale; block-mean downscale by DOWNSCALE; Otsu threshold (ink =
dark side); connected components via row-run union-find; components
kept in the glyph-scale area band [AREA_MIN, AREA_MAX] px.

REGISTERED FEASIBILITY GATES:
  G1 binarization stability — median ink fraction within
     [INK_LO, INK_HI] and folio-to-folio coefficient of variation
     < INK_CV_MAX. (If thresholding is erratic, everything downstream
     is noise.)
  G2 segmentation sees the text — Spearman correlation between
     per-folio glyph-scale component counts and the transliteration's
     per-folio character counts: >= G2_STRONG strong; >= G2_WEAK
     partial; below, the pipeline is not seeing what the transcribers
     saw (drawings, bleed-through, and lighting dominate). Reported
     both for all sampled folios and for text-only folios (f103-116),
     where drawings cannot confound.
  G3 cluster-stability precursor — up to MAX_COMPONENTS glyph-scale
     components, 8 shape descriptors (log-area, height, width, aspect,
     fill, normalized central moments mu20/mu02/mu11), z-scored;
     seeded numpy k-means over K_SWEEP on two disjoint folio halves:
     G3a |k*_1 - k*_2| / mean(k*) <= 0.30 with k* = silhouette-best k
         (mirrors S2's registered ±30% kill),
     G3b at k=K_REF, greedy-matched centroid distance between halves
         < CENTROID_RATIO_MAX x the mean within-half centroid spacing.
PRE-REGISTERED VERDICTS:
  feasible                   — G1 and G2-strong (all-folio) and G3a
                               and G3b: build S2 proper.
  partially_feasible         — G1 and G2 >= G2_WEAK on all folios OR
                               >= G2_STRONG on text-only folios:
                               proceed restricted to text-only pages
                               and/or with better tooling; blockers
                               named.
  infeasible_at_this_quality — G1 fails, or G2 < G2_WEAK everywhere:
                               S2 is starved at this scan quality and
                               tooling (F10); revisit with better
                               scans or a real CV stack.
Vocabulary discipline: a feasibility probe of imaging, not a result
about the manuscript's content.
"""
import io
import json
import math
import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from common import result_path
from common.core import FOLIO_DIR, ivtff_clean_words

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

SEED = 123
N_FOLIOS = 30
CROP_FRAC = 0.8
DOWNSCALE = 2
AREA_MIN = 8
AREA_MAX = 800
INK_LO = 0.01
INK_HI = 0.30
INK_CV_MAX = 0.6
G2_STRONG = 0.8
G2_WEAK = 0.5
MAX_COMPONENTS = 6000
K_SWEEP = [10, 15, 20, 25, 30, 35, 40]
K_REF = 25
CENTROID_RATIO_MAX = 0.5
SIL_SAMPLE = 1500


def zl_char_count(stem):
    text = (FOLIO_DIR / f'{stem}.txt').read_text(encoding='utf-8',
                                                 errors='replace')
    n = 0
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('#') or not re.match(r'<([^>]+)>', line):
            continue
        for w in ivtff_clean_words(line[line.index('>') + 1:].strip()):
            n += len(w)
    return n


def load_grey(stem):
    im = Image.open(FOLIO_DIR / f'{stem}.png').convert('L')
    a = np.asarray(im, dtype=np.float32)
    h, w = a.shape
    ch, cw = int(h * (1 - CROP_FRAC) / 2), int(w * (1 - CROP_FRAC) / 2)
    a = a[ch:h - ch, cw:w - cw]
    d = DOWNSCALE
    a = a[:a.shape[0] // d * d, :a.shape[1] // d * d]
    return a.reshape(a.shape[0] // d, d, a.shape[1] // d, d).mean((1, 3))


def otsu(a):
    hist, edges = np.histogram(a, bins=256, range=(0, 255))
    p = hist / hist.sum()
    om = np.cumsum(p)
    mu = np.cumsum(p * np.arange(256))
    mu_t = mu[-1]
    with np.errstate(divide='ignore', invalid='ignore'):
        sigma = (mu_t * om - mu) ** 2 / (om * (1 - om))
    return float(np.nanargmax(sigma))


def components(mask):
    """Row-run connected components (8-conn via run overlap+diag),
    union-find. Returns list of (area, h, w, fill, mu20, mu02, mu11)."""
    runs = []          # (row, c0, c1, label)
    parent = []

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    prev = []
    for r in range(mask.shape[0]):
        row = mask[r]
        idx = np.flatnonzero(row)
        cur = []
        if idx.size:
            splits = np.flatnonzero(np.diff(idx) > 1)
            starts = np.concatenate(([0], splits + 1))
            ends = np.concatenate((splits, [idx.size - 1]))
            for s, e in zip(starts, ends):
                lab = len(parent)
                parent.append(lab)
                run = (r, int(idx[s]), int(idx[e]), lab)
                cur.append(run)
                runs.append(run)
        i = j = 0
        while i < len(prev) and j < len(cur):
            _, p0, p1, pl = prev[i]
            _, c0, c1, cl = cur[j]
            if c0 <= p1 + 1 and p0 <= c1 + 1:
                union(pl, cl)
            if p1 < c1:
                i += 1
            else:
                j += 1
        prev = cur

    groups = {}
    for r, c0, c1, lab in runs:
        groups.setdefault(find(lab), []).append((r, c0, c1))
    feats = []
    for g in groups.values():
        area = sum(c1 - c0 + 1 for _, c0, c1 in g)
        if not (AREA_MIN <= area <= AREA_MAX):
            continue
        rs = [r for r, _, _ in g]
        r0, r1 = min(rs), max(rs)
        c0s = min(c0 for _, c0, _ in g)
        c1s = max(c1 for _, _, c1 in g)
        h, w = r1 - r0 + 1, c1s - c0s + 1
        sy = sx = sxx = syy = sxy = 0.0
        for r, ca, cb in g:
            n = cb - ca + 1
            xs = (ca + cb) / 2
            sy += r * n
            sx += xs * n
            sxx += (n * (n * n - 1) / 12 + n * xs * xs)
            syy += n * r * r
            sxy += n * r * xs
        cy, cx = sy / area, sx / area
        mu20 = sxx / area - cx * cx
        mu02 = syy / area - cy * cy
        mu11 = sxy / area - cx * cy
        norm = max(area, 1)
        feats.append((area, h, w, area / (h * w),
                      mu20 / norm, mu02 / norm, mu11 / norm))
    return feats


def kmeans(X, k, rng, iters=40, restarts=3):
    best, best_inertia = None, np.inf
    for _ in range(restarts):
        C = X[rng.choice(len(X), k, replace=False)]
        for _ in range(iters):
            d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(2)
            lab = d.argmin(1)
            newC = np.array([X[lab == j].mean(0) if (lab == j).any()
                             else C[j] for j in range(k)])
            if np.allclose(newC, C):
                break
            C = newC
        inertia = ((X - C[lab]) ** 2).sum()
        if inertia < best_inertia:
            best_inertia, best = inertia, (C, lab)
    return best


def silhouette(X, lab, rng):
    idx = rng.choice(len(X), min(SIL_SAMPLE, len(X)), replace=False)
    Xs, ls = X[idx], lab[idx]
    D = np.sqrt(((Xs[:, None, :] - Xs[None, :, :]) ** 2).sum(2))
    out = []
    for i in range(len(Xs)):
        same = ls == ls[i]
        same[i] = False
        if not same.any():
            continue
        a = D[i][same].mean()
        b = min(D[i][ls == c].mean() for c in set(ls) if c != ls[i])
        out.append((b - a) / max(a, b))
    return float(np.mean(out)) if out else -1.0


# ────────────────────────────────────────────────────────────────────
def main():
    print('=' * 76)
    print('RAW-SCAN GLYPH FEASIBILITY (S2 rung 0) — imaging probe (N8)')
    print('=' * 76)
    print(f'seed={SEED} folios={N_FOLIOS} crop={CROP_FRAC} '
          f'downscale={DOWNSCALE} area=[{AREA_MIN},{AREA_MAX}] '
          f'k_sweep={K_SWEEP}')

    stems = sorted(p.stem for p in FOLIO_DIR.glob('*.png')
                   if (FOLIO_DIR / f'{p.stem}.txt').exists())
    rng = random.Random(SEED)
    sample = sorted(rng.sample(stems, N_FOLIOS))
    nrng = np.random.default_rng(SEED)

    ink_fracs, comp_counts, char_counts, textonly = [], [], [], []
    all_feats, feat_folio = [], []
    for stem in sample:
        a = load_grey(stem)
        t = otsu(a)
        mask = a < t
        ink = float(mask.mean())
        feats = components(mask)
        ink_fracs.append(ink)
        comp_counts.append(len(feats))
        char_counts.append(zl_char_count(stem))
        m = re.match(r'f(\d+)', stem)
        textonly.append(bool(m) and 103 <= int(m.group(1)) <= 116)
        for f in feats:
            all_feats.append(f)
            feat_folio.append(stem)
        print(f'  {stem:<14} ink {ink:.3f}  components {len(feats):>5}  '
              f'ZL chars {char_counts[-1]:>6}'
              + ('  [text-only]' if textonly[-1] else ''))

    # G1
    med_ink = statistics.median(ink_fracs)
    cv_ink = statistics.pstdev(ink_fracs) / statistics.mean(ink_fracs)
    g1 = INK_LO <= med_ink <= INK_HI and cv_ink < INK_CV_MAX
    print(f'\n  G1 binarization: median ink {med_ink:.3f} '
          f'(band [{INK_LO},{INK_HI}]), CV {cv_ink:.2f} '
          f'(< {INK_CV_MAX}) -> {"PASS" if g1 else "FAIL"}')

    # G2
    def spearman(xs, ys):
        def rank(v):
            order = sorted(range(len(v)), key=lambda i: v[i])
            r = [0.0] * len(v)
            for rk, i in enumerate(order):
                r[i] = rk
            return r
        rx, ry = rank(xs), rank(ys)
        n = len(xs)
        mx, my = sum(rx) / n, sum(ry) / n
        num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        den = math.sqrt(sum((a - mx) ** 2 for a in rx)
                        * sum((b - my) ** 2 for b in ry))
        return num / den if den else 0.0

    rho_all = round(spearman(comp_counts, char_counts), 3)
    to_c = [c for c, t in zip(comp_counts, textonly) if t]
    to_z = [z for z, t in zip(char_counts, textonly) if t]
    rho_text = (round(spearman(to_c, to_z), 3) if len(to_c) >= 5
                else None)
    print(f'  G2 segmentation: Spearman(components, ZL chars) all '
          f'{rho_all:+.3f} (strong >= {G2_STRONG}); text-only folios '
          f'(n={len(to_c)}): '
          + (f'{rho_text:+.3f}' if rho_text is not None else 'n<5'))

    # G3
    X = np.array([list(f) for f in all_feats], dtype=np.float64)
    X[:, 0] = np.log(X[:, 0])
    X = np.hstack([X, (X[:, 1] / np.maximum(X[:, 2], 1))[:, None]])
    X = (X - X.mean(0)) / np.maximum(X.std(0), 1e-9)
    if len(X) > MAX_COMPONENTS:
        keep = nrng.choice(len(X), MAX_COMPONENTS, replace=False)
        X, feat_folio = X[keep], [feat_folio[i] for i in keep]
    half_f = set(sample[:len(sample) // 2])
    m1 = np.array([f in half_f for f in feat_folio])
    ks, cds = {}, None
    halves = [X[m1], X[~m1]]
    kstar = []
    for hi, Xh in enumerate(halves):
        best_k, best_s = None, -2
        for k in K_SWEEP:
            C, lab = kmeans(Xh, k, nrng)
            s = silhouette(Xh, lab, nrng)
            if s > best_s:
                best_s, best_k = s, k
            ks.setdefault(k, []).append((C, lab))
        kstar.append(best_k)
        print(f'  G3 half {hi + 1}: n={len(Xh)}, silhouette-best '
              f'k* = {best_k} (s={best_s:.3f})')
    g3a = abs(kstar[0] - kstar[1]) / max((kstar[0] + kstar[1]) / 2,
                                         1) <= 0.30
    C1, C2 = ks[K_REF][0][0], ks[K_REF][1][0]
    d = np.sqrt(((C1[:, None, :] - C2[None, :, :]) ** 2).sum(2))
    matched = []
    used = set()
    for i in np.argsort(d.min(1)):
        j = min((jj for jj in range(len(C2)) if jj not in used),
                key=lambda jj: d[i, jj])
        used.add(j)
        matched.append(d[i, j])
    within = np.sqrt(((C1[:, None, :] - C1[None, :, :]) ** 2)
                     .sum(2))[np.triu_indices(len(C1), 1)].mean()
    ratio = float(np.mean(matched) / within)
    g3b = ratio < CENTROID_RATIO_MAX
    print(f'  G3a k* stability: {kstar[0]} vs {kstar[1]} '
          f'-> {"PASS" if g3a else "FAIL"} (±30% rule)')
    print(f'  G3b centroid match ratio at k={K_REF}: {ratio:.3f} '
          f'(< {CENTROID_RATIO_MAX}) -> {"PASS" if g3b else "FAIL"}')

    # ── pre-registered adjudication ─────────────────────────────────
    print('\n  ADJUDICATION (pre-registered):')
    if g1 and rho_all >= G2_STRONG and g3a and g3b:
        verdict = 'feasible'
        print('    FEASIBLE: the naive pipeline binarizes stably, sees '
              'what the transcribers saw, and clusters reproducibly — '
              'S2 proper is worth building.')
    elif g1 and (rho_all >= G2_WEAK or (rho_text is not None
                                        and rho_text >= G2_STRONG)):
        verdict = 'partially_feasible'
        blockers = []
        if rho_all < G2_STRONG:
            blockers.append(f'all-folio correlation {rho_all:+.3f} < '
                            f'{G2_STRONG} (drawings confound)')
        if not g3a:
            blockers.append('k* unstable across halves')
        if not g3b:
            blockers.append(f'centroid ratio {ratio:.2f}')
        print('    PARTIALLY FEASIBLE: proceed restricted (text-only '
              'pages and/or better tooling). Blockers: '
              + '; '.join(blockers) + '.')
    else:
        verdict = 'infeasible_at_this_quality'
        print('    INFEASIBLE AT THIS QUALITY: the pipeline does not '
              'reliably see the text (F10) — S2 is starved pending '
              'better scans or a real CV stack.')

    with open(result_path('scan_glyph_feasibility.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'params': {'seed': SEED, 'n_folios': N_FOLIOS,
                              'crop_frac': CROP_FRAC,
                              'downscale': DOWNSCALE,
                              'area_band': [AREA_MIN, AREA_MAX],
                              'ink_band': [INK_LO, INK_HI],
                              'ink_cv_max': INK_CV_MAX,
                              'g2_strong': G2_STRONG,
                              'g2_weak': G2_WEAK,
                              'k_sweep': K_SWEEP, 'k_ref': K_REF,
                              'centroid_ratio_max': CENTROID_RATIO_MAX},
                   'results': {'sample': sample,
                               'ink': {'median': round(med_ink, 4),
                                       'cv': round(cv_ink, 3),
                                       'pass': g1},
                               'g2': {'rho_all': rho_all,
                                      'rho_textonly': rho_text,
                                      'n_textonly': len(to_c)},
                               'g3': {'kstar': kstar, 'g3a': g3a,
                                      'centroid_ratio': round(ratio, 3),
                                      'g3b': g3b},
                               'n_components_total': len(all_feats)},
                   'verdict': verdict},
                  fh, indent=1)
    print('\n  -> results/scan_glyph_feasibility.json')


if __name__ == '__main__':
    main()
