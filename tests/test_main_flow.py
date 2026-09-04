import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import chess
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from app.main import MainWindow
from app.chess.coordinates import Orientation

def test_successful_ai_scan_starts_tracking(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); calls=[]
 monkeypatch.setattr(w,'start_tracking',lambda:calls.append('tracking')); monkeypatch.setattr(w,'analyze',lambda:calls.append('analysis'))
 result=SimpleNamespace(side_to_move='white',orientation='white_bottom',confidence=.98,warnings=[])
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result,.1,object())
 assert calls==['tracking','analysis']; assert w.scan_button.text()=='RESCAN'; w.close()
def test_widget_reads_canonical_board_reference():
 app=QApplication.instance() or QApplication([]); w=MainWindow(); assert w.view.board is w.board
 w.board.push_uci('e2e4'); w.view.update(); assert w.view.piece_map()==w.board.piece_map(); w.close()
def test_stale_analysis_is_discarded():
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.board_version=4; before=w.best.text(); w.analysis_done(3,[('e4','e2e4',20,None,12)]); assert w.best.text()==before; w.close()
def test_rescan_invalidates_tracking_session(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); old=w.tracking_session_id; monkeypatch.setattr(w,'hide',lambda:None); monkeypatch.setattr('app.main.QTimer.singleShot',lambda *args:None); w.scan_board(); assert w.tracking_session_id==old+1; w.close()
def test_ai_recovery_atomically_replaces_canonical_board(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); monkeypatch.setattr(w,'start_tracking',lambda:None); monkeypatch.setattr(w,'analyze',lambda:None); replacement=chess.Board(); replacement.push_uci('e2e4'); version=w.board_version; result=SimpleNamespace(side_to_move='black',orientation='white_bottom',confidence=.9,warnings=[]); w.ai_done(w.tracking_session_id,version,True,replacement,result,.1,object()); assert w.board_version==version+1 and w.board is replacement and w.view.board is replacement; w.close()
def test_rescan_sets_black_user_and_recovery_preserves_orientation(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); monkeypatch.setattr(w,'start_tracking',lambda:None); monkeypatch.setattr(w,'analyze',lambda:None)
 white=SimpleNamespace(side_to_move='white',orientation='white_bottom',confidence=.9,warnings=[])
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),white,.1,object())
 assert w.orientation is Orientation.WHITE_BOTTOM and w.user_color==chess.WHITE
 w.tracking_session_id+=1; w.board_version+=1
 result=SimpleNamespace(side_to_move='black',orientation='black_bottom',confidence=.9,warnings=[])
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result,.1,object())
 assert w.orientation is Orientation.BLACK_BOTTOM and w.user_color==chess.BLACK and w.playing.text()=='Playing: Black'
 recovery=SimpleNamespace(side_to_move='black',orientation='white_bottom',confidence=.9,warnings=[])
 w.ai_done(w.tracking_session_id,w.board_version,True,chess.Board(),recovery,.1,object())
 assert w.orientation is Orientation.BLACK_BOTTOM and w.view.orientation is Orientation.BLACK_BOTTOM
 w.close()
def test_unknown_ai_orientation_uses_explicit_user_choice(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); monkeypatch.setattr(w,'start_tracking',lambda:None); monkeypatch.setattr(w,'analyze',lambda:None); monkeypatch.setattr(w,'ask_orientation',lambda:Orientation.BLACK_BOTTOM)
 result=SimpleNamespace(side_to_move='black',orientation='unknown',confidence=.5,warnings=[])
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result,.1,object())
 assert w.orientation is Orientation.BLACK_BOTTOM and w.user_color==chess.BLACK
 w.close()
def test_black_bottom_arrow_endpoints_use_flipped_visual_cells():
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.view.resize(420,420); w.view.set_orientation(Orientation.BLACK_BOTTOM); w.view.arrow=(chess.G8,chess.F6)
 start=w.view._rect_for(chess.G8).center(); end=w.view._rect_for(chess.F6).center()
 assert (start.x(),start.y())==(78.75,393.75)
 assert (end.x(),end.y())==(131.25,288.75)
 w.close()
def test_engine_recommendation_is_suppressed_on_opponent_turn():
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.user_color=chess.BLACK; w.board=chess.Board(); w.view.arrow=(chess.E2,chess.E4)
 w.analyze()
 assert w.best.text()=='BEST MOVE\nWaiting' and w.view.arrow is None and w.status.text()=='Waiting for opponent'
 w.close()
def test_svg_assets_cover_every_piece():
 for color in ('white','black'):
  for name in ('pawn','knight','bishop','rook','queen','king'):assert Path(f'assets/pieces/{color}_{name}.svg').exists()
