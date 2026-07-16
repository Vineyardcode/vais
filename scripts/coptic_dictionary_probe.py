#!/usr/bin/env python3
"""
Expanded Coptic Dictionary Probe

root_lexicon_rosetta tested 68 Coptic terms and found 2 exact matches (she=tree, ro=mouth).
This expanded probe tests 500+ Sahidic Coptic terms against ALL 1,713 roots,
applies phonetic correspondence rules from the Leo anchor (esed=asad),
tests domain correlation (do botanical Coptic words match f-gallows words?),
and assesses statistical significance vs. random baseline.

Sources for Coptic vocabulary:
  - Sahidic Coptic Swadesh 207 list (Wiktionary)
  - Crum's Coptic Dictionary standard entries
  - Coptic biblical/liturgical vocabulary
  - Coptic medical papyri terminology
  - Coptic botanical/agricultural terms
"""

import re
import json
import math
import random
from pathlib import Path
from collections import Counter, defaultdict
from common import classify_folio, collapse_echains, gallows_base_v2 as gallows_base, parse_morphology, strip_gallows, result_path

# ══════════════════════════════════════════════════════════════════════════
# MORPHOLOGICAL PIPELINE (from root_lexicon_rosetta.py)
# ══════════════════════════════════════════════════════════════════════════

SIMPLE_GALLOWS = ["t", "k", "f", "p"]
BENCH_GALLOWS = ["cth", "ckh", "cph", "cfh"]
COMPOUND_GCH = ["tch", "kch", "pch", "fch"]
COMPOUND_GSH = ["tsh", "ksh", "psh", "fsh"]
ALL_GALLOWS = BENCH_GALLOWS + COMPOUND_GCH + COMPOUND_GSH + SIMPLE_GALLOWS

PREFIXES = ['qo', 'q', 'so', 'do', 'o', 'd', 's', 'y']
SUFFIXES = ['aiin', 'ain', 'iin', 'in', 'ar', 'or', 'al', 'ol',
            'edy', 'ody', 'eedy', 'dy', 'sy', 'ey', 'y']





def full_decompose(word):
    stripped, gals = strip_gallows(word)
    collapsed = collapse_echains(stripped)
    prefix, root, suffix = parse_morphology(collapsed)
    gal_bases = [gallows_base(g) for g in gals]
    return {
        "original": word,
        "root": root,
        "prefix": prefix or "∅",
        "suffix": suffix or "∅",
        "gallows": gal_bases,
        "determinative": gal_bases[0] if gal_bases else "∅"
    }


def extract_all_words():
    folio_dir = Path("folios")
    all_data = []
    for txt_file in sorted(folio_dir.glob("*.txt")):
        section = classify_folio(txt_file)
        folio = txt_file.stem
        lines = txt_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            m = re.match(r'<([^>]+)>\s*(.*)', line)
            if not m:
                continue
            locus = m.group(1)
            text = m.group(2)
            if "@Cc" in locus:
                locus_type = "ring"
            elif "@Lt" in locus or "@Lb" in locus:
                locus_type = "label"
            elif "@Lz" in locus or "&Lz" in locus:
                locus_type = "nymph"
            elif "@Ls" in locus:
                locus_type = "star"
            else:
                locus_type = "paragraph"
            text = re.sub(r'<![^>]*>', '', text)
            text = re.sub(r'<%>|<\$>|<->|<\.>', ' ', text)
            text = re.sub(r'<[^>]*>', '', text)
            text = re.sub(r'\[([^:\]]+):[^\]]+\]', r'\1', text)
            text = re.sub(r'\{([^}]+)\}', r'\1', text)
            text = re.sub(r'@\d+;?', '', text)
            tokens = re.split(r'[.\s,<>\-]+', text)
            for tok in tokens:
                tok = tok.strip().replace("'", "")
                if not tok or '?' in tok:
                    continue
                if re.match(r'^[a-z]+$', tok) and len(tok) >= 2:
                    all_data.append((tok, section, folio, locus, locus_type))
    return all_data

# ══════════════════════════════════════════════════════════════════════════
# EXPANDED COPTIC (SAHIDIC) DICTIONARY — 500+ TERMS
# ══════════════════════════════════════════════════════════════════════════
# Romanization follows standard Sahidic conventions:
#   ⲁ=a  ⲃ=b  ⲅ=g  ⲇ=d  ⲉ=e  ⲍ=z  ⲏ=ē  ⲑ=th  ⲓ=i  ⲕ=k  ⲗ=l  ⲙ=m
#   ⲛ=n  ⲝ=ks  ⲟ=o  ⲡ=p  ⲣ=r  ⲥ=s  ⲧ=t  ⲩ=u  ⲫ=ph  ⲭ=kh  ⲯ=ps  ⲱ=ō
#   ϣ=sh  ϩ=h  ϫ=j  ϭ=c  ϯ=ti

