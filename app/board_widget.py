from pathlib import Path
import math,chess
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter,QColor,QFont,QPen,QBrush,QImage,QPolygonF
from PySide6.QtCore import Qt,Signal,QRectF,QPointF
from PySide6.QtSvg import QSvgRenderer

NAMES={chess.PAWN:'pawn',chess.KNIGHT:'knight',chess.BISHOP:'bishop',chess.ROOK:'rook',chess.QUEEN:'queen',chess.KING:'king'}
class ChessBoardWidget(QWidget):
    move_made=Signal(str)
    def __init__(self):
        super().__init__(); self.board=chess.Board(); self.flipped=False; self.arrow=None; self.selected=None; self._piece_cache={}; self.setMinimumSize(420,420)
    def set_board(self,board):self.board=board; self.update()
    def piece_map(self):return self.board.piece_map()
    def _layout(self):
        side=min(self.width(),self.height()); square=side/8; return (self.width()-side)/2,(self.height()-side)/2,square
    def _visual_square(self,row,col):return chess.square(7-col if self.flipped else col,row if self.flipped else 7-row)
    def _rect_for(self,square):
        ox,oy,size=self._layout(); file=chess.square_file(square); rank=chess.square_rank(square); col=7-file if self.flipped else file; row=rank if self.flipped else 7-rank; return QRectF(ox+col*size,oy+row*size,size,size)
    def _piece_image(self,piece,pixels,dpr):
        key=(piece.symbol(),pixels,round(dpr,2))
        if key in self._piece_cache:return self._piece_cache[key]
        color='white' if piece.color else 'black'; path=Path('assets/pieces')/f'{color}_{NAMES[piece.piece_type]}.svg'; renderer=QSvgRenderer(str(path)); physical=max(1,round(pixels*dpr)); image=QImage(physical,physical,QImage.Format_ARGB32_Premultiplied); image.fill(Qt.transparent); image.setDevicePixelRatio(dpr); painter=QPainter(image); renderer.render(painter,QRectF(0,0,pixels,pixels)); painter.end()
        if len(self._piece_cache)>=72:self._piece_cache.clear()
        self._piece_cache[key]=image; return image
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.Antialiasing); ox,oy,size=self._layout(); light=QColor('#d7d4cb'); dark=QColor('#667b68'); last=set()
        if self.board.move_stack:
            move=self.board.peek(); last={move.from_square,move.to_square}
        suggested=set(self.arrow or ())
        for row in range(8):
            for col in range(8):
                square=self._visual_square(row,col); rect=QRectF(ox+col*size,oy+row*size,size,size); base=light if (row+col)%2==0 else dark; painter.fillRect(rect,base)
                if square in last:painter.fillRect(rect,QColor(236,196,73,62))
                if square in suggested:painter.fillRect(rect,QColor(75,174,238,72))
                piece=self.board.piece_at(square)
                if piece:
                    extent=size*.86; margin=(size-extent)/2; image=self._piece_image(piece,round(extent),self.devicePixelRatioF()); painter.drawImage(QRectF(rect.x()+margin,rect.y()+margin,extent,extent),image)
                if col==0:
                    painter.setFont(QFont('Segoe UI',max(7,round(size*.12)),QFont.DemiBold)); painter.setPen(QColor('#566157') if base==light else QColor('#d8ddd5')); rank=chess.square_rank(square)+1; painter.drawText(rect.adjusted(3,2,-2,-2),Qt.AlignLeft|Qt.AlignTop,str(rank))
                if row==7:
                    painter.setFont(QFont('Segoe UI',max(7,round(size*.12)),QFont.DemiBold)); painter.setPen(QColor('#566157') if base==light else QColor('#d8ddd5')); file=chr(ord('a')+chess.square_file(square)); painter.drawText(rect.adjusted(2,2,-4,-2),Qt.AlignRight|Qt.AlignBottom,file)
        if self.arrow:
            start=self._rect_for(self.arrow[0]).center(); end=self._rect_for(self.arrow[1]).center(); painter.setPen(QPen(QColor(43,135,210,195),max(5,size*.09),Qt.SolidLine,Qt.RoundCap)); painter.drawLine(start,end); angle=math.atan2(end.y()-start.y(),end.x()-start.x()); wing=size*.22; points=QPolygonF([end,QPointF(end.x()-wing*math.cos(angle-.55),end.y()-wing*math.sin(angle-.55)),QPointF(end.x()-wing*math.cos(angle+.55),end.y()-wing*math.sin(angle+.55))]); painter.setBrush(QBrush(QColor(43,135,210,215))); painter.setPen(Qt.NoPen); painter.drawPolygon(points)
