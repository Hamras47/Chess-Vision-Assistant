import time
from PySide6.QtCore import QThread,Signal
from .capture import ScreenCapture
class TrackingWorker(QThread):
 frame=Signal(object); failed=Signal(str); heartbeat=Signal(float)
 def __init__(self,region,interval_ms=300): super().__init__(); self.region=region; self.interval=interval_ms; self.running=True
 def run(self):
  cap=ScreenCapture(); failures=0
  while self.running:
   try:
    self.frame.emit(cap.grab(self.region)); self.heartbeat.emit(time.monotonic()); failures=0
   except Exception as e:
    failures+=1
    if failures>=3:self.failed.emit(str(e)); return
    self.msleep(min(1000,200*failures)); continue
   self.msleep(self.interval)
 def stop(self): self.running=False; self.wait(1200)
