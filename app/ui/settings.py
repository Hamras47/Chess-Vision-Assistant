"""Settings dialog for the only two external services."""
import os

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from app.ai.openai_client import DEFAULT_OPENAI_VISION_MODEL


class SettingsDialog(QDialog):
    def __init__(self, model, engine_path, analysis_ms, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(470)
        form = QFormLayout(self)
        self.model = QLineEdit(model)
        form.addRow("OpenAI model", self.model)
        reset = QPushButton("Use Luna default")
        reset.clicked.connect(lambda: self.model.setText(DEFAULT_OPENAI_VISION_MODEL))
        form.addRow("", reset)
        status = QLabel("Loaded" if os.getenv("OPENAI_API_KEY") else "Missing — add OPENAI_API_KEY to .env")
        status.setObjectName("apiLoaded" if os.getenv("OPENAI_API_KEY") else "apiMissing")
        form.addRow("OpenAI API key", status)

        path_row = QWidget()
        row = QHBoxLayout(path_row)
        row.setContentsMargins(0, 0, 0, 0)
        self.engine_path = QLineEdit(engine_path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.engine_path, 1)
        row.addWidget(browse)
        form.addRow("Stockfish executable", path_row)

        self.analysis_time = QComboBox()
        for milliseconds in (300, 600, 1000, 2000):
            self.analysis_time.addItem(f"{milliseconds} ms", milliseconds)
        index = self.analysis_time.findData(analysis_ms)
        self.analysis_time.setCurrentIndex(index if index >= 0 else 1)
        form.addRow("Move time", self.analysis_time)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Locate Stockfish", "", "Executable (*.exe);;All files (*)")
        if path:
            self.engine_path.setText(path)

    def values(self):
        return self.model.text().strip(), self.engine_path.text().strip(), self.analysis_time.currentData()
