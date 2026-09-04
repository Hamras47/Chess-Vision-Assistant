import numpy as np
import mss
class ScreenCapture:
    def grab(self, region):
        with mss.mss() as s: return np.array(s.grab(region))[:, :, :3]
    def desktop(self):
        with mss.mss() as s:
            monitor=s.monitors[0]
            return np.array(s.grab(monitor))[:, :, :3], dict(left=monitor['left'],top=monitor['top'],width=monitor['width'],height=monitor['height'])
    def monitor_frames(self):
        with mss.mss() as s:
            return [(np.array(s.grab(m))[:, :, :3],dict(left=m['left'],top=m['top'],width=m['width'],height=m['height'])) for m in s.monitors[1:]]
