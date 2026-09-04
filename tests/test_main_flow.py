import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import chess,pytest,numpy as np,time
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from app.main import MainWindow
from app.chess.coordinates import Orientation
from app.chess.move_tracker import transition_squares
from app.vision.change_detector import frame_signature

FRAME=np.zeros((64,64,3),dtype=np.uint8)

def result(side='white',orientation='white_bottom'):
 return SimpleNamespace(side_to_move=side,orientation=orientation,confidence=.98,warnings=[])

def quiet_window(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); monkeypatch.setattr(w,'start_tracking',lambda:None); monkeypatch.setattr(w,'analyze',lambda:None); return w

def test_successful_scan_explicitly_selects_player_and_starts_tracking(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); calls=[]
 monkeypatch.setattr(w,'ask_player_color',lambda:chess.BLACK); monkeypatch.setattr(w,'start_tracking',lambda:calls.append('tracking')); monkeypatch.setattr(w,'analyze',lambda:calls.append('analysis'))
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result(),.1,FRAME)
 assert calls==['tracking','analysis'] and w.player_color==chess.BLACK
 assert w.session.app_display_orientation is Orientation.BLACK_BOTTOM and w.playing.text()=='Playing: Black' and w.scan_button.text()=='RESCAN'; w.close()

def test_player_choice_and_browser_orientation_are_independent(monkeypatch):
 w=quiet_window(monkeypatch); monkeypatch.setattr(w,'ask_player_color',lambda:chess.WHITE)
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result(orientation='black_bottom'),.1,FRAME)
 assert w.session.browser_orientation is Orientation.BLACK_BOTTOM
 assert w.session.app_display_orientation is Orientation.WHITE_BOTTOM and w.view.orientation is Orientation.WHITE_BOTTOM
 w.close()

def test_unknown_browser_orientation_has_separate_explicit_choice(monkeypatch):
 w=quiet_window(monkeypatch); calls=[]; monkeypatch.setattr(w,'ask_player_color',lambda:chess.BLACK); monkeypatch.setattr(w,'ask_browser_orientation',lambda:calls.append('browser') or Orientation.WHITE_BOTTOM)
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result(orientation='unknown'),.1,FRAME)
 assert calls==['browser'] and w.session.browser_orientation is Orientation.WHITE_BOTTOM and w.session.app_display_orientation is Orientation.BLACK_BOTTOM
 w.close()

def test_starting_position_is_white_to_move_without_turn_dialog(monkeypatch):
 w=quiet_window(monkeypatch); monkeypatch.setattr(w,'ask_player_color',lambda:chess.BLACK); monkeypatch.setattr(w,'ask_side_to_move',lambda:pytest.fail('turn dialog must not open for starting position'))
 w.ai_done(w.tracking_session_id,w.board_version,False,chess.Board(),result(side='unknown'),.1,FRAME)
 assert w.board.turn==chess.WHITE; w.close()

def test_unknown_midgame_turn_is_asked_exactly_once(monkeypatch):
 w=quiet_window(monkeypatch); calls=[]; monkeypatch.setattr(w,'ask_player_color',lambda:chess.WHITE); monkeypatch.setattr(w,'ask_side_to_move',lambda:calls.append('turn') or chess.BLACK)
 board=chess.Board(); board.remove_piece_at(chess.E2)
 w.ai_done(w.tracking_session_id,w.board_version,False,board,result(side='unknown'),.1,FRAME)
 assert calls==['turn'] and w.board.turn==chess.BLACK; w.close()

def test_recovery_reconciles_one_legal_move_and_preserves_player(monkeypatch):
 w=quiet_window(monkeypatch); w.select_player(chess.BLACK); w.session.browser_orientation=Orientation.BLACK_BOTTOM; w.board=chess.Board(); recovered=w.board.copy(); recovered.push_uci('e2e4'); monkeypatch.setattr(w,'ask_player_color',lambda:pytest.fail('recovery must not ask player')); monkeypatch.setattr(w,'ask_side_to_move',lambda:pytest.fail('legal recovery must preserve turn'))
 w.ai_done(w.tracking_session_id,w.board_version,True,recovered,result(side='unknown'),.1,FRAME)
 assert w.player_color==chess.BLACK and w.session.app_display_orientation is Orientation.BLACK_BOTTOM and w.board.peek().uci()=='e2e4' and w.board.turn==chess.BLACK
 w.close()

