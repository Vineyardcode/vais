#!/usr/bin/env python3
"""Verify + complete scripts/common/core.py dependency closure.

For every exported function:
  1. Find external names it references.
  2. If the name resolves inside core.py (function/constant/import) -> OK,
     but additionally require that every file carrying this variant defines
     that dependency identically to core's version (hash/literal match).
  3. If unresolved: if all carrier files define it with one identical
     literal, append it to core.py; otherwise mark the export UNSAFE and
     remove it (scripts keep their local defs).

Prints a report; rewrites core.py in place.
"""
import ast
import builtins
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
CORE = SCRIPTS / "common" / "core.py"

sys.path.insert(0, str(ROOT / "tools"))
from build_common import AlphaRenamer, strip_docstring, alpha_hash, external_names  # noqa: E402

manifest = json.loads((ROOT / "tools" / "common_manifest.json").read_text())

core_src = CORE.read_text(encoding="utf-8")
core_tree = ast.parse(core_src)
core_funcs = {n.name: n for n in core_tree.body if isinstance(n, ast.FunctionDef)}
core_consts = {}
for n in core_tree.body:
    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
        core_consts[n.targets[0].id] = n
core_imports = {"io", "math", "re", "sys", "Counter", "defaultdict", "Path", "np",
                "PROJECT_ROOT", "FOLIO_DIR", "DATA_DIR", "RESULTS_DIR", "urllib", "json",
                "random", "itertools"}

# Index every script's top-level defs/constants
script_funcs = defaultdict(dict)   # file -> name -> node
script_consts = defaultdict(dict)  # file -> name -> (repr, src)
script_srcs = {}
for p in sorted(SCRIPTS.glob("*.py")):
    src = p.read_text(encoding="utf-8", errors="replace")
    script_srcs[p.name] = src
    try:
        tree = ast.parse(src)
    except SyntaxError:
        continue
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            script_funcs[p.name][node.name] = node
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                val = repr(ast.literal_eval(node.value))
                script_consts[p.name][node.targets[0].id] = (val, ast.get_source_segment(src, node))
            except Exception:
                pass

# Map: which files carry each (name, hash) variant
variant_files = defaultdict(list)
for fname, funcs in script_funcs.items():
    for name, node in funcs.items():
        variant_files[(name, alpha_hash(node))].append(fname)

unsafe = []
additions = {}  # const_name -> src (appended once)
renames_needed = []

for entry in manifest["functions"]:
    export, name, h = entry["export"], entry["name"], entry["hash"]
    if export not in core_funcs:
        continue
    fn = core_funcs[export]
    deps = external_names(fn)
    carriers = variant_files.get((name, h), [])
    ok = True
    for d in sorted(deps):
        if hasattr(builtins, d) or d in core_imports:
            continue
        if d in core_funcs or d in core_consts or d in additions:
            # dependency exists in core under bare name: verify each carrier's
            # local version matches core's
            for cf in carriers:
                if d in script_funcs[cf]:
                    core_target = core_funcs.get(d)
                    if core_target is None or alpha_hash(script_funcs[cf][d]) != alpha_hash(core_target):
                        ok = False
                        print(f"UNSAFE {export}: dep fn {d} differs in {cf}")
                        break
                elif d in script_consts[cf]:
                    cd = core_consts.get(d)
                    add = additions.get(d)
                    core_val = None
                    if cd is not None:
                        try:
                            core_val = repr(ast.literal_eval(cd.value))
                        except Exception:
                            pass
                    elif add is not None:
                        core_val = add[0]
                    if core_val != script_consts[cf][d][0]:
                        ok = False
                        print(f"UNSAFE {export}: dep const {d} differs in {cf}")
                        break
            if not ok:
                break
            continue
        # unresolved: try to lift a constant identical across carriers
        vals = set()
        src_seg = None
        for cf in carriers:
            if d in script_consts[cf]:
                vals.add(script_consts[cf][d][0])
                src_seg = script_consts[cf][d][1]
            elif d in script_funcs[cf]:
                vals.add("FN:" + alpha_hash(script_funcs[cf][d]))
            else:
                vals.add("<missing>")
        if len(vals) == 1 and src_seg is not None:
            additions[d] = (next(iter(vals)), src_seg)
            print(f"LIFT   {export}: adding const {d} (identical in {len(carriers)} carriers)")
        elif len(vals) == 1 and next(iter(vals)).startswith("FN:"):
            # dependency is a function identical across carriers but not exported
            # under bare name -> unsafe for now
            ok = False
            print(f"UNSAFE {export}: dep fn {d} not exported (identical across carriers)")
        else:
            ok = False
            print(f"UNSAFE {export}: dep {d} varies across carriers: {len(vals)} values")
    if not ok:
        unsafe.append(export)

# Rewrite core.py: drop unsafe exports, append lifted constants before functions
lines = core_src.splitlines()
out = []
skip_until_next = False
current_fn = None
new_src_parts = []
tree = ast.parse(core_src)
kept = []
for node in tree.body:
    seg = ast.get_source_segment(core_src, node)
    if isinstance(node, ast.FunctionDef) and node.name in unsafe:
        continue
    kept.append(seg)

# insert lifted constants after the constants banner
const_block = "\n".join(f"# lifted dependency constant\n{src}" for _, (val, src) in sorted(additions.items(), key=lambda kv: kv[0]) for src in [kv_src] if (kv_src := src) ) if False else ""
lift_lines = []
for cname, (val, src) in sorted(additions.items()):
    lift_lines.append("# lifted dependency constant (identical across all carrier scripts)")
    lift_lines.append(src)
    lift_lines.append("")

final = []
inserted = False
for seg in kept:
    final.append(seg)
    if not inserted and seg.startswith("# ── shared constants"):
        final.extend(lift_lines)
        inserted = True
if not inserted and lift_lines:
    final = lift_lines + final

CORE.write_text("\n\n".join(final) + "\n", encoding="utf-8")

# update manifest
manifest["functions"] = [e for e in manifest["functions"] if e["export"] not in unsafe]
manifest["lifted_constants"] = sorted(additions.keys())
(ROOT / "tools" / "common_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")

print(f"\nDropped {len(unsafe)} unsafe exports: {unsafe}")
print(f"Lifted {len(additions)} constants: {sorted(additions)}")
print(f"Remaining exports: {len(manifest['functions'])}")
