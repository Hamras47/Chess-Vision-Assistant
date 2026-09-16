"""Focused mode checks: no network and no external engine required."""
from dataclasses import replace
from types import SimpleNamespace

import chess
import chess.engine
import pytest
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtTest import QTest

from app.chess.game_mode import GameMode, GameOptions, remaining_move_delay
from app.engine.stockfish import EngineWorker, configure_play_strength
from app.ui.main_window import MainWindow
from app.ui.new_game_dialog import NewGameDialog


class FakeWorker(QObject):
    result = Signal(int, object)
    error = Signal(int, str)
    finished = Signal()

    def __init__(self, path, analysis_time, multipv=3, play_elo=None):
        super().__init__()
        self.play_elo = play_elo
        self.requests = []
        self.running = False

    def start(self): self.running = True
    def isRunning(self): return self.running
    def submit(self, board, token): self.requests.append((board, token))
    def submit_play(self, board, token): self.requests.append((board.copy(stack=True), token))
    def request_stop(self): self.running = False


@pytest.fixture
def window(monkeypatch, qtbot):
    monkeypatch.setattr(MainWindow, "_find_engine", lambda self: "")
    monkeypatch.setattr("app.ui.main_window.EngineWorker", FakeWorker)
    window = MainWindow()
    window.engine_path = "fake-engine"
    qtbot.addWidget(window)
    window.show()
    yield window
    window.close()


def move(window, uci):
    parsed = chess.Move.from_uci(uci)
    return window.commit_manual_move(parsed.from_square, parsed.to_square)


def reply(window, uci):
    # Controller-only check; separate tests exercise timer and worker dispatch.
    window._apply_computer_move(window.play_token, chess.Move.from_uci(uci))


@pytest.mark.parametrize("mode", list(GameMode))
def test_modes_start_and_legal_turns(window, mode):
    window.start_game(GameOptions(mode))
    assert window.mode == mode
    assert move(window, "e2e4")
    if mode == GameMode.VS_COMPUTER:
        assert window.play_worker.requests
        assert not window.view.isEnabled()
        assert not move(window, "e7e5")
        reply(window, "e7e5")
        assert window.view.isEnabled()
    else:
        assert move(window, "e7e5")
        assert window.play_worker is None
    assert window.board.turn == chess.WHITE
    assert window.panel.scan_button.isEnabled() == (mode == GameMode.ANALYSIS)


def test_black_opens_automatically(window):
    window.start_game(GameOptions(GameMode.VS_COMPUTER, color="Black"))
    assert window.player_color == chess.BLACK and window.view.flipped
    assert window.play_worker.requests[0][0].turn == chess.WHITE
    assert not window.view.isEnabled()
    reply(window, "e2e4")
    assert window.view.isEnabled()
    assert "Black" in window.panel.playing_label.text()


@pytest.mark.parametrize("color", [chess.WHITE, chess.BLACK])
def test_random_color(window, monkeypatch, color):
    monkeypatch.setattr("app.chess.game_mode.random.choice", lambda choices: color)
    window.start_game(GameOptions(GameMode.VS_COMPUTER, color="Random"))
    assert window.player_color == color
    assert window.view.flipped == (color == chess.BLACK)
    assert bool(window._play_request) == (color == chess.BLACK)


@pytest.mark.parametrize("elapsed,expected", [(0,800), (0.12,680), (0.8,0), (1.2,0)])
def test_presentation_delay(elapsed, expected):
    assert abs(remaining_move_delay(0, elapsed) - expected) <= 1


def test_timer_result_does_not_commit_immediately(window, monkeypatch):
    monkeypatch.setattr("app.ui.main_window.thinking_delay_ms", lambda elo: 1000)
    window.start_game(GameOptions(GameMode.VS_COMPUTER, color="Black"))
    started = window._play_request[2]
    monkeypatch.setattr("app.ui.main_window.time.monotonic", lambda: started + 0.12)
    scheduled = []
    monkeypatch.setattr("app.ui.main_window.QTimer.singleShot", lambda delay, callback: scheduled.append((delay, callback)))
    window._computer_done(window.play_token, (chess.Move.from_uci("e2e4"), 1400))
    assert not window.board.move_stack
    assert 879 <= scheduled[0][0] <= 881
    scheduled[0][1]()
    assert window.board.peek().uci() == "e2e4"


