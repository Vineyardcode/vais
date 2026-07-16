"""Apply the test-rename refactor defined in tools/rename_map.py.

Order of operations (order matters — identifiers before prose):
  1. git mv scripts.
  2. In every live text file: replace full old stems, longest first.
  3. Per script: bare phaseNN tokens -> owner's new stem (own file wins;
     ambiguous cross-file refs are reported, not guessed).
  4. Prose cleanup: strip "PHASE NN —/:" prefixes, "(Phase NN)"
     parentheticals, "PHASE NN SYNTHESIS/COMPLETE" markers, redundant
     "Voynich Manuscript — " docstring prefixes.
  5. Rename results/ files by the same stem map.
  6. Report every remaining case-insensitive /phase\\s*\\d/ for manual review.

Historical records (baseline/, CHANGES.md, AUDIT.md, RESEARCH.md,
INVENTORY.md pre-regeneration, attic/) are deliberately untouched.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rename_map import RENAME, NUMBER_OWNERS

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'
RESULTS = ROOT / 'results'

LIVE_FILES = (
    sorted(SCRIPTS.glob('*.py'))
    + sorted((SCRIPTS / 'common').glob('*.py'))
    + sorted((ROOT / 'webui').glob('*.py'))
    + [ROOT / 'webui' / 'presets.json', ROOT / 'README_WEBUI.md']
    + sorted((ROOT / 'sanity_checks').glob('*.py'))
    + [ROOT / 'tools' / 'run_baseline.py', ROOT / 'tools' / 'rewrite_scripts.py']
)

STEMS_LONGEST_FIRST = sorted(RENAME, key=len, reverse=True)


def replace_stems(text):
    for old in STEMS_LONGEST_FIRST:
        text = text.replace(old, RENAME[old])
    return text


def replace_bare_numbers(text, own_stem_old):
    """phaseNN tokens left after full-stem replacement."""
    own_num = None
    m = re.match(r'phase(\d+[a-zA-Z]?)_', own_stem_old or '')
    if m:
        own_num = m.group(1)

    def sub(mm):
        num = mm.group(1)
        owners = NUMBER_OWNERS.get(num, [])
        if own_num and num == own_num:
            return RENAME[own_stem_old]
        if len(owners) == 1:
            return owners[0][1]
        return mm.group(0)  # ambiguous or unknown: leave, gets reported

    return re.sub(r'(?i)\bphase[\s_]?(\d+[a-zA-Z]?)\b', sub, text)


def prose_cleanup(text):
    # "PHASE 21a: TITLE" / "Phase 20.1 — Title" -> keep the title part
    text = re.sub(r'(?i)\bphase\s+\d+[a-zA-Z]?(?:\.\d+)?\s*[:—–-]\s*', '', text)
    # "(Phase 12)" parentheticals
    text = re.sub(r'\s*\(\s*(?i:phase)\s+\d+[a-zA-Z]?\s*\)', '', text)
    # "PHASE 39 SYNTHESIS" / "PHASE 46 COMPLETE"
    text = re.sub(r'(?i)\bphase\s+\d+[a-zA-Z]?\s+SYNTHESIS', 'SYNTHESIS', text)
    text = re.sub(r'(?i)\bphase\s+\d+[a-zA-Z]?\s+(?:DEEP DIVE\s+)?COMPLETE',
                  'ANALYSIS COMPLETE', text)
    # redundant corpus prefix on docstring titles
    text = re.sub(r'(?i)^(?:VOYNICH MANUSCRIPT|Voynich Manuscript)\s*—\s*',
                  '', text, count=1, flags=re.M)
    return text


def main():
    # 1. git mv
    for old, new in RENAME.items():
        src, dst = SCRIPTS / f'{old}.py', SCRIPTS / f'{new}.py'
        if src.exists():
            subprocess.run(['git', 'mv', str(src), str(dst)],
                           cwd=ROOT, check=True)
    print(f'moved {len(RENAME)} scripts')

    # 2-4. content passes
    inverse = {v: k for k, v in RENAME.items()}
    changed = 0
    for f in LIVE_FILES:
        # after the mv, mapped scripts live under their new names
        path = f
        if f.parent == SCRIPTS and f.stem in RENAME:
            path = SCRIPTS / f'{RENAME[f.stem]}.py'
        if not path.exists():
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        orig = text
        text = replace_stems(text)
        own_old = inverse.get(path.stem) if path.parent == SCRIPTS else None
        text = replace_bare_numbers(text, own_old)
        text = prose_cleanup(text)
        if text != orig:
            path.write_text(text, encoding='utf-8')
            changed += 1
    print(f'rewrote {changed} files')

    # 5. results/ file renames
    renamed = 0
    for p in sorted(RESULTS.iterdir()):
        if not p.is_file():
            continue
        newname = replace_stems(p.name)
        if newname != p.name:
            p.rename(RESULTS / newname)
            renamed += 1
    print(f'renamed {renamed} result files')

    # 6. residual report
    print('\nresidual phase references (manual review):')
    count = 0
    for f in LIVE_FILES:
        path = f
        if f.parent == SCRIPTS and f.stem in RENAME:
            path = SCRIPTS / f'{RENAME[f.stem]}.py'
        if not path.exists():
            continue
        for i, line in enumerate(
                path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if re.search(r'(?i)\bphase\s*_?\d', line):
                print(f'  {path.relative_to(ROOT)}:{i}: {line.strip()[:90]}')
                count += 1
    print(f'  ({count} lines)')


if __name__ == '__main__':
    main()
