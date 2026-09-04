from dataclasses import dataclass
from pathlib import Path
import cv2, numpy as np, chess
from .grid import split
from app.chess.coordinates import visual_index_to_square,as_orientation

@dataclass
class PiecePrediction: piece: str|None; confidence: float

class TemplateClassifier:
    def __init__(self, path): self.path=Path(path); self.templates={}; self.load()
    def load(self):
        if self.path.exists():
            data=np.load(self.path,allow_pickle=True); self.templates={k:data[k] for k in data.files}
    def calibrated(self): return bool(self.templates)
    def calibrate_start(self, crop, orientation):
        board=chess.Board(); templates={}; orientation=as_orientation(orientation)
        for i,img in enumerate(split(crop)):
            sq=visual_index_to_square(i,orientation); pc=board.piece_at(sq); key=pc.symbol() if pc else 'empty_' + ('light' if (i//8+i%8)%2==0 else 'dark')
            templates[key]=cv2.resize(img,(48,48),interpolation=cv2.INTER_AREA)
        self.templates=templates; self.path.parent.mkdir(parents=True,exist_ok=True); np.savez_compressed(self.path,**templates)
    def classify(self,img,index):
        if not self.templates:return PiecePrediction(None,0)
        a=cv2.resize(img,(48,48),interpolation=cv2.INTER_AREA).astype(np.float32)
        scores=[]
        for key,t in self.templates.items(): scores.append((float(np.mean(np.abs(a-t.astype(np.float32)))),key))
        scores.sort(); dist,key=scores[0]; conf=max(0.,1-dist/80)
        return PiecePrediction(None if key.startswith('empty') else key,conf)
    def recognize(self,crop,orientation,turn):
        board=chess.Board(None); conf=[]; orientation=as_orientation(orientation)
        for i,img in enumerate(split(crop)):
            p=self.classify(img,i); conf.append(p.confidence)
            if p.piece: board.set_piece_at(visual_index_to_square(i,orientation),chess.Piece.from_symbol(p.piece))
        board.turn=turn; return board,float(np.mean(conf)),conf
