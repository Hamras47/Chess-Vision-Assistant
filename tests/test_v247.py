from types import SimpleNamespace
from threading import Event
import os

import chess
import chess.engine
import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit, QComboBox, QVBoxLayout

from app.ai.openai_client import OpenAIClient, resolve_model
from app.ai.board_recognizer import _recognize_with_retries
from app.engine.stockfish import engine_startup_options, parse_analysis
from app.ui.main_window import MainWindow
from app.ui.evaluation_bar import EvaluationBar, white_fraction, evaluation_text
from app.ui.settings import SettingsDialog
from app.vision.capture import validated_board_crop, ScreenCapture


@pytest.fixture
def window(monkeypatch, qtbot):
    monkeypatch.setattr(MainWindow, "_find_engine", lambda self: "")
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.activateWindow()
    window.view.setFocus()
    QApplication.processEvents()
    yield window
    window.close()


def arrow(window, key):
    window.activateWindow()
    window.view.setFocus()
    QApplication.processEvents()
    QTest.keyClick(window.view, key)


@pytest.mark.parametrize("fen,uci", [
    (chess.STARTING_FEN, "e2e4"),
    ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1"),
    ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2", "e5d6"),
    ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8q"),
])
def test_arrow_exact_history(window, monkeypatch, fen, uci):
    from app.ui.promotion_dialog import PromotionDialog
    monkeypatch.setattr(PromotionDialog, "choose", lambda *args: chess.QUEEN)
    window.game.load(chess.Board(fen), chess.BLACK)
    window.view.set_board(window.board)
    window.flip_board()
    orientation = window.view.orientation
    before = window.board.fen(en_passant="fen")
    move = chess.Move.from_uci(uci)
    assert window.commit_manual_move(move.from_square, move.to_square)
    after = window.board.fen(en_passant="fen")
    arrow(window, Qt.Key_Left)
    assert window.board.fen(en_passant="fen") == before
    assert window.view._animated_move is None
    arrow(window, Qt.Key_Right)
    assert window.board.fen(en_passant="fen") == after
    assert window.view.orientation == orientation


def test_multiple_history_and_branch(window):
    positions = [window.board.fen()]
    for uci in ("e2e4", "e7e5", "g1f3"):
        move = chess.Move.from_uci(uci)
        window.commit_manual_move(move.from_square, move.to_square)
        positions.append(window.board.fen())
    for expected in reversed(positions[:-1]):
        arrow(window, Qt.Key_Left)
        assert window.board.fen() == expected
    for expected in positions[1:]:
        arrow(window, Qt.Key_Right)
        assert window.board.fen() == expected
    arrow(window, Qt.Key_Left)
    window.commit_manual_move(chess.F1, chess.C4)
    assert not window.game.can_redo


@pytest.mark.parametrize("kind", [QLineEdit, QComboBox])
def test_focus_consumes_arrows(window, kind):
    window.commit_manual_move(chess.E2, chess.E4)
    edit = kind(window.centralWidget())
    if isinstance(edit, QLineEdit):
        edit.setText("api-key-example")
    else:
        edit.addItems(["One", "Two"])
    edit.show()
    edit.setFocus()
    QApplication.processEvents()
    QTest.keyClick(edit, Qt.Key_Left)
    assert len(window.board.move_stack) == 1
    edit.deleteLater()


def test_modal_blocks_history(window, qtbot):
    window.commit_manual_move(chess.E2, chess.E4)
    dialog = QDialog(window)
    dialog.setModal(True)
    qtbot.addWidget(dialog)
    dialog.show()
    QApplication.processEvents()
    QTest.keyClick(dialog, Qt.Key_Left)
    assert len(window.board.move_stack) == 1
    dialog.close()


def fake_engine(window):
    calls = []
    window.engine_path = "fake-stockfish"
    state = {"running": True}
    window.engine_worker = SimpleNamespace(isRunning=lambda: state["running"], submit=lambda fen, token: calls.append((fen, token)), request_stop=lambda: state.update(running=False))
    return calls


