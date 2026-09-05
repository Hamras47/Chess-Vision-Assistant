import os,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import chess,numpy as np
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from app.main import MainWindow
from app.chess.coordinates import Orientation
from app.chess.move_tracker import expected_changed_squares,infer_move
from app.chess.session import RECOVERING,SYNCED,VERIFYING
from app.vision.change_detector import frame_signature
from app.vision.grid import locked_square_crop

def window(monkeypatch):
    QApplication.instance() or QApplication([])
    w=MainWindow(); monkeypatch.setattr(w,'start_tracking',lambda:None); monkeypatch.setattr(w,'analyze',lambda:None)
    w.session.browser_orientation=Orientation.WHITE_BOTTOM
    return w

def test_initial_square_crop_never_expands_selection():
    image=np.zeros((831,820,3),np.uint8); crop,(x,y,width,height)=locked_square_crop(image)
    assert crop.shape[:2]==(820,820) and (x,y,width,height)==(0,5,820,820)

def test_fifty_changed_squares_keeps_locked_rect_and_retries(monkeypatch):
    w=window(monkeypatch); baseline=np.zeros((128,128,3),np.uint8); current=np.full_like(baseline,255); w.previous=baseline; w.region={'left':100,'top':200,'width':128,'height':128}; locked=w.region.copy(); w.session.last_accepted_signature=frame_signature(baseline)
    signals={square:{'combined':.2} for square in list(chess.SQUARES)[:50]}; calls=[]
    monkeypatch.setattr('app.main.score_squares',lambda *_:signals)
    monkeypatch.setattr('app.main.infer_move',lambda *_:(_ for _ in ()).throw(AssertionError('must not score a 50-square change')))
    monkeypatch.setattr(w,'recover',lambda crop:calls.append(crop))
    w.tracking_frame(w.tracking_session_id,current)
    assert w.region==locked and w.session.tracking_state==VERIFYING and not calls
    w.tracking_frame(w.tracking_session_id,current)
    assert w.region==locked and len(calls)==1 and w.board==chess.Board()
    w.close()

def test_noisy_stockfish_prior_selects_e7f7():
    board=chess.Board('k7/4R3/8/8/8/8/8/7K w - - 0 1'); move=chess.Move.from_uci('e7f7')
    observed={chess.parse_square(name) for name in ('e2','e3','e4','e5','e7','f7','e8','f8')}
    selected,score,_=infer_move(board,observed,prior_uci='e7f7')
    assert selected==move and score>=.9

def test_twenty_noisy_plies_keep_locked_geometry(monkeypatch):
    w=window(monkeypatch); w.select_player(chess.WHITE); w.region={'left':10,'top':20,'width':128,'height':128}; locked=w.region.copy(); frame=np.zeros((128,128,3),np.uint8)
    moves=['e2e4','e7e5','g1f3','b8c6','f1b5','a7a6','b5a4','g8f6','e1g1','f8e7','f1e1','b7b5','a4b3','d7d6','c2c3','e8g8','h2h3','c6b8','d2d4','b8d7']
    for uci in moves:
        move=chess.Move.from_uci(uci); observed=expected_changed_squares(w.board,move)|{chess.E2,chess.E3,chess.E4,chess.E5}
        selected,_,_=infer_move(w.board,observed,prior_uci=uci)
        assert selected==move and w.accept_sequence((selected,),frame,frame_signature(frame),'test',1.0) and w.region==locked and w.session.tracking_state==SYNCED
    assert len(w.board.move_stack)==20
    w.close()

def test_recovery_waits_twenty_seconds_not_eight(monkeypatch):
    w=window(monkeypatch); w.region={'left':0,'top':0,'width':64,'height':64}; w.tracker=SimpleNamespace(isRunning=lambda:True,stop=lambda:None)
    w.recovery=True; w.recovery_in_progress=True; w.recovery_request_id=4; w.recovery_started=time.monotonic()-13.3; w.set_sync_state(RECOVERING,'test')
    failed=[]; monkeypatch.setattr(w,'ai_failed',lambda *args:failed.append(args)); w.check_watchdog()
    assert not failed and w.session.tracking_state==RECOVERING
    w.close()
