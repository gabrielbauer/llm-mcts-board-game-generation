# Play the generated games

A browser demo of the best board games produced by the LLM agent pipeline in
**"Generating Board Games with MCTS and LLM Agents"** (Gabriel Bauer de Oliveira
and Anderson Rocha Tavares, AIIDE 2026). You play each game against the same
UCT agent the pipeline used to evaluate it.

Everything runs in the browser. Python runs on [Pyodide](https://pyodide.org)
inside a Web Worker, so there is no server or build step, and the page works on
any static host (GitHub Pages included).

| Prompt | Game (class) | Model | Fitness |
|---|---|---|---|
| C1 | `Bridge` | DeepSeek-V4-Pro | 0.819 |
| C2 | `OrthoSurround6` | Qwen3.6-Plus | 0.982 |
| C3 | `GuardTheKing` | Claude-Sonnet-5 | 0.165 |
| C4 | `AscensionCheckers` | Qwen3.6-Plus | 0.870 |

The table lists, for each prompt, the highest-fitness game across all four
models. Each game's run id, prompt and metrics are in `py/games/provenance.json`.

## What runs

- `py/games/c*.py` is the game code exactly as the pipeline produced it. The only
  change is the import line, `app.games.boardwalk` → `boardwalk`.
- `py/uct.py` is the pipeline's `UCTAgent`, again with only the import changed.
  `bridge.py` subclasses it to count iterations and report the root statistics
  that the UI shows. The search itself is the same.
- `py/boardwalk.py` is a dependency-free port of the Boardwalk 2.0 engine. It
  keeps the same API, coordinates and iteration order, but stores the board in a
  flat tuple instead of a NumPy array. That removes the NumPy download (about
  8 MB) and makes rollouts 1.5–6× faster.
  `tests/test_equivalence.py` replays 200 seeded random games per game on the
  original engine (`tests/reference/`) and on the port, and checks that every
  state and every legal-move list is identical.
- `py/bridge.py` is the JSON interface between the UI and the engine. It handles
  legal moves as an indexed list, the last move with the cells it changed, undo,
  and hints.

Python in the browser runs at roughly half the speed of native CPython. To match
the paper's tester (1 s per move, native Python, NumPy engine), use about 2 s per
move in the demo.

## Interface

- An SVG board with coordinates. Columns are a, b, c… from left to right and
  rows are 1, 2, 3… from top to bottom. Hovering a square shows its Boardwalk
  `(x, y)`.
- Click to place a piece. To move one, click it and then click a highlighted
  destination. If a square allows more than one move, a small menu lets you
  choose. Moves that are not on the board, such as a forced pass, appear as
  buttons.
- The board marks the last move with captured squares crossed out, shows goal
  edges, promotion rows and goal corners, and draws a ghost piece when you hover
  a placement.
- You can choose your side and UCT's thinking time (0.5 / 1 / 2 / 4 s), and use
  undo and a UCT hint. The status line shows UCT's simulation count and win
  estimate.
- The rules panel describes what each generated file actually does. That is not
  always what the prompt asked for (C3 in particular).

## Run locally

```bash
python -m http.server 8000      # from the repository root
# open http://localhost:8000/
```

The page loads Pyodide 0.27.7 from jsDelivr. To test offline, `npm i pyodide@0.27.7`,
serve `node_modules/pyodide` next to the project, and open
`index.html?pyodide=/path/to/pyodide/`.

## Tests

```bash
python tests/test_games.py          # every game finishes (UCT vs random, via the bridge)
python tests/test_equivalence.py    # browser engine == original Boardwalk 2.0 (needs numpy)
```

## Layout

```
index.html          page
css/style.css       styles (IBM Plex Sans, Source Serif 4; fonts/ bundled)
js/app.js           UI controller: turn loop, clicks → legal-move index
js/board.js         SVG renderer
js/games.js         per-game presentation: pieces, goals, rules text
js/worker.js        Pyodide worker
py/                 engine, UCT agent, bridge, generated games
tests/              smoke test, equivalence test, reference engine
```

## Citation

```bibtex
@inproceedings{bauer2026generating,
  title     = {Generating Board Games with MCTS and LLM Agents},
  author    = {Bauer de Oliveira, Gabriel and Tavares, Anderson Rocha},
  booktitle = {Proceedings of the AAAI Conference on Artificial Intelligence and Interactive Digital Entertainment (AIIDE)},
  year      = {2026}
}
```
