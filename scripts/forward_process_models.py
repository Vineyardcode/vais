#!/usr/bin/env python3
"""
FORWARD MODELING: WHAT PROCESS REPRODUCES THE VMS FINGERPRINT?
===========================================================================

cross_script_fingerprint established that VMS has:
  - NORMAL word-level statistics (TTR, hapax, word length: all z<1.1)
  - EXTREME character-level anomalies (H(c|prev) z=−19.9, H-ratio z=−12.6)

This is a constructive test: take a real natural-language text (Italian,
historically plausible), apply different encoding transformations, and
measure which scheme(s) reproduce the VMS fingerprint.

TARGET (VMS):
  alpha_size  = 32      H(char)    = 3.86    H(char|prev) = 2.47
  H_ratio     = 0.64    IC         = 0.082   mean_wlen    = 4.94
  TTR         = 0.27    hapax_ratio= 0.66    V_frac       = 0.28
  VC_alt      = 0.73

Encoding schemes tested:
  1) SYLLABIC ENCODING — syllabify Italian, map each syllable → fixed
     2-3 char sequence from ~25-char alphabet. Preserves word boundaries.
  2) ONSET-RIME ENCODING — decompose syllable into onset + rime,
     encode each component separately with a small alphabet per slot.
  3) VERBOSE POSITIONAL — each source letter → 1 or 2 cipher chars;
     vowels → 2 chars (from small set), consonants → 1 char.
  4) SELF-CITING ABBREVIATION — common words get fixed short codes,
     uncommon words spelled out with a character mapping. This produces
     stereotyped token patterns (like VMS's repeated word structures).
  5) BENCHMARK: simple substitution (should NOT match VMS — confirms
     cross_script_fingerprint finding).

Source text: Italian (Dante, Inferno — Gutenberg #1012).
"""

import re, sys, io, math, random, json, string
from pathlib import Path
from collections import Counter, defaultdict
import urllib.request
import numpy as np
from common import eva_to_glyphs_v2 as eva_to_glyphs, fetch_gutenberg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdout.reconfigure(line_buffering=True)

random.seed(59)
np.random.seed(59)

_print = print
def pr(s=''):
    _print(s)
    sys.stdout.flush()

# ─── Metrics (reused from cross_script_fingerprint) ───────────────────────────────────

def compute_metrics(words, chars, name='', max_tokens=10000):
    """Compute the 10-feature fingerprint."""
    nb_chars = [c for c in chars if c != ' ']
    if len(nb_chars) < 200:
        return None

    alphabet = set(nb_chars)
    alpha_size = len(alphabet)

    counts = Counter(nb_chars)
    total = sum(counts.values())
    H_char = -sum((n/total)*math.log2(n/total) for n in counts.values())

    bigram_counts = defaultdict(Counter)
    for i in range(1, len(nb_chars)):
        bigram_counts[nb_chars[i-1]][nb_chars[i]] += 1
    H_cond = 0.0
    for prev_char, nexts in bigram_counts.items():
        prev_total = sum(nexts.values())
        p_prev = prev_total / (total - 1)
        h_local = -sum((n/prev_total)*math.log2(n/prev_total)
                       for n in nexts.values())
        H_cond += p_prev * h_local

    H_ratio = H_cond / H_char if H_char > 0 else 0
    IC = sum(n*(n-1) for n in counts.values()) / (total*(total-1)) if total > 1 else 0
    mean_wlen = np.mean([len(w) for w in words]) if words else 0

    std_words = words[:max_tokens]
    std_n = len(std_words)
    ttr = len(set(std_words)) / std_n if std_n > 0 else 0

    std_counts = Counter(std_words)
    hapax = sum(1 for c in std_counts.values() if c == 1)
    hapax_ratio = hapax / len(std_counts) if std_counts else 0

    v_count, v_set = sukhotin(nb_chars, alphabet)
    v_frac = v_count / alpha_size if alpha_size > 0 else 0
    alt_rate = vc_alternation(nb_chars, v_set)

    return {
        'name': name,
        'alpha_size': alpha_size,
        'H_char': H_char,
        'H_cond': H_cond,
        'H_ratio': H_ratio,
        'IC': IC,
        'mean_wlen': mean_wlen,
        'TTR': ttr,
        'hapax_ratio': hapax_ratio,
        'V_frac': v_frac,
        'VC_alt': alt_rate,
        'n_chars': len(nb_chars),
        'n_words': len(words),
        'n_types': len(set(words)),
    }

