"""Accessible promotion picker using the installed SVG piece set."""
from pathlib import Path

import chess
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NAMES = {
    chess.QUEEN: "queen",
    chess.ROOK: "rook",
    chess.BISHOP: "bishop",
    chess.KNIGHT: "knight",
}


class PromotionDialog(QDialog):
    def __init__(self, color: chess.Color, parent=None):
        super().__init__(parent)
        self.choice = None
        self.setWindowTitle("Choose promotion")
        self.setModal(True)
        self.setObjectName("promotionDialog")
        outer = QVBoxLayout(self)
        title = QLabel("Promote pawn to")
        title.setObjectName("dialogTitle")
        outer.addWidget(title)
        row = QHBoxLayout()
        color_name = "white" if color else "black"
        queen_button = None
        for piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
            button = QPushButton(NAMES[piece_type].title())
            button.setIcon(QIcon(str(PROJECT_ROOT / "assets" / "pieces" / f"{color_name}_{NAMES[piece_type]}.svg")))
            button.setIconSize(QSize(44, 44))
            button.clicked.connect(lambda checked=False, value=piece_type: self._choose(value))
            row.addWidget(button)
            if piece_type == chess.QUEEN:
                queen_button = button
        outer.addLayout(row)
        if queen_button:
            queen_button.setDefault(True)
            queen_button.setFocus()

    def _choose(self, piece_type):
        self.choice = piece_type
        self.accept()

    @classmethod
    def choose(cls, color: chess.Color, parent=None):
        dialog = cls(color, parent)
        return dialog.choice if dialog.exec() == QDialog.Accepted else None
