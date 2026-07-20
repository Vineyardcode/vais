#!/usr/bin/env python3
"""Generate the static VAIS mirror into docs/ (served by GitHub Pages).

Read-only snapshot of the repo for people following the public link:
the 144-test catalog (docstrings, parameters, golden outputs), the
research program (RESEARCH.md incl. Phase 8), the overnight run
reports, and the adjudicated verdict ledger. No JavaScript, no external
assets, dark/light via prefers-color-scheme. Dependency-free (built-in
minimal markdown renderer — tables, lists, code fences, emphasis).

Regenerate after any result-changing commit:
    python tools/build_site.py
then commit docs/. GitHub Pages setting: deploy from branch, main /docs.
"""
import ast
import html
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webui"))
import registry as registry_mod  # noqa: E402

OUT = ROOT / "docs"
REPO_URL = "https://github.com/Vineyardcode/vais"

CSS = """
:root { --bg:#ffffff; --fg:#1a1a1a; --muted:#666; --line:#ddd;
        --code:#f5f5f5; --accent:#7a4a1e; --warn:#a33; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#141414; --fg:#ddd; --muted:#999; --line:#333;
          --code:#1e1e1e; --accent:#d9a05b; --warn:#e77; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
       font:16px/1.55 Georgia, 'Times New Roman', serif; }
nav { border-bottom:1px solid var(--line); padding:.7em 1.2em;
      font-family: system-ui, sans-serif; font-size:.9em; }
nav a { color:var(--accent); text-decoration:none; margin-right:1.2em; }
main { max-width: 62em; margin: 0 auto; padding: 1.5em 1.2em 4em; }
h1,h2,h3 { font-family: system-ui, sans-serif; line-height:1.25; }
h1 { font-size:1.7em; } h2 { font-size:1.3em; margin-top:2em; }
a { color: var(--accent); }
code, pre { font-family: ui-monospace, Consolas, monospace;
            font-size:.86em; background:var(--code); }
code { padding:.1em .3em; border-radius:3px; }
pre { padding: .9em; overflow-x:auto; border:1px solid var(--line);
      border-radius:4px; line-height:1.4; }
table { border-collapse: collapse; margin: 1em 0; font-size:.92em;
        display:block; overflow-x:auto; }
th, td { border:1px solid var(--line); padding:.35em .6em;
         text-align:left; vertical-align:top; }
th { font-family: system-ui, sans-serif; background:var(--code); }
blockquote { border-left:3px solid var(--accent); margin:1em 0;
             padding:.2em 1em; color:var(--muted); }
.muted { color:var(--muted); font-size:.9em; }
.tag { font-family: system-ui, sans-serif; font-size:.75em;
       border:1px solid var(--line); border-radius:3px;
       padding:.05em .45em; margin-left:.5em; }
.tag.sug { border-color:var(--warn); color:var(--warn); }
details summary { cursor:pointer; font-family: system-ui, sans-serif; }
input.param { font-family: ui-monospace, Consolas, monospace;
              font-size:.85em; width:24em; max-width:100%;
              background:var(--code); color:var(--fg);
              border:1px solid var(--line); border-radius:3px;
              padding:.25em .4em; }
button { font-family: system-ui, sans-serif; font-size:.95em;
         padding:.35em 1em; border:1px solid var(--accent);
         border-radius:4px; background:var(--code); color:var(--fg);
         cursor:pointer; }
button:disabled { opacity:.5; cursor:default; }
#run-out { min-height:2em; }
footer { border-top:1px solid var(--line); margin-top:3em;
         padding-top:1em; font-size:.85em; color:var(--muted); }
"""

esc = html.escape


def inline_md(s):
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    return s


