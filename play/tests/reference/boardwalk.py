"""
Boardwalk 2.0
==============

A framework for implementing finite orthogonal board games.

Coordinate System
------------------
The public API always uses Cartesian coordinates:

    (x, y)

where

    x = column
    y = row

Internally, NumPy arrays are indexed as

    layout[y, x]

but this detail is completely hidden from game implementations.

This module is the single source of truth for the engine, and it stays
deliberately generic: Position/Move/Placement/Board/GameState/GameRules,
parsing, and structural board geometry (bounds, neighbors, rays, lines).

Game-specific mechanics — a capture rule, a surrounding rule, a
particular movement pattern — do NOT belong here, even if they look
reusable. They belong in the game's own module, implemented against
these primitives. Keeping the API to high-level questions only (what is
the state, what moves are legal, how does a move transform the state)
is what lets each generated game encode its own identity instead of
inheriting behavior from a shared "mechanics" grab-bag.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Optional, Iterable, Iterator, Union, Generic, TypeVar, Any
import re
import random
import numpy as np


# ============================================================================
# Position
# ============================================================================

@dataclass(frozen=True, slots=True)
class Position:
    """
    Represents one square on the board.

    Coordinates are always (x, y), e.g. Position(2, 5) means
    column = 2, row = 5.
    """

    x: int
    y: int

    def __iter__(self):
        yield self.x
        yield self.y

    def __add__(self, other):
        if not isinstance(other, Position):
            return NotImplemented
        return Position(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        if not isinstance(other, Position):
            return NotImplemented
        return Position(self.x - other.x, self.y - other.y)

    def offset(self, dx: int, dy: int) -> "Position":
        return Position(self.x + dx, self.y + dy)

    def distance(self, other: "Position") -> tuple[int, int]:
        return (other.x - self.x, other.y - self.y)

    def __str__(self):
        return f"{self.x},{self.y}"


# ============================================================================
# Move
# ============================================================================

@dataclass(frozen=True, slots=True)
class Move:
    """Move a piece from one position to another."""

    start: Position
    end: Position

    @property
    def dx(self):
        return self.end.x - self.start.x

    @property
    def dy(self):
        return self.end.y - self.start.y

    @property
    def delta(self):
        return (self.dx, self.dy)

    def __str__(self):
        return f"{self.start} {self.end}"


# ============================================================================
# Placement
# ============================================================================

@dataclass(frozen=True, slots=True)
class Placement:
    """Place a piece on the board."""

    piece: str
    position: Position

    def __str__(self):
        return f"{self.piece} {self.position}"


# ============================================================================
# Parsing
# ============================================================================

_MOVE_RE = re.compile(r"^\s*(\d+)\s*,\s*(\d+)\s+(\d+)\s*,\s*(\d+)\s*$")
_PLACEMENT_RE = re.compile(r"^\s*(.)\s+(\d+)\s*,\s*(\d+)\s*$")


def parse_move(text: str) -> Union[Move, Placement]:
    """
    Parse a human-readable move.

    Accepted formats:
        0,5 1,4     -> Move from (0,5) to (1,4)
        A 2,3       -> Placement of piece 'A' at (2,3)
    """
    m = _MOVE_RE.fullmatch(text)
    if m:
        x1, y1, x2, y2 = map(int, m.groups())
        return Move(Position(x1, y1), Position(x2, y2))

    m = _PLACEMENT_RE.fullmatch(text)
    if m:
        piece, x, y = m.groups()
        return Placement(piece, Position(int(x), int(y)))

    raise ValueError(f"Invalid move: {text!r}")


def format_move(move: Union[Move, Placement]) -> str:
    """Convert a move object into a human-readable string."""
    return str(move)


# ============================================================================
# Directions
# ============================================================================

ORTHOGONAL = (Position(0, -1), Position(1, 0), Position(0, 1), Position(-1, 0))
DIAGONAL = (Position(-1, -1), Position(1, -1), Position(1, 1), Position(-1, 1))
ALL_DIRECTIONS = ORTHOGONAL + DIAGONAL


# ============================================================================
# Utilities
# ============================================================================

def sign(value: int) -> int:
    """Returns -1, 0, or 1."""
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


def normalize(delta: Position) -> Position:
    """
    Normalize a direction vector.

    Example: (3,2) -> (1,1), (-5,0) -> (-1,0)
    """
    return Position(sign(delta.x), sign(delta.y))


# ============================================================================
# Board
# ============================================================================

PieceT = TypeVar("PieceT")


class Board(Generic[PieceT]):
    """
    Immutable board.

    Public coordinates are always (x, y). Internally NumPy is indexed
    as layout[y, x]. All modification methods return a NEW board.

    Every square is in exactly one of three states:
        BLANK ('_')  -> part of play, currently vacant
        NULL  (' ')  -> permanently outside play (non-rectangular boards)
        <piece char> -> part of play, occupied by a game piece

    NULL is never empty, never occupied by a piece, and never returned
    by pieces()/find()/count() — it exists purely to carve non-rectangular
    playable areas out of the rectangular grid. Use board.playable(pos)
    to ask whether a square is part of the game area at all.
    """

    BLANK = "_"
    NULL = " "

    # ---------------------------------------------------------------------
    # Construction
    # ---------------------------------------------------------------------

    def __init__(self, shape: tuple[int, int], layout: str | np.ndarray | None = None):
        self.height, self.width = shape

        self._layout = np.full((self.height, self.width), self.BLANK, dtype=object)

        if layout is None:
            return

        if isinstance(layout, np.ndarray):
            if layout.shape != (self.height, self.width):
                raise ValueError("Board shape does not match supplied layout.")
            self._layout = layout.copy()
            return

        if isinstance(layout, str):
            rows = layout.strip("\n").split("\n")
            if len(rows) != self.height:
                raise ValueError("Board height does not match layout.")
            for y, row in enumerate(rows):
                if len(row) != self.width:
                    raise ValueError("Board width does not match layout.")
                for x, piece in enumerate(row):
                    self._layout[y, x] = piece
            return

        raise TypeError("layout must be None, numpy.ndarray or str.")

    # ---------------------------------------------------------------------
    # Basic properties
    # ---------------------------------------------------------------------

    @property
    def shape(self) -> tuple[int, int]:
        """Returns (width, height)."""
        return self.width, self.height

    @property
    def size(self) -> int:
        return self.width * self.height

    # ---------------------------------------------------------------------
    # Copying
    # ---------------------------------------------------------------------

    def copy(self) -> "Board":
        """Deep copy of the board."""
        return Board((self.height, self.width), self._layout.copy())

    # ---------------------------------------------------------------------
    # Bounds
    # ---------------------------------------------------------------------

    def in_bounds(self, pos: Position) -> bool:
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def on_edge(self, pos: Position) -> bool:
        """True if pos sits on the outer ring of the board (no full set
        of orthogonal neighbors)."""
        self.require(pos)
        return pos.x == 0 or pos.x == self.width - 1 or pos.y == 0 or pos.y == self.height - 1

    def require(self, pos: Position):
        if not self.in_bounds(pos):
            raise IndexError(f"{pos} is outside the board.")

    # ---------------------------------------------------------------------
    # Reading
    # ---------------------------------------------------------------------

    def get(self, pos: Position):
        self.require(pos)
        return self._layout[pos.y, pos.x]

    def __getitem__(self, pos: Position):
        return self.get(pos)

    def empty(self, pos: Position) -> bool:
        """True if this square is part of play and currently vacant.
        NULL squares are never empty."""
        return self[pos] == self.BLANK

    def occupied(self, pos: Position) -> bool:
        """True if this square is part of play and holds a game piece.
        NULL squares are never occupied — they aren't part of play at all."""
        cell = self[pos]
        return cell != self.BLANK and cell != self.NULL

    def playable(self, pos: Position) -> bool:
        """True if this square is part of the game area at all (i.e. not
        a NULL square). A playable square may still be empty or occupied
        — this only answers whether the square exists in play."""
        return self[pos] != self.NULL

    # ---------------------------------------------------------------------
    # Immutable writing
    # ---------------------------------------------------------------------

    def with_piece(self, pos: Position, piece: PieceT) -> "Board":
        """Returns a NEW board with a piece placed."""
        self.require(pos)
        board = self.copy()
        board._layout[pos.y, pos.x] = piece
        return board

    def without_piece(self, pos: Position) -> "Board":
        """Returns a NEW board with the square emptied."""
        return self.with_piece(pos, self.BLANK)

    def moved(self, move: Move) -> "Board":
        """Returns a NEW board with a move applied."""
        self.require(move.start)
        self.require(move.end)

        board = self.copy()
        piece = board._layout[move.start.y, move.start.x]
        board._layout[move.start.y, move.start.x] = self.BLANK
        board._layout[move.end.y, move.end.x] = piece
        return board

    def swapped(self, a: Position, b: Position) -> "Board":
        """Returns a NEW board with two squares swapped."""
        self.require(a)
        self.require(b)

        board = self.copy()
        board._layout[a.y, a.x], board._layout[b.y, b.x] = (
            board._layout[b.y, b.x],
            board._layout[a.y, a.x],
        )
        return board

    # ---------------------------------------------------------------------
    # Iteration
    # ---------------------------------------------------------------------

    def positions(self) -> Iterator[Position]:
        """Iterate over every board position in row-major order."""
        for y in range(self.height):
            for x in range(self.width):
                yield Position(x, y)

    def pieces(self) -> Iterator[tuple[Position, PieceT]]:
        """Iterate over all occupied squares — i.e. squares holding an
        actual game piece. Excludes both BLANK and NULL squares. Yields
        (Position, piece)."""
        for pos in self.positions():
            piece = self[pos]
            if piece != self.BLANK and piece != self.NULL:
                yield pos, piece

    def occupied_positions(self) -> Iterator[Position]:
        for pos, _ in self.pieces():
            yield pos

    def empty_positions(self) -> Iterator[Position]:
        for pos in self.positions():
            if self.empty(pos):
                yield pos

    def null_positions(self) -> Iterator[Position]:
        """Iterate over squares permanently outside the playable area."""
        for pos in self.positions():
            if self[pos] == self.NULL:
                yield pos

    # ---------------------------------------------------------------------
    # Searching
    # ---------------------------------------------------------------------

    def find(self, piece: PieceT) -> Iterator[Position]:
        """Yield every position containing the given piece."""
        for pos, current in self.pieces():
            if current == piece:
                yield pos

    def count(self, piece: PieceT) -> int:
        """Count the occurrences of a piece."""
        return sum(1 for _, current in self.pieces() if current == piece)

    def contains(self, piece: PieceT) -> bool:
        """Returns True if the board contains the piece."""
        return any(current == piece for _, current in self.pieces())

    # ---------------------------------------------------------------------
    # Neighbourhood
    # ---------------------------------------------------------------------

    def neighbors(self, pos: Position, directions=ALL_DIRECTIONS) -> Iterator[Position]:
        """Yield neighboring positions according to the supplied directions."""
        self.require(pos)
        for direction in directions:
            nxt = pos + direction
            if self.in_bounds(nxt):
                yield nxt

    def orthogonal_neighbors(self, pos: Position) -> Iterator[Position]:
        yield from self.neighbors(pos, ORTHOGONAL)

    def diagonal_neighbors(self, pos: Position) -> Iterator[Position]:
        yield from self.neighbors(pos, DIAGONAL)

    # ---------------------------------------------------------------------
    # Rays
    # ---------------------------------------------------------------------

    def ray(self, start: Position, direction: Position) -> Iterator[Position]:
        """Yield every position while walking in one direction."""
        current = start + direction
        while self.in_bounds(current):
            yield current
            current = current + direction

    def line(self, start: Position, end: Position) -> Iterator[Position]:
        """
        Yield every square from start to end (inclusive). Only horizontal,
        vertical and diagonal lines are supported.
        """
        dx = end.x - start.x
        dy = end.y - start.y
        step = normalize(Position(dx, dy))

        current = start
        while True:
            yield current
            if current == end:
                break
            current = current + step

    # ---------------------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------------------

    def to_numpy(self) -> np.ndarray:
        """Return a copy of the underlying NumPy array."""
        return self._layout.copy()

    def to_string(self) -> str:
        """Serialize the board into the multiline format accepted by the
        constructor."""
        return "\n".join(
            "".join(self._layout[y, x] for x in range(self.width))
            for y in range(self.height)
        )

    # ---------------------------------------------------------------------
    # Equality
    # ---------------------------------------------------------------------

    def __eq__(self, other):
        if not isinstance(other, Board):
            return False
        return np.array_equal(self._layout, other._layout)

    def __hash__(self):
        return hash(self.to_string())

    # ---------------------------------------------------------------------
    # Representation
    # ---------------------------------------------------------------------

    def __repr__(self):
        return f"Board(width={self.width}, height={self.height})"

    def __str__(self):
        row_digits = max(1, len(str(self.height - 1)))
        col_digits = max(1, len(str(self.width - 1)))

        lines = []
        header = " " * (row_digits + 1)
        header += " ".join(f"{x:>{col_digits}}" for x in range(self.width))
        lines.append(header)

        for y in range(self.height):
            row = f"{y:>{row_digits}} "
            row += " ".join(f"{self._layout[y, x]:>{col_digits}}" for x in range(self.width))
            lines.append(row)

        return "\n".join(lines)


