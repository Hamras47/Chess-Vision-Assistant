import chess, chess.engine, os
from PySide6.QtCore import QThread, Signal

class AnalysisWorker(QThread):
    result = Signal(object); error = Signal(str)
    def __init__(self, fen, path, time=0.6, depth=18, multipv=3):
        super().__init__(); self.fen,self.path,self.time,self.depth,self.multipv=fen,path,time,depth,multipv
    def run(self):
        try:
            if not self.path or not os.path.exists(self.path): raise FileNotFoundError("Stockfish executable is not configured")
            b=chess.Board(self.fen); e=chess.engine.SimpleEngine.popen_uci(self.path)
            infos=e.analyse(b, chess.engine.Limit(time=self.time, depth=self.depth), multipv=self.multipv); e.quit()
            rows=[]
            for i in infos:
                score=i["score"].pov(b.turn); rows.append((b.san(i["pv"][0]), i["pv"][0].uci(), score.score(mate_score=100000), score.mate(), i.get("depth",0)))
            self.result.emit(rows)
        except Exception as ex: self.error.emit(str(ex))
