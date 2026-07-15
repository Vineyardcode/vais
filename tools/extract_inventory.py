#!/usr/bin/env python3
"""Inventory extractor: static analysis of every script in scripts/.

Produces tools/inventory_raw.json with, per script:
  - docstring (module-level)
  - module-level constant assignments (candidate parameters)
  - function definitions
  - data files / directories referenced
  - results files written / read
  - imports (flags for scipy/sklearn/urllib/numpy)
  - seed pinning, line count

This is scaffolding for the hand-written INVENTORY.md — it does not replace
reading the scripts.
"""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

LITERAL_TYPES = (ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set)


def literal_repr(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def analyze(path: Path):
    src = path.read_text(encoding="utf-8", errors="replace")
    info = {
        "file": path.name,
        "lines": src.count("\n") + 1,
        "docstring": None,
        "constants": {},
        "functions": [],
        "imports": [],
        "reads": sorted(set(re.findall(r"['\"]([\w./\\*-]+\.(?:txt|xml|json|csv))['\"]", src))),
        "writes_results": bool(re.search(r"results[/\\]", src)),
        "seeds": bool(re.search(r"\.seed\(", src)),
        "utf8_wrapper": "TextIOWrapper" in src,
        "syntax_error": None,
    }
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        info["syntax_error"] = str(e)
        return info

    info["docstring"] = ast.get_docstring(tree)

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                info["imports"].extend(a.name.split(".")[0] for a in node.names)
            else:
                if node.module:
                    info["imports"].append(node.module.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info["functions"].append(node.name)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and isinstance(node.value, LITERAL_TYPES):
                val = literal_repr(node.value)
                if val is not None or isinstance(node.value, ast.Constant):
                    # Store only reasonably-sized, JSON-safe literals
                    r = repr(val)
                    if len(r) <= 400:
                        try:
                            json.dumps({t.id: val})
                            info["constants"][t.id] = val
                        except TypeError:
                            info["constants"][t.id] = r
    info["imports"] = sorted(set(info["imports"]))
    return info


def main():
    out = []
    for p in sorted(SCRIPTS.glob("*.py")):
        out.append(analyze(p))
    dest = ROOT / "tools" / "inventory_raw.json"
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str),
                    encoding="utf-8")
    print(f"Wrote {dest} ({len(out)} scripts)")
    # Quick duplication report
    from collections import Counter
    fn_counter = Counter()
    for i in out:
        for f in i["functions"]:
            fn_counter[f] += 1
    print("\nMost-duplicated function names:")
    for name, n in fn_counter.most_common(25):
        if n > 1:
            print(f"  {n:3d}x {name}")


if __name__ == "__main__":
    main()
