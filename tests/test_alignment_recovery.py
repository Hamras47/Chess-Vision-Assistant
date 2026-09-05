import os,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import chess,numpy as np
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from app.main import MainWindow
from app.chess.coordinates import Orientation
from app.chess.session import RECOVERING,SYNCED
from app.vision.alignment import geometry_changed,plausible_board_crop,search_region
from app.vision.change_detector import frame_signature

def window(monkeypatch):
    QApplication.instance() or QApplication([])
    w=MainWindow(); monkeypatch.setattr(w,'start_tracking',lambda:None); monkeypatch.setattr(w,'analyze',lambda:None)
    w.session.browser_orientation=Orientation.WHITE_BOTTOM
    return w

def test_massive_change_reanchors_without_move_inference(monkeypatch):
    w=window(monkeypatch); baseline=np.zeros((800,800,3),np.uint8); current=np.full_like(baseline,255); w.previous=baseline; w.session.last_accepted_signature=frame_signature(baseline); before=w.board.fen()
    signals={square:{'combined':.2} for square in list(chess.SQUARES)[:50]}
    monkeypatch.setattr('app.main.score_squares',lambda *_:signals)
    monkeypatch.setattr('app.main.infer_move',lambda *_:(_ for _ in ()).throw(AssertionError('legal inference must not run')))
    corrected=np.full_like(baseline,60)
    def reanchor(reason):
        w.set_board_geometry({'left':15,'top':10,'width':720,'height':720},corrected,reason); return corrected
    monkeypatch.setattr(w,'reanchor_board',reanchor)
    w.tracking_frame(w.tracking_session_id,current)
    assert w.board.fen()==before and w.session.tracking_state==SYNCED and w.region['width']==720 and w.previous.mean()==60
    w.close()

def test_resize_and_move_are_geometry_changes_not_chess_moves(monkeypatch):
    w=window(monkeypatch); w.region={'left':100,'top':100,'width':800,'height':800}; crop=np.zeros((720,720,3),np.uint8); before=w.board.fen()
    w.set_board_geometry({'left':115,'top':110,'width':720,'height':720},crop,'test resize')
    assert w.board.fen()==before and w.board_anchor==(115,110) and w.square_size==90 and w.previous.shape==(720,720,3)
    assert geometry_changed({'left':100,'top':100,'width':800,'height':800},w.region)
    w.close()

def test_recovery_waits_twenty_seconds_not_eight(monkeypatch):
    w=window(monkeypatch); w.region={'left':0,'top':0,'width':64,'height':64}; w.tracker=SimpleNamespace(isRunning=lambda:True,stop=lambda:None)
    w.recovery=True; w.recovery_in_progress=True; w.recovery_request_id=4; w.recovery_started=time.monotonic()-13.3; w.set_sync_state(RECOVERING,'test')
    failed=[]; monkeypatch.setattr(w,'ai_failed',lambda *args:failed.append(args))
    w.check_watchdog()
    assert not failed and w.session.tracking_state==RECOVERING
    w.close()

def test_canonical_piece_color_survives_legal_move(monkeypatch):
    w=window(monkeypatch); w.select_player(chess.WHITE); w.board=chess.Board('4k3/3N4/8/8/8/8/8/4K3 w - - 0 1'); w.view.set_board(w.board); frame=np.zeros((128,128,3),np.uint8)
    move=chess.Move.from_uci('d7f8'); assert w.accept_sequence((move,),frame,frame_signature(frame),'test',1.0)
    assert w.board.piece_at(chess.F8)==chess.Piece(chess.KNIGHT,chess.WHITE) and w.view.piece_map()==w.board.piece_map()
    w.close()

def test_alignment_helpers_bound_search_and_require_square_crop():
    assert plausible_board_crop(np.zeros((800,800,3),np.uint8))[0]
    assert not plausible_board_crop(np.zeros((800,780,3),np.uint8))[0]
    assert search_region({'left':15,'top':10,'width':800,'height':800})['left']==0