# ============================================================================
# GameState
# ============================================================================

@dataclass(frozen=True, slots=True)
class GameState:
    """Immutable snapshot of a game at a point in time."""

    board: Board
    current_player: int
    turn: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def with_board(self, board: Board) -> "GameState":
        return GameState(board=board, current_player=self.current_player, turn=self.turn, extra=self.extra)

    def next_player(self) -> "GameState":
        return GameState(board=self.board, current_player=1 - self.current_player, turn=self.turn + 1, extra=self.extra)


# ============================================================================
# Player Interface
# ============================================================================

class Player(Protocol):
    """Any AI or human controller must implement this."""

    def choose_move(self, game: "GameRules", state: GameState, legal_moves: list[Any]) -> Any:
        ...


# ============================================================================
# GameRules (abstract engine)
# ============================================================================

class GameRules:
    """
    Defines rules for a game.

    This class contains NO mutable state. It only defines how states
    transform.
    """

    def initial_state(self) -> GameState:
        raise NotImplementedError

    def legal_moves(self, state: GameState) -> list[Any]:
        raise NotImplementedError

    def apply(self, state: GameState, move: Any) -> GameState:
        """Returns a NEW GameState after applying a move."""
        raise NotImplementedError

    def is_terminal(self, state: GameState) -> bool:
        raise NotImplementedError

    def winner(self, state: GameState) -> Optional[int]:
        """Return 0 or 1 for a winner, None for a draw or unfinished game."""
        return None

    def play_move(self, state: GameState, move: Any) -> GameState:
        """Safe wrapper around apply()."""
        if move not in self.legal_moves(state):
            raise ValueError(f"Illegal move: {move}")
        return self.apply(state, move)

    def result(self, state: GameState) -> Optional[int]:
        """Returns winner if terminal."""
        if not self.is_terminal(state):
            return None
        return self.winner(state)


