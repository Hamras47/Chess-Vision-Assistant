import cv2, numpy as np
try: import mss
except ImportError: mss=None

class ScreenCapture:
    def grab(self, region):
        if not mss: raise RuntimeError("Install mss to capture the screen")
        with mss.mss() as s: return np.array(s.grab(region))[:,:,:3]

class BoardVision:
    """Baseline pixel pipeline: selected region is the contract; recognition is pluggable."""
    def split(self, image):
        h,w=image.shape[:2]; side=min(h,w); x=(w-side)//2; y=(h-side)//2; image=image[y:y+side,x:x+side]
        return [image[r*side//8:(r+1)*side//8,c*side//8:(c+1)*side//8] for r in range(8) for c in range(8)]
    def changed_squares(self, old, new, threshold=12):
        a,b=self.split(old),self.split(new); return [i for i,(x,y) in enumerate(zip(a,b)) if np.mean(cv2.absdiff(x,y))>threshold]
