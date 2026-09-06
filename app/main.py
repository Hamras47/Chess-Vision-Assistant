import sys,os,time,logging,shutil,chess,cv2,numpy as np
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QFileDialog,QMessageBox,QDialog,QDialogButtonBox,QFormLayout,QLineEdit
from PySide6.QtCore import Qt,QSettings,QTimer
from .board_widget import ChessBoardWidget
from .engine import EngineWorker
from .vision.capture import ScreenCapture
from .vision.grid import locked_square_crop
from .vision.change_detector import frame_signature,signature_difference
from .vision.tracking_worker import TrackingWorker
from .ui.region_selector import RegionSelector
from .ui.dpi_coordinates import match_monitor
from .ai.board_recognizer import RecognitionWorker
from .ai.openai_client import OpenAIClient,DEFAULT_OPENAI_VISION_MODEL,resolve_model
from .chess.move_tracker import reconcile_reconstruction
from .chess.coordinates import Orientation
from .chess.session import TrackingSession,SYNCED,VERIFYING,RECOVERING,LOST
from .core.logging_setup import LOG_DIRECTORY,configure,install_exception_hook

class MainWindow(QMainWindow):
 def __init__(self):
  super().__init__(); self.settings=QSettings('ChessVisionAssistant','V16'); self.debug=self.settings.value('debug_mode',False,type=bool) or os.getenv('CHESS_VISION_DEBUG')=='1'; configure(self.debug)
  stored=self.settings.value('ai_model','',type=str); self.model=resolve_model(stored); self.openai_client=OpenAIClient(self.model); logging.info('APP_START'); logging.info('OPENAI_MODEL_RESOLVED model=%s source=%s',self.model,'settings' if stored else 'environment_or_default'); logging.info('PIECE_STATE_FROM_CANONICAL_ONLY'); self.engine_path=self.find_engine(); self.session=TrackingSession(); self.tracker=None; self.ai_worker=None; self.last_recovery=0.; self.recovery_attempts=0; self.recovery=False; self.recovery_in_progress=False; self.recovery_request_id=0; self.recovery_started=0.; self.last_capture=0.; self.pending_move=None; self.board_size=0; self.square_size=0.; self.last_recommended_uci=None; self.settle_started=0.; self.settle_frame=None; self.debounce_until=0.; self.rescan_pending=False; self.ai_metrics={'changes':0,'scans':0,'success':0,'failed':0,'plies0':0,'plies1':0,'plies2':0,'resyncs':0,'latency_total':0.}; self.restart_times=[]; self.restart_pending=False; self._closing=False
  self.setWindowTitle('Chess Vision Assistant V1.6'); self.resize(850,570); self.setWindowFlag(Qt.WindowStaysOnTopHint,True)
  root=QWidget(); self.setCentralWidget(root); outer=QVBoxLayout(root); header=QHBoxLayout(); title=QLabel('Chess Vision Assistant'); title.setObjectName('title'); gear=QPushButton('⚙'); gear.setFixedWidth(42); gear.clicked.connect(self.open_settings); header.addWidget(title); header.addStretch(); header.addWidget(gear); outer.addLayout(header)
  body=QHBoxLayout(); self.view=ChessBoardWidget(); body.addWidget(self.view,1); side=QVBoxLayout(); self.position=QLabel('POSITION\nReady'); self.playing=QLabel('Playing: White'); self.best=QLabel('BEST MOVE\n—'); self.evaluation=QLabel('Evaluation —'); self.alts=QLabel(''); self.scan_button=QPushButton('SCAN BOARD'); self.scan_button.clicked.connect(self.scan_board); side.addWidget(self.position); side.addWidget(self.playing); side.addSpacing(18); side.addWidget(self.best); side.addWidget(self.evaluation); side.addWidget(self.alts); side.addStretch(); side.addWidget(self.scan_button); body.addLayout(side); outer.addLayout(body,1); self.status=QLabel('Ready'); outer.addWidget(self.status)
  self.setStyleSheet("QMainWindow{background:#171a1f} QLabel{color:#e9edf1;font-size:15px;padding:5px} QLabel#title{font-size:20px;font-weight:600} QPushButton{background:#303640;color:white;padding:11px;border:1px solid #48505c;border-radius:6px} QPushButton:hover{background:#3a424e}")
  self.view.set_board(self.board)
  if not self.engine_path: self.status.setText('Stockfish needs to be configured. Open Settings.')
  self.engine_worker=None
  if self.engine_path:self.start_engine()
  self.watchdog=QTimer(self); self.watchdog.setInterval(1000); self.watchdog.timeout.connect(self.check_watchdog); self.watchdog.start(); install_exception_hook(self.crash_context)
 @property
 def board(self):return self.session.board
 @board.setter
 def board(self,value):self.session.board=value
 @property
 def board_version(self):return self.session.board_version
 @board_version.setter
 def board_version(self,value):self.session.board_version=value
 @property
 def tracking_session_id(self):return self.session.tracking_session_id
 @tracking_session_id.setter
 def tracking_session_id(self,value):self.session.tracking_session_id=value
 @property
 def region(self):return self.session.board_region
 @region.setter
 def region(self,value):self.session.board_region=value
 @property
 def previous(self):return self.session.last_accepted_frame
 @previous.setter
 def previous(self,value):self.session.last_accepted_frame=value
 @property
 def player_color(self):return self.session.player_color
 @property
 def opponent_color(self):return self.session.opponent_color
 def set_sync_state(self,new_state,reason):
  old_state=self.session.tracking_state
  self.session.tracking_state=new_state
  if old_state!=new_state:logging.info('SYNC_STATE_CHANGED old_state=%s new_state=%s reason=%s',old_state,new_state,reason)
 def lock_board_rect(self,rect,crop):
  self.region=dict(rect); self.board_size=rect['width']; self.square_size=rect['width']/8; self.reset_baseline(crop); logging.info('BOARD_RECT_LOCKED x=%d y=%d size=%d',rect['left'],rect['top'],rect['width'])
 def save_openai_crop(self,crop):
  if self.debug:
   debug=LOG_DIRECTORY/'debug'; debug.mkdir(parents=True,exist_ok=True); cv2.imwrite(str(debug/'latest_openai_board.png'),crop)
 def crop_is_valid(self,crop):
  valid=crop is not None and crop.ndim==3 and crop.shape[0]==crop.shape[1] and crop.shape[0]>=64
  logging.info('RECOVERY_CROP_%s size=%s reason=%s','VALIDATED' if valid else 'REJECTED',None if crop is None else f'{crop.shape[1]}x{crop.shape[0]}','locked board rectangle' if valid else 'not a plausible square crop')
  return valid
 def find_engine(self):
  stored=self.settings.value('stockfish','')
  if stored and Path(stored).exists():return stored
  found=shutil.which('stockfish')
  if found:return found
  for p in Path('.').glob('**/stockfish*.exe'):
   if '.venv' not in p.parts:return str(p.resolve())
  return ''
 def scan_board(self):
  logging.info('%s session=%d', 'RESCAN_STARTED' if self.region else 'SCAN_STARTED',self.tracking_session_id+1); self.tracking_session_id+=1; self.board_version+=1; self.session.player_color=None; self.session.browser_orientation=None; self.session.last_accepted_frame=None; self.session.latest_frame=None; self.session.last_capture_signature=None; self.session.last_accepted_signature=None; self.session.frame_sequence=0; self.set_sync_state(SYNCED,'scan reset'); self.pending_move=None; self.recovery_attempts=0
  if self.tracker:self.stop_tracking()
  self.hide(); QTimer.singleShot(180,self.begin_snip)
 def begin_snip(self):
  try:
   frames=ScreenCapture().monitor_frames(); monitors=[m for _,m in frames]; self.selectors=[]
   for screen in QApplication.screens():
    logging.debug('Qt screen name=%s geometry=%s available=%s DPR=%.2f; MSS monitors=%s',screen.name(),screen.geometry(),screen.availableGeometry(),screen.devicePixelRatio(),monitors)
    mapping=match_monitor(screen,monitors); frame=next(img for img,m in frames if m is mapping.physical); selector=RegionSelector(frame,mapping); selector.selected.connect(self.snip_selected); selector.cancelled.connect(self.snip_cancelled); selector.show(); self.selectors.append(selector)
   if self.selectors:self.selectors[0].activateWindow()
  except Exception: logging.exception('desktop capture failed'); self.show(); self.user_error('Could not capture the desktop.')
 def close_selectors(self):
  for selector in getattr(self,'selectors',[]):selector.hide(); selector.deleteLater()
  self.selectors=[]
 def snip_cancelled(self): self.close_selectors(); self.show(); self.status.setText('Ready')
 def snip_selected(self,selection):
  self.close_selectors(); rough=selection['physical']; self.logical_selection=selection['logical']; self.physical_selection=rough; logging.info('RAW_SELECTION x=%d y=%d w=%d h=%d',rough['left'],rough['top'],rough['width'],rough['height'])
  try:
   image=ScreenCapture().grab(rough); crop,(x,y,size,_)=locked_square_crop(image); rect={'left':rough['left']+x,'top':rough['top']+y,'width':size,'height':size}
   self.lock_board_rect(rect,crop); logging.info('BOARD_REGION_SELECTED x=%d y=%d width=%d height=%d',self.region['left'],self.region['top'],self.region['width'],self.region['height'])
   if self.debug:
    Path('debug').mkdir(exist_ok=True); cv2.imwrite('debug/post_selection_capture.png',image); cv2.imwrite('debug/selected_frozen.png',selection['frozen_image'])
    same=image.shape==selection['frozen_image'].shape and np.array_equal(image,selection['frozen_image']); logging.debug('Frozen selection versus post-selection capture exact_pixel_match=%s frozen_shape=%s post_shape=%s',same,selection['frozen_image'].shape,image.shape)
   self.save_openai_crop(crop); self.show(); self.raise_(); self.status.setText('Scanning...'); self.position.setText('POSITION\nScanning...'); self.start_ai(crop,False)
  except Exception: logging.exception('board crop failed'); self.show(); self.user_error('Could not capture the selected board.')
 def start_ai(self,crop,recovery,request_id=None):
  if recovery and not self.crop_is_valid(crop):self.ai_failed(self.tracking_session_id,self.board_version,'bad recovery crop',request_id); return
  if self.ai_worker and self.ai_worker.isRunning():return
  if not self.openai_client.ready():
   if recovery:self.recovery=True; self.ai_failed(self.tracking_session_id,self.board_version,'OpenAI is not configured'); return
   self.user_error('OpenAI is not configured. Add the API key to .env.'); return
  self.recovery=recovery
  if recovery:self.set_sync_state(RECOVERING,'stable visual change'); self.recovery_started=time.monotonic(); self.session.ai_recoveries+=1; self.ai_metrics['scans']+=1; self.status.setText('● Reading board...'); self.position.setText('POSITION\n● Reading board...'); logging.info('AI_BOARD_SCAN_STARTED request_id=%d version=%d',request_id,self.board_version)
  self.save_openai_crop(crop); session=self.tracking_session_id; version=self.board_version; self.ai_worker=RecognitionWorker(crop,self.model,self.debug,self.openai_client); self.ai_worker.result.connect(lambda b,r,l:self.ai_done(session,version,recovery,b,r,l,crop,request_id)); self.ai_worker.error.connect(lambda error:self.ai_failed(session,version,error,request_id)); self.ai_worker.start()
 def ask_color(self,title,text,white_label='WHITE',black_label='BLACK'):
  dialog=QMessageBox(self); dialog.setWindowTitle(title); dialog.setText(text); dialog.setWindowFlag(Qt.WindowCloseButtonHint,False); white=dialog.addButton(white_label,QMessageBox.AcceptRole); black=dialog.addButton(black_label,QMessageBox.RejectRole)
  while True:
   dialog.exec()
   if dialog.clickedButton() is white:return chess.WHITE
   if dialog.clickedButton() is black:return chess.BLACK
 def ask_player_color(self):return self.ask_color('Player color','You are playing:')
 def ask_my_turn(self):
  mine=self.ask_color('Whose turn?','Who moves next?','MY TURN',"OPPONENT'S TURN")
  turn=self.player_color if mine==chess.WHITE else self.opponent_color; logging.info('TURN_SELECTED turn=%s selection=%s','white' if turn else 'black','my_turn' if mine==chess.WHITE else 'opponent_turn'); return turn
 def is_starting_position(self,board):return board.board_fen()==chess.STARTING_BOARD_FEN
 def select_player(self,color):
  self.session.select_player(color); self.view.set_orientation(self.session.app_display_orientation); self.playing.setText('Playing: '+('White' if color else 'Black')); logging.info('PLAYER_COLOR_SELECTED color=%s','white' if color else 'black')
 def ai_done(self,session,version,recovery,board,result,latency,crop,request_id=None):
  if session!=self.tracking_session_id or version!=self.board_version or (recovery and (not self.recovery_in_progress or request_id!=self.recovery_request_id)):return
  if recovery and not board.is_valid():logging.error('Discarded invalid staged AI recovery board fen=%s',board.fen()); self.ai_failed(session,version,'invalid reconstructed board'); return
  if not recovery:
   self.session.browser_orientation=Orientation.WHITE_BOTTOM if result.orientation=='unknown' else Orientation(result.orientation)
   self.select_player(self.ask_player_color())
   board.turn=self.ask_my_turn()
  else:
   reconciled,recovered_moves=reconcile_reconstruction(self.board,board,2)
   if reconciled is not None:
    board=reconciled
    self.ai_metrics[f'plies{len(recovered_moves)}']+=1; logging.info('AI_RECONCILIATION plies=%d',len(recovered_moves))
   else:
    board.turn=self.ask_my_turn(); self.ai_metrics['resyncs']+=1; logging.warning('AI_RECONCILIATION full_resync=true')
  pending=self.rescan_pending; self.rescan_pending=False; self.board=board; self.board_version+=1; self.reset_baseline(crop); self.recovery_in_progress=False; self.ai_metrics['success']+=1; self.ai_metrics['latency_total']+=latency; self.set_sync_state(SYNCED,'AI board accepted'); self.pending_move=None; self.view.set_orientation(self.session.app_display_orientation); self.view.set_board(self.board); logging.info('AI_BOARD_SCAN_RESULT confidence=%.3f latency_seconds=%.3f',result.confidence,latency); logging.info('AI_BOARD_ACCEPTED version=%d',self.board_version); self.status.setText('● Synced'); self.position.setText('POSITION\n● Synced'); self.scan_button.setText('RESCAN'); self.recovery_attempts=0; self.debounce_until=time.monotonic()+.4; self.start_tracking(); QTimer.singleShot(350,lambda:self.refresh_baseline(session,self.board_version)); self.analyze()
  if pending:logging.info('AI_RESCAN_QUEUED dispatching=true'); QTimer.singleShot(450,lambda:self.recover(self.current_frame()))
 def ai_failed(self,session,version,technical,request_id=None):
  if session!=self.tracking_session_id or version!=self.board_version or (self.recovery and request_id is not None and request_id!=self.recovery_request_id):return
  logging.error('AI recognition failed: %s',technical)
  if self.recovery:
   self.recovery_in_progress=False; self.ai_metrics['failed']+=1; self.session.failed_ai_recoveries+=1; self.pending_move=None; logging.warning('AI_BOARD_REJECTED reason=%s',technical)
   if self.recovery_attempts>=2:self.tracking_lost('Could not read board. Press Rescan.')
   else:self.set_sync_state(VERIFYING,'AI scan failed; retrying once'); QTimer.singleShot(250,lambda:self.recover(self.current_frame()))
   return
  logging.error('WORKER_ERROR worker=recognition error=%s',technical); self.stop_tracking(); self.position.setText('POSITION\nTracking lost'); self.user_error('Could not recognize board.')
 def start_tracking(self):
  self.stop_tracking(); session=self.tracking_session_id; self.last_capture=time.monotonic(); self.settle_started=0.; self.settle_frame=None; interval=max(75,min(500,int(self.settings.value('tracking_interval',125)))); self.tracker=TrackingWorker(self.region,interval); self.tracker.frame.connect(lambda crop:self.tracking_frame(session,crop)); self.tracker.heartbeat.connect(lambda stamp:self.tracker_heartbeat(session,stamp)); self.tracker.metrics.connect(lambda fps,average,count:self.tracker_metrics(session,fps,average,count)); self.tracker.failed.connect(lambda error:self.tracker_failed(session,error)); self.tracker.start(); logging.info('TRACKER_STARTED interval_ms=%d session=%d',interval,session)
 def stop_tracking(self):
  if self.tracker:self.tracker.stop(); self.tracker=None
 def retry_recovery(self):
  try:self.start_ai(self.current_frame(),True)
  except Exception:logging.exception('WORKER_ERROR worker=recovery_capture'); self.set_sync_state(VERIFYING,'recovery capture failed'); self.status.setText('● Checking position')
 def current_frame(self):
  return ScreenCapture().grab(self.region)
 def tracking_frame(self,session,crop):
  if session!=self.tracking_session_id or self.previous is None:return
  now=time.monotonic(); self.session.frame_sequence+=1; self.session.latest_frame=crop; signature=frame_signature(crop); self.session.last_capture_signature=signature
  if self.recovery_in_progress:
   if signature_difference(self.session.last_accepted_signature,signature)>=.010:self.rescan_pending=True; logging.info('AI_RESCAN_QUEUED')
   return
  if self.session.tracking_state==LOST or now<self.debounce_until:return
  if signature_difference(self.session.last_accepted_signature,signature)<.010:self.settle_started=0.; self.settle_frame=None; return
  if not self.settle_started:
   self.ai_metrics['changes']+=1; self.settle_started=now; self.settle_frame=crop; self.set_sync_state(VERIFYING,'visual change detected'); self.status.setText('● Reading board...'); logging.info('VISUAL_CHANGE_DETECTED'); return
  stable=signature_difference(frame_signature(self.settle_frame),signature)<.012
  elapsed=now-self.settle_started
  if not stable and elapsed<.70:self.settle_frame=crop; return
  logging.info('BOARD_SETTLED latency_ms=%d',round(elapsed*1000)); self.settle_started=0.; self.settle_frame=None; self.recover(crop)
 def reset_baseline(self,crop,signature=None):
  self.previous=crop.copy(); self.session.last_accepted_signature=signature if signature is not None else frame_signature(crop); self.session.last_capture_signature=self.session.last_accepted_signature; logging.info('BASELINE_RESET version=%d locked_rect=%s',self.board_version,self.region)
 def refresh_baseline(self,session,version):
  if session!=self.tracking_session_id or version!=self.board_version or self.recovery_in_progress:return
  try:self.reset_baseline(self.current_frame())
  except Exception:logging.exception('WORKER_ERROR worker=baseline_capture')
 def recover(self,crop):
  now=time.monotonic()
  if self.recovery_in_progress or (self.ai_worker and self.ai_worker.isRunning()):return
  if self.recovery_attempts>=2:self.tracking_lost(); return
  self.last_recovery=now; self.recovery_attempts+=1; self.recovery=True; self.recovery_in_progress=True; self.recovery_request_id+=1; request_id=self.recovery_request_id; self.set_sync_state(RECOVERING,'local reconciliation failed'); self.hide(); QTimer.singleShot(150,lambda:self.capture_recovery_board(request_id))
 def capture_recovery_board(self,request_id):
  if not self.recovery_in_progress or request_id!=self.recovery_request_id:return
  try:
   crop=ScreenCapture().grab(self.region)
   self.show(); self.raise_()
   if crop is None:self.ai_failed(self.tracking_session_id,self.board_version,'bad locked recovery crop',request_id); return
   self.start_ai(crop,True,request_id)
  except Exception:
   self.show(); self.raise_(); logging.exception('WORKER_ERROR worker=recovery_capture'); self.ai_failed(self.tracking_session_id,self.board_version,'recovery capture failed',request_id)
 def tracking_lost(self,reason='recovery attempts exhausted'): self.set_sync_state(LOST,reason); logging.error('TRACKING_LOST reason=%s',reason); self.stop_tracking(); self.position.setText('POSITION\n● Tracking lost'); self.status.setText('● Tracking lost'); self.scan_button.setText('RESCAN')
 def tracker_heartbeat(self,session,stamp):
  if session==self.tracking_session_id:self.last_capture=stamp
 def tracker_metrics(self,session,fps,average,count):
  if session==self.tracking_session_id:logging.info('Tracker metrics capture_fps=%.2f average_capture_ms=%.2f samples=%d board_version=%d state=%s ai_scans=%d ai_success=%d ai_failed=%d',fps,average,count,self.board_version,self.session.tracking_state,self.ai_metrics['scans'],self.ai_metrics['success'],self.ai_metrics['failed'])
 def tracker_failed(self,session,error):
  if session!=self.tracking_session_id:return
  logging.error('WORKER_ERROR worker=tracker session=%d error=%s',session,error); self.schedule_tracker_restart()
 def schedule_tracker_restart(self):
  if self.restart_pending:return
  now=time.monotonic(); self.restart_times=[t for t in self.restart_times if now-t<60]
  if len(self.restart_times)>=3:self.tracking_lost(); return
  self.restart_pending=True; self.restart_times.append(now); logging.warning('Restarting tracker attempt=%d/3',len(self.restart_times)); QTimer.singleShot(600,self.restart_tracker_if_current)
 def restart_tracker_if_current(self):
  self.restart_pending=False
  if self.region and not self._closing:self.start_tracking()
 def check_watchdog(self):
  if self._closing or not self.region or not self.tracker:return
  now=time.monotonic()
  if self.recovery_in_progress and self.session.tracking_state==RECOVERING and self.recovery_started and now-self.recovery_started>20:
   request_id=self.recovery_request_id; self.recovery_in_progress=False; logging.error('OPENAI_RECOVERY_TIMEOUT request_id=%d timeout_seconds=20',request_id); self.ai_failed(self.tracking_session_id,self.board_version,'OpenAI recovery timed out',request_id); return
  if not self.tracker.isRunning() or time.monotonic()-self.last_capture>2:self.schedule_tracker_restart()
 def start_engine(self):
  if self.engine_worker:self.engine_worker.stop()
  self.engine_worker=EngineWorker(self.engine_path,float(self.settings.value('analysis_time',.6))); self.engine_worker.result.connect(self.analysis_done); self.engine_worker.error.connect(lambda session,version,error:logging.error('Stockfish session=%d version=%d error=%s',session,version,error)); self.engine_worker.start()
 def analyze(self):
  if self.player_color is None or self.session.tracking_state!=SYNCED:return
  if self.board.turn!=self.player_color:
   self.view.arrow=None; self.view.update(); self.best.setText('BEST MOVE\nWaiting'); self.evaluation.setText('Evaluation —'); self.alts.setText(''); self.position.setText('POSITION\n● Watching'); self.status.setText('Waiting for opponent'); return
  self.position.setText('POSITION\n● Your turn')
  if not self.engine_path:self.status.setText('Your turn'); return
  if not self.engine_worker or not self.engine_worker.isRunning():self.start_engine()
  self.status.setText('Your turn — analyzing...'); logging.info('STOCKFISH_STARTED version=%d',self.board_version); self.engine_worker.submit(self.board.fen(),self.tracking_session_id,self.board_version)
 def analysis_done(self,session,version,rows):
  if session!=self.tracking_session_id or version!=self.board_version or self.player_color is None or self.board.turn!=self.player_color or self.session.tracking_state!=SYNCED or not rows:logging.info('Discarded stale/inapplicable Stockfish result'); return
  san,uci,score,mate,_=rows[0]; self.last_recommended_uci=uci; self.best.setText(f'BEST MOVE\n{san}\n{uci[:2]} → {uci[2:4]}'); self.evaluation.setText('Evaluation '+(f'Mate {mate}' if mate is not None else f'{score/100:+.2f}')); self.alts.setText('Alternatives: '+', '.join(x[0] for x in rows[1:3])); self.view.arrow=(chess.parse_square(uci[:2]),chess.parse_square(uci[2:4])); self.view.update(); self.status.setText('Your turn'); logging.info('STOCKFISH_RESULT version=%d',version)
 def open_settings(self):
  dialog=QDialog(self); dialog.setWindowTitle('Settings'); form=QFormLayout(dialog); model=QLineEdit(self.model); reset=QPushButton('RESET TO DEFAULT'); reset.clicked.connect(lambda:model.setText(DEFAULT_OPENAI_VISION_MODEL)); form.addRow('OpenAI model:',model); form.addRow('',reset); buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
  if dialog.exec()!=QDialog.Accepted:return
  self.model=resolve_model(model.text().strip()); self.openai_client=OpenAIClient(self.model); self.settings.setValue('ai_model',self.model); logging.info('OPENAI_MODEL model=%s',self.model)
  if not self.engine_path and QMessageBox.question(self,'Settings','Locate Stockfish now?')==QMessageBox.Yes:
   p=QFileDialog.getOpenFileName(self,'Locate Stockfish','','Executable (*.exe)')[0]
   if p:self.engine_path=p; self.settings.setValue('stockfish',p); self.start_engine()
 def user_error(self,text): self.status.setText(text); QMessageBox.warning(self,'Chess Vision Assistant',text)
 def crash_context(self):return {'fen':self.board.fen(),'tracking':bool(self.tracker and self.tracker.isRunning()),'tracking_state':self.session.tracking_state,'frame_sequence':self.session.frame_sequence,'region':self.region,'board_version':self.board_version,'session':self.tracking_session_id}
 def closeEvent(self,event):
  if self.ai_worker and self.ai_worker.isRunning() and not self._closing:
   self._closing=True; self.tracking_session_id+=1; self.stop_tracking(); self.status.setText('Finishing current scan before closing...'); self.ai_worker.finished.connect(self.close); event.ignore(); return
  self._closing=True; self.tracking_session_id+=1; self.watchdog.stop(); self.stop_tracking()
  if self.engine_worker:self.engine_worker.stop(); self.engine_worker=None
  super().closeEvent(event)
if __name__=='__main__':
 app=QApplication(sys.argv); window=MainWindow(); window.show(); sys.exit(app.exec())