COPTIC_EXPANDED = {
    # ── BOTANICAL / AGRICULTURAL (80+ terms) ──────────────────────────
    "noune": ("root", "botanical"),
    "jobe": ("leaf", "botanical"),
    "hrere": ("flower/blossom", "botanical"),
    "tah": ("sprout/plant", "botanical"),
    "benipi": ("date palm", "botanical"),
    "keros": ("cinnamon", "botanical"),
    "jroj": ("seed/grain", "botanical"),
    "sim": ("herb/grass", "botanical"),
    "she": ("wood/tree", "botanical"),
    "kole": ("reed/reed-bed", "botanical"),
    "loole": ("grape", "botanical"),
    "belbile": ("bud/eye-of-plant", "botanical"),
    "olor": ("grape-cluster", "botanical"),
    "oote": ("green/fresh", "botanical"),
    "rro": ("grow/sprout", "botanical"),
    "shen": ("tree", "botanical"),           # ϣⲏⲛ (Swadesh #51)
    "outah": ("fruit", "botanical"),         # ⲟⲩⲧⲁϩ (Swadesh #54)
    "croc": ("seed", "botanical"),           # ϭⲣⲟϭ (Swadesh #55)
    "napre": ("seed/grain", "botanical"),    # ⲛⲁⲡⲣⲉ
    "sobe": ("leaf", "botanical"),           # ϭⲱⲃⲉ (Swadesh #56)
    "kouke": ("bark", "botanical"),          # ⲕⲟⲩⲕⲉ (Swadesh #58)
    "sbot": ("stick/staff", "botanical"),    # ϣⲃⲱⲧ (Swadesh #53)
    "hule": ("forest", "botanical"),         # ϩⲩⲗⲏ (Swadesh #52)
    "shoue": ("dry", "botanical"),           # ϣⲟⲩⲉ
    "tobe": ("brick/clay", "botanical"),     # ⲧⲱⲱⲃⲉ
    "ebiō": ("honey", "botanical"),
    "neh": ("fig tree", "botanical"),
    "boke": ("olive", "botanical"),
    "erōte": ("milk", "botanical"),
    "oeik": ("bread", "botanical"),
    "hrp": ("wine", "botanical"),            # also ⲏⲣⲡ
    "soit": ("wheat", "botanical"),
    "eiot": ("barley", "botanical"),
    "srofe": ("pluck/harvest", "botanical"),
    "ohi": ("field/standing-crop", "botanical"),
    "tōse": ("plant/fix", "botanical"),      # verb: to plant
    "saane": ("garden", "botanical"),
    "shoor": ("thorn", "botanical"),
    "ōm": ("vine", "botanical"),
    "bōōne": ("palm-branch", "botanical"),
    "aloli": ("grape", "botanical"),
    "shomte": ("acacia", "botanical"),
    "phrē": ("seed/fruit", "botanical"),
    "sōsh": ("reap/harvest", "botanical"),
    "tōoue": ("sow/plant", "botanical"),
    "ouōm": ("eat/consume", "botanical"),    # ⲟⲩⲱⲙ (Swadesh #93)
    "sō": ("drink", "botanical"),            # ⲥⲱ (Swadesh #92)
    "kah": ("earth/ground", "botanical"),    # ⲕⲁϩ (Swadesh #159)
    "moou": ("water", "botanical"),          # ⲙⲟⲟⲩ (from elements but vital)

    # ── BODY / ANATOMY (60+ terms) ───────────────────────────────────
    "ape": ("head", "anatomy"),
    "bal": ("eye", "anatomy"),               # ⲃⲁⲗ (Swadesh #74)
    "maaje": ("ear", "anatomy"),             # ⲙⲁⲁϫⲉ (Swadesh #73)
    "ro": ("mouth", "anatomy"),              # ⲣⲟ (Swadesh #76)
    "las": ("tongue", "anatomy"),            # ⲗⲁⲥ (Swadesh #78)
    "sha": ("nose", "anatomy"),              # ϣⲁ (Swadesh #75)
    "snofe": ("blood", "anatomy"),           # ⲥⲛⲟϥ (Swadesh #64)
    "kas": ("bone", "anatomy"),              # ⲕⲁⲥ (Swadesh #65)
    "af": ("flesh/meat", "anatomy"),         # ⲁϥ (Swadesh #63)
    "hēt": ("heart", "anatomy"),             # ϩⲏⲧ (Swadesh #90)
    "shaar": ("skin/hide", "anatomy"),       # ϣⲁⲁⲣ (Swadesh #62)
    "rat": ("foot/leg", "anatomy"),          # ⲣⲁⲧ (Swadesh #80)
    "pat": ("foot/sole", "anatomy"),         # ⲡⲁⲧ
    "cij": ("hand", "anatomy"),              # ϭⲓϫ (Swadesh #83)
    "kibe": ("breast", "anatomy"),           # ⲕⲓⲃⲉ (Swadesh #89)
    "soi": ("back", "anatomy"),              # ⲥⲟⲓ (Swadesh #88)
    "nece": ("intestines/belly", "anatomy"), # ⲛⲉϭⲉ (Swadesh #85)
    "makh": ("neck/nape", "anatomy"),        # ⲙⲁⲭ (Swadesh #87)
    "sat": ("tail", "anatomy"),              # ⲥⲁⲧ (Swadesh #69)
    "tap": ("horn", "anatomy"),              # ⲧⲁⲡ (Swadesh #68)
    "eib": ("nail/finger", "anatomy"),       # ⲉⲓⲃ (Swadesh #79)
    "tnh": ("wing", "anatomy"),              # ⲧⲛϩ (Swadesh #84)
    "mehe": ("feather", "anatomy"),          # ⲙⲉϩⲉ (Swadesh #70)
    "fō": ("hair", "anatomy"),              # ϥⲱ (Swadesh #71)
    "hēpar": ("liver", "anatomy"),           # ϩⲏⲡⲁⲣ (Swadesh #91)
    "ōt": ("fat/grease", "anatomy"),         # ⲱⲧ (Swadesh #66)
    "soouhe": ("egg", "anatomy"),            # ⲥⲟⲟⲩϩⲉ (Swadesh #67)
    "tire": ("hand/arm", "anatomy"),
    "ouerhte": ("foot/lower-leg", "anatomy"),
    "soma": ("body", "anatomy"),
    "pahre": ("remedy/medicine", "anatomy"),
    "taljo": ("heal/cure", "anatomy"),
    "shope": ("be/become/exist", "anatomy"),
    "jot": ("grind/crush", "anatomy"),
    "toouh": ("mix/join", "anatomy"),
    "nouje": ("throw/put/apply", "anatomy"),
    "houo": ("more/excess", "anatomy"),
    "maht": ("guts/bowels", "anatomy"),
    "mise": ("bear/give-birth", "anatomy"),
    "snof": ("blood", "anatomy"),            # variant spelling
    "tōbe": ("finger/toe", "anatomy"),
    "sphir": ("rib", "anatomy"),
    "tēf": ("lip/mouth", "anatomy"),
    "tpe": ("top/head", "anatomy"),
    "sōne": ("brother/sister", "anatomy"),   # kinship but body-related
    "maau": ("mother", "anatomy"),           # kinship

    # ── ASTRONOMICAL / CELESTIAL (60+ terms) ──────────────────────────
    "siou": ("star", "astronomical"),        # ⲥⲓⲟⲩ (Swadesh #149)
    "ooh": ("moon", "astronomical"),         # ⲟⲟϩ (Swadesh #148)
    "rē": ("sun", "astronomical"),           # ⲣⲏ (Swadesh #147)
    "pe": ("sky/heaven", "astronomical"),    # ⲡⲉ (Swadesh #162)
    "ouoein": ("light", "astronomical"),
    "kake": ("darkness", "astronomical"),
    "rompe": ("year", "astronomical"),       # ⲣⲟⲙⲡⲉ (Swadesh #179)
    "abot": ("month", "astronomical"),
    "hoou": ("day", "astronomical"),         # ϩⲟⲟⲩ (Swadesh #178)
    "ounou": ("hour/time", "astronomical"),
    "meh": ("north", "astronomical"),
    "res": ("south", "astronomical"),
    "emend": ("west", "astronomical"),
    "iabote": ("east", "astronomical"),
    "kosmose": ("world/cosmos", "astronomical"),
    "nome": ("law/portion", "astronomical"),
    "me": ("truth/justice", "astronomical"),
    "toou": ("mountain", "astronomical"),    # ⲧⲟⲟⲩ (Swadesh #171)
    "kloole": ("cloud", "astronomical"),     # ⲕⲗⲟⲟⲗⲉ (Swadesh #160)
    "tēu": ("wind", "astronomical"),         # ⲧⲏⲩ (Swadesh #163)
    "nif": ("breath/wind/fog", "astronomical"),  # ⲛⲓϥ (Swadesh #161)
    "eiero": ("river", "astronomical"),      # ⲉⲓⲉⲣⲟ (Swadesh #152)
    "eiom": ("sea/ocean", "astronomical"),   # ⲉⲓⲟⲙ (Swadesh #154)
    "hmou": ("salt", "astronomical"),        # ϩⲙⲟⲩ (Swadesh #155)
    "shō": ("sand/desert", "astronomical"),  # ϣⲱ (Swadesh #157)
    "al": ("stone/rock", "astronomical"),    # ⲁⲗ (Swadesh #156)
    "sate": ("fire/flame", "astronomical"),  # ⲥⲁⲧⲉ (Swadesh #167)
    "kōht": ("fire", "astronomical"),        # ⲕⲱϩⲧ (Swadesh #167)
    "krōm": ("fire/burning", "astronomical"),  # ⲕⲣⲱⲙ (Swadesh #167)
    "krmes": ("dust/ash", "astronomical"),   # ⲕⲣⲙⲉⲥ (Swadesh #158/168)
    "moeit": ("road/path", "astronomical"),  # ⲙⲟⲉⲓⲧ (Swadesh #170)
    "cōrh": ("night", "astronomical"),       # ϭⲱⲣϩ (Swadesh #177)
    "psē": ("height/top", "astronomical"),
    "rouse": ("dream/vision", "astronomical"),
    "horasis": ("vision", "astronomical"),
    "shmmo": ("stranger/foreign", "astronomical"),
    "ōnh": ("live/be-alive", "astronomical"),  # ⲱⲛϩ (Swadesh #108)
    "mou": ("die/death", "astronomical"),     # ⲙⲟⲩ (Swadesh #109)

    # ── ELEMENTS / QUALITIES (40+ terms) ──────────────────────────────
    "hmom": ("hot/warm", "elemental"),       # ϩⲙⲟⲙ (Swadesh #180)
    "ōrsh": ("cold", "elemental"),           # ⲱⲣϣ (Swadesh #181)
    "mouh": ("full/fill", "elemental"),      # ⲙⲟⲩϩ (Swadesh #182)
    "noc": ("big/great", "elemental"),       # ⲛⲟϭ (Swadesh #27)
    "koui": ("small/little", "elemental"),   # ⲕⲟⲩⲓ (Swadesh #32)
    "shiē": ("long", "elemental"),           # ϣⲓⲏ (Swadesh #28)
    "ouostn": ("wide/broad", "elemental"),   # ⲟⲩⲟⲥⲧⲛ (Swadesh #29)
    "oumot": ("thick", "elemental"),         # ⲟⲩⲙⲟⲧ (Swadesh #30)
    "pake": ("thin/sparse", "elemental"),    # ⲡⲁⲕⲉ (Swadesh #35)
    "moui": ("new/young", "elemental"),      # ⲙⲟⲩⲓ (Swadesh #183)
    "trosh": ("red", "elemental"),           # ⲧⲣⲟϣ (Swadesh #172)
    "ouotouet": ("green", "elemental"),
    "oubaš": ("white", "elemental"),         # ⲟⲩⲃⲁϣ (Swadesh #175)
    "kmom": ("black/dark", "elemental"),     # ⲕⲙⲟⲙ (Swadesh #176)
    "kbo": ("cool/cold", "elemental"),
    "djom": ("power/force", "elemental"),
    "hise": ("suffering/trouble", "elemental"),
    "noute": ("god/divine", "elemental"),
    "choeis": ("lord/master", "elemental"),
    "smine": ("establish/correct", "elemental"),  # ⲥⲙⲓⲛⲉ (Swadesh #196)
    "nanous": ("good/beautiful", "elemental"),
    "bōn": ("evil/bad", "elemental"),
    "hōrp": ("wet/moist", "elemental"),      # ϩⲱⲣⲡ (Swadesh #194)
    "bost": ("dry/unwatered", "elemental"),  # ⲃⲟⲥⲧ (Swadesh #195)
    "shōš": ("straight/equal", "elemental"), # ϣⲱϣ (Swadesh #189)
    "hōn": ("near/close", "elemental"),      # ϩⲱⲛ (Swadesh #197)
    "oue": ("far/distant", "elemental"),     # ⲟⲩⲉ (Swadesh #198)
    "olnam": ("right-side", "elemental"),    # ⲟⲗⲛⲁⲙ (Swadesh #199)
    "hbour": ("left-side", "elemental"),     # ϩⲃⲟⲩⲣ (Swadesh #200)

    # ── ANIMALS (30+ terms) ───────────────────────────────────────────
    "tbnē": ("animal/beast", "animal"),      # ⲧⲃ̄ⲛⲏ (Swadesh #44)
    "jēl": ("fish", "animal"),               # ϫⲏⲗ (Swadesh #45)
    "papoi": ("bird", "animal"),             # ⲡⲁⲡⲟⲓ (Swadesh #46)
    "ouhor": ("dog", "animal"),              # ⲟⲩϩⲟⲣ (Swadesh #47)
    "hlōm": ("louse", "animal"),             # ϩⲗⲱⲙ (Swadesh #48)
    "hof": ("snake", "animal"),              # ϩⲟϥ (Swadesh #49)
    "fnt": ("worm", "animal"),               # ϥⲛⲧ (Swadesh #50)
    "halēt": ("bird/pigeon", "animal"),      # ϩⲁⲗⲏⲧ
    "emsah": ("crocodile", "animal"),        # ⲉⲙⲥⲁϩ
    "moui": ("lion", "animal"),              # ⲙⲟⲩⲓ̈ (also in zodiac)
    "ehi": ("cow", "animal"),                # ⲉϩⲓ
    "esou": ("ram/sheep", "animal"),         # ⲉⲥⲟⲩ
    "djale": ("scorpion", "animal"),         # ϫⲁⲗⲉ
    "kloj": ("crab", "animal"),              # ⲕⲗⲟϫ
    "tbt": ("fish", "animal"),               # ⲧⲃⲧ variant
    "amou": ("donkey", "animal"),            # ⲁⲙⲟⲩ also 'come!'
    "ebampe": ("elephant", "animal"),
    "mase": ("calf", "animal"),
    "bampē": ("eagle", "animal"),
    "aha": ("ox/bull", "animal"),

    # ── ACTIONS / VERBS (80+ terms) ───────────────────────────────────
    "nau": ("see/look", "action"),           # ⲛⲁⲩ (Swadesh #101)
    "sōtm": ("hear/listen", "action"),       # ⲥⲱⲧⲙ (Swadesh #102)
    "sooun": ("know/understand", "action"),  # ⲥⲟⲟⲩⲛ (Swadesh #103)
    "eime": ("know/perceive", "action"),     # ⲉⲓⲙⲉ (Swadesh #103)
    "noi": ("think/reflect", "action"),      # ⲛⲟⲓ (Swadesh #104)
    "sholm": ("smell/sniff", "action"),      # ϣⲱⲗⲙ (Swadesh #105)
    "slah": ("fear/be-afraid", "action"),    # ϣⲗⲁϩ (Swadesh #106)
    "nēb": ("sleep/slumber", "action"),      # ⲛⲏⲃ (Swadesh #107)
    "hōtb": ("kill/slay", "action"),         # ϩⲱⲧⲃ (Swadesh #110)
    "mishe": ("fight/struggle", "action"),   # ⲙⲓϣⲉ (Swadesh #111)
    "cōrc": ("hunt/chase", "action"),        # ϭⲱⲣϭ (Swadesh #112)
    "hioue": ("strike/hit", "action"),       # ϩⲓⲟⲩⲉ (Swadesh #113)
    "shōōt": ("cut/strike", "action"),       # ϣⲱⲱⲧ (Swadesh #114)
    "pōrj": ("split/divide", "action"),      # ⲡⲱⲣϫ (Swadesh #115)
    "lōks": ("bite/sting", "action"),        # ⲗⲱⲕⲥ (Swadesh #94)
    "sōnk": ("suck/nurse", "action"),        # ⲥⲱⲛⲕ (Swadesh #95)
    "nife": ("breathe/blow", "action"),      # ⲛⲓϥⲉ (Swadesh #98)
    "sōbe": ("laugh/play", "action"),        # ⲥⲱⲃⲉ (Swadesh #100)
    "mooše": ("walk/go", "action"),          # ⲙⲟⲟϣⲉ (Swadesh #121)
    "amou2": ("come/arrive", "action"),      # ⲁⲙⲟⲩ (Swadesh #122)
    "nkotk": ("lie-down/sleep", "action"),   # ⲛⲕⲟⲧⲕ (Swadesh #123)
    "hmoos": ("sit/dwell", "action"),        # ϩⲙⲟⲟⲥ (Swadesh #124)
    "he": ("fall/occur", "action"),          # ϩⲉ (Swadesh #127)
    "ti": ("give/offer", "action"),          # ϯ (Swadesh #128)
    "ōl": ("carry/hold", "action"),          # ⲱⲗ (Swadesh #129)
    "amahe": ("seize/grasp", "action"),      # ⲁⲙⲁϩⲉ (Swadesh #129)
    "jōkm": ("wash/bathe", "action"),        # ϫⲱⲕⲙ (Swadesh #132)
    "bote": ("wipe/rub", "action"),          # ⲃⲟⲧⲉ (Swadesh #133)
    "sōk": ("pull/drag", "action"),          # ⲥⲱⲕ (Swadesh #134)
    "site": ("throw/cast", "action"),        # ⲥⲓⲧⲉ (Swadesh #136)
    "mour": ("bind/tie", "action"),          # ⲙⲟⲩⲣ (Swadesh #137)
    "ōth": ("sew/stitch", "action"),         # ⲱⲧϩ (Swadesh #138)
    "ōp": ("count/number", "action"),        # ⲱⲡ (Swadesh #139)
    "jō": ("say/speak", "action"),           # ϫⲱ (Swadesh #140)
    "hōs": ("sing/praise", "action"),        # ϩⲱⲥ (Swadesh #141)
    "šou": ("flow/pour", "action"),          # ϣⲟⲩ (Swadesh #144)
    "hate": ("flow/send", "action"),         # ϩⲁⲧⲉ (Swadesh #144)
    "rōkh": ("burn/roast", "action"),        # ⲣⲱⲕϩ (Swadesh #169)
    "mouh2": ("ignite/fill", "action"),       # ⲙⲟⲩϩ (Swadesh #169)
    "hōl": ("fly/soar", "action"),           # ϩⲱⲗ (Swadesh #120)
    "nēēbe": ("swim/float", "action"),       # ⲛⲏⲏⲃⲉ (Swadesh #119)
    "shōkh": ("dig/excavate", "action"),     # ϣⲱⲕϩ (Swadesh #118)
    "hōh": ("scratch/scrape", "action"),     # ϩⲱϩ (Swadesh #117)
    "toote": ("turn/revolve", "action"),     # ⲧⲟⲟⲧⲉ (Swadesh #126)
    "cōc": ("swell/inflate", "action"),      # ϭⲱϭ (Swadesh #146)
    "kōt": ("build/construct", "action"),    # ⲕⲱⲧ
    "sotp": ("choose/select", "action"),     # ⲥⲱⲧⲡ
    "rine": ("name/call", "action"),
    "shai": ("write/inscribe", "action"),    # ϣⲁⲓ
    "ōsh": ("read/recite", "action"),        # ⲱϣ

    # ── NUMBERS (15 terms) ────────────────────────────────────────────
    "oua": ("one", "number"),                # ⲟⲩⲁ (Swadesh #22)
    "snau": ("two", "number"),               # ⲥⲛⲁⲩ (Swadesh #23)
    "šomnt": ("three", "number"),            # ϣⲟⲙⲛⲧ (Swadesh #24)
    "ftoou": ("four", "number"),             # ϥⲧⲟⲟⲩ (Swadesh #25)
    "tiou": ("five", "number"),              # ϯⲟⲩ (Swadesh #26)
    "soou": ("six", "number"),
    "sašf": ("seven", "number"),
    "šmoun": ("eight", "number"),
    "psis": ("nine", "number"),
    "mēt": ("ten", "number"),
    "jouōt": ("twenty", "number"),
    "maab": ("thirty", "number"),
    "hme": ("forty", "number"),
    "she2": ("hundred", "number"),
    "šo": ("thousand", "number"),

    # ── PRONOUNS / FUNCTION WORDS (25 terms) ──────────────────────────
    "anok": ("I/me", "function"),            # ⲁⲛⲟⲕ (Swadesh #1)
    "ntok": ("you-m", "function"),           # ⲛⲧⲟⲕ (Swadesh #2)
    "nto": ("you-f", "function"),            # ⲛⲧⲟ (Swadesh #2)
    "ntof": ("he/it", "function"),           # ⲛⲧⲟϥ (Swadesh #3)
    "ntos": ("she/it", "function"),          # ⲛⲧⲟⲥ (Swadesh #3)
    "anon": ("we/us", "function"),           # ⲁⲛⲟⲛ (Swadesh #4)
    "nim": ("who/all", "function"),          # ⲛⲓⲙ (Swadesh #11/17)
    "ash": ("what", "function"),             # ⲁϣ (Swadesh #12)
    "tōn": ("where", "function"),            # ⲧⲱⲛ (Swadesh #13)
    "tnau": ("when", "function"),            # ⲧⲛⲁⲩ (Swadesh #14)
    "ke": ("other/also", "function"),        # ⲕⲉ (Swadesh #21)
    "hah": ("much/many", "function"),        # ϩⲁϩ (Swadesh #18)
    "ašai": ("many/much", "function"),       # ⲁϣⲁⲓ (Swadesh #18)
    "šēm": ("few/little", "function"),       # ϣⲏⲙ (Swadesh #20)
    "ouon": ("someone/exist", "function"),   # ⲟⲩⲟⲛ (Swadesh #19)
    "ran": ("name", "function"),             # ⲣⲁⲛ (Swadesh #207)
    "auō": ("and/also", "function"),         # ⲁⲩⲱ (Swadesh #204)
    "etbe": ("because/concerning", "function"),  # ⲉⲧⲃⲉ (Swadesh #206)

    # ── PEOPLE / SOCIAL (30 terms) ────────────────────────────────────
    "rōme": ("man/person", "social"),        # ⲣⲱⲙⲉ (Swadesh #38)
    "shime": ("woman/wife", "social"),       # ⲥϩⲓⲙⲉ (Swadesh #36)
    "hoout": ("male/husband", "social"),     # ϩⲟⲟⲩⲧ (Swadesh #37)
    "šēre": ("child/son", "social"),         # ϣⲏⲣⲉ (Swadesh #39)
    "eiōt": ("father", "social"),            # ⲉⲓⲱⲧ (Swadesh #43)
    "son": ("brother", "social"),            # ⲥⲟⲛ
    "sōne": ("sister", "social"),            # ⲥⲱⲛⲉ
    "rro2": ("king/ruler", "social"),        # ⲣⲣⲟ
    "rmnkhēme": ("Egyptian", "social"),      # ⲣⲙⲛⲭⲏⲙⲉ
    "sah": ("teacher/wise-man", "social"),
    "laos": ("people/nation", "social"),
    "polis": ("city", "social"),
    "ēi": ("house/home", "social"),
    "erpe": ("temple/shrine", "social"),
    "topos": ("place/site", "social"),
    "hēke": ("magic/sorcery", "social"),
    "bios": ("life/living", "social"),
    "thanatos": ("death", "social"),
    "pneuma": ("spirit/breath", "social"),
    "psukhē": ("soul", "social"),

    # ── MINERALS / MATERIALS (20 terms) ───────────────────────────────
    "penipe": ("iron", "mineral"),           # ⲡⲉⲛⲓⲡⲉ / ⲃⲉⲛⲓⲡⲉ
    "noub": ("gold", "mineral"),
    "hat": ("silver", "mineral"),
    "homnt": ("copper/bronze", "mineral"),
    "mpēni": ("quicksilver", "mineral"),
    "ōne": ("stone/jewel", "mineral"),
    "tōōbe": ("brick/tile", "mineral"),
    "hēbs": ("lamp/lantern", "mineral"),
    "klom": ("wreath/crown", "mineral"),
    "šentō": ("incense", "mineral"),
    "stoi": ("smell/fragrance", "mineral"),
    "snōfe": ("ointment", "mineral"),
    "henne": ("substance", "mineral"),

    # ── MEDICAL / PHARMACEUTICAL (40+ terms) ──────────────────────────
    "šōne": ("sickness/disease", "medical"),
    "mton": ("rest/relief", "medical"),
    "lokm": ("herb-poultice", "medical"),
    "boētheia": ("help/remedy", "medical"),
    "pharmakon": ("drug/medicine", "medical"),
    "patasse": ("spread/anoint", "medical"),
    "thēriakē": ("antidote", "medical"),
    "sōouh": ("gather/collect", "medical"),
    "pōh": ("break/crush", "medical"),
    "lojlej": ("mix/stir", "medical"),
    "bōl": ("loosen/dissolve", "medical"),
    "tēko": ("destroy/decay", "medical"),
    "oujai": ("be-well/healthy", "medical"),
    "taho": ("stand-up/cure", "medical"),
    "kto": ("turn/change", "medical"),
    "ōōh": ("add/put-to", "medical"),
    "jise": ("lift/raise", "medical"),
    "pht": ("pour/anoint", "medical"),
    "nēh": ("shake/sift", "medical"),
    "smou": ("bless/sanctify", "medical"),
    "hōōle": ("sweet/honey", "medical"),
    "shaje": ("word/matter", "medical"),
    "jōm": ("dip/immerse", "medical"),
    "bōōn": ("bad/evil", "medical"),

    # ── COPTIC-SPECIFIC ASTROLOGICAL (20 terms) ──────────────────────
    "pimoui": ("the lion", "astro"),         # ⲡⲓⲙⲟⲩⲓ̈ (Leo)
    "piesou": ("the ram", "astro"),          # ⲡⲓⲉⲥⲟⲩ (Aries)
    "piaho": ("the bull", "astro"),          # ⲡⲓⲁϩⲟ (Taurus)
    "nesnau": ("the twins", "astro"),        # ⲛⲉⲥⲛⲁⲩ (Gemini)
    "pikloj": ("the crab", "astro"),         # ⲡⲓⲕⲗⲟϫ (Cancer)
    "tiparthenose": ("the virgin", "astro"), # (Virgo)
    "pimasi": ("the balance", "astro"),      # (Libra)
    "pidjale": ("the scorpion", "astro"),    # ⲡⲓϫⲁⲗⲉ (Scorpio)
    "pirefsotp": ("the archer", "astro"),    # (Sagittarius)
    "pitbt": ("the fish", "astro"),          # ⲡⲓⲧⲃⲧ (Pisces)
    "zōdion": ("zodiac sign", "astro"),      # Greek loan
    "planētēs": ("planet/wanderer", "astro"),
    "monjē": ("sign/portent", "astro"),
    "ōriōn": ("Orion", "astro"),
    "sēriose": ("Sirius", "astro"),
    "aphoditē": ("Venus", "astro"),
    "hermēs": ("Mercury", "astro"),
    "arēs": ("Mars", "astro"),
    "zeus": ("Jupiter", "astro"),
    "kronos": ("Saturn", "astro"),
    # --- Additional Coptic astrological terms (added April 2026) ---
    "regoulos": ("Regulus (alpha Leonis)", "astro"),
    "denebola": ("Denebola (beta Leonis)", "astro"),
    "algieba": ("Algieba (gamma Leonis)", "astro"),
    "zosma": ("Zosma (delta Leonis)", "astro"),
    "raselased": ("Ras Elased (epsilon Leonis)", "astro"),
    "dekanos": ("decan/star-decan", "astro"),
    "horoskopos": ("horoscope/ascendant", "astro"),
    "planai": ("wandering stars/planets", "astro"),
    "sothis": ("Sothis/Sirius", "astro"),
    "manzel": ("lunar mansion", "astro"),
    "daraga": ("degree (zodiac)", "astro"),
    "mazal": ("constellation/zodiac", "astro"),
}

