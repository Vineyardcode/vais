// VAIS in-browser test runner — Web Worker.
// Boots Pyodide (CPython on WebAssembly) + numpy, mounts the repository
// data pack into the virtual filesystem, then executes a test the same
// way `python scripts/<stem>.py` does (runpy, cwd = repo root), with
// parameter overrides spliced by the repo's own webui/runner.py.
// PYTHONHASHSEED=0 is requested at interpreter start; the page compares
// output against the committed golden and reports any drift.
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/';
importScripts(PYODIDE + 'pyodide.js');

let pyodide = null;
const post = (type, data) => postMessage({ type: type, data: data });

const HARNESS = `
import io, json, os, sys, traceback, runpy
os.chdir('/vais')
# python scripts/X.py puts scripts/ on sys.path; runpy.run_path does not
sys.path.insert(0, '/vais/scripts')
import vais_js

class _JSRaw(io.RawIOBase):
    def writable(self): return True
    def write(self, b):
        vais_js.emit(bytes(b).decode('utf-8', 'replace'))
        return len(b)

def _fresh_streams():
    w = io.TextIOWrapper(io.BufferedWriter(_JSRaw()), encoding='utf-8',
                         errors='replace', line_buffering=True)
    sys.stdout = w
    sys.stderr = w
    return w

def run_test(stem, overrides_json, specs_json):
    w = _fresh_streams()
    try:
        overrides = json.loads(overrides_json)
        src = open('scripts/%s.py' % stem, encoding='utf-8').read()
        if overrides:
            if '/vais/webui' not in sys.path:
                sys.path.insert(0, '/vais/webui')
            from runner import apply_overrides
            src = apply_overrides(src, overrides, json.loads(specs_json))
        path = 'scripts/_web_%s.py' % stem
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(src)
        try:
            runpy.run_path(path, run_name='__main__')
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
        return 'ok'
    except SystemExit as e:
        return 'ok' if not e.code else 'exit %s' % e.code
    except BaseException:
        w.write('\\n' + traceback.format_exc())
        return 'error'
    finally:
        try:
            sys.stdout.flush()
        except Exception:
            pass
`;

async function init() {
  post('status', 'loading Python runtime (WebAssembly, ~15 MB — cached after first visit)…');
  pyodide = await loadPyodide({ indexURL: PYODIDE, env: { PYTHONHASHSEED: '0' } });
  post('status', 'loading numpy…');
  await pyodide.loadPackage('numpy');
  post('status', 'fetching repository data pack…');
  const resp = await fetch(new URL('data_pack.zip', self.location).href);
  if (!resp.ok) throw new Error('data pack fetch failed: ' + resp.status);
  const buf = await resp.arrayBuffer();
  pyodide.FS.mkdir('/vais');
  pyodide.unpackArchive(buf, 'zip', { extractDir: '/vais' });
  post('status', 'preparing harness…');
  pyodide.registerJsModule('vais_js', { emit: (s) => post('out', s) });
  await pyodide.runPythonAsync(HARNESS);
  post('ready');
}

onmessage = async (e) => {
  const m = e.data;
  try {
    if (m.type === 'init') {
      await init();
    } else if (m.type === 'run') {
      post('status', 'running ' + m.stem + ' — the tab may feel busy until it finishes…');
      const runner = pyodide.globals.get('run_test');
      const status = runner(m.stem, JSON.stringify(m.overrides || {}),
                            JSON.stringify(m.specs || {}));
      if (runner.destroy) runner.destroy();
      post('done', status);
    }
  } catch (err) {
    post('error', String(err && err.message ? err.message : err));
  }
};
