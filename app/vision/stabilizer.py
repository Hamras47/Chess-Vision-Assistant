import time, numpy as np
class Stabilizer:
    def __init__(self, delay_ms=300): self.delay=delay_ms/1000; self.pending=None; self.last=None
    def observe(self, frame, changed):
        now=time.monotonic()
        if not changed: self.pending=None; self.last=frame; return False
        if self.pending is None: self.pending=now; self.last=frame; return False
        stable=float(np.mean(np.abs(frame.astype(float)-self.last.astype(float))))<2.5; self.last=frame
        return stable and now-self.pending>=self.delay
