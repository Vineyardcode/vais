#!/usr/bin/env python3
"""
CROSS-SCRIPT STATISTICAL FINGERPRINTING
=====================================================

Compare the Voynich manuscript's statistical fingerprint against
reference texts in known scripts and Cipher variants.

CORE QUESTION: Where does VMS fall in the space of known writing
systems?  Does it cluster with alphabets, syllabaries, or ciphers?

Reference texts (fetched from Project Gutenberg):
  - English      (Alice in Wonderland, #11)
  - Latin        (Caesar, De Bello Gallico, #10657)
  - Italian      (Dante, Inferno, #1012)
  - German       (Goethe, Faust, #2229)
  - Spanish      (Cervantes, Don Quixote, #2000)
  - French       (Hugo, Les Misérables, #17489)
  - Finnish      (Lönnrot, Kalevala, #7000)
  - Hawaiian     (embedded sample — CV syllable structure)

Cipher references (generated from English):
  - Simple substitution cipher of English
  - Bigram substitution cipher of English (pairs → single symbols)

Non-Latin scripts (embedded Unicode samples):
  - Japanese hiragana (syllabary)
  - Korean (featural alphabet / syllabic blocks)
  - Arabic

Metrics computed for each:
  1. Alphabet size (distinct symbol count)
  2. H(char)         — character unigram entropy
  3. H(char|prev)    — bigram conditional entropy
  4. H-ratio         — H(c|prev) / H(c)  (bigram predictability)
  5. IC              — index of coincidence
  6. Mean word len   — in characters
  7. TTR-10K         — type-token ratio at 10K tokens
  8. Hapax-10K       — hapax legomena fraction at 10K tokens
  9. Sukhotin V-frac — fraction of alphabet classified as vowels
  10. V/C alternation — fraction of adjacent char pairs that switch V↔C
"""

import re, sys, io, math, random, json
from pathlib import Path
from collections import Counter, defaultdict
import urllib.request
import numpy as np
from common import fetch_gutenberg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdout.reconfigure(line_buffering=True)

random.seed(58)
np.random.seed(58)

_print = print
def pr(s=''):
    _print(s)
    sys.stdout.flush()

# ─── VMS loading (reuse from earlier phases) ───────────────────────────

FOLIO_DIR = Path("folios")

ALL_GALLOWS = ['cth','ckh','cph','cfh','tch','kch','pch','fch',
               'tsh','ksh','psh','fsh','t','k','f','p']

def eva_to_glyphs(word):
    """Convert an EVA word to a list of glyph tokens (digraphs as single tokens)."""
    glyphs = []
    i = 0
    w = word
    while i < len(w):
        # Try 3-char gallows first
        if i+2 < len(w) and w[i:i+3] in ('cth','ckh','cph','cfh'):
            glyphs.append(w[i:i+3]); i += 3
        elif i+1 < len(w) and w[i:i+2] in ('ch','sh','th','kh','ph','fh'):
            glyphs.append(w[i:i+2]); i += 2
        else:
            glyphs.append(w[i]); i += 1
    return glyphs

def load_vms():
    """Load VMS text, return (list_of_words, list_of_lines_as_word_lists)."""
    words_all = []
    lines = []
    for fpath in sorted(FOLIO_DIR.glob("*.txt")):
        for line in fpath.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if line.startswith('#'): continue
            m = re.match(r'<([^>]+)>', line)
            rest = line[m.end():].strip() if m else line
            if not rest: continue
            ws = [w.strip() for w in re.split(r'[.\s,;]+', rest)
                  if w.strip() and re.match(r'^[a-z]+$', w.strip())]
            if len(ws) >= 1:
                words_all.extend(ws)
                if len(ws) >= 2:
                    lines.append(ws)
    return words_all, lines

def vms_char_sequence(words):
    """Convert VMS words to a flat glyph sequence with word-boundary markers."""
    seq = []
    for w in words:
        seq.extend(eva_to_glyphs(w))
        seq.append(' ')  # word boundary
    return seq

# ─── Reference text helpers ────────────────────────────────────────────


