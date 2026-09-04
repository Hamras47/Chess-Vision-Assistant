import cv2, numpy as np
from .grid import split
from app.chess.coordinates import visual_index_to_square
def square_difference(a,b):
    """Edge-weighted metric suppresses flat highlight/background color changes."""
    ga=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY); gb=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY)
    ea=cv2.Canny(ga,45,110); eb=cv2.Canny(gb,45,110)
    h,w=ga.shape; margin=max(2,int(min(h,w)*.12)); center=np.zeros_like(ga); center[margin:h-margin,margin:w-margin]=1
    edges=np.mean(cv2.absdiff(ea,eb)[center==1])/255
    texture=np.mean(cv2.absdiff(cv2.Laplacian(ga,cv2.CV_16S),cv2.Laplacian(gb,cv2.CV_16S))[center==1])/255
    return float(.8*edges+.2*min(texture,1))
def changed_squares(previous,current,white_bottom,threshold=.075):
    scored=[]
    for i,(a,b) in enumerate(zip(split(previous),split(current))):
        score=square_difference(a,b)
        if score>=threshold:scored.append((visual_index_to_square(i,white_bottom),score))
    return scored
