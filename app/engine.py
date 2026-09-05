import os,threading,chess,chess.engine
from PySide6.QtCore import QThread,Signal
def parse_analysis(board,infos):
    rows=[]
    for info in infos:
        score=info['score'].pov(board.turn); move=info['pv'][0]; rows.append((board.san(move),move.uci(),score.score(mate_score=100000),score.mate(),info.get('depth',0)))
    return rows
class EngineWorker(QThread):
    result=Signal(int,int,object); error=Signal(int,int,str)
    def __init__(self,path,analysis_time=.6,depth=18,multipv=3):
        super().__init__(); self.path=path; self.analysis_time=analysis_time; self.depth=depth; self.multipv=multipv; self._condition=threading.Condition(); self._pending=None; self._running=True
    def submit(self,fen,session,version):
        with self._condition:self._pending=(fen,session,version); self._condition.notify()
    def run(self):
        engine=None
        try:
            if not self.path or not os.path.exists(self.path):raise FileNotFoundError('Stockfish executable is not configured')
            engine=chess.engine.SimpleEngine.popen_uci(self.path)
            while self._running:
                with self._condition:
                    while self._pending is None and self._running:self._condition.wait(.5)
                    if not self._running:break
                    fen,session,version=self._pending; self._pending=None
                try:
                    board=chess.Board(fen); infos=engine.analyse(board,chess.engine.Limit(time=self.analysis_time,depth=self.depth),multipv=self.multipv); self.result.emit(session,version,parse_analysis(board,infos))
                except Exception as e:self.error.emit(session,version,str(e))
        except Exception as e:self.error.emit(-1,-1,str(e))
        finally:
            if engine:
                try:engine.quit()
                except Exception:pass
    def stop(self):
        with self._condition:self._running=False; self._condition.notify_all()
        self.wait(3000)
class AnalysisWorker(QThread):
    result=Signal(object); error=Signal(str)
    def __init__(self,fen,path,time=.6,depth=18,multipv=3):super().__init__(); self.fen=fen; self.path=path; self.time=time; self.depth=depth; self.multipv=multipv
    def run(self):
        engine=None
        try:
            engine=chess.engine.SimpleEngine.popen_uci(self.path); board=chess.Board(self.fen); self.result.emit(parse_analysis(board,engine.analyse(board,chess.engine.Limit(time=self.time,depth=self.depth),multipv=self.multipv)))
        except Exception as e:self.error.emit(str(e))
        finally:
            if engine:
                try:engine.quit()
                except Exception:pass
