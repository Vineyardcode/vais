#!/usr/bin/env python3
"""Rewrite scripts to import shared helpers from common/ instead of
defining local copies.

Safety model:
  - A local function is removed ONLY if its alpha-hash matches a manifest
    entry (i.e. it is byte-equivalent to the extracted canonical variant,
    modulo naming/formatting).
  - Per-script dependency guard: every global name the canonical body
    references must resolve identically in that script (function hash or
    constant literal equal to core's), else the function is left alone.
  - Imports are inserted after the last top-level import.
  - Each modified file must py_compile afterwards or the change is reverted.

Usage: python tools/rewrite_scripts.py [--apply]  (default: dry run)
"""
import ast
import builtins
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT / "tools"))
from build_common import alpha_hash, external_names  # noqa: E402

CORE = SCRIPTS / "common" / "core.py"
core_src = CORE.read_text(encoding="utf-8")
core_tree = ast.parse(core_src)
core_funcs = {n.name: n for n in core_tree.body if isinstance(n, ast.FunctionDef)}
core_func_hash = {name: alpha_hash(n) for name, n in core_funcs.items()}
core_consts = {}
for n in core_tree.body:
    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
        try:
            core_consts[n.targets[0].id] = repr(ast.literal_eval(n.value))
        except Exception:
            pass
CORE_IMPORTS = {"io", "math", "re", "sys", "np", "json", "urllib", "Counter",
                "defaultdict", "Path", "PROJECT_ROOT", "FOLIO_DIR", "DATA_DIR",
                "RESULTS_DIR"}

manifest = json.loads((ROOT / "tools" / "common_manifest.json").read_text())
# hash -> (export, orig_name)
hash_map = {}
for e in manifest["functions"]:
    hash_map[(e["name"], e["hash"])] = e["export"]

# Renamed dependencies inside manually-added core functions:
# core function name -> {name in canonical carrier script: name in core}
DEP_RENAME = {
    "parse_morphology": {"SUFFIXES": "MORPH_SUFFIXES"},
    "get_collapsed": {"strip_gallows": "strip_gallows_v2"},
}


def const_repr(node):
    try:
        return repr(ast.literal_eval(node.value))
    except Exception:
        return None


def process(path, apply=False):
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    local_funcs = {}
    local_consts = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            local_funcs[node.name] = node
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            r = const_repr(node)
            if r is not None:
                local_consts[node.targets[0].id] = r

    removals = []  # (node, export)
    for name, node in local_funcs.items():
        h = alpha_hash(node)
        export = hash_map.get((name, h))
        if not export or export not in core_funcs:
            continue
        # dependency guard: core body refs must resolve identically in script
        deps = external_names(core_funcs[export])
        rename = DEP_RENAME.get(export, {})
        inv_rename = {v: k for k, v in rename.items()}
        ok = True
        for d in deps:
            if hasattr(builtins, d) or d in CORE_IMPORTS:
                continue
            script_name = inv_rename.get(d, d)
            if d in core_funcs:
                if script_name in local_funcs:
                    if alpha_hash(local_funcs[script_name]) != core_func_hash[d]:
                        # local dep will ALSO be replaced only if it maps to same
                        # export; check hash_map
                        exp2 = hash_map.get((script_name, alpha_hash(local_funcs[script_name])))
                        if exp2 != d:
                            ok = False
                            break
                # if script doesn't define it, core's version is used: fine
            elif d in core_consts:
                if script_name in local_consts and local_consts[script_name] != core_consts[d]:
                    ok = False
                    break
            else:
                ok = False
                break
        if ok:
            removals.append((node, export, name))

    if not removals:
        return None

    lines = src.splitlines()
    drop = set()
    imports_needed = []
    for node, export, name in removals:
        start = node.lineno - 1
        # absorb immediately preceding comment block
        while start - 1 >= 0 and lines[start - 1].lstrip().startswith("#"):
            start -= 1
        for i in range(start, node.end_lineno):
            drop.add(i)
        imports_needed.append(f"{export} as {name}" if export != name else name)

    # insertion point: after last top-level import
    last_import = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import = max(last_import, node.end_lineno)
    imp_line = "from common import " + ", ".join(sorted(set(imports_needed)))

    new_lines = []
    for i, ln in enumerate(lines):
        if i == last_import:
            new_lines.append(imp_line)
        if i not in drop:
            new_lines.append(ln)
    if last_import >= len(lines):
        new_lines.append(imp_line)
    new_src = "\n".join(new_lines) + "\n"

    if apply:
        path.write_text(new_src, encoding="utf-8")
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            path.write_text(src, encoding="utf-8")
            return f"REVERTED {path.name}: {e}"
    return f"{path.name}: -{len(removals)} defs ({', '.join(sorted(set(n for _, _, n in removals)))})"


def main():
    apply = "--apply" in sys.argv
    n = 0
    for p in sorted(SCRIPTS.glob("*.py")):
        r = process(p, apply=apply)
        if r:
            print(r)
            n += 1
    print(f"\n{'Applied to' if apply else 'Would modify'} {n} scripts")


if __name__ == "__main__":
    main()
