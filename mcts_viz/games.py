"""Concrete game implementations."""

from __future__ import annotations
import numpy as np
from .game_base import GameState


class TicTacToeState(GameState):
    """3x3 TicTacToe. action = row*3 + col (0-8)."""

    def __init__(self, board: np.ndarray | None = None, player: int = 1):
        self._board = board if board is not None else np.zeros(9, dtype=int)
        self._player = player

    @classmethod
    def game_id(cls) -> str:
        return "tictactoe"

    @classmethod
    def board_shape(cls) -> tuple[int, int]:
        return (3, 3)

    @classmethod
    def action_to_coords(cls, action: int) -> tuple[int, int]:
        return divmod(action, 3)

    @property
    def current_player(self) -> int:
        return self._player

    def legal_actions(self) -> list[int]:
        return [i for i in range(9) if self._board[i] == 0]

    def apply(self, action: int) -> TicTacToeState:
        b = self._board.copy()
        b[action] = self._player
        return TicTacToeState(b, -self._player)

    def is_terminal(self) -> bool:
        return self._winner() is not None or not self.legal_actions()

    def result(self, player: int) -> float:
        w = self._winner()
        if w is None:
            return 0.0
        return 1.0 if w == player else -1.0

    def _winner(self) -> int | None:
        b = self._board.reshape(3, 3)
        lines = [
            *[b[r, :] for r in range(3)],
            *[b[:, c] for c in range(3)],
            np.diag(b),
            np.diag(np.fliplr(b)),
        ]
        for line in lines:
            if abs(line.sum()) == 3:
                return int(line[0])
        return None

    def to_dict(self) -> dict:
        return {
            "game": self.game_id(),
            "board": self._board.tolist(),
            "current_player": self._player,
            "is_terminal": self.is_terminal(),
            "legal_actions": self.legal_actions(),
            "winner": self._winner(),
            "shape": list(self.board_shape()),
        }


class TwoInARowState(GameState):
    """2x2 board, 2-in-a-row wins (horizontal/vertical/diagonal)."""

    def __init__(self, board: np.ndarray | None = None, player: int = 1):
        self._board = board if board is not None else np.zeros(4, dtype=int)
        self._player = player

    @classmethod
    def game_id(cls) -> str:
        return "twoinrow"

    @classmethod
    def board_shape(cls) -> tuple[int, int]:
        return (2, 2)

    @classmethod
    def action_to_coords(cls, action: int) -> tuple[int, int]:
        return divmod(action, 2)

    @property
    def current_player(self) -> int:
        return self._player

    def legal_actions(self) -> list[int]:
        return [i for i in range(4) if self._board[i] == 0]

    def apply(self, action: int) -> TwoInARowState:
        b = self._board.copy()
        b[action] = self._player
        return TwoInARowState(b, -self._player)

    def is_terminal(self) -> bool:
        return self._winner() is not None or not self.legal_actions()

    def result(self, player: int) -> float:
        w = self._winner()
        if w is None:
            return 0.0
        return 1.0 if w == player else -1.0

    def _winner(self) -> int | None:
        b = self._board.reshape(2, 2)
        for r in range(2):
            for c in range(2):
                v = b[r, c]
                if v == 0:
                    continue
                if c + 1 < 2 and b[r, c + 1] == v:  # right
                    return int(v)
                if r + 1 < 2 and b[r + 1, c] == v:  # down
                    return int(v)
                if r + 1 < 2 and c + 1 < 2 and b[r + 1, c + 1] == v:  # diag
                    return int(v)
                if r + 1 < 2 and c - 1 >= 0 and b[r + 1, c - 1] == v:  # anti-diag
                    return int(v)
        return None

    def to_dict(self) -> dict:
        return {
            "game": self.game_id(),
            "board": self._board.tolist(),
            "current_player": self._player,
            "is_terminal": self.is_terminal(),
            "legal_actions": self.legal_actions(),
            "winner": self._winner(),
            "shape": list(self.board_shape()),
        }


