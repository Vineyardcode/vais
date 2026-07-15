"""Local web UI for the Voynich analysis suite.

    python webui/server.py            # http://127.0.0.1:5000

Endpoints:
  GET  /                      single-page UI
  GET  /api/tests             registry (descriptions, params w/ defaults, timings)
  POST /api/run               {name, params?, timeout?} -> {job}
  POST /api/run_all           {names?} -> {job}   sequential batch
  GET  /api/jobs/<id>         job status + captured output
  GET  /api/presets/<test>    named presets (always includes "defaults")
  POST /api/presets/<test>    {name, params} save
  DELETE /api/presets/<test>/<preset>
"""
import json
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import registry as registry_mod
import runner as runner_mod

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
PRESETS_FILE = Path(__file__).resolve().parent / "presets.json"

app = Flask(__name__, static_folder=None)

REGISTRY = registry_mod.build_registry()

JOBS = {}
JOBS_LOCK = threading.Lock()
PRESETS_LOCK = threading.Lock()


def _load_presets():
    if PRESETS_FILE.exists():
        try:
            return json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_presets(data):
    PRESETS_FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False),
                            encoding="utf-8")


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/api/tests")
def api_tests():
    return jsonify(REGISTRY)


def _default_timeout(test):
    base = test.get("baseline_seconds") or 60
    return max(120, min(3600, int(base * 3 + 60)))


def _run_job(job_id, names, params_by_test, timeout_by_test):
    for name in names:
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["tests"][name]["status"] = "running"
            job["current"] = name
        test = REGISTRY.get(name)
        res = runner_mod.run_test(
            name,
            overrides=params_by_test.get(name) or {},
            param_specs=test["params"] if test else None,
            timeout=timeout_by_test.get(name) or _default_timeout(test or {}),
        )
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["tests"][name].update(res)
            job["tests"][name]["status"] = res.get("status", "error")
    with JOBS_LOCK:
        JOBS[job_id]["done"] = True
        JOBS[job_id]["current"] = None


def _start_job(names, params_by_test, timeout_by_test):
    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id, "names": names, "done": False, "current": None,
            "tests": {n: {"status": "pending"} for n in names},
        }
    t = threading.Thread(target=_run_job,
                         args=(job_id, names, params_by_test, timeout_by_test),
                         daemon=True)
    t.start()
    return job_id


@app.post("/api/run")
def api_run():
    body = request.get_json(force=True)
    name = body.get("name")
    if name not in REGISTRY:
        return jsonify({"error": f"unknown test {name}"}), 404
    params = body.get("params") or {}
    unknown = set(params) - set(REGISTRY[name]["params"])
    if unknown:
        return jsonify({"error": f"unknown parameters: {sorted(unknown)}"}), 400
    timeout = body.get("timeout")
    job_id = _start_job([name], {name: params},
                        {name: int(timeout)} if timeout else {})
    return jsonify({"job": job_id})


@app.post("/api/run_all")
def api_run_all():
    body = request.get_json(silent=True) or {}
    names = body.get("names") or sorted(REGISTRY.keys())
    bad = [n for n in names if n not in REGISTRY]
    if bad:
        return jsonify({"error": f"unknown tests: {bad}"}), 400
    job_id = _start_job(names, {}, {})
    return jsonify({"job": job_id})


@app.get("/api/jobs/<job_id>")
def api_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "unknown job"}), 404
        return jsonify(job)


@app.get("/api/presets/<test>")
def api_presets_get(test):
    if test not in REGISTRY:
        return jsonify({"error": "unknown test"}), 404
    defaults = {k: v["default"] for k, v in REGISTRY[test]["params"].items()}
    with PRESETS_LOCK:
        saved = _load_presets().get(test, {})
    return jsonify({"defaults": defaults, **saved})


@app.post("/api/presets/<test>")
def api_presets_save(test):
    if test not in REGISTRY:
        return jsonify({"error": "unknown test"}), 404
    body = request.get_json(force=True)
    name = (body.get("name") or "").strip()
    params = body.get("params") or {}
    if not name or name == "defaults":
        return jsonify({"error": "preset name required ('defaults' is reserved)"}), 400
    unknown = set(params) - set(REGISTRY[test]["params"])
    if unknown:
        return jsonify({"error": f"unknown parameters: {sorted(unknown)}"}), 400
    with PRESETS_LOCK:
        data = _load_presets()
        data.setdefault(test, {})[name] = params
        _save_presets(data)
    return jsonify({"ok": True})


@app.delete("/api/presets/<test>/<preset>")
def api_presets_delete(test, preset):
    if preset == "defaults":
        return jsonify({"error": "cannot delete built-in defaults"}), 400
    with PRESETS_LOCK:
        data = _load_presets()
        if test in data and preset in data[test]:
            del data[test][preset]
            if not data[test]:
                del data[test]
            _save_presets(data)
            return jsonify({"ok": True})
    return jsonify({"error": "preset not found"}), 404


if __name__ == "__main__":
    print(f"Registry: {len(REGISTRY)} tests")
    app.run(host="127.0.0.1", port=5000, debug=False)