def md_to_html(text):
    """Minimal renderer for the subset used by the repo's documents."""
    out, para, lines = [], [], text.replace("\r\n", "\n").split("\n")
    i, in_code, in_list = 0, False, None

    def flush_para():
        if para:
            out.append("<p>" + inline_md(" ".join(para)) + "</p>")
            para.clear()

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            flush_para()
            close_list()
            if not in_code:
                out.append("<pre>")
            else:
                out.append("</pre>")
            in_code = not in_code
            i += 1
            continue
        if in_code:
            out.append(esc(ln))
            i += 1
            continue
        s = ln.strip()
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            flush_para()
            close_list()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline_md(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if re.fullmatch(r"-{3,}", s):
            flush_para()
            close_list()
            out.append("<hr>")
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and \
                re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            flush_para()
            close_list()
            out.append("<table>")
            head = [c.strip() for c in s.strip("|").split("|")]
            out.append("<tr>" + "".join(f"<th>{inline_md(c)}</th>"
                                        for c in head) + "</tr>")
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|")
                         .split("|")]
                out.append("<tr>" + "".join(f"<td>{inline_md(c)}</td>"
                                            for c in cells) + "</tr>")
                i += 1
            out.append("</table>")
            continue
        if s.startswith(">"):
            flush_para()
            close_list()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip("> "))
                i += 1
            out.append("<blockquote>" + inline_md(" ".join(quote))
                       + "</blockquote>")
            continue
        m = re.match(r"^(\d+)\.\s+(.*)", s) or re.match(r"^[-*]\s+(.*)", s)
        if m:
            flush_para()
            kind = "ol" if m.re.pattern.startswith("^(\\d") else "ul"
            if in_list != kind:
                close_list()
                out.append(f"<{kind}>")
                in_list = kind
            item = m.group(m.lastindex)
            i += 1
            # continuation lines: 2+ spaces of hanging indent that are
            # not themselves new list items (RESEARCH.md uses 3-space
            # continuations under numbered items)
            while i < len(lines) and re.match(r"^\s{2,}\S", lines[i]) \
                    and not re.match(r"^\s{2,}(\d+\.|[-*])\s", lines[i]):
                item += " " + lines[i].strip()
                i += 1
            out.append(f"<li>{inline_md(item)}</li>")
            continue
        if not s:
            flush_para()
            close_list()
            i += 1
            continue
        para.append(s)
        i += 1
    flush_para()
    close_list()
    return "\n".join(out)


FULL_NAME = "VAIS - Voynich Analysis Interactive Suite"


def page(title, body, depth=0, stamp=""):
    p = "../" * depth
    full = FULL_NAME if title == "VAIS" else f"{title} — {FULL_NAME}"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full)}</title><style>{CSS}</style></head><body>
<nav><a href="{p}index.html">{esc(FULL_NAME)}</a><a href="{p}catalog.html">Catalog</a>
<a href="{p}research.html">Research</a><a href="{p}reports.html">Reports</a>
<a href="{p}credits.html">Credits</a><a href="{p}contributing.html">Contributing</a>
<a href="{REPO_URL}">GitHub</a></nav>
<main>{body}<footer>Static mirror — read-only. {stamp}
To run any test with your own parameters, clone
<a href="{REPO_URL}">the repository</a> and start the local web UI
(<code>python webui/server.py</code>). All numbers reproduce at
PYTHONHASHSEED=0.</footer></main></body></html>"""


def golden_text(stem):
    f = ROOT / "golden" / f"{stem}.stdout.txt"
    if not f.exists():
        return None
    t = f.read_text(encoding="utf-8", errors="replace", newline="")
    return t.replace("\r\r\n", "\n").replace("\r\n", "\n")


def build_data_pack():
    """Everything the tests read, zipped for the in-browser runner's
    virtual filesystem. Deterministic (sorted entries, fixed dates) so
    rebuilds only change git when content changes."""
    patterns = ("scripts/*.py", "scripts/common/*.py", "webui/runner.py",
                "folios/*.txt", "data/controls/*", "data/latin_texts/*",
                "data/gutenberg_cache/*", "data/translit/*",
                "results/*.json")
    zpath = OUT / "data_pack.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for pat in patterns:
            for f in sorted(ROOT.glob(pat)):
                if not f.is_file() or f.name.startswith(
                        ("_webui_", "_overnight_", "_web_")):
                    continue
                zi = zipfile.ZipInfo(
                    f.relative_to(ROOT).as_posix(),
                    date_time=(2020, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(zi, f.read_bytes())
    return zpath.stat().st_size


LOCAL_RUN = """<h2>Run it locally (full speed, byte-exact)</h2>
<pre>git clone {repo}
cd vais
pip install numpy flask
python scripts/{stem}.py        # this test; output also lands in results/
python webui/server.py          # or the full interactive UI at localhost:5000</pre>"""


