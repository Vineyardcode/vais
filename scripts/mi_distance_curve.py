#!/usr/bin/env python3
"""
MI(d) Text-Meaning-Area Analysis

═══════════════════════════════════════════════════════════════════════

MOTIVATION:

  quimqu (Voynich Ninja thread-5380, "Measuring Long-Range Structure")
  introduced the concept of "text meaning area" vs "generative area":

    MI(d) = mutual information between characters at distance d apart
            in the character stream (including spaces between words).

  For natural language:
    - MI(d) is high at d=1 (within-word correlations)
    - MI(d) decays slowly, staying positive out to d=100+
    - CRUCIALLY: word-shuffled text has LOWER MI that converges faster

  The GAP between raw-text MI(d) and word-shuffled MI(d) at mid-range
  distances = "text meaning area" (TMA). This represents the information
  carried by WORD ORDER — syntax and semantics.

  For GENERATED text (e.g. Torsten Timm's copy-modify):
    - There is NO text meaning area (TMA ≈ 0)
    - The only elevated MI comes from local character correlations
      ("generative area"), not from word-order meaning

  quimqu's findings:
    - VMS Currier A: looks GENERATIVE (TMA ≈ 0, like Torsten Timm)
    - VMS Currier B: shows SMALL positive TMA

  THE KEY EXPERIMENT FOR US:
    Does our verbose cipher (the forward_process_models /
    positional_verbose_cipher model) PRESERVE or DESTROY
    the text-meaning-area when applied to real meaningful text?

    If verbose cipher on real NL text → positive TMA:
      → Cipher preserves word-order structure → supports cipher hypothesis
    If verbose cipher on real NL text → TMA ≈ 0:
      → Cipher destroys meaning signal → model is incomplete

  This is a NOVEL discriminator that no prior test has probed.

APPROACH:
  1. Compute MI(d) for d=1..150 on: VMS (full, A, B), verbose cipher
     output, 6 NL texts, char-shuffled control
  2. Compute word-shuffled MI(d) (average over 10 shuffles) for each
  3. Compute TMA = ∫(raw MI - shuffled MI) for d in [20, 80]
  4. Compare TMA values across text types

SKEPTICISM NOTES:
  - Small texts give noisy MI(d) at large d; must check sample sizes
  - The integration range [d_start, d_end] matters; test sensitivity
  - Verbose cipher is deterministic per word → same source word always
    produces same cipher word → word-order info IS preserved by design.
    The question is HOW MUCH MI survives the alphabet scrambling.
  - quimqu's original plots used characters, not EVA glyphs; our VMS
    uses EVA glyphs which lump digraphs → fewer symbols → affects MI scale
"""

import re, sys, io, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import random
from common import clean_word, eva_to_glyphs, extract_words, get_currier_language

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
FOLIO_DIR = PROJECT_DIR / 'folios'
DATA_DIR = PROJECT_DIR / 'data'
RESULTS_DIR = PROJECT_DIR / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

OUTPUT = []
def pr(s='', end='\n'):
    print(s, end=end, flush=True)
    OUTPUT.append(str(s) + (end if end != '\n' else '\n'))


# ── EVA glyph tokenizer (from encoding_layer_sweep) ──────────────────────────────

GALLOWS_TRI = ['cth', 'ckh', 'cph', 'cfh']
GALLOWS_BI  = ['ch', 'sh', 'th', 'kh', 'ph', 'fh']



# ── VMS parsing ───────────────────────────────────────────────────────