# ============================================================================
# Simple Move Validation Helpers
# ============================================================================

def must_be_in_bounds(board: Board, pos: Position):
    if not board.in_bounds(pos):
        raise ValueError(f"Out of bounds: {pos}")


def is_empty(board: Board, pos: Position) -> bool:
    return board[pos] == board.BLANK


def is_enemy(board: Board, pos: Position, player_piece: str) -> bool:
    """True if pos holds an opponent's piece. NULL squares are never
    an enemy — they're outside play, not owned by anyone."""
    cell = board[pos]
    return cell != board.BLANK and cell != board.NULL and cell != player_piece


# ============================================================================
# Human Player
# ============================================================================

class HumanPlayer:
    """Reads moves from stdin."""

    def choose_move(self, game: GameRules, state: GameState, legal_moves: list):
        print("\nCurrent board:")
        print(state.board)

        print("\nLegal moves:")
        for m in legal_moves:
            print("  ", m)

        while True:
            raw = input("\nYour move: ")
            try:
                move = parse_move(raw)
            except Exception as e:
                print("Invalid format:", e)
                continue

            if move not in legal_moves:
                print("Illegal move.")
                continue

            return move


# ============================================================================
# Random Player
# ============================================================================

class RandomPlayer:
    """Chooses a random legal move."""

    def choose_move(self, game: GameRules, state: GameState, legal_moves: list):
        return random.choice(legal_moves)


# ============================================================================
# Game Session (Runner)
# ============================================================================

class GameSession:
    """Executes a full game between two players."""

    def __init__(self, game: GameRules, player0: Player, player1: Player):
        self.game = game
        self.players = {0: player0, 1: player1}

    def run(self) -> Optional[int]:
        state = self.game.initial_state()

        while not self.game.is_terminal(state):
            current = state.current_player
            player = self.players[current]

            moves = self.game.legal_moves(state)
            if not moves:
                break

            move = player.choose_move(self.game, state, moves)
            state = self.game.apply(state, move)

        print("\nFinal board:")
        print(state.board)

        winner = self.game.winner(state)
        if winner is None:
            print("\nResult: Draw")
        else:
            print(f"\nWinner: Player {winner}")

        return winner


# ============================================================================
# CLI helper
# ============================================================================

def play_cli(game: GameRules):
    """Convenience function for human vs human or human vs AI."""
    session = GameSession(game=game, player0=HumanPlayer(), player1=HumanPlayer())
    return session.run()


# ============================================================================
# Utility: move adapter (for future AI use)
# ============================================================================

def ensure_move_is_valid(move, legal_moves):
    if move not in legal_moves:
        raise ValueError(f"Illegal move: {move}")