"""Small per-game configuration; canonical moves stay in ManualGameState."""
from dataclasses import dataclass
from enum import Enum
import random

import chess


class GameMode(Enum):
    ANALYSIS = "Analysis"
    LOCAL_PVP = "Player vs Player"
    VS_COMPUTER = "Player vs Computer"


@dataclass(frozen=True)
class GameOptions:
    mode: GameMode = GameMode.ANALYSIS
    color: str = "White"
    elo: int = 1400
    evaluation: bool = True
    suggestions: bool = False
    allow_history: bool = True

    def resolve_color(self):
        return random.choice((chess.WHITE, chess.BLACK)) if self.color == "Random" else self.color == "White"


def remaining_move_delay(started: float, now: float) -> int:
    """Presentation minimum overlaps engine calculation, never adds to it."""
    import math
    return max(0, math.ceil((0.8 - (now - started)) * 1000))