def sukhotin(chars, alphabet):
    alpha_list = sorted(alphabet)
    n = len(alpha_list)
    idx = {c: i for i, c in enumerate(alpha_list)}
    adj = np.zeros((n, n), dtype=float)
    for i in range(1, len(chars)):
        a, b = chars[i-1], chars[i]
        if a in idx and b in idx and a != b:
            adj[idx[a]][idx[b]] += 1
            adj[idx[b]][idx[a]] += 1
    row_sums = adj.sum(axis=1)
    vowels = set()
    remaining = set(range(n))
    for _ in range(n):
        best = -1; best_val = 0
        for r in remaining:
            if row_sums[r] > best_val:
                best_val = row_sums[r]; best = r
        if best < 0 or best_val <= 0: break
        vowels.add(best)
        remaining.discard(best)
        for r in remaining:
            row_sums[r] -= 2 * adj[best][r]
    v_set = {alpha_list[i] for i in vowels}
    return len(v_set), v_set

def vc_alternation(chars, vowels):
    if len(chars) < 2: return 0
    transitions = sum(1 for i in range(1, len(chars))
                      if (chars[i-1] in vowels) != (chars[i] in vowels))
    return transitions / (len(chars) - 1)

# ─── VMS loading ─────────────────────────────────────────────────────

FOLIO_DIR = Path("folios")


def load_vms():
    words_all = []
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'): continue
            m = re.match(r'<([^>]+)>', line)
            rest = line[m.end():].strip() if m else line
            if not rest: continue
            ws = [w.strip() for w in re.split(r'[.\s,;]+', rest)
                  if w.strip() and re.match(r'^[a-z]+$', w.strip())]
            words_all.extend(ws)
    return words_all

def vms_char_sequence(words):
    seq = []
    for w in words:
        seq.extend(eva_to_glyphs(w))
        seq.append(' ')
    return seq

# ─── Source text loader ──────────────────────────────────────────────


def load_italian():
    """Load Italian text (Dante, Inferno), return words list."""
    raw = fetch_gutenberg(1012)
    text = raw.lower()
    # Keep only Italian letters
    text = re.sub(r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþß]+', ' ', text)
    words = [w for w in text.split() if len(w) >= 1]
    return words[:50000]

# ─── Italian syllabifier ────────────────────────────────────────────

ITALIAN_VOWELS = set('aeiouàáâãäåèéêëìíîïòóôõöùúûüý')

def syllabify_italian(word):
    """
    Simple rule-based Italian syllabification.
    Rules:
      - V alone is a syllable nucleus
      - Split between VV (unless diphthong)
      - Split between VC.CV
      - Split between VCC.CV (keep onset clusters)
      - Never split common onsets: bl, br, cl, cr, dr, fl, fr, gl, gr,
        pl, pr, sb, sc, sf, sg, sl, sm, sn, sp, sq, sr, st, str, sv, tr, vr
    """
    ONSETS = {'bl','br','cl','cr','dr','fl','fr','gl','gr','gn',
              'pl','pr','sb','sc','sf','sg','sl','sm','sn','sp',
              'sq','sr','st','sv','tr','vr','str','spr','scr',
              'spl','chr','shr','sch'}

    chars = list(word)
    n = len(chars)
    if n <= 1:
        return [word]

    is_v = [c in ITALIAN_VOWELS for c in chars]

    # Find syllable boundaries
    boundaries = []  # indices where a new syllable starts
    i = 0
    while i < n:
        if not is_v[i]:
            i += 1
            continue
        # Found a vowel — this is a nucleus
        # Look ahead for the end of this syllable
        j = i + 1
        # Skip additional vowels in diphthong (simplified: max 2 vowels together)
        if j < n and is_v[j]:
            # Check if this is a "split" vowel pair
            # Italian splits: ae, ao, ea, eo, ia (sometimes), oa, oe, etc.
            # Simplified: treat consecutive vowels as same syllable
            j += 1

        # Now j points at first consonant after nucleus (or end)
        # Count consonants
        cons_start = j
        while j < n and not is_v[j]:
            j += 1

        if j >= n:
            # Word ends with consonants — they belong to current syllable
            break

        # j points at next vowel. Consonant cluster is chars[cons_start:j]
        cons_cluster = ''.join(chars[cons_start:j])
        cluster_len = j - cons_start

        if cluster_len == 0:
            # VV — split
            boundaries.append(j)
        elif cluster_len == 1:
            # V.CV — consonant goes with next vowel
            boundaries.append(cons_start)
        elif cluster_len >= 2:
            # Check if entire cluster is a valid onset
            if cons_cluster in ONSETS:
                boundaries.append(cons_start)
            else:
                # Check if last 2 or 3 chars form a valid onset
                found = False
                for onset_len in [3, 2]:
                    if onset_len <= cluster_len:
                        candidate = cons_cluster[-onset_len:]
                        if candidate in ONSETS:
                            boundaries.append(j - onset_len)
                            found = True
                            break
                if not found:
                    # Split: first consonant(s) go with prev, last goes with next
                    boundaries.append(j - 1)

        i = j

    # Build syllable strings
    if not boundaries:
        return [word]

    syllables = []
    prev = 0
    for b in sorted(set(boundaries)):
        if b > prev:
            syllables.append(word[prev:b])
        prev = b
    if prev < n:
        syllables.append(word[prev:])
    return [s for s in syllables if s]

