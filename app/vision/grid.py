import cv2, numpy as np

def board_crop(image):
    """Find a near-square region whose 64 cells exhibit alternating grid structure."""
    h,w=image.shape[:2]; side=min(h,w); best=(-1,0,0,side)
    for scale in np.linspace(.78,1.0,9):
        s=int(side*scale); room_x=w-s; room_y=h-s
        xs=sorted(set(int(room_x*t) for t in (0,.25,.5,.75,1)))
        ys=sorted(set(int(room_y*t) for t in (0,.25,.5,.75,1)))
        for ox in xs:
          for oy in ys:
            crop=image[oy:oy+s,ox:ox+s]
            med=np.array([np.median(c.reshape(-1,3),axis=0) for c in split(crop)]).reshape(8,8,3)
            neighbor=np.mean(np.abs(med[:,1:].astype(float)-med[:,:-1]))+np.mean(np.abs(med[1:].astype(float)-med[:-1]))
            consistency=np.std(med[::2,::2],axis=(0,1)).mean()+np.std(med[1::2,1::2],axis=(0,1)).mean()
            score=float(neighbor-.15*consistency)
            if score>best[0]: best=(score,ox,oy,s)
    _,x,y,s=best; return image[y:y+s,x:x+s],(x,y,s,s)

def split(image):
    h,w=image.shape[:2]; return [image[r*h//8:(r+1)*h//8,c*w//8:(c+1)*w//8] for r in range(8) for c in range(8)]

def draw_grid(image):
    out=image.copy(); h,w=out.shape[:2]
    for i in range(9): cv2.line(out,(i*w//8,0),(i*w//8,h),(0,0,255),1); cv2.line(out,(0,i*h//8),(w,i*h//8),(0,0,255),1)
    return out
