import sys,os,time,logging,shutil,chess,cv2,numpy as np
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QFileDialog,QMessageBox,QInputDialog
from PySide6.QtCore import Qt,QSettings,QTimer
from .board_widget import ChessBoardWidget
from .engine import EngineWorker
from .vision.capture import ScreenCapture
from .vision.grid import board_crop
from .vision.change_detector import score_squares,AdaptiveThreshold
from .vision.stabilizer import Stabilizer
from .vision.tracking_worker import TrackingWorker
from .ui.region_selector import RegionSelector
from .ui.dpi_coordinates import match_monitor
from .ai.board_recognizer import RecognitionWorker
from .ai.openai_client import OpenAIClient,normalize_model
from .chess.move_tracker import infer_move,infer_move_from_scores
from .chess.coordinates import Orientation,user_color,square_to_visual
from .core.logging_setup import configure,install_exception_hook

class MainWindow(QMainWindow):
 def __init__(self):
  super().__init__(); self.settings=QSettings('ChessVisionAssistant','ChessVisionAssistant'); self.debug=self.settings.value('debug_mode',False,type=bool) or os.getenv('CHESS_VISION_DEBUG')=='1'; configure(self.debug)
  requested_model=self.settings.value('ai_model',os.getenv('OPENAI_VISION_MODEL','gpt-5.2')); self.model=normalize_model(requested_model); self.openai_client=OpenAIClient(self.model); self.engine_path=self.find_engine(); self.board=chess.Board(); self.orientation=Orientation.WHITE_BOTTOM; self.user_color=chess.WHITE; self.opponent_color=chess.BLACK; self.board_version=0; self.tracking_session_id=0; self.region=None; self.previous=None; self.tracker=None; self.ai_worker=None; self.stabilizer=Stabilizer(); self.threshold=AdaptiveThreshold(); self.baseline_frames=0; self.last_recovery=0.; self.recovery_attempts=0; self.recovery=False; self.last_capture=0.; self.last_stable=0.; self.last_move=0.; self.restart_times=[]; self.restart_pending=False; self._closing=False
  if requested_model!=self.model:self.settings.setValue('ai_model',self.model)
  self.setWindowTitle('Chess Vision Assistant'); self.resize(850,570); self.setWindowFlag(Qt.WindowStaysOnTopHint,True)
  root=QWidget(); self.setCentralWidget(root); outer=QVBoxLayout(root); header=QHBoxLayout(); title=QLabel('Chess Vision Assistant'); title.setObjectName('title'); gear=QPushButton('⚙'); gear.setFixedWidth(42); gear.clicked.connect(self.open_settings); header.addWidget(title); header.addStretch(); header.addWidget(gear); outer.addLayout(header)
  body=QHBoxLayout(); self.view=ChessBoardWidget(); body.addWidget(self.view,1); side=QVBoxLayout(); self.position=QLabel('POSITION\nReady'); self.playing=QLabel('Playing: White'); self.best=QLabel('BEST MOVE\n—'); self.evaluation=QLabel('Evaluation —'); self.alts=QLabel(''); self.scan_button=QPushButton('SCAN BOARD'); self.scan_button.clicked.connect(self.scan_board); side.addWidget(self.position); side.addWidget(self.playing); side.addSpacing(18); side.addWidget(self.best); side.addWidget(self.evaluation); side.addWidget(self.alts); side.addStretch(); side.addWidget(self.scan_button); body.addLayout(side); outer.addLayout(body,1); self.status=QLabel('Ready'); outer.addWidget(self.status)
  self.setStyleSheet("QMainWindow{background:#171a1f} QLabel{color:#e9edf1;font-size:15px;padding:5px} QLabel#title{font-size:20px;font-weight:600} QPushButton{background:#303640;color:white;padding:11px;border:1px solid #48505c;border-radius:6px} QPushButton:hover{background:#3a424e}")
  self.view.set_board(self.board)
  if not self.engine_path: self.status.setText('Stockfish needs to be configured. Open Settings.')
  self.engine_worker=None
  if self.engine_path:self.start_engine()
  self.watchdog=QTimer(self); self.watchdog.setInterval(2000); self.watchdog.timeout.connect(self.check_watchdog); self.watchdog.start(); install_exception_hook(self.crash_context)
 def find_engine(self):
  stored=self.settings.value('stockfish','')
  if stored and Path(stored).exists():return stored
  found=shutil.which('stockfish')
  if found:return found
  for p in Path('.').glob('**/stockfish*.exe'):
   if '.venv' not in p.parts:return str(p.resolve())
  return ''
 def scan_board(self):
  self.tracking_session_id+=1; self.board_version+=1
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
  self.close_selectors(); rough=selection['physical']; self.logical_selection=selection['logical']; self.physical_selection=rough
  try:
   image=ScreenCapture().grab(rough); ratio=rough['width']/rough['height']; correction=not .90<=ratio<=1.10
   if correction: crop,bounds=board_crop(image); x,y,w,h=bounds; self.region={'left':rough['left']+x,'top':rough['top']+y,'width':w,'height':h}
   else: crop=image; self.region=dict(rough)
   logging.info('User selection physical=%s logical=%s crop_correction_applied=%s final_ai_image=%dx%d',rough,self.logical_selection,correction,crop.shape[1],crop.shape[0])
   if self.debug:
    Path('debug').mkdir(exist_ok=True); cv2.imwrite('debug/post_selection_capture.png',image); cv2.imwrite('debug/selected_frozen.png',selection['frozen_image'])
    same=image.shape==selection['frozen_image'].shape and np.array_equal(image,selection['frozen_image']); logging.debug('Frozen selection versus post-selection capture exact_pixel_match=%s frozen_shape=%s post_shape=%s',same,selection['frozen_image'].shape,image.shape)
   self.show(); self.raise_(); self.status.setText('Scanning...'); self.position.setText('POSITION\nScanning...'); self.start_ai(crop,False)
  except Exception: logging.exception('board crop failed'); self.show(); self.user_error('Could not capture the selected board.')
 def start_ai(self,crop,recovery):
  if self.ai_worker and self.ai_worker.isRunning():return
  if not self.openai_client.ready():self.user_error('OpenAI is not configured. Add the API key to .env.'); return
  self.recovery=recovery; session=self.tracking_session_id; version=self.board_version; self.ai_worker=RecognitionWorker(crop,self.model,self.debug,self.openai_client); self.ai_worker.result.connect(lambda b,r,l:self.ai_done(session,version,recovery,b,r,l,crop)); self.ai_worker.error.connect(lambda error:self.ai_failed(session,version,error)); self.ai_worker.start()
 def ask_orientation(self):
  dialog=QMessageBox(self); dialog.setWindowTitle('Board orientation'); dialog.setText('Which side is at the bottom?'); dialog.setWindowFlag(Qt.WindowCloseButtonHint,False); white=dialog.addButton('WHITE',QMessageBox.AcceptRole); black=dialog.addButton('BLACK',QMessageBox.RejectRole)
  while True:
   dialog.exec()
   if dialog.clickedButton() is white:return Orientation.WHITE_BOTTOM
   if dialog.clickedButton() is black:return Orientation.BLACK_BOTTOM
 def ai_done(self,session,version,recovery,board,result,latency,crop):
  if session!=self.tracking_session_id or version!=self.board_version:return
  if not recovery:
   if result.orientation=='unknown':
    self.orientation=self.ask_orientation()
   else:self.orientation=Orientation(result.orientation)
   self.user_color=user_color(self.orientation); self.opponent_color=not self.user_color
  if result.side_to_move=='unknown':
   answer=QMessageBox.question(self,'Side to move','Is White to move?',QMessageBox.Yes|QMessageBox.No); board.turn=answer==QMessageBox.Yes
  self.board=board; self.board_version+=1; self.previous=crop; self.view.set_orientation(self.orientation); self.view.set_board(self.board); self.playing.setText('Playing: '+('White' if self.user_color else 'Black')); logging.info('Session orientation=%s user_color=%s opponent_color=%s',self.orientation.name,'white' if self.user_color else 'black','black' if self.user_color else 'white'); self.status.setText('Board synchronized'); self.position.setText('POSITION\n● Watching'); self.scan_button.setText('RESCAN'); self.recovery_attempts=0; self.start_tracking(); self.analyze()
 def ai_failed(self,session,version,technical):
  if session!=self.tracking_session_id or version!=self.board_version:return
  logging.error('AI recognition failed: %s',technical)
  if self.recovery and self.recovery_attempts<2:
   self.recovery_attempts+=1; QTimer.singleShot(400,self.retry_recovery); return
  self.stop_tracking(); self.position.setText('POSITION\nTracking lost'); self.user_error('Could not recognize board.')
 def start_tracking(self):
  self.stop_tracking(); session=self.tracking_session_id; self.threshold=AdaptiveThreshold(); self.baseline_frames=6; self.stabilizer=Stabilizer(); self.last_capture=time.monotonic(); self.tracker=TrackingWorker(self.region,int(self.settings.value('tracking_interval',300))); self.tracker.frame.connect(lambda crop:self.tracking_frame(session,crop)); self.tracker.heartbeat.connect(lambda stamp:self.tracker_heartbeat(session,stamp)); self.tracker.failed.connect(lambda error:self.tracker_failed(session,error)); self.tracker.start()
 def stop_tracking(self):
  if self.tracker:self.tracker.stop(); self.tracker=None
 def retry_recovery(self):
  try:self.start_ai(self.current_frame(),True)
  except Exception:logging.exception('AI recovery capture failed'); self.tracking_lost()
 def current_frame(self):
  return ScreenCapture().grab(self.region)
 def tracking_frame(self,session,crop):
  if session!=self.tracking_session_id or self.previous is None:return
  signals=score_squares(self.previous,crop,self.orientation); numeric={sq:value['combined'] for sq,value in signals.items()}; threshold=self.threshold.value; observed={sq for sq,value in numeric.items() if value>=threshold}
  if self.baseline_frames>0 and (not numeric or max(numeric.values())<threshold):self.threshold.sample(signals); self.baseline_frames-=1; threshold=self.threshold.value
  if not observed:self.stabilizer.observe(crop,False); return
  self.status.setText('Move detected...')
  if not self.stabilizer.observe(crop,True):return
  if self.debug:Path('debug').mkdir(exist_ok=True); cv2.imwrite('debug/current_stable_frame.png',crop)
  self.last_stable=time.monotonic(); move,confidence,candidates=infer_move(self.board,observed)
  if not move:
   relaxed={sq for sq,value in numeric.items() if value>=max(.025,threshold*.62)}; move,confidence,candidates=infer_move(self.board,relaxed,True)
  if not move:move,confidence,candidates=infer_move_from_scores(self.board,numeric,threshold)
  visual_mapping={f'r{square_to_visual(s,self.orientation)[0]}c{square_to_visual(s,self.orientation)[1]}':chess.square_name(s) for s in observed}
  logging.info('Stable visual change session=%d version=%d orientation=%s threshold=%.4f visual_to_canonical=%s scores=%s fen=%s candidates=%s accepted=%s confidence=%.3f',session,self.board_version,self.orientation.name,threshold,visual_mapping,{chess.square_name(s):round(v,4) for s,v in numeric.items() if v>=threshold*.45},self.board.fen(),[(m.uci(),round(score,3)) for score,m,_ in candidates],move.uci() if move else None,confidence)
  if move:
   if move not in self.board.legal_moves:logging.warning('Rejected stale/illegal move=%s version=%d',move,self.board_version); return
   mover=self.board.turn; san=self.board.san(move); self.board.push(move); self.board_version+=1; self.last_move=time.monotonic(); self.previous=crop; self.stabilizer.reset(); self.view.set_board(self.board); move_text=('...'+san if mover==chess.BLACK else san); self.status.setText(('Opponent: ' if mover==self.opponent_color else 'Played: ')+move_text); self.position.setText('POSITION\n'+('● Your turn' if self.board.turn==self.user_color else '● Watching')); self.recovery_attempts=0
   logging.info('Accepted canonical move=%s render from=%s to=%s orientation=%s',move.uci(),square_to_visual(move.from_square,self.orientation),square_to_visual(move.to_square,self.orientation),self.orientation.name)
   if self.debug:Path('debug').mkdir(exist_ok=True); cv2.imwrite('debug/last_accepted_frame.png',crop)
   self.analyze()
  else:logging.warning('Change rejected: no candidate passed threshold'); self.recover(crop)
 def recover(self,crop):
  now=time.monotonic()
  if now-self.last_recovery<5:return
  if self.recovery_attempts>=2:self.tracking_lost(); return
  self.last_recovery=now; self.recovery_attempts+=1; self.status.setText('Resynchronizing...'); self.start_ai(crop,True)
 def tracking_lost(self): self.stop_tracking(); self.position.setText('POSITION\nTracking lost'); self.status.setText('Tracking lost'); self.scan_button.setText('RESCAN')
 def tracker_heartbeat(self,session,stamp):
  if session==self.tracking_session_id:self.last_capture=stamp
 def tracker_failed(self,session,error):
  if session!=self.tracking_session_id:return
  logging.error('Tracking worker failed session=%d error=%s',session,error); self.schedule_tracker_restart()
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
  if not self.tracker.isRunning() or time.monotonic()-self.last_capture>4:self.schedule_tracker_restart()
 def start_engine(self):
  if self.engine_worker:self.engine_worker.stop()
  self.engine_worker=EngineWorker(self.engine_path,float(self.settings.value('analysis_time',.6))); self.engine_worker.result.connect(self.analysis_done); self.engine_worker.error.connect(lambda version,error:logging.error('Stockfish version=%d error=%s',version,error)); self.engine_worker.start()
 def analyze(self):
  if self.board.turn!=self.user_color:
   self.view.arrow=None; self.view.update(); self.best.setText('BEST MOVE\nWaiting'); self.evaluation.setText('Evaluation —'); self.alts.setText(''); self.position.setText('POSITION\n● Watching'); self.status.setText('Waiting for opponent'); return
  self.position.setText('POSITION\n● Your turn')
  if not self.engine_path:self.status.setText('Your turn'); return
  if not self.engine_worker or not self.engine_worker.isRunning():self.start_engine()
  self.status.setText('Your turn — analyzing...'); self.engine_worker.submit(self.board.fen(),self.board_version)
 def analysis_done(self,version,rows):
  if version!=self.board_version or self.board.turn!=self.user_color or not rows:logging.info('Discarded stale/inapplicable Stockfish result version=%d current=%d user_turn=%s',version,self.board_version,self.board.turn==self.user_color); return
  san,uci,score,mate,_=rows[0]; self.best.setText(f'BEST MOVE\n{san}\n{uci[:2]} → {uci[2:4]}'); self.evaluation.setText('Evaluation '+(f'Mate {mate}' if mate is not None else f'{score/100:+.2f}')); self.alts.setText('Alternatives: '+', '.join(x[0] for x in rows[1:3])); self.view.arrow=(chess.parse_square(uci[:2]),chess.parse_square(uci[2:4])); self.view.update(); self.status.setText('Your turn')
 def open_settings(self):
  model,ok=QInputDialog.getText(self,'Settings','OpenAI model:',text=self.model)
  if ok and model.strip():self.model=normalize_model(model.strip()); self.openai_client=OpenAIClient(self.model); self.settings.setValue('ai_model',self.model)
  if not self.engine_path and QMessageBox.question(self,'Settings','Locate Stockfish now?')==QMessageBox.Yes:
   p=QFileDialog.getOpenFileName(self,'Locate Stockfish','','Executable (*.exe)')[0]
   if p:self.engine_path=p; self.settings.setValue('stockfish',p); self.start_engine()
 def user_error(self,text): self.status.setText(text); QMessageBox.warning(self,'Chess Vision Assistant',text)
 def crash_context(self):return {'fen':self.board.fen(),'tracking':bool(self.tracker and self.tracker.isRunning()),'region':self.region,'board_version':self.board_version,'session':self.tracking_session_id}
 def closeEvent(self,event):
  if self.ai_worker and self.ai_worker.isRunning() and not self._closing:
   self._closing=True; self.tracking_session_id+=1; self.stop_tracking(); self.status.setText('Finishing current scan before closing...'); self.ai_worker.finished.connect(self.close); event.ignore(); return
  self._closing=True; self.tracking_session_id+=1; self.watchdog.stop(); self.stop_tracking()
  if self.engine_worker:self.engine_worker.stop(); self.engine_worker=None
  super().closeEvent(event)
if __name__=='__main__':
 app=QApplication(sys.argv); window=MainWindow(); window.show(); sys.exit(app.exec())