# ─── Encoding scheme 1: SYLLABIC ENCODING ───────────────────────────

def encode_syllabic(words, alpha_size=25, syl_len_range=(2, 3)):
    """
    Syllabify each word, map each unique syllable to a fixed random
    character sequence from a constrained alphabet.
    """
    ALPHA = [chr(ord('a') + i) for i in range(alpha_size)]

    # Syllabify all words, collect unique syllables
    word_syls = []
    all_syls = Counter()
    for w in words:
        syls = syllabify_italian(w)
        word_syls.append(syls)
        for s in syls:
            all_syls[s] += 1

    # Map each syllable to a random char sequence
    # More common syllables get shorter codes (2 chars), rare ones get 3
    syl_list = sorted(all_syls.keys(), key=lambda s: all_syls[s], reverse=True)
    syl_map = {}
    used = set()
    for i, syl in enumerate(syl_list):
        code_len = syl_len_range[0] if i < len(syl_list) // 3 else syl_len_range[1]
        # Generate a unique code
        for _ in range(1000):
            code = ''.join(random.choice(ALPHA) for _ in range(code_len))
            if code not in used:
                used.add(code)
                syl_map[syl] = code
                break
        else:
            # Fallback: use longer code
            code = ''.join(random.choice(ALPHA) for _ in range(code_len + 1))
            syl_map[syl] = code

    # Encode words
    enc_words = []
    enc_chars = []
    for syls in word_syls:
        w_chars = []
        for s in syls:
            w_chars.extend(list(syl_map.get(s, s)))
        enc_words.append(''.join(w_chars))
        enc_chars.extend(w_chars)
        enc_chars.append(' ')

    return enc_words, enc_chars

# ─── Encoding scheme 2: ONSET-RIME ENCODING ─────────────────────────