class NInARowState(GameState):
    """Generic RxC board, K-in-a-row wins. Subclass and set ROWS, COLS, K."""
    ROWS = 4
    COLS = 4
    K = 3

    def __init__(self, board: np.ndarray | None = None, player: int = 1):
        size = self.ROWS * self.COLS
        self._board = board if board is not None else np.zeros(size, dtype=int)
        self._player = player

    @classmethod
    def game_id(cls) -> str:
        return f"{cls.K}row_{cls.ROWS}x{cls.COLS}"

    @classmethod
    def board_shape(cls) -> tuple[int, int]:
        return (cls.ROWS, cls.COLS)

    @classmethod
    def action_to_coords(cls, action: int) -> tuple[int, int]:
        return divmod(action, cls.COLS)

    @property
    def current_player(self) -> int:
        return self._player

    def legal_actions(self) -> list[int]:
        return [i for i in range(self.ROWS * self.COLS) if self._board[i] == 0]

    def apply(self, action: int) -> NInARowState:
        b = self._board.copy()
        b[action] = self._player
        return self.__class__(b, -self._player)

    def is_terminal(self) -> bool:
        return self._winner() is not None or not self.legal_actions()

    def result(self, player: int) -> float:
        w = self._winner()
        if w is None:
            return 0.0
        return 1.0 if w == player else -1.0

    def _winner(self) -> int | None:
        b = self._board.reshape(self.ROWS, self.COLS)
        dirs = [(0, 1), (1, 0), (1, 1), (1, -1)]  # right, down, diag, anti-diag
        for r in range(self.ROWS):
            for c in range(self.COLS):
                v = b[r, c]
                if v == 0:
                    continue
                for dr, dc in dirs:
                    er, ec = r + dr * (self.K - 1), c + dc * (self.K - 1)
                    if er < 0 or er >= self.ROWS or ec < 0 or ec >= self.COLS:
                        continue
                    if all(b[r + dr * i, c + dc * i] == v for i in range(self.K)):
                        return int(v)
        return None

    def to_dict(self) -> dict:
        return {
            "game": self.game_id(),
            "board": self._board.tolist(),
            "current_player": self._player,
            "is_terminal": self.is_terminal(),
            "legal_actions": self.legal_actions(),
            "winner": self._winner(),
            "shape": list(self.board_shape()),
        }


class ThreeInRow4x4(NInARowState):
    """4x4 board, 3-in-a-row."""
    ROWS = 4
    COLS = 4
    K = 3


class FourInRow5x5(NInARowState):
    """5x5 board, 4-in-a-row."""
    ROWS = 5
    COLS = 5
    K = 4


class NimState(GameState):
    """Subtraction game (Nim variant).

    N stones, each turn a player takes k stones where k is in `allowed`.
    The player who takes the last stone wins.
    action = number of stones to take.
    """

    INITIAL_STONES = 7
    ALLOWED = (1, 2)  # can take 1, 2

    def __init__(self, stones: int | None = None, player: int = 1):
        self._stones = stones if stones is not None else self.INITIAL_STONES
        self._player = player

    @classmethod
    def game_id(cls) -> str:
        return "nim"

    @classmethod
    def board_shape(cls) -> tuple[int, int]:
        return (1, 1)  # not a grid game

    @classmethod
    def action_to_coords(cls, action: int) -> tuple[int, int]:
        return (0, 0)

    @property
    def current_player(self) -> int:
        return self._player

    def legal_actions(self) -> list[int]:
        return [k for k in self.ALLOWED if k <= self._stones]

    def apply(self, action: int) -> NimState:
        return NimState(self._stones - action, -self._player)

    def is_terminal(self) -> bool:
        return self._stones == 0

    def result(self, player: int) -> float:
        # The player who just moved (took the last stone) wins.
        # When stones=0, the previous player took the last stone.
        last_mover = -self._player
        return 1.0 if last_mover == player else -1.0

    def to_dict(self) -> dict:
        last_mover = -self._player if self._stones == 0 else None
        return {
            "game": self.game_id(),
            "stones": self._stones,
            "allowed": list(self.ALLOWED),
            "current_player": self._player,
            "is_terminal": self.is_terminal(),
            "legal_actions": self.legal_actions(),
            "winner": last_mover if self.is_terminal() else None,
            "shape": [1, 1],
            "board": [self._stones],  # for compat
        }