def test_recovery_replacement_asks_only_who_moves_next(monkeypatch):
 w=quiet_window(monkeypatch); w.select_player(chess.BLACK); w.session.browser_orientation=Orientation.BLACK_BOTTOM; calls=[]; monkeypatch.setattr(w,'ask_player_color',lambda:pytest.fail('recovery must not ask player')); monkeypatch.setattr(w,'ask_side_to_move',lambda:calls.append('turn') or chess.WHITE)
 replacement=chess.Board(); replacement.remove_piece_at(chess.A2); replacement.remove_piece_at(chess.B2)
 w.ai_done(w.tracking_session_id,w.board_version,True,replacement,result(side='unknown'),.1,FRAME)
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
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.session.browser_orientation=Orientation.WHITE_BOTTOM; baseline=np.zeros((64,64,3),dtype=np.uint8); newest=np.full_like(baseline,255); w.previous=baseline; seen=[]
 monkeypatch.setattr('app.main.score_squares',lambda old,new,orientation:seen.append((old,new,orientation)) or {})
 w.tracking_frame(w.tracking_session_id,newest)
 assert len(seen)==1 and seen[0][0] is baseline and seen[0][1] is newest and seen[0][2] is Orientation.WHITE_BOTTOM
 assert w.previous is baseline and w.session.latest_frame is newest
 w.close()

class AlwaysStable:
 state='NEW_STABLE_POSITION'
 def observe(self,frame,changed):return True
 def reset(self):pass