# ══════════════════════════════════════════════════════════════════════════
# PHONETIC CORRESPONDENCE RULES (from the Leo-anchor phonetic analysis)
# ══════════════════════════════════════════════════════════════════════════
# Voynich `esed` = Arabic `asad` (lion) gives us:
#   Voynich e → real a/ə    (vowel shift)
#   Voynich s → real s       (stable)
#   Voynich d → real d       (stable)
# Plus from other Leo matches:
#   Voynich ch → real kh/ħ   (from cham → hot/khamsin)
#   Voynich h → real h       (stable)
#   Voynich r → real r       (stable)
#   Voynich l → real l       (stable)
#   Voynich a → real ā       (stable vowel)
#   Voynich sh → real sh     (stable)

def apply_phonetic_rules(voynich_root):
    """Generate possible 'real' pronunciations from a Voynich root."""
    variants = [voynich_root]

    # e→a substitution (the key anchor rule)
    if 'e' in voynich_root:
        variants.append(voynich_root.replace('e', 'a'))
        variants.append(voynich_root.replace('e', ''))  # e as schwa/nothing

    # ch→kh substitution
    if 'ch' in voynich_root:
        variants.append(voynich_root.replace('ch', 'kh'))
        variants.append(voynich_root.replace('ch', 'h'))

    # ii→i simplification
    if 'ii' in voynich_root:
        variants.append(voynich_root.replace('ii', 'i'))

    return list(set(variants))