def text_to_words_and_chars(text, script='latin'):
    """
    Normalize text and extract words and character sequence.
    For Latin scripts: lowercase, strip non-alpha, split on whitespace.
    For non-Latin: split on whitespace, keep script chars.
    Returns (words, char_sequence_with_spaces).
    """
    if script == 'latin':
        # Lowercase, keep letters and spaces
        text = text.lower()
        text = re.sub(r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöùúûüýþß]+', ' ', text)
        words = [w for w in text.split() if len(w) >= 1]
        chars = []
        for w in words:
            chars.extend(list(w))
            chars.append(' ')
        return words, chars
    elif script == 'japanese':
        # Keep only hiragana (U+3040-U+309F)
        chars_only = [c for c in text if '\u3040' <= c <= '\u309f']
        # Split into "words" by runs between spaces/punctuation
        raw = re.sub(r'[^\u3040-\u309f\s]+', ' ', text)
        words = [w for w in raw.split() if len(w) >= 1 and any('\u3040' <= c <= '\u309f' for c in w)]
        # For Japanese, we also need the char sequence
        # Since Japanese doesn't have spaces natively, use the full hiragana stream
        chars = list(''.join(chars_only))
        return words, chars
    elif script == 'korean':
        # Keep Hangul syllables (U+AC00-U+D7AF) and jamo (U+1100-U+11FF, U+3130-U+318F)
        text_clean = re.sub(r'[^\uac00-\ud7af\u1100-\u11ff\u3130-\u318f\s]+', ' ', text)
        words = [w for w in text_clean.split() if len(w) >= 1]
        chars = []
        for w in words:
            chars.extend(list(w))
            chars.append(' ')
        return words, chars
    elif script == 'arabic':
        # Keep Arabic characters (U+0600-U+06FF)
        text_clean = re.sub(r'[^\u0600-\u06ff\s]+', ' ', text)
        words = [w for w in text_clean.split() if len(w) >= 1]
        chars = []
        for w in words:
            chars.extend(list(w))
            chars.append(' ')
        return words, chars
    elif script == 'hawaiian':
        text = text.lower()
        text = re.sub(r"[^a-zāēīōūʻ ]+", ' ', text)
        words = [w for w in text.split() if len(w) >= 1]
        chars = []
        for w in words:
            chars.extend(list(w))
            chars.append(' ')
        return words, chars

# ─── Embedded non-Latin samples ────────────────────────────────────────
# Public domain text samples for scripts not available on Gutenberg
# These are from public domain or government sources

JAPANESE_HIRAGANA_SAMPLE = (
    # Opening of Ise Monogatari (Tales of Ise), public domain (10th century)
    # Transliterated to pure hiragana for syllabary analysis
    "むかし おとこ うゐかうぶり して ならの きやう かすがの さとに "
    "しるよし して かりに いにけり その さとに いと なまめいたる "
    "をんな はらから すみけり この おとこ かいまみて けり "
    "おもほえず ふるさとに いと はしたなく して ありけれ ば "
    "おとこの きたる きぬの すそを きりて うたを かきて やる "
    "かすがの の わかむらさき の すりごろも しのぶの みだれ "
    "かぎり しられず むかし おとこ ひがしの いつてうに すむ をんなを "
    "えうじて いきかよふ あひだに ひさしう なりに ければ "
    "をんな おとこの もとに こころざし あるかた に いきけり "
    "おとこ ゆくかたを しらで やすく ねられざりけり "
    "むかし おとこ ありけり けちえんとも いふべき をんな を えて "
    "としを へて よばひ わたりけるを こころかはりに けるに "
    "いきどほりて なくなく よめる しらたまか なにぞと ひとの "
    "とひし とき つゆと こたへて きえなましもの を "
    "むかし おとこ あり けり をんなの え うまじかりける を "
    "としを へて よばひ わたりけるを からうじて おもひかなひて "
    "あひえりけるを あはれとも いふべし あるじゆるして けり "
    "みそかなりけり むかし おとこ ありけり ひがしの ごでう わたりに "
    "いと しのびて いきけり みそかなれば かどよりも いらで "
    "かきの くづれより かよひけり ひとしげく あらね ど "
    "たびかさなりけれ ば あるじ きゝ つけて その みちに よごとに "
    "ひとを すゑて まもらせけれ ば いけども えあはで かへりけり "
    "さてよめる ひと しれず こそ おもひそめしか のきに おふる "
    "しのぶは いろの ことなる やまと うたの おこり は ひさしき ことなり "
    "あめ つち の ひらけし ときより いで きに けり "
    "しかれども よに つたはる こと は ひさかたの あめに あがりて "
    "よもの くにくに を みそなはし たまひ ちかき まもりの つかさ "
    "として あめの みかど に つかへ たてまつり おほやけの まつりごと "
    "を たすけ おこなふ なれば おのづから にぎはひ たつ くにの "
    "かたち を みつつ よろこび にたへず して いにしへの ことに "
    "よせて うたの こゝろ を のべたるなり"
)