def test_toggle_history_stale_results(window):
    calls = fake_engine(window)
    window.commit_manual_move(chess.E2, chess.E4)
    stale_token = calls[-1][1]
    arrow(window, Qt.Key_Left)
    arrow(window, Qt.Key_Right)
    assert len(calls) == 3
    window.analysis_done(stale_token, [("e5", "e7e5", 30, None, 10)])
    assert not window.eval_bar.active
    window.suggestions_enabled = False
    window.analyze()
    arrow(window, Qt.Key_Left)
    arrow(window, Qt.Key_Right)
    window.commit_manual_move(chess.E7, chess.E5)
    assert len(calls) == 3
    window.analysis_done(window.analysis_token, [("Nf3", "g1f3", 20, None, 10)])
    assert window.view.arrow is None
    assert not window.eval_bar.active
    assert window.panel.best_button.text() == "Off"


def test_model_toggle_persist_and_next_scan(window, monkeypatch):
    monkeypatch.setattr(SettingsDialog, "exec", lambda self: (self.model.setCurrentIndex(1), self.suggestions.setChecked(False), 1)[-1])
    window.open_settings()
    assert window.settings.value("ai_model") == "gpt-5.6-luna"
    assert window.openai_client.model == "gpt-5.6-luna"
    restarted = MainWindow()
    try:
        assert restarted.model == "gpt-5.6-luna"
        assert not restarted.suggestions_enabled
        monkeypatch.setattr(SettingsDialog, "exec", lambda self: (self.model.setCurrentIndex(0), self.suggestions.setChecked(True), 1)[-1])
        restarted.open_settings()
        assert restarted.model == "gpt-5.6-terra"
        assert restarted.suggestions_enabled
    finally:
        restarted.close()


@pytest.mark.parametrize("model", ["gpt-5.6-terra", "gpt-5.6-luna"])
def test_exact_request_routing(model):
    calls = []
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: (calls.append(kwargs), SimpleNamespace(output_text='{}'))[1]))
    OpenAIClient(model, client=client, api_key="mock-key").recognize(b"png", {}, "prompt")
    assert len(calls) == 1 and calls[0]["model"] == model


def test_model_fallback():
    assert resolve_model("bad", {}) == "gpt-5.6-terra"
    assert resolve_model("gpt-5.6-luna", {"OPENAI_VISION_MODEL": "gpt-5.6-terra"}) == "gpt-5.6-luna"


def test_eval_mapping_and_mate(window):
    assert white_fraction(0) == 0.5
    assert 0.5 < white_fraction(70) < white_fraction(10000) < 1
    assert 0 < white_fraction(-10000) < white_fraction(-70) < 0.5
    assert evaluation_text(mate=3) == "M3"
    assert evaluation_text(mate=-2) == "-M2"
    window.eval_bar.set_evaluation(70)
    fraction = window.eval_bar.target_fraction
    window.flip_board()
    assert window.eval_bar.target_fraction == fraction
    assert window.eval_bar.text == "+0.7"
    assert window.eval_bar.flipped
    for width in (1400, 960, 800, 700):
        window.resize(width, 900)
        QApplication.processEvents()
        assert window.eval_bar.height() == window.view.height() - 8
        assert window.eval_bar.x() + window.eval_bar.width() < window.view.x()
    window.eval_bar.set_inactive()
    assert window.eval_bar.text == "--" and window.eval_bar.fraction == .5


def test_black_mate_white_perspective():
    board = chess.Board()
    board.push_uci("e2e4")
    info = {"score": chess.engine.PovScore(chess.engine.Mate(2), chess.BLACK), "pv": [chess.Move.from_uci("e7e5")]}
    assert parse_analysis(board, info)[0][3] == -2


def test_footer_feedback_never_resizes_board(window):
    window.resize(1150, 800)
    QApplication.processEvents()
    geometry = window.view.geometry()
    window.status.setText("Analyzing position…")
    QApplication.processEvents()
    assert window.view.geometry() == geometry
    window.status.setText("")
    QApplication.processEvents()
    assert window.view.geometry() == geometry
    window.commit_manual_move(chess.E2, chess.E4)
    assert window.panel.turn_label.text() == "Black to move"


def image():
    return np.tile(np.arange(128, dtype=np.uint8)[None, :, None], (128, 1, 3))


