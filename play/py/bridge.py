"""
JSON bridge between the browser UI and the Python engine.

The UI never sees Python objects: every call returns a JSON string with the
board, the legal moves (indexed, so the UI answers with an index), the last
move and the cells it changed. The game files and uct.py are used exactly as
the pipeline produced/used them.
"""

import importlib
import json
import time

from boardwalk import GameRules, Move, Placement
from uct import UCTAgent

GAMES = {"c1": "games.c1", "c2": "games.c2", "c3": "games.c3", "c4": "games.c4"}


def _rules_class(module):
    for value in vars(module).values():
        if isinstance(value, type) and issubclass(value, GameRules) and value is not GameRules:
            return value
    raise ValueError("no GameRules subclass in " + module.__name__)


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _move_json(move):
    if isinstance(move, Placement):
        return {"t": "place", "p": move.piece, "to": [move.position.x, move.position.y]}
    if isinstance(move, Move):
        return {"t": "move", "from": [move.start.x, move.start.y], "to": [move.end.x, move.end.y]}
    name = type(move).__name__.strip("_") or "Pass"
    return {"t": "other", "label": name}


class StatsUCT(UCTAgent):
    """UCTAgent with the same search, plus a count of iterations and the
    root statistics, so the UI can show what the agent saw."""

    def search(self, game, state):
        is_terminal = game.is_terminal(state)
        terminal_winner = game.winner(state) if is_terminal else None
        root = self._make_node(state, game, is_terminal=is_terminal, terminal_winner=terminal_winner)
        if root.is_terminal or len(root.untried_actions) <= 1:
            action = root.untried_actions[0] if root.untried_actions else None
            return action, {"iterations": 0, "forced": True}

        iterations = 0
        deadline = time.time() + self.time_limit
        while time.time() < deadline:
            node = self._select(root)
            node, winner = self._expand(node, game)
            if winner is None and not node.is_terminal:
                winner, steps = self._rollout(node, game)
            else:
                steps = 0
            self._backpropagate(node, winner, steps)
            iterations += 1

        action = self._best_action(root)
        child = root.children.get(action)
        value = (child.wins / child.visits) if child and child.visits else None
        return action, {"iterations": iterations, "value": value,
                        "visits": child.visits if child else 0, "forced": False}


class Session:
    def __init__(self, gid):
        module = importlib.import_module(GAMES[gid])
        self.gid = gid
        self.game = _rules_class(module)()
        self.history = []          # list of (state, move_json, changed)
        self.state = self.game.initial_state()
        self._legal = None
        self.last = None

    # -- core ---------------------------------------------------------------

    def legal(self):
        if self._legal is None:
            self._legal = [] if self.game.is_terminal(self.state) else list(self.game.legal_moves(self.state))
        return self._legal

    def _apply(self, move, who, stats=None):
        before = self.state.board
        player = self.state.current_player
        new_state = self.game.apply(self.state, move)
        after = new_state.board
        changed = []
        if after is not before:
            b, a = before._cells, after._cells
            w = before.width
            for i in range(len(b)):
                if b[i] != a[i]:
                    changed.append([i % w, i // w, b[i], a[i]])
        mj = _move_json(move)
        mj.update({"player": player, "who": who, "changed": changed})
        if stats:
            mj["stats"] = stats
        self.history.append((self.state, self.last))
        self.state = new_state
        self.last = mj
        self._legal = None

    def snapshot(self):
        s = self.state
        moves = self.legal()
        terminal = self.game.is_terminal(s)
        stalled = (not terminal) and not moves
        over = terminal or stalled
        winner = self.game.winner(s) if over else None
        extra = {k: v for k, v in s.extra.items() if k != "history"}
        return json.dumps({
            "game": self.gid,
            "rows": s.board.rows(),
            "w": s.board.width, "h": s.board.height,
            "player": s.current_player, "turn": s.turn, "ply": len(self.history),
            "over": over, "stalled": stalled, "winner": winner,
            "moves": [_move_json(m) for m in moves],
            "last": self.last,
            "extra": _jsonable(extra),
        })

    # -- commands -----------------------------------------------------------

    def human(self, index):
        moves = self.legal()
        self._apply(moves[int(index)], "human")
        return self.snapshot()

    def ai(self, seconds):
        agent = StatsUCT(time_limit=float(seconds))
        move, stats = agent.search(self.game, self.state)
        if move is None:
            return self.snapshot()
        self._apply(move, "ai", stats)
        return self.snapshot()

    def hint(self, seconds):
        agent = StatsUCT(time_limit=float(seconds))
        move, stats = agent.search(self.game, self.state)
        moves = self.legal()
        index = next((i for i, m in enumerate(moves) if m is move or m == move), None)
        return json.dumps({"index": index, "stats": stats})

    def undo(self, human_player):
        """Go back to the previous position where the human was to move."""
        human_player = int(human_player)
        while self.history:
            self.state, self.last = self.history.pop()
            self._legal = None
            if self.state.current_player == human_player:
                break
        return self.snapshot()


_session = None


def new_game(gid):
    global _session
    _session = Session(gid)
    return _session.snapshot()


def human(index):
    return _session.human(index)


def ai(seconds):
    return _session.ai(seconds)


def hint(seconds):
    return _session.hint(seconds)


def undo(human_player):
    return _session.undo(human_player)