KOREAN_SAMPLE = (
    # Opening of Hunminjeongeum Haerye (1446), public domain
    # Plus modern Korean public domain text (government notices)
    "나랏 말이 중국과 달라 한자와 서로 통하지 아니하므로 "
    "어리석은 백성이 말하고자 하는 바가 있어도 마침내 제 뜻을 "
    "펴지 못하는 사람이 많다 내가 이를 불쌍히 여겨 새로 스물여덟 "
    "글자를 만드니 사람마다 쉽게 익혀 날마다 쓰는 데 편하게 하고자 "
    "할 따름이다 하늘이 만물을 내실 때 소리가 있는 것은 반드시 "
    "기운이 있고 기운이 있으면 반드시 소리가 있으니 소리는 기운에서 "
    "나는 것이다 사계절이 바뀌면서 하늘과 땅 사이에 만물이 생겨나는 "
    "것도 역시 기운에 의한 것이다 대저 사람의 소리를 가지고 "
    "말하면 가장 정밀하고 가장 신묘하여 능히 만물을 통하고 사계절에 "
    "걸맞으니 실로 하늘과 땅의 이치를 드러내고 만물의 정기를 갖추어 "
    "어디서나 통하지 않음이 없으며 어디서나 갖추어지지 않음이 없느니라 "
    "하늘과 땅의 도리는 하나의 음양과 오행일 뿐이다 곤괘와 복괘 "
    "사이가 태극이요 태극의 움직임과 고요함이 음양이니 사람이 살아가면서 "
    "내는 소리에도 모두 음양의 이치가 있으니 다만 사람이 살피지 못할 "
    "따름이다 이제 바른 소리를 만드니 처음으로 하늘과 땅의 마음에 "
    "근본을 두되 사람과 만물의 뜻까지도 빠져나가지 않게 하였다 "
    "바른 소리의 첫소리 글자는 모두 열일곱 자이니 어금닛소리 "
    "혓소리 입술소리 잇소리 목구멍소리가 각각 하나의 차례를 이루어 "
    "모두 오행에 합한다 다시 그 가운데에서 혀를 윗입천장에 댄 소리가 "
    "있어 모두 서른일곱 자인데 첫소리로 쓸 수 있는 것은 모두 "
    "스물세 자이다 반혓소리와 반잇소리가 있는 까닭은 혀와 이에서 "
    "나는 소리가 서로 비슷하여 이웃함이 있기 때문이다 대저 사람의 "
    "소리가 생기는 것은 오행이 있어 사계절에 합하여 비추어보면 어김이 "
    "없으니 정음의 글자를 만든 것도 역시 그 이치를 활용한 것이지 "
    "사람의 지혜로 억지로 만들어낸 것이 아닌 것이다"
)

ARABIC_SAMPLE = (
    # Opening of Muqaddimah by Ibn Khaldun (14th century, public domain)
    "الحمد لله الذي له العزة والجبروت وبيده الملك والملكوت "
    "وله الاسماء الحسنى والصفات وعلمه محيط بما هو آت وبما مضى "
    "وفات مقدر الاقدار ومدبر الادوار اخرج الخلق من العدم ورتبهم "
    "في مراتبه اصنافا واصطفى من البشر رسلا وانبياء وخصهم بمرتبة "
    "الوحي والالهام ثم استقرت بعدهم المعارف في اهل العلم "
    "والدين وانتحلها من دونهم بالتقليد والايمان واوعى لها قلوبا "
    "طاهرة وافئدة صادقة ثم وفقهم لحفظها وحمايتها حتى صارت "
    "علوما مدونة وكتبا مسطورة يطالعها الناس ويتعلمونها ويعملون بها "
    "وهي كثيرة جدا منها ما يتعلق بالعبادات ومنها ما يتعلق "
    "بالمعاملات ومنها العلوم العقلية التي يشترك فيها جميع الامم "
    "كالفلسفة والمنطق والطب والهندسة والفلك وما اشبه ذلك "
    "وكل ذلك صادر عن العقل الذي ميز الله به الانسان عن سائر "
    "المخلوقات وجعله وسيلة لمعرفة الحق والخير والجمال فالعلم "
    "نور يضيء القلوب ويهدي العقول الى سواء السبيل وبه ترتقي "
    "الامم وتزدهر الحضارات وتعمر الارض وتصلح احوال الناس "
    "والعمران هو ما اجتمع عليه الناس في معايشهم من تعاون "
    "وتكافل وما بنوه من مدن وقرى وما اقاموه من حكومات ودول"
)