def test_medium_confidence_move_waits_for_another_stable_frame(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.select_player(chess.BLACK); w.session.browser_orientation=Orientation.WHITE_BOTTOM; w.previous=FRAME.copy(); w.session.last_accepted_signature=np.zeros((16,16),dtype=np.uint8); w.stabilizer=AlwaysStable(); w.baseline_frames=0; w.last_consistency=w.last_strong_consistency=time.monotonic(); monkeypatch.setattr(w,'analyze',lambda:None)
 move=chess.Move.from_uci('e2e4'); signals={square:{'combined':.10} for square in chess.SQUARES}; monkeypatch.setattr('app.main.score_squares',lambda *args:signals); monkeypatch.setattr('app.main.infer_move',lambda *args:(move,.80,[(.80,move,{chess.E2,chess.E4})])); monkeypatch.setattr('app.main.visual_plausibility',lambda *args:.90)
 changed=np.full_like(FRAME,255); w.tracking_frame(w.tracking_session_id,changed); assert len(w.board.move_stack)==0 and w.pending_move==(0,'e2e4')
 w.tracking_frame(w.tracking_session_id,changed); assert w.board.peek()==move and w.board.turn==chess.BLACK
 w.close()

def test_unchanged_signature_skips_expensive_square_analysis(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.session.browser_orientation=Orientation.WHITE_BOTTOM; w.previous=FRAME.copy(); w.session.last_accepted_signature=frame_signature(w.previous); w.last_consistency=w.last_strong_consistency=time.monotonic(); monkeypatch.setattr('app.main.score_squares',lambda *args:pytest.fail('unchanged frame should be discarded cheaply'))
 w.tracking_frame(w.tracking_session_id,w.previous.copy()); assert w.session.tracking_state=='WATCHING'; w.close()

def test_highlight_only_drift_does_not_trigger_recovery(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.session.browser_orientation=Orientation.WHITE_BOTTOM; baseline=np.full((64,64,3),(120,160,190),dtype=np.uint8); highlighted=np.full((64,64,3),(80,180,210),dtype=np.uint8); w.previous=baseline; w.session.last_accepted_signature=frame_signature(baseline); monkeypatch.setattr(w,'recover',lambda crop:pytest.fail('flat highlight must not trigger recovery'))
 w.tracking_frame(w.tracking_session_id,highlighted); assert w.session.tracking_state=='WATCHING' and w.board.board_fen()==chess.STARTING_BOARD_FEN; w.close()

def test_two_ply_local_recovery_applies_both_moves_without_ai(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.select_player(chess.WHITE); w.session.browser_orientation=Orientation.WHITE_BOTTOM; w.previous=FRAME.copy(); monkeypatch.setattr(w,'analyze',lambda:None); monkeypatch.setattr(w,'start_ai',lambda *args:pytest.fail('strong local recovery must not call AI'))
 visible=w.board.copy(); visible.push_uci('e2e4'); visible.push_uci('e7e5'); observed=transition_squares(w.board,visible); numeric={square:(.10 if square in observed else 0.) for square in chess.SQUARES}
 w.try_local_recovery(np.full_like(FRAME,255),np.full((16,16),255,dtype=np.uint8),observed,numeric,.065)
 assert [move.uci() for move in w.board.move_stack]==['e2e4','e7e5'] and w.session.two_ply_recoveries==1 and w.view.piece_map()==w.board.piece_map(); w.close()

def test_ambiguous_local_recovery_escalates_to_ai(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); calls=[]; monkeypatch.setattr('app.main.infer_legal_sequence',lambda *args:(None,.4,[])); monkeypatch.setattr(w,'start_ai',lambda crop,recovery:calls.append(recovery)); w.last_recovery=0
 w.try_local_recovery(FRAME,frame_signature(FRAME),{chess.E2},{chess.E2:.08},.065)
 assert calls==[True]; w.close()

def test_failed_background_ai_recovery_is_non_modal_and_preserves_state(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.select_player(chess.BLACK); w.session.browser_orientation=Orientation.BLACK_BOTTOM; w.board.push_uci('e2e4'); snapshot=w.board.fen(); version=w.board_version; w.recovery=True; w.recovery_attempts=1; monkeypatch.setattr(w,'user_error',lambda text:pytest.fail('background failure must not show modal error'))
 w.ai_failed(w.tracking_session_id,w.board_version,'mock failure')
 assert w.board.fen()==snapshot and w.board_version==version and w.player_color==chess.BLACK and w.session.browser_orientation is Orientation.BLACK_BOTTOM and w.session.failed_ai_recoveries==1 and w.session.tracking_state=='WATCHING'; w.close()

class SignalStub:
 def connect(self,callback):pass
class FakeTracker:
 def __init__(self,region,interval):self.interval=interval; self.frame=SignalStub(); self.heartbeat=SignalStub(); self.metrics=SignalStub(); self.failed=SignalStub()
 def start(self):pass
 def stop(self):pass
 def isRunning(self):return True
def test_fast_tracker_defaults_and_consistency_intervals(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.region={'left':0,'top':0,'width':64,'height':64}; monkeypatch.setattr('app.main.TrackingWorker',FakeTracker); monkeypatch.setattr(w.settings,'value',lambda key,default=None,*args:default)
 w.start_tracking(); assert w.tracker.interval==125 and w.consistency_interval==1.5 and w.strong_consistency_interval==5.; w.close()

def test_black_bottom_arrow_endpoints_use_flipped_visual_cells():
 app=QApplication.instance() or QApplication([]); w=MainWindow(); w.view.resize(420,420); w.view.set_orientation(Orientation.BLACK_BOTTOM); w.view.arrow=(chess.G8,chess.F6)
 start=w.view._rect_for(chess.G8).center(); end=w.view._rect_for(chess.F6).center(); assert (start.x(),start.y())==(78.75,393.75) and (end.x(),end.y())==(131.25,288.75); w.close()

def test_svg_assets_cover_every_piece():
 for color in ('white','black'):
  for name in ('pawn','knight','bishop','rook','queen','king'):assert Path(f'assets/pieces/{color}_{name}.svg').exists()
