"""Replay seeded random games on the original Boardwalk 2.0 (NumPy) and on
the browser port; every legal-move list and every state must match.

usage: python tests/test_equivalence.py [games]   (needs numpy for the reference engine)
"""
import importlib, random, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1] / "py"

def load(engine_dir, gid):
    for m in [k for k in sys.modules if k == "boardwalk" or k.startswith("games")]:
        del sys.modules[m]
    sys.path[:0] = [str(engine_dir), str(ROOT)]
    try:
        mod = importlib.import_module(f"games.{gid}")
    finally:
        del sys.path[:2]
    from boardwalk import GameRules
    cls = [v for v in vars(mod).values() if isinstance(v, type) and issubclass(v, GameRules) and v is not GameRules][0]
    return cls()

def trace(game, seed, max_plies=400):
    rng = random.Random(seed); s = game.initial_state(); out = []
    for _ in range(max_plies):
        term = game.is_terminal(s)
        out.append((s.board.to_string(), s.current_player, s.turn, term, game.winner(s) if term else None))
        if term: break
        mv = game.legal_moves(s)
        out.append(tuple(str(m) if hasattr(m, "__dataclass_fields__") else type(m).__name__ for m in mv))
        if not mv: break
        s = game.apply(s, mv[rng.randrange(len(mv))])
    return out

if __name__ == "__main__":
    orig = pathlib.Path(__file__).resolve().parent / "reference"
    games = sys.argv[1:] or ["c1", "c2", "c3", "c4"]
    for gid in games:
        a, b = load(orig, gid), load(ROOT, gid)
        n = 200
        for seed in range(n):
            ta, tb = trace(a, seed), trace(b, seed)
            assert ta == tb, f"{gid} seed {seed} differs"
        print(f"{gid}: {n} random games identical")