HAWAIIAN_SAMPLE = (
    # From Hawaiian language public domain texts (government proclamations)
    # Hawaiian has a 13-letter alphabet (a e i o u h k l m n p w ʻ) + long vowels
    "aloha mai kākou e nā kānaka o ka ʻāina nei ua hana ʻia kēia "
    "kanawai no ka pono o nā kānaka a pau loa o kēia moku ʻāina "
    "no ka mea he mea nui ka mālama ʻana i nā kānaka a me ka ʻāina "
    "a me nā holoholona a me nā mea kanu a pau i ka wā kahiko loa "
    "ua noho ka poʻe hawaiʻi ma kēia ʻāina me ka maluhia a me ka "
    "aloha kekahi i kekahi a ua mālama lākou i ka ʻāina me ka "
    "naʻauao a ua kanu lākou i ka ʻai a me ka iʻa a me nā mea "
    "like ʻole no ka ʻai ʻana me ke aloha a me ka hana pū ʻana "
    "i ka wā kahiko ua aloha nā aliʻi i nā makaʻāinana a ua "
    "hana nā makaʻāinana no nā aliʻi me ka hauʻoli a me ka "
    "mahalo a ua hoʻomau kēia hana a hiki i ka wā i hiki mai ai "
    "nā haole i kēia ʻāina a me ka wā i hoʻomaka ai ka noho ʻana "
    "ma ka ʻaoʻao o ke aupuni hou ua hoʻololi ʻia nā mea he nui "
    "ma ka noho ʻana a me ka hana ʻana o nā kānaka o kēia ʻāina "
    "a ua komo mai nā ʻōlelo hou a me nā hana hou i loko o ka "
    "nohona o ka poʻe hawaiʻi a ua hoʻomaka ka hoʻonaʻauao ʻia "
    "ʻana o nā keiki ma nā kula a ua aʻo ʻia lākou i ka heluhelu "
    "a me ka palapala a me ka helu a ua piha nā kula i nā haumāna "
    "he nui ua hele nā keiki i ke kula me ka hauʻoli no ka mea "
    "he mea hou ia ia lākou a ua makemake lākou e aʻo i nā mea "
    "hou a pau e pili ana i ka honua nei a me nā mea ma ka lani "
    "a ua nui ka naʻauao o ka poʻe hawaiʻi ma muli o kēia hana "
    "akā naʻe ua nalowale kekahi mau mea kahiko i ka wā e neʻe "
    "ana ka wā hou i mua a ua poina ʻia kekahi mau mele kahiko "
    "a me nā moʻolelo o ka wā i hala e pono e mālama kākou i "
    "kēia mau mea waiwai a e haʻi hou aku i nā keiki a me nā "
    "moʻopuna i nā moʻolelo o ko kākou poʻe kūpuna"
)

# ─── Metrics computation ───────────────────────────────────────────────

def compute_metrics(words, chars, name='', max_tokens=10000):
    """
    Compute the full fingerprint vector for a text.
    chars = list of characters/glyphs, with ' ' as word boundary.
    words = list of word strings.
    """
    # Non-boundary chars only
    nb_chars = [c for c in chars if c != ' ']
    if len(nb_chars) < 200:
        return None  # too short

    # 1. Alphabet size
    alphabet = set(nb_chars)
    alpha_size = len(alphabet)

    # 2. H(char)
    counts = Counter(nb_chars)
    total = sum(counts.values())
    H_char = -sum((n/total)*math.log2(n/total) for n in counts.values())

    # 3. H(char|prev) — bigram conditional entropy
    bigram_counts = defaultdict(Counter)
    for i in range(1, len(nb_chars)):
        bigram_counts[nb_chars[i-1]][nb_chars[i]] += 1
    H_cond = 0.0
    for prev_char, nexts in bigram_counts.items():
        prev_total = sum(nexts.values())
        p_prev = prev_total / (total - 1)
        h_local = -sum((n/prev_total)*math.log2(n/prev_total) for n in nexts.values())
        H_cond += p_prev * h_local

    # 4. H-ratio
    H_ratio = H_cond / H_char if H_char > 0 else 0

    # 5. IC (index of coincidence)
    IC = sum(n*(n-1) for n in counts.values()) / (total*(total-1)) if total > 1 else 0

    # 6. Mean word length
    wlens = [len(w) for w in words]
    mean_wlen = np.mean(wlens) if wlens else 0

    # 7. TTR at standardized size
    # Use first max_tokens tokens
    std_words = words[:max_tokens]
    std_n = len(std_words)
    ttr = len(set(std_words)) / std_n if std_n > 0 else 0

    # 8. Hapax ratio at standardized size
    std_counts = Counter(std_words)
    hapax = sum(1 for c in std_counts.values() if c == 1)
    hapax_ratio = hapax / len(std_counts) if std_counts else 0

    # 9. Sukhotin vowel fraction
    v_count, v_set = sukhotin(nb_chars, alphabet)
    v_frac = v_count / alpha_size if alpha_size > 0 else 0

    # 10. V/C alternation rate
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
    """
    Sukhotin's algorithm: classify characters as vowels/consonants
    based on adjacency statistics.
    Returns (n_vowels, set_of_vowels).
    """
    alpha_list = sorted(alphabet)
    n = len(alpha_list)
    idx = {c: i for i, c in enumerate(alpha_list)}

    # Build adjacency matrix
    adj = np.zeros((n, n), dtype=float)
    for i in range(1, len(chars)):
        a, b = chars[i-1], chars[i]
        if a in idx and b in idx and a != b:
            adj[idx[a]][idx[b]] += 1
            adj[idx[b]][idx[a]] += 1

    # Row sums = total adjacency for each char
    row_sums = adj.sum(axis=1)

    vowels = set()
    remaining = set(range(n))

    for _ in range(n):
        # Find char with max row sum among remaining
        best = -1
        best_val = 0
        for r in remaining:
            if row_sums[r] > best_val:
                best_val = row_sums[r]
                best = r
        if best < 0 or best_val <= 0:
            break
        vowels.add(best)
        remaining.discard(best)
        # Update row sums: subtract 2 * adj[best][r] for each remaining r
        for r in remaining:
            row_sums[r] -= 2 * adj[best][r]

    v_set = {alpha_list[i] for i in vowels}
    return len(v_set), v_set

