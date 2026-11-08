/* SVG board renderer. Boardwalk coordinates are (x, y) with (0, 0) at the
   top-left; the UI labels columns a, b, c… and rows 1, 2, 3… from the top. */

(function () {
  const C = 60;                       // cell size (viewBox units)
  const COLORS = ["#A3262A", "#1C1C1C"];
  const EDGE = ["#7E1C1F", "#000000"];
  const PAPER = "#F8F6F2";
  const LETTERS = "abcdefghijklmnopqrstuvwxyz";

  const coord = (x, y) => LETTERS[x] + (y + 1);

  function pieceSVG(kind, player, cx, cy, r, extra = "") {
    const f = COLORS[player], s = EDGE[player];
    const disc = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${f}" stroke="${s}" stroke-width="1.5"/>`;
    switch (kind) {
      case "bridge": {
        const d = r * .82;
        return `<g ${extra}><rect x="${cx - d}" y="${cy - d}" width="${2 * d}" height="${2 * d}" fill="${f}" stroke="${s}" stroke-width="1.5" transform="rotate(45 ${cx} ${cy})"/>
          <path d="M${cx - r * .55} ${cy - r * .22}H${cx + r * .55}M${cx - r * .55} ${cy + r * .22}H${cx + r * .55}" stroke="${PAPER}" stroke-width="${r * .14}" stroke-linecap="square"/></g>`;
      }
      case "king": {
        const w = r * .62, h = r * .5, b = cy + r * .32;
        return `<g ${extra}>${disc}<path d="M${cx - w} ${b}L${cx - w} ${b - h}L${cx - w / 2} ${b - h * .55}L${cx} ${b - h * 1.25}L${cx + w / 2} ${b - h * .55}L${cx + w} ${b - h}L${cx + w} ${b}Z" fill="${PAPER}"/></g>`;
      }
      case "guard":
        return `<g ${extra}>${disc}<rect x="${cx - r * .38}" y="${cy - r * .38}" width="${r * .76}" height="${r * .76}" fill="none" stroke="${PAPER}" stroke-width="${r * .13}"/></g>`;
      case "ascended": {
        const pts = [];
        for (let i = 0; i < 10; i++) {
          const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * .25 : r * .58;
          pts.push(`${(cx + rr * Math.cos(a)).toFixed(1)},${(cy + rr * Math.sin(a)).toFixed(1)}`);
        }
        return `<g ${extra}>${disc}<polygon points="${pts.join(" ")}" fill="${PAPER}"/></g>`;
      }
      case "reserve":
        return `<g ${extra}>${disc}<path d="M${cx - r * .42} ${cy}H${cx + r * .42}M${cx} ${cy - r * .42}V${cy + r * .42}" stroke="${PAPER}" stroke-width="${r * .16}"/></g>`;
      default:
        return `<g ${extra}>${disc}</g>`;
    }
  }

  function legendIcon(kind, player) {
    return `<svg viewBox="0 0 20 20" aria-hidden="true">${pieceSVG(kind, player, 10, 10, 8)}</svg>`;
  }

  /* ui: {targets: Map key->{capture}, selected:"x,y"|null, hint:{from,to}|null,
          placeGhost: Map key->{kind,player}, active:Set key} */
  function render(svg, game, state, ui) {
    const W = state.w, H = state.h;
    const L = 30, T = 30, R = 14, B = 14;      // margins (labels left/top)
    const VW = L + W * C + R, VH = T + H * C + B;
    svg.setAttribute("viewBox", `0 0 ${VW} ${VH}`);
    const X = (x) => L + x * C, Y = (y) => T + y * C;
    const out = [];

    // goal edges
    const edges = Object.assign({}, game.edges || {});
    if (game.promotionRows) { edges.bottom = 0; edges.top = 1; }
    const bar = 6, gap = 3;
    if (edges.left !== undefined) out.push(`<rect x="${L - gap - bar}" y="${T}" width="${bar}" height="${H * C}" fill="${COLORS[edges.left]}"/>`);
    if (edges.right !== undefined) out.push(`<rect x="${L + W * C + gap}" y="${T}" width="${bar}" height="${H * C}" fill="${COLORS[edges.right]}"/>`);
    if (edges.top !== undefined) out.push(`<rect x="${L}" y="${T - gap - bar}" width="${W * C}" height="${bar}" fill="${COLORS[edges.top]}"/>`);
    if (edges.bottom !== undefined) out.push(`<rect x="${L}" y="${T + H * C + gap}" width="${W * C}" height="${bar}" fill="${COLORS[edges.bottom]}"/>`);

    // coordinate labels
    const lblOff = (edges.top !== undefined) ? 14 : 11;
    for (let x = 0; x < W; x++)
      out.push(`<text x="${X(x) + C / 2}" y="${T - lblOff}" text-anchor="middle" font-size="15" fill="#6E6E6E">${LETTERS[x]}</text>`);
    for (let y = 0; y < H; y++)
      out.push(`<text x="${(edges.left !== undefined) ? L - 15 : L - 12}" y="${Y(y) + C / 2 + 5}" text-anchor="end" font-size="15" fill="#6E6E6E">${y + 1}</text>`);

    const last = state.last;
    const lastCells = new Set();
    const captured = [];
    if (last) {
      if (last.from) lastCells.add(last.from.join(","));
      if (last.to) lastCells.add(last.to.join(","));
      for (const [cx, cy, before, after] of last.changed || []) {
        const k = cx + "," + cy;
        if (after === "_" && !(last.from && k === last.from.join(","))) captured.push([cx, cy, before]);
      }
    }
    const corners = game.corners ? new Set(["0,0", `${W - 1},0`, `0,${H - 1}`, `${W - 1},${H - 1}`]) : null;

    // cells
    for (let y = 0; y < H; y++) {
      const row = state.rows[y];
      for (let x = 0; x < W; x++) {
        const k = x + "," + y, ch = row[x];
        if (ch === " ") continue;                       // outside play
        let fill = "#F4F0E8";
        if (corners && corners.has(k)) fill = "#F0DCD8";
        if (lastCells.has(k)) fill = "#E6D9C6";
        const act = ui.active && ui.active.has(k);
        const parts = [`<rect x="${X(x)}" y="${Y(y)}" width="${C}" height="${C}" fill="${fill}" stroke="#DCD7CE" stroke-width="1"/>`];
        if (corners && corners.has(k))
          parts.push(`<rect x="${X(x) + 6}" y="${Y(y) + 6}" width="${C - 12}" height="${C - 12}" fill="none" stroke="#A3262A" stroke-width="1.2" stroke-dasharray="4 3"/>`);
        const p = game.pieces[ch];
        if (p) parts.push(pieceSVG(p.kind, p.player, X(x) + C / 2, Y(y) + C / 2, C * .34));
        if (ui.selected === k)
          parts.push(`<rect x="${X(x) + 2}" y="${Y(y) + 2}" width="${C - 4}" height="${C - 4}" fill="none" stroke="#A3262A" stroke-width="3"/>`);
        const g = ui.placeGhost && ui.placeGhost.get(k);
        if (g && !p) parts.push(pieceSVG(g.kind, g.player, X(x) + C / 2, Y(y) + C / 2, C * .34, `class="ghost"`));
        const t = ui.targets && ui.targets.get(k);
        if (t) {
          if (p || t.capture) parts.push(`<circle cx="${X(x) + C / 2}" cy="${Y(y) + C / 2}" r="${C * .44}" fill="none" stroke="#1C1C1C" stroke-opacity=".55" stroke-width="2.5"/>`);
          else parts.push(`<circle cx="${X(x) + C / 2}" cy="${Y(y) + C / 2}" r="${C * .12}" fill="#1C1C1C" fill-opacity=".35"/>`);
        }
        if (ui.hint && (ui.hint.from === k || ui.hint.to === k))
          parts.push(`<rect x="${X(x) + 3}" y="${Y(y) + 3}" width="${C - 6}" height="${C - 6}" fill="none" stroke="#A3262A" stroke-width="2.5" stroke-dasharray="6 4"/>`);
        out.push(`<g class="cell${act ? " act" : ""}${t ? " tgt" : ""}" data-k="${k}"><title>${coord(x, y)} (x=${x}, y=${y})</title>${parts.join("")}</g>`);
      }
    }

    // captured markers from the last move
    for (const [cx, cy] of captured) {
      const mx = X(cx) + C / 2, my = Y(cy) + C / 2, d = C * .14;
      out.push(`<path d="M${mx - d} ${my - d}L${mx + d} ${my + d}M${mx + d} ${my - d}L${mx - d} ${my + d}" stroke="#A3262A" stroke-width="2.5" pointer-events="none"/>`);
    }
    // arrow for the last move
    if (last && last.from && last.to) {
      const [ax, ay] = last.from, [bx, by] = last.to;
      out.push(`<line x1="${X(ax) + C / 2}" y1="${Y(ay) + C / 2}" x2="${X(bx) + C / 2}" y2="${Y(by) + C / 2}" stroke="#A3262A" stroke-opacity=".45" stroke-width="3" stroke-linecap="round" pointer-events="none"/>`);
    }

    svg.innerHTML = `<style>.ghost{opacity:0;pointer-events:none}.cell.act:hover .ghost{opacity:.35}</style>` + out.join("");
    svg.dataset.geom = JSON.stringify({ VW, VH, L, T, C });
  }

  window.Board = { render, pieceSVG, legendIcon, coord, COLORS };
})();
