import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import chess
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from app.main import MainWindow

def test_successful_ai_scan_starts_tracking(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); calls=[]
 monkeypatch.setattr(w,'start_tracking',lambda:calls.append('tracking')); monkeypatch.setattr(w,'analyze',lambda:calls.append('analysis'))
 result=SimpleNamespace(side_to_move='white',orientation='white_bottom',confidence=.98,warnings=[])
 w.ai_done(w.tracking_session_id,w.board_version,chess.Board(),result,.1,object())
 assert calls==['tracking','analysis']; assert w.scan_button.text()=='RESCAN'; w.close()
def test_widget_reads_canonical_board_reference():
 app=QApplication.instance() or QApplication([]); w=MainWindow(); assert w.view.board is w.board
 w.board.push_uci('e2e4'); w.view.update(); assert w.view.piece_map()==w.board.piece_map(); w.close()
def test_stale_analysis_is_discarded():
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.board_version=4; before=w.best.text(); w.analysis_done(3,[('e4','e2e4',20,None,12)]); assert w.best.text()==before; w.close()
def test_rescan_invalidates_tracking_session(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); old=w.tracking_session_id; monkeypatch.setattr(w,'hide',lambda:None); monkeypatch.setattr('app.main.QTimer.singleShot',lambda *args:None); w.scan_board(); assert w.tracking_session_id==old+1; w.close()
def test_ai_recovery_atomically_replaces_canonical_board(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); monkeypatch.setattr(w,'start_tracking',lambda:None); monkeypatch.setattr(w,'analyze',lambda:None); replacement=chess.Board(); replacement.push_uci('e2e4'); version=w.board_version; result=SimpleNamespace(side_to_move='black',orientation='white_bottom',confidence=.9,warnings=[]); w.ai_done(w.tracking_session_id,version,replacement,result,.1,object()); assert w.board_version==version+1 and w.board is replacement and w.view.board is replacement; w.close()
def test_svg_assets_cover_every_piece():
 for color in ('white','black'):
  for name in ('pawn','knight','bishop','rook','queen','king'):assert Path(f'assets/pieces/{color}_{name}.svg').exists()