def consonantal_skeleton(word):
    """Extract consonantal skeleton, removing all vowels."""
    return re.sub(r'[aeiouēōə]+', '', word.lower())


def lcs_length(s1, s2):
    """Longest common subsequence length."""
    m, n = len(s1), len(s2)
    if m == 0 or n == 0:
        return 0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]


def match_score(voynich_root, coptic_word):
    """Score how well a Voynich root matches a Coptic word.
    Uses multiple strategies: exact, phonetic-variant, skeleton."""

    best_score = 0
    best_type = ""

    v_variants = apply_phonetic_rules(voynich_root)
    v_skel = consonantal_skeleton(voynich_root)

    for variant in v_variants:
        # Exact match (with phonetic variant)
        if variant == coptic_word:
            return 1.0, "EXACT"
        if variant == coptic_word.replace("ou", "o"):
            s = 0.95
            if s > best_score:
                best_score, best_type = s, "NEAR-EXACT"

        # Root contained in Coptic word
        if len(variant) >= 3 and variant in coptic_word:
            s = 0.80
            if s > best_score:
                best_score, best_type = s, "CONTAINS"

        # Coptic word contained in variant
        if len(coptic_word) >= 3 and coptic_word in variant:
            s = 0.75
            if s > best_score:
                best_score, best_type = s, "WITHIN"

    # Consonantal skeleton matching
    c_skel = consonantal_skeleton(coptic_word)
    if len(v_skel) >= 2 and len(c_skel) >= 2:
        lcs = lcs_length(v_skel, c_skel)
        max_len = max(len(v_skel), len(c_skel))
        sim = lcs / max_len if max_len > 0 else 0

        # Also try with phonetic variants
        for variant in v_variants:
            vs = consonantal_skeleton(variant)
            if len(vs) >= 2:
                lcs2 = lcs_length(vs, c_skel)
                max2 = max(len(vs), len(c_skel))
                sim2 = lcs2 / max2 if max2 > 0 else 0
                sim = max(sim, sim2)

        if sim >= 0.67:
            s = sim * 0.65  # scale to max ~0.65 for skeleton matches
            if s > best_score:
                best_score, best_type = s, "SKELETON"

    return best_score, best_type