@pytest.mark.parametrize("bad", [None, np.zeros((128,128,3), np.uint8), np.zeros((10,10,3), np.uint8), np.full((128,128,3), [255,0,0], np.uint8)])
def test_invalid_captures(bad):
    with pytest.raises(ValueError):
        validated_board_crop(bad)


@pytest.mark.parametrize("blank", [False, True])
def test_capture_one_local_retry_one_dispatch(window, monkeypatch, qtbot, blank):
    api_calls, captures = [], []
    window._scan_active = True
    window.hide()
    region = {"left": -300, "top": 45, "width": 128, "height": 128}
    def capture(self, physical):
        assert not window.isVisible() and not window.selectors
        captures.append(physical)
        return image()
    monkeypatch.setattr(ScreenCapture, "region", capture)
    monkeypatch.setattr(window, "_start_recognition", lambda crop, token: api_calls.append(token))
    window.snip_selected({"physical": region, "frozen_image": np.zeros((128,128,3), np.uint8) if blank else image()})
    qtbot.waitUntil(lambda: len(api_calls) == 1)
    assert captures == ([region] if blank else [])
    assert len(api_calls) == 1


def test_no_api_retry_on_failure():
    calls = []
    class Client:
        def recognize(self, *args):
            calls.append(1)
            raise RuntimeError("mock failure")
    with pytest.raises(Exception):
        _recognize_with_retries(image(), "gpt-5.6-terra", False, Client(), Event())
    assert len(calls) == 1


def test_invalid_recapture_stops_without_api(window, monkeypatch, qtbot):
    captures, errors, calls = [], [], []
    window._scan_active = True
    window.hide()
    monkeypatch.setattr(ScreenCapture, "region", lambda self, region: (captures.append(region), np.zeros((128,128,3), np.uint8))[1])
    monkeypatch.setattr(window, "user_error", errors.append)
    monkeypatch.setattr(window, "_start_recognition", lambda *args: calls.append(1))
    window.snip_selected({"physical": {"left": 0, "top": 0, "width": 128, "height": 128}, "frozen_image": np.zeros((128,128,3), np.uint8)})
    qtbot.waitUntil(lambda: bool(errors))
    assert len(captures) == 1 and not calls
    assert window.isVisible() and not window._scan_active


def test_app_hides_before_frozen_capture(window, monkeypatch):
    from app.ui.main_window import QTimer
    scheduled = []
    monkeypatch.setattr(window.openai_client, "ready", lambda: True)
    monkeypatch.setattr(QTimer, "singleShot", lambda delay, callback: scheduled.append((delay, callback)))
    window.scan_board()
    assert not window.isVisible()
    assert scheduled[0][0] == 180
    assert window._scan_active
    window.snip_cancelled()


def test_windows_engine_flags():
    import subprocess
    expected = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    assert engine_startup_options() == expected


def test_close_retains_slow_engine_without_blocking(window, qtbot):
    from PySide6.QtCore import QThread
    class SlowWorker(QThread):
        def run(self):
            self.msleep(180)
        def request_stop(self):
            pass
    worker = SlowWorker()
    window.engine_worker = worker
    worker.start()
    window.close()
    assert window.isVisible()
    assert window.engine_worker is worker
    assert window._closing
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=2000)
    assert not worker.isRunning()
    assert window.engine_worker is None


@pytest.mark.parametrize("change", ["new", "move", "undo", "redo"])
def test_board_change_rejects_pending_scan(window, monkeypatch, change):
    from app.ui.setup_dialog import PositionSetupDialog
    window.commit_manual_move(chess.E2, chess.E4)
    if change == "redo":
        window.undo()
    window._scan_active = True
    token = window.scan_token
    if change == "new":
        window.load_position(chess.Board(), chess.WHITE, chess.WHITE, imported=False)
        window.commit_manual_move(chess.D2, chess.D4)
    elif change == "move":
        window.commit_manual_move(chess.E7, chess.E5)
    else:
        getattr(window, change)()
    current = window.board.fen()
    def unexpected(*args, **kwargs):
        pytest.fail("obsolete scan must not show confirmation")
    monkeypatch.setattr(PositionSetupDialog, "get_values", unexpected)
    window.scan_done(token, chess.Board(), SimpleNamespace(confidence=1), .1)
    assert window.board.fen() == current
