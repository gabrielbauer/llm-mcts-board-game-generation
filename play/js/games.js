/* Presentation metadata for the four games. The rules text describes what
   the generated code actually does (py/games/*.py), not the original prompt. */

const RED = 0, BLACK = 1;

window.GAMES = {
  c1: {
    id: "c1", prompt: "C1", title: "Bridge", cls: "Bridge",
    model: "DeepSeek-V4-Pro", modelColor: "#2a78d6", fitness: 0.819, metrics: { completion: 0.75, balance: 0.867, agency: 0.979, coverage: 0.728 },
    promptText: "Build a continuous path connecting opposite sides of the board while using a limited number of bridge tiles to cross opponent paths.",
    players: ["Red", "Black"],
    goals: ["connect left ↔ right", "connect top ↔ bottom"],
    pieces: {
      A: { player: RED, kind: "stone", name: "stone" },
      a: { player: RED, kind: "bridge", name: "bridge" },
      B: { player: BLACK, kind: "stone", name: "stone" },
      b: { player: BLACK, kind: "bridge", name: "bridge" },
    },
    edges: { left: RED, right: RED, top: BLACK, bottom: BLACK },
    rules: [
      "Red moves first and wins by linking the left and right edges with an orthogonally connected chain of red pieces. Black links the top and bottom edges.",
      "On your turn, place a stone on any empty square.",
      "Or spend one of your 5 bridges: put it on an opponent's stone or bridge. It replaces that piece and counts as part of your chain.",
      "A player who cannot place must pass; two passes in a row end the game in a draw.",
    ],
    info: (s) => [
      ["Red bridges left", s.extra.bridge_reserve_0],
      ["Black bridges left", s.extra.bridge_reserve_1],
    ],
    labels: { place: (m, g) => m.p === m.p.toLowerCase() ? "Bridge" : "Stone" },
  },

  c2: {
    id: "c2", prompt: "C2", title: "Ortho Surround", cls: "OrthoSurround6",
    model: "Qwen3.6-Plus", modelColor: "#eda100", fitness: 0.982, metrics: { completion: 1.0, balance: 0.95, agency: 1.0, coverage: 0.978 },
    promptText: "6×6 grid, unlimited pieces; capture by surrounding opponent pieces on all orthogonal sides; the player with more pieces when the board is full wins.",
    players: ["Red", "Black"],
    goals: ["more pieces at the end", "more pieces at the end"],
    pieces: {
      A: { player: RED, kind: "stone", name: "piece" },
      B: { player: BLACK, kind: "stone", name: "piece" },
    },
    rules: [
      "Red moves first. On your turn, either place a piece from your reserve on any empty square, or slide one of your pieces one square orthogonally into an empty square.",
      "After your move, every opponent piece with at least 3 orthogonal neighbours occupied by your pieces is captured. An edge piece needs all 3 neighbours; a corner piece (2 neighbours) can never be captured.",
      "Reserves are uneven, as generated: Red 19, Black 21.",
      "The game ends when the board is full, after 120 turns, or when neither player can move. The player with more pieces wins; a tie goes to Black.",
    ],
    info: (s) => [
      ["Red reserve", s.extra.reserves.A],
      ["Black reserve", s.extra.reserves.B],
      ["Turn", `${s.extra.turn_counter} / 120`],
    ],
  },

  c3: {
    id: "c3", prompt: "C3", title: "Guard the King", cls: "GuardTheKing",
    model: "Claude-Sonnet-5", modelColor: "#eb6834", fitness: 0.165, metrics: { completion: 1.0, balance: 0.05, agency: 0.997, coverage: 0.45 },
    promptText: "Asymmetric 5×5 game: a King in the centre wins by reaching a corner; four Guards win by immobilising it. Pieces slide orthogonally until blocked.",
    players: ["King", "Guards"],
    goals: ["reach a corner", "trap the King"],
    pieces: {
      A: { player: RED, kind: "king", name: "King" },
      B: { player: BLACK, kind: "guard", name: "Guard" },
    },
    corners: true,
    rules: [
      "The generated game drifts from the prompt: a 7×7 board, eight Guards, and a King that steps one square.",
      "The King (Red) moves first, one square orthogonally into an empty square, and wins on reaching any corner.",
      "On their turn, the Guards (Black) slide one guard orthogonally any number of empty squares.",
      "The Guards win when the King cannot move. The King also wins if the Guards have no move. 300 turns without a result is a draw.",
      "Low fitness (0.165): in self-play the King almost always escapes, so the game is badly unbalanced.",
    ],
    info: (s) => [["Turn", `${s.extra.turn_count} / 300`]],
  },

  c4: {
    id: "c4", prompt: "C4", title: "Ascension Checkers", cls: "AscensionCheckers",
    model: "Qwen3.6-Plus", modelColor: "#eda100", fitness: 0.870, metrics: { completion: 0.8, balance: 1.0, agency: 0.801, coverage: 0.911 },
    promptText: "6×6, six Basic pieces per side; step forward, capture by jumping diagonally; reaching the far row promotes to Ascended; the model had to invent one extra mechanic.",
    players: ["Red", "Black"],
    goals: ["capture all Black pieces", "capture all Red pieces"],
    pieces: {
      A: { player: RED, kind: "stone", name: "Basic" },
      a: { player: RED, kind: "ascended", name: "Ascended" },
      V: { player: RED, kind: "reserve", name: "Reinforcement" },
      B: { player: BLACK, kind: "stone", name: "Basic" },
      b: { player: BLACK, kind: "ascended", name: "Ascended" },
      C: { player: BLACK, kind: "reserve", name: "Reinforcement" },
    },
    promotionRows: { 0: 5, 1: 0 },
    rules: [
      "Red starts on the top row and moves first; Black starts on the bottom row.",
      "Basic pieces step one square straight forward, or capture by jumping diagonally forward over an opponent into the empty square behind. If any capture is available, you must capture.",
      "A piece reaching the far row becomes Ascended: it steps or jumps in any of the 8 directions.",
      "Invented mechanic (reinforcement): once per game, with 2 or fewer pieces left, you may place a reinforcement in your two home rows. It moves like a Basic piece.",
      "You win by capturing all enemy pieces, or when the opponent has no move. After turn 30, a lead of 2+ pieces held for two consecutive turns also wins. At turn 80 the higher score wins, with Ascended pieces counting double.",
    ],
    info: (s) => [
      ["Red reinforcement", s.extra.reserves["0"] ? "available" : "used"],
      ["Black reinforcement", s.extra.reserves["1"] ? "available" : "used"],
      ["Turn", `${s.extra.turn_count} / 80`],
    ],
  },
};
