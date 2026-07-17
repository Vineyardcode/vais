#!/usr/bin/env python3
"""
tools/overnight.py — unattended overnight research runner (manual launch).

Started MANUALLY from a plain terminal before bed — never from inside an
agent session (permission prompts stall those):

    python tools/overnight.py            # next open queue item
    python tools/overnight.py N1         # a specific item
    python tools/overnight.py N1 --smoke # tiny-budget rehearsal of the
                                         # full pipeline (separate log/
                                         # report/branch; no state, no
                                         # RESEARCH.md writes)

CONTRACT
- One process, zero interaction. It never waits for input; a per-item
  timeout guarantees it never hangs. On any failure it writes the full
  traceback to the log, emits a partial report, commits what exists, and
  exits non-zero.
- PYTHONHASHSEED is pinned to 0 (the process re-execs itself if needed;
  experiment subprocesses inherit the pin).
- Progress streams to results/overnight_<date>.log (line-buffered — safe
  to tail while running). The adjudicated human-readable report goes to
  results/overnight_<date>_report.md.
- Experiments run their control battery before the manuscript (enforced
  inside the scripts themselves); adjudication here re-derives verdicts
  from the results JSON against the PRE-REGISTERED criteria — never from
  eyeballing stdout, and never against criteria invented after seeing
  the numbers.
- Results are committed to branch overnight/<date> using git plumbing
  (temporary index -> write-tree -> commit-tree -> update-ref). The
  working tree checkout and the current branch are never touched, and by
  construction nothing is ever committed to main.
- Any decode-like or positive finding is quarantined under "SUGGESTIVE —
  awaiting human review": flagged at the top of the report and appended
  to RESEARCH.md (that edit is committed only to the overnight branch;
  merging is a human decision). A kill is a valid result and is logged
  in RESEARCH.md with equal prominence.

QUEUE
  N1  Max-strength verbose cipher inversion (rung 3): folio-level
      holdout + the pre-registered budget EM_OUTER=32, EM_PROPOSALS=48,
      EM_RESTARTS=16, RESTARTS=64, TOP_LMS_RUNG2=3, spliced over the
      prototype defaults of scripts/verbose_cipher_inversion.py (see its
      docstring ladder for the registration history).
  N2  Cross-transliteration invariance (portfolio S9) — NOT READY:
      needs external transliteration files (Currier, v101, GC) plus
      scripts/cross_transliteration_invariance.py with pre-registered
      criteria in its docstring and an adjudicator registered here.
  N3  Line-as-record structures (portfolio S7) — NOT READY: needs
      scripts/line_as_record_structures.py (pre-registered kill per
      RESEARCH.md S7: field structure matched by the N1 word-shuffle
      control = line-length artifact) and an adjudicator here.

Adding an item = write the experiment script (controls first, kill
criteria in the docstring), then fill in the queue entry's 'stem',
'overrides', 'result_json' and an adjudicate_<id>() that reads the JSON
and returns a verdict dict. Nothing else changes.

State lives in results/overnight_state.json. An item stays open until a
run completes THROUGH adjudication — kills count as completed (a kill is
a result); crashes leave the item open for retry.

Exit codes: 0 = ran to a verdict (pass OR kill), 1 = failure (partial
report written), 2 = queue item not ready / nothing open.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'
RESULTS = ROOT / 'results'
RESEARCH_MD = ROOT / 'RESEARCH.md'
STATE_PATH = RESULTS / 'overnight_state.json'

sys.path.insert(0, str(ROOT))
from webui.runner import apply_overrides  # noqa: E402  (the same AST-level
# constant splicing the web UI uses; scripts are never modified in place)

BANNER_MARK = '<!-- OVERNIGHT-SUGGESTIVE -->'
BANNER = (
    '> **SUGGESTIVE FINDING — AWAITING HUMAN REVIEW — DO NOT MERGE.**\n'
    '> A run below produced a decode-like/positive signal. It is\n'
    '> quarantined: committed only to its overnight/ branch, claims\n'
    '> nothing beyond "consistent with", and is not a decode. See the\n'
    '> flagged run section for the numbers and the pre-registered\n'
    '> criteria they were judged against.')


class RunFailed(Exception):
    pass


class AdjudicationError(Exception):
    pass


class NotReady(Exception):
    pass


# ────────────────────────────────────────────────────────────────────
# logging: line-buffered file + console tee
# ────────────────────────────────────────────────────────────────────
class Log:
    """Runner lines are timestamped; child (experiment) lines carry a
    '  | ' prefix so a tail distinguishes orchestration from science."""

    def __init__(self, path):
        self.path = path
        self.fh = open(path, 'a', encoding='utf-8', buffering=1, newline='\n')
        try:
            sys.stdout.reconfigure(errors='replace')
        except Exception:
            pass

    def _emit(self, text):
        self.fh.write(text + '\n')
        try:
            print(text)
        except Exception:
            pass

    def line(self, msg):
        self._emit(f'[{time.strftime("%H:%M:%S")}] {msg}')

    def child(self, msg):
        self._emit('  | ' + msg)

    def close(self):
        try:
            self.fh.close()
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────
# experiment execution (streaming, timeout-guarded)
# ────────────────────────────────────────────────────────────────────
def run_script(stem, overrides, timeout_s, log):
    """Run scripts/<stem>.py with UPPERCASE-constant overrides spliced
    into a temporary copy (deleted afterwards; '_'-prefixed names are
    invisible to the web UI registry and gitignored like _webui_*).
    Streams combined stdout/stderr to the log. Returns (rc, seconds,
    timed_out)."""
    script = SCRIPTS / f'{stem}.py'
    if not script.exists():
        raise RunFailed(f'script missing: {script}')
    run_path, tmp = script, None
    if overrides:
        specs = {k: {'type': 'int'} for k in overrides}
        src = script.read_text(encoding='utf-8')
        tmp = SCRIPTS / f'_overnight_{stem}.py'
        tmp.write_text(apply_overrides(src, overrides, specs),
                       encoding='utf-8')
        run_path = tmp
        log.line(f'spliced overrides {overrides} -> {tmp.name}')
    env = {**os.environ, 'PYTHONHASHSEED': '0', 'PYTHONIOENCODING': 'utf-8',
           'PYTHONUNBUFFERED': '1'}
    t0 = time.time()
    proc = subprocess.Popen([sys.executable, str(run_path)], cwd=str(ROOT),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, env=env)

    def pump():
        for raw in iter(proc.stdout.readline, b''):
            log.child(raw.decode('utf-8', errors='replace').rstrip('\r\n'))

    reader = threading.Thread(target=pump, daemon=True)
    reader.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        log.line(f'TIMEOUT after {timeout_s}s — killing the experiment')
        proc.kill()
        proc.wait()
    reader.join(timeout=30)
    if tmp is not None:
        try:
            tmp.unlink()
        except OSError:
            pass
    return proc.returncode, time.time() - t0, timed_out


# ────────────────────────────────────────────────────────────────────
# git plumbing: commit results to overnight/<date> without touching the
# working tree or the checked-out branch
# ────────────────────────────────────────────────────────────────────
def git(args, env=None):
    p = subprocess.run(['git'] + args, cwd=str(ROOT), capture_output=True,
                       text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(f'git {" ".join(args)}: {p.stderr.strip() or p.stdout.strip()}')
    return p.stdout.strip()


def commit_results(branch, paths, message):
    """Plumbing commit: parent = existing branch tip (runs chain) or the
    current HEAD. A temporary GIT_INDEX_FILE means no checkout, no
    staging-area side effects, no chance of landing on main."""
    if not branch.startswith('overnight/'):
        raise RuntimeError(f'refusing to commit to non-overnight branch {branch!r}')
    try:
        parent = git(['rev-parse', '--verify', '-q', f'refs/heads/{branch}'])
    except RuntimeError:
        parent = git(['rev-parse', 'HEAD'])
    fd, index = tempfile.mkstemp(prefix='overnight_index_')
    os.close(fd)
    os.unlink(index)  # git creates it; an empty pre-existing file confuses it
    env = {**os.environ, 'GIT_INDEX_FILE': index}
    try:
        git(['read-tree', parent], env=env)
        rels = [Path(p).resolve().relative_to(ROOT).as_posix()
                for p in paths if Path(p).exists()]
        if not rels:
            raise RuntimeError('no result files exist to commit')
        git(['update-index', '--add', '--'] + rels, env=env)
        tree = git(['write-tree'], env=env)
        commit = git(['commit-tree', tree, '-p', parent, '-m', message],
                     env=env)
        git(['update-ref', f'refs/heads/{branch}', commit])
        return commit
    finally:
        try:
            os.unlink(index)
        except OSError:
            pass


# ────────────────────────────────────────────────────────────────────
# report + RESEARCH.md writers
# ────────────────────────────────────────────────────────────────────
def write_report(path, date, run_section, suggestive):
    title = f'# Overnight report — {date}\n'
    content = path.read_text(encoding='utf-8') if path.exists() else title
    if suggestive and BANNER_MARK not in content:
        lines = content.split('\n')
        lines.insert(1, '\n' + BANNER_MARK + '\n' + BANNER)
        content = '\n'.join(lines)
    content = content.rstrip('\n') + '\n\n' + run_section.rstrip('\n') + '\n'
    path.write_text(content, encoding='utf-8', newline='\n')


def append_research(section):
    with open(RESEARCH_MD, 'a', encoding='utf-8', newline='\n') as fh:
        fh.write('\n---\n\n' + section.rstrip('\n') + '\n')


def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=1), encoding='utf-8',
                          newline='\n')


# ────────────────────────────────────────────────────────────────────
# N1 adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n1(item, expected_params, run_started):
    """Re-derives the verdict from results/verbose_cipher_inversion.json
    against the PRE-REGISTERED criteria (script docstring, RESEARCH.md
    Phase 4b): the instrument passes ONLY if rung-2 P4 planted-inventory
    recovery (latin/plain LM) >= 50% AND rung-2 P4 best gap beats the
    same-rung noise floor (best of N2/N3/N4) by >= 0.1 bits/sym. VMS
    rows are interpreted only if the instrument passes, and only ever as
    'consistent with a verbose cipher' — never 'decoded'."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale '
                                'file; the experiment did not write it')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    params = data.get('params', {})
    for k, v in expected_params.items():
        if params.get(k.lower()) != v:
            raise AdjudicationError(
                f'results JSON ran with {k.lower()}={params.get(k.lower())}, '
                f'expected {v} — refusing to adjudicate a mismatched run')
    if params.get('holdout_unit') != 'folio':
        raise AdjudicationError('results JSON is not from the folio-holdout '
                                'instrument (rung 3)')

    r1, r2 = data['rung1'], data['rung2']
    p4 = r2['results']['P4_latin_verbose']
    lp = p4.get('latin/plain', {})
    rec = lp.get('inventory_recovery', 0.0)
    acc = lp.get('mapping_accuracy', 0.0)
    floor = r2['noise_floor']
    gap = p4['best_gap']
    margin = gap - floor
    rec_ok, margin_ok = rec >= 0.5, margin >= 0.1
    instrument_ok = rec_ok and margin_ok

    vms = {}
    for v in ('VMS_full', 'VMS_currier_A', 'VMS_currier_B'):
        row = r2['results'][v]
        vms[v] = (row['best_lm'], row['best_gap'],
                  row['best_gap'] - floor >= 0.1)
    suggestive = instrument_ok and any(hit for _, _, hit in vms.values())

    def pf(ok):
        return 'PASS' if ok else '**FAIL**'

    md = []
    md.append('**Pre-registered criteria** (verbose_cipher_inversion.py '
              'docstring; RESEARCH.md Phase 4b): instrument passes only if '
              'BOTH hold — P4 planted-inventory recovery >= 50% AND P4 best '
              'holdout gap beats the same-rung noise floor by >= 0.1 '
              'bits/sym. VMS rows are interpreted only if the instrument '
              'passes, and only as "consistent with", never "decoded".')
    md.append('')
    md.append('| pre-registered check | threshold | actual | verdict |')
    md.append('|---|---|---|---|')
    md.append(f'| P4 inventory recovery (rung 2, latin/plain LM) | >= 50% | '
              f'{rec:.0%} (mapping accuracy {acc:.0%}) | {pf(rec_ok)} |')
    md.append(f'| P4 gap − noise floor (rung 2) | >= +0.100 bits/sym | '
              f'{margin:+.3f} (gap {gap:+.3f} via {p4["best_lm"]}, floor '
              f'{floor:+.3f}) | {pf(margin_ok)} |')
    md.append('')
    md.append('Rung-2 holdout gaps (folio-level holdout, this budget):')
    md.append('')
    md.append('| corpus | best LM | gap (bits/sym) | gap − floor | '
              'holdout words excluded |')
    md.append('|---|---|---|---|---|')
    for cname, row in r2['results'].items():
        e = row.get(row['best_lm'], {})
        excl = e.get('excluded_words')
        excl_s = f'{excl:.1%}' if isinstance(excl, (int, float)) else 'n/a'
        if e.get('degenerate'):
            excl_s += ' — DEGENERATE ROW'
        md.append(f'| {cname} | {row["best_lm"]} | {row["best_gap"]:+.3f} | '
                  f'{row["best_gap"] - floor:+.3f} | {excl_s} |')
    r1p4 = r1['results']['P4_latin_verbose']
    md.append('')
    md.append(f'Rung 1 for the record: P4 segmenter inventory recovery '
              f'{r1p4.get("inventory_recovery", 0.0):.0%}, best gap '
              f'{r1p4["best_gap"]:+.3f} vs rung-1 noise floor '
              f'{r1["noise_floor"]:+.3f}.')
    md.append('')

    if not instrument_ok:
        verdict = 'INSTRUMENT KILLED (pre-registered)'
        md.append(f'**VERDICT: {verdict}.** At this budget, with the '
                  'folio-holdout memorization leak closed, the strict 1:1 '
                  'inverter still cannot invert a KNOWN verbose cipher '
                  'clearly above what a free mapping extracts from '
                  'meaningless text. Per the pre-registered protocol the '
                  'VMS rows below are NOT interpretable (shown for the '
                  'record only):')
        md.append('')
        for v, (lm, g, _) in vms.items():
            md.append(f'- {v}: best gap {g:+.3f} ({lm}) — not interpretable, '
                      'instrument killed')
        md.append('')
        md.append('The compute rungs of the ladder are now exhausted. The '
                  'next rung would relax model strictness (homophones / '
                  'positional variants), which per the pre-registration '
                  'requires a human-logged justification in the script '
                  'docstring BEFORE any run — not an overnight decision.')
    else:
        verdict = 'INSTRUMENT PASSED'
        md.append(f'**VERDICT: {verdict}** — the known cipher was inverted '
                  'above the noise floor at this rung. VMS rows, read under '
                  'the pre-registered vocabulary:')
        md.append('')
        for v, (lm, g, hit) in vms.items():
            if hit:
                md.append(f'- {v}: best gap {g:+.3f} ({lm}) — beats the '
                          'noise floor by >= 0.1 bits/sym: **consistent '
                          'with a verbose cipher — NOT a decode. '
                          'SUGGESTIVE, quarantined, awaiting human '
                          'review.** No mapping table is to be read or '
                          'published from this run until a human '
                          're-derives it on fresh holdout (charter rule 5).')
            else:
                md.append(f'- {v}: best gap {g:+.3f} ({lm}) — within the '
                          'noise floor: nothing beyond free-mapping noise '
                          'at this rung (a clean negative for the strict '
                          '1:1 verbose-cipher family under these 6 LMs).')

    summary = (f'{verdict}; P4 recovery {rec:.0%}, margin {margin:+.3f} '
               f'(need >= +0.100)')
    return {'verdict': verdict, 'suggestive': suggestive,
            'md': '\n'.join(md), 'summary': summary,
            'params': params, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# queue
# ────────────────────────────────────────────────────────────────────
N1_PROFILE = {'EM_OUTER': 32, 'EM_PROPOSALS': 48, 'EM_RESTARTS': 16,
              'RESTARTS': 64, 'TOP_LMS_RUNG2': 3}
N1_SMOKE = {'EM_OUTER': 1, 'EM_PROPOSALS': 1, 'EM_RESTARTS': 1,
            'RESTARTS': 2, 'TOP_LMS_RUNG2': 1}

QUEUE = [
    {
        'id': 'N1',
        'title': 'Max-strength verbose cipher inversion (rung 3: '
                 'folio-level holdout, pre-registered budget)',
        'stem': 'verbose_cipher_inversion',
        'overrides': N1_PROFILE,
        'smoke_overrides': N1_SMOKE,
        'timeout_s': 12 * 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'verbose_cipher_inversion.json',
        'adjudicate': adjudicate_n1,
        'not_ready': None,
    },
    {
        'id': 'N2',
        'title': 'Cross-transliteration invariance audit (portfolio S9)',
        'stem': 'cross_transliteration_invariance',
        'not_ready': 'needs external transliteration files (Currier, v101, '
                     'GC — data acquisition) and '
                     'scripts/cross_transliteration_invariance.py with '
                     'pre-registered criteria + an adjudicator in this file',
    },
    {
        'id': 'N3',
        'title': 'Line-as-record structures (portfolio S7)',
        'stem': 'line_as_record_structures',
        'not_ready': 'needs scripts/line_as_record_structures.py (kill '
                     'criterion per RESEARCH.md S7: field structure matched '
                     'by the N1 word-shuffle control = line-length artifact) '
                     '+ an adjudicator in this file',
    },
]


def pick_item(state, wanted):
    if wanted:
        for it in QUEUE:
            if it['id'] == wanted:
                return it
        raise NotReady(f'unknown queue item {wanted!r} — queue is '
                       f'{[q["id"] for q in QUEUE]}')
    for it in QUEUE:
        if state.get(it['id'], {}).get('status') != 'completed':
            return it
    return None


# ────────────────────────────────────────────────────────────────────
def ensure_hashseed():
    if os.environ.get('PYTHONHASHSEED') != '0':
        env = {**os.environ, 'PYTHONHASHSEED': '0'}
        sys.exit(subprocess.run([sys.executable] + sys.argv, env=env).returncode)


def main():
    ensure_hashseed()
    smoke = '--smoke' in sys.argv
    pos = [a for a in sys.argv[1:] if not a.startswith('--')]
    wanted = pos[0] if pos else None
    date = time.strftime('%Y-%m-%d')
    sfx = '_smoke' if smoke else ''
    RESULTS.mkdir(exist_ok=True)
    log_path = RESULTS / f'overnight_{date}{sfx}.log'
    report_path = RESULTS / f'overnight_{date}{sfx}_report.md'
    branch = f'overnight/{date}' + ('-smoke' if smoke else '')
    log = Log(log_path)
    state = load_state()
    started = time.strftime('%Y-%m-%d %H:%M:%S')
    t_run0 = time.time()
    item = None
    section = []  # accumulated report section (works for partial reports)

    def finalize(exit_code, suggestive=False, research_section=None):
        """Everything that must happen no matter how the run ended:
        report to disk, RESEARCH.md (real runs with a verdict), state,
        git commit to the overnight branch. Never raises."""
        try:
            write_report(report_path, date, '\n'.join(section), suggestive)
            log.line(f'report -> {report_path}')
        except Exception:
            log.line('FAILED writing report:\n' + traceback.format_exc())
        if research_section and not smoke:
            try:
                append_research(research_section)
                log.line('RESEARCH.md: section appended (working tree; '
                         'committed only to the overnight branch)')
            except Exception:
                log.line('FAILED appending RESEARCH.md:\n'
                         + traceback.format_exc())
        if not smoke:
            try:
                save_state(state)
            except Exception:
                log.line('FAILED writing state:\n' + traceback.format_exc())
        try:
            files = [log_path, report_path, STATE_PATH]
            if item and item.get('result_json'):
                files.append(RESULTS / item['result_json'])
            if not smoke:
                files.append(RESEARCH_MD)
            iid = item['id'] if item else 'queue'
            msg = (f'overnight {date}: {iid} '
                   f'{state.get(iid, {}).get("verdict", "partial/failed") if not smoke else "smoke rehearsal"}')
            log.line(f'committing results to branch {branch} ...')
            commit = commit_results(branch, files, msg)
            log.line(f'committed {commit[:12]} on {branch} (main untouched)')
        except Exception:
            log.line('FAILED git commit (results remain on disk):\n'
                     + traceback.format_exc())
        log.line(f'done, exit {exit_code}')
        log.close()
        sys.exit(exit_code)

    log.line('=' * 68)
    log.line(f'overnight runner start {started}  smoke={smoke} '
             f'PYTHONHASHSEED={os.environ.get("PYTHONHASHSEED")}')
    try:
        head = git(['rev-parse', '--short', 'HEAD'])
        dirty = git(['status', '--porcelain']).strip()
        log.line(f'code at {head} ({"dirty" if dirty else "clean"} tree), '
                 f'python {sys.version.split()[0]}')
    except Exception as e:
        log.line(f'git introspection failed: {e}')

    try:
        item = pick_item(state, wanted)
        if item is None:
            log.line('queue: every item completed — nothing open. '
                     'Pass an item id to re-run one explicitly.')
            section = [f'## Run {started} — queue empty',
                       'All queue items are completed in '
                       'results/overnight_state.json; nothing was run.']
            finalize(2)
        if item.get('not_ready'):
            raise NotReady(f'{item["id"]} is not ready: {item["not_ready"]}')

        overrides = item['smoke_overrides'] if smoke else item['overrides']
        timeout_s = item['smoke_timeout_s'] if smoke else item['timeout_s']
        log.line(f'queue item {item["id"]}: {item["title"]}')
        log.line(f'profile: {overrides}  timeout={timeout_s}s')
        section = [f'## Run {started} — {item["id"]}'
                   + (' (SMOKE REHEARSAL — tiny budget, not science)'
                      if smoke else ''),
                   f'**{item["title"]}**',
                   f'- script: `scripts/{item["stem"]}.py`',
                   f'- profile: `{overrides}`',
                   f'- log: `{log_path.name}`; results JSON: '
                   f'`{item["result_json"]}`; branch: `{branch}`']

        rc, dur, timed_out = run_script(item['stem'], overrides, timeout_s,
                                        log)
        hours = dur / 3600
        log.line(f'experiment finished rc={rc} in {dur:.0f}s ({hours:.2f}h)'
                 + (' TIMED OUT' if timed_out else ''))
        section.append(f'- runtime: {dur:.0f}s ({hours:.2f} h), exit code '
                       f'{rc}{" — TIMED OUT and killed" if timed_out else ""}')
        if timed_out or rc != 0:
            raise RunFailed(f'experiment {"timed out" if timed_out else f"exited rc={rc}"}'
                            ' — see the child output above in the log')

        adj = item['adjudicate'](item, overrides, t_run0)
        log.line(f'adjudication: {adj["summary"]}')
        section.append('')
        section.append(adj['md'])

        research_section = None
        if item['id'] == 'N1':
            research_section = build_n1_research_section(
                date, adj, overrides, dur, branch, smoke)
            if smoke:
                section.append('')
                section.append('---')
                section.append('*Smoke mode: the following RESEARCH.md '
                               'section was generated but NOT appended:*')
                section.append('')
                section.append(research_section)

        if not smoke:
            state[item['id']] = {'status': 'completed', 'date': date,
                                 'verdict': adj['verdict'],
                                 'suggestive': adj['suggestive'],
                                 'summary': adj['summary']}
        if adj['suggestive']:
            log.line('SUGGESTIVE finding — quarantined, flagged at the top '
                     'of the report, awaiting human review')
        finalize(0, suggestive=adj['suggestive'],
                 research_section=research_section)

    except NotReady as e:
        log.line(f'NOT READY: {e}')
        section = section or [f'## Run {started} — not ready']
        section.append('')
        section.append(f'**NOT READY:** {e}')
        finalize(2)
    except Exception:
        tb = traceback.format_exc()
        log.line('FAILURE:\n' + tb)
        section = section or [f'## Run {started} — FAILED before start']
        section.append('')
        section.append('**RUN FAILED — partial report.** Traceback:')
        section.append('')
        section.append('```')
        section.append(tb.rstrip())
        section.append('```')
        if item is not None and not smoke:
            state[item['id']] = {'status': 'error', 'date': date,
                                 'error': tb.splitlines()[-1]}
        finalize(1)


def build_n1_research_section(date, adj, overrides, dur, branch, smoke):
    killed = adj['verdict'].startswith('INSTRUMENT KILLED')
    head = ('### Phase 4c — Verbose cipher inversion, rung 3: max strength '
            f'+ folio-level holdout ({date})')
    tag = ('[AUTOMATED — written by tools/overnight.py'
           + (', smoke rehearsal' if smoke else '')
           + f'; run committed to branch {branch}; awaiting human review '
             'before promotion to any evidence tier.]')
    body = [head, '', tag, '',
            f'Budget (pre-registered in the script docstring): {overrides}. '
            f'Runtime {dur/3600:.2f} h at PYTHONHASHSEED=0. Holdout: whole '
            'folios (VMS) / 24-line pseudo-folios (controls), closing the '
            'rung-2 Currier-A memorization leak.', '']
    if adj['suggestive']:
        body.append('**SUGGESTIVE — awaiting human review (quarantined; '
                    'never merged automatically):**')
        body.append('')
    body.append(adj['md'])
    if killed:
        body.append('')
        body.append('The corpse is logged with the same prominence as a '
                    'positive would be, per charter rule 5.')
    return '\n'.join(body)


if __name__ == '__main__':
    main()
