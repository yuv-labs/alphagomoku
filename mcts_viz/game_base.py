"""Game-agnostic interfaces for MCTS visualization."""
from __future__ import annotations
from abc import ABC, abstractmethod


class GameState(ABC):
    """2-player zero-sum game state interface.

    Rules:
    - States are immutable — apply() always returns a new object.
    - Players are 1 (first) or -1 (second).
    """

    @property
    @abstractmethod
    def current_player(self) -> int: ...

    @abstractmethod
    def legal_actions(self) -> list[int]: ...

    @abstractmethod
    def apply(self, action: int) -> GameState: ...

    @abstractmethod
    def is_terminal(self) -> bool: ...

    @abstractmethod
    def result(self, player: int) -> float:
        """Result from player's perspective: 1=win, -1=loss, 0=draw."""
        ...

    @abstractmethod
    def to_dict(self) -> dict:
        """Serialize state for JSON transport to frontend."""
        ...

    @classmethod
    @abstractmethod
    def game_id(cls) -> str:
        """Unique identifier for this game type (e.g. 'tictactoe')."""
        ...

    @classmethod
    @abstractmethod
    def board_shape(cls) -> tuple[int, int]:
        """(rows, cols) for the board."""
        ...

    @classmethod
    @abstractmethod
    def action_to_coords(cls, action: int) -> tuple[int, int]:
        """Convert action int to (row, col)."""
        ...
