"""Executes analysis scripts for the web UI.

A test run is the script's own code, unmodified except for requested
parameter overrides, which are spliced in as new literal values for the
matching module-level constant assignments (AST-located, source-level
replacement). The modified copy runs from scripts/ so relative and
__file__-based paths behave exactly like a manual run; stdout/stderr are
captured. No analysis logic lives in the web layer.
"""
import ast
import difflib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
RESULTS = ROOT / "results"
GOLDEN = ROOT / "golden"

DEFAULT_TIMEOUT = 900
MAX_DIFF_LINES = 400


class ParamError(ValueError):
    pass


def _literal(value, container):
    if container == "set":
        if not value:
            return "set()"
        return "{" + ", ".join(repr(v) for v in value) + "}"
    if container == "tuple":
        return repr(tuple(value))
    return repr(value)


def _coerce(value, spec):
    """Validate/coerce an override against the parameter spec."""
    t = spec["type"]
    try:
        if t == "int":
            if isinstance(value, bool):
                raise ParamError("expected int")
            return int(value)
        if t == "float":
            return float(value)
        if t == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on")
            return bool(value)
        if t == "str":
            return str(value)
        if t == "json":
            if isinstance(value, str):
                value = ast.literal_eval(value)
            if not isinstance(value, (list, dict, tuple, set)):
                raise ParamError("expected list/dict literal")
            return value
    except ParamError:
        raise
    except Exception as e:
        raise ParamError(f"invalid value: {e}")
    raise ParamError(f"unknown type {t}")


def apply_overrides(src, overrides, param_specs):
    """Return source with module-level constant assignments replaced."""
    tree = ast.parse(src)
    lines = src.splitlines()
    edits = []  # (start, end, replacement)
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in overrides):
            name = node.targets[0].id
            spec = param_specs[name]
            val = _coerce(overrides[name], spec)
            indent = lines[node.lineno - 1][:len(lines[node.lineno - 1])
                                            - len(lines[node.lineno - 1].lstrip())]
            repl = f"{indent}{name} = {_literal(val, spec.get('container'))}  # webui override"
            edits.append((node.lineno - 1, node.end_lineno - 1, repl))
    applied = {lines[s].split("=")[0].strip() for s, _, _ in edits}
    missing = set(overrides) - applied
    if missing:
        raise ParamError(f"parameters not found as module constants: {sorted(missing)}")
    for start, end, repl in sorted(edits, reverse=True):
        lines[start:end + 1] = [repl]
    return "\n".join(lines) + "\n"


def _results_snapshot():
    if not RESULTS.exists():
        return {}
    return {p.name: p.stat().st_mtime_ns for p in RESULTS.iterdir() if p.is_file()}


def compare_to_golden(name, stdout, had_overrides):
    """Diff a default-parameter run against the committed golden output.

    Runs execute under PYTHONHASHSEED=0, matching how golden/ was captured,
    so an identical result really means "nothing changed". Runs with
    parameter overrides are not comparable and are marked as such.
    """
    ref = GOLDEN / f"{name}.stdout.txt"
    if not ref.exists():
        return {"state": "no_reference"}
    if had_overrides:
        return {"state": "not_comparable_overrides"}
    # Normalize line endings on both sides: golden files are written with
    # newline='' but may carry legacy \r\r\n from older captures, and the
    # in-memory stream uses \r\n.
    def norm(t):
        return t.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    ref_text = norm(ref.read_text(encoding="utf-8", errors="replace", newline=""))
    stdout = norm(stdout)
    if ref_text == stdout:
        return {"state": "identical"}
    a, b = ref_text.splitlines(), stdout.splitlines()
    diff = list(difflib.unified_diff(a, b, fromfile="golden", tofile="this run",
                                     lineterm=""))
    changed = sum(1 for d in diff
                  if d[:1] in "+-" and d[:3] not in ("+++", "---"))
    return {
        "state": "differs",
        "changed_lines": changed,
        "golden_lines": len(a),
        "run_lines": len(b),
        "diff": "\n".join(diff[:MAX_DIFF_LINES]) +
                ("\n… (diff truncated)" if len(diff) > MAX_DIFF_LINES else ""),
    }


def run_test(name, overrides=None, param_specs=None, timeout=DEFAULT_TIMEOUT,
             progress_cb=None):
    script = SCRIPTS / f"{name}.py"
    if not script.exists():
        return {"status": "error", "error": f"unknown test {name}"}
    overrides = overrides or {}
    run_path = script
    tmp = None
    try:
        if overrides:
            if param_specs is None:
                raise ParamError("param specs required for overrides")
            src = script.read_text(encoding="utf-8")
            new_src = apply_overrides(src, overrides, param_specs)
            tmp = SCRIPTS / f"_webui_{name}_{uuid.uuid4().hex[:8]}.py"
            tmp.write_text(new_src, encoding="utf-8")
            run_path = tmp

        before = _results_snapshot()
        t0 = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, str(run_path)],
                cwd=str(ROOT), capture_output=True, timeout=timeout,
                # PYTHONHASHSEED pinned so outputs are comparable with golden/
                env={**os.environ, "PYTHONIOENCODING": "utf-8",
                     "PYTHONHASHSEED": "0"},
            )
            dur = time.time() - t0
            stdout = proc.stdout.decode("utf-8", errors="replace")
            stderr = proc.stderr.decode("utf-8", errors="replace")
            status = "ok" if proc.returncode == 0 else "error"
            rc = proc.returncode
        except subprocess.TimeoutExpired as e:
            dur = time.time() - t0
            stdout = (e.stdout or b"").decode("utf-8", errors="replace")
            stderr = (e.stderr or b"").decode("utf-8", errors="replace")
            status, rc = "timeout", None
        after = _results_snapshot()
        touched = sorted(k for k in after if k not in before or after[k] != before[k])
        return {
            "status": status, "returncode": rc, "duration_s": round(dur, 2),
            "stdout": stdout, "stderr": stderr, "results_files": touched,
            "overrides": overrides,
            "golden": compare_to_golden(name, stdout, bool(overrides))
                      if status == "ok" else {"state": "not_comparable_" + status},
        }
    except ParamError as e:
        return {"status": "param_error", "error": str(e)}
    finally:
        if tmp is not None and tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
