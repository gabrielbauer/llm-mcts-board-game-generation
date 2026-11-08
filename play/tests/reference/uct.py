import math
import random
import time
from typing import Any, Optional

# NOTE: expects Boardwalk 2.0's GameState / GameRules (board.py / rules.py).
from app.games.boardwalk import GameState, GameRules


class UCTNode:
    __slots__ = (
        "state", "parent", "action", "children",
        "visits", "wins", "player_to_move", "untried_actions", "is_terminal",
        "terminal_winner"
    )

    def __init__(
        self,
        state: "GameState",
        untried_actions: list[Any],
        is_terminal: bool,
        parent: Optional["UCTNode"] = None,
        action: Optional[Any] = None,
        terminal_winner: Optional[int] = None
    ):
        self.state           = state
        self.parent          = parent
        self.action           = action
        self.children:       dict[Any, "UCTNode"] = {}
        self.visits:         int   = 0
        self.wins:           float = 0.0
        # CHANGED: GameState is a frozen dataclass, not a dict.
        self.player_to_move: int   = state.current_player
        self.untried_actions       = untried_actions
        self.is_terminal           = is_terminal
        self.terminal_winner       = terminal_winner

    def uct_score(self, log_parent_visits: float, C: float) -> float:
        if self.visits == 0:
            return float("inf")
        return self.wins / self.visits + C * math.sqrt(log_parent_visits / self.visits)

    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0


class UCTAgent:
    """
    Mathematically corrected UCT agent with zero-sum depth discounting.
    Actively hunts faster wins and deliberately delays losses.

    Migrated to Boardwalk 2.0's GameRules API:
      - game.legal_moves(state)   replaces game.possible_moves(state)
      - game.apply(state, move)   + game.is_terminal(state) + game.winner(state)
        together replace game.next_state(state, action)
    """

    def __init__(
        self,
        time_limit: Optional[float] = 1.0,
        iterations: Optional[int] = None,
        C: float = 1.4,
        max_rollout_steps: int = 200,
        discount_factor: float = 0.99
    ):
        self.time_limit = time_limit
        self.iterations = iterations
        self.C = C
        self.max_rollout_steps = max_rollout_steps
        self.discount_factor = discount_factor

    def get_action(self, game: "GameRules", state: "GameState"):
        # CHANGED: the old API let next_state() report terminal/winner lazily.
        # GameRules has no combined call, so the root's terminal status has to
        # be established explicitly before building the node.
        is_terminal = game.is_terminal(state)
        terminal_winner = game.winner(state) if is_terminal else None

        root = self._make_node(
            state, game,
            is_terminal=is_terminal,
            terminal_winner=terminal_winner,
        )

        # Short-circuit if there is only 1 legal move (or 0)
        if root.is_terminal or len(root.untried_actions) <= 1:
            return root.untried_actions[0] if root.untried_actions else None

        deadline = time.time() + self.time_limit

        while time.time() < deadline:
            node = self._select(root)
            node, winner = self._expand(node, game)

            # Handling the updated rollout signature (winner, steps)
            if winner is None and not node.is_terminal:
                winner, steps = self._rollout(node, game)
            else:
                steps = 0

            self._backpropagate(node, winner, steps)

        return self._best_action(root)

    def _make_node(self, state, game, parent=None, action=None, is_terminal=False, terminal_winner=None):
        # CHANGED: game.possible_moves(state) -> game.legal_moves(state).
        # Still wrapped in list() since legal_moves() may return moves backed
        # by a generator/view in some implementations, and we mutate this
        # list later via .remove().
        moves = [] if is_terminal else list(game.legal_moves(state))

        return UCTNode(
            state=state,
            untried_actions=moves,
            is_terminal=is_terminal,
            parent=parent,
            action=action,
            terminal_winner=terminal_winner
        )

    def _select(self, node: UCTNode) -> UCTNode:
        while not node.is_terminal and node.is_fully_expanded() and node.children:
            log_n = math.log(node.visits) if node.visits > 0 else 0.0
            node  = max(node.children.values(),
                        key=lambda child: child.uct_score(log_n, self.C))
        return node

    def _expand(self, node: UCTNode, game: "GameRules") -> tuple["UCTNode", Optional[int]]:
        if node.is_terminal or not node.untried_actions:
            return node, node.terminal_winner

        action = random.choice(node.untried_actions)
        node.untried_actions.remove(action)

        # CHANGED: game.next_state(state, action) -> game.apply() + is_terminal() + winner()
        new_state, finished, winner = self._next_state(game, node.state, action)

        child = self._make_node(new_state, game,
                                parent=node, action=action, is_terminal=finished,
                                terminal_winner=winner)
        node.children[action] = child

        return child, winner

    def _rollout(self, node: UCTNode, game: "GameRules") -> tuple[Optional[int], int]:
        state    = node.state
        finished = node.is_terminal
        steps    = 0
        winner   = None

        while not finished and steps < self.max_rollout_steps:
            # CHANGED: game.possible_moves(state) -> game.legal_moves(state)
            actions = list(game.legal_moves(state))
            if not actions:
                break

            # CHANGED: game.next_state(...) -> _next_state() helper
            state, finished, winner = self._next_state(
                game,
                state,
                random.choice(actions)
            )
            steps += 1

            if finished:
                break

        return winner, steps

    def _next_state(
        self,
        game: "GameRules",
        state: "GameState",
        action: Any,
    ) -> tuple["GameState", bool, Optional[int]]:
        """
        Bridges the old next_state()-style tuple return onto Boardwalk 2.0's
        split apply() / is_terminal() / winner() API. Uses game.apply()
        directly (not play_move()) since the action is already known-legal,
        avoiding a redundant legality check on every simulation step.
        """
        new_state = game.apply(state, action)
        finished = game.is_terminal(new_state)
        winner = game.winner(new_state) if finished else None
        return new_state, finished, winner

    def _backpropagate(self, node: UCTNode, winner: Optional[int], steps: int) -> None:
        # Distance starts at the rollout length
        current_steps = steps

        while node is not None:
            node.visits += 1
            if node.parent is not None:
                # Calculate the centered discount based on distance from the current node
                discounted_reward = 0.5 * (self.discount_factor ** current_steps)

                if winner is None:
                    node.wins += 0.5  # True draw
                elif node.parent.player_to_move == winner:
                    node.wins += 0.5 + discounted_reward  # Win (decayed towards 0.5)
                else:
                    node.wins += 0.5 - discounted_reward  # Loss (decayed towards 0.5)

            else:
                if winner is None:
                    node.wins += 0.5
                elif node.player_to_move == winner:
                    node.wins += 1.0

            node = node.parent
            # Increase distance by 1 for every step we move up the tree
            current_steps += 1

    def _best_action(self, root: UCTNode) -> Optional[Any]:
        if root.children:
            max_visits = max(n.visits for n in root.children.values())
            best_nodes = [n for n in root.children.values() if n.visits == max_visits]
            return random.choice(best_nodes).action
        return random.choice(root.untried_actions) if root.untried_actions else None