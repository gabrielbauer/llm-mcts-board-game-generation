/* UI controller: talks to the Python worker, keeps the human/AI turn loop,
   turns clicks into indices of the engine's legal-move list. */

(function () {
  const $ = (id) => document.getElementById(id);
  const qs = new URLSearchParams(location.search);
  const VERSION = "1";
  const THINK = [0.5, 1, 2, 4];

  // ---------- worker RPC ----------
  const workerURL = "js/worker.js?v=" + VERSION + (qs.get("pyodide") ? "&base=" + encodeURIComponent(qs.get("pyodide")) : "");
  const worker = new Worker(workerURL);
  let nextId = 1;
  const pending = new Map();
  worker.onmessage = (e) => {
    const { id, ok, result, error } = e.data;
    const p = pending.get(id); pending.delete(id);
    if (p) ok ? p.resolve(result) : p.reject(new Error(error));
  };
  worker.onerror = (e) => showLoadError(e.message || "worker failed to start");
  const call = (cmd, ...args) => new Promise((resolve, reject) => {
    const id = nextId++; pending.set(id, { resolve, reject });
    worker.postMessage({ id, cmd, args });
  });

  // ---------- state ----------
  const store = {
    get(k, d) { try { const v = localStorage.getItem("bgplay." + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("bgplay." + k, JSON.stringify(v)); } catch { } },
  };
  let G = null, S = null;
  let human = store.get("side", 0);
  let think = store.get("think", 1);
  let selected = null, hint = null, busy = false, aiStats = null, token = 0, ready = false;

  // ---------- helpers ----------
  const key = (xy) => xy[0] + "," + xy[1];
  const coord = (xy) => Board.coord(xy[0], xy[1]);
  const fmtInt = (n) => n.toLocaleString("en-US");
  const myTurn = () => ready && S && !S.over && !busy && S.player === human;

  function moveText(m, game) {
    if (m.t === "place") {
      const p = game.pieces[m.p];
      return `${p ? p.name : m.p} ${coord(m.to)}`;
    }
    if (m.t === "move") {
      const cap = (m.changed || []).some(([x, y, b, a]) => a === "_" && !(x === m.from[0] && y === m.from[1]));
      return `${coord(m.from)}${cap ? "×" : "–"}${coord(m.to)}`;
    }
    return m.label;
  }

  function index() {
    const placeAt = new Map(), from = new Map(), other = [];
    S.moves.forEach((m, i) => {
      if (m.t === "place") { const k = key(m.to); if (!placeAt.has(k)) placeAt.set(k, []); placeAt.get(k).push(i); }
      else if (m.t === "move") { const k = key(m.from); if (!from.has(k)) from.set(k, []); from.get(k).push(i); }
      else other.push(i);
    });
    return { placeAt, from, other };
  }

  // ---------- rendering ----------
  function renderTabs() {
    $("tabs").innerHTML = Object.values(GAMES).map((g) =>
      `<button role="tab" aria-selected="${G && g.id === G.id}" data-g="${g.id}">
        <span class="tp">${g.prompt}</span><span class="tn">${g.title}</span>
        <span class="tf">${g.model} · ${g.fitness.toFixed(3)}</span></button>`).join("");
  }

  function renderStatic() {
    $("g-prompt").textContent = `${G.prompt} · best game for this prompt`;
    $("g-title").textContent = G.title;
    $("g-sw").style.background = G.modelColor;
    $("g-meta").textContent = `${G.model} · fitness ${G.fitness.toFixed(3)}`;
    $("g-cls").textContent = `games/${G.id}.py · class ${G.cls}`;
    $("g-ptext").textContent = "Prompt: " + G.promptText;
    $("g-mets").innerHTML = Object.entries(G.metrics).map(([k, v]) => `<span><b>${v.toFixed(2)}</b> ${k}</span>`).join("");
    $("rules").innerHTML = G.rules.map((r) => `<li>${r}</li>`).join("");
    $("side").innerHTML = [0, 1].map((p) =>
      `<button aria-pressed="${human === p}" data-side="${p}">${G.players[p]} (${p === 0 ? "first" : "second"})</button>`).join("");
    $("think").innerHTML = THINK.map((t) => `<button aria-pressed="${think === t}" data-t="${t}">${t} s</button>`).join("");
    const seen = new Set();
    $("legend").innerHTML = Object.values(G.pieces).filter((p) => {
      const k = p.kind + p.player; if (seen.has(k)) return false; seen.add(k); return true;
    }).map((p) => {
      const pl = G.players[p.player], n = p.name;
      const label = pl.toLowerCase().startsWith(n.toLowerCase()) ? n : `${pl} ${n.toLowerCase()}`;
      return `<span>${Board.legendIcon(p.kind, p.player)}${label}</span>`;
    }).join("")
      + (G.edges ? `<span>Coloured bars: the edges each side must link</span>` : "")
      + (G.promotionRows ? `<span>Coloured bars: the row where each side promotes</span>` : "")
      + (G.corners ? `<span>Dashed squares: the King's goal</span>` : "");
  }

  function render() {
    if (!S) return;
    const idx = index();
    const targets = new Map(), active = new Set(), placeGhost = new Map();
    if (myTurn()) {
      if (selected && idx.from.has(selected)) {
        for (const i of idx.from.get(selected)) {
          const m = S.moves[i], dx = Math.abs(m.to[0] - m.from[0]), dy = Math.abs(m.to[1] - m.from[1]);
          targets.set(key(m.to), { capture: G.id === "c4" && (dx === 2 || dy === 2) });
          active.add(key(m.to));
        }
      }
      for (const k of idx.from.keys()) active.add(k);
      for (const [k, list] of idx.placeAt) {
        active.add(k);
        const p = G.pieces[S.moves[list[0]].p];
        if (p) placeGhost.set(k, p);
        if (S.rows[+k.split(",")[1]][+k.split(",")[0]] !== "_") targets.set(k, { capture: true });
      }
    }
    Board.render($("board"), G, S, { targets, active, placeGhost, selected, hint });

    // extra (non-board) moves, e.g. a forced pass
    $("extra").innerHTML = myTurn() ? idx.other.map((i) => `<button class="btn" data-i="${i}">${S.moves[i].label}</button>`).join("") : "";

    // players
    $("players").innerHTML = [0, 1].map((p) => {
      const glyph = Object.values(G.pieces).find((x) => x.player === p);
      const turn = !S.over && S.player === p;
      return `<div class="prow${turn ? " turn" : ""}">${Board.legendIcon(glyph.kind, p).replace("<svg", '<svg width="20" height="20"')}
        <span class="who">${G.players[p]} · ${p === human ? "You" : "UCT"}</span><span class="goal">${G.goals[p]}</span></div>`;
    }).join("");
    $("info").innerHTML = G.info(S).map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");

    renderStatus();
    $("b-undo").disabled = busy || !S.ply;
    $("b-hint").disabled = !myTurn();
  }

  function renderStatus() {
    const st = $("status");
    st.classList.toggle("over", !!S.over);
    const dot = (p) => `<span class="dot" style="background:${Board.COLORS[p]}"></span>`;
    let main = "", stat = "";
    if (S.over) {
      const w = S.winner;
      main = w === null || w === undefined ? "Draw." : (w === human ? "You win." : "UCT wins.");
      if (S.stalled) main += " No legal moves left.";
      main += ` <button class="btn" id="again" style="margin-left:8px;padding:4px 12px">Play again</button>`;
    } else if (busy === "ai") {
      main = `<span class="spin"></span> UCT is thinking (${think} s)…`;
    } else if (busy === "hint") {
      main = `<span class="spin"></span> Looking for a hint…`;
    } else if (S.player === human) {
      main = `${dot(human)} Your move${selected ? `: choose a destination for ${Board.coord(...selected.split(",").map(Number))}` : ""}.`;
      if (S.moves.length && S.moves.every((m) => m.t === "other")) main = `${dot(human)} You have no placement available, so you must pass.`;
      if (hint && hint.text) main += ` <span class="stat">Hint: ${hint.text}</span>`;
    }
    if (S.last && S.last.who === "ai" && !busy) {
      const s = S.last.stats || {};
      stat = `UCT played ${moveText(S.last, G)}` + (s.forced ? " (only move)" : s.iterations ? ` · ${fmtInt(s.iterations)} simulations` + (s.value != null ? ` · estimate ${Math.round(s.value * 100)}%` : "") : "");
    }
    st.innerHTML = `<span class="grow">${main}</span>${stat ? `<span class="stat">${stat}</span>` : ""}`;
    const again = $("again"); if (again) again.onclick = () => newGame();
  }

  function renderLog() {
    // rebuilt from snapshots we have seen this game
    $("log").innerHTML = logEntries.map((e, n) =>
      `<span class="n">${n + 1}.</span><span class="p" style="color:${Board.COLORS[e.player]}">${G.players[e.player]}</span><span>${e.text}${e.who === "ai" ? "" : " <span class='small'>(you)</span>"}</span>`).join("");
    $("log").scrollTop = $("log").scrollHeight;
  }
  let logEntries = [];

  // ---------- flow ----------
  async function apply(snapshotPromise, t) {
    const snap = await snapshotPromise;
    if (t !== token) return false;
    S = snap;
    if (S.last) {
      logEntries = logEntries.slice(0, S.ply - 1);
      logEntries.push({ player: S.last.player, who: S.last.who, text: moveText(S.last, G) });
    } else logEntries = [];
    logEntries = logEntries.slice(0, S.ply);
    renderLog();
    return true;
  }

  async function step() {
    render();
    if (!S || S.over || S.player === human) return;
    const t = token;
    busy = "ai"; render();
    await new Promise((r) => setTimeout(r, 200));
    try { await apply(call("ai", think), t); }
    catch (err) { console.error(err); }
    if (t !== token) return;
    busy = false; step();
  }

  async function newGame(gid) {
    if (gid && (!G || gid !== G.id)) { G = GAMES[gid]; renderStatic(); }
    renderTabs();
    token++; const t = token;
    selected = null; hint = null; logEntries = [];
    busy = "new";
    const snap = await call("new_game", G.id);
    if (t !== token) return;
    S = snap; busy = false; renderLog(); step();
  }

  async function playIndex(i) {
    if (!myTurn()) return;
    const t = token;
    selected = null; hint = null; hideChoice();
    busy = "move";
    await apply(call("human", i), t);
    if (t !== token) return;
    busy = false; step();
  }

  // ---------- clicks ----------
  function hideChoice() { $("choice").hidden = true; }

  function showChoice(k, list) {
    const box = $("choice");
    box.innerHTML = list.map((i) => {
      const m = S.moves[i];
      const label = m.t === "place" ? `Place ${G.pieces[m.p] ? G.pieces[m.p].name.toLowerCase() : m.p}` : `Move to ${coord(m.to)}`;
      return `<button data-i="${i}">${label}</button>`;
    }).join("") + `<button data-cancel>Cancel</button>`;
    const geom = JSON.parse($("board").dataset.geom);
    const r = $("board").getBoundingClientRect(), wr = $("boardwrap").getBoundingClientRect();
    const [x, y] = k.split(",").map(Number), sc = r.width / geom.VW;
    box.style.left = Math.min(r.left - wr.left + (geom.L + (x + 1) * geom.C) * sc, wr.width - 160) + "px";
    box.style.top = (r.top - wr.top + (geom.T + y * geom.C) * sc) + "px";
    box.hidden = false;
  }

  function onCell(k) {
    if (!myTurn()) return;
    hideChoice();
    const idx = index();
    if (selected) {
      const cands = (idx.from.get(selected) || []).filter((i) => key(S.moves[i].to) === k);
      if (cands.length === 1) return playIndex(cands[0]);
      if (cands.length > 1) return showChoice(k, cands);
      if (idx.from.has(k) && k !== selected) { selected = k; return render(); }
      selected = null;
    }
    if (idx.from.has(k)) { selected = k; hint = null; return render(); }
    const pl = idx.placeAt.get(k);
    if (pl && pl.length === 1) return playIndex(pl[0]);
    if (pl && pl.length > 1) return showChoice(k, pl);
    render();
  }

  $("board").addEventListener("click", (e) => {
    const g = e.target.closest(".cell"); if (g) onCell(g.dataset.k);
  });
  $("choice").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    hideChoice();
    if (b.dataset.i !== undefined) playIndex(+b.dataset.i);
  });
  $("extra").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-i]"); if (b) playIndex(+b.dataset.i);
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") { hideChoice(); selected = null; render(); } });

  $("tabs").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-g]"); if (!b || !ready) return;
    if (location.hash !== "#" + b.dataset.g) history.replaceState(null, "", "#" + b.dataset.g);
    newGame(b.dataset.g);
  });
  $("side").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-side]"); if (!b || !ready) return;
    human = +b.dataset.side; store.set("side", human); renderStatic(); newGame();
  });
  $("think").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-t]"); if (!b) return;
    think = +b.dataset.t; store.set("think", think); renderStatic();
  });
  $("b-new").onclick = () => ready && newGame();
  $("b-undo").onclick = async () => {
    if (!ready || busy || !S.ply) return;
    const t = ++token; selected = null; hint = null; hideChoice();
    busy = "undo";
    const snap = await call("undo", human);
    if (t !== token) return;
    S = snap; logEntries = logEntries.slice(0, S.ply); renderLog();
    busy = false; step();
  };
  $("b-hint").onclick = async () => {
    if (!myTurn()) return;
    const t = token; busy = "hint"; selected = null; render();
    const res = await call("hint", Math.min(think, 2));
    if (t !== token) return;
    busy = false;
    if (res.index != null) {
      const m = S.moves[res.index];
      hint = { from: m.from ? key(m.from) : null, to: m.to ? key(m.to) : null, text: moveText(m, G) };
    }
    render();
  };

  function showLoadError(msg) {
    $("loadmsg").innerHTML = `<span class="err">Could not start Python in this browser: ${msg}. Try reloading, or use a recent Chrome, Firefox or Safari.</span>`;
  }

  // ---------- boot ----------
  const first = (location.hash || "").slice(1);
  G = GAMES[first] || GAMES.c1;
  renderTabs(); renderStatic();
  $("status").innerHTML = `<span class="spin"></span><span class="grow">Loading the Python engine…</span>`;
  call("init").then(() => {
    ready = true; $("loading").hidden = true; newGame(G.id);
  }).catch((err) => showLoadError(err.message));
  window.addEventListener("hashchange", () => {
    const g = location.hash.slice(1); if (ready && GAMES[g] && g !== G.id) newGame(g);
  });
})();
