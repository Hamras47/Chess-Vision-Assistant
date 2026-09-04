import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import chess
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from app.main import MainWindow

def test_successful_ai_scan_starts_tracking(monkeypatch):
 app=QApplication.instance() or QApplication([]); w=MainWindow(); calls=[]
 monkeypatch.setattr(w,'start_tracking',lambda:calls.append('tracking')); monkeypatch.setattr(w,'analyze',lambda:calls.append('analysis'))
 result=SimpleNamespace(side_to_move='white',orientation='white_bottom',confidence=.98,warnings=[])
 w.ai_done(chess.Board(),result,.1,object())
 assert calls==['tracking','analysis']; assert w.scan_button.text()=='RESCAN'; w.close()
