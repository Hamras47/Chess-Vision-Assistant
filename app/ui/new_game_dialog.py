"""Compact setup for analysis, local play and a native Stockfish opponent."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QHBoxLayout,
                             QLabel, QPushButton, QSlider, QVBoxLayout, QWidget, QLineEdit, QFormLayout)

from app.chess.game_mode import GameMode, GameOptions


class NewGameDialog(QDialog):
    def __init__(self, parent=None, options=None):
        super().__init__(parent)
        options = options or GameOptions()
        self.setWindowTitle("New Game")
        self.setFixedWidth(470)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 16, 22, 16)
        layout.setSpacing(8)
        title = QLabel("New Game")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        layout.addWidget(self.heading("MODE"))
        self.modes = self.choices(layout, [m.value for m in GameMode], options.mode.value)
        self.names = QWidget()
        names = QFormLayout(self.names)
        names.setContentsMargins(0, 0, 0, 0)
        names.setSpacing(6)
        self.white_name = QLineEdit(options.white_name)
        self.black_name = QLineEdit(options.black_name)
        self.human_name = QLineEdit(options.human_name)
        self.white_name.setPlaceholderText("White")
        self.black_name.setPlaceholderText("Black")
        self.human_name.setPlaceholderText("Player")
        for field in (self.white_name, self.black_name, self.human_name):
            field.setMaxLength(32)
        names.addRow("White Player", self.white_name)
        names.addRow("Black Player", self.black_name)
        names.addRow("Your Name", self.human_name)
        self.names_form = names
        layout.addWidget(self.names)
        self.computer = QWidget()
        computer = QVBoxLayout(self.computer)
        computer.setContentsMargins(0, 0, 0, 0)
        computer.setSpacing(5)
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
        self.elo.setRange(600, 2800)
        self.elo.setSingleStep(50)
        self.elo.setPageStep(100)
        self.elo.setValue(options.elo)
        self.elo.valueChanged.connect(self.update_rating)
        computer.addWidget(self.elo)
        note = QLabel("ChessAI · Approximate strength, not a rated Elo.")
        note.setToolTip("Below native Elo limits, ChessAI selects among evaluated Stockfish candidates. Higher strengths use native limiting.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        computer.addWidget(note)
        layout.addWidget(self.computer)
        self.time_controls = QWidget()
        times = QVBoxLayout(self.time_controls)
        times.setContentsMargins(0, 0, 0, 0)
        times.setSpacing(5)
        times.addWidget(self.heading("TIME CONTROL"))
        self.times = self.choices(times, ["1 min", "5 min", "10 min", "20 min"], f"{options.minutes} min")
        layout.addWidget(self.time_controls)
        self.tools = QWidget()
        tools = QVBoxLayout(self.tools)
        tools.setContentsMargins(0, 0, 0, 0)
        tools.setSpacing(5)
        tools.addWidget(self.heading("LEARNING TOOLS"))
        self.evaluation = self.toggle(tools, "Evaluation Bar", options.evaluation)
        self.suggestions = self.toggle(tools, "Best Move Suggestions", options.suggestions)
        tools.addWidget(self.heading("GAME CONTROLS"))
        self.history = self.toggle(tools, "Allow Undo / Redo", options.allow_history)
        self.history.setToolTip("Changes board history only; elapsed clock time is not restored.")
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
        labels = [(600, "Beginner"), (1100, "Casual"), (1400, "Intermediate"),
                  (1700, "Club"), (2000, "Advanced"), (2300, "Expert"), (2600, "Master")]
        self.category.setText(next(label for threshold, label in reversed(labels) if value >= threshold))

    def update_mode(self):
        mode = GameMode(self.modes.checkedButton().text())
        self.computer.setVisible(mode == GameMode.VS_COMPUTER)
        self.tools.setVisible(mode != GameMode.ANALYSIS)
        self.names.setVisible(mode != GameMode.ANALYSIS)
        self.names_form.setRowVisible(self.white_name, mode == GameMode.LOCAL_PVP)
        self.names_form.setRowVisible(self.black_name, mode == GameMode.LOCAL_PVP)
        self.names_form.setRowVisible(self.human_name, mode == GameMode.VS_COMPUTER)
        self.time_controls.setVisible(mode != GameMode.ANALYSIS)
        self.analysis_note.setVisible(mode == GameMode.ANALYSIS)
        self.layout().activate()
        self.adjustSize()

    def values(self):
        return GameOptions(GameMode(self.modes.checkedButton().text()),
                           self.colors.checkedButton().text(), self.elo.value(),
                           self.evaluation.isChecked(), self.suggestions.isChecked(), self.history.isChecked(),
                           int(self.times.checkedButton().text().split()[0]),
                           self.white_name.text().strip(), self.black_name.text().strip(), self.human_name.text().strip())