def main():
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            cwd=ROOT, capture_output=True,
                            text=True).stdout.strip()
    stamp = (f"Generated {time.strftime('%Y-%m-%d')} from commit "
             f"<code>{commit}</code>. ")
    reg = registry_mod.build_registry()
    OUT.mkdir(exist_ok=True)
    (OUT / "tests").mkdir(exist_ok=True)
    (OUT / ".nojekyll").write_text("")
    for asset in (ROOT / "tools" / "site_assets").glob("*.js"):
        shutil.copy(asset, OUT / asset.name)
    pack_bytes = build_data_pack()

    # per-test pages
    for stem, t in reg.items():
        body = [f"<h1>{esc(stem)}</h1>",
                f'<p class="muted">{esc(t["file"])}'
                + (f' · baseline {t["baseline_seconds"]:.0f}s'
                   if t.get("baseline_seconds") else "")
                + (f' · depends on {", ".join(t["depends"])}'
                   if t["depends"] else "") + "</p>"]
        # full docstring (registry's 'doc' field truncates to 14 lines;
        # the registration ladders live deep in the docstrings)
        src = (ROOT / t["file"]).read_text(encoding="utf-8",
                                           errors="replace")
        full_doc = ast.get_docstring(ast.parse(src)) or t["doc"]
        body.append(f"<pre>{esc(full_doc)}</pre>")
        if t["params"]:
            body.append("<h2>Parameters</h2><p class=\"muted\">Edit a "
                        "value to override it for an in-browser run "
                        "(the script itself is never modified).</p>"
                        "<table><tr><th>name</th><th>type</th>"
                        "<th>value</th></tr>")
            for name, spec in t["params"].items():
                v = (str(spec["default"]) if spec["type"] == "str"
                     else repr(spec["default"]))
                body.append(f"<tr><td><code>{esc(name)}</code></td>"
                            f"<td>{esc(spec['type'])}</td>"
                            f'<td><input class="param" data-param='
                            f'"{esc(name)}" value="{esc(v)}"></td></tr>')
            body.append("</table>")
        secs = t.get("baseline_seconds") or 0
        slow = (f" <strong>This test takes ~{secs/60:.0f} min natively "
                "and several times longer in the browser — cloning is "
                "the fast path.</strong>" if secs > 120 else "")
        body.append(
            "<h2>Run it in your browser</h2>"
            "<p class=\"muted\">Python + numpy on WebAssembly, entirely "
            "on your machine — nothing is uploaded. First run downloads "
            "the runtime (~15 MB) and the repository data pack "
            "(~9 MB); both are cached afterwards. Expect it to be "
            f"slower than a native run.{slow}</p>"
            '<p><button id="run-btn">&#9654; Run</button> '
            '<button id="stop-btn">Stop</button> '
            '<span id="run-status" class="muted"></span></p>'
            '<pre id="run-out"></pre>')
        specs = {n: {"type": s["type"], "container": s["container"]}
                 for n, s in t["params"].items()}
        cfg = {"stem": stem, "specs": specs, "base": "../",
               "baselineSeconds": secs}
        body.append(f"<script>window.VAIS_TEST = {json.dumps(cfg)};"
                    '</script><script src="../runner.js"></script>')
        body.append(LOCAL_RUN.format(repo=REPO_URL, stem=stem))
        g = golden_text(stem)
        if g:
            body.append("<h2>Golden output (PYTHONHASHSEED=0)</h2>"
                        "<details><summary>show</summary>"
                        f'<pre id="golden-pre">{esc(g)}</pre></details>')
        (OUT / "tests" / f"{stem}.html").write_text(
            page(stem, "\n".join(body), depth=1, stamp=stamp),
            encoding="utf-8")

    # catalog
    body = [f"<h1>Test catalog — {len(reg)} runnable tests</h1>",
            "<table><tr><th>test</th><th>description</th><th>params</th>"
            "<th>baseline</th></tr>"]
    for stem, t in reg.items():
        secs = (f"{t['baseline_seconds']:.0f}s"
                if t.get("baseline_seconds") else "—")
        body.append(f'<tr><td><a href="tests/{stem}.html">{esc(stem)}</a>'
                    f"</td><td>{esc(t['description'][:110])}</td>"
                    f"<td>{len(t['params'])}</td><td>{secs}</td></tr>")
    body.append("</table>")
    (OUT / "catalog.html").write_text(
        page("Catalog", "\n".join(body), stamp=stamp), encoding="utf-8")

    # research + credits + reports
    research = (ROOT / "RESEARCH.md").read_text(encoding="utf-8")
    (OUT / "research.html").write_text(
        page("Research", md_to_html(research), stamp=stamp),
        encoding="utf-8")
    credits = (ROOT / "CREDITS.md").read_text(encoding="utf-8")
    (OUT / "credits.html").write_text(
        page("Credits", md_to_html(credits), stamp=stamp),
        encoding="utf-8")
    contrib = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    (OUT / "contributing.html").write_text(
        page("Contributing", md_to_html(contrib), stamp=stamp),
        encoding="utf-8")
    report_files = sorted(ROOT.glob("results/overnight_*_report.md"))
    report_files = [f for f in report_files if "smoke" not in f.name]
    links = ["<h1>Overnight run reports</h1><ul>"]
    for f in report_files:
        date = f.stem.replace("overnight_", "").replace("_report", "")
        (OUT / f"report_{date}.html").write_text(
            page(f"Report {date}",
                 md_to_html(f.read_text(encoding="utf-8")), stamp=stamp),
            encoding="utf-8")
        links.append(f'<li><a href="report_{date}.html">{date}</a></li>')
    links.append("</ul>")
    (OUT / "reports.html").write_text(
        page("Reports", "\n".join(links), stamp=stamp), encoding="utf-8")

    # index with the verdict ledger
    state = json.loads((ROOT / "results" / "overnight_state.json")
                       .read_text(encoding="utf-8"))
    body = ["<h1>VAIS — Voynich Analysis Interactive Suite</h1>",
            "<p>A reproducible laboratory for statistical analysis of "
            "the Voynich manuscript (Beinecke MS 408): "
            f"{len(reg)} runnable tests with pre-registered kill "
            "criteria, calibrated control corpora, golden reference "
            "outputs, and an adjudicated research program. Nothing here "
            "claims a decode; the methodology is the point.</p>",
            "<p>Every test page has a <strong>&#9654; Run</strong> "
            "button that executes the real instrument in your browser "
            "(Python on WebAssembly — nothing uploaded, nothing "
            "installed), plus copy-paste instructions for running it "
            "locally at full speed.</p>",
            f'<p><a href="catalog.html">Test catalog</a> · '
            f'<a href="research.html">Research program &amp; findings'
            f"</a> · <a href=\"reports.html\">Overnight reports</a> · "
            f'<a href="{REPO_URL}">Source on GitHub</a></p>',
            "<h2>Adjudicated verdict ledger</h2>",
            "<table><tr><th>item</th><th>verdict</th><th>date</th></tr>"]
    for k, v in sorted(state.items()):
        tag = (' <span class="tag sug">SUGGESTIVE — quarantined</span>'
               if v.get("suggestive") else "")
        body.append(f"<tr><td>{esc(k)}</td><td>{esc(v['verdict'])}{tag}"
                    f"</td><td>{esc(v.get('date', ''))}</td></tr>")
    body.append("</table>")
    body.append('<p class="muted">SUGGESTIVE entries are quarantined '
                "findings awaiting further scrutiny — reported as "
                "“consistent with”, never as decodes. Full criteria, "
                "registration history, and known weaknesses: "
                '<a href="research.html">Research</a> (Phase 8).</p>')
    (OUT / "index.html").write_text(
        page("VAIS", "\n".join(body), stamp=stamp), encoding="utf-8")

    n = len(list(OUT.rglob("*.html")))
    print(f"Wrote {n} pages to docs/ (commit {commit}); "
          f"data pack {pack_bytes / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
