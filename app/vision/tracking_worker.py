import time
from PySide6.QtCore import QThread,Signal
from .capture import ScreenCapture
class TrackingWorker(QThread):
 frame=Signal(object); failed=Signal(str); heartbeat=Signal(float); metrics=Signal(float,float,int)
 def __init__(self,region,interval_ms=125): super().__init__(); self.region=region; self.interval=interval_ms; self.running=True
 def run(self):
  cap=ScreenCapture(); failures=0; started=time.monotonic(); captures=0; capture_seconds=0.
  while self.running:
   try:
    before=time.monotonic(); image=cap.grab(self.region); after=time.monotonic(); captures+=1; capture_seconds+=after-before; self.frame.emit(image); self.heartbeat.emit(after); failures=0
    if after-started>=5:self.metrics.emit(captures/(after-started),1000*capture_seconds/captures,captures); started=after; captures=0; capture_seconds=0.
   except Exception as e:
    failures+=1
    if failures>=3:self.failed.emit(str(e)); return
    self.msleep(min(1000,200*failures)); continue
   self.msleep(max(1,self.interval-round((after-before)*1000)))
 def stop(self): self.running=False; self.wait(1200)
