"""Manual analysis-board main window."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

import chess
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.ai.board_recognizer import RecognitionWorker
from app.ai.openai_client import OpenAIClient, resolve_model
from app.chess.coordinates import Orientation
from app.chess.game_state import ManualGameState, turn_from_selection
from app.core.logging_setup import LOG_DIRECTORY, configure, install_exception_hook
from app.engine.stockfish import EngineWorker
from app.ui.analysis_panel import AnalysisPanel
from app.ui.board_widget import ChessBoardWidget
from app.ui.dpi_coordinates import match_monitor
from app.ui.promotion_dialog import PromotionDialog
from app.ui.region_selector import RegionSelector
from app.ui.settings import SettingsDialog
from app.ui.setup_dialog import PositionSetupDialog
from app.vision.capture import ScreenCapture, square_crop

PROJECT_ROOT = Path(__file__).resolve().parents[2]

STYLE = """
QMainWindow, QWidget#root { background: #101416; color: #eef2ef; }
QWidget { color: #e9eeeb; font-family: "Segoe UI"; font-size: 14px; }
QLabel#appTitle { font-size: 21px; font-weight: 600; color: #f4f6f4; }
QLabel#appSubtitle, QLabel#muted { color: #98a39e; }
QLabel#positionOwner { font-size: 18px; font-weight: 600; }
QLabel#stateLabel { color: #e7bd65; font-weight: 600; }
QLabel#eyebrow, QLabel#dialogEyebrow { color: #91a099; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
QLabel#moveCoordinates { color: #a8b4ae; font-size: 14px; }
QLabel#evaluation { color: #cbd4cf; font-size: 16px; }
QLabel#alternative { background: rgba(255,255,255,0.035); border-radius: 7px; padding: 7px 10px; }
QLabel#history { background: transparent; padding: 3px; color: #cbd3cf; }
QFrame#analysisCard { background: rgba(26,31,32,0.94); border: 1px solid rgba(255,255,255,0.09); border-radius: 13px; }
QScrollArea#historyScroll { border: none; background: rgba(7,10,11,0.25); border-radius: 8px; }
QScrollArea#historyScroll > QWidget > QWidget { background: transparent; }
QPushButton { background: #2a3131; color: #edf2ef; border: 1px solid #3b4542; border-radius: 8px; padding: 8px 12px; }
QPushButton:hover { background: #343e3b; border-color: #52605b; }
QPushButton:pressed { background: #202625; }
QPushButton:disabled { color: #68736e; background: #202524; border-color: #2b3230; }
QPushButton#primaryButton { background: #3f745f; border-color: #568a73; font-weight: 600; }
QPushButton#primaryButton:hover { background: #4a836c; }
QPushButton#bestMove { background: transparent; border: none; padding: 0; text-align: left; font-size: 31px; font-weight: 650; color: #f4f6f4; }
QPushButton#bestMove:hover { color: #a9d2bd; }
QPushButton#utilityButton { padding: 7px 12px; color: #b8c2bd; }
QPushButton#choiceButton { min-width: 125px; padding: 13px; }
QPushButton#choiceButton:checked { background: #477b67; border-color: #72a18d; }
QDialog { background: #181d1e; }
QLineEdit, QComboBox { background: #222829; border: 1px solid #3a4542; border-radius: 7px; padding: 7px; }
QLabel#apiLoaded { color: #85c6a5; }
QLabel#apiMissing { color: #e3ad69; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("ChessVisionAssistant", "V16")
        self.debug = self.settings.value("debug_mode", False, type=bool) or os.getenv("CHESS_VISION_DEBUG") == "1"
        configure(self.debug)
        stored_model = self.settings.value("ai_model", "", type=str)
        self.model = resolve_model(stored_model)
        self.openai_client = OpenAIClient(self.model)
        self.game = ManualGameState()
        self.engine_path = self._find_engine()
        self.analysis_ms = int(self.settings.value("analysis_time_ms", 600))
        self.engine_worker = None
        self.ai_worker = None
        self.selectors = []
        self.scan_token = 0
        self.analysis_token = 0
        self.has_imported_position = False
        self._closing = False
        logging.info("APP_START")
        logging.info("OPENAI_MODEL_RESOLVED model=%s source=%s", self.model, "settings" if stored_model else "environment_or_default")
        self.setWindowTitle("Chess Vision Assistant V1.6")
        self.resize(1150, 800)
        self.setMinimumSize(900, 650)
        self._build_ui()
        self.setStyleSheet(STYLE)
        self._install_shortcuts()
        self.view.set_board(self.game.board)
        self._update_position(ready=True)
        if self.engine_path:
            self._start_engine()
        else:
            self.panel.set_unavailable()
            self.status.setText("Stockfish not configured — manual board is ready")
        install_exception_hook(self.crash_context)

    @property
    def board(self):
        return self.game.board

    @property
    def player_color(self):
        return self.game.player_color

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(14)
        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title_group.setSpacing(0)
        title = QLabel("Chess Vision")
        title.setObjectName("appTitle")
        subtitle = QLabel("Manual analysis board")
        subtitle.setObjectName("appSubtitle")
        title_group.addWidget(title)
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()
        flip = QPushButton("Flip")
        flip.setToolTip("Flip board (F)")
        flip.setObjectName("utilityButton")
        flip.clicked.connect(self.flip_board)
        settings = QPushButton("Settings")
        settings.setToolTip("Settings")
        settings.setObjectName("utilityButton")
        settings.clicked.connect(self.open_settings)
        header.addWidget(flip)
        header.addWidget(settings)
        outer.addLayout(header)
        body = QHBoxLayout()
        body.setSpacing(22)
        board_host = QWidget()
        board_layout = QVBoxLayout(board_host)
        board_layout.setContentsMargins(0, 0, 0, 0)
        self.view = ChessBoardWidget()
        self.view.move_requested.connect(self.commit_manual_move)
        board_layout.addWidget(self.view, 1)
        body.addWidget(board_host, 1)
        self.panel = AnalysisPanel()
        self.panel.undo_requested.connect(self.undo)
        self.panel.redo_requested.connect(self.redo)
        self.panel.scan_requested.connect(self.scan_board)
        self.panel.new_game_requested.connect(self.new_game)
        self.panel.best_move_clicked.connect(self.pulse_best_move)
        body.addWidget(self.panel)
        outer.addLayout(body, 1)
        self.status = QLabel("Ready")
        self.status.setObjectName("muted")
        outer.addWidget(self.status)

    def _install_shortcuts(self):
        for sequence, callback in (("Ctrl+Z", self.undo), ("Ctrl+Y", self.redo), ("Ctrl+R", self.scan_board), ("Ctrl+N", self.new_game), ("F", self.flip_board), ("Escape", self.view.clear_selection)):
            QShortcut(QKeySequence(sequence), self, activated=callback)

    def _find_engine(self):
        stored = self.settings.value("stockfish", "", type=str)
        if stored and Path(stored).is_file():
            return stored
        found = shutil.which("stockfish")
        if found:
            return found
        for path in PROJECT_ROOT.glob("**/stockfish*.exe"):
            if ".venv" not in path.parts:
                return str(path.resolve())
        return ""

    def _start_engine(self):
        if self.engine_worker:
            self.engine_worker.stop()
        self.engine_worker = EngineWorker(self.engine_path, self.analysis_ms / 1000, multipv=3)
        self.engine_worker.result.connect(self.analysis_done)
        self.engine_worker.error.connect(self.analysis_failed)
        self.engine_worker.start()

    def analyze(self):
        self.analysis_token += 1
        token = self.analysis_token
        self.view.arrow = None
        self.view.update()
        if self.board.is_game_over():
            self.panel.clear_analysis()
            return
        if not self.engine_path:
            self.panel.set_unavailable()
            self.status.setText("Stockfish not configured — manual board is ready")
            return
        if not self.engine_worker or not self.engine_worker.isRunning():
            self._start_engine()
        self.panel.set_analyzing()
        self.status.setText("Analyzing position…")
        logging.info("STOCKFISH_START token=%d turn=%s", token, "white" if self.board.turn else "black")
        self.engine_worker.submit(self.board.fen(), token)

    def analysis_done(self, token, rows):
        if token != self.analysis_token:
            logging.info("Discarded stale Stockfish result token=%d current=%d", token, self.analysis_token)
            return
        self.panel.set_analysis(rows)
        if rows:
            uci = rows[0][1]
            self.view.arrow = (chess.parse_square(uci[:2]), chess.parse_square(uci[2:4]))
            self.view.update()
            logging.info("STOCKFISH_RESULT token=%d best=%s alternatives=%d", token, uci, max(0, len(rows) - 1))
        self.status.setText("Ready")

    def analysis_failed(self, token, error):
        if token not in (-1, self.analysis_token):
            return
        logging.error("Stockfish unavailable token=%d error=%s", token, error)
        self.panel.set_unavailable()
        self.status.setText("Stockfish not configured — manual board is ready")

    def _update_position(self, ready=False):
        owner, turn = self.game.turn_labels()
        self.panel.set_position("Ready" if ready else owner, turn, self.game.outcome_status())
        self.panel.set_history(self.game.history_text())
        self.panel.set_undo_redo(self.game.can_undo, self.game.can_redo)

    def load_position(self, board, player_color, side_to_move, imported=True):
        loaded = chess.Board() if board.board_fen() == chess.STARTING_BOARD_FEN else board.copy(stack=False)
        loaded.turn = side_to_move
        if loaded.board_fen() != chess.STARTING_BOARD_FEN:
            loaded.castling_rights = chess.BB_EMPTY
            loaded.ep_square = None
        self.game.load(loaded, player_color)
        self.has_imported_position = imported
        self.view.set_orientation(Orientation.WHITE_BOTTOM if player_color else Orientation.BLACK_BOTTOM)
        self.view.arrow = None
        self.view.set_board(self.board)
        self.panel.clear_analysis()
        self.panel.set_scan_mode(imported)
        self._update_position()
        logging.info("POSITION_LOADED fen=%s player=%s", self.board.fen(), "white" if player_color else "black")
        self.analyze()

    def commit_manual_move(self, source, target):
        promotion = None
        if self.game.promotion_options(source, target):
            promotion = PromotionDialog.choose(self.board.turn, self)
            if promotion is None:
                self.view.clear_selection()
                return False
        before = self.board.copy(stack=True)
        try:
            record = self.game.make_move(source, target, promotion)
        except ValueError:
            logging.info("Illegal manual move blocked source=%s target=%s", chess.square_name(source), chess.square_name(target))
            self.status.setText("That move is not legal")
            return False
        self.view.animate_move(before, record.move, self.board)
        self._update_position()
        logging.info("MANUAL_MOVE san=%s uci=%s fen=%s", record.san, record.move.uci(), self.board.fen())
        self.analyze()
        return True

    def undo(self):
        record = self.game.undo()
        if not record:
            return False
        self.view.arrow = None
        self.view.set_board(self.board, self.board.peek() if self.board.move_stack else None)
        self._update_position()
        logging.info("UNDO san=%s fen=%s", record.san, self.board.fen())
        self.analyze()
        return True

    def redo(self):
        before = self.board.copy(stack=True)
        record = self.game.redo()
        if not record:
            return False
        self.view.animate_move(before, record.move, self.board)
        self._update_position()
        logging.info("REDO san=%s fen=%s", record.san, self.board.fen())
        self.analyze()
        return True

    def new_game(self):
        values = PositionSetupDialog.get_values(self, ask_turn=False, initial_color=self.player_color)
        if values is None:
            return
        player_color, _ = values
        self.load_position(chess.Board(), player_color, chess.WHITE, imported=False)
        self.status.setText("New game ready")

    def flip_board(self):
        self.view.flip()

    def pulse_best_move(self):
        if not self.view.arrow:
            return
        source, target = self.view.arrow
        self.view.selected = source
        self.view.legal_targets = {target: self.board.piece_at(target) is not None}
        self.view.update()
        QTimer.singleShot(280, self.view.clear_selection)

    def scan_board(self):
        if self.ai_worker and self.ai_worker.isRunning():
            return
        self.scan_token += 1
        logging.info("SCAN_STARTED token=%d", self.scan_token)
        self.status.setText("Select the chessboard")
        self.hide()
        QTimer.singleShot(180, self.begin_snip)

    def begin_snip(self):
        try:
            frames = ScreenCapture().monitor_frames()
            monitors = [monitor for _, monitor in frames]
            self.selectors = []
            for screen in QApplication.screens():
                mapping = match_monitor(screen, monitors)
                frame = next(image for image, monitor in frames if monitor is mapping.physical)
                selector = RegionSelector(frame, mapping)
                selector.selected.connect(self.snip_selected)
                selector.cancelled.connect(self.snip_cancelled)
                selector.show()
                self.selectors.append(selector)
            if self.selectors:
                self.selectors[0].activateWindow()
        except Exception:
            logging.exception("OPENAI_SCAN_FAILED reason=desktop_capture")
            self._close_selectors()
            self.show()
            self.user_error("Could not capture the desktop.")

    def _close_selectors(self):
        for selector in self.selectors:
            selector.hide()
            selector.deleteLater()
        self.selectors = []

    def snip_cancelled(self):
        self._close_selectors()
        self.show()
        self.status.setText("Ready")

    def snip_selected(self, selection):
        self._close_selectors()
        physical = selection["physical"]
        logging.info("BOARD_REGION_SELECTED x=%d y=%d width=%d height=%d", physical["left"], physical["top"], physical["width"], physical["height"])
        try:
            crop = square_crop(selection["frozen_image"])
            if self.debug:
                debug_path = LOG_DIRECTORY / "debug"
                debug_path.mkdir(parents=True, exist_ok=True)
                import cv2
                cv2.imwrite(str(debug_path / "latest_openai_board.png"), crop)
            self.show()
            self.raise_()
            self.status.setText("Reading board with Luna…")
            self.panel.set_position("Scanning…", "One-time position import")
            self._start_recognition(crop, self.scan_token)
        except Exception:
            logging.exception("OPENAI_SCAN_FAILED reason=invalid_selection")
            self.show()
            self.user_error("Could not capture the selected board.")

    def _start_recognition(self, crop, token):
        if not self.openai_client.ready():
            logging.error("OPENAI_SCAN_FAILED reason=api_key_missing")
            self.user_error("OpenAI API key not configured. Add OPENAI_API_KEY to .env.")
            self._update_position()
            return
        self.ai_worker = RecognitionWorker(crop, self.model, self.debug, self.openai_client)
        self.ai_worker.result.connect(lambda board, result, latency: self.scan_done(token, board, result, latency))
        self.ai_worker.error.connect(lambda error: self.scan_failed(token, error))
        self.ai_worker.start()

    def scan_done(self, token, board, result, latency):
        if token != self.scan_token:
            return
        logging.info("OPENAI_SCAN_SUCCESS token=%d confidence=%.3f latency=%.3f", token, result.confidence, latency)
        values = PositionSetupDialog.get_values(self, ask_turn=True, initial_color=self.player_color)
        if values is None:
            self._update_position()
            self.status.setText("Scan cancelled")
            return
        player_color, my_turn = values
        board.turn = turn_from_selection(player_color, my_turn)
        logging.info("PLAYER_COLOR_SELECTED color=%s", "white" if player_color else "black")
        logging.info("TURN_SELECTED turn=%s", "white" if board.turn else "black")
        self.load_position(board, player_color, board.turn, imported=True)
        self.status.setText("Position imported")

    def scan_failed(self, token, error):
        if token != self.scan_token:
            return
        logging.error("OPENAI_SCAN_FAILED token=%d error=%s", token, error)
        self._update_position()
        self.user_error("Could not verify board. Try Rescan.")

    def open_settings(self):
        dialog = SettingsDialog(self.model, self.engine_path, self.analysis_ms, self)
        if not dialog.exec():
            return
        model, engine_path, analysis_ms = dialog.values()
        self.model = resolve_model(model)
        self.openai_client = OpenAIClient(self.model)
        self.settings.setValue("ai_model", self.model)
        self.settings.setValue("analysis_time_ms", analysis_ms)
        self.analysis_ms = analysis_ms
        if engine_path and Path(engine_path).is_file():
            self.engine_path = engine_path
            self.settings.setValue("stockfish", engine_path)
            self._start_engine()
            self.analyze()
        elif engine_path:
            QMessageBox.warning(self, "Settings", "The selected Stockfish executable does not exist.")
        logging.info("OPENAI_MODEL_RESOLVED model=%s source=settings", self.model)

    def user_error(self, text):
        self.status.setText(text)
        QMessageBox.warning(self, "Chess Vision", text)

    def crash_context(self):
        return {"fen": self.board.fen(), "board_version": self.game.version, "scan_active": bool(self.ai_worker and self.ai_worker.isRunning())}

    def closeEvent(self, event):
        if self.ai_worker and self.ai_worker.isRunning() and not self._closing:
            self._closing = True
            self.scan_token += 1
            self.status.setText("Finishing current scan before closing…")
            self.ai_worker.finished.connect(self.close)
            event.ignore()
            return
        self._closing = True
        self._close_selectors()
        if self.engine_worker:
            self.engine_worker.stop()
            self.engine_worker = None
        super().closeEvent(event)
