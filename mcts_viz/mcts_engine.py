"""MCTS engine with W/L/D tracking for visualization."""
from __future__ import annotations
import math
import random
from .game_base import GameState


class VizNode:
    __slots__ = (
        "state", "parent", "action", "children", "untried_actions",
        "visits", "wins", "win_count", "loss_count", "draw_count",
    )

    def __init__(self, state: GameState, parent: VizNode | None = None,
                 action: int | None = None):
        self.state = state
        self.parent = parent
        self.action = action
        self.children: list[VizNode] = []
        self.untried_actions = state.legal_actions()
        random.shuffle(self.untried_actions)
        self.visits = 0
        self.wins = 0.0
        self.win_count = 0
        self.loss_count = 0
        self.draw_count = 0

    @property
    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal()

    def ucb(self, c: float) -> float:
        if self.visits == 0:
            return float("inf")
        exploitation = self.wins / self.visits
        exploration = c * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration

    def best_child(self, c: float = 1.41) -> VizNode:
        return max(self.children, key=lambda ch: ch.ucb(c))

    def expand(self) -> VizNode:
        action = self.untried_actions.pop()
        child = VizNode(self.state.apply(action), parent=self, action=action)
        self.children.append(child)
        return child

    def rollout(self) -> float:
        s = self.state
        while not s.is_terminal():
            s = s.apply(random.choice(s.legal_actions()))
        parent_player = (
            self.parent.state.current_player if self.parent
            else self.state.current_player
        )
        return s.result(parent_player)

    def backpropagate(self, value: float):
        node = self
        v = value
        while node is not None:
            node.visits += 1
            node.wins += v
            if v > 0:
                node.win_count += 1
            elif v < 0:
                node.loss_count += 1
            else:
                node.draw_count += 1
            v = -v
            node = node.parent

    def to_dict(self, c: float = 1.41, max_depth: int = 30) -> dict:
        """Serialize tree to JSON-friendly dict."""
        win_rate = self.wins / self.visits if self.visits > 0 else 0
        ucb_val = None
        if self.parent and self.visits > 0:
            ucb_val = round(self.ucb(c), 4)

        d = {
            "action": self.action,
            "visits": self.visits,
            "wins": round(self.wins, 2),
            "win_rate": round(win_rate, 4),
            "W": self.win_count,
            "L": self.loss_count,
            "D": self.draw_count,
            "ucb": ucb_val,
            "state": self.state.to_dict(),
            "children": [],
        }
        if max_depth > 0:
            for ch in sorted(self.children, key=lambda c: c.visits, reverse=True):
                d["children"].append(ch.to_dict(c, max_depth - 1))
        return d


def mcts_search(state: GameState, num_simulations: int = 1000,
                c: float = 1.41) -> VizNode:
    """Run MCTS and return the root node with full tree."""
    root = VizNode(state)
    for _ in range(num_simulations):
        node = root
        while node.is_fully_expanded and not node.is_terminal:
            node = node.best_child(c)
        if not node.is_terminal:
            node = node.expand()
        value = node.rollout()
        node.backpropagate(value)
    return root
