"""Contained gameplay additions, with deterministic time and no network."""
from types import SimpleNamespace
import chess
import chess.engine
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from app.chess.game_clock import GameClock, timeout_result
from app.chess.game_mode import GameMode, GameOptions, thinking_delay_ms, remaining_move_delay
from app.chess.game_state import ManualGameState
from app.engine.stockfish import EngineWorker, choose_beginner_move
from app.ui.board_widget import ChessBoardWidget
from app.ui.new_game_dialog import NewGameDialog
from test_game_modes import window, move, reply


@pytest.mark.parametrize("minutes", [1,5,10,20])
def test_initial_clocks(minutes):
    clock = GameClock(minutes, now=lambda: 0)
    assert clock.remaining_ms == {True:minutes*60000,False:minutes*60000}


def test_monotonic_switch_and_pause():
    now = [0.0]
    clock = GameClock(1, now=lambda: now[0])
    clock.switch(chess.WHITE)
    now[0] = 2.125
    clock.settle()
    assert clock.remaining_ms == {True:57875, False:60000}
    clock.switch(chess.BLACK)
    now[0] = 5
    clock.pause()
    assert clock.remaining_ms == {True:57875, False:57125}
    now[0] = 100
    clock.settle()
    assert clock.remaining_ms[False] == 57125


def mock_clock(window):
    now = [0.0]
    window.clock.now = lambda: now[0]
    window.clock.anchor = 0
    window.clock.remaining_ms = {True: window.game_options.minutes * 60000.0, False: window.game_options.minutes * 60000.0}
    return now


def test_moves_switch_clocks_and_pvc_delay_counts(window):
    window.start_game(GameOptions(GameMode.VS_COMPUTER))
    now = mock_clock(window)
    now[0] = 2
    move(window, "e2e4")
    assert window.clock.active == chess.BLACK
    now[0] = 3.5
    reply(window, "e7e5")
    assert window.clock.remaining_ms == {True:598000,False:598500}
    assert window.clock.active == chess.WHITE
    assert "thinking" not in window.panel.state_label.text()


@pytest.mark.parametrize("color", [chess.WHITE,chess.BLACK])
def test_timeout_stops_engine_and_rejects_late_move(window, color):
    window.start_game(GameOptions(GameMode.VS_COMPUTER, color="White" if color else "Black", minutes=1))
    now = mock_clock(window)
    old = window.play_token
    now[0] = 61
    window._clock_tick()
    assert window._timeout == "Black wins on time"
    assert window.clock.active is None
    assert not window.view.isEnabled()
    before = window.board.fen()
    window._apply_computer_move(old, chess.Move.from_uci("e2e4"))
    assert not move(window, "e2e4")
    assert window.board.fen() == before


def test_timeout_draw_insufficient_opponent_material():
    board = chess.Board("7k/8/8/8/8/8/P7/K7 w - - 0 1")
    assert timeout_result(board, chess.WHITE) == "Draw"
    assert timeout_result(board, chess.BLACK) == "White wins on time"


def test_new_game_cancels_old_clock_and_analysis_has_none(window):
    window.start_game(GameOptions(GameMode.LOCAL_PVP, minutes=1))
    old = window.clock
    window.start_game(GameOptions(GameMode.LOCAL_PVP, minutes=20))
    assert old.active is None and window.clock is not old
    assert window.clock.remaining_ms[False] == 1200000
    window.start_game(GameOptions())
    assert window.clock is None and not window._clock_timer.isActive()
    assert not window.top_player.isHidden() and not window.bottom_player.isHidden()
    assert window.top_player.remaining_ms is None and window.bottom_player.remaining_ms is None


def test_new_dialog_pauses_then_cancel_resumes(window, monkeypatch):
    window.start_game(GameOptions(GameMode.LOCAL_PVP))
    now = mock_clock(window)
    def cancel(dialog):
        assert window.clock.active is None
        now[0] = 200
        window._clock_tick()
        return 0
    monkeypatch.setattr(NewGameDialog, "exec", cancel)
    window.new_game()
    assert window.clock.remaining_ms[True] == 600000
    assert window.clock.active == chess.WHITE


