"""Settings dialog for OpenAI credentials and the local Stockfish engine."""
from __future__ import annotations

import os
from pathlib import Path

import chess.engine
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget, QCheckBox,
)

from app.ai.openai_client import DEFAULT_OPENAI_VISION_MODEL, VISION_MODELS, OpenAIClient
from app.core.credentials import CredentialStore, CredentialStoreError
from app.engine.stockfish import engine_startup_options


def mask_api_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:3]}{'•' * 12}{value[-4:]}"


def friendly_api_error(error: Exception) -> str:
    message = str(error)
    for safe in ("Invalid API key", "Network unavailable", "Request timed out"):
        if safe.lower() in message.lower():
            return safe
    return "API error"


class ConnectionTestWorker(QThread):
    complete = Signal(bool, str)

    def __init__(self, api_key: str, model: str, parent=None):
        super().__init__(parent)
        self.api_key, self.model = api_key, model

    def run(self):
        try:
            OpenAIClient(self.model, api_key=self.api_key).test_connection()
            self.complete.emit(True, "✓ API connection successful")
        except Exception as exc:
            self.complete.emit(False, friendly_api_error(exc))


class EngineTestWorker(QThread):
    complete = Signal(bool, str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        engine = None
        try:
            engine = chess.engine.SimpleEngine.popen_uci(self.path, timeout=5, **engine_startup_options())
            self.complete.emit(True, "✓ Engine detected")
        except Exception:
            self.complete.emit(False, "Could not start engine")
        finally:
            if engine:
                engine.quit()


class SettingsDialog(QDialog):
    def __init__(self, model, engine_path, analysis_ms, parent=None, credential_store=None, suggestions_enabled=True):
        super().__init__(parent)
        self.credential_store = credential_store or CredentialStore()
        self._test_worker = None
        self._engine_worker = None
        try:
            self._saved_key = self.credential_store.get_openai_key()
        except CredentialStoreError:
            self._saved_key = ""
        self.setWindowTitle("Chess Vision Settings")
        self.setMinimumWidth(500)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(16)
        form = QFormLayout()
        form.setVerticalSpacing(12)
        root.addLayout(form)

        heading = QLabel("AI RECOGNITION")
        heading.setObjectName("dialogEyebrow")
        form.addRow(heading)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText(mask_api_key(self._saved_key) or "Paste your OpenAI API key")
        key_row = QWidget()
        key_layout = QHBoxLayout(key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(self.api_key, 1)
        self.show_key = QPushButton("Show")
        self.show_key.setCheckable(True)
        self.show_key.toggled.connect(self._toggle_key)
        key_layout.addWidget(self.show_key)
        remove_key = QPushButton("Remove Saved Key")
        remove_key.clicked.connect(self._remove_key)
        key_layout.addWidget(remove_key)
        form.addRow("API Key", key_row)
        self.model = QComboBox()
        for identifier, label in VISION_MODELS.items():
            self.model.addItem(label, identifier)
        if model not in VISION_MODELS:
            self.model.addItem(f"Developer override: {model}", model)
        self.model.setCurrentIndex(max(0, self.model.findData(model)))
        form.addRow("Recognition model", self.model)
        self.api_status = QLabel("Saved securely" if self._saved_key else ("Using environment key" if os.getenv("OPENAI_API_KEY") else "Not configured"))
        self.test_api = QPushButton("Test Connection")
        self.test_api.clicked.connect(self._test_connection)
        api_actions = QWidget()
        actions = QHBoxLayout(api_actions)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addWidget(self.test_api)
        actions.addWidget(self.api_status, 1)
        form.addRow("", api_actions)

        engine_heading = QLabel("CHESS ENGINE")
        engine_heading.setObjectName("dialogEyebrow")
        form.addRow(engine_heading)
        path_row = QWidget()
        row = QHBoxLayout(path_row)
        row.setContentsMargins(0, 0, 0, 0)
        self.engine_path = QLineEdit(engine_path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.engine_path, 1)
        row.addWidget(browse)
        form.addRow("Engine", path_row)
        self.engine_status = QLabel("✓ Engine detected" if engine_path and Path(engine_path).is_file() else "Not configured")
        self.test_engine = QPushButton("Test Engine")
        self.test_engine.clicked.connect(self._test_engine)
        engine_actions = QWidget()
        engine_row = QHBoxLayout(engine_actions)
        engine_row.setContentsMargins(0, 0, 0, 0)
        engine_row.addWidget(self.test_engine)
        engine_row.addWidget(self.engine_status, 1)
        form.addRow("Status", engine_actions)

        self.analysis_time = QComboBox()
        for milliseconds in (300, 600, 1000, 2000):
            self.analysis_time.addItem(f"{milliseconds} ms", milliseconds)
        index = self.analysis_time.findData(analysis_ms)
        self.analysis_time.setCurrentIndex(index if index >= 0 else 1)
        form.addRow("Move time", self.analysis_time)
        self.suggestions = QCheckBox("Stockfish Suggestions")
        self.suggestions.setChecked(suggestions_enabled)
        self.suggestions.setToolTip("Show best moves, arrows and evaluation. Off stops automatic analysis.")
        form.addRow("", self.suggestions)
        about = QLabel("Chess Vision 3.5  ·  Built by 47 Lab")
        about.setObjectName("muted")
        root.addWidget(about)
        footer = QHBoxLayout()
        footer.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._save)
        footer.addWidget(cancel)
        footer.addWidget(save)
        root.addLayout(footer)

    def _toggle_key(self, visible):
        self.api_key.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
        self.show_key.setText("Hide" if visible else "Show")

    def _remove_key(self):
        try:
            self.credential_store.delete_openai_key()
            self._saved_key = ""
            self.api_key.clear()
            self.api_key.setPlaceholderText("Paste your OpenAI API key")
            self.api_status.setText("Using environment key" if os.getenv("OPENAI_API_KEY") else "Not configured")
        except CredentialStoreError as exc:
            self.api_status.setText(str(exc))

    def effective_key(self):
        return self.api_key.text().strip() or self._saved_key or os.getenv("OPENAI_API_KEY", "").strip()

    def _test_connection(self):
        key = self.effective_key()
        if not key:
            self.api_status.setText("OpenAI API key required")
            return
        self.test_api.setEnabled(False)
        self.api_status.setText("Testing…")
        self._test_worker = ConnectionTestWorker(key, self.model.currentData() or DEFAULT_OPENAI_VISION_MODEL, self)
        self._test_worker.complete.connect(self._api_test_done)
        self._test_worker.start()

    def _api_test_done(self, ok, message):
        self.api_status.setText(message)
        self.test_api.setEnabled(True)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Locate Stockfish", "", "Executable (*.exe);;All files (*)")
        if path:
            self.engine_path.setText(path)
            self.engine_status.setText("Ready to test")

    def _test_engine(self):
        path = self.engine_path.text().strip()
        if not path or not Path(path).is_file():
            self.engine_status.setText("Executable not found")
            return
        self.test_engine.setEnabled(False)
        self.engine_status.setText("Testing…")
        self._engine_worker = EngineTestWorker(path, self)
        self._engine_worker.complete.connect(self._engine_test_done)
        self._engine_worker.start()

    def _engine_test_done(self, ok, message):
        self.engine_status.setText(message)
        self.test_engine.setEnabled(True)

    def _save(self):
        if self._busy():
            self.api_status.setText("Please wait for the current test")
            return
        entered = self.api_key.text().strip()
        try:
            if entered:
                self.credential_store.set_openai_key(entered)
                self._saved_key = entered
        except CredentialStoreError as exc:
            self.api_status.setText(str(exc))
            return
        self.accept()

    def values(self):
        return self.model.currentData(), self.engine_path.text().strip(), self.analysis_time.currentData()

    def _busy(self):
        return any(worker and worker.isRunning() for worker in (self._test_worker, self._engine_worker))

    def reject(self):
        if self._busy():
            self.api_status.setText("Please wait for the current test")
            return
        super().reject()

    def closeEvent(self, event):
        if self._busy():
            self.api_status.setText("Please wait for the current test")
            event.ignore()
            return
        super().closeEvent(event)
