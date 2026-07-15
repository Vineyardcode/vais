"""Test registry for the Voynich analysis web UI.

Builds the catalog of runnable analysis scripts by static inspection:
  - description: first meaningful docstring line
  - params: module-level UPPERCASE literal constants (the code's real
    defaults), type-tagged for form rendering/validation
  - dependencies: which other scripts' result files a script consumes
  - runtime/status: from baseline/_meta.json when available

Nothing here executes analysis code.
"""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
BASELINE_META = ROOT / "baseline" / "_meta.json"

# Pure downloaders — excluded from the runnable registry.
EXCLUDE = {"download_folios.py", "download_latin.py"}

# Scripts that hit the network for reference corpora (flagged in UI).
NETWORK = {
    "phase58_cross_script", "phase59_forward_model", "phase60_positional_verbose",
    "phase61_word_shape_validation", "phase62_word_anatomy",
    "phase64_encoding_tournament", "phase65_reverse_engineer_script",
    "phase72_naibbe_calibration", "phase73_abbreviation_model",
    "phase75_latin_mapping", "phase76_vernacular_mapping",
}

# Dependency edges: consumer -> [producer scripts] (from Phase 1 inventory).
DEPENDS = {
    "astro_crossref": ["astro_label_pipeline"],
    "crosssign_network": ["ring_decan_mapping"],
    "medieval_degrees": ["ring_decan_mapping"],
    "four_tasks_audit": ["ring_decan_mapping"],
    "innermost_ring_dive": ["grammar_extraction", "ring_text_analysis"],
    "herbal_crossref": ["grammar_extraction"],
    "hebrew_comparison": ["attack_plan"],
    "hebrew_deep_analysis": ["attack_plan"],
    "phase59_forward_model": ["phase58_cross_script"],
    "phase60_positional_verbose": ["phase58_cross_script"],
    "phase100_decipherment": ["phase86_chunk_equivalence"],
    "phase101_currier_ab_dichotomy": ["phase86_chunk_equivalence"],
    "phase102_historical_validation": ["phase86_chunk_equivalence"],
    "phase98_generative_chunk_model": ["phase86_chunk_equivalence"],
}

# Param names that are infrastructure, not analysis knobs.
PARAM_EXCLUDE = re.compile(
    r"^(FOLIO_DIR|DATA_DIR|RESULTS_DIR|PROJECT_DIR|SCRIPT_DIR|LATIN_DIR|OUTPUT"
    r"|.*_PATH|.*_FILE|.*_DIR)$")

MAX_LIST_REPR = 800


def _param_type(v):
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    return "json"  # list/tuple/dict/set edited as JSON-ish literal


def extract_params(tree):
    params = {}
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        name = node.targets[0].id
        if not name.isupper() or PARAM_EXCLUDE.match(name):
            continue
        try:
            val = ast.literal_eval(node.value)
        except Exception:
            continue
        if isinstance(val, (set, tuple)):
            # keep editable but note original container type
            container = type(val).__name__
        else:
            container = None
        if len(repr(val)) > MAX_LIST_REPR:
            continue
        try:
            default = (sorted(val) if isinstance(val, set)
                       else list(val) if isinstance(val, tuple) else val)
            json.dumps(default)
        except TypeError:
            continue  # not JSON-representable (e.g. tuple-keyed dict)
        params[name] = {
            "default": default,
            "type": _param_type(val),
            "container": container,
            "line": node.lineno,
        }
    return params


def build_registry():
    meta = {}
    if BASELINE_META.exists():
        try:
            meta = json.loads(BASELINE_META.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            meta = {}
    tests = {}
    for p in sorted(SCRIPTS.glob("*.py")):
        if p.name in EXCLUDE or p.name.startswith((".", "_")):
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        doc = ast.get_docstring(tree) or ""
        desc_lines = [ln.strip() for ln in doc.splitlines()
                      if ln.strip() and not set(ln.strip()) <= set("=─━═-")]
        stem = p.stem
        m = meta.get(stem, {})
        tests[stem] = {
            "name": stem,
            "file": f"scripts/{p.name}",
            "description": desc_lines[0] if desc_lines else stem,
            "doc": "\n".join(desc_lines[:14]),
            "lines": src.count("\n") + 1,
            "params": extract_params(tree),
            "depends": DEPENDS.get(stem, []),
            "network": stem in NETWORK,
            "baseline_status": m.get("status"),
            "baseline_seconds": m.get("duration_s"),
            "results_files": m.get("results_files_touched", []),
        }
    return tests


if __name__ == "__main__":
    r = build_registry()
    n_params = sum(len(t["params"]) for t in r.values())
    print(f"{len(r)} tests, {n_params} total parameters")
    for name, t in list(r.items())[:8]:
        print(f"  {name}: {len(t['params'])} params — {t['description'][:70]}")
