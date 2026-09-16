"""Monotonic two-player clocks; GUI timers only request fresh readings."""
import time
import chess


class GameClock:
    def __init__(self, minutes, now=None):
        if minutes not in (1, 5, 10, 20):
            raise ValueError("Supported time controls: 1, 5, 10, 20 minutes")
        self.now = now or time.monotonic
        self.remaining_ms = {chess.WHITE: minutes * 60000.0, chess.BLACK: minutes * 60000.0}
        self.active = None
        self.anchor = self.now()

    def settle(self):
        current = self.now()
        if self.active is not None:
            self.remaining_ms[self.active] = max(0.0, self.remaining_ms[self.active] - max(0, current - self.anchor) * 1000)
        self.anchor = current
        return next((color for color in (chess.WHITE, chess.BLACK) if self.remaining_ms[color] <= 0), None)

    def switch(self, color):
        expired = self.settle()
        self.active = color if expired is None else None

    def pause(self):
        self.settle()
        self.active = None


def timeout_result(board, flagged):
    winner = not flagged
    if board.has_insufficient_material(winner):
        return "Draw"
    return f"{'White' if winner else 'Black'} wins on time"