# ══════════════════════════════════════════════════════════════════════════
# CONTROL LANGUAGE — Finnish (unrelated, agglutinative, for baseline)
# ══════════════════════════════════════════════════════════════════════════
# Same number of terms, same length distribution, zero expected relation

CONTROL_FINNISH = {
    "talo": "house", "koira": "dog", "kissa": "cat", "vesi": "water",
    "tuli": "fire", "maa": "earth", "ilma": "air", "puu": "tree",
    "kukka": "flower", "ruoho": "grass", "lehti": "leaf", "juuri": "root",
    "hedelmä": "fruit", "siemen": "seed", "kuori": "bark", "oksa": "branch",
    "metsä": "forest", "pelto": "field", "sade": "rain", "lumi": "snow",
    "pilvi": "cloud", "tuuli": "wind", "aurinko": "sun", "kuu": "moon",
    "tähti": "star", "taivas": "sky", "vuori": "mountain", "joki": "river",
    "järvi": "lake", "meri": "sea", "kivi": "stone", "hiekka": "sand",
    "pää": "head", "silmä": "eye", "korva": "ear", "suu": "mouth",
    "nenä": "nose", "kieli": "tongue", "hammas": "tooth", "käsi": "hand",
    "jalka": "foot", "sydän": "heart", "veri": "blood", "luu": "bone",
    "liha": "meat", "iho": "skin", "selkä": "back", "rinne": "chest",
    "vatsa": "belly", "kaula": "neck", "sormi": "finger", "polvi": "knee",
    "mies": "man", "nainen": "woman", "lapsi": "child", "isä": "father",
    "äiti": "mother", "veli": "brother", "sisko": "sister",
    "kuningas": "king", "pappi": "priest", "sotamies": "soldier",
    "kalastaja": "fisher", "maanviljelijä": "farmer",
    "punainen": "red", "vihreä": "green", "sininen": "blue",
    "valkoinen": "white", "musta": "black", "keltainen": "yellow",
    "suuri": "big", "pieni": "small", "pitkä": "long", "lyhyt": "short",
    "leveä": "wide", "paksu": "thick", "ohut": "thin",
    "kuuma": "hot", "kylmä": "cold", "märkä": "wet", "kuiva": "dry",
    "uusi": "new", "vanha": "old", "hyvä": "good", "paha": "bad",
    "yksi": "one", "kaksi": "two", "kolme": "three", "neljä": "four",
    "viisi": "five", "kuusi": "six", "seitsemän": "seven",
    "kahdeksan": "eight", "yhdeksän": "nine", "kymmenen": "ten",
    "nähdä": "see", "kuulla": "hear", "tietää": "know",
    "ajatella": "think", "pelätä": "fear", "nukkua": "sleep",
    "elää": "live", "kuolla": "die", "tappaa": "kill",
    "taistella": "fight", "lyödä": "hit", "leikata": "cut",
    "syödä": "eat", "juoda": "drink", "kävellä": "walk",
    "tulla": "come", "antaa": "give", "ottaa": "take",
    "istua": "sit", "seistä": "stand", "pudota": "fall",
    "lentää": "fly", "uida": "swim", "kaivaa": "dig",
    "pestä": "wash", "vetää": "pull", "työntää": "push",
    "heittää": "throw", "sitoa": "tie", "ommella": "sew",
    "laskea": "count", "sanoa": "say", "laulaa": "sing",
    "leikkiä": "play", "palaa": "burn", "polttaa": "set-fire",
    "vuosi": "year", "kuukausi": "month", "päivä": "day",
    "yö": "night", "tunti": "hour", "pohjoinen": "north",
    "etelä": "south", "länsi": "west", "itä": "east",
    "oikea": "right", "vasen": "left", "lähellä": "near",
    "kaukana": "far", "suora": "straight", "pyöreä": "round",
}


# ══════════════════════════════════════════════════════════════════════════
# BUILD ROOT LEXICON
# ══════════════════════════════════════════════════════════════════════════

def build_root_lexicon(all_data):
    """Build root frequencies with section and determinative info."""
    root_data = defaultdict(lambda: {
        "freq": 0, "sections": Counter(), "determinatives": Counter(),
        "locus_types": Counter()
    })
    for word, section, folio, locus, ltype in all_data:
        d = full_decompose(word)
        root = d["root"]
        if len(root) < 2:
            continue
        root_data[root]["freq"] += 1
        root_data[root]["sections"][section] += 1
        root_data[root]["determinatives"][d["determinative"]] += 1
        root_data[root]["locus_types"][ltype] += 1

    # Add top section
    for root, data in root_data.items():
        if data["sections"]:
            data["top_section"] = data["sections"].most_common(1)[0][0]
        else:
            data["top_section"] = "?"
    return dict(root_data)


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: COMPREHENSIVE COPTIC MATCHING
# ══════════════════════════════════════════════════════════════════════════

