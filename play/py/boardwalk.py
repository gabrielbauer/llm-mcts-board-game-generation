"""
Boardwalk 2.0 (browser edition)
===============================

A dependency-free port of the Boardwalk 2.0 engine used by the generation
pipeline. The public API, coordinate system and iteration orders are the
same as the original, so the generated game files run unchanged; the only
difference is that the board is stored in a flat tuple instead of a NumPy
object array, which keeps the browser download small (no NumPy wheel) and
makes copies cheaper during MCTS rollouts.

Coordinates are Cartesian, (x, y): x = column, y = row, (0, 0) = top-left.

`tests/test_equivalence.py` replays seeded random games with this module
and with the original engine and checks that every state and every list of
legal moves is identical.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Generic, Iterator, Optional, Protocol, TypeVar, Union


# ============================================================================
# Position
# ============================================================================

@dataclass(frozen=True, slots=True)
class Position:
    """One square on the board, as (x, y) = (column, row)."""

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
# Move / Placement
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
    """Parse "0,5 1,4" (Move) or "A 2,3" (Placement)."""
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
    return str(move)


# ============================================================================
# Directions / utilities
# ============================================================================

ORTHOGONAL = (Position(0, -1), Position(1, 0), Position(0, 1), Position(-1, 0))
DIAGONAL = (Position(-1, -1), Position(1, -1), Position(1, 1), Position(-1, 1))
ALL_DIRECTIONS = ORTHOGONAL + DIAGONAL


def sign(value: int) -> int:
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


def normalize(delta: Position) -> Position:
    return Position(sign(delta.x), sign(delta.y))


# ============================================================================
# Board
# ============================================================================

PieceT = TypeVar("PieceT")


class Board(Generic[PieceT]):
    """
    Immutable board. All modification methods return a NEW board.

    Squares are BLANK ('_', vacant), NULL (' ', outside play) or hold a
    piece character. Cells are stored row-major in a tuple: index y*w + x.
    """

    BLANK = "_"
    NULL = " "

    __slots__ = ("height", "width", "_cells")

    def __init__(self, shape: tuple[int, int], layout=None):
        self.height, self.width = shape
        n = self.height * self.width

        if layout is None:
            self._cells = (self.BLANK,) * n
            return

        if isinstance(layout, str):
            rows = layout.strip("\n").split("\n")
            if len(rows) != self.height:
                raise ValueError("Board height does not match layout.")
            cells = []
            for row in rows:
                if len(row) != self.width:
                    raise ValueError("Board width does not match layout.")
                cells.extend(row)
            self._cells = tuple(cells)
            return

        if isinstance(layout, tuple) and len(layout) == n:
            # internal fast path (already a flat cell tuple)
            self._cells = layout
            return

        if hasattr(layout, "shape") and hasattr(layout, "tolist"):
            # NumPy array, kept for API compatibility
            if tuple(layout.shape) != (self.height, self.width):
                raise ValueError("Board shape does not match supplied layout.")
            self._cells = tuple(c for row in layout.tolist() for c in row)
            return

        raise TypeError("layout must be None, numpy.ndarray or str.")

    @classmethod
    def _make(cls, height: int, width: int, cells: tuple) -> "Board":
        b = cls.__new__(cls)
        b.height = height
        b.width = width
        b._cells = cells
        return b

    # -- properties ---------------------------------------------------------

    @property
    def shape(self) -> tuple[int, int]:
        """Returns (width, height)."""
        return self.width, self.height

    @property
    def size(self) -> int:
        return self.width * self.height

    def copy(self) -> "Board":
        return Board._make(self.height, self.width, self._cells)

    # -- bounds -------------------------------------------------------------

    def in_bounds(self, pos: Position) -> bool:
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def on_edge(self, pos: Position) -> bool:
        self.require(pos)
        return pos.x == 0 or pos.x == self.width - 1 or pos.y == 0 or pos.y == self.height - 1

    def require(self, pos: Position):
        if not (0 <= pos.x < self.width and 0 <= pos.y < self.height):
            raise IndexError(f"{pos} is outside the board.")

    # -- reading ------------------------------------------------------------

    def get(self, pos: Position):
        x, y = pos.x, pos.y
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"{pos} is outside the board.")
        return self._cells[y * self.width + x]

    __getitem__ = get

    def empty(self, pos: Position) -> bool:
        return self.get(pos) == self.BLANK

    def occupied(self, pos: Position) -> bool:
        cell = self.get(pos)
        return cell != self.BLANK and cell != self.NULL

    def playable(self, pos: Position) -> bool:
        return self.get(pos) != self.NULL

    # -- immutable writing --------------------------------------------------

    def with_piece(self, pos: Position, piece: PieceT) -> "Board":
        self.require(pos)
        i = pos.y * self.width + pos.x
        c = self._cells
        return Board._make(self.height, self.width, c[:i] + (piece,) + c[i + 1:])

    def without_piece(self, pos: Position) -> "Board":
        return self.with_piece(pos, self.BLANK)

    def moved(self, move: Move) -> "Board":
        self.require(move.start)
        self.require(move.end)
        w = self.width
        cells = list(self._cells)
        s = move.start.y * w + move.start.x
        e = move.end.y * w + move.end.x
        piece = cells[s]
        cells[s] = self.BLANK
        cells[e] = piece
        return Board._make(self.height, w, tuple(cells))

    def swapped(self, a: Position, b: Position) -> "Board":
        self.require(a)
        self.require(b)
        w = self.width
        cells = list(self._cells)
        i, j = a.y * w + a.x, b.y * w + b.x
        cells[i], cells[j] = cells[j], cells[i]
        return Board._make(self.height, w, tuple(cells))

    # -- iteration (row-major, same order as the original) ------------------

    def positions(self) -> Iterator[Position]:
        for y in range(self.height):
            for x in range(self.width):
                yield Position(x, y)

    def pieces(self) -> Iterator[tuple[Position, PieceT]]:
        w = self.width
        blank, null = self.BLANK, self.NULL
        for i, piece in enumerate(self._cells):
            if piece != blank and piece != null:
                yield Position(i % w, i // w), piece

    def occupied_positions(self) -> Iterator[Position]:
        for pos, _ in self.pieces():
            yield pos

    def empty_positions(self) -> Iterator[Position]:
        w = self.width
        blank = self.BLANK
        for i, piece in enumerate(self._cells):
            if piece == blank:
                yield Position(i % w, i // w)

    def null_positions(self) -> Iterator[Position]:
        w = self.width
        for i, piece in enumerate(self._cells):
            if piece == self.NULL:
                yield Position(i % w, i // w)

    # -- searching ----------------------------------------------------------

    def find(self, piece: PieceT) -> Iterator[Position]:
        for pos, current in self.pieces():
            if current == piece:
                yield pos

    def count(self, piece: PieceT) -> int:
        if piece == self.BLANK or piece == self.NULL:
            return 0
        return self._cells.count(piece)

    def contains(self, piece: PieceT) -> bool:
        if piece == self.BLANK or piece == self.NULL:
            return False
        return piece in self._cells

    # -- neighbourhood ------------------------------------------------------

    def neighbors(self, pos: Position, directions=ALL_DIRECTIONS) -> Iterator[Position]:
        self.require(pos)
        for direction in directions:
            nxt = pos + direction
            if self.in_bounds(nxt):
                yield nxt

    def orthogonal_neighbors(self, pos: Position) -> Iterator[Position]:
        yield from self.neighbors(pos, ORTHOGONAL)

    def diagonal_neighbors(self, pos: Position) -> Iterator[Position]:
        yield from self.neighbors(pos, DIAGONAL)

    # -- rays ---------------------------------------------------------------

    def ray(self, start: Position, direction: Position) -> Iterator[Position]:
        current = start + direction
        while self.in_bounds(current):
            yield current
            current = current + direction

    def line(self, start: Position, end: Position) -> Iterator[Position]:
        step = normalize(Position(end.x - start.x, end.y - start.y))
        current = start
        while True:
            yield current
            if current == end:
                break
            current = current + step

    # -- serialization ------------------------------------------------------

    def rows(self) -> list[str]:
        w = self.width
        c = self._cells
        return ["".join(str(p) for p in c[y * w:(y + 1) * w]) for y in range(self.height)]

    def to_string(self) -> str:
        return "\n".join(self.rows())

    def to_numpy(self):
        import numpy as np  # optional; not needed in the browser
        arr = np.empty((self.height, self.width), dtype=object)
        for y in range(self.height):
            for x in range(self.width):
                arr[y, x] = self._cells[y * self.width + x]
        return arr

    # -- equality / repr ----------------------------------------------------

    def __eq__(self, other):
        if not isinstance(other, Board):
            return False
        return (self.height, self.width) == (other.height, other.width) and self._cells == other._cells

    def __hash__(self):
        return hash(self.to_string())

    def __repr__(self):
        return f"Board(width={self.width}, height={self.height})"

    def __str__(self):
        row_digits = max(1, len(str(self.height - 1)))
        col_digits = max(1, len(str(self.width - 1)))
        lines = [" " * (row_digits + 1) + " ".join(f"{x:>{col_digits}}" for x in range(self.width))]
        for y in range(self.height):
            row = f"{y:>{row_digits}} "
            row += " ".join(f"{self._cells[y * self.width + x]:>{col_digits}}" for x in range(self.width))
            lines.append(row)
        return "\n".join(lines)


# ============================================================================
# GameState / GameRules
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


class Player(Protocol):
    def choose_move(self, game: "GameRules", state: GameState, legal_moves: list[Any]) -> Any:
        ...


class GameRules:
    """Defines the rules of a game. Holds no mutable state."""

    def initial_state(self) -> GameState:
        raise NotImplementedError

    def legal_moves(self, state: GameState) -> list[Any]:
        raise NotImplementedError

    def apply(self, state: GameState, move: Any) -> GameState:
        raise NotImplementedError

    def is_terminal(self, state: GameState) -> bool:
        raise NotImplementedError

    def winner(self, state: GameState) -> Optional[int]:
        return None

    def play_move(self, state: GameState, move: Any) -> GameState:
        if move not in self.legal_moves(state):
            raise ValueError(f"Illegal move: {move}")
        return self.apply(state, move)

    def result(self, state: GameState) -> Optional[int]:
        if not self.is_terminal(state):
            return None
        return self.winner(state)


# ============================================================================
# Helpers kept from the original API
# ============================================================================

def must_be_in_bounds(board: Board, pos: Position):
    if not board.in_bounds(pos):
        raise ValueError(f"Out of bounds: {pos}")


def is_empty(board: Board, pos: Position) -> bool:
    return board[pos] == board.BLANK


def is_enemy(board: Board, pos: Position, player_piece: str) -> bool:
    cell = board[pos]
    return cell != board.BLANK and cell != board.NULL and cell != player_piece


class RandomPlayer:
    def choose_move(self, game: GameRules, state: GameState, legal_moves: list):
        return random.choice(legal_moves)


def ensure_move_is_valid(move, legal_moves):
    if move not in legal_moves:
        raise ValueError(f"Illegal move: {move}")