def vc_alternation(chars, vowels):
    """Fraction of adjacent character pairs that switch between V and C."""
    if len(chars) < 2:
        return 0
    transitions = 0
    total = 0
    for i in range(1, len(chars)):
        a_v = chars[i-1] in vowels
        b_v = chars[i] in vowels
        if a_v != b_v:
            transitions += 1
        total += 1
    return transitions / total if total > 0 else 0

# ─── Cipher generators ────────────────────────────────────────────────

def make_substitution_cipher(words, chars):
    """Simple monoalphabetic substitution cipher of a Latin-script text."""
    nb = [c for c in chars if c != ' ']
    alphabet = sorted(set(nb))
    # Random permutation
    shuffled = alphabet[:]
    random.shuffle(shuffled)
    mapping = dict(zip(alphabet, shuffled))
    new_chars = [mapping.get(c, c) if c != ' ' else ' ' for c in chars]
    new_words = []
    for w in words:
        new_words.append(''.join(mapping.get(c, c) for c in w))
    return new_words, new_chars

def make_bigram_cipher(words, chars):
    """
    Bigram substitution: replace character pairs with single novel symbols.
    This REDUCES alphabet size but CHANGES character-level statistics.
    Simulates a polygraphic cipher.
    """
    nb = [c for c in chars if c != ' ']
    # Collect all bigrams
    bigrams = set()
    for i in range(0, len(nb)-1, 2):
        bigrams.add((nb[i], nb[i+1]))
    # Map each bigram to a unique symbol (use uppercase + digits + symbols)
    bigram_list = sorted(bigrams)
    symbols = [chr(i) for i in range(0x0100, 0x0100 + len(bigram_list))]
    bg_map = dict(zip(bigram_list, symbols))

    new_chars = []
    i = 0
    while i < len(chars):
        if chars[i] == ' ':
            new_chars.append(' ')
            i += 1
        elif i+1 < len(chars) and chars[i+1] != ' ':
            bg = (chars[i], chars[i+1])
            new_chars.append(bg_map.get(bg, chars[i]))
            i += 2
        else:
            new_chars.append(chars[i])
            i += 1

    # Reconstruct words
    new_words = []
    current = []
    for c in new_chars:
        if c == ' ':
            if current:
                new_words.append(''.join(current))
                current = []
        else:
            current.append(c)
    if current:
        new_words.append(''.join(current))
    return new_words, new_chars

# ─── Main ─────────────────────────────────────────────────────────────

