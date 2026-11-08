from boardwalk import GameRules, GameState, Board, Position, Move, Placement
import random, math

class AscensionCheckers(GameRules):
    def __init__(self):
        self.MAX_TURNS = 80

    def initial_state(self):
        initial_layout = "AAAAAA\n______\n______\n______\n______\nBBBBBB"
        board = Board((6, 6), initial_layout)
        return GameState(
            board=board,
            current_player=0,
            turn=0,
            extra={
                "history": [],
                "reserves": {0: 1, 1: 1},
                "turn_count": 0,
                "dominance_streak": 0,
                "dominance_leader": None
            }
        )

    def _simulate_action(self, state, action):
        board = state.board
        if isinstance(action, Move):
            board = board.moved(action)
            dx = abs(action.start.x - action.end.x)
            dy = abs(action.start.y - action.end.y)
            if dx == 2 or dy == 2:
                mid = Position((action.start.x + action.end.x) // 2, (action.start.y + action.end.y) // 2)
                board = board.without_piece(mid)
            if state.current_player == 0 and action.end.y == 5:
                board = board.with_piece(action.end, 'a')
            elif state.current_player == 1 and action.end.y == 0:
                board = board.with_piece(action.end, 'b')
        elif isinstance(action, Placement):
            board = board.with_piece(action.position, action.piece)
        return board

    def legal_moves(self, state):
        w, h = state.board.width, state.board.height
        player = state.current_player
        my_pieces = ('A', 'a', 'V') if player == 0 else ('B', 'b', 'C')
        opp_pieces = ('B', 'b', 'C') if player == 0 else ('A', 'a', 'V')
        moves = []
        
        for pos, piece in state.board.pieces():
            if piece not in my_pieces:
                continue
            x, y = pos.x, pos.y
            
            if piece in ('A', 'V'):
                nx, ny = x, y + 1
                if 0 <= nx < w and 0 <= ny < h and state.board[Position(nx, ny)] == Board.BLANK:
                    moves.append(Move(pos, Position(nx, ny)))
                for dx in (-1, 1):
                    mx, my_c = x + dx, y + 1
                    jx, jy = x + dx, y + 2
                    if 0 <= mx < w and 0 <= my_c < h and 0 <= jx < w and 0 <= jy < h:
                        mid = state.board[Position(mx, my_c)]
                        if mid in opp_pieces and state.board[Position(jx, jy)] == Board.BLANK:
                            moves.append(Move(pos, Position(jx, jy)))
                            
            elif piece in ('B', 'C'):
                nx, ny = x, y - 1
                if 0 <= nx < w and 0 <= ny < h and state.board[Position(nx, ny)] == Board.BLANK:
                    moves.append(Move(pos, Position(nx, ny)))
                for dx in (-1, 1):
                    mx, my_c = x + dx, y - 1
                    jx, jy = x + dx, y - 2
                    if 0 <= mx < w and 0 <= my_c < h and 0 <= jx < w and 0 <= jy < h:
                        mid = state.board[Position(mx, my_c)]
                        if mid in opp_pieces and state.board[Position(jx, jy)] == Board.BLANK:
                            moves.append(Move(pos, Position(jx, jy)))
                            
            elif piece in ('a', 'b'):
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and state.board[Position(nx, ny)] == Board.BLANK:
                            moves.append(Move(pos, Position(nx, ny)))
                        jx, jy = x + 2*dx, y + 2*dy
                        mx, my_c = x + dx, y + dy
                        if 0 <= mx < w and 0 <= my_c < h and 0 <= jx < w and 0 <= jy < h:
                            mid = state.board[Position(mx, my_c)]
                            if mid in opp_pieces and state.board[Position(jx, jy)] == Board.BLANK:
                                moves.append(Move(pos, Position(jx, jy)))
                                
        reserves = state.extra.get("reserves", {0: 1, 1: 1})
        if reserves.get(player, 0) > 0:
            my_count = sum(state.board.count(p) for p in my_pieces)
            if my_count <= 2:
                place_piece = 'V' if player == 0 else 'C'
                zone_rows = (0, 1) if player == 0 else (4, 5)
                for pos in state.board.empty_positions():
                    if pos.y in zone_rows:
                        moves.append(Placement(place_piece, pos))

        jump_moves = [m for m in moves if isinstance(m, Move) and (abs(m.start.x - m.end.x) == 2 or abs(m.start.y - m.end.y) == 2)]
        if jump_moves:
            moves = jump_moves
                        
        return moves

    def apply(self, state, action):
        new_extra = dict(state.extra)
        new_extra["history"] = list(state.extra.get("history", []))
        new_extra["reserves"] = dict(state.extra.get("reserves", {0: 1, 1: 1}))
        new_extra["turn_count"] = state.extra.get("turn_count", 0) + 1
        
        board = state.board
        if isinstance(action, Move):
            board = board.moved(action)
            dx = abs(action.start.x - action.end.x)
            dy = abs(action.start.y - action.end.y)
            if dx == 2 or dy == 2:
                mid = Position((action.start.x + action.end.x) // 2, (action.start.y + action.end.y) // 2)
                board = board.without_piece(mid)
            if state.current_player == 0 and action.end.y == 5:
                board = board.with_piece(action.end, 'a')
            elif state.current_player == 1 and action.end.y == 0:
                board = board.with_piece(action.end, 'b')
        elif isinstance(action, Placement):
            board = board.with_piece(action.position, action.piece)
            new_extra["reserves"][state.current_player] -= 1
            
        w, h = board.width, board.height
        board_sig = tuple(board[Position(x, y)] for y in range(h) for x in range(w))
        new_extra["history"].append((board_sig, 1 - state.current_player))
        
        p0_count = sum(board.count(p) for p in ('A', 'a', 'V'))
        p1_count = sum(board.count(p) for p in ('B', 'b', 'C'))
        diff = p0_count - p1_count
        if abs(diff) >= 2:
            leader = 0 if diff > 0 else 1
            if leader == new_extra.get("dominance_leader"):
                new_extra["dominance_streak"] = new_extra.get("dominance_streak", 0) + 1
            else:
                new_extra["dominance_streak"] = 1
                new_extra["dominance_leader"] = leader
        else:
            new_extra["dominance_streak"] = 0
            new_extra["dominance_leader"] = None
        
        return GameState(
            board=board,
            current_player=1 - state.current_player,
            turn=state.turn + 1,
            extra=new_extra
        )

    def is_terminal(self, state):
        if self.winner(state) is not None:
            return True
        if state.extra.get("turn_count", 0) >= self.MAX_TURNS:
            return True
        return False

    def winner(self, state):
        board = state.board
        p0_count = sum(board.count(p) for p in ('A', 'a', 'V'))
        p1_count = sum(board.count(p) for p in ('B', 'b', 'C'))
        if p0_count == 0:
            return 1
        if p1_count == 0:
            return 0
        if not self.legal_moves(state):
            return 1 - state.current_player
        if state.extra.get("turn_count", 0) >= self.MAX_TURNS:
            p0_score = sum(board.count(p) * (2 if p == 'a' else 1) for p in ('A', 'a', 'V'))
            p1_score = sum(board.count(p) * (2 if p == 'b' else 1) for p in ('B', 'b', 'C'))
            if p0_score > p1_score:
                return 0
            elif p1_score > p0_score:
                return 1
            else:
                return None
        if state.turn > 30 and state.extra.get("dominance_streak", 0) >= 2:
            return state.extra.get("dominance_leader")
        return None