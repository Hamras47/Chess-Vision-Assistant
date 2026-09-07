"""Human-friendly player-color and side-to-move setup."""
import chess
from PySide6.QtWidgets import QButtonGroup, QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.chess.game_state import (
    BLACK_KINGSIDE,
    BLACK_QUEENSIDE,
    WHITE_KINGSIDE,
    WHITE_QUEENSIDE,
)

CASTLING_LABELS = {
    WHITE_KINGSIDE: "King side",
    WHITE_QUEENSIDE: "Queen side",
    BLACK_KINGSIDE: "King side",
    BLACK_QUEENSIDE: "Queen side",
}


class PositionSetupDialog(QDialog):
    def __init__(self, parent=None, ask_turn=True, initial_color=chess.WHITE, castling_options=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Position")
        self.setModal(True)
        self.player_color = initial_color
        self.my_turn = True
        self.castling_rights = set()
        self.castling_boxes = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(10)
        heading = QLabel("Confirm Position")
        heading.setObjectName("dialogTitle")
        outer.addWidget(heading)
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

        options = tuple(castling_options or ())
        if options:
            castling_title = QLabel("Castling still available?")
            castling_title.setObjectName("dialogEyebrow")
            outer.addSpacing(6)
            outer.addWidget(castling_title)
            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(6)
            row = 0
            for color_name, color_options in (
                ("White", (WHITE_KINGSIDE, WHITE_QUEENSIDE)),
                ("Black", (BLACK_KINGSIDE, BLACK_QUEENSIDE)),
            ):
                visible = [option for option in color_options if option in options]
                if not visible:
                    continue
                grid.addWidget(QLabel(color_name), row, 0)
                for column, option in enumerate(visible, 1):
                    checkbox = QCheckBox(CASTLING_LABELS[option])
                    checkbox.setProperty("castling_option", option)
                    checkbox.setChecked(False)
                    self.castling_boxes[option] = checkbox
                    grid.addWidget(checkbox, row, column)
                row += 1
            outer.addLayout(grid)

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
        self.castling_rights = {
            option for option, checkbox in self.castling_boxes.items() if checkbox.isChecked()
        }
        self.accept()

    @classmethod
    def get_values(cls, parent=None, ask_turn=True, initial_color=chess.WHITE, castling_options=None):
        dialog = cls(parent, ask_turn, initial_color, castling_options)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.player_color, dialog.my_turn, dialog.castling_rights
