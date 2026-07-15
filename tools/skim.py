#!/usr/bin/env python3
"""Compact per-script summary for inventory work: docstring, functions,
tunable constants, file I/O, seeds. Usage: python tools/skim.py name1 name2 ..."""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for name in sys.argv[1:]:
    p = ROOT / "scripts" / (name if name.endswith(".py") else name + ".py")
    src = p.read_text(encoding="utf-8", errors="replace")
    t = ast.parse(src)
    doc = ast.get_docstring(t) or ""
    funcs = [n.name for n in t.body if isinstance(n, ast.FunctionDef)]
    consts = []
    for n in t.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            nm = n.targets[0].id
            if nm.isupper() and isinstance(n.value, (ast.Constant, ast.Num)):
                try:
                    consts.append(f"{nm}={ast.literal_eval(n.value)}")
                except Exception:
                    pass
    writes = sorted(set(re.findall(r"""open\(['"]([^'"]+)['"],\s*['"]w""", src)))
    writes += sorted(set(re.findall(r"""(results/[\w.]+)['"]""", src)))
    reads = sorted(set(re.findall(r"""open\(['"]([^'"]+\.json)['"][,)]""", src)))
    seeds = re.findall(r"(random\.seed\(\d+\)|np\.random\.seed\(\d+\))", src)
    lines = src.count("\n") + 1
    print(f"##### {p.name} ({lines} ln)")
    print(doc[:750].strip())
    print(f"FUNCS: {funcs}")
    if consts:
        print(f"CONSTS: {consts[:15]}")
    print(f"WRITES: {sorted(set(writes))}  READS: {reads}  SEEDS: {seeds}")
    print()