@pytest.mark.parametrize("evaluation,suggestions", [(False,False),(True,False),(False,True),(True,True)])
def test_learning_tools_independent(window, evaluation, suggestions):
    window.start_game(GameOptions(GameMode.LOCAL_PVP, evaluation=evaluation, suggestions=suggestions))
    assert window.eval_bar.isHidden() == (not evaluation)
    assert window.needs_analysis == (evaluation or suggestions)
    window.analysis_done(window.analysis_token, [("e4", "e2e4", 45, None, 12)])
    assert bool(window.view.arrow) == suggestions
    assert (window.panel.best_button.text() == "e4") == suggestions
    assert window.board_host.board.x() >= 0


def test_analysis_preserves_saved_toggle_and_manual_history(window):
    window.suggestions_enabled = False
    window.start_game(GameOptions(GameMode.ANALYSIS, allow_history=False))
    assert not window.needs_analysis
    assert not window.eval_bar.isHidden()
    move(window, "e2e4")
    assert window.undo() and window.redo()


@pytest.mark.parametrize("mode", [GameMode.LOCAL_PVP, GameMode.VS_COMPUTER])
def test_history_disabled_all_entry_points(window, mode):
    window.start_game(GameOptions(mode, allow_history=False))
    move(window, "e2e4")
    before = window.board.fen()
    assert not window.undo() and not window.redo()
    window.activateWindow()
    window.panel.new_button.setFocus()
    QTest.keyClick(window.panel.new_button, Qt.Key_Left)
    QTest.keyClick(window.panel.new_button, Qt.Key_Z, Qt.ControlModifier)
    assert window.board.fen() == before


def test_pvp_one_ply(window):
    window.start_game(GameOptions(GameMode.LOCAL_PVP))
    move(window, "e2e4")
    first = window.board.fen()
    move(window, "e7e5")
    assert window.undo() and window.board.fen() == first
    assert window.redo() and len(window.board.move_stack) == 2


@pytest.mark.parametrize("color", ["White", "Black"])
def test_pvc_pair_exact_history_and_branch(window, color):
    window.start_game(GameOptions(GameMode.VS_COMPUTER, color=color))
    if color == "Black": reply(window, "e2e4")
    before = window.board.fen()
    move(window, "e2e4" if color == "White" else "e7e5")
    reply(window, "e7e5" if color == "White" else "g1f3")
    after = window.board.fen()
    requests = len(window.play_worker.requests)
    assert window.undo() and window.board.fen() == before
    assert window.redo() and window.board.fen() == after
    assert len(window.play_worker.requests) == requests
    assert window.undo()
    move(window, "d2d4" if color == "White" else "d7d5")
    assert not window.game.can_redo


def test_black_opening_undo_redo(window):
    window.start_game(GameOptions(GameMode.VS_COMPUTER, color="Black"))
    reply(window, "e2e4")
    assert window.undo() and window.board.fen() == chess.STARTING_FEN
    assert window._play_request is None
    assert window.redo() and window.board.peek().uci() == "e2e4"
    assert len(window.play_worker.requests) == 1


@pytest.mark.parametrize("action", ["new_game", "undo", "reset", "close"])
def test_stale_result_and_scheduled_move_rejected(window, action):
    window.start_game(GameOptions(GameMode.VS_COMPUTER))
    move(window, "e2e4")
    old = window.play_token
    if action == "new_game": window.start_game(GameOptions(GameMode.LOCAL_PVP))
    elif action == "undo": window.undo()
    elif action == "reset": window.load_position(chess.Board(), chess.WHITE, chess.WHITE)
    else: window.close()
    before = window.board.fen()
    window._computer_done(old, (chess.Move.from_uci("e7e5"), 1400))
    window._apply_computer_move(old, chess.Move.from_uci("e7e5"))
    assert window.board.fen() == before


