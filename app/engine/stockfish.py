"""Single long-lived, coalescing Stockfish analysis worker."""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import math
import random

import chess
import chess.engine
from PySide6.QtCore import QThread, Signal


def engine_startup_options():
    """python-chess forwards these options to its subprocess transport."""
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def configure_play_strength(engine, elo):
    """Respect the installed engine's actual UCI option names and bounds."""
    names = {name.casefold(): name for name in engine.options}
    if not {"uci_limitstrength", "uci_elo"}.issubset(names):
        raise ValueError("Adjustable Elo is unavailable for this engine. Select a Stockfish engine with UCI_LimitStrength and UCI_Elo in Settings.")
    option = engine.options[names["uci_elo"]]
    effective = max(option.min if option.min is not None else elo,
                    min(option.max if option.max is not None else elo, elo))
    beginner = option.min is not None and elo < option.min
    engine.configure({names["uci_limitstrength"]: not beginner, names["uci_elo"]: effective})
    return elo if beginner else effective


def below_native_range(engine, elo):
    option = next(option for name, option in engine.options.items() if name.casefold() == "uci_elo")
    return option.min is not None and elo < option.min


def choose_beginner_move(board, infos, elo):
    """Approximate difficulty, not a calibrated rating: sample evaluated candidates.

    Lower settings tolerate more centipawn loss, never unassessed random moves.
    Retain forced mating moves and avoid forced mate losses when alternatives exist.
    """
    candidates = []
    for info in infos if isinstance(infos, list) else [infos]:
        pv = info.get("pv") or []
        if pv and pv[0] in board.legal_moves and "score" in info:
            score = info["score"].pov(board.turn).score(mate_score=100000)
            if score is not None:
                candidates.append((pv[0], score))
    if not candidates:
        raise ValueError("Stockfish returned no evaluated legal candidates")
    best = max(score for _, score in candidates)
    weakness = max(0, min(1, (1320 - elo) / 720))
    loss_budget = 100 + 500 * weakness
    temperature = 25 + 225 * weakness
    bounded = [(move, best - score) for move, score in candidates if best - score <= loss_budget]
    return random.choices([move for move, _ in bounded],
                          weights=[math.exp(-loss / temperature) for _, loss in bounded], k=1)[0]


def parse_analysis(board: chess.Board, infos) -> list[tuple[str, str, int, int | None, int]]:
    if isinstance(infos, dict):
        infos = [infos]
    rows = []
    for info in infos:
        pv = info.get("pv") or []
        if not pv:
            continue
        move = pv[0]
        # All consumers use White's perspective, independent of turn/orientation.
        score = info["score"].white()
        rows.append(
            (
                board.san(move),
                move.uci(),
                score.score(mate_score=100000) or 0,
                score.mate(),
                info.get("depth", 0),
            )
        )
    return rows


class EngineWorker(QThread):
    result = Signal(int, object)
    error = Signal(int, str)

    def __init__(self, path: str, analysis_time: float = 0.6, multipv: int = 3, play_elo: int | None = None):
        super().__init__()
        self.path = path
        self.analysis_time = analysis_time
        self.multipv = multipv
        self.play_elo = play_elo
        self._condition = threading.Condition()
        self._pending = None
        self._running = True

    def submit(self, fen: str, token: int):
        with self._condition:
            self._pending = (fen, token)
            self._condition.notify()

    def submit_play(self, board: chess.Board, token: int):
        # Preserve repetition history for the playing engine.
        with self._condition:
            self._pending = (board.copy(stack=True), token)
            self._condition.notify()

    def run(self):
        engine = None
        try:
            if not self.path or not os.path.isfile(self.path):
                raise FileNotFoundError("Stockfish executable is not configured")
            engine = chess.engine.SimpleEngine.popen_uci(self.path, **engine_startup_options())
            effective_elo = configure_play_strength(engine, self.play_elo) if self.play_elo is not None else None
            beginner = self.play_elo is not None and below_native_range(engine, self.play_elo)
            while self._running:
                with self._condition:
                    while self._pending is None and self._running:
                        self._condition.wait(0.5)
                    if not self._running:
                        break
                    fen, token = self._pending
                    self._pending = None
                try:
                    board = fen if isinstance(fen, chess.Board) else chess.Board(fen)
                    if board.is_game_over():
                        self.result.emit(token, [])
                        continue
                    if self.play_elo is not None:
                        if beginner:
                            infos = engine.analyse(board, chess.engine.Limit(time=self.analysis_time),
                                                   multipv=min(12, board.legal_moves.count()))
                            move = choose_beginner_move(board, infos, self.play_elo)
                        else:
                            move = engine.play(board, chess.engine.Limit(time=self.analysis_time)).move
                        self.result.emit(token, (move, effective_elo))
                        continue
                    infos = engine.analyse(
                        board,
                        chess.engine.Limit(time=self.analysis_time),
                        multipv=self.multipv,
                    )
                    self.result.emit(token, parse_analysis(board, infos))
                except Exception as exc:
                    logging.exception("Stockfish analysis failed")
                    self.error.emit(token, str(exc))
        except Exception as exc:
            logging.exception("Stockfish worker failed")
            self.error.emit(-1, str(exc))
        finally:
            if engine:
                try:
                    engine.quit()
                except Exception:
                    logging.exception("Stockfish shutdown failed")

    def request_stop(self):
        with self._condition:
            self._running = False
            self._pending = None
            self._condition.notify_all()

    def stop(self):
        self.request_stop()
        self.wait(3000)
