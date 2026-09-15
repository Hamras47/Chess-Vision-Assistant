"""White-perspective evaluation, attached to the board rather than the sidebar."""
import math

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget


def white_fraction(centipawns=0, mate=None):
    # Logistic-style tanh: 0cp = 50%; +/-400cp ~= 88%/12%.
    # Finite scores never fill the bar completely; only forced mates do.
    if mate is not None:
        return 1.0 if mate > 0 else 0.0
    return 0.5 + 0.49 * math.tanh(centipawns / 400.0)


def evaluation_text(centipawns=0, mate=None):
    if mate is not None:
        return f"{'-' if mate < 0 else ''}M{abs(mate)}"
    return f"{centipawns / 100:+.1f}" if centipawns else "0.0"


class EvaluationBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fraction = 0.5
        self.target_fraction = 0.5
        self.active = False
        self.flipped = False
        self.text = "--"
        self.setAccessibleName("Position evaluation, White perspective")
        self.setToolTip("Positive favors White · Negative favors Black")
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(180)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.valueChanged.connect(self._changed)

    def _changed(self, value):
        self.fraction = float(value)
        self.update()

    def set_evaluation(self, centipawns=0, mate=None):
        self.active = True
        self.text = evaluation_text(centipawns, mate)
        self.target_fraction = white_fraction(centipawns, mate)
        self.animation.stop()
        self.animation.setStartValue(self.fraction)
        self.animation.setEndValue(self.target_fraction)
        self.animation.start()
        self.setAccessibleDescription(f"White perspective: {self.text}")
        self.update()

    def set_inactive(self):
        self.animation.stop()
        self.active = False
        self.text = "--"
        self.fraction = self.target_fraction = 0.5
        self.setAccessibleDescription("Evaluation inactive")
        self.update()

    def set_flipped(self, flipped):
        self.flipped = bool(flipped)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(rect, 6, 6)
        painter.setClipPath(clip)
        painter.fillRect(rect, QColor("#30383d"))
        white_height = rect.height() * self.fraction
        white_y = 0 if self.flipped else rect.height() - white_height
        painter.fillRect(QRectF(0, white_y, rect.width(), white_height), QColor("#edece5"))
        if not self.active:
            painter.fillRect(rect, QColor(36, 44, 47, 130))
        # Numeric readout stays at the end with the larger region for contrast.
        white_label = self.fraction >= 0.5
        top_label = self.flipped if white_label else not self.flipped
        painter.setPen(QColor("#30383d") if white_label and self.active else QColor("#e1e5e3"))
        font = QFont("Segoe UI", 8)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect.adjusted(0, 7, 0, -7), Qt.AlignHCenter | (Qt.AlignTop if top_label else Qt.AlignBottom), self.text)