def test_undo_during_thinking_redo_does_not_recompute(window):
    window.start_game(GameOptions(GameMode.VS_COMPUTER))
    move(window, "e2e4")
    assert window.undo() and window.board.fen() == chess.STARTING_FEN
    assert window.redo() and window.board.peek().uci() == "e2e4"
    assert window._play_request is None
    assert len(window.play_worker.requests) == 1


def test_game_over_stops_computer(window):
    window.start_game(GameOptions(GameMode.VS_COMPUTER))
    move(window, "f2f3")
    reply(window, "e7e5")
    move(window, "g2g4")
    reply(window, "d8h4")
    count = len(window.play_worker.requests)
    window._request_computer()
    assert window.board.is_checkmate()
    assert window.panel.state_label.text() == "Black wins"
    assert not window.view.isEnabled()
    assert len(window.play_worker.requests) == count


def test_native_strength_and_clamp():
    calls = []
    engine = SimpleNamespace(options={
        "UCI_LimitStrength": chess.engine.Option("UCI_LimitStrength", "check", False, None, None, []),
        "UCI_Elo": chess.engine.Option("UCI_Elo", "spin", 1320, 1320, 3190, []),
    }, configure=calls.append)
    assert configure_play_strength(engine, 1400) == 1400
    assert calls[-1] == {"UCI_LimitStrength": True, "UCI_Elo": 1400}
    assert configure_play_strength(engine, 800) == 800
    assert calls[-1] == {"UCI_LimitStrength": False, "UCI_Elo": 1320}
    with pytest.raises(ValueError, match="Adjustable Elo is unavailable"):
        configure_play_strength(SimpleNamespace(options={}), 1400)


def test_play_and_analysis_roles_are_separate(window):
    window.start_game(GameOptions(GameMode.VS_COMPUTER, color="Black", elo=1700, suggestions=True))
    assert window.play_worker is not window.engine_worker
    assert window.play_worker.play_elo == 1700
    assert window.engine_worker.play_elo is None
    reply(window, "e2e4")
    assert window.board_host.board._animated_move is not None


def test_real_worker_calls_play_with_history(monkeypatch):
    worker = EngineWorker("fake", play_elo=1700)
    board = chess.Board()
    board.push_uci("e2e4")
    worker.submit_play(board, 10)
    captured = []
    class Engine:
        options = {"UCI_LimitStrength": None, "UCI_Elo": SimpleNamespace(min=800,max=2800)}
        def configure(self, values): captured.append(values)
        def play(self, position, limit):
            captured.append(position.move_stack[:])
            worker.request_stop()
            return SimpleNamespace(move=chess.Move.from_uci("e7e5"))
        def quit(self): pass
    monkeypatch.setattr("app.engine.stockfish.os.path.isfile", lambda path: True)
    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", lambda *a, **k: Engine())
    results = []
    worker.result.connect(lambda token, result: results.append((token, result)))
    worker.run()
    assert captured == [{"UCI_LimitStrength":True,"UCI_Elo":1700}, [chess.Move.from_uci("e2e4")]]
    assert results == [(10,(chess.Move.from_uci("e7e5"),1700))]


def test_engine_failure_is_nonmodal_and_actionable(window):
    window.start_game(GameOptions(GameMode.VS_COMPUTER, color="Black"))
    window._computer_failed(-1, "Adjustable Elo unavailable; select Stockfish in Settings")
    assert "Settings" in window.panel.state_label.text()
    assert window._play_request is None
    assert window.panel.new_button.isEnabled()


def test_dialog_mode_visibility_and_elo(window, qtbot):
    dialog = NewGameDialog(window)
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.computer.isHidden() and dialog.tools.isHidden()
    for mode in (GameMode.LOCAL_PVP, GameMode.VS_COMPUTER):
        next(button for button in dialog.modes.buttons() if button.text() == mode.value).click()
        assert not dialog.tools.isHidden()
        assert dialog.computer.isHidden() == (mode == GameMode.LOCAL_PVP)
    dialog.elo.setValue(1700)
    assert dialog.category.text() == "Club"
    assert dialog.values() == replace(GameOptions(GameMode.VS_COMPUTER), elo=1700)
