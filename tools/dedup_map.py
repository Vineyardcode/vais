#!/usr/bin/env python3
"""Function-level duplication map.

For every top-level function in scripts/*.py, compute a hash of its
normalized AST dump (strips comments/whitespace/docstrings). Group by
function name; report which copies are identical and which diverge.

Output: tools/dedup_map.json + console summary.
"""
import ast
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def norm_hash(node):
    # Strip docstrings for stable comparison
    class Strip(ast.NodeTransformer):
        def visit_FunctionDef(self, n):
            self.generic_visit(n)
            if (n.body and isinstance(n.body[0], ast.Expr)
                    and isinstance(n.body[0].value, ast.Constant)
                    and isinstance(n.body[0].value.value, str)):
                n.body = n.body[1:] or [ast.Pass()]
            return n
    node = Strip().visit(node)
    dump = ast.dump(node, annotate_fields=False, include_attributes=False)
    return hashlib.sha1(dump.encode()).hexdigest()[:12]


def main():
    groups = defaultdict(lambda: defaultdict(list))  # name -> hash -> [files]
    consts = defaultdict(lambda: defaultdict(list))  # const name -> repr -> [files]
    for p in sorted(SCRIPTS.glob("*.py")):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                groups[node.name][norm_hash(node)].append(p.name)
            elif (isinstance(node, ast.Assign) and len(node.targets) == 1
                  and isinstance(node.targets[0], ast.Name)
                  and node.targets[0].id in (
                      "PREFIXES", "SUFFIXES", "ROOT_ONSETS", "ROOT_BODIES",
                      "ALL_GALLOWS", "SIMPLE_GALLOWS", "BENCH_GALLOWS",
                      "SUFFIXES_LIST", "SLOT_TOKENS")):
                try:
                    consts[node.targets[0].id][repr(ast.literal_eval(node.value))].append(p.name)
                except Exception:
                    pass

    out = {"functions": {}, "constants": {}}
    print("=== Duplicated functions (name: n_files, n_variants) ===")
    rows = []
    for name, variants in groups.items():
        total = sum(len(v) for v in variants.values())
        if total > 1:
            rows.append((total, len(variants), name))
            out["functions"][name] = {h: fs for h, fs in variants.items()}
    rows.sort(reverse=True)
    for total, nvar, name in rows[:40]:
        flag = " <-- DIVERGENT" if nvar > 1 else ""
        print(f"  {name:32s} files={total:3d} variants={nvar}{flag}")

    print("\n=== Parser constant lists ===")
    for cname, variants in consts.items():
        total = sum(len(v) for v in variants.values())
        print(f"  {cname:16s} files={total:3d} variants={len(variants)}")
        out["constants"][cname] = {f"v{i}": fs for i, (val, fs) in enumerate(variants.items())}

    (ROOT / "tools" / "dedup_map.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print("\nWrote tools/dedup_map.json")


if __name__ == "__main__":
    main()
