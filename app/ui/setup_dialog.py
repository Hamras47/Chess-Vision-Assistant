"""Human-friendly player-color and side-to-move setup."""
import chess
from PySide6.QtWidgets import QButtonGroup, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class PositionSetupDialog(QDialog):
    def __init__(self, parent=None, ask_turn=True, initial_color=chess.WHITE):
        super().__init__(parent)
        self.setWindowTitle("Position setup")
        self.setModal(True)
        self.player_color = initial_color
        self.my_turn = True
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 26, 28, 24)
        outer.setSpacing(12)
        title = QLabel("You are playing")
        title.setObjectName("dialogEyebrow")
        outer.addWidget(title)
        color_row = QHBoxLayout()
        self.color_group = QButtonGroup(self)
        self.white = self._choice("White", chess.WHITE, self.color_group)
        self.black = self._choice("Black", chess.BLACK, self.color_group)
        color_row.addWidget(self.white)
        color_row.addWidget(self.black)
        outer.addLayout(color_row)
        (self.white if initial_color else self.black).setChecked(True)

        self.turn_group = None
        if ask_turn:
            turn_title = QLabel("Whose turn")
            turn_title.setObjectName("dialogEyebrow")
            outer.addSpacing(8)
            outer.addWidget(turn_title)
            turn_row = QHBoxLayout()
            self.turn_group = QButtonGroup(self)
            mine = self._choice("My turn", True, self.turn_group)
            opponent = self._choice("Opponent", False, self.turn_group)
            mine.setChecked(True)
            turn_row.addWidget(mine)
            turn_row.addWidget(opponent)
            outer.addLayout(turn_row)

        start = QPushButton("Start analysis")
        start.setObjectName("primaryButton")
        start.clicked.connect(self._accept_values)
        outer.addSpacing(10)
        outer.addWidget(start)

    @staticmethod
    def _choice(text, value, group):
        button = QPushButton(text)
        button.setCheckable(True)
        button.setProperty("value", value)
        button.setObjectName("choiceButton")
        group.addButton(button)
        return button

    def _accept_values(self):
        color_button = self.color_group.checkedButton()
        if color_button is None:
            return
        self.player_color = bool(color_button.property("value"))
        if self.turn_group:
            turn_button = self.turn_group.checkedButton()
            if turn_button is None:
                return
            self.my_turn = bool(turn_button.property("value"))
        self.accept()

    @classmethod
    def get_values(cls, parent=None, ask_turn=True, initial_color=chess.WHITE):
        dialog = cls(parent, ask_turn, initial_color)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.player_color, dialog.my_turn
