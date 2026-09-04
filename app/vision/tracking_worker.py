import time
from PySide6.QtCore import QThread,Signal
from .capture import ScreenCapture
class TrackingWorker(QThread):
 frame=Signal(object); failed=Signal(str)
 def __init__(self,region,interval_ms=300): super().__init__(); self.region=region; self.interval=interval_ms; self.running=True
 def run(self):
  cap=ScreenCapture()
  while self.running:
   try:
    self.frame.emit(cap.grab(self.region))
   except Exception as e:self.failed.emit(str(e)); return
   self.msleep(self.interval)
 def stop(self): self.running=False; self.wait(1200)