def parse_vms_by_currier():
    """Parse VMS folios, return dict with 'all', 'A', 'B' word lists (EVA glyph lists)."""
    results = {'all': [], 'A': [], 'B': []}

    folio_files = sorted(FOLIO_DIR.glob('f*.txt'),
                         key=lambda p: int(re.match(r'f(\d+)', p.stem).group(1))
                         if re.match(r'f(\d+)', p.stem) else 0)

    for filepath in folio_files:
        m_num = re.match(r'f(\d+)', filepath.stem)
        if not m_num:
            continue
        folio_num = int(m_num.group(1))
        currier = get_currier_language(folio_num)

        with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                m = re.match(r'<([^>]+)>', line)
                if not m:
                    continue
                tag = m.group(1)
                rest = line[m.end():].strip()
                if not rest:
                    continue
                is_content = '@P' in tag or '*P' in tag or '+P' in tag or '=P' in tag
                if not is_content:
                    continue
                raw_words = extract_words(rest)
                for w in raw_words:
                    glyphs = eva_to_glyphs(w)
                    if glyphs:
                        results['all'].append(glyphs)
                        results[currier].append(glyphs)

    return results


# ── Verbose cipher generator (from encoding_layer_sweep/60) ──────────────────────

def generate_verbose_cipher(source_text, n_zones=3, expand_prob=0.8,
                            n_c_shared=4, n_c_unique=3,
                            n_v_shared=2, n_v_unique=5):
    """Generate a verbose positional cipher from a source text.
    Returns: list of cipher words (each word is a list of cipher chars)."""
    vowels = set('aeiouàèéìòù')
    consonants = set('bcdfghlmnpqrstvz')

    all_c = [chr(ord('A') + i) for i in range(n_c_shared + n_zones * n_c_unique)]
    all_v = [chr(ord('a') + i) for i in range(n_v_shared + n_zones * n_v_unique)]

    zone_c = {}
    zone_v = {}
    for z in range(n_zones):
        shared_c = all_c[:n_c_shared]
        unique_c = all_c[n_c_shared + z*n_c_unique : n_c_shared + (z+1)*n_c_unique]
        zone_c[z] = shared_c + unique_c

        shared_v = all_v[:n_v_shared]
        unique_v = all_v[n_v_shared + z*n_v_unique : n_v_shared + (z+1)*n_v_unique]
        zone_v[z] = shared_v + unique_v

    src_vowels = sorted(vowels & set('aeiou'))
    expanding = {v for v in src_vowels if hash(v) % 100 < expand_prob * 100}

    cipher_words = []
    source_words = re.findall(r'[a-zàèéìòù]+', source_text.lower())

    for word in source_words:
        chars = list(word)
        n = len(chars)
        if n == 0:
            continue
        cipher_word = []
        for pos, ch in enumerate(chars):
            if n == 1:
                z = 0
            elif pos == 0:
                z = 0
            elif pos == n - 1:
                z = n_zones - 1
            else:
                z = min(1, n_zones - 2)

            c_pool = zone_c[z]
            v_pool = zone_v[z]

            if ch in vowels:
                v_idx = ord(ch) % len(v_pool)
                if ch in expanding:
                    c_idx = ord(ch) % len(c_pool)
                    cipher_word.append(c_pool[c_idx])
                    cipher_word.append(v_pool[v_idx])
                else:
                    cipher_word.append(v_pool[v_idx])
            elif ch in consonants:
                c_idx = ord(ch) % len(c_pool)
                cipher_word.append(c_pool[c_idx])

        if cipher_word:
            cipher_words.append(cipher_word)

    return cipher_words


# ── NL text loading ───────────────────────────────────────────────────

