import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import chess,pytest,numpy as np
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from app.main import MainWindow
from app.chess.coordinates import Orientation

def result(side='white',orientation='white_bottom'):
 return SimpleNamespace(side_to_move=side,orientation=orientation,confidence=.98,warnings=[])

def quiet_window(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); monkeypatch.setattr(w,'start_tracking',lambda:None); monkeypatch.setattr(w,'analyze',lambda:None); return w

def test_successful_scan_explicitly_selects_player_and_starts_tracking(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); calls=[]
 monkeypatch.setattr(w,'ask_player_color',lambda:chess.BLACK); monkeypatch.setattr(w,'start_tracking',lambda:calls.append('tracking')); monkeypatch.setattr(w,'analyze',lambda:calls.append('analysis'))
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result(),.1,object())
 assert calls==['tracking','analysis'] and w.player_color==chess.BLACK
 assert w.session.app_display_orientation is Orientation.BLACK_BOTTOM and w.playing.text()=='Playing: Black' and w.scan_button.text()=='RESCAN'; w.close()

def test_player_choice_and_browser_orientation_are_independent(monkeypatch):
 w=quiet_window(monkeypatch); monkeypatch.setattr(w,'ask_player_color',lambda:chess.WHITE)
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result(orientation='black_bottom'),.1,object())
 assert w.session.browser_orientation is Orientation.BLACK_BOTTOM
 assert w.session.app_display_orientation is Orientation.WHITE_BOTTOM and w.view.orientation is Orientation.WHITE_BOTTOM
 w.close()

def test_unknown_browser_orientation_has_separate_explicit_choice(monkeypatch):
 w=quiet_window(monkeypatch); calls=[]; monkeypatch.setattr(w,'ask_player_color',lambda:chess.BLACK); monkeypatch.setattr(w,'ask_browser_orientation',lambda:calls.append('browser') or Orientation.WHITE_BOTTOM)
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result(orientation='unknown'),.1,object())
 assert calls==['browser'] and w.session.browser_orientation is Orientation.WHITE_BOTTOM and w.session.app_display_orientation is Orientation.BLACK_BOTTOM
 w.close()

def test_starting_position_is_white_to_move_without_turn_dialog(monkeypatch):
 w=quiet_window(monkeypatch); monkeypatch.setattr(w,'ask_player_color',lambda:chess.BLACK); monkeypatch.setattr(w,'ask_side_to_move',lambda:pytest.fail('turn dialog must not open for starting position'))
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result(side='unknown'),.1,object())
 assert w.board.turn==chess.WHITE; w.close()

def test_unknown_midgame_turn_is_asked_exactly_once(monkeypatch):
 w=quiet_window(monkeypatch); calls=[]; monkeypatch.setattr(w,'ask_player_color',lambda:chess.WHITE); monkeypatch.setattr(w,'ask_side_to_move',lambda:calls.append('turn') or chess.BLACK)
 board=chess.Board(); board.remove_piece_at(chess.E2)
 w.ai_done(w.tracking_session_id,w.board_version,False,board,result(side='unknown'),.1,object())
 assert calls==['turn'] and w.board.turn==chess.BLACK; w.close()

def test_recovery_reconciles_one_legal_move_and_preserves_player(monkeypatch):
 w=quiet_window(monkeypatch); w.select_player(chess.BLACK); w.session.browser_orientation=Orientation.BLACK_BOTTOM; w.board=chess.Board(); recovered=w.board.copy(); recovered.push_uci('e2e4'); monkeypatch.setattr(w,'ask_player_color',lambda:pytest.fail('recovery must not ask player')); monkeypatch.setattr(w,'ask_side_to_move',lambda:pytest.fail('legal recovery must preserve turn'))
 w.ai_done(w.tracking_session_id,w.board_version,True,recovered,result(side='unknown'),.1,object())
 assert w.player_color==chess.BLACK and w.session.app_display_orientation is Orientation.BLACK_BOTTOM and w.board.peek().uci()=='e2e4' and w.board.turn==chess.BLACK
 w.close()

