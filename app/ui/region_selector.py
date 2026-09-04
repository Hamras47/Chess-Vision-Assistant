import cv2,logging
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt,QRect,Signal
from PySide6.QtGui import QPainter,QColor,QPen,QImage,QPixmap
from .dpi_coordinates import MonitorCoordinates

class RegionSelector(QWidget):
    selected=Signal(object); cancelled=Signal()
    def __init__(self,desktop,mapping:MonitorCoordinates):
        super().__init__(); self.origin=None; self.selection=QRect(); self.mapping=mapping; self.desktop=desktop
        rgb=cv2.cvtColor(desktop,cv2.COLOR_BGR2RGB); h,w=rgb.shape[:2]
        self.pixmap=QPixmap.fromImage(QImage(rgb.data,w,h,3*w,QImage.Format_RGB888).copy())
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool); self.setCursor(Qt.CrossCursor); self.setGeometry(mapping.logical)
        logging.debug('Snip monitor Qt logical=%s available DPR=%.2f MSS physical=%s capture=%dx%d',mapping.logical,mapping.dpr,mapping.physical,w,h)
    def mousePressEvent(self,e): self.origin=e.position().toPoint(); self.selection=QRect(self.origin,self.origin)
    def mouseMoveEvent(self,e): self.selection=QRect(self.origin,e.position().toPoint()).normalized(); self.update()
    def mouseReleaseEvent(self,e):
        r=self.selection
        if r.width()>80 and r.height()>80:
            physical=self.mapping.selection_to_physical(r)
            logical={'left':self.mapping.logical.x()+r.x(),'top':self.mapping.logical.y()+r.y(),'width':r.width(),'height':r.height()}
            logging.debug('Snip selection logical=%s physical=%s',logical,physical)
            sx=self.desktop.shape[1]/self.width(); sy=self.desktop.shape[0]/self.height(); x=round(r.x()*sx); y=round(r.y()*sy); w=round(r.width()*sx); h=round(r.height()*sy)
            self.selected.emit({'logical':logical,'physical':physical,'frozen_image':self.desktop[y:y+h,x:x+w].copy()})
        else:self.cancelled.emit()
    def keyPressEvent(self,e):
        if e.key()==Qt.Key_Escape:self.cancelled.emit()
    def paintEvent(self,e):
        p=QPainter(self)
        # The physical-pixel pixmap is explicitly fitted to this monitor's logical geometry.
        p.drawPixmap(self.rect(),self.pixmap,self.pixmap.rect()); p.fillRect(self.rect(),QColor(0,0,0,115))
        if not self.selection.isNull():
            sx=self.pixmap.width()/self.width(); sy=self.pixmap.height()/self.height()
            source=QRect(round(self.selection.x()*sx),round(self.selection.y()*sy),round(self.selection.width()*sx),round(self.selection.height()*sy))
            p.drawPixmap(self.selection,self.pixmap,source); p.setPen(QPen(QColor('#f2b84b'),3)); p.drawRect(self.selection)