def encode_onset_rime(words, n_onset_chars=10, n_rime_chars=12):
    """
    Decompose each syllable into onset (leading consonants) and rime
    (vowel + trailing consonants). Encode onset and rime separately
    with distinct character sets, maintaining CV alternation.
    """
    ONSET_ALPHA = [chr(ord('a') + i) for i in range(n_onset_chars)]
    RIME_ALPHA = [chr(ord('a') + n_onset_chars + i) for i in range(n_rime_chars)]

    # Collect all unique onsets and rimes
    all_onsets = Counter()
    all_rimes = Counter()
    word_parts = []

    for w in words:
        syls = syllabify_italian(w)
        parts = []
        for s in syls:
            # Split into onset + rime
            onset = ''
            rime = s
            for k, c in enumerate(s):
                if c in ITALIAN_VOWELS:
                    onset = s[:k]
                    rime = s[k:]
                    break
            all_onsets[onset] += 1
            all_rimes[rime] += 1
            parts.append((onset, rime))
        word_parts.append(parts)

    # Map onsets → 1 onset char, rimes → 1-2 rime chars
    onset_list = sorted(all_onsets.keys(), key=lambda x: all_onsets[x], reverse=True)
    rime_list = sorted(all_rimes.keys(), key=lambda x: all_rimes[x], reverse=True)

    onset_map = {}
    for i, o in enumerate(onset_list):
        if not o:  # empty onset (vowel-initial syllable)
            onset_map[o] = ''
        else:
            onset_map[o] = ONSET_ALPHA[i % len(ONSET_ALPHA)]

    rime_map = {}
    for i, r in enumerate(rime_list):
        if i < len(RIME_ALPHA):
            rime_map[r] = RIME_ALPHA[i]
        else:
            # Use 2-char code for rare rimes
            rime_map[r] = RIME_ALPHA[i % len(RIME_ALPHA)] + RIME_ALPHA[(i * 7) % len(RIME_ALPHA)]

    # Encode
    enc_words = []
    enc_chars = []
    for parts in word_parts:
        w_chars = []
        for onset, rime in parts:
            w_chars.extend(list(onset_map.get(onset, '')))
            w_chars.extend(list(rime_map.get(rime, rime)))
        enc_words.append(''.join(w_chars))
        enc_chars.extend(w_chars)
        enc_chars.append(' ')

    return enc_words, enc_chars

# ─── Encoding scheme 3: VERBOSE POSITIONAL CIPHER ───────────────────

def encode_verbose_positional(words, vowel_expand=True, context_vary=False):
    """
    Each source letter maps to 1-2 cipher characters.
    Vowels → 2 chars (consonant + vowel-marker from small set).
    Consonants → 1 char.

    This creates predictable bigram patterns within each vowel encoding.
    If context_vary=True, the vowel encoding depends on the preceding
    consonant, further constraining bigrams.
    """
    # Italian alphabet
    SRC_VOWELS = set('aeiouàèéìòù')
    SRC_CONSONANTS = set('bcdfghlmnpqrstvz')

    # Cipher alphabet: ~8 "consonant" chars + ~5 "vowel" chars
    C_CHARS = list('bcdfghkl')   # 8
    V_CHARS = list('aeiou')       # 5

    # Map source consonants → cipher consonants
    src_cons = sorted(SRC_CONSONANTS)
    cons_map = {c: C_CHARS[i % len(C_CHARS)] for i, c in enumerate(src_cons)}

    # Map source vowels → cipher vowel pairs (C_char + V_char)
    # Each vowel becomes a fixed 2-char sequence
    src_vowels = sorted(SRC_VOWELS)
    vowel_map = {}
    for i, v in enumerate(src_vowels):
        if context_vary:
            # Base vowel encoding — will be modified by context
            vowel_map[v] = (i % len(C_CHARS), i % len(V_CHARS))
        else:
            c1 = C_CHARS[i % len(C_CHARS)]
            c2 = V_CHARS[i % len(V_CHARS)]
            vowel_map[v] = c1 + c2

    enc_words = []
    enc_chars = []
    for w in words:
        w_chars = []
        prev_c = 0
        for j, c in enumerate(w):
            if c in SRC_VOWELS:
                if context_vary:
                    base_c, base_v = vowel_map[c]
                    # Modify by preceding consonant context
                    c1 = C_CHARS[(base_c + prev_c) % len(C_CHARS)]
                    c2 = V_CHARS[base_v]
                    w_chars.extend([c1, c2])
                elif vowel_expand:
                    w_chars.extend(list(vowel_map[c]))
                else:
                    w_chars.append(V_CHARS[src_vowels.index(c) % len(V_CHARS)])
            elif c in SRC_CONSONANTS:
                mapped = cons_map[c]
                w_chars.append(mapped)
                prev_c = C_CHARS.index(mapped)
            # else: skip character
        if w_chars:
            enc_words.append(''.join(w_chars))
            enc_chars.extend(w_chars)
            enc_chars.append(' ')

    return enc_words, enc_chars

# ─── Encoding scheme 4: SELF-CITING ABBREVIATION ────────────────────

