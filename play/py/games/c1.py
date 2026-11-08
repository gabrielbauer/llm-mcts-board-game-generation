from boardwalk import GameRules, GameState, Board, Position, Move, Placement
import random
import math


class Bridge(GameRules):
    def __init__(self):
        # No fixed configuration constants needed beyond those implied by the rules.
        pass

    # ------------------------------------------------------------------
    #  Initial state
    # ------------------------------------------------------------------
    def initial_state(self):
        initial_layout = (
            "______\n"
            "______\n"
            "______\n"
            "______\n"
            "______\n"
            "______"
        )
        board = Board((6, 6), initial_layout)
        extra = {
            "bridge_reserve_0": 5,
            "bridge_reserve_1": 5,
            "passes": 0,
        }
        return GameState(board=board, current_player=0, turn=0, extra=extra)

    # ------------------------------------------------------------------
    #  Legal moves
    # ------------------------------------------------------------------
    class _Pass:
        """Sentinel action representing a forced pass when no placements exist."""
        pass

    def legal_moves(self, state):
        board = state.board
        extra = state.extra
        player = state.current_player
        moves = []

        if player == 0:
            # Regular placements on empty squares
            for pos in board.empty_positions():
                moves.append(Placement("A", pos))
            # Bridge placements on opponent-occupied squares
            if extra["bridge_reserve_0"] > 0:
                for pos, piece in board.pieces():
                    if piece in ("B", "b"):
                        moves.append(Placement("a", pos))
        else:  # player == 1
            for pos in board.empty_positions():
                moves.append(Placement("B", pos))
            if extra["bridge_reserve_1"] > 0:
                for pos, piece in board.pieces():
                    if piece in ("A", "a"):
                        moves.append(Placement("b", pos))

        # If no placements are possible, the player must pass.
        if not moves:
            moves.append(self._Pass())
        return moves

    # ------------------------------------------------------------------
    #  Apply an action
    # ------------------------------------------------------------------
    def apply(self, state, action):
        if isinstance(action, Placement):
            piece = action.piece
            pos = action.position
            new_extra = dict(state.extra)

            if piece in ("A", "B"):
                # Regular placement
                new_board = state.board.with_piece(pos, piece)
                new_extra["passes"] = 0
            else:  # piece in ("a", "b")
                # Bridge placement – replace opponent's piece
                new_board = state.board.with_piece(pos, piece)
                new_extra["passes"] = 0
                if piece == "a":
                    new_extra["bridge_reserve_0"] -= 1
                else:
                    new_extra["bridge_reserve_1"] -= 1

            return GameState(
                board=new_board,
                current_player=1 - state.current_player,
                turn=state.turn + 1,
                extra=new_extra,
            )
        else:
            # Pass action – no board change, only extra and turn updated
            new_extra = dict(state.extra)
            new_extra["passes"] = new_extra.get("passes", 0) + 1
            return GameState(
                board=state.board,
                current_player=1 - state.current_player,
                turn=state.turn + 1,
                extra=new_extra,
            )

    # ------------------------------------------------------------------
    #  Terminal check
    # ------------------------------------------------------------------
    def is_terminal(self, state):
        if self.winner(state) is not None:
            return True
        # Draw after two consecutive passes (both players have no moves)
        if state.extra.get("passes", 0) >= 2:
            return True
        # If there is at least one legal action (including pass), game continues
        return False

    # ------------------------------------------------------------------
    #  Winner detection
    # ------------------------------------------------------------------
    def winner(self, state):
        board = state.board
        # Player 0 wins by connecting left edge (x=0) to right edge (x=5)
        # using only their own pieces ('A' or 'a')
        if self._has_path(board, {"A", "a"}, start_x=0, target_x=board.width - 1, axis="x"):
            return 0
        # Player 1 wins by connecting top edge (y=0) to bottom edge (y=5)
        # using only their own pieces ('B' or 'b')
        if self._has_path(board, {"B", "b"}, start_y=0, target_y=board.height - 1, axis="y"):
            return 1
        return None

    def _has_path(self, board, own_pieces, start_x=None, target_x=None,
                  start_y=None, target_y=None, axis="x"):
        """
        BFS from every cell on the start edge that contains an own piece.
        Returns True if any reachable cell lies on the target edge.
        axis == 'x'  → start/target are x coordinates (left-right connection)
        axis == 'y'  → start/target are y coordinates (top-bottom connection)
        """
        width, height = board.width, board.height
        visited = set()

        # Determine starting positions
        if axis == "x":
            start_candidates = [Position(start_x, y) for y in range(height)]
            target_edge = target_x
            def is_target(pos):
                return pos.x == target_edge
        else:  # axis == "y"
            start_candidates = [Position(x, start_y) for x in range(width)]
            target_edge = target_y
            def is_target(pos):
                return pos.y == target_edge

        from collections import deque
        queue = deque()
        for pos in start_candidates:
            if board[pos] in own_pieces:
                visited.add((pos.x, pos.y))
                queue.append(pos)

        while queue:
            pos = queue.popleft()
            if is_target(pos):
                return True
            # Explore orthogonal neighbours
            for nb in board.orthogonal_neighbors(pos):
                if board[nb] in own_pieces and (nb.x, nb.y) not in visited:
                    visited.add((nb.x, nb.y))
                    queue.append(nb)
        return False