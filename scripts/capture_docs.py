"""Capture privacy-safe documentation images from real Qt widgets."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
from PySide6.QtCore import QRect
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.chess.game_state import BLACK_KINGSIDE, BLACK_QUEENSIDE, WHITE_KINGSIDE, WHITE_QUEENSIDE
from app.ui.dpi_coordinates import MonitorCoordinates
from app.ui.main_window import MainWindow
from app.ui.region_selector import RegionSelector
from app.ui.settings import SettingsDialog
from app.ui.setup_dialog import PositionSetupDialog


class EmptyCredentialStore:
    def get_openai_key(self): return ""
    def set_openai_key(self, value): pass


def save(widget, path, app):
    widget.show()
    app.processEvents()
    QTest.qWait(220)
    widget.grab().save(str(path))
    widget.close()


def main():
    os.environ.pop("OPENAI_API_KEY", None)
    app = QApplication.instance() or QApplication([])
    output = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)

    MainWindow._find_engine = lambda self: ""
    # Render without inheriting the developer's model/engine preferences.
    import app.ui.main_window as main_module
    main_module.QSettings = lambda *args: QSettings(str(output / "render-preferences.ini"), QSettings.IniFormat)
    window = MainWindow()
    window.resize(960, 760)
    save(window, output / "01-main-window.png", app)

    background = cv2.imread(str(output / "01-main-window.png"))
    selector = RegionSelector(background, MonitorCoordinates(QRect(0, 0, background.shape[1], background.shape[0]), {"left": 0, "top": 0, "width": background.shape[1], "height": background.shape[0]}, 1.0))
    selector.selection = QRect(110, 75, 620, 620)
    save(selector, output / "02-scan-board.png", app)

    confirm = PositionSetupDialog(castling_options=(WHITE_KINGSIDE, WHITE_QUEENSIDE, BLACK_KINGSIDE, BLACK_QUEENSIDE))
    confirm.setStyleSheet(window.styleSheet())
    save(confirm, output / "03-confirm-position.png", app)

    analysis = MainWindow()
    analysis.resize(960, 760)
    analysis.panel.set_analysis([("Nf3", "g1f3", 34, None, 18)])
    analysis.eval_bar.set_evaluation(34)
    analysis.status.setText("")
    analysis.view.arrow = (6, 21)
    save(analysis, output / "04-analysis.png", app)

    settings = SettingsDialog("gpt-5.6-terra", "", 600, credential_store=EmptyCredentialStore())
    settings.setStyleSheet(window.styleSheet())
    save(settings, output / "05-settings.png", app)

    compact = MainWindow()
    compact.resize(700, 800)
    compact.panel.set_analysis([("e4", "e2e4", 21, None, 16)])
    compact.eval_bar.set_evaluation(21)
    compact.status.setText("")
    save(compact, output / "06-split-screen.png", app)
    for width in (1400, 960, 800, 700):
        review = MainWindow()
        review.resize(width, 900)
        review.panel.set_analysis([("Nf3", "g1f3", 42, None, 18)])
        review.eval_bar.set_evaluation(42)
        review.status.setText("")
        review.view.arrow = (6, 21)
        save(review, output / f"review-{width}.png", app)
    moved = MainWindow()
    moved.resize(1150, 800)
    moved.commit_manual_move(12, 28)
    moved.panel.set_analysis([("e5", "e7e5", 31, None, 18)])
    moved.eval_bar.set_evaluation(31)
    moved.status.setText("Position ready")
    save(moved, output / "review-after-e4.png", app)
    settings_off = SettingsDialog("gpt-5.6-terra", "", 600, credential_store=EmptyCredentialStore(), suggestions_enabled=False)
    settings_off.setStyleSheet(window.styleSheet())
    save(settings_off, output / "review-settings-off.png", app)


if __name__ == "__main__":
    main()