def encode_abbreviation(words, top_n=200, alpha_size=22):
    """
    The most common N words get fixed short codes (2-4 chars).
    All other words are encoded letter-by-letter with a simple mapping.
    This produces a vocabulary with many stereotyped short tokens
    (like VMS's repeated qokeedy, daiin, etc.) mixed with more varied
    rare tokens.
    """
    ALPHA = [chr(ord('a') + i) for i in range(alpha_size)]

    # Count word frequencies
    wfreq = Counter(words)
    # Top N words get fixed codes
    top_words = [w for w, _ in wfreq.most_common(top_n)]

    # Generate short codes for top words
    word_codes = {}
    used = set()
    for i, w in enumerate(top_words):
        code_len = 2 if i < 20 else (3 if i < 80 else 4)
        for _ in range(1000):
            code = ''.join(random.choice(ALPHA) for _ in range(code_len))
            if code not in used:
                used.add(code)
                word_codes[w] = code
                break

    # Letter-level mapping for uncommon words
    src_alpha = sorted(set(c for w in words for c in w))
    letter_map = {}
    for i, c in enumerate(src_alpha):
        letter_map[c] = ALPHA[i % alpha_size]

    enc_words = []
    enc_chars = []
    for w in words:
        if w in word_codes:
            code = word_codes[w]
        else:
            code = ''.join(letter_map.get(c, c) for c in w)
        enc_words.append(code)
        enc_chars.extend(list(code))
        enc_chars.append(' ')

    return enc_words, enc_chars

# ─── Encoding scheme 5: simple substitution (benchmark) ─────────────

def encode_simple_subst(words):
    """1:1 letter substitution. Should NOT match VMS (cross_script_fingerprint confirmed)."""
    all_chars = sorted(set(c for w in words for c in w))
    shuffled = all_chars[:]
    random.shuffle(shuffled)
    mapping = dict(zip(all_chars, shuffled))
    enc_words = [''.join(mapping.get(c, c) for c in w) for w in words]
    enc_chars = []
    for w in enc_words:
        enc_chars.extend(list(w))
        enc_chars.append(' ')
    return enc_words, enc_chars

# ─── Encoding scheme 6: SYLLABIC with frequency-tuned params ────────

def encode_syllabic_tuned(words, alpha_size=30, common_len=2, rare_len=3,
                          common_frac=0.5):
    """
    Like scheme 1, but tuned to VMS-like parameters:
    - alpha_size ~30 (matching VMS's 32)
    - Common syllables get 2-char codes, rare get 3-char
    - Controlled to produce ~5-char mean word length
    """
    ALPHA = [chr(ord('a') + i) for i in range(min(alpha_size, 26))]
    if alpha_size > 26:
        ALPHA += [chr(0x100 + i) for i in range(alpha_size - 26)]

    word_syls = []
    all_syls = Counter()
    for w in words:
        syls = syllabify_italian(w)
        word_syls.append(syls)
        for s in syls:
            all_syls[s] += 1

    syl_list = sorted(all_syls.keys(), key=lambda s: all_syls[s], reverse=True)
    n_common = int(len(syl_list) * common_frac)

    syl_map = {}
    used = set()
    for i, syl in enumerate(syl_list):
        code_len = common_len if i < n_common else rare_len
        for _ in range(2000):
            code = ''.join(random.choice(ALPHA) for _ in range(code_len))
            if code not in used:
                used.add(code)
                syl_map[syl] = code
                break
        else:
            code = ''.join(random.choice(ALPHA) for _ in range(code_len + 1))
            syl_map[syl] = code

    enc_words = []
    enc_chars = []
    for syls in word_syls:
        w_chars = []
        for s in syls:
            w_chars.extend(list(syl_map.get(s, s)))
        enc_words.append(''.join(w_chars))
        enc_chars.extend(w_chars)
        enc_chars.append(' ')

    return enc_words, enc_chars

# ─── Distance calculation ───────────────────────────────────────────

FEATURE_KEYS = ['alpha_size', 'H_char', 'H_cond', 'H_ratio', 'IC',
                'mean_wlen', 'TTR', 'hapax_ratio', 'V_frac', 'VC_alt']

def feature_vec(m):
    return np.array([m[k] for k in FEATURE_KEYS])

