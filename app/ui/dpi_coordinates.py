from dataclasses import dataclass
from PySide6.QtCore import QRect

@dataclass(frozen=True)
class MonitorCoordinates:
    logical: QRect
    physical: dict
    dpr: float

    @property
    def scale_x(self): return self.physical['width']/self.logical.width()
    @property
    def scale_y(self): return self.physical['height']/self.logical.height()

    def selection_to_physical(self, local: QRect):
        return {
            'left': self.physical['left']+round(local.x()*self.scale_x),
            'top': self.physical['top']+round(local.y()*self.scale_y),
            'width': round(local.width()*self.scale_x),
            'height': round(local.height()*self.scale_y),
        }

def match_monitor(screen, physical_monitors):
    g=screen.geometry(); dpr=float(screen.devicePixelRatio())
    def score(m):
        return abs(m['left']-g.x())+abs(m['top']-g.y())+abs(m['width']-round(g.width()*dpr))+abs(m['height']-round(g.height()*dpr))
    monitor=min(physical_monitors,key=score)
    return MonitorCoordinates(QRect(g),monitor,dpr)
