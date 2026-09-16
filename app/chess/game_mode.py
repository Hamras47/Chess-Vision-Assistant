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
    minutes: int = 10
    white_name: str = ""
    black_name: str = ""
    human_name: str = ""

    def resolve_color(self):
        return random.choice((chess.WHITE, chess.BLACK)) if self.color == "Random" else self.color == "White"


def thinking_delay_ms(elo: int) -> int:
    if elo < 1000:
        return random.randint(1200, 1600)
    if elo < 1400:
        return random.randint(1000, 1400)
    if elo < 1900:
        return random.randint(900, 1200)
    return random.randint(750, 1000)


def remaining_move_delay(started: float, now: float, target_ms: int = 800) -> int:
    """Presentation minimum overlaps engine calculation, never adds to it."""
    import math
    return max(0, math.ceil(target_ms - (now - started) * 1000))