def z_score_distance(vms_vec, test_vec, nl_mu, nl_sigma):
    """Distance in z-score space (normalized by NL distribution)."""
    z_vms = (vms_vec - nl_mu) / nl_sigma
    z_test = (test_vec - nl_mu) / nl_sigma
    return np.sqrt(np.sum((z_vms - z_test)**2))

# ─── Main ────────────────────────────────────────────────────────────

def main():
    pr("=" * 70)
    pr("forward_process_models: FORWARD MODELING — WHAT REPRODUCES THE VMS FINGERPRINT?")
    pr("=" * 70)
    pr()

    # ── Load VMS ──
    pr("Loading VMS corpus...")
    vms_words = load_vms()
    vms_chars = vms_char_sequence(vms_words)
    vms_m = compute_metrics(vms_words, vms_chars, name='VMS (target)')
    pr(f"  VMS: {vms_m['n_words']} words, {vms_m['n_chars']} chars")
    pr(f"  H(c)={vms_m['H_char']:.3f}, H(c|p)={vms_m['H_cond']:.3f}, "
       f"H-ratio={vms_m['H_ratio']:.3f}, IC={vms_m['IC']:.4f}")
    pr()

    # ── Load cross_script_fingerprint NL reference stats for z-score normalization ──
    pr("Loading cross_script_fingerprint reference data...")
    try:
        with open('results/cross_script_fingerprint_output.json') as f:
            p58 = json.load(f)
        nl_names = ['English', 'Latin', 'Italian', 'German', 'Spanish', 'French', 'Finnish']
        nl_vecs = []
        for lang in nl_names:
            if lang in p58:
                nl_vecs.append(np.array([p58[lang][k] for k in FEATURE_KEYS]))
        nl_matrix = np.array(nl_vecs)
        nl_mu = nl_matrix.mean(axis=0)
        nl_sigma = nl_matrix.std(axis=0)
        nl_sigma[nl_sigma == 0] = 1
        pr(f"  Loaded {len(nl_vecs)} NL references for normalization")
    except Exception as e:
        pr(f"  WARNING: Could not load cross_script_fingerprint data ({e}), using raw distances")
        nl_mu = np.zeros(len(FEATURE_KEYS))
        nl_sigma = np.ones(len(FEATURE_KEYS))
    pr()

    # ── Load Italian source text ──
    pr("Fetching Italian source text (Dante, Inferno)...")
    ita_words = load_italian()
    pr(f"  Italian: {len(ita_words)} words, {len(set(ita_words))} types")

    # Compute Italian baseline metrics
    ita_chars = []
    for w in ita_words:
        ita_chars.extend(list(w))
        ita_chars.append(' ')
    ita_m = compute_metrics(ita_words, ita_chars, name='Italian (source)')
    pr(f"  H(c)={ita_m['H_char']:.3f}, H(c|p)={ita_m['H_cond']:.3f}, "
       f"IC={ita_m['IC']:.4f}, MWL={ita_m['mean_wlen']:.2f}")
    pr()

    # ── Test encoding schemes ──
    results = {'VMS': vms_m, 'Italian_source': ita_m}

    schemes = [
        ("1: Syllabic (α=25)",
         lambda: encode_syllabic(ita_words, alpha_size=25)),
        ("2: Onset-rime (10+12)",
         lambda: encode_onset_rime(ita_words, n_onset_chars=10, n_rime_chars=12)),
        ("3a: Verbose positional",
         lambda: encode_verbose_positional(ita_words, vowel_expand=True, context_vary=False)),
        ("3b: Verbose context-vary",
         lambda: encode_verbose_positional(ita_words, vowel_expand=True, context_vary=True)),
        ("4: Abbreviation (top200)",
         lambda: encode_abbreviation(ita_words, top_n=200, alpha_size=22)),
        ("5: Simple substitution",
         lambda: encode_simple_subst(ita_words)),
        ("6a: Syllabic tuned (α=30)",
         lambda: encode_syllabic_tuned(ita_words, alpha_size=30)),
        ("6b: Syllabic tuned (α=26, 50% short)",
         lambda: encode_syllabic_tuned(ita_words, alpha_size=26, common_len=2,
                                        rare_len=3, common_frac=0.5)),
        ("6c: Syllabic (α=20, longer codes)",
         lambda: encode_syllabic_tuned(ita_words, alpha_size=20, common_len=3,
                                        rare_len=4, common_frac=0.4)),
    ]

    pr("=" * 70)
    pr("A) ENCODING SCHEME RESULTS")
    pr("=" * 70)
    pr()

    vms_vec = feature_vec(vms_m)

    for name, encoder in schemes:
        pr(f"  Encoding: {name}")
        try:
            enc_w, enc_c = encoder()
            m = compute_metrics(enc_w, enc_c, name=name)
            if m is None:
                pr(f"    FAILED: too few characters")
                continue
            results[name] = m
            dist_raw = np.sqrt(np.sum((feature_vec(m) - vms_vec)**2))
            dist_z = z_score_distance(vms_vec, feature_vec(m), nl_mu, nl_sigma)
            pr(f"    α={m['alpha_size']:>3d}  H(c)={m['H_char']:.3f}  "
               f"H(c|p)={m['H_cond']:.3f}  H-rat={m['H_ratio']:.3f}  "
               f"IC={m['IC']:.4f}  MWL={m['mean_wlen']:.2f}")
            pr(f"    TTR={m['TTR']:.4f}  Hapax={m['hapax_ratio']:.3f}  "
               f"V-fr={m['V_frac']:.3f}  V/C-alt={m['VC_alt']:.3f}")
            pr(f"    Distance from VMS: raw={dist_raw:.3f}, z-normalized={dist_z:.3f}")
        except Exception as e:
            pr(f"    ERROR: {e}")
        pr()

    # ── Comparison table ──
    pr("=" * 70)
    pr("B) DISTANCE RANKING (z-score normalized)")
    pr("=" * 70)
    pr()

    ranking = []
    for key, m in results.items():
        if m is None or key == 'VMS':
            continue
        dist_z = z_score_distance(vms_vec, feature_vec(m), nl_mu, nl_sigma)
        ranking.append((dist_z, key, m))
    ranking.sort()

    hdr = (f"{'Rank':<5s} {'Scheme':<35s} {'Dist':>7s} "
           f"{'H(c|p)':>7s} {'H-rat':>7s} {'IC':>7s} {'MWL':>7s} {'α':>4s}")
    pr(hdr)
    pr("-" * len(hdr))
    for i, (dist, key, m) in enumerate(ranking):
        pr(f"{i+1:<5d} {m['name']:<35s} {dist:>7.3f} "
           f"{m['H_cond']:>7.3f} {m['H_ratio']:>7.3f} "
           f"{m['IC']:>7.4f} {m['mean_wlen']:>7.2f} {m['alpha_size']:>4d}")
    pr()

    # VMS reference line
    pr(f"{'':5s} {'VMS (TARGET)':35s} {'0.000':>7s} "
       f"{vms_m['H_cond']:>7.3f} {vms_m['H_ratio']:>7.3f} "
       f"{vms_m['IC']:>7.4f} {vms_m['mean_wlen']:>7.2f} {vms_m['alpha_size']:>4d}")
    pr()

    # ── Feature-by-feature analysis of best match ──
    pr("=" * 70)
    pr("C) FEATURE-BY-FEATURE: BEST ENCODING vs VMS")
    pr("=" * 70)
    pr()

    if ranking:
        best_dist, best_key, best_m = ranking[0]
        pr(f"Best match: {best_m['name']} (distance {best_dist:.3f})")
        pr()

        pr(f"{'Feature':<16s} {'VMS':>8s} {'Best':>8s} {'Delta':>8s} {'NL mean':>8s} {'VMS z':>8s} {'Best z':>8s}")
        pr("-" * 68)
        for j, fk in enumerate(FEATURE_KEYS):
            v = vms_m[fk]
            b = best_m[fk]
            z_v = (v - nl_mu[j]) / nl_sigma[j]
            z_b = (b - nl_mu[j]) / nl_sigma[j]
            pr(f"  {fk:<14s} {v:>8.3f} {b:>8.3f} {b-v:>+8.3f} {nl_mu[j]:>8.3f} {z_v:>+8.2f} {z_b:>+8.2f}")
        pr()

    # ── Critical assessment ──
    pr("=" * 70)
    pr("D) CRITICAL ASSESSMENT")
    pr("=" * 70)
    pr()

    # Characterize what worked and what didn't
    # Identify which encoding dimension(s) are closest/farthest
    if ranking:
        best_dist, best_key, best_m = ranking[0]
        worst_dist, worst_key, worst_m = ranking[-1]

        pr(f"Closest to VMS:  {best_m['name']} (d={best_dist:.3f})")
        pr(f"Farthest:        {worst_m['name']} (d={worst_dist:.3f})")
        pr()

        # What features does the best match get right/wrong?
        best_vec = feature_vec(best_m)
        vms_z = (vms_vec - nl_mu) / nl_sigma
        best_z = (best_vec - nl_mu) / nl_sigma

        matched = []
        mismatched = []
        for j, fk in enumerate(FEATURE_KEYS):
            delta_z = abs(vms_z[j] - best_z[j])
            if delta_z < 2.0:
                matched.append((fk, delta_z))
            else:
                mismatched.append((fk, delta_z, vms_z[j], best_z[j]))

        pr("Features the best encoding MATCHES (Δz < 2):")
        for fk, dz in sorted(matched, key=lambda x: x[1]):
            pr(f"  {fk}: Δz = {dz:.2f}")
        pr()

        if mismatched:
            pr("Features the best encoding MISSES (Δz ≥ 2):")
            for fk, dz, vz, bz in sorted(mismatched, key=lambda x: -x[1]):
                direction = "too high" if bz > vz else "too low"
                pr(f"  {fk}: Δz = {dz:.2f} (VMS z={vz:.1f}, best z={bz:.1f}, {direction})")
            pr()

    # ── Does ANY scheme land in the VMS zone? ──
    pr("=" * 70)
    pr("E) SYNTHESIS")
    pr("=" * 70)
    pr()

    # Count how many schemes are closer to VMS than any NL is
    if ranking:
        # cross_script_fingerprint: nearest NL to VMS was Spanish at ~2.3 (z-normalized)
        closer_than_nl = [(d, k, m) for d, k, m in ranking if d < 2.3]
        pr(f"Schemes closer to VMS than nearest NL (Spanish, d=2.30):")
        if closer_than_nl:
            for d, k, m in closer_than_nl:
                pr(f"  {m['name']}: d={d:.3f}")
        else:
            pr(f"  NONE — no encoding scheme gets closer to VMS than "
               f"Spanish does")
        pr()

    # The key H(c|prev) comparison
    pr("The critical metric — H(char|prev):")
    pr(f"  VMS target:     {vms_m['H_cond']:.3f}")
    for d, k, m in ranking[:5]:
        pr(f"  {m['name']:<35s} {m['H_cond']:.3f}")
    pr(f"  NL mean:        {nl_mu[FEATURE_KEYS.index('H_cond')]:.3f}")
    pr()

    # Final assessment
    pr("INTERPRETATION:")
    pr()
    if ranking and ranking[0][0] < 2.0:
        pr(f"  The {ranking[0][2]['name']} encoding reproduces the VMS")
        pr(f"  fingerprint well (d={ranking[0][0]:.3f}). This is EVIDENCE")
        pr(f"  that VMS could be produced by this type of process.")
    elif ranking and ranking[0][0] < 3.0:
        pr(f"  The {ranking[0][2]['name']} encoding is the closest match")
        pr(f"  (d={ranking[0][0]:.3f}) but doesn't fully reproduce the VMS")
        pr(f"  fingerprint. The encoding class is PLAUSIBLE but the")
        pr(f"  specific parameters need further tuning.")
    else:
        pr(f"  NO encoding scheme closely matches VMS. Either the")
        pr(f"  encoding process is more exotic than tested, or EVA")
        pr(f"  transcription artifacts dominate the fingerprint.")
    pr()

    # Save results
    out_path = Path("results/forward_process_models_output.json")
    out_path.parent.mkdir(exist_ok=True)
    json_data = {}
    for key, m in results.items():
        if m is None: continue
        json_data[key] = {k: float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v
                          for k, v in m.items()}
    with open(out_path, 'w') as f:
        json.dump(json_data, f, indent=2, default=str)
    pr(f"Results saved to {out_path}")

if __name__ == '__main__':
    main()
