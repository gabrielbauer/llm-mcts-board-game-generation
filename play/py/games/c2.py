from boardwalk import GameRules, GameState, Board, Position, Move, Placement
import random, math


class OrthoSurround6(GameRules):
    def __init__(self):
        self.MAX_TURNS = 120

    def initial_state(self):
        initial_layout = "______\n______\n______\n______\n______\n______"
        board = Board((6, 6), initial_layout)
        return GameState(
            board=board,
            current_player=0,
            turn=0,
            extra={"turn_counter": 0, "reserves": {"A": 19, "B": 21}}
        )

    def legal_moves(self, state):
        moves = []
        marker = 'A' if state.current_player == 0 else 'B'
        
        if state.extra["reserves"][marker] > 0:
            for y in range(state.board.height):
                for x in range(state.board.width):
                    pos = Position(x, y)
                    if state.board.empty(pos):
                        moves.append(Placement(marker, pos))
                        
        for pos, piece in state.board.pieces():
            if piece == marker:
                for neighbor in state.board.orthogonal_neighbors(pos):
                    if state.board.empty(neighbor):
                        moves.append(Move(pos, neighbor))
                        
        return moves

    def apply(self, state, action):
        marker = 'A' if state.current_player == 0 else 'B'
        opponent_marker = 'B' if state.current_player == 0 else 'A'
        
        new_board = state.board
        new_extra = {
            "turn_counter": state.extra["turn_counter"] + 1,
            "reserves": dict(state.extra["reserves"])
        }
        
        if isinstance(action, Placement):
            new_board = new_board.with_piece(action.position, action.piece)
            new_extra["reserves"][marker] -= 1
        elif isinstance(action, Move):
            new_board = new_board.moved(action)
            
        captures = []
        for pos, piece in new_board.pieces():
            if piece == opponent_marker:
                neighbors = new_board.orthogonal_neighbors(pos)
                blocked_count = sum(1 for n in neighbors if new_board[n] == marker)
                if blocked_count >= 3:
                    captures.append(pos)
                    
        for pos in captures:
            new_board = new_board.without_piece(pos)
            
        return GameState(
            board=new_board,
            current_player=1 - state.current_player,
            turn=state.turn + 1,
            extra=new_extra
        )

    def is_terminal(self, state):
        if state.extra["turn_counter"] >= self.MAX_TURNS:
            return True
        if not list(state.board.empty_positions()):
            return True
        if not self.legal_moves(state):
            other_state = GameState(
                board=state.board,
                current_player=1 - state.current_player,
                turn=state.turn,
                extra=state.extra
            )
            if not self.legal_moves(other_state):
                return True
        return False

    def winner(self, state):
        count_a = state.board.count('A')
        count_b = state.board.count('B')
        if count_a > count_b:
            return 0
        elif count_b > count_a:
            return 1
        else:
            return 1