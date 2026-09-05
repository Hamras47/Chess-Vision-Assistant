import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import chess,numpy as np
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from app.main import MainWindow
from app.chess.coordinates import Orientation
from app.chess.session import SYNCED,VERIFYING
from app.chess.move_tracker import transition_squares
from app.vision.change_detector import frame_signature

FRAME=np.zeros((64,64,3),dtype=np.uint8)
def result(): return SimpleNamespace(side_to_move='unknown',orientation='white_bottom',confidence=.98,warnings=[])
def window(monkeypatch):
    QApplication.instance() or QApplication([]); w=MainWindow(); monkeypatch.setattr(w,'start_tracking',lambda:None); monkeypatch.setattr(w,'analyze',lambda:None); return w

def test_initial_flow_uses_player_and_my_turn_prompts(monkeypatch):
    w=window(monkeypatch); monkeypatch.setattr(w,'ask_player_color',lambda:chess.BLACK); monkeypatch.setattr(w,'ask_my_turn',lambda:chess.BLACK)
    w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result(),.1,FRAME)
    assert w.player_color==chess.BLACK and w.board.turn==chess.BLACK and w.view.orientation is Orientation.BLACK_BOTTOM and w.session.tracking_state==SYNCED
    w.close()

def test_openai_zero_one_and_two_ply_recovery(monkeypatch):
    for moves in ((),('e2e4',),('e2e4','e7e5')):
        w=window(monkeypatch); w.select_player(chess.WHITE); w.session.browser_orientation=Orientation.WHITE_BOTTOM; recovered=w.board.copy()
        for move in moves: recovered.push_uci(move)
        w.ai_done(w.tracking_session_id,w.board_version,True,recovered,result(),.1,FRAME)
        assert w.session.tracking_state==SYNCED
        w.close()

def test_atomic_two_ply_commit_and_baseline(monkeypatch):
    w=window(monkeypatch); w.select_player(chess.WHITE); w.session.browser_orientation=Orientation.WHITE_BOTTOM
    visible=w.board.copy(); visible.push_uci('e2e4'); visible.push_uci('e7e5'); observed=transition_squares(w.board,visible); scores={s:(.1 if s in observed else 0.) for s in chess.SQUARES}
    w.try_local_recovery(np.full_like(FRAME,255),frame_signature(FRAME),observed,scores,.065)
    assert [m.uci() for m in w.board.move_stack]==['e2e4','e7e5'] and w.session.tracking_state==SYNCED and w.previous.mean()==255
    w.close()

def test_stale_stockfish_result_is_discarded(monkeypatch):
    w=window(monkeypatch); w.select_player(chess.WHITE); before=w.best.text(); w.analysis_done(w.tracking_session_id+1,w.board_version,[('e4','e2e4',20,None,12)])
    assert w.best.text()==before; w.close()

def test_visual_change_enters_verifying_without_network(monkeypatch):
    w=window(monkeypatch); w.session.browser_orientation=Orientation.WHITE_BOTTOM; w.previous=FRAME.copy(); w.session.last_accepted_signature=frame_signature(FRAME); w.stabilizer.observe=lambda *_:False
    monkeypatch.setattr('app.main.score_squares',lambda *_:{chess.E2:{'combined':.2}})
    w.tracking_frame(w.tracking_session_id,np.full_like(FRAME,255))
    assert w.session.tracking_state==VERIFYING
    w.close()

def test_watchdog_escalates_only_after_visual_verification(monkeypatch):
    w=window(monkeypatch); w.region={'left':0,'top':0,'width':64,'height':64}; w.tracker=SimpleNamespace(isRunning=lambda:True,stop=lambda:None); w.session.tracking_state=VERIFYING; w.verifying_started=0
    calls=[]; monkeypatch.setattr(w,'recover',lambda frame:calls.append(frame)); w.check_watchdog(); assert not calls
    w.verifying_started=-2; w.check_watchdog(); assert calls
    w.close()
