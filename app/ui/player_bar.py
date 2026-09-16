"""Compact player information using the board's existing SVG image cache."""
import math
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtWidgets import QWidget


class PlayerBar(QWidget):
    def __init__(self, board_view, parent):
        super().__init__(parent)
        self.board_view = board_view
        self.name = ""
        self.captures = ()
        self.remaining_ms = 0
        self.active = False

    def set_player(self, name, captures, remaining_ms, active):
        self.name, self.captures = name, tuple(captures)
        self.remaining_ms, self.active = remaining_ms, active
        self.setToolTip(name)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.remaining_ms is not None:
            seconds = max(0, math.ceil(self.remaining_ms / 1000))
            clock = f"{seconds // 60:02d}:{seconds % 60:02d}"
            clock_rect = QRectF(self.width() - 74, 0, 74, self.height())
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#42574e") if self.active else QColor("#2b3538"))
            painter.drawRoundedRect(clock_rect, 6, 6)
            painter.setFont(QFont("Consolas", 12, QFont.DemiBold))
            painter.setPen(QColor("#edbb83") if seconds < 10 else QColor("#edf2ee"))
            painter.drawText(clock_rect, Qt.AlignCenter, clock)
        available = max(0, self.width() - (86 if self.remaining_ms is not None else 12))
        icon_width = min(20, max(8, (available - min(90, available / 2)) / max(1, len(self.captures))))
        name_width = max(0, available - len(self.captures) * icon_width - 6)
        painter.setFont(QFont("Segoe UI", 10, QFont.DemiBold if self.active else QFont.Normal))
        painter.setPen(QColor("#e5ece7") if self.active else QColor("#a8b6ae"))
        painter.drawText(QRectF(0, 0, name_width, self.height()), Qt.AlignVCenter,
                         painter.fontMetrics().elidedText(self.name, Qt.ElideRight, int(name_width)))
        for i, piece in enumerate(self.captures):
            image = self.board_view._piece_image(piece, 20, self.devicePixelRatioF())
            painter.drawImage(QRectF(name_width + 6 + i * icon_width, 4, 20, 20), image)
