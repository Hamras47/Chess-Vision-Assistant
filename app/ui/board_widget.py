"""Premium interactive chessboard backed by python-chess."""
from __future__ import annotations

import math
from pathlib import Path

import chess
from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPolygonF
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.chess.coordinates import Orientation, square_to_visual, visual_to_square

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}


class ChessBoardWidget(QWidget):
    move_requested = Signal(int, int)
    animation_completed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.board = chess.Board()
        self.orientation = Orientation.WHITE_BOTTOM
        self.arrow: tuple[int, int] | None = None
        self.selected: int | None = None
        self.legal_targets: dict[int, bool] = {}
        self.last_move: chess.Move | None = None
        self._pressed_square: int | None = None
        self._press_position = QPointF()
        self._dragging = False
        self._drag_position = QPointF()
        self._invalid_square: int | None = None
        self._piece_cache: dict[tuple, QImage] = {}
        self._animation: QVariantAnimation | None = None
        self._animated_move: chess.Move | None = None
        self._animated_piece: chess.Piece | None = None
        self._animation_progress = 1.0
        self._animation_before = None
        self._moving_pieces = []
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def heightForWidth(self, width):
        return width

    def set_board(self, board: chess.Board, last_move: chess.Move | None = None):
        self._stop_animation()
        self.board = board
        self.last_move = last_move
        self.clear_selection()
        self.update()

    def animate_move(self, before: chess.Board, move: chess.Move, after: chess.Board, duration=210):
        self._stop_animation()
        self.board = after
        self.last_move = move
        self.arrow = None
        self.clear_selection()
        self._animated_move = move
        self._animated_piece = before.piece_at(move.from_square)
        self._animation_before = before.copy(stack=False)
        self._moving_pieces = [(move.from_square, move.to_square, self._animated_piece)]
        if before.is_castling(move):
            rank = chess.square_rank(move.from_square)
            kingside = move.to_square > move.from_square
            source = chess.square(7 if kingside else 0, rank)
            target = chess.square(5 if kingside else 3, rank)
            self._moving_pieces.append((source, target, before.piece_at(source)))
        self._animation_progress = 0.0
        animation = QVariantAnimation(self)
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.valueChanged.connect(self._animation_value)
        animation.finished.connect(self._animation_finished)
        self._animation = animation
        animation.start()

    def _stop_animation(self):
        # Rapid undo/redo must not leave an old animation hiding a new piece.
        if self._animation is not None:
            self._animation.stop()
            self._animation.deleteLater()
            self._animation = None
        self._animation_finished()

    def _animation_value(self, value):
        self._animation_progress = float(value)
        self.update()

    def _animation_finished(self):
        was_animating = self._animated_move is not None
        self._animation_progress = 1.0
        self._animated_move = None
        self._animated_piece = None
        self._animation_before = None
        self._moving_pieces = []
        self.update()
        if was_animating:
            self.animation_completed.emit()

    def resizeEvent(self, event):
        self._stop_animation()
        super().resizeEvent(event)

    def set_orientation(self, orientation: Orientation):
        self._stop_animation()
        self.orientation = Orientation(orientation)
        self.clear_selection()
        self.update()

    def flip(self):
        self.set_orientation(
            Orientation.BLACK_BOTTOM
            if self.orientation == Orientation.WHITE_BOTTOM
            else Orientation.WHITE_BOTTOM
        )

    @property
    def flipped(self):
        return self.orientation == Orientation.BLACK_BOTTOM

    def piece_map(self):
        return self.board.piece_map()

    def _layout(self):
        side = min(self.width(), self.height()) - 8
        square = side / 8
        return (self.width() - side) / 2, (self.height() - side) / 2, square

    def _square_at(self, position: QPointF) -> int | None:
        ox, oy, size = self._layout()
        col = int((position.x() - ox) / size)
        row = int((position.y() - oy) / size)
        if not 0 <= row < 8 or not 0 <= col < 8:
            return None
        return visual_to_square(row, col, self.orientation)

    def _rect_for(self, square: int) -> QRectF:
        ox, oy, size = self._layout()
        row, col = square_to_visual(square, self.orientation)
        return QRectF(ox + col * size, oy + row * size, size, size)

    def clear_selection(self):
        self.selected = None
        self.legal_targets = {}
        self._dragging = False
        self.update()

    def select_square(self, square: int) -> bool:
        piece = self.board.piece_at(square)
        moves = [move for move in self.board.legal_moves if move.from_square == square]
        if piece is None or piece.color != self.board.turn or not moves:
            self._invalid_feedback(square)
            return False
        self.selected = square
        self.legal_targets = {
            move.to_square: self.board.is_capture(move)
            for move in moves
        }
        self.update()
        return True

    def activate_square(self, square: int) -> bool:
        """Apply click-click interaction; returns whether a move was requested."""
        if self.selected is None:
            self.select_square(square)
            return False
        if square == self.selected:
            self.clear_selection()
            return False
        if square in self.legal_targets:
            source = self.selected
            self.clear_selection()
            self.move_requested.emit(source, square)
            return True
        piece = self.board.piece_at(square)
        if piece and piece.color == self.board.turn:
            self.select_square(square)
        else:
            self._invalid_feedback(square)
            self.clear_selection()
        return False

    def _invalid_feedback(self, square: int | None):
        self._invalid_square = square
        self.update()
        QTimer.singleShot(140, self._clear_invalid)

    def _clear_invalid(self):
        self._invalid_square = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._pressed_square = self._square_at(event.position())
        self._press_position = event.position()
        self._drag_position = event.position()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._pressed_square is None or not event.buttons() & Qt.LeftButton:
            return
        if (event.position() - self._press_position).manhattanLength() > 7:
            if self.selected != self._pressed_square and not self.select_square(self._pressed_square):
                return
            self._dragging = True
            self._drag_position = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        target = self._square_at(event.position())
        source = self._pressed_square
        was_dragging = self._dragging
        self._pressed_square = None
        self._dragging = False
        if source is None or target is None:
            self.clear_selection()
            return
        if was_dragging:
            if self.selected == source and target in self.legal_targets:
                self.clear_selection()
                self.move_requested.emit(source, target)
            elif target != source:
                self._invalid_feedback(target)
                self.clear_selection()
            self.update()
            return
        self.activate_square(target)

    def _piece_image(self, piece: chess.Piece, pixels: int, dpr: float) -> QImage:
        key = (piece.symbol(), pixels, round(dpr, 2))
        if key in self._piece_cache:
            return self._piece_cache[key]
        color = "white" if piece.color else "black"
        path = PROJECT_ROOT / "assets" / "pieces" / f"{color}_{PIECE_NAMES[piece.piece_type]}.svg"
        physical = max(1, round(pixels * dpr))
        image = QImage(physical, physical, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        image.setDevicePixelRatio(dpr)
        painter = QPainter(image)
        QSvgRenderer(str(path)).render(painter, QRectF(0, 0, pixels, pixels))
        painter.end()
        if len(self._piece_cache) > 96:
            self._piece_cache.clear()
        self._piece_cache[key] = image
        return image

    def _draw_piece(self, painter: QPainter, piece: chess.Piece, rect: QRectF, size: float):
        extent = size * 0.82
        margin = (size - extent) / 2
        image = self._piece_image(piece, round(extent), self.devicePixelRatioF())
        painter.drawImage(QRectF(rect.x() + margin, rect.y() + margin, extent, extent), image)

    def _draw_arrow(self, painter: QPainter, size: float):
        if not self.arrow:
            return
        start = self._rect_for(self.arrow[0]).center()
        end = self._rect_for(self.arrow[1]).center()
        color = QColor(67, 153, 126, 210)
        painter.setPen(QPen(color, max(5, size * 0.09), Qt.SolidLine, Qt.RoundCap))
        direction = end - start
        length = math.hypot(direction.x(), direction.y())
        if length:
            end = end - direction / length * size * 0.18
        painter.drawLine(start, end)
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        wing = size * 0.24
        points = QPolygonF([
            end,
            QPointF(end.x() - wing * math.cos(angle - 0.55), end.y() - wing * math.sin(angle - 0.55)),
            QPointF(end.x() - wing * math.cos(angle + 0.55), end.y() - wing * math.sin(angle + 0.55)),
        ])
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPolygon(points)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        ox, oy, size = self._layout()
        light, dark = QColor(216, 212, 197, 242), QColor(111, 136, 116, 242)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 75))
        painter.drawRoundedRect(QRectF(ox - 4, oy - 4, size * 8 + 8, size * 8 + 8), 8, 8)
        last = set()
        if self.last_move:
            last = {self.last_move.from_square, self.last_move.to_square}
        check_square = self.board.king(self.board.turn) if self.board.is_check() else None

        for row in range(8):
            for col in range(8):
                square = visual_to_square(row, col, self.orientation)
                rect = QRectF(ox + col * size, oy + row * size, size, size)
                base = light if (row + col) % 2 == 0 else dark
                painter.fillRect(rect, base)
                if square in last:
                    painter.fillRect(rect, QColor(231, 193, 86, 88))
                if square == self.selected:
                    painter.fillRect(rect, QColor(66, 145, 123, 112))
                if square == check_square:
                    painter.fillRect(rect, QColor(185, 65, 69, 125))
                if square == self._invalid_square:
                    painter.fillRect(rect, QColor(210, 78, 78, 95))
                if square in self.legal_targets:
                    painter.setPen(QPen(QColor(25, 42, 35, 115), max(2, size * 0.035)))
                    if self.legal_targets[square]:
                        painter.setBrush(Qt.NoBrush)
                        painter.drawEllipse(rect.center(), size * 0.37, size * 0.37)
                    else:
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(QColor(25, 42, 35, 105))
                        painter.drawEllipse(rect.center(), size * 0.11, size * 0.11)

                rendered = self._animation_before if self._animation_before is not None else self.board
                piece = rendered.piece_at(square)
                hide_for_drag = self._dragging and square == self.selected
                hide_for_animation = any(source == square for source, _, _ in self._moving_pieces)
                if piece and not hide_for_drag and not hide_for_animation:
                    self._draw_piece(painter, piece, rect, size)

                font = QFont("Segoe UI", max(7, round(size * 0.115)), QFont.DemiBold)
                painter.setFont(font)
                painter.setPen(QColor("#53645a") if base == light else QColor("#d7ddd6"))
                if col == 0:
                    painter.drawText(rect.adjusted(4, 2, -2, -2), Qt.AlignLeft | Qt.AlignTop, str(chess.square_rank(square) + 1))
                if row == 7:
                    painter.drawText(rect.adjusted(2, 2, -5, -3), Qt.AlignRight | Qt.AlignBottom, chess.FILE_NAMES[chess.square_file(square)])

        self._draw_arrow(painter, size)

        if self._moving_pieces:
            for source_square, target_square, piece in self._moving_pieces:
                source = self._rect_for(source_square)
                target = self._rect_for(target_square)
                point = source.topLeft() + (target.topLeft() - source.topLeft()) * self._animation_progress
                self._draw_piece(painter, piece, QRectF(point.x(), point.y(), size, size), size)
        elif self._dragging and self.selected is not None:
            piece = self.board.piece_at(self.selected)
            if piece:
                self._draw_piece(
                    painter,
                    piece,
                    QRectF(self._drag_position.x() - size / 2, self._drag_position.y() - size / 2, size, size),
                    size,
                )


