"""Checks for the web-layer plumbing (override splicing, coercion, golden diff)."""
import runner


def run():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append(f"{name}: got {got!r}, want {want!r}")

    # ── coercion table ───────────────────────────────────────────────
    check("coerce str->int", runner._coerce("42", {"type": "int"}), 42)
    check("coerce str->float", runner._coerce("2.5", {"type": "float"}), 2.5)
    check("coerce str->bool false", runner._coerce("false", {"type": "bool"}), False)
    check("coerce str->bool on", runner._coerce("on", {"type": "bool"}), True)
    check("coerce json str", runner._coerce("[1, 2]", {"type": "json"}), [1, 2])
    for bad, spec in [("abc", {"type": "int"}), (True, {"type": "int"}),
                      ("not[a]list", {"type": "json"})]:
        try:
            runner._coerce(bad, spec)
            fails.append(f"coerce should reject {bad!r} for {spec}")
        except runner.ParamError:
            pass

    # ── literal reconstruction for containers ────────────────────────
    check("literal set", eval(runner._literal(["a", "b"], "set")), {"a", "b"})
    check("literal empty set", runner._literal([], "set"), "set()")
    check("literal tuple", eval(runner._literal([1, 2], "tuple")), (1, 2))

    # ── override splicing on synthetic source ────────────────────────
    src = "X = 5\nY = [1,\n     2]\nZ = 'keep'\n"
    specs = {"X": {"type": "int"}, "Y": {"type": "json"}}
    out = runner.apply_overrides(src, {"X": 7}, specs)
    if "X = 7" not in out or "Z = 'keep'" not in out or "2]" not in out:
        fails.append(f"apply_overrides basic: {out!r}")
    out2 = runner.apply_overrides(src, {"Y": [9]}, specs)
    if "Y = [9]" not in out2 or "X = 5" not in out2:
        fails.append(f"apply_overrides multiline: {out2!r}")
    try:
        runner.apply_overrides(src, {"NOPE": 1}, {"NOPE": {"type": "int"}})
        fails.append("apply_overrides should reject unknown constant")
    except runner.ParamError:
        pass

    # ── golden comparison newline handling ───────────────────────────
    ref = runner.GOLDEN / "__sanity__.stdout.txt"
    try:
        runner.GOLDEN.mkdir(exist_ok=True)
        with open(ref, "w", encoding="utf-8", newline="") as fh:
            fh.write("line1\r\nline2\r\n")
        g = runner.compare_to_golden("__sanity__", "line1\nline2\n", False)
        check("golden crlf-normalized identical", g["state"], "identical")
        g2 = runner.compare_to_golden("__sanity__", "line1\nlineX\n", False)
        check("golden differs detected", g2["state"], "differs")
        check("golden changed count", g2["changed_lines"], 2)
        g3 = runner.compare_to_golden("__sanity__", "line1\nline2\n", True)
        check("golden overrides not compared", g3["state"],
              "not_comparable_overrides")
    finally:
        if ref.exists():
            ref.unlink()

    return fails