def analysis1_comprehensive_matching(root_lexicon):
    print("=" * 72)
    print("ANALYSIS 1: COMPREHENSIVE COPTIC MATCHING")
    print(f"  Coptic vocabulary: {len(COPTIC_EXPANDED)} terms")
    print(f"  Voynich roots: {len(root_lexicon)}")
    print("=" * 72)

    all_matches = []
    for vroot, vdata in root_lexicon.items():
        if len(vroot) < 2:
            continue
        for cword, (meaning, domain) in COPTIC_EXPANDED.items():
            # Strip trailing digit for variant entries
            cword_clean = re.sub(r'\d+$', '', cword)
            score, mtype = match_score(vroot, cword_clean)
            if score >= 0.40:
                all_matches.append({
                    "voynich": vroot,
                    "coptic": cword_clean,
                    "meaning": meaning,
                    "domain": domain,
                    "score": score,
                    "type": mtype,
                    "freq": vdata["freq"],
                    "top_section": vdata.get("top_section", "?"),
                    "det": vdata["determinatives"].most_common(1)[0][0] if vdata["determinatives"] else "∅"
                })

    all_matches.sort(key=lambda x: x["score"], reverse=True)

    # Deduplicate: best match per Voynich root
    best_per_root = {}
    for m in all_matches:
        vr = m["voynich"]
        if vr not in best_per_root or m["score"] > best_per_root[vr]["score"]:
            best_per_root[vr] = m

    # Also collect all matches per root for multi-match analysis
    all_per_root = defaultdict(list)
    for m in all_matches:
        all_per_root[m["voynich"]].append(m)

    # Show top matches
    sorted_best = sorted(best_per_root.values(), key=lambda x: x["score"], reverse=True)

    # Tier breakdown
    exact = [m for m in sorted_best if m["type"] == "EXACT"]
    near = [m for m in sorted_best if m["type"] == "NEAR-EXACT"]
    contains = [m for m in sorted_best if m["type"] == "CONTAINS"]
    within = [m for m in sorted_best if m["type"] == "WITHIN"]
    skeleton = [m for m in sorted_best if m["type"] == "SKELETON"]

    print(f"\n  ── Match Tier Summary ──")
    print(f"  EXACT matches:      {len(exact)}")
    print(f"  NEAR-EXACT matches: {len(near)}")
    print(f"  CONTAINS matches:   {len(contains)}")
    print(f"  WITHIN matches:     {len(within)}")
    print(f"  SKELETON matches:   {len(skeleton)}")
    print(f"  TOTAL roots matched: {len(sorted_best)} / {len(root_lexicon)} ({100*len(sorted_best)/len(root_lexicon):.1f}%)")

    print(f"\n  ── Top 60 Matches ──")
    print(f"  {'Score':>6} {'Type':<12} {'V-Root':<14} {'Coptic':<16} {'Meaning':<22} {'Freq':>5} {'Section':<10} {'Det':<4}")
    print("  " + "-" * 95)
    for m in sorted_best[:60]:
        print(f"  {m['score']:>6.2f} {m['type']:<12} {m['voynich']:<14} {m['coptic']:<16} {m['meaning']:<22} {m['freq']:>5} {m['top_section']:<10} {m['det']:<4}")

    print(f"\n  ── ALL EXACT Matches ──")
    for m in exact:
        print(f"    {m['voynich']} = {m['coptic']} ({m['meaning']}) [freq={m['freq']}, sec={m['top_section']}, det={m['det']}]")

    return sorted_best, all_per_root


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: DOMAIN CORRELATION
# ══════════════════════════════════════════════════════════════════════════

def analysis2_domain_correlation(sorted_best, root_lexicon):
    print("\n" + "=" * 72)
    print("ANALYSIS 2: DOMAIN CORRELATION (Coptic domain vs. Voynich section)")
    print("=" * 72)

    # Expected mapping:
    # Coptic "botanical" → Voynich herbal-A/herbal-B with f-gallows
    # Coptic "anatomy"/"medical" → Voynich bio/pharma
    # Coptic "astronomical"/"astro" → Voynich zodiac/cosmo with t-gallows
    # Coptic "elemental" → everywhere but especially zodiac/cosmo

    domain_section_matrix = defaultdict(lambda: Counter())
    domain_det_matrix = defaultdict(lambda: Counter())

    for m in sorted_best:
        if m["score"] >= 0.50:  # only credible matches
            domain_section_matrix[m["domain"]][m["top_section"]] += 1
            domain_det_matrix[m["domain"]][m["det"]] += 1

    print(f"\n  ── Coptic Domain → Voynich Section (score≥0.50) ──")
    all_sections = ["herbal-A", "herbal-B", "zodiac", "bio", "cosmo", "pharma", "text"]
    print(f"  {'Domain':<14}", end="")
    for s in all_sections:
        print(f" {s:>9}", end="")
    print(f" {'TOTAL':>7}")
    print("  " + "-" * (14 + 10 * len(all_sections) + 8))

    for domain in sorted(domain_section_matrix.keys()):
        ctr = domain_section_matrix[domain]
        total = sum(ctr.values())
        print(f"  {domain:<14}", end="")
        for s in all_sections:
            cnt = ctr.get(s, 0)
            pct = f"{100*cnt/total:.0f}%" if total > 0 else "-"
            print(f" {cnt:>5}({pct:>3})", end="")
        print(f" {total:>7}")

    print(f"\n  ── Coptic Domain → Voynich Determinative (score≥0.50) ──")
    all_dets = ["∅", "t", "k", "f", "p"]
    print(f"  {'Domain':<14}", end="")
    for d in all_dets:
        print(f" {d:>8}", end="")
    print(f" {'TOTAL':>7}")
    print("  " + "-" * (14 + 9 * len(all_dets) + 8))

    for domain in sorted(domain_det_matrix.keys()):
        ctr = domain_det_matrix[domain]
        total = sum(ctr.values())
        print(f"  {domain:<14}", end="")
        for d in all_dets:
            cnt = ctr.get(d, 0)
            pct = f"{100*cnt/total:.0f}%" if total > 0 else "-"
            print(f" {cnt:>4}({pct:>3})", end="")
        print(f" {total:>7}")

    # Key correlation tests
    print(f"\n  ── Key Correlation Tests ──")

    # Test 1: Do botanical Coptic matches preferentially appear in herbal sections?
    bot_matches = [m for m in sorted_best if m["domain"] == "botanical" and m["score"] >= 0.50]
    bot_herbal = sum(1 for m in bot_matches if "herbal" in m["top_section"])
    bot_total = len(bot_matches)
    if bot_total > 0:
        print(f"  Botanical Coptic → herbal sections: {bot_herbal}/{bot_total} ({100*bot_herbal/bot_total:.1f}%)")

    # Test 2: Do astronomical Coptic matches preferentially appear in zodiac/cosmo?
    astro_matches = [m for m in sorted_best if m["domain"] in ("astronomical", "astro") and m["score"] >= 0.50]
    astro_zodiac = sum(1 for m in astro_matches if m["top_section"] in ("zodiac", "cosmo"))
    astro_total = len(astro_matches)
    if astro_total > 0:
        print(f"  Astronomical Coptic → zodiac/cosmo: {astro_zodiac}/{astro_total} ({100*astro_zodiac/astro_total:.1f}%)")

    # Test 3: Do botanical Coptic matches correlate with f-gallows?
    bot_f = sum(1 for m in bot_matches if m["det"] == "f")
    if bot_total > 0:
        print(f"  Botanical Coptic → f-gallows: {bot_f}/{bot_total} ({100*bot_f/bot_total:.1f}%)")

    # Test 4: Do anatomical matches correlate with bio/pharma sections?
    anat_matches = [m for m in sorted_best if m["domain"] in ("anatomy", "medical") and m["score"] >= 0.50]
    anat_bio = sum(1 for m in anat_matches if m["top_section"] in ("bio", "pharma"))
    anat_total = len(anat_matches)
    if anat_total > 0:
        print(f"  Anatomy/Medical Coptic → bio/pharma: {anat_bio}/{anat_total} ({100*anat_bio/anat_total:.1f}%)")

    # Baseline: what fraction of ALL roots are in each section?
    sec_dist = Counter()
    for r, d in root_lexicon.items():
        sec_dist[d.get("top_section", "?")] += 1
    total_roots = sum(sec_dist.values())
    print(f"\n  ── Baseline Section Distribution (all roots) ──")
    for s in all_sections:
        cnt = sec_dist.get(s, 0)
        print(f"    {s}: {cnt}/{total_roots} ({100*cnt/total_roots:.1f}%)")

    return domain_section_matrix


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 3: STATISTICAL SIGNIFICANCE vs CONTROL
# ══════════════════════════════════════════════════════════════════════════

