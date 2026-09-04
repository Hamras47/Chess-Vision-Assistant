import cv2,numpy as np
from .grid import split
from app.chess.coordinates import visual_index_to_square
def square_signals(a,b):
    ga=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY); gb=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY); h,w=ga.shape; my=max(2,int(h*.12)); mx=max(2,int(w*.12)); ca=ga[my:h-my,mx:w-mx]; cb=gb[my:h-my,mx:w-mx]
    texture=min(1.,(float(np.std(ca))+float(np.std(cb)))/40); grayscale=float(np.mean(cv2.absdiff(ga,gb))/255)*texture; center=float(np.mean(cv2.absdiff(ca,cb))/255)*texture; edge=float(np.mean(cv2.absdiff(cv2.Canny(ca,40,110),cv2.Canny(cb,40,110)))/255); na=cv2.normalize(ca,None,0,255,cv2.NORM_MINMAX); nb=cv2.normalize(cb,None,0,255,cv2.NORM_MINMAX); normalized=float(np.mean(cv2.absdiff(na,nb))/255); silhouette=float(min(1,np.mean(np.abs(cv2.Laplacian(ca,cv2.CV_16S)-cv2.Laplacian(cb,cv2.CV_16S)))/255))
    return {'grayscale':grayscale,'center':center,'edge':edge,'silhouette':silhouette,'normalized':normalized,'combined':.06*grayscale+.18*center+.30*edge+.24*normalized+.22*silhouette}
def square_difference(a,b):return square_signals(a,b)['combined']
def score_squares(previous,current,orientation):return {visual_index_to_square(i,orientation):square_signals(a,b) for i,(a,b) in enumerate(zip(split(previous),split(current)))}
def changed_squares(previous,current,orientation,threshold=.075):return [(sq,v['combined']) for sq,v in score_squares(previous,current,orientation).items() if v['combined']>=threshold]
class AdaptiveThreshold:
    def __init__(self,minimum=.040,maximum=.135,margin=.025):self.minimum=minimum; self.maximum=maximum; self.margin=margin; self.noise=[]
    def sample(self,signals):self.noise=(self.noise+[v['combined'] for v in signals.values()])[-320:]
    @property
    def value(self):return .065 if not self.noise else float(np.clip(np.percentile(self.noise,99)+self.margin,self.minimum,self.maximum))
