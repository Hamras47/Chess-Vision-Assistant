"""Chess Vision Assistant V1.6 entry point."""
import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Chess Vision")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