def test_checkmate_pauses_clock(window):
    window.start_game(GameOptions(GameMode.LOCAL_PVP))
    for uci in ("f2f3","e7e5","g2g4","d8h4"):
        move(window, uci)
    assert window.clock.active is None


def test_undo_retains_spent_time(window):
    window.start_game(GameOptions(GameMode.LOCAL_PVP))
    now = mock_clock(window)
    now[0] = 4
    move(window,"e2e4")
    now[0] = 6
    window.undo()
    assert window.clock.remaining_ms == {True:596000,False:598000}
    assert window.clock.active == chess.WHITE
    window.redo()
    assert window.clock.remaining_ms == {True:596000,False:598000}
    assert window.clock.active == chess.BLACK


@pytest.mark.parametrize("color", [True,False])
def test_names_and_random_orientation(window, monkeypatch, color):
    monkeypatch.setattr("app.chess.game_mode.random.choice", lambda choices: color)
    window.start_game(GameOptions(GameMode.VS_COMPUTER, color="Random", human_name="Alex"))
    assert window.bottom_player.name == "Alex" and window.top_player.name == "ChessAI"
    window.flip_board()
    assert window.top_player.name == "Alex" and window.bottom_player.name == "ChessAI"


def test_pvp_names_defaults_and_captures(window):
    window.start_game(GameOptions(GameMode.LOCAL_PVP, white_name="A",black_name="B"))
    assert window.bottom_player.name == "A" and window.top_player.name == "B"
    for uci in ("e2e4","d7d5","e4d5"):
        move(window,uci)
    assert window.bottom_player.captures == (chess.Piece(chess.PAWN,False),)
    window.undo()
    assert not window.bottom_player.captures
    window.redo()
    assert len(window.bottom_player.captures) == 1
    window.start_game(GameOptions(GameMode.LOCAL_PVP))
    assert window.bottom_player.name == "White" and window.top_player.name == "Black"


@pytest.mark.parametrize("fen,uci,captured", [
    ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2","e5d6",chess.PAWN),
    ("1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1","a7b8q",chess.ROOK),
])
def test_special_capture_history(fen,uci,captured):
    state = ManualGameState(chess.Board(fen))
    m = chess.Move.from_uci(uci)
    state.make_move(m.from_square,m.to_square,m.promotion)
    assert state.captures_by(True) == (chess.Piece(captured,False),)
    state.undo()
    assert not state.captures_by(True)
    state.redo()
    assert state.captures_by(True) == (chess.Piece(captured,False),)


@pytest.mark.parametrize("fen,uci,movers", [
    (chess.STARTING_FEN,"e2e4",1),
    ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1","e1g1",2),
    ("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1","e8c8",2),
    ("1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1","a7b8q",1),
    ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2","e5d6",1),
])
def test_animation_canonical_completion(qtbot,fen,uci,movers):
    view = ChessBoardWidget()
    qtbot.addWidget(view)
    view.resize(500,500)
    view.show()
    before = chess.Board(fen)
    after = before.copy()
    m = chess.Move.from_uci(uci)
    after.push(m)
    with qtbot.waitSignal(view.animation_completed, timeout=1000):
        view.animate_move(before,m,after)
        assert view._animation.duration() == 210
        assert len(view._moving_pieces) == movers
        assert view._animation_before.fen() == before.fen()
        # Drawing suppresses each source exactly once; all movers have distinct endpoints.
        assert len({source for source,_,_ in view._moving_pieces}) == movers
        assert view.board.fen() == after.fen()
    assert view._animated_move is None and not view._moving_pieces
    assert view._animation_before is None
    assert view.board.fen() == after.fen()


def test_resize_finishes_animation(qtbot):
    view = ChessBoardWidget()
    qtbot.addWidget(view)
    view.show()
    before=chess.Board(); after=before.copy(); m=chess.Move.from_uci("e2e4"); after.push(m)
    view.animate_move(before,m,after)
    view.resize(450,450)
    assert view._animated_move is None
    assert view.board.piece_at(chess.E4) == chess.Piece(chess.PAWN,True)


