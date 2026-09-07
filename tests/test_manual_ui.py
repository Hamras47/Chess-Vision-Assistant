import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess
import numpy as np
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QPushButton

from app.chess.coordinates import Orientation, mapping_table, square_to_visual, visual_to_square
from app.ui.board_widget import ChessBoardWidget
from app.ui.dpi_coordinates import MonitorCoordinates
from app.ui.main_window import MainWindow
from app.ui.promotion_dialog import PromotionDialog
from app.ui.region_selector import RegionSelector


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def make_window(monkeypatch, app):
    monkeypatch.setattr(MainWindow, "_find_engine", lambda self: "")
    window = MainWindow()
    window.show()
    app.processEvents()
    return window


def test_64_square_mapping_and_orientations():
    for orientation in (Orientation.WHITE_BOTTOM, Orientation.BLACK_BOTTOM):
        mapped = [visual_to_square(row, col, orientation) for row in range(8) for col in range(8)]
        assert len(set(mapped)) == 64
        for square in chess.SQUARES:
            row, col = square_to_visual(square, orientation)
            assert visual_to_square(row, col, orientation) == square
    assert mapping_table(Orientation.WHITE_BOTTOM)[7] == ["a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1"]
    assert mapping_table(Orientation.BLACK_BOTTOM)[7] == ["h8", "g8", "f8", "e8", "d8", "c8", "b8", "a8"]


def test_click_click_legal_move_and_illegal_target(app):
    widget = ChessBoardWidget()
    widget.resize(640, 640)
    widget.show()
    app.processEvents()
    spy = QSignalSpy(widget.move_requested)
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, widget._rect_for(chess.E2).center().toPoint())
    assert widget.selected == chess.E2
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, widget._rect_for(chess.E5).center().toPoint())
    assert spy.count() == 0
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, widget._rect_for(chess.E2).center().toPoint())
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, widget._rect_for(chess.E4).center().toPoint())
    assert spy.count() == 1
    assert list(spy.at(0)) == [chess.E2, chess.E4]
    widget.close()


def test_drag_drop_legal_move(app):
    widget = ChessBoardWidget()
    widget.resize(640, 640)
    widget.show()
    app.processEvents()
    spy = QSignalSpy(widget.move_requested)
    source = widget._rect_for(chess.G1).center().toPoint()
    target = widget._rect_for(chess.F3).center().toPoint()
    QTest.mousePress(widget, Qt.LeftButton, Qt.NoModifier, source)
    QTest.mouseMove(widget, QPoint((source.x() + target.x()) // 2, (source.y() + target.y()) // 2), 20)
    QTest.mouseMove(widget, target, 20)
    QTest.mouseRelease(widget, Qt.LeftButton, Qt.NoModifier, target)
    assert spy.count() == 1
    assert list(spy.at(0)) == [chess.G1, chess.F3]
    widget.close()


def test_main_window_smoke_responsive_and_pieces_render(monkeypatch, app):
    window = make_window(monkeypatch, app)
    assert window.board.board_fen() == chess.STARTING_BOARD_FEN
    assert len(window.view.piece_map()) == 32
    for width, height in ((1150, 800), (900, 650), (1400, 900)):
        window.resize(width, height)
        app.processEvents()
        _, _, square = window.view._layout()
        assert square > 45
        assert window.panel.isVisible()
    image = window.view.grab().toImage()
    assert not image.isNull()
    window.close()


def test_white_piece_on_light_and_black_piece_on_dark_have_contrast(app):
    widget = ChessBoardWidget()
    widget.resize(640, 640)
    widget.show()
    app.processEvents()
    image = widget.grab().toImage()

    def contrasting_pixels(square, background):
        rect = widget._rect_for(square).adjusted(10, 10, -10, -10).toRect()
        count = 0
        for x in range(rect.left(), rect.right() + 1, 2):
            for y in range(rect.top(), rect.bottom() + 1, 2):
                color = image.pixelColor(x, y)
                if sum(abs(component - base) for component, base in zip((color.red(), color.green(), color.blue()), background)) > 75:
                    count += 1
        return count

    assert contrasting_pixels(chess.B1, (216, 212, 197)) > 80
    assert contrasting_pixels(chess.B8, (111, 136, 116)) > 80
    widget.close()


def test_white_and_black_orientation_follow_player(monkeypatch, app):
    window = make_window(monkeypatch, app)
    window.load_position(chess.Board(), chess.BLACK, chess.WHITE)
    assert window.view.orientation == Orientation.BLACK_BOTTOM
    window.load_position(chess.Board(), chess.WHITE, chess.WHITE)
    assert window.view.orientation == Orientation.WHITE_BOTTOM
    window.flip_board()
    assert window.view.orientation == Orientation.BLACK_BOTTOM
    window.close()


def test_manual_moves_both_sides_trigger_analysis(monkeypatch, app):
    window = make_window(monkeypatch, app)
    calls = []
    monkeypatch.setattr(window, "analyze", lambda: calls.append(window.board.turn))
    assert window.commit_manual_move(chess.E2, chess.E4)
    assert window.commit_manual_move(chess.E7, chess.E5)
    assert calls == [chess.BLACK, chess.WHITE]
    assert window.panel.history_label.text() == "1. e4    e5"
    window.close()


def test_stale_stockfish_result_is_ignored(monkeypatch, app):
    window = make_window(monkeypatch, app)
    window.analysis_token = 4
    rows = [("e4", "e2e4", 20, None, 12)]
    window.analysis_done(3, rows)
    assert window.view.arrow is None
    window.analysis_done(4, rows)
    assert window.view.arrow == (chess.E2, chess.E4)
    window.close()


def test_rescan_style_load_resets_history_undo_redo_and_arrow(monkeypatch, app):
    window = make_window(monkeypatch, app)
    monkeypatch.setattr(window, "analyze", lambda: None)
    window.commit_manual_move(chess.E2, chess.E4)
    window.undo()
    window.view.arrow = (chess.E7, chess.E5)
    imported = chess.Board(None)
    imported.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    imported.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    window.load_position(imported, chess.WHITE, chess.BLACK)
    assert not window.game.records and not window.game.can_undo and not window.game.can_redo
    assert window.view.arrow is None
    assert window.board.turn == chess.BLACK
    assert window.board.castling_rights == 0
    window.close()


def test_promotion_and_scan_overlays_construct(app):
    promotion = PromotionDialog(chess.WHITE)
    assert {button.text() for button in promotion.findChildren(QPushButton)} == {"Queen", "Rook", "Bishop", "Knight"}
    assert promotion.isModal()
    promotion.close()
    desktop = np.zeros((600, 800, 3), dtype=np.uint8)
    mapping = MonitorCoordinates(QRect(0, 0, 800, 600), {"left": 0, "top": 0, "width": 800, "height": 600}, 1.0)
    selector = RegionSelector(desktop, mapping)
    selector.show()
    app.processEvents()
    assert selector.cursor().shape() == Qt.CrossCursor
    selector.close()


def test_no_live_tracking_runtime_files_or_imports():
    root = Path(__file__).parents[1]
    forbidden_files = {"tracking_worker.py", "change_detector.py", "move_tracker.py", "session.py", "stabilizer.py"}
    assert not forbidden_files & {path.name for path in (root / "app").rglob("*.py")}
    source = "\n".join(path.read_text(encoding="utf-8") for path in (root / "app").rglob("*.py"))
    for forbidden in ("TrackingWorker", "start_tracking", "tracking_frame", "RECOVERING", "VERIFYING", "TRACKING_LOST", "frame_signature"):
        assert forbidden not in source
