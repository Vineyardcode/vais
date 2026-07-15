#!/usr/bin/env python3
"""Build scripts/common/ from canonical duplicated-function variants.

Method:
 1. Hash every top-level function with alpha-renamed args/locals and
    stripped docstrings, so formatting/naming differences collapse.
 2. For each (name, variant) group covering >= MIN_FILES files, pick a
    representative file and copy the source verbatim into
    scripts/common/core.py. The dominant variant keeps the bare name;
    smaller variants get a disambiguating suffix.
 3. Shared parser constants used by those functions are copied too
    (literal-compared across files for safety).

The companion rewriter (tools/rewrite_scripts.py) then replaces matching
local defs with imports. Nothing here edits existing scripts.
"""
import ast
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
COMMON = SCRIPTS / "common"
MIN_FILES = 4

# Functions we deliberately do NOT extract (coupled to per-script globals
# or too script-specific to centralize safely).
SKIP = {"main", "pr", "analyze", "synthesis"}

# Constants eligible for extraction when literal-identical across files.
CONST_NAMES = [
    "SIMPLE_GALLOWS", "BENCH_GALLOWS", "COMPOUND_GCH", "COMPOUND_GSH",
    "ALL_GALLOWS", "GALLOWS_TRI", "GALLOWS_BI", "GALLOWS_DI",
    "TRIGRAPHS", "DIGRAPHS", "SLOT_TOKENS", "MAX_CHUNKS",
]


class AlphaRenamer(ast.NodeTransformer):
    """Rename function arguments and purely-local names to canonical ids."""

    def __init__(self):
        self.mapping = {}

    def visit_FunctionDef(self, node):
        # collect args
        for a in node.args.args + node.args.kwonlyargs:
            self.mapping.setdefault(a.arg, f"_v{len(self.mapping)}")
            a.arg = self.mapping[a.arg]
        # collect assigned names inside
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                self.mapping.setdefault(sub.id, f"_v{len(self.mapping)}")
            elif isinstance(sub, (ast.For,)) and isinstance(sub.target, ast.Name):
                self.mapping.setdefault(sub.target.id, f"_v{len(self.mapping)}")
        self.generic_visit(node)
        return node

    def visit_Name(self, node):
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        return node


def strip_docstring(node):
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        node.body = node.body[1:] or [ast.Pass()]
    return node


def alpha_hash(fn_node):
    node = ast.parse(ast.unparse(fn_node)).body[0]
    node = strip_docstring(node)
    node = AlphaRenamer().visit(node)
    dump = ast.dump(node, annotate_fields=False, include_attributes=False)
    return hashlib.sha1(dump.encode()).hexdigest()[:12]


def external_names(fn_node):
    """Global names a function reads (candidate dependencies)."""
    assigned = set()
    for a in fn_node.args.args + fn_node.args.kwonlyargs:
        assigned.add(a.arg)
    for sub in ast.walk(fn_node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
            assigned.add(sub.id)
    loads = set()
    for sub in ast.walk(fn_node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
            loads.add(sub.id)
    import builtins
    return {n for n in loads - assigned if not hasattr(builtins, n)}


def main():
    # Pass 1: catalog all functions and constants
    func_variants = defaultdict(lambda: defaultdict(list))  # name -> ahash -> [(file, src, node)]
    const_values = defaultdict(lambda: defaultdict(list))   # name -> repr -> [file]
    const_src = {}

    for p in sorted(SCRIPTS.glob("*.py")):
        src = p.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name not in SKIP:
                seg = ast.get_source_segment(src, node)
                func_variants[node.name][alpha_hash(node)].append((p.name, seg, node))
            elif (isinstance(node, ast.Assign) and len(node.targets) == 1
                  and isinstance(node.targets[0], ast.Name)
                  and node.targets[0].id in CONST_NAMES):
                try:
                    val = repr(ast.literal_eval(node.value))
                except Exception:
                    continue
                cname = node.targets[0].id
                const_values[cname][val].append(p.name)
                const_src.setdefault((cname, val), ast.get_source_segment(src, node))

    # Pass 2: choose exports
    exports = []  # (export_name, orig_name, ahash, rep_file, src, n_files)
    for name, variants in sorted(func_variants.items()):
        big = [(len(v), h, v) for h, v in variants.items() if len(v) >= MIN_FILES]
        big.sort(reverse=True)
        for rank, (n, h, v) in enumerate(big):
            export = name if rank == 0 else f"{name}_v{rank + 1}"
            rep_file, seg, node = v[0]
            exports.append((export, name, h, rep_file, seg, n))

    # Constants: only single-variant ones get extracted
    const_exports = []
    for cname, variants in const_values.items():
        if len(variants) == 1:
            val = next(iter(variants))
            files = variants[val]
            if len(files) >= MIN_FILES:
                const_exports.append((cname, const_src[(cname, val)], len(files)))

    # Emit core.py
    COMMON.mkdir(exist_ok=True)
    lines = [
        '"""Shared analysis helpers extracted verbatim from the phase scripts.',
        "",
        "Every function below is a byte-for-byte copy (modulo the attribution",
        "comment) of the dominant variant found across scripts/, selected by",
        "AST hash with alpha-renaming. tools/build_common.py regenerates this",
        "file; tools/rewrite_scripts.py swaps matching local defs for imports.",
        "Divergent minority variants keep suffixed names (e.g. *_v2).",
        '"""',
        "import io",
        "import math",
        "import re",
        "import sys",
        "from collections import Counter, defaultdict",
        "from pathlib import Path",
        "",
        "try:",
        "    import numpy as np",
        "except ImportError:  # numpy optional for the pure-stdlib helpers",
        "    np = None",
        "",
        "PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent",
        "FOLIO_DIR = PROJECT_ROOT / 'folios'",
        "DATA_DIR = PROJECT_ROOT / 'data'",
        "RESULTS_DIR = PROJECT_ROOT / 'results'",
        "",
        "",
        "def utf8_stdout():",
        '    """The UTF-8 stdout wrapper used by 81 scripts (idempotent)."""',
        "    if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding.lower() != 'utf-8':",
        "        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')",
        "    return sys.stdout",
        "",
    ]

    lines.append("# ── shared constants " + "─" * 50)
    for cname, seg, n in sorted(const_exports):
        lines.append(f"# constant used identically in {n} scripts")
        lines.append(seg)
        lines.append("")

    manifest = {"functions": [], "constants": [c for c, _, _ in const_exports]}
    for export, name, h, rep, seg, n in exports:
        lines.append("")
        lines.append(f"# ── {export}: variant {h} from {rep} ({n} scripts)")
        if export != name:
            seg = seg.replace(f"def {name}(", f"def {export}(", 1)
        lines.append(seg)
        manifest["functions"].append(
            {"export": export, "name": name, "hash": h, "rep": rep, "files": n})

    (COMMON / "core.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (COMMON / "__init__.py").write_text(
        '"""Shared helpers for the Voynich analysis scripts."""\n'
        "from .core import *  # noqa: F401,F403\n", encoding="utf-8")
    (ROOT / "tools" / "common_manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")

    print(f"Extracted {len(exports)} function variants, {len(const_exports)} constants")
    for e in exports:
        print(f"  {e[0]:36s} <- {e[3]} ({e[5]} files)")


if __name__ == "__main__":
    main()
