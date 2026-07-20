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

QUEUE (order = run order; N3 promoted ahead of N2 by direction
2026-07-17: "put the line-as-record test next in the queue")
  N1  [SUPERSEDED, completed 2026-07-17: INSTRUMENT KILLED] rung-3
      max-strength verbose cipher inversion. The script now carries the
      rung-3b objective, so N1 as registered can no longer be re-run;
      use N1b.
  N1b Rung 3b: same instrument with the coverage-penalized objective
      (registered in the script docstring after rung 3's
      exclusion-exploit autopsy, before any 3b run). Same budget:
      EM_OUTER=32, EM_PROPOSALS=48, EM_RESTARTS=16, RESTARTS=64,
      TOP_LMS_RUNG2=3. Same kill criteria.
  N3  Line-as-record structures (portfolio S7),
      scripts/line_as_record_structures.py: interior positional-field
      information vs the N1 word-shuffle artifact baseline; instrument
      gate on the P-REC synthetic-records positive control. Gates
      pre-registered in the script docstring.
  N3b Line-as-record RUNG 2 (per-hand), scripts/line_as_record_per_hand
      .py: registered follow-up to N3's post-hoc Currier-B observation,
      made strictly harder (per-hand null batteries, 10-split medians,
      empirical p vs 20 nulls + 0.05 effect floor). Full provenance
      disclosure in the script docstring.
  N3c Line-as-record RUNG 3 (composition vs ordinal),
      scripts/line_as_record_ordinal.py: Phase-7-informed separation of
      the B signal into composition / length-ordinal / glyph-ordinal
      readings (folio-nulls, line-nulls, glyph-only test, P-JUST
      justification reference, per-folio read-outs).
  N2  Cross-transliteration invariance (portfolio S9),
      scripts/cross_transliteration_invariance.py: A1 audit over CD /
      GC(v101) / FSG / IT files (data/translit/, voynich.nu) —
      fingerprint spread report + the S7-B ordinal battery per reading
      with alphabet-agnostic features; robust / partial /
      artifact_suspect ladder pre-registered in the docstring.

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
    if item.get('objective') and params.get('objective') != item['objective']:
        raise AdjudicationError(
            f'results JSON objective={params.get("objective")!r}, item '
            f'requires {item["objective"]!r} — code/queue mismatch')

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
# N3 adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n3(item, expected_params, run_started):
    """Pre-registered gates (line_as_record_structures.py docstring):
    instrument gate = P-REC interior gain >= gate_prec_min AND P1
    interior gain <= gate_p1_max; kill if VMS_full - N1 < kill_margin;
    positive (quarantined SUGGESTIVE) only if all three VMS rows beat
    N1 by >= kill_margin (F8 concordance); otherwise discordant = no
    claim. The runner re-derives the verdict and refuses to proceed if
    it disagrees with the script's own."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, r = data['params'], data['results']
    prec = r['PREC_records']['interior_gain']
    p1 = r['P1_latin_plain']['interior_gain']
    n1 = r['N1_word_shuffle']['interior_gain']
    gate_ok = prec >= p['gate_prec_min'] and p1 <= p['gate_p1_max']
    vms_rows = ('VMS_full', 'VMS_currier_A', 'VMS_currier_B')
    margins = {v: round(r[v]['interior_gain'] - n1, 4) for v in vms_rows}
    if not gate_ok:
        key = 'instrument_gate_failed'
    elif margins['VMS_full'] < p['kill_margin']:
        key = 'killed_line_length_artifact'
    elif all(m >= p['kill_margin'] for m in margins.values()):
        key = 'consistent_with_records'
    else:
        key = 'discordant_hands'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'consistent_with_records'

    md = []
    md.append('**Pre-registered gates** (line_as_record_structures.py '
              f'docstring): instrument gate P-REC >= {p["gate_prec_min"]} '
              f'and P1 <= {p["gate_p1_max"]} interior bits/token; kill if '
              f'VMS_full − N1 < {p["kill_margin"]}; positive only if all '
              'three VMS rows clear the margin (F8 concordance). Headline '
              'is INTERIOR gain — the line edges are the already-'
              'established anomaly.')
    md.append('')
    md.append('| corpus | interior gain (bits/token) | edge gain | '
              'margin over N1 |')
    md.append('|---|---|---|---|')
    for cname, row in r.items():
        marg = (f'{row["interior_gain"] - n1:+.4f}'
                if cname in vms_rows else '—')
        md.append(f'| {cname} | {row["interior_gain"]:+.4f} | '
                  f'{row["edge_gain"]:+.4f} | {marg} |')
    md.append('')
    md.append(f'Instrument gate: P-REC {prec:+.4f}, P1 {p1:+.4f} → '
              f'{"PASS" if gate_ok else "**FAIL**"}.')
    verdict_text = {
        'instrument_gate_failed':
            'INSTRUMENT GATE FAILED — no VMS interpretation.',
        'killed_line_length_artifact':
            'KILLED (pre-registered): VMS_full interior margin '
            f'{margins["VMS_full"]:+.4f} < {p["kill_margin"]} — interior '
            'positional structure is not distinguishable from a '
            'line-length artifact at this instrument. The moat stays at '
            'the line EDGES.',
        'consistent_with_records':
            'POSITIVE (quarantined SUGGESTIVE): all three VMS rows beat '
            'the N1 artifact baseline — consistent with line-level field '
            'structure. NOT a decode; no field is named or read.',
        'discordant_hands':
            'DISCORDANT HANDS — VMS_full clears the margin but Currier '
            'A/B disagree; no claim (discordance is data, F8).',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    if key == 'killed_line_length_artifact' and margins.get(
            'VMS_currier_B', 0) >= p['kill_margin'] > margins.get(
            'VMS_currier_A', 0):
        md.append('')
        md.append('Observation for the record (NO claim, not adjudicated '
                  f'here): Currier B alone clears the margin '
                  f'({margins["VMS_currier_B"]:+.4f}) while A shows none '
                  f'({margins["VMS_currier_A"]:+.4f}) — consistent with '
                  'the "B is the more systematized register" thread. A '
                  'per-hand adjudication would need its own '
                  'pre-registration in a future rung.')
    verdict = ('INSTRUMENT KILLED (S7 v1)' if key in
               ('instrument_gate_failed', 'killed_line_length_artifact')
               else 'S7 v1: ' + key.upper())
    summary = (f'{key}; P-REC {prec:+.3f}, VMS_full margin '
               f'{margins["VMS_full"]:+.4f} (need >= {p["kill_margin"]})')
    return {'verdict': verdict, 'suggestive': suggestive,
            'md': '\n'.join(md), 'summary': summary,
            'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N3b adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n3b(item, expected_params, run_started):
    """Pre-registered outcomes (line_as_record_per_hand.py docstring):
    gate = P-REC median >= gate_prec_min AND P1 median <= gate_p1_max;
    a hand PASSES iff it beats ALL its null medians AND its margin over
    the null median >= effect_floor. Outcomes: gate_failed /
    killed_split_luck / B_only / A_only / both. The runner re-derives
    everything and refuses on any mismatch with the script's record."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, r = data['params'], data['results']
    prec = r['PREC_records']['median_gain']
    p1 = r['P1_latin_plain']['median_gain']
    gate_ok = prec >= p['gate_prec_min'] and p1 <= p['gate_p1_max']
    passes = {}
    for hand in ('A', 'B'):
        row = r[f'VMS_currier_{hand}']
        ok = (row['beats_all_nulls']
              and row['margin_over_null_median'] >= p['effect_floor'])
        if ok != row['pass']:
            raise AdjudicationError(f'hand {hand}: runner derives '
                                    f'pass={ok}, script recorded '
                                    f'{row["pass"]}')
        passes[hand] = ok
    if not gate_ok:
        key = 'gate_failed'
    elif not passes['A'] and not passes['B']:
        key = 'killed_split_luck'
    elif passes['B'] and not passes['A']:
        key = 'B_only'
    elif passes['A'] and not passes['B']:
        key = 'A_only'
    else:
        key = 'both'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key in ('B_only', 'A_only', 'both')

    md = []
    md.append('**Pre-registered outcomes** (line_as_record_per_hand.py '
              'docstring, full post-hoc provenance disclosed there): a '
              'hand passes only if its 10-split median interior gain beats '
              f'ALL {p["n_nulls"]} of its own null-shuffle medians '
              f'(empirical p ~ {1/(p["n_nulls"]+1):.3f}) AND clears the '
              f'{p["effect_floor"]} bits/token effect floor over the null '
              'median — strictly harder than the rung-1 observation that '
              'motivated this rung.')
    md.append('')
    md.append('| corpus | median gain (bits/token) | null max | '
              'null median | margin | pass |')
    md.append('|---|---|---|---|---|---|')
    for cname in ('PREC_records', 'P1_latin_plain'):
        md.append(f'| {cname} | {r[cname]["median_gain"]:+.4f} | — | — | '
                  '— | gate |')
    for hand in ('A', 'B'):
        row = r[f'VMS_currier_{hand}']
        md.append(f'| VMS_currier_{hand} | {row["median_gain"]:+.4f} | '
                  f'{row["null_max"]:+.4f} | {row["null_median"]:+.4f} | '
                  f'{row["margin_over_null_median"]:+.4f} | '
                  f'{"**PASS**" if row["pass"] else "fail"} |')
    md.append('')
    md.append(f'Instrument gate: P-REC {prec:+.4f}, P1 {p1:+.4f} → '
              f'{"PASS" if gate_ok else "**FAIL**"}.')
    verdict_text = {
        'gate_failed': 'INSTRUMENT GATE FAILED — no interpretation.',
        'killed_split_luck':
            'KILLED (pre-registered): neither hand survives the per-hand '
            'null battery — the rung-1 Currier-B observation was split '
            'luck / baseline mismatch.',
        'B_only':
            'B ONLY — consistent with line-level field structure in '
            'Currier B (SUGGESTIVE, quarantined; the first registered '
            'test of the rung-1 observation). NOT a decode; no field is '
            'named or read.',
        'A_only':
            'A ONLY — contrary to the motivating pattern; SUGGESTIVE '
            'with extra suspicion (the motivating observation failed to '
            'replicate while its complement fired).',
        'both':
            'BOTH hands pass — consistent with per-hand field structure '
            '(SUGGESTIVE, quarantined). NOT a decode.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    verdict = ('S7 rung 2: ' + key.upper()) if suggestive else (
        'INSTRUMENT GATE FAILED (S7 rung 2)' if key == 'gate_failed'
        else 'KILLED (S7 rung 2, split luck)')
    b = r['VMS_currier_B']
    summary = (f'{key}; B margin {b["margin_over_null_median"]:+.4f} '
               f'(floor {p["effect_floor"]}), A margin '
               f'{r["VMS_currier_A"]["margin_over_null_median"]:+.4f}')
    return {'verdict': verdict, 'suggestive': suggestive,
            'md': '\n'.join(md), 'summary': summary,
            'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N2 adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n2(item, expected_params, run_started):
    """Pre-registered outcomes (cross_transliteration_invariance.py
    docstring): part-2 ladder = gate (ZL passes with reduced features),
    then robust / partial / artifact_suspect over the usable
    alternative transliterations; part 1 is a report-out of
    transliteration-sensitive fingerprint features. Re-derived from the
    JSON; refuses on mismatch."""
    import statistics as _st  # noqa: F401  (parity with sibling adjudicators)
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, part2 = data['params'], data['part2']

    def derived_pass(row):
        b = row['B']
        return (b['median_gain'] > b['null_max']
                and b['margin'] >= p['effect_floor'])

    for tag, row in part2.items():
        if row['usable'] and derived_pass(row) != row['B']['pass']:
            raise AdjudicationError(f'{tag}: runner derives '
                                    f'{derived_pass(row)}, script recorded '
                                    f'{row["B"]["pass"]}')
    zl_pass = part2['ZL'].get('B', {}).get('pass', False)
    alts = {t: r for t, r in part2.items() if t != 'ZL' and r['usable']}
    alt_pass = sorted(t for t, r in alts.items() if r['B']['pass'])
    alt_fail = sorted(t for t, r in alts.items() if not r['B']['pass'])
    if not zl_pass:
        key = 'gate_failed'
    elif alts and not alt_fail:
        key = 'robust'
    elif alt_pass:
        key = 'partial'
    else:
        key = 'artifact_suspect'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'robust'

    md = []
    md.append('**Pre-registered outcomes** (script docstring): gate = ZL '
              'passes the S7-B ordinal battery with alphabet-agnostic '
              'features; then robust / partial / artifact_suspect over '
              'usable alternatives (usable = >= '
              f'{p["min_b_lines"]} B-lines). Part 1 flags fingerprint '
              f'features deviating > {p["rel_dev_flag"]:.0%} from ZL.')
    md.append('')
    md.append('| transliteration | B-lines | median gain | null max | '
              'margin | battery |')
    md.append('|---|---|---|---|---|---|')
    for tag, row in part2.items():
        if row['usable']:
            b = row['B']
            md.append(f'| {tag} | {row["n_B_lines"]} | '
                      f'{b["median_gain"]:+.4f} | {b["null_max"]:+.4f} | '
                      f'{b["margin"]:+.4f} | '
                      f'{"**PASS**" if b["pass"] else "fail"} |')
        else:
            md.append(f'| {tag} | {row["n_B_lines"]} | — | — | — | '
                      'unusable |')
    flagged = {k: v['flagged'] for k, v in data['sensitivity'].items()
               if v['flagged']}
    md.append('')
    md.append(f'Part 1: flagged transliteration-sensitive features: '
              f'{flagged if flagged else "none"}.')
    verdict_text = {
        'gate_failed':
            'GATE FAILED — ZL does not pass with reduced features; the '
            'gallows feature was load-bearing; audit inconclusive.',
        'robust':
            'ROBUST — the S7-B ordinal signal passes in every usable '
            'alternative reading; one named objection to the quarantined '
            'rung-3 finding is removed (the finding itself remains '
            'SUGGESTIVE and quarantined).',
        'partial':
            'PARTIAL — the signal passes in some readings and misses in '
            'others; sensitive to reading choices. Investigation required '
            'before any promotion of the rung-3 finding.',
        'artifact_suspect':
            'ARTIFACT-SUSPECT — ZL passes but every usable alternative '
            'fails: the rung-3 finding is DEMOTED to artifact-suspect.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    if key == 'partial':
        md.append('')
        md.append('Observation for the investigation (no claim): every '
                  'usable transliteration beats ALL its nulls (empirical '
                  'p bar 5/5); the misses are effect-floor misses only — '
                  'whether a fixed bits/token floor mechanically penalizes '
                  'finer-grained alphabets (GC: 162 symbols, miss by '
                  '0.0013) is the registered question for the follow-up.')
    summary = (f'{key}; pass {["ZL"] + alt_pass}, fail {alt_fail}, '
               f'flagged features {sorted(flagged) if flagged else "none"}')
    return {'verdict': f'S9: {key.upper()}', 'suggestive': suggestive,
            'md': '\n'.join(md), 'summary': summary,
            'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N2b adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n2b(item, expected_params, run_started):
    """Pre-registered outcomes (transliteration_floor_calibration.py
    docstring): reference_flip / floor_artifact_robust / partial_stands
    over sensitivity-normalized floors (floor_R = floor_base x rho_R,
    rho measured from a planted sort implant, anchored at ZL,
    symmetric). Re-derived from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, rows = data['params'], data['rows']
    usable = {t: r for t, r in rows.items() if r.get('usable')}
    for t, r in usable.items():
        floor = round(p['floor_base'] * r['rho'], 4)
        if abs(floor - r['floor_normalized']) > 1e-9:
            raise AdjudicationError(f'{t}: floor mismatch')
        mine = r['beats_all'] and r['margin'] >= floor
        if mine != r['pass_normalized']:
            raise AdjudicationError(f'{t}: runner derives {mine}, script '
                                    f'recorded {r["pass_normalized"]}')
    zl_ok = usable['ZL']['pass_normalized']
    raised_flips = sorted(t for t, r in usable.items()
                          if r['pass_n2_fixed'] and not r['pass_normalized']
                          and r['floor_normalized'] > p['floor_base'])
    fails = sorted(t for t, r in usable.items()
                   if not r['pass_normalized'])
    if not zl_ok or raised_flips:
        key = 'reference_flip'
    elif not fails:
        key = 'floor_artifact_robust'
    else:
        key = 'partial_stands'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'floor_artifact_robust'

    md = []
    md.append('**Pre-registered outcomes** (script docstring; written '
              'with full disclosure AFTER N2\'s PARTIAL): floors scale by '
              'MEASURED sensitivity rho (planted sort implant, ZL anchor, '
              'symmetric — floors may rise), battery values inherited '
              'from N2\'s exact seed streams and cross-checked.')
    md.append('')
    md.append('| reading | margin | implant response | rho | normalized '
              'floor | verdict (was, fixed 0.05) |')
    md.append('|---|---|---|---|---|---|')
    for t, r in rows.items():
        if not r.get('usable'):
            md.append(f'| {t} | — | — | — | — | unusable |')
            continue
        md.append(f'| {t} | {r["margin"]:+.4f} | '
                  f'{r["implant_response"]:+.4f} | {r["rho"]:.4f} | '
                  f'{r["floor_normalized"]:.4f} | '
                  f'{"PASS" if r["pass_normalized"] else "fail"} '
                  f'({"PASS" if r["pass_n2_fixed"] else "fail"}) |')
    verdict_text = {
        'reference_flip':
            'REFERENCE FLIP — symmetric normalization flipped a '
            'previously-passing reading by RAISING its floor: the '
            'normalized-floor instrument is not consistent enough to '
            're-adjudicate at these margins. No claim; N2 PARTIAL '
            'unchanged. The registered question IS answered: measured '
            'sensitivities refute the "finer alphabets are mechanically '
            'penalized" hypothesis (GC rho > 1).',
        'floor_artifact_robust':
            'FLOOR ARTIFACT CONFIRMED — S9 upgrades to ROBUST (removes '
            'one named objection to the quarantined rung-3 finding; '
            'upgrades nothing else).',
        'partial_stands':
            'PARTIAL STANDS — sensitivity does not explain the misses; '
            'N2\'s verdict is unchanged, now on content grounds.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; rho: ' + ', '.join(
        f'{t} {r["rho"]:.2f}' for t, r in usable.items()))
    return {'verdict': f'S9 follow-up: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N2c adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n2c(item, expected_params, run_started):
    """Pre-registered outcomes (transliteration_significance.py
    docstring; criteria change — significance-only, 200 nulls, no
    effect floor — human-approved 2026-07-18): per reading PASS iff the
    real median gain beats ALL n_nulls null medians (p = 1/(n+1) <
    0.005). Ladder: reference_not_significant / robust_significance /
    partial_significance / artifact_suspect_significance. Re-derived
    from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, rows = data['params'], data['rows']
    usable = {t: r for t, r in rows.items() if r.get('usable')}
    for t, r in usable.items():
        mine = r['n_nulls_ge_real'] == 0
        if mine != r['pass']:
            raise AdjudicationError(f'{t}: runner derives {mine}, script '
                                    f'recorded {r["pass"]}')
        if r['pass'] and r['median_gain'] <= r['null_max']:
            raise AdjudicationError(f'{t}: pass recorded but real <= '
                                    'null max')
    zl_ok = usable['ZL']['pass']
    alts = {t: r for t, r in usable.items() if t != 'ZL'}
    alt_pass = sorted(t for t, r in alts.items() if r['pass'])
    alt_fail = sorted(t for t, r in alts.items() if not r['pass'])
    if not zl_ok:
        key = 'reference_not_significant'
    elif alts and not alt_fail:
        key = 'robust_significance'
    elif alt_pass:
        key = 'partial_significance'
    else:
        key = 'artifact_suspect_significance'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'robust_significance'

    md = []
    md.append('**Pre-registered criterion** (script docstring; '
              'significance-only criteria change human-approved '
              '2026-07-18): per reading, PASS iff the real 10-split '
              f'median interior gain beats ALL {p["n_nulls"]} '
              'within-line-shuffle null medians — empirical p = '
              f'{1 / (p["n_nulls"] + 1):.4f}. No effect floor; margins '
              'are observational. Null stream is a strict superset of '
              'N2\'s (first 20 identical, cross-checked), splits '
              'identical to N2 (cross-checked).')
    md.append('')
    md.append('| reading | B-lines | real gain | null max (of '
              f'{p["n_nulls"]}) | nulls ≥ real | p | verdict |')
    md.append('|---|---|---|---|---|---|---|')
    for t, r in rows.items():
        if not r.get('usable'):
            md.append(f'| {t} | {r["n_B_lines"]} | — | — | — | — | '
                      'unusable |')
            continue
        md.append(f'| {t} | {r["n_B_lines"]} | {r["median_gain"]:+.4f} | '
                  f'{r["null_max"]:+.4f} | {r["n_nulls_ge_real"]} | '
                  f'{r["p_empirical"]:.4f} | '
                  f'{"**PASS**" if r["pass"] else "fail"} |')
    verdict_text = {
        'reference_not_significant':
            'REFERENCE NOT SIGNIFICANT — ZL fails at p < 0.005 with '
            'reduced features; the cross-reading support argument '
            'collapses. No claim about alternates.',
        'robust_significance':
            'ROBUST AT SIGNIFICANCE — the S7-B ordinal signal is '
            'significant at p < 0.005 in every usable independent '
            'reading. The cross-reading objection to the quarantined '
            'rung-3 finding is resolved in favor of robustness. The '
            'finding remains SUGGESTIVE, quarantined, and is not a '
            'decode.',
        'partial_significance':
            'PARTIAL AT SIGNIFICANCE — the PARTIAL verdict stands at '
            'significance level; failing readings named above.',
        'artifact_suspect_significance':
            'ARTIFACT-SUSPECT — significant only in ZL; demoted until '
            'shown otherwise.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; ' + ', '.join(
        f'{t} p={r["p_empirical"]:.3f}' for t, r in usable.items()))
    return {'verdict': f'S9 significance: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N3c adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n3c(item, expected_params, run_started):
    """Pre-registered ladder (line_as_record_ordinal.py docstring),
    Currier B only (A observational): T1 total vs folio-nulls, T2 total
    vs line-nulls (floor effect_floor), T3 glyph component vs
    line-nulls (floor glyph_floor); each = beats ALL nulls AND margin
    over the null median >= floor. Outcome keys per the docstring. The
    runner re-derives every test from the stored null arrays and
    refuses on any mismatch with the script's record."""
    import statistics as _st
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, r = data['params'], data['results']
    gate_ok = (r['PREC_records']['total'] >= p['gate_prec_min']
               and r['P1_latin_plain']['total'] <= p['gate_p1_max'])

    def rederive(row, nulls_key, component, floor):
        vals = row[nulls_key][component]
        real = row['real'][component]
        return (real > max(vals)
                and real - _st.median(vals) >= floor)

    b = r['VMS_currier_B']
    t1 = rederive(b, 'folio_nulls', 'total', p['effect_floor'])
    t2 = rederive(b, 'line_nulls', 'total', p['effect_floor'])
    t3 = rederive(b, 'line_nulls', 'glyph', p['glyph_floor'])
    for name, mine, stored in (('t1', t1, b['t1_composition']['pass']),
                               ('t2', t2, b['t2_ordinal']['pass']),
                               ('t3', t3, b['t3_glyph']['pass'])):
        if mine != stored:
            raise AdjudicationError(f'{name}: runner derives {mine}, '
                                    f'script recorded {stored}')
    if not gate_ok:
        key = 'gate_failed'
    elif not t1 and not t2:
        key = 'compositional_artifact'
    elif not t1 and t2:
        key = 'inconsistent_nulls'
    elif t1 and not t2:
        key = 'line_composition_not_order'
    elif not t3:
        key = 'length_ordering_only'
    else:
        key = 'ordinal_glyph_structure'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key in ('ordinal_glyph_structure',
                         'line_composition_not_order')

    md = []
    md.append('**Pre-registered ladder** (line_as_record_ordinal.py '
              'docstring; Currier B adjudicated, A observational): T1 '
              'composition (folio-nulls), T2 ordinal (line-nulls), T3 '
              'glyph-only (line-nulls); each = beat ALL '
              f'{p["n_nulls"]} nulls AND clear the floor '
              f'({p["effect_floor"]} total / {p["glyph_floor"]} glyph). '
              'P-JUST (width-broken Latin) is the justification '
              'reference, not a gate.')
    md.append('')
    md.append('| corpus | total (bits/token) | glyph | len |')
    md.append('|---|---|---|---|')
    for cname in ('PREC_records', 'P1_latin_plain', 'PJUST_justified'):
        row = r[cname]
        md.append(f'| {cname} | {row["total"]:+.4f} | {row["glyph"]:+.4f} '
                  f'| {row["len"]:+.4f} |')
    for hand in ('A', 'B'):
        row = r[f'VMS_currier_{hand}']['real']
        md.append(f'| VMS_currier_{hand} | {row["total"]:+.4f} | '
                  f'{row["glyph"]:+.4f} | {row["len"]:+.4f} |')
    md.append('')
    md.append('| B test | margin | null max | verdict |')
    md.append('|---|---|---|---|')
    for tname, t in (('T1 composition', b['t1_composition']),
                     ('T2 ordinal', b['t2_ordinal']),
                     ('T3 glyph-only', b['t3_glyph'])):
        md.append(f'| {tname} | {t["margin"]:+.4f} | {t["null_max"]:+.4f} '
                  f'| {"**PASS**" if t["pass"] else "fail"} |')
    verdict_text = {
        'gate_failed': 'INSTRUMENT GATE FAILED — no interpretation.',
        'compositional_artifact':
            'KILLED: the rung-2 signal was composition, not order.',
        'inconsistent_nulls':
            'INCONSISTENT NULLS — no claim; instrument investigation '
            'required.',
        'line_composition_not_order':
            'LINE COMPOSITION, NOT ORDER — word-to-line assignment '
            'non-random, intra-line order adds nothing (read against '
            'P-JUST). SUGGESTIVE (weak), quarantined.',
        'length_ordering_only':
            'LENGTH ORDERING ONLY — consistent with scribal space '
            'management (LAAFU/Stolfi); the field reading is killed.',
        'ordinal_glyph_structure':
            'ORDINAL GLYPH STRUCTURE — Currier B\'s intra-line word '
            'order carries glyph-identity signal beyond composition and '
            'beyond length-based space management: consistent with '
            'field-like vocabulary ordering. SUGGESTIVE, quarantined, '
            'NOT a decode; no field is named or read.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    a = r['VMS_currier_A']
    md.append('')
    md.append(f'Observation (A, not adjudicated): total '
              f'{a["real"]["total"]:+.4f} (glyph {a["real"]["glyph"]:+.4f}) '
              '— same glyph-dominated shape at ~1/5 the strength, above '
              'all its nulls but under the floors: the hand gradient '
              'persists at rung 3.')
    verdict = ('S7 rung 3: ' + key.upper()) if suggestive else (
        'INSTRUMENT GATE FAILED (S7 rung 3)' if key == 'gate_failed'
        else f'S7 rung 3: {key.upper()}')
    summary = (f'{key}; B t1 {b["t1_composition"]["margin"]:+.4f} '
               f't2 {b["t2_ordinal"]["margin"]:+.4f} '
               f't3 {b["t3_glyph"]["margin"]:+.4f}; '
               f'P-JUST ref {r["PJUST_justified"]["total"]:+.4f} '
               '(len-dominated)')
    return {'verdict': verdict, 'suggestive': suggestive,
            'md': '\n'.join(md), 'summary': summary,
            'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N3d adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n3d(item, expected_params, run_started):
    """Pre-registered outcomes (line_as_record_characterization.py
    docstring): gate = rung-3 headline reproduced exactly; T-PARA
    (adjudicated) = paragraph-initial lines excluded, PASS iff real
    beats ALL n_nulls_para nulls (p < 0.005); decomposition is
    descriptive only. Outcomes: characterized / paragraph_confound.
    Re-derived from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p = data['params']
    if not data.get('headline', {}).get('verified'):
        raise AdjudicationError('rung-3 headline was not verified')
    t = data['t_para']
    mine = t['n_nulls_ge_real'] == 0
    if mine != t['pass']:
        raise AdjudicationError(f'T-PARA: runner derives {mine}, script '
                                f'recorded {t["pass"]}')
    key = 'characterized' if t['pass'] else 'paragraph_confound'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'characterized'

    d = data['decomposition']
    md = []
    md.append('**Pre-registered structure** (script docstring): gate = '
              'rung-3 headline reproduced (verified); T-PARA = '
              'paragraph-initial lines excluded, significance-only '
              f'battery ({p["n_nulls_para"]} nulls, p < '
              f'{1 / (p["n_nulls_para"] + 1):.4f}); decomposition is '
              'descriptive only and adjudicates nothing.')
    md.append('')
    md.append(f'T-PARA: {t["n_lines_excluded"]} paragraph-initial lines '
              f'excluded → {t["n_lines_kept"]} kept; real '
              f'{t["median_gain"]:+.4f} vs null max {t["null_max"]:+.4f} '
              f'(nulls ≥ real: {t["n_nulls_ge_real"]}, p = '
              f'{t["p_empirical"]:.4f}) → '
              f'{"**PASS**" if t["pass"] else "**fail**"}.')
    md.append('')
    md.append('| interior bin | gain (bits/token) |')
    md.append('|---|---|')
    for b, v in d['per_bin'].items():
        md.append(f'| {b} | {v:+.4f} |')
    md.append('')
    md.append('| feature | gain |')
    md.append('|---|---|')
    for f, v in d['per_feature'].items():
        md.append(f'| {f} | {v:+.4f} |')
    for f in ('first', 'last'):
        md.append('')
        md.append(f'| {f} glyph | support | contribution | skew m1/m2/m3 |')
        md.append('|---|---|---|---|')
        for r in d['categories'][f]:
            sk = r['bin_skew']
            md.append(f'| {r["value"]} | {r["support"]} | '
                      f'{r["contribution"]:+.4f} | {sk["m1"]}/{sk["m2"]}/'
                      f'{sk["m3"]} |')
    verdict_text = {
        'characterized':
            'CHARACTERIZED — the signal survives the paragraph control '
            '(the last registered structural threat); the tables above '
            'are the program\'s description of the Currier-B ordinal '
            'signal. SUGGESTIVE supporting detail for the quarantined '
            'finding; NOT a decode; no value is a translation.',
        'paragraph_confound':
            'PARAGRAPH CONFOUND — the signal is carried by '
            'paragraph-initial lines; the rung-3 finding is DEMOTED and '
            'the decomposition is not interpreted.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; T-PARA p={t["p_empirical"]:.4f}, bins '
               + '/'.join(f'{v:+.3f}' for v in d['per_bin'].values())
               + ', top first-glyph '
               + (d['categories']['first'][0]['value']
                  if d['categories']['first'] else '—'))
    return {'verdict': f'S7 rung 4: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N3e adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n3e(item, expected_params, run_started):
    """Pre-registered outcomes (line_as_record_section_split.py
    docstring): gate = pooled rung-3 headline reproduced; per usable
    section (bio / recipes / other_B), PASS iff the real median beats
    ALL n_nulls within-line-shuffle nulls (p < 0.005). Outcomes:
    section_general / section_specific / pooling_artifact. Re-derived
    from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, rows = data['params'], data['rows']
    if not data.get('headline', {}).get('verified'):
        raise AdjudicationError('pooled rung-3 headline was not verified')
    usable = {s: r for s, r in rows.items() if r.get('usable')}
    for s, r in usable.items():
        mine = r['n_nulls_ge_real'] == 0
        if mine != r['pass']:
            raise AdjudicationError(f'{s}: runner derives {mine}, script '
                                    f'recorded {r["pass"]}')
    passed = sorted(s for s, r in usable.items() if r['pass'])
    failed = sorted(s for s, r in usable.items() if not r['pass'])
    if usable and not failed:
        key = 'section_general'
    elif passed:
        key = 'section_specific'
    else:
        key = 'pooling_artifact'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key in ('section_general', 'section_specific')

    md = []
    md.append('**Pre-registered outcomes** (script docstring; '
              'human-directed section-confound test): per usable section '
              f'PASS iff the real median beats ALL {p["n_nulls"]} '
              'within-line-shuffle nulls (p < '
              f'{1 / (p["n_nulls"] + 1):.4f}); taxonomy: '
              f'{p["taxonomy"]}. Pooled rung-3 headline reproduced '
              '(gate).')
    md.append('')
    md.append('| section | lines / folios | real gain | null max | '
              'nulls ≥ real | p | verdict |')
    md.append('|---|---|---|---|---|---|---|')
    for s, r in rows.items():
        if not r.get('usable'):
            md.append(f'| {s} | {r["n_lines"]} | — | — | — | — | '
                      'unusable |')
            continue
        md.append(f'| {s} | {r["n_lines"]} / {r["n_folios"]} | '
                  f'{r["median_gain"]:+.4f} | {r["null_max"]:+.4f} | '
                  f'{r["n_nulls_ge_real"]} | {r["p_empirical"]:.4f} | '
                  f'{"**PASS**" if r["pass"] else "fail"} |')
    verdict_text = {
        'section_general':
            'SECTION-GENERAL — the ordinal signal replicates within '
            'every usable B section independently; the section-confound '
            'objection is dismissed. SUGGESTIVE supporting detail for '
            'the quarantined finding; not a decode.',
        'section_specific':
            f'SECTION-SPECIFIC — replicates in {passed}, fails in '
            f'{failed}; the finding\'s scope narrows to the passing '
            'sections. SUGGESTIVE (scoped), quarantined.',
        'pooling_artifact':
            'POOLING ARTIFACT / UNRESOLVED — no section replicates the '
            'signal alone; the rung-3 finding is demoted to unresolved '
            'and promotion is blocked.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; ' + ', '.join(
        f'{s} p={r["p_empirical"]:.3f}'
        + (f' (margin {r["margin_observational"]:+.4f})')
        for s, r in usable.items()))
    return {'verdict': f'S7 rung 5: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N4 adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n4(item, expected_params, run_started):
    """Pre-registered rule (line_class_family_test.py docstring): gate =
    family centroids separate (min pairwise dist > gate_sep x max split
    RMS); B assigned to nearest family centroid only if d1 <
    margin_ratio x d2, else none_of_the_above (F4 arm). Re-derived from
    the JSON; refuses on mismatch."""
    import math as _m
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, prof = data['params'], data['profiles']
    cent = {'family_language': 'P1_language',
            'family_records': 'PREC_records',
            'family_positional': 'PNUM_positional',
            'family_hoax': 'N4_hoax'}

    def dist(a, b):
        return _m.sqrt((prof[a]['r_pos'] - prof[b]['r_pos']) ** 2
                       + (prof[a]['r_bi'] - prof[b]['r_bi']) ** 2)

    names = list(cent.values())
    min_sep = min(dist(a, b) for i, a in enumerate(names)
                  for b in names[i + 1:])
    max_rms = max(prof[v]['split_rms'] for v in names)
    gate_ok = min_sep > p['gate_sep'] * max_rms
    if gate_ok != data['gate']['pass']:
        raise AdjudicationError('gate re-derivation mismatch')
    dists = sorted((dist('VMS_currier_B', v), k) for k, v in cent.items())
    d1, fam1 = dists[0]
    d2, fam2 = dists[1]
    if not gate_ok:
        key = 'gate_failed'
    elif d1 < p['margin_ratio'] * d2:
        key = fam1
    else:
        key = 'none_of_the_above'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key.startswith('family_')

    md = []
    md.append('**Pre-registered rule** (script docstring): nearest family '
              f'centroid with margin (d1 < {p["margin_ratio"]} x d2) and '
              'an explicit none-of-the-above arm (F4); gate = centroids '
              f'separate (> {p["gate_sep"]} x max split RMS). Profiles = '
              'normalized position-driven vs neighbor-driven class-'
              'sequence information, folio holdout, 10-split medians.')
    md.append('')
    md.append('| corpus | r_pos | r_bi | split RMS | lines |')
    md.append('|---|---|---|---|---|')
    for name, row in prof.items():
        md.append(f'| {name} | {row["r_pos"]:+.4f} | {row["r_bi"]:+.4f} | '
                  f'{row["split_rms"]:.4f} | {row["n_lines"]} |')
    md.append('')
    md.append(f'Gate: min centroid separation {min_sep:.4f} vs required '
              f'{p["gate_sep"] * max_rms:.4f} → '
              f'{"PASS" if gate_ok else "**FAIL**"}. B distances: '
              + ', '.join(f'{k} {d:.4f}' for d, k in dists) + '.')
    md.append('')
    if key.startswith('family_'):
        md.append(f'**VERDICT: {key.upper()}** — B\'s line-class ordering '
                  f'profile is nearest the {key[7:]} reference with clear '
                  'margin. A family-level reading only: nothing is '
                  'decoded, and the S7 positional finding stands as the '
                  'residual that separates B from the pure family '
                  'centroid (real prose shows r_pos ~ 0; B does not).')
    elif key == 'none_of_the_above':
        md.append('**VERDICT: NONE OF THE ABOVE** — B matches no '
                  'calibrated family clearly (the F4 arm).')
    else:
        md.append('**VERDICT: GATE FAILED** — no reading.')
    summary = (f'{key}; B (r_pos {prof["VMS_currier_B"]["r_pos"]:+.4f}, '
               f'r_bi {prof["VMS_currier_B"]["r_bi"]:+.4f}), nearest '
               f'{fam1} d={d1:.4f}, second {fam2} d={d2:.4f}')
    return {'verdict': f'S5/S6 family test: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N5 adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n5(item, expected_params, run_started):
    """Pre-registered ladder (line_ordinal_rank_test.py docstring):
    gate = P-REC rejects (p < p_replicate) AND P1/N1 in the null band
    (p >= p_nullband); B replicated / ambiguous / not_replicated
    (design-artifact-suspect). Re-derived from the JSON; refuses on
    mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, rows = data['params'], data['rows']
    for name, r in rows.items():
        derived = round((1 + r['n_perm_ge']) / (p['n_perm'] + 1), 4)
        if abs(derived - r['p']) > 1e-9:
            raise AdjudicationError(f'{name}: p re-derivation mismatch')
    gate_ok = (rows['PREC_records']['p'] < p['p_replicate']
               and rows['P1_latin']['p'] >= p['p_nullband']
               and rows['N1_shuffle']['p'] >= p['p_nullband'])
    pb = rows['VMS_currier_B']['p']
    if not gate_ok:
        key = 'gate_failed'
    elif pb < p['p_replicate']:
        key = 'replicated'
    elif pb < p['p_nullband']:
        key = 'ambiguous'
    else:
        key = 'not_replicated'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'replicated'

    md = []
    md.append('**Pre-registered ladder** (script docstring; answers '
              'PHASE8_DRAFT §8.7-1 at IMPLEMENTATION level — same-author '
              'caveat disclosed): rank statistic T = weighted '
              'between-class variance of mean interior rank, first-EVA-'
              'glyph classes, no bins / smoothing / holdout; inference '
              f'by {p["n_perm"]} within-line permutations.')
    md.append('')
    md.append('| corpus | T | perms ≥ T | p | lines |')
    md.append('|---|---|---|---|---|')
    for name, r in rows.items():
        md.append(f'| {name} | {r["T"]:.6f} | {r["n_perm_ge"]} | '
                  f'{r["p"]:.4f} | {r["n_lines"]} |')
    verdict_text = {
        'gate_failed': 'GATE FAILED — no reading.',
        'replicated':
            'REPLICATED — the intra-line class-ordering signal survives '
            'a methodologically disjoint instrument (B p < 0.005; and '
            'observationally, hand A also rejects under this more '
            'sensitive statistic). The shared-implementation-DNA '
            'objection is answered; author-level independence remains '
            'open and travels with the finding.',
        'ambiguous': 'AMBIGUOUS — no claim; a third design is required.',
        'not_replicated':
            'NOT REPLICATED — the v1 finding is flagged '
            'DESIGN-ARTIFACT-SUSPECT pending third-party '
            'implementation.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    if key == 'replicated':
        bm = rows['VMS_currier_B']['class_means']
        ordered = sorted(bm.items(), key=lambda kv: kv[1])
        md.append('')
        md.append('B class mean interior ranks (early → late): '
                  + ', '.join(f'{c} {u:.3f}' for c, u in ordered)
                  + ' — coherent with the rung-4 characterization '
                  '(q-early), and the EVA-parsed sh class emerges as the '
                  'earliest carrier.')
    summary = (f'{key}; B p={pb:.4f}, A p='
               f'{rows["VMS_currier_A"]["p"]:.4f}, PREC p='
               f'{rows["PREC_records"]["p"]:.4f}')
    return {'verdict': f'S7-R re-implementation: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N6 adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n6(item, expected_params, run_started):
    """Pre-registered outcomes (line_discipline_tournament.py
    docstring): gate = G0 ablation FAILS the line group (D_line > bar);
    then G1 vs the phase-109 contiguous-halves bars: closes neither /
    line only / both -> discipline_insufficient / partial_forgery_bind
    / line_texture_reducible. Re-derived from the JSON; refuses on
    mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    r = data['results']
    bar_line, bar_unfit = r['bar']['line'], r['bar']['unfitted']
    g0 = r['G0_ablation']['dist']
    g1 = r['G1_discipline']['dist']
    g0_fails = g0['line'] > bar_line
    g1_line = g1['line'] <= bar_line
    g1_unfit = g1['unfitted'] <= bar_unfit
    if not g0_fails:
        key = 'gate_failed'
    elif not g1_line:
        key = 'discipline_insufficient'
    elif not g1_unfit:
        key = 'partial_forgery_bind'
    else:
        key = 'line_texture_reducible'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'line_texture_reducible'

    md = []
    md.append('**Pre-registered outcomes** (script docstring; a '
              'DIAGNOSTIC REDUCTION TEST, not a blind generator — the '
              'class-position table is measured from B, plus ONE '
              f'strength knob fitted on one feature, frozen at '
              f'LAMBDA={data["results"]["lambda"]}). Bars are the '
              'phase-109 contiguous-halves convention.')
    md.append('')
    md.append('| entrant | D_line (bar '
              f'{bar_line}) | D_unfitted (bar {bar_unfit}) |')
    md.append('|---|---|---|')
    for name in ('G0_ablation', 'G1_discipline', 'G2_verbose_ref'):
        d = r[name]['dist']
        md.append(f'| {name} | {d["line"]} | {d["unfitted"]} |')
    md.append('')
    md.append('| feature | B | G0 | G1 |')
    md.append('|---|---|---|---|')
    for k in (data['params']['line_group']
              + data['params']['unfitted_group']):
        md.append(f'| {k} | {r["B"][k]} | '
                  f'{r["G0_ablation"]["features"][k]} | '
                  f'{r["G1_discipline"]["features"][k]} |')
    verdict_text = {
        'gate_failed':
            'GATE FAILED — the ablation already closes the line group; '
            'no reading.',
        'discipline_insufficient':
            'DISCIPLINE INSUFFICIENT — the moat is not reducible to '
            'lexicon + table + knob at this budget; corpse logged with '
            'coordinates.',
        'partial_forgery_bind':
            'PARTIAL FORGERY (BIND) — the line group closes but the '
            'unfitted order-texture breaks; a new bind theorem.',
        'line_texture_reducible':
            'LINE TEXTURE REDUCIBLE — Currier B\'s full line texture '
            '(edge effects AND interior ordinal residue) is '
            'statistically forgeable from its lexicon plus one measured '
            'class-position table and one strength knob, without '
            'breaking the unfitted order-sensitive features. '
            'SUGGESTIVE, quarantined. Scope: a mechanism-family claim '
            'about statistics — the phase-109 moat is reduced, not '
            'decoded; blind generation of the table is the registered '
            'future rung.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; G1 D_line {g1["line"]} (bar {bar_line}), '
               f'D_unfit {g1["unfitted"]} (bar {bar_unfit}), '
               f'lambda {data["results"]["lambda"]}')
    return {'verdict': f'S3 rung 2: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': data['params'],
            'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N6b adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n6b(item, expected_params, run_started):
    """Pre-registered outcomes (line_discipline_compression.py
    docstring): G1b (rank-1 table) vs the N6 bars (cross-checked in the
    script): not_compressible / partial_bind / one_axis_sufficient.
    Re-derived from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    r = data['results']
    d = r['G1b']['dist']
    line_ok = d['line'] <= r['bar']['line']
    unfit_ok = d['unfitted'] <= r['bar']['unfitted']
    if not line_ok:
        key = 'not_compressible'
    elif not unfit_ok:
        key = 'partial_bind'
    else:
        key = 'one_axis_sufficient'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'one_axis_sufficient'

    md = []
    md.append('**Pre-registered outcomes** (script docstring): rank-1 '
              'SVD compression of the N6 discipline table (deterministic, '
              'no search), same bars and machinery as N6 (all '
              'cross-checked at runtime), one re-fitted knob '
              f'(LAMBDA={r["lambda"]}). Rank-1 variance share: '
              f'{r["var_share"]:.1%}.')
    md.append('')
    md.append(f'| entrant | D_line (bar {r["bar"]["line"]}) | '
              f'D_unfitted (bar {r["bar"]["unfitted"]}) |')
    md.append('|---|---|---|')
    md.append(f'| G1 full table (N6) | {r["n6_g1_dist"]["line"]} | '
              f'{r["n6_g1_dist"]["unfitted"]} |')
    md.append(f'| G1b rank-1 table | {d["line"]} | {d["unfitted"]} |')
    md.append('')
    md.append('Class axis A (low → high): '
              + ', '.join(f'{c} {a:+.3f}' for c, a in
                          sorted(r['axis'].items(),
                                 key=lambda kv: kv[1])) + '.')
    md.append('Position profile V: '
              + ', '.join(f'{b} {v:+.3f}'
                          for b, v in r['profile'].items()) + '.')
    md.append('Observational axis correlations (declared predictors): '
              + ', '.join(f'{k} {v:+.3f}'
                          for k, v in r['axis_correlations'].items())
              + '.')
    verdict_text = {
        'not_compressible':
            'NOT COMPRESSIBLE — one latent axis does not reproduce the '
            'line texture (the dominant axis is the EDGE/paragraph axis; '
            'the interior ordering is a second, independent dimension). '
            'The discipline is at least rank-2; corpse logged with '
            'coordinates.',
        'partial_bind':
            'PARTIAL (BIND) — line group closes under rank-1 but the '
            'unfitted order-texture breaks.',
        'one_axis_sufficient':
            'ONE AXIS SUFFICIENT — the discipline reduces to one class '
            'score axis, one position profile, and one knob. '
            'SUGGESTIVE, quarantined; not a decode.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; G1b D_line {d["line"]} vs bar '
               f'{r["bar"]["line"]} (full table {r["n6_g1_dist"]["line"]}), '
               f'var_share {r["var_share"]:.1%}')
    return {'verdict': f'S3 rung 2b: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': data['params'],
            'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N6c adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n6c(item, expected_params, run_started):
    """Pre-registered outcomes (line_discipline_rank2.py docstring):
    G1c (rank-2 table) vs the N6 bars (cross-checked in the script):
    still_not_compressible / partial_bind / two_axes_sufficient.
    Re-derived from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    r = data['results']
    d = r['G1c']['dist']
    line_ok = d['line'] <= r['bar']['line']
    unfit_ok = d['unfitted'] <= r['bar']['unfitted']
    if not line_ok:
        key = 'still_not_compressible'
    elif not unfit_ok:
        key = 'partial_bind'
    else:
        key = 'two_axes_sufficient'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'two_axes_sufficient'

    md = []
    md.append('**Pre-registered outcomes** (script docstring): rank-2 SVD '
              'reconstruction (deterministic; declared sign convention), '
              'N6 machinery/bars cross-checked, one re-fitted knob '
              f'(LAMBDA={r["lambda"]}). Rank-2 variance share: '
              f'{r["var_share2"]:.1%}.')
    md.append('')
    md.append(f'| entrant | D_line (bar {r["bar"]["line"]}) | '
              f'D_unfitted (bar {r["bar"]["unfitted"]}) |')
    md.append('|---|---|---|')
    md.append(f'| G1 full table (N6) | {r["n6_g1_dist"]["line"]} | '
              f'{r["n6_g1_dist"]["unfitted"]} |')
    md.append(f'| G1b rank-1 (N6b) | {r["n6b_g1b_dist"]["line"]} | '
              f'{r["n6b_g1b_dist"]["unfitted"]} |')
    md.append(f'| G1c rank-2 | {d["line"]} | {d["unfitted"]} |')
    md.append('')
    md.append('Axis 2 (interior, low → high): '
              + ', '.join(f'{c} {a:+.3f}' for c, a in
                          sorted(r['axes']['axis2'].items(),
                                 key=lambda kv: kv[1])) + '.')
    md.append('Observational correlations: '
              + ', '.join(f'{k} {v:+.3f}'
                          for k, v in r['correlations'].items()) + '.')
    verdict_text = {
        'still_not_compressible':
            'STILL NOT COMPRESSIBLE — two axes (96.9% of the table) do '
            'not close the line group at the tournament bar; the '
            'discipline carries tournament-relevant structure beyond '
            'rank 2. Note the convergence ladder (rank-1 → rank-2 → '
            'full) and that axis 2 independently reproduces the N5 '
            'interior ordering (ρ = '
            f'{r["correlations"]["axis2_vs_n5_mean_ranks"]:+.2f}).',
        'partial_bind':
            'PARTIAL (BIND) — line group closes under rank-2 but the '
            'unfitted order-texture breaks.',
        'two_axes_sufficient':
            'TWO AXES SUFFICIENT — the discipline is exactly two '
            'interpretable axes plus one knob. SUGGESTIVE, quarantined; '
            'not a decode.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; G1c D_line {d["line"]} vs bar {r["bar"]["line"]} '
               f'(rank-1 {r["n6b_g1b_dist"]["line"]}, full '
               f'{r["n6_g1_dist"]["line"]}), var2 {r["var_share2"]:.1%}, '
               f'axis2~N5 ρ '
               f'{r["correlations"]["axis2_vs_n5_mean_ranks"]:+.2f}')
    return {'verdict': f'S3 rung 2c: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': data['params'],
            'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N6d adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n6d(item, expected_params, run_started):
    """Pre-registered outcomes (line_discipline_rank3.py docstring):
    G1d (rank-3 table) vs the N6 bars (cross-checked in the script):
    still_not_compressible / partial_bind / three_axes_sufficient.
    Re-derived from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    r = data['results']
    d = r['G1d']['dist']
    line_ok = d['line'] <= r['bar']['line']
    unfit_ok = d['unfitted'] <= r['bar']['unfitted']
    if not line_ok:
        key = 'still_not_compressible'
    elif not unfit_ok:
        key = 'partial_bind'
    else:
        key = 'three_axes_sufficient'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'three_axes_sufficient'

    md = []
    md.append('**Pre-registered outcomes** (script docstring): rank-3 SVD '
              'reconstruction, N6 machinery/bars cross-checked, one '
              f're-fitted knob (LAMBDA={r["lambda"]}). Rank-3 variance '
              f'share: {r["var_share3"]:.1%}.')
    md.append('')
    md.append(f'| entrant | D_line (bar {r["bar"]["line"]}) | '
              f'D_unfitted (bar {r["bar"]["unfitted"]}) |')
    md.append('|---|---|---|')
    md.append(f'| G1 full table (N6) | {r["n6_g1_dist"]["line"]} | '
              f'{r["n6_g1_dist"]["unfitted"]} |')
    md.append(f'| G1b rank-1 (N6b) | {r["n6b_g1b_dist"]["line"]} | '
              f'{r["n6b_g1b_dist"]["unfitted"]} |')
    md.append(f'| G1c rank-2 (N6c) | {r["n6c_g1c_dist"]["line"]} | '
              f'{r["n6c_g1c_dist"]["unfitted"]} |')
    md.append(f'| G1d rank-3 | {d["line"]} | {d["unfitted"]} |')
    md.append('')
    md.append('Axis 3 (pre-final zone, low → high): '
              + ', '.join(f'{c} {a:+.3f}' for c, a in
                          sorted(r['axes']['axis3'].items(),
                                 key=lambda kv: kv[1])) + '.')
    md.append('Profile 3: '
              + ', '.join(f'{b} {v:+.3f}'
                          for b, v in r['axes']['profile3'].items())
              + '.')
    md.append('Observational correlations: '
              + ', '.join(f'{k} {v:+.3f}'
                          for k, v in r['correlations'].items()) + '.')
    verdict_text = {
        'still_not_compressible':
            'STILL NOT COMPRESSIBLE — the discipline resists rank-3 '
            'compression; corpse logged.',
        'partial_bind':
            'PARTIAL (BIND) — line group closes under rank-3 but the '
            'unfitted order-texture breaks.',
        'three_axes_sufficient':
            'THREE AXES SUFFICIENT — Currier B\'s line discipline '
            'compresses to three interpretable axes plus one knob '
            '(~55 numbers vs the 91-cell table): the edge/paragraph '
            'axis, the interior early-late gradient (= the N5 residue, '
            'ρ +0.80), and a previously unnamed PRE-FINAL-ZONE axis '
            '(peaks m3/pL-1, not pL; uncorrelated with the declared '
            'predictors). SUGGESTIVE, quarantined; a compression of '
            'statistics, not a decode. Deriving each axis from '
            'independent principles is the registered blind-generation '
            'rung.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; G1d D_line {d["line"]} vs bar {r["bar"]["line"]} '
               f'(ladder: rank-1 {r["n6b_g1b_dist"]["line"]}, rank-2 '
               f'{r["n6c_g1c_dist"]["line"]}, full '
               f'{r["n6_g1_dist"]["line"]}), var3 {r["var_share3"]:.1%}')
    return {'verdict': f'S3 rung 2d: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': data['params'],
            'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N6e adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n6e(item, expected_params, run_started):
    """Pre-registered outcomes (line_discipline_transfer.py docstring):
    G1e (Currier-A-measured table placing B) vs the N6 bars
    (cross-checked in the script): not_transferable / partial_bind /
    discipline_transfers. Re-derived from the JSON; refuses on
    mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    r = data['results']
    d = r['G1e']['dist']
    line_ok = d['line'] <= r['bar']['line']
    unfit_ok = d['unfitted'] <= r['bar']['unfitted']
    if not line_ok:
        key = 'not_transferable'
    elif not unfit_ok:
        key = 'partial_bind'
    else:
        key = 'discipline_transfers'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'discipline_transfers'

    md = []
    md.append('**Pre-registered outcomes** (script docstring; blind WITH '
              'RESPECT TO B — the table is measured on Currier A only '
              f'({r["n_a_lines"]} lines), B contributes its lexicon and '
              f'the single knob, fitted LAMBDA={r["lambda"]} vs B\'s own '
              f'{r["lambda_b_own"]}).')
    md.append('')
    md.append(f'| entrant | D_line (bar {r["bar"]["line"]}) | '
              f'D_unfitted (bar {r["bar"]["unfitted"]}) |')
    md.append('|---|---|---|')
    md.append(f'| G1 B-table (N6) | {r["n6_g1_dist"]["line"]} | '
              f'{r["n6_g1_dist"]["unfitted"]} |')
    md.append(f'| G1e A-table | {d["line"]} | {d["unfitted"]} |')
    md.append('')
    md.append('Per-axis transfer (Spearman, A-table vs B-table rank-3 '
              'axes): '
              + ', '.join(f'{k} {v:+.3f}'
                          for k, v in r['axis_transfer'].items()) + '.')
    verdict_text = {
        'not_transferable':
            'NOT TRANSFERABLE — the A-measured table does not close B\'s '
            'line group at any knob setting. The per-axis profile '
            'localizes the failure: the edge axis (+0.92) and interior '
            'gradient (+0.83) ARE manuscript-wide (shared shape, '
            'strength-scaled — the switch picture holds for them); the '
            'pre-final-zone axis ANTI-transfers (−0.46) and is '
            'B-specific. The hand difference is intensity on two shared '
            'rules PLUS one qualitatively B-own rule. Corpse logged.',
        'partial_bind':
            'PARTIAL (BIND) — line group closes under the A-table but '
            'the unfitted order-texture breaks.',
        'discipline_transfers':
            'DISCIPLINE TRANSFERS — a table measured exclusively on '
            'Currier A closes B\'s full line texture; the discipline is '
            'a manuscript-wide system with a hand strength difference. '
            'SUGGESTIVE, quarantined; not a decode.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; G1e D_line {d["line"]} vs bar {r["bar"]["line"]} '
               f'(B-table {r["n6_g1_dist"]["line"]}); transfer axis1 '
               f'{r["axis_transfer"]["axis1"]:+.2f} axis2 '
               f'{r["axis_transfer"]["axis2"]:+.2f} axis3 '
               f'{r["axis_transfer"]["axis3"]:+.2f}; lambda '
               f'{r["lambda"]} vs {r["lambda_b_own"]}')
    return {'verdict': f'S3 rung 3: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': data['params'],
            'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N7 adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n7(item, expected_params, run_started):
    """Pre-registered outcomes (hapax_locus_readjudication.py
    docstring): gate = all-loci replication reproduces the committed
    language_vs_cipher golden; then Part D's own thresholds on the
    P-only corpus: verdict_survives / verdict_softened. Re-derived from
    the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    rows, p = data['rows'], data['params']
    a, po = rows['all'], rows['P_only']
    gate_ok = data['gate_ok'] and \
        abs(a['chi2'] - data['golden_ref']['chi2']) <= 0.1
    if not gate_ok:
        key = 'gate_failed'
    else:
        chi_ok = (po['chi_class'] == 'CONCENTRATED'
                  if a['chi_class'] == 'CONCENTRATED' else True)
        order = {'UNIFORM': 0, 'MILD': 1, 'CLUSTERED': 2}
        b_ok = order[po['b_class']] >= order[a['b_class']]
        key = 'verdict_survives' if (chi_ok and b_ok) else \
            'verdict_softened'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')

    md = []
    md.append('**Pre-registered outcomes** (script docstring): Part D of '
              'language_vs_cipher replicated faithfully (gate = golden '
              'reproduction) and re-adjudicated by its OWN original '
              f'thresholds (chi2 > {p["chi2_threshold"]}; B classes) on '
              'a paragraph-only corpus. Same rules, cleaned data.')
    md.append('')
    md.append('| policy | lines | tokens | hapaxes | chi2 (class) | '
              'B (class) |')
    md.append('|---|---|---|---|---|---|')
    for name, r in rows.items():
        md.append(f'| {name} | {r["n_lines"]} | {r["n_tokens"]} | '
                  f'{r["n_hapax"]} | {r["chi2"]} ({r["chi_class"]}) | '
                  f'{r["burstiness"]:+.3f} ({r["b_class"]}) |')
    verdict_text = {
        'gate_failed': 'GATE FAILED — replication does not reproduce '
                       'the committed golden; no reading.',
        'verdict_survives':
            'VERDICT SURVIVES — the hapax-clustering evidence is a '
            'property of the running text: decontamination removes '
            f'~{100 * (a["chi2"] - po["chi2"]) / a["chi2"]:.0f}% of the '
            'chi2 statistic (the measured layout-artifact share) but '
            'every original classification holds. The contamination '
            'asterisk on Part D is removed by test.',
        'verdict_softened':
            'VERDICT SOFTENED — decontamination breaks an original '
            'classification; Part D\'s language-favoring evidence was '
            'partly layout artifact and is demoted to conditional-on-'
            'corpus-scope.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; chi2 {a["chi2"]} -> {po["chi2"]} (threshold '
               f'{p["chi2_threshold"]}), B {a["burstiness"]:+.3f} -> '
               f'{po["burstiness"]:+.3f}')
    return {'verdict': f'N7 Part-D re-adjudication: {key.upper()}',
            'suggestive': False, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N6f adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n6f(item, expected_params, run_started):
    """Pre-registered outcomes (line_discipline_axis3_handA.py
    docstring): gates = B self-projection ~1 and axes-1/2 continuity;
    axis-3 verdict from the fixed-direction projection + null battery
    + bin-level sign agreement: axis3_absent_in_A /
    axis3_inverted_in_A / axis3_shared_weak / discordant_methods.
    Re-derived from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    r = data['results']
    gate_a = all(abs(x - 1.0) < 0.05 for x in r['beta_b_self'])
    sig = {int(k): v for k, v in r['significant'].items()}
    ba = r['beta_a']
    gate_b = sig[1] and sig[2] and ba[0] > 0 and ba[1] > 0
    b3, rho = ba[2], r['rho_bins']
    if not (gate_a and gate_b):
        key = 'gate_failed'
    elif not sig[3]:
        key = 'axis3_absent_in_A'
    elif b3 < 0 and rho < 0:
        key = 'axis3_inverted_in_A'
    elif b3 > 0 and rho > 0:
        key = 'axis3_shared_weak'
    else:
        key = 'discordant_methods'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key in ('axis3_inverted_in_A', 'axis3_shared_weak')

    md = []
    md.append('**Pre-registered outcomes** (script docstring): hand A\'s '
              'centered log-table projected onto B\'s FIXED N6d axes (no '
              'SVD on A — avoiding the component-mixing hazard behind '
              'N6e\'s −0.46), permutation null '
              f'({data["params"]["n_nulls"]} within-line shuffles), '
              'model-free bin-level sign cross-check.')
    md.append('')
    md.append('| axis | beta(A) | null max |beta| | significant |')
    md.append('|---|---|---|---|')
    for i in (1, 2, 3):
        md.append(f'| {i} | {ba[i - 1]:+.3f} | '
                  f'{r["null_max_abs"][str(i)]:.3f} | '
                  f'{"yes" if sig[i] else "no"} |')
    md.append('')
    md.append(f'Bin-level pre-final skew, A vs B: Spearman {rho:+.3f} '
              '(observational).')
    verdict_text = {
        'gate_failed': 'GATE FAILED — no reading.',
        'axis3_absent_in_A':
            'AXIS 3 ABSENT IN A — no measurable pre-final-zone rule at '
            'A\'s sample size (the axis-3 direction is intrinsically '
            'noisy: wide null band). The point observations lean weakly '
            'SAME-direction, so N6e\'s −0.46 is resolved as component-'
            'mixing artifact, not inversion. Axis 3 remains B\'s own as '
            'far as A\'s data can resolve; ledger entry 15\'s "anti-'
            'transfers" reading is refined to "undetectable in A".',
        'axis3_inverted_in_A':
            'AXIS 3 INVERTED IN A — a qualitative hand difference. '
            'SUGGESTIVE, quarantined.',
        'axis3_shared_weak':
            'AXIS 3 SHARED (WEAK) — N6e\'s −0.46 was component mixing; '
            'the rule is manuscript-wide after all. SUGGESTIVE, '
            'quarantined.',
        'discordant_methods':
            'DISCORDANT METHODS — no claim; investigation required.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; beta_3(A) {b3:+.3f} vs null max '
               f'{r["null_max_abs"]["3"]:.3f}; bins rho {rho:+.3f}; '
               f'continuity beta_1/2 {ba[0]:+.2f}/{ba[1]:+.2f}')
    return {'verdict': f'S3 rung 3b: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': data['params'],
            'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N8 adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n8(item, expected_params, run_started):
    """Pre-registered verdicts (scan_glyph_feasibility.py docstring):
    G1 binarization band/CV, G2 component-vs-char Spearman thresholds,
    G3 cluster-stability precursors -> feasible / partially_feasible /
    infeasible_at_this_quality. Re-derived from the JSON; refuses on
    mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, r = data['params'], data['results']
    g1 = r['ink']['pass']
    rho_all = r['g2']['rho_all']
    rho_text = r['g2']['rho_textonly']
    g3a, g3b = r['g3']['g3a'], r['g3']['g3b']
    if g1 and rho_all >= p['g2_strong'] and g3a and g3b:
        key = 'feasible'
    elif g1 and (rho_all >= p['g2_weak']
                 or (rho_text is not None
                     and rho_text >= p['g2_strong'])):
        key = 'partially_feasible'
    else:
        key = 'infeasible_at_this_quality'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')

    md = []
    md.append('**Pre-registered verdicts** (script docstring): a rung-0 '
              'imaging probe of S2 with in-repo scans and numpy+Pillow '
              'only — the question is whether transliteration-free '
              'analysis can get off the ground, not anything about the '
              'manuscript\'s content.')
    md.append('')
    md.append(f'G1 binarization: median ink {r["ink"]["median"]}, CV '
              f'{r["ink"]["cv"]} → {"PASS" if g1 else "FAIL"}. '
              f'G2 segmentation: Spearman(components, ZL chars) '
              f'{rho_all:+.3f} over {p["n_folios"]} folios '
              f'(strong ≥ {p["g2_strong"]}). '
              f'G3: k* {r["g3"]["kstar"]} '
              f'({"PASS" if g3a else "FAIL"} ±30%), centroid ratio '
              f'{r["g3"]["centroid_ratio"]} '
              f'({"PASS" if g3b else "FAIL"} < '
              f'{p["centroid_ratio_max"]}). '
              f'{r["n_components_total"]} glyph-scale components.')
    verdict_text = {
        'feasible': 'FEASIBLE — build S2 proper.',
        'partially_feasible':
            'PARTIALLY FEASIBLE — the pipeline reliably SEES the '
            'writing (count correlation +0.84 with the transliteration '
            'through drawings and all), but glyph-shape cluster counts '
            'are unstable across folio halves (the F10 concern, at '
            'rung 0). S2 proceeds restricted: better shape descriptors '
            '/ a real CV stack / text-only pages.',
        'infeasible_at_this_quality':
            'INFEASIBLE AT THIS QUALITY — S2 starved (F10) pending '
            'better scans or tooling.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; G2 rho {rho_all:+.3f}, k* {r["g3"]["kstar"]}, '
               f'centroid ratio {r["g3"]["centroid_ratio"]}')
    return {'verdict': f'S2 rung 0: {key.upper()}',
            'suggestive': False, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N9 adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n9(item, expected_params, run_started):
    """Pre-registered outcomes (hapax_clustering_calibration.py
    docstring): does Part D's hapax-burstiness threshold separate
    language from non-language on the control battery?
    discriminator_valid / _broken / _weak / inconclusive. Re-derived
    from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    rows, p = data['rows'], data['params']
    thr = p['b_clustered']
    bP1, bP2 = rows['P1_latin']['B'], rows['P2_italian']['B']
    negs = [rows[n]['B'] for n in ('N3_grille', 'N4_self_citation')
            if rows[n]['B'] is not None]
    pos_clustered = bP1 > thr and bP2 > thr
    if not pos_clustered:
        key = 'inconclusive'
    elif negs and max(negs) >= min(bP1, bP2):
        key = 'discriminator_broken'
    elif not any(b > thr for b in negs):
        key = 'discriminator_valid'
    else:
        key = 'discriminator_weak'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')

    md = []
    md.append('**Pre-registered outcomes** (script docstring): Part D '
              f'reads hapax burstiness B > {thr} as "language". This '
              'calibration runs that exact statistic on the control '
              'battery. Hapax = strict count==1 on the collapsed '
              'vocabulary (Part D\'s definition, NOT relaxed to "rare '
              'words").')
    md.append('')
    md.append('| corpus | class | burstiness B | hapax rate | TTR |')
    md.append('|---|---|---|---|---|')
    for name, r in rows.items():
        b = 'n/a (<10 hapax)' if r['B'] is None else f'{r["B"]:+.3f}'
        hr = r.get('hapax_rate', '—')
        tt = r.get('ttr', '—')
        md.append(f'| {name} | {r["class"]} | {b} | {hr} | {tt} |')
    md.append('')
    n4 = rows['N4_self_citation']['B']
    verdict_text = {
        'inconclusive':
            'INCONCLUSIVE by the pre-registered criteria — which '
            'required the language positives to cluster, and they do '
            f'NOT (Latin {bP1:+.3f}, Italian {bP2:+.3f}, both below '
            f'{thr}). The controls are single-work corpora with no '
            'manuscript-like sections, so they cannot exhibit *topical* '
            'hapax clustering; the battery as built cannot fully test '
            'the topical version of the claim. But two observations '
            '(reported, not re-adjudicated) independently undermine Part '
            'D\'s inference as stated: (a) high hapax burstiness is NOT '
            'an intrinsic property of language text — real Latin/Italian '
            f'sit near zero; (b) a NON-language hoax control '
            f'(N4 self-citation, B {n4:+.3f}) clusters more strongly '
            'than anything else, so burstiness alone is not diagnostic '
            'of language. Net: Part D\'s "clustered → language" '
            'inference is uncalibrated and unsupported by these '
            'controls; a properly powered re-test needs multi-topic '
            'language and cipher corpora (a registered future rung). '
            'Ledger entry 14 — which claims only that the VMS clustering '
            'is real and locus-robust, never that it proves language — '
            'is unaffected and now carries a pointer to this result.',
        'discriminator_broken':
            'DISCRIMINATOR BROKEN — a non-language control clusters at '
            'or above the language positives; Part D\'s inference '
            'abandoned.',
        'discriminator_valid':
            'DISCRIMINATOR VALID — positives cluster, negatives do not.',
        'discriminator_weak':
            'DISCRIMINATOR WEAK — negatives cluster but below the '
            'positives; inference downgraded to suggestive-only.',
    }[key]
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; P1 {bP1:+.3f}, P2 {bP2:+.3f}, N4 {n4:+.3f} '
               f'(threshold {thr})')
    return {'verdict': f'N9 hapax-discriminator calibration: '
                       f'{key.upper()}',
            'suggestive': False, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N10 adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n10(item, expected_params, run_started):
    """Pre-registered outcomes (egyptian_determinative_test.py
    docstring): gate = the P-DET/P-DIA controls separate determinative
    from dialect; then pooled VMS U*(gallows) vs U*(root) ->
    determinative_supported / dialect_not_determinative / ambiguous.
    Re-derived from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, r = data['params'], data['results']
    det, dia, v = r['P_DET'], r['P_DIA'], r['VMS_full']
    gate = (det['u_gallows'] > det['u_root']
            and dia['u_root'] > dia['u_gallows'])
    if gate != data['gate_pass']:
        raise AdjudicationError('gate re-derivation mismatch')
    diff = v['u_gallows'] - v['u_root']
    if not gate:
        key = 'gate_failed'
    elif diff >= p['margin']:
        key = 'determinative_supported'
    elif v['u_root'] >= v['u_gallows']:
        key = 'dialect_not_determinative'
    else:
        key = 'ambiguous'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'determinative_supported'

    md = []
    md.append('**Pre-registered outcomes** (script docstring): the '
              'Egyptian core claim (gallows = semantic determinatives) '
              'tested by its discriminating signature — a determinative '
              'predicts SECTION more than the phonetic root does; '
              'dialect predicts the reverse. U*(X) = section-'
              'predictiveness above a cardinality-shuffle null.')
    md.append('')
    md.append('| corpus | U*(gallows) | U*(root) | reading |')
    md.append('|---|---|---|---|')
    labels = {'P_DET': 'P-DET control', 'P_DIA': 'P-DIA control',
              'VMS_full': 'VMS pooled', 'VMS_A': 'VMS Currier A',
              'VMS_B': 'VMS Currier B'}
    for tag, lab in labels.items():
        row = r[tag]
        read = ('gallows-carried' if row['u_gallows'] > row['u_root']
                else 'root-carried')
        md.append(f'| {lab} | {row["u_gallows"]:+.5f} | '
                  f'{row["u_root"]:+.5f} | {read} |')
    md.append('')
    md.append(f'Gate (controls separate the mechanisms): '
              f'{"PASS" if gate else "**FAIL**"}.')
    verdict_text = {
        'gate_failed': 'GATE FAILED — controls do not separate; no '
                       'reading.',
        'determinative_supported':
            'DETERMINATIVE SUPPORTED — gallows out-predict the root; the '
            'Egyptian core claim revives as a controlled finding. '
            'SUGGESTIVE, quarantined.',
        'dialect_not_determinative':
            'DIALECT, NOT DETERMINATIVE — the section information lives '
            'in the ROOT vocabulary (pooled U* '
            f'{v["u_root"]:.3f}), not the gallows '
            f'({v["u_gallows"]:.3f}); a ~{v["u_root"]/max(v["u_gallows"],1e-9):.0f}× '
            'gap matching the dialect control. The gallows-section '
            'association the pre-charter test read as "determinatives" '
            'is dialectal vocabulary variation. The Egyptian '
            'determinative claim is KILLED on its core prediction — '
            'now with controls, where the old test had none.',
        'ambiguous': 'AMBIGUOUS — neither feature dominates; no claim.',
    }[key]
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; VMS U*(gallows) {v["u_gallows"]:+.4f} vs '
               f'U*(root) {v["u_root"]:+.4f}; gate '
               f'{"pass" if gate else "fail"}')
    return {'verdict': f'N10 Egyptian determinative test: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N6g adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n6g(item, expected_params, run_started):
    """Pre-registered outcomes (line_discipline_derivation.py
    docstring): do the two shared axes reduce to position-independent
    class properties (log-freq + gallows + word-length)? Both axes'
    R^2-excess >= threshold AND the derived-axes table closes the moat
    -> shared_axes_derived; axis 1 only -> axis1_only; else
    not_derived. Re-derived from the JSON; refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, r = data['params'], data['results']
    fit = r['fit']
    thr = p['r2_excess']
    a1 = fit['1']['excess'] >= thr
    a2 = fit['2']['excess'] >= thr
    closes = r['derived_d_line'] <= r['bar_line']
    if a1 and a2 and closes:
        key = 'shared_axes_derived'
    elif a1 and closes:
        key = 'axis1_only'
    else:
        key = 'not_derived'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key in ('shared_axes_derived', 'axis1_only')

    md = []
    md.append('**Pre-registered outcomes** (script docstring): "derive" '
              'means REDUCE the shared axes to position-independent class '
              'properties (log-frequency + gallows-membership + word-'
              'length) — not external layout physics, which stays open. '
              f'An axis is reduced if its OLS R^2 beats a shuffle null by '
              f'>= {thr} AND the derived table still closes the moat.')
    md.append('')
    md.append('| axis | R² | null R² | excess | freq β | gallows β | '
              'wlen β |')
    md.append('|---|---|---|---|---|---|---|')
    for k in ('1', '2', '3'):
        f = fit[k]
        tag = {'1': ' (edge, shared)', '2': ' (interior, shared)',
               '3': ' (pre-final, B-only)'}[k]
        md.append(f'| {k}{tag} | {f["r2"]} | {f["null_r2"]} | '
                  f'{f["excess"]:+.3f} | {f["beta"]["freq"]:+.2f} | '
                  f'{f["beta"]["gallows"]:+.2f} | {f["beta"]["wlen"]:+.2f} |')
    md.append('')
    md.append(f'Derived-axes table (Âx₁, Âx₂ + measured axis 3): D_line '
              f'{r["derived_d_line"]} vs bar {r["bar_line"]} (measured '
              f'rank-3 achieved {r["measured_rank3_d_line"]}).')
    verdict_text = {
        'shared_axes_derived':
            'SHARED AXES DERIVED — both manuscript-wide rules reduce to '
            'the principles and the derived table closes the moat. '
            'SUGGESTIVE, quarantined.',
        'axis1_only':
            'AXIS 1 ONLY — the edge rule reduces (Grove/LAAFU '
            'quantified) with closure; the interior gradient does not. '
            'SUGGESTIVE, quarantined.',
        'not_derived':
            'NOT DERIVED (partial reduction, corpse logged) — the three '
            'principles explain a SUBSTANTIAL, above-chance share of '
            f'each shared axis (edge R² {fit["1"]["r2"]}, interior '
            f'{fit["2"]["r2"]}, both ~2× the shuffle null) with '
            'interpretable coefficients (frequent, gallows-initial, '
            'short words → line edges — Grove/LAAFU made quantitative), '
            'but substituting the ~50%-fidelity predictions reopens the '
            f'moat (D_line {r["derived_d_line"]} > bar {r["bar_line"]}). '
            'The strong claim ("the shared axes ARE these properties") '
            'is killed; the weak claim (they are ~half these properties, '
            'plus real residual structure the interior gradient carries '
            'on its own) is documented. Richer principle sets are the '
            'informed next candidate.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; axis1 excess {fit["1"]["excess"]:+.3f}, axis2 '
               f'{fit["2"]["excess"]:+.3f} (thr {thr}), derived D_line '
               f'{r["derived_d_line"]} vs bar {r["bar_line"]}')
    return {'verdict': f'S3 rung 4: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


# ────────────────────────────────────────────────────────────────────
# N6h adjudication — pre-registered, mechanical, JSON-only
# ────────────────────────────────────────────────────────────────────
def adjudicate_n6h(item, expected_params, run_started):
    """Pre-registered outcomes (line_discipline_morphology.py
    docstring): does within-word glyph morphology (wwpos + finality)
    reduce the INTERIOR gradient? gate = 3-principle baseline
    reproduces N6g; then interior R^2 >= r2_target AND gain >= delta_min
    -> interior_morphology_reduced; gain >= delta_modest ->
    modest_improvement; else no_improvement. Re-derived from the JSON;
    refuses on mismatch."""
    jpath = RESULTS / item['result_json']
    if not jpath.exists():
        raise AdjudicationError(f'{jpath.name} was not written by the run')
    if jpath.stat().st_mtime < run_started:
        raise AdjudicationError(f'{jpath.name} predates this run — stale')
    data = json.loads(jpath.read_text(encoding='utf-8'))
    p, r = data['params'], data['results']
    a2 = r['fit']['2']
    base_ok = r['base_gate']
    if not base_ok:
        key = 'gate_failed'
    elif a2['r2'] >= p['r2_target'] and a2['gain'] >= p['delta_min']:
        key = 'interior_morphology_reduced'
    elif a2['gain'] >= p['delta_modest']:
        key = 'modest_improvement'
    else:
        key = 'no_improvement'
    if data.get('verdict') != key:
        raise AdjudicationError(f'runner derives {key!r} but the script '
                                f'recorded {data.get("verdict")!r}')
    suggestive = key == 'interior_morphology_reduced'

    md = []
    md.append('**Pre-registered outcomes** (script docstring): the '
              'HYPOTHESIS — the line orders words by the typical WITHIN-'
              'WORD position of their first glyph (word-initial-type '
              'early, word-final-type late) — tested by adding within-'
              'word morphology (wwpos + finality) to the N6g principle '
              f'set. Reduced iff interior R^2 >= {p["r2_target"]} AND '
              f'gain over the 3-principle baseline >= {p["delta_min"]}.')
    md.append('')
    md.append('| axis | R² (3-principle → +morphology) | gain | wwpos β | '
              'finality β |')
    md.append('|---|---|---|---|---|')
    for k, lab in (('1', 'edge'), ('2', 'interior'), ('3', 'pre-final')):
        f = r['fit'][k]
        md.append(f'| {k} ({lab}) | {f["r2_3principle"]} → {f["r2"]} | '
                  f'{f["gain"]:+.3f} | {f["beta"]["wwpos"]:+.2f} | '
                  f'{f["beta"]["finality"]:+.2f} |')
    md.append('')
    ww = r['wwpos_by_class']
    order = sorted(ww, key=lambda c: ww[c])
    md.append('Within-word position by class (0=word-initial, 1=word-'
              'final): ' + ', '.join(f'{c} {ww[c]:.2f}' for c in order)
              + '.')
    md.append(f'Enriched derived table: D_line {r["derived_d_line"]} vs '
              f'bar {r["bar_line"]} (does not close; the residual '
              'persists).')
    verdict_text = {
        'gate_failed': 'GATE FAILED — baseline does not reproduce N6g.',
        'interior_morphology_reduced':
            'INTERIOR MORPHOLOGY REDUCED — the interior gradient is '
            'substantially a within-word-morphology effect. SUGGESTIVE, '
            'quarantined.',
        'modest_improvement':
            'MODEST IMPROVEMENT (hypothesis directionally confirmed, not '
            'dominant) — within-word position is the LARGEST predictor '
            f'of the interior gradient (wwpos β {a2["beta"]["wwpos"]:+.2f}, '
            'positive as hypothesized: word-initial-type glyphs early, '
            f'word-final-type late) and raises interior R^2 by '
            f'{a2["gain"]:+.3f} (0.50 → {a2["r2"]}), clearing the gain '
            f'bar but not the {p["r2_target"]} strong-reduction target. '
            'So the interior gradient is PARTLY a morphological echo — '
            'the line reflects word structure — but a residual survives '
            'even frequency + gallows + length + within-word position. '
            'The line-discipline mystery is now this smaller, sharper '
            'residual.',
        'no_improvement':
            'NO IMPROVEMENT — within-word position does not explain the '
            'interior gradient; the residual is deeper. Corpse logged.',
    }[key]
    md.append('')
    md.append(f'**VERDICT: {verdict_text}**')
    summary = (f'{key}; interior R^2 {a2["r2"]} (gain {a2["gain"]:+.3f}, '
               f'wwpos β {a2["beta"]["wwpos"]:+.2f}), target '
               f'{p["r2_target"]}')
    return {'verdict': f'S3 rung 5: {key.upper()}',
            'suggestive': suggestive, 'md': '\n'.join(md),
            'summary': summary, 'params': p, 'json_name': jpath.name}


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
        'title': 'Max-strength verbose cipher inversion (rung 3) '
                 '[SUPERSEDED by N1b]',
        'stem': 'verbose_cipher_inversion',
        'not_ready': 'completed 2026-07-17 (INSTRUMENT KILLED) and '
                     'superseded: the script now carries the rung-3b '
                     'coverage-penalized objective, so the rung-3 '
                     'configuration no longer exists to re-run. Use N1b.',
    },
    {
        'id': 'N1b',
        'title': 'Verbose cipher inversion, rung 3b: coverage-penalized '
                 'objective, max-strength budget',
        'stem': 'verbose_cipher_inversion',
        'overrides': N1_PROFILE,
        'smoke_overrides': N1_SMOKE,
        'timeout_s': 12 * 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'verbose_cipher_inversion.json',
        'adjudicate': adjudicate_n1,
        'objective': 'coverage_penalized',
        'research_heading': 'Phase 4d — Verbose cipher inversion, rung 3b: '
                            'coverage-penalized objective',
        'not_ready': None,
    },
    {
        'id': 'N3',
        'title': 'Line-as-record structures (portfolio S7): interior '
                 'positional-field information',
        'stem': 'line_as_record_structures',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 1800,
        'smoke_timeout_s': 900,
        'result_json': 'line_as_record_structures.json',
        'adjudicate': adjudicate_n3,
        'research_heading': 'Portfolio S7 — line-as-record structures, '
                            'first instrumented run',
        'not_ready': None,
    },
    {
        'id': 'N3b',
        'title': 'Line-as-record rung 2 (portfolio S7): per-hand '
                 'adjudication with per-hand null batteries',
        'stem': 'line_as_record_per_hand',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_as_record_per_hand.json',
        'adjudicate': adjudicate_n3b,
        'research_heading': 'Portfolio S7, rung 2 — per-hand '
                            'line-as-record adjudication',
        'not_ready': None,
    },
    {
        'id': 'N2b',
        'title': 'S9 follow-up: sensitivity-normalized effect floors '
                 '(floor-scaling hypothesis test)',
        'stem': 'transliteration_floor_calibration',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'transliteration_floor_calibration.json',
        'adjudicate': adjudicate_n2b,
        'research_heading': 'Portfolio S9, follow-up — sensitivity-'
                            'normalized effect floors',
        'not_ready': None,
    },
    {
        'id': 'N2c',
        'title': 'S9 follow-up 2: significance-only cross-reading battery '
                 '(200 nulls, no effect floor)',
        'stem': 'transliteration_significance',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 7200,
        'smoke_timeout_s': 3600,
        'result_json': 'transliteration_significance.json',
        'adjudicate': adjudicate_n2c,
        'research_heading': 'Portfolio S9, follow-up 2 — significance-only '
                            'cross-reading battery',
        'not_ready': None,
    },
    {
        'id': 'N3c',
        'title': 'Line-as-record rung 3 (portfolio S7): composition vs '
                 'ordinal structure in Currier B',
        'stem': 'line_as_record_ordinal',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_as_record_ordinal.json',
        'adjudicate': adjudicate_n3c,
        'research_heading': 'Portfolio S7, rung 3 — composition vs '
                            'ordinal structure (Currier B)',
        'not_ready': None,
    },
    {
        'id': 'N3d',
        'title': 'Line-as-record rung 4 (portfolio S7): paragraph control '
                 '+ characterization of the Currier-B ordinal signal',
        'stem': 'line_as_record_characterization',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_as_record_characterization.json',
        'adjudicate': adjudicate_n3d,
        'research_heading': 'Portfolio S7, rung 4 — paragraph control and '
                            'characterization (Currier B)',
        'not_ready': None,
    },
    {
        'id': 'N3e',
        'title': 'Line-as-record rung 5 (portfolio S7): within-section '
                 'replication (bio / recipes / other_B)',
        'stem': 'line_as_record_section_split',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_as_record_section_split.json',
        'adjudicate': adjudicate_n3e,
        'research_heading': 'Portfolio S7, rung 5 — within-section '
                            'replication (Currier B)',
        'not_ready': None,
    },
    {
        'id': 'N4',
        'title': 'S5/S6 line-class family test: which calibrated process '
                 'orders Currier B\'s lines?',
        'stem': 'line_class_family_test',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_class_family_test.json',
        'adjudicate': adjudicate_n4,
        'research_heading': 'Portfolio S5/S6 — line-class sequence family '
                            'classification (Currier B)',
        'not_ready': None,
    },
    {
        'id': 'N1c',
        'title': 'Verbose cipher inversion, rung 3c: Occitan LM extension '
                 '(max-strength budget, coverage-penalized objective)',
        'stem': 'verbose_cipher_inversion',
        'overrides': N1_PROFILE,
        'smoke_overrides': N1_SMOKE,
        'timeout_s': 12 * 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'verbose_cipher_inversion.json',
        'adjudicate': adjudicate_n1,
        'objective': 'coverage_penalized',
        'research_heading': 'Phase 4e — Verbose cipher inversion, rung 3c: '
                            'Occitan LM extension',
        'not_ready': None,
    },
    {
        'id': 'N5',
        'title': 'S7-R: independent re-implementation of the intra-line '
                 'ordinal measurement (rank statistic, PHASE8 §8.7-1)',
        'stem': 'line_ordinal_rank_test',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_ordinal_rank_test.json',
        'adjudicate': adjudicate_n5,
        'research_heading': 'Portfolio S7-R — independent '
                            're-implementation (rank-based)',
        'not_ready': None,
    },
    {
        'id': 'N6',
        'title': 'S3 rung 2: line-discipline tournament — is B\'s line '
                 'texture reducible to lexicon + table + one knob?',
        'stem': 'line_discipline_tournament',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_discipline_tournament.json',
        'adjudicate': adjudicate_n6,
        'research_heading': 'Portfolio S3, rung 2 — line-discipline '
                            'reduction tournament (Currier B)',
        'not_ready': None,
    },
    {
        'id': 'N6b',
        'title': 'S3 rung 2b: table-compression test — is the discipline '
                 'one latent axis?',
        'stem': 'line_discipline_compression',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_discipline_compression.json',
        'adjudicate': adjudicate_n6b,
        'research_heading': 'Portfolio S3, rung 2b — discipline-table '
                            'compression (Currier B)',
        'not_ready': None,
    },
    {
        'id': 'N6c',
        'title': 'S3 rung 2c: rank-2 test — do two axes complete the '
                 'discipline?',
        'stem': 'line_discipline_rank2',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_discipline_rank2.json',
        'adjudicate': adjudicate_n6c,
        'research_heading': 'Portfolio S3, rung 2c — rank-2 discipline '
                            'test (Currier B)',
        'not_ready': None,
    },
    {
        'id': 'N6d',
        'title': 'S3 rung 2d: rank-3 test — do three axes complete the '
                 'discipline?',
        'stem': 'line_discipline_rank3',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_discipline_rank3.json',
        'adjudicate': adjudicate_n6d,
        'research_heading': 'Portfolio S3, rung 2d — rank-3 discipline '
                            'test (Currier B)',
        'not_ready': None,
    },
    {
        'id': 'N6e',
        'title': 'S3 rung 3: cross-hand blind test — does an A-measured '
                 'table place B\'s lines?',
        'stem': 'line_discipline_transfer',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'line_discipline_transfer.json',
        'adjudicate': adjudicate_n6e,
        'research_heading': 'Portfolio S3, rung 3 — cross-hand blind '
                            'table test (A → B)',
        'not_ready': None,
    },
    {
        'id': 'N7',
        'title': 'Part-D hapax re-adjudication: does language_vs_cipher\'s '
                 'hapax clustering survive a paragraph-only corpus?',
        'stem': 'hapax_locus_readjudication',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 1800,
        'smoke_timeout_s': 900,
        'result_json': 'hapax_locus_readjudication.json',
        'adjudicate': adjudicate_n7,
        'research_heading': 'Legacy-test audit — language_vs_cipher '
                            'Part D under locus decontamination',
        'not_ready': None,
    },
    {
        'id': 'N6f',
        'title': 'S3 rung 3b: axis-3 characterization in hand A — '
                 'absent, inverted, or shared?',
        'stem': 'line_discipline_axis3_handA',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 1800,
        'smoke_timeout_s': 900,
        'result_json': 'line_discipline_axis3_handA.json',
        'adjudicate': adjudicate_n6f,
        'research_heading': 'Portfolio S3, rung 3b — axis-3 '
                            'characterization in hand A',
        'not_ready': None,
    },
    {
        'id': 'N8',
        'title': 'S2 rung 0: raw-scan glyph feasibility probe '
                 '(numpy+Pillow, no CV stack)',
        'stem': 'scan_glyph_feasibility',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'scan_glyph_feasibility.json',
        'adjudicate': adjudicate_n8,
        'research_heading': 'Portfolio S2, rung 0 — raw-scan glyph '
                            'feasibility probe',
        'not_ready': None,
    },
    {
        'id': 'N9',
        'title': 'Hapax-clustering discriminator calibration: does '
                 '"clustered → language" separate the control classes?',
        'stem': 'hapax_clustering_calibration',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 1800,
        'smoke_timeout_s': 900,
        'result_json': 'hapax_clustering_calibration.json',
        'adjudicate': adjudicate_n9,
        'research_heading': 'Legacy-test audit — hapax-clustering '
                            'discriminator calibration',
        'not_ready': None,
    },
    {
        'id': 'N10',
        'title': 'Egyptian determinative test: are the gallows semantic '
                 'determinatives, or dialectal vocabulary?',
        'stem': 'egyptian_determinative_test',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 1800,
        'smoke_timeout_s': 900,
        'result_json': 'egyptian_determinative_test.json',
        'adjudicate': adjudicate_n10,
        'research_heading': 'Legacy-hypothesis trial — gallows as '
                            'semantic determinatives (controlled)',
        'not_ready': None,
    },
    {
        'id': 'N6g',
        'title': 'S3 rung 4: principled derivation — do the two shared '
                 'axes reduce to class properties?',
        'stem': 'line_discipline_derivation',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 1800,
        'smoke_timeout_s': 900,
        'result_json': 'line_discipline_derivation.json',
        'adjudicate': adjudicate_n6g,
        'research_heading': 'Portfolio S3, rung 4 — principled '
                            '(reductive) derivation of the shared axes',
        'not_ready': None,
    },
    {
        'id': 'N6h',
        'title': 'S3 rung 5: morphology derivation — does within-word '
                 'position reduce the interior gradient?',
        'stem': 'line_discipline_morphology',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 1800,
        'smoke_timeout_s': 900,
        'result_json': 'line_discipline_morphology.json',
        'adjudicate': adjudicate_n6h,
        'research_heading': 'Portfolio S3, rung 5 — within-word '
                            'morphology derivation of the interior '
                            'gradient',
        'not_ready': None,
    },
    {
        'id': 'N2',
        'title': 'Cross-transliteration invariance audit (portfolio S9): '
                 'A1 fingerprint spread + S7-B ordinal invariance',
        'stem': 'cross_transliteration_invariance',
        'overrides': {},
        'smoke_overrides': {},
        'timeout_s': 3600,
        'smoke_timeout_s': 1800,
        'result_json': 'cross_transliteration_invariance.json',
        'adjudicate': adjudicate_n2,
        'research_heading': 'Portfolio S9 — cross-transliteration '
                            'invariance audit (A1)',
        'not_ready': None,
    },
]


def pick_item(state, wanted):
    if wanted:
        for it in QUEUE:
            if it['id'] == wanted:
                return it
        raise NotReady(f'unknown queue item {wanted!r} — queue is '
                       f'{[q["id"] for q in QUEUE]}')
    blocked = []
    for it in QUEUE:
        if state.get(it['id'], {}).get('status') == 'completed':
            continue
        if it.get('not_ready'):
            blocked.append(f'{it["id"]}: {it["not_ready"]}')
            continue
        return it
    if blocked:
        raise NotReady('every open item is blocked — ' + ' | '.join(blocked))
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
        if item.get('research_heading'):
            research_section = build_research_section(
                item, date, adj, overrides, dur, branch, smoke)
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


def build_research_section(item, date, adj, overrides, dur, branch, smoke):
    killed = adj['verdict'].startswith('INSTRUMENT KILLED')
    head = f'### {item["research_heading"]} ({date})'
    tag = ('[AUTOMATED — written by tools/overnight.py'
           + (', smoke rehearsal' if smoke else '')
           + f'; run committed to branch {branch}; awaiting human review '
             'before promotion to any evidence tier.]')
    body = [head, '', tag, '',
            f'Configuration (pre-registered in the script docstring): '
            f'{overrides if overrides else "script defaults"}. '
            f'Runtime {dur/3600:.2f} h at PYTHONHASHSEED=0. Holdout: whole '
            'folios (VMS) / 24-line pseudo-folio blocks (controls).', '']
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
