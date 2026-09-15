"""Minimal, reflowing analysis companion."""
from __future__ import annotations

import chess
from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QSizePolicy


class AnalysisPanel(QFrame):
    # Undo/redo remain keyboard-only; signals preserve the existing behavior API.
    undo_requested = Signal()
    redo_requested = Signal()
    scan_requested = Signal()
    new_game_requested = Signal()
    best_move_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("analysisCard")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._compact = False
        self.playing_label = QLabel("Playing: White")
        self.playing_label.setObjectName("playing")
        self.turn_label = QLabel("White to move")
        self.turn_label.setObjectName("muted")
        self.turn_label.setWordWrap(True)
        self.state_label = QLabel("")
        self.state_label.setObjectName("stateLabel")
        self.state_label.setWordWrap(True)
        self.best_heading = QLabel("BEST MOVE")
        self.best_heading.setObjectName("eyebrow")
        self.best_button = QPushButton("—")
        self.best_button.setObjectName("bestMove")
        self.best_button.setEnabled(False)
        self.best_button.clicked.connect(self.best_move_clicked)
        self.uci_label = QLabel("")
        self.uci_label.setObjectName("moveCoordinates")
        self.evaluation_label = QLabel("Evaluation —")
        self.evaluation_label.setObjectName("evaluation")
        self.scan_button = self._button("Scan Board", self.scan_requested, "primaryButton")
        self.new_button = self._button("New Game", self.new_game_requested)
        self.layout_grid = QGridLayout(self)
        self.set_compact(False)

    @staticmethod
    def _button(text, signal, object_name="secondaryButton"):
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.clicked.connect(lambda checked=False: signal.emit())
        return button

    @property
    def compact(self):
        return self._compact

    def _clear_layout(self):
        while self.layout_grid.count():
            self.layout_grid.takeAt(0)
        for row in range(10):
            self.layout_grid.setRowStretch(row, 0)
        for column in range(5):
            self.layout_grid.setColumnStretch(column, 0)

    def set_compact(self, compact: bool):
        self._compact = compact
        self._clear_layout()
        if compact:
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.setMinimumHeight(105)
            self.setMaximumHeight(128)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.layout_grid.setContentsMargins(14, 10, 14, 10)
            self.layout_grid.setHorizontalSpacing(10)
            self.layout_grid.setVerticalSpacing(2)
            self.layout_grid.addWidget(self.playing_label, 0, 0)
            self.layout_grid.addWidget(self.turn_label, 0, 1, 1, 3)
            self.layout_grid.addWidget(self.best_heading, 1, 0)
            self.layout_grid.addWidget(self.best_button, 1, 1)
            self.layout_grid.addWidget(self.uci_label, 1, 2)
            self.layout_grid.addWidget(self.evaluation_label, 1, 3)
            self.layout_grid.addWidget(self.state_label, 2, 0, 1, 2)
            self.layout_grid.addWidget(self.scan_button, 2, 2)
            self.layout_grid.addWidget(self.new_button, 2, 3)
            self.layout_grid.setColumnStretch(1, 1)
        else:
            self.setMinimumWidth(175)
            self.setMaximumWidth(205)
            self.setMinimumHeight(0)
            self.setMaximumHeight(280)
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.layout_grid.setContentsMargins(14, 16, 14, 14)
            self.layout_grid.setHorizontalSpacing(6)
            self.layout_grid.setVerticalSpacing(4)
            self.layout_grid.addWidget(self.playing_label, 0, 0, 1, 2)
            self.layout_grid.addWidget(self.turn_label, 1, 0, 1, 2)
            self.layout_grid.addWidget(self.state_label, 2, 0, 1, 2)
            self.layout_grid.addWidget(self.best_heading, 4, 0, 1, 2)
            self.layout_grid.addWidget(self.best_button, 5, 0, 1, 2)
            self.layout_grid.addWidget(self.uci_label, 6, 0, 1, 2)
            self.layout_grid.addWidget(self.evaluation_label, 7, 0, 1, 2)
            self.layout_grid.addWidget(self.scan_button, 8, 0, 1, 2)
            self.layout_grid.addWidget(self.new_button, 9, 0, 1, 2)

    def sizeHint(self):
        return QSize(390, 112) if self._compact else QSize(205, 205)

    def minimumSizeHint(self):
        return QSize(360, 105) if self._compact else QSize(175, 180)

    def wide_width_hint(self):
        return 205

    def set_player(self, color: chess.Color):
        self.playing_label.setText("Playing: White" if color else "Playing: Black")

    def set_position(self, owner: str, turn: str, state: str = ""):
        self.turn_label.setText(turn)
        self.turn_label.setToolTip(f"{owner} · {turn}" if owner and owner != "Ready" else turn)
        self.state_label.setText(state)
        self.state_label.setVisible(bool(state))

    def clear_analysis(self):
        self.best_button.setText("—")
        self.best_button.setEnabled(False)
        self.uci_label.clear()
        self.evaluation_label.setText("Evaluation —")

    def set_analyzing(self):
        self.clear_analysis()
        self.best_button.setText("Analyzing…")

    def set_unavailable(self):
        self.clear_analysis()
        self.best_button.setText("Unavailable")

    def set_off(self):
        self.clear_analysis()
        self.best_button.setText("Off")
        self.evaluation_label.setText("Suggestions off")

    def set_analysis(self, rows):
        if not rows:
            self.clear_analysis()
            return
        san, uci, score, mate, _ = rows[0]
        self.best_button.setText(san)
        self.best_button.setEnabled(True)
        self.uci_label.setText(f"{uci[:2]}  →  {uci[2:4]}")
        self.evaluation_label.setText(
            f"{'-' if mate < 0 else ''}M{abs(mate)}" if mate is not None else f"{score / 100:+.2f}"
        )

    # History and undo/redo remain available in game state and shortcuts, not primary UI.
    def set_history(self, text: str):
        return None

    def set_undo_redo(self, can_undo: bool, can_redo: bool):
        return None

    def set_scan_mode(self, has_imported_position: bool):
        self.scan_button.setText("Rescan" if has_imported_position else "Scan Board")
