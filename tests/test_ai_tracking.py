import os,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import chess,numpy as np
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from app.main import MainWindow
from app.chess.coordinates import Orientation
from app.chess.move_tracker import reconcile_reconstruction
from app.chess.session import RECOVERING,SYNCED,VERIFYING
from app.vision.change_detector import frame_signature,signature_difference

FRAME=np.zeros((128,128,3),np.uint8)
def result(confidence=.99): return SimpleNamespace(side_to_move='unknown',orientation='white_bottom',confidence=confidence,warnings=[])
def window(monkeypatch):
    QApplication.instance() or QApplication([]); w=MainWindow(); monkeypatch.setattr(w,'start_tracking',lambda:None); monkeypatch.setattr(w,'analyze',lambda:None); w.region={'left':10,'top':20,'width':128,'height':128}; w.session.browser_orientation=Orientation.WHITE_BOTTOM; w.previous=FRAME.copy(); w.session.last_accepted_signature=frame_signature(FRAME); return w

def test_change_trigger_is_whole_image_only():
    assert signature_difference(frame_signature(FRAME),frame_signature(FRAME.copy()))==0
    changed=np.full_like(FRAME,255)
    assert signature_difference(frame_signature(FRAME),frame_signature(changed))>.9

def test_runtime_does_not_import_local_chess_vision():
    source=(Path(__file__).parents[1]/'app'/'main.py').read_text(encoding='utf-8')
    for forbidden in ('score_squares','infer_move','infer_legal_sequence','visual_plausibility','changed_squares'):
        assert forbidden not in source

def test_change_settles_then_starts_one_ai_scan(monkeypatch):
    w=window(monkeypatch); calls=[]; monkeypatch.setattr(w,'recover',lambda image:calls.append(image.copy()))
    changed=np.full_like(FRAME,255); w.tracking_frame(w.tracking_session_id,changed); assert w.session.tracking_state==VERIFYING and not calls
    w.tracking_frame(w.tracking_session_id,changed); assert len(calls)==1
    w.close()

def test_exact_zero_one_and_two_ply_ai_reconciliation():
    board=chess.Board()
    for moves in ((),('e2e4',),('e2e4','e7e5')):
        observed=board.copy()
        for move in moves: observed.push_uci(move)
        recovered,sequence=reconcile_reconstruction(board,observed)
        assert recovered is not None and len(sequence)==len(moves)

def test_ai_full_resync_preserves_player_orientation(monkeypatch):
    w=window(monkeypatch); w.select_player(chess.BLACK); replacement=chess.Board(); replacement.remove_piece_at(chess.A2); w.recovery=True; w.recovery_in_progress=True; w.recovery_request_id=1; monkeypatch.setattr(w,'ask_my_turn',lambda:chess.WHITE)
    w.ai_done(w.tracking_session_id,w.board_version,True,replacement,result(),.1,FRAME,1)
    assert w.player_color==chess.BLACK and w.view.orientation is Orientation.BLACK_BOTTOM and w.board.piece_at(chess.A2) is None and w.session.tracking_state==SYNCED
    w.close()

def test_stale_ai_response_is_discarded(monkeypatch):
    w=window(monkeypatch); w.recovery=True; w.recovery_in_progress=True; w.recovery_request_id=2; before=w.board.fen()
    w.ai_done(w.tracking_session_id,w.board_version,True,chess.Board(),result(),.1,FRAME,1)
    assert w.board.fen()==before
    w.close()

def test_request_coalesces_visual_changes(monkeypatch):
    w=window(monkeypatch); w.recovery_in_progress=True; w.session.tracking_state=RECOVERING
    w.tracking_frame(w.tracking_session_id,np.full_like(FRAME,255))
    assert w.rescan_pending
    w.close()

def test_debounce_ignores_immediate_follow_up(monkeypatch):
    w=window(monkeypatch); w.debounce_until=time.monotonic()+1; calls=[]; monkeypatch.setattr(w,'recover',lambda image:calls.append(image))
    w.tracking_frame(w.tracking_session_id,np.full_like(FRAME,255)); assert not calls
    w.close()

def test_twenty_ai_observed_plies_commit_canonical_state(monkeypatch):
    w=window(monkeypatch); w.select_player(chess.WHITE)
    moves=['e2e4','e7e5','g1f3','b8c6','f1b5','a7a6','b5a4','g8f6','e1g1','f8e7','f1e1','b7b5','a4b3','d7d6','c2c3','e8g8','h2h3','c6b8','d2d4','b8d7']
    for index,uci in enumerate(moves,1):
        observed=w.board.copy(); observed.push_uci(uci); w.recovery=True; w.recovery_in_progress=True; w.recovery_request_id=index
        w.ai_done(w.tracking_session_id,w.board_version,True,observed,result(),.01,FRAME,index)
        assert w.session.tracking_state==SYNCED and len(w.board.move_stack)==index
    w.close()