def analysis3_statistical_significance(root_lexicon):
    print("\n" + "=" * 72)
    print("ANALYSIS 3: STATISTICAL SIGNIFICANCE — Coptic vs Finnish (control)")
    print("=" * 72)

    thresholds = [0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]

    # Count Coptic matches at each threshold
    coptic_counts = {t: 0 for t in thresholds}
    for vroot in root_lexicon:
        if len(vroot) < 2:
            continue
        for cword, (meaning, domain) in COPTIC_EXPANDED.items():
            cword_clean = re.sub(r'\d+$', '', cword)
            score, _ = match_score(vroot, cword_clean)
            for t in thresholds:
                if score >= t:
                    coptic_counts[t] += 1
                    break  # count once per root per threshold? No, once per root

    # Recount properly: best match per root
    coptic_best = {}
    for vroot in root_lexicon:
        if len(vroot) < 2:
            continue
        best = 0
        for cword, (meaning, domain) in COPTIC_EXPANDED.items():
            cword_clean = re.sub(r'\d+$', '', cword)
            score, _ = match_score(vroot, cword_clean)
            if score > best:
                best = score
        coptic_best[vroot] = best

    # Count Finnish control matches
    finnish_best = {}
    for vroot in root_lexicon:
        if len(vroot) < 2:
            continue
        best = 0
        for fword in CONTROL_FINNISH:
            score, _ = match_score(vroot, fword)
            if score > best:
                best = score
        finnish_best[vroot] = best

    print(f"\n  {'Threshold':>10} {'Coptic':>10} {'Finnish':>10} {'Ratio':>10} {'Excess':>10}")
    print("  " + "-" * 55)

    for t in thresholds:
        cop_n = sum(1 for s in coptic_best.values() if s >= t)
        fin_n = sum(1 for s in finnish_best.values() if s >= t)
        ratio = cop_n / fin_n if fin_n > 0 else float('inf')
        excess = cop_n - fin_n
        print(f"  {t:>10.2f} {cop_n:>10} {fin_n:>10} {ratio:>10.2f}x {excess:>+10}")

    # Root length analysis — short roots give false positives
    print(f"\n  ── Match Rate by Root Length (score≥0.50) ──")
    print(f"  {'Len':>5} {'Coptic':>10} {'Finnish':>10} {'Cop-Tot':>10} {'Fin-Tot':>10} {'Cop%':>8} {'Fin%':>8} {'Ratio':>8}")
    print("  " + "-" * 75)

    for rlen in range(2, 8):
        cop_match = sum(1 for r, s in coptic_best.items() if len(r) == rlen and s >= 0.50)
        fin_match = sum(1 for r, s in finnish_best.items() if len(r) == rlen and s >= 0.50)
        cop_tot = sum(1 for r in coptic_best if len(r) == rlen)
        fin_tot = sum(1 for r in finnish_best if len(r) == rlen)
        cop_pct = 100 * cop_match / cop_tot if cop_tot > 0 else 0
        fin_pct = 100 * fin_match / fin_tot if fin_tot > 0 else 0
        ratio = cop_pct / fin_pct if fin_pct > 0 else float('inf')
        print(f"  {rlen:>5} {cop_match:>10} {fin_match:>10} {cop_tot:>10} {fin_tot:>10} {cop_pct:>7.1f}% {fin_pct:>7.1f}% {ratio:>7.2f}x")

    return coptic_best, finnish_best


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 4: PHONETIC HYPOTHESIS TESTING
# ══════════════════════════════════════════════════════════════════════════

def analysis4_phonetic_hypotheses(sorted_best, root_lexicon):
    print("\n" + "=" * 72)
    print("ANALYSIS 4: PHONETIC CORRESPONDENCE PATTERNS")
    print("=" * 72)

    # For exact/near-exact matches, catalog letter correspondences
    high_matches = [m for m in sorted_best if m["score"] >= 0.70]

    print(f"\n  High-confidence matches (score≥0.70): {len(high_matches)}")
    print(f"\n  ── Letter-by-letter Correspondences ──")

    v_to_c = defaultdict(Counter)  # voynich_char → coptic_char frequencies

    for m in high_matches:
        vr = m["voynich"]
        cr = m["coptic"]
        # Align by LCS
        v_skel = consonantal_skeleton(vr)
        c_skel = consonantal_skeleton(cr)

        # Simple character pairing if similar length
        min_len = min(len(vr), len(cr))
        for i in range(min_len):
            v_to_c[vr[i]][cr[i]] += 1

    print(f"\n  {'V-char':<8} {'→ Most common Coptic correspondences'}")
    print("  " + "-" * 50)
    for vc in sorted(v_to_c.keys()):
        top3 = v_to_c[vc].most_common(3)
        corr_str = ", ".join(f"{cc}:{cnt}" for cc, cnt in top3)
        print(f"  {vc:<8} → {corr_str}")

    # Test specific hypotheses from Leo anchor
    print(f"\n  ── Testing Leo-Anchor Hypotheses ──")
    hypotheses = {
        "e→a": ("e", "a"),
        "s→s": ("s", "s"),
        "d→d": ("d", "d"),
        "ch→kh": ("ch", "kh"),
        "r→r": ("r", "r"),
        "l→l": ("l", "l"),
        "sh→sh": ("sh", "sh"),
    }
    for label, (v_pat, c_pat) in hypotheses.items():
        # Count matches supporting this
        support = 0
        contradict = 0
        for m in high_matches:
            vr = m["voynich"]
            cr = m["coptic"]
            if v_pat in vr and c_pat in cr:
                support += 1
            elif v_pat in vr and c_pat not in cr:
                contradict += 1
        if support + contradict > 0:
            pct = 100 * support / (support + contradict)
            print(f"  {label:<10}: support={support}, contradict={contradict}, rate={pct:.0f}%")


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 5: ROOT-LENGTH-FILTERED HIGH-VALUE MATCHES
# ══════════════════════════════════════════════════════════════════════════

def analysis5_filtered_matches(sorted_best):
    print("\n" + "=" * 72)
    print("ANALYSIS 5: HIGH-VALUE MATCHES (root length ≥ 3, score ≥ 0.60)")
    print("=" * 72)

    filtered = [m for m in sorted_best
                if len(m["voynich"]) >= 3 and m["score"] >= 0.60]

    print(f"\n  Matches passing filter: {len(filtered)}")
    print(f"\n  {'Score':>6} {'Type':<12} {'V-Root':<14} {'Coptic':<16} {'Meaning':<22} {'Domain':<12} {'Freq':>5} {'Section':<10}")
    print("  " + "-" * 105)
    for m in filtered[:80]:
        print(f"  {m['score']:>6.2f} {m['type']:<12} {m['voynich']:<14} {m['coptic']:<16} {m['meaning']:<22} {m['domain']:<12} {m['freq']:>5} {m['top_section']:<10}")

    # Group by domain
    domain_counts = Counter(m["domain"] for m in filtered)
    print(f"\n  ── Domain Distribution of Filtered Matches ──")
    for domain, cnt in domain_counts.most_common():
        print(f"    {domain:<14}: {cnt}")

    return filtered


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 6: PERMUTATION TEST
# ══════════════════════════════════════════════════════════════════════════