@pytest.mark.parametrize("elo,low,high", [(600,1200,1600),(900,1200,1600),(1100,1000,1400),(1400,900,1200),(2200,750,1000)])
def test_natural_delay_ranges(elo,low,high):
    assert all(low <= thinking_delay_ms(elo) <= high for _ in range(10))
    assert remaining_move_delay(0,1.5,1200) == 0
    assert remaining_move_delay(0,.4,1200) == 800


def test_low_strength_bounded_candidates(monkeypatch):
    board=chess.Board()
    infos=[{'pv':[chess.Move.from_uci(uci)],'score':chess.engine.PovScore(chess.engine.Cp(score),True)}
           for uci,score in [('e2e4',30),('d2d4',20),('a2a3',-300),('b2b3',-1000)]]
    observed=[]
    def choose(moves,weights,k):
        observed.append((moves,weights)); return [moves[-1]]
    monkeypatch.setattr('app.engine.stockfish.random.choices',choose)
    assert choose_beginner_move(board,infos,600).uci() == 'a2a3'
    assert choose_beginner_move(board,infos,1300).uci() == 'd2d4'
    assert observed[0][1][0] > observed[0][1][-1]


def test_low_worker_uses_evaluations_not_native_play(monkeypatch):
    worker=EngineWorker('fake',play_elo=600)
    worker.submit_play(chess.Board(),1)
    calls=[]
    class Engine:
        options={'UCI_LimitStrength':None,'UCI_Elo':SimpleNamespace(min=1320,max=3190)}
        def configure(self,values): calls.append(values)
        def analyse(self,board,limit,multipv):
            calls.append(multipv); worker.request_stop()
            return [{'pv':[chess.Move.from_uci('e2e4')],'score':chess.engine.PovScore(chess.engine.Cp(20),True)}]
        def play(self,*args): raise AssertionError('Native play used below minimum')
        def quit(self): pass
    monkeypatch.setattr('app.engine.stockfish.os.path.isfile',lambda path:True)
    monkeypatch.setattr(chess.engine.SimpleEngine,'popen_uci',lambda *a,**k:Engine())
    worker.run()
    assert calls == [{'UCI_LimitStrength':False,'UCI_Elo':1320},12]


def test_new_dialog_fields(window,qtbot):
    d=NewGameDialog(window,GameOptions(GameMode.VS_COMPUTER,elo=600))
    qtbot.addWidget(d); d.show()
    assert d.elo.minimum() == 600 and d.elo.maximum() == 2800
    assert [b.text() for b in d.times.buttons()] == ['1 min','5 min','10 min','20 min']
    d.human_name.setText('Alex')
    assert d.values().human_name == 'Alex'
    next(b for b in d.modes.buttons() if b.text()=='Analysis').click()
    assert d.time_controls.isHidden() and d.names.isHidden()


def test_analysis_captures_without_clocks(window):
    window.start_game(GameOptions())
    for uci in ('e2e4','d7d5','e4d5'):
        move(window,uci)
    assert window.bottom_player.captures == (chess.Piece(chess.PAWN,False),)
    assert window.clock is None and window.bottom_player.remaining_ms is None
    window.undo()
    assert not window.bottom_player.captures
    window.redo()
    assert len(window.bottom_player.captures) == 1
    window.flip_board()
    assert len(window.top_player.captures) == 1


def test_brand_link_keeps_label_and_opens_site(window,monkeypatch):
    from app.ui.main_window import BrandingLabel, QDesktopServices
    opened=[]
    monkeypatch.setattr(QDesktopServices,'openUrl',lambda url: opened.append(url.toString()))
    label=window.findChild(BrandingLabel)
    assert label.text() == 'Built by 47 Lab'
    assert 'font-size: 10px' in label.styleSheet()
    size=label.size()
    QTest.mouseClick(label,Qt.LeftButton)
    assert opened == ['https://fortysevenlab.com']
    assert label.size() == size
