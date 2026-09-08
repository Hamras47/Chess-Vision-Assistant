"""Chess Vision Assistant V1.6 entry point."""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.core.resources import resource_path
from app.ui.main_window import MainWindow


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Chess Vision")
    app.setApplicationDisplayName("Chess Vision")
    app.setApplicationVersion("1.6.0")
    icon = resource_path("assets", "icons", "chess-vision.ico")
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