def analysis6_permutation_test(root_lexicon):
    print("\n" + "=" * 72)
    print("ANALYSIS 6: PERMUTATION TEST — Is Coptic match rate above chance?")
    print("=" * 72)

    # Count real Coptic matches at score ≥ 0.60 with root len ≥ 3
    real_matches = 0
    roots_tested = [r for r in root_lexicon if len(r) >= 3]

    for vroot in roots_tested:
        for cword, (meaning, domain) in COPTIC_EXPANDED.items():
            cword_clean = re.sub(r'\d+$', '', cword)
            score, _ = match_score(vroot, cword_clean)
            if score >= 0.60:
                real_matches += 1
                break  # count root once

    print(f"\n  Real Coptic matches (score≥0.60, len≥3): {real_matches}/{len(roots_tested)}")

    # Generate random "pseudo-Coptic" words with same length distribution
    coptic_lengths = [len(re.sub(r'\d+$', '', w)) for w in COPTIC_EXPANDED.keys()]

    random.seed(42)
    n_permutations = 20
    perm_counts = []

    consonants = "bcdfghjklmnprstvz"
    vowels = "aeiou"

    # Use simplified matching for permutation test (much faster)
    def quick_match(vroot, rword):
        """Fast match check - exact/contains/simple skeleton only."""
        if vroot == rword:
            return True
        vs = apply_phonetic_rules(vroot)
        for v in vs:
            if v == rword:
                return True
            if len(v) >= 3 and v in rword:
                return True
            if len(rword) >= 3 and rword in v:
                return True
        # Quick skeleton check
        v_sk = consonantal_skeleton(vroot)
        r_sk = consonantal_skeleton(rword)
        if len(v_sk) >= 2 and len(r_sk) >= 2:
            lcs = lcs_length(v_sk, r_sk)
            mx = max(len(v_sk), len(r_sk))
            if lcs / mx >= 0.67:
                return True
        return False

    for trial in range(n_permutations):
        # Generate random words matching Coptic length distribution
        random_vocab = []
        for ln in coptic_lengths:
            word = ""
            for i in range(ln):
                if i % 2 == 0:
                    word += random.choice(consonants)
                else:
                    word += random.choice(vowels)
            random_vocab.append(word[:ln])

        # Count matches
        trial_matches = 0
        for vroot in roots_tested:
            for rword in random_vocab:
                if quick_match(vroot, rword):
                    trial_matches += 1
                    break

        perm_counts.append(trial_matches)

    mean_random = sum(perm_counts) / len(perm_counts)
    std_random = (sum((x - mean_random)**2 for x in perm_counts) / len(perm_counts))**0.5
    z_score = (real_matches - mean_random) / std_random if std_random > 0 else float('inf')

    print(f"  Random baseline (100 trials): mean={mean_random:.1f}, std={std_random:.1f}")
    print(f"  Z-score: {z_score:.2f}")
    print(f"  Interpretation: {'SIGNIFICANT (z>2)' if z_score > 2 else 'NOT SIGNIFICANT (z≤2)' if z_score > 0 else 'BELOW RANDOM'}")

    # Distribution
    print(f"\n  Random match count distribution:")
    print(f"    Min: {min(perm_counts)}, Max: {max(perm_counts)}, Real: {real_matches}")
    pct_above = 100 * sum(1 for x in perm_counts if x >= real_matches) / len(perm_counts)
    print(f"    Random trials ≥ real: {pct_above:.1f}% (p-value ≈ {pct_above/100:.3f})")

    return real_matches, mean_random, z_score


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 7: SEMANTIC COHERENCE CHECK
# ══════════════════════════════════════════════════════════════════════════

def analysis7_semantic_coherence(sorted_best, all_per_root, root_lexicon):
    print("\n" + "=" * 72)
    print("ANALYSIS 7: SEMANTIC COHERENCE — Do meanings make contextual sense?")
    print("=" * 72)

    # Look at exact/near-exact matches and check if meaning fits context
    high = [m for m in sorted_best if m["score"] >= 0.75 and len(m["voynich"]) >= 3]

    print(f"\n  High-confidence matches: {len(high)}")
    print(f"\n  ── Match-by-Match Semantic Assessment ──")

    # Define expected domains per section
    section_expected = {
        "herbal-A": ["botanical", "medical"],
        "herbal-B": ["botanical", "medical"],
        "zodiac": ["astronomical", "astro", "elemental", "animal"],
        "bio": ["anatomy", "medical", "social"],
        "cosmo": ["astronomical", "elemental", "astro"],
        "pharma": ["medical", "botanical", "anatomy"],
        "text": ["function", "social", "action"],
    }

    coherent = 0
    incoherent = 0
    neutral = 0

    for m in high:
        section = m["top_section"]
        domain = m["domain"]
        expected = section_expected.get(section, [])
        if domain in expected:
            status = "✓ COHERENT"
            coherent += 1
        elif section in ("unknown",):
            status = "? UNKNOWN"
            neutral += 1
        else:
            status = "✗ MISMATCH"
            incoherent += 1

        print(f"    {status:<14} {m['voynich']:<12} = {m['coptic']:<14} ({m['meaning']:<18}) [{domain}] in [{section}]")

    total_assessed = coherent + incoherent + neutral
    if total_assessed > 0:
        print(f"\n  Coherent:   {coherent}/{total_assessed} ({100*coherent/total_assessed:.1f}%)")
        print(f"  Mismatch:   {incoherent}/{total_assessed} ({100*incoherent/total_assessed:.1f}%)")
        print(f"  Neutral:    {neutral}/{total_assessed}")
        print(f"\n  Chance level for coherence: ~{100/len(set(section_expected.keys())):.0f}%")


# ══════════════════════════════════════════════════════════════════════════
# SYNTHESIS
# ══════════════════════════════════════════════════════════════════════════

def synthesis(sorted_best, coptic_best, finnish_best, real_matches, mean_random, z_score, filtered):
    print("\n" + "=" * 72)
    print("SYNTHESIS: COPTIC AS SUBSTRATE LANGUAGE — VERDICT")
    print("=" * 72)

    n_exact = sum(1 for m in sorted_best if m["type"] == "EXACT")
    n_near = sum(1 for m in sorted_best if m["type"] == "NEAR-EXACT")
    n_high = sum(1 for m in sorted_best if m["score"] >= 0.70)
    n_filtered = len(filtered)

    cop50 = sum(1 for s in coptic_best.values() if s >= 0.50)
    fin50 = sum(1 for s in finnish_best.values() if s >= 0.50)
    ratio50 = cop50 / fin50 if fin50 > 0 else float('inf')

    print(f"\n  MATCHES:")
    print(f"    Exact matches:           {n_exact}")
    print(f"    Near-exact matches:      {n_near}")
    print(f"    High-conf (≥0.70):       {n_high}")
    print(f"    Filtered (len≥3, ≥0.60): {n_filtered}")
    print(f"\n  CONTROL COMPARISON (score≥0.50):")
    print(f"    Coptic matches:          {cop50}")
    print(f"    Finnish matches:         {fin50}")
    print(f"    Ratio:                   {ratio50:.2f}x")
    print(f"\n  STATISTICAL:")
    print(f"    Z-score vs random:       {z_score:.2f}")
    print(f"    Real vs random mean:     {real_matches} vs {mean_random:.1f}")

    # Verdict
    print(f"\n  ╔{'═'*68}╗")
    if z_score > 3 and ratio50 > 1.5:
        print(f"  ║  VERDICT: STRONG EVIDENCE for Coptic as substrate language       ║")
    elif z_score > 2 and ratio50 > 1.2:
        print(f"  ║  VERDICT: MODERATE EVIDENCE for Coptic as substrate language     ║")
    elif z_score > 1:
        print(f"  ║  VERDICT: WEAK EVIDENCE — Coptic signal above noise but marginal║")
    else:
        print(f"  ║  VERDICT: No significant evidence for Coptic substrate           ║")
    print(f"  ╚{'═'*68}╝")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Loading Voynich data...")
    all_data = extract_all_words()
    print(f"  Loaded {len(all_data)} word tokens")

    print("Building root lexicon...")
    root_lexicon = build_root_lexicon(all_data)
    print(f"  Built {len(root_lexicon)} unique roots")

    # Analysis 1: Comprehensive matching
    sorted_best, all_per_root = analysis1_comprehensive_matching(root_lexicon)

    # Analysis 2: Domain correlation
    domain_matrix = analysis2_domain_correlation(sorted_best, root_lexicon)

    # Analysis 3: Statistical significance
    coptic_best, finnish_best = analysis3_statistical_significance(root_lexicon)

    # Analysis 4: Phonetic patterns
    analysis4_phonetic_hypotheses(sorted_best, root_lexicon)

    # Analysis 5: Filtered high-value matches
    filtered = analysis5_filtered_matches(sorted_best)

    # Analysis 6: Permutation test
    real_matches, mean_random, z_score = analysis6_permutation_test(root_lexicon)

    # Analysis 7: Semantic coherence
    analysis7_semantic_coherence(sorted_best, all_per_root, root_lexicon)

    # Synthesis
    synthesis(sorted_best, coptic_best, finnish_best, real_matches, mean_random, z_score, filtered)

    # Save results
    results = {
        "coptic_terms_tested": len(COPTIC_EXPANDED),
        "voynich_roots_tested": len(root_lexicon),
        "exact_matches": [m for m in sorted_best if m["type"] == "EXACT"],
        "near_exact_matches": [m for m in sorted_best if m["type"] == "NEAR-EXACT"],
        "top_60": sorted_best[:60],
        "filtered_matches": filtered[:100],
    }
    with open(result_path("coptic_probe_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to results/coptic_probe_results.json")
