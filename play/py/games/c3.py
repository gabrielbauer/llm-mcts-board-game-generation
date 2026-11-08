from boardwalk import GameRules, GameState, Board, Position, Move, Placement
import random
import math


class GuardTheKing(GameRules):
    def __init__(self):
        self.MAX_TURNS = 300
        self.DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        self.CORNERS = [(0, 0), (6, 0), (0, 6), (6, 6)]

    def initial_state(self):
        initial_layout = (
            "___B___\n"
            "_B___B_\n"
            "_______\n"
            "B__A__B\n"
            "_______\n"
            "_B___B_\n"
            "___B___\n"
        )
        board = Board((7, 7), initial_layout)
        return GameState(board=board, current_player=0, turn=0, extra={"turn_count": 0})

    def _slide_destinations(self, board, pos):
        destinations = []
        x, y = pos.x, pos.y
        for dx, dy in self.DIRS:
            k = 1
            while True:
                nx, ny = x + dx * k, y + dy * k
                if nx < 0 or nx >= board.width or ny < 0 or ny >= board.height:
                    break
                candidate = Position(nx, ny)
                if board[candidate] != board.BLANK:
                    break
                destinations.append(candidate)
                k += 1
        return destinations

    def _step_destinations(self, board, pos):
        destinations = []
        x, y = pos.x, pos.y
        for dx, dy in self.DIRS:
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= board.width or ny < 0 or ny >= board.height:
                continue
            candidate = Position(nx, ny)
            if board[candidate] == board.BLANK:
                destinations.append(candidate)
        return destinations

    def _find_piece_positions(self, board, piece):
        return [pos for pos, p in board.pieces() if p == piece]

    def legal_moves(self, state):
        board = state.board
        moves = []
        if state.current_player == 0:
            king_positions = self._find_piece_positions(board, 'A')
            for pos in king_positions:
                for dest in self._step_destinations(board, pos):
                    moves.append(Move(pos, dest))
            return moves
        else:
            guard_positions = self._find_piece_positions(board, 'B')
            guard_positions.sort(key=lambda p: (p.y, p.x))
            for pos in guard_positions:
                for dest in self._slide_destinations(board, pos):
                    moves.append(Move(pos, dest))
            return moves

    def apply(self, state, action):
        new_extra = dict(state.extra)
        new_extra["turn_count"] = state.extra.get("turn_count", 0) + 1

        new_board = state.board.moved(action)

        return GameState(
            board=new_board,
            current_player=1 - state.current_player,
            turn=state.turn + 1,
            extra=new_extra,
        )

    def is_terminal(self, state):
        if self.winner(state) is not None:
            return True
        if state.extra.get("turn_count", 0) >= self.MAX_TURNS:
            return True
        return False

    def winner(self, state):
        board = state.board
        king_positions = self._find_piece_positions(board, 'A')
        if not king_positions:
            return None
        king_pos = king_positions[0]

        if (king_pos.x, king_pos.y) in self.CORNERS:
            return 0

        destinations = self._step_destinations(board, king_pos)
        if not destinations:
            return 1

        if state.current_player == 1:
            guard_positions = self._find_piece_positions(board, 'B')
            guard_moves_exist = False
            for pos in guard_positions:
                if self._slide_destinations(board, pos):
                    guard_moves_exist = True
                    break
            if not guard_moves_exist:
                return 0

        return None