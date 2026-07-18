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
    "cross_script_fingerprint", "forward_process_models", "positional_verbose_cipher",
    "word_shape_validation", "word_functional_anatomy",
    "encoding_model_tournament", "script_reverse_engineering",
    "naibbe_cipher_calibration", "abbreviation_shorthand_model",
    "latin_paragraph_initials", "vernacular_paragraph_initials",
}

# Dependency edges: consumer -> [producer scripts]. Audit-verified against
# actual result-file reads in the code (AUDIT.md A2): hebrew_deep_analysis
# does NOT read morphology_full_survey output (comment only); f66r_analysis and
# chunk_equivalence_revalidation were missing.
DEPENDS = {
    "astro_crossref": ["astro_label_pipeline"],
    "zodiac_label_network": ["ring_decan_mapping"],
    "zodiac_degree_semantics": ["ring_decan_mapping"],
    "claims_correction_audit": ["ring_decan_mapping"],
    "inner_ring_inventory": ["ring_grammar_extraction", "ring_text_analysis"],
    "herbal_crossref": ["ring_grammar_extraction"],
    "hebrew_comparison": ["morphology_full_survey"],
    "f66r_analysis": ["morphology_full_survey", "freq_rank_mapping"],
    "forward_process_models": ["cross_script_fingerprint"],
    "positional_verbose_cipher": ["cross_script_fingerprint"],
    "chunk_equivalence_revalidation": ["chunk_equivalence_classes"],
    "chunk_alphabet_decipherment": ["chunk_equivalence_classes"],
    "transliteration_floor_calibration": ["cross_transliteration_invariance"],
    "transliteration_significance": ["cross_transliteration_invariance"],
    "line_as_record_characterization": ["line_as_record_ordinal"],
    "line_as_record_section_split": ["line_as_record_ordinal"],
    "currier_dichotomy_resolution": ["chunk_equivalence_classes"],
    "historical_validation": ["chunk_equivalence_classes"],
    "generative_chunk_model": ["chunk_equivalence_classes"],
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
