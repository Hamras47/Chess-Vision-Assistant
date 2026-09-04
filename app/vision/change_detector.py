import cv2,numpy as np
from .grid import split
from app.chess.coordinates import visual_index_to_square
def square_signals(a,b):
    ga=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY); gb=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY); h,w=ga.shape; my=max(2,int(h*.12)); mx=max(2,int(w*.12)); ca=ga[my:h-my,mx:w-mx]; cb=gb[my:h-my,mx:w-mx]
    edge=float(np.mean(cv2.absdiff(cv2.Canny(ca,40,110),cv2.Canny(cb,40,110)))/255); centered_a=ca.astype(np.float32)-float(np.median(ca)); centered_b=cb.astype(np.float32)-float(np.median(cb)); center=float(np.mean(np.abs(centered_a-centered_b))/255); na=cv2.normalize(ca,None,0,255,cv2.NORM_MINMAX); nb=cv2.normalize(cb,None,0,255,cv2.NORM_MINMAX); normalized=float(np.mean(cv2.absdiff(na,nb))/255); silhouette=float(min(1,np.mean(np.abs(cv2.Laplacian(ca,cv2.CV_16S)-cv2.Laplacian(cb,cv2.CV_16S)))/255))
    return {'edge':edge,'center':center,'normalized':normalized,'silhouette':silhouette,'combined':.38*edge+.20*center+.22*normalized+.20*silhouette}
def square_difference(a,b):return square_signals(a,b)['combined']
def score_squares(previous,current,white_bottom):return {visual_index_to_square(i,white_bottom):square_signals(a,b) for i,(a,b) in enumerate(zip(split(previous),split(current)))}
def changed_squares(previous,current,white_bottom,threshold=.075):return [(sq,v['combined']) for sq,v in score_squares(previous,current,white_bottom).items() if v['combined']>=threshold]
class AdaptiveThreshold:
    def __init__(self,minimum=.040,maximum=.135,margin=.025):self.minimum=minimum; self.maximum=maximum; self.margin=margin; self.noise=[]
    def sample(self,signals):self.noise=(self.noise+[v['combined'] for v in signals.values()])[-320:]
    @property
    def value(self):return .065 if not self.noise else float(np.clip(np.percentile(self.noise,99)+self.margin,self.minimum,self.maximum))
