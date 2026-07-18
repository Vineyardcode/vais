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
