import time,numpy as np
class Stabilizer:
    def __init__(self,delay_ms=220,required_frames=2,tolerance=2.8):self.delay=delay_ms/1000; self.required=required_frames; self.tolerance=tolerance; self.reset()
    def reset(self):self.started=None; self.latest=None; self.stable_count=0; self.state='STABLE'
    def observe(self,frame,changed):
        now=time.monotonic()
        if not changed:self.latest=frame; return False
        if self.started is None:self.started=now; self.latest=frame; self.state='CHANGE_DETECTED'; return False
        delta=float(np.mean(np.abs(frame.astype(np.float32)-self.latest.astype(np.float32)))); self.latest=frame
        if delta<=self.tolerance:self.stable_count+=1; self.state='STABILIZING'
        else:self.stable_count=0; self.state='ANIMATING'
        if self.stable_count>=self.required and now-self.started>=self.delay:self.state='NEW_STABLE_POSITION'; return True
        return False
