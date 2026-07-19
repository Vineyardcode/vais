// Page-side controller for the in-browser test runner (see pyworker.js).
// Expects window.VAIS_TEST = { stem, specs, base, baselineSeconds } and
// the elements #run-btn, #stop-btn, #run-status, #run-out (+ optional
// #golden-pre for the diff check and [data-param] inputs).
(function () {
  var cfg = window.VAIS_TEST;
  if (!cfg) return;
  var worker = null, ready = false, running = false;
  var outEl = document.getElementById('run-out');
  var statusEl = document.getElementById('run-status');
  var runBtn = document.getElementById('run-btn');
  var stopBtn = document.getElementById('stop-btn');
  var chunks = [];

  function setStatus(s) { statusEl.textContent = s; }
  function flushOut() {
    if (chunks.length) {
      outEl.textContent += chunks.join('');
      chunks = [];
    }
  }
  setInterval(flushOut, 150);

  function collectOverrides() {
    var o = {};
    var inputs = document.querySelectorAll('[data-param]');
    for (var i = 0; i < inputs.length; i++) {
      var inp = inputs[i];
      if (inp.value !== inp.defaultValue) o[inp.dataset.param] = inp.value;
    }
    return o;
  }

  function goldenVerdict(overridden) {
    var g = document.getElementById('golden-pre');
    if (!g) return '';
    if (overridden) return ' Parameters were overridden — golden not comparable.';
    var norm = function (t) {
      return t.replace(/\r\n/g, '\n').replace(/\s+$/, '');
    };
    var a = norm(g.textContent).split('\n');
    var b = norm(outEl.textContent).split('\n');
    if (a.join('\n') === b.join('\n')) return ' Output matches the committed golden.';
    var n = 0, len = Math.max(a.length, b.length);
    for (var i = 0; i < len; i++) if (a[i] !== b[i]) n++;
    return ' Output differs from the golden on ' + n + ' line(s) ' +
           '(WASM platform drift is possible — clone the repo for the ' +
           'byte-exact reference).';
  }

  function ensureWorker() {
    if (worker) return;
    worker = new Worker(cfg.base + 'pyworker.js');
    ready = false;
    worker.onmessage = function (e) {
      var m = e.data;
      if (m.type === 'status') setStatus(m.data);
      else if (m.type === 'out') chunks.push(m.data);
      else if (m.type === 'ready') {
        ready = true;
        if (pendingRun) { pendingRun = false; doRun(); }
      } else if (m.type === 'done') {
        flushOut();
        running = false;
        runBtn.disabled = false;
        setStatus('finished (' + m.data + ').' + goldenVerdict(lastOverridden));
      } else if (m.type === 'error') {
        flushOut();
        running = false;
        runBtn.disabled = false;
        setStatus('runner error: ' + m.data);
      }
    };
    worker.onerror = function (e) {
      running = false;
      runBtn.disabled = false;
      setStatus('worker error: ' + (e.message || 'failed to load'));
    };
  }

  var pendingRun = false, lastOverridden = false;
  function doRun() {
    var overrides = collectOverrides();
    lastOverridden = Object.keys(overrides).length > 0;
    outEl.textContent = '';
    running = true;
    runBtn.disabled = true;
    worker.postMessage({ type: 'run', stem: cfg.stem,
                         overrides: overrides, specs: cfg.specs });
  }

  runBtn.onclick = function () {
    if (running) return;
    if (cfg.baselineSeconds > 120 &&
        !confirm('This test takes ~' + Math.round(cfg.baselineSeconds / 60) +
                 ' min natively and several times longer in the browser. ' +
                 'Run anyway? (Cloning the repo is the fast path.)')) return;
    ensureWorker();
    if (ready) doRun();
    else { pendingRun = true; worker.postMessage({ type: 'init' }); }
  };

  stopBtn.onclick = function () {
    if (worker) { worker.terminate(); worker = null; }
    ready = false; running = false; pendingRun = false;
    runBtn.disabled = false;
    setStatus('stopped — the Python runtime was discarded; Run reloads it.');
  };
})();
