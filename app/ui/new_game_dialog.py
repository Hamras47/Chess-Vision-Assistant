"""Compact setup for analysis, local play and a native Stockfish opponent."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QHBoxLayout,
                             QLabel, QPushButton, QSlider, QVBoxLayout, QWidget)

from app.chess.game_mode import GameMode, GameOptions


class NewGameDialog(QDialog):
    def __init__(self, parent=None, options=None):
        super().__init__(parent)
        options = options or GameOptions()
        self.setWindowTitle("New Game")
        self.setFixedWidth(470)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        title = QLabel("New Game")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        layout.addWidget(self.heading("MODE"))
        self.modes = self.choices(layout, [m.value for m in GameMode], options.mode.value)
        self.computer = QWidget()
        computer = QVBoxLayout(self.computer)
        computer.setContentsMargins(0, 0, 0, 0)
        computer.setSpacing(10)
        computer.addWidget(self.heading("PLAY AS"))
        self.colors = self.choices(computer, ["White", "Black", "Random"], options.color)
        computer.addWidget(self.heading("COMPUTER STRENGTH"))
        self.rating = QLabel()
        self.rating.setObjectName("eloValue")
        self.category = QLabel()
        self.category.setObjectName("muted")
        computer.addWidget(self.rating)
        computer.addWidget(self.category)
        self.elo = QSlider(Qt.Horizontal)
        self.elo.setRange(800, 2800)
        self.elo.setSingleStep(50)
        self.elo.setPageStep(100)
        self.elo.setValue(options.elo)
        self.elo.valueChanged.connect(self.update_rating)
        computer.addWidget(self.elo)
        note = QLabel("Uses your engine’s supported Elo range. Lower selections may be clamped to its minimum.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        computer.addWidget(note)
        layout.addWidget(self.computer)
        self.tools = QWidget()
        tools = QVBoxLayout(self.tools)
        tools.setContentsMargins(0, 0, 0, 0)
        tools.setSpacing(10)
        tools.addWidget(self.heading("LEARNING TOOLS"))
        self.evaluation = self.toggle(tools, "Evaluation Bar", options.evaluation)
        self.suggestions = self.toggle(tools, "Best Move Suggestions", options.suggestions)
        tools.addWidget(self.heading("GAME CONTROLS"))
        self.history = self.toggle(tools, "Allow Undo / Redo", options.allow_history)
        layout.addWidget(self.tools)
        self.analysis_note = QLabel("Explore both colors, scan positions and use your existing analysis preferences.")
        self.analysis_note.setWordWrap(True)
        self.analysis_note.setObjectName("muted")
        layout.addWidget(self.analysis_note)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        start = QPushButton("Start Game")
        start.setObjectName("primaryButton")
        start.setDefault(True)
        start.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(start)
        layout.addLayout(buttons)
        self.modes.buttonClicked.connect(self.update_mode)
        self.update_rating()
        self.update_mode()

    @staticmethod
    def heading(text):
        label = QLabel(text)
        label.setObjectName("dialogEyebrow")
        return label

    def choices(self, layout, labels, selected):
        group = QButtonGroup(self)
        row = QHBoxLayout()
        row.setSpacing(5)
        for text in labels:
            button = QPushButton(text)
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setChecked(text == selected)
            group.addButton(button)
            row.addWidget(button)
        layout.addLayout(row)
        return group

    @staticmethod
    def toggle(layout, text, checked):
        row = QHBoxLayout()
        row.addWidget(QLabel(text))
        row.addStretch()
        toggle = QCheckBox("On" if checked else "Off")
        toggle.setAccessibleName(text)
        toggle.setChecked(checked)
        toggle.toggled.connect(lambda enabled: toggle.setText("On" if enabled else "Off"))
        row.addWidget(toggle)
        layout.addLayout(row)
        return toggle

    def update_rating(self):
        value = self.elo.value()
        self.rating.setText(f"ELO {value}")
        labels = [(800, "Beginner"), (1100, "Casual"), (1400, "Intermediate"),
                  (1700, "Club"), (2000, "Advanced"), (2300, "Expert"), (2600, "Master")]
        self.category.setText(next(label for threshold, label in reversed(labels) if value >= threshold))

    def update_mode(self):
        mode = GameMode(self.modes.checkedButton().text())
        self.computer.setVisible(mode == GameMode.VS_COMPUTER)
        self.tools.setVisible(mode != GameMode.ANALYSIS)
        self.analysis_note.setVisible(mode == GameMode.ANALYSIS)
        self.layout().activate()
        self.adjustSize()

    def values(self):
        return GameOptions(GameMode(self.modes.checkedButton().text()),
                           self.colors.checkedButton().text(), self.elo.value(),
                           self.evaluation.isChecked(), self.suggestions.isChecked(), self.history.isChecked())
