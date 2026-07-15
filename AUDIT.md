# AUDIT.md — VAIS full adversarial audit + rebrand log

Branch: `audit/full-review` (from `refactor/test-webui` @ f219bf7).
Conventions: every fix logged with file, what was wrong, what changed, and a
before/after where results shift; lower-confidence judgment calls tagged
`[REVIEW]`. Clean areas are recorded too — an audit that only lists problems
is unverifiable.

## Phase 0.5 — Rebrand sweep (voynich_slop → VAIS)

Case-insensitive sweep for `voynich_slop` / "voynich slop" over all tracked
source/doc/config files (excluding data corpora `folios/`, `data/voynichese/`,
and output dirs `baseline/`, `golden/`, `results/`, `attic/`, scratch dirs).
Hits and disposition:

| location | occurrences | disposition |
|---|---|---|
| `scripts/phase96_cluster_hchar.py` 448-450, 468, 531 | 5 hardcoded absolute paths | **AUDIT FINDING A1 — fixed in code (see below), not a rebrand edit** |
| `webui/static/index.html` (title, h1) | brand string "Voynich Analysis Suite" | rebrand → "VAIS — Voynich Analysis Interactive Suite" |
| `README_WEBUI.md` (header, root-path line) | brand + old path | rebrand; path updated to the post-Phase-5 location |
| `.claude/launch.json` | server name `voynich-webui` | rebrand → `vais-webui` |
| `webui/server.py` docstring | "Voynich analysis suite" | rebrand |
| `tools/gen_inventory.py` → `INVENTORY.md` header | generated doc | generator updated + doc regenerated |
| `CHANGES.md` 51, 120 | historical quotes of the old hardcoded paths | **kept verbatim** — they quote past defects; rewriting them would falsify the accountability record. Header note added. |
| `tools/inventory_notes.md` | historical Phase-1 reading notes | kept verbatim (same reason) |
| `tools/inventory_raw.json` | generated static-scan artifact | regenerated after A1 fix (strings disappear with the code fix) |
| remote `origin` | github.com/Vineyardcode/voynich_slop | `gh repo rename` attempted — outcome logged below |

## Findings

### A1 — CRITICAL(portability) / previous-pass error: phase96 hardcoded paths survived
- **File**: `scripts/phase96_cluster_hchar.py` lines 448-450, 468, 531.
- **Wrong**: the previous pass replaced the module-level `FOLIO_DIR`
  constant and CHANGES.md claims phase96's "hardcoded absolute paths [were]
  replaced with `__file__`-relative equivalents" — but five more absolute
  paths (`latin_dir`, `vern_dir`, `czech_dir`, and a temp-file path used
  twice) sit mid-file in lowercase locals, which both the constant-grep and
  the module-level static scan missed. The folder rename (Phase 5) would
  have broken this script; CHANGES.md's claim was false as stated.
- **Fix**: all five derive from a `_PROJECT_DIR = dirname(dirname(__file__))`
  base, same idiom as the previous partial fix.
- **Shift**: none on this machine (paths resolve identically);
  verified byte-identical vs `golden/`.
