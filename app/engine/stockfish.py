"""Single long-lived, coalescing Stockfish analysis worker."""
from __future__ import annotations

import logging
import os
import threading

import chess
import chess.engine
from PySide6.QtCore import QThread, Signal


def parse_analysis(board: chess.Board, infos) -> list[tuple[str, str, int, int | None, int]]:
    if isinstance(infos, dict):
        infos = [infos]
    rows = []
    for info in infos:
        pv = info.get("pv") or []
        if not pv:
            continue
        move = pv[0]
        score = info["score"].pov(board.turn)
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

    def __init__(self, path: str, analysis_time: float = 0.6, multipv: int = 3):
        super().__init__()
        self.path = path
        self.analysis_time = analysis_time
        self.multipv = multipv
        self._condition = threading.Condition()
        self._pending = None
        self._running = True

    def submit(self, fen: str, token: int):
        with self._condition:
            self._pending = (fen, token)
            self._condition.notify()

    def run(self):
        engine = None
        try:
            if not self.path or not os.path.isfile(self.path):
                raise FileNotFoundError("Stockfish executable is not configured")
            engine = chess.engine.SimpleEngine.popen_uci(self.path)
            while self._running:
                with self._condition:
                    while self._pending is None and self._running:
                        self._condition.wait(0.5)
                    if not self._running:
                        break
                    fen, token = self._pending
                    self._pending = None
                try:
                    board = chess.Board(fen)
                    if board.is_game_over():
                        self.result.emit(token, [])
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

    def stop(self):
        with self._condition:
            self._running = False
            self._condition.notify_all()
        self.wait(3000)