def load_nl_text(filepath):
    """Load NL text, return list of words (each word = list of characters)."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read().lower()
    raw_words = re.findall(r'[a-zàèéìòùäöüßâêîôûçñ]+', text)
    return [list(w) for w in raw_words]


# ══════════════════════════════════════════════════════════════════════
# MI(d) COMPUTATION — Vectorized with numpy for speed
# ══════════════════════════════════════════════════════════════════════

SPACE_TOKEN = '<SP>'

def words_to_stream(word_lists, use_space=True):
    """Convert list of word lists (each word = list of tokens) to flat token stream.
    Inserts SPACE_TOKEN between words if use_space=True."""
    stream = []
    for i, word in enumerate(word_lists):
        stream.extend(word)
        if use_space and i < len(word_lists) - 1:
            stream.append(SPACE_TOKEN)
    return stream


def encode_stream(stream):
    """Map token stream to integer indices. Returns (int_array, vocab_size, token_to_idx)."""
    vocab = sorted(set(stream))
    tok2idx = {t: i for i, t in enumerate(vocab)}
    encoded = np.array([tok2idx[t] for t in stream], dtype=np.int32)
    return encoded, len(vocab), tok2idx


def mi_at_distance_fast(arr, n_symbols, d):
    """Compute MI between elements at distance d using numpy bincount."""
    N = len(arr)
    if N <= d:
        return 0.0
    left = arr[:N - d]
    right = arr[d:]
    n = len(left)

    # Flatten to 1D pair index, then bincount
    pair_flat = left.astype(np.int64) * n_symbols + right.astype(np.int64)
    counts = np.bincount(pair_flat, minlength=n_symbols * n_symbols)
    joint = counts.reshape(n_symbols, n_symbols).astype(np.float64)

    # Marginals
    p_left = joint.sum(axis=1)
    p_right = joint.sum(axis=0)
    total = float(n)

    # Normalize
    joint_p = joint / total
    p_left_n = p_left / total
    p_right_n = p_right / total

    # MI = sum p(x,y) * log2(p(x,y) / (p(x)*p(y)))
    outer = np.outer(p_left_n, p_right_n)
    mask = (joint_p > 0) & (outer > 0)
    if not mask.any():
        return 0.0
    mi = np.sum(joint_p[mask] * np.log2(joint_p[mask] / outer[mask]))
    return float(mi)


def mi_profile(word_lists, d_max=150):
    """Compute MI(d) for d=1..d_max on a text given as list of word lists."""
    stream = words_to_stream(word_lists)
    if len(stream) < d_max + 10:
        pr(f'    WARNING: stream too short ({len(stream)} tokens) for d_max={d_max}')
        d_max = max(1, len(stream) // 2)
    arr, n_sym, _ = encode_stream(stream)
    return [mi_at_distance_fast(arr, n_sym, d) for d in range(1, d_max + 1)]


def shuffled_mi_profile(word_lists, d_max=150, n_shuffles=10):
    """MI(d) profile averaged over n_shuffles word-order permutations."""
    profiles = []
    for _ in range(n_shuffles):
        shuffled = word_lists[:]
        random.shuffle(shuffled)
        stream = words_to_stream(shuffled)
        arr, n_sym, _ = encode_stream(stream)
        profile = [mi_at_distance_fast(arr, n_sym, d) for d in range(1, d_max + 1)]
        profiles.append(profile)
    d_actual = len(profiles[0])
    return [sum(p[d] for p in profiles) / n_shuffles for d in range(d_actual)]


def text_meaning_area(raw_profile, shuffled_profile, d_start=20, d_end=80):
    """TMA = integral of (raw - shuffled) over d in [d_start, d_end].
    Positive = word order carries information (meaningful text).
    Near zero = generative (no word-order structure)."""
    area = 0.0
    for d in range(d_start - 1, min(d_end, len(raw_profile), len(shuffled_profile))):
        area += raw_profile[d] - shuffled_profile[d]
    return area


def generative_area(raw_profile, shuffled_profile, d_start=1, d_end=10):
    """Generative area = integral of (raw - shuffled) for SHORT distances.
    This measures within-word structure (present in both NL and generated text)."""
    area = 0.0
    for d in range(d_start - 1, min(d_end, len(raw_profile), len(shuffled_profile))):
        area += raw_profile[d] - shuffled_profile[d]
    return area


# ══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ══════════════════════════════════════════════════════════════════════

def main():
    pr('=' * 76)
    pr('mi_distance_curve — MI(d) TEXT-MEANING-AREA ANALYSIS')
    pr('=' * 76)
    pr()
    pr('  Does the VMS carry word-order meaning, or is it purely generated?')
    pr('  Does our verbose cipher PRESERVE or DESTROY text meaning area?')
    pr('  Based on quimqu\'s MI(d) concept (Voynich Ninja thread-5380).')
    pr()

    random.seed(42)
    np.random.seed(42)

    D_MAX = 150
    N_SHUFFLES = 10
    TMA_D_START = 20
    TMA_D_END = 80

    # ── Step 1: Parse VMS ─────────────────────────────────────────────
    pr('─' * 76)
    pr('Step 1: Parse VMS corpus')
    pr('─' * 76)

    vms = parse_vms_by_currier()
    pr(f'  VMS all:       {len(vms["all"]):,} words')
    pr(f'  VMS Currier A: {len(vms["A"]):,} words')
    pr(f'  VMS Currier B: {len(vms["B"]):,} words')

    # Glyph counts
    for label in ['all', 'A', 'B']:
        n_glyphs = sum(len(w) for w in vms[label])
        pr(f'    {label} → {n_glyphs:,} glyphs in stream')

    # ── Step 2: Load NL texts ─────────────────────────────────────────
    pr()
    pr('─' * 76)
    pr('Step 2: Load natural language reference texts')
    pr('─' * 76)

    nl_sources = [
        ('Latin-Caesar',      'latin_texts/caesar.txt'),
        ('Latin-Vulgate',     'latin_texts/vulgate_genesis.txt'),
        ('Italian-Cucina',    'vernacular_texts/italian_cucina.txt'),
        ('German-Medical',    'vernacular_texts/german_bvgs_raw.txt'),
        ('German-Faust',      'vernacular_texts/german_faust.txt'),
        ('French-Viandier',   'vernacular_texts/french_viandier.txt'),
        ('English-Cury',      'vernacular_texts/english_cury.txt'),
    ]

    nl_texts = {}
    for name, relpath in nl_sources:
        fpath = DATA_DIR / relpath
        if fpath.exists():
            words = load_nl_text(fpath)
            nl_texts[name] = words
            n_chars = sum(len(w) for w in words)
            pr(f'  {name:20s}: {len(words):,} words, {n_chars:,} chars')
        else:
            pr(f'  {name:20s}: FILE NOT FOUND ({fpath})')

    # ── Step 3: Generate verbose cipher texts ─────────────────────────
    pr()
    pr('─' * 76)
    pr('Step 3: Generate verbose cipher from NL source texts')
    pr('─' * 76)

    cipher_texts = {}
    cipher_source_pairs = [
        ('VCipher-Italian', 'vernacular_texts/italian_cucina.txt'),
        ('VCipher-Latin',   'latin_texts/caesar.txt'),
        ('VCipher-German',  'vernacular_texts/german_bvgs_raw.txt'),
    ]

    for name, relpath in cipher_source_pairs:
        fpath = DATA_DIR / relpath
        if fpath.exists():
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                source_text = f.read()
            cipher_words = generate_verbose_cipher(source_text)
            cipher_texts[name] = cipher_words
            n_chars = sum(len(w) for w in cipher_words)
            pr(f'  {name:20s}: {len(cipher_words):,} cipher words, {n_chars:,} cipher chars')
        else:
            pr(f'  {name:20s}: source not found')

    # ── Step 4: Char-shuffled control ─────────────────────────────────
    pr()
    pr('─' * 76)
    pr('Step 4: Prepare char-shuffled control (sanity check)')
    pr('─' * 76)

    # Char-shuffle VMS: shuffle ALL characters, breaking word boundaries
    # MI(d) should be ≈ 0 for all d — validates our MI computation
    vms_stream = words_to_stream(vms['all'])
    char_shuffled = vms_stream[:]
    random.shuffle(char_shuffled)
    # Repackage as single "word" for the MI function
    char_shuffled_words = [char_shuffled]  # one giant "word"
    pr(f'  VMS char-shuffled: {len(char_shuffled):,} tokens (should give MI ≈ 0)')

    # ── Step 5: Compute all MI(d) profiles ────────────────────────────
    pr()
    pr('─' * 76)
    pr('Step 5: Compute MI(d) profiles (d=1..{}, {} word-shuffles)'.format(D_MAX, N_SHUFFLES))
    pr('─' * 76)
    pr()

    all_texts = {}
    all_texts['VMS-Full'] = vms['all']
    all_texts['VMS-CurrierA'] = vms['A']
    all_texts['VMS-CurrierB'] = vms['B']
    for name, words in nl_texts.items():
        all_texts[name] = words
    for name, words in cipher_texts.items():
        all_texts[name] = words
    all_texts['VMS-CharShuffle'] = char_shuffled_words

    results = {}

    for name, words in all_texts.items():
        pr(f'  Computing MI(d) for {name}...')
        raw = mi_profile(words, D_MAX)
        pr(f'    Raw profile: MI(1)={raw[0]:.6f}, MI(10)={raw[9]:.6f}, MI(50)={raw[49]:.6f}')

        if name == 'VMS-CharShuffle':
            # No need for word-shuffle of already char-shuffled text
            shuffled = [0.0] * len(raw)
            tma = 0.0
            ga = 0.0
        else:
            shuffled = shuffled_mi_profile(words, D_MAX, N_SHUFFLES)
            tma = text_meaning_area(raw, shuffled, TMA_D_START, TMA_D_END)
            ga = generative_area(raw, shuffled, 1, 10)
            pr(f'    Shuffled:    MI(1)={shuffled[0]:.6f}, MI(10)={shuffled[9]:.6f}, MI(50)={shuffled[49]:.6f}')
            pr(f'    TMA[{TMA_D_START}-{TMA_D_END}]={tma:.6f}  GA[1-10]={ga:.6f}')

        results[name] = {
            'raw': raw,
            'shuffled': shuffled,
            'tma': tma,
            'ga': ga,
            'n_words': len(words),
            'n_tokens': sum(len(w) for w in words),
        }
        pr()

    # ── Step 6: Results table ─────────────────────────────────────────
    pr()
    pr('─' * 76)
    pr('Step 6: Summary — Text Meaning Area (TMA) comparison')
    pr('─' * 76)
    pr()
    pr(f'  TMA = ∫(MI_raw - MI_shuffled) for d ∈ [{TMA_D_START}, {TMA_D_END}]')
    pr(f'  Positive TMA → word order carries meaning')
    pr(f'  TMA ≈ 0      → text is generative (no word-order structure)')
    pr()

    pr(f'  {"Text":<22s} {"Words":>8s} {"Tokens":>8s} '
       f'{"MI(1)":>8s} {"MI(50)":>8s} {"MI(100)":>8s} '
       f'{"TMA":>10s} {"GA[1-10]":>10s}')
    pr(f'  {"─"*22} {"─"*8} {"─"*8} {"─"*8} {"─"*8} {"─"*8} {"─"*10} {"─"*10}')

    # Sort: NL texts, then cipher texts, then VMS, then controls
    order = []
    nl_names = sorted(nl_texts.keys())
    cipher_names = sorted(cipher_texts.keys())
    vms_names = ['VMS-Full', 'VMS-CurrierA', 'VMS-CurrierB']
    ctrl_names = ['VMS-CharShuffle']
    for group in [nl_names, cipher_names, vms_names, ctrl_names]:
        for name in group:
            if name in results:
                order.append(name)

    for name in order:
        r = results[name]
        raw = r['raw']
        mi1 = raw[0] if len(raw) > 0 else 0
        mi50 = raw[49] if len(raw) > 49 else 0
        mi100 = raw[99] if len(raw) > 99 else 0
        pr(f'  {name:<22s} {r["n_words"]:>8,d} {r["n_tokens"]:>8,d} '
           f'{mi1:>8.4f} {mi50:>8.4f} {mi100:>8.4f} '
           f'{r["tma"]:>10.4f} {r["ga"]:>10.4f}')

    # ── Step 6b: MI(d) decay profiles at key distances ────────────────
    pr()
    pr('─' * 76)
    pr('Step 6b: MI(d) at selected distances')
    pr('─' * 76)
    pr()

    selected_d = [1, 2, 5, 10, 20, 50, 80, 100, 150]
    header_d = ''.join(f'{"d="+str(d):>10s}' for d in selected_d)
    pr(f'  {"Text":<22s} {header_d}')
    pr(f'  {"─"*22} ' + '─' * (10 * len(selected_d)))

    for name in order:
        raw = results[name]['raw']
        vals = []
        for d in selected_d:
            if d - 1 < len(raw):
                vals.append(f'{raw[d-1]:>10.5f}')
            else:
                vals.append(f'{"N/A":>10s}')
        pr(f'  {name:<22s} ' + ''.join(vals))

    # ── Step 6c: Shuffled profiles at key distances ───────────────────
    pr()
    pr('  Word-shuffled MI(d):')
    pr(f'  {"Text":<22s} {header_d}')
    pr(f'  {"─"*22} ' + '─' * (10 * len(selected_d)))

    for name in order:
        shuf = results[name]['shuffled']
        vals = []
        for d in selected_d:
            if d - 1 < len(shuf):
                vals.append(f'{shuf[d-1]:>10.5f}')
            else:
                vals.append(f'{"N/A":>10s}')
        pr(f'  {name:<22s} ' + ''.join(vals))

    # ── Step 6d: Gap (raw - shuffled) at key distances ────────────────
    pr()
    pr('  Gap (raw − shuffled):')
    pr(f'  {"Text":<22s} {header_d}')
    pr(f'  {"─"*22} ' + '─' * (10 * len(selected_d)))

    for name in order:
        raw = results[name]['raw']
        shuf = results[name]['shuffled']
        vals = []
        for d in selected_d:
            if d - 1 < len(raw) and d - 1 < len(shuf):
                gap = raw[d-1] - shuf[d-1]
                vals.append(f'{gap:>10.5f}')
            else:
                vals.append(f'{"N/A":>10s}')
        pr(f'  {name:<22s} ' + ''.join(vals))

    # ── Step 7: TMA sensitivity analysis ──────────────────────────────
    pr()
    pr('─' * 76)
    pr('Step 7: TMA sensitivity to integration range')
    pr('─' * 76)
    pr()

    ranges_to_test = [(10, 50), (20, 80), (30, 100), (40, 120), (20, 60)]
    pr(f'  {"Text":<22s}' + ''.join(f'{"["+str(a)+"-"+str(b)+"]":>14s}' for a, b in ranges_to_test))
    pr(f'  {"─"*22}' + '─' * (14 * len(ranges_to_test)))

    for name in order:
        raw = results[name]['raw']
        shuf = results[name]['shuffled']
        vals = []
        for a, b in ranges_to_test:
            tma_val = text_meaning_area(raw, shuf, a, b)
            vals.append(f'{tma_val:>14.4f}')
        pr(f'  {name:<22s}' + ''.join(vals))

    # ── Step 8: A/B comparison ────────────────────────────────────────
    pr()
    pr('─' * 76)
    pr('Step 8: Currier A vs B — detailed comparison')
    pr('─' * 76)
    pr()

    if 'VMS-CurrierA' in results and 'VMS-CurrierB' in results:
        ra = results['VMS-CurrierA']
        rb = results['VMS-CurrierB']
        pr(f'  Currier A: {ra["n_words"]:,} words, TMA={ra["tma"]:.4f}, GA={ra["ga"]:.4f}')
        pr(f'  Currier B: {rb["n_words"]:,} words, TMA={rb["tma"]:.4f}, GA={rb["ga"]:.4f}')
        pr()
        if abs(ra['tma']) > 0 or abs(rb['tma']) > 0:
            ratio = rb['tma'] / ra['tma'] if abs(ra['tma']) > 1e-8 else float('inf')
            pr(f'  TMA ratio (B/A): {ratio:.2f}')
        pr()
        pr('  quimqu found: A looks generative (TMA ≈ 0), B has small positive TMA.')
        pr('  If confirmed: A and B may encode differently (or A is less meaningful).')

    # ── Step 9: Cipher preservation test ──────────────────────────────
    pr()
    pr('─' * 76)
    pr('Step 9: Does verbose cipher preserve text-meaning-area?')
    pr('─' * 76)
    pr()

    # Compare each cipher output to its source NL text
    source_map = {
        'VCipher-Italian': 'Italian-Cucina',
        'VCipher-Latin':   'Latin-Caesar',
        'VCipher-German':  'German-Medical',
    }

    for cipher_name, source_name in source_map.items():
        if cipher_name in results and source_name in results:
            rc = results[cipher_name]
            rs = results[source_name]
            pr(f'  {source_name} → {cipher_name}:')
            pr(f'    Source TMA:  {rs["tma"]:.4f}')
            pr(f'    Cipher TMA:  {rc["tma"]:.4f}')
            if abs(rs['tma']) > 1e-8:
                preservation = rc['tma'] / rs['tma']
                pr(f'    Preservation: {preservation:.1%}')
            pr()

    pr('  INTERPRETATION:')
    pr('  • If cipher TMA ≈ source TMA: cipher preserves word-order info')
    pr('  • If cipher TMA ≈ 0: cipher destroys word-order info')
    pr('  • Compare cipher TMA to VMS TMA for compatibility')

    # ── Step 10: Synthesis ────────────────────────────────────────────
    pr()
    pr('─' * 76)
    pr('Step 10: SYNTHESIS')
    pr('─' * 76)
    pr()

    # Classify each text
    nl_tmas = [results[n]['tma'] for n in nl_names if n in results]
    cipher_tmas = [results[n]['tma'] for n in cipher_names if n in results]
    vms_full_tma = results.get('VMS-Full', {}).get('tma', 0)
    vms_a_tma = results.get('VMS-CurrierA', {}).get('tma', 0)
    vms_b_tma = results.get('VMS-CurrierB', {}).get('tma', 0)

    avg_nl_tma = np.mean(nl_tmas) if nl_tmas else 0
    avg_cipher_tma = np.mean(cipher_tmas) if cipher_tmas else 0

    pr(f'  Average NL TMA:        {avg_nl_tma:.4f}')
    pr(f'  Average cipher TMA:    {avg_cipher_tma:.4f}')
    pr(f'  VMS full TMA:          {vms_full_tma:.4f}')
    pr(f'  VMS Currier A TMA:     {vms_a_tma:.4f}')
    pr(f'  VMS Currier B TMA:     {vms_b_tma:.4f}')
    pr()

    # Determine which bin VMS falls into
    pr('  CLASSIFICATION:')

    for label, tma in [('VMS Full', vms_full_tma), ('VMS Currier A', vms_a_tma), ('VMS Currier B', vms_b_tma)]:
        if avg_nl_tma > 0:
            ratio_to_nl = tma / avg_nl_tma
        else:
            ratio_to_nl = 0
        if ratio_to_nl > 0.5:
            classification = 'MEANINGFUL (NL-like word-order structure)'
        elif ratio_to_nl > 0.1:
            classification = 'WEAKLY MEANINGFUL (some word-order signal)'
        else:
            classification = 'GENERATIVE (no/minimal word-order structure)'
        pr(f'    {label:18s}: TMA/NL = {ratio_to_nl:.2f} → {classification}')

    pr()

    for label, tma in [('Verbose cipher', avg_cipher_tma)]:
        if avg_nl_tma > 0:
            ratio_to_nl = tma / avg_nl_tma
        else:
            ratio_to_nl = 0
        pr(f'    {label:18s}: TMA/NL = {ratio_to_nl:.2f}')
        if ratio_to_nl > 0.3:
            pr(f'      → Cipher PRESERVES word-order structure')
        else:
            pr(f'      → Cipher DESTROYS word-order structure')

    pr()
    pr('  KEY QUESTION ANSWERS:')
    pr()

    # Q1: Does VMS carry word-order meaning?
    if vms_full_tma > avg_nl_tma * 0.1:
        pr('  Q1. Does VMS carry word-order meaning?')
        pr(f'      → YES: VMS TMA ({vms_full_tma:.4f}) shows word-order structure')
    else:
        pr('  Q1. Does VMS carry word-order meaning?')
        pr(f'      → NO: VMS TMA ({vms_full_tma:.4f}) ≈ 0, consistent with generation')

    pr()

    # Q2: Does verbose cipher preserve TMA?
    if avg_cipher_tma > avg_nl_tma * 0.3:
        pr('  Q2. Does verbose cipher preserve word-order meaning?')
        pr(f'      → YES: Cipher TMA ({avg_cipher_tma:.4f}) retains substantial structure')
    else:
        pr('  Q2. Does verbose cipher preserve word-order meaning?')
        pr(f'      → NO/PARTIALLY: Cipher TMA ({avg_cipher_tma:.4f}) loses most structure')

    pr()

    # Q3: Currier A vs B
    if abs(vms_b_tma) > abs(vms_a_tma) * 1.5:
        pr('  Q3. Currier A vs B difference?')
        pr(f'      → CONFIRMED: B ({vms_b_tma:.4f}) > A ({vms_a_tma:.4f})')
        pr(f'      → Matches quimqu: A is more generative, B has meaning signal')
    elif abs(vms_a_tma - vms_b_tma) < abs(vms_full_tma) * 0.3:
        pr('  Q3. Currier A vs B difference?')
        pr(f'      → NOT CONFIRMED: A ({vms_a_tma:.4f}) ≈ B ({vms_b_tma:.4f})')
    else:
        pr('  Q3. Currier A vs B difference?')
        pr(f'      → PARTIALLY: A={vms_a_tma:.4f}, B={vms_b_tma:.4f}')

    pr()

    # Q4: Compatibility
    if avg_cipher_tma > 0 and abs(vms_full_tma - avg_cipher_tma) / max(avg_cipher_tma, 0.001) < 0.5:
        pr('  Q4. Is VMS TMA compatible with verbose cipher on NL?')
        pr(f'      → YES: VMS ({vms_full_tma:.4f}) ≈ cipher ({avg_cipher_tma:.4f})')
    else:
        pr('  Q4. Is VMS TMA compatible with verbose cipher on NL?')
        pr(f'      → MISMATCH: VMS ({vms_full_tma:.4f}) vs cipher ({avg_cipher_tma:.4f})')

    pr()

    # ── Save results ──────────────────────────────────────────────────
    pr('─' * 76)
    pr('Saving results...')
    pr('─' * 76)

    results_txt = RESULTS_DIR / 'mi_distance_curve.txt'
    with open(results_txt, 'w', encoding='utf-8') as f:
        f.write(''.join(OUTPUT))
    pr(f'  Text results: {results_txt}')

    # JSON with full profiles
    json_data = {}
    for name, r in results.items():
        json_data[name] = {
            'n_words': r['n_words'],
            'n_tokens': r['n_tokens'],
            'tma_20_80': r['tma'],
            'ga_1_10': r['ga'],
            'raw_mi': [round(v, 8) for v in r['raw']],
            'shuffled_mi': [round(v, 8) for v in r['shuffled']],
        }

    results_json = RESULTS_DIR / 'mi_distance_curve.json'
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
    pr(f'  JSON results: {results_json}')

    pr()
    pr('=' * 76)
    pr('mi_distance_curve COMPLETE')
    pr('=' * 76)


if __name__ == '__main__':
    main()