class SquareBoardHost(QWidget):
    """Keep the actual board widget square and centered at every host size."""

    def __init__(self, board: ChessBoardWidget, parent=None, evaluation_bar=None):
        super().__init__(parent)
        self.board = board
        self.board.setParent(self)
        self.evaluation_bar = evaluation_bar
        self.player_bars = None
        if evaluation_bar is not None:
            evaluation_bar.setParent(self)
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def resizeEvent(self, event):
        self.arrange_board()
        super().resizeEvent(event)

    def arrange_board(self):
        gutter = 40 if self.evaluation_bar is not None and not self.evaluation_bar.isHidden() else 0
        bars = self.player_bars is not None and not self.player_bars[0].isHidden()
        side = max(0, min(self.width() - gutter, self.height() - (64 if bars else 0)))
        left = (self.width() - side - gutter) // 2 + gutter
        top = (self.height() - side) // 2
        self.board.setGeometry(left, top, side, side)
        if self.evaluation_bar is not None:
            self.evaluation_bar.setGeometry(left - gutter + 4, top + 4, 30, max(0, side - 8))
        if bars:
            self.player_bars[0].setGeometry(left + 4, top - 30, side - 8, 28)
            self.player_bars[1].setGeometry(left + 4, top + side + 2, side - 8, 28)
