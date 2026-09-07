"""Compact right-hand analysis panel."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class AnalysisPanel(QFrame):
    undo_requested = Signal()
    redo_requested = Signal()
    scan_requested = Signal()
    new_game_requested = Signal()
    best_move_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("analysisCard")
        self.setMinimumWidth(280)
        self.setMaximumWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 20)
        layout.setSpacing(8)

        layout.addWidget(self._eyebrow("POSITION"))
        self.owner_label = QLabel("Ready")
        self.owner_label.setObjectName("positionOwner")
        self.turn_label = QLabel("White to move")
        self.turn_label.setObjectName("muted")
        self.state_label = QLabel("")
        self.state_label.setObjectName("stateLabel")
        layout.addWidget(self.owner_label)
        layout.addWidget(self.turn_label)
        layout.addWidget(self.state_label)

        layout.addSpacing(16)
        layout.addWidget(self._eyebrow("BEST MOVE"))
        self.best_button = QPushButton("—")
        self.best_button.setObjectName("bestMove")
        self.best_button.setEnabled(False)
        self.best_button.clicked.connect(self.best_move_clicked)
        self.uci_label = QLabel("")
        self.uci_label.setObjectName("moveCoordinates")
        self.evaluation_label = QLabel("Evaluation —")
        self.evaluation_label.setObjectName("evaluation")
        layout.addWidget(self.best_button)
        layout.addWidget(self.uci_label)
        layout.addWidget(self.evaluation_label)

        layout.addSpacing(14)
        layout.addWidget(self._eyebrow("ALTERNATIVES"))
        self.alternative_labels = [QLabel("—"), QLabel("—")]
        for label in self.alternative_labels:
            label.setObjectName("alternative")
            layout.addWidget(label)

        layout.addSpacing(14)
        layout.addWidget(self._eyebrow("MOVE HISTORY"))
        self.history_label = QLabel("No moves yet")
        self.history_label.setObjectName("history")
        self.history_label.setWordWrap(True)
        self.history_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        scroll = QScrollArea()
        scroll.setObjectName("historyScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self.history_label)
        scroll.setMinimumHeight(90)
        layout.addWidget(scroll, 1)

        edit_row = QHBoxLayout()
        self.undo_button = self._button("Undo", self.undo_requested)
        self.redo_button = self._button("Redo", self.redo_requested)
        edit_row.addWidget(self.undo_button)
        edit_row.addWidget(self.redo_button)
        layout.addLayout(edit_row)

        grid = QGridLayout()
        self.scan_button = self._button("Scan Board", self.scan_requested, "primaryButton")
        self.new_button = self._button("New Game", self.new_game_requested)
        grid.addWidget(self.scan_button, 0, 0)
        grid.addWidget(self.new_button, 0, 1)
        layout.addLayout(grid)
        self.set_history("")
        self.set_undo_redo(False, False)

    @staticmethod
    def _eyebrow(text):
        label = QLabel(text)
        label.setObjectName("eyebrow")
        return label

    @staticmethod
    def _button(text, signal, object_name="secondaryButton"):
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.clicked.connect(lambda checked=False: signal.emit())
        return button

    def set_position(self, owner: str, turn: str, state: str = ""):
        self.owner_label.setText(owner)
        self.turn_label.setText(turn)
        self.state_label.setText(state)
        self.state_label.setVisible(bool(state))

    def clear_analysis(self):
        self.best_button.setText("—")
        self.best_button.setEnabled(False)
        self.uci_label.clear()
        self.evaluation_label.setText("Evaluation —")
        for label in self.alternative_labels:
            label.setText("—")

    def set_analyzing(self):
        self.clear_analysis()
        self.best_button.setText("Analyzing…")

    def set_unavailable(self):
        self.clear_analysis()
        self.best_button.setText("Not configured")

    def set_analysis(self, rows):
        if not rows:
            self.clear_analysis()
            return
        san, uci, score, mate, _ = rows[0]
        self.best_button.setText(san)
        self.best_button.setEnabled(True)
        self.uci_label.setText(f"{uci[:2]}  →  {uci[2:4]}")
        self.evaluation_label.setText(
            f"Mate {mate:+d}" if mate is not None else f"Evaluation {score / 100:+.2f}"
        )
        alternatives = rows[1:3]
        for index, label in enumerate(self.alternative_labels):
            label.setText(f"{index + 1}.  {alternatives[index][0]}" if index < len(alternatives) else "—")

    def set_history(self, text: str):
        self.history_label.setText(text or "No moves yet")

    def set_undo_redo(self, can_undo: bool, can_redo: bool):
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)

    def set_scan_mode(self, has_imported_position: bool):
        self.scan_button.setText("Rescan" if has_imported_position else "Scan Board")
