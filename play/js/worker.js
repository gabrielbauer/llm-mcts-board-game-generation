/* Runs Python (Pyodide) off the main thread: the engine, the four games
   and the UCT agent. Messages: {id, cmd, args} -> {id, ok, result|error}. */

const params = new URL(self.location.href).searchParams;
const BASE = params.get("base") || "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
const VERSION = params.get("v") || "1";
const PY_FILES = ["boardwalk.py", "uct.py", "bridge.py",
  "games/__init__.py", "games/c1.py", "games/c2.py", "games/c3.py", "games/c4.py"];

let bridge = null;

const ready = (async () => {
  importScripts(BASE + "pyodide.js");
  const py = await loadPyodide({ indexURL: BASE });
  py.FS.mkdirTree("/play/games");
  const files = await Promise.all(PY_FILES.map(async (f) => {
    const r = await fetch(`../py/${f}?v=${VERSION}`);
    if (!r.ok) throw new Error(`could not load ${f} (${r.status})`);
    return [f, await r.text()];
  }));
  for (const [f, text] of files) py.FS.writeFile(`/play/${f}`, text);
  py.runPython("import sys; sys.path.insert(0, '/play')");
  bridge = py.pyimport("bridge");
})();

self.onmessage = async (e) => {
  const { id, cmd, args = [] } = e.data;
  try {
    await ready;
    if (cmd === "init") { self.postMessage({ id, ok: true, result: null }); return; }
    if (typeof bridge[cmd] !== "function") throw new Error("unknown command " + cmd);
    const out = bridge[cmd](...args);
    self.postMessage({ id, ok: true, result: JSON.parse(out) });
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message || err) });
  }
};
