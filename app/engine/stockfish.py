"""Single long-lived, coalescing Stockfish analysis worker."""
from __future__ import annotations

import logging
import os
import subprocess
import threading

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
    engine.configure({names["uci_limitstrength"]: True, names["uci_elo"]: effective})
    return effective


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
                        reply = engine.play(board, chess.engine.Limit(time=self.analysis_time))
                        self.result.emit(token, (reply.move, effective_elo))
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