def main():
    pr("=" * 70)
    pr("cross_script_fingerprint: CROSS-SCRIPT STATISTICAL FINGERPRINTING")
    pr("=" * 70)
    pr()

    # ── Load VMS ──
    pr("Loading VMS corpus...")
    vms_words, vms_lines = load_vms()
    vms_chars = vms_char_sequence(vms_words)
    pr(f"  VMS: {len(vms_words)} words, {len([c for c in vms_chars if c != ' '])} chars")
    pr()

    # ── Fetch reference texts ──
    GUTENBERG_REFS = {
        'English':  11,      # Alice in Wonderland
        'Latin':    10657,   # Caesar, De Bello Gallico
        'Italian':  1012,    # Dante, Inferno
        'German':   2229,    # Goethe, Faust
        'Spanish':  2000,    # Don Quixote
        'French':   17489,   # Hugo, Les Misérables
        'Finnish':  7000,    # Kalevala
    }

    results = {}

    # VMS metrics
    pr("Computing VMS metrics...")
    vms_m = compute_metrics(vms_words, vms_chars, name='VMS (EVA glyphs)')
    results['VMS'] = vms_m
    pr(f"  Done: alpha={vms_m['alpha_size']}, H={vms_m['H_char']:.3f}, "
       f"H|prev={vms_m['H_cond']:.3f}, IC={vms_m['IC']:.4f}")
    pr()

    # Fetch and compute Latin-script references
    for lang, ebook_id in GUTENBERG_REFS.items():
        pr(f"Fetching {lang} (Gutenberg #{ebook_id})...")
        try:
            raw = fetch_gutenberg(ebook_id)
            words, chars = text_to_words_and_chars(raw, script='latin')
            # Truncate to ~50K words for consistency
            if len(words) > 50000:
                words = words[:50000]
                chars = []
                for w in words:
                    chars.extend(list(w))
                    chars.append(' ')
            m = compute_metrics(words, chars, name=lang)
            results[lang] = m
            pr(f"  {lang}: {m['n_words']} words, alpha={m['alpha_size']}, "
               f"H={m['H_char']:.3f}, H|prev={m['H_cond']:.3f}")
        except Exception as e:
            pr(f"  FAILED: {e}")
    pr()

    # Non-Latin embedded samples
    pr("Processing non-Latin script samples...")

    # Japanese hiragana
    jw, jc = text_to_words_and_chars(JAPANESE_HIRAGANA_SAMPLE, script='japanese')
    if len(jc) > 200:
        m = compute_metrics(jw, jc, name='Japanese (hiragana)')
        results['Japanese'] = m
        pr(f"  Japanese: {m['n_words']} words, alpha={m['alpha_size']}, "
           f"H={m['H_char']:.3f}, H|prev={m['H_cond']:.3f}")
    else:
        pr("  Japanese: too few chars, skipping")

    # Korean
    kw, kc = text_to_words_and_chars(KOREAN_SAMPLE, script='korean')
    if len([c for c in kc if c != ' ']) > 200:
        m = compute_metrics(kw, kc, name='Korean (hangul)')
        results['Korean'] = m
        pr(f"  Korean: {m['n_words']} words, alpha={m['alpha_size']}, "
           f"H={m['H_char']:.3f}, H|prev={m['H_cond']:.3f}")
    else:
        pr("  Korean: too few chars, skipping")

    # Arabic
    aw, ac = text_to_words_and_chars(ARABIC_SAMPLE, script='arabic')
    if len([c for c in ac if c != ' ']) > 200:
        m = compute_metrics(aw, ac, name='Arabic')
        results['Arabic'] = m
        pr(f"  Arabic: {m['n_words']} words, alpha={m['alpha_size']}, "
           f"H={m['H_char']:.3f}, H|prev={m['H_cond']:.3f}")
    else:
        pr("  Arabic: too few chars, skipping")

    # Hawaiian
    hw, hc = text_to_words_and_chars(HAWAIIAN_SAMPLE, script='hawaiian')
    if len([c for c in hc if c != ' ']) > 200:
        m = compute_metrics(hw, hc, name='Hawaiian (CV)')
        results['Hawaiian'] = m
        pr(f"  Hawaiian: {m['n_words']} words, alpha={m['alpha_size']}, "
           f"H={m['H_char']:.3f}, H|prev={m['H_cond']:.3f}")
    else:
        pr("  Hawaiian: too few chars, skipping")

    pr()

    # ── Cipher variants (from English) ──
    pr("Generating cipher variants from English text...")
    if 'English' in results:
        eng_raw = fetch_gutenberg(11)
        eng_w, eng_c = text_to_words_and_chars(eng_raw, script='latin')
        eng_w = eng_w[:50000]
        eng_c = []
        for w in eng_w:
            eng_c.extend(list(w))
            eng_c.append(' ')

        # Simple substitution cipher
        sub_w, sub_c = make_substitution_cipher(eng_w, eng_c)
        m = compute_metrics(sub_w, sub_c, name='Cipher: subst(English)')
        results['Cipher_subst'] = m
        pr(f"  Subst cipher: alpha={m['alpha_size']}, H={m['H_char']:.3f}, "
           f"H|prev={m['H_cond']:.3f}, IC={m['IC']:.4f}")

        # Bigram cipher
        bg_w, bg_c = make_bigram_cipher(eng_w, eng_c)
        m = compute_metrics(bg_w, bg_c, name='Cipher: bigram(English)')
        results['Cipher_bigram'] = m
        pr(f"  Bigram cipher: alpha={m['alpha_size']}, H={m['H_char']:.3f}, "
           f"H|prev={m['H_cond']:.3f}, IC={m['IC']:.4f}")
    pr()

    # ── Display comparison table ──
    pr("=" * 70)
    pr("58a) FINGERPRINT COMPARISON TABLE")
    pr("=" * 70)
    pr()

    # Column headers
    cols = ['alpha', 'H(c)', 'H(c|p)', 'H-rat', 'IC', 'MWL', 'TTR', 'Hpx%', 'V-fr', 'V/C-a']
    hdr = f"{'System':<28s}" + ''.join(f'{c:>8s}' for c in cols)
    pr(hdr)
    pr("-" * len(hdr))

    # VMS first in bold
    ordered = ['VMS'] + [k for k in results if k != 'VMS']
    for key in ordered:
        m = results[key]
        if m is None: continue
        marker = ">>>" if key == 'VMS' else "   "
        row = (f"{marker} {m['name']:<24s}"
               f"{m['alpha_size']:>8d}"
               f"{m['H_char']:>8.3f}"
               f"{m['H_cond']:>8.3f}"
               f"{m['H_ratio']:>8.3f}"
               f"{m['IC']:>8.4f}"
               f"{m['mean_wlen']:>8.2f}"
               f"{m['TTR']:>8.4f}"
               f"{m['hapax_ratio']:>8.3f}"
               f"{m['V_frac']:>8.3f}"
               f"{m['VC_alt']:>8.3f}")
        pr(row)
    pr()

    # ── Compute distances ──
    pr("=" * 70)
    pr("58b) EUCLIDEAN DISTANCE FROM VMS (normalized features)")
    pr("=" * 70)
    pr()

    feature_keys = ['alpha_size', 'H_char', 'H_cond', 'H_ratio', 'IC',
                    'mean_wlen', 'TTR', 'hapax_ratio', 'V_frac', 'VC_alt']

    # Build matrix
    names = []
    vecs = []
    for key in ordered:
        m = results[key]
        if m is None: continue
        names.append(m['name'])
        vecs.append([m[fk] for fk in feature_keys])
    X = np.array(vecs)

    # Z-score normalize
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1  # avoid division by zero
    Z = (X - mu) / sigma

    # Distance from VMS (index 0)
    vms_z = Z[0]
    pr(f"{'System':<28s} {'Distance':>10s}")
    pr("-" * 40)
    dists = []
    for i, name in enumerate(names):
        d = np.sqrt(np.sum((Z[i] - vms_z)**2))
        dists.append((d, name))
    dists.sort()
    for d, name in dists:
        marker = ">>>" if 'VMS' in name else "   "
        pr(f"{marker} {name:<24s} {d:>10.3f}")
    pr()

    # ── PCA ──
    pr("=" * 70)
    pr("58c) PCA — FIRST 3 COMPONENTS")
    pr("=" * 70)
    pr()

    # Simple PCA via eigendecomposition of covariance
    Z_centered = Z - Z.mean(axis=0)
    cov = np.cov(Z_centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    # Sort by descending eigenvalue
    idx_sort = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx_sort]
    eigenvectors = eigenvectors[:, idx_sort]

    var_explained = eigenvalues / eigenvalues.sum() * 100

    pr("Variance explained:")
    for i in range(min(5, len(eigenvalues))):
        pr(f"  PC{i+1}: {var_explained[i]:.1f}%")
    pr()

    # Project
    proj = Z_centered @ eigenvectors[:, :3]
    pr(f"{'System':<28s} {'PC1':>8s} {'PC2':>8s} {'PC3':>8s}")
    pr("-" * 56)
    for i, name in enumerate(names):
        marker = ">>>" if 'VMS' in name else "   "
        pr(f"{marker} {name:<24s} {proj[i,0]:>8.3f} {proj[i,1]:>8.3f} {proj[i,2]:>8.3f}")
    pr()

    # Feature loadings for interpretation
    pr("PC loadings (which features drive separation):")
    for pc_i in range(min(3, eigenvectors.shape[1])):
        loadings = eigenvectors[:, pc_i]
        ranked = sorted(zip(feature_keys, loadings), key=lambda x: abs(x[1]), reverse=True)
        top3 = ', '.join(f"{f}={v:+.3f}" for f, v in ranked[:3])
        pr(f"  PC{pc_i+1}: {top3}")
    pr()

    # ── Nearest neighbors analysis ──
    pr("=" * 70)
    pr("58d) NEAREST NEIGHBOR CLASSIFICATION")
    pr("=" * 70)
    pr()
    pr("Question: Do VMS's nearest neighbors tend to be natural languages,")
    pr("ciphers, or syllabaries?")
    pr()

    # Classify each system
    categories = {}
    for name in names:
        if 'Cipher' in name:
            categories[name] = 'cipher'
        elif 'Japanese' in name or 'Korean' in name:
            categories[name] = 'syllabary/featural'
        elif 'Hawaiian' in name:
            categories[name] = 'CV-alphabet'
        elif 'Arabic' in name:
            categories[name] = 'abjad'
        elif 'VMS' in name:
            categories[name] = 'UNKNOWN'
        else:
            categories[name] = 'alphabet'

    pr(f"{'Rank':<6s} {'System':<28s} {'Distance':>10s} {'Category':<20s}")
    pr("-" * 66)
    for rank, (d, name) in enumerate(dists):
        cat = categories.get(name, '?')
        marker = ">>>" if 'VMS' in name else "   "
        pr(f"{marker} {rank:<4d} {name:<28s} {d:>10.3f} {cat:<20s}")
    pr()

    # ── Feature-by-feature analysis ──
    pr("=" * 70)
    pr("58e) WHERE VMS IS ANOMALOUS (feature-level z-scores vs natural languages)")
    pr("=" * 70)
    pr()

    # Compute z-scores of VMS relative to natural language distribution only
    nl_names = [n for n in names if categories.get(n) == 'alphabet']
    nl_indices = [names.index(n) for n in nl_names]
    if nl_indices:
        nl_matrix = X[nl_indices]
        nl_mu = nl_matrix.mean(axis=0)
        nl_sigma = nl_matrix.std(axis=0)
        nl_sigma[nl_sigma == 0] = 1

        vms_vec = X[0]
        pr(f"{'Feature':<16s} {'VMS':>8s} {'NL mean':>8s} {'NL std':>8s} {'z-score':>8s} {'Verdict':>12s}")
        pr("-" * 66)
        for j, fk in enumerate(feature_keys):
            z = (vms_vec[j] - nl_mu[j]) / nl_sigma[j]
            verdict = "NORMAL" if abs(z) < 2 else ("ANOMALOUS" if abs(z) < 3 else "EXTREME")
            pr(f"  {fk:<14s} {vms_vec[j]:>8.3f} {nl_mu[j]:>8.3f} {nl_sigma[j]:>8.3f} {z:>8.2f} {verdict:>12s}")
        pr()

    # ── Sample size caveat ──
    pr("=" * 70)
    pr("58f) SAMPLE SIZE CAVEATS")
    pr("=" * 70)
    pr()
    pr("Corpus sizes used:")
    for key in ordered:
        m = results[key]
        if m is None: continue
        pr(f"  {m['name']:<28s}  {m['n_words']:>8d} words  {m['n_chars']:>8d} chars")
    pr()
    pr("NOTE: Embedded samples (Japanese, Korean, Arabic, Hawaiian) are SHORT")
    pr("(hundreds of words). Their entropy and TTR estimates are LESS STABLE")
    pr("than the Gutenberg references (tens of thousands of words).")
    pr("Sukhotin's algorithm is also less reliable on short texts.")
    pr("These samples provide DIRECTIONAL information only.")
    pr()

    # ── Summary ──
    pr("=" * 70)
    pr("cross_script_fingerprint SYNTHESIS")
    pr("=" * 70)
    pr()

    # Find VMS's rank and nearest neighbor
    vms_rank = [i for i, (d, n) in enumerate(dists) if 'VMS' in n][0]
    nearest = [(d, n) for d, n in dists if 'VMS' not in n]
    if nearest:
        pr(f"VMS nearest neighbor: {nearest[0][1]} (distance {nearest[0][0]:.3f})")
        pr(f"VMS 2nd nearest:      {nearest[1][1]} (distance {nearest[1][0]:.3f})")
        pr(f"VMS 3rd nearest:      {nearest[2][1]} (distance {nearest[2][0]:.3f})")
        pr()

    # Count category representation in top-3 neighbors
    top3_cats = [categories.get(n, '?') for _, n in nearest[:3]]
    pr(f"Top-3 neighbor categories: {', '.join(top3_cats)}")
    pr()

    # Key discriminating features
    pr("Key observations:")
    vms_m = results['VMS']
    pr(f"  IC = {vms_m['IC']:.4f}  (alphabets typically 0.06-0.08; "
       f"syllabaries 0.01-0.03)")
    pr(f"  H-ratio = {vms_m['H_ratio']:.3f}  (low = more bigram predictability)")
    pr(f"  Alpha size = {vms_m['alpha_size']}  (alphabets 20-30; syllabaries 40-80+)")
    pr(f"  V-fraction = {vms_m['V_frac']:.3f}  (alphabets ~0.2-0.4; "
       f"degenerate = possible artifact)")
    pr(f"  V/C alternation = {vms_m['VC_alt']:.3f}")
    pr()

    # Save results to JSON for downstream use
    out_path = Path("results/cross_script_fingerprint_output.json")
    out_path.parent.mkdir(exist_ok=True)
    json_data = {}
    for key in ordered:
        m = results[key]
        if m is None: continue
        json_data[key] = {k: float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v
                          for k, v in m.items()}
    with open(out_path, 'w') as f:
        json.dump(json_data, f, indent=2, default=str)
    pr(f"Results saved to {out_path}")

if __name__ == '__main__':
    main()
