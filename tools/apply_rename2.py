"""Rename pass 2: fixes the \\b-underscore gap of pass 1 and the leftovers.

1. phaseNN tokens attached to underscores (result filenames like
   'phase29_results.json') -> owning stem, own-file first.
2. Single-digit internal pipeline function names (def phase1_x) -> part1_x.
3. Prose references to the pre-phase-numbered scripts (Phase 12-17 era)
   and to ambiguous numbers, via a hand-checked map.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rename_map import RENAME, NUMBER_OWNERS

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'

# hand-checked: prose references to numbers with no/ambiguous owner
PROSE_MAP = {
    '12': 'diacritic_audit',
    '13': 'gallows_semantics',
    '14': 'egyptian_connection',
    '15': 'root_lexicon_rosetta',
    '16b': 'coptic_dictionary_probe',
    '16c': 'herbal_labels',
    '17': 'sentence_translation',
    '85': 'chunk_fingerprint',          # the chunk parser/fingerprint source
    '86': 'chunk_equivalence_classes',
    '87': 'spectral_vowel_consonant',
    '83': 'encoding_layer_sweep',
}

inverse = {v: k for k, v in RENAME.items()}
files = sorted(SCRIPTS.glob('*.py')) + sorted((SCRIPTS / 'common').glob('*.py')) \
    + sorted((ROOT / 'webui').glob('*.py')) + sorted((ROOT / 'sanity_checks').glob('*.py')) \
    + [ROOT / 'tools' / 'run_baseline.py', ROOT / 'tools' / 'rewrite_scripts.py']

changed = 0
for path in files:
    text = path.read_text(encoding='utf-8', errors='replace')
    orig = text

    own_old = inverse.get(path.stem)
    own_num = None
    m = re.match(r'phase(\d+[a-zA-Z]?)_', own_old or '')
    if m:
        own_num = m.group(1)

    # 2. internal pipeline functions first (single digit + underscore + name)
    text = re.sub(r'\bphase([0-9])_(?=[a-z])', r'part\1_', text)

    # 1. remaining phaseNN tokens (incl. underscore-attached), NN >= 2 digits
    #    or letter-suffixed
    def sub_token(mm):
        num = mm.group(1)
        owners = NUMBER_OWNERS.get(num, [])
        if own_num and num == own_num:
            return RENAME[own_old]
        if len(owners) == 1:
            return owners[0][1]
        if num in PROSE_MAP:
            return PROSE_MAP[num]
        return mm.group(0)

    text = re.sub(r'(?i)\bphase[\s_]?(\d{2,}[a-zA-Z]?|\d[a-zA-Z])(?=[_\W]|$)',
                  sub_token, text)

    if text != orig:
        path.write_text(text, encoding='utf-8')
        changed += 1

print(f'pass 2 rewrote {changed} files')

# residual report
count = 0
for path in files:
    for i, line in enumerate(
            path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if re.search(r'(?i)\bphase\s*_?\d', line):
            print(f'  {path.relative_to(ROOT)}:{i}: {line.strip()[:100]}')
            count += 1
print(f'residual: {count} lines')