def test_recovery_replacement_asks_only_who_moves_next(monkeypatch):
 w=quiet_window(monkeypatch); w.select_player(chess.BLACK); w.session.browser_orientation=Orientation.BLACK_BOTTOM; calls=[]; monkeypatch.setattr(w,'ask_player_color',lambda:pytest.fail('recovery must not ask player')); monkeypatch.setattr(w,'ask_side_to_move',lambda:calls.append('turn') or chess.WHITE)
 replacement=chess.Board(); replacement.remove_piece_at(chess.A2); replacement.remove_piece_at(chess.B2)
 w.ai_done(w.tracking_session_id,w.board_version,True,replacement,result(side='unknown'),.1,object())
 assert calls==['turn'] and w.player_color==chess.BLACK and w.board.turn==chess.WHITE
 w.close()

class FakeEngine:
 def __init__(self):self.submissions=[]
 def isRunning(self):return True
 def submit(self,fen,version):self.submissions.append((fen,version))
 def stop(self):pass

def test_black_player_turn_sequence_uses_board_turn_without_dialogs(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.select_player(chess.BLACK); w.engine_path='stockfish'; w.engine_worker=FakeEngine(); w.board=chess.Board(); w.board.push_uci('e2e4'); monkeypatch.setattr(w,'ask_side_to_move',lambda:pytest.fail('live tracking must not ask turn'))
 w.analyze(); assert len(w.engine_worker.submissions)==1 and 'Your turn' in w.status.text()
 w.board.push_uci('g8f6'); w.analyze(); assert w.status.text()=='Waiting for opponent' and len(w.engine_worker.submissions)==1
 w.board.push_uci('g1f3'); w.analyze(); assert len(w.engine_worker.submissions)==2 and 'Your turn' in w.status.text(); w.close()

def test_white_player_turn_sequence_uses_board_turn_without_dialogs(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.select_player(chess.WHITE); w.engine_path='stockfish'; w.engine_worker=FakeEngine(); w.board=chess.Board(); monkeypatch.setattr(w,'ask_side_to_move',lambda:pytest.fail('live tracking must not ask turn'))
 w.analyze(); assert len(w.engine_worker.submissions)==1
 w.board.push_uci('e2e4'); w.analyze(); assert w.status.text()=='Waiting for opponent'
 w.board.push_uci('e7e5'); w.analyze(); assert len(w.engine_worker.submissions)==2 and 'Your turn' in w.status.text(); w.close()

def test_widget_reads_canonical_board_reference():
 app=QApplication.instance() or QApplication([]); w=MainWindow(); assert w.view.board is w.board
 w.board.push_uci('e2e4'); w.view.update(); assert w.view.piece_map()==w.board.piece_map(); w.close()

def test_stale_analysis_is_discarded():
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.board_version=4; before=w.best.text(); w.analysis_done(3,[('e4','e2e4',20,None,12)]); assert w.best.text()==before; w.close()

def test_rescan_invalidates_and_clears_player_session(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.select_player(chess.BLACK); old=w.tracking_session_id; monkeypatch.setattr(w,'hide',lambda:None); monkeypatch.setattr('app.main.QTimer.singleShot',lambda *args:None); w.scan_board()
 assert w.tracking_session_id==old+1 and w.player_color is None and w.session.browser_orientation is None; w.close()

def test_tracking_compares_new_frames_to_last_accepted_frame(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.session.browser_orientation=Orientation.WHITE_BOTTOM; baseline=np.zeros((64,64,3),dtype=np.uint8); newest=np.ones_like(baseline); w.previous=baseline; seen=[]
 monkeypatch.setattr('app.main.score_squares',lambda old,new,orientation:seen.append((old,new,orientation)) or {})
 w.tracking_frame(w.tracking_session_id,newest)
 assert len(seen)==1 and seen[0][0] is baseline and seen[0][1] is newest and seen[0][2] is Orientation.WHITE_BOTTOM
 assert w.previous is baseline and w.session.latest_frame is newest
 w.close()

def test_black_bottom_arrow_endpoints_use_flipped_visual_cells():
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.view.resize(420,420); w.view.set_orientation(Orientation.BLACK_BOTTOM); w.view.arrow=(chess.G8,chess.F6)
 start=w.view._rect_for(chess.G8).center(); end=w.view._rect_for(chess.F6).center(); assert (start.x(),start.y())==(78.75,393.75) and (end.x(),end.y())==(131.25,288.75); w.close()

def test_svg_assets_cover_every_piece():
 for color in ('white','black'):
  for name in ('pawn','knight','bishop','rook','queen','king'):assert Path(f'assets/pieces/{color}_{name}.svg').exists()
