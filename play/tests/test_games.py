"""Smoke test: every game finishes when UCT (short time limit) plays a random
opponent, through the same JSON bridge the browser uses.  python tests/test_games.py"""
import json, pathlib, random, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "py"))
import bridge

random.seed(0)
for gid in ["c1", "c2", "c3", "c4"]:
    s = json.loads(bridge.new_game(gid))
    while not s["over"]:
        if s["player"] == 0:
            s = json.loads(bridge.ai(0.05))
        else:
            s = json.loads(bridge.human(random.randrange(len(s["moves"]))))
    print(f"{gid}: finished after {s['ply']} plies, winner {s['winner']}")
