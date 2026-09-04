import sys,os,time,logging,shutil,chess,cv2,numpy as np
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QFileDialog,QMessageBox,QInputDialog
from PySide6.QtCore import Qt,QSettings,QTimer
from .board_widget import ChessBoardWidget
from .engine import AnalysisWorker
from .vision.capture import ScreenCapture
from .vision.grid import board_crop
from .vision.change_detector import changed_squares
from .vision.stabilizer import Stabilizer
from .vision.tracking_worker import TrackingWorker
from .ui.region_selector import RegionSelector
from .ui.dpi_coordinates import match_monitor
from .ai.board_recognizer import RecognitionWorker
from .ai.openai_client import OpenAIClient,normalize_model
from .chess.move_tracker import infer_move

class MainWindow(QMainWindow):
 def __init__(self):
  super().__init__(); self.settings=QSettings('ChessVisionAssistant','ChessVisionAssistant'); Path('logs').mkdir(exist_ok=True); self.debug=self.settings.value('debug_mode',False,type=bool) or os.getenv('CHESS_VISION_DEBUG')=='1'; logging.basicConfig(filename='logs/chess_vision.log',level=logging.DEBUG if self.debug else logging.INFO)
  requested_model=self.settings.value('ai_model',os.getenv('OPENAI_VISION_MODEL','gpt-5.2')); self.model=normalize_model(requested_model); self.engine_path=self.find_engine(); self.board=chess.Board(); self.region=None; self.previous=None; self.tracker=None; self.ai_worker=None; self.engine_worker=None; self.stabilizer=Stabilizer(); self.last_recovery=0.; self.recovery_attempts=0; self.recovery=False
  if requested_model!=self.model:self.settings.setValue('ai_model',self.model)
  self.setWindowTitle('Chess Vision Assistant'); self.resize(850,570); self.setWindowFlag(Qt.WindowStaysOnTopHint,True)
  root=QWidget(); self.setCentralWidget(root); outer=QVBoxLayout(root); header=QHBoxLayout(); title=QLabel('Chess Vision Assistant'); title.setObjectName('title'); gear=QPushButton('⚙'); gear.setFixedWidth(42); gear.clicked.connect(self.open_settings); header.addWidget(title); header.addStretch(); header.addWidget(gear); outer.addLayout(header)
  body=QHBoxLayout(); self.view=ChessBoardWidget(); body.addWidget(self.view,1); side=QVBoxLayout(); self.position=QLabel('POSITION\nReady'); self.best=QLabel('BEST MOVE\n—'); self.evaluation=QLabel('Evaluation —'); self.alts=QLabel(''); self.scan_button=QPushButton('SCAN BOARD'); self.scan_button.clicked.connect(self.scan_board); side.addWidget(self.position); side.addSpacing(18); side.addWidget(self.best); side.addWidget(self.evaluation); side.addWidget(self.alts); side.addStretch(); side.addWidget(self.scan_button); body.addLayout(side); outer.addLayout(body,1); self.status=QLabel('Ready'); outer.addWidget(self.status)
  self.setStyleSheet("QMainWindow{background:#171a1f} QLabel{color:#e9edf1;font-size:15px;padding:5px} QLabel#title{font-size:20px;font-weight:600} QPushButton{background:#303640;color:white;padding:11px;border:1px solid #48505c;border-radius:6px} QPushButton:hover{background:#3a424e}")
  if not self.engine_path: self.status.setText('Stockfish needs to be configured. Open Settings.')
 def find_engine(self):
  stored=self.settings.value('stockfish','')
  if stored and Path(stored).exists():return stored
  found=shutil.which('stockfish')
  if found:return found
  for p in Path('.').glob('**/stockfish*.exe'):
   if '.venv' not in p.parts:return str(p.resolve())
  return ''
 def scan_board(self):
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
  if not OpenAIClient(self.model).ready():self.user_error('OpenAI is not configured. Add the API key to .env.'); return
  self.recovery=recovery; self.ai_worker=RecognitionWorker(crop,self.model,self.debug); self.ai_worker.result.connect(lambda b,r,l:self.ai_done(b,r,l,crop)); self.ai_worker.error.connect(self.ai_failed); self.ai_worker.start()
 def ai_done(self,board,result,latency,crop):
  if result.side_to_move=='unknown':
   answer=QMessageBox.question(self,'Side to move','Is White to move?',QMessageBox.Yes|QMessageBox.No); board.turn=answer==QMessageBox.Yes
  self.board=board; self.previous=crop; self.view.flipped=result.orientation=='black_bottom'; self.view.set_board(self.board); self.status.setText('Board synchronized'); self.position.setText('POSITION\n● Watching'); self.scan_button.setText('RESCAN'); self.recovery_attempts=0; self.start_tracking(); self.analyze()
 def ai_failed(self,technical):
  logging.error('AI recognition failed: %s',technical)
  if self.recovery and self.recovery_attempts<2:
   self.recovery_attempts+=1; QTimer.singleShot(400,lambda:self.start_ai(self.current_frame(),True)); return
  self.stop_tracking(); self.position.setText('POSITION\nTracking lost'); self.user_error('Could not recognize board.')
 def start_tracking(self):
  self.stop_tracking(); self.tracker=TrackingWorker(self.region,int(self.settings.value('tracking_interval',300))); self.tracker.frame.connect(self.tracking_frame); self.tracker.failed.connect(lambda _:self.tracking_lost()); self.tracker.start()
 def stop_tracking(self):
  if self.tracker:self.tracker.stop(); self.tracker=None
 def current_frame(self):
  return ScreenCapture().grab(self.region)
 def tracking_frame(self,crop):
  if self.previous is None:return
  scored=changed_squares(self.previous,crop,not self.view.flipped); observed={x[0] for x in scored}
  if not observed:self.stabilizer.observe(crop,False); return
  self.status.setText('Move detected...')
  if not self.stabilizer.observe(crop,True):return
  move,confidence,_=infer_move(self.board,observed)
  if move:
   san=self.board.san(move); self.board.push(move); self.previous=crop; self.stabilizer=Stabilizer(); self.view.set_board(self.board); self.status.setText('Opponent moved: '+san); self.position.setText('POSITION\n● Watching'); self.recovery_attempts=0; self.analyze()
  else:self.recover(crop)
 def recover(self,crop):
  now=time.monotonic()
  if now-self.last_recovery<5:return
  if self.recovery_attempts>=2:self.tracking_lost(); return
  self.last_recovery=now; self.recovery_attempts+=1; self.status.setText('Resynchronizing...'); self.start_ai(crop,True)
 def tracking_lost(self): self.stop_tracking(); self.position.setText('POSITION\nTracking lost'); self.status.setText('Tracking lost'); self.scan_button.setText('RESCAN')
 def analyze(self):
  if not self.engine_path:return
  fen=self.board.fen(); self.status.setText('Analyzing...'); self.engine_worker=AnalysisWorker(fen,self.engine_path); self.engine_worker.result.connect(lambda rows:self.analysis_done(fen,rows)); self.engine_worker.error.connect(lambda e:logging.error('Stockfish: %s',e)); self.engine_worker.start()
 def analysis_done(self,fen,rows):
  if fen!=self.board.fen() or not rows:return
  san,uci,score,mate,_=rows[0]; self.best.setText(f'BEST MOVE\n{san}\n{uci[:2]} → {uci[2:4]}'); self.evaluation.setText('Evaluation '+(f'Mate {mate}' if mate is not None else f'{score/100:+.2f}')); self.alts.setText('Alternatives: '+', '.join(x[0] for x in rows[1:3])); self.view.arrow=(chess.parse_square(uci[:2]),chess.parse_square(uci[2:4])); self.view.update(); self.status.setText('Watching board')
 def open_settings(self):
  model,ok=QInputDialog.getText(self,'Settings','OpenAI model:',text=self.model)
  if ok and model.strip():self.model=model.strip(); self.settings.setValue('ai_model',self.model)
  if not self.engine_path and QMessageBox.question(self,'Settings','Locate Stockfish now?')==QMessageBox.Yes:
   p=QFileDialog.getOpenFileName(self,'Locate Stockfish','','Executable (*.exe)')[0]
   if p:self.engine_path=p; self.settings.setValue('stockfish',p)
 def user_error(self,text): self.status.setText(text); QMessageBox.warning(self,'Chess Vision Assistant',text)
 def closeEvent(self,e): self.stop_tracking(); super().closeEvent(e)
if __name__=='__main__':
 app=QApplication(sys.argv); window=MainWindow(); window.show(); sys.exit(app.exec())