class ChopsticksState(GameState):
    """Chopsticks finger game.

    State: (p1_left, p1_right, p2_left, p2_right), each 0-4.
    0 = dead hand, 1-4 = alive fingers.

    Actions:
      Tap:   0..3 = (my_hand_idx, opp_hand_idx) where idx 0=left, 1=right
             0: my_L->opp_L, 1: my_L->opp_R, 2: my_R->opp_L, 3: my_R->opp_R
      Split: 10+new_left = redistribute fingers (total stays same)
    """

    def __init__(self, hands: tuple[int, int, int, int] = (1, 1, 1, 1),
                 player: int = 1):
        self._hands = hands  # (p1L, p1R, p2L, p2R)
        self._player = player

    @classmethod
    def game_id(cls) -> str:
        return "chopsticks"

    @classmethod
    def board_shape(cls) -> tuple[int, int]:
        return (1, 1)

    @classmethod
    def action_to_coords(cls, action: int) -> tuple[int, int]:
        return (0, 0)

    @property
    def current_player(self) -> int:
        return self._player

    def _my_hands(self) -> tuple[int, int]:
        if self._player == 1:
            return (self._hands[0], self._hands[1])
        return (self._hands[2], self._hands[3])

    def _opp_hands(self) -> tuple[int, int]:
        if self._player == 1:
            return (self._hands[2], self._hands[3])
        return (self._hands[0], self._hands[1])

    def legal_actions(self) -> list[int]:
        my = self._my_hands()
        opp = self._opp_hands()
        actions = []
        # Tap: my_hand_idx(0,1) x opp_hand_idx(0,1)
        for mi in range(2):
            if my[mi] == 0:
                continue
            for oi in range(2):
                if opp[oi] == 0:
                    continue
                actions.append(mi * 2 + oi)
        # Split: redistribute my fingers, total stays same
        total = my[0] + my[1]
        if total > 0:
            for new_left in range(min(total, 4) + 1):
                new_right = total - new_left
                if new_right > 4 or new_right < 0:
                    continue
                if (new_left, new_right) == (my[0], my[1]):
                    continue  # must be different
                actions.append(10 + new_left)
        return actions

    def apply(self, action: int) -> ChopsticksState:
        h = list(self._hands)
        # Indices: player 1 = [0,1], player 2 = [2,3]
        base = 0 if self._player == 1 else 2
        opp_base = 2 if self._player == 1 else 0

        if action < 10:
            # Tap
            mi = action // 2  # 0=left, 1=right
            oi = action % 2
            attack = h[base + mi]
            result = h[opp_base + oi] + attack
            h[opp_base + oi] = 0 if result >= 5 else result
        else:
            # Split
            new_left = action - 10
            total = h[base] + h[base + 1]
            new_right = total - new_left
            h[base] = new_left
            h[base + 1] = new_right

        return ChopsticksState(tuple(h), -self._player)

    def is_terminal(self) -> bool:
        p1_dead = self._hands[0] == 0 and self._hands[1] == 0
        p2_dead = self._hands[2] == 0 and self._hands[3] == 0
        return p1_dead or p2_dead

    def result(self, player: int) -> float:
        p1_dead = self._hands[0] == 0 and self._hands[1] == 0
        if p1_dead:
            return -1.0 if player == 1 else 1.0
        return 1.0 if player == 1 else -1.0

    def to_dict(self) -> dict:
        p1_dead = self._hands[0] == 0 and self._hands[1] == 0
        p2_dead = self._hands[2] == 0 and self._hands[3] == 0
        winner = None
        if p1_dead:
            winner = -1
        elif p2_dead:
            winner = 1
        return {
            "game": self.game_id(),
            "hands": list(self._hands),  # [p1L, p1R, p2L, p2R]
            "current_player": self._player,
            "is_terminal": self.is_terminal(),
            "legal_actions": self.legal_actions(),
            "winner": winner,
            "shape": [1, 1],
            "board": list(self._hands),
        }


GAME_REGISTRY: dict[str, type[GameState]] = {
    "tictactoe": TicTacToeState,
    "twoinrow": TwoInARowState,
    "3row4x4": ThreeInRow4x4,
    "4row5x5": FourInRow5x5,
    "nim": NimState,
    "chopsticks": ChopsticksState,
}
