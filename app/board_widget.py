import chess
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtCore import Qt, Signal

UNICODE={"P":"♙","N":"♘","B":"♗","R":"♖","Q":"♕","K":"♔","p":"♟","n":"♞","b":"♝","r":"♜","q":"♛","k":"♚"}
class ChessBoardWidget(QWidget):
    move_made=Signal(str)
    def __init__(self): super().__init__(); self.board=chess.Board(); self.flipped=False; self.selected=None; self.arrow=None; self.setMinimumSize(420,420)
    def set_board(self,b): self.board=b.copy(); self.update()
    def sq_at(self,p):
        s=min(self.width(),self.height())//8; c=p.x()//s; r=p.y()//s
        if c>7 or r>7:return None
        return chess.square((7-c if self.flipped else c),(r if self.flipped else 7-r))
    def mousePressEvent(self,e):
        q=self.sq_at(e.position().toPoint());
        if q is None:return
        if self.selected is None: self.selected=q
        else:
            m=chess.Move(self.selected,q)
            if m in self.board.legal_moves: self.board.push(m); self.move_made.emit(m.uci()); self.arrow=(self.selected,q)
            self.selected=None; self.update()
    def paintEvent(self,e):
        p=QPainter(self); s=min(self.width(),self.height())//8; colors=[QColor('#e8d6b0'),QColor('#9b7354')]; p.setFont(QFont('Segoe UI Symbol', max(20,s//2)))
        for r in range(8):
          for c in range(8):
            sq=chess.square(7-c if self.flipped else c,r if self.flipped else 7-r); p.fillRect(c*s,r*s,s,s,colors[(r+c)%2])
            if sq==self.selected:p.fillRect(c*s,r*s,s,s,QColor(90,180,120,150))
            if sq in self.board.pieces(chess.PAWN,True) or any(sq in self.board.pieces(pt,col) for pt in range(1,6) for col in [True,False]):
                pc=self.board.piece_at(sq); p.setPen(QPen(QColor('#202020') if pc.color else QColor('#f7f1df'),2)); p.drawText(c*s,r*s,s,s,Qt.AlignCenter,UNICODE[pc.symbol()])
        p.setPen(QPen(QColor('#f0b84b'),5));
        if self.arrow:
          a,b=self.arrow
          def pos(q): return ((7-chess.square_file(q) if self.flipped else chess.square_file(q))*s+s//2,(chess.square_rank(q) if self.flipped else 7-chess.square_rank(q))*s+s//2)
          p.drawLine(*pos(a),*pos(b))
